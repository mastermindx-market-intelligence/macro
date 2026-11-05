# Research intake v2: evidence, counterevidence and unresolved scientific questions

**Revised:** 2026-10-04. **Classification:** research-source audit, not a new backtest, registered experiment, product master plan or strategy promotion.

The complete first intake, including the supplied Deep Research consolidation and every reported quantitative table, is preserved at [the immutable v1 research dossier][v1]. Read that dossier for historical detail; read this revision for the strengthened interpretation, newly checked internal research and specific unanswered questions. No statistic has been silently upgraded from reported to reproduced.

## 1. The actual mission and the evidence boundary

The Chairman is asking whether Prophet can identify worthwhile opportunities early enough to act, distinguish persistent trends from short-lived rotations, select the appropriate strategy and horizon for the environment, and reduce severe failures without discarding the large winners that pay for them. He explicitly asks for research beyond MACD and RSI, using the existing technical catalog, historical macro and market structure, theme/subtheme intelligence, and the connected Terminal.

The motivating theory is that narrow participation and rising real yields can shorten follow-through, so 3D confirmation may arrive after a daily impulse is largely consumed. The competing theory is that some apparent timeframe deterioration comes from indicator definitions, bar clocks, data, selection changes or confirmation lag rather than a new economic regime. Both can be partly true.

A correct takeover must separate four levels:

1. **Mechanical reproducibility:** are the same prices, sessions and indicator definitions producing the same signal?
2. **Descriptive association:** did certain signals fail more often in an observed environment?
3. **Out-of-sample decision usefulness:** does information available before the decision improve outcomes beyond a matched baseline, after costs?
4. **Production acceptance:** does the promoted, versioned behavior actually reach the user consistently and safely?

None implies the next. The source Deep Research report contained a substantial synthesis but returned no independently reproducible new cross-indicator/multi-regime test bundle. Its internal citation IDs included invalid references. Several continuation attempts were interrupted. This audit performed source reads and primary-source checking, not fresh raw-data performance experiments.

**Evidence labels:** source-verified means the exact document/code was read; reported development evidence means the supplied research states a result which was not re-run; externally checked means a primary public source was inspected; hypothesis means a proposition still requiring a lawful test. Production-proven requires its own real-path receipt.

## 2. Numerical research record that must not disappear

### 2.1 Small live-plan sample: historical, not current lifetime performance

The supplied report describes an August 12 audit: 28 closed plans, 9 positive, 32.1% positive-return rate, mean +0.51%, median -4.60%, mean winner +19.73%, mean loser -8.59%, payoff ratio approximately 2.30, mean t-statistic +0.178 and approximate 95% interval [-5.14%, +6.17%]. Its earlier 16-plan reading was 12.5% positive, mean -5.03%, median -5.51%.

Those figures are retained as **reported historical evidence**. They are not a current October track record, user execution P&L, or proof that a proposed filter improves expectancy. Exact returns, exits, adjustments, benchmark definitions, versions and uncertainty estimation still need reconstruction. An old note that the plan ledger lacked a benchmark field is a schema audit lead, not proof the current ledger still lacks it.

The report's later illustrative rows included VSEC -17.44%, UEC -10.48%, ADAM -9.17%, XPEL -9.11%, WT +11.62%, DAN +5.45% and FCX +3.65%. Do not compute an aggregate from those selected examples.

### 2.2 Phase-21 forensic population

Reported population: 209 matured V3 episodes, eight admission dates, 181 tickers. The later Phase-22 source explicitly treats this as already-inspected development evidence. Its cited synthesis digest is `37b5ac78bd93c6d8ebc9b7effb260eb00c0fb77ef8c3259ecd29c231bd124ed6`; the raw artifact was not recovered and rehashed in this audit.

| Eight-date-block relationship | Reported Spearman correlation |
|---|---:|
| Original mean outcome vs realized real-yield rise during holding | -0.595 |
| Benefit of a roughly five-session hold vs realized yield rise | +0.762 |
| Original mean outcome vs later RSP-SPY performance | +0.762 |
| Shorter-hold benefit vs later RSP-SPY performance | -0.762 |

The predictors in this table include **future realized** conditions. They are mechanism clues, not trading-time features. Eight common decision blocks do not become 209 independent macro experiments.

The same report found: near-prior-high entries (approximately within 5%) had zero major winners and six severe losers, averaging roughly -4.25%; severe losers had daily cross age around seven sessions and StochRSI K around 77; large winners had older daily cross age around 13 and K around 82. Losers' 2D cross age averaged approximately 25 sessions, median 18; winners' approximately 11, median three. Recover the exact meaning of each cross before joining it to a new study. These observations do not authorize tuning an age, off-high or oscillator threshold on the same episodes.

### 2.3 Earlier-entry replay is selected on the future

| Earlier entry on names eventually selected by Prophet | Lead | Mean-return change | Severe losses | Large winners |
|---|---:|---:|---:|---:|
| Original entry | Baseline | About -2.0% mean | 17 | 8 |
| Previous 1D cross | About 7 sessions | +0.9 pp | 26 | 19 |
| Previous 2D cross | About 30 sessions | +2.2 pp | 42 | 31 |
| Previous 3D cross | About 48 sessions | +5.2 pp | 38 | 48 |

These are reported development counts, not an implementable strategy backtest: the names were selected using information from a later Prophet admission. The correct earlier-decision population includes names that never become Prophet candidates, fail early or delist. The result neither validates universal early entry nor proves it useless.

The report also describes a historical sequence audit: 5,926/7,973 episodes, about 74%, used a branch with an already-active daily cross before the 3D leg. That is a historical semantic defect to reconcile by era and source, not a current defect established by this audit.

## 3. New contrary evidence: leadership is not the same thing as entry extension

The first handoff listed CPU-leadership research but did not carry its concrete findings into the decision discussion. The following two source documents were now read at Macro `02fb67891222f9710c2a16b1fa6feb917996cab7`. Their numbers are **source-verified historical results, not newly recomputed statistics**.

### 3.1 Relative-strength cutoffs

The [RS-threshold study][rs] uses a 1998-12-22 to 2026-09-04 US sector-SPDR proxy panel, 11 sectors and 12 hash-bound input parquet files. The percentile is a theme/sector's own rolling relative-price-history percentile, not its rank among all stocks.

| Otherwise-clean episode cohort | Episodes | Median 21d relative return | Median 21d drawdown | P(drawdown < -8%) | Continuation failure |
|---|---:|---:|---:|---:|---:|
| RS < .75 | 3,523 | +0.068% | -1.896% | 8.88% | 48.77% |
| .75 <= RS < .85 | 1,201 | +0.379% | -1.749% | 7.41% | 43.80% |
| RS >= .85 | 1,686 | +0.106% | -2.040% | 10.68% | 48.70% |

Dependence-aware inference, middle band minus <.75, over 267 paired months: relative-return difference +0.063%, Newey-West p=.735, bootstrap interval [-0.308%, +0.403%]; drawdown-risk difference +0.34 pp, interval [-1.51, +2.42] pp; failure difference -3.06 pp, interval [-7.27, +1.72] pp. The source does not establish that .75 is a validated protective cutoff, but it also does not promote .85 live.

For >=.85 minus the middle band, over 261 paired months, the reported continuation-failure difference is +6.05 pp, p=.0139, interval [+1.34, +10.45] pp. This is the source's strongest hotter-band separation; it is not proof of drawdown reduction, current AI-subtheme performance or a universal percentile law.

The motivating September snapshot had AI Semiconductors, Memory/HBM/Storage and AI Infrastructure all blocked only by the .75 veto, while their own-price extension textures differed. That supports keeping leadership and chase risk as separate measurements. It does not justify hard-coding semiconductor membership or mining these examples for a threshold.

### 3.2 The apparently sensible 1.5-ATR veto failed

The [direct-extension challenger][extension] tested the existing close-based ATR formula and 1.5 boundary inside the otherwise-clean RS<.85 population.

| Cohort | Episodes | Median 21d relative return | Median drawdown | P(drawdown < -8%) | Continuation failure |
|---|---:|---:|---:|---:|---:|
| Extension <1.5 ATR | 2,712 | +0.041% | -2.166% | 10.95% | 49.48% |
| Extension >=1.5 ATR | 3,254 | +0.067% | -1.802% | 6.85% | 48.71% |

In the preregistered paired-month analysis over 288 months, extended minus normal gave relative-return difference +0.008%, p=.951, interval [-0.229%, +0.270%]; drawdown-risk difference +0.11 pp, p=.912, interval [-1.76, +1.93] pp; failure difference -0.07 pp, p=.966, interval [-3.18, +3.03] pp. The source ruling is **NO-GO as a gate; display texture preserved**.

Do not replace the paired-month estimator with the more attractive pooled table. Do not use a post-hoc middle-band split to rescue the failed primary test. Do not combine two unvalidated vetoes because their story sounds coherent.

**Takeover implication:** Remaining Opportunity is a problem to measure, not an already validated score. Distance from a high, oscillator level, ATR extension, cross age and target progress are different proxies. None inherits authority from the name of the problem.

## 4. Regime evidence: more granular, but not automatically more predictive

### 4.1 The existing historical atlas is useful but not a real-time classifier

The [S&P/Nasdaq regime-rotation atlas][atlas] already studies 2013 through July 2026. It explicitly states that regime boundaries were chosen ex post and that rotation describes relative pricing, not observed investor dollar flows. It uses QQQ for Nasdaq-100, not the Nasdaq Composite, and adjusted ETF returns rather than cash-index price returns.

Its weekly standard price-MACD result is material contrary evidence: in the stated QQQ sample, 84% of observations were positive 26 weeks after a bearish cross and the asset rose during 29 of 31 completed bear-to-next-bull episodes. Selling each bearish cross reduced drawdown but also reduced CAGR. This concerns a binary exit/re-entry rule on that asset/window; it is neither Prophet's RSI-MACD nor proof that weekly context has no value.

The atlas is an episode library and a source of counterexamples. It cannot supply historical decision-time labels merely by assigning its retrospective labels to every date. Its observation that defensive relative performance may largely reflect lower beta is another warning: relative outperformance does not itself prove new capital inflow or a forecastable rotation.

### 4.2 Preserve the prior broad-regime null

The earlier regime-reliability adjudication reports 57,642 matured signals across 763 months for its simple regime axis. Reported magnitudes: family main effect 3.59 pp, regime main effect .95 pp, largest interaction 1.49 pp; five of 15 cell intervals exclude zero and 8/13 era-split signs agree. Richer regime variables covered only about .4% of an older 58,149-row record. An older 2,282-row board dataset spanned only 18 sessions.

This is a scoped null for a particular family-by-label/forward-drawdown construction, not a prohibition on all future conditional research. The existing `engine/regime_conditioning_coverage.py` is prior art for deciding whether a conditional question is estimable. Re-measure current coverage and independent periods; do not treat a recent large row count as many regimes.

### 4.3 Macro, market structure, theme state and instrument behavior are different axes

The broad research question needs separation of: discount-rate level/change; growth and inflation information; funding/credit conditions; market trend, volatility, dispersion and correlation; breadth/concentration; theme participation and leadership persistence; and the security's own liquidity, catalyst and path behavior. These are analytical coordinates, not a proposed new fused regime score.

A falling real yield can accompany improving financial conditions or a growth shock. Narrow breadth can coexist with a durable leader trend or an unstable rotation. A broad market can still have individual exhaustion. Therefore neither 'rates down = 3D works' nor 'breadth weak = use 1D' is an accepted rule.

The important unresolved statistical question is the **incremental interaction**: does knowing the environment change which signal/strategy is useful after accounting for baseline market, family, sector, risk and sample composition? A bad market lowering every strategy's return is not proof that timeframe selection improves.

## 5. Clock and indicator mechanics: a necessary causal separation

The source-verified incumbent cascade is **RSI-MACD**, RSI length 14 and fast/base/signal lengths 14/60/5, with StochRSI 14/3/3. Standard price MACD 12/26/9 is a distinct comparator. Its current source already declares absolute session anchoring and era `abs-session-2026-08-06`. Rebuilding that repair from the old report would waste work and risk moving the graded population.

The newly recovered [Temporal Grain programme][temporal] already owns G/A/K/D separation. Its W0 architecture PR #6790 is merged; its empirical completion is not proven. The exact-chart study and the broad TOI data-clock audit have separate responsibilities.

A timeframe change normally changes both sampling and filter memory. For an EMA with alpha `a`, half-life in bars is `ln(.5)/ln(1-a)`. To compare equal elapsed-time decay across intervals d and d0, the algebraic control is `a_new = 1 - (1-a_old)^(d/d0)`. This is a filter-equivalence diagnostic, not a claim that nested RSI-MACD outputs become equivalent: RSI is nonlinear, Wilder initialization matters, sessions are irregular and resampling changes information. Match the chosen time metric explicitly.

Three invariants must not be confused:

- shared calendar/version should preserve bar boundaries across history slices;
- shared seeds/state or sufficient declared warmup are needed for numerical indicator parity;
- equal numerical indicators do not establish profitable decisions.

Holiday-short weeks are not necessarily five-session bars. 12 clock hours are not half of a US regular session. A 4H chart may contain an unequal closing stub. No historical intraday series may be invented from daily OHLC. Future-confirmed pivots/fractals must carry their confirmation delay, not fire at the visually attractive pivot date.

## 6. Beyond MACD: what the existing method census must distinguish

The [technical catalog][catalog] already contains substantially broader families. The table below is an **audit question map**, not measured performance or a proposed ranking formula. The [existing TOI W1 contract][w1] specifies the method passports and equivalence work needed before outcomes are read.

| Family | What it measures | Research question | Important confound/failure |
|---|---|---|---|
| Moving averages, ribbons, RSI-MACD, momentum | Trend level, change or acceleration with different memory | Which adds information beyond the incumbent at equal horizon? | Correlated transforms counted as several confirmations; late confirmation |
| ADX/directional trend, Aroon/recency, efficiency | Strength, trend age, directional efficiency | Does persistence information distinguish trends from chop? | State labels built from the same future path being graded |
| Bollinger/range compression, channels, ATR expansion | Compression followed by expansion/breakout | Which releases follow through versus fake out, under qualified participation? | Intrabar highs used before known; gap fills and stop ordering |
| RSI/rank oscillators, stochastic, mean reversion | Relative location and short-run stretch | When is pullback/reset informative rather than an early falling knife? | Blanket overbought veto discarding durable winners |
| Volume participation, money flow, VWAP/profile | Trading participation and price-volume location | Does independent participation evidence add net value? | Adjusted volume, incomplete sessions, unavailable trade-level history; flow proxy mistaken for dollars moved |
| Swing/fractal/bar structure, divergence | Path sequence, breaks, failed breaks and reversals | Does a causal sequence outperform simultaneous-state counting? | Backdated pivots, retrospective pattern selection and repainting |
| Adaptive filters and ATR trends | Memory/sensitivity adjusted to observed path | Does adaptation beat a simpler fixed-memory control out of sample? | Adaptivity conceals a larger parameter search |
| Relative strength and peer/theme breadth | Cross-sectional leadership and internal participation | Is the apparent edge local/industry-driven rather than stock-specific? | Today's memberships, factor exposure, stale peers and survivorship |
| Path risk, drawdown, extension, exhaustion | Distribution and stage of adverse/favorable paths | Which predicts remaining payoff or invalidation at decision time? | Entire future move used to label 'opportunity already consumed' |
| Cycle transforms, composite oscillators, gap and sequence challengers | Alternative temporal representations | Is there robust incremental signal after simpler family controls? | Fragile dominant-period estimates, noncausality, overfit model selection |

The contract's roles are context, setup, trigger, participation and risk. A useful candidate sequence can combine different roles; adding five highly dependent oscillators is not five independent pieces of evidence. Popularity or a polished Terminal display is not validation. Killed constructions remain closed unless a genuinely different construction is admitted through existing law.

## 7. Specific unresolved questions for scientific takeover

These questions identify evidence missing from the handoff. They do not register trials, prescribe new live policy, or replace the absent product master plan.

**A. Did performance deteriorate, or did the denominator change?** Recover the incumbent served definition and compare complete, date-qualified candidate cohorts across eras. Print all probes, detected opportunities, surfaced rows, featured picks, entry-open rows, manual picks and plans separately. Attribute changes to definition, data, admission, display and exit policy before attributing them to macro. Include never-confirmed and failed opportunities.

**B. Is slow confirmation late in the economically relevant sense?** Distinguish time to signal, time to accessible entry, price progress before signal, subsequent net payoff and false-start cost. A signal arriving earlier is not automatically better. A later signal may reduce false positives enough to offset delay. Never define eligible early trades using later Prophet selection.

**C. Is there a genuine environment-by-family/timeframe interaction?** Compare matched-horizon, matched-universe baselines; distinguish main effects from interactions; preserve date/name dependence; use time-ordered validation with overlap protection; and report uncertainty and sign stability. If the enriched state has no independent contrast, report not-estimable rather than an impressive grid of cell means.

**D. Does leading-theme restriction help, and what does it miss?** Historical memberships must be known at the decision. Compare broad and leadership-qualified populations without quietly changing risk or exposure. Measure rejected future winners, emerging themes, turnover and concentration as well as losses avoided. A leaders-only rule can mechanically remove tomorrow's emerging leaders. No current-semiconductor-only test is an independent evaluation.

**E. Is opportunity remaining measurable before the outcome?** Separate cross age, extension, prior-high distance, reset freshness, independent catalyst, and theme persistence. The existing ATR gate failed. Any expected target or cycle-length estimate used as a feature needs its own out-of-sample construction; hindsight swing endpoints are labels, not inputs.

**F. Is the entry wrong, or does the hold become wrong?** Preserve entry-time context and each later decision-time context separately. Realized yield moves during a hold cannot be used at entry. Compare policy changes against the same entry population and actual exit/fill assumptions. Faster realization may reduce losers and truncate the large-winner tail; both must be printed.

**G. Does a regime-adaptive policy beat simply doing less?** A filtered strategy's higher hit rate can arise from reduced exposure, fewer trades or a different beta mix. Compare total net utility, time invested, turnover, tail loss, large-winner contribution, coverage and abstention against appropriate controls. A decision system should be allowed to return insufficient evidence rather than manufacture a favored indicator.

**H. Will the product tell the same truth?** Evidence existence, maturity, current availability, rank and permission are separate. Stale/missing input must not become false or neutral. A dashboard and Terminal disagreement about a completed bar or event identity is an engineering failure, not a market regime.

## 8. Historical reconstruction requirements implied by these questions

The existing atlas and long price history do not by themselves create a point-in-time regime dataset. Separate three evidence classes:

1. **Final-vintage reconstruction:** useful for exploratory mechanisms, visibly not as-observed evidence.
2. **Source-vintage/as-observed reconstruction:** values and publication availability from a dated source, with explicit uncertainty about intraday/system capture.
3. **Live-forward observation:** source availability, actual system observation, decision cutoff and immutable revision recorded by the existing owner.

A regime observation needs economic reference period, source release/available time, first-observed time where required, revision/vintage, source identity, transformation and missingness. Historical final revised GDP/inflation cannot enter a simulated earlier decision as though already known. Full-sample smoothed state assignments cannot be described as online filtering. Pre-inception proxies and sector classification changes require explicit mappings and separate sensitivity analysis.

Effective sample size is limited by independent decisions, names, regimes and overlapping holding windows, not just rows. Broad regime models need adequate distinct episodes across states. Do not pool markets or instruments to inflate N while ignoring different sessions, price limits, instrument/roll structure or available data.

The research library should distinguish exploration from confirmatory work, record the entire attempted search family and its nulls, and bind outcomes to immutable code/data/config. These are existing Evaluation OS responsibilities, not a request to build a second experiment tracker.

## 9. Frozen Phase 22: preserve the exact question

[Phase 22][phase22] defines future LIVE_FORWARD `C2_1D_TURN@1` events after an explicit start receipt, conditioned on same-cut `C4_MTF_TURN@1.d2.turn`. This is a strict confirmed **2D StochRSI K/D cross**, not a generic MACD-age feature; C4 itself remains non-firing.

Q1: H10 W5 `excess_net`, mean-within-decision-date arm difference, then decision-week block bootstrap. Missing C4 is retained and disclosed, not converted to false. Q2: difference-in-differences between the prespecified hidden-fragility and relief/broadening cells, using qualified prior-known DFII10 and RSP/SPY over completed sessions ending T-1. The direction of the interaction is not assumed.

The start boundary requires accepted C1 private transport; C3 real RTH event through spool/forward store/QLedger; same-cut C4 durability without changing C2 identity; qualified real-yield availability/first-known evidence; prior TrialLedger registration of the exact config hash; and recorded live-forward epoch. A preregistration file is not that receipt.

The source's confirmatory floors are at least 30 episodes, 12 distinct decision months and name effective-N at least 8 in every arm used for a verdict. No return/statistic peek before the applicable floor. At the qualified read it specifies 5,000 decision-week bootstrap draws, seed 20260919. Those are this experiment's rules, not universal thresholds to transplant into every new study.

Historical latest-revised DFII10 without qualified first-known support cannot be silently inserted into Q2. Source-vintage recovery could support a separately frozen admissible amendment; it does not retroactively turn a historical dataset into this forward epoch. Operational counts/missingness can be inspected without opening the outcome.

## 10. Primary literature: what it does and does not establish

**Economic data vintage:** [FRED real-time documentation][fredrt] distinguishes information known at a historical time from current revised observations. Its [observations API][fredobs] exposes real-time/vintage and initial-release options. This supports source-vintage research, but date-level vintage metadata alone does not prove precise intraday availability or Mastermind's capture time.

**Momentum crashes:** [Daniel and Moskowitz][momentum] identify partly forecastable losses following market declines/high volatility and during rebounds. That is not a general theorem that every weak-breadth market makes every slow long-only signal fail. The portfolio construction, horizon, short leg and rebound exposure must be mapped before applying the result to Prophet.

**Industry momentum:** [Moskowitz and Grinblatt][industry] study industry contributions at intermediate, largely 6-12 month horizons. This motivates separating industry from stock-specific behavior, not a verified 1D/3D timing rule or a guarantee that narrow subthemes persist.

**Search bias:** [Bailey and Lopez de Prado][dsr] address selection bias, non-normality and backtest overfitting in Sharpe comparisons. A large indicator/parameter/regime search must disclose its search breadth. A deflated statistic is an additional diagnostic, not a substitute for an untouched time-ordered evaluation or realistic execution.

**Current descriptive macro check:** the [Treasury September table][treasury], inspected again in this audit, lists 10-year par real yield at 2.44% on September 1 and 2.93% on September 30: +49 bp. This supports the reported move, not its causal attribution to Prophet losses. Treasury par-real observations are not automatically the exact DFII10 series required by Phase 22.

The prior dossier preserves SEC/TradingView and media-source leads. This revision does not claim their figures were newly rechecked. Overnight volume share cannot alone establish or exclude price-discovery impact; even an unchanged 3D clock can reflect prices affected by overnight information.

## 11. Decision summary for the receiver

Already source-supported: the existing anchor repair must be reused; Prophet's baseline is not ordinary price MACD; independent product axes and existing owners matter; the broad family-regime null and failed 1.5-ATR gate must remain visible; Temporal Grain and TOI are distinct dependencies; Phase 22 has a specific unaltered question and strict start/read boundaries.

Still hypotheses: a universal shift toward shorter profitable cycles; systematic 3D lateness in narrow/high-rate environments; reliable regime-selected indicator/timeframe choice; theme-only admission; a valid Remaining Opportunity score; and a better dynamic exit policy. No live promotion follows from this handoff.

The scientific goal is not to prove the Chairman's first explanation. It is to identify which mechanisms survive falsification, where they add useful information and where the system should abstain, then use the existing product/evaluation owners to deliver the supported behavior. Scientific closure may be a null. Product completion still requires a coherent user capability rather than a stack of reports.

[v1]: https://github.com/mastermindx-market-intelligence/macro/blob/b598819bcecc2ef98e5848f473df9b21bd045118/research/prophet_v4/astra_regime_indicator_handoff_20261004/01_RESEARCH_INTAKE_AND_AUDIT.md
[rs]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/prophet/cpu_leadership/ENTRY_RS_THRESHOLD_FINDINGS_2026-09-21.md
[extension]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/prophet/cpu_leadership/ENTRY_DIRECT_EXTENSION_CHALLENGER_FINDINGS_2026-09-21.md
[atlas]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/SP500_NASDAQ_REGIME_ROTATION_ATLAS_2013_2026.md
[temporal]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/agentos/workstreams/WS-TEMPORAL-GRAIN-INTELLIGENCE.md
[catalog]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/engine/tech_catalog.py
[w1]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W1_EVIDENCE_CENSUS_HANDOFF_2026-08-27.md
[phase22]: https://github.com/mastermindx-market-intelligence/macro/blob/f5c2e829fef0a9891df0527a4bf74f280aaa0813/research/prophet_v4/US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md
[fredrt]: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
[fredobs]: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
[momentum]: https://www.nber.org/papers/w20439
[industry]: https://www.aqr.com/insights/research/journal-article/do-industries-explain-momentum
[dsr]: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
[treasury]: https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?field_tdr_date_value=202609&type=daily_treasury_real_yield_curve
