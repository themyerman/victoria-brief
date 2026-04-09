# Victoria Morning Brief

A daily HTML digest of Victoria BC / Vancouver Island news. Runs locally or on a schedule via GitHub Actions.

Topics: tech & startups, jobs, cultural events, First Nations news, BC legislature, arts funding, UVic/Camosun, BC Ferries, and real estate.

No LLM required. Entirely local NLP via NLTK + scikit-learn.

---

## How it works

1. **RSS feeds** (`feeds.yaml`) are fetched and filtered to the last 24 hours
2. **Supplemental web searches** (DuckDuckGo, no API key) fill in categories without RSS coverage
3. **Stock prices** are pulled from Yahoo Finance for Victoria-area public companies
4. **NLP pipeline** runs locally:
   - Deduplicates near-identical stories across feeds (TF-IDF cosine similarity)
   - Extracts summaries from each item (frequency-based sentence scoring)
   - Pulls top keywords across the day's stories
   - Runs VADER sentiment analysis and renders a tone bar
5. Output is a **styled HTML file** on your Desktop, or sent via **SMTP email**

---

## Quickstart (local)

```bash
git clone git@github.com:YOUR_USERNAME/victoria-brief.git
cd victoria-brief
pip install -e .
python main.py --file
```

That's it — no API keys needed. On first run NLTK will download ~3MB of data (stopwords, punkt tokenizer, VADER lexicon) and cache it permanently.

Output: `~/Desktop/victoria-brief-YYYY-MM-DD.html`

---

## Output options

```bash
# Write HTML to your Desktop (default location)
python main.py --file

# Write to a specific directory or file
python main.py --file ~/Documents/briefs/

# Send via email instead
python main.py --email
```

`--file` and `--email` are mutually exclusive.

---

## Email setup

Only needed if you use `--email`. Set these environment variables:

```bash
export EMAIL_SMTP_HOST="smtp.gmail.com"
export EMAIL_SMTP_PORT="587"
export EMAIL_SMTP_USER="you@gmail.com"
export EMAIL_SMTP_PASSWORD="your-app-password"
export EMAIL_FROM="you@gmail.com"
export EMAIL_TO="you@gmail.com"
```

Add them to `~/.zshrc` to make permanent.

**Gmail:** requires an App Password (not your account password) when 2FA is enabled. Create one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

---

## GitHub Actions (scheduled email)

The workflow runs daily at **14:00 UTC** (6 AM PST / 7 AM PDT).

Add these as repo Secrets under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `EMAIL_SMTP_HOST` | e.g. `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | `587` |
| `EMAIL_SMTP_USER` | Your SMTP login |
| `EMAIL_SMTP_PASSWORD` | Your SMTP password or app password |
| `EMAIL_FROM` | From address |
| `EMAIL_TO` | Delivery address |

To change the schedule, edit `.github/workflows/morning-digest.yml`:

```yaml
- cron: "0 14 * * *"   # 14:00 UTC = 6 AM PST
```

You can also trigger manually from the **Actions** tab → **Victoria Morning Brief** → **Run workflow**.

---

## Customizing feeds

Edit `feeds.yaml` — no Python required. Add/remove RSS URLs, stock tickers, or search queries:

```yaml
feeds:
  tech_startups:
    - https://example.com/feed/

stocks:
  - CMH.TO

web_search_queries:
  first_nations:
    - "Songhees Nation news announcement"
```

---

## Project structure

```
victoria-brief/
  main.py                       # Entry point (3 lines)
  feeds.yaml                    # All config: feeds, stocks, search queries
  pyproject.toml                # pip install -e .
  .github/
    workflows/
      morning-digest.yml        # GitHub Actions cron
  victoria_brief/
    cli.py                      # Orchestrator + argument parsing
    config.py                   # Loads feeds.yaml
    rss.py                      # RSS fetching
    search.py                   # DuckDuckGo supplemental search
    stocks.py                   # yfinance stock prices
    nlp.py                      # Dedup, summarization, keywords, sentiment
    render.py                   # HTML generation
    mailer.py                   # SMTP delivery
```
