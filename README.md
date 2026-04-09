# Victoria Morning Brief

A daily email digest of Victoria BC / Vancouver Island news, sent each morning via GitHub Actions. Topics covered: tech & startups, jobs, cultural events, First Nations news, BC legislature, arts funding, UVic/Camosun, BC Ferries, and real estate.

Powered by RSS feeds + DuckDuckGo search + the Claude API.

---

## How it works

1. **RSS feeds** (`feeds.yaml`) are fetched and filtered to the last 24 hours
2. **Supplemental web searches** (DuckDuckGo) fill in categories without RSS coverage
3. **Stock prices** are pulled from Yahoo Finance for Victoria-area public companies
4. **Claude** (`claude-sonnet-4-20250514`) deduplicates, categorizes, and writes the digest as Markdown
5. The digest is **emailed** via SMTP as both plain text and styled HTML

---

## Setup

### 1. Clone the repo

```bash
git clone git@github.com:YOUR_USERNAME/victoria-brief.git
cd victoria-brief
```

### 2. Install dependencies (local testing)

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

For local testing, export these in your shell:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export EMAIL_SMTP_HOST="smtp.gmail.com"
export EMAIL_SMTP_PORT="587"
export EMAIL_SMTP_USER="you@gmail.com"
export EMAIL_SMTP_PASSWORD="your-app-password"  # see Gmail note below
export EMAIL_FROM="you@gmail.com"
export EMAIL_TO="you@gmail.com"
```

### 4. Run locally

```bash
python digest.py
```

---

## GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret** and add each of the following:

| Secret name | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (starts with `sk-ant-`) |
| `EMAIL_SMTP_HOST` | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `EMAIL_SMTP_PORT` | SMTP port — use `587` for TLS (recommended) |
| `EMAIL_SMTP_USER` | Your SMTP login (usually your email address) |
| `EMAIL_SMTP_PASSWORD` | Your SMTP password or app password |
| `EMAIL_FROM` | The From: address on the email |
| `EMAIL_TO` | Where to deliver the digest |

---

## Gmail setup

Gmail requires an **App Password** (not your regular account password) when using SMTP with 2FA enabled:

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Create a new app password (name it "victoria-brief" or similar)
3. Use that 16-character password as `EMAIL_SMTP_PASSWORD`

---

## Schedule

The workflow runs daily at **14:00 UTC** (6 AM PST / 7 AM PDT). To change the time, edit `.github/workflows/morning-digest.yml`:

```yaml
- cron: "0 14 * * *"   # 14:00 UTC = 6 AM PST
```

You can also trigger it manually from the **Actions** tab → **Victoria Morning Brief** → **Run workflow**.

---

## Customizing feeds

Edit `feeds.yaml` to add, remove, or adjust RSS feeds and the stock ticker list. No Python required — it's plain YAML.

```yaml
feeds:
  tech_startups:
    - https://example.com/feed/
  ...

stocks:
  - CMH.TO
  - WELL.TO
```

---

## Project structure

```
victoria-brief/
  digest.py                        # Main script
  feeds.yaml                       # RSS feeds, stock tickers, search queries
  requirements.txt                 # Python dependencies
  .github/
    workflows/
      morning-digest.yml           # GitHub Actions cron schedule
  README.md
```
