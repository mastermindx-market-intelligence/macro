# Adaptive rotation: information, forecast and update contract

Owner: Sol. Parent outcome remains the Chairman's continuously aware multi-horizon rotation and Prophet system, not a diagnostic dashboard. Procedure pin: protected Mastermind `0fe8074ff953b2ced9025ed40f0f66019c759967`, Skillpack 1.0.1. This is a proposed implementation/research contract in existing PR7168, not empirical forecasting proof, runtime admission, a new workstream or trading-policy promotion.

## 1. Material source discoveries and their implications

Terminal PR593 merged the actual-session-close repair. Deployment remains unproven after the earlier tool refusal; do not redo or reroute that deployment. PR594, source `328890d4e7284e5c184c1aa14266ed2f29e335ca`, contains partial intraday lineage components. Its actual API integration is blocked and the required real-route fixture test fails because the new field is absent. Component tests are not an end-to-end success.

A bounded read-only production inventory in this continuation found 4,009 hourly files and 669 five-minute files. These are file counts, not a measured eligible-universe coverage rate. DINO has hourly history but lacks a five-minute file; VLO and XOM have both. This constrains a future intraday rotation design, but does not establish the cause of today's daily Prophet energy admission behavior.

The thirteen readable files in the seven-name/two-grain sample lack explicit adjustment/availability receipts. SPY and NVDA five-minute stores each contain 60,000 rows spanning different calendar periods. Current `ingest/backfill_intraday.py` caps incremental history by row count and sets `asof` to the last bar-start display epoch. Neither the file label nor that time proves historical first availability. Exact file hashes and limitations are in Terminal PR594's `docs/ROTATION_INTRADAY_LINEAGE_2026-09-16.md`.

Design consequence: distinguish market state from information state. A data-poor name must not become economically unattractive merely because our finest source is unavailable. Retain the daily thesis and show that precise timing is unassessed. Track source-qualified denominator alongside opportunity denominator so a sector does not silently disappear when only its intraday coverage is weak.

## 2. Four separately observable clocks

Keep source event time, actual information availability, feature/forecast computation, and user-visible publication separate. Existing source/episode/plan/publication owners retain them; this does not create another clock database. A completed exchange session does not by itself prove a finalized vendor revision. A recent server response does not prove recent market information. A historical bar timestamp is not a historical ingestion receipt.

The existing Terminal display epoch is a chart coordinate, not a UTC event instant. Preserve that identity through the source adapter; only a declared conversion can produce an actual market instant. Endpoint-specific vendor timestamp units govern query construction. The formal Massive aggregate REST specification uses milliseconds, despite a generic FAQ's conflicting nanosecond wording.

Later source corrections must not rewrite which feature version, plan version or publication a past decision used. A present-day byte hash is useful current identity, not retroactive point-in-time proof. Existing immutable source/checkpoint owners are the extension targets.

## 3. Adapt four behaviors at different rates

**Observation cadence:** reuse the existing collectors and Entry Radar/event-spool paths. Update features when a relevant source changes; expensive universe-wide reconciliation remains a separate batch responsibility. Nightly builds remain useful for reconciliation and reproducibility, but should not be the sole opportunity-discovery clock.

**Opportunity reconsideration:** evaluate an affected security, sector or thesis when the declared dependency changes, not on every unrelated tick. Preserve the original holding intent and episode identity. A shorter-term entry warning is not automatically an instruction to liquidate a longer-term holding. A newly strong sector is not automatically a fresh buy at any price.

**Forecast uncertainty:** study whether horizon-specific uncertainty can adapt to matured forecast errors while the predictive model stays fixed. This is a cleaner initial experiment than simultaneously changing model family, data source, ranking and risk policy. Wider uncertainty and abstention are legitimate outputs; a new confidence number is not a trading override.

**Model or capital policy:** retain versioned approval and separate validation. Do not continuously retrain or switch exposure merely because the observed state moves. An adaptive controller may eventually choose among approved alternatives only after incremental utility, turnover, attainable execution and rollback are established.

This cadence separation is a proposed integration approach over existing owners, not a new scheduler or live implementation claim.

## 4. Forecast the remaining opportunity, not an oscillator label

Proposed target family: for each registered horizon, estimate the distribution of attainable return and adverse excursion, whether a declared target precedes invalidation, and how long an opportunity remains usable. Keep directional thesis, leadership, new-entry economics and position management as different decisions. A bullish slow cross can coexist with unattractive entry economics; a stretched short-term reading can coexist with durable continuation. Neither case is resolved by a universal additional confirmation rule.

Targets must use the first attainable action after information availability. Same-close signal marks are diagnostics, not fills. If an OHLC bar contains both target and invalidation, do not choose the favorable ordering; mark the path ambiguous unless admissible finer data resolves it. Keep open/censored outcomes and missing data distinct from losses or successes. Multi-horizon labels mature at different times, so online calibration cannot consume tomorrow's outcome in today's update.

The market-state representation should retain hierarchical market/sector/security measurements of dispersion, leadership persistence, dependence, liquidity, shock exposure and path behavior. State uncertainty and source coverage accompany those measurements. An asset's eligibility for a particular data-dependent model is separate from its economic attractiveness. No per-name search for the retrospectively best grain/anchor/kernel is authorized.

## 5. A bounded uncertainty challenger, not a new strategy engine

Gibbs and Candes' adaptive conformal work supplies a relevant research pattern: wrap an existing forecaster with an online uncertainty procedure. Their 2024 extension targets adaptation over local intervals and includes volatility forecasting examples. It does not prove profitable entries for Mastermind, uniform conditional coverage for every security/regime, or safe sizing from an interval. Treat it as a candidate method, not a guarantee.

Proposed first comparison: freeze one already-admitted forecasting family and its horizon, inputs and decision-version lineage. Compare incumbent uncertainty with an adaptive calibration wrapper using only matured outcomes. Evaluate coverage, interval width, calibration lag after changes, and selective-abstention behavior under chronological replay. Cluster shared dates/episodes; do not treat correlated tickers as independent regime observations. Preserve a common calendar window and source-qualified population. A forecasting-quality gain remains distinct from any downstream trading-policy gain.

This is not yet a preregistration or execution authorization. The current data/Temporal Grain/TrialLedger gates still apply. Keep look budgets and all tried configurations with the existing evaluation owner. Backtest selection papers motivate accounting for multiple trials, but no statistical correction replaces point-in-time inputs, chronological validation or forward evidence.

## 6. Overnight awareness: observation is not execution

Massive aggregates use qualifying trades; some intervals have no aggregate and many extended-hours trade conditions do not update those bars. Therefore sparse candle history cannot by itself establish that price discovery was absent. Do not synthesize flat bars, impute a sweep, or call every gap a feed outage. Keep aggregate evidence, eligible/all-trade evidence and executable quote evidence separate.

The first overnight-information experiment should keep regular-hours execution fixed and add only legitimately available extended-session observations. A later overnight-execution study needs its own liquidity, spread, fill and venue assumptions. Documented 04:00-20:00 coverage is not a full 20:00-04:00 entitlement. REST split-adjusted series and raw flat files are not silently interchangeable; price and volume basis must be jointly declared.

A compact proving cohort should be selected by source availability and a frozen coverage rule before reading outcomes, not by which names recently won. Energy examples provide a coverage stress case, not a preordained profitable portfolio. Any broader expansion reuses current data stores, issuer/security identities and event owners.

## 7. Ordered implementation and stop boundaries

1. Complete PR594's existing API consumer after the route-write gate is resolved. Verify actual returned-bar/date/cache evidence without changing candles. Do not call its current pure projection a live endpoint.
2. Through the existing ingestion/data owner, qualify one common-basis finer/daily source family with explicit retention, correction and availability semantics. Do not overwrite historical files with invented receipts or infer missing fields from today's source code. The thirteen-file sample is not a complete estate audit.
3. Resolve exact episode-to-plan-to-private-publication linkage under the current Prophet owner; PR7180 already owns overlapping origination/source-clock work. No competing write or ticker-proximity substitute.
4. Under existing research owners, preregister the limited horizon/uncertainty comparison and the separate extended-information arm. No W3 or outcome gate is lifted here.
5. Only surviving forecasts proceed to an explicitly versioned decision-policy test and then forward shadow evidence. Capital/rank/admission changes remain prohibited until independently accepted.

The full ambition is a coherent market-aware decision workflow. These dependencies are not an excuse to replace intelligence with more provenance, and source correctness is not the claimed investment edge. They establish which observations and decision outcomes the intelligence is allowed to learn from.

## Primary sources read in this continuation

- Massive Custom Bars, formal stock REST contract: https://www.massive.com/docs/rest/stocks/aggregates/custom-bars
- Massive stock flat files: https://massive.com/docs/flat-files/stocks/overview
- Massive extended-hours trade/aggregate distinctions: https://massive.com/knowledge-base/article/does-massive-offer-pre-market-and-after-hours-data
- Gibbs and Candes, Adaptive Conformal Inference Under Distribution Shift, NeurIPS 2021: https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html
- Gibbs and Candes, Conformal Inference for Online Prediction with Arbitrary Distribution Shifts, JMLR 2024: https://www.jmlr.org/beta/papers/v25/22-1218.html
- Bailey et al., The Probability of Backtest Overfitting, 2015: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

Literature observations here are bounded to the primary abstracts/documentation reviewed; no paper's experiments were independently replicated in this turn. All proposed Mastermind methods remain unvalidated until the named controlled studies actually run.