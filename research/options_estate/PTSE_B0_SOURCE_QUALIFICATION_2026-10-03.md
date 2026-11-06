# PTSE-B0-H5-v1 — price/source qualification receipt

Date: 2026-10-03 (execution continued into 2026-10-04 UTC).
Parent: Macro #7925.
Implementation carrier: #8364.
Architecture carrier: #8325.
Frozen event-qualified C1 carrier: #7929.
Initial source census pin: Macro `786e180f88bf5a47d705ed477969cdd1f7d46823`.\nContinuation re-census pin: Macro main `818d1bcea9f878a3872d341b6ee355441fd620cf`.

## Disposition

**Current actual-data PTSE-B0-H5-v1 disposition: `NON_EVALUABLE / SOURCE_NOT_QUALIFIED + PROTOCOL_NOT_RATIFIED`.**

This is a source/protocol disposition, not an empirical timing result, market null, model failure, forecast qualification, or production ruling. No protected outcome values were opened to reach it.

The separately implemented source-independent B0 runner is software-complete enough to exercise synthetic conformance, but it deliberately refuses to manufacture source admission or numerical research law. Event, Options and full feature-family history are **not** dependencies of B0.

## Exact target requirement

The proposed B0 target retains the C1-compatible continuous H5 closing-path downside measurement:

`Y5(t) = max(0, -min(log(T[t+k]/T[t]) for k=1..5)) / (v20(t) * sqrt(5))`.

For an actual run the research owner therefore needs, at minimum, a decision-time-qualified SPY panel that can distinguish:

- split/share-count-adjusted structural closes `S`;
- split-and-distribution-aware total-return closes `T`;
- the adjustment/corporate-action vintage actually available for each origin;
- attributable source availability no later than the decision cutoff;
- complete session/horizon identity and mature outcomes.

A present-day adjusted series without its vintage cannot be silently treated as historical PIT replay.

## Source census

### 1. Massive daily archive — deep and rights-cleared, but not the required dual basis

Current committed manifest:
- path: `data/massive_stock_day/_manifest.json`
- blob: `d6ad060e3d0af3296757883f43e955012f9564d8`
- coverage: 2021-07-06 through 2026-10-02
- processed days: 1,369
- SPY anchor: 1,318 rows; first 2021-07-06; last 2026-10-02; maximum calendar gap 4 days.

Rights:
- `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0`.
- `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`, blob `a9ee6f288bfb2716facd88dcf2c5135ca8125303`, records acquisition, processing, retention and model use for the Massive feed as available under the house entitlement record.

Basis/clock:
- Data OS price vocabulary: `lib/dataos/price.py`, blob `be127fa853a6aafbf0bcb33b58783316ac972faa`, classifies `data/massive_stock_day:close` as raw/unadjusted.
- The existing Market Memory v1 SPY contract, `contracts/market_memory/spy_daily_price_source_observation.v1.schema.json`, blob `7d20efaa85ba8b0a5b9890fbecd7bad92a16f347`, marks historical rows support-only/non-operational, `point_in_time_corporate_actions=false`, `total_return=false`, and `regular_session_close_authenticated=false`.

Result: **`RETROSPECTIVE_PIT_UNPROVEN` and insufficient to construct the exact B0 dual-basis target by itself.** Rights and depth do not manufacture a total-return leg or historical adjustment vintage.

### 2. Yahoo daily store — dual basis exists, but vintage and rights block PTSE fitting

Current Data OS registry:
- `config/dataset_registry.yml`, blob `70a08e25ea45927bed001b3cb1c48e286680525e`.
- dataset `equity.bars.daily.yahoo` is `PRODUCED`, adjustment `dual_basis`.
- `close` is the measured total-return-adjusted leg; `close_price` is the split-adjusted / dividend-unadjusted leg.
- registry notes explicitly state both bases are re-adjusted on each Yahoo fetch and that `adjustment_asof` is owed and not carried.

Rights:
- `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`, blob `a9ee6f288bfb2716facd88dcf2c5135ca8125303`, classifies Basket/SPY closes as internal-only and records **no model-use right**; Yahoo registry licensing remains `vendor_terms_personal_use`.

Result: **not admitted for PTSE model fitting.** It has the two numerical basis families but cannot establish historical PIT vintage and does not currently carry the model-use right needed for this study. Combining it with a licensed raw Massive leg does not cure either defect.

### 3. Market Memory M0D v2 REST successor — prospective candidate, current contract conflict

Accepted existing decisions:
- `agentos/decisions/DEC-W2C-M0C-V2-HYBRID-PRICE-ACTIVITY-SCOPE.md`, blob `919cd320b1113f3f2d553665de479725eda5bb81`.
- `agentos/decisions/DEC-W2C-M0C-SOL-RATIFIED-REST-SUCCESSOR.md`, blob `c1c5d1cc61172d7c5bfa07d51779067b6892e1eb`.

They require:
- profile `market_memory.private.spy_rth_price_fullday_activity_daily_aggregate.v2`;
- basis `massive_rest_day_aggs_unadjusted_rth_price_fullday_activity`;
- XNYS regular-session price rungs;
- `regular_session_close_authenticated=true`;
- full-market-day volume/transaction activity.

Current executable:
- `scripts/capture_market_memory_technicals_v2.py`, blob `e10ecd2de4b690a930dada0cd7af37d2b94e11c7`, whose module-level freeze states the same true/RTH-price contract but whose emitted `feature_object` currently writes `regular_session_close_authenticated=false` and `price_basis=unadjusted_daily_aggregate_sealed_rest_bar`.
- `scripts/accrue_market_memory_spy_experience_v2.py`, blob `8e779d3f008fb6c4a353fb9e9e46c507b41b601f`, emits the same false/generic pair into admitted experience rows.

Result: **`SOURCE_CONTRACT_CONFLICT` for the PTSE initial REGULAR-session live reader.** PTSE does not relabel or repair the incumbent source. The bounded return is saved on MAS-94 comment `3aed9c44-d602-49d6-9160-ba3a7a147de0`; the existing M0D owner must reconcile its own code/decision/prospective evidence.

Even after that conflict is repaired, M0D v2 is a prospective source vertical; it does not retroactively create a multi-era dual-basis PIT panel for historical B0.

### 4. Data OS selected-price evidence carrier — useful evidence, still not the B0 target source

The current bounded Data OS price-evidence carrier is **Macro #8183**, branch semantics at exact head `3ad47339cc11b54a61ba677490bcd41fab32cc61` (Draft / HOLD at this census).

Its accepted scope is materially useful to PTSE because it upgrades the **existing** adjusted-first price ladder with opt-in evidence for the actual selected object:
- ladder source and relative path;
- selected parquet column;
- exact basis only where the incumbent source contract can support it;
- SHA-256 and byte count of the exact encoded object that was decoded;
- explicit nulls where adjustment vintage, RTH/auction session, venue or historical observed-at semantics remain unproven.

The independent review caught an overclaim in the first candidate: the legacy `closes_cache_UNADJUSTED` source tag was being promoted to canonical `RAW` even though the native cache producer may use `auto_adjust=True`. The same-carrier repair at `3ad47339...` preserves the legacy selected values/rung/source tag but changes canonical basis to **null / unknown** unless a source owner actually attests it. Current semantic blobs recorded by the owner are:
- `engine/price_ladder.py` blob `12b4d54e071fd2ca288e5ea4837851d6bdf71e34`;
- `tests/test_price_ladder.py` blob `3410103be724a098dbcdb09d30ced4cf798fbdca`;
- Data OS vocabulary remains `lib/dataos/price.py` blob `be127fa853a6aafbf0bcb33b58783316ac972faa`.

Exact-head hosted CI/fences for #8183 are green and the cache-basis semantic defect has been independently requalified as closed, but the carrier remains on release HOLD for source-custody / changed-suite CI ownership / formal release state. More importantly for PTSE, **#8183 deliberately does not manufacture `adjustment_asof`, corporate-action factors, RTH/auction session identity, venue or historical first-availability**.

Therefore #8183 improves exact selected-source evidence and is the correct incumbent path to consume later, but it still does **not** supply the rights-cleared historical raw+factor/vintage panel required for confirmatory B0.

Cross-owner corroboration: **Macro #8069 is a Prophet Q06 carrier, not the Data OS owner.** Its U.S. outcome-price source ruling independently records the same gap: Massive daily prices are unadjusted, the local store lacks session/venue/source timestamp, and “Data OS V2 raw-plus-factor derivation and a corporate-action factor table are not built.” That statement is corroborating source evidence only and must not be mistaken for #8069 owning the price implementation.

## Data OS conclusion

Current Data OS correctly describes adjusted prices as point-in-time quantities. The available V1 vocabulary labels raw/split-adjusted/total-return bases, but current adjusted stores do not carry the historical `adjustment_asof` required to turn today's restated values into a protected historical decision-time panel.

There is therefore no lawful current-source shortcut from:
- licensed raw Massive history,
- current-vintage Yahoo dual-basis history,
- or prospective M0D REST receipts

to a confirmatory dual-basis B0 dataset.

A future accepted raw-plus-corporate-action-factor route may solve this under the existing Data OS owner. PTSE must consume that owner if and when it exists rather than build a second corporate-action store or price authority.

## Source-independent implementation now available

`research/options_estate/ptse_baseline.py` implements the source-independent `PTSE-B0-H5-v1` benchmark contract.

It has no embedded numerical research defaults and requires an explicit protocol packet containing:
- owner ratification reference;
- source-manifest and calendar digests;
- feature and evaluation-partition identity;
- explicit ridge alpha;
- explicit minimum train support;
- explicit mode/evidence grade.

CONFIRMATORY mode rejects `RETROSPECTIVE_PIT_UNPROVEN`. The runner enforces source-known-at <= decision time, mature labels, outcome-window purge at fit cutoff, chronological/disjoint evaluation, train-only scaling, a past-only mean reference, and the registered P-vector ridge arm. It emits no research-pass, probability or decision authority.

At implementation head `b1c7b88fbd878d6384a465a8607bbacf17f4fb5d`, the exact remote PTSE code/test bytes pass **173 methods** total across the W2 contract/consumer, B0 benchmark contract, passive market/regime adapter, bounded Options adapter, NEW_ENTRY compiler, PULLBACK_BUY compiler, prospective-readiness validator and fail-closed post-entry action coverage. This remains software/conformance evidence, not empirical B0 validation.

## Exact next source/science gates

1. **Price/Data OS owner:** return an immutable, rights-cleared dual-basis SPY source manifest with adjustment vintage / historical availability sufficient for the registered target, or an explicit non-evaluable disposition. Do not create this inside PTSE.
2. **Market Memory owner:** reconcile the v2 true/false regular-session contract before PTSE consumes its live observation.
3. **PTSE scientific owner:** ratify the exact B0 protocol values/partitions only after the intended source manifest and prior-history exposure are known, and before protected outcome access.
4. **Then:** execute the real B0 runner once on admitted data, retain every trial/failure, and report `RESEARCH_PASS | NO_INCREMENTAL_EVIDENCE | REFUTED_CONSTRUCTION | INCONCLUSIVE | NON_EVALUABLE` or the accepted equivalent.

No event/calendar or Options completion is added as a global B0 dependency. No current finding here grants forecast, rank, admission, entry, plan, alert, sizing, portfolio, execution or trading authority.
