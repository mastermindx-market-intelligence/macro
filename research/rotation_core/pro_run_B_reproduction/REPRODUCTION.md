# PRO-RUN B reproduction rerun — REPRODUCTION.md

Machine rerun of Macro commit `2afbd280fe09aae929dbf9ce3be86dcccfd82db3`
(`research/rotation_core/pro_runs/B/`, remote branch `pro-run/rotation-b-20261111-reconcile`)
to check that the committed code reproduces its own committed `out/` tables.
No data dated after 2019-12-31 entered any computation, input file or comparison. One disclosure:
during initial parquet schema inspection, `df.tail(3)` displayed the UNRATE store series' last
three monthly labels (2026-08/09/10, values 4.1/4.2/4.1) before truncation; no post-2019 value
was used or printed anywhere else, and the series served to the study was truncated at
2019-12-31 in memory first. No git branch was modified and nothing was pushed; the Macro
worktree was used read-only via `git show`/`ls-tree`.

## 1. Commands executed

```bash
R=/home/ubuntu2/.t3/worktrees/Macro/rotation-core            # read-only blobless worktree
PY=/home/ubuntu2/.t3/worktrees/Macro/.venv-prophet/bin/python
B=/home/ubuntu2/tmp/rotation-core/pro_runs/B_rerun

# fetch attempted: branch ref no longer on origin (commit object already present locally)
git -C $R fetch origin pro-run/rotation-b-20261111-reconcile   # -> "couldn't find remote ref"
git -C $R cat-file -t 2afbd280fe                               # -> commit (present)

# extract study at pin (per file, via git show) -> $B/src/ ; committed tables kept at $B/committed_out/
for f in $(git -C $R ls-tree -r --name-only 2afbd280fe research/rotation_core/pro_runs/B/); do ...; done

# input preparation ($B/data/): date-field-only truncation of the two files that run past 2019
$PY  # trunc script: drop lines whose first comma field is an 8-digit date > 20191231; no other field parsed
#   x/F-F_Research_Data_Factors_daily.csv -> data/factors.txt   (kept 24650, dropped 1695 post-2019 lines)
#   x/F-F_Momentum_Factor_daily.csv        -> data/momentum.txt (kept 24558, dropped 1695)
#   le2019/{49,12,17}_Industry_Portfolios_Daily_le20191231.csv -> data/ind{49,12,17}.txt (verbatim; end 20191231)

cd $B && $PY assert_maxdates.py          # ADDED assertion: every input series max date <= 2019-12-31
cd $B/src && $PY -m unittest -v test_integrity   # 12 tests OK
cd $B/src && $PY run_study.py            # COMPLETE: 40 rule/segment rows, 30 primary slots
cd $B/src && $PY verify_results.py       # independent vectorized check, max_abs_error R1=0.0 R3=0.0
cd $B &&   $PY compare.py                # cell-by-cell comparison vs committed_out/ (this report)
```

Not run: `acquire.py` (downloads from the internet — out of scope; local inputs used instead) and
`render_report.py` (renders the issue comment from `out/`; produces no table). `test_integrity.py`
is self-contained (synthetic fixtures) and needed no raw inputs.

## 2. Adapter changes (full diff in `adapter_changes.diff`; original files in `pin_ref/`)

| # | file | change |
|---|------|--------|
| 1 | `inputs.py` | `RAW` points at `../data` (local truncated copies) instead of `./raw` downloads |
| 2 | `inputs.py` | `fred()`: `UNRATE` served **in memory** from repo blob store `git -C <repo> show 4d49b23a8f:data/fred/UNRATE.parquet`, truncated at 2019-12-31 before use (FRED content never written to disk); `BAA`, `BAA10YM`, `GS10`, `TB3MS` absent from the store on this machine -> returned as empty DatetimeIndex series so affected rules are marked unavailable |
| 3 | `inputs.py` | `shiller()`: `shiller.xls` absent on this machine -> empty frame with expected schema (R9/R10 and rate diagnostics become unavailable) |
| 4 | `inputs.py` | `coverage()`: skip French/FRED sources whose input file is absent locally |
| 5 | `verify_results.py` | skip R1–R4 rules with no computable path (R2/R4 need BAA10YM) |
| 6 | `episodes.py` | `rate_diagnostics()`: empty-frame guard (no macro feature states computable here) |

No allocation rule, threshold, cost, date range or statistical setting was touched.

## 3. Input sha256

| input | sha256 |
|---|---|
| `data/french/F-F_Research_Data_Factors_daily_CSV.zip` | `96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89` **== committed run_manifest** |
| `data/french/F-F_Momentum_Factor_daily_CSV.zip` | `e56d5bc845544e2993e77353b12c611cfce3149ef754f9b59fc67904ddadd369` **== committed run_manifest** |
| `data/french/le2019/49_Industry_Portfolios_Daily_le20191231.csv` (= `data/ind49.txt`) | `8fe0aba40cefa7ccf9464e970dc30ce2ab12ac67feb4089582905485a5dceb71` |
| `data/french/le2019/12_Industry_Portfolios_Daily_le20191231.csv` (= `data/ind12.txt`) | `dd8171610a4a0bbfad55f57f7dd2433d0c18d5825efb671e6a15ceb33f0bff96` |
| `data/french/le2019/17_Industry_Portfolios_Daily_le20191231.csv` (= `data/ind17.txt`) | `229427433fd280b678c5f69ac374546e3f3bea687eb754166d87b89729a9d483` |
| `data/french/x/F-F_Research_Data_Factors_daily.csv` (source of truncated `data/factors.txt` = `746f1f9bcaf13fe680917a29f4215f8e365580c5a82e54230459e89c29274de3`) | `3f7910502dd6f188748210e5145d95642de1d8cff56c2cf0fa85985299610ff0` |
| `data/french/x/F-F_Momentum_Factor_daily.csv` (source of truncated `data/momentum.txt` = `7679f508ab7921dcb436910495bc3e43db7a5b17636f2a991a4953593a1b52a3`) | `00b9291e5c7d5c35d4a94b62782a6fe2c0b25ba7999896016474d6d19757b0b4` |
| FRED `UNRATE.parquet` blob at pin `4d49b23a8f` (in memory only) | `fe9f62448d6613b92ef0e6e52d80be17d72f7a595fd7fc36fdc33d721d0b011b` |

Unavailable on this machine (not in the repo store at `4d49b23a8f`, not local, downloads not
permitted): FRED `BAA`, `BAA10YM`, `GS10`, `TB3MS`; Shiller `ie_data.xls`; Yahoo SPX json;
French `size` and `ind49monthly`.

## 4. Data max-date assertion output (`assert_maxdates.py`, added for this rerun)

```
factors/   24643 rows  max 2019-12-31  OK      ind17 VW 24643  2019-12-31  OK
momentum/  24542 rows  max 2019-12-31  OK      ind17 EW 24643  2019-12-31  OK
ind12 VW   24643 rows  max 2019-12-31  OK      ind49 VW 24643  2019-12-31  OK
ind12 EW   24643 rows  max 2019-12-31  OK      ind49 EW 24643  2019-12-31  OK
BAA/BAA10YM/GS10/TB3MS  0 rows  OK-empty       UNRATE 864 rows max 2019-12-01 OK
shiller.xls absent -> OK-empty ; spx_yahoo.json absent -> OK-empty
ASSERTION PASSED: no input series on this machine contains any date after 2019-12-31.
```

Parsers additionally discard post-2019 rows by date field before parsing values (their own
`assert ... <= CUTOFF`), and 12/12 `test_integrity` tests pass. Rerun session count 24643 ==
committed manifest `data_sessions` 24643; `calm_years` list identical (39 years).

## 5. Cell comparison vs committed tables at `2afbd280fe`

Method: rows aligned on natural keys, every numeric cell compared; tolerance = identical at the
tables' printed precision (`%.10g`). Runtime here: python 3.12.3 / numpy 2.5.4 / pandas 3.1.1
(committed run: 3.12.14 / 2.3.5 / 2.2.3).

| table | cells compared | matched | mismatch | not-computable cells (rows) |
|---|---|---|---|---|
| results.csv | 1033 | 1033 | 0 | 1005 |
| primary_era_results.csv | 456 | 456 | 0 | 615 |
| partial_segments.csv | 348 | 348 | 0 | 174 (3 rows) |
| false_pivots.csv | 60 | 60 | 0 | 60 |
| passive_references.csv | 108 | 108 | 0 | 0 |
| h1_common_sample.csv | 0 | 0 | 0 | 108 (9 rows) |
| episodes.csv | 270 | 270 | 0 | 251 |
| episode_relative.csv | 150 | 150 | 0 | 90 |
| episode_transitions.csv | 742 | 742 | 0 | 395 (132 rows) |
| factor_diagnostics.csv | 36 | 36 | 0 | 0 |
| rate_conditions.csv | 0 | 0 | 0 | 92 (23 rows) |
| coverage.csv | 26 | 26 | 0 | 16 (8 rows) |
| missing_observations.csv | 0 (row-identical) | — | 0 | 0 |
| **TOTAL** | **3229** | **3229** | **0** | **2806** (175 rows) |

- `factor_diagnostics.csv`, `passive_references.csv`, `missing_observations.csv` are **byte-identical**
  (sha256) to the committed files.
- `independent_checks.json`: rerun `{R1: 0.0, R3: 0.0}`, checked_rows `{R1: 24443, R3: 17882}` —
  identical to committed for the computable rules (committed also lists R2/R4, which need BAA10YM).
- `run_manifest.json`: rule/bootstrap/seed/cutoff/data_sessions/calm_years identical; `source_manifest`,
  python/numpy/pandas versions differ (fewer local inputs, different runtime) — informational fields.
- Non-numeric cells (statuses, dates, labels) also compared: no differences among computable rows;
  no rerun-only rows anywhere.

### Mismatches

**None.** Every numeric cell the rerun could produce (3,229 across 13 tables) matches the committed
value exactly at printed precision. `compare_mismatches.txt` is empty ("NONE").

### Not-computable inventory (missing inputs, not value disagreements)

All 2,806 cells / 175 rows trace to inputs that do not exist on this machine and may not be
downloaded: rules R2/R4/R6 (FRED BAA10YM credit), R9/R10 (Shiller), all 9 `h1_common_sample.csv`
rows and all 23 `rate_conditions.csv` rows (R2/R4 paths; Shiller/TB3MS features), 132
`episode_transitions.csv` rows and the macro-flag/spx columns of `episode_relative.csv`, 8
`coverage.csv` source rows (size, ind49monthly, BAA, BAA10YM, GS10, TB3MS, Shiller, S&P500_price),
and the corresponding rule rows in the other tables. Full list: `compare_not_computable.txt`.

## 6. Verdict

**REPRODUCED — all 3,229 computable numeric cells identical to the committed tables at printed precision, 0 mismatches; 2,806 cells (rules R2/R4/R6/R9/R10 and macro/rate/H1 tables) were not computable on this machine because FRED BAA/BAA10YM/GS10/TB3MS, the Shiller workbook, the SPX json and French size/ind49monthly inputs are not present locally and downloading was out of scope.**
