from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_BOILERPLATE_RE = re.compile(
    r'\s*(The post\s+.+?\s+appeared first on\s+[^.]+\.?|appeared first on\s+[^.]+\.?)\s*$',
    re.IGNORECASE | re.DOTALL,
)

def _clean_summary(text: str) -> str:
    return _BOILERPLATE_RE.sub("", text).strip()


# ---------------------------------------------------------------------------
# Title cleaning
# ---------------------------------------------------------------------------

# Known outlet names to strip from prefixes / suffixes
_OUTLETS = (
    r"CBC|CTV|Global News|CHEK News?|Times Colonist|Victoria Buzz|BC Ferries|"
    r"APTN News?|Vancouver Sun|National Post|Globe and Mail|Business Examiner|"
    r"Douglas Magazine|BC Government News|BC Gov(?:ernment)?|Songhees Nation|"
    r"BC Arts Council|BCAC|UVic|Camosun|Google News|Yahoo News|MSN|Reuters|"
    r"The Canadian Press|CP24|Victoria Times Colonist|Victoria News"
)

# "Google News - Some headline" → strip leading outlet prefix
_TITLE_PREFIX_RE = re.compile(rf'^(?:{_OUTLETS})\s*[—–\-]\s*', re.IGNORECASE)

# "Some headline | CBC" or "Some headline — Global News" → strip suffix
_TITLE_SUFFIX_RE = re.compile(r'\s*[\|—–]\s*.{1,50}$')

# Filler phrases tacked onto the end of headlines
_TITLE_FILLER_RE = re.compile(
    r"[,:]?\s*(here'?s? what (you need )?to know|what (you )?need to know|"
    r"officials? say|report says?|data shows?|new data shows?|"
    r"study (?:says?|finds?|shows?)|experts? say|police say)\s*$",
    re.IGNORECASE,
)

# Dates like "April 7, 2026" anywhere in the title
_TITLE_DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

# Leading dateline: "VICTORIA, BC — " or "VANCOUVER — "
_TITLE_DATELINE_RE = re.compile(r'^[A-Z][A-Z\s,\.]{2,25}\s*[—–\-]\s*')


def _clean_title(text: str) -> str:
    """Strip outlet names, datelines, dates, and filler from a headline."""
    text = text.strip()
    text = _TITLE_DATELINE_RE.sub("", text)       # "VICTORIA, BC — ..."
    text = _TITLE_PREFIX_RE.sub("", text)          # "Google News - ..."
    text = _TITLE_DATE_RE.sub("", text)            # "... April 7, 2026"
    text = text.strip().rstrip(",-.:").strip()
    text = _TITLE_SUFFIX_RE.sub("", text)          # "... | CBC"
    text = _TITLE_FILLER_RE.sub("", text)          # "... officials say"
    text = text.strip().rstrip(",-.:").strip()
    # ALL CAPS titles → Title Case
    if len(text) > 3 and text == text.upper():
        text = text.title()
    return text


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
                "title": _clean_title(entry.get("title", "")),
                "link": link,
                "summary": _clean_summary(_strip_html(raw))[:200],
                "published": pub,
            })
    except Exception as exc:
        print(f"  [warn] RSS failed for {url}: {exc}", file=sys.stderr)
    return items


def _is_article_url(url: str) -> bool:
    """Return True if the URL looks like an article rather than a homepage or wiki page."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if "wikipedia.org" in parsed.netloc:
        return False
    path_parts = [p for p in parsed.path.split("/") if p]
    return len(path_parts) >= 1


def fetch_search(query: str, max_results: int = 6) -> list[dict]:
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return [
                {
                    "title": _clean_title(r.get("title", "")),
                    "link": r.get("href", ""),
                    "summary": _clean_summary(r.get("body", ""))[:200],
                    "published": None,
                }
                for r in ddgs.text(query, max_results=max_results)
                if _is_article_url(r.get("href", ""))
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
