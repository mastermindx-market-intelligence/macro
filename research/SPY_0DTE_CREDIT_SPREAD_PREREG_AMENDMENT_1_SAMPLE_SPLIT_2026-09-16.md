# SPY 0DTE Credit-Spread Prereg Amendment 1 — sample split + forensic quarantine

**Date:** 2026-09-16  
**Status:** FROZEN PRE-OUTCOME AMENDMENT — **NO TRADE / SCORE / SIZING AUTHORITY**  
**Parent prereg:** `research/SPY_0DTE_CREDIT_SPREAD_FORENSIC_PREREG_2026-09-16.md`  
**Branch base before amendment:** `e34268fc2bd808404f4184a3dff16a15b447e488`  
**Protected Sol procedure used for this continuation:** `mastermindx-market-intelligence/Mastermind@8ba7deedde164c90298d3e88785d98e02fa5e2d2`, Skillpack `1.0.1`, bootstrap major `1`.

## 1. Why this amendment exists

The parent prereg deliberately deferred exact calendar partitions until point-in-time source availability was measured. That availability has now been measured without calculating broad strategy returns.

A second contamination issue is now explicit: this research session has inspected public OPG/Caleb trade/P&L disclosures during the 2026 live experiment, including exact-strike executable replays on 2026-08-24, 2026-09-03 and 2026-09-15 plus surrounding public running-P&L information. Those dates, and the surrounding disclosed experiment window, are therefore not an untouched statistical holdout.

This amendment freezes the split **before** A0/A1 economic outcomes are calculated across the historical panel. It does not change the frozen strategy clocks, credit band, spread width, TP/stop families, execution-cost law or gamma ablation order.

## 2. Availability observation used to freeze the split

Read-only inspection of the incumbent licensed ThetaData v3 history on the existing host found:

- SPY stock-quote session dates are present through 2026-09-15;
- SPY has a same-day listed option expiration on every stock-quote session from 2023-01-03 through 2026-09-15;
- total common SPY stock-quote / same-day-expiration sessions in that interval: **928 / 928 (100%)**;
- the uninterrupted daily-0DTE era already begins before this panel (2022-11-11), so the 2023 start is a deliberate study boundary rather than the first available daily 0DTE session.

This proves listing/date-level availability only. Exact per-clock quote quality, underlying minute-bar completeness, PIT Greeks/IV availability, event coverage and close-path replayability remain separate coverage gates and are measured next.

## 3. Frozen calendar partitions

The statistical study now uses these contiguous date partitions:

| Partition | Dates | SPY sessions | Same-day expiration sessions | Role |
|---|---:|---:|---:|---|
| Development | 2023-01-03 → 2024-06-28 | 374 | 374 | feature construction, deterministic baseline implementation, finite rule-family development |
| Validation | 2024-07-01 → 2025-06-30 | 250 | 250 | choose clock/direction/risk-rule families and freeze remaining finite choices |
| Final holdout | 2025-07-01 → 2026-07-14 | 260 | 260 | one-shot untouched economic evaluation after development + validation freeze |
| Forensic quarantine | 2026-07-15 → 2026-09-15 | 44 | 44 | public OPG reconciliation / external face-validity only; excluded from statistical inference and parameter choice |

All four ranges tile the 928-session 2023-01-03 → 2026-09-15 availability panel with no overlap and no gap.

## 4. Why the final holdout ends on 2026-07-14

Public OPG running-day counts are not perfectly internally consistent about whether the experiment's first counted day was 2026-07-15 or 2026-07-16. A 28-day running total ending 2026-08-21 back-counts to 2026-07-15, while several 22/36/42-day references back-count to 2026-07-16 under the licensed SPY session calendar.

The study therefore adopts the conservative boundary: **2026-07-15 and later are quarantined**. This avoids treating a possibly disclosed first session as untouched simply because newsletter counting conventions disagree by one day.

The quarantine is stronger than excluding only the three exact-strike replay dates. Public running totals and day-level outcomes can leak qualitative knowledge about the same strategy family even when a particular day's strikes are unknown.

## 5. Holdout law

The 260-session final holdout is sealed against:

- parameter tuning;
- clock-family selection;
- direction-policy selection;
- TP/stop-rule selection;
- credit-band changes;
- strike-envelope changes;
- feature-family promotion;
- gamma inclusion/exclusion decisions;
- discretionary removal of losing or unusual sessions.

Coverage/null diagnostics may inspect whether a required source exists on a holdout date and may inspect timestamp/schema validity, because availability must be known before evaluation. They may **not** calculate or summarize holdout trade returns, TP/stop outcomes, P&L, Sharpe, drawdown or tail metrics until the complete A0/A1 development/validation choice set is frozen.

If a source family is systematically unavailable, that family is removed or the study status becomes `INSUFFICIENT_HISTORY`; missing holdout rows are not retrospectively repaired with future-known or different-source substitutes.

## 6. Forensic-quarantine law

The 44 quarantined sessions are not discarded. They serve a different evidentiary role:

- reconcile public entry clock / strikes / credit / exit claims against historical executable NBBO;
- test reporting-accounting and integer-size hypotheses;
- test whether a frozen earlier-era rule produces externally face-valid behavior **after** its statistical evaluation is complete;
- document disagreements between public narrative, source quotes and inferred account economics.

They may never improve a parameter that is then scored as if it were selected without those observations.

## 7. Immediate next gate

Before any broad A0/A1 return calculation, publish exact date-level availability for:

1. 09:35 / 09:45 / 10:00 same-day SPY option quotes under the frozen executable quote-quality law;
2. SPY 1-minute opening-path bars needed for price/VWAP/range features;
3. PIT same-day IV/Greeks inputs where available;
4. scheduled-event flags;
5. executable close-path quote coverage required by the frozen TP/stop simulation.

Only when those coverage results are frozen may development/validation A0/A1 outcomes be computed. The final holdout stays sealed until the remaining finite choices are frozen.
