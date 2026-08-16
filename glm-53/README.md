# GLM-5.3 — is it open source, and where can you get it on subscription billing?

*Researched 2026-08-16 (two days after release). This is a fast-moving snapshot — the
weights drop expected ~end of August 2026 will invalidate the "who has it" table below.*

## TLDR

- **GLM-5.3 is NOT open source yet — but it's promised.** Zhipu/Z.ai released it
  2026-08-14 as API/subscription-only, with open weights coming "~2 weeks" after
  release, pending security reviews. License unconfirmed (5.2 was MIT within days
  of its release; the delay + unstated license for 5.3 is a mild deviation the
  community is watching).
- **Today, exactly one subscription carries it: Z.ai's own GLM Coding Plan.**
  Every other flat-rate provider (Ollama cloud, Chutes, Synthetic, NanoGPT,
  Cerebras Code) hosts *open weights*, so they're stuck at GLM-5.2 until the drop.

## What GLM-5.3 is

- Zhipu AI / Z.ai's next-gen coding model, released **2026-08-14**.
- **Same base architecture as GLM-5.2** — all gains from extended post-training.
  (GLM-5.2 is 744B params, ~976K context; expect 5.3 to match.)
- Claimed **"strongest open-weights coding model"**, ~50% jump in agentic coding.
- Notable **cybersecurity angle**: trained for multi-stage exploit reasoning;
  Zhipu reports it found 2,436 flaws across 269 projects in their testing.
- Works today inside **Claude Code / OpenCode / ZCode** via Z.ai's
  Anthropic-compatible endpoint.

## Open-source status

| Question | Answer (as of 2026-08-16) |
|---|---|
| Weights downloadable? | **No** — promised ~2 weeks post-release (≈ end of Aug 2026) |
| License | **Unannounced.** GLM-5.2 was MIT; watch whether 5.3 keeps it |
| Pay-per-token API price | **Unpublished** — Z.ai's API table still tops out at GLM-5.2 ($1.40 in / $4.40 out per 1M); don't assume 5.3 matches |
| Prior precedent | 5.2 shipped MIT weights within days; 5.3's security-review delay is new |

## Subscription-billing access

### Has GLM-5.3 today
- **Z.ai GLM Coding Plan** (https://z.ai/subscribe) — the only route.
  - **Lite $18/mo** · **Pro $80/mo** · **Max $168/mo** (yearly billing ≈30% off:
    $12.60 / $56 / $117.60 effective).
  - Tiers differ only in **weekly quota** (plus a 5-hour rolling limit), not model
    access — all tiers get GLM-5.3, GLM-5.2, GLM-5-Turbo.
  - Anthropic-compatible API → drop-in for Claude Code (`ANTHROPIC_BASE_URL` swap).

### Will get it after the weights drop (currently GLM-5.2)
- **Ollama cloud** — $20/mo; `glm-5.2:cloud` and `glm-5.1:cloud` today, no 5.3 tag
  yet. GLM there is **cloud-only** (no local tag even for 5.2 — 744B params).
- **Chutes.ai** — frontier models (incl. GLM-5 family) need the **$10/mo** tier
  (no longer on the $3 plan).
- **Synthetic** — base plan now **$30/mo**.
- **NanoGPT** — flat-rate plan carries the GLM-5 family.
- **Cerebras Code** — $50/mo Pro (1M TPM, 24M tok/day) / $200/mo Max (1.5M TPM,
  120M tok/day); has hosted GLM before (fastest GLM-4.6 inference) — needs weights.

### Self-host (once weights land)
- GLM-5.2 scale needs ~8×H200 under vLLM — realistic only vs. renting; the $18–30/mo
  subscription tier is the economic answer for individual use.

## Watch-fors

1. **The weights drop (~end of Aug 2026)** — check Hugging Face `zai-org/` org.
2. **The license** — MIT continuity vs. something more restrictive.
3. **Third-party cascade** — Ollama cloud / Chutes / Synthetic / Cerebras should
   pick it up within days of the weights; that's when subscription choice opens up.

## Sources

- https://the-decoder.com/zhipu-ai-releases-glm-5-3-claims-its-the-strongest-open-weights-coding-model/
- https://mlq.ai/news/zhipu-releases-glm-53-through-its-coding-service-with-weights-still-two-weeks-away/
- https://felloai.com/glm-5-3/
- https://emergent.sh/learn/glm-5-3-pricing
- https://z.ai/subscribe
- https://ollama.com/search?c=cloud
- https://blog.patshead.com/2026/01/squeezing-value-from-free-and-low-cost-ai-coding-subscriptions.html
- https://www.cerebras.ai/code
