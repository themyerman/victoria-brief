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
# "Events" is excluded from the grid and rendered in its own bottom section.
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
_EVENTS_CATEGORY = "Events"


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
        img = f'<img class="pgrid-img" src="{url}" alt="{title}" onerror="this.closest(\'.pgrid-cell\').style.display=\'none\'">'
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
# Weather widget (with optional sun + air quality tile)
# ---------------------------------------------------------------------------

def _weather_widget(forecast: list, sun: dict = None, aqhi: dict = None) -> str:
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

    # Optional sun & air quality tile
    if sun or aqhi:
        parts = ['<div class="wx-label">Sun &amp; Air</div>', '<div class="wx-icon">🌅</div>']
        if sun:
            parts.append(f'<div class="wx-desc">&#x2600;&#xFE0F; {sun.get("sunrise","")} &nbsp; 🌇 {sun.get("sunset","")}</div>')
            hrs = sun.get("day_length", "").split(":")[0]
            if hrs:
                parts.append(f'<div class="wx-desc">{hrs}h of daylight</div>')
        if aqhi:
            val = aqhi.get("value", "")
            lbl = aqhi.get("label", "")
            ico = aqhi.get("icon", "")
            parts.append(f'<div class="wx-desc" style="margin-top:4px">Air: {ico} {val} <em>{lbl}</em></div>')
        days_html.append(f'<div class="wx-day">{"".join(parts)}</div>')

    return f'<div class="wx-bar">{"".join(days_html)}</div>'


# ---------------------------------------------------------------------------
# Coastal right panel: tides + (whale / wildfire / transit / webcam stubs)
# ---------------------------------------------------------------------------

def _coastal_right_panel(
    tides: list,
    whales: Optional[list] = None,
    wildfire: Optional[dict] = None,
    transit: Optional[list] = None,
    webcam_url: Optional[str] = None,
    trail_data: Optional[dict] = None,
) -> str:
    sections = []

    # ── Tides ─────────────────────────────────────────────────────────────────
    if tides:
        events = []
        for t in tides:
            past_cls = " tide-past" if t.get("past") else ""
            type_str = t.get("type", "")
            type_cls = "tide-high" if type_str == "High" else "tide-low"
            icon     = "🌊" if type_str == "High" else "〰️"
            events.append(
                f'<div class="tide-event{past_cls}">'
                f'<span class="tide-type {type_cls}">{icon} {type_str}</span>'
                f'<span class="tide-time">{t.get("time_str","")}</span>'
                f'<span class="tide-ht">{t.get("value_m","")}m / {t.get("value_ft","")}ft</span>'
                f'</div>'
            )
        sections.append(
            f'<div class="crp-section">'
            f'<h4 class="crp-h4">🌊 Tides — Victoria Harbour</h4>'
            f'<div class="tides-row">{"".join(events)}</div>'
            f'<p class="coastal-src">Source: Canadian Hydrographic Service</p>'
            f'</div>'
        )

    # ── Mini grid: webcam | whale | wildfire | transit ─────────────────────────
    mini = []

    if webcam_url:
        mini.append(
            f'<div class="crp-mini crp-webcam">'
            f'<h5 class="crp-h5">📷 Harbour Cam</h5>'
            f'<img src="{webcam_url}" class="webcam-img" alt="Victoria Harbour webcam">'
            f'</div>'
        )

    if whales:
        items = "".join(
            f'<li><a href="{w.get("link","")}" target="_blank">{w.get("title","")}</a>'
            f'<span class="crp-age">{_rel_time(w.get("published"))}</span></li>'
            for w in whales[:3]
        )
        sections.append(
            f'<div class="crp-section">'
            f'<h4 class="crp-h4">🐋 Whale Sightings</h4>'
            f'<ul class="crp-list">{items}</ul>'
            f'</div>'
        )

    if wildfire is not None:
        total = wildfire.get("total_active", 0)
        fon   = wildfire.get("has_fire_of_note", False)
        fires = wildfire.get("fires", [])
        if total == 0:
            fire_body = '<p class="crp-ok">✅ No active fire warnings nearby</p>'
        else:
            flag = "⚠️" if fon else "🔥"
            count_html = (
                f'<p class="crp-fire-count">{flag} '
                f'<strong>{total}</strong> active fire{"s" if total != 1 else ""} nearby</p>'
            )
            rows = "".join(
                f'<li>{f["icon"]} '
                f'{"<strong>⭐ Fire of Note</strong> · " if f["fire_of_note"] else ""}'
                f'<a href="{f["url"]}" target="_blank">{f["location"]}</a>'
                f' <span class="crp-fire-meta">{f["status"]} · {f["size_ha"]}ha</span></li>'
                for f in fires
            )
            fire_body = f'{count_html}<ul class="crp-list">{rows}</ul>'
        sections.append(
            f'<div class="crp-section">'
            f'<h4 class="crp-h4">🔥 Wildfire — VI Region</h4>'
            f'{fire_body}'
            f'<p class="coastal-src">Source: BC Wildfire Service</p>'
            f'</div>'
        )

    if transit:
        rows = "".join(
            f'<li>{a.get("icon","ℹ️")} <strong>{a.get("header","")}</strong>'
            f'<span class="crp-transit-desc"> — {a.get("description","")}</span></li>'
            for a in transit[:4]
        )
        sections.append(
            f'<div class="crp-section">'
            f'<h4 class="crp-h4">🚌 BC Transit Alerts</h4>'
            f'<ul class="crp-list">{rows}</ul>'
            f'<p class="coastal-src">Source: BC Transit GTFS-RT</p>'
            f'</div>'
        )

    if trail_data:
        featured = trail_data.get("featured", {})
        feat_html = ""
        if featured:
            feat_link = featured.get("url", "")
            feat_name = featured.get("name", "")
            feat_type = featured.get("type", "")
            feat_km   = featured.get("km", "")
            name_html = f'<a href="{feat_link}" target="_blank">{feat_name}</a>' if feat_link else feat_name
            feat_html = (
                f'<p class="crp-trail-feat">&#127956; {name_html}'
                f'<span class="crp-fire-meta"> · {feat_type} · {feat_km}</span></p>'
            )
        tf_url = trail_data.get("trailforks_url", "")
        tf_link = f' <a href="{tf_url}" target="_blank" class="crp-trail-link">Trailforks →</a>' if tf_url else ""
        sections.append(
            f'<div class="crp-section">'
            f'<h4 class="crp-h4">&#128692; Trails &amp; Cycling</h4>'
            f'<p class="crp-trail-status">{trail_data.get("icon","🟢")} '
            f'<strong>{trail_data.get("condition","")} — {trail_data.get("label","")}</strong>'
            f'<span class="crp-transit-desc"> · {trail_data.get("note","")}</span></p>'
            f'{feat_html}'
            f'<p class="coastal-src">Based on {trail_data.get("precip_24h",0)}mm rain last 24h{tf_link}</p>'
            f'</div>'
        )

    if mini:
        sections.append(f'<div class="crp-minigrid">{"".join(mini)}</div>')

    if not sections:
        return ""
    return f'<div class="coastal-panel coastal-right">{"".join(sections)}</div>'


# ---------------------------------------------------------------------------
# Ferries widget
# ---------------------------------------------------------------------------

def _ferries_widget(routes: list) -> str:
    if not routes:
        return ""
    routes_html = []
    for route in routes:
        sailings = route.get("sailings", [])
        if not sailings:
            continue
        dep = route.get("from_name", "")
        arr = route.get("to_name", "")
        dur = route.get("duration", "")
        sail_rows = []
        for s in sailings[:4]:
            is_current = s.get("status") == "current"
            cur_cls    = " sailing-current" if is_current else ""
            fill_cls   = s.get("fill_class", "fill-low")
            fill_lbl   = s.get("fill_label", "")
            cur_badge  = '<span class="sail-now">Now</span>' if is_current else ""
            vs = s.get("vessel_status", "")
            vs_html = f'<span class="vessel-alert"> ⚠️ {vs}</span>' if vs else ""
            sail_rows.append(
                f'<div class="sailing{cur_cls}">'
                f'  {cur_badge}'
                f'  <span class="sail-time">{s.get("time","")}</span>'
                f'  <span class="sail-arr">→ {s.get("arrival_time","")}</span>'
                f'  <span class="sail-vessel">{s.get("vessel","")}</span>'
                f'  <span class="sail-fill {fill_cls}">{fill_lbl}</span>'
                f'  {vs_html}'
                f'</div>'
            )
        routes_html.append(
            f'<div class="ferry-route">'
            f'  <div class="ferry-route-hdr">{dep} → {arr}'
            f'    <span class="ferry-dur">{dur}</span></div>'
            f'  {"".join(sail_rows)}'
            f'</div>'
        )
    if not routes_html:
        return ""
    return (
        f'<div class="coastal-panel ferries-panel">'
        f'<h3 class="coastal-h3">⛴ BC Ferries</h3>'
        f'{"".join(routes_html)}'
        f'<p class="coastal-src">Source: bcferriesapi.ca</p>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Coastal strip: ferries (left) + right panel (tides + extras)
# ---------------------------------------------------------------------------

def _coastal_strip(
    tides: list,
    ferry_routes: list,
    whales: Optional[list] = None,
    wildfire: Optional[dict] = None,
    transit: Optional[list] = None,
    webcam_url: Optional[str] = None,
    trail_data: Optional[dict] = None,
) -> str:
    ferries_html = _ferries_widget(ferry_routes)
    right_html   = _coastal_right_panel(tides, whales, wildfire, transit, webcam_url, trail_data)
    if not ferries_html and not right_html:
        return ""
    return f'<div class="coastal-strip">{ferries_html}{right_html}</div>'


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
# Events section (full-width, bottom of page)
# ---------------------------------------------------------------------------

def _events_section(
    sources: dict[str, list[dict]],
    categories: Optional[dict[str, str]],
    top_n: int = 12,
) -> str:
    """Pull all Events-category sources into a dedicated bottom section."""
    items = []
    for name, source_items in sources.items():
        cat = (categories or {}).get(name, "")
        if cat == _EVENTS_CATEGORY:
            items.extend(source_items)

    if not items:
        return ""

    # Deduplicate by link, sort by score
    seen: set[str] = set()
    unique = []
    for item in sorted(items, key=lambda x: x.get("_score", 0), reverse=True):
        link = item.get("link", "")
        if link and link not in seen:
            seen.add(link)
            unique.append(item)

    cards = []
    for item in unique[:top_n]:
        title     = item.get("title", "")
        link      = item.get("link", "")
        summary   = (item.get("summary", "") or "")[:160].strip()
        thumbnail = item.get("thumbnail", "")
        age       = _rel_time(item.get("published"))
        anchor    = f'<a href="{link}" target="_blank">{title}</a>' if link else title
        age_html  = f'<span class="age">{age}</span>' if age else ""
        thumb_html = f'<img class="thumb" src="{thumbnail}" alt="">' if thumbnail else ""
        snip_html  = f'<p class="snip">{summary}</p>' if summary else ""
        cards.append(
            f'<div class="event-card">'
            f'{thumb_html}'
            f'<strong>{anchor}{age_html}</strong>'
            f'{snip_html}'
            f'</div>'
        )

    return f"""<section class="events-section">
  <h2 class="events-h2">&#128197; Events &amp; Community</h2>
  <div class="events-grid">{"".join(cards)}</div>
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
        if cat == _EVENTS_CATEGORY:
            continue   # handled separately in events section
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
    sun: Optional[dict] = None,
    aqhi: Optional[dict] = None,
    tides: Optional[list] = None,
    ferries: Optional[list] = None,
    whales: Optional[list] = None,
    wildfire: Optional[dict] = None,
    transit: Optional[list] = None,
    webcam_url: Optional[str] = None,
    trail_data: Optional[dict] = None,
    entities: Optional[dict] = None,
    photos: Optional[list] = None,
) -> str:
    today = datetime.now().strftime("%A, %B %-d, %Y")

    major        = _major_stories_section(major_stories or [], photo_list=photos)
    grid         = _flat_grid(sources, categories, top_n)
    events_html  = _events_section(sources, categories)
    weather_html = _weather_widget(forecast or [], sun=sun or {}, aqhi=aqhi or {})
    coastal_html = _coastal_strip(
        tides or [], ferries or [],
        whales=whales, wildfire=wildfire,
        transit=transit, webcam_url=webcam_url,
        trail_data=trail_data,
    )
    ner_html     = _ner_card(entities or {})

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
  .photos-panel {{ flex-shrink: 0; width: 420px; display: flex; flex-direction: column; gap: 8px; }}
  .photos-h2 {{ margin: 0 0 6px; font-size: 0.75em; text-transform: uppercase;
                letter-spacing: 0.08em; color: #1a1a2e; }}
  .pgrid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .pgrid-cell {{ position: relative; overflow: hidden; border-radius: 6px; }}
  .pgrid-img {{ width: 100%; height: 160px; object-fit: cover; display: block;
                transition: transform 0.25s; }}
  .pgrid-cell:hover .pgrid-img {{ transform: scale(1.05); }}
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

  /* Story age */
  .age {{ font-size:0.75em; color:#aaa; margin-left:4px; white-space:nowrap; }}

  /* NER card */
  .ner-card {{ display:flex; gap:0; padding:0; margin-top:14px; }}
  .ner-col {{ flex:1; padding:14px; border-right:1px solid #eee; }}
  .ner-col:last-child {{ border-right:none; }}
  .ner-col h4 {{ margin:0 0 8px; font-size:0.72em; text-transform:uppercase; letter-spacing:0.06em; color:#555; }}
  .ner-col ul {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:4px; }}
  .ner-col li {{ font-size:0.83em; color:#333; }}

  /* Coastal strip */
  .coastal-strip {{ display:flex; gap:14px; margin-bottom:16px; align-items:stretch; }}
  .coastal-panel {{ background:#fff; border:1px solid #ddd; border-radius:7px;
                    padding:12px 16px; min-width:0; }}
  .ferries-panel {{ flex:1.4; }}
  .coastal-right {{ flex:1; display:flex; flex-direction:column; gap:0; padding:0; overflow:visible; border-radius:7px; }}
  .coastal-h3 {{ margin:0 0 10px; font-size:0.72em; text-transform:uppercase;
                 letter-spacing:0.07em; color:#555; }}
  .coastal-src {{ margin:6px 0 0; font-size:0.65em; color:#bbb; }}

  /* Coastal right panel sections */
  .crp-section {{ padding:12px 16px; border-bottom:1px solid #eee; }}
  .crp-section:last-child {{ border-bottom:none; }}
  .crp-h4 {{ margin:0 0 8px; font-size:0.72em; text-transform:uppercase;
             letter-spacing:0.07em; color:#555; }}
  .crp-list {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:5px; }}
  .crp-list li {{ font-size:0.82em; color:#333; }}
  .crp-list a {{ color:#1a1a2e; text-decoration:none; }}
  .crp-list a:hover {{ color:#1a6b9a; text-decoration:underline; }}
  .crp-age {{ font-size:0.78em; color:#aaa; margin-left:4px; }}
  .crp-ok {{ font-size:0.82em; color:#2d6a4f; margin:0; }}
  .crp-fire-count {{ font-size:0.82em; margin:0 0 6px; color:#333; }}
  .crp-fire-meta {{ font-size:0.78em; color:#888; margin-left:4px; }}
  .crp-transit-desc {{ font-size:0.78em; color:#666; }}
  .crp-trail-status {{ font-size:0.82em; margin:0 0 5px; }}
  .crp-trail-feat {{ font-size:0.82em; margin:4px 0 0; color:#333; }}
  .crp-trail-feat a {{ color:#1a1a2e; text-decoration:none; }}
  .crp-trail-feat a:hover {{ color:#1a6b9a; text-decoration:underline; }}
  .crp-trail-link {{ font-size:0.85em; color:#1a6b9a; text-decoration:none; margin-left:4px; }}
  .crp-trail-link:hover {{ text-decoration:underline; }}
  .crp-minigrid {{ display:grid; grid-template-columns:1fr 1fr; gap:0; }}
  .crp-mini {{ padding:10px 14px; border-top:1px solid #eee; }}
  .crp-mini:nth-child(even) {{ border-left:1px solid #eee; }}
  .crp-h5 {{ margin:0 0 6px; font-size:0.7em; text-transform:uppercase;
             letter-spacing:0.06em; color:#555; }}
  .webcam-img {{ width:100%; border-radius:4px; display:block; object-fit:cover; max-height:90px; }}

  /* Tides */
  .tides-row {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .tide-event {{ display:flex; flex-direction:column; align-items:center; gap:3px;
                 background:#f7f9fc; border-radius:6px; padding:8px 12px; min-width:86px; }}
  .tide-event.tide-past {{ opacity:0.4; }}
  .tide-type {{ font-size:0.7em; font-weight:700; text-transform:uppercase;
                letter-spacing:0.05em; padding:2px 6px; border-radius:3px; }}
  .tide-high {{ background:#1a6b9a; color:#fff; }}
  .tide-low  {{ background:#5a8a6a; color:#fff; }}
  .tide-time {{ font-size:0.85em; font-weight:600; color:#222; }}
  .tide-ht   {{ font-size:0.73em; color:#777; }}

  /* Ferries */
  .ferry-route {{ margin-bottom:10px; }}
  .ferry-route:last-child {{ margin-bottom:0; }}
  .ferry-route-hdr {{ font-size:0.8em; font-weight:700; color:#333; margin-bottom:6px; }}
  .ferry-dur {{ font-weight:400; color:#888; margin-left:6px; }}
  .sailing {{ display:flex; align-items:center; gap:8px; font-size:0.82em;
              padding:5px 0; border-bottom:1px solid #f0f0f0; flex-wrap:wrap; }}
  .sailing:last-child {{ border-bottom:none; }}
  .sailing-current {{ background:#fffbe6; border-radius:4px; padding:5px 8px;
                      border-bottom:none; margin-bottom:4px; }}
  .sail-now {{ font-size:0.7em; font-weight:700; text-transform:uppercase;
               background:#e6a817; color:#fff; border-radius:3px; padding:1px 5px; }}
  .sail-time {{ font-weight:600; color:#1a1a2e; white-space:nowrap; }}
  .sail-arr  {{ color:#888; white-space:nowrap; }}
  .sail-vessel {{ flex:1; color:#555; font-size:0.9em; white-space:nowrap;
                  overflow:hidden; text-overflow:ellipsis; }}
  .sail-fill {{ font-size:0.78em; font-weight:700; padding:2px 7px;
                border-radius:10px; white-space:nowrap; }}
  .fill-low  {{ background:#d4edda; color:#155724; }}
  .fill-mid  {{ background:#fff3cd; color:#856404; }}
  .fill-high {{ background:#f8d7da; color:#721c24; }}
  .vessel-alert {{ font-size:0.78em; color:#c0392b; }}

  /* Events section */
  .events-section {{ background:#fff; border:1px solid #ddd; border-radius:7px;
                     padding:14px 20px; margin-top:16px; }}
  .events-h2 {{ margin:0 0 12px; font-size:0.85em; text-transform:uppercase;
                letter-spacing:0.06em; color:#2d6a4f; border-bottom:1px solid #eee;
                padding-bottom:8px; }}
  .events-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
  .event-card {{ font-size:0.85em; display:flex; flex-direction:column; gap:5px; }}
  .event-card .thumb {{ height:90px; border-radius:5px; }}
  .event-card strong a {{ color:#1a1a2e; text-decoration:none; line-height:1.35; display:block; }}
  .event-card strong a:hover {{ color:#2d6a4f; text-decoration:underline; }}
  @media (max-width:900px) {{ .events-grid {{ grid-template-columns:repeat(2,1fr); }} }}
  @media (max-width:520px) {{ .events-grid {{ grid-template-columns:1fr; }} }}

  @media (max-width:700px) {{ .coastal-strip {{ flex-direction:column; }} }}
</style>
</head><body>

<div class="masthead">
  <h1>Victoria Morning Brief</h1>
  <p class="date">{today}</p>
</div>

{weather_html}
{major}
{coastal_html}
{grid}
{events_html}
{ner_html}

<p class="meta">Generated by victoria-brief.</p>
</body></html>"""
