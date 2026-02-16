# Dev-Strom — Project Plan

> **Check off tasks:** Change `[ ]` to `[x]` when done. In Cursor/VS Code, open Markdown preview (e.g. `Ctrl+Shift+V` / `Cmd+Shift+V`) and click the checkbox to toggle.

## Core Idea

A system that helps developers who want to learn a tech stack but don't know what to build. User enters the **tech stack** they want to learn; the system suggests a short list of **concrete project ideas**, each with a clear **problem statement** and an **implementation plan** using that stack. Suggestions are grounded in web search results (tutorials, articles, "project ideas for X") so they feel practical and current.

## Problem Statement

Developers often get stuck in a loop: they pick a stack to learn (e.g. LangChain, LangGraph, Deep Agents) but can't land on a project idea. They hop between AI tools and docs without a clear starting point. Dev-Strom solves this by taking the stack as input and returning actionable project suggestions with problem statements and step-by-step plans, so learners can start building instead of circling.

## v1 Implementation

### Scope

- **Input:** One field — tech stack (e.g. `"LangChain, LangGraph, Deep Agents"`).
- **Output:** A short list of **3 project ideas**. Each item includes:
  - Name
  - Problem statement (1–2 sentences)
  - Why it fits (short bullets per tech in the stack)
  - Real-world value (1 sentence)
  - Implementation plan (3–5 high-level steps)

### Flow

User submits stack → **fetch web context** (mandatory) → generate 3 ideas using that context → return 3 full ideas (name + problem statement + why it fits + real-world value + implementation plan) in one response.

### Stack Roles

- **LangChain:** Prompts and a **mandatory** web search tool to ground ideas in articles, tutorials, and "project ideas for X" content.
- **LangGraph:** Orchestration — `start → fetch_web_context → generate_ideas → end`. State: `tech_stack`, `web_context`, `ideas`. Web fetch is always executed.
- **Deep Agents:** The node that generates the 3 ideas; receives `tech_stack` + `web_context`; uses LangChain for the prompt; middleware for logging/counting.

### Implementation Order

1. **Project setup** — Dependencies (LangChain, LangGraph, Deep Agents, python-dotenv); define output schema for 3 ideas.
2. **Web search tool** — LangChain tool that queries the web (e.g. Tavily, Serper, or DuckDuckGo) for "project ideas for [stack]" / tutorials / articles; returns snippets/summaries.
3. **LangGraph** — Graph with two nodes: `fetch_web_context` (uses web search tool, writes to state) and `generate_ideas` (reads `tech_stack` + `web_context`, writes `ideas`). Edges: start → fetch_web_context → generate_ideas → end.
4. **Deep Agent in generate_ideas** — Replace plain LLM call with Deep Agent that takes state and returns 3 ideas in the agreed format; attach middleware.
5. **CLI or FastAPI** — Single entry point: input tech stack string → run graph → return 3 ideas.

---

## v1 Todo

See [V1_TICKETS.md](V1_TICKETS.md) for Jira-style tickets with clear instructions. Summary:

- [x] DEVSTROM-1: Project setup and output schema
- [x] DEVSTROM-2: Web search tool (LangChain)
- [x] DEVSTROM-3: LangGraph (fetch_web_context + generate_ideas)
- [x] DEVSTROM-4: Deep Agent integration and middleware
- [x] DEVSTROM-5: CLI or FastAPI endpoint

---

*Reference this file when context is lost. Update as we move forward; new plan files can be added for later versions.*
