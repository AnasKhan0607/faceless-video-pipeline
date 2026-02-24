# Faceless Video Pipeline

Automated faceless video generation for TikTok, YouTube Shorts, and Instagram Reels.

## Features

- 🎙️ AI voice generation (Fish.audio)
- 📝 Word-level karaoke subtitles (Deepgram)
- 🎬 Character overlays that appear when speaking
- 🎮 Gameplay backgrounds (Subway Surfers, Minecraft, etc.)
- ⚡ One-command video generation

## Quick Start

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install httpx

# 2. Configure API keys
cp config.example.json config.json
# Edit config.json with your API keys

# 3. Generate a video
python pipeline.py --script scripts/example.json
```

## Folder Structure

```
pipeline/
├── characters/           # Character duos (voices + images)
│   ├── peter_stewie/
│   │   ├── config.json   # Voice IDs, colors, positions
│   │   ├── peter.png
│   │   └── stewie.png
│   └── babar_virat/
│       └── ...
├── backgrounds/          # Gameplay footage
│   ├── subway_surfers/
│   └── minecraft_parkour/
├── niches/               # Topic lists per niche
│   ├── tech/
│   │   └── topics.json
│   └── cricket/
│       └── topics.json
├── scripts/              # Generated scripts
├── audio/                # Generated audio (gitignored)
├── out/                  # Final videos (gitignored)
├── queue/                # Videos pending review
├── completed/            # Uploaded videos
├── pipeline.py           # Main script
└── config.json           # API keys (gitignored)
```

## Configuration

### config.json

```json
{
  "fish_api_key": "YOUR_FISH_AUDIO_API_KEY",
  "deepgram_api_key": "YOUR_DEEPGRAM_API_KEY"
}
```

### Character Duo (characters/*/config.json)

```json
{
  "duo_name": "peter_stewie",
  "char1": {
    "name": "peter",
    "display_name": "Peter Griffin",
    "voice_id": "d75c270eaee14c8aa1e9e980cc37cf1b",
    "image": "peter.png",
    "subtitle_color": "&H00FFFF",
    "position": {"x": 50, "y": 1350}
  },
  "char2": {
    "name": "stewie",
    "display_name": "Stewie Griffin", 
    "voice_id": "e91c4f5974f149478a35affe820d02ac",
    "image": "stewie.png",
    "subtitle_color": "&H5050FF",
    "position": {"x": 700, "y": 1350}
  }
}
```

### Topics List (niches/*/topics.json)

```json
{
  "niche": "tech",
  "topics": [
    "What is an API",
    "How does Git work",
    "REST vs GraphQL",
    "What is Docker"
  ]
}
```

## Script Format

```json
{
  "episode": "ep001",
  "title": "What is an API",
  "duo": "peter_stewie",
  "background": "subway_surfers",
  "dialogue": [
    {
      "id": 1,
      "character": "peter",
      "line": "Hey Stewie, you know what an API is?",
      "pause_after_ms": 300
    }
  ]
}
```

## Cost

~$0.03 per video:
- Fish.audio TTS: ~$0.02
- Deepgram transcription: ~$0.01

## Requirements

- Python 3.10+
- FFmpeg (with libass for subtitles)
- Fish.audio API key
- Deepgram API key

## License

Private - All rights reserved
