---
key: GLOBAL-LIQUIDITY-TRANSMISSION
title: Global Liquidity Transmission perception lobe
objective: >
  Build the governed measurement plane specified by Mastermind issue #117 without
  acquiring trading authority. Done means the state producer, downstream reader,
  causal transmission lab, and accepted product surface each pass their separately
  commissioned gates with explicit point-in-time and quality receipts.
status: awaiting_review
program: policy-transmission-intelligence
repos: [macro, mastermind]
owner: ceo-sol
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - config/global_liquidity_transmission_v1.yml
  - engine/global_liquidity_transmission.py
  - scripts/build_global_liquidity_transmission.py
  - data/global_liquidity_transmission/**
  - site/liquiditydata/global_liquidity_transmission.json
  - research/GLOBAL_LIQUIDITY_*.md
discoveries:
  - DSC:BOJ-ASSETS-REQUIRE-MONTH-END-ANCHOR
artifacts:
  - research/GLOBAL_LIQUIDITY_DATA_CENSUS_2026-08-22.md
  - research/GLOBAL_LIQUIDITY_TRANSMISSION_STATE_METHODOLOGY_2026-08-22.md
  - data/global_liquidity_transmission/state_history.parquet
  - data/global_liquidity_transmission/factor_comparison_btc_4w.json
  - site/liquiditydata/global_liquidity_transmission.json
waves:
  - id: W-LIQ.0
    title: Architecture and orchestration freeze in Mastermind issues 117 and 123
    status: done
  - id: W-LIQ.1
    title: Macro data census and state-quality-freshness producer
    status: done
    pr: 6296
    next_action: >
      Source repair accepted in #6296 comment 5539622225 and merged on 2026-09-04
      as 38fd57a676de07c361040eea7d5e5127034063e1. Do not redo that repair.
      This source milestone is not a fresh production or downstream-consumer proof.
  - id: W-LIQ.2
    title: Mastermind reader and Market View shadow plane
    status: todo
    depends_on: [W-LIQ.1]
  - id: W-LIQ.3
    title: Shock registry and causal transmission lab
    status: in_progress
    depends_on: [W-LIQ.2]
    next_action: >
      Existing Mastermind PR #124 at 23f97360131d05123acc440da15780b0bb200e82
      contains the research foundation and repaired producer adapter. BUILT_NOT_PROVEN:
      both hosted runs 35046156905 and 35051016157 failed; independent review is
      unplaced. No admitted study, live reader, or predictive authority. Reconcile
      hosted failure and exact-head independent review on the same PR. The authored
      dependency remains the whole-wave delivery gate, not a claim that W-LIQ.2 is done.
  - id: W-LIQ.4
    title: Repricing gap engine
    status: todo
    depends_on: [W-LIQ.3]
  - id: W-LIQ.5
    title: Product and chart surface
    status: todo
    depends_on: [W-LIQ.4]
  - id: W-LIQ.6
    title: Learning, calibration, and promotion governance
    status: todo
    depends_on: [W-LIQ.3]
landmines:
  - "The existing engine/global_liquidity.py uses JPNASSETS provider labels directly; do not reuse its monthly timestamp kernel for causal work."
  - "Availability lag is not a vintage archive: ECB and BoJ historical revisions remain a declared limitation."
  - "A null global credit impulse is the correct result until comparable release-stamped coverage exists; never coerce US C&I and China TSF into one scalar."
  - "Current liquidity measurement, future-liquidity forecasting, and asset-response estimation are separate capabilities. PR #124 supplies no future-liquidity forecast."
do_not_redo:
  - "Do not add a second global-liquidity collector before re-running the committed census against existing stores."
  - "Do not revive discontinued EZ/JP/KR/GB M2 parquets or admit China M2/NFCI/ANFCI into the causal state without a governed vintage solution."
  - "Do not build W-LIQ.2 or later waves from this Macro producer PR; issue #123 gives Sol cross-repo sequencing and acceptance authority."
  - "Do not rebuild accepted #6296, replace #124, weaken Executive security checks to green a native fixture, or call CI/merge a production outcome."
next_action: >
  Resolve Mastermind #124's hosted failure and obtain independent exact-head review,
  then separately admit the bounded reader/study policy under #123. Preserve all
  downstream gates; the broader Aion options repair is Terminal #591/#592, not this lobe.
---

## Boundary and corrected state

W-LIQ.1 owns state measurement and receipts only. Macro #6296 was source-accepted
and merged on September 4; the earlier body saying it was unmerged and awaiting
producer review is superseded by its GitHub merge metadata and acceptance comment.
This correction does not claim a fresh producer run, current data, deployment, or
real consumer acceptance. The weak research-only BTC comparison remains unchanged.

Mastermind #124 now contains the sole raw-producer adapter and research-episode
repairs. Native related evidence is 292 tests, including 96 lab tests, passed on
Python 3.12.13. Both full hosted runs failed; their cause remains unresolved.
The isolated native full-run diagnosis encountered an external-volume ancestry
check and was interrupted, not completed or passed. That local finding does not
identify the hosted Linux failure and must not authorize a security-policy change.

The research foundation progressed independently under control board #123, while
W-LIQ.3's whole-wave reader dependency remains unmet. No graph edge is silently
removed by this record. No empirical search or policy threshold was admitted.

Continuation: `agentos/handoffs/GLOBAL-LIQUIDITY-TRANSMISSION-2026-09-16-aion-recovery.md`.
Implementation/evidence owner: Mastermind #124, latest source-continuation comments
5691555906 and 5692332264. Runtime liveness is not inferred from this authored record.
