# Native Rates scenarios — pure calculation phase

## Assignment and scope

This is an implementation phase of the Chairman's 2026-11-14 assignment to complete the Market Ontology Macro experience as a native shared-shell product. It belongs to WS:MARKET-OS / Macro issue #6819 and the existing `NATIVE_MACRO_EXPERIENCE_2026-11-14.md` subplan. It does not create a new programme, publication owner, runtime, scheduler, admission service or capability registry.

Governing Mastermind source: protected master `199fd4f91ecc426b1d974eb3bf47f5162476cf24`. Source base: protected Macro main `8dd7689db40d27594161eb1a124553bfc285280f`. The original Rates composer and its existing test module are byte-identical to the earlier inspected protected base `86098fc3a0739711ca8290f58541c3d7e913f81c`; the contract, publication-prior helper, snapshot schema and AGENTS.md were also verified unchanged. The exact source preimages are:

| Path | Git blob |
| --- | --- |
| `engine/market_os/macro_workspaces/rates_curves.py` | `09eb20d1c2855086fa2d9ee7bb3c78ef09362adc` |
| `tests/test_macro_workspace_rates_curves.py` | `50f16badd8e48708eb3e4c9202901e493266a162` |

Publication uses the assigned GitHub-native carrier and isolated branch `sol/native-rates-scenario-core-20261114-c3`, with exact tree/parent/blob readback and compare-and-swap. Fabric was unavailable before effects; direct principal implementation proceeds under the already recorded NO_ELIGIBLE_PRE_EFFECT_WORKER / PRINCIPAL_JUDGMENT disposition. Native advisory work was reasoning only. No production write is implied by this source phase.

## User capability being enabled

The eventual Rates workspace should let a member ask what happens to the 2Y/10Y Treasury slope if either yield changes by a specified number of basis points. This phase implements the bounded calculation and the qualification of its observed input. It does not expose controls, return an HTTP result, or claim that the consumer journey exists.

The two independent assumptions are `us2y_bp` and `us10y_bp`: each ranges from -300 to +300 basis points in steps of 5. Zero is valid. Integral numeric floats normalize to the same identity as integers. Booleans, strings, nonfinite numbers, extra fields, client-supplied baseline values and unsupported assumptions are rejected. The direct output contains the assumed two yields, observed and assumed 2s10s spreads, and their mechanical difference. Opposing endpoint shocks can change the spread by 600 basis points. Negative assumed yields are permitted. Finite numerical magnitudes that cannot represent the requested shock are refused.

No full curve, term premium, policy reaction, credit/equity response, portfolio return or future path is inferred. The immutable internal result is display-only and carries zero canonical, alert, portfolio and calibration writes, with no ranking, gating, sizing, signal-origination or execution authority.

## Observed baseline and identity

The helper validates the existing sealed Rates snapshot through the incumbent contract before reading it. It accepts only the exact US Rates workspace, producer and composition method. It resolves DGS2 and DGS10 through their complete series/source/artifact/owner tuples; ambiguous or conflicting identities fail closed. Both legs independently require OPEN rights, compatible percent/CMT units, and matching observed freshness states. A simulated or failed leg cannot be hidden by aggregating it with a more severe stale state. Stale observed data can remain explicitly stale; the pure helper does not silently reclassify it as current.

Published points must have strict date-only labels, ascending unique dates, finite published four-decimal values, the existing bounded history window, and matching disclosure/reference dates. Null points remain gaps. Every listed date, including a null point, must be no later than the snapshot's supplied publication date. The existing cadence helper and caller-supplied publication clock are reused; there is no new wall-clock reader. The baseline uses the incumbent `_pair_value()` common-date rule, including its five-day maximum lag, rather than combining independently latest yield tiles. Missing unrelated tenors do not veto a qualified pair.

Frozen, detached source and baseline records prevent later caller mutations from changing the calculation inputs. Domain-separated IDs bind the snapshot content digest, method, common date, source qualifications, normalized assumptions and exact direct outputs. Volatile build clocks and the generation label are not represented as manifest or historical-knowledge receipts. The digest is an unkeyed content-consistency check, not authentication, service admission, proof of current publication or point-in-time availability. The future HTTP branch must construct the baseline from a qualified server read; it must never accept client-reconstructed baseline objects merely because a digest matches.

The original composer, its method version, source cleaning, common-date helper, published schema and all fourteen workspaces' `execution_available=false` flags are unchanged. The internal dataclass is deliberately not advertised as a public scenario-result schema.

## Verification

Local command, 2026-11-14:

```sh
PYTHONPATH=/workspace/scratch/613742d6b57a/qualification_deps:/workspace/scratch/613742d6b57a/qualification python -m pytest qualification/tests/test_macro_workspace_rates_curves.py -q
```

Result: **225 passed**, including all 125 pre-existing cases and 100 added scenario cases. The sole warning is the existing anyio pytest plugin's CallSpec2 deprecation. Regression coverage includes zero and opposing shocks, negative assumed yields, normalization and malformed inputs, common-date boundary cases, detached inputs, tampering and resealed source contradictions, individual source qualification, stale versus simulated states, null gaps, future-dated null history, reference clocks, published precision and unrepresentable finite shocks. No test or existing publisher invariant was weakened. Source review found and the implementation repaired the future-null date edge; review did not execute or independently certify the tests.

These are deterministic fixture tests, not served-production or browser proof. Hosted exact-head checks, protected release and actual consumer acceptance remain separate evidence.

## Custody and remaining delivery

The existing scenario endpoint remains `/api/ontology/explorer/scenario/v1`. Open Macro PR #10614 at `078f4ab8aa8609a4eb484dd4490749bde49d486b` owns changes in `engine/ontology_scenario_runtime.py`, `lib/store.py` and its transport/UI tests. It retains `merge-blocked` and original unknown execution effects recorded in its body. This phase changes none of those paths or controls, replays no execution, and makes no release request for that PR. Native experience source PR #11258 and its current CI are also left intact.

Next safe phases are: qualify a served publication receipt and define the closed Rates request/result branch; add reader support for the next contract version before publisher emission; integrate the existing private scenario service with server-selected inputs and before/after publication checks; add native Rates controls, chart/table comparison and subject/baseline/departure cancellation; then enable only the supported Rates publisher capability after the service and reader path work. A source change must produce a real 409, retain no stale assumed result and require explicit baseline reacceptance. Existing authentication, size limits, duplicate-key handling, no-store behavior, input-logging limits, release holds and single-runtime ownership bind throughout.

Parent DONE_WHEN remains open: Paper desktop/mobile and theme/language design acceptance, protected source/catalogue order, actual native consumer proof, alerts and evidence attachment, revision/PIT depth and the remaining original analytical capabilities. Completing this pure phase is not completion of scenarios or the overall redesign. Continue with the next safe authorized phase after saving and readback.
