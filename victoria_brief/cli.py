from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .config import load_config
from .sources import fetch_all
from .nlp import deduplicate, score_items, find_major_stories, fill_major_stories, summarize_item, sort_sources, extract_entities
from .render import to_html
from . import mailer, thumbnails, weather, photos, tides, ferries, wildfire, transit, whale, trails, bikecount, marine


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

    sources_config, notify_list, extra = load_config()
    categories = extra.get("categories", {})
    source_weights = {s["name"]: s.get("weight", 1.0) for s in sources_config}

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

    processed = sort_sources(processed, source_weights, top_n=3)

    # Pull Events and Rugby sources out BEFORE the 6-card grid limit so they
    # always flow through to their dedicated sections at the bottom of the page.
    BYPASS_CATS = {"Events"}
    event_sources: dict[str, list[dict]] = {
        name: items
        for name, items in processed.items()
        if categories.get(name) in BYPASS_CATS
    }
    processed = {
        name: items
        for name, items in processed.items()
        if categories.get(name) not in BYPASS_CATS
    }

    # Limit grid to 6 named cards.
    # Two-pass: pinned sources are reserved first, then gravity-sorted
    # sources fill remaining slots, so pinned cards always appear.
    TOP_CARDS = 6
    MIN_ITEMS = 3
    PINNED = {
        "Victoria Buzz",
        "First Nations — Victoria & Island",
        "Victoria Housing & Real Estate",
    }

    top = {}
    # Pass 1: reserve slots for pinned sources (only if they have items)
    for name in PINNED:
        if name in processed and processed[name]:
            top[name] = processed[name]

    # Pass 2: fill remaining slots in gravity order
    rest_items = []
    for name, items in processed.items():
        if name in top:
            continue
        if len(items) >= MIN_ITEMS and len(top) < TOP_CARDS:
            top[name] = items
        else:
            rest_items.extend(items)

    processed = top

    major = find_major_stories(processed, min_sources=2, max_stories=5, similarity_threshold=0.25)
    major = fill_major_stories(major, processed, fill_to=5)
    print(f"  {len(major)} major stories ({sum(1 for s in major if not s.get('promoted'))} cross-source, {sum(1 for s in major if s.get('promoted'))} promoted)")

    print("Fetching thumbnails...")
    processed = thumbnails.enrich(processed, top_n=3)
    event_sources = thumbnails.enrich(event_sources, top_n=3)

    print("Fetching weather...")
    forecast = weather.fetch_forecast()
    sun = weather.fetch_sun()
    aqhi = weather.fetch_aqhi()

    print("Fetching tides...")
    tide_list = tides.fetch_tides()

    print("Fetching ferry status...")
    ferry_routes = ferries.fetch_ferries()

    print("Fetching wildfire status...")
    wildfire_data = wildfire.fetch_wildfire()

    print("Fetching BC Transit alerts...")
    transit_alerts = transit.fetch_transit_alerts()

    print("Fetching whale sightings...")
    whale_sightings = whale.fetch_whale_sightings()

    print("Fetching trail conditions...")
    trail_data = trails.fetch_trail_conditions()

    print("Fetching bike/pedestrian counts...")
    bike_counts = bikecount.fetch_bike_counts()

    print("Fetching marine forecast...")
    marine_forecast = marine.fetch_marine_forecast()

    print("Fetching photos...")
    photo_list = photos.fetch_photos(n=4)

    print("Extracting entities...")
    # Merge event sources back for rendering (events section + entity extraction)
    all_sources = {**processed, **event_sources}
    entities = extract_entities(all_sources)

    html = to_html(
        all_sources,
        major_stories=major,
        top_n=3,
        categories=categories,
        forecast=forecast,
        sun=sun,
        aqhi=aqhi,
        tides=tide_list,
        ferries=ferry_routes,
        whales=whale_sightings,
        wildfire=wildfire_data,
        transit=transit_alerts,
        trail_data=trail_data,
        bike_counts=bike_counts,
        marine_forecast=marine_forecast,
        entities=entities,
        photos=photo_list,
    )

    if not html.strip():
        print("ERROR: render produced empty output.", file=sys.stderr)
        sys.exit(1)

    today = datetime.now().strftime("%B %-d, %Y")

    if args.email:
        mailer.send(subject=f"Victoria Morning Brief — {today}", html=html)
        print("Done.")
    else:
        dest = Path(args.file).expanduser()
        if dest.is_dir():
            dest = dest / "victoria-daily-brief.html"
        dest.write_text(html, encoding="utf-8")
        print(f"Saved: {dest}")

    if notify_list:
        try:
            mailer.notify(notify_list)
        except Exception as exc:
            print(f"  [warn] Notification failed: {exc}", file=sys.stderr)
