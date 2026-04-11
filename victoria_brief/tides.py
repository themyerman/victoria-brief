from __future__ import annotations

"""
Tidal predictions for Victoria Harbour (Station 07120) from the
Canadian Hydrographic Service (DFO) API — no key required.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

_STATION_UUID = "5cebf1df3d0f4a073c4bbd1e"   # Victoria Harbour
_BASE = "https://api-iwls.dfo-mpo.gc.ca/api/v1"


def _vancouver_tz():
    """Return zoneinfo or a fixed-offset fallback for America/Vancouver."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/Vancouver")
    except Exception:
        # Python < 3.9 fallback: approximate with DST heuristic
        now = datetime.now(timezone.utc)
        # DST runs second Sunday March → first Sunday November
        offset = -7 if 3 <= now.month <= 10 else -8
        return timezone(timedelta(hours=offset))


def _classify(tides: list[dict]) -> list[dict]:
    """Label each event High or Low by comparing to its neighbours."""
    vals = [t["value_m"] for t in tides]
    for i, tide in enumerate(tides):
        prev = vals[i - 1] if i > 0 else None
        nxt  = vals[i + 1] if i < len(vals) - 1 else None
        if prev is None:
            tide["type"] = "High" if (nxt is not None and vals[i] > nxt) else "Low"
        elif nxt is None:
            tide["type"] = "High" if vals[i] > prev else "Low"
        else:
            tide["type"] = "High" if vals[i] > prev and vals[i] > nxt else "Low"
    return tides


def fetch_tides() -> list[dict]:
    """
    Fetch today's high/low tide predictions for Victoria Harbour.
    Returns a list of dicts:
        time_str   – "6:42 AM"
        value_m    – 2.56  (metres)
        value_ft   – 8.4   (feet)
        type       – "High" | "Low"
        past       – True if tide time has already passed
    Returns [] on any failure.
    """
    try:
        tz = _vancouver_tz()
        now_utc = datetime.now(timezone.utc)

        # Fetch midnight → midnight+28h to capture all turning points for the day
        start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end   = start + timedelta(hours=28)

        url = (
            f"{_BASE}/stations/{_STATION_UUID}/data"
            f"?time-series-code=wlp-hilo"
            f"&from={start.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f"&to={end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )
        req = Request(url, headers={
            "User-Agent": "victoria-brief/1.0",
            "Accept": "application/json",
        })
        with urlopen(req, timeout=12) as resp:
            raw = json.loads(resp.read())

        if not raw:
            return []

        tides = []
        for entry in raw:
            dt_utc   = datetime.fromisoformat(entry["eventDate"].replace("Z", "+00:00"))
            dt_local = dt_utc.astimezone(tz)
            val_m    = round(float(entry["value"]), 2)
            tides.append({
                "time_str":  dt_local.strftime("%-I:%M %p"),
                "value_m":   val_m,
                "value_ft":  round(val_m * 3.28084, 1),
                "type":      None,          # filled by _classify
                "past":      dt_utc < now_utc,
                "_dt":       dt_utc,
            })

        _classify(tides)

        # Drop the internal _dt key
        for t in tides:
            t.pop("_dt", None)

        return tides

    except Exception as exc:
        print(f"  [warn] Tides fetch failed: {exc}", file=sys.stderr)
        return []
