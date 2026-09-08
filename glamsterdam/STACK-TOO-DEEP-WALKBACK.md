# "Stack too deep" walk-back (checked 2026-09-08)

Context: Austin tweeted 2026-08-27 that the next Ethereum fork "lets compilers
fix stack too deep" (https://x.com/austingriffith/status/2092988619707584726,
83K views). Nomic shipped slang-solx on 2026-09-07 and said it already avoids
the error with no new opcodes (https://x.com/NomicFoundation/status/2097011670862254582).
This doc is the fact base for a correction tweet.

## The one-line truth

The fork does not "let compilers" fix it. Compilers can already fix it. The
fork gives **solc's legacy pipeline** (the default everyone runs) a cheap way
to reach deep stack slots without rewriting its codegen. Everyone else
already solved it in software by spilling variables to memory.

## Who already kills the error today, without EIP-8024

| Compiler | How | Status |
|---|---|---|
| **Vyper** | All locals live in memory by default; stack only for expression temps. Never had the error. | Shipping for years |
| **solc `--via-ir`** | Yul pipeline "can move local variables from stack to memory to avoid stack-too-deep errors" (docs, assembly.rst). Only if inline asm is `memory-safe`. Still fails in some cases. | Shipping since ~0.8.13 |
| **solc `--via-ssa-cfg`** (experimental) | New backend spills "on demand in the stack scheduling phase" (Argot roadmap 2026-07-01). Changelog 0.8.36: "can now spill stack values to memory to avoid stack-too-deep errors." | 0.8.35 opt-in (2026-04-29); stabilizing H2 2026 |
| **slang-solx** (Nomic / ex-Matter Labs solx) | LLVM register allocator spills to a memory spill area "only when strictly necessary"; solc front-end, LLVM back-end. Skips Yul optimizer entirely. | Hardhat plugin released 2026-09-07 |

Source for the Vyper/solc mechanism: frangio, "Spilling in the EVM"
(https://frang.io/blog/spilling-in-evm/, 2025-02-19): "In both compilers the
issue is addressed by statically allocating memory for variables." Solidity
puts vars on the stack and moves unreachable ones to memory; Vyper puts them
all in memory and promotes some to the stack. Cost: those functions can't be
recursive/reentrant.

## slang-solx facts (Nomic blog, Patricio Palladino, 2026-09-07)

https://blog.nomic.foundation/announcing-slang-solx-a-solidity-compiler-thats-up-to-5x-faster/
Hardhat cookbook: https://hardhat.org/docs/cookbook/compiling-with-slang-solx

- "1.7x faster than solc in legacy mode and roughly 5x faster than solc in
  via-IR mode." Nine repos via-IR: solc 749s total, slang-solx 151s. Best
  single repo 10.6x (graph-horizon 285s -> 27s). Solady 6.2x, Uniswap v4
  6.0x, OpenZeppelin 5.1x, Aave v4 3.2x.
- Stack too deep: "it doesn't result in 'stack too deep' errors in 99.85% of
  test cases." Blog does not name the test set or the 0.15%.
- Separate compile-compat figure: 112,587 Sourcify contracts (0.8.34, evm >=
  cancun), 99.56% compile without issues.
- Lineage: "originally developed for several years at Matter Labs under the
  name solx." zksolc 2021; solx 0.1 alpha July 2025; Nomic began taking over
  late 2025; takeover finalized July 2026 with the remaining Matter Labs
  engineers joining Nomic.
- Mechanism (from Matter Labs/Cyfrin material, not the Nomic blog): LLVM
  spills "variables to memory only when strictly necessary." Limits: no
  spilling inside recursive functions; spilling is disabled for the whole
  contract if any inline assembly isn't marked `memory-safe`.
- Matter Labs' claim (Paragraph, 2025): "fixes solc's notorious stack-too-deep
  failure without altering contract semantics." solc via-IR by contrast can
  reorder evaluation (Cyfrin's `++a + a` example).
- Caveats: **"not safe for mainnet deployments"**, hardening "hasn't started
  yet." Solidity 0.8.34 only. Hardhat 3 only, only in a `slang-solx` build
  profile (using it in `default`/`production` is a validation error unless
  you set `dangerouslyAllowSlangSolxInProduction: true`). EVM targets
  cancun/prague/osaka. `viaIR: true` changes nothing but the metadata hash.
  Foundry: works via `solc = "/path/to/solx"`; linking not fully supported.
- Roadmap: `slang` = full compiler (solc-independent, multithreaded),
  `slang-frontend` = the old Slang parser lib, `slang-solx` = this. Zero-solc
  compiler "targeting an initial release by the end of this year." Mainnet
  hardening after that.
- Nomic's thread credits @the_matter_labs for starting solx.

## What EIP-8024 actually does and who wanted it

Spec: https://eips.ethereum.org/EIPS/eip-8024 (status: Review; SFI in
Glamsterdam per EIP-7773). DUPN 0xe6, SWAPN 0xe7, EXCHANGE 0xe8, 3 gas each.
Reach depth 17-235.

- EIP motivation, verbatim: memory spilling / "stack to memory elevation" in a
  compiler "can result in complex and inefficient code." So: the opcodes are a
  gas + simplicity win, not the only fix.
- frangio (author, Magicians thread 2025-12-17): "solc hasn't been able to
  solve it yet, and we can't wait forever." "This error is not acceptable in
  what should by now be a mature tech stack." He also says SWAPN/DUPN "will
  eventually make the need for spilling a lot less pressing."
- chfast (author): EXCHANGE alone would eliminate 16.2% of SWAP instructions
  in a ~2,720-block mainnet sample, saving 16.2% of that gas.
- **charles-cooper (Vyper) opposed it**: "Vyper does not have the
  stack-too-deep problem." "adding more opcodes to the VM is solving an
  application level problem at the VM level." "Maybe try a different language
  or compiler, which does solve it!" Also: "EIP-8024 also only pushes the
  problem out" (still need spilling past 235). norswap seconded.
- Geth's ranking: "provides a way to solve the 'stack too deep' issue for
  compiler authors, while maintaining the ability to use the stack for
  storing variables." That last clause is the real point.
  https://notes.ethereum.org/@fjl/geth-glamsterdam-eip-ranking
- Thread: https://ethereum-magicians.org/t/eip-8024-backward-compatible-swapn-dupn-exchange/25486

## solc adoption of EIP-8024: not merged

- PR #16424 "Implement EIP-8024 in legacy codegen" (frangio, 2026-01-27):
  **closed, unmerged**. Note: "Evmone doesn't implement this EIP yet."
- PR #16872 "Introduce support for SWAPN, DUPN opcodes according to the EIP
  8024" (rodiazet, 2026-07-16): **open, review required**, not merged as of
  2026-09-08. EXCHANGE not in the title.
- Argot roadmap 2026-07-01 lists "SWAPN/DUPN support for Glamsterdam" as in
  progress and "Glamsterdam support" as a Q3/Q4 item. Main H2 focus is
  stabilizing SSA-CFG out of `--experimental`.
- solc 0.8.37 (unreleased) changelog has Amsterdam `block.slotnum` but no
  8024 line yet.
- So even when Glamsterdam ships (~Q4 2026, no date), legacy solc will not
  emit these opcodes until a release lands them, and you'd have to target
  `evmVersion: glamsterdam`.

## What was wrong / right in the 08-27 tweet

- "the ability to deploy larger contracts": **right** (EIP-7954, 24->64 KiB).
- "lets compilers fix stack too deep": **overclaims**. Compilers already
  can; the fork mainly lets *solc's default pipeline* do it cheaply, and solc
  hasn't merged support yet. Vyper, via-IR, SSA-CFG and slang-solx all do it
  in software today.
- "eth dev is going to rip in Q4": fine as vibes; the more immediate rip is
  the compiler race (slang-solx 5x faster today, solc SSA-CFG stabilizing).

## Tweet drafts (Austin voice)

**A. short correction + prop**

> correction on my "the next hardfork kills stack too deep" post
>
> the fork (EIP-8024) gives *solc* new opcodes so its default pipeline can reach deeper in the stack
>
> but other compilers already kill it in software by spilling to memory. vyper never had it. and @NomicFoundation just shipped slang-solx for hardhat: no stack too deep in 99.85% of tests and 5x faster than via-ir
>
> the fork helps. the compilers were already fixing it.

**B. thread opener, more voice**

> I was wrong-ish about stack too deep
>
> said the next @ethereum fork "lets compilers fix it"
>
> more honest: it lets THE compiler (solc, legacy mode) fix it with new opcodes. everyone else already did it without them
>
> - vyper: never had the bug, locals live in memory
> - solc --via-ir: moves vars to memory, has for years
> - solc's new ssa-cfg backend: spills on demand (experimental in 0.8.35+)
> - slang-solx from @NomicFoundation: LLVM does the spilling, 99.85% no error, 5x faster than via-ir, shipped yesterday
>
> the opcodes are still good (3 gas, keep vars on the stack) but solc hasn't even merged them yet
>
> the real story is the compiler race, not the fork

**C. one-liner quote-tweet of Nomic**

> this is the actual stack too deep fix. no hardfork needed. the new opcodes in glamsterdam mostly help solc's default pipeline catch up to what LLVM already does here

Notes for whichever you post:
- Don't say "hardhat compiler." It's slang-solx, a compiler backend, used
  through a Hardhat plugin. Nomic also says it's not mainnet-safe yet.
- If you say "5x", say "vs via-ir." Legacy mode is 1.7x.
- The 99.85% is Nomic's number on their own test set; the blog doesn't say
  what the set is.
