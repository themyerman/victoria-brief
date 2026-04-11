from __future__ import annotations

"""
Weather forecast for Victoria BC using Open-Meteo (no API key required).
Uses only stdlib: urllib.request, json.
"""

import json
import sys
import urllib.request

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
