# Lane D Exact-Head Acceptance — Lane F

**Lane F operation:** `theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001`  
**Lane D operation:** `theme-intelligence-d-entry-and-stock-routing-20260919-sol-001`  
**Candidate head:** `0ce6bbf54b9c623891274e278a6ff581b602bfef`  
**Candidate tree:** `85fb619c32fea4e0559d4aa6a0fa1a226966aefc`  
**Latest protected main reviewed:** `fa85fb5de1c5a2afdb3a2425ebcbf8c4f2f389e2`  
**Latest integration tree:** `fd12a6f4fa8b32e2c3861a9fd7d6964ae94fb673`  
**Disposition:** **SEMANTIC PASS / REQUEST_CHANGES ON CARRIER ADMISSION**

## Independent result

Lane D's bounded product contract passes independent Lane F evaluation. The exact current-main integration tree compiles and the owning suite reports **55 passed** with five pre-existing temporary Chromium cleanup warnings.

Real committed-artifact proof preserves the incumbent Board V2 population and order: `entry_open=[(1, AMD),(2, DOCN)]`, `setting_up=[]`.

- AMD remains a stock-qualified setup with group `EXTENDED`, confirmation `UNCONFIRMED`, and no invented trigger/zone/invalidation/chase levels on the `setups.json` fallback.
- ADI remains qualified with `PENDING` confirmation, owner-supplied levels, and separate `EXTENDED` group risk.
- NVDA is `DESCRIPTIVE_ONLY_MEMBER_INELIGIBLE`; parent Semiconductors `ENTRY-NOW` is group-only context and is not positive stock-entry provenance.
- `may_rank`, `may_gate`, `may_size`, `may_escalate`, and `may_trade` remain false.

A stale-confluence mutation was run through the actual `GroupContext -> Board V2` path. GroupContext marks the confluence source degraded and the additive member context fails closed to descriptive-only. A repo usage census shows the lower-level `EntryContextSource` is used in production only by `GroupContext`; other direct calls are tests.

Protected main moved seven commits beyond the prior integration base with zero Lane D-owned or direct relevant path overlap. A fresh conflict-free integration tree was built and rerun rather than rebasing the source branch.

## Blocking finding — TI-D-AGENTOS-RECORD-001

The committed Lane D handoff has YAML frontmatter, but it is not a valid current Agent OS handoff record. Fences run `35502935108` and CI run `35502935516` report the record is missing required fields including `workstream`, `session`, `model`, `mission`, `state_before`, `changed`, `verified`, `unverified`, `unresolved`, `next_actions`, `do_not_redo`, `danger_areas`, and `ended_because`.

This is records/admission failure, not a Lane D entry-semantics failure.

### Smallest accepted repair

The Lane D source writer should repair only:

`agentos/handoffs/THEME-INTELLIGENCE-LANE-D-ENTRY-ROUTING-2026-09-20.md`

into the existing Agent OS schema on PR #7508. Do not change product semantics merely to obtain green checks.

If the repair is records-only, all reviewed semantic blobs remain identical, and current-main movement remains material-path disjoint, Lane F classifies semantic review reuse as **allowed**. Rerun Agent OS validation, fences, and current integration proof; a full semantic rereview is required only if semantic/product or governing material dependency bytes change.

## Acceptance boundary

Lane D is `BUILT_NOT_PROVEN`. No merge, deployment, browser proof, production acceptance, rank/gate/size/trade authority, or parent-program completion is claimed. Lane A remains the integration lead.
