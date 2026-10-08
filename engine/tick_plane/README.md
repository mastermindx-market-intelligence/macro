# TP-1 equity T/Q source semantics — independent bounded implementation

**Status: BUILT_NOT_PROVEN.** No live socket, vendor credential, daemon, R2 store, scheduler, replay authority or user-facing publication exists in this package. It is a pure ingestion/analysis substrate, not the completed TP-1 service.

This package extends the parent [Macro #7368](https://github.com/mastermindx-market-intelligence/macro/issues/7368) under [#7367](https://github.com/mastermindx-market-intelligence/macro/issues/7367), plus C15 research. The existing Terminal Quote Hub remains market-data authority; **do not** open a second RT stock socket. Massive §3.1b.4 already measured the evict-oldest WebSocket hazard, so no duplicate concurrency experiment.

The source owner must provide the exact private raw T/Q WebSocket frame bytes, original host receive timestamp, exact session and bounded subscribed ticker set. `stream_events.normalize_ws_event` records original frame sha256 and per-frame event index, plus native T/Q fields. Massive real-time WS clocks are **milliseconds**, multiplied to ns for integer compatibility without claiming nanosecond resolution. The vendor's REST tape carries original nanosecond clocks.

Trade IDs are source-scoped by **ticker × exchange × TRF**, additionally bound to the SIP clock for the captured event. They are not global per ticker. Vendor WebSocket messages **do not include corrections**. All live prints remain STREAM_PROVISIONAL_UNRECONCILED until a separate source-owned REST/flat-file correction review. Never replace original as-seen evidence with a final-vintage record.

`InFlightNBBO` holds only bounded in-memory normalized NBBO updates for one exact session. Ingestion gaps poison the ring until an independently qualified new ring/session. One-sided, zero-size, crossed, stale or same-millisecond ambiguous quote states fail closed; the presence of a source quote is not proof of its eligibility. The caller must attest source-contiguous T/Q event scope, condition-policy coverage, and original available-at watermark before invoking `match`. **SIP message sequence gaps are not automatically dropped-event proof** because documented sequence values need not be consecutive.

`rest_corrections.compare_rest_trade` consumes a fully fetched, privately held REST response (no network) and returns typed mismatch/correction/ambiguity evidence without changing the original stream row. REST fields include a correction indicator; zero or absent correction in a later REST snapshot is not independent proof of historically final execution. Missing REST records are not automatically cancellations.

`print_observations.observe_provisional_trade` invokes the ONE canonical `engine.flow_signing.classify_print` only after original as-seen trade/quote and condition checks. Output remains observational, correction-provisional, and explicitly null for directional alpha or future markouts. Lit and TRF are separate populations. Unknown-side notional must remain unknown—not a silent zero.

**Local tests (from the Macro repository root):**
```
PYTHONPATH=. python3 -m pytest -q tests/test_tp1_qualified_print_classifier.py tests/test_tick_plane_stream_events.py tests/test_tick_plane_asof_nbbo.py tests/test_tick_plane_rest_corrections.py tests/test_tick_plane_print_observations.py
```

Preliminary stdlib-only normalization/ring/REST tests can also run with `PYTHONPATH=. python3 tests/test_tick_plane_stream_events.py` etc. Passing a source-contract fixture does **not** prove capture completeness, native condition-rule correctness, actual source availability, historical correction lineage or production behavior.

**Still required:** canonical singleton RT T.*+Q.* producer on admitted host, 1008/slot-fight kill switch, source-owner receipt/condition/correction/watermark qualification, private spool/R2, RTH coverage and reconciliation, Macro-to-Terminal derived consumption, independent predictive validation and production browser proof. Never publish raw licensed frame bytes or private receipt diagnostics.
