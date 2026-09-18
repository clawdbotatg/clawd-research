#!/bin/sh
# One-shot prompt: ./chat.sh "your question"
set -e
cd "$(dirname "$0")"
exec ./llama.cpp/build/bin/llama-cli \
  -m models/Ternary-Bonsai-2-27B-PQ2_0.gguf \
  -ngl 99 -fa on -c 32768 \
  --temp 1.0 --top-p 0.95 --top-k 20 \
  -p "$1" -n "${N:-1024}"
