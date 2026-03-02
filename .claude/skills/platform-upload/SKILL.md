---
name: platform-upload
description: Upload videos to TikTok, YouTube Shorts, and Instagram Reels. Use when troubleshooting uploads, setting up platform authentication, or modifying upload behavior.
---

# Platform Upload

## Quick Reference

```bash
cd /Users/anaskhan/.openclaw/workspace/tiktok/pipeline
source venv/bin/activate

# YouTube Shorts
python upload_youtube.py "out/video.mp4" "Title here #shorts #tech"

# TikTok
python upload_tiktok.py "out/video.mp4" "Caption here #fyp #tech"

# Instagram Reels
python upload_instagram.py "out/video.mp4" "Caption here #reels #tech"
```

---

## YouTube Shorts (`upload_youtube.py`)

### How It Works
- Uses Google YouTube Data API v3
- OAuth 2.0 authentication
- Uploads as unlisted by default, then sets to public

### Setup

1. **Create OAuth Credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable YouTube Data API v3
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download JSON as `client_secrets.json`

2. **First Run**
   ```bash
   python upload_youtube.py "test.mp4" "Test"
   # Browser opens for OAuth consent
   # Token saved to .youtube_token.json
   ```

### Token Management
- Token stored in `.youtube_token.json`
- Auto-refreshes when expired
- Delete file to re-authenticate

### Troubleshooting

| Issue | Fix |
|-------|-----|
| 401 Unauthorized | Delete `.youtube_token.json`, re-auth |
| Quota exceeded | Wait 24h or request quota increase |
| Video not showing | May take 10-30min to process |

---

## TikTok (`upload_tiktok.py`)

### How It Works
- Uses Playwright browser automation
- Navigates to TikTok Creator Studio
- Uploads via web interface
- **Requires GUI** (not true headless)

### Setup

1. **Install Playwright**
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **First Run (Login)**
   ```bash
   python upload_tiktok.py "test.mp4" "Test"
   # Browser opens, log in manually
   # Cookies saved to tiktok_cookies.json
   ```

### Cookie Management
- Stored in `tiktok_cookies.json`
- Contains `sessionid` for auth
- Re-login if uploads fail with auth errors

### Headless Mac Mini

TikTok requires actual GUI rendering. Options:

1. **HDMI Dummy Plug** (~$10)
   - Plugs into HDMI port
   - Tricks macOS into thinking monitor is connected

2. **BetterDisplay App**
   ```bash
   brew install --cask betterdisplay
   # Create virtual display in app
   ```

3. **Keep Monitor Connected**
   - Can be powered off
   - `sudo pmset -a displaysleep 0` to prevent sleep

### Known Issues

| Issue | Fix |
|-------|-----|
| "Joyride overlay" intercepts clicks | Script handles this automatically |
| "Content may be restricted" popup | Script dismisses this |
| Upload stuck at 99% | Increase timeout, check network |
| Browser not launching | Ensure Playwright installed |
| Headless fails | Must use `headless=False` |

### Debug Mode

Screenshots are saved to `debug_screenshots/`:
- `01_after_nav.png` - After navigating to upload page
- `02_after_upload.png` - After file upload
- `03_after_caption.png` - After entering caption
- `04_after_post_click.png` - After clicking post

---

## Instagram Reels (`upload_instagram.py`)

### How It Works
- Uses `instagrapi` library
- Uploads via Instagram private API
- More reliable than browser automation

### Setup

1. **Install instagrapi**
   ```bash
   pip install instagrapi
   ```

2. **First Run**
   ```bash
   python upload_instagram.py "test.mp4" "Test caption"
   # Enter username/password when prompted
   # Session saved to instagram_session.json
   ```

### Session Management
- Stored in `instagram_session.json`
- Contains auth tokens
- Delete to re-login

### Two-Factor Auth

If 2FA is enabled:
1. Script will prompt for code
2. Enter code from authenticator/SMS
3. Session saved for future use

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Login failed | Delete session, re-login |
| Challenge required | Complete challenge in app/browser |
| Video too long | Must be < 90 seconds |
| Wrong aspect ratio | Should be 9:16, script handles |

---

## Hashtag Strategy

### Tech Niche
```
#tech #coding #programming #developer #software #learntocode #techlife #fyp #viral
```

### Per Platform
- **TikTok**: `#fyp #foryou #foryoupage` boost discovery
- **YouTube**: `#shorts` required for Shorts
- **Instagram**: `#reels #explore` help discovery

### Best Practices
- 5-10 hashtags per post
- Mix popular + niche tags
- First 3-5 hashtags most important
