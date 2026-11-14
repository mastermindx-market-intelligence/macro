# From indicator confluence to a mechanism-and-horizon research system

Date: 2026-11-14 UTC. Research synthesis for the Chairman's November 13 commission.
Owner/program: WS:PROPHET-CONDITIONAL-FUSION, linked to the existing Entry Radar,
Stock Identity and entry-timing owners. See `ENTRY_REGIME_RESEARCH_PROGRAM_2026-11-14.md`
for source pins, task tree, acceptance, custody and retained holds.

**Conclusion:** the useful design is not 'more indicators agree, therefore buy'. It
is a testable account of **why a payoff might exist, what information is not already
priced, when that mechanism should act, how it can fail, and whether its net payoff
survives implementation**. T1/T2 is one timing representation, not a sacred engine
and not an independent source of economic value. No claimed breakthrough or live
trading authority follows from this memo.

## 1. The decision we actually want to improve

A hypothetical decision at time t concerns a distribution of future payoffs, not a
binary label saying that a stock is good. For a specified horizon h, the research
question is whether expected incremental payoff exceeds implementation costs and
whether the uncertainty and loss path are acceptable. The comparator matters:
profit versus cash, excess versus the market, and marginal contribution to a
portfolio are different quantities. Keep them as different heads in the incumbent
arena rather than blending them into a flattering score.

For a simple win/loss illustration, expectancy is p*average_win -
(1-p)*average_loss - costs. Raising p while truncating the average winner can make
expectancy worse. A 55% win-rate strategy is not necessarily better than a 45%
strategy. Likewise, fewer stop-outs can merely mean a lower-volatility selection,
and lower drawdown can merely mean less market exposure. These are algebraic
possibilities, not claims about our current signal's performance.

An attractive chart pattern also does not identify a unique cause. A rising price
could be information incorporation, risk-premium repricing, temporary demand or a
price response to constrained liquidity. Price alone cannot prove who bought, what
they believed or whether they were informed. We should not turn an LLM narrative
about institutional accumulation into a measured flow feature.

## 2. What published practitioner approaches actually contribute

There is no single public recipe used by 'the best traders', and selected stories
about successful calls are not an unbiased strategy test. The following sources
supply useful mechanisms and implementation lessons, not transferable win rates.

| Public primary source | Bounded observation | Application to this program |
|---|---|---|
| Berkshire 1992 shareholder letter [S1] | Value is framed through expected cash flows, price and a margin for estimation error; a low multiple alone does not establish value. | Separate economic selection from a short-term trigger. A company's attractiveness is not proof of a 21-session timing edge. |
| Oaktree, Taking the Temperature (2023) [S2] | The memo describes rare extreme-cycle judgments, ordinarily distinct from frequent market timing; selling can reflect value realization, thesis deterioration or a better alternative. | Use context to test a mechanism, not to claim daily macro foresight. Distinguish thesis exits from price-risk exits and opportunity-cost exits. |
| Moskowitz/Ooi/Pedersen, Time Series Momentum (2012) [S3] | The study reports return persistence using own past returns across 58 futures/forwards. | Test transparent persistence baselines. Evidence at those instruments and horizons does not validate daily individual-stock T1/T2 entries. |
| Novy-Marx, Fundamentally, Momentum is Fundamental Momentum (2015) [S4] | The paper argues earnings momentum explains price-momentum results in its sample. | Treat changes in business expectations as a distinct hypothesis; do not revive our rejected SUE construction or infer its implementation is valid. |
| Gârleanu/Pedersen, Dynamic Trading (2013) [S5] | Predictors can have different strengths and decay rates; costs, risk and correlations affect their useful combination. | Match signal horizon, holding logic and execution. Fast and slow evidence need not fire simultaneously. |
| Frazzini/Israel/Moskowitz, Trading Costs (2018) [S6] | Actual institutional trade data reveal costs varying with trade and asset characteristics. | Constant basis-point costs are a sensitivity screen, not an execution model or capacity proof. |
| Daniel/Moskowitz, Momentum Crashes (2016) [S7] | Momentum losses can cluster in rebound/panic conditions; the long-short construction's losing-stock short leg matters. | Study transitions and mechanism-specific exposure. Do not copy a long-short crash rule blindly into long-only entries. |
| Moreira/Muir (2017) versus Cederburg et al. (2020) [S8/S9] | The former reports benefits from volatility management; the latter finds weak real-time transfer across a larger strategy set and unstable fitted combinations. | Use an equal-risk comparator, genuinely ex-ante parameters and implementation costs. Lower exposure is not new alpha. |
| Goyal/Welch/Zafirov (2024) [S10] | Many published equity-premium predictors deteriorate on later data; a small subset remains useful. | Freeze rules, preserve negative results and reserve truly unseen observations. A plausible macro explanation is not enough. |
| Asness/Moskowitz/Pedersen, Value and Momentum Everywhere (2013) [S11] | The paper studies value and momentum across markets and asset classes. | Diversifying complementary strategies is different from requiring every security to pass all their filters. |

These summaries rely on the linked original publications or author/institution
abstracts, not performance claims inferred from a vendor chart. Full methods have
not been independently replicated here. Where a full paper fetch was blocked,
only its available primary abstract was used.

## 3. Give every component a distinct, falsifiable job

### Economic opportunity: why could ownership be rewarded?

Candidate mechanisms include a change in expected cash generation, an excessive
price relative to a defensible valuation range, a change in required risk premium,
or a temporary supply/demand constraint. The useful variable is often the change
relative to expectations, not simply a high level of reported growth or quality.
A company can report excellent results yet fail to outperform if the price already
requires even better results. That is a research hypothesis to operationalize with
proper expectation data; an absent consensus history cannot be replaced by a
confident analyst narrative.

Within the existing registry, this maps to qualified F4 event inputs and F7
fundamental/identity inputs. Snapshot-only fundamentals remain snapshot-only.
Economic claims require a timestamp and a defined alternative explanation. A strong
business may be a good long-horizon candidate yet a poor short-horizon purchase.

**Falsifier:** after contemporaneous price, industry and risk controls, the proposed
new information does not improve out-of-time net outcomes or is not knowable then.

### Context: when should this particular mechanism work?

Replace a universal 'good market' label with a small set of observable axes:
trend direction/persistence, volatility and stress, participation/correlation,
liquidity/cost and relevant event state. These describe different things. A stable
uptrend is not the same as low volatility; a rebound after panic is not the same as
an established bullish regime. A lagging market gate may omit the first recovery
phase, which can be exactly the opportunity a reversal mechanism seeks.

The proposal is to test context as an **interaction**, not automatically as a veto.
A trend-continuation mechanism and a dislocation-recovery mechanism can rationally
respond differently to the same state. A sector-local opportunity can coexist with
an unfavorable index. Sector membership and historical context must be point-in-time;
today's sector assignment is not sufficient.

Use the existing F6 and F3 owners and estimability meter. Begin with interpretable
observable controls. A latent-state model must beat those controls on untouched
windows, use filtering available at the time rather than hindsight smoothing, and
carry uncertainty/abstention. Do not choose the number of regimes because a return
heatmap looks appealing.

**Falsifier:** apparent context uplift disappears under matched calendar/risk
controls, fails later eras or requires thin states/retrospective labels.

### Momentum: what changed in the price process?

T1/T2 detects a particular multi-timeframe momentum transition. It is not synonymous
with every economically useful form of momentum. Separate three candidate jobs:
**direction/persistence** (is a move continuing), **relative leadership** (is this
asset outperforming alternatives), and **transition/repair** (has a prior adverse
path changed). Breakout and pullback-reclaim observations are additional timing
representations, not necessarily additional independent information.

MACD, RSI, StochRSI and moving-average derivatives can all reuse the same price
history. Counting agreement as independent evidence inflates apparent confidence.
Within F1/F2, compare substitutions first, then combinations with leave-one-family-out
and redundancy tests. If a simpler return/average rule captures the useful effect,
prefer it unless the more intricate detector demonstrably improves capture or risk.

Our first registered pilot does exactly the substitution/control experiment: the
explicit technical T1/T2 core, positive-trend state, prior-high breakout and
pullback reclaim, each with the same unfiltered/trend/stress context definitions.
Those are fixed mechanisms, not a threshold search. The native current gate's
context waiver and latch are excluded and disclosed; the pilot is not live-board
performance.

**Falsifier:** the complex trigger cannot improve on simpler alternatives after
costs, common coverage, observation clocks and independent-event accounting.

### Entry and execution: what can actually be captured?

The relevant price is an executable price after the evidence becomes known, not
the candle on which a favorable cross is later drawn. Completion of a multi-session
bar, observation, publication, order submission and fill are separate clocks.
Waiting for confirmation can reduce false starts while paying away part of the
move; neither consequence is automatically desirable. Treat that as a measured
trade-off between capture, adverse excursion and rejection of winners.

A stop level or drawn reward/risk box is not an expected payoff distribution.
Gap risk, spreads, liquidity, delayed fills and costs can break the geometry. The
current pilot uses next-session-close returns and symmetric cost sensitivities;
it does not pretend to simulate an intraday stop. The incumbent execution-cost
research owns richer cost estimates; reuse it rather than adding another execution
model with convenient constants.

**Falsifier:** the apparent edge is predominantly signal-to-fill price movement,
vanishes at plausible cost/delay, or depends on unavailable intraday ordering.

### Exit and holding period: why continue to own the position?

Separate (a) the information thesis being invalidated, (b) a path/risk limit,
(c) expiry of the forecast horizon and (d) a more attractive use of capital.
They are not interchangeable. A technical oscillation need not invalidate a slow
business thesis; a long-run business thesis does not excuse an unbounded loss in a
short-horizon tactical experiment. Entry and exit must refer to the same declared
mechanism and objective.

Keep fixed-horizon grading policy-free. Test trade management on the SAME qualified
entries through `scripts/exit_policy_study.py` and the existing replay/execution
owners, without rewriting the track record. Reuse the prior exit-grid negatives;
no undirected stop/target lottery. Any new exit interaction needs a separate frozen
protocol, next-available execution convention, cash carry, cost and paired-calendar
controls. A close-derived trigger cannot be sold at that same close without an
explicit executable convention.

**Falsifier:** an exit advantage is just shorter exposure, hindsight trigger timing,
ignored reinvestment/cash return or removal of a few large losses selected after seeing them.

### Portfolio and uncertainty: is the combination useful and knowable?

Do not sum overlapping trade averages and call the result a portfolio CAGR.
Calendar-level capital, concurrent holdings, risk concentration, turnover and idle
cash must reconcile. Several technology names can be one market bet. Conversely,
a somewhat weaker individual mechanism can still improve a portfolio if its
qualified payoff is genuinely complementary.

A confidence layer should answer what is measured and how stable it is, not produce
a reassuring number. Missing features, stale contexts, thin states and source gaps
are reasons to abstain from a new claim. A beta residual is an attribution diagnostic,
not a complete neutralized portfolio or proof of tradable alpha.

**Falsifier:** the result depends on duplicated same-day rows, a single episode,
one era/name, concentrated exposure, unstable parameter fits or selective reporting.

### Prior negative regime evidence remains binding

`DNR:KILL-PER-SIGNAL-FAMILY-RELIABILITY` already rejected a broad family-by-regime
reliability grid graded on forward drawdown, with weak/unstable interaction evidence
and unestimable richer axes. This program does not resurrect that grid, predict a
family win probability, or convert a market-state tag into a multiplier. The fixed
pilot measures descriptive net-return selection contrasts on explicitly named price
mechanisms; it cannot establish a family-by-regime interaction or reopen a promotion.
Any future interaction claim must first satisfy the native target-axis estimability
meter, register the interaction as primary and survive matched calendar/main-effect
controls and forward validation. A contrast table is not a reliability model.

The 12 pilot arms and 11 primary contrasts were fixed in an immutable specification
before numerical outcomes. No Deflated Sharpe claim or best-of-grid selection is
made. Any future fitted search must use the existing trial-accounting and arena
owners, count every generated candidate and preserve previous negative evidence;
the pilot manifest is not a second trial registry or permission to lower that count.

## 4. The combination ladder and existing ownership

This is a bounded ladder of hypotheses, not permission to run every Cartesian
product. New comparisons need exact data/clock qualification and a frozen budget.

| Lane | Proposed informational interaction | Existing owner | Required next proof |
|---|---|---|---|
| A. Price mechanism x market context | Does a predeclared trend/stress state improve a particular trigger rather than all triggers? | F1/F2/F6; research adapter, no detector registry change | Registered pilot and independent later evaluation; full-board parity separately |
| B. Relative leadership x participation | Is leadership broad/sector-supported rather than just market beta? | F2/F3; existing RS/Entry Radar work | PIT cohort membership, common coverage, matched-sector/calendar controls |
| C. Event/expectation change x price acceptance | Does a newly available business/event change add information beyond prior price movement? | F4 with F1/F2 | Actual release/receipt timestamps, expectation data, missed-winner accounting; retain prior SUE nulls |
| D. Durable economics x repaired path | Does a longer-horizon economic thesis benefit from a timing overlay without destroying winner capture? | F7/Stock Identity with entry owner | Vintage fundamentals and separate long-horizon objective; not Stage-2 win-gate resurrection |
| E. Dislocation x stabilization | Is recovery information distinct from simply buying lower-volatility or cheaper names? | Existing bottom/entry-timing owners, F3/F6 | A materially new, registered mechanism; do not recycle killed calm-base or insider confirmers |
| F. Mechanism x exit horizon | Is holding logic appropriate for information persistence and risk? | Existing exit-policy/replay/execution owners | Fixed-entry, executable-clock, cash/cost and exposure-matched paired tests |

After one component survives its proper test, first ask whether it is a substitute,
a rank modifier, an explanatory tag or a genuine selective gate. A useful descriptive
feature need not become a gate. Combining two useful strategies at portfolio level
is another experiment, not the same as applying their intersection to every entry.

## 5. How we make a false winner harder to manufacture

Predeclare the metric, events, mechanism, inputs, horizons and comparison count before
looking at results. Preserve the unchanged incumbent. Use the actual source-availability
clock, point-in-time universe and non-survivors. Normalize/fit only on training data;
purge overlapping horizons and embargo adjacent evaluation windows. Compare against
simpler controls and then against equal-risk/exposure controls. Date/episode blocks,
not ticker rows, set uncertainty; multiplicity includes attempted combinations and
abandoned variants. Report rejected opportunities and negative outcomes alongside
retained-trade precision. Use known-good and deliberately broken fixtures before
financial evidence. Treat a later prospectively frozen test as confirmation, not a
continuation of tuning.

The current implementation makes these requirements observable: immutable input
hashes and specification, future-suffix mutation tests, native-gate prefix parity,
unknown-not-false handling, common-calendar checks, date-blocked comparisons, cost
sensitivity and a no-promotion research consumer. It does not solve all empirical
problems. The fixed survivor sample and price-vintage/basis limits remain explicit.

## 6. Measured data reality, not a model wish list

The new outcome-blind readiness audit found 206,840 candidate rows but only 64 dates
across five calendar months at the pinned source. All four examined native macro axes
failed the existing twelve-month-per-state contrast requirement. The full-family
coverage calculation also exposes absent, snapshot-only and forward-only evidence.
This does NOT invalidate the operator-adopted C1 ranker; it prevents claiming that
this short record establishes new conditional alpha. `readiness.json` preserves
counts, native refusals, source hashes, date discrepancies and decoded column lists.

Date discrepancies require original publication/receipt evidence, not cosmetic
backfills. A later context attached to an older economic-session label may or may
not have been usable; the two dates alone do not prove it. Do not make a model look
better by treating an unknown input as a measured neutral value, or by substituting
an unrelated historical regime series for the specified one.

## 7. Research judgment

The most promising design hypothesis is **mechanism-specific, horizon-aware,
uncertainty-aware conditional selection**, with a replaceable momentum module and
separate execution/portfolio discipline. This is a research direction, not a proven
strategy. The highest-value near-term improvement may be discovering where NOT to
make a claim, removing redundant confirmation and paying less implementation cost,
rather than discovering a secret indicator. A genuine success can be a simpler,
more robust system; a credible negative result also prevents expensive mistakes.

## Source register (primary; accessed November 14, 2026 UTC)

S1. Berkshire Hathaway, 1992 shareholder letter, intrinsic value/growth/margin of safety:
https://www.berkshirehathaway.com/letters/1992.html

S2. Howard Marks/Oaktree, Taking the Temperature, July 10, 2023:
https://www.oaktreecapital.com/insights/memo/taking-the-temperature

S3. Moskowitz, Ooi and Pedersen, Time Series Momentum, 2012:
https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum

S4. Novy-Marx, Fundamentally, Momentum is Fundamental Momentum, NBER w20984, 2015;
primary abstract retrieved; blocked full-page request was not treated as a full-method read:
https://www.nber.org/papers/w20984

S5. Garleanu and Pedersen, Dynamic Trading With Predictable Returns and Transactions Costs, 2013:
https://www.aqr.com/Insights/Research/Journal-Article/Dynamic-Trading-With-Predictable-Returns-and-Transactions-Costs

S6. Frazzini, Israel and Moskowitz, Trading Costs, 2018:
https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs

S7. Daniel and Moskowitz, Momentum Crashes, Journal of Financial Economics, 2016;
original author/institution abstract and publisher search extract:
https://business.columbia.edu/faculty/research/momentum-crashes
https://doi.org/10.1016/j.jfineco.2015.12.002

S8. Moreira and Muir, Volatility-Managed Portfolios, Journal of Finance, 2017;
primary abstract, not an independently replicated portfolio:
https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.12513

S9. Cederburg, O'Doherty, Wang and Yan, On the performance of volatility-managed
portfolios, Journal of Financial Economics, 2020; author-institution abstract:
https://experts.arizona.edu/en/publications/on-the-performance-of-volatility-managed-portfolios/

S10. Goyal, Welch and Zafirov, A Comprehensive 2022 Look at the Empirical Performance
of Equity Premium Prediction, Review of Financial Studies, 2024; published abstract:
https://academic.oup.com/rfs/article/37/11/3490/7749383

S11. Asness, Moskowitz and Pedersen, Value and Momentum Everywhere, 2013:
https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere
