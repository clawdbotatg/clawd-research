# Personal LLM Router + LLM Co-op — feasibility research

*Researched 2026-08-18. Three parallel web-research sweeps (OAuth-as-API mechanics,
router prior art, co-op ToS/risk) + the in-house prior art in
`clawd-harness/docs/fleet/SUB-ROUTING.md`.*

## TLDR

- **Personal router: YES, buildable — but the architecture is dictated by ToS.**
  Raw OAuth-token replay ("relay pattern") is explicitly banned by Anthropic,
  actively fingerprinted, and has produced ban waves since Jan 2026. The
  sanctioned path is driving the **official client** — Agent SDK / `claude -p` /
  interactive PTY — per account dir, which is *exactly what clawd-harness already
  does*. The router is a gateway that assigns requests to official-client
  workers, not a proxy that replays tokens.
- **Friend co-op: NOT viable as imagined for Claude.** It violates on two
  independent axes (account sharing §2; consumer OAuth outside official clients,
  Feb 2026 clarification) *regardless of transport* — even PTY-based dispatch of
  a friend's request through your login is "making your Account available to
  anyone else." Anthropic's Agent SDK credits are explicitly **non-transferable**
  (pooling foreclosed by design), and the small-scale version of this idea is
  architecturally identical to the gray-market pools ("Poison Claude") that
  Anthropic cited when it built the enforcement machinery. Real risk = friends
  lose accounts.
- **The co-op idea survives in a legal shape at API economics**: a shared credit
  pool (own API org with spend caps, or an OpenRouter organization) with our own
  router doing per-member accounting/analytics. And notably, **OpenAI already
  sells the co-op**: ChatGPT Business is $20/seat with a workspace-shared
  flexible-credit pool any member draws from — about the same price as everyone
  buying Plus individually.

---

## 1. The hard constraint: what subscription auth may and may not do

### Anthropic — the enforcement timeline (all verified, multi-source)

| Date | Event |
|---|---|
| 2025-07-28 | Weekly rate limits announced, explicitly citing **account sharing and reselling** as the abuse being stopped ([TechCrunch](https://techcrunch.com/2025/07/28/anthropic-unveils-new-rate-limits-to-curb-claude-code-power-users/), [@AnthropicAI](https://x.com/AnthropicAI/status/1949898502688903593)) |
| 2026-01-09 | Server-side block on **spoofing the Claude Code harness**; third-party harnesses (OpenCode etc.) using sub OAuth die with "This credential is only authorized for use with Claude Code." Account bans *preceded* the block. Anthropic's Thariq Shihipar: third-party harnesses produced "unusual traffic patterns without any of the usual telemetry" ([VentureBeat](https://venturebeat.com/technology/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses)) |
| 2026-02-17 | ToS clarification: *"Using OAuth tokens obtained through Claude Free, Pro, or Max accounts in any other product, tool, or service — including the Agent SDK — is not permitted."* Anthropic also legally forced OpenCode to delete its Claude OAuth code ([The Register](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)) |
| 2026-04-04 | Hard cutoff: subscriptions stop powering third-party harnesses (OpenClaw, ~135k+ instances, the headline casualty); transition credits offered ([TechCrunch](https://techcrunch.com/2026/04/04/anthropic-says-claude-code-subscribers-will-need-to-pay-extra-for-openclaw-support/)) |
| 2026-05-13 | "Agent SDK credits" announced ($20/Pro, $100/Max-5x, $200/Max-20x monthly, **non-transferable**) |
| 2026-06-15 | …and **paused on its effective date**. Current live state ([help center](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)): **Agent SDK, `claude -p`, GitHub Actions, and third-party apps authing via Agent SDK are permitted and draw from the subscription's normal usage limits.** |

Mechanics footnote: raw `/v1/messages` calls with a sub OAuth token *technically*
still worked as of 2026-03-29 — but only with an exact impersonation of Claude
Code (Bearer token + `anthropic-beta: oauth-2025-04-20,claude-code-20250219` +
the system prompt **beginning with the verbatim** "You are Claude Code…" string
as its own first block; Haiku exempt — curl transcripts in
[claude-code#40515](https://github.com/anthropics/claude-code/issues/40515)).
That's the cat-and-mouse zone: undocumented, narrowed repeatedly, ToS-banned,
and the thing accounts get banned for. **Not a foundation to build on.**

### OpenAI — near-opposite posture

- Codex CLI OAuth hits `chatgpt.com/backend-api/codex/responses` (Responses API
  shape, codex-family models only, plan rate limits). Full protocol is public
  ([gist](https://gist.github.com/ravidsrk/4e72b774c044917cd260560ec5831e1d)).
- **Sam Altman publicly blessed ChatGPT-subscription OAuth in OpenClaw**
  (2026-05-01, "happy lobstering"), and OpenAI later acquired OpenClaw. No
  documented crackdown on Codex-OAuth proxies. But the ToS still forbids
  credential sharing, opaque Pro-account bans do happen, and the blessing was
  for OpenClaw specifically — arbitrary proxies remain gray.
- ChatGPT Enterprise has official non-interactive access tokens for Codex CI.

### The architecture split (the load-bearing insight)

A [dev.to analysis](https://dev.to/vainamoinen/two-multi-account-claude-code-architectures-one-anthropic-accepts-one-they-ban-2om7)
of the ban waves names two multi-account architectures:

1. **Relay pattern** (server holds N OAuth tokens, terminates the API itself,
   impersonates the official client) → **banned**. Detection signature: one
   source endpoint, many tokens, no client telemetry. This is what
   claude-relay-service, CLIProxyAPI-for-Claude (dead 2026-04-04, author's
   postmortem: "Two months. That's how long it lasted."), and OpenCode did.
2. **Per-profile official-client pattern** (isolated `CLAUDE_CONFIG_DIR` per
   account, real `claude` processes, router assigns *work* to *sessions*) →
   **accepted** (Anthropic acknowledged the config-dir isolation pattern in
   claude-code#261).

**clawd-harness is already architecture #2.** Its sub-router (headroom via the
oauth/usage endpoint, weekly-reset-soonest spend policy, capability gate,
mid-session handoff) is ahead of every OSS scheduler we found — the OSS pools
(claude-relay-service, CLIProxyAPI) schedule by round-robin/cooldown, not by
live quota.

---

## 2. Prior art — what exists, what to reuse

| System | What it gives us | Where it falls short |
|---|---|---|
| **LiteLLM proxy** (MIT core, very active) | The whole gateway layer free: OpenAI **and** Anthropic `/v1/messages` ingress, virtual keys, per-key budgets, spend tracking in USD, fallbacks, admin UI. Sanctioned extension point: `CustomRoutingStrategyBase`. Even has an official "Claude Code Max subscription" tutorial — but it's **passthrough only** (client's own OAuth header forwarded) | Built for static API keys. No server-held OAuth, no token refresh, no live-quota headroom (its "usage-based" routing counts against *statically configured* tpm/rpm), no difficulty routing |
| **claude-relay-service** (11.7k★, active) | Best-in-class account-pool mechanics to study: per-account cooldowns by error class, sticky sessions, usage capture, cost-at-list-rates | It IS the banned relay pattern — reference only, never deploy |
| **new-api / one-api** (Chinese ecosystem) | The accounting model: user tokens with quota ledgers, channel priority/weight, tri-format ingress (OpenAI/Claude/Gemini) | Static keys, no headroom, AGPLv3 (new-api) |
| **OpenRouter** (design reference) | The accounting pattern worth copying: prepaid credits at list price + small skim, failed requests never billed, per-key analytics, inverse-price² provider weighting with a 30s health window. OpenRouter **organizations** = legal shared credit pool today | It's a service, not software |
| **claude-max-api-proxy** family, ai-cli-bridge, 0x0ndra's Agent-SDK proxy | Proof the sanctioned shape works: OpenAI-compatible HTTP over the official CLI/SDK, still alive post-crackdown *because they are Claude Code* | Latency (process spawn / CLI boot), CC's harness system prompt rides along, no logprobs/param fidelity, re-chunked pseudo-streaming |
| **Difficulty routing**: RouteLLM (canonical, aging, 8k-token limit, degrades on agentic traffic), **vLLM Semantic Router** (the serious 2026 effort, six signal types, Apache 2.0), **Arch-Router** (1.5B open-weights, routes to *user-defined policy lanes* — no training, human-legible) | 30–85% cost savings claims depending on mix | Trained difficulty scorers all degrade on agentic/tool traffic — our dominant traffic type. Policy lanes > learned scorer for us |

Gateway landscape churn worth knowing: Portkey → Palo Alto (2026-05), Helicone →
Mintlify maintenance mode (2026-03), TensorZero archived (2026-06). LiteLLM and
new-api are the survivors with real Anthropic ingress.

---

## 3. Personal router — proposed design (buildable now)

One gateway ("**clawd-router**"), one URL, two ingress dialects
(`/v1/chat/completions` + `/v1/messages`), virtual keys per product. Three
backend classes:

1. **API-key pool** (Bankr, OpenRouter, any raw key): true API semantics,
   ~300ms first token. This is where **light traffic** goes (naming-tier jobs —
   the qwen3-coder lesson from the harness survey generalizes).
2. **Claude subscription pool**: Agent SDK / `claude -p` workers, one per
   `~/.clawd-accounts/<name>` config dir, **routed by the harness's existing
   brain** (`_route_key`: usage-endpoint headroom, reset-soonest,
   fable-capability gate — port or import those ~200 lines). This is where
   **heavy/agentic traffic** goes, where the CLI's tradeoffs (system-prompt
   overhead, seconds of latency) don't matter.
3. **Codex subscription**: `codex exec` / app-server workers (the harness
   already speaks app-server JSON-RPC for rate-limit reads).

Difficulty routing v1 = **explicit lanes, not a learned scorer**: expose model
aliases (`router/fast`, `router/smart`, `router/agent`) and simple heuristics
(prompt length, tool presence, caller identity) — Arch-Router-style policy, no
training. A classifier can come later; every trained router degrades on agentic
traffic anyway.

Accounting/analytics built in from day one: every request → sqlite/jsonl row
(virtual key, backend, tokens, latency, cost at API list rates even for
sub-served requests — that's the number that shows what the subs are *worth*).

**Build vs assemble**: LiteLLM in front would buy virtual keys/admin UI at the
cost of a Postgres + a big dependency; a pure-stdlib homebrew matches the
harness ethos and the routing brain already exists in `server.py`. Recommend
homebrew MVP, steal LiteLLM later only if key-management pain appears.

Honest caveats:
- Sub-served requests are **not** a drop-in API: Claude Code's harness prompt
  shapes tone, params like temperature aren't honored, streaming is re-chunked.
  Fine for agent workloads; wrong for low-latency product features (those go to
  lane 1).
- The June 2026 permission ("draws from your subscription's usage limits") is a
  help-center article on a paused policy — Anthropic has repriced this ground
  three times in a year. Design so the Claude-sub backend can be swapped for
  metered API keys without touching clients.
- Multiple subs, one human, own machines = consistent with the accepted
  pattern. Volume discipline still matters (24/7 background burn was the other
  cited abuse trigger).

### Prototype plan (step one, ~a day of work)

1. Skeleton gateway: stdlib HTTP server, `/v1/chat/completions` +
   `/v1/messages`, virtual keys in a json file, jsonl request ledger.
2. Lane 1 passthrough to Bankr/OpenRouter (immediately useful — one URL for all
   products).
3. Lane 2: Agent SDK worker over **two** of the existing account dirs, routing
   by a ported `_route_key` + usage poller. Verify handoff when one sub goes
   hot.
4. Point one real product at it; read the ledger; decide whether the sub lane
   earns its complexity vs just buying API credits for programmatic traffic.

---

## 4. The co-op — verdict and the legal pivot

### Why token-sharing doesn't work

- **Anthropic Consumer ToS §2**: "You may not share your Account login
  information… You also may not make your Account available to anyone else."
  Serving a friend's request through your login violates this **whatever the
  transport** — relay OR official-client PTY.
- **Feb 2026 clarification** independently kills the "website where friends
  refresh their token monthly" mechanic: consumer OAuth tokens may not be used
  in any non-official product *at all*, even by their owner.
- **Agent SDK credits are non-transferable** — Anthropic foreclosed pooling by
  design, after explicitly citing account-sharing/reselling as the abuse that
  triggered the 2025 limits.
- Enforcement is real and current: Jan 2026 ban wave, Okta's Aug 2026 research
  on pooled-account gray markets ("Poison Claude", ~881 users), reported
  identity-verification tightening at checkout. Detection profile of a 5-friend
  co-op (one router, many tokens, diverse IPs, no client telemetry) is exactly
  what they fingerprint. Small pools reportedly slip through longer — but the
  stake is each friend's account (and Austin has 4).
- OpenAI: same sharing clause, historically laxer enforcement, opaque bans do
  happen. Not a foundation either.

### What IS possible (three legal shapes)

1. **Co-op at API economics** — the real option for "our own router with our own
   accounting." Friends fund a shared pool: either an **OpenRouter organization**
   (shared credits, per-key attribution, role-based billing — exists today,
   ~5.5% fee) or our **own API org** (Anthropic/OpenAI orgs support members,
   one bill, workspace spend caps) fronted by clawd-router for per-member
   virtual keys, analytics, and burn-the-expiring-credits-first logic. Loses
   the subscription arbitrage — but that arbitrage is precisely the thing that
   was named and shut down. This is where "analytics + accounting built in"
   shines legitimately.
2. **Buy the co-op off the shelf (OpenAI side)** — **ChatGPT Business**:
   $20/seat/mo annual (2-seat min), plus a workspace-purchased **shared
   flexible-credit pool any member draws from** after their own limit. That is
   the co-op, legally, at ~the price of individual Plus. (Caveat: Codex seats
   closed to new Business workspaces since 2026-06-24.) Anthropic's equivalent
   (true shared org pool) exists only at Enterprise; **Claude Team seats do NOT
   pool usage** — 5 premium seats = $500/mo = same as 5×Max-5x, still unpooled.
3. **Co-op of infrastructure, not headroom** — friends each keep their own subs
   and logins, and share the *harness/fleet tooling* (each person's requests
   only ever touch their own accounts). Shared software, shared dashboards,
   zero shared credentials. This is just "friends run clawd-harness" and is
   fully clean.

### Recommendation

Build the **personal router** (it's sanctioned, mostly-written, and immediately
useful across all products). Skip the token co-op. If the friend group
materializes, offer shape 1 or 3 — and let the router's ledger be the pitch:
after a month of data it can literally print "here's what this traffic would
cost as a shared API pool vs what you each pay in subs."

---

## Source notes

Primary: anthropic.com/legal/consumer-terms (2025-10-08) ·
support.claude.com/articles/15036540 (Agent SDK on plans, live) ·
claude-code#40515 (OAuth gate curl transcripts) · theregister.com 2026-02-20 &
2026-04-06 · techcrunch.com 2025-07-28 & 2026-04-04 ·
x.com/sama/status/2050357911915028689 · docs.litellm.ai (routing /
anthropic_unified / claude_code_max_subscription) ·
github.com/Wei-Shaw/claude-relay-service · github.com/router-for-me/CLIProxyAPI ·
github.com/QuantumNous/new-api · github.com/lm-sys/routellm ·
github.com/vllm-project/semantic-router · huggingface.co/katanemo/Arch-Router-1.5B ·
openrouter.ai/docs/organization-management · help.openai.com/articles/11487671
(Business flexible pricing). Flagged-secondary: autonomee.ai, explainx.ai,
groundy.com ban-wave details; "raw spoofed calls still work in Aug 2026" is
unverified (last proof 2026-03-29).
