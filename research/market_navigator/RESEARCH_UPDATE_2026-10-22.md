# Research update: measurement clocks, historical evidence and forecast targets

22 October 2026. Research/engineering findings, not a new trial registration,
profitability claim, promotion or allocation instruction.

## 1. VIX1D needs a measurement-phase label

Cboe's launch-methodology explanation describes changing near/next-expiry weights.
With less than 60 business minutes to near expiry, the near-term volatility is held
at its last valid value during interpolation. After near expiry, only the next term
remains. This concerns the construction of the indicator, not equity direction.
Source inspected as HTML: Cboe, 24 April 2023, Important Qualities section:
https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ/

Engineering consequence: `engine/market_navigator_measurement.py` annotates the
published measurement phase using explicitly supplied owner session instants.
It does not construct an exchange calendar, assume all closes occur at 16:00,
recalculate VIX1D, or verify the vendor actually applied the methodology. Missing
calendar evidence and observations unavailable at the cutoff remain unavailable.
Boundary tests cover the exact 60-minute transition, expiry, dissemination end,
early-close inputs, timezone equivalence and future evidence. Every authority flag
remains false. The session fixture is synthetic, not a claim that the named date
was an actual early close.

The accompanying coverage assessor makes daily bars, missing availability clocks,
missing joint underlying observations, missing executable options and unresolved
path ordering explicit. Even all declared coverage flags being true is NOT source
verification or trial admission. A minute bar that contains both relevant touches
cannot automatically establish which event came first.

## 2. Volatility forecasts are not stock-direction forecasts

Albers (2025), Journal of Futures Markets, studies next-day S&P 500 realized volatility.
The paper reports 316 out-of-sample days and a 77.85% rise/fall accuracy for volatility
with its risk-premium-adjusted VIX1D approach; that is NOT a stock-direction hit rate.
Its target combines five-minute returns and an overnight return, and its forecasting
information is taken at the previous close. These are author-reported results, not
Mastermind replication or validation of a 6.88 reversal trigger. Relevant inspected
HTML sections: 2.2, 2.8, 3, 4.2, 4.5 and 5.
https://onlinelibrary.wiley.com/doi/10.1002/fut.70023

Internal integration finding: `engine/vol_fitted_har.py` is an existing, unwired Q07
research reference with a DAILY_CC_MSR target and existing controls. Its header
explicitly distinguishes that daily proxy from high-frequency integrated variance.
Do not compare differently defined targets and call the result a model improvement.
The next admissible study must bind the same realized-risk definition, observation
window, information cutoff, loss function and existing registration before fitting.
No second HAR implementation or probability/size layer was introduced here.

Albers and Kestner (2024), Finance Research Letters 105186, report a methodology-driven
intraday/overnight pattern. Only the publisher's indexed abstract/highlights were
available; the attempted full-page retrieval returned HTTP 403. Their full methods
were not inspected or replicated.
https://www.sciencedirect.com/science/article/pii/S1544612324002162

## 3. An available historical product is not a live licensed feed

The Cboe DataShop Main Channel Tick Data page describes disseminated index values
and delivery shortly after the next day's open, with external redistribution
restricted. The page alone does not establish VIX1D membership, our entitlement,
latency, or product display rights. The linked definition-feed retrieval did not
resolve in this session. No purchase, account change or data acquisition was made.
https://datashop.cboe.com/main-channel-tick-data

Consequently, an eventual archive adapter must retain actual availability separately
from event time. An overnight delivered file cannot support claims that Mastermind
held the data live on the prior afternoon. Daily coverage already audited in the
foundation remains useful descriptive evidence, not a replacement for joint
intraday observations or option-execution data.

## 4. Executed incumbent-owner integration

`engine/market_navigator_memory.py` now reads the incumbent AsKnownAtReader contract,
validates its complete packet and retains the owner's clocks without translation.
The display projection withholds opaque snapshot contents instead of inventing a
market state from a reference. It distinguishes exact absence, access denial,
unavailable storage, an invalid packet and a wrong instrument/cutoff.

Comparison labels separate changed recorded values, changed references, changed
source evidence and coverage loss. A missing return is not zero. Contradictory
objects for one exact operational query are refused rather than silently called a
refresh. Original packets remain detached and unchanged.

An executable consumer uses TrustedFileAsKnownAtReader directly. Synthetic tests
exercise the incumbent source projector, identity builder, trusted capture writer,
retained read and Navigator projection through a real subprocess. File and directory
contents are unchanged by inspection. An absent trusted root remains absent.
This proves the source/reader integration on synthetic evidence, NOT a deployed live
market path. Production entitlement and the installed source generation remain open.

The legacy W1A missing-only reader has a separate integration hazard: its validation
path can create a previously absent root. Navigator's inspection CLI does not select
that reader or modify its owner. The existing owner module was left unchanged.

## 5. Concrete release repair and remaining evidence

The foundation CI failed its import-pinning check for the benchmark and model-audit
entrypoints. Both now pin their own repository root before importing engine modules;
foreign-working-directory subprocess tests cover the repair. No baseline or waiver
was loosened. Focused CI and real release still need to be consumed for the new head.

The independent review summon returned backend_unavailable and its exact original
reply lookup returned reply_unavailable. No START or reviewer result is established;
the original operation was not replayed or replaced. Direct bounded source work
continued. Native Paper still needs a safe new file, and the full product remains
unaccepted until live source, design, personal-state and production-path proof exist.
