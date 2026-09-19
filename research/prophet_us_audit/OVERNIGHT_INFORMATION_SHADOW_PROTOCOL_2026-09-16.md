# Overnight Information Shadow Protocol — 2026-09-16

**Status:** architecture/research freeze only. No production feed cutover, no 24h chart claim, no Prophet admission/ranking/sizing/trading authority.

**Parent:** Chairman-directed adaptive rotation / Prophet / sector-intelligence programme. This extends the existing data/event/state owners; it does not create a second price store, scheduler, publication plane, opportunity identity, grader or execution engine.

**Procedure pin:** protected `mastermindx-market-intelligence/Mastermind@a78b8fe23d8e1ed129880ac47e97ebe96afa8aea`, Skillpack 1.0.1.

## 1. Current seam and why it matters

Terminal currently has two different concepts that must not be conflated:

- the candle/history path treats US `extended` bars as 04:00–20:00 ET;
- Quote Hub already contains a conditional Alpaca overnight quote seam for 20:00–04:00 ET.

Therefore an overnight price can exist without a corresponding overnight candle/history path. A 4h/extended chart is not presently a 24-hour observation surface. This protocol keeps that distinction explicit.

Primary provider contracts verified on 2026-09-16:

- Alpaca 24/5 docs define overnight market data as 20:00–04:00 ET and expose bars, quotes, trades and snapshots. Historical overnight requests use `feed=boats`; free-plan historical BOATS is delayed and Algo Trader Plus can access BOATS directly.
- Alpaca historical stock bars accept multiple symbols, explicit `feed=boats`, and adjustment choices including `raw`, `split`, `dividend`, and `all`; default adjustment is raw.
- Databento exposes direct Blue Ocean ATS MEMOIR depth as `OCEA.MEMOIR`, with the Blue Ocean Session 20:00–04:00 ET Sunday through Thursday.

Provider documentation establishes capability, not Mastermind's current entitlement. Runtime credential/feed admission remains separately verified before any collection starts.

## 2. Source choice for the first shadow lane

**First candidate:** Alpaca BOATS historical/streaming data, because the existing Quote Hub already contains an Alpaca adapter and BOATS session logic. Reuse that provider/credential boundary; do not build another credential plane.

**Later precision candidate:** Databento `OCEA.MEMOIR` for direct order-book/trade replay when the research question genuinely requires venue-depth or receive-time precision that bars/quotes cannot answer.

No automatic fallback between providers is allowed inside one experiment. A provider/source change creates a new source stratum/version; it does not silently continue the same series.

## 3. Trading-session identity across midnight

Never identify the BOATS observation by naive calendar date alone.

For a valid NYSE trading session `D`:

- the evening leg begins at 20:00 ET on the prior eligible calendar evening;
- the overnight leg ends at 04:00 ET on session date `D`;
- 20:00–23:59 observations therefore bind to the *next* trading-session identity, while 00:00–04:00 observations bind to that same `D` identity.

The existing canonical NYSE/session calendar remains the authority for holidays/closures. Do not recreate a holiday table in this lane. Alpaca notes that the overnight session follows the NYSE holiday calendar and does not run on the prior evening when the next session is a holiday.

Required keys for every retained observation:

- `symbol` / canonical security identity where available;
- `trading_session_date`;
- `event_time_utc` plus source timestamp basis;
- `observed_at_utc` for prospective captures;
- `source_provider` and `source_feed` (`alpaca` / `boats` initially);
- `interval` / event type;
- requested adjustment basis;
- source schema/version and collection version.

## 4. Price-basis law

Do not join Alpaca BOATS default-raw history to the existing Massive `adjusted=true` store and call the resulting return continuous.

For the first BOATS qualification, explicitly request `adjustment=split` and verify the endpoint actually returns that contract for the BOATS feed before admitting the series. If it is unsupported or materially inconsistent, the lane stays held and the experiment is stratified or transformed by the existing corporate-action owner instead of silently mixing bases.

Adjustment metadata does not prove historical first-availability time. Historical re-downloads can prove current source bytes, not what the system could have known on an old date.

## 5. Shadow observation object

The first implementation should project into an additive, research-only observation object through existing research storage/receipts. It is not another canonical quote/bar store.

Minimum fields:

- session identity and source fields above;
- first/last BOATS price observed for the session;
- high/low and total traded volume over actually observed BOATS bars;
- observed bar count and expected-grid count separately;
- longest observed no-bar interval;
- prior regular-session close and prior 20:00 reference when legitimately available;
- return from prior RTH close to overnight close;
- BOATS-only return 20:00→04:00 when both endpoints are observed;
- overnight range normalized by a trailing causal regular-session volatility scale;
- maximum favorable/adverse excursion from the declared reference;
- reversion fraction by 04:00 after the largest overnight excursion;
- quote spread/depth descriptors only when an entitled quote source is actually collected;
- explicit `coverage_state`, `missing_reason`, and `basis_state`.

No-bar intervals remain missing/no qualifying trade evidence. Do not forward-fill them into synthetic flat candles or infer that the market was inactive.

## 6. Overnight sweep / gap features without hindsight

The user hypothesis is that corrections, gap fills and liquidity sweeps increasingly complete outside RTH. Test it causally rather than encoding the conclusion.

Candidate deterministic features at the end of the BOATS session:

- `overnight_return_from_rth_close`;
- `overnight_range_sigma`;
- `overnight_max_up_sigma` / `overnight_max_down_sigma`;
- `overnight_close_location` inside the observed BOATS range;
- `overnight_reversion_fraction` from the largest excursion to the 04:00 observation;
- whether the observed range touched/crossed a preregistered prior-session level (prior close, high, low, approved structural level);
- observed volume relative to the same symbol's trailing BOATS volume distribution once enough history exists;
- source-qualified bar/quote coverage.

A “sweep” label is descriptive unless a separately frozen market-microstructure definition is satisfied. It must not be an LLM interpretation of a chart.

## 7. First experiment: information only, regular-hours execution fixed

Primary question:

> On the same already-eligible structural opportunity episodes, does adding source-qualified BOATS information available before RTH improve remaining-opportunity forecasts or entry-timing calibration versus the same model/state without BOATS information?

Frozen arms:

- `O0`: incumbent regular + current extended information only;
- `O1`: identical model/state plus BOATS-derived information features available by the preregistered cutoff.

Hold fixed:

- opportunity/episode population;
- slow structural eligibility;
- model family and hyperparameters;
- regular-hours first-attainable execution policy;
- outcome horizons and invalidation definitions;
- price/universe basis;
- chronological train/calibration/test folds.

This arm does **not** execute overnight. Its action remains the first admissible regular-session action after the information cutoff. That isolates information value from spread/liquidity/execution value.

## 8. Cutoff and chronology

Use explicit decision cutoffs; do not let the model see BOATS data that arrived after the decision it is grading.

A clean first comparison is a pre-open decision frame in which the BOATS session has completed. Later variants may evaluate event-driven updates during the overnight session, but each update needs its own observed-at clock and first-attainable action.

Historical BOATS downloads lack Mastermind first-seen receipts. Retrospective work therefore proves market-event history under the provider's current archive, not historical ingestion availability. Prospective shadow collection must persist actual observation/collection timestamps through the existing source receipt owner.

## 9. Coverage cohort

Do not select names because their recent overnight behavior was profitable.

Freeze the first cohort before reading O1 outcomes using source-independent criteria such as:

- the existing RPH market/sector ETF panel;
- a predeclared liquidity/universe snapshot from the existing security universe owner;
- predefined Prophet structural episodes whose identity already exists before BOATS outcome analysis.

Report both opportunity denominator and BOATS-source-qualified denominator. A name with missing BOATS data is not economically unattractive; its overnight timing state is unknown/unavailable.

## 10. Evaluation

Forecast metrics:

- paired proper scoring/calibration change by horizon;
- interval width / abstention;
- error after large overnight moves versus ordinary nights;
- calibration lag after macro/event shocks.

Decision-policy shadow metrics with RTH execution fixed:

- paired remaining return/excess from the same eligible episode;
- MAE/MFE;
- target-before-invalidation and time-to-event;
- change in action/abstention timing;
- opportunity lifetime remaining at the first RTH action;
- concentration by date, sector and event regime.

Operational/source metrics:

- source-qualified coverage;
- missing/no-bar rate;
- delayed/error rate;
- correction/re-download difference rate;
- observed-at latency for prospective shadow captures.

No positive-frequency metric alone can promote O1.

## 11. Overnight execution is a later, separate experiment

Only after O1 demonstrates incremental information utility may an execution arm be registered.

That later arm must add its own:

- executable quotes, spreads and depth;
- order type/venue eligibility;
- partial-fill and no-fill states;
- latency and slippage assumptions;
- 20:00–04:00 liquidity regime;
- position/risk limits and rollback.

Historical bars alone cannot support an overnight fill claim.

## 12. Product integration boundary

Do not overload the existing `ext=1` candle flag to mean 24h. `extended` currently has a settled 04:00–20:00 meaning.

If the shadow lane survives:

- Terminal can later expose explicit session layers: regular / pre-post / overnight, with source identity;
- Sector Intelligence can distinguish overnight structural pressure from RTH leadership rather than merge them into one opaque score;
- Prophet can consume BOATS features as a versioned input while keeping structural thesis, entry economics and position management separate;
- Mastermind AI can explain what changed overnight from deterministic state receipts instead of inventing a causal narrative.

Any visible UI requires its own real browser proof and must not imply BOATS coverage where the source state is missing.

## 13. Ordered implementation waves

`ON-A — entitlement/source qualification`: verify current Alpaca credential/feed access without exposing credentials; capture a bounded fixed cohort; verify timestamps, `feed=boats`, adjustment behavior, session identity, missing-bar semantics and historical depth.

`ON-B — deterministic shadow collector`: extend the existing source adapter/receipt path to collect BOATS observations and write a research shadow artifact. No chart/Prophet consumer.

`ON-C — deterministic feature projection`: compute only frozen overnight features with causal cutoffs and explicit nulls.

`ON-D — O0/O1 paired replay`: same episodes/model/RTH execution, with versus without overnight information. Register all looks before outcome inspection.

`ON-E — prospective shadow`: event-driven collection and forecast updates using actual observed-at receipts; nightly reconciliation remains for reproducibility.

`ON-F — product consumer`: only if independently accepted, project the state into existing Prophet/Sector Intelligence/Terminal consumers without changing capital authority.

`ON-G — overnight execution study`: separate commission and proof law.

## 14. Stop conditions

Hold the lane if:

- current BOATS entitlement cannot be verified;
- historical and regular-session price bases cannot be made explicit/compatible;
- cross-midnight session identity is ambiguous;
- missing bars are being synthesized as trades;
- the O1 population differs from O0 for reasons other than source qualification;
- the model/hyperparameters change between arms;
- BOATS features only help after outcome-driven feature selection;
- benefit disappears under paired common episodes or is concentrated in a few dates;
- a historical bar result is being used to claim executable overnight fills;
- implementation would create a second credential, event, price, episode, evaluation or publication authority.

## 15. Capability boundary

The end-state sought here is **overnight awareness**, not “trade 24 hours because we can.” The first valuable capability is knowing whether overnight price discovery materially changes the estimated remaining opportunity before the regular session opens, with exact source/session/time evidence and the ability to abstain when overnight coverage is weak.

Primary sources consulted 2026-09-16:

- Alpaca 24/5 Trading: `https://docs.alpaca.markets/us/docs/245-trading-for-trading-api`
- Alpaca Historical Bars: `https://docs.alpaca.markets/us/reference/stockbarsingle-1`
- Alpaca real-time stock feeds: `https://docs.alpaca.markets/us/v1.1/docs/real-time-stock-pricing-data`
- Databento venues/datasets, Blue Ocean ATS: `https://databento.com/docs/venues-and-datasets/dbeq-summary`

This protocol is a frozen research contract, not proof that BOATS information improves Mastermind forecasts.