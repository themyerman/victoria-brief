from __future__ import annotations

from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rel_time(published) -> str:
    if not published:
        return ""
    from datetime import datetime, timezone
    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
    age_h = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
    if age_h < 1:
        return f"{int(age_h * 60)}m"
    if age_h < 24:
        return f"{int(age_h)}h"
    if age_h < 48:
        return "1d"
    return ""


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

def _photos_panel(photo_list: list) -> str:
    """2×2 grid of Victoria nature photos with photographer credits."""
    if not photo_list:
        return ""
    cells = []
    for p in photo_list[:4]:
        url    = p.get("url", "")
        link   = p.get("link", "")
        title  = p.get("title", "")
        author = p.get("author", "")
        if not url:
            continue
        img = f'<img class="pgrid-img" src="{url}" alt="{title}">'
        wrapped = f'<a href="{link}" target="_blank">{img}</a>' if link else img
        credit = f'<span class="pgrid-credit">📷 {author}</span>' if author else ""
        cells.append(f'<div class="pgrid-cell">{wrapped}{credit}</div>')
    if not cells:
        return ""
    return f"""<div class="photos-panel">
  <h2 class="photos-h2">&#127758; Victoria</h2>
  <div class="pgrid">{"".join(cells)}</div>
</div>"""


def _major_stories_section(stories: list[dict], photo_list: Optional[list] = None) -> str:
    if not stories:
        return ""

    items_html = []
    for s in stories:
        title = s.get("title", "")
        link = s.get("link", "")
        summary = (s.get("summary", "") or "")[:120].strip()
        count = s.get("source_count", 0)
        promoted = s.get("promoted", False)
        sources_str = " &middot; ".join(s.get("sources", []))
        anchor = f'<a href="{link}">{title}</a>' if link else title
        if promoted:
            badge = '<span class="badge badge-promoted">&#9889; Top Story</span>'
        else:
            badge = f'<span class="badge">{count} source{"s" if count != 1 else ""}</span>'
        items_html.append(f"""<li class="major-item">
  <div class="major-text">
    <strong>{anchor}</strong>
    {badge}
    {"<p>" + summary + "</p>" if summary else ""}
    <p class="byline">{sources_str}</p>
  </div>
</li>""")

    photos_html = _photos_panel(photo_list or [])

    return f"""<section class="major-section">
  <div class="major-inner">
    <div class="major-stories-col">
      <h2 class="major-h2">&#9733; Major Stories</h2>
      <ul class="major-list">{"".join(items_html)}</ul>
    </div>
    {photos_html}
  </div>
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
        age = _rel_time(item.get("published"))
        age_html = f'<span class="age">{age}</span>' if age else ""
        thumb_html = f'<img class="thumb" src="{thumbnail}" alt="">' if thumbnail else ""
        snippet = f"<p class='snip'>{summary}</p>" if summary else ""
        stories_html.append(f"""<li>
  {thumb_html}
  <strong>{anchor}{age_html}</strong>
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
_GLANCE_MAX_WORDS = 8             # word cap on headlines (after title cleaning)
_GLANCE_SKIP_CATS = {"Other"}     # categories too noisy for the digest


def _truncate(text: str, max_words: int = _GLANCE_MAX_WORDS) -> str:
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words]) + "…"


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

    # Build category groups: [(cat, [item, ...]), ...]
    groups = []
    for cat in _CATEGORY_ORDER:
        if cat in _GLANCE_SKIP_CATS:
            continue
        items = cat_items.get(cat)
        if not items:
            continue
        candidates = sorted(items, key=lambda x: x.get("_score", 0), reverse=True)
        picks = [i for i in candidates if i.get("_score", 0) >= _GLANCE_THRESHOLD][:_GLANCE_MAX_PER_CAT]
        if not picks and candidates:
            picks = candidates[:1]
        picks = [i for i in picks if i.get("title", "").strip()]
        if picks:
            groups.append((cat, picks))

    if not groups:
        return ""

    # Distribute groups into two columns, greedy-balance by item count
    left_groups: list = []
    right_groups: list = []
    left_n = right_n = 0
    for group in groups:
        if left_n <= right_n:
            left_groups.append(group)
            left_n += len(group[1])
        else:
            right_groups.append(group)
            right_n += len(group[1])

    def _render_col(col_groups: list) -> str:
        rows = []
        for cat, picks in col_groups:
            for idx, item in enumerate(picks):
                title = _truncate(item.get("title", "").strip())
                link = item.get("link", "")
                anchor = f'<a href="{link}">{title}</a>' if link else title
                badge = f'<span class="glance-cat">{cat}</span>' if idx == 0 else '<span class="glance-indent"></span>'
                rows.append(f'<li>{badge}{anchor}</li>')
        return f'<ul class="glance-list">{"".join(rows)}</ul>'

    cols_html = (
        f'<div class="glance-cols">'
        f'{_render_col(left_groups)}{_render_col(right_groups)}'
        f'</div>'
    )

    return f"""<section class="glance-section">
  <div class="glance-inner">
    <div class="glance-bullets">
      <h2 class="glance-h2">Today at a glance</h2>
      {cols_html}
    </div>
    {hero_html}
  </div>
</section>"""


# ---------------------------------------------------------------------------
# Weather widget
# ---------------------------------------------------------------------------

def _weather_widget(forecast: list) -> str:
    if not forecast:
        return ""
    days_html = []
    for day in forecast:
        label     = day.get("label", "")
        icon      = day.get("icon", "")
        desc      = day.get("desc", "")
        high_c    = day.get("high_c", 0)
        low_c     = day.get("low_c", 0)
        high_f    = day.get("high_f", 0)
        low_f     = day.get("low_f", 0)
        precip    = day.get("precip_pct", 0)
        rain_html = f'<div class="wx-rain">&#x1F4A7; {precip}%</div>' if precip > 10 else ""
        days_html.append(
            f'<div class="wx-day">'
            f'<div class="wx-label">{label}</div>'
            f'<div class="wx-icon">{icon}</div>'
            f'<div class="wx-desc">{desc}</div>'
            f'<div class="wx-temp">{high_c}°C / {low_c}°C &nbsp; {high_f}°F / {low_f}°F</div>'
            f'{rain_html}'
            f'</div>'
        )
    return f'<div class="wx-bar">{"".join(days_html)}</div>'


# ---------------------------------------------------------------------------
# Keyword strip
# ---------------------------------------------------------------------------

def _keyword_strip(keywords: list) -> str:
    if not keywords:
        return ""
    pills = "".join(f'<span class="kw-pill">{kw}</span>' for kw in keywords)
    return f'<div class="kw-strip"><span class="kw-label">Today:</span> {pills}</div>'


# ---------------------------------------------------------------------------
# NER card
# ---------------------------------------------------------------------------

def _ner_card(entities: dict) -> str:
    people = entities.get("people", [])
    places = entities.get("places", [])
    orgs   = entities.get("orgs",   [])
    if not people and not places and not orgs:
        return ""

    cols_html = []
    for header, names in [("👤 People", people), ("📍 Places", places), ("🏢 Organizations", orgs)]:
        if not names:
            continue
        items = "".join(f"<li>{n}</li>" for n in names)
        cols_html.append(
            f'<div class="ner-col">'
            f'<h4>{header}</h4>'
            f'<ul>{items}</ul>'
            f'</div>'
        )

    return f'<div class="card ner-card">{"".join(cols_html)}</div>'


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
    forecast: Optional[list] = None,
    keywords: Optional[list] = None,
    entities: Optional[dict] = None,
    photos: Optional[list] = None,
) -> str:
    today = datetime.now().strftime("%A, %B %-d, %Y")

    major = _major_stories_section(major_stories or [], photo_list=photos)
    grid = _flat_grid(sources, categories, top_n)
    weather_html = _weather_widget(forecast or [])
    kw_html = _keyword_strip(keywords or [])
    ner_html = _ner_card(entities or {})

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
  .glance-cols {{ display: flex; gap: 24px; }}
  .glance-list {{ list-style: none; padding: 0; margin: 0; flex: 1;
                  display: flex; flex-direction: column; gap: 5px; }}
  @media (max-width: 700px) {{ .glance-cols {{ flex-direction: column; }} }}
  .glance-list li {{ font-size: 0.85em; display: flex; align-items: flex-start; gap: 8px; }}
  .glance-cat {{ flex-shrink: 0; width: 112px; text-align: center; font-size: 0.72em;
                 font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
                 color: #fff; background: #1a1a2e; padding: 2px 6px;
                 border-radius: 3px; opacity: 0.85; white-space: nowrap; line-height: 1.6; }}
  .glance-indent {{ flex-shrink: 0; width: 112px; }}
  .glance-list a {{ color: #1a1a2e; text-decoration: none; line-height: 1.35; }}
  .glance-list a:hover {{ color: #1a6b9a; text-decoration: underline; }}

  /* Major stories */
  .major-section {{ background: #fff; border: 2px solid #8b0000;
                    border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; }}
  .major-inner {{ display: flex; gap: 16px; align-items: stretch; }}
  .major-stories-col {{ flex: 1; min-width: 0; }}
  /* Photos panel */
  .photos-panel {{ flex-shrink: 0; width: 280px; display: flex; flex-direction: column; gap: 8px; }}
  .photos-h2 {{ margin: 0 0 6px; font-size: 0.75em; text-transform: uppercase;
                letter-spacing: 0.08em; color: #1a1a2e; }}
  .pgrid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
  .pgrid-cell {{ position: relative; overflow: hidden; border-radius: 5px; }}
  .pgrid-img {{ width: 100%; height: 110px; object-fit: cover; display: block;
                transition: transform 0.2s; }}
  .pgrid-cell:hover .pgrid-img {{ transform: scale(1.04); }}
  .pgrid-credit {{ display: block; font-size: 0.65em; color: #999;
                   white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                   margin-top: 2px; }}
  @media (max-width: 700px) {{ .photos-panel {{ display: none; }} }}
  .major-h2 {{ margin: 0 0 12px; font-size: 0.85em; text-transform: uppercase;
               letter-spacing: 0.06em; color: #8b0000; }}
  .major-list {{ list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }}
  .major-item {{ display: flex; gap: 10px; align-items: flex-start; }}
  .major-text {{ flex: 1; }}
  .major-text strong a {{ color: #222; text-decoration: none; font-size: 0.95em; }}
  .major-text strong a:hover {{ color: #8b0000; }}
  .major-text p {{ margin: 3px 0 0; font-size: 0.82em; color: #555; }}
  .major-text .byline {{ color: #999; font-size: 0.78em; }}
  .badge {{ display: inline-block; background: #8b0000; color: #fff;
            border-radius: 10px; font-size: 0.7em; padding: 1px 7px;
            margin-left: 6px; vertical-align: middle; }}
  .badge-promoted {{ background: #7a5c00; }}

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

  /* Weather */
  .wx-bar {{ display:flex; gap:10px; margin-bottom:14px; }}
  .wx-day {{ background:#fff; border:1px solid #ddd; border-radius:7px; padding:10px 14px; flex:1; text-align:center; }}
  .wx-icon {{ font-size:1.8em; line-height:1; }}
  .wx-label {{ font-size:0.7em; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#555; margin-bottom:4px; }}
  .wx-desc {{ font-size:0.75em; color:#666; margin:2px 0; }}
  .wx-temp {{ font-size:0.85em; font-weight:600; color:#222; }}
  .wx-rain {{ font-size:0.72em; color:#1a6b9a; margin-top:2px; }}

  /* Keywords */
  .kw-strip {{ margin-bottom:12px; display:flex; flex-wrap:wrap; align-items:center; gap:5px; }}
  .kw-label {{ font-size:0.72em; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#888; }}
  .kw-pill {{ font-size:0.75em; background:#eee; color:#444; padding:2px 8px; border-radius:10px; }}

  /* Story age */
  .age {{ font-size:0.75em; color:#aaa; margin-left:4px; white-space:nowrap; }}

  /* NER card */
  .ner-card {{ display:flex; gap:0; padding:0; margin-top:14px; }}
  .ner-col {{ flex:1; padding:14px; border-right:1px solid #eee; }}
  .ner-col:last-child {{ border-right:none; }}
  .ner-col h4 {{ margin:0 0 8px; font-size:0.72em; text-transform:uppercase; letter-spacing:0.06em; color:#555; }}
  .ner-col ul {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:4px; }}
  .ner-col li {{ font-size:0.83em; color:#333; }}
</style>
</head><body>

<div class="masthead">
  <h1>Victoria Morning Brief</h1>
  <p class="date">{today}</p>
</div>

{weather_html}
{kw_html}
{major}
{grid}
{ner_html}

<p class="meta">Generated by victoria-brief.</p>
</body></html>"""
