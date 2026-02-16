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

- **Internationalization (i18n)** — Multiple languages for the UI and optional localization of generated ideas. Not in v2 scope.
- **Favorites / saved ideas** — Let users mark specific ideas as favorites and list them separately from full run history. Partially overlaps with history (V2-6); can be added on top of persistence later.
- **Feedback on ideas** — Thumbs up/down or ratings on generated ideas to improve future prompts or ranking. Not in v2 scope.

---

## Reliability and scale

- **Async or background jobs** — For long-running runs, return a job id and poll for completion instead of blocking. Not in v2 scope.
- **Queue and workers** — Decouple API from graph execution with a queue (e.g. Celery, Redis) for higher throughput. Not in v2 scope.

---

*Add new items as they come up; move items into a plan (e.g. V3_TICKETS) when scheduling.*
