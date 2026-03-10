#!/usr/bin/env python3
"""
Video Pipeline Dashboard v2.0
=============================
Cleaner, more intuitive interface for managing video generation.

Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import json
import os
import subprocess
import psutil
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Import account manager
from accounts import (
    load_accounts, save_accounts, get_account, create_account,
    update_account, delete_account, toggle_account, get_active_accounts,
    migrate_existing_credentials, CREDENTIALS_DIR
)

# Config paths
PIPELINE_DIR = Path(__file__).parent
SCRIPTS_DIR = PIPELINE_DIR / "scripts"
OUT_DIR = PIPELINE_DIR / "out"
AUDIO_DIR = PIPELINE_DIR / "audio"
NICHES_DIR = PIPELINE_DIR / "niches"
CHARACTERS_DIR = PIPELINE_DIR / "characters"
BACKGROUNDS_DIR = PIPELINE_DIR / "backgrounds"
DEBUG_DIR = PIPELINE_DIR / "debug_screenshots"
LOGS_DIR = PIPELINE_DIR / "logs"
QUEUE_FILE = PIPELINE_DIR / "queue" / "pending.json"
PERFORMANCE_FILE = PIPELINE_DIR / "analytics" / "performance.json"

# Ensure directories exist
for d in [LOGS_DIR, PIPELINE_DIR / "queue", PIPELINE_DIR / "analytics"]:
    d.mkdir(exist_ok=True)

# Cost per video
COST_PER_VIDEO = 0.03

# Page config
st.set_page_config(
    page_title="Video Pipeline",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Root variables */
    :root {
        --bg-primary: #0f0f0f;
        --bg-secondary: #1a1a1a;
        --bg-tertiary: #252525;
        --accent: #6366f1;
        --accent-hover: #818cf8;
        --success: #22c55e;
        --warning: #eab308;
        --error: #ef4444;
        --text-primary: #ffffff;
        --text-secondary: #a1a1aa;
        --border: #333;
    }
    
    .stApp {
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border);
    }
    
    section[data-testid="stSidebar"] .stRadio > label {
        display: none;
    }
    
    section[data-testid="stSidebar"] .stRadio > div {
        flex-direction: column;
        gap: 4px;
    }
    
    section[data-testid="stSidebar"] .stRadio > div > label {
        background: transparent;
        padding: 12px 16px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        border: none;
    }
    
    section[data-testid="stSidebar"] .stRadio > div > label:hover {
        background: var(--bg-tertiary);
    }
    
    section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
        background: var(--accent);
    }
    
    /* Card styling */
    .card {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    
    .card-header {
        font-size: 14px;
        color: var(--text-secondary);
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .card-value {
        font-size: 32px;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .card-subtitle {
        font-size: 13px;
        color: var(--text-secondary);
        margin-top: 4px;
    }
    
    /* Metric cards row */
    .metrics-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }
    
    /* Status pills */
    .pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 100px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .pill-success { background: rgba(34, 197, 94, 0.15); color: var(--success); }
    .pill-warning { background: rgba(234, 179, 8, 0.15); color: var(--warning); }
    .pill-error { background: rgba(239, 68, 68, 0.15); color: var(--error); }
    .pill-neutral { background: var(--bg-tertiary); color: var(--text-secondary); }
    
    /* Section headers */
    .section-header {
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border);
    }
    
    /* Quick action buttons */
    .quick-actions {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;
    }
    
    .action-btn {
        background: var(--bg-tertiary);
        border: 1px solid var(--border);
        padding: 12px 20px;
        border-radius: 8px;
        color: var(--text-primary);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .action-btn:hover {
        background: var(--accent);
        border-color: var(--accent);
    }
    
    .action-btn-primary {
        background: var(--accent);
        border-color: var(--accent);
    }
    
    /* Video grid */
    .video-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 16px;
    }
    
    .video-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
    }
    
    .video-thumb {
        aspect-ratio: 9/16;
        background: var(--bg-tertiary);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .video-info {
        padding: 12px;
    }
    
    /* Table styling */
    .dataframe {
        border: none !important;
    }
    
    .dataframe th {
        background: var(--bg-tertiary) !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        font-size: 11px !important;
        letter-spacing: 0.5px !important;
    }
    
    .dataframe td {
        background: var(--bg-secondary) !important;
        border-color: var(--border) !important;
    }
    
    /* Tabs override */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--bg-secondary);
        border-radius: 8px;
        padding: 4px;
        border: 1px solid var(--border);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        color: var(--text-secondary);
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--accent) !important;
        color: white !important;
    }
    
    /* Button overrides */
    .stButton > button {
        background: var(--bg-tertiary);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text-primary);
        font-weight: 500;
        padding: 8px 16px;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background: var(--accent);
        border-color: var(--accent);
    }
    
    .stButton > button[kind="primary"] {
        background: var(--accent);
        border-color: var(--accent);
    }
    
    /* Input overrides */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ==================== HELPER FUNCTIONS ====================

def get_videos():
    """Get list of generated videos"""
    videos = []
    if OUT_DIR.exists():
        for f in sorted(OUT_DIR.glob("*.mp4"), reverse=True):
            stat = f.stat()
            videos.append({
                "file": f.name,
                "path": str(f),
                "size_mb": round(stat.st_size / 1024 / 1024, 1),
                "created": datetime.fromtimestamp(stat.st_mtime),
                "thumbnail": str(f) + ".jpg" if (Path(str(f) + ".jpg")).exists() else None
            })
    return videos


def get_scripts():
    """Get list of script files"""
    scripts = []
    if SCRIPTS_DIR.exists():
        for f in sorted(SCRIPTS_DIR.glob("*.json"), reverse=True):
            try:
                with open(f) as file:
                    data = json.load(file)
                    scripts.append({
                        "file": f.name,
                        "path": str(f),
                        "topic": data.get("topic", "Unknown"),
                        "characters": data.get("characters", []),
                        "created": datetime.fromtimestamp(f.stat().st_mtime)
                    })
            except:
                pass
    return scripts


def get_queue():
    """Get pending queue items"""
    if QUEUE_FILE.exists():
        try:
            with open(QUEUE_FILE) as f:
                return json.load(f)
        except:
            return []
    return []


def save_queue(queue):
    """Save queue to file"""
    QUEUE_FILE.parent.mkdir(exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2, default=str)


def get_topics(niche="tech"):
    """Get topics for a niche"""
    topics_file = NICHES_DIR / niche / "topics.json"
    if topics_file.exists():
        with open(topics_file) as f:
            data = json.load(f)
            return data.get("topics", [])
    return []


def save_topics(topics, niche="tech"):
    """Save topics to file"""
    topics_file = NICHES_DIR / niche / "topics.json"
    topics_file.parent.mkdir(parents=True, exist_ok=True)
    with open(topics_file, "w") as f:
        json.dump({"niche": niche, "topics": topics}, f, indent=2)


def get_system_stats():
    """Get system resource usage"""
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu": cpu,
        "memory_percent": memory.percent,
        "memory_used_gb": round(memory.used / 1024**3, 1),
        "memory_total_gb": round(memory.total / 1024**3, 1),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / 1024**3, 1)
    }


def get_folder_size(path):
    """Get total size of a folder"""
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def format_size(bytes_size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def get_characters():
    """Get available character duos"""
    characters = []
    if CHARACTERS_DIR.exists():
        for d in CHARACTERS_DIR.iterdir():
            if d.is_dir():
                config_file = d / "config.json"
                if config_file.exists():
                    with open(config_file) as f:
                        characters.append(json.load(f))
    return characters


def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PIPELINE_DIR)
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)


# ==================== SIDEBAR NAVIGATION ====================

with st.sidebar:
    st.markdown("## 🎬 Video Pipeline")
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["🏠 Home", "📹 Content", "✂️ Editor", "📊 Analytics", "👥 Accounts", "⚙️ Settings", "📋 Logs"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Quick stats in sidebar
    videos = get_videos()
    st.markdown(f"**{len(videos)}** videos generated")
    
    accounts_data = load_accounts()
    active_accounts = len([a for a in accounts_data.get("accounts", []) if a.get("active", True)])
    st.markdown(f"**{active_accounts}** active accounts")
    
    # System health
    stats = get_system_stats()
    if stats["cpu"] > 80 or stats["memory_percent"] > 80:
        st.warning(f"⚠️ High resource usage")
    else:
        st.success(f"✅ System healthy")
    
    st.markdown("---")
    st.caption("v2.0 • Built with Streamlit")


# ==================== PAGE: HOME ====================

if page == "🏠 Home":
    st.markdown("# Dashboard")
    
    # Quick Actions
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("▶️ Generate Video", use_container_width=True, type="primary"):
            st.session_state["show_generate"] = True
    with col2:
        if st.button("📤 Upload All", use_container_width=True):
            st.info("Running upload for pending videos...")
            output = run_command("python upload_all.py")
            st.code(output[:500])
    with col3:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_home"):
            st.rerun()
    with col4:
        if st.button("📁 Open Folder", use_container_width=True):
            run_command(f"open {OUT_DIR}")
    
    st.markdown("---")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    videos = get_videos()
    today_videos = [v for v in videos if v["created"].date() == datetime.now().date()]
    total_size = sum(v["size_mb"] for v in videos)
    
    with col1:
        st.metric("Total Videos", len(videos), f"+{len(today_videos)} today")
    with col2:
        st.metric("Storage Used", f"{total_size/1024:.1f} GB", f"{len(videos) * COST_PER_VIDEO:.2f} cost")
    with col3:
        queue = get_queue()
        st.metric("In Queue", len(queue))
    with col4:
        topics = get_topics()
        unused = len([t for t in topics if not t.get("used", False)])
        st.metric("Topics Left", unused, f"of {len(topics)}")
    
    st.markdown("---")
    
    # Recent videos
    st.markdown("### Recent Videos")
    
    if videos:
        cols = st.columns(4)
        for i, video in enumerate(videos[:8]):
            with cols[i % 4]:
                with st.container():
                    # Thumbnail or placeholder
                    if video["thumbnail"] and Path(video["thumbnail"]).exists():
                        st.image(video["thumbnail"], use_container_width=True)
                    else:
                        st.markdown(
                            f'<div style="aspect-ratio:9/16;background:#252525;border-radius:8px;display:flex;align-items:center;justify-content:center;">🎬</div>',
                            unsafe_allow_html=True
                        )
                    
                    st.caption(video["file"][:25] + "...")
                    st.caption(f"{video['size_mb']} MB • {video['created'].strftime('%b %d')}")
    else:
        st.info("No videos generated yet. Click 'Generate Video' to get started!")
    
    # Generate video modal
    if st.session_state.get("show_generate", False):
        st.markdown("---")
        st.markdown("### Generate New Video")
        
        with st.form("generate_form"):
            topic = st.text_input("Topic", placeholder="What is an API?")
            
            col1, col2 = st.columns(2)
            with col1:
                characters = get_characters()
                char_names = [c.get("duo_name", "Unknown") for c in characters]
                selected_char = st.selectbox("Characters", char_names)
            with col2:
                backgrounds = ["subway_surfers", "minecraft_parkour", "gta_gameplay"]
                selected_bg = st.selectbox("Background", backgrounds)
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Generate", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state["show_generate"] = False
                    st.rerun()
            
            if submitted and topic:
                st.info(f"Generating video: {topic}")
                cmd = f'python auto_generate.py --topic "{topic}" --characters {selected_char}'
                output = run_command(cmd)
                st.code(output[-1000:])
                st.session_state["show_generate"] = False


# ==================== PAGE: CONTENT ====================

elif page == "📹 Content":
    st.markdown("# Content")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📹 Videos", "📋 Queue", "📝 Topics", "📄 Scripts"])
    
    # --- Videos Tab ---
    with tab1:
        videos = get_videos()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{len(videos)} videos** • {sum(v['size_mb'] for v in videos)/1024:.1f} GB total")
        with col2:
            if st.button("🔄", key="refresh_videos"):
                st.rerun()
        
        if videos:
            # Filter options
            with st.expander("Filters"):
                col1, col2 = st.columns(2)
                with col1:
                    date_filter = st.selectbox("Date", ["All", "Today", "This Week", "This Month"])
                with col2:
                    sort_by = st.selectbox("Sort", ["Newest", "Oldest", "Largest", "Smallest"])
            
            # Apply filters
            filtered_videos = videos.copy()
            if date_filter == "Today":
                filtered_videos = [v for v in videos if v["created"].date() == datetime.now().date()]
            elif date_filter == "This Week":
                week_ago = datetime.now() - timedelta(days=7)
                filtered_videos = [v for v in videos if v["created"] > week_ago]
            elif date_filter == "This Month":
                month_ago = datetime.now() - timedelta(days=30)
                filtered_videos = [v for v in videos if v["created"] > month_ago]
            
            if sort_by == "Oldest":
                filtered_videos = sorted(filtered_videos, key=lambda x: x["created"])
            elif sort_by == "Largest":
                filtered_videos = sorted(filtered_videos, key=lambda x: x["size_mb"], reverse=True)
            elif sort_by == "Smallest":
                filtered_videos = sorted(filtered_videos, key=lambda x: x["size_mb"])
            
            # Video list
            for video in filtered_videos[:20]:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.markdown(f"**{video['file']}**")
                        st.caption(f"{video['created'].strftime('%Y-%m-%d %H:%M')} • {video['size_mb']} MB")
                    with col2:
                        if st.button("▶️", key=f"play_{video['file']}"):
                            st.video(video["path"])
                    with col3:
                        if st.button("📤", key=f"upload_{video['file']}"):
                            st.info(f"Uploading {video['file']}...")
                    with col4:
                        if st.button("🗑️", key=f"delete_{video['file']}"):
                            Path(video["path"]).unlink()
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("No videos yet")
    
    # --- Queue Tab ---
    with tab2:
        queue = get_queue()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{len(queue)} items** in queue")
        with col2:
            if st.button("Clear Queue", key="clear_queue"):
                save_queue([])
                st.rerun()
        
        if queue:
            for i, item in enumerate(queue):
                with st.container():
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.markdown(f"**{item.get('topic', 'Unknown')}**")
                        st.caption(f"Added: {item.get('added_at', 'Unknown')}")
                    with col2:
                        status = item.get("status", "pending")
                        if status == "pending":
                            st.markdown('<span class="pill pill-warning">Pending</span>', unsafe_allow_html=True)
                        elif status == "processing":
                            st.markdown('<span class="pill pill-neutral">Processing</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="pill pill-success">Done</span>', unsafe_allow_html=True)
                    with col3:
                        if st.button("❌", key=f"remove_queue_{i}"):
                            queue.pop(i)
                            save_queue(queue)
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("Queue is empty")
        
        # Add to queue
        with st.expander("Add to Queue"):
            new_topic = st.text_input("Topic", key="new_queue_topic")
            if st.button("Add", key="add_to_queue"):
                if new_topic:
                    queue.append({
                        "topic": new_topic,
                        "added_at": datetime.now().isoformat(),
                        "status": "pending"
                    })
                    save_queue(queue)
                    st.success(f"Added: {new_topic}")
                    st.rerun()
    
    # --- Topics Tab ---
    with tab3:
        niche = st.selectbox("Niche", ["tech", "finance", "gaming", "motivation"])
        topics = get_topics(niche)
        
        used = len([t for t in topics if t.get("used", False)])
        unused = len(topics) - used
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Topics", len(topics))
        with col2:
            st.metric("Used", used)
        with col3:
            st.metric("Available", unused)
        
        st.markdown("---")
        
        # Topics list
        show_used = st.checkbox("Show used topics", value=False)
        
        filtered_topics = topics if show_used else [t for t in topics if not t.get("used", False)]
        
        for i, topic in enumerate(filtered_topics[:30]):
            col1, col2 = st.columns([5, 1])
            with col1:
                topic_text = topic.get("topic", topic) if isinstance(topic, dict) else topic
                if isinstance(topic, dict) and topic.get("used"):
                    st.markdown(f"~~{topic_text}~~")
                else:
                    st.markdown(topic_text)
            with col2:
                if st.button("🎬", key=f"gen_topic_{i}", help="Generate video for this topic"):
                    st.info(f"Would generate: {topic_text}")
        
        # Add topic
        st.markdown("---")
        with st.expander("Add Topics"):
            new_topics = st.text_area("Enter topics (one per line)")
            if st.button("Add Topics"):
                if new_topics:
                    for line in new_topics.strip().split("\n"):
                        if line.strip():
                            topics.append({"topic": line.strip(), "used": False})
                    save_topics(topics, niche)
                    st.success(f"Added {len(new_topics.strip().split(chr(10)))} topics")
                    st.rerun()
    
    # --- Scripts Tab ---
    with tab4:
        st.markdown("### Generated Scripts")
        
        scripts = get_scripts()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{len(scripts)} scripts** generated")
        with col2:
            if st.button("🔄", key="refresh_scripts"):
                st.rerun()
        
        if scripts:
            for script in scripts[:20]:
                with st.expander(f"📄 {script['topic'][:50]}... ({script['created'].strftime('%b %d')})"):
                    st.caption(f"File: {script['file']}")
                    st.caption(f"Characters: {', '.join(script.get('characters', []))}")
                    
                    # Load and show script content
                    try:
                        with open(script['path']) as f:
                            content = json.load(f)
                        
                        st.markdown("**Dialogue:**")
                        for line in content.get("script", [])[:5]:
                            char = line.get("character", "?")
                            text = line.get("line", "")[:100]
                            st.markdown(f"**{char}:** {text}...")
                        
                        if len(content.get("script", [])) > 5:
                            st.caption(f"... and {len(content['script']) - 5} more lines")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("📋 Copy JSON", key=f"copy_{script['file']}"):
                                st.code(json.dumps(content, indent=2)[:2000])
                        with col2:
                            if st.button("🗑️ Delete", key=f"del_script_{script['file']}"):
                                Path(script['path']).unlink()
                                st.rerun()
                    except Exception as e:
                        st.error(f"Could not load script: {e}")
        else:
            st.info("No scripts generated yet")


# ==================== PAGE: EDITOR ====================

elif page == "✂️ Editor":
    st.markdown("# Video Editor")
    st.markdown("Edit videos using natural language prompts powered by AI + FFmpeg.")
    
    # Import video editor
    try:
        from video_editor import edit_video, get_video_info, get_edit_history, PRESETS, EDITED_DIR
        editor_available = True
    except ImportError:
        editor_available = False
        st.warning("Video editor module not found. Make sure video_editor.py exists.")
    
    if editor_available:
        # Video selector
        col1, col2 = st.columns([2, 1])
        
        with col1:
            all_videos = sorted(OUT_DIR.glob("*_final.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
            edited_videos = sorted(EDITED_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True) if EDITED_DIR.exists() else []
            
            video_options = ["Select a video..."]
            video_options += [f"📹 {v.name}" for v in all_videos[:20]]
            if edited_videos:
                video_options += ["---"]
                video_options += [f"✂️ {v.name}" for v in edited_videos[:10]]
            
            selected = st.selectbox("Select Video", video_options)
        
        with col2:
            if selected and selected != "Select a video..." and selected != "---":
                video_name = selected.split(" ", 1)[1] if " " in selected else selected
                if selected.startswith("✂️"):
                    video_path = EDITED_DIR / video_name
                else:
                    video_path = OUT_DIR / video_name
                
                if video_path.exists():
                    info = get_video_info(video_path)
                    st.metric("Duration", f"{info.get('duration', 0):.1f}s")
                    st.caption(f"{info.get('width')}x{info.get('height')} • {info.get('size_mb', 0):.1f}MB")
        
        st.markdown("---")
        
        if selected and selected != "Select a video..." and selected != "---":
            video_name = selected.split(" ", 1)[1] if " " in selected else selected
            if selected.startswith("✂️"):
                video_path = EDITED_DIR / video_name
            else:
                video_path = OUT_DIR / video_name
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Quick Presets")
                preset_cols = st.columns(2)
                
                preset_list = list(PRESETS.items())
                for i, (key, desc) in enumerate(preset_list[:8]):
                    with preset_cols[i % 2]:
                        if st.button(desc[:25] + "..." if len(desc) > 25 else desc, key=f"preset_{key}", use_container_width=True):
                            st.session_state['edit_prompt'] = desc
            
            with col2:
                st.markdown("#### Custom Edit")
                prompt = st.text_area(
                    "Describe your edit",
                    value=st.session_state.get('edit_prompt', ''),
                    placeholder="e.g., 'Add text FOLLOW at bottom for last 3 seconds'",
                    height=100
                )
                
                if 'edit_prompt' in st.session_state:
                    del st.session_state['edit_prompt']
            
            st.markdown("---")
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                dry_run = st.button("🔍 Preview Command", use_container_width=True, disabled=not prompt)
            
            with btn_col2:
                execute = st.button("✂️ Apply Edit", use_container_width=True, type="primary", disabled=not prompt)
            
            if dry_run and prompt:
                with st.spinner("Generating FFmpeg command..."):
                    result = edit_video(str(video_path), prompt, dry_run=True)
                
                if result.get("success"):
                    st.success("**Command preview:**")
                    st.code(" ".join(result.get("command", [])), language="bash")
                    st.info(f"📝 {result.get('description', '')}")
                else:
                    st.error(f"Error: {result.get('error')}")
            
            if execute and prompt:
                with st.spinner("Applying edit... This may take a moment."):
                    result = edit_video(str(video_path), prompt)
                
                if result.get("success"):
                    st.success("✅ Edit complete!")
                    st.write(f"**Output:** `{result.get('output_path')}`")
                    st.write(f"**Size:** {result.get('size_mb', 0):.1f} MB")
                    
                    output_path = Path(result.get('output_path'))
                    if output_path.exists():
                        st.video(str(output_path))
                else:
                    st.error(f"❌ Edit failed: {result.get('error')}")
            
            st.markdown("---")
            st.markdown("#### Video Preview")
            if video_path.exists():
                st.video(str(video_path))
        else:
            st.info("👆 Select a video to start editing")
        
        # Edit history
        st.markdown("---")
        st.markdown("### Edit History")
        
        history = get_edit_history()
        if history:
            history_df = pd.DataFrame(history[-10:][::-1])
            if 'timestamp' in history_df.columns:
                history_df['timestamp'] = pd.to_datetime(history_df['timestamp']).dt.strftime('%m/%d %H:%M')
            st.dataframe(history_df[['timestamp', 'input', 'prompt', 'output']], use_container_width=True)
        else:
            st.caption("No edits yet.")
    else:
        st.info("The video editor requires the `video_editor.py` module. Check that it exists in the pipeline directory.")


# ==================== PAGE: ANALYTICS ====================

elif page == "📊 Analytics":
    st.markdown("# Analytics")
    
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "🏆 Top Content", "⏰ Best Times"])
    
    with tab1:
        videos = get_videos()
        
        # Videos over time
        if videos:
            df = pd.DataFrame(videos)
            df["date"] = df["created"].dt.date
            daily_counts = df.groupby("date").size().reset_index(name="count")
            
            fig = px.bar(
                daily_counts, x="date", y="count",
                title="Videos Generated Per Day",
                color_discrete_sequence=["#6366f1"]
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#a1a1aa",
                xaxis_title="",
                yaxis_title="Videos"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_per_day = len(videos) / max(len(daily_counts), 1)
                st.metric("Avg Videos/Day", f"{avg_per_day:.1f}")
            with col2:
                total_cost = len(videos) * COST_PER_VIDEO
                st.metric("Total Cost", f"${total_cost:.2f}")
            with col3:
                avg_size = sum(v["size_mb"] for v in videos) / max(len(videos), 1)
                st.metric("Avg Size", f"{avg_size:.1f} MB")
        else:
            st.info("No data yet. Generate some videos to see analytics!")
    
    with tab2:
        st.markdown("### Top Performing Content")
        st.info("Connect YouTube/TikTok analytics to see real performance data")
        
        # Placeholder for when analytics is connected
        st.markdown("#### Coming Soon")
        st.markdown("- Views by video")
        st.markdown("- Engagement rates")
        st.markdown("- Best performing topics")
    
    with tab3:
        st.markdown("### Best Posting Times")
        st.info("Connect analytics to see optimal posting times")
        
        # Placeholder heatmap
        st.markdown("#### Recommended Times")
        st.markdown("- **TikTok:** 7-9 AM, 12-3 PM, 7-9 PM")
        st.markdown("- **YouTube Shorts:** 2-4 PM, 6-9 PM")
        st.markdown("- **Instagram:** 11 AM-1 PM, 7-9 PM")


# ==================== PAGE: ACCOUNTS ====================

elif page == "👥 Accounts":
    st.markdown("# Accounts")
    
    accounts_data = load_accounts()
    accounts = accounts_data.get("accounts", [])
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{len(accounts)} accounts** configured")
    with col2:
        if st.button("➕ Add Account", key="add_account_btn"):
            st.session_state["show_add_account"] = True
    
    st.markdown("---")
    
    # Account cards
    for account in accounts:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                status = "🟢" if account.get("active", True) else "🔴"
                st.markdown(f"### {status} {account.get('name', 'Unnamed')}")
                st.caption(f"ID: {account.get('id')} • Niche: {account.get('niche')}")
            
            with col2:
                platforms = account.get("platforms", {})
                platform_status = []
                for p, config in platforms.items():
                    if config.get("enabled"):
                        platform_status.append(f"✅ {p.title()}")
                    else:
                        platform_status.append(f"❌ {p.title()}")
                st.markdown(" • ".join(platform_status))
            
            with col3:
                if st.button("Toggle", key=f"toggle_{account['id']}"):
                    toggle_account(account["id"])
                    st.rerun()
                if st.button("Delete", key=f"delete_{account['id']}"):
                    delete_account(account["id"])
                    st.rerun()
            
            # Expanded details
            with st.expander("Details"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Schedule**")
                    schedule = account.get("schedule", {})
                    st.write(f"Timezone: {schedule.get('timezone', 'Not set')}")
                    for slot in schedule.get("slots", []):
                        st.write(f"• {slot.get('time')} → {', '.join(slot.get('platforms', []))}")
                with col2:
                    st.markdown("**Content**")
                    content = account.get("content", {})
                    st.write(f"Characters: {', '.join(content.get('characters', []))}")
                    st.write(f"Backgrounds: {', '.join(content.get('backgrounds', []))}")
            
            st.markdown("---")
    
    # Add account form
    if st.session_state.get("show_add_account", False):
        st.markdown("### Add New Account")
        
        with st.form("add_account_form"):
            name = st.text_input("Account Name")
            niche = st.selectbox("Niche", ["tech", "finance", "gaming", "motivation"])
            
            st.markdown("**Platforms**")
            col1, col2, col3 = st.columns(3)
            with col1:
                enable_tiktok = st.checkbox("TikTok", value=True)
            with col2:
                enable_youtube = st.checkbox("YouTube", value=True)
            with col3:
                enable_instagram = st.checkbox("Instagram", value=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Create", type="primary"):
                    if name:
                        new_account = create_account(
                            name=name,
                            niche=niche,
                            platforms={
                                "tiktok": {"enabled": enable_tiktok, "credentials": f"credentials/tiktok_{name.lower()}.json"},
                                "youtube": {"enabled": enable_youtube, "credentials": f"credentials/youtube_{name.lower()}.json"},
                                "instagram": {"enabled": enable_instagram, "credentials": f"credentials/instagram_{name.lower()}.json"},
                            },
                            characters=["peter", "stewie"],
                            backgrounds=["subway_surfers"],
                            schedule={
                                "timezone": "America/Toronto",
                                "slots": [{"time": "10:00", "platforms": ["tiktok", "youtube", "instagram"]}],
                                "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                            }
                        )
                        st.success(f"Created account: {new_account['id']}")
                        st.session_state["show_add_account"] = False
                        st.rerun()
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state["show_add_account"] = False
                    st.rerun()


# ==================== PAGE: SETTINGS ====================

elif page == "⚙️ Settings":
    st.markdown("# Settings")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎭 Characters", "🎮 Backgrounds", "⏰ Schedule", "💾 Storage", "🔧 Advanced"])
    
    # --- Characters ---
    with tab1:
        st.markdown("### Character Duos")
        
        characters = get_characters()
        
        for char in characters:
            with st.expander(f"🎭 {char.get('duo_name', 'Unknown')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Character 1**")
                    c1 = char.get("char1", {})
                    st.write(f"Name: {c1.get('display_name', 'Unknown')}")
                    st.write(f"Voice ID: {c1.get('voice_id', 'N/A')[:20]}...")
                
                with col2:
                    st.markdown("**Character 2**")
                    c2 = char.get("char2", {})
                    st.write(f"Name: {c2.get('display_name', 'Unknown')}")
                    st.write(f"Voice ID: {c2.get('voice_id', 'N/A')[:20]}...")
        
        if not characters:
            st.info("No characters configured. Add character folders to /characters/")
    
    # --- Backgrounds ---
    with tab2:
        st.markdown("### Background Videos")
        
        if BACKGROUNDS_DIR.exists():
            backgrounds = [d.name for d in BACKGROUNDS_DIR.iterdir() if d.is_dir()]
            for bg in backgrounds:
                bg_path = BACKGROUNDS_DIR / bg
                videos = list(bg_path.glob("*.mp4"))
                st.markdown(f"**{bg}** — {len(videos)} videos")
        else:
            st.info("No backgrounds configured")
    
    # --- Schedule ---
    with tab3:
        st.markdown("### Upload Schedule")
        
        accounts_data = load_accounts()
        
        for account in accounts_data.get("accounts", []):
            with st.expander(f"⏰ {account.get('name', 'Unknown')}"):
                schedule = account.get("schedule", {})
                
                timezone = st.selectbox(
                    "Timezone",
                    ["America/Toronto", "America/New_York", "America/Los_Angeles", "UTC"],
                    index=0,
                    key=f"tz_{account['id']}"
                )
                
                st.markdown("**Time Slots**")
                for i, slot in enumerate(schedule.get("slots", [])):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.text_input("Time", value=slot.get("time", ""), key=f"slot_time_{account['id']}_{i}")
                    with col2:
                        st.multiselect(
                            "Platforms",
                            ["tiktok", "youtube", "instagram"],
                            default=slot.get("platforms", []),
                            key=f"slot_plat_{account['id']}_{i}"
                        )
    
    # --- Storage ---
    with tab4:
        st.markdown("### Storage Management")
        
        stats = get_system_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Disk Free", f"{stats['disk_free_gb']} GB")
        with col2:
            st.metric("Disk Used", f"{stats['disk_percent']}%")
        with col3:
            st.metric("Memory", f"{stats['memory_percent']}%")
        
        st.markdown("---")
        
        st.markdown("**Folder Sizes**")
        folders = [
            ("Videos", OUT_DIR),
            ("Audio", AUDIO_DIR),
            ("Scripts", SCRIPTS_DIR),
        ]
        
        for name, path in folders:
            size = get_folder_size(path)
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(name)
            with col2:
                st.markdown(format_size(size))
            with col3:
                if st.button("Clear", key=f"clear_{name}"):
                    if path.exists():
                        for f in path.glob("*"):
                            if f.is_file():
                                f.unlink()
                        st.success(f"Cleared {name}")
                        st.rerun()
        
        st.markdown("---")
        
        # Auto cleanup settings
        st.markdown("### Auto Cleanup")
        retention_days = st.slider("Keep videos for (days)", 7, 90, 14)
        if st.button("Run Cleanup Now"):
            cutoff = datetime.now() - timedelta(days=retention_days)
            deleted = 0
            if OUT_DIR.exists():
                for f in OUT_DIR.glob("*.mp4"):
                    if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink()
                        deleted += 1
            st.success(f"Deleted {deleted} old videos")
    
    # --- Advanced ---
    with tab5:
        st.markdown("### Advanced Settings")
        
        st.markdown("**API Keys**")
        st.info("API keys are stored in config.json and .env files")
        
        config_file = PIPELINE_DIR / "config.json"
        if config_file.exists():
            st.success("✅ config.json found")
        else:
            st.warning("⚠️ config.json not found")
        
        env_file = PIPELINE_DIR / ".env"
        if env_file.exists():
            st.success("✅ .env found")
        else:
            st.warning("⚠️ .env not found")
        
        st.markdown("---")
        
        st.markdown("**Commands**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Restart Scheduler", use_container_width=True):
                output = run_command("pkill -f scheduler.py; nohup python scheduler.py &")
                st.code(output or "Scheduler restarted")
        with col2:
            if st.button("🧪 Test Pipeline", use_container_width=True):
                output = run_command("python pipeline.py --help")
                st.code(output[:500])
        
        st.markdown("---")
        
        st.markdown("**Logs**")
        
        log_files = list(LOGS_DIR.glob("*.log")) if LOGS_DIR.exists() else []
        if log_files:
            selected_log = st.selectbox("Select log file", [f.name for f in log_files])
            if selected_log:
                log_path = LOGS_DIR / selected_log
                if log_path.exists():
                    with open(log_path) as f:
                        content = f.read()[-5000:]  # Last 5000 chars
                    st.code(content)
        else:
            st.info("No log files found")
        
        # Debug screenshots
        if DEBUG_DIR.exists():
            screenshots = list(DEBUG_DIR.glob("*.png"))
            if screenshots:
                st.markdown("**Debug Screenshots**")
                selected_ss = st.selectbox("Select screenshot", [f.name for f in sorted(screenshots, reverse=True)[:10]])
                if selected_ss:
                    st.image(str(DEBUG_DIR / selected_ss))


# ==================== PAGE: LOGS ====================

elif page == "📋 Logs":
    st.markdown("# Logs & Monitoring")
    
    LIVE_LOG_FILE = LOGS_DIR / "pipeline.log"
    ERROR_LOG_FILE = LOGS_DIR / "errors.json"
    
    tab1, tab2, tab3, tab4 = st.tabs(["📺 Live Output", "🚨 Errors", "📸 Screenshots", "🔴 System Monitor"])
    
    # --- Live Output ---
    with tab1:
        st.markdown("### Live Pipeline Output")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key="refresh_logs"):
                st.rerun()
            if st.button("🗑️ Clear Log"):
                if LIVE_LOG_FILE.exists():
                    LIVE_LOG_FILE.write_text("")
                st.success("Log cleared!")
                st.rerun()
        
        if LIVE_LOG_FILE.exists():
            log_content = LIVE_LOG_FILE.read_text()
            if log_content.strip():
                lines = log_content.strip().split('\n')
                recent_lines = lines[-100:]
                st.code('\n'.join(recent_lines), language="text")
                st.caption(f"Showing last {len(recent_lines)} of {len(lines)} lines")
            else:
                st.info("Log is empty.")
        else:
            st.info("No log file yet. Run the pipeline to see output.")
        
        st.markdown("---")
        st.markdown("**Tip:** Run with logging:")
        st.code(f"python auto_generate.py 2>&1 | tee {LIVE_LOG_FILE}")
    
    # --- Errors ---
    with tab2:
        st.markdown("### Error Log")
        
        def load_error_log():
            try:
                if ERROR_LOG_FILE.exists():
                    return json.loads(ERROR_LOG_FILE.read_text())
                return []
            except:
                return []
        
        def save_error_log(errors):
            ERROR_LOG_FILE.write_text(json.dumps(errors, indent=2, default=str))
        
        errors = load_error_log()
        
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
            error_filter = st.selectbox("Filter by type", ["All"] + list(set(e.get("type", "unknown") for e in errors)))
            
            filtered_errors = errors if error_filter == "All" else [e for e in errors if e.get("type") == error_filter]
            filtered_errors = sorted(filtered_errors, key=lambda x: x.get("timestamp", ""), reverse=True)
            
            for error in filtered_errors[:15]:
                timestamp = datetime.fromisoformat(error.get("timestamp", "")).strftime("%Y-%m-%d %H:%M")
                error_type = error.get("type", "unknown")
                message = error.get("message", "No message")
                
                with st.expander(f"🔴 [{error_type}] {timestamp}"):
                    st.write(f"**Message:** {message}")
                    if error.get("details"):
                        st.json(error.get("details"))
            
            if st.button("🗑️ Clear All Errors"):
                save_error_log([])
                st.rerun()
        else:
            st.success("✅ No errors logged!")
    
    # --- Screenshots ---
    with tab3:
        st.markdown("### Debug Screenshots")
        
        if DEBUG_DIR.exists():
            screenshots = sorted(DEBUG_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if screenshots:
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("🗑️ Clear Screenshots"):
                        for f in screenshots:
                            f.unlink()
                        st.rerun()
                
                selected = st.selectbox("Select screenshot", [f.name for f in screenshots[:20]])
                if selected:
                    st.image(str(DEBUG_DIR / selected))
                    st.caption(f"Taken: {datetime.fromtimestamp((DEBUG_DIR / selected).stat().st_mtime).strftime('%Y-%m-%d %H:%M')}")
            else:
                st.info("No screenshots yet")
        else:
            st.info("Debug directory not found")
    
    # --- System Monitor ---
    with tab4:
        st.markdown("### Real-Time System Monitor")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Refresh Stats", key="refresh_system"):
                st.rerun()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            st.metric("🔥 CPU", f"{cpu_percent:.1f}%")
            st.progress(min(cpu_percent / 100, 1.0))
        
        with col2:
            memory = psutil.virtual_memory()
            st.metric("🧠 Memory", f"{memory.percent:.1f}%")
            st.progress(min(memory.percent / 100, 1.0))
            st.caption(f"{memory.used / 1024**3:.1f} / {memory.total / 1024**3:.1f} GB")
        
        with col3:
            disk = shutil.disk_usage(PIPELINE_DIR)
            disk_percent = (disk.used / disk.total) * 100
            st.metric("💿 Disk", f"{disk_percent:.1f}%")
            st.progress(min(disk_percent / 100, 1.0))
            st.caption(f"{disk.free / 1024**3:.1f} GB free")
        
        with col4:
            try:
                net = psutil.net_io_counters()
                total_mb = (net.bytes_sent + net.bytes_recv) / 1024**2
                st.metric("🌐 Network", f"{total_mb:.0f} MB")
                st.caption("Total transferred")
            except:
                st.metric("🌐 Network", "N/A")
        
        st.markdown("---")
        
        # Running processes related to pipeline
        st.markdown("### Running Processes")
        
        pipeline_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(x in cmdline.lower() for x in ['pipeline', 'scheduler', 'upload', 'streamlit']):
                    pipeline_processes.append({
                        "PID": proc.info['pid'],
                        "Name": proc.info['name'],
                        "CPU%": f"{proc.info['cpu_percent']:.1f}",
                        "Mem%": f"{proc.info['memory_percent']:.1f}",
                    })
            except:
                pass
        
        if pipeline_processes:
            st.dataframe(pd.DataFrame(pipeline_processes), use_container_width=True)
        else:
            st.info("No pipeline processes running")


# ==================== FOOTER ====================

st.markdown("---")
st.caption("Video Pipeline Dashboard v2.0 • Built with ❤️")
