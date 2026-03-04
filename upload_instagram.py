#!/usr/bin/env python3
"""
Instagram Reels Uploader
========================
Upload videos to Instagram Reels using instagrapi.

Setup:
  python upload_instagram.py --setup

Usage:
  python upload_instagram.py video.mp4 "Caption here"
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_SESSION_FILE = Path(__file__).parent / "instagram_session.json"


def login_instagram(username: str = None, password: str = None, session_file: str = None):
    """Login to Instagram and save session.
    
    Args:
        username: Instagram username (for fresh login)
        password: Instagram password (for fresh login)
        session_file: Path to session file (optional, uses default if not specified)
    """
    from instagrapi import Client
    
    cl = Client()
    
    # Determine which session file to use
    sess_path = Path(session_file) if session_file else DEFAULT_SESSION_FILE
    
    # Try to load existing session
    if sess_path.exists() and not username:
        try:
            cl.load_settings(sess_path)
            cl.login_by_sessionid(cl.settings.get('authorization_data', {}).get('sessionid', ''))
            print(f"✅ Logged in from saved session ({sess_path.name})")
            return cl
        except Exception as e:
            print(f"⚠️ Session expired: {e}")
    
    # Fresh login
    if not username or not password:
        raise ValueError("Username and password required for fresh login")
    
    print(f"🔐 Logging in as {username}...")
    cl.login(username, password)
    cl.dump_settings(sess_path)
    print("✅ Logged in and session saved")
    return cl


def upload_reel(video_path: str, caption: str, thumbnail_path: str = None, session_file: str = None) -> bool:
    """Upload a video to Instagram Reels.
    
    Args:
        video_path: Path to the video file
        caption: Reel caption
        thumbnail_path: Path to custom thumbnail (optional)
        session_file: Path to session file (optional, uses default if not specified)
    """
    from instagrapi import Client
    from instagrapi.types import StorySticker
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False
    
    # Determine which session file to use
    sess_path = Path(session_file) if session_file else DEFAULT_SESSION_FILE
    
    print(f"📤 Uploading to Instagram Reels...")
    print(f"   Video: {video_path}")
    print(f"   Caption: {caption[:60]}...")
    if session_file:
        print(f"   Session: {sess_path.name}")
    
    try:
        cl = Client()
        
        # Load session
        if not sess_path.exists():
            print(f"❌ Not logged in. Session file not found: {sess_path}")
            print("   Run: python upload_instagram.py --setup")
            return False
        
        cl.load_settings(sess_path)
        cl.login_by_sessionid(cl.settings.get('authorization_data', {}).get('sessionid', ''))
        
        # Upload as reel
        media = cl.clip_upload(
            path=str(video_path),
            caption=caption,
            thumbnail=str(thumbnail_path) if thumbnail_path else None,
        )
        
        print(f"✅ Uploaded successfully!")
        print(f"   URL: https://www.instagram.com/reel/{media.code}/")
        return True
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        
        # Check if it's a login issue
        if "login_required" in str(e).lower() or "challenge" in str(e).lower():
            print("⚠️ Session expired or challenge required. Run: python upload_instagram.py --setup")
        
        return False


def setup_auth():
    """Interactive setup for Instagram authentication."""
    from instagrapi import Client
    
    print("🔐 Instagram Login Setup")
    print("=" * 40)
    print()
    print("⚠️  Note: Use an account you don't mind risking.")
    print("    Instagram may flag automated logins.")
    print()
    
    username = input("Instagram username: ").strip()
    password = input("Instagram password: ").strip()
    
    if not username or not password:
        print("❌ Username and password required")
        return
    
    try:
        cl = Client()
        cl.login(username, password)
        cl.dump_settings(DEFAULT_SESSION_FILE)
        print(f"\n✅ Logged in as @{username}")
        print(f"   Session saved to: {DEFAULT_SESSION_FILE}")
        print("   You can now upload reels!")
    except Exception as e:
        print(f"\n❌ Login failed: {e}")
        if "challenge" in str(e).lower():
            print("⚠️ Instagram is requesting verification.")
            print("   Try logging in on the app first, then retry.")


def main():
    parser = argparse.ArgumentParser(description="Upload videos to Instagram Reels")
    parser.add_argument("video", nargs="?", help="Video file to upload")
    parser.add_argument("caption", nargs="?", help="Video caption")
    parser.add_argument("--thumbnail", help="Custom thumbnail image")
    parser.add_argument("--setup", action="store_true", help="Interactive login setup")
    args = parser.parse_args()
    
    if args.setup:
        setup_auth()
        return
    
    if not args.video or not args.caption:
        parser.print_help()
        print("\n💡 First time? Run: python upload_instagram.py --setup")
        return
    
    success = upload_reel(args.video, args.caption, args.thumbnail)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
