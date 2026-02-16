# Dev-Strom

Suggests project ideas for a tech stack using web search and LLM. See [PLAN.md](PLAN.md) and [TICKETS.md](TICKETS.md).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then set OPENAI_API_KEY and TAVILY_API_KEY
```

## Schema

Output shape for the 3 ideas is defined in `schema.py`: `ProjectIdea` (name, problem_statement, why_it_fits, real_world_value, implementation_plan) and `IdeasResponse` (list of exactly 3 ideas).
