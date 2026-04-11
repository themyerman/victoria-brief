from __future__ import annotations

"""
BC Ferries sailing status via bcferriesapi.ca (community API, no key required).
Fetches next sailings + fill % for Swartz Bay ↔ Tsawwassen (the main Victoria route).
"""

import json
import sys
from urllib.request import Request, urlopen

_API = "https://bcferriesapi.ca/v2/capacity/"

# Terminal display names
_TERMINAL_NAMES = {
    "SWB": "Swartz Bay",
    "TSA": "Tsawwassen",
    "HSB": "Horseshoe Bay",
    "DUK": "Duke Point",
    "LNG": "Langdale",
    "NAN": "Departure Bay",
    "FUL": "Fulford Harbour",
    "BOW": "Bowen Island",
    "SGI": "Salt Spring / Long Harbour",
}

# Routes to include (both directions)
_WANTED = {("SWB", "TSA"), ("TSA", "SWB")}


def _fill_label(pct: int) -> str:
    """Human-readable fill label."""
    if pct == 0:
        return "Empty"
    if pct < 25:
        return f"{pct}%"
    return f"{pct}%"


def _fill_class(pct: int) -> str:
    """CSS class name for colour-coding fill."""
    if pct < 50:
        return "fill-low"
    if pct < 80:
        return "fill-mid"
    return "fill-high"


def fetch_ferries() -> list[dict]:
    """
    Fetch upcoming sailings for Swartz Bay ↔ Tsawwassen.
    Returns a list of route dicts, each with:
        from_code / to_code / from_name / to_name / duration
        sailings: list of upcoming (current + future) sailings, each with:
            time / arrival_time / status / car_fill / vessel / vessel_status
            fill_class / fill_label
    Returns [] on any failure.
    """
    try:
        req = Request(_API, headers={
            "User-Agent": "victoria-brief/1.0",
            "Accept": "application/json",
        })
        with urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())

        routes_out = []
        for route in data.get("routes", []):
            dep = route.get("fromTerminalCode", "")
            arr = route.get("toTerminalCode", "")
            if (dep, arr) not in _WANTED:
                continue

            sailings_raw = route.get("sailings", [])
            # Keep current sailing + up to 3 future ones
            upcoming = [
                s for s in sailings_raw
                if s.get("sailingStatus") in ("current", "future")
            ][:4]

            sailings = []
            for s in upcoming:
                car_fill = s.get("carFill", s.get("fill", 0))
                sailings.append({
                    "time":           s.get("time", ""),
                    "arrival_time":   s.get("arrivalTime", ""),
                    "status":         s.get("sailingStatus", ""),
                    "car_fill":       car_fill,
                    "fill_label":     _fill_label(car_fill),
                    "fill_class":     _fill_class(car_fill),
                    "vessel":         s.get("vesselName", ""),
                    "vessel_status":  s.get("vesselStatus", ""),
                })

            routes_out.append({
                "from_code": dep,
                "to_code":   arr,
                "from_name": _TERMINAL_NAMES.get(dep, dep),
                "to_name":   _TERMINAL_NAMES.get(arr, arr),
                "duration":  route.get("sailingDuration", ""),
                "sailings":  sailings,
            })

        # SWB→TSA first
        routes_out.sort(key=lambda r: (0 if r["from_code"] == "SWB" else 1))
        return routes_out

    except Exception as exc:
        print(f"  [warn] Ferries fetch failed: {exc}", file=sys.stderr)
        return []
