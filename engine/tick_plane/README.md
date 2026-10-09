# TP-1 equity T/Q source semantics — independent bounded implementation

**Status: BUILT_NOT_PROVEN.** No live socket, vendor credential, daemon, R2 store, scheduler, replay authority or user-facing publication exists in this package. It is a pure ingestion/analysis substrate, not the completed TP-1 service.

This package extends the parent [Macro #7368](https://github.com/mastermindx-market-intelligence/macro/issues/7368) under [#7367](https://github.com/mastermindx-market-intelligence/macro/issues/7367), plus C15 research. The existing Terminal Quote Hub remains market-data authority; **do not** open a second RT stock socket. Massive §3.1b.4 already measured the evict-oldest WebSocket hazard, so no duplicate concurrency experiment.

The source owner must provide the exact private raw T/Q WebSocket frame bytes, original host receive timestamp, exact session and bounded subscribed ticker set. `stream_events.normalize_ws_event` records original frame sha256 and per-frame event index, plus native T/Q fields. Massive real-time WS clocks are **milliseconds**, multiplied to ns for integer compatibility without claiming nanosecond resolution. The vendor's REST tape carries original nanosecond clocks.

Trade IDs are source-scoped by **ticker × exchange × TRF**, additionally bound to the SIP clock for the captured event. They are not global per ticker. Vendor WebSocket messages **do not include corrections**. All live prints remain STREAM_PROVISIONAL_UNRECONCILED until a separate source-owned REST/flat-file correction review. Never replace original as-seen evidence with a final-vintage record.

`InFlightNBBO` holds only bounded in-memory normalized NBBO updates for one exact session. Ingestion gaps poison the ring until an independently qualified new ring/session. One-sided, zero-size, crossed, stale or same-millisecond ambiguous quote states fail closed; the presence of a source quote is not proof of its eligibility. The caller must attest source-contiguous T/Q event scope, condition-policy coverage, and original available-at watermark before invoking `match`. **SIP message sequence gaps are not automatically dropped-event proof** because documented sequence values may increase nonconsecutively and reset daily.

The ring uses an append-first ordered index and a logical head for amortized eviction; genuinely out-of-order events use a bounded insertion path. It has a hard total capacity ceiling of 131,072 active observations across its subscribed symbols (plus bounded per-symbol compaction overhang). A capacity breach quarantines the affected symbol rather than silently asserting a continuous valid NBBO. Default 4,096 per-symbol allowance is only a memory cap, **not a production throughput admission**. On Mini4 synthetic observations, 9,000 same-symbol insertions completed in 145 ms versus 6,466 ms for the older implementation; this is not a live exchange-load SLO.

### Historical REST source qualification and venue safeguards

`rest_page.normalize_rest_page` now accepts one immutable private Massive Stocks REST trades/quotes response, preserving the original retrieval timestamp and byte digest, native nanosecond SIP/participant/TRF fields, fractional notional and native condition/correction identifiers. Historical REST outputs are **`FINAL_VINTAGE` only**: even a terminal pagination response cannot independently prove full-range capture, historical receivability, original correction lineage or an as-seen decision. Missing condition arrays stay null rather than being treated as empty. The path opens no new REST client or WebSocket; it reuses the existing source owner's collection capability.

Both live and historical normalizers share `_coarse_venue_class`. Exchange 4 with a **recognized** TRF ID 201/202/203 is TRF (off-exchange reporting). Missing or unknown TRF IDs, SIP IDs 5/13 and FINRA ORF ID 62 remain UNKNOWN, never lit signed pressure. Other exchanges remain only **coarse lit candidates** until a source-versioned `/v3/reference/exchanges` admission has independently confirmed their type. Current Massive primary docs explicitly say exchange 62 is OTC/ORF and lacks the ordinary originating participant timestamp; it cannot be used as a lit trade.

**Source-branch acceptance (2026-10-08):** candidate `d6eeb39f2f1529cdee1fb1d71467ad3d2dfed900` passed **233 pytest tests and 39 subtests** on M2 Studio (actual shared classifier plus all TP-1 modules). This is synthetic source-contract behavior, not real T/Q capture, final CI acceptance, a selected runtime or a production deployment.

**Host boundary:** The canonical Terminal Quote Hub is VPS-local at `127.0.0.1:3100`, not a worker host. The attended M2 Studio read-only SSH preflight to the documented production VPS was denied `Permission denied (publickey)`; this does not confer source custody or a real-time socket lease. No alternative account/tool path or competing socket may be used to work around the denied access. Real capture requires current incumbent-host ownership/health and human-authorized host credential/permission resolution through its proper owner.

`rest_corrections.compare_rest_trade` consumes a fully fetched, privately held REST response (no network) and returns typed mismatch/correction/ambiguity evidence without changing the original stream row. REST fields include a correction indicator; zero or absent correction in a later REST snapshot is not independent proof of historically final execution. Missing REST records are not automatically cancellations.

`print_observations.observe_provisional_trade` invokes the ONE canonical `engine.flow_signing.classify_print` only after original as-seen trade/quote and condition checks. Output remains observational, correction-provisional, and explicitly null for directional alpha or future markouts. Lit and TRF are separate populations. Unknown-side notional must remain unknown—not a silent zero.

### Versioned exchange reference gate

`exchange_reference.parse_exchange_reference` consumes the original response bytes to the existing vendor `/v3/reference/exchanges` source and records its receipt time, request ID and SHA-256. `classify_trade_venue` binds ticker-scoped native trade identity, exchange/TRF identifiers, decision cutoff and original reference availability. It grants a **lit-market candidate** only when the versioned reference identifies a genuine exchange. FINRA ORF 62, SIP 5/13, unknown reporting codes and any unexplained mismatches abstain.

`observe_provisional_trade` now requires this typed verdict, not just the decoder's coarse `venue_class` label; a future/mismatched reference cannot backfill a previously unavailable print. The minute evidence compiler preserves one reference digest and refuses mixed source-reference generations. It remains observational and correction-provisional; a caller-supplied custody flag cannot independently authenticate a host source receipt.

**2026-10-08 source-head verification:** `746bdc985824111b431fa3039676785ac225a0ae` passed **251 pytest tests plus 42 subtests** on M2 Studio against the actual source modules. The corrected test explicitly distinguishes a trade received after decision time from a venue-qualification failure. This is not production approval.

### Private provisional 1-minute derived evidence

`condition_policy.parse_condition_reference` and `evaluate_trade_conditions` bind source-native trade-condition codes to an original response digest, true reference availability and conservative price/volume eligibility. The resulting decision is required by `observe_provisional_trade`; a bare caller-supplied `eligible=True` is not accepted.

`minute_projection.project_provisional_minute` consumes those existing, strictly shaped `equity.tick_plane.provisional_print_observation/v0` records. It emits `equity.tick_plane.minute_observation/v0` only for an owner-attested, already-matured half-open UTC minute and one original decision cutoff. Buy/sell quote-location proxies, midpoint notional, unknown/condition-excluded prints and TRF notional are separated; native identities stay behind a content digest, with raw paid T/Q messages excluded.

`source_completeness_attested=True` is a required **external owner assertion**, not a self-authenticating completeness proof. The pure function cannot discover a dropped SIP event, qualify original point-in-time source possession, reconstruct corrections or measure independent market-wide capture. Outputs preserve provisional correction status, source receipt, null forward-response labels and `absorption_signal=None`; they neither implement nor override R0's statistical price-response experiment in PR #8659. The eventual private R2/dedicated API publisher must project allowed fields through existing delivery/security owners—this code publishes nothing.

**Tests (Macro root, exact TP-1 candidate):**
```
PYTHONPATH=. python3 -m pytest -q tests/test_tp1_qualified_print_classifier.py tests/test_tick_plane_*.py
```

At source candidate `746bdc985824111b431fa3039676785ac225a0ae`, M2 Studio completed 251 pytest cases and 42 subtests on the actual shared classifier plus all source modules. The local synthetic test result does not satisfy hosted CI, independent review, actual vendor-source coverage or production acceptance.



Preliminary stdlib-only normalization/ring/REST tests can also run with `PYTHONPATH=. python3 tests/test_tick_plane_stream_events.py` etc. Passing a source-contract fixture does **not** prove capture completeness, native condition-rule correctness, actual source availability, historical correction lineage or production behavior.

**Still required:** canonical singleton RT T.*+Q.* producer on admitted host, 1008/slot-fight kill switch, source-owner receipt/condition/correction/watermark qualification, private spool/R2, RTH coverage and reconciliation, Macro-to-Terminal derived consumption, independent predictive validation and production browser proof. Never publish raw licensed frame bytes or private receipt diagnostics.
