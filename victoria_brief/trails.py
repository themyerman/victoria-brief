"""Trail conditions for Victoria BC, derived from recent precipitation."""
from __future__ import annotations

import requests
from datetime import datetime

# Static list of popular Victoria / CRD trails — rotated as "featured" by day of year
_TRAILS = [
    {
        "name": "Galloping Goose Regional Trail",
        "type": "Paved/Gravel",
        "km": "55 km",
        "url": "https://www.crd.bc.ca/parks-recreation-culture/parks-natural-areas/trails/regional-trails/galloping-goose",
    },
    {
        "name": "Lochside Regional Trail",
        "type": "Paved/Gravel",
        "km": "29 km",
        "url": "https://www.crd.bc.ca/parks-recreation-culture/parks-natural-areas/trails/regional-trails/lochside",
    },
    {
        "name": "Hartland MTB Trails",
        "type": "Mountain Bike",
        "km": "25 km",
        "url": "https://www.trailforks.com/region/hartland-landfill/",
    },
    {
        "name": "Bear Mountain Trails",
        "type": "Mountain Bike",
        "km": "40+ km",
        "url": "https://www.trailforks.com/region/bear-mountain/",
    },
    {
        "name": "McKenzie Bight Trail",
        "type": "Forest / Coastal",
        "km": "8 km",
        "url": "https://bcparks.ca/gowlland-tod-provincial-park/",
    },
    {
        "name": "Durrance Lake Loop",
        "type": "Forest",
        "km": "5 km",
        "url": "https://www.alltrails.com/trail/canada/british-columbia/durrance-lake-loop",
    },
    {
        "name": "Roche Cove Regional Park",
        "type": "Forest / Coast",
        "km": "7 km",
        "url": "https://www.crd.bc.ca/parks-recreation-culture/parks-natural-areas/find-park-trail/roche-cove-regional-park",
    },
    {
        "name": "Mount Work Regional Park",
        "type": "Forest",
        "km": "15 km",
        "url": "https://www.crd.bc.ca/parks-recreation-culture/parks-natural-areas/find-park-trail/mount-work-regional-park",
    },
    {
        "name": "Thetis Lake Regional Park",
        "type": "Forest / Swimming",
        "km": "12 km",
        "url": "https://www.crd.bc.ca/parks-recreation-culture/parks-natural-areas/find-park-trail/thetis-lake-regional-park",
    },
    {
        "name": "Sea to Sea Regional Park",
        "type": "Forest / Waterfall",
        "km": "20 km",
        "url": "https://www.crd.bc.ca/parks-recreation-culture/parks-natural-areas/find-park-trail/sea-to-sea-regional-park",
    },
]


def _condition_from_precip(mm: float) -> dict:
    if mm == 0:
        return {"condition": "Dry", "label": "Excellent", "icon": "🟢",
                "note": "Trails are dry — great day for a ride or hike"}
    if mm < 3:
        return {"condition": "Damp", "label": "Good", "icon": "🟡",
                "note": "Light moisture — minor mud possible on forest trails"}
    if mm < 10:
        return {"condition": "Wet", "label": "Fair", "icon": "🟠",
                "note": "Muddy conditions — stick to gravel/paved routes"}
    return {"condition": "Very Wet", "label": "Poor", "icon": "🔴",
            "note": "Heavy rain — avoid technical MTB, trail damage risk"}


def fetch_trail_conditions() -> dict:
    """Return trail conditions derived from recent 24h precipitation."""
    precip_24h = 0.0
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 48.4284,
                "longitude": -123.3656,
                "hourly": "precipitation",
                "past_days": 1,
                "forecast_days": 0,
                "timezone": "America/Vancouver",
            },
            timeout=10,
        )
        data = r.json()
        precip_24h = round(sum(data["hourly"]["precipitation"][-24:]), 1)
    except Exception:
        pass

    status = _condition_from_precip(precip_24h)

    # Rotate featured trail by day of year
    day_idx = datetime.now().timetuple().tm_yday % len(_TRAILS)
    featured = _TRAILS[day_idx]

    return {
        "precip_24h": precip_24h,
        "featured": featured,
        "trailforks_url": "https://www.trailforks.com/region/victoria/",
        **status,
    }
