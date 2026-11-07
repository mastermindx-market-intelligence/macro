# International Markets: Global Surveillance Masterplan

## A worldwide equity, credit, dollar and US transmission research system

**Prepared:** 21 October 2026 UTC. Census observations were collected across 20–21 October 2026.  
**Commission:** census the existing International Markets programme, integrate its unfinished masterplans, design the global expansion, and upgrade the editable Paper reference.  
**Programme home:** international-risk-intelligence / WS:PAPER-INTERNATIONAL-WAVES.  
**Status:** consolidated architecture and implementation proposal; editable design reference completed. This document does not claim that the production page, either existing draft PR, or a new global model has shipped.  
**Source baseline:** Macro main at 90eb4df175c009b770303dee417eb09aef1a63b4. Mutable PR and served-site observations are dated evidence, not permanent state.  
**Paper:** [Global Surveillance · R13 · Expansion](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-H-0), within the existing “International Markets · R10 · Current Build” file. R12 country research and the earlier programme pages remain intact.

---

## 1. Executive decision

Build a **global market observatory above the existing country research cockpit**. The top-level job is to discover unusual moves and spreading financial pressure anywhere material, then establish whether there is a plausible, evidenced path into US assets. Country research supplies policy and economic depth after a market earns attention.

The product should answer six questions, in order:

1. What changed across the world's important equity markets?
2. Is the move local equity weakness, currency translation, a common global factor, or a more unusual local divergence?
3. Is there supporting credit, funding, liquidity or external-balance evidence?
4. Which documented channels could carry the shock elsewhere, particularly into US markets?
5. Has an eligible US observation corroborated the proposed pathway, contradicted it, or remained inconclusive?
6. What evidence would strengthen, invalidate or resolve the research thesis?

The unit of coverage must become **the market and its instruments**, with geography as one relationship. An economy, exchange, benchmark, listed company, ETF and currency are not interchangeable identities. “Emerging” is a dated classification supplied by a named index provider, not a permanent intrinsic property.

### The central architecture distinction

Keep three layers independent:

| Layer | Question | Expansion rule |
|---|---|---|
| Market observations | Can we show qualified equity, currency, liquidity and other observations? | Expand broadly as identity, source rights, history and calendar qualification permit. |
| Research and risk context | What do the observations imply, with which limitations? | Publish capability-specific findings and explicit gaps. |
| Validated scoring or action authority | Can this model change a risk score, sizing decision or automated action? | Expand only through the existing validation and promotion owners. |

A market can be covered in the scanner while remaining unscored for comprehensive risk. A market outside the existing contagion graph can still have useful exposure research. Neither condition authorizes a fabricated model score.

### Recommended scope

Use a **63-jurisdiction initial planning roster**, comprising the current 47-country MSCI developed/emerging universe plus 16 additional or specially handled markets. Treat this as an initial floor, not an exhaustive definition of “major.” Add every venue or segment that satisfies the materiality rules in section 4. The implementation may therefore contain substantially more market segments and benchmarks than jurisdictions.

The first release should be a reliable global daily scanner. Intraday coverage, constituent breadth, country credit, refinancing profiles and statistically qualified propagation should advance on separate coverage dimensions. A promise of universal real-time, full-credit coverage would be unsupported by the present infrastructure.

---

## 2. What the census actually found

### 2.1 The served page has a concrete access and asset failure

During this census, the anonymous route [mastermind-x.com/intl.html](https://www.mastermind-x.com/intl.html) returned HTTP 200 and approximately **3.06 MB of HTML**, while the referenced workspace stylesheet and entry script returned **HTTP 401, authentication_required**:

| Resource observed | Result | Product consequence |
|---|---|---|
| /intl.html | 200 HTML | The document arrives. This alone does not prove a functioning page. |
| /intl_workspace.css?v=e321de56 | 401 JSON | Workspace presentation does not load. |
| /intl_workspace_entry.js?v=8dccfb1b | 401 JSON | Workspace controls do not initialize. |

A real browser showed the unstyled workspace, disabled primary controls and multiple alternative panels exposed together. The existing public navigation still rendered. Nine disabled main buttons were observed. This establishes a served-path defect rather than merely a design preference.

**Closing recheck:** at 21 October 2026 00:28:35 UTC, the page still returned 200 with 3,056,004 bytes, and both cited assets still returned 401 authentication_required. Both PRs remained open drafts at the same heads listed below.

The observed main access configuration lacked the workspace asset entries. The country-cockpit candidate in PR #9596 already proposes nine precise asset paths: workspace, macro, risk and history CSS; state, library search, scenario, workspace and entry JavaScript. **That diff is a candidate repair, not proof of repair.** The correct next step is to reconcile and release through the incumbent lane, preserve raw-data/API restrictions, and verify anonymous and entitled journeys on the actual served site. Do not blanket-open a directory or add another competing access patch.

Evidence: [main access policy](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/config/site_access.yml), [PR #9596](https://github.com/mastermindx-market-intelligence/macro/pull/9596), plus direct browser and anonymous HTTP observations in this session. This report does not establish the cause of unrelated CI failures.

### 2.2 Existing coverage is broader in code than on the landing page

| Plane | Observed current scope | What that does and does not establish |
|---|---|---|
| Configured International countries | JP, KR, TW, IN, AU, GB, EZ | Seven configured cockpit records, not seven universally complete data sets. |
| Served index/FX comparison | Seven markets; five qualified returns for the observed default 1-month USD view | Japan and Korea were unsupported for that selected comparison. Coverage is horizon- and basis-dependent. |
| Market turns / wider context | Existing world-context capabilities and country routes | These must survive the redesign; they are not proof of global scanner completeness. |
| EM fast-stress research | Existing equity proxies include INDA, EIDO, EZA, EWZ, EWW, EWY and EWT; several EM FX legs exist | EM is already partially represented in the backend. The work is expansion and integration, not inventing EM monitoring from zero. |
| Statistical contagion engine | Fixed 14-ETF basket: six DM proxies, six EM proxies, EEM and SPY | A fixed research population; not every country, exchange or global index. |
| Contagion links | Fixed 11-market set: US, China, Hong Kong, Canada, Korea, Japan, Taiwan, India, Australia, Britain and EZ | Structural/dynamic link context. Brazil and many other EMs are outside this graph. |
| Country macro contract | Five standalone country routes, with shared field qualification and official-source overrides where admitted | It does not imply full official-source coverage for every new market. |
| Stock search | A configured target of 220 names per market and a five-year history setting | Configuration is not a measured census of live, valid constituents or complete histories. |

The observed public snapshot was dated 16 October 2026 and explicitly delayed. It must not be called live. The five-versus-seven comparison is an eligibility result for that specific view, not a general statement that two markets have no data.

Evidence: [config.yml](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/config.yml), [intl_inputs.py](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/engine/intl_inputs.py), [intl_risk.py](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/engine/intl_risk.py), [contagion.py](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/engine/contagion.py), [contagion_links.py](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/engine/contagion_links.py).

### 2.3 A geography mismatch needs explicit repair

The current “Eurozone” market record uses STOXX Europe 600 as its equity benchmark. European equities and euro-area macroeconomic data describe different populations. The expansion must create explicit regional benchmark and economic-area relationships, retain historical identifiers and deep links, and avoid silently relabeling the old series as a euro-area equity market.

The same discipline applies elsewhere: a US-listed country ETF is a traded instrument with its own composition and clock; Hong Kong is a separate listing and market-access context from mainland China; India can contain multiple venues and indices without becoming multiple economies. The Brazil and TOPIX examples in R13 are proposed design examples, not silent changes to existing benchmark defaults.

Evidence: [International Macro Data Contract](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md).

### 2.4 The unfinished implementation has two distinct carriers

| Carrier | Observed exact state | Required disposition |
|---|---|---|
| [PR #9596 — country cockpit](https://github.com/mastermindx-market-intelligence/macro/pull/9596) | Draft, open; head 6ad0c377ed80a8ccf07ecbfb6c7b44530b753cf7. Product/design/accessibility acceptance and extensive local checks are reported by its owner. CI run 39411669144 concluded failure; legacy packs 0, 2, 3 and 9 failed. | Retain the existing owner and exact-candidate review path. Resolve permitted diagnostics, remaining data/logic/integration verdicts, full-depth index/FX acquisition and served publication. Local passes are not release acceptance. |
| [PR #8754 — ten-view workspace](https://github.com/mastermindx-market-intelligence/macro/pull/8754) | Draft, open; published head 582708537fd4f07b6a4d42cd54ed6220a34c640b. Incumbent checkpoint records clean local head 7f1aa2ec3ff3a9211bc4c3acdd5999bcf9e624f3 with four unpublished commits. | Preserve shared-source custody and its explicit hold. No alternative CI log/artifact reader, push or rerun may be used to probe around the egress admission restriction. |
| Existing Terminal Investigation / Saved integration | IM08/IM09 remain dependency-bound; original IW2 ownership persists. | Extend the existing investigation and saved-record contract. Do not build a second Saved store or transfer custody through this plan. |

The #8754 host checkpoint was read at /Volumes/Mastermind/evidence/paper-waves-20261006-01a1101f/CHECKPOINT.md. Its current frontier was dated 20 October 2026 11:25 UTC. The checkpoint explicitly pauses its continuation automation and forbids further requests to the historically refused hosted log/artifact path until its owner establishes restored admission. This census did not fetch those logs, rerun CI, push its branch, or change the pause.

The earlier September R2 checkpoint is historical context. It must not reset the newer programme to “not built.” Accepted source leaves, numerical contracts and component evidence should be reused unless a material change invalidates them.

---

## 3. Integrating the existing masterplans

This proposal is an expansion of the existing programme, not a parallel dashboard, risk engine, data control plane or scoring constitution.

### 3.1 Prior-plan crosswalk

| Existing authority or plan | Preserve | Expansion introduced here |
|---|---|---|
| [INTL_FIX_MASTERPLAN](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/research/INTL_FIX_MASTERPLAN.md) | Existing validation constitution, killed claims, display-versus-scoring boundary and sole promotion path. | Add global market candidates to research coverage; preregister any new signal or changed universe separately. Do not revive rejected return-prediction claims. |
| [International Risk Desk](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/research/INTL_RISK_DESK_MASTERPLAN_BY_FABLE.md) | Fast stress versus slow vulnerability; country/regional/proxy distinctions; source limitations. | Broaden country/venue observations and make risk coverage visible field by field. Keep missing CDS, funding-basis and maturity data explicit. |
| [Cross-Border Flow Regimes](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/research/CROSS_BORDER_FLOW_REGIMES_MASTERPLAN_BY_FABLE.md) | FX/equity/spread regime inference remains descriptive. | Compare inferred pressure with measured flow or position evidence when available; never label the inference as observed capital flows. |
| [Contagion Links](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/research/CONTAGION_LINKS_MASTERPLAN_BY_FABLE.md) | Frozen structural version, declared basket, existing dynamic method and shadow status. | Add typed exposure evidence and candidate broader networks without changing the accepted graph in place. |
| [Contagion Sensing and Propagation](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/research/CONTAGION_SENSING_PROPAGATION_MASTERPLAN_BY_FABLE.md) | Existing state, source and AI-context wiring; owner boundaries. | Feed the same evidence records into the new user journeys; no second alert or narrative authority. |
| [Paper International Waves 1–3](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/research/paper_international_wave1_wave2/README.md) | Foundation, ten existing views, 18 legacy families, stocks mode, source/auth/publication owners and real-path acceptance. | Add global discovery above the country depth layer; preserve accepted adapters and disclosures. |
| [WS:PAPER-INTERNATIONAL-WAVES](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md) | One connected programme and integration owner. | Attach the new work packages in section 15 after owner reconciliation. The proposed package labels are not new execution grants. |
| R12 Country Intelligence / PR #9596 | Country thesis, official forecasts where qualified, policy/fiscal/external context, independent clocks and thesis-change conditions. | Retain as Country research; link from a worldwide scanner and market dossiers. |

### 3.2 IM00–IM10 disposition

| Existing package | Integration treatment |
|---|---|
| IM00 foundation | Extend identity, coverage and snapshot contracts. Keep one controller and the same publication generation. |
| IM01 overview | Add Global scanner as the international entry journey; preserve the existing overview evidence. |
| IM02 compare / rotation | Expand eligible market populations through explicit versioned selection. Preserve basis, window and comparison state. |
| IM03 inspector / evidence | Reuse as the market dossier and evidence drawer substrate. |
| IM04 macro / policy | Preserve source qualification and connect economy context to the selected market; do not imply policy depth exists everywhere. |
| IM05 risk / transmission | Extend channel evidence, US eligibility and coverage boundaries. Preserve accepted source/reported-state contracts. |
| IM06 history / scenarios | Add event replay and user-authored shocks through the same history/scenario owner. |
| IM07 library / search | Expand discovery and routes through the existing catalogue and deterministic search. |
| IM08 International Investigation | Reuse the existing Terminal investigation adapter; no new research session store. |
| IM09 Saved extension | Persist the same evidence-bound research object through its existing owner; no duplicate watchlist or thesis database. |
| IM10 qualified policy comparison | Preserve accepted four-point arithmetic; complete source mappings, preview and same-record Saved integration under the incumbent programme. |

### 3.3 All 18 legacy research families retain a destination

The existing [library catalogue](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/config/intl_library_catalogue.json) is the authoritative inventory. Keep its presentation keys and route relationships; do not replace it with a new catalogue.

| Existing family | Primary R13 destination / continuation |
|---|---|
| Performance & currency | Scanner, Compare and market price/FX decomposition |
| Leadership rotation | Compare / rotation, with its existing cohort qualification |
| Cross-country comparison | Compare, with economy versus market identity explicit |
| Market turns | Market dossier recovery evidence; existing world-context cohort preserved |
| Recovery quality | Dossier and recovery investigation |
| Participation & concentration | Dossier Stocks & sectors; unavailable breadth remains unavailable |
| Rates, curves & carry | Country research and Credit & dollar risk |
| Central banks & liquidity | Country research / policy divergence |
| Credit & bonds | Risk / credit context; regional proxies cannot substitute for country credit |
| Euro-area fragmentation | European regional context; preserve the selected market on return |
| Growth & inflation | Country research, dated macro evidence |
| Dollar conditions | Dollar channel and the existing Dollar Drivers destination |
| Structural fragility | Dossier external vulnerability, source vintage visible |
| Contagion | Transmission to US, with statistical and EM-US methods distinguished |
| Trade & supply links | Exposure evidence; model context is not documented company exposure |
| Cross-market correlation | Compare / research methods; association is not causality |
| Risk-radar track record | History / model evidence / false-alarm record |
| Country sectors & stocks | Existing /intl_stocks.html and selected-market continuation |

Navigation simplification is a design act only when the demoted capability has a named reachable destination. Preserve old routes, saved links, selected market, horizon, currency, language and theme across these transitions.

---

## 4. Defining worldwide coverage

### 4.1 A versioned universe, not another seven-country list

The September 2026 MSCI ACWI factsheet identifies 23 developed and 24 emerging countries. FTSE's October 2026 matrix uses a different classification scheme and includes classification changes effective in September 2026. These are useful starting taxonomies, not a single universal definition. [MSCI factsheet](https://www.msci.com/documents/10199/255599/msci-acwi.pdf); [FTSE matrix](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/country-classification/matrix-of-markets.pdf).

The universe policy should include:

1. The union of the current MSCI and FTSE developed/emerging market populations, with both provider labels and effective dates retained.
2. Every material national equity venue or segment, even where the jurisdiction is already represented by a headline benchmark.
3. Frontier and other markets with meaningful regional, commodity, dollar-credit, banking, trade or US-company exposure.
4. A special-handling cohort where investability, data access, market functioning or rights require separate treatment. Monitoring relevance is not a declaration that a market is accessible to trade.
5. An explicit inventory of excluded or unsupported markets, including the reason and reconsideration condition.

Use the [ISO 10383 MIC register](https://www.iso20022.org/market-identifier-codes) for venue identity, filtered to the relevant equity venues and effective states. It also contains trading and reporting facilities, so membership in that register alone is not a decision to create an equity scanner row.

Use an approved source of domestic listed market capitalization and equity turnover to test completeness. [WFE statistics](https://www.world-exchanges.org/our-work/statistics) offers monthly/annual market indicators and venue factsheets, but its redistribution terms must be honored. Access to a statistics page is not permission to republish its database.

**Proposed acceptance targets:** all named core jurisdictions have an explicit capability record; all venues above 0.25% of the chosen global capitalization or turnover denominator are reviewed; the qualified observational universe aims to cover at least 99% of eligible domestic listed capitalization and 95% of eligible equity turnover. These are proposed engineering/product targets, not measured achievements. Include regional importance overrides and disclose the denominator, vintage, double-count rules and uncovered share. Avoid double-counting dual listings or exchange-group aggregates.

Freeze the target denominator independently of source availability before calculating coverage. A missing provider, denied entitlement, short history or unsupported instrument remains uncovered within the target universe; it cannot be removed merely to improve the percentage. Report separately: target-universe coverage, coverage within the currently authorized acquisition scope, and unsupported share with reasons. Changes to the target denominator require a dated scope decision and a before/after comparison.

Define what the numerator measures. Coverage through a representative benchmark is **benchmark-surveillance footprint**, not constituent-level capitalization coverage. Count constituent capitalization only where constituent identity, membership and qualified observations support that calculation. Retain separate jurisdiction, venue, benchmark and constituent denominators. The 99%/95% targets must always name which of these measurements they describe; they cannot be used as unlabeled global-completeness claims.

### 4.2 Initial 63-jurisdiction planning roster

| Cohort | Jurisdictions | Count |
|---|---|---:|
| MSCI developed: Americas | United States, Canada | 2 |
| MSCI developed: Europe / Israel | Austria, Belgium, Denmark, Finland, France, Germany, Ireland, Israel, Italy, Netherlands, Norway, Portugal, Spain, Sweden, Switzerland, United Kingdom | 16 |
| MSCI developed: Asia Pacific | Australia, Hong Kong, Japan, New Zealand, Singapore | 5 |
| MSCI emerging: Latin America | Brazil, Chile, Colombia, Mexico, Peru | 5 |
| MSCI emerging: Asia | China, India, Indonesia, South Korea, Malaysia, Philippines, Taiwan, Thailand | 8 |
| MSCI emerging: Europe / Türkiye | Czech Republic, Greece, Hungary, Poland, Türkiye | 5 |
| MSCI emerging: Middle East / Africa | Egypt, Kuwait, Qatar, Saudi Arabia, South Africa, United Arab Emirates | 6 |
| Additional classification / regional coverage candidates | Iceland, Romania, Vietnam | 3 |
| Additional frontier / regional candidates | Argentina, Bahrain, Bangladesh, Kazakhstan, Kenya, Morocco, Nigeria, Oman, Pakistan, Sri Lanka | 10 |
| Special-handling research candidates | Russia, Iran, Venezuela | 3 |
| **Initial planning roster** | Core 47 + additional/special 16 | **63** |

The last three rows are a recommended research scope, not a representation of a uniform current classification or investability status. Every candidate still needs source and access qualification. Markets such as Croatia, Jordan, Mauritius, Slovenia, Tunisia and other regionally important venues can enter through the materiality policy; 63 is not a ceiling.

### 4.3 Multiple markets inside a geography

The first identity wave should explicitly model mainland China's major listing segments and Hong Kong separately; India's major venues; Korean large-cap and growth segments; Taiwan's exchange and OTC context; US major listing venues; European national markets and regional baskets; and major local-versus-offshore instruments.

Each jurisdiction receives a broad-market benchmark candidate, one or more important segment benchmarks where useful, and clearly labeled investable proxies. Choose final providers and exact series only after methodology, rights, history, adjustment and session review. Do not silently replace the existing Nikkei 225 history with TOPIX merely because R13 illustrates a broader Japanese benchmark.

### 4.4 Coverage is a vector

Every market record should report independent capability states for:

- Equity index price/total return and currency translation.
- Constituent breadth, concentration, liquidity and sector composition.
- Local rates and sovereign/credit evidence.
- Dollar funding, external debt, reserves and refinancing.
- Macroeconomic context, policy and official forecasts.
- Documented US exposure and qualified statistical transmission.
- Historical depth, point-in-time usability and rights to display.

States should distinguish qualified, partial, delayed, retained/stale, market closed, suspended, unavailable, denied and not applicable. A missing feed is not a zero; a holiday is not a flat return; a stable peg is not proof of safe dollar funding.

The scanner's headline counts must state the capability being counted. The R13 counts are deliberately labeled illustrative and are not a census of current qualified production coverage.

---

## 5. Identity, time and observation contracts

### 5.1 Extend the existing identity owner

Add the required entities and relationships to the existing identity/ontology contracts after a current-owner interface check. Do not introduce a parallel market registry service or a new universal identifier scheme owned only by this page.

| Entity | Required identity / relationships |
|---|---|
| Economy | Geography and statistical area; country, euro area and regional aggregates remain distinct. |
| Venue / market segment | MIC where appropriate, operating/segment relationship, timezone, session calendar and effective status. |
| Benchmark | Provider identifier, methodology version, constituent population, weighting, quote currency, price versus total return and hedging basis. |
| Instrument | Existing security identifier, listing venue, instrument currency, issuer, underlying benchmark or exposure relationship. |
| Currency | Quote convention, onshore/offshore relationship, regime context and applicable fixing/spot source. |
| Classification | Provider, category, announced date, effective date and historical validity. |
| Economic exposure | Trade, revenue, banking, holdings, commodity or funding relationship with evidence and vintage. |

Maintain aliases for current country keys and URL state. Migration is additive until old routes and saved objects have tested compatibility mappings.

### 5.2 Observation contract

Each observation needs value and units; source and series identity; instrument/market identity; observation or reference period; local session; UTC observation timestamp; source publication/availability timestamp when known; acquisition timestamp; qualification timestamp; revision/supersession relationship; adjustment and return basis; rights scope; quality status; and a pointer to its source receipt.

Distinguish at least these clocks:

1. **Economic reference period:** what month, quarter or trading session the value describes.
2. **Source availability:** when the information became available to a user or the collection process.
3. **Acquisition and qualification:** when this system obtained and accepted it.
4. **Publication:** when an existing product snapshot exposed it.

Re-rendering a page must not advance acquisition or first-known time. A backfill obtained today must not masquerade as information the production system possessed during a past crisis. An official fetch without a successful observation write is not proof of a refreshed stored series.

The existing [intl_run.py](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/engine/intl_run.py) and International Macro Data Contract already establish important parts of this separation. Extend them, rather than creating a second forward-accrual path.

### 5.3 Two comparison modes, plus event-time eligibility

**Latest available** answers what each market most recently reported. It shows the local session and age per row. It is useful for a global desk handoff but must not imply synchronized prices.

**Aligned periods** compares qualified windows under an explicit cutoff policy. Index and FX observations must cover compatible endpoints. The comparison discloses dropped or partial markets. Do not forward-fill an old close into a new return or rank it as a current zero.

**Event-time transmission** adds a stricter condition: the proposed recipient must have had an eligible opportunity to trade after the source event. If Asia has moved and the US session has not yet begun, the correct state is “US response pending,” not “the US ignored the shock.” A matched historical comparison and a causal-response window are different calculations.

### 5.4 Return arithmetic

For FX quoted as USD per unit of local currency:

    1 + r_USD = (1 + r_local) × (1 + r_FX)

Local equities +5% and the currency −10% produce −5.5% in USD. Additive contribution charts must either show the interaction term or allocate it through a declared attribution convention. Price return, gross/net total return, hedged/unhedged return and investable ETF return cannot silently share one ranking.

R13's synthetic Brazil example reconciles −4.2% local equity and −2.8% FX to approximately −6.9% USD. Its chart uses matched synthetic endpoints and makes no claim about current Brazilian prices.

---

## 6. Data acquisition and qualification

### 6.1 Reuse the existing pipeline

The target flow is:

    Existing source adapters and schedules
        → existing observation storage and provenance
        → qualification and session-aware market projections
        → versioned descriptive analytics / research candidates
        → one publication snapshot
        → scanner, dossier, compare, risk, history and existing Saved adapters

The existing scoring/promotion bridge remains a separate downstream boundary. UI code reads a qualified snapshot and never starts collection, advances a ledger, recalculates a new model population or grants a data entitlement.

### 6.2 Source plan

| Capability | Preferred source class | Operational / interpretation rule |
|---|---|---|
| Global equity benchmarks and FX | Existing qualified vendor adapters, official exchange/index sources where permitted, or a licensed global feed selected for the required rights | The current specific EOD grant is not blanket redistribution authority for every new instrument, provider, constituent or intraday series. |
| Venue calendars and market status | Existing calendar owner extended with maintained exchange-specific facts | Handle holidays, half-days, unscheduled closures, auctions and daylight saving; do not assume every exchange follows a weekday calendar. |
| Constituents, corporate actions and breadth | Licensed constituent/security master, authoritative issuer/exchange records | Preserve historical membership, delistings, splits, distributions and methodology changes. No breadth inferred from a small ETF basket. |
| Sovereign and corporate credit | Qualified spread/yield/CDS source with maturity, duration and currency metadata | Regional OAS and ETF performance are explicitly regional/proxy observations. Local yield changes alone do not identify default stress. |
| Dollar funding | Qualified basis, swap/forward and money-market sources where available; existing US funding inputs; official backstop operations | Spot FX is a translation observation, not a direct measure of dollar scarcity. Separate facility availability, actual usage and operational tests. |
| External vulnerability | BIS, IMF, official central-bank/statistical sources and other admitted official debt/reserve data | Slow, vintage-aware context. Never turn a quarterly data release into a daily market trigger by forward-filling its timestamp. |
| Cross-border banking | BIS CBS and LBS, used according to their distinct definitions | Consolidated banking-group exposure and residence-based positions cannot be added as if they were independent measurements of the same thing. |
| Portfolio exposure | IMF Portfolio Investment Positions by Counterpart Economy and qualified holdings sources | Positions are not daily flows. Coverage and reporting participation vary. |
| Company / sector US exposure | Existing company research and ontology sources, filings, qualified holdings, revenue and supply-chain evidence | Issuer domicile or a generated narrative does not establish a documented operating exposure. |
| Policy and forecasts | Existing official-source adapters and the qualified country cockpit | Store forecast publication, horizon, units and revision; keep forecasts separate from realized values. |

Primary references: [BIS global liquidity](https://data.bis.org/topics/GLI), [BIS consolidated banking statistics](https://data.bis.org/topics/CBS), [IMF portfolio positions](https://data.imf.org/en/datasets/IMF.STA:PIP), [BIS debt service ratios](https://data.bis.org/topics/DSR), [New York Fed swap operations](https://www.newyorkfed.org/markets/desk-operations/central-bank-liquidity-swap-operations).

BIS global-liquidity measures include foreign-currency credit and are quarterly. BIS DSR methodology also cautions that changes relative to a country's own history are more meaningful than a naive ranking of absolute levels across countries. The New York Fed distinguishes actual swap operations from small-value operational-readiness exercises. These distinctions belong in the data contracts, not only in prose footnotes.

### 6.3 Acquisition tiers and operational budgets

Start with lawful daily benchmark/FX observations across the broad universe. Add priority intraday coverage only where the source supports both the required cadence and user-facing rights. Give slower structural sources their own update schedules and retained-data states.

For each adapter, record history depth, expected release schedule, source timeout, retry policy, rate limit, rights, fallback policy and qualification tests. Publish coverage and source health separately from market risk.

The incumbent country-cockpit evidence reports a BIS bulk acquisition taking about 238 seconds against a 45-second collector budget. Resolve that through the existing collection owner: appropriately scheduled bulk acquisition, bounded incremental work, retained observation provenance and publication that tolerates one slow organ. Raising a page-render timeout or inventing a fetch-on-view path is not the solution.

Vendor procurement should follow a written gap analysis: exact instrument coverage, index/constituent rights, corporate actions, historical point-in-time support, local session timestamps, bulk versus streaming cost, redistribution and auditability. This plan does not authorize a purchase or assert that publicly readable data is freely redistributable.

---

## 7. The analytical system

### 7.1 Keep observation, vulnerability and propagation separate

| Object | Time scale | Examples | User interpretation |
|---|---|---|---|
| Current market pressure | Session / daily / weekly | Equity drawdown, breadth deterioration, spread widening, FX moves, liquidity changes | What is happening now? |
| Structural vulnerability | Monthly / quarterly / annual | External debt composition, reserves, refinancing needs, fiscal/external balances, bank or portfolio exposure | What could make this market sensitive to a shock? |
| Receiver response and propagation evidence | Event windows / market sessions | Qualified receiver response, wider credit stress, funding response, cross-market tail dependence | What receiver evidence is consistent with the proposed channel? |
| Research anomaly | Declared estimation window | Peer-relative underperformance, factor residual, price/credit disagreement | What is unusual enough to investigate? |
| Data quality | Source-specific | Missing, delayed, denied, corrected, conflicting, non-trading | Which conclusions are supportable? |

A vulnerability is not an alarm. An anomaly is not a buy recommendation. A stressed local market is not automatically a systemic US threat. Data quality may constrain an assessment without changing the economic risk that actually exists.

### 7.2 Equity surveillance

The broad scanner should begin with transparent calculations: local and USD returns, drawdown from a declared peak, realized volatility, gap size, turnover relative to the market's own history and a clearly defined trend/repair view. Compare horizons only when history and endpoints qualify.

Where constituent evidence exists, add advance/decline participation, share above declared trend levels, equal-weight versus cap-weight performance, sector contribution and concentration. Publish the covered constituent share and historical-membership basis. A market whose top two stocks dominate its index deserves a different interpretation from a broad participation decline.

Keep bank and financial-sector relative performance available as a credit-sensitive observation, with no claim that it measures bank solvency. Keep local and offshore listings separate; US trading in an ETF after the local market has closed may contain information absent from the underlying last close.

### 7.3 Dislocation research

Use a ladder of increasing analytical complexity:

1. **Own-history anomaly:** an unusually large return, drawdown, volatility or liquidity move relative to that market's qualified past.
2. **Peer divergence:** the market differs from an economically justified peer group, after currency basis and sector composition are disclosed.
3. **Factor residual:** estimate how much remains after declared global equity, sector, commodity, rate and currency factors.
4. **Cross-asset disagreement:** equities, FX and credit tell different stories at compatible times.
5. **Instrument discrepancy:** local-versus-offshore, ETF-versus-benchmark or cross-listing differences, only after trading hours, distributions, costs and quote conventions qualify.

Start with robust and explainable baselines. Robust normalization against own history, shrinkage toward a regional baseline and minimum-history gates are preferable initial candidates to an opaque global anomaly score. The product should disclose whether a percentile compares the market with its own past or with other markets today. Neither is a reversal probability.

For a factor residual, store the factors, estimation window, usable observations, parameters, outlier treatment and stability diagnostics. A residual can reflect an omitted exposure or poor data. Preserve that alternative in the research explanation.

Rank **research attention**, not expected profit, until a separate predictive claim earns qualification. Opportunity and fragility remain independent axes: a market can be statistically unusual while its funding and liquidity deteriorate. Do not hide the latter behind a “cheap” or “bottom forming” label.

### 7.4 Credit surveillance

Separate sovereign, bank, corporate and regional credit. For every spread or yield, retain instrument currency, maturity, duration, benchmark, source close and comparability. A local sovereign yield change can reflect inflation or expected policy; it cannot be automatically recoded as credit deterioration.

Useful initial views include qualified sovereign spread change, regional EM OAS, bank-equity relative performance, sovereign-curve moves, credit-versus-equity divergence and country bond-proxy returns. Each proxy retains its name and level of aggregation. A regional EM bond ETF cannot supply an individual country's CDS value.

Credit alerts should distinguish level, change, acceleration and persistence. A wide spread that is steadily improving is different from a narrow spread that is abruptly widening. Publish the relevant history and qualification rather than blending all four readings into an unexplained score.

### 7.5 Dollar and external-financing surveillance

Use two complementary panels:

**Dollar pressure now:** broad dollar context, local FX changes, onshore/offshore divergence where comparable, qualified forward/basis or funding data, liquidity and official operation evidence.

**Sensitivity to dollar pressure:** external debt currency and sector, remaining-maturity refinancing needs where available, reserve adequacy with composition/encumbrance caveats, current-account and export-revenue context, natural hedges, foreign participation and policy constraints.

The mechanism is important: a depreciation can increase the local-currency burden of unhedged dollar liabilities, while dollar export revenue or hedging can offset part of it. The system needs evidence about those exposures before asserting a balance-sheet effect. A currency peg may conceal adjustment elsewhere; a flat exchange rate never substitutes for a funding observation.

Avoid adding incompatible debt stocks or comparing short-term debt and reserves with inconsistent reference periods or maturity definitions. Present a missing maturity ladder as a coverage gap. Do not manufacture one from aggregate debt totals.

Official support facilities are a backstop context, not proof that all firms can access dollars or that support will be used. Actual usage, operational testing and policy availability should be separate fields.

### 7.6 Slow vulnerability and country depth

Reuse the R12 cockpit for policy, growth, inflation, fiscal/external context, official forecasts, research thesis and conditions to change view. Broader market observation does not wait for a fully written country dossier.

New countries receive a small qualified context first: what the benchmark represents, the FX regime evidence, major sector concentration, available external-credit facts, policy-event links and explicit unknowns. Add deeper policy and forecast content only when the source contract qualifies it.

Official DSRs and credit-gap estimates should be interpreted according to their methodology and their own-history deviations. Do not rank all countries by raw DSR levels as though differences in institutions and estimation assumptions were absent. [BIS DSR methodology](https://data.bis.org/topics/DSR).

---

## 8. Contagion and transmission mechanisms

### 8.1 Build an evidence graph with typed channels

Extend the existing ontology and exposure contracts with a typed evidence projection. Keep the accepted eleven-market graph and fourteen-ETF statistical model unchanged. Any broader statistical graph is a separately versioned research candidate under the existing validation owner.

Each edge must have a channel, source, vintage, units or interpretation, direction if supported, coverage, revision and model/evidence status. Do not populate a plausible-looking network with LLM-invented weights.

**Recipient corroboration** means an eligible response consistent with the proposed channel. It does not establish that the source caused the response. Shared shocks and other explanations remain live until the evidence distinguishes them. Use “US evidence” or “recipient corroboration” in default product labels; reserve stronger causal language for an independently supported claim.

| Channel | Source-side evidence | Structural link | Recipient corroboration |
|---|---|---|---|
| Dollar funding | Qualified funding or FX pressure | USD liabilities, refinancing, banking or dollar-intermediation exposure | US or global funding response after an eligible interval |
| Sovereign / banking | Sovereign or bank stress | Qualified cross-border banking claims or documented holdings | Receiver bank/credit response, with global factors retained |
| Portfolio / fund ownership | Local asset repricing and liquidity pressure | Shared investor holdings, fund exposures or measured redemptions where available | Related assets or funds respond; positions are not treated as observed sales |
| Trade / earnings | Local economic or policy shock | Company revenue, supply-chain, import/export relationships | Relevant US sectors or companies respond in a plausible window |
| Commodity / terms of trade | Commodity shock or local resource sensitivity | Export/import dependence, sector composition and company exposure | Receiver earnings/credit/equity sensitivity corroborates |
| Leverage / liquidity | Widening spreads, volatility and deteriorating liquidity | Qualified leverage, collateral or common-position evidence | Broader deleveraging evidence, not merely a second correlated price chart |
| Common global shock | Global rates, broad USD, risk or commodity move | Shared factor exposure | Simultaneous international weakness may fit this alternative better than bilateral transmission |

The displayed pathway should distinguish:

- Observed source stress.
- Documented exposure.
- Statistical association or directional candidate.
- Hypothetical scenario.
- Observed recipient corroboration.

These labels must survive summaries and downstream reuse. A generated sentence cannot promote a directional candidate into confirmed causality.

### 8.2 Preserve the fixed existing models

The current links model contains 11 markets and a frozen structural matrix. The statistical engine uses a separate 14-ETF population. Preserve both identities, versions, thresholds and promotion status. Adding a market to the scanner must not change their normalizations, weights, centrality, percentiles or historical results.

For a market outside those populations, show structural exposure research and qualified observations first. R13 explicitly demonstrates this with Brazil. A user should never see a low graph score merely because a market is absent from the graph.

### 8.3 Candidate broader models

A naive extension of the current VAR to dozens of markets is not acceptable. With 63 series and two lags, an unrestricted equation already needs 126 lag coefficients before other terms; a 150-observation window leaves little room for stable estimation. More venue/sector series make the problem worse.

Evaluate a small set of preregistered candidates instead:

- Regional factor models with market-specific residuals.
- Regularized or shrinkage VARs on a qualified core, with explicit population/version control.
- Tail co-exceedance and conditional stress breadth, which describe joint stress without claiming direction.
- Lagged response research using session-aware timestamps and common-factor controls.
- Structural exposure networks whose weights are measured positions or documented exposure categories, kept separate from statistical connectedness.

Use the existing model validation owner and research harness. Do not deploy a new model merely because its network visualization looks convincing. Rising correlation can be affected by changing volatility; the identification problem has a substantial literature, including [Forbes and Rigobon](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00494). A statistical network is not a causal map.

### 8.4 A qualified transmission event

An event record should contain the origin observation, first-qualified timestamp, affected markets, proposed channel evidence, relevant receiver, eligible receiver window, observed response, alternative explanations, severity, confidence, coverage and revision status.

Suggested descriptive progression:

    Local stress → regional spread candidate → US response pending / mixed / corroborating

This is a research vocabulary, not a new action state machine. Map it onto the existing state and alert owners. Existing signal promotion remains unchanged.

Require independent evidence families before using stronger language. Three equity-derived indicators are not three independent confirmations. Two data vendors carrying the same underlying close are not independent economic evidence. Retain a “common global shock” explanation wherever appropriate.

---

## 9. The US relevance layer

The page becomes useful to a US-focused investor when it identifies **which US exposures deserve investigation and why**. A world heatmap alone cannot do this.

### 9.1 Recipient hierarchy

Start with US broad equity, credit and funding context. Then drill into sectors, industry groups, banks, companies, funds or supply chains only where the existing exposure owner has qualified evidence.

For each recipient, distinguish operating revenue exposure, production/import exposure, direct financial claims, fund holdings and shared factor sensitivity. Do not combine them into a single “country exposure percentage” when their denominators differ.

### 9.2 Exposure versus market response

A large documented exposure and a small current price response can coexist. A large price response without documented direct exposure can reflect shared factors. The interface should show the two reads side by side and preserve the uncertainty.

The user should be able to open the existing company or sector research page with the same market, channel and evidence context. It should not create a new company dossier inside International Markets.

### 9.3 Ranking what matters

Prioritize the attention queue using transparent components: magnitude and persistence of qualified stress; breadth across independent assets; documented receiver relevance; observation eligibility; and evidence quality. Initially this can be a deterministic research ordering with clear component explanations.

Do not average countries equally and call the result a global portfolio risk measure. Do not let an extreme small-market reading dominate US Risk Radar merely because the scanner has added a new row. If an aggregate is introduced, declare its economic weighting and missing-data rule, then validate the intended claim separately.

---

## 10. Advanced product features and complete journeys

### 10.1 Global scanner

Primary question: **What changed, and where should I investigate?**

The landing view contains a brief, a bounded market table and an attention rail. Filters cover region, provider classification, session, capability and research relevance. Users can choose local, USD and other qualified return bases, horizon and aligned versus latest observations. The default glance shows plain-language anomaly labels; technical residual statistics live in the study view and evidence controls.

Useful additions include an Asia–Europe–Americas handoff view, since-last-visit changes, new-versus-persistent pressure, source corrections and a qualified coverage drawer. The system should preserve the user's selected market set and basis across all destinations.

### 10.2 Dislocation explorer

Primary question: **What is unusual, and what could explain it?**

Separate price anomaly from vulnerability. Include comparator/factor basis, confidence, liquidity, missing inputs, competing explanations and conditions to change the thesis. A partially observed market can remain visible in the research queue while being absent from the vulnerability plot.

Continue into a market dossier, a peer comparison or the existing Saved research object. Do not end the journey with a ranking that has no evidence or follow-up action.

### 10.3 Market dossier

Primary question: **What exactly am I exposed to, and has the thesis changed?**

Tabs cover Market & FX; Credit & dollar risk; Economy & policy; Stocks & sectors; US exposure; and Evidence & history. Preserve the separation between the economy, benchmark and investable instrument. Show market access and liquidity context where supported, without implying that every user can trade the market.

A concise lead presents the current evidence and next research step. The existing R12 cockpit supplies deeper policy and forecast work. A new market can have complete price surveillance and incomplete macro research without appearing broken.

### 10.4 Transmission workbench

Primary question: **Through what channel could this matter to the US, and is that happening?**

The default is a channel evidence matrix. Network context and scenario exploration are secondary modes. Source stress, exposure evidence and US corroboration remain separate columns. Selecting a channel opens its source evidence and receiver, rather than an ungrounded causal narrative.

### 10.5 Scenario lab

Allow a user to specify shocks such as a currency depreciation, sovereign spread widening, local equity decline, commodity move or funding disruption. Reuse the existing scenario owner and snapshot binding.

Every result states assumptions, horizon, source vintage and which inputs are held constant. Mechanical translation can be exact: a hypothetical local equity decline of 10% with a 5% local-currency decline produces a 14.5% USD loss. A modeled US-sector response requires a separate qualified exposure or estimation model; if that model is unavailable, show a qualitative exposure pathway rather than a fabricated loss number.

Scenario results never become forecasts merely because a user saved them. Include adverse, benign and invalidated conditions, plus sensitivity to uncertain inputs.

### 10.6 Historical event replay

Offer a “what was known then?” replay through the existing History system. Use only then-available observations, membership, classifications and revisions for point-in-time model evaluation. Where historical reconstruction lacks availability metadata, label it as reconstructed research and exclude it from claims about what the live system would have known.

The current five-year configuration cannot by itself support every older crisis. Extend history through qualified acquisition before promising a multi-decade crisis library. Distinguish a documentary historical case study from a fully testable historical signal path.

### 10.7 Saved investigations and watch conditions

Reuse the existing Investigation and Saved owners. A saved object should retain selected markets/instruments, comparison basis, evidence snapshot, thesis, counterevidence, user-defined conditions and last-reviewed version. It should explain what changed when opened against a newer snapshot.

Watch conditions use the existing alert lifecycle: first observation, qualification, persistence, escalation, acknowledgement, resolution and revision. Missing data pauses an evaluation or changes its coverage state; it cannot silently resolve an active watch. Group related updates into one evolving event to avoid alert fatigue.

The Paper buttons express this intended workflow. They do not establish that the unfinished IM08/IM09 integration is already implemented.

### 10.8 Evidence-grounded briefings

AI may summarize a deterministic, qualified evidence package and help the user formulate research questions. Require supporting links, the most material caveat and an alternative explanation. Keep the glance brief short; place methods and numerical diagnostics in the study layer.

AI must not invent observations, assign graph weights, alter thresholds, create causal certainty, change a score or initiate a trade. The same underlying event must retain its evidence identity across International Markets, a country page and US Risk Radar, avoiding three apparent confirmations derived from one observation.

### 10.9 Six end-to-end acceptance journeys

1. **Global discovery:** scanner → unusual EM market → local/FX decomposition → evidence → saved research.
2. **US contagion investigation:** source stress → documented channel → eligible US response → existing recipient research.
3. **Policy depth:** scanner market → R12 country cockpit → qualified forecast/policy comparison → same saved comparison.
4. **Dislocation challenge:** unusual return → peer/factor explanation → liquidity and credit counterevidence → thesis-change condition.
5. **What changed:** saved thesis → new publication/revision → evidence diff → retained original record.
6. **Degraded operation:** missing credit/funding → clear unavailable conclusion → working equity/FX and unaffected research → qualified recovery.

---

## 11. Validation and model authority

### 11.1 Retain the single promotion door

The existing [intl_feed.py](https://github.com/mastermindx-market-intelligence/macro/blob/90eb4df175c009b770303dee417eb09aef1a63b4/engine/intl_feed.py) reads the established bridge ledger emitted by the existing phase-zero process. It is the only route from this domain into sizing/derisk authority. Context, pending, killed, stale or missing inputs do not gain action weight through a new dashboard.

No new page, model score or AI narrative may create an alternative promotion register. A changed basket or feature definition is a new candidate, with a version and requalification; it is not a cosmetic expansion.

### 11.2 Research protocol

Before evaluating a candidate, freeze the hypothesis, target, eligible population, features, horizon, baseline, event definition, parameter search budget and intended decision use. Use point-in-time walk-forward testing, leakage checks and a genuinely held-out period or episode set.

Report independent episodes rather than inflating the sample with overlapping daily warnings. Preserve failed, suspended, inaccessible and delisted markets where the research question requires them. Publish missing cohorts and selection effects before presenting a global average.

Use simple baselines: own-history stress, regional breadth, broad USD, US credit and the existing model. A complex graph should demonstrate incremental usefulness over those baselines, not just an attractive in-sample fit.

### 11.3 What to measure

| Claim type | Appropriate evidence |
|---|---|
| Descriptive anomaly | Reproducible calculation, endpoint integrity, stability, factor/peer transparency and data-quality controls |
| Risk warning | Episode precision/recall, false-alert burden, lead-time distribution, persistence and usefulness for the declared decision |
| Probability forecast | Reliability/calibration, proper scoring rules, uncertainty and sufficient eligible sample |
| Directional propagation | Session-aware timing, common-factor alternatives, model stability and robust event evidence |
| Trade or sizing value | Existing promotion constitution, economic costs, execution/access constraints and explicit authorized action scope |

Uncalibrated scores must not be displayed as probabilities. Missing data, short history and unstable parameters should trigger abstention or reduced claim scope. Severity, confidence, coverage and calibration are distinct fields; a high-severity event can have incomplete evidence, and a precise observation can describe a small event.

### 11.4 Independent review

Separate data-contract review, numerical/model review, product/design review and served-path verification. A model can pass its arithmetic tests and still fail the user-facing conclusion. Reviewers should challenge whether the proposed output answers the actual US-risk and EM-dislocation questions, including current examples that motivated the feature.

No self-awarded “validated” label is permitted. Maintain shadow accrual and compare candidate versus current outputs before any authority change. A visually complete Paper board closes a design task only; it does not qualify the model or ship the feature.

---

## 12. Application integration and operational behavior

### 12.1 Preserve the current product architecture

Implement inside the existing Python/Jinja/CSS/JavaScript International workspace. Reuse its controller, state contract, publication generation, library search, data readers, navigation families and existing component system. No new React shell, independent API service, scheduler or global risk backend is implied by this plan.

The implementation should add small typed projections for global observations, capability coverage, dislocation findings and transmission evidence to the existing publication contract. Proposed field groupings are design requirements, not claims that those schemas already exist. Confirm their exact names and extension points with the incumbent integration owner before coding.

Keep model calculation out of the browser. Keep source collection out of page rendering. A single snapshot identity should bind the brief, rows, dossier, scenario and evidence drawer so a user does not compare mixed generations.

### 12.2 Shared user state

Extend existing route/workspace state with market selection, benchmark/instrument selection, peer group, horizon, return basis, aligned/latest mode, channel and snapshot selection. Use backward-compatible aliases for existing country keys and hashes. Retain language/theme and return focus on navigation.

The existing /intl_stocks.html mode and country routes remain reachable. The new market dossier must not assume that the stocks owner already supports every new market filter; capabilities must be negotiated and visibly qualified.

### 12.3 Performance

The observed 3 MB HTML and exposed alternative panels justify a rendering audit. Do not server-render every market, horizon, currency and study panel into the initial document. Publish a compact default view, load authorized detail through the existing architecture, and reuse shared assets.

Establish measured budgets for initial HTML, critical assets, data payloads, interaction latency and memory before freezing an implementation target. Evaluate a full global fixture, not a seven-row fixture. Pagination or virtualization belongs inside the table container; it must preserve keyboard navigation and deterministic ordering.

### 12.4 Failure isolation

| Failure | Required product behavior |
|---|---|
| A daily equity feed is late | Retain the last qualified value with its original session; exclude unsupported current comparisons. |
| A quarterly source has not released a new vintage | Evaluate against that source's release schedule; do not mark it broken merely because it is old in calendar days. |
| Credit source denied / unlicensed | Withhold the affected conclusion and explain the scope. Keep qualified equity/FX research usable. |
| Conflicting source values | Quarantine the affected field or lower its qualification; preserve the disagreement and provenance. |
| Market closed or suspended | Show the status; do not manufacture a current zero return or lower volatility. |
| Source correction | Publish a superseding observation, invalidate dependent derived results and preserve the original research record. |
| One model fails | Withhold that model's output; keep independent evidence and unaffected models available. |
| Entry script or CSS fails | Public/entitled access-safe shell and comprehensible fallback; monitor the served dependency chain, not only the HTML status. |

### 12.5 Access and publication

Treat public static assets, public product copy, entitled derived data and raw source payloads as separate rights questions. The exact existing access policy remains authoritative. Audit transitive imports and embedded data before making a static asset public.

Acceptance requires correct response status, content type, intended access behavior and actual browser initialization. Test anonymous and entitled paths, direct deep links and cache behavior. A cached authentication response must not become a public stylesheet; a public shell must not embed restricted data merely to avoid an API gate.

The normal publisher must reproduce the accepted result on a subsequent run. A manually repaired site artifact that disappears at the next publication is not a completed repair.

---

## 13. Paper design and engineering handoff

### 13.1 What was actually changed

The existing International Markets file was located and inspected. A new **Global Surveillance · R13 · Expansion** page was created in that same file, with twelve editable artboards. The R12 country-cockpit boards and existing programme pages were preserved, avoiding a collision with the unfinished implementation reference.

| Board | Paper node | Purpose |
|---|---|---|
| Global scanner · desktop dark EN | EZ1-0 | Worldwide discovery, local/FX/USD comparison, attention rail and capability counts |
| Global scanner · desktop light EN | FNH-0 | White research surfaces, neutral table structure and restrained depth |
| Global scanner · desktop dark ZH | FUM-0 | Native Chinese copy and correct direction-color convention |
| Global scanner · desktop light ZH | FZY-0 | Chinese layout and accessible light financial inks |
| Dislocation explorer · desktop | F4Y-0 | Price anomaly versus vulnerability; selected-market explanation and research continuation |
| Transmission to US · desktop | F93-0 | Origin, exposure and recipient evidence separated; frozen-model scope visible |
| EM market dossier · desktop | FCL-0 | Market identity, local/FX/USD chart, credit/funding coverage and country research continuation |
| Global scanner · mobile dark EN | FG7-0 | A deliberately reduced 390px research journey |
| Global scanner · mobile light EN | FST-0 | White reading surface, corrected system-icon contrast |
| Global scanner · mobile dark ZH | G5A-0 | Chinese mobile copy and direction/health separation |
| Global scanner · mobile light ZH | G73-0 | Chinese light mobile reference |
| Coverage and partial data · light | FIB-0 | Simultaneous healthy, dated, missing and paused states; preserved saved thesis |

Open the [R13 Paper page](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-H-0). All quoted market moves, pressures, counts and classifications shown as scenario content are **illustrative design data**, not current investment findings. The 63-jurisdiction scope is a proposal; the displayed qualified counts are examples of how coverage should be communicated.

### 13.2 Design decisions

**Dark treatment:** existing Macro graphite surfaces, luminance hierarchy, restrained blue wayfinding, neutral dividers and semantic financial ink. The global answer sits above a bounded table and a narrower research rail.

**Light treatment:** cool canvas with explicit white research surfaces, even hairlines, inset table controls and subtle local shadows. The coverage screen is designed as an evidence-reading workspace. It is not a dark screenshot with its background inverted.

**Typography:** Inter for the English/numeric system; PingFang SC for Chinese copy. Chinese tracking is removed. Signed return direction flips between English and Chinese conventions; warning/health meaning does not flip.

**Selection and status:** selected tabs use quiet neutral fills and stronger text. Decorative colored container edges were removed in accordance with current house law. Status is labeled in text, with color as additional meaning.

**Disclosure:** the scanner uses plain anomaly labels. Residual statistics and methodological details belong in the Dislocation study view. The mobile view retains the qualifiers that change interpretation: basis, session, coverage and corroboration status.

**Unknowns:** Poland is explicitly unscored in the vulnerability map when credit/funding evidence is insufficient. A stable spot FX reading does not grant a dollar-risk verdict. A paused credit condition preserves the saved thesis.

### 13.3 Visual checks performed

Actual Paper screenshots were inspected while building each core screen and across the eight scanner theme/language/device variants. Corrections included inherited text contrast, neutral selection treatment, light status icons, Chinese headline balance, Chinese typography, financial-direction colors, missing-data placement and the synthetic chart's endpoint/window consistency. Relevant JSX/styles were read for the scanner, mobile reference and chart.

This is visual reference evidence, not a running implementation, accessibility certification, independent product acceptance or release approval. Keyboard behavior, screen-reader semantics, 320px/200% text behavior, full deeper-view localization, all degraded states and production-shaped data require implementation review before those packets can be frozen for release.

### 13.4 Component mapping

| R13 element | Existing implementation home |
|---|---|
| Product shell and global navigation | Existing _site_nav.html.j2 / _navlinks.html.j2 family; do not paste a third navigation shell from exported JSX |
| Page answer and section headers | Existing design-system verdict/section primitives, with plain-language budgets |
| Scanner / coverage matrices | Existing table and row primitives, in-container overflow and bounded initial rows |
| Controls and task tabs | Existing workspace state, task tabset and segmented controls |
| Freshness and qualification | Existing .dtp status/as-of vocabulary and qualified source projection |
| Evidence details | Existing LENS disclosures and inspector/evidence contract, reachable by touch and keyboard |
| Time-series illustration | Existing lib/illus.py plus illus CSS/JS in the implementation; preserve exact chart data and null semantics |
| Dossier and country depth | Existing inspector, country-cockpit and country-route owners |
| Saved research / watch condition | Existing Investigation/Saved/alerts owners after IM08/IM09 dependencies resolve |
| Partial / empty / denied / error | Existing empty-state and tier/access primitives, scoped to affected capabilities |

Paper-exported JSX is a visual starting point. It is not production architecture and should not replace governed components or source contracts.

### 13.5 State matrix for builders

For every new capability, specify loading, qualified, empty, partial, delayed/stale, closed, suspended, denied, corrected and recovered states. A loading skeleton is not an empty conclusion. “No unusual move” requires enough qualified evidence; “no data” cannot use the same state.

All new runtime screens need dark/light × EN/ZH × desktop/mobile evidence. Extend the incumbent 320px, focus, keyboard and text-expansion checks where the changed geometry makes them relevant. Reuse unchanged accepted evidence; do not rerun the entire programme merely because a new planning document exists.

---

## 14. Hard acceptance tests

These tests define the architecture more precisely than a list of features. They are proposed acceptance obligations for implementation, not tests executed during this design commission.

| Test | Required result |
|---|---|
| Frozen-universe invariance | Add a scanner market; the existing seven-country calculations, fixed 14-ETF model and fixed 11-market graph remain unchanged for identical inputs. |
| Coverage vector | Equity/FX-qualified, credit-missing markets remain visible but receive no reassuring comprehensive risk verdict. |
| Denominator integrity | Removing a source or entitlement cannot increase target-universe coverage. Adding a country benchmark cannot silently count all of that jurisdiction’s constituents as directly observed. |
| Graph boundary | An out-of-graph market displays structural research or a qualified candidate label, never an invented graph score. |
| Stable aggregate meaning | Adding a distressed small market cannot mechanically change existing US Risk Radar outputs or the meaning of a global aggregate. |
| Session cutoff integrity | A market that has not had an eligible post-event session is “pending,” not non-confirming or resilient. |
| Return identity | +5% local equity with −10% FX produces −5.5% USD; price/total/hedged bases cannot mix. |
| Closure/suspension honesty | Non-trading produces a dated retained observation and status, not a current zero or an improvement in risk. |
| Common-shock counterexample | A global rates shock followed by simultaneous EM/US weakness cannot be labeled EM-to-US causality from correlation alone. |
| Dollar-risk counterexample | A stable peg with missing funding data cannot be declared safe; a depreciation alone cannot be called a dollar funding crisis. |
| Opportunity/fragility coexistence | An extreme dislocation can coexist with worsening credit/liquidity; no automatic “best entry” or bottom call is created. |
| Missing-data non-improvement | Removing a stressed qualified input reduces coverage or withholds the assessment; it cannot make the displayed risk improve silently. |
| Point-in-time replay | Future revisions, later-acquired data, surviving constituents and later classifications cannot improve an old warning retrospectively. |
| Cross-surface consistency | The same event retains its evidence identity, first-qualified time, revision and meaning across International, country and US research. |
| Proxy honesty | Regional OAS, ETF returns and inferred flow regimes remain labeled by their actual populations and methods. |
| Correction propagation | A corrected source invalidates dependent results and creates a visible revision without erasing the original saved evidence. |
| Rights isolation | Public static assets load as intended; denied raw or entitled data remains denied under negative access tests. |
| Served-path proof | Actual anonymous and entitled browsers initialize, navigate and preserve state on the served URL; HTTP 200 alone fails. |
| Publication retention | The normal subsequent publisher preserves the accepted feature and its source qualification. |
| Legacy continuity | All ten existing views, 18 tool families, stocks mode and country routes remain reachable with state preserved. |
| Bilingual/theme semantics | Signed market direction follows locale convention; severity does not flip; labels and critical qualifiers survive both themes and narrow layouts. |

### Review evidence required

For each package, record the exact source revision, changed contracts, data fixture/snapshot, test commands/results, independent review scope, visual evidence identity, served-path proof where applicable, remaining limitations and the next normal publication result. Keep a reported owner pass distinct from a pass independently observed in this session.

---

## 15. Implementation roadmap

The following labels are proposed work packages within the existing programme. They are not new workstreams, workers, leases or grants. The incumbent integration owner should adopt the dependency graph and exact source boundaries before assigning implementation.

### Wave 0 — restore and reconcile the current International workspace

**Outcome:** a functioning existing page, with the correct access contract and a single reconciled source baseline.

1. Re-read the exact incumbent PR heads and their current holds before any source effect.
2. Reconcile #9596's nine-asset access candidate with the existing policy and negative data-access gates. Audit imports and embedded content; preserve private data boundaries.
3. Resolve the #9596 failed checks only through permitted diagnostics. Do not assert that asset access explains the four failed CI packs without evidence.
4. Preserve #8754's egress hold and source custody. Obtain its owner's release condition through the existing path; do not use another reader, push or rerun as a workaround.
5. Compare accepted module blobs and receipts across the old workspace, current main and the cockpit candidate. Do not blindly replay two overlapping PR histories or rebuild accepted numerical leaves.
6. Complete remaining source/FX qualification through the existing acquisition owner, including the incumbent full-depth intl_prices backfill requirement where still applicable.
7. Verify the intended anonymous and entitled journeys, all current destinations, EN/ZH, both themes, narrow layouts and independent data clocks on the actual served candidate.
8. Verify one subsequent normal publication. Retain rollback to the last accepted source/snapshot through the normal release lane.

**Exit gate:** current workspace release acceptance, not a Paper screenshot or a local test report. R13 research/design can progress independently while this lane remains held.

### Wave 1 — global identity, scope and source qualification

**Proposed package IM11: Global market coverage contract.** Extend the existing identity/ontology relationships, versioned classification, venue/session metadata, benchmark mappings and capability vector. Produce the 63-jurisdiction roster plus material venue/segment additions and explicit exclusions.

**Proposed package IM12: Qualified global observations.** Extend existing source adapters, rights records, observation clocks and history qualification. Establish daily equity/FX coverage first; document gaps in credit, breadth, funding and macro separately.

**Dependencies:** exact incumbent interfaces; source rights; maintained calendars; publication contract.  
**Exit gate:** the materiality census is reproducible; no claimed covered market is merely an all-null placeholder; all eligible comparisons reconcile and unsupported capabilities remain explicit. Initial partial releases must be named as partial coverage.

### Wave 2 — worldwide scanner and market continuation

**Proposed package IM13: Global scanner and session comparisons.** Implement the R13 entry journey, filters, local/FX/USD basis, aligned/latest modes, coverage drawer and evidence-bound attention queue through the existing workspace controller.

**Proposed package IM14: Market dossier and existing country/stock continuation.** Extend the inspector and country/stock routes with exact instrument identity, source clocks, price/FX decomposition and coverage-specific context. Preserve R12 policy depth.

**Dependencies:** IM11/IM12, existing IM00–IM03/IM07 interfaces.  
**Exit gate:** the discovery → selected market → decomposition → evidence segment and the independent degraded-data segment pass on production-shaped fixtures and served routes. Existing Saved functionality may be used only where its accepted IM08/IM09 capability is already available; otherwise the unavailable continuation is explicit. The complete discovery → Saved journey remains a Wave 5 acceptance obligation. All old destinations survive, changed route/state contracts remain backward compatible, and the fixed existing models remain numerically invariant.

### Wave 3 — dislocations, EM credit and dollar context

**Proposed package IM15: Dislocation research.** Add transparent own-history and peer comparisons first, then a preregistered factor-residual candidate. Keep anomaly and vulnerability independent. Include counterevidence and instrument/session caveats.

**Proposed package IM16: EM credit and external-dollar context.** Reuse existing fast/slow risk modules; broaden qualified sovereign/regional credit, funding context, external vulnerability and refinancing coverage where sources permit. Dossier gaps must remain honest.

Before freezing IM16, the programme owner must adopt a **market-by-capability acceptance matrix**. It must identify the markets and regional systems requiring qualified credit, dollar/funding, external-vulnerability and US-exposure coverage; the permitted direct or proxy measures for each claim; and which gaps prevent completion. A proxy can satisfy a requirement only at its actual population and interpretation. Missing data remains visible but does not fulfill a mandatory capability.

Mandatory practical demonstrations must include an EM credit investigation and a dollar-pressure investigation that connect qualified source observations, documented exposure or vulnerability, eligible recipient evidence and an explicit alternative explanation. Synthetic design values and all-unavailable fields cannot satisfy these demonstrations.

**Dependencies:** qualified histories, composition/adjustment data, rights for required credit/funding series, existing IM04/IM05 contracts.  
**Exit gate:** descriptive findings reproduce; coverage and proxy boundaries pass adversarial cases; user-facing claims remain within their qualified scope. A missing licensed data source cannot be replaced by an unlabeled proxy.

### Wave 4 — exposure pathways and US relevance

**Proposed package IM17: Typed transmission evidence and US exposure.** Connect source stress, measured/documented exposures and eligible receiver evidence using the existing graph, company, sector and risk owners. Preserve common-factor alternatives.

Start with structural research and current observations. Keep the old graph frozen. Broader statistical networks run as separately versioned candidates in the existing research/validation system.

**Dependencies:** exposure source qualification; event-time calendars; existing contagion/state and company identity interfaces.  
**Exit gate:** the source→channel→receiver journey works without causal overclaiming or duplicated corroboration. Markets outside the accepted graph remain explicitly outside it.

### Wave 5 — evidence-bound research loop and model qualification

**Proposed package IM18: Replay, saved investigations and watch lifecycle.** Complete through existing IM06/IM08/IM09 owners: scenario persistence, evidence diffs, correction propagation, watch-condition evaluation and history/replay.

Qualify any new risk or predictive claim separately. Freeze hypotheses and evaluation budgets; retain simple baselines; accrue forward evidence; obtain independent model/conclusion review. Only the existing promotion bridge can change action authority.

**Dependencies:** incumbent Investigation/Saved custody, historical availability metadata and qualified candidate models.  
**Exit gate:** the complete six-journey matrix passes, watch conditions handle missing/corrected evidence, normal publication retains the result, and any stronger model claim has its own acceptance record.

### Recommended sequencing inside the universe

Source qualification should begin with all existing seven markets and currently modeled world-context nodes, then close the largest observational holes: major Latin American, Southeast Asian, Middle Eastern, African and European markets. Prioritize by materiality, source readiness and US/external-credit relevance, not by a current market prediction made from this design exercise.

Broad daily coverage and deep country research should proceed on separate schedules. The programme should not wait for dozens of fully written policy dossiers before making qualified major-market observations available.

### Ownership and review map

| Boundary | Existing owner to reuse | Required evidence |
|---|---|---|
| Programme priority and source integration | International programme / incumbent integration writer | Current source custody, dependency and overlap reconciliation |
| Source acquisition and rights | Existing data/source owners | Provider rights, successful writes, provenance and collection budget |
| Identity / venue / geography | Existing identity/ontology and calendar owners | Versioned mappings, effective dates and compatibility |
| Descriptive calculations | Existing International engine owners | Deterministic numerical and missing-data tests |
| Model claims / action promotion | Existing validation harness and intl bridge | Preregistration, review, forward evidence and explicit promotion |
| UX / page composition | Existing design system and International controller | Component mapping, theme/language/device evidence and real journeys |
| Investigation / Saved / alerts | Existing Terminal/Saved/IW2 and alert owners | Same-record integration, custody and lifecycle compatibility |
| Release / access / publication | Existing site access and normal publisher owners | Exact-candidate checks, served rights proof and subsequent publication |

This map names system boundaries, not live sessions to invent or hunt for. Assign concrete work only through the current admitted owner path.

---

## 16. Success measures and operating economics

### Product and evidence outcomes

Measure the proportion of material markets with qualified equity/FX observations; the capitalization/turnover denominator actually covered; credit/funding/breadth depth separately; freshness against source schedules; the share of research findings with a complete evidence chain; time from discovery to a useful dossier; saved-thesis review completion; and false or redundant watch burden.

For transmission research, measure how often the product correctly distinguishes source stress, shared factors, pending US sessions, incomplete channels and genuine corroboration. More warnings are not automatically better.

### Performance and cost

The daily benchmark layer is relatively modest compared with full constituent histories. For capacity planning only, 100 benchmark series over ten years at roughly 250 sessions per year is about 250,000 price observations before revisions and auxiliary fields. Tens of thousands of constituent series can be orders of magnitude larger. This is an illustrative sizing model, not a measurement of current storage.

The first bottlenecks are likely to be source rights, identity consistency, time alignment and model validity. Profile collection, publication and UI behavior before adding services or buying compute. Reuse existing schedules and storage, cache qualified projections, and avoid recalculating the same statistics per page view.

Track source cost and coverage value by capability. A licensed credit/funding feed may unlock a meaningful risk conclusion; another redundant price source may add little. Procurement should be tied to the explicit gaps users encounter, with an agreed budget and rights review at that implementation step.

### Programme completion definition

The expansion is complete only when the independently defined market census satisfies its declared observational coverage standard; the adopted market-by-capability matrix satisfies its mandatory credit, dollar, vulnerability and exposure requirements; all six complete journeys work on the served site; current source, rights and quality claims are truthful; legacy capabilities remain reachable; and the next normal publication preserves the accepted state. Residual nonmandatory gaps remain disclosed. A truthful partial release is valuable, but must retain a partial capability disposition rather than close the global-risk programme.

The design commission is complete when the consolidated plan and editable reference are delivered and verified. These are distinct acceptance boundaries.

---

## 17. Decisions, assumptions and unresolved implementation facts

### Recommended decisions

- Global discovery becomes the entry layer; country research remains the depth layer.
- Coverage is capability-specific and session-aware.
- The initial planning roster is 63 jurisdictions plus material venue/segment additions; it is not a cap.
- Classification is provider- and date-specific.
- Existing frozen models and promotion authority remain unchanged by coverage expansion.
- Dislocation and vulnerability are separate; observed stress and causal transmission are separate.
- Existing workspace, source, identity, Saved, alerts and publication owners are reused.
- Current page restoration precedes any claim that R13 has reached production.

### Facts still requiring implementation discovery

| Open fact | Why it matters | Next action |
|---|---|---|
| Exact current disposition of #9596 and #8754 at implementation start | Heads and holds can change after this dated census. | Re-read incumbent metadata/checkpoint; preserve custody. |
| Root causes of #9596's failed CI packs | The observed failure is not a diagnosis. | Use only admitted diagnostics through the owner. |
| Restored admission for the held #8754 hosted-log path | An explicit refusal cannot be worked around. | Existing owner establishes the permitted release condition; no probing from this plan. |
| Current identity/calendar extension interfaces | No global registry or exchange-calendar implementation was proven by this census. | Reconcile existing owners before naming concrete new modules. |
| Exact source rights and qualified histories for the expanded universe | Existing EOD rights do not imply universal coverage. | Build the instrument/source/rights matrix and test acquisition. |
| Complete global market-cap/turnover denominator | “Every major” needs a reproducible measurement. | Obtain a permitted source, define de-duplication and record vintage. |
| Qualified country credit, basis and maturity data | Some advanced EM conclusions require data that the current public/proxy layer cannot supply. | Keep gaps explicit; evaluate licensed/official alternatives against capability value. |
| Exact Saved/Investigation cutover state | IM08/IM09 remain incumbent-owned and unfinished. | Integrate through that owner; do not duplicate the store. |
| Predictive value of any expanded model | No new global warning or timing model was validated here. | Preregister, test, shadow and independently review through the existing constitution. |

None of these unknowns prevents the planning/design work delivered here. They do prevent stronger claims about production readiness or globally validated risk intelligence.

---

## 18. Evidence index and completion record

### Source evidence

The census used pinned Macro source, the two existing PRs, the incumbent host checkpoint, current Paper file/page reads, a real browser and bounded anonymous HTTP checks. Historical masterplan claims were treated as historical; code presence was not treated as live source health. No prohibited #8754 logs/artifacts were retrieved, and no release/CI rerun was initiated.

Primary external sources used for architecture and data semantics:

1. [MSCI market classification](https://www.msci.com/indexes/index-resources/market-classification) — provider taxonomy and classification criteria.
2. [MSCI ACWI September 2026 factsheet](https://www.msci.com/documents/10199/255599/msci-acwi.pdf) — 23 developed / 24 emerging core roster.
3. [FTSE October 2026 market classification matrix](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/country-classification/matrix-of-markets.pdf) — alternative provider classifications and effective changes.
4. [ISO MIC register](https://www.iso20022.org/market-identifier-codes) — venue identifiers and effective publication metadata.
5. [WFE statistics](https://www.world-exchanges.org/our-work/statistics) — market-statistics scope, venue factsheets and use restrictions.
6. [BIS global liquidity indicators](https://data.bis.org/topics/GLI) — foreign-currency credit and quarterly context.
7. [BIS consolidated banking statistics](https://data.bis.org/topics/CBS) — consolidated banking exposure definitions.
8. [IMF Portfolio Investment Positions by Counterpart Economy](https://data.imf.org/en/datasets/IMF.STA:PIP) — portfolio positions, not daily flows.
9. [BIS debt service ratios](https://data.bis.org/topics/DSR) — quarterly methodology and cross-country interpretation limits.
10. [New York Fed central-bank swap operations](https://www.newyorkfed.org/markets/desk-operations/central-bank-liquidity-swap-operations) — operations, weekly publication when conducted, and operational-readiness exercises.
11. [Forbes and Rigobon, Journal of Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00494) — caution about correlation-based contagion inference under changing volatility.

### Delivered in this commission

- Dated census of the current product, model populations, legacy tools, unfinished implementation and served asset failure.
- Consolidated masterplan with explicit prior-plan crosswalk, worldwide scope, contracts, mechanisms, user journeys, validation, rollout and acceptance.
- Twelve editable Paper boards in the existing International file, including the complete eight-way scanner reference matrix and four deeper workflow/state designs.
- Actual visual inspection and targeted corrections of those references.
- A principal architecture and conclusion review of the full planning document, with denominator integrity, mandatory credit/dollar capability gates, Saved sequencing and causal-language corrections incorporated. This review assessed the plan; it did not independently verify external sources, inspect Paper or accept production implementation.

### Not represented as completed

- Repair, merge, deployment or acceptance of either incumbent PR.
- A production global feed, newly licensed data source or full 63-jurisdiction risk capability.
- A qualified new global contagion, probability, timing or sizing model.
- Final runtime accessibility, all deeper-view language/device variants or independent production design acceptance.
- A new background watcher, service, external notification or scheduled automation.

**Next implementation act:** reconcile the incumbent release frontier and asset-access repair, then adopt IM11/IM12 contracts and the source-rights matrix under the existing programme. The R13 page is the editable expansion reference; R12 remains the country-depth reference.

**Completion boundary:** planning and editable-design outcome delivered; production implementation remains the staged programme described above.

