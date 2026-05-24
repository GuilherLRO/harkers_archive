"""Streamlit UI for batch transcription with separate input and output folders."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import whisper

from transcribe import MODEL_NAME, missing_transcriptions, transcribe_file

MODEL_OPTIONS = ("tiny", "base", "small", "medium", "large")
ASSETS_DIR = Path(__file__).parent / "assets"
HERO_IMAGE = ASSETS_DIR / "mina.png"

st.set_page_config(
    page_title="Mina's Typewriter",
    page_icon=str(HERO_IMAGE),
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #12121a 100%);
    }
    .block-container {
        padding-top: 2rem;
        max-width: 1100px;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: rgba(212, 168, 83, 0.35) !important;
        border-radius: 16px;
        box-shadow: 0 0 40px rgba(212, 168, 83, 0.12);
        padding: 1rem 1.25rem;
        margin-bottom: 0.5rem;
    }
    .hero-tagline {
        color: #d4a853;
        font-size: 1.05rem;
        font-style: italic;
        margin-top: 0.25rem;
        letter-spacing: 0.02em;
    }
    .hero-blurb {
        color: #b8b8c0;
        font-size: 0.95rem;
        line-height: 1.6;
        margin-top: 1rem;
    }
    h1 {
        color: #f0e6d0 !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em;
    }
    h2, h3, label, .stMarkdown p {
        color: #d8d8e0;
    }
    hr {
        border-color: rgba(212, 168, 83, 0.25) !important;
        margin: 1.5rem 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_model(model_name: str) -> whisper.Whisper:
    return whisper.load_model(model_name)


def validate_dirs(input_dir: Path, output_dir: Path) -> str | None:
    if not input_dir.is_dir():
        return f"Input folder does not exist: {input_dir}"
    if not output_dir.is_dir():
        return f"Output folder does not exist: {output_dir}"
    return None


def render_hero() -> None:
    with st.container(border=True):
        hero_left, hero_right = st.columns([1.35, 1], gap="large")

        with hero_left:
            st.image(str(HERO_IMAGE), use_container_width=True)

        with hero_right:
            st.markdown("# Mina's Typewriter")
            st.markdown(
                '<p class="hero-tagline">Gathering whispers from the air...</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p class="hero-blurb">Scan a folder of audio or video, '
                "transcribe only what's missing, and write plain-text "
                "transcripts with timestamped segments.</p>",
                unsafe_allow_html=True,
            )

    st.divider()


render_hero()

input_path = st.text_input("Input folder", placeholder="/path/to/audio")
output_path = st.text_input("Output folder", placeholder="/path/to/transcripts")
model_name = st.selectbox(
    "Whisper model",
    MODEL_OPTIONS,
    index=MODEL_OPTIONS.index(MODEL_NAME),
)

col_scan, col_transcribe = st.columns(2)
scan_clicked = col_scan.button("Scan", type="secondary", use_container_width=True)
transcribe_clicked = col_transcribe.button(
    "Transcribe pending", type="primary", use_container_width=True
)

if "pending" not in st.session_state:
    st.session_state.pending = []

if scan_clicked or transcribe_clicked:
    if not input_path.strip() or not output_path.strip():
        st.error("Enter both input and output folder paths.")
    else:
        input_dir = Path(input_path.strip())
        output_dir = Path(output_path.strip())
        error = validate_dirs(input_dir, output_dir)
        if error:
            st.error(error)
        elif scan_clicked:
            st.session_state.pending = missing_transcriptions(input_dir, output_dir)
            if st.session_state.pending:
                st.warning(f"{len(st.session_state.pending)} file(s) need transcription.")
            else:
                st.success("All media files already have a transcript.")
        elif transcribe_clicked:
            pending = missing_transcriptions(input_dir, output_dir)
            if not pending:
                st.success("Nothing to transcribe.")
                st.session_state.pending = []
            else:
                with st.status(f"Loading model ({model_name})...") as status:
                    model = load_model(model_name)
                    status.update(label="Model loaded.", state="running")

                progress = st.progress(0, text="Transcribing...")
                for index, filename in enumerate(pending, start=1):
                    transcribe_file(
                        model,
                        input_dir,
                        filename,
                        output_dir,
                        index=index,
                        total=len(pending),
                    )
                    progress.progress(
                        index / len(pending),
                        text=f"Transcribed {filename} ({index}/{len(pending)})",
                    )

                st.session_state.pending = missing_transcriptions(input_dir, output_dir)
                st.success(f"Finished transcribing {len(pending)} file(s).")

if st.session_state.pending:
    st.subheader("Pending files")
    for filename in st.session_state.pending:
        st.write(filename)
