"""History page — browse and view past idea-generation runs.

Data comes from GET /history and GET /runs/{run_id} via api_client.
Ideas are rendered in read-only mode using the shared render_idea_card component.
"""

import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path for sub-page imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

import ui.api_client as api
from ui.components import render_idea_card

st.set_page_config(page_title="Dev-Strom — History", page_icon="📋")
st.title("📋 History")
st.caption("Browse your past idea-generation runs")

# ── Pagination state ──────────────────────────────────────────────────────────

PAGE_SIZE = 10

if "history_offset" not in st.session_state:
    st.session_state["history_offset"] = 0
if "history_runs" not in st.session_state:
    st.session_state["history_runs"] = []
if "selected_run_id" not in st.session_state:
    st.session_state["selected_run_id"] = None

# ── Fetch runs ────────────────────────────────────────────────────────────────


def _load_runs(offset: int = 0, append: bool = False) -> None:
    """Fetch a page of runs from the API and store in session state."""
    try:
        result = api.get_history(limit=PAGE_SIZE, offset=offset)
        new_runs = result.get("runs", [])
        if append:
            st.session_state["history_runs"].extend(new_runs)
        else:
            st.session_state["history_runs"] = new_runs
        st.session_state["history_offset"] = offset
    except Exception as exc:
        st.error(f"Failed to load history: {exc}")


# Initial load
if not st.session_state["history_runs"] and st.session_state["history_offset"] == 0:
    _load_runs(offset=0)

runs = st.session_state["history_runs"]

# ── Route: detail view vs. run list ──────────────────────────────────────────

selected_id = st.session_state.get("selected_run_id")

if selected_id:
    # ── Run detail ────────────────────────────────────────────────────────
    try:
        run_detail = api.get_run_detail(selected_id)
    except Exception as exc:
        st.error(f"Failed to load run: {exc}")
        st.stop()

    tech = run_detail.get("tech_stack", "")
    ideas = run_detail.get("ideas", [])

    if st.button("← Back to list"):
        st.session_state["selected_run_id"] = None
        st.rerun()

    st.subheader(f"🔍 {tech}")
    st.caption(f"Run ID: `{selected_id}` · {len(ideas)} idea(s)")

    for i, idea in enumerate(ideas, 1):
        render_idea_card(idea, i, selected_id, read_only=False)

else:
    # ── Run list ──────────────────────────────────────────────────────────
    if not runs:
        st.info("No history yet. Go to the Home page and generate some ideas!")
        st.stop()

    st.markdown(f"**{len(runs)} run(s) loaded**")

    for run in runs:
        run_id = run["run_id"]
        tech = run.get("tech_stack", "Unknown")
        domain = run.get("domain") or ""
        level = run.get("level") or ""
        created = run.get("created_at", "")

        # Format timestamp
        try:
            dt = datetime.fromisoformat(created)
            ts_label = dt.strftime("%b %d, %Y  %I:%M %p")
        except (ValueError, TypeError):
            ts_label = created

        # Build label
        meta_parts = [p for p in [domain, level] if p]
        meta = f" · {' · '.join(meta_parts)}" if meta_parts else ""
        label = f"**{tech}**{meta}  —  {ts_label}"

        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(label)
        with col2:
            if st.button("View", key=f"view_{run_id}"):
                st.session_state["selected_run_id"] = run_id
                st.rerun()

    st.divider()

    # ── Load more ─────────────────────────────────────────────────────
    if len(runs) >= PAGE_SIZE and len(runs) % PAGE_SIZE == 0:
        if st.button("Load more"):
            _load_runs(
                offset=st.session_state["history_offset"] + PAGE_SIZE,
                append=True,
            )
            st.rerun()

