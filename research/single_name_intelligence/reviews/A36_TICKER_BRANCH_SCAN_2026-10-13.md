# A36 ticker-branch scan — 2026-10-13

SNI-local DRAFT evidence toward acceptance row A36, "US and Mag-7 packs
need no ticker-specific strategy branches". The scanner consumes
owner-supplied profile YAML (ticker, listing, sector_etf). It does not
mint identity ids and does not feed a rank, gate, size, signal,
escalation, or trade path. Every authority flag in the scanner is
literal false.

Pinned on worktree base `d8e1d87e5436586c17ced147edab5e013bb2c069`.

## Summary

Today's computed answer: the US/Mag-7 generalization surface
(`us_stress/`, `us_transfer/`, `common/`, `evaluation/`) has **no**
ticker or company literal in a decision position. The whole SNI Python
tree has **eight** decision-position findings, all in S1/S2
Alibaba/Tencent reference-study code, all pinned as
`REFERENCE_STUDY_EXPECTED`. `ALLOWLIST` is empty. No real US/Mag-7
strategy branch was found, so test 01 is not xfailed.

| Measure | Count |
|---|---|
| Python files scanned | **32** (`research/single_name_intelligence/**/*.py`, tests excluded) |
| `TICKER_LITERALS` (hand-typed + profile) | **29** tokens |
| Profile-loaded tokens | **11** (7 Mag-7 tickers + NASDAQ + XLK/XLC/XLY) |
| Findings, us_stress/us_transfer/common/evaluation | **0** (clean) |
| Findings, whole SNI tree | **8** |
| Verdict: clean | **0** findings |
| Verdict: reference-study-expected | **8** |
| Verdict: allowlisted | **0** |
| Verdict: real (US/Mag-7 strategy branch) | **0** |
| Row A36 | **PARTIAL** |

Company differences for the seven Mag-7 names live in
`research/single_name_intelligence/us_stress/profiles/*.yml`. The
held-out onboarding test still shows a new profile works; this scan
shows the existing seven are not special-cased in Python.

## Rules

Stdlib `ast` only. Scanned modules are never imported. A finding is a
ticker/company string (case-insensitive membership in
`TICKER_LITERALS`) in a decision position:

| Kind | Decision position |
|---|---|
| `compare` | `ast.Compare` with a ticker string constant on either side, including `in` / `not in` against a tuple, list, or set of constants |
| `match` | `match` case pattern constant |
| `dispatch` | dict literal whose keys include a ticker constant, when that dict is subscripted or `.get()`-ed in the same module |
| `call_branch` | `str.startswith` / `endswith` / `upper()==` against a ticker constant |

Not findings: docstrings, comments, f-strings used only for messages
or paths, module-level constants that are never compared. Path strings
such as `data/yahoo/BABA.parquet` are not ticker literals.

`TICKER_LITERALS` is the hand-typed Mag-7 + HK reference-product set,
union every `ticker` / `listing` / `sector_etf` value read at scan time
from `us_stress/profiles/*.yml` and
`config/single_name_intelligence/coverage_profiles/{alibaba,tencent}.yml`.
PyYAML is used when importable; otherwise the stress_set indent-based
subset parser is copied into the scanner so the scan never imports a
scanned module. Unreadable profiles are recorded in `PROFILE_LOAD_GAPS`
and skipped.

`ALLOWLIST` is `(path, kind, literal, justification)` and is only for
findings that are genuinely not strategy branches. A stale entry
(matches nothing) is an error. S1/S2 reference-study findings are
never allowlisted.

## Scope

Default `scan_tree` walks every `*.py` under
`research/single_name_intelligence/`, tests excluded, using the same
`sorted(base.rglob(...))` file-walking idiom as
`tests/test_sni_program_invariants.py`. That invariant scanner already
checks authority-false, owner-supplied identity ids, split dates,
horizons, and secret-shape substrings. This scan does not duplicate
those checks.

Test 01 restricts the walk to `us_stress/`, `us_transfer/`, `common/`,
and `evaluation/`. Test 02 walks the whole SNI Python tree.

## Findings table

| Path | Line | Kind | Literal | Verdict |
|---|---|---|---|---|
| `event_response/s2_seal.py` | 153 | dispatch | `alibaba` | reference-study-expected — S2 seal dispatch of the graded US ADS leg for the Alibaba issuer group |
| `event_response/s2_seal.py` | 154 | dispatch | `tencent` | reference-study-expected — S2 seal dispatch marking the Tencent issuer group census-only |
| `event_response/s2_selection.py` | 156 | compare | `BABA` | reference-study-expected — S2 earnings census selects Alibaba ADS rows |
| `event_response/s2_selection.py` | 240 | compare | `alibaba` | reference-study-expected — S2 coverage-census report label E1 vs E2 |
| `residual/run_s1.py` | 448 | dispatch | `KWEB` | reference-study-expected — S1 P03 factor-path table keys the KWEB sector series |
| `residual/s1_report.py` | 425 | compare | `TCEHY` | reference-study-expected — S1 exemplar table prints the UNRESOLVED TCEHY row |
| `residual/s1_synth.py` | 31 | dispatch | `KWEB` | reference-study-expected — S1 synthetic-frame builder maps KWEB onto a fixture path |
| `residual/s1_synth.py` | 77 | compare | `KWEB` | reference-study-expected — S1 synthetic frames attach a US close_price column on KWEB |

`ALLOWLIST` is empty. No entry is stale. No finding in
`us_stress/`, `us_transfer/`, `common/`, or `evaluation/` exists to
replace with a config-driven profile field.

The Alibaba/Tencent reference product is those two companies. The
eight rows above are the study's own issuer dispatch and census
filters, pinned so a *new* ticker branch fails the test and a
*disappeared* expected row also fails.

## Mutation proof

Done in this worktree and reverted before commit.

**(m1)** Appended to `us_stress/stress_set.py`:

```python
def _mut(ticker):
    if ticker == "NVDA":
        return 2.0
    return 1.0
```

Test 01 failed, naming `stress_set.py` and `NVDA` (kind `compare`).
Reverted.

**(m2)** Appended instead:

```python
_TABLE = {"AAPL": 1.0}
def _mut2(t):
    return _TABLE.get(t)
```

Test 01 failed with kind `dispatch` (literal `AAPL`). Reverted.
Tree green after both reverts.

## What this does NOT prove

This is a static scan of string constants in decision positions. It
does not see a branch on a value read from data, for example
`if row["symbol"] == profile_field`, and that is acceptable: the
company difference then lives in the profile, which is the A36 shape.

It also does not see a lookup of an *imported* dispatch table using a
ticker constant as the index when the dict literal lives in another
module (`GRADED_LEG_LABEL["alibaba"]` in `s2_splits.py` is the S2
table already reported at `s2_seal.py:153-154`).

It says nothing about the U1-U4 product packs, which are not built
and stay gated. Row A36 stays PARTIAL.

## Gaps

* Profile YAML on this checkout loaded (0 `PROFILE_LOAD_GAPS`). Mag-7
  tickers AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA plus listing
  NASDAQ and sector ETFs XLK, XLC, XLY came from the YAMLs.
* Coverage profiles for Alibaba/Tencent have no `ticker` / `listing` /
  `sector_etf` keys in that shape; their `local_code` values are not
  harvested (the frozen spec names those three fields only).
* Integer `700` is not a string constant and is not a finding.
* `GOOG` is hand-typed; the GOOGL profile carries `GOOGL` only.
* U1-U4 packs are absent. A36 remains PARTIAL until those packs exist
  and this scan stays clean on them.
