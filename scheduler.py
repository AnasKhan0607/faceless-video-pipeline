#!/usr/bin/env python3
"""
Multi-Account Scheduler
=======================
Checks all active accounts and generates/uploads videos based on their schedules.

Run this every 5 minutes via cron or systemd timer:
    */5 * * * * cd /path/to/pipeline && python scheduler.py

Or run once to process any pending schedule slots:
    python scheduler.py --once

Debug mode (shows what would run without executing):
    python scheduler.py --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Load .env file if present
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from accounts import load_accounts, get_active_accounts, get_schedule_for_time

# Paths
PIPELINE_DIR = Path(__file__).parent
STATE_FILE = PIPELINE_DIR / ".scheduler_state.json"
LOGS_DIR = PIPELINE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def load_state() -> dict:
    """Load scheduler state (last run times per account/slot)."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_runs": {}, "last_check": None}


def save_state(state: dict):
    """Save scheduler state."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_day_abbrev(dt: datetime) -> str:
    """Get 3-letter day abbreviation."""
    return dt.strftime("%a").lower()[:3]


def should_run_now(account: dict, slot: dict, state: dict, tolerance_minutes: int = 10) -> bool:
    """
    Check if a scheduled slot should run now.
    
    Args:
        account: Account config
        slot: Schedule slot with time and platforms
        state: Scheduler state
        tolerance_minutes: How many minutes after scheduled time to still trigger
    
    Returns:
        True if should run
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    day_abbrev = get_day_abbrev(now)
    
    # Parse scheduled time
    scheduled_time = slot.get("time", "")
    if not scheduled_time:
        return False
    
    try:
        hour, minute = map(int, scheduled_time.split(":"))
    except ValueError:
        return False
    
    # Check if current time is within tolerance of scheduled time
    scheduled_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    time_diff = (now - scheduled_dt).total_seconds() / 60
    
    # Must be after scheduled time but within tolerance
    if time_diff < 0 or time_diff > tolerance_minutes:
        return False
    
    # Check if already run today for this slot
    run_key = f"{account['id']}_{scheduled_time}_{today}"
    if run_key in state.get("last_runs", {}):
        return False
    
    return True


def mark_as_run(account: dict, slot: dict, state: dict) -> dict:
    """Mark a slot as run for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    scheduled_time = slot.get("time", "")
    run_key = f"{account['id']}_{scheduled_time}_{today}"
    
    if "last_runs" not in state:
        state["last_runs"] = {}
    
    state["last_runs"][run_key] = datetime.now().isoformat()
    
    # Clean up old entries (keep last 7 days)
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    state["last_runs"] = {
        k: v for k, v in state["last_runs"].items()
        if k.split("_")[-1] >= cutoff
    }
    
    return state


def run_for_account(account: dict, platforms: list, dry_run: bool = False) -> bool:
    """
    Generate and upload a video for an account.
    
    Args:
        account: Account config
        platforms: List of platforms to upload to
        dry_run: If True, just log what would happen
    
    Returns:
        True if successful
    """
    account_id = account["id"]
    account_name = account["name"]
    
    print(f"\n{'='*50}")
    print(f"🎬 Running for: {account_name} ({account_id})")
    print(f"📱 Platforms: {', '.join(platforms)}")
    print(f"{'='*50}")
    
    if dry_run:
        print("🔍 DRY RUN - would generate and upload video")
        return True
    
    # Import and run auto_generate
    try:
        from auto_generate import generate_one_video
        
        success = generate_one_video(
            account_id=account_id,
            upload=True,
            platforms=platforms
        )
        
        if success:
            print(f"✅ Successfully generated video for {account_name}")
            log_event("success", account_id, platforms)
        else:
            print(f"❌ Failed to generate video for {account_name}")
            log_event("failure", account_id, platforms, "Generation failed")
        
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        log_event("error", account_id, platforms, str(e))
        return False


def log_event(event_type: str, account_id: str, platforms: list, error: str = None):
    """Log scheduler events."""
    log_file = LOGS_DIR / "scheduler.log"
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "account_id": account_id,
        "platforms": platforms,
        "error": error
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_scheduler(dry_run: bool = False, once: bool = False):
    """
    Main scheduler loop.
    
    Args:
        dry_run: If True, don't actually run anything
        once: If True, run once and exit
    """
    print(f"📅 Scheduler running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    state = load_state()
    now = datetime.now()
    day_abbrev = get_day_abbrev(now)
    
    # Get all active accounts
    accounts = get_active_accounts()
    
    if not accounts:
        print("ℹ️ No active accounts found")
        return
    
    print(f"👥 Found {len(accounts)} active account(s)")
    
    runs_triggered = 0
    
    for account in accounts:
        schedule = account.get("schedule", {})
        days = [d.lower()[:3] for d in schedule.get("days", [])]
        
        # Check if today is a scheduled day
        if day_abbrev not in days:
            continue
        
        # Check each time slot
        for slot in schedule.get("slots", []):
            if should_run_now(account, slot, state):
                platforms = slot.get("platforms", ["tiktok", "youtube", "instagram"])
                
                # Filter to only enabled platforms
                enabled_platforms = [
                    p for p in platforms
                    if account.get("platforms", {}).get(p, {}).get("enabled", False)
                ]
                
                if enabled_platforms:
                    if run_for_account(account, enabled_platforms, dry_run):
                        runs_triggered += 1
                    
                    # Mark as run even if failed (to avoid retry spam)
                    if not dry_run:
                        state = mark_as_run(account, slot, state)
    
    # Save state
    state["last_check"] = now.isoformat()
    if not dry_run:
        save_state(state)
    
    print(f"\n✅ Scheduler complete. Triggered {runs_triggered} run(s).")


def show_schedule():
    """Show upcoming schedule for all accounts."""
    accounts = get_active_accounts()
    
    if not accounts:
        print("No active accounts")
        return
    
    print("\n📅 Scheduled Posts\n")
    
    now = datetime.now()
    today = now.strftime("%A")
    
    for account in accounts:
        schedule = account.get("schedule", {})
        days = schedule.get("days", [])
        slots = schedule.get("slots", [])
        
        platforms = [
            p for p, cfg in account.get("platforms", {}).items()
            if cfg.get("enabled", False)
        ]
        
        print(f"👤 {account['name']} ({account['id']})")
        print(f"   Niche: {account['niche']}")
        print(f"   Platforms: {', '.join(platforms)}")
        print(f"   Days: {', '.join([d.title() for d in days])}")
        print(f"   Times: {', '.join([s['time'] for s in slots])}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Multi-account video scheduler")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    parser.add_argument("--show", action="store_true", help="Show schedule for all accounts")
    parser.add_argument("--run", metavar="ACCOUNT_ID", help="Manually trigger run for specific account")
    args = parser.parse_args()
    
    if args.show:
        show_schedule()
        return
    
    if args.run:
        from accounts import get_account
        account = get_account(args.run)
        if not account:
            print(f"❌ Account not found: {args.run}")
            sys.exit(1)
        
        platforms = [
            p for p, cfg in account.get("platforms", {}).items()
            if cfg.get("enabled", False)
        ]
        run_for_account(account, platforms, args.dry_run)
        return
    
    run_scheduler(dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()
