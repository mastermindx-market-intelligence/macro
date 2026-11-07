# Global Prophet upgrade — Run 2: measurement autopsy and model research

Date: 2026-09-16. Principal: Sol. Operation: `prophet-global-r2-autopsy-20260916-sol-001`.

## Scope, authority and truthful status

Chairman commissioned an end-to-end US / China / Hong Kong / Canada Prophet upgrade, explicitly divided into research and build turns. This is the second research chunk, not completion of that programme. User outcome: a daily, proactive, risk-aware opportunity product that finds strong candidates and exceptional runners without manufacturing BUY recommendations when expected utility is poor. Machine outcome: discover broadly, distinguish selection from entry/exit and market exposure, estimate conditional outcomes, and learn prospectively.

This dossier coordinates existing owners; it creates no new workstream, rank authority, identity spine, grader, event store, scheduler or control plane. US implementation remains under `WS:PROPHET-US-V4-RECOVERY` and `WS:PROPHET-CONDITIONAL-FUSION`; China ranking/evidence under `WS:CHINA-ALPHA-INTELLIGENCE` and its canonical ranker; HK/Canada under `WS:PROPHET-HK-CA-REVAMP`. Executive OS retains lifecycle/admission authority. GitHub owns source/evidence, Agent OS continuity, Linear projection, Slack transport.

**Status: executed research and reproduced characterization findings. New global selector: SPEC_ONLY. No production code, weights, admission, sizing, exits, model promotion, or deployment changed.** No Fable/subagent job was submitted. No paired W3 outcome comparison was opened. This research does not repeal existing preregistration, earned-authority, source-rights or promotion gates.

Procedure was atomically read at protected `Mastermind@8ba7deedde164c90298d3e88785d98e02fa5e2d2` (Skillpack 1.0.1/bootstrap 1 compatible); that ref was rechecked before publication. Analysis source is immutable `macro@c37c4e37b20ada935f32516a2a31428d558430c3`. Publication branch starts from fresh main `3deb4eb40636f8a3c9adcddfb78445bc52bdbf5f`; this does not change the analysis vintage.

## Method and limits

Downloaded 31 selected source/artifact files at the analysis SHA into an isolated research directory on the verified Mac, with byte counts, SHA-256 and Git-blob hashes. No production checkout, another worker's worktree, scheduled run, or source data was altered. Local evidence home: `/Volumes/Mastermind/Mastermind/research/prophet-global-20260916-run2-c37c4e37/`.

Full JSON ledgers were parsed, not sampled; each reports `meta.truncated=0`. Descriptive statistics use their published rounded row values, not recomputed full-precision prices. They are not cost-adjusted returns, a portfolio backtest, or new proof of alpha. US/CN are episode-grain; HK/CA are board-day-grain. Repeated names and overlapping holding periods are not independent observations. Source-artifact verification is not an authenticated production-browser check.

Retained executable investigations: `mechanism_probe.py` and `rank_clock_probe.py`, with source-hash verification and JSON results. The first executed 16 checks: 13 desired conditions satisfied and three documented contract failures reproduced. Exit 0 means characterization completed, not bugs repaired. The second executed the exact US ledger emitter with real `track_scoring`/`build_shell`, synthetic prices, and controlled era/oscillator/continuity helpers; it reproduced rank-time contamination. No product acceptance is inferred from either.

## 1. The headline is not the current US model's win rate

`site/factordata/us_track_ledger.json` is as-of 2026-09-14, priced through 2026-09-15. Its headline is 874 matured episodes / 31 origin dates, 50.1% wins, +0.01% mean P&L, profit factor 1.01. But its rows contain FIVE board definitions. The oscillator-anchor era fence is not a board-model fence.

| Admission definition | Matured episodes | Origin dates | Positive published P&L | Mean published P&L |
|---|---:|---:|---:|---:|
| us_prophet_v3 | 240 | 10 | 34.58% | -2.0958% |
| us_prophet_v2 | 112 | 3 | 32.14% | -2.8848% |
| us_prophet_v1 | 68 | 1 | 57.35% | +1.7779% |
| confluence | 280 | 9 | 63.57% | +2.3739% |
| bottoming-alignment | 174 | 8 | 57.47% | +0.3029% |

V3 covers origin dates August 17–28 and 200 unique tickers. It has 83 positive-P&L episodes, mean excess versus SPY -1.8334%, positive excess 33.75%, median P&L -2.0%, descriptive profit factor 0.403. Every one of its ten origin-date groups has negative mean published SPY excess. This is an alarming descriptive cohort, but ten clustered dates do not identify which rule caused the loss, establish a stable win probability, or justify reverting to an older model evaluated in another market period. SPY excess is not sector/factor-adjusted alpha.

V3 exit anatomy: 179 horizon verdicts (mean P&L -2.4888%); 46 oscillator-target exits (+2.5152%); 15 stop exits (-11.5467%). These are OUTCOME-CONDITIONED groups, not admissible predictors or causal policy comparisons. The published status `stopped` means a losing outcome (157 V3 rows), not 157 stop-order executions. The 90-session-trough stop and ten-session verdict are grader conventions, not proof of the user's executable trade experience. Stops and price-adjustment/corporate-action handling need a separate path audit before tuning.

### 1.1 Do not calculate historical Top-K accuracy from popup `rk`

`scripts/grade_us_board.py::emit_ledger` assigns sector, rank and tier from `meta_by_tk`, overwritten by the ticker's LATEST board appearance. Only `board_definition` is bound to the admission date. Exact-source probe: append a later board where TEST moves rank 1 -> 99 and InitialSector -> LaterSector. The earlier episode retains its original date, entry, P&L and definition, but its emitted rank becomes 99 and sector becomes LaterSector.

Therefore popup `rk` and `sec` are display metadata, NOT point-in-time research features. The exploratory sector breakdown is retained locally but may not support a sector-weight change. Historical Top-1/3/5/10, sector attribution and gate analysis must join the existing frozen board snapshots at the decision cut. Do not create another board-history store or rewrite old episodes to repair this distinction.

Source: `scripts/grade_us_board.py:2625-2652,2720-2785`; blob `68ef9eb7620f0592e3cd02d66a3eae2ab0998dce`. Ledger blob `8936a655604eb2855b6a32d9820b8ca0b1eda095`.

## 2. China: intended version and actually executed ordering differ

Latest China board at the analysis pin is September 15, `cn_prophet_v4`, with 16 buy and 25 watch rows. Its own ordering receipt says:

- requested: `intel_interest_then_v3_score`;
- effective: `cn_prophet_v3_score`;
- mode: `v3_coverage_fallback`;
- `intel_order_active=false`;
- ranked input population 1,616; measured 1,612; unavailable four, all `no_edge_evidence`.

All 16 buy and 25 watch rows have measured interest, yet the broader ranked population's missing evidence disables intelligence ordering for the entire bake. This follows the existing coverage-atomic policy, not an accidental mixed-scale sort. Do not remove the gate, drop unknown names, fabricate zeros, or present v4's name as evidence the v4 ordering ran. First investigate the four absent inputs and measure the frequency and population of these fallbacks prospectively. Any alternative calibrated missing-data policy requires separate evidence and owner approval.

The China v4 ledger is September 14: 159 matured episodes over 11 origin dates, 143 distinct names, 44.03% positive ten-session CSI300 excess, mean -0.5971%, median -0.98%. These are definition-era results, not an attribution of loss to active intelligence ordering; episode-level effective-order provenance must be recovered before that inference.

### 2.1 A concrete anti-leadership prior exists, but its performance effect is unproven

`engine/china_intel_interest.py::_edge_remaining` rewards greater distance below a trailing high, and discounts positive 20-day relative strength as edge already spent. Rolling-over and overhang guards exist and must not be erased.

Exact-source controlled probe fixes altdata evidence, 20-day return at 8%, and other trajectory inputs. Moving off-high from -2% to -20% increases interest from 50.83 to 78.20. Holding off-high at -10%, moving relative strength from 0% to +20% reduces score from 63.89 to 39.88. A rolling-over control reduces it to 38.88; absent evidence remains null.

This proves the heuristic, not that its sign should be flipped. Proposed test: separate continuation/leadership from recovery/washout experts, then measure conditional contribution using historical effective-mode stamps and prospective shadow comparisons. The live September 15 fallback means this probe cannot explain that day's rank order.

The so-called leading gap currently has `lag_up=0` structurally: it is positive leading-desk count, not a measured consensus-recognition gap. Preserve the four-model China distinction rather than relabeling an evidence count as recognition intelligence.

Sources: `engine/china_intel_interest.py:161-246,284-338`, blob `cb7e1895c75a560b09f8207de8aa58bc4389bafe`; China board blob `0edba42f31af0539bed991f1b2c46e96ace7e5f4`; ledger blob `40ee54f0f4f464bb9c69aa24a516011e958c80b0`.

## 3. Canada: correct the earlier diagnosis

The first chat pass suggested zero matured outcomes meant a malfunction. That conclusion was premature and is withdrawn.

Current Canada ledger: September 15, 251 displayed board-day rows, zero H21 grades. Raw current-definition parquet: 267 rows, first August 19, last September 15; 192 non-null H5 MFE values, 135 H10, zero H21. Grading IS maturing at shorter horizons.

The existing grader enters at the next session's CLOSE and waits 21 additional sessions. An August 19 signal fills August 20; there are only 17 subsequent TSX sessions through September 15 after excluding Labour Day, September 7. The first calendar-complete H21 mark is September 21, assuming complete prices and the natural pipeline. This is a calendar expectation, not a delivery promise. Exact `grading.forward_metrics` on synthetic calendar-complete prices reproduced null H21 on September 15 and non-null H21 on September 21.

### 3.1 A separate real semantic defect: right-censoring is labeled suspension

`board_ledger._is_suspended` returns true whenever fewer than five bars exist after fill. A healthy just-entered name therefore becomes `suspended` simply because time has not passed. Exact AST-function probe reproduces this with an uninterrupted recent price series; the older-series control returns false.

All 59 Canada and 81 HK suspension flags in the inspected popup artifacts occur in recent origin-date groups. These counts must not be presented as confirmed trading halts. They can conflate legitimate immaturity with missing prices/halts. A repair must distinguish awaiting fill, awaiting horizon, stale/missing data, confirmed suspension and delisting; it must preserve exclusions and historical evidence rather than simply deleting the check or forward-filling prices.

Sources: `engine/board_ledger.py:749-758,764-915`, blob `004dc416819f2bc2b6887b2c3d7534410fd6fcb4`; `engine/grading.py:166-245`, blob `1208a7aa597159969a0ed7ccd359972bc413941a`; [TMX official 2026 calendar](https://www.tsx.com/en/trading/calendars-and-trading-hours/calendar).

## 4. Regime context exists, but conditional decision authority and PIT history are incomplete

US C1 is an unfitted equal-family percentile vote, not a learned return forecast. The inspected live board has F1 technical, F2 momentum/extension, F4 catalyst and F5 flow families active. F6 macro is explicitly excluded as night-constant and reserved for routing/interactions. A nonconstant synthetic C1 pool scores identically after adding standalone macro/sector labels. This demonstrates the extractor boundary only; other upstream computations can still carry market context.

HK already has a hand-set `risk_state` master switch in `hk_stock_signals.hk_edge`. Canada already passes local liquidity into analysis and computes a dispersion sizing multiplier. Thus 'no regime awareness anywhere' is inaccurate. The missing capability is reliable, validated context-dependent stock selection and risk permission, not merely another regime label.

Both current HK and Canada raw board ledgers have zero populated `own_market_regime` values (421 and 267 current-era rows respectively). The code deliberately leaves them null because the existing local regime history is recomputed rather than a lawful point-in-time append history. Never join today's rewritten regime history into an old decision as contemporaneous belief.

HK's board still imports shared US priority weights and entry-ladder arithmetic. Its own disclosure says the US entry-ladder remeasurement was not equivalently performed on HK episodes. Shared implementation is useful; shared coefficients are not evidence of successful market transfer. Current HK popup result: 95 matured BOARD-DAY observations, only 33 names and nine origin dates, 44.21% benchmark beats and mean published 21-session excess -1.5892%. The latest board has one buy row; that establishes width, not missed-winner recall.

## 5. Two reproducible earnings-extraction edge cases

US C1 and the US historical row-feature writer share `bool(sue_z and (sue_fresh_days or 999) <= 60)`. Despite the documented fresh-POSITIVE semantics, negative nonzero SUE at age one returns true, and positive SUE at age zero returns false. Positive age one, age 61, and absent controls behave as expected.

These are reproduced boundary-contract failures, NOT an explanation of the recent losses. The inspected current 50-row buy board has seven SUE readings, all positive and older than zero days; neither bad case was observed there. Trace upstream reachability and historical frequency before claiming live impact. Any fix must update serving and research extraction together under the current owner; no silent restatement of historical evidence or automatic alpha claim.

## 6. Measurement contract for the next experiments

Keep five questions separate:

1. Discovery: which investable opportunities never reached a nomination lane?
2. Ranking: among the SAME decision-time candidate pool, which names deserved attention first?
3. Entry: was an executable entry available before the move, under local market rules?
4. Management: how much of the available path did the actual exit policy retain?
5. Risk permission: was buying any of these names worthwhile after costs and portfolio risk?

The prior response's 'negative runner capture' wording is corrected: `track_scoring.capture` is realized return divided by positive maximum favorable excursion, aggregated as a median. It can be negative and is NOT the share of all market runners discovered. True runner recall has not been measured in this run.

No single statistic should mix US managed ten-session P&L, China ten-session benchmark excess, and HK/Canada fixed 21-session board-day excess. Reuse owner-native graders, with a comparison projection carrying market, definition, effective mode, decision/available/observed time, episode identity, original rank and sector, fill convention, horizon, costs, and uncertainty. Retain each native historical record; do not force a retroactive common grader over it.

For research, report absolute net payoff, broad-market excess, sector-relative excess, tail loss, precision at K, opportunity coverage/runner recall, executable lead time, and abstention together. Sector-relative performance diagnoses name selection; it must not erase profitable sector allocation by definition. Fixed candidate sets test ranking; separate whole-funnel experiments test discovery/admission. Do not improve measured precision by silently deleting hard or unavailable cases.

## 7. Primary-source research and the resulting model shortlist

These are research implications, not transferred performance claims:

- [Gu, Kelly and Xiu, Empirical Asset Pricing via Machine Learning, 2020](https://www.aqr.com/insights/research/journal-article/empirical-asset-pricing-via-machine-learning): nonlinear predictor interactions helped historical risk-premium prediction. This motivates testing interactions; it does not prove a complex daily Prophet model wins.
- [Moskowitz and Grinblatt, Do Industries Explain Momentum?, 1999](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146): industry momentum accounts for substantial individual-stock momentum in their sample. Preserve sector selection and within-sector residual selection as distinct contributions.
- [Daniel and Moskowitz, Momentum Crashes, 2014/2016](https://www.nber.org/papers/w20439): momentum portfolio crashes cluster in particular decline/high-volatility/rebound states. This is not a universal 'risk-off means buy losers' rule and is not automatically a long-only-stock result.
- [DeMiguel, Martin-Utrera and Uppal, A Multifactor Perspective on Volatility-Managed Portfolios, 2024](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13395): contrasts estimation/cost problems in simple volatility timing with a tested conditional multifactor construction. Costs and genuine out-of-sample implementation must be part of the decision policy, not an afterthought.
- [Harvey, Liu and Zhu, ...and the Cross-Section of Expected Returns, 2014/2016](https://www.nber.org/papers/w20592): multiple testing undermines naive significance thresholds. Register the experiment family and nested time splits before looking for a winning variant.
- [Liu, Stambaugh and Yuan, Size and Value in China, 2018/2019](https://www.nber.org/papers/w24458): historical Chinese factor construction differed materially from simply importing US recipes. This supports native controls, not blindly imposing that paper's old small-stock exclusion in 2026.
- [Zaffran et al., Adaptive Conformal Predictions for Time Series, ICML 2022](https://proceedings.mlr.press/v162/zaffran22a.html): dependence/distribution shift complicate uncertainty calibration. Adaptive intervals are a research candidate, not a guarantee of per-stock conditional coverage or profitability.
- [LightGBM official parameter documentation](https://lightgbm.readthedocs.io/en/stable/Parameters.html): ranking, binary and quantile objectives exist, but ranking relevance is not an expected-return probability. Date-grouped rank training must be compared with calibrated payoff/risk models, not accepted because NDCG improves.

### Preferred research sequence, not a premature architecture freeze

A. Preserve the exact incumbent plus simple market/sector/price baselines. Fix verifiable feature-contract defects separately so model gains are not credited for software repairs.

B. Fit regularized market-native payoff/probability models with a SMALL declared set of context interactions and partial pooling. Estimate absolute and benchmark/sector-relative outcomes separately. Missing evidence is typed uncertainty, not bullishness or a zero vote.

C. Race a constrained boosted-tree ranker and regression/quantile alternatives on identical decision-date groups and executable policies. A ranking model needs separately calibrated downside and abstention; rank score is not confidence.

D. Add a soft mixture of continuation, pullback, recovery/washout and event-driven experts ONLY if it beats the strongest simpler surviving approach on untouched periods. Router uncertainty and sparse regime/sector cells should shrink influence toward a robust baseline rather than creating many tiny overfit specialists. Do not make a separate model for every stock or reuse historical outcomes to choose a name's preferred expert.

E. Multi-head selection / upside-tail / downside-path / entry / confidence becomes the intended product interface, with implementation complexity earned by evidence. Existing canonical owners supply identity, events, evidence, risk and evaluation; no global mega-score or LLM-written BUY permission.

No new model was fit this run. Ten US V3 dates are an autopsy sample, not a training corpus. Deep existing point-in-time price/event history can support earlier bounded tests; snapshot-only intelligence must accrue prospectively. This avoids both premature promotion and waiting idly for every rich data family.

## 8. Next bounded capability and continuation

**R3: recover admission-time ranks, sectors, expert nominations and rejection reasons from the existing frozen US board/candidate episode owners; then construct a point-in-time full-funnel loss/missed-runner reference panel.** First reconcile publication-vintage gaps and effective-mode fields. No Top-K or sector-adjusted promotion claim before these joins are valid. Do not use popup `rk`/`sec` as historical features. Respect W3's existing maturity/read gates and do not read its paired outcomes merely to fill this report.

In parallel, owner-routed bounded repairs may address SUE extraction, censoring labels and China missing-input fallback once producer reachability and source collisions are reconciled. US collector/availability repairs already have their own carrier (#7180/#7187/#7200); adopt their accepted evidence, do not take over their files or dispatch another nightly. Current #7200 PR status/evidence is separate from this research and not treated as production acceptance.

Production end-state remains owed: real inputs through market-native discovery, risk-conditioned selection, executable entry, coherent UI/alerts, calibrated outcomes and forward learning. The final architecture, implementation packets, separate country promotion rulings and browser proof are still future dependencies. This research narrows the next action; it does not finish the parent programme.
