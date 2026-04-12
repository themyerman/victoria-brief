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

    # Collect top stories across all non-events sources, sorted by score
    all_stories = []
    for src_name, items in sources.items():
        cat = categories.get(src_name, "Other")
        for item in items[:3]:
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

    # Sort by score, cap at 50 to stay within token limits
    all_stories.sort(key=lambda x: x["score"], reverse=True)
    all_stories = all_stories[:50]

    lines = []
    for i, s in enumerate(all_stories, 1):
        lines.append(f"{i}. [{s['title']}]({s['link']}) — {s['source']} ({s['category']})")
    stories_text = "\n".join(lines)

    # Seed with known category names so output matches our headers
    known_cats = [
        "BC News", "Victoria & Island", "Indigenous",
        "Jobs & Economy", "Arts & Culture", "Education",
        "Housing & Transit", "Other"
    ]

    prompt = f"""Today is {today}. You are organizing a morning news brief for Victoria, BC.

Group these stories into news categories and write a 2-3 sentence summary for each category that has enough stories.

Rules:
- Use these category names where they fit: {', '.join(known_cats)}
- You may create a new category name if stories clearly don't fit any above
- Skip categories with fewer than 2 relevant stories
- Every story you mention in a summary MUST use an inline markdown link: [words](url)
- Link natural phrases mid-sentence — NOT "read more" or "click here" at end
- Deduplicate: if two stories cover the same event, mention it once
- Be concise and direct — no fluff

Respond with valid JSON only, in this exact format:
{{
  "categories": [
    {{"name": "Victoria & Island", "icon": "🏙️", "summary": "...inline [linked text](url) here..."}},
    {{"name": "BC News", "icon": "🏔️", "summary": "..."}}
  ]
}}

Stories:
{stories_text}"""

    try:
        r = requests.post(
            _API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json={
                "model":           _MODEL,
                "messages":        [{"role": "user", "content": prompt}],
                "max_tokens":      1200,
                "temperature":     0.4,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        r.raise_for_status()
        data = json.loads(r.json()["choices"][0]["message"]["content"])
        return data.get("categories", [])
    except Exception as exc:
        print(f"  [warn] AI news grid failed: {exc}", file=sys.stderr)
        return []


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

    prompt = f"""Today is {today}. Write a 2-3 sentence morning news paragraph for someone in Victoria, BC.

Rules:
- Every story you mention MUST be hyperlinked using markdown: [words](url)
- Link natural phrases mid-sentence — NOT "click here" or "read more" at the end
- Example of correct style: "The city is moving forward with [new zoning changes](https://example.com) while [BC Ferries warns of delays](https://example.com) this weekend."
- Weave the stories together naturally, do not list them
- Write only the paragraph, nothing else

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
                "max_tokens": 350,
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
