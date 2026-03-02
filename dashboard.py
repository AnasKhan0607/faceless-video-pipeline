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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Overview", "📹 Videos", "📝 Scripts", "📈 Analytics", "💰 Costs", "⚙️ Settings"])

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

# ==================== TAB 6: SETTINGS ====================
with tab6:
    st.subheader("⚙️ Settings & Tools")
    
    settings_tab1, settings_tab2, settings_tab3 = st.tabs(["💡 Topic Editor", "🎮 Backgrounds", "🛠️ Commands"])
    
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
    
    # ==================== BACKGROUNDS ====================
    with settings_tab2:
        st.markdown("### 🎮 Backgrounds")
        backgrounds = list(BACKGROUNDS_DIR.glob("*.mp4"))
        for bg in backgrounds:
            size_mb = bg.stat().st_size / (1024 * 1024)
            st.write(f"• **{bg.stem}** ({size_mb:.1f} MB)")
        
        st.info("To add backgrounds: place MP4 files in `backgrounds/` folder")
    
    # ==================== COMMANDS ====================
    with settings_tab3:
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
