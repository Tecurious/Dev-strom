# Dev-Strom

Suggests project ideas for a tech stack using web search and LLM. See [md/PLAN.md](md/PLAN.md) and [md/V1_TICKETS.md](md/V1_TICKETS.md).

## Architecture

![Dev-Strom architecture flow](docs/architecture.png)



**Flow:** User sends a tech stack → **fetch_web_context** runs the web search tool (Tavily) and stores snippets in state → **generate_ideas** uses that context plus an LLM/agent to produce 3 ideas in the schema → response returns the 3 ideas.

| Layer        | Role                                                                 |
|-------------|----------------------------------------------------------------------|
| **LangGraph** | Orchestration: state (tech_stack, web_context, ideas) and nodes fetch_web_context → generate_ideas. |
| **LangChain** | Web search tool and prompts.                                        |
| **Deep Agents** | Generates the 3 ideas inside the generate_ideas node (with optional middleware). |

### Flow: schema, tools, and control

**Schema** (`schema.py`) — Defines the *output contract*. It does not run anything; it describes the shape of data so every part of the system agrees.

- **ProjectIdea:** one idea = `name`, `problem_statement`, `why_it_fits` (list), `real_world_value`, `implementation_plan` (list of steps).
- **IdeasResponse:** exactly 3 `ProjectIdea`s.

The prompt tells the LLM to produce this shape; the API returns it; validation (e.g. Pydantic) checks it. One source of truth.

**Tools** (`tools.py`) — Define *actions* the system can take. They do the work when called.

- **web_search_project_ideas(tech_stack):** builds the query `"project ideas and tutorials for {tech_stack}"`, calls Tavily, returns a single string of snippets (up to 5 results, ~3k chars). Used by the **fetch_web_context** step to fill `web_context` in state. No orchestration—just “given a tech stack, return web snippets.”

**Control** — *Orchestration*: what runs when, in what order, and what state is passed along. Implemented in `graph.py` via LangGraph.

- Holds **state:** `tech_stack` (input), `web_context` (filled by fetch), `ideas` (filled by generate).
- Runs **nodes** in order: `fetch_web_context` → `generate_ideas`. No branching in v1.
- **fetch_web_context:** reads `tech_stack`, calls the web search tool, writes the result to `web_context`.
- **generate_ideas:** reads `tech_stack` and `web_context`, calls the LLM/agent to produce 3 ideas in the schema, writes the result to `ideas`.

So: **schema** = shape of data; **tools** = how we get external data (web); **control** = who calls tools and the agent, in what order, and how state flows between steps.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then set OPENAI_API_KEY and TAVILY_API_KEY
```

Set `TAVILY_API_KEY` in `.env` for web search (get one at https://tavily.com). Set `OPENAI_API_KEY` for the idea-generation agent.

**CLI:** `python scripts/run_graph.py` or `python scripts/run_graph.py "Your, Tech, Stack"` (requires both API keys in `.env`). Use `--stream` to see state after each node; use `--debug` for execution traces.

**API:** Start the server with `uvicorn api:api --reload` (default port 8000). Then `POST /ideas` with body `{"tech_stack": "LangChain, LangGraph"}` returns `{"ideas": [...]}`. Example: `curl -X POST http://localhost:8000/ideas -H "Content-Type: application/json" -d '{"tech_stack": "LangChain, LangGraph"}'`.

## Schema

Output shape for the 3 ideas is defined in `schema.py`: `ProjectIdea` (name, problem_statement, why_it_fits, real_world_value, implementation_plan) and `IdeasResponse` (list of exactly 3 ideas).
