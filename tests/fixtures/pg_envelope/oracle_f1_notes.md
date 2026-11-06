# NOTES — independent oracle, family F1 (five P&G quarterly earnings releases, Exhibit 99.1)

Authored from `./src` raw bytes only. No repository code was read, listed, grepped or run. Helper
scripts live in `./work/` and use only the Python standard library (`re`, `html`, `json`, `hashlib`).

## Method

1. Every `<table` start tag was located in byte order (case-insensitive, nested tables included) and
   numbered 0-based; that number is `table_ordinal`. Table counts: FY24-Q4 = 21, FY26-Q1 = 17,
   FY26-Q2 = 16, FY26-Q3 = 16, FY26-Q4 = 21.
2. Tables were split into rows/cells; each `cell_text` in `oracle_f1.json` was **read mechanically out
   of the cited `<td>`** rather than typed by hand, then the value was parsed with one rule set:
   parentheses = negative, `—`/`—%` = 0.0, otherwise a plain number.
3. A post-build audit (`./work/audit.py`) re-opened the source bytes and confirmed every
   `cell_text`/`row_label` pair in the finished JSON (primary locators **and** every `also_found`
   entry) really occurs in the cited table, and that `headline` and
   `pg_core_reconciliation_context` occur verbatim in the document text. Result: **253 citations
   verified, 0 failures.**

## Ambiguities met, and how they were resolved

### A1. Which table is "the" drivers table
Each release prints the quarter's percent-change drivers **twice**: once in the release body
("Net Sales Drivers", columns `Volume / Foreign Exchange / Price / Mix / Other (2) / Net Sales /
Organic Volume / Organic Sales`, row label `Total P&G`) and again in the financial exhibit
("Consolidated Earnings Information", row label `Total Company` or `TOTAL`). Per the spec the body
percent-change drivers table is **primary** for sales, volume, price, mix, FX and other; the exhibit
copy is recorded in `also_found`. Values agree in all five releases.

### A2. Naming of the two volume columns
The metric names quote "Volume with Acquisitions & Divestitures" and "Volume Excluding Acquisitions
& Divestitures". Those exact labels exist **only in the two Q4 releases** (exhibit drivers table).
In the three interim releases the same table is headed simply `Volume` and `Organic Volume`. In the
interim releases `Volume` is the all-in volume (it is the column that reconciles to net sales after
FX/price/mix/other, and it equals the `Volume with Acquisitions & Divestitures` figure printed a
quarter later). I treated `Volume` = with A&D and `Organic Volume` = excluding A&D. This is noted on
every `pg_total_volume_growth_pct` entry.

### A3. Sign convention on foreign exchange
The drivers table shows FX as a **contribution to reported growth**; the reported-to-organic
reconciliation shows the **same item with the opposite sign** as the deduction used to reach organic
growth. Example FY26-Q1: drivers `Foreign Exchange 1%`, reconciliation `Foreign Exchange Impact
(1)%`. Both are recorded (the second in `also_found`) and `pg_fx_contribution_pp` takes the drivers
sign, per the spec's primary-location rule. The two places disagree in sign but not in substance;
this is the only systematic "disagreement" in the set.

### A4. "Other" in the drivers table vs "Acquisition & Divestiture Impact/Other" in the reconciliation
`Other (2)` in the drivers table is not the same quantity as `Acquisition & Divestiture
Impact/Other (1)` in the reconciliation (the latter is a sales-side plug that includes rounding). The
drivers-table `Other (2)` is used for `pg_other_contribution_pp`, per the spec's primary rule. In
FY26-Q4 the reconciliation also carries an A&D/Other of `(1)%` while the drivers `Other (2)` is `1%`
— different definitions, both recorded where relevant.

### A5. Core EPS when the reconciliation has no adjustments
In three releases the year-ago Core EPS is printed under a column headed `As Reported (GAAP) (1)`
rather than `Core (Non-GAAP)`, because footnote (1) states there were no adjustments for that period
(FY26-Q2: three months ended Dec 31 2024 = $1.88; FY26-Q3: Mar 31 2025 = $1.54; FY26-Q4: Jun 30 2025
= $1.48). FY24-Q4 is the mirror image: the *current* quarter (Jun 30 2025, $1.48) has no adjustments
and sits under `As Reported (GAAP) (1)`, while the year-ago Core of $1.40 sits under `Core
(Non-GAAP)`. In those cases the non-GAAP reconciliation table is still the primary locator, with the
exact printed column header recorded and the footnote explained in `notes`. The highlights table
(`Core EPS` row) is always in `also_found` and agrees in every case.

### A6. `table_title` for tables with no preceding title text
Several exhibit tables are preceded only by another table or a footnote, so there is no preceding
heading. Rule applied: use the table's own printed title line when it has one
("Consolidated Earnings Information", "Reconciliation of Non-GAAP Measures", "CHANGE VERSUS YEAR
AGO"), otherwise the nearest preceding heading ("July - September Quarter Discussion", "April-June
Quarter Business Discussion"), otherwise the preceding caption ("Organic sales growth : The
reconciliation of reported sales growth to organic sales is as follows:"). The highlights table is
identified by its printed period-block label ("Fourth Quarter ($ billions, except EPS)") because the
same physical table also contains the fiscal-year block.

### A7. Adjacent cells holding "$" and "%"
The filer splits currency signs and percent signs into their own `<td>` in some tables (statement of
earnings, reconciliation tables, "CHANGE VERSUS YEAR AGO" blocks). `cell_text` always records the
**exact text of the single cell** holding the value (e.g. `1.48`, `6`, `—`), and `notes` says when a
`$` or `%` sits in the adjacent cell. Where the whole printed value is one cell (`4%`, `(2)%`,
`$1.48` in the highlights table) that full text is recorded.

### A8. Headline spanning two rows
In the three interim releases the headline block is two table rows (sales line, EPS line). They are
recorded joined with `" | "`. In the two Q4 releases the quarter line is a single row (`Q4 ’25: …` /
`Q4 ’26: …`) and is recorded alone; the fiscal-year line on the next row is not part of `headline`.

### A9. `pg_core_reconciliation_context` is narrative, not a cell
The locator points at the section heading and the nearest preceding table (`table_ordinal` of the
drivers table for interim releases, the highlights table for the Q4 releases). `row_label` and
`column_header` are null for that metric. The text chosen is the quarter-specific narrative that
names the excluded items; the standing Exhibit 1 definition of Core EPS and the "Incremental
restructuring" bullet are in `also_found`.

### A10. Fiscal-year material in the Q4 releases
Both Q4 releases print full fiscal-year tables. They were seen and ignored for every quarter metric;
the document field `fiscal_year_tables_present` lists exactly which tables/blocks they are
(tables 2, 4, 7, 8, 12, 18 and 20 in each of the two Q4 files). No `expected` value anywhere in this
oracle comes from a twelve-month figure.

## Printed values that disagree with one another

* **FX sign** — drivers table vs organic reconciliation (see A3). Systematic in all five releases;
  not an error, a sign-convention difference.
* **Rounded vs computed EPS growth** — the printed percentages are the rounded values of the
  underlying per-share figures: FY24-Q4 diluted `17%` printed vs `+16.5%` computed; FY24-Q4 core `6%`
  vs `+5.7%`; FY26-Q1 `21%` vs `+21.1%`, `3%` vs `+3.1%`; FY26-Q2 `(5)%` vs `-5.3%`; FY26-Q3 `6%` vs
  `+5.8%`, `3%` vs `+3.2%`; FY26-Q4 `(15)%` vs `-14.9%`, `(3)%` vs `-3.4%`. `expected` is always the
  **printed** figure.
* **`+` signs on the highlights table** — the two Q4 releases print `+2%`, `+6%`, `(3)%` in the
  highlights table while the drivers/reconciliation tables print `2%`, `6%`, `(3)%`. Same values,
  different typography; both recorded.
* No two places printed a **different number** for the same fact in any of the five releases.

## Judgment calls

* `pg_total_volume_growth_pct` for interim releases taken from the column printed simply as
  `Volume` (A2).
* `pg_fx_contribution_pp` carries the drivers-table sign (A3).
* Primary locators follow the spec's list: drivers table for sales/volume/price/mix/FX/other;
  reported-to-organic reconciliation for organic sales (total and by segment); consolidated statement
  of earnings for GAAP diluted EPS; non-GAAP reconciliation for Core EPS.
* The `%`-change figures for GAAP and Core EPS are primary in the statement of earnings `% Chg`
  column and in the "CHANGE VERSUS YEAR AGO" block of the non-GAAP exhibit respectively; those blocks
  are part of Exhibit 1 and sit immediately beside the reconciliation they summarise.
* Segment organic sales growth is primary in the reported-to-organic reconciliation table (per the
  spec), with the drivers table's `Organic Sales` column in `also_found`. The two agree for all five
  segments in all five releases.
* `expected` values are signed decimals: `(2)%` → `-2.0`, `—`/`—%` → `0.0`.
* All 20 metrics were located with certainty in all five documents, so there are **no nulls** and no
  `absence_reason` values.

## Values at a glance (the quarter, vs same quarter a year earlier)

| file | rep sales | org sales | vol | org vol | price | mix | fx | other | dil EPS | prior | rep g% | core EPS | prior | core g% | Beauty | Groom | Health | F&HC | BFFC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fy2425q4 | 2 | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 1.48 | 1.27 | 17 | 1.48 | 1.40 | 6 | 1 | 1 | 2 | 1 | 1 |
| fy2526q1 | 3 | 2 | 0 | 0 | 1 | 1 | 1 | 0 | 1.95 | 1.61 | 21 | 1.99 | 1.93 | 3 | 6 | 3 | 1 | 0 | 0 |
| fy2526q2 | 1 | 0 | -1 | -1 | 1 | 0 | 1 | 0 | 1.78 | 1.88 | -5 | 1.88 | 1.88 | 0 | 4 | 0 | 3 | 0 | -4 |
| fy2526q3 | 7 | 3 | 2 | 2 | 1 | 0 | 4 | 0 | 1.63 | 1.54 | 6 | 1.59 | 1.54 | 3 | 7 | 1 | 2 | 3 | 3 |
| fy2526q4 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1.26 | 1.48 | -15 | 1.43 | 1.48 | -3 | 4 | 0 | -1 | 0 | -2 |

## Files written

* `./oracle_f1.json` — the oracle (5 documents × 20 metrics).
* `./work/*.py` — extraction/verification helpers (standard library only).
