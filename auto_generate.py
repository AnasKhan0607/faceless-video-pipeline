#!/usr/bin/env python3
"""
Auto Video Generator
====================
Fully automated video generation:
1. Pick next unused topic
2. Generate script with AI
3. Render video
4. Mark topic as used
5. (Optional) Upload to platforms

Usage:
  python auto_generate.py                        # Generate one video (default account)
  python auto_generate.py --account tech-main    # Generate for specific account
  python auto_generate.py --count 3              # Generate 3 videos
  python auto_generate.py --topic "What is X"    # Specific topic
  python auto_generate.py --upload               # Generate and upload
"""

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import httpx
import os

# Load .env file if present
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Import account manager
from accounts import (
    get_account, 
    load_accounts, 
    get_topics_for_account,
    mark_topic_used as account_mark_topic_used,
    get_credentials_path
)

# Paths
PIPELINE_DIR = Path(__file__).parent
NICHES_DIR = PIPELINE_DIR / "niches"
SCRIPTS_DIR = PIPELINE_DIR / "scripts"
OUT_DIR = PIPELINE_DIR / "out"
QUEUE_DIR = PIPELINE_DIR / "queue"

# Config
DEFAULT_NICHE = "tech"
DEFAULT_DUO = "peter_stewie"
DEFAULT_BACKGROUND = "subway_surfers"

# API Keys (from environment or config)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


def load_topics(niche: str) -> dict:
    """Load topics for a niche."""
    topics_file = NICHES_DIR / niche / "topics.json"
    if not topics_file.exists():
        raise FileNotFoundError(f"Topics file not found: {topics_file}")
    return json.loads(topics_file.read_text())


def save_topics(niche: str, data: dict):
    """Save topics back to file."""
    topics_file = NICHES_DIR / niche / "topics.json"
    topics_file.write_text(json.dumps(data, indent=2))


def get_next_topic(niche: str) -> dict | None:
    """Get next unused topic."""
    data = load_topics(niche)
    for topic in data["topics"]:
        if not topic.get("used", False):
            return topic
    return None


def mark_topic_used(niche: str, topic_id: int):
    """Mark a topic as used."""
    data = load_topics(niche)
    for topic in data["topics"]:
        if topic["id"] == topic_id:
            topic["used"] = True
            topic["used_at"] = datetime.now().isoformat()
            break
    save_topics(niche, data)


def generate_script_with_ai(topic: str, duo: str = DEFAULT_DUO) -> dict:
    """Generate a script using OpenAI API."""
    
    # Load character config for context
    char_config_path = PIPELINE_DIR / "characters" / duo / "config.json"
    char_config = json.loads(char_config_path.read_text()) if char_config_path.exists() else {}
    
    char1 = char_config.get("char1", {}).get("name", "peter")
    char2 = char_config.get("char2", {}).get("name", "stewie")
    char1_display = char_config.get("char1", {}).get("display_name", "Peter")
    char2_display = char_config.get("char2", {}).get("display_name", "Stewie")
    
    prompt = f"""Generate a TikTok script where {char1_display} and {char2_display} do a TECHNICAL DEEP DIVE on "{topic}".

CRITICAL REQUIREMENTS:
- This is for SOFTWARE ENGINEERS and TECH ENTHUSIASTS - don't dumb it down
- Use REAL technical terms: algorithms, data structures, protocols, system design concepts
- Explain the ACTUAL implementation details - how it works under the hood
- Include specific numbers, metrics, or technical facts when relevant
- NO surface-level fluff - every line should teach something specific
- 12-16 lines of dialogue total
- Each line should be 1-2 sentences max (under 15 words per line)
- Keep total runtime under 60 seconds when spoken

STRUCTURE:
1. Hook with a surprising technical fact (1-2 lines)
2. The core technical concept explained precisely (3-4 lines)
3. Implementation details / how it actually works (4-5 lines)
4. Edge cases, tradeoffs, or why it's designed this way (2-3 lines)
5. Quick wrap-up or mind-blowing conclusion (1-2 lines)

EXAMPLE DEPTH LEVEL:
- BAD: "It's like a recommendation system that shows you videos"
- GOOD: "It uses collaborative filtering combined with a deep neural network that processes watch time, engagement signals, and content embeddings"

CHARACTER DYNAMICS:
- {char1_display}: Asks pointed technical questions, wants specifics
- {char2_display}: Explains with technical precision, uses exact terminology
- Keep some humor but PRIORITIZE technical depth over jokes

Output ONLY valid JSON (no markdown, no explanation):
{{
  "title": "SHORT_CATCHY_TITLE",
  "dialogue": [
    {{"id": 1, "character": "{char1}", "line": "...", "pause_after_ms": 400}},
    {{"id": 2, "character": "{char2}", "line": "...", "pause_after_ms": 300}},
    ...
  ]
}}

Use pause_after_ms of 300-500 between lines. Alternate characters naturally."""

    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set. Set it in environment.")
        print("   export OPENAI_API_KEY='sk-...'")
        sys.exit(1)
    
    print(f"🤖 Generating script for: {topic}")
    
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a senior software engineer creating technical explainer content for developers. Be precise, use real terminology, and go deep. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.9,
            "max_tokens": 1000
        },
        timeout=60
    )
    
    if response.status_code != 200:
        print(f"❌ OpenAI API error: {response.text}")
        sys.exit(1)
    
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    
    # Clean up response (remove markdown if present)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    try:
        script_data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse AI response as JSON: {e}")
        print(f"Response was: {content[:500]}")
        sys.exit(1)
    
    return script_data


def generate_topic_image(topic: str, episode_id: str) -> Path | None:
    """Generate a simple topic image with text overlay using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("⚠️ Pillow not installed, skipping topic image")
        return None
    
    topics_dir = PIPELINE_DIR / "assets" / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = topics_dir / f"{episode_id}.png"
    
    # Clean topic text for display
    display_text = topic.replace("What is ", "").replace("What are ", "").replace("?", "").strip().upper()
    
    # Create image
    width, height = 800, 400
    bg_color = (26, 26, 46)  # Dark blue/purple
    text_color = (255, 255, 255)  # White
    accent_color = (99, 102, 241)  # Indigo accent
    
    img = Image.new('RGBA', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default
    font_size = 64
    try:
        # Try common macOS fonts
        for font_name in ["/System/Library/Fonts/Helvetica.ttc", 
                          "/System/Library/Fonts/SFNSDisplay.ttf",
                          "/Library/Fonts/Arial Bold.ttf"]:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except:
                continue
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Handle long text - wrap if needed
    if len(display_text) > 20:
        words = display_text.split()
        mid = len(words) // 2
        display_text = " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
    
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw accent rectangle behind text
    padding = 30
    draw.rounded_rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        radius=15,
        fill=accent_color
    )
    
    # Draw text
    draw.text((x, y), display_text, font=font, fill=text_color, align="center")
    
    # Save
    img.save(output_path, "PNG")
    print(f"🖼️ Generated topic image: {output_path.name}")
    return output_path


def create_full_script(topic: str, topic_id: int, duo: str, background: str) -> Path:
    """Create a full script file ready for the pipeline."""
    
    # Generate dialogue with AI
    ai_script = generate_script_with_ai(topic, duo)
    
    # Create episode ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    episode_id = f"ep_{topic_id:03d}_{timestamp}"
    
    # Generate topic image
    topic_image = generate_topic_image(topic, episode_id)
    
    # Build full script
    full_script = {
        "episode": episode_id,
        "title": ai_script.get("title", topic),
        "topic": topic,
        "duo": duo,
        "background": background,
        "dialogue": ai_script["dialogue"],
        "generated_at": datetime.now().isoformat()
    }
    
    # Add topic image if generated
    if topic_image:
        full_script["topic_image"] = str(topic_image)
    
    # Save script
    script_path = SCRIPTS_DIR / f"{episode_id}.json"
    script_path.write_text(json.dumps(full_script, indent=2))
    print(f"📝 Script saved: {script_path}")
    
    return script_path


def render_video(script_path: Path) -> Path | None:
    """Render video using pipeline.py."""
    print(f"🎬 Rendering video...")
    
    # Use pipeline_v2 if it exists, otherwise pipeline
    pipeline_script = PIPELINE_DIR / "pipeline_v2.py"
    if not pipeline_script.exists():
        pipeline_script = PIPELINE_DIR / "pipeline.py"
    
    result = subprocess.run(
        [sys.executable, str(pipeline_script), "--script", str(script_path)],
        cwd=PIPELINE_DIR,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Render failed:")
        print(result.stderr)
        return None
    
    print(result.stdout)
    
    # Find output file
    script_data = json.loads(script_path.read_text())
    episode_id = script_data["episode"]
    output_path = OUT_DIR / f"{episode_id}_final.mp4"
    
    if output_path.exists():
        print(f"✅ Video rendered: {output_path}")
        return output_path
    
    # Try to find any matching output
    for f in OUT_DIR.glob(f"{episode_id}*.mp4"):
        print(f"✅ Video rendered: {f}")
        return f
    
    print("⚠️ Video file not found after render")
    return None


def upload_to_tiktok(video_path: Path, title: str, topic: str, account_id: str = None) -> bool:
    """Upload video to TikTok."""
    try:
        from upload_tiktok import upload_video
        
        # Get account-specific credentials if account provided
        credentials_path = None
        niche_tags = ["tech", "coding", "programming"]
        
        if account_id:
            cred_path = get_credentials_path(account_id, "tiktok")
            if cred_path and cred_path.exists():
                credentials_path = str(cred_path)
            account = get_account(account_id)
            if account:
                niche_tags = [account["niche"]] + niche_tags[:2]
        
        caption = f"{title} 🔥 #{niche_tags[0]} #shorts #learn #viral"
        return upload_video(str(video_path), caption, niche_tags + ["shorts"], cookies_file=credentials_path)
    except ImportError:
        print("⚠️ TikTok uploader not available")
        return False
    except Exception as e:
        print(f"❌ TikTok upload failed: {e}")
        return False


def upload_to_youtube(video_path: Path, title: str, topic: str, account_id: str = None) -> bool:
    """Upload video to YouTube Shorts."""
    try:
        from upload_youtube import upload_video
        
        # Get account-specific credentials if account provided
        credentials_path = None
        niche = "Tech"
        
        if account_id:
            cred_path = get_credentials_path(account_id, "youtube")
            if cred_path and cred_path.exists():
                credentials_path = str(cred_path)
            account = get_account(account_id)
            if account:
                niche = account["niche"].title()
        
        description = f"Explaining {topic} in under 60 seconds!\n\n#Shorts #{niche} #Learn #Explained"
        return upload_video(
            str(video_path),
            title,
            description=description,
            tags=["shorts", niche.lower(), "learn", "explained", "educational"],
            credentials_file=credentials_path
        )
    except ImportError:
        print("⚠️ YouTube uploader not available")
        return False
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        return False


def upload_to_instagram(video_path: Path, title: str, topic: str, account_id: str = None) -> bool:
    """Upload video to Instagram Reels."""
    try:
        from upload_instagram import upload_reel
        
        # Get account-specific credentials if account provided
        credentials_path = None
        niche = "tech"
        
        if account_id:
            cred_path = get_credentials_path(account_id, "instagram")
            if cred_path and cred_path.exists():
                credentials_path = str(cred_path)
            account = get_account(account_id)
            if account:
                niche = account["niche"]
        
        caption = f"{title} 🔥\n\n#{niche} #learn #reels #educational #viral"
        return upload_reel(str(video_path), caption, session_file=credentials_path)
    except ImportError:
        print("⚠️ Instagram uploader not available")
        return False
    except Exception as e:
        print(f"❌ Instagram upload failed: {e}")
        return False


def generate_one_video(
    niche: str = DEFAULT_NICHE,
    duo: str = DEFAULT_DUO,
    background: str = DEFAULT_BACKGROUND,
    specific_topic: str = None,
    upload: bool = False,
    account_id: str = None,
    platforms: list = None
) -> bool:
    """Generate one video end-to-end.
    
    Args:
        niche: Topic niche (overridden by account if provided)
        duo: Character duo (overridden by account if provided)
        background: Background video (overridden by account if provided)
        specific_topic: Specific topic to use (bypasses topic list)
        upload: Whether to upload after generating
        account_id: Account ID to use (loads settings from accounts.json)
        platforms: List of platforms to upload to (default: all enabled for account)
    """
    
    # Load account settings if account_id provided
    if account_id:
        account = get_account(account_id)
        if not account:
            print(f"❌ Account not found: {account_id}")
            return False
        
        print(f"📋 Using account: {account['name']} ({account['niche']})")
        niche = account["niche"]
        
        # Pick random character combo from account's list
        chars = account.get("content", {}).get("characters", ["peter", "stewie"])
        if len(chars) >= 2:
            char1, char2 = random.sample(chars, 2)
            duo = f"{char1}_{char2}"
        
        # Pick random background from account's list
        backgrounds = account.get("content", {}).get("backgrounds", [DEFAULT_BACKGROUND])
        background = random.choice(backgrounds)
        
        # Get enabled platforms if not specified
        if platforms is None and upload:
            platforms = [
                p for p, cfg in account.get("platforms", {}).items()
                if cfg.get("enabled", False)
            ]
    
    # Get topic
    if specific_topic:
        topic = specific_topic
        topic_id = 0
    elif account_id:
        # Use account's topic list
        available_topics = get_topics_for_account(account_id)
        if not available_topics:
            print(f"❌ No unused topics left for account {account_id}!")
            return False
        topic_data = available_topics[0]
        topic = topic_data["topic"]
        topic_id = topic_data["id"]
    else:
        topic_data = get_next_topic(niche)
        if not topic_data:
            print(f"❌ No unused topics left in {niche}!")
            return False
        topic = topic_data["topic"]
        topic_id = topic_data["id"]
    
    print(f"\n{'='*50}")
    print(f"🎯 Topic: {topic}")
    print(f"👥 Characters: {duo}")
    print(f"🎮 Background: {background}")
    if account_id:
        print(f"👤 Account: {account_id}")
    print(f"{'='*50}\n")
    
    # Generate script
    script_path = create_full_script(topic, topic_id, duo, background)
    
    # Render video
    video_path = render_video(script_path)
    
    if video_path:
        # Mark topic as used
        if topic_id > 0:
            if account_id:
                account_mark_topic_used(account_id, topic_id)
            else:
                mark_topic_used(niche, topic_id)
            print(f"✓ Marked topic {topic_id} as used")
        
        # Upload if requested
        if upload:
            script_data = json.loads(script_path.read_text())
            title = script_data.get("title", topic)
            print("\n📤 Uploading to platforms...")
            
            platforms_to_upload = platforms or ["tiktok", "youtube", "instagram"]
            
            if "tiktok" in platforms_to_upload:
                upload_to_tiktok(video_path, title, topic, account_id)
            if "youtube" in platforms_to_upload:
                upload_to_youtube(video_path, title, topic, account_id)
            if "instagram" in platforms_to_upload:
                upload_to_instagram(video_path, title, topic, account_id)
        
        return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Auto-generate TikTok videos")
    parser.add_argument("--account", help="Account ID from accounts.json (recommended)")
    parser.add_argument("--count", type=int, default=1, help="Number of videos to generate")
    parser.add_argument("--niche", default=DEFAULT_NICHE, help="Topic niche (default: tech)")
    parser.add_argument("--duo", default=DEFAULT_DUO, help="Character duo (default: peter_stewie)")
    parser.add_argument("--background", default=DEFAULT_BACKGROUND, help="Background video")
    parser.add_argument("--topic", help="Specific topic (bypasses topic list)")
    parser.add_argument("--upload", action="store_true", help="Upload after generating")
    parser.add_argument("--platforms", nargs="+", help="Platforms to upload to (tiktok youtube instagram)")
    parser.add_argument("--dry-run", action="store_true", help="Generate script only, no render")
    parser.add_argument("--list-accounts", action="store_true", help="List available accounts")
    args = parser.parse_args()
    
    # List accounts if requested
    if args.list_accounts:
        data = load_accounts()
        print("📋 Available accounts:")
        for acc in data.get("accounts", []):
            status = "✅" if acc.get("active", True) else "⏸️"
            platforms = ", ".join([
                p for p, cfg in acc.get("platforms", {}).items() 
                if cfg.get("enabled", False)
            ])
            print(f"  {status} {acc['id']}: {acc['name']} ({acc['niche']}) -> {platforms}")
        return
    
    # If no account specified, try to use default
    account_id = args.account
    if not account_id:
        data = load_accounts()
        default_account = data.get("settings", {}).get("default_account")
        if default_account and get_account(default_account):
            account_id = default_account
            print(f"ℹ️ Using default account: {account_id}")
    
    print("🚀 Auto Video Generator")
    print(f"   Generating {args.count} video(s)...\n")
    
    success = 0
    for i in range(args.count):
        if args.count > 1:
            print(f"\n📹 Video {i+1}/{args.count}")
        
        if args.dry_run:
            if account_id:
                topics = get_topics_for_account(account_id)
                topic_data = topics[0] if topics else None
            else:
                topic_data = get_next_topic(args.niche)
            
            if topic_data:
                print(f"Would generate: {topic_data['topic']}")
                script_path = create_full_script(
                    topic_data["topic"], 
                    topic_data["id"],
                    args.duo, 
                    args.background
                )
                print(f"Script created (dry run): {script_path}")
                success += 1
        else:
            if generate_one_video(
                niche=args.niche,
                duo=args.duo,
                background=args.background,
                specific_topic=args.topic if i == 0 else None,
                upload=args.upload,
                account_id=account_id,
                platforms=args.platforms
            ):
                success += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Generated {success}/{args.count} videos")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
