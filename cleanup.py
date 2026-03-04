#!/usr/bin/env python3
"""
Video Pipeline Cleanup
======================
Automatically delete old videos, audio, and scripts to save disk space.

Usage:
  python cleanup.py                    # Dry run (show what would be deleted)
  python cleanup.py --execute          # Actually delete files
  python cleanup.py --days 7           # Delete files older than 7 days
  python cleanup.py --keep-scripts     # Keep script files, only delete media
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Paths
PIPELINE_DIR = Path(__file__).parent
OUT_DIR = PIPELINE_DIR / "out"
AUDIO_DIR = PIPELINE_DIR / "audio"
SCRIPTS_DIR = PIPELINE_DIR / "scripts"
TOPICS_IMG_DIR = PIPELINE_DIR / "assets" / "topics"
CLEANUP_LOG = PIPELINE_DIR / "logs" / "cleanup.json"

# Ensure logs directory exists
(PIPELINE_DIR / "logs").mkdir(exist_ok=True)


def get_file_age_days(filepath: Path) -> float:
    """Get file age in days."""
    mtime = filepath.stat().st_mtime
    age_seconds = datetime.now().timestamp() - mtime
    return age_seconds / (60 * 60 * 24)


def get_file_size_mb(filepath: Path) -> float:
    """Get file size in MB."""
    return filepath.stat().st_size / (1024 * 1024)


def get_storage_stats() -> dict:
    """Get current storage usage statistics."""
    stats = {
        "videos": {"count": 0, "size_mb": 0, "oldest_days": 0},
        "audio": {"count": 0, "size_mb": 0, "oldest_days": 0},
        "scripts": {"count": 0, "size_mb": 0, "oldest_days": 0},
        "topic_images": {"count": 0, "size_mb": 0, "oldest_days": 0},
        "total_mb": 0,
    }
    
    # Videos
    if OUT_DIR.exists():
        for f in OUT_DIR.glob("*.mp4"):
            stats["videos"]["count"] += 1
            stats["videos"]["size_mb"] += get_file_size_mb(f)
            age = get_file_age_days(f)
            if age > stats["videos"]["oldest_days"]:
                stats["videos"]["oldest_days"] = age
    
    # Audio
    if AUDIO_DIR.exists():
        for f in AUDIO_DIR.glob("*"):
            if f.is_file():
                stats["audio"]["count"] += 1
                stats["audio"]["size_mb"] += get_file_size_mb(f)
                age = get_file_age_days(f)
                if age > stats["audio"]["oldest_days"]:
                    stats["audio"]["oldest_days"] = age
    
    # Scripts
    if SCRIPTS_DIR.exists():
        for f in SCRIPTS_DIR.glob("*.json"):
            stats["scripts"]["count"] += 1
            stats["scripts"]["size_mb"] += get_file_size_mb(f)
            age = get_file_age_days(f)
            if age > stats["scripts"]["oldest_days"]:
                stats["scripts"]["oldest_days"] = age
    
    # Topic images
    if TOPICS_IMG_DIR.exists():
        for f in TOPICS_IMG_DIR.glob("*.png"):
            stats["topic_images"]["count"] += 1
            stats["topic_images"]["size_mb"] += get_file_size_mb(f)
            age = get_file_age_days(f)
            if age > stats["topic_images"]["oldest_days"]:
                stats["topic_images"]["oldest_days"] = age
    
    stats["total_mb"] = (
        stats["videos"]["size_mb"] +
        stats["audio"]["size_mb"] +
        stats["scripts"]["size_mb"] +
        stats["topic_images"]["size_mb"]
    )
    
    return stats


def find_old_files(max_age_days: int = 14) -> dict:
    """Find files older than max_age_days."""
    old_files = {
        "videos": [],
        "audio": [],
        "scripts": [],
        "topic_images": [],
    }
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    cutoff_ts = cutoff.timestamp()
    
    # Videos
    if OUT_DIR.exists():
        for f in OUT_DIR.glob("*.mp4"):
            if f.stat().st_mtime < cutoff_ts:
                old_files["videos"].append(f)
    
    # Audio - find folders/files matching old videos
    if AUDIO_DIR.exists():
        for f in AUDIO_DIR.glob("*"):
            if f.stat().st_mtime < cutoff_ts:
                old_files["audio"].append(f)
    
    # Scripts
    if SCRIPTS_DIR.exists():
        for f in SCRIPTS_DIR.glob("ep_*.json"):
            if f.stat().st_mtime < cutoff_ts:
                old_files["scripts"].append(f)
    
    # Topic images
    if TOPICS_IMG_DIR.exists():
        for f in TOPICS_IMG_DIR.glob("ep_*.png"):
            if f.stat().st_mtime < cutoff_ts:
                old_files["topic_images"].append(f)
    
    return old_files


def cleanup(
    max_age_days: int = 14,
    execute: bool = False,
    keep_scripts: bool = False,
    keep_topic_images: bool = False,
) -> dict:
    """
    Clean up old files.
    
    Args:
        max_age_days: Delete files older than this
        execute: If False, dry run only
        keep_scripts: Keep script JSON files
        keep_topic_images: Keep topic image PNGs
    
    Returns:
        Summary of deleted files
    """
    old_files = find_old_files(max_age_days)
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "max_age_days": max_age_days,
        "dry_run": not execute,
        "deleted": {
            "videos": {"count": 0, "size_mb": 0, "files": []},
            "audio": {"count": 0, "size_mb": 0, "files": []},
            "scripts": {"count": 0, "size_mb": 0, "files": []},
            "topic_images": {"count": 0, "size_mb": 0, "files": []},
        },
        "total_freed_mb": 0,
    }
    
    # Delete videos
    for f in old_files["videos"]:
        size_mb = get_file_size_mb(f)
        summary["deleted"]["videos"]["count"] += 1
        summary["deleted"]["videos"]["size_mb"] += size_mb
        summary["deleted"]["videos"]["files"].append(str(f.name))
        if execute:
            f.unlink()
    
    # Delete audio
    for f in old_files["audio"]:
        if f.is_dir():
            size_mb = sum(get_file_size_mb(x) for x in f.rglob("*") if x.is_file())
        else:
            size_mb = get_file_size_mb(f)
        summary["deleted"]["audio"]["count"] += 1
        summary["deleted"]["audio"]["size_mb"] += size_mb
        summary["deleted"]["audio"]["files"].append(str(f.name))
        if execute:
            if f.is_dir():
                shutil.rmtree(f)
            else:
                f.unlink()
    
    # Delete scripts (unless keep_scripts)
    if not keep_scripts:
        for f in old_files["scripts"]:
            size_mb = get_file_size_mb(f)
            summary["deleted"]["scripts"]["count"] += 1
            summary["deleted"]["scripts"]["size_mb"] += size_mb
            summary["deleted"]["scripts"]["files"].append(str(f.name))
            if execute:
                f.unlink()
    
    # Delete topic images (unless keep_topic_images)
    if not keep_topic_images:
        for f in old_files["topic_images"]:
            size_mb = get_file_size_mb(f)
            summary["deleted"]["topic_images"]["count"] += 1
            summary["deleted"]["topic_images"]["size_mb"] += size_mb
            summary["deleted"]["topic_images"]["files"].append(str(f.name))
            if execute:
                f.unlink()
    
    summary["total_freed_mb"] = (
        summary["deleted"]["videos"]["size_mb"] +
        summary["deleted"]["audio"]["size_mb"] +
        summary["deleted"]["scripts"]["size_mb"] +
        summary["deleted"]["topic_images"]["size_mb"]
    )
    
    # Log cleanup
    if execute:
        log_cleanup(summary)
    
    return summary


def log_cleanup(summary: dict):
    """Log cleanup to cleanup.json."""
    logs = []
    if CLEANUP_LOG.exists():
        try:
            logs = json.loads(CLEANUP_LOG.read_text())
        except:
            logs = []
    
    # Keep only last 30 cleanups
    logs.append(summary)
    logs = logs[-30:]
    
    CLEANUP_LOG.write_text(json.dumps(logs, indent=2))


def get_last_cleanup() -> dict | None:
    """Get the last cleanup summary."""
    if not CLEANUP_LOG.exists():
        return None
    try:
        logs = json.loads(CLEANUP_LOG.read_text())
        return logs[-1] if logs else None
    except:
        return None


def main():
    parser = argparse.ArgumentParser(description="Clean up old video pipeline files")
    parser.add_argument("--days", type=int, default=14, help="Delete files older than N days (default: 14)")
    parser.add_argument("--execute", action="store_true", help="Actually delete files (default: dry run)")
    parser.add_argument("--keep-scripts", action="store_true", help="Keep script JSON files")
    parser.add_argument("--keep-images", action="store_true", help="Keep topic image PNGs")
    parser.add_argument("--stats", action="store_true", help="Show storage stats only")
    args = parser.parse_args()
    
    if args.stats:
        stats = get_storage_stats()
        print("\n📊 Storage Statistics")
        print("=" * 40)
        print(f"Videos:       {stats['videos']['count']:3} files, {stats['videos']['size_mb']:7.1f} MB (oldest: {stats['videos']['oldest_days']:.0f} days)")
        print(f"Audio:        {stats['audio']['count']:3} files, {stats['audio']['size_mb']:7.1f} MB (oldest: {stats['audio']['oldest_days']:.0f} days)")
        print(f"Scripts:      {stats['scripts']['count']:3} files, {stats['scripts']['size_mb']:7.1f} MB (oldest: {stats['scripts']['oldest_days']:.0f} days)")
        print(f"Topic Images: {stats['topic_images']['count']:3} files, {stats['topic_images']['size_mb']:7.1f} MB (oldest: {stats['topic_images']['oldest_days']:.0f} days)")
        print("-" * 40)
        print(f"Total:                    {stats['total_mb']:7.1f} MB")
        return
    
    mode = "🗑️ EXECUTING CLEANUP" if args.execute else "🔍 DRY RUN (use --execute to delete)"
    print(f"\n{mode}")
    print(f"Deleting files older than {args.days} days...\n")
    
    summary = cleanup(
        max_age_days=args.days,
        execute=args.execute,
        keep_scripts=args.keep_scripts,
        keep_topic_images=args.keep_images,
    )
    
    print("📁 Files to delete:")
    print(f"  Videos:       {summary['deleted']['videos']['count']} ({summary['deleted']['videos']['size_mb']:.1f} MB)")
    print(f"  Audio:        {summary['deleted']['audio']['count']} ({summary['deleted']['audio']['size_mb']:.1f} MB)")
    print(f"  Scripts:      {summary['deleted']['scripts']['count']} ({summary['deleted']['scripts']['size_mb']:.1f} MB)")
    print(f"  Topic Images: {summary['deleted']['topic_images']['count']} ({summary['deleted']['topic_images']['size_mb']:.1f} MB)")
    print(f"\n💾 Total space {'freed' if args.execute else 'to free'}: {summary['total_freed_mb']:.1f} MB")
    
    if not args.execute:
        print("\n⚠️  This was a dry run. Use --execute to actually delete files.")


if __name__ == "__main__":
    main()
