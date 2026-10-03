# Subtheme replay qualification - research candidate

Start with `MASTER_PLAN.md` for the census, observed result audit, architecture, experiments and U0-U6 owner-mapped delivery plan. `ECONOMIC_PILOT.md` adds source-grounded optical/fabrication cases and event-stage tests.

The offline qualification adapter remains an acceptance asset, not a second canonical grader. PR #8299 now also repairs the existing production-source evaluator and its existing scorecard renderer; source changes are not deployed merely because they are committed. Every trading/action-authority flag remains false. Inputs labeled PIT or qualified require external source-owner verification; a parser or timestamp cannot certify a dishonest attestation.

## Run

The offline qualification CLI uses Python 3.10+ standard-library code. The public industry-reference study also requires NumPy, pandas and SciPy. The existing owner test suite uses its normal engine dependencies and Node for renderer contract checks. Current targeted verification ran with Python 3.14.7 and pytest 9.1.1.

From the repository root, use the existing CI-owned suite:

```sh
python -m pytest -q tests/test_subsector_track_record.py tests/test_subsector_significance_guard.py
node --check templates/subsector_rotation.js
```

From this research directory:

```sh
python legacy_seams.py
python audit_existing.py
python qualification.py /path/to/qualified_owner_packet.json --output /path/to/result.json
```

Exit 0 means the supplied packet was processed, not that a strategy was validated. Inspect the label statuses, coverage and comparison exclusions. Exit 2 means the packet/CLI was refused. A measured group target is not a cost- or capacity-adjusted portfolio return.

A synthetic end-to-end fixture is defined by `packet()` in repository-root `tests/test_subsector_track_record.py`; the CLI tests materialize it in a temporary directory. This fixture is never market-performance evidence.

## Actual verification

Historical phase counts remain in their immutable evidence receipts. The original 81-case offline study grew to 107 qualification/seam cases, then to 137 research cases. Those were not the complete application suite. The two originally unregistered research test files were consolidated into the existing CI-owned owner suite; no waiver or new workflow was introduced.

Canonical evaluator integration reached 188 passing targeted tests with real imports and synthetic parquet IO. That source head, ee4124d999a5cc8e10526127352534f18ca557f4, passed hosted CI 37094428913 and its fences. Coverage and renderer integration reached 218 passing targeted tests; six capture-clock cases then reached 224. Five of those six clock cases failed before the clock repair. No independent review or actual-market predictive acceptance is implied.

`evidence/engine_integration.json`, `evidence/coverage_integration.json` and `evidence/snapshot_clock.json` bind the source, test scope and remaining limitations. Newer heads require their own hosted acceptance. Node tests exercise the actual renderer in a VM, not the full browser. The local static-fragment Chromium navigation was blocked by administrator policy; no screenshot/layout proof is claimed.

Current source behavior deliberately separates:
- exact following-session entry/exit clocks from calendar days;
- decision, feature-known, membership-known, weight-known and outcome-known times;
- expected population from observed coverage;
- same-sample model comparison from unpaired historical columns;
- source clusters from duplicated reports or corrected versions; retracted claims no longer count as confirmations;
- content digests from ID-only fingerprints; the paired digest binds actual scores, labels, population and clocks;
- disjoint time intervals, reported separately by horizon, from independent market episodes.

## Owner-packet contract

`manifest` contains `membership_basis=POINT_IN_TIME`, `price_basis=OWNER_QUALIFIED_ADJUSTED_OHLC` and nonempty calendar/price/signal receipts. `sessions` supplies a unique, ordered exchange-session axis with timezone-aware opens and closes. This adapter neither infers a calendar from prices nor invents early-close times.

Each signal supplies a stable snapshot/group ID, signal session, decision and feature-known time, PIT membership, benchmark and the baseline/challenger scores to compare. Each member supplies ticker, issuer ID, positive weight, membership and weight known times, and effective start/end dates. Membership end is exclusive. Identifiers must be nonempty canonical strings; effective dates must parse and form a valid interval. Repeated issuers are refused; use the existing issuer/listing owner to resolve legitimate multi-listing representation first.

Prices supply exact ticker/session open and close, when that finalized record became known, and a consistent adjustment-basis identifier. Each price value must agree with its ticker/session map key. Outcomes use frozen starting weights. If any expected member or benchmark endpoint is missing, the target is unavailable; it is not recomputed over a smaller survivor basket.

The target is explicitly NEXT session open through the Hth following session close, inclusive. An end-of-day observation received after the next open is refused rather than backdated. This target differs from the canonical information-content evaluator's close-to-close, exact-session definition and must retain its own evaluation label/version. Neither target implies a cost-adjusted executed strategy.

`evaluation_at`, `horizons`, `baseline` and `challenger` complete the packet. Baseline and challenger must have distinct, nonempty identities. Paired comparisons reject mixed target bases. Results preserve latest outcome availability; training purging requires both an elapsed outcome and its knowledge clock before validation begins.

## Coverage and capture-time contract

The canonical evaluator now publishes per-horizon input, due, measured, pending, invalid and unavailable counts, plus first-failing-gate reasons and bounded stage breakdowns. Due excludes pending observations and invalid records; its zero-denominator fraction is null. The basis is parsed snapshot rows, not all raw lines or the market universe. These diagnostics expose selection; they do not correct missing-not-at-random bias.

The existing renderer shows measured / due, visible exclusions and accessible reason details. Legacy or inconsistent counters remain unknown. A data generation without an explicit complete-basket policy is not described as if it had one.

Newly appended canonical snapshot rows also carry `recorded_at_utc` and `recording_time_basis=observer_wall_clock`. This is the observer's capture timestamp, NOT a market-session label, source-publication time, original ingestion time, or fully qualified decision-time attestation. Caller payload timestamps cannot override it. A single batch uses one observed instant. Existing rows remain byte-preserved; idempotent replays do not update the original timestamp and no historical availability is backfilled.

A session dated September 25 but first recorded October 3 must not be treated as a decision known on September 25. The new capture clock is evidence for later qualification, not an automatic conversion to the adapter's `feature_known_at`. Clock accuracy, upstream availability, revisions, membership/weight provenance and execution admissibility remain with existing source/Evaluation owners. Old rows lacking the field remain unknown. This source change has not yet accrued live records because this PR remains undeployed.

## Required real-data export and unresolved qualification

The existing owner should resolve its exact retained rotation snapshots, source-tree and membership history, qualified prices and calendar. Existing inspected assets include `data/themes_heatmap/subsector_perf_history.jsonl`, `data/themes_heatmap/tree_history.jsonl`, `data/themes_heatmap/themes_tree.json` and the rotation builder/grader source paths cited in the master plan. These are navigation references, not permission to infer missing member history.

A historical Lane C receipt is available at PR #7455 under `research/theme_graph/lane_c_closed_session_proof_2026-09-18/README.md`: it pins source commit `2208fe40039d356929fac0f96b626edc33d42288`, 46 committed Yahoo tapes out of 47 requested members and an exact manifest/result digest. That proves a bounded historical measurement, not current publication, a qualified corporate-action basis or a predictive backtest. It can guide source acquisition without being promoted into stronger evidence.

Required before a real comparison: actual source/known-time receipts; correct membership/weight vintages; corporate-action and delisting handling; common execution clocks; complete-case selection analysis; a frozen target; and independent review. The continuation inventoried the existing M2 project: 6,066 entries in `data/yahoo`, 9,944 retained snapshot rows through September 10, and two source-tree vintages. These counts establish presence, not qualified price coverage or current freshness. The subsequent bounded source-data read was explicitly blocked by the platform before a process receipt; it was not replayed or transferred to another carrier. No new raw-market replay is claimed. This is not evidence that the company lacks the data.

## Delivery boundary

Keep this candidate in review. Integrate accepted functions into the incumbent evaluation path rather than create a second canonical grader. Require exact-head hosted execution of the consolidated owner suite and independent review before accepting source integration. Do not edit the active #7455/#7976/#7664 source paths without reconciling their custody. This research contains no permission to change ranking, sizing, risk gates, candidate population or live deployment.
