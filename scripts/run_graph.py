import os
import sys

root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, root)
from dotenv import load_dotenv

load_dotenv(os.path.join(root, ".env"))

from graph import app


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set. Set it in .env to run the graph.")
        sys.exit(1)
    if not os.getenv("TAVILY_API_KEY"):
        print("TAVILY_API_KEY not set. Set it in .env to run the graph.")
        sys.exit(1)

    tech_stack = sys.argv[1] if len(sys.argv) > 1 else "LangChain, LangGraph, Deep Agents"
    result = app.invoke({"tech_stack": tech_stack})

    assert result.get("web_context"), "web_context should be non-empty"
    ideas = result.get("ideas", [])
    assert len(ideas) == 3, f"expected 3 ideas, got {len(ideas)}"

    print("web_context length:", len(result["web_context"]))
    print("ideas count:", len(ideas))
    for i, idea in enumerate(ideas, 1):
        name = idea.get("name", "") if isinstance(idea, dict) else getattr(idea, "name", "")
        print(f"  {i}. {name}")


if __name__ == "__main__":
    main()
