from __future__ import annotations

"""
Whale sightings near Victoria BC / Salish Sea via DuckDuckGo search.
The Whale Museum Hotline API (hotline.whalemuseum.org) appears to be
offline; this uses the same search infrastructure as other sources.
"""

import sys


def fetch_whale_sightings(max_results: int = 4) -> list[dict]:
    """
    Search for recent whale and orca sightings near Victoria BC / Salish Sea.
    Returns list of dicts: title, summary, link, published (None).
    Returns [] on any failure.
    """
    try:
        from ddgs import DDGS
        query = (
            "orca OR whale sighting Victoria BC OR Vancouver Island "
            "OR Salish Sea 2025 OR 2026"
        )
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results * 3)

        results = []
        seen: set[str] = set()
        for r in (raw or []):
            href  = r.get("href", "")
            title = r.get("title", "").strip()
            body  = r.get("body", "")[:150].strip()
            if not href or not title or href in seen:
                continue
            seen.add(href)
            results.append({
                "title":     title,
                "summary":   body,
                "link":      href,
                "published": None,
            })
            if len(results) >= max_results:
                break

        return results

    except Exception as exc:
        print(f"  [warn] Whale sightings search failed: {exc}", file=sys.stderr)
        return []
