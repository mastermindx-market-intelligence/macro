# Options Alpha: preserve decision-time source clocks

Operation: `options-flow-source-clocks-20260929-sol-001`. Parent: Terminal #599 / `WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY`.

## Implemented result and ceiling

The existing Flow collector now retains five optional producer timestamps in its existing keep-first ledger and reports their coverage through the existing `flow_signals.gate/v2` operational artifact. This is a tested source-to-history-to-diagnostics repair, **not a candidate, new event store, strategy, fitted model, ranking change, activation receipt or production-enabled capability**. Source: `collectors/flow_signals.py`, `scripts/build_flow_signals.py`, and the existing CI-owned `tests/test_flow_signals.py`.

The source base is Macro `1df73c1ac9289a21e192aeb50088a4f9119aee82`. Protected procedure is Mastermind `0b3bdf78be9b86bc3672f224ddacf80854a4c3fb`, Skillpack 1.0.1/bootstrap1. This read-only qualification and additive collection repair do not open the held candidate-formation or fitting gates.

## The measured gap

Exact committed `data/flow_signals/ledger.parquet`, blob `9b322983866ffc42b274e495f5107c9c1364c06b`, SHA256 `c14b99cf92c29467d40a823a42e1b8974f018233c76b70d917b403f7a3898b62`, contains **92,574 distinct events across 44 sessions, July 13 through September 25, 2026**. **16,052** rows contain `options.trade_nbbo_microstructure/v1`. The five producer-clock columns below are absent from this file. These are input-coverage measurements, not independent trade samples or performance evidence.

Source inspection identifies the omission: the collector retained `ts` and its own `ingested_at`, but its column list and event flattener did not preserve the producer clocks. `scripts/live_flow_poller.py` already handles those source fields. A later collector timestamp is not a substitute for original source availability.

This does **not** establish that the producer lacked clocks, that every historical row is irrecoverable, or that all prior research is invalid. Existing exact-event source receipts may qualify a bounded historical join through their own owner. No such join or historical reconstruction was performed here; nothing was backdated or overwritten.

## Additive contract

The retained fields are `observed_at`, `decision_at`, `available_at`, `published_at`, and `source_snapshot_asof`. Supplied valid timestamps normalize to UTC while preserving up to nanosecond precision. Missing values remain null; trade time, wrapper build time and harvest time never fill them. Invalid strings, naive local times, numeric/bool values, impossible dates and malformed offsets become null with diagnostic invalid status. This is a conservative application profile, not a claim to implement every RFC3339 form: leap-second strings and fractions beyond nanosecond precision are not accepted.

`source_clock_status` is one of `ordered`, `partial`, `unavailable`, or `invalid`. Ordered requires supplied trade, observation, decision and availability times in nondecreasing order, not later than ingestion. A supplied publication time must also preserve that order. The independent snapshot clock is retained and cannot be later than ingestion, but is not substituted for event/publication clocks. Incomplete valid chains are partial. Valid fields remain available for diagnosis when another field or ordering fails.

**Ordered means clock structure only.** It does not prove source authenticity, first public delivery, revision provenance, exchange coverage, package identity, entitlement, or executable entry. The candidate's own first-observation and publication clocks and its forward activation fence remain separately owed.

Ordinary keep-first append preserves old event identity and its original fields. Legacy rows acquire null additive columns, not invented times or retroactive ordered classifications. The operational ledger block now includes `source_clock_coverage`: total rows, separate status counts including `legacy_unknown`/`unrecognized`, and per-field non-null counts. The block explicitly declares `diagnostic_only` authority. No UI warning wall was added.

## Executed proof

The original collector suite had 38 passing cases. The first 22 source-clock regressions failed on the original implementation. Adversarial testing then reproduced pandas normalizing invalid `+01:99` and `+01:60` offsets; range checks close those cases. Final existing suite: **68 passed**. It covers nanoseconds, missing/reversed/future/invalid clocks, first-seen immutability, legacy append, actual parquet/statistics/gate passage and the unchanged native feature matrix. No training or model fit was called.

A separate real-input diagnostic ran the repaired native statistics and gate writer against a temporary copy of the exact committed ledger. It preserved all 92,574 rows and reported all as `legacy_unknown`, with zero populated source-clock fields; source bytes were unchanged. Both `scored` and `scoring.enabled` stayed false. This is not a live nightly result. The full Macro suite was not run from the sparse workspace.

Reproduce software verification with `python3 -m pytest tests/test_flow_signals.py -q`. Aggregated input, native-gate and source/log hash receipts are in `research/options_estate/flow_source_clock_qualification_20260929/`; no individual licensed trade rows are included.

## Research implications, not inherited alpha

Pan and Poteshman used buyer-initiated **opening** volume in their research, not undifferentiated call premium. Their historical result does not establish performance for our differently labelled feed. [NBER WP10925](https://www.nber.org/papers/w10925), published in RFS 2006, DOI `10.1093/rfs/hhj024`.

Savickas and Wilson document option trade-classification errors, including outside/reversed quotes and complex-trade components. Their sample is not a calibration of the current provider. Directional-sleeve research must therefore distinguish measured execution location from inferred initiator and preserve package uncertainty. [JFQA 38(4), 2003](https://doi.org/10.2307/4126747).

Cboe's Open-Close summaries distinguish participant, buy/sell and open/close within the selected Cboe exchanges. Its enhanced trade-by-trade product describes C1-only coverage, execution identifiers and **T+1** delivery. These are separate licensed capabilities, not evidence of our subscription or permission to treat next-day labels as live information. No purchase or data extraction occurred. Sources checked September 29, 2026: [Open-Close](https://datashop.cboe.com/cboe-options-open-close-volume-summary), [TBT](https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail). The Open-Close page also announces later November changes; those are not treated as effective now.

RFC3339 section 4.3 states that `-00:00` retains a known UTC instant while the local offset is unknown. An initially incorrect supplementary test assumption was corrected accordingly; it is not counted as a repaired production defect. [RFC3339](https://www.rfc-editor.org/rfc/rfc3339).

## Exact next acceptance

After independent review and protected release, prove one **ordinary scheduled** new event reaches the incumbent ledger with the original source timestamps unchanged and appears in the existing coverage report. Do not invoke a historical production harvest to manufacture this proof. Then qualify candidate observation/publication delay under the accepted formation policy. Existing Macro #7265 history-integrity failure, #7398 correction law, AD-1T2 acceptance, OA-2 no-fit gates and Terminal #667 production/browser proof remain independent outstanding obligations.
