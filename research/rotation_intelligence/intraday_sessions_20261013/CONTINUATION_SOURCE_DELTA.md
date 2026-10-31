# Source-clocked intraday rotation: continuation delta

Operation: `rotation-intraday-session-research-20261013`. Same source workspace, branch and Macro PR #9196. Protected procedure pin remains `54e8659730141fc130ebbeb214dbb50f3edb04a7` / Skillpack 1.0.1. Host observation during this continuation: 2026-10-14T04:08:11Z. Capability: **BUILT_NOT_PROVEN**; the larger sector/theme/overnight product remains incomplete.

## What now works in source

The existing Basket Pulse producer can compare two regular-session observations using the same members, source conventions and benchmark. The existing Market State Packet reads those measurements and renders them for model grounding even when daily returns are flat. It does not reconstruct overnight paths, issue a trading signal, modify cycle positions, create an alert, or invent a new score.

The three connected changes are:

1. The previously published heatmap repair measures actual elapsed time rather than row offsets. Its new test suite is now named by the existing code-gated shared heatmap job and by the workflow's test-only trigger inventory.
2. Basket Pulse no longer treats a saved `delayMin` as a permanent age. It computes elapsed source age and retains valid declared delay as a floor. Missing, synthetic, malformed or future clocks are unknown. Unknown-clock and non-finite observations cannot enter an aggregate simply because its mode is delayed. The source clock range and `n_priced` describe actual contributors; coverage is priced coverage rather than merely the number of quote objects.
3. A bounded `intraday_comparison` beside each existing basket row measures change since the preceding eligible observation. The Market State Packet allowlists the measured fields, validates clocks/counts/coverage, renders absolute price change beside SPY-relative change, and labels the observation as **not fund flows**. Existing daily ranking, cycle, scoring, strategy, entry and notification formulas are not replaced.

## Measurement and persistence contract

The baseline lives only in the **existing** `basket_pulse_lastgood.json` sidecar. No new collector, endpoint, history store, scheduler, queue, grader or publication authority is added. The normal `basket_pulse.json` payload does not expose the baseline quotes. The existing VPS orchestrator preserves optional sidecars before its next builder run and publishes them beside the required artifact; the legacy workflow already stages the same sidecar. These are source traces, not observed production installation.

The first eligible run seeds a baseline and reports `baseline_missing`. Subsequent US regular-session observations require:

- the same session date and session, with the existing calendar owner's actual regular-session window, including early closes;
- identical economic membership, ignoring ordering but rejecting duplicated or changed membership;
- positive finite prices, real source timestamps, matching per-instrument quote source, price basis, currency and reference close;
- strictly advancing benchmark and constituent timestamps;
- constituent clocks within both 60 seconds and one tenth of the measured interval of the benchmark clocks, at **both** ends;
- enough matched members under the existing display coverage floor, with the exact matched/total count and coverage disclosed.

These alignment and coverage policies are measurement filters, not calibrated predictive thresholds. The current 30 percent display floor does not establish representative sector-wide leadership or alert confidence. Qualification for future alerts and higher-confidence classifications remains separate.

For the matched subset, each member's simple holding-period return is calculated from its own two prices. Their equal-weight mean is the subset's price return. Relative change is `(1 + subset_return) / (1 + SPY_return) - 1`, not the average of member log returns and not a direct measure of investor fund transfers. The interval is disclosed from source timestamps; a nominal five-minute poll does not manufacture a five-minute observation.

Unavailable comparisons retain explicit reasons: missing baseline/benchmark, changed session or membership, nonadvancing source, changed reference basis, insufficient matched coverage or out-of-session observations. Rebuilding an unchanged quote file does not issue another measured interval. No cross-session comparison is smuggled in as an intraday move.

## Executed proof

`final_qualification.txt`: **491 passed** across eight existing/new focused modules, including Basket Pulse, Market State Packet, current notification behavior, settled-close behavior and heatmap regressions.

The proof was test-first: the source-clock cases initially produced **25 failures / 2 passes**; the matched-comparison cases initially produced **13 failures**; the grounding additions initially produced **2 failures / 11 passes** (negative cases correctly remained absent). Subsequent tests include the actual producer -> serialized JSON -> packet reader -> rendered grounding path. These counts describe the retained stages, not independent market observations.

`producer_grounding_replay.json` is generated by `replay_observation_pair.py`, which executes the real application modules with synthetic source files and an isolated existing sidecar. It retains source-file SHA-256 identities. In this control:

- the first observation prices the two one-member example groups at 102 and 99, with SPY at 100;
- the second prices both at 100 and SPY at 100;
- both daily group changes are zero, but the 30-minute source interval reports approximately -1.960784% and +1.010101% relative change;
- both measurements survive in the actual grounding digest with source clocks and matched-member counts;
- replaying the unchanged snapshot thirty minutes later yields age 31 minutes, mode `delayed`, and `benchmark_nonadvancing`, not a fresh rotation.

Other controls reject coverage swaps, nonadvancing timestamps, future/synthetic clocks, changed source/basis/reference close, missing benchmarks, excessive clock skew, early-close after-hours samples, malformed comparisons and forwarded confidence/target/trading fields. A separate multi-member control verifies true equal-weight return arithmetic and a relative winner that is still falling in absolute terms.

One earlier integration run had **460 passes / 1 failure** because the sparse workspace lacked the committed product fixtures. The exact already-tracked `site/live/basket_pulse.json` was restored from HEAD, without modifying its bytes or production data; the final integrated suite above passed. The failure evidence is retained, not silently deleted.

## CI and current-source recovery

The original #9196 candidate's twelve hosted test packs passed, but `contract-delta` correctly found the new heatmap test file was not invoked by CI. The continuation wires that file into the code-gated shared heatmap job and adds its test-only workflow trigger. The existing fully synthetic Basket Pulse suite moves from the data/nightly group to the existing code-gated live-quote group; no waiver, weakened assertion, new gate or permission change is used.

The local unrun-suite audit completed successfully. Existing stale-baseline warnings remain attributed to the repository; no unrelated baseline cleanup was performed. Hosted checks must run against the new published head; the earlier twelve-pack result does not certify this extension.

At main revision `3512440213bab09ed16f6ebed1ee7418188162e0`, the original source blobs for `engine/sp500_heatmap.py`, `scripts/build_basket_pulse.py` and `engine/neuralweb/market_packet.py` were individually checked against the operation baseline and were unchanged. This is source compatibility evidence at that revision, not a perpetual merge guarantee.

The opening-price collector remains untouched: another active carrier owns `collectors/yahoo.py`. Existing source shows the private full quote projection can retain source-native `day_open`; its session meaning, receipt and access must be qualified by that owner before an opening-anchor integration. Absence of opens in the inspected daily stores is not a claim that no source can provide them.

## Reproduce

```sh
python3 -m pytest tests/test_build_basket_pulse.py tests/test_market_packet.py tests/test_notify_turn_events.py tests/test_settled_close_tape.py tests/test_sp500_heatmap_intraday_clock.py tests/test_sp500_heatmap_caps.py tests/test_market_heatmap.py tests/test_china_board_breadth.py -q
python3 research/rotation_intelligence/intraday_sessions_20261013/replay_observation_pair.py
python3 scripts/audit_unrun_tests.py
```

The application tests and replay are synthetic/source proofs. They are not live provider coverage, customer/browser acceptance, a held-out financial experiment or evidence of alpha.

## Recoverable frontier and remaining gates

Continue on Macro PR #9196 and its existing managed workspace. Do not redo the baseline defects, current 491-test result or source-pair replay unless their source/dependency changes. Do not create a second rotation program or adopt #9134, #9035, #8923, #9224 or #9225's source custody. Their active files and held empirical outputs remain outside this change.

No production SSH read was retried; its public-key authentication denial remains action-specific and unchanged. No credentials, permissions, workers, automations, customer notifications or deployment were created. Current minute coverage, rights, actual source-to-screen latency and authenticated production behavior remain unverified.

Next release steps: exact-head independent review, required hosted checks, any actual current-base conflict reconciliation, normal release, and a genuine production producer/consumer observation. No auto-merge or deployment follows from these source tests.

Next product steps after that boundary: qualify opening anchors and minute/overnight sources through their existing owners; add persistence/history through the retained-history owner; expose the tactical interval beside the structural cycle in the existing Sector Intelligence/Terminal workspace; qualify notification-specific false-alarm and freshness behavior. This first source slice is intentionally regular-session descriptive measurement, not the completed multiscale/overnight rotation product.
