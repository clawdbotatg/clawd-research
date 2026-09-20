# Ternary Bonsai 2 27B — running locally on the Mac

Announced 2026-09-17 by PrismML (https://x.com/PrismML/status/2100692248480596348).
Qwen3.8-27B compressed to ternary weights ({-1,0,+1}, 1.75–2.13 bits/weight). 7.2 GB on disk,
Apache 2.0, multimodal (text + images), 262K context, reasoning on by default.

## The one gotcha

**Stock llama.cpp, Ollama and stock MLX do not run this model.** The weights need an activation
(Hadamard) transform that only exists in PrismML's forks. Stock llama.cpp refuses the PQ2_0 / PTQ1_0
files with an unknown-type error; a "Q2_0" dev file loads in stock builds and outputs gibberish with no
warning. So: `./llama.cpp` here is `PrismML-Eng/llama.cpp`, branch `prism`, built with Metal.

## Layout

- `llama.cpp/` — PrismML fork (gitignored). Rebuild: `cmake -B build -DLLAMA_CURL=OFF && cmake --build build -j --target llama-cli llama-server llama-bench`
- `models/` — gitignored. `Ternary-Bonsai-2-27B-PQ2_0.gguf` (7.2 GB) + `Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf` (0.6 GB vision tower)
- `serve.sh` — OpenAI-compatible server on :8090 with vision. `BONSAI_PORT=… BONSAI_CTX=… ./serve.sh`
- `chat.sh "prompt"` — one-shot answer in the terminal
- `bench.sh` — llama-bench numbers

## Which file

| pack | bits/w | size | note |
|---|---|---|---|
| PQ2_0 | 2.13 | 7.2 GB | faster prefill; what PrismML's demo uses by default. **We use this.** |
| PTQ1_0 | 1.75 | 5.9 GB | the headline "5.9 GB" number; denser packing, slower prompt processing |

Re-download: `hf download prism-ml/Ternary-Bonsai-2-27B-gguf Ternary-Bonsai-2-27B-PQ2_0.gguf --local-dir models`

## Sampling (from the model card, also baked into GGUF metadata)

- thinking (default): temp 1.0, top_p 0.95, top_k 20
- non-thinking: temp 0.7, top_p 0.80, top_k 20, presence_penalty 1.5
- reasoning effort defaults to `xhigh`; `medium` is shorter; `low` is not supported

## Links

- Model card: https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf
- MLX pack (needs PrismML-Eng/mlx fork, branch prism): https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-mlx-2bit
- Demo repo (setup.sh, Open WebUI, vision, speculative decoding docs): https://github.com/PrismML-Eng/Bonsai-demo
- Whitepaper: https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-27b-whitepaper.pdf
- Blog: https://prismml.com/news/bonsai-2-27b

## Verified 2026-09-17 on this Mac (M3 Max, 128 GB, macOS 26.2)

Fork commit `5d80cff` (branch `prism`), built with Metal. Everything below was run through `serve.sh` / `bench.sh`.

| check | result |
|---|---|
| server start to `/health` ok | 7 s |
| text Q&A (reasoning on) | coherent, reasoning trace returned in `reasoning_content` |
| code gen (Fibonacci w/ docstring) | correct |
| vision (64px PNG, red square on blue) | "blue background with a red square centered in the middle" |
| llama-bench pp512 (prefill) | 180 tok/s |
| llama-bench tg128 (decode) | 18.6 tok/s |

Decode is the same ~18 tok/s PrismML lists for an M4 Pro, well under what M3 Max bandwidth
(~400 GB/s over 6.7 GiB ≈ 60 tok/s ceiling) should allow. The ternary Metal kernel is not
bandwidth-saturating on M3 yet; PrismML's own numbers are all M5. Worth re-benching after fork updates.

Gotchas hit:
- The harness exports `PORT=8787`, so the server script uses `BONSAI_PORT` instead.
- `llama-cli` in this fork is the new interactive-only one (no `-no-cnv`); use `llama-server` + curl for scripted use.
- `reasoning_effort` is passed as `"chat_template_kwargs": {"reasoning_effort": "medium"}` in the request body.
- Ollama can't run it (no fork), and the Qwen3.8 hybrid-attention arch means an F16 GGUF also won't help there.
