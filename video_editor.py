#!/usr/bin/env python3
"""
AI-Powered Video Editor
=======================
Uses OpenAI to interpret natural language prompts and generate FFmpeg commands.

Usage:
  python video_editor.py input.mp4 "trim first 5 seconds"
  python video_editor.py input.mp4 "add text 'Subscribe!' at bottom" --output edited.mp4
  python video_editor.py input.mp4 "speed up 1.5x" --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
PIPELINE_DIR = Path(__file__).parent
EDITED_DIR = PIPELINE_DIR / "edited"
LOGS_DIR = PIPELINE_DIR / "logs"

# Ensure directories exist
EDITED_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def get_video_info(video_path: Path) -> dict:
    """Get video metadata using ffprobe."""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(video_path)
        ], capture_output=True, text=True)
        
        data = json.loads(result.stdout)
        
        # Extract useful info
        video_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "audio"), {})
        fmt = data.get("format", {})
        
        return {
            "duration": float(fmt.get("duration", 0)),
            "size_mb": int(fmt.get("size", 0)) / (1024 * 1024),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": eval(video_stream.get("r_frame_rate", "30/1")),
            "video_codec": video_stream.get("codec_name", "unknown"),
            "audio_codec": audio_stream.get("codec_name", "none"),
            "bitrate": int(fmt.get("bit_rate", 0)) // 1000,  # kbps
        }
    except Exception as e:
        return {"error": str(e)}


def generate_ffmpeg_command(
    video_path: Path,
    prompt: str,
    output_path: Path,
    video_info: dict
) -> dict:
    """Use OpenAI to generate an FFmpeg command from a natural language prompt."""
    
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY not set"}
    
    system_prompt = f"""You are an FFmpeg expert. Generate FFmpeg commands based on user requests.

VIDEO INFO:
- Duration: {video_info.get('duration', 0):.1f} seconds
- Resolution: {video_info.get('width', 0)}x{video_info.get('height', 0)}
- FPS: {video_info.get('fps', 30)}
- Input file: {video_path.name}
- Output file: {output_path.name}

RULES:
1. Output ONLY valid JSON with this structure:
   {{"command": ["ffmpeg", "-i", "input.mp4", ...], "description": "what this does"}}
2. Always use "-y" flag to overwrite output
3. For text overlays, use drawtext filter with fontsize appropriate for {video_info.get('height', 1920)}p video
4. Use "-c:v libx264 -c:a aac" for good compatibility
5. Keep quality high with "-crf 18" or similar
6. For trimming, use -ss (start) and -t (duration) or -to (end time)
7. Input path: "{video_path}"
8. Output path: "{output_path}"

COMMON PATTERNS:
- Trim start: -ss START_TIME
- Trim duration: -t DURATION  
- Trim to end time: -to END_TIME
- Speed up: -filter:v "setpts=0.5*PTS" -filter:a "atempo=2.0" (for 2x)
- Add text: -vf "drawtext=text='TEXT':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=h-100"
- Fade in: -vf "fade=t=in:st=0:d=1"
- Fade out: -vf "fade=t=out:st=DURATION-1:d=1"
- Mute: -an
- Volume: -filter:a "volume=0.5" (for 50%)

Output valid JSON only. No markdown, no explanation outside JSON."""

    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate FFmpeg command for: {prompt}"}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return {"error": f"OpenAI API error: {response.text}"}
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Parse JSON from response
        if content.startswith("```"):
            content = re.sub(r"```json?\n?", "", content)
            content = content.replace("```", "").strip()
        
        parsed = json.loads(content)
        return parsed
        
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response: {e}", "raw": content}
    except Exception as e:
        return {"error": f"AI generation failed: {e}"}


def execute_ffmpeg(command: list, dry_run: bool = False) -> dict:
    """Execute an FFmpeg command."""
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "command": " ".join(command)
        }
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(command)
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out (5 min limit)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def edit_video(
    video_path: str | Path,
    prompt: str,
    output_path: str | Path = None,
    dry_run: bool = False
) -> dict:
    """
    Main function to edit a video using AI-generated FFmpeg commands.
    
    Args:
        video_path: Path to input video
        prompt: Natural language description of desired edit
        output_path: Optional output path (auto-generated if not provided)
        dry_run: If True, only show command without executing
    
    Returns:
        Dict with results including command, success status, output path
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        return {"success": False, "error": f"Video not found: {video_path}"}
    
    # Generate output path if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = EDITED_DIR / f"{video_path.stem}_edited_{timestamp}.mp4"
    else:
        output_path = Path(output_path)
    
    # Get video info
    print(f"📹 Analyzing video: {video_path.name}")
    video_info = get_video_info(video_path)
    if "error" in video_info:
        return {"success": False, "error": f"Failed to analyze video: {video_info['error']}"}
    
    print(f"   Duration: {video_info['duration']:.1f}s, Resolution: {video_info['width']}x{video_info['height']}")
    
    # Generate FFmpeg command
    print(f"🤖 Generating FFmpeg command for: {prompt}")
    ai_result = generate_ffmpeg_command(video_path, prompt, output_path, video_info)
    
    if "error" in ai_result:
        return {"success": False, "error": ai_result["error"]}
    
    command = ai_result.get("command", [])
    description = ai_result.get("description", "")
    
    if not command:
        return {"success": False, "error": "AI did not generate a valid command"}
    
    print(f"📝 {description}")
    print(f"🔧 Command: {' '.join(command[:6])}...")
    
    # Execute
    if dry_run:
        print("🔍 DRY RUN - command not executed")
        return {
            "success": True,
            "dry_run": True,
            "command": command,
            "description": description,
            "output_path": str(output_path)
        }
    
    print("⚙️ Executing FFmpeg...")
    exec_result = execute_ffmpeg(command)
    
    if exec_result["success"]:
        output_path = Path(output_path)
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"✅ Success! Output: {output_path.name} ({size_mb:.1f} MB)")
            
            # Log the edit
            log_edit(video_path, prompt, command, output_path)
            
            return {
                "success": True,
                "command": command,
                "description": description,
                "output_path": str(output_path),
                "size_mb": size_mb
            }
        else:
            return {"success": False, "error": "FFmpeg completed but output file not found"}
    else:
        print(f"❌ FFmpeg failed: {exec_result.get('error', exec_result.get('stderr', 'Unknown error'))}")
        return {
            "success": False,
            "error": exec_result.get("error", exec_result.get("stderr")),
            "command": command
        }


def log_edit(video_path: Path, prompt: str, command: list, output_path: Path):
    """Log edit to history file."""
    log_file = LOGS_DIR / "edits.json"
    
    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text())
        except:
            logs = []
    
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "input": str(video_path.name),
        "prompt": prompt,
        "command": " ".join(command),
        "output": str(output_path.name)
    })
    
    # Keep last 100 edits
    logs = logs[-100:]
    log_file.write_text(json.dumps(logs, indent=2))


def get_edit_history() -> list:
    """Get edit history."""
    log_file = LOGS_DIR / "edits.json"
    if not log_file.exists():
        return []
    try:
        return json.loads(log_file.read_text())
    except:
        return []


# Preset edits for common operations
PRESETS = {
    "trim_start_2s": "Trim the first 2 seconds",
    "trim_end_2s": "Trim the last 2 seconds", 
    "speed_1.5x": "Speed up the video 1.5x",
    "speed_2x": "Speed up the video 2x",
    "slow_0.5x": "Slow down the video to 0.5x speed",
    "fade_in_out": "Add 0.5 second fade in at start and fade out at end",
    "mute": "Remove all audio",
    "volume_50": "Reduce volume to 50%",
    "text_subscribe": "Add white text 'SUBSCRIBE!' at bottom center for the last 3 seconds",
    "text_follow": "Add white text 'Follow for more!' at bottom center for the last 3 seconds",
    "grayscale": "Convert to black and white / grayscale",
    "brightness_up": "Increase brightness by 20%",
    "sharpen": "Apply sharpening filter",
}


def main():
    parser = argparse.ArgumentParser(description="AI-powered video editor")
    parser.add_argument("video", nargs="?", help="Input video file")
    parser.add_argument("prompt", nargs="?", help="Edit prompt (or use --preset)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--dry-run", action="store_true", help="Show command without executing")
    parser.add_argument("--preset", "-p", help="Use a preset edit", choices=list(PRESETS.keys()))
    parser.add_argument("--list-presets", action="store_true", help="List available presets")
    args = parser.parse_args()
    
    if args.list_presets:
        print("\n📋 Available Presets:\n")
        for key, desc in PRESETS.items():
            print(f"  {key:20} → {desc}")
        print()
        return
    
    if not args.video:
        print("❌ Please provide a video file")
        print("   Example: python video_editor.py video.mp4 \"trim first 5 seconds\"")
        sys.exit(1)
    
    prompt = args.prompt
    if args.preset:
        prompt = PRESETS.get(args.preset)
    
    if not prompt:
        print("❌ Please provide a prompt or use --preset")
        print("   Example: python video_editor.py video.mp4 \"trim first 5 seconds\"")
        print("   Example: python video_editor.py video.mp4 --preset speed_1.5x")
        sys.exit(1)
    
    result = edit_video(
        video_path=args.video,
        prompt=prompt,
        output_path=args.output,
        dry_run=args.dry_run
    )
    
    if not result["success"]:
        print(f"\n❌ Error: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
