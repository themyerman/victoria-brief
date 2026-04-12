from __future__ import annotations

"""
Whale & orca sightings near Victoria BC / Salish Sea.

Uses two sources (first that returns results wins):
  1. iNaturalist API — free, no auth, returns verified citizen-science sightings
     of whales/orcas within ~150 km of Victoria with photos and dates.
  2. DuckDuckGo fallback (original approach) if iNat returns nothing.
"""

import sys
from datetime import datetime, timezone


# iNaturalist taxon IDs
_TAXON_CETACEA = 152871      # Infraorder Cetacea (all whales, dolphins, porpoises)
_INATURALIST_API = "https://api.inaturalist.org/v1/observations"

# Victoria, BC coordinates
_LAT = 48.43
_LNG = -123.37
_RADIUS_KM = 150   # covers entire Salish Sea


def _fmt_date(date_str: str) -> str:
    """Format iNat observed_on date string (YYYY-MM-DD) to 'Apr 11'."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %-d")
    except Exception:
        return date_str


def fetch_whale_sightings(max_results: int = 4) -> list[dict]:
    """
    Fetch recent whale / orca sightings near Victoria BC.
    Returns list of dicts: title, summary, link, published (None or time_t).
    """
    results = _fetch_from_inaturalist(max_results)
    if not results:
        results = _fetch_from_ddgs(max_results)
    return results


def _fetch_from_inaturalist(max_results: int) -> list[dict]:
    """Query iNaturalist observations API for recent Cetacean sightings."""
    try:
        import requests
        params = {
            "taxon_id":   _TAXON_CETACEA,
            "lat":        _LAT,
            "lng":        _LNG,
            "radius":     _RADIUS_KM,
            "per_page":   max_results * 2,
            "order_by":   "observed_on",
            "order":      "desc",
            "quality_grade": "research,needs_id",
            "photos":     "true",
        }
        r = requests.get(
            _INATURALIST_API,
            params=params,
            headers={"User-Agent": "victoria-brief/1.0 (contact: myerman@gmail.com)"},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"  [warn] iNaturalist whale fetch failed: {exc}", file=sys.stderr)
        return []

    results = []
    seen: set[str] = set()
    for obs in data.get("results", []):
        obs_id  = obs.get("id")
        species = (obs.get("taxon") or {}).get("preferred_common_name", "") or \
                  (obs.get("taxon") or {}).get("name", "Unknown species")
        species = species.title()
        date_str = obs.get("observed_on", "")
        place    = obs.get("place_guess", "Salish Sea") or "Salish Sea"
        link     = f"https://www.inaturalist.org/observations/{obs_id}"
        if link in seen:
            continue
        seen.add(link)

        title   = f"{species} — {place}"
        summary = f"Observed {_fmt_date(date_str)}"
        if obs.get("description"):
            summary += f". {obs['description'][:100]}"

        # Convert observed_on to a time tuple for _rel_time() in render.py
        published = None
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                published = dt.timetuple()
            except Exception:
                pass

        results.append({
            "title":     title,
            "summary":   summary,
            "link":      link,
            "published": published,
        })
        if len(results) >= max_results:
            break

    return results


def _fetch_from_ddgs(max_results: int) -> list[dict]:
    """Fallback: DuckDuckGo search for whale sighting reports."""
    try:
        from ddgs import DDGS
        query = (
            "orca OR whale sighting Victoria BC OR Salish Sea 2026 "
            "site:whalemuseum.org OR site:orcalab.org OR site:dfo-mpo.gc.ca"
        )
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results * 3)

        results = []
        seen: set[str] = set()
        for r in (raw or []):
            href  = r.get("href", "")
            title = r.get("title", "").strip()
            body  = r.get("body", "")[:150].strip()
            if not href or not title or href in seen:
                continue
            seen.add(href)
            results.append({
                "title":     title,
                "summary":   body,
                "link":      href,
                "published": None,
            })
            if len(results) >= max_results:
                break
        return results

    except Exception as exc:
        print(f"  [warn] Whale DDG fallback failed: {exc}", file=sys.stderr)
        return []
