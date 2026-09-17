#!/bin/bash
# Dedicated automation Chrome for jev-ultrafast. Separate profile + CDP port so it
# never attaches to Austin's real browser. Pass --windowed to see it.
cd "$(dirname "$0")"
mode=--headless=new; [ "$1" = "--windowed" ] && mode=
if curl -s http://127.0.0.1:9333/json/version >/dev/null; then echo "already up on :9333"; exit 0; fi
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9333 --user-data-dir="$PWD/chrome-profile" \
  --no-first-run --no-default-browser-check $mode about:blank >chrome.log 2>&1 &
sleep 2; curl -s http://127.0.0.1:9333/json/version | head -2
