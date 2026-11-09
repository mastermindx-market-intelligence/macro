# Paper workflow expansion — 9 November 2026

## Result

This continuation adds **24 editable native boards across four Paper files**: 12 Catalyst, 8 Intraday, 2 Search and 2 Watchlists. It also corrects one existing AI builder board in a fifth file. It completes the planned native workflow expansion and source-matched builder packet. It does not complete the broader Macro #10617 implementation programme or establish production acceptance.

The previous Breadth, Revenue and OS navigation amendment remains intact at commit `5455ebfef331b4f01f1ddd9b580b4f6d3cd2b9dd`. This separate packet extends the same [PR10894](https://github.com/mastermindx-market-intelligence/macro/pull/10894) and branch `design/paper-breadth-navigation-20261109-c2`.

## Open the current work

| Paper entry | New boards | What changed |
|---|---:|---|
| [Catalyst Product](https://app.paper.design/file/01M6Y2VTQBVC9NA39HNG1DYWFH/p-6-0) · [Review](https://app.paper.design/file/01M6Y2VTQBVC9NA39HNG1DYWFH/p-7-0) · [Build](https://app.paper.design/file/01M6Y2VTQBVC9NA39HNG1DYWFH/p-8-0) | 12 | Four-case workbench, separate evidence journeys, source/version recovery, two themes and mobile, builder/motion board |
| [Intraday Product](https://app.paper.design/file/01M6Y2QK8TQZRN8T4BHG10CJXT/p-3-0) · [Build](https://app.paper.design/file/01M6Y2QK8TQZRN8T4BHG10CJXT/p-4-0) | 8 | Compact scan with five names, evidence and all classes, explicit missing inputs and source basis, EN/ZH and two themes |
| [Search recovery](https://app.paper.design/file/01M6Y31C449F02KGRNPGK94Q8D/p-4-0) | 2 | Companies unavailable while Tools work; query and useful next actions retained at EN/ZH320 |
| [Watchlists empty state](https://app.paper.design/file/01M6Y309YH7PJZMF23R7EDH3CM/p-4-0) | 2 | Qualified empty owned inventory, useful Monitor/return actions, no unusable Save/chooser; EN390/ZH320 |

The [AI builder correction](https://app.paper.design/file/01M3P1QEHS5XXQY85BJT6QR2E1/p-9-0) clarifies saved-case resume versus current unsent-draft preservation and the Stay / Discard boundary. Existing AI product screens remain.

All 81 pre-existing product/build boards in these four files remain available: Catalyst 24, Intraday 10, Search 20 and Watchlists 27. The other writer's AGENT README pages remain first and unchanged. Current product/build/state pages precede older references. No original board was archived or deleted.

## Capability delta

Before this pass, long card/report layouts consumed the initial scan, selected-case evidence lacked the new explicit destinations, and the narrow shared-state gaps were not represented by these focused screens. The new work separates fast selection from deep evidence, keeps exact return destinations and gives builders a concrete state contract.

The design changes also expose real source limits rather than implying unsupported capabilities:

- Catalyst has no verified issuer-to-NCT join for its fictional companies. Those saves stay unavailable, and eligible real-trial saves continue through the existing R2 owner.
- Intraday mixes mutable retained inputs and source clocks. Its new static specimens say Recorded example; current/historical behavior requires the qualified basis described in the build plan.
- Search uses one shared query across scopes. Companies and Tools retain independent service state; no extra query store is invented.
- Empty owned inventory cannot suppress an existing unknown-save recovery or turn shared-with-me lists into writable destinations.

These are native design fixes and source findings. Runtime logic repair, authenticated browser proof, merge and deployment are separate outcomes and were not performed.

## Read the implementation contract

1. [BUILD_PLAN.md](BUILD_PLAN.md) — owners, data meaning, sequence, interactions, motion and discriminating proof.
2. [CATALYST_WORKFLOW.md](CATALYST_WORKFLOW.md) — all 12 native IDs, case-specific evidence, manual-save and source-version rules.
3. [INTRADAY_WORKFLOW.md](INTRADAY_WORKFLOW.md) — all 8 native IDs, exact source findings, missingness and current/recorded qualification.
4. [SHARED_STATES.md](SHARED_STATES.md) — four narrow boards, exact guards, query/account/return behavior.
5. [VERIFICATION.md](VERIFICATION.md) — observed native/source proof, retention, static motion checks and limits.
6. [AI_AND_COMPARISON_AUDIT.md](AI_AND_COMPARISON_AUDIT.md) — exact inspected coverage, retained screens and the AI builder correction.
7. [CONTINUATION.md](CONTINUATION.md) — scope, durable refs, do-not-redo and next implementation action.

The [motion specimen](motion_specimen.html) contains the original example illustration and existing Signal Ink assets, with a case transition and reduced-motion controls. Browser execution has not been proven.

## Evidence map

- `paper/`: 25 current JSX exports (24 new boards and one corrected AI builder) with native node IDs.
- `screenshots/`: 25 complete-board screenshots plus four UI-only crops from native capture.
- `evidence/*.native_census.json`: exact page/node inventory and original-board retention.
- `evidence/paper_operations.json`: 229 observed adapter mutation responses, each APPLIED_RESPONSE_OBSERVED; no unresolved native effect.
- `evidence/source_characterization.json` and `intraday.source_functions.json`: pinned Macro source findings.
- `evidence/terminal.source_excerpt.json`: root-inspected current Terminal source excerpts with blob identities.
- `evidence/motion_static_validation.json`: syntax, asset/hash, series and no-network/storage checks.
- `MANIFEST.json`: SHA256 and byte size for every packet file other than the manifest itself.

Source pins: Macro `cf07e7a73334c646a09c043647c43e43ee6e4060`; Terminal master `1c0bf028cf72539a4d3fcb17fa137ee474d764f9`; reused procedure pin `494d095813dad415938800fa0e4d2719497738fa`.

The final exact commit and committed-byte readback receipt are recorded in PR10894 after publication. The packet is a reviewable source candidate; green CI would not by itself establish runtime acceptance.

