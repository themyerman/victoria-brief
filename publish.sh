#!/bin/bash
# Generates the daily brief and uploads it to myerman.art/victoria-brief/

set -e

REPO="/Users/myerman/Desktop/code/victoria-brief"
BRIEF="$REPO/index.html"
LOG="$HOME/Library/Logs/victoria-brief.log"
ENV="$HOME/.victoria-brief.env"

echo "--- $(date) ---" >> "$LOG"

# Load credentials
if [ -f "$ENV" ]; then
  source "$ENV"
else
  echo "ERROR: $ENV not found" >> "$LOG"
  exit 1
fi

cd "$REPO"

# Generate
echo "Generating brief..." >> "$LOG"
/Users/myerman/Library/Python/3.9/bin/victoria-brief --file "$BRIEF" >> "$LOG" 2>&1

# Upload via FTP
echo "Uploading..." >> "$LOG"
curl -s --ftp-ssl --insecure --no-sessionid -T "$BRIEF" \
  "ftp://ftp.myerman.art/public_html/victoria-brief/index.html" \
  --user "ftp2@myerman.art:$FTP_PASS" >> "$LOG" 2>&1

echo "Done. Published to myerman.art/victoria-brief/" >> "$LOG"
