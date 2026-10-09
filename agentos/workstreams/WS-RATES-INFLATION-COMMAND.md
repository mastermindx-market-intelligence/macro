---
key: RATES-INFLATION-COMMAND
title: Rates & Inflation Command plus Macro Release Intelligence completion
objective: >
  Deliver one correction-safe, evidence-calibrated premium Rates & Inflation workflow spanning
  releases, rates/curve momentum, dealer/OPEX context, canonical transmission, policy/Fed path,
  Forward Path synthesis and learning. Done means real current inputs traverse production into the
  actual user/machine consumers with all authority ceilings, nulls, evidence clocks and failure states
  intact; CI or merged infrastructure alone is not completion.
status: awaiting_ci
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
    status: awaiting_ci
    pr: 6543
    next_action: >
      Independently review and accept PR #6543 only after exact-head semantic/fence CI completes
      green; no product/runtime behavior is changed by F0.
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
  - research/sovereign_auction_pressure/NOTICE_ARCHIVE_V2_CONTRACT.md
  - research/sovereign_auction_pressure/SETTLEMENT_LEDGER_INPUT_CONTRACT.md
  - research/RATES_INFLATION_COMMAND_RECOVERY_AND_COMPLETION_FREEZE_2026-08-27.md
  - research/RATES_INFLATION_COMMAND_MASTERPLAN_BY_FABLE.md
  - research/MACRO_RELEASE_INTEL_MASTERPLAN_BY_FABLE.md
  - research/TRANSMISSION_INTELLIGENCE_MASTERPLAN_BY_FABLE.md
next_action: >
  RIC F3: confirm fixed_grid_origin.v4 liveness on the first nightly data/transmission/latest.json
  after PR #8030 (merged 2026-09-25), then execute W3 — the display-only yield_momentum consumer
  block in engine/credit_momentum.py beside interim_tlt (handoff RATES-INFLATION-COMMAND-2026-09-25).
  RIC-F1/F2 packets still go through canonical Executive admission as disjoint operations.
  Sovereign auction continuation: independently review stacked Draft/HOLD #8668 source and
  qualify its parent #8657 before main-targeted hosted CI; retain unknown private cash and
  the incumbent Macro/Bonds and cross-repository writer gates.
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


## Sovereign auction local Codex source continuation, 2026-10-08

The Chairman directly assigned operation `sovereign-auction-funding-local-codex-20261008-001` to Codex root `01a11e6d-efdc-78a0-a489-9c1a7891df0a`. Its own SSD source carrier extends #8657 without changing that branch or the other held carriers. Source commit `f6a9bbd0b8e9` implements inspected v7 notices, cutoff-first bounded archive replay, compatible context-age evidence and the H3 private cash/released financing input gate. Stacked [#8668](https://github.com/mastermindx-market-intelligence/macro/pull/8668) remains Draft/HOLD.

The source suite passes 124 tests and 79 subtests; the unchanged import/DAG suite passes 59 tests. Both exact held consumer readers pass the six-case compatibility matrix. Twelve original funding hashes still verify, with zero eligible at the October 5 cutoff, no qualified private cash inventory and H3 `INSUFFICIENT_PIT`. Three new XML captures and three original official cancellation/postponement PDFs have literal October 9 body/verification clocks. The PDFs establish source shapes; they are not an implemented special-notice transition or historical PIT eligibility.

Independent source acceptance is pending: current Executive ingress reports read-only and review admission returned `NONE reason=no_pool_available`, before any child launch. The stacked-base CI authority rejected the source candidate as `unsupported_base_ref`; no guard was altered and no main-targeted native CI pass is claimed. Correct issue binding remains `UNKNOWN`: current #6819 identifies Market Ontology. The parent mission, Macro/Bonds journey, entitled consumers, dataset freeze and production acceptance remain incomplete. Existing RIC waves and unrelated ownership are unchanged.

## Sovereign auction Fabric review and repaired source, 2026-10-09

On explicit Chairman resumption, the same root admitted independent Fabric child `sovereign-notice-archive-review-20261008-01` through the existing stable-handle adapter. Selected Grok/Ubuntu2 reviewed exact8e347f8e and returned `CHANGES_REQUIRED`; transportrc0, cleanup and12595byte artifact are separately verified. Parent reproduced both blockers and accepted the useful review task return without accepting source.

Semantic source `ce0211e3fc0bb98181615063faae5f0616e12c45` repairs result-close eligibility, economic-date relabeling, immutable vintage metadata, incomparable release bases, missing-body capture causality and nonregular archive reads. It passes132 tests/91 subtests and the six held-reader composition cases; all12 original funding hashes remain verified, with zero cutoff eligibility and `INSUFFICIENT_PIT`. Stacked #8668 stays Draft/HOLD; exact hosted check113656172939 rejects `unsupported_base_ref` and starts no native packs.

The repaired blobs owe `FULL_REREVIEW_REQUIRED`. Prepared child `sovereign-source-repair-review-20261009-02` was refused before launch when its selected MiniMax/mini2 route lost current host eligibility; same-ID status is `NOT_FOUND`. Continue with the retained same-root/child/packet through current admitted Fabric, not a duplicate worker or capacity override. Receipt: `research/sovereign_auction_pressure/verification/local_codex_20261008/FABRIC_REVIEW_REPAIR_20261009.json`. No active child, automatic wake, production deployment or programme completion is claimed.
