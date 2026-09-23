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

TODO

## Q3 ISSUER-TO-DOMAIN MAPPING

TODO

## Q4 RIGHTS

TODO

## Q5 DATA-INDEPENDENT READINESS RULE + CANDIDATES

TODO

## Q6 GAPS + MUST-NOTS

TODO

## EVIDENCE INDEX

TODO
