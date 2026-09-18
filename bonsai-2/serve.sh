#!/bin/sh
# Serve Ternary Bonsai 2 27B (OpenAI-compatible) on http://127.0.0.1:${BONSAI_PORT:-8090}
# Vision on via the mmproj. Stock llama.cpp will NOT run this model; this uses PrismML's fork in ./llama.cpp.
set -e
cd "$(dirname "$0")"
BONSAI_PORT="${BONSAI_PORT:-8090}"
CTX="${BONSAI_CTX:-32768}"
exec ./llama.cpp/build/bin/llama-server \
  -m models/Ternary-Bonsai-2-27B-PQ2_0.gguf \
  --mmproj models/Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf \
  --host 127.0.0.1 --port "$BONSAI_PORT" \
  -ngl 99 -fa on -c "$CTX" \
  --temp 1.0 --top-p 0.95 --top-k 20 \
  --jinja \
  "$@"
