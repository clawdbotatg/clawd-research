# Agent marketplaces — where to list leftclaw.services + onedollaraudit.com

Researched 2026-10-07. Goal: more traffic for $1 audits and other leftclaw services.
Nothing has been signed up for or submitted yet.

## TL;DR

- We're in almost none of the x402 directories. Main reason: we settle through our
  own facilitator (`clawd-facilitator.vercel.app`). Coinbase's x402 Bazaar only
  indexes routes after **CDP's facilitator** settles a payment. The Bazaar feeds
  Agentic.Market, OpenSea Tools, 402index, agent-tools.cloud and others — one fix
  unlocks ~6 listings.
- Our 402 response already carries correct `extensions.bazaar` metadata. It's a
  routing change, not a rewrite.
- Audits are a nearly empty niche: Bazaar search "smart contract audit" = 8
  competitors (agent402.tools, minia2a.uk, automatoncolony.xyz...); Agentic.Market
  "audit" = 2.
- x402 total volume is small (~$1M/mo, down 77–93% from late-2025 peak). Listing is
  cheap, so do it, but don't expect a flood from any one place.

## Fix our own metadata first

| Problem | Where |
|---|---|
| Prices stale: audit **$200**, QA $50, consult $20 (real: $1 / $2.50 / $1) | `leftclaw.services/.well-known/agent.json`, `/.well-known/agent-registration.json` |
| Two payout addresses: `0x11ce…1442` in agent.json vs `0xCfB3…76EA` in `/api/services` + live 402 | agent.json — Circle wallet check and x402scan ownership proof will trip on it |
| Old contract `0x1e70…4A9F` in agent.json vs `0xb2fb…413a` live | agent.json |
| onedollaraudit.com has skill.md + llms.txt but no `/.well-known/agent.json`, `/api/services`, `/openapi.json`, `/.well-known/x402` | onedollaraudit.com |
| ERC-8004 agent #21548 "Clawd" (12 feedbacks, avg 95) doesn't mention "leftclaw" or "onedollaraudit"; only protocol declared is "Web"; not on Base | 8004 registration |

## Do-list, ranked by traffic per effort

| # | Action | Effort | Notes |
|---|---|---|---|
| 1 | **Circle Agent Marketplace** — [form](https://forms.gle/7YFzvdmMcn1JH5tF6) ([docs](https://developers.circle.com/agent-stack/agent-marketplace/get-listed)) | 15 min + OpenAPI spec | This is "Circle's one." ~2,850 endpoints / 41 providers. Manual review, payout wallet sanctions check, health-checked. LoneStarOracle already sells `/audit` there. |
| 2 | **Coinbase x402 Bazaar → Agentic.Market, OpenSea Tools, copy sites** | half day | Settle paid routes via CDP facilitator (needs CDP keys; 1k settlements/mo free, then $0.001). Make one real $1 payment. Indexing bug [#3677](https://github.com/x402-foundation/x402/issues/3677) — verify after. |
| 3 | **x402scan** — [register](https://www.x402scan.com/resources/register) + PR adding our facilitator to `packages/external/facilitators/` | <1 h | Without the PR our volume shows as zero. Reads `/openapi.json` (`x-payment-info`) or `/.well-known/x402`. |
| 4 | **402index** (`POST /api/v1/register`), **x402-list.com** (`POST /api/v1/submit`), **Agent402** (register API) | minutes each | Free. Agent402 routes orders, 57K settlements. |
| 5 | **PR to [pashov/ai-web3-security](https://github.com/pashov/ai-web3-security)** adding LeftClaw | 10 min | One Dollar Audit is already on it. Read by auditors. |
| 6 | **Own channels:** Scaffold-ETH docs/extensions, SpeedRunEthereum, BuidlGuidl | low | Easiest high-fit audience. |
| 7 | **Awesome-list PRs:** [saeidshirazi/Awesome-Smart-Contract-Security](https://github.com/saeidshirazi/Awesome-Smart-Contract-Security), [bkrem/awesome-solidity](https://github.com/bkrem/awesome-solidity) (7k★), [Merit-Systems/awesome-x402](https://github.com/Merit-Systems/awesome-x402), [shanzson/…Auditor-Tools](https://github.com/shanzson/Smart-Contract-Auditor-Tools-and-Techniques) | 15 min each | |
| 8 | **Base ecosystem** — [form](https://forms.gle/hJhc2PqfAsQp86YL8) | 10 min | PRs to base/web no longer accepted. |
| 9 | **ERC-8004 cleanup:** add names, A2A/MCP + skills to registration, serve `/.well-known/agent-card.json`, register on Base too | 1 h | Helps Agent0 / 8004scan search. |
| 10 | **Skills:** public repo so `npx skills add clawdbotatg/...` works ([skills.sh](https://skills.sh) ranks by install telemetry); `clawhub skill publish` to [ClawHub](https://clawhub.ai) | low | We already have skill.md files. |
| 11 | **Virtuals ACP** — [acp-cli](https://github.com/Virtual-Protocol/acp-cli) | ~1 day + ~1 wk review | No token needed. Biggest real agent-to-agent job market (Cybercentry security agent: ~11K jobs, 573 buyers). Needs a job-listener wrapper, 10 sandbox jobs, graduation review. Numbers inflated by $1M/mo incentives; protocol cut possibly ~40% (unconfirmed). |
| 12 | **Daski** — [providers](https://daski.io/providers) | low–medium | What you found. Launched ~09-30 on Base, x402 + MCP + ERC-8004. Only 3 services, all the founder's. Early slot, no buyers yet. Whitelist via Discord. |
| 13 | **x402 MCP server** (free `list_services`/`quote`/`job_status`, paid tools return 402) → official MCP Registry (PulseMCP/Glama follow), Smithery, Cline, cursor.directory, mcp.so | 1–2 days | Buyer needs a wallet MCP (Coinbase Payments MCP, PipRail). Claude Connectors Directory §4A bans tools that move money — only OK if our server never pays. OpenAI apps: banned. |
| 14 | **There's An AI For That** — $49 one-time | 10 min + $49 | Only paid human directory with real traffic (~5–9M/mo). |
| 15 | Masumi/Sokosumi (register any 402 URL), Nevermined (1–2% fee), Visa CLI merchants, Ampersend, Pay.sh PR | low each | Small audiences. |
| 16 | Hardhat plugin (`hardhat-onedollaraudit`) → community plugins list | medium | Dev reach; a competing AI-auditor plugin is already listed. |

## Needs a wrapper / other chain — later, maybe

Warden Agent Hub (Warden Code wrapper, ~1 USDC), Kite AI (settles on Kite chain),
OpenServ (x402 market, tiny listings), OKX AI (X Layer, USDT), Skyfire (own tokens),
Taskmarket/Daydreams (we'd bid on tasks), Moltlaunch (ETH-paid), Olas Mech (15% fee,
self-dealing volume), Heurist Mesh, the402.ai, Fetch.ai Agentverse (mostly dormant).

## Skip

- Dead/paused: ClawTasks, Work402, Clawork, Molt4Hire, Cod3x, ElizaOS/auto.fun, agent.ai (→ HubSpot), x402.org ecosystem page (404).
- Pivoted: Questflow, Theoriq, Payman.
- Not a listing surface: Crossmint, Sentient, Giza, Almanak, Wayfinder, Talus, Morpheus, Bittensor, Solodit, DefiLlama, Composio, LangChain Hub, OpenZeppelin forum.
- Bad value: Futurepedia ($497), aiagentstore ($50, stale traffic), Google Cloud Marketplace/AP2 (enterprise), thirdweb/PayAI/Daydreams discovery (need their facilitator), Remix plugins (PRs don't merge).
