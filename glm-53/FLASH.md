# GLM-5.3-Flash — Ox Alpha unmasked, MIT weights, can we run it?

*Researched 2026-08-26, day of release.
Source tweet: https://x.com/Zai_org/status/2092616204787626030*

## TLDR

- **Ox Alpha (the free stealth model on OpenRouter) = GLM-5.3-Flash.** Z.ai
  confirmed it in the launch tweet — "previously previewed as Ox Alpha, running
  entirely on Chinese AI chips."
- **Weights are live NOW**: https://huggingface.co/zai-org/GLM-5.3-Flash —
  **MIT license**, 320B total / **18B active** MoE, natively multimodal
  (image+video in), 1M-token context. FP8 release (~330GB of safetensors).
- **Local on a 128GB Mac (M3 Max): technically yes, at 1-bit only.** Not worth
  it for real work. 256GB+ (M3 Ultra Studio, 2×DGX Spark) runs 2–4-bit fine.
- **Ollama: not yet.** No library entry; llama.cpp support is a WIP PR. Unsloth
  GGUFs (`unsloth/GLM-5.3-Flash-GGUF`) were still uploading on release day.
- **Best cloud path: don't self-host — the API is dirt cheap.**
  $0.15 in / $0.50 out / $0.03 cached per 1M. Self-hosting 8×H100 (~$20/hr)
  only wins for privacy or fine-tunes.

## What it is

- First **natively multimodal** GLM-5-series model; 30T-token multimodal corpus.
- **NOT the same model as GLM-5.3** (the 744B coding/cyber model from 08-14,
  whose own weights drop was promised ≈08-28 and is still pending as of today).
  Flash is a new smaller base: hybrid sparse+linear attention +
  "Manifold-Constrained Hyper-Connections (mHC)" — a genuinely new arch
  (`glm5_next`), which is why llama.cpp support lags.
- Z.ai's Code Bench claim: beats GLM-5.2 at every effort level, **on par with
  Claude Opus 4.8** on real-world coding.
- Trained/served "entirely on Chinese AI chips" — notable geopolitics flex.
- HF model card shows 300K max context in the base config; the API and Unsloth
  docs advertise the full 1,048,576.

## Can we run it locally?

Math: 320B params → FP8 ~330GB, Q4 ~180GB, Q2 ~115GB, IQ1_S ~75GB.
18B active means it's FAST once it fits (MoE — expect 20–40+ tok/s on Apple
Silicon at fitting quants).

| Hardware | Verdict |
|---|---|
| **This M3 Max, 128GB** | Only Unsloth's 1-bit (IQ1_S ≈75GB) fits under the wired-memory ceiling. Runs, but 1-bit quality on an 18B-active MoE is demo-tier. Unsloth's own docs default to IQ1_S for a reason. |
| Mac Studio M3 Ultra 256GB | Q2_K_XL comfortable, Q4 tight |
| Mac Studio 512GB | Q4–Q8, full send |
| 2× DGX Spark (256GB) | Q2–Q3 territory |
| 1× RTX 5090 (32GB) | No (even with CPU-offload MoE tricks, 128GB system RAM box + GPU could do Q2 via llama.cpp/KTransformers) |

**Tooling status (release day):**
- **llama.cpp**: WIP PR (new `glm5_next` arch). Unsloth Desktop can run it now.
- **Unsloth GGUFs**: repo up (`unsloth/GLM-5.3-Flash-GGUF`), files uploading
  "later today/early tomorrow" per their reply on the launch tweet.
- **Ollama**: nothing in the library; will need llama.cpp support to land +
  Ollama to vendor it. Expect days–weeks. When GGUFs land you can try
  `ollama run hf.co/unsloth/GLM-5.3-Flash-GGUF:IQ1_S` but only after Ollama
  ships the arch.
- **MLX**: expect mlx-community quants shortly; same memory math applies.
- **vLLM / SGLang / KTransformers**: day-0 recommended by the model card
  (that's the serious-GPU path, not the Mac path).

## Best way to run it in the cloud

1. **Z.ai API** — $0.15/$0.50 per 1M ($0.03 cached). Anthropic-compatible
   endpoint works inside Claude Code/OpenCode. This is ~30× cheaper than
   GLM-5.2's old pricing and undercuts basically everything at this quality
   claim. docs.z.ai/guides/llm/glm-5.3-flash
2. **OpenRouter** — `stealth/ox-alpha` was the free preview; expect a proper
   `z-ai/glm-5.3-flash` listing (free window likely closing now that it's
   revealed).
3. **Z.ai Coding Plan** (z.ai/subscribe) — flat-rate sub, now includes Flash.
4. **Self-host cloud** (only for privacy/fine-tune): FP8 on 4×H200 (564GB) or
   8×H100 (640GB) via vLLM/SGLang; ~$20–25/hr on Runpod/Lambda. At the API's
   $0.50/M output you'd need to push ~40M+ output tokens/hr to break even —
   don't, unless the data can't leave.
5. **Flat-rate GLM hosts** (Chutes, Synthetic, NanoGPT, Ollama cloud) — now
   that weights are MIT they can host it; watch for listings this week.

## Open questions / watch

- Big-sibling **GLM-5.3 (744B) weights** still unreleased (promised ≈08-28,
  security-review delay per betanews). Flash dropping first with MIT is a good
  sign the big one follows.
- llama.cpp PR merge → Ollama/LM Studio availability.
- Independent evals of the "on par with Opus 4.8" coding claim (vendor bench).
- Multimodal (image/video) support in GGUF land usually lags text — check
  whether Unsloth quants carry the vision tower.
