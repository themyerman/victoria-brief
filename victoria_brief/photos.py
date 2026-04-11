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


def _entry_to_dict(entry) -> dict:
    return {
        "url":    _image_url(entry),
        "title":  entry.get("title", ""),
        "author": _clean_author(entry.get("author", "")),
        "link":   entry.get("link", ""),
    }


def _url_reachable(url: str) -> bool:
    """Quick HEAD check to confirm the image actually loads."""
    try:
        import requests
        r = requests.head(url, timeout=4, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False


def fetch_photos(n: int = 4) -> list[dict]:
    """
    Fetch n Victoria BC nature photos from Flickr, one from each of n
    different randomly-chosen feeds for maximum visual variety.
    Validates each image URL before including it so broken/private photos
    don't appear. Returns a list of dicts with: url, title, author, link.
    """
    try:
        import feedparser
    except ImportError:
        print("  [warn] feedparser not available for photos", file=sys.stderr)
        return []

    feeds = _FEEDS.copy()
    random.shuffle(feeds)

    photos = []
    seen_urls: set[str] = set()

    for feed_url in feeds:
        if len(photos) >= n:
            break
        try:
            parsed = feedparser.parse(feed_url)
            # Shuffle candidates so we don't always pick the same photo per feed
            candidates = [
                e for e in parsed.entries[:20]
                if _image_url(e) and _image_url(e) not in seen_urls
            ]
            random.shuffle(candidates)
            for entry in candidates:
                p = _entry_to_dict(entry)
                if not p["url"] or p["url"] in seen_urls:
                    continue
                if not _url_reachable(p["url"]):
                    continue
                seen_urls.add(p["url"])
                photos.append(p)
                break
        except Exception as exc:
            print(f"  [warn] Flickr feed failed: {exc}", file=sys.stderr)

    return photos
