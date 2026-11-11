# PRO-RUN B — public-history risk pivots and defensive rotation

Research commission return for Macro issue #11014. Rules and trial count are in
`PROTOCOL.md`, frozen at `ba5ae1e353c6f9738bbf8936b9032e71c747b9ba` before outcomes.
`CLARIFICATIONS.md`, `EXECUTION_NOTES.md` and `MISSING_DATA.md` record pre-outcome
implementation definitions. No rule or threshold was changed after results.

The study covers available observations through 2019-12-31. It cannot supply an
exact public daily stock-equal-weighted market series or restore missing French
49-industry returns. Those gaps are marked unavailable, not imputed.

## Reproduce

Use Python 3 with numpy, pandas, scipy and xlrd (tested versions in run_manifest).

```bash
python acquire.py
python -m unittest -v test_integrity
python run_study.py
python verify_results.py
python render_report.py --commit <code-and-result-commit>
```

Raw source downloads go only in `raw/`. Neither those files nor the local daily
audit caches belong in Git. The repository contains code, protocol and small
derived result tables. The acquisition script records errors rather than silently
inventing unavailable sources. Shiller's official download link can change; a new
source revision must be recorded and matched against the saved input hashes.

## Output contract

- `out/primary_era_results.csv`: 30 requested rule/era slots. Any unidentified
  full-era path has NA metrics and p=1 in the fixed testing family. Macro rules
  start only at their actual input availability, with dates explicitly recorded.
- `out/partial_segments.csv`: nine descriptive continuous segments selected
  only on input missingness. These are not the full requested eras or primary tests.
- `out/results.csv`: working combination of era/segment and descriptive pooled
  results. Always read `coverage_status`, `start` and `end` before using a row.
- `out/episodes.csv`: 120 rule/episode rows with exit/re-entry and separate
  decline/recovery eligibility. PRE and ON may have negative offsets; NONE is a
  failure to pivot within the specified window. NA means unavailable evidence.
- `out/episode_relative.csv`: fixed episode anchors, gross C/D comparisons,
  derived macro regime flags, member counts and descriptive S&P price-return
  cross-check. Raw price/rate levels are excluded from the published tables.
- `out/episode_transitions.csv`: every within-window exit plus a designated PRE
  exit; prior63 and next63 relative returns. Not a set of independent trials.
- `out/h1_common_sample.csv`: paired confluence-versus-single descriptive checks.
- `out/false_pivots.csv`: mechanically defined exits per complete eligible calm year.
- `out/rate_conditions.csv`: overlapping month-end regime diagnostics; no causal test.
- `out/passive_references.csv` and `out/factor_diagnostics.csv`: passive allocation
  and factor-exposure diagnostics, not searched trading variants.
- `out/coverage.csv`, `out/missing_observations.csv`, `out/run_manifest.json`,
  `out/independent_checks.json`: source coverage, data holes, hashes and validation.

All reported performance is historical simulation on retrospective public data.
Industry portfolios are synthetic, current-vintage macro is not real-time history,
and costs omit unobserved trading inside the published portfolios. No result
authorizes trading, production rankings, a release or access to the sealed sample.

Transaction costs use the frozen target-notional approximation: the per-side fee
multiplies the equity-weight change before fees, then reduces wealth
multiplicatively. Exact post-fee traded-notional financing is not solved. Both
base and doubled-cost results use the same convention. The report states this
limitation; it does not claim exact fee-funded trade accounting.

## Authority and scope

GitHub-native branch: `pro-run/rotation-b-20261111`, based on Macro
`71405417a0ff9dfc615654deea6ea44a5305f735`. Protected procedure pin: Mastermind
`c42e812e4a754d7a95efd954441d3f01607a7fb5`, skillpack 1.0.1. Only this research
directory is modified. One final issue comment is authorized; no PR, merge,
production effect or external message is part of this commission.
