# Fixed input-transformation x kernel ablation

Evidence class: exploratory follow-on on an already-inspected panel. This is not independent validation, untouched out-of-sample evidence or a new production registration. It cannot clear a ranking, data-rights, source-window, W3, Phase-22 or deployment gate.

## Rationale

The native ETF pilot compared price MACD12/26/9 with RSI14 -> MACD14/60/5. Input transformation and smoothing memory both changed. Therefore its negative RSI-MACD 3D regime interaction cannot distinguish those mechanisms. The current intake's memory-matching field is declaration consistency, not a physical-equivalence proof.

## Frozen four policies

Cross exactly two inputs with exactly two existing kernel parameterizations. A=(12,26,9); B=(14,60,5). Inputs: price close and native RSI14 of close.

| Policy | Status |
|---|---|
| Price + A | Existing raw price-MACD baseline, reuse parent events |
| RSI14 + B | Existing raw Prophet oscillator baseline, reuse parent events |
| Price + B | Research-only crossed variant |
| RSI14 + A | Research-only crossed variant |

No parameter optimization, selection of a best arm, new indicator definition in the production catalog or change to validated Prophet-take logic. Use the same native pandas EMA/RSI implementations and native calendar/aggregation functions. Do not mix in Terminal Wilder primitives or normalized MACDX.

All four policies are evaluated on 1D/2D/3D/completed weekly bars with the existing source snapshot, ETF universe, lagged regime features, next-session-close entry, H10, 20bp cost assumption, early/later/combined periods and quarter-bootstrap conventions. Refer to ETF_PILOT_SPEC and CALENDAR_PILOT_AMENDMENT. The calendar defect remains unresolved for production; no re-anchor or expanded historical window is introduced.

Parent artifact must match SHA-256 `ce0abe8268301b7f3ac9dee5dc6807e79d1644dd689007b29b2195197a402b9e` and code `0b0bc00c5efae74618824581639f7bfa7c8e190b`. Read no new datasets. Every source buffer in the added-arm run must match the parent's ten source digests. Preserve the original 2,730 events; calculate only the two crossed variants. Report all four policies, not just favorable results.

## Fixed comparisons

For each policy let D = (3D hidden-minus-relief mean net excess) minus (1D hidden-minus-relief mean net excess). Report D for all policies and each fixed era using the existing summarizer.

Then report four additional exploratory differences per era: B-minus-A D holding price input fixed; B-minus-A D holding RSI input fixed; RSI-minus-price D holding A fixed; RSI-minus-price D holding B fixed. A shared sample of entry-quarter weights must be applied to all component cells before differencing. Never subtract marginal confidence-interval endpoints. Require the original twelve-month/four-quarter support floor in every component state cell and at least 95% finite bootstrap draws.

These are comparisons of signal POLICY event populations. They are not matched identical entry dates, experimental causal effects, proof of an institutional flow mechanism or evidence of live user gains. All intervals are descriptive and unadjusted for the research search already conducted. Point-in-time stock-candidate, theme membership, full validated-take, execution and portfolio tests remain the later acceptance path.

## Acceptance and rejection

Exact code/data/parent hashes, synthetic known-answer tests, unchanged parent-event readback, every policy/era table and contrasts, missing-cell abstention and explicit uncertainty. A null, unstable, counterintuitive or non-estimable result is a valid outcome. If the apparent native-family distinction weakens when memory is controlled, update the research interpretation rather than retaining a timeframe-only explanation.
