---
key: LEADERSHIP-PERSISTENCE-INTELLIGENCE
title: Leadership Persistence Intelligence — published theme memory and sector-price controls
objective: >
  Measure how existing published U.S. theme ordering and liquid sector leadership persist across
  exact session horizons without creating a new regime, signal or entry authority. Preserve separate
  estimands for rank memory, subsequent-return persistence, dispersion/correlation, phase-complete
  MACD outcomes, transitions and leader residency; make structural estimability, exact source bytes,
  sample units and immutable-head review explicit before any downstream consumer is considered.
status: active
program: sector-rotation-intelligence
repos: [macro]
owner: ceo-sol
class: research
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - research/rotation_persistence/
  - scripts/research/rotation_persistence/
  - scripts/research/run_rotation_persistence_rph0.py
  - scripts/research/run_sector_control_rph1.py
  - tests/test_rotation_persistence_*.py
  - docs/superpowers/plans/2026-09-10-leadership-persistence-rph0.md
  - docs/superpowers/plans/2026-09-12-sector-rotation-daily-control-rph1.md
  - docs/superpowers/plans/2026-09-14-sector-rotation-daily-control-rph1-review-repair.md
  - agentos/workstreams/WS-LEADERSHIP-PERSISTENCE-INTELLIGENCE.md
  - agentos/decisions/DEC-LEADERSHIP-PERSISTENCE-*.md
  - agentos/handoffs/LEADERSHIP-PERSISTENCE-INTELLIGENCE-*.md
decisions:
  - DEC:LEADERSHIP-PERSISTENCE-CROSS-OWNER-BOUNDARY
waves:
  - id: RPH0
    title: Frozen published-output persistence, transition and leader-residency harness
    status: awaiting_ci
    next_action: >
      Reconcile final hosted checks on Draft/HOLD PR #7064 while preserving its accepted exact-head
      research boundary, structurally unestimable temporal-shape receipt and zero product/trading
      authority. Do not merge or project it into a product in this wave.
  - id: RPH1
    title: Preregistered daily sector-price leadership and phase-complete MACD control
    status: done
    depends_on: [RPH0]
    next_action: >
      PARKED / HOLD-FOR-SOL on Draft PR #7095 after semantic PASS and records-repair review
      PASS_FOR_CLOSURE_COMMIT at 25a75a900e04. One exact closure-head read-only confirmation is the
      external acceptance receipt; no further source mutation is expected on PASS. The hosted archive
      lane remains main-only and no production timeframe, rank, gate, entry or trade consumer exists.
  - id: RPH2
    title: Separately preregistered 23/30-session or deeper point-in-time stratification
    status: todo
    depends_on: [RPH1]
    next_action: >
      HOLD as a separate future operation. Before reading or reusing another result, freeze a new
      preregistration, source-owner path, at-least-23-session or deeper-PIT estimand, lifecycle and
      hierarchy strata, and an untouched confirmation boundary. Do not relabel the current daily
      sector-control RPH-1 child as this wave or treat observed RPH-0/RPH-1 results as confirmatory.
landmines:
  - "Published score continuation is not economic-return IC or alpha."
  - "Leadership rank memory and subsequent-return persistence are distinct estimands and can have opposite signs."
  - "Whole-ranking half-life, strict-leader residency and score pressure are distinct estimands; no fused scalar authority."
  - "The frozen RPH-0 temporal-shape long side is structurally unestimable at recent_sessions=20 and min_pairs=8."
  - "A 23- or 30-session rerun after seeing RPH-0 is a new operation, never confirmatory RPH-0 evidence."
  - "Archive gaps are never forward-filled; incomplete multi-session bars are discarded."
  - "MACD phase rows share daily source sessions and are not independent pooled observations."
  - "WS:TEMPORAL-GRAIN-INTELLIGENCE retains chart-grain mechanics; Prophet Entry Truth retains strategy-specific availability."
  - "GMI/ThemeState and current basket owners retain identity, membership and publication authority."
  - "No result has rank, gate, size, trade, can_open_entry, Prophet, Oracle or portfolio authority at birth."
do_not_redo:
  - "Do not build a second ThemeState, rotation event, membership, identity, half-life, trial, publication or regime plane."
  - "Do not overwrite the structurally unestimable RPH-0 shape with a post-hoc wider-window label."
  - "Do not interpret rank persistence as expected return or top-Q membership as entry availability."
  - "Do not forward-fill missing dates, retain incomplete bars, shorten warm-up or bridge leader episodes across gaps."
  - "Do not pool phase rows as independent evidence or promote a descriptive hierarchy label into a production timeframe."
  - "Do not expose a product score before a real existing-owner consumer and authority review."
artifacts:
  - research/rotation_persistence/LEADERSHIP_PERSISTENCE_RPH0_ARCHITECTURE_FREEZE_2026-09-10.md
  - research/rotation_persistence/RPH0_FINDINGS_2026-09-10.md
  - research/rotation_persistence/results/result.json
  - research/rotation_persistence/results/report.md
  - research/rotation_persistence/evidence/open_pr_path_census_2026-09-11.json
  - research/rotation_persistence/evidence/mutation_self_review_2026-09-11.json
  - research/rotation_persistence/evidence/verification_2026-09-11.json
  - docs/superpowers/plans/2026-09-10-leadership-persistence-rph0.md
  - research/rotation_persistence/LEADERSHIP_PERSISTENCE_SECTOR_CONTROL_RPH1_PREREGISTRATION_2026-09-12.md
  - scripts/research/rotation_persistence/sector_control.py
  - scripts/research/run_sector_control_rph1.py
  - research/rotation_persistence/sector_control_rph1/result.json
  - research/rotation_persistence/sector_control_rph1/report.md
  - research/rotation_persistence/sector_control_rph1/verification.json
  - docs/superpowers/plans/2026-09-12-sector-rotation-daily-control-rph1.md
  - docs/superpowers/plans/2026-09-14-sector-rotation-daily-control-rph1-review-repair.md
  - agentos/handoffs/LEADERSHIP-PERSISTENCE-INTELLIGENCE-2026-09-14-RPH1.md
next_action: >
  Advance the separate Temporal Grain W1A external-evidence gate on PR #6803: recover a right-safe exact
  WMT chart recipe/export/lower-grain packet and an exact motivating-silver product/vendor/contract-or-
  roll/session packet, then run the existing deterministic harness. RPH-1 remains parked Draft/HOLD and
  may not become a production timeframe or consumer. RPH-0 PR #7064 remains a separate held carrier.
---

## Owner boundary

This workstream measures existing published theme-output archives and a bounded daily sector-ETF price
control. Sector Pulse, Rotation Events and Subsector Turn remain the live rotation-state owners.
GMI/ThemeState remain identity, membership and canonical state owners. Signal Commons retains family-
level holding-horizon/staleness decay. Temporal Grain retains exact chart-grain mechanics and any
lower-grain identity/utility study. Prophet Entry Truth retains strategy-specific availability. RPH-0
and RPH-1 write only research artifacts, tests, deterministic evidence and Agent OS records.
