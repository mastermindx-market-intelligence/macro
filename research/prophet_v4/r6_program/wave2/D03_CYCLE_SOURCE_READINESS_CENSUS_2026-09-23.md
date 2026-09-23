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

VERDICT: PARTIALLY FOUND. Repo records answer most Massive dimensions and classify FRED IDs; Census and the historical issuer/segment provider require explicit authorization before any storage/model/redistribution commitment. No credential, `.env`, or key file was read.

| Family | Acquisition | Processing | Storage | Model use | User redistribution |
|---|---|---|---|---|---|
| FRED/ALFRED | FRED records core macro observations as `public_domain`, but `CMRMTSPL` as `copyrighted: citation required`; M3 pages report `public domain: citation requested`. Current observations have a keyless CSV fallback; vintage reads require a keyed ALFRED API call. | Repo transforms observations/vintages into parquet, computes growth and cycle inputs. No special restriction is recorded for internal processing. | Repo already records production stores for FRED observations and ALFRED vintages. | No explicit restriction is recorded for these internal model features, but each series license field must govern the final user-facing presentation and redistribution. | `public_domain` legs permit redistribution with the recorded citation convention; `CMRMTSPL` is citation-required but its full redistribution terms are otherwise UNKNOWN. A blanket public-domain claim for every leg is forbidden. |
| Census M3 | The page provides historical documentation/files; no acquisition contract or key requirement is recorded in the repo. | Census documentation defines adjustment, code, and revision conventions. | No explicit Census M3 retention policy is recorded. | No explicit Census M3 model-use restriction is recorded. | Census page rights were not read as an explicit redistribution grant. UNKNOWN; do not assume public redistribution. |
| Issuer identity/segments | The current identity spine uses provider constituents/profiles/EDGAR CIK evidence; a historical segment provider is not identified. The GMI Finviz family is a keyless public scrape and explicitly unresolved. THS is a receipted scrape, also unresolved for new public emissions. Massive reference rights are broad in its own record, but no specific historical segment history table is recorded here. | Current maps and membership snapshots are processed internally. | Current identity artifacts and PIT membership snapshots are stored. Finviz derivatives stay on an internal plane pending rights resolution. | No blanket external-provider model-use right is recorded for historical segments; internal research can proceed only under current internal-only/unresolved classifications. | House content is direct display OK; Finviz/THS new public emissions refuse; Massive reference may support redistribution only if the specific historical segment product is within the enterprise scope and any dataset condition. |
| Massive `massive_stock_day` | The collector records the `us_stocks_sip/day_aggs_v1` flat-file entitlement and a rolling five-year window probe. R2 is canonical and nightly restore/update/publish is recorded. | Collector derives per-ticker append-only parquet files and stamps manifest freshness. | Whole-store R2-private design, ~617 MB/~20k files, local mirror freshness gates. | License record explicitly allows backtesting, factor research, screening, AI/ML, feature engineering, and inference. | Enterprise license and redistribution addendum record allows raw/derived external redistribution, display, non-display, white-label, end-user export, retention, and no required attribution; dataset-specific written conditions remain authoritative. The vendor is not named on public product surfaces. |

## Q5 DATA-INDEPENDENT READINESS RULE + CANDIDATES

No return, trade outcome, strategy artifact, or protected outcome file was opened or cited. The rule depends only on source clocks, vintage depth, definition continuity, mapping coverage, rights, and failure coverage.

**Rule.** A proving domain may be a pilot only if all seven pass:

1. At least two independent economic mechanisms have configured source legs (for example orders/backlog, shipments/inventory, production/utilization, segment or issuer sales/order drivers).
2. Every mechanism-critical leg has measured ALFRED/source vintage depth covering the preregistered episode window; for monthly legs require a minimum of 120 observed post-first-release months unless the source itself is older by audited receipt.
3. The release clock is explicit and conservative: first-observation/publication date, not a modeled lag, bounds every backtest admission; late or absent vintage rows must block that row, not silently fall back.
4. Issuer or segment mapping at the decision cut is either genuinely observed or the domain is macro-only. Current membership, current sector, or current concept maps may never be backdated. Failed/delisted issuer coverage is measured or declared as an explicit limitation.
5. Every definition break (NAICS/benchmark/reclassification/seasonal methodology/discontinuity) is dated and handled by era split, splice factor declared as diagnostic-only, or exclusion. No undated relabeling.
6. Rights are resolved separately for acquisition, processing, storage, model use, and user redistribution before a user-facing pilot. Internal-only sources may support private research, never public display.
7. There is a named negative control and falsifier, and the minimum admitted issuer/segment population is stated before outcomes are inspected.

Applications:

**(a) Industrial capital goods/machinery — CONDITIONAL / NOT READY.**
- Mechanisms: NEWORDER provides orders; AMTMUO/AMTMVS and ISRATIO/MNFCTRIRSA provide backlog, shipment and inventory context. This passes the breadth condition structurally.
- Fails depth/clock: first usable vintages and minimum months are UNKNOWN for every configured vintage leg.
- Fails issuer mapping: no historical industrial capital-goods/machinery membership or failed-issuer history is observable here.
- Definition tolerance: broad aggregate breaks are documented, but machinery subsector continuity is unresolved; semiconductor M3 support has a dated 2010 break.
- Rights: partial. Economic legs are mostly public-domain, but `CMRMTSPL` is citation-required; Census redistribution and historical segment rights are unresolved.
- Verdict: admit only as macro-only retrospective diagnostic/prospective collection until keyed depth, machinery lineage, and rights close.

**(b) Alternative 1: semiconductor equipment — PROSPECTIVE / NOT READY.**
- Mechanisms: repo configures semiconductor capacity utilization and semiconductor-device PPI plus broader electronic capacity; equipment orders/shipments are not configured.
- Fails depth: detail capacity/PPI vintage coverage is explicitly called plausible but unverified.
- Fails issuer mapping: historical membership is not present; only prospective theme snapshots exist.
- Definition tolerance: M3 semiconductor publication break at April 2010 is documented, but the economic legs are FRED G.17/PPI and need their own vintage continuity check.
- Rights: public-domain FRED metadata is favorable for those IDs; no rights blocker beyond redistribution presentation.
- Verdict: prospective-only diagnostic until measured vintage depth and a dated membership/issuer cut exist.

**(c) Alternative 2: building products / residential construction — PROSPECTIVE / NOT READY.**
- Mechanisms: permits are configured and housing-cycle monitors include a case-shiller-style index, permits/starts, mortgage rate, and a building-products ETF proxy; this gives macro mechanisms but no issuer segment mapping in the observed evidence.
- Fails depth: PERMIT is modeled and configured, but first vintage and depth are UNKNOWN; the other housing monitor legs are not vintage-configured here.
- Fails issuer mapping: no historical building-products membership or failed-issuer coverage observed.
- Definition tolerance: source-level benchmark/rebaseline treatment is not yet assembled for the alternative legs.
- Rights: FRED leg metadata is favorable; proxy/ETF rights inherit the price plane, and issuer display needs a resolved historical segment source.
- Verdict: prospective-only until all leg depths and issuer mapping pass the same rule.

## Q6 GAPS + MUST-NOTS

TODO

## EVIDENCE INDEX

TODO
