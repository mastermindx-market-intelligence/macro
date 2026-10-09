---
key: FACTOR-ATLAS-S1
title: Factor Atlas — factor definitions and reproducible historical measurement
objective: >
  Deliver the Chairman's Session 1 research and an additive native read-only basket
  measurement slice, with distinct current-roster and point-in-time histories,
  deterministic computation, explicit source/correction/coverage evidence and an
  accepted consumer integration before any product release. This child does not
  redefine the incumbent Factor Intelligence programme or GMI ownership.
status: active
program: factor-intelligence
repos: [macro]
owner: sol
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - engine/factor_atlas_read.py
  - engine/factor_atlas_sources.py
  - contracts/factor_atlas_read.v1.schema.json
  - scripts/factor_atlas_read.py
  - tests/test_factor_atlas_read.py
  - tests/test_factor_atlas_sources.py
  - tests/test_factor_atlas_contract.py
  - tests/fixtures/factor_atlas/
  - research/factor_atlas/session1/
waves:
  - id: S1-RESEARCH
    title: Publish the original research package with exact preservation receipts
    status: done
    pr: 8680
  - id: S1-NATIVE
    title: Native read-only measurement, incumbent-owner bridge, schema and executable proof
    status: in_progress
    pr: 8680
  - id: S1-SOURCE
    title: Qualify actual price, identity, collection and correction inputs for three house baskets
    status: todo
  - id: S1-CONSUMER
    title: Accept and prove the additive Macro and Terminal consumer interface
    status: todo
next_action: >
  Complete exact-source native qualification and review in Macro PR 8680; preserve
  unavailable rights, action vintage and PIT evidence instead of inventing them.
  Then bind accepted owner inputs and the incumbent consumer interface. Do not merge,
  deploy or expose the candidate merely because fixture tests or CI pass.
artifacts:
  - research/factor_atlas/01_FACTOR_MODEL_AND_PIT_RESEARCH.md
  - research/factor_atlas/session1/PUBLICATION_RECEIPT.json
  - research/factor_atlas/session1/IMPLEMENTATION_STATUS.md
  - research/factor_atlas/session1/NATIVE_PILOT.md
  - contracts/factor_atlas_read.v1.schema.json
landmines:
  - Current-roster history is not an historical investment decision or strict PIT fallback.
  - A displayed window must not reset weights from the immutable construction inception.
  - A file hash is not entitlement, corporate-action vintage or a public/knowledge clock.
  - Native schema and necessary reference checks are not source-owner admission or live acceptance.
  - Parallel capital-pressure and Session 4 workspaces retain their own custody.
do_not_redo:
  - Preserve the 23 verified original research manifest entries; the six raw-log omissions are explicit.
  - Do not create a new graph, membership, identity, ThemeState, rights, portfolio or publication authority.
  - Do not edit research/factor_intelligence, engine/theme_graph, incumbent basket/style math or portfolio decisions from this slice.
---

## Current commission and evidence

Current direct Chairman instruction: **save to GitHub, initiate the project and implement it**.
Implementation owner record: [Macro #8676](https://github.com/mastermindx-market-intelligence/macro/issues/8676).
Carrying candidate: [Macro PR #8680](https://github.com/mastermindx-market-intelligence/macro/pull/8680), **DRAFT / HOLD-FOR-SOL**.

The existing `factor-intelligence` semantic programme owns factor definitions and validation evidence. This is a bounded child measurement workstream under that existing programme, not a new ontology, selection engine or replacement for Fable's company-conditioning contract. GMI, Data OS, basket/price owners and incumbent consumers retain authority.

The native adapter and owner bridge are **BUILT_NOT_PROVEN** at product level. Research publication is complete on the PR branch; this record itself is not an accepted main-branch registry update until normal source acceptance. No Executive Job, provider worker, live user feed, deployment or authenticated browser proof is claimed.

Managed operation: `factor-atlas-s1-native-20261009-c1`; branch `sol/web-factor-atlas-s1-native-20261009-c1`. The cumulative source and proof frontier is `research/factor_atlas/session1/IMPLEMENTATION_STATUS.md`; source/PR/CI evidence remains GitHub-owned, while runtime lifecycle remains Executive-owned.
