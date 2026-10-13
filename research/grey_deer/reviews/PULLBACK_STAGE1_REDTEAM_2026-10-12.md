# Pullback stage-1 red team — 2026-10-12

Lane G-RT1, read-only. The runner `scripts/research/grey_deer_pullback_stage1.py` was compared with the frozen prereg `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` §4–§12. No runner code was changed. No market series was loaded or downloaded. Repros call the runner on synthetic series only.

This is development research. It makes no customer-facing claim about a forecast record.

## Summary

| Severity | Count | IDs |
|---|---|---|
| CRITICAL | 0 | — |
| MAJOR | 2 | RT-01 (MISMATCH), RT-03 (UNCLEAR) |
| MINOR | 3 | RT-02, RT-04, RT-05 |
| NOTE | 4 | RT-06, RT-07, RT-08, RT-09 |

**Most important finding: RT-01.** `compute_point_metrics` indexes comparison-set arrays with an evaluation-length sensitivity mask. When any binary claim configuration abstains on any origin and `M3-ALL-C0.1` still issues somewhere in that mask, the call raises `IndexError` inside `evaluate_and_write` before episodes, the bootstrap, the gates and the artifacts are written. The prereg says the `C = 0.1` row is a sensitivity row and that abstentions are reported. The failure is closed: it does not write a gate with a flipped bound. It does destroy the stage-1 artifact.

The published W3 rerun did not take this path. In `research/grey_deer/pullback_stage1_r1/PULLBACK_STAGE1_RESULTS_2026-10-11.json`, B0, B1-20, B1-63, B2-21, B2-63, M3-ALL and M3-ALL-C0.1 abstain on 0 origins at h = 5, 10 and 21. Q3-ALL abstains 1 origin at h = 5 and 5 at h = 10 (`QUANTILE_CROSSING`); that family does not use the sensitivity indexer. All 12 gate verdicts are `underpowered/blocked claim`. Those verdicts were not produced by RT-01.

RT-03 is the one descriptive output the published rerun already carries under a split reading of the prereg: INC probability metrics use the native label, and the INC early-warning table uses protocol episodes. The deviation log states that split. It is not a gate.

**Bounds.** Every normative sentence in prereg §4–§12 is a row below. Checked in code and, where the row says so, by a synthetic call: target A and the inclusive 0.05 cut; purge boundary `idx(t) + h <= idx(s0)`; fold constants 63 / 315 / 126 / 63 and the final-block merge; episode merge, windows and the 10-and-10 power floor; circular-block bootstrap, `L`, seeds, `numpy.quantile` rather than `nanquantile`, and failing extremes; gate quantile `0.05/12`, the WACE `0.05` quantile, and the four verdict strings; trial budget 69 registered before outcomes. Not in scope: prereg v1.1, the 14-ticker panel, a re-execution on SPY, and any edit to the runner.

Existing tests, this lane: `~/lanes/venv/bin/python -m pytest -q tests/test_grey_deer_pullback_stage1.py` → `16 passed in 4.04s`.

## How a row was judged

`MATCH` means the runner implements that sentence, including a boundary the sentence states. `MISMATCH` means a synthetic call shows a different behaviour. `UNCLEAR` means two prereg sentences disagree, or the sentence is not implemented and stage 1 does not yet execute it. Every non-MATCH row has a finding. Line numbers are the runner unless another file is named.

## Normative table (§4–§12)

| ID | Normative sentence | Code | Verdict |
|---|---|---|---|
| S4-01 | `A(t,h) = max(0, 1 − min(P_{t+1}…P_{t+h}) / P_t)`. The low at `t` is not in the min. | `build_labels` 612–618; `lib/observed_moves.py` `forward_max_loss` 101–111 | MATCH. Series `[80,100,100,70,…]`, h=3, t=0 gives A=0.125 = 1−70/80. |
| S4-02 | `Y = 1` iff `A ≥ 0.05`, inclusive. | `loss_event` 114–119; `THRESHOLD` 213 | MATCH. 100→95 gives A≈0.050000000000000044 and Y true; 100→95.01 gives Y false; 100→94.99 gives Y true. |
| S4-03 | Quantile target is `A` at τ ∈ {0.5, 0.8, 0.9}. | `TAUS` 214; `fit_q0` 800–801; `fit_quantile_lp` 762–775 | MATCH. Intercept-only LP on `linspace(0,1,101)` returns 0.5000 / 0.8000 / 0.9000. |
| S4-04 | Mature only when `t+h` is inside the window. An immature label is absent, never zero. | `forward_max_loss` 110–111; `loss_event` 116–118 | MATCH. Last row of a 7-point series at h=1 is A=nan, Y=`<NA>`. |
| S4-05 | RAW ex-dividend drops are disclosed and not corrected. | no dividend or split adjustment in the runner; integrity refuses a close ratio outside [0.75, 1/0.75] (`integrity_checks` 551–588) | MATCH. The runner does not adjust closes. |
| S4-06 | `D_total` is reported for P-active only, descriptively, and is never a gate. | no symbol `D_total`; `build_populations` 654–662 | UNCLEAR. RT-08. |
| S5-01 | An origin is warm when its row index is at least 63. | `WARM_IDX` 209; `build_populations` 657 | MATCH. |
| S5-02 | P-all is every warm, mature origin. Primary, executable now. | `build_populations` 657–660 | MATCH. On 1,321 rows, h=5 warm-mature count is 1,253. |
| S5-03 | P-active is the causal `close_path.v1` observer. It is not on main, and this file does not copy it. | `BLOCKED_CONFIG_ROWS` 300–304; `build_populations` 661 | MATCH. Return is `OBSERVER_NOT_ON_MAIN`. |
| S5-04 | Until that landing, every P-active row is `BLOCKED / OBSERVER_NOT_ON_MAIN`. | `_blocked_claim_row` 2005–2020; `build_gates` 2029–2031 | MATCH. Six blocked rows, verdict `underpowered/blocked claim`, flag `OBSERVER_NOT_ON_MAIN`. |
| S5-05 | A rules change on landing needs a new revision. Frozen rule values are not copied into this file. | no observer constants in the runner | MATCH. Stage 1 blocks instead of reproducing the nine rule values. |
| S6-01 | Features use closes at or before `t`. `SMA_w` includes `t`. `r_k = log(P_t / P_{t−k})`. | `build_features` 621–637; `sma_gap` 142–146; `log_return` 136–139; `trailing_drawdown` 129–134 | MATCH. Rolling windows end at `t`. |
| S6-02 | Standardisation uses the training-row mean and standard deviation with `ddof = 0` only. | `_standardise` 826–829 | MATCH. Train `[[1,2],[3,4],[5,6]]` gives std `[1.63299, 1.63299]`, equal to `ndarray.std(ddof=0)`. The test row is scaled with those train stats. |
| S6-03 | `realized_vol` `min_periods` is 10 at w=20 and 31 at w=63. | `engine/vol_forecast.py` `realized_vol` 22–25, called at `build_features` 623–624 | MATCH. On an 80-point line the first finite index is 10 and 31. |
| S6-04 | Every feature window is full at row index 63 and later. | `build_features` 638–647 | UNCLEAR. RT-06. A noisy series is finite at index 63. A flat series is not, and the run stops. |
| S6-05 | B0 is `(k + 0.5) / (n + 1)` and always issues. | `fit_b0` 793–797; thin exception `run_fits` 867 | MATCH. Empty prefix returns 0.5. 2 events in 20 origins returns 0.11904761904761904 = 2.5/21. |
| S6-06 | B1-20 and B1-63 are L2-logistic on `log rv_w`. B2-21 and B2-63 are L2-logistic on `close/SMA_w − 1`. | `CONFIGURATIONS` 268–273; `run_fits` 884–899 | MATCH. Feature names match. |
| S6-07 | M3-ALL is L2-logistic on `dd63`, `r5`, `r10`, `log rv20`, population P-all. | `CONFIGURATIONS` 274–280 | MATCH. |
| S6-08 | M3-ACT and Q3-ACT are recorded and not run in stage 1. | `BLOCKED_CONFIG_ROWS` 301–302 | MATCH. `abstention_type` is `OBSERVER_NOT_ON_MAIN`. |
| S6-09 | Logistic objective is sum of log-loss plus `(1/(2C))‖β‖²`, intercept unpenalized, `C = 1.0`, L-BFGS-B, `gtol = 1e-8`, `maxiter = 10000`, start at zero. Non-convergence abstains as `FIT_NONCONVERGENCE`. | `logistic_objective_and_gradient` 736–745; `fit_logistic` 748–759 | MATCH. Dedicated test checks the gradient. Failure type is `FIT_NONCONVERGENCE`. |
| S6-10 | `C = 0.1` is a sensitivity row for M3-ALL only and is never a gate. | `SENSITIVITY_CONFIG` 999; sensitivity branch `compute_point_metrics` 1372–1383 | MISMATCH. RT-01. The row is excluded from the claim set, and the indexer aborts the run when a binary claim origin abstains. |
| S6-11 | Q0 is the training-prefix empirical quantile of `A`, numpy `method="linear"`. | `fit_q0` 800–801 | MATCH. |
| S6-12 | Q1 uses rv20 tercile bounds `numpy.quantile(..., [1/3, 2/3], method="linear")` and `searchsorted(..., side="right")`. A cell under 20 training origins issues the block Q0 and logs `TRAINING_CELL_THIN_FALLBACK`. Q1 does not abstain on cell size. | `fit_q1` 804–823 | MATCH. A cell of 19 falls back; a cell of 20 does not. |
| S6-13 | Per τ, unpenalized linear quantile regression, unpenalized intercept, `linprog(method="highs")`. Crossing `q0.5 > q0.8` or `q0.8 > q0.9` is judged on unclipped predictions; a crossing origin abstains as `QUANTILE_CROSSING`; survivors are then clipped below at 0. Q0 and Q1 are never clipped. Solver failure abstains as `FIT_NONCONVERGENCE`. | `fit_quantile_lp` 762–775; `quantile_output_policy` 778–790 | MATCH. Equal q50 and q80 still issue. A negative unclipped value is clipped to 0 after the check. Tau weights are not swapped (S4-03). |
| S6-14 | INC is the displayed-probability replay named in §6, look-ahead disclosed, own table, never pooled, never a reference, never a gate. A replay failure is `BLOCKED` and blocks nothing else. | `run_inc` 2253–2333 | MATCH for the call order, `look_ahead_disclosed: True`, and the catch that returns `INC_SOURCE_UNAVAILABLE` or `INC_REPLAY_ERROR`. The audit pin is blob `b5b4f753…` (`AUDIT_SCRIPT_BLOB` 238). The prereg names commit `f1ae1e0365fc`. Those are different identifier kinds; this review did not re-derive one from the other. |
| S6-15 | INC is scored on the dates of this protocol's P-all evaluation origins that it covers, against its own native label only. | `run_inc` 2301–2315 and 2321 | MISMATCH. RT-02. The date set is `cell["origin_idx"]`, the comparison set, stored under the name `evaluation_origins`. |
| S6-16 | INC is never scored against the Massive RAW label. | `binary_metric_set(..., y_native)` at 2315; `early_warning_table(..., cell["y"], ...)` at 2317–2318 | UNCLEAR. RT-03. Metrics follow this sentence. Early warning does not. |
| S6-17 | Mechanism families and complex models are not in this revision. The S07 phase-only baseline is not a reference. | no such configuration ids | MATCH. |
| S6-18 | Trial budget is registered with `register_trials`, family `grey_deer_pullback_v1`, `basis="itemized"`, budget 69, before any outcome. | `trial_ledger_scope` 604–606; `main` 2813–2814 | MATCH. A ledger pointed at `/tmp` recorded family `grey_deer_pullback_v1`, budget 69, basis `itemized`, and the context manager writes on `__enter__`, before `build_labels`. The ledger row kind is `declared_budget` with `n: 69` (that is the ledger's itemized stamp, not 69 separate ids). Opting the sparse worktree into `data/` is the executing lane's step; this runner does not do it. |
| S7-01 | Expanding window. First test block starts at the 253rd warm origin. Training counts at that block are 248, 243 and 232 at h = 5, 10 and 21. Later blocks train on every earlier warm mature origin that passes the purge, earlier test blocks included. | `FIRST_TEST_IDX` 210; candidate mask `run_fits` 855–856 | MATCH. 63+252 = 315. On n=1,321 the purged first-block counts are 248 / 243 / 232. Candidates are `idx < s0`. |
| S7-02 | Test blocks are 126 warm origins. A final block shorter than 63 merges into its predecessor. | `build_fold_calendar` 694–712 | MATCH. Remainder 62 merges to one block of 188. Remainder 63 stays two blocks, 126+63. Remainder 64 stays 126+64. A lone short block has no predecessor and is kept. |
| S7-03 | Frozen sample: 8 blocks; evaluation origins 1,001 / 996 / 985; final lengths 119 / 114 / 103; warm mature 1,253 / 1,248 / 1,237. | `fold_calendar_for_population` 715–717 | MATCH. Recomputed on n=1,321 with no prices. |
| S7-04 | Purge: admit `t` only when `idx(t) + h ≤ idx(s0)`, so the label is known at the close of `s0`. Embargo is 0. | `purged_training_indices` 720–723 | MATCH. For s0=315, h=5 keeps 310 and drops 311 (gap 5). h=10 keeps 305, drops 306. h=21 keeps 294, drops 295. The shared close of `s0` is what the inequality says. No second embargo gap. |
| S7-05 | One fit per configuration per test block. Never refit inside a block. | `run_fits` 846–864 | MATCH. One record per `(h, block, config)`. |
| S7-06 | A training prefix with fewer than 20 origins or fewer than 2 events abstains as `TRAINING_FOLD_THIN`, except B0. | `training_fold_is_thin` 726–730; `MIN_TRAIN_ORIGINS` 223; `MIN_TRAIN_EVENTS` 224 | MATCH. n=20 and 2 events is not thin. n=19, or 1 event, or 0 events, is thin. |
| S7-07 | The comparison set is the origins where every compared configuration issues. Binary set is B0, B1×2, B2×2, M3 at C=1.0. Quantile set is Q0, Q1, Q3. Abstentions are reported, not imputed. | `intersection_of_issued` 1060–1066; `FAMILY_CONFIGS` 1000; `build_comparison_sets` 1104–1118 | MATCH for the intersection. `M3-ALL-C0.1` is outside `FAMILY_CONFIGS`. A binary abstention shortens `y` and does not fill a probability. Reporting of that case is RT-01, because the process then dies before the artifact. |
| S8-01 | Event clusters merge when the session-index gap is ≤ h, using the session index, not the position in the comparison set. | `event_clusters` 1406–1418 | MATCH. Gap == h merges. Gap == h+1 stays two clusters. |
| S8-02 | An episode window runs from 21 sessions before the first event origin through h sessions after the last. | `cluster_window` 1421–1423; `EPISODE_PRE` 228 | MATCH. A cluster at 100..105, h=5, has window [79, 105]. A cluster whose first event is near 0 gets a negative start (executed window [−20, 10]); that is the same arithmetic. |
| S8-03 | An episode is the union of clusters whose windows overlap. | `merge_episodes` 1426–1436 | MATCH. Two clusters separated by h+1 still form one episode when the 21-session wings overlap. Separation of 21+h+1 yields two episodes. |
| S8-04 | Honest-N reports origins, events, clusters, episodes and distinct calendar months of event origins. | `honest_n` 1439–1458 | MATCH. Months come from `dates[i][:7]` of event origins only. |
| S8-05 | Power floor is at least 10 episodes and at least 10 distinct event months. Below that the claim is `UNDERPOWERED_DISCLOSED` whatever its bounds say. | `honest_n` 1445; `_binary_claim_row` 1874–1875; `_quantile_claim_row` 1972–1973 | MATCH. 10 episodes and 10 months is met. 10 episodes and 9 months is not. 9 and 9 is not. A failed calibration condition plus an unmet floor still returns `underpowered/blocked claim` (RT-01's companion gate probe). |
| S8-06 | If the floor fails, baseline and INC tables are still produced and the sample is not re-cut. | no re-cut in `evaluate_and_write` | MATCH on the path that finishes. RT-01 is the path that does not finish, so those tables are then absent too. |
| S9-01 | Brier score, and `BSS = 1 − Brier / Brier(B0)`. | `brier_score` 1147; `brier_skill_score` 1153 | MATCH. |
| S9-02 | `CITL = mean(p) − mean(y)`. | `calibration_in_the_large` 1162; draw path 1572 | MATCH. CITL has no class-count denominator: a zero-event draw still returns a finite CITL (`mean(p) − 0`). |
| S9-03 | WACE over bins with `n_b ≥ 100`, edges `[0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0]`, left-closed, last bin closed. Coverage `N_cov / N` is printed. RWSCE uses the same bins and is reported only. | `_wace_bin_ids` 1169–1172; `wace_and_rwsce` 1175–1210; `WACE_MIN_BIN` 219 | MATCH. 0 and 0.019999 → bin 0; 0.02 → bin 1; 1.0 → bin 6. Values outside [0, 1] stay in the end bins; logistic probabilities are inside (0, 1). RWSCE is not a gate condition. |
| S9-04 | AUC is Mann–Whitney with ties counted ½, printed beside the base rate, descriptive only. | `auc_mann_whitney` 1213–1222 | MATCH. Not referenced by `_binary_claim_row`. |
| S9-05 | Every binary metric is also reported by calendar year, by test block and by training rv20 tercile. | `compute_point_metrics` 1333–1358 | MATCH. Keys are `calendar_year`, `test_block`, `training_rv20_tercile`. |
| S9-06 | Richardson `V` with alarm `p ≥ α`, `α_h ∈ {0.5 b_h, b_h, 2 b_h}`, `b_5 = 0.036`, `b_10 = 0.082`, `b_21 = 0.176`. | `richardson_v` 1225–1247; `alpha_grid` 1011–1014; `BASE_RATES` 215 | MATCH. `p == α` alarms (V = 0 when every origin alarms). `p` just below `α` does not (V ≈ −3 on that probe). |
| S9-07 | Quantile metrics: pinball per τ and summed, coverage `P(A ≤ q_τ)`, width `q0.9 − q0.5`, tail exceedance and mean excess above `q0.9`, crossing count, stability by year and block. | `quantile_metric_set` 1282–1306; slices 1359–1370 | MATCH. Crossing count on the comparison set is 0 in the W3 rerun (h5 N_common 1000, h10 991, h21 985) because a crossing origin never enters the set. The abstention table holds the crossings: Q3-ALL abstained 1 and 5. That is the policy in S6-13, not a second count. |
| S9-08 | Early warning for M3 at C=1.0, alarm `p ≥ b_h`: cluster recall, lead to the first close at least 5% below the alarmed origin, missed damage, false-alarm share, false-alarm time outside episode windows, alarm runs, censoring. | `early_warning_table` 2339–2439; call at `evaluate_and_write` 2681–2683 | MATCH for M3. Lead uses `close <= 0.95 * P_origin` after the origin. Exact 5% drop 100→95, alarm only at t=0, h=5: lead n=1, median=min=max=1, censored=0, recall=1, false-alarm share=0. No events: recall is None. False-alarm time denominator is comparison-set origins outside episode windows. |
| S9-09 | The same early-warning statistics for INC, using §8 episodes. | `run_inc` 2317–2318 and 2325 | UNCLEAR. RT-03. |
| S9-10 | Abstention rate and typed reason per configuration; event-origin rate against non-event rate; comparisons on identical eligibility. The gate denominator is evaluation origins. | `abstention_tables` 2084–2110 | MATCH. Rate is the mean over `evaluation_origin_indices`, not over the comparison set. Gate comparisons are `rate <= 0.05` and `gap_pp <= 5` (`_binary_claim_row` 1843). Rate 0.05 and gap 5 pass; 0.0501 and gap 5.01 fail; a negative gap passes. |
| S10-01 | Paired circular moving-block bootstrap. One index draw is applied to every configuration. | `bootstrap_index_matrix` 1490–1515; `binary_draw_statistics` 1540–1548 | MATCH. |
| S10-02 | `L = max(21, 2h)` so 21, 21, 42. Sensitivity rerun at `L = h` so 5, 10, 21, reported only. | `block_length` 1485–1487 | MATCH. |
| S10-03 | 10,000 draws per horizon, population, family and block-length variant. | `N_DRAWS` 220; `run_bootstrap_cells` 1671 | MATCH. Stage 1 passes pop code 0 only (`run_bootstrap_cells` 1663). |
| S10-04 | `starts = rng.integers(0, N, size=ceil(N/L))`; block `(start + arange(L)) % N`; keep the first N. | `bootstrap_index_matrix` 1506–1514 | MATCH. Row 0 of a synthetic matrix matched that formula (`L` 21, two blocks). An empty comparison (`N = 0`) returns shape `(2, 0)` and does not raise. |
| S10-05 | Seeds `SeedSequence([221011, h, pop, fam, var])` with pop 0/1, fam 0/1, var 0/1. | `bootstrap_index_matrix` 1507–1509; `SEED_CODES` 248–252 | MATCH. Primary h=5 seed list is `[221011, 5, 0, 0, 0]`. Replay is identical. Changing pop, fam or var changes the stream. |
| S10-06 | The best-baseline maximum and the better reference are recomputed inside each draw. | `binary_draw_statistics` 1569–1570; `quantile_draw_statistics` 1619–1621; `_point_delta_v` 1898–1903 | MATCH. One synthetic draw: V(B1-20)=1, V(B1-63)≈−25.78, V(B2-21)≈−25.78, V(B2-63)≈−26.78, max=1, V(M3)=1, delta=0. Delta is M3 minus the best baseline, not minus a worse one. Quantile skill uses `min(PL(Q0), PL(Q1))` inside the draw. |
| S10-07 | An undefined gated statistic is −∞ where the gate needs it large and +∞ where it needs it small (WACE). Bounds use `numpy.quantile` over all draws. `nanquantile` is never used. An undefined leave-one-episode-out point estimate is `FRAGILE`. | `binary_draw_statistics` 1545–1580; `_quantile_all_draws` 1627–1648; `loeo_checks` 1712–1751 | MATCH. A zero-event draw stores V=−inf, ΔV=−inf, WACE=+inf, BSS=−inf. All-−inf: raw `np.quantile` is NaN and the helper repairs that to −inf, so the failing extreme stays in the bound. The helper does not drop NaNs: `np.quantile` and the helper are both NaN on `[nan, 0.1, 0.2, 0.3, 0.4]`, while `nanquantile` returns 0.25. A repaired −inf lower bound still fails `lb > 0`. One episode covering every origin is fragile, with undefined V, ΔV and BSS. Zero episodes is not fragile (vacuous); the power floor already requires 10 episodes. |
| S11-01 | Twelve claims: {binary, quantile} × {P-all, P-active} × {5, 10, 21}. Blocked P-active claims keep their `0.05/12` share. | `build_gates` 2023–2032; `GATE_Q` 222 | MATCH. `build_gates` appends 6 scored rows and 6 blocked rows. `GATE_Q = 0.05/12`. |
| S11-02 | Each one-sided lower bound is the `0.05/12` quantile, numpy `method="linear"`, of the 10,000 primary draws. | `gate_lower_bound` 1651–1653 | MATCH. |
| S11-03 | Binary 1: lower bound of `V(M3) > 0` at all three α. | `_binary_claim_row` 1784–1796 | MATCH. One α with lower bound −1 and the others +1, power met, returns `rejected candidate`. |
| S11-04 | Binary 2: lower bound of `ΔV > 0` at `α = b_h`, ΔV = V(M3) − max of the four baselines. | `_binary_claim_row` 1797–1806; S10-06 | MATCH. |
| S11-05 | Binary 3: lower bound of `BSS(M3 vs B0) > 0`. | `_binary_claim_row` 1808–1817 | MATCH. |
| S11-06 | Binary 4: the 90% CITL interval (0.05 and 0.95 quantiles) contains 0, and the 0.05 quantile of WACE is at most `0.5 b_h`. `N_cov / N < 0.5` fails as `CALIBRATION_UNDERCOVERED`. | `_binary_claim_row` 1819–1834; `interval_90` 1656–1657 | MATCH. A WACE vector whose `0.05/12` quantile is 0 (under the cap 0.018) and whose 0.05 quantile is 1 stores 1.0 and fails condition 4. The code uses 0.05, which is what this sentence says, not `GATE_Q`. Coverage exactly 0.5 passes. Coverage 0.49 sets `CALIBRATION_UNDERCOVERED`. An all-NaN CITL interval does not contain 0. |
| S11-07 | Binary 5: M3 abstains on at most 5% of evaluation origins, and the event-minus-nonevent gap is at most 5 percentage points. Else `ABSTENTION_CONCENTRATED`. | `_binary_claim_row` 1836–1846 | MATCH. See S9-10 for the boundary calls. The denominator function is the evaluation-origin union. |
| S11-08 | Binary 6: dropping each episode window keeps the point estimates of V at `α = b_h`, ΔV and BSS above 0. Point estimates only, no draws, no refit. Else `FRAGILE`. | `loeo_checks` 1709–1760 | MATCH. Deletion is on the comparison-set arrays (the scored origins). Training is not refit. Undefined estimates fail the condition. |
| S11-09 | Binary 7 and quantile 5: the §8 power floor holds. A miss forces `underpowered/blocked claim` even if another condition failed. | `_binary_claim_row` 1858–1879; `_quantile_claim_row` 1959–1977 | MATCH. Coverage 0.49 and power unmet returns `underpowered/blocked claim`, not `rejected candidate`. |
| S11-10 | Quantile 1: lower bound of pinball skill `1 − PL(Q3) / min(PL(Q0), PL(Q1)) > 0`, minimum inside the draw. | `_quantile_claim_row` 1911–1921; `quantile_draw_statistics` 1619 | MATCH. |
| S11-11 | Quantile 2: at each τ, the 90% interval of coverage intersects `[τ − 0.05, τ + 0.05]`. | `_quantile_claim_row` 1923–1936 | MATCH. The test is `iv[1] >= τ−0.05` and `iv[0] <= τ+0.05`. |
| S11-12 | Quantile 3 and 4: the same abstention rule for Q3, and leave-one-episode-out keeps pinball skill above 0. | `_quantile_claim_row` 1937–1957 | MATCH. Same threshold constants and the same LOEO helper. |
| S11-13 | Baseline-against-baseline differences are descriptive and are not claims. | `descriptive_differences` 2038; `VERDICT_DESCRIPTIVE` 1005 | MATCH. |
| S12-01 | Verdict words, exactly: `accepted descriptive measurement`; `rejected candidate`; `underpowered/blocked claim`; `qualified research evidence (development, reconstructed)`. | `VERDICT_*` 1005–1008 | MATCH. `verbatim` equality holds for all four constants. |
| S12-02 | Below the power floor, or blocked by a typed reason, the verdict is `underpowered/blocked claim`. A claim that fails any condition while the floor holds is `rejected candidate`. A claim that passes every condition is the qualified-research verdict. | `_binary_claim_row` 1874–1879 | MATCH. All-pass synthetic row (power met, WACE quantile 0, coverage 0.8, positive bounds) returns the qualified-research verdict. One failed α returns `rejected candidate`. |
| S12-03 | Rungs 1–2 always run. Rung 3 runs on P-all now. Rungs 4–5 are absent. | `CONFIGURATIONS` plus blocked rows | MATCH. |
| S12-04 | One execution per revision. A code-defect rerun keeps the original output and names the defect, the fix and both results. | `main` 2783–2793 | UNCLEAR. RT-07. |
| S12-05 | If the observer lands with any different rule value, every P-active claim becomes `underpowered/blocked claim` with `OBSERVER_RULES_CHANGED`, permanently. | no such string in the runner | UNCLEAR. RT-09. |
| S12-06 | A failed claim is not re-tuned. A passed claim is not promoted by this file. | no retune or promotion call | MATCH. |
| S12-07 | A manifest-row, rights or basis change is `BLOCKED` and needs a new revision. | `verify_identities` 341–356 | MATCH. Manifest blob and version `1.0.0` are checked before a sample is read. |
| S12-08 | The results note and the JSON both carry the three §3 check-5 identities (manifest version `1.0.0`, `subframe_content_sha256`, prereg git blob), the commit sha, and the blob shas of the script and of the test file, plus blocked or abstained rows with their types. | `render_markdown` 2458–2540; `assemble_payload` 2624–2640; `write_blocked_artifact` 2756–2758; `main` 2835–2847 | MISMATCH. RT-04. |
| S12-09 | The census carries typed exclusions `PRE_ENTITLEMENT`, `WARMUP`, `IMMATURE`, `TRAINING_FOLD_THIN` and the other types named in the prereg. | `census_populations` 665–688 | MISMATCH. RT-05. |
| S12-10 | Negative control: `numpy.roll(y, len(y)//2)` per training prefix, no seed; report BSS, V at `α = b_h` and pinball skill; not a gate. | `negative_control_shift` 2116–2119; `run_negative_control` 2149–2231 | MATCH. The shift is per training prefix. Scoring uses the eval-length arrays `y_eval` and `p_eval`, masked by `common_mask & issued_shift`, so this path does not have the RT-01 length bug. The existing test covers the roll. |
| S12-11 | The dedicated test file proves purge, fold calendar, comparison-set intersection, reuse of one index draw, and crossing-then-clip, on synthetic data only. | `tests/test_grey_deer_pullback_stage1.py` | MATCH. Those five tests are present. This lane's run: 16 passed. |

## Findings

Each repro was run with `~/lanes/venv/bin/python`. The header for every snippet is:

```python
import sys
sys.path.insert(0, "/home/ubuntu3/lanes/wt/gd-w4-g-rt1")
import numpy as np
import pandas as pd
import scripts.research.grey_deer_pullback_stage1 as s
```

The pasted output is the stdout of that snippet (warnings omitted except where they are the behaviour). The combined run exited 0.

### RT-01 — MAJOR — MISMATCH

`scripts/research/grey_deer_pullback_stage1.py:1378`

Quote: `y[sens_mask], p0=cell["p"]["B0"][sens_mask]`

The prereg (§6) says `C = 0.1` is run as a sensitivity row and is never a gate, and (§7) says abstentions are reported, not imputed. A block may abstain as `TRAINING_FOLD_THIN`, `FIT_NONCONVERGENCE` or `FEATURE_DEGENERATE`.

`build_comparison_sets` stores `y` and `p["B0"]` at comparison-set length (`y_eval[common]`, lines 1116–1128). It stores the sensitivity mask as `common & sens["issued"]` and `sensitivity["p"]` at evaluation-origin length (lines 1133–1138). Those lengths differ as soon as any binary claim configuration abstains on one origin. `compute_point_metrics` then boolean-indexes the short arrays with the long mask. `evaluate_and_write` calls that function at line 2666, before `compute_episodes` (2667), `run_bootstrap_cells` (2669) and `build_gates` (2670). The exception is not caught there, so no results note and no JSON are written.

When every binary claim configuration issues, `common` is all true, the lengths match, and the sensitivity metrics are aligned. A quantile abstention does not enter this branch. The W3 rerun is the all-issued binary case, so its gate file was not produced by this crash.

```python
def fake_record(cid, kind, s0, e0, abstain0=False):
    m = e0 - s0 + 1
    issued = np.ones(m, dtype=bool)
    reasons = np.full(m, None, dtype=object)
    if abstain0:
        issued[0] = False
        reasons[0] = "FIT_NONCONVERGENCE"
    rec = {"config": cid, "kind": kind, "population": "P-all",
           "block": [int(s0), int(e0)], "train": {"origins": 40, "events": 4.0},
           "issued": issued, "reasons": reasons}
    if kind == "binary":
        rec["p"] = np.full(m, 0.2)
    else:
        rec["q"] = {k: np.full(m, 0.02) for k in s.TAU_KEYS}
    return rec

def fill_fits(abstain=None):
    fits = {"fits": {}}
    for h in s.HORIZONS:
        for bi, (s0, e0) in enumerate(s.fold_calendar_for_population(400, h), start=1):
            for cid in s.BINARY_CLAIM_CONFIGS + (s.SENSITIVITY_CONFIG,):
                fits["fits"][(h, bi, cid)] = fake_record(cid, "binary", s0, e0, abstain == (h, cid))
            for cid in s.QUANTILE_CLAIM_CONFIGS:
                fits["fits"][(h, bi, cid)] = fake_record(cid, "quantile", s0, e0, abstain == (h, cid))
    return fits

rng = np.random.default_rng(7)
px = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, 400)))
close = pd.Series(px, index=[f"d{i:04d}" for i in range(400)])
labels = s.build_labels(close)
rv = np.abs(rng.normal(0.01, 0.002, 400)) + 0.005
dates = [f"2021-{(i % 12) + 1:02d}-01" for i in range(400)]

comp = s.build_comparison_sets(fill_fits(None), 400, labels)
cell = comp[5]["binary"]
print("no abstention", "eval", len(cell["eval_origin_idx"]), "y", len(cell["y"]),
      "sens_mask", len(cell["sensitivity"]["mask"]))
s.compute_point_metrics(comp, 400, rv, dates)
print("no abstention: compute_point_metrics returned")

comp_q = s.build_comparison_sets(fill_fits((5, "Q3-ALL")), 400, labels)
qc = comp_q[5]["quantile"]
print("Q3 abstains origin 0: N_common", int(qc["common_mask"].sum()), "of", len(qc["eval_origin_idx"]))
s.compute_point_metrics(comp_q, 400, rv, dates)
print("Q3 abstention: compute_point_metrics returned")

comp_b = s.build_comparison_sets(fill_fits((5, "M3-ALL")), 400, labels)
bc = comp_b[5]["binary"]
print("M3 abstains", "eval", len(bc["eval_origin_idx"]), "y", len(bc["y"]),
      "sens_mask", len(bc["sensitivity"]["mask"]), "sens_any", bool(bc["sensitivity"]["mask"].any()))
try:
    s.compute_point_metrics(comp_b, 400, rv, dates)
    print("NO CRASH")
except Exception as exc:
    print(type(exc).__name__, exc)
```

Output:

```
no abstention eval 80 y 80 sens_mask 80
no abstention: compute_point_metrics returned
Q3 abstains origin 0: N_common 79 of 80
Q3 abstention: compute_point_metrics returned
M3 abstains eval 80 y 79 sens_mask 80 sens_any True
IndexError boolean index did not match indexed array along axis 0; size of axis is 79 but size of corresponding boolean axis is 80
```

The same `IndexError` and the same lengths (eval 80, y 79, sens mask 80, sens p 80) occurred when `run_fits` itself, on a 400-row geometric Brownian series (seed 7), left `M3-ALL` unissued on origin 0 with reason `FIT_NONCONVERGENCE` while `M3-ALL-C0.1` issued. The fabricated masks above are the controlled form of that call.

### RT-02 — MINOR — MISMATCH

`scripts/research/grey_deer_pullback_stage1.py:2302`

Quote: `origin_idx = cell["origin_idx"]`

The prereg (§6) says INC is scored on the dates of the P-all evaluation origins that it covers. Evaluation origins are the test-block union (`evaluation_origin_indices`, lines 1020–1024). `cell["origin_idx"]` is that union filtered by the binary comparison set (line 1116). The artifact field is named `evaluation_origins` and is `len(origin_idx)` (line 2321).

A binary abstention therefore drops origins INC might cover, and the name in the artifact still says evaluation origins. In the W3 rerun the two sets are the same length, because no binary configuration abstained: the field is 1001 / 996 / 985 and covered is 1001 / 996 / 985. INC is not a gate. The unpatched `run_inc` was not called on a market store.

The length split is the RT-01 cell: eval 80, comparison-set `y` 79. The snippet below shows that the stored field equals `len(cell["origin_idx"])` on a patched replay whose comparison set was supplied directly.

```python
import engine.risk_radar as rr
import engine.risk_radar_backtest as rrb
import scripts.research.risk_radar_displayed_probability_audit as audit
idx = pd.bdate_range("2022-01-03", periods=40)
protocol = np.full(40, 100.0); protocol[6] = 90.0
protocol_s = pd.Series(protocol, index=idx)
native_s = pd.Series(np.linspace(100.0, 110.0, 40), index=idx)
rr._calib = lambda: {"patched": True}
rr.leading_signals = lambda: pd.DataFrame({"x": np.ones(40)}, index=idx)
rr.subscore_series = lambda sigs, calib: pd.DataFrame({"s": np.ones(40)}, index=idx)
rrb.state_series = lambda subs, calib, sigs=None: pd.Series(["watch"] * 40, index=idx)
rrb._spy = lambda drop_missing=False: native_s
audit.hot_tier_a_count = lambda subs, calib: pd.Series(np.zeros(40, dtype=int), index=idx)
audit.displayed_probability_series = lambda state, hot, calib, horizon: pd.Series(np.full(40, 0.5), index=idx)
origin_idx = np.arange(0, 31)
comp_by_h = {hh: {"binary": {"origin_idx": origin_idx, "y": np.zeros(31, dtype=bool),
                             "a": np.zeros(31), "episodes": []}} for hh in s.HORIZONS}
inc = s.run_inc(comp_by_h, protocol_s, deviations=[])
print(inc["horizons"]["h5"]["evaluation_origins"], len(origin_idx))
```

Output of the executed call, which also built protocol events so RT-03 could be read off the same return:

```
field evaluation_origins 31 len(origin_idx) 31
```

### RT-03 — MAJOR — UNCLEAR

`scripts/research/grey_deer_pullback_stage1.py:2317`

Quote: `early_warning_table(p, cell["y"], origin_idx, close_arr`

§6 says INC is never scored against the Massive RAW label, and that its label is the native close-relative 5% loss. §9 defines early warning for INC with the §8 episodes, and §8 builds episodes from the claim's comparison set, which is the protocol label. Those two sentences cannot both be satisfied by one table. The code splits them: `binary_metric_set` receives `y_native` (line 2315); `early_warning_table` receives `cell["y"]`, `cell["a"]`, `cell["episodes"]` and the protocol close (lines 2317–2318). The JSON key is `early_warning_vs_protocol_episodes`.

On one synthetic pair the native series is a straight rise (no 5% drop) and the protocol series drops 10% at session 6. Displayed probability is 0.5 everywhere, which alarms at `b_5 = 0.036`. Metrics report 0 native events. Early warning reports the protocol cluster.

```python
# same patches as RT-02, then:
import lib.observed_moves as om
A = om.forward_max_loss(protocol_s, 5)
Y = om.loss_event(A, 0.05).fillna(False).astype(bool).to_numpy()
origin_idx = np.arange(0, 31)
y_cmp = Y[origin_idx]
episodes = s.merge_episodes(s.event_clusters(origin_idx[y_cmp], 5), 5)
print("protocol events", int(y_cmp.sum()), "windows", [e["window"] for e in episodes])
comp_by_h = {hh: {"binary": {"origin_idx": origin_idx, "y": y_cmp,
                             "a": A.to_numpy()[origin_idx], "episodes": episodes}}
             for hh in s.HORIZONS}
inc = s.run_inc(comp_by_h, protocol_s, deviations=[])
h5 = inc["horizons"]["h5"]
ew = h5["early_warning_vs_protocol_episodes"]
print("native events", h5["metrics_vs_native_label"]["events"], "covered", h5["covered"],
      "protocol clusters", ew["n_clusters"], "protocol recall", ew["cluster_recall"],
      "false_alarm_share", ew["false_alarm_share"])
```

Output:

```
protocol events 5 windows [[-20, 10]]
native events 0 covered 31 protocol clusters 1 protocol recall 1.0 false_alarm_share 0.8387096774193549
```

The same native-versus-protocol formula, on one geometric Brownian series with planted 5% drops and the same closes for both, disagreed on 0 origins (h=5/10/21: 13/45/92 events). The split appears when the native close and the protocol close differ, which is the case §6 is written for. The W3 deviation log records native events 11/35/113 against protocol events 11/36/117, and it states that early warning was published against protocol episodes. Gates do not read that table.

### RT-04 — MINOR — MISMATCH

`scripts/research/grey_deer_pullback_stage1.py:2467`

Quote: `` `subframe_content_sha256` matches ``

§3 check 5 says every result artifact carries manifest version `1.0.0`, the subframe hash, and the prereg git blob. §12 says the note and the JSON both carry those three, plus the commit sha and the script and test blob shas.

The success JSON from the W3 rerun carries all of them: subframe `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb`, prereg blob `49a68b5e9c6543d662044b0aa391c4b6e6e6052e`, manifest `1.0.0` blob `38925409555d046eb9d3ad38ddaba33e2159a3d3`, commit `fbeff30d34ed7a8280f8dc9ca1a13d21b8db4c24`, script blob `9eeba12d9f668dbe8940f4f25109a3da1cbe75be`, test blob `6d404f95d4cb25307d33d22c3053a6915046dc47`. The note's sample line does not contain the hash, the script blob or the test blob. The rerun note's fifth line is the same sentence `render_markdown` produces.

The blocked path (`write_blocked_artifact` 2756–2758, `main` 2835–2847) writes JSON only. It attaches `verify_identities` when that step has passed, and it does not attach a sample, so the subframe hash is absent. There is no markdown sibling.

```python
payload = {
    "schema": s.SCHEMA,
    "prereg": {"blob_sha": s.PREREG_BLOB, "sha256": s.PREREG_SHA256, "path": s.PREREG_PATH},
    "manifest": {"version": s.MANIFEST_VERSION, "blob_sha": s.MANIFEST_BLOB, "path": s.MANIFEST_PATH},
    "run": {"commit_sha": "abc", "script_blob_sha": "scriptblob", "test_blob_sha": "testblob"},
    "sample": {"rows": 1321, "first_date": "2021-07-06", "last_date": "2026-10-07",
               "subframe_content_sha256": s.SUBFRAME_SHA256},
    "trial_budget": {"family": s.TRIAL_FAMILY, "budget": s.TRIAL_BUDGET, "basis": "itemized"},
    "gates": [], "episodes": {}, "comparison_sets": {}, "negative_control": {},
    "inc": {"blocked": "INC_SOURCE_UNAVAILABLE", "detail": "synthetic"},
    "deviations": [], "blocked": [],
}
note = s.render_markdown(payload)
print(note.splitlines()[4])
print("hash value in note", s.SUBFRAME_SHA256 in note)
print("script blob in note", "scriptblob" in note)
print("test blob in note", "testblob" in note)
print("prereg blob in note", s.PREREG_BLOB in note)
print("manifest version in note", s.MANIFEST_VERSION in note)
```

Output:

```
- sample: 1321 rows 2021-07-06..2026-10-07, `subframe_content_sha256` matches
hash value in note False
script blob in note False
test blob in note False
prereg blob in note True
manifest version in note True
```

Blocked path, executed by `main(["--skip-hydrate", "--out-dir", "/tmp/gd-rt1-blocked"])` with `collectors.massive_stock_day.load_ticker` replaced by a function that returns an empty frame. The worktree was clean, so `verify_identities` ran. No trial ledger was opened: `load_sample` raises before `trial_ledger_scope`. Output:

```
BLOCKED / SOURCE_UNREADABLE
main rc 2
blocked keys ['blocked', 'deviations', 'hydrate', 'manifest', 'prereg', 'run', 'schema']
has subframe False
has prereg blob True
has manifest version True
blocked type SOURCE_UNREADABLE
markdown written False
```

### RT-05 — MINOR — MISMATCH

`scripts/research/grey_deer_pullback_stage1.py:675`

Quote: `"warmup": int((idx < WARM_IDX).sum())`

§12 asks the census to carry the typed exclusions `PRE_ENTITLEMENT`, `WARMUP`, `IMMATURE` and `TRAINING_FOLD_THIN`. The census uses lowercase counts `pre_entitlement`, `warmup`, `immature`, `eligible`. The uppercase tokens `PRE_ENTITLEMENT`, `WARMUP` and `IMMATURE` do not appear. `TRAINING_FOLD_THIN` appears only inside the P-active detail sentence `"recorded, not run; TRAINING_FOLD_THIN is counted per block in folds/fits"`, not as a count. Thin-fold counts live on `folds.thin_blocks` and on abstention `by_type`. The W3 rerun census keys are the lowercase set.

```python
census = s.census_populations(1321, 3)
print(census[0])
blob = str(census)
for token in ("PRE_ENTITLEMENT", "WARMUP", "IMMATURE", "TRAINING_FOLD_THIN"):
    print(token, token in blob)
```

Output:

```
{'population': 'P-all', 'horizon': 5, 'pre_entitlement': 3, 'warmup': 63, 'immature': 5, 'eligible': 1253}
PRE_ENTITLEMENT False
WARMUP False
IMMATURE False
TRAINING_FOLD_THIN True
```

### RT-06 — NOTE — UNCLEAR

`scripts/research/grey_deer_pullback_stage1.py:645`

Quote: `feature {name} non-finite at row idx`

§6 says every feature window is full at index 63 and later, given the stated `min_periods`. It does not name a whole-run refusal. `build_features` raises `Blocked FEATURE_UNDEFINED_AFTER_WARMUP` on the first non-finite feature at index ≥ 63. Other degeneracies (`FEATURE_DEGENERATE`, a zero training standard deviation) abstain for that block. A flat close makes `log(rv) = −inf`. A noisy series of the same length is finite at index 63. The W3 run completed, so this refusal did not fire on the frozen SPY sample.

```python
try:
    s.build_features(pd.Series(np.full(80, 100.0), index=[str(i) for i in range(80)]))
    print("flat: no refusal")
except s.Blocked as exc:
    print(exc.type, exc.detail)
```

Output (the log-of-zero warning is the cause of the refusal):

```
FEATURE_UNDEFINED_AFTER_WARMUP feature log_rv20 non-finite at row idx 63 (date 63); refusing, never imputing
```

### RT-07 — NOTE — UNCLEAR

`scripts/research/grey_deer_pullback_stage1.py:2786`

Quote: `--rerun-of needs a non-default --out-dir so the original output is kept`

§12 says one execution per revision, and that a code-defect rerun keeps the original output. `main` enforces that only when `--rerun-of` is passed: the default directory is then a `parser.error`, and a missing `--rerun-defect` is also an error. A second invocation without `--rerun-of` uses the default directory and overwrites `PULLBACK_STAGE1_RESULTS_2026-10-11.{json,md}`. The existing test covers the flag, not a second plain invocation. The W3 rerun did pass `--rerun-of` and wrote `pullback_stage1_r1/`. This repro does not write an artifact.

```python
import io, contextlib
err = io.StringIO()
try:
    with contextlib.redirect_stderr(err):
        s.main(["--rerun-of", "dd67262e7ab8", "--rerun-defect", "synthetic"])
except SystemExit as exc:
    print("SystemExit", exc.code)
print(err.getvalue().strip().splitlines()[-1])
```

Output:

```
SystemExit 2
grey_deer_pullback_stage1: error: --rerun-of needs a non-default --out-dir so the original output is kept
```

### RT-08 — NOTE — UNCLEAR

`scripts/research/grey_deer_pullback_stage1.py:654`

Quote: `P-active blocked until the observer is on main`

§4 says `D_total` is reported for P-active origins. The string `D_total` does not occur in the runner. Stage 1 has nothing to report: `build_populations(80)["P-active"]["blocked"]` is `OBSERVER_NOT_ON_MAIN`, and `D_total` is never a gate. §12 also says nothing in this file may change between stage 1 and stage 2, so a later P-active pass of this same file has no function to call.

```python
src = open("scripts/research/grey_deer_pullback_stage1.py", encoding="utf-8").read()
print("D_total present", "D_total" in src)
print(s.build_populations(80)["P-active"]["blocked"])
```

Output:

```
D_total present False
OBSERVER_NOT_ON_MAIN
```

### RT-09 — NOTE — UNCLEAR

`scripts/research/grey_deer_pullback_stage1.py:2015`

Quote: `flags: ["OBSERVER_NOT_ON_MAIN"]`

§12 says that if the observer lands with any different `close_path.v1` value, every P-active claim on this sample becomes `underpowered/blocked claim` with type `OBSERVER_RULES_CHANGED`, permanently. That string does not occur. `_blocked_claim_row` always flags `OBSERVER_NOT_ON_MAIN`. Stage 1 is unaffected, because the observer is not on main. The same "nothing in this file may change between the stages" sentence means the branch is absent for stage 2 as well.

```python
src = open("scripts/research/grey_deer_pullback_stage1.py", encoding="utf-8").read()
print("OBSERVER_RULES_CHANGED present", "OBSERVER_RULES_CHANGED" in src)
print(s._blocked_claim_row(5, "binary")["verdict"], s._blocked_claim_row(5, "binary")["flags"])
```

Output:

```
OBSERVER_RULES_CHANGED present False
underpowered/blocked claim ['OBSERVER_NOT_ON_MAIN']
```

## Minimum checks

| Check | Result |
|---|---|
| A is the min of closes `t+1..t+h`, and `≥ 0.05` is inclusive | MATCH. S4-01, S4-02. Output above. |
| Purge drops every training row whose label window overlaps the test block; boundary `t = s0 − h` is kept | MATCH. S7-04. h=5 keeps 310, drops 311. |
| Fold calendar 63 / 315 / 126 / 63 and the final-block merge | MATCH. S7-02, S7-03. Remainder 62 merges; 63 does not. Frozen-sample finals 119 / 114 / 103. |
| Episodes merge at gap ≤ h; window is 21 before through h after; power floor is ≥10 episodes and ≥10 event months | MATCH. S8-01..S8-05. Gap `h+1` is one episode via the wings. 10 episodes and 9 months fails. |
| Bootstrap: circular blocks, `L = max(21, 2h)`, sensitivity `L = h`, seeds `[221011, h, pop, fam, var]`, undefined stats on the failing side, `numpy.quantile` not `nanquantile` | MATCH. S10-01..S10-07. |
| Gates: quantile `0.05/12`; WACE uses 0.05; verdict words exact | MATCH. S11-01, S11-06, S12-01. Discriminating WACE stores 1.0 and fails; `0.05/12` on that vector is 0. |
| Trial ledger records budget 69 before outcomes | MATCH. S6-18. Ledger line written to `/tmp`, not to `data/`: `{"family": "grey_deer_pullback_v1", "kind": "declared_budget", "n": 69}`. |

Gate-priority output from the same synthetic claim-row calls:

```
q_gate 0.0 q05 1.0 cap 0.018
cond4 False stored 1.0 verdict rejected candidate
coverage 0.5 verdict qualified research evidence (development, reconstructed) cond4 True
coverage 0.49 power unmet False CALIBRATION_UNDERCOVERED underpowered/blocked claim
one alpha fails rejected candidate
all pass qualified research evidence (development, reconstructed)
blocked words underpowered/blocked claim ['OBSERVER_NOT_ON_MAIN']
```

The qualified-research string above is the prereg's verdict constant, returned by `_binary_claim_row` on a hand-built draw. It is not a statement about the SPY run. The SPY run's 12 verdicts are all `underpowered/blocked claim`.

## Checked and not filed

- Native and protocol labels agree when both are computed on the same closes (0 disagreements on the planted synthetic series). The published count gap is the two close series, which RT-03 is about.
- `crossing_count` of 0 on the scored set is the crossing-abstention policy. The crossings are in `by_type`.
- The −inf quantile repair puts the failing extreme back after `numpy.quantile` returns NaN for `inf − inf`. It does not turn a failing bound into a passing one.
- An empty comparison bootstrap returns a `(draws, 0)` index matrix. Draw statistics are −inf / +inf / NaN and the CITL interval does not contain 0.
- `FEATURE_DEGENERATE` is an extra abstention type. It refuses to divide by a zero training standard deviation. That is stricter than a named prereg type and does not impute. Not filed separately; it is one of the abstentions that triggers RT-01.
- Leave-one-episode-out with zero episodes is vacuous and does not by itself award a passing claim, because the power floor requires 10 episodes.
- The purge keeps `t = s0 − h`. That origin's label uses `P_{s0}`, which the prereg calls known at the close of `s0`.

## Tests

```
~/lanes/venv/bin/python -m pytest -q tests/test_grey_deer_pullback_stage1.py
................                                                         [100%]
16 passed in 4.04s
```

The 16 tests include purge (parametrized over the three horizons), the fold calendar, comparison-set intersection, one shared bootstrap index draw, and crossing-then-clip. They do not construct a binary abstention beside an issued `M3-ALL-C0.1` row, which is why RT-01 is uncaught.
