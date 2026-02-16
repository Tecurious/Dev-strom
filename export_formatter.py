def idea_to_markdown(idea: dict, extended_plan: list[str], tech_stack: str | None = None) -> str:
    name = (idea.get("name") or "").strip() or "Project"
    problem = (idea.get("problem_statement") or "").strip()
    why_fits = idea.get("why_it_fits") or []
    real_value = (idea.get("real_world_value") or "").strip()
    impl_plan = idea.get("implementation_plan") or []
    ext_plan = [s for s in extended_plan if isinstance(s, str) and s.strip()]

    lines = [
        f"# Project: {name}",
        "",
        "## 1. Context and goal",
        "",
    ]
    if tech_stack:
        lines.append(f"**Tech stack:** {tech_stack}")
        lines.append("")
    lines.append("**Problem statement**")
    lines.append(problem or "(Not specified)")
    lines.append("")
    lines.append("**Real-world value**")
    lines.append(real_value or "(Not specified)")
    lines.append("")
    lines.append("**Why this tech stack fits:**")
    for w in why_fits:
        lines.append(f"- {w}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. High-level implementation plan")
    lines.append("")
    for i, step in enumerate(impl_plan, 1):
        lines.append(f"{i}. {step}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Detailed implementation plan")
    lines.append("")
    for i, step in enumerate(ext_plan, 1):
        lines.append(f"{i}. {step}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Assumptions / Out of scope")
    lines.append("")
    lines.append("- Assume a local development environment unless stated otherwise.")
    if tech_stack:
        lines.append(f"- Use current stable versions for: {tech_stack}. Adjust to your environment if needed.")
    lines.append("- Out of scope: production deployment, CI/CD, and infrastructure unless listed above.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Next step")
    lines.append("")
    first_action = ext_plan[0] if ext_plan else (impl_plan[0] if impl_plan else "Review the plan above and set up your environment.")
    lines.append(f"**Start with:** {first_action}")
    lines.append("")
    return "\n".join(lines)
