# Native Rates scenarios — closed request and result preparation

## Assignment, ownership and source

This is a bounded implementation phase of the Chairman's 2026-11-14 native Macro / Market Ontology assignment, within WS:MARKET-OS / Macro issue #6819 and `NATIVE_MACRO_EXPERIENCE_2026-11-14.md`. The parent outcome remains a fully designed, integrated and production-proven native consumer product. This phase creates no runtime, queue, publication owner or capability registry.

The mathematical owner is PR #11269 at `66a8e4cf15ebcb9c3a470d182fce5c0e15cacf3e`, tree `865596633a4f7827524c5e1409fc5aeef86f7bb6`. All five paths in this contract phase were absent at that exact parent. It leaves the Rates composer/calculator, original tests, endpoint, shared reader and publisher untouched. Publication uses a separate GitHub-native child branch, `sol/native-rates-scenario-contract-20261114-c3`, with immutable blob/tree/parent readback and compare-and-swap. Do not update the armed core head to publish this phase.

Current governing pin remains Mastermind `199fd4f91ecc426b1d974eb3bf47f5162476cf24`; comparison with observed protected `df641640e6dc1ce5bc7717fa458b49ba4cb0e052` found no applicable law change. Direct principal work continues under the recorded NO_ELIGIBLE_PRE_EFFECT_WORKER / PRINCIPAL_JUDGMENT disposition. Native advisory work was source reasoning only, without implementation, test execution or approval impersonation.

Core #11269's 26 exact-head checks completed:21 success, four skipped and the explicitly inactive pilot context. `ci-gate`, all12 scheduled packs, active `ci-authority/main`, fences and contract-delta succeeded. Its Ready/open state, current head, author, absence of holds/comments/reviews and source compatibility were checked before one additive `merge-on-green` opt-in. The label and unchanged head were read back. This is an opt-in to the existing Macro controller, not a merge or production receipt. The controller retains freshness and admission authority.

## Consumer question and contract

The intended consumer asks how the 2Y/10Y Treasury slope changes under two chosen yield shifts. The new request schema is `ontology_scenario_request.v2`, for a future branch on the incumbent `/api/ontology/explorer/scenario/v1` route. It contains exactly:

- `schema` and exact method `rates_curves.two_yield_shift.v1`, which fixes the Rates/US scope;
- `expected_publication.manifest_sha256`, the raw manifest-byte digest already observed through the selected reader;
- `expected_publication.snapshot_content_sha256`, the canonical snapshot content digest; and
- `assumptions.us2y_bp` and `assumptions.us10y_bp`, normalized by the existing owner to integers in [-300,300], multiples of5.

Every object is closed. Zero is valid; booleans, strings, nonfinite numbers, unknown methods/versions and unsupported assumptions are refused. The client cannot supply yields, source qualifications, paths, dates, permissions or a reconstructed baseline. Expected digests are comparisons, not proof of identity, entitlement or source qualification. No new request/publication hash identity is introduced, and the browser need not implement the owner's baseline hash.

The declared `mastermind.macro_workspace_scenario_result.v1` now has a concrete closed JSON schema for the narrowly supported Rates method. It separates observed yields/spread from assumed yields/spread and their change. Explicit units distinguish yield percent from basis points. It retains the actual common observation date, both complete source identities and freshness/rights qualifications, the published-point basis, baseline ID and calculation ID.

The result lists the same unsupported effects as the mathematical owner: other tenors, term premium, policy response, credit/equity response, portfolio P&L and a future path. It remains display-only with all five authority flags false and all four write counters zero. Nothing in this phase reclassifies an illustration as a forecast or action recommendation.

## Pure serializer and publication boundary

`lib/macro_rates_scenario_contract.py` normalizes decoded requests and serializes a consistent owner calculation. The existing private transport remains responsible for its4KiB body bound, deadline and duplicate-key rejection. The new module performs no HTTP dispatch, filesystem access, wall-clock read, authentication, publication, cache, logging or persistence.

Serialization reuses `evaluate_rates_scenario()` to verify the supplied baseline, normalized assumptions, arithmetic, IDs and unsupported effects. Contradictory fields are refused rather than overwritten. Explicit scalar checks prevent Python's bool/int equality from making `display_only=1`, `can_execute=0`, false write counts or integral-float shift records look like proper owner outputs.

A public success result requires caller-supplied selected publication metadata: actual manifest digest/time, actual generation label, and the incumbent artifact fields. The path/region are fixed, bytes are a positive integer within the existing2MiB body bound, contract admission remains exactly1.0.0, generation labeling agrees with content, and artifact content agrees with the owner baseline. `artifact.sha256` retains its incumbent meaning as canonical content digest; it is not renamed or represented as a raw-file digest. The manifest clock must cover the common date and both included source reference dates, and its timezone components must be valid RFC3339 ranges.

This is structural consistency only. A fixture or caller-created mapping passing validation is not proof of served bytes, current publication, collection/release time, licensing, authentication or historical knowledge. The serializer does not manufacture missing metadata from a calculation. Before actual service admission the incumbent secured reader must provide the raw snapshot and matching metadata; the runtime must derive the baseline internally and recheck publication stability after evaluation.

Three mismatches remain distinct:

| Case | Pure result |
| --- | --- |
| Old client expectation; consistent new server calculation and receipt | `source_changed` |
| Calculation crossed with another content receipt | `invalid_rates_publication` |
| Same canonical content but a new raw manifest with old expectation | `source_changed`, while mathematical IDs remain unchanged |

Later service integration maps the first and third cases to the incumbent409 response. It must detect an actual before/after serving race itself; malformed internal metadata is not automatically evidence of such a race.

## Verification and limits

Local qualification:

```sh
PYTHONPATH=/workspace/scratch/613742d6b57a/qualification_deps:/workspace/scratch/613742d6b57a/qualification python -m pytest qualification/tests/test_macro_rates_scenario_contract.py -q
```

**98 passed**, with the existing anyio CallSpec2 deprecation warning. Fixtures write real sealed composer bodies and matching manifests into temporary directories, consume them through the incumbent `read_workspace()`, extract the owner baseline, calculate and serialize, and validate the closed schemas with format checking. They are local temporary publications, not authenticated or served-beta evidence.

Coverage includes exact hand-computable yield/spread outputs, zero/integral-float normalization, opposite shocks with600bp spread change, negative assumed yields, preserved stale source state, closed/missing fields, nonfinite/bool values, crossed actual fixture publications, republished metadata with unchanged mathematical identity, absent/malformed receipts, edited calculation/authority/write fields, wrong units and source identities, and detached output. Source review found two clock edges: a publication preceding the newer source leg, and Python normalization of malformed timezone offsets. Both were repaired and have executed regression cases.

The existing core's225 tests and hosted qualification belong to its own exact head. No unchanged core test is rewritten. New-head hosted checks and eventual actual service/browser acceptance are separate obligations. There is no new endpoint branch, UI control, snapshot-version emission or enabled capability here; all14 workspaces still publish `execution_available=false`.

## Custody and next action

Preserve #10614 at `078f4ab8aa8609a4eb484dd4490749bde49d486b`, its runtime/store writer, recorded holds and original unknown execution effects. Preserve #11246/#11265's selected-reader ownership and feature-base authority boundary. Preserve #11253/#11267's controller/catalogue holds. Do not replace the secured read closure with another filesystem loader or reconstruct a sealed snapshot from the projected consumer view.

The source-linked successor on Terminal #1524 is actively continuing Paper and Rates source provenance. Terminal child #1533 at `53f59b6d95ec5f06b4385eb31af025e46ea9689a` contains our separate Inflation/readability/pointer and browser qualification work; no parent write or handoff pickup is claimed. Macro #11258 moved from our earlier `a33a59e76a415c012c1072ba5bee2d7c9c3ac35c` to `5f464a227fd33799210bcfca294b8b63099d5c4a`, one successor commit by mastermindxryan adding Treasury source binding, its tests and a complete-kind label-scanner repair. Terminal #1524 likewise moved from `166a0c79456cb8edd64f76faec2edf3c8ff982a3` to `0fe5166fc208b78f61ac906df624f616fd282055`, with twelve changed paths and explicit source linkage. Its three new browser harness files overlap our child #1533 and require an owned-branch union before integration. Old source/CI acceptance is not substituted for either new head. This contract phase edits none of those paths.

Next: consume the core controller's actual disposition; once core is protected, reconcile this child onto the actual protected base and qualify its checks. Separately prepare exact1.0.0/1.1.0 snapshot-reader and result-publication admission while keeping current producer selection unchanged. Extract the qualified raw-read/recheck seam only after reconciling its current owner, then integrate the existing entitled private service, real409 behavior and explicit baseline reacceptance. Add native controls/assumed-vs-observed chart and table, cancellation across subject/baseline/departure, then enable only the supported Rates capability after that path works.

Paper completion, canonical registry/export order, native authenticated served-data journeys, alerts/Analyst attachment, revision/PIT depth and the original analytical denominator remain open. Contract preparation is a useful component result, not completion of scenarios or the parent redesign.
