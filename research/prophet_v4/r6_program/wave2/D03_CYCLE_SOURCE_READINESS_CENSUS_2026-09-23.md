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

VERDICT: PARTIALLY FOUND. The exact Census/FRED aggregate capital-goods IDs are FOUND; machinery subsector mappings are FOUND in Census historical documentation. Direct FRED IDs for machinery subsector orders/shipments/unfilled/inventories were NOT FOUND by the tested candidate spellings, and their existence status remains UNKNOWN rather than proven absent.

| Claim | Candidate series | FRED status | Census vintage status | Claim support |
|---|---|---|---|---|
| Nondefense capital goods ex-aircraft new orders | `NEWORDER` = `A33XMNO` | FOUND: FRED series exists; SA, millions of dollars. | Configured as ALFRED initial-release leg; depth unknown. | Granular capital-goods aggregate is supported, subject to depth. |
| Same category shipments | probable FRED `A33XMVS` | UNKNOWN: not repo-configured and not tested through a vintage call. | Census code `NXA` + `VS` exists in the 6-digit M3 code law. | Census-only history likely; not usable as a vintage series on repo evidence alone. |
| Same category unfilled orders | probable FRED `A33XMUO` | UNKNOWN. | Census code `NXA` + `UO` exists in the code law. | Census-only history likely; not usable as a vintage series on repo evidence alone. |
| Same category inventories | probable FRED `A33XMTI` | UNKNOWN. | Census code `NXA` + `TI` exists in the code law. | Census-only history likely; not usable as a vintage series on repo evidence alone. |
| Machinery subsector total (`33S`) orders/shipments/unfilled/inventories | Census `A33SNO`, `A33SVS`, `A33SUO`, `A33STI` | UNKNOWN: the four exact IDs returned FRED HTTP 404, which may reflect an undocumented ID transformation. | Census historical-code law directly names `33S` machinery and all item suffixes. | Census history is supported; FRED/ALFRED status is unresolved. |
| Machinery subindustries | Census `33A`, `33C`, `33D`, `33E`, `33I`, turbine/power transmission, `33M`; several later categories not published | UNKNOWN at FRED. | Census documentation names/publishes the listed categories and explicitly says others are included but not published. | Per-machine-type economic claims must not be built on a broad machinery series; exact Census-only series would be needed. |
| Semiconductor subtheme via M3 | Semiconductor industry removed as a separately published M3 estimate in the April 2010 report | UNKNOWN at FRED. | FOUND: Census page documents the April 2010 break. | Semiconductor subtheme is UNSUPPORTED by any M3 vintage series after that break; use semiconductor-specific FRED capacity/PPI legs only for their own themes, not machinery membership. |

Documented M3 definition/benchmark changes:

- SIC→NAICS conversion: revised monthly data for January 1992–March 2001 were released on May 21, 2001; shipments/inventories were benchmarked to the 1997 Economic Census and 1998–1999 ASM, unfilled orders to the 1999 survey, with seasonal/trading-day factors updated. Treat pre-/post-1992 and SIC/NAICS categories as separate definitions.
- The SIC→NAICS allocation used product-based factors and, in places, arbitrary equal splits across multiple NAICS codes; inventory factors were assumed to follow shipment factors. These are documented, material composition breaks for subsector claims.
- The Census page says current-month numbers are revised and gives semiconductor-specific publication break in April 2010; it does not state a vintage-by-vintage download contract on the page read.
- Broad series must not be relabeled granular: `INDPRO`, `DGORDER`, total manufacturing `AMTM*`, and capital-goods aggregates do not prove claims about construction machinery, machine tools, material-handling equipment, turbines, or farm machinery.

## Q3 ISSUER-TO-DOMAIN MAPPING

VERDICT: PARTIALLY FOUND. Prospective, dated membership infrastructure exists; no table/module observed here can reconstruct historical industrial capital-goods/machinery membership before its own first snapshot. Current sector maps are explicitly not usable for a historical cut.

| Candidate | Source | First date / cadence | Point-in-time status | Delisted/failed coverage | Rename/spin handling | Honest use |
|---|---|---|---|---|---|---|
| US curated baskets / membership history | `data/baskets/membership.json`, plus append-only `data/baskets/membership_history.parquet` and dated JSON snapshots. | Store birth begins at the first W1a snapshot; no pre-W1a history reconstructed. Nightly. | Prospective PIT only. Reader falls back to current membership with `pit=False` before first snapshot. | UNKNOWN in sparse tree; store coverage not readable here. | Rows carry the document's own `added`/`removed` dates; snapshot keep-first handles edits. Identity migration is separate. | Build a forward-only machinery/capital-goods basket, but do not backfill membership. |
| Finviz theme ladder | Declared seed `finviz_themes/finviz_themes_map.json` asof 2026-06-27 plus `data/themes_heatmap/tree_history.jsonl`. | Seed 2026-06-27; subsequent observed snapshots. | Prospective observed intervals only. Membership opens at first observation and closes at first absence; close dates are interval-censored. | UNKNOWN in sparse tree; no coverage measured. | Snapshot presence/absence controls membership; symbol identity separately. | Same forward-only rule; source is unresolved for new public GMI emissions. |
| THS concept history | Canonical owner history passed into `ths_membership_intervals`. | Depends on stored snapshots; not readable in sparse tree. | Prospective observed snapshots; raw concept dumps may carry PIT members but today's basket mapping, so are excluded by default. | UNKNOWN. | Concept-to-basket mapping is deliberately not backdated. | Not a US industrial-domain solution. |
| Data OS identity master | SEC/security/issuer master and migration receipts built from current symbol joins plus append-only correction receipts. | On-demand; effective/ingested clocks in rows. | Current identity/corrections, not general historical industry/segment membership. | Master answers existence only via a correction enum; a general lifecycle/delisting model is explicitly absent. | Current CIK evidence, explicit issuer migrations, superseded security corrections; no historical lineage. | Use for current key stitching, never as historical industry membership. |
| Institutional 13F census | SEC raw receipts and catalog generations with report period, acceptance, retention, source cutoff, and publication clocks. | Period-dependent; not measured in sparse tree. | Prospect/receipt PIT for ownership filings, not issuer domain classification. | Holdings and filings are source-bounded; failed issuer coverage not established here. | Underlying accession/CIK evidence supports receipts, but no historical industry mapping was observed. | Not sufficient for issuer-to-domain. |
| Stock-identity episodes | Price-derived technical episode catalog plus PIT admission gate. | Artifacts omitted; code has research-navigation authority. | Not PIT-gated for episode existence; outcomes masked when knowable. Explicitly not a tradeable universe and not decision-grade. | Claims survivorship contamination concern only pre-2021/non-massive cohorts; coverage absent in sparse tree. | Symbol-plane identity; no industry segment mapping. | Not an issuer domain mapping. |
| Current sector map | `data/breadth/ticker_sectors.parquet` from current GICS constituents, profile SIC text, and EDGAR CIK/SIC. | Current build, one row per ticker. | Current-only. | Target coverage includes historical/delisted names, but the evidence basis is current and no vintage column was observed. | Same current identity joins. | FORBIDDEN to backdate. |

Gap that cannot be reconstructed from this repo: historical industrial capital-goods/machinery membership, spin-off predecessor membership, and failed/delisted issuer inclusion before a genuine observed source snapshot. Acquiring the historical industry/segment cut requires a provider with dated classification history and rights; current membership must not be projected backward.

## Q4 RIGHTS

TODO

## Q5 DATA-INDEPENDENT READINESS RULE + CANDIDATES

TODO

## Q6 GAPS + MUST-NOTS

TODO

## EVIDENCE INDEX

TODO
