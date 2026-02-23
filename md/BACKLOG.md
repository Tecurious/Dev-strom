# Dev-Strom — Backlog

Features and improvements that are not in the current v1 or v2 scope. Prioritize or schedule as needed.

---

## Post–V2 (high priority)

- **Audit web search trimming and summarization** — After V2 is complete, review how we trim and summarize web search data. Today: (1) `tools.py` caps snippets at `MAX_SNIPPETS_CHARS` (3000) and may truncate the last block to fit; (2) `graph.py` slices `web_context[:4000]` when building the prompt. There is no summarization step today—raw snippets go straight to the idea generator. Post-V2, assess whether these trim points and any new summarization (V2-2) are optimal (e.g. fair per-query caps, prompt budget, loss of signal) and document or adjust as needed.

---

## Share and history

- **Share by saved result ID** — Share a link that points to a stored run (e.g. `/result/abc123`) instead of re-running from params. Requires session history (DEVSTROM-V2-6) to be implemented first; deferred to avoid ticket dependency.

---

## API and platform

- **Rate limiting** — Throttle requests per IP or API key to protect the service (e.g. per-minute caps). Not in v2 scope.
- **Authentication** — API keys or auth for the public API so only authorized clients can call `POST /ideas`. Not in v2 scope.
- **API versioning** — Versioned routes (e.g. `/v1/ideas`, `/v2/ideas`) for backward compatibility when the schema or contract changes. Consider when introducing breaking changes.

---

## Discovery and sources

- **GitHub repo search** — Use GitHub (or similar) in addition to or instead of web search to ground ideas in real repos. Discussed for v1; skipped in favor of web search; can be revisited as an optional source.
- **Multiple search providers** — Support more than one web search backend (e.g. Serper, DuckDuckGo) with configurable choice. Current implementation is Tavily-only.

---

## UX and product

- **Idea randomization** — When a user clicks "Get Ideas" again for the **same tech stack**, the results should be meaningfully different each time rather than repeating the same ideas. Options: (a) add a `seed` or `variation_hint` to the LLM prompt that changes per request (e.g. timestamp, random adjective); (b) query the user's past runs via MCP and instruct the LLM to avoid repeating them (V3-15 already plans this); (c) inject a `temperature` bump for repeat requests. The MCP-based approach (b) is the cleanest long-term solution and is partly covered by V3-15. A quick win with (a) can be added as a one-line prompt change for V3. Defer full implementation to post-V3.
- **Internationalization (i18n)** — Multiple languages for the UI and optional localization of generated ideas. Not in v2 scope.
- **Favorites / saved ideas** — Let users mark specific ideas as favorites and list them separately from full run history. Partially overlaps with history (V2-6); can be added on top of persistence later.
- **Feedback on ideas** — Thumbs up/down or ratings on generated ideas to improve future prompts or ranking. Not in v2 scope.
- **Estimated time per project idea** — Add a small metadata tag at the top of each idea card (e.g. "Weekend Project", "1–2 Weeks", "4-Week Build") to signal expected scope and effort. Especially useful for larger, architect-level ideas so users can quickly choose work that fits their available time. Post-V2, should be implemented in a backward-compatible way (e.g. optional field or UI-only metadata) without breaking current API/CLI contracts.
- **Resume keywords per idea** — Extract 3–4 high-signal keywords per idea (e.g. `Microservices`, `Event-Driven`, `High-Availability`) and display them as metadata chips on the card. Keywords should reflect what recruiters/ATS search for and be derived from existing idea content (tech stack, patterns, architecture). This is a post-V2, additive enhancement and should avoid breaking existing response schemas by default.

---

## Reliability and scale

- **Async or background jobs** — For long-running runs, return a job id and poll for completion instead of blocking. Not in v2 scope.
- **Queue and workers** — Decouple API from graph execution with a queue (e.g. Celery, Redis) for higher throughput. Not in v2 scope.

---

## V4 — Deferred from V3

Items explicitly dropped from V3 scope with design rationale documented.

| Item | Deferred reason |
|---|---|
| `web_chunks.created_at` column | Not needed at V3 scale; add when chunk pruning by age is required |
| Email + password login | Google OAuth only for V3 — password management (bcrypt, reset flow, email verification) is 3-4 extra tickets with no learning benefit |
| Trigger-based `updated_at` | Only one update path per table in V3; application-controlled is sufficient; add trigger if multiple update paths emerge |
| Chunk pruning by age | Depends on `created_at` column deferred above; not needed until DB grows large |
| Redis caching layer | `cachetools.TTLCache` in-process is sufficient for V3; Redis needed for multi-process / distributed deployment |
| Multiple expansions history UI | Backend allows multiple expansions (no UNIQUE constraint); surfacing past expansions in the UI is a UX feature for V4 |
| Cross-user web chunk reuse | V3 scopes `web_chunks` by `run_id`; cross-user retrieval requires semantic deduplication and raises privacy questions — V4 concern |

---

*Add new items as they come up; move items into a plan (e.g. V3_TICKETS) when scheduling.*

