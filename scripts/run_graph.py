import argparse
import json
import os
import sys

root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, root)
from dotenv import load_dotenv

load_dotenv(os.path.join(root, ".env"))

from graph import app


def main():
    parser = argparse.ArgumentParser(description="Run Dev-Strom graph")
    parser.add_argument("tech_stack", nargs="?", default="LangChain, LangGraph, Deep Agents", help="Tech stack string")
    parser.add_argument("--stream", action="store_true", help="Stream graph steps and state after each node")
    parser.add_argument("--debug", action="store_true", help="Stream debug traces (node names, inputs, outputs)")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set. Set it in .env to run the graph.")
        sys.exit(1)
    if not os.getenv("TAVILY_API_KEY"):
        print("TAVILY_API_KEY not set. Set it in .env to run the graph.")
        sys.exit(1)

    tech_stack = args.tech_stack
    inputs = {"tech_stack": tech_stack}

    if args.debug:
        print("--- stream_mode=debug ---")
        for chunk in app.stream(inputs, stream_mode="debug"):
            print(json.dumps(chunk, default=str, indent=2)[:2000])
            print("---")
        return

    if args.stream:
        print("--- stream_mode=values (full state after each node) ---")
        for i, state in enumerate(app.stream(inputs, stream_mode="values")):
            print(f"\n[After step {i + 1}]")
            print("  tech_stack:", state.get("tech_stack", "")[:60] + ("..." if len(str(state.get("tech_stack", ""))) > 60 else ""))
            wc = state.get("web_context", "")
            print("  web_context length:", len(wc))
            if wc:
                print("  web_context preview:", wc[:200].replace("\n", " ") + "...")
            ideas = state.get("ideas", [])
            print("  ideas count:", len(ideas))
            for j, idea in enumerate(ideas, 1):
                name = idea.get("name", "") if isinstance(idea, dict) else getattr(idea, "name", "")
                print(f"    {j}. {name}")
        return

    result = app.invoke(inputs)
    assert result.get("web_context"), "web_context should be non-empty"
    ideas = result.get("ideas", [])
    assert len(ideas) == 3, f"expected 3 ideas, got {len(ideas)}"

    print("web_context length:", len(result["web_context"]))
    print("ideas count:", len(ideas))
    for i, idea in enumerate(ideas, 1):
        d = idea if isinstance(idea, dict) else idea.model_dump() if hasattr(idea, "model_dump") else {}
        print(f"\n--- Idea {i}: {d.get('name', '')} ---")
        print("  problem_statement:", (d.get("problem_statement") or "")[:200] + ("..." if len(d.get("problem_statement") or "") > 200 else ""))
        fits = d.get("why_it_fits") or []
        if fits:
            print("  why_it_fits:")
            for b in fits:
                print(f"    - {b}")
        print("  real_world_value:", (d.get("real_world_value") or "")[:150] + ("..." if len(d.get("real_world_value") or "") > 150 else ""))
        steps = d.get("implementation_plan") or []
        if steps:
            print("  implementation_plan:")
            for s in steps:
                print(f"    - {s}")


if __name__ == "__main__":
    main()
