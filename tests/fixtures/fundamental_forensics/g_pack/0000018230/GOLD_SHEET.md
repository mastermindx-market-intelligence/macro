# CAT gold sheet — G2 pack (assembly lane `fif-g-a-cat-20261019c`)

- Issuer: Caterpillar Inc.; CIK 0000018230; ticker CAT (US-XNYS-CAT).
- Base commit: `cbcf823d4045ff640e63a2a0531a1a8155f5ae02` (G0 branch head).
- Gold source: `fif-g-gr-cat-20261019a/r3` (`gold_source_r3.json`); the r3 rebuild that re-attributed the 0000018230-25-000008 periods C6 fix. **Do not use the r2 CAT gold.**
- `attested: false`; `historical_attestation: unavailable_until_d2_admission` (spec §0 gate 8).
- The ORCH-G kernel-comparison rulings R-G-1..R-G-6 (this lane's packet + RULINGS.md) are distinct from the earlier gold-engine rulings R-G1 (Decimal contract), R-G2 (period alignment) and R-G3 (knowledge time + two views) that the r2/r3 sheets cite.
- Packet basis: `as_filed` of 0000018230-26-000046 (newest 10-Q); knowledge_time 2026-08-05T12:43:40.000Z from `sec_submissions_witness.json:acceptanceDateTime`.
- Gold derives from the staged retained filing bytes only (T11 / ERRATA E5); this lane re-opened every relevant iXBRL member, re-computed its sha256, and re-read every correction below from the bytes with an stdlib inline-XBRL scanner (no `engine/` or `collectors/` imports). Kernel, census and renderer outputs were never used.

## 1. Accessions (admitted set; knowledge time cited per accession)

The pack's `admitted_accessions` and the `packet_basis` row below are copied from `pack_manifest.json` (newest first by `source_accepted_at`):

| form | accession | period_of_report | knowledge_time |
|---|---|---|---|
| 10-Q | 0000018230-26-000046 | 2026-06-30 | 2026-08-05T12:43:40.000Z |
| 10-Q | 0000018230-26-000021 | 2026-03-31 | 2026-05-06T15:08:09.000Z |
| 10-K | 0000018230-26-000008 | 2025-12-31 | 2026-02-13T15:18:27.000Z |
| 10-K | 0000018230-25-000008 | 2024-12-31 | 2025-02-14T14:36:30.000Z |

Capture-only (not admitted, R5): 0000018230-25-000040 (10-Q, 2025-06-30, 2025-08-06).

## 2. Views (R-G3)

- **VIEW A `as_filed`**: one cell set per admitted package, built only from that package's own ix facts (comparative columns included). **1428 cells across 4 packages.**
  - 0000018230-26-000008: 357 cells — not_applicable_verified=182, typed_absence_verified=84, verified_from_bytes=91
  - 0000018230-25-000008: 408 cells — not_applicable_verified=208, typed_absence_verified=109, verified_from_bytes=91
  - 0000018230-26-000046: 408 cells — not_applicable_verified=208, typed_absence_verified=113, verified_from_bytes=87
  - 0000018230-26-000021: 255 cells — not_applicable_verified=130, typed_absence_verified=60, verified_from_bytes=65
- **VIEW B `latest_known_as_of`**: for each (metric, period) the value from the newest admitted package reporting it, ordered by knowledge_time (r1 method). **969 cells** — not_applicable_verified=494, typed_absence_verified=223, verified_from_bytes=252. Informational only; never cross-checked against the census.
- knowledge_time order: -26-000046 > -26-000021 > -26-000008 > -25-000008.

## 3. Gold corrections (this lane; machine form in `pack_manifest.json:gold_corrections`)

Every entry below is an R-G-2 correction: a View B row coded `missing_standard_fact` whose mapped concept exists only on dimensioned contexts in the searched accessions. Each entry is confirmed by an independent byte re-read of the iXBRL members of the searched accessions; the byte evidence lists every accessed member's context that carries a mapped concept for the period, its contextRef, axis=member pairs, and byte_offset of the fact's opening tag, and states that no dimension-free fact exists. The headline cell is a dimension refusal, not a missing concept.

### 3.1 View B `common_stock_repurchases` Q1 FY2024 (period ['duration', '2024-01-01', '2024-03-31'])

| field | r2 value (g_source) | corrected value |
|---|---|---|
| `code` | `missing_standard_fact` | `disallowed_dimension` |
| `r1_code` | `MISSING_CONCEPT` | `NOT_EVALUABLE_DIMENSION` |
| `detail` | "zero-hit search across every admitted package: no dimension-free fact for any mapped concept of common_stock_repurchases for this period (concepts searched: us-gaap:PaymentsForRepurchaseOfCommonStock)" | "facts exist only on dimensioned contexts in this package; G0-c allowed axes do not apply to the headline cell" |
| `axes_seen` | (absent) | `["srt:ShareRepurchaseProgramAxis"]` |

Byte evidence (`accession=0000018230-25-000008`, `member_file=cat-20241231.htm`, `contextRef=c-674`, `members={"srt:ShareRepurchaseProgramAxis": "cat:ASRAgreementsMember"}`): the same contextRef holds 2 ix:nonFraction facts named `us-gaap:PaymentsForRepurchaseOfCommonStock` at byte_offset `5065365` and `5065594` (decimals `-7`, scale `9`, unit `usd`, format `ixt:num-dot-decimal`). No dimension-free fact exists in this period across the searched accessions (26-000046, 26-000021, 26-000008, 25-000008). The View A twin in `0000018230-25-000008` is `disallowed_dimension` and stays as such; the headline (View B) correction flows from that as_filed outcome.

### 3.2 View B `common_stock_repurchases` Q2 FY2024 (period ['duration', '2024-04-01', '2024-06-30'])

| field | r2 value (g_source) | corrected value |
|---|---|---|
| `code` | `missing_standard_fact` | `disallowed_dimension` |
| `r1_code` | `MISSING_CONCEPT` | `NOT_EVALUABLE_DIMENSION` |
| `detail` | "zero-hit search across every admitted package: no dimension-free fact for any mapped concept of common_stock_repurchases for this period (concepts searched: us-gaap:PaymentsForRepurchaseOfCommonStock)" | "facts exist only on dimensioned contexts in this package; G0-c allowed axes do not apply to the headline cell" |
| `axes_seen` | (absent) | `["srt:ShareRepurchaseProgramAxis"]` |

Byte evidence (`accession=0000018230-25-000008`, `member_file=cat-20241231.htm`, `contextRef=c-675`, `members={"srt:ShareRepurchaseProgramAxis": "cat:ASRAgreementsMember"}`): the same contextRef holds 2 ix:nonFraction facts named `us-gaap:PaymentsForRepurchaseOfCommonStock` at byte_offset `5066361` and `5066590` (decimals `-7`, scale `9`, unit `usd`, format `ixt:num-dot-decimal`). No dimension-free fact exists in this period across the searched accessions. View A twin in `0000018230-25-000008` is `disallowed_dimension`.

### 3.3 View B `short_term_debt` 2026-03-31 (period ['instant', '2026-03-31'])

| field | r2 value (g_source) | corrected value |
|---|---|---|
| `code` | `missing_standard_fact` | `disallowed_dimension` |
| `r1_code` | `MISSING_CONCEPT` | `NOT_EVALUABLE_DIMENSION` |
| `detail` | "zero-hit search across every admitted package: no dimension-free fact for any mapped concept of short_term_debt for this period (concepts searched: us-gaap:ShortTermBorrowings)" | "facts exist only on dimensioned contexts in this package; G0-c allowed axes do not apply to the headline cell" |
| `axes_seen` | (absent) | `["srt:ProductOrServiceAxis"]` |

Byte evidence (`accession=0000018230-26-000021`, `member_file=cat-20260331.htm`, `contextRef=c-13`, `members={"srt:ProductOrServiceAxis": "cat:FinancialProductsMember"}`): 1 ix:nonFraction fact named `us-gaap:ShortTermBorrowings` (unit `usd`, decimals `-6`, scale `6`, format `ixt:num-dot-decimal`). No dimension-free fact exists for the period across the searched accessions (26-000046, 26-000021, 26-000008, 25-000008).

### 3.4 Consequence entry on View B `total_debt` 2026-03-31 (R-G-2 consequence)

The formula row `total_debt` 2026-03-31 stays `missing_dependency` (E2: never derived from a partial input set), but its `missing_inputs` is re-coded to follow the corrected dependency: `short_term_debt` moves from `missing_standard_fact` to `disallowed_dimension`; `long_term_debt_current` and `long_term_debt` stay `missing_standard_fact`. The formula value is never derived; the component cells print under their own labels.

## 4. Typed absences (counts by code and reason, from `gold_cells.jsonl`)

Across 2397 gold cells: 586 verified_from_bytes; 589 typed_absence_verified; 1222 not_applicable_verified.

Counts within typed_absence_verified (rows that carry a `code` other than `null`):
- `missing_standard_fact`: 416 (concept absent or no dimension-free fact in the package)
- `missing_dependency`: 156 (formula's named input is missing or unresolvable; E2 rule preserved)
- `disallowed_dimension`: 17 (every fact for a mapped concept sits on a dimensioned context; G0-c allowed axes do not apply to the headline cell)

`r1_code` companion codes are kept from the r3 source (`MISSING_CONCEPT` for `missing_standard_fact`, `MISSING_DEPENDENCY` for `missing_dependency`, `NOT_EVALUABLE_DIMENSION` for `disallowed_dimension`); codes are read from `engine/fundamental_forensics/metric_registry.py:43-50,1515,2093-2106` and `financial_intelligence_packet.py:893,910`.

## 5. ERRATA-1 handling

- **E1 BAC alias candidates** — does not apply to CAT.
- **E2** — `total_debt` is `missing_dependency` and never derived from a partial input set. The resolved components print under their own labels: `short_term_debt` 5,514M (us-gaap:ShortTermBorrowings, c-4, @4878695, `raw 5,514`) and `long_term_debt` 30,696M (us-gaap:LongTermDebtNoncurrent, c-4, @4950784, `raw 30,696`) at 2025-12-31. `long_term_debt_current` is absent in the admitted 10-Ks (zero `us-gaap:LongTermDebtCurrent` occurrences).
- **E3 GOOGL** — does not apply.
- **E4 CAT** — every cash-flow and debt cell carries `scope_label: consolidated (including Financial Products)`. The r3 cell count is **752 cell lines across views** (versus r2's 672); the binding evidence is the 8 `scope_label` pin (Section 6 below). MP&E-only figures are PK01 in K, never gold cells. CAT SBC (`share_based_compensation_expense`) = `MISSING_CONCEPT` (`missing_standard_fact`); zero `us-gaap:ShareBasedCompensation` occurrences in any admitted package; only a methodology-difference SBC line exists in the filings (never aliased).
- **E5 census values** — never used as gold.
- **E6 admission dependencies** — the CAT 10-Q **#9056** is in G0 and **CONFIRMED**; no D1-ext dependency remains for CAT. CAT admission state: `admitted`.
- **E7** — pre-A0 work; this lane runs G-GOLD finalisation (source packaging) plus G2 assembly.

## 6. Pins (full machine form in `pack_manifest.json:pins`)

All byte evidence: member `cat-20251231.htm`, sha256 `4777564fdc7b0b9e28317e484a3fa9a4be6f15e108851dca9f72b3223e548482` (equals g_src manifest digest and this lane's re-hash), accession 0000018230-26-000008 unless noted.

### P1 `scope_label` — ERRATA E4
- label exactly `consolidated (including Financial Products)`.
- statement families: cash_flow_statement = the 7 metrics anchored `*cash_flow_statement` in `config/fundamental_forensics/metrics/v1/metric_catalog.yaml:36-41` (per-metric lines :186-234); debt = `short_term_debt` :346-352, `long_term_debt_current` :353-359, `long_term_debt` :360-366 (balance_sheet anchor :43-48) plus the derived debt metrics `total_debt` :367-373, `cash_to_total_debt` :467-478, `net_debt` :479-490, `debt_to_equity` :503-514 whose dependencies are the debt inputs (`formulas/core.yaml:20-25,32-43,50-55`); E4 additions `free_cash_flow` :491-502 (`formulas/core.yaml:44-49`) and `share_based_compensation_expense` :179-185 (E4's own SBC ruling).
- coverage: every cash-flow and debt cell across views carries the label; **0 lack it**; no non-family row carries it.
- MP&E/PK01: the FY2025 filing names the former ME&T column "Machinery, Power & Energy" (MP&E; income-statement supplemental columns exist in the bytes: `srt:ProductOrServiceAxis=cat:MachineryPowerEnergyMember` Revenues 63,980M @2284633 c-5 and `cat:FinancialProductsMember` 3,609M @2287050 c-8). MP&E-only figures are PK01 in K, never gold cells. **Count of r3 cells whose trace context carries a group axis member (MP&E or Financial Products): 0** (every traced context is undimensioned).

### P2 `errata_absence` (E4) — share_based_compensation_expense = missing_standard_fact
- us-gaap:ShareBasedCompensation occurrences: **0 in every admitted package** (-26-000008, -25-000008, -26-000046, -26-000021) and 0 in capture-only -25-000040.
- Every gold cell stays typed_absence_verified (missing_standard_fact); only a methodology-difference SBC line exists, never aliased.

### P3 `errata_absence` — gross_profit = missing_standard_fact (no derivation)
- us-gaap:GrossProfit occurrences: **0 in all five staged packages**.
- CAT reports cost_of_revenue and revenue but no gross profit line; arithmetic the issuer did not perform is forbidden (§0 gate 5).

### P4 `errata_absence` (E2) — total_debt = missing_dependency naming long_term_debt_current
- long_term_debt resolves under its own label: us-gaap:LongTermDebtNoncurrent, contextRef c-4, byte_offset 4950784, raw_text `30,696`, scale 6, decimals −6, value 30696000000, rendered row "Total long-term debt due after one year".
- long_term_debt_current: us-gaap:LongTermDebtCurrent occurrences 0 in the admitted 10-Ks → typed absence (missing_standard_fact).
- total_debt cell: typed_absence_verified (missing_dependency, missing input long_term_debt_current); resolved components print under their own labels (short_term_debt 5,514M; long_term_debt 30,696M); never derived from a partial input set.

### P5 `errata_absence` (R3) — net_income_loss = missing_standard_fact
- us-gaap:NetIncomeLoss occurrences: **0 in all five staged packages**.
- Candidate us-gaap:ProfitLoss (FY2025 consolidated): contextRef c-1, byte_offset 2322497, raw_text `8,882`, value 8882000000 — never aliased (includes NCI; A29 splice).
- Candidate cat:ProfitOfConsolidatedCompanies (FY2025 consolidated): contextRef c-1, byte_offset 2317330, raw_text `8,773`, value 8773000000 — never aliased (custom cat: concept outside ALLOWED_TAXONOMIES, `engine/fundamental_forensics/metric_registry.py:53`).
- r3 records 0 valued net_income_loss rows in any view.

### P6 `errata_absence` (R3) — stockholders_equity = missing_standard_fact
- us-gaap:StockholdersEquity occurrences: **0 in all five staged packages**.
- Candidate us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest (2025-12-31 consolidated): contextRef c-4, byte_offset 2442663, raw_text `21,318`, value 21318000000 — never aliased (includes the NCI portion).

### P7 `negative_mapping` — inventory_net must not cite cat:WholesaleInventoryReceivables
- Every valued inventory_net row (12) cites us-gaap:InventoryNet; the string `cat:WholesaleInventoryReceivables` appears nowhere in r3 CAT gold_facts.jsonl (0 citations).
- The newest 10-K cell uses us-gaap:InventoryNet: contextRef c-4, byte_offset 2385105, raw_text `18,135`, value 18135000000.
- The forbidden concept exists in the bytes only as dimensioned Cat Financial fair-value disclosure facts (e.g. contextRef c-851, byte_offset 5351156, raw_text `1,931`, `us-gaap:FairValueByMeasurementBasisAxis=CarryingReportedAmountFairValueDisclosureMember`, instant 2025-12-31) — a receivable, never inventory.

### P8 `segment_as_filed` — FY2025 revenue by reportable segment (newest 10-K)
All us-gaap:Revenues, unit usd, decimals −6, scale 6, duration 2025-01-01→2025-12-31; axis `us-gaap:StatementBusinessSegmentsAxis` (+ `srt:ConsolidationItemsAxis`):

| member (as filed) | value | trace (contextRef @ byte_offset, raw_text) | external excl. intersegment | intersegment |
|---|---|---|---|---|
| cat:ConstructionIndustriesMember | 25,060M | c-878 @5537759 `25,060` | 24,800M (c-876 @5536018) | (260)M (c-877 @5536900, sign −) |
| cat:ResourceIndustriesMember | 12,474M | c-885 @5542765 `12,474` | 12,185M (c-883 @5541426) | (289)M (c-884 @5542107, sign −) |
| cat:PowerEnergyMember | 32,201M | c-892 @5547802 `32,201` | 27,143M (c-890 @5546432) | (5,058)M (c-891 @5547113, sign −) |
| cat:FinancialProductsSegmentMember | 4,220M | c-899 @5553015 `4,220` | 4,220M (c-897 @5551383) | — (c-898, nil) |

- Consolidated: **67,589M**, the filing's own undimensioned fact (us-gaap:Revenues, contextRef c-1 @2289084, raw_text `67,589`; also rendered in the segment note @5572475).
- Reconciling items as the filing shows them: intersegment sales included in reportable segments **(5,607)M** (c-905 @5557702, sign −, raw `5,607`); All Other segment total **327M** (c-912 @5563349); corporate items and eliminations **(6,693)M** (c-919 @5567519, sign −, raw `6,693`; components: corporate items (805)M c-917 @5566416, intersegment eliminations (5,888)M c-918 @5566952).
- Sum of segments (check only): 25,060+12,474+32,201+4,220 = **73,955M** = the filing's own reportable-aggregation total (c-906 @5558449). It differs from consolidated and reconciles as filed: 73,955 + 327 − 6,693 = 67,589. The kernel never sums segments (A31 no-sum fence).

### Omitted pin types
`not_applicable_class`: omitted — the coverage file's `field_denominator.not_applicable` excludes metrics only for BAC; CAT is `industrial` (`config/fundamental_forensics/coverage/five_issuer_v1.json`) and all 50 catalog metrics apply. `kpi_vintages`, `decimals_precision`, `dual_listing`: no CAT trap in the pin list; single listing US-XNYS-CAT.

## §Findings (hand-derived detector states; machine form in `expected_run_v1.json:finding_states` and `coverage_counts`)

Basis view (from `pack_manifest.packet_basis`): `as_filed` @ 0000018230-26-000046 (newest 10-Q, knowledge_time 2026-08-05T12:43:40.000Z). Rules read as data: `config/fundamental_forensics.yml:61-85` (formulas + thresholds; pack `fundamental-forensics-five/v1` :4), `engine/fundamental_forensics/detectors.py:20-21,112-119` (300–430-day annual pairing), `:263-267/:399-414` (two/three-period gates + consecutive check), `:23-33,52-72` (applicability; SIC 3531 → industrial → all five applicable), `:36-49` (reason vocabulary), `engine/fundamental_forensics/normalize.py:255-277,289-325` (vintage grouping/selection), `models.py:31-34` (states). Kernel never run.

Vintage period ends of the basis view (valued direct cells): 2025-06-30 (26 obs), 2025-12-31 (12), 2026-06-30 (27); the 10-Q's durations are 3- and 6-month only — **no annual duration period exists in the basis view**, so no pair can satisfy the 300–430-day annual window.

| detector | state | threshold | rule cites | missing inputs (named) |
|---|---|---|---|---|
| accruals_trending_up | not_evaluable | min_three_period_increase 0.03 | yml:81-85; detectors.py:397-449 | consecutive_annual_periods; net_income@2025-06-30, @2025-12-31, @2026-06-30 (R3 typed absence); operating_cash_flow@2025-12-31; assets@2025-06-30 |
| capital_intensity_rising | not_evaluable | growth_gap_pp 10 | yml:76-80; detectors.py:520-522 | consecutive_annual_periods; revenue@, capital_expenditures@, operating_income@ 2025-12-31 |
| inventory_build | not_evaluable | growth_gap_pp 15 | yml:71-75; detectors.py:517-519 | consecutive_annual_periods; revenue@2025-12-31 |
| margin_compression_despite_revenue_growth | not_evaluable | min_revenue_growth_pp 3 | yml:61-65; detectors.py:509-511 | consecutive_annual_periods; gross_profit@2025-12-31, @2026-06-30 (E4/spec §5 typed absence); revenue@2025-12-31 |
| receivables_stretch | not_evaluable | growth_gap_pp 10 | yml:66-70; detectors.py:512-516 | consecutive_annual_periods; revenue@2025-12-31 |

State counts: triggered 0 / clear 0 / not_evaluable 5. The states above replace the r2 placeholder `not_evaluable` (which carried no derivation) with rule-cited reasons.

## §Projection note (assembly decisions; from RULINGS.md)

This projection is the r3 of CAT (`fif-g-gr-cat-20261019a/r3`) carried forward under the lane's `build_pack.py`:
- Drops: `concepts_searched`, `catalog_codes`, `occurrences`, the per-row header fields `schema`/`issuer`/`cik`, and `dependency_cells` except an orphan dependency cell (kept slimmed to ORPHAN_FIELDS when no standalone row exists at the gold test's join key).
- Sort: lines by `(view, source_accession or "", metric_id, period_key)`.
- Row count: equals the gold source (2397). Every kept field is byte-equal to the gold source except the (row, field) pairs listed in `gold_corrections`.
- Placeholders: every draft-`pending-G-PR` value in the two draft JSONs becomes `kernel_minted_not_gold` under identity keys only.
- `attested: false` everywhere; `historical_attestation: unavailable_until_d2_admission`.

## §Kernel defect records (this lane; applied in commit 3)

`pack_manifest.defects[]` is populated by `apply_defects.py` from `defects_0000018230.json` in the lane's third commit (after the five pack files are committed). Record shape (per defect entry):

| field | meaning |
|---|---|
| `id` | unique defect identifier (e.g. `D-C1-0001`, `D-C2-0010`, `D-C4a-0001`) |
| `row_keys` | list of `{view, source_accession, metric_id, period_key}` tuples the kernel disagrees with the gold on |
| `comparison` | `value` (kernel output value differs from gold) or `code` (kernel output code differs from gold) |
| `record` | `{ruling, cluster, kr_label, category, accession, concept, context, filed_value, filed_location, formula, gold, kernel_output, kernel_observation, repro}` |

Counts by cluster (from `defects_0000018230.json`):
- `C1_viewB_unlinked_vintages`: 60 (ruling R-G-1, comparison `value`).
- `C2_viewB_formula_unlinked_cascade`: 20 (ruling R-G-1, comparison `value` for the two formula rows `inventory_to_revenue` and `receivables_to_revenue` FY2023; comparison `code` for the others).
- `C4a_formula_dimension_cascade`: 24 (ruling R-G-3, comparison `code`).

The two View B formula rows **`inventory_to_revenue` FY2023** and **`receivables_to_revenue` FY2023** stay C2 kernel defects under R-G-1 with comparison category `value_vs_absence` (the `residual_reclass.json` reclassification): the r3 gold derives the formula value from latest-known dependencies (inventory or receivables at 2023-12-31 from `0000018230-25-000008`, revenue FY2023 from `0000018230-26-000008`); the kernel still refuses unlinked vintages (`incompatible_dependencies`). Gold was never edited to match the kernel.

Repro command (every defect): `FIF_GSRC_STAGE_ROOT=$HOME/lanes/in/orch-g/stage/fif-gsrc ~/lanes/venv/bin/python -m pytest tests/test_fif_g_pack_kernel.py -q -p no:cacheprovider -rxX -k "<id>"`. The shared kernel test turns each `defects[]` entry into `xfail(strict=True, reason=<id>)` for exactly its comparison group.

## §Gaps

- Kernel-minted hash/id fields in the two draft JSONs hold the literal `kernel_minted_not_gold` placeholder; they are minted by the kernel, never copied from a kernel run into these files.
- finding_states are now hand-derived (§Findings); they are gold-side states under the published rules, not kernel output.
- Browser evidence and the live FIF page render are pending A0 and live publish (§0 gate 6); no packet/page/browser proof exists in this lane.
- fiscal_quarter / fiscal_year / calendar_kind in period objects stay null/unknown (AAPL witness shape); the fiscal label encodes the issuer FYE.
- View B formula cells carry `dep_source_accessions` instead of a single `source_accession` (inputs may come from several packages under the r1 method).
- Backlog is MD&A prose → K: PK03 + PK01; no gold cell.
- `0000018230-25-000040` is capture-only (not admitted); not a gold cell source.