from __future__ import annotations
from datetime import datetime
from typing import Optional


CATEGORY_LABELS = {
    "tech_startups":    "Tech & Startups",
    "jobs":             "Jobs",
    "cultural_events":  "Cultural Events",
    "first_nations":    "First Nations",
    "bc_legislature":   "BC Legislature",
    "arts_funding":     "Arts Funding",
    "uvic_camosun":     "UVic & Camosun",
    "bc_ferries":       "BC Ferries",
    "real_estate":      "Housing & Real Estate",
    "general_victoria": "General Victoria",
}


def _sentiment_bar(sentiment: dict) -> str:
    pos = sentiment["positive_pct"]
    neu = sentiment["neutral_pct"]
    neg = sentiment["negative_pct"]
    overall = sentiment["overall"]
    score = sentiment["score"]
    label_color = {"positive": "#2a7a2a", "neutral": "#888", "negative": "#c0392b"}[overall]
    return f"""
<div class="sentiment">
  <span class="sentiment-label" style="color:{label_color}">
    Overall tone: <strong>{overall}</strong> (score: {score:+.3f})
  </span>
  <div class="sentiment-bar">
    <div class="bar-pos" style="width:{pos}%" title="Positive {pos}%"></div>
    <div class="bar-neu" style="width:{neu}%" title="Neutral {neu}%"></div>
    <div class="bar-neg" style="width:{neg}%" title="Negative {neg}%"></div>
  </div>
  <div class="sentiment-pcts">
    <span style="color:#2a7a2a">&#9632; {pos}% positive</span>
    &nbsp;&nbsp;
    <span style="color:#888">&#9632; {neu}% neutral</span>
    &nbsp;&nbsp;
    <span style="color:#c0392b">&#9632; {neg}% negative</span>
  </div>
</div>"""


def _keywords_block(keywords: list[str]) -> str:
    tags = "".join(f'<span class="kw">{k}</span>' for k in keywords)
    return f'<div class="keywords"><strong>Today\'s keywords:</strong> {tags}</div>'


def to_html(
    rss_items: dict,
    supplemental: dict,
    stock_prices: dict,
    keywords: Optional[list[str]] = None,
    sentiment: Optional[dict] = None,
) -> str:
    today = datetime.now().strftime("%A, %B %-d, %Y")
    sections = []

    for cat, label in CATEGORY_LABELS.items():
        combined = rss_items.get(cat, []) + supplemental.get(cat, [])
        if not combined:
            continue

        items_html = []
        for item in combined[:15]:
            title = item.get("title", "(no title)")
            link = item.get("link", "")
            body = (item.get("summary") or item.get("snippet", "")).strip()
            anchor = f'<a href="{link}">{title}</a>' if link else title
            snippet = f"<p>{body}</p>" if body else ""
            items_html.append(f"<li><strong>{anchor}</strong>{snippet}</li>")

        sections.append(f"""
<section>
  <h2>{label}</h2>
  <ul>{"".join(items_html)}</ul>
</section>""")

    stocks_html = ""
    if stock_prices:
        rows = []
        for ticker, data in stock_prices.items():
            sign = "+" if data["change_pct"] >= 0 else ""
            color = "#2a7a2a" if data["change_pct"] >= 0 else "#c0392b"
            rows.append(
                f'<tr><td>{ticker}</td>'
                f'<td>{data["currency"]} ${data["price"]}</td>'
                f'<td style="color:{color}">{sign}{data["change_pct"]}%</td></tr>'
            )
        stocks_html = f"""
<section>
  <h2>Stock Watch</h2>
  <table>
    <thead><tr><th>Ticker</th><th>Price</th><th>Change</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
</section>"""

    nlp_header = ""
    if sentiment:
        nlp_header += _sentiment_bar(sentiment)
    if keywords:
        nlp_header += _keywords_block(keywords)

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Victoria Morning Brief — {today}</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 720px; margin: 40px auto; padding: 0 20px; color: #222; line-height: 1.6; }}
  h1 {{ font-size: 1.6em; border-bottom: 2px solid #333; padding-bottom: 10px; }}
  h2 {{ font-size: 1.1em; margin-top: 2em; color: #444; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
  ul {{ padding-left: 1.2em; }}
  li {{ margin-bottom: 1em; }}
  li p {{ margin: 4px 0 0; font-size: 0.9em; color: #555; }}
  a {{ color: #1a6b9a; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 6px 12px; border-bottom: 1px solid #eee; }}
  th {{ background: #f5f5f5; font-size: 0.85em; }}
  .meta {{ color: #888; font-size: 0.85em; margin-top: 2em; border-top: 1px solid #eee; padding-top: 1em; }}
  .sentiment {{ background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin: 1em 0; }}
  .sentiment-label {{ font-size: 0.95em; }}
  .sentiment-bar {{ display: flex; height: 10px; border-radius: 4px; overflow: hidden; margin: 8px 0; }}
  .bar-pos {{ background: #2a7a2a; }}
  .bar-neu {{ background: #bbb; }}
  .bar-neg {{ background: #c0392b; }}
  .sentiment-pcts {{ font-size: 0.8em; }}
  .keywords {{ margin: 0.8em 0; font-size: 0.9em; line-height: 2; }}
  .kw {{ display: inline-block; background: #e8f0fe; color: #1a4a8a; border-radius: 3px; padding: 2px 8px; margin: 2px 3px; font-size: 0.85em; }}
</style>
</head><body>
<h1>Victoria Morning Brief</h1>
<p class="meta">{today}</p>
{nlp_header}
{"".join(sections)}
{stocks_html}
<p class="meta">Generated by victoria-brief.</p>
</body></html>"""
