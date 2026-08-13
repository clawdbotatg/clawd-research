# eth-eval — build plan (2026-08-12)

Working name: **eth-eval** (naming candidates: `evm-iq`, `gwei-bench`, `ethbench`,
**esoterica** — Austin likes this one; see domain status below).

## Domain: esoteri.ca (checked 2026-08-12)

Registered 2020, **expired 2026-06-24, now in `redemptionPeriod`/`pendingDelete`**
(serverHold, no DNS — site dark). Unless the owner redeems, it drops into CIRA's
weekly Wednesday **TBR (To-Be-Released)** pool within ~2–6 weeks — grab it via a
.ca backorder at a CIRA-certified registrar (GoDaddy CA, Sibername, …).
**Catch: CIRA's Canadian Presence Requirement** — registrant must be a Canadian
citizen/resident, Canadian corporation, or hold a registered *Canadian* trademark;
no trustee loophole. Needs a Canadian friend/entity or a CA trademark before a
backorder is worth paying for. Fallbacks: `esoterica.eth`, `esoterica.dev`.
Thesis: measure the **esoteric working knowledge** of Ethereum that no benchmark
covers — gas mechanics, transaction anatomy, EIP mechanics, tooling (foundry/viem/
wagmi/cast), and deterministic derivations — and publish it Supabase-style with a
leaderboard. See `LANDSCAPE.md` for why this lane is open.

## Positioning

- **Don't compete** with EVMbench (audits) or ChainBench (codegen). Complement them:
  "can this model actually *work* in the Ethereum stack" vs "can it audit/write
  contracts."
- The headline artifact is a **leaderboard + quotable findings** ("every frontier
  model gets EIP-1559 refund math wrong", "X is the only model that knows viem v3").
  Supabase's launch worked because the findings were tweetable, the repo was open,
  and grading was execution-based — copy all three.
- Natural brand fit: builder/educator angle (SpeedRunEthereum / BuidlGuidl adjacency)
  rather than a security-vendor angle.

## Architecture: three tracks, shipped in order

### Track 1 — Knowledge & computation (v0, days) ✅ start here
Fork the **simple-eval** bones (`clawd-research/simple-eval`: stdlib-only runner,
JSONL tasks, deterministic graders, bootstrap CI, leaderboard script — already
proven on 4 models). New repo, fresh `results/`.

Categories (~10–15 tasks each to start, ~120 total):

| category | example task | grader |
|---|---|---|
| `gas-mechanics` | intrinsic gas of this tx (calldata zero/nonzero bytes); base fee after N blocks at given fullness; effective priority fee w/ maxFee cap | bigint |
| `tx-anatomy` | decode this raw signed tx (type, nonce, to, value); what does blob tx type 3 carry; legacy vs 1559 field diff | json |
| `calldata` | decode this calldata against this ABI → function + args; encode this call | json / exact |
| `derivations` | CREATE/CREATE2 address; EIP-55 checksum; storage slot of `mapping(addr=>uint)[k]`; event topic0 | exact (case-sensitive) |
| `eip-esoterica` | 7702 delegation mechanics; 4844 blob fee market; what changed in each fork; opcode gas/semantics (SSTORE refunds, warm/cold) | exact / regex / numeric |
| `tooling` | the cast command that does X; foundry.toml/fork-test idioms; viem vs ethers API mapping; wagmi hooks; hardhat→foundry translation | regex / pycheck / json |
| `units` | wei/gwei/ether math at full precision; token decimals math | bigint |
| `wallet-safety` | is this signature request / approval calldata dangerous, and why | json (classify + reason substring) |
| `recall` (minority) | which EIP introduced X; fork ordering | exact — contamination accepted & disclosed |

Harness changes needed (all small, identified in the simple-eval review):
1. **`bigint` grader** — exact integer compare incl. hex forms; current `numeric`
   parses `0x1a2b`→0 and rounds wei above 2^53.
2. **`exact` case-sensitive by default in `derivations`** (EIP-55 casing is the answer).
3. **Per-task context docs** — `{{DOC:eip1559}}` style, ~5-line change in `load_tasks`.
4. Optional: `any_of` matcher for multi-phrasing answers.

**Task generators, not hand-written tasks** (the contamination defense): a
`gen/` dir of Python generators that use `eth-utils`/`eth-abi`/a local script to
compute ground truth for randomized instances (random ABIs → calldata, random
init-code hashes → CREATE2, random block sequences → base fees). Hand-write the
esoterica/tooling/recall items; generate the computational ones. Regenerate a
fresh instance-set per release → nothing to memorize. `--self-test` (grade the
reference answers) stays the guard.

### Track 2 — Execution track (v1, ~weeks)
Tasks graded by **running the model's answer against a real chain**:
- Model writes a `cast`/`viem` invocation or short script; we execute in a sandbox
  against a **forked mainnet (Alchemy — never public RPCs, per house rules)** and
  check resulting state / output. EVM-QuestBench proved the pattern; ours aims at
  builder tasks (read a storage slot, simulate this swap, estimate gas within X%).
- Solidity micro-tasks graded by `forge test` in a temp project (needs the
  sandboxed-execution work the simple-eval review flagged — model code currently
  runs with runner privileges; Docker it).

### Track 3 — Agent-harness track + leaderboard site (v2)
The full Supabase move: run **Claude Code / Codex / OpenCode** (we already own a
fleet of harness-driven Claude sessions — this is our home turf) on real tasks in
scaffold-eth / foundry repos: "add a withdraw function + test", "debug this failing
fork test", "wire this contract into the frontend with wagmi". Execution-graded.
Publish a static leaderboard site (charts + per-run drilldowns) and the writeup.
Optional skills A/B: does an `ethereum` / `scaffold-eth` skill close the gap for
cheaper models — that finding *is* the marketing for a skills repo, exactly like
supabase/agent-skills.

## Running models

- v0 via the existing simple-eval targets: OpenAI-compatible endpoints (bankr
  gateway reaches ~41 models — instant breadth) + `CmdTarget` for claude/codex
  CLIs. temperature 0, N≥3 runs; **publish N and temperature** (Supabase didn't —
  a cheap rigor win), report pass@1 with the existing bootstrap CI.
- Cost is trivial for Track 1 (short prompts, short answers, deterministic
  grading, zero judge tokens).

## Publish plan

1. Repo public under clawdbotatg (Apache-2.0 like supabase/evals).
2. Leaderboard: start as README table from `report.py`, graduate to a static site.
3. Launch content: the chart + 3–5 quotable failure findings + "here's the best
   model for Ethereum work" framing. X first (HN didn't work for Supabase).
4. Cadence: re-run on new model releases; regenerate computational instances per
   release (dated instance-sets, ScaBench-style).

## Open questions for Austin

- Name / brand: standalone or under a BuidlGuidl/SRE umbrella?
- Scope of v0 model list: bankr's 41 + the CLI harnesses, or a curated ~10?
- Wallet-safety category: keep in v0 or hold for a dedicated release (it's the
  most headline-y and there's *no* competing eval)?

## Next actions (v0)

1. Scaffold `eth-eval/` repo from simple-eval; add `bigint` grader + per-task docs.
2. Write generators: calldata, derivations, gas-math, units (~60 generated tasks).
3. Hand-write esoterica + tooling + tx-anatomy + recall (~60 tasks).
4. `--self-test` green → run the model sweep → `report.py` leaderboard → writeup.
