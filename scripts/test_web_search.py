import os
import sys

root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, root)
from dotenv import load_dotenv

load_dotenv(os.path.join(root, ".env"))

from tools import web_search_project_ideas


def main():
    if not os.getenv("TAVILY_API_KEY"):
        print("TAVILY_API_KEY not set; set it in .env to run this test.")
        sys.exit(1)
    tech_stack = "LangChain, LangGraph"
    result = web_search_project_ideas.invoke({"tech_stack": tech_stack})
    assert result, "Expected non-empty search result"
    print("Search result (first 500 chars):")
    print(result[:500])
    print("...")
    print(f"Total length: {len(result)} chars")


if __name__ == "__main__":
    main()
