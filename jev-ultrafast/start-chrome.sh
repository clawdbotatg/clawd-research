#!/bin/bash
# Dedicated automation Chrome for jev-ultrafast. Separate profile + CDP port so it
# never attaches to Austin's real browser or another agent's Chrome. --windowed to see it.
# Refuses to start if anything already listens on the port (2026-09-17: 9333 was
# silently taken by another headless Chrome and CDP calls landed in it).
cd "$(dirname "$0")"
PORT=9444
mode=--headless=new; [ "$1" = "--windowed" ] && mode=
if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null; then
  if [ -f chrome.pid ] && lsof -nP -iTCP:$PORT -sTCP:LISTEN | grep -q " $(cat chrome.pid) "; then echo "already up on :$PORT"; exit 0; fi
  echo "port $PORT is held by a different process, refusing:"; lsof -nP -iTCP:$PORT -sTCP:LISTEN; exit 1
fi
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=$PORT --user-data-dir="$PWD/chrome-profile" \
  --no-first-run --no-default-browser-check $mode about:blank >chrome.log 2>&1 &
echo $! > chrome.pid
sleep 2; curl -s http://127.0.0.1:$PORT/json | python3 -c "import sys,json; [print(t['type'], t['url']) for t in json.load(sys.stdin)]"
