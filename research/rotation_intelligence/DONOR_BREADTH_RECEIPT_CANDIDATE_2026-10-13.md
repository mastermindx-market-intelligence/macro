# Donor breadth comparison: bounded repair candidate

Operation: rotation-breadth-receipt-truth-20261013, a bounded engineering investigation under rotation-intelligence-architecture-20261012 / research PR #9035.

**Status: UNAPPLIED SOURCE PROPOSAL; synthetic function/caller checks pass. Not installed, not a project test-suite result, not production or financial-performance proof.**

## Defect and correction

Current `engine/rotation_events.py:into_strength` permits missing donor breadth as an optional input but then reports a measured-looking positive comparison:

```python
"breadth_above_donor": bool(breadth_donor is None or breadth_recv > breadth_donor),
```

The proposed receipt-only replacement is:

```python
"breadth_above_donor": (None if breadth_donor is None
                        else bool(breadth_recv > breadth_donor)),
```

Missing comparison evidence should be null, not true. The donor's optional-input event-admission behavior remains unchanged; this is not a new veto and does not adjust any threshold, score, rank, entry policy, lifecycle or notification. Nonfinite/out-of-range input policy is not expanded by this narrow proposal. Consumer compatibility with nullable comparison evidence remains an integration/review obligation.

## Exact source and proof

Base Macro commit: `317f2c06090d15347fe8117290a0e13ad2e2ad5b`.

Original complete rotation_events.py SHA-256: `099713025dd2873f2f8b770e43a19acc2e8b92bd84775aa3d46ab9c2d92eaa56`.

Complete candidate text after the unique string replacement, including the tested indentation: `02abe068ee869c62499b0c4374801841887aa75931932fc380af87eab3e63d67`.

Proof used AST-extracted exact source functions `into_strength`, `evaluate_cross`, `donor_state`, `blowoff_crash`, `turn_up`, `pair_confirm`, and the exact PARAMS/PARAMS_V2 constants. The isolated process supplied synthetic prices and breadth. It did not import the application's full runtime, initialize collectors, inspect financial data, call publication, or modify a source checkout. Original and candidate function namespaces were compared in the same process.

| Direct case | Candidate emits event | Comparison receipt | Admission vs original |
|---|---|---|---|
| Donor breadth absent | yes | null | unchanged |
| Donor breadth lower | yes | true | unchanged |
| Donor breadth equal | no | no event | unchanged |
| Donor breadth higher | no | no event | unchanged |
| Receiver breadth absent | no | no event | unchanged |
| Receiver breadth below threshold | no | no event | unchanged |
| Breadth history absent | no | no event | unchanged |
| Breadth history flat | no | no event | unchanged |
| Receiver has no qualifying price strength | no | no event | unchanged |

All nine direct cases passed. The missing-donor case independently established original true versus candidate null; every other receipt field matched. All eight other direct-case results matched the original exactly. The candidate serialized using strict JSON and round-tripped the unknown comparison as null.

Four additional `evaluate_cross` caller cases—absent, lower, equal, and higher donor breadth—also passed. Event/no-event outcomes and event types were unchanged. For the absent-donor caller, the sole changed field was `receiver.breadth_above_donor`; after replacing that field for comparison, the full original/candidate caller outputs were equal.

Studio process **88830** completed exit 0. There were **13 controlled cases**, not 13 passing repository pytest tests. No new statistical or trading claim follows from these tests.

## Source-workspace admission

A normal managed workspace acquisition was attempted once:

`mmx-workspace acquire --operation-id rotation-breadth-receipt-truth-20261013 --base-sha 317f2c06090d15347fe8117290a0e13ad2e2ad5b --lane web --repository macro`

Process 83088 returned **NOT_APPLIED / STORAGE_LOW_SPACE**. The follow-up existing storage owner reported, at 2026-10-13T02:21:46Z:

- mount: `/Volumes/Mastermind`;
- free bytes: 144,298,266,624;
- required reserve: 171,798,691,840;
- admission_allowed: false;
- policy SHA-256: `9cdebe5de9a9fd9f9317f2e71043e499fa7ebdbbc0aded4f0217eb6f268c232e`.

No workspace was created. No alternate internal-disk worktree, reserve reduction, deletion of someone else's files, primary-checkout edit, or hidden source write was attempted. The subsequent in-memory synthetic comparison was independent read-only research, not a workaround that created a source workspace. No source integration, hosted CI, merge or production change is asserted.

The small patch was retained directly because its exact effect could be independently compared at lower total overhead than dispatch; this does not establish a Fabric outage. The current Executive read showed no running Attempts, but that observation does not attest all native workers or grant source custody.

## Collision and reuse checks

The scoped rotation PR census found #8412 at `7afe6716a7cecb1fb506e047918223b9d7f7bc1a`. Its changed paths are `engine/subsector_rotation_alerts.py`, `scripts/build_rotation_events.py`, and `tests/test_rotation_events_china.py`; this candidate does not adopt those paths. Existing `tests/test_rotation_events_v2.py` is the proper test owner for source integration. Its network-free synthetic fixture and direct `into_strength` coverage were inspected; they should be extended rather than introducing another test framework. No all-repository custody absence is claimed.

## Exact next engineering action

When the normal workspace owner admits source work, recheck only the candidate's exact source/consumer/test dependencies and live writer state. Add a failing null-receipt test to the existing v2 test owner, apply the above receipt-only delta, run its actual focused suite plus relevant consumers, and obtain independent current-head review and normal source/production acceptance. Preserve event-admission parity. Do not remove broad risk gates or promote an early rotation signal as part of this patch.

The separate historical/live Risk Radar missing-breadth discrepancy remains unmodified. It needs its own canonical missingness decision and replay/model-identity qualification; combining it with this receipt-only patch would hide a materially different semantic change.
