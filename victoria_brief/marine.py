from __future__ import annotations

"""
Marine forecast for Juan de Fuca Strait / Victoria BC coastal waters.

Source: Environment Canada MSC GeoMet OGC-API — marineweather-realtime collection.
Prefers "Juan de Fuca Strait" area; falls back to "Haro Strait" or any Georgia Basin
south coast area if Juan de Fuca is not in the bbox response.
"""

import sys
from datetime import datetime

import requests

_GEOMET_ITEMS = (
    "https://api.weather.gc.ca/collections/marineweather-realtime/items"
    "?f=json&lang=en&limit=50&bbox=-125.5,48.0,-122.5,48.9"
)

# Human-friendly page link (east entrance Juan de Fuca)
_MARINE_URL = "https://weather.gc.ca/marine/forecast_e.html?mapID=03&siteID=07010"

_UA = "victoria-brief/1.0 (contact: myerman@gmail.com)"

# Preference order for area names (first match wins)
_PREFERRED_AREAS = [
    "juan de fuca strait",
    "haro strait",
    "strait of georgia",
]


def fetch_marine_forecast() -> dict:
    """
    Returns dict with:
        location  — display name (e.g. "Juan de Fuca Strait")
        period    — forecast period ("Today Tonight and Monday.")
        summary   — combined weather/visibility sentence
        wind      — wind description
        source_url — link to full EC marine forecast page
        issued    — human-readable issue time or ""
    Returns {} on failure.
    """
    try:
        r = requests.get(_GEOMET_ITEMS, headers={"User-Agent": _UA}, timeout=12)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"  [warn] Marine GeoMet fetch failed: {exc}", file=sys.stderr)
        return {}

    features = data.get("features", [])
    if not features:
        return {}

    # Sort features by preference for area name
    def area_priority(feat: dict) -> int:
        area_name = (feat.get("properties", {}).get("area", {})
                     .get("value", {}).get("en", "")).lower()
        for i, pref in enumerate(_PREFERRED_AREAS):
            if pref in area_name:
                return i
        return len(_PREFERRED_AREAS)

    features_sorted = sorted(features, key=area_priority)
    target = features_sorted[0]

    props = target.get("properties", {})
    area  = props.get("area", {})
    loc_name = area.get("value", {}).get("en", "Juan de Fuca Strait")

    rf      = props.get("regularForecast", {})
    issued  = _parse_issued(rf.get("issuedDatetimeUTC", ""))
    locs    = rf.get("locations", [])

    # Use first location entry
    loc_data = locs[0] if locs else {}
    wc       = loc_data.get("weatherCondition", {})

    period   = wc.get("periodOfCoverage", {}).get("en", "")
    wind     = wc.get("wind", {}).get("en", "")
    vis      = wc.get("weatherVisibility", {}).get("en", "")
    waves    = wc.get("waves", {}).get("en", "")

    # Build a combined summary sentence
    summary_parts = []
    if vis:
        summary_parts.append(vis.rstrip("."))
    if waves:
        summary_parts.append(waves.rstrip("."))
    summary = ". ".join(summary_parts) if summary_parts else ""
    if not summary and wind:
        summary = wind[:180]

    return {
        "location":   loc_name,
        "period":     period,
        "summary":    summary[:200],
        "wind":       wind[:180],
        "source_url": _MARINE_URL,
        "issued":     issued,
    }


def _parse_issued(s: str) -> str:
    """Convert ISO datetime to 'Apr 12, 8:00 AM' format."""
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%b %-d, %-I:%M %p UTC")
    except Exception:
        return s[:30]
