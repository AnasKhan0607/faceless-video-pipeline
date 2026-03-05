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

DEFAULT_COOKIES_FILE = Path(__file__).parent / "tiktok_cookies.json"


def get_cookies_list(cookies_file: Path = None):
    """Load cookies from JSON file.
    
    Args:
        cookies_file: Path to cookies file. If None, uses default location.
    """
    file_path = cookies_file if cookies_file else DEFAULT_COOKIES_FILE
    
    if not file_path.exists():
        return None
    
    try:
        data = json.loads(file_path.read_text())
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "sessionid" in data:
            return [{"name": "sessionid", "value": data["sessionid"], "domain": ".tiktok.com"}]
        return None
    except Exception as e:
        print(f"❌ Error loading cookies from {file_path}: {e}")
        return None


def dismiss_modal_dialogs(page):
    """Dismiss any modal dialogs that might block interaction.
    
    Handles:
    - "Are you sure you want to exit?" confirmation modals
    - Other confirmation/warning dialogs
    """
    modal_handled = False
    
    try:
        # Check for exit confirmation modal
        exit_modal_selectors = [
            'text="Are you sure you want to exit"',
            'text="Are you sure you want to leave"',
            'text="Discard changes"',
            '[class*="modal"][class*="confirm"]',
            '[class*="Modal"][class*="Confirm"]',
        ]
        
        for selector in exit_modal_selectors:
            try:
                modal = page.locator(selector)
                if modal.count() > 0 and modal.is_visible():
                    print(f"  ⚠️ Modal detected: {selector}")
                    
                    # Try to click Cancel/Stay/Continue editing buttons
                    dismiss_buttons = [
                        'button:has-text("Cancel")',
                        'button:has-text("Stay")',
                        'button:has-text("Continue editing")',
                        'button:has-text("Keep editing")',
                        'button:has-text("No")',
                        '[class*="cancel" i]',
                        '[class*="Cancel"]',
                    ]
                    
                    for btn_selector in dismiss_buttons:
                        try:
                            btn = page.locator(btn_selector)
                            if btn.count() > 0 and btn.first.is_visible():
                                btn.first.click(timeout=2000)
                                print(f"  ✓ Dismissed modal via: {btn_selector}")
                                modal_handled = True
                                time.sleep(0.5)
                                break
                        except:
                            pass
                    
                    if modal_handled:
                        break
            except:
                pass
        
        # Also try JavaScript fallback to close any modal
        if not modal_handled:
            try:
                closed = page.evaluate('''(function() {
                    var modals = document.querySelectorAll('[class*="modal"], [class*="Modal"], [role="dialog"]');
                    var closed = false;
                    for (var i = 0; i < modals.length; i++) {
                        var modal = modals[i];
                        var text = modal.textContent || '';
                        if (text.indexOf('exit') !== -1 || text.indexOf('leave') !== -1 || text.indexOf('discard') !== -1) {
                            var buttons = modal.querySelectorAll('button');
                            for (var j = 0; j < buttons.length; j++) {
                                var btn = buttons[j];
                                var t = (btn.textContent || '').toLowerCase();
                                if (t.indexOf('cancel') !== -1 || t.indexOf('stay') !== -1 || t.indexOf('continue') !== -1 || t.indexOf('no') !== -1) {
                                    btn.click();
                                    closed = true;
                                    break;
                                }
                            }
                        }
                        if (closed) break;
                    }
                    return closed;
                })()''')
                if closed:
                    print("  ✓ Dismissed modal via JavaScript")
                    modal_handled = True
                    time.sleep(0.5)
            except Exception as js_err:
                print(f"  ⚠️ JS modal dismiss failed (non-fatal): {js_err}")
                
    except Exception as e:
        print(f"  ⚠️ Modal dismiss error (non-fatal): {e}")
    
    return modal_handled


def dismiss_joyride(page, max_attempts=10):
    """Try to dismiss any Joyride/tutorial overlays and feature popups."""
    for i in range(max_attempts):
        try:
            # FIRST: Handle "New editing features" popup - this is common on TikTok
            try:
                got_it_btn = page.locator('button:has-text("Got it")').first
                if got_it_btn.count() > 0 and got_it_btn.is_visible():
                    print(f"  🚫 Found 'Got it' popup (attempt {i+1}), dismissing...")
                    got_it_btn.click(timeout=3000)
                    time.sleep(0.5)
                    continue  # Check for more popups
            except:
                pass
            
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
                'button:has-text("OK")',
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


def upload_video(video_path: str, caption: str, tags: list[str] = None, cookies_file: str = None) -> bool:
    """Upload a video to TikTok with Joyride handling.
    
    Args:
        video_path: Path to the video file
        caption: Video caption
        tags: List of hashtags
        cookies_file: Path to cookies JSON file (optional, uses default if not specified)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ playwright not installed. Run: pip install playwright && playwright install")
        return False
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False
    
    # Use custom cookies file if provided
    cookies_path = Path(cookies_file) if cookies_file else None
    cookies = get_cookies_list(cookies_path)
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
            
            # Scroll to bottom first to make sure Post button is visible
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            
            # CRITICAL: Dismiss any modal dialogs BEFORE clicking Post
            dismiss_modal_dialogs(page)
            dismiss_joyride(page)
            
            # Find and click the Post button with retry logic
            post_clicked = False
            max_post_attempts = 5
            
            for attempt in range(max_post_attempts):
                if post_clicked:
                    break
                    
                if attempt > 0:
                    print(f"  → Post attempt {attempt + 1}/{max_post_attempts}...")
                    # Dismiss any modals that appeared
                    dismiss_modal_dialogs(page)
                    time.sleep(1)
                
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
                            
                            # Check for and dismiss modals right before clicking
                            dismiss_modal_dialogs(page)
                            
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
                        # Check if a modal appeared during click attempt
                        if dismiss_modal_dialogs(page):
                            print(f"  ⚠️ Modal blocked click, dismissed and will retry...")
                            break  # Break inner loop to retry
                        print(f"  Selector {selector} failed: {e}")
                        continue
                
                # After each attempt, check if modal appeared
                time.sleep(0.5)
                dismiss_modal_dialogs(page)
            
            if not post_clicked:
                # Fallback to JavaScript - find and click the Post button
                print("  ⚠️ Trying JavaScript click...")
                # First dismiss modals via JS
                try:
                    page.evaluate('''(function() {
                        var modals = document.querySelectorAll('[class*="modal"], [class*="Modal"], [role="dialog"]');
                        for (var i = 0; i < modals.length; i++) {
                            var el = modals[i];
                            if (el.textContent && el.textContent.indexOf('exit') !== -1) {
                                var buttons = el.querySelectorAll('button');
                                for (var j = 0; j < buttons.length; j++) {
                                    var btn = buttons[j];
                                    var t = (btn.textContent || '').toLowerCase();
                                    if (t.indexOf('cancel') !== -1 || t.indexOf('stay') !== -1) {
                                        btn.click();
                                        break;
                                    }
                                }
                            }
                        }
                    })()''')
                except:
                    pass
                time.sleep(0.3)
                
                clicked = page.evaluate('''(function() {
                    var btns = document.querySelectorAll('button');
                    var clicked = false;
                    for (var i = 0; i < btns.length; i++) {
                        var btn = btns[i];
                        var text = (btn.textContent || '').trim().toLowerCase();
                        if (text === 'post' && !btn.disabled) {
                            console.log('Found Post button:', btn);
                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                            btn.focus();
                            btn.click();
                            btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                            clicked = true;
                            break;
                        }
                    }
                    return clicked;
                })()''')
                if clicked:
                    print("  ✓ JavaScript click executed")
                    post_clicked = True
            
            # Extra wait and retry if Post button still visible
            time.sleep(3)
            dismiss_modal_dialogs(page)  # Handle any post-click modals
            
            still_has_post = page.locator('button:has-text("Post")').count() > 0
            if still_has_post:
                print("  ⚠️ Post button still visible, trying force click...")
                dismiss_modal_dialogs(page)
                page.locator('button:has-text("Post")').first.click(force=True, timeout=5000)
                time.sleep(2)
            
            # Wait for post to complete (look for success indicators)
            print("  → Waiting for post confirmation...")
            success = False
            for check in range(90):  # Max 90 seconds for TikTok to process
                time.sleep(1)
                try:
                    page_content = page.content().lower()
                    current_url = page.url.lower()
                    
                    # Handle any modal dialogs that might be blocking
                    if dismiss_modal_dialogs(page):
                        print("  ⚠️ Modal dismissed during confirmation, re-clicking Post...")
                        time.sleep(0.5)
                        # Re-click Post button after dismissing modal
                        try:
                            post_retry = page.locator('button:has-text("Post")').first
                            if post_retry.count() > 0 and post_retry.is_visible():
                                post_retry.click(timeout=5000)
                                print("  → Re-clicked Post button")
                        except:
                            pass
                        continue
                    
                    # Handle "Continue editing" button specifically
                    try:
                        continue_btn = page.locator('button:has-text("Continue editing")')
                        if continue_btn.count() > 0 and continue_btn.is_visible():
                            print("  ⚠️ 'Continue editing' modal appeared, clicking...")
                            continue_btn.click(timeout=3000)
                            time.sleep(1)
                            continue
                    except:
                        pass
                    
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
                    
                    # Check if Post button changed to "Posting..." or disappeared
                    post_btn_check = page.locator('button:has-text("Post")')
                    posting_btn = page.locator('button:has-text("Posting")')
                    
                    if posting_btn.count() > 0:
                        print("  → 'Posting...' detected, waiting...")
                        continue
                    
                    # Check if Post button is no longer loading (post complete)
                    # Look for the loading spinner being gone AND the page changing
                    spinner = page.locator('[class*="loading"], [class*="spinner"]')
                    
                    # If there's no spinner and no Post button, we likely succeeded
                    if spinner.count() == 0 and post_btn_check.count() == 0:
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
    
    DEFAULT_COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    print(f"\n✅ Cookies saved to: {DEFAULT_COOKIES_FILE}")
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
