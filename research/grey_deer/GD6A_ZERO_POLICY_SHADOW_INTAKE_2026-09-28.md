# GD-6A zero-policy shadow intake — R4 source qualification

**PARTIAL / BUILT_NOT_PROVEN. MISSION_COMPLETE:false. PR #8141 remains under
HOLD-FOR-SOL: no release, live policy, ranking, sizing or trading activation.**

Operation: `gd6a-us-shadow-intake-20260928-sol-001`, existing
`WS:GREY-DEER-RISK-INTELLIGENCE` / GD-6A. Parent #6817; R2 common inputs and
research adjudication5865326642; original R3 checkpoint5866759684; cumulative
R4 qualification on #8141/5867109469. The original CEO's UI work, H1/Cycle and
Seat B's #7107/#7094 remain separate. No source custody is transferred.

## Existing owner and scope

This implements the existing `prophet.market_eligibility/v1` after-rank sidecar,
not another detector, policy registry, identity plane, allocator, ledger or publisher.
Current native `engine/risk_envelope.py` supplies zero policies and episodes.
Nonempty, null or unsupported policy inputs remain UNAVAILABLE, never an invented
active rule. The native composer is unchanged.

Every row of the exact raw board's `/buy` array retains its original order, nullable
rank/lane and full candidate content. Array positions are exact-board pointers, not
issuer/security/episode identities. Off-board research stays with its existing owner.
The bound server-side view recomputes all sidecar semantics from independently supplied
source bindings. Hashes do not establish authority, entitlement or current freshness.

AVAILABLE / ELIGIBLE means only
`NO_MARKET_POLICY_CONSTRAINT_NOT_BUY_PERMISSION`. All eight downstream authority
flags remain false and `production_behavior=UNCHANGED`. B4, rankers, plans, personal
holdings, alerts and production publication are untouched. The explicit validity
window comes from the caller's actual owner; no calendar or financial TTL is invented.

## R4 implementation changes

### CI registration is complete, not still a materialization blocker

Commit `69601edd13829d6a32a5a51ffa07e781ff314ef3` changes exactly one existing
`synapse-read-gate` command in `.github/ci/legacy-jobs.yml`. It retains its six original
suites and adds both GD-6A test files. No new workflow or indirect test-discovery path.

The entire preimage was obtained and verified before replacement:

- Before: 1,033,991 bytes, Git blob `272a7fe415b82811f34946bbd50816ee7aee8069`.
- After: 1,034,080 bytes, Git blob `2542e6eeaf5a6f8a8737414bac22d49977534577`.
- After SHA256: `aecd1a59453419f0f7cfd9c478049596e8420aba4e5c34b718eba9b454d1ebee`.

The native authenticated gh route completed this new bounded operation. It did not
retry the earlier denied host inspection. Every original manifest line except the
single appended command is preserved. Registration does not prove CI executed it.

### Complete source inventory and clocks

Repair commit `3b759248902e49a597ed8c3e740f4bde52c8631b` closes a reproduced gap:
an optional contributing native source can have `as_of=null` while summaries say
FRESH and `all_on_session=true`. Checking only required clocks admitted that input.

The narrow FRESH-only shadow now verifies required/optional inventory disjointness,
fresh-set equality and uniqueness, integer source count, complete per-source keys
and every declared source clock. A genuine optional source with a qualified clock
remains usable. This is validation of the existing input contract, not a change to
native required-source policy or production recommendations. Missing evidence keeps
the intact board visible as UNAVAILABLE; it does not invent Calm or a liquidation.

### Descriptor-bound source reading

The stdout-only CLI now applies no-follow and nonblocking flags to the actual open,
then checks the opened descriptor is a regular file and enforces the size limit.
This rejects a final-component symlink swap, devices and FIFOs without waiting for
a producer. Descriptors close on success and failure. The guard concerns the opened
file, not a new filesystem authorization system; source hashes and owner bindings
remain mandatory. The CLI still creates no publication, scheduler or runtime store.

## Executed qualification and exact scope

Six new test methods bring the suite from63 to69. One method has six inventory
subcases; failure counts are not inflated into independent market observations.

| Run | Result | Scope |
|---|---|---|
| New tests against original implementation |69 methods,10 assertion failures,0 errors|Reproduces the gaps before repair; no market data.|
| Repaired source, conversation Linux/Python3.13.5 |69 PASS,0 failures/errors/skips|Actual modules and CLI, fictional observations/files.|
| Same repaired blobs, native Mac/Python3.14.7 |69 PASS,0 failures/errors/skips|Same distinct tests, not69 additional cases.|
| Native Agent OS validator at code head3b759248 |1,340 records,0 errors,755 warnings|Complete exact-candidate Agent OS store; not a full application checkout or CI.|

The native composer dependency remains30,642 bytes / Git blob
`3b0df2d426f50245142b943e38faf4996f96e995`, SHA256
`f0d9b1786b524f8092cfcaa194e8d590f1ff4b3db97ca8d2b0b2af5595331099`.
It was verified before import, not rewritten or mocked.

Repaired blobs:
- Module: `3ba4c0e5cd10db3e3787cd1e17a0f6469aae2f64`.
- CLI: `c2a48d8a2454a66ecf6c092b87eae08c239265ba`.
- Unit tests: `a08a2f78af5485e00bcacf210331d06c07b2345c`.
- Native compatibility tests: `43f5246a37618298dfdc7ab4d7cf10e20792f677`.
- Native69-test log SHA256: `966e986d33f05cc17ff7c1e70843bd306d3007c8d48292b0ee736bf6b5ed8c10`.

The Agent OS run used all1,347 exact files from tree
`ecd992f146bccee1e162d8780724e119bcdd88b1`, the complete native validator blob
`a0e69ea9bf279ea38eb89a7ade694c294cc42876` and actual program registry. It reused
1,297 locally available byte-matching files and fetched only50 differing versions.
An initial20-file materialization bound stopped before validation; the preserved
prefix was then completed under an explicit bounded50-file plan. No installed
source was modified and no substitute knowledge plane was created.

Warnings are retained:249 artifact-path and477 owned-path warnings in this isolated
metadata fixture,27 overdue reviews,1 active-but-complete and1 blocked-without-cause.
The path warnings cannot establish absence in the real checkout. The other warnings
remain organizational findings, not repaired by this PR. Log SHA256:
`b8dde406422249c1d017451a7758d4e56a623661c0cccd09e256f93bdfaa226c`.
This run predates the records-only R4 handoff refresh; its final exact-source rerun
receipt belongs on the cumulative qualification comment rather than a recursive
claim that a document validates itself.

## Remaining release gates

A compound native PR/workflow/check-status inspection was blocked before dispatch
by the tool safety layer. It was not retried through another carrier or delegated
as a proxy request. Current CI execution/conclusion is therefore not claimed here.
This is an action-scoped observation limitation, not proof of a GitHub outage.

The exposed Executive ingress reports readonly. No review Job or worker was
submitted, started or inferred from available-worker counts. Independent review
remains outstanding; author tests and a changed account label are not independence.

Keep HOLD until independently reviewed exact source, owning-suite/registered CI
execution, current-base integration and remaining release conditions are proved.
Do not arm automatic merge, repeat an unchanged source proof for activity, or
reopen a protected study. Source-layer tests are not authenticated user proof.

## Next product capability

After source acceptance, connect the existing frozen origination-board receipt
and settled envelope through the normal after-rank publication owner. Prove
unchanged board/rank/plans, lossless shadow counts, the next ordinary refresh and
existing counterfactual accrual. No duplicate scheduler, store or grader.

Actual risk-off/de-risking recommendations require separately supported,
individually authorized policy records with scope, version, clocks, expiry,
repair and kill conditions. Original Grey Deer promotion and mandate requirements
remain; R2's research budget does not supersede them. This zero-policy source slice
is not a completed no-new-long filter or a forecast-performance result.

Protected Skillpack: Mastermind `e981ec1b0b6e3bd47e267b6abc92adee4a94d6a8`,
compatible1.0.1/bootstrap1. The exact next step is registered qualification and
independent review of this same PR, followed by the existing publication connection.
