# Deepstate research — agent handoff

*Written 2026-08-19 ~17:20 PT. Read this first; it's the map to everything else.
Audience: a future session picking up any thread of this work.*

## Why this exists

Austin interviews **Joseph DeLong** ("Joe") on his podcast **Friday 2026-08-21**
about **Deepstate** (deepstate.sh) — DeLong's fully-onchain CLOB DEX on Robinhood
Chain. Research grew three branches: (1) podcast prep, (2) an independent audit
Austin commissioned, (3) a maker-bot plan to acquire DEEP. All three have open
ends; see "Open threads" at the bottom.

## Files in this folder

- **`RESEARCH.md`** — the full deep-dive: protocol mechanics, DeLong bio, Robinhood
  Chain context, tokenomics, risks, 10 prepared podcast questions, all sources,
  live contract addresses, traction quotes, community framing.
- **`MAKER-BOT-SPEC.md`** — how to earn DEEP by market-making: live onchain math,
  emission/quantity-ramp tables, competition analysis, bot architecture, the
  atomic claim-and-dump variant, compliance caveats.
- **`HANDOFF.md`** — this file.

## Published artifacts (claude.ai, Austin's account)

- **Deepstate Briefing** (favicon 🎙): https://claude.ai/code/artifact/d7345c7b-fe9a-4145-9766-b9804d2af944
  — polished podcast-prep page: guest arc, venue, mechanism diagram, tokens,
  risks, 10 questions, live addresses, traction stats.
- **Deepstate ELI5** (favicon 📚): https://claude.ai/code/artifact/439dfc62-416d-4b6c-b082-57a193a98aa7
  — plain-English study guide: analogies, numbers-to-memorize table, "five
  things to remember."
- To update either from a NEW session: pass its URL as `url` to the Artifact
  tool (publishing without `url` forks a new artifact).

## The 60-second recap

Deepstate = price-time-priority order book entirely in contracts (orders packed
into single 32-byte words in a radix tree, bounded gas; lineage = Joseph Poon's
"Warp", which Austin saw presented at SBC '23). First market NVDA/USDG. Only
best-bid + best-ask earn DEEP ("pays for aggression, not depth"); DEEP burns
one-way into STATE (ERC-4626 vault = governance + fee claims). 1B DEEP over 395
days, 50/50 per side, zero founder allocation, contracts non-upgradeable, no
governance timelock. The NVDA token is a Jersey-issued debt IOU from a Robinhood
subsidiary, not offered to US persons — enforced at interface level only.
DeLong: ex-Sushi CTO (Dec 2021 meltdown resignation), Astaria, Kraken, now
Colossus CEO; Deepstate is his side project. Launch traction: $50k → $2.5M/18h →
$10M/24h.

## Hard-won operational knowledge (don't re-derive)

### Chain access
- **Alchemy serves Robinhood Chain**: slug `robinhood-mainnet`
  (`https://robinhood-mainnet.g.alchemy.com/v2/$KEY`), **chainId 4663 (0x1237)**.
  Probed slugs `rhc-mainnet`/`robinhoodchain-mainnet` are dead.
- A working `ALCHEMY_API_KEY` lives in **`~/clawd/enslookup/.env`** (also serves
  Base). Per Austin's global rules: never public RPCs.
- Robinhood Chain: Arbitrum Orbit L2, 100ms blocks, ETH gas, **FCFS sequencing**
  (no gas-priority queue jumping — this is why DeLong chose it; time priority
  holds). Block height was ~40.94M on 2026-08-19.
- `cast` (foundry 1.7.1) is installed and works against it.

### Contract addresses (Robinhood Chain, from DeLong's launch tweet, verified live)
- DEEP `0x1DA24f6Bb623b9d1aFEae3F3146659A2662D6d27`
- STATE Vault `0xbfb7b3Ff3D498a559b946B836d26F0E168f273D5`
- Governor `0x3DC3b787EBDC78bf916f4e30195C61c764C111Ff`
- **Order book (DeepstateV1)** `0x6cf19308C22FC82ea620Fa0B3E94948d20f27B96` —
  DeLong's tweet labeled this "Router" but `Rewarder.deepstate()` points here;
  it IS the book. `topOrder(bookId,bool)` works on it.
- Rewarder `0xE85ADBC03a6b52a2c9894c1BB525eC883ea156D7`
- USDG `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` (**6 decimals**, = token0)
- NVDA `0xd0601CE157Db5bdC3162BbaC2a2C8aF5320D9EEC` (18 decimals, = token1)
- Pool ID `0x42819cadfbb25aab80543236e280fba4e61aa61e0b5b777541de54ae69da35e4`
  (= keccak256(token0,token1)); active bookId (epoch-scoped) was
  `0xdf941c235503a5d2e67aee5dea00f2965f99421c0d034bd77f924c05c66bf399`.

### Source code
- GitHub org `Deepstate-Protocol`; **the book is in `deepstate-contracts`**
  (`src/DeepstateV1.sol`, ~3,400 lines) but **the Rewarder/Vault/Token/Governor
  are in the separate `deepstate-protocol` repo** (`src/DeepstateRewarder.sol`
  etc.). Clone both; scratchpad clones from this session are gone.
- Rewarder mechanics (verified in source): per-side cap 500M DEEP, duration
  395d; cumulative emissions `cap·ln(1+t/30d)/ln(1+395d/30d)`; full-reward
  quantity ramps geometrically over 30 days (bid 1→1,000,000 USDG; ask
  1→5,000 NVDA) then freezes at max forever; sub-target size earns linearly.
- **Claim flow trap**: the engine deletes order ownership on cancel/fill —
  call `Rewarder.registerClaimant(bookId, order)` while the order is LIVE or
  rewards become unclaimable. Collect via `distributeRewardsBatch`.
- **Settlement is pull-based**: taker fills credit proceeds inside DeepstateV1;
  `cancel(token0,token1,epoch,order)` both cancels AND claims proceeds. This is
  what enables the atomic claim-and-dump (never hold NVDA across a tx boundary).
- Useful event topic: `RewardsDistributed(bytes32,bytes32,address,address,uint256)`
  = `0x68328323bbb12cd4e9d6680575d0d8a5b45dd89313479ba6efea4fb1a9205f23` on the
  Rewarder (params non-indexed; owner = 4th word of data).

### Verification pass (2026-08-20, second model/session)

All load-bearing claims were independently re-verified: emission math matches
the contract's own `fullRewardQuantityAt`/`cumulativeEmissionsAt` to 3+ digits;
decimals confirmed onchain (USDG 6 / NVDA 18 / DEEP 18); event recount matches
the rewarder's balance drawdown to 0.001%; pull-based settlement, the
registerClaimant trap, and the 100bps integrator cap confirmed in source.
**One new trap found:** contract `isBid=true` = buying token0 (USDG) — inverted
from human NVDA terms; bot must place `isBid=false` to bid for NVDA. See
MAKER-BOT-SPEC.md §3b. Competition drifted: dominant bot 51.0% (was 54.9%),
58.2M DEEP distributed, 179 claimants.

### Live economics snapshot (2026-08-19, day 4.7 of 395)
- Emissions ~5.44M DEEP/day/side and falling; 94–98% of ceiling actually accrued
  (top-of-book near-continuously held).
- 51.8M DEEP distributed to **177 claimants**; **`0x2acb…0706` has 54.9%**
  (dominant latency bot). Top bid was $105k USDG, top ask 28.2 NVDA.
- **The strategic clock: full-reward quantity hits $1M/side on ~Sep 14** (day
  30). Small-player window ≈ two weeks from launch. Tables in MAKER-BOT-SPEC.md.
- DEEP has **no market price**; only fundamental floor is STATE's claim on
  vault fees (~$10k/day at $10M/day volume).

### The audit (open thread)
- Austin commissioned **One Dollar Audit #693** of `DeepstateV1.sol`.
- **TWO links, use the second one:**
  - Status page (coarse stage only): https://www.onedollaraudit.com/audit/693
  - **Work log with actual findings: https://leftclaw.services/jobs/693** ← this
    one. The `onedollaraudit` front page hides the findings behind a stage
    string; the leftclaw job page shows the running work log and prelim results.
- Both pages are JS SPAs — curl gets a placeholder; read with a real browser
  (clawd-browser MCP). **Stage state ALSO lives onchain on Base**: Multicall3 →
  registry `0xb2fb486a9569ad2c97d9c73936b46ef7fdaa413a`, selector `0xbf22c457` +
  uint256(693). Poll via Alchemy Base to detect changes cheaply (that's what the
  Monitor watchers did — but the onchain struct only flips on stage change, so
  it can sit still for hours mid-phase; the leftclaw work log updates sooner).
- Job facts: executor `0xEE8f…377c`, paid 164,772 CLAWD (~$1.02), client
  austingriffith.eth. It sized the target correctly: "3390-LOC CLOB DEX, custom
  Patricia-trie order book," 7 opus domain agents.
- Progress: `accepted` (16:23) → `phase-0-context` → `phase-1-ethskills`
  (16:50) → Phase 1 breadth complete (18:26) → **Phase 2 (pashov-depth, blind)
  running** at last check ~18:40.
- **Preliminary findings (18:26, NOT final):** 2 High — (1) pooled-balance
  fee-on-transfer drain, (2) uint160 quantity-ceiling DoS; 3 Medium — fee
  front-run, fee-recipient DoS, hook gas cost; ~12 Low, 9 Info. Full list +
  a cross-check note is in RESEARCH.md under "Independent audit."
- **TODO when final:** append final severities to RESEARCH.md; check whether the
  2 Highs are genuinely new or overlap Deepstate's own published accepted
  fee-on-transfer findings (theirs were about the VAULT; a drain on the BOOK's
  pooled balances would be new surface). Good podcast material either way.

## Compliance flag (unresolved, blocks the bot)

Austin is presumably a US person; NVDA stock tokens are explicitly not offered
to US persons (Reg-S-style, interface-enforced). Bid-side market making fills
into NVDA. The atomic claim-and-dump variant reduces holding to sub-second and
market risk to ~zero, but a fill is still an acquisition — mitigation, not safe
harbor. Austin was advised to get a real legal read before funding anything.
**Do not deploy or fund a bot without Austin explicitly deciding this.**

## Open threads, in priority order

1. **Audit #693 final findings** → append to RESEARCH.md (+ mention in artifacts
   if material). Preliminary already logged (2 High / 3 Med). Check
   https://leftclaw.services/jobs/693 for the finished report; Phase 2 was still
   running at last check.
2. **Podcast Friday 2026-08-21** — prep is done (briefing + ELI5 artifacts +
   10 questions in RESEARCH.md). Best hooks: Sushi-scars → governance design;
   SBC/Warp personal connection; "aggression not depth"; PFOF irony of
   integrator fees; the US-person fence question; atomic-dump hypothetical.
3. **Maker bot** — specced, not built. Blocked on Austin's compliance/sizing
   call. If green-lit: helper contract (claimAndDump) + bid-quoting bot +
   registerClaimant flow ≈ a day of work. **Every day of delay costs reward
   share; window effectively closes ~Sep 5–14.**
4. (Idea, unprioritized) Post-podcast: verify DeLong claims made on air against
   this research; publish anything interesting.

## Memory

`deepstate-podcast.md` in the auto-memory dir points here. Repo = the canonical
store; memory = the pointer. Update both if scope shifts.
