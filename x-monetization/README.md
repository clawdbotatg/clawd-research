# X Original Content Rewards — where Austin stands (2026-09-02)

Source: help.x.com/en/using-x/original-content-rewards (read 2026-09-02) and
x.com/i/account_analytics for @austingriffith. Prior algorithm research (code-level
read of xai-org/x-algorithm) lives in `~/clawd/clawd-x-research/` — see its
`tldrTweetGuide.md` and `findings/`.

## The program in one paragraph

Replaced Creator Revenue Sharing on 2026-08-08 (rev share retires 09-07). You get
paid every two weeks for **qualified impressions** on **original** posts. Rate is
undisclosed. Minimum payout $30. US payouts go through X Money. Apply from
Creator Studio once eligible; review takes 3 business days; one appeal, then a
90-day lockout.

**Qualified impression** = a *unique* view by a Premium subscriber (any tier), on
the **Home timeline** (For You / Following), with at least 50% of the post on
screen. Replies never count. Profile visits, search, notifications, detail views,
promoted views don't count.

## Eligibility scorecard

| Requirement | Austin | Status |
|---|---|---|
| Premium / Premium+ / Business | Premium+ | done |
| 18+ | yes | done |
| 500 verified followers | 15.2K | done |
| 500K verified Home-timeline impressions, trailing 90d, replies excluded | **425.4K** | **74.6K short** |
| Actively post original content | yes | done |

The only gate is impressions.

## The numbers behind the gap

From analytics with the "Verified" toggle on:

| Window | Verified impressions (all surfaces) | Per day |
|---|---|---|
| Last 90 days | 763.5K (+36%) | 8.5K |
| Last 28 days | 300.8K (+52%) | 10.7K |

Program counter says 425.4K of that 763.5K qualifies, so roughly **56%** of a
verified impression is a qualified one (rest is replies, non-home surfaces,
duplicates, partial views).

Translation of the gap: 74.6K qualified ≈ **~134K more raw verified impressions
in the window**, or ~830 qualified/day above the current 90-day average.

## When it crosses on its own

The window is rolling. Days from early June (~4–5K verified/day) are dropping off
while August days (~10–30K) come in.

- If the last-28-day pace holds, a full 90 days = ~967K verified ≈ ~540K
  qualified. That's over.
- Net gain is ~6K verified/day → crosses in roughly **3 weeks (late September)**
  if August pace holds.
- Trap: the Jul 7–8 one-dollar-audit launch (~100K verified over two days) drops
  out of the window around **Oct 6**. That's a ~55K qualified cliff. Cross it
  with margin or you fall back under before the application is reviewed.
- The last 4 days (Aug 29–Sep 1) were 3–4K/day. Pace is decaying; the Sep 1
  hardware/omarchy post (42K) is the exception.

## What actually moves the number

Top posts in the window (impressions, all users):

| Post | Imps | Type |
|---|---|---|
| one dollar audit launch (Jul 7) | 164K | product launch, checklist format |
| "we will finally kill stack too deep" (Aug 27) | 80K | eth dev news explained plainly |
| "give your ai <link> and let it rip" (Aug 11) | 67K | short take + link (link in body, still worked) |
| EE degree / omarchy voice+vision harness (Sep 1) | 42K | personal story + photo |
| Beau born (Jun 4) | 41K | personal + photo |
| one dollar audit job #450 (Jul 21) | 37K | product progress |
| qwen in solidity + gaskiller clip (Aug 12) | 28K | native video |
| "oh man i get it now" linux/agents (Aug 20) | 26K | opinion arc |

Pattern: lowercase, one idea, 3–6 short lines, a strong first line, eth-dev news
or AI-workflow takes, product launches. No thread needed.

Replies are a rounding error for this program: top reply in 90 days was 11K, most
are 1–2K, and none of them count anyway. The Posts-vs-Replies chart shows reply
volume far above post volume. That energy is worth moving into standalone posts
or quote posts (quotes count as posts).

### Playbook (from the code-level algo research, applied here)

1. **One original post per day, minimum.** Median post is ~5–15K verified imps.
   One extra median post per day alone covers the gap.
2. **Space them out.** Same-author posts in one feed get decayed exponentially.
   Two posts a day, hours apart, beat five in an hour.
3. **Lead with the take, not the link.** Dwell is rewarded, tapping away is not.
   Link in the first reply. (Aug 11 shows body links aren't fatal, but they cost.)
4. **Native video/photos.** Video past the minimum duration earns the extra
   "quality view" signal. Phone clips of the hardware stuff, the ciphernode, the
   3D printer all fit.
5. **Eth dev news, explained in plain English**, is the highest-ROI lane. The
   stack-too-deep post is the template: what shipped, why devs care, one line of
   hype. Glamsterdam/Fusaka items, EIPs, client releases, tooling.
6. **Reply → quote post.** When a reply would be a real take, quote-post instead.
7. **Ask for replies, not likes.** Questions ("when was your first POAP", "who is
   doing local ai for normies") drew 12–43 replies. Never ask for likes/RTs/
   bookmarks: engagement solicitation is a program violation.

### Things that can get the content excluded or the account kicked

- Posts "created or posted using automated means" are not original content.
  Anything the harness/clawd auto-posts on @austingriffith won't count and is a
  risk. Keep agent-written posts on @clawdbotatg.
- Reposted/re-uploaded media, minimally edited clips, aggregation.
- Any post that gets a helpful Community Note.
- Posts that are mainly about monetization/payouts.
- Soliciting engagement, bots, buying views.

## Next steps

1. Post one original post a day for the next 3 weeks (news explainer or workflow
   take). Check the counter at x.com/i/jf/creators/original_content_rewards.
2. When it flips to an Apply button, apply immediately. Make sure X Money is set
   up (US payouts only route through it).
3. Keep pace through Oct 6 so the July launch rolling off doesn't drop you under.

Payout expectation: undisclosed rate. Third-party calculators guess, X publishes
nothing. Treat it as beer money until the first biweekly payout says otherwise.

## After you're in

The 500K impressions and 500 followers are checked **at the time of application**
only. The "Continuous Eligibility" list on the help page does not repeat them.
What you must keep doing to stay in and get paid:

- Stay subscribed to Premium / Premium+ / Business. Lapse = no payouts.
- Keep posting original, authentic content. Payouts are per qualified impression,
  so a quiet fortnight just pays $0 (nothing under $30 is paid out); it does not
  eject you.
- No bots, bought engagement, algorithm tampering, or engagement solicitation.
- Individual posts get excluded (not you) if they're copied, reuploaded,
  community-noted, monetization-talk, or auto-posted.

X "periodically reviews" enrolled accounts and can suspend or remove you for
violations, with an appeal path. The list is explicitly "not exhaustive" and X
can end or change the program at will (as it just did to rev share).
