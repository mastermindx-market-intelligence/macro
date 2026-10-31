# Durable pivot confluence study

This completed research tests weekly/two-week Stoch RSI and MACD confluence,
shorter-timeframe agreement and disagreement, auxiliary technical filters, and
durable local bottoms/tops across a fixed 50-instrument cohort.

Read `deliverables/Durable_Pivot_Research.md` for findings and
limitations. Read `DATA_DICTIONARY.md` before interpreting a percentage. The
experiment measures pivot detection, not trade win rate or permission for
aggressive position sizing.

## Evidence supplied in this package

- Complete narrative report and four vector figures. The PDF and ZIP were delivered separately.
- Full 2,434-rule development/validation grid and 34 frozen final-period rules.
- Group/regime/year, uncertainty, outcome, bar-phase and price-basis diagnostics.
- Fixed waiting policies and standardized same-time comparisons.
- Protocols written before the relevant outcome rankings, selection lock and
  input/source audits.
- Core calculations, acquisition, diagnostic and report-generation code.

The full raw snapshot, normalized OHLCV files and event caches are retained on
the connected computer in:

`/Volumes/Mastermind 2/agent-workspaces/macro/web/durable-pivot-confluence-research-20261021/research/durable_pivots_20261021`

Those complete price files and caches are not embedded in this downloadable
package. The included `illustrative_prices.csv` is only the named chart windows.
The original manifest records exact hashes, cutoff, provider receipts and
normalization basis. Re-downloading later public-provider history can differ
after corporate-action or vendor revisions; use the retained snapshot for exact
reproduction. Canonical numeric content hashes are also supplied, independent
of parquet serialization.

## Run in the original research workspace

The core study intentionally reuses the existing Macro repository's canonical
`engine.trial_ledger.TrialLedger` implementation, confined to this study's local
ledger. It expects the script at `research/durable_pivots_20261021/study.py` in
that repository. The package does not create a second independent ledger owner.

Required numerical packages: numpy, pandas, pyarrow. Acquisition additionally
uses curl_cffi. Report rendering uses matplotlib, Pillow, reportlab and pypdf.
The host calculation used Python 3.14, numpy 2.5.2 and pandas 3.0.5. Report generation
used the provided Python runtime; no production signals or trading code changed.

Core verification without input data or repository ledger:

```bash
python study.py --self-test --out verification
```

Full research in the Macro worktree, using retained exact inputs:

```bash
python research/durable_pivots_20261021/study.py \
  --manifest research/durable_pivots_20261021/data/input_manifest.json \
  --out research/durable_pivots_20261021/results
```

The original run first wrote feature caches using `--features-only`; its next
run used `--reuse-cache` and froze selection before writing final tables. Do not
claim a fresh run is prospectively held out after inspecting these results.

The registered robustness analyses then used:

```bash
python robustness.py --out results --register
python robustness_batch.py --manifest data/input_manifest.json --out results
python mechanics.py --manifest data/input_manifest.json --out results
python export_diagnostics.py
```

For GitHub rendering, the four figure references use SVG. The manuscript and figures are generated from saved result tables by
`build_figures.py`, `write_report.py`, and `build_pdf.py`. They can be rerun from
this package layout without the full input snapshot. For the core study,
preserve the original directory structure and canonical ledger dependency.

## Interpretation safeguards

- Read `n`, `qualified_n`, primary success and pivot coverage together.
- The primary near-pivot limit is 2 ATR; the 3 ATR sensitivity materially changes
  weekly-rule rankings. Neither should be selected after the fact to declare a
  universal winner.
- A late crossover can show high survival of an old low while failing the
  near-pivot objective. That is not evidence the crossover has no possible use.
- Pointwise block intervals are approximate and not selection-adjusted. Tiny
  qualified samples, correlated assets and zero-success arms limit inference.
- The fixed surviving cohort is not a point-in-time all-equity universe.
- The study establishes neither trade expectancy nor an aggressive allocation
  or liquidation policy.
