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
  - **Sealing:** every return, excess, interval, p-value, drawdown and cost figure goes to `/home/ubuntu2/tmp/rotation-core/data/sealed_stage1/results_v2_stage1_pre1998.json`, written mode 000. The committed `results_v2_stage1_gate.json` carries the signs, gate result, diagnostics, engine commit and that file's sha256.
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
   - **Declared limit (R24.2):** a fresh clone rewound exactly to the release head is caught only by the host layers (ruleset 27041175 and the activity log's `force_push` entry) and by the outside witness, not by the local ancestry pin. The three layers are: the ruleset forbids the rewind; the activity log records it; the witness holds the shas outside this repository. Tests cover the host layers.
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
