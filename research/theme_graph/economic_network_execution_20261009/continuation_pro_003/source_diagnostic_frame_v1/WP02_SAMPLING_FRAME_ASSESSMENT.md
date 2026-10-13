# WP02 — Actual sampling-frame assessment

**Disposition: `NOT_READY — NO_120_ISSUER_SELECTION`.** The bounded inspection is complete. The accepted diagnostic cannot be instantiated from the inspected current repository inputs without inventing issuer resolution, primary-listing assignments, valuation vintage or selection policy. No issuer cohort was frozen; no relationship-vendor output was consumed; no production or predictive admission follows.

This is the actual outcome of a source-frame execution task, not a replacement proposal for the research commission. It supplies measured input deficiencies, reusable components, an exact field handoff and the primary-data route needed to remove those deficiencies. Root retains implementation, acquisition, procurement and adjudication custody.

## 1. The accepted requirement and the remaining policy gap

The controlling sampling instructions are WP02 in the [accepted implementation masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/research/theme_graph/economic_network_20261008/IMPLEMENTATION_MASTERPLAN.md), lines 79–93, and §6 of the [accepted source strategy](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/research/theme_graph/economic_network_20261008/SOURCING_AND_COMPETITIVE_DILIGENCE.md), lines 130–158. Both files were fetched at the assigned immutable revision and their Git blob identities agree with the accepted local source package. This does not infer blanket architectural adoption from the earlier research merge.

| Primary-listing stratum | Issuers | Sector groups | Size composition within each sector group |
|---|---:|---|---|
| US | 24 | Six groups, four issuers each | Two large, one mid, one small |
| CN_MAINLAND | 24 | Same | Same |
| HK | 24 | Same | Same |
| CA | 24 | Same | Same |
| INT | 24 | Same | Same; additionally eight UK, eight Japan, eight EU |
| Total | 120 | 30 stratum/sector groups | 60 large, 30 mid, 30 small |

The six named groups are **semiconductor/cloud, industrials, consumer, energy/materials, financials and healthcare**. They are diagnostic groups; they are not the eleven broad sector labels present in several current tables. The design also requires one issuer per dual listing, a fixed selection date and market-capitalization basis, company identifiers, selected source scope, document availability, and manual source annotation before vendor consumption. Annual reporting periods 2023–2025 and actually available 2026 interim/material-event documents are the specified document scope. At least 30 difficult cases, six per geographic stratum, require independent adjudication. [Accepted sources above.]

**The accepted text does not give numeric large/mid/small thresholds, a market-cap date, an issuer-versus-security capitalization rule, a currency conversion rule, or an executable sector crosswalk.** Those are genuine unfilled inputs. S&P 400/600 membership, a Nasdaq market category, an ETF holding weight, or a JPX market segment cannot silently become a size threshold. No threshold has been selected to make the observed data fit the requested quotas.

The eight/eight/eight constraint is simultaneous with INT's sector and size quotas. A procedure that independently takes four names per sector and checks only the total of 24 is insufficient. Once the frame and policy are accepted, the INT selection needs a deterministic constrained allocation across country group and sector/size cells. No additional per-country sector quota is implied by the accepted text.

## 2. Exact source and observation boundary

The assigned repository is `mastermindx-market-intelligence/macro`, revision **`4d736c55adb630a4a8eb11b261e31acd0f6dc48b`**. Read-only native identity checks observed:

- Device `m2studio`, Darwin `25.5.0`, `arm64`.
- Workspace `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-observations-20261009-pro-003`.
- Branch `sol/web-gmi-economic-observations-20261009-pro-003`, HEAD equal to the assigned revision when initially checked.
- Common Git directory `/Users/chriswong/Documents/Cluade/Macro Dashboard/.git`.

All dataset reads used **actual fixed-ref Git object bytes** through `git --no-lazy-fetch --no-optional-locks`. Python ran with `-B`; Parquet was parsed with the installed `pyarrow.parquet` library, without importing application modules, invoking producers, or constructing runtime/source clients. The five native read processes—25398, 28554, 34174, 38807 and 49845—each completed with exit code 0. The detailed table observations span `2026-10-09T10:31:47.590938+00:00` through `2026-10-09T10:36:22.826197+00:00`.

The bounded search first enumerated **72,062 tracked path names under `data/` and `config/`**, then applied declared filename terms, yielding 252 candidates. Most were irrelevant histories, including crypto files; no contents were read merely because a filename matched. Follow-up navigation was restricted to named producers, the Canadian and mainland-sector directories, and specifically referenced metadata tables. Thirteen Parquet files and six other metadata/config files were profiled. Separate registry, source-contract and identity-receipt reads supplied interpretation. The complete path filters, selected files, digests and process completion evidence are represented in `inspection_source_manifest.json` and supporting JSON files.

**Runtime availability is not established.** All thirteen inspected Parquet paths returned false for `os.path.isfile` in the queried pro-003 worktree; the two inspected configuration files were present and byte-equal to their fixed-ref objects. The data therefore exists as parsed committed artifacts, not as demonstrated materialized application inputs at those workspace paths. This assessment did not hydrate the sparse worktree, inspect another native data root, enumerate host stores, fetch Git objects, or invoke the application. No conclusion about every dataset elsewhere on the host is warranted.

Primary web pages were inspected only as rendered documentation or navigation evidence. No new exchange list, financial document, vendor sample or capture was acquired into a source store. No raw-response SHA-256 is attributed to a web rendering. Web access failures remain visible in the primary route register.

## 3. What the stored artifacts actually contain

The following quantities come from parsed immutable Parquet/JSON bytes, rather than comments describing intended output. Full SHA-256 values, byte counts and schemas are in `inspection_source_manifest.json`; full field null counts are in the profile files.

| Stored artifact | Actual population unit and count | Useful information | Deficiency for WP02 |
|---|---|---|---|
| `data/reference/security_master.parquet` | 2,384 security rows | Stored security/issuer identifiers, listing keys, venue/country, issuer evidence state, observation dates, supersession | Only US/CN/HK listing countries; no primary-global-listing assertion, sector, cap, document inventory |
| `data/reference/issuer_master.parquet` | 1,215 stored issuer rows | 1,211 `sec_company_tickers` evidence rows and four `legacy_mint` rows | Current registrant evidence only; nine legal names and four CIK/evidence dates are null; legacy rows are not resolved issuer proof |
| `data/reference/vendor_aliases.parquet` | 6,046 alias rows | Existing owner-maintained alias/security links and some dated boundaries | Only one non-null `known_at`/evidence/binding tuple; does not establish historical identity for all aliases |
| `data/universe/membership.parquet` | 3,600 ticker/group rows, 2,938 distinct tickers | S&P 500/400/600 and Russell 2000 membership ledger; broad sectors and first/last observations | Ticker/group grain, not deduplicated issuer grain; no listing country, global primary listing, cap or source-availability receipt |
| `data/breadth/constituents.parquet` | 503 symbol rows | Eleven broad sector labels and names | Index roster; no cap, issuer ID or dataset observation field |
| `data/breadth/ticker_sectors.parquet` | 1,515 distinct ticker rows | 503 `gics_sp500`, 400 `gics_sp400`, 600 `gics_sp600`, 12 `sic_mapped` source labels | No dated source receipt in the table; no semiconductor/cloud crosswalk or issuer IDs |
| `data/polygon_universe/reference.parquet` | 509 distinct ticker rows | Eleven broad sectors; 504 positive finite values labelled USD, five nulls; all `asof=2026-10-07` | Display cache build date, not independently proved valuation date; no retained per-value response/availability, issuer or primary-listing binding |
| `data/stock_identity/partition/universe_snapshot_v1.parquet` | 2,781 symbol/price-plane rows | Tape boundaries and compute/blind eligibility; all `asof=2026-08-13` | Price-tape partition, not issuer/sector/capitalization frame; first price date is not listing or document availability |
| `data/symbol_directory/snapshots/2026-10-09.parquet` | 13,293 security-directory rows | Symbols, exchange, security name, ETF/test/preferred flags; separate completion receipt | Security types are mixed; no economic issuer deduplication, sector or cap; listing venue does not prove primary global listing |
| `data/symbol_directory/cik_map/2026-10-05.parquet` | 10,440 ticker/CIK/title rows | SEC registrant reference, with separate completion receipt | CIK reference does not independently establish primary listing, complete global coverage or historical issuer lineage |
| `data/canada_breadth/constituents.parquet` | 74 symbol rows | Curated breadth roster, ten sector labels | No healthcare label in this particular table; no identity, cap or dates; producer explicitly describes curated large-cap scope |
| `data/canada_search/members.parquet` | 216 ticker rows | Name, sector, holding weight, volume; includes five `Health Care` rows | iShares XIC holding-based search population, no issuer ID, primary listing, market cap or observation date; weight is not capitalization |
| `data/china_sectors/membership.parquet` | 5,223 interval rows, 5,221 distinct tickers, 5,220 open intervals | 31 Shenwan L1 labels, inclusion/end dates and first collection dates | No resolved global issuer key, cap or selected six-group mapping; ticker/membership rows are not issuers |
| `data/hk_stocks_ext/_universe.json` | 582 ticker strings | HSCI constituent-source URL and `as_of=2026-10-08T15:03:35Z` | Index subset; strings lack issuer identity, sector, cap and primary/secondary listing evidence |

The Canadian search table was found by following its actual producer after the initial filename pass. It prevents a false conclusion that Canadian healthcare is absent from the estate. Its five healthcare labels still do not establish the four requested healthcare issuers at the required two/one/one capitalization mix. The 74- and 216-name tables must remain separately described.

The additional inspected `data/baskets/membership.json` contains 49 curated US theme baskets. Its own metadata distinguishes back-projected inclusion dates from actual curation dates. It is not an independent global sampling frame. `config/rotation_universe.json` describes a registered US rotation series set, not an issuer census. `config/market_reference.yml` is explanatory reference copy without live issuer values. These were rejected by content, not merely by their filenames. [Profiles and source-contract copies.]

### 3.1 Identity counts reconcile, but international issuer coverage does not

The security master contains 1,219 US, 1,018 CN and 147 HK rows. No row carries CA, UK, Japan or an EU listing-country value. This is a statement about this exact authority table, not all potential overseas listings or ADR issuers.

All 1,018 CN and 147 HK rows are `NO_ISSUER_EVIDENCE`. They have observed security identities; they cannot be treated as 1,165 deduplicated economic issuers. Across the full table there are 1,169 `NO_ISSUER_EVIDENCE` rows, 1,214 `RESOLVED` rows and one `DEFERRED_IDENTITY_EXCEPTION`. One unevidenced row is a retained `SUPERSEDED_DUPLICATE_MINT`. Excluding it leaves 2,383 active rows and **1,168 active unevidenced rows**, agreeing with the receipt. This explains the one-row difference without overwriting either observation.

The 1,214 active resolved security rows map to **1,211 distinct stored issuer IDs**, all on the US-listing-country axis. Three extra share-class/security rows do not create three extra issuers. This is the strongest immediate reusable identity pool observed; it is not a verified pool of 1,211 issuers whose primary global listing is US.

The [registry contract](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/config/dataset_registry.yml), lines 252–374 and 460–496, gives the existing `macro-dashboard`/`scripts/build_security_master.py` custody and makes resolved evidence a prerequisite for issuer aggregation. It explicitly refuses to equate `effective_at` with an actual listing date and describes historical issuer lineage as unavailable. Those limitations remain binding. No alternative issuer allocator or private namespace was created.

### 3.2 Vintages are different facts

The October 9 directory artifact hash, row count and schema agree with its saved completion receipt. That receipt records collection start/end at `2026-10-09T03:23:46.894658Z` and `2026-10-09T03:23:48.114931Z`. The October 5 CIK artifact likewise agrees with its receipt, whose collection interval is `2026-10-05T02:16:26.646352Z` to `2026-10-05T02:16:29.577967Z`. Both receipts state that source-response bytes were **not retained** and are **not replay-verifiable**, although response commitments were recorded at capture. This assessment verified the committed artifact binding, not a replay of their original HTTP responses. Their purpose flags remain context/reference-only.

The universe ledger's first observations range from June 13 to October 9, 2026. Its producer documents a June 14–July 10 accrual gap and a cold-start limitation; sector/name values are refreshed on present-member updates. A reconstructed membership interval does not establish a historical sector revision or a document's first availability. The stock-identity tape's first dates, reaching back to 1962, are especially unsuitable as listing dates. [Current `engine/universe_history.py`; stored profiles.]

The mainland sector store has first-collection dates from September 3–30, 2026, whereas reported membership starts reach back to December 13, 2021. The producer deliberately distinguishes these clocks and refuses pre-accrual historical replay. The cap cache's producer writes `date.today()` into `asof`; its request for `market_cap` has no explicit historical valuation date and its final table retains no per-value response clock. None of these dates can be substituted for a frozen global market-cap valuation date. [Current `collectors/china_sectors.py` and `scripts/build_polygon_universe.py`.]

## 4. Measured reusable bounds and excluded shortcuts

There is **no selected US subcohort** in this package. The evidence supports resource bounds that can reduce later work:

- Up to 1,211 current resolved US-listing issuer IDs can be handed back to the incumbent identity owner for primary-listing verification and complete source joining.
- Up to 504 positive, finite cap-bearing ticker records are present in the current display cache. This is a cap-record bound; it is not 504 distinct, eligible issuers. No unproved alias join or share-class aggregation was used to produce a stronger count.
- The membership ledger supplies 2,938 distinct ticker strings across 3,600 records. The 662 extra records reflect repeated ticker appearances across groups; ticker uniqueness itself would still not deduplicate legal issuers.
- The directory offers a considerably larger security-discovery pool, with 5,769 ETF flags, 378 preferred flags and 37 test flags. These flags can overlap; their counts must not simply be subtracted and presented as an operating-company census. The manifest's common-stock figure is explicitly an estimate.

No annual-document availability inventory, accepted primary-listing assignment, size-policy application or six-group source-backed sector adjudication was supplied for the requested 120. **Global eligible-frame size and each stratum's eligible issuer count remain unknown, not zero.** The frozen cohort size is zero because no selection was made. Source coverage, precision, recall and unknown-case rates are therefore null; a 0/120 coverage statistic would falsely imply 120 completed source requests.

The preserved exclusion classes include unevidenced/deferred issuer identity, superseded duplicate securities, unresolved primary listing, absent capitalization/vintage, unadopted sector mapping, undated roster provenance and unproved source availability/rights. Their row counts are table-specific and may overlap. They are not added into an invented denominator of globally excluded issuers.

## 5. Field-by-field handoff needed for a valid frame

`required_field_mapping.json` records this handoff as structured research requirements. It does not register a new dataset or adopt a new application schema.

| Required fact or control | Reusable incumbent field/source | What must be supplied before selection |
|---|---|---|
| Economic issuer identity | `security_master.issuer_id`, `issuer_state`, `issuer_cik`; `issuer_master` | Resolved legal-entity evidence under the existing owner; foreign issuer resolution and one retained identity across listings/classes |
| Security-to-issuer mapping | Stored security ID, listing key, aliases, migrations | Current authoritative linkage, conflict/exception disposition and a source-vintaged cross-listing record; never symbol-only equality |
| Primary listing and stratum | `country` and `mic` describe an observed listing | Source establishing primary/secondary or dual-primary status; an accepted tie rule for dual-primary cases; geographic/venue perimeter |
| Six-group sector assignment | Broad GICS/SIC-derived, Shenwan and ETF-sector labels | Frozen crosswalk, dated input classification and activity evidence for semiconductor/cloud and mixed businesses; explicit unmappable status |
| Market capitalization | 504 current display-cache values | Accepted issuer/security basis; original value, currency, units, valuation timestamp/date, source observation/publication clock and revision; approved aggregation/FX rules |
| Size category | No accepted numeric rule | Exact thresholds, boundary inclusivity, currency, cutoff and handling of unquoted classes, deposits/ADRs, missing/suspended values; rule frozen before candidate selection |
| Population coverage | Source-specific rosters and current-directory receipts | Declared source population and exclusions, instrument eligibility, board/venue coverage, pagination/row reconciliation and source version |
| Document inventory | Existing filing/source owners, not these universe tables | Attempt/status records for specified annual and current interim/event scope, actual availability, language, URL/accession and retained evidence identity where lawful |
| Time and correction | Receipt clocks and some collection dates | Distinct valid/reporting, publication, observation and system-availability clocks; precision and revisions preserved; no reconstruction from filename or Git time |
| Rights for this purpose | Existing source-policy/rights owners | Exact authorized research collection, retention, derivative use and publication scope; current source terms and entitlement where applicable |
| Deterministic selection | Accepted quota shape only | Frozen method inputs, seed/order and tie rule, joint INT feasibility, complete candidate disposition and no vendor-outcome-dependent replacement |
| Difficult-case adjudication | Accepted stress-label vocabulary | Thirty prespecified difficult cases across five strata, absence logs, fixed substitution rule, independent review and disagreement record |

Availability is a diagnostic outcome as well as provenance. Once identities and the frame are valid, a source fetch failure or a missing annual report must remain a recorded case, not cause silent replacement with an easy disclosed company. New listings may lack earlier annual periods; record the proper scope/status rather than fabricating documents or filtering out all recent entrants. A current-issuer diagnostic over 2023–2025 documents is not a historical investment universe or a survivorship-free backtest.

## 6. Lawful primary-data route

The following is a concrete acquisition handoff for incumbent source owners. No route was launched by this lane. The primary pages establish navigation, declared fields or terms only; an owner still needs a completed, rights-cleared snapshot and a usable byte/clock receipt. `primary_source_route_register.json` preserves successes, rendering limitations and access failures separately.

### US

Reuse the already retained Nasdaq-directory and SEC-reference artifacts where their current purpose/profile permits. The [Nasdaq field definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs), sections “Nasdaq-Listed Securities” and “Other Exchange-Listed Securities,” describe security symbols, exchange/security-type fields and a file-creation timestamp. They supply a listing-discovery route, not primary-global-listing or cap evidence. The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), “data.sec.gov/submissions,” supplies current/former registrant names, exchanges/tickers and filing-history navigation without an API key. Use the existing SEC source owner and its access policy. Neither source alone supplies a market-capitalization frame. [P01–P02.]

For capitalization, require an authorized original exchange close/share-capital source or an explicitly entitled reference feed with declared valuation semantics. If a calculation uses issuer-reported outstanding shares and a price, preserve both component dates, share-class/ADR treatment and all revisions. A fiscal-period share count or SEC non-affiliate public float is not automatically selection-date total issuer capitalization. Until the owner chooses and proves this basis, the current Polygon cache remains display-reference evidence only.

### Mainland China and Hong Kong

Use official exchange/listing and issuer disclosures, preserving native identifiers and language, to resolve legal entities and listing relationships. The [SSE stocks/depositary-receipts list](https://www.sse.com.cn/assortment/stock/list/share/) was discoverable, but this web rendering did not expose a validated complete export. An [official JPX cross-exchange page](https://www.jpx.co.jp/english/markets/equities/foreign/szse/index.html) links directly to SZSE's stock-data search; following that link failed in this retrieval. These are explicit access/schema gaps, not completed mainland directories. The owner must declare the mainland venue/board perimeter, including the disposition of markets outside the current SSE/SZSE identity table, before selecting 24. [P03–P04.]

The [HKEX Securities Lists page](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) exposes official full-list, ISIN and dual-counter navigation. The attempted full-list link did not return a usable artifact here. Currency counters, distinct securities, ADRs, A/H classes and economic issuers require separate mapping. Existing HSCI strings are an index subset. For primary or dual-primary status, preserve the relevant exchange/issuer listing disclosure; for cap, retain the exact share/price/currency basis and date. The requested research collection/retention and any market-data use must be covered by the existing source policy; index membership or web visibility does not grant that scope. [P05.]

### Canada

The [TSX/TSXV official company directory](https://tsx.com/en/listings/listing-with-us/listed-company-directory) was found in primary search, but direct retrieval returned 403. The next lawful step is the existing source owner's supported directory access or licensed exchange extract, with dated issuer/security and field coverage. Do not evade that response or replace it with a success-dependent handpicked list. Determine the declared Canadian venue perimeter and use issuer/exchange disclosures to reconcile cross-listings. Supplement with the approved Canadian filing/issuer route for legal identity, share capital and document availability. The existing XIC-derived 216-name table may aid navigation after its use rights are confirmed; ETF weights and volumes cannot fill capitalization. [P06; current `collectors/canada_universe.py`.]

### International: UK, Japan and EU

For the UK, the [LSE reports page](https://www.londonstockexchange.com/reports) is primary discovery for issuer/instrument reports and archive downloads. Its search rendering exposed this navigation; direct opening returned no body. The [LSE issuer-profile help](https://www.londonstockexchange.com/help/whats-issuer-profile-our-story) search rendering describes issuer market cap and industry fields, but no actual report schema or row bytes were obtained. Have the source owner secure the specific dated issuer and instrument files and reconcile their identities and cap definitions. Freeze the UK market/instrument perimeter rather than assuming every London-traded security has its primary listing there. [P07–P08.]

For Japan, the [JPX TSE-listed-issues page](https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html), lines 74–97, identifies a previous-month-end list and sequential updates, including a correction example. This is a viable original-list route, but no workbook was acquired or parsed. **JPX's [current terms](https://www.jpx.co.jp/english/term-of-use/index.html), General section, condition commercial data collection or secondary use on prior permission or a paid contract.** Root's source/rights owner must establish that permission before commissioning the commercial frame extract; a public download link is not sufficient. The list's vintage, revision, sector mapping and cap evidence must still be validated. [P09–P10.]

For EU listings, the [Euronext equities directory](https://live.euronext.com/en/products/equities/list) renders fields for name, ISIN, symbol, market, last value and date/time, plus market/industry filters. It did not expose a complete row export in this inspection. Its [official data catalogue](https://www.euronext.com/en/data/data-products?product_service%5B0%5D=5940) supplies a reference-data and historical-data acquisition route. This is an exchange-group candidate pool, not a demonstrated census of EU issuers. Freeze the included EU markets and exclusions, or extend the source-owner frame to the remaining declared markets; do not count a non-EU venue merely because the operator is European. Obtain the purpose-specific terms and exact extract schema, then prove issuer/primary-listing and cap joins. [P11–P12.]

### Cross-border identity support

The [GLEIF Open Data page](https://www.gleif.org/en/about/open-data), lines 355–360, documents legal-entity reference data under CC0 and links to LEI and mapping resources. It is a useful lawful identity-evidence route. The dedicated terms-page open failed, so this package relies on the successful Open Data page for that narrow fact; mapping products must be checked for their own exact scope. LEI evidence should be submitted to the existing identity owner. It does not itself supply primary-listing status, market cap, a complete population of listed issuers or a new authoritative GMI issuer ID. [P13.]

## 7. Required owner actions and falsifiable completion conditions

The next work is concrete and can be done without waiting for the C01 producer:

1. **Research/commissioning owner freezes missing method inputs:** cap basis/date/currency/thresholds and boundary rules, geographic/venue and instrument perimeter, six-group crosswalk, cross-listing/dual-primary tie rules, deterministic selection ordering and stress-case replacement rule. Keep the accepted 120 and its simultaneous quotas unless the commissioning owner explicitly amends them.
2. **Incumbent source and rights owners bind permissible data routes:** reuse proven stored observations first, obtain the missing original-list/reference extracts and required permissions, and preserve precise source/valuation/observation vintages. Do not create another identity or availability registry.
3. **Incumbent identity owner supplies foreign resolved mappings and exceptions:** retain legacy IDs and migrations, prevent security/class/currency-counter duplication, and publish explicit unresolved cases. Nothing here authorizes minting new production issuer identities.
4. **Research data assembly produces a complete pre-vendor candidate-frame receipt:** ordered inputs and hashes, source population and completeness, field mappings, missingness and exclusions, all selection-policy bindings, and source-attempt/document inventory. Freeze a deterministic cohort only if every requested quota is feasible under those unchanged inputs. Log infeasible cells; do not loosen thresholds after seeing the result.
5. **Independent reviewers verify the frame and source labels:** reproduce quota totals and one-issuer uniqueness, inspect a source-linked sample of primary-listing/size/sector assignments, and keep unavailable/anonymous/undisclosed cases in their correct denominators. Freeze the 30 difficult cases before relationship-vendor outputs are consumed.

The current conclusion would be falsified by an actual, lawfully held source snapshot at the declared vintage that supplies all required identifiers, primary-listing assignments, sector evidence, cap basis and document-status metadata, together with an adopted numeric size policy and a reproducible feasible selection. A path name, a collector implementation, a successful C01 inspection, a current price, or a table with 120 arbitrary symbols does not falsify it.

**No executable selector or selection-validation contract is published in this package**, because the accepted thresholds and necessary frame fields are absent. That is the condition in the principal's assignment, not a new approval barrier. The factual audit and source-deficiency receipt are complete. Future source acquisition and the missing method adoption are distinct root-owned actions; no supplier messages, purchase, job launch, source/store edit, application test/replay or Git mutation was performed here.

## 8. Deliverables, verification and scope of the result

Core artifacts are this report, `frame_deficiency_receipt.json`, `required_field_mapping.json`, `primary_source_route_register.json`, and `inspection_source_manifest.json`. Supporting profiles preserve all measured schemas, counts, nulls, clocks and table hashes. Seven source-contract copies match their exact Git blob identities; their SHA-256 values are in `source_contract_bindings.json`. `PACKAGE_MANIFEST.json` binds the final local deliverable set.

Useful bounded outcome: **the existing estate supplies reusable US identity/reference components and regional discovery/sector subsets, but it does not supply the requested global issuer sampling frame.** No international issuer identities, market caps, listing facts, availability dates or quantitative selection thresholds were fabricated. Earlier six-case pilot and replay artifacts were untouched. The six purposively selected cases remain a separate semantic/native pilot, with no statistical-cohort or 120-issuer coverage implication.

**Source-diagnostic research only. Production admission: false. Predictive admission: false. Selection frozen: false. Full source diagnostic: not run.**
