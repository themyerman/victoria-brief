from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

# Display order for categories. Any category not listed here falls into "Other".
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

def _source_card(name: str, items: list[dict], top_n: int = 3) -> str:
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
    return f"""<div class="card">
  <h3>{name}</h3>
  <ul>{"".join(stories_html)}</ul>
</div>"""


# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------

def _category_grid(
    sources: dict[str, list[dict]],
    categories: Optional[dict[str, str]],
    top_n: int,
) -> str:
    """Group source cards into labelled category sections."""
    cat_map: dict[str, list[str]] = defaultdict(list)
    for name in sources:
        cat = (categories or {}).get(name, "Other")
        cat_map[cat].append(name)

    # Sort categories by canonical order, unknown ones at the end
    def cat_sort_key(cat: str) -> int:
        try:
            return _CATEGORY_ORDER.index(cat)
        except ValueError:
            return len(_CATEGORY_ORDER)

    sections = []
    for cat in sorted(cat_map, key=cat_sort_key):
        cards = [
            _source_card(name, sources[name], top_n)
            for name in cat_map[cat]
            if sources.get(name)
        ]
        cards = [c for c in cards if c]
        if not cards:
            continue
        sections.append(
            f'<h2 class="cat-header">{cat}</h2>'
            f'<div class="grid">{"".join(cards)}</div>'
        )
    return "\n".join(sections)


def to_html(
    sources: dict[str, list[dict]],
    major_stories: Optional[list[dict]] = None,
    top_n: int = 3,
    categories: Optional[dict[str, str]] = None,
) -> str:
    today = datetime.now().strftime("%A, %B %-d, %Y")

    major = _major_stories_section(major_stories or [])
    grid = _category_grid(sources, categories, top_n)

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
              padding-bottom: 6px; }}
  .card ul {{ list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }}
  .card li {{ font-size: 0.88em; }}
  .card li strong a {{ color: #1a1a2e; text-decoration: none; line-height: 1.35; }}
  .card li strong a:hover {{ color: #1a6b9a; }}
  .thumb {{ width: 100%; height: 70px; object-fit: cover; border-radius: 4px;
            display: block; margin-bottom: 5px; }}
  .snip {{ margin: 2px 0 0; color: #666; font-size: 0.82em; line-height: 1.4; }}

  /* Category section headers */
  .cat-header {{
    font-size: 0.7em;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #fff;
    background: #1a1a2e;
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    margin: 20px 0 10px;
  }}

  .meta {{ color: #aaa; font-size: 0.78em; margin-top: 24px; text-align: center; }}
</style>
</head><body>

<div class="masthead">
  <h1>Victoria Morning Brief</h1>
  <p class="date">{today}</p>
</div>

{major}
<div class="grid">
{grid}
</div>

<p class="meta">Generated by victoria-brief.</p>
</body></html>"""
