# Wave A BUILD — RETURN (orchestrator a9344cf74506b9cc1 → seat 69eb9a1c, 2026-10-21T09:5xZ)

## STATUS: PARTIAL
All three Wave A PRs are open and re-homed onto main. A1 and A3 each have a READ_ONLY review verdict of PASS_WITH_NOTES with no BLOCKING finding. The A2 review never ran: fabric admission refused it every time, and custody has moved to the seat. No CI result was consumed, because the watchers were stopped on the seat's order before they printed a completion line. I did not merge, arm, label, post or edit any PR body.

## RESULT
### A1 cards-plans — PR #9954
- Branch `claude/prophet-r7-wave-a-a1`. Head last seen: **25f6ca414a495c4d1592368f23decf66dbb5e3ec**.
  - The PR opened at b1130262307aa10ebe71c3547d7cb48d274c7337; 25f6ca41 is a fast-forward that adds the site/theme.css pair.
  - Parent main: 526ce826f0898d8724e79acf3a884f9cec6f3096.
- Build lane pro-wavea-cardsplans-20261021-r1 (ubuntu3), lane commit ef9ca3b6.
- Files (5):
  - `templates/_us_prophet_plan_cards.html.j2` (+20);
  - `templates/theme.css` (+10: `--line-quiet` in both themes, OQ8 `.sg-wx`/`.sx-vw-tier` → `var(--ink-warn, var(--warn))`, `.nowrap`);
  - `site/theme.css` (+10, byte pair);
  - `tests/test_prophet_r7_wave_a_plan_cards.py` (+389);
  - `.github/ci/legacy-jobs.yml` (+3).
- Tests: 27/27 new. Export run: 90 passed, 1 failed. The failure is `test_prophet_card_shared` with rjsmin ModuleNotFoundError; it also fails on main.
- Closure: `washout-turn-organ: closure=968 declared=963 globs=6 MISS=0`.
- Probes, all delta 0:
  - `templates/index.html jobs=135->135 weight= 5825-> 5825`
  - `scripts/build_free_content.py jobs=135->135 weight= 5798-> 5798`
  - `engine/prophet/plan_book.py jobs=128->128 weight= 5574-> 5574`
- Review lane **pro-wavea-cardsplans-review-20261021-r1** (ubuntu1, rc=0), reviewed at base b1130262:
  - **PASS_WITH_NOTES**, 7/7 surfaces PASS;
  - note: `.nowrap` is not yet used by any markup;
  - lane commit 59f71f3e;
  - report at `research/prophet_v4/r7_program/build_a/WAVE_A_A1_REVIEW_2026-10-21.md`.
- CI at return: not consumed. Watcher bazub6wy1 stopped (seat order); no line consumed.

### A3 receipts-guards — PR #9955
- Branch `claude/prophet-r7-wave-a-a3`. Head last seen: **21a95484becdc5c5671e9a3f5586cc5890840e06**. Parent main: 2d50943eb154430efda02ffc117bb37b5addc242.
- Build lane pro-wavea-receipts-20261021-r1 (ubuntu0), lane commit fedc5912.
- Files (3):
  - `templates/_prophet_receipts.html.j2` (+128, add-only: `pvr_receipts`, `pvr_today_count`, sample footnote);
  - `tests/test_prophet_r7_wave_a_guards.py` (+359, 24 cases);
  - `.github/ci/legacy-jobs.yml` (+5).
- Tests: 144 passed, plus the same pre-existing rjsmin failure.
- Closure: `closure=970 declared=965 globs=6 MISS=0`. Probes: the same three lines, delta 0.
- Review lane **pro-wavea-receipts-review-20261021-r1** (ubuntu1, rc=0):
  - **PASS_WITH_NOTES**, 8/8 PASS;
  - lane commit eedef183;
  - report at `research/prophet_v4/r7_program/build_a/WAVE_A_A3_REVIEW_2026-10-21.md`.
  - A3 uses `var(--line-quiet, var(--line))`, so it does not depend on A1 merging first.
- CI at return: not consumed. Watcher brh3im4ki stopped.

### A2 watchlist — PR #9956
- Branch `claude/prophet-r7-wave-a-a2`. Head last seen: **b48469a57949dfffc1d152a50077d4dff1a88471**.
  - Re-home commit 472e9637cb15bc6679da235c607df6c5ce2c2361, plus the site-pair commit.
  - Parent main: 35321d4c07e6e6e321269a01d34339f5d18d4c7e.
- Build lane pro-wavea-watchlist-20261021-r1 (ubuntu3) ended with error_max_turns and no commit. I salvaged its partial patch as `refs/pro/wa-a2-lane=3b22223e` and re-homed it directly.
- Files (7):
  - `templates/watchlist.html.j2`, `templates/watchlist.js`, `templates/watchstore.js`;
  - `site/watchlist.js`, `site/watchstore.js` (byte pairs);
  - `tests/test_prophet_r7_wave_a_watchlist.py` (17 cases);
  - `.github/ci/legacy-jobs.yml` (+6).
- Tests: 16 passed, 1 skipped (stale-quote guard: no per-row staleness flag exists).
  - In the related subset after the site pairs: 212 passed, 3 skipped, 5 failed. All 5 failures are identical on main 35321d4c.
- Closure: `closure=971 declared=966 globs=6 MISS=0`. Probes: the same three lines, delta 0.
- Review: **none**. Custody passed to the seat (see GAPS).
- CI at return: not consumed. Watcher bnz0wv67c stopped.

## EVIDENCE
- Merge-tree rc=0 for every slice against main, the B23 ship, cnp1arch and the sibling slices.
- `scripts.check_template_site_sync` passes for the paired files. The only residual is `site/theme.js`, an rjsmin environment artifact that also appears on main.
- The carrier fence on #6817 last comment read `6306863736 mastermindxryan 2026-10-21T02:54:39Z` before every push and every PR open.
- The worklog `research/prophet_v4/r7_program/build_a/WAVE_A_WORKLOG.md` has one timestamped line per material event.

### Run ids launched (used — never relaunch)
- Build lanes: pro-wavea-cardsplans-20261021-r1, pro-wavea-receipts-20261021-r1, pro-wavea-watchlist-20261021-r1.
- Review lanes: pro-wavea-cardsplans-review-20261021-r1, pro-wavea-receipts-review-20261021-r1.
- A2 review attempts, all refused at admission before any work:
  - pro-wavea-watchlist-review-20261021-r1 (r1 attempt 1: NO_HOST, no state; attempt 2: ubuntu1 temperature);
  - pro-wavea-watchlist-review-20261021-r2 (ubuntu3, disk reserve);
  - pro-wavea-watchlist-review-20261021-r3 (ubuntu2, disk reserve);
  - pro-wavea-watchlist-review-20261021-r4 (ubuntu1, temperature);
  - pro-wavea-watchlist-review-20261021-r5 (ubuntu4, FABRIC_NEW_MACRO_LINUX_HOST_REFUSED before lease).
- I did **not** launch r6. My gate b5djiyx0g never fired; `a2rev_launch7.log` does not exist. The r6 refusal on record came from another carrier.

### Background task ids
- **I hold none.** I stopped b5djiyx0g, bazub6wy1, brh3im4ki and bnz0wv67c. Monitor bpyqltere and launch tasks b0ksk9xjf/bgvhip641 had already ended.

### Uncommitted files in the session worktree (besides WAVE_A_WORKLOG.md)
- `research/prophet_v4/r7_program/build_a/WAVE_A_A1_REVIEW_2026-10-21.md` and `research/prophet_v4/r7_program/build_a/WAVE_A_A3_REVIEW_2026-10-21.md` (my copies).
- `research/prophet_v4/r7_program/build_a/WAVE_A_RETURN.md` (this file).
- `research/prophet_v4/r7_program/reviews/WAVE_A_A1_REVIEW_2026-10-21.md` and `research/prophet_v4/r7_program/reviews/WAVE_A_A3_REVIEW_2026-10-21.md` are the seat's scp copies, not mine.

### Local refs
- `refs/pro/wa-a1`, `refs/pro/wa-a2`, `refs/pro/wa-a3`, `refs/pro/wa-a2-lane`.

## GAPS
- **A2 READ_ONLY review not run.** Every lane host failed admission on 2026-10-21 at 09:2x–09:4xZ:
  - ubuntu0, ubuntu2 and ubuntu3 were below `min_free_gb + checkout_reserve_gb`;
  - ubuntu1 was at or above its 80°C Tctl limit;
  - ubuntu4 is not qualified for new macro lanes.
  - hosts.json was left untouched. Custody of the review is now the seat's.
- **CI not consumed for #9954, #9955 and #9956.** The seat owns the CI read.
- **Product gaps, mostly Wave B or missing producers:**
  - Entry revoked has no producer field.
  - The five-slot decision line and its guard ride Wave B #9495.
  - `plans.html.j2` is the pricing page; the no-Plan copy lives in `_prophet_setup_detail.html.j2:93` (Wave B).
  - The receipts Today-switch hunk at dashboard l.17448 is Wave B.
  - What-passed rows, the sector line and the capped-group copy have no producer field.
  - The server snapshot schema is undefined.
  - OQ10 goes to Wave B.
  - Guard 5 (a stale quote means no Buy) has no staleness flag to read.
  - `saveChecked` has no in-page caller yet.
- **R7_DESIGN_SPEC_2026-10-21.md** is not tracked at BASE; both reviewers flagged it.
- **OQ8:** 13 `--warn`-as-text hits outside custody, listed in the worklog (calculators, dashboard, flow_velocity, policy_watch, sector_central, seo_base, seo_calculator_base, ticker, vector).
- **Pre-existing corrupt worktree ref** `contract-delta-base-cqkuuipv` in ubuntu1's shared store. Not ours; untouched.

## DEVIATIONS
- `<details>`/`<summary>` is used instead of `<button aria-expanded>` (the A3 reviewer accepted this).
- Fallback reconstructed copy (the A1 reviewer passed it).
- The A3 lane made no `.github` edit; I registered the test at re-home.
- The A2 salvage was re-homed directly, with no r2 build lane.
- `site/` pair files were added beyond the listed owned files, as the paired-artifact law requires.
- A1 was fast-forwarded after the PR opened, so the A1 review is of b1130262 rather than head 25f6ca41. The difference is the site/theme.css byte copy only.
- A2 review ids r2–r5 were spent across hosts. After two equivalent refusals I changed to a measured, gated tactic; the gate never fired.

SESSION END: DURABLE_EXECUTION_RUNNING
