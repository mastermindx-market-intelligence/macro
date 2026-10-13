---
key: EVAL-OS-EVIDENCE-VIEW
title: Intelligence Evaluation OS — T7 per-engine evidence scorecards + T8 CEO evidence view
objective: >
  Extend the existing read-only Intelligence OS admin surface so an operator can answer,
  per canonical T1 engine, whether its evidence is Validated, Accruing, Ungraded by design,
  Degraded, or Disproven, with every claim tied to its lawful ruler/basis and with an honest
  global CEO view ranked by evidence strength rather than headline performance. The Validated
  set may be empty. No score store, second admin product, promotion authority, engine registry,
  claims ledger, monitor or queue may be created.
status: active
program: qualitative-intelligence
repos:
  - macro
owner: Eval-OS program (CEO Sol; bounded operator implementation)
class: build
blast_radius: reversible
ambiguity: specified
depends_on:
  - "WS:EVAL-OS-T1-ENGINE-REGISTRY"
  - "WS:EVAL-OS-OUTPUT-HEALTH"
decisions:
  - "DEC:EVAL-OS-RECOVERY-ARCHITECTURE-FREEZE"
waves:
  - id: A1
    title: T7 per-engine evidence scorecard + T8 global CEO view
    status: in_progress
    next_action: >
      Finish exact-head verification, independent review and authenticated production proof for
      the derived Intelligence OS evidence view, without persisting a new score state.
next_action: >
  Continue the existing held PR #6651 under current Chairman assignment and root
  01a1333d-b0c0-7f33-9259-dd718391d9e4. Complete qualified evidence, coherent selected-store
  reads, dark/light EN/ZH experience, exact-head CI/review, authorized hold release and
  authenticated normal-release proof. Historical receiver labels do not imply a live writer.
  Natural accrual remains independent and must remain honestly qualified.
owns_paths:
  - admin/intelligence_os.py
  - tests/test_admin_intelligence_os.py
  - engine/intelligence_registry.py
  - engine/output_health.py
  - tests/test_output_health.py
  - agentos/workstreams/WS-EVAL-OS-EVIDENCE-VIEW.md
landmines:
  - "T1 output_class is the selector; null stays null and may not be guessed from engine name."
  - "T4 health is evidence/context, not performance or promotion authority."
  - "Qledger readiness is advisory; existing qual-ladder/species/prereg/gauntlet owners remain authoritative."
  - "Clock bases that cannot legally pool may be displayed side by side but never collapsed into one evidence statistic."
  - "Validated may be empty; do not manufacture a positive category to make the UI look healthy."
do_not_redo:
  - "No second engine registry, score/evidence database, generated score artifact, health monitor/store, promotion service, admin product or work queue."
  - "Do not rank by hit rate, return, or model confidence without the frozen legality/maturity contract. Evidence strength is the ordering dimension."
  - "Do not reopen H1/T4. H1 is terminal PROVEN_LIVE; A1 consumes it."
  - "Do not block A1 on E1 natural-time completion. Surface incomplete accrual honestly."
artifacts:
  - research/EVAL_OS_RECOVERY_ARCHITECTURE_FREEZE_2026-08-27.md
  - agentos/workstreams/WS-EVAL-OS-OUTPUT-HEALTH.md
  - agentos/workstreams/WS-EVAL-OS-T1-ENGINE-REGISTRY.md
  - research/EVAL_OS_CONTINUATION_2026-10-12.md
---

## Opening reconciliation — 2026-08-28

H1 is terminal and `WS:EVAL-OS-OUTPUT-HEALTH` is `done`/`PROVEN_LIVE` for the bounded T4 admin
health capability. The recovery freeze explicitly unlocks A1 after H1 and permits it to consume
E1 accrual state honestly. E1 remains active because current Macro main still lacks durable
`stock_desk` and `thematic_desk` general evidence-clock receipts; that does not block this derived
answer layer. A1 is therefore a separate operation/carrier, not a continuation of the H1 watcher.

## Current source reconciliation — 2026-10-12

PR #6651 remains the sole held draft carrier. Its historical recovery operation ended with Sol ACCEPTED/STOP; the prior preflight session completed and its65aba5 push was reconciled. The current assigned principal inspected actual writers/effects and continues in that existing allocated tree. Merge e125e270fe09 integrates main a8e054ce; source repairs and tests remain in progress, not production acceptance. The former missing-thematic-clock statement above is historical: current main contains the original2026-08-31T05:01:42.762963+00:00 receipt. No clock was reissued. See the continuation record for precise unfinished acceptance.

## Current consumer qualification — 2026-10-13

Latest delta: published213d5f29 source/browser/resource review is accepted. Its hosted CI found16 missing dependency-path entries across7 curated jobs; the same predicate failed contract-delta and pack0 while11 packs passed. Current main595a8927 was integrated cleanly, exact coverage was repaired without changing job commands/gates, and both affected controls pass locally. All21 qualified nonmanifest application/test hashes remain unchanged. Real200% browser zoom and observed reduced motion now pass their named scoped checks; the42-state matrix is unchanged. The repaired published head still requires concluded hosted CI and the existing reserved release/live/operator gates. See the current frontier at the top of the acceptance record for chronology and the original daily collector-versus-workflow distinction.

The current source consumes bounded, dated owner readiness and recorded display-only confluence findings. Exact unique T4 paths associate context with canonical engines; unknown/ambiguous rows and unavailable numeric verification stay visible. Final malformed-row, null, fraction and partial-empty controls pass. Existing shared API/UI writer custody transferred explicitly to root after all product test sessions reconciled. Independent source-bound synthetic browser acceptance now passes all eight theme/language/viewport contexts and42 actual states; the65-file canonical bundle has zero receipt/manifest findings. Whole-corpus-sized647-artifact local synthetic capacity is qualified at446MiB maximumRSS, preserving a1.293s cache metadata cost; VPS/client latency remains unproved. Held-PR current-head CI/review, reserved release and normal authenticated production/operator acceptance remain pending. See research/EVAL_OS_ACCEPTANCE_RECORD_2026-10-12.md, mockups/evidence/intelligence-os-a1-20261012/EVIDENCE.yml and the continuation; no authority or completion flag changed.
