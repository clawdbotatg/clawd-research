# Levanto Sage — complete use-case inventory + our own

*Part 1 is every example Levanto publishes (marketing site + all doc pages + their agent skill file), collected 2026-07-28. Part 2 is examples they don't list — invented for clawd-harness, slop computer, and how Austin actually works.*

---

## Part 1 — Every example THEY list

### Category framing (docs `use-cases.md`)
Five buckets: **Agentic workflows** (routing/branching/escalation as the "decision layer for agents"), **Operations** (triage across DevOps/SecOps/customer support), **Agentic guardrails** (check tool calls & responses on the hot path), **Content screening & moderation** (tag/rank/score/sort; abuse flagging, policy-risk severity), **Risk & fraud** (transactions, asset trades, agentic actions like refunds).

### Concrete examples, by decision kind

**yesno**
1. *Compliance gate* — marketing email promising "guaranteed 40% returns," "risk-free" → "Does this copy require compliance review before send?" (their canonical example, everywhere)
2. *Agent pause-before-send* — agent drafted an all-staff email saying "I quit, effective immediately" when the user only asked to mention an afternoon absence → "Should the agent pause and ask you before sending this email?" (marketing site)
3. *Tool-call blocking* — agent proposes an $800 refund to an external bank account; policy allows $50 max, internal only → "Given the system policy above, must this tool call be blocked?" (marketing site)
4. *Grounded recency check* — "Has there been a major Cloudflare incident this month?" with `low_confidence` web-search grounding (grounding doc)
5. *Marketplace policy* — post "Selling verified Instagram accounts, DM for bulk pricing" → "Does this post violate marketplace policy?" (batch doc)

**choice**
6. *LLM model routing* — "Route this prompt to the cheapest model that can still answer it well" over gpt-5.6-luna / -terra / -sol (marketing site — they explicitly pitch **model routing**, Austin's instinct was on their roadmap)
7. *Department routing* — "Which department should own this message first?" → billing / technical_support / customer_success / sales (marketing site)
8. *Sentiment* — mixed review (praises product, rough onboarding) → positive / neutral / negative / mixed (marketing site)
9. *Contract disposition* — an MSA with auto-renewal + 90-day termination clause → approve / revise / reject / escalate for legal (choice doc)

**scale (always 0–4)**
10. *Ticket urgency* — "Checkout returns a 500 for about 10% of EU customers" → 0 cosmetic … 4 critical (marketing site)
11. *Interview scoring* — candidate explained roadmap well, struggled on DB scaling → 0 not-qualified … 4 strong-hire; expectation 2.4 (scale doc)
12. *Content harm level* — the Instagram-accounts post → 0 no harm … 4 active scam (batch doc)

**sort**
13. *Support triage* — {DB unreachable, double-charged $299 invoice, slow login, FAQ typo, Enterprise pricing question} → by operational urgency (marketing + sort doc)
14. *Crypto asset ranking* — ETH/BTC/SOL/ARB/DOGE with RSI/MACD/divergence signals → "rank best to worst short-term buy" (marketing site)

**tags**
15. *Moderation* — "Buy cheap followers now!!! click here → bit.ly/deal" → {spam, promotion, scam_or_fraud, safe} with thresholds (marketing + tags doc)

**batch**
16. One content, many questions — the marketplace post scored for policy_violation (yesno) *and* harm_level (scale) in one call (batch doc)

---

## Part 2 — Examples they DON'T list (ours)

Rule of thumb applied throughout, from our benchmarks: **phrase as `yesno` and threshold on probability** (well-calibrated, 0.04–0.94 spread) rather than `choice` (confidence saturates at ~1.00 even when wrong). Sage earns its ~$0.0005/decision only where **~300ms inline latency + a thresholdable probability** matter; anything bulk/offline goes to qwen-class models at 1/75th the price.

### clawd-harness (session manager / fleet)

1. **Notification-worthiness gate** *(yesno — the single best fit in our stack)*. Every Stop hook carries `last_assistant_message`. Ask: "Does this completed turn need the human's attention now — a question for them, a blocker, a failure, or a finished deliverable?" p≥0.9 → PushNotification to Austin's phone; p≤0.3 → silent; middle → badge only. Kills notification fatigue across N fleet machines for ~$0.0005 per turn-end, and the probability threshold *is* the sensitivity knob.
2. **Idle-session triage** *(sort)*. The future AI-controller sweep: hand Sage the last-message snippets of all idle sessions → "sort by how much they need human attention." The fleet UI's session rung renders pre-ordered. One batch call, list-level confidence tells us when the ordering is a coin flip.
3. **Wedged-session detector** *(yesno)*. Over the last ~20 PTY lines: "Is this session stuck waiting on interactive input (login prompt, y/N confirm, pager, menu)?" The harness's regex approaches can't cover the long tail of TUI states; a 300ms classifier can, and it drives auto-keypress or an alert.
4. **Limit-banner second opinion** *(yesno)*. `_scan_for_limit` is regex over a noisy ANSI stream. Before triggering an account handoff + prompt redelivery (expensive, disruptive), confirm: "Does this terminal output show the CLI refusing due to a usage limit?" Cuts false handoffs; 300ms is nothing next to a handoff.
5. **Subscription-tier routing at send time** *(yesno — demoed in RESULTS.md)*. "Does this prompt need a frontier-tier model?" → route to the hot Opus pool vs a cheap path. Only worth it because the tiers being routed between are expensive; the router pays for itself on the first downgraded prompt.
6. **Turn-completion audit** *(scale 0–4)*. After each Stop: rubric-score "how completely did the assistant do what was last asked" (0 ignored → 4 fully done & verified). Low scores surface sessions that *claimed* done — feeds the controller and Austin's distrust of unverified "done" reports.

### leftclaw services / onedollaraudit

**0. Job-payload sanitization gate** *(batch of 4 yesno — currently an Opus pass; benchmarked in full: see `INJECTION.md`)*. Before an untrusted audit job reaches a worker, scan it for prompt injection. Measured on 11 samples: **11/11 correct, benign max 0.63 vs injection min 0.83**, ~460ms, **$0.66/1k scans vs ~$3.75/1k for Opus (~5.7×)**. Critical design detail: a single "is this an injection?" question **does not separate** (benign audit requests scored 0.63–0.67) and the `tags` kind is worse still (no per-tag descriptions → benign scored 0.98). It only works as one question per attack class — override / verdict-dictation / exfiltration / external-instructions — flagging on the max. Recommended shape is **pre-filter, not replacement**: Sage gates everything, anything ≥0.75 escalates to the existing Opus pass, so Opus keeps every consequential call at ~1% of the volume.

### Guardrails (Austin's actual rules, made machine-checkable)

7. **Secret-leak second layer** *(tags — highest-stakes fit)*. Austin's #1 global rule exists because ~6 ETH private keys hit commits; gitleaks is regex and "can miss novel patterns" (his own CLAUDE.md says to also eyeball it). Tag staged diff hunks with {eth_private_key, mnemonic_phrase, api_token, generic_secret} at threshold 0.5 → any hit blocks the commit and asks. This is exactly "a visual scan," automated, for a tenth of a cent per commit.
8. **Destructive-command gate** *(yesno)*. When an AI controller (or any automation) is about to type into a PTY: "Could this command cause irreversible damage — force-push, rm -rf outside a temp dir, history rewrite, remote branch delete, DROP TABLE?" Inline at 300ms; maps 1:1 to the harness's "hard stops that override just-ship."
9. **Ship-vs-ask classifier** *(yesno)*. The `~/clawd/` autonomy policy is "ship by default, except secrets and destructive/irreversible changes." Make the exception checkable: score each diff summary for "does this fall under the confirm-first carve-out?" — turns a prose policy into a thresholdable gate any agent in the fleet can call.
10. **Inbound-message screening** *(tags)*. Telegram/fleet channel inputs tagged {prompt_injection_attempt, pairing_request, urgent, spam} before they reach a live session. Their moderation example, pointed at *agent* inboxes instead of user content — injection screening on agent channels is a gap their docs don't mention.

### slop computer / streaming

11. **Live-chat gold panning** *(tags + sort)*. Tag viewer messages {abuse, spam, question_for_agent, gold}; sort the gold by "most entertaining for the agent to respond to on stream." Fast enough to run per message on a live broadcast; an LLM doing this adds a visible beat of lag.
12. **Bit-picker** *(choice, low stakes so saturation is fine)*. Given current stream context, pick the next segment/task from the backlog by "most entertaining right now." Cheap enough to re-ask every segment.

### Agent arena / Factorio red-vs-blue / esports

13. **Referee on the hot path** *(yesno)*. "Did this agent action violate match rules?" at 300ms — fast enough to referee *live* without pausing the match, which no frontier-LLM judge can do. Kill-switch wiring: p≥0.95 → auto-flag; 0.6–0.95 → human ref review.
14. **Close-call detector for judging** *(sort)*. Rank N agent submissions per round; the list-level confidence is an automatic "this round was close, escalate to human judges" signal — confidence-as-escalation is their core pitch, and esports judging is a cleaner match for it than most of their own examples.
15. **Sage as a contestant** *(choice, for fun)*. From our chess probes: engine enumerates legal moves, Sage picks (≤120 options fits any position). A ~$0.0005/move, 300ms baseline contestant for the arena — the pattern-matcher-with-no-search division.

### Research / how Austin works

16. **Memory-worthiness gate** *(yesno)*. Before writing a persistent memory file: "Is this a durable fact about the user/project, not derivable from the repo, worth recalling in future sessions?" Cheap enough to run on every candidate; keeps memory high-signal.
17. **Cron/loop tick gate** *(yesno)*. Every `/loop` and scheduled agent burns a full model turn just to conclude "nothing changed." Put Sage in front: "Given this status output vs last tick, did anything change enough to warrant action?" p<0.2 → skip the turn entirely. At scale across the fleet this is real subscription-budget savings from a $0.0005 gate.
18. **Backlog sort for research ideas** *(sort)*. clawd-research accumulates ad-hoc ideas; periodically sort them by "highest expected value for Austin's current projects" as a standing prioritization view.
19. **simple-eval correlation experiment** *(scale — research, not production)*. Run Sage's 0–4 rubric over simple-eval transcripts and correlate with our deterministic pass/fail. Two birds: measures Sage's calibration on our domain, and flags eval tasks where "passed deterministically but scored low" (gaming) or vice versa (grader too strict).
20. **Typosquat / scam-token check with grounding** *(yesno + grounding)*. Before an agent `npm install`s an unfamiliar package or touches an unfamiliar token contract: "Is this the canonical package/contract, not a typosquat or scam clone?" — the one place their $0.01 web-search grounding is clearly worth it in our stack, since the answer genuinely requires current facts.

### Anti-fits (so we don't misuse it)
- **Session naming, summaries, commit messages** — generation; qwen3-coder stays.
- **simple-eval grading itself** — deterministic by design; Sage only as the side-experiment above.
- **Anything over ~32K tokens** — hard cap, no truncation.
- **Bulk offline classification** — 75× cheaper on qwen-class models; Sage's edge is latency, not price.
