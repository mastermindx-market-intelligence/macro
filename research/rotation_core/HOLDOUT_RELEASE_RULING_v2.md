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
21. **S11:** seeds as listed under R16; shared indices across H1, H2, H3.
22. **S1b(i):** warm state and warm holdings; scoring by slicing.
23. **S1b(ii):** H2 pooled = paired difference, same weights and indices, no mix.
24. **S1b(iii):** one-sided Holm governs; two-sided reported, labelled.
25. **S1b(vi):** block 21 governs; block 63 reported as sensitivity.
26. **O1:** the relative line is net of re-formation cost at 10 bp, computed once. Convention, not a correction.
27. **R18 base run:** leg-level re-formation at 10 bp inside the legs; switches 100 % out and in; the mix on the same net legs, no cost for its daily rebalancing. Convention, not a correction.
28. **O5:** NaN is neither sign; fails closed; an integrity failure closes the gate.

**New silent choices made in this change set, without data (for ruling):**

29. **Integrity failure closes the gate for good.** Under O5 and R18 a NaN or a strict-run violation closes the gate, and under R17 a closed gate is final. An engine bug that produced a NaN would therefore end the historical tier. Implemented as ruled; flagged because the combination was not stated.
30. **H2's drawdown leg.** H2 has no matched mix. The leg is read as "H1's drawdown no worse than the price-only control's" (the yardstick of H2's own contrast), on both windows, both cost runs and both readings.
31. **Fund veto for H2.** The fund point estimate for H2 is the paired difference of the fund-executed H1 and price-only books on 2020–2025; any negative estimate fires the veto, as for H1 and H3.
32. **Gate integrity counts also close the gate.** The gate result is open only if every NaN count is 0 and the strict-run violation count is 0, as well as the sign condition.
33. **Two-sided p:** centred, (1 + #{|d − obs| ≥ |obs|}) / (B + 1).
34. **2020–2025 yardsticks:** SPY, RSP (Yahoo total return), BASE and the French market (added for continuity with pre-1998); named episodes E2020, E2022, E2025 from the v1 header's windows.
35. **Descriptive state split:** H1's excess over the mix by the leg held that day (the largest start-of-day weight).
36. **A stage-1 rerun at the same engine commit is refused**; a rerun needs an engine change (R17.2).
37. **Selection rerun output** goes to `results_v2_selection_rerun.json` and `RESULTS_V2_SELECTION_RERUN.md`; `1ca5228b3c`'s files stay as the superseded record; the run-once guard reads the remote branch.
