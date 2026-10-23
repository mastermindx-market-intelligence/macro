# RRU-1A: frozen real-data arithmetic-impact diagnostic

Operation: risk-radar-all-regions-upgrade-20260908-sol-001.
Scope: research only; this specification precedes outcome inspection.
Code and data pin: eb9e91961ddc4f3043d0dad358602525e66eccda.
Candidate: existing RRU1A_MISSINGNESS_CANDIDATE.patch; no parameter selection.

## Method
Use all ten existing profiles and actual percentile code. Compare original and
candidate composite_series on identical committed parquet inputs requested by the
existing profile builders. No forward ledger reads or writes, new market-data
fetches, model fitting, production data directory, portfolio or source changes.
Record exact input Git blob, SHA256, rows and first/last observation. Missing
objects are explicit; read/parse failures do not silently become missing data.
Report paired dates, changed percentiles, maximum score-point difference, changed
gated states, latest old/new score and historical/current component coverage.
Complete current inputs do not guarantee parity if missing history changed ranks.
This is current-vintage arithmetic sensitivity, not a point-in-time backtest,
forecast-skill demonstration, calibration approval or source-release permission.

## Write reconciliation
Two native-file requests timed out during path validation. Subsequent read-only
same-device inspection proved the file absent and owned worktree/head unchanged.
The write below uses the same authorized host/process and owned path after that
reconciliation; no effect-unknown write is replayed or moved to another carrier.
