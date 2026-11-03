# E0 — Frozen research and outcome protocol (Rates & Inflation Command, e2e 2026-10-13)

Status: **FROZEN** on merge of the PR that adds this file (seat `fc3dfe4b`, task-graph row E0). Revision 3: it applies
both independent review rounds recorded in §9. Census basis: read-only E0 census of `origin/main` @
`1e9364f5ab8c4452820731e87da2c138e53b0571` (verdict PASS-WITH-GAPS, gaps in §8). Acceptance rows served: **A28**
(finite trials) directly; inputs to M0 (A11, A28, A30), E1 (A09, A31, A32), X0 (A29), E2 (A29, A30, A32, A48).
Masterplan pin: `research/rates_inflation_command/e2e_20261013/MASTERPLAN.md` @ `fd5c6600` §7, §8, §13.

**Owners reused, nothing new minted.** Trial counting = `engine/trial_ledger.py` (`TrialLedger.log_declared_budget`,
`data/trial_ledger.jsonl`). Frozen model specs = `research/release_forecast/PREREG_*.md`. Prospective record and the
only advancer = `scripts/build_release_forecast.py` → `data/release_forecast/forward_ledger.jsonl` (MRI-R8).
Release dates = the ALFRED first-vintage `realtime_start` that the release owners already read
(`engine/release_forecast.py`, `engine/release_cpi_target_history.py`, `engine/pit.py`). FOMC decision days =
`engine/event_window.py::_FOMC_ANNOUNCEMENT_DATES`. Daily rates = the `fred` group of `lib/store` (DGS2, DGS10, DFII10,
T10YIE are already collected for `engine/forex_dollar.py`, `engine/transmission_chains.py` and the market-OS rates
curves). Statistics = existing primitives only, called with parameters and never re-implemented:
`engine/grading_stats.py` (`block_bootstrap_scalar_ci`, `wilson_ci`), `engine/challenger_spa_comparison.py`
(`newey_west_lag`, `newey_west_lrvar`), `engine/desk_placebo.py` (`holm_adjust`). The corrections owner is
`data/release_forecast/{defect_notices.json,official_actual_defects.json}`. The CPI coherent target is
`data/release_forecast/cpi_truth/alfred_same_release_vintage_proxy_v1.json` (parity in `cpi_truth/parity_report.json`).
No evaluator, scorecard, trial plane, Research Factory, queue, calendar or publication surface is created here.

## 0. What this protocol is and is not

- It freezes finite questions **before** any new outcome work (masterplan §7). Each later task (M0, E1, X0, E2)
  executes exactly what is frozen here, or records a deviation that §7 allows.
- **E0 only tightens claims.** It never overrides an owner's existing kill rule and never reactivates a killed or
  `benchmark_only` family. E0 itself changes no producer. Task E1 is a separate PR with its own review: it may
  **extend** the forward-ledger writer's row vocabulary, append-only and nightly-only (§5). That is the only producer
  change this protocol authorizes.
- **Retrospective evidence can falsify or qualify; it cannot promote.** A coherent-target walk-forward over history
  was designed with that history visible (the PREREG files were frozen in 2026-07 after looking at 2010+ data). It is
  therefore in-sample to the design period. Only forecasts issued **after this protocol's freeze commit** and scored
  against their first print under the owner's immutable record are promotion-capable (§5).
- Natural time governs. A forecast cannot be graded before its release. Underpowered evidence stays `INSUFFICIENT`,
  `NOT_DEMONSTRATED` or `PENDING`, never "trending" or "promising".
- A NO-GO closes the specific construction tested. It never waives a mandatory product capability
  (basis-qualified display, abstention, rights), and "not found yet" is not "does not exist".

## 1. Retained evidence (never rerun as "new")

| Evidence | Identity | Verdict carried forward |
|---|---|---|
| #7909 RD1 rates direction (held, read-only) | head `1ddc25a80f6c2f6ce87a602f883056671f1f0d50`; freeze `8796829eea9fe8792a73155f64d5c1dbe83ae3b6`; 48 configs; `research/rates_direction/RD1_RESULTS_2026-09-24.md`; `results_v1.json` sha256 `4c91cbd0…a3d812` | No-change MSE 176.53 bp² beat curve+real 184.13 (+4.30%, failed the 5% hurdle) → `DEC:RIC-RD1-NO-PROMOTION`. Counts 48 trials. |
| #7909 swing proxy | freeze `975259d0f78b090b8941af5e5168a906d39a7905`; 18 configs; `SWING_PROXY_EXTENDED_RESULTS_2026-09-24.md` | Trend/vol Brier 0.665530 vs MPR 0.665704 (−0.026%); P+R pilot +1.71% became −0.575% on the expanded partition → no candidate accepted. Counts 18 trials. |
| MRI claims | `scripts/build_release_forecast.py:159-175` | `benchmark_only` (attempt-2 MAE 43.9k vs naive 27.9k full; 17.7k vs 14.8k 2021+). Not in M0. |
| MRI NFP first→third revision (Track R) | `PREREG_NFP_REVISION_V1.md`, `RESULTS_NFP_REVISION_V1.md` | KILL (Wilson LB ≤ majority base rate). Not in M0. |
| cpi_bridge core | `PREREG_CPI_BRIDGE_V1.md` | NULL / not shadowed. Not in M0. |
| AHE / AWH | `results/backtest_nfp_decomp_v1.md` | `no_data`, 0 predictions. Not in M0. |
| Retail sales | `PREREG_NEW_TARGETS_V1.md` | scaffold only. Not in M0. |
| CPI revision / ex-ante CPI timing | `DNR:KILL-CPI-REVISION-MODEL`, `DNR:KILL-CPI-020`, `DNR:KILL-CPI-IX1-DOWN` | Standing kills; nothing here re-tests them. |
| Calendar-gated risk | `DNR:KILL-CALENDAR-GATED-RISK` | No calendar signal, timing predictor or sizing is built (also excluded by the commission). |

The #7909 PR stays held. This protocol cites its bytes read-only, never merges, arms, pushes to or comments on it,
and E2 consumes its verdicts as retained negatives.

## 2. Hypotheses and finite questions

Every question lists: question · target · origin · baselines · criterion · margin · trial budget · dependence ·
accept / hold / no-go. Metric families are never pooled (§4).

### H1 — First-print models vs naive baselines on the same origin and target (task M0, then E1)

**Question.** Under a coherent first-print target, does each inherited MRI model beat the naive baselines for the
same release, period, origin and target? A gain that disappears under coherent vintages falsifies the old accuracy
claim (masterplan §7 H1; acceptance A11, A30).

**Target (per family, never pooled).**
- CPI headline / core m/m: `alfred_same_release_vintage_proxy_v1.published_proxy_1dp` (the registry's coherent
  epoch; `official_first_print_epoch` stays `withheld`). Rows whose proxy disagrees with `parity_report.json` are
  re-scored without them as a reported sensitivity (§2.H1 Sensitivities).
- NFP m/m change, PCE headline / core m/m, PPI final demand m/m: the same-release ALFRED vintage first print
  (`realtime_start` = the release day), never a later revised value.
- First-print target and revised-history fit are separate metric families and are never pooled (§4).

**Origin.** D = the calendar day before the actual release. Each spec builds its features under **the
point-in-time rules of its own frozen PREREG**. ALFRED `realtime_start ≤ D` governs only the legs that the PREREG
reads from ALFRED vintages. The A09 label is `day_precision_origin`, and no intraday ordering is claimed. Two kinds
of leg are not vintage-exact, and M0 lists them per spec, from the PREREG text, before the run:
- **Revision-optimistic legs**, as the PREREG itself declares them (for example `PREREG_V3_FACTOR.md` §1.2–1.3:
  DTWEXBGS, PPIFES / PPIFIS, AWHMAN, ADP). A later vintage can only flatter the model. A spec with any such leg can
  therefore still be `FALSIFIED`, but its best attainable verdict is `NOT_DEMONSTRATED` with reason `non_pit_inputs`.
  It can never be `QUALIFIED_RETROSPECTIVE`.
- **Assumed-lag legs** (for example champion v2's ZORI at observation date + 45 days, `PREREG_V2.md:41,92`). These
  carry the limitation label `approximate_pit_lag` on every verdict for that spec.

**Inclusion and missingness.** A period whose first print never appeared (shutdown-cancelled) is `MISSING_SOURCE`.
It is excluded from accuracy and counted in coverage. A delayed release keeps D = the day before the actual release
and carries the owner's quirk flag (`quirk_calendars/government_shutdowns.yml`, `hurricane_landfalls.yml`,
`nfp_preliminary_benchmarks.yml`). Each excluded row is listed by (release, period, reason).

**Ordinary corrections.** An agency erratum within the same release cycle is re-scored against the corrected value
as a reported sensitivity, owned by `defect_notices.json` / `official_actual_defects.json`. Ordinary later revisions
never change the first-print target.

**Splits.** Expanding-window walk-forward, first prediction after `MIN_TRAIN_OBS = 60` (owner default,
`engine/release_forecast.py`), refit every origin, with **zero tuning**: every spec runs at its PREREG commit.
`mf_energy` runs at its T−1 configuration only (`PREREG_MF_ENERGY_V1.md:320-331`). Its early-run variants are not
evaluated. There is no held-out tuning split because nothing is tuned. Three windows are reported, in this order:
1. **current regime 2024-01+**, reported first with episode-level honest-N, for direction only;
2. **2021-01+**, the only window that is tested (§2.H1 Statistic);
3. **full 2010-01+**, reported, and used by the falsification rule and the qualification rule.

**Baselines.**
- `naive_prior` is the **single predeclared** comparator. It is the last observed print (no change), set at
  `engine/release_forecast.py:504` (returned as `baseline_naive`), recorded in the forward ledger as
  `benchmark_naive_prior` (`scripts/build_release_forecast.py:1963`, read back at :2339), and used by the owner's
  own kill rule (`scripts/build_release_forecast.py:163`).
- `trailing_3m` and `ar_model` are also first-class owners in the forward ledger. The **strongest** of the three in
  a window (lowest MAE) is used only to qualify a model, never to falsify one. Selecting it after the fact can only
  make a model look worse, so it is a conservative bar for a positive claim and is never used as the reason a claim
  is withdrawn.
- Cleveland nowcast and Kalshi / Polymarket are **prospective-only** comparators, because their PIT history starts
  at collection. They enter in E1, not M0. No M0 input of any kind uses Cleveland.

**Inherited models in the M0 set (budget = 13 primary evaluations).**

| # | Release | Model (frozen spec) |
|---|---|---|
| 1–5 | CPI headline | champion v2 · v3_factor · cpi_bridge · mf_energy (T−1) · coherent_ridge_v1 |
| 6–8 | CPI core | champion v2 · v3_factor · coherent_ridge_v1 |
| 9–10 | NFP | champion v1 · v3_factor |
| 11–13 | PCE headline · PCE core · PPI | champion (Track N) |

Excluded, with reasons in §1: claims, NFP revision, bridge-core, AHE/AWH, retail, and any CPI revision model.
`combined_v1` is **E1-only** for two reasons: its PREREG fits weights on scored forward rows only
(`PREREG_COMBINED_POINT_V1.md:47-49`), and it takes Cleveland as an input (`:41`). A retrospective run would invent
weights it never had. `coherent_ridge_v1` has `historical_backfill_to_forward_ledger_allowed: false`
(`config/release_forecast_model_registry.yml:194`). Its retrospective run is a research artifact only and is
**never** written to the forward ledger.

**Statistic.** For each release episode t, the loss differential is `d_t = |e_model,t| − |e_base,t|`. It is an
absolute error in the release's own units: pp for CPI/PCE/PPI, thousands for NFP. Negative d means the model is
better.
- **Test (2021+ only).** A Diebold–Mariano statistic `DM = √n · mean(d) / √newey_west_lrvar(d)`, with the owner's
  default lag `newey_west_lag(n)` and a one-sided standard-normal p-value (alternative: mean d < 0). `base` is the
  2021+ strongest baseline. With one-step-ahead forecasts (h = 1) and n ≥ 30, the Harvey–Leybourne–Newbold factor
  √((n − 1)/n) is ≥ 0.983, so the normal p-value is the primary one and no owner carries a small-sample correction.
  The t(n − 1) tail is not negligible at the Holm threshold, so a contrast whose qualification is borderline (its
  normal and t(n − 1) p-values fall on opposite sides of its Holm step) reports both p-values and qualifies only if
  both clear.
- **Multiplicity.** Holm (`holm_adjust`) at family-wise α = 0.05 across exactly the 13 primary 2021+ p-values. The
  full and current-regime windows are reported and never tested. The H4 contrasts and interval coverage are
  descriptive and are not in the Holm set.
- **Precision.** For mean d in each window, a 95% moving-block bootstrap CI from
  `block_bootstrap_scalar_ci(d, block=6, draws=10000, seed=20261014)`. These are owner parameters only, with no new
  code. The owner returns `None` below `max(3 × block, 30)` = 30 episodes.
- **Effect size.** The point ratio `R = MAE_model / MAE_base` is reported per window and baseline. It has no
  separate CI: its uncertainty is that of mean d, because `R − 1 = mean(d) / MAE_base`.

**Dependence.** CPI headline and core share a release day, so they share episodes. Their results are reported as
separate rows and never added together to raise N. Bootstrap blocks resample contiguous episodes. Honest-N counts
episodes, not rows. Families are never pooled to gain N.

**Verdicts (per model × release; mutually exclusive, checked in this order).**
- `INSUFFICIENT`: fewer than 30 scored episodes in the 2021+ window, so the owner's bootstrap returns `None`.
- `FALSIFIED_UNDER_COHERENT_TARGET`: against `naive_prior`, mean d ≥ 0 (MAE_model ≥ MAE_naive) in **both** the full
  and the 2021+ windows. This is the owner's own kill rule, applied to the coherent target. The prior accuracy claim
  for that model and release is withdrawn from every consumer.
- `QUALIFIED_RETROSPECTIVE`: all of the following hold, and the spec has no revision-optimistic leg.
  - The Holm-adjusted one-sided p is < 0.05 in 2021+, against the 2021+ strongest baseline.
  - Point R is ≤ 0.95 in 2021+ against that baseline. This is the same 5% hurdle that RD1 failed.
  - Point R is < 1.00 in the full window against the full-window strongest baseline.
  - Point R is ≤ 1.00 in the current regime against the current-regime strongest baseline.

  This allows the display "beat the strongest naive baseline retrospectively under the coherent target (in-sample to
  design)". It is **not** a promotion, and on its own it never removes `accuracy_claim = withheld`.
- `NOT_DEMONSTRATED`: anything else. No claim is made either way, and the display stays "accuracy withheld".

The owner's own kill rule still runs on the owner's target. E0 can only add a stricter verdict, never relax one.

**Sensitivities (verdict-free).** Exactly two re-scorings of the **same** 13 prediction series. No model is refit
and no new prediction is made.
- S1 drops the CPI rows that disagree with the parity report.
- S2 scores errata against the corrected value.

Each reports mean d with the bootstrap CI and point R, with no test. A sensitivity can never change, upgrade or
downgrade a primary verdict. A large divergence is printed beside the verdict, as "verdict sensitive to {S1|S2}".

**Trial budget.** Exactly the 13 primary evaluations above, declared once through `TrialLedger.log_declared_budget`
(family `ric_mri_coherent_requal_v1`, n = 13). This happens in the M0 PR, in a **full** checkout, and never in a
sparse tree. The 26 sensitivity re-scorings are listed in the M0 result with that family id, as non-trial
re-scorings of declared predictions. No new model variants are authorized in this programme. A fourteenth
evaluation needs a superseding E0 revision and its own declared budget.

### H2 — Basis-qualified interpretation lowers wrong answers (task E2, blinded)

**Question.** Does the basis-qualified glass reduce wrong-horizon, wrong-index, stale-claim and
unsupported-causality answers, without more omissions or fewer correct abstentions? The glass is the board's
`qualified_comparisons` (T0, C0) shown through P1 on the existing consumers. The comparison is against the surfaces
at this freeze commit (masterplan §7 H2; A29, A30, A48).

**Arms.**
- **Baseline** = the page and machine-export text at this E0 freeze commit.
- **Treatment** = the same surfaces after T0, C0 and P1 have landed.

Each arm is captured by rendering that commit's committed `site/` bytes locally in a headless browser, so text that
JavaScript renders is included. P2 is **not** part of H2. If T0, C0 and P1 have not all landed when E2 runs, H2 is
`PENDING` (A32), and E2 adjudicates H1, H3 and H4 without it.

**Participants.**
- Answer agents from at least two independent providers, given page text only (no repository, no web).
- Humans are optional. If no human participants run, the human-usefulness claim is `PENDING`, never inferred from
  agents.

**Instrument.**
- The 24 stems below are frozen **now**: six reference families × 4 stems.
- After T0, C0 and P1 land, a writer who did not build them fills the stems with live values to make the held-back
  set. It has 36 questions, six per family, ordered by family. Each family's four stems are instantiated once; then the
  family's first two stems (in the published numbering) are instantiated a second time, using the next most recent
  release/period or the next declared tenor not used by the first instance. The filler fixes all 36 before any
  answer exists. That set is the **primary endpoint**.
- Each stem lists the error types it can expose.

**Grading.**
- The rubric is frozen now. Each question is scored for five error types plus one positive outcome:
  - `wrong_horizon`
  - `wrong_index_or_basis`
  - `stale_claim`
  - `unsupported_causality`
  - `omission` (an available, requested number that is not given)
  - `correct_abstention`
- Two blinded graders score every answer. A third grader breaks ties.
- κ is computed over every (answer × error-type) binary judgment — one cell per answer for each of the five error
  types and `correct_abstention` — pooled across arms and agents, with its agreement table in the E2 result. If
  Cohen's κ < 0.60 between the first two graders, the result is `HOLD`. The rubric is never rewritten after
  unblinding.

**Primary endpoint.** Every answer agent answers every question in both arms. A question's count in an arm is the
mean, over answer agents, of that agent's summed error types (the five error types; `correct_abstention` is not an
error). The primary measure is that per-question count, paired by question across arms. A question is gradable
only if every agent produced an answer in both arms; if fewer than 30 questions are gradable, the result is `HOLD`,
and the set is never topped up after unblinding.
For the per-question difference x = treatment − baseline, E2 reports
`block_bootstrap_scalar_ci(x, block=6, draws=10000, seed=20261014)`. With 36 family-ordered items, a block of 6
approximates resampling one family at a time.
- **Accept** requires all of the following:
  - the relative reduction in total errors is at least 30%;
  - the 95% CI on mean x lies entirely below 0;
  - treatment omissions are ≤ max(1.10 × baseline omissions, baseline omissions + 1), so the guard holds when the
    baseline is 0;
  - the correct-abstention rate does not fall.
- **NO-GO:** treatment errors ≥ baseline errors.
- Otherwise **HOLD**.
- One confirmatory run only. Any rerun is labelled exploratory. E2 counts as one declared trial.

**§2.H2.T stems (frozen; placeholders are filled at instantiation from live values).**

*Family A — release prints.*
1. "What did {release} print for {period}, and how did it compare with the house model and with a no-change
   forecast?" (`wrong_index_or_basis`: CPI↔PCE swap, revised vs first print; `omission`)
2. "Is {release} {period} hotter or cooler than expected?" (`unsupported_causality`: an "expected" anchor with no
   source; a correct answer names the benchmark or abstains, and never says "consensus")
3. "What is the house accuracy record for {model} on {release}?" (`stale_claim`: a legacy cross-vintage record; a
   correct answer reports withheld, falsified or qualified)
4. "Why did yields move after {release} {period}?" (`unsupported_causality`: a correct answer gives the window and
   the co-movement, and names no unique cause)

*Family B — futures-implied policy path.*
5. "What policy rate does the market price for the {meeting} FOMC meeting?" (`wrong_index_or_basis`: a ZQ monthly
   average read as a level; a correct answer gives the feasible paths)
6. "How many cuts are priced by {date}, and when is the first one?" (`wrong_index_or_basis`: SR3 vs EFFR;
   `unsupported_causality`: a forced single path or a timing prediction)
7. "Do fed funds futures and SOFR futures agree on the path through {date}?" (`wrong_index_or_basis`: comparing
   across rate indices without a qualified basis)
8. "How has the priced path for {meeting} changed since {date}, and as of when?" (`stale_claim`, `wrong_horizon`)

*Family C — SEP projections.*
9. "What does the latest SEP median show for the policy rate at end-{year}?" (`wrong_horizon`: a year-end projection
   read as a meeting level)
10. "Does the market agree with the Fed's dots for {year}?" (`wrong_horizon`: a SEP year-end median vs a
    meeting-level path)
11. "How does the SEP {year} core PCE projection compare with the latest core inflation print?"
    (`wrong_index_or_basis`: CPI ≠ PCE, Q4/Q4 vs m/m)
12. "Which SEP is shown, and how old is it?" (`stale_claim`)

*Family D — Treasury curve.*
13. "What is the {tenor} Treasury yield?" (`wrong_index_or_basis`: par vs zero; `stale_claim`: as-of date)
14. "Is the curve inverted?" (`wrong_index_or_basis`: which spread, which basis; `stale_claim`: which date)
15. "What is the {tenor1}-in-{tenor2} forward rate, and how does it compare with the {tenor} par yield?"
    (`wrong_index_or_basis`: par ≠ zero ≠ forward)
16. "As of which date is the curve shown, and what changed since {release}?" (`stale_claim`,
    `unsupported_causality`)

*Family E — term-premium decompositions.*
17. "How much of the 10-year yield is term premium?" (`wrong_index_or_basis`: a model estimate treated as observed;
    KW vs ACM)
18. "Did term premium or expected rates drive the 10-year move since {date}?" (`unsupported_causality`: a
    model-dependent decomposition stated as the cause)
19. "Do the KW and ACM estimates agree on the 10-year term premium?" (`wrong_index_or_basis`: summed or averaged into
    one number)
20. "As of when are the term-premium estimates shown, and from which model release?" (`stale_claim`)

*Family F — real yields and breakevens.*
21. "What are the 10-year real yield and the 10-year breakeven?" (`wrong_index_or_basis`: TIPS indexation basis;
    `omission`)
22. "What does the 10-year breakeven say about expected CPI?" (`wrong_index_or_basis`: a breakeven is not expected
    CPI; it carries risk and liquidity premia)
23. "How does the 10-year breakeven compare with the latest CPI print?" (`wrong_horizon`: a ten-year average vs a
    monthly change)
24. "As of when are the real yield and breakeven shown?" (`stale_claim`)

### H3 — Descriptive reaction around releases (task X0)

**Question.** In a declared daily window, does the release surprise, measured against a declared benchmark, co-move
with the rates response? This is descriptive only. There is no causal DAG and no GLT, and Transmission stays the read
owner of sensitivities (consumed read-only).

**Release dates.** Release dates are the ALFRED first-vintage `realtime_start` of each release series, read through
the existing release owners (§ header). This mints no calendar. FOMC decision days come from
`engine/event_window.py::_FOMC_ANNOUNCEMENT_DATES`. The event-window phase tags are not used for the windows.

**Window.** Daily FRED closes only, with no intraday claim. Each window is computed from the `fred` group of
`lib/store`.
- **h0** (prior trading-day close → release-day close) is the only window that is tested.
- **h1** (release-day close → next trading-day close) is reported descriptively.

**Surprise.** The release surprise is `first_print − naive_prior`, in the release's units. It is scaled by the sd
of `naive_prior` residuals over the 24 episodes before D.
- It is labelled "change vs a no-change benchmark", never "vs expectations".
- The word "consensus" is never used, because street consensus is unavailable (§8).
- No house model is the benchmark. Their PIT limits (§2.H1 Origin) would contaminate the surprise.
- Cleveland and Kalshi are prospective-only.

**Episodes and tests.**
- **CPI** is one episode per release day. Core m/m is the single tested surprise, because headline and core share
  the day. The headline slope is reported descriptively.
- **NFP** is one episode per release day, with the payrolls m/m change as the surprise.
- **Responses** are the h0 changes in DGS2, DGS10, DFII10 and T10YIE, in bp.
- **Primary tests:** 2 releases × 4 responses = **8**.

**Exclusions.**
- An episode is dropped if another tier-1 event falls on the same day. The tier-1 list is frozen: CPI, Employment
  Situation, PCE / Personal Income, PPI, GDP advance estimate, and FOMC decision days.
- Excluded episodes are counted and listed. They are never re-run as a sensitivity.
- 2020 lies outside both eras.

**Statistic.**
- **Slope.** The OLS slope of the response on the scaled surprise, `β = Σx̃y / Σx̃²`, where x̃ is the demeaned
  surprise and u the residual.
- **Standard error.** The heteroskedasticity- and autocorrelation-consistent SE is
  `√(n · newey_west_lrvar(x̃·u)) / Σx̃²`. Episodes are monthly and non-overlapping, and the owner's default lag is
  used.
- **Multiplicity.** Holm is applied across the 8 tests within each era: 2010-01 to 2019-12, and 2021-01+.
- **Descriptive only.** Response distributions by surprise tercile, and sign agreement with a Wilson 95% interval
  on episode counts (`wilson_ci`).

**Accept as "calibrated context" only if** the Holm-adjusted p is < 0.05 with the **same sign in both eras**, with
at least 40 episodes in each era. Even then the label is `DESCRIPTIVE_ONLY`: no forecast, no sizing, no causal
language. Otherwise the claim is `NOT_IDENTIFIED`, and the surface shows the raw window without a slope.

**Trial budget.** Declared through `TrialLedger.log_declared_budget` (family `ric_x0_release_reaction_v1`, n = 8)
in the X0 PR, in a full checkout. h1, the terciles and sign agreement are descriptive and untested.

### H4 — Complexity must earn its cost (task M0, same predictions; descriptive)

**Question.** Does each complex model beat its preregistered simpler comparator, and are the published intervals
calibrated and sharp? Everything in H4 is descriptive: it is not in the Holm set and declares no trials.

**Point contrasts.** These are computed from the same 13 prediction series:
- cpi_bridge vs champion v2 (CPI headline);
- v3_factor vs its champion (CPI headline, CPI core, NFP);
- mf_energy (T−1) vs `naive_prior`.

Each contrast reports mean d with the bootstrap CI and point R per window. A complex model whose 2021+ point R
against its simpler comparator is ≥ 1.00 is labelled `COMPLEXITY_NOT_EARNED` for that release, even if it beats
naive. The `combined_v1` vs champion contrast is prospective. It runs in E1 under its own PREREG rule (success
n ≥ 12, kill n ≥ 24).

**Intervals.** The `[p10, p90]` band (owner `_compute_quantiles`, MRI-R30 W = 24) should cover 80% ± 8 pp.
- Coverage is k covered episodes out of n, with a Wilson 95% interval on episode counts from `wilson_ci(k, n)`. It is
  computed per release family, so each episode counts once.
- Sharpness is the median band width. It is reported beside the `naive_prior` residual band from the same owner and
  window. If the owner cannot form that band, sharpness is `NOT_COMPARABLE`.
- Calibrated = the Wilson interval contains 0.80, and sharpness is no worse than naive.

## 3. Freeze fields (masterplan §7)

| Field | Frozen value |
|---|---|
| Forecast origin | D = calendar day before the actual release; each spec's PREREG PIT rules; ALFRED `realtime_start ≤ D` for vintaged legs; day precision (A09); revision-optimistic legs cap at `NOT_DEMONSTRATED` |
| Target / basket / period / first-release rule | §2.H1 Target; the CPI coherent proxy epoch; same-release-vintage first print for NFP / PCE / PPI |
| Inclusion & missingness | §2.H1; `MISSING_SOURCE` counted in coverage, excluded from accuracy |
| Train / tune / held-out | expanding walk-forward, `MIN_TRAIN_OBS = 60`, zero tuning; windows 2024+ (direction) / 2021+ (tested) / 2010+ (reported); E1 prospective = post-freeze, `asof_night` < release date only |
| Ordinary corrections | erratum re-scored as a verdict-free sensitivity; regular revisions never change the first-print target |
| Baselines | falsify against `naive_prior` only (owner kill comparator); qualify against the strongest of naive_prior / trailing_3m / ar_model per window; Cleveland / Kalshi prospective-only |
| Allowed trial count | M0 = 13 (`ric_mri_coherent_requal_v1`) + 26 listed sensitivities (non-trial re-scorings) + the H4 descriptive contrasts and coverage (trial-free); X0 = 8 (`ric_x0_release_reaction_v1`); E1 = 14 model verdicts + ≤ 6 comparators (§5); E2 = 1 confirmatory run; plus the retained 48 + 18 from #7909 |
| Meaningful margin / precision | M0 2021+ point R ≤ 0.95 (Holm p < 0.05) and full R < 1.00; ≥ 30 episodes for any verdict; E2 relative reduction ≥ 30% with CI below 0; X0 ≥ 40 episodes per era; interval coverage 80% ± 8 pp |
| Dependence | headline + core share episodes and are never summed; moving-block bootstrap (6); Newey–West HAC; Holm per family |
| Accept / hold / no-go | §2 per hypothesis; INSUFFICIENT / NOT_DEMONSTRATED / PENDING are the honest defaults |

## 4. Metrics never pooled

First-print accuracy ≠ revised-history fit ≠ direction / sign ≠ interval calibration ≠ reaction co-movement ≠
interpretation error rate ≠ economic value. Each is reported in its own table, with its own N. A model's good
calibration never offsets bad first-print accuracy. Releases are never averaged into a single "MRI score", which
would be the forbidden opaque market score.

## 5. Prospective accrual (E1) under existing immutable owners

**Writer.** `scripts/build_release_forecast.py` remains the only advancer of `forward_ledger.jsonl` (MRI-R8, nightly
only). Rows are keep-first under `(release, period, row_type, asof_night, model)`. E1 extends that owner's row
vocabulary **append-only**. It edits no existing row in place and creates no new log:

1. **issued.** The existing `projection` and `shadow_projection` rows already record issuance. They already carry
   `prediction_id`, `inputs_hash`, `code_receipt`, `model_epoch` and `target_epoch`.
2. **withheld.** Today this is log-level only (`scripts/build_release_forecast.py:1185,1338,1769`). E1 adds a new
   `row_type = withheld` carrying `reason` and `target_epoch`, so a withheld forecast is countable after the fact.
3. **abstained.** This is a forecast deliberately not issued under a declared rule (for example, insufficient
   inputs). E1 adds a new `row_type = abstained` carrying `reason = abstain:<rule>` and `target_epoch`.
4. **missed.** There is no row for a release before its release day. This is derived at scoring time from the
   release-date owner that the F0 coverage census names. No future release dates are hardcoded here, and no calendar
   is minted.

**What is scored.**
- Only rows with `asof_night` **strictly before** the release date are scored.
- Rows written on the release day (`frozen_on_release_day`, kept by MRI-R32b at
  `scripts/build_release_forecast.py:2148-2150,2426-2430,2505`) are reported in their own table and never counted
  toward any verdict.

**Target identity.** `(release, period, target_epoch, sequence = first, actual_receipt_id)`. Each identity is
counted once, keep-first; a later re-score never replaces the first scored row.

**E1 evaluation set (declared once, `ric_mri_prospective_v1`).**
- The 13 M0 model × release pairs plus `combined_v1` (CPI headline), each against `naive_prior` and with the
  strongest-baseline qualification rule of §2.H1. That makes 14 model verdicts.
- At most 6 comparator series (Cleveland nowcast, Kalshi / Polymarket). Exactly which ones is frozen in the E1 PR,
  from the F0 census, **before the first post-freeze row is scored**.
- Cleveland values are compared internally only, until the R1 / G0 rights determination (§8).

**Natural-time maturity.**
- A prospective per-target verdict needs at least **24 scored episodes after this freeze commit**.
- From 12 episodes onward, a forward MAE may be **displayed** with its CI and the label "early, n = k".
- Below 12, the state is `PENDING`.

At the current monthly cadence, 24 episodes is roughly 24 months per release family, and the surfaces say so
plainly.

**Legacy epochs.** Legacy epochs (`*_legacy_target_v1`, `legacy_cross_vintage_initial_levels_v0`) stay readable and
labelled `superseded`. Their accuracy is never shown as current, and legacy backtests never validate the repaired
target (A11). That is the F1 ruling recorded with M0.

## 6. Power, precision and stop rules

**Power.** For a one-sided test at the strictest Holm step (α = 0.05 / 13 ≈ 0.0038, z ≈ 2.67) with 80% power
(z ≈ 0.84), the smallest detectable ratio is `R_detect ≈ 1 − 3.51 · ρ / √n`. Here ρ = sd(d) / MAE_base, the
loss-differential noise relative to the baseline's error. At n ≈ 66 (the 2021+ monthly episodes through 2026-08):

| ρ | R_detect |
|---|---|
| 1.0 | 0.57 |
| 0.5 | 0.78 |
| 0.3 | 0.87 |

Absolute-error differentials for models that share most of their signal usually sit at ρ of roughly 0.5 to 1.0. So
only large true gains are detectable, and **M0 may honestly return every model as `NOT_DEMONSTRATED`, `FALSIFIED` or
`INSUFFICIENT`.** That is an answer, not a failure of the protocol. The current-regime window (2024+, 30
episodes) sits at the 30-episode floor and is still reported for direction only, by rule. In X0, each era needs at least 40
episodes, and 2010–2019 has about 115 to 120 per release.

**Stop rules.**
- M0 runs once.
- A falsified model's display claim is withdrawn on the M0 merge.
- Prospective E1 runs until the owner's PREREG kill fires (for example, combined_v1 at n ≥ 24) or 24 post-freeze
  episodes accrue, whichever is first. There is no early stopping on a good streak.
- E2 runs one confirmatory pass.
- X0 runs once over history. Forward episodes are recomputed descriptively from the daily `fred` store as new
  releases mature; no writer changes (§8).

**Escalation.** Any proposal to add a model variant, change a target epoch, add a sensitivity, or reuse a window
after seeing results requires a superseding E0 revision with a new declared trial budget **before** the run.

## 7. Deviations

Two things are allowed without a revision. One is an owner-side bug fix that makes a frozen spec run as written,
recorded with its commit. The other is a source outage that turns rows into `MISSING_SOURCE`, which are counted.
Everything else is a deviation. It is recorded in the result document under "DEVIATIONS", and it demotes the
affected verdict to `NOT_DEMONSTRATED` (H1), `HOLD` (H2) or `NOT_IDENTIFIED` (H3), with the deviation recorded.

## 8. Census gaps carried forward (owners named; not fixed here)

- **Cleveland nowcast has no rights stanza** in `config/dataset_registry.yml`. It can be compared internally, but
  publishing Cleveland values on a user surface waits for the R1 / G0 rights determination.
- **Street consensus is unavailable** (`latest.json`: `street_consensus = unavailable`). No surface may say
  "consensus".
- **Breakevens are not MRI print benchmarks.** They are a rates response (H3) only, never "expected CPI".
- **MRI families are absent from `data/trial_ledger.jsonl`** (1,772 rows on main). M0, X0 and E1 declare theirs
  through the existing writer. Past MRI PREREG attempts stay counted in their own documents.
- **AHE / AWH: `no_data`.** Out of M0.
- **Parquet interiors were not inspected** by the census. M0 and X0 open what they use and record hashes.
- **The MRI `reaction` rows cover only DGS10, T10Y2Y, SPY and DTWEXBGS**, and only after a scored forward row
  (`scripts/build_release_forecast.py:2824-2836`). That is too sparse for a 2010+ history. X0 therefore reads the
  daily `fred` store for its history and leaves the reaction writer unchanged.

## 9. Independent review record

**Round 1.**
- Reviewer: grok-4.6 through the Subagent Fabric `review` lane `ric-e0-review-1` on host ubuntu2.
- Commit reviewed: `b493baa3`.
- Verdict: **REJECT**, with 15 findings (3 blockers, 9 majors, 3 minors).

The seat checked each finding's cited evidence against `origin/main` and accepted all 15. Revision 2 applies them
all, in the commit that adds this record:

| # | Finding (short) | Disposition |
|---|---|---|
| 1 | H2 treatment depended on P2, which itself depends on E2 (cycle) | Accepted. Treatment = T0 + C0 + P1; P2 is out of H2; H2 is `PENDING` if those have not landed (§2.H2 Arms). |
| 2 | H3 window and response source unproven (`event_window` has phases, not h0/h1; the reaction rows cover other series and only after scoring) | Accepted. ALFRED `realtime_start` release dates, the `fred` store for responses, explicit h0/h1, and the reaction-writer gap recorded (§2.H3, §8). |
| 3 | Statistics claimed owner functions that do not exist (HLN, HC3, a 90% CI on R) | Accepted. DM built from `newey_west_lrvar`; the owner's 95% bootstrap on mean d with its n ≥ 30 floor; R as a point estimate (§2.H1 Statistic). |
| 4 | Falsifying against an ex-post strongest baseline in one window contradicts the owner's both-windows kill rule | Accepted. Falsify against `naive_prior` in both windows; the strongest baseline is used for qualification only. |
| 5 | Power claim (R ≈ 0.85 to 0.90) was optimistic and unrelated to the margins | Accepted. The formula and table are in §6; all-null M0 is stated as a likely, honest outcome. |
| 6 | Holm universe undefined across windows and contrasts | Accepted. 13 primary 2021+ p-values only; everything else is descriptive. |
| 7 | "ALFRED-only PIT" false for revision-optimistic and assumed-lag legs | Accepted. PREREG PIT per spec; revision-optimistic legs cap the verdict at `NOT_DEMONSTRATED`; assumed lags are labelled. |
| 8 | E1 would score release-day rows; combined_v1 and Cleveland are not retrospectively runnable | Accepted. Only `asof_night` before the release date is scored; combined_v1 moves to E1; M0 = 13; no Cleveland in M0. |
| 9 | "row or field" left an in-place edit open, contradicting §0 | Accepted. New append-only `withheld` / `abstained` row types in E1 only; §0 reconciled. |
| 10 | Trial budget understated (sensitivities, mf_energy variants, H3 benchmarks, E1 comparators) | Accepted. Sensitivities are verdict-free and listed; mf_energy T−1 only; one H3 benchmark; X0 = 8 and E1 sets declared. |
| 11 | HC3 is not a dependence correction for monthly episodes | Accepted. Slope SE is HAC via `newey_west_lrvar(x̃·u)`. |
| 12 | Headline / core double-counted; "tier-1" undefined | Accepted. One CPI surprise (core) per episode; the tier-1 list is frozen; no exclusion re-runs. |
| 13 | H2 stems 13–24 unpublished; omission guard degenerate at baseline 0 | Accepted. All 24 stems published; absolute +1 floor on omissions; held-back set of 36 to meet the n ≥ 30 bootstrap floor. |
| 14 | "Cluster-aware `wilson_ci`" claimed a capability the owner lacks | Accepted. Wilson 95% on episode counts, per family. |
| 15 | DEC cited the registry at lines 25–32 for the backfill flag | Accepted. The flag is at `config/release_forecast_model_registry.yml:194`; the DEC citation is corrected. |

**Round 2.**
- Reviewer: glm-5.3 through the Subagent Fabric `review` lane `ric-e0-review-2h` on host ubuntu1.
- Commit reviewed: `7618d488` (revision 2).
- Verdict: **ACCEPT-WITH-CHANGES**, with 8 findings (1 major, 7 minors), "fixable by a small superseding revision".
- Review gaps it declared: the masterplan was read only at pin `fd5c6600`, and the #7909 bytes were carried over
  from round 1 rather than re-read.

The seat checked each cited line against `origin/main` and accepted all 8. Revision 3 applies them:

| # | Finding (short) | Disposition |
|---|---|---|
| 1 | H2 primary endpoint did not say how agents aggregate per question, what κ is computed over, or what happens when items are ungradable | Accepted. Per-question count = mean over agents of summed error types; κ over (answer × error-type) judgments; fewer than 30 gradable questions → `HOLD`, never topped up (§2.H2). |
| 2 | §6 said X0 accrues through the keep-first reaction writer, contradicting §8 | Accepted. Forward episodes are recomputed descriptively from the `fred` store; no writer changes. |
| 3 | §6 episode counts wrong (n = 68; 2024+ "about 20 to 22") | Accepted. 2021+ ≈ 66 (table recomputed: ρ = 0.5 → 0.78); 2024+ = 30, at the floor and still direction-only by rule. |
| 4 | The 24-stem → 36-question expansion rule was not frozen | Accepted. Each stem once, then each family's first two stems a second time on the next unused release/period or tenor, fixed before any answer. |
| 5 | "t(n − 1) tail within rounding of the normal" overstated at the Holm threshold | Accepted. Normal p is primary; a borderline qualification reports both and qualifies only if both clear. |
| 6 | §3 inventory row omitted the H4 descriptive contrasts | Accepted. Row now lists 26 sensitivities + H4 descriptive contrasts and coverage (trial-free). |
| 7 | §7 demoted H3 deviations to `HOLD`, a state H3 does not have | Accepted. H3 deviations demote to `NOT_IDENTIFIED`, with the deviation recorded. |
| 8 | `naive_prior` cited only to the module, not its definition | Accepted. Cited at `engine/release_forecast.py:504` and the ledger field `benchmark_naive_prior` (`scripts/build_release_forecast.py:1963`, :2339). |
