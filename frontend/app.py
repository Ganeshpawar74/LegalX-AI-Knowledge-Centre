"""
LegalX AI Knowledge Centre - Streamlit App

Homepage: displays auto-generated legal topic cards (Feature 1).
Clicking "Read More" navigates to the topic detail page.
"""
import sys
from pathlib import Path

# Allow running `streamlit run app.py` from project root with backend/ as a package
sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st

from backend.config import TOPICS
from backend.database import init_db, get_all_topic_cards, get_topic_card

st.set_page_config(
    page_title="LegalX AI Knowledge Centre",
    page_icon="\u2696\ufe0f",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .legalx-hero {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 50%, #1a365d 100%);
        color: white;
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
    }
    .legalx-hero h1 { margin: 0; font-size: 2.4rem; }
    .legalx-hero p { margin-top: 0.5rem; font-size: 1.1rem; opacity: 0.9; }

    .topic-card {
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.4rem;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        height: 100%;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .topic-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
    }
    .topic-card h3 { margin-top: 0; color: #1a365d; }
    .topic-card p { color: #4a5568; min-height: 60px; }
    .badge {
        display: inline-block;
        background: #ebf8ff;
        color: #2b6cb0;
        border-radius: 999px;
        padding: 0.2rem 0.7rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown("""
<div class="legalx-hero">
    <h1>\u2696\ufe0f LegalX AI Knowledge Centre</h1>
    <p>Browse legal topics, read AI-simplified summaries, listen to audio explanations,
    and ask an AI Legal Assistant your questions \u2014 powered by Mistral AI.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pipeline status / generation trigger
# ---------------------------------------------------------------------------
cards = get_all_topic_cards()
generated_ids = {c["topic_id"] for c in cards}
missing = [tid for tid in TOPICS if tid not in generated_ids]

if missing:
    st.warning(
        f"{len(missing)} topic(s) have not been processed yet by the AI pipeline: "
        f"{', '.join(TOPICS[t]['name'] for t in missing)}"
    )
    if st.button("\U0001F916 Run AI Processing Pipeline now", type="primary"):
        with st.spinner("Running automation pipeline (Mistral AI processing, RAG indexing, audio generation)..."):
            from backend.pipeline import process_topic
            from backend.audio_generator import generate_audio
            from backend.database import upsert_topic_card

            progress = st.progress(0)
            for i, topic_id in enumerate(missing):
                result = process_topic(topic_id)
                card = result["card"]
                audio_path = generate_audio(topic_id, card["summary"], force=result["needs_audio"])
                upsert_topic_card(
                    topic_id=topic_id,
                    name=TOPICS[topic_id]["name"],
                    card=card,
                    audio_path=audio_path,
                    source_hash=result["source_hash"],
                )
                progress.progress((i + 1) / len(missing))
        st.success("Pipeline complete! Refresh to see all cards.")
        st.rerun()

# ---------------------------------------------------------------------------
# Knowledge Centre Cards (Feature 1)
# ---------------------------------------------------------------------------
st.subheader("\U0001F4DA Legal Topics")

cards = get_all_topic_cards()

if not cards:
    st.info("No knowledge cards generated yet. Click the button above to run the AI pipeline.")
else:
    cols = st.columns(3)
    for idx, card in enumerate(cards):
        with cols[idx % 3]:
            st.markdown(f"""
            <div class="topic-card">
                <span class="badge">AI-Generated</span>
                <h3>{card['name']}</h3>
                <p>{card['short_description']}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Read More \u2192", key=f"read_more_{card['topic_id']}", use_container_width=True):
                st.session_state["selected_topic"] = card["topic_id"]
                st.switch_page("pages/1_Topic_Detail.py")

st.divider()
st.caption(
    "All summaries, key information, and audio are generated automatically by an AI "
    "processing pipeline (Mistral AI) from source legal text \u2014 nothing on this page "
    "is manually written."
)
