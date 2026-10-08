# 03 | Public evidence synthesis

## How to read this evidence

This is an incremental adjudication of the existing RS Pullback and LLR-24 literature census, not a replacement bibliography. Primary papers, author/institution repositories, publishers and the exchange calendar were used. Replication blogs, AI summaries, vendor marketing and attractive charts were not admitted as performance evidence. Where access exposed only an abstract or introduction, the source register says so. No inaccessible full-text result was silently inferred. [I03, I06, I26]

The search addressed three different claims: intraday returns can contain predictable structure; relative/group information can matter; and the exact proposed pivot package improves decisions after realistic costs. Evidence for the first two is not automatically evidence for the third.

## Intraday timing is plausible, but 30m is not crowned

**Heston, Korajczyk and Sadka (2010).** Their half-hour result concerns return continuation at the same intraday interval on later days. Their short-lag reversal analysis also implicates liquidity and bid–ask effects. In the examined implementation, crossing the spread removes pure strategy profits. This supports time-of-day controls and an explicit execution model, not a bullish-rejection-bar rule. [E02]

**Gao, Han, Li and Zhou (2018).** The paper studies market intraday momentum: an opening return measure including the overnight component predicts the final half-hour in its SPY sample. It motivates separately identifying opening/session effects. It does not establish that a stock's 30m pullback pivot predicts its next two hours. [E03]

**Huddleston, Liu and Stentoft (online 2021; journal issue 2023).** The publisher reports economically meaningful five-minute market prediction from lagged constituent returns using regularized linear and tree models, with performance conditional on trading environment. This is positive evidence that intraday cross-sectional information is not automatically useless. It remains a different target and universe from leader-pivot localization. [E04]

**Lo, Mamaysky and Wang (2000).** Systematic pattern recognition yielded conditional information in daily stock-return distributions. The relevant lesson is to specify a pattern mechanically and compare conditional forecasts rigorously. It is not evidence that future-confirmed chart pivots were knowable earlier, or that an intraday implementation clears costs. [E05]

**Synthesis.** The literature justifies a bounded causal experiment. It does not justify treating a familiar chart interval as a privileged economic timescale. A observed clock benefit must survive matched information, anchoring, filter memory, seasonality and economic decision-time comparisons. That conclusion is this report's inference, not a result quoted from any one paper.

## Industry, residual and relationship information: relevant at the right ruler

**Moskowitz and Grinblatt (1999).** Industry momentum accounts for much of stock momentum at intermediate, roughly six-to-twelve-month horizons. Industry is therefore an essential comparator before attributing a benefit to a dynamic theme. The horizon mismatch is material; an intermediate-horizon effect does not validate a two-hour permission gate. [E06]

**Blitz, Huij and Martens (2011).** The verified abstract reports that residual-return ranking reduces time-varying factor exposures and improves historical risk-adjusted momentum performance. This supports residualization as a representation worth considering. It does not validate a residual trough-turn timer; exact intraday parameters cannot be imported from that abstract. [E07]

**Hoberg and Phillips.** Their primary data library provides text-based, firm-centric product-market relationship structures. It demonstrates an economically motivated alternative to coarse administrative industry labels. An annual relationship label is not, by itself, a receipt showing when an intraday trader could know it. Our PIT and rights requirements remain separate. [E08]

**Cohen and Frazzini (2008).** Public customer–supplier links support evidence of delayed information incorporation across economically linked firms. This gives a mechanism for researching related-firm information. Semantic theme membership is not the same relation, and the reported economic result does not transfer its magnitude or horizon to this product. [E09]

**Synthesis.** Group identity can carry information, but “strong group + weak stock” is not a sufficient entry hypothesis. The new question is selective resilience during a common shock, versus idiosyncratic deterioration after peers recover. Mastermind's own peer-diffusion and synchronized-participation failures make that distinction more important, not less. [I19]

## Information, liquidity and the limits of OHLCV

**Savor (2012).** Analyst-report-associated price events show a different subsequent return pattern from the paper's no-information events. The information proxy and observation timing matter. A missing item in our news feed cannot be reclassified as a proven absence of information. [E10]

Mastermind's own OHLCV-grade liquidity-shock classifier did not reproduce the hoped-for separation and is closed in that construction. A new six-label taxonomy cannot revive it. Mechanism labels should report source-supported observations, possible explanations and unknowns; they must not purport to identify institutions or hidden intentions. [I19]

**Cont, Kukanov and Stoikov (2014).** Genuine order-book events and order-flow imbalance explain contemporaneous short-interval price changes in their study. This motivates a later L1 experiment on otherwise matched pivot states. Contemporaneous explanation is not a 30–120m forecast result, and bar-volume proxies are not the paper's OFI. [E11]

## Statistical method is part of the product decision

**Gneiting and Raftery (2007)** supplies the justification for proper probabilistic scoring rather than judging probabilities by hit rate alone. The commercial threshold and acceptable risk trade-off are still our preregistered decisions. [E12]

**Sullivan, Timmermann and White (1999)** shows why the full universe of examined technical rules matters for data-snooping adjustment. **Bailey and coauthors** develops backtest-overfitting diagnostics. Neither licenses repeated inspection of a nominally sealed holdout or converting a chronological experiment into random row splits. [E13–E14]

## Evidence-weighted ruling

The reviewed primary corpus contains relevant positive mechanisms and important limits, but no directly qualifying validation of the entire commissioned conjunction. This is a bounded statement about the reviewed sources, not a claim that no such study exists anywhere.

The strongest reason to build is that a truthful, source-bound structural record has immediate descriptive value and creates a disciplined test of incremental timing. The strongest reason not to launch a richer predictive system now is the combination of unadmitted target data, substantial internal negative evidence, and several easy ways to create apparent success through definition, timing or selection.

The architecture should therefore make it cheap to reject a feature, cheap to keep the simple version, and impossible for an untested layer to acquire trading authority merely by being installed.
