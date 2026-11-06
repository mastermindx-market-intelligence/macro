# D03 Source Readiness Matrix — 2026-09-23
STATUS: COMPLETE

## 1. SOURCE_SHA + PATHS READ

- SOURCE_SHA: `b47cab58e79ab825e07f640c4a37826095eecc78` (`git rev-parse origin/main`).
- Governing fallback records were read by exact `git show` from PR refs, not from `origin/main`: ruling `d3b1fb743cbcde38a23ff13def1db47e42335514`, cycle census `68ece597765bb8d842a16434be9c8fc67200ee53`, issuer census `6c0539e253fbab4a8caee8fe02a0732d2f3fb341`. The ruling and issuer census are still absent from `origin/main`; the cycle census subsequently landed at `b61a3f1930` and the same PR-head object remains the governing version read here. §9 records the three exact fallback commands.
- Paths read with `git show origin/main:<path>`:
  1. `data/fred_vintage/vintages.parquet`
  2. `data/fred_vintage/alfred_depth_audit.json`
  3. `data/baskets/membership_history.parquet`
  4. `data/themes_heatmap/tree_history.jsonl`
  5. `data/reference/security_master.parquet`
  6. `data/reference/vendor_aliases.parquet`
  7. `data/reference/_receipt.json` (`git ls-tree origin/main data/reference/` listed `_receipt.json`, issuer/security master and migrations, security master, vendor aliases)
  8. `config/delisted_symbols.yml`
  9. `config.yml`
  10. `config/dataset_registry.yml`
  11. `config/theme_sources.yml`
  12. `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`
  13. `research/licenses/THETADATA_ENTITLEMENT_RECORD.md`
  14. `scripts/audit_alfred_depth.py`
  15. `collectors/fred.py`
  16. `collectors/base.py`
  17. `lib/config.py`
  18. `lib/store.py`
  19. `data/basket_levels/china_ths.parquet` (the first history path found by the required THS locator)
- Listing-only commands were used for allowlisted discovery: `git ls-tree --name-only origin/main data/reference/`, `git ls-tree -r --name-only origin/main data | grep -iE 'ths' | head`, and `git ls-tree -r --name-only origin/main research/licenses/`. The five support paths immediately above are not source inputs; §9 records that unchanged audit dependencies were copied to scratch solely to reproduce the mandated cross-check. No listed detail was opened outside the paths above. No forbidden path was read.

## 2. VINTAGE DEPTH PER SERIES

The cycle census Q6-1 list contains all 17 series below. `post-first-release months` is the calendar-month span from each series' first observation period through its latest observation period, not merely the row count. `gaps` lists missing calendar months in that span. Release lag runs from month end to `realtime_start` and is reported min/median/max in days.

| Series | First realtime | Latest realtime | n_vintages | n_periods | Post-first-release months | Missing vintage months | Lag min/med/max days | 120-month mark |
|---|---:|---:|---:|---:|---:|---|---:|---|
| AWHMAN | 1997-01-10 | 2026-09-04 | 356 | 357 | 357 | none | 1/5/51 | ≥120 |
| PERMIT | 1999-09-17 | 2026-09-17 | 321 | 325 | 325 | none | 16/18/101 | ≥120 |
| NEWORDER | 1997-03-26 | 2026-08-26 | 354 | 354 | 354 | none | 21/26/57 | ≥120 |
| CMRMTSPL | 2013-06-24 | 2026-08-26 | 155 | 160 | 160 | none | 50/60/114 | ≥120 |
| INDPRO | 1997-01-17 | 2026-09-18 | 356 | 357 | 357 | none | 14/16/64 | ≥120 |
| ISRATIO | 1997-04-15 | 2026-09-16 | 354 | 354 | 354 | none | 39/45/86 | ≥120 |
| MNFCTRIRSA | 2013-07-15 | 2026-09-16 | 159 | 159 | 159 | none | 40/45/86 | ≥120 |
| AMTMUO | 2011-07-05 | 2026-09-02 | 181 | 183 | 183 | none | 31/34/79 | ≥120 |
| AMTMVS | 2011-07-05 | 2026-09-02 | 181 | 183 | 183 | none | 31/34/79 | ≥120 |
| CAPUTLG3344S | 2022-09-15 | 2026-09-18 | 48 | 49 | 49 | none | 14/16/64 | <120 |
| CAPUTLG334S | 2015-03-16 | 2026-09-18 | 138 | 139 | 139 | none | 14/16/64 | ≥120 |
| CAPUTLG331S | 2015-03-16 | 2026-09-18 | 138 | 139 | 139 | none | 14/16/64 | ≥120 |
| PCU334413334413 | 2015-05-14 | 2026-09-10 | 136 | 137 | 137 | none | 8/13/75 | ≥120 |
| PCU331110331110 | 2015-05-14 | 2026-09-10 | 136 | 137 | 137 | none | 8/13/75 | ≥120 |
| IPG2211S | 2015-03-16 | 2026-09-18 | 138 | 139 | 139 | none | 14/16/64 | ≥120 |
| CAPUTLG2211S | 2015-03-16 | 2026-09-18 | 138 | 139 | 139 | none | 14/16/64 | ≥120 |
| WPU0543 | 2015-04-14 | 2026-09-10 | 137 | 138 | 138 | none | 8/13/75 | ≥120 |

Cross-check: `python3 -m scripts.audit_alfred_depth --series ... --output research/prophet_v4/r6_program/wave2/alfred_depth_b16a.json` found all 17 present, no gaps in its per-series counts, and verdicts OK/THIN/SHALLOW as quoted in §9. Its OK/THIN thresholds (first vintage before 2010/2015) are **not** rule-1 passes: rule 1 requires at least 120 post-first-release months for two independent mechanisms over the ratified preregistered window. For example, CMRMTSPL is THIN under the audit but has 160 source-clock months; CAPUTLG3344S is SHALLOW and also has only 49 months.

## 3. KEYED-VS-KEYLESS + M3 CROSSWALK

- **First-published value per period (Q6-2):** the keyed store proves it for all 17 configured machinery candidates. It has an initial-release `value` row for every represented `(series, period)` (357 rows across 357 periods for AWHMAN through 138 rows across 138 periods for WPU0543), with `realtime_start` and `realtime_end`. Four series (`PERMIT`, `CMRMTSPL`, `AMTMUO`, `AMTMVS`) also contain later revised rows at the same release timestamp; this does not remove the first-published values, but a keyed audit must select the minimum `realtime_start` row per period. `config/dataset_registry.yml:206-249` records the ALFRED realtime endpoint, the `(series, period, realtime_start)` grain, `value`, and `realtime_start` as the publication clock. This is stronger than the keyless CSV evidence in the cycle census, but it does not prove equality of FRED CSV bytes and the keyed output-type-4 response; that equivalence remains UNKNOWN.
- **Remaining M3 crosswalk (Q6-3):** the only committed M3 observations found in the governing cycle census are public single-ID probes for machinery totals/categories and exact-ID failures for the queried alternatives. No authoritative Census-to-FRED crosswalk is present at `origin/main`. Therefore:
  - Machinery total and tested category order/shipment/unfilled/inventory IDs: PUBLIC PROBE FOUND in the census, but local vintage store status UNKNOWN.
  - `A33XMVS` / `A33XMUO` / `A33XMTI` capital-goods counterparts, farm `A33ANO` / `A33AUO`, and all `A33J*` turbine measures: UNKNOWN in this repo; exact-ID probe failures are not proof of Census absence.
  - Census-only historical files and their vintage clocks: UNKNOWN; no provider contract is present.

## 4. MEMBERSHIP, IDENTITY AND FAILURE COVERAGE

| Artifact | Measurement | Readiness implication |
|---|---|---|
| `membership_history.parquet` | 3,114 rows; snapshots 2026-08-13, 2026-08-18, and 2026-09-04; 1 suite (`baskets`), 49 lists, 710 distinct names; 1,038 rows and 708 distinct names per snapshot | First observed cut is 2026-08-13; content is identical across all three cuts. |
| Dead-name candidates | `EQR` and `GOLD` occur in earlier snapshots but not the latest. Neither is in the six-row `config/delisted_symbols.yml`. Both currently resolve through vendor aliases to one security-master row each; `EQR→VMRK` has dated alias rows and the census records an identity break, while `GOLD` is explicitly deferred/disclosed in `_receipt.json`. | Their absence is not failure coverage; it is identity-change/reuse evidence. |
| `tree_history.jsonl` | every `asof`: 2026-07-05 and 2026-08-15 | Theme-tree history begins 2026-07-05. |
| THS history | `data/basket_levels/china_ths.parquet`: first date 2026-07-02, 78 rows | Daily levels exist only from 2026-07-02; this is not issuer membership and is not a US industrial mapping source. |
| `security_master.parquet` | 2,380 rows, 2,379 securities, 1,213 issuer IDs, effective dates 2012-08-31→2026-09-21, ingestion 2026-08-13→2026-09-21; security states: 2,379 null and 1 `SUPERSEDED_DUPLICATE_MINT`; issuer states: 1,212 `RESOLVED`, 1,167 `NO_ISSUER_EVIDENCE`, 1 deferred | It is a current/correction snapshot, not an issuer lifecycle table. Effective dates are key inception facts, not first-observed issuer coverage. |
| `vendor_aliases.parquet` | 6,035 rows, 2,379 security IDs; vendors: membership 1,218, store 1,217, theme graph 1,163, Yahoo/Yahoo fetch 1,219 each, ledger 2; 7 rows have `valid_from`/`valid_to` | Alias coverage is overwhelmingly current-name; only 7 dated alias bounds exist. |
| Membership alias coverage | 3,088 of 3,114 membership rows have an alias symbol; 9 distinct names are uncovered at some cut: `ANGPY`, `B`, `BLD`, `CBOE`, `EA`, `GATO`, `IMPUY`, `MAG`, `RHHBY` | `_receipt.json` reports identity resolution 708/718 with these names unresolved; alias presence alone is not issuer-safe historical identity. |
| Delisted registry | Six names: `AVB`, `CTRA`, `FBRX`, `LEG`, `TPH`, `TWO`. Only `AVB` appears in every membership cut. | Six curated exits do not constitute general failure coverage. |

Per historical membership cut, failed/delisted issuer coverage is: **FAIL** at 2026-08-13, 2026-08-18, and 2026-09-04. Only one of six delisted names is present; the other five are absent without evidence that they belong to these baskets, and no general original-universe/failed-issuer registry exists. Security-master ingestion starts 2026-08-13, so no earlier cut can be evidenced from this snapshot. **Earliest cut satisfying rules 2 and 3: none.** Rule 2 alone has a genuine observed membership cut at 2026-08-13, but rule 3 fails at every observed cut.

## 5. UNITS AND MAPPING CASES

| Candidate / leg | Configured semantic evidence | Unit and measurement case | Mapping constraint |
|---|---|---|---|
| (a) `AWHMAN` | `config.yml:361-365` | Average weekly hours, manufacturing; labor level, not orders or shipments. | Macro-only; no issuer mapping. |
| (a) `PERMIT` | `config.yml:361-365` | Count of new private housing units authorized; physical permit volume, NSA-compatible administrative count as configured without a seasonal declaration here. | Macro-only; no issuer mapping. |
| (a) `NEWORDER` | `config.yml:361-365` and `:433-456` | New orders, nondefense capital goods excluding aircraft; nominal order flow, dollars. | Capital-goods aggregate, not granular machinery. |
| (a) `CMRMTSPL` | `config.yml:366-368` | Real manufacturing and trade sales; real dollar volume. | Macro-only. |
| (a) `ISRATIO` | `config.yml:369-372` and `:446-453` | Total-business inventories divided by sales; dimensionless ratio. | Macro-only. |
| (a) `MNFCTRIRSA` | `config.yml:446-453` | Manufacturing inventory-to-sales ratio, SA. | Total manufacturing, not machinery grain. |
| (a) `AMTMUO` | `config.yml:446-453` | Manufacturers' unfilled orders, total manufacturing; nominal order backlog in dollars. | Backlog/order-flow case; total manufacturing grain. |
| (a) `AMTMVS` | `config.yml:446-453` | Manufacturers' value of shipments, total manufacturing; nominal shipment flow in dollars. | Shipment case; total manufacturing grain. |
| (b) `CAPUTLG3344S` | `config.yml:433-445` | Capacity utilization, semiconductors and electronic components, percent, NAICS 3344. | Sector capacity, not equipment-maker membership. |
| (b) `CAPUTLG334S` | `config.yml:433-445` | Capacity utilization, computer and electronic products, percent, NAICS 334. | Broad electronics capacity, not semiconductor equipment. |
| (b) `PCU334413334413` | `config.yml:433-457` | PPI, semiconductor and related device manufacturing; price index. | Price level, not equipment orders/shipments. |
| (b) `CAPUTLG331S` | `config.yml:433-445` | Capacity utilization, primary metals, percent, NAICS 331. | Upstream industrial capacity context. |
| (c) `PERMIT` plus housing legs | `config.yml:211-214` and `:361-365` | Permits and starts are counts/SAAR; Case-Shiller is a seasonally adjusted house-price index; mortgage rate is a percent. | Only `PERMIT` is in the vintage list; starts/HPI/mortgage legs lack measured vintage rows. |
| (c) other detail power/steel legs | `config.yml:154-157` | Capacity utilization is percent; `PCU331110331110` and `WPU0543` are PPI indices. | Broad industrial material context, not building-products issuer membership. |

No segment mapping dated after a decision cut may be used. `members_asof` selects only the newest stored snapshot on or before the decision date and returns `pit=False` for pre-store fallback; the measured snapshots make that fence effective from 2026-08-13. Security-master ingestion (first 2026-08-13), dated aliases (seven rows), tree history (2026-07-05), and THS daily history (2026-07-02) likewise establish first observed/correction clocks rather than permitting backdating. A later-dated GICS, current basket, theme, or identity mapping cannot be substituted at an earlier cut; if a cut predates its source clock, the mapped branch is prospective-only or macro-only.

## 6. RIGHTS PER BRANCH

Five answers always mean acquisition / processing / storage / model use / user redistribution. “Recorded” means the cited in-repo record says it; otherwise it is UNKNOWN. A family-level label is not extended to an unrecorded dataset.

| Branch | Acquisition | Processing | Storage | Model use | User redistribution | Proof |
|---|---|---|---|---|---|---|
| FRED/ALFRED initial-release store | RECORDED through the API endpoint | UNKNOWN beyond the local read contract | RECORDED as the named parquet | UNKNOWN | UNKNOWN | Endpoint, grain, value and publication clock at `config/dataset_registry.yml:206-244`; storage at `:210-213`; one blanket `licensing: public_domain` label at `:225`, which does not separately answer processing, model use, or redistribution. No per-series rights tag is present in the parquet or JSON. |
| Census M3 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No Census row was found in `config/dataset_registry.yml`, `config/theme_sources.yml`, or `research/licenses/`. This explicitly answers cycle Q6-6 as UNKNOWN. |
| Historical issuer/segment mapping | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Explicit cycle Q6-7 answer; no entitlement record exists. |
| Massive historical issuer universe | RECORDED for enterprise stock-market reference data | RECORDED for non-display calculation and Derived Materials | RECORDED archival retention | RECORDED for AI/ML and inference | RECORDED for raw/derived external redistribution | `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:8-17` grants scope; rights at `:19-48`; dataset-specific overrides at `:50-55`. Explicit cycle Q6-8 caveat: no Massive historical-issuer/dead-name dataset or per-feed designation is present, so the scope record alone does not prove that this exact provider branch exists. |
| Curated basket membership | RECORDED house curation | RECORDED house-owned | RECORDED local store | RECORDED house direct-display posture | RECORDED direct display / no external rights | `config/theme_sources.yml:21-28`; storage measured in §4. |
| Finviz theme tree | RECORDED as keyless public route | UNKNOWN | UNKNOWN for model-facing rights | UNKNOWN | UNKNOWN / unresolved | `config/theme_sources.yml:29-34`. |
| THS concepts | RECORDED as receipted scrape | UNKNOWN | UNKNOWN for model-facing rights | UNKNOWN | UNKNOWN / unresolved | `config/theme_sources.yml:36-41`; first measured date in §4. |
| S&P Kensho | UNKNOWN (reserved, no ingestion) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `config/theme_sources.yml:43-48`; public methodology documents only and no bulk constituent route. |
| Theia | UNKNOWN (commercial license required, not held in repo) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `config/theme_sources.yml:49-52`. |
| SEC EDGAR | RECORDED public endpoint in issuer census | UNKNOWN rights grant | Mechanism recorded, rights UNKNOWN | UNKNOWN | UNKNOWN | Issuer census §Q5, quoted from its PR-head evidence. |
| Nasdaq earnings calendar/surprise | RECORDED public endpoint in issuer census | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Issuer census §Q5. |
| Yahoo/yfinance expectations | RECORDED direct accessors | RECORDED processing contract | RECORDED local parquets | UNKNOWN (`rights_class: UNKNOWN`) | UNKNOWN | Issuer census §Q5. |
| Transcripts | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Issuer census §Q5; `rp_public_primary_v1` is not a grant. |
| Press / narrative / search | Partly recorded endpoints; rights otherwise | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Issuer census §Q5. |
| ThetaData | RECORDED private subscription | UNKNOWN from filed terms | UNKNOWN from filed terms | UNKNOWN from filed terms | PARTIAL operator record only; full-universe intraday-derived scope open | `research/licenses/THETADATA_ENTITLEMENT_RECORD.md:7-19`. |

## 7. PROVIDER EVALUATION

The required repository search named S&P Kensho, Theia, FactSet, CRSP, Refinitiv, Compustat, and S&P Capital IQ-family candidates. In-repo records establish no licensed historical issuer-mapping provider:

| Provider | Scope recorded in repo | Rights recorded in repo | Cost recorded in repo | Readiness |
|---|---|---|---|---|
| S&P Kensho | Reserved provider row; public methodology/index description only; no bulk constituent route. ETF research records current-only SSGA/SPDR Kensho fund files for forward collection. | `rights_class: unresolved`; no acquisition. | None. | Not a source. |
| Theia | Reserved row for commercial license; no ingestion. The GMI research note records semantic taxonomy concepts only and explicitly authorizes nothing. | `rights_class: unresolved`; commercial license required. | None. | Not a source. |
| FactSet / FactSet Revere | Research notes mention Western supplier/edge coverage and public earnings summaries; they are outside observations, not an entitlement. | No five-rights record. | None. | UNKNOWN. |
| CRSP | Research notes say point-in-time survivorship work would need paid CRSP; no committed provider contract. | No five-rights record. | None. | UNKNOWN. |
| Refinitiv | Research notes mention consensus snapshot or Bloomberg/Refinitiv integration alternatives. | No five-rights record. | None. | UNKNOWN. |
| Compustat | No material row appeared in the capped required search beyond the provider-family term itself. | UNKNOWN. | None. | UNKNOWN. |
| S&P Capital IQ / GICS history | Search returned S&P Capital Markets ETF labels, not a historical GICS entitlement. No GICS-history source appeared. | No five-rights record. | None. | UNKNOWN. |
| Massive | Enterprise record covers stock-market reference data, corporate actions, historical archives, non-display/model use and redistribution, subject to per-feed designations. | Recorded in `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`. | No cost figure is recorded in the allowlisted record. | Enterprise rights are recorded, but no historical issuer-mapping/dead-name feed is identified; scope remains unproved. |

The exact capped command output is quoted in §9. No external provider page or private entitlement was opened, and no cost figure was inferred.

## 8. THE MATRIX + VERDICTS


| Branch | First consumer | Classification | Admissible coverage window | Rights posture | Fallback | Proof path |
|---|---|---|---|---|---|---|
| FRED/ALFRED initial releases | B04/B16 | Admissible point-in-time replay for the 17 measured series | `1997-01-10 → 2026-09-18` overall; series-specific §2 | Five rights unresolved beyond acquisition/storage | Macro-only private diagnostic until rights branch is recorded | `data/fred_vintage/vintages.parquet`; `config/dataset_registry.yml:206-249` |
| Census M3 candidate IDs | B16 | Prospective-only / source-existence observation | none locally (no vintage rows) | UNKNOWN | Keyed collection only after rights record | Cycle census Q2; §3 |
| Curated US membership | B08/B09/B16/B18 | Observed as run from first snapshot | `2026-08-13 → 2026-09-04` | House rights recorded | Macro-only; no pre-snapshot issuer mapping | §4 |
| Finviz tree history | B08/B09 | Observed as run | `2026-07-05 → 2026-08-15` | unresolved | Diagnostic-only; no historical mapping | §4; `config/theme_sources.yml:29-34` |
| THS daily levels | B08 | Observed as run | `2026-07-02 → 2026-09-23` | unresolved | CN diagnostic only; not a US mapping | §4 |
| Security master / aliases | B08/B09 | Current and correction snapshot; only seven dated alias bounds | `2026-08-13 → 2026-09-21` for observation/ingestion | No five-rights source grant | Fail closed for historical issuer identity | §4; `config/dataset_registry.yml:251-330` |
| Delisted-symbol registry | B09 | Observed event registry, not general failure coverage | Six curated exits; dates recorded in the allowlisted file | In-repo curated record | Declare survivorship limit / macro-only | §4 |
| Massive enterprise feed family | B08/B09 | Prospective-only until an exact historical issuer/dead-name feed is identified | none for this use | Enterprise five rights recorded; exact feed scope unknown | Require per-feed designation | `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md:8-55` |
| Licensed historical segment map | B08/B09/B16 | Prospective-only / not acquired | none | UNKNOWN | Macro-only or Chairman provider gate after exact evidence | §6–§7 |

Classification uses playbook step 2 as incorporated by ruling §3: no current map or current identity may be backdated, and reconstruction is diagnostic rather than historical knowledge.

### Candidate × rule verdicts

Each cell names the number that decides it. For rule 1, the two-mechanism independence condition is not adjudicated here; the count column is the measured post-first-release months.

| Candidate | Rule 1 vintage depth | Rule 2 mapping | Rule 3 failure | Rule 4 definitions | Rule 5 rights |
|---|---|---|---|---|---|
| (a) Industrial capital goods / machinery | PASS: at least `NEWORDER` 354 and `AMTMUO`/`AMTMVS` 183 or `AWHMAN` 357 exceed 120; independence reserved to B16-b | FAIL: first genuine membership cut is `2026-08-13`; historical industrial segment-map paths = 0 | FAIL: satisfiable cuts = 0; 1/6 delisted names in observed baskets and no general failed universe | UNKNOWN: dated Census SIC→NAICS/benchmark treatment exists in the census, but this lane did not open the cited source; source-receipted era treatments = 0; total-manufacturing legs cannot be relabeled machinery | FAIL: Census/M3 and mapping branches each have 0 of 5 recorded rights; FRED model/redistribution rights recorded = 0 |
| (b) Semiconductor equipment | FAIL: configured `CAPUTLG3344S` has 49 months; `CAPUTLG334S` has 139 but is broad electronics; equipment-specific orders/shipments legs = 0 | FAIL: first historical equipment-map snapshot = none; historical segment-map paths = 0 | FAIL: failed/delisted issuer rows = 0 for this candidate universe; satisfiable cuts = 0 | UNKNOWN: census asserts the April 2010 M3 discontinuity date, but source-receipted era splits = 0 here; equipment substitution is forbidden | FAIL: Census M3 rights recorded = 0 of 5; historical mapping rights recorded = 0 of 5 |
| (c) Building products / residential construction | FAIL: `PERMIT` has 325 months, but measured housing starts/HPI/mortgage legs = 0, leaving fewer than two measured legs | FAIL: first historical building-products membership snapshot = none; historical segment-map paths = 0 | FAIL: failed/delisted issuer rows = 0 for this candidate universe; satisfiable cuts = 0 | FAIL: source-receipted HPI/starts/mortgage rebaseline or discontinuity treatments = 0; `PERMIT` alone cannot carry the domain | FAIL: issuer mapping and ETF-derived rights recorded = 0 of 5; FRED model/redistribution rights recorded = 0 |

### Proposed preregistered window for (a)

**none.** The source-clock intersection for two legs having vintage rows **and** a genuine membership cut exists only at/after 2026-08-13, but that is merely the first observed membership snapshot, rules 2–3 still fail there, and no pre-2026 historical mapping source exists. Therefore no preregistered issuer-mapped replay window is proposed. If the seat instead declares (a) macro-only, the source-only clock floor is 2013-06-24 (first date when `NEWORDER`, `CMRMTSPL`, and other measured macro legs coexist); this is a fallback fact, not a proposed window, and B16-b must ratify either choice before any outcome work.

## 9. EVIDENCE

Commands are in execution order. `$TMP` denotes the external scratch directory created by `mktemp`; binary paths were written there only after `git show origin/main:<path> > "$TMP/<name>"`.

1. Source and skeleton:

```text
$ git rev-parse origin/main
b47cab58e79ab825e07f640c4a37826095eecc78
$ git status --short --branch
$ wc -l research/prophet_v4/r6_program/wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md
22 ...
```

1. Governing records: `origin/main` lacked all three (`git cat-file -e origin/main:<path>` failed for each), so the exact fallbacks were fetched:

```text
$ git fetch origin refs/pull/7841/head:refs/remotes/pr/7841
 * [new ref] refs/pull/7841/head -> pr/7841
$ git fetch origin refs/pull/7836/head:refs/remotes/pr/7836
 * [new ref] refs/pull/7836/head -> pr/7836
$ git fetch origin refs/pull/7837/head:refs/remotes/pr/7837
 * [new ref] refs/pull/7837/head -> pr/7837
$ git show pr/7841:research/prophet_v4/r6_program/rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md > "$TMP/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md"
$ git show pr/7836:research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md > "$TMP/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md"
$ git show pr/7837:research/prophet_v4/r6_program/wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md > "$TMP/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md"
$ git rev-parse pr/7841 pr/7836 pr/7837
d3b1fb743cbcde38a23ff13def1db47e42335514
68ece597765bb8d842a16434be9c8fc67200ee53
6c0539e253fbab4a8caee8fe02a0732d2f3fb341
```

1. Round-2 source refresh:

```text
$ git fetch origin main
 * branch main -> FETCH_HEAD
   b61a3f1930..b47cab58e7 main -> origin/main
$ git rev-parse origin/main
b47cab58e79ab825e07f640c4a37826095eecc78
$ git ls-tree -r --name-only origin/main data | grep -iE 'ths' | head
data/basket_levels/china_ths.parquet
```

1. Allowlist discovery:

```text
$ git ls-tree --name-only origin/main data/reference/
data/reference/_receipt.json
data/reference/issuer_master.parquet
data/reference/issuer_migrations.parquet
data/reference/security_master.parquet
data/reference/security_migrations.parquet
data/reference/vendor_aliases.parquet
$ git ls-tree -r --name-only origin/main data | grep -iE 'ths' | head
data/basket_levels/china_ths.parquet
$ git ls-tree -r --name-only origin/main research/licenses/
research/licenses/MASSIVE_ENTITLEMENT_RECORD.md
research/licenses/THETADATA_ENTITLEMENT_RECORD.md
```

Every path in §1 was copied by `git show origin/main:<path> > "$TMP/<name>"`. `collectors/fred.py`, `collectors/base.py`, `lib/config.py`, `lib/store.py`, and `config.yml` were then copied with `cp` into `$TMP/audit-root` so the unchanged module import path could resolve the already-copied parquet. No worktree data path was read or written.

1. Round-1 source shapes were inspected with a scratch-only `inspect_sources.py`; round 2 refreshed every listed source at `b47cab58e7` and changed only the master-row counts recorded in this section:

```text
### data_fred_vintage_vintages.parquet
shape (16472, 5)
columns ['series', 'period', 'value', 'realtime_start', 'realtime_end']
### data_baskets_membership_history.parquet
shape (3114, 9)
columns ['snapshot_date', 'suite', 'basket_id', 'ticker', 'added', 'removed', 'name_zh', 'members_sha', 'source_shape']
### data_themes_heatmap_tree_history.jsonl
0 {'asof': '2026-07-05'}
1 {'asof': '2026-08-15'}
### data_reference_security_master.parquet
shape (2380, 13)
columns ['security_id', 'issuer_id', 'issuer_state', 'issuer_cik', 'issuer_evidence_snapshot', 'listing_key', 'country', 'mic', 'inception_code', 'effective_at', 'ingested_at', 'security_state', 'superseded_by']
### data_reference_vendor_aliases.parquet
shape (6035, 6)
columns ['vendor', 'vendor_symbol', 'security_id', 'valid_from', 'valid_to', 'ingested_at']
### data_basket_levels_china_ths.parquet
shape (78, 1186)
THS_INDEX_NAME date
THS_FIRST_ROWS [Timestamp('2026-07-02'), Timestamp('2026-07-03')]
THS_LAST_ROWS [Timestamp('2026-09-22'), Timestamp('2026-09-23')]
```

1. The §2 pandas snippet created the exact `series` list from Q6-1 and, for each series, calculated min/max `realtime_start`, row and period counts, the calendar-month span, missing calendar months, and month-end→release lag:

```python
series = 'AWHMAN PERMIT NEWORDER CMRMTSPL INDPRO ISRATIO MNFCTRIRSA AMTMUO AMTMVS CAPUTLG3344S CAPUTLG334S CAPUTLG331S PCU334413334413 PCU331110331110 IPG2211S CAPUTLG2211S WPU0543'.split()
v = pd.read_parquet(root / 'data_fred_vintage_vintages.parquet')
for sid in series:
    d = v[v.series.eq(sid)].copy()
    first_period, latest_period = d.period.min(), d.period.max()
    months = (latest_period.year - first_period.year) * 12 + (latest_period.month - first_period.month) + 1
    present = pd.PeriodIndex(d.period, freq='M')
    all_months = pd.period_range(first_period, latest_period, freq='M')
    gaps = sorted(str(x) for x in all_months.difference(present))
    month_end = d.period.dt.to_period('M').dt.to_timestamp('M')
    lag_days = (d.realtime_start - month_end).dt.days
```

Its output follows. No series was missing and every gap list was `none`.

```text
AWHMAN first_rt=1997-01-10 latest_rt=2026-09-04 n_vintages=356 rows=357 n_periods=357 post_months=357 gaps=none lag=1/5/51
PERMIT first_rt=1999-09-17 latest_rt=2026-09-17 n_vintages=321 rows=325 n_periods=325 post_months=325 gaps=none lag=16/18/101
NEWORDER first_rt=1997-03-26 latest_rt=2026-08-26 n_vintages=354 rows=354 n_periods=354 post_months=354 gaps=none lag=21/26/57
CMRMTSPL first_rt=2013-06-24 latest_rt=2026-08-26 n_vintages=155 rows=160 n_periods=160 post_months=160 gaps=none lag=50/60/114
INDPRO first_rt=1997-01-17 latest_rt=2026-09-18 n_vintages=356 rows=357 n_periods=357 post_months=357 gaps=none lag=14/16/64
ISRATIO first_rt=1997-04-15 latest_rt=2026-09-16 n_vintages=354 rows=354 n_periods=354 post_months=354 gaps=none lag=39/45/86
MNFCTRIRSA first_rt=2013-07-15 latest_rt=2026-09-16 n_vintages=159 rows=159 n_periods=159 post_months=159 gaps=none lag=40/45/86
AMTMUO first_rt=2011-07-05 latest_rt=2026-09-02 n_vintages=181 rows=183 n_periods=183 post_months=183 gaps=none lag=31/34/79
AMTMVS first_rt=2011-07-05 latest_rt=2026-09-02 n_vintages=181 rows=183 n_periods=183 post_months=183 gaps=none lag=31/34/79
CAPUTLG3344S first_rt=2022-09-15 latest_rt=2026-09-18 n_vintages=48 rows=49 n_periods=49 post_months=49 gaps=none lag=14/16/64
CAPUTLG334S first_rt=2015-03-16 latest_rt=2026-09-18 n_vintages=138 rows=139 n_periods=139 post_months=139 gaps=none lag=14/16/64
CAPUTLG331S first_rt=2015-03-16 latest_rt=2026-09-18 n_vintages=138 rows=139 n_periods=139 post_months=139 gaps=none lag=14/16/64
PCU334413334413 first_rt=2015-05-14 latest_rt=2026-09-10 n_vintages=136 rows=137 n_periods=137 post_months=137 gaps=none lag=8/13/75
PCU331110331110 first_rt=2015-05-14 latest_rt=2026-09-10 n_vintages=136 rows=137 n_periods=137 post_months=137 gaps=none lag=8/13/75
IPG2211S first_rt=2015-03-16 latest_rt=2026-09-18 n_vintages=138 rows=139 n_periods=139 post_months=139 gaps=none lag=14/16/64
CAPUTLG2211S first_rt=2015-03-16 latest_rt=2026-09-18 n_vintages=138 rows=139 n_periods=139 post_months=139 gaps=none lag=14/16/64
WPU0543 first_rt=2015-04-14 latest_rt=2026-09-10 n_vintages=137 rows=138 n_periods=138 post_months=138 gaps=none lag=8/13/75
```

1. Membership/identity/failure snippet:

```python
m = pd.read_parquet(root / 'data_baskets_membership_history.parquet')
dead = sorted(set(m.ticker[m.snapshot_date < m.snapshot_date.max()]) - set(m.ticker[m.snapshot_date == m.snapshot_date.max()]))
sm = pd.read_parquet(root / 'data_reference_security_master.parquet')
va = pd.read_parquet(root / 'data_reference_vendor_aliases.parquet')
dl = yaml.safe_load((root / 'config_delisted_symbols.yml').read_text())['symbols']
```

```text
MEMBERSHIP 2026-08-13 2026-09-04 3114 1 49
SNAPSHOTS: each of 2026-08-13, 2026-08-18, 2026-09-04 has 1038 rows, 49 lists, 708 tickers
DEAD_NAME_CANDIDATES 2 EQR,GOLD
DELISTED 6 AVB,CTRA,FBRX,LEG,TPH,TWO
DEAD_CANDIDATE EQR delisted False alias_rows 3 master_rows 1
DEAD_CANDIDATE GOLD delisted False alias_rows 4 master_rows 1
SECURITY_MASTER 2380 ... states {nan: 2379, SUPERSEDED_DUPLICATE_MINT: 1} ingested 2026-08-13 ... 2026-09-21
VENDOR_ALIASES 6035 ... valid_from_nonnull 7 valid_to_nonnull 7 securities 2379
ALIAS_UNCOVERED_NAMES ANGPY,B,BLD,CBOE,EA,GATO,IMPUY,MAG,RHHBY
THS_LEVELS 78 2026-07-02 2026-09-23
```

1. The mandated cross-check ran from `$TMP/audit-root` using the unchanged support copies named in §1 and the already-read parquet. It wrote only the mandated JSON into this worktree:

```text
$ (cd "$TMP/audit-root" && python3 -m scripts.audit_alfred_depth --series AWHMAN,...,WPU0543 --output "$REPO/research/prophet_v4/r6_program/wave2/alfred_depth_b16a.json")
loaded vintage store: 16,472 rows, 54 series
AWHMAN           OK        1997-01-10          356
PERMIT           OK        1999-09-17          321
NEWORDER         OK        1997-03-26          354
CMRMTSPL         THIN      2013-06-24          155
INDPRO           OK        1997-01-17          356
ISRATIO          OK        1997-04-15          354
MNFCTRIRSA       THIN      2013-07-15          159
AMTMUO           THIN      2011-07-05          181
AMTMVS           THIN      2011-07-05          181
CAPUTLG3344S     SHALLOW   2022-09-15           48
CAPUTLG334S      SHALLOW   2015-03-16          138
CAPUTLG331S      SHALLOW   2015-03-16          138
PCU334413334413  SHALLOW   2015-05-14          136
PCU331110331110  SHALLOW   2015-05-14          136
IPG2211S         SHALLOW   2015-03-16          138
CAPUTLG2211S     SHALLOW   2015-03-16          138
WPU0543          SHALLOW   2015-04-14          137
SUMMARY: PIT-OK ... AWHMAN, PERMIT, NEWORDER, INDPRO, ISRATIO
SUMMARY: THIN/SHALLOW ... CMRMTSPL, MNFCTRIRSA, AMTMUO, AMTMVS, CAPUTLG3344S, CAPUTLG334S, CAPUTLG331S, PCU334413334413, PCU331110331110, IPG2211S, CAPUTLG2211S, WPU0543
SUMMARY: ABSENT ... none
```

The audit's `n_vintages` counts distinct release timestamps; §2's row counts are the literal store rows. Both agree on period coverage.

1. Provider search:

```text
$ git grep -n -iE 'kensho|theia|compustat|crsp|refinitiv|factset|s&p capital|gics history' origin/main -- config research | head -40
origin/main:config/theme_sources.yml:45: # sp_kensho:
origin/main:config/theme_sources.yml:49: # theia:
origin/main:research/CN_COMMERCIAL_SUPPLY_CHAIN_DILIGENCE_2026_08_19.md:191: Western FactSet Revere ... not a license.
origin/main:research/ETF_DATA_SOURCES.md:72: SSGA / SPDR S&P Kensho (current-only XLSX — forward collection)
origin/main:research/GATE0_SURVIVORSHIP.md:90: ... needs paid CRSP ...
origin/main:research/GLOBAL_MARKET_INTELLIGENCE_MASTERPLAN_BY_FABLE.md:284: Theia taxonomy/Kensho ... authorizes nothing ...
origin/main:research/RIC_DOMAIN_RESEARCH_PACK_2026-07-13.md:96: ... free via standard data vendors including Bloomberg, Refinitiv ...
origin/main:research/RIC_DOMAIN_RESEARCH_PACK_2026-07-13.md:698: FactSet GeoRev methodology ...
origin/main:research/SEASONAX_BIOPHARMA_SEASONALITY_INTELLIGENCE_BUILD_DOCKET_FOR_FABLE.md:107: ... reserved for Bloomberg/Refinitiv integrations.
origin/main:research/SIGNAL_AUDIT.md:83: ... needs paid CRSP ... Basis: Shumway (1997), CRSP PIT.
origin/main:research/SIGNAL_LAB_FRONTIER_DAY2_FABLE_ADJUDICATION_2026-07-06.md:107: sparse vs FactSet Revere coverage
origin/main:research/SIGNAL_LAB_FRONTIER_PHASE0_2026-07-06.md:92: N-PORT/CRSP ... not fully in repo.
origin/main:research/alpha_intelligence/censuses/B0/B0_MANAGER_COMPLEX_DRAFT.md:49: SSGA Kensho ...
```

The full capped result had 40 lines; no Compustat entitlement or GICS-history row appeared. Duplicated ETF/research name-drops and non-provider prose are represented above without changing any provider conclusion.

## 10. GAPS + MUST-NOTS REFUSED

- **Rule 2/3 closure:** no historical industrial, equipment, or building-products segment map and no original failed-issuer universe exist. The earliest satisfiable cut is none. A licensed historical mapping/failure source remains the exact human/provider question; no commitment is made here.
- **Rule 4 for (a)/(b):** the census cites Census SIC→NAICS, benchmark, semiconductor-M3 discontinuity and seasonal-method treatment, but those source documents were outside this task allowlist. This matrix records UNKNOWN rather than opening them.
- **Rule 5:** Census/M3 and historical issuer mapping have no recorded five-rights answers. FRED model use and redistribution remain unresolved; one blanket public-domain label is insufficient. Massive enterprise scope is recorded but does not identify an exact historical issuer/dead-name feed.
- **M3:** keyless CSV/keyed API byte-equivalence and authoritative Census crosswalks remain UNKNOWN. No key was used and no missing probe was run.
- **Identity:** security master is not a lifecycle table; alias coverage is current-heavy and only seven alias rows are dated. Nine membership names remain unresolved, and `EQR`/`GOLD` are identity-change cases, not dead-name coverage.
- **Costs:** no provider cost was inferred. The only allowlisted cost number, ThetaData's private subscription amount, is deliberately not restated here because it is irrelevant to this branch and commercial details should remain in its record.
- MUST-NOT REFUSED: no current membership, event set, GICS assignment, segment mapping, or issuer identity was backdated; no broad aggregate was relabeled as machinery; no modeled lag minted a vintage date.
- MUST-NOT REFUSED: no sparse-tree opt-in, `--probe-missing`, keyed network call, credential, `.env`, or forbidden outcome artifact was used. `data/` was never written.
- **No return, outcome, ledger, scoreboard or trial artifact was opened.**
