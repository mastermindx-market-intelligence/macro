# SNOW gold sheet — G1 gold pack (CIK 0001640147, Snowflake Inc.)

Base commit cbcf823d4045ff640e63a2a0531a1a8155f5ae02 (G0 branch head, merges
origin/main through 69dd6e77). Gold source: frozen r2
`fif-ggold-20261013/r2/SNOW/` (FREEZE.txt sha-bound per file in
`pack_manifest.gold_source`). `attested:false` and
`historical_attestation: unavailable_until_d2_admission` everywhere. The
ORCH-G kernel-comparison rulings **R-G-1 .. R-G-6** (RULINGS.md, 2026-10-19)
are distinct from the earlier gold-engine rulings **R-G1** (Decimal contract),
**R-G2** (period alignment) and **R-G3** (knowledge time and the two views)
cited in §5; both sets appear in this sheet and never mix.

This is the r2 gold sheet (`SNOW_gold_sheet.md`, sha256
`115794209604c28bf519ba596e29bbc196e4b08ae96a8ac39874a7aee10c6c86` in the r2
FREEZE) carried forward into the committed G-pack layout, with exactly these
changes (G_PACK_BUILD_SPEC.md §1; ERRATA-1 where they differ):

1. **Kernel-minted hash/id fields** in the two expected JSONs hold the string
   `kernel_minted_not_gold` (minted by the kernel; not gold; never copied from a
   kernel run). Two draft `limitations` lines that described the draft
   placeholders and the then-underived finding states were reworded to describe
   the final file — forced by the rules that the draft placeholder token must
   not remain and the not-gold string may appear only under identity keys.
2. **finding_states** are the hand derivation in §Findings below (the r2 draft
   carried a placeholder). The finding coverage counts that follow from them
   are unchanged: triggered 0, clear 0, not_evaluable 5.
3. **gold_cells.jsonl** is the §Projection projection of r2 `gold_facts.jsonl`:
   3723 rows, checker output 52527 checked fields byte-equal, 48 corrected
   (row, field) pairs, 1 re-keyed row, 0 problems (§Gold corrections). Dropped
   as verbose duplicates: `concepts_searched`, `catalog_codes`, `occurrences`,
   `dependency_cells`, and the per-row header fields `schema`/`issuer`/`cik`
   (identity and attestation live in `pack_manifest.json`; every row keeps
   `attested:false` and `historical_attestation`). Formula dependency values
   are re-derived by the (view, source_accession, metric_id, dep_period) join
   the gold test performs.
4. **§8.1 corrected.** The r2 §8.1 table printed `576` for the FY2024 vintage
   of the FY2026 10-K row. The staged bytes decide: the row reads 733 / 576 /
   449 under column headers January 31, 2026 / 2025 / 2024, so the FY2024-column
   value is **449** (byte offset 819165). `576` is the FY2025 column. The r2
   summary line (449) agrees with the bytes. No r2 gold_facts value is
   contradicted by that correction, so it adds no `gold_corrections` entry.
5. **Gold corrections (48 entries, RULINGS.md R-G-2 and R-G-5)** applied to the
   r2 projection, each confirmed by this lane's independent byte re-read
   (§Gold corrections). Gold was never edited to match the kernel; every
   correction is bytes-over-r2, adjudicated before this lane ran.
6. **Kernel defect records** (87, all RULINGS.md R-G-1) are inserted into
   `pack_manifest.defects` by this lane's third commit (§Kernel defect
   records). The gold cells are untouched by them.

Packet basis: view `as_filed`, source_accession 0001640147-26-000037 (the r2
draft's basis; newest admitted package by knowledge_time), knowledge_time
2026-09-05T00:06:23.000Z (`sec_submissions_witness.json:acceptanceDateTime`).
Admitted set (R5): 0001640147-26-000008, -25-000052 (10-K) and
0001640147-26-000037, -26-000030 (10-Q). FYE January 31. Issuer class
`software` (SIC 7372, coverage contract five_issuer_v1.json; detectors.py:52-72).

---

## Source accessions (from pack_manifest.json; R5 admitted set)

| form | accession | period_of_report | knowledge_time |
|---|---|---|---|
| 10-Q | 0001640147-26-000037 | 2026-07-31 | 2026-09-05T00:06:23.000Z |
| 10-Q | 0001640147-26-000030 | 2026-04-30 | 2026-05-30T00:04:43.000Z |
| 10-K | 0001640147-26-000008 | 2026-01-31 | 2026-03-21T00:12:39.000Z |
| 10-K | 0001640147-25-000052 | 2025-01-31 | 2025-03-22T00:19:20.000Z |

Capture-only, not admitted (R5): 0001640147-24-000101 (10-K, 2024-01-31,
knowledge_time 2024-03-27T00:16:31.000Z) and 0001640147-25-000187 (10-Q,
2025-07-31, not admitted; knowledge_time 2025-09-06T00:16:10.000Z). Their
bytes never enter a gold cell; the FY2024 10-K appears only as the
documentation-only KPI vintage in §Pins.

## Views built (gold-engine R-G3)

- **VIEW A `as_filed`**: one cell set per admitted package, built ONLY from that
  package's own ix facts (comparative columns included). 2142 cells across 4
  packages.
- **VIEW B `latest_known_as_of`**: for each (metric, period) the value from the
  newest admitted package reporting it, ordered by knowledge_time. 1581 cells.
  Informational only; never cross-checked against the census.
- knowledge_time order: 0001640147-26-000037 > -26-000030 > -26-000008 >
  -25-000052.
- Cross-package value differences are recorded as `restatement_observed`
  findings, never resolved by picking. SNOW has none (§restatement_observed).
- `statement_roles.json` and `tagged_facts.jsonl` remain r2 byte-copies (inputs
  unchanged); both are bound by sha256 in `pack_manifest.gold_source`.

## Headline cells — VIEW A of the newest admitted 10-K (0001640147-26-000008)

Value column is `value_exact` (Decimal string; formula cells carry the R-G1
contract result as `str(result)`). Rendered columns come from the independent
DOM cross-read (kept for every verified value). Every value cites accession,
concept and contextRef and equals the gold_cells.jsonl row.

| metric | period | value_exact | concept | contextRef | rendered row label | cross-read | state |
|---|---|---|---|---|---|---|---|
| revenue | FY2026 | 4683946000 | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | c-1 | Revenue | agree | verified_from_bytes |
| cost_of_revenue | FY2026 | 1537805000 | us-gaap:CostOfGoodsAndServicesSold | c-1 | Cost of revenue | agree | verified_from_bytes |
| gross_profit | FY2026 | 3146141000 | us-gaap:GrossProfit | c-1 | Gross profit | agree | verified_from_bytes |
| operating_expenses | FY2026 | 4581306000 | us-gaap:OperatingExpenses | c-1 | Total operating expenses | agree | verified_from_bytes |
| operating_income_loss | FY2026 | -1435165000 | us-gaap:OperatingIncomeLoss | c-1 | Operating loss | agree | verified_from_bytes |
| net_income_loss | FY2026 | -1331616000 | us-gaap:NetIncomeLoss | c-1 | Net loss attributable to Snowflake Inc. | agree | verified_from_bytes |
| research_and_development_expense | FY2026 | 1969472000 | us-gaap:ResearchAndDevelopmentExpense | c-1 | Research and development | agree | verified_from_bytes |
| net_cash_from_operating_activities | FY2026 | 1221942000 | us-gaap:NetCashProvidedByUsedInOperatingActivities | c-1 | Net cash provided by operating activities | agree | verified_from_bytes |
| capital_expenditures | FY2026 | 101628000 | us-gaap:PaymentsToAcquirePropertyPlantAndEquipment | c-1 | Purchases of property and equipment | agree | verified_from_bytes |
| cash_and_cash_equivalents | 2026-01-31 | 2828163000 | us-gaap:CashAndCashEquivalentsAtCarryingValue | c-4 | Cash and cash equivalents | agree | verified_from_bytes |
| short_term_investments | 2026-01-31 | | | | | | typed_absence_verified (missing_standard_fact) as-filed zero-hit in 0001640147-26-000008: no dimension-free fact for any of the 2 mapped concepts this period |
| inventory_net | 2026-01-31 | | | | | | typed_absence_verified (missing_standard_fact) as-filed zero-hit in 0001640147-26-000008: no dimension-free fact for any of the 1 mapped concepts this period |
| total_assets | 2026-01-31 | 9132495000 | us-gaap:Assets | c-4 | Total assets | agree | verified_from_bytes |
| long_term_debt | 2026-01-31 | | | | | | typed_absence_verified (missing_standard_fact) as-filed zero-hit in 0001640147-26-000008: no dimension-free fact for any of the 1 mapped concepts this period |
| long_term_debt_current | 2026-01-31 | | | | | | typed_absence_verified (missing_standard_fact) as-filed zero-hit in 0001640147-26-000008: no dimension-free fact for any of the 1 mapped concepts this period |
| short_term_debt | 2026-01-31 | | | | | | typed_absence_verified (missing_standard_fact) as-filed zero-hit in 0001640147-26-000008: no dimension-free fact for any of the 1 mapped concepts this period |
| total_debt | 2026-01-31 | | | | | | typed_absence_verified (missing_dependency) never derived from a partial input set (E2); missing: short_term_debt, long_term_debt_current, long_term_debt |
| stockholders_equity | 2026-01-31 | 1924102000 | us-gaap:StockholdersEquity | c-4 | Total Snowflake Inc. stockholders' equity | agree | verified_from_bytes |
| total_liabilities | 2026-01-31 | 7208393000 | us-gaap:Liabilities | c-4 | Total liabilities | agree | verified_from_bytes |
| basic_earnings_per_share | FY2026 | -3.95 | us-gaap:EarningsPerShareBasic | c-1 | Net loss per share—basic and diluted | agree | verified_from_bytes |
| diluted_earnings_per_share | FY2026 | -3.95 | us-gaap:EarningsPerShareDiluted | c-1 | Net loss per share—basic and diluted | agree | verified_from_bytes |
| basic_weighted_average_shares | FY2026 | 337493000 | us-gaap:WeightedAverageNumberOfSharesOutstandingBasic | c-1 | Weighted-average shares, basic and diluted | agree | verified_from_bytes |
| diluted_weighted_average_shares | FY2026 | 337493000 | us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding | c-1 | Weighted-average shares, basic and diluted | agree | verified_from_bytes |
| share_based_compensation_expense | FY2026 | 1599547000 | us-gaap:ShareBasedCompensation | c-1 | Stock-based compensation, net of amounts capitalized | agree | verified_from_bytes |
| free_cash_flow | FY2026 | 1120314000 | formula `net_cash_from_operating_activities - capital_expenditures` (formula.free_cash_flow/v1; dependencies valued at the same accession, contextRefs c-1) | | | | verified_from_bytes |
| gross_margin | FY2026 | 0.6716860100436683087294345408764320 | formula `gross_profit / revenue` (formula.gross_margin/v1; dependencies c-1) | | | | verified_from_bytes |
| common_shares_outstanding | 2026-01-31 | | | | | | typed_absence_verified (missing_standard_fact) as-filed zero-hit in 0001640147-26-000008: no dimension-free fact for any of the 1 mapped concepts this period |
| receivables_to_revenue | FY2026 | 0.2783422353716289641255471348303332 | formula `accounts_receivable_net / revenue` (formula.receivables_to_revenue/v1) | | | | verified_from_bytes |
| inventory_to_revenue | FY2026 | | | | | | typed_absence_verified (missing_dependency) never derived from a partial input set (E2); missing: inventory_net |
| current_ratio | 2026-01-31 | 1.298736614566689531222331004133939 | formula `current_assets / current_liabilities` (formula.current_ratio/v1) | | | | verified_from_bytes |

## Gold corrections (pack_manifest.gold_corrections, 48 entries, 9 rows)

Each entry is {row_key, field, op, r2_value, corrected_value, evidence, reason,
ruling}; only where the filing bytes contradict r2. Every one was confirmed by
this lane's independent byte re-read over the staged members (stdlib scan of
the raw ix bytes; script `scan_goodwill.py` in the lane output, never
committed). Gold was never edited to match the kernel: the kernel comparison
that surfaced these rows is classification input only, and the corrections
were frozen in RULINGS.md before this lane ran.

### R-G-5 — common_stock_repurchases FY2023 (2 rows)

RULINGS.md R-G-5: an ixt:fixed-zero element is a filed zero (the dash is the
glyph of an explicit zero transform), so the cell is the valued zero "0" with
the byte citation — not a missing concept, not a zero stand-in.

Row 1 — View A, as_filed 0001640147-25-000052, period
['duration','2022-02-01','2023-01-31']. r2 had missing_standard_fact /
MISSING_CONCEPT ("concept tagged nil/dash for this period"). Corrected:
verification_state verified_from_bytes, concept
us-gaap:PaymentsForRepurchaseOfCommonStock, value_exact "0", code/r1_code/
detail/nil_facts_for_period removed, trace added. Byte confirmation
(snow-20250131.htm, sha256 516c7fc913f21fe346ceeef6638b7d6c3c5c18eee9c1715dc7c235103cad4c13):
at byte_offset 1582980 the opening tag is
`<ix:nonFraction unitRef="usd" contextRef="c-13" decimals="-3"
name="us-gaap:PaymentsForRepurchaseOfCommonStock" format="ixt:fixed-zero"
scale="3" id="f-499">&#8212;</ix:nonFraction>` — glyph "&#8212;" (em dash),
context c-13 period duration 2022-02-01 → 2023-01-31, dimension-free. Every
confirmed field equals the trace.

Row 2 — the View B twin re-keyed to 0001640147-25-000052 (source_accession set,
knowledge_time 2025-03-22T00:19:20.000Z, searched_accessions removed,
also_reported_by [], restatement_observed false). Same byte confirmation at the
same offset; same filed zero "0". Per RULINGS.md, the corrected rows omit
cross_read and alias_presence (the zero is read directly from the transform
element).

### R-G-2 — View B goodwill, 7 rows (C4b)

RULINGS.md R-G-2: a View B row coded missing_standard_fact where every fact for
a mapped concept in that period sits on a dimensioned context is
disallowed_dimension / NOT_EVALUABLE_DIMENSION (catalog direct no-result code;
config/fundamental_forensics/metrics/v1/metric_catalog.yaml:63; E3 precedent).
Corrected fields per row: code, r1_code, detail, and axes_seen added; evidence
carries the byte re-read (contexts + dimension_free_fact_found false).

The re-read scanned every iXBRL member of all four searched accessions
(0001640147-26-000037, -26-000030, -26-000008, -25-000052) for ix:nonFraction /
ix:nonNumeric facts named us-gaap:Goodwill whose context period equals the row
instant. **No dimension-free fact exists for any of the seven periods in any
searched accession**; every fact found sits on us-gaap:BusinessAcquisitionAxis
(business-combination measurement dates), so the axes_seen union is exactly
["us-gaap:BusinessAcquisitionAxis"] per row:

| period (instant) | facts found | contexts (accession, member, contextRef, member axis value, byte offset) |
|---|---|---|
| 2022-03-31 | 1 | 0001640147-25-000052 snow-20250131.htm c-233 snow:StreamlitIncMember @2236120 |
| 2022-09-23 | 1 | 0001640147-25-000052 snow-20250131.htm c-227 snow:ApplicaSpZooMember @2214826 |
| 2023-02-10 | 4 | 0001640147-26-000008 snow-20260131.htm c-266 snow:MountainUSCorporation…MobilizeNetCorporationMember @2313603; c-268 snow:LeapYearTechnologiesIncMember @2328302; 0001640147-25-000052 snow-20250131.htm c-216 (MobilizeNet) @2173028; c-218 (LeapYear) @2186941 |
| 2023-07-31 | 2 | 0001640147-26-000008 snow-20260131.htm c-264 snow:NeevaIncAndItsEquityInvesteeMember @2299944; 0001640147-25-000052 snow-20250131.htm c-214 (Neeva) @2160271 |
| 2023-12-20 | 2 | 0001640147-26-000008 snow-20260131.htm c-259 snow:SamoohaInc.Member @2285475; 0001640147-25-000052 snow-20250131.htm c-211 (Samooha) @2146415 |
| 2024-11-25 | 2 | 0001640147-26-000008 snow-20260131.htm c-246 snow:DatavoloInc.Member @2242242; 0001640147-25-000052 snow-20250131.htm c-197 (Datavolo) @2102433 |
| 2025-06-06 | 1 | 0001640147-26-000008 snow-20260131.htm c-234 snow:CrunchyDataSolutionsInc.Member @2203182 |

Consequence (R-G-2): no formula row names a corrected goodwill dependency in
SNOW (goodwill feeds no formula), so no formula re-coding follows here.

## Typed absences (from gold_cells.jsonl)

Closed vocabulary as the repo defines it (catalog no-result codes,
config/fundamental_forensics/metrics/v1/metric_catalog.yaml:63):
missing_standard_fact, outside_period_constraint, disallowed_dimension; plus
missing_dependency (E2) and unsupported_metric refusals. Every absence carries
value_exact null and its r1_code twin; never a zero, a guess or a stand-in.

| code | r1_code | rows | reason |
|---|---|---|---|
| outside_period_constraint | — | 1825 | period not present in the package (View A comparative columns / View B period lattice) |
| missing_standard_fact | MISSING_CONCEPT | 815 | 472 "as-filed zero-hit …no dimension-free fact for any of the N mapped concepts this period" (View A); 343 "zero-hit search across every admitted package…" (View B) |
| missing_dependency | MISSING_DEPENDENCY | 315 | E2: total_debt family and ratios — never derived from a partial input set; the missing inputs are named per row |
| disallowed_dimension | NOT_EVALUABLE_DIMENSION | 23 | facts exist only on dimensioned contexts; G0-c allowed axes do not apply (includes the 7 corrected goodwill rows above) |
| unsupported_metric | — | 73 | refusal rows (R4: 8-K / non-GAAP / KPI series — CustomerCount &c. — no governed catalog contract), routed to E2 |

Valued rows 672 (593 direct, every one carrying a trace with accession,
member_file, member_sha256, concept, contextRef, unitRef, decimals; 79 formula
rows carrying formula_rule_id + dependency list instead). Formula rows total
394 (79 valued, 315 missing_dependency).

## ERRATA-1 handling

- E1 is BAC-only: no SNOW aliasing occurs under it. R3 (frozen spec, restated
  by ERRATA-1 G0-f) does bind SNOW: AllocatedShareBasedCompensationExpense and
  ProfitLoss are never aliased (§Pins), and RPO is a tagged fact, not a metric.
- E2 binds: total_debt is never derived from a partial input set — every
  total_debt row (both views, all periods) is missing_dependency naming
  short_term_debt, long_term_debt_current, long_term_debt; the resolved
  component never prints as "debt".
- R4 binds: 8-K EX-99.1 non-GAAP reconciliations and KPI time-series serving
  are refused in G and routed to E2; refusal rows name them.
- E6: SNOW already met the R5 admission bar pre-G (2 10-K + 2 10-Q admitted);
  no D1-ext dependency applies.
- E7: this pack's bytes were finalised pre-A0; A0's schedule-born proof runs on
  unchanged kernel semantics (browser evidence pending A0, §Gaps).

## Rulings applied (gold-engine; unchanged in this pack)

- **R-G1** decimal contract: prec=34, ROUND_HALF_EVEN, Emin=-6143, Emax=6144,
  capitals=1, clamp=0; `ctx.plus` on inputs and result; `str(result)` recorded;
  no quantize/normalize. 15 SNOW cells changed vs r1 (all listed in r2
  DELTA.md).
- **R-G2** period alignment: `dependency_period_alignment` read from
  `config/fundamental_forensics/metrics/v1/formulas/core.yaml` (8 same_period,
  2 ending_instant_to_duration: receivables_to_revenue, inventory_to_revenue).
  Example: receivables_to_revenue FY2024 (as_filed 0001640147-25-000052,
  formula row) takes accounts_receivable_net at ['instant','2024-01-31']
  against revenue over ['duration','2023-02-01','2024-01-31'] =
  0.3302710254699020733735282767899678.
- **R-G3** knowledge time + two views; every row carries view,
  source_accession, knowledge_time, knowledge_time_source
  (`sec_submissions_witness.json:acceptanceDateTime`). Cited cell:
  accounts_receivable_net 2024-01-31 — VIEW A of 26-000008 as-filed zero-hit
  typed absence; VIEW B 926902000 from 0001640147-25-000052
  (us-gaap:AccountsReceivableNetCurrent, contextRef c-5).

## restatement_observed

None: no (metric, period) carries different dimension-free values across the
admitted packages of SNOW.

## Projection note (RULINGS.md assembly decisions)

gold_cells.jsonl is produced by gold_assemble/project_gold from r2
gold_facts.jsonl only: drops concepts_searched, catalog_codes, occurrences,
the per-row header fields schema/issuer/cik, and dependency_cells EXCEPT an
orphan dependency cell (kept slimmed when no standalone row exists at the gold
test's join key — SNOW has 0 orphan rows). Row count equals the gold source
(3723); every kept field is byte-equal except the 48 listed gold_corrections
(1 row re-keyed to 0001640147-25-000052 under R-G-5). The checker re-derives
the projection independently: 52527 fields checked, 0 problems. Defects are
applied in the lane's third commit (apply_defects.py), not by a later seat
step. attested false everywhere; historical_attestation
unavailable_until_d2_admission.

## Pins (pack_manifest.pins, 11 entries; each with ruling + cited evidence)

### KPI vintages (A29/R5/R4; untagged text rows — byte evidence re-read from the staged members)

"Customers with trailing 12-month product revenue greater than $1 million",
FY2024 column, re-read from the staged member bytes (sha256 pinned per row):

| vintage accession | admitted | member (sha256 prefix) | column headers | row values | FY2024-column value | value byte offset | label byte offset |
|---|---|---|---|---|---|---|---|
| 0001640147-24-000101 | no (capture-only) | snow-20240131.htm b2ea12cbc6ad67ef | Jan 31 2024 / 2023 / 2022 | 461 / 331 / 186 | **461** (col 1) | 673164 | 672666 |
| 0001640147-25-000052 | yes | snow-20250131.htm 516c7fc913f21fe3 | Jan 31 2025 / 2024 / 2023 | 580 / 455 / 329 | **455** (col 2) | 759288 | 758379 |
| 0001640147-26-000008 | yes | snow-20260131.htm 729e02a5c711ed37 | Jan 31 2026 / 2025 / 2024 | 733 / 576 / 449 | **449** (col 3) | 819165 | 817866 |

Row label at each offset: "Customers with trailing 12-month product revenue
greater than $1 million(3)" (FY2024 10-K) / "…$1 million(4)" (FY2025, FY2026
10-Ks). Metrics-table footnote (retrospective adjustment policy) at byte 680224
(snow-20240131.htm), 766516 (snow-20250131.htm), 826033 (snow-20260131.htm):
"Historical numbers for (i) net revenue retention rate, (ii) customers with
trailing 12-month product revenue greater than $1 million, and (iii) Forbes
Global 2000 customers reflect any adjustments for acquisitions, consolidations,
spin-offs, and other market activity."

Gate (R5 amendment): two admitted vintages with different values — 455
(0001640147-25-000052) vs 449 (0001640147-26-000008); 461 documentation-only.
`splice_refused: true` — the kernel never splices the vintages into one series.

### decimals_precision — tagged RPO (R3/R4; A25; 3 pins)

Served as tagged, never corrected from prose; RPO is a tagged fact, not a G
metric:

| period | accession | contextRef | value_exact | decimals | scale | raw text | byte offset | member |
|---|---|---|---|---|---|---|---|---|
| 2026-01-31 | 0001640147-26-000008 | c-4 | 9800000000 | -8 | 9 | 9.8 | 1904556 | snow-20260131.htm 729e02a5c711ed37 |
| 2025-01-31 | 0001640147-25-000052 | c-4 | 6900000000 | -8 | 9 | 6.9 | 1810126 | snow-20250131.htm 516c7fc913f21fe3 |
| 2024-01-31 | 0001640147-24-000101 | c-4 | 5200000000 | -8 | 9 | 5.2 | 1619055 | snow-20240131.htm b2ea12cbc6ad67ef |

Each byte offset lands on the `ix:nonFraction` element (decimals="-8",
name us-gaap:RevenueRemainingPerformanceObligation, contextRef c-4) inside the
sentence "As of January 31, <year>, the Company's RPO was $…". The precise
MD&A-table values ($9,771.5M / $6,867.5M / $5,174.7M) are prose and are never
served (A25).

### negative_mapping (4 pins) + errata_absence (3 pins)

| pin | statement | gold-cell evidence |
|---|---|---|
| negative_mapping share_based_compensation_expense ↔ us-gaap:AllocatedShareBasedCompensationExpense | allocated expense is not the cash-flow add-back; never aliased (R3) | every valued SBC cell cites us-gaap:ShareBasedCompensation only (FY2026 1599547000 @ 0001640147-26-000008, contextRef c-1) |
| negative_mapping net_income_loss ↔ us-gaap:ProfitLoss | attribution split; never aliased (R3) | every valued cell cites us-gaap:NetIncomeLoss (FY2026 -1331616000 @ 0001640147-26-000008, contextRef c-1; ProfitLoss FY2026 = -1329035000 exists dimension-free but is never mapped) |
| negative_mapping long_term_debt ↔ us-gaap:ConvertibleDebtNoncurrent | candidate_not_aliased (R3) | long_term_debt 2026-01-31 = typed_absence_verified (missing_standard_fact) |
| negative_mapping short_term_investments ↔ us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent | candidate_not_aliased (R3) | short_term_investments 2026-01-31 = typed_absence_verified (missing_standard_fact) |
| errata_absence R3 long_term_debt code missing_standard_fact, candidate us-gaap:ConvertibleDebtNoncurrent (2279827000 @ byte 1202412 of snow-20260131.htm, "Convertible senior notes, net") | typed absence stands | same cell |
| errata_absence R3 short_term_investments code missing_standard_fact, candidate us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent (1201523000 @ byte 1175675) | typed absence stands | same cell |
| errata_absence E2 total_debt code missing_dependency | never derived from a partial input set; missing inputs named in the cell: short_term_debt, long_term_debt_current, long_term_debt | every total_debt row in both views |

### Refusals routed to E2 (R4; no pin object — refusal rows name them)

8-K EX-99.1 non-GAAP reconciliations and KPI time-series serving are refused in
G and routed to E2; no 8-K is staged or retained (bytes cannot answer). The
CustomerCount gold rows are `unsupported_metric` refusals
("unsupported_metric: no governed catalog contract") — no KPI envelope exists
in G.

### Attestation + envelope

Every file carries `attested:false` and `historical_attestation:
unavailable_until_d2_admission`. No `specialist_pack_result` envelope and no PK
catalogue content anywhere.

## Findings (hand derivation; spec §1)

Rule sources read as data at base commit cbcf823d4045:
`engine/fundamental_forensics/detectors.py` (:27-33 applicability, :52-72
issuer_class_for_sic, :86-99 class gate, :112-119 consecutive window,
:252-302 two-period flow, :263-268 the <2 guard, :305-330 margin compute,
:333-351 working-capital compute, :354-387 capital-intensity compute,
:390-449 accruals detector, :399-404 the <3 guard) and
`config/fundamental_forensics.yml:60-85` (formulas + thresholds). The kernel
was never run.

Applicability: SIC 7372 → issuer_class `software` (detectors.py:70-71).
`DETECTOR_APPLICABILITY` (detectors.py:27-33) admits software for all five
detectors (accruals: every class except bank/insurance) — no class gate fires
(detectors.py:86-99).

Vintage census of the packet basis view (as_filed of 0001640147-26-000037, a
10-Q): only annual forms mint statement vintages
(`ANNUAL_FORMS = {"10-K","10-K/A"}`, normalize.py:25), so the basis view
holds 0 annual vintages (the r2 coverage records 1 total statement vintage —
the quarterly package). Its durations are fiscal quarters (Q2 FY2027
2026-05-01..2026-07-31, Q2 FY2026 2025-05-01..2025-07-31), never annual
periods. Under either reading the guards fire before any metric is read.

| detector | inputs the rule names (gold cell keys) | arithmetic / threshold (config yml) | guard applied | result |
|---|---|---|---|---|
| accruals_trending_up | net_income_loss, net_cash_from_operating_activities, total_assets × 3 consecutive annual period ends | (net_income − operating_cash_flow) / assets per period; TRIGGERED iff last − first ≥ 0.03 AND last > first | len(selected) < 3 (detectors.py:399-404) | not_evaluable, missing input `three_consecutive_annual_periods` |
| capital_intensity_rising | revenue, capital_expenditures, operating_income_loss × 2 consecutive annual ends | capex growth − revenue growth > 10 pp AND capex growth − OI growth > 10 pp | len(selected) < 2 (detectors.py:263-268) | not_evaluable, missing input `two_consecutive_annual_periods` |
| inventory_build | revenue, inventory_net × 2 consecutive annual ends | inventory growth − revenue growth > 15 pp | len(selected) < 2 | not_evaluable, missing input `two_consecutive_annual_periods` |
| margin_compression_despite_revenue_growth | revenue, gross_profit × 2 consecutive annual ends | revenue growth ≥ 3 pp AND current gross margin < prior | len(selected) < 2 | not_evaluable, missing input `two_consecutive_annual_periods` |
| receivables_stretch | revenue, accounts_receivable_net × 2 consecutive annual ends | AR growth − revenue growth > 10 pp | len(selected) < 2 | not_evaluable, missing input `two_consecutive_annual_periods` |

Basis-view input availability (why no arithmetic is reachable): the quarterly
analogue cells exist — revenue Q2 FY2027 1546793000 (0001640147-26-000037,
us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax, contextRef c-5),
gross_profit Q2 FY2027 1036718000 (0001640147-26-000037, us-gaap:GrossProfit,
contextRef c-5), total_assets 2026-07-31 8690459000 (0001640147-26-000037,
us-gaap:Assets, contextRef c-3) — but they are quarterly durations/instants,
not annual periods, and the vintage selector (normalize.py:25) never pairs them
into annual vintages; inventory_net has no valued cell in the basis view at
all. (The earlier r2-sheet draft quoted 2937744000 / 1963169000 for the two
flow cells; the gold cells decide and both quotes are corrected here.)
Derivation artifact: `finding_derivation.json` in the lane output (not
committed).

Counts that follow: findings_triggered 0, findings_clear 0,
findings_not_evaluable 5 (recorded in expected_run_v1.json coverage).

## Kernel defect records (pack_manifest.defects, 87 entries — third commit)

RULINGS.md R-G-1 KERNEL DEFECT: the View B unlinked-vintage cluster (C1) and
its formula cascade (C2) are kernel defects; **gold was never edited to match
the kernel.** Each residual comparison becomes one defects[] entry whose record
shape is (ruling, cluster, kr_label, category, accession, concept, context
{contextRef, unitRef, decimals, scale, dimensioned, nil}, filed_value,
filed_location {accession, member_file, member_sha256, byte_offset, raw_text},
formula or null, gold {value_exact, code, source_accession}, kernel_output
{state, value_exact, kernel_code, reason, provenance_accession},
kernel_observation with its engine cite, repro {test node, env}). The kernel
test turns each entry into xfail(strict=True) for exactly that comparison.

Counts (defects_0001640147.json, applied by apply_defects.py): 87 total —
C1_viewB_unlinked_vintages 67, C2_viewB_formula_unlinked_cascade 20; ruling
R-G-1 for all; comparison value 78 (category value_vs_absence), code 9
(category code_mismatch). C2 entries carry cascade_of links to their C1
dependencies. Repro command:
`FIF_GSRC_STAGE_ROOT=$HOME/lanes/in/orch-g/stage/fif-gsrc ~/lanes/venv/bin/python -m pytest "tests/test_fif_g_pack_kernel.py::test_kernel_cells_match_gold_cells[0001640147-latest_known_as_of-union]" -q -p no:cacheprovider -rxX`.

The kernel observations cite
engine/fundamental_forensics/query.py:5952-5982 (unlinked source vintages
refusal; "Filing time and hashes are not a source-fusion policy") and
engine/fundamental_forensics/raw_ledger.py:1212-1233 (duplicate_group_key
includes accession + body_sha256, so any two filings' facts are distinct
groups).

## Gaps

- Browser evidence pending A0 (§0 gate 6): the packet/page render belongs to
  the seat-side integration step, not this gold lane.
- Kernel-minted hash/id fields in the two expected JSONs hold the not-gold
  placeholder string `kernel_minted_not_gold` (run_id, canonical bytes/sha,
  packet_id, content_sha256, governance ids, receipts digests, cell ids,
  source/mapping/formula digests, occurrence ids, dependency cell ids).
- fiscal_quarter / fiscal_year / calendar_kind in period objects stay
  null/unknown (AAPL witness shape); the fiscal label encodes the issuer FYE.
- View B formula cells carry `dep_source_accessions` (several packages may feed
  the r1 method) instead of relying on a single source.
- 8-K EX-99.1 non-GAAP is not staged (no lane retains 8-K); refused rows name
  it; routed to E2 (R4).
- The G-CENSUS cross-check values are candidate output only (E5); no
  disagreement was escalated from this lane.
