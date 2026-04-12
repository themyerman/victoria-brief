# Victoria Morning Brief

A daily HTML digest of Victoria BC / Vancouver Island news, weather, tides, ferries, trails, and more. Generates a single self-contained HTML file and FTPs it to myerman.art/victoria-brief/.

---

## What's in it

- **Weather** — Environment Canada 7-day forecast, sunrise/sunset, AQHI air quality
- **Marine forecast** — Juan de Fuca Strait wind/weather (EC GeoMet API), active warnings
- **BC Ferries** — Live sailing status and capacity for Swartz Bay ↔ Tsawwassen
- **BC Transit** — Active service alerts
- **Trails & Cycling** — Trail conditions derived from precipitation, featured trail of the day, Eco-Counter bike/pedestrian counts from 43 CRD trail counters
- **Tides** — Victoria Harbour tide events (Canadian Hydrographic Service)
- **Whale sightings** — Recent cetacean observations near Victoria from iNaturalist
- **Wildfire** — Active fires on Vancouver Island (BC Wildfire Service)
- **News grid** — RSS feeds across Local, BC Politics, First Nations, Arts & Culture, Real Estate, Tech, and more
- **Events** — Local Victoria event listings (7-day window)
- **Photos** — Recent Flickr photos tagged with Victoria/Vancouver Island

No LLM required. NLP pipeline uses NLTK + scikit-learn locally.

---

## Quickstart

```bash
git clone git@github.com:myerman-art/victoria-brief.git
cd victoria-brief
pip install -e .
victoria-brief --file ~/Desktop
```

Output: `~/Desktop/victoria-daily-brief.html`

On first run NLTK downloads ~3 MB of data (stopwords, punkt, VADER) and caches it permanently.

---

## Running it

```bash
# Write to Desktop
victoria-brief --file

# Write to a specific path or directory
victoria-brief --file ~/Documents/briefs/

# Write to a specific file (used by the publish script)
victoria-brief --file /path/to/index.html
```

---

## Publishing to myerman.art

The publish script generates the brief and FTPs it to the live site.

Credentials go in `~/.victoria-brief.env`:

```bash
FTP_PASS=yourpassword
```

Then run:

```bash
bash ~/Library/Scripts/victoria-brief-run.sh
```

The macOS popup trigger (`victoria-brief-prompt.sh`) fires at 8am via launchd and opens a Terminal window with a "Launch Brief" button. Scripts are versioned in `scripts/` in this repo.

---

## Configuration

Edit `feeds.yaml` — no Python required. Add or remove RSS feeds, adjust weights, set lookback windows.

```yaml
sources:
  - name: "My Feed"
    url: "https://example.com/feed/"
    hours: 24        # how far back to look
    weight: 1.2      # baseline priority multiplier
    category: "Local"
```

Categories control which grid column a source appears in. Special categories:
- `"Events"` — shown in a full-width section below the grid (7-day lookback)

---

## Project structure

```
victoria-brief/
  feeds.yaml                    # All feed config
  pyproject.toml
  scripts/                      # macOS launch scripts (mirrored to ~/Library/Scripts/)
    victoria-brief-run.sh       # Generate + FTP publish
    victoria-brief-prompt.sh    # macOS popup dialog trigger
  victoria_brief/
    cli.py                      # Orchestrator
    config.py                   # Loads feeds.yaml
    sources.py                  # RSS fetching
    nlp.py                      # Dedup, scoring, summarization, NER
    render.py                   # HTML generation
    weather.py                  # Environment Canada forecast + AQHI
    marine.py                   # EC Juan de Fuca marine forecast
    tides.py                    # Canadian Hydrographic Service
    ferries.py                  # BC Ferries API
    transit.py                  # BC Transit GTFS-RT alerts
    trails.py                   # Trail conditions from precipitation data
    bikecount.py                # Eco-Counter CRD trail usage counts
    whale.py                    # iNaturalist cetacean sightings
    wildfire.py                 # BC Wildfire Service
    photos.py                   # Flickr photo feed
    thumbnails.py               # OG image extraction for news cards
    mailer.py                   # (unused — retained for reference)
```
