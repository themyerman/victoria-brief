# Victoria Brief — Claude Code Guidelines

## What this project is
A daily morning news digest for Victoria, BC. Fetches RSS feeds, runs NLP,
calls GitHub Models (gpt-4o-mini) for AI summaries, and publishes a static
HTML page to GitHub Pages. Runs automatically via GitHub Actions at 6 AM PDT.

## Architecture
- `victoria_brief/sources.py` — RSS + DDG search fetching
- `victoria_brief/nlp.py` — deduplication, scoring, major story detection
- `victoria_brief/ai_summary.py` — GitHub Models API calls (briefing + news grid)
- `victoria_brief/render.py` — HTML generation, all CSS inline
- `victoria_brief/cli.py` — entry point, orchestrates everything
- `feeds.yaml` — all news sources, categories, weights
- `.github/workflows/morning-digest.yml` — 6 AM publish + email workflow

## AI summary rules (hard-won)

### Always forbid training-data hallucination
Every AI prompt must include:
> "ONLY use facts from the provided stories — do not add background, context,
> or knowledge from your training data."

Without this the model will confidently state stale facts (wrong PM, old events).

### Use JSON mode for structured output
All calls that return structured data use `"response_format": {"type": "json_object"}`.
Never rely on the model to return clean JSON without it.

### Single call beats two calls for prose+structure
The news grid asks for both `stories` (headline+url) AND `summary` prose in one
JSON object. When the model writes the summary while the URLs are in the same
object, it reliably links them. Splitting into two calls causes name-mismatch
failures and link-dropping.

### Always have a prose fallback
If `summary` is empty, the renderer falls back to linked headlines joined with
em-dashes. Never show a category with no content.

### Model choice
Use `gpt-4o-mini`. The `o1` family doesn't support `temperature` and hits rate
limits immediately (10 req/day). `gpt-4o` works but burns the daily quota fast.

## Data pipeline rules

### Drop undated RSS items
`sources.py` drops any RSS entry with no `published_parsed` or `updated_parsed`.
Undated items bypass the 26-hour cutoff and can be years old.

### Black Press feeds recycle old articles with fresh pubDates
The Black Press group (Saanich News, Oak Bay News, Goldstream Gazette, Peninsula
News Review, Sooke News Mirror, Nanaimo Bulletin, Victoria News) sometimes
republishes old articles stamped with today's `pubDate`. The date check passes
but the article is years old. Fix: `_url_year_is_stale()` in `sources.py` checks
the URL path for embedded years (e.g. `/2021/`) and drops anything more than
1 year old regardless of `pubDate`.

### Flickr photos: 15-day recency filter
`photos.py` filters Flickr entries older than 15 days using `published_parsed`.
Without this, Flickr feeds can surface photos from years ago.

### AI sees all sources, flat grid sees 6
`cli.py` splits news sources into two sets:
- `news_sources` — all non-events sources (fed to AI grid, no limit)
- `top` — top 6 by gravity score (used for major stories + fallback flat grid)
Events bypass both limits via `BYPASS_CATS = {"Events"}`.

### Token budget
- `generate_briefing`: 500 max_tokens
- `generate_news_grid`: 2500 max_tokens, sends up to 80 stories
- Actual prompt is ~4,700 tokens against 128k context — loads of headroom
- GitHub Models free tier: ~150 req/day shared across all repos
- Each brief run uses 2 API calls (briefing + news grid)

### Current sources (29 total, ~150 items/day)
**Victoria & Island:** CHEK, Times Colonist, Victoria News, Victoria Buzz,
Saanich News, Oak Bay News, Goldstream Gazette, Peninsula News Review,
Sooke News Mirror, Nanaimo Bulletin, Douglas Magazine, TC Opinion
**BC News:** CBC BC, BC Government News, Global News BC
**Indigenous:** APTN, CBC Indigenous, First Nations search
**Jobs & Economy:** Business Examiner VI, TC Business, BC Tech search, VI Jobs search
**Arts & Culture:** BC Arts Council search
**Events:** Victoria Buzz Events, TC Entertainment, Indigenous Events search
**Education:** UVic News
**Housing & Transit:** BC Ferries search, Victoria Housing search

## Publishing

### GitHub Pages
`index.html` is committed to `main` branch root and served via GitHub Pages.
The Actions bot commits it after each run. Always `git pull --rebase` before
pushing local changes.

### Workflow schedule (UTC)
```
0 13 * * *   # 6:00 AM PDT — generate & publish
```
Email fires after build succeeds (`needs: build`, `needs.build.result == 'success'`).
Do NOT use separate schedule triggers for build + email — they run in separate
workflow contexts and can't depend on each other.

### Required GitHub secrets
```
SMTP_SERVER     smtp.gmail.com
SMTP_PORT       465
SMTP_USERNAME   sender Gmail address
SMTP_PASSWORD   Gmail app password (not account password)
NOTIFY_EMAILS   comma-separated recipient list
BRIEF_URL       public URL of the page
```

## Things we tried that didn't work
- **SMS via AppleScript** — removed; fragile and Mac-only
- **FTP publishing** — replaced with git push to GitHub Pages
- **Two-call AI grid** (categorize then prose separately) — name mismatches between
  calls caused most categories to fall back to em-dash lists
- **o1 model** — 400 error (no temperature support), immediate 429 rate limit
- **Separate cron triggers for build + email** — email fired without build running
  because jobs in separate workflow runs can't use `needs:`
