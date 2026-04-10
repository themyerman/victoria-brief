from __future__ import annotations

from datetime import datetime
from typing import Optional

# Display order for categories — cards are sorted by this within the flat grid.
_CATEGORY_ORDER = [
    "BC News",
    "Victoria & Island",
    "Indigenous",
    "Jobs & Economy",
    "Arts & Culture",
    "Education",
    "Housing & Transit",
    "Other",
]


# ---------------------------------------------------------------------------
# Major stories (full-width)
# ---------------------------------------------------------------------------

def _major_stories_section(stories: list[dict]) -> str:
    if not stories:
        return ""
    items_html = []
    for s in stories:
        title = s.get("title", "")
        link = s.get("link", "")
        summary = (s.get("summary", "") or "")[:120].strip()
        count = s.get("source_count", 0)
        sources_str = " &middot; ".join(s.get("sources", []))
        anchor = f'<a href="{link}">{title}</a>' if link else title
        thumbnail = s.get("thumbnail", "")
        thumb_html = f'<img class="major-thumb" src="{thumbnail}" alt="">' if thumbnail else ""
        items_html.append(f"""<li class="major-item">
  {thumb_html}
  <div class="major-text">
    <strong>{anchor}</strong>
    <span class="badge">{count} sources</span>
    {"<p>" + summary + "</p>" if summary else ""}
    <p class="byline">{sources_str}</p>
  </div>
</li>""")
    return f"""<section class="major-section">
  <h2 class="major-h2">&#9733; Major Stories</h2>
  <ul class="major-list">{"".join(items_html)}</ul>
</section>"""


# ---------------------------------------------------------------------------
# Source card (grid item)
# ---------------------------------------------------------------------------

def _source_card(name: str, items: list[dict], top_n: int = 3, category: str = "") -> str:
    if not items:
        return ""
    stories_html = []
    for item in items[:top_n]:
        title = item.get("title", "(no title)")
        link = item.get("link", "")
        summary = (item.get("summary", "") or "")[:110].strip()
        thumbnail = item.get("thumbnail", "")
        anchor = f'<a href="{link}">{title}</a>' if link else title
        thumb_html = f'<img class="thumb" src="{thumbnail}" alt="">' if thumbnail else ""
        snippet = f"<p class='snip'>{summary}</p>" if summary else ""
        stories_html.append(f"""<li>
  {thumb_html}
  <strong>{anchor}</strong>
  {snippet}
</li>""")
    badge = f'<span class="cat-badge">{category}</span>' if category else ""
    return f"""<div class="card">
  <h3><span class="card-source">{name}</span>{badge}</h3>
  <ul>{"".join(stories_html)}</ul>
</div>"""


# ---------------------------------------------------------------------------
# Today at a Glance
# ---------------------------------------------------------------------------

_GLANCE_THRESHOLD = 0.20          # min score to appear in glance
_GLANCE_MAX_PER_CAT = 3           # hard cap per category
_GLANCE_TITLE_LEN = 68            # chars before truncation
_GLANCE_SKIP_CATS = {"Other"}     # categories too noisy for the digest


def _truncate(text: str, length: int = _GLANCE_TITLE_LEN) -> str:
    return text if len(text) <= length else text[:length].rsplit(" ", 1)[0] + "…"


def _glance_section(
    sources: dict[str, list[dict]],
    categories: Optional[dict[str, str]],
) -> str:
    """Score-threshold driven glance: up to 3 items per category that clear
    the score bar, rendered in a 2-column list. No LLM required."""

    cat_items: dict[str, list[dict]] = {}
    all_items: list[dict] = []
    for name, items in sources.items():
        cat = (categories or {}).get(name, "Other")
        cat_items.setdefault(cat, []).extend(items)
        all_items.extend(items)

    # Hero image: thumbnail from the highest-scored item that has one
    hero_html = ""
    scored_with_thumb = [
        i for i in all_items if i.get("thumbnail") and i.get("_score", 0) > 0
    ]
    if scored_with_thumb:
        hero = max(scored_with_thumb, key=lambda x: x.get("_score", 0))
        hero_link = hero.get("link", "")
        hero_src = hero.get("thumbnail", "")
        img = f'<img class="glance-hero" src="{hero_src}" alt="">'
        hero_html = f'<a href="{hero_link}" class="glance-hero-wrap">{img}</a>' if hero_link else img

    rows = []
    for cat in _CATEGORY_ORDER:
        if cat in _GLANCE_SKIP_CATS:
            continue
        items = cat_items.get(cat)
        if not items:
            continue
        # Sort by score, keep those above threshold (up to max)
        candidates = sorted(items, key=lambda x: x.get("_score", 0), reverse=True)
        picks = [i for i in candidates if i.get("_score", 0) >= _GLANCE_THRESHOLD][:_GLANCE_MAX_PER_CAT]
        # Always show at least the top item even if it misses the threshold
        if not picks and candidates:
            picks = candidates[:1]
        for idx, item in enumerate(picks):
            title = _truncate(item.get("title", "").strip())
            link = item.get("link", "")
            if not title:
                continue
            anchor = f'<a href="{link}">{title}</a>' if link else title
            # Category badge only on first item; empty cell keeps alignment on rest
            badge = f'<span class="glance-cat">{cat}</span>' if idx == 0 else '<span class="glance-indent"></span>'
            rows.append(f'<li>{badge}{anchor}</li>')

    if not rows:
        return ""

    return f"""<section class="glance-section">
  <div class="glance-inner">
    <div class="glance-bullets">
      <h2 class="glance-h2">Today at a glance</h2>
      <ul class="glance-list">{"".join(rows)}</ul>
    </div>
    {hero_html}
  </div>
</section>"""


# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------

def _flat_grid(
    sources: dict[str, list[dict]],
    categories: Optional[dict[str, str]],
    top_n: int,
) -> str:
    """Render all source cards in a single flat grid, sorted by category order.
    Cards flow naturally into columns with no per-category grid breaks."""

    def sort_key(name: str) -> int:
        cat = (categories or {}).get(name, "Other")
        try:
            return _CATEGORY_ORDER.index(cat)
        except ValueError:
            return len(_CATEGORY_ORDER)

    cards = []
    for name in sorted(sources.keys(), key=sort_key):
        cat = (categories or {}).get(name, "Other")
        card = _source_card(name, sources[name], top_n, category=cat)
        if card:
            cards.append(card)

    if not cards:
        return ""
    return f'<div class="grid">{"".join(cards)}</div>'


def to_html(
    sources: dict[str, list[dict]],
    major_stories: Optional[list[dict]] = None,
    top_n: int = 3,
    categories: Optional[dict[str, str]] = None,
) -> str:
    today = datetime.now().strftime("%A, %B %-d, %Y")

    major = _major_stories_section(major_stories or [])
    glance = _glance_section(sources, categories)
    grid = _flat_grid(sources, categories, top_n)

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Victoria Morning Brief — {today}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
    max-width: 1100px;
    margin: 32px auto;
    padding: 0 20px;
    color: #222;
    line-height: 1.5;
    background: #f4f4f4;
  }}

  /* Header */
  .masthead {{ background: #1a1a2e; color: #fff; padding: 16px 20px; border-radius: 8px; margin-bottom: 16px; }}
  .masthead h1 {{ margin: 0 0 2px; font-size: 1.4em; }}
  .masthead .date {{ color: #aaa; font-size: 0.85em; margin: 0; }}

  /* Today at a glance */
  .glance-section {{ background: #fff; border: 1px solid #ddd; border-radius: 8px;
                     padding: 14px 20px; margin-bottom: 16px; }}
  .glance-inner {{ display: flex; gap: 16px; align-items: stretch; }}
  .glance-bullets {{ flex: 1; min-width: 0; }}
  .glance-hero-wrap {{ flex-shrink: 0; display: block; width: 220px; }}
  .glance-hero {{ width: 220px; height: 100%; max-height: 220px; object-fit: cover;
                  border-radius: 6px; display: block; }}
  @media (max-width: 600px) {{ .glance-hero-wrap {{ display: none; }} }}
  .glance-h2 {{ margin: 0 0 10px; font-size: 0.75em; text-transform: uppercase;
                letter-spacing: 0.08em; color: #555; }}
  .glance-list {{ list-style: none; padding: 0; margin: 0;
                  display: grid; grid-template-columns: 1fr 1fr; column-gap: 24px; row-gap: 5px; }}
  @media (max-width: 700px) {{ .glance-list {{ grid-template-columns: 1fr; }} }}
  .glance-list li {{ font-size: 0.85em; display: flex; align-items: flex-start; gap: 8px; }}
  .glance-cat {{ flex-shrink: 0; width: 118px; text-align: center; font-size: 0.72em;
                 font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
                 color: #fff; background: #1a1a2e; padding: 2px 6px;
                 border-radius: 3px; opacity: 0.85; white-space: nowrap; line-height: 1.6; }}
  .glance-indent {{ flex-shrink: 0; width: 118px; }}
  .glance-list a {{ color: #1a1a2e; text-decoration: none; line-height: 1.4; }}
  .glance-list a:hover {{ color: #1a6b9a; text-decoration: underline; }}

  /* Major stories */
  .major-section {{ background: #fff; border: 2px solid #8b0000;
                    border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; }}
  .major-h2 {{ margin: 0 0 12px; font-size: 0.85em; text-transform: uppercase;
               letter-spacing: 0.06em; color: #8b0000; }}
  .major-list {{ list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }}
  .major-item {{ display: flex; gap: 12px; align-items: flex-start; }}
  .major-thumb {{ width: 90px; height: 60px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }}
  .major-text {{ flex: 1; }}
  .major-text strong a {{ color: #222; text-decoration: none; font-size: 0.95em; }}
  .major-text strong a:hover {{ color: #8b0000; }}
  .major-text p {{ margin: 3px 0 0; font-size: 0.82em; color: #555; }}
  .major-text .byline {{ color: #999; font-size: 0.78em; }}
  .badge {{ display: inline-block; background: #8b0000; color: #fff;
            border-radius: 10px; font-size: 0.7em; padding: 1px 7px;
            margin-left: 6px; vertical-align: middle; }}

  /* Source grid */
  .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
  @media (max-width: 800px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media (max-width: 520px) {{ .grid {{ grid-template-columns: 1fr; }} }}

  /* Cards */
  .card {{ background: #fff; border: 1px solid #ddd; border-radius: 7px;
           padding: 14px; display: flex; flex-direction: column; }}
  .card h3 {{ margin: 0 0 10px; font-size: 0.75em; text-transform: uppercase;
              letter-spacing: 0.06em; color: #555; border-bottom: 1px solid #eee;
              padding-bottom: 6px; display: flex; justify-content: space-between;
              align-items: center; gap: 6px; }}
  .card-source {{ flex: 1; min-width: 0; }}
  .cat-badge {{ flex-shrink: 0; font-size: 0.85em; font-weight: 600; color: #fff;
                background: #1a1a2e; padding: 1px 6px; border-radius: 3px;
                letter-spacing: 0.04em; opacity: 0.75; }}
  .card ul {{ list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }}
  .card li {{ font-size: 0.88em; }}
  .card li strong a {{ color: #1a1a2e; text-decoration: none; line-height: 1.35; }}
  .card li strong a:hover {{ color: #1a6b9a; }}
  .thumb {{ width: 100%; height: 70px; object-fit: cover; border-radius: 4px;
            display: block; margin-bottom: 5px; }}
  .snip {{ margin: 2px 0 0; color: #666; font-size: 0.82em; line-height: 1.4; }}

  .meta {{ color: #aaa; font-size: 0.78em; margin-top: 24px; text-align: center; }}
</style>
</head><body>

<div class="masthead">
  <h1>Victoria Morning Brief</h1>
  <p class="date">{today}</p>
</div>

{glance}
{major}
{grid}

<p class="meta">Generated by victoria-brief.</p>
</body></html>"""
