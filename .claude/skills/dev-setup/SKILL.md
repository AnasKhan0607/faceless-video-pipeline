---
name: dev-setup
description: Set up the local development environment for the faceless video pipeline. Use when user wants to install dependencies, configure API keys, or run the pipeline locally.
---

# Development Setup

## Prerequisites

- **Python 3.10+**: `python3 --version`
- **FFmpeg**: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
- **Pillow dependencies**: Installed via pip

## Quick Setup

### 1. Clone and Enter Directory

```bash
cd /Users/anaskhan/.openclaw/workspace/tiktok/pipeline
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install httpx pillow playwright instagrapi google-api-python-client google-auth-oauthlib streamlit
playwright install chromium
```

### 4. Configure API Keys

API keys are currently hardcoded in `auto_generate.py`. Find and update:

```python
# Fish.audio TTS
FISH_API_KEY = "your-key"

# Deepgram timestamps
DEEPGRAM_API_KEY = "your-key"

# OpenAI script generation
OPENAI_API_KEY = "your-key"
```

### 5. Platform Authentication

#### TikTok
1. Run `python upload_tiktok.py` once
2. Browser opens, log in manually
3. Cookies saved to `tiktok_cookies.json`

#### YouTube
1. Create OAuth credentials at Google Cloud Console
2. Download as `client_secrets.json`
3. Run `python upload_youtube.py` once
4. Complete OAuth flow in browser
5. Token saved to `.youtube_token.json`

#### Instagram
1. Run `python upload_instagram.py` with credentials
2. Session saved to `instagram_session.json`
3. May need to verify via email/SMS on first login

## Verification

```bash
# Test pipeline with existing script
python pipeline_v2.py --script scripts/ep001.json

# Check output
ls -la out/
```

## Running the Dashboard

```bash
streamlit run dashboard.py
# Opens at http://localhost:8501
```

## Directory Permissions

Ensure these directories exist and are writable:
- `audio/` - Generated audio files
- `out/` - Final video output
- `scripts/` - Generated scripts
- `assets/topics/` - Topic images

```bash
mkdir -p audio out scripts assets/topics
```

## Mac Mini Headless Setup

For TikTok uploads without a monitor:

1. **Option A**: HDMI dummy plug (~$10)
2. **Option B**: BetterDisplay app (`brew install --cask betterdisplay`)
3. **Required**: `sudo pmset -a displaysleep 0`

TikTok's web player requires actual GUI rendering.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Activate venv: `source venv/bin/activate` |
| FFmpeg not found | `brew install ffmpeg` |
| Playwright browser missing | `playwright install chromium` |
| Permission denied on audio/ | `chmod 755 audio out scripts` |
