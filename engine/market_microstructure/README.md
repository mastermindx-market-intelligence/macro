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

## Matured forward-response outcomes — separate from live recognition

`engine.market_microstructure.matured_response.measure_matured_response` adds the **evaluation-only** `equity.price_response_evaluation_label/v0` contract. It requires an explicit original decision cutoff, anchor quote eligible at that original cutoff, a forward endpoint, an already-matured source watermark/receipt, market-session health, and fresh qualified NBBO at the endpoint.

A future quote not received by its evaluation cutoff cannot be applied retroactively. A halted/unknown market, stale/locked/ambiguous quote or absent maturity produces a typed null/censored outcome. A quiet symbol may legitimately reuse an unchanged best quote only while it still passes the declared age bound—lack of a new quote by itself is not a malfunction. Source quality, original custody and quote-stream coverage remain externally qualified by TP-1, not authenticated by the evaluation math.

The output has `authority=RESEARCH_OUTCOME_LABEL_ONLY` and leaves `absorption_signal`, `signal`, trade fills and execution-adjusted returns null. It may support preregistered future-outcome validation only after source qualification; it grants no entry/rank/sizing/alert authority and is not part of the earlier candidate's information set.

**Candidate acceptance:** At `9048a47caf90ea89e59ba71b2480a0db63ed1a81`, M2 Studio ran both existing R0 test suites including 16 new matured-response falsifiers: **58 passed**. Hosted exact-head CI, independent reviewer and real source evidence remain separate acceptance requirements.


## TP-1 canonical minute-to-R0 compatibility bridge

The additive pure research leaf `engine.market_microstructure.tp1_context.project_tp1_pressure_context` consumes the existing **TP-1 minute observations** (`equity.tick_plane.minute_observation/v0`) plus normalized SIP quote updates (`equity.tick_plane.stream_event/v0`). It deliberately does **not** transform correction-provisional WebSocket prints into the original R0 consumer's `revision=0/action=ORIGINAL` trade records, and it never reclassifies signed trades. Macro TP-1 remains the one signing and source-time owner.

The bridge requires contiguous 1–5 minute packets; the original minute/source arrival cutoffs; condition and exchange-reference SHAs; no source-authority fields or future labels; per-quote original frame/receipt and versioned quote-condition eligibility; and separately attested TP-1 capture continuity. Invalid, absent or unqualified quote updates remain as invalid top-of-book states, not discarded updates that resurrect prior eligible BBOs. A 30-second study needs separately eligible sub-minute evidence; a minute rollup alone cannot supply it.

Output `equity.pressure_response.tp1_context/v0` is **correction-provisional research context only**. It preserves gross/known/unknown/condition-excluded/TRF denominators, source-original timing, separate SHA-256 digests for each source-minute generation and for the quote observations, price-response bps, and NBBO top-size recovery **proxy**. `absorption_signal`, future outcome, trading execution, rank and any probability remain null/false. The source-condition and capture flags are externally asserted and are not cryptographic proof of completeness; no automatic production eligibility is implied.

**Test evidence (October 8, 2026):** PR candidate `9ab3f85ce59f6fc8b9c7134d2e90d01d1366ac50` passed **85 tests** on M2 Studio against its exact source/test blobs (bridge blob `9b80f73ad82731bd40b142bffc34e002b8e7150f`, fixture blob `ec35b2b149a82cd36dc8ecd3b6b6e61604cb552b`). The 85 include 23 original TP-1 bridge falsifiers and 4 follow-up source-digest/count-integrity regressions. Separate cross-branch integration verified actual TP-1 `stream_events→condition_policy→exchange_reference→asof_nbbo→print_observations→minute_projection` at TP-1 `7f03ffd50ed3eb1c53f7998fe27adeae5211ace9`, then R0 bridge `8203e5e9ad53234c62f8e5fa7358fe0971afa507`, with two synthetic source-native prints, exact `$1009/$1001` buy/sell proxies, zero price response and null signal. Neither suite tests a live Massive frame, true original source completeness or forward edge.

**Integration admission:** this adapter does not import unmerged TP-1 code in the R0 PR, so current standalone R0 tests remain CI-enrollable without a circular PR dependency. After TP-1 acceptance, the integration owner should rerun the cross-branch fixture against the accepted shared SHA and prove real source-to-consumer causality; do not invent a second signer or duplicate the stream.

### Canonical TP-1 quote-policy and complete captured-frame reconciliation

The R0 `tp1_context` compatibility bridge now accepts only the exact TP-1 `equity.tick_plane.quote_condition_admission/v0` per-quote receipt shape: source quote ID, native condition and indicator array, immutable original frame digest/availability, source-review/condition-policy SHA-256 and independently recorded policy decision cutoff. A loose `eligible=True` or retired `rules_sha256` receipt fails closed. The **minute packet's** `quote_condition_rules_sha256` must equal the actually observed normalized quote verdict generation, with mixed or absent versions rejected. The bridge still consumes TP-1 minute **already-signed** buy/sell/unknown totals and does not reclassify prints or retrofit trade corrections.

R0 test candidate `4be612b27edb5e25a3232e2f26471afc79e97acb` passed **92 tests** locally at M2 Studio (bridge blob `b063180470aca7b504a80b9661f233f02523a994`). An additional cross-branch test against source TP-1 head `7ed3088acb13a3a08514573a357c8be4e1a07035` used four synthetic original frame buffers carrying three Q updates and two T prints; it exercised the actual TP-1 batch decoding, source conditions and venue checks, quote-policy review, as-of NBBO ring, provisional trade classification, minute compiler and R0 bridge. Outcome: `$1009` buyer-location proxy, `$1001` seller-location proxy, zero bps completed-window midpoint response, qualified best-quote size-recovery **proxy**, two separate source reference digests, original ordered-frame digest and `absorption_signal=None`. Source quality remained `EXTERNAL_OWNER_RECEIPTS_REQUIRED`: this is not evidence of real market capture, a predictive edge or licensed publication.

**Important temporal/authority boundary:** A user's or worker's claim of original availability is never equivalent to a source-operator receipt, despite typed fields and content digests. TP-1 still lacks admitted single-socket real-time production, source-authenticated feed completeness and private-R2 publication; PR #8660 has an outstanding contract-delta CI enrollment blocker. This branch must not be merged into real-time Terminal/Prophet consumers until the actual owner supplies production and independent review receipts.

### Source-to-research quote-age policy agreement

The newest TP-1 typed trade observation includes the `quote_age_limit_ns` used when deciding whether a trade had a sufficiently fresh prior NBBO. Its minute compiler preserves exactly one `max_quote_age_ns` admission policy for the full minute. The R0 `tp1_context` reader requires the source policy to be **at least as strict as** the study's `max_quote_age_ns`; otherwise `MINUTE_NOT_QUALIFIED / SOURCE_QUOTE_AGE_POLICY_TOO_LENIENT`. It also refuses mixed source age rules across constituent minutes. Thus an old upstream quote-rule classification cannot be relabeled as a tight quote-age sample after the fact.

At R0 source head `a520da79ccfee637673f27c0d8cca6091f81ee04`, **95 tests passed** locally on M2 Studio. A direct cross-branch test with source TP-1 `04e737a2ad35e43f32719d47c37e9d3250b93ae8` accepted the same synthetic four original frame buffers, two trades and a 25-second source/research age limit while rejecting a one-second research interpretation. Buy/sell proxy notionals remained `1009.0/1001.0`, prediction null. Neither this source test nor the code's caller-supplied completeness flag proves genuine provider packet continuity or price-impact alpha.

## Real-data and production gates

1. **Consume, do not repeat, the 2026-08-08 TP-0.5 socket experiment** recorded in Massive masterplan §3.1b.4: delayed and real-time are separate buckets, but opening a second real-time socket evicts the oldest. Verify the *current* Quote Hub `/health` effective cluster and original TP-1 live-slot owner without starting any rival RT WebSocket. Qualify T/Q real RTH frames, event/receipt clocks and remaining source gates only inside the admitted owner/maintenance path.
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

## Private TP-1/R0 handoff checkpoint — 2026-10-09

**Latest verified R0 candidate:** `5c9ea3e78349315ad8fe56202d10e12fe086e017`. Full R0 source/test suite **128 passed locally** on M2 Studio, using exact GitHub source blob `896c5d2622458aa2930f47509ac050d8ba2bd18f` for `engine/market_microstructure/private_context_view.py` and fixture blob `21e3cb07d38028923063be8ce61408a99fcd6db6`. The earlier hosted CI failure at `f7d5e057...` included one R0-specific incorrect bid-recovery test expectation, plus an unrelated Intelligence Hub template failure. The R0 test expectation has been corrected and source verified locally; exact latest-head hosted CI and independent review still determine release acceptance.

**Pure private handoff (no new storage plane):** `private_context_view.project_private_research_context` serializes one already-qualified `equity.pressure_response.tp1_context/v0` into **allowlisted canonical JSON bytes** and a byte-exact SHA-256 receipt. Quote-size recovery fields are exact decimal strings labeled `MEASURED_NBBO_SIZE_PROXY_NOT_ORDER_REPLENISHMENT`; no raw T/Q records, trade IDs, original receipt strings, future labels, signals, execution, rank or public URL. `verify_private_research_context_bytes` validates exact byte length, SHA-256, canonical serialization, nested count/notional/recovery field allowlists, ratio/conservation identities, RTH session, original-source digests and immutable PRIVATE-only status. Even a recomputed matching hash cannot promote raw source, finality, signal or public publication. No vendor-authenticity claim or private-R2 install is made.

**Independent cross-PR source test:** TP-1 head `0c65ff24820eade42e09265dbe627c027480bda5` was paired with R0 head `5c9ea3e78349315ad8fe56202d10e12fe086e017`. Combined that TP-1 head's actual `captured_minute` and `private_minute_artifact` code with R0 `5c9ea3e7...`, calling the real source decoder, reference policies, NBBO, minute projection, R0 bridge and both private projection/readback functions. The offline **synthetic** run passed with 2,404 bytes of private TP-1 minute output and 2,247 bytes of private R0 context, source/quote-policy/watermark hash agreement, `1009.0` buy-location proxy and `1001.0` sell-location proxy, and null absorption signal. Both were flagged `public_delivery_allowed=false`; no raw vendor data was acquired. This is a compatibility proof and **not** proof of 99% RTH connectivity, qualified native condition table, private R2 delivery, original source completeness or alpha.

**Still required:** TP-1 #8660's separately owned original-source/host and denied CI-manifest clearance, independent exact-head review, genuine one-owner T/Q data and correction lineage, licensed private store and authenticated Terminal consumer/browser proof. Do not merge R0 into ranking/entry/Prophet until the source owner and prospective statistics have qualified it.


## TP-1 source-qualified matured label protocol — 2026-10-10

`tp1_matured_response.project_tp1_matured_response` joins one byte-verified
private R0 feature to a separate 30-second, 2-minute or 5-minute NBBO response
label. The feature SHA-256, length and original `decision_ns=T` stay fixed;
the anchor remains T. Horizon, evaluation cutoff E and quote-age policy have
a separate specification fingerprint. This records the supplied specification,
not preregistration or actual platform emission.

The adapter shares `tp1_context` quote normalization/admission and calls the
existing `measure_matured_response` selector/arithmetic. It does not sign
trades. Original and later native Q/verdict generations together are bounded
by the existing 20,000-quote limit. Source policy/venue vintages must agree
with the original feature. Latest nonfirm, crossed, zero-size or ambiguous
updates invalidate their endpoint; they cannot resurrect an older firm quote.

| Evidence boundary | Required meaning |
| --- | --- |
| Frozen original feature | Exact private bytes/hash/length; original normalized-Q digest and count must reproduce the feature. Original full typed-verdict digest has its own supplied frozen receipt, available by T and no earlier than its verdicts. |
| Original source clock | Original event watermark covers `feature.end_ns` and its receipt is known by T. Separately, owner-attested `ORIGINAL_FRAME_RECEIPT` snapshot continuity covers T. Positive event/watermark lag is permitted; event completeness through T is not claimed. |
| Original health | Required basis `LATEST_STATUS_AS_SEEN_AT_SNAPSHOT`: latest status actually available by T. Output exposes its receipt time and age at T. This does not claim event-time health completeness through T or introduce a maximum health-age policy. |
| Later source clock | Canonical TP-1 endpoint minute and watermark are mature by E. The later interval health/continuity evidence covers the anchor-age interval through the horizon and can censor a label without modifying the feature. |
| Evidence serialization | Original evidence wrapper may arrive after T; its availability is separate from the original snapshot and frozen verdict-fingerprint receipt. Later wrapper binds normalized Q and endpoint minute and must follow their raw receipts; full later verdict metadata has a separate digest/clock. |
| First knowability | Maximum of all material supplied feature, quote, verdict, fingerprint, reference, minute/watermark, health and wrapper availability clocks. It means earliest knowable from supplied evidence, never asserted actual emission. |

A mature `NO_SAMPLED_PRINTS` source minute can support a quote-only endpoint.
No trade volume, pressure, zero activity or alpha is inferred from that state.
An unavailable clock, changed original digest, missing custody/continuity
assertion, gap, halt, stale quote or unresolved source qualification yields a
typed refusal/abstention and no numerical label. Original quotes received after
T cannot repair the anchor; later archive entries unavailable by E are excluded.

The separate label preserves `STREAM_PROVISIONAL_UNRECONCILED` and private
distribution limits. Signal, absorption, alpha and execution return remain
null; rank/trade/alert/publication/promotion authority remains false.
Owner receipts and their fingerprints are supplied frozen evidence requiring
external provenance. Caller assertions, hashes and synthetic compatibility
tests do not authenticate capture, prove market completeness or open a service.

The existing `tests/test_equity_pressure_response.py` contains the adapter
falsifiers; no new CI enrollment is needed. A bounded synthetic integration
also exercises the actual TP-1 captured-frame composer, native policy/reference
parsers, provisional print/minute pipeline, R0 feature/private projection and
this label adapter. A condition-ineligible latest quote with positive prices
and sizes must produce `UNOBSERVABLE / INVALID_NBBO`, not the naive
199.0049751243781094527363200 bp return. Status remains **BUILT_NOT_PROVEN**.
