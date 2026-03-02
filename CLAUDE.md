# Faceless Video Pipeline

Automated faceless video generation for TikTok, YouTube Shorts, and Instagram Reels.

## Core Workflow

1. **Script Generation** → GPT-4o creates dialogue for character duo
2. **TTS** → Fish.audio generates character voices
3. **Timestamps** → Deepgram extracts word-level timing
4. **Compositing** → FFmpeg combines background + characters + karaoke subtitles
5. **Upload** → Playwright (TikTok) / Google API (YouTube) / instagrapi (Instagram)

---

## Common Commands

```bash
# Activate virtual environment
cd /Users/anaskhan/.openclaw/workspace/tiktok/pipeline
source venv/bin/activate

# Generate + upload a single video (full pipeline)
python auto_generate.py --niche tech --num 1

# Generate video from existing script
python pipeline_v2.py --script scripts/ep_XXX.json

# Upload to specific platforms
python upload_youtube.py "out/video.mp4" "Title #hashtags"
python upload_tiktok.py "out/video.mp4" "Title #hashtags"
python upload_instagram.py "out/video.mp4" "Caption #hashtags"

# Run the dashboard
streamlit run dashboard.py
```

---

## Project Structure

```
pipeline/
├── auto_generate.py      # Full pipeline: script gen → render → upload
├── pipeline_v2.py        # Video rendering (TTS + subtitles + compositing)
├── generate_script.py    # GPT-4o script generation
├── upload_youtube.py     # YouTube Shorts upload (Google API)
├── upload_tiktok.py      # TikTok upload (Playwright)
├── upload_instagram.py   # Instagram Reels upload (instagrapi)
├── dashboard.py          # Streamlit monitoring dashboard
├── characters/           # Character duos (voices + images)
│   ├── peter_stewie/
│   │   ├── config.json   # Voice IDs, colors, positions
│   │   ├── peter.png
│   │   └── stewie.png
│   └── elon_zuck/
├── backgrounds/          # Gameplay footage
│   ├── subway-720p.mp4   # 63MB
│   ├── minecraft-parkour.mp4  # 28MB
│   └── gta-gameplay.mp4  # 96MB
├── niches/               # Topic lists per niche
│   └── tech/
│       └── topics.json   # 100 tech topics
├── assets/topics/        # Generated topic images (PNG)
├── scripts/              # Generated script JSONs
├── audio/                # Generated audio (gitignored)
└── out/                  # Final videos (gitignored)
```

---

## API Keys Required

| Service | Purpose | Env Var |
|---------|---------|---------|
| OpenAI | Script generation (GPT-4o) | `OPENAI_API_KEY` |
| Fish.audio | TTS voices | In `auto_generate.py` |
| Deepgram | Word timestamps | In `auto_generate.py` |

---

## Character Configuration

Each character duo lives in `characters/<duo_name>/`:

```json
// config.json
{
  "character_a": {
    "name": "Peter",
    "voice_id": "fish-audio-voice-id",
    "color": "#FFD700",
    "position": "left"
  },
  "character_b": {
    "name": "Stewie",
    "voice_id": "fish-audio-voice-id",
    "color": "#FF6B6B",
    "position": "right"
  }
}
```

Character PNGs appear when that character speaks.

---

## Script JSON Format

```json
{
  "topic": "What is Docker?",
  "niche": "tech",
  "character_duo": "peter_stewie",
  "lines": [
    {
      "character": "Peter",
      "text": "Hey Stewie, what the heck is Docker?"
    },
    {
      "character": "Stewie",
      "text": "Docker is containerization. It packages your app with all dependencies into an isolated container."
    }
  ]
}
```

---

## Video Specs

| Property | Value |
|----------|-------|
| Resolution | 1080x1920 (9:16 vertical) |
| Duration | < 60 seconds |
| Background | Random gameplay footage |
| Subtitles | Karaoke-style, word-by-word highlight |
| Topic Image | Fades in at start, fades out at 3s |
| Cost | ~$0.03/video |

---

## Upload Notes

### TikTok (`upload_tiktok.py`)
- Uses Playwright with `headless=False` (TikTok detects headless mode)
- Requires GUI rendering (Mac mini needs monitor/HDMI dummy plug)
- Cookies stored in `tiktok_cookies.json`
- Handles Joyride overlay + "Content may be restricted" popup

### YouTube (`upload_youtube.py`)
- Uses Google API with OAuth
- Token stored in `.youtube_token.json`
- Client secrets in `client_secrets.json`

### Instagram (`upload_instagram.py`)
- Uses `instagrapi` library
- Session stored in `instagram_session.json`
- More reliable than browser automation

---

## Cron Jobs (OpenClaw)

| Schedule | Job ID | What |
|----------|--------|------|
| 10am daily | `4eb50692...` | Generate + upload 1 video |
| 6pm daily | `9409fc7c...` | Generate + upload 1 video |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| TikTok upload fails headless | Need monitor/HDMI dummy plug for GUI |
| Fish.audio 401 | Check API key in `auto_generate.py` |
| Deepgram fails | Check API key in `auto_generate.py` |
| YouTube auth expired | Delete `.youtube_token.json`, re-run |
| Instagram login failed | Delete `instagram_session.json`, re-run |
| FFmpeg not found | `brew install ffmpeg` |
| Topic image not rendering | Check Pillow install: `pip install Pillow` |

---

## Adding New Content

### New Character Duo
1. Create `characters/<duo_name>/`
2. Add `config.json` with voice IDs + colors
3. Add character PNG images (transparent background)
4. Update `auto_generate.py` to include new duo

### New Niche
1. Create `niches/<niche_name>/`
2. Add `topics.json` with 100 topics
3. Run `python auto_generate.py --niche <niche_name>`

### New Background
1. Add video to `backgrounds/` (720p, landscape OK)
2. Update `BACKGROUNDS` list in `pipeline_v2.py`
