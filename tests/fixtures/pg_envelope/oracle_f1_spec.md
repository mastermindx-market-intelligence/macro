# Independent oracle: expected bindings for five P&G quarterly earnings releases (family F1)

You are an INDEPENDENT reader. Your answers become the frozen truth that production software is checked against, so the software must never be the source of them.

## Independence rules (binding)

- Work ONLY from the five files in `./src/`: the original SEC 8-K Exhibit 99.1 files, exact bytes.
- Never open, read, grep, list or import anything outside this directory. There is no repository here for you to consult, and you must not look for one.
- You may write helper scripts in `./work/` using only the Python standard library (`html.parser`, `re`, `json`, `hashlib`). You may also read the HTML directly.
- Do not guess. When a value cannot be located with certainty, set `expected` to null with `absence_reason: "not_located"` and explain in `notes`.

## Documents

| file | accession | fiscal year | fiscal quarter | quarter start | quarter end |
|---|---|---|---|---|---|
| fy2425q4amj8-kexhibit991.htm | 0000080424-25-000067 | 2025 | 4 | 2025-04-01 | 2025-06-30 |
| fy2526q1jas8-kexhibit991.htm | 0000080424-25-000240 | 2026 | 1 | 2025-07-01 | 2025-09-30 |
| fy2526q2ond8-kexhibit991.htm | 0000080424-26-000006 | 2026 | 2 | 2025-10-01 | 2025-12-31 |
| fy2526q3jfm8-kexhibit991.htm | 0000080424-26-000056 | 2026 | 3 | 2026-01-01 | 2026-03-31 |
| fy2526q4amj8-kexhibit991.htm | 0000080424-26-000093 | 2026 | 4 | 2026-04-01 | 2026-06-30 |

Record the sha256 of each file's raw bytes (`hashlib.sha256(open(f,'rb').read())`).

## What to extract, per document

Every metric is about THE QUARTER, meaning the three months ended on the quarter-end date above, compared with the same three months a year earlier. Fiscal-year (twelve-month) figures are never the answer. When the quarter is Q4, the release also prints fiscal-year tables; ignore them, except to note that you saw them.

| metric | meaning | unit |
|---|---|---|
| pg_reported_sales_growth_pct | Total company net sales growth, reported (GAAP), quarter vs year-ago quarter | percent |
| pg_organic_sales_growth_pct | Total company ORGANIC sales growth for the quarter | percent |
| pg_total_volume_growth_pct | Total company volume growth INCLUDING acquisitions and divestitures ("Volume with Acquisitions & Divestitures") | percent |
| pg_organic_volume_growth_pct | Total company volume growth EXCLUDING acquisitions and divestitures ("Volume Excluding Acquisitions & Divestitures") | percent |
| pg_price_contribution_pp | Total company price impact on net sales growth | percentage points |
| pg_mix_contribution_pp | Total company mix impact | percentage points |
| pg_fx_contribution_pp | Total company foreign exchange impact | percentage points |
| pg_other_contribution_pp | Total company "Other" impact | percentage points |
| pg_diluted_eps | GAAP diluted net earnings per common share, the quarter | USD per share |
| pg_prior_diluted_eps | the same measure for the year-ago quarter, as printed in this release | USD per share |
| pg_reported_eps_growth_pct | the % change in quarterly GAAP diluted EPS as LITERALLY PRINTED in this release (null + "not_disclosed" when not printed) | percent |
| pg_core_eps | Core EPS (P&G's non-GAAP measure), the quarter | USD per share |
| pg_prior_core_eps | Core EPS for the year-ago quarter, as printed in this release | USD per share |
| pg_core_eps_growth_pct | the % change in quarterly Core EPS as LITERALLY PRINTED (null + "not_disclosed" when not printed) | percent |
| pg_core_reconciliation_context | the release's text explaining how quarterly Core EPS differs from GAAP diluted EPS (which items are excluded) | text, at most 400 characters verbatim |
| pg_beauty_organic_sales_growth_pct | Beauty segment organic sales growth, the quarter | percent |
| pg_grooming_organic_sales_growth_pct | Grooming segment organic sales growth | percent |
| pg_health_care_organic_sales_growth_pct | Health Care segment organic sales growth | percent |
| pg_fabric_home_organic_sales_growth_pct | Fabric & Home Care segment organic sales growth | percent |
| pg_baby_feminine_family_organic_sales_growth_pct | Baby, Feminine & Family Care segment organic sales growth | percent |

Value conventions:
- Numbers are signed; parentheses mean negative: "(2)%" is -2.0.
- "—%" or "—" printed where a number belongs is 0.0, with `cell_text` recording the dash.
- EPS values are plain numbers, e.g. 1.48.

## Locators (for every value you record)

- `table_ordinal`: the 0-based index of the table's `<table` start tag among ALL `<table` start tags in the file, in byte order, case-insensitive, nested tables included.
- `table_title`: the nearest title text that precedes the table, verbatim, trimmed to 120 characters.
- `period_header`: the header text naming the period of the value's column, e.g. "Three Months Ended June 30, 2026" or "April - June 2026".
- `row_label` and `column_header`: exactly as printed.
- `cell_text`: the printed cell text, e.g. "(2)%", "$1.48", "4%".

When the same fact is printed in more than one place (a drivers table and a reconciliation table, a highlights table and a statement), put the primary location in `locator` and every other one in `also_found`, each with its own `cell_text`. Say in `notes` whether they agree. The primary is:
- the quarter's detailed table: the percent-change drivers table for sales, volume, price, mix, FX and other;
- the reported-to-organic reconciliation table for organic sales;
- the consolidated statement of earnings for GAAP EPS;
- the non-GAAP reconciliation table for Core EPS.

Also record, per document, the headline line near the top, verbatim; for example, it names Net Sales, Organic Sales, Diluted EPS and Core EPS for the quarter.

## Output

Write `./oracle_f1.json` (valid JSON, `json.load`-able) in this shape:

```json
{
  "family": "F1_pg_workiva_ex991",
  "authored_by": "<your model name>",
  "independence": "authored from ./src raw bytes only; no repository code read or run",
  "documents": [
    {
      "file": "...", "sha256": "...", "accession": "...",
      "fiscal_year": 2026, "fiscal_quarter": 4, "quarter_start": "2026-04-01", "quarter_end": "2026-06-30",
      "headline": "...",
      "metrics": {
        "pg_reported_sales_growth_pct": {
          "expected": 2.0, "unit": "percent", "absence_reason": null,
          "cell_text": "2%",
          "locator": {"table_ordinal": 0, "table_title": "...", "period_header": "...", "row_label": "...", "column_header": "..."},
          "also_found": [],
          "notes": ""
        }
      }
    }
  ]
}
```

- Every document carries all 20 metrics.
- When absent: `"expected": null`, `absence_reason` one of `"not_disclosed" | "not_located" | "ambiguous"`, and `locator` null.

Also write `./NOTES.md`, listing:
- every ambiguity you met;
- every place two printed values disagree;
- every judgment call, with its reason.

## Return (final message)

End with these five sections:
- STATUS (`DONE | PARTIAL | BLOCKED`);
- RESULT: counts of values found and absent per document;
- EVIDENCE: the `python3 -c "import json;json.load(open('oracle_f1.json'))"` output, and the sha256 list;
- GAPS;
- DEVIATIONS from this spec.
