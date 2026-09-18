#!/bin/sh
# llama-bench: prefill (pp512) + decode (tg128) tok/s on this Mac
cd "$(dirname "$0")"
exec ./llama.cpp/build/bin/llama-bench -m models/Ternary-Bonsai-2-27B-PQ2_0.gguf -ngl 99 -fa 1 -p 512 -n 128 "$@"
