#!/bin/bash
# Victoria Brief — daily generation and publish
# Bulletproofed: timestamped logging, network wait, FTP retry, macOS notifications

REPO="/Users/myerman/Desktop/code/victoria-brief"
BRIEF="$REPO/index.html"
LOG="$HOME/Library/Logs/victoria-brief.log"
ENV="$HOME/.victoria-brief.env"

# Pass --no-sms to skip iMessage notifications (used for afternoon/evening runs)
SEND_SMS=1
for arg in "$@"; do
  [ "$arg" = "--no-sms" ] && SEND_SMS=0
done

# ── Helpers ───────────────────────────────────────────────────────────────────

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*" >> "$LOG"; }

notify() {
  osascript -e "display notification \"$1\" with title \"Victoria Brief\"" 2>/dev/null || true
}

# Rotate log if > 2 MB
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 2097152 ]; then
  mv "$LOG" "${LOG%.log}-$(date +%Y%m%d).log"
fi

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Victoria Brief starting"

# ── Load credentials ──────────────────────────────────────────────────────────

if [ -f "$ENV" ]; then
  source "$ENV"
else
  log "ERROR: $ENV not found"
  notify "⚠️ Config missing — brief not generated"
  exit 1
fi

# ── Wait for network (up to 3 minutes) ───────────────────────────────────────

log "Checking network..."
NETWORK_OK=0
for i in $(seq 1 18); do
  if curl -sf --max-time 5 https://google.com > /dev/null 2>&1; then
    log "Network ready (attempt $i)"
    NETWORK_OK=1
    break
  fi
  log "  No network yet, waiting 10s... ($i/18)"
  sleep 10
done

if [ $NETWORK_OK -eq 0 ]; then
  log "ERROR: No network after 3 minutes — aborting"
  notify "⚠️ No network — brief skipped today"
  exit 1
fi

# ── Generate brief ────────────────────────────────────────────────────────────

cd "$REPO"
log "Generating brief..."

if /Users/myerman/Library/Python/3.9/bin/victoria-brief --file "$BRIEF" >> "$LOG" 2>&1; then
  log "Brief generated OK"
else
  log "ERROR: Brief generation failed (exit code $?)"
  notify "⚠️ Generation failed — check ~/Library/Logs/victoria-brief.log"
  exit 1
fi

# ── Upload via FTP (3 attempts with 30s backoff) ──────────────────────────────

FTP_URL="ftp://ftp.myerman.art/public_html/victoria-brief/index.html"
FTP_USER="ftp2@myerman.art:$FTP_PASS"
UPLOADED=0

for attempt in 1 2 3; do
  log "FTP upload attempt $attempt/3..."
  if curl -s --ftp-ssl --insecure --no-sessionid -T "$BRIEF" \
      "$FTP_URL" --user "$FTP_USER" >> "$LOG" 2>&1; then
    log "Upload succeeded (attempt $attempt)"
    UPLOADED=1
    break
  fi
  log "  Upload failed"
  [ $attempt -lt 3 ] && { log "  Waiting 30s before retry..."; sleep 30; }
done

if [ $UPLOADED -eq 0 ]; then
  log "WARN: All 3 FTP attempts failed — brief saved locally only"
  notify "⚠️ FTP failed after 3 tries — brief saved locally, upload manually"
  exit 0  # don't send iMessages if not published
fi

# ── iMessage notifications (8:30am run only) ─────────────────────────────────

if [ $SEND_SMS -eq 1 ]; then
  MSG="Good morning! Today's Victoria Brief is ready: https://myerman.art/victoria-brief/"
  for NUMBER in "+17202928866" "+17204591466"; do
    osascript << APPLESCRIPT >> "$LOG" 2>&1
tell application "Messages"
  set targetService to 1st service whose service type = iMessage
  set targetBuddy to participant "$NUMBER" of targetService
  send "$MSG" to targetBuddy
end tell
APPLESCRIPT
    log "  iMessage sent to $NUMBER"
  done
else
  log "SMS skipped (--no-sms flag)"
fi

notify "✅ Brief published — https://myerman.art/victoria-brief/"
log "Done."
