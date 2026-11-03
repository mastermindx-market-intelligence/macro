# D06 Macro research route contracts

**Scope: design and migration specification at Macro fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9.** No collector, builder, model, backtest or production query was executed. These contracts preserve source behavior and identify contradictions for the existing owners. They do not validate investment claims.

## Market Structure

### Product, producer and publication

The page explains dealer exposure, modeled systematic positioning, volatility, stock-picker conditions and a locked weekly range. Keep these independent analytical objects; no combined VC+CTA score or implied observed fund transactions.

Actual flow: [scripts/build_market_structure.py](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_market_structure.py) assembles data/market_structure/latest.json with schema market_structure_context.v1, deterministic history.parquet and nightly-only ledger.parquet. It imports engine.systematic_flows and engine.market_structure_context.build_changes. [build_market_structure_page.py](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_market_structure_page.py) renders [the template](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/market_structure.html.j2) through lib.pages.write_page.

The page builder's “market_structure_context.py not yet built” comment is stale. That module exists as a change-feed helper; it is not the primary artifact builder. Do not carry the census's unknown-source assumption into implementation.

Root fields: schema,asof,built_at,is_context_only=true,display_only=true,gamma,systematic,vol,dispersion,week_map,state_changes,prev_state. Independently missing blocks must not hide valid siblings.

### Fields, units and time

| Block | Actual input / key fields | Correct interpretation |
| --- | --- | --- |
| gamma | data/cboe/gex_SPX.parquet; net_gex_bn,net_gex_pctile,gamma_flip,spot,dist_to_flip_pct,regime,history,coverage | Exposure billions; percentile0–100 over stored history; flip/spot SPX index levels; distance=(spot−flip)/spot×100. Retain observed count, expected session, gaps and coverage receipt |
| systematic.vc | SPX close data/yahoo/_GSPC.parquet; representative$300B AUM,10% annual volatility target; alloc_frac,alloc_bn,flow_1d_bn,flow_5d_bn | Fraction and modeled billions. Actual rolling sample count qualifies state. Not observed money movement |
| systematic.cta | Same close history; normalized20/50/100/200-session trends; score,z,flow_1d,flow_5d,cta_near_flat | Dimensionless values, never dollars. Preserve near-flat producer qualifier and separate VC/CTA meanings |
| vol | rv21,rv63; cboe/vix_curve.parquet tenor,settle,dte | Realized vol annualized fractions→percent; curve slope=M6−M1 in index points |
| dispersion | CboeCOR1M,COR3M,DSPX; history and regime | COR1M percentage-point index units, not0–1correlation. Regime uses up to504prior observations, minimum20,20th/80th cutoffs; annual delta is level difference |
| week_map | SPX close andiv30 at/before last close strictly preceding targetMonday | Width=iv30×sqrt(5/252); ±1σ/±2σ SPX levels. 30-day→five-day scaling assumes flat volatility term structure. Model range, not a market boundary or guarantee |

Root asof normally reflects latest SPX close; if those closes are absent it falls back to current UTC date, so it **cannot certify sibling freshness**. built_at is UTC generation. Gamma separately carries last_obs,expected_last_session,sessions_behind,missing-session lists and observed-versus-session counts. COR/VIX lack equivalent explicit last-observation clocks: display unknown when needed rather than borrowing root asof.

Weekly bands advance to the upcoming week on the weekend using build date in ET; price/IV anchor stays locked. The included gamma flip comes from latest gamma, which may not share that lock date. Show its own basis and do not imply every line was known at the lock time.

Source detail: [builder](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_market_structure.py), [systematic mechanics](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/systematic_flows.py), [change feed](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/market_structure_context.py).

### Historical controls and retained interaction

GEX ranges:21/63/126/252/all observations, default126. Systematic/correlation:63/252/all, default252. Persist independently as msp-gex-range,msp-sys-range,msp-cor-range. “All” is all embedded history, capped500rows by producer; not full history.parquet. Keep actual observation/date summaries, bilingual copy, native buttons, aria-pressed and live status. No page-specific URL query/hash range parser exists.

Primary phone order: concise market-state summary and source date, one dominant history chart, related context in meaningful sections. Range controls stay near their chart. Long charts/tables use contained interaction and textual summaries. Source/assumption details use disclosures without hiding important “model estimate” or stale labels.

### Required corrections, not implemented

1. SVGs use value||0 for missingGEX,spot,flip,VCallocation,COR. Render gaps or explicit unavailable values; true0 remains0.
2. UI recomputes correlation thresholds from≤500embedded rows while producer uses up to504. Use the existing producer's authoritative threshold/state or request its explicit field; do not create an unnoticed second model.
3. Template invents missing2σ bands from1σlow×.975 and1σhigh×1.025, then labels them wide/95%. Missing2σ must remain missing; no fabricated95% interval.
4. VC zero-volatility docstring and code disagree: implementation yieldsNaN. flow_state(None) returns“pausing,” not observed inactivity. Model owner must decide correct unknown-state projection.
5. Separate build, observation and weekly-anchor clocks; missing clocks remain visible.

These are design/data defects to fix through existing owners after review. D06 does not change model parameters, rerun calculations or endorse statistical coverage.

## Stage Analysis

### Product and source graph

Stage Analysis helps an investor screen and compare a classification universe, inspect industry context, earnings/attention/research, then open the exact security for deeper investigation. Its source is weekly-native classification; a “daily” board does not imply a daily-native model.

[scripts/build_stage_analysis.py](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_stage_analysis.py) invokes engine.stage_analysis.build_context_feed, with separate earnings, alt-data and research producers. The engine uses engine.weinstein_stage.classify and current-population inputs for stage_industry and stage_flows. [Page builder](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_stage_analysis_page.py) renders the initial context artifact data/stage_analysis/context/latest.json, schema stage_context.v1, and publishes14JSON files to site/stagedata/.

| Surface | Fetched files | Retained controls and deeper views |
| --- | --- | --- |
| Screener | screener.json | Ticker/name search; industry percentile,SATA,deltaSATA,stage,weeks,ATR,earnings tone/result,rating filters; sort;L1/L2tags; reset;row expansion;local watchlist;CSV |
| Board | stage_board_weekly.json,stage_board_daily.json | Weekly default and daily selector; stage columns, counts, names and context; both use weekly-native classifier |
| Industries | industry_ranks.json,industry_heatmap.json,ec_industry_heatmap.json,industry_flows.json | Ranking;rank heatmap;earnings heatmap score/count;flow industry/sub-industry grain |
| Earnings | earnings_table.json,earnings_season.json,earnings_compare.json | Calls,season,quarter comparison;industry/tone filters;summary reader drawer |
| Alt-data | altdata_trending.json | Google,Reddit,Wikipedia,TikTok columns;source-specific asof;seed/currentness qualifications |
| Research | research_index.json | Search;expand thesis snippets;model-presence badges;external full-note links |

industry_name_pctile.json and ec_industry.json are also published, although these controls do not directly fetch them. Some valid earnings artifacts use surface rather than schema; a universal schema assertion would regress publication.

### Identity, scales and currentness

Rows include ticker,name,sector,region,source,industry; industry percentile,SATA,weekly change,stage/detailed label,weeks,fresh; stage_week_end,stage_source_asof,tri-valued stage_current; ATRextension/ATRprice,MansfieldRS;earnings tone/result;rating;gate/event/blackout/tags. Preserve source scale adapters: SATA0–10,rating0–100,industry percentile0–100,ATRextension in weeklyATR multiples,ATR/price a fraction,earnings tone0–100,result0–10. Live and seed native scales differ before normalization.

“Fresh” means early Stage2 lifecycle (at most10completed weeks), not recent data. source=live identifies classifier lineage, not current observation. Currentness requires row's completed week equal the resolved target; retired names are noncurrent.

Target is population's modal completed week, later week wins ties. SPY corroborates rather than overrides this mode; unresolvedSPY means no target. Stale comments describing aSPY cap are not the implemented resolver. Divergence or<60%current coverage creates an explicit population warning. With no target, headline counts/weather become null; stale/unknown rows stay browsable without current rank.

Clocks remain separate:
- rootasof: caller/build-date label;
- built: UTC generation;
- target_stage_week: actual completed classification week;
- data_session: latest tape among current rows;
- per-row stage_week_end / stage_source_asof and population receipt.

See [stage engine](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/stage_analysis.py), [classifier](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/weinstein_stage.py), [template visible context](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/stage_analysis.html.j2). Preserve the visible classification-week/source-tape pair even when reducing header copy.

### Navigation, state and partial feature truth

Initial hashes support six top-level tabs only: screener,board,industries,earnings,altdata,research. Invalid hash falls backscreener. Tabs use replaceState; no hashchange listener or page-specific query parser. Filters, sort, cadence and subviews are memory state. Any future shared-link persistence is a separately approved extension.

US is the sole enabled region button. Four other regions remain disabled with coverage explanation. Research/Alt-data disable all region controls because they are combined indices. The engine's ability to append non-US seed rows does not establish a live regional workflow.

Watchlist is browser-local sga_watch ticker array. Preserve it; do not silently merge it into Terminal account storage. D23 owns any future explicit migration/import. Ordinary navigation, filter or region changes must not write it.

Expanded row is a labeled idealized stage sketch; it does not fetch historical candles. Earnings reader uses existing highlights,quote,tags from ERN.table; it does not retrieve full transcript text. Current company link is https://app.mastermind-x.com/analysis?symbol=<ticker>&page=intelligence; D07 owns whether that query is accepted, and the proposed chart return must preserve exact listing rather than assume ticker suffices.

Research expansion shows a snippet, not a longer report. Screener display cap600rows and research cap240cards need visible narrowing guidance; counts/exports must not silently imply a full display.

### Required corrections, not implemented

- CSV omits source/currentness/clocks and exports rawATR fraction under generic“Volatility.” Include explicit unit/provenance columns through the existing export owner.
- Overall-rating tooltip claims earnings tone contribution, while earnings producer explicitly excludesLLM output fromsga_score. Reconcile with model owner; do not adjust ranking formula to match copy.
- Lazy-load failures can mark a surface loaded without retry reset. Provide explicit retry that re-enters the existing reader state.
- Publisher revokes destination when source absent, but unreadable/invalidJSON may skip copying and leave yesterday's public file without newly declared stale state. Specify stale/revoke behavior with publication owner.
- Preserve heterogeneous per-surface schemas; do not restore the universal-schema regression that stopped five valid outputs.
- Keep source-aware null,zero,current/stale and seeded distinctions in every filter,heatmap,CSV and summary.

On narrow content widths, preserve dense comparison through a contained table with sticky identity where useful, an accessible column/value path and visible horizontal-scroll affordance. Expanded details reflow below the chosen row. Reader drawer traps focus only when modal and returns to the triggering call row. All six tabs and every secondary view remain reachable without hidden horizontal global navigation.

## S&P Vector

### Product and producer

This is a US allocation strategy page, not a generic chart utility. Retain the current mechanical allocation, risk components, historical strategy comparison and advisory overlay as distinct objects.

[scripts/build_spvector.py](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_spvector.py) calls engine.inputs.build_features/conditions_frame, equity_alloc.risk_score/risk_legs/vector_alloc/summarize/after_tax, dislocation.master_switch_frame and validation.backtest_core. It uses build_vector plot helpers, writes site/spvector.html through write_page and data/regime/spvector_latest.json for the hub.

Price source is yahoo/SPY.close. The store's close convention is total-return adjusted; close_price is distinct. Cash yield tries FRED DTB3→DGS3MO→DFF in annualized percent. Do not present the total-return strategy price as an executable quote. [Inputs](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/inputs.py), [allocation engine](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/equity_alloc.py).

### Mechanical, historical and advisory contracts

| Object | Existing semantics | Required presentation |
| --- | --- | --- |
| Risk score | Renormalized0–100 weighted mean of available drawdown,recession,NFCI,HYwidening,liquidity; publication lags10/22/5/3/0tradingdays | Missing legs omitted from numerator/denominator; all missing not automatically “zero risk.” Show component source times and availability |
| Mechanical allocation | Bands25/50/75 map100/66/33/0%equity after5-day confirmation; separate redeployment gate/minimumhold | Instantaneous band and effective allocation can differ. Explain the actual deciding state; do not silently change rules |
| Backtest timing/cost | Allocation acts next bar;3bps one-way per unit turnover | Decision-date chart marker is not same-day executed holding. Keep fill/cost assumptions next to results |
| Cash carry | Annualized yield over elapsed calendar days including weekends | Cash performance is not zero by default; zero yield and unavailable yield differ |
| Metrics | CAGR/maxdrawdown/timeinvested percent; carry contribution percentagepoints; turnover multiples/year | Preserve units,window,benchmark and missing values; no profit certainty |
| Bootstrap |5000resamples in21-session blocks | Method description, not evidence this review validated statistical significance |
| After-tax view |35%scenario before final liquidation | Clearly scenario-specific; no personal tax claim or strategy gate |
| LLM overlay | Builder describes shadow/log-only and writes forward log | Keep separate from mechanical hero; do not grant veto/sizing authority via UI label |

[Backtest core](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/validation.py), [scorecard and allocation](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/equity_alloc.py), [producer overlay](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_spvector.py).

### Charts, ranges and clocks

Keep three synchronized strategy panels,allocation shading/change markers,1Y/5Y/10Y/All controls (5Ydefault) and y-range rescale,growth-of-$1log comparison and drawdown comparison. Plotly modebar is disabled; charts responsive. Older samples are thinned/rounded while change markers retain decision dates. Do not claim each plotted point is an unsampled execution record.

as_of is SPY last session; built is generation. Headline risk aligns/forward-fills to SPY, while leg breakdown can use its own latestscore date. Present these roles independently; one global stamp doesn't prove simultaneous inputs. No page-specific query/hash state exists.

### Required corrections and unresolved quantitative authority

The template says “veto active” and “Live recommendation” although the builder treats overlay as shadow/log-only and hero uses mechanicalequity_w. Change the proposed presentation to match effective source authority unless the actual owner supplies accepted activation evidence.

Unknownscores become0insideglide_path, allocation alignment can fill100%, and missing capitulation/Fed-put outputs can display0/present. These mechanics are observed source behavior; the quant owner must distinguish intentional policy from unavailable data before any change. D06 must not visually convert this ambiguity into confidence.

Static copy asserts verifiededge,permutation significance andALFRED robustness. Supporting evaluation artifacts were not inspected or revalidated here. Retain methodology reachability and mark those claims for D12/market-source/quant evidence validation before design acceptance. This assignment does not certify them.

## Shared builder and owner boundary

All three templates retain shared imports from the existing Macro shell/generator and lib.pages publication path. F01/F02 supply shell slots/tokens after release verification; F03 owns registry/export correction, including the resolved S&P builder. D12 owns strategy/model archetype and quantitative authority for S&P. Existing Stage,earnings,market-structure and data owners retain their formulas and publication contracts.

Implementing these requirements is a later commission after reference review. Migration tests in [BUILD_AND_TEST_PLAN.md](BUILD_AND_TEST_PLAN.md) specify missing/corrupt/stale/null/zero/clock/region/history cases. Rollback must restore prior template/adapter behavior without deleting history, changing model ledgers or overwriting saved local state.

