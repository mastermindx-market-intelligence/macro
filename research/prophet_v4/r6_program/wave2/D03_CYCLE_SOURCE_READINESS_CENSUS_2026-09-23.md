# D03 Cycle source-readiness census — R6 wave 2

## SOURCE_SHA

- `5f02cd6c95ab3aa26f6ec61cffc775fb85b14af2` — detached main HEAD before the skeleton commit.
- OBSERVED: `git rev-parse HEAD~1` was expected to equal `git rev-parse origin/main`; instead it returned `1e28f99cd110a9cfd6078baaecc7c4bae4a97a8c` versus `f517796c69904fb2b891e40bad6cc5e89fc47bc9`. Therefore SOURCE_SHA remains the recorded detached HEAD, and equality is UNKNOWN pending no-op verification.

## ANCHORS READ

TODO

## Q1 VINTAGE LEG INVENTORY

VERDICT: PARTIALLY FOUND. The configured legs, units, adjustment, modeled lag, and store revision semantics are OBSERVED. The first usable vintage date for every leg is UNKNOWN in this sparse worktree because the authoritative local vintage store is omitted and no committed depth report covers the required set.

| Leg | FRED ID | Unit/adjustment | Modeled publication lag | Revision behavior in code | First usable vintage | Exact class | Deciding fact |
|---|---|---:|---:|---|---|---|---|
| AWHMAN | AWHMAN | Manufacturing production and nonsupervisory hours; seasonally adjusted. | 1 month. | Latest-revised fallback in `business_cycle`; initial release only if present in the local vintage map/store. | UNKNOWN | prospective-only | Configured for collection, but not in the business-cycle vintage lookup map. |
| PERMIT | PERMIT | New private housing permits; thousands of units, SAAR. | 1 month. | Latest-revised fallback; no business-cycle vintage lookup. | UNKNOWN | prospective-only | Configured for ALFRED collection, but the business-cycle code does not select it. |
| NEWORDER | NEWORDER | New orders, nondefense capital goods excluding aircraft; millions of dollars, SA. | 1 month. | Latest-revised fallback; no business-cycle vintage lookup. | UNKNOWN | prospective-only | Configured and central to capital goods, but absent from the code-level vintage lookup. |
| CMRMTSPL | CMRMTSPL | Real manufacturing and trade sales; millions of chained 2017 dollars, SA. | 2 months. | Latest-revised fallback; no business-cycle vintage lookup. | UNKNOWN | prospective-only | Configured for collection, but not in the business-cycle vintage lookup. |
| INDPRO | INDPRO | Total industrial production index, 2017=100, SA. | 1 month. | `use_vintage=True` selects the first-published value from ALFRED output type 4; otherwise latest-revised. | UNKNOWN | observed-as-run | This leg is actually mapped into the business-cycle vintage lookup. |
| ISRATIO | ISRATIO | Total business inventories/sales ratio, SA. | 2 months. | Latest-revised fallback; no business-cycle vintage lookup. | UNKNOWN | prospective-only | Configured for collection, but absent from the business-cycle vintage lookup. |
| ICSA | ICSA | Initial claims, persons, seasonally adjusted weekly level. | 0 in the monthly table. | `use_vintage=True` selects initial release when present. | UNKNOWN | observed-as-run | Code-mapped vintage leg. |
| PAYEMS | PAYEMS | Total nonfarm payrolls, thousands, SA. | 1 month. | `use_vintage=True` selects initial release when present. | UNKNOWN | observed-as-run | Code-mapped vintage leg. |
| UMCSENT | UMCSENT | Consumer sentiment index, 1966=100. | 1 month. | `use_vintage=True` selects initial release when present. | UNKNOWN | observed-as-run | Code-mapped vintage leg. |
| MNFCTRIRSA | MNFCTRIRSA | Manufacturers inventories/sales ratio, SA. | Not modeled in `business_cycle`. | Initial-release ALFRED store if keyed collection succeeds; otherwise no leg. | UNKNOWN | prospective-only | Newly configured for vintage collection without a measured depth receipt. |
| AMTMUO | AMTMUO | Manufacturers unfilled orders, total manufacturing; millions of dollars, SA. | Not modeled in `business_cycle`. | Initial-release ALFRED store if keyed collection succeeds. | UNKNOWN | prospective-only | Configured vintage candidate with no committed usable-date audit. |
| AMTMVS | AMTMVS | Manufacturers value of shipments, total manufacturing; millions of dollars, SA. | Not modeled in `business_cycle`. | Initial-release ALFRED store if keyed collection succeeds. | UNKNOWN | prospective-only | Configured vintage candidate with no committed usable-date audit. |
| CAPUTLG3344S | CAPUTLG3344S | Semiconductor and electronic-component capacity utilization, percent, SA. | Not modeled in `business_cycle`. | Initial-release ALFRED store if keyed collection succeeds; empty otherwise. | UNKNOWN | prospective-only | Config says detail-vintage coverage is plausible but unverified. |
| CAPUTLG334S | CAPUTLG334S | Computer/electronic-products capacity utilization, percent, SA. | Not modeled in `business_cycle`. | Same keyed ALFRED path. | UNKNOWN | prospective-only | Same unverified-detail-series limitation. |
| CAPUTLG331S | CAPUTLG331S | Primary-metal capacity utilization, percent, SA. | Not modeled in `business_cycle`. | Same keyed ALFRED path. | UNKNOWN | prospective-only | Same unverified-detail-series limitation. |
| PCU334413334413 | PCU334413334413 | Semiconductor and related device manufacturing PPI, index. | Not modeled in `business_cycle`. | Same keyed ALFRED path. | UNKNOWN | prospective-only | Configured for vintage collection, depth not measured. |
| PCU331110331110 | PCU331110331110 | Iron and steel mills/ferroalloy PPI, index. | Not modeled in `business_cycle`. | Same keyed ALFRED path. | UNKNOWN | prospective-only | Configured for vintage collection, depth not measured. |
| IPG2211S | IPG2211S | Electric-power generation industrial production, 2017=100, SA. | Not modeled in `business_cycle`. | Same keyed ALFRED path. | UNKNOWN | prospective-only | Configured for vintage collection, depth not measured. |
| CAPUTLG2211S | CAPUTLG2211S | Electric-power generation capacity utilization, percent, SA. | Not modeled in `business_cycle`. | Same keyed ALFRED path. | UNKNOWN | prospective-only | Configured for vintage collection, depth not measured. |
| WPU0543 | WPU0543 | Industrial electric power PPI, index. | Not modeled in `business_cycle`. | Same keyed ALFRED path. | UNKNOWN | prospective-only | Configured for vintage collection, depth not measured. |

Additional capital-goods/machinery symbols found in the repo: `ACOGNO`, `A34SNO`, `AMTMNO`, `AMTMUO`, `AMTMVS`, `NEWORDER`, `DGORDER`. `AMTMUO` and `AMTMVS` are configured for initial-release collection; the others are latest-revision FRED legs, not granular machinery vintage series. No `IPMAN` or `IPBUSEQ` occurrence was found outside tests/prose in the non-sparse search. The exact measurement command is:

`python3 -m scripts.audit_alfred_depth --output data/fred_vintage/alfred_depth_d03_cycle.json`

After a keyed `collectors.fred.fetch_vintages()` run, the audit must cover all legs above and report `min(realtime_start)` per series. Do not infer that date from the release-lag table.

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
