# Defensive nested washouts V12 — research, not live trading

Read RESEARCH_REPORT.md first. Equity inputs end October 8, 2026; evaluation begins January 2018. The V11 entry contract is unchanged. V12 compares frozen setup-low failure, lower momentum, weekly/two-week harvest clocks, and a separately labeled bounded reentry experiment.

Seven exit policies and all core/peer results are retained. Reclaim results are isolated-event counterfactuals, NOT a single-position account. No optimal allocation, calibrated prediction, production installation or merge acceptance is represented.

## Files

- RESEARCH_REPORT.md: method, measured findings, negative findings and qualifications.
- source/: executed V12 analysis and its preserved initial event-only reference.
- tests/: 35 mechanical regression/integration checks.
- specifications/: initial frozen design and explicitly later exploratory extensions.
- results/: derived summary tables readable in GitHub.
- curated_results.json: ten rounded table views used for the reader workbook.
- Full_Source_and_Results.zip: all executed research source, tests, specifications, all derived CSV/JSON outputs and member checksums. No original equity OHLC, FRED raw series, pickle caches, credentials or broker code.

## Reproduction prerequisites

This is an extension of the existing V11 research environment, not a new downloader. It requires the original V11 code and native caches at /tmp/mmx_defensive_empirical_v11_20261011, and the original V1 source/input environment at /tmp/mmx_defensive_compounders_20261009. Original inputs are deliberately not redistributed. Their manifest digest is 69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3.

With those legitimately available inputs, copy source/*.py, tests/*.py and specifications/*.json into a new working folder with an empty results/ subdirectory. Run Python with numpy, pandas and scipy available:

    python -m unittest discover -p 'test_*.py'
    python cycle_failure.py
    python account_replay.py
    python reclaim.py
    python robustness.py
    python horizon_extension.py

Do not treat 340 overlapping event slots or thousands of scenario rows as independent validation. Open account positions remain marked; no forced year-end close; cash earns zero. All examined history was already exposed, and extensions were added sequentially. Source/user-chart parity, external price verification, point-in-time fundamentals, portfolio constraints and genuinely new forward evidence are still outstanding.
