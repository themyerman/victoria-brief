"""
Bicycle & pedestrian trail counts for Victoria / CRD.
Data: CRD Regional Cyclist and Pedestrian Count Program via Eco-Counter public API.
43 automated counters across the region, updated daily.
"""
from __future__ import annotations

import requests

_API_URL = "https://www.eco-visio.net/api/aladdin/1.0.0/pbl/publicwebpageplus/4828"
_DASHBOARD_URL = "https://data.eco-counter.com/ParcPublic/?id=4828"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Hand-picked counters covering the main trails people care about
# idPdc values confirmed from the API
_FEATURED_IDS = {
    100053581: "Galloping Goose",   # South of Culduthal — highest traffic GG point
    100053580: "Lochside Trail",    # South of Nigel Ave
    100053578: "E&N Trail",         # West of Hallowell Rd
    100053584: "Harbour Pathway",   # if present
}


def fetch_bike_counts() -> dict:
    """
    Returns dict with:
      counters  — list of {name, last_day, avg_day, vs_avg_pct, trend_icon}
      total_yesterday — sum of lastDay across all counters
      dashboard_url
    """
    try:
        r = requests.get(_API_URL, headers={"User-Agent": _UA}, timeout=12)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}

    if not isinstance(data, list):
        return {}

    # Build featured counters (those we named above) + fall back to top-3 by avg
    featured = []
    for c in data:
        pdc_id  = c.get("idPdc")
        name    = _FEATURED_IDS.get(pdc_id)
        if not name:
            continue
        last    = c.get("lastDay", 0) or 0
        avg     = c.get("moyD", 0) or 0
        if avg > 0:
            pct = round((last - avg) / avg * 100)
        else:
            pct = 0
        if pct >= 10:
            trend = "📈"
        elif pct <= -10:
            trend = "📉"
        else:
            trend = "➡️"
        featured.append({
            "name": name,
            "last_day": last,
            "avg_day": avg,
            "vs_avg_pct": pct,
            "trend": trend,
        })

    # Fall back: if we matched fewer than 2, just take top-3 by avg_day
    if len(featured) < 2:
        fallback = sorted(data, key=lambda c: c.get("moyD", 0), reverse=True)[:3]
        featured = []
        for c in fallback:
            last = c.get("lastDay", 0) or 0
            avg  = c.get("moyD", 0) or 0
            pct  = round((last - avg) / avg * 100) if avg > 0 else 0
            trend = "📈" if pct >= 10 else ("📉" if pct <= -10 else "➡️")
            featured.append({
                "name": c.get("nom", "Unknown"),
                "last_day": last,
                "avg_day": avg,
                "vs_avg_pct": pct,
                "trend": trend,
            })

    total_yesterday = sum(c.get("lastDay", 0) or 0 for c in data)

    return {
        "counters": featured,
        "total_yesterday": total_yesterday,
        "num_counters": len(data),
        "dashboard_url": _DASHBOARD_URL,
    }
