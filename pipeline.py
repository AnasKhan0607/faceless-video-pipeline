#!/usr/bin/env python3
"""
TikTok Video Pipeline v2
========================
Script → TTS → Subtitles → Character Overlays → Video

Usage: python pipeline.py --script scripts/ep001.json
"""

import argparse
import json
import os
import subprocess
import httpx
from pathlib import Path

# === CONFIG ===
FISH_API_KEY = "40288fd705db4ac08078d3d908687ba9"
FISH_VOICES = {
    "peter": "d75c270eaee14c8aa1e9e980cc37cf1b",
    "stewie": "e91c4f5974f149478a35affe820d02ac",
    "trump": "5196af35f6ff4a0dbf541793fc9f2157",
    "morgan": "76bb6ae7b26c41fbbd484514fdb014c2",
    "spongebob": "54e3a85ac9594ffa83264b8a494b901b",
    "rogan": "0a8f443cf9c34f6f848e01ea7260c549",
    "babar": "98ba6b7be2fe48d493e55b26e7c4b9dd",
    "virat": "43e496790b8f4f9390a9ede0e7cc149b",
}

# Character positions (bottom of screen, left/right)
CHAR_POSITIONS = {
    "peter": {"x": 50, "y": 1350, "file": "peter-final.png"},
    "stewie": {"x": 700, "y": 1350, "file": "stewie.png"},
    "babar": {"x": 50, "y": 1350, "file": "babar.png"},
    "virat": {"x": 700, "y": 1350, "file": "virat.png"},
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


def generate_subtitles(words: list, timeline: list, output_path: Path):
    """Generate .ass subtitle file - one line per character segment."""
    print("📺 Generating subtitles...")
    
    header = """[Script Info]
Title: TikTok Video
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,100,1
Style: Peter,Arial,72,&H00FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,100,1
Style: Stewie,Arial,72,&H5050FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,100,1
Style: Babar,Arial,72,&H00FF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,100,1
Style: Virat,Arial,72,&HFF7F00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,100,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    
    events = []
    
    if words:
        # Match words to timeline segments (one subtitle per character line)
        for entry in timeline:
            start_s = entry["start_s"]
            end_s = entry["end_s"]
            style = entry["character"].capitalize()
            
            # Find words that fall within this segment
            segment_words = [w for w in words if w["start"] >= start_s - 0.1 and w["end"] <= end_s + 0.1]
            
            if segment_words:
                # Build karaoke text for this line
                text_parts = []
                for w in segment_words:
                    duration_cs = int((w["end"] - w["start"]) * 100)
                    text_parts.append(f"{{\\kf{duration_cs}}}{w['word']}")
                
                line_text = " ".join(text_parts)
                start = format_ass_time(start_s)
                end = format_ass_time(end_s)
                events.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{line_text}")
            else:
                # Fallback to plain text
                start = format_ass_time(start_s)
                end = format_ass_time(end_s)
                events.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{entry['line']}")
    else:
        # Line-level subtitles with character colors
        for entry in timeline:
            start = format_ass_time(entry["start_s"])
            end = format_ass_time(entry["end_s"])
            style = entry["character"].capitalize()
            events.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{entry['line']}")
    
    output_path.write_text(header + "\n".join(events))
    print(f"✅ Subtitles: {output_path}")


def composite_video(script: dict, timeline: list, audio_path: Path, subs_path: Path) -> Path:
    """Phase 3: FFmpeg compositing with character overlays and subtitles."""
    episode = script["episode"]
    print("🎬 Compositing video with character overlays...")
    
    bg_video = ASSETS_DIR / "backgrounds" / "subway-720p.mp4"
    if not bg_video.exists():
        raise FileNotFoundError(f"Background video not found: {bg_video}")
    
    duration_s = get_audio_duration(audio_path)
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"{episode}_final.mp4"
    
    # Get unique characters
    characters = list(set(entry["character"] for entry in timeline))
    
    # Build input list
    inputs = [
        "-stream_loop", "-1", "-i", str(bg_video),
        "-i", str(audio_path),
    ]
    
    # Add character images
    char_input_idx = {}
    for i, char in enumerate(characters):
        char_info = CHAR_POSITIONS.get(char)
        if char_info:
            char_file = ASSETS_DIR / "characters" / char_info["file"]
            if char_file.exists():
                inputs.extend(["-i", str(char_file)])
                char_input_idx[char] = i + 2  # +2 for bg and audio
    
    # Build filter_complex
    filters = []
    
    # Scale background to 1080x1920
    filters.append("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg]")
    
    # Process each character image
    for char, input_idx in char_input_idx.items():
        char_info = CHAR_POSITIONS[char]
        
        # Build enable expression for when this character is speaking
        enable_parts = []
        for entry in timeline:
            if entry["character"] == char:
                # Add fade in/out by using opacity
                enable_parts.append(f"between(t,{entry['start_s']},{entry['end_s']})")
        
        enable_expr = "+".join(enable_parts) if enable_parts else "0"
        
        # Scale character image and set position
        filters.append(
            f"[{input_idx}:v]scale=300:-1,format=rgba[{char}_img]"
        )
    
    # Chain overlays
    current = "bg"
    for i, (char, input_idx) in enumerate(char_input_idx.items()):
        char_info = CHAR_POSITIONS[char]
        next_label = f"v{i}"
        
        # Build enable expression
        enable_parts = []
        for entry in timeline:
            if entry["character"] == char:
                enable_parts.append(f"between(t,{entry['start_s']},{entry['end_s']})")
        enable_expr = "+".join(enable_parts) if enable_parts else "0"
        
        filters.append(
            f"[{current}][{char}_img]overlay=x={char_info['x']}:y={char_info['y']}:"
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        # Print the filter for debugging
        print(f"Filter complex: {filter_complex}")
        raise RuntimeError("FFmpeg failed")
    
    print(f"✅ Output: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="TikTok Video Pipeline")
    parser.add_argument("--script", required=True, help="Path to script JSON")
    args = parser.parse_args()
    
    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = BASE_DIR / script_path
    
    with open(script_path) as f:
        script = json.load(f)
    
    print(f"\n🚀 Building: {script['title']}\n")
    
    # Phase 1: Audio
    audio_path, timeline = generate_audio(script)
    
    # Phase 2: Subtitles
    words = get_word_timestamps(audio_path)
    subs_path = audio_path.parent / f"{script['episode']}.ass"
    generate_subtitles(words, timeline, subs_path)
    
    # Phase 3: Video
    output = composite_video(script, timeline, audio_path, subs_path)
    
    print(f"\n🎉 Done! Video saved to: {output}\n")


if __name__ == "__main__":
    main()
