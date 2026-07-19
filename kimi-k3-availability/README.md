# Kimi K3 — where to get it, and how to run it on a subscription

*Researched 2026-07-18 (K3 shipped two days earlier, on 2026-07-16). Method: deep-research
workflow — 5 search angles → 21 sources fetched → 104 claims extracted → top 25
adversarially verified (3 independent refute-votes each; 20 confirmed, 4 killed,
1 left unverified) — plus direct browser reads of the live kimi.com pricing pages.*

## TL;DR

**Kimi K3 exists** (released 2026-07-16: ~2.8T-param MoE, open-weight, 1M context,
native vision) **and yes — there is a subscription path.** The confusion is that
Moonshot runs two separate storefronts:

| Storefront | Billing | K3? |
|---|---|---|
| `platform.kimi.ai` / `api.moonshot.ai` (API platform) | **Pay-per-token only** — K3: $3.00/M in, $0.30/M cached in, $15.00/M out | ✅ `kimi-k3` |
| `kimi.com` (consumer membership) | **Flat-rate subscription** — every paid tier includes **Kimi Code**, which serves K3 through its own coding API | ✅ `k3` (Moderato tier+) |

So the answer to "can I get K3 on a subscription?" is **yes: any paid Kimi
membership ($19/mo and up) includes Kimi Code credits, Kimi Code serves `k3`,
and it exposes an Anthropic-compatible endpoint you can point Claude Code (or
the clawd harness) at.**

## The subscription: Kimi membership → Kimi Code

Pricing read live from `kimi.com/membership/pricing` on 2026-07-18:

| Tier | Monthly | Annual (eff./mo) | Kimi Code credits | K3 notes |
|---|---|---|---|---|
| Adagio | $0 | — | — | no Kimi Code |
| **Moderato** | $19 | $15 | 1x | **k3 unlocked**, 262K context |
| Allegretto | $39 | $31 | 5x | + 1M context window, low/high/max thinking effort |
| Allegro | $99 | $79 | 15x | + "K3 extra long chat capacity (up to 1M tokens)" |
| Vivace | $199 | $159 | 30x | 10x agent credits |

- Kimi Code limits (official docs): **~300–1,200 requests per 5-hour window**
  (tier-dependent), up to 30 concurrent requests. Same shape as a Claude
  subscription's 5-hour session windows — the harness's routing model maps onto it.
- ⚠️ **Restructure imminent:** the pricing page carries a banner — *"New Membership
  Plans Coming Soon. Kimi and Kimi Code benefits will be separated. Existing
  subscribers are unaffected. You can still buy the current plan before launch."*
  A standalone Kimi Code plan is about to launch; buying now grandfathers the
  bundled deal.

## Wiring the subscription into an agent

Kimi Code (the subscription product) exposes real API endpoints, keyed by API
keys minted in the **Kimi Code Console** (max 5 keys per account), all confirmed
against the official docs (`kimi.com/code/docs/en/`):

- **OpenAI-compatible:** `https://api.kimi.com/coding/v1`
- **Anthropic-compatible:** `https://api.kimi.com/coding/`

Claude Code on the subscription (from Moonshot's own third-party-tools doc):

```bash
export ANTHROPIC_BASE_URL=https://api.kimi.com/coding/
export ANTHROPIC_API_KEY=<key from Kimi Code Console>
# model name: k3  (Moderato+, 262K ctx; "k3[1m]" long-context variant appears
#                  in Moonshot's Claude Code guide — Allegretto+ unlocks 1M)
# legacy alias: kimi-for-coding
```

First-party tooling on the same subscription:
- **Kimi Code CLI** (Node.js): `curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash`
- **Kimi Code for VS Code** extension
- JetBrains / Zed via the CLI's **ACP** protocol
- Claude Code officially listed as a supported third-party agent

## Pay-per-token alternatives (no subscription)

| Provider | Model | Price (in/out per 1M) | Context | Notes |
|---|---|---|---|---|
| Moonshot API platform | `kimi-k3` | $3.00 / $15.00 ($0.30 cached) | 1M | OpenAI-compatible `https://api.moonshot.ai/v1` (`MOONSHOT_API_KEY`); Anthropic-compatible `https://api.moonshot.ai/anthropic` (`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`) — their Claude Code guide says `kimi-k3` is the default, works out of the box |
| OpenRouter | `moonshotai/kimi-k3` | $3 / $15 | 1M | listed day-of-release (2026-07-16); OpenAI-compatible, swap base URL |
| OpenRouter | `moonshotai/kimi-k2.6` | ~$0.66 / ~$3.41 (post-cache blended) | 262K | previous flagship (2026-04-20) |
| OpenRouter | `moonshotai/kimi-k2.5` | $0.375 / $2.025 | 262K | cheap agentic/visual-coding model |
| OpenRouter | `moonshotai/kimi-k2-thinking` | $0.60 / $2.50 | 256K | 2025-era reasoning model |

Note the pattern: K3 API pricing is ~5x K2.6 — the flat-rate membership is where
the value is if you're running an agent hard.

## Third-party flat-rate subscriptions (K2-era only, no K3 yet)

- **NanoGPT Pro — $12/mo** (`nano-gpt.com/subscription`): 60M included input
  tokens/week across 200+ open models, 5% off PAYG beyond that. As of 2026-07-18
  the newest Kimi included is **K2.7 Code** — *no K3* (K3 is 2 days old;
  unverified whether/when it lands, and one claim that K2.7 burns quota at 2x
  was refuted — treat quota details for specific models as unconfirmed).
- **Chutes — Plus $10/mo / Pro $20/mo** (`chutes.ai/pricing`): bundled daily
  quota + 6%/10% off PAYG. Quota numbers not on the pricing page; K3 not
  confirmed there yet either.

Open weights are released, so expect Fireworks/Groq/Together/DeepInfra hosting
and third-party-sub inclusion to follow within weeks — as of today (day 2),
none of the checked third-party flat plans serve K3; only Moonshot's own
membership does.

## Recommendation for the harness experiment

Cheapest real test of "K3 as a coding agent on a subscription":

1. **Moderato monthly ($19)** at kimi.com → activate Kimi Code → mint a key in
   the Kimi Code Console.
2. Point Claude Code at it: `ANTHROPIC_BASE_URL=https://api.kimi.com/coding/`,
   `ANTHROPIC_API_KEY=<key>`, model `k3` — i.e. the same env-var shape the clawd
   harness already knows how to scrub/route, so a "kimi" account could slot in
   as another pool.
3. If the 1x credits (~300 req/5h floor) or 262K context pinch, Allegretto ($39)
   is the 1M-context + 5x tier.
4. Buy before the plan split lands if the bundled pricing looks good.

## Sources (primary)

- https://openrouter.ai/moonshotai/kimi-k3 — K3 listing, 2026-07-16 release, $3/$15
- https://www.kimi.com/code/docs/en/ — Kimi Code overview: subscription benefit, limits, endpoints, tools
- https://www.kimi.com/code/docs/en/third-party-tools/other-coding-agents.html — Claude Code env vars, tier→model table
- https://platform.kimi.ai/docs/guide/claude-code-kimi — official Claude Code guide (API-platform side)
- https://platform.kimi.ai/docs/pricing/chat-k3 — K3 API pricing (read directly)
- https://www.kimi.com/membership/pricing — tier prices (read directly via browser, JS-rendered)
- https://nano-gpt.com/subscription · https://chutes.ai/pricing — third-party flat plans
- Secondary color: CNBC 2026-07-17 (K3 launch), simonwillison.net 2026-07-16

*Verification note: 4 claims were killed in adversarial review — all were "K3
doesn't exist" inferences from stale K2.x pages predating the 2026-07-16 launch.
Watch for this staleness in any pre-July-2026 writeup.*
