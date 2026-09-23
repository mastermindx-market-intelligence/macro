# D03 Source Readiness Matrix — 2026-09-23
STATUS: IN_PROGRESS

## 1. SOURCE_SHA + PATHS READ

- SOURCE_SHA: `742a2e86c505cca926dee2c68d7166c10a7128a1` (`git rev-parse origin/main`).
- Governing fallback records were read by exact `git show` from PR refs, not from `origin/main`: ruling `d3b1fb743cbcde38a23ff13def1db47e42335514`, cycle census `68ece597765bb8d842a16434be9c8fc67200ee53`, issuer census `6c0539e253fbab4a8caee8fe02a0732d2f3fb341`. The three are absent from `origin/main`; §9 records the three exact fallback commands.
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
  15. `data/basket_levels/china_ths.parquet` (the first history path found by the required THS locator)
- Listing-only commands were used for allowlisted discovery: `git ls-tree --name-only origin/main data/reference/`, `git ls-tree -r --name-only origin/main | grep -iE 'ths' | head`, and `git ls-tree -r --name-only origin/main research/licenses/`. No listed detail was opened outside the paths above. No forbidden path was read.

## 2. VINTAGE DEPTH PER SERIES

The cycle census Q6-1 list contains all 17 series below. `post-first-release months` is the calendar-month span from each series' first observation period through its latest observation period, not merely the row count. `gaps` lists missing calendar months in that span. Release lag runs from month end to `realtime_start` and is reported min/median/max in days.

| Series | First realtime | Latest realtime | n_vintages | n_periods | Post-first-release months | Missing vintage months | Lag min/med/max days | 120-month mark |
|---|---:|---:|---:|---:|---:|---|---:|---|
| AWHMAN | 1997-01-10 | 2026-09-04 | 357 | 357 | 357 | none | 1/5/30 | ≥120 |
| PERMIT | 1999-09-17 | 2026-09-17 | 325 | 325 | 325 | none | 7/9/72 | ≥120 |
| NEWORDER | 1997-03-26 | 2026-08-26 | 354 | 354 | 354 | none | 9/14/42 | ≥120 |
| CMRMTSPL | 2013-06-24 | 2026-08-26 | 160 | 160 | 160 | none | 19/29/83 | ≥120 |
| INDPRO | 1997-01-17 | 2026-09-18 | 357 | 357 | 357 | none | 1/3/49 | ≥120 |
| ISRATIO | 1997-04-15 | 2026-09-16 | 354 | 354 | 354 | none | 9/15/55 | ≥120 |
| MNFCTRIRSA | 2013-07-15 | 2026-09-16 | 159 | 159 | 159 | none | 10/15/55 | ≥120 |
| AMTMUO | 2011-07-05 | 2026-09-02 | 183 | 183 | 183 | none | 1/4/49 | ≥120 |
| AMTMVS | 2011-07-05 | 2026-09-02 | 183 | 183 | 183 | none | 1/4/49 | ≥120 |
| CAPUTLG3344S | 2022-09-15 | 2026-09-18 | 49 | 49 | 49 | none | 1/3/49 | <120 |
| CAPUTLG334S | 2015-03-16 | 2026-09-18 | 139 | 139 | 139 | none | 1/3/49 | ≥120 |
| CAPUTLG331S | 2015-03-16 | 2026-09-18 | 139 | 139 | 139 | none | 1/3/49 | ≥120 |
| PCU334413334413 | 2015-05-14 | 2026-09-10 | 137 | 137 | 137 | none | 1/6/68 | ≥120 |
| PCU331110331110 | 2015-05-14 | 2026-09-10 | 137 | 137 | 137 | none | 1/6/68 | ≥120 |
| IPG2211S | 2015-03-16 | 2026-09-18 | 139 | 139 | 139 | none | 1/3/49 | ≥120 |
| CAPUTLG2211S | 2015-03-16 | 2026-09-18 | 139 | 139 | 139 | none | 1/3/49 | ≥120 |
| WPU0543 | 2015-04-14 | 2026-09-10 | 138 | 138 | 138 | none | 1/6/68 | ≥120 |

Cross-check: `python3 -m scripts.audit_alfred_depth --series ... --output research/prophet_v4/r6_program/wave2/alfred_depth_b16a.json` found all 17 present, no gaps in its per-series counts, and verdicts OK/THIN/SHALLOW as quoted in §9. Its OK/THIN thresholds (first vintage before 2010/2015) are **not** rule-1 passes: rule 1 requires at least 120 post-first-release months for two independent mechanisms over the ratified preregistered window. For example, CMRMTSPL is THIN under the audit but has 160 source-clock months; CAPUTLG3344S is SHALLOW and also has only 49 months.

## 3. KEYED-VS-KEYLESS + M3 CROSSWALK

## 4. MEMBERSHIP, IDENTITY AND FAILURE COVERAGE

## 5. UNITS AND MAPPING CASES

## 6. RIGHTS PER BRANCH

## 7. PROVIDER EVALUATION

## 8. THE MATRIX + VERDICTS

## 9. EVIDENCE

## 10. GAPS + MUST-NOTS REFUSED
