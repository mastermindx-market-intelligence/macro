# E0 — Frozen research and outcome protocol (Rates & Inflation Command, e2e 2026-10-13)

Status: **FROZEN** on merge of the PR that adds this file (seat `fc3dfe4b`, task-graph row E0). Census basis:
read-only E0 census of `origin/main` @ `1e9364f5ab8c4452820731e87da2c138e53b0571` (verdict PASS-WITH-GAPS, gaps in §8).
Independent review: §9. Acceptance rows served: **A28** (finite trials) directly; inputs to M0 (A11, A28, A30),
E1 (A09, A31, A32), X0 (A29), E2 (A29, A30, A32, A48). Masterplan pin:
`research/rates_inflation_command/e2e_20261013/MASTERPLAN.md` @ `fd5c6600` §7, §8, §13.

**Owners reused, nothing new minted.** Trial counting = `engine/trial_ledger.py` (`TrialLedger.log_declared_budget`,
`data/trial_ledger.jsonl`). Frozen model specs = `research/release_forecast/PREREG_*.md`. Prospective record and the
only advancer = `scripts/build_release_forecast.py` → `data/release_forecast/forward_ledger.jsonl` (MRI-R8).
Reaction windows = `engine/event_window.py` + `scripts/build_event_windows.py` → `data/event_windows/forward_log.jsonl`
and the MRI `reaction` rows. Statistics = existing primitives only: `engine/grading_stats.py`
(`block_bootstrap_scalar_ci`, `wilson_ci`, `effective_n`), `engine/challenger_spa_comparison.py`
(`newey_west_lag`, `newey_west_lrvar`), `engine/desk_placebo.py` (`holm_adjust`). The corrections owner is
`data/release_forecast/{defect_notices.json,official_actual_defects.json}`. The CPI coherent target is
`data/release_forecast/cpi_truth/alfred_same_release_vintage_proxy_v1.json` (parity in `cpi_truth/parity_report.json`).
No evaluator, scorecard, trial plane, Research Factory, queue, calendar or publication surface is created here.

## 0. What this protocol is and is not

- It freezes finite questions **before** any new outcome work (masterplan §7). Each later task (M0, E1, X0, E2)
  executes exactly what is frozen here, or records a deviation that this document's §7 rule allows.
- **E0 only tightens claims.** It never overrides an owner's existing kill rule, never reactivates a killed or
  `benchmark_only` family, and never changes a producer's live behaviour.
- **Retrospective evidence can falsify or qualify; it cannot promote.** A coherent-target walk-forward over history
  was designed with that history visible (the PREREG files were frozen in 2026-07 after looking at 2010+ data). It is
  therefore in-sample to the design period. Only forecasts issued **after this protocol's freeze commit** and scored
  against their first print under the owner's immutable record are promotion-capable (§5).
- Natural time governs. A forecast cannot be graded before its release. Underpowered evidence stays `INSUFFICIENT`
  or `PENDING`, never "trending" or "promising".
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

### H1 — First-print models vs the strongest baseline on the same origin and target (task M0, then E1)

**Question.** Under a coherent first-print target, does each inherited MRI model beat the strongest naive baseline
for the same release, period, origin and target? A gain that disappears under coherent vintages falsifies the old
accuracy claim (masterplan §7 H1; acceptance A11, A30).

**Target (per family, never pooled).**
- CPI headline / core m/m: `alfred_same_release_vintage_proxy_v1.published_proxy_1dp` (the registry's coherent
  epoch; `official_first_print_epoch` stays `withheld`). Rows whose proxy disagrees with `parity_report.json` are
  reported as a sensitivity with and without them.
- NFP m/m change, PCE headline / core m/m, PPI final demand m/m: the same-release ALFRED vintage first print
  (`realtime_start` = the release day), never a later revised value.
- First-print target and revised-history fit are separate metric families and are never pooled (§4).

**Origin.** D = the calendar day before the actual release. Features are point-in-time: only observations with
ALFRED `realtime_start ≤ D`. ALFRED is day-precision, so "before the release" means "before the release day"; the
A09 label is `day_precision_origin` and no intraday ordering is claimed.

**Inclusion and missingness.** A period whose first print never appeared (shutdown-cancelled) is `MISSING_SOURCE`.
It is excluded from accuracy and counted in coverage. A delayed release keeps D = the day before the actual release
and carries the owner's quirk flag (`quirk_calendars/government_shutdowns.yml`, `hurricane_landfalls.yml`,
`nfp_preliminary_benchmarks.yml`). Each excluded row is listed by (release, period, reason).

**Ordinary corrections.** An agency erratum within the same release cycle is scored both ways, original and
corrected, as a sensitivity owned by `defect_notices.json` / `official_actual_defects.json`. Ordinary later revisions
never change the first-print target.

**Splits.** Expanding-window walk-forward, first prediction after `MIN_TRAIN_OBS = 60` (owner default,
`engine/release_forecast.py`), refit every origin, with **zero tuning**: every spec runs at its PREREG commit.
There is no held-out tuning split because nothing is tuned. Windows reported, in this order:
1. **current regime 2024-01+**, reported first with episode-level honest-N;
2. **2021-01+**;
3. **full 2010-01+**.

**Baselines.** `naive_prior`, `trailing_3m` and `ar_model` (first-class owners in the forward ledger). For each
window, the comparator is the **strongest** of the three in that window. Choosing the best baseline after the fact
is deliberately conservative: it can only make a model look worse. Cleveland nowcast and Kalshi / Polymarket are
**prospective-only** comparators (their PIT history starts at collection), so they enter in E1, not in M0.

**Inherited models in the M0 set (budget ≤ 15 frozen-spec evaluations).**

| # | Release | Model (frozen spec) |
|---|---|---|
| 1–6 | CPI headline | champion v2 · v3_factor · cpi_bridge · mf_energy · coherent_ridge_v1 · combined_v1 |
| 7–10 | CPI core | champion v2 · v3_factor · coherent_ridge_v1 · combined_v1 |
| 11–12 | NFP | champion v1 · v3_factor |
| 13–15 | PCE headline · PCE core · PPI | champion (Track N) |

Excluded, with reasons in §1: claims, NFP revision, bridge-core, AHE/AWH, retail, and any CPI revision model.
`coherent_ridge_v1` has `historical_backfill_to_forward_ledger_allowed: false`. Its retrospective run is a research
artifact only and is **never** written to the forward ledger.

**Statistic.** Per release episode, loss differential `d_t = |e_model,t| − |e_base,t|` (absolute error, in the
release's own units: pp for CPI/PCE/PPI, thousands for NFP).
- Diebold–Mariano with the Newey–West long-run variance at lag `⌊4(n/100)^{2/9}⌋` (`newey_west_lrvar`), the
  Harvey–Leybourne–Newbold small-sample correction, and a one-sided test with alternative "model better".
- Holm across the M0 set (`holm_adjust`), family-wise α = 0.05.
- Effect size: MAE ratio `R = MAE_model / MAE_base`, with a 90% moving-block bootstrap CI (block 6 releases,
  10,000 reps, seed `20261014`, `block_bootstrap_scalar_ci`).

**Dependence.** Headline and core from the same release day form one episode cluster. Bootstrap blocks resample
episodes, and cluster-aware counts are reported as honest-N (episodes, not rows). Families are never pooled to
gain N.

**Verdicts (per model × release; mutually exclusive, checked in this order).**
- `INSUFFICIENT`: fewer than 24 episodes in the 2021+ window, OR the 2021+ R CI width exceeds 0.30.
- `FALSIFIED_UNDER_COHERENT_TARGET`: 2021+ `R ≥ 1.00` (no better than the strongest baseline). The prior accuracy
  claim for that model and release is withdrawn from every consumer.
- `QUALIFIED_RETROSPECTIVE`: Holm-adjusted p < 0.05 in **both** the full and 2021+ windows, `R ≤ 0.90` in both,
  AND current-regime `R ≤ 1.00`. This allows the display "beat the strongest naive baseline retrospectively under
  the coherent target (in-sample to design)". It is **not** a promotion and never removes `accuracy_claim =
  withheld` on its own.
- `HOLD`: anything else. No claim either way, and the display remains "accuracy withheld".

The owner's own kill rule (model MAE ≥ naive MAE in BOTH full and 2021+ → `benchmark_only`) still runs. E0 can
only add a stricter verdict, never relax it.

**Trial budget.** Exactly the 15 evaluations above, declared once through `TrialLedger.log_declared_budget`
(family `ric_mri_coherent_requal_v1`, n = 15) in the M0 PR, in a **full** checkout and never in a sparse tree. No new
model variants are authorized in this programme. A sixteenth evaluation needs a superseding E0 revision and its
own declared budget.

### H2 — Basis-qualified interpretation lowers wrong answers (task E2, blinded)

**Question.** Do the post-P2 surfaces (basis contract `rates_command_basis.v1` on the existing consumers) reduce
wrong-horizon, wrong-index, stale-claim and unsupported-causality answers versus the surfaces at this freeze commit,
without more omissions or fewer correct abstentions? (masterplan §7 H2; A29, A30, A48.)

**Instrument.**
- About 24 question templates are frozen **now** in §2.H2.T, four per reference family: (1) release prints vs house
  model and naive, (2) futures-implied policy path (ZQ / SR3), (3) SEP projections, (4) Treasury curve
  par / zero / forward, (5) term-premium decompositions (KW / ACM), (6) real yields and breakevens.
- A held-back set of about 12 questions is instantiated from the same templates **after** P2 lands, by a writer
  who did not build P2. That set is the **primary endpoint**.

**Arms.** Baseline = page content at this E0 freeze commit. Treatment = page content after P2 is live.
- Participants: answer agents from at least two independent providers, given page text only (no repository, no web).
- Humans are optional. If no human participants run, the human-usefulness claim is `PENDING`, never inferred from
  agents.

**Grading.**
- Two blinded graders, each scoring against a frozen rubric with five error types plus "correct abstention".
- A third grader breaks ties.
- If Cohen's κ < 0.60 between the first two graders, the result is `HOLD` and the rubric is not rewritten
  after unblinding.

**Primary endpoint.** Summed error count per question, paired by question across arms.
- **Accept:** a relative reduction of at least 30%, with the 90% paired-bootstrap CI excluding 0. Omissions must
  not rise by more than 10% relative, and the correct-abstention rate must not fall.
- **NO-GO:** treatment errors ≥ baseline errors.
- Otherwise **HOLD**.
- One confirmatory run only. Any rerun is labelled exploratory.

**§2.H2.T templates (frozen; placeholders are filled at instantiation from live values).**
1. "What did {release} print for {period}, and how did it compare with the house model and with a naive forecast?"
   (traps: consensus wording, CPI↔PCE swap, revised vs first print)
2. "Is {release} {period} hotter or cooler than expected?" (trap: an unsupported "expected" anchor; a correct
   answer names the benchmark or abstains)
3. "What is the house accuracy record for {model} on {release}?" (trap: a stale or legacy accuracy claim; a correct
   answer reports it as withheld or qualified)
4. "Why did yields move after {release}?" (trap: causal attribution; a correct answer is descriptive, gives the
   window, and gives no unique cause)
5. "What policy rate does the market price for the {meeting} FOMC?" (trap: ZQ monthly average vs a level; a correct
   answer gives the feasible paths)
6. "How many cuts are priced by {date}?" (trap: SR3 vs EFFR basis, and a forced single path)
7. "Does the market agree with the Fed's dots for {year}?" (trap: SEP year-end median vs a meeting-level path;
   horizon mismatch)
8. "What is the {tenor} Treasury yield and the {tenor} forward?" (trap: par vs zero vs forward)
9. "How much of the 10-year yield is term premium?" (trap: summing KW and ACM, or treating either as observed)
10. "What is the 10-year real yield and breakeven?" (trap: a TIPS indexation-lag basis; breakeven ≠ expected CPI)
11. "Is the curve inverted?" (trap: which spread, which basis, which date)
12. "When will the Fed cut next?" (trap: a policy-timing prediction; a correct answer abstains or gives conditional
    priced probabilities with basis)
13–24. One "comparison" and one "freshness / vintage" variant of each family above. Each tests whether the answer
    carries as-of date, vintage, model / target and rights qualification.

### H3 — Descriptive reaction around releases (task X0)

**Question.** At a declared daily window, does the release surprise (versus a declared benchmark) co-move with the
rates response? This is descriptive only. There is no causal DAG and no GLT, and Transmission stays the read owner
of sensitivities (consumed read-only).

**Window.** Daily, from the existing `engine/event_window.py` phases.
- **h0** (prior session close → release-day close) is primary.
- **h1** (next session) is descriptive only.
- No intraday data is claimed.

**Surprise.** `actual_first_print − benchmark`, scaled by the benchmark's own prior walk-forward residual sd at D.
- Primary benchmark: the house walk-forward champion, labelled "vs house model".
- Secondary benchmark: the strongest naive baseline.
- Cleveland and Kalshi are prospective-only.
- The word "consensus" is never used. Street consensus is unavailable (§8).

**Responses.** Daily changes in DGS2, DGS10, DFII10 and T10YIE, in bp.
**Releases.** CPI headline, CPI core and NFP are primary. PCE core is secondary.
**Primary tests.** 3 releases × 4 responses = 12.

**Exclusions.** Days with a scheduled FOMC decision, or with a second tier-1 release, are excluded from the primary
sample and included only as a sensitivity.

**Statistic.**
- OLS slope of the response on the scaled surprise, with HC3 standard errors, Holm across the 12 tests.
- Also reported: response distribution by surprise tercile, and sign agreement with a `wilson_ci`.

**Accept as "calibrated context" only if** the slope CI excludes 0 in **both** the 2010–2019 and 2021+ eras, with
at least 40 episodes per era. Even then the label is `DESCRIPTIVE_ONLY`: no forecast, no sizing, no causal language.
Otherwise the claim is `NOT_IDENTIFIED` and the surface shows the raw window without a slope.

### H4 — Complexity must earn its cost (task M0, same evaluations)

**Question.** Does each complex model beat its preregistered simpler comparator, and are the published intervals
calibrated and sharp?

**Point contrasts (taken from the same 15 evaluations; no new trials).**
- combined_v1 vs champion (its own PREREG success / kill rule: success n ≥ 12, kill n ≥ 24);
- cpi_bridge vs champion;
- v3_factor vs champion;
- mf_energy vs the strongest naive.

The H1 statistic and windows apply. A complex model that does not beat its simpler comparator is labelled
`COMPLEXITY_NOT_EARNED` for that release, even if it beats naive.

**Intervals.** The `[p10, p90]` band (owner `_compute_quantiles`, MRI-R30 W = 24) should cover 80% ± 8 pp.
- Coverage is reported with a cluster-aware `wilson_ci` on episodes.
- Sharpness is the median band width relative to the naive interval at the same coverage.
- Calibrated = the coverage CI contains 0.80, and sharpness is no worse than naive.

## 3. Freeze fields (masterplan §7)

| Field | Frozen value |
|---|---|
| Forecast origin | D = calendar day before the actual release; `realtime_start ≤ D`; day precision (A09) |
| Target / basket / period / first-release rule | §2.H1 Target; the CPI coherent proxy epoch; same-release-vintage first print for NFP / PCE / PPI |
| Inclusion & missingness | §2.H1; `MISSING_SOURCE` counted in coverage, excluded from accuracy |
| Train / tune / held-out | expanding walk-forward, `MIN_TRAIN_OBS = 60`, zero tuning; windows current regime 2024+ / 2021+ / 2010+; E1 prospective = post-freeze only |
| Ordinary corrections | erratum scored both ways (sensitivity); regular revisions never change the first-print target |
| Baselines | strongest of naive_prior / trailing_3m / ar_model per window; Cleveland / Kalshi prospective-only |
| Allowed trial count | M0 = 15 (declared `ric_mri_coherent_requal_v1`); X0 = 12 descriptive tests (no model trials); E2 = 1 confirmatory run; plus the retained 48 + 18 from #7909 |
| Meaningful margin / precision | M0 R ≤ 0.90 and CI width ≤ 0.30; E2 relative reduction ≥ 30%; X0 at least 40 episodes per era; interval coverage 80% ± 8 pp |
| Dependence | headline + core = one episode; moving-block bootstrap (6); Newey–West HAC; Holm per family |
| Accept / hold / no-go | §2 per hypothesis; INSUFFICIENT / PENDING are the honest defaults |

## 4. Metrics never pooled

First-print accuracy ≠ revised-history fit ≠ direction / sign ≠ interval calibration ≠ reaction co-movement ≠
interpretation error rate ≠ economic value. Each is reported in its own table, with its own N. A model's good
calibration never offsets bad first-print accuracy. Releases are never averaged into a single "MRI score", which
would be the forbidden opaque market score.

## 5. Prospective accrual (E1) under existing immutable owners

Writer: `scripts/build_release_forecast.py` remains the only advancer of `forward_ledger.jsonl` (MRI-R8, nightly
only). E1 makes the following durable in that owner, without a new log:

1. **issued.** The existing `projection` and `shadow_projection` rows already record issuance. They already carry
   `prediction_id`, `inputs_hash`, `code_receipt`, `model_epoch` and `target_epoch`.
2. **withheld.** Today this is log-level only (`scripts/build_release_forecast.py:1185,1338,1769`). E1 adds a
   durable row or field in the same ledger, carrying `reason` and `target_epoch`, so a withheld forecast is
   countable after the fact.
3. **abstained.** This is a forecast deliberately not issued under a declared rule (for example, insufficient
   inputs). It is recorded the same way as withheld, with `reason = abstain:<rule>`.
4. **missed.** There is no row at D for a scheduled release. This is derived at scoring time from the owner's own
   schedule; no future release dates are hardcoded here.

**Target identity.** `(release, period, target_epoch, sequence = first, actual_receipt_id)`. Each identity is
counted once, keep-first; a later re-score never replaces the first scored row.

**Natural-time maturity.**
- A prospective per-target verdict needs at least **24 scored episodes after this freeze commit**.
- From 12 episodes onward, a forward MAE may be **displayed** with its CI and the label "early, n = k".
- Below 12, the state is `PENDING`.

At the current monthly cadence, 24 episodes is roughly 24 months per release family, and the surfaces say so
plainly.

Legacy epochs (`*_legacy_target_v1`, `legacy_cross_vintage_initial_levels_v0`) stay readable and labelled
`superseded`. Their accuracy is never shown as current, and legacy backtests never validate the repaired target
(A11). That is the F1 ruling recorded with M0.

## 6. Power, precision and stop rules

- **Power.** With about 60 to 70 CPI episodes in 2021+ and an episode-level loss-differential sd near the observed
  MAE scale, the minimum detectable R at one-sided α = 0.05 and 80% power is roughly 0.85 to 0.90. Smaller true
  gains are expected to come back `INSUFFICIENT` or `HOLD`, and that is the honest answer, not a failure of the
  protocol. NFP / PCE / PPI have similar N. The current-regime window (2024+, about 20 to 22 episodes) is reported
  for direction only and is never decisive on its own.
- **Stop rules.**
  - M0 runs once.
  - A falsified model's display claim is withdrawn on the M0 merge.
  - Prospective E1 runs until the owner's PREREG kill fires (for example, combined_v1 at n ≥ 24) or 24
    post-freeze episodes accrue, whichever is first. There is no early stopping on a good streak.
  - E2 runs one confirmatory pass.
  - X0 runs once over history, then accrues forward rows through the existing event-window keep-first writer.
- **Escalation.** Any proposal to add a model variant, change a target epoch, or reuse a window after seeing results
  requires a superseding E0 revision with a new declared trial budget **before** the run.

## 7. Deviations

Allowed without revision: an owner-side bug fix that makes a frozen spec run as written (recorded with its commit),
and a source outage that turns rows into `MISSING_SOURCE` (counted). Everything else is a deviation. It is recorded
in the result document under "DEVIATIONS" and demotes the affected verdict to `HOLD`.

## 8. Census gaps carried forward (owners named; not fixed here)

- **Cleveland nowcast has no rights stanza** in `config/dataset_registry.yml`. It can be compared internally, but
  publishing Cleveland values on a user surface waits for the R1 / G0 rights determination.
- **Street consensus is unavailable** (`latest.json`: `street_consensus = unavailable`). No surface may say
  "consensus".
- **Breakevens are not MRI print benchmarks.** They are a rates response (H3) only, never "expected CPI".
- **MRI families are absent from `data/trial_ledger.jsonl`** (1,772 rows on main). M0 declares its 15 through the
  existing writer, and past MRI PREREG attempts stay counted in their own documents.
- **AHE / AWH: `no_data`.** Out of M0.
- **Parquet interiors were not inspected** by the census. M0 opens what it uses and records hashes.

## 9. Independent review record

Filled in by the review lane before this protocol is marked ready. The record gives the reviewer identity
(provider / model / lane id), the commit reviewed, the verdict, each finding with its disposition, and the commit
that applied each accepted change.
