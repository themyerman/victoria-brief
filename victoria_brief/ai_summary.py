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

    prompt = f"""Today is {today}. You are writing a morning news brief for someone who lives in Victoria, BC, Canada.

Based on these top stories from today's news, write a single paragraph of 2-3 conversational sentences summarizing what's happening. Be warm and direct — like a friend telling you what's in the news over coffee. Don't list the stories one by one; weave them together naturally.

When you reference a specific story, use a markdown link: [linked text](url). Use the URLs provided. Link the most natural phrase — not the full headline, just the key words.

Today's top stories:
{stories_text}

Write only the paragraph, no preamble, using markdown links."""

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
                "max_tokens": 180,
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
