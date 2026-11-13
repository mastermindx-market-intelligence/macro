# Displaced-clock timing control v1.1: joint page, RD and Risk Radar leader (v1 merged 396df6b4…; v1.1 leader text 2026-11-12T22:33Z)

This is for CEO approval (ruling ceo-ruling-fallback-a-20261112). No outcome was read for it.
- v0 (RD): 8243b32b….
- Leader markup: MARKUP_v0_LEADER.md, cacd1d9c…. All 8 points are accepted.

## What it is, and what it is not
- It shifts the read's own alert series as a whole, keeping mass, run count and run lengths exactly.
- It is NOT the BT1 control. That control (run_bt1.py 426–535) rolled the underlying score per calendar year and re-formed the alert, did not keep exposure exactly, filtered on counts, and had no n_eff and no p90 pass.

## Construction
1. **One block-level shift per draw.** The circular shift a'(t) = a((t − k) mod n) is applied over the read's block of n sessions.
   - A k is admissible only if the shifted series has exactly the original sorted run lengths. So no run wraps across the block end, and no two runs touch where the block ends meet.
   - Every run stays whole.
   - The page reports how many k this removes.
   - The per-year form was considered and not chosen: it adds draws, not independent episodes.
2. **Minimum shift.** K_min = max(63, pre + post_max + 1). The admissible k lie in [K_min, n − K_min], excluding the wrapping ones.
3. **Scoring.** Each shifted series is scored by the read's own scorer, on the same turns and clusters, with cluster catch as the statistic. The control is defined only where the admissible k give n_eff ≥ 10.
4. **Edge runs (amendment C).** Scoring uses the read's scorer unchanged and reads no session outside the block. Tops are credited on a run start, and a run ON at session 0 starts at session 0. Bottoms are credited on a run end: the first OFF session i after a run such that sessions i … i + min_off − 1 are all OFF (`_calls`, pivots.py 105–115). A run still ON at the last session, or a first OFF session with i + min_off > n, records no end and makes no bottom call. Turns within pre of the first session or post of the last are censored. The same treatment applies to the observed series and to every shifted series, and the count of fixture and synthetic series with such a run is reported.
5. **Several series (amendment A).** One k per draw for every contributing series; k is admissible only if admissible on each.

## Independence and pass
- n_eff = min(A, B), where:
  - A is the number of admissible k ÷ the lag at which the autocorrelation of the shifted-catch series first drops below 0.2;
  - B is the number of distinct credited-cluster sets across the admissible k.
- n_eff ≥ 10 is required. Otherwise the result is "too few independent shifts", which is not defined.
- **Pass:** the observed catch is strictly above the p90 over admissible k. Ties fail.
- **Reported:** p = (1 + #k with catch ≥ observed) ÷ (1 + #k), with n_eff beside it. With n_eff of 10–12, the smallest attainable p is about .08–.09.

## What it can show
Whether the alert's placement relative to the turns beats the same alert pattern placed elsewhere in the same block. It keeps the alert's share, clumping and run structure.

## What it cannot show
- It cannot separate timing from block-level coincidence when the turns themselves cluster. D has 2–4 market episodes, so n_eff and the 20-cluster rule both stay.
- It does not control for regime: a shifted alert sits in a different regime.
- It does not separate timing from state persistence. Synthetic check (c) addresses this.
- It does not cover false calls; part (b) does.
- It is coarse on short blocks.

## Checks before CEO use approval (no outcome joined)
- **Fixture.** It uses the runs and n of F1–F5 (n = 40), with **K_min = 5, a fixture-only value**. At the production K_min (≥ 63) no k is admissible when n = 40, so every case would trivially read "not defined".
  - Both sides give the same admissible-k set, the same wrap exclusions, and the same shifted series at k = K_min and at the admissible k nearest n/2.
  - A separate check confirms that the production K_min reads "not defined" for every n < 2·K_min.
- **Fixture (e).** Every k wraps a run, so the result must read "not defined".
- **Synthetic, over 1,000 synthetic blocks of n = 1,000 with about 20 clusters each:**
  - (a) an alert ON at [turn−10, turn] must pass in at least 90% of blocks;
  - (b) randomly placed alerts must pass at about 10% at most, reported with a binomial 90% interval;
  - (c) a state alert ON 35% of the time, independent of the turns, must pass 10% or less;
  - (d) a late-confirmation alert ON from turn + post + 1 (tops post 5, bottoms post 10) for 25 sessions must pass in at most 10% of blocks.
  - (a)–(d) are each run for tops scoring and for bottoms scoring (amendment B).
  - Joint definedness for 1, 6 and 11 series at alert shares of 15%, 25% and 35% (amendment A).
  - Power, reported only (amendment D).
  - n_eff is reported for each.
- **Who does what.** The desk worker builds the harness from this page. The leader checks its fixture output against an independent reading before the CEO sees it.

## Boundaries
- The design was approved by the CEO at 2026-11-12T22:33Z (APPROVAL_DC_v1_DESIGN.md, 2868806e…). Use on any real alert needs a separate CEO use approval.
- Before CEO approval, no real alert is shifted and no outcome is joined.
- After approval, real reads stay inside the seal (through 2023-12-29).
- It is a description control. It grants no trading permission, sizing or execution.

## CEO amendments A–F (verbatim from APPROVAL_DC_v1_DESIGN.md 2868806e…; these bind over any text above)

## Amendments (all binding; a v1.1 page carries them before the harness is called final)

A. Reads with more than one series. One k per draw, applied to every contributing series
   together. A k is admissible only if it is admissible on every contributing series.
   If the joint admissible set gives n_eff < 10 the read is "not defined". No per-series
   shifts, no dropping a series to make a read defined.
   The checks report how often the control is defined for 1, 6 and 11 series at alert
   shares of 15%, 25% and 35%. If it is mostly undefined at 25% with 6 series, say so
   plainly: then it does not replace part (a) for pooled sets and I need to know.

B. Synthetic check (d) as written is wrong for tops. Tops are credited on a run START in
   [turn−21, turn+5], so a run starting at turn+5 is inside the window and a correct
   harness would pass it. The late alert starts at turn + post + 1 or later, where post
   is the read's own value (5 for tops, 10 for bottoms). All four synthetic checks are
   run for tops scoring and for bottoms scoring.

C. Edge runs. State in one line how a run that touches the first or last session of the
   block is scored in the observed series, and apply the same treatment to every shifted
   series. Report how many of the fixture and synthetic series have one.

D. Power, reported only, no threshold: 20 clusters, an early alert that catches half the
   turns and carries two false runs a year. Give the pass rate. I need to know what a
   "fail" means before any real read.

E. Constants are fixed now: K_min = max(63, pre + post_max + 1), autocorrelation cut 0.2,
   n_eff >= 10, strict p90, ties fail. None is changed after any real read. If a synthetic
   check fails, the page gets a new version and a new approval from me; no constant is
   tuned to make a check pass.

F. Scope. Forward sets only. It never changes the verdict of any of the 14 closed reads.
   Which control applies is fixed before the read and without any outcome: Rule A where
   it is defined on every contributing series; displaced clock only where Rule A is not
   defined. Never both with a choice afterwards.
