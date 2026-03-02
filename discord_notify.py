#!/usr/bin/env python3
"""
Discord Webhook Notifications
=============================
Send alerts to Discord on video generation success/failure.

Setup:
1. Create a Discord webhook in your server
2. Set DISCORD_WEBHOOK_URL environment variable or add to config
"""

import os
import json
import httpx
from pathlib import Path
from datetime import datetime

# Config
PIPELINE_DIR = Path(__file__).parent
CONFIG_FILE = PIPELINE_DIR / "dashboard_config.json"


def load_config():
    """Load dashboard config."""
    try:
        return json.loads(CONFIG_FILE.read_text())
    except:
        return {}


def save_config(config):
    """Save dashboard config."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_webhook_url():
    """Get Discord webhook URL from env or config."""
    # Try environment variable first
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if url:
        return url
    
    # Try config file
    config = load_config()
    return config.get("discord_webhook_url")


def set_webhook_url(url: str):
    """Save webhook URL to config."""
    config = load_config()
    config["discord_webhook_url"] = url
    save_config(config)


def send_notification(
    title: str,
    message: str,
    status: str = "info",  # info, success, error, warning
    fields: list = None,
    thumbnail_url: str = None
):
    """
    Send a Discord webhook notification.
    
    Args:
        title: Embed title
        message: Main message body
        status: info/success/error/warning (determines color)
        fields: List of {"name": str, "value": str, "inline": bool}
        thumbnail_url: Optional thumbnail image URL
    """
    webhook_url = get_webhook_url()
    
    if not webhook_url:
        print("[Discord] No webhook URL configured, skipping notification")
        return False
    
    # Status colors
    colors = {
        "info": 0x3498db,      # Blue
        "success": 0x2ecc71,   # Green
        "error": 0xe74c3c,     # Red
        "warning": 0xf39c12    # Orange
    }
    
    # Status emojis
    emojis = {
        "info": "ℹ️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️"
    }
    
    embed = {
        "title": f"{emojis.get(status, '📢')} {title}",
        "description": message,
        "color": colors.get(status, colors["info"]),
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": "Video Pipeline"
        }
    }
    
    if fields:
        embed["fields"] = fields
    
    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"[Discord] Notification sent: {title}")
        return True
    except Exception as e:
        print(f"[Discord] Failed to send notification: {e}")
        return False


def notify_video_generated(
    topic: str,
    video_path: str,
    duration_seconds: float = None,
    character_duo: str = None
):
    """Notify that a video was successfully generated."""
    fields = [
        {"name": "📝 Topic", "value": topic, "inline": False}
    ]
    
    if character_duo:
        fields.append({"name": "🎭 Characters", "value": character_duo.replace("_", " ").title(), "inline": True})
    
    if duration_seconds:
        fields.append({"name": "⏱️ Duration", "value": f"{duration_seconds:.1f}s", "inline": True})
    
    if video_path:
        fields.append({"name": "📁 File", "value": Path(video_path).name, "inline": False})
    
    return send_notification(
        title="Video Generated",
        message="A new video has been successfully rendered!",
        status="success",
        fields=fields
    )


def notify_upload_success(
    platform: str,
    topic: str,
    url: str = None
):
    """Notify that a video was uploaded successfully."""
    fields = [
        {"name": "📱 Platform", "value": platform.title(), "inline": True},
        {"name": "📝 Topic", "value": topic, "inline": True}
    ]
    
    if url:
        fields.append({"name": "🔗 Link", "value": url, "inline": False})
    
    return send_notification(
        title=f"Uploaded to {platform.title()}",
        message="Video successfully uploaded!",
        status="success",
        fields=fields
    )


def notify_upload_failed(
    platform: str,
    topic: str,
    error: str
):
    """Notify that an upload failed."""
    fields = [
        {"name": "📱 Platform", "value": platform.title(), "inline": True},
        {"name": "📝 Topic", "value": topic, "inline": True},
        {"name": "❌ Error", "value": error[:500], "inline": False}
    ]
    
    return send_notification(
        title=f"Upload Failed - {platform.title()}",
        message="Video upload encountered an error.",
        status="error",
        fields=fields
    )


def notify_generation_failed(
    topic: str,
    error: str
):
    """Notify that video generation failed."""
    fields = [
        {"name": "📝 Topic", "value": topic, "inline": False},
        {"name": "❌ Error", "value": error[:500], "inline": False}
    ]
    
    return send_notification(
        title="Video Generation Failed",
        message="Failed to generate video.",
        status="error",
        fields=fields
    )


def notify_daily_summary(
    videos_generated: int,
    videos_uploaded: dict,  # {"tiktok": 2, "youtube": 2, "instagram": 1}
    errors: int = 0,
    cost: float = 0.0
):
    """Send a daily summary notification."""
    upload_summary = "\n".join([f"• {k.title()}: {v}" for k, v in videos_uploaded.items()])
    if not upload_summary:
        upload_summary = "No uploads"
    
    fields = [
        {"name": "🎬 Videos Generated", "value": str(videos_generated), "inline": True},
        {"name": "💰 Cost", "value": f"${cost:.2f}", "inline": True},
        {"name": "❌ Errors", "value": str(errors), "inline": True},
        {"name": "📤 Uploads", "value": upload_summary, "inline": False}
    ]
    
    status = "success" if errors == 0 else "warning"
    
    return send_notification(
        title="Daily Summary",
        message=f"Pipeline report for {datetime.now().strftime('%Y-%m-%d')}",
        status=status,
        fields=fields
    )


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            print("Sending test notification...")
            send_notification(
                title="Test Notification",
                message="This is a test from the video pipeline!",
                status="info",
                fields=[
                    {"name": "Test Field", "value": "Test Value", "inline": True}
                ]
            )
        elif sys.argv[1] == "set-webhook":
            if len(sys.argv) > 2:
                set_webhook_url(sys.argv[2])
                print(f"Webhook URL saved!")
            else:
                print("Usage: python discord_notify.py set-webhook <url>")
        elif sys.argv[1] == "get-webhook":
            url = get_webhook_url()
            print(f"Webhook URL: {url or 'Not configured'}")
    else:
        print("Discord Notification Module")
        print("Commands:")
        print("  python discord_notify.py test          - Send test notification")
        print("  python discord_notify.py set-webhook <url>  - Set webhook URL")
        print("  python discord_notify.py get-webhook   - Show current webhook URL")
