from __future__ import annotations

"""
AI-generated morning briefing via GitHub Models.

Sends today's major story headlines to a GitHub-hosted model and gets back
a 2-3 sentence conversational summary to display at the top of the brief.

Auth: reads GITHUB_TOKEN from environment (auto-available in GitHub Actions;
add to ~/.victoria-brief.env for local use).

Falls back silently to "" if the token is missing or the API call fails.
"""

import os
import sys
import json
from datetime import datetime

import requests

_API_URL = "https://models.inference.ai.azure.com/chat/completions"
_MODEL   = "gpt-4o-mini"
_TIMEOUT = 20


def generate_events_summary(events: list[dict]) -> str:
    """
    Given a list of upcoming Victoria events (title, link, summary),
    return a 2-3 sentence conversational paragraph with inline markdown links.
    Returns "" on failure or missing token.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or not events:
        return ""

    today = datetime.now().strftime("%A, %B %-d, %Y")

    lines = []
    for i, e in enumerate(events[:10], 1):
        title   = e.get("title", "")
        link    = e.get("link", "")
        snippet = (e.get("summary", "") or "")[:80].strip()
        line    = f"{i}. {title}"
        if link:
            line += f" — {link}"
        if snippet:
            line += f" | {snippet}"
        lines.append(line)

    events_text = "\n".join(lines)

    prompt = f"""Today is {today}. Write a 2-3 sentence paragraph highlighting what's happening in Victoria, BC this week.

Rules:
- Every event you mention MUST be hyperlinked inline using markdown: [words](url)
- Link natural phrases mid-sentence, NOT "click here" or "read more" at the end
- Example: "This week Victoria is hosting [the annual symphony gala](https://url) and a free [outdoor film screening](https://url) at Beacon Hill Park."
- Be warm and inviting — like a local friend telling you what not to miss
- Write only the paragraph, nothing else

Upcoming events (use these exact URLs):
{events_text}"""

    try:
        r = requests.post(
            _API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       _MODEL,
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  300,
                "temperature": 0.6,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"  [warn] AI events summary failed: {exc}", file=sys.stderr)
        return ""


def generate_news_grid(
    sources: dict[str, list],
    categories: dict[str, str],
) -> list[dict]:
    """
    Takes all processed news sources, sends top stories to the AI, and gets
    back a list of topic-grouped categories with inline-linked summaries.

    Returns a list of dicts: {name, icon, summary}
    Returns [] on failure or missing token.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or not sources:
        return []

    today = datetime.now().strftime("%A, %B %-d, %Y")

    # Collect top stories across all sources, sorted by score
    all_stories = []
    for src_name, items in sources.items():
        cat = categories.get(src_name, "Other")
        for item in items[:5]:  # up to 5 per source
            title = item.get("title", "")
            link  = item.get("link", "")
            if title and link:
                all_stories.append({
                    "title":    title,
                    "link":     link,
                    "source":   src_name,
                    "category": cat,
                    "score":    item.get("_score", 0),
                })

    # Sort by score, cap at 80 to stay within token limits
    all_stories.sort(key=lambda x: x["score"], reverse=True)
    all_stories = all_stories[:80]

    lines = []
    for i, s in enumerate(all_stories, 1):
        lines.append(f"{i}. {s['title']} | url: {s['link']} | source: {s['source']} | category: {s['category']}")
    stories_text = "\n".join(lines)

    # Seed with known category names so output matches our headers
    known_cats = [
        "Victoria & Island", "BC News", "Indigenous",
        "Events & Community", "Arts & Culture", "Jobs & Economy",
        "Housing & Transit", "Education", "Other"
    ]

    # ── Call 1: categorize stories and lock in URLs (JSON mode, reliable) ──────
    cat_prompt = f"""Today is {today}. Organize these Victoria BC news stories into categories.

For each category return the stories as objects with a short headline and the EXACT url from the input.

Rules:
- Use these category names where they fit: {', '.join(known_cats)}
- You may create a new category if stories don't fit any above
- Include all categories with at least 1 story; include all stories per category
- Deduplicate: one entry per event, keep the best one
- Keep headlines concise (under 12 words)
- Copy each url EXACTLY as given — do not change or omit it
- Pick a relevant emoji icon for each category

Respond with valid JSON only:
{{"categories": [{{"name": "Victoria & Island", "icon": "🏙️", "stories": [{{"headline": "...", "url": "https://..."}}]}}]}}

Stories:
{stories_text}"""

    try:
        r1 = requests.post(
            _API_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": _MODEL, "messages": [{"role": "user", "content": cat_prompt}],
                "max_tokens": 2000, "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        r1.raise_for_status()
        structured = json.loads(r1.json()["choices"][0]["message"]["content"]).get("categories", [])
    except Exception as exc:
        print(f"  [warn] AI news grid (categorize) failed: {exc}", file=sys.stderr)
        return []

    if not structured:
        return []

    # ── Call 2: write prose paragraphs using the locked-in URLs ─────────────
    # Build explicit headline→url mapping so the model can't lose a link
    prose_sections = []
    for cat in structured:
        name    = cat.get("name", "")
        stories = cat.get("stories", [])
        if not name or not stories:
            continue
        story_lines = "\n".join(
            f'  - "{s["headline"]}" → {s["url"]}'
            for s in stories if s.get("headline") and s.get("url")
        )
        prose_sections.append(f'{name}:\n{story_lines}')
    prose_input = "\n\n".join(prose_sections)

    prose_prompt = f"""Today is {today}. Write a 2-3 sentence prose paragraph for each news category below about Victoria, BC.

RULES (follow exactly):
- Every story you mention MUST be linked with markdown: [words](url)
- Use the exact URL listed next to each story — no exceptions
- Link natural phrases mid-sentence (e.g. "The [South Island Powwow](url) returns...")
- Do NOT end sentences with "read more" or "click here"
- Write only the paragraphs — no headers, no labels, no extra text

Respond with valid JSON:
{{"categories": [{{"name": "Victoria & Island", "summary": "prose with [inline links](url) here..."}}]}}

Categories and stories (headline → url):
{prose_input}"""

    try:
        r2 = requests.post(
            _API_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": _MODEL, "messages": [{"role": "user", "content": prose_prompt}],
                "max_tokens": 2000, "temperature": 0.6,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        r2.raise_for_status()
        prose_cats = json.loads(r2.json()["choices"][0]["message"]["content"]).get("categories", [])
    except Exception as exc:
        print(f"  [warn] AI news grid (prose) failed: {exc}", file=sys.stderr)
        prose_cats = []

    # Merge prose summaries back onto the structured categories
    prose_by_name = {c["name"]: c.get("summary", "") for c in prose_cats}
    result = []
    for cat in structured:
        name = cat.get("name", "")
        result.append({
            "name":    name,
            "icon":    cat.get("icon", "📰"),
            "summary": prose_by_name.get(name, ""),
            "stories": cat.get("stories", []),  # fallback if prose failed
        })
    return result


def generate_briefing(stories: list[dict]) -> str:
    """
    Given a list of major story dicts (title, summary, sources),
    return a 2-3 sentence morning briefing paragraph.
    Returns "" on failure or missing token.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return ""

    if not stories:
        return ""

    today = datetime.now().strftime("%A, %B %-d, %Y")

    # Build a compact story list for the prompt, including URLs for inline linking
    lines = []
    for i, s in enumerate(stories[:5], 1):
        title   = s.get("title", "")
        link    = s.get("link", "")
        sources = ", ".join(s.get("sources", []))
        snippet = (s.get("summary", "") or "")[:100].strip()
        line = f"{i}. {title}"
        if link:
            line += f" — {link}"
        if sources:
            line += f" ({sources})"
        if snippet:
            line += f" | {snippet}"
        lines.append(line)

    stories_text = "\n".join(lines)

    prompt = f"""Today is {today}. Write a short morning news briefing for someone in Victoria, BC.

Rules:
- Group the stories into themes (e.g. local politics, environment, economy)
- Write one short paragraph (1-3 sentences) per theme, separated by a blank line
- Every story you mention MUST be hyperlinked using markdown: [words](url)
- Link natural phrases mid-sentence — NOT "click here" or "read more" at the end
- Example: "The city is moving forward with [new zoning changes](https://example.com) while [BC Ferries warns of delays](https://example.com) this weekend."
- Write only the paragraphs, nothing else — no headers, no labels

Stories (use these exact URLs):
{stories_text}"""

    try:
        r = requests.post(
            _API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json={
                "model":      _MODEL,
                "messages":   [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.6,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text
    except Exception as exc:
        print(f"  [warn] AI briefing failed: {exc}", file=sys.stderr)
        return ""
