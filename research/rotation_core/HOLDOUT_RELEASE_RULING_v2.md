# Rotation Core v2 — hold-out release ruling R13 (staged release)

- **Ruled by:** Prophet programme CEO, 2026-11-11 12:42Z (real UTC). Recorded by the Rotation Core lead.
- **Frozen header:** `protocol_header_v2.json`, sha256 `ca5af27429b54df534e959bde8a3db037c95f7fe5c7c430fe7e6bb5b03d01728` (freeze commit `ac68f2e72a`).
- **When written:** after the selection result on 1998–2019 (`1ca5228b3c`: selected h = 3, b = 25; H1 −2.29 %/yr against its matched mix, H3 +1.33 %/yr; neither informative), and before any v2 number on pre-1998 or 2020–2025 exists.
- **Scope:** R13 changes no rule, threshold, window, yardstick or pass condition in the frozen header. It fixes only the order in which the two confirmation windows are read, which the header leaves to the parent's release file.

## The two confirmation windows are not equally clean

- **Pre-1998 (Ken French industries, 1928–1997)** was already examined for this question by Pro run B's ten rules on the French 49 industries 1926–2019. Those 10 trials are counted in the ledger. This window is not clean.
- **2020-01-02 → 2025-12-31** is the only window no test of this programme has read. It contains about two stress episodes. It can be opened once.

## Rule

**Stage 1.** The parent releases `pre1998_1928_1997` only. One run computes, for the selected setting:
- H1, the price-only control (for H2), H3 and the cash ablation;
- all four yardsticks (the French market in place of SPY, the stated equal-weight proxy in place of RSP, equal-weight industries, and the binding exposure-matched mix);
- each era (1928–1945, 1946–1997) and the full window, at 10 bp and at 2× costs;
- drawdown against the mix, turnover, and false DEFEND calls per calm year.

No pooled Holm p is computed at this stage, because it needs both windows. No date after 1997-12-31 is read in Stage 1.

**Stage 2.** 2020-01-02 → 2025-12-31 opens once, by a second release the parent writes, **only if** at least one of H1 and H3 has a positive point estimate over its matched mix in **both** pre-1998 eras. The runner checks this against the committed Stage 1 result file, not against anyone's word. If the window opens, it opens for every configuration in the header at once, including the tradable-funds check and the named mapping. The pooled Holm test (m = 3, all three hypotheses, as frozen) is computed then. A hypothesis that already failed its pre-1998 leg stays FAIL; its 2020–2025 numbers are reported, not scored.

**If neither H1 nor H3 clears the pre-1998 leg:**
- the historical tier closes as FAIL for all three hypotheses;
- 2020–2025 and the sealed French post-2019 files stay sealed and are recorded as unspent;
- the forward tier is unaffected.

## Why this ordering cannot raise the false-positive rate

The frozen pass condition is a conjunction. One of its necessary parts is "point estimate > 0 in both pre-1998 eras" on the primary contrast. A hypothesis with a non-positive estimate in either era fails the frozen test, whatever 2020–2025 shows.

R13 only ever skips reading 2020–2025 in that case. It never adds a way to pass, never changes a statistic, and never lets Stage 1 numbers alter anything computed in Stage 2. Every pass under R13 is therefore also a pass under the frozen header read in one go, and the false-positive rate cannot rise. For H1 and H3 the stop costs nothing, because the stopped case is already a fail.

**The lead's caveat, recorded before any number (one place where the stop is not costless).** H2's primary contrast is its own paired difference, H1 minus the price-only control, and its sign leg is on that difference. Suppose H1 and H3 both fail their pre-1998 eras while H2's paired difference is positive in both. Then R13 keeps 2020–2025 shut, and H2 never receives the test it could otherwise pass.

That is a loss of power for H2, not a route to a false positive, so it is not a stop under R13's own test. ~~The parent may name H2 in the Stage 2 release's opening-condition list if the parent wants H2 to be able to open the window. The runner reads that list from the release file.~~ *Struck by R16 S1c: the amendment governs. The opening list is the constant (H1 at the selected setting, H3) in code; no release can name or change it; a closed gate records H2 FAILED.*

## Guards (implemented in `scripts/run_rotation_core_v2.py`)

- **Stage 1** requires a committed, clean `HOLDOUT_RELEASE_v2.json` whose `windows_released` is exactly `["pre1998_1928_1997"]`. It reads only the truncated `le2019` French copies, refuses any date after 1997-12-31 and any sealed path, and runs once.
- **Stage 2** requires a second committed release, `HOLDOUT_RELEASE_v2_stage2.json`, with `windows_released` `["2020-01-02..2025-12-31"]`. It also requires the committed stage-1 gate file, every entry of whose `gate_history` is open (R17), pinned by sha256 in the release, with the same engine commit as the latest stage-1 run. It runs once. (Superseded wording: "satisfies the opening condition named in that release" — the opening list is now a constant, R16 S1c.)
- **Order of work still open:** Sector Intelligence's reviewer findings on the engine. Stage 1 does not run until the parent forwards them or says there are none.

---

## Amendment 1 to R13 (parent 12:48Z and 12:51Z; recorded before any pre-1998 or 2020–2025 v2 number exists)

**a. Failures stay failed.** A hypothesis whose point estimate is not positive in both pre-1998 eras is recorded FAILED before 2020–2025 opens, and nothing read later revives it. The Holm family at the pooled test is the full frozen family of three (H1, H2, H3), computed exactly as frozen, never the survivors.

**b. Pass sets and effect sizes.**
- **Identical-pass-set argument.** The lead flagged a flaw (12:48Z): it holds for H1 and H3, not H2. Sector Intelligence confirmed this, and the parent ruled (f) below. Read with (f), the frozen pass test (pooled Holm p plus the sign legs) is unchanged, and staging cannot raise its false-positive rate:
  - every outcome that passes under staging passes unstaged;
  - for H1 and H3 the pass sets are identical, because their stopped outcomes fail the frozen conjunction anyway;
  - for H2 the staged pass set is a subset.
- **Effect sizes.** Any pooled or all-eras point estimate reported after a gated opening is conditional on the gate and biased upward as an effect size. The 2020–2025 standalone estimate is reported as the out-of-sample effect size. Pooled figures are reported for the frozen test only, labelled "conditional on the pre-1998 gate, not an unbiased effect size".

**c. Gate definition.**
- **Statistic:** the sign of the point estimate of annualised mean daily excess of the book over its exposure-matched mix, net of costs at 10 bp per side, for H1 at the selected setting and for H3.
- **Eras by date:**
  - E1 = 1928-01-02 → 1945-12-31. 1928-01-02 is the first scored session: H1 and the price-only control first have a state on 1927-06-01 and H3 on 1926-12-31, so the frozen window start of 1928 governs.
  - E2 = 1946-01-02 (the first session of 1946) → 1997-12-31.
- **What the header says about the mix:** the frozen header builds the mix "at H1's average weights, rebuilt inside every bootstrap resample from that resample's own average weights". It is silent on era-level estimates. **Specification made before the read:** the mix for an era's point estimate is built on that era alone.
- **Release contents:** the release file carries the engine commit, the frozen header sha256 and the selected configuration. The runner refuses unless engine, scripts and tests at HEAD are byte-identical to the named engine commit and the tree is clean. A release commit necessarily sits on top of the engine commit, so "refuses any other commit" is enforced as "refuses any other engine code".
- **Engine fixes after a read:** any engine fix after a window has been read reruns every window read so far, including ones that passed, as a logged deviation.

**d. A closed gate.** 2020–2025 stays unread. Pre-1998 then counts as development data for any successor protocol, and a successor's trial count carries all 55 (v1's 36, v2's 9, run B's 10) plus its own.

**e. Funds.** The gate is on industry portfolios only, since no sector funds exist before 1998-12-22. The tradable-funds veto applies in full at 2020–2025 and cannot be waived or softened by a strong pre-1998 result.

**f. H2 under a closed gate.** H2's pass set is not inside the gate: H2 can be positive in both eras while H1 and H3 each miss one, so staging shrinks it. A closed gate records H2 as FAILED on the historical tier, not as untested. This is conservative, and it is disclosed as a consequence of staging.

**g. The gate is the same number the final conjunction uses.**
1. **Setting:** H1's gate setting is "the grid point selected at commit `1ca5228b3c`" (h = 3, b = 25). The runner reads it from the committed `results_v2_selection.json`, never from an argument, and refuses a release naming anything else.
2. **Costs, stricter reading:** "holds at 2× costs" applies to the whole conjunction. Significance and every sign leg must hold at 10 bp per side and again at 20 bp per side. The gate is evaluated at 10 bp only, so under this reading the gate is implied by the frozen pass condition and removes no passing outcome for H1 or H3. The header's wording also admits a narrower reading (2× applying to the effect alone); R13 takes the stricter one before any confirmation number exists.
3. **One function:** `engine.rotation_core_v2.window_excess` (mix on the window or era alone) computes the gate signs and the final conjunction's era signs. A test asserts it returns the identical value as the era point estimate of `matched_contrast`.

**h. No open choices while anyone knows a pre-1998 number.**
- **Seeds:** stage 1 20261113, stage 2 20261114, pooled test 20261115. Within a stage, books use fixed offsets written in the runner.
- **Bootstrap:** B = 10,000; mean block 21 sessions, 63 as sensitivity; the stationary bootstrap of the frozen header. The gate uses no bootstrap.
- **Pooled series across the 1997-12-31 / 2020-01-02 join.** The frozen header says only "the pooled pre-1998 + 2020-2025 primary contrast". The lead chose the conservative construction:
  - each window keeps its own daily excess series, with its own exposure-matched mix built on that window alone;
  - the bootstrap resamples each window separately, so no block spans the join (stratified);
  - the pooled statistic is the years-weighted mean of the two windows' annualised excesses;
  - the one-sided centred p is taken from that stratified distribution.

  **Why conservative:** a single mix across 1928–2025 would be one fixed reference over two eras of very different leg returns, which flatters a book whose average weights differ between windows. Separate mixes remove that. No block crosses a 22-year gap.
- **Choices the frozen header leaves silent** (each made without looking at data):
  1. **Era-level mix:** built on the era alone, for both the gate and the final conjunction.
  2. **Annualisation:** 252 × sessions ÷ weekday sessions (252 wherever there are no Saturdays), revised before any read from sessions per calendar year; see R15.5. Signs are unaffected; the pooled p is computed under this and under fixed 252, both must hold.
  3. **Pooled construction:** as above.
  4. **First scored session:** 1928-01-02, taken from the frozen window, not from first state availability.
  5. **"Holds at 2× costs":** the stricter reading (g.2).
  6. **Drawdown condition:** "drawdown no worse than the matched mix" is assessed on the full pre-1998 window and on 2020–2025 separately, and both must hold.
  7. **H2 at stage 1:** ~~its era signs are recorded in the gate file but do not open the window unless the parent names H2 in the stage-2 release~~. *Superseded by R16 S1c: H2's signs are neither printed nor written at stage 1; they are inside the magnitudes hash only. H2 cannot open the window.*
  8. **Intra-month leg weighting:** OFFENCE and DEFENCE are equal weight every session over the member set fixed at month-end (R14(a) reading; the header is silent).
- **Stage 1 is blind to magnitudes.** *(The sealing mechanics below — mode-000 file, `open_sealed_stage1` — are superseded by R16 S6; see that section. The blind principle stands.)*
  - **What the run prints:** only the four gate signs (H1 and H3, each era), the gate result, non-return integrity diagnostics, and the sha256 of the results file. The diagnostics are session counts per era, offence-member counts, deferred executions, days holding after a last close, dropped industry-days, state counts and episode count. H2's era signs are written to the gate file, not printed.
  - **Sealing:** every return, excess, interval, p-value, drawdown and cost figure goes to `<data root>/sealed_stage1/results_v2_stage1_pre1998.json`, written mode 000. The committed `results_v2_stage1_gate.json` carries the signs, gate result, diagnostics, engine commit and that file's sha256.
  - **Gate open:** the sealed file stays unopened; the final run recomputes pre-1998, and `verify_reproduction` refuses to print anything unless the recomputation's sha equals the sealed sha.
  - **Gate closed:** the sealed file is readable through `open_sealed_stage1` and is reported in full; 2020–2025 stays unread.
  - **Tests:** stdout contains no decimal number (fixture run); the sealed file is unreadable without a stage-2 release or a recorded closed gate; the reproduction check fails on a one-byte difference; a fixture recomputation is byte-identical.
  - **Integrity under the blind:** nothing needed a magnitude. The integrity checks that matter (gaps, deferrals, dead positions, state counts, window dates) are all counts.

**i. Reporting rule.** The pooled minimum detectable effect is about 2.1–2.3 pp/yr, and about 7.6–8.3 for 2020–2025 alone, so a pooled p-value is set almost entirely by pre-1998, which the header discloses as previously examined. If the gate opens and the test passes, the result text gives the 2020–2025 standalone estimate with its interval. It says in words that significance comes from the examined window and that the unexamined window supplied a sign check, which a rule with no edge passes about half the time. The label stays "survives falsification on history"; nothing stronger is written anywhere, including the PR draft.

## Notes on the frozen header (power method)

- **MDE lines** (`power_statement_top`, `power.h1_actual_tilt`):
  - MDE = (z₁₋α/₃ + z₀.₈₀) × SE.
  - SE is the standard deviation of a stationary-bootstrap distribution (block 21, B = 4,000) of H1's matched-mix contrast on 1998–2019, scaled by √(D years ÷ window years).
  - **Method:** normal approximation, at the Bonferroni bound α/3 (Holm's first step, the worst case). It is not a simulation under Holm.
- **Joint-rule pass probabilities** (63 % at the MDE, 50–57 % at 2 pp/yr):
  - Monte Carlo of independent normal per-window estimates (E1 17.2 y, E2 52 y, 2020–2025 6 y) with D's per-year standard deviation;
  - pooled significance at the Bonferroni bound α/3, plus the four sign legs;
  - normal approximation, Bonferroni bound.
- **Post-freeze check, labelled as such** (`v2_power/power_holm_sim_D.*`):
  - **Method:** simulated under Holm (m = 3) with the D covariance of the three contrasts (variance and covariance only, centred series), H1 at the MDE and H2, H3 null.
  - **Results:**

    | True H1 edge | P(H1 rejected), Holm | P(H1 rejected), Bonferroni | Joint pass, Holm | Joint pass, Bonferroni |
    |---|---|---|---|---|
    | 2.18 pp/yr | 0.805 | 0.803 | 0.636 | 0.635 |
    | 2.0 pp/yr | 0.73 | 0.73 | 0.57 | 0.57 |
    | 1.0 pp/yr | 0.23 | 0.23 | 0.16 | 0.16 |

    The frozen figures are accurate approximations.
- **Bootstrap calibration** (`tests/test_rotation_core_si_findings.py`): under an AR(1) null (φ = 0.1, 3,000 sessions, 300 replications, B = 400, block 21), the measured one-sided size at nominal 5 % was **4.3 %** and the 95 % basic-interval coverage **94.7 %**. The tolerance, declared before running, was size in [2 %, 9 %] and coverage in [90 %, 99 %].

---

## R14 — BASE weighting (parent, about 13:20Z; added after selection results were seen and before any confirmation read; it cannot turn a fail into a pass)

- **(a) Governing reading.** The header says "BASE = equal weight of all eligible industries, rebalanced monthly". The code fixes the eligible set at each month-end and weights it equally every session; that reading governs. This is a clarification of wording that admits two readings, dated before any confirmation read. Selection is not rerun for it and the frozen bytes are untouched.
- **Legs, same fact.** The code also holds OFFENCE and DEFENCE as equal weight every session over the member set fixed at month-end (`form_legs`, the same `mean(axis=1)` per session). The header says only "OFFENCE = top third by beta, DEFENCE = bottom third ..., used for the following month" and is silent on intra-month weighting. Added to the silent-choices list (item 8) with the same reading.
- **(b) Other reading implemented.** `BASE_DRIFT`: the same members, equal weights at the month's first session, drifting to month-end, with the same re-formation cost. A book that holds the base under this reading holds that series; nothing else changes. Regression test: `test_R14_drift_base_hand_example`.
- **(c) Stricter of both.** Every gate sign and every leg of the final conjunction must hold under both base readings. Stage 1 records eight gate signs (H1, H3 × two eras × two readings) and one gate result, true only if all hold under both. This can only make passing harder.
- **(d) Disclosed sensitivity on 1998–2019.** The selected H1 setting (h = 3, b = 25, by reference to `1ca5228b3c`) and H3 against the matched mix under the drift base are reported in the R15 rerun beside the committed figures. This is not a re-selection.

## Engine findings F1–F4 (first independent reader, parent rulings about 13:20Z)

- **F1 — loader sealing.** Yahoo parquet files used by v2 (SPY, RSP; later the sector funds) are now read by `load_yahoo_tr`, which filters on the `Date` column at the Arrow level before any pandas frame exists, under the same release guard (`seal_guard`, `assert_window`). Test: `test_F1_yahoo_loader_filters_before_any_frame_and_refuses_after_2019`. The audit of the other loaders is in the lead's report.
- **F3 — false-pivot timing.** The false-pivot table now uses the state held after each close (`post_holdings`), not the state decided at t. Test: `test_F3_false_pivot_uses_held_state_not_decided_state`. The corrected selection-window figures appear in the R15 rerun as a dated erratum, old beside new. They are descriptive only.
- **F4 — tradable fund tier.** Not yet built (`FEE_FUND_BP` is unused). It will be built, tested on pre-2020 fund data only, and independently reviewed before any stage-2 release. Queued after stage-1 readiness; not needed if the gate closes.

## R15 — one selection rerun, after the complete engine change set (parent, about 13:20Z)

- **When:** after the complete engine change set (F1–F4/R14 plus the two 14:00Z reviews). One rerun.
- **Authority:** the parent authorised removing and re-arming the selection run-once guard for that single rerun. To be logged here at that time with the engine commits before and after, every engine change since `1ca5228b3c`, and why each can or cannot move a number. `1ca5228b3c`'s results stay as the superseded record.
- **Pre-check already run (at the F1/F3/R14 head, on 1998–2019):** against the `1ca5228b3c` engine, for all 17 books (four settings × H1, price-only, 2× costs, cash ablation, plus H3), the state series are identical and the maximum absolute daily-return difference is 0.0. It will be repeated on the final engine before the rerun.
- **Annualisation factor on 1998–2019:** exactly 252. `ann_factor` = 252 × sessions ÷ weekday sessions, and there are no Saturday sessions after 1952. Old × 1.0 = new for every annualised figure. This replaces `b7ef827b1d`'s sessions-per-calendar-year factor, a change made before any read.
- **Release:** the release pins the rerun's engine commit and the rerun's selection-results commit (`results_v2_selection_rerun.json`). The runner reads the selected setting from that file and refuses if engine, scripts or tests, or the selection file, differ from the named commits.

## Annualisation and pooling (R15.5)

- **What the frozen JSON says:**
  - **Annualisation:** only "annualised". The contrasts are "annualised mean daily return of H1 minus the exposure-matched static mix ..." and "annualised mean of the paired daily difference H1 - H1_price_only". It states no factor and no sessions-per-year convention. The only "252" in the JSON is in look-back and eligibility windows, never in annualisation.
  - **Pooling:** "Holm p < 0.05 (m=3) on the pooled pre-1998 + 2020-2025 primary contrast". It is silent on how the pooled statistic is formed.
- **Silent, so the pre-read choice stands:** 252 × sessions ÷ weekday sessions, which is 252 on any window without Saturdays.
- **Can it change a SIGN against fixed 252?** No. Within a window or era it is one positive constant multiplying a mean.
- **Can it change the pooled p?** Yes, in principle. Pre-1998 gets a factor above 252 (Saturdays before 1952) while 2020–2025 gets exactly 252. That changes the relative scale of the two windows in the years-weighted pooled mean, and so the p-value. Therefore, by the R14 principle, the pooled conjunction is computed under both conventions (this one and fixed 252), and significance must hold under both.

## F4 — tradable fund tier (parent, about 13:25Z: built in the same engine change set, before the R15 rerun and stage 1)

- **Frozen words built, nothing more** (`historical_tier.tradable_second_confirmation`):
  - **signal:** "both keys computed on the industry portfolios exactly as in the primary test; only execution differs". The header is NOT silent here: the fund tier uses the industry-portfolio H1 state, mapped to fund sessions; nothing is recomputed on funds.
  - **execution:** "SPDR sector funds; offence = three highest trailing-252-session-beta funds, defence = three lowest, beta on data to t-1, re-formed monthly, among funds with >= 252 sessions of history ...; base = equal weight of eligible funds; 5 bp per side". Implemented by `form_fund_legs` (the shared `form_legs` with leg size 3 and `FEE_FUND_BP`), simulated by the shared `rc.simulate` through `simulate_states`.
  - **veto (exact words):** "A pass on industry portfolios with a negative point estimate on the tradable funds in 2020-2025 is reported as 'signal not shown to be tradable', not as a pass." One function, `tradable_veto`; it produces no positive evidence.
- **Data:** only through `load_yahoo_tr`, sealed at 2019-12-31 until a stage-2 release.
- **Silent choices, made now, before any fund number** (items 9–15):
  9. **Beta reference for funds:** SPY total return (the header says "beta" without naming the market for funds; SPY is the fund tier's market and its declared yardstick).
  10. **State mapping:** the fund book holds the industry state decided at the last French industry date on or before each fund session. The two calendars differ only on rare holidays.
  11. **Base readings:** the fund base is built under both R14 readings (equal every session; equal at month start then drifting), and the veto's "negative point estimate" is checked under both.
  12. **Fees in the veto:** the point estimate is checked at 5 bp and at 2× (10 bp), consistent with R13-g(ii)'s stricter reading; any negative estimate fires the veto.
  13. **Contrast:** "point estimate" means the fund book's annualised excess over its own exposure-matched mix of fund offence/defence/base (the same primary-contrast definition as the industry test), mix built on 2020–2025 alone.
  14. **Ties in beta ranking:** stable sort by beta then the fund order XLB … XLC (as the industry legs).
  15. **Named mapping (descriptive, hindsight):** offence XLK, defence XLP/XLU/XLV, the same H1 state, base = all eligible funds; reported beside the tier with no pass/fail.
- **Pre-2020 fund span:** may be printed by the R15 rerun as a labelled descriptive table (not selection, not evidence). Stage 1 does not touch funds.

---

## R16 — nothing that decides pass or fail is written after a gate sign is known (CEO post-review batch 1, about 13:30Z)

Recorded before any pre-1998 or 2020–2025 v2 number exists. Implemented in this change set; tests named in brackets.

- **S1 — the whole stage-2 evaluator and the final conjunction exist now**, pinned by the same engine commit as stage 1 (`final_evaluation`, `conjunction_legs`, `fund_tier` in `scripts/run_rotation_core_v2.py`; primitives `window_arrays`, `bootstrap_draws`, `pooled_weights`, `two_sided_p`, `verdict` in the engine). Tested end to end on a synthetic fixture: pass case, every single-leg fail case (each of the 33 legs is hit), veto case, reproduction refusal on a wrong hash [`test_S1_*`].
  - **(a)** `stage2_release` checks that its `engine_commit` equals the latest stage-1 run's, then the pinned-paths check.
  - **(b)(i) Warm state.** Legs, beta, look-backs, armed memory, state AND holdings come from one continuous run from the first formed legs; each window is scored by slicing from its first date. No cold NEUTRAL restart.
  - **(b)(ii) H2 pooled.** Paired daily difference H1 − price-only; the same years-weighted pooled statistic; the same stratified resample indices as H1 and H3; no mix.
  - **(b)(iii) Holm sidedness.** The header's words: *"Holm p < 0.05 (m=3) on the pooled pre-1998 + 2020-2025 primary contrast"* (`historical_tier.pass_condition`), and *"80% power, Holm m=3"* (`power_statement_top`). It does not name a side. The frozen power figures were computed one-sided: `v2_power/power_v2_D.py:25` `k3 = z(1 - 0.05 / 3) + z(0.8)` and `v2_power/power_h1_actual_D.py:14` `inv_cdf(1 - 0.05 / 3)`, a one-sided critical value. **Dated clarification (2026-11-11, before any read):** one-sided (alternative: contrast > 0) governs, with the centred p of `rc.centred_p`; a two-sided centred p is reported beside it, labelled "not governing".
  - **(b)(iv)** The pooled test must hold under both annualisation conventions (252 × sessions ÷ weekday sessions, and fixed 252); each convention weights the windows consistently (`pooled_weights`) [`test_S1_pooled_weights_*`].
  - **(b)(v) Drawdown.** Checked at the base and at the strict cost run, under both leg readings, on pre-1998 and on 2020–2025. Fund drawdown is reported, not binding.
  - **(b)(vi) Block 63.** The header's only words: *"stationary bootstrap block 21 (63 sensitivity), B=10,000"* (`unchanged`). Not binding: block 21 governs; block 63 is computed with its own seed stream and reported, labelled sensitivity.
  - **(b)(vii)** Every sign leg of every hypothesis is computed at the base and the strict cost run (R18).
  - **(c)** The opening list is the constant `OPENING_HYPOTHESES = ("H1", "H3")`. A stage-1 release may only repeat it; a stage-2 release that names it is refused. Stage 1 neither prints nor writes H2's signs (they are inside the magnitudes hash only). A closed gate records H2 FAILED [`test_S1c_*`, `test_S6_stage1_prints_only_signs_counts_and_hex`].
- **S2, S3, S4, S8** — committed at `48c4d9dd4b` with the signals-only table (0 scored sessions differ in 17 books).
- **S5** — the release pins the selection result by sha256 as well as by commit; `check_engine_commit` covers `engine/`, `scripts/`, `tests/`, the frozen header and every other file the runner reads under `research/rotation_core/` (the superseded selection file `results_v2_selection.json` and `v2_power/FRENCH_SEALED_FULL_FILES_SHA256.txt`); the selection rerun result is pinned separately by commit and sha256; stage 2 verifies the gate file's hash and reproduces the recorded magnitudes hash; a release, gate or selection file whose last commit is not contained in `origin/fable/rotation-core-20261110` after a fetch is refused [`test_S5_*`].
- **S6 — replaces the sealing part of R13.h.** Stage 1 keeps no magnitudes file. It writes only the sixteen gate signs, NaN counts, the strict-run inequality count, integrity counts, the gate result and the sha256 of a canonical serialisation of the magnitudes. A closed gate publishes the magnitudes at once (`results_v2_stage1_pre1998_published.json`). The final run recomputes with fixed seeds and must reproduce the hash before anything prints. An exception during stage 1 prints only its type ("message withheld"). `write_sealed`, the mode-000 file and `open_sealed_stage1` are removed [`test_S6_*`].
- **S7** — template: `stage1.engine_commit`, `stage1.selection_results_sha256`, `stage1.inputs_sha256`, `stage1.versions`; `stage2.stage1_result_commit` names the gate file; `stage2.stage1_gate_sha256`; `stage2.engine_commit`; the opening list is removed from stage 2.
- **S9** — clarification: the arming memory `rolling(arm_memory + 1)` means armed at an age of at most 21 sessions (22 closes) [`test_S9_arming_memory_boundary_21_sessions`].
- **S10** — silent choice: a leg is observed if any member has a close [`test_S10_*`].
- **S11** — confirmation seeds, all in the release-pinned runner (`seeds_record()`): stage-1 standalone `20261113 + c` (block 63: `+ 500000 + c`); stage-2 standalone `20261114 + c` (`+ 500000 + c`); pooled pre-1998 stream `20261115 + c`, pooled 2020–2025 stream `20261115 + 100000 + c` (each `+ 500000` for block 63); c = chunk 0..19 of 500 resamples. **The three Holm contrasts share resample indices**: within one window and block length H1, H2, H3 and all four reading × cost runs use the same indices; the windows are resampled separately (stratified). Selection seeds stay as committed at `1ca5228b3c`.
- **S12** — power keys labelled "Holm" are a normal approximation at the Bonferroni bound; already recorded under "Notes on the frozen header".
- **Forward tier:** index weight is not a start condition; it may be null on any night (narrowness is descriptive with the frozen fallback).

## R17 — the first gate result is final against later fixes (CEO post-review batch 2)

1. Stage 2 can open only if the gate is open in the FIRST committed stage-1 run and in every later rerun of it. A closed gate, on the first run or any rerun, is closed for good for this protocol: later fixes may rerun and report pre-1998 as development data and can never open 2020–2025.
2. After a closed gate, any successor is a new protocol carrying all trials (R13 d). After an open gate, an engine change before stage 2 forces a blind stage-1 rerun whose hash must be reproduced and whose gate must again be open.
3. Enforced in code: the committed gate file carries a monotonic, hash-chained `gate_history` (`append_gate_entry`, `verify_chain`); each entry records `prev_chain_sha256`, the hash of all earlier entries. The runner refuses stage 2 if any entry is closed; refuses to append unless the local history extends the committed remote history (a deleted or rewritten entry is refused); refuses a second stage-1 run at the same engine commit [`test_R17_*`, `test_O8_*`].

R17 was made before any confirmation read; it removes the only path found by which a fail could become a pass.

## R18 — two cost runs (CEO 13:50Z; replaces O3)

**Record of O3.** The CEO's first wording of O3 ("the matched mix pays no cost") was factually wrong: the mix is built from leg returns that are net of the monthly re-formation cost, so it does pay re-formation. The research lead corrected it before anything was built on it. That sentence is struck wherever it was copied; it appears nowhere else in this repository.

1. **BASE run** (governs selection, the primary contrast, the Holm test and the base sign legs) — exactly what the engine computed at selection: legs carry the monthly re-formation cost at leg level at 10 bp; the book additionally pays 100 % out and 100 % in at each state switch; the matched mix is built from the same net legs and pays nothing for its daily rebalancing across legs. The one direction that favours the book: charging the mix's re-formation at leg level instead of netted across legs charges the mix the same or more in months when a member moves between legs or base membership changes. **Size on 1998–2019, counts and traded weight only, no return** (`v2_power/netting_counts_R18.py`, `.stdout`): 265 formations; months in which a member moved between offence and defence: 0; months with a base membership change: 0; months in which leg-level and netted traded weight differ: 0 for H1 (h3 b25), its price-only control and H3; traded weight per year, leg-level minus netted: 0.0000 for all three. On 1998–2019 the two charges are identical. Pre-1998 (industries entering the base) can differ; it is sealed and not measured.
2. **STRICT run** — what "holds at 2× costs" means from now on, covering the whole conjunction (every sign leg, the pooled test under both annualisation conventions, the drawdown leg), under both leg readings: the book pays 20 bp per side on state switches AND 20 bp on the monthly re-formation of whatever it holds; the matched mix is built on GROSS leg returns and pays nothing; signals are unchanged (the relative line stays net at 10 bp, computed once). On every session the strict book return is no higher than the base run's and the strict mix return no lower, so the strict excess bounds every milder cost reading from below. Asserted session by session in a fixture test and counted at run time; a non-zero count is an integrity failure that closes the gate [`test_R18_*`, `test_O1_*`].
3. The 10 bp reproduction against `1ca5228b3c` stays exact (`v2_power/repro_check.stdout`: scored sessions identical in all 17 books, maximum daily-return difference 0.0; warm-up sessions before 1998 changed by S2: H1-family books NEUTRAL on at most 133 sessions, 1997-01-02 → 1997-07-30; H3 without a state on 253 sessions, 1996-07-31 → 1997-07-30). In the single R15 rerun the only selection-file figures that change are the 2× rows, shown old beside new (`H1_at_2x_costs_before_R18_superseded`). The fund tier follows the same two runs (5 bp base; 10 bp on switches and re-formation with a costless mix for strict). The printed gate signs are sixteen: H1 and H3 × two eras × two leg readings × {base, strict}.

R18 was made before any confirmation read and without a return; the base reading is unchanged from the engine that produced selection; the strict reading can only make passing harder.

## Conventions O1–O8 (CEO post-review batch 2 and 13:46Z)

- **O1 — relative line net of re-formation cost.** The net-of-re-formation-cost relative line governs because it is the reading under which the frozen signal counts were produced (97 qualifying / 83 firing at h=3; the gross reading gives 96 / 82). When the convention was recorded, the CEO had also been told its measured effect on the already-examined 1998-2019 selection window (six state-days, 0.02 pp/yr, no sign or selection change). No confirmation-window number existed. (i) The line is computed once, at the base 10 bp, by `relative_line(legs)`; no state function takes a cost argument; the state series and every execution are identical in the base and strict runs [`test_O1_states_identical_at_10_and_20bp_signal_line_computed_once`].
- **O2 — arming memory of 22 closes** stands (S9).
- **O3** — replaced by R18.
- **O4 — warm-up padding** fixed by S2.
- **O5 — NaN.** A NaN gate statistic is neither sign (`sign()` returns "NaN"); the gate fails closed; the run prints `NaN_count` for each of the sixteen statistics (non-finite statistic plus non-finite book days in the era); a non-zero count is an integrity failure reported as such [`test_O5_*`].
- **O6 — inputs pinned.** The release carries `inputs_sha256` (sha256 of every input file's bytes) and `versions` (python, numpy, pandas, pyarrow, scipy); the runner refuses on mismatch; the gate entry records both. `--manifest stage1|stage2` prints them [`test_O6_*`].
- **O7 — fixture dry run.** Refused unless the directory carries `FIXTURE_MANIFEST.json` whose sha256 values match the files and none of which equals a real input's hash (readable real inputs hashed; sealed French files from the recorded hashes). Every printed line begins "FIXTURE" [`test_O7_*`].
- **O8 — run once.** The guard state is the committed file on the remote branch plus the chained `gate_history`; a deleted local marker cannot allow a second first run (stage 1, the selection rerun and the final run) [`test_O8_*`].

O1–O3 are conventions, not corrections; not eligible as a later engine fix.

## Limits (added)

- Pre-1998 data is sealed by procedure only: the files are on disk and ordinary code can read them. The protection is the committed release, the commit pins and the record, not a technical lock.
- What remains procedural after R20 (unchanged): anyone can call the engine and runner functions directly from Python (for example `pre1998_report(IND_D, FACT)`, or `stage1_command` with an in-memory ledger), bypassing `main`, the ledger, the release checks and the loader guard. The recorded tool path (`scripts/run_rotation_core_v2.py --stage …`) cannot do so: it fetches (failing closed), replays the ledger, writes every record to the remote before going further, and the fixture dry run takes no path. The protection against a direct call remains the record and its review, not code.
- Industries or sectors agreeing are never presented as that many independent confirmations: 49 industries at typical pairwise correlation are roughly 2 to 2.5 independent bets by the equal-correlation formula (8 to 12 by eigenvalue count); breadth is described as a share of members, not a count of confirmations. This rule applies to every results file and the PR draft.

## Declared successor ideas, not started, not a trial of v2

- An event study of the industry-breadth washout against a price-only twin (date-clustered, base rate beside hit rate). In v2 the washout sits in H1's ATTACK key in both arms, so v2 measures what breadth adds to arming, not what the washout adds to re-entry. Declared before any outcome and computed by nobody. It does not change the 55-trial count.

## Conventions and silent choices as they now stand (numbered; one list for the outside readers)

Items 1–15 are unchanged from above (amendment h items 1–8; F4 items 9–15), except item 5 (now R18) and item 7 (struck by S1c).

1. Era-level mix built on the era alone, for the gate and the final conjunction.
2. Annualisation 252 × sessions ÷ weekday sessions; the pooled test also under fixed 252; both must hold.
3. Pooled construction: each window its own mix; stratified bootstrap; years-weighted mean of annualised window statistics.
4. First scored session 1928-01-02.
5. "Holds at 2× costs" = the R18 strict run over the whole conjunction.
6. Drawdown no worse than the matched mix, on pre-1998 and on 2020–2025 separately, at both cost runs and both leg readings.
7. *(Struck by S1c.)* H2's stage-1 signs are neither printed nor written; H2 cannot open the window.
8. Intra-month leg weighting: equal every session over the month-end member set (R14(a)).
9. Fund beta reference: SPY total return.
10. Fund state mapping: the industry state at the last industry date on or before each fund session.
11. Fund base under both R14 readings.
12. Fund veto checked at the base (5 bp) and strict (10 bp switches and re-formation, costless mix) runs; any negative estimate fires it.
13. Fund point estimate = the fund book's excess over its own matched mix on 2020–2025 alone.
14. Beta ties: stable sort, fund order XLB … XLC.
15. Named mapping XLK vs XLP/XLU/XLV: descriptive, hindsight, no pass/fail.
16. **S2:** every 126-session quantity needs 126 formed-leg sessions and the SMA 50; before that the book is NEUTRAL and unarmed; H3 has no state before its momentum exists.
17. **S3:** a missing industry-day is not a close: the level carries, the SMA is over the last 50 observed closes, and the industry is out of that day's breadth numerator and denominator.
18. **S4:** the second reading drifts all three legs; signals stay on the governing reading (the header's words "used for the following month" and "rebalanced monthly" govern membership and the base; signals depend only on membership and the governing line).
19. **S9/O2:** arming memory = armed at an age of at most 21 sessions (22 closes). Clarification.
20. **S10:** a leg is observed if any member has a close.
21. **S11 / R21.4:** every confirmation stream is `numpy.random.SeedSequence(20261113, spawn_key=(stage, window, block, chunk))` with stage ids stage1 = 1, stage2 = 2, pooled = 3, rehearsal = 4 and window ids pre1998 = 1, h2020_2025 = 2, rehearsal_1998_2019 = 3, so every stream is distinct by construction (a test enumerates all 160 keys at B = 10,000 and their generated states). H1, H2 and H3 share indices within one window and block length. The 1998–2019 selection seeds are unchanged ("left as committed").
22. **S1b(i):** warm state and warm holdings; scoring by slicing.
23. **S1b(ii):** H2 pooled = paired difference, same weights and indices, no mix.
24. **S1b(iii):** one-sided Holm governs; two-sided reported, labelled.
25. **S1b(vi):** block 21 governs; block 63 reported as sensitivity.
26. **O1:** the relative line is net of re-formation cost at 10 bp, computed once. Convention, not a correction.
27. **R18 base run:** leg-level re-formation at 10 bp inside the legs; switches 100 % out and in; the mix on the same net legs, no cost for its daily rebalancing. Convention, not a correction.
28. **O5:** NaN is neither sign; fails closed; an integrity failure closes the gate.

**New silent choices made in this change set, without data (for ruling):**

29. ~~Integrity failure closes the gate for good.~~ *Replaced by R19.1: an integrity failure is an INTEGRITY_ABORT before any sign exists, not a gate result.*
30. **H2's drawdown leg (R19.2: accepted as a dated clarification, base and strict).** H2 has no matched mix. The leg is read as "H1's drawdown no worse than the price-only control's" (the yardstick of H2's own contrast), on both windows, both cost runs and both readings.
31. **Fund veto for H2 (R19.3: accepted).** The fund point estimate for H2 is the paired difference of the fund-executed H1 and price-only books on 2020–2025; any negative estimate fires the veto, as for H1 and H3.
32. ~~Gate integrity counts also close the gate.~~ *Replaced by R19.1: integrity counts are settled in Phase A, before any sign; the gate result is the sign condition only (exactly eight signs per hypothesis, R20.3).*
33. **Two-sided p (R19.4: reported only, labelled "not governing"):** centred, (1 + #{finite d: |d − obs| ≥ |obs|}) / (B + 1). **Governing one-sided p, beside it for the reviewers:** (1 + #{finite d: d − obs ≥ obs}) / (B + 1) (`rc.centred_p`; non-finite draws never count as exceedances).
34. **2020–2025 yardsticks (R19.5: descriptive only; enter no pass condition; labelled so where printed):** SPY, RSP (Yahoo total return), BASE and the French market (added for continuity with pre-1998); named episodes E2020, E2022, E2025 from the v1 header's windows.
35. **Descriptive state split (R19.5: descriptive only; enters no pass condition):** H1's excess over the mix by the leg held that day (the largest start-of-day weight).
36. **A stage-1 rerun at the same engine commit is refused** once a gate record exists (R19.6); the stage-2 run reproducing the stage-1 magnitudes hash is the reproducibility proof. *Amended by R20.1:* after a Phase-A-clean run with no gate record, the identical rerun is required and is the only permitted action.
37. **(R19.7: accepted.) Selection rerun output** goes to `results_v2_selection_rerun.json` and `RESULTS_V2_SELECTION_RERUN.md`; `1ca5228b3c`'s files stay as the superseded record; the run-once guard reads the remote branch.

## R19 — integrity is not a gate result (CEO, about 14:30Z; recorded before any confirmation read)

1. **Two phases inside one command.** Phase A (integrity only) is computed, printed and recorded before any gate statistic or sign exists. It covers: input hashes; versions; the engine-commit check; every NaN count, per book × window × leg reading × cost run (non-finite book returns, non-finite weights, held legs with a non-finite return, cash held on a day with a non-finite rate, an empty window); the strict-inequality count (book against the same book at two cost levels, and legs against the same legs; nothing book against mix); held legs with no observed member close; and warm state (a state on every scored session, holdings carried in from before the window). Phase A is counts and booleans only: no mean, sum, cumulative return or drawdown, and no comparison of a book with its mix. An AST test pins the functions Phase A may call (`test_R19_phase_a_calls_no_gate_statistic_function`).
   - **If Phase A is not clean:** `INTEGRITY_ABORT`. No gate statistic is computed in that process, no sign is printed or written, and no gate record is made. The abort record (time, engine commit, the non-zero counts, no magnitudes) goes to the run ledger. It is not a gate result and does not close the gate.
   - **After an abort:** a fix is a new engine commit. It must leave every 1998–2019 scored state and 10 bp series identical (repro_check, the same two lines). It needs a new release from the CEO naming the new commit and citing the abort record (`ledger_records_cited`). The CEO will not release after an abort unless the cause is shown to be data or code handling of missing values, not anything touching the rule. Each abort is disclosed in the results.
   - **Only a clean Phase A** lets Phase B compute the sixteen signs. From that point R17 applies in full.
   - **The same two phases open the stage-2 final run:** an abort there comes before any 2020–2025 number.

   An abort reveals no sign, so repair after it is not repair after a result; R16 and R17 are unaffected.
2. **(item 30)** Accepted as a dated clarification: H2's drawdown leg is H1's drawdown no worse than the price-only control's, at base and strict.
3. **(item 31)** Accepted: H2's fund veto is the paired difference of the fund-executed H1 and price-only books.
4. **(item 33)** Accepted, reported only, labelled "not governing"; the governing one-sided formula is stated beside it in the list.
5. **(items 34, 35)** Accepted as descriptive only; neither enters any pass condition. The results label them so where they are printed.
6. **(item 36)** Accepted: a stage-1 rerun at the same engine commit is refused; the stage-2 final run reproducing the stage-1 magnitudes hash is the reproducibility proof. (Amended by R20.1.)
7. **(item 37)** Accepted.

Tests: `test_R19_*`, among them a NaN in one leg and a strict-inequality violation, each aborting with no sign in stdout or the ledger; a clean fixture proceeding with Phase A printed before the first sign; and the stage-2 abort before any 2020–2025 statistic.

## R20 — the runner writes the record (CEO, after the independent re-implementer's review of `0eeca4f5ea`)

The reviewer found three blockers in the enforcement of R17 (X1 an unpushed closed run is invisible; X2 a re-chained history passes; X3 `gate_open` is trusted) and five must-fix items (Y1–Y5). Each reproduction in `review_opus/synthetic2/guard_breaks.py` is now a test that fails to bypass (`test_R20_case1…case5`).

1. **One append-only, hash-chained run ledger** (`research/rotation_core/results_v2_run_ledger.json`), committed on the remote branch by the runner itself (`GitLedger`). Each entry is a commit built from a temporary index on top of the just-fetched remote head and pushed. The working tree is touched only after the push succeeds, and the runner refuses to go on if a push fails. The ledger replaces the gate file and the separate `integrity_aborts` file.
   - (a) **START** (release sha256, engine commit, input hashes, versions, time) is pushed before anything is loaded.
   - (b) **INTEGRITY_ABORT** (counts only) **or PHASE_A_CLEAN** is pushed before any gate statistic is computed.
   - (c) **GATE** (sixteen signs, counts, magnitudes sha256, gate_open) is pushed before any sign is printed or written elsewhere. If that push fails, nothing about signs is printed and the run exits non-zero. Stage 2 ends with a **FINAL** record (verdicts, results hash), pushed before any result is printed or written.
   - **State rules** (`start_allowed`), enforced at the start of every stage-1 and stage-2 invocation, on the remote after a fetch that must succeed, and replayed over the whole ledger (`validate_ledger`):
     - START with no outcome: only the identical rerun is allowed, or a new engine commit under R19 (new release, citation).
     - INTEGRITY_ABORT: no sign existed; a new engine commit under R19 only.
     - PHASE_A_CLEAN with no record: the ONLY permitted action is the identical rerun (same stage, release, engine commit and input hashes); any other engine commit or release is refused, permanently.
     - A closed GATE: final; every later stage-1 and stage-2 invocation refuses, at any engine commit.
     - A FINAL: nothing further runs.
     - An open gate: a stage-1 rerun needs a new engine commit and a new release (R17.2), and stage 2 must use the latest gate's engine commit.
   - **Release history:** every version of every release file committed on the remote must map to a ledger START, or be listed as unused in a later version's `supersedes_unused_releases` (a CEO commit that says so; `check_release_history`).
   - The local branch must equal the fetched remote head before anything runs.
2. **(X2)** Every committed version of the ledger on the remote branch must be a prefix of the current one; checked in stage 1 and stage 2. A dropped or re-chained entry refuses.
3. **(X3)** Nothing recorded is trusted where it can be recomputed.
   - Stage 2, after reproducing the magnitudes hash, re-derives the gate decision from the reproduced numbers and requires it open, with its signs equal to the recorded ones.
   - Any GATE entry whose `gate_open` disagrees with its own signs refuses, at ledger validation and at the stage-2 release.
   - `gate_decision` requires exactly the eight keys per hypothesis; an empty, short or extra key set is closed.
4. **(Y1)** The fixture dry run takes no path: `--dry-run-stage1-fixture` builds its inputs in memory from the committed seeded generator (`tests/rotation_core_v2_fixture.fixture_texts`, seed 7); the loaders accept in-memory text; it writes to an in-memory ledger only; every line is stamped FIXTURE. O7's manifest guard is removed. What remains procedural is stated under Limits.
5. **(Y2)** The remote fetch fails closed and returns the sha it fetched; every remote check takes that sha, never a stale ref.
6. **(Y3)** The reproduction hash and the recorded gate signs are required arguments of `final_evaluation`: no default, no None.
7. **(Y4)** Stage 2 verifies, in order: the ledger, the release, the engine commit. Then `stage2_opened` unseals the sealed files (mode 0400) inside the runner, checks them against the recorded sealed hashes (`v2_power/FRENCH_SEALED_FULL_FILES_SHA256.txt`) and the release manifest, opens the loaders, and re-seals (mode 000) and closes on exit, whatever happens. The loader guard no longer reads a release itself; it is open only inside that verified context. Code and fixture-tested only; no sealed file was touched.
8. **(Y5)** The engine-commit check refuses:
   - modified or untracked files under the pinned paths;
   - `PYTHONPATH` being set;
   - a loaded `usercustomize`;
   - a covered module (`engine.`, `scripts.`, `tests.`) imported from outside the repository or differing from its blob at the engine commit.

   **Implemented with one amendment, for ruling** (the literal text cannot be met on this host). The interpreter here always loads the distribution's own `sitecustomize` (`/usr/lib/python3.12/sitecustomize.py` → `/etc/python3.12/sitecustomize.py`, Ubuntu's crash-report hook). Only `-S` suppresses it, and `-S` also drops the virtual environment's site-packages, so numpy would not import. A literal "refuse if sitecustomize is loaded" therefore refuses every run. As implemented, a sitecustomize from any location other than the interpreter's standard library is refused, and the loaded file's sha256 is part of `versions()`, so the release manifest pins it and any change refuses.
9. **(S5)** The stage-1 path checks that the selection rerun's commit is contained in the fetched remote head and that the selection file (and the release file) on disk equals the remote's.
10. **Planted-edge fixtures** run end to end through the command path (`stage1_command` → ledger GATE → stage-2 release verified against the ledger → `stage2_opened` → `confirm_command` → FINAL), with the verdict asserted exactly. The vacuous end-to-end test is replaced.
    - **Pass:** H3 "survives falsification on history" with 0 of 33 legs failed; H1 and H2 FAIL.
    - **Late failure:** H3 FAIL on exactly the four `sign|h2020_2025|*` legs.
    - **Veto:** H3 "signal not shown to be tradable", fund veto fired.

    The planted regime is a ±0.15 %/day drift of the top beta third against the bottom third, alternating every two calendar years. The late-failure fixture uses a ±0.04 %/day regime alternating every two months from 2020. The veto fixture reverses the regime on the funds. All synthetic, B = 200.
11. Phase A prints counts only and always leaves its ledger entry. Once PHASE_A_CLEAN is pushed, a failure during sign computation is recorded as nothing else (the run stands as clean-without-record: identical rerun only); it can never become an abort (`test_S6_exception_text_carries_no_value` checks the ledger after each failure).

**Template:**
- the stage-2 release pins the ledger prefix (`ledger_prefix_len`, `ledger_prefix_chain_sha256`) instead of a gate-file hash;
- both releases may carry `ledger_records_cited` (R19) and `supersedes_unused_releases` (R20.1);
- `versions` carries `sitecustomize_sha256`.

**Test set (the one both readers should run):**

```
python -m pytest -q tests/test_rotation_core_v2.py tests/test_rotation_core_v2_funds.py \
  tests/test_rotation_core_si_findings.py tests/test_rotation_core_v2_confirm.py tests/test_rotation_core_evaluation.py
```

The reviewer's 79 at `0eeca4f5ea` were the first four files. The lead's 118 included `tests/test_rotation_core_evaluation.py` (39 tests, the shared simulator and statistics of `engine/rotation_core_evaluation.py`, which v2 imports). Per-file counts at the final commit are in the lead's report.

## R21 — Phase B failures, retry rules, non-finite statistics, streams, rehearsal (CEO 15:20Z)

0. **sitecustomize.** Final under R22.4 below.
1. **An exception in Phase B** (amends R20.1 for PHASE_A_CLEAN without a record).
   - After a clean Phase A, any exception while Phase B computes makes the runner push a GATE with `gate_open: false`, `closed_by: "phase_b_exception"` and the exception's type name only (no signs, no magnitudes, no message). That GATE is a closed gate under R17, final at any engine commit. The exceptions excluded are `MemoryError`, `OSError`, `KeyboardInterrupt` and `LedgerPushFailed`.
   - In stage 2 the same rule records FINAL with every hypothesis FAIL and the same `closed_by`.
   - For the four excluded types, and for process death, the PHASE_A_CLEAN entry stands and only the identical rerun is permitted.
   - *(Note superseded by R24.1: the stage-1 reproduction is now Phase A2, before Phase B, and `SealedRefusal` is not exempt.)*
2. **Retry rules, stated once.**
   - (i) **INTEGRITY_ABORT:** never retried at the same engine commit (R19).
   - (ii) **START with no Phase A outcome** (a failure in preparation or in Phase A code, before any statistic): a rerun at the same engine commit is permitted only under a new release that lists that START in `ledger_records_cited`. A rerun at a new engine commit follows R19's conditions. Nothing was computed, so neither is repair after a result.
   - (iii) **PHASE_A_CLEAN without a record:** R20.1 as amended by R21.1 and R23.1.
   - (iv) **A closed GATE:** final.
3. **Non-finite statistics.**
   - Phase A is unchanged: inputs only; book against the same book, legs against the same legs; never book against mix.
   - A non-finite value in a Phase B statistic is not an abort. Its sign is not "+", and it is counted in the `integrity` block (`nonfinite_gate_statistics` at stage 1; `nonfinite_statistics_by_hypothesis` at stage 2).
   - A non-finite pooled p enters Holm as 1 (never rejected) and is counted (`holm_safe`).
   - Every hypothesis a non-finite statistic touches fails its integrity leg.
4. **Bootstrap streams:** SeedSequence spawn keys; see list item 21.
5. **Smaller items.**
   - (1) Fund drawdown of the fund-executed book and of its matched mix is reported, descriptive only; it is not a leg of the veto.
   - (2) The result text states: "Pre-1998 figures come from the through-2019 French file and the warm 2020 state from the full file's own history, both pinned by sha256 in the release manifest."
   - (3) Accepted conventions, wording only:
     - the monthly reset of retained members to equal weight is not charged under the drift reading, which affects only the stricter extra reading;
     - a book switching into a leg at month-end also pays that leg's re-formation charge the next day, which is conservative.
   - (4) S8's count covers eligible industries only, not the header's 366 scope. The printed key is `dropped_industry_days_unique_eligible_industries_only`.
   - (5) The selection-rerun file's on-remote check is in `stage1_release` (`on_remote(selection, …)`).
6. **Rehearsal (`--rehearsal`).**
   - The complete stage-1 command (START, Phase A, Phase B, GATE; the same functions and ledger code) runs on the open 1998–2019 window only, with pseudo-eras 1998–2008 and 2009–2019, against a temporary bare remote. It never touches the real ledger or a release file, and every line is stamped `REHEARSAL`.
   - Inputs are built in memory from the through-2019 files, keeping lines dated 1996-01-02..2019-12-31 by the date field alone. Any input whose first date is before 1996 or whose last date is after 2019-12-31 is refused.
   - Its numbers are on an already-examined window and are evidence of nothing.
   - Not run until authorised with the selection rerun.

## R22 — the host's own record decides; ancestry pins; outside witness (CEO, after the SI reader's addendum)

**Probe of `GET /repos/{owner}/{repo}/activity`, 2026-11-11 15:22Z.**
- **Documentation:** `activity_type` ∈ {`push`, `force_push`, `branch_creation`, `branch_deletion`, `pr_merge`, `merge_queue_merge`}; cursor pagination via the Link header; no retention limit is stated.
- **Scratch branch** `fable/rotation-core-ledger-probe-20261111` (two content-free commits on the freeze commit's tree; deleted at the end). The log read after each step was:
  1. `branch_creation`;
  2. `+ push`;
  3. `+ force_push`;
  4. `+ branch_deletion`;
  5. `+ branch_creation` (re-created);
  6. after the final deletion, `+ branch_deletion`.
- **History is NOT lost on deletion:** the re-created branch's log still shows the earlier creation, the push, the force push and the deletion.
- **Pagination** (`per_page=2`) returned all entries through the Link cursor.
- The recorded log is `tests/data/rotation_core_activity_probe_20261111.json`.

1. **On every invocation** of stage 1, stage 2 and the selection-rerun check, after the fetch and before anything else, the runner reads the whole log (all pages, `gh api --paginate`) and refuses unless:
   - (a) the call succeeded and parsed;
   - (b) the first entry is the branch's single `branch_creation` and every later entry is a plain `push`; any `force_push`, deletion or second creation refuses permanently;
   - (c) the entries form one unbroken chain (`before` = previous `after`) from that creation, and the anchor commit lies inside it;
   - (d) the newest `after` is the fetched head.
   - **Anchor (a factual note on R22.1(c)):** the freeze commit `ac68f2e72a4de055c36b048cb02301ccd7544964` is not itself a push boundary. It arrived inside the push `3f5b44f3c6 → af488e68dd` (12:32:42Z), so no entry has it as `before` or `after`. The check therefore requires the chain to be complete from the branch's creation, and the anchor to be an ancestor of some entry's `after` and not of its `before`. This is at least as strict as "from the anchor".
   - The entry count and the sha256 of the canonical (type, before, after) list are recorded in every ledger entry (`host`).
   - On the real branch at `343347ea6b`: 34 entries, one chain, anchor inside, ruleset active.
2. **No forced fetch.** The refspec has no `+`, so a non-fast-forward remote refuses. Each release pins `branch_head_at_release`, which must be an ancestor of the fetched head. The stage-2 release also pins `gate_commit`, which must be an ancestor and must contain the latest GATE entry.
   - **Declared limit (R24.2, restated by R25.4):** the local layers (non-forced fetch, ancestry pins) miss ANY rewrite whose new head still descends from `branch_head_at_release`. Examples: a rewind to the START commit, or a rewind plus re-appended commits, seen from a fresh clone. The ruleset (27041175, which forbids the rewind), the activity log (which records it as `force_push`) and the outside witness (which holds the shas outside this repository) catch all of them. Tests cover the host layers.
3. **Outside witness.**
   - The runner prints `WITNESS start_commit <40-hex>` after START, and `WITNESS gate_commit <40-hex> ledger_index <n>` after a successful GATE push and before any sign.
   - The stage-2 release carries `witnessed` (the two shas and the acknowledgement times, filled by the CEO); the final result text cites it.
4. **Start-up code, and push-state messages.**
   - (1) Every module in `sys.modules` with a `__file__` must have its REAL path under the interpreter's stdlib, platstdlib, purelib, platlib or the repository; otherwise the run refuses. `versions()` pins `pth_sha256`, a sha256 over the sorted (relative name, sha256) of every `*.pth` in every site directory, and `pth_count`.
   - **The sitecustomize deviation is accepted with these additions.** On this host the one loaded module whose real path is outside those roots is the distribution's `sitecustomize` (`/usr/lib/python3.12/sitecustomize.py` → `/etc/python3.12/sitecustomize.py`). It is accepted only where its link sits in the stdlib directory, with its content pinned (`sitecustomize_sha256`).
   - (2) A push that did not confirm reports its state as UNKNOWN. The next invocation's fetch decides, and a gate record on the remote is final.
   - (3) `main` passes the selection file as a parameter and never writes `v2.SELECTION_RESULT`.
5. **Tests that now exercise their claim:**
   - prefix and rewrite tests through a real temporary remote;
   - force-push-back-before-START and delete-and-recreate against a temporary bare remote (non-forced fetch and ancestry pin; the host record for the fresh-clone case);
   - activity-check tests on recorded JSON (clean chain, `force_push`, deletion, broken chain, truncated log, wrong head, other ref, API failure, unparsable body);
   - the selection on-remote refusal asserted by message;
   - the sitecustomize and `.pth` pins asserted by value and by refusal.

## R23 — the reviewer's delta (CEO)

1. **"Identical rerun only" binds permanently.** `start_allowed` scans ALL runs. A run with PHASE_A_CLEAN and no record, not later completed by a run of the same identity, binds every later START to its identity, whatever came after. This holds for stage 1 (GATE) and stage 2 (FINAL). The reviewer's D1 and D2 are tests that refuse. With this rule the GATE blob left in the local object store by a failed push is harmless: the forced rerun is deterministic. (N2) `append` re-evaluates the START's state rules on the freshly fetched entries, immediately before building the commit.
2. **Ruleset 27041175** (`rotation-core-ledger-append-only`, rules `non_fast_forward` and `deletion`). After the fetch, the runner reads `GET /repos/…/rules/branches/<branch>` and `GET /repos/…/rulesets/27041175`, and refuses unless both rules are present, `enforcement == "active"` and `bypass_actors == []`. The ruleset id and `updated_at` are recorded in every ledger entry. The activity chain (R22.1) still catches "ruleset off, rewrite, ruleset on".
3. **Remote identity.**
   - The run refuses unless `git remote get-url origin` and `git remote get-url --push origin` both equal `https://github.com/mastermindx-market-intelligence/macro.git`.
   - It refuses any `url.*.insteadof` or `url.*.pushinsteadof` at any level; this check runs first, because a rewrite changes what `get-url` reports.
   - It refuses any `GIT_CONFIG*` environment variable.
4. **Interpreter environment.**
   - `PYTHONSTARTUP` and `PYTHONHOME` refuse, as `PYTHONPATH` does.
   - The location test compares REAL paths; a test plants a link inside an allowed root that points outside, and it refuses.
   - The documented sealed-run command line is `python -E scripts/run_rotation_core_v2.py --stage …`.
5. **Phase A is an allowlist.** Every call in the four Phase A functions must be in an explicit set, never an arithmetic reduction. Every comparison must be one of the 17 reviewed forms present today. Arithmetic is limited to boolean masks, sums of counts and three reviewed tolerance and weight expressions. The checker rejects `count_nonzero(r > 0)`, a reduction, book-minus-mix, `mean`, `cumprod` and `max` (tests).
6. **The planted edges run through `main()`** with the real `GitLedger` on a temporary bare remote, using real release files committed and pushed there. Two things are stubbed, through `Ctx` passed as `main(_ctx=…)`, which the command line and environment never set:
   - the host API, with a chain built from the temporary remote's own history;
   - the engine-commit check, because the test tree is not a commit.

   The verdicts are as asserted. This replaces the in-memory end-to-end runs.
7. **The fund veto fails closed:** it fires unless every estimate is finite and ≥ 0. A non-finite estimate is also counted in integrity (R21.3).
8. **Test counts** come from one `--collect-only -q` at the final head (in the lead's report).

**Sealed-run command lines:**

```
python -E scripts/run_rotation_core_v2.py --stage pre1998
python -E scripts/run_rotation_core_v2.py --stage confirm
```

## R24 — rulings on the lead's five points (CEO)

1. **A refusal in Phase B.**
   - (a) **Phase A2: reproduction.** In stage 2, reproducing stage 1 is an integrity check on a window already released and read; it reveals nothing new. It runs after Phase A and before any 2020–2025 statistic: the magnitudes hash must equal the stage-1 GATE record's `magnitudes_sha256`, and the gate re-derived from the reproduced numbers must be open with signs equal to the record.
     - **Outcome pushed before Phase B:** `REPRODUCTION_OK`, or `INTEGRITY_ABORT` with `reason: "stage1_not_reproduced"`. An exception during the reproduction gives `INTEGRITY_ABORT` with `reason: "stage1_reproduction_exception"` and the type only. In either abort case no 2020–2025 number is computed and nothing is printed but the reason.
     - **Governed by R19:** an abort is not a final run and records no FINAL. A later run needs a new release from the CEO citing it, and can proceed only when the reproduction matches the recorded hash exactly. The stage-1 GATE record and its `magnitudes_sha256` are the fixed reference; no engine commit may change them.
     - **Ledger order:** FINAL requires REPRODUCTION_OK.
   - (b) **`SealedRefusal` is not exempt**, whatever its base class. It is caught explicitly before the `OSError` exemption; `LedgerPushFailed` stays exempt.
     - Raised in Phase B, it is recorded like any other Phase B exception: stage 1 records a closed GATE, stage 2 a FINAL with every hypothesis FAIL, both with `closed_by: "phase_b_refusal"` and the type only.
     - The design goal is that no refusal is reachable after that point.
     - Tests: a planted refusal in each stage asserts the record; a reproduction mismatch leaves INTEGRITY_ABORT and no FINAL.
2. **Declared limit:** a fresh clone rewound exactly to the release head is caught only by the host layers (ruleset 27041175 and the activity log's `force_push` entry) and by the outside witness, not by the local ancestry pin. (Written beside the three layers under R22.2.)
3. **The anchor:** chain complete from the branch's creation, anchor inside one push. Accepted, stricter than the original wording.
4. **sitecustomize:** the distribution `sitecustomize` keeps the one exception. Its link sits in the standard library and its content hash is pinned by the release; every other module is checked by real path. Accepted.
5. **The test context:** accepted, with tests that:
   - `main()` called as the command line calls it (no `_ctx`) runs the REAL host check (`api` None, so `gh api`) and passes the REAL engine-commit check to the release check, then refuses for lack of a release;
   - the argument parser exposes no option, and `main`, `Ctx`, `verified_ledger` and `run_once_guard` read no environment variable, that could set the test context.

## R25 — seen but unrecorded; Phase A pin; tools (CEO, after the reader's delta on `0f45b94510`)

0. **Accepted as built:** an exception during the stage-2 reproduction of stage 1 is INTEGRITY_ABORT, reason `stage1_reproduction_exception`.
1. **Seen but unrecorded.**
   - (a) **`-E` is enforced.** The runner refuses before anything else unless `sys.flags.ignore_environment` is set and `sys.flags.inspect` and `sys.flags.interactive` are both zero.
   - (b) **No live frame after a failure.** From the first sealed statistic to the pushed record, every `BaseException` ends in `_hard_exit`: one fixed line with the exception TYPE only (no traceback, no value), then `os._exit(5)`. This covers Phase B and the GATE, REPRODUCTION_OK and FINAL appends, including a fetch failing inside `append` after Phase B (the reader's case, now a test through `main()` in a real `python -E` process). The R21.1/R24.1 classification of which record is written is unchanged.
   - (c) **Default-closed.** A PHASE_A_CLEAN with no GATE (stage 1) or no FINAL (stage 2) on the remote is a closed result for every purpose, from the moment PHASE_A_CLEAN is pushed, with no time window, until an identical rerun pushes a record.
     - `--ledger-report` prints and writes it (`results_v2_ledger_status.json`, `RESULTS_V2_LEDGER_STATUS.md`): historical tier FAIL, or every hypothesis FAIL, "closed by rule R25.1: Phase A clean, no record on the remote". It publishes under S6.
     - Stage 2 can never start on it.
     - The identical rerun stays permitted and is the only thing that can change it.
   - (d) Superseded by R26.1: fixed, not declared.
2. **Phase A pinned by syntax-tree hash.**
   - The normalised syntax-tree sha256 of each Phase A function (`ast.dump`, no positions) is computed by the runner at import. It is written into `versions()` (pinned by the release) and into every ledger entry, and pinned in the test.
   - The development guard also allowlists every assignment in the four functions, so the reader's two rebinding cases fail it (tests).
   - Remaining gaps (`Subscript`, the argument of `int(...)`) are covered by the hash pin.
3. **`git` and `gh` by absolute path.** Each is resolved once, never through PATH, as `/usr/bin/<name>` or `/usr/local/bin/<name>`. It must have its real path under one of those directories and not be writable by group or other. Both are called by that path everywhere; path and `--version` are recorded in `versions()`.
4. **Wording:** R24.2's declared limit is restated as the reader found it (see R22.2 above).
5. **An object body fails closed.** A 200 response whose body is an object (or whose entries are not activity objects) is a `SealedRefusal` with a plain message, before START.

## R26 — the Sector Intelligence reader on `0f45b94510` (CEO)

1. **A failed push leaves nothing on disk.**
   - Inside `GitLedger.append`, every object is written into a private object directory (`tempfile.mkdtemp`, mode 700, prefix `rc_ledger_objects_`). It is used as `GIT_OBJECT_DIRECTORY` with `GIT_ALTERNATE_OBJECT_DIRECTORIES` pointing at the real store, for `hash-object`, `read-tree`, `update-index`, `write-tree`, `commit-tree` and `push` only.
   - The directory is removed in every outcome inside `append` (a `finally` that runs before the exception leaves `append`, so before any `_hard_exit`). The fetch after a successful push brings the objects into the real store.
   - Every invocation, before anything else, deletes leftover directories with that prefix without reading them.
   - **Declared limit:** process death between `hash-object` and the push leaves the directory until the next invocation; default-closed (R25.1(c)) covers it.
   - Tests, in a real process and in-process: after a failed record push, `git fsck --unreachable --no-reflogs` on the real store shows no blob containing `gate_open`, and no private directory remains.
2. **The suite can never run a sealed stage.**
   - The runner refuses `--stage pre1998` and `--stage confirm` with the real context whenever `pytest` is in `sys.modules` (module presence; refusal only).
   - The real-hooks test runs with a context whose release path is an absent path inside the repository, every other hook real.
   - **Run instruction:** after the release commit, the suite is not run on the run host until that stage's record is on the remote.
3. **The import check is repeated.** The loaded-module check runs at start and again inside `append` immediately before every GATE, REPRODUCTION_OK and FINAL push. At those same points (and at start) the runner refuses any untracked or ignored `*.py`, `*.pth`, `*.so`, or `*.pyc` outside `__pycache__`, anywhere in the working tree (`git status --porcelain --untracked-files=all --ignored`). The reader's case, an untracked `X.py` at the repository root, is tested through `main()`.
4. **Redirecting `git` or `gh`.**
   - Any inherited `GIT_*` or `GH_*` variable, and `HTTP_PROXY`, `HTTPS_PROXY` or `ALL_PROXY` in either case, refuses.
   - Git config at any scope refuses when it carries `http.proxy` (also per-URL), `https.proxy`, `core.gitProxy`, `core.sshCommand` or `http[.<url>].sslVerify=false`, in addition to the `insteadOf` pair.
   - `gh` is called with `--hostname github.com`.
   - This host's authentication does not depend on a refused variable: `gh` reads `~/.config/gh/hosts.yml`, and git uses the credential helper `!/usr/bin/gh auth git-credential` from `~/.gitconfig`.
   - The run shell must not export `GIT_EDITOR` or any other `GIT_*`/`GH_*` variable.
5. **The witness is load-bearing.** The stage-2 runner refuses unless `witnessed` has `branch`, `release_commit`, `start_commit`, `gate_commit` and `witness_utc`, with:
   - `witnessed.gate_commit == gate_commit` and `witnessed.branch == BRANCH`;
   - `witnessed.start_commit` equal to the remote commit that recorded the stage-1 START;
   - `witnessed.release_commit` equal to the commit that added the stage-1 release used by that START.

   The first WITNESS line carries the branch: `WITNESS start_commit <sha> branch <branch>`.
6. **Notes.**
   - `check_activity` also requires every `push` entry to be a fast-forward (`is_ancestor(before, after)`) in the real local history. The fresh-clone test uses real ancestry on a real temporary repository; only the activity JSON is hand-built.
   - **Declared:** if the host ever drops old activity entries, every run stops; only a new ruling changes that.
   - **Loaders:** the industry and market loaders decide by the date field alone and drop lines after the window's end before any split, numeric parse or DataFrame. `repro_check` is byte-identical after the change.

**Sealed-run command lines (unchanged; `-E` now enforced):**

```
python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --stage pre1998
python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --stage confirm
python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --ledger-report
```

## R27 — scope of the runner's defences; the committed driver; children; one invocation (CEO, 17:30Z)

0. **The standard a finding is classed against.**
   - **In scope** (must be refused or neutralised by code): accident; anything tracked in the repository; anything in the repository's own directory (untracked or ignored files, `.git/config`, the worktree config, hooks); anything in the inherited environment; any use of a committed file (tests, the driver) as a way in.
   - **Declared, not defended by code:** an operator who changes the host outside the repository (installed packages, binaries, system or user-level config files), who calls functions beneath `main` from their own Python, or who hand-builds ledger commits. Those are covered only by: one operator (the CEO), one run host, the append-only ruleset and activity log, default-closed (R25.1(c)), and the outside witness's timed record.
1. **The committed driver cannot run a real sealed stage.** A context is REAL if root, ledger or a release path lies at or inside the real repository (real path), or the remote URL is the pinned one, or branch and remote together name the real branch on the real remote (`is_real`).
   - (a) In `main`, after `parse_args`, for a sealed stage (`--stage pre1998`, `--stage=pre1998`, likewise `confirm`):
     - **No context:** the real run. `__main__` must be the runner script by real path (no `-c`, no driver, no other file), `pytest` must not be loaded, no `PYTEST_*` variable may be set, and `sys.flags.optimize` must be 0.
     - **A supplied context that touches anything REAL:** permitted only with the real host check and the real engine-commit check, and only if no file exists at the stage's release path. It therefore ends in the missing-release refusal. A file at that path refuses with a distinct message before it is read.
     - **A supplied context with nothing REAL:** a test context. Root, ledger and releases must lie under `/tmp` by real path, and the remote must be a local filesystem path.
   - (b) `validate_ledger` on a REAL ledger refuses any entry whose `host` record is missing, names another ruleset, has an unparseable `updated_at`, or carries the test stub's `"stub": true`.
   - (c) The driver refuses any config with a path outside `/tmp` before importing the runner. The reader's exact config (real root, real branch, both stubs) is a test that is refused before import.
2. **Children's environment and configuration.**
   - Every `git` and `gh` child gets a constructed environment: `PATH=/usr/bin:/bin`, `HOME` from the password database, `LANG=C`, `LC_ALL=C`, plus the object-directory variables only inside `append`.
   - Every `git` call carries `-c core.hooksPath=/dev/null -c core.fsmonitor=false -c core.untrackedCache=false`, and `hash-object` uses `--no-filters`.
   - The push goes to the pinned URL, not the remote name; the fetch afterwards moves the tracking ref.
   - **Authentication** works under the constructed environment (fetch, a dry-run push, and the `gh` API were verified). Nothing was widened.
   - **Repository-scope config** (common `.git/config` and the worktree config) is an allowlist, each entry named in the code with its reason:
     - `core.{repositoryformatversion, filemode, bare, logallrefupdates, ignorecase, precomposeunicode}`;
     - `extensions.worktreeconfig`;
     - `remote.origin.{url, fetch}`;
     - `remote.origin.{promisor, partialclonefilter}` (this checkout is a blob-less partial clone);
     - `branch.*.{remote, merge}`;
     - `branch.*.{t3-merge-base, t3-merge-base-ref, gh-merge-base}` (T3/gh branch metadata, names only);
     - `user.{name, email}`;
     - `core.{sparsecheckout, sparsecheckoutcone}` (the worktree is a sparse checkout).

     Anything else refuses. User and system scope keep the R26.4 block list (declared limit under R27.0).
   - The runner's own process refuses `LD_PRELOAD`, `LD_LIBRARY_PATH`, `LD_AUDIT`, `TMPDIR`, `TEMP` and `TMP`.
   - The private object directory lives under `/dev/shm` (refused if absent), mode 700.
   - A non-empty `gh config get http_unix_socket` refuses.
3. **One invocation at a time.** An exclusive `flock` on `/dev/shm/rotation_core_v2.lock` is taken before the leftover sweep and held for the whole invocation, in every mode (including `--ledger-report` and `--preflight`). A second invocation refuses without touching anything.
4. **Notes.**
   - Both stages compare the release's `versions()` (tools' paths and versions, the `.pth` hash, the `sitecustomize` hash, the Phase A function hashes) with the running interpreter's.
   - The check before each record push includes blob equality of every loaded `engine.`/`scripts.`/`tests.` module against the release's engine commit.
   - The worktree check also covers `.pyd`, `.dylib`, `.zip` and `.egg-link`, and parses `git status -z`.
   - `--preflight` runs every start check: environment, repository config, tools, lock, worktree, modules, remote identity and fetch, ruleset, activity log, the ledger's chain and committed versions, the real host records, and the engine commit (HEAD, clean, loaded as committed). It prints `PREFLIGHT PASS …` or `PREFLIGHT REFUSED: <the first refusal>`, and reads no release or data, writes nothing and pushes nothing.
5. **Witness procedure.**
   - Before a sealed run, the witness records the branch and the release sha. After it, they record the first START sha and the GATE sha, each at arrival, with their own clock.
   - The `WITNESS gate_commit` line is sent to the witness at once, before the signs are used for anything.
   - Before the stage-2 release is written, the CEO sends the witness the `witnessed` block, and they answer `match` or `mismatch`.
   - The stage-2 release carries `witness_confirmation_utc` (the time of their answer). The runner requires it non-empty and later than the GATE entry's time.

6. **No core (reader's N2).**
   - At the very start of every invocation, the runner sets `RLIMIT_CORE` to (0, 0) (children inherit it) and `PR_SET_DUMPABLE` to 0 through `ctypes` `prctl`, then reads back `PR_GET_DUMPABLE` as 0.
   - It refuses if any of these calls fails.
   - A native crash after the first sealed statistic leaves nothing for apport.
7. **More refused git config at any scope (reader's N3):**
   - `remote.*.proxy`, `http[.<url>].curloptResolve`, `http[.<url>].sslCAInfo`, `http[.<url>].sslCAPath`, `http.sslBackend` and `http[.<url>].extraHeader`;
   - any `credential.*` setting other than this host's helper. The accepted settings are exactly `credential.https://github.com.helper` and `credential.https://gist.github.com.helper`, each with the empty reset line followed by `!/usr/bin/gh auth git-credential`.
   - At repository scope the R27.2 allowlist already excludes them.

**Run instructions (in order, from a clean login shell exporting no `GIT_*`, `GH_*`, `PYTHON*`, `PYTEST_*`, proxy, `LD_*` or temporary-directory variable):**

```
env -i HOME=$HOME PATH=/usr/bin:/bin <venv>/bin/python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --preflight
env -i HOME=$HOME PATH=/usr/bin:/bin <venv>/bin/python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --stage pre1998
env -i HOME=$HOME PATH=/usr/bin:/bin <venv>/bin/python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --stage confirm
env -i HOME=$HOME PATH=/usr/bin:/bin <venv>/bin/python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --ledger-report
```

`<venv>` is the interpreter whose `versions()` the release pins (the project's virtual environment on the run host). After a release commit, the test suite is not run on the run host until that stage's record is on the remote.

## R28 — a supplied context is wholly real or wholly temporary (CEO, after the reader's B1 on `e2e51ec779`)

The finding: a driver config with root, ledger, releases and remote under `/tmp`, both stubs, and no input keys passed every gate. Omitted keys fell back to the real inputs, so stage 1 would have run on the real 1928–1997 data against a throwaway ledger. This was the third finding of one kind (a test context that is partly real); R28 closes the kind.

1. **Two constructions, no shared defaults.**
   - `Ctx` takes every field keyword-only with no default; a missing field raises `TypeError`.
   - The real context is built in exactly one place: the `_ctx is None` branch of `main` (`_main_body`), from the module constants. There is no `Ctx()`.
   - A supplied context reads no module constant.
2. **Wholly real or wholly temporary, over every field.**
   - `is_real` is True if ANY path the run can read or write resolves (real path) to or inside the repository root or the real data root (`REAL_DATA_ROOT` in the engine). That covers every path field, every value of both input maps and every sealed path. It is also True if the remote is the pinned URL or resolves there, or if branch and remote name the real branch on the real remote.
   - **A test context:** `is_real` is False, every path lies under `/tmp` by real path, and the remote is a local path under `/tmp`. This is checked for every mode, not only sealed stages.
   - **A wholly-real supplied context:** unchanged from R27.1 (real hooks, no file at the release path). It may read and write no data at all.
3. **Enforced at the point of use.** One choke point, `io_check`, sits before every data read (both French loaders, the Yahoo loader, manifest hashing), every result write (the closed-gate publication, the final JSON and Markdown, the selection rerun, the ledger status) and every `chmod` of a sealed file.
   - In a test context it refuses, before opening, any path not under `/tmp` or inside the repository or the real data root.
   - It also refuses any input whose sha256 equals a recorded real hash: `v2_power/REAL_INPUT_SHA256.txt` (the 15 readable inputs, newly committed and pinned) and every line of `FRENCH_SEALED_FULL_FILES_SHA256.txt`.
   - A sealed `chmod` is reachable only from the real run.
   - In a wholly-real supplied context every data read and write refuses.
   - A direct call beneath `main` sets no mode (declared, R27.0).
4. **Completeness is tested.**
   - The table below has a machine-readable twin in the tests. A test introspects `Ctx.__init__` and fails if any field is absent from the twin or from this table, or has a default.
   - For every field, omitting it raises.
   - For every path-like field, pointing it at the repository or the data root (directly, by symlink, by `..`) makes `is_real` True, and with stubs the context refuses.
   - The reader's B1 config is refused by the driver before import, and by the constructor in-process.
   - No real data file is opened by these tests.
5. **The driver** refuses before importing anything a config that omits any required key, or that has any path value outside `/tmp`: each path key, every value of both input maps, every sealed path, the remote, and the driver's own outputs.
6. **Pinned paths by blob.** `check_engine_commit` hashes the working-tree bytes of every file the engine commit holds under the pinned paths (`hash-object --no-filters --stdin-paths`) and compares each with the commit's blob. It refuses:
   - any pinned path flagged skip-worktree (`S`) or assume-unchanged (lower case) in `git ls-files -v`;
   - any pinned path absent from the working tree.

   This checkout's pinned paths (10,120 files) are all present and unflagged.

| Field | Purpose | Real value (constant) | Test constraint |
|---|---|---|---|
| `root` | repository checkout | `ROOT` | under `/tmp` |
| `ledger_path` | run ledger file | `v2.LEDGER` | under `/tmp` |
| `release1` | stage-1 release file | `v2.RELEASE` | under `/tmp` |
| `release2` | stage-2 release file | `v2.RELEASE2` | under `/tmp` |
| `selection` | committed selection result | `v2.SELECTION_RESULT` | under `/tmp` |
| `ind_d` | through-2019 industry file | `IND_D` | under `/tmp`; not a recorded real hash |
| `ind_full` | full (sealed) industry file | `IND_FULL` | under `/tmp`; not a recorded real hash |
| `fact` | factor file | `FACT` | under `/tmp`; not a recorded real hash |
| `fund_dir` | fund parquet directory | `FUND_DIR` | under `/tmp`; each file not a recorded real hash |
| `final_j` | final results JSON (write) | `FINAL_J` | under `/tmp` |
| `final_m` | final results Markdown (write) | `FINAL_M` | under `/tmp` |
| `stage1_published` | closed-gate publication (write) | `STAGE1_PUBLISHED` | under `/tmp` |
| `selection_rerun_j` | selection rerun JSON (write) | `SELECTION_RERUN_J` | under `/tmp` |
| `selection_rerun_m` | selection rerun Markdown (write) | `SELECTION_RERUN_M` | under `/tmp` |
| `ledger_status_j` | ledger status JSON (write) | `results_v2_ledger_status.json` | under `/tmp` |
| `ledger_status_m` | ledger status Markdown (write) | `RESULTS_V2_LEDGER_STATUS.md` | under `/tmp` |
| `stage1_inputs` | stage-1 manifest inputs (map) | `STAGE1_INPUTS` | every value under `/tmp`; not a recorded real hash |
| `stage2_inputs` | stage-2 manifest inputs (map) | `stage2_inputs(FUND_DIR)` | every value under `/tmp`; not a recorded real hash |
| `sealed_paths` | files unsealed by stage 2 (list) | `[IND_FULL]` | every value under `/tmp`; `chmod` refused in a test context |
| `branch` | ledger branch | `v2.BRANCH` | with the pinned URL it is REAL |
| `remote_url` | ledger remote | `v2.REMOTE_URL` | a local path under `/tmp` |
| `sealed_recorded` | recorded sealed hashes | `None` (the committed record) | any (no path) |
| `host_api` | host-record API | `None` (real `gh`) | a stub allowed only when nothing is REAL |
| `anchor` | activity-log anchor commit | `v2.ANCHOR_COMMIT` | any (no path) |
| `engine_check` | engine-commit check | `v2.check_engine_commit` | a stub allowed only when nothing is REAL |
| `B` | bootstrap resamples | `B_STAGE` | any (no path) |

## R29 — failed reads are never absence; reads are blobs; bytecode; fetch; constants (CEO, after the second reader on `e2e51ec779`)

**The command line (every documented command), Linux run host only (`/dev/shm`, `prctl`):**

```
env -i HOME=$HOME PATH=/usr/bin:/bin <venv>/bin/python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --preflight
```

(and likewise `--stage pre1998`, `--stage confirm`, `--ledger-report`).

1. **A failed read is never absence.**
   - (a) `blob_at` establishes absence only from the tree (`ls-tree`). It returns nothing only when the path is truly absent there; a failed read of a present path, or an unreadable tree, refuses. Every git read that was interpreted is swept (list in the lead's report): `_entries_at`, `file_versions` and every history walk (`_commits_touching`; a failed `log` refuses), `check_release_history`/`commit_adding_entry`/`check_witness` (through `file_versions`), `run_once_guard` (presence from the tree), `on_remote` (blob presence at the fetched head), `check_pinned_blobs` (`ls-files` and `hash-object` exit codes), every `git config` read (`_config_regexp`: exit 1 means no match, anything else refuses; `config --local/--worktree --list` must succeed unless the worktree extension is unset), and `check_read_flags`.
   - (b) **The ledger never shrinks.** Across commits, every first-parent version extends the one before, and a deletion after the ledger existed refuses. Inside one invocation, a later read must extend the last ledger read.
   - (c) **Materialise before use.** Every `git` child runs with `GIT_NO_LAZY_FETCH=1`. After every fetch (including the one after each push, which brings no blob in a blob-less clone), `materialise` lazily fetches, explicitly and only there, every committed version of the ledger, both release files, the selection file and (in the real repository) the pinned paths. It then confirms with lazy fetching off that none is missing, and refuses otherwise. The reader's point holds: after the private object directory is removed the ledger blob is not local until this step brings it.
   - (d) Tested on a real blob-less partial clone of a temporary local remote (`uploadpack.allowFilter`), with the promisor made unreachable right after a fetch: the run refuses, nothing is pushed, and no one-entry ledger appears.
2. **Reads are blobs.** Inside a run, both release files and the selection result are read as blobs at the fetched head of their repository (`set_read_head`, `read_repo_bytes`). The ledger always was. The sealed-hash and real-input records are read as blobs at HEAD of the code repository (`code_text`). A skip-worktree or assume-unchanged flag on any of these, or on any pinned path, refuses. The test edits a committed release under `--skip-worktree`: the flag refuses, and without it the committed bytes are what the runner reads.
3. **Bytecode.**
   - The runner refuses unless `sys.dont_write_bytecode` is true and `sys.pycache_prefix` is `/dev/shm/rotation_core_v2_pycache`, and, checked under the lock, that directory is absent or empty. Every module is therefore compiled from its source.
   - It also refuses any module under the repository loaded from bytecode (a `.pyc` file, a sourceless loader, or a cached file that exists).
   - Before each record push the flags and modules are checked again.
   - Tested with a crafted `.pyc` whose header carries the source's mtime and size: without the flags it runs; under the runner's flags the source runs.
4. **Fetch and config.**
   - Every fetch passes `--refmap=` with the explicit non-forced refspec. After a force-push the fetch refuses and the tracking ref does not move.
   - Allowlisted values are pinned:
     - `remote.origin.fetch` is the standard `+refs/heads/*:refs/remotes/origin/*` or this checkout's single-branch `+refs/heads/main:refs/remotes/origin/main`. The real checkout carries the latter, and it is harmless under `--refmap=`.
     - `remote.origin.promisor=true`.
     - `remote.origin.partialclonefilter=blob:none`.
     - `extensions.partialclone=origin`, which the real checkout does not carry.
   - `--preflight` "reads no release file and no data; writes nothing in the working tree and pushes nothing" (it takes the lock, sweeps leftovers and fetches).
   - The rehearsal's temporary remote and the driver's stub use the constructed environment.
5. **Real-path constants only in the builder.**
   - `_real_ctx` is the only function that reads `IND_D`, `IND_FULL`, `FACT`, `FR`, `YAHOO`, `FUND_DIR`, the result paths, `STAGE1_INPUTS`, `v2.RELEASE`, `v2.RELEASE2`, `v2.LEDGER` or `v2.SELECTION_RESULT`.
   - The guards that must name a root to refuse it (`io_check`, `_touches_real`) are the only other readers of `REAL_DATA_ROOT`.
   - `run_selection`, `pipeline`, `_yahoo_tr`, the fixture fallback and every function default now take their paths from the context.
   - A parse-tree test enforces this over the runner, the engine and the report writer.
   - **Declared (R27.0 class):** a copy of real data placed under the temporary directory with one byte changed is not caught by the hash refusal; that is a host change outside the repository.
6. **Small items.**
   - `is_real` is also True when the context root's git common directory is the real repository's, so a second worktree of the real repository is not a test context.
   - `witness_confirmation_utc` must carry a timezone, be later than the GATE entry's time and not later than now plus 5 minutes; a malformed value is a plain refusal.
   - A lock file that cannot be opened is a plain refusal.
   - A `python -E` process that applies the runner's start-up settings and then aborts leaves no new file in `/var/crash` and no core (verified on this host with apport active; tested).

## R30 — tests that prove their claim; every return code; history walks; config values; hygiene (CEO, 19:17Z)

1. **Tests prove their claim.**
   - `test_R29_1a_missing_blob_is_a_refusal_not_absence` is rewritten. A fresh blob-less clone made with `--no-checkout` (so no blob is fetched) has its promisor made unreachable, then `assert not has`. `_entries_at` and `file_versions` must each raise under `GIT_NO_LAZY_FETCH=1`.
   - The confirmation test file was swept for assertions under a condition the test does not assert; the findings are in the lead's report.
2. **Every return code.**
   - `materialise` refuses on a failed `cat-file --batch-check` before reading its output.
   - `is_ancestor` is three-valued (0 yes, 1 no, anything else refuses), and every ancestry check uses it.
   - The sweep list is in the lead's report.
3. **History walks agree.**
   - `file_versions` and `commit_adding_entry` walk first parents, as `version_entries` does.
   - Every history walk uses `--full-history`.
   - The branch's own history is linear by construction: the activity log shows pushes only, each a fast-forward.
   - `check_no_merges` refuses if any commit after the branch's creation commit (the activity log's first `after`) up to the fetched head has more than one parent and touches the ledger, a release file or the selection file. This runs on every invocation and in `--preflight`; the real branch has no merge commit since its creation.
4. **Config values, not only keys.**
   - Repository-scope config is read with `-z` and allowlisted as (key, value) pairs, each full-matched:
     - `core.bare=false`, `core.filemode=true`, `core.logallrefupdates=true`;
     - `core.ignorecase=false` and `core.precomposeunicode=false` (the Linux defaults; this checkout carries neither);
     - `core.sparsecheckout=true` and `core.sparsecheckoutcone=true`;
     - `core.repositoryformatversion` 0 or 1 (this checkout: 1);
     - `extensions.worktreeconfig=true`;
     - the pinned `remote.origin.*` values.
   - `user.*` and `branch.*` values must contain no newline and must not begin with `!` or `-`.
   - The two-value `remote.origin.fetch` is accepted as built: with `--refmap=` and an explicit non-forced refspec neither configured value takes part.
5. **The parse-tree test is a lint, not the boundary.** The boundary is the runtime `io_check` in the loaders, writers and sealed `chmod`. The lint also catches the cheap alias cases:
   - `from … import X [as Y]` of a forbidden name;
   - `getattr(module, "<forbidden literal>")`;
   - module-level statements that use a forbidden name other than to define a constant.

   No further cases are chased.
6. **Hygiene.**
   - `REAL_INPUT_SHA256.txt` now records paths relative to the data root. No check reads the path column (`recorded_real_hashes` takes the first field only; `sealed_record` uses the file name only); a test shows a recorded hash at a different path is still refused.
   - The absolute-path sweep of the files this branch adds or changes is in the lead's report. The code constants that must name the data root are `REAL_DATA_ROOT` (engine) and `FR`, `YAHOO` (runner).
   - The frozen headers, the earlier results files, the v1 runner and the research scripts that read real data carry absolute paths and are left unchanged: the headers are frozen, the results are records of earlier runs, the v1 runner is not run again, and the research scripts are not part of the runner.

## R31 — one read of a release file; sentences true of the code (CEO, 19:28Z)

1. **One read of a release file.**
   - (a) `_load_release` returns the document with `_blob_sha256`, the sha256 of the exact blob bytes it parsed (`load_release_blob`). START records that hash. No `sha256_file` on a release or selection path remains on the run path; a parse-tree test enforces it.
   - (b) `GitLedger.append` refuses, before any push, a START whose `release_sha256` is not the hash of a committed version of a release file at the fetched head. It uses `release_docs`, the same mapping `check_release_history` builds for `validate_ledger`. A START that can be pushed is therefore one the next invocation accepts. The runner's ledger in the real context carries both release paths, so a START that can be pushed names a committed release. The rehearsal ledger (a temporary remote) and the temporary test ledgers carry none and name no release. They never append to the real ledger, so their STARTs are not checked against release files. A release path outside the context root is not passed (`_release_paths` keeps only paths inside the root); in the real context both release paths are inside it.
   - (c) Before START (in `verified_ledger`, every mode) and in `--preflight`, the run refuses when the working-tree copy of a release or the selection file differs byte for byte from the blob at the fetched head, or exists in only one of the two.
   - (d) Tests:
     - a release re-saved with a trailing newline, and with CRLF, no index flag: refused before START, nothing spent;
     - with (c) skipped in a test: START carries the committed blob's hash (not the working tree's), and the next invocation's `verified_ledger` passes;
     - a direct `append` naming a hash that was never committed: refused, nothing pushed.
   - (e) Every value written into a ledger entry or compared against a pin, and where its bytes come from:

| Value | Where | Bytes from |
|---|---|---|
| START `release_sha256` | ledger | blob of the release at the fetched head (`load_release_blob`) |
| START `engine_commit` | ledger | the release document (blob at the fetched head) |
| START `inputs_sha256` | ledger; compared with the release manifest | the data files the run reads (outside the repository). The same files, read twice: hashed by `check_manifest` before START, then opened again by the loaders. A file replaced between the two reads is not detected; that is a change of the host outside the repository (R27.0, declared). Hashing inside the loaders would touch the loaders on the compute path, so it is not done. |
| START `versions` (tools, `sitecustomize`, `.pth`, Phase A hashes) | ledger; compared with the release manifest | computed in memory: tool `--version` output, installed files, the loaded source's syntax tree (the code that runs; R28.6 pins it to the engine commit's blobs) |
| `host` record (activity count and hash, ruleset id and `updated_at`, creation commit) | every entry | the GitHub API, read after the fetch |
| `phase_a_ast_sha256` | every entry | computed in memory from the loaded source (as above) |
| PHASE_A_CLEAN / INTEGRITY_ABORT counts | ledger | computed in memory |
| GATE signs, `magnitudes_sha256`, integrity, `gate_open` | ledger | computed in memory |
| REPRODUCTION_OK `magnitudes_sha256` | ledger | the GATE entry (ledger blob at the fetched head) |
| FINAL verdicts, `results_sha256` | ledger | computed in memory |
| `selection_results_sha256` (pin) | release vs selection | blob of the selection at the fetched head (`read_repo_bytes`) |
| `selection_results_commit` (pin) | release vs history | `git diff <commit> HEAD -- selection`: tree against tree; HEAD equals the fetched head |
| `engine_commit` (pin) | release vs code | the running code's working-tree bytes against the engine commit's blobs (`check_pinned_blobs`, `check_import_environment`): the code that runs is the working tree, so this is intended |
| `ledger_prefix_len` / `ledger_prefix_chain_sha256` (pin) | stage-2 release vs ledger | ledger blob at the fetched head |
| `branch_head_at_release`, `gate_commit` (pins) | release vs history | ancestry in the fetched history; the gate record from the ledger blob at `gate_commit` |
| `witnessed` (pin) | stage-2 release vs ledger and release history | ledger blobs (first-parent commits) and release blobs (`file_versions`) |
| `stage1_gate` magnitudes (pin) | GATE vs reproduction | computed in memory, compared with the ledger blob |
| sealed hashes (pin) | record vs sealed files | record: code blob at HEAD (`code_text`); files: bytes on disk, read inside the verified stage-2 run |
| real-input hashes (pin) | record vs test-context inputs | record: code blob at HEAD; inputs: bytes on disk |
| frozen header sha (pin) | constant vs header | the header's working-tree bytes, pinned to the engine commit's blob by R28.6. In the sealed stages the header is read after the engine-commit check (R32.6: after `stage1_release` / `ctx.engine_check`); in the other modes it is read before `verified_ledger`. |

   No value is taken from working-tree bytes while the run reads a blob of the same file. The release hash was the one such value, and is fixed above.
2. **`--manifest`** calls `io_check(p, "read")` on each path before hashing it.
3. **Supplied-real guard.** After the fetch, a supplied context that touches anything real is also refused when the stage's release path exists in the tree at the fetched head. The working-tree test is kept.
4. **Sentences made true.**
   - **R29.2:** fixed by R31.1. **R28.3:** fixed by R31.2. **R28.2:** fixed by R31.3.
   - **R29.5:** the remaining real defaults are removed. `fetch_remote`, `host_checks`, `check_remote_identity`, `on_remote`, `commit_on_remote`, `file_versions`, `check_release_pins`, `check_repo_config`, `stage1_release` (its root) and `GitLedger`'s `code_root` now take every repository, branch, remote and anchor argument from the caller.
   - **R29.5, what stays:** `root=ROOT` remains the default of the code-integrity checks (`check_import_environment`, `check_pinned_blobs`, `check_no_bytecode_modules`, `check_engine_commit`, `check_worktree_code`, `_committed_clean`). That root is the repository of the code that is running, not a data, ledger or release path, and it is the only correct value.
   - **R28.1, corrected:** `_real_ctx()` is the only constructor of a real context. It is called by `main`, and by the one driver test in `real_hooks` mode, which replaces the release path with an absent file and so refuses before any data read. That test asserts that `io_check` saw no `read`.
   - **R28.5, corrected:** in `real_hooks` mode the path rule is R27.1's: no file at the release path, in the working tree and (R31.3) in the tree at the fetched head. It is not the `/tmp` rule. Every other driver mode keeps the `/tmp` rule on every key.
5. **Rehearsal warm-up (adds to R21.6).** The rehearsal keeps lines dated 1996-01-02..1997-12-31 as signal warm-up only. That is the same warm-up the selection run already used and declared (`WARMUP_FROM`, `warmup_note`), so the rehearsal uses nothing the examined selection run did not. What the seal protects is any statistic scored on a session before 1998-01-02, and none is.
   - A test checks that every statistic the rehearsal computes (`window_block`, `paired_h2`, `window_series`, `window_excess`, `standalone`) starts on 1998-01-02 or later, for both pseudo-eras.
   - **Printed counts that include warm-up sessions** are integrity counts, not return statistics: `deferred_executions_total_incl_warmup`, `days_holding_after_last_close_total`, `dropped_industry_days_unique_eligible_industries_only`.
   - No printed figure is a return, mean or ratio that includes a pre-1998 session.
6. **Nothing in the repository's directory runs before the checks (R31.6).**
   - (a) **`-P` is enforced.** The command is `python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py …` in every form in this file, the template and the witness procedure.
     - The runner refuses at its very top, after `import sys` and before any other import, unless `sys.flags.safe_path` is set when run as a script, so `scripts/argparse.py` is never imported.
     - `main` repeats the refusal with the `-E` check.
   - (b) **The root is appended, not inserted.** The repository root goes at the end of `sys.path` (`append`), so the standard library and site-packages always win.
     - Every `engine.*`, `scripts.*` and `tests.*` module still resolves from the root (tested). Nothing named `engine`, `scripts` or `tests` exists in site-packages; R32.2 also checks the three packages' own files.
     - *Limit, corrected by R32.8:* with the root last on the path, a name found nowhere else (an optional import of numpy, pandas or scipy, such as `cython`) would resolve to a file at the root. R32.8 closes that: the root comes off the import path for the whole of `main`, and root-level files with optional names are refused.
     - The runner no longer imports the v1 runner, whose import inserts the root at the front of the path. Its two episode tables (`DPEAK`, `LPEAK`) are copied into the v2 runner verbatim, and a test pins them equal to v1's. The v1 runner is untouched.
     - The driver also appends.
   - (c) **No shadowed name** (as amended by R32.8). Before the first import from the root, again under the lock, and again before every record push (R26.3), a real run, which is never under pytest, refuses when any loaded module other than `engine`, `scripts`, `tests` (and the script itself) has its file under the repository root. Under pytest, which loads other tracked packages such as `lib`, the in-process check is names-only: no standard-library or installed-package name from the root.
   - (d) **Tests.** Planted `scripts/argparse.py` (with and without `-P`), `json.py` at the root, `engine/ctypes.py` and `engine/fcntl.py` (both lazily imported by the engine): none is ever imported, and the run refuses (without `-P` at the top, with `-P` by the untracked-code check). A run without `-P` refuses. A fake `json` module loaded from the root is refused by both checks.
   - (e) **Every import on the run path after the root is added, and what it resolves to** under the new order. Source modules swept: the runner, the v2 engine, the evaluation engine, the report writer and the fixture generator.
     - **Standard library:** `__future__`, `argparse`, `ast`, `ctypes`, `dataclasses`, `datetime`, `glob`, `hashlib`, `importlib.metadata`, `inspect`, `json`, `pathlib`, `platform`, `re`, `resource`, `shutil`, `subprocess`, `sysconfig`, `tempfile`, `textwrap`, `typing`, `urllib.parse`, `warnings`.
     - **Frozen or built-in:** `fcntl`, `importlib.machinery`, `io`, `math`, `os`, `pwd`, `site`, `stat`, `sys`.
     - **Site-packages:** `numpy`, `pandas`, `pyarrow`, `pyarrow.parquet`, `scipy`.
     - **Repository:** `engine` (an empty `__init__.py`), `engine.rotation_core_evaluation`, `engine.rotation_core_v2`, `engine.validation` (lazy, in `dsr`; it imports `math`, `numpy` and `pandas` only), `scripts.rotation_core_v2_report`, and `tests.rotation_core_v2_fixture` (only by `--dry-run-stage1-fixture`).
     - None of the repository modules changes `sys.path`.

## R32 — the report module; top-level packages; metadata; format version; driver remote; wording (CEO, after the outside reader on `d4a3601b89`)

1. **The report module no longer puts the root first.** `scripts/rotation_core_v2_report.py`'s `sys.path.insert(0, …)` is deleted. A comment says it is not an entry script and relies on the runner, which has already appended the root.
   - A test asserts that no file on the R31.6(e) list calls `sys.path.insert` or touches `sys.meta_path` or `sys.path_hooks`. The list: the runner, the v2 engine, the evaluation engine, `engine/validation.py`, the report writer and the fixture generator.
   - A second test asserts that `sys.path[0]` is not the root after each of the runner's three report import sites.
   - **Sweep of statements on the run path that change import state:**
     - the runner's `sys.path.append(ROOT)` (R31.6(b));
     - the driver's `append` (tests only);
     - `site.getsitepackages()` and `site.getusersitepackages()` in `site_dirs` (read-only queries; `getusersitepackages` caches `site.USER_SITE`, which changes no import path).

     - `main`'s removal of the root at its start and the restore when it returns (R32.8(b′)).

     Nothing else changes `sys.path`, `sys.meta_path`, `sys.path_hooks` or `site` state. The v1 runner's insert is no longer on the run path (R31.6(b)).
2. **Top-level packages.** `check_import_environment` refuses unless the file (or, for a namespace package, every `__path__` entry) of `engine`, `scripts` and `tests`, when loaded, lies under the root. Tested with a faked installed `engine` and a faked namespace `tests`.
3. **Metadata errors refuse.** `_protected_names` refuses (R32.3) when installed-package metadata cannot be read, instead of falling back to standard-library names. Tested.
4. **`core.repositoryformatversion`** is 1 only in the real context. 0 is accepted only with `check_repo_config(..., test_repo=True)`, which the runner never passes; only the tests do, for their temporary repositories. Tested both ways.
5. **The driver refuses any remote containing `://`** before the `/tmp` rule, so that check stands on its own. Tested.
6. **Wording made true:**
   - the committed-release refusal in `append` covers the real context, and the rehearsal and test ledgers are named;
   - `inputs_sha256` is "the same files, read twice", with the limit stated;
   - the frozen header is pinned to the engine commit's blob, and in the sealed stages it is now read after the engine-commit check (a reorder with no compute effect).
7. **Warm-up counts.** A test runs the rehearsal on synthetic data and enumerates every `count` line it prints and every integrity key it records (the same set). Each is either one of the three declared warm-up-inclusive counts, or its expression in `pre1998_stats` uses the window's index, eras, episodes or era values. The Phase A lines are taken on the two pseudo-eras, both from 1998-01-02.
   - **Mechanical coverage:** every printed and recorded count key. The signs and magnitudes are covered by the R31.5 test, which spies on the statistics functions.
   - **Not mechanical:** that a windowed expression truly restricts to the window. The test checks that the expression names the window's index; it does not evaluate it.
8. **Only `engine`, `scripts` and `tests` load from the root (R32.8).**
   - (a) **Strict check.** Outside pytest (every real run), any loaded module other than the three repository packages and the script itself whose file is under the root refuses. This runs before the first import from the root, under the lock, before every record push, and before unsealing in stage 2.
   - (b) **Under pytest** the in-process check stays names-only; the strict rule is proven in subprocesses that are not pytest:
     - a temporary repository holding a copy of the run's code, with a committed root-level `cython.py`, `bottleneck.py` or `numexpr.py`: the run refuses at the runner's top, before START, and the planted body never ran (a marker file under `/tmp` is absent);
     - an arbitrary name (`zz_anything.py`, committed): nothing imports it, the run completes, and the marker is absent;
     - the same module forced into `sys.modules` from the root: refused by the strict check before `main`.
   - (b') **The root is off the import path for all of `main`.** Once `engine`, `scripts` and `tests` are imported (at the runner's top, while the root is appended), their submodules resolve through each package's own `__path__`. `main` therefore removes the root from `sys.path` at its start and restores it on exit (for in-process callers). For the whole invocation, no root-level module of any name can be found by an import. Tested: during `main` the root is absent, `engine.validation`, `scripts.rotation_core_v2_report` and `tests.rotation_core_v2_fixture` still import, and the path is restored afterwards.
   - (c) **Optional names refused at the root.** Before numpy, pandas or scipy are imported (at the runner's top) and again under the lock, the run refuses when the root, in the working tree or in the tree at HEAD, has a module or package named like one of their optional imports.
     - The list (`OPTIONAL_NAMES`, 54 names) was found mechanically: pandas' declared optional dependencies (`pandas.compat._optional.VERSIONS`), plus every `try: import X … except ImportError` in numpy, pandas, scipy and pyarrow outside their test folders, minus the standard library and installed packages. It includes `cython`, `bottleneck`, `numexpr`, `numba`, `tables`, `fsspec`, `matplotlib`, `jinja2`, `sqlalchemy`, `xarray`, `torch` and `zstandard`.
     - It cannot be complete (an import of a computed name escapes the scan). (b') is what makes the guarantee hold regardless.
   - (d) **Order relative to sealed reads.**
     - Before `main`, the runner imports numpy and pandas before the root is appended. After appending, the only new top-level modules are `engine`, `scripts` and `tests` (measured; the other import statements re-bind modules already loaded). No other root-level module can run there, and the strict check runs right after.
     - From the start of `main` the root is off the path, so no root-level module can be loaded at all.
     - The first sealed read (`stage2_opened`: chmod, then hashing the sealed file) comes after the strict check under the lock. In stage 2 it also comes after an explicit `versions()` call (which performs every probe import: scipy, pyarrow) and a further strict check immediately before unsealing.
     - *Reworded by R33.1, final after R33.4:*
       - **Before R33.4**, imports happened after the last pre-read check:
         - stage 1: `scipy` (through `versions()` at START) and `pyarrow.pandas_compat`;
         - stage 2: `pyarrow.parquet` and its family, `pyarrow.dataset`, `ssl`, and, after FINAL, the report writer.
       - **R33.4 moved them before the check.** `versions()` and `import pyarrow.parquet, pyarrow.dataset, pyarrow.pandas_compat` now run immediately before the pre-read strict check in stage 1, in the rehearsal and before unsealing in stage 2; the report writer is imported at the runner's top.
       - **Measured after the change** (every module name, any depth) on a stage-1-then-stage-2 run through `main` with synthetic data: no module is newly imported after the pre-read check, nor between any two later checks, in either stage. Each record push (START, GATE, REPRODUCTION_OK, FINAL) runs the strict check first.
       - **Limit:** the measurement covers the synthetic path. Real data could take another branch with a lazy import. Any such import happens inside `main`, where the root is off `sys.path` (R32.8(b′)), so it resolves from site-packages or the standard library or fails; it cannot reach a root file. The next record push re-checks.
       - No sealed byte can be read after a root-level module has run, because no root-level module can be loaded inside `main`. No blocker was found.
     - **Limit, for what (a) alone would guarantee:** it detects a module after its top-level code has run. With (b') no such module can run inside `main`; before `main`, only the steps above run, and none can load a root-level module.

## R33 — one sentence made literal; stage-1 symmetry (CEO, after the CEO's reader on `bae3b90eb1`)

1. **The ordering sentence** in R32.8(d) is reworded to the measured facts: which imports happen after the last check before the reads in each stage, why none can reach the root (R32.8(b′)), and which record push re-checks each.
   - **Sweep of R32 for other absolute claims:**
     - "Nothing else changes `sys.path` …" (R32.1) now also lists R32.8's removal and restore.
     - "the runner never passes `test_repo`" (R32.4): checked, true.
     - "the planted body never ran" and "nothing imports it" (R32.8(b)): shown by the marker files in the tests.
     - "after appending imports only …" (R32.8(d)): measured and reworded.
     - "none can load a root-level module before `main`": true by the same measurement.
2. **Stage-1 symmetry.** An explicit strict check (`refuse_shadowed_modules`) now runs immediately before the first read of pre-1998 data in stage 1 (before `stage1_release`, whose manifest check hashes the inputs) and in the rehearsal (before `window_text` reads the through-2019 files). It is one call each, with no compute effect.
   - Tested through `main` with an order spy in the driver: in stage 1 a strict check follows `verified_ledger` and precedes the first `io_check` read.
   - The rehearsal branch's order is checked in the source.
3. **No child process before the configuration checks (MUST-FIX).** The runner's top keeps only the working-tree half of the optional-name check (`os.listdir`); before numpy loads, an import resolves from the working tree, so that is the half that matters. The tree-at-HEAD half runs under the lock through `v2._git`, after `check_env_vars` and `check_repo_config`.
   - Every child process on the run path starts in one of two engine wrappers:
     - `_git` (git with the pinned options and constructed environment);
     - `_tool_run` (`gh` and the tools' `--version`, by absolute path, constructed environment). `gh_api`, `check_gh_socket` and `tool_versions` now go through it.
   - **Sweep** (runner, both engines, `engine/validation.py`, the report writer, the fixture generator): every `subprocess.*`, `os.system`, `os.popen`, `os.fork*`, `os.posix_spawn*`, `os.exec*`, `os.spawn*` and `pty.spawn` call lies inside `_git` or `_tool_run`. Before this change there were five others: the runner's top-level `git ls-tree`, `check_gh_socket`, `tool_versions` and `gh_api` (direct `subprocess.run`), and the test-only driver's stub (not on the run path).
   - Tested by a parse-tree test, and by importing the runner's top-level code with every child-process entry point replaced by a refusal: it completes.
4. **Probe imports before the check.** Beside each `versions()` call that precedes a strict check (stage 1, the rehearsal, stage 2 before unsealing), the run imports `pyarrow.parquet`, `pyarrow.dataset` and `pyarrow.pandas_compat`. The report writer is imported at the runner's top.
   - What is still imported after the last check: nothing, measured (see R32.8(d)). Tested through `main` over both stages: every interval after the pre-read check shows no new module.
5. **START push.** A strict check runs directly before the START push. It is added as an explicit call in `GitLedger.append`, not by adding START to `RECORD_KINDS`, because that would also run the blob, worktree and bytecode checks at START. Tested.
6. **Writes to the import path.** A parse-tree test finds every write to `sys.path`, `sys.meta_path` or `sys.path_hooks` (including through an alias of `sys`): `insert`, `append`, `extend`, `remove`, `pop`, `clear`, `+=`, item or slice assignment, `del` and rebinding.
   - No run-path file other than the runner has one.
   - The runner's are exactly the reviewed three: `append(ROOT)`, and the slice assignments that take the root off and restore the path.
   - The detector is tested on each write form.
7. **Root names by name.** The root-name check uses the part of the name before the first dot, so every suffix (`.py`, `.pyc`, `.so`, `.cpython-312-…so`, `.pyd`, `.zip`, `.egg-link`, …) is stripped. A root directory of that name is a hit with or without `__init__.py`. Tested, including a temporary repository with a bare `cython/` directory.
8. **Namespace packages.** The strict check uses each `__path__` entry when a module has no `__file__`. A namespace package under the root whose top-level name is not `engine`, `scripts` or `tests` refuses: strict in a plain subprocess; names-only (for a protected name) under pytest, in both the runner and the engine. Tested.
9. **Declared, wording only.**
   - **Stage-1 order (N1):** after R33.2 and R33.4, stage 1 runs `verified_ledger`, then `versions()` with the pyarrow imports, then the strict check, then `stage1_release`, whose `check_manifest` hashes the inputs before comparing `versions()`. The probe imports have already happened, so the order matches stage 2's.
   - **N6:** an installed distribution named `tests`, `scripts` or `engine` would run its `__init__` before R32.2 refuses it. Installed packages are the declared class (R27.0).
   - **N8:** the R32.7 count test checks the names in each expression, not the values; it is a tripwire and does not prove that a figure excludes warm-up sessions.

## R15 log — the single selection rerun (CEO authorisation 2026-11-11 22:35Z, order amended)

- **Engine before:** `1ca5228b3c` (the selection run). **Engine after:** `b3f7ce4548cadabee85e5e616b88317dc63346d2`. The rerun ran on the after-engine. Its outputs are `results_v2_selection_rerun.json` and `RESULTS_V2_SELECTION_RERUN.md`; `1ca5228b3c`'s `results_v2_selection.json` and `RESULTS_V2_SELECTION.md` stay untouched as the superseded record.
- **Commands,** run from the checkout with `env -i HOME=… PATH=/usr/bin:/bin <venv>/bin/python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py <mode>`:
  - `--preflight` at 22:34:51Z: PASS on `b3f7ce4548`, ledger entries 0, activity entries 41, ruleset 27041175;
  - `--stage select` at 22:35:18Z: exit 0, 183 s, printed `selected: h3_b25.0`. Its stdout sha256 is `ca2f8724567086e907776d7963b47c5f20ce7a29a27d71938854def4f8033a0d`.
- **Pre-check (R15, repeated on the final engine):** `repro_check` against `1ca5228b3c` gave 17 books, scored 1998–2019 states identical, maximum absolute daily-return difference 0.0, byte-identical to the recorded `v2_power/repro_check.stdout`.
- **Selected grid point:** h = 3, b = 25, the same as `1ca5228b3c`. Observed H1 excess over the matched mix (10 bp, selection window) is unchanged at every setting: h3 b25 −2.287 %, h3 b37.5 −2.623 %, h5 b25 −2.870 %, h5 b37.5 −2.687 % per year.
- **Engine changes since `1ca5228b3c`, and whether each can move a number** (commits `5a58f3e5d6` … `b3f7ce4548` under `engine/`, `scripts/`, `tests/`):
  - **Release, seal, ledger, host and environment machinery** (R13 … R33: staged release, blind stage 1, run ledger, Phase A/A2, host record, import, bytecode and config checks, the I/O choke point): these move no 1998–2019 number. They gate access or decide refusals and compute nothing used by selection; the reproduction above is exact.
  - **F1 (guarded parquet loader):** the same rows (filtered at the Arrow level), so no number moves.
  - **F3 (false-DEFEND timing on held, not decided, state):** this moves the descriptive false-DEFEND figures. They are the erratum below.
  - **R14 (two base readings, eq governing):** the eq series is unchanged; the drift reading adds the `R14d_drift_base_sensitivity` rows, which are new and not a re-selection.
  - **F4 (fund tier):** not used by selection.
  - **S2 (no padded start):** changes only warm-up sessions before 1998, which are never scored. **S3 (SMA over observed closes)** and **S4 (drift legs):** the reproduction shows 0 scored states and 0.0 return difference.
  - **S8 (unique dropped industry-days):** a count label only.
  - **R18 (strict 2× run):** this moves the 2× rows. It is shown below, old beside new, with the old row kept in `H1_at_2x_costs_before_R18_superseded`.
  - **R21.4 (bootstrap SeedSequence streams):** confirmation runs only. Selection seeds are unchanged (S11), so every 10 bp interval and p is identical.
  - **R29.5 / R31.6 (paths from the context; v1's episode tables copied):** the same files and the same episodes.
- **Figures that moved** (all others are identical to the last bit):

| Setting | Figure | `1ca5228b3c` | rerun |
|---|---|---|---|
| h3 b25 | H1 at 2× costs vs matched mix (R18 strict) | −3.508 % [−6.301, −0.780] p 0.9936 | −3.651 % [−6.447, −0.921] p 0.9954 |
| h3 b37.5 | same | −3.753 % [−6.411, −1.031] p 0.9966 | −3.893 % [−6.556, −1.166] p 0.9976 |
| h5 b25 | same | −4.282 % [−7.155, −1.404] p 0.9984 | −4.430 % [−7.300, −1.550] p 0.9987 |
| h5 b37.5 | same | −4.018 % [−6.816, −1.187] p 0.9973 | −4.161 % [−6.952, −1.322] p 0.9979 |
| all four | 2× costs per year | 2.444 / 2.262 / 2.827 / 2.664 % | 2.444 / 2.262 / 2.827 / 2.664 % (changes in the 6th digit: the strict book holds re-formation at 20 bp) |
| h3 b25 | false DEFEND calls / calm year, H1 · price-only · cash (F3 erratum) | 2.007 · 2.768 · 2.007 | 2.076 · 2.838 · 2.076 |
| h3 b37.5 | same | 1.661 · 2.768 · 1.661 | 1.730 · 2.838 · 1.730 |
| h5 b25 | same | 2.976 · 3.737 · 2.976 | 3.045 · 3.807 · 3.045 |
| h5 b37.5 | same | 2.699 · 3.737 · 2.699 | 2.768 · 3.807 · 2.768 |
| H3 | false DEFEND calls / calm year (F3 erratum) | 0.831 | 0.900 |

  The false-DEFEND cost per calm year moves with the counts (for example, H1 h3 b25 goes from 1.276 % to 1.424 %); all values are in the JSON. These figures are descriptive only; no selection or pass condition uses them.
- **F3 erratum:** the false-pivot table now uses the state held after each close, not the state decided at t. Each false-DEFEND count rises by one call over the 22 years (about +0.07 per calm year) in every book. This is an erratum to a descriptive table, made before any confirmation read.
- **Order of the authorised runs:** the first rehearsal attempt at 22:33:51Z refused with "selection result is not committed" before Phase A, having written only START to its own temporary remote. The order was changed so that the rehearsal follows the rerun. No code changed.
