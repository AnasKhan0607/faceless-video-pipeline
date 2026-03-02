#!/usr/bin/env python3
"""
Daily Summary Report
====================
Generates and sends a daily summary of pipeline activity.

Run manually:
  python daily_summary.py

Or schedule via cron for daily reports.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Paths
PIPELINE_DIR = Path(__file__).parent
SCRIPTS_DIR = PIPELINE_DIR / "scripts"
OUT_DIR = PIPELINE_DIR / "out"
LOGS_DIR = PIPELINE_DIR / "logs"
ERROR_LOG_FILE = LOGS_DIR / "errors.json"
CONFIG_FILE = PIPELINE_DIR / "dashboard_config.json"

# Cost per video
COST_PER_VIDEO = 0.03


def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text())
    except:
        return {}


def load_errors():
    try:
        if ERROR_LOG_FILE.exists():
            return json.loads(ERROR_LOG_FILE.read_text())
        return []
    except:
        return []


def get_videos_generated_today():
    """Get videos generated in the last 24 hours."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    videos = []
    for script_path in SCRIPTS_DIR.glob("ep_*.json"):
        try:
            mtime = datetime.fromtimestamp(script_path.stat().st_mtime)
            if mtime > yesterday:
                script = json.loads(script_path.read_text())
                videos.append({
                    "ep_id": script_path.stem,
                    "topic": script.get("topic", "Unknown"),
                    "created": mtime
                })
        except:
            pass
    
    return videos


def get_errors_today():
    """Get errors from the last 24 hours."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    errors = load_errors()
    today_errors = []
    
    for error in errors:
        try:
            error_time = datetime.fromisoformat(error.get("timestamp", "2000-01-01"))
            if error_time > yesterday:
                today_errors.append(error)
        except:
            pass
    
    return today_errors


def get_upload_stats():
    """Get upload statistics (placeholder - would need actual tracking)."""
    # This would need integration with upload logs
    # For now, return empty stats
    return {
        "tiktok": 0,
        "youtube": 0,
        "instagram": 0
    }


def generate_summary():
    """Generate the daily summary report."""
    videos = get_videos_generated_today()
    errors = get_errors_today()
    uploads = get_upload_stats()
    
    # Calculate stats
    num_videos = len(videos)
    num_errors = len(errors)
    total_cost = num_videos * COST_PER_VIDEO
    
    # Group errors by type
    error_types = defaultdict(int)
    for error in errors:
        error_types[error.get("type", "unknown")] += 1
    
    summary = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "videos_generated": num_videos,
        "videos": [{"topic": v["topic"], "ep_id": v["ep_id"]} for v in videos],
        "uploads": uploads,
        "errors": num_errors,
        "error_breakdown": dict(error_types),
        "cost": total_cost
    }
    
    return summary


def format_summary_text(summary):
    """Format summary as readable text."""
    lines = [
        f"📊 **Daily Pipeline Report** - {summary['date']}",
        "",
        f"🎬 **Videos Generated:** {summary['videos_generated']}",
    ]
    
    if summary['videos']:
        lines.append("")
        for v in summary['videos'][:5]:  # Limit to 5
            lines.append(f"  • {v['topic']}")
        if len(summary['videos']) > 5:
            lines.append(f"  ... and {len(summary['videos']) - 5} more")
    
    lines.extend([
        "",
        f"📤 **Uploads:**",
        f"  • TikTok: {summary['uploads'].get('tiktok', 0)}",
        f"  • YouTube: {summary['uploads'].get('youtube', 0)}",
        f"  • Instagram: {summary['uploads'].get('instagram', 0)}",
        "",
        f"❌ **Errors:** {summary['errors']}",
    ])
    
    if summary['error_breakdown']:
        for error_type, count in summary['error_breakdown'].items():
            lines.append(f"  • {error_type}: {count}")
    
    lines.extend([
        "",
        f"💰 **Cost:** ${summary['cost']:.2f}",
    ])
    
    return "\n".join(lines)


def send_discord_summary(summary):
    """Send summary to Discord webhook."""
    try:
        from discord_notify import notify_daily_summary, get_webhook_url
        
        if not get_webhook_url():
            print("No Discord webhook configured")
            return False
        
        return notify_daily_summary(
            videos_generated=summary['videos_generated'],
            videos_uploaded=summary['uploads'],
            errors=summary['errors'],
            cost=summary['cost']
        )
    except ImportError:
        print("discord_notify module not found")
        return False
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")
        return False


def save_summary(summary):
    """Save summary to logs directory."""
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Save to dated file
    summary_file = LOGS_DIR / f"summary_{summary['date']}.json"
    summary_file.write_text(json.dumps(summary, indent=2))
    
    # Append to history
    history_file = LOGS_DIR / "summary_history.json"
    try:
        history = json.loads(history_file.read_text())
    except:
        history = []
    
    history.append(summary)
    
    # Keep last 30 days
    history = history[-30:]
    history_file.write_text(json.dumps(history, indent=2))
    
    return summary_file


def main():
    print("Generating daily summary...")
    
    summary = generate_summary()
    
    # Print to console
    print("\n" + format_summary_text(summary))
    
    # Save to file
    summary_file = save_summary(summary)
    print(f"\nSaved to: {summary_file}")
    
    # Send to Discord
    config = load_config()
    notifications = config.get("notifications", {})
    
    if notifications.get("daily_summary", False):
        print("\nSending to Discord...")
        if send_discord_summary(summary):
            print("✅ Discord notification sent!")
        else:
            print("❌ Failed to send Discord notification")
    else:
        print("\nDiscord daily summary disabled (enable in dashboard)")
    
    return summary


if __name__ == "__main__":
    main()
