# Dev-Strom v2 — Jira-style Tickets

> **Check off tasks:** Change `[ ]` to `[x]` when done. Tickets are **independent**: pick any, implement, merge. Existing V1 functionality must not break.

Work in any order. Each ticket is additive; defaults preserve current behavior.

---

## DEVSTROM-V2-1 — Optional domain and level input

- [x] **Ticket completed**

**Type:** Feature  
**Priority:** High  
**Depends on:** None

### Description

Add optional `domain` (e.g. fintech, dev tools) and `level` (e.g. beginner, portfolio) to the input. Pass them through API, CLI, and UI into graph state and the idea-generation prompt so ideas are better targeted. When not provided, behavior is unchanged from V1.

### Acceptance criteria

- [x] API: `POST /ideas` accepts optional `domain` and `level` in the request body; both default to null/omit.
- [x] CLI: optional flags or args for domain and level; graph receives them when provided.
- [x] UI: optional input fields for domain and level; submit sends them when filled.
- [x] Graph state (or prompt) includes domain and level when provided; prompt instructs the model to bias ideas accordingly.
- [x] Existing calls with only `tech_stack` behave exactly as in V1.

### Instructions

1. Extend request schema (e.g. `IdeasRequest`) and graph state with optional `domain: str | None` and `level: str | None`.
2. Update `generate_ideas` (or agent prompt) to use domain/level when present; omit from prompt when null.
3. Add optional params to CLI and UI; ensure defaults do not change current behavior.

---

## DEVSTROM-V2-2 — Web context summarization (themes)

- [ ] **Ticket completed**

**Type:** Feature  
**Priority:** High  
**Depends on:** None

### Description

Add an optional step that summarizes raw web snippets into a short **themes summary** before passing to the idea generator. Use the same Deep Agent (or LLM) pattern as `generate_ideas`: a dedicated summarization call that takes `web_context` and returns a concise "themes" string (trends, common project types, tutorials/examples mentioned). This gives a **clear, defined context** for idea generation instead of trimming or dropping content arbitrarily. When disabled, behavior is unchanged (raw snippets as in V1).

### Acceptance criteria

- [ ] Optional summarization is implemented (e.g. a new graph node or tool) that takes `web_context` and returns a short themes summary string; off by default or behind a flag/param.
- [ ] When enabled: a dedicated step (node or inline before `generate_ideas`) uses Deep Agent or LLM to produce the themes summary; `generate_ideas` receives this summary as `web_context` (or a separate state key that the prompt uses).
- [ ] When disabled: raw `web_context` is passed through as today; no change to V1 behavior.
- [ ] No breaking change to API/CLI/UI; new behavior is opt-in (config or optional request param).
- [ ] Document how to enable/configure summarization.

### Instructions

1. Add a summarization step (e.g. new node `summarize_web_context` or a tool call from the fetch node) that invokes Deep Agent / LLM with a prompt like "Summarize the following web snippets into a short themes summary: trends, project types, and key resources."
2. Gate behind config or optional request param; default = current behavior (no summarization).
3. Ensure `generate_ideas` receives either the raw context (when summarization off) or the themes summary (when on); state shape can stay `web_context` (overwrite with summary) or add an optional key and pass the chosen one into the prompt.
4. Update README or code docs for the new option.

### Pending evaluation

**⚠️ Quality concern identified:** Testing shows summarization may remove valuable technical details (library names, algorithms, implementation specifics) that developers need. Raw output preserves these details better.

**Status:** Implementation complete and merged to `feature/DEVSTROM-V2-2` branch. Feature defaults to OFF (preserves V1 behavior). Do not merge to main until quality evaluation is complete.

**Next steps:**
- Evaluate summarization quality vs raw output in production testing
- Consider alternatives: extraction/formatting instead of summarization, or deprecate if quality degradation is confirmed
- See PR comments for detailed analysis

---

## DEVSTROM-V2-3 — Multi-query web context

- [x] **Ticket completed**

**Type:** Feature  
**Priority:** High  
**Depends on:** None

### Description

Run 2–3 web search queries per run (e.g. "project ideas for {stack}", "{stack} tutorials", "{stack} example projects") and merge results into a single `web_context` string. When summarization (V2-2) is enabled, the merged raw content can be summarized into themes, avoiding the need for blunt trimming. When summarization is off, use a **sensible cap** (e.g. higher limit for multi-query or a per-query cap so each query contributes proportionally) so we don't drop entire query results by trimming only the tail.

### Acceptance criteria

- [x] `fetch_web_context` (or web search tool) runs multiple queries when multi-query is enabled; results are merged into one string.
- [x] If a total length cap is applied (e.g. for prompt limits), it is implemented so each query contributes (e.g. per-query cap or proportional split), not by truncating the merged string from the end.
- [x] Single-query mode remains available (config or default); V1 behavior preserved when multi-query is off.
- [x] State key `web_context` remains a single string; no change to `generate_ideas` contract.
- [x] Document how to enable/configure multi-query (env, constant, or optional param).

### Instructions

1. In `tools.py` or the fetch node, add logic to build 2–3 queries from `tech_stack` (and optional domain), call search for each, then merge (e.g. concatenate with separators). If a total cap is needed, apply a per-query cap or proportional split so no single query dominates and we don't lose whole result sets.
2. Keep single-query as default or configurable; ensure existing tests/flows still pass.
3. Update docs (README or code) for multi-query behavior and interaction with optional summarization (V2-2).

**Note:** Implement after V2-2 (summarization) so that multi-query's larger raw context can be turned into a clear themes summary instead of blunt trimming.

---

## DEVSTROM-V2-4 — Configurable idea count and expand one idea

- [x] **Ticket completed**

**Type:** Feature  
**Priority:** High  
**Depends on:** None

### Description

Allow requesting a number of ideas other than 3 (e.g. 1–5) via an optional parameter. Each idea in the API response is assigned a **PID** (1-based id). Add an "expand" flow: call `POST /expand` with `{"pid": 1}` (id from the last `POST /ideas` response) to get a deeper implementation plan or next steps for that idea. Both are additive; default count remains 3.

### Acceptance criteria

- [x] API/CLI/UI accept optional `count` (e.g. 1–5); default 3. Graph and schema support variable-length ideas list.
- [x] "Expand one idea" available as a separate endpoint or flow: `POST /expand` accepts `{"pid": 1}` (idea id from last `POST /ideas`); returns extended plan/steps. API assigns PID (1, 2, …) to each idea in the response.
- [x] When `count` is 3 and expand is not used, behavior matches V1.
- [x] Schema (e.g. `IdeasResponse`) allows variable list length; validation and prompts updated accordingly.

### Instructions

1. Extend schema and graph to support `count`; prompt and parsing must produce `count` ideas.
2. Implement expand: new route or graph path that takes one idea and calls the LLM for a deeper plan; return structured result.
3. Wire optional count through API, CLI, UI; ensure defaults preserve V1.

---

## DEVSTROM-V2-5 — Export (markdown, CLI --output, UI download)

- [ ] **Ticket completed**

**Type:** Feature  
**Priority:** Medium  
**Depends on:** None

### Description

Allow exporting the generated ideas as a markdown file or downloadable asset. CLI: e.g. `--output ideas.md`. API: optional query param or endpoint that returns markdown. UI: "Download" button that saves a file. No change to existing response format when export is not used.

### Acceptance criteria

- [ ] CLI: flag or option to write ideas to a markdown file (path or stdout); existing default (print to terminal) unchanged.
- [ ] API: way to get ideas as markdown (e.g. `Accept: text/markdown` or `?format=md` on existing endpoint, or separate endpoint).
- [ ] UI: button/link to download ideas as a file (e.g. .md); current on-screen display unchanged.
- [ ] Export format is documented (e.g. one idea per section with all schema fields).

### Instructions

1. Add a small formatter (ideas list → markdown string) in a shared module or script.
2. CLI: add `--output FILE` (or similar); when set, write markdown to file.
3. API: add format option or endpoint; return markdown when requested.
4. UI: add download action using the same formatter; trigger file save in browser.

---

## DEVSTROM-V2-6 — Session history and persistence

- [ ] **Ticket completed**

**Type:** Feature  
**Priority:** Medium  
**Depends on:** None

### Description

Persist runs (input + output) so users can view past results. Use a simple store (e.g. SQLite, JSON file, or in-memory with optional file backup). UI shows a list of past runs; optional API to list or get by id. Existing flows work unchanged when not using history.

### Acceptance criteria

- [ ] Each run (tech_stack + optional params + ideas) can be stored with a unique id and timestamp.
- [ ] UI: section or page to list recent runs; clicking one shows the ideas (read-only).
- [ ] Optional: API endpoint(s) to list history or get run by id; not required for CLI or core POST /ideas.
- [ ] Storage is additive; no change to existing POST /ideas or CLI when history is not queried.
- [ ] Document storage choice and how to clear or disable if needed.

### Instructions

1. Choose storage (SQLite, file, etc.); implement a thin layer to save and load runs.
2. After a successful graph run, optionally save (tech_stack, params, ideas, id, timestamp).
3. UI: add history list and detail view; API: optional GET /history and GET /runs/{id} if desired.
4. Ensure existing behavior is unchanged when history is not used.

---

## DEVSTROM-V2-7 — Shareable link (input params only)

- [ ] **Ticket completed**

**Type:** Feature  
**Priority:** Medium  
**Depends on:** None

### Description

Generate a URL that encodes the current input (tech_stack and optional domain, level). When someone opens the link, the app loads with those values pre-filled and can run the graph again (no persistence of results required). Enables sharing a "query" not a stored result.

### Acceptance criteria

- [ ] UI: way to copy or open a shareable link that contains tech_stack (and optional domain, level) as query params.
- [ ] Opening the link in the app pre-fills the form and does not auto-run unless desired; user can click "Get ideas" to run.
- [ ] No dependency on history or stored results; link is stateless.
- [ ] API/CLI unchanged; feature is UI and URL handling only (and possibly a simple landing route that redirects or renders UI with params).

### Instructions

1. In the UI, build a URL with query params (e.g. `?tech_stack=React&domain=fintech`); add "Copy link" or "Share" control.
2. On load, parse query params and pre-fill the form; do not change existing behavior when no params present.
3. If the app is SPA or multi-page, ensure the share URL opens the right view with params applied.

---

## DEVSTROM-V2-8 — Retry and schema validation

- [ ] **Ticket completed**

**Type:** Task  
**Priority:** High  
**Depends on:** None

### Description

Add retry logic when idea parsing fails (e.g. invalid JSON or wrong shape) and validate parsed ideas against the schema before returning. Return clear, non-500 errors when validation fails after retries. Improves reliability without changing the success-path contract.

### Acceptance criteria

- [ ] On parse failure in `generate_ideas`, retry a defined number of times (e.g. 1–2 retries) before failing.
- [ ] Parsed ideas are validated against the schema (e.g. Pydantic); invalid items are rejected with a clear error message or fallback (e.g. generic idea placeholder).
- [ ] API returns appropriate status and message (e.g. 422 or 500 with detail) when validation fails after retries; success response shape unchanged.
- [ ] CLI/UI show a clear error when the graph returns invalid data after retries.
- [ ] V1 success path unchanged; only failure handling is improved.

### Instructions

1. In the graph node that parses ideas, wrap parsing in a retry loop; on repeated failure, return a structured error or fallback.
2. Validate each idea against `ProjectIdea` (or current schema); if validation fails, retry or fail with clear message.
3. Ensure API/CLI/UI surface the error without breaking existing success behavior.

---

## DEVSTROM-V2-9 — Caching (by input key)

- [ ] **Ticket completed**

**Type:** Task  
**Priority:** Medium  
**Depends on:** None

### Description

Cache graph results keyed by (tech_stack, domain?, level?) so identical requests within a TTL return the cached ideas without calling web search or the LLM. Cache is optional (e.g. env flag or default off) so V1 behavior is unchanged when disabled.

### Acceptance criteria

- [ ] When caching is enabled, a cache key is derived from the graph input (tech_stack and any optional params); result (ideas + optional metadata) is stored and reused for a configurable TTL.
- [ ] When cache is disabled or not configured, every request runs the graph as in V1.
- [ ] Cache storage is simple (e.g. in-memory dict, or file-based, or Redis); document choice and limits.
- [ ] No change to response shape; cached response is identical to a fresh run.
- [ ] Document how to enable/disable and set TTL.

### Instructions

1. Add a cache layer (e.g. wrapper around graph invoke, or middleware) that checks the key before invoking the graph; on hit, return cached value.
2. Key: normalize (tech_stack, domain, level) into a string or tuple; TTL from config/env.
3. Make caching opt-in or default off so existing deployments are unchanged.
4. Document configuration and behavior.

---

## DEVSTROM-V2-10 — Structured logging and optional tracing

- [ ] **Ticket completed**

**Type:** Task  
**Priority:** Medium  
**Depends on:** None

### Description

Add structured logging (request id, step, latency, errors) across the graph and API. Optionally integrate with a tracing solution (e.g. LangSmith) for deeper observability. Logging is additive; no change to business logic or response format.

### Acceptance criteria

- [ ] Each request (API or CLI run) has a request id (e.g. UUID); it is logged and optionally included in response headers or logs.
- [ ] Key steps (fetch_web_context, generate_ideas) log start/end and duration; errors are logged with context.
- [ ] Log format is structured (e.g. JSON or key=value) for easier parsing.
- [ ] Optional: LangSmith or similar tracing when configured; when not configured, only application logs are used.
- [ ] Existing behavior and response format unchanged; logging is additive.

### Instructions

1. Generate and propagate a request id in API and CLI entry points; add to log context.
2. In graph nodes or around invoke, log step name, duration, and optional payload size; on exception, log error and request id.
3. Add optional integration for LangSmith (or chosen tracer) behind a config flag; document env vars and setup.
4. Ensure no functional change when tracing is off; logs can be minimal when not configured.

---

## Ticket summary (v2)

| Key             | Title                              | Done | Dependencies |
|-----------------|------------------------------------|------|---------------|
| DEVSTROM-V2-1   | Optional domain and level input    | [x]  | None          |
| DEVSTROM-V2-2   | Web context summarization (themes) | [ ]  | None          |
| DEVSTROM-V2-3   | Multi-query web context            | [x]  | None          |
| DEVSTROM-V2-4   | Configurable count + expand idea   | [x]  | None          |
| DEVSTROM-V2-5   | Export (markdown, CLI, UI)         | [ ]  | None          |
| DEVSTROM-V2-6   | Session history + persistence     | [ ]  | None          |
| DEVSTROM-V2-7   | Shareable link (input params)     | [ ]  | None          |
| DEVSTROM-V2-8   | Retry and schema validation       | [ ]  | None          |
| DEVSTROM-V2-9   | Caching by input key              | [ ]  | None          |
| DEVSTROM-V2-10  | Structured logging and tracing    | [ ]  | None          |

**v2 progress:** [x] 3/10 complete

Pick any ticket; complete and merge in any order. Preserve existing V1 functionality.
