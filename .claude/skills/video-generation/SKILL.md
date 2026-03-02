---
name: video-generation
description: Generate videos using the faceless pipeline. Use when user wants to create new videos, modify the rendering process, or troubleshoot video generation issues.
---

# Video Generation Pipeline

## Full Auto-Generation (Recommended)

```bash
cd /Users/anaskhan/.openclaw/workspace/tiktok/pipeline
source venv/bin/activate

# Generate 1 tech video and upload to all platforms
python auto_generate.py --niche tech --num 1

# Generate without uploading
python auto_generate.py --niche tech --num 1 --no-upload

# Generate multiple videos
python auto_generate.py --niche tech --num 5
```

## Manual Pipeline Steps

### Step 1: Generate Script

```bash
python generate_script.py --niche tech --topic "What is Kubernetes?"
# Output: scripts/ep_XXX.json
```

Or create manually:

```json
{
  "topic": "What is Kubernetes?",
  "niche": "tech",
  "character_duo": "peter_stewie",
  "lines": [
    {"character": "Peter", "text": "Hey Stewie, what's this Kubernetes thing?"},
    {"character": "Stewie", "text": "It's container orchestration. Manages deployment, scaling, and operations of containers across clusters."}
  ]
}
```

### Step 2: Render Video

```bash
python pipeline_v2.py --script scripts/ep_XXX.json
# Output: out/ep_XXX_TIMESTAMP_final.mp4
```

### Step 3: Upload (Optional)

```bash
# YouTube
python upload_youtube.py "out/video.mp4" "Title #shorts #tech"

# TikTok
python upload_tiktok.py "out/video.mp4" "Title #fyp #tech"

# Instagram
python upload_instagram.py "out/video.mp4" "Caption #reels #tech"
```

## Pipeline Flow (pipeline_v2.py)

```
Script JSON
    ↓
┌─────────────────────────────────────────────┐
│ For each line:                              │
│   1. Fish.audio TTS → audio/line_X.mp3      │
│   2. Deepgram → word timestamps             │
│   3. Build subtitle track (karaoke style)   │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Compositing:                                │
│   1. Pick random background video           │
│   2. Scale to 1080x1920                     │
│   3. Add topic image (fade in/out at 3s)    │
│   4. Add character PNGs when speaking       │
│   5. Overlay karaoke subtitles              │
│   6. Concatenate audio tracks               │
└─────────────────────────────────────────────┘
    ↓
out/ep_XXX_TIMESTAMP_final.mp4
```

## Customization

### Change Character Duo

Edit `auto_generate.py`:

```python
CHARACTER_DUO = "elon_zuck"  # or "peter_stewie", etc.
```

### Change Background

Backgrounds rotate randomly. To add new ones:

1. Add video to `backgrounds/` (any resolution, will be scaled)
2. Update `BACKGROUNDS` list in `pipeline_v2.py`:

```python
BACKGROUNDS = [
    "backgrounds/subway-720p.mp4",
    "backgrounds/minecraft-parkour.mp4",
    "backgrounds/gta-gameplay.mp4",
    "backgrounds/your-new-video.mp4",  # Add here
]
```

### Adjust Subtitle Styling

In `pipeline_v2.py`, find the subtitle generation section:

```python
# Font size
FONT_SIZE = 48

# Colors (per character, defined in config.json)
# Karaoke highlight: current word in yellow
```

### Change Topic Image Duration

In `pipeline_v2.py`:

```python
TOPIC_IMAGE_FADE_OUT = 3.0  # seconds
```

## Output Specs

| Property | Value |
|----------|-------|
| Resolution | 1080x1920 |
| FPS | 30 |
| Codec | H.264 |
| Audio | AAC 128kbps |
| Max Duration | 60 seconds |

## Debugging

### Check Generated Audio

```bash
ls -la audio/
# Each line gets its own audio file

# Play specific audio
afplay audio/line_0.mp3
```

### Preview Without Upload

```bash
python pipeline_v2.py --script scripts/ep_XXX.json
open out/ep_XXX_*_final.mp4
```

### FFmpeg Debug

Add verbose flag to see FFmpeg output:

```bash
# In pipeline_v2.py, change:
subprocess.run(cmd, check=True)
# To:
subprocess.run(cmd, check=True)  # Remove capture_output if present
```

## Cost Breakdown

| Service | Cost per Video |
|---------|----------------|
| Fish.audio TTS | ~$0.01 |
| Deepgram | ~$0.01 |
| OpenAI GPT-4o | ~$0.01 |
| **Total** | **~$0.03** |
