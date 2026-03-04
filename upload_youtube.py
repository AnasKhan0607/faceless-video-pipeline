#!/usr/bin/env python3
"""
YouTube Shorts Uploader
=======================
Upload videos to YouTube Shorts using Google API.

Setup (one-time):
1. Create OAuth credentials at console.cloud.google.com
2. Download client_secrets.json to this directory
3. Run: python upload_youtube.py --setup
4. Authorize in browser

Usage:
  python upload_youtube.py video.mp4 "Title" --description "Description" --tags "tech,coding"
"""

import argparse
import os
import sys
from pathlib import Path
import json

# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_CLIENT_SECRETS_FILE = Path(__file__).parent / "client_secrets.json"
DEFAULT_TOKEN_FILE = Path(__file__).parent / ".youtube_token.json"


def get_authenticated_service(credentials_file: str = None):
    """Get authenticated YouTube API service.
    
    Args:
        credentials_file: Path to OAuth credentials/token file (optional).
                         If provided, looks for token at same path with .token.json suffix.
                         Falls back to default locations if not specified.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ Google API libraries not installed. Run:")
        print("   pip install google-api-python-client google-auth-oauthlib")
        return None
    
    # Determine which files to use
    if credentials_file:
        cred_path = Path(credentials_file)
        # If the file is a token file (JSON with access_token), use it directly
        # Otherwise treat it as client_secrets and derive token path
        if cred_path.exists():
            try:
                data = json.loads(cred_path.read_text())
                if "access_token" in data or "token" in data:
                    # It's a token file
                    token_file = cred_path
                    client_secrets_file = DEFAULT_CLIENT_SECRETS_FILE
                else:
                    # It's a client_secrets file
                    client_secrets_file = cred_path
                    token_file = cred_path.parent / f".{cred_path.stem}_token.json"
            except:
                client_secrets_file = cred_path
                token_file = cred_path.parent / f".{cred_path.stem}_token.json"
        else:
            client_secrets_file = cred_path
            token_file = cred_path.parent / f".{cred_path.stem}_token.json"
    else:
        client_secrets_file = DEFAULT_CLIENT_SECRETS_FILE
        token_file = DEFAULT_TOKEN_FILE
    
    creds = None
    
    # Load existing token
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    
    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets_file.exists():
                print(f"❌ Client secrets not found: {client_secrets_file}")
                print("   Download from Google Cloud Console > APIs & Services > Credentials")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for future use
        token_file.write_text(creds.to_json())
    
    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] = None,
    category: str = "28",  # Science & Technology
    privacy: str = "public",
    credentials_file: str = None
) -> bool:
    """Upload a video to YouTube as a Short.
    
    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        tags: List of tags
        category: YouTube category ID (default: Science & Technology)
        privacy: Privacy setting (public, private, unlisted)
        credentials_file: Path to OAuth credentials file (optional, uses default if not specified)
    """
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False
    
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("❌ Google API not installed. Run: pip install google-api-python-client")
        return False
    
    youtube = get_authenticated_service(credentials_file)
    if not youtube:
        return False
    
    # Add #Shorts to title/description for YouTube to recognize it
    if "#Shorts" not in title and "#shorts" not in title.lower():
        title = f"{title} #Shorts"
    
    tags = tags or ["shorts", "tech", "coding", "programming", "learn"]
    if "shorts" not in [t.lower() for t in tags]:
        tags.append("Shorts")
    
    print(f"📤 Uploading to YouTube Shorts...")
    print(f"   Video: {video_path}")
    print(f"   Title: {title}")
    
    body = {
        "snippet": {
            "title": title[:100],  # YouTube limit
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True
    )
    
    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = request.execute()
        video_id = response["id"]
        
        print(f"✅ Uploaded successfully!")
        print(f"   URL: https://youtube.com/shorts/{video_id}")
        return True
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False


def setup_auth():
    """Interactive setup for YouTube authentication."""
    print("🔐 YouTube Authentication Setup")
    print("=" * 40)
    
    if not CLIENT_SECRETS_FILE.exists():
        print(f"❌ Missing: {CLIENT_SECRETS_FILE}")
        print("\nSetup steps:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a project (or select existing)")
        print("3. Enable YouTube Data API v3")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download JSON and save as client_secrets.json here")
        return
    
    print("A browser window will open. Authorize the app.\n")
    
    youtube = get_authenticated_service()
    if youtube:
        print("\n✅ Authentication successful!")
        print("   You can now upload videos with upload_youtube.py")


def main():
    parser = argparse.ArgumentParser(description="Upload videos to YouTube Shorts")
    parser.add_argument("video", nargs="?", help="Video file to upload")
    parser.add_argument("title", nargs="?", help="Video title")
    parser.add_argument("--description", default="", help="Video description")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--privacy", default="public", choices=["public", "private", "unlisted"])
    parser.add_argument("--setup", action="store_true", help="Run authentication setup")
    args = parser.parse_args()
    
    if args.setup:
        setup_auth()
        return
    
    if not args.video or not args.title:
        parser.print_help()
        print("\n💡 First time? Run: python upload_youtube.py --setup")
        return
    
    tags = args.tags.split(",") if args.tags else None
    success = upload_video(
        args.video,
        args.title,
        description=args.description,
        tags=tags,
        privacy=args.privacy
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
