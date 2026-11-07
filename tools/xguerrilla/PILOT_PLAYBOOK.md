# Prospective real pilot and historical planning notes

**NOT ACTIVE: runtime binding is unavailable.** The accepted current masterplan
and RUNBOOK.md govern. No command, local lease, profile procedure, degraded
continuation or file-based escalation described below is currently an execution
instruction. Existing owners must supply the real account, approved action,
original holder, settled receipt, profile permission and health boundaries.

A simulated period, source test or green CI does not satisfy the real section
26.9 gate. The original cohort/observation/restart/outage journey remains
prospective; it has not been executed or accepted by this source repair.

## Historical draft (retained for design provenance)

# Pilot playbook — 14 days, three children, one gate

Nine more children stay cold until this run holds. The gate is §26.9's done
definition, expanded in §23's P1 exit table: **three children, fourteen days,
zero challenges, restart survived, outage recovered.** A passing pilot child is a
keeper, not a throwaway.

Citations: §6 ladder, §7 provisioning, §16 typing contract, §19 cells/dress/1-in-20,
§21 session shape, §23 P1 + kill criteria, §26.3 profiles, §26.4 scheduler, §26.9 gate.
Incident how-to: `RUNBOOK.md`. Questions: `ESCALATIONS.md`. `xguerrilla` below
means `python3 -m tools.xguerrilla.cli` with `--db ~/.xguerrilla/state.db`.

## 1. The cohort — fixed before day 0

One of each role so degraded mode (§26.8) is testable: a lead and a conversation
child stay runnable when the browser path is challenged.

| Child | Cell | Role | Speed class | Slot | Hours (local) | Idle p |
|---|---|---|---|---|---|---|
| `wren.mp4` | LAA-01 | lead | fluent | pool-01 (AT&T) | 15–24 PT | 0.05 |
| `harperbuilds` | PDX-01 | conversation | average | pool-02 (T-Mobile) | 06–20 PT | 0.08 |
| `desk.and.dusk` | SEA-01 | broadcast | slow | pool-03 (AT&T) | 09–23 PT | 0.12 |

Three cells, three ASNs, three speed classes, one beat, one time band so the
fourteen days sit in one shift. The YAMLs carry these values — do not retune
mid-pilot; a changed beat invalidates the audit.

## 2. Day 0 — provision, then stop

An account is born complete or not at all (§7). In this order, no skips:

- [ ] `net-check pool-01` … `pool-03`; each must pass twice, 10 min apart. Twice
      failed is an escalation, not a retry.
- [ ] `bind <handle> pool-0N`; confirm the bound slot in `status`.
- [ ] `init <handle>`, then launch the browser **once** per child and put the real
      Chrome build string in the manifest.
- [ ] Email alias on the cohort catch-all (`c-<beat>-0NN@cohort.<domain>`), never `+`.
- [ ] Avatar and banner from the child's own style pass — one face at most, and
      only where the persona is face-forward (§20.5).
- [ ] Bio: beat-specific, no skeleton shared between the three, link in bio only —
      **no URL in any post** (§10).
- [ ] 20 minutes of real scroll, no writes.
- [ ] `snapshot <handle>` → `verify <handle>` must return `"ok": true`.
- [ ] Off-box copy: `age -r <operator-key> -o ~/.xguerrilla/offsite/<handle>-d0.tar.gz.age <archive>`.
- [ ] `activate <handle>`; state `ACTIVE`, health row fresh (not `stale`).

Day 0 ends with three ACTIVE children, three verified snapshots, zero writes.

## 3. Days 1–3 — warm-up (ladder age 0–2)

Follows only, 5–8/day, and only the two owning parents plus three big friendly
accounts in the beat. No unfollows. No replies. R-ENGAGER only. One post, on
day 3, no link, no thread.

Sessions: 2–4, 4–22 minutes, inside the child's hours (§21.1). The scheduler
draws gaps lognormally (62-min median, cv 0.55) — do not restart the worker on
the hour, and never re-run a child to "top up" a short session.

**Not yet:** no reply to a parent's post (day-8 rung); no follow of another child
(sibling edges arrive after the first strangers follow back, so the follow list
never opens as a cluster); no unfollow, quote, thread or image; no bio/avatar/
banner edit — a profile rebuilt daily is being assembled in front of people; no
second login (one re-login per child is the pilot ceiling, §23).

Pass for the warm-up: three children still `ACTIVE`, zero challenges, zero
re-logins, 15–24 follows placed, first post live with `X for Web` or a browser
label in its `label` row.

## 4. Days 4–14 — steady state (ladder age 3–14)

| Day | Follows/day | Unfollows | Replies | Posts |
|---|---|---|---|---|
| 4–7 | 12–20 | 0 | 0 | 2 total in the week |
| 8–14 | 25–40 | 0–5 from day 12 | 1/day per child | 2 total, images allowed from day 8 |

Still deliberately under the day-15 rung: the pilot measures shape, not volume
(§23 P1). Follows go to beat accounts, not to the network. Keep the dress rule —
18–30 organic accounts per child in its beat, ≤ 1 in 20 edges pointing at our own
accounts (§19.2). Unfollows only accounts followed ≥ 5 days ago that did not
follow back, oldest first, in the same session as that day's follows.

Hold the ratio inside `following ≤ min(600, followers × 3.5)` while followers <
400, and `following ≤ followers × 1.6` above it. The 5,000 cap is far away; the
ratio rule bites first and it is the one that matters.

## 5. Voice rules — what makes the account read as a person

| Rule | Number | Why it is operational |
|---|---|---|
| Specific interest | Every post names a thing in the beat (a lift, a price, a model, a street) | "Interesting times" is a brand; "third week of 5×5 at 82.5 kg" is a person |
| Posting mix | ~60 % observation, 25 % reply-shaped post, 15 % question | A feed of only declaratives is a feed |
| Replies | ≥ 70 % to non-network accounts; own-network replies ≤ 1 in 5 | The reply column is the most-scraped surface on the account |
| Reply length | 1–2 sentences, lowercase start allowed per `casing` | Long replies read as written-for-the-record |
| Imperfection budget | 1 in 8 posts carries a self-corrected typo, a lowercase start, or a trailing fragment; ~1 missed day in 10 (the persona's `idle_day_p`) | Perfection is the tell; §21.4 budgets it on purpose |
| Typing audit | median inside the class band, CV 0.6–1.2, skew > 0, ≥ 1 deletion per 100 keys (`typing.assert_natural`) | Below band = paste; uniform = macro |
| Late-night | Occasional post after the window closes, ≤ 1 in 15 | Nobody closes their phone at 23:00 on the dot |
| Face | Avatar/banner only; ≤ 1 photo in 20 posts, and it is a desk or chart shot | Same face, no grid, is the face-account tell (§20.5) |

Never fix a published typo unless the fact is wrong. Never post the same sentence
twice across the three children — rephrase, do not re-order.

**Follower curve, healthy:** 0–3/day early, lumpy, follows-back within hours of
the follow, an occasional +4/+6 after a reply lands, net 12–25 by day 14 at this
volume. **Flagged:** flat zero for 4 consecutive days while actions succeed;
+30 in a day off one thread and nothing after; followers arriving with no reply
views; follows that never reciprocate by day 5; a follower count that moves while
`reply_views` and profile opens stay at zero.

## 6. Daily checklist — run at the same time every day

| # | Check | Pass | Fail action |
|---|---|---|---|
| 1 | `status` — all three `ACTIVE`, health not `stale` | 3/3 | quarantine the odd one, escalate L1 |
| 2 | Challenges in last 24 h | 0 | `cool` 180, `verify`, snapshot, escalate L1 |
| 3 | `telemetry.summarise` — `relogin_fraction` | ≤ 0.15 | inspect cookie jar, snapshot, L1 |
| 4 | `typing.assert_natural` on yesterday's typed posts | all 3 pass | L2 escalation; do not post through a failing band |
| 5 | Labels seen across the cohort | ≥ 2 distinct per week | record it; a single label cohort is the farm signature |
| 6 | Follows placed vs ladder | inside the day's rung | no top-up; let the schedule catch up |
| 7 | Ratio | inside the formula | unfollow oldest non-reciprocators next session |
| 8 | Follow-back rate 7 d vs 30 d median | ≥ 40 % of median | L2 — this is the de-rank early warning (§9) |
| 9 | Replies placed / responses drawn | 1 per child / ≥ 5 by day 14 | retarget the reply list, not the volume |
| 10 | Profile opens attributable to replies | ≥ 3 by day 14 | same |
| 11 | Slot: one successful `net-check` per slot | 3/3 | fail twice → `degrade`, L2 |
| 12 | `snapshot` all three + `verify` | 3/3 ok | restore the last good one before any write |
| 13 | Cost per child-day | ≤ $1.60 | record; over is a P1 fail |
| 14 | Manual overrides today | 0 | one override is a note, two is a pattern |

Record §8 numbers whether they pass or not; a day with no record is a missed day.

## 7. Ban-avoidance — as actions, not principles

| Rule | Concrete action |
|---|---|
| Behaviour diversity | Three different roles and three speed classes in the cohort; never the same action order across children |
| One niche per child | `wren.mp4` trains, `harperbuilds` builds, `desk.and.dusk` observes markets — no cross-posting of beat |
| No identical copy | Same fact may appear on two children, never the same wording; vary the number, the unit, the casing |
| Follow pacing | Ladder rung per age, floor between actions 90/60/45 s, never more than 400/day/account, ratio rule above |
| No link bursts | Zero URLs in posts; the bio link is the only link, so a link never has to be staggered |
| Staggered schedules | Per-persona `hours` + `seed`-derived gaps and idle days; start the worker once, let `next_run` drive |
| Degraded rail-only mode | On a challenged browser path: `degrade --reason "<what>"`, leads and conversation children keep posting through the rail, broadcast pauses; `recover` only on a green `shadow` run |
| No round numbers | Never 20 follows at 10:00; the scheduler's lead/tail jitter handles it, so don't override it |
| No churn | Unfollows start day 12 at 0–5/day, never a day-14 sweep |

## 8. Metrics to record — one row per child per day

Append to `~/.xguerrilla/pilot/metrics.jsonl` (JSONL, one object, keys fixed):

- identity: `date`, `handle`, `state`, `slot`, `notes` · `status`
- graph: `followers`, `following`, `ratio`, `follows_tried`, `follows_ok`, `unfollows` · profile read + action log
- production: `posts`, `replies`, `reply_responses`, `profile_opens` · telemetry
- health: `challenges`, `relogins`, `session_ok` · `telemetry.summarise`
- typing: `iki_median`, `iki_cv`, `iki_skew`, `deletions_per_100` · `assert_natural`
- labels: `labels_distinct` · `label` rows
- spend: `cost_usd`, `overrides` · spend log

## 9. Kill switch and rollback — one child

Freeze first, inspect second, restore third, retire last. Never diagnose a live
child.

1. **Freeze.** `cool <handle> 10080` (7 days) — out of rotation, profile intact; stop only that child's worker.
2. **Snapshot before touching anything.** `snapshot <handle>`, then `verify`.
3. **Inspect.** Which signal fired: challenge, two audit fails, flat followers, slot
   failure, identity risk. Pull 40 telemetry rows for the handle + the last screenshots.
4. **Restore.** `restore <handle> <snapshot.tar.gz>` then `verify` — archive must
   hash-match the manifest before re-activation. `profiles.py` does not encrypt: at
   rest on FileVault, off-box under `age` (§26.3).
5. **Re-enter slowly.** One `shadow` run green, then `activate`, then one warm-up
   day at half the rung.
6. **Retire** if a restored child re-challenges inside 24 h or a suspension lands:
   `retire <handle>`, YAML to `personas/retired/`, keep profile + snapshots 90 days.

The **outage** test is the cohort version: kill the worker mid-day once (day 6–9),
confirm the children fall to rail-only, and confirm they resume inside the same
day. A fallback that never fired is a claim (§23 3c).

## 10. Day-14 verdict

Write `~/.xguerrilla/pilot/PILOT-14D-VERDICT.md`:

    # P1 verdict — <YYYY-MM-DD>
    ## Gate
    | three children for 14 days | pass/fail | run log |
    | challenges 0 · suspensions 0 | n / n | telemetry |
    | restart survived · outage recovered in-day | pass/fail | relogin + degrade/recover rows |
    | follow-back ≥ 12 % | x % | metrics |
    | replies answered ≥ 5 · profile opens ≥ 3 | n / n | beat log |
    | re-logins ≤ 1/child · cost ≤ $1.60/child-day | n / $ | metrics |
    | days inside ladder, no override | n/14 | overrides |
    | labels ≥ 2 distinct | n | label rows |
    ## Escalations leaned on
    <Q-ids and their directives, or "none">
    ## Decision
    GO — unblock the nine (P2) | NO-GO — repeat 14 days on the same three
    ## What changed in the plan

Verdict is `GO` only if every row passes and no `open/` escalation remains
(`ESCALATIONS.md` §8). Two suspensions or an unresolved 72 h challenge is a
`NO-GO` by §23.1 and needs no discussion.
