# Commission 16 — Operational Alternative Data Adapters
## Hardened research commission and implementation masterplan

**Version:** 2.0, 4 October 2026 (UTC).  
**Disposition:** research complete; implementation recommendation only.  
**Mandate:** establish a defensible, point-in-time operational-sensor program for MastermindX.  
**Scope boundary:** this report grants no procurement, production, deployment, portfolio, trading, or source-decision authority. Its follow-on commission in Section L is proposed and unexecuted.

**Decision:** build a small, auditable route from operational observations to explicitly defined company KPIs. Admit one source and one KPI bridge at a time. Prove temporal lineage before forecasting, measure forecasting value before claiming expectation information, and test investment usefulness separately. The first implementation should establish one real source replay and a registered study, not a general alternative-data warehouse.

This report replaces the recommendations in the supplied 62,820-byte report, SHA-256 c76c42dd8b0feeaad09183dee3261c492ac0f6ced41ae24fc9720a5dfda4d310. It does not supersede canonical repository law or ratify proposed engineering work. The supplied report's central measurement-first thesis survives; its current-state census, source diligence, temporal semantics, prioritization, and empirical acceptance rules required material revision.

### Reading and evidence conventions

Sections A–L form the complete commission. The companion [current-estate census](COMMISSION_16_CURRENT_ESTATE_CENSUS_2026-10-04.md) contains detailed Macro/Terminal evidence; [source diligence](COMMISSION_16_SOURCE_DILIGENCE_2026-10-04.md) separates vendor documentation from unverified entitlements; the [hardening audit](COMMISSION_16_HARDENING_AUDIT_2026-10-04.md) records corrections and completion checks.

Repository citations use immutable commit permalinks. Public-source citations identify official documentation, regulator material, issuer disclosures, or primary research, accessed on 4 October 2026. A documented vendor feature is not evidence that Mastermind licenses it, that a sample passed inspection, or that its predictive claims are independently true. No commercial dataset, customer contract, paid trial, production process, or historical backtest was executed for this commission.

The evidence rungs are distinct: **specified → code present → committed data present → observed acquisition → observed consumption → empirically validated → separately authorized**. This research establishes only the rung stated for each finding. Negative search results are bounded to the repositories, trees, files, and candidate carriers inspected.

# A. Executive conclusion

## A1. What to build

Mastermind should add **KPI-specific operational evidence** to its existing data and research system. Each accepted sensor should answer a concrete question such as “Are comparable restaurant transactions accelerating?” or “Is measured app activity consistent with reported user growth?” It should preserve the measured quantity, coverage, causal/accounting bridge, available vintage, uncertainty, and dependence on other evidence.

The useful chain is:

**source-native observation → historically valid economic exposure → reproducible feature → calibrated KPI forecast → same-scope expectation comparison → existing research and outcome owners.**

The output is an inspectable collection of observations and forecasts. A merchant-sales estimate, hiring composition, app activity, and port throughput must not disappear into one “alt-data strength” number. Nor should a vendor logo count as an independent vote. This is important infrastructure for between-earnings understanding, but predictive and investment value remain unproved until the proposed tests run.

## A2. What changed in the hardening

The recensus materially changes the starting point. Macro already has DOL hiring-intent and Census trade-flow producers; both are adjacent to this commission, although neither is a mature company-level operational nowcast. The committed trade-flow artifact reports no available underlying data. Mastermind already has an earnings-expectation **risk** lane, while V3 Decision Snapshot and evidence-fusion concepts remain specified rather than demonstrated implementations. Current alternative-data outcomes also contain more observations than the attachment's historical August cohort, but their authority evaluation still fails eligibility and explicitly separates clock vintages. [R03][R06][R10][R11][R16]

The research found source-specific hazards that a generic “PIT” flag would hide. Similarweb documents historical model reruns; Earnest documents a later panel expansion with earlier-dated backfill; Facteus documents a retrospective pro-forma merchant grouping; Revelio distinguishes its default retrospective corporate hierarchy from a PIT alternative. Sensor Tower advertises a PIT Scheduled Data Feed, making it a stronger diligence candidate, but the actual vintage scope is not verified. Kpler documents both dated snapshots and short-retention change feeds; these are different capabilities. [W01][W02][W03][W04][W05][W06][W07][W08]

The empirical program now distinguishes measurement feasibility, actual available information, conditional forecast value, and stock-return utility. It also distinguishes a valid but underpowered study from a failed source. Engineering completion cannot depend on future earnings outcomes that have not happened.

## A3. Prioritized recommendation

| Priority | Recommended action | Reason and boundary |
|---|---|---|
| **P0** | Reconcile existing owners; define the source/KPI admission record; prove one real, authorized provenance and revision replay. | Current lineage, availability, and consumption uncertainty would invalidate a larger program. No purchase is implied. |
| **P1, conditional** | Merchant payments → a narrowly defined restaurant sales KPI. Start issuer diligence with CMG and register a comparable cohort before inference. | Short measurement-to-KPI distance; transaction/check decomposition is economically interpretable. Facteus Arbiter and Earnest Orion are diligence candidates, not approved purchases. |
| **P1, conditional** | Digital usage → reported users, starting issuer diligence with DUOL. | Better target than treating ratings or downloads as revenue. Sensor Tower's documented PIT offer is worth testing. |
| **P1 for a semiconductor mandate** | Establish a receipt-backed issuer monthly-KPI comparator and reconcile existing TIL/GMI physical evidence. | A lawful reported monthly revenue series can be more relevant than a consumer panel. TSMC monthly disclosure work already appears in adjacent Macro research. |
| **P2** | Add one question-specific sensor: matched-location footfall, narrow SKU price/sell-through, hiring capacity, issuer manifests, or commodity throughput. | Each must beat the admitted baseline for its own sector/KPI and justify its cost and maintenance. |
| **Defer / reject** | Broad bundles, generic sensor warehouses, automatic convergence-score admission, proxy-to-revenue arithmetic without a bridge, and historical tests using unproven vintages. | More observations do not establish more usable or independent information. |

These are design priorities based on economic proximity, technical diligence, and existing-system fit. They are not ranked empirical alpha estimates. A source with stronger vintage evidence and a better scoped target can displace a named candidate before procurement.

## A4. Minimum successful first result

A later implementation owner should return one source's lawful, replayable observations; one versioned exposure type; explicit missingness and correction handling; a target definition if supportable; a frozen feature recipe; and a registered benchmark with a future adjudication trigger. Existing reviews, GitHub, or Hugging Face observations can demonstrate provenance. If they cannot support a disclosed KPI, the correct forecast status is **NOT_ESTIMABLE**.

A numerical KPI result is required only after a defensible target and calibration data exist. A predictive-success claim requires actual evaluation. A portfolio change requires a separate authorized decision. This staged contract avoids both premature promotion and the impossible demand that a short engineering task manufacture years of forward labels.

# B. Current-state census

## B1. Source pins and estate identity

| Repository / estate | Branch and immutable revision | Source-status observation |
|---|---|---|
| mastermindx-market-intelligence/Mastermind | master — **521720b09be2921e996d9396b522b1c4ca62041c** | Branch protected=true. Current bootstrap INDEX and governing source-law files were loaded at this same revision. |
| mastermindx-market-intelligence/macro | main — **79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f** | Branch response protected=false. Do not describe this branch as protected. |
| mastermindx-market-intelligence/mastermind-terminal | master — **1c708450187755160e1a5889b69598a2fcb1f0d1** | Branch protected=true. Existing Macro bridge and company-intelligence consumer were inspected. |
| Research Vault | Macro engine/research_vault, app/research.py, and research/RESEARCH_VAULT_MASTERPLAN.md at the Macro pin | Repository inventory and code resolve the estate here. The separate executive-dr-vault repository is not a substitute identity for this product. |

**Publication recheck:** Macro main advanced to **59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc**, a direct child of the census pin. Its only changed files are the Trend Persistence workstream and October 4 handoff. The inspected sensor code, contracts and committed artifacts are unchanged; the older immutable links remain valid evidence for those findings. Mastermind and Terminal heads were unchanged. The new coordination record notes Mastermind PR #1230's Wave C-2 instrument and the existing freeze/one-run constraints; later research must reconcile that incumbent experiment rather than duplicate it. [R34]

The original commission header's d1594f3c7ae750db3f14b4eebf0de3460f84267a was treated as historical context. This census uses current retrieved pins, not that SHA or the attachment's superseded pins. Branch status is an observation at census time; the report does not assert the runtime deployment SHA equals any branch head.

## B2. What exists and what remains missing

| Capability | Verified current state | Implication for Commission 16 |
|---|---|---|
| Static Mastermind census | data/census/CENSUS.md declares generation on **16 July 2026**, against an older source revision. [R01] | Refresh and generation provenance need attention. This is evidence of a stale checked-in census, not evidence that every source is stale. |
| Broad market/evidence estate | The inspected census and consuming paths contain price/breadth, PIT-oriented fundamentals, options, themes, filings, insider/political/government-contract, ETF/fund, news, and macro context. [R01][R02][R03][R04] | Start from a strong existing baseline. Completeness and current freshness were not audited for every dataset. |
| Existing altdata portfolio row | portfolio/lenses.py builds political/insider/government-contract/affiliation context and existing convergence fallbacks. [R02] | It is not an operating-KPI schema. Do not append unrelated paid sensors to its score. |
| Earnings expectations | portfolio/held_risk.py::_lane_earnings_expectation uses SUE-related state, revisions, and stale checks; it prefers expectation_state and has legacy fallback. [R03] | A real existing risk consumer, not generic nowcast admission. New estimates must not be wired directly into these thresholds. |
| PIT fundamentals and universe | loop/fundamentals.py filters by as-of date; loop/single_name_panel.py supports effective membership spans and deep/delisted panels. [R04][R21] | Reuse the existing mechanisms, while verifying actual filing-release/correction and historical-identity completeness for the chosen target. A filter cannot repair faulty upstream clocks. |
| Historical revisions / dynamic subthemes | Current Trend Persistence research explicitly limits mature historical analyst revisions, fine subtheme identity, and institutional-flow claims. [R05] | Do not fill missing history from current state. Reconcile with Macro GMI's incumbent graph work before proposing any identity extension. |
| Evidence and outcome owners | Trend Persistence names existing predictions, KEEP-FIRST signal history, outcome ledger/outcomes, and shadow paths. [R05] | Extend existing compatible owners. Do not create an operational-sensor outcome ledger in parallel. |
| V3 architecture | The V3 design is SPEC_ONLY and lists important Decision Snapshot, claim, and independence/fusion elements as NOT_BUILT. A corresponding implementation plan exists; the bounded tree/collision audit did not establish the missing implementation. [R06] | Keep this work research-only. Do not invent a V3 owner or delay all useful provenance work until the entire V3 program exists. |
| Research desk and bottlenecks | Research desk already handles research/proposals and lagged holdings context. Bottleneck code uses relative-strength baskets to identify chain layers. [R07][R22] | Reuse research consumption; basket relative strength is not a measurement of physical scarcity. |
| Macro mounting / snapshots | macro_refresh distinguishes production symlink use from managed dev/DR source copies. bridge/macro_snapshot is a static public portfolio export. [R08][R23] | Do not call every installation a managed sparse checkout or confuse this bridge with a V3 Decision Snapshot. |
| App demand | Current rule uses ratings ≥4.3 and review count ≥1,000; review velocity is display-only. [R09] | Ratings/reviews are neither active users nor downloads nor revenue. Keep separate from a future app-usage family. |
| DOL hiring intent | LCA/PERM collector, employer resolver, and TIL W7 transform already exist; certification velocity, AI-title share, wage change are display context. Output contracts have no consumers; the inspected committed hiring artifact is absent. [R10][R24][R25] | Existing adjacent owner; not broad daily vacancies or realized hires. Decision dates precede public disclosure and cannot alone serve as availability dates. |
| Trade flows | Census monthly HS imports feed TIL W8, covering 29 configured codes and 11 themes. The September 30 committed artifact reports parquet_absent=true, 0 codes and 0 themes with data. [R11][R26][R27] | Code exists, useful acquisition is unproved. “Neutral” must not override explicit missing-data validity. Aggregate imports are not company manifests. |
| Trade corrections | Collector assumes older monthly data is not revised and does not routinely refetch old months. Official Census documentation describes revisions. [R11][W09] | A concrete source assumption conflicts with primary documentation. A later repair must retain vintages and revise the acquisition policy; this commission changes no collector. |
| Developer observations | GitHub represents a ticker with its highest-star repository; HF uses top models/author and curated issuer mappings. Both keep the last same-day record. [R12][R28] | Cohort composition can change. Existing first-seen fields do not make same-day observations immutable revisions. |
| Generic convergence | Canonical families are event, flow, mid, slow, attention; inspected routing has no altdata_fast. Highest-weight-channel assignment can impose a different family's horizon. [R13] | Keep KPI studies outside generic convergence adjudication. A sensor should not inherit an arbitrary stock horizon through another channel. |
| Terminal and Vault | Terminal already normalizes Macro intelligence with freshness and typed generation lineage. Inspected source kinds are earnings_history, score_overlay, transcript. Vault is third-party-research display, not signal/decision authority. [R17][R30][R31] | Extend compatible typed consumers later. Neither UI nor document storage becomes a second acquisition or decision plane. |

## B3. Current outcome evidence: update the numbers without overstating them

The historical August first-maturity adjudication remains a valid historical record. It is no longer the latest description. The pinned October 3 qledger artifact reports the following descriptive family panels. These are existing-system results, not Commission 16 sensor experiments. [R14][R16]

| Display cohort | Rows | Display dates | Direction hit rate | Mean signed excess return |
|---|---:|---:|---:|---:|
| Event at 21 | 104 | 19 | 48.08% | +0.7771% |
| Flow at 21 | 50 | 14 | 42.00% | −0.8641% |
| Mid at 63 | 22 | 6 | 40.91% | −1.2884% |
| Slow at 63 | 93 | 11 | 35.48% | −2.3153% |

The artifact's authority ladder is different: corrected trading-day event and flow cohorts have **6 and 4 dates**, respectively; mid/slow retain legacy unstamped clocks with 6/11 dates. All relevant eligibility values are false and states are ACCRUING. Mixed-clock panels explicitly refuse pooling. The existing 25-date floor is a policy of that ledger, not a scientifically sufficient sample size for a new KPI experiment. [R16]

A separate convergence artifact's 54.5% “hit rate” measures falsifier survival; its directional accuracy is 41.3%. A separate brain emission is context-only with insufficient eligibility and another calibration ledger. These metrics must not be combined into a claim of validated predictive accuracy. [R15][R29]

Committed October 3 run status says the app/GitHub/HF acquisitions were “ok,” but its rows=1 values describe log entries, not source coverage. Binary parquet objects were identified, not decoded for complete history. The October 4 scheduled run inspected was green while collect, engine, and collect_tail were skipped. No natural source → acquired data → consumed evidence → evaluated decision proof was established. See the companion census for exact receipts. [R32][R33]

## B4. Duplicate work and integration collisions

Existing TIL W7/W8 own hiring/trade context. Existing lib.warn_fuzzy and employer mappings must precede a new company-name matcher. GMI theme-graph work is the adjacent identity, exposure, and correction owner. Macro PRs #8324 and #8417 contain related graph/research readers; #7870 contains a semiconductor proposal. These were open candidate carriers when inspected, not merged capabilities. [R18]

Macro PR #7420 contains an app-demand audit at head de1dfc7093c5170fd53f7f41c6362b612c900769. Its reported row counts, exclusions, and truncation findings are useful collision evidence, but are not proof of canonical issuer identities, live integration, or missed investment opportunities. Terminal #777/#792 concern investigation/research presentation. Reconcile the relevant exact heads before later implementation touches their paths. [R19]

Bounded vendor-name and collector searches did not establish a current card, commercial web, or issuer-manifest adapter. This supports a scoped gap statement, not a claim that no related work exists anywhere. Existing TSMC monthly-disclosure proposals mean the semiconductor comparator is adjacent work to reconcile, not a newly discovered program. [R20]

# C. State of the art and what it implies

## C1. The useful institutional pattern

The public technical evidence supports a modular measurement system, not a universal alternative-data score. Transaction vendors expose merchant and panel measures; digital vendors estimate activity from panels and models; location vendors define geofences and suppression; workforce vendors model late reports and corporate hierarchies; physical-flow vendors maintain changing shipment states. The system must preserve those distinctions. There is no inspected primary evidence that buying all these products creates independent alpha.

The differentiating architecture is the ability to reconstruct **which version of which measurement and exposure was available**, connect it to an explicitly defined reported KPI, and compare it with a strong contemporaneous baseline. FRED versus ALFRED provides a public methodological example of why today's best historical estimate differs from historical knowledge. It is an analogy for design, not certification of a vendor's archive. [W10]

A mature vendor may still sell several different products: latest corrected history, dated events, archived model states, or client-specific receipt history. Each answers a different question. A five-year event history plus a current API is not five years of decision-time evidence.

## C2. Causality, accounting, and prediction are separate

An operational observation may be close to economic activity while still far from reported earnings. A card panel can measure a sample of merchant spend; reported sales also depend on store eligibility, non-card channels, returns, tax treatment, international mix, franchise relationships, and fiscal periods. A measured app session is not a distinct person; users are not paid subscribers; bookings are not recognized revenue. Shipments can precede or follow revenue recognition depending on the transaction.

Accordingly, the causal bridge should specify latent business activity, sampling mechanism, measured proxy, accounting transformation, and disclosed target. The bridge supplies falsifiable restrictions and plausible lags, not proof of a causal effect. A predictive study asks whether the sensor improves forecasts conditional on information already available. A causal study of advertising effectiveness or hiring interventions asks a different question and needs a defensible identification strategy. Adding all correlated controls can change the estimand or introduce bias. [W11]

## C3. Evaluation must acknowledge how financial panels behave

Repeated observations of the same issuer and common calendar shocks create dependent errors. Many daily sensor rows can still correspond to a small number of earnings outcomes. Finance-panel and cluster-inference research motivates issuer/time dependence and caution with few clusters. Multiple-testing research motivates a logged search space and a prespecified confirmatory family. Proper-scoring research motivates predictive-interval quality, including both coverage and sharpness. These sources support the methodology; they do not supply a universal promotion threshold. [W12][W13][W14][W15]

Online-job-posting research provides a plausible association with later corporate performance. It does not establish that every vacancy feed, every posting removal, or every “AI hiring” label measures future revenue. This commission therefore puts nearer capacity/expense targets ahead of a generalized hiring-to-sales model. [W16]

## C4. Competitive advantage to pursue

The defensible advantage is narrower than “more feeds”: better first-release KPI targets, stable economic identities, explicit missingness, correct vintage replay, calibrated uncertainty, and disciplined comparisons against existing information. Source commoditization does not eliminate all usefulness, but it raises the burden on incremental benefit relative to cost and timing.

Operational context can remain useful even when it has no stock alpha—for example, identifying a measurement contradiction that improves research. Such context should be labelled accordingly and must not be promoted through a statistical result from a different sensor or target.

# D. Source landscape

## D1. How to interpret this comparison

“Documented” below means an official source describes the capability. **No commercial entry has passed a licensed sample inspection in this research.** “Unknown” is an unresolved requirement, not a negative finding. History is separated from archived availability. Cost classes are procurement categories: public source with engineering cost, metered/tiered commercial access, or negotiated enterprise license. Exact prices, minimum commitments, retention, and actual Mastermind rights are unknown. No quoted dollar budget would be defensible from the inspected evidence.

The full documentary register and source-specific diligence questions are in the source companion. These tables are the decision summary.

## D2. Consumer and digital sources

| Source | Coverage | History | Latency | PIT quality | Corrections | Rights | Cost class | Best use |
|---|---|---|---|---|---|---|---|---|
| **Facteus Arbiter** [W03] | US merchant payment-panel measures; merchant/entity, spend, transactions, cardholders | Exact start and archived vintages unverified | One-day-source measures and fuller-panel measures differ; validate actual receipt SLA | Not established by public schema | Panel/merchant mapping revisions require samples; retrospective PRO_FORMA must be separated | Actual order needed for storage, automated research, and derived display | Enterprise quote | Restaurant/merchant spend, transactions, average observed ticket |
| **Earnest Orion** [W18][W02] | US credit/debit panel, company/merchant analytics | Advertised 2016 event history; 2023 expansion backfilled prior years | Contract/product dependent | Expanded history is not original 2016 availability | Frozen panel/mapping generations unverified | Actual order required | Enterprise quote | Challenger to the same merchant-KPI benchmark |
| **Similarweb** [W01][W17] | Modeled web activity by domain, geography, product/segment | Metric/package dependent; documented five-year rerun | Daily usually within 72 hours; monthly by the 10th | Current API history is revised; require explicit old-vintage delivery or forward receipts | Version updates can rerun history | API/retention/derivative permissions require order | Commercial tier / enterprise | Web-mediated demand, engagement and funnel components |
| **Sensor Tower** [W05][W06][W56] | App activity, downloads, engagement and estimated monetization by product; digital ads separately | Metric-specific start must be verified | Advertised as little as 24 hours for relevant feeds | PIT Scheduled Data Feed advertised; scope and historical start unverified | Combined panel/model transition in 2025 requires a break analysis | Order-specific feed, retention, hosted computation and display rights | Enterprise quote | Active-use KPI study; strongest explicit digital PIT diligence candidate |
| **Placer** [W19] | Modeled location/POI activity; low-panel limits | Venue and subscription specific | Documented 3–5-day processing | Geofence/model/panel vintages unverified | Venue definitions, model and API/dashboard outputs can differ | Paid account/API permissions; derived use needs confirmation | Enterprise quote | Same-location visits after venue and panel qualification |
| **Facteus Onyx / separate CPG product** [W21][W22] | Retail SKU/brand measures; CPG POS sources are a distinct sampling product | Exact dataset start unverified | Product-specific; file generation is not first availability | Vintage archive unverified | SKU, merchant, panel and product hierarchy revisions | Contract-specific; never inherit ordinary card-feed rights | Enterprise quote | Narrow product sell-through, mix and retailer exposure |
| **Keepa** [W20] | Amazon product prices, availability and ranks | Per-ASIN tracking start, not a uniform universe history | Product refresh varies | Retrieved history alone does not prove past customer availability | ASIN/variation/category/rank definitions and tracking gaps matter | API and permitted derived use require terms review | Metered/tiered commercial | Price/promotion/availability monitoring; rankings as ordinal evidence |

## D3. Labor, developer, and advertising sources

| Source | Coverage | History | Latency | PIT quality | Corrections | Rights | Cost class | Best use |
|---|---|---|---|---|---|---|---|---|
| **DOL LCA/PERM public disclosures** [R10][W37] | Certification cases, employers, occupations and wages | File-specific public history; existing Macro collector | Periodic disclosure, not real-time decisions | Use evidenced file release/receipt, never decision_date alone | Later releases/files may change records; archive file hashes | Public source; respect applicable use and minimize personal fields | Public + engineering | Employer capacity/composition context, not total hiring |
| **Revelio** [W04][W39][W55] | Workforce profiles, roles, postings, modeled flows | Workforce 2008; posting sources differ; unified COSMOS 2021 | Workforce monthly; selected postings daily | PIT hierarchy offered; observation-vintage PIT separately unverified | Late profiles, deduplication, role weights and modeled hires revise | Actual license governs workforce/LLM/retention uses | Enterprise quote | Capacity, skill mix and expense-linked studies |
| **Public employer job boards / Greenhouse API** [W38] | Currently published jobs for known employers | Prospective archive unless historical rights/data proven | Source publication and polling dependent | Can establish actual forward receipts | Jobs edited, duplicated, closed; removal is not a hire | Public GET access does not imply unrestricted reuse of every payload | Public access + engineering | Small employer/role panel for prospective validation |
| **GitHub** [W34][W35][W50] | Public repository interest/activity | New star history is conditioned on stars still active today | API/polling dependent | Forward receipts useful; backfilled star totals are not prior net totals | Unstars, transfers, repo selection and bot activity | Public API terms/limits; no private data entitlement | Public access + engineering | Developer ecosystem interest with an explicit monetization bridge |
| **Hugging Face** [W36] | Public model download-request statistics | Metric/collection specific | Published counters and polling dependent | Preserve forward receipts and selected model universe | Library/query-file rules, model mix and automation affect counts | Hub/API terms; granular owner analytics not competitor-wide permission | Public access + engineering | Model distribution/adoption proxies, not paid inference |
| **Pathmatics / Sensor Tower advertising** [W33] | Observed digital creative/placement and modeled spend/impressions | Platform/metric-specific | Product-dependent | Historical model vintages unverified | Platform coverage, modeled CPM and classification changes | Separate entitlement and retention/display rules | Enterprise quote | Acquisition effort and competitive advertising context |
| **USDA advertised grocery prices** [W48] | Weekly advertised commodity retail prices | Report-specific archive | Weekly | Preserve first published report receipts | Report corrections and commodity definitions need tracking | Public source; verify report-specific restrictions | Public + engineering | Broad price/promotion controls, not issuer realized SKU revenue |

## D4. Trade, logistics, and issuer controls

| Source | Coverage | History | Latency | PIT quality | Corrections | Rights | Cost class | Best use |
|---|---|---|---|---|---|---|---|---|
| **US Census international trade** [W09][W58][W59] | Aggregate commodity/country/port flows, not issuer manifests | Monthly API from 2010; archived releases vary in granularity | Monthly release schedule | Latest API is revised; archive exact release state | Monthly/annual revisions documented | Public data; API conditions and disclosure suppression apply | Public + engineering | Sector physical-flow controls and aggregate reconciliation |
| **Panjiva** [W23][W24] | Country/direction-specific shipment and company data | Global search last five years; underlying country sources can differ | Country/source dependent | Dated shipments are not archived knowledge; vintages unverified | Corrections, master/house duplicates and entity links need samples | Order and restrictive customer agreement govern enrichment/derivatives [W46] | Enterprise quote | Issuer/supplier manifests where legal entity coverage is adequate |
| **ImportGenius** [W25][W26] | Particularly documented US ocean imports; other coverage differs | US plan examples: 12 months versus 2006+ | Dataset dependent | Archived publication/revision states unverified | Corrections and identity availability must be demonstrated | API is plan/add-on specific | Commercial tiers / enterprise API | US import exposure challenger on identical issuer cohort |
| **Descartes Datamyne** [W27][W28] | Company/commodity/country trade products | Analytics rolling two years plus current year; API history must be checked separately | Analytics weekly refresh; API depends on source/product | Historical availability unverified | Correction/version retention unverified | Actual API/order scope controls | Enterprise quote | Alternate company/cargo attribution and coverage comparison |
| **Kpler commodity flows** [W07][W08] | Product, installation and cargo/trade states | Dated snapshot API exists; earliest vintage entitlement unverified | Updates by product; inspect actual delivery | Strongest documented snapshot/change interface in inspected physical-flow shortlist | Change feed retains 15 days of diffs; snapshot retention is a separate question | Contract-specific raw/derived/archive use | Enterprise quote | Commodity loadings, throughput and inventories with issuer exposure |
| **Kpler legacy Spire AIS** [W30][W31][W32] | Vessel messages and positions, not a cargo invoice | Legacy message archive described from 2011; interface dependent | Reception and processing clocks differ | Client receipt remains necessary | Gaps, delayed reception, vessel metadata and deduplication | Current successor entitlement required; old positions endpoint is discontinued | Enterprise quote | Input to physical flow interpretation, not an independent Kpler vote |
| **Issuer disclosures, e.g. TSMC monthly revenue** [W40][W41] | First-party company operating KPI | Issuer archive and definition dependent | Scheduled public disclosure | Strong prospectively with timestamped releases; today's historical table is not a complete vintage archive | Later restatements/currency definitions require separate generations | Public disclosures; source-specific reuse terms apply | Public + engineering | Direct KPI baseline before paid semiconductor proxies |

Manifest identities can be withheld under CBP confidentiality procedures. Missing importer names therefore cannot be interpreted as zero activity. Country counts do not imply equal fields, coverage, or issuer attribution across countries. [W29]

## D5. Required source admission packet

For commercial forecast-source admission, the owner must have a concrete source/KPI decision, not merely a vendor list. An existing-source provenance-only pilot instead needs a declared lawful research use and may retain NOT_ESTIMABLE status. Apply the following requirements to the intended use, with price evidence only where payment applies:

1. The exact product, metric, geography, entity granularity, native identifiers, observed versus modeled status, fiscal/calendar basis, and intended target.
2. A lawful sample with stable record IDs, first publication evidence, actual delivery/receipt, missingness, and method/panel/map versions. Where the source exposes corrections, require source-originated revision and cancellation/tombstone examples before certifying that behavior. Otherwise document the limitation. Synthetic fixtures supplement but cannot prove actual vendor behavior.
3. Separate start dates for events, current reconstructed history, archived source states, and actual client receipts. Explicitly identify which dates are verified and which remain claimed.
4. A coverage report that includes suppressed, unmapped, newly entered, exited, and low-volume entities; a current surviving-company list is insufficient.
5. Where payment applies, an actual price and total-cost quote for the narrow pilot, including history, API/bulk limits, storage, seat restrictions, audit retention and maintenance. No recommendation to buy before this is reviewed.
6. Permissions for internal investment research, raw receipt retention, derived features, model fitting, external-hosted/LLM processing, affiliate/contractor access, displayed evidence, and post-termination reproduction. Each permission needs a contract reference, not one blanket rights flag.
7. Exit options: portable native IDs, export format, retained derived artifacts where allowed, correction replay, and an honest irreproducibility state if lawful retention ends.

The SEC's App Annie matter is a documented example of misleading representations about source inputs and consent. It supports verifying provenance and authorized use; it does not establish misconduct by a current unrelated supplier. This is a diligence design, not legal advice or a finding about any present contract. [W47]

# E. Minimum canonical data model and temporal semantics

## E1. Four conceptual contracts, existing owners

The proposed names below describe logical artifacts. They do not authorize four services, databases, registries, or workstreams. The implementation owner must first map them to current accepted data/evidence contracts and extend those owners only where needed.

| Contract | Minimum useful contents | Design rule |
|---|---|---|
| **operational_observation.v1** | Observation ID; source/product/metric versions; source-native entity and record IDs; measured value/unit or source interval; period; source clock evidence; actual receipt; generation/hash; correction/tombstone link; null state; provenance and license reference | Preserve what the source said before issuer resolution. Never overwrite a raw record merely because a current parent mapping changed. |
| **entity_exposure_map.v1** | Native entity → legal issuer/segment/asset relation; relationship type; valid and knowledge intervals; ownership and economic reporting scope; mapping evidence/version; confidence/ambiguity; separate security links | Implement as an extension or sidecar of the incumbent identity owner, not a competing company graph. |
| **operational_feature_snapshot.v1** | Feature ID/definition/version; forecast origin; input receipt/generation IDs; selected mapping versions; aggregation scope; deterministic code/model artifact hash; training/normalization cutoff; computation/usable times; coverage denominator; validity/abstention state | Reproduce the same value from the same inputs and artifacts. Learned models are allowed if versioned and trained correctly. |
| **kpi_nowcast_evidence.v1** | Forecast ID; issuer and exact KPI definition/version; fiscal period; issued/usable time; model and fit window; first-release target convention; point-forecast functional; predictive interval level/method; baseline forecast IDs; same-scope consensus receipt or null; dependency lineage; authority=context/research only | A forecast is not a source observation, and a forecast difference is not a trading decision. |

Every artifact needs an explicit state such as VALID, UNAVAILABLE, STALE, AMBIGUOUS, METHOD_BREAK, NOT_ESTIMABLE, or REVOKED, with a reason. Source values and generated forecasts must not share one unlabeled numeric column.

## E2. Define every clock

| Field | Meaning | Required behavior |
|---|---|---|
| **event_time / period_start / period_end** | When activity occurred, or the interval summarized | Retain source timezone, precision, business calendar and interval boundaries. A monthly sum has no invented instantaneous event time. |
| **as_of** | Business watermark or reporting reference date | Never use alone as proof of publication or availability. A fresh output can contain no new underlying data. |
| **source_observed_at** | When the provider says it observed the underlying event, if exposed | Optional, sourced field; distinguish estimated/provider-reported times from verified clocks. |
| **available_at** | Earliest evidenced time this exact source product/version was distributed to an entitled recipient class | Attach receipt/evidence and uncertainty. An event date or latest API retrieval cannot establish this retrospectively. |
| **observed_at** | Actual time Mastermind's collector first received/observed this payload | Immutable local receipt. A source timestamp cannot replace it. |
| **ingested_at** | When the payload became durable in the approved sink | Preserve write success and content hash, not merely job start. |
| **quality_released_at** | When the record passed required quality/restriction checks for the designated use | Rejections and later releases have separate events; do not backdate acceptance. |
| **feature_computed_at** | When a particular derived feature or forecast finished | Model/code/input hashes identify the completed version. |
| **known_at** | First time the particular record/feature was actually usable internally for the stated purpose | No earlier than the relevant receipt, ingestion, QA, lawful-access activation, prerequisite usable times, mapping knowledge and computation. Never substitute hypothetical availability. |
| **effective_from / effective_to** | Half-open interval in which the real-world relationship/definition was valid | Preserve acquisitions, dispositions, rebrands, fiscal changes and scope changes. |
| **recorded_from / recorded_to** | Half-open knowledge interval for that assertion's generation | Reconstruct which mapping or assertion version was believed then. Later corrections cannot silently revise earlier knowledge. |
| **correction_generation** | Source/ingestion revision sequence with supersedes links and reason | New immutable value plus cancellation state; no “keep latest” rewrite of the historical receipt. |

For an actual derived artifact, known_at is the maximum of all applicable internal usability prerequisites above; it is not simply the earliest vendor timestamp. Where a required timestamp is missing, actual replay availability is unproved. Record coarse date precision as a bound; a date-only release does not justify intraday use before a documented safe boundary.

A source may have been generally released before Mastermind was entitled to or received it. That supports, at most, a clearly labelled hypothetical source-availability study—not a claim that Mastermind possessed the information. Current revoked rights do not erase historical facts, but reproduction and retention still obey the actual agreement.

## E3. Three evidence tracks

| Track | Admissible data | Permitted conclusion |
|---|---|---|
| **R — historical real-time vintages** | Archived source, method, map and panel states with evidenced availability. Actual-system replay additionally requires actual internal receipt, access and computation evidence. | Historical information study within the proven availability scope. Hypothetical subscriber availability must be separately labelled and cannot represent actual Mastermind history. |
| **M — restated measurement history** | Current best reconstruction, expanded panels, retrospective maps, or otherwise unproven historical states | Feasibility, measurement alignment, lag diagnostics and developmental power planning. No investable historical-alpha or actual-system replay claim. |
| **P — prospective receipts and shadow forecasts** | Immutable acquisition, mapping, computation and issued forecasts from registration onward | Actual forward performance when first-release labels mature. Earlier M training remains disclosed and cannot be relabelled R. |

Do not pool these tracks under one out-of-sample chart. Current corrected history can be useful without being historically tradable. It is also not a guaranteed upper bound on achievable forecast quality: a revision can change either direction and can alter the measurement itself.

## E4. Replay and correction rules

At origin t, select the latest eligible generation for each native record whose relevant usability and knowledge clocks are no later than t. Apply its cancellation/tombstone status. For exposure mapping, select the assertion version known by t and valid over the measured economic interval. Do not sum every correction satisfying known_at ≤ t; that double counts revisions.

An acquisition test must distinguish three cases: ownership before acquisition, ownership after acquisition, and a later correction to the recorded acquisition date. Valid time controls the first two; knowledge time controls the third. If a measured aggregate straddles ownership change, split with supported source granularity or abstain. Do not allocate a quarterly total by an invented daily profile.

Preserve source method changes, panel entrants/exits, merge/split events, and withdrawn records. A “balanced panel” selected today from companies or devices that survived the whole study is not a historically available panel. Construct matched panels from membership known at each origin. Reconstruction of old observations must retain its actual reconstruction timestamp.

## E5. Economic identity and accounting scope

A ticker is not a durable company identity. A company is not automatically the economic recipient of every transaction involving its brand. Store/app/domain/repository/SKU identities first map to their operating entities, then to the relevant issuer/segment and reporting relation.

Keep **ownership share**, **KPI attribution**, and **sample coverage** separate. None can substitute for another. A royalty-bearing franchise can have full brand exposure but only partial revenue recognition. A merchant descriptor can identify a delivery platform rather than the restaurant. An app can change owner or be part of a paid family plan. A GTIN can identify a trade item while pack sizes and brand ownership still require versioned mappings. [W49]

Targets must specify currency, FX treatment, gross/net basis, tax/tip/refund treatment, channel, geography, same-store eligibility, 52/53-week fiscal periods, recognition timing, and definition revisions. The primary observed outcome is the first public release of that KPI—not automatically the later 10-Q filing. Latest-restated economics can be a secondary target, labelled separately.

## E6. Missingness, uncertainty, and access

Use explicit reasons: uncovered, suppressed, delayed source publication, ingestion failure, ambiguous identity, invalid method, or genuinely observed zero. A source's complete-scope definition is required before zero means zero. Forward-filling a transaction flow is generally invalid; a still-valid static state may be carried only under an explicit age rule.

A coverage denominator must say what is covered: panel cardholders, qualified stores, provider devices, countries, products, or a fraction of the target's economic scope. If the denominator is unknown, say unknown. A modeled total is not an observed sample count.

Retain source intervals where available. Propagate measurement, mapping, model and target-definition uncertainty through explicit sensitivity analysis; do not fabricate calibrated probabilities from subjective confidence labels.

The permission record should point to actual contract clauses and approved uses. If retention or deletion obligations prevent keeping a raw payload, preserve only what is lawfully permitted—such as a tombstone or receipt metadata—and disclose the resulting replay limitation. The architecture must not assume indefinite raw-data retention as a universal right.

# F. Derived intelligence and prioritized operational sensors

## F1. Measure a business quantity before interpreting it

The following are candidate feature families, not a requirement to compute every transform. Each first pilot should register at most two economically justified features and one primary target/origin. Additional lags, transformations, cohorts and targets count as new hypotheses.

| Sensor | Nearest defensible KPI / causal bridge | Initial reproducible feature | Critical falsifier / limitation | Relative priority |
|---|---|---|---|---|
| **Merchant payments** | Eligible merchant purchases → comparable sales or chain sales, after payment/accounting bridge | Origin-known matched-panel/location spending growth; transaction growth where defined | Performance explained by panel/store entry, merchant reassignment, tax/refunds, intermediaries or non-card mix | P1 conditional; strongest first commercial candidate |
| **App usage** | Measured activity → disclosed DAU/MAU with platform/country bridge | Fixed-definition active-use growth and registered coverage/mix adjustment | Apparent growth is panel/model change, cross-device duplication or platform substitution | P1 conditional |
| **Web traffic** | Visits/engagement → relevant digital users/orders only with conversion evidence | Same-domain/country activity growth; qualified funnel share if documented | Bots, migration, small-site suppression, channel mix or conversion drift explain signal | P1 for a web-led cohort; otherwise P2 |
| **Foot traffic** | Qualified same-location activity → visits; further sales bridge requires transaction evidence | Sequentially matched-location visit growth | Radius activity, employees, neighboring venues or panel shifts dominate | P2 after merchant study poses an incremental question |
| **Job postings** | Hiring demand → capacity/expense/headcount, with uncertain realization and lag | Deduplicated openings flow and role mix | Evergreen/ghost postings, replacements, staffing agencies or removal≠hire | P2 separate medium-lag study |
| **Hiring composition / certifications** | Occupational investment mix → future labor cost/capacity | Existing DOL metrics; fixed taxonomy role share and disclosed expense/headcount comparison | Decision-date leakage, reporting lag, visa coverage or classification drift | Reconcile existing P0 owner; P2 predictive research |
| **Customs / issuer manifests** | Physical imports/exports → input availability, inventory, shipment activity | Deduplicated issuer-linked quantity/weight by stable product unit | Confidentiality, ocean-only coverage, forwarders, front-loading or arrival/recognition mismatch | P2, sector-specific |
| **Shipping / commodity flows** | Completed loadings/deliveries → throughput, utilization or inventory | Installation/product flow versus seasonal baseline, with cargo-state vintages | AIS gaps or changed destination/product attribution create the change | P2; can rank higher for a commodity mandate |
| **Advertising** | Acquisition effort/competition → possible future demand, not identified ROAS | Same-platform impression/share or estimated-spend change with model flags | Common demand or deteriorating efficiency explains spending | Context first; causal-ROI claims deferred |
| **SKU pricing / sell-through** | Comparable product price×units/mix → retail sales or manufacturer demand with channel bridge | Constant pack-size price/promo index; units only where actually measured | Pack/variant/category changes; posted≠paid price; retailer sell-through≠issuer sell-in | P2 narrow vertical |
| **E-commerce rankings** | Relative category position → ordinal demand information | Stable-category rank persistence/breadth with tracking coverage | Category changes, promotions and selection make rank-to-unit mapping unstable | P2 only as a proxy; reject universal units conversion |
| **Channel inventory** | Inventory stock, receipts and sell-through → replenishment/production risk | Inventory days or stock-flow reconciliation where all denominators are observed | Stockouts are censored demand; distributor/retailer stocks incomplete; shipment timing dominates | High economic relevance, conditional on defensible access |
| **Developer activity** | Economically exposed project adoption → possible product demand | Stable repo/model cohort activity; distinguish contributors, users and request counts | Bots, CI/CD, free distribution, repository switching, survival-biased histories | Existing context; revenue nowcast deferred without bridge |

Matched sales divided by measured visits is, at most, a revenue-per-observed-visit proxy. It does not identify conversion and average transaction value separately. Those claims require independently observed transaction counts and compatible store, channel, geography, period and panel definitions. Advertising spend rising with traffic and transactions is a descriptive pattern; it does not establish causal return on advertising.

## F2. Merchant pilot: concrete and bounded

**Candidate target.** Start diligence with CMG's disclosed comparable restaurant sales, whose first-party disclosures define the eligible operating-store cohort and discuss transactions/check. Expand only to a preregistered group with compatible disclosure definitions. This makes CMG a calibration example, not an ex post selected “winner.” [W42]

**Candidate source.** Request the narrowly scoped Arbiter merchant dataset; compare Orion if its historic vintage/coverage package is better. Source choice follows sample and contract evidence. Both must use the same eligible issuer/origin set and the same target definitions. Do not buy unrelated SKU, advertising, or location bundles to launch this pilot.

**Bridge.** Sampled spending growth can approximate comparable sales only after controlling the actual same-store criterion, operating geography, measured payment channels, refunds, taxes/tips, delivery merchant descriptors, cash/gift cards, and store openings/closures. If store identities/opening dates are unavailable, **do not claim same-store measurement**. Either define a prespecified chain-sales target with an expansion bridge or retain the study as measurement feasibility.

**Features.** The primary candidate is origin-known matched-panel/store spending growth. A second may be same-scope transaction growth or a coverage-drift diagnostic, chosen before confirmatory evaluation. Average observed ticket is spend divided by transaction count when both share scope. Cardholders are not necessarily transactions or store visits.

**Accounting portability.** A franchise-heavy restaurant's systemwide sales do not equal consolidated company revenue. McDonald's public reporting illustrates the need to distinguish franchise sales and the revenue recognized by the parent. A model calibrated to company-owned restaurant revenue cannot transfer unchanged. [W45]

**Kill condition.** Stop the same-store claim if eligible stores or a valid alternative target cannot be identified; stop historical information claims if vintages cannot be demonstrated. In either case, a prospective narrower study may remain legitimate. Stop vendor selection if mapping/panel instability dominates or rights/price do not support the bounded use.

## F3. Digital pilot: users first, monetization second

**Candidate target.** DUOL provides a concrete issuer with reported operating metrics. Start with active-user growth under an explicit app-versus-total-user bridge. Paid subscribers, bookings, and recognized revenue require separate definitions and models. Its disclosures distinguish paying subscriptions and other user categories, so a download or device estimate cannot simply be relabelled as a subscriber. [W43][W44]

**Candidate source.** Sensor Tower's specific usage/PIT delivery is the first diligence candidate. Verify the exact products, platform/country scope, deduplication, historical vintage start and versioning. Treat the 2025 model/panel combination as a prespecified method boundary, not a business acceleration. Similarweb is a sensible alternative for a web-led cohort, subject to its explicit revised-history limitations.

**Features.** Use active-use growth on a fixed platform/country definition and one justified scope adjustment. Do not fit downloads, ranks, retention, sessions, revenue, ads and reviews simultaneously and report whichever works. Current app-ratings telemetry remains a separately identified descriptive input whose incremental value must also be tested.

**Bridge.** A user can appear on multiple devices/platforms, use the web, join a nonpaying family account, enter a free trial, or pay through a different channel. Estimated app revenue can omit or differently treat taxes, fees, FX and web billing. Annual prepayments and recognition create lags. Keep uncertainty explicit instead of treating a one-to-one conversion as fact.

**Kill condition.** If cross-platform/global scope cannot be reconciled, limit the output to a narrower activity index. Failure to estimate global users does not turn the index into zero or justify a numerical total-company revenue forecast.

## F4. Sector-sensitive alternatives

For semiconductors, begin with a first-party monthly KPI comparator and the existing GMI/TIL research estate. TSMC publishes monthly revenue information and a financial calendar. Preserve the actual releases, timestamp, currency and any later corrections; a current historical table is insufficient to reconstruct every past release. A useful public KPI may already be quickly priced, which is precisely why expectation and investment tests follow measurement. [W40][W41][R20]

For manufacturers and retailers, channel inventory may be more economically direct than web traffic. The obstacle is often source completeness and the sell-in/sell-through bridge, not lack of relevance. Rank it after a lawful data demonstration, not below every cheap public proxy by default. Reconcile beginning inventory + receipts − sales ± transfers/adjustments only when the terms and units are actually observed; otherwise report the unidentified components.

For commodities, Kpler snapshots deserve a technical sample before a generic manifest product. For issuer-specific imports, compare Panjiva, ImportGenius, and Datamyne on the same legal-entity/supplier cases. Aggregate Census flows supply controls and plausibility checks, not an attribution substitute.

## F5. Calculations before LLM reasoning

Deterministic, reproducible stages should handle receipt hashing, timestamp normalization, generation selection, entity resolution under approved rules, deduplication, fiscal alignment, unit/FX conversion, coverage checks, known-at panel selection, feature computation, model inference, baseline comparisons and evaluation.

This does not prohibit statistical models. Seasonal adjustment, panel correction, regularized regression or a hierarchical forecast may be appropriate if fitted only on available training data and preserved as immutable model artifacts. “Deterministic” means reproducible from declared inputs and versions, not “no estimation.”

Use cheap LLMs only for bounded candidate labels—for example occupation class, product category, alias suggestions or source-text extraction—with schema validation, versioned prompts/models, sampled adjudication, error estimates, and abstention. No candidate label becomes an authoritative historical mapping because a model sounds confident. No model may send licensed source text to an unapproved processor.

Use frontier LLMs to critique causal bridges, reconcile contradictions across accepted observations, explain alternative mechanisms, and propose falsifiers. They should cite receipt-backed facts and separate hypotheses from measurements. Neither model tier may invent observations, fill missing values by narrative, assign source promotion, choose portfolio weights, or originate uncalibrated numerical forecasts.

# G. Mastermind integration map

## G1. Producer → owner → family → consumer

| Producer | Canonical artifact / data owner to reuse | Inspectable evidence family | Proposed consumer and boundary |
|---|---|---|---|
| Existing DOL source | Macro DOL collector, existing employer resolver, TIL W7 and declared contracts | Labor certification / capacity context | Existing theme research/display when valid data and consumers are actually present; no fused score |
| Existing Census source | Macro Census collector, TIL W8, current HS/theme configuration | Aggregate trade / physical activity | Existing theme context with revision and validity repair in a later authorized task |
| Existing app/GitHub/HF | Current collectors and registered Macro channels | Ratings, developer interest, model distribution kept separate | Existing research context; optional provenance pilot, not automatic usage/revenue conversion |
| One admitted commercial sensor | Existing Macro data-layer/contract registration; approved logical observation artifact | Merchant spend, app usage, or selected source family | Reproducible KPI feature/forecast research artifact; no generic convergence admission |
| Exposure resolution | Existing issuer/security identity plus GMI/TIL relationship owners | Ownership, operating scope, supplier/customer/asset relationships | Feature construction and source-grounded research; never a second company graph |
| Forecast and target evaluation | Existing compatible prediction, signal-history, outcome and shadow owners [R05] | Company KPI forecast, target vintage and loss difference | Research adjudication with exact forecast/label IDs; no separate sensor outcome ledger |
| Research interpretation | Existing research_desk and accepted evidence interfaces | Mechanism, contradiction, uncertainty, expectation comparison | Research proposals; existing risk lane receives new input only after a separate approved contract change |
| Terminal display | Existing Macro intelligence projection and typed Terminal normalizer | Context-only KPI/source receipt presentation | UI reads generation and freshness; no direct vendor acquisition or decision authority |
| Research Vault material | Existing Vault display/document owner | Licensed document context | Source discovery and human research; storage does not grant extraction, redistribution or signal rights |
| Future V3 components | Canonical V3 owner once accepted and implemented | Decision Snapshot/claim lineage when available | Integrate later by accepted contract; this report does not instantiate V3 authority |

## G2. Independent information is an empirical property

The source-dependency record should identify shared upstream panels, publishers, customer datasets, merchant maps, geofences, model estimates, and common economic episodes. Sensor Tower/data.ai are related; Kpler/Spire Maritime are related. More generally, two commercial feeds can share inputs without public documentation proving exactly how much.

Correlation is a diagnostic, not a permission to count independent votes. Low correlation can be noise. High correlation can reflect the intended common KPI. Assess incremental value with the matched baseline-plus-family study, removal ablations, shared-event stress and stability across time/coverage changes. Keep the dependence unknown if source lineage cannot be established.

## G3. Observability without a new control plane

Use existing operational reporting to expose last successful acquisition, source release age, receipt age, data completeness, mapping failures, method changes, corrections, valid forecast counts, matured outcomes and downstream consumer status. Separate job success from source success, output generation from underlying freshness, and available rows from valid coverage.

A circuit breaker should make research evidence unavailable when rights, mapping, time semantics or source validity fail. It should not alter trading behavior; that is outside this commission. Recovery creates a new auditable generation and does not backdate usability.

# H. Empirical validation program

## H1. Registered question and admissible claim

For the first commercial candidate, register:

> For a prespecified comparable company/KPI cohort, does adding at most two operational-source features improve forecasts of the first publicly reported KPI beyond a strong, same-origin baseline, by a practically meaningful amount, under demonstrated availability and stable measurement?

This is a **conditional predictive-utility** question. It is not a causal intervention estimate, a broad universal sensor ranking, or a stock-alpha claim. Identify Track R, M or P before selecting data. For R, specify whether actual-system availability is proved or only hypothetical source delivery is reconstructed.

Record the source/product, target definition, historical eligibility rule, exclusion reasons, point-in-time mapping, feature recipes, baseline ladder, model/tuning budget, origin, loss, practical margin, multiplicity procedure, analysis date/label trigger, and stop criteria before confirmatory outcomes are viewed.

## H2. Cohort, fiscal periods, and forecast origins

A working cohort of roughly **15–25 eligible issuers** is a capacity-planning suggestion, not a power claim. Use historically known eligibility, including companies later acquired, delisted, renamed or dropped by the provider. A current portfolio list is appropriate for a current scoped operational use, not for a broad survivorship-free historical claim.

Define the primary origin by a fixed calendar rule relative to fiscal period end; for example, seven calendar days after quarter end **only if the target is still unpublished**. Choose the actual rule from pre-study delivery and reporting constraints, then freeze it. An archived then-known earnings schedule may support an alternative origin. Do not anchor historical forecasts to the eventual actual earnings date without contemporaneous schedule evidence.

At each origin retain the whole eligible denominator, publication status, source coverage, mapping status and abstention. If a target was already released, it is not a forecast opportunity. Earlier secondary origins for the same issuer-quarter remain dependent, not extra independent labels.

Target vintages must include first disclosure timestamp and source. The first earnings release can precede the filing. Historical targets used for training are themselves selected from what had been released by the fit timestamp, with later restatements isolated.

## H3. Strong nested baselines

| Model | Inputs | Purpose |
|---|---|---|
| **B0** | Previously available issuer KPI history, fiscal seasonality and a small transparent persistence structure | Establish a credible cheap operating baseline |
| **B1** | B0 + same-metric, same-scope PIT consensus where available | Test against expectations the system could actually know |
| **B2** | B1 + a small frozen set of relevant existing pre-origin Mastermind evidence | Give the proposed sensor a fair comparison with the incumbent information set |
| **B3** | B2 + at most two registered sensor features | Estimate incremental utility of the new source |

Where historical consensus is absent, B1 is unavailable. Build the explicitly named **B2-no-consensus / B3-no-consensus** comparison from B0 and the registered existing signals; do not silently substitute today's consensus or claim to beat “the Street.” Begin lawful prospective consensus receipts if later authorized.

Use the same model class, tuning opportunity, target definition and forecast origins for paired comparisons. A sensor should not win because its model is much more flexible or its baseline is deliberately weak. Learn all coefficients, normalization, seasonal adjustment, winsorization, weights, matching thresholds and feature selection inside training windows.

Primary comparison is B3 versus B2 on exactly matched valid forecasts. Also score the **entire eligible opportunity set** with B2 fallback wherever B3 abstains. Publish both. Coverage loss that disproportionately removes difficult companies must not look like prediction improvement. Cross-provider comparisons require a shared overlap sample plus separate full-coverage and cost results.

## H4. Measurement and sample diagnostics

Before judging prediction, quantify identity correctness on a stratified, adjudicated sample; native-entity coverage; ambiguous and unmatched records; stable versus changing panel/location cohorts; source revisions; delivery lag distribution; missingness and suppression; concentration by issuer/region/channel; and the age of usable data.

Compare sequentially matched-panel growth with all-panel growth and with coverage/method-change indicators. Sample inclusion probabilities may be unknown. Reweighting does not by itself make a convenience panel representative. Separate coverage, nonresponse, measurement and processing/linkage errors, consistent with Census quality principles. [W52]

When actual weights exist, the diagnostic effective weight count is (sum of weights)² / sum of squared weights. It measures weight concentration under limited assumptions. It is not the number of independent company-quarter outcomes, nor proof of a representative sample. Provider-modeled population totals must not be reported as observed panel sizes.

Require stability around acquisitions, platform/model changes, store openings, panel supplier switches, holidays and 53-week fiscal years. Report missed coverage and large errors, not only average fit. No synthetic data can establish actual supplier coverage or real correction retention.

## H5. Losses, intervals, and uncertainty

The proposed primary endpoint is **paired improvement in scale-normalized absolute error** on first-release KPI outcomes. Normalize by a training-only company scale fixed for the scoring window; avoid unstable percentage losses around zero. Define d(i,q) = loss(B2,y) − loss(B3,y); positive values favor the sensor.

Report the average paired loss difference and an uncertainty interval, the distribution across issuers/periods, worst misses, abstention rate, and concentration of benefit. Raw-unit MAE, RMSE, acceleration direction and beat/miss are secondary; define materiality/tie bands before evaluation. Do not switch the winning endpoint after seeing results.

A forecast interval concerns the future KPI, not merely a fitted mean. Register interval levels and evaluate coverage together with width and a proper interval score. Wider intervals can improve coverage while making the forecast useless. Distinguish model uncertainty from unresolved mapping/scope scenarios; do not attach unsupported probabilistic precision to the latter. Proper-scoring research supports these principles. [W15]

Register a practical improvement margin, delta_min, in the chosen normalized loss using intended use, baseline error and source/maintenance cost. This report does not invent a universal “5% improvement” hurdle. A later study must state its chosen margin before the confirmatory block.

## H6. Validation, dependence, and power

Use chronological outer evaluation with training-only inner tuning, then an untouched final calendar block or forward shadow. Every training label must have been publicly released before fit time. Purge overlapping outcome windows where relevant; set any embargo from actual label availability and overlap, not an unrelated stock-return horizon. Random row splits are invalid.

Primary units are issuer-quarter forecast episodes. Report raw input rows, forecast episodes, issuer clusters, calendar/release-window clusters, and shared panel/method generations. Date-only clustering can miss issuer persistence; issuer-only clustering can miss marketwide shocks. Choose a dependence method appropriate to the panel and sample size, with issuer/time-block robustness. Few clusters remain few even after bootstrapping. [W12][W13]

Before confirmatory launch, estimate a minimum detectable improvement under plausible issuer persistence, calendar shocks and coverage loss using the developmental sample. An 80% power design target, if adopted, is a declared study policy rather than a property of the data. Eight forward quarters across 20 companies provide at most 160 company-quarter pairs but only eight broad quarter clusters. Daily rows cannot fix that limitation.

If the planned study cannot discriminate delta_min, narrow the claim, improve measurement, extend the forward window under a registered rule, or retain context-only status. Do not force a pass/fail prediction verdict. For nested squared-error forecast tests, specialized model-comparison inference has assumptions that do not automatically transfer to regularized panel MAE. [W53][W54]

## H7. Multiplicity, peeking, and causal interpretation

Log every tried vendor, universe, target, feature, lag, cutoff, model and horizon, including discarded variants. Exploratory work informs the registration but cannot be relabelled confirmatory. For a small confirmatory family use a declared fixed sequence or multiple-comparison procedure such as Holm. A factor-paper t-statistic threshold is not a universal antidote to search. [W14]

Freeze the final holdout recipe and govern access to confirmatory losses. Repeatedly viewing performance and deciding when to stop is sequential testing; use a valid preregistered procedure or wait for the planned analysis trigger.

Register a short mechanism model. For merchant spend, latent demand influences both panel transactions and reported sales; panel composition influences measured transactions without necessarily changing the business. For ads, demand can cause both spending and sales, and traffic can mediate effects. For hiring, cost and capacity can be nearer outcomes than revenue.

For causal claims, select controls for the stated estimand and acknowledge confounding. For operational forecast utility, B2 deliberately includes legitimate pre-origin information even if it mediates the sensor's information into news or consensus. The result then measures remaining usefulness at that origin. It does not establish that the sensor's operating measurement is false or causally irrelevant. [W11]

## H8. Required falsifiers

1. **Coverage explanation:** panel/method-change indicators explain the forecast gain better than the business feature.
2. **Vintage failure:** the result disappears when using true source vintages, then-known maps, or forward receipts.
3. **Ownership leakage:** present-day pro-forma affiliations create improvement that vanishes under actual historical economic exposure.
4. **Wrong-entity placebo:** a dependence-preserving matched wrong-issuer/domain/store assignment performs similarly. Design the placebo within plausible sector/calendar structure; naive circular shifts can destroy seasonality.
5. **Timing failure:** the useful signal arrives only after the KPI's first release, or after the stated executable decision cutoff.
6. **Accounting failure:** scope, currency, store expansion, refunds, franchise treatment or recognition timing explains the apparent surprise.
7. **Concentration:** one issuer, event, method generation or exceptional quarter supplies most improvement.
8. **Redundancy:** a sufficiently precise comparison rules out practical improvement beyond B2 at the chosen origin.
9. **Calibration failure:** forecast intervals or abstention policies are materially unreliable in the stated use.
10. **Economics failure:** a cheaper lawful source or existing baseline is practically equivalent within a prespecified margin and uncertainty.

Future-value “oracle” variants can be clearly labelled leakage diagnostics. They can never be candidate forecasts. Failure to reject equal performance is not equivalence; wide intervals mean inconclusive.

## H9. From KPI value to expectation and investment value

A calibrated KPI forecast can be compared with contemporaneous consensus only when definition, geography, currency, accounting basis and period match. Otherwise the expectation gap is unavailable. Do not subtract total-company revenue consensus from a domestic merchant index.

KPI accuracy alone does not establish information not already priced. A later expectation study should test whether the sensor forecasts first-release surprise beyond B2. A separate investment study must register formation/exit timing, one primary horizon, market calendars, execution after availability, realistic costs, liquidity, borrow where needed, delistings, benchmark exposure and concentration.

Pre-release and post-release return studies answer different questions. Report IC, bucket plots and gross returns as diagnostics, not substitutes for net utility of a specified executable rule. This commission runs neither study and authorizes no trades.

## H10. Adjudication states

| State | Meaning | Next permitted disposition |
|---|---|---|
| **INVALID / STOP** | Rights, lineage, timing, target or identity cannot support intended use | Stop that use; preserve the reason and lawful evidence |
| **ADVERSE** | Reliable evidence shows deterioration or unacceptable fragility | Reject/narrow the proposed sensor use; record null/adverse results |
| **INCONCLUSIVE** | Valid study but uncertainty cannot distinguish practical benefit | Remain research/shadow; continue only under a bounded registered plan |
| **DESCRIPTIVE ONLY** | Reliable observation or narrow measurement without a valid forecast/expectation bridge | Context with scope and uncertainty; no promotion |
| **VALIDATED FOR STATED KPI SCOPE** | Confirmatory evidence supports practical conditional forecast benefit with robustness | Eligible for separate expectation/integration review |
| **AUTHORITY REVIEW** | Appropriate subsequent decision evidence and canonical owner exist | A separate approval/implementation process; never automatic from this report |

For a strong confirmatory acceptance rule, preregister that the lower confidence bound on improvement exceeds delta_min, with acceptable coverage, calibration and no material lineage failure. If another rule is justified, document it before outcomes. A narrow one-company result can support a narrow claim; it cannot establish general portability.

# I. Risks and failure modes

| Risk | Detection / mitigation | Stop or limit |
|---|---|---|
| Event dates masquerade as availability | Separate release, receipt, ingestion and usable timestamps; replay adversarial examples | No historical information claim without evidence |
| Revised history and changed models | Preserve source snapshots, correction generations and method boundaries | Track M or P when R is unproved |
| Current ownership contaminates history | Native identity plus valid/knowledge intervals; acquisition and mapping-correction cases | Reject retrospective pro-forma use for as-reported history |
| Coverage/survivorship bias | Historical eligibility, origin-known panels, full-denominator fallback, delisting/M&A records | Narrow scope or stop if target population cannot be supported |
| Empty source looks neutral/fresh | Separate data completeness from output generation and qualitative tags | Unavailable evidence; no zero or neutral vote |
| Proxy confused with KPI | Written accounting/scope bridge and target-definition validation | NOT_ESTIMABLE or descriptive-only |
| Many correlated signals look independent | Upstream dependency map, matched ablations, common-event stress | No independent votes from product count |
| Sparse outcome history creates precision | Issuer/time clusters, power planning, registered practical margin | INCONCLUSIVE; no forced positive/negative verdict |
| Search/peeking inflates success | Trial log, fixed endpoint, untouched holdout or valid sequential rule | Exploratory label until independent confirmation |
| Geographic/fiscal/channel mismatch | Exact calendar, FX, accounting and target-scope reconciliation | No expectation-gap subtraction across mismatched quantities |
| Legal/source provenance uncertainty | Actual contract/source-use record and approved processing/retention scope | Stop prohibited or unverified intended use |
| Vendor lock-in / unaffordable maintenance | Narrow quote, portable IDs, version exports, lawful exit/archive plan | Prefer practically equivalent lower-cost source; otherwise defer |
| Fragile LLM classification | Versioned candidate labels, adjudicated validation and abstention | No autonomous historical mapping or numerical imputation |
| Operational context promoted into trades | Explicit context/research state and existing owner boundary | Separate authorized integration and decision review required |
| Unavailable live proof overclaimed | Report code, artifacts, workflow and consumption separately | State exact observed rung; do not infer from green jobs |
| Scope inflation / duplicate control plane | Exact carrier collision review, one source/type/KPI, existing owners | Stop overlapping edits and return the bounded owner handoff |

A sensor may be useful for one region, business model or phase of the cycle and invalid elsewhere. The report should retain that narrower outcome rather than force a universal build/reject verdict. Conversely, a rich dataset with weak linkage or unusable rights should not be retained simply because acquisition was expensive.

# J. Build priority and explicit dispositions

## P0 — prerequisite hardening, one bounded provenance slice

- Resolve the current source/KPI owner and open-carrier collisions. Record the selected source's allowed use and available evidence track.
- Preserve receipts, revisions, valid/knowledge-time mappings, missingness, and a first-release target definition where one exists.
- Correct the **research specification** of DOL availability, Census revisions, and existing developer same-day overwrites; implement any repair only through the later appropriate owner.
- Register one benchmark and existing prediction/outcome integration. Deliver NOT_ESTIMABLE honestly if the first source has no defensible KPI bridge.
- Add source-level observability through the existing reporting surface. Do not build a new dashboard service or general warehouse.

## P1 — conditional KPI studies

1. Merchant-spend restaurant pilot after store/merchant/panel and rights demonstration.
2. App active-usage pilot after exact PIT-product/vintage and scope demonstration.
3. For a semiconductor-focused mandate, first-party monthly KPI comparator plus existing sector physical evidence can precede either consumer pilot. This is a mandate-dependent sequence, not a third mandatory commercial program.
4. Prospective expectation receipts only for an exact supported target, with existing owner and lawful access.

No paid source is authorized by being listed P1. Select one first; the second requires evidence that its question is not already covered and that staff/cost capacity exists.

## P2 — conditional extensions

Footfall after a defined incremental transaction question; targeted SKU price/sell-through; labor-capacity and expense studies; issuer manifests; commodity throughput; and genuine channel-inventory reconciliation. Each receives its own target, evidence track and registered test. A commodity or manufacturing mandate may move the relevant physical source ahead of consumer sensors without changing the admission rules.

## Defer

Broad real-time global operational coverage; cross-sector hiring-to-revenue models; developer-to-sales claims without disclosed monetization bridges; advertising attribution/ROAS; free-form frontier forecasting; universal supplier/customer graph construction; and broad multivendor fusion before individual marginal value is measured.

## Reject

A generic feed warehouse without a specified decision/research use; universal alternative-data score; source authority awarded by freshness or correlation; current-pro-forma backtests described as actual historical knowledge; rank-to-unit conversion without calibration; no-records-as-zero assumptions; synthetic “forward results”; unauthorized scraping/data purchase; and new allocator, risk gate or V3 control plane under this research commission.

“Defer” and “reject” here are research recommendations for these uses. They do not create official company dispositions, close incumbent workstreams, or alter canonical authority.

# K. Sequenced implementation recommendation

| Phase | Work and deliverable | Exit evidence | Dependency / next decision |
|---|---|---|---|
| **0. Admission and collision resolution** | Pin then-current law and sources; pick one authorized source, one mapping type and one target/use; record rights, tracks, owner and unresolved requirements | Reviewable admission record; exact existing paths/owner; no competing carrier | If source access or scope is unresolved, return a concrete bounded decision packet |
| **1. Temporal provenance proof** | Research-only replay from real receipts through mapping and feature; revision, cancellation, missingness and usable-time checks | Reproducible artifact/receipt IDs; real-source behavior distinguished from synthetic contract fixtures | Source readiness depends on observed evidence; missing real vendor revision behavior remains unverified |
| **2. Measurement feasibility and registration** | Define target/accounting bridge; characterize coverage; run labelled developmental M/R diagnostics if lawful; freeze benchmark and power plan | Target and baseline records; explicit search history; NOT_ESTIMABLE where appropriate; forward-study registration | No confirmatory or alpha claim from developmental fit |
| **3. Prospective KPI shadow** | Issue immutable research forecasts on registered origins; acquire first-release labels as they occur | Forecast/label lineage; data-quality and abstention reports; matured outcome counts | Adjudicate at registered date or label-count/power trigger; no invented completion date |
| **4. Empirical adjudication** | Paired B3–B2 loss, dependence-aware uncertainty, falsifiers, calibration, coverage and cost | INVALID, ADVERSE, INCONCLUSIVE, DESCRIPTIVE, or validated for a stated KPI scope | A positive result earns only the corresponding narrow claim |
| **5. Expectation / investment study and later integration** | Same-scope surprise test; separately authorized executable investment study; accepted consumer contract | Independent evidence and canonical-owner decision | Separate implementation/promotion authorization; V3 dependency only where actually required |

There is no fixed “two quarters prove alpha” timeline. A short engineering phase can complete quickly while the inferential phase remains open for real labels. The collection plan must name who will adjudicate, the allowed observation window/budget, the next review trigger, and the disposition if the sample remains underpowered. It must not create an indefinite watcher or silently authorize recurring external spending.

# L. Exact proposed follow-on implementation commission

> **Issue only after this research recommendation is accepted. This text is not executed by Commission 16.**

## L1. Title and objective

**Operational Sensor P0 — one-source provenance and registered KPI-study foundation**

Implement one research-only, production-inert slice that preserves a real authorized operational source through time, resolves one economic relationship type through the incumbent identity owner, computes one reproducible feature recipe, and prepares an explicit KPI-study registration. Reuse current data, evidence, prediction and outcome owners. The primary deliverable is trustworthy temporal lineage and a bounded empirical contract.

## L2. Starting authority and source census

At task start, follow current Mastermind bootstrap/source law and pin then-current Mastermind, Macro and Terminal identities. Treat this report's pins as evidence of the research date, not current execution permission. Read the applicable repository instructions and identify the lawful parent carrier.

Check only relevant open collisions: app/developer demand audit, TIL W7/W8, GMI identity/theme work, current prediction/outcome owner, and any accepted operational-sensor carrier created since this report. Reuse or coordinate with the existing carrier; do not create a parallel owner to avoid a collision. Record changed source assumptions since this report.

## L3. Scope and source selection

Select **one already authorized real source**, **one native-entity relationship type**, and **one feature recipe**. Prefer an existing source whose lawful receipt history can actually support the demonstration. Existing Macro GitHub/app/HF observations are candidates for provenance, not assumed KPI forecasts; existing DOL/Census require their documented temporal limitations to be resolved for any historical use.

No vendor purchase or new external service is included. If the only defensible KPI pilot requires a commercial product, complete source/KPI admission and the accessible provenance work, then return the exact sample/rights/price decision required. Do not fabricate licensed data.

Use historical Track R only where source, mapping, method and actual/hypothetical availability are correctly proved and labelled. Otherwise use Track M for developmental measurement or Track P from actual receipts onward. A targetless source returns NOT_ESTIMABLE.

## L4. Allowed work

- Add or extend the minimum compatible research contracts for raw observation, exposure, feature snapshot and optional KPI forecast; names must map to existing approved owners.
- Build an isolated research replay/validation harness using lawful real source receipts. Record native IDs, all relevant clocks, generations, hashes, validity states and model/code artifacts.
- Demonstrate one exposure relationship under valid-time and knowledge-time corrections.
- Add focused tests for future publication/receipt exclusion, late ingestion, later mapping knowledge, acquisition scope, corrected/withdrawn records, same-day revision preservation, explicit missingness, fiscal alignment, and a model-version change.
- If a defensible target exists, register that target and the B0–B3 or explicitly labelled no-consensus ladder, primary origin/loss, practical margin selection procedure, coverage denominator, dependence/power plan, hypothesis log and future adjudication trigger. Otherwise freeze a provenance-validation plan, document the missing KPI bridge, return NOT_ESTIMABLE, and identify the exact next source/target decision.
- Expose a concise source-health readout through an existing research/reporting path, if compatible. A documentation artifact is sufficient for this bounded P0 slice.

Choose exact changed paths after the admission/collision check and record them before edits. Use a reversible isolated branch/worktree as applicable; no edits to shared production checkouts. The source fixtures and research artifacts must obey actual retention and redistribution rights.

## L5. Prohibited work

No live scheduler, production pipeline, vendor procurement, new credentials or entitlements, deployment, portfolio/risk/position change, generic convergence admission, new outcome ledger, new identity control plane, or implementation of NOT_BUILT V3 authority. No proprietary raw dataset or restricted source content committed to GitHub.

No LLM-originated observations, imputed missing measurements, numerical nowcast without a calibrated target, or claimed statistical validation based on synthetic fixtures. No broad adapter framework for every sensor family.

## L6. Acceptance evidence

The implementation return must show:

1. **Source proof:** one real authorized source, precise available-use scope, real sample coverage and identified native record/receipt IDs. Documentation-only vendor claims remain labelled unverified.
2. **Replay proof:** selecting origin t cannot see later receipt, QA, computation, mapping or correction knowledge; each native record contributes only its eligible generation; cancellations are respected.
3. **Economic mapping proof:** one actual relationship type with a worked acquisition/effective-date or mapping-correction case. Synthetic boundary cases may test the contract but do not establish historical source truth.
4. **Quality proof:** unknown/suppressed/uncovered/late/ambiguous states remain distinct from zero; method changes create explicit versions; output generation does not mask empty data.
5. **Feature proof:** the same accepted inputs and model/code versions reproduce the same feature. A numerical forecast exists only with a documented target, training cutoff and usable label history.
6. **Integration proof:** exact reused owner/contract paths and downstream consumers; no second signal/prediction/outcome owner; no source-decision authority change.
7. **Scope proof:** inspect the diff and applicable run configuration to establish the change is production-inert. No deployment or live acceptance is claimed without observed evidence.
8. **Study readiness:** for a supported target, a frozen proposed benchmark, evidence track, baseline availability, search history, coverage/power plan and named future adjudication role/trigger. For a targetless provenance pilot, a frozen lineage-validation plan, exact missing bridge and bounded next decision; no fictitious forecast benchmark.
9. **Honest completion state:** ENGINEERING_PROVEN, PROVENANCE_ONLY, NOT_ESTIMABLE, or BLOCKED with exact evidence and reason. These are proposed task-result labels, not new global authority states.

A synthetic correction fixture can prove the harness handles corrections. It cannot prove the supplier retains real historical revisions. If no actual revision sample exists, state **supplier correction behavior unverified** and withhold certification of those supplier archival/correction capabilities. Immutable client receipts can still prove the narrower record of what the client actually received and when; certify only that demonstrated receipt/lineage scope, with its correction limitations explicit.

Engineering acceptance does not require future earnings labels to have matured. Do not promise an empirical shadow “result” that cannot yet exist. Conversely, shipping a schema does not count as completing a source replay.

## L7. Stop and return conditions

Stop the dependent use if source rights are unknown, real receipt history is absent, a required KPI cannot be defined, current source law conflicts, an existing carrier owns the change, a purchase is required but not authorized, or the task would require production/trading authority. Complete independent safe work and return the concrete missing decision or prerequisite; do not broaden scope to work around it.

If historical PIT cannot be established, withdraw that historical claim and propose the lawful M/P alternative. If a bridge is unsupported, return NOT_ESTIMABLE instead of a guessed revenue forecast. If the study is underpowered, return a finite registered shadow plan or defer recommendation rather than force a positive result.

## L8. Final implementation return

Return a durable report containing the current pinned source identities; collision and owner decisions; exact changed files/contracts; lawful data/rights references; raw receipt and model/code hashes; temporal replay examples; test commands/results and limitations; data-quality/coverage census; target and accounting bridge or NOT_ESTIMABLE reason; baseline availability; complete study registration; no-authority-change evidence; null/adverse findings; unresolved source/vintage/procurement questions; and the **single next bounded commission** appropriate to the demonstrated result.

The proposed next commission may be a narrowly scoped commercial sample/rights evaluation, prospective collection, or a repair under an existing source owner. It must not bundle three vendor programs, all sensor families, V3 construction, and portfolio integration.

---

# Evidence references

## Repository evidence

All Mastermind links below are pinned to 521720b09be2921e996d9396b522b1c4ca62041c; Macro links to 79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f; Terminal links to 1c708450187755160e1a5889b69598a2fcb1f0d1. Candidate PRs are separately labelled in the report and companion census.

[R01]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/data/census/CENSUS.md
[R02]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/portfolio/lenses.py#L245-L300
[R03]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/portfolio/held_risk.py#L737-L839
[R04]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/loop/fundamentals.py
[R05]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/research/TREND_PERSISTENCE_PROTOCOL.md
[R06]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/superpowers/specs/2026-09-15-mastermind-portfolio-v3-risk-first-autonomous-manager-design.md
[R07]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/brain/research_desk.py
[R08]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/data_layer/macro_refresh.py
[R09]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata_models.py#L189-L233
[R10]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/dol_labor_certs.py
[R11]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/census_trade.py
[R12]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/github_repos.py
[R13]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata_ledger.py#L71-L130
[R14]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/ALTDATA_CONVERGENCE_FIRST_COHORT_ADJUDICATION_2026-08-13.md
[R15]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/altdata/track_record.json
[R16]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/site/qledger/track_record.json
[R17]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/terminal/lib/companyIntelligence.ts
[R18]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/agentos/workstreams/WS-GMI-THEME-GRAPH.md
[R19]: https://github.com/mastermindx-market-intelligence/macro/pull/7420
[R20]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/INTL_ENGINE_PROBLEM_AUDIT_FOR_FABLE.md#L593-L602
[R21]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/loop/single_name_panel.py
[R22]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/brain/bottleneck.py
[R23]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/bridge/macro_snapshot.py
[R24]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/theme_hiring.py
[R25]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/config/synapse.yml#L13802-L13886
[R26]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/site/basketdata/trade_flows.json
[R27]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/theme_trade_flows.py
[R28]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/huggingface.py
[R29]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/altdata/mastermind.json
[R30]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/RESEARCH_VAULT_MASTERPLAN.md
[R31]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/ingest/pull_macro_intel.py
[R32]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/run_status.json
[R33]: https://github.com/mastermindx-market-intelligence/macro/actions/runs/37172153941
[R34]: https://github.com/mastermindx-market-intelligence/macro/commit/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc

## Primary public sources

The following references are deliberately ordinary URLs so the report remains portable outside this research session. The source companion records what was actually documented and what still needs a sample, license or methodological demonstration.

[W01]: https://support.similarweb.com/hc/en-us/articles/18876356573725-Everything-you-need-to-know-about-Similarweb-s-2024-Data-Version-Update
[W02]: https://www.prnewswire.com/news-releases/earnest-analytics-increases-orion-panel-sales-by-4x-adds-historic-data-301906934.html
[W03]: https://facteus.com/products/arbiter
[W04]: https://www.reveliolabs.com/faq
[W05]: https://sensortower.com/solutions/finance
[W06]: https://sensortower.com/product/mobile-app/app-performance-insights
[W07]: https://python-sdk.dev.kpler.com/_modules/kpler/sdk/resources/trades_snapshot.html
[W08]: https://python-sdk.dev.kpler.com/_modules/kpler/sdk/resources/trades_updates.html
[W09]: https://www.census.gov/data/developers/data-sets/international-trade.html
[W10]: https://fred.stlouisfed.org/docs/api/fred/fred_vs_alfred.html
[W11]: https://journals.sagepub.com/doi/10.1177/00491241221099552
[W12]: https://www.kellogg.northwestern.edu/faculty/petersen/htm/papers/standarderror.html
[W13]: https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015.pdf
[W14]: https://www.nber.org/papers/w20592
[W15]: https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf
[W16]: https://escholarship.org/uc/item/24w173zx
[W17]: https://docs.similarweb.com/api-v5/support-and-faq/faq
[W18]: https://www.earnestanalytics.com/datasets/orion-credit-card-data
[W19]: https://docs.placer.ai/reference/faqs-1
[W20]: https://keepa.com/api-docs/product-object.html
[W21]: https://facteus.com/products/onyx
[W22]: https://www.facteus.com/cpg-sku-data
[W23]: https://panjiva.com/api-guide/spec/
[W24]: https://panjiva.com/api-guide/data-selection/data-sources
[W25]: https://w3.importgenius.com/faq
[W26]: https://w3.importgenius.com/features/api-integration
[W27]: https://www.datamyne.com/our-product/global-trade-data-api/
[W28]: https://www.datamyne.com/our-product/global-trade-analytics/
[W29]: https://www.help.cbp.gov/s/article/Article-1108
[W30]: https://www.kpler.com/blog/kpler-completes-acquisition-of-spire-maritime-strengthening-maritime-intelligence-capabilities
[W31]: https://servicedocs-sm.kpler.com/messages-api/
[W32]: https://servicedocs-sm.kpler.com/historical-positions-api/
[W33]: https://sensortower.com/product/digital-advertising/pathmatics?directory=true
[W34]: https://github.blog/changelog/2026-09-04-new-api-endpoint-provides-privacy-safe-star-history-data/
[W35]: https://github.com/orgs/community/discussions/206104
[W36]: https://huggingface.co/docs/hub/models-download-stats
[W37]: https://www.dol.gov/agencies/eta/foreign-labor/performance
[W38]: https://docs.greenhouse.io/job-board.html
[W39]: https://www.datasets.reveliolabs.com/faq.html
[W40]: https://investor.tsmc.com/english/monthly-revenue/2026
[W41]: https://investor.tsmc.com/english/financial-calendar
[W42]: https://ir.chipotle.com/2026-07-29-CHIPOTLE-RAISES-FULL-YEAR-COMPARABLE-SALES-GUIDANCE-ON-STRONG-Q2-MOMENTUM
[W43]: https://www.sec.gov/Archives/edgar/data/1562088/000162828026012494/duol-20251231.htm
[W44]: https://www.sec.gov/Archives/edgar/data/1562088/000162828026029790/q1fy26duolingo3-31x26share.htm
[W45]: https://corporate.mcdonalds.com/content/dam/sites/corp/nfl/pdf/MCD%202025%20Annual%20Report.pdf
[W46]: https://panjiva.com/info/customer_agreement
[W47]: https://www.sec.gov/newsroom/press-releases/2021-176
[W48]: https://www.ams.usda.gov/market-news/grocerystore
[W49]: https://support.gs1.org/support/solutions/articles/43000734283-what-is-a-global-trade-item-number-gtin-
[W50]: https://docs.github.com/en/rest/activity/starring?apiVersion=2026-03-10
[W51]: https://alfred.stlouisfed.org/help
[W52]: https://www.census.gov/about/policies/quality/standards/standardd3.html
[W53]: https://www.nber.org/papers/t0326
[W54]: https://www.clevelandfed.org/publications/working-paper/2011/wp-1120-advances-in-forecast-evaluation
[W55]: https://www.data-dictionary.reveliolabs.com/methodology.html
[W56]: https://sensortower.com/product/connect
[W57]: https://support.similarweb.com/hc/en-us/articles/32914267250077-Similarweb-s-Data-Accuracy
[W58]: https://www.census.gov/foreign-trade/guide/sec2.html
[W59]: https://www.census.gov/foreign-trade/Press-Release/ft900_index.html
[W60]: https://www.sec.gov/Archives/edgar/data/1816017/000095017025058698/spir-20250425.htm
