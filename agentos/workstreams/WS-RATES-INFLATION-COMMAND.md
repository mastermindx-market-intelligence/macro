---
key: RATES-INFLATION-COMMAND
title: Rates & Inflation Command plus Macro Release Intelligence completion
objective: >
  Deliver one correction-safe, evidence-calibrated premium Rates & Inflation workflow spanning
  releases, rates/curve momentum, dealer/OPEX context, canonical transmission, policy/Fed path,
  Forward Path synthesis and learning. Done means real current inputs traverse production into the
  actual user/machine consumers with all authority ceilings, nulls, evidence clocks and failure states
  intact; CI or merged infrastructure alone is not completion.
status: active
program: rates-inflation-command
repos: [macro]
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - engine/release_forecast*.py
  - engine/event_calendar.py
  - engine/event_window.py
  - engine/opex_risk.py
  - engine/options_surface.py
  - engine/rate_inflation_transmission.py
  - engine/rates_inflation_command.py
  - scripts/build_rates_command.py
  - data/release_forecast/**
  - data/rates_command/**
  - data/options_surface/**
  - data/transmission/**
  - site/macro.html
depends_on: []
waves:
  - id: F0
    title: Recovery, capability ledger and architecture freeze
    status: done
    pr: 6543
  - id: F1
    title: Release and event truth/intelligence closure
    status: todo
    depends_on: [F0]
  - id: F2
    title: Dealer/OPEX state and HS3/HS4 historical priors
    status: todo
    depends_on: [F0]
  - id: F3
    title: Yield momentum and canonical Transmission extension
    status: todo
    depends_on: [F0]
  - id: F4
    title: Forward Path canonical composition
    status: todo
    depends_on: [F1, F3]
  - id: F5
    title: Unified premium Rates & Inflation experience
    status: todo
    depends_on: [F2, F4]
  - id: F6
    title: Evaluation, learning and evidence-clock composition
    status: todo
    depends_on: [F1, F2, F3, F4]
  - id: F7
    title: End-to-end production reliability and acceptance
    status: todo
    depends_on: [F5, F6]
decisions:
  - DEC:RIC-CANONICAL-COMPOSITION-BOUNDARIES
  - DEC:RIC-BASIS-CONTRACT-V1-QUALIFIED-COMPARISON
  - DEC:RIC-F1-EVALUATION-TARGET-IS-PUBLISHED-FIRST-PRINT
  - DEC:RIC-E0-RETROSPECTIVE-FALSIFIES-PROSPECTIVE-PROMOTES
discoveries:
  - DSC:RIC-RECOVERY-FOUND-STATUS-DRIFT-AND-W3-W4-DISCONNECT
landmines:
  - "Old July W-number status is not current capability truth; see DSC:RIC-RECOVERY-FOUND-STATUS-DRIFT-AND-W3-W4-DISCONNECT."
  - "Calendar/OPEX proximity may not rank, score, gate or size risk; preserve DNR:KILL-CALENDAR-GATED-RISK."
  - "MRI current accuracy is withheld under the repaired target epoch; do not cite superseded legacy backtests as current efficacy."
  - "Slack delivery/membership is not runtime claim or worker execution; current Autonomy V1 dispatch law applies."
do_not_redo:
  - "Do not create a second release/calendar truth plane; compose MRI + event_calendar."
  - "Do not create a second options/dealer store or resurrect retired Polygon source assumptions; current ThetaData/options_surface owns the broad surface."
  - "Do not create the July-style parallel rates-to-cohort engine; canonical Transmission owns pass-through and per-name sensitivity."
  - "Do not build a policy-timing predictor or calendar/OPEX directional signal."
artifacts:
  - research/RATES_INFLATION_COMMAND_RECOVERY_AND_COMPLETION_FREEZE_2026-08-27.md
  - research/RATES_INFLATION_COMMAND_MASTERPLAN_BY_FABLE.md
  - research/MACRO_RELEASE_INTEL_MASTERPLAN_BY_FABLE.md
  - research/TRANSMISSION_INTELLIGENCE_MASTERPLAN_BY_FABLE.md
  - research/rates_inflation_command/seat_20261014/R0_CUSTODY_LEDGER.md
  - research/rates_inflation_command/seat_20261014/B0_BASIS_CONTRACT_FREEZE.md
  - research/rates_inflation_command/seat_20261014/F0_COVERAGE.md
next_action: >
  E2E completion programme (Chairman masterplan 2026-10-13, Fable Meta-CEO seat fc3dfe4b). Wave 1 is
  merged: R0/B0 records #9206, E0+P0 #9212, F0 gap #9222, F1 #9232, B0 #9233, D0 #9252, T0 #9253,
  Y0 #9254. Next: merge M0/X0 #9282 (never re-run M0/X0), one main ci.yml baseline, then ship
  D1/Y1/I0, then C0 composition, then P1, X1, V0, A0, E1, P2, G0, S0, E2, B1, A1, Z0 per masterplan
  section 13. Latest handoff: agentos/handoffs/RATES-INFLATION-COMMAND-2026-10-14-e2e-seat-wave1.md.
  F0 (#6543, #9222) is reused, never redone; held #7909 and the GRI programme (#8317) are preserved.
---

## Why this workstream exists

Rates & Inflation Command accumulated real implementation across multiple July/August programs, but
there was no durable Agent OS workstream tying current product intent, authority law, current gaps and
continuation together. The result was a stale W-number masterplan coexisting with newer canonical
release/transmission/options systems and disconnected implementation seams.

## Current frontier

F0 is records-only and has no product/runtime effect. F1/F2/F3 are the first independently useful
capability lanes, but as of the recovery they are not runtime-claimed. F4-F7 remain CEO-owned
integration waves and may not be treated as commissioned merely because this record names them.

The complete capability ledger, exact first commission packets and production acceptance contract are
in `research/RATES_INFLATION_COMMAND_RECOVERY_AND_COMPLETION_FREEZE_2026-08-27.md`.
