# Sector & Theme Factor Intelligence — research, source gates and product experience

Date: 2026-10-30. Companion to `research/sector_theme_factor_intelligence/MASTERPLAN.md`.
Status: **research specification / source census**, not a validated alpha model or Paper canvas acceptance.
Exact Macro source census `6f60f9c75328996fbd43e4472d8890283de165fc`; protected Mastermind `bb85b429f2ffffd38408080ce4df7d6378c34100` / skillpack 1.0.1.
The P1 projection is isolated in draft PR #10213. Every factor below is a *candidate* until owner inputs, lawful use and the empirical acceptance gates are qualified.

## Critical new source finding: subtheme proxy is not constituent membership

At the pinned source, `engine/theme_graph/hierarchy_breadth_display.py` provides taxonomy adjacency `macro_category -> theme -> sub_theme -> micro_theme` with an allowed direct `theme -> micro_theme`. It counts direct children and descendant nodes, **not** stocks and not price breadth.

`engine/theme_graph/micro_rs_proxy_display.py` explicitly states that `sub_theme` and `micro_theme` have **no EXPRESSES/MEMBER_OF edges by law**; their current RS representation is an **ancestor-theme ETF/basket proxy**, with `proxy_not_micro_membership` labeling, and with no weights/RS numbers/scores/ranks provided by that reader. NEVER relabel ancestor breadth as micro-theme breadth. Do not invent subtheme membership by walking ancestors and copying their constituents.

`engine/theme_graph/theme_state_owner_readers.py` currently re-reads incumbent basket PIT membership, identity resolution and rights receipts, but emits no eligibility. It explicitly notes date-only membership clocks do not prove same-day known-at, and production custody is outstanding. `engine/theme_graph/activity_history_bridge.py` holds new activity-membership events without an applicable Chairman source-purpose grant. `engine/theme_graph/rights_use.py` has per-purpose, per-phase use verdicts. These are substantive data/rights gates, not mere page wiring.

**Required choice for P2/P5**: (A) display existing subtheme as explicit ancestor proxy with no ticker/member breadth, or (B) obtain GMI's reviewed ontology/data-source/rights/identity/clock specification and a qualified *real* subtheme-member producer, then display true measured breadth. Tier B is an existing-owner programme change, never a shortcut in the new factor projection. Prototype both available and proxy/held states; acceptance must fail if proxy values appear as measured micro-theme facts.

## Factor laboratory: measurement families, not an unvalidated mega-score

Every feature is a `factor_definition_id` tied to horizon, exact source endpoint, membership vintage, lookback, group, reference population, units, null coverage, and source-use status. The baseline observed frame can support multiple separate analytical axes; it MUST NOT issue a single trade/risk score by convenience.

| Family | Candidate feature and definition | Counterexample / omission |
|---|---|---|
| Participation | `positive_return_breadth` = proportion of eligible *current known* members with R > 0; expected-N bounds in every frame | A few missing leaders cannot be counted as decliners |
| Participation | `above_ma20/50/200`, `uptrend/downtrend`, 52w new-high/new-low, advance/decline volume where licensed | Ineligible warmup cannot masquerade as below MA; zero volume is not no feed |
| RS | `relative_wealth_market` = (1+R_i)/(1+R_SPY)-1; additionally parent sector, sector peer and own historical standardized RS | Arithmetic return difference is not a wealth ratio; same endpoints mandatory |
| RS | residual-from-lagged-beta (only when sufficient independent historical sample) and equal-weight / properly lagged cap-weight group measures | beta fitted through decision date after endpoint is leakage; observed-sample mean is not full-cohort performance |
| Trend structure | 1/5/15/60m, RTH, 1/5/20/63/126/252d, 3/5y contextual observations, same maturity and basis | RTH return is not overnight+RTH synthetic without aligned basis and volume, exchange calendars and corporate actions |
| Acceleration | standardized changes of *matched* trailing RS slopes over nonoverlapping or dependence-declared intervals | Recomputing z with changing peer universe creates spurious acceleration |
| Breadth change | `breadth_change` on common-known members, separate entrants/exits/coverage and true crossings | Unknown-to-positive is not a new cross; endpoint flips are not the full within-window event list |
| Dispersion | median vs EW vs cap-weighted, upper/lower decile of member returns, top-k contribution, HHI/effective leader count | One mega-cap carrying the index is not broad participation; overlapping issuer cannot be double-counted as independent evidence |
| Group divergence | price strength + negative breadth slope, leader–laggard decoupling, market vs parent divergences | New group constituents added during a rally can superficially improve breadth |
| Stage/extension | own-historical price/RS stretch vs moving average, trailing run age, max adverse excursion, conditional run survival | An 80th percentile stretch is not '20% more room'; active runs are right-censored |
| Inverse & cross-asset | historically observed relationship between risk-on and defensive/hedge proxies; rolling signed beta/correlation, conditional lower-tail co-movement | TLT/gold/XLU cannot be hardwired negative-beta to equities; inflation regimes change stock/bond correlation |
| Credit & liquidity | HY OAS, IG spread, term slope, excess bond premium where qualified; level/change/accel vs previously published vintage | FRED/ICE OAS daily close cannot become 10:30 AM fresh credit tick; FRED 3-year displayed limit is not a multi-decade authorized license |

Every numeric window is a candidate registered *before* inspecting an evaluation set. Covariates that add no incremental value stay descriptive, not promoted. Avoid double counting momentum across nearby horizons, or treating stochastic RSI and ROC transforms of the same return path as independent evidence.

## Multi-factor interpretation grid (descriptive, not probability)

| Group RS vs parent | Same-member breadth derivative | Credited defensive/credit context | Interpretation |
|---|---|---|---|
| Positive / improving | Broadening | Credit stable, defensives not gaining | Broad observed leadership |
| Positive / improving | Narrowing | Credit widening or defensive RS improving | **Participation divergence**, watch for confirmation; not a predicted top |
| Negative / still weak | Broadening | Credit stabilizing | **Repair/rotation candidate**, distinguish loser rebound from durable leadership |
| Negative / deteriorating | Narrowing | Credit widening | Broad observed deterioration; do not claim exact crash timing |
| Any | Missing | Any or missing | Unmeasured/partial; no rank promotion or confident interpretation |

A theme can be measured as an RS leader while its existing entry/valuation/crowding gate remains HOLD. The factor laboratory never overrides entry authority.

## Historical 'room to run' — falsifiable design

First freeze a **run definition**: start only after a predeclared multi-horizon RS and breadth transition; end at a predeclared relative trend break or drawdown threshold; record source availability. Analysis must separate:

1. *Continuation odds* by next 1/5/20/63 sessions;
2. expected *max favorable excursion* and *max adverse excursion* after the signal;
3. distribution of *remaining* run lifetime conditioned on run age, recent range/extension, volatility regime, concentration and credit background;
4. survival estimator accounting for **right censoring** of currently open runs;
5. baselines: unconditional same-sector run, momentum-only, volatility-adjusted momentum, breadth-only and historical run-age-only.

The full historical run may be reconstructed **as a research outcome** once closed, but the live signal at its start may use only knowledge actually available then. Distinguish CURRENT_ROSTER descriptive backfill from strict PIT_AS_KNOWN forward-valid studies. Require matched observation vintages (identity, price/corporate action, source rights, membership clock) and retain the unobserved-right-hand tails.

Output wording: 'In qualified comparable historical runs (n=...), X% were still above the predefined threshold after 20 sessions; coverage Y%; uncertainty Z; input as-of ...'. No 'room to run: +17.4%' fiction from distance to high.

## Credit / inverse source contract

- `BAMLH0A0HYM2` is ICE BofA US HY OAS via FRED/ALFRED, **daily close**, units percent; published series only shows 3 years of observations starting April 2026 and reflects ICE proprietary underlying data. A three-year UI series is not a licensed 15-year backtest corpus. Source rights, vintage and redistribution must be reviewed.
- ALFRED vintage support does not magically make a previously mutable/Yahoo data series point-in-time lawful or first-seen historically. It is source-specific and requires the exact original observation availability/release rules.
- The Fed Gilchrist-Zakrajšek excess bond premium is conceptually distinct from a simple HY OAS series: it attempts to isolate non-default credit compensation. Do not label HY OAS as 'excess bond premium'.
- Before labeling any asset 'inverse', require signed relationship and tail co-movement tests on predeclared rolling lookbacks (e.g. 63/126 sessions) with a **minimum sample**, multiple regime checks, confidence interval/bootstrapping, corporate-action basis, and a `relationship_unstable` status when its sign is not persistent.
- Intraday proxy layer may report observed HYG/LQD/IEF/TLT/GLD/XLU/XLP returns if rights/clock qualified; it must be labeled 'market proxy' and cannot assert same-minute ICE bond OAS change.

## Scientific preregistration before model promotion

**Universe:** 11 US GICS sectors + valid same-vintage, rights-approved themes; subthemes only when genuine admitted member evidence exists. Fixed selection dates and issuer/cross-group overlap metadata; no minimum-size filler names. If source data fails qualification, report missing strata rather than weakening the gate.

**Frozen outcomes:** forward risk-adjusted sector-vs-parent returns and adverse excursion at 1, 5, 20, 63 sessions, plus rank migration, false deterioration/recovery alerts and drawdown-specific impact; probability models separate from descriptive strength.

**Hypotheses to register in fresh versioned manifests (not results):**
- H1 narrowing same-member breadth adds *incremental* lead time for market/sector deterioration over price-only trend;
- H2 RS-level + RS-acceleration improves stability of leader/laggard transition classification over RS level alone;
- H3 breadth × credit spread widening interaction improves near-term drawdown risk classification beyond either factor alone;
- H4 defensive group RS repair conditional on credit and realized volatility distinguishes defensive rotation from transient bounce;
- H5 own-historical run survival is better calibrated than 'days since breakout' or own percentile stretch;
- H6 laggards' squeeze/market rebound state protects against momentum-crash overconfidence, relative to current scoring;
- H7 overnight/RTH conflict and opening-gap transitions contribute **only if** timestamped rights-cleared extended-hours data are available and holding/trading costs do not erase usefulness.
H1–H7 are untested for this implementation; their statistical results cannot be inferred from published papers or original rotation preregs.

**Testing gates:** chronological walk-forward, nonoverlapping embargo/purged labels and overlapping-group clustered uncertainty; vintage audit, rights, survival/identity bias, data revisions, sector composition drift, calendar leakage, and corporate actions; compare naïve sector momentum, SPY trend, current theme scoring and breadth-only baselines; winsorization/volatility targeting pre-registered; multiple hypothesis control, leave-one-regime/sector/issuer out, ablation by factor family, turnover/costs/bid-ask/latency. Use crisis and low-volatility regimes, pre-2020 vs recent when valid point-in-time data exist, and untouched prospective shadow observations. Reject a factor if improvements vanish after dependence, data rights or cost controls. Independent non-author scientist review required.

### Evidentiary literature (supports hypotheses, not Mastermind alpha)
- Moskowitz & Grinblatt (1999), *Do Industries Explain Momentum?*, J Finance, https://doi.org/10.1111/0022-1082.00146 — industry return components capture a substantial part of stock-level momentum.
- Daniel & Moskowitz (2016), *Momentum Crashes*, J Financial Economics, https://doi.org/10.1016/j.jfineco.2015.12.002 — momentum losers can rebound violently following high-volatility market drawdowns; a one-sided leader score is fragile.
- Barroso & Santa-Clara (2015), *Momentum Has Its Moments*, JFE, https://doi.org/10.1016/j.jfineco.2014.11.010 — momentum risk varies over time; published in-sample research is not a guarantee for new theme cohorts.
- Gilchrist & Zakrajšek (2012), *Credit Spreads and Business Cycle Fluctuations*, AER, https://doi.org/10.1257/aer.102.4.1692 — distinction between spread and excess bond premium.
- Molenaar et al. (2024), *Empirical Evidence on the Stock–Bond Correlation*, Financial Analysts Journal, https://doi.org/10.1080/0015198X.2024.2317333 — stock–bond correlation can abruptly change with inflation/rates.
- *What Does Equity Sector Orderflow Tell Us About the Economy?*, Review of Financial Studies, https://academic.oup.com/rfs/article/24/11/3688/1589538 — carefully measured sector rebalancing/flows may contain information beyond prices; NOT a license to infer institutions from options prints.
- FRED series official documentation: https://fred.stlouisfed.org/series/BAMLH0A0HYM2 and ALFRED vintage: https://alfred.stlouisfed.org/series?seid=BAMLH0A0HYM2.
- Gao/Li/Yuan/Zhou (2026) *Anatomy of Industry Momentum*, SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6371558 — **recent preprint, not independently established**; suggests stock short-horizon reversal and industry short-horizon momentum require separated controls.

## Paper product brief — NOT_APPLIED_TO_PAPER

Paper target: none selected. Current direct Mastermind Paper `paper_inspect` failed with MCP SSE **429**; no file identity or screenshot was received and no canvas mutation was attempted. Studio Direct gateway also returned 429 in this session; that is a transport observation, not a Paper Desktop outage. Do not substitute a mockup file for an accepted Paper edit or use a raw bridge bypass. Resume only with approved exact file ID, fresh guarded snapshot, original-carrier admission and a non-conflicting node/artboard target.

**Target persona:** active macro trader/researcher who wants a transparent multi-horizon market map plus an inspectable explanation, not a floating black-box 'BUY' badge.

**Desktop flagship: Sector/Theme Breadth Command**
- Header: timestamped market clock (exchange session / vendor delay), evidence-mode switch CURRENT_ROSTER vs PIT_AS_KNOWN (only when real source allowed), daily/historical replay time control and clear source/rights/coverage banner.
- Main 2D **leadership matrix**: rows sector→theme→subtheme, columns 1m/5m/15m/60m/RTH/5d/20d/63d/252d; cells show signed RS vs parent, hover reveals sample eligible/expected N, dispersion/participation and factor provenance. Unqualified subthemes appear **PROXY** or unavailable, never fabricated measured heat.
- Side **formation waterfall**: group positive breadth, >50DMA, >200DMA, growing/declining same-member states, top-k contribution vs median, EW vs cap mismatch, leadership-rotation rank migration. Keep current strength/formation/entry as separate columns.
- Bottom **cross-asset stress strip**: credit as **prior published daily vintage**; risk proxies stamped with own frequencies and observed relationships (negative/positive/unstable), not assumed hedge labels.
- Ticker drilldown: member trend state and RS vs SPY/parent by timeframe, percent change, moving-average stack, historical run stage distribution/coverage, which factor flipped and when. Multiple theme memberships visibly linked; investor can distinguish an issuer from duplicated theme appearances.
- Trend replay: timestamp scrub → repeat exact known-as-of frame; reconstructed historical context shaded/marked separately, never retroactively glued to an original alert.

**Meaningful screens/states:** full qualified source; partial member coverage (bounds); current-roster backfill only; unqualified rights/identity; micro-theme ancestor proxy; no available source; stale or late vendor; market closed/extended hours; conflicting RS-vs-breadth; credit last published yesterday; zero-result historical cohort; phone 390x844, tablet 820x1180, desktop 1440x900; light/dark; English/Chinese; keyboard/screenreader.

**Visual information hierarchy:** (1) observed market state and freshness, (2) breadth and leader/laggard internal disagreement, (3) underlying ticker evidence, (4) cross-asset context, (5) historical conditional research, (6) existing entry gate. All factor displays are descriptive before a separate validated research promotion. Avoid a giant all-green/up-all-timeframe heatmap hiding different source clocks. Interaction acceptance requires 3-click sector→theme→constituent detail, one-click compare vs parent, explicit null reasons, stable navigation and zero contradictory stale labels.

**Paper acceptance gate:** bind exact file/artboard, inspect tokens, create on authorized carrier, screenshot and review all meaningful states; then extract JSX and wire to authenticated, entitled canonical owner contracts, with production browser proof. None of those Paper actions are claimed complete here.
