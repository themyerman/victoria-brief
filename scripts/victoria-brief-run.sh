#!/bin/bash
# Victoria Brief — progress runner. Opened in a Terminal window when user clicks "Launch Brief".

REPO="/Users/myerman/Desktop/code/victoria-brief"
BRIEF="$REPO/index.html"
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

# ── Publish via git push → GitHub Pages ──────────────────────────────────────
step "Publishing to GitHub Pages..."
cd "$REPO"
git add index.html
if git diff --staged --quiet; then
    ok "No changes — already up to date"
else
    git commit -m "brief: $(date '+%Y-%m-%d')" > /dev/null 2>&1
    if git push origin main > /tmp/vb-push.log 2>&1; then
        ok "Published → themyerman.github.io/victoria-brief/"
    else
        warn "Push output:"
        tail -3 /tmp/vb-push.log | sed 's/^/     /'
        fail "Git push failed"
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ──────────────────────────────────"
echo "  ${GREEN}${BOLD}  All done!${RESET}  themyerman.github.io/victoria-brief/"
echo ""
echo "  ${DIM}Closing in 12 seconds...${RESET}"
sleep 12
