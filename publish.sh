#!/bin/bash
# Generates the daily brief and publishes it to GitHub Pages.

set -e

REPO="/Users/myerman/Desktop/code/victoria-brief"
BRIEF="$REPO/index.html"
LOG="$HOME/Library/Logs/victoria-brief.log"

echo "--- $(date) ---" >> "$LOG"

cd "$REPO"

# Generate
/Users/myerman/Library/Python/3.9/bin/victoria-brief --file "$BRIEF" >> "$LOG" 2>&1

# Commit and push
git add index.html
git commit -m "Daily brief $(date +'%Y-%m-%d')" >> "$LOG" 2>&1
git push origin main >> "$LOG" 2>&1

echo "Published." >> "$LOG"
