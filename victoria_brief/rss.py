from __future__ import annotations
import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser


def fetch_rss_items(feeds: dict, hours: int = 26) -> dict[str, list[dict]]:
    """
    Parse RSS feeds and return items published within the last `hours` hours.
    Returns {category: [{"title", "link", "summary"}, ...]}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    results: dict[str, list[dict]] = {}

    for category, feed_urls in feeds.items():
        items: list[dict] = []
        for url in feed_urls:
            try:
                parsed = feedparser.parse(
                    url, request_headers={"User-Agent": "victoria-brief/1.0"}
                )
                for entry in parsed.entries:
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub:
                        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue

                    link = entry.get("link", "")
                    if any(i["link"] == link for i in items):
                        continue  # deduplicate within category

                    raw_summary = entry.get("summary", "") or entry.get("description", "")
                    summary = re.sub(r"<[^>]+>", " ", raw_summary).strip()
                    summary = re.sub(r"\s+", " ", summary)[:400]

                    items.append({
                        "title": entry.get("title", "").strip(),
                        "link": link,
                        "summary": summary,
                    })
            except Exception as exc:
                print(f"  [warn] RSS fetch failed for {url}: {exc}", file=sys.stderr)

        results[category] = items

    return results
