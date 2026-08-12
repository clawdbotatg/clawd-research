# Ethereum LLM eval — landscape research (2026-08-12)

Research for building an "Ethereum eval" — a benchmark of how well LLMs understand
Ethereum (gas, transactions, tooling, esoterica), published Supabase-style with a
leaderboard. Two questions answered here: **how Supabase did it** and **what already
exists for Ethereum** (so we build in the gap, not the crowd).

## 1. How Supabase did it (the model to copy)

Repo: [supabase/evals](https://github.com/supabase/evals) (Apache-2.0, TS monorepo),
announced 2026-08-01 — [blog](https://supabase.com/blog/introducing-supabase-evals) ·
[live leaderboard](https://supabase.com/evals) ·
[X post](https://x.com/supabase/status/2083282155170340898).

- **They eval agents, not raw models.** Real harnesses — Claude Code (Opus 5 /
  Sonnet 5), Codex (GPT-5.6, 5.4-mini), OpenCode (Kimi K3) — run real tasks in
  Docker sandboxes with the real Supabase CLI or against their MCP server. Raw-model
  "executor" configs exist as a baseline tier.
- **Scenario = folder**: `PROMPT.md` (frontmatter: product × topic × stage) +
  `EVAL.ts` (scoring fn) + optional starting project state. Dimensions: Products
  (DB, Auth, Storage, Edge Functions…) × Topics (RLS, migrations, SDK…) × Stages
  (Build / Deploy / Investigate / Resolve).
- **Grading is execution-based first** — SQL checks against resulting state, real
  client calls, function return values; LLM-judge only for semantic leftovers. One
  retry allowed before scoring.
- **Dual suite**: public benchmark suite (breadth, powers leaderboard) + internal
  regression suite (depth, refreshed daily).
- **Every config has a `-no-skills` twin** — the skills A/B is half the content.
  Quotable findings carried the launch: Sonnet 5 78%→100% with skills; Codex reads
  ~8 doc pages/scenario vs ~2 for Claude Code; rewriting one skill *description*
  raised activation ~10%→~60%.
- **Why it landed**: honest self-serving frame ("do agents use our platform
  right"), open source + reproducible, execution-based not vibes, and it doubles
  as marketing for their skills/MCP story. (It flopped on HN — 2 points; the
  distribution was X + tech press.)
- **Rigor gaps to not copy**: no published trial count or temperature; one-retry
  inflates vs pass@1; LLM-judge portion under-documented.

## 2. What already exists for Ethereum (the crowd)

### Solidity code-gen — crowded
- **SolidityBench** (IQ/BrainDAO, HF leaderboard) — spec→contract + HumanEval-for-
  Solidity; stale (late-2024 models). [leaderboard](https://huggingface.co/spaces/braindao/soliditybench-leaderboard)
- **ChainBench** (Circle + OpenZeppelin, 2026-05) — 42 multichain tasks (Solidity,
  Move, Cairo, NEAR Rust), Dockerized, pass@1. [blog](https://www.circle.com/blog/chainbench-an-llm-benchmark-for-multichain-code-generation)
- Academic: SolEval (repo-level, 1,507 samples), SolBench (28,825 fns, differential
  fuzzing), SolContractEval, SmartEval, a second repo-level "SolidityBench"
  (arXiv 2606.19988, name collision).

### Security / audit — the marquee space, taken
- **EVMbench** (OpenAI + Paradigm + OtterSec, 2026-02) — 117 vulns from 40 audits;
  find / exploit / patch. The big one; third-party leaderboards exist; Nethermind's
  AuditAgent posts 67% recall vs Opus 4.6's 47%. [repo](https://github.com/paradigmxyz/evmbench)
- **ScaBench** — rolling real-audit benchmark (555 vulns), dated datasets to dodge
  contamination, actively maintained. [repo](https://github.com/scabench-org/scabench)
- Plus a wave of academic auditors (iAudit F1 91, LLM-SmartAudit, …) and vendor
  head-to-heads (Sherlock).

### Crypto knowledge QA — partially covered
- **DMind Benchmark** — 9 categories MCQ+subjective, 26 models; semi-maintained
  ("leaderboard coming soon" for a year). [repo](https://github.com/DMindAI/DMind-Benchmark)
- **CryptoBench** — 50 fresh expert questions/month (contamination-proof by
  refresh); finding: models fine at retrieval, near-total failure at prediction.
- **CryptoAnalystBench** (Sentient) — 198 open-ended analyst queries, LLM-judged.

### Agentic / onchain-action — emerging
- **EVM-QuestBench** — NL→TypeScript tx scripts executed on a forked chain, state
  validated; dynamic templating defeats memorization. [arXiv 2601.06565]
- **Intent2Tx** — 31k instances from real mainnet traces, differential state
  analysis on forks. [arXiv 2604.27763]
- **TxSum** — transaction summarization for users (lone tx-decoding entry).

## 3. The gap (verified nothing exists)

- **Gas**: no benchmark for gas estimation, intrinsic-gas math, EIP-1559 fee
  mechanics, or gas-golfing.
- **Transaction decoding**: no calldata→explanation leaderboard, no "is this
  signature request malicious" eval, despite agent wallets shipping.
- **EIP esoterica / protocol mechanics**: nothing on 1559/4844/7702 mechanics,
  fork history, opcode semantics, consensus details.
- **Tooling**: zero benchmarks on Foundry/Hardhat/viem/ethers/wagmi/cast usage —
  the biggest practical surface for builders.
- **Deterministic derivations**: nobody tests ABI encoding, RLP, CREATE/CREATE2
  address derivation, EIP-55 checksums, storage-slot computation.
- Also absent: Vyper/Yul/Huff, MEV-as-a-skill, invariant/formal-spec writing.
- **No ecosystem org has shipped one** — not EF, not EthGlobal, not a16z crypto.
  The serious entries came from OpenAI/Paradigm, Circle/OZ, and academia.

**Conclusion: the "esoteric working knowledge" eval — gas + tx anatomy + EIPs +
tooling + deterministic derivations — is exactly the open lane**, and it's the lane
that best matches a builder/educator brand (vs competing with OpenAI on audits).

## 4. Contamination — the key design inversion

Knowledge questions about public Ethereum material are trained-on by definition.
The defense is **novel computation over known primitives**: decode *this* calldata,
derive *this* CREATE2 address, compute the base fee after *these* 5 blocks, name
the storage slot of *this* mapping key. Ground truth is computable (a node, foundry,
or 20 lines of Python), so tasks can be **generated programmatically in unlimited
fresh instances** — the CryptoBench refresh idea, but automated instead of
expert-authored. Pure-recall items (which EIP did X) stay as a minority category
with contamination accepted and disclosed.
