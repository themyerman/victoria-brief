import sys


def web_search(query: str, max_results: int = 4) -> list[dict]:
    """Return [{title, link, snippet}] from DuckDuckGo (no API key required)."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")[:300],
                }
                for r in ddgs.text(query, max_results=max_results)
            ]
    except Exception as exc:
        print(f"  [warn] Web search failed for '{query}': {exc}", file=sys.stderr)
        return []


def fetch_supplemental(search_queries: dict) -> dict[str, list[dict]]:
    """
    Run web searches for categories without RSS coverage.
    Returns {category: [{"title", "link", "snippet"}, ...]}
    """
    results: dict[str, list[dict]] = {}
    for category, queries in search_queries.items():
        seen: set[str] = set()
        items: list[dict] = []
        for query in queries:
            for item in web_search(query):
                if item["link"] not in seen:
                    seen.add(item["link"])
                    items.append(item)
        results[category] = items
    return results
