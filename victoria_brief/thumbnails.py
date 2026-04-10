from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def _fetch_og(url: str, timeout: int = 3) -> str | None:
    try:
        import requests
        from bs4 import BeautifulSoup
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "victoria-brief/1.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for prop in ("og:image", "twitter:image"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                return tag["content"]
    except Exception:
        pass
    return None


def enrich(sources: dict[str, list[dict]], top_n: int = 3, workers: int = 12) -> dict[str, list[dict]]:
    """
    Fetch og:image thumbnails in parallel for the top_n items per source.
    Attaches 'thumbnail' key to each item where found.
    """
    # Collect (source_name, index, url) for items we'll actually display
    jobs = []
    for name, items in sources.items():
        for i, item in enumerate(items[:top_n]):
            if item.get("link"):
                jobs.append((name, i, item["link"]))

    if not jobs:
        return sources

    print(f"  Fetching thumbnails ({len(jobs)} articles)...", file=sys.stderr)

    url_to_img: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(_fetch_og, url): url for _, _, url in jobs}
        for future in as_completed(future_map):
            url = future_map[future]
            img = future.result()
            if img:
                url_to_img[url] = img

    # Attach thumbnails back to items
    enriched = {}
    for name, items in sources.items():
        new_items = []
        for i, item in enumerate(items):
            if i < top_n and item.get("link") in url_to_img:
                item = dict(item, thumbnail=url_to_img[item["link"]])
            new_items.append(item)
        enriched[name] = new_items

    found = len(url_to_img)
    print(f"  {found}/{len(jobs)} thumbnails found", file=sys.stderr)
    return enriched
