# Data source, cost, rights and availability matrix

**Evidence cut: 2026-10-06. Catalog capabilities are not current account entitlement or runtime acceptance. No purchases or vendor contacts occurred.** The companion CSV records every product separately; alternate suppliers are candidates under incumbent owners, not a recommendation for duplicate feeds. All source IDs resolve in SOURCE_REGISTER.md.

## 1. Participant data: the most useful bounded extension

### Cboe Open-Close: what can be observed

Cboe's public catalog offers exchange-specific EOD, ten-minute and one-minute Open-Close files. C1 history is advertised from January 2005 for EOD, January 2011 for ten-minute and October 7, 2019 for one-minute; C2/BZX/EDGX histories differ. Intraday files arrive after interval end, rather than being tick feeds [A29].

The ten-minute specification classifies transactions by participant capacity. For market makers it supplies buy and sell quantities, not separate opening and closing buckets. The suffix “vol” means contracts, while “qty” means number of trades. Files are cumulative within the applicable day/segment, so successive files need differencing and revision reconciliation [A30].

For contract i and a consistent covered segment, the net transaction increment is:

\[
\Delta I^{MM}_{i,k}
=
\big(B^{cum}_{i,k}-B^{cum}_{i,k-1}\big)
-
\big(S^{cum}_{i,k}-S^{cum}_{i,k-1}\big).
\]

Opening/closing status is unnecessary for this net signed transaction increment. Buying increases a participant's signed position whether it opens a long or closes a short. Selling decreases it whether it closes a long or opens a short. That algebra does not turn transaction flow into an observed absolute starting position. Reconstruction from contract inception additionally requires complete covered history and treatment of expiry, exercise/assignment, transfers and adjustments.

This suggests three graduated uses:

- **Signing audit:** compare quote-based public trade inference with venue/capacity net transactions.
- **Inventory-change feature:** estimate covered market-maker net delta/gamma change at the time the file is actually received.
- **Model comparison:** ask whether this label source improves held-out prediction or calibration over public-only proxies.

C1 coverage may be especially informative for its index-option franchise, but a C1 market-maker category is not every dealer, all venues, every listed/OTC product or a record of hedge trades. The identifier is capacity, not a named consolidated institution. A future SPX result must remain labeled with those coverage bounds.

### Why ten-minute can be preferable to one-minute for the first study

As currently documented, one-minute files do not apply subsequent bust/cancel corrections; the ten-minute product handles such corrections differently. High-volume processing can also delay files, and some session-transition records carry forward a cumulative state rather than new activity [A31]. The catalog announces changes on November 8, 2026, including one-minute correction/schema changes [A29]. That date is future at this research cut, so pre- and post-change samples must be distinct.

The initial sensible test is a small C1 ten-minute history with a realistic delayed release assumption, followed by an actual-arrival shadow capture if licensed. Evaluate 15/30-minute horizons and broader intraday state, including whether the observed flow changes improve the public proxy. This does not support an asserted fine-grained final-minute advantage. Historical final files can train or audit labels, but their information cannot enter a feature until its actual availability.

C1's October 1 fee schedule lists EOD at $600/month, ten-minute at $3,000/month and one-minute at $12,000/month. Historical ten-minute data is $1,000 per requested month; recent one-minute history is $4,000 per month, older history $2,500. External derived distribution adds separate charges. The schedule also advertises eligibility-limited samples, which have not been requested [A33]. BZX has different published rates [A34]. This is a reason to measure marginal information on a bounded sample, not a request to spend.

### Other participant-labeled candidates

Cboe's enhanced C1 trade-by-trade execution detail advertises execution/capacity/side, NBBO/local BBO and complex-trade context, with history from October 7, 2019 and next-day availability. It is an attractive label/audit candidate, not evidence of a live participant feed [A35]. Its position-type field must be checked for per-capacity applicability before interpreting it as MM opening/closing truth.

NYSE's current Open-Close specification describes Arca/American EOD and ten-minute histories, cumulative capacity fields and MM buy/sell aggregation. EOD/FINAL availability is around the following morning; intraday publication examples contain a timing inconsistency [A36]. Marketing also advertises one-minute data [A37]. Treat one-minute deployment, actual history and release latency as unresolved until a dated sample and current contract establish them.

## 2. Options, equity quotes, futures and Greeks: qualification before sophistication

Theta remains the first option-source candidate because it is already the designated owner. Its historical trade_quote endpoint attaches the preceding NBBO to each trade and exposes separate trade/quote fields with an exclusivity setting [A23]. This supports a trade-signing model, subject to stale, crossed, locked, complex and condition filters. It does not reveal all intervening quote updates. Continuous queue/liquidity measures need an event quote source; Theta's quote endpoint distinguishes tick output from sampled interval output [A27].

The current all-Greeks documentation creates a material final-hour qualification issue: version 1 uses a fixed 0.15-day maturity assumption, while “latest” uses actual time with a minimum one hour. Its overview and one IV-field description also differ on midpoint versus trade-price language [A28]. Do not use those fields as unqualified true-expiry charm/gamma inputs in the final hour. Preserve method/version and compare with a documented independent expiry clock and model, including settlement, rate/dividend and quote inputs. This is a method check, not evidence that all vendor Greeks are unusable.

OI is a prior-session end-of-day position count, normally disseminated the next morning around 06:30 ET [A24]. Record both its economic date and publication/receipt date. Avoid a blanket extra day shift that makes a correctly released prior-EOD observation two days old. Conversely, a file indexed by trade date must not enter a previous afternoon's feature.

Theta's commercial catalog currently lists Options $1,600/month, Stocks $1,200 and Indices $400, with conditional startup offers. It distinguishes real-time Nasdaq Basic stock coverage from delayed CTA/UTP data [A22]. Nasdaq Basic is not a current consolidated equity NBBO. Existing collector ownership and a July entitlement observation are not an account-level October receipt.

Databento provides useful reference alternatives. For OPRA, event time is consolidator processing and receive time is its capture clock; trades have no disseminated aggressor side. Before March 28, 2023 its options quote history is subsampled, with one-minute maximum BBO granularity and receive timestamps actually replaced by event timestamps and flagged [A56]. That history cannot support a continuous quote-event study or reconstruct historical delivery latency.

For ES/NQ futures and options, the GLBX source documents engine, capture and sending-time fields, legacy history and book-event completion semantics. Implied orders and spreads require care; preliminary/final OI can be published on different dates [A40]. Use contract-specific multipliers, expiry/settlement calendars and roll mapping. A price-continuous back-adjusted future is unsuitable as the identity of an actual inventory or depth record. CME DataMine is another official historical route, with price/coverage still to be qualified [A58].

The fee distinction is material. CME's June 2026 list includes datafeed and research/principal non-display charges separately [A38]. Databento's current CME plans range from a $199/month Standard personal product to $1,750 Plus and $4,500 Unlimited, with different history and licensing conditions [A41]. OPRA also separately prices non-display analysis [A26]. A cheap display subscription is not evidence of enterprise model use. Theta's agreement [A25] and CME's policy catalog [A39] require actual use/retention/derived-output terms to be resolved in the acquisition record.

## 3. Acquisition sequence and unresolved evidence

The sequence below is a research recommendation, not approval to subscribe. After shared source, owner, rights and clock qualification, the participant-information pilot and venue-specific auction study are independent branches. Auction-feed acquisition is not a prerequisite for the first SPX/SPXW-to-ES inventory experiment.

**First, resolve what the existing owners actually retain.** Obtain a dated inventory of raw trade/quote events, source/receipt clocks, corrections, symbol/contract definitions, session coverage and executed rights. Prove the supplied OI's economic/available dates and Greek methodology. An atomic capture/known-at deficiency can invalidate a sophisticated signal before model choice matters.

**Independent auction branch: secure venue-correct labels and public states.** Qualify a licensed NYSE/Arca imbalance and Nasdaq NOII historical source, including data regimes and actual-close messages. Begin with a small representative sample containing ordinary sessions, early closes, expiration, rebalance, halt/no-auction and correction events. Commercial rights, historical completeness and final file vintages remain open.

**Priority inventory branch: test the marginal value of participant labels.** Prefer a bounded C1 ten-minute sample for the SPX-oriented hypothesis and compare public-only with capacity-observed increments. Add other venues/products only if out-of-sample improvement warrants the incremental cost. Use one-minute or trade-by-trade labels when a concrete remaining uncertainty requires them.

**Later extensions: add cross-product and event context.** Add ES/NQ event books and options with explicit contract mapping, point-in-time basket/rebalance files and clearly delayed off-exchange context. Early broker MOC merits a separate test only after a complete licensed panel and real availability clocks exist.

| Unknown | Concrete receipt that resolves it | Consequence while unresolved |
|---|---|---|
| Current internal machine/derived/retention rights | Executed agreement/exchange classification covering the exact owner, use and outputs | Product marked catalog-only or entitlement-unverified |
| Theta raw event retention and clock completeness | Representative immutable event sample plus collector/retention manifest | No claim of continuous-flow reconstruction |
| Final-hour Greek model behavior | Versioned endpoint sample and independent documented maturity/input comparison | Exclude unqualified true-expiry derivative features |
| Cboe release lag and correction chronology | Original interval files, listing/publication times, own receipt times and subsequent revisions | Coarser horizon; conservative availability; no final-minute claim |
| Cboe absolute starting inventory | Complete contract-inception coverage and inventory adjustment treatment | Report net transactions/partial reconstruction with initial-state uncertainty |
| NYSE 2026-36 deployment | Dated Trader Update and matching production sample | Maintain old and pending regimes separately |
| NYSE one-minute Open-Close | Current spec, entitlement, sample and history manifest | No assumed current one-minute capability |
| Early MOC archive quality | All-record channel sample with universe, timestamps, corrections and rights | Candidate only; no backtest assertion |
| Auction archive coverage and stale/gap logic | Venue-specific event manifest, heartbeats/sequences and corrections | Missing/unknown state rather than fabricated zero imbalance |
| ETF executed primary flow/AP inventory | Legally obtained transactions with actual availability | Basket/net-share scenarios only |
| Nasdaq/NYSE historical all-in cost | Exact vendor/archive quote plus exchange/internal-use classification | Price unknown; no invented budget |
| Empirical usefulness | Locked chronological held-out comparison with simple baselines and costs | Mechanism plausible; incremental alpha unproven |

For promotion, require complete event identity and known-at reconstruction first, then an incremental result at the intended horizon that survives matched baselines, regime/venue splits, reasonable latency/cost assumptions and uncertainty calibration. Stop expanding a scoped source/model family when adequate coverage and power rule out its preregistered useful gain. An imprecise null is inconclusive. The useful end state is an auditable pressure estimate with coverage and uncertainty, not an asserted universal dealer-position oracle.

## 4. Complete machine-readable source matrix

The companion [CSV](14_DATA_SOURCE_COST_RIGHTS.csv) covers **37 products across 28 fields**. Each row records field scope, source/history/cadence, economic/publication/receipt clocks, corrections, coverage, participant observability, quote scope, dated price components, retention/training/internal/external rights, current evidence, owner, qualification receipt, phase-specific essential/optional status and incremental engineering.

| ID | Product / representation | Role and current evidence |
|---|---|---|
| D01 | Theta options trade_quote | Essential trade/quote representation for public signing; Theta is the existing candidate, not an exclusive vendor requirement; Integrated path in supplied corpus; raw retention/current entitlement unverified |
| D02 | Theta options quote history tick | Essential for quote-event/liquidity models; optional for an initial trade-sampled baseline; vendor replaceable; Public documentation only; no purchase or account test |
| D03 | Theta all-Greeks history | Sensitivity representation essential for Greek pressure; this vendor calculation optional; Public documentation only; no purchase or account test |
| D04 | Theta options OI | Essential if using OI-based state assumptions; optional for pure intraday flow increments; Public documentation only; no purchase or account test |
| D05 | Theta stocks Nasdaq Basic live | Optional local-venue reference; insufficient as the required consolidated live equity BBO; Public documentation only; no purchase or account test |
| D06 | Theta stocks CTA/UTP delayed | Optional historical/delayed reference; unsuitable for live feature timestamps without delay; Public documentation only; no purchase or account test |
| D07 | Existing Terminal Quote Plane | Essential equity-reference ownership and current quote evidence for live priced signals; Ownership established in corpus; no current probe |
| D08 | Theta index values | Essential appropriate index reference for index-level hypotheses; alternative reference vendor possible; Public documentation only; no purchase or account test |
| D09 | Databento OPRA.PILLAR alternative | Optional alternative/comparator to D01/D02; not an additional mandatory subscription; Public documentation only; no purchase or account test |
| D10 | OPRA non-display fee layer | Essential rights classification when the selected OPRA use is in scope; not a separate alpha input; Public documentation only; no purchase or account test |
| D11 | Cboe C1 Open-Close 10-minute | Optional high-priority participant pilot after public-data baseline; essential only to the labeled-capacity experiment; Public documentation only; no purchase or account test |
| D12 | Cboe C1 Open-Close one-minute | Optional later refinement after ten-minute marginal value is demonstrated; Public documentation only; no purchase or account test |
| D13 | Cboe C1 Open-Close EOD | Initialization evidence essential for claimed absolute covered inventory; this EOD product optional for flow-only research; Public documentation only; no purchase or account test |
| D14 | Cboe C1 enhanced trade-by-trade | Optional later trade-signing/complex-package label audit; Public documentation only; no purchase or account test |
| D15 | Cboe BZX Open-Close | Optional cross-venue expansion; required coverage evidence only if BZX inventory claims are made; Public documentation only; no purchase or account test |
| D16 | Cboe C2/EDGX Open-Close | Optional cross-venue expansion; no C1/BZX price or rights extrapolation; Public documentation only; no purchase or account test |
| D17 | NYSE Arca/American options Open-Close | Optional cross-venue participant expansion; one-minute capability remains unqualified; Public documentation only; no purchase or account test |
| D18 | NYSE Pillar Order Imbalances | Essential NYSE auction-state representation for NYSE nowcasts; delivery vendor replaceable; Public documentation only; no purchase or account test |
| D19 | NYSE Arca Order Imbalances | Essential Arca auction-state representation for SPY/Arca nowcasts; delivery vendor replaceable; Public documentation only; no purchase or account test |
| D20 | Nasdaq NOII via TotalView/ITCH | Essential Nasdaq auction-state representation for Nasdaq nowcasts; delivery vendor replaceable; Public documentation only; no purchase or account test |
| D21 | AmerX early MOC portal | Optional licensed early-channel experiment; not required to build a public-data pre-publication forecast; Public documentation only; no purchase or account test |
| D22 | MrTopStep Market Imbalance Meter | Optional consumer comparator; not an essential machine data source; Public documentation only; no purchase or account test |
| D23 | FinancialJuice early-MOC headlines | Optional headline provenance experiment; weak standalone panel; Public documentation only; no purchase or account test |
| D24 | Databento GLBX.MDP3 futures | Essential futures representation for an ES/NQ cross-product claim; this vendor and full depth are optional choices; Public documentation only; no purchase or account test |
| D25 | CME futures options via GLBX/DataMine | Essential only when CME options are within the claimed cross-product coverage; optional later extension; Public documentation only; no purchase or account test |
| D26 | CME non-display fee layer | Essential CME rights classification when selected usage is in scope; Public documentation only; no purchase or account test |
| D27 | DTCC ETF Portfolio Data | Optional basket enhancement; contemporaneous basket representation essential if creation-basket demand is claimed; Public documentation only; no purchase or account test |
| D28 | Issuer ETF NAV/shares/holdings | Essential dated issuer observations for ETF net-share-flow proxy; optional for baseline options-only model; Public documentation only; no purchase or account test |
| D29 | NYSE Arca EOD ETP report | Optional external close-label cross-check; not a primary-flow requirement; Public documentation only; no purchase or account test |
| D30 | FTSE Russell membership/rebalance notices | Essential Russell event representation within rebalance program; specific licensed feed optional; Public documentation only; no purchase or account test |
| D31 | MSCI review schedule/change files | Essential MSCI event representation within rebalance program; specific licensed feed optional; Public documentation only; no purchase or account test |
| D32 | S&P DJI notices/pro-forma weights | Essential S&P event representation within rebalance program; specific licensed feed optional; Public documentation only; no purchase or account test |
| D33 | Nasdaq GIW/GIFFD NDX reference data | Essential Nasdaq event representation within rebalance program; specific licensed feed optional; Public documentation only; no purchase or account test |
| D34 | FINRA ATS/non-ATS transparency | Optional delayed market-structure context; never a live dealer-flow dependency; Corpus integration exists; no current health claim |
| D35 | Author closing-auction research dataset | Optional older-regime external benchmark; Public documentation only; no purchase or account test |
| D36 | Massive consolidated stock trades / intraday off-exchange prints | Essential intraday trade representation if testing intraday off-exchange effects; Massive optional alternative; not required for core options model; Official documentation candidate only; no API runtime or entitlement verified |
| D37 | Theta live options full-trade stream plus selected-contract quote stream | Essential live event delivery for a live options product; streaming not required for historical-only research; Theta is current candidate; Documented capability only; current live subscription/socket not tested |

### Final source-qualification additions

Massive consolidated trade documentation distinguishes participant, SIP and TRF clocks and REST nanosecond versus streaming millisecond encodings. A reporting-facility ID is not an ATS, beneficial owner or dealer-side label. The optional intraday execution-memory projection must pass through the existing tape owner. [A64] [A65] [A66]

Theta full-trade streaming includes the preceding NBBO and subsequent quotes; those later quotes cannot enter earlier signing. Dedicated quote subscriptions are a separate capability for selected contracts. The current subscription documentation also has symbol-specific history limits and a CTA-history discrepancy with commercial copy; D06/D08/D37 preserve them rather than applying one broad history date. [A67] [A68] [A69] [A70]

### Budget interpretation

Published fees are components, not all-in quotes. Historical months, ongoing subscriptions, exchange non-display classifications, storage/processing and external derived use can be separate. Confirm scope with the current owner and executed terms before any later spend. No license, sample request or subscription was initiated by this research. C1 ten-minute history at the displayed schedule would make three requested months $3,000 in historical-file charges; that arithmetic is neither a live entitlement nor a sufficient validation sample. A formal study may need much longer history or prospective capture. [A33]

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[A22]: https://www.thetadata.net/commercial-use
[A23]: https://www.thetadata.net/docs/operations/option_history_trade_quote.html
[A24]: https://www.thetadata.net/docs/operations/option_history_open_interest.html
[A25]: https://www.thetadata.net/subscriber-agreement
[A26]: https://cdn.opraplan.com/documents/OPRA_Fee_Schedule.pdf
[A27]: https://www.thetadata.net/docs/operations/option_history_quote.html
[A28]: https://www.thetadata.net/docs/operations/option_history_greeks_all.html
[A29]: https://datashop.cboe.com/cboe-options-open-close-volume-summary
[A30]: https://datashop.cboe.com/documents/Open_Close_10m_Spec_v1.6.pdf
[A31]: https://datashop.cboe.com/documents/Open_Close_1m_Spec_v1.5.pdf
[A33]: https://cdn.cboe.com/resources/membership/Cboe_FeeSchedule.pdf
[A34]: https://www.cboe.com/us/options/membership/fee_schedule/bzx/
[A35]: https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail
[A36]: https://www.nyse.com/publicdocs/nyse/data/NYSE_Options_Exchange_Open-Close_Client_Specification_v1.0d.pdf
[A37]: https://www.nyse.com/data-products/catalog/open-close-volume-summary
[A38]: https://www.cmegroup.com/market-data/files/june-2026-market-data-fee-list.pdf
[A39]: https://www.cmegroup.com/market-data/license-data/market-data-policy-education-center.html
[A40]: https://databento.com/docs/venues-and-datasets/glbx-mdp3
[A41]: https://databento.com/pricing
[A56]: https://databento.com/docs/venues-and-datasets/opra-pillar
[A58]: https://www.cmegroup.com/market-data/browse-data/catalog/futures-and-options-data.html
[A64]: https://massive.com/docs/rest/stocks/trades-quotes/trades
[A65]: https://massive.com/docs/websocket/stocks/trades
[A66]: https://massive.com/docs/rest/stocks/market-operations/condition-codes
[A67]: https://http-docs.thetadata.us/Streaming/US-Options/Full-Trade-Stream.html
[A68]: https://thetadata.net/docs/Articles/Getting-Started/Subscriptions.html
[A69]: https://http-docs.thetadata.us/Streaming/Getting-Started.html
[A70]: https://http-docs.thetadata.us/Streaming/US-Options/Quote-Stream.html
