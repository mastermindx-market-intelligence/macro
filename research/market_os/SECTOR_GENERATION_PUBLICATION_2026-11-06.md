# Coherent generation publication and readback

Status: integrated source candidate with parent repairs; no runtime activation, API binding or deployment acceptance.

Mission: [#10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Canonical source carrier: [#10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780).

## Ownership and source

This extends `scripts/vps_live_orchestrator.py`, the existing runtime owner. It does not create a second publication service, scheduler, lock registry or recovery controller. Production wiring must supply the real domain semantic validators and qualified input identities; the presence of a callback alone is not freshness qualification.

The parent recovered the terminal `bundle-final-01` candidate at commit `572aba29536243003ed8b6957ae313bf95a6107f`, verified its two-file patch SHA-256 `764da83139b2daac4e0c03f60c192c50629847618fd9e1f6fd2297d8ab96ce2f`, checked applicability against the original source carrier, and integrated it locally. The worker response is source evidence, not deployment or blanket acceptance. Three parent repairs below are part of the integration.

## Publication contract

Each domain retains private, immutable generation directories and one atomic current-selection file. The request identifies source revision, input identities and computed time separately from publication time. The publisher captures source bytes once, applies the supplied validators to the staged bytes, records exact members and digests, verifies the complete generation, and switches the selection only after the candidate passes. A domain lock and expected-current-content fence prevent concurrent or stale selection changes.

The selected pointer's domain, generation identity/directory, artifact rows and publication stamp must agree with its verified manifest. Leaf symlinks, unsafe names, unexpected members, oversized files, malformed pointers and corrupted selected generations are refused. Nonblocking descriptor reads keep FIFOs from hanging the reader. A damaged current selection is not treated as an empty store.

A directory-fsync failure and a pointer effect are different outcomes. After a failed selection write, the parent repair compares the complete observed pointer with both the intended target and the captured prior state, and reuses the canonical generation verifier:

- Exact verified target: applied, with durability unconfirmed.
- Exact still-verified prior, or the explicitly captured absent state: the prior selection is established.
- Any different, malformed, unreadable or inconsistent selection: uncertain; no retry or rollback is inferred.

Matching only a content-ID field is insufficient. In particular, an invalid directory binding carrying the target content ID cannot report successful publication.

The strict generation path requires directory fsync. Existing callers of `atomic_write_json` retain the actual previous file-fsync-and-rename behavior by default, with no newly introduced directory-fsync failure. The recovered candidate's claim that a best-effort directory fsync was pre-existing was incorrect; the parent removed that compatibility change.

## Rollback and read contract

`select_generation` uses the same owner, expected-current fence and verified publication path. It verifies matching retained candidates before selecting one. An orphan copy with a mismatched directory identity cannot shadow the genuine target later in directory order. Invalid directories are preserved, not deleted or repaired. Corruption of an unrelated unselected directory does not block a new publication; corruption of the selected generation or the requested reused generation blocks the affected operation.

`read_selected_generation(generations_root=..., domain=..., members=...)` captures one selection, verifies its complete bundle through the same verifier, and returns the exact member bytes it verified. It has no publication, repair, fallback, directory-creation or lock-file side effect. Unknown members and incoherent selections raise `SelectedGenerationUnavailable`. Returned manifest data is a detached private copy, not a claim of deep immutability. This is the only generation resolver to bind into the future API.

## Parent verification

At parent baseline `2b1ee3c6ec55ab8d47d4f61d38136834a5754cef`, the full `tests/test_vps_live_orchestration.py` run reported **153 passed and 3 failed**, with six existing temporary-directory cleanup warnings. All 14 added parent regression cases passed, as did the generation/read tests from the recovered candidate. The three failures are the pre-existing BEA/PCE defect-repair tests:

- `test_bea_known_feed_bound_state_repairs_only_from_successful_detail_page`
- `test_aged_governed_pce_defect_forces_feed_and_detail_repair`
- `test_aged_governed_pce_defect_failure_is_quarantined_and_bounded`

The parent loaded the exact baseline orchestrator and test source from git and reproduced those same assertion/KeyError failures. This establishes inherited failures in the observed workspace; it does not declare the entire suite green or waive hosted CI. Their production behavior remains with the existing release-publication owner.

The new cases exercise failed writes on both publish and rollback, invalid target pointer fields despite matching content IDs, a third valid selection mistaken for the prior, verified prior preservation, absent-versus-deleted pointers, an orphan shadowing the rollback target, and the actual legacy fsync contract. They use disposable files and fake failures; no live generation, provider or VPS service was mutated.

## Remaining integration gates

Bind actual source-cohort validators, history continuity and the complete Sector input chain; integrate the fixed-resource entitlement API and native consumer; register/repair CI through its incumbent owner; transfer legacy writers only with the deployment barrier and rollback policy in place; then prove the authenticated beta source-to-screen path and failure drills. Generation bytes being coherent does not prove that their economic inputs are fresh or that the complete Macro estate is migrated.
