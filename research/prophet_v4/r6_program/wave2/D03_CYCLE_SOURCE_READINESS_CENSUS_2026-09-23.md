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

TODO

## Q5 DATA-INDEPENDENT READINESS RULE + CANDIDATES

TODO

## Q6 GAPS + MUST-NOTS

TODO

## EVIDENCE INDEX

TODO
