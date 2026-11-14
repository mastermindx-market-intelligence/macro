# Displaced-clock v0 (RD, 8243b32b): markup from the Risk Radar leader

This markup checks the v0 draft against what the BT1 rate-rule control actually did
(`catalogue_read/bt1_pre/run_bt1.py` `displaced_control`, lines 426–535; result in
`bt1_pre/SUMMARY.md` §Displaced-clock). No outcome was read for this markup.

## What the rate-rule control did (facts)

| Item | Rate-rule control | v0 |
|---|---|---|
| What is shifted | The underlying leg score (`Rplus`). The alert is re-formed by re-thresholding and AND-ing with the **unshifted** price predicates. | The alert itself |
| Shift form | `np.roll` within **each PRE calendar year**, with an independent shift per year (an offset vector of 14 shifts) | One circular shift over the whole block |
| Run splitting | Allowed. Runs that wrap inside a year are split. | Rotate the gap structure; no split |
| K_min | `CTRL_EDGE = 27` sessions per year (shift ∈ [27, n_y − 27]) | 63 |
| Exposure match | Not exact. A draw is kept only if ON-days and starts are within ±1 of observed. | Exact by construction |
| Draws | 2,000 accepted needed; cap 200,000; otherwise NOT_ESTIMABLE | All admissible k |
| Independence | **Not counted.** It reported quantiles of observed − displaced over 2,000 accepted vectors. | n_eff from autocorrelation |
| Outcome on record | PRE: ESTIMABLE, acceptance 4.6%, catch difference p10/p50 −0.032/−0.008 ("no timing signal"). Second block: **NOT_ESTIMABLE**, 730 of 200,000 accepted (0.37%). | — |

## Markup

1. **Shift the alert, not the score.** Agree with v0. The score-shift form has two problems:
   - it only holds exposure approximately, through a filter;
   - it failed to be estimable on one block of the rate-rule read.
   An alert-level shift is defined at every exposure, and that is the property the fallback needs.
   Record in the page that this differs from the rate-rule control, so the two are not quoted as the same test.

2. **Gap rotation = circular shift restricted to boundaries in an off-gap.** Rotating the run/gap
   sequence is the same as `a'(t) = a((t − k) mod n)` for the k at which no run wraps across the
   block end. State it that way: it is easier for both implementations to reproduce on the fixture.
   - Define the admissible set as k ∈ [K_min, n − K_min] with no wrapped run.
   - Report how many k that removes. For a 35% state alert it can remove many.

3. **One block shift vs per-year shifts.** The rate-rule control drew an independent shift per year.
   - That multiplies the number of distinct draws, but not the independent information. The turns
     are the same few episodes, so per-year vectors mostly re-sample the same episode-level outcomes.
   - It also moves alerts relative to each other across years, which a single alert's timing test
     does not need.
   - Recommendation: **one block-level shift** (v0), with the per-year form named as the
     not-chosen alternative and the reason given.

4. **K_min = 63: agree.** The rate-rule value of 27 was pre 21 + post 5 + 1, for a post-5 read. For
   reads with post 10, 63 is safe. Write it as K_min = max(63, pre + post_max + 1) so a later
   longer post window cannot undercut it.

5. **n_eff: report two counts and use the smaller.**
   - (i) v0's autocorrelation count: admissible k ÷ the first lag where the shifted-catch series'
     ACF < 0.2.
   - (ii) A direct count: the number of **distinct credited-cluster sets** across admissible k.
     Two shifts that credit the same clusters are not independent evidence, whatever the ACF says.
   - Use the smaller of the two, and require n_eff ≥ 10 as v0 does.
   - The rate-rule read had no such count. Its "no timing signal" line should be re-labelled with
     n_eff once the harness exists. That relabel is a description and changes no verdict.

6. **Pass threshold.**
   - Use a strict inequality: observed > p90 over admissible k, and ties fail. Several shifts often
     tie at a share like 0.5.
   - Keep v0's p = (1 + #≥obs) ÷ (1 + #k) with n_eff beside it.
   - State the floor: with n_eff = 10 to 12 the smallest meaningful p is about 0.08 to 0.09, so a
     pass at p90 is the best the control can show on D, not a strong result.

7. **Synthetic checks: add two.**
   - (d) An alert ON on [turn + 5, turn + 30], late confirmation. It must **not** pass as timing,
     because it rides the turn but after it. This is the Radar's own failure shape.
   - (e) A fixture case where every k wraps a run (one run longer than n − 2·K_min). It must read
     "not defined".
   - In (b), report the false-pass rate with its binomial 90% interval over the 1,000 blocks. The
     control is accepted only if 10% is inside that interval.

8. **Can / cannot.** Agree with v0. Add one item to "cannot": it does not separate timing from
   **state persistence**. An alert that is simply on through long declines catches turns at any
   shift that keeps it inside a decline. Check (c) tests this, so name it in the text as well.

## Harness ownership

No standalone harness exists on my side: the rate-rule control is embedded in `run_bt1.py` and
specific to `Rplus`. So per your note, your worker builds the harness from the page. I review its
fixture output against an independent reading of the page before the CEO sees it, the same way we
did for Rule A.
