#!/bin/bash
# Victoria Brief — progress runner. Opened in a Terminal window when user clicks "Launch Brief".

REPO="/Users/myerman/Desktop/code/victoria-brief"
BRIEF="$REPO/index.html"
ENV="$HOME/.victoria-brief.env"
PY="/Users/myerman/Library/Python/3.9/bin/victoria-brief"

# ── Terminal formatting (graceful fallback if no $TERM) ───────────────────────
if [ -n "$TERM" ] && tput bold 2>/dev/null; then
  BOLD=$(tput bold); RESET=$(tput sgr0)
  GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3)
  RED=$(tput setaf 1); BLUE=$(tput setaf 4); DIM=$(tput dim)
else
  BOLD=""; RESET=""; GREEN=""; YELLOW=""; RED=""; BLUE=""; DIM=""
fi

clear 2>/dev/null || true
echo ""
echo "  ${BOLD}☀️  Victoria Brief${RESET}"
echo "  ${DIM}$(date '+%A, %B %-d at %-I:%M %p')${RESET}"
echo "  ──────────────────────────────────"
echo ""

step()  { echo "  ${BLUE}▸${RESET}  $1"; }
ok()    { echo "  ${GREEN}✓${RESET}  ${BOLD}$1${RESET}"; }
warn()  { echo "  ${YELLOW}⚠${RESET}  $1"; }
fail()  { echo "  ${RED}✗${RESET}  ${BOLD}$1${RESET}"; echo ""; exit 1; }

# ── Load credentials ──────────────────────────────────────────────────────────
[ -f "$ENV" ] && source "$ENV"
[ -z "$FTP_PASS" ] && fail "Missing credentials ($ENV not found)"

# ── Network ───────────────────────────────────────────────────────────────────
step "Checking network..."
if ! curl -sf --max-time 6 https://google.com > /dev/null 2>&1; then
    fail "No network connection"
fi
ok "Network ready"

# ── Generate ──────────────────────────────────────────────────────────────────
step "Generating brief  (takes ~30s)..."
if (cd "$REPO" && "$PY" --file "$BRIEF") > /tmp/vb-run.log 2>&1; then
    ok "Brief generated"
else
    warn "Generator output:"
    tail -5 /tmp/vb-run.log | sed 's/^/     /'
    fail "Brief generation failed"
fi

# ── Upload ────────────────────────────────────────────────────────────────────
FTP_URL="ftp://ftp.myerman.art/public_html/victoria-brief/index.html"
FTP_USER="ftp2@myerman.art:$FTP_PASS"
UPLOADED=0
for attempt in 1 2 3; do
    step "Uploading to myerman.art  (attempt $attempt/3)..."
    if curl -s --ftp-ssl --insecure -T "$BRIEF" "$FTP_URL" \
            --user "$FTP_USER" > /dev/null 2>&1; then
        ok "Published → myerman.art/victoria-brief/"
        UPLOADED=1
        break
    fi
    warn "Upload attempt $attempt failed"
    [ $attempt -lt 3 ] && sleep 20
done

[ $UPLOADED -eq 0 ] && fail "FTP failed after 3 attempts — brief saved locally only"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ──────────────────────────────────"
echo "  ${GREEN}${BOLD}  All done!${RESET}  myerman.art/victoria-brief/"
echo ""
echo "  ${DIM}Closing in 12 seconds...${RESET}"
sleep 12
