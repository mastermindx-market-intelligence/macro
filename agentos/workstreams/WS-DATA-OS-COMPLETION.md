---
key: DATA-OS-COMPLETION
title: Canonical market data and corporate-action integrity — Data OS completion
objective: >-
  Complete the existing equity-data contract through three real consumers (Terminal
  daily OHLC with a narrow data-origin readout, DataWorkspace canonical read, basket
  membership/price composition) under one declared view contract. Done when all three
  consumer positives, the declared market/population contract, independent
  numerical/temporal/access proof, installed production reads and
  correction/recovery/second-cycle evidence exist on main and live.
status: active
program: terminal-market-data
repos: [macro, terminal]
owner: Fable Meta-CEO seat (Data OS completion programme, Chairman delegation 2026-10-13)
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - lib/dataos/read_contract.py
  - lib/dataos/price_views.py
  - lib/dataos/basket_read.py
  - tests/test_dataos_read_contract.py
  - tests/test_dataos_read_coherence.py
  - tests/test_dataos_reference_read.py
  - tests/test_dataos_price_views.py
  - tests/test_dataos_price_revisions.py
  - tests/test_dataos_action_projection.py
  - tests/test_dataos_rights_matrix.py
  - tests/test_dataos_coverage.py
  - tests/test_dataos_quality_inspector.py
  - tests/test_dataos_basket_read.py
  - tests/test_dataos_support_matrix.py
  - tests/verification/**
  - research/data_os_completion/**
  - research/DATA_OS_COMPLETION_CONTINUATION_HANDOFF_2026-10-13.md
decisions:
  - DEC:DATAOS-D00-SEMANTIC-DECISIONS
  - DEC:DATAOS-D00-A1-VENUE-CLOCK-UNITS-SCOPE
  - DEC:DATAOS-VIEW-CONTRACT-SIDECAR-IS-A-NIGHTLY-EMITTER
  - DEC:DATAOS-D00-D3-ABSENT-VS-UNRESOLVED
waves:
  - id: d00-freeze
    title: Freeze the six semantic decisions (D00)
    status: done
    pr: 9133
  - id: identity-time
    title: Identity adoption, reference snapshots, continuity refusal matrix, three read modes, read coherence (G01, I01-I03, T01-T02)
    status: done
    pr: [9135, 9136, 9142, 9143, 9144]
    depends_on: [d00-freeze]
  - id: math-registry-rights
    title: Baseline and discriminators, dataset registry matrix, rights/leakage matrix, action projection and split/distribution views (Q00, R00, K01, P01-P04)
    status: done
    pr: [9147, 9148, 9150, 9152, 9154, 9156, 9168]
    depends_on: [d00-freeze]
  - id: consumers
    title: Retained views, D00.A1 venue clock + declared units, price-ladder opt-in canonical read, coverage, agreement inspector, view-contract sidecar emitter, Terminal / DataWorkspace / basket reads, support matrix (P05, P06, C01-C04, U01-U04, M01)
    status: done
    pr: [9179, 9184, 9185, 9188, 9210, 9218, 9220, 9226, 9234, 9236, 9237, 9241, 9539, 9555]
    depends_on: [identity-time, math-registry-rights]
  - id: verification-acceptance
    title: Independent oracle, adversarial access, matched workload, end-to-end journey, corrections, recovery, source review, install and cycle plans (Q01-Q03, F01, A01-A03, R01-R03)
    status: done
    pr: [9273, 9275]
    depends_on: [consumers]
  - id: c00-closeout
    title: Live verification on the served product, second nightly cycle, acceptance matrix closeout (C00)
    status: in_progress
    depends_on: [verification-acceptance]
next_action: >-
  (1) R03 / consumer C production proof: after PR #9556 merges, bind ONE bounded watcher (≥150 s) on the next daily.yml nightly and, when its push step succeeds, verify `git show origin/main:data/stocks/_view_contract.json` plus the generation invariants cycle 1 → cycle 2 (same dataset_version lineage, bar_count monotone, no repriced history); never dispatch daily.yml. (2) DONE — Q02-F1 #9654 (b300469398ca) and gap A1 #9709 (fc44c814c192) merged and land-proofed. (3) DONE — main RIG red healed by #7100 (b91514a3); main ci.yml 39245121273 @ff1b80af0f5e completed SUCCESS, clearing the C04 / wire-5 / #9273 CI-authority heads. (4) D00.D5/D6 generation producer (matrix row GEN): owned by Sol operation `rs-pullback-initial-generation-r13-20261013-c1` (WS:LIVE-ENTRY-RADAR; held R25 writer-exclusion DRAFT PR #9617 on `scripts/build_security_master.py` + `tests/verification/test_a03_recovery.py`, cumulative evidence on #8649); consume its landed lineage, never build a competing publisher. Then flip c00-closeout and this workstream to done. Never redeploy Terminal #996; never re-dispatch a concluded baseline.
landmines:
  - "WS:TIINGO-DATA-OS owns lib/dataos/tiingo_*.py, collectors/tiingo_archive.py, scripts/tiingo_*, docs/tiingo-evidence/ and the twenty PROPOSED Tiingo registry rows; this workstream never touches them."
  - "lib/dataos/__init__.py has exactly one writer per wave (the identity+time orchestrator in wave 1; the seat from the wave-2 wiring #9168 on); parallel export wiring collides on the shared export list."
  - "engine/price_ladder.py S10 (false ADJUSTED equivalence) is a documented legacy defect; the consumer wave adds an opt-in canonical read and leaves legacy bytes unchanged."
  - "Terminal PR #955 is held and never touched; Terminal release acts and any live/VPS act are seat-only."
  - "DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT: CN limit arithmetic stays RAW; no repricing of historical books anywhere in the programme."
  - "A fabric lane on a claude/* branch inherits the ship-loop Stop hook and will push and arm; lanes run on lane/* branches and only the orchestrator pushes to claude/dataos-<pkg>-2026-10-13."
  - "R02 m3/m6/m8 (UTC as_at day, undeclared currency, consumer-A venues/basis) are recorded limitations RULED by D00.A1; consumer lanes implement P06 exactly as written, never a local variant."
  - "Terminal: any edit to terminal/lib/i18n.tsx, terminal/app/globals.css, terminal/components/ChartPanel.tsx or terminal/lib/dataCache.ts turns every pr-crops EVIDENCE.yml lock that pins it RED; reconcile per the house form (dated source-hash-reconciliation comment + new sha256 rows, PNG preserved; real recapture where the surface renders the changed region) and run the FULL npm test shard, never targeted files."
do_not_redo:
  - "D00 (PR #9133, squash 52af4108676b, 2026-10-13) is accepted and frozen; re-open only on a material invalidator (contradicting evidence, changed contract, explicit authority reversal)."
  - "Identity candidate PR #8637 is adopted by cherry-pick -x in package I01; do not re-author identity continuity or recommission its GMI sidecar changes."
  - "The route proof (G01) is one lane, one round; do not replay a blocked preflight."
artifacts:
  - research/data_os_completion/2026-10-13/C00_CLOSEOUT_MATRIX.md
  - research/data_os_completion/2026-10-13/R02_RECEIPTS.md
  - research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md
  - research/data_os_completion/2026-10-13/D00_A1_AMENDMENT.md
  - research/MASTERMIND_DATA_OS_ARCHITECTURE.md
  - research/MASTERMIND_DATA_OS_V1_IMPLEMENTATION_PLAN.md
  - research/DATA_OS_COMPLETION_CONTINUATION_HANDOFF_2026-10-13.md
---

## What this is

The Chairman's 2026-10-13 masterplan "Canonical Market Data & Corporate-Action
Integrity — Data OS completion" (plan text PR #9121). The existing Data OS library
(`lib/dataos/`) has identity, temporal, price, registry, nulls, quality and web-workspace
surface but no consumer that reads it under a declared contract. This workstream completes
the contract through three real consumers and proves it end to end.

## Hierarchy and delegation

Fable Meta-CEO seat (owner) → native Opus orchestrators (at most two concurrently) →
Mastermind Subagent Fabric lanes on the M2 (B-kit `ext/sub.sh`, GLM ladder
`glm-5.3-flash` leaf → `glm-5.3` frontier labor / review / operator → local `grok` →
remote `cursor`) → optional worker lanes under one `glm-5.3` operator when a package carries
two or more parallel worker lanes under one frozen spec. The seat may also delegate directly
to the fabric. Lanes commit on `lane/*` branches and never push; orchestrators judge by
artifact, push to `claude/dataos-<pkg>-2026-10-13`, and open DRAFT PRs; the seat marks
ready, merges, verifies landing and performs every live/release act.

## Consumers (D00.D6)

- A — Terminal daily OHLC (`charting-app` `ingest/build_universe.py` → `terminal/lib/dataCache.ts`
  → `terminal/components/ChartFrameBar.tsx` status area): a narrow data-origin readout that
  serializes the Macro view contract, never a Terminal-local re-derivation.
- B — DataWorkspace canonical read (`lib/dataos/web_api.py::validate_request` →
  `lib/dataos/web_workspace.py::DataWorkspace`), request carries the ReadRequest fields,
  response bound stays 131072 bytes, `statv1:` token unchanged.
- C — basket membership / price composition (`engine/basket_membership_pit.py` readers),
  one ReadRequest/ViewContract binding membership, identity and price; the `pit=False`
  fallback can never fund a historical claim.

## Resume

Read `research/DATA_OS_COMPLETION_CONTINUATION_HANDOFF_2026-10-13.md` (wave map, package
→ branch map, acceptance rules, seat-only acts, current rung) and the latest
`agentos/handoffs/DATA-OS-COMPLETION-*.md` before any act.
