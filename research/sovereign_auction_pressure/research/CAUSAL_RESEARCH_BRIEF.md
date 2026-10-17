# Sovereign Auction and Funding Pressure Intelligence — causal research return

Prepared 2026-10-08. Bounded research support under the parent program owner. No empirical model was fitted, no source repository was changed, and no production effect was attempted. These scratch notes require the parent's normal canonical persistence. The attached packet and the three recovered null-study artifacts were read; the combined MASTER_PACKET was verified to contain the three substantive packet documents exactly.

## Decision

**Build the official lifecycle, separate duration and settlement amounts, and deterministic event importance now. The most defensible first new empirical vertical is settlement funding context. No inspected evidence establishes a point-in-time T-1 SPY/QQQ auction warning for Mastermind.**

This is a scoped primary-source synthesis, not an exhaustive systematic review or a replication. The evidence supports researching five distinct questions; it does not support treating their answers as interchangeable. An announcement price shock, a predictable intraday concession, an auction-result surprise, and settlement financing pressure are different exposures with different legal decision times.

The accompanying `H1_H5_PREREGISTRATION_CANDIDATE.md` turns that separation into a runnable research specification. It is outcome-blind with respect to new calculations in this task, but it is not canonically preregistered until adopted and committed by the parent. Historical studies already reported to the team cannot be relabeled untouched holdouts.

## 1. Directly inspected evidence and limitations

The following capsules intentionally distinguish a paper's measurement from a forecast that Mastermind could actually implement. PDF page numbers below refer to printed article pages unless explicitly called PDF indices.

### S1 — Intraday concession and its recent attenuation

Fleming, Liu and Nguyen, NY Fed Staff Report 1188, March 2026, revised July 2026. [Paper](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1188.pdf); [official record and licensing disclosures](https://www.newyorkfed.org/research/staff_reports/sr1188).

Inspected §§2.4, 3, 4.1 and the introduction/results discussion. Nominal coupon auctions span June 25, 1991–July 25, 2024, across 2/3/5/7/10/30-year tenors; scheduled reopenings are included, while 20-year bonds and several exceptional reopenings are excluded. GovPX/BrokerTec tick data are sampled each minute. Pressure compares three hours before cutoff with three hours after results, excluding the immediate result jump. Full-sample pressure is approximately 0.7–1.2 bp, and attenuates recently despite higher issuance. More nondealer absorption is one explanation. This measures rates microstructure, not ex-ante equity returns.

PIT warning: §3.1 footnote 12 reconstructs missing result times using surrounding auctions, including six future auctions. §3.3 standardizes volatility over the full sample. Neither procedure is an eligible historical forecasting transform. Commercial data rights are explicit on the official record.

### S2 — Dealer constraints add information in the liquidity tail

Duffie, Fleming, Keane, Nelson, Shachar and Van Tassel, NY Fed Staff Report 1070, August 2023, revised October 2023. [Paper](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1070.pdf); [official record](https://www.newyorkfed.org/research/staff_reports/sr1070).

Inspected §§4, 6 and 7. Main sample: July 2017–December 2022, 23 primary dealers, 1,336 trading days. Extended analyses begin in 2005. The study combines BrokerTec, Tradeweb, regulatory TRACE, dealer-level FR 2004 and supervisory VaR data. Quantile regressions find that inventory/flow-based capacity measures explain extreme illiquidity beyond yield volatility; benign-period effects are much smaller. This supports testing a nonlinear constraint mechanism.

Its capacity denominator is each dealer's in-sample maximum; weekly positions are attached to the most recent Wednesday. These are explanatory research constructions, not public contemporaneous capacity readings. Public aggregate positions do not recreate dealer-level supervisory information. A released inventory percentile can be a proxy, but must not be named measured capacity utilization. No SPY-warning claim follows.

### S3 — Announcement news and a material identification assumption

Phillot, *AEJ Macroeconomics* 17(1), January 2025, pp.245–273. [Article record](https://www.aeaweb.org/articles?id=10.1257/mac.20210243); [current supplementary appendix](https://www.aeaweb.org/articles/materials/22186); [replication-package record](https://doi.org/10.3886/E192741V1).

The article's abstract reports 1998–2020 announcement-window futures instruments and subsequent financial-market responses. **Main article access was gated; its full methods were not inspected.** The 14-page current appendix was inspected, including A.3/A.4/A.6 and data citations. A.4 requires constant demand elasticity, or variation unrelated to unexpected supply characteristics, to compare price-derived shocks across time. A.6's prose says “reject” where its predominantly high p-values support failure to reject lag predictability; those tests cannot prove exogeneity. The data bibliography includes purchased PortaraCQG minute futures and Bloomberg/Refinitiv inputs.

The replication record was readable, but file download was unavailable through the retrieval tool. No replication or data-license entitlement is claimed. The author-linked 2021 preprint was also inaccessible. The companion 2026 study below supplies directly inspected announcement-identification methods.

### S4 — Supply volume and maturity composition need different interpretations

Bi, Phillot and Zubairy, Kansas City Fed RWP 26-04, April 2026; manuscript dated March 26, 2026. [Paper](https://www.kansascityfed.org/documents/15746/rwp26-04biphillotzubairy.pdf).

Inspected §§2, 4, 5 and Appendices A.3, B.1/B.2. Announcement sample: October 1998–February 2025. Four Treasury futures return series in 30-minute windows feed two rotated factors; daily local projections use lagged controls and HAC inference. The factors are interpreted as debt-volume and maturity-composition news. Volume shocks generally raise yields; maturity extension can steepen the curve while reducing credit premia and VIX. These are working-paper estimates, not forecast validation.

The “shock” is constructed from prices observed around the announcement, not a T-1 dollar surprise. Appendix A.3 explains why TBAC-recommendation gaps are not equivalent to expected-supply news. Appendix B.2 specifies licensed LSEG minute futures, Bloomberg DV01 and public daily outcomes. Full-sample factor extraction or the reaction itself cannot become a pre-announcement predictor. Institutional simplifications in §2.1 must yield to the actual Treasury notices.

### S5 — A direct modern settlement/repo experiment

Anbil, Anderson, Cordes and Ruprecht, FEDS Note, August 26, 2026. [Full note](https://www.federalreserve.gov/econres/notes/feds-notes/repo-markets-and-the-feds-balance-sheet-implications-for-monetary-policy-implementation-20260826.html).

Inspected full note, especially §2 Equation 1/Table 1 and §3 Figure 2. Daily September 2014–March 2026 sample: 2,902 observations. A regression of changes in TGCR minus IORB includes net bill/coupon issuance, dealer holdings, government-MMF assets and liquidity measures, with weekly clustered errors. Net coupons affect repo borrowing demand; bills can reduce MMFs' available repo lending. Issuance sensitivity is larger at lower liquidity levels. This is particularly relevant to H3.

The study interpolates weekly dealer/MMF values to daily observations. A Mastermind forecasting study must instead use actual release-aware step-held values. Its coefficients must not be pasted into a live forecast or treated as causal certainty. Reserve levels and actual repo funding capacity are related but distinct. The note also documents policy offsets, including bill purchases and standing repo operations; an unconditional “QT always active” assumption is invalid.

### S6 — Why reserves alone are insufficient

Anbil, Anderson, Cohen and Ruprecht, FEDS 2026-041, June 2026. [Paper](https://www.federalreserve.gov/econres/feds/files/2026041pap.pdf).

Inspected model motivation, §4 calibration and data descriptions. The structural model jointly treats bank reserve demand and nonbank funding supply. Calibration covers June 1, 2022–August 31, 2024, using seven targeted moments, with later-2024 checks. Government-MMF portfolio allocation and repo financing can constrain the balance-sheet size before minimum bank reserve demand binds. This is a model-based mechanism, not a universal measured reserve threshold. The authors exclude the 2025 debt-issuance-suspension period from calibration because it adds channels outside their model. Its historical calibrated thresholds should not become deterministic current risk cutoffs.

### S7 — A real stressed settlement episode, with confounds

Anbil, Anderson and Senyuz, FEDS Note, February 27, 2020. [Full note](https://www.federalreserve.gov/econres/notes/feds-notes/what-Happened-in-Money-Markets-in-September-2019-20200227.htm).

Inspected the full account. September 16, 2019 combined corporate taxes and $54 billion in long-term Treasury settlement; reserves fell about $120 billion over two business days. Dealer financing demand and reluctant/inelastic cash supply contributed to repo pressure, followed by Federal Reserve intervention. The episode demonstrates that an ordinary scheduled settlement can become consequential in a constrained system. It does not isolate an auction-only causal effect, establish a permanent reserve loss, or validate a pre-auction equity trade. Tax dates, pre-existing liquidity, funding-market structure and the policy response are essential parts of the case.

### S8 — Observed balance-sheet offsets

Federal Reserve, *Federal Reserve Balance Sheet Developments*, November 2023, Table 1 and “Changes in Federal Reserve Liabilities.” [Official report](https://www.federalreserve.gov/monetarypolicy/November-2023-Federal-Reserve-Balance-Sheet-Developments.htm).

Between March 29 and September 27, 2023, the report records TGA growth of $509 billion, ON RRP decline of $822 billion, and reserve decline of $233 billion while Fed assets also contracted. The report links ON RRP reductions to more attractive Treasury bills and private repo. These observations reject a one-for-one inference from TGA growth or gross issuance to reserve loss. They do not identify each auction's funding source. The required product output is a decomposed balance-sheet scenario plus later observed reconciliation, not a fabricated purchaser-channel allocation.

### S9 — Liquidity fragility and information shocks are distinct

Dobrev, Liu, Kim and Rodriguez, FEDS Note, November 3, 2025. [Full note](https://www.federalreserve.gov/econres/notes/feds-notes/order-flow-imbalances-and-amplification-of-price-movements-evidence-from-u-s-treasury-markets-20251103.html).

Inspected methods, event figures and conclusion. The note compares April 7 and April 9, 2025 tariff-news windows using five-minute volume, five-second yields and directional futures flow. Similar low depth and high volume coexist with different directional imbalances and price responses. April 9 includes an auction and subsequent tariff announcement, illustrating why daily auction attribution is unsafe. The authors describe an amplification interpretation; this is not a prospective auction indicator. Licensed intraday sources include LSEG/Datascope and Bloomberg. Daily total volume is not a substitute for directional order imbalance or order-book depth.

### S10 — Counterevidence about demand and the disappearance of daily rebounds

Somogyi, Wallen and Xu, HBS Working Paper 26-033, version December 2, 2025. [Paper](https://www.hbs.edu/ris/Publication%20Files/26-033_9bebc98f-09f9-4485-aae6-972388865b19.pdf).

Inspected §§2 and 3.1 plus the introduction/results discussion. The sample spans January 1992–April 2025; US auctions are at least five-year maturity and at least $500 million. Public bid-distribution points are used for an aggregate demand-elasticity approximation; Bloomberg/Refinitiv yields supply market outcomes. The study reports weaker demand elasticity and disappearance of average post-auction daily yield declines after 2010. This is compatible with S1's reduced temporary pressure: aggregate demand slope and intraday intermediation concessions are different objects. The normalization depends on outstanding debt in broad tenor buckets. Treat the measure as research context, not a directly observed investor demand curve or a replacement for H4 validation.

## 2. Internal results that remain binding constraints on promotion

These artifacts were read directly at the recovered source revisions; no underlying backtest was rerun.

| Artifact | Exact recovered anchor | Result to preserve |
|---|---|---|
| `macro/reports/slf006-auction-absorption-phase0.md` | Macro `eefddf818163c557c2c7aabba05f02a4325b34d2`; blob `530b1e7ad5d3a819ebda9d785e0ce16dc969855c` | 413 scored coupon auctions, 2016-12-13–2026-06-25. Composite demand score remains NULL/NO-GO. Corrected two-arm standard error leaves no contrast passing BH q≤0.10; split-half sign gate fails. |
| `macro/reports/d2-rates-calendar-flows-phase0.md` | Same Macro revision; blob `80d2dba31446eb633a503bff58cc61358cf0dc49` | 268 10Y/30Y auctions, 2016-06-22–2026-06-11. Auction-cycle V1 FAIL: conditional post-window TLT mean −0.011%, t≈−0.066; split halves reverse. Overall family “SCORED” comes from month-end V3, not V1. |
| `mastermind-terminal/docs/PHASE2_MARKET_RISK_GATE_VERDICT.md` | Terminal `d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a`; blob `d9e1a679f5fe0da715fabb56d4d7642329db7cd4` | Market-risk modulation of name exit warnings remains KILL/display-only. Confirm-in-stress deep-giveback rate 0.209 is below random-bar-in-stress 0.219. Same-regime base rates are the controlling comparator. |

The SLF report retains inaccurate “foreigners” shorthand in introductory prose and a generic 13:00 assumption. Its accepted outcome is a study of the implemented composite and ETF mapping, with stated limitations, rather than a clean null for every conceivable auction mechanism. Correcting bidder semantics does not by itself reopen alpha. The D2 report's conditional wiring language cannot override its explicit V1 failure.

## 3. Architecture consequences — research judgment

1. **Four causal stages need separate feature namespaces and output eligibility.** `announcement_revision` is not `auction_result`, and neither is `settlement_realization`. Record decision cutoff and each input's first lawful availability.
2. **Size changes need honest names.** A difference from the last auction is `offering_change`; a difference from a prior official plan is `official_plan_revision`; a difference from an independently recorded market expectation is `expectation_surprise`. A futures-price-derived announcement factor is an after-release inferred news measure. Only the last two can support a carefully defined surprise claim.
3. **Current official facts do not recreate old information sets.** Historical final results, final issue sizes or revised macro series can support retrospective descriptions; they do not prove a schedule was knowable at T-1.
4. **Keep gross duration and cash quantities separate.** Coupon DV01 can be useful event importance; bill notional can matter through funding without comparable duration. Net financing, TGA cash movements, reserve balance changes and repo capacity are different quantities.
5. **No inferred capacity precision.** Public lagged dealer positions and rates volatility are observable proxies. They do not reveal each dealer's remaining balance-sheet limit or same-day VaR headroom.
6. **Avoid post-treatment control errors.** H3's realized settlement-day TGA change can be a mediator. Putting it in a purported pre-settlement forecast leaks information; controlling for it in a total-effect causal regression can remove the mechanism being tested. Use prior known projections for forecasting and separate realized accounting/mediation analyses.
7. **The first predictive comparison must reuse Macro's actual contemporaneous baseline.** If it cannot be reconstructed, publish that limitation and use a separately labeled public-proxy baseline. A win against the proxy cannot establish incremental value over the existing Risk Radar.
8. **No universal cross-asset sign.** Do not assign bearish SPY arrows from larger supply or higher rate volatility. Forecast absolute volatility and signed downside separately. Context may show observed disagreement with duration, credit and equity behavior.
9. **No output promotion by convenience.** Importance ranks are deterministic relevance. Probability, expected drawdown, policy advice and any per-name exit modification require independent evidence/authority. Existing display-only paths are the appropriate first consumers.

## 4. Accounting check that should accompany the first funding vertical

Use the Fed balance-sheet identity as an accounting reconciliation, not as a predictive model:

`Δreserves = ΔFed_assets − ΔTGA − ΔON_RRP − Δother_liabilities − Δcapital`.

Separately reconcile Treasury cash:

`ΔTGA = receipts − outlays + net_cash_from_issuance/redemptions/buybacks + other_cash_items`, with the source convention explicit.

The exact production decomposition belongs to existing Treasury Watch/liquidity ownership. It must not mix face-value “new cash” with cash settlement proceeds, accrued interest and premiums without adjustment. If official net-private borrowing already includes a redemption or buyback component, do not subtract it again. Principal refinancing and budget interest payments are different ledger lines.

Suggested hand cases: equal issuance/refinancing principal with zero net cash; MMF reallocation from ON RRP into bills; deposit-funded purchase raising TGA; later Treasury expenditure; SOMA rollover versus runoff; buyback financed by replacement issuance. Specify these as scenarios when purchaser funding cannot be observed. The identity alone cannot identify private flows, a causal repo effect, or equity selling.

## 5. Research dispositions and first experiments

| Branch | Current disposition for Mastermind | First executable evidence target |
|---|---|---|
| H1 announcement news | `INSUFFICIENT_PIT` for market-expectation surprise; literature mechanism is retrospective | Pair original releases with earlier expectation/plan vintages. Record plan revision without calling it a surprise. Intraday reaction tests require licensed quotes. |
| H2 capacity-conditioned concession | `RETROSPECTIVE_ONLY` external evidence; no Mastermind pass | True-cutoff, own-tenor intraday test if feed exists. A separately named daily rates-volatility proxy may test a new burden×fragility hypothesis; it cannot reproduce intraday concession. |
| H3 settlement funding | `MEASURED_DESCRIPTIVE` external mechanism; local statistical verdict untested | Settlement-cohort net bill/coupon cash ledger, then release-aware TGCR/SOFR spread test against existing funding baseline. This is the strongest public-data first research vertical. |
| H4 results | Existing composite `NULL_NO_GO`; genuine WI-tail branch `INSUFFICIENT_PIT` until rights/quotes verified | Log actual result-known time, competitive allocations and bid dispersion as post-result context. Evaluate only future returns after an executable observation delay. |
| H5 equity hazard | `NOT_TESTED/INSUFFICIENT_PIT`; no cash-first implication | Freeze T-1 snapshots and baseline before prospective outcomes. Historical replay is explicitly retrospective; no warning modulation or numerical user probability yet. |

No new empirical outcome, calibrated probability, prospective pass, live data availability, new research schedule, or background process is claimed by this return. The strongest ready implementation contribution is a correctly dated funding-event dossier that remains useful under a null equity result.

## 6. Remaining concrete gaps

- Actual quote entitlements and historical intraday WI/futures availability are unverified here. The source agent and existing data owner must establish them; no paid acquisition is proposed.
- The Phillot main article remains access-limited, despite direct inspection of its current appendix and companion-paper methods. A lawful existing copy could close that precise gap without repeating broad research.
- The official source feasibility agent owns the real announcement/result/settlement casebook and current parser schema. This return does not duplicate that collector audit.
- A source-vintage census is needed before any date span earns PIT status. Null-study dates are not an eligibility manifest.
- No empirical harness was run. Implementation of the preregistration contract and an outcome-blind coverage audit are safe next steps for the parent after source custody is reconciled.
