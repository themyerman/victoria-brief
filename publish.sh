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

# iMessage notifications
MSG="Good morning! Today's Victoria Brief is ready: https://myerman.art/victoria-brief/"
for NUMBER in "+17202928866" "+17204591466"; do
  osascript << APPLESCRIPT >> "$LOG" 2>&1
tell application "Messages"
  set targetService to 1st service whose service type = iMessage
  set targetBuddy to participant "$NUMBER" of targetService
  send "$MSG" to targetBuddy
end tell
APPLESCRIPT
  echo "  iMessage sent to $NUMBER" >> "$LOG"
done
