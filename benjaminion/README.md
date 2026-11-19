# Ben Edgington (benjaminion) — podcast prep

Researched 2026-11-19. Podcast is 2026-11-20.

## Who he is

- Ben Edgington, `benjaminion.eth`, [@benjaminion_xyz](https://x.com/benjaminion_xyz), [benjaminion.xyz](https://benjaminion.xyz/).
- Joined Consensys in Oct 2017. Led the PegaSys R&D team. Founded and ran **Teku**, the Consensys consensus client.
- Wrote 100 editions of **"What's New in Eth2"** ([eth2.news](https://eth2.news)), every two weeks for four years up to The Merge.
- Wrote **Upgrading Ethereum**, "the Eth2 Book" ([eth2book.info](https://eth2book.info/)). About 143,000 words, 400 pages. His own site now says he "failed to finish" it.
- Wrote `c-kzg`, part of which went into EIP-4844 (blobs).
- At OP Labs until Feb 2025, working on decentralising OP Stack development.
- Since Jan 2026: working with the Ethereum Foundation on **fast finality**. Also the new moderator of the All Core Devs Consensus call (ACDC).
- Angel investor in Obol (his only one, he says).
- Co-hosted "Mapping Out Eth 2.0" with Christine Kim in 2021.

## What is finality?

A block is **final** when it can never be undone.

Before that point, a block can still be reorged out: your tx was in, and then it isn't. After that point, undoing it would need at least 1/3 of all staked ETH to get slashed (almost 13 million ETH).

As an app dev you already touch this. It is the `finalized` block tag in JSON-RPC. `latest` can reorg. `finalized` cannot.

## Why is it slow today?

Finality needs 2/3 of all stake to vote. That is well over 600,000 votes.

Today those votes are spread over an **epoch**: 32 slots × 12 s = 6.4 min. And it takes **two rounds** (justify, then finalize).

- Best case: 2 × 32 × 12 = 768 s (12.8 min)
- Typical: about 960 s (16 min)

So at any moment, the last 63–95 blocks are not final.

Everyone works around it:

- Exchanges count confirmations.
- Base waits 14 slots (2.8 min) for deposits.
- Arbitrum uses "justified", about 8.5 min sooner than final.
- Circle CCTP: ~15 min normal path, or ~20 s fast path with a fee and a cap.
- One bridge that waits for L1 finality says Base→Arbitrum takes 15–18 min.

## What is fast finality?

The work to get finality from about **1000 seconds to about 10 seconds**.

It is not faster blocks. Slot time (12 s) is a separate effort. Fast finality is "how long until my included tx can never be undone."

Who cares most: bridges, solvers, relayers, L2 deposits. Every minute of waiting is locked capital or reorg risk someone is paid to carry. Faster finality = cheaper, faster bridging.

## What is decoupled consensus?

Today every validator sends **one message** that does two jobs:

1. "This is the head of the chain" (fork choice, LMD-GHOST)
2. "I vote to finalize this checkpoint" (Casper FFG)

Because they ride in one message, finality is stuck on the slot/epoch clock.

**Decoupled consensus ([EIP-8453](https://github.com/ethereum/EIPs/pull/12566)) splits it into two messages on two clocks:**

| | Head vote | Finality vote |
|---|---|---|
| Job | pick the next block | make old blocks permanent |
| Who | small committee, ~512 validators per slot | all validators |
| Clock | every slot | its own rounds, not tied to epochs |

What that buys:

- Finality votes can flow all the time and use bandwidth that sits idle today.
- Finality goes as fast as votes arrive, not at epoch edges.
- Head voting needs only ~512 signatures per slot instead of ~30,000, which helps shorter slots later.
- The head rule only counts recent votes, so attackers can't save up old votes and dump them.
- Leaves room to swap in post-quantum signatures later.

First target: **4x faster, ~16 min → ~4 min.** Then more steps on top, one fork at a time. Ben's math: four steps at ~3x each gets close to 100x.

His line: past attempts (single-slot finality, three-slot finality) "required that we solve *everything* before we can solve *anything*." Decoupling is the small first step that unlocks the rest.

## Where it stands

- EIP-8453 opened 2026-10-21. Draft. Many parts still TBD (rewards, inactivity leak, fork transition, safety proofs).
- Authors: Francesco D'Amato, Roberto Saltini, Yann Vonlanthen, Mikhail Kalinin, Ben Edgington.
- A proof of concept this week on ethPandaOps' 1000-node testbed showed the 4x.
- Not scheduled. It is a stretch-goal candidate for the `I*` fork, likely 2027–28.

## The later steps (candidates, not a plan)

- **Validator consolidation.** Big operators merge their 32 ETH validators (up to 64 into one since Electra). Fewer votes to collect.
- **Rotation (Orbit-style).** Only a subset votes on finality at a time. No one is kicked out.
- **Better networking and aggregation.** Batch votes at the source. SNARK aggregation.
- **One-round finality.** Almost halves the time. But safety drops from 33% to about 17–20% bad stake.

## What he found asking the ecosystem (July 2026)

He did 19 interviews: L2s, bridges, payments, wallets, stakers, client teams.

- **Tens of seconds is enough.** Nobody needs one second. Quote: "Ethereum doesn't need to get to one second. It just needs to not be 18 minutes."
- 10–20 s is the sweet spot for bridges. 1–3 min is fine for most L2s.
- Point of sale needs 1–3 s. L1 will never do that. That is for L2s and preconfirmations.
- Institutions don't care much. Loans settle in 10–30 days.
- **Don't copy fast alt-L1s.** An L2 said: "we would rather you not do the 'move fast and break things' thing."
- **One-round finality has weak support.** Coinbase, Lido, or a client bug could reach 17–20%.
- People would rather finality pause more easily than be less safe, as long as blocks keep coming.
- Split on validator count: some bridge/gaming people are fine with 1,000–2,000 validators. Client teams and stakers defend home stakers hard.
- He used ChatGPT 5.5 to code the interviews to cut his own bias.
- He could not get any real solver to give cost numbers.

## Questions to ask him

1. For an app dev: what changes for me the day this ships? Does `finalized` just get 4x closer?
2. 4 minutes is nice, but bridges want 10–20 s. Which step after decoupling gets the biggest cut?
3. The ~512 head-vote committee: isn't that a small DoS target? How is it picked privately?
4. One-round finality: is 17% ever OK? What would have to be true?
5. Is there a point where home stakers and fast finality can't both win?
6. How does this relate to Lean Ethereum / Minimmit / the strawmap? Same road or a different one?
7. Does it fit with the fast confirmation rule (~13 s), or replace it?
8. What happens to the inactivity leak?
9. Why was post-quantum the first reason listed in the EIP?
10. Why didn't the book get finished? Will it?
11. Teku → OP Labs → back to L1. What did the L2 time teach him?
12. What's it like running ACDC?
13. Glamsterdam's Hoodi fork just got delayed. Does that push `I*` and fast finality too?

## Sources

- [benjaminion.xyz](https://benjaminion.xyz/)
- [Upgrading Finality 1: Decoupling Consensus](https://consensus.ethereum.foundation/blog/upgrading-finality-edition-1) (May 2026)
- [Upgrading Finality 2: What the Ecosystem Told Us](https://consensus.ethereum.foundation/blog/upgrading-finality-edition-2) (July 2026)
- [Stakeholder research report](https://consensus.ethereum.foundation/articles/stakeholder-research)
- [EIP-8453 PR](https://github.com/ethereum/EIPs/pull/12566), [discussion](https://ethereum-magicians.org/t/eip-8453-decoupled-consensus/30045), [spec branch](https://github.com/ethereum/consensus-specs/tree/decoupled-consensus/specs/_features/dc)
- [Christine Kim interview](https://christinedkim.substack.com/p/acde-248) (Oct 2026, video — not watched, only the summary read)
- [Vitalik on the strawmap](https://x.com/VitalikButerin/status/2026779557479723418)
- [leanroadmap.org](https://leanroadmap.org/)
