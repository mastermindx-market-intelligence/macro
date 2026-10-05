# R3 — chronological reconstruction and recipient-specific risk

Operation `risk-regime-mechanism-research-20260927-sol-001`; continuation of #8128 / Draft-HOLD #8133. Source/data pin remains `f6dae649ee6d32ec65a95ccea411b205d0b0bc45`, end date 2026-09-25. R1/R2 negative evidence remains unchanged. No model, policy or production promotion.

## Current action boundary

On this continuation a Studio source-inspection call covering engine/axes.py, engine/regime.py, engine/risk_radar_backtest.py and engine/inputs.py was explicitly blocked with 'could not determine the safety status'. No modification was in that command. Do not repeat/rephrase it or move those requested reads to another carrier. This leaves the original exact-incumbent comparison and full source-native input reconstruction open. Independent work below uses the already inspected regime_one endpoint, previously qualified archives, and new recipient outcome data, not the denied source reads. Prior MOVE denied integration remains untouched.

## A. Chronological reconstruction contract

Build a pure research adapter, not a new live regime engine/store. It calls a supplied existing regime endpoint separately on each admissible knowledge snapshot. Inputs and parameters must be cut before the decision; generated full-history probabilities must never be treated as issued historical values.

For date-only ALFRED data, select per-observation-period the latest value whose realtime_start is strictly earlier than the decision date and whose validity interval has not expired at the conservative prior-date cutoff. Preserve period and release dates separately. Reject conflicting duplicate period/vintage rows, future periods, bad values, non-full-vintage payloads, malformed intervals and missing required observations. Later revisions may change a later assessment, but must not rewrite an earlier assessment. Hash the selected knowledge separately from the full archive: adding later rows must not change the historical knowledge digest.

For the existing `_causal_filtered_pquad`, use the unmodified function's endpoint on score rows through each requested date, not its retrospective history. Retain its original data requirements and source SHA. A SciPy Gaussian-density reference may replace the unavailable hmmlearn density as in R2, explicitly labeled dependency-isolated and not full production parity. Do not claim source-vintage qualification merely because parameters are prefix-limited. The legacy score archive remains current-snapshot reconstruction; its replay is a PARAMETER_ONLY_DIAGNOSTIC with no forecast/capital authority.

Native verification dates: quarter-end source sessions from 2015 through 2026-09-25 plus 2020-02-19, 2020-02-28, 2020-03-09, 2020-03-23, 2020-04-06, 2021-05-10, 2021-06-30, 2022-10-14, 2023-03-08, 2023-03-13. Retain all available historical score prehistory. Compare endpoint-for-date outputs on a truncated source archive and an extended one. A non-production batch optimization is permitted only with direct original-endpoint equality evidence; it may not silently change fit cadence, state mappings or priors.

## B. Recipient/target mismatch diagnostic — not a detector

Question: how often does the same 21-session future-loss definition differ between SPY, regional-bank equity and broad financial equity, including the 2023 bank episode? Does scoring every mechanism only against SPY hide concentrated receiving-exposure damage?

Use existing `data/yahoo/SPY.parquet`, `KRE.parquet`, `XLF.parquet` at the fixed pin, `close` total-return convention. Print source hashes before outcome computation. Missing recipient means that cell is unavailable; do not substitute an ETF or benchmark. Calendar is the complete SPY observed session index. Reindex recipients without forward/back fill; any missing future session leaves a target immature/unavailable. These ETFs are traded exposure proxies, not proof of bank runs, funding impairment, actual holdings or causal transmission.

Primary outcomes: any next-21-session close <=95% of its own decision close, separately for each asset; exclude today's loss. Secondary: <=90% over the same horizon; continuous minimum future return and ending return. Include existing drawdown from each asset's trailing 252-session high separately; current damage is not target success. Retain full-horizon maturity through the fixed end date.

Report a full common-sample 2x2 table (SPY event/no event versus KRE event/no event), corresponding XLF cells, and yearly counts. Daily windows overlap: no independence or prediction claims. Also use every 21st SPY session starting with the first session >=2007-01-01 as a nonoverlapping sensitivity grid, never reset around an event. Report pre/post2011-10-24 separately because the KRE sponsor documents a benchmark change; fund price history is not retrospectively restated as a single unchanged index. Do not use today's holdings as historical constituents.

Fixed illustrative dates: 2008-09-12, 2020-02-19, 2020-03-09, 2020-03-23, 2021-05-10, 2022-01-03, 2022-10-14, 2023-03-08, 2023-03-13, 2023-05-01, 2024-08-02, 2025-04-02. Cases were motivated by already-known history; this is exploratory mechanism/target diagnosis, not untouched or prospective validation. Date unavailable => no observation, not shifted to a favourable neighbouring date.

No fitted coefficients, threshold tuning, stock selection, trade recommendation, new alert or risk escalation results from B. A subsequent forecasting study needs independent bank/funding observations and qualified exposure, not an equity-loss outcome alone.

## Implementation and verification

- RED -> GREEN pure adapter/archive tests: future extension/revision invariance, timestamps, expired vintages, duplicate rows, deterministic knowledge hashes, missing inputs, endpoint asof/probability validity, mutation isolation.
- RED -> GREEN recipient tests: current loss excluded, fully mature windows, missing sessions, independent oracle, common sampling and no fabricated bank-run label.
- Run real-data reconstruction and recipient diagnostics in a new isolated research output directory on the existing Studio carrier. No edits to working checkouts, raw stores or production modules.
- Record source/data hashes, dependency limits, exact artifacts, tests, original-endpoint parity and any unperformed step. Publish findings and update the same cumulative Agent OS checkpoint with readback.

## Sources and interpretation

ALFRED vintage/validity definitions: https://alfred.stlouisfed.org/help/downloaddata
KRE sponsor, regional-bank exposure and 2011 benchmark change: https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-regional-banking-etf-kre
XLF sponsor, broader financial-industry exposure: https://www.ssga.com/us/en/individual/etfs/state-street-financial-select-sector-spdr-etf-xlf

These sources qualify interpretation, not Mastermind predictive strength. Source endpoints/metadata were checked September 28, 2026. Final outcome remains end-to-end regime-aware risk intelligence; this is one necessary data-contract and mechanism-target slice.