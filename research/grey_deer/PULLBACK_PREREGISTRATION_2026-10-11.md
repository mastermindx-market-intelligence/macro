# Pullback Probability and Depth — Preregistration v1

Status: pre-analysis protocol. Freeze this file in Git before computing any outcome, label, feature or
score on the qualified sample.

Source base: `f1ae1e0365fc` (`origin/main`, 2026-10-11).
Protected procedure: `mastermindx-market-intelligence/Mastermind@66495f7b479ebf1c2188a6188c60b3b35d728da0`, Skillpack 1.0.1/bootstrap 1.
Eligible-input manifest: `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md`
v1.0.0, blob `38925409555d046eb9d3ad38ddaba33e2159a3d3` at `565d883c2657`.
Program: `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258 · operation `risk-radar-pullback-20261009`.

**Label mapping.** Seat lane GD-PB-T22 is masterplan §6.3 and `TASK_GRAPH.json` T16 (O5, "Freeze
evaluation and reproduce qualified baseline comparisons"). `TASK_GRAPH` T22 is the later acceptance
task and is not this file. Authored in the O5 function by the Fable seat (session `da1ad7ad`). The O8
function is an independent read-only audit of this file before merge. The O8 audit of the draft
returned FAIL (3 blockers, 8 majors, 10 minors). Every finding was applied before this freeze. The
audit reproduced the fold calendar exactly and computed no outcome.

## 0. What was already seen before this freeze

The seat states its exposure so a reader can judge what "pre-analysis" means here.

| Already read | Not computed |
|---|---|
| Sample availability and identity only: row count, first and last date, gaps, NA count, duplicate count, hashes, fold calendar | Any close-to-close return, drawdown, label, feature, forecast or score on this sample |
| The 2026-09-22 displayed-probability aggregates (base rates, BSS, n, events per horizon) | Any Massive-basis outcome |
| The 2026-09-23 walk-forward verdict (`not_promotion_eligible`) | |
| The 2026-09-24 prospective readiness bar | |
| The S07 phase-only verdict (N 291 / 104 / 96, 8 abstained) and S06 (not promotion eligible) | |
| Public market history of 2021–2026 | |

**Consequence.** The retrospective sample is development evidence. Its major episodes are public
knowledge, so no part of it is an untouched holdout. The only untouched reserve is prospective.

**Manifest erratum, recorded here and not by editing the manifest.** Manifest §5 says the episodes
reachable in the window are "the 2022 drawdown and the 2023 banking stress only". Public market
history also places the 2023 autumn, 2024 summer and 2025 spring drawdowns inside the window. This
protocol never uses a named episode list. Clusters are counted mechanically from labels (§8).

## 1. Question

On a licensed, historically-available US sample, do simple, causal, close-only models forecast SPY
pullback probability and depth better than unconditional, volatility-matched and trend baselines, by
enough and stably enough to count as qualified research evidence?

This protocol does not issue, display, publish or size anything. It changes no customer odds,
severity or capital. Masterplan §6.3 and SCIENTIFIC_PROTOCOL §5–§6 bind it.

## 2. Four sample views (SCIENTIFIC_PROTOCOL §2)

| View | Evidence class | Role here |
|---|---|---|
| Historically-available reconstruction | HISTORICALLY_AVAILABLE | The primary sample (§3). All gates. |
| Current-vintage reconstruction | CURRENT_VINTAGE | The incumbent replay only (§6, INC). Diagnostic table. Never pooled. Never a gate. |
| Prospective issued origins | GENUINELY_ISSUED | Not started. N = 0 at freeze (§13). |
| Excluded or unavailable origins | typed | Every excluded origin carries its first failing reason (§3, §10). |

The three evidence classes are never pooled (manifest D8).

## 3. Frozen sample

**Input.** Manifest row 1 only: US SPY Massive `us_stocks_sip/day_aggs_v1` closes, RAW basis
(manifest D5). Hydrate with `python -m scripts.fetch_r2 --dirs massive_stock_day`; a nonzero exit stops
the run. Then load with `collectors.massive_stock_day.load_ticker("SPY")`, a plain `pd.read_parquet` of
the local store file hydrated from R2 prefix `massive_stock_day/`. `load_ticker` returns an empty frame
on a missing file or any read error (`collectors/massive_stock_day.py`, `load_ticker`), so an empty
frame stops the run as `BLOCKED / SOURCE_UNREADABLE`. The standalone recipe below reads the same file
by path; the executing script applies the recipe's identical normalisation and encoding to the very
frame `load_ticker` returned, never to a second read. The parquet is never committed.

**Window.** From `EARLIEST_ENTITLED` 2021-07-06 through the manifest store receipt `latest_date`
2026-10-07, inclusive. Rows after 2026-10-07 are dropped before anything else runs. The floor is a
rolling entitlement floor (manifest D1). A later floor shrinks the sample and requires a new revision.

**Measured identity at freeze.**

| Field | Value |
|---|---|
| rows in window | 1,321 |
| first / last date | 2021-07-06 / 2026-10-07 |
| rows with any NA in the hashed columns | 0 |
| duplicate dates | 0 |
| longest calendar gap | 4 days |
| weekday absences | 51, all NYSE holidays |
| `subframe_content_sha256` | `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb` |

The object hash of the whole store file is disclosed but is not the identity, because the file grows
every night. At measurement the R2 object had etag `2202e6276bf2fb97fe5cc645bdc4fe8c`, 63,556 B,
`last_modified` 2026-10-10T09:20:10Z, sha256
`03edf79f05699ca239a4b53e444d0254071479587e40f2528a4280ade99781b1`, 1,323 rows through 2026-10-09.

**Identity recipe (frozen, run first, prints identity only).**

```python
"""Canonical content hash of the frozen SPY subframe. Prints identity only, never values."""
import hashlib, sys
import pandas as pd
p = sys.argv[1]
raw = open(p, "rb").read()
df = pd.read_parquet(p)
df = df.reset_index(drop=("date" in df.columns))
if "date" not in df.columns:
    df = df.rename(columns={df.columns[0]: "date"})
df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
cols = ["date", "open", "high", "low", "close", "volume", "transactions"]
sub = df[df["date"] <= "2026-10-07"][cols].sort_values("date")
def enc(v):
    if isinstance(v, str): return v
    if pd.isna(v): return "NA"
    return float(v).hex()
h = hashlib.sha256()
h.update(("|".join(cols) + "\n").encode())
for row in sub.itertuples(index=False):
    h.update(("|".join(enc(v) for v in row) + "\n").encode())
print("subframe_content_sha256", h.hexdigest())
```

A different hash means the run stops as `BLOCKED / SAMPLE_IDENTITY_MISMATCH`. It is never re-hashed
into agreement, and the fix is a new revision of this file.

**Integrity checks, in order, before any feature.** The first failure stops the run with its type.

1. Dates strictly increasing; no duplicates; the set of row dates equals
   `lib.nyse_calendar.sessions_between(date(2021, 7, 6), date(2026, 10, 7))` exactly. A session with no
   row stops the run as `ABSENT_SESSION`, because a label spanning an absent session is immature
   (SCIENTIFIC_PROTOCOL). Equality held at measurement: 1,321 rows, 1,321 sessions.
2. Every close is positive and finite.
3. Every day-over-day close ratio lies in [0.75, 1/0.75]. Otherwise `PRICE_BASIS_DISCONTINUITY`. This
   is the S08 split-like guard, `SPLIT_LIKE_RATIO = 0.75`. The run refuses rather than re-adjusts.
4. Manifest §7 refusals 1–6 apply as written. Nothing is ever filled.
5. Every result artifact carries manifest version `1.0.0`, the `subframe_content_sha256` above and
   the Git blob sha of this file.

## 4. Frozen target

For origin `t` with close `P_t` and horizon `h ∈ {5, 10, 21}` sessions:

`A(t, h) = max(0, 1 − min(P_{t+1}, …, P_{t+h}) / P_t)`

- **Event.** `Y(t, h) = 1` iff `A(t, h) ≥ 0.05`. This matches the target of the incumbent and of the
  2026-09-22 prereg: SPY close-relative maximum loss of at least 5% within the next `h` closes.
- **Quantile target.** `A(t, h)` itself, at levels `τ ∈ {0.5, 0.8, 0.9}`.
- **Maturity.** An origin is mature for `h` only when its `t+h` close is inside the window. An
  immature label is absent, never zero.
- **Basis disclosure.** RAW closes drop on SPY ex-dividend dates. Measured loss is therefore slightly
  inflated. This is disclosed and not corrected (manifest D5).
- **Total episode depth.** `D_total(a) = max(1 − T/H, 1 − (P_t/H)(1 − a))` (masterplan §6.2, S09)
  is reported for P-active origins only, descriptively, with `H` and `T` from the observer. An S09
  refusal is an abstention. It is never a gate.

## 5. Populations and warm-up

- **Warm-up.** An origin is warm when its row index is at least 63, matching the observer's
  `reference_closes = 63`. The first warm origin is 2021-10-04.
- **P-all.** Every warm, mature origin. Executable now. Primary.
- **P-active.** Every P-all origin where the causal pullback observer, run on the prefix through `t`
  only, returns `active is True`. The observer is `lib/pullback_observation.py` `observe()` with rules
  `close_path.v1`. It is on held draft PR #8188 (head `ff27a268abaa`) and not on main.
  - Until that observer is on main with byte-identical rules, every P-active row is
    `BLOCKED / OBSERVER_NOT_ON_MAIN`. This seat never copies #8188's code.
  - A rules change on landing (any of the nine `close_path.v1` values) requires a new revision,
    subject to the §12 stage-2 rule.
  - Frozen rule values: reference 63, onset drawdown 0.02, onset closes 2, shock drawdown 0.05,
    stabilization 3, recovery above MA 5, recovery no-low 10, trend-repair above MA 20, trend-repair
    no-low 21.

## 6. Frozen configurations

All features use closes at or before `t`. Feature standardisation uses only the mean and standard
deviation (`ddof = 0`) of that block's purged training rows of that population. `SMA_w =
close.rolling(w).mean()`, including `t`. `r_k = log(P_t / P_{t−k})`. Every feature window is full at
row index 63 and later (`realized_vol` `min_periods` is 10 at `w = 20` and 31 at `w = 63`,
`engine/vol_forecast.py`).

| Id | Population | Kind | Definition |
|---|---|---|---|
| B0 | each | binary | `(k + 0.5) / (n + 1)` over the training prefix of that population |
| B1-20, B1-63 | each | binary | L2-logistic on `log rv_w`, `rv_w = engine.vol_forecast.realized_vol(close, w)` |
| B2-21, B2-63 | each | binary | L2-logistic on `close / SMA_w − 1` |
| M3-ALL | P-all | binary | L2-logistic on `dd63 = 1 − close / max(close over the 63 closes ending at t)`, `r5`, `r10` (log returns over 5 and 10 closes), `log rv20` |
| M3-ACT | P-active | binary | L2-logistic on observer worst drawdown `1 − low_close / peak_close`, rebound `close / low_close − 1`, `r5`, `r10`, `log rv20`, `log1p(observed_closes_since_onset)` |
| INC | P-all origins it covers | binary | Incumbent replay, CURRENT_VINTAGE (below) |
| Q0 | each | quantile | Training-prefix empirical quantile of `A` (numpy `method="linear"`) |
| Q1 | each | quantile | Q0 within training rv20 tercile cells. Bounds `numpy.quantile(train_rv20, [1/3, 2/3], method="linear")`; a test origin goes to cell `numpy.searchsorted(bounds, rv20, side="right")`. A cell with under 20 training origins issues the block's Q0 value instead (logged `TRAINING_CELL_THIN_FALLBACK`), so Q1 never abstains on cell size |
| Q3-ALL | P-all | quantile | Linear quantile regression of `A` on the M3-ALL features |
| Q3-ACT | P-active | quantile | Linear quantile regression of `A` on the M3-ACT features |

- **Logistic fit.** Objective `Σ log-loss + (1 / (2C)) ‖β‖²`, intercept unpenalized, `C = 1.0`.
  `scipy.optimize.minimize(method="L-BFGS-B")`, `gtol = 1e-8`, `maxiter = 10000`, start at zero.
  Non-convergence abstains for that block as `FIT_NONCONVERGENCE`. `C = 0.1` is run for M3-ALL and
  M3-ACT as a sensitivity row only and is never a gate.
- **Quantile fit.** Per `τ`, unpenalized linear quantile regression with an unpenalized intercept on
  the same training-standardised features as the matching M3, solved as a linear programme with
  `scipy.optimize.linprog(method="highs")`. The crossing check (`q0.5 > q0.8` or `q0.8 > q0.9`) runs
  on the unclipped predictions, and a crossing origin abstains as `QUANTILE_CROSSING`. Non-crossing
  predictions are then clipped below at 0, because `A ≥ 0`. Q0 and Q1 are never clipped. A solver
  failure abstains for the block as `FIT_NONCONVERGENCE`.
- **INC.** The 2026-09-22 replay object exactly as implemented in
  `scripts/research/risk_radar_displayed_probability_audit.py` at `f1ae1e0365fc`:
  `calib = engine.risk_radar._calib()`, `sigs = leading_signals()`, `subs = subscore_series(sigs,
  calib)`, `state = engine.risk_radar_backtest.state_series(subs, calib, sigs=sigs)`,
  `hot = hot_tier_a_count(subs, calib)` (defined in that script) and
  `engine.risk_radar._drawdown_prob(state, hot, calib)[f"h{h}"]`. The artifact records the Git blob sha
  of the `data/risk_radar/calibration.json` overlay that `_calib()` read.
  - INC's probability table was measured on 2006–2026 history (`engine/risk_radar.py`), which
    includes this evaluation window. INC is therefore look-ahead-advantaged and is disclosed as such.
  - It is scored against its own CURRENT_VINTAGE label under the 2026-09-22 native semantics:
    `risk_radar_backtest._spy(drop_missing=False)` closes, a close-relative maximum loss of at least 5%
    within the next `h` native closes, complete windows only. It is scored on the dates of this
    protocol's P-all evaluation origins that it covers. It is never scored against the Massive RAW
    label (manifest §3 rule 4, §7 refusal 3).
  - It sits in its own table and is never pooled, never a reference model and never a gate. A replay
    failure is reported `BLOCKED` and blocks nothing else.
- **Not in this revision.** Mechanism families (ladder rung 4) and complex models (rung 5). The S07
  phase-only baseline is rejected for publication and is not used as a reference.

**Trial budget.** Registered with `engine.trial_ledger.register_trials` (a class, used as a context
manager), family `grey_deer_pullback_v1`, `basis="itemized"`, budget 69 = 23 per horizon, before any
outcome is computed. It appends to `data/trial_ledger.jsonl`, so the executing lane first opts its sparse
worktree into `data/` with `python3 scripts/worktree_sparse.py add data`.

| Per horizon | Count |
|---|---|
| P-all binary: B0, B1 ×2, B2 ×2, M3-ALL `C=1.0`, M3-ALL `C=0.1` | 7 |
| P-active binary: the same seven with M3-ACT | 7 |
| INC | 1 |
| P-all quantile: Q0, Q1, Q3-ALL | 3 |
| P-active quantile: Q0, Q1, Q3-ACT | 3 |
| Negative control (§12): M3-ALL shifted, Q3-ALL shifted | 2 |

## 7. Frozen folds

The fold calendar was derived mechanically from the session list before any outcome. It was not
chosen by looking at prices.

- **Training.** Expanding window. The first test block starts at the 253rd warm origin (2022-10-04).
  Its training set is the earlier warm origins that pass the purge: 248, 243 and 232 at `h` = 5, 10
  and 21. Every later block trains on every earlier warm, mature origin of that population that passes
  the purge, earlier test blocks included.
- **Test blocks.** Consecutive blocks of 126 warm origins after that. A final block shorter than 63
  merges into the previous block (not triggered at this freeze).
- **Purge.** A training origin `t` is admitted for a test block starting at origin `s0` only when
  `idx(t) + h ≤ idx(s0)`, so its label is known at the close of `s0`. `idx` is the row index in the
  frozen sample, which is the NYSE session index because §3 check 1 makes the rows equal the session
  list.
- **Embargo.** 0, because every feature is known at the close of issuance.
- **Refit.** One fit per configuration per test block. Never refit inside a block.
- **Thin folds.** A training prefix with fewer than 20 origins or fewer than 2 events (`Y(t, h) = 1`)
  abstains for that block as `TRAINING_FOLD_THIN`, except B0, which always issues.

| Horizon | Warm mature origins | Last mature origin | Evaluation origins | Test blocks |
|---|---|---|---|---|
| 5 | 1,253 | 2026-09-30 | 1,001 | 8 |
| 10 | 1,248 | 2026-09-23 | 996 | 8 |
| 21 | 1,237 | 2026-09-08 | 985 | 8 |

| Block | First test origin | Last test origin |
|---|---|---|
| 1 | 2022-10-04 | 2023-04-04 |
| 2 | 2023-04-05 | 2023-10-04 |
| 3 | 2023-10-05 | 2024-04-05 |
| 4 | 2024-04-08 | 2024-10-04 |
| 5 | 2024-10-07 | 2025-04-08 |
| 6 | 2025-04-09 | 2025-10-08 |
| 7 | 2025-10-09 | 2026-04-10 |
| 8 | 2026-04-13 | last mature origin (119 / 114 / 103 origins at h = 5 / 10 / 21) |

**Comparison set.** Every comparison is computed on the origins where every compared configuration
issues. For each horizon and population this is one binary set (B0, B1 ×2, B2 ×2, M3 `C=1.0`) and one
quantile set (Q0, Q1, Q3). Abstentions are reported, not imputed.

## 8. Clusters, honest-N and power

- **Event cluster.** The event-positive origins in the claim's comparison set, in time order, merged
  when `idx(e_{j+1}) − idx(e_j) ≤ h`, with `idx` the session index of §7, not the position in the
  comparison set. This is the 2026-09-24 definition, made explicit.
- **Episode window.** For a cluster, from 21 sessions before its first event origin through `h`
  sessions after its last event origin.
- **Episode.** The union of clusters whose episode windows overlap. The episode is the unit of the
  power floor and of the leave-one-out checks in §11.
- **Honest-N.** Every claim reports origins, events, clusters, episodes and distinct calendar months
  containing an event origin. Sessions are never presented as independent evidence.
- **Power floor.** A claim is assessable only with at least 10 episodes and at least 10 distinct event
  months in its comparison set. Below that the claim is `UNDERPOWERED_DISCLOSED` whatever its bounds
  say. The reason: a proportion estimated from `E` independent episodes has a 90% half-width of about
  `1.645 · sqrt(0.25 / E)`, which is 0.26 at `E = 10`. Ten is the coarsest floor at which a
  cluster-level statement means anything, and it is twice the 2026-09-24 readiness floor of 5.
- **Expectation stated in advance.** Evaluation starts 2022-10-04, so nearly all of the 2022 drawdown
  falls in training only. The floor may fail at every horizon and in both populations. Then every
  claim is `UNDERPOWERED_DISCLOSED`, the baseline and INC tables are still produced, and qualification
  moves to the prospective lane (§13). That outcome is reported, never re-cut.

## 9. Frozen metrics

**Binary, per horizon and population, on the comparison set:**

- Brier score; Brier skill score `BSS = 1 − Brier / Brier(B0)`.
- Calibration-in-the-large `CITL = mean(p) − mean(y)`.
- Weighted absolute calibration error `WACE = Σ_b (n_b / N_cov) |p̄_b − ō_b|` over bins with
  `n_b ≥ 100`, where `N_cov` is the sum of those `n_b`. Coverage `N_cov / N` is printed beside it.
  Bin edges: `[0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0]`, left-closed, last bin closed.
- Root weighted squared calibration error `RWSCE = sqrt(Σ_b (n_b / N_cov)(p̄_b − ō_b)²)` over the same
  bins, reported only.
- AUC (Mann–Whitney, ties counted ½), always printed beside the base rate, descriptive only.
- Every metric also by calendar year, by test block and by training rv20 tercile.

**Cost-sensitive value (Richardson).** With cost-loss ratio `α`, alarm when `p ≥ α`, event rate `s`,
hit rate `H` and false-alarm rate `F` on the comparison set:

- `E_fcst = α (H s + F (1 − s)) + (1 − H) s`
- `E_clim = min(α, s)`
- `E_perfect = s α`
- `V = (E_clim − E_fcst) / (E_clim − E_perfect)`

`α_h ∈ {0.5 b_h, b_h, 2 b_h}` with frozen constants `b_5 = 0.036`, `b_10 = 0.082`, `b_21 = 0.176`.
Source: `data/risk_radar/probability_evidence.json`, blob `3fd3b0a514e9531e1586f221aba371abc960c7cd`,
keys `horizons.h{5,10,21}.base_rate` = 0.03567, 0.08229 and 0.17647, rounded to three places. Their
window is `y2020`: 2020-01-02 through 2026-09-11, 2026-09-03 and 2026-08-19, native SPY closes,
CURRENT_VINTAGE. That window overlaps the evaluation window, so `b_h` is only a fixed scale for `α`
and the alarm threshold, never a model input. It differs from the engine's `_PROB_BASE`
(0.036 / 0.086 / 0.178 in `engine/risk_radar.py`), which is not used.

**Quantile:** pinball loss per `τ` and summed over the three levels; empirical coverage
`P(A ≤ q_τ)`; interval width `q0.9 − q0.5`; tail exceedance rate and mean excess above `q0.9`;
crossing count; stability by year and block.

**Early warning (descriptive), for M3 at `C = 1.0` and for INC, alarm = `p ≥ b_h`:**

- Cluster recall: share of clusters with an alarm on at least one of their event origins.
- Lead: sessions from the first alarmed event origin to the first session whose close is at least 5%
  below that origin's close.
- Missed damage: the largest `A` in each cluster with no alarm.
- False-alarm share: alarms at non-event origins over all alarms.
- False-alarm time: alarmed sessions outside every episode window, as a count and as a share of the
  sessions outside every episode window.
- Alarm runs: run lengths, and the share of runs overlapping an episode window.
- Censoring: clusters whose episode window touches the first or last origin of the comparison set are
  flagged.

**Abstention:** frequency and typed reason per configuration; abstention rate among event origins
against non-event origins; every comparison on identical eligibility.

## 10. Frozen uncertainty

- **Method.** Paired circular moving-block bootstrap over the time-ordered comparison set. One index
  draw per resample is applied to every configuration, so differences are paired.
- **Block length.** `L = max(21, 2h)`: 21, 21 and 42. Sensitivity rerun at `L = h`, reported only.
- **Draws.** 10,000 per horizon, population, family and block-length variant. The same draws serve
  the gate bound and the 90% reporting interval.
- **Algorithm.** `starts = rng.integers(0, N, size=ceil(N / L))`; each block is
  `(start + arange(L)) % N`; concatenate and keep the first `N`.
- **Seeds.** `rng = numpy.random.default_rng(numpy.random.SeedSequence([221011, h, pop, fam, var]))`
  with `pop` 0 = P-all and 1 = P-active, `fam` 0 = binary and 1 = quantile, `var` 0 = primary and
  1 = `L = h` sensitivity.
- **Recompute per draw.** Every statistic, including the best-baseline maximum and the better
  reference, is recomputed inside each draw.
- **Undefined statistics.** A draw in which a gated statistic is undefined (zero events, zero
  non-events or a zero denominator) records that statistic at its failing extreme: −∞ where the gate
  needs it large and +∞ where the gate needs it small (`WACE`). Bounds are `numpy.quantile` over all
  10,000 draws; `nanquantile` is never used. An undefined leave-one-episode-out point estimate fails
  that condition as `FRAGILE`.

## 11. Frozen gates

There are 12 gated claims: {binary, quantile} × {P-all, P-active} × {5, 10, 21}. They form one family.
Each one-sided lower bound is the `0.05 / 12` quantile (numpy `method="linear"`) of the 10,000 primary
draws. Within a claim every condition must hold (intersection-union), so no further adjustment is
made. Blocked P-active claims keep their share of the family; the level is never re-spent.

**Binary claim** (M3 at `C = 1.0`), all of:

1. Lower bound of `V(M3) > 0` at all three `α_h`.
2. Lower bound of `ΔV > 0` at `α = b_h`, where `ΔV = V(M3) − max(V(B1-20), V(B1-63), V(B2-21), V(B2-63))`.
3. Lower bound of `BSS(M3 vs B0) > 0`.
4. Calibration, on the same primary draws: the 90% interval (0.05 and 0.95 quantiles) of `CITL`
   contains 0, the 2026-09-24 idiom, and the 0.05 quantile of `WACE` is at most `0.5 b_h`. Point
   `CITL` and `WACE` are printed. If bins with `n_b ≥ 100` hold under 50% of the comparison set
   (`N_cov / N < 0.5`), this condition fails as `CALIBRATION_UNDERCOVERED`.
5. Abstention: M3 abstains, for any reason, at no more than 5% of the claim's evaluation origins, and
   its abstention rate among event origins exceeds its rate among non-event origins by no more than
   5 percentage points. Otherwise `ABSTENTION_CONCENTRATED`.
6. Leave-one-episode-out: dropping each episode's window in turn keeps the point estimates of `V` at
   `α = b_h`, `ΔV` and `BSS` above 0. Point estimates only: no draws and no refit, and the deletion
   applies to the evaluation set only. Otherwise `FRAGILE`.
7. The power floor in §8 holds.

**Quantile claim** (Q3), all of:

1. Lower bound of pinball skill `1 − PL(Q3) / min(PL(Q0), PL(Q1)) > 0`, where `PL` is pinball loss
   summed over the three `τ` and the minimum is taken inside each draw.
2. At each `τ`, the 90% interval of `coverage_τ` on the primary draws intersects
   `[τ − 0.05, τ + 0.05]`. Point coverage is printed.
3. Abstention: Q3 abstains, for any reason, at no more than 5% of the claim's evaluation origins, and
   its abstention rate among event origins exceeds its rate among non-event origins by no more than
   5 percentage points. Otherwise `ABSTENTION_CONCENTRATED`.
4. Leave-one-episode-out keeps the pinball-skill point estimate above 0, under the same rules as
   binary condition 6. Otherwise `FRAGILE`.
5. The power floor in §8 holds.

Baseline-against-baseline differences on P-all (B1 and B2 against B0, Q1 against Q0) are reported
with intervals as descriptive measurement and are not claims.

## 12. Verdicts and stopping

Verdict words are those of SCIENTIFIC_PROTOCOL; no new state machine.

| Outcome | Verdict |
|---|---|
| Baseline and INC tables reproduced and audited | accepted descriptive measurement |
| Claim fails any condition | rejected candidate |
| Claim below the power floor, or blocked by a typed reason | underpowered/blocked claim |
| Claim passes every condition | qualified research evidence (development, reconstructed) |
| Any live use | separately admitted live promotion, never produced by this protocol |

- **Rungs.** Rungs 1–2 (B0, B1, B2, Q0, Q1, INC) always run. Rung 3 runs on P-all now and on
  P-active only once the observer is on main. Rungs 4–5 are not in this revision.
- **One execution per revision, in two declared stages.** Stage 1 runs every P-all configuration now.
  Stage 2 runs every P-active configuration, unchanged, once the observer is on main with
  byte-identical `close_path.v1`. Nothing in this file may change between the stages.
  - If the observer lands with any different rule value, every P-active claim on this sample becomes
    `underpowered/blocked claim` (`OBSERVER_RULES_CHANGED`) permanently.
  - A later revision that admits P-active on 2021-07-06..2026-10-07 is development-only and cannot
    yield qualified research evidence. P-active qualification then moves to the prospective lane
    (§13).
- **No re-tuning.** A failed claim is preserved and never re-tuned. A passed claim is not promoted by
  this file; binding promotion goes through the existing promotion owner.
- **Deviations.** A code defect found after outcomes may be fixed only when the fix changes no frozen
  choice here. The original output is kept, and a deviation log names the defect, the fix and both
  results.
- **Source or rights change.** Any change to the manifest row, its rights or its basis is
  `BLOCKED` and requires a new revision.
- **Execution artifact.** The executing lane writes a results note and a JSON artifact under
  `research/grey_deer/`. Both carry:
  - the three identities in §3 check 5, and the blocked or abstained rows with their types;
  - the commit sha, and the blob shas of the executing script and of its dedicated test file;
  - an eligibility and maturity census per horizon and population, with typed exclusions
    (`PRE_ENTITLEMENT`, `WARMUP`, `IMMATURE`, `TRAINING_FOLD_THIN` and the other types named here);
  - a negative control, which is neither a claim nor a gate: M3-ALL and Q3-ALL refit with each
    training prefix's labels and targets circularly shifted by half its length
    (`numpy.roll(y, len(y) // 2)`, deterministic, no seed), reporting BSS, `V` at `α = b_h` and
    pinball skill, all expected at or below 0.
- **Synthetic tests.** The dedicated test file must prove the purge, the fold calendar, the
  comparison-set intersection, the reuse of one index draw across configurations and the
  crossing-then-clip order, on synthetic data only.

## 13. Prospective lane

- The prospective clock starts at the first GENUINELY_ISSUED forecast written under this exact recipe
  after this file merges. No issuing lane exists in this revision, so prospective N is 0 and the
  status is not started.
- An issuing lane belongs to its own owner. It writes into the existing forward-ledger identity
  (issue receipt and `issued_at`), never a second ledger.
- Prospective refits happen every 126 sessions as in §7, expanding, with every choice here unchanged.
- Prospective evaluation runs only when both bars hold: the 2026-09-24 readiness floor (252 issued
  sessions, a 300-day span, and per horizon 200 graded rows, 20 events, 50 non-events and 5
  clusters) and this protocol's power floor (§8).

## 14. Interpretation ceiling

- Reconstruction is not issued history. No sentence may describe a retrospective result as a
  forecast record.
- No customer odds, severity, publication or capital change follows from any result here. The
  manifest D4 publication gate stands.
- This protocol writes nothing to PR #8721 or PR #8188.
- If no candidate passes, the descriptive capability ships and predictive delivery is reported
  incomplete. Negative results stay discoverable in `research/grey_deer/`.

No alternate confidence level, binning, block length, population, target, threshold, quantile level,
cost ratio, power floor or horizon may be selected after outcome inspection.
