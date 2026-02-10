"""
Streamlit Client — Narrative Transformation Engine
=====================================================
A real-time streaming UI that connects to the FastAPI backend.
Shows live progress through each pipeline stage with cooldown
countdowns, intermediate outputs, and the final story.
"""

import streamlit as st
import requests
import json
import time

# ── Page Config ──
st.set_page_config(
    page_title="Narrative Transformer",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
# ── Custom CSS ──
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Header - Gradient with fallback */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        color: white !important;
    }
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.9;
        margin: 0.5rem 0 0 0;
        color: white !important;
    }

    /* Stage cards - Theme accessible */
    .stage-card {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin: 0.5rem 0;
        background-color: transparent;
    }
    
    /* Hide hamburger menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Sidebar info box */
    .sidebar-info {
        padding: 1rem;
        background-color: rgba(128, 128, 128, 0.1);
        border-radius: 12px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }

    div[data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
</style>
""", unsafe_allow_html=True)


# ── Constants ──
STAGE_LABELS = {
    1: ("🔍 ANALYZE", "Extracting narrative DNA..."),
    2: ("🔄 TRANSFORM", "Mapping to target world..."),
    3: ("📋 OUTLINE", "Creating scene structure..."),
    4: ("✍️ GENERATE", "Writing the reimagined story..."),
}

STAGE_ICONS = {1: "🔍", 2: "🔄", 3: "📋", 4: "✍️"}
STAGE_COMPLETE_ICONS = {1: "✅", 2: "✅", 3: "✅", 4: "✅"}


# ── Sidebar ──
with st.sidebar:
    st.image("https://em-content.zobj.net/source/apple/391/crystal-ball_1f52e.png", width=60)
    st.title("Settings")

    # Try to get from secrets, otherwise default to local
    default_url = "http://localhost:8001"
    if "BACKEND_URL" in st.secrets:
        default_url = st.secrets["BACKEND_URL"]

    api_url = st.text_input(
        "Backend URL",
        value=default_url,
        help="URL of the FastAPI backend server"
    )

    if st.button("Check Server Status"):
        try:
            r = requests.get(f"{api_url}/api/health", timeout=3)
            if r.status_code == 200:
                st.success("✅ Server is Online")
            else:
                st.error(f"❌ Server Error: {r.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Server Offline")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    st.divider()

    st.markdown("""
    <div class="sidebar-info">
        <strong>How it works</strong><br>
        The engine transforms stories in 4 stages:<br><br>
        1️⃣ <strong>Analyze</strong> — Extract story DNA<br>
        2️⃣ <strong>Transform</strong> — Map to new world<br>
        3️⃣ <strong>Outline</strong> — Scene structure<br>
        4️⃣ <strong>Generate</strong> — Write the story<br><br>
        ⏱️ Each stage has a 65s cooldown<br>
        (Groq API rate limits: 6K TPM)
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("Powered by Groq + Llama 4 Maverick")
    st.caption("Built with FastAPI + Streamlit")


# ── Header ──
st.markdown("""
<div class="main-header">
    <h1>🔮 Narrative Transformation Engine</h1>
    <p>Transform any story into any world — powered by AI</p>
</div>
""", unsafe_allow_html=True)


# ── Load examples ──
@st.cache_data(ttl=300)
def load_examples(url):
    try:
        resp = requests.get(f"{url}/api/examples", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# ── Example buttons ──
examples = load_examples(api_url)

if examples:
    with st.expander("📚 **Load an example** — click to auto-fill", expanded=False):
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**📖 Source Stories**")
            for name, content in examples.get("stories", {}).items():
                if st.button(f"📖 {name}", key=f"story_{name}", use_container_width=True):
                    st.session_state["source_text"] = content

        with cols[1]:
            st.markdown("**🌍 Target Worlds**")
            for name, content in examples.get("worlds", {}).items():
                if st.button(f"🌍 {name}", key=f"world_{name}", use_container_width=True):
                    st.session_state["target_world"] = content


# ── Input Section ──
st.markdown("### 📝 Input")
col1, col2 = st.columns(2)

with col1:
    uploaded_source = st.file_uploader("📂 Load Source Story", type=["txt", "md"], key="source_upload")
    if uploaded_source:
        st.session_state["source_text"] = uploaded_source.read().decode("utf-8")

    source_text = st.text_area(
        "📖 Source Story",
        value=st.session_state.get("source_text", ""),
        height=250,
        placeholder="Paste a story summary, plot description, or full text here...\n\n"
                    "Examples:\n"
                    "- 'Hamlet by Shakespeare — a prince discovers his uncle murdered his father...'\n"
                    "- 'The story of Shivaji Maharaj — a warrior king who built an empire...'\n"
                    "- Any story you want to reimagine!",
        help="Any story works — fiction, history, mythology, or your own creation."
    )

with col2:
    uploaded_target = st.file_uploader("📂 Load Target World", type=["txt", "md"], key="target_upload")
    if uploaded_target:
        st.session_state["target_world"] = uploaded_target.read().decode("utf-8")

    target_world = st.text_area(
        "🌍 Target World",
        value=st.session_state.get("target_world", ""),
        height=250,
        placeholder="Describe the world you want to reimagine the story in...\n\n"
                    "Examples:\n"
                    "- 'AI startup ecosystem in Silicon Valley, 2027'\n"
                    "- 'Cyberpunk Tokyo, 2077'\n"
                    "- 'Medieval India during the Mughal era'\n"
                    "- 'Space opera in a distant galaxy'",
        help="Be as detailed or brief as you like. More detail = richer transformation."
    )


# ── Transform Button ──
st.markdown("")
transform_clicked = st.button(
    "🚀 Transform Story",
    type="primary",
    use_container_width=True,
    disabled=not (source_text and target_world),
)


# ── SSE Stream Parser ──
def parse_sse_stream(response):
    """Parse Server-Sent Events from a streaming response."""
    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
                yield data
            except json.JSONDecodeError:
                continue


# ── Run Transformation ──
if transform_clicked:
    # Validate
    if len(source_text.strip()) < 20:
        st.error("⚠️ Source story must be at least 20 characters.")
        st.stop()

    if len(target_world.strip()) < 5:
        st.error("⚠️ Target world must be at least 5 characters.")
        st.stop()

    st.divider()
    st.markdown("### 🔄 Transformation Progress")

    # Initialize tracking
    stages_data = {}
    st.session_state["stages_data"] = {}
    
    overall_progress = st.progress(0, text="Initializing engine...")
    
    # Create containers for each stage
    stage_status_containers = {}
    for i in range(1, 5):
        stage_status_containers[i] = st.empty()

    cooldown_container = st.empty()
    error_container = st.empty()

    try:
        # Connect to backend SSE stream
        response = requests.post(
            f"{api_url}/api/transform",
            json={"source_text": source_text, "target_world": target_world},
            stream=True,
            headers={"Accept": "text/event-stream"},
            timeout=600,  # 10 min total timeout
        )

        if response.status_code != 200:
            st.error(f"❌ Backend returned status {response.status_code}")
            st.stop()

        current_stage = 0

        for event in parse_sse_stream(response):
            event_type = event.get("type", "")

            if event_type == "init":
                overall_progress.progress(0, text=f"Engine ready — Model: {event.get('model', 'unknown')}")

            elif event_type == "stage_start":
                current_stage = event["stage"]
                label, msg = STAGE_LABELS[current_stage]
                icon = STAGE_ICONS[current_stage]

                overall_progress.progress(
                    (current_stage - 1) / 4,
                    text=f"Stage {current_stage}/4: {msg}"
                )

                # Show active status
                stage_status_containers[current_stage].info(
                    f"{icon} **Stage {current_stage}: {event['name']}** — {event.get('description', msg)}"
                )

                # Clear cooldown display
                cooldown_container.empty()

            elif event_type == "stage_complete":
                stage = event["stage"]
                stages_data[stage] = event.get("content", "")
                st.session_state["stages_data"] = stages_data  # Update session state

                # Update to complete
                stage_status_containers[stage].success(
                    f"✅ **Stage {stage}: {event['name']}** — Done ({event.get('chars', 0)} chars)"
                )

                overall_progress.progress(
                    stage / 4,
                    text=f"Stage {stage}/4 complete"
                )

            elif event_type == "cooldown_start":
                seconds = event.get("seconds", 65)
                cooldown_container.warning(
                    f"⏸️ **Rate limit cooldown**: Waiting {seconds}s for API reset..."
                )

            elif event_type == "cooldown_tick":
                remaining = event.get("seconds_remaining", 0)
                if remaining > 0:
                    cooldown_container.warning(
                        f"⏸️ **Cooldown**: {remaining}s remaining..."
                    )
                else:
                    cooldown_container.empty()

            elif event_type == "complete":
                overall_progress.progress(1.0, text="✅ Transformation complete!")
                cooldown_container.empty()

            elif event_type == "error":
                error_container.error(f"❌ Error: {event.get('message', 'Unknown error')}")
                st.stop()

        response.close()

    except requests.exceptions.ConnectionError:
        st.error(
            "❌ **Cannot connect to backend.** Make sure the FastAPI server is running:\n\n"
            "```bash\ncd backend && uvicorn app:app --reload --port 8000\n```"
        )
        st.stop()
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.stop()
    
    st.rerun()


# ── Display Results (from Session State) ──
if "stages_data" in st.session_state and st.session_state["stages_data"]:
    stages_data = st.session_state["stages_data"]
    
    st.divider()
    st.markdown("### 📖 Results")

    # Final story — prominently displayed
    if 4 in stages_data:
        st.markdown("#### ✨ Reimagined Story")
        
        # Use native container for theme compatibility
        with st.container(border=True):
            st.markdown(stages_data[4])
            
        st.download_button(
            "📥 Download Story",
            data=stages_data[4],
            file_name="reimagined_story.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # Intermediate stages — in tabs
    st.markdown("#### 🔬 Pipeline Details")
    tabs = st.tabs(["🔍 Analysis", "🔄 Transformation", "📋 Outline", "✍️ Full Story"])

    for i, tab in enumerate(tabs, 1):
        with tab:
            if i in stages_data:
                st.markdown(stages_data[i])
            else:
                st.info("No data for this stage.")

    # Download combined
    if stages_data:
        combined = "\n\n---\n\n".join([
            f"## Stage {i}\n\n{stages_data[i]}"
            for i in sorted(stages_data.keys())
        ])
        st.download_button(
            "📥 Download Full Output",
            data=combined,
            file_name="full_transformation_output.md",
            mime="text/markdown",
        )

    if transform_clicked: # If we just finished, show balloons
        st.balloons()
