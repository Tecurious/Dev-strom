import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from graph import app as graph_app, expand_idea as graph_expand_idea

st.set_page_config(page_title="Dev-Strom", page_icon="💡")
st.title("Dev-Strom ⛈️")
st.caption("Get curated project ideas for any tech stack or job role")

tech_stack = st.text_input(
    "Tech stack or Job Role",
    placeholder="e.g. LangChain, LangGraph, Deep Agents, etc.",
)
domain = st.text_input("Domain or Company (optional)", placeholder="e.g. Retail, Banking, Amazon, Walmart, etc.")
level = st.text_input("Level (optional)", placeholder="e.g. beginner, portfolio, Sr. Software Engineer, etc.")
enable_multi_query = st.checkbox("Enable multi-query search", value=False, help="Run 2-3 web queries and merge results for better coverage")
count = st.number_input("Number of ideas", min_value=1, max_value=5, value=3, step=1)

def _idea_dict(idea):
    return idea if isinstance(idea, dict) else (idea.model_dump() if hasattr(idea, "model_dump") else {})


if st.button("Get ideas", type="primary"):
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        st.error("Set OPENAI_API_KEY and TAVILY_API_KEY in .env")
        st.stop()
    if not tech_stack.strip():
        st.warning("Enter a tech stack")
        st.stop()
    inputs = {"tech_stack": tech_stack.strip()}
    if domain and domain.strip():
        inputs["domain"] = domain.strip()
    if level and level.strip():
        inputs["level"] = level.strip()
    if enable_multi_query:
        inputs["enable_multi_query"] = True
    inputs["count"] = int(count)
    with st.spinner("Fetching web context and generating ideas…"):
        result = graph_app.invoke(inputs)
    ideas = result.get("ideas", [])
    if len(ideas) != int(count):
        st.error(f"Expected {count} ideas, got {len(ideas)}")
        st.stop()
    st.session_state["ideas"] = ideas
    for k in list(st.session_state.keys()):
        if k.startswith("expanded_"):
            del st.session_state[k]

ideas = st.session_state.get("ideas", [])
if ideas:
    all_empty = all(not ((_idea_dict(idea).get("name") or "").strip()) for idea in ideas)
    if all_empty:
        st.warning("Ideas could not be generated (model returned empty or invalid response). Try again.")
    for i, idea in enumerate(ideas, 1):
        d = _idea_dict(idea)
        name = (d.get("name") or "").strip() or "Idea"
        with st.expander(f"{i}. {name}", expanded=True):
            problem = (d.get("problem_statement") or "").strip()
            st.markdown("**Problem**")
            st.write(problem if problem else "_Could not generate. Try again._")
            fits = d.get("why_it_fits") or []
            if fits:
                st.markdown("**Why it fits**")
                st.markdown("\n".join(f"- {b}" for b in fits))
            st.markdown("**Real-world value**")
            real = (d.get("real_world_value") or "").strip()
            st.write(real if real else "_Could not generate. Try again._")
            steps = d.get("implementation_plan") or []
            if steps:
                st.markdown("**Implementation plan**")
                for j, step in enumerate(steps, 1):
                    st.write(f"{j}. {step}")
            if st.button("Expand idea", key=f"expand_{i}"):
                with st.spinner("Generating deeper plan…"):
                    expanded = graph_expand_idea(d)
                st.session_state[f"expanded_{i}"] = expanded
                st.rerun()
            expanded_data = st.session_state.get(f"expanded_{i}")
            if expanded_data:
                ext = expanded_data.get("extended_plan") or []
                if ext:
                    st.markdown("**Extended plan**")
                    for j, step in enumerate(ext, 1):
                        st.write(f"{j}. {step}")
                else:
                    st.warning("Could not generate extended plan.")
