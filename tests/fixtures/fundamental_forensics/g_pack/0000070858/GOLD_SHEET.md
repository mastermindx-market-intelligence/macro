# BAC gold sheet — G3 pack (lane fif-g-a-bac-20261019b, 2026-10-19)

- Issuer: BANK OF AMERICA CORP /DE/; CIK 0000070858; legal_name `BANK OF AMERICA CORP /DE/`; entity_id `ISS:US-XNYS-BAC`; security_ids `["SEC:US-XNYS-BAC"]`; listing_keys `["US-XNYS-BAC"]`; issuer_class `bank` (SIC 6021 -> bank, coverage `config/fundamental_forensics/coverage/five_issuer_v1.json`).
- Base commit: `cbcf823d4045ff640e63a2a0531a1a8155f5ae02` (G0 branch head, `lane/fif-g-a-bac-20261019b`).
- Gold source: `fif-ggold-20261013/r2/BAC/` (lane `fif-ggold-20261013/r2`); every file's sha256 was re-checked against `FREEZE.txt` before use; ALL matches.
- `attested: false`; `historical_attestation: unavailable_until_d2_admission` (spec §0 gate 8).
- The ORCH-G kernel-comparison rulings (R-G-1 .. R-G-6, seat 96dc937a, 2026-10-19) are **distinct** from the gold-engine rulings (R-G1 Decimal contract, R-G2 period alignment, R-G3 knowledge time / the two views). Every gold-sheet sentence that uses both says so once, here.

## 1. Source accessions (packet basis = `as_filed` of 0000070858-26-000394)

| form | accession | period_of_report | knowledge_time |
|---|---|---|---|
| 10-K (newest) | 0000070858-26-000157 | 2025-12-31 | 2026-02-26T03:01:44.000Z |
| 10-K (comparable) | 0000070858-25-000139 | 2024-12-31 | 2025-02-26T03:07:15.000Z |
| 10-Q (newest, packet basis) | 0000070858-26-000394 | 2026-06-30 | 2026-08-01T00:44:20.000Z |
| 10-Q (second) | 0000070858-26-000249 | 2026-03-31 | 2026-05-02T00:39:01.000Z |

`admitted_accessions` is the same set (newest first). `packet_basis.view = as_filed`, `source_accession = 0000070858-26-000394`, `knowledge_time = 2026-08-01T00:44:20.000Z`, `knowledge_time_source = sec_submissions_witness.json:acceptanceDateTime` (from `pack_manifest.json`).

## 2. Gold corrections (R-G-2, R-G-4)

The pack carries 283 `gold_corrections` entries (applied by `apply_fills.py` for R-G-2; pre-baked into `0000070858_pins.json` for R-G-4). No R-G-5 row in BAC (R-G-5 is SNOW-only). Gold values, concepts, and contextRefs are unchanged; only fields derived from the byte re-read are touched.

### 2.1 R-G-2 (View B rows; every fact for the mapped concept in the period sits on a dimensioned context)

7 corrected rows, each `view = latest_known_as_of` with `source_accession = null` (View B is the latest admitted package reporting the cell, not a single package). For each row, the field-level changes are: `code: missing_standard_fact -> disallowed_dimension` and `r1_code: MISSING_CONCEPT -> NOT_EVALUABLE_DIMENSION`. Consequence: a formula row whose `missing_inputs` named the corrected dependency gets that entry re-coded; the formula itself stays `missing_dependency` (E2). `axes_seen` lists the prefix:Axis names observed on every context that carries the mapped concept in the period, across all 4 searched accessions (`0000070858-26-000394`, `0000070858-26-000249`, `0000070858-26-000157`, `0000070858-25-000139`).

| metric | period | searched concept | axes_seen | context evidence |
|---|---|---|---|---|
| cash_and_cash_equivalents | instant 2023-12-31 | us-gaap:CashAndCashEquivalentsAtCarryingValue | `srt:ConsolidatedEntitiesAxis` | 0000070858-25-000139 / bac-20241231.htm / c-N (consolidated-entity member); no dimension-free fact in any searched accession |
| cash_and_cash_equivalents | instant 2024-12-31 | us-gaap:CashAndCashEquivalentsAtCarryingValue | `srt:ConsolidatedEntitiesAxis` | 0000070858-26-000157 / bac-20251231.htm / c-N + 0000070858-25-000139 / bac-20241231.htm / c-N (consolidated-entity members); no dimension-free fact |
| cash_and_cash_equivalents | instant 2025-12-31 | us-gaap:CashAndCashEquivalentsAtCarryingValue | `srt:ConsolidatedEntitiesAxis` | 0000070858-26-000157 / bac-20251231.htm / c-N (consolidated-entity member); no dimension-free fact |
| retained_earnings_accumulated_deficit | instant 2022-12-31 | us-gaap:RetainedEarningsAccumulatedDeficit | `srt:RestatementAxis` | 0000070858-25-000139 / bac-20241231.htm / c-N (restatement member); no dimension-free fact |
| short_term_debt | instant 2023-12-31 | us-gaap:ShortTermBorrowings | `srt:ConsolidatedEntitiesAxis`, `us-gaap:FinancialInstrumentAxis` | 4 facts on dimensioned contexts (0000070858-25-000139); no dimension-free fact |
| short_term_debt | instant 2024-12-31 | us-gaap:ShortTermBorrowings | `srt:ConsolidatedEntitiesAxis`, `us-gaap:FinancialInstrumentAxis` | 12 facts on dimensioned contexts (0000070858-26-000157 + 0000070858-25-000139); no dimension-free fact |
| short_term_debt | instant 2026-03-31 | us-gaap:ShortTermBorrowings | `srt:ConsolidatedEntitiesAxis`, `us-gaap:FinancialInstrumentAxis` | 4 facts on dimensioned contexts (0000070858-26-000249); no dimension-free fact |

Source value -> corrected value: `code: missing_standard_fact -> disallowed_dimension`; `r1_code: MISSING_CONCEPT -> NOT_EVALUABLE_DIMENSION`; `axes_seen: LANE_FILL -> [sorted union of the observed axes]`. Byte evidence: every fact the byte re-read found for `concept + searched_accession + period_key` is recorded in `fills.json` as `{"accession", "member_file", "contextRef", "members": {axis: member}, "byte_offset"}`. `dimension_free_fact_found` is `false` on every row (so the row is not escalated; the typed absence is the visible answer).

### 2.2 R-G-4 (BAC class closure; `inventory_to_revenue` only)

252 corrected rows (1 metric × every in-window cell of both views × the rows whose r2 code was `missing_dependency` and whose catalog applicability lists `excluded_classes: [bank]`). Catalog proof: `config/fundamental_forensics/metrics/v1/metric_catalog.yaml:527-536` for `inventory_to_revenue` `applicability.issuer_class_basis: sic, excluded_classes: [bank]`; coverage `config/fundamental_forensics/coverage/five_issuer_v1.json` `issuer cik 70858 issuer_class bank, sic 6021`. Source value -> corrected value: `code: missing_dependency -> NOT_APPLICABLE`; `verification_state: typed_absence_verified -> not_applicable_verified`; `r1_code MISSING_DEPENDENCY` removed; `detail`, `missing_inputs`, `formula_rule_id`, `expression`, `dependencies`, `dependency_period_alignment`, `dep_periods` removed; `reason: not_applicable_class: bank class policy G0-b Tier 1 / Tier 2 (R2)` added; `dep_source_accessions` removed. Byte evidence: 0 facts for `us-gaap:InventoryNet` in every package, dimension-free or dimensioned; the formula was never evaluated because the metric is refused by the catalog policy before `qualify_metric` runs.

Other metrics whose catalog `excluded_classes: [bank]` matches BAC's class (`cost_of_revenue`, `gross_profit`, `gross_margin`, `operating_expenses`, `operating_income_loss`, `inventory_net`, `current_assets`, `current_liabilities`, `working_capital`, `current_ratio`, `cash_to_total_debt`, `net_debt`, `free_cash_flow`, `debt_to_equity`, `receivables_to_revenue`) are NOT_APPLICABLE on every in-window cell from r2 directly (no R-G-4 correction needed; class gate fires before cell build). Their 240 NOT_APPLICABLE rows appear in `gold_cells.jsonl` with `code: NOT_APPLICABLE`. `inventory_to_revenue` alone needed correction because its r2 code was `missing_dependency` (a formula absence), not NOT_APPLICABLE.

## 3. Typed absences (counts by code; from `gold_cells.jsonl`)

| code | count | reason |
|---|---|---|
| outside_period_constraint | 1425 | the period is outside the package's reporting window (the cell exists in r2 but the admitted package does not file it) |
| missing_standard_fact | 511 | zero dimension-free hits for any mapped concept this period |
| NOT_APPLICABLE | 456 | catalog `excluded_classes: [bank]` refused the metric for issuer class `bank` (SIC 6021) |
| missing_dependency | 35 | a formula's required input was unresolved at the basis view (E2) |
| disallowed_dimension | 22 | R-G-2 corrections: every fact for the concept in the period sits on a dimensioned context |
| unsupported_metric | 57 | catalog rule marks the metric unsupported for the period |

`outside_period_constraint` (1425) and `unsupported_metric` (57) are unchanged from r2. `disallowed_dimension` grew from 15 (r2) to 22 (after R-G-2: 15 + 7). `NOT_APPLICABLE` grew by 22 (R-G-4 corrections flip 22 of the 35 originally `missing_dependency` `inventory_to_revenue` cells to NOT_APPLICABLE). `missing_dependency` dropped by 22 (those flipped to NOT_APPLICABLE). `missing_standard_fact` dropped by 7 (the 7 R-G-2 rows flipped to `disallowed_dimension`). No new zero, guess, or derived stand-in.

## 4. ERRATA-1 handling

| errata | handling |
|---|---|
| E1 (BAC alias candidates) | `LongTermDebt` (mapping is `LongTermDebtNoncurrent`; LongTermDebt includes current maturities), `PaymentsOfOrdinaryDividends` (mapping is `PaymentsOfDividendsCommonStock`), and `bac:TimeDepositsAndOtherShortTermInvestments` (non-catalog bac: short-term-investments concept) are NOT aliased in G. Three `errata_absence` pins carry the rule + the cited byte occurrence (R3: identity needs us-gaap element documentation verbatim). The corresponding gold cells stay `missing_standard_fact` with `r1_code: MISSING_CONCEPT` and the candidate concept under `candidate_not_aliased` with its accession. |
| E2 (half-printed leverage pairs) | `total_debt` is never derived from a partial input set. One `errata_absence` pin carries the rule. Gold cells: `missing_dependency` with `missing_inputs` naming the missing components (`short_term_debt`, `long_term_debt_current`, `long_term_debt`). A resolved component prints under its own label, never as "debt". |
| E4 (CAT scope label) | not applicable to BAC. |
| E5 (census values are candidate output, never gold) | every gold cell was re-derived from the staged filing bytes via `gold_assemble.py`; the census Q4 numbers were never copied into the gold. |
| E6 (BAC admission dependencies) | **confirmed at the G0 head**: B'2 merged + re-admission regen shows the R5 bar (4/4 BAC admitted packages parse and admit). `admission_state = admitted` (the r2 header value `blocked_until_d1x_b2_and_readmission` was the pre-G0 marker; `build_pack.py` strips it). `admission_state_basis = {errata: E6, statement: "BAC B'2 is in G0; KR-ALL re-checked it at the G0 head (4/4 BAC admitted packages parse and admit)", evidence_file: fif-g-kr-all-20261019a/e6.json, evidence_sha256: b7199c046b278602f563703aed2db1141855c7c312663f9de3d565159b733177, g0_head: cbcf823d4045ff640e63a2a0531a1a8155f5ae02}`. |

## 5. Pins (closed set; full objects in `pack_manifest.pins[]`)

6 pins. The packet basis row for `inventory_to_revenue` View B and `inventory_to_revenue` View A carry the R-G-4 corrections inline.

| type | summary | ruling |
|---|---|---|
| `not_applicable_class` | 16 metrics whose catalog `excluded_classes: [bank]` matches BAC's class; 456 cells NOT_APPLICABLE across both views | `G_PACK_FROZEN_SPEC.md §2 G0-b (Tier 1 D0-ratified five_issuer_v1.json:59-68; Tier 2 seat ruling R2) + §6 G3 Metrics; ERRATA-1 E6 context` |
| `errata_absence` (E1, `long_term_debt`) | `LongTermDebt` is not aliased to `LongTermDebtNoncurrent` (includes current maturities); the cell stays `missing_standard_fact` / `MISSING_CONCEPT` | `G_CENSUS_ERRATA.md E1 + G_PACK_BUILD_SPEC.md §2 E1` |
| `errata_absence` (E1, `cash_dividends_paid`) | `PaymentsOfOrdinaryDividends` is not aliased to `PaymentsOfDividendsCommonStock`; the cell stays typed absence | `G_CENSUS_ERRATA.md E1 + G_PACK_BUILD_SPEC.md §2 E1` |
| `errata_absence` (E1, `short_term_investments`) | `bac:TimeDepositsAndOtherShortTermInvestments` is a non-catalog concept with no us-gaap element documentation; the cell stays typed absence | `G_CENSUS_ERRATA.md E1 + G_PACK_BUILD_SPEC.md §2 E1` |
| `errata_absence` (E2, `total_debt`) | `total_debt` is `missing_dependency` (E2); the component cells print under their own labels | `G_CENSUS_ERRATA.md E2 + G_PACK_BUILD_SPEC.md §2 E2` |
| `decimals_precision` | `bac:FinancingReceivableExcludingAccruedInterestAndOffBalanceSheetLiabilityCreditLossProvisionReversal` 5,675 @ `c-1` byte_offset 5082333 of `bac-20251231.htm` of 0000070858-26-000157 (sha256 `aa035c1ba6e8ae99223ceb2afcb762670264665194e33bb8415874bef7985934`); decimals -6, scale 6; the provision composes 5,595 (loan/lease) + 80 (unfunded commitments) = 5,675 (a cross-read; the total is the filing's own tagged fact and is never computed by us) | `G_PACK_FROZEN_SPEC.md §6 G3 Metrics + fif-g3-bac.md §3.1/§8.3` |

## 6. Findings (hand-derived detector states for the packet basis view)

Packet basis: `as_filed` of `0000070858-26-000394` (newest 10-Q), knowledge_time 2026-08-01T00:44:20.000Z. Issuer class `bank` (SIC 6021).

| detector | state | missing input named | rule (path:line) | threshold (path:line) | required inputs |
|---|---|---|---|---|---|
| margin_compression_despite_revenue_growth | not_evaluable | not_applicable_for_issuer_class | detectors.py:27-33 (applicable: industrial/software); gate :481-496 | min_revenue_growth_pp "3" (yml:61-65; read :307) | revenue, gross_profit |
| receivables_stretch | not_evaluable | not_applicable_for_issuer_class | detectors.py:27-33; gate :481-496 | growth_gap_pp "10" (yml:66-70; read :334) | revenue, accounts_receivable |
| inventory_build | not_evaluable | not_applicable_for_issuer_class | detectors.py:27-33; gate :481-496 | growth_gap_pp "15" (yml:71-75; read :334) | revenue, inventory |
| capital_intensity_rising | not_evaluable | not_applicable_for_issuer_class | detectors.py:27-33; gate :481-496 | growth_gap_pp "10" (yml:76-80; read :355) | revenue, capital_expenditures, operating_income |
| accruals_trending_up | not_evaluable | not_applicable_for_issuer_class | detectors.py:32 (all classes minus bank/insurance); gate :481-496 | min_three_period_increase "0.03" (yml:81-85; read :435) | net_income, operating_cash_flow, assets (3 consecutive annual periods, :399-404) |

Method: the class gate at detectors.py:481 fires before input collection; bank is not in the detector's applicable classes; emit `not_evaluable` with `missing_inputs=("not_applicable_for_issuer_class",)` and `limitations=("issuer_class:bank",)` (emit :491-495); no threshold arithmetic is run. Bank gating is pinned by `tests/test_fundamental_forensics_detector_applicability.py:153-164` (4 industrial detectors) and `:166-171` (accruals). Counts: triggered 0 / clear 0 / not_evaluable 5.

## 7. Projection note (`gold_cells.jsonl`)

2907 rows; one JSON object per line; sorted by `(view, source_accession or "", metric_id, period_key)`. Lossless projection of r2 `gold_facts.jsonl` except for two verbose duplicates dropped: `concepts_searched` and `catalog_codes` (per ORCH-G assembly decision). Row count equals r2's; values are never changed; corrections match the 283 `gold_corrections` listed in §2. The byte proof for every valued row's accession / member_file / member_sha256 / concept / contextRef / unitRef / decimals / scale / sign / format sits in the row's `trace`. Identity digests (e.g. `canonical_sha256`, `run_id`) are replaced by the string `kernel_minted_not_gold`; they are minted by the kernel and are never gold.

## 8. Kernel defect records (`pack_manifest.defects[]`, applied by `apply_defects.py` after commit 2)

63 defect entries, all R-G-1 or R-G-3 (no R-G-2 BAC defects). Cluster counts:

| cluster | ruling | count | comparison category |
|---|---|---|---|
| C1_viewB_unlinked_vintages | R-G-1 | 47 | value (kernel refuses unlinked source vintages per `engine/fundamental_forensics/query.py:5952-5982` + `raw_ledger.py:1212-1233`) |
| C4d_source_not_numeric | R-G-1 | 3 | value (filed fact present but kernel refactored to non-numeric stream) |
| C4a_formula_dimension_cascade | R-G-3 | 13 | code (gold keeps `missing_dependency` per E2; the kernel's different output is recorded as a defect entry of comparison type `code`) |

Shape: `{"id": "D-C1-NNNN" or "D-C4a-NNNN" ..., "row_keys": [{view, source_accession, metric_id, period_key}, ...], "comparison": "value"|"code", "record": {ruling, cluster, kr_label, category, accession, concept, context: {contextRef, unitRef, decimals, scale, dimensioned, nil}, filed_value, filed_location: {accession, member_file, member_sha256, byte_offset, raw_text}, formula, gold: {value_exact, code, source_accession}, kernel_output: {state, value_exact, kernel_code, reason, provenance_accession}, kernel_observation: {kernel, cite}, repro: {test, env}}}`. The repro for every entry is the kernel test node (`tests/test_fif_g_pack_kernel.py::test_kernel_cells_match_gold_cells[<cik>-latest_known_as_of-union]`) under `FIF_GSRC_STAGE_ROOT=<stage root holding the admitted package bytes>`. The kernel test turns each entry into `xfail(strict=True, reason=<defect id>)` for exactly the affected comparison.

`gold was never edited to match the kernel`. The defect entries record the difference; the test xfails; no gold value, code, pin or defect entry was changed to make a test pass.

## 9. Gaps

- Browser evidence (packet rendered on the FIF page at dark/light × EN/ZH × 1440/390, typed absences visible) is pending A0 and live publish; this offline lane produces no page.
- Identity digests are minted by the kernel and not committed; `kernel_minted_not_gold` is the only honest placeholder.
- View B `fiscal_quarter` / `fiscal_year` / `calendar_kind` stay null/unknown (AAPL witness shape); the fiscal label encodes the issuer FYE.
- CET1 / LCR / NSFR / HQLA: 0 dimension-free (consolidated-surface) tags in every admitted package; not_in_xbrl cells are absent (no served row); not part of `gold_cells.jsonl`.
- Capital-ratio tags exist only on dimensioned contexts (Standardized/Advanced approach or ParentCompany/Subsidiaries axes); same conclusion as the r2 prose records.
- A stale or unexpected defect entry in `defects_0000070858.json` would fail the kernel test with the entry id; none observed after `apply_defects.py` ran.