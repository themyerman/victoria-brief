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
