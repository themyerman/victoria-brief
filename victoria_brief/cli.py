from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .config import load_config
from .sources import fetch_all
from .nlp import deduplicate, score_items, find_major_stories, summarize_item, sentiment_summary
from .render import to_html
from . import mailer, thumbnails


def main() -> None:
    parser = argparse.ArgumentParser(description="Victoria BC Morning Brief")
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument(
        "--email", action="store_true",
        help="Send digest via SMTP (requires EMAIL_* env vars)",
    )
    output.add_argument(
        "--file", metavar="PATH", nargs="?", const="~/Desktop",
        help="Write digest to an HTML file (default: ~/Desktop/victoria-brief-YYYY-MM-DD.html)",
    )
    args = parser.parse_args()

    sources_config, _, _ = load_config()

    print("Fetching sources...")
    raw_sources = fetch_all(sources_config)
    total = sum(len(v) for v in raw_sources.values())
    print(f"  {total} items across {len(raw_sources)} sources")

    print("Running NLP pipeline...")
    # Build a set of search-based source names for stricter relevance filtering
    search_sources = {s["name"] for s in sources_config if "search" in s}

    processed: dict[str, list[dict]] = {}
    for name, items in raw_sources.items():
        items = deduplicate(items)
        items = [dict(item, summary=summarize_item(item)) for item in items]
        items = score_items(items, drop_zero_local=(name in search_sources))
        processed[name] = items

    major = find_major_stories(processed, min_sources=3, max_stories=5)
    print(f"  {len(major)} major stories detected")

    sentiment = sentiment_summary(processed)
    print(f"  tone: {sentiment['overall']} ({sentiment['score']:+.3f})")

    print("Fetching thumbnails...")
    processed = thumbnails.enrich(processed, top_n=3)

    html = to_html(processed, major_stories=major, sentiment=sentiment, top_n=3)

    if not html.strip():
        print("ERROR: render produced empty output.", file=sys.stderr)
        sys.exit(1)

    today = datetime.now().strftime("%B %-d, %Y")

    if args.email:
        mailer.send(subject=f"Victoria Morning Brief — {today}", html=html)
        print("Done.")
    else:
        date_slug = datetime.now().strftime("%Y-%m-%d")
        dest = Path(args.file).expanduser()
        if dest.is_dir():
            dest = dest / f"victoria-brief-{date_slug}.html"
        dest.write_text(html, encoding="utf-8")
        print(f"Saved: {dest}")
