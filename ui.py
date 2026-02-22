import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import services.api_client as api

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


def _idea_dict(idea) -> dict:
    return idea if isinstance(idea, dict) else (idea.model_dump() if hasattr(idea, "model_dump") else {})


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
    all_empty = all(not ((_idea_dict(idea).get("name") or "").strip()) for idea in ideas)
    if all_empty:
        st.warning("Ideas could not be generated (model returned empty or invalid response). Try again.")

    for i, idea in enumerate(ideas, 1):
        d = _idea_dict(idea)
        pid = d.get("pid", i)
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

            # ── Expand ──────────────────────────────────────────────────────
            if st.button("Expand idea", key=f"expand_{i}"):
                with st.spinner("Generating deeper plan…"):
                    try:
                        expanded = api.expand_idea(run_id, pid)
                    except Exception as exc:
                        st.error(f"Expand failed: {exc}")
                        expanded = None
                if expanded:
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

                # ── Export ───────────────────────────────────────────────────
                tech_for_export = st.session_state.get("export_tech_stack", "")
                try:
                    md = api.export_idea(run_id, pid)
                except Exception:
                    # graceful fallback: build markdown locally if export fails
                    from export_formatter import idea_to_markdown
                    md = idea_to_markdown(d, ext, tech_for_export or None)

                fname = (name.replace(" ", "_")[:50] or "idea") + ".md"
                st.download_button(
                    "Download as Markdown",
                    data=md,
                    file_name=fname,
                    mime="text/markdown",
                    key=f"download_{i}",
                )
