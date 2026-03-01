#!/usr/bin/env python3
"""
TikTok Uploader (Custom with Joyride handling)
==============================================
Upload videos to TikTok with automatic tour/popup dismissal.

Setup:
1. Get your TikTok sessionid from browser cookies
2. Create tiktok_cookies.json with your session

Usage:
  python upload_tiktok.py video.mp4 "Caption here"
  python upload_tiktok.py video.mp4 "Caption" --tags "tech,coding"
"""

import argparse
import json
import sys
import time
from pathlib import Path

COOKIES_FILE = Path(__file__).parent / "tiktok_cookies.json"


def get_cookies_list():
    """Load cookies from JSON file."""
    if not COOKIES_FILE.exists():
        return None
    
    try:
        data = json.loads(COOKIES_FILE.read_text())
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "sessionid" in data:
            return [{"name": "sessionid", "value": data["sessionid"], "domain": ".tiktok.com"}]
        return None
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return None


def dismiss_joyride(page, max_attempts=10):
    """Try to dismiss any Joyride/tutorial overlays."""
    for i in range(max_attempts):
        try:
            # Check for react-joyride overlay (the actual class used by TikTok)
            joyride_selectors = [
                '.react-joyride__overlay',
                '[class*="joyride"]',
                '[data-test-id="overlay"]',
                '.joyride-overlay',
            ]
            
            dismissed = False
            for selector in joyride_selectors:
                joyride = page.locator(selector)
                if joyride.count() > 0:
                    print(f"  🚫 Found overlay: {selector} (attempt {i+1})...")
                    # Use JavaScript to remove the overlay entirely
                    page.evaluate(f'''
                        document.querySelectorAll('{selector}').forEach(el => el.remove());
                        document.querySelectorAll('.react-joyride').forEach(el => el.remove());
                        document.querySelectorAll('[class*="joyride"]').forEach(el => el.remove());
                    ''')
                    dismissed = True
                    time.sleep(0.3)
            
            # Also try clicking any "Skip", "Got it", "Close", "X" buttons
            skip_selectors = [
                'button:has-text("Skip")', 
                'button:has-text("Got it")',
                'button:has-text("Got It")',
                'button:has-text("Next")', 
                'button:has-text("Close")',
                '[aria-label="Close"]',
                '[class*="close"]', 
                '[class*="skip"]',
                '[class*="CloseButton"]',
            ]
            
            for selector in skip_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0:
                        btn.first.click(timeout=1000, force=True)
                        dismissed = True
                        time.sleep(0.3)
                except:
                    pass
            
            if not dismissed:
                # No overlays found, we're good
                return True
                    
        except Exception as e:
            pass
        
        # Final check - if no joyride elements exist, we're done
        try:
            if page.locator('.react-joyride__overlay').count() == 0 and \
               page.locator('[class*="joyride"]').count() == 0:
                return True
        except:
            pass
            
    return False


def upload_video(video_path: str, caption: str, tags: list[str] = None) -> bool:
    """Upload a video to TikTok with Joyride handling."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ playwright not installed. Run: pip install playwright && playwright install")
        return False
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False
    
    cookies = get_cookies_list()
    if not cookies:
        print("❌ No cookies found. Run: python upload_tiktok.py --setup")
        return False
    
    # Build caption with tags
    full_caption = caption
    if tags:
        hashtags = " ".join(f"#{tag.strip('#')}" for tag in tags)
        full_caption = f"{caption} {hashtags}"
    
    print(f"📤 Uploading to TikTok...")
    print(f"   Video: {video_path}")
    print(f"   Caption: {full_caption[:60]}...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # headless breaks TikTok
            context = browser.new_context()
            
            # Add cookies
            tiktok_cookies = []
            for c in cookies:
                tiktok_cookies.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".tiktok.com"),
                    "path": c.get("path", "/"),
                })
            context.add_cookies(tiktok_cookies)
            
            page = context.new_page()
            
            # Debug screenshots folder
            debug_dir = Path(__file__).parent / "debug_screenshots"
            debug_dir.mkdir(exist_ok=True)
            
            # Go to upload page (with retry)
            print("  → Navigating to upload page...")
            for attempt in range(3):
                try:
                    page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"  ⚠️ Retry {attempt+1}...")
                        time.sleep(2)
                    else:
                        raise e
            
            # Screenshot after navigation
            page.screenshot(path=str(debug_dir / "01_after_nav.png"))
            print(f"  📸 Screenshot: {debug_dir / '01_after_nav.png'}")
            
            # Dismiss any cookie banners
            try:
                cookie_btn = page.locator('button:has-text("Accept")')
                if cookie_btn.count() > 0:
                    cookie_btn.first.click(timeout=2000)
            except:
                pass
            
            # Dismiss Joyride overlays
            dismiss_joyride(page)
            
            # Upload file
            print("  → Uploading video file...")
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(str(video_path.absolute()))
            
            # Wait for upload to process
            time.sleep(5)
            page.screenshot(path=str(debug_dir / "02_after_upload.png"))
            print(f"  📸 Screenshot: {debug_dir / '02_after_upload.png'}")
            
            # Dismiss any new overlays that appeared
            dismiss_joyride(page)
            
            # Set caption
            print("  → Setting caption...")
            caption_input = page.locator('[contenteditable="true"]').first
            
            # Try to clear and type caption
            try:
                caption_input.click(timeout=5000)
                time.sleep(0.5)
                dismiss_joyride(page)  # Dismiss if overlay appeared
                caption_input.click(timeout=5000)
                page.keyboard.press("Control+a")
                page.keyboard.type(full_caption[:2200])  # TikTok limit
            except Exception as e:
                print(f"  ⚠️ Caption setting issue: {e}")
            
            # Wait for video to finish uploading (look for green checkmark "Uploaded")
            print("  → Waiting for video upload to complete...")
            for wait_attempt in range(120):  # Max 2 minutes
                time.sleep(1)
                try:
                    # Look for the green "Uploaded" text that appears when complete
                    uploaded_indicator = page.locator('text="Uploaded"')
                    if uploaded_indicator.count() > 0:
                        print("  ✓ Upload complete!")
                        break
                    
                    # Also check for checkmark icon near upload status
                    if page.locator('[class*="success"], [class*="complete"], [class*="check"]').count() > 0:
                        content = page.content()
                        if "Uploaded" in content:
                            print("  ✓ Upload complete (checkmark found)!")
                            break
                except:
                    pass
                if wait_attempt % 10 == 0:
                    print(f"  ... still uploading ({wait_attempt}s)")
            
            # Extra wait for processing after upload
            time.sleep(5)
            
            page.screenshot(path=str(debug_dir / "03_after_caption.png"))
            print(f"  📸 Screenshot: {debug_dir / '03_after_caption.png'}")
            
            # Dismiss any overlays before clicking post
            dismiss_joyride(page)
            
            # Click post button
            print("  → Preparing to post...")
            
            # First, click somewhere neutral to dismiss any dropdowns
            try:
                page.locator('body').click(position={"x": 10, "y": 10})
                time.sleep(0.5)
            except:
                pass
            
            # Wait for content checks to complete (TikTok runs copyright/content checks)
            print("  → Waiting for content checks...")
            for check_wait in range(60):  # Max 60 seconds for checks
                time.sleep(1)
                try:
                    page_content = page.content()
                    # Look for "No issues found" which indicates checks passed
                    if "No issues found" in page_content or "no issues found" in page_content.lower():
                        checks_passed = page_content.lower().count("no issues found")
                        if checks_passed >= 2:  # Both music and content checks
                            print(f"  ✓ Content checks passed! ({checks_passed} checks)")
                            break
                    # Also check for green checkmarks
                    if page.locator('text="No issues found"').count() >= 2:
                        print("  ✓ Content checks passed!")
                        break
                except:
                    pass
                if check_wait % 10 == 0 and check_wait > 0:
                    print(f"  ... waiting for checks ({check_wait}s)")
            
            # Extra buffer after checks pass (TikTok needs time to fully process)
            print("  → Extra buffer for TikTok processing...")
            time.sleep(5)
            
            # Take screenshot before clicking Post
            page.screenshot(path=str(debug_dir / "03b_before_post.png"))
            print(f"  📸 Screenshot: {debug_dir / '03b_before_post.png'}")
            
            print("  → Clicking post button...")
            
            # Find the Post button first
            post_btn = None
            for selector in [
                'button:has-text("Post")',
                '[data-e2e="post-button"]',
                'button[class*="TUXButton"][class*="primary"]',
            ]:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0:
                        post_btn = btn
                        break
                except:
                    continue
            
            if not post_btn:
                print("  ⚠️ Could not find Post button!")
            else:
                # Scroll button into view and click
                try:
                    post_btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    
                    # Check if button is enabled
                    is_disabled = post_btn.get_attribute('disabled')
                    btn_class = post_btn.get_attribute('class') or ''
                    print(f"  Button state: disabled={is_disabled}, class={btn_class[:50]}...")
                    
                    post_btn.click(timeout=10000)
                    print(f"  ✓ Clicked Post button")
                    post_clicked = True
                except Exception as e:
                    print(f"  Post button click failed: {e}")
            
            # Find and click the Post button (try multiple selectors)
            post_clicked = False
            for selector in [
                'button:has-text("Post")',
                '[data-e2e="post-button"]',
                'button[class*="TUXButton"][class*="primary"]',
                'button[class*="post" i]',
                'button[class*="Post" i]',
            ]:
                try:
                    post_btn = page.locator(selector).first
                    if post_btn.count() > 0:
                        # Scroll the button into view
                        post_btn.scroll_into_view_if_needed()
                        time.sleep(0.3)
                        
                        # Check if button is enabled
                        is_disabled = post_btn.get_attribute('disabled')
                        btn_class = post_btn.get_attribute('class') or ''
                        print(f"  Button state: disabled={is_disabled}, class={btn_class[:50]}...")
                        
                        if post_btn.is_visible() and not is_disabled:
                            post_btn.click(timeout=5000)
                            post_clicked = True
                            print(f"  ✓ Clicked: {selector}")
                            break
                except Exception as e:
                    print(f"  Selector {selector} failed: {e}")
                    continue
            
            if not post_clicked:
                # Fallback to JavaScript - find and click the Post button
                print("  ⚠️ Trying JavaScript click...")
                page.evaluate('''
                    // Find all buttons
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        if (btn.textContent.trim().toLowerCase() === 'post') {
                            console.log('Found Post button:', btn);
                            btn.scrollIntoView();
                            btn.click();
                            break;
                        }
                    }
                ''')
            
            # Wait for any confirmation popup to appear
            time.sleep(3)
            
            # Immediately try to handle any popup that appeared after clicking Post
            print("  → Checking for confirmation popups...")
            try:
                # Use JavaScript to find and click any Continue/confirm button in modals
                page.evaluate('''
                    // Find modal/popup containers
                    const modals = document.querySelectorAll('[class*="Modal"], [class*="modal"], [class*="Dialog"], [class*="dialog"], [class*="TUXModal"]');
                    for (const modal of modals) {
                        // Look for buttons in modals
                        const buttons = modal.querySelectorAll('button');
                        for (const btn of buttons) {
                            const text = btn.textContent.toLowerCase();
                            // Click Continue, Post, or similar confirmation buttons
                            if (text.includes('continue') || text.includes('post') || text.includes('confirm') || text.includes('yes')) {
                                console.log('Clicking modal button:', btn.textContent);
                                btn.click();
                                break;
                            }
                        }
                    }
                    // Also try clicking any primary/red button that appeared
                    const primaryBtns = document.querySelectorAll('button[class*="primary"], button[class*="danger"], button[class*="confirm"]');
                    for (const btn of primaryBtns) {
                        if (btn.offsetParent !== null) { // is visible
                            console.log('Clicking primary button:', btn.textContent);
                            btn.click();
                            break;
                        }
                    }
                ''')
                time.sleep(2)
            except Exception as e:
                print(f"  Popup check error: {e}")
            
            # Wait for post to complete (look for success indicators)
            print("  → Waiting for post confirmation...")
            success = False
            for check in range(90):  # Max 90 seconds for TikTok to process
                time.sleep(1)
                try:
                    # Handle "Content may be restricted" popup - click Continue/Post anyway
                    for continue_sel in [
                        'button:has-text("Continue")',
                        'button:has-text("Continue posting")',
                        'button:has-text("Post anyway")',
                        'button:has-text("Post now")',
                        '[class*="TUXButton--primary"]',
                        '[class*="confirm"] button',
                        '[class*="modal"] button[class*="primary"]',
                    ]:
                        try:
                            cont_btn = page.locator(continue_sel)
                            if cont_btn.count() > 0 and cont_btn.first.is_visible():
                                print(f"  ⚠️ Found confirmation popup - clicking {continue_sel}...")
                                cont_btn.first.click(timeout=2000)
                                time.sleep(1)
                                break
                        except:
                            pass
                    
                    page_content = page.content().lower()
                    current_url = page.url.lower()
                    
                    # Success indicators
                    if "your video is being uploaded" in page_content:
                        print("  ✓ 'Your video is being uploaded' detected!")
                        success = True
                        break
                    if "successfully" in page_content or "posted" in page_content:
                        print("  ✓ Success message detected!")
                        success = True
                        break
                    if "/profile" in current_url or "/@" in current_url:
                        print("  ✓ Redirected to profile!")
                        success = True
                        break
                    if "manage" in current_url or "content" in current_url:
                        print(f"  ✓ Redirected to content manager: {current_url}")
                        success = True
                        break
                    if "upload" not in current_url and "studio" not in current_url:
                        print(f"  ✓ Left upload page: {current_url}")
                        success = True
                        break
                    
                    # Check if Post button is no longer loading (post complete)
                    # Look for the loading spinner being gone AND the page changing
                    spinner = page.locator('[class*="loading"], [class*="spinner"]')
                    post_btn = page.locator('button:has-text("Post")')
                    
                    # If there's no spinner and no Post button, we likely succeeded
                    if spinner.count() == 0 and post_btn.count() == 0:
                        print("  ✓ Post button and spinner gone - likely posted!")
                        success = True
                        break
                        
                except:
                    pass
                
                if check % 10 == 0:
                    print(f"  ... waiting ({check}s)")
            
            page.screenshot(path=str(debug_dir / "04_after_post_click.png"))
            print(f"  📸 Screenshot: {debug_dir / '04_after_post_click.png'}")
            print(f"  📍 Current URL: {page.url}")
            
            browser.close()
            
            if success:
                print("✅ Uploaded successfully!")
                return True
            else:
                print("⚠️ Upload may have failed - check TikTok manually")
                return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False


def setup_auth():
    """Interactive setup for TikTok authentication."""
    print("🔐 TikTok Cookie Setup")
    print("=" * 40)
    print()
    print("To get your TikTok sessionid:")
    print("1. Open TikTok.com in Chrome")
    print("2. Log in to your account")
    print("3. Press F12 → Application → Cookies → tiktok.com")
    print("4. Find 'sessionid' and copy the value")
    print()
    
    sessionid = input("Paste your sessionid here: ").strip()
    
    if not sessionid:
        print("❌ No sessionid provided")
        return
    
    cookies = [
        {"name": "sessionid", "value": sessionid, "domain": ".tiktok.com", "path": "/"}
    ]
    
    COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    print(f"\n✅ Cookies saved to: {COOKIES_FILE}")
    print("   You can now upload videos!")


def main():
    parser = argparse.ArgumentParser(description="Upload videos to TikTok")
    parser.add_argument("video", nargs="?", help="Video file to upload")
    parser.add_argument("caption", nargs="?", help="Video caption")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--setup", action="store_true", help="Interactive cookie setup")
    args = parser.parse_args()
    
    if args.setup:
        setup_auth()
        return
    
    if not args.video or not args.caption:
        parser.print_help()
        print("\n💡 First time? Run: python upload_tiktok.py --setup")
        return
    
    tags = args.tags.split(",") if args.tags else ["shorts", "tech", "coding", "learn"]
    success = upload_video(args.video, args.caption, tags)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
