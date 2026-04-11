from __future__ import annotations

"""
BC Transit service alerts for Victoria (operator 48) via GTFS-Realtime.
Requires: pip install gtfs-realtime-bindings
Feed: https://bct.tmix.se/gtfs-realtime/alerts.pb?operatorIds=48
"""

import sys
from urllib.request import urlopen

_FEED_URL = "https://bct.tmix.se/gtfs-realtime/alerts.pb?operatorIds=48"

_EFFECT_LABEL = {
    1:  "No service",
    2:  "Reduced service",
    3:  "Significant delays",
    4:  "Detour",
    5:  "Additional service",
    6:  "Modified service",
    7:  "Other effect",
    9:  "Stop moved",
    10: "No effect",
    11: "Accessibility issue",
}

_EFFECT_ICON = {
    1: "🚫",
    2: "🔻",
    3: "⏱",
    4: "↩️",
    9: "📍",
}


def fetch_transit_alerts(max_alerts: int = 5) -> list[dict]:
    """
    Fetch active BC Transit service alerts for Victoria.
    Returns list of dicts:
        header      – short alert title (e.g. "DETOUR", "STOP CLOSURE")
        description – first ~120 chars of the alert body
        effect      – human-readable effect label
        icon        – emoji for the effect type
    Returns [] on any failure or if package not installed.
    """
    try:
        from google.transit import gtfs_realtime_pb2
    except ImportError:
        print("  [warn] gtfs-realtime-bindings not installed — skipping transit alerts", file=sys.stderr)
        return []

    try:
        with urlopen(_FEED_URL, timeout=12) as resp:
            raw = resp.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(raw)

        alerts = []
        for entity in feed.entity:
            if not entity.HasField("alert"):
                continue
            a = entity.alert

            header = (
                a.header_text.translation[0].text
                if a.header_text.translation else ""
            )
            desc_full = (
                a.description_text.translation[0].text.strip()
                if a.description_text.translation else ""
            )
            # Trim to first sentence or 120 chars
            desc = desc_full.split("\n")[0][:120]
            if len(desc_full.split("\n")[0]) > 120:
                desc += "…"

            effect_id = a.effect
            alerts.append({
                "header":      header.title(),
                "description": desc,
                "effect":      _EFFECT_LABEL.get(effect_id, ""),
                "icon":        _EFFECT_ICON.get(effect_id, "ℹ️"),
            })
            if len(alerts) >= max_alerts:
                break

        return alerts

    except Exception as exc:
        print(f"  [warn] BC Transit alerts fetch failed: {exc}", file=sys.stderr)
        return []
