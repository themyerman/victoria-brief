from __future__ import annotations

"""
Active wildfire data near Vancouver Island from the BC Wildfire Service
via the BC government WFS endpoint — no API key required.
Data refreshes every 15 minutes.
"""

import json
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_BASE = (
    "https://openmaps.gov.bc.ca/geo/pub/"
    "WHSE_LAND_AND_NATURAL_RESOURCE.PROT_CURRENT_FIRE_PNTS_SP/ows"
)

# Bounding box: Vancouver Island + Gulf Islands + Sunshine Coast
_LAT_MIN, _LAT_MAX =  48.0, 51.5
_LON_MIN, _LON_MAX = -129.0, -122.0

_STATUS_ICON = {
    "Active":          "🔴",
    "Out of Control":  "🔴",
    "Being Held":      "🟠",
    "Under Control":   "🟡",
}


def fetch_wildfire() -> dict:
    """
    Fetch active wildfires within ~300km of Victoria BC.
    Returns:
        fires          – list of up to 5 fire dicts, sorted fires-of-note first, then by size
        total_active   – total count of active fires in the region
        has_fire_of_note – bool: any fires of note?
        region_ok      – bool: True when no active fires
    Returns {} on any failure.
    """
    try:
        params = {
            "service":      "WFS",
            "version":      "2.0.0",
            "request":      "GetFeature",
            "typeName":     "WHSE_LAND_AND_NATURAL_RESOURCE.PROT_CURRENT_FIRE_PNTS_SP",
            "outputFormat": "application/json",
            "CQL_FILTER": (
                f"FIRE_STATUS NOT IN ('Out') "
                f"AND LATITUDE >= {_LAT_MIN} AND LATITUDE <= {_LAT_MAX} "
                f"AND LONGITUDE >= {_LON_MIN} AND LONGITUDE <= {_LON_MAX}"
            ),
            "count": "50",
        }
        url = _BASE + "?" + urlencode(params)
        req = Request(url, headers={
            "User-Agent": "victoria-brief/1.0",
            "Accept": "application/json",
        })
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        fires = []
        for feat in data.get("features", []):
            p    = feat["properties"]
            status = p.get("FIRE_STATUS", "")
            icon   = _STATUS_ICON.get(status, "🔥")
            size   = p.get("CURRENT_SIZE") or 0
            loc    = p.get("GEOGRAPHIC_DESCRIPTION", "")
            fon    = p.get("FIRE_OF_NOTE_IND", "N") == "Y"
            fires.append({
                "fire_number":   p.get("FIRE_NUMBER", ""),
                "status":        status,
                "icon":          icon,
                "location":      loc,
                "size_ha":       round(float(size), 1),
                "fire_of_note":  fon,
                "url":           p.get("FIRE_URL", ""),
            })

        # Fires of note first, then largest
        fires.sort(key=lambda x: (not x["fire_of_note"], -x["size_ha"]))

        return {
            "fires":            fires[:5],
            "total_active":     len(fires),
            "has_fire_of_note": any(f["fire_of_note"] for f in fires),
            "region_ok":        len(fires) == 0,
        }

    except Exception as exc:
        print(f"  [warn] Wildfire fetch failed: {exc}", file=sys.stderr)
        return {}
