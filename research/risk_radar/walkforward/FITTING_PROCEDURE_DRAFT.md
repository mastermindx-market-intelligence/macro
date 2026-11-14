> **Superseded 2026-11-12 by PREREG_WALKFORWARD_v1.md.**

# Risk Radar fitting procedure — DRAFT (not frozen)

Status: working draft. Freezing (hash-pinned prereg) waits for the PRO-RUN D adjudication of the
fold design, per the principal's ruling of 2026-11-12. No refit has been run.

## 1. What is fitted

| Group | Parameters | Search grid (coarse) |
|---|---|---|
| Bands | watch, caution, elevated, risk_off on the 0–100 sub-score | each in 5-point steps, ordered watch < caution < elevated < risk_off, from 40 to 95 |
| Tier-A leg confirm threshold | one shared `thr_pct` for validated legs | 0.80, 0.85, 0.90, 0.95 |
| Tier-A weight pairs | major-leg weight in credit, rates, bubble, growth | 0.5, 0.65, 0.8, 0.95 |
| Context gate | breadth percentile cut | 0.20, 0.30, 0.40, 0.50; or gate off |
| Step-down persistence | sessions a down-trigger must hold before RISK-OFF → GUARDED | 1, 3, 5, 10 |

Everything else is assigned `convention` (504/63 percentile windows, 200-session averages,
252-session maturity floors, decile tails) or `structural` (tier rules, Tier-B escalate-only,
display-only legs, the armed+confirm form). Each of the census's 44 groups gets one of these
three origins, with a written reason, in `definition_origins.json` (to be written with the freeze).

Tier-B weights are not fitted. They have no out-of-window evidence; they keep equal weights
(`structural`), which replaces today's unsourced splits.

## 2. Objective

Primary, at a **fixed alert budget** for the loud state (elevated+): maximise *episode recall by
breach* for ≥7% episodes at h = 21, with ties broken by median lead to breach, then by fewer false
alarms. The budget is declared in the prereg (proposal: 15% of sessions, about today's in-sample
loud share). Day-level precision is reported, never optimised.

Rationale: §4 of `SCORECARD_INSAMPLE_2026-11-12.md` shows that day-level precision rewards
switching on inside drawdowns. The user needs earlier recognition of an episode, at a budget users
can live with.

## 3. Search discipline

- Coordinate-wise search in the fixed order of the table above, two passes.
- Shrinkage: a parameter leaves its current value only if the objective improves by at least one
  episode, or by five sessions of median lead, on the fit window.
- Every evaluated configuration is logged with its fit-window score, so the effective search size
  is reported.

## 4. Folds

Expanding fit window from 2020-01-02 (inputs use earlier history for trailing percentiles). Outcomes
through the fit end only (`outcomes_through`). A 21-session embargo separates fit end from score
start. Score years: 2022, 2023, 2024, 2025, 2026 to date; 2024 onward is labelled seen history.
Fold design is open to change after PRO-RUN D.

## 5. Inputs

All Tier-A legs and the gate have stored history long before 2018, enough for 504-session
percentiles in fold 1 (census check, 2026-11-12):

- credit OAS from 1998
- MOVE from 2003
- real yields from 2004
- bubble legs from 1994/2001
- growth legs from 2000
- breadth from 1962

Nothing needed rebuilding for fold 1.

Three Tier-B inputs have only forward history, and are absent from both live and replay until they
mature:

- put/call from 2026-06
- GEX from 2026-06
- AI-breadth split from 2025-03

They are rebuild candidates under the standing rule:

- put/call from CBOE's published daily archive
- GEX from historical option chains (ThetaData, covered by the standing attestation)
- AI-breadth split from point-in-time constituents and the AI tag

This is scheduled as slice 1b. It does not block fold 1.

## 6. Outputs

- Per fold: parameters (hashed), the fit-window scorecard and the out-of-sample scorecard.
- Pooled out-of-sample scorecard, kept apart from in-sample.
- Baseline scorecards on the same windows and budget.
- `walkforward_state_series` and alert series (dated, each row tagged with its fold and hash).
- A descriptive stress table for 2007–09 and 2018.
