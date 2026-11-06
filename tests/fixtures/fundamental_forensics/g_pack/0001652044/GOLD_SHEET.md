# GOOGL gold sheet — G4 pack (fif-g-a-googl-20261019b)

- Issuer: Alphabet Inc. — CIK 0001652044 — entity_id `ISS:US-XNAS-GOOG` — security_id `SEC:US-XNAS-GOOGL` — listing_keys `US-XNAS-GOOG`, `US-XNAS-GOOGL` — issuer_class `software` (config/fundamental_forensics/coverage/five_issuer_v1.json).
- Base commit: `cbcf823d4045ff640e63a2a0531a1a8155f5ae02` (branch claude/fif-g0-rebase-20261018, which merges origin/main through 69dd6e77).
- Gold source: `fif-ggold-20261013/r2`, file list + sha256 in `pack_manifest.gold_source.files`.
- `attested: false`; `historical_attestation: unavailable_until_d2_admission` (spec §0 gate 8).
- The ORCH-G kernel-comparison rulings `R-G-1 .. R-G-6` (hyphenated) are distinct from the earlier gold-engine rulings `R-G1` (Decimal contract), `R-G2` (period alignment) and `R-G3` (knowledge time and the two views) that the r2/r3 gold sheets cite (RULINGS.md §0; GOLD_SHEET.md preamble).
- Rulings applied to this issuer (each with cited example cells below): **R-G-2** for the 9 View B `common_shares_outstanding` cover-page instants and `operating_expenses` duration cells (C4b dimension refusal, byte re-read on this lane).
- Frozen spec sha256: `e7b0286c0a0d33221a23d4a546c25c26abe7ee1347a8116c89142e330299bb98` (matches G_PACK_FROZEN_SPEC.md). ERRATA-1 (E1-E7) binds. No r2 gold value changed for this issuer (gold_corrections fields = `code`, `r1_code`, `detail`, `axes_seen` only — every corrected (row, field) is an absence-classification correction, not a value edit).
- Every staged member re-passed the package-manifest sha256 check on the r2 lane and again on this lane for every member cited by a pin or correction.

## 1. Accessions (admitted set R5; knowledge time cited per accession; from pack_manifest)

| role | accession | form | period_of_report | knowledge_time | manifest verdict | View A cells |
|---|---|---|---|---|---|---|
| newest 10-K | 0001652044-26-000018 | 10-K | 2025-12-31 | 2026-02-05T02:56:03.000Z | pass (6 members) | 408 (verified 91 / na 208 / absent 109) |
| comparable 10-K | 0001652044-25-000014 | 10-K | 2024-12-31 | 2025-02-05T01:41:40.000Z | pass (6 members) | 408 (verified 93 / na 208 / absent 107) |
| newest 10-Q | 0001652044-26-000071 | 10-Q | 2026-06-30 | 2026-07-23T01:15:54.000Z | pass (6 members) | 663 (verified 102 / na 338 / absent 223) |
| second 10-Q | 0001652044-26-000048 | 10-Q | 2026-03-31 | 2026-04-30T01:02:11.000Z | pass (6 members) | 459 (verified 73 / na 234 / absent 152) |
| capture-only (not admitted, R5) | 0001652044-25-000062 | 10-Q | 2025-06-30 | — | pass (6 members) | n/a |

knowledge_time for every accession from `sec_submissions_witness.json:acceptanceDateTime`.

## 2. Views built (R-G3)

- **VIEW A `as_filed`**: one cell set per admitted package, built ONLY from that package's own ix facts (comparative columns included). 1938 cells across 4 packages.
  - 0001652044-26-000018: 408 cells — not_applicable_verified=208, typed_absence_verified=109, verified_from_bytes=91
  - 0001652044-25-000014: 408 cells — not_applicable_verified=208, typed_absence_verified=107, verified_from_bytes=93
  - 0001652044-26-000071: 663 cells — not_applicable_verified=338, typed_absence_verified=223, verified_from_bytes=102
  - 0001652044-26-000048: 459 cells — not_applicable_verified=234, typed_absence_verified=152, verified_from_bytes=73
- **VIEW B `latest_known_as_of`**: for each (metric, period) the value from the newest admitted package reporting it, ordered by knowledge_time — the r1 method. 1275 cells — not_applicable_verified=650, typed_absence_verified=358, verified_from_bytes=267. Informational only.
- Cross-package value differences are recorded as `restatement_observed` findings (§Findings), never resolved by picking. None for GOOGL.

## 3. Statement roles

Copied from r1 `statement_roles.json` without edits. Deterministic rule text and per-accession role picks are in that file.

## 4. Headline cells — VIEW A of the newest admitted 10-K (0001652044-26-000018; knowledge_time 2026-02-05T02:56:03.000Z)

Value column is `value_exact`. Every verified cell below re-opened `goog-20251231.htm` (sha256 `34a5db240851fab80a2ed1bf7d01b5c9c648b1290148ba4030acf2da89071172`, equal to the g_src manifest digest), located by concept+contextRef at the r2 byte_offset, and re-derived from raw text under scale/sign.

| metric | period | value_exact | rendered millions | concept | contextRef | state |
|---|---|---|---|---|---|---|
| revenue | FY2025 | 402836000000 | 402,836 | us-gaap:Revenues | c-1 | verified_from_bytes |
| cost_of_revenue | FY2025 | 162535000000 | 162,535 | us-gaap:CostOfRevenue | c-1 | verified_from_bytes |
| gross_profit | FY2025 | | | | | typed_absence_verified (missing_standard_fact) |
| operating_expenses | FY2025 | | | | | typed_absence_verified (disallowed_dimension) |
| operating_income_loss | FY2025 | 129039000000 | 129,039 | us-gaap:OperatingIncomeLoss | c-1 | verified_from_bytes |
| net_income_loss | FY2025 | 132170000000 | 132,170 | us-gaap:NetIncomeLoss | c-1 | verified_from_bytes |
| research_and_development_expense | FY2025 | 61087000000 | 61,087 | us-gaap:ResearchAndDevelopmentExpense | c-1 | verified_from_bytes |
| net_cash_from_operating_activities | FY2025 | 164713000000 | 164,713 | us-gaap:NetCashProvidedByUsedInOperatingActivities | c-1 | verified_from_bytes |
| capital_expenditures | FY2025 | 91447000000 | 91,447 | us-gaap:PaymentsToAcquirePropertyPlantAndEquipment | c-1 | verified_from_bytes |
| cash_and_cash_equivalents | 2025-12-31 | 30708000000 | 30,708 | us-gaap:CashAndCashEquivalentsAtCarryingValue | c-1 | verified_from_bytes |
| short_term_investments | 2025-12-31 | 96135000000 | 96,135 | us-gaap:MarketableSecuritiesCurrent | c-1 | verified_from_bytes |
| inventory_net | 2025-12-31 | | | | | typed_absence_verified (missing_standard_fact) |
| total_assets | 2025-12-31 | 595281000000 | 595,281 | us-gaap:Assets | c-1 | verified_from_bytes |
| long_term_debt | 2025-12-31 | 46547000000 | 46,547 | us-gaap:LongTermDebtNoncurrent | c-20 | verified_from_bytes |
| long_term_debt_current | 2025-12-31 | 1996000000 | 1,996 | us-gaap:LongTermDebtCurrent | c-1 | verified_from_bytes |
| short_term_debt | 2025-12-31 | | | | | typed_absence_verified (missing_standard_fact) |
| total_debt | 2025-12-31 | | | | | typed_absence_verified (missing_dependency) — E2 |
| stockholders_equity | 2025-12-31 | 415265000000 | 415,265 | us-gaap:StockholdersEquity | c-1 | verified_from_bytes |
| total_liabilities | 2025-12-31 | 180016000000 | 180,016 | us-gaap:Liabilities | c-1 | verified_from_bytes |
| basic_earnings_per_share | FY2025 | 10.91 | 10.91 | us-gaap:EarningsPerShareBasic | c-1 | verified_from_bytes |
| diluted_earnings_per_share | FY2025 | 10.81 | 10.81 | us-gaap:EarningsPerShareDiluted | c-1 | verified_from_bytes |
| basic_weighted_average_shares | FY2025 | 12116000000 | 12116000000 | us-gaap:WeightedAverageNumberOfSharesOutstandingBasic | c-1 | verified_from_bytes |
| diluted_weighted_average_shares | FY2025 | 12230000000 | 12230000000 | us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding | c-1 | verified_from_bytes |
| share_based_compensation_expense | FY2025 | 24953000000 | 24,953 | us-gaap:ShareBasedCompensation | c-1 | verified_from_bytes |
| free_cash_flow | FY2025 | 73266000000 (formula) | | net_cash_from_operating_activities − capital_expenditures | | verified_from_bytes |
| gross_margin | FY2025 | | | | | typed_absence_verified (missing_dependency) — E2 |
| common_shares_outstanding | 2025-12-31 | | | | | typed_absence_verified (missing_standard_fact) |
| receivables_to_revenue | FY2025 | 0.1561081929122521323814157622456781 (formula) | | accounts_receivable_net / revenue | | verified_from_bytes |
| inventory_to_revenue | FY2025 | | | | | typed_absence_verified (missing_dependency) |
| current_ratio | 2025-12-31 | 2.005333592875565720959657404253248 (formula) | | current_assets / current_liabilities | | verified_from_bytes |

## 5. Gold corrections (R-G-2, this lane)

Nine View B rows carry byte re-read evidence. For each row the r2 `code: missing_standard_fact` is corrected to `disallowed_dimension`, `r1_code: MISSING_CONCEPT` to `NOT_EVALUABLE_DIMENSION`, the `detail` is restated to the dimension-refusal wording, and `axes_seen` is added as a sorted list of axis names observed on every matching ix:nonFraction / ix:nonNumeric fact. No r2 value or concept was changed. Full evidence: `tests/fixtures/fundamental_forensics/g_pack/0001652044/pack_manifest.json` entries where `ruling = R-G-2`.

### 5.1 common_shares_outstanding (cover-page instants)

Concepts searched: `dei:EntityCommonStockSharesOutstanding`. Searched accessions per the r2 row: `0001652044-26-000071`, `0001652044-26-000048`, `0001652044-26-000018`, `0001652044-25-000014`.

| period_key | axes_seen | dimension_free_fact_found | n_contexts | member_file (latest-bytes hit) | cite |
|---|---|---|---|---|---|
| instant 2025-01-28 | us-gaap:StatementClassOfStockAxis | false | 3 | goog-20241231.htm (0001652044-25-000014) | c-5 CommonClassAMember @ 205543; c-6 CommonClassBMember @ 205793; c-7 CapitalClassCMember @ 206016 |
| instant 2026-01-28 | us-gaap:StatementClassOfStockAxis | false | 3 | goog-20251231.htm (0001652044-26-000018) | c-16 CommonClassAMember @ 265642; c-17 CommonClassBMember @ 265893; c-18 CapitalClassCMember @ 266117 |
| instant 2026-04-22 | us-gaap:StatementClassOfStockAxis | false | 3 | goog-20260331.htm (0001652044-26-000048) | c-7 CommonClassAMember @ 209304; c-8 CommonClassBMember @ 209555; c-9 CapitalClassCMember @ 209779 |

Statement per row: **no dimension-free fact exists in any searched accession**. The period-2025-01-28 row's only hits sit in the comparable 10-K (0001652044-25-000014) because that accession's cover page covers 2025-01-28; the 0001652044-26-000018 accession's cover covers 2026-01-28 and the 0001652044-26-000048 10-Q cover covers 2026-04-22. The other two accessions return zero hits for the respective period. Every fact observed sits on `us-gaap:StatementClassOfStockAxis` (G0-c per-class axis).

### 5.2 operating_expenses (durations)

Concepts searched: `us-gaap:OperatingExpenses`. Searched accessions: same four admitted packages.

| period_key | axes_seen | dimension_free_fact_found | n_contexts |
|---|---|---|---|
| duration 2022-01-01..2022-12-31 | us-gaap:StatementBusinessSegmentsAxis | false | 4 |
| duration 2023-01-01..2023-12-31 | us-gaap:StatementBusinessSegmentsAxis | false | 4 |
| duration 2024-01-01..2024-12-31 | us-gaap:StatementBusinessSegmentsAxis | false | 4 |
| duration 2025-01-01..2025-03-31 (Q1 FY2025) | us-gaap:StatementBusinessSegmentsAxis | false | 2 |
| duration 2025-01-01..2025-12-31 (FY2025) | us-gaap:StatementBusinessSegmentsAxis | false | 2 |
| duration 2026-01-01..2026-03-31 (Q1 FY2026) | us-gaap:StatementBusinessSegmentsAxis | false | 2 |

Statement per row: **no dimension-free fact exists in any searched accession**. Every OperatingExpenses fact observed across the four packages sits on `us-gaap:StatementBusinessSegmentsAxis` (the G0-c segment axis already allowed for revenue / operating_income_loss). No new axis is added for `operating_expenses` (E3 ruling). Full context list per row in `pack_manifest.json` `gold_corrections[].evidence.byte_reread.contexts[]`.

### 5.3 Scanned accessions and the tool

The byte re-read used only the staged primary iXBRL member (`goog-YYYYMMDD.htm`) of every searched accession under `~/lanes/in/orch-g/stage/fif-gsrc/0001652044/<accession>/members/`. The scanner is `~/lanes/out/orch-g/fif-g-a-googl-20261019b/byte_reread.py` — stdlib `re` over the raw bytes (no `engine/`, `collectors/`, or `app/` import, per the packet). It builds a contextRef map from `<xbrli:context>` blocks (period from `<xbrli:instant>` or `<xbrli:startDate>`/`<xbrli:endDate>`; members from `<xbrldi:explicitMember>` / `<xbrldi:typedMember>`), then for each `<ix:nonFraction>` / `<ix:nonNumeric>` tag with `name` ∈ concepts_searched and matching context period, records `{accession, member_file, contextRef, members, byte_offset}`. `axes_seen` is the sorted union of axis names observed; `dimension_free_fact_found` is true only if at least one hit has an empty `members` map. For all 9 rows it was `false`.

## 6. Typed absences (counts from gold_cells.jsonl)

3213 total cells (1938 View A + 1275 View B): not_applicable_verified=1638, typed_absence_verified=949, verified_from_bytes=626.

Typed absence code breakdown (verified_from_bytes excluded):

| code | count | reason (verbatim where the row carries one) |
|---|---|---|
| missing_standard_fact | 641 | as-filed zero-hit in <accession>: no dimension-free fact for any of the 1 mapped concepts this period (r1 MISSING_CONCEPT) |
| missing_dependency | 272 | never derived from a partial input set (E2); named missing input follows (short_term_debt for total_debt; gross_profit for gross_margin; inventory_net for inventory_to_revenue; total_debt for cash_to_total_debt and debt_to_equity) |
| disallowed_dimension | 36 | facts exist only on dimensioned contexts in this package; G0-c allowed axes do not apply to the headline cell (E3 / R-G-2) |

## 7. ERRATA-1 handling

- E1 (BAC alias): not applicable to GOOGL.
- E2 (total_debt never derived from a partial input set): applied — `total_debt` rows are `missing_dependency` naming `short_term_debt`; resolved component keeps its own label (long_term_debt via LongTermDebtNoncurrent). 8 `total_debt` View B periods + 2 View A instants carry this code.
- E3 (GOOGL operating_expenses = NOT_EVALUABLE_DIMENSION, no new axis): applied — every View A duration cell of operating_expenses across the 4 admitted packages carries `disallowed_dimension`. The six View B duration rows that r2 recorded as `missing_standard_fact` are corrected to `disallowed_dimension` under R-G-2 (§5.2). G0-c's axis list is closed; no new axis is added for operating_expenses.
- E4 (CAT scope labels): not applicable to GOOGL.
- E5 (census values are candidate output only, never gold): honored — T11 gold is byte-derived only.
- E6 (admission dependencies): G1 SNOW and G4 GOOGL already meet the R5 bar (2 10-K + 2 10-Q admitted each); the G4 manifest lists the four ADMITTED accessions ordered by `source_accepted_at` desc.
- E7 (pre-A0): this lane produced three commits under the G0 BUILD clause; no draft is armed.

## 8. Pins (rows)

Six typed pin objects are recorded in `pack_manifest.pins[]`. All byte evidence cites `goog-20251231.htm` of accession 0001652044-26-000018 (sha256 `34a5db240851fab80a2ed1bf7d01b5c9c648b1290148ba4030acf2da89071172`, equal to the g_src manifest digest) unless noted otherwise. `byte_offset` is the offset of the `<ix:nonFraction …>` opening tag.

| pin | ruling | evidence |
|---|---|---|
| dual_listing | spec §3 dual_listing; frozen spec §7 Identity (A14/A32) | listing_keys `US-XNAS-GOOG` (manifest `entity_id` ISS:US-XNAS-GOOG) and `US-XNAS-GOOGL` (manifest `listing_key`), identical on every committed g_src manifest; both listings resolve to the same four ADMITTED capture_index rows |
| errata_absence E3 (operating_expenses) | ERRATA E3; frozen spec §2 G0-c | code `disallowed_dimension` on every View A duration cell across the four admitted packages. Dimensioned-only fact cited: us-gaap:OperatingExpenses, contextRef `c-74` (`us-gaap:StatementBusinessSegmentsAxis` / `goog:GoogleServicesMember`, FY2025), offset 2390206, raw `158,193`, value 158193000000 |
| errata_absence E2 (total_debt) | ERRATA E2; spec §2 | total_debt 2025-12-31 = missing_dependency naming short_term_debt; resolved component under its own label: us-gaap:LongTermDebtNoncurrent, contextRef `c-20`, offset 877723, raw `46,547`, value 46547000000 |
| errata_absence (gross_profit) | frozen spec §7 + §0 gate 5 | missing_standard_fact; `us-gaap:GrossProfit` occurrence count per admitted package: 0 facts and 0 raw substrings in every primary member (sha256 34a5db24…, e7a92122…, d9046d6f…, 2f35fe23…); no derivation |
| decimals_precision (cost_of_revenue) | spec §3 decimals_precision; frozen spec §7 COGS verify CLOSED | us-gaap:CostOfRevenue FY2025: value_exact 162535000000, decimals -6, scale 6, sign null, unitRef usd, contextRef `c-1`, offset 909036, raw `162,535` |
| segment_as_filed (FY2025 revenue) | frozen spec §2 G0-c A31 no-sum fence + R6 | segments Google Services 342721000000 (c-74 @ 2364193), Google Cloud 58705000000 (c-77 @ 2366185), Other Bets 1537000000 (c-80 @ 2368172); consolidated = filing's own undimensioned us-gaap:Revenues `c-1` 402836000000 @ 2372761; reconciling Hedging gains (losses) us-gaap:RevenueNotFromContractWithCustomer `c-1` sign −, offset 2370075, raw `127`, value −127000000. Sum check only: 342721 + 58705 + 1537 − 127 = 402836 (millions); consolidated cell never served as a sum |

The dual_listing pin's `key_source` is the committed issuer-group data (`config/issuer_group_allowlist.yml` groups[cik 0001652044].members and `data/reference/_receipt.json` multi_security_groups[issuer_id ISS:US-XNAS-GOOG].security_ids). The two manifest listing_keys (`US-XNAS-GOOG`, `US-XNAS-GOOGL`) are a subset of that issuer-group data.

## 9. Findings (hand-derived for the packet basis view)

Basis (from the r2 packet draft and adopted unchanged by the build): view `as_filed`, source_accession `0001652044-26-000071` (newest admitted 10-Q, knowledge_time 2026-07-23T01:15:54.000Z), 663 gold cells. Rules read as data: `engine/fundamental_forensics/detectors.py`, `engine/fundamental_forensics/normalize.py`, `config/fundamental_forensics.yml`.

Applicability: SIC 7370 → `software` (detectors.py:70-71); `software` is in every DETECTOR_APPLICABILITY set (detectors.py:27-33), so no detector is class-gated for GOOGL.

Vintage structure: the basis package's registry-metric facts sit at period ends 2025-06-30, 2025-12-31 and 2026-06-30. Gap arithmetic: 2025-06-30→2025-12-31 = 184 days; 2025-12-31→2026-06-30 = 181 days; both below MIN_PERIOD_GAP_DAYS=300, and the package contains no 12-month duration, so no consecutive-annual pair (or triple) exists. The two-period window is (2025-12-31, 2026-06-30); the three-period window is (2025-06-30, 2025-12-31, 2026-06-30).

| detector | state | missing inputs (detectors.py:141 vocabulary) |
|---|---|---|
| accruals_trending_up | not_evaluable | assets@2025-06-30; net_income@2025-12-31; operating_cash_flow@2025-12-31; consecutive_annual_periods |
| capital_intensity_rising | not_evaluable | revenue@2025-12-31; capital_expenditures@2025-12-31; operating_income@2025-12-31; consecutive_annual_periods |
| inventory_build | not_evaluable | revenue@2025-12-31; consecutive_annual_periods |
| margin_compression_despite_revenue_growth | not_evaluable | revenue@2025-12-31; gross_profit@2025-12-31; gross_profit@2026-06-30; consecutive_annual_periods |
| receivables_stretch | not_evaluable | revenue@2025-12-31; consecutive_annual_periods |

Coverage counts: findings_triggered=0, findings_clear=0, findings_not_evaluable=5.

## 10. Projection note (RULINGS.md assembly decisions)

`gold_cells.jsonl` is a lossless projection of r2 `gold_facts.jsonl` produced by `gold_assemble.py build` and checked by `gold_assemble.py check`. It removes only the verbose duplicates per row — `concepts_searched`, `catalog_codes`, `occurrences`, `dependency_cells`, and the per-row header fields `schema`/`issuer`/`cik` — and sorts by (view, source_accession, metric_id, period_key). Every other field, every value, and the row count are carried byte-equal except the exact (row, field) pairs listed in `gold_corrections`. For GOOGL those pairs are 9 row_keys × 4 fields (code, r1_code, detail, axes_seen) = 36 corrections; no r2 value or concept changed. `trace` is reduced to the seven spec fields plus scale/sign/format where r2 has them; formula cells keep `formula_rule_id` and the dependency list r2 records. The packet and run drafts drop the `-draft-r2` schema suffix and replace every kernel-minted hash/id placeholder with `kernel_minted_not_gold`; identity digests are minted by the kernel and are never gold.

## 11. Kernel defect records (R-G-1)

89 entries in `tests/fixtures/fundamental_forensics/g_pack/0001652044/pack_manifest.json` `defects[]` (after commit 3). Cluster counts:

| cluster | ruling | count | comparison | description |
|---|---|---|---|---|
| C1_viewB_unlinked_vintages | R-G-1 | 66 | value | gold = a typed value at the period; kernel = `not_evaluable` / `UNMAPPED_KERNEL_REASON:unlinked source vintages require an explicit typed revision lineage` (query.py:5952-5982; raw_ledger.py:1212-1233) |
| C2_viewB_formula_unlinked_cascade | R-G-1 | 20 | code | gold = `missing_dependency`; kernel = `incompatible_dependencies` cascading from a C1 dependency cell |
| C3_viewB_equal_value_vintage_attribution | R-G-1 | 2 | value | value disagreement; not a formula |
| C9_viewB_cross_package_formula_basis | R-G-1 | 1 | value | cross-package formula basis mismatch |

The `record` shape per the packet is: `{ruling, cluster, kr_label, category, accession, concept, context, filed_value, filed_location, formula, gold, kernel_output, kernel_observation, repro}`. Repro per entry: `tests/test_fif_g_pack_kernel.py::test_kernel_cells_match_gold_cells[0001652044-latest_known_as_of-union]` with `FIF_GSRC_STAGE_ROOT=<stage root holding the admitted package bytes>`.

**Sentence (per packet): gold was never edited to match the kernel.** Every entry compares the unchanged r2 typed value (or `missing_dependency` / `disallowed_dimension` code) against the kernel output and records the comparison; the `record.gold` block is byte-equivalent to the gold_cells row at the join key. The kernel test (commit 1, owned by the kernel lane) applies each entry as `xfail(strict=True, reason=<defect id>)` for exactly the affected comparison group; a stale or unexpected entry fails the test.

## 12. Gaps

- The kernel-minted hash/id placeholders in the two expected JSONs become `kernel_minted_not_gold` under identity keys only; identity digests are minted by the kernel in the build lane and are never gold.
- finding_states are now hand-derived (§9): all five detectors `not_evaluable` with named missing inputs for the packet basis view; r2's placeholder note is superseded.
- Browser evidence (packet + page at dark/light × EN/ZH × 1440/390, typed absences visible) stays pending A0 acceptance and live publish (spec §0 gate 6); this lane produced no UI and no live proof.
- fiscal_quarter / fiscal_year / calendar_kind in period objects stay null/unknown (AAPL witness shape); the fiscal label encodes the issuer FYE.
- View B formula cells carry `dep_source_accessions` instead of a single `source_accession` (inputs may come from several packages under the r1 method).
- The 9 R-G-2 View B rows carry no `trace` field (typed absence); no dimension-free fact exists to cite.
- The byte re-read scanned only the primary iXBRL member (`goog-YYYYMMDD.htm`) of each searched accession; if a future lane wants the `_lab.xml` / `_cal.xml` / `_def.xml` / `_pre.xml` artifacts they are not iXBRL-bearing facts and carry no extra ground truth for these rows.