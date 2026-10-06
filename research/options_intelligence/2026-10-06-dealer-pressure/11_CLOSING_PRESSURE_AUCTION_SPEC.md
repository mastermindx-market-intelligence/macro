# Closing pressure and auction intelligence specification

**Evidence cut: 2026-10-06. Research architecture; no auction feed, forecast model or trading policy was deployed.** Auction regimes are venue-, calendar- and implementation-version-specific. All source IDs resolve in SOURCE_REGISTER.md.

## 1. What this changes for Mastermind

Closing pressure should become a family of venue-aware, timestamped research outputs. A single universal “15:50 MOC signal” would misclassify the information available for SPY, Nasdaq names and NYSE names. An imbalance is also a current auction-book state: it does not identify the ultimate investor, imply dealer inventory, or guarantee a profitable directional trade.

The strongest newly identified participant-data candidate is Cboe Open-Close. Its market-maker buy and sell contract volumes can measure signed net transactions for the covered exchange and contract. This materially reduces one uncertainty in public trade-based inference. It still leaves initial inventory, other venues and instruments, transfers, exercise/assignment and actual hedge execution unresolved. A bounded C1 ten-minute pilot has a more plausible cost/information tradeoff than immediately buying the one-minute product.

The existing integration boundaries remain valuable. Commission 15 establishes Theta as the options collector, the Terminal Quote Plane as the equity-quote owner, Macro as the intelligence owner and Radar as the lifecycle/evaluator owner. The T2a bulk path currently aggregates and discards raw option rows; a parser containing fields does not establish an atomic archive. SnapshotGreek prices are expressly not live executable NBBO. The August darkpool audit removed accumulation/distribution inference, and its unsigned volume labels should remain context. These conclusions come from the supplied repository evidence, not a new runtime test.

The source corpus consumed before this research was:

- The commission attachment, Pasted text(1).txt.
- COMMISSION_15_HARDENED_REPORT.md, CURRENT_STATE_AND_HARDENING_LOG.md and VALIDATION_PROTOCOL.md.
- DARKPOOL_DESK_AUDIT_AND_UPGRADE_2026-08-05.md.
- Relevant trade_quote, bulk, quote, snapshot and OI sections of collectors/thetadata.py.

The Macro reference pin is c9631f8b2469587dec643bec94b16e77c09ef511; the procedure reference is Mastermind a6d40ff648671b03bd4d829d84dd066b58ea8c3f. The existing sealed PSS-AF1 evaluation is not evidence of intraday auction performance or current feed health.

## 2. Exchange clocks: model a phase, not a wall-clock constant

Use the primary listing/official closing-auction venue valid on that date, the exchange calendar and America/New_York. Maintain scheduled close and actual security-specific auction completion separately. “16:00 close” does not guarantee every auction print arrives at precisely that instant.

| Venue and event | Normal 16:00 equity close | Scheduled 13:00 equity close | Information or restriction |
|---|---:|---:|---|
| NYSE regular public closing imbalance | 15:50 onward | 12:50 onward | Changed fields at up to one-second cadence, through security close |
| NYSE ordinary MOC/LOC admission freeze | 15:50 | 12:50 | Later MOC/LOC requires a qualifying published opposite-side Significant Closing Imbalance |
| NYSE D-order entry/change deadline, currently documented operational regime | 15:59:50 | 12:59:50 | Proposed earlier change/cancel cutoff needs a separate deployment flag |
| Nasdaq early imbalance, EOII | 15:50 | 12:50 | Every ten seconds; reduced field set |
| Nasdaq full NOII and MOC entry cutoff | 15:55 | 12:55 | Full one-second information; late LOC rules continue |
| Nasdaq LOC admission cutoff | 15:58 | 12:58 | Restricted pricing after full-NOII phase begins |
| NYSE Arca closing imbalance | 15:00 | 12:00 | Public auction state already exists an hour before close |
| NYSE Arca closing freeze | 15:59 | 12:59 | Different phase from NYSE's ten-minute freeze |

Sources: NYSE overview and early-close specifications [A01] [A11], NYSE regulatory memorandum [A06], Nasdaq Rule 4754 [A13]. Early Nasdaq values express the rule's close-relative schedule, not a claim that this project has captured early-close messages. The 2026 NYSE calendar lists 13:00 equity closes on November 27 and December 24; eligible options can have a different 13:15 endpoint [A12].

This matters directly to the initial universe: SPY's issuer identifies NYSE Arca as its listing exchange [A44]. A SPY forecast at 15:30 is after routine Arca imbalance publication has begun. A Nasdaq stock at 15:52 is in the early-information phase, while a NYSE stock at that moment is already in its normal closing-imbalance phase. All three can coexist in an S&P-weighted basket; averaging them without phase labels hides material differences.

### NYSE: the late book is mutable, and its imbalance types differ

The normal freeze does not freeze every form of eligible liquidity. Closing IO orders may still enter on either side; qualifying contra-significant MOC/LOC can enter; floor-broker D orders can change the late state. The NYSE fact sheet explains the distinct auction-only order types and their allocation role [A02]. D orders are agency orders with price discretion, not an identifier for market-maker hedging [A03].

The latest retrieved NYSE regulatory memo is particularly useful. It prohibits MOC/LOC/Closing IO cancellation or reduction after the freeze even for legitimate error. Only the stated limited Trading Official relief route can suspend the MOC/LOC prohibition. It also documents approved manual imbalance publications before routine dissemination and information available to floor brokers from 14:00. An erroneously published imbalance should be corrected promptly [A06]. A parser should therefore preserve original and correcting observations rather than overwrite them.

Do not interchange these quantities:

- **Total imbalance:** the current eligible auction interest at the relevant reference price.
- **Closing imbalance / Significant Closing Imbalance:** a separately defined measure and publication whose qualifying side governs some late order entry.
- **Paired quantity:** shares that can match at the stated reference, not total daily volume.
- **Unpaired quantity and clearing prices:** additional state variables with their own definitions.
- **Actual auction execution:** realized volume and price, potentially different from any earlier indicative state.

NYSE changed the D-order inclusion time in disseminated total imbalance from 15:55 to 15:50 effective August 12, 2024 [A04]. Its significant-imbalance threshold changed October 28, 2024: the size hurdle depends on 20-day average closing volume and index grouping, with an additional $200,000 notional hurdle. The percentages are 30% for S&P 500, 50% for S&P 400/600 and 70% otherwise [A05]. Historical replay must use historical membership and the applicable rule; a fixed 50,000-share rule is no longer an adequate current classifier.

### A 2026 NYSE filing must not be mistaken for a deployed regime

SR-NYSE-2026-36 was filed July 31 and published in the Federal Register August 18, 2026. It broadens the defined Closing Imbalance to include Closing IO and, near the close, D orders. It also moves D-order cancellation/modification rejection to one minute before close while leaving entry rejection ten seconds before close. The filing describes implementation through a future Trader Update, anticipated by Q1 2027. Immediate legal effectiveness therefore does not establish the live technology date. No operative rollout notice was verified in this lane [A07].

Maintain a pending regime entry and require the actual implementation receipt before activation. This is distinct from the D-order inclusion in total imbalance already implemented in 2024. Otherwise a research system could silently apply a new cancellation rule to historical or current observations under the old behavior.

### Nasdaq: 15:50 is early NOII, not full NOII

Nasdaq introduced the earlier information window effective November 4, 2019. Its implementation notice specifies paired shares, imbalance shares/direction and current reference price during 15:50–15:55; near and far indicative prices are zero in that phase. Frequency changes from ten seconds to one second at 15:55 [A15]. Treat those early zero prices as unavailable by design, not genuine zero-dollar prices or a quality failure.

Current Rule 4754 also distinguishes free cancellation before 15:50, a legitimate-error exception request through 15:58 and the late LOC pricing/admission restrictions. MOC entry ends at 15:55 and LOC at 15:58; IO has a separate offsetting role. Full near/far prices compare different eligible interest sets [A13]. Applying NYSE cancellation exceptions or freeze semantics to Nasdaq would be wrong.

ITCH provides imbalance, cross-trade and broken-trade message types. Its stock mapping and timestamp encoding should be retained alongside auction fields [A16]. A normal cross, halted-security process and subsequent extended-close trading are separate event classes. For research targets, use the primary official cross where one occurred; label fallback official closes and no-auction cases distinctly.

## 3. Early MOC is legitimate in some channels, but not yet a usable historical panel

“Before publication” must name the channel. The current NYSE functional specification distinguishes regular XDP dissemination from floor-broker information [A08]. An exchange can make information available through a broker channel before the routine public feed starts. Separately, a public manual imbalance can appear early for an individual security [A06]. Either circumstance changes what was actually known.

AmerX advertises a market-on-close portal with early information from 14:00 and subsequent updates. This is credible evidence that an early broker product exists, not evidence that Mastermind can currently access or backtest it. The site describes broker-mediated information and selection features. It does not establish an API, a complete retained universe, capture timestamps, revisions, machine rights, price, or historical availability [A19].

MrTopStep's current Market Imbalance Meter catalog describes the last ten minutes of NYSE auction information, with $75 monthly, $175 quarterly and $500 yearly consumer pricing. That current catalog does not substantiate older anecdotes of a presently licensable 14:00 feed or machine-use permission [A20]. A FinancialJuice historical “early MOC” headline establishes an individual published example, but cannot supply a defensible panel, exact availability clock or commercial license [A21].

A future early-product qualification should demand a dated sample showing every published record, original publication and receipt timestamps, selected-universe rules, corrections, missing records and archive version. Its incremental value is the gain over whatever public/manual information was already available at each observation. Hand-picked screenshots, a recent headline and reconstructed later totals cannot answer that question.

## 4. Four research targets with different admissible evidence

1. **Forecast before routine public imbalance.** Predict later imbalance, matched volume or closing-price displacement using only already available market, event and reference data. Flag any manual publication or licensed early observation rather than pretending the information set is empty.
2. **Forecast conditional on an early channel.** Estimate the residual change from the early observation to the later state. Compare against that early observation and a simple persistence baseline. This target is only feasible after rights and a point-in-time archive are proven.
3. **Auction nowcast after publication.** Estimate the actual cross and subsequent imbalance evolution using the live indicative state, allowed late order behavior, reference-price movement and continuous liquidity.
4. **Executable return prediction.** Distinguish continuous-market decision-to-cross, cross-to-post-close and cross-to-next-open returns. An accurate auction imbalance forecast can coexist with unprofitable returns after price adaptation, spreads, latency and fees.

A primary-auction dollar imbalance can be expressed as signed shares times its own reference price. Normalize it by historically available closing volume, forecast close liquidity or basket risk; do not compare raw shares across differently priced stocks. A broad index aggregation needs point-in-time weights, symbol mappings, a stated missing-constituent denominator and venue phases. Avoid counting ETF share imbalances and the entire underlying basket as independent demand without an overlap model.

For LOD/HOD integration, auction information is a conditional state variable. It cannot establish that a future high or low has already occurred. Research should estimate probability of a subsequent extremum and continuation/reversal distributions, with horizon and session cutoff explicit. Ex post “day high held” labels remain outcomes, not streaming features.

The correct baseline hierarchy is simple: time-of-day/volatility, price/volume and continuous quotes, public auction state, options-pressure proxy, then incremental participant/early-channel information. Test the improvement at the same decision time and latency. The comparison against no-information or yesterday's close alone would exaggerate usefulness.

## 5. Wire fields and known-at clocks

Store a shared event envelope before constructing features:

| Component | Required treatment |
|---|---|
| Identity | Canonical instrument, raw symbol, primary venue, source venue, auction type, trade date, session/segment and mapping version |
| Source clock | Preserve its stated semantics and native precision |
| Publication/capture clock | Keep exchange/vendor dissemination or capture time separately where supplied |
| Own receipt clock | Record local arrival and sequencing; this establishes what this system could have known |
| Availability clock | Latest required input's actual known time, plus processing lag |
| Version | Schema, effective rule regime, data-vintage ID, correction state and contract terms |
| Completeness | Gaps, reconnects, unavailable fields, absent snapshots and expected no-change behavior |
| Outcome | Auction print, official fallback close, later corrected close and evaluation-vintage policy |

NYSE Message 105 carries source seconds and nanoseconds, symbol sequence, reference price, paired and imbalance quantities, side, auction type and additional clearing/status fields. Several fields, including indicative-match price and collars, are supported on some NYSE Group venues but not NYSE itself. Messages are generated up to once a second when calculated fields change [A10]. Absence of a fresh record alone therefore cannot distinguish stable state from a broken channel; sequence/heartbeat and channel health are necessary.

The technical-document catalog separately labels current and upcoming versions. At the research cut it lists current imbalance v2.2n while another Q4 2026 version is upcoming; Open-Close also has a future specification alongside the current one [A09]. Freeze schemas and algorithm versions per observation. Do not build to an upcoming document simply because a generic URL returns a newer PDF.

The NYSE functional document describes repeated and corrected official-close dissemination after a security closes [A08]. Preserve the first decision-available observation and the eventual corrected truth. A late correction is useful for final outcome quality but must not repair a historical feature silently. A book cleared at session end should not erase the final pre-close reference quote from the research record.

## 6. ETF, index and off-exchange evidence

ETF basket data measures a portfolio specification, not an executed hedge. DTCC's ETF Portfolio Data Service supplies daily and supplemental reference content [A42]; its processing documentation places important files on prior-evening and update cycles [A43]. A current holdings download can differ from the creation basket and from what a participant used earlier. Version every portfolio before estimating an expected basket.

Daily issuer NAV and shares outstanding can support a net primary-flow proxy, such as change in shares times an appropriately dated NAV. That estimate does not reveal simultaneous gross creations and redemptions, the AP's inventory or intraday hedging decisions. SPY's issuer supplies dated daily observations [A44]. NYSE's EOD ETP report supplies market prices, volumes and close-quote references, not primary-market flow records [A48].

Index rebalances create dated expected demand scenarios, but announced weights and fund-tracking assumptions must be separated from executed orders. FTSE Russell's 2026 schedule changes the process to semiannual reconstitution. The June sequence separates April 30 ranking, May 22 initial lists after 18:00 ET, later revisions, June 26 after-close implementation and June 29 open effectiveness [A45]. Use original announcement versions; a final constituent file backfilled onto rank day leaks later decisions. Do not generalize this schedule to other index providers or infer December dates from a third-Friday rule.

FINRA ATS/non-ATS aggregates observe reported shares/trades and facility/member concentration [A46]. Rule 6110 delays Tier 1 weekly publications by at least two weeks and Tier 2 by at least four; low-activity non-ATS participants can be aggregated [A47]. Those reports are unsuitable as live directional dealer-flow evidence. Reporting venue is not beneficial owner or investor capacity, and a TRF print is not automatically a dark-pool execution. Preserve the existing unsigned context language and actual release dates.

### Index-family schedules need separate records

| Family | Current primary source | Evidence and integration consequence |
|---|---|---|
| MSCI | August 12, 2026 review-date release [A59] | November review announcement November 11, 2026; effective December 1. Preserve the announced effective date and exchange-specific preceding implementation close; obtain the actual change files. |
| S&P | July 2026 U.S. Indices methodology [A60] | S&P 1500 composition changes occur as needed, without a scheduled reconstitution. Additions/deletions generally receive at least three business days' notice, with discretion for less. Quarterly share updates and other index-family weight resets are different events. |
| S&P share/IWF cycle | August 2026 Equity Policies [A61] | Quarterly references precede implementation; float-cap pro-formas generally arrive two weeks before effectiveness and capped/alternative-weight pro-formas one week before. Freeze and mandatory-action exceptions require original file versions. |
| Nasdaq-100 | Current methodology calendar, page 8 [A62] | Annual December reconstitution and quarterly rebalancing; reference dates, announcement after the sixth preceding trading day's close, and effective open after the relevant third Friday are distinct. Special rebalances and Fast Entry add off-calendar events. |

Nasdaq's March 30, 2026 official announcement makes the updated methodology effective May 1, with the former method through April 30 [A63]. A current Nasdaq rule PDF cannot safely generate earlier historical constituent changes. The listed public methodology sources do not grant historical-weight or pro-forma redistribution rights.

### A concrete pre-publication demand model

Use separate explanatory components and preserve the assumptions of each. This is a proposed model structure, not a claim that all components are currently observable.

**Passive rebalance demand.** For fund/index family f, start with estimated tracking assets and the difference between announced target weight and the old portfolio's price-drifted weight:

\[
\widehat D_i^{passive}
=
\sum_f \widehat A_f
\left(w^{new}_{if}-w^{drift}_{if}\right).
\]

Divide by price for shares, then apply scenario ranges for cash versus derivative implementation, participation at the close, anticipated execution already completed, and tracking behavior. Membership, AUM, shares, float and price inputs must each be dated. Assets “benchmarked to” an index are not all mechanically indexed assets. Overlapping funds and derivatives must not inflate the sum.

**ETF creation/redemption scenarios.** Use the dated creation basket and a range for net primary activity. Separate executed observations, issuer daily net-share changes and modeled same-day activity. Cash substitutions, in-kind transfers, inventory netting and prehedging make basket notional an imperfect estimate of same-time market demand. Treat overlap with passive rebalance estimates explicitly.

**Pension allocation scenarios.** Given an assumed initial equity/bond allocation and relative returns, calculate the trades needed to restore target weights under stated assets and rebalance participation. Even the simple two-asset, no-flow approximation produces a range, not an observed MOC order. Contributions, liabilities, discretionary bands and derivative use can alter size and timing. Report a scenario stress variable unless actual legally obtained instructions exist.

**VWAP/POV residual scenarios.** A known authorized parent-order record can establish remaining quantity and schedule. Public volume alone cannot identify all institutions' parent orders, original targets or completed quantities. With public data, estimate a distribution of possible residual execution using a historical intraday volume curve and participation assumptions; never label it observed unfinished institutional demand.

**Symbol-specific closing history.** Use point-in-time rolling auction volume, close share of daily volume, price dislocation, early-to-final imbalance transitions, volatility and event flags. Estimate ordinary-day, expiration, index and month-end regimes separately with shrinkage for sparse samples. This baseline provides the denominator and uncertainty against which other demand scenarios must add information.

The system should retain component ranges and correlation/overlap assumptions rather than add every headline dollar estimate as independent demand. Forecast later auction state and executable response separately, and compare the combined estimate against the public auction state once it becomes available.

## 7. Original model specification: forecast before disclosure

Use one security's primary auction as the measurement unit. Proposed response variables are final signed auction imbalance where defined, actual paired/executed quantity, auction price relative to the decision-time eligible midpoint, and close-to-next-open reversal. They are different targets. A final auction imbalance can mechanically disappear when the book clears; retain the correct final pre-cross field, not an empty post-cross book.

Start with a robust, shrinkage-based symbol × venue × time-of-day model. Covariates are already-known event demand scenarios, float/ADV and historical auction participation; current price/volume/volatility/basis; sector-synchronized residual flow; options expiry and exact remaining hedge scenarios; and source-qualified early indications if actually available. Each event component includes an uncertainty range and whether it overlaps another component.

Use distributional regression or quantile models for signed shares and price displacement, with asymmetric/heavy-tail errors. Compare an interpretable regularized model with shallow trees under the same study budget. Do not fit a high-dimensional model per symbol with only a handful of rebalances.

A simple two-asset pension scenario illustrates the accounting. With initial wealth A, target equity fraction w, equity return r_e and bond return r_b, post-return equity is A w(1+r_e), total wealth is A[w(1+r_e)+(1-w)(1+r_b)], and target-restoration equity trading is their difference:

\[
D^{pension}_{equity}=A\,w(1-w)(r_b-r_e).
\]

This is a scenario identity with no contributions, withdrawals, leverage or allocation bands. Unknown A, policy participation, futures use and close execution require ranges. It is not a measured pension MOC order.

Public VWAP/POV residual estimates likewise remain scenarios. Only an authorized actual parent-order record establishes a specific remaining quantity. The model may learn associations in synchronized sector flow, but cannot label its residual “genuine discretionary institutional selling.”

## 8. Original model specification: nowcast after disclosure

At each eligible official message, forecast the distribution of auction-price displacement from the current tradable reference:

\[
p\!\left(r^{auction}_{t:C}\mid
 I_t,P_t^{paired},p_t^{indicative},p_t^{near},p_t^{far},
 \Delta I_t,\Delta P_t^{paired},\text{phase},\text{liquidity},
 \text{event state},\text{dealer scenarios}\right).
\]

Use fields only where the venue and phase define them. NYSE, Arca and Nasdaq require separate observation adapters. Missing or early-phase zero prices do not enter a regression as genuine observations. A change in imbalance can reflect a changed reference price admitting different orders; it is not necessarily newly submitted net shares. Add reference-price change and eligible field state when evaluating imbalance velocity.

Mandatory nowcast baselines are current indicative-price persistence where valid, current signed imbalance normalized by historical auction volume, and a venue/phase historical elasticity model. Add paired growth, near/far differences, allowed late-order changes and continuous liquidity next. Add dealer-pressure features only after those baselines; otherwise an options model can take credit for official auction information.

A dynamic latent-order model is a later challenger: latent demand can evolve with arrivals, cancellations, discretion and strategic order migration, while observed messages are a venue-specific function of that demand and the reference price. Its observation equation must reproduce the exchange's eligible-interest definitions. A generic random walk in reported imbalance is only a statistical baseline, not a recovered order book.

## 9. EOD attractors and cross-product integration

Compute remaining options target-demand scenarios under the same inventory and surface conventions as report07. A zero of a remaining-runoff field is a **conditional zero-demand root**. It becomes an attractor candidate only if expected subsequent execution points inward on both sides, liquidity is material and the root remains stable under credible scenarios. A charm-weighted strike or maximum gross gamma alone does not meet that definition.

The predicted close region should ultimately come from a calibrated distribution combining price/liquidity history, venue-specific auction state and options information. A mechanism root can be a covariate or candidate bin boundary; it is not automatically the forecast mode or a guaranteed equilibrium. An auction can overwhelm continuous-market damping, and a dealer book may hedge in ES while the final price is set in constituent share auctions.

SPX has no single executable SPX closing auction. A constituent aggregation needs causal membership/weights, official calculation rules and divisor/reference state, primary venues and a missing-constituent denominator. An index-weighted pressure proxy is not identical to the official SPX close or to SPY's Arca cross. Retain index, ETF and futures close targets separately; a 16:00 ES mark is not CME settlement.

## 10. Exact study and failure policy

Freeze prediction snapshots before each phase boundary and at a prespecified post-publication cadence. Store the first available version and corrections, actual dissemination/receipt times, source health, reference-price state, model completion and consumer availability. Construct labels only after the actual cross and the relevant reversal horizon mature.

Evaluate pre-public demand error, directional bias and interval coverage; close-distribution CRPS/quantile loss; properly normalized impact error; next-day continuation/reversal; and incremental decision outcomes after executable costs. Compare identical symbols, phases, horizons and information sets. Ordinary days, early closes, rebalances, OPEX, halts/no-auction and rule-version transitions are declared strata.

Historical final NOII/Pillar files without original vintages can support a receivability sensitivity study, not captured-live proof. An early product needs a complete original archive before any accuracy claim. If options adds nothing after public auction and liquidity inputs at adequate power, retain the simpler auction model. If accurate imbalance forecasts do not improve executable returns or existing-candidate outcomes, retain them as context only.

The adjacent auction experiment can proceed independently after source qualification; it is not a prerequisite for the first inventory-information test. It uses the existing Data OS, quote, publication and evaluation owners described in report18.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[A01]: https://www.nyse.com/trade/auctions
[A02]: https://www.nyse.com/publicdocs/nyse/markets/nyse/NYSE_Opening_and_Closing_Auctions_Fact_Sheet.pdf
[A03]: https://www.nyse.com/trade/d-orders
[A04]: https://www.nyse.com/data-insights/nyse-closing-auction-price-discovery-opportunities-reach-new-highs
[A05]: https://www.nyse.com/data-insights/the-nyse-significant-imbalance-enhanced-trading-opportunities-at-the-nyse-closing-auction
[A06]: https://www.nyse.com/publicdocs/nyse/markets/nyse/rule-interpretations/2026/Q1_2026_Quarterly_Expiration_RM_3.20.2026.pdf
[A07]: https://www.govinfo.gov/content/pkg/FR-2026-08-18/pdf/2026-16783.pdf
[A08]: https://www.nyse.com/publicdocs/nyse/markets/nyse/Functional_Differences_NYSE_Pillar.pdf
[A09]: https://www.nyse.com/market-data/technical-documents
[A10]: https://www.ice.com/publicdocs/nyse/data/NYSE_Pillar_Order_Imbalances_Client_Specification_v2.2n.pdf
[A11]: https://www.nyse.com/publicdocs/nyse/data/NYSE_Pillar_Depth_Client_Specification_v1.4.pdf
[A12]: https://www.nyse.com/trade/hours-calendars
[A13]: https://listingcenter.nasdaq.com/rulebook/nasdaq/rules/nasdaq-equity-4
[A15]: https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2019-66
[A16]: https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf
[A19]: https://www.amerx.com/market-on-close-portal
[A20]: https://mrtopstep.com/catalog/market-imbalance-meter
[A21]: https://www.financialjuice.com/News/7218281/1-Early-MOC-imbalance-528-mln-sell-side.aspx?xy=rss
[A42]: https://www.dtcc.com/products-and-services/data-services/corporate-actions-reference-data/etf-portfolio-data-service
[A43]: https://dtcclearning.com/products-and-services/equities-clearing/etf-processing/etf-timeline.html
[A44]: https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-500-etf-trust-spy
[A45]: https://www.lseg.com/en/media-centre/press-releases/ftse-russell/2026/russell-reconstitution-2026-schedule
[A46]: https://www.finra.org/filing-reporting/otc-transparency
[A47]: https://www.finra.org/rules-guidance/rulebooks/finra-rules/6110
[A48]: https://www.nyse.com/publicdocs/nyse/data/NYSE_Arca_EOD_ETF_Report_Product_Spec.pdf
[A59]: https://www.msci.com/eqb/pressreleases/archive/ir_dates.pdf
[A60]: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf
[A61]: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-equity-indices-policies-practices.pdf
[A62]: https://indexes.nasdaq.com/docs/Methodology_NDX.pdf
[A63]: https://ir.nasdaq.com/news-releases/news-release-details/nasdaq-concludes-public-consultation-nasdaq-100-indexr
