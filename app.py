"""
TeachCheck AI - Streamlit Dashboard
"Don't just watch the lesson. Verify what it teaches."

An AI-powered educational video consistency checker that detects discrepancies
between what instructors say, what appears on screen, and what the code does.
Powered by Google Gemma 4 (gemma-4-26b-a4b-it) via the Google Gen AI SDK.
"""

import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modules.video_processor import (
    validate_video_file,
    get_video_metadata,
    extract_representative_frames,
    extract_audio_from_video,
    VideoProcessingError
)
from modules.audio_transcriber import (
    transcribe_audio,
    format_transcript_as_text,
    parse_manual_transcript,
    TranscriptionError
)
from modules.gemma_analyzer import (
    analyze_lecture_with_gemma,
    get_demo_analysis_data,
    GEMMA_MODEL_ID,
    GemmaAPIError,
    GemmaParseError
)
from modules.report_generator import (
    get_summary_metrics,
    generate_json_report
)

# Page configuration
st.set_page_config(
    page_title="TeachCheck AI | Educational Video Consistency Checker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dark Theme CSS
CUSTOM_CSS = """
<style>
/* Main app dark theme */
.stApp {
    background: radial-gradient(circle at 15% 15%, #111827 0%, #0a0e1a 100%);
    color: #F3F4F6;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    color: #F9FAFB !important;
    font-weight: 700;
}

/* Header Banner */
.hero-container {
    background: linear-gradient(135deg, rgba(30, 27, 75, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.4);
}

.hero-title {
    font-size: 2.3rem;
    font-weight: 800;
    background: linear-gradient(90deg, #A78BFA 0%, #60A5FA 50%, #38BDF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 6px;
    letter-spacing: -0.5px;
}

.hero-tagline {
    font-size: 1.15rem;
    color: #94A3B8;
    font-weight: 500;
    margin-bottom: 10px;
}

.hero-description {
    color: #CBD5E1;
    font-size: 0.95rem;
    line-height: 1.5;
    max-width: 900px;
}

/* Metric Cards */
.metric-card {
    background: rgba(17, 24, 39, 0.85);
    border: 1px solid rgba(75, 85, 99, 0.4);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(139, 92, 246, 0.6);
}

.metric-val {
    font-size: 2.1rem;
    font-weight: 800;
    margin-bottom: 4px;
}
.metric-lbl {
    font-size: 0.82rem;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

/* Findings Card */
.finding-box {
    background: rgba(17, 24, 39, 0.85);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 18px;
    border-left: 5px solid #4B5563;
    border-top: 1px solid rgba(75, 85, 99, 0.3);
    border-right: 1px solid rgba(75, 85, 99, 0.3);
    border-bottom: 1px solid rgba(75, 85, 99, 0.3);
}

.finding-box-confirmed {
    border-left-color: #EF4444 !important;
    background: linear-gradient(90deg, rgba(239, 68, 68, 0.08) 0%, rgba(17, 24, 39, 0.95) 100%);
}
.finding-box-potential {
    border-left-color: #F59E0B !important;
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.08) 0%, rgba(17, 24, 39, 0.95) 100%);
}
.finding-box-verified {
    border-left-color: #10B981 !important;
    background: linear-gradient(90deg, rgba(16, 185, 129, 0.08) 0%, rgba(17, 24, 39, 0.95) 100%);
}
.finding-box-insufficient {
    border-left-color: #6B7280 !important;
    background: linear-gradient(90deg, rgba(107, 114, 128, 0.08) 0%, rgba(17, 24, 39, 0.95) 100%);
}

/* Badges */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-confirmed { background-color: #7F1D1D; color: #FCA5A5; border: 1px solid #EF4444; }
.badge-potential { background-color: #78350F; color: #FDE68A; border: 1px solid #F59E0B; }
.badge-verified  { background-color: #064E3B; color: #A7F3D0; border: 1px solid #10B981; }
.badge-insufficient { background-color: #1F2937; color: #D1D5DB; border: 1px solid #6B7280; }

/* Section Header */
.section-header {
    border-bottom: 2px solid rgba(139, 92, 246, 0.2);
    padding-bottom: 8px;
    margin-top: 24px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: #0D121F;
    border-right: 1px solid rgba(75, 85, 99, 0.3);
}

/* Frame thumbnail */
.frame-thumb-box {
    background: #111827;
    border-radius: 8px;
    padding: 8px;
    border: 1px solid rgba(75, 85, 99, 0.4);
    text-align: center;
    margin-bottom: 10px;
}
.frame-thumb-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #94A3B8;
    margin-top: 4px;
}

/* Tab styling and contrast */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    height: 44px;
    white-space: pre-wrap;
    background-color: rgba(31, 41, 55, 0.5);
    border: 1px solid rgba(75, 85, 99, 0.3);
    border-radius: 8px 8px 0px 0px;
    padding: 8px 16px;
    color: #94A3B8;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background-color: rgba(139, 92, 246, 0.2) !important;
    color: #C4B5FD !important;
    border-color: rgba(139, 92, 246, 0.5) !important;
    border-bottom: 3px solid #8B5CF6 !important;
}

/* Code snippet styling */
code {
    background: rgba(30, 41, 59, 0.8) !important;
    color: #38BDF8 !important;
    border-radius: 4px !important;
    padding: 2px 6px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    """Initializes persistent application session variables."""
    env_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if env_key == "your_gemini_api_key_here":
        env_key = ""
    if "api_key" not in st.session_state:
        st.session_state.api_key = env_key
    if "api_key_override" not in st.session_state:
        st.session_state.api_key_override = ""
    if "video_path" not in st.session_state:
        st.session_state.video_path = None
    if "video_meta" not in st.session_state:
        st.session_state.video_meta = None
    if "extracted_frames" not in st.session_state:
        st.session_state.extracted_frames = []
    if "transcript_segments" not in st.session_state:
        st.session_state.transcript_segments = []
    if "manual_transcript_text" not in st.session_state:
        st.session_state.manual_transcript_text = ""
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "is_demo_mode" not in st.session_state:
        st.session_state.is_demo_mode = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0


init_session_state()


# ==========================================
# SIDEBAR: Configuration & Navigation
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ System Configuration")
    st.markdown(
        f"""
        <div style="background: rgba(139, 92, 246, 0.1); border: 1px solid #8B5CF6; border-radius: 10px; padding: 12px; margin-bottom: 16px;">
            <div style="font-size: 0.75rem; color: #A78BFA; font-weight: 700;">REASONING ENGINE</div>
            <div style="font-size: 1.05rem; font-weight: 800; color: #FFFFFF;">Google Gemma 4</div>
            <div style="font-size: 0.8rem; color: #94A3B8; font-family: monospace;"><code>{GEMMA_MODEL_ID}</code></div>
            <div style="font-size: 0.72rem; color: #38BDF8; margin-top: 4px;">via Google Gen AI SDK & Files API</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # API Key Section
    env_api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    is_env_configured = bool(env_api_key and env_api_key != "your_gemini_api_key_here")

    if is_env_configured:
        st.markdown(
            """
            <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid #10B981; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #10B981; box-shadow: 0 0 8px #10B981;"></span>
                <div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #A7F3D0;">Google Gemini API: Configured</div>
                    <div style="font-size: 0.74rem; color: #94A3B8;">Loaded securely from .env</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("⚙️ Override API Key (Optional)", expanded=False):
            override_input = st.text_input(
                "Custom API Key",
                value=st.session_state.api_key_override,
                type="password",
                placeholder="Paste key to override .env...",
                help="Optional: Override the .env key for this session without modifying local files."
            )
            if override_input.strip():
                st.session_state.api_key_override = override_input.strip()
                st.session_state.api_key = override_input.strip()
                st.caption("✓ Using custom override key.")
            else:
                st.session_state.api_key_override = ""
                st.session_state.api_key = env_api_key
    else:
        st.markdown(
            """
            <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid #F59E0B; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #F59E0B; box-shadow: 0 0 8px #F59E0B;"></span>
                <div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #FDE68A;">Google Gemini API: Not Found in .env</div>
                    <div style="font-size: 0.74rem; color: #94A3B8;">Enter key below or use Demo Mode</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        manual_key_input = st.text_input(
            "Google Gemini API Key",
            value=st.session_state.api_key,
            type="password",
            placeholder="AIzaSy...",
            help="Required for Live Gemma 4 Analysis. Key is kept in session memory only."
        )
        if manual_key_input != st.session_state.api_key:
            st.session_state.api_key = manual_key_input.strip()

    st.markdown("---")
    st.markdown("### 🎯 Operation Mode")
    mode_selection = st.radio(
        "Select Pipeline Mode:",
        ["🚀 Live Gemma 4 Analysis", "🧪 Demo Mode (Curated Evaluation)"],
        index=1 if st.session_state.is_demo_mode else 0,
        help="Live calls Gemma 4 API. Demo mode uses pre-loaded sample analysis without API consumption."
    )
    st.session_state.is_demo_mode = (mode_selection == "🧪 Demo Mode (Curated Evaluation)")

    st.markdown("---")
    st.markdown("### 🎬 Sample Educational Lecture")
    st.markdown(
        "<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px;'>"
        "Load our bundled 30s Python lecture with speech narration and code consistency discrepancies:</div>",
        unsafe_allow_html=True
    )
    sample_video_path = os.path.join(BASE_DIR, "sample_data", "sample_lecture_python.mp4")
    if st.button("📁 Load Sample Lecture Video", use_container_width=True):
        if os.path.exists(sample_video_path):
            st.session_state.video_path = sample_video_path
            st.session_state.video_meta = get_video_metadata(sample_video_path)
            st.session_state.analysis_results = None
            st.session_state.extracted_frames = []
            st.session_state.transcript_segments = []
            st.success("Sample lecture loaded successfully!")
            st.rerun()
        else:
            st.error("Sample video file not found in sample_data directory.")

    st.markdown("---")
    if st.button("🔄 Reset Application State", use_container_width=True):
        st.session_state.video_path = None
        st.session_state.video_meta = None
        st.session_state.extracted_frames = []
        st.session_state.transcript_segments = []
        st.session_state.manual_transcript_text = ""
        st.session_state.analysis_results = None
        st.rerun()

    st.markdown(
        "<div style='font-size: 0.75rem; color: #94A3B8; margin-top: 24px; text-align: center; line-height: 1.4;'>"
        "TeachCheck AI v1.0 • Built for MLH Hackathon<br>CPU INT8 Faster-Whisper + Gemma 4</div>",
        unsafe_allow_html=True
    )


# ==========================================
# MAIN PAGE: Hero Banner
# ==========================================
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">🎯 TeachCheck AI</div>
        <div class="hero-tagline">"Don't just watch the lesson. Verify what it teaches."</div>
        <div class="hero-description">
            TeachCheck AI is an automated video consistency checker for educational programming lectures.
            It scrutinizes educational videos to expose discrepancies between <b>what the instructor says</b>,
            <b>what is visible on screen</b>, and <b>what the programming code actually executes</b>.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if st.session_state.is_demo_mode:
    st.info(
        "🧪 **DEMO MODE ACTIVE**: Analysis will display curated benchmark findings demonstrating "
        "cross-modal consistency detection on the sample Python lecture. Switch to **Live Gemma 4 Analysis** "
        "in the sidebar to query the real model API."
    )


# ==========================================
# STEP 1: Video Upload & Preview
# ==========================================
st.markdown('<div class="section-header"><h3>1. Video Selection & Preview</h3></div>', unsafe_allow_html=True)

col_upload, col_preview = st.columns([1, 1], gap="medium")

with col_upload:
    uploaded_file = st.file_uploader(
        "Upload Educational Lecture Video (MP4, MOV, AVI)",
        type=["mp4", "mov", "avi"],
        help="Upload a programming lecture excerpt (up to 200 MB). Max 6 frames sampled at ~5s intervals."
    )

    if uploaded_file is not None:
        # Save uploaded file to temp directory
        temp_dir = os.path.join(BASE_DIR, "outputs", "uploads")
        os.makedirs(temp_dir, exist_ok=True)
        saved_video_path = os.path.join(temp_dir, uploaded_file.name)

        with open(saved_video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            val_info = validate_video_file(saved_video_path, max_size_mb=200)
            meta = get_video_metadata(saved_video_path)
            st.session_state.video_path = saved_video_path
            st.session_state.video_meta = meta
            st.success(f"Video uploaded: `{uploaded_file.name}` ({val_info['size_mb']} MB)")
        except VideoProcessingError as v_err:
            st.error(f"Video Error: {str(v_err)}")
            st.session_state.video_path = None

    if st.session_state.video_path:
        meta = st.session_state.video_meta or {}
        st.markdown(
            f"""
            <div style="background: rgba(31, 41, 55, 0.7); border-radius: 8px; padding: 12px; margin-top: 10px; font-size: 0.88rem;">
                <b>Selected Video:</b> <code>{os.path.basename(st.session_state.video_path)}</code><br>
                <b>Duration:</b> {meta.get('duration_str', 'N/A')} ({meta.get('duration_sec', 0):.1f}s) &nbsp;|&nbsp;
                <b>Resolution:</b> {meta.get('width', 0)}x{meta.get('height', 0)} &nbsp;|&nbsp;
                <b>FPS:</b> {meta.get('fps', 0):.1f}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='color: #94A3B8; font-size: 0.9rem; padding: 10px 0;'>"
            "Upload a video above or click <b>'📁 Load Sample Lecture Video'</b> in the sidebar to test immediately."
            "</div>",
            unsafe_allow_html=True
        )

with col_preview:
    if st.session_state.video_path and os.path.exists(st.session_state.video_path):
        st.video(st.session_state.video_path)
    else:
        st.markdown(
            """
            <div style="background: rgba(17, 24, 39, 0.5); border: 2px dashed rgba(75, 85, 99, 0.5); border-radius: 12px; height: 260px; display: flex; align-items: center; justify-content: center; text-align: center; color: #6B7280; flex-direction: column;">
                <div style="font-size: 2.2rem; margin-bottom: 8px;">🎬</div>
                <div>No video loaded yet.<br>Upload a file or load the sample video to preview.</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ==========================================
# STEP 2 & 3: Execution Control & Pipeline
# ==========================================
st.markdown('<div class="section-header"><h3>2. Run Consistency Analysis</h3></div>', unsafe_allow_html=True)

can_analyze = bool(st.session_state.video_path and os.path.exists(st.session_state.video_path))
btn_col, info_col = st.columns([1, 2])

with btn_col:
    analyze_btn = st.button(
        "🔍 Analyze Lecture Consistency",
        type="primary",
        disabled=not can_analyze,
        use_container_width=True
    )

with info_col:
    if not can_analyze:
        st.caption("👈 Upload a video or load the sample lecture first to enable analysis.")
    else:
        st.caption("Extracts audio with FFmpeg, transcribes with Faster-Whisper, samples up to 6 frames with OpenCV, and reasons with Gemma 4.")

# Pipeline Processing Execution
if analyze_btn:
    video_file = st.session_state.video_path
    work_dir = os.path.join(BASE_DIR, "outputs", f"run_{int(time.time())}")
    frames_dir = os.path.join(work_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    progress_bar = st.progress(0, text="Initializing TeachCheck AI pipeline...")
    status_box = st.status("Processing Lecture...", expanded=True)

    try:
        # 1. Video validation
        status_box.write("📹 Validating video and calculating timing intervals...")
        progress_bar.progress(15, text="Step 1/5: Validating video metadata...")
        meta = get_video_metadata(video_file)
        st.session_state.video_meta = meta

        # 2. Extract representative frames
        status_box.write("🖼️ Extracting representative frames (~1 frame every 5s, max 6 frames)...")
        progress_bar.progress(35, text="Step 2/5: Extracting representative frames with OpenCV...")
        extracted_frames = extract_representative_frames(
            video_file,
            frames_dir,
            interval_sec=5.0,
            max_frames=6
        )
        st.session_state.extracted_frames = extracted_frames
        status_box.write(f"✓ Extracted {len(extracted_frames)} representative frames.")

        # 3. Audio Extraction & Transcription
        status_box.write("🎙️ Extracting audio stream and running Faster-Whisper (CPU INT8)...")
        progress_bar.progress(55, text="Step 3/5: Transcribing speech with Faster-Whisper...")

        transcript_segments = []
        try:
            audio_path = extract_audio_from_video(video_file, os.path.join(work_dir, "audio.wav"))
            transcript_segments = transcribe_audio(audio_path, model_size="tiny")
            st.session_state.transcript_segments = transcript_segments
            st.session_state.manual_transcript_text = format_transcript_as_text(transcript_segments)
            status_box.write(f"✓ Transcribed {len(transcript_segments)} speech segments.")
        except Exception as t_err:
            status_box.write(f"⚠️ Audio transcription warning: {str(t_err)}")
            # If user already entered manual transcript, use it
            if st.session_state.manual_transcript_text.strip():
                status_box.write("Using manually provided transcript fallback.")
                transcript_segments = parse_manual_transcript(st.session_state.manual_transcript_text)
                st.session_state.transcript_segments = transcript_segments
            else:
                # Provide empty or fallback
                transcript_segments = [{
                    "segment_id": 1,
                    "timestamp": "00:00 - 00:30",
                    "text": "Audio unavailable or silent. Use manual transcript input tab to enter speech."
                }]
                st.session_state.transcript_segments = transcript_segments

        # 4. Consistency Analysis with Gemma 4
        progress_bar.progress(75, text="Step 4/5: Cross-referencing speech and visual code with Gemma 4...")
        status_box.write(f"🧠 Querying {GEMMA_MODEL_ID} for visual reasoning and code cross-referencing...")

        if st.session_state.is_demo_mode:
            # Demo Mode: use curated evaluation
            time.sleep(1.0)  # Brief realistic pause
            analysis_data = get_demo_analysis_data(extracted_frames)
            st.session_state.analysis_results = analysis_data
            status_box.write("✓ Demo evaluation completed with benchmark findings.")
        else:
            # Live Gemma 4 API Call
            if not st.session_state.api_key or not st.session_state.api_key.strip():
                raise GemmaAPIError(
                    "Missing GEMINI_API_KEY. Please enter your API key in the sidebar, "
                    "or toggle 'Demo Mode' to view the benchmark verification."
                )

            analysis_data = analyze_lecture_with_gemma(
                frames=extracted_frames,
                transcript_segments=transcript_segments,
                api_key=st.session_state.api_key
            )
            st.session_state.analysis_results = analysis_data
            status_box.write("✓ Gemma 4 visual reasoning and consistency analysis finished.")

        progress_bar.progress(100, text="Analysis Complete!")
        status_box.update(label="Lecture Consistency Analysis Finished!", state="complete", expanded=False)
        st.success("Analysis complete! Review the results below.")

    except Exception as e:
        status_box.update(label="Analysis Halted with Error", state="error", expanded=True)
        st.error(f"❌ Error encountered: {str(e)}")
        if isinstance(e, GemmaAPIError):
            st.warning(
                "💡 Note: Gemma 4 (`gemma-4-26b-a4b-it`) is the required model. "
                "Ensure your Google Gemini API key has access to Gemma 4, or switch to Demo Mode in the sidebar."
            )


# ==========================================
# STEP 3: Extracted Frames & Transcript Review
# ==========================================
if st.session_state.extracted_frames or st.session_state.transcript_segments:
    st.markdown('<div class="section-header"><h3>3. Extracted Lecture Context</h3></div>', unsafe_allow_html=True)

    tab_frames, tab_transcript = st.tabs(["🖼️ Representative Frames (Max 6)", "📝 Lecture Audio Transcript"])

    with tab_frames:
        if st.session_state.extracted_frames:
            st.caption(f"Showing {len(st.session_state.extracted_frames)} representative frames sampled at ~5s intervals:")
            frame_cols = st.columns(min(len(st.session_state.extracted_frames), 6))
            for i, frame in enumerate(st.session_state.extracted_frames):
                with frame_cols[i % len(frame_cols)]:
                    st.image(frame["file_path"], use_container_width=True)
                    st.markdown(
                        f"""
                        <div class="frame-thumb-box">
                            <span class="badge badge-insufficient">Frame {frame['frame_index']}</span>
                            <div class="frame-thumb-title">⏱️ {frame['timestamp_str']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("No frames extracted yet. Run analysis to extract frames.")

    with tab_transcript:
        st.caption("Timestamped transcription generated by Faster-Whisper (CPU INT8) or manually edited:")
        col_t_view, col_t_edit = st.columns([1, 1], gap="medium")

        with col_t_view:
            st.markdown("**Structured Segments:**")
            if st.session_state.transcript_segments:
                for seg in st.session_state.transcript_segments:
                    st.markdown(
                        f"""
                        <div style="background: rgba(31, 41, 55, 0.6); padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; font-size: 0.88rem;">
                            <span style="color: #60A5FA; font-weight: 700; font-family: monospace;">[{seg.get('timestamp', '00:00')}]</span>
                            <span style="color: #E2E8F0;">{seg.get('text', '')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("No transcript segments available.")

        with col_t_edit:
            st.markdown("**Manual Transcript Input / Fallback:**")
            manual_input = st.text_area(
                "Edit or provide custom transcript lines:",
                value=st.session_state.manual_transcript_text,
                height=220,
                help="You can manually type or paste transcript lines like '[00:05] Today we use add...' as a fallback."
            )
            if st.button("💾 Apply Manual Transcript", key="apply_manual_ts"):
                if manual_input.strip():
                    try:
                        parsed = parse_manual_transcript(manual_input)
                        st.session_state.transcript_segments = parsed
                        st.session_state.manual_transcript_text = manual_input
                        st.success(f"Applied {len(parsed)} manual transcript segments!")
                        st.rerun()
                    except Exception as pe:
                        st.error(f"Failed to parse manual transcript: {str(pe)}")


# ==========================================
# STEP 4: Results Dashboard
# ==========================================
if st.session_state.analysis_results:
    st.markdown('<div class="section-header"><h3>4. Consistency Verification Dashboard</h3></div>', unsafe_allow_html=True)

    results = st.session_state.analysis_results
    findings = results.get("findings", [])
    metrics = get_summary_metrics(findings)

    # Representative Frame Scope Disclaimer
    st.markdown(
        """
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 8px; padding: 10px 16px; margin-bottom: 18px; font-size: 0.85rem; color: #FCD34D;">
            ⚠️ <b>Representative Frame Scope</b>: Analysis is based on 6 representative frames sampled across the lecture excerpt.
            Verified moments confirm consistency for the analyzed frames, not exhaustive verification of off-screen or un-sampled lecture footage.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Metrics Summary Row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-val" style="color: #F87171;">{metrics['total_issues']}</div>
                <div class="metric-lbl">Total Issues</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-val" style="color: #EF4444;">{metrics['confirmed_inconsistencies']}</div>
                <div class="metric-lbl">Confirmed Errors</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-val" style="color: #F59E0B;">{metrics['potential_inconsistencies']}</div>
                <div class="metric-lbl">Potential Mismatches</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-val" style="color: #10B981;">{metrics['verified_sections']}</div>
                <div class="metric-lbl">Verified Sections</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m5:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-val" style="color: #9CA3AF;">{metrics['insufficient_evidence']}</div>
                <div class="metric-lbl">Insufficient Evidence</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Overall Summary
    overall_sum = results.get("overall_summary", "No summary provided.")
    is_demo = results.get("is_demo_mode", False) or st.session_state.is_demo_mode
    demo_badge = '<span class="badge badge-potential" style="margin-left: 8px;">DEMO BENCHMARK</span>' if is_demo else '<span class="badge badge-verified" style="margin-left: 8px;">GEMMA 4 VERIFIED</span>'

    st.markdown(
        f"""
        <div style="background: rgba(30, 27, 75, 0.5); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 12px; padding: 18px 22px; margin-top: 18px; margin-bottom: 24px;">
            <div style="font-weight: 700; font-size: 1.05rem; color: #C4B5FD; margin-bottom: 6px;">
                AI Consistency Summary {demo_badge}
            </div>
            <div style="color: #E2E8F0; font-size: 0.95rem; line-height: 1.55;">
                {overall_sum}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Detailed Findings List
    st.markdown("#### 🔍 Timestamped Cross-Modal Findings")

    # Map frame index to file path for display
    frame_map = {f["frame_index"]: f for f in st.session_state.extracted_frames}

    for idx, finding in enumerate(findings):
        cat = finding.get("category", "Potential inconsistency")
        f_idx = finding.get("frame_index", idx + 1)
        ts = finding.get("timestamp", f"Frame {f_idx}")
        spoken = finding.get("spoken_statement", "N/A")
        visible = finding.get("visible_evidence", "N/A")
        expl = finding.get("explanation", "N/A")
        corr = finding.get("suggested_correction", "N/A")

        # Category class & badge styling
        box_class = "finding-box-potential"
        badge_html = '<span class="badge badge-potential">Potential Inconsistency</span>'
        if cat == "Confirmed inconsistency":
            box_class = "finding-box-confirmed"
            badge_html = '<span class="badge badge-confirmed">🚨 Confirmed Inconsistency</span>'
        elif cat == "No inconsistency observed":
            box_class = "finding-box-verified"
            badge_html = '<span class="badge badge-verified">✅ Verified Consistent</span>'
        elif cat == "Insufficient evidence":
            box_class = "finding-box-insufficient"
            badge_html = '<span class="badge badge-insufficient">⚠️ Insufficient Evidence</span>'

        f_data = frame_map.get(f_idx)

        with st.container():
            f_col_img, f_col_desc = st.columns([1, 2], gap="medium")

            with f_col_img:
                if f_data and os.path.exists(f_data["file_path"]):
                    st.image(
                        f_data["file_path"],
                        caption=f"Frame {f_idx} at {ts}",
                        use_container_width=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div style="background: #1F2937; height: 160px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #9CA3AF;">
                            Frame {f_idx} Preview
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            with f_col_desc:
                st.markdown(
                    f"""
                    <div class="finding-box {box_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <span style="font-weight: 700; font-size: 1.05rem; color: #F9FAFB;">⏱️ Timestamp: {ts}</span>
                            {badge_html}
                        </div>
                        <div style="margin-bottom: 8px; font-size: 0.9rem;">
                            <span style="color: #94A3B8; font-weight: 600;">🗣️ Spoken Statement:</span><br>
                            <span style="color: #F3F4F6;">"{spoken}"</span>
                        </div>
                        <div style="margin-bottom: 8px; font-size: 0.9rem;">
                            <span style="color: #94A3B8; font-weight: 600;">👁️ Visible Evidence on Screen:</span><br>
                            <span style="color: #E2E8F0; font-family: monospace; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">{visible}</span>
                        </div>
                        <div style="margin-bottom: 8px; font-size: 0.9rem;">
                            <span style="color: #94A3B8; font-weight: 600;">🧠 AI Visual Reasoning:</span><br>
                            <span style="color: #CBD5E1;">{expl}</span>
                        </div>
                        <div style="font-size: 0.88rem; background: rgba(0, 0, 0, 0.2); padding: 8px 10px; border-radius: 6px;">
                            <span style="color: #38BDF8; font-weight: 600;">💡 Suggested Correction:</span>
                            <span style="color: #E0F2FE;">{corr}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # Raw Response Inspector
    with st.expander("🛠️ Inspect Raw Model Output & JSON Payload", expanded=False):
        if results.get("raw_response"):
            st.code(results.get("raw_response"), language="json")
        else:
            st.json(results)

    # ==========================================
    # STEP 5: Export Report
    # ==========================================
    st.markdown('<div class="section-header"><h3>5. Export Analysis Report</h3></div>', unsafe_allow_html=True)

    json_report_str = generate_json_report(
        analysis_data=results,
        video_meta=st.session_state.video_meta or {},
        transcript_segments=st.session_state.transcript_segments,
        frames=st.session_state.extracted_frames,
        is_demo=is_demo
    )

    exp_col1, exp_col2 = st.columns([1, 2])
    with exp_col1:
        st.download_button(
            label="📥 Download JSON Report",
            data=json_report_str,
            file_name=f"teachcheck_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    with exp_col2:
        st.caption("Exports full verification findings, transcript segments, video metadata, and summary metrics.")
