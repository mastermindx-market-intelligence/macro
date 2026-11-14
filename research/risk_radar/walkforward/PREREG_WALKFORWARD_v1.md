# Risk Radar walk-forward refit — preregistration v1 (FROZEN 2026-11-12)

Supersedes `FITTING_PROCEDURE_DRAFT.md`. Frozen after the PRO-RUN D adjudication (master plan
§14). The SHA-256 of this file is recorded in `PREREG_WALKFORWARD_v1.sha256` at the freeze commit.
Any later change is a dated addendum below the line at the end, never an edit. No fit has run.

**Claim class.** Retrospectively designed, chronological refit reconstruction. The leg set,
transforms, tier rules and every constant not listed in §2 were chosen with knowledge of 2020
onward and are frozen here as hindsight-informed design components. The result can show whether
annual refitting of the two declared quantities holds up out of the fit window. It cannot show that
the design is independent of 2020+. Scoring of 2024+ is the Radar's own seen history (direction
ruling 2026-11-12, point 6), not the research desk's sealed confirmation. Paper-only; nothing here
sizes, ranks, gates or executes.

## 1. Folds

| Fold | Fit window (features and matured labels) | Parameter freeze | Score window |
|---|---|---|---|
| F22 | 2020-01-02 → 2021-12-31 | 2021-12-31 close | 2022-01-03 → 2022-12-30 |
| F23 | 2020-01-02 → 2022-12-30 | 2022-12-30 close | 2023-01-03 → 2023-12-29 |
| F24 | 2020-01-02 → 2023-12-29 | 2023-12-29 close | 2024-01-02 → 2024-12-31 (seen history) |
| F25 | 2020-01-02 → 2024-12-31 | 2024-12-31 close | 2025-01-02 → 2025-12-31 (seen history) |
| F26 | 2020-01-02 → 2025-12-31 | 2025-12-31 close | 2026-01-02 → 2026-11-10 (seen history) |

- **Label maturity, not a score embargo.** At cutoff T a fit label is used only if every
  observation supporting it is dated ≤ T: episodes come from closes ≤ T; a top is a fit label only
  if its window [top − 21, top + 10] ends ≤ T; a bottom only if its episode recovered ≤ T and its
  window ends ≤ T. Scoring starts the next session; January events are kept.
- **Features** are the shipped causal transforms (trailing 504/63-session percentiles). They extend
  before 2020 as inputs only. No outcome before 2020 enters any fit.
- **State carries across fold boundaries** as one continuous stream: the resolver is memoryless per
  row, so there is no persistence state to reset.

## 2. What is fitted (two quantities, four candidates)

1. **Context-gate breadth cut** `g` ∈ {0.30, 0.40, 0.50, none} (outcome-fitted, the one degree of
   freedom). "none" = the context gate never clamps.
2. **Band offset** `Δ` (outcome-free): one shift added to all four bands (55/68/78/88), Δ ∈
   {−10, −8, …, +10}. For each `g`, Δ is the value whose loud share (elevated or risk-off) on the
   fit window is closest to **15%**; ties go to the smaller |Δ|. This uses inputs only.

Default = shipped (g = 0.40, Δ = 0). Everything else (individual band spacing, leg thresholds,
weights, tier rules, probability table) is frozen at shipped values. Step-down persistence is
dropped: the live resolver has no persistence memory, so the parameter would not be consumed.

## 3. Fit objective (in turn units; penalty declared here, not tuned)

On the fit window, at ≥5% SPY total-return episodes (shared definitions, `labels.py` and
`pivots.py`), using the loud state as the alert:

J = (tops flagged + bottoms flagged within [turn − 21, turn + 10])
    − 0.5 × (false risk-off calls + premature all-clears)

All-clear = off for at least 10 sessions. **Retain the default** unless the fit window has
≥ 4 matured scored turns **and** J(best) − J(default) ≥ 1. Ties: default first, then the
candidate with the smaller loud share.

## 4. Primary endpoint and comparators (out of sample, pooled F22–F26)

**Primary endpoint:** the pivot read of the walk-forward loud state on 2022-01-03 → 2026-11-10 at
≥5%, post window 10:
- tops flagged and bottoms flagged (counts, scored-turn denominators and exact 90% intervals);
- delays;
- false risk-off calls per year;
- premature all-clears per year.

**Primary comparator:** the shipped v2 loud state (frozen constants) over the same window. The
question is whether refitting helps.

**Secondary comparators:**
- HY OAS 21-day change, top decile, at its natural share. This is the baseline to beat (§13.4).
- A budget-calibrated HY OAS analogue, with its threshold set on each fit window to that fold's
  walk-forward loud share.
- SPY < 200-day average.
- VIX ≥ 20 and ≥ 25.

Realized score-window budgets are reported for each series. No threshold is set from a score
window.

**Practically important difference:** at least 2 more turns flagged than the comparator over the
pooled scored turns, with no more false risk-off plus premature all-clear calls. Anything smaller
is reported as **inconclusive**. That is a valid result: it promotes nothing and condemns nothing.
The per-fold table is descriptive only; there is no "wins k of 5" rule.

**Secondary endpoints:**
- day-level P(≥5% within 21);
- episode catch at onset and by breach;
- calibration;
- paper attribution, renamed as follows:
  - "loss avoided" becomes **remaining decline after first alert**;
  - the return sums become **retrospective arithmetic attribution**.

None of these choose anything.

## 5. Proofs required before the first fit runs

1. **Label maturity:** a top or bottom whose window or recovery passes T is refused as a fit label.
2. **Feature prefix invariance:** appending or perturbing input rows after date t leaves legs,
   sub-scores, gate and state at t and earlier unchanged.
3. **Parameter intervention:** on a fixture, changing `g` and changing `Δ` each change the state
   series. The harness injects its own gate; it does not read the module constant.
4. **Calendar:** missing alert sessions are refused, not compressed.
5. **Censoring:** right-censored turns and open episodes are excluded, not scored as misses.
6. **Effective-state hash:** each fold records `g`, `Δ`, effective bands, the code commit, this
   file's hash, input last-dates and leg availability by date.

## 6. Outputs

- `data/risk_radar/walkforward_state_series.json`, one row per session 2022-01-03 → 2026-11-10,
  with:
  - fold, `g`, `Δ`;
  - state;
  - loud flag;
  - legs available;
  - `design_seen` = true;
  - `fit_cutoff`;
  - `seen_history` (true from 2024-01-02).
- `data/risk_radar/walkforward_alert_series.csv` (date, loud) with its realized budget, for the
  research desk.
- A per-fold and pooled scorecard (pivot first, then secondary metrics) beside the in-sample
  reference. Out-of-sample and in-sample figures are never mixed in one figure.
- Every evaluated candidate is logged (4 per fold), plus any revision. Every attempted version is
  kept.

## 7. Turn catalogue reconciliation

The research desk is building a swing-rule turn catalogue (Chairman steer 2026-11-12).
- The fit objective (§3) uses the v1 SPY episode turns frozen here.
- If a reconciled catalogue arrives, the frozen walk-forward predictions are re-scored against it
  and reported as a separate read.
- The fit is not redone against it.

---
Addenda (dated, append only):
