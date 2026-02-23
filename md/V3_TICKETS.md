# Dev-Strom V3 — Jira-style Tickets

> Work through tickets in order (V3-1 → V3-19). Each ticket is self-contained with a concept explanation inside the Description, acceptance criteria, and plain-English instructions. Mark `[ ]` → `[x]` when done.
> **V3-1, V3-2, V3-3** are hard prerequisites — complete them before anything else.

---

## Ticket Summary

| Key             | Title                                            | Done | Depends on     |
|-----------------|--------------------------------------------------|------|----------------|
| DEVSTROM-V3-1   | Decouple Streamlit → FastAPI HTTP calls          | [x]  | None           |
| DEVSTROM-V3-2   | PostgreSQL install + db.py connection service    | [x]  | None           |
| DEVSTROM-V3-3   | Alembic setup + all 5 table migrations           | [ ]  | V3-2           |
| DEVSTROM-V3-4   | Google OAuth2 + JWT service (backend)            | [ ]  | V3-1, V3-3     |
| DEVSTROM-V3-5   | JWT middleware + protect existing API routes     | [ ]  | V3-4           |
| DEVSTROM-V3-6   | Streamlit login page + JWT session handling      | [ ]  | V3-4           |
| DEVSTROM-V3-7   | API Key Vault — service + FastAPI routes         | [ ]  | V3-5           |
| DEVSTROM-V3-8   | Streamlit Settings page (key management UI)      | [ ]  | V3-6, V3-7     |
| DEVSTROM-V3-9   | Wire graph + tools to use user-supplied keys     | [ ]  | V3-7           |
| DEVSTROM-V3-10  | Run service + FastAPI history endpoints          | [ ]  | V3-5, V3-9     |
| DEVSTROM-V3-11  | Streamlit History page                           | [ ]  | V3-6, V3-10    |
| DEVSTROM-V3-12  | Web chunking + embedding + pgvector storage      | [ ]  | V3-3           |
| DEVSTROM-V3-13  | Semantic retrieval at idea-generation time       | [ ]  | V3-12, V3-10   |
| DEVSTROM-V3-14  | Setup MCP Postgres server (standalone)           | [ ]  | V3-3           |
| DEVSTROM-V3-15  | Integrate MCP into DeepAgent                     | [ ]  | V3-14, V3-10   |
| DEVSTROM-V3-16  | Per-user TTL caching layer (cachetools)          | [ ]  | V3-5           |
| DEVSTROM-V3-17  | React + Vite scaffold + routing + API client     | [ ]  | V3-1           |
| DEVSTROM-V3-18  | React auth (login page + JWT flow)               | [ ]  | V3-17, V3-4    |
| DEVSTROM-V3-19  | React Home + History + Settings pages            | [ ]  | V3-18          |

**V3 Progress: 2/19 complete**

---

---

## DEVSTROM-V3-1 — Decouple Streamlit → FastAPI HTTP Calls

- [x] **Ticket completed**

**Type:** Architecture refactor
**Priority:** Highest — must be done first
**Depends on:** None

### Description

Currently `ui.py` imports `graph.py` directly and calls the graph as a Python function. This tightly couples the Streamlit UI to the backend. If you later swap Streamlit for React, you'd need to rewrite all graph-calling logic in the new frontend.

The fix is to make Streamlit call FastAPI over HTTP, exactly like any other client (React, mobile app, CLI) would. The UI becomes a pure display layer with no knowledge of the graph internals. All business logic stays in FastAPI. This is the pattern that makes any future frontend swap completely seamless — zero backend changes required.

A thin `services/api_client.py` module will handle all HTTP calls so the Streamlit pages only need to call functions like `get_ideas(payload)` or `expand_idea(run_id, pid)` without knowing anything about the underlying HTTP details.

### Acceptance Criteria

- [x] `ui.py` contains zero imports from `graph.py` or `tools.py`.
- [x] All network calls go through a new `services/api_client.py` module using the `httpx` library.
- [x] The FastAPI base URL is read from an `API_BASE_URL` environment variable, defaulting to `http://localhost:8000`.
- [x] The `run_id` returned by the `/ideas` endpoint is stored in Streamlit session state and passed to all subsequent expand and export calls.
- [x] The full app flow (generate → expand → download) works end-to-end with both servers running simultaneously.
- [x] `API_BASE_URL` is documented in `.env.example`.

### Instructions

1. Add `httpx` to `requirements.txt`.
2. Create a `services/` folder in the project root if it does not already exist.
3. Create `services/api_client.py` with individual functions for each FastAPI endpoint: one for fetching ideas, one for expanding an idea, and one for exporting. Each function takes the relevant parameters, makes an HTTP POST call to the FastAPI server, raises an error if the response is not successful, and returns the parsed JSON or text response.
4. Update `ui.py` to import and use `api_client` functions instead of calling the graph directly. Remove all imports from `graph.py` and `tools.py`.
5. Store the `run_id` field from the `/ideas` response in `st.session_state` so it is available when the user clicks Expand or Export.
6. Add `API_BASE_URL=http://localhost:8000` to `.env.example`.
7. Test by starting the FastAPI server and the Streamlit server in separate terminals. Verify the complete flow works without errors.

---

---

## DEVSTROM-V3-2 — PostgreSQL Install + `services/db.py` Connection Service

- [ ] **Ticket completed**

**Type:** Infrastructure
**Priority:** Highest — required before all database-dependent tickets
**Depends on:** None (can be done in parallel with V3-1)

### Description

PostgreSQL is a relational database that stores data in tables with rows and columns, linked together by foreign keys. It is the most widely used production database in professional software projects.

This ticket sets up the PostgreSQL server locally and creates a Python service module that the rest of the application uses to open and close database connections. Rather than connecting to the database directly from multiple places in the code, a single `services/db.py` module manages the connection pool and exposes a clean interface for running queries safely.

The `pgvector` extension is also enabled in this ticket. It is a PostgreSQL plugin that adds a special column type for storing vector embeddings, which will be used later in the RAG (semantic search) tickets.

SQLAlchemy is the Python library used to communicate with PostgreSQL. It handles low-level connection management and lets the rest of the code use Python objects instead of raw SQL strings.

### Acceptance Criteria

- [ ] PostgreSQL is running locally and accessible. A database named `devstrom` exists.
- [ ] The `pgvector` extension is enabled inside the `devstrom` database.
- [ ] The `psycopg2-binary`, `sqlalchemy>=2.0`, `pgvector`, and `alembic` packages are added to `requirements.txt`.
- [ ] `services/db.py` exists and exposes a SQLAlchemy engine and a `get_session()` context manager for safe database access.
- [ ] The `DATABASE_URL` environment variable is the only place the connection string is defined — no hardcoded values anywhere in the codebase.
- [ ] A simple connectivity test (connecting and running a basic query) passes without errors.
- [ ] `DATABASE_URL` is documented in `.env.example`.

### Instructions

1. Install PostgreSQL locally using Docker or the system package manager. Create a database named `devstrom` and confirm it is accessible.
2. Connect to the `devstrom` database and run the command to enable the `vector` extension (part of pgvector). Confirm it is listed as an installed extension.
3. Add the four required packages to `requirements.txt` and install them.
4. Create `services/db.py`. This file should define a SQLAlchemy engine using the `DATABASE_URL` environment variable, a session factory, a `Base` class for ORM models, and a `get_session()` context manager that automatically commits on success and rolls back on error.
5. Write a simple script or one-liner that imports the engine and runs a trivial query (such as `SELECT 1`) to confirm the connection is working.
6. Add `DATABASE_URL=postgresql://postgres:devstrom@localhost:5432/devstrom` to `.env.example`.

---

---

## DEVSTROM-V3-3 — Alembic Setup + All 5 Table Migrations

- [ ] **Ticket completed**

**Type:** Infrastructure
**Priority:** Highest
**Depends on:** V3-2

### Description

A database migration is a versioned file that describes a change to the database schema — creating a table, adding a column, or modifying an index. Alembic is Python's standard migration tool. Instead of manually running SQL `CREATE TABLE` commands every time a new server is set up, you run a single Alembic command and all migrations apply automatically in order.

This ticket creates the initial migration that defines all five tables for the Dev-Strom V3 database: `users`, `user_api_keys`, `runs`, `expanded_ideas`, and `web_chunks`. The schema for each table is described in `PLAN.md`.

### Acceptance Criteria

- [ ] Alembic is initialized in the project root. The `alembic.ini` configuration file and `migrations/` directory both exist.
- [ ] Alembic is configured to read `DATABASE_URL` from the environment rather than using a hardcoded connection string.
- [ ] The initial migration file creates all five tables with the correct columns, data types, foreign keys, unique constraints, and indexes as defined in `PLAN.md`.
- [ ] The `web_chunks.embedding` column uses the `vector(1536)` type provided by the pgvector SQLAlchemy integration.
- [ ] Running `alembic upgrade head` on a fresh database creates all five tables without errors.
- [ ] Running `alembic downgrade -1` removes the tables cleanly.
- [ ] `alembic upgrade head` is idempotent — running it twice does not cause errors.

### Instructions

1. Run `alembic init migrations` in the project root to create the Alembic scaffold.
2. Edit `alembic.ini` to remove the hardcoded `sqlalchemy.url` value and replace it with a reference to the `DATABASE_URL` environment variable.
3. Edit `migrations/env.py` to load the `.env` file using `python-dotenv` and set the SQLAlchemy URL from the environment before Alembic runs any migrations.
4. Create the initial migration file either by running Alembic's autogenerate command or writing it manually. The migration must include all five tables from the schema in `PLAN.md`: `users`, `user_api_keys`, `runs`, `expanded_ideas`, and `web_chunks`.
5. Ensure UUID primary keys use `gen_random_uuid()` as the default, foreign keys use `ON DELETE CASCADE`, and the `web_chunks.embedding` column is typed as `vector(1536)` using the pgvector SQLAlchemy type.
6. Add the IVFFlat index on `web_chunks.embedding` for fast similarity search, and standard B-tree indexes on `runs.user_id` and `runs.created_at DESC`.
7. Run `alembic upgrade head` and verify all five tables appear in the database.
8. Run `alembic downgrade -1` and verify the tables are removed. Then run `alembic upgrade head` again to confirm idempotency.

---

---

## DEVSTROM-V3-4 — Google OAuth2 + JWT Service (Backend)

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** High
**Depends on:** V3-1, V3-3

### Description

OAuth2 is a protocol where your application delegates the "who is this user?" question to a trusted third party — Google in this case. Instead of managing passwords, Google verifies the user's identity and tells your application their email address, display name, and a unique Google account ID. Your application never handles or stores passwords.

After Google confirms the user's identity, your FastAPI server issues a JWT (JSON Web Token). A JWT is a compact, signed token that encodes the user's ID and an expiry time. It has three sections separated by dots: a header, a payload, and a cryptographic signature. Any server that knows your secret key can verify the signature instantly without hitting the database. This is called stateless authentication — the JWT itself carries the proof of identity.

This ticket covers only the backend: registering the application with Google, building the auth service, and creating the FastAPI routes for login, OAuth callback, and fetching the current user's profile.

### Acceptance Criteria

- [ ] A Google Cloud OAuth2 application is registered. `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`.
- [ ] `services/auth.py` contains a function to create a signed JWT from a user ID and email, and a function to verify and decode a JWT, raising an error if it is invalid or expired.
- [ ] `services/auth.py` contains a function that upserts a user row in the `users` table given a Google ID, email, name, and avatar URL. It returns the user record.
- [ ] FastAPI `GET /auth/login` redirects the browser to Google's OAuth consent page.
- [ ] FastAPI `GET /auth/callback` receives the Google authorization code, exchanges it for user information, calls the upsert function, issues a JWT, and returns the JWT and basic user info in the response.
- [ ] FastAPI `GET /auth/me` accepts a valid JWT and returns the current user's profile.
- [ ] JWT expiry is configurable via a `JWT_TTL_DAYS` environment variable, defaulting to 7 days.
- [ ] `JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `JWT_TTL_DAYS` are all documented in `.env.example`.

### Instructions

1. Go to Google Cloud Console, navigate to APIs and Services, then Credentials. Create a new OAuth 2.0 Client ID of type "Web application". Set the authorized redirect URI to `http://localhost:8000/auth/callback`. Copy the client ID and secret into `.env`.
2. Add `authlib` and `python-jose[cryptography]` to `requirements.txt`.
3. Generate a random hex string to use as `JWT_SECRET_KEY` and add it to `.env`. Document it in `.env.example`.
4. Create `services/auth.py` with three components: a JWT creation function that signs a payload containing the user ID and email with an expiry timestamp; a JWT verification function that decodes and validates a token, raising a clear error if invalid or expired; and a database upsert function that inserts a new user if the Google ID does not exist, or updates the name and avatar if it does.
5. Add the three auth routes to `api.py`. The login route builds a Google OAuth URL using `authlib` and redirects. The callback route exchanges the code for user info using Google's token endpoint, calls the auth service upsert, creates a JWT, and returns it. The `me` route reads the JWT from the `Authorization` header and returns the user's profile.
6. Test the full auth flow manually: visit `GET /auth/login`, complete the Google sign-in, and confirm that `GET /auth/callback` returns a JWT string.

---

---

## DEVSTROM-V3-5 — JWT Middleware + Protect Existing API Routes

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** High
**Depends on:** V3-4

### Description

FastAPI has a dependency injection system that lets you write a reusable function — called a dependency — and attach it to routes that require authentication. When a route declares a `get_current_user` dependency, FastAPI automatically calls that function before the route handler runs. If the token is missing or invalid, FastAPI returns a 401 Unauthorized response and never executes the route handler.

This is how authentication is applied consistently across all protected routes without duplicating auth logic in every handler. This ticket wires the JWT verification from V3-4 into FastAPI's dependency system and applies it to all existing data routes.

### Acceptance Criteria

- [ ] A `get_current_user` function exists that reads the `Authorization: Bearer <token>` header from the incoming request, calls `auth.verify_jwt`, and returns the decoded user payload. It raises an HTTP 401 if the header is missing or the token is invalid or expired.
- [ ] The dependency is applied to all existing routes: `POST /ideas`, `POST /expand`, and `POST /export`.
- [ ] The auth routes (`GET /auth/login`, `GET /auth/callback`) are excluded from the authentication requirement.
- [ ] Calling a protected route without a token returns a 401 response with a clear error message.
- [ ] Calling a protected route with a valid JWT in the `Authorization` header returns the expected response.

### Instructions

1. Add a `get_current_user` function to `api.py` or `services/auth.py`. Use FastAPI's `HTTPBearer` security class to extract the token from the Authorization header automatically. Call `auth.verify_jwt` on the extracted token. Return the decoded payload on success. Raise an `HTTPException` with status 401 on failure.
2. Add `current_user: dict = Depends(get_current_user)` as a parameter to `post_ideas`, `post_expand`, and `post_export`.
3. Confirm the auth routes do not include this dependency.
4. Test with a tool like `curl` or Postman: send a request to `POST /ideas` without a token and confirm a 401 is returned. Then send the same request with a valid JWT in the Authorization header and confirm a normal response is returned.

---

---

## DEVSTROM-V3-6 — Streamlit Login Page + JWT Session Handling

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** High
**Depends on:** V3-4

### Description

Streamlit reruns the entire script on every user interaction. A JWT stored in `session_state` persists across reruns within the same browser session but is cleared when the tab closes.

The auth gate pattern is: at the top of every page, check whether a JWT exists in `session_state`. If it does not, show a login page and stop rendering the rest of the page. If it does, allow the page to render. This creates a consistent login wall across the entire Streamlit app without repeating auth logic on every page.

After a successful Google OAuth flow, the JWT arrives as a query parameter in the redirect URL. Streamlit reads it, stores it in `session_state`, and removes it from the URL to keep the browser address clean.

### Acceptance Criteria

- [ ] The Streamlit app is restructured as a multi-page app. `ui.py` is moved to `pages/1_🏠_Home.py` and a new `app.py` serves as the entry point.
- [ ] A shared `require_auth()` helper function in `services/ui_auth.py` checks for a JWT in session state, shows a login page with a "Login with Google" button if absent, and calls `st.stop()` so the rest of the page does not render.
- [ ] `require_auth()` is called at the top of every page file.
- [ ] After the Google OAuth redirect, the JWT in the URL query parameters is read and stored in `session_state`, then removed from the URL.
- [ ] All HTTP calls made by `api_client.py` automatically include the JWT from `session_state` in the `Authorization: Bearer` header.
- [ ] A Logout button in the sidebar clears the JWT from `session_state` and triggers a page rerun, returning the user to the login screen.

### Instructions

1. Rename `ui.py` to `pages/1_🏠_Home.py`. Create `app.py` as the root entry point that handles the auth gate and sidebar navigation.
2. Create `services/ui_auth.py` with a `require_auth()` function. The function checks `st.session_state` for a key named `jwt`. If missing, it renders the login page — a title, a short description, and a link button pointing to `GET /auth/login` on the FastAPI server. Then it calls `st.stop()`.
3. Add logic at the top of `app.py` to check for a `jwt` query parameter in the URL using `st.query_params`. If found, store it in `session_state["jwt"]` and clear the query params.
4. Update `services/api_client.py` so all request functions read the JWT from `st.session_state` and include it in the `Authorization` header on every call.
5. Add a Logout button to the Streamlit sidebar. When clicked, delete `session_state["jwt"]` and call `st.rerun()`.
6. Add `require_auth()` as the first line of every Streamlit page file.
7. Test the full flow: open the app in a browser, click Login with Google, complete sign-in, confirm the app renders with the user logged in, then click Logout and confirm the login screen reappears.

---

---

## DEVSTROM-V3-7 — API Key Vault — Service + FastAPI Routes

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** High
**Depends on:** V3-5

### Description

Users provide their own OpenAI and Tavily API keys, which must be stored securely. Storing them in plain text is unacceptable. The approach is symmetric encryption using Fernet, a scheme from Python's `cryptography` library.

Symmetric encryption means the same secret key is used to both encrypt and decrypt. The server's secret key lives only in `.env`. When a user saves their API key, the application encrypts it with this server secret and stores the encrypted value in the `user_api_keys` table. When the user logs in later, the encrypted value is read from the database and decrypted in memory. The decrypted key is never written back to disk or logged — it only ever lives in memory.

Even if an attacker steals the entire database dump, they cannot recover the API keys without also having the server's `.env` file — which is a much higher threshold.

### Acceptance Criteria

- [ ] A `VAULT_SECRET_KEY` is generated and stored in `.env`. It is documented in `.env.example`.
- [ ] `services/key_vault.py` contains an `encrypt(plain_text)` function that returns an encrypted string, and a `decrypt(cipher_text)` function that returns the original plain text. Both use Fernet.
- [ ] `POST /vault/keys` accepts a provider name (`openai` or `tavily`) and a raw API key. It encrypts the key and upserts the row in `user_api_keys` for the current user. Requires authentication.
- [ ] `GET /vault/keys` returns the current user's stored providers with masked key values. The mask shows only the last four characters preceded by bullet characters. Requires authentication.
- [ ] `DELETE /vault/keys/{provider}` deletes the specified provider's key for the current user. Requires authentication.
- [ ] A private vault session endpoint (or an extension to `GET /auth/me`) returns both keys decrypted, used once immediately after login to load keys into session state. This is the only moment decrypted keys travel over the network.
- [ ] The `cryptography` package is added to `requirements.txt`.

### Instructions

1. Add `cryptography` to `requirements.txt`.
2. Generate a Fernet secret key by running a short Python snippet using `Fernet.generate_key()`. Paste the output as `VAULT_SECRET_KEY` in `.env` and document the variable name in `.env.example`.
3. Create `services/key_vault.py` with two functions: `encrypt` takes a plain text string, creates a Fernet instance using the server secret from the environment, encrypts the string, and returns it as a UTF-8 string. `decrypt` does the reverse.
4. Add a `POST /vault/keys` route to `api.py`. It reads the provider and key from the request body, validates that the provider is either `openai` or `tavily`, encrypts the key using `key_vault.encrypt`, and inserts or updates the row in `user_api_keys` for the current user.
5. Add a `GET /vault/keys` route that queries `user_api_keys` for the current user, masks each key (eight bullet characters followed by the last four characters of the encrypted value is acceptable), and returns the list.
6. Add a `DELETE /vault/keys/{provider}` route that deletes the matching row.
7. Add a `GET /auth/session` route (or extend `/auth/me`) that decrypts and returns both API keys for the current logged-in user. This is called once right after login to load the keys into Streamlit session state.

---

---

## DEVSTROM-V3-8 — Streamlit Settings Page (Key Management UI)

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Medium
**Depends on:** V3-6, V3-7

### Description

This ticket builds the Settings page in Streamlit where users can view, add, update, and delete their API keys. It is a pure frontend ticket — all backend logic was implemented in V3-7.

The UX principle for sensitive fields: display only the masked key. To update a key, the user types the new value into a password-type input field and clicks Save. This prevents accidental exposure of the key on screen.

### Acceptance Criteria

- [ ] A `pages/3_⚙️_Settings.py` page exists and is accessible from the Streamlit sidebar.
- [ ] The page displays the current user's name and email fetched from `GET /auth/me`.
- [ ] The masked OpenAI and Tavily keys are shown, fetched from `GET /vault/keys`.
- [ ] An Update flow exists for each provider: a password-type text input and a Save button. Clicking Save calls `POST /vault/keys` and shows a success or error message.
- [ ] A Delete button exists for each provider. Clicking it asks for confirmation and then calls `DELETE /vault/keys/{provider}`.
- [ ] After a successful save or delete, the masked key display refreshes automatically.
- [ ] `require_auth()` is called at the top of the page.

### Instructions

1. Create `pages/3_⚙️_Settings.py`. Add `require_auth()` as the first line.
2. Add helper functions to `api_client.py` for three new actions: fetching the current user's profile, fetching vault keys, saving a vault key, and deleting a vault key.
3. Fetch and display the user's name and email using the profile API call.
4. Fetch and display the masked keys. For each provider, show the masked value alongside an Update section and a Delete button.
5. For the Update section, use a password-type `st.text_input` and a Save button. On click, call the save vault key function. Show `st.success` on success and `st.error` on failure. Call `st.rerun()` to refresh the masked key display.
6. For the Delete button, use `st.button` with a confirmation step. On confirmation, call the delete vault key function and rerun.

---

---

## DEVSTROM-V3-9 — Wire Graph + Tools to Use User-Supplied Keys

- [ ] **Ticket completed**

**Type:** Refactor
**Priority:** High
**Depends on:** V3-7

### Description

Currently, `graph.py` and `tools.py` read `OPENAI_API_KEY` and `TAVILY_API_KEY` from environment variables. These are the developer's personal keys, shared implicitly across all users. This is not acceptable in a multi-user platform — each user must use only their own keys.

The fix is to pass the decrypted keys explicitly through the graph state so that each node uses the correct key for the correct user. The graph state gains two new fields for the API keys. The FastAPI `/ideas` handler decrypts the keys from the vault and injects them into the graph input before invoking. No user's key ever mixes with another user's execution context.

### Acceptance Criteria

- [ ] `DevStromState` in `graph.py` has two new fields: `openai_api_key` and `tavily_api_key`.
- [ ] `fetch_web_context` reads `tavily_api_key` from graph state instead of the environment.
- [ ] `generate_ideas` and the idea-generation agent use `openai_api_key` from graph state instead of the environment.
- [ ] The FastAPI `/ideas` handler calls the vault service to retrieve the current user's decrypted keys before invoking the graph, and adds them to the graph input dict.
- [ ] If a required key is missing from the vault, the handler returns HTTP 400 with a message directing the user to the Settings page to add their keys.
- [ ] The `.env` variables `OPENAI_API_KEY` and `TAVILY_API_KEY` are now documented as development-only fallbacks, not used in production user flows.

### Instructions

1. Add `openai_api_key: str` and `tavily_api_key: str` to `DevStromStateRequired` in `graph.py`.
2. Update the `fetch_web_context` node to read `state["tavily_api_key"]` when constructing the Tavily client, instead of calling `os.getenv("TAVILY_API_KEY")`.
3. Update the `generate_ideas` node and the `_get_idea_agent` function to accept and use `openai_api_key` from the graph state. Since agents are cached as singletons, pass the key at invocation time rather than at construction time.
4. In the `/ideas` handler in `api.py`, after verifying the JWT, call the vault service's session function to retrieve the current user's decrypted OpenAI and Tavily keys. If either key is missing, return HTTP 400 with the message: "API key not configured. Please go to Settings and add your OpenAI and Tavily API keys."
5. Add the two decrypted keys to the graph input dictionary before calling `graph_app.invoke`.
6. Remove all direct `os.getenv("OPENAI_API_KEY")` and `os.getenv("TAVILY_API_KEY")` calls from `graph.py` and `tools.py`. Add a comment in `.env.example` noting these are development-only fallbacks.

---

---

## DEVSTROM-V3-10 — Run Service + FastAPI History Endpoints

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Medium
**Depends on:** V3-5, V3-9

### Description

Every time a user clicks "Get Ideas", the result — inputs and generated ideas — is saved to the `runs` table. This is a simple insert after the graph finishes. The ideas are stored as JSONB, PostgreSQL's queryable JSON column type.

Once runs are persisted, the history endpoints let the user retrieve past results. They never need to re-run the graph to see an old result — the ideas are loaded from the database instantly and for free.

### Acceptance Criteria

- [ ] `services/run_service.py` exists with a `save_run` function that inserts a new row into `runs` and returns the generated `run_id`.
- [ ] The FastAPI `/ideas` handler calls `save_run` after a successful graph result. The `run_id` is included in the response.
- [ ] `GET /history` returns the current user's runs, most recent first, with support for `limit` and `offset` query parameters. Default limit is 20. Requires authentication.
- [ ] `GET /runs/{run_id}` returns the full details of a single run including all ideas. Returns 404 if the run does not exist or belongs to a different user. Requires authentication.
- [ ] Expanded ideas created via `POST /expand` are persisted to the `expanded_ideas` table, linked to the `run_id` and idea position.
- [ ] All history endpoints enforce user scoping — a user can only access their own runs.

### Instructions

1. Create `services/models.py` with SQLAlchemy ORM model classes for `Run` and `ExpandedIdea` that map to the corresponding database tables.
2. Create `services/run_service.py` with three functions: a `save_run` function that inserts a row into `runs` and returns the run ID as a string; a `load_history` function that queries runs by user ID in descending creation order with limit and offset; and a `get_run` function that fetches a single run by ID, verifying it belongs to the requesting user.
3. Update the `/ideas` handler to call `save_run` after the graph returns successfully. Add the `run_id` to the response body.
4. Add `GET /history` and `GET /runs/{run_id}` routes to `api.py`. Both require authentication. The history route supports `limit` and `offset` query parameters. The run detail route returns 404 if not found or if the run belongs to a different user.
5. Update the `/expand` handler to save the expanded result to the `expanded_ideas` table using the `run_id` and position index from the request.

---

---

## DEVSTROM-V3-11 — Streamlit History Page

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Medium
**Depends on:** V3-6, V3-10

### Description

The history page is the display layer for the data built in V3-10. It fetches the logged-in user's past runs and displays them as a navigable list. Clicking a past run loads the stored ideas without any new API or LLM calls — everything is served from the database instantly.

### Acceptance Criteria

- [ ] `pages/2_📋_History.py` exists and is reachable from the Streamlit sidebar.
- [ ] The page fetches and displays a list of the current user's past runs, showing the tech stack and creation timestamp for each.
- [ ] Clicking a run fetches the full run from `GET /runs/{run_id}` and renders the ideas in read-only mode using the same card layout as the Home page.
- [ ] A "No history yet" message is shown if the user has no saved runs.
- [ ] A "Load more" button appears if more runs exist beyond the current page.
- [ ] `require_auth()` is called at the top of the page.

### Instructions

1. Create `pages/2_📋_History.py`. Add `require_auth()` as the first line.
2. Add `get_history(limit, offset)` and `get_run(run_id)` functions to `api_client.py`.
3. On page load, call `get_history` and render the results as a selectable list. Use the tech stack and formatted timestamp as the display label for each item.
4. When the user selects a run, store the selected `run_id` in `session_state` and call `get_run`. Render the ideas using the same card components used on the Home page. If the idea card component is duplicated, extract it into a shared `services/components.py` helper.
5. Track the current pagination offset in `session_state`. Show a "Load more" button if the number of returned items equals the page limit. Clicking it increments the offset and fetches the next page, appending results to the displayed list.

---

---

## DEVSTROM-V3-12 — Web Chunking + Embedding + pgvector Storage (RAG Part 1)

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Medium
**Depends on:** V3-3

### Description

An embedding is a list of numbers (a vector) that represents the semantic meaning of a piece of text, generated by an AI model. Two texts with similar meaning will have vectors that are mathematically close to each other. This is the foundation of semantic search.

Before embedding, long web search results are split into small overlapping segments called chunks — typically around 500 characters each, with some overlap at the boundaries. Each chunk is embedded individually and stored in the `web_chunks` table with its vector in the pgvector column.

This "store" phase is the first half of RAG (Retrieval Augmented Generation). The "retrieve" phase — using those stored vectors to find the most relevant content at query time — is implemented in V3-13.

This replaces the current approach of blindly truncating `web_context` at a fixed character limit, which loses potentially important content from the middle or end of search results.

This feature is gated behind an `ENABLE_RAG` environment variable so existing behavior is preserved when it is set to false.

### Acceptance Criteria

- [ ] `services/chunker.py` exists with a `chunk_text` function that splits a string into overlapping segments of approximately 500 characters with 50-character overlap.
- [ ] `services/embedder.py` exists with an `embed_chunks` function that sends a list of text strings to OpenAI's `text-embedding-3-small` model and returns the corresponding list of embedding vectors. It uses the user-supplied OpenAI API key.
- [ ] `services/chunk_store.py` exists with a `save_chunks` function that inserts chunk content and embedding vector pairs into the `web_chunks` table, linked to the current `run_id`.
- [ ] After the Tavily search in `fetch_web_context`, when `ENABLE_RAG=true`, the raw content is chunked, embedded, and stored in the database.
- [ ] The `run_id` field is added to `DevStromState` and is populated before `fetch_web_context` runs.
- [ ] When `ENABLE_RAG=false`, behavior is identical to V2. No embeddings are created.
- [ ] `ENABLE_RAG=false` is documented in `.env.example`.

### Instructions

1. Create `services/chunker.py` with a `chunk_text(text, size=500, overlap=50)` function. It should slide a window of `size` characters across the input, advancing by `size - overlap` each step, and return the list of non-empty stripped segments.
2. Create `services/embedder.py` with an `embed_chunks(chunks, api_key)` function. It creates an OpenAI client using the provided API key and calls the embeddings endpoint with model `text-embedding-3-small`. It returns the list of embedding vectors from the response.
3. Create `services/chunk_store.py` with a `save_chunks(run_id, chunks, embeddings)` function. It inserts one row per chunk into the `web_chunks` table with the run ID, content text, and embedding vector.
4. Add `run_id` as an optional field to `DevStromState`. Populate it in the FastAPI `/ideas` handler by calling `save_run` before invoking the graph (a preliminary save with empty ideas, or restructure the flow so the ID is reserved first).
5. In `fetch_web_context`, after retrieving the Tavily results, check the `ENABLE_RAG` environment variable. If true and a `run_id` is present in state, call `chunk_text`, then `embed_chunks`, then `save_chunks` in sequence.
6. Add `ENABLE_RAG=false` to `.env.example`.
7. Test by running the app with `ENABLE_RAG=true` and verifying that rows appear in the `web_chunks` table after a generation run.

---

---

## DEVSTROM-V3-13 — Semantic Retrieval at Idea-Generation Time (RAG Part 2)

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Medium
**Depends on:** V3-12, V3-10

### Description

With chunks stored in pgvector from V3-12, the retrieval step works as follows: the user's current query (tech stack, domain, and level) is embedded to produce a query vector. That vector is compared against all stored chunk vectors for the current run using cosine distance — a measure of how similar two vectors are in direction. The most similar chunks are returned and fed to the LLM prompt instead of the raw truncated string.

This replaces the blunt `web_context[:4000]` slice with precision retrieval. The LLM receives the most relevant pieces of the web search regardless of where they appeared in the original text, which produces richer and more grounded ideas.

pgvector's distance operator syntax (`embedding <-> query_vector`) allows this similarity search to be expressed as a single SQL query with `ORDER BY` and `LIMIT`.

### Acceptance Criteria

- [ ] `services/retriever.py` exists with a `retrieve_top_k(run_id, query_embedding, k=5)` function that queries the `web_chunks` table for the closest chunks to the given embedding vector, scoped to the current run ID.
- [ ] In `generate_ideas`, when `ENABLE_RAG=true`, the query string is embedded and the top-5 retrieved chunks are joined and used as the context in the LLM prompt instead of `web_context[:4000]`.
- [ ] When `ENABLE_RAG=false`, the prompt uses `web_context[:4000]` exactly as in V2.
- [ ] Retrieval is strictly scoped to the current `run_id` — chunks from other runs are never returned.
- [ ] The output format and API contract are unchanged.

### Instructions

1. Create `services/retriever.py` with a `retrieve_top_k(run_id, query_embedding, k)` function. It queries the `web_chunks` table filtering by `run_id`, ordering by the pgvector cosine distance operator between the `embedding` column and the query embedding, and limiting to `k` results. It returns the list of content strings.
2. In the `generate_ideas` node in `graph.py`, when `ENABLE_RAG=true`, build a query string from the tech stack, domain, and level fields in the state. Call `embedder.embed_chunks` with this single query string and the user's OpenAI key to get the query vector. Call `retriever.retrieve_top_k` with the current `run_id` and query vector. Join the returned chunks into a single context string.
3. Replace the `web_context[:4000]` slice in the prompt-building logic with the retrieved context string. If no chunks are returned (e.g., because `run_id` was not available), fall back to `web_context[:4000]`.
4. Test by comparing idea output with `ENABLE_RAG=false` versus `ENABLE_RAG=true` for the same inputs. The ideas with RAG enabled should feel more specific and targeted to the actual web content.

---

---

## DEVSTROM-V3-14 — Setup MCP Postgres Server (Standalone)

- [ ] **Ticket completed**

**Type:** Infrastructure
**Priority:** Medium
**Depends on:** V3-3

### Description

MCP (Model Context Protocol) is an open standard published by Anthropic in 2024. It defines a structured protocol for LLM agents to interact with external systems — databases, APIs, file systems — using tool calls. Instead of Python code querying the database and injecting the result as a text string into a prompt, the LLM agent itself decides when to query and what to ask.

The official PostgreSQL MCP server (`@modelcontextprotocol/server-postgres`) is a pre-built Node.js process that sits between your agent and your database. It exposes SQL query capabilities as tools the agent can call. You configure it to connect to your database with read-only credentials and start it as a separate process.

This ticket is purely infrastructure: install the MCP server, configure it, verify it connects to the `devstrom` database, and confirm it can respond to a manual test query — all before any agent integration.

### Acceptance Criteria

- [ ] Node.js is installed on the server.
- [ ] `@modelcontextprotocol/server-postgres` is installed globally via npm.
- [ ] A dedicated read-only PostgreSQL user (`mcp_reader`) is created with SELECT-only access to the `runs` and `web_chunks` tables.
- [ ] The MCP server starts successfully and connects to the `devstrom` database using the read-only credentials.
- [ ] A manual test query via the MCP protocol returns the expected rows from the database.
- [ ] A startup script at `scripts/start_mcp.sh` documents the command to start the server.
- [ ] `MCP_POSTGRES_URL` is documented in `.env.example` with the read-only connection string.

### Instructions

1. Install Node.js if not already present using the NodeSource package or the system package manager.
2. Install the MCP server globally using npm: `npm install -g @modelcontextprotocol/server-postgres`.
3. Connect to PostgreSQL as the admin user and create a new role named `mcp_reader` with a password. Grant `SELECT` on the `runs` and `web_chunks` tables to this role. Confirm no other permissions are granted.
4. Create `scripts/start_mcp.sh` with the command to launch the MCP server using the `MCP_POSTGRES_URL` connection string. Make the script executable.
5. Run the script and confirm the server outputs a message indicating it is listening for connections and connected to the database without errors.
6. Send a test MCP protocol message (a JSON-RPC request) to the running server asking it to query the `runs` table. Confirm it returns a valid JSON response with the expected structure.
7. Add `MCP_POSTGRES_URL=postgresql://mcp_reader:password@localhost/devstrom` to `.env.example`.

---

---

## DEVSTROM-V3-15 — Integrate MCP into DeepAgent

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Medium
**Depends on:** V3-14, V3-10

### Description

With the MCP server running from V3-14, this ticket wires it into the DeepAgent as a callable tool. The agent can then query the PostgreSQL database directly during the idea-generation step.

The key use case: before generating ideas, the agent can check whether the current user has had similar ideas generated in the past for the same tech stack. If prior ideas exist, the system prompt instructs the agent to ensure the new ideas are meaningfully different — different problems, different architectures, different primary focus. This makes the generator progressively more useful over time, rather than repeating the same ideas every session.

This integration is controlled by the `ENABLE_MCP` environment variable. When false, no tool is registered and behavior is identical to prior versions.

### Acceptance Criteria

- [ ] The MCP Postgres server from V3-14 is running before this ticket is tested.
- [ ] When `ENABLE_MCP=true`, an MCP tool is registered with the `generate_ideas` agent that allows it to execute read-only SQL queries against the `devstrom` database.
- [ ] The `_IDEAS_SYSTEM` prompt includes an instruction directing the agent to query the user's past runs for the same tech stack before generating new ideas, and to ensure the new ideas differ meaningfully from past results.
- [ ] `user_id` and `tech_stack` are included in the user message passed to the agent so it can construct the correct database query.
- [ ] Running two consecutive idea requests for the same tech stack produces a second set of ideas that is meaningfully different from the first.
- [ ] When `ENABLE_MCP=false`, no MCP tool is added and the agent behaves exactly as in prior versions.
- [ ] `ENABLE_MCP=false` is documented in `.env.example`.

### Instructions

1. Review the DeepAgents documentation for how to register an MCP server as a tool with `create_deep_agent`. Identify the correct parameter and configuration format.
2. In `_get_idea_agent()`, check the `ENABLE_MCP` environment variable. If true, create an MCP client instance configured to connect to the URL from `MCP_POSTGRES_URL` and pass it in the `tools` list when calling `create_deep_agent`.
3. Add a new section to the `_IDEAS_SYSTEM` prompt — after the existing guardrails — that instructs the agent to: call the database query tool to retrieve the current user's last three runs for the given tech stack; review any returned ideas; and ensure all new ideas are distinguishable by their core problem, architecture pattern, or primary use case.
4. In the `generate_ideas` node, include `user_id` and `tech_stack` in the user message string passed to the agent so it can form the SQL query independently.
5. Test by generating ideas for the same tech stack twice in a row. Inspect the second result and confirm the ideas are noticeably different from those in the first result.
6. Add `ENABLE_MCP=false` to `.env.example`.

---

---

## DEVSTROM-V3-16 — Per-User TTL Caching Layer (cachetools)

- [ ] **Ticket completed**

**Type:** Task
**Priority:** Medium
**Depends on:** V3-5

### Description

A TTL (Time To Live) cache stores the result of an expensive computation and returns it instantly on repeated calls with the same inputs, until the TTL window expires.

In Dev-Strom, the expensive operations are the Tavily web search and the OpenAI LLM call — together they take 10 to 20 seconds and cost real API credit. If the same user submits identical inputs within an hour, they should receive the same ideas instantly without any API calls.

The cache key must include the user ID alongside the input parameters. This ensures that User A's cached result is never returned to User B. A SHA-256 hash of all these values combined produces a short, consistent key string.

This caching layer is implemented in FastAPI as a check that happens before the graph is invoked. On a cache hit, the handler returns the stored result directly. On a miss, the graph runs normally and the result is stored in the cache before returning.

### Acceptance Criteria

- [ ] `services/cache.py` implements a `TTLCache` from the `cachetools` library with a configurable maximum size and TTL.
- [ ] A `make_key(user_id, params)` function returns a SHA-256 hash of the combined user ID and input parameters, normalized consistently.
- [ ] `get(key)` and `set(key, value)` functions provide a simple interface to the cache.
- [ ] The FastAPI `/ideas` handler checks the cache before invoking the graph. On a hit, it returns the cached response immediately.
- [ ] The handler stores the response in the cache after a successful graph invocation.
- [ ] Caching is controlled by an `ENABLE_CACHE` environment variable, defaulting to false.
- [ ] `CACHE_TTL_SECONDS` controls the TTL, defaulting to 3600 seconds.
- [ ] Cache hits are logged with a `[CACHE HIT]` prefix and a short key identifier. Cache misses are logged with `[CACHE MISS]`.
- [ ] The second identical request from the same user returns in under 100 milliseconds.
- [ ] `ENABLE_CACHE` and `CACHE_TTL_SECONDS` are documented in `.env.example`.

### Instructions

1. Add `cachetools` to `requirements.txt`.
2. Create `services/cache.py` with a module-level `TTLCache` instance using `maxsize=500` and the TTL from the environment. Implement `make_key` using Python's `hashlib.sha256` on a normalized string combining all relevant inputs. Implement `get` and `set` as thin wrappers around the cache instance.
3. In the `/ideas` handler in `api.py`, after verifying the JWT, check `ENABLE_CACHE`. If true, call `make_key` with the current user's ID and the request body fields. Call `cache.get(key)`. If a result is found, log `[CACHE HIT]` and return the stored response immediately without calling the graph.
4. After a successful graph invocation, call `cache.set(key, response_object)` and log `[CACHE MISS]`.
5. Add `ENABLE_CACHE=false` and `CACHE_TTL_SECONDS=3600` to `.env.example`.
6. Test by submitting the same request twice with `ENABLE_CACHE=true`. The second response should arrive nearly instantly and the log should show `[CACHE HIT]`.

---

---

## DEVSTROM-V3-17 — React + Vite Scaffold + Routing + API Client

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Low — complete after all backend is stable
**Depends on:** V3-1

### Description

React is a JavaScript library for building user interfaces as reusable components. Vite is the modern build tool for React: it starts in milliseconds and hot-reloads changes instantly during development. Together, React and Vite are the current industry standard for building web frontends.

Because V3-1 moved all business logic to FastAPI endpoints, the React app only needs to call those same endpoints — the backend is completely unchanged. This is the entire reason V3-1 was the first ticket.

This ticket creates the React project scaffold, sets up the routing structure, and builds the shared API client that all pages will use. No feature pages are built yet — those are V3-18 and V3-19.

### Acceptance Criteria

- [ ] A `frontend/` directory exists in the project root containing a Vite + React + TypeScript project.
- [ ] React Router is configured with four routes: `/` (Home), `/history`, `/settings`, and `/login`.
- [ ] A shared `api.ts` Axios client exists in `frontend/src/`. Its base URL is read from a Vite environment variable. It has a request interceptor that automatically reads the JWT from `localStorage` and adds it to the `Authorization` header on every request.
- [ ] The app renders without errors at `http://localhost:5173` after `npm run dev`.
- [ ] FastAPI has CORS middleware configured to allow requests from `http://localhost:5173`.

### Instructions

1. Run the Vite scaffolding command in the project root to create the `frontend/` directory with the React TypeScript template.
2. Install the required packages inside the `frontend/` directory: Axios for HTTP requests and React Router for client-side navigation.
3. Add CORS middleware to `api.py` in FastAPI. Allow origin `http://localhost:5173`, allow all methods and headers, and allow credentials.
4. Create `frontend/src/api.ts`. Define an Axios instance with a `baseURL` read from the Vite `VITE_API_URL` environment variable, defaulting to `http://localhost:8000`. Add a request interceptor that reads the JWT from `localStorage` and sets the `Authorization: Bearer` header if a token is present.
5. Set up `App.tsx` with `BrowserRouter` and `Routes`. Define route entries for `/`, `/history`, `/settings`, and `/login`, each pointing to a placeholder component that renders the page name as a heading.
6. Create a `frontend/.env.example` file with `VITE_API_URL=http://localhost:8000`.
7. Start both servers and confirm the React app renders at `http://localhost:5173` without console errors.

---

---

## DEVSTROM-V3-18 — React Auth (Login Page + JWT Flow)

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Low
**Depends on:** V3-17, V3-4

### Description

In React, the JWT is stored in `localStorage` — it persists across browser sessions until cleared. The Axios interceptor from V3-17 picks it up automatically on every request.

The auth gate pattern in React uses a `ProtectedRoute` component that wraps any page requiring authentication. When rendered, it checks for the JWT in `localStorage`. If absent, it redirects to `/login`. If present, it renders the child page normally.

The login flow: the user clicks a button that navigates to `GET /auth/login` on the FastAPI server. Google handles the consent screen. FastAPI's callback route issues a JWT and redirects back to the React frontend with the token as a URL query parameter. React reads the parameter, stores the JWT in `localStorage`, and routes to the home page.

### Acceptance Criteria

- [ ] The `/login` page shows the app name and a "Login with Google" button that navigates the browser to the FastAPI auth login route.
- [ ] When the browser is redirected back to the frontend with a `jwt` query parameter after a successful Google login, the JWT is extracted from the URL, saved to `localStorage`, the parameter is removed from the URL, and the user is redirected to the home page.
- [ ] A `ProtectedRoute` component checks `localStorage` for a JWT. If absent, it redirects to `/login`. If present, it renders its child component.
- [ ] All routes except `/login` are wrapped in `ProtectedRoute`.
- [ ] A Logout function clears the JWT from `localStorage` and navigates to `/login`. It is placed in a shared navbar component.
- [ ] FastAPI's `/auth/callback` redirect URL points to `http://localhost:5173/?jwt=...` to return the token to the React app.

### Instructions

1. Build the `LoginPage` component. It renders the app name, a brief tagline, and a single button or link that navigates to the FastAPI `/auth/login` endpoint URL.
2. In `App.tsx`, add a startup effect that runs once on mount. It checks the current URL for a `jwt` query parameter. If found, it saves the value to `localStorage`, removes the query parameter from the URL using the History API, and navigates to `/`.
3. Create a `ProtectedRoute` component. It reads `localStorage["jwt"]`. If the value is absent or empty, it returns a React Router `Navigate` element pointing to `/login`. Otherwise it renders its `children` prop.
4. Wrap the `/`, `/history`, and `/settings` routes in `ProtectedRoute` in `App.tsx`.
5. Create a `Navbar` component with links to Home, History, and Settings, plus a Logout button. The Logout button calls a function that removes `jwt` from `localStorage` and navigates to `/login`. This component will be included on all protected pages.
6. Update the FastAPI `/auth/callback` handler to redirect to `http://localhost:5173/?jwt=<token>` instead of returning JSON, so the token flows back to the React frontend correctly.
7. Test the full flow: open the React app, click Login with Google, complete sign-in, confirm the home page renders with the user authenticated, then click Logout and confirm you return to the login screen.

---

---

## DEVSTROM-V3-19 — React Home + History + Settings Pages

- [ ] **Ticket completed**

**Type:** Feature
**Priority:** Low
**Depends on:** V3-18

### Description

This is the final ticket — building the three core feature pages as full React components. Each page mirrors the Streamlit equivalent in functionality, but is built with React's component model: `useState` for local state, `useEffect` for data fetching on mount, and conditional rendering for loading and error states.

All API communication uses the shared Axios client from V3-17. Authentication is handled automatically by the interceptor. No new backend work is required.

### Acceptance Criteria

- [ ] The Home page renders the input form (tech stack, domain, level, count, multi-query toggle), a submit button, loading state, and idea cards after a successful response. Each card shows the idea name, problem statement, why it fits, real-world value, and implementation steps. An Expand button on each card calls `POST /expand` and shows the extended plan below.
- [ ] The History page fetches and renders the user's past runs as a selectable list showing tech stack and creation date. Selecting a run loads and displays its ideas in read-only mode. A "Load more" button handles pagination.
- [ ] The Settings page fetches and displays the current user's name, email, and masked API keys. It provides Update and Delete controls for each provider key.
- [ ] A shared `Navbar` component with links and a Logout button appears on all three pages.
- [ ] Loading spinners are shown while requests are in progress. Error messages are shown if any request fails.

### Instructions

1. Build the `HomePage` component. Use `useState` to track the form field values, the loading state, the generated ideas, and the current run ID. On form submit, set loading to true, call `api.post('/ideas', body)`, store the returned ideas and `run_id`, and set loading to false. Render a card component for each idea.
2. Build an `IdeaCard` component that accepts an idea object and the run ID as props. It renders the idea fields in sections. Include an Expand button that calls `api.post('/expand', {run_id, pid})` and renders the returned extended plan below the card. Manage expand loading state locally within each card.
3. Build the `HistoryPage` component. Use `useEffect` to call `api.get('/history')` on mount. Render the results as a clickable list. When an item is clicked, call `api.get('/runs/{run_id}')` and render its ideas using the same `IdeaCard` component in read-only mode (no Expand button). Track a pagination offset in state and fetch additional pages on "Load more" click.
4. Build the `SettingsPage` component. Use `useEffect` to call `api.get('/auth/me')` and `api.get('/vault/keys')` on mount. Render the user's name and email. For each provider, render the masked key alongside a password input and Save button, and a Delete button. Wire the Save button to `api.post('/vault/keys', {provider, key})` and the Delete button to `api.delete('/vault/keys/{provider}')`. Refresh the masked key display after each action.
5. Add the `Navbar` component to all three pages.
6. Test the complete end-to-end flow: generate ideas, expand one, view it in history, and manage keys in settings. Confirm all loading and error states are handled gracefully.

---

*Last updated: 2026-02-22. Mark tickets done in the summary table above as you complete them. Create V4_TICKETS.md when V3 is complete.*
