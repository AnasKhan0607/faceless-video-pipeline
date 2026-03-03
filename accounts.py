"""
Account Manager for Multi-Account Video Pipeline
================================================
Handles loading, saving, and managing multiple accounts across platforms.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

BASE_DIR = Path(__file__).parent
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
CREDENTIALS_DIR = BASE_DIR / "credentials"


def load_accounts() -> dict:
    """Load all accounts from accounts.json"""
    if not ACCOUNTS_FILE.exists():
        return {"accounts": [], "settings": {}}
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)


def save_accounts(data: dict) -> None:
    """Save accounts to accounts.json"""
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_account(account_id: str) -> Optional[dict]:
    """Get a specific account by ID"""
    data = load_accounts()
    for account in data["accounts"]:
        if account["id"] == account_id:
            return account
    return None


def get_active_accounts() -> list:
    """Get all active accounts"""
    data = load_accounts()
    return [a for a in data["accounts"] if a.get("active", True)]


def get_accounts_for_platform(platform: str) -> list:
    """Get all accounts that have a specific platform enabled"""
    data = load_accounts()
    result = []
    for account in data["accounts"]:
        if account.get("active", True):
            platform_config = account.get("platforms", {}).get(platform, {})
            if platform_config.get("enabled", False):
                result.append(account)
    return result


def create_account(
    name: str,
    niche: str,
    platforms: dict,
    characters: list,
    backgrounds: list,
    schedule: dict,
    topics: Optional[list] = None,
) -> dict:
    """
    Create a new account.
    
    Args:
        name: Display name for the account
        niche: Content niche (tech, finance, gaming, etc.)
        platforms: Dict of platform configs {tiktok: {enabled: bool, ...}, ...}
        characters: List of character IDs to use
        backgrounds: List of background video names
        schedule: Schedule config {timezone, slots, days}
        topics: Optional list of initial topics
    
    Returns:
        The created account dict
    """
    # Generate account ID from name
    account_id = f"{niche}-{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    
    # Create topics file for this account
    topics_dir = BASE_DIR / "niches" / niche
    topics_dir.mkdir(parents=True, exist_ok=True)
    topics_file = f"niches/{niche}/topics_{account_id}.json"
    
    topics_data = {
        "niche": niche,
        "topics": [
            {"id": i + 1, "topic": t, "used": False}
            for i, t in enumerate(topics or [])
        ]
    }
    with open(BASE_DIR / topics_file, "w") as f:
        json.dump(topics_data, f, indent=2)
    
    # Create credentials directory for this account
    CREDENTIALS_DIR.mkdir(exist_ok=True)
    
    account = {
        "id": account_id,
        "name": name,
        "niche": niche,
        "platforms": platforms,
        "content": {
            "topics_file": topics_file,
            "characters": characters,
            "backgrounds": backgrounds,
        },
        "schedule": schedule,
        "active": True,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    
    # Add to accounts file
    data = load_accounts()
    data["accounts"].append(account)
    save_accounts(data)
    
    return account


def update_account(account_id: str, updates: dict) -> Optional[dict]:
    """Update an existing account"""
    data = load_accounts()
    for i, account in enumerate(data["accounts"]):
        if account["id"] == account_id:
            # Deep merge updates
            for key, value in updates.items():
                if isinstance(value, dict) and isinstance(account.get(key), dict):
                    account[key].update(value)
                else:
                    account[key] = value
            account["updated_at"] = datetime.utcnow().isoformat() + "Z"
            data["accounts"][i] = account
            save_accounts(data)
            return account
    return None


def delete_account(account_id: str, delete_files: bool = False) -> bool:
    """Delete an account"""
    data = load_accounts()
    for i, account in enumerate(data["accounts"]):
        if account["id"] == account_id:
            if delete_files:
                # Delete topics file
                topics_file = BASE_DIR / account["content"]["topics_file"]
                if topics_file.exists():
                    topics_file.unlink()
                # Delete credentials
                for platform, config in account.get("platforms", {}).items():
                    cred_file = BASE_DIR / config.get("credentials", "")
                    if cred_file.exists():
                        cred_file.unlink()
                # Delete output directory
                out_dir = BASE_DIR / "out" / account_id
                if out_dir.exists():
                    shutil.rmtree(out_dir)
            
            data["accounts"].pop(i)
            save_accounts(data)
            return True
    return False


def toggle_account(account_id: str) -> Optional[bool]:
    """Toggle account active status, returns new status"""
    data = load_accounts()
    for i, account in enumerate(data["accounts"]):
        if account["id"] == account_id:
            account["active"] = not account.get("active", True)
            data["accounts"][i] = account
            save_accounts(data)
            return account["active"]
    return None


def get_credentials_path(account_id: str, platform: str) -> Optional[Path]:
    """Get the full path to credentials file for an account/platform"""
    account = get_account(account_id)
    if not account:
        return None
    platform_config = account.get("platforms", {}).get(platform, {})
    cred_path = platform_config.get("credentials")
    if cred_path:
        return BASE_DIR / cred_path
    return None


def get_topics_for_account(account_id: str) -> list:
    """Get unused topics for an account"""
    account = get_account(account_id)
    if not account:
        return []
    
    topics_file = BASE_DIR / account["content"]["topics_file"]
    if not topics_file.exists():
        return []
    
    with open(topics_file) as f:
        data = json.load(f)
    
    return [t for t in data.get("topics", []) if not t.get("used", False)]


def mark_topic_used(account_id: str, topic_id: int) -> bool:
    """Mark a topic as used for an account"""
    account = get_account(account_id)
    if not account:
        return False
    
    topics_file = BASE_DIR / account["content"]["topics_file"]
    if not topics_file.exists():
        return False
    
    with open(topics_file) as f:
        data = json.load(f)
    
    for topic in data.get("topics", []):
        if topic["id"] == topic_id:
            topic["used"] = True
            topic["used_at"] = datetime.utcnow().isoformat()
            break
    
    with open(topics_file, "w") as f:
        json.dump(data, f, indent=2)
    
    return True


def get_schedule_for_time(hour: int, minute: int, day: str) -> list:
    """
    Get accounts that should post at a specific time.
    Returns list of (account, platforms) tuples.
    """
    time_str = f"{hour:02d}:{minute:02d}"
    results = []
    
    for account in get_active_accounts():
        schedule = account.get("schedule", {})
        days = schedule.get("days", [])
        
        # Check if today is a scheduled day
        if day.lower()[:3] not in [d.lower()[:3] for d in days]:
            continue
        
        # Check time slots
        for slot in schedule.get("slots", []):
            if slot.get("time") == time_str:
                results.append({
                    "account": account,
                    "platforms": slot.get("platforms", [])
                })
    
    return results


def migrate_existing_credentials():
    """
    Migrate existing credential files to the new structure.
    Run once during initial setup.
    """
    CREDENTIALS_DIR.mkdir(exist_ok=True)
    
    migrations = [
        ("tiktok_cookies.json", "credentials/tiktok_tech.json"),
        ("instagram_session.json", "credentials/instagram_tech.json"),
        ("client_secrets.json", "credentials/youtube_tech.json"),
    ]
    
    for old_name, new_name in migrations:
        old_path = BASE_DIR / old_name
        new_path = BASE_DIR / new_name
        if old_path.exists() and not new_path.exists():
            shutil.copy2(old_path, new_path)
            print(f"Migrated {old_name} -> {new_name}")


if __name__ == "__main__":
    # Test/demo
    print("Current accounts:")
    for acc in load_accounts().get("accounts", []):
        print(f"  - {acc['id']}: {acc['name']} ({acc['niche']})")
    
    print("\nActive accounts for TikTok:")
    for acc in get_accounts_for_platform("tiktok"):
        print(f"  - {acc['id']}")
