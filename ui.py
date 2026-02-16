import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from graph import app as graph_app

st.set_page_config(page_title="Dev-Strom", page_icon="💡")
st.title("Dev-Strom")
st.caption("Get 3 project ideas for a tech stack (web search + LLM)")

tech_stack = st.text_input(
    "Tech stack",
    value="LangChain, LangGraph, Deep Agents",
    placeholder="e.g. React, Node.js, PostgreSQL",
)

if st.button("Get ideas", type="primary"):
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        st.error("Set OPENAI_API_KEY and TAVILY_API_KEY in .env")
        st.stop()
    if not tech_stack.strip():
        st.warning("Enter a tech stack")
        st.stop()
    with st.spinner("Fetching web context and generating ideas…"):
        result = graph_app.invoke({"tech_stack": tech_stack.strip()})
    ideas = result.get("ideas", [])
    if len(ideas) != 3:
        st.error(f"Expected 3 ideas, got {len(ideas)}")
        st.stop()
    for i, idea in enumerate(ideas, 1):
        d = idea if isinstance(idea, dict) else {}
        with st.expander(f"**{i}. {d.get('name', 'Idea')}**", expanded=True):
            st.markdown("**Problem**")
            st.write(d.get("problem_statement", ""))
            fits = d.get("why_it_fits") or []
            if fits:
                st.markdown("**Why it fits**")
                st.markdown("\n".join(f"- {b}" for b in fits))
            st.markdown("**Real-world value**")
            st.write(d.get("real_world_value", ""))
            steps = d.get("implementation_plan") or []
            if steps:
                st.markdown("**Implementation plan**")
                for j, step in enumerate(steps, 1):
                    st.write(f"{j}. {step}")
