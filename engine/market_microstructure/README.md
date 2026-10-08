# Equity pressure-response R0 — research measurement leaf

**Status:** BUILT_NOT_PROVEN (synthetic tests only). No runtime, feed, consumer, model, ranking, alert, portfolio or trading authority.

## Ownership and predecessors

This is a bounded implementation of the existing [Commission 15](../../research/market_microstructure/commission15/COMMISSION_15_HARDENED_REPORT.md) recommendation, underneath the existing [Massive TP-1/TP-2 program](https://github.com/mastermindx-market-intelligence/macro/issues/7367). It is **not** a new equity tape producer, order book, ingest schedule, canonical event store, model, execution loop or source of historical clock truth.

- TP-1 / Macro #7368: source-owner normalization, continuously observed T/Q messages, corrected trade lineage, source/version/conditions, qualified **combined trade + quote event-time completeness watermark**, and original received-at receipts.
- Terminal Quote Plane: existing shared quote service and vendor socket ownership; do not open a competing Massive socket to collect research evidence.
- Macro: pure deterministic feature calculation and subsequent calibration; do not reinterpret this module's research values as an existing validated gate.
- Existing options source/Flow (ThetaData/OA-1T): separate grain and authority; no options source/signing migration through this equity module.

## Exact input semantics

Call `engine.market_microstructure.pressure_response.measure_window` with one symbol and one exact session, half-open `[start_ns,end_ns)`, decision cutoff `decision_ns`, watermark `watermark_ns` observed at `watermark_seen_ns`, source/clock receipt identities, explicit `evidence_mode` and explicit `max_quote_age_ns`.

All times are **integer Unix UTC nanoseconds**. The caller must normalize Massive streaming milliseconds and historical REST nanoseconds without inventing precision or event order.

Quotes are source-owner-normalized continuous best-quote updates with `id,ticker,session,sip_ns,available_ns,bid,ask,bid_size,ask_size,bid_exchange,ask_exchange,source_receipt`; prices must be decimal strings or exact Decimal values. Stream gaps, restarts, sequence ambiguity, market halts and feed completeness must already be assessed by their real source owner. **Trade-attached quote snapshots alone do not qualify** for recovery or continuous liquidity-state claims.

Trades are source-owner-normalized records with `id,ticker,session,sip_ns,available_ns,price,size,revision,action,venue_class,eligible_for_pressure,eligibility_rules_ref,source_receipt`. Actions: `ORIGINAL`, `REPLACE`, `CANCEL`; venue classes: `LIT`, `TRF`, `UNKNOWN`. The eligibility decision and versioned condition-rule reference come from the existing source-conditions owner, **never guessed from hard-coded condition IDs**. Unknown eligibility must not be represented as True. Corrections require verified native linkage to the original stable trade identity.

Valid evidence modes are `ACTUAL_AS_SEEN`, `HISTORICAL_RECEIVABILITY`, and `FINAL_VINTAGE`. A mode label supplied to this pure function does not itself prove original possession or actual historic watermark availability. That proof belongs to the upstream source/receipt owner; absent proof, results can only be exploratory and may not enter as-seen consumer replay. Same-SIP-clock ties without strict native order **abstain**.

## Output and interpretation

Output `equity.pressure_response_observation/v0` includes:

- BUY_PROXY/SELL_PROXY/UNKNOWN notional, unclassified breakdown, classified-notional coverage and pressure balance **among classified notional**;
- completed-window best-NBBO midpoint response in bps or an explicit missing reason;
- same-price, same-displayed-best-venue quote-size depletion/recovery **proxy** or a typed unknown reason; venue/price changes invalidate continuity;
- bounded private diagnostics with original trade/quote receipt references, watermark lineage and explicit source mode.

**There is no absorption threshold or directional signal.** `absorption_signal` is null by design until a registered outcome-blind relative-impact study with time-of-day, volatility, spread, sector, regime and liquidity controls passes its independent gate. Neither buying near the ask nor a recovering NBBO size reveals a customer's side, passive owner, iceberg order or same-order replenishment. TRF/off-exchange prints remain separate unknown-side observations; they are not silently included in lit quote pressure or attributed to named ATS venues.

This module holds no data, opens no socket, and publishes no artifact. `print_diagnostics_private_only` is intentionally not a public-R2/frontend contract. Consumer/publisher owners must project permitted derived fields separately.

## Verification

Run `PYTHONPATH=. python -m pytest -q tests/test_equity_pressure_response.py` from Macro repository root. Synthetic fixtures exercise availability, future correction/cancel, late quote, invalid/ambiguous NBBO, condition policy consistency, venue switch, midpoint/outside, unmatured window and missing receipts. Passing these fixtures is **not** live-data qualification or any claim of alpha.

## Real-data and production gates

1. Finish TP-0.5/RTH qualification against the **incumbent** Terminal socket and host, no second connection; prove T/Q entitlement and proper event/ingestion clocks.
2. Establish source-owner continuous T/Q retention or qualified targeted historical replay, condition-update rules, corrections and original availability mode. Published Massive aggregate bars or quote snapshots are insufficient.
3. Freeze a small PIT-selected cohort (SPY, QQQ and pre-selected liquidity/sector strata) and event-window protocol before outcome inspection. Record trade/quote capture coverage, lit/TRF separated classification coverage, baseline markouts, source gaps and byte receipts.
4. Integrate as a nullable derived leaf behind the existing Macro intelligence/R2 source owner, followed by existing Terminal consumer fixture + real browser proof. No duplicate vendor connection or fresh event lifecycle.
5. Pre-register and independently validate response-vs-flow incremental utility against matched trend, volatility, spread, time-of-day, event, sector and price-only controls; preserve prior null studies and Commission 15's trial accounting.
6. Promote beyond display/research only through the incumbent outcome/admission owners; execution, sizing, Prophet gate, and automatic alerts remain OFF.

**Current first blocker:** Macro main has no `engine/tick_plane/` producer or real TP-1 source watermark contract. This R0 leaf is deliberately independent and not live-connected. Resume upstream work at [TP-1 #7368](https://github.com/mastermindx-market-intelligence/macro/issues/7368) and the parent [#7367](https://github.com/mastermindx-market-intelligence/macro/issues/7367); do not start a second producer.

## Offline pilot execution (the Macro repository, not the Terminal or a Mac terminal)

After an authorized source owner has produced a **private, qualified** input file, run from the root directory of the **Macro repository** (the directory containing `engine/`, `scripts/` and `tests/`):

```bash
python3 -m scripts.microstructure_pressure_response_pilot --input /private/path/to/qualified_TQ_window.json
```

The private input envelope is exactly:

```json
{
  "contract": "equity.pressure_response_input/v0",
  "measurement": {
    "ticker": "SPY",
    "session": "2026-10-08:RTH",
    "start_ns": 0,
    "end_ns": 1,
    "decision_ns": 2,
    "watermark_ns": 1,
    "watermark_seen_ns": 2,
    "watermark_receipt": "REPLACE_WITH_AUTHENTIC_SOURCE_RECEIPT",
    "source_manifest": "REPLACE_WITH_AUTHENTIC_SOURCE_MANIFEST",
    "evidence_mode": "FINAL_VINTAGE",
    "max_quote_age_ns": 5000000000,
    "trades": [],
    "quotes": []
  }
}
```

That envelope is an **illustration of field shapes only**, not admissible real-market provenance. Never use the example receipt strings as genuine evidence. The CLI reads only a JSON file of at most 16 MiB, makes no network calls, and writes a bounded derived summary to stdout without native print/quote identities. A nonzero exit denotes qualification failure; it must not be interpreted as neutral flow.

Run local unit verification from the same Macro root:

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_equity_pressure_response.py tests/test_microstructure_pressure_response_pilot.py
```

These commands are **not** production-deployment instructions. No supplied license key, RTH stream slot, private data file or actual watermark proof was available in this draft PR, and no synthetic measurement should ever be presented as a real session.
