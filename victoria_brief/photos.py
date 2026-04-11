from __future__ import annotations

import random
import re
import sys

# Nature/landscape focused tag searches for Victoria BC & Vancouver Island.
# tagmode=all requires ALL listed tags to be present — much more targeted.
_BASE = "https://www.flickr.com/services/feeds/photos_public.gne?format=rss2"
_FEEDS = [
    f"{_BASE}&tags=victoria,bc,landscape&tagmode=all",
    f"{_BASE}&tags=victoria,bc,nature&tagmode=all",
    f"{_BASE}&tags=victoria,bc,ocean&tagmode=all",
    f"{_BASE}&tags=victoria,bc,whale&tagmode=all",
    f"{_BASE}&tags=vancouver+island,landscape",
    f"{_BASE}&tags=vancouver+island,nature",
    f"{_BASE}&tags=vancouver+island,hiking",
    f"{_BASE}&tags=vancouver+island,mountains",
    f"{_BASE}&tags=vancouver+island,ocean",
    f"{_BASE}&tags=juan+de+fuca,trail&tagmode=all",
    f"{_BASE}&tags=butchart+gardens,victoria&tagmode=all",
    f"{_BASE}&tags=malahat,bc&tagmode=all",
    f"{_BASE}&tags=tofino,bc,landscape&tagmode=all",
    f"{_BASE}&tags=victoria,bc,trail&tagmode=all",
    f"{_BASE}&tags=saanich,bc,nature&tagmode=all",
]

# Flickr author field looks like "nobody@flickr.com (Real Name)" — extract the name
_AUTHOR_RE = re.compile(r'\((.+?)\)$')


def _clean_author(raw: str) -> str:
    m = _AUTHOR_RE.search(raw.strip())
    return m.group(1) if m else raw.strip()


def _image_url(entry) -> str:
    """Pull the best image URL from a feedparser entry."""
    for m in getattr(entry, "media_content", []):
        url = m.get("url", "")
        if url and "staticflickr" in url:
            return url
    for enc in getattr(entry, "enclosures", []):
        url = enc.get("href", "") or enc.get("url", "")
        if url:
            return url
    return ""


def fetch_photo() -> dict | None:
    """
    Fetch a random recent Victoria BC photo from Flickr's public tag feeds.
    Returns a dict with: url, title, author, link — or None on failure.
    Tries all feeds in random order and picks from the top 20 results.
    """
    try:
        import feedparser
    except ImportError:
        print("  [warn] feedparser not available for photos", file=sys.stderr)
        return None

    feeds = _FEEDS.copy()
    random.shuffle(feeds)

    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            candidates = [
                e for e in parsed.entries[:20]
                if _image_url(e)
            ]
            if not candidates:
                continue
            entry = random.choice(candidates)
            return {
                "url":    _image_url(entry),
                "title":  entry.get("title", ""),
                "author": _clean_author(entry.get("author", "")),
                "link":   entry.get("link", ""),
            }
        except Exception as exc:
            print(f"  [warn] Flickr feed failed ({feed_url}): {exc}", file=sys.stderr)

    return None
