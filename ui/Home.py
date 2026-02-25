import sys
from pathlib import Path

# Ensure project root is on sys.path so `ui.*` and `app.*` imports work
# when Streamlit runs this file as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import ui.api_client as api
from ui.components import render_idea_card

st.set_page_config(page_title="Dev-Strom", page_icon="💡")
st.title("Dev-Strom ⛈️")
st.caption("Get curated project ideas for any tech stack or job role")

tech_stack = st.text_input(
    "Tech stack or Job Role",
    value="LangChain, LangGraph, Deep Agents",
    placeholder="e.g. LangChain, LangGraph, Deep Agents, etc.",
)
domain = st.text_input(
    "Domain or Company (optional)",
    value="Retail",
    placeholder="e.g. Retail, Banking, Amazon, Walmart, etc.",
)
level = st.text_input(
    "Level (optional)",
    value="beginner",
    placeholder="e.g. beginner, portfolio, Sr. Software Engineer, etc.",
)
count = st.number_input("Number of ideas", min_value=1, max_value=5, value=3, step=1)
enable_multi_query = st.checkbox(
    "Enable multi-query search",
    value=True,
    help="Run 2-3 web queries and merge results for better coverage",
)

if st.button("Get ideas", type="primary"):
    if not tech_stack.strip():
        st.warning("Enter a tech stack")
        st.stop()

    with st.spinner("Fetching web context and generating ideas…"):
        try:
            result = api.get_ideas(
                tech_stack.strip(),
                domain=domain,
                level=level,
                count=int(count),
                enable_multi_query=enable_multi_query,
            )
        except Exception as exc:
            st.error(f"API error: {exc}")
            st.stop()

    ideas = result.get("ideas", [])
    run_id = result.get("run_id", "")

    if len(ideas) != int(count):
        st.error(f"Expected {count} ideas, got {len(ideas)}")
        st.stop()

    st.session_state["ideas"] = ideas
    st.session_state["run_id"] = run_id
    st.session_state["export_tech_stack"] = tech_stack.strip()

    # clear any previous expand state when a fresh generation runs
    for k in list(st.session_state.keys()):
        if k.startswith("expanded_"):
            del st.session_state[k]


ideas = st.session_state.get("ideas", [])
run_id = st.session_state.get("run_id", "")

if ideas:
    all_empty = all(
        not ((idea if isinstance(idea, dict) else {}).get("name") or "").strip()
        for idea in ideas
    )
    if all_empty:
        st.warning("Ideas could not be generated (model returned empty or invalid response). Try again.")

    for i, idea in enumerate(ideas, 1):
        render_idea_card(idea, i, run_id, read_only=False)

