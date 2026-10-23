# Adaptive Signal Clock — Deep Research Scoping: Scientific and Product Sources

**Research vintage:** 2026-10-03. **Archive:** 2026-10-07. **Status:** literature/product scoping, not a complete systematic review or empirical Mastermind result. Companion: [main archive](ADAPTIVE_SIGNAL_CLOCK_DEEP_RESEARCH_SCOPING_2026-10-03.md) and [experiment/build gaps](ADAPTIVE_SIGNAL_CLOCK_SCOPING_EXPERIMENTS_2026-10-03.md).

## Scientific literature synthesis

The cited papers support the legitimacy of non-calendar market time and several plausible measurements. **None proves** that a unique ex-ante optimal signal timeframe exists for Mastermind or that adaptive selection improves entry localization, risk or economics on untouched instruments.

| Primary work | What it supports | Critical limitation or falsifier |
|---|---|---|
| [Clark (1973), A Subordinated Stochastic Process Model](https://econpapers.repec.org/article/ecmemetrp/v_3a41_3ay_3a1973_3ai_3a1_3ap_3a135-55.htm) | Stochastic market-time/time-change models | Time change is not a signal-family-specific winning horizon |
| [Engle & Russell (1998), Autoregressive Conditional Duration](https://econpapers.repec.org/article/ecmemetrp/v_3a66_3ay_3a1998_3ai_3a5_3ap_3a1127-1162.htm) | Irregular inter-transaction durations are dependent/stochastic | Venue/feed coverage, seasonality and duration-model instability |
| [Dacorogna et al. (1996), Changing Time Scale](https://onlinelibrary.wiley.com/doi/abs/10.1002/%28SICI%291099-131X%28199604%2915%3A3%3C203%3A%3AAID-FOR619%3E3.0.CO%3B2-Y) | Intrinsic-time research in financial forecasting | Sample/era-specific, not transferable clock-selection proof |
| [Aït-Sahalia, Mykland & Zhang (2005), How Often to Sample](https://collaborate.princeton.edu/en/publications/how-often-to-sample-a-continuous-time-process-in-the-presence-of-/) | A finite apparent optimal sampling interval can result from ignored microstructure noise | Explicit noise treatment may outperform discarding observations |
| [Barndorff-Nielsen et al. (2008), Realized Kernels](https://onlinelibrary.wiley.com/doi/10.3982/ECTA6495) | Noise-robust realized-variation estimation | A variance estimator is not a predictive signal-clock policy |
| [Andersen, Bollerslev, Diebold & Labys (2003), Realized Volatility](https://www.nber.org/papers/w8160) | Volatility dynamics and high-frequency information | Volatility forecast quality does not imply entry-timing gain |
| [Lo & MacKinlay (1988), Variance-Ratio Test](https://web.mit.edu/~alo/www/Papers/lo-mackinlay-88.html) | Tests for horizon-dependent departures from random-walk behavior | Multiple horizons, dependence, regime shifts and hindsight tuning |
| [Mandelbrot, Fisher & Calvet (1997), Multifractal Asset Returns](https://cowles.yale.edu/node/145456) | Serious multiscale/time-deformation alternative | One characteristic time may not exist |
| [Corsi (2009), HAR-RV](https://academic.oup.com/jfec/article-abstract/7/2/174/856522) | Parsimonious heterogeneous fixed-horizon volatility representation | A strong **fixed multiscale** baseline that may defeat adaptation |
| [Bacry & Muzy (2014), Hawkes Price and Trades](https://www.tandfonline.com/doi/full/10.1080/14697688.2014.897000) | Clustered/self-exciting trade and price activity | High data/compute burden and model-risk sensitivity |
| [Chen, Diebold & Schorfheide (2012), Multifractal Inter-Trade Durations](https://www.nber.org/papers/w18078) | Regime-switching and multiscale duration behavior | Does not identify a universally stable signal horizon |
| [Ntantamis (2010), Duration Hidden Markov Regimes](https://pure.au.dk/portal/en/publications/a-duration-hidden-markov-model-for-the-identification-of-regimes-/) | Regime state duration as a model target | Estimated state must be issued causally, not revised with future observations |

**Claim classes:** mathematical/model fact; empirical result for a specific market/sample/era; plausible mechanism; vendor claim; Mastermind hypothesis. Do not promote one into another. Microstructure-noise findings and fixed multiscale/multifractal explanations are adversarial evidence, not footnotes.

### Candidate ex-ante structural estimators (ranked for testing, never by future signal returns)

| Candidate | Data and rationale | Main weakness | Relative cost |
|---|---|---|---|
| Causal autocorrelation-decay / variance-ratio transition band | Existing PIT return history; persistence/reversal scales | Unstable under weak signal, nonstationarity and multiple comparisons | Low |
| Stationary-residual mean-reversion half-life | Causal Stock Identity measurement with identification/cap flags | Many price series are not stationary; half-life may be nonidentified | Low–medium |
| Volatility-persistence / HAR-style horizon components | PIT returns or noise-robust realized variation | Could merely rediscover volatility targeting; fixed HAR may suffice | Low–medium |
| Causally confirmed swing-period distribution | Time-stamped, confirmation-lagged extrema | Hindsight pivot detection is a severe leakage trap | Medium |
| Session/overnight contribution and actual bar duration | Existing canonical session/clock owner | May explain all apparent grain advantage without an adaptive clock | Low |
| Activity/trade-count/volume/dollar/variance-duration distributions | Qualified high-frequency activity and rights | Feed semantics, intraday seasonality, corrections and entitlements | Medium–high |
| Causal regime duration/change points | Regime owner's issued state/age/transition estimates | Smoothed full-sample states leak; change-point latency | Medium |
| Catalyst/event-arrival cadence | PIT event owner with publication/known-at timestamps | Sparse and nonstationary events, heterogeneous event importance | Medium |
| Wavelet/spectral scale concentration | Trailing-only multiresolution transforms | Full-sample period selection, aliasing, short-window instability | High |
| Hawkes/activity intensity | Trade/order-flow events with exact identity | Expensive, feed-dependent, estimation instability | High |

Favor robust bands/posteriors and explicit MULTISCALE or UNRESOLVED states over noisy argmax. Any estimator must specify units, censoring, data vintage, publication/known-at cutoff and independent confirmation design.

## Professional-system comparison — official docs checked in October 2026 scoping

| Product | Documented feature | Not demonstrated by cited documentation |
|---|---|---|
| [TradingView tick intervals](https://www.tradingview.com/support/solutions/43000709225-what-are-tick-based-intervals/) and [range charts](https://www.tradingview.com/support/solutions/43000474007-understanding-range-charts/) | Non-wall-clock display/bar construction | Ex-ante uncertainty-bearing optimal signal clock or OOS lift |
| [NinjaTrader bar types](https://ninjatrader.com/support/helpguides/nt8/bar_types.htm) | Tick, volume, range and session-sensitive bar construction | Generalizable predictive clock-selection evidence |
| [Sierra Chart bar periods](https://www.sierrachart.com/index.php?page=doc%2FChangingPeriodOfBars.php) | Flexible time/non-time chart configuration | Causal inferred scale distribution/abstention |
| [Bookmap Footprint](https://bookmap.com/knowledgebase/nl/docs/Addons-Footprint) | Time, reversal, range, volume variants | Automatic structural signal-clock selection with OOS validation |
| [QuantConnect time consolidators](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/consolidator-types/time-period-consolidators) and [volume Renko](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/consolidator-types/renko-consolidators/volume-renko-consolidators) | Programmable observation aggregation | A native proven ex-ante market-clock posterior |
| [Bloomberg BQuant](https://professional.bloomberg.com/products/bloomberg-terminal/research/bquant/) | Programmable institutional analytics/data/backtesting | Proprietary adaptive-clock algorithm must not be inferred |
| [LSEG CodeBook](https://www.lseg.com/en/data-analytics/products/codebook) | Cloud Python/data-platform research | Proprietary adaptive-clock algorithm must not be inferred |

**Product opportunity:** not more chart cosmetics. Mastermind may eventually integrate canonical instrument identity, session/data rights, Stock Identity structure, Granular Regime duration, catalysts, Market Memory, signal kernel and multiple downstream consumers into a transparent **why this horizon / why not choose** explanation. This differentiation remains a design hypothesis until incremental utility is measured.

## High-value visualizations for the eventual empirical report

Show (1) uncertainty density over log horizon with multiple modes; (2) G/A/K/D intervention effects; (3) scale turnover and hysteresis; (4) instrument-disjoint OOS forest plot against fixed multiscale/no-selector; (5) regime-by-scale concentration; (6) kernel-memory compatibility; (7) effective versus nominal independent N; and (8) wall-time versus activity-time comparisons. Negative captions should be reported plainly: if memory matching or a fixed ensemble removes the edge, adaptation loses.

**Source quality warning:** the links above are a prioritized primary-source and official-doc starting set, not a claim that the entire requested literature/competitive audit has been completed or that all vendor features are unchanged after the October 2026 scoping date.
