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
