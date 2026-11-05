# Defensive compounders — V11 nested-washout empirical research

**Research only — not a live trading system, sizing model, or proof of predictive alpha.**
Data through **October 8, 2026**; principal evaluation from **January 2018**. Published on October 12, 2026.

## Research outputs

- [Corrected, source-grounded V11 assessment](../DEFENSIVE_NESTED_V11_EMPIRICAL_2026-10-11.md): complete definitions, results, caveats, and a record of further empirical qualifications.
- [Full reproducibility archive](./Defensive_Nested_V11_Full_Reproduction_2026-10-12.zip): **2,302,614 bytes**, SHA-256 `97966f72ea15cb34e0f5453252eef683411c894b7ca4432de4ce7c540d1ffaf0`; research source, tests, specifications, derived CSV/JSON and input inventory. This deliberately excludes raw vendor OHLC bars, FRED raw series, credentials, broker calls, and live orders.
- Companion *viewer-format* workbook and long-form report were delivered in the source ChatGPT conversation as downloadable attachments. They are not contained in the GitHub reproducibility ZIP. Original attachment digests: `Defensive_Nested_Washout_V11_Evidence_Workbook_2026-10-12.xlsx` SHA-256 `3c9471d9b3704bff069c778a6ee7e7ac59febdef9b1bb16eba08946c471e4587`; `RESEARCH_REPORT.md` SHA-256 `376c5f1cb437432ee0dcc66376c9cb502131c567293d8d979a696c6dda4a1496`. The downloadable conversation results bundle contains both.

## Key, bounded findings

- Across the five core stocks MCD, WMT, WM, COST and PG, **67/74** daily RSI-MACD crossovers under a recently washed-out weekly **and** two-week StochRSI context had positive returns 126 trading sessions after entry; **214/308** with neither context did. Means were **+10.68% vs +6.79%**. These are highly correlated, exploratory fixed-horizon historical events, *not* future success probabilities or stopped-strategy win rates.
- The stronger setup generally **did not** guarantee that waiting for a new daily/two-day crossover after the watch armed was superior to immediate-watch entry at a common endpoint. Six-month winners frequently breached realistic interim protective stops.
- Rising real yields, market stress, and other regime labels **cannot be promoted as universal entry vetoes** from small observational strata. Exit-on-worsening-stress tests reduced some adverse paths while sacrificing recovery.
- The thirteen peer names showed a weaker, not universally positive, context effect. No strategy has been installed into production.

## Scope and verification

This is a **PARTIAL** capability: completed research and testable code, with chart-native indicator parity, point-in-time source vintages, independent price-vendor reconciliation, portfolio accounting, prospective frozen holdout, and live execution still **UNPROVEN**. Avoid copying old price-MACD or RSI(2) performance conclusions onto this different RSI-MACD-on-RSI method. Do not fit the indicator species or 2W bar phase by comparing backtest returns.

Original source-input snapshot inventory digest: `69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3`. The final research run recorded **58 mechanical tests passed**, not 58 independent statistical validations. The archive can reproduce results only with separately licensed original raw inputs, as explained in its own README.

This publication uses a clean branch from current macro main, retaining review and CI protections. It does not merge earlier speculative V1–V10 research notes or change product runtime.
