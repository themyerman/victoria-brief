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

# Direct item ID for Juan de Fuca Strait (confirmed by EC GeoMet API)
# Fallback: bbox query covering Victoria-area marine zones
_GEOMET_ITEM  = "https://api.weather.gc.ca/collections/marineweather-realtime/items/m0000009?f=json"
_GEOMET_ITEMS = (
    "https://api.weather.gc.ca/collections/marineweather-realtime/items"
    "?f=json&lang=en&limit=50&bbox=-125.5,48.0,-122.5,48.9"
)

# Human-friendly page link (east entrance Juan de Fuca)
_MARINE_URL = "https://weather.gc.ca/marine/forecast_e.html?mapID=03&siteID=07010"

_UA = "victoria-brief/1.0 (contact: myerman@gmail.com)"

# Preference order for area names when using bbox fallback (first match wins)
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
        warnings  — list of active warning strings (may be empty)
        source_url — link to full EC marine forecast page
        issued    — human-readable issue time or ""
    Returns {} on failure.
    """
    # Try direct item ID first (faster, confirmed working)
    try:
        r = requests.get(_GEOMET_ITEM, headers={"User-Agent": _UA}, timeout=12)
        r.raise_for_status()
        data = r.json()
        # Single-item response has properties at top level
        if data.get("type") == "Feature":
            return _parse_feature(data)
    except Exception as exc:
        print(f"  [warn] Marine direct fetch failed, trying bbox: {exc}", file=sys.stderr)

    # Fallback: bbox query
    try:
        r = requests.get(_GEOMET_ITEMS, headers={"User-Agent": _UA}, timeout=12)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"  [warn] Marine GeoMet bbox fetch failed: {exc}", file=sys.stderr)
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

    return _parse_feature(target)


def _parse_feature(feature: dict) -> dict:
    """Parse a single GeoJSON Feature from the marine weather API."""
    props    = feature.get("properties", {})
    area     = props.get("area", {})
    loc_name = area.get("value", {}).get("en", "Juan de Fuca Strait")

    rf      = props.get("regularForecast", {})
    issued  = _parse_issued(rf.get("issuedDatetimeUTC", ""))
    locs    = rf.get("locations", [])

    # Use first location entry (east entrance for Juan de Fuca)
    loc_data = locs[0] if locs else {}
    wc       = loc_data.get("weatherCondition", {})

    period = wc.get("periodOfCoverage", {}).get("en", "")
    wind   = wc.get("wind", {}).get("en", "")
    vis    = wc.get("weatherVisibility", {}).get("en", "")
    waves  = wc.get("waves", {}).get("en", "")

    # Build combined weather/vis summary (separate from wind)
    summary_parts = []
    if vis:
        summary_parts.append(vis.rstrip("."))
    if waves:
        summary_parts.append(waves.rstrip("."))
    summary = ". ".join(summary_parts) if summary_parts else ""

    # Active warnings
    warnings_raw = props.get("warnings", {}).get("locations", [])
    warning_names: list[str] = []
    for wloc in warnings_raw:
        for ev in wloc.get("events", []):
            name = ev.get("name", {})
            label = name.get("en", "") if isinstance(name, dict) else str(name)
            if label and label not in warning_names:
                warning_names.append(label)

    return {
        "location":   loc_name,
        "period":     period,
        "summary":    summary[:200],
        "wind":       wind[:220],
        "warnings":   warning_names,
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
