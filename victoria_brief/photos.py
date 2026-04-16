from __future__ import annotations

import random
import re
import sys
from datetime import datetime, timedelta, timezone

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


def _entry_to_dict(entry) -> dict:
    return {
        "url":    _image_url(entry),
        "title":  entry.get("title", ""),
        "author": _clean_author(entry.get("author", "")),
        "link":   entry.get("link", ""),
    }


def _url_reachable(url: str) -> bool:
    """GET-based check — Flickr CDN often blocks HEAD requests."""
    try:
        import requests
        r = requests.get(url, timeout=5, stream=True)
        r.close()
        return r.status_code == 200
    except Exception:
        return False


def fetch_photos(n: int = 4) -> list[dict]:
    """
    Fetch n Victoria BC nature photos from Flickr. Collects up to 2×n
    candidates across all feeds first, then validates URLs (GET stream)
    so broken/private photos are skipped. Falls back to unvalidated if
    we can't reach n confirmed photos.
    Returns a list of dicts with: url, title, author, link.
    """
    try:
        import feedparser
    except ImportError:
        print("  [warn] feedparser not available for photos", file=sys.stderr)
        return []

    feeds = _FEEDS.copy()
    random.shuffle(feeds)
    cutoff = datetime.now(timezone.utc) - timedelta(days=15)

    # Gather candidates from as many feeds as needed, one per feed for variety
    candidates: list[dict] = []
    seen_urls: set[str] = set()
    for feed_url in feeds:
        if len(candidates) >= n * 2:
            break
        try:
            parsed = feedparser.parse(feed_url)
            entries = [e for e in parsed.entries[:20] if _image_url(e)]
            random.shuffle(entries)
            for entry in entries:
                # Skip photos older than 15 days
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                p = _entry_to_dict(entry)
                if p["url"] and p["url"] not in seen_urls:
                    seen_urls.add(p["url"])
                    candidates.append(p)
                    break
        except Exception as exc:
            print(f"  [warn] Flickr feed failed: {exc}", file=sys.stderr)

    # Validate URLs — skip broken/private images
    photos: list[dict] = []
    for p in candidates:
        if len(photos) >= n:
            break
        if _url_reachable(p["url"]):
            photos.append(p)

    # If validation was too aggressive, fall back to unvalidated candidates
    if len(photos) < n:
        used = {p["url"] for p in photos}
        for p in candidates:
            if len(photos) >= n:
                break
            if p["url"] not in used:
                photos.append(p)

    return photos[:n]
