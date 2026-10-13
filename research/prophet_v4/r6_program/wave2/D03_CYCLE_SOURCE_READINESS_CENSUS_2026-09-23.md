# D03 Cycle Source-Readiness Census — 2026-09-23

## SOURCE_SHA

- OBSERVED: `10166ad5272f8ca24161aed5bdd8d3980271489e` — detached census base before the skeleton commit, as returned by `git rev-parse HEAD`; at that moment it was the tip of `origin/main` (`git rev-parse origin/main`, rc 0).
- INFERRED: anchor facts cited below use `10166ad5272f`, not the PR head, because they read immutable committed source objects. Later `origin/main` fast-forwards do not change those object contents; a post-read SHA re-check must be made if a claim is changed or challenged.

## ANCHORS READ

- D03 requires exact usable dates, field semantics, vintage/correction lineage, original-universe coverage, delistings, publication/processing rights and source costs; forbids backdating current membership/events, guessed availability lags, relabeling broad series as granular subthemes, and assumed licenses: `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/DECISION_REGISTER.json:62@10166ad5272f`–`:68@10166ad5272f`.
- Q01 requires decision-time source revisions and owner clocks, controls current-only discovery and future labels, and maps irrecoverable history to prospective-only use: `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json:6@10166ad5272f`–`:15@10166ad5272f`.
- Q07 requires a Cycle source-readiness candidate selected by coverage/mapping before return inspection, with vintage orders/backlog/shipments/inventories/production, issuer segments and failure histories: `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json:172@10166ad5272f`–`:181@10166ad5272f`.
- Configured vintage set: `config.yml:124@10166ad5272f`–`:157@10166ad5272f`.
- ALFRED/FRED dataset rows: `config/dataset_registry.yml:199@10166ad5272f`–`:248@10166ad5272f`.
- Publication-lag table and business-cycle vintage map: `engine/business_cycle.py:124@10166ad5272f`–`:140@10166ad5272f`.
- ALFRED collection, initial-release reader and as-of reader: `collectors/fred.py:176@10166ad5272f`–`:195@10166ad5272f`; `:239@10166ad5272f`–`:262@10166ad5272f`.
- Local-store depth audit contract and verdict thresholds: `scripts/audit_alfred_depth.py:1@10166ad5272f`–`:17@10166ad5272f`; `:54@10166ad5272f`–`:95@10166ad5272f`.

## ANCHORS ACCOUNTED (repair r3)

- `engine/cycles.py` provides the instrument-level Cycle timing machinery: multi-timeframe indicator snapshots, daily/investor cycle position, entry timing, calibrated ladder states and related technical readouts from supplied price series. It is not a candidate B16/B18 Cycle-source input: it consumes a price tape after an economic/source process has supplied it and cannot establish vintage depth, issuer mapping, failure coverage, definition tolerance or rights. It changes no Q1–Q6 verdict. Evidence: `engine/cycles.py:349@10166ad5272f`–`:394@10166ad5272f`; `:423@10166ad5272f`–`:434@10166ad5272f`; `:622@10166ad5272f`–`:723@10166ad5272f`; `:2638@10166ad5272f`–`:2685@10166ad5272f`.
- `engine/sector_cycles.py` provides sector-ETF and generalized level-series cycle kernels: GICS-sector metadata, price-derived swings and phases, relative-strength reads, and a monthly/daily `record_series` kernel that can consume a level series. It is not a candidate B16/B18 Cycle-source input: it transforms series already provided to it. Its XLK–XLRE ETF universe is not historical industrial capital-goods/machinery issuer membership, and its transformations do not solve vintage availability, historical industry mapping, survivorship or rights. It changes no Q1–Q6 verdict. Evidence: `engine/sector_cycles.py:1@10166ad5272f`–`:25@10166ad5272f`; `:45@10166ad5272f`–`:57@10166ad5272f`; `:503@10166ad5272f`–`:555@10166ad5272f`; `:591@10166ad5272f`–`:594@10166ad5272f`.
- `engine/vintage_stamp.py` provides a research-result stamp and refusal gate for price plane, adjustment mode, universe date, point-in-time basis, survivorship flag, coverage, dead-name coverage and era cohort. It is not a candidate B16/B18 Cycle-source input: it is a vintage-stamping and integrity utility, not a source, and does not acquire or date economic Cycle observations. It changes no Q1–Q6 verdict. Evidence: `engine/vintage_stamp.py:1@10166ad5272f`–`:23@10166ad5272f`; `:55@10166ad5272f`–`:85@10166ad5272f`; `:91@10166ad5272f`–`:177@10166ad5272f`.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/baseline_r5/inputs/PROPHET_US_EARNINGS_CYCLE_R4.md` provides the binding R4 design context for Cycle Capture: economic mechanism, issuer funding, and original-equity recovery must remain separate from technical repair/current entry; it recommends industrial capital-goods/machinery as the first source-readiness candidate subject to measured vintage, rights, issuer mapping and failed-name coverage; and it establishes failure-inclusive evaluation and lifecycle/delisting treatment. It is not a candidate B16/B18 Cycle-source input: it is a proposed design packet and consumer of revised data only, not the source clock, vintage history, membership, failure panel or rights receipt needed by D03. It changes no Q1–Q6 verdict. Evidence: `research/prophet_v4/r6_fable_meta_ceo_handoff/baseline_r5/inputs/PROPHET_US_EARNINGS_CYCLE_R4.md:13@10166ad5272f`–`:17@10166ad5272f`; `:137@10166ad5272f`–`:148@10166ad5272f`; `:151@10166ad5272f`–`:161@10166ad5272f`; `:233@10166ad5272f`–`:239@10166ad5272f`.

## Q1 VINTAGE LEG INVENTORY

VERDICT: PARTIALLY FOUND. The configured legs, semantics, modeled release clocks and code revision paths are FOUND. The FIRST USABLE VINTAGE DATE for every leg is UNKNOWN because the sparse tree omits `data/fred_vintage/vintages.parquet` and no committed depth report covering this set was found.

Observed code law:

- `config.yml` replaces the collector default with `fred.vintage_series`: `config.yml:124@10166ad5272f`–`:157@10166ad5272f`.
- Business-cycle `PUB_LAG_M` is a modeled per-leg floor, not a measured availability receipt; the code says the base lag is added to the caller's stress lag: `engine/business_cycle.py:122@10166ad5272f`–`:129@10166ad5272f`.
- Only `ICSA`, `UMCSENT`, `PAYEMS` and `INDPRO` are wired into the business-cycle initial-release lookup; absent legs are scored on revised data and flagged revised: `engine/business_cycle.py:131@10166ad5272f`–`:140@10166ad5272f`; `:151@10166ad5272f`–`:158@10166ad5272f`.
- Collector output type 4 stores one initial release per period with `realtime_start`; absent/no-key runs return empty: `collectors/fred.py:176@10166ad5272f`–`:203@10166ad5272f`.
- The depth audit reads only the local store unless `--probe-missing` is supplied, and probing explicitly requires `FRED_API_KEY`: `scripts/audit_alfred_depth.py:10@10166ad5272f`–`:12@10166ad5272f`; `:98@10166ad5272f`–`:108@10166ad5272f`.

No `ACOGNO`, `A34SNO`, `AMTMNO`, `IPMAN` or `IPBUSEQ` occurrence was found in the configured engine/config source at `10166ad5272f`. Receipt: `git grep -nE 'ACOGNO|A34SNO|AMTMNO|AMTMUO|NEWORDER|IPMAN|IPBUSEQ' 10166ad5272f -- ':!data' ':!site' ':!mockups' ':!verify_shots'`, rc 0, 43 lines; matched files included `config.yml`, `engine/business_cycle.py`, `engine/bottleneck.py`, `engine/glut_watch.py` and prose/tests, but none of the five absent symbols. `DGORDER` occurs only in prose/config-adjacent searches as durable-goods aggregate, not a machinery vintage leg.

| Leg | Economic semantics / adjustment | Modeled lag | Revision behavior in code | First usable vintage | Exact class | Deciding fact |
|---|---|---:|---|---|---|---|
| `AWHMAN` | Manufacturing production and nonsupervisory hours; seasonally adjusted index/hours proxy. | 1 month | Configured for collector vintage store, but absent from business-cycle vintage map; live/validation fallback is latest-revised. | UNKNOWN | prospective-only | Configured for collection; no measured local depth receipt. |
| `PERMIT` | New private housing permits; thousands of units, SAAR. | 1 month | Same collector-only vintage path; business-cycle fallback latest-revised. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `NEWORDER` | Nondefense capital goods excluding aircraft new orders; millions of dollars, SA. | 1 month | Same collector-only vintage path; business-cycle fallback latest-revised. | UNKNOWN | prospective-only | Capital-goods aggregate configured, but no measured local depth receipt. |
| `CMRMTSPL` | Real manufacturing and trade sales; millions of chained 2017 dollars, SA. | 2 months | Same collector-only vintage path; business-cycle fallback latest-revised. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `INDPRO` | Total industrial production index, 2017=100, SA. | 1 month | Mapped in `business_cycle.VINTAGE_SERIES`; `use_vintage` reads the first-published value, otherwise latest-revised. | UNKNOWN | prospective-only | Code path is PIT-capable, but local vintage depth is unavailable and unmeasured. |
| `ISRATIO` | Total business inventories/sales ratio, SA. | 2 months | Collector-only vintage path; business-cycle fallback latest-revised. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `MNFCTRIRSA` | Manufacturers' inventories/sales ratio, SA. | not in `PUB_LAG_M` | Collector-only vintage path; no business-cycle initial-release wiring. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `AMTMUO` | Manufacturers' unfilled orders, total manufacturing; millions of dollars, SA. | not in `PUB_LAG_M` | Collector-only vintage path; used elsewhere as backlog context on revised store data. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `AMTMVS` | Manufacturers' value of shipments, total manufacturing; millions of dollars, SA. | not in `PUB_LAG_M` | Collector-only vintage path; used elsewhere as shipment context on revised store data. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `CAPUTLG3344S` | Semiconductor and electronic-component capacity utilization; percent, SA. | not in `PUB_LAG_M` | Collector-only vintage path; config explicitly calls detail-vintage coverage plausible but unverified. | UNKNOWN | prospective-only | Config warning plus absent store. |
| `CAPUTLG334S` | Computer/electronic-products capacity utilization; percent, SA. | not in `PUB_LAG_M` | Same collector-only path. | UNKNOWN | prospective-only | Config warning plus absent store. |
| `CAPUTLG331S` | Primary-metal capacity utilization; percent, SA. | not in `PUB_LAG_M` | Same collector-only path. | UNKNOWN | prospective-only | Config warning plus absent store. |
| `PCU334413334413` | Semiconductor and related device manufacturing PPI; index. | not in `PUB_LAG_M` | Same collector-only path. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `PCU331110331110` | Iron and steel mills/ferroalloy manufacturing PPI; index. | not in `PUB_LAG_M` | Same collector-only path. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `IPG2211S` | Electric-power generation industrial production; 2017=100, SA. | not in `PUB_LAG_M` | Same collector-only path. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `CAPUTLG2211S` | Electric-power generation capacity utilization; percent, SA. | not in `PUB_LAG_M` | Same collector-only path. | UNKNOWN | prospective-only | No measured local depth receipt. |
| `WPU0543` | Industrial electric power PPI; index. | not in `PUB_LAG_M` | Same collector-only path. | UNKNOWN | prospective-only | No measured local depth receipt. |

Exact closure command (not run; requires a legitimately keyed collection into the approved store): `python3 -m scripts.audit_alfred_depth --series AWHMAN,PERMIT,NEWORDER,CMRMTSPL,INDPRO,ISRATIO,MNFCTRIRSA,AMTMUO,AMTMVS,CAPUTLG3344S,CAPUTLG334S,CAPUTLG331S,PCU334413334413,PCU331110331110,IPG2211S,CAPUTLG2211S,WPU0543 --output data/fred_vintage/alfred_depth_d03_cycle.json`. The receipt must expose `min(realtime_start)` and period count per leg; a modeled `PUB_LAG_M` must not be read as that date. Do not restore or write `data/` in this sparse tree.

## Q2 GRANULAR M3 SERIES

VERDICT: FOUND for machinery and capital-goods aggregates on FRED/ALFRED, with coverage and definition caveats. The prior 404 verdict was a probe defect: a multi-ID pipe query returned 404, while each valid single-ID CSV request returned 200. Whether every FRED initial-release CSV row is equivalent to the repository's keyed API output-type-4 contract remains UNKNOWN.

Measured public CSV probes, 2026-09-23:

- `A33SNO`, `A33SVS`, `A33SUO`, `A33STI` each returned HTTP 200 from single-ID FRED CSV and single-ID ALFRED CSV. Data begin 1992-02/1992-01 and end 2026-07; ALFRED CSV first observation dates match those dates. The erroneous combined request `https://fred.stlouisfed.org/graph/fredgraph.csv?id=A33SNO|A33SVS|A33SUO|A33STI` returned HTTP 404; it is a probe syntax result, not evidence that any component series is absent.
- Machinery subindustry new orders `A33CNO`, `A33DNO`, `A33ENO`, `A33INO`, `A33MNO` each returned HTTP 200 and 415 FRED data rows, first 1992-02, last 2026-07; representative single-ID ALFRED CSV calls also returned HTTP 0 and first vintage/observation date 1992-02.
- Capital-goods aggregate shipments/unfilled/inventories were not found at the tested IDs `A33XMVS`, `A33XMUO`, `A33XMTI` (HTTP 404). This does not prove Census absence; exact FRED/Census crosswalks are still needed.

| Claim | Exact FRED IDs measured | FRED/ALFRED vintage status | Census status | Claim support |
|---|---|---|---|---|
| Machinery total orders/shipments/unfilled/inventories | `A33SNO`, `A33SVS`, `A33SUO`, `A33STI` | FOUND: FRED HTTP 200; ALFRED HTTP 0 and dated history from 1992. Titles are Manufacturers' New Orders / Value of Shipments / Unfilled Orders / Total Inventories: Machinery; all millions SA, Census source. | Census aggregate table names `33S Machinery`: downloaded `aggseries.pdf`, line 99. | Granular machinery claims are supported at category grain, not at individual machine-type grain. |
| Construction machinery | orders `A33CNO`; tested shipment/inventory/unfilled IDs `A33CVS`, `A33CUO`, `A33CTI` all HTTP 200 | FOUND for the tested four; CSV spans 1992 through 2026 and new orders have ALFRED history from 1992-02. | `aggseries.pdf` names `33C Construction machinery manufacturing`: line 172. | Supported only as construction machinery category. |
| Mining and oil/gas field machinery | orders `A33DNO`; tested all four `A33D*` IDs HTTP 200 | FOUND for tested four; CSV spans 1992 through 2026 and new orders have ALFRED history from 1992-02. | `aggseries.pdf` names `33D`: line 173. | Supported at mining/oil/gas machinery category grain. |
| Industrial machinery | orders `A33ENO`; tested all four `A33E*` IDs HTTP 200 | FOUND for tested four; CSV spans 1992 through 2026 and new orders have ALFRED history from 1992-02. | `aggseries.pdf` names `33E`: line 174. | Supported at industrial machinery category grain. |
| Metalworking machinery | orders `A33INO`; tested all four `A33I*` IDs HTTP 200 | FOUND for tested four; CSV spans 1992 through 2026 and new orders have ALFRED history from 1992-02. | `aggseries.pdf` names `33I`: line 179. | Supported at metalworking machinery category grain. |
| Material-handling equipment | orders `A33MNO`; tested all four `A33M*` IDs HTTP 200 | FOUND for tested four; CSV spans 1992 through 2026 and new orders have ALFRED history from 1992-02. | `aggseries.pdf` names `33M`: line 183. | Supported at material-handling equipment category grain. |
| Farm machinery | tested `A33AVS` and `A33ATI`: HTTP 200; tested `A33ANO`, `A33AUO`: HTTP 404 | PARTIALLY FOUND: shipments and inventories exist at the tested IDs; orders/unfilled orders do not exist at those exact IDs. | `aggseries.pdf` names `33A Farm machinery and equipment manufacturing`: line 232. | Do not claim a complete four-measure farm-machinery vintage set from these probes. |
| Turbine / power transmission | tested `A33J*` orders/shipments/unfilled/inventories: HTTP 404 | UNKNOWN, not proven Census-absent: the aggregate Census label exists as `TGP TURBINES, GENERATORS, AND OTHER POWER TRANSMISSION EQUIPMENT` and subcategory `33J` (`aggseries.pdf` lines 297–298). | Exact-ID crosswalk/download contract missing. | UNSUPPORTED as an individual FRED vintage subtheme. |
| Nondefense capital goods ex-aircraft | repository aggregate `NEWORDER`; tested exact counterpart IDs `A33XMVS`, `A33XMUO`, `A33XMTI`: HTTP 404 | FOUND for `NEWORDER` orders only in repository; shipments/unfilled/inventories remain UNKNOWN at exact crosswalk IDs. | `aggseries.pdf` names `NXA NONDEFENSE CAPITAL GOODS EXCLUDING AIRCRAFT`: line 260. | Orders-only aggregate is supported; the four-measure granular aggregate is not established. |
| Semiconductor via M3 | no separate post-2010 M3 series claimed | UNKNOWN for any exact historical ID. | Census page states that from the April 2010 reports semiconductor estimates are no longer separately available and are included in computers/electronics and applicable aggregates: `https://www.census.gov/manufacturing/m3/historical/timeseries.html`, downloaded HTML line 719. | Semiconductor is UNSUPPORTED as a post-April-2010 M3 vintage subtheme. |

Definition/benchmark breaks:

- May 21, 2001: Census released revised January 1992–March 2001 data on NAICS basis, benchmarking shipments/inventories to the 1997 Economic Census and 1998–1999 ASM, and unfilled orders to the 1999 Unfilled Orders Survey; trading-day and seasonal factors were updated: downloaded `summary.pdf`, lines 1–24.
- The conversion used product allocation and, for products split across NAICS categories, arbitrary decisions usually equal to splits; inventory and unfilled-order allocations assumed shipment factors, with documented reliability limits: downloaded `summary.pdf`, lines 153–190.
- The 1997 product allocation was applied to 1992–2000 under an assumed stable company product mix; Census says confidence falls with distance from 1997: downloaded `summary.pdf`, lines 191–195.
- Current-month numbers are subject to revision; dollar amounts are in millions except two-decimal IS/US files: `https://www.census.gov/manufacturing/m3/historical/timeseries.html`, downloaded HTML line 719.
- Broad `INDPRO`, `DGORDER`, total manufacturing `AMTM*`, and aggregate capital-goods orders must not be relabeled as construction, metalworking, material-handling, turbine, farm, or other machinery subthemes.

## Q3 ISSUER-TO-DOMAIN MAPPING

VERDICT: PARTIALLY FOUND. The repository has prospective membership infrastructure and limited rename/correction receipts. It has NO observed table or module that can reconstruct historical industrial capital-goods/machinery membership before that source's first dated observation, and current membership/sector maps are forbidden to backdate.

| Candidate | Source / implementation | First date / cadence | Point-in-time status | Delisted/failed coverage | Rename / spin handling | Honest use |
|---|---|---|---|---|---|---|
| US curated baskets / PIT history | Mutable `membership.json` plus append-only dated snapshots and `membership_history.parquet`; contract implemented in `scripts/build_baskets.py` and `engine/basket_membership_pit.py`: `scripts/build_baskets.py:13@10166ad5272f`–`:26@10166ad5272f`; `engine/basket_membership_pit.py:16@10166ad5272f`–`:33@10166ad5272f`. | First snapshot only; source docs explicitly forbid pre-W1a reconstruction. | Prospective only. Before the first snapshot the reader falls back to current membership with `pit=False`: `engine/basket_membership_pit.py:73@10166ad5272f`–`:80@10166ad5272f`. | UNKNOWN: parquet omitted in sparse tree. | Rows carry document-supplied `added`/`removed`; same-date rewrites keep first: `engine/basket_membership_pit.py:126@10166ad5272f`–`:141@10166ad5272f`. | Forward-only basket permitted; backfill and historical cut forbidden without a new historical provider. |
| Finviz theme ladder | Declared 2026-06-27 seed plus dated `tree_history` observations: `engine/theme_graph/local_sources.py:1@10166ad5272f`–`:28@10166ad5272f`; `:132@10166ad5272f`–`:160@10166ad5272f`. | Seed 2026-06-27, then observed snapshots. | Prospective intervals only; `valid_from` means first observed and closes are interval-censored: `engine/theme_graph/local_sources.py:16@10166ad5272f`–`:18@10166ad5272f`; `:312@10166ad5272f`–`:340@10166ad5272f`. | UNKNOWN: `tree_history.jsonl` omitted. | Presence/absence forms observations; the code refuses mid-window invented closes. Symbol identity is separate. | Forward-only diagnostic; rights unresolved before new public emissions. |
| THS concept history | `ths_membership_intervals` admits only membership-shaped snapshots; concept-dump mapping is excluded because its concept-to-basket map is today's: `engine/theme_graph/local_sources.py:343@10166ad5272f`–`:358@10166ad5272f`. | Depends on stored snapshots; omitted in sparse tree. | Prospective for stored snapshots; no pre-store membership. | UNKNOWN. | Reappearance is a new observed interval; mapping itself is not backdated. | Not a US industrial-domain solution. |
| Data OS identity / issuer corrections | Master artifacts and correction receipts; master explicitly has no general lifecycle column and `models_lifecycle: false`: `config/identity_seams.yml:37@10166ad5272f`–`:53@10166ad5272f`; `:55@10166ad5272f`–`:64@10166ad5272f`; `:94@10166ad5272f`. | Current master plus append-only correction eras. | Current identity/corrections; issuer CIK evidence is a current-registrant observation with no historical issuer lineage: `config/identity_seams.yml:69@10166ad5272f`–`:79@10166ad5272f`. | Explicitly not modeled as general existence/delisting. | Security/issuer correction receipts and curated migrations govern duplicate mints and current keys; not general historical lineage. | Use only for current key stitching and audited corrections; do not infer a historical industry domain. |
| Ledger rename identity | Curated ticker-key continuation map for append-only ledgers: `engine/ledger_identity.py:1@10166ad5272f`–`:12@10166ad5272f`; `:54@10166ad5272f`–`:70@10166ad5272f`. | Ratified migration dates, example SATS→ECHO 2026-06-24: `engine/ledger_identity.py:13@10166ad5272f`–`:30@10166ad5272f`. | Event-dated for named continuations only. | No general failed/delisted universe. | Curation splits identity breaks and merges continuations; detector candidates never self-ratify: `engine/ledger_identity.py:67@10166ad5272f`–`:70@10166ad5272f`. | Useful targeted rename stitch after the mapping source exists; not a domain-classification source. |
| Institutional 13F census | SEC raw receipt and catalog clocks with report period, acceptance/retention, source cutoff and publication: `engine/institutional_census/models.py:251@10166ad5272f`–`:283@10166ad5272f`; `:288@10166ad5272f`–`:320@10166ad5272f`. | Period-dependent; store coverage omitted. | PIT for filing/catalog clocks, not issuer domain membership. | Coverage of failed/dead issuers not established here. | CIK/accession evidence does not supply historical segment history or spin lineage. | Not sufficient for issuer-to-industrial-domain mapping. |
| Stock-identity episodes | Price-derived episode catalog with start admission; existence explicitly not PIT-gated and not a tradeable universe: `engine/stock_identity/analog_pit.py:1@10166ad5272f`–`:14@10166ad5272f`; `:15@10166ad5272f`–`:24@10166ad5272f`. | Store omitted; code uses start/resolve clocks. | Research-navigation ceiling only; authority verbatim "research_navigation_until_promoted": `engine/stock_identity/analog_pit.py:26@10166ad5272f`. | Coverage not established. | Symbol-plane, no industry segment history. | Not an issuer-domain mapping. |
| Current sector map | Current GICS constituents and SIC/profile/EDGAR fallbacks: `scripts/build_sector_map.py:1@10166ad5272f`–`:20@10166ad5272f`; merge priority `:621@10166ad5272f`–`:637@10166ad5272f`. | Current daily build. | Current-only; no historical classification/vintage table. | Coverage target includes historical/delisted tickers, but the evidence basis is current: `scripts/build_sector_map.py:19@10166ad5272f`–`:21@10166ad5272f`. | Joins by current identifiers; no historical membership lineage. | FORBIDDEN as backdated historical membership; display/context firewall at `scripts/build_sector_map.py:28@10166ad5272f`–`:31@10166ad5272f`. |

Unreconstructable from observed repo sources: historical industrial capital-goods/machinery membership, predecessor/spin lineage, failed/delisted inclusion before an observed snapshot, and exact first-coverage counts. Closing this gap requires a licensed provider artifact with dated industry/segment history, dead-name coverage and explicit lineage rules. Backdating current GICS, sector, basket, or concept membership is forbidden by D03 and Q01.

## Q4 RIGHTS

VERDICT: PARTIALLY FOUND. Massive and the two FRED registry stores have explicit repo records. Selected FRED pages distinguish public-domain and copyrighted series. Census M3 and every historical issuer/segment provider family lack a complete five-way repo grant; they remain UNKNOWN wherever no explicit record exists.

Rights search receipt: `git grep -n -i -E 'license|licensing|rights|terms|redistribut|public domain|copyright|citation|entitlement' 10166ad5272f -- ':!data' ':!site' ':!mockups' ':!verify_shots'`, rc 0, 15,983 matching lines; targeted records below were then read directly.

| Family | Acquisition | Processing | Storage | Model use | User redistribution |
|---|---|---|---|---|---|
| FRED/ALFRED | Repo records keyless latest-revised observations and keyed ALFRED initial-release calls; stores are L1 vendor-API siblings. Latest store registry says `licensing: public_domain`: `config/dataset_registry.yml:183@10166ad5272f`–`:188@10166ad5272f`; vintage store row `:221@10166ad5272f`–`:225@10166ad5272f`. Keyed path: `collectors/fred.py:176@10166ad5272f`–`:203@10166ad5272f`. | Repo converts and stores observations/vintages; no special internal-processing restriction is recorded. | Approved latest and vintage stores are recorded at `data/fred/*.parquet` and `data/fred_vintage/vintages.parquet`: `config/dataset_registry.yml:171@10166ad5272f`; `:211@10166ad5272f`. | No blanket restriction is recorded for internal model features, but each series tag governs user-facing display/redistribution. Public-domain tags observed for `A33SNO` and `NEWORDER`; `CMRMTSPL` tagged copyrighted/citation-required by keyless FRED page read. | Public-domain pages request citation; exact redistribution terms beyond that tag are UNKNOWN. Do not assume every leg is public-domain. No user-facing redistribution decision may rest on the registry row alone. |
| Census M3 | Public page and downloadable historical documentation observed without a key; no acquisition contract or terms grant recorded in the repo. | Census documentation observed for definitions, revision and allocation/benchmark breaks. | No explicit retention rule found in targeted repo search. | No explicit model-use restriction or grant found. | UNKNOWN: no explicit redistribution grant/citation contract observed; public accessibility is not a license. |
| Issuer identity/segments | Curated house content is explicitly `direct_display_ok`/house: `config/theme_sources.yml:21@10166ad5272f`–`:27@10166ad5272f`. Finviz is keyless-public but unresolved/internal-only; THS is receipted-scrape and unresolved: `config/theme_sources.yml:29@10166ad5272f`–`:40@10166ad5272f`. Current GICS/SIC/EDGAR sources are described in `scripts/build_sector_map.py:1@10166ad5272f`–`:12@10166ad5272f` without historical-segment license terms. | Current maps and prospective snapshots may be processed internally where classified; new Finviz/THS GMI emissions refuse until rights resolve: `config/theme_sources.yml:4@10166ad5272f`–`:8@10166ad5272f`. | Current identity and dated membership artifacts are stored internally. | No blanket external-provider model-use right is recorded for historical segment/industry history. House content is the only explicit public display grant. | Finviz/THS new public emissions: forbidden while unresolved. Massive reference rights may or may not cover a specific historical segment product; the repo has no product-specific written designation, so UNKNOWN. |
| Massive `massive_stock_day` | Enterprise Market Data License and Redistribution Addendum effective 2026-08-09; collector records `us_stocks_sip/day_aggs_v1` and a rolling ~5-year entitlement probe to 2021-07-06: `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:8@10166ad5272f`–`:15@10166ad5272f`; `collectors/massive_stock_day.py:3@10166ad5272f`–`:6@10166ad5272f`. | Collector derives append-only per-ticker parquet and a manifest: `collectors/massive_stock_day.py:11@10166ad5272f`–`:15@10166ad5272f`. | R2 canonical, ~617 MB/~20k files, strict restore/publish chain: `collectors/massive_stock_day.py:17@10166ad5272f`–`:26@10166ad5272f`. | Record explicitly permits backtesting, factor research, screening, AI/ML, feature engineering and inference: `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:31@10166ad5272f`–`:39@10166ad5272f`. | Enterprise record permits raw/derived external redistribution, display, non-display, white-label, export, retention and no attribution, subject to per-dataset written vendor conditions: `:26@10166ad5272f`–`:48@10166ad5272f`; `:50@10166ad5272f`–`:57@10166ad5272f`. Vendor debranding remains required on public product surfaces. |

No credential, `.env`, key file, private executed contract text, or commercial term was read or copied.

## Q5 DATA-INDEPENDENT READINESS RULE + CANDIDATES

No return, trade outcome, strategy artifact or protected outcome file was opened or cited. The rule uses only source clocks, vintage depth, definition continuity, issuer mapping/coverage and rights.

**Readiness rule.** A proving domain may enter pilot only if all five pass:

1. **Vintage depth/clock:** at least two independent economic mechanisms have source legs with measured source-vintage history of at least 120 post-first-release months over the preregistered window. Admission uses source observation/publication clocks; a modeled lag may stress but never create an available date. Missing or late vintage rows block, not silently fall back.
2. **Mapping at cut:** issuer or segment membership at each decision cut is genuinely observed from a dated source, or the domain is declared macro-only. Current membership/sector/concept maps may never be backdated.
3. **Failure coverage:** the decision universe includes failed/delisted issuers at that cut, or the study is explicitly macro-only and reports survivorship as a limit.
4. **Definition tolerance:** every NAICS/benchmark/reclassification/seasonal-method/discontinuity is dated and handled by era split, declared diagnostic-only splice, or exclusion. Broad series may never be relabeled as granular subthemes.
5. **Rights:** acquisition, processing, storage, model use and user redistribution are each resolved; internal-only or unresolved sources support private diagnostics, never public pilots.

Applications:

**(a) Industrial capital goods / machinery — NOT PILOT-READY; prospective collection plus retrospective diagnostic only.**
- Passes mechanism breadth structurally: capital-goods orders and total-manufacturing backlog/shipments/inventory context are configured: `config.yml:127@10166ad5272f`; `:155@10166ad5272f`; `:450@10166ad5272f`–`:456@10166ad5272f`. Q2 now identifies granular machinery series, but they are not repo-configured and their API-contract depth is unmeasured.
- Fails rule 1: first usable vintages remain UNKNOWN for every configured leg (`data/fred_vintage/vintages.parquet` omitted); 120 months is unproved. The Q2 keyless single-ID history is a source-existence observation, not the repository's keyed output-type-4 store receipt.
- Fails rules 2–3: no historical machinery/capital-goods issuer mapping or failed-issuer coverage exists; only prospective snapshots are present.
- Conditionally passes rule 4 only after era treatment: Census SIC→NAICS and benchmark breaks are dated; machinery grain cannot be substituted by broad aggregate series.
- Fails rule 5 for user-facing use: FRED/Census rights are partially recorded; Census redistribution and historical-segment rights remain unresolved.

**(b) Alternative 1: semiconductor equipment — NOT PILOT-READY; macro-only prospective diagnostic.**
- Mechanism breadth is incomplete: repository has semiconductor and electronics capacity, semiconductor IP/capacity, and semiconductor-device PPI (`config.yml:440@10166ad5272f`–`:445@10166ad5272f`; `:456@10166ad5272f`), but not equipment-specific orders/shipments/backlog legs.
- Fails rule 1: detail capacity/PPI vintage coverage is explicitly plausible but unverified: `config.yml:143@10166ad5272f`–`:149@10166ad5272f`. M3 is unavailable as a post-April-2010 separate semiconductor estimate.
- Fails rules 2–3: only prospective theme snapshots are available; no historical equipment-maker membership or failure universe.
- Conditionally passes rule 4 by refusing the M3 semiconductor subtheme after its dated April 2010 discontinuity and refusing to relabel broad electronics/production/PPI as equipment.
- Rights are not pilot-sufficient: FRED public-domain tags are favorable for observed economic legs, but historical issuer mapping remains unresolved.

**(c) Alternative 2: building products / residential construction — NOT PILOT-READY; macro-only prospective diagnostic.**
- Mechanism breadth exists structurally at macro level: housing permits/starts, mortgage rate, Case-Shiller HPI and an XHB building-products monitor are configured: `config.yml:211@10166ad5272f`–`:214@10166ad5272f`; `:364@10166ad5272f`; `engine/cycle_proxies.py:299@10166ad5272f`–`:302@10166ad5272f`.
- Fails rule 1: PERMIT vintage depth is UNKNOWN; housing starts/HPI/mortgage legs are not configured in the vintage set: `config.yml:124@10166ad5272f`–`:157@10166ad5272f`.
- Fails rules 2–3: no historical building-products issuer mapping, failed-name inclusion, or sector membership cut is observed; XHB is a current monitor, not a historical membership source.
- Fails rule 4: benchmark/rebaseline treatment for HPI/starts/mortgage/building-product legs is not assembled.
- Rights are not pilot-sufficient: FRED metadata is favorable for observed economic legs, but issuer mapping and ETF-derived public redistribution conditions are unresolved in this record.

**No alternative is selected.** Q07 permits either one admissible domain or a documented alternative chosen by the same rule; both fail the same mapping and measured-depth gates before return inspection.

## Q6 GAPS + MUST-NOTS

UNKNOWNs and exact closure evidence:

1. **Configured-leg vintage depth.** Every Q1 first usable vintage remains UNKNOWN because the approved parquet is omitted in this sparse worktree. After a lawful keyed production collection, run `python3 -m scripts.audit_alfred_depth --series AWHMAN,PERMIT,NEWORDER,CMRMTSPL,INDPRO,ISRATIO,MNFCTRIRSA,AMTMUO,AMTMVS,CAPUTLG3344S,CAPUTLG334S,CAPUTLG331S,PCU334413334413,PCU331110331110,IPG2211S,CAPUTLG2211S,WPU0543 --output data/fred_vintage/alfred_depth_d03_cycle.json`; require `earliest_vintage`, `n_periods`, and a verdict per leg. Do not write or restore `data/` in this census.
2. **Keyless-to-keyed vintage equivalence.** Q2 proves public single-ID FRED/ALFRED history exists, but not that the default CSV equals the repo collector's keyed output-type-4 initial-release contract. Closure needs a keyed audit receipt exposing `realtime_start` and the first-published value per period for each candidate.
3. **Remaining M3 exact crosswalks.** Exact FRED status remains unknown for `A33XMVS`/`A33XMUO`/`A33XMTI` counterparts, farm-machinery `A33ANO`/`A33AUO`, and all turbine `A33J*` measures. Needed artifact is the authoritative Census-to-FRED series crosswalk and, where Census-only, the historical file contract and vintage clock.
4. **Historical issuer mapping.** Required artifact is a licensed dated industry/segment history with event/snapshot clocks, dead-name/failed coverage, and explicit rename/spin predecessor lineage. No current GICS/SIC/basket/concept map may be backdated.
5. **Membership first dates and coverage.** `data/baskets/membership_history.parquet`, `data/themes_heatmap/tree_history.jsonl`, and THS history are omitted. A full-checkout read-only audit must report each suite's first date, membership rows, dead names, and identity coverage.
6. **Census rights.** A Census terms/open-data record or written source-owner ruling must answer acquisition, processing, storage, model use and user redistribution separately. Public file accessibility is not a grant.
7. **Issuer/segment provider rights.** Required artifact is a provider entitlement record separating all five rights dimensions and specifying historical-cut access, derivative display and failed-name coverage. No assumed Massive coverage.
8. **Massive dead-name coverage.** Restore the R2 canonical store in a full/production runner, then audit manifest and per-ticker coverage against the licensed historical issuer universe. The sparse tree was deliberately not restored.
9. **ALFRED ingestion availability.** Per-series exact first eligibility can come only from measured `realtime_start` receipts; documentation and modeled lags cannot mint dates.

Forbidden shortcuts considered and refused:

- Did not infer series absence from the failed multi-ID pipe request; the exact-ID probes replaced that invalid conclusion.
- Did not backdate current membership, sector, index, curated-basket, or concept mappings.
- Did not relabel `INDPRO`, durable goods, total manufacturing, or aggregate capital-goods series as granular machinery themes.
- Did not convert `PUB_LAG_M`, CSV first observation dates, or prose release schedules into first-vintage dates.
- Did not read, use, print or copy credentials or keys; no keyed FRED/ALFRED call was made.
- Did not open, compute or cite strategy returns, trade outcomes, or protected outcome artifacts.
- Did not invent unavailable membership, failures, licenses, vintage dates, or production schedules.
- Did not opt into sparse trees, restore `data/`, run the full test suite, force-push, rebase, or rewrite history.

## EVIDENCE INDEX

**Object/source citations.** All 44 unique `path:line@10166ad5272f` references in Q1–Q6 are part of this index; they were read from immutable object `10166ad5272f`, which was `origin/main` when the census base was observed. The same fact may be cited at the first line of a code span whose later line appears elsewhere (for example, a table row ending `:456@10166ad5272f` is indexed together with `config.yml:440@10166ad5272f`).

**Public-primary and sparse receipts.**

```text
git rev-parse HEAD
10166ad5272f8ca24161aed5bdd8d3980271489e
git rev-parse origin/main
10166ad5272f8ca24161aed5bdd8d3980271489e
rc=0

python3 scripts/worktree_sparse.py status
worktree-sparse: SPARSE checkout — omitting data, mockups, site, verify_shots
worktree-sparse: sparse worktree — data, mockups, site, verify_shots not checked out; opt into a full checkout with: python3 scripts/worktree_sparse.py full
rc=0

git grep -nE 'ACOGNO|A34SNO|AMTMNO|AMTMUO|NEWORDER|IPMAN|IPBUSEQ' 10166ad5272f -- ':!data' ':!site' ':!mockups' ':!verify_shots'
43 matches in config, engine, reports, research and tests; no ACOGNO, A34SNO, AMTMNO, IPMAN, or IPBUSEQ match
rc=0

curl -L -sS -o /dev/null -w '%{http_code}' 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=A33SNO'
200
rc=0
curl -L -sS -o /dev/null -w '%{http_code}' 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=A33SVS'
200
rc=0
curl -L -sS -o /dev/null -w '%{http_code}' 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=A33SUO'
200
rc=0
curl -L -sS -o /dev/null -w '%{http_code}' 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=A33STI'
200
rc=0

for id in A33SNO A33SVS A33SUO A33STI; do curl -fsSL "https://fred.stlouisfed.org/graph/fredgraph.csv?id=${id}" > "${id}_fred.csv"; curl -fsSL "https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=${id}" > "${id}_alfred.csv"; done
A33SNO FRED_ROWS=415 ALFRED_ROWS=415 FRED_FIRST=1992-02-01,14202 FRED_LAST=2026-07-01,44641 ALFRED_FIRST_VINTAGE=1992-02-01
A33SVS FRED_ROWS=416 ALFRED_ROWS=416 FRED_FIRST=1992-01-01,14623 FRED_LAST=2026-07-01,43778 ALFRED_FIRST_VINTAGE=1992-01-01
A33SUO FRED_ROWS=416 ALFRED_ROWS=416 FRED_FIRST=1992-01-01,40073 FRED_LAST=2026-07-01,152221 ALFRED_FIRST_VINTAGE=1992-01-01
A33STI FRED_ROWS=416 ALFRED_ROWS=416 FRED_FIRST=1992-01-01,36225 FRED_LAST=2026-07-01,105561 ALFRED_FIRST_VINTAGE=1992-01-01
rc=0

for id in A33XMVS A33XMUO A33XMTI A33SNO A33SVS A33SUO A33STI A34SNO A34SVS A34SUO A34STI A33AMNO A33CMNO A33DMNO A33EMNO A33IMNO A33JMNO A33MMNO; do status=$(curl ... "$id"); done
A33XMVS HTTP_404; A33XMUO HTTP_404; A33XMTI HTTP_404; A33S* HTTP_200; A34S* HTTP_200; A33AMNO HTTP_404; A33CMNO HTTP_200; A33DMNO HTTP_200; A33EMNO HTTP_200; A33IMNO HTTP_200; A33JMNO HTTP_404; A33MMNO HTTP_200
rc=0

for code in A C D E I J M; do for suffix in NO VS UO TI; do id="A33${code}${suffix}"; status=$(curl ... "$id"); done; done
A33AVS HTTP_200; A33ATI HTTP_200; A33ANO HTTP_404; A33AUO HTTP_404; A33C*–A33I* and A33M* all HTTP_200; A33J* all HTTP_404
rc=0

curl -fsSL 'https://www.census.gov/manufacturing/m3/historical/timeseries.html' > m3_timeseries.html
BYTES=77451
rc=0
visible-text/html line 719: from the April 2010 Reports, semiconductor estimates are no longer available separately; current-month numbers are subject to revision

curl -fsSL 'https://www.census.gov/manufacturing/m3/historical_data/aggseries.pdf' > m3_aggseries.pdf; pdftotext -layout m3_aggseries.pdf -
BYTES=29160; LINES=299; rc=0
line 99: 33S Machinery; line 172: 33C Construction; line 173: 33D Mining/oil/gas; line 174: 33E Industrial; line 179: 33I Metalworking; line 183: 33M Material handling; line 232: 33A Farm; lines 260 and 297–298: NXA and TGP/33J

curl -fsSL 'https://www.census.gov/manufacturing/m3/historical_data/summary.pdf' > m3_summary.pdf; pdftotext -layout m3_summary.pdf -
BYTES=22166; LINES=196; rc=0
lines 1–24: May 21, 2001 NAICS release, 1997 Economic Census/1998–1999 ASM/1999 Unfilled Orders benchmarks, seasonal/trading-day updates; lines 153–190 arbitrary product splits and inventory/unfilled shipment-factor assumptions; lines 191–195 product-mix assumption

curl -fsSL 'https://fred.stlouisfed.org/docs/api/fred/realtime_period.html'
rc=0
visible text: real-time period marks when a fact was true/known; defaults to today; realtime_start and realtime_end form a closed interval
```

**Git and validation receipts at this record head.**

```text
git diff --check
rc=0

wc -l research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md
271 research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md

grep -v 'TODO_COUNT' research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md | grep -c 'TODO' || true
0
rc=0

git diff --stat origin/main...HEAD
research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md | 271 +++++++++++++++++++++
1 file changed, 271 insertions(+)
```
