from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_rss(url: str, hours: int = 26) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = []
    try:
        parsed = feedparser.parse(url, request_headers={"User-Agent": "victoria-brief/1.0"})
        seen = set()
        for entry in parsed.entries:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            link = entry.get("link", "")
            if link in seen:
                continue
            seen.add(link)
            raw = entry.get("summary", "") or entry.get("description", "")
            items.append({
                "title": entry.get("title", "").strip(),
                "link": link,
                "summary": _strip_html(raw)[:200],
                "published": pub,
            })
    except Exception as exc:
        print(f"  [warn] RSS failed for {url}: {exc}", file=sys.stderr)
    return items


def fetch_search(query: str, max_results: int = 6) -> list[dict]:
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "summary": r.get("body", "")[:200],
                    "published": None,
                }
                for r in ddgs.text(query, max_results=max_results)
            ]
    except Exception as exc:
        print(f"  [warn] Search failed for '{query}': {exc}", file=sys.stderr)
        return []


def fetch_all(sources: list[dict]) -> dict[str, list[dict]]:
    """
    Fetch every source and return {source_name: [items]}.
    Each source dict has 'name' and either 'url' or 'search'.
    """
    results = {}
    for source in sources:
        name = source["name"]
        if "url" in source:
            items = fetch_rss(source["url"])
        elif "search" in source:
            items = fetch_search(source["search"])
        else:
            items = []
        results[name] = items
        print(f"  {name}: {len(items)} items")
    return results
