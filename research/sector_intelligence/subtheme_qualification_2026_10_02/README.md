# Subtheme replay qualification - research candidate

Start with `MASTER_PLAN.md` for the census, observed result audit, architecture, experiments and U0-U6 owner-mapped delivery plan. `ECONOMIC_PILOT.md` adds source-grounded optical/fabrication cases and event-stage tests.

This package does not install, import into or modify a production engine. It is a deterministic offline acceptance asset for the existing Evaluation/Prophet/Group Reads owners. Every action-authority flag is false. Inputs labeled PIT or qualified require external source-owner verification; the parser cannot certify a dishonest attestation.

## Run

Python 3.10 or newer is required. The runtime uses the standard library. Tests require pytest; the actual verification used Python 3.13.5 and the installed pytest environment.

From this directory:

```sh
python -m pytest -q tests
python legacy_seams.py
python audit_existing.py
python qualification.py /path/to/qualified_owner_packet.json --output /path/to/result.json
```

Exit 0 means the supplied packet was processed, not that a strategy was validated. Inspect the label statuses, coverage and comparison exclusions. Exit 2 means the packet/CLI was refused. A measured group target is not a cost- or capacity-adjusted portfolio return.

A synthetic end-to-end fixture is defined by `packet()` in `tests/test_qualification.py`; the CLI tests materialize it in a temporary directory. This fixture is never market-performance evidence.

## Actual verification

81 local tests passed. Four preserve isolated semantic reproductions of legacy horizon, available-member averaging and iteration-order behavior. Twelve author adversarial cases initially failed and were repaired before the final pass. No independent reviewer verdict, full-repository CI result, historical raw-market replay or production/browser proof is claimed.

Current source behavior deliberately separates:
- exact following-session entry/exit clocks from calendar days;
- decision, feature-known, membership-known, weight-known and outcome-known times;
- expected population from observed coverage;
- same-sample model comparison from unpaired historical columns;
- source clusters from duplicated reports or corrected versions;
- disjoint time intervals from independent market episodes.

## Owner-packet contract

`manifest` contains `membership_basis=POINT_IN_TIME`, `price_basis=OWNER_QUALIFIED_ADJUSTED_OHLC` and nonempty calendar/price/signal receipts. `sessions` supplies a unique, ordered exchange-session axis with timezone-aware opens and closes. This adapter neither infers a calendar from prices nor invents early-close times.

Each signal supplies a stable snapshot/group ID, signal session, decision and feature-known time, PIT membership, benchmark and the baseline/challenger scores to compare. Each member supplies ticker, issuer ID, positive weight, membership and weight known times, and effective start/end dates. Membership end is exclusive. Repeated issuers are refused; use the existing issuer/listing owner to resolve legitimate multi-listing representation first.

Prices supply exact ticker/session open and close, when that finalized record became known, and a consistent adjustment-basis identifier. Outcomes use frozen starting weights. If any expected member or benchmark endpoint is missing, the target is unavailable; it is not recomputed over a smaller survivor basket.

The target is explicitly NEXT session open through the Hth following session close, inclusive. An end-of-day observation received after the next open is refused rather than backdated. This target differs from the incumbent legacy close-to-close/calendar-day definition and must receive its own evaluation label/version.

`evaluation_at`, `horizons`, `baseline` and `challenger` complete the packet. Results preserve latest outcome availability; training purging requires both an elapsed outcome and its knowledge clock before validation begins.

## Required real-data export and unresolved qualification

The existing owner should resolve its exact retained rotation snapshots, source-tree and membership history, qualified prices and calendar. Existing inspected assets include `data/themes_heatmap/subsector_perf_history.jsonl`, `data/themes_heatmap/tree_history.jsonl`, `data/themes_heatmap/themes_tree.json` and the rotation builder/grader source paths cited in the master plan. These are navigation references, not permission to infer missing member history.

A historical Lane C receipt is available at PR #7455 under `research/theme_graph/lane_c_closed_session_proof_2026-09-18/README.md`: it pins source commit `2208fe40039d356929fac0f96b626edc33d42288`, 46 committed Yahoo tapes out of 47 requested members and an exact manifest/result digest. That proves a bounded historical measurement, not current publication, a qualified corporate-action basis or a predictive backtest. It can guide source acquisition without being promoted into stronger evidence.

Required before a real comparison: actual source/known-time receipts; correct membership/weight vintages; corporate-action and delisting handling; common execution clocks; complete-case selection analysis; a frozen target; and independent review. The local runtime did not receive the qualified raw panel in this investigation. Do not claim the company lacks it.

## Delivery boundary

Keep this candidate in review. Integrate accepted functions into the incumbent evaluation path rather than create a second canonical grader. Wire tests into the existing CI owner before accepting source integration. Do not edit the active #7455/#7976/#7664 source paths without reconciling their custody. This research contains no permission to change ranking, sizing, risk gates, candidate population or live deployment.
