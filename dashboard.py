#!/usr/bin/env python3
"""
Video Pipeline Dashboard
========================
Track video generation, uploads, and analytics.

Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import base64

# Config
PIPELINE_DIR = Path(__file__).parent
SCRIPTS_DIR = PIPELINE_DIR / "scripts"
OUT_DIR = PIPELINE_DIR / "out"
AUDIO_DIR = PIPELINE_DIR / "audio"
TOPICS_FILE = PIPELINE_DIR / "niches" / "tech" / "topics.json"
BACKGROUNDS_DIR = PIPELINE_DIR / "assets" / "backgrounds"
TOPICS_IMG_DIR = PIPELINE_DIR / "assets" / "topics"
DEBUG_DIR = PIPELINE_DIR / "debug_screenshots"
LOGS_DIR = PIPELINE_DIR / "logs"
ERROR_LOG_FILE = LOGS_DIR / "errors.json"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)

# Cost estimates (per video)
COSTS = {
    "openai_gpt4o": 0.01,  # Script generation
    "fish_audio": 0.015,   # TTS
    "deepgram": 0.005,     # Timestamps
    "total_per_video": 0.03
}

st.set_page_config(
    page_title="Video Pipeline Dashboard",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .video-thumbnail {
        border-radius: 8px;
        border: 2px solid #333;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎬 Video Pipeline Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")

# ==================== TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📊 Overview", "📹 Videos", "📝 Scripts", "📈 Analytics", "💰 Costs", "🚨 Logs", "⚙️ Settings"])

# ==================== TAB 1: OVERVIEW ====================
with tab1:
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    scripts = list(SCRIPTS_DIR.glob("ep_*.json"))
    videos = list(OUT_DIR.glob("*_final.mp4"))
    
    with col1:
        st.metric("📝 Scripts", len(scripts))
    
    with col2:
        st.metric("🎥 Videos", len(videos))
    
    # Topics
    try:
        topics_data = json.loads(TOPICS_FILE.read_text())
        topics_used = sum(1 for t in topics_data.get("topics", []) if t.get("used"))
        topics_total = len(topics_data.get("topics", []))
    except:
        topics_used, topics_total = 0, 0
    
    with col3:
        st.metric("💡 Topics Left", topics_total - topics_used)
    
    # Backgrounds
    backgrounds = list(BACKGROUNDS_DIR.glob("*.mp4"))
    with col4:
        st.metric("🎮 Backgrounds", len(backgrounds))
    
    # Estimated cost
    total_cost = len(videos) * COSTS["total_per_video"]
    with col5:
        st.metric("💵 Total Cost", f"${total_cost:.2f}")
    
    st.markdown("---")
    
    # Platform Status
    st.subheader("📱 Platform Status")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tiktok_auth = (PIPELINE_DIR / "tiktok_cookies.json").exists()
        if tiktok_auth:
            st.success("✅ TikTok Connected")
        else:
            st.error("❌ TikTok Not Setup")
    
    with col2:
        youtube_auth = (PIPELINE_DIR / ".youtube_token.json").exists()
        if youtube_auth:
            st.success("✅ YouTube Connected")
        else:
            st.error("❌ YouTube Not Setup")
    
    with col3:
        instagram_auth = (PIPELINE_DIR / "instagram_session.json").exists()
        if instagram_auth:
            st.success("✅ Instagram Connected")
        else:
            st.error("❌ Instagram Not Setup")
    
    st.markdown("---")
    
    # Cron Jobs
    st.subheader("⏰ Scheduled Posts")
    st.info("""
    | Job | Schedule | Status |
    |-----|----------|--------|
    | Morning Post | 10:00 AM daily | ✅ Enabled |
    | Evening Post | 6:00 PM daily | ✅ Enabled |
    """)
    
    st.markdown("---")
    
    # Quick Generate Section
    st.subheader("🚀 Quick Generate")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Generation options
        gen_col1, gen_col2, gen_col3 = st.columns(3)
        
        with gen_col1:
            num_videos = st.number_input("Videos to generate", min_value=1, max_value=10, value=1)
        
        with gen_col2:
            # Load character duos
            CHARACTERS_DIR = PIPELINE_DIR / "characters"
            duos = [d.name for d in CHARACTERS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
            selected_duo = st.selectbox("Character Duo", duos, index=duos.index("peter_stewie") if "peter_stewie" in duos else 0)
        
        with gen_col3:
            upload_after = st.checkbox("Upload after generation", value=False)
    
    with col2:
        st.markdown("")  # Spacing
        st.markdown("")
        
        # Generate button
        if st.button("🎬 Generate Video", type="primary", use_container_width=True):
            # Store generation request in session state
            st.session_state['generate_request'] = {
                'num': num_videos,
                'duo': selected_duo,
                'upload': upload_after,
                'started': True
            }
    
    # Handle generation (outside the button to prevent rerun issues)
    if st.session_state.get('generate_request', {}).get('started'):
        req = st.session_state['generate_request']
        st.session_state['generate_request'] = {}  # Clear request
        
        with st.status("🎬 Generating video...", expanded=True) as status:
            import subprocess
            import sys
            
            # Build command
            cmd = [sys.executable, "auto_generate.py", "--count", str(req['num'])]
            if req.get('upload'):
                cmd.append("--upload")
            
            st.write(f"Running: `{' '.join(cmd)}`")
            st.write(f"Character duo: {req['duo']}")
            
            try:
                # Run the command
                result = subprocess.run(
                    cmd,
                    cwd=str(PIPELINE_DIR),
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    status.update(label="✅ Video generated!", state="complete")
                    st.success("Video generated successfully!")
                    
                    # Show output
                    with st.expander("Output"):
                        st.code(result.stdout)
                    
                    # Refresh to show new video
                    st.balloons()
                else:
                    status.update(label="❌ Generation failed", state="error")
                    st.error("Generation failed!")
                    with st.expander("Error Output"):
                        st.code(result.stderr or result.stdout)
                        
            except subprocess.TimeoutExpired:
                status.update(label="⏱️ Timeout", state="error")
                st.error("Generation timed out after 5 minutes")
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

# ==================== TAB 2: VIDEOS ====================
with tab2:
    st.subheader("📹 Video Library")
    
    # View mode toggle
    view_mode = st.radio("View Mode", ["🎬 Grid", "▶️ Player"], horizontal=True)
    st.markdown("---")
    
    # Get all videos with their data
    video_cards = []
    for script_path in sorted(SCRIPTS_DIR.glob("ep_*.json"), reverse=True):
        try:
            script = json.loads(script_path.read_text())
            ep_id = script_path.stem
            
            # Find matching video and thumbnail
            video_files = list(OUT_DIR.glob(f"{ep_id}*.mp4"))
            thumbnail_files = list(TOPICS_IMG_DIR.glob(f"{ep_id}*.png"))
            
            video_cards.append({
                "ep_id": ep_id,
                "title": script.get("title", "Unknown"),
                "topic": script.get("topic", "Unknown"),
                "script": script,
                "video_path": video_files[0] if video_files else None,
                "thumbnail_path": thumbnail_files[0] if thumbnail_files else None,
                "created": datetime.fromtimestamp(script_path.stat().st_mtime)
            })
        except:
            pass
    
    if view_mode == "▶️ Player":
        # Video Player Mode
        if video_cards:
            # Video selector
            video_options = {f"{v['ep_id']} - {v['topic'][:50]}": i for i, v in enumerate(video_cards) if v['video_path']}
            
            if video_options:
                selected = st.selectbox("Select Video", list(video_options.keys()))
                selected_video = video_cards[video_options[selected]]
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Video player
                    st.markdown(f"### {selected_video['topic']}")
                    if selected_video['video_path'] and selected_video['video_path'].exists():
                        st.video(str(selected_video['video_path']))
                        
                        # Download button
                        with open(selected_video['video_path'], 'rb') as f:
                            st.download_button(
                                label="⬇️ Download Video",
                                data=f,
                                file_name=selected_video['video_path'].name,
                                mime="video/mp4"
                            )
                    else:
                        st.error("Video file not found")
                
                with col2:
                    # Video info
                    st.markdown("### 📋 Info")
                    if selected_video['video_path']:
                        size_mb = selected_video['video_path'].stat().st_size / (1024 * 1024)
                        st.write(f"**Size:** {size_mb:.1f} MB")
                    st.write(f"**Created:** {selected_video['created'].strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Episode:** {selected_video['ep_id']}")
                    
                    # Thumbnail
                    if selected_video['thumbnail_path'] and selected_video['thumbnail_path'].exists():
                        st.markdown("### 🖼️ Thumbnail")
                        st.image(str(selected_video['thumbnail_path']), use_container_width=True)
                    
                    # Script preview
                    st.markdown("### 📝 Script")
                    with st.expander("View Script"):
                        for i, line in enumerate(selected_video['script'].get('lines', [])):
                            st.write(f"**{line.get('character', 'Unknown')}:** {line.get('text', '')}")
            else:
                st.info("No rendered videos yet. Generate some videos first!")
        else:
            st.info("No videos generated yet. Run `python auto_generate.py --count 1`")
    
    else:
        # Grid Mode (original)
        if video_cards:
            for i in range(0, len(video_cards), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(video_cards):
                        video = video_cards[i + j]
                        with col:
                            # Thumbnail
                            if video["thumbnail_path"] and video["thumbnail_path"].exists():
                                st.image(str(video["thumbnail_path"]), use_container_width=True)
                            else:
                                st.image("https://via.placeholder.com/300x400/333/fff?text=No+Thumbnail", use_container_width=True)
                            
                            st.markdown(f"**{video['title'][:40]}...**" if len(video['title']) > 40 else f"**{video['title']}**")
                            st.caption(f"📅 {video['created'].strftime('%b %d, %H:%M')}")
                            st.caption(f"💡 {video['topic']}")
                            
                            # Video status
                            if video["video_path"]:
                                size_mb = video["video_path"].stat().st_size / (1024 * 1024)
                                st.success(f"✅ Rendered ({size_mb:.1f} MB)")
                                # Play button in expander
                                with st.expander("▶️ Play"):
                                    st.video(str(video["video_path"]))
                            else:
                                st.warning("⏳ Not rendered")
                            
                            st.markdown("---")
        else:
            st.info("No videos generated yet. Run `python auto_generate.py --count 1`")

# ==================== TAB 3: SCRIPTS ====================
with tab3:
    st.subheader("📝 Script Library")
    
    # Get all scripts
    all_scripts = []
    for script_path in sorted(SCRIPTS_DIR.glob("ep_*.json"), reverse=True):
        try:
            script = json.loads(script_path.read_text())
            video_files = list(OUT_DIR.glob(f"{script_path.stem}*.mp4"))
            all_scripts.append({
                "path": script_path,
                "ep_id": script_path.stem,
                "topic": script.get("topic", "Unknown"),
                "character_duo": script.get("character_duo", "Unknown"),
                "lines": script.get("lines", []),
                "created": datetime.fromtimestamp(script_path.stat().st_mtime),
                "rendered": len(video_files) > 0
            })
        except:
            pass
    
    if all_scripts:
        # Filter options
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search = st.text_input("🔍 Search topics", "")
        with col2:
            filter_rendered = st.selectbox("Status", ["All", "Rendered", "Not Rendered"])
        with col3:
            sort_by = st.selectbox("Sort", ["Newest", "Oldest"])
        
        # Apply filters
        filtered = all_scripts
        if search:
            filtered = [s for s in filtered if search.lower() in s["topic"].lower()]
        if filter_rendered == "Rendered":
            filtered = [s for s in filtered if s["rendered"]]
        elif filter_rendered == "Not Rendered":
            filtered = [s for s in filtered if not s["rendered"]]
        if sort_by == "Oldest":
            filtered = list(reversed(filtered))
        
        st.markdown(f"**Showing {len(filtered)} scripts**")
        st.markdown("---")
        
        # Script list with preview
        for script in filtered:
            with st.expander(f"{'✅' if script['rendered'] else '⏳'} **{script['topic']}** ({script['ep_id']})"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Character Duo:** {script['character_duo']}")
                    st.markdown(f"**Created:** {script['created'].strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**Lines:** {len(script['lines'])}")
                    
                    st.markdown("---")
                    st.markdown("**📜 Full Script:**")
                    
                    for i, line in enumerate(script['lines']):
                        character = line.get('character', 'Unknown')
                        text = line.get('text', '')
                        st.markdown(f"**{character}:** {text}")
                
                with col2:
                    # Actions
                    st.markdown("**Actions:**")
                    
                    if script['rendered']:
                        st.success("✅ Rendered")
                    else:
                        st.warning("⏳ Not rendered")
                        st.code(f"python pipeline_v2.py --script {script['path'].name}")
                    
                    # Raw JSON view
                    with st.expander("📄 Raw JSON"):
                        st.json(json.loads(script['path'].read_text()))
                    
                    # Estimated duration
                    word_count = sum(len(line.get('text', '').split()) for line in script['lines'])
                    est_duration = word_count / 2.5  # ~2.5 words per second
                    st.write(f"⏱️ Est. duration: {est_duration:.0f}s")
    else:
        st.info("No scripts found. Generate one with: `python auto_generate.py --count 1`")

# ==================== TAB 4: ANALYTICS ====================
with tab6:
    st.subheader("📈 Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Generation timeline
        st.markdown("### Videos Per Day")
        timeline_data = []
        for script_path in SCRIPTS_DIR.glob("ep_*.json"):
            try:
                created = datetime.fromtimestamp(script_path.stat().st_mtime)
                timeline_data.append({"date": created.date(), "count": 1})
            except:
                pass
        
        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)
            df_grouped = df_timeline.groupby("date").sum().reset_index()
            fig = px.bar(df_grouped, x="date", y="count", 
                        labels={"date": "Date", "count": "Videos"})
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet")
    
    with col2:
        # Topics usage
        st.markdown("### Topics Status")
        try:
            topics_data = json.loads(TOPICS_FILE.read_text())
            topics = topics_data.get("topics", [])
            used = sum(1 for t in topics if t.get("used"))
            unused = len(topics) - used
            
            fig = go.Figure(data=[go.Pie(
                labels=['Used', 'Available'],
                values=[used, unused],
                hole=.4,
                marker_colors=['#ff6b6b', '#4ecdc4']
            )])
            fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("No topics data")
    
    # Upload history from debug screenshots
    st.markdown("### 📤 Recent Upload Attempts")
    if DEBUG_DIR.exists():
        screenshots = sorted(DEBUG_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)[:4]
        if screenshots:
            cols = st.columns(4)
            for i, ss in enumerate(screenshots):
                with cols[i]:
                    st.image(str(ss), caption=ss.name, use_container_width=True)
        else:
            st.info("No upload screenshots yet")
    
    # Platform links
    st.markdown("### 🔗 View on Platforms")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("📱 TikTok Studio", "https://www.tiktok.com/tiktokstudio/content")
    with col2:
        st.link_button("▶️ YouTube Studio", "https://studio.youtube.com")
    with col3:
        st.link_button("📸 Instagram", "https://www.instagram.com")
    
    st.markdown("---")
    
    # Daily Summary History
    st.markdown("### 📊 Daily Summaries")
    
    SUMMARY_HISTORY_FILE = LOGS_DIR / "summary_history.json"
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("📊 Generate Today's Summary", use_container_width=True):
            try:
                import subprocess
                import sys
                result = subprocess.run(
                    [sys.executable, "daily_summary.py"],
                    cwd=str(PIPELINE_DIR),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    st.success("Summary generated!")
                    st.rerun()
                else:
                    st.error("Failed to generate summary")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Load history
    try:
        if SUMMARY_HISTORY_FILE.exists():
            history = json.loads(SUMMARY_HISTORY_FILE.read_text())
            history = sorted(history, key=lambda x: x.get("date", ""), reverse=True)
        else:
            history = []
    except:
        history = []
    
    if history:
        # Show recent summaries
        for summary in history[:7]:  # Last 7 days
            date = summary.get("date", "Unknown")
            videos = summary.get("videos_generated", 0)
            errors = summary.get("errors", 0)
            cost = summary.get("cost", 0)
            
            status = "✅" if errors == 0 else "⚠️"
            
            with st.expander(f"{status} **{date}** - {videos} videos, ${cost:.2f}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Videos", videos)
                with col2:
                    st.metric("Errors", errors)
                with col3:
                    st.metric("Cost", f"${cost:.2f}")
                with col4:
                    uploads = summary.get("uploads", {})
                    total_uploads = sum(uploads.values())
                    st.metric("Uploads", total_uploads)
                
                if summary.get("videos"):
                    st.markdown("**Topics:**")
                    for v in summary["videos"][:5]:
                        st.write(f"• {v.get('topic', 'Unknown')}")
                
                if summary.get("error_breakdown"):
                    st.markdown("**Error Breakdown:**")
                    for err_type, count in summary["error_breakdown"].items():
                        st.write(f"• {err_type}: {count}")
    else:
        st.info("No daily summaries yet. Click 'Generate Today's Summary' to create one.")

# ==================== TAB 5: COSTS ====================
with tab6:
    st.subheader("💰 Cost Tracking")
    
    num_videos = len(videos)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Cost Breakdown Per Video")
        cost_data = pd.DataFrame([
            {"Service": "OpenAI GPT-4o (Script)", "Cost": f"${COSTS['openai_gpt4o']:.3f}"},
            {"Service": "Fish.audio (TTS)", "Cost": f"${COSTS['fish_audio']:.3f}"},
            {"Service": "Deepgram (Timestamps)", "Cost": f"${COSTS['deepgram']:.3f}"},
            {"Service": "FFmpeg (Rendering)", "Cost": "$0.00"},
            {"Service": "Total", "Cost": f"${COSTS['total_per_video']:.3f}"},
        ])
        st.dataframe(cost_data, hide_index=True, use_container_width=True)
    
    with col2:
        st.markdown("### Total Spend")
        
        total = num_videos * COSTS['total_per_video']
        
        st.metric("Videos Generated", num_videos)
        st.metric("Cost Per Video", f"${COSTS['total_per_video']:.2f}")
        st.metric("Total Spent", f"${total:.2f}")
        
        # Projection
        st.markdown("---")
        st.markdown("### 📊 Projections")
        daily_videos = 2
        monthly_cost = daily_videos * 30 * COSTS['total_per_video']
        yearly_cost = monthly_cost * 12
        
        st.write(f"**At 2 videos/day:**")
        st.write(f"- Monthly: ${monthly_cost:.2f}")
        st.write(f"- Yearly: ${yearly_cost:.2f}")
    
    # Cost over time chart
    st.markdown("### 📈 Cumulative Cost")
    if num_videos > 0:
        cost_timeline = []
        running_total = 0
        for script_path in sorted(SCRIPTS_DIR.glob("ep_*.json")):
            try:
                created = datetime.fromtimestamp(script_path.stat().st_mtime)
                running_total += COSTS['total_per_video']
                cost_timeline.append({"date": created, "total": running_total})
            except:
                pass
        
        if cost_timeline:
            df_cost = pd.DataFrame(cost_timeline)
            fig = px.line(df_cost, x="date", y="total", markers=True,
                         labels={"date": "Date", "total": "Total Cost ($)"})
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

# Config file for storing selected character duo
CONFIG_FILE = PIPELINE_DIR / "dashboard_config.json"

def load_dashboard_config():
    try:
        return json.loads(CONFIG_FILE.read_text())
    except:
        return {"selected_character_duo": "peter_stewie"}

def save_dashboard_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

# ==================== TAB 6: LOGS ====================
with tab6:
    st.subheader("🚨 Logs & Debug")
    
    # Live log file path
    LIVE_LOG_FILE = LOGS_DIR / "pipeline.log"
    
    # Sub-tabs for different log views
    log_tab1, log_tab2, log_tab3 = st.tabs(["📺 Live Output", "🚨 Errors", "📸 Screenshots"])
    
    # ==================== LIVE OUTPUT ====================
    with log_tab1:
        st.markdown("### 📺 Live Pipeline Output")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
            if st.button("🗑️ Clear Log", use_container_width=True):
                if LIVE_LOG_FILE.exists():
                    LIVE_LOG_FILE.write_text("")
                st.success("Log cleared!")
                st.rerun()
        
        # Auto-refresh using st.empty and time
        if auto_refresh:
            import time
            st.info("Auto-refreshing every 5 seconds...")
            time.sleep(5)
            st.rerun()
        
        # Read and display log
        if LIVE_LOG_FILE.exists():
            log_content = LIVE_LOG_FILE.read_text()
            if log_content.strip():
                # Show last 100 lines
                lines = log_content.strip().split('\n')
                recent_lines = lines[-100:]
                
                st.code('\n'.join(recent_lines), language="text")
                
                st.caption(f"Showing last {len(recent_lines)} of {len(lines)} lines")
            else:
                st.info("Log is empty. Start a video generation to see output here.")
        else:
            st.info("No log file yet. Pipeline output will appear here when generation runs.")
        
        st.markdown("---")
        st.markdown("**Tip:** Run pipeline with logging:")
        st.code(f"python auto_generate.py --count 1 2>&1 | tee {LIVE_LOG_FILE}")
    
    # ==================== ERRORS ====================
    with log_tab2:
        st.markdown("### 🚨 Error Log")
        
        # Helper functions for error logging
        def load_error_log():
            try:
                if ERROR_LOG_FILE.exists():
                    return json.loads(ERROR_LOG_FILE.read_text())
                return []
            except:
                return []
        
        def save_error_log(errors):
            ERROR_LOG_FILE.write_text(json.dumps(errors, indent=2))
        
        def add_error(error_type, message, details=None):
            errors = load_error_log()
            errors.append({
                "timestamp": datetime.now().isoformat(),
                "type": error_type,
                "message": message,
                "details": details or {}
            })
            save_error_log(errors)
    
        # Load errors
        errors = load_error_log()
        
        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Errors", len(errors))
        with col2:
            upload_errors = len([e for e in errors if "upload" in e.get("type", "").lower()])
            st.metric("Upload Errors", upload_errors)
        with col3:
            recent_errors = len([e for e in errors if datetime.fromisoformat(e.get("timestamp", "2000-01-01")) > datetime.now() - timedelta(days=1)])
            st.metric("Last 24h", recent_errors)
        
        st.markdown("---")
        
        if errors:
            # Filter
            col1, col2 = st.columns(2)
            with col1:
                error_filter = st.selectbox("Filter by type", ["All"] + list(set(e.get("type", "unknown") for e in errors)))
            with col2:
                time_filter = st.selectbox("Time range", ["All Time", "Last 24h", "Last 7 days"])
            
            # Apply filters
            filtered_errors = errors
            if error_filter != "All":
                filtered_errors = [e for e in filtered_errors if e.get("type") == error_filter]
            if time_filter == "Last 24h":
                filtered_errors = [e for e in filtered_errors if datetime.fromisoformat(e.get("timestamp", "2000-01-01")) > datetime.now() - timedelta(days=1)]
            elif time_filter == "Last 7 days":
                filtered_errors = [e for e in filtered_errors if datetime.fromisoformat(e.get("timestamp", "2000-01-01")) > datetime.now() - timedelta(days=7)]
            
            # Sort by newest first
            filtered_errors = sorted(filtered_errors, key=lambda x: x.get("timestamp", ""), reverse=True)
            
            st.markdown(f"**Showing {len(filtered_errors)} errors**")
            
            for error in filtered_errors[:20]:  # Limit to 20
                timestamp = datetime.fromisoformat(error.get("timestamp", "")).strftime("%Y-%m-%d %H:%M:%S")
                error_type = error.get("type", "unknown")
                message = error.get("message", "No message")
                
                with st.expander(f"🔴 [{error_type}] {timestamp} - {message[:50]}..."):
                    st.write(f"**Type:** {error_type}")
                    st.write(f"**Time:** {timestamp}")
                    st.write(f"**Message:** {message}")
                    if error.get("details"):
                        st.markdown("**Details:**")
                        st.json(error.get("details"))
            
            # Clear errors button
            st.markdown("---")
            if st.button("🗑️ Clear All Errors", type="secondary"):
                save_error_log([])
                st.success("Errors cleared!")
                st.rerun()
        else:
            st.success("✅ No errors logged!")
            st.info("Errors from upload scripts will appear here. You can also manually add errors for testing.")
        
        # Manual error entry (for testing)
        with st.expander("➕ Add Test Error"):
            test_type = st.text_input("Error Type", "upload_tiktok")
            test_message = st.text_input("Message", "Test error message")
            if st.button("Add Error"):
                errors.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": test_type,
                    "message": test_message,
                    "details": {"manual": True}
                })
                save_error_log(errors)
                st.success("Error added!")
                st.rerun()
    
    # ==================== SCREENSHOTS ====================
    with log_tab3:
        st.markdown("### 📸 Debug Screenshots")
        if DEBUG_DIR.exists():
            screenshots = sorted(DEBUG_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
            if screenshots:
                # Group by date
                today_ss = [s for s in screenshots if datetime.fromtimestamp(s.stat().st_mtime).date() == datetime.now().date()]
                older_ss = [s for s in screenshots if datetime.fromtimestamp(s.stat().st_mtime).date() != datetime.now().date()]
                
                if today_ss:
                    st.markdown("#### Today")
                    cols = st.columns(min(4, len(today_ss)))
                    for i, ss in enumerate(today_ss[:4]):
                        with cols[i]:
                            st.image(str(ss), caption=ss.name, use_container_width=True)
                            st.caption(datetime.fromtimestamp(ss.stat().st_mtime).strftime("%H:%M:%S"))
                
                if older_ss:
                    st.markdown("#### Older Screenshots")
                    cols = st.columns(4)
                    for i, ss in enumerate(older_ss[:12]):
                        with cols[i % 4]:
                            st.image(str(ss), caption=ss.name, use_container_width=True)
                
                # Clear screenshots button
                st.markdown("---")
                if st.button("🗑️ Clear All Screenshots", type="secondary"):
                    for ss in screenshots:
                        ss.unlink()
                    st.success("Screenshots cleared!")
                    st.rerun()
            else:
                st.info("No debug screenshots yet")
        else:
            st.info("Debug directory not found")

# ==================== TAB 7: SETTINGS ====================
with tab7:
    st.subheader("⚙️ Settings & Tools")
    
    settings_tab1, settings_tab2, settings_tab3, settings_tab4, settings_tab5 = st.tabs(["💡 Topic Editor", "🎭 Characters", "🎮 Backgrounds", "📢 Notifications", "🛠️ Commands"])
    
    # ==================== TOPIC EDITOR ====================
    with settings_tab1:
        st.markdown("### 💡 Topic Editor")
        
        # Load topics
        try:
            topics_data = json.loads(TOPICS_FILE.read_text())
            topics = topics_data.get("topics", [])
        except:
            topics_data = {"niche": "tech", "topics": []}
            topics = []
        
        # Stats
        col1, col2, col3 = st.columns(3)
        used_count = sum(1 for t in topics if t.get("used"))
        with col1:
            st.metric("Total Topics", len(topics))
        with col2:
            st.metric("Used", used_count)
        with col3:
            st.metric("Available", len(topics) - used_count)
        
        st.markdown("---")
        
        # Add new topic
        st.markdown("#### ➕ Add New Topic")
        col1, col2 = st.columns([3, 1])
        with col1:
            new_topic = st.text_input("Topic", placeholder="e.g., What is Machine Learning")
        with col2:
            if st.button("Add Topic", use_container_width=True):
                if new_topic.strip():
                    # Find max ID
                    max_id = max([t.get("id", 0) for t in topics], default=0)
                    topics.append({
                        "id": max_id + 1,
                        "topic": new_topic.strip(),
                        "used": False
                    })
                    topics_data["topics"] = topics
                    TOPICS_FILE.write_text(json.dumps(topics_data, indent=2))
                    st.success(f"Added: {new_topic}")
                    st.rerun()
                else:
                    st.error("Topic cannot be empty")
        
        st.markdown("---")
        
        # Filter
        col1, col2 = st.columns(2)
        with col1:
            topic_filter = st.selectbox("Filter", ["All", "Available", "Used"], key="topic_filter")
        with col2:
            topic_search = st.text_input("Search", "", key="topic_search")
        
        # Apply filter
        filtered_topics = topics
        if topic_filter == "Available":
            filtered_topics = [t for t in topics if not t.get("used")]
        elif topic_filter == "Used":
            filtered_topics = [t for t in topics if t.get("used")]
        if topic_search:
            filtered_topics = [t for t in filtered_topics if topic_search.lower() in t.get("topic", "").lower()]
        
        st.markdown(f"**Showing {len(filtered_topics)} topics**")
        
        # Topic list
        for i, topic in enumerate(filtered_topics):
            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
            
            with col1:
                status = "✅" if topic.get("used") else "⏳"
                st.write(f"{status} **{topic.get('topic', 'Unknown')}**")
            
            with col2:
                # Toggle used status
                if topic.get("used"):
                    if st.button("↩️ Unuse", key=f"unuse_{topic.get('id')}"):
                        for t in topics:
                            if t.get("id") == topic.get("id"):
                                t["used"] = False
                                t.pop("used_at", None)
                        topics_data["topics"] = topics
                        TOPICS_FILE.write_text(json.dumps(topics_data, indent=2))
                        st.rerun()
                else:
                    if st.button("✓ Mark Used", key=f"use_{topic.get('id')}"):
                        for t in topics:
                            if t.get("id") == topic.get("id"):
                                t["used"] = True
                                t["used_at"] = datetime.now().isoformat()
                        topics_data["topics"] = topics
                        TOPICS_FILE.write_text(json.dumps(topics_data, indent=2))
                        st.rerun()
            
            with col3:
                # Edit (in expander)
                pass  # Edit handled in expander below
            
            with col4:
                # Delete
                if st.button("🗑️", key=f"del_{topic.get('id')}"):
                    topics = [t for t in topics if t.get("id") != topic.get("id")]
                    topics_data["topics"] = topics
                    TOPICS_FILE.write_text(json.dumps(topics_data, indent=2))
                    st.success(f"Deleted topic")
                    st.rerun()
    
    # ==================== CHARACTERS ====================
    with settings_tab2:
        st.markdown("### 🎭 Character Duos")
        
        # Get all character duos
        CHARACTERS_DIR = PIPELINE_DIR / "characters"
        character_duos = []
        
        for duo_dir in CHARACTERS_DIR.iterdir():
            if duo_dir.is_dir() and not duo_dir.name.startswith('.'):
                config_file = duo_dir / "config.json"
                if config_file.exists():
                    try:
                        config = json.loads(config_file.read_text())
                        char1_img = duo_dir / config.get("char1", {}).get("image", "char1.png")
                        char2_img = duo_dir / config.get("char2", {}).get("image", "char2.png")
                        character_duos.append({
                            "name": duo_dir.name,
                            "display_name": config.get("display_name", duo_dir.name.replace("_", " ").title()),
                            "config": config,
                            "dir": duo_dir,
                            "char1_name": config.get("char1", {}).get("display_name", "Character 1"),
                            "char2_name": config.get("char2", {}).get("display_name", "Character 2"),
                            "char1_img": char1_img if char1_img.exists() else None,
                            "char2_img": char2_img if char2_img.exists() else None
                        })
                    except:
                        pass
        
        if character_duos:
            # Load current config
            dashboard_config = load_dashboard_config()
            current_duo = dashboard_config.get("selected_character_duo", "peter_stewie")
            
            st.markdown("#### Select Default Character Duo")
            
            # Character duo selector
            duo_names = [d["name"] for d in character_duos]
            duo_display = {d["name"]: f"{d['display_name']} ({d['char1_name']} & {d['char2_name']})" for d in character_duos}
            
            selected = st.selectbox(
                "Default duo for new videos",
                duo_names,
                index=duo_names.index(current_duo) if current_duo in duo_names else 0,
                format_func=lambda x: duo_display.get(x, x)
            )
            
            if selected != current_duo:
                dashboard_config["selected_character_duo"] = selected
                save_dashboard_config(dashboard_config)
                st.success(f"Default character duo set to: {duo_display[selected]}")
            
            st.markdown("---")
            st.markdown("#### Available Duos")
            
            # Display character duos
            for duo in character_duos:
                is_selected = duo["name"] == selected
                status = "✅ Selected" if is_selected else ""
                
                with st.expander(f"{'⭐ ' if is_selected else ''}{duo['display_name']} {status}"):
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        st.markdown(f"**{duo['char1_name']}**")
                        if duo["char1_img"]:
                            st.image(str(duo["char1_img"]), width=150)
                        else:
                            st.info("No image")
                    
                    with col2:
                        st.markdown(f"**{duo['char2_name']}**")
                        if duo["char2_img"]:
                            st.image(str(duo["char2_img"]), width=150)
                        else:
                            st.info("No image")
                    
                    with col3:
                        st.markdown("**Config:**")
                        st.json(duo["config"])
        else:
            st.info("No character duos found. Add them to `characters/` folder.")
    
    # ==================== BACKGROUNDS ====================
    with settings_tab3:
        st.markdown("### 🎮 Background Manager")
        
        # Ensure backgrounds directory exists
        BACKGROUNDS_DIR.mkdir(exist_ok=True)
        
        backgrounds = list(BACKGROUNDS_DIR.glob("*.mp4"))
        
        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Backgrounds", len(backgrounds))
        with col2:
            total_size = sum(bg.stat().st_size for bg in backgrounds) / (1024 * 1024)
            st.metric("Total Size", f"{total_size:.1f} MB")
        with col3:
            # Load config for active backgrounds
            bg_config = load_dashboard_config()
            active_bgs = bg_config.get("active_backgrounds", [bg.name for bg in backgrounds])
            st.metric("Active", len([b for b in active_bgs if (BACKGROUNDS_DIR / b).exists()]))
        
        st.markdown("---")
        
        # Upload new background
        st.markdown("#### ⬆️ Upload New Background")
        uploaded_file = st.file_uploader(
            "Upload MP4 video",
            type=["mp4"],
            help="Upload gameplay footage (Subway Surfers, Minecraft, etc.)"
        )
        
        if uploaded_file:
            col1, col2 = st.columns([3, 1])
            with col1:
                # Custom filename
                custom_name = st.text_input(
                    "Filename (optional)",
                    value=uploaded_file.name.replace(".mp4", ""),
                    help="Leave empty to use original filename"
                )
            with col2:
                st.markdown("")
                st.markdown("")
                if st.button("💾 Save Background", use_container_width=True):
                    # Save the file
                    filename = f"{custom_name or uploaded_file.name.replace('.mp4', '')}.mp4"
                    save_path = BACKGROUNDS_DIR / filename
                    
                    if save_path.exists():
                        st.error(f"File {filename} already exists!")
                    else:
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"Saved: {filename}")
                        st.rerun()
        
        st.markdown("---")
        
        # List backgrounds with controls
        st.markdown("#### 📁 Available Backgrounds")
        
        if backgrounds:
            for bg in sorted(backgrounds, key=lambda x: x.name):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                size_mb = bg.stat().st_size / (1024 * 1024)
                is_active = bg.name in active_bgs
                
                with col1:
                    status = "✅" if is_active else "⏸️"
                    st.write(f"{status} **{bg.stem}** ({size_mb:.1f} MB)")
                
                with col2:
                    # Toggle active status
                    if is_active:
                        if st.button("⏸️ Disable", key=f"disable_{bg.name}"):
                            active_bgs = [b for b in active_bgs if b != bg.name]
                            bg_config["active_backgrounds"] = active_bgs
                            save_dashboard_config(bg_config)
                            st.rerun()
                    else:
                        if st.button("✅ Enable", key=f"enable_{bg.name}"):
                            active_bgs.append(bg.name)
                            bg_config["active_backgrounds"] = active_bgs
                            save_dashboard_config(bg_config)
                            st.rerun()
                
                with col3:
                    # Preview (just show file info for now)
                    with st.expander("ℹ️"):
                        st.write(f"**Path:** {bg}")
                        st.write(f"**Size:** {size_mb:.1f} MB")
                        modified = datetime.fromtimestamp(bg.stat().st_mtime)
                        st.write(f"**Modified:** {modified.strftime('%Y-%m-%d %H:%M')}")
                
                with col4:
                    # Delete button
                    if st.button("🗑️", key=f"del_bg_{bg.name}"):
                        bg.unlink()
                        # Remove from active list
                        active_bgs = [b for b in active_bgs if b != bg.name]
                        bg_config["active_backgrounds"] = active_bgs
                        save_dashboard_config(bg_config)
                        st.success(f"Deleted: {bg.name}")
                        st.rerun()
        else:
            st.info("No backgrounds found. Upload some MP4 files above!")
    
    # ==================== NOTIFICATIONS ====================
    with settings_tab4:
        st.markdown("### 📢 Discord Notifications")
        
        st.markdown("""
        Get notified on Discord when videos are generated or uploads succeed/fail.
        
        **Setup:**
        1. Go to your Discord server → Server Settings → Integrations → Webhooks
        2. Create a new webhook and copy the URL
        3. Paste it below
        """)
        
        # Load current webhook
        webhook_config = load_dashboard_config()
        current_webhook = webhook_config.get("discord_webhook_url", "")
        
        # Webhook input
        webhook_url = st.text_input(
            "Discord Webhook URL",
            value=current_webhook,
            type="password",
            placeholder="https://discord.com/api/webhooks/..."
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Webhook", use_container_width=True):
                if webhook_url:
                    webhook_config["discord_webhook_url"] = webhook_url
                    save_dashboard_config(webhook_config)
                    st.success("Webhook saved!")
                else:
                    # Remove webhook
                    webhook_config.pop("discord_webhook_url", None)
                    save_dashboard_config(webhook_config)
                    st.info("Webhook removed")
        
        with col2:
            if st.button("🧪 Test Notification", use_container_width=True):
                if webhook_url:
                    # Test the webhook
                    try:
                        import httpx
                        test_payload = {
                            "embeds": [{
                                "title": "🧪 Test Notification",
                                "description": "Discord notifications are working!",
                                "color": 0x2ecc71,
                                "footer": {"text": "Video Pipeline"}
                            }]
                        }
                        response = httpx.post(webhook_url, json=test_payload, timeout=10)
                        if response.status_code == 204:
                            st.success("Test notification sent! Check Discord.")
                        else:
                            st.error(f"Failed: HTTP {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Enter a webhook URL first")
        
        st.markdown("---")
        st.markdown("### Notification Events")
        
        # Notification toggles
        notify_config = webhook_config.get("notifications", {
            "on_video_generated": True,
            "on_upload_success": True,
            "on_upload_failed": True,
            "daily_summary": False
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            notify_config["on_video_generated"] = st.checkbox(
                "🎬 Video Generated",
                value=notify_config.get("on_video_generated", True)
            )
            notify_config["on_upload_success"] = st.checkbox(
                "✅ Upload Success",
                value=notify_config.get("on_upload_success", True)
            )
        
        with col2:
            notify_config["on_upload_failed"] = st.checkbox(
                "❌ Upload Failed",
                value=notify_config.get("on_upload_failed", True)
            )
            notify_config["daily_summary"] = st.checkbox(
                "📊 Daily Summary",
                value=notify_config.get("daily_summary", False)
            )
        
        # Save notification settings
        if notify_config != webhook_config.get("notifications", {}):
            webhook_config["notifications"] = notify_config
            save_dashboard_config(webhook_config)
    
    # ==================== COMMANDS ====================
    with settings_tab5:
        st.markdown("### 🛠️ Quick Commands")
        st.code("""
# Generate 1 video + upload
python auto_generate.py --count 1 --upload

# Generate without upload
python auto_generate.py --count 1

# TikTok setup
python upload_tiktok.py --setup

# Instagram setup
python upload_instagram.py --setup

# Run dashboard
streamlit run dashboard.py
        """)
        
        st.markdown("---")
        st.markdown("### 📁 Paths")
        st.code(f"""
Pipeline: {PIPELINE_DIR}
Scripts:  {SCRIPTS_DIR}
Videos:   {OUT_DIR}
        """)

# ==================== FOOTER ====================
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col2:
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.rerun()

st.caption("Video Pipeline Dashboard • Built with Streamlit • Cost: ~$0.03/video")
