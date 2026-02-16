# Dev-Strom v1 — Jira-style Tickets

> **Check off tasks:** Change `[ ]` to `[x]` when done. In Cursor/VS Code, open Markdown preview (`Ctrl+Shift+V` / `Cmd+Shift+V`) and click the checkbox to toggle.

Work through tickets in order (DEVSTROM-1 → DEVSTROM-5). Mark done in PLAN.md and here when complete.

---

## DEVSTROM-1 — Project setup and output schema

- [x] **Ticket completed**

**Type:** Task  
**Priority:** Highest

### Description

Set up the Dev-Strom project environment and define the canonical output schema for the 3 project ideas so all downstream components (prompt, agent, API) use the same shape.

### Acceptance criteria

- [x] Project root contains `requirements.txt` (or equivalent) with: `langchain`, `langgraph`, `deepagents`, `python-dotenv`, and the web search client of choice (e.g. `tavily-python` or `duckduckgo-search`).
- [x] A `.env.example` lists required env vars (e.g. `OPENAI_API_KEY`, `TAVILY_API_KEY` or similar for web search). No secrets committed.
- [x] A single source of truth defines the output schema for one "idea" and for the list of 3 ideas (e.g. Pydantic model(s) or a JSON schema in a doc/module). Schema fields: `name`, `problem_statement`, `why_it_fits` (list or string per tech), `real_world_value`, `implementation_plan` (list of steps).

### Instructions

1. In `Dev-Strom/`, create `requirements.txt` with pinned or minimum versions for LangChain, LangGraph, Deep Agents, python-dotenv, and one web search dependency (Tavily, Serper, or DuckDuckGo).
2. Create `.env.example` with placeholders: `OPENAI_API_KEY=`, `TAVILY_API_KEY=` (or the key for your chosen search API). Add `.env` to `.gitignore` if present.
3. Create a module or doc (e.g. `schema.py` or a "Schema" section in `PLAN.md` / `README`) that defines the structure of one idea and of the response (list of 3 ideas). Use Pydantic if you use Python; otherwise document JSON shape with field names and types.
4. Verify: `pip install -r requirements.txt` (or equivalent) runs; schema is importable or clearly documented.

---

## DEVSTROM-2 — Web search tool (LangChain)

- [x] **Ticket completed**

**Type:** Task  
**Priority:** High  
**Depends on:** DEVSTROM-1

### Description

Implement a LangChain tool that performs web search for project ideas and tutorials related to the given tech stack, and returns a concise text summary (snippets or summaries) for use in the graph state.

### Acceptance criteria

- [x] A LangChain tool (e.g. `@tool` or `StructuredTool`) exists that accepts a query string (or tech stack string from which a query is built) and returns a string of search results (snippets/summaries, not raw HTML).
- [x] The tool is callable in isolation: given a tech stack (e.g. "LangChain, LangGraph"), it returns non-empty text grounded in web results (e.g. from Tavily/Serper/DuckDuckGo).
- [x] API keys are read from environment; no hardcoded secrets.
- [x] Query construction is explicit (e.g. "project ideas for LangChain LangGraph", "tutorials for X") so the agent/graph can rely on consistent behavior.

### Instructions

1. Choose one web search provider: Tavily (tavily-python), Serper (google search API), or DuckDuckGo (duckduckgo-search). Add the dependency to `requirements.txt` if not already present.
2. Implement a function that takes `tech_stack: str`, builds a search query (e.g. `f"project ideas and tutorials for {tech_stack}"`), calls the search API, and returns a single string of relevant snippets or summaries (limit size, e.g. first 3–5 results, max 2–3k chars).
3. Wrap that function as a LangChain tool (e.g. `@tool` or `StructuredTool`) with a clear name and description so it can be bound to an agent or called from a graph node.
4. Write a minimal test or script: call the tool with a sample tech stack and assert the result is non-empty and contains text from the web. Use env vars for the API key.
5. Document in code or README how to set the required env var for the search API.

---

## DEVSTROM-3 — LangGraph (fetch_web_context + generate_ideas)

- [ ] **Ticket completed**

**Type:** Task  
**Priority:** High  
**Depends on:** DEVSTROM-1, DEVSTROM-2

### Description

Implement the LangGraph workflow with two nodes: `fetch_web_context` and `generate_ideas`. The graph must always run web search first, then generate 3 ideas using that context.

### Acceptance criteria

- [ ] A compiled LangGraph is defined with state containing at least: `tech_stack` (str), `web_context` (str), `ideas` (list or str).
- [ ] Node `fetch_web_context`: reads `tech_stack` from state; calls the web search tool (from DEVSTROM-2); writes result to state under `web_context`.
- [ ] Node `generate_ideas`: reads `tech_stack` and `web_context` from state; invokes an LLM (or placeholder) with a prompt that asks for 3 ideas in the schema from DEVSTROM-1; writes result to state under `ideas`.
- [ ] Edges: `START → fetch_web_context → generate_ideas → END`. No conditional edges required for v1.
- [ ] Invoking the graph with input `{"tech_stack": "LangChain, LangGraph, Deep Agents"}` returns state where `web_context` is non-empty and `ideas` contains 3 ideas in the agreed format (LLM can be mocked for this ticket if Deep Agent is added in DEVSTROM-4).

### Instructions

1. Define the state schema (TypedDict or Pydantic): `tech_stack: str`, `web_context: str`, `ideas: list` (or str to be parsed later). Use LangGraph's `Annotation` pattern if applicable for your LangGraph version.
2. Implement `fetch_web_context(state) -> partial state`: call the web search tool with `state["tech_stack"]`; return `{"web_context": "<search result string>"}`.
3. Implement `generate_ideas(state) -> partial state`: build a prompt that includes `state["tech_stack"]` and `state["web_context"]`, and asks the LLM to output exactly 3 ideas matching the schema from DEVSTROM-1. Call the LLM (e.g. via LangChain `ChatOpenAI` + `invoke`); parse or pass through the response and return `{"ideas": ...}`.
4. Build the graph: `StateGraph` with the state schema; `add_node("fetch_web_context", fetch_web_context)`; `add_node("generate_ideas", generate_ideas)`; `add_edge(START, "fetch_web_context")`; `add_edge("fetch_web_context", "generate_ideas")`; `add_edge("generate_ideas", END)`. Compile.
5. Add a small script or test that runs the graph with a sample `tech_stack` and checks that `web_context` and `ideas` are populated. Use a real LLM or a mock that returns valid schema.

---

## DEVSTROM-4 — Deep Agent integration and middleware

- [ ] **Ticket completed**

**Type:** Task  
**Priority:** High  
**Depends on:** DEVSTROM-3

### Description

Replace the plain LLM call in the `generate_ideas` node with a Deep Agent that receives `tech_stack` and `web_context`, and returns 3 ideas in the agreed schema. Add middleware (e.g. logging or call counting) for observability.

### Acceptance criteria

- [ ] The `generate_ideas` node uses a Deep Agent (e.g. `create_deep_agent`) instead of a raw LLM call. The agent has access to the prompt and any tools needed to produce the 3 ideas (e.g. no extra tools if the agent only needs to reason over context).
- [ ] The agent is invoked with state (e.g. `tech_stack` and `web_context` passed as user message or structured input); the agent's response is parsed into the 3-idea schema and written to state `ideas`.
- [ ] At least one middleware (e.g. `@wrap_tool_call` or equivalent) is attached to log or count agent actions; middleware is visible when the graph runs (e.g. console output or structured log).
- [ ] End-to-end: running the graph with a real tech stack produces 3 ideas that match the schema and reflect the `web_context` (ideas are grounded in search results).

### Instructions

1. Create a Deep Agent (see `deep-agents-lab` for pattern): define the agent with a model and a system/user prompt that receives `tech_stack` and `web_context` and instructs the model to output 3 ideas in the exact format defined in DEVSTROM-1 (e.g. JSON or markdown with clear sections).
2. Add middleware (e.g. wrap tool calls or agent steps) to log or count invocations; ensure the middleware is registered with the agent.
3. In the `generate_ideas` node: call `agent.invoke(...)` with the current state (e.g. a message containing `tech_stack` and `web_context`). Parse the agent's response into the schema (list of 3 ideas); handle parse errors (e.g. retry or fallback to raw text).
4. Write the parsed `ideas` into the graph state. Ensure the rest of the graph (and any CLI/API from DEVSTROM-5) still receives the same state shape.
5. Run the full graph once and confirm: middleware fires; `ideas` contains 3 items; each idea has the required fields and content that references or aligns with the web context.

---

## DEVSTROM-5 — CLI or FastAPI endpoint

- [ ] **Ticket completed**

**Type:** Task  
**Priority:** High  
**Depends on:** DEVSTROM-4

### Description

Provide a single entry point for users: input a tech stack string and receive the 3 project ideas. Implement either a CLI or a FastAPI endpoint (or both); document how to run it.

### Acceptance criteria

- [ ] User can pass the tech stack (e.g. "LangChain, LangGraph, Deep Agents") and receive the 3 ideas in the agreed schema (JSON or formatted text).
- [ ] If CLI: e.g. `python run.py "LangChain, LangGraph"` or `devstrom "LangChain, LangGraph"` prints or saves the 3 ideas. If API: e.g. `POST /ideas` with `{"tech_stack": "..."}` returns `{"ideas": [...]}`.
- [ ] The entry point uses the compiled LangGraph from DEVSTROM-3/4; env vars are loaded (e.g. dotenv) so API keys work.
- [ ] README or PLAN.md describes how to run the project (install, set env, run CLI or start server).

### Instructions

1. Create an entry script (e.g. `run.py` or `main.py`). Load environment (e.g. `load_dotenv()`). Accept tech stack from argv (CLI) or from request body (API).
2. Invoke the compiled graph with input `{"tech_stack": "<user input>"}`. Read `ideas` from the final state.
3. Output: print the 3 ideas in a readable format (CLI) or return JSON (API). Ensure the output matches the schema (e.g. valid JSON with `name`, `problem_statement`, etc.).
4. If FastAPI: add one route (e.g. `POST /ideas`) that accepts `{"tech_stack": "..."}` and returns `{"ideas": state["ideas"]}`. Document the port and how to start (e.g. `uvicorn app:app`).
5. Update README or PLAN.md with: install steps, required env vars, and the exact command(s) to run the CLI or API. Add a one-line example (e.g. "Example: python run.py 'LangChain, LangGraph'").

---

## Ticket summary

| Key          | Title                              | Done   | Depends on   |
|--------------|------------------------------------|--------|--------------|
| DEVSTROM-1   | Project setup and output schema    | [x]   | —            |
| DEVSTROM-2   | Web search tool (LangChain)        | [x]   | DEVSTROM-1   |
| DEVSTROM-3   | LangGraph (fetch + generate)       | [ ]    | DEVSTROM-1, 2 |
| DEVSTROM-4   | Deep Agent integration and middleware | [ ]  | DEVSTROM-3   |
| DEVSTROM-5   | CLI or FastAPI endpoint            | [ ]    | DEVSTROM-4   |

**v1 progress:** [ ] All tickets complete

Mark tickets complete: check "Ticket completed" and the acceptance criteria for each ticket, and the matching row in the table above. Sync with [PLAN.md](PLAN.md) v1 Todo.
