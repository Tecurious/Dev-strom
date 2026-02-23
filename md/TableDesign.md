# Dev-Strom V3 — Database Table Design

> Final decisions locked in. This is the reference document for V3-3 (Alembic migrations).
> All design choices are documented here with rationale.

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Auth method | Google OAuth only | Email/password deferred to V4 (out of V3 scope) |
| `updated_at` management | Application-controlled | Only one update path per table; no trigger needed |
| `expanded_ideas` on re-expand | Allow multiple rows | Preserves expansion history; app queries `ORDER BY created_at DESC LIMIT 1` |
| `web_chunks.created_at` | Omitted | Not needed at V3 scale; add in V4 |
| `ideas` storage | JSONB on `runs` | Nested structure; no need to query by individual idea fields |
| `extended_plan` storage | JSONB on `expanded_ideas` | Same reasoning as ideas |
| API key providers | Open `TEXT` field | Supports `openai`, `tavily`, and any future provider without schema changes |

---

## Entity Relationship

```
users
  │
  ├──── user_api_keys   (user_id FK, one row per provider)
  │
  └──── runs            (user_id FK, one row per generation call)
             │
             ├──── expanded_ideas   (run_id FK, one or many rows per idea position)
             │
             └──── web_chunks       (run_id FK, one row per text chunk + embedding)
```

All relationships use `ON DELETE CASCADE` — deleting a user removes all their data.

---

## Table 1 — `users`

**Purpose:** Identity anchor. One row per person who has logged in via Google OAuth.
Stores only what Google provides — we never manage passwords.

```sql
CREATE TABLE users (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id   TEXT        UNIQUE NOT NULL,   -- Google's permanent account ID
    email       TEXT        UNIQUE NOT NULL,   -- may change on Google side
    name        TEXT,                          -- display name
    avatar_url  TEXT,                          -- profile picture URL
    created_at  TIMESTAMPTZ DEFAULT now(),     -- first login
    updated_at  TIMESTAMPTZ DEFAULT now()      -- set explicitly on each OAuth upsert
);
```

**Why `google_id` and `email` are both UNIQUE:**
- `google_id` is the stable key — never changes even if email changes
- `email` is unique as a secondary lookup key for display/search

**How `updated_at` is managed:**
Set explicitly in the OAuth upsert query every time the user logs in.
No trigger — the Python auth service always includes `updated_at = now()` in the UPDATE clause.

---

## Table 2 — `user_api_keys`

**Purpose:** Encrypted storage for user-supplied API keys.
Users bring their own OpenAI and Tavily keys — Dev-Strom never pays for their LLM or search calls.

```sql
CREATE TABLE user_api_keys (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider      TEXT        NOT NULL,   -- 'openai' | 'tavily' | any future provider
    encrypted_key TEXT        NOT NULL,   -- Fernet(VAULT_SECRET_KEY).encrypt(plain_key)
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);
```

**Why no UNIQUE(user_id, provider):** Removed per design decision — allows multiple keys
per provider if needed in future. Application enforces one active key per provider via upsert logic.

**Security rule:** `encrypted_key` stores Fernet ciphertext only.
The decrypted value lives only in Python memory during the lifespan of a request.
It is never logged, never written to disk, never returned in API responses.

**Provider field is open text:** Inserting `provider = 'anthropic'` in the future
requires no schema change — just a new row.

---

## Table 3 — `runs`

**Purpose:** Permanent record of every idea generation call.
Enables: History page, cache-by-DB-lookup, MCP agent querying past ideas.

```sql
CREATE TABLE runs (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tech_stack         TEXT        NOT NULL,
    domain             TEXT,                          -- nullable
    level              TEXT,                          -- nullable
    count              INT         DEFAULT 3,
    enable_multi_query BOOLEAN     DEFAULT false,
    ideas              JSONB       NOT NULL,           -- [{name, problem_statement, ...}]
    web_context        TEXT,                          -- raw Tavily output (used for RAG)
    created_at         TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_runs_user_id    ON runs(user_id);
CREATE INDEX idx_runs_created_at ON runs(created_at DESC);
```

**Why `ideas` is JSONB and not a separate table:**
The idea structure is deeply nested (a list of objects, each containing lists of strings).
A normalized `ideas` table would require 3+ joins per history page load.
JSONB stores the whole array as one blob — one query to load a full run.
PostgreSQL can still index inside JSONB if needed in V4.

**Why two indexes:**
- `user_id` — every history query filters by user first
- `created_at DESC` — history page always shows most recent runs first

---

## Table 4 — `expanded_ideas`

**Purpose:** Stores the output of the "Expand idea" step.
Multiple expansions of the same idea are allowed — the app retrieves the most recent one.

```sql
CREATE TABLE expanded_ideas (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        UUID        NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    pid           INT         NOT NULL,     -- 1-based position of the idea in runs.ideas
    extended_plan JSONB       NOT NULL,     -- ["Step 1: ...", "Step 2: ..."]
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_expanded_ideas_run_pid ON expanded_ideas(run_id, pid);
```

**Why `pid` instead of an idea row ID:**
Ideas live inside the `runs.ideas` JSONB blob — they have no individual rows.
`pid` is the 1-based position within that array (idea #1, #2, etc.).
The pair `(run_id, pid)` uniquely identifies which idea was expanded.

**Why multiple expansions are allowed:**
Same idea expanded twice produces two rows. The app always queries:
`WHERE run_id = X AND pid = Y ORDER BY created_at DESC LIMIT 1`
This preserves expansion history without extra complexity.

**Why `created_at` is included (unlike `web_chunks`):**
Required to order multiple expansions and retrieve the latest one.

---

## Table 5 — `web_chunks`

**Purpose:** Stores web search text as overlapping chunks with vector embeddings.
This is the storage half of the RAG pipeline — the retrieval half is in V3-13.

```sql
CREATE EXTENSION IF NOT EXISTS vector;  -- enable pgvector (already done in V3-2)

CREATE TABLE web_chunks (
    id        UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id    UUID    NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    content   TEXT    NOT NULL,             -- raw chunk text (~500 chars)
    embedding vector(1536) NOT NULL         -- OpenAI text-embedding-3-small output
);

CREATE INDEX idx_web_chunks_embedding ON web_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

**How this fits the RAG pipeline — async design:**

```
User clicks Get Ideas (synchronous path — user is waiting)
  ├── Tavily search → raw web_context text
  ├── Generate ideas via LLM (uses raw text, same latency as V2)
  └── Return ideas + run_id to user  ← ✅ fast response

Background task (fires after response is sent — user does NOT wait)
  ├── Chunk web_context into ~500 char segments  (services/chunker.py)
  ├── Embed each chunk via OpenAI embeddings API  (services/embedder.py)
  └── INSERT one row per chunk into web_chunks   (services/chunk_store.py)

Future run (same user, same stack)
  ├── Cache hit in `runs` table → return instantly, no LLM call
  OR
  ├── Embed new query → similarity search on web_chunks
  └── Top-5 most relevant chunks → richer LLM context
```

**Why async matters:** Storing embeddings synchronously adds 4-7 seconds per request
(N embedding API calls + N DB inserts). Using FastAPI `BackgroundTasks`, the embedding
work happens after the response is already sent. The user gets V2-speed responses while
the embedding store is built in the background for future benefit.


**Why scoped to `run_id`:**
Each run's chunks come from a search about a specific tech stack.
Scoping prevents chunks from "React" searches contaminating "LangChain" idea generation.

**Why no `created_at`:**
Not needed at V3 scale. Chunks are always retrieved via similarity search, never by date.
Will be added in V4 if chunk pruning by age becomes necessary.

**Why IVFFlat index with `lists=50`:**
IVFFlat partitions vectors into 50 clusters. A similarity search only scans the nearest
cluster instead of every row — fast at scale without the overhead of HNSW.
`lists=50` is the standard starting point for tables under 500,000 rows.

---

## Full Schema at a Glance

```
users                    user_api_keys
──────────────────        ──────────────────────
id (PK)                   id (PK)
google_id (UNIQUE)  ◄──── user_id (FK)
email (UNIQUE)            provider
name                      encrypted_key
avatar_url                created_at
created_at                updated_at
updated_at

runs                      expanded_ideas          web_chunks
────────────────────       ──────────────────      ──────────────────────
id (PK)            ◄────── run_id (FK)    ◄────── run_id (FK)
user_id (FK)               pid                    content
tech_stack                 extended_plan (JSONB)  embedding vector(1536)
domain                     created_at
level
count
enable_multi_query
ideas (JSONB)
web_context
created_at
```

---

*Last updated: 2026-02-23. Supersedes any schema definitions in PLAN.md.*
*Migration implementation: V3-3 (Alembic). See V3_TICKETS.md for ticket details.*
