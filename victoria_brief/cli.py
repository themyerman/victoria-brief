import argparse
import sys
from datetime import datetime
from pathlib import Path

from .config import load_config
from .rss import fetch_rss_items
from .search import fetch_supplemental
from .render import to_html
from .nlp import deduplicate_by_category, summarize_all, sentiment_summary
from . import mailer


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

    feeds, _, search_queries = load_config()

    print("Fetching RSS feeds...")
    rss_items = fetch_rss_items(feeds)
    print(f"  {sum(len(v) for v in rss_items.values())} items")

    print("Running supplemental web searches...")
    supplemental = fetch_supplemental(search_queries)
    print(f"  {sum(len(v) for v in supplemental.values())} items")

    print("Running NLP (dedup, summarization, sentiment)...")
    rss_items, supplemental = deduplicate_by_category(rss_items, supplemental)
    rss_items, supplemental = summarize_all(rss_items, supplemental)
    sentiment = sentiment_summary(rss_items, supplemental)
    print(f"  tone: {sentiment['overall']} ({sentiment['score']:+.3f})")

    html = to_html(rss_items, supplemental, sentiment=sentiment)

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
