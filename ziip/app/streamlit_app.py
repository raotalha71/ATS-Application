import streamlit as st
import requests
import re
import time
import os

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ATS Resume Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0c10;
    color: #e8eaf0;
}
.stApp { background: #0a0c10; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1100px; }

.hero {
    text-align: center;
    padding: 3rem 0 2.5rem;
}
.hero-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #5eead4;
    background: rgba(94, 234, 212, 0.08);
    border: 1px solid rgba(94, 234, 212, 0.2);
    padding: 0.35rem 1rem;
    border-radius: 100px;
    margin-bottom: 1.2rem;
}
.hero h1 {
    font-family: 'Syne', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1.1;
    margin: 0.4rem 0;
    background: linear-gradient(135deg, #f0f4ff 0%, #a5b4fc 50%, #5eead4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero p { color: #6b7280; font-size: 1.05rem; font-weight: 300; margin-top: 0.6rem; }

.pipeline-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 2rem 0 2.5rem;
    padding: 1.5rem 2rem;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    overflow-x: auto;
}
.pipeline-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    min-width: 100px;
}
.pipeline-step-circle {
    width: 48px; height: 48px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; font-weight: 700;
    border: 2px solid transparent;
    transition: all 0.4s ease;
}
.step-waiting .pipeline-step-circle {
    background: rgba(255,255,255,0.04);
    border-color: rgba(255,255,255,0.1);
    color: #374151;
}
.step-active .pipeline-step-circle {
    background: rgba(94,234,212,0.1);
    border-color: #5eead4;
    color: #5eead4;
    animation: pulse-ring 1.4s ease-in-out infinite;
}
@keyframes pulse-ring {
    0%, 100% { box-shadow: 0 0 0 0 rgba(94,234,212,0.4); }
    50%       { box-shadow: 0 0 0 8px rgba(94,234,212,0.0); }
}
.step-done .pipeline-step-circle {
    background: rgba(94,234,212,0.15);
    border-color: #5eead4;
    color: #5eead4;
}
.pipeline-step-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: center;
    color: #6b7280;
    max-width: 90px;
    line-height: 1.3;
}
.step-active .pipeline-step-label,
.step-done .pipeline-step-label { color: #9ca3af; }

.pipeline-connector {
    width: 40px; height: 2px;
    margin: 0 4px;
    margin-bottom: 22px;
    background: rgba(255,255,255,0.07);
    flex-shrink: 0;
    transition: background 0.4s;
}
.connector-done { background: rgba(94,234,212,0.4); }

.score-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
}
.score-ring-wrap { display: flex; justify-content: center; margin: 1rem 0; }
.score-circle-outer {
    width: 140px; height: 140px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    position: relative;
}
.score-number { font-family: 'Syne', sans-serif; font-size: 2.8rem; font-weight: 800; line-height: 1; }
.score-max { font-family: 'DM Mono', monospace; font-size: 0.75rem; color: #6b7280; margin-top: 2px; }
.grade-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    padding: 0.3rem 1rem;
    border-radius: 100px;
    margin-top: 0.8rem;
    letter-spacing: 0.06em;
}

.category-bar-wrap { margin: 0.5rem 0; }
.category-bar-label {
    display: flex; justify-content: space-between;
    font-size: 0.8rem; margin-bottom: 5px; color: #9ca3af;
}
.category-bar-track {
    height: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 100px;
    overflow: hidden;
}
.category-bar-fill { height: 100%; border-radius: 100px; }

.tag-wrap { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
.tag { font-family: 'DM Mono', monospace; font-size: 0.7rem; padding: 0.25rem 0.7rem; border-radius: 100px; letter-spacing: 0.04em; }
.tag-green  { background: rgba(94,234,212,0.1);  color: #5eead4; border: 1px solid rgba(94,234,212,0.2); }
.tag-red    { background: rgba(248,113,113,0.1); color: #f87171; border: 1px solid rgba(248,113,113,0.2); }
.tag-amber  { background: rgba(251,191,36,0.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.2); }
.tag-blue   { background: rgba(129,140,248,0.1); color: #818cf8; border: 1px solid rgba(129,140,248,0.2); }

.section-heading {
    font-family: 'Syne', sans-serif;
    font-size: 1rem; font-weight: 700;
    letter-spacing: 0.04em; text-transform: uppercase;
    color: #e8eaf0; margin-bottom: 1rem;
    display: flex; align-items: center; gap: 0.5rem;
}
.info-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
}
.info-card h4 {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.12em; color: #5eead4;
    margin: 0 0 0.6rem 0;
}

.chat-bubble-user {
    background: rgba(129,140,248,0.12);
    border: 1px solid rgba(129,140,248,0.2);
    border-radius: 14px 14px 4px 14px;
    padding: 0.8rem 1.2rem; margin: 0.6rem 0;
    font-size: 0.9rem; max-width: 75%;
    margin-left: auto; color: #c7d2fe;
}
.chat-bubble-ai {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px 14px 14px 4px;
    padding: 0.8rem 1.2rem; margin: 0.6rem 0;
    font-size: 0.9rem; max-width: 85%;
    color: #d1d5db; line-height: 1.65;
}

div[data-testid="stFileUploader"] > div {
    background: rgba(94,234,212,0.03) !important;
    border: 2px dashed rgba(94,234,212,0.25) !important;
    border-radius: 14px !important;
    padding: 1.5rem !important;
}
div[data-testid="stFileUploader"] label { color: #9ca3af !important; }

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e8eaf0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

.stButton > button {
    background: linear-gradient(135deg, #5eead4, #818cf8) !important;
    color: #0a0c10 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.8rem !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

.stTextArea label, .stTextInput label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: #6b7280 !important;
}

div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
    gap: 0 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: #6b7280 !important;
    background: transparent !important;
    border: none !important;
    padding: 0.6rem 1.4rem !important;
}
div[data-testid="stTabs"] [aria-selected="true"] {
    color: #5eead4 !important;
    border-bottom: 2px solid #5eead4 !important;
}
.stSpinner > div { border-top-color: #5eead4 !important; }
[data-testid="stSidebar"] { background: #060810 !important; }
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
}
hr { border-color: rgba(255,255,255,0.07) !important; }
.stAlert { border-radius: 12px !important; background: rgba(94,234,212,0.06) !important; border-left-color: #5eead4 !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# ── Session State Init ─────────────────────────────────────────────────────────
for key, default in {
    "resume_id": None,
    "ats_report": None,
    "suggestions": None,
    "filename": None,
    "chat_history": [],
    "upload_done": False,
    "pending_question": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helper: Score Ring ─────────────────────────────────────────────────────────
def render_score_ring(score: int, grade: str):
    if score >= 85:
        color, grade_bg = "#5eead4", "rgba(94,234,212,0.15)"
    elif score >= 70:
        color, grade_bg = "#818cf8", "rgba(129,140,248,0.15)"
    elif score >= 55:
        color, grade_bg = "#fbbf24", "rgba(251,191,36,0.15)"
    else:
        color, grade_bg = "#f87171", "rgba(248,113,113,0.15)"

    circumference = 2 * 3.14159 * 54
    dash = (score / 100) * circumference
    gap = circumference - dash

    st.markdown(f"""
    <div class="score-card">
        <div style="font-family:'DM Mono',monospace;font-size:0.68rem;text-transform:uppercase;
                    letter-spacing:0.14em;color:#6b7280;margin-bottom:0.5rem;">ATS Score</div>
        <div class="score-ring-wrap">
            <div class="score-circle-outer">
                <svg width="140" height="140" style="position:absolute;top:0;left:0;transform:rotate(-90deg)">
                    <circle cx="70" cy="70" r="54" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="10"/>
                    <circle cx="70" cy="70" r="54" fill="none" stroke="{color}" stroke-width="10"
                        stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-linecap="round"/>
                </svg>
                <div style="position:relative;text-align:center;">
                    <div class="score-number" style="color:{color}">{score}</div>
                    <div class="score-max">/ 100</div>
                </div>
            </div>
        </div>
        <div class="grade-badge" style="background:{grade_bg};color:{color};border:1px solid {color}33">
            {grade}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Helper: Category Bars ──────────────────────────────────────────────────────
def render_category_bars(categories: dict):
    colors = {
        "contact_info":   ("#5eead4", 10),
        "sections":       ("#818cf8", 15),
        "action_verbs":   ("#f472b6", 15),
        "keyword_match":  ("#fbbf24", 25),
        "role_match":     ("#fb7185", 100),
        "quantification": ("#34d399", 20),
        "formatting":     ("#60a5fa", 15),
    }
    labels = {
        "contact_info":   "Contact Info",
        "sections":       "Sections",
        "action_verbs":   "Action Verbs",
        "keyword_match":  "Keyword Match",
        "role_match":     "Role Match",
        "quantification": "Quantification",
        "formatting":     "Formatting",
    }
    for key, (color, max_val) in colors.items():
        if key not in categories:
            continue
        score = categories[key]["score"]
        pct = (score / max_val) * 100
        st.markdown(f"""
        <div class="category-bar-wrap">
            <div class="category-bar-label">
                <span>{labels[key]}</span>
                <span style="font-family:'DM Mono',monospace">{score}/{max_val}</span>
            </div>
            <div class="category-bar-track">
                <div class="category-bar-fill" style="width:{pct:.0f}%;background:{color};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Helper: Tag Cloud ──────────────────────────────────────────────────────────
def render_tags(items: list, css_class: str):
    if not items:
        st.markdown('<span style="color:#6b7280;font-size:0.8rem;font-style:italic;">None found</span>', unsafe_allow_html=True)
        return
    tags = "".join(f'<span class="tag {css_class}">{t}</span>' for t in items)
    st.markdown(f'<div class="tag-wrap">{tags}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT — Hero + Pipeline (rendered ONCE at top level via a single slot)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <div class="hero-badge">Resume Intelligence Platform</div>
    <h1>ATS Analyzer</h1>
    <p>Rule-based scoring · LLM suggestions · RAG-powered Q&amp;A</p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_upload, tab_score, tab_suggestions, tab_chat = st.tabs([
    "📤  Upload Resume",
    "📊  ATS Score",
    "💡  Suggestions",
    "💬  Chat",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
with tab_upload:
    st.markdown('<div class="section-heading">📁 Upload Resume</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        uploaded_file = st.file_uploader(
            "Drop your PDF or DOCX resume here",
            type=["pdf", "docx"],
            help="Max 10MB. PDF or DOCX only.",
        )
        candidate_name = st.text_input(
            "Candidate Name (optional)",
            placeholder="e.g. Talha Rao",
        )
        job_description = st.text_area(
            "Job Description (optional — paste for keyword scoring)",
            placeholder="Paste the job posting here to get keyword match score...",
            height=140,
        )

        upload_btn = st.button("Analyze Resume", use_container_width=True)

    with col_right:
        st.markdown("""
        <div class="info-card">
            <h4>What happens on upload</h4>
            <div style="font-size:0.85rem;color:#9ca3af;line-height:1.8">
                <div>① Text extracted from PDF/DOCX</div>
                <div>② 6-category rule-based ATS scoring</div>
                <div>③ LLM narrates findings into suggestions</div>
                <div>④ FAISS vector index built (CV + ATS + tips)</div>
                <div>⑤ Chat Q&A enabled for this resume</div>
            </div>
        </div>
        <div class="info-card" style="margin-top:0.8rem">
            <h4>Scoring breakdown</h4>
            <div style="font-family:'DM Mono',monospace;font-size:0.75rem;color:#6b7280;line-height:2">
                Contact Info &nbsp;&nbsp;&nbsp;&nbsp; 10 pts<br/>
                Sections Present &nbsp; 15 pts<br/>
                Action Verbs &nbsp;&nbsp;&nbsp;&nbsp; 15 pts<br/>
                Keyword Match &nbsp;&nbsp;&nbsp; 25 pts<br/>
                Quantification &nbsp;&nbsp;&nbsp; 20 pts<br/>
                Formatting &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 15 pts
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Upload Logic ───────────────────────────────────────────────────────────
    if upload_btn:
        if not uploaded_file:
            st.warning("Please upload a PDF or DOCX file first.")
        else:
            # Reset all state
            st.session_state.resume_id = None
            st.session_state.ats_report = None
            st.session_state.suggestions = None
            st.session_state.chat_history = []
            st.session_state.upload_done = False

            status_box = st.empty()
            status_box.markdown(
                '<div style="color:#5eead4;font-family:\'DM Mono\',monospace;font-size:0.8rem;padding:0.5rem 0">'
                '🔍 Extracting text from resume...</div>',
                unsafe_allow_html=True,
            )

            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {
                "candidate_name": candidate_name or "the candidate",
                "job_description": job_description or "",
            }

            status_box.markdown(
                '<div style="color:#5eead4;font-family:\'DM Mono\',monospace;font-size:0.8rem;padding:0.5rem 0">'
                '⚖️ Running ATS rule engine...</div>',
                unsafe_allow_html=True,
            )

            try:
                resp = requests.post(f"{API_BASE}/upload", files=files, data=data, timeout=180)
                resp.raise_for_status()
                result = resp.json()

                if "resume_id" not in result:
                    detail = result.get("detail") or result.get("message") or result.get("error") or "Upload rejected"
                    st.session_state.upload_done = False
                    status_box.empty()
                    st.error(f"❌ Upload failed: {detail}")
                    if isinstance(result.get("detail"), dict) and result["detail"].get("upload_suggestions"):
                        st.markdown("**What to upload instead:**", unsafe_allow_html=True)
                        for suggestion in result["detail"]["upload_suggestions"]:
                            st.markdown(f"- {suggestion}")
                else:
                    st.session_state.resume_id = result["resume_id"]
                    st.session_state.filename = result["filename"]
                    st.session_state.upload_done = True

                    status_box.empty()
                    validation = result.get("validation", {})
                    sections_missing = result.get("sections_missing", [])

                    if not validation.get("is_resume", True):
                        st.warning(
                            "This upload does not look like a standard CV/resume. The system still processed it, but the agent will treat it cautiously."
                        )

                    if sections_missing:
                        st.warning(
                            "Missing standard sections detected: " + ", ".join(sections_missing)
                        )

                    st.success(
                        f"✅ Resume analyzed! **{result['filename']}** — "
                        f"Score: **{result['ats_score']}/100** ({result['grade']}) — "
                        f"Role Match: **{result.get('role_match_score', 0)}/100** "
                        f"({result.get('role_match_verdict', 'Not evaluated')}) — "
                        f"{result['total_chunks_indexed']} chunks indexed"
                    )

            except requests.exceptions.ConnectionError:
                status_box.empty()
                st.error("❌ Cannot reach backend. Is `uvicorn app.main:app --reload --port 8000` running?")

            except requests.exceptions.Timeout:
                status_box.empty()
                st.error("❌ Request timed out. Mistral 7B may be taking long — try again.")

            except Exception as e:
                status_box.empty()
                detail = ""
                try:
                    payload = resp.json()
                    detail = payload.get("detail") or payload.get("message") or payload.get("error") or str(e)
                except Exception:
                    detail = str(e)
                st.error(f"❌ Upload failed: {detail}")

    # Show current resume status if loaded
    if st.session_state.resume_id:
        st.markdown(f"""
        <div class="info-card" style="border-color:rgba(94,234,212,0.25);margin-top:1rem">
            <h4>Active Resume</h4>
            <div style="font-size:0.85rem;color:#9ca3af">
                <b style="color:#5eead4">{st.session_state.filename}</b><br/>
                <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:#6b7280">
                    ID: {st.session_state.resume_id}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ATS SCORE
# ══════════════════════════════════════════════════════════════════════════════
with tab_score:
    if not st.session_state.resume_id:
        st.markdown("""
        <div style="text-align:center;padding:4rem 0;color:#6b7280">
            <div style="font-size:2.5rem;margin-bottom:1rem">📊</div>
            <div style="font-family:'DM Mono',monospace;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em">
                Upload a resume first
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        if not st.session_state.ats_report:
            with st.spinner("Fetching ATS report..."):
                try:
                    r = requests.get(f"{API_BASE}/ats/{st.session_state.resume_id}", timeout=30)
                    r.raise_for_status()
                    st.session_state.ats_report = r.json()["ats_report"]
                except Exception as e:
                    st.error(f"Failed to fetch ATS report: {e}")

        if st.session_state.ats_report:
            rep = st.session_state.ats_report
            col1, col2 = st.columns([1, 2], gap="large")

            with col1:
                render_score_ring(rep["total_score"], rep["grade"])
                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown('<div class="section-heading" style="font-size:0.8rem">Category Breakdown</div>', unsafe_allow_html=True)
                render_category_bars(rep["categories"])

            with col2:
                findings = rep.get("findings", {})

                with st.expander("📇 Contact Info", expanded=True):
                    contact = findings.get("contact", {})
                    for k, v in contact.items():
                        icon = "✅" if v else "❌"
                        color = "#5eead4" if v else "#f87171"
                        st.markdown(
                            f'<span style="font-family:\'DM Mono\',monospace;font-size:0.8rem;color:{color}">{icon} {k.title()}</span>',
                            unsafe_allow_html=True,
                        )

                with st.expander("📑 Sections Detected"):
                    sf = findings.get("sections_found", {})
                    for section, found in sf.items():
                        icon = "✅" if found else "❌"
                        color = "#5eead4" if found else "#f87171"
                        st.markdown(
                            f'<span style="font-family:\'DM Mono\',monospace;font-size:0.8rem;color:{color}">{icon} {section.title()}</span>',
                            unsafe_allow_html=True,
                        )

                with st.expander("🎯 Action Verbs"):
                    st.markdown('<div style="font-size:0.78rem;color:#6b7280;margin-bottom:0.3rem">Strong verbs ↗</div>', unsafe_allow_html=True)
                    render_tags(findings.get("strong_verbs", []), "tag-green")
                    st.markdown('<div style="font-size:0.78rem;color:#6b7280;margin:0.6rem 0 0.3rem">Weak verbs ↘</div>', unsafe_allow_html=True)
                    render_tags(findings.get("weak_verbs", []), "tag-red")

                with st.expander("🔑 Keywords"):
                    kw_score = rep["categories"]["keyword_match"]
                    st.markdown(
                        f'<div style="font-family:\'DM Mono\',monospace;font-size:0.75rem;color:#9ca3af;margin-bottom:0.6rem">'
                        f'Match: <b style="color:#fbbf24">{kw_score.get("match_pct", 0):.1f}%</b></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div style="font-size:0.78rem;color:#6b7280;margin-bottom:0.3rem">Matched ✓</div>', unsafe_allow_html=True)
                    render_tags(findings.get("matched_keywords", []), "tag-green")
                    st.markdown('<div style="font-size:0.78rem;color:#6b7280;margin:0.6rem 0 0.3rem">Missing — add these</div>', unsafe_allow_html=True)
                    render_tags(findings.get("missing_keywords", []), "tag-red")

                with st.expander("📈 Quantification"):
                    q = findings.get("quantified_lines", 0)
                    t = findings.get("total_bullet_lines", 1)
                    pct = (q / t * 100) if t else 0
                    st.markdown(
                        f'<div style="font-family:\'DM Mono\',monospace;font-size:0.8rem;color:#9ca3af">'
                        f'<b style="color:#34d399">{q}</b> of <b>{t}</b> bullet lines have numbers '
                        f'<span style="color:#6b7280">({pct:.0f}%)</span></div>',
                        unsafe_allow_html=True,
                    )

                warnings = findings.get("formatting_warnings", [])
                if warnings:
                    with st.expander("⚠️ Formatting Warnings"):
                        for w in warnings:
                            st.markdown(
                                f'<div class="info-card" style="padding:0.7rem 1rem;margin-bottom:0.4rem">'
                                f'<span style="font-size:0.82rem;color:#fbbf24">⚠ {w}</span></div>',
                                unsafe_allow_html=True,
                            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_suggestions:
    if not st.session_state.resume_id:
        st.markdown("""
        <div style="text-align:center;padding:4rem 0;color:#6b7280">
            <div style="font-size:2.5rem;margin-bottom:1rem">💡</div>
            <div style="font-family:'DM Mono',monospace;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em">
                Upload a resume first
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        if not st.session_state.suggestions:
            with st.spinner("Fetching LLM suggestions..."):
                try:
                    r = requests.get(f"{API_BASE}/suggestions/{st.session_state.resume_id}", timeout=30)
                    r.raise_for_status()
                    st.session_state.suggestions = r.json()["suggestions"]
                except Exception as e:
                    st.error(f"Failed to fetch suggestions: {e}")

        if st.session_state.suggestions:
            st.markdown('<div class="section-heading">💡 Improvement Suggestions</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="info-card" style="margin-bottom:1.5rem;border-color:rgba(251,191,36,0.2);background:rgba(251,191,36,0.04)">
                <div style="font-size:0.82rem;color:#9ca3af">
                    Generated by Mistral 7B based on rule-engine findings.
                    The model <i>narrates</i> the ATS findings — it doesn't invent new rules.
                </div>
            </div>
            """, unsafe_allow_html=True)

            lines = st.session_state.suggestions.strip().split('\n')
            card_html = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                is_numbered = re.match(r'^(\d+[\.\)])', line)
                if is_numbered:
                    num = is_numbered.group(1).rstrip('.')
                    text = line[len(is_numbered.group(0)):].strip()
                    card_html += f"""
                    <div class="info-card" style="display:flex;gap:1rem;align-items:flex-start;margin-bottom:0.7rem">
                        <div style="min-width:28px;height:28px;border-radius:50%;
                                    background:rgba(94,234,212,0.1);border:1px solid rgba(94,234,212,0.3);
                                    display:flex;align-items:center;justify-content:center;
                                    font-family:'DM Mono',monospace;font-size:0.72rem;color:#5eead4;font-weight:700">
                            {num}
                        </div>
                        <div style="font-size:0.88rem;color:#d1d5db;line-height:1.6">{text}</div>
                    </div>
                    """
                else:
                    card_html += f'<div style="font-size:0.85rem;color:#9ca3af;margin-bottom:0.4rem">{line}</div>'

            st.markdown(card_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    if not st.session_state.resume_id:
        st.markdown("""
        <div style="text-align:center;padding:4rem 0;color:#6b7280">
            <div style="font-size:2.5rem;margin-bottom:1rem">💬</div>
            <div style="font-family:'DM Mono',monospace;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em">
                Upload a resume first
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-heading">💬 Chat with Resume</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-card" style="margin-bottom:1rem;border-color:rgba(129,140,248,0.2);background:rgba(129,140,248,0.04)">
            <div style="font-size:0.8rem;color:#9ca3af">
                Ask anything about this CV. FAISS retrieves the 3 most relevant chunks
                (CV · ATS · Suggestions) and Mistral answers from them. Streamed live.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<div style="font-family:\'DM Mono\',monospace;font-size:0.68rem;text-transform:uppercase;'
            'letter-spacing:0.1em;color:#6b7280;margin-bottom:0.5rem">Quick Questions</div>',
            unsafe_allow_html=True,
        )

        qcols = st.columns(3)
        quick_questions = [
            "Why is this CV weak?",
            "What skills does this person have?",
            "What improvements are needed?",
        ]
        for i, (col, qq) in enumerate(zip(qcols, quick_questions)):
            with col:
                if st.button(qq, key=f"quick_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": qq})
                    st.session_state.pending_question = qq
                    st.rerun()

        st.markdown("<br/>", unsafe_allow_html=True)

        # Chat history display
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-bubble-user">🧑 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-bubble-ai">🤖 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

        question = st.text_input(
            "Ask a question",
            placeholder="e.g. What is this person's experience in Python?",
            key="chat_input",
            label_visibility="collapsed",
        )

        col_ask, col_clear = st.columns([1, 4])
        with col_ask:
            ask_btn = st.button("Ask →", use_container_width=True)
        with col_clear:
            if st.button("Clear History", use_container_width=False):
                st.session_state.chat_history = []
                st.rerun()

        # Determine active question
        active_question = None
        if ask_btn and question:
            active_question = question
        elif st.session_state.pending_question:
            active_question = st.session_state.pending_question
            st.session_state.pending_question = None

        if active_question:
            last = st.session_state.chat_history[-1:] 
            if not (last and last[0]["role"] == "user" and last[0]["content"] == active_question):
                st.session_state.chat_history.append({"role": "user", "content": active_question})

            response_placeholder = st.empty()
            response_placeholder.markdown(
                '<div class="chat-bubble-ai">🤖 <span style="color:#5eead4">▋</span></div>',
                unsafe_allow_html=True,
            )

            try:
                full_response = ""
                with requests.post(
                    f"{API_BASE}/chat/{st.session_state.resume_id}",
                    json={"question": active_question},
                    stream=True,
                    timeout=120,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            decoded = line.decode("utf-8")
                            if decoded.startswith("data: "):
                                token = decoded[6:]
                                if token == "[DONE]":
                                    break
                                full_response += token
                                response_placeholder.markdown(
                                    f'<div class="chat-bubble-ai">🤖 {full_response}<span style="color:#5eead4">▋</span></div>',
                                    unsafe_allow_html=True,
                                )

                response_placeholder.empty()
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})

            except requests.exceptions.ConnectionError:
                response_placeholder.empty()
                st.error("❌ Cannot reach backend.")
            except Exception as e:
                response_placeholder.empty()
                st.error(f"Chat error: {e}")

            st.rerun()
