from __future__ import annotations

"""
Weather forecast for Victoria BC using Open-Meteo (no API key required).
Also fetches sunrise/sunset from sunrise-sunset.org and AQHI from
Environment Canada — all free, no API key needed.
Uses only stdlib: urllib.request, json.
"""

import json
import sys
import urllib.request
from urllib.request import Request, urlopen

_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=48.4284&longitude=-123.3656"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode"
    "&timezone=America%2FVancouver&forecast_days=3"
)

_WMO: dict[int, tuple[str, str]] = {
    0:  ("☀️",  "Clear"),
    1:  ("🌤",  "Mainly clear"),
    2:  ("⛅",  "Partly cloudy"),
    3:  ("☁️",  "Overcast"),
    45: ("🌫",  "Fog"),
    48: ("🌫",  "Icy fog"),
    51: ("🌦",  "Light drizzle"),
    53: ("🌦",  "Drizzle"),
    55: ("🌧",  "Heavy drizzle"),
    61: ("🌧",  "Light rain"),
    63: ("🌧",  "Rain"),
    65: ("🌧",  "Heavy rain"),
    71: ("🌨",  "Light snow"),
    73: ("🌨",  "Snow"),
    75: ("❄️",  "Heavy snow"),
    80: ("🌦",  "Light showers"),
    81: ("🌧",  "Showers"),
    82: ("⛈",  "Heavy showers"),
    95: ("⛈",  "Thunderstorm"),
}


def _c_to_f(c: float) -> float:
    return round(c * 9 / 5 + 32, 1)


def fetch_forecast() -> list[dict]:
    """
    Returns a list of up to 3 dicts, one per day:
        label, icon, desc, high_c, low_c, high_f, low_f, precip_pct
    Returns [] on any failure.
    """
    try:
        with urllib.request.urlopen(_URL, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        daily = data["daily"]
        dates      = daily["time"]
        highs      = daily["temperature_2m_max"]
        lows       = daily["temperature_2m_min"]
        precips    = daily["precipitation_probability_max"]
        codes      = daily["weathercode"]

        result = []
        for i, date_str in enumerate(dates[:3]):
            if i == 0:
                label = "Today"
            elif i == 1:
                label = "Tomorrow"
            else:
                from datetime import datetime
                label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")

            code = int(codes[i]) if codes[i] is not None else 0
            icon, desc = _WMO.get(code, ("🌡", "Unknown"))
            high_c = round(float(highs[i]), 1) if highs[i] is not None else 0.0
            low_c  = round(float(lows[i]),  1) if lows[i]  is not None else 0.0
            precip = int(precips[i]) if precips[i] is not None else 0

            result.append({
                "label":      label,
                "icon":       icon,
                "desc":       desc,
                "high_c":     high_c,
                "low_c":      low_c,
                "high_f":     _c_to_f(high_c),
                "low_f":      _c_to_f(low_c),
                "precip_pct": precip,
            })
        return result

    except Exception as exc:
        print(f"  [warn] Weather fetch failed: {exc}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Sunrise / Sunset
# ---------------------------------------------------------------------------

_SUN_URL = (
    "https://api.sunrise-sunset.org/json"
    "?lat=48.4284&lng=-123.3656&tzid=America/Vancouver"
)


def fetch_sun() -> dict:
    """
    Returns dict with sunrise, sunset, day_length strings (local Victoria time).
    Returns {} on any failure.
    """
    try:
        req = Request(_SUN_URL, headers={"User-Agent": "victoria-brief/1.0"})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        if data.get("status") != "OK":
            return {}
        r = data["results"]

        def _fmt(t: str) -> str:
            """'6:30:32 AM' → '6:30 AM'"""
            parts = t.split(":")
            return f"{parts[0]}:{parts[1]} {t.split()[-1]}" if len(parts) >= 2 else t

        return {
            "sunrise":    _fmt(r.get("sunrise", "")),
            "sunset":     _fmt(r.get("sunset", "")),
            "day_length": r.get("day_length", ""),
        }
    except Exception as exc:
        print(f"  [warn] Sunrise/sunset fetch failed: {exc}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# Air Quality Index (AQHI) — Environment Canada
# ---------------------------------------------------------------------------

_AQHI_URL = (
    "https://api.weather.gc.ca/collections/aqhi-observations-realtime/items"
    "?f=json&limit=1&sortby=-observation_datetime&location_id=JBOBQ"
)

_AQHI_LABELS = [
    (3,  "Low",       "🟢"),
    (6,  "Moderate",  "🟡"),
    (10, "High",      "🟠"),
    (99, "Very High", "🔴"),
]


def _aqhi_label(value: float) -> tuple[str, str]:
    for threshold, label, icon in _AQHI_LABELS:
        if value <= threshold:
            return label, icon
    return "Very High", "🔴"


def fetch_aqhi() -> dict:
    """
    Returns dict: value (float), label, icon, updated_text.
    Returns {} on any failure.
    """
    try:
        req = Request(_AQHI_URL, headers={
            "User-Agent": "victoria-brief/1.0",
            "Accept": "application/json",
        })
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        features = data.get("features", [])
        if not features:
            return {}

        props = features[0].get("properties", {})
        value = props.get("aqhi")
        if value is None:
            return {}

        value = round(float(value), 1)
        label, icon = _aqhi_label(value)
        return {
            "value":        value,
            "label":        label,
            "icon":         icon,
            "updated_text": props.get("observation_datetime_text_en", ""),
        }
    except Exception as exc:
        print(f"  [warn] AQHI fetch failed: {exc}", file=sys.stderr)
        return {}
