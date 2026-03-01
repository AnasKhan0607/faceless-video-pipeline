#!/usr/bin/env python3
"""
TikTok Video Pipeline v3 - FullStackPeter Style
================================================
- Big centered subtitles (1-4 words at a time)
- Word-by-word highlighting
- Large character at bottom (only speaking character visible)
- Topic image at top half

Usage: python pipeline_v2.py --script scripts/ep001.json
"""

import argparse
import json
import os
import random
import subprocess
import httpx
from pathlib import Path

# === CONFIG ===
FISH_API_KEY = "40288fd705db4ac08078d3d908687ba9"
FISH_VOICES = {
    # Cartoon characters
    "peter": "d75c270eaee14c8aa1e9e980cc37cf1b",
    "stewie": "e91c4f5974f149478a35affe820d02ac",
    "spongebob": "54e3a85ac9594ffa83264b8a494b901b",
    # Celebrities
    "morgan": "76bb6ae7b26c41fbbd484514fdb014c2",
    "rogan": "0a8f443cf9c34f6f848e01ea7260c549",
    # Politicians
    "trump": "5196af35f6ff4a0dbf541793fc9f2157",
    "biden": "9b42223616644104a4534968cd612053",
    # Tech bros
    "elon": "03397b4c4be74759b72533b663fbd001",
    "zuckerberg": "b7bb42ad9b194f39a273461985bb6fd2",
    # Rappers
    "drake": "6bf390d5d8ac405a872b76a34cf3a196",
    "kendrick": "f2bfa372e34e4ae198ef478920a9e6c6",
    # Sports GOATs
    "lebron": "cdd2ce5aa47e436a9760b1d4b60265bc",
    "ronaldo": "3cbfb82b132a429e876086b275c710f0",
    # Controversial
    "tate": "beeebb06bb0c4530967cd7dd9b63e2e8",
    # Cricket
    "babar": "98ba6b7be2fe48d493e55b26e7c4b9dd",
    "virat": "43e496790b8f4f9390a9ede0e7cc149b",
}

DEEPGRAM_KEY = os.environ.get("DEEPGRAM_API_KEY", "abb2368e3cde6038043254bba1d5364bd94b8166")

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
AUDIO_DIR = BASE_DIR / "audio"
OUT_DIR = BASE_DIR / "out"


def get_audio_duration(path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", 
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def generate_silence(duration_ms: int, output_path: Path):
    """Generate a silent audio clip (mono to match TTS output)."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration_ms / 1000), "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ], capture_output=True, check=True)


def generate_audio(script: dict) -> tuple[Path, list]:
    """Phase 1: Generate TTS for each line, assemble with pauses."""
    episode = script["episode"]
    ep_audio_dir = AUDIO_DIR / episode
    ep_audio_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎙️ Generating audio for {episode}...")
    
    clips_to_concat = []
    timeline = []
    current_ms = 0
    
    for entry in script["dialogue"]:
        clip_path = ep_audio_dir / f"{entry['id']:03d}_{entry['character']}.mp3"
        
        if not clip_path.exists():
            voice_id = FISH_VOICES.get(entry["character"])
            if not voice_id:
                raise ValueError(f"Unknown character: {entry['character']}")
            
            print(f"  → Generating {clip_path.name}...")
            resp = httpx.post(
                "https://api.fish.audio/v1/tts",
                headers={"Authorization": f"Bearer {FISH_API_KEY}"},
                json={
                    "text": entry["line"],
                    "reference_id": voice_id,
                    "format": "mp3",
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            clip_path.write_bytes(resp.content)
        else:
            print(f"  ✓ {clip_path.name} (cached)")
        
        clip_duration_s = get_audio_duration(clip_path)
        clip_duration_ms = int(clip_duration_s * 1000)
        
        start_ms = current_ms
        end_ms = current_ms + clip_duration_ms
        timeline.append({
            "id": entry["id"],
            "character": entry["character"],
            "line": entry["line"],
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start_s": start_ms / 1000,
            "end_s": end_ms / 1000,
        })
        
        clips_to_concat.append(clip_path)
        current_ms = end_ms
        
        pause_ms = entry.get("pause_after_ms", 0)
        if pause_ms > 0:
            pause_path = ep_audio_dir / f"{entry['id']:03d}_pause.mp3"
            generate_silence(pause_ms, pause_path)
            clips_to_concat.append(pause_path)
            current_ms += pause_ms
    
    print("🔧 Assembling master audio...")
    concat_file = ep_audio_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for clip in clips_to_concat:
            f.write(f"file '{clip.absolute()}'\n")
    
    master_path = ep_audio_dir / f"{episode}_master.mp3"
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), 
        "-af", "aresample=async=1:first_pts=0,aformat=sample_rates=44100:channel_layouts=mono",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(master_path)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg concat warning: {result.stderr[-500:] if result.stderr else 'unknown'}")
    
    timeline_path = ep_audio_dir / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, indent=2))
    
    total_duration = get_audio_duration(master_path)
    print(f"✅ Master audio: {master_path} ({total_duration:.1f}s)")
    return master_path, timeline


def get_word_timestamps(audio_path: Path) -> list:
    """Phase 2: Get word-level timestamps from Deepgram."""
    if not DEEPGRAM_KEY:
        print("⚠️ No DEEPGRAM_API_KEY set, using line-level subtitles")
        return []
    
    print("📝 Getting word timestamps from Deepgram...")
    
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    resp = httpx.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-2", "smart_format": "true"},
        headers={
            "Authorization": f"Token {DEEPGRAM_KEY}",
            "Content-Type": "audio/mpeg",
        },
        content=audio_data,
        timeout=120.0,
    )
    resp.raise_for_status()
    
    words = resp.json()["results"]["channels"][0]["alternatives"][0]["words"]
    words_path = audio_path.parent / "words.json"
    words_path.write_text(json.dumps(words, indent=2))
    
    print(f"✅ Got {len(words)} words with timestamps")
    return words


def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format (H:MM:SS.cc)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def generate_subtitles_v2(words: list, timeline: list, output_path: Path):
    """
    Generate .ass subtitle file - FullStackPeter style
    - Big text, centered in middle of screen
    - 1-4 words at a time
    - Current word highlighted in yellow, others white
    """
    print("📺 Generating subtitles (FullStackPeter style)...")
    
    # Style: Big centered text, middle of screen
    # MarginV=400 puts it roughly in the middle-upper area (above character)
    header = """[Script Info]
Title: TikTok Video
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Impact,120,&H00FFFFFF,&H0000FFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,5,3,5,20,20,400,1
Style: Highlight,Impact,120,&H00FFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,5,3,5,20,20,400,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    
    events = []
    
    if words:
        # Show 1-3 words at a time with highlight on current word
        i = 0
        while i < len(words):
            # Take 1-3 words
            chunk_size = min(3, len(words) - i)
            chunk = words[i:i+chunk_size]
            
            # For each word in the chunk, create a subtitle event
            for j, word in enumerate(chunk):
                start = format_ass_time(word["start"])
                end = format_ass_time(word["end"])
                
                # Build text with current word highlighted
                text_parts = []
                for k, w in enumerate(chunk):
                    if k == j:
                        # Highlighted word (yellow)
                        text_parts.append(f"{{\\c&H00FFFF&}}{w['word']}{{\\c&HFFFFFF&}}")
                    else:
                        text_parts.append(w["word"])
                
                line_text = " ".join(text_parts)
                events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{line_text}")
            
            i += chunk_size
    else:
        # Fallback: show full lines
        for entry in timeline:
            start = format_ass_time(entry["start_s"])
            end = format_ass_time(entry["end_s"])
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{entry['line']}")
    
    output_path.write_text(header + "\n".join(events))
    print(f"✅ Subtitles: {output_path}")


def composite_video_v2(script: dict, timeline: list, audio_path: Path, subs_path: Path) -> Path:
    """
    Phase 3: FFmpeg compositing - FullStackPeter style
    - Large character centered at bottom (only speaking character visible)
    - Topic image at top half (optional)
    """
    episode = script["episode"]
    print("🎬 Compositing video (FullStackPeter style)...")
    
    # Pick a random background video from available ones
    bg_dir = ASSETS_DIR / "backgrounds"
    bg_videos = list(bg_dir.glob("*.mp4"))
    if not bg_videos:
        raise FileNotFoundError(f"No background videos found in: {bg_dir}")
    bg_video = random.choice(bg_videos)
    print(f"  📺 Background: {bg_video.name}")
    
    duration_s = get_audio_duration(audio_path)
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"{episode}_final.mp4"
    
    # Get unique characters and their images
    characters = list(set(entry["character"] for entry in timeline))
    
    # Character image files
    char_files = {
        "peter": ASSETS_DIR / "characters" / "peter-final.png",
        "stewie": ASSETS_DIR / "characters" / "stewie.png",
        "babar": ASSETS_DIR / "characters" / "babar.png",
        "virat": ASSETS_DIR / "characters" / "virat.png",
        "trump": ASSETS_DIR / "characters" / "trump.png",
        "biden": ASSETS_DIR / "characters" / "biden.png",
        "elon": ASSETS_DIR / "characters" / "elon.png",
        "zuckerberg": ASSETS_DIR / "characters" / "zuckerberg.png",
        "lebron": ASSETS_DIR / "characters" / "lebron.png",
        "ronaldo": ASSETS_DIR / "characters" / "ronaldo.png",
        "drake": ASSETS_DIR / "characters" / "drake.png",
        "kendrick": ASSETS_DIR / "characters" / "kendrick.png",
        "tate": ASSETS_DIR / "characters" / "tate.png",
    }
    
    # Check for topic image
    topic_image_path = None
    if "topic_image" in script:
        topic_img = Path(script["topic_image"])
        if not topic_img.is_absolute():
            topic_img = ASSETS_DIR / "topics" / topic_img
        if topic_img.exists():
            topic_image_path = topic_img
            print(f"  📷 Topic image: {topic_img.name}")
    
    # Build input list
    inputs = [
        "-stream_loop", "-1", "-i", str(bg_video),
        "-i", str(audio_path),
    ]
    
    next_input_idx = 2  # bg=0, audio=1
    
    # Add topic image if exists
    topic_input_idx = None
    if topic_image_path:
        inputs.extend(["-i", str(topic_image_path)])
        topic_input_idx = next_input_idx
        next_input_idx += 1
    
    # Add character images
    char_input_idx = {}
    for char in characters:
        char_file = char_files.get(char)
        if char_file and char_file.exists():
            inputs.extend(["-i", str(char_file)])
            char_input_idx[char] = next_input_idx
            next_input_idx += 1
    
    # Build filter_complex
    filters = []
    
    # Scale background to 1080x1920
    filters.append("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg]")
    
    # Process topic image - scale to fit top portion (max 500px height, centered)
    current = "bg"
    if topic_input_idx is not None:
        # Scale topic image, add fade in/out
        # The image stays until fade out completes, then we use eof_action=pass to continue
        filters.append(
            f"[{topic_input_idx}:v]loop=loop=-1:size=1:start=0,setpts=N/FRAME_RATE/TB,"
            f"scale=700:-1,format=rgba,"
            f"fade=t=out:st=3:d=1:alpha=1,"
            f"trim=0:4,setpts=PTS-STARTPTS[topic_img]"
        )
        # Overlay topic image at top center, eof_action=pass continues after image ends
        filters.append(
            f"[{current}][topic_img]overlay=x=(W-w)/2:y=150:eof_action=pass[bg_topic]"
        )
        current = "bg_topic"
    
    # Process each character image - make them LARGE (600px height) and centered
    for char, input_idx in char_input_idx.items():
        # Scale to 600px height, centered at bottom
        filters.append(
            f"[{input_idx}:v]scale=-1:600,format=rgba[{char}_img]"
        )
    
    # Chain overlays - only show speaking character, centered at bottom
    for i, (char, input_idx) in enumerate(char_input_idx.items()):
        next_label = f"v{i}"
        
        # Build enable expression for when this character is speaking
        enable_parts = []
        for entry in timeline:
            if entry["character"] == char:
                enable_parts.append(f"between(t,{entry['start_s']},{entry['end_s']})")
        enable_expr = "+".join(enable_parts) if enable_parts else "0"
        
        # Centered at bottom: x = (1080 - width) / 2, y = 1920 - 600 - 50 = 1270
        # Using overlay_w for dynamic centering
        filters.append(
            f"[{current}][{char}_img]overlay=x=(W-w)/2:y=H-h-50:"
            f"enable='{enable_expr}'[{next_label}]"
        )
        current = next_label
    
    # Add subtitles
    subs_escaped = str(subs_path).replace("\\", "\\\\\\\\").replace(":", "\\\\:")
    filters.append(f"[{current}]ass='{subs_escaped}'[out]")
    
    filter_complex = ";".join(filters)
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-t", str(duration_s),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    
    print(f"  Running FFmpeg (this may take a moment)...")
    # Debug: print full filter_complex
    print(f"  DEBUG filter_complex:\n{filter_complex[:500]}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        print(f"Filter complex: {filter_complex}")
        raise RuntimeError("FFmpeg failed")
    
    print(f"✅ Output: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="TikTok Video Pipeline v2 - FullStackPeter Style")
    parser.add_argument("--script", required=True, help="Path to script JSON")
    args = parser.parse_args()
    
    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = BASE_DIR / script_path
    
    with open(script_path) as f:
        script = json.load(f)
    
    print(f"\n🚀 Building (FullStackPeter style): {script['title']}\n")
    
    # Phase 1: Audio
    audio_path, timeline = generate_audio(script)
    
    # Phase 2: Subtitles
    words = get_word_timestamps(audio_path)
    subs_path = audio_path.parent / f"{script['episode']}_v2.ass"
    generate_subtitles_v2(words, timeline, subs_path)
    
    # Phase 3: Video
    output = composite_video_v2(script, timeline, audio_path, subs_path)
    
    print(f"\n🎉 Done! Video saved to: {output}\n")


if __name__ == "__main__":
    main()
