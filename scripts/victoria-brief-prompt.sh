#!/bin/bash
# Victoria Brief — popup prompt. Shown by launchd every few hours.

osascript << 'APPLESCRIPT'
try
    set theDialog to display dialog "Ready to generate & publish?" buttons {"Skip", "Launch Brief"} default button "Launch Brief" with title "☀️ Victoria Brief" giving up after 900
    if gave up of theDialog then return
    if button returned of theDialog is not "Launch Brief" then return

    tell application "Terminal"
        activate
        set w to do script "bash '/Users/myerman/Library/Scripts/victoria-brief-run.sh'; exit"
        delay 0.3
        tell front window
            set number of columns to 56
            set number of rows to 22
        end tell
    end tell
on error
    return
end try
APPLESCRIPT
