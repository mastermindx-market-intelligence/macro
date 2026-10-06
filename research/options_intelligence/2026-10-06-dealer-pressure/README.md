# Mastermind dealer pressure, extremes and closing intelligence

**Research commission completed — 2026-10-06.** All twenty commissioned reports are present, with **72 feature hypotheses**, a **37-product / 28-field data matrix**, **260 source records**, **168 claim/evidence records**, and **62/62 passing synthetic assertions**. This is a research and implementation handoff; no market backtest, calibrated forecast, data purchase or production change was performed.

## Start here

Read [01 Executive verdict](01_EXECUTIVE_RESEARCH_VERDICT.md), then [20 CEO/Fable handoff](20_CEO_FABLE_HANDOFF.md). The exact later experiment is in [16 Validation masterplan](16_EMPIRICAL_VALIDATION_MASTERPLAN.md), including mandatory separate F1/F2/F3 verdicts for fifteen-minute excursions, remaining-session extremes and the ES close. [18 Integration map](18_MASTERMIND_INTEGRATION_MAP.md) and [02 Current-state census](02_CURRENT_STATE_NO_REDO.md) identify the existing owners and source-custody boundaries.

**Recommended first slice:** a new SPX/SPXW-to-ES information-value experiment comparing explicit OI assumptions, eligible public flow and scoped participant-informed inventory with identical repricing, liquidity, clocks and outcome targets. Preserve accepted P5 SPY/QQQ/IWM ten-minute variance and the existing Exposure Outlook GEX-promotion refusal. Use its current price/volatility baseline and outcome/consumer owners; do not recreate their local/unpushed work.

**Decision rule:** test whether better inventory information adds useful out-of-sample value, then how much survives actual release/consumer latency and cost. Stop endpoint-specific claims when sufficiently precise evidence excludes useful value. Broad reconstruction stops only after required extreme/close families are resolved, or an explicit cost decision records the remaining uncertainty.

## Twenty commissioned deliverables

| No. | Report |
|---|---|
| 01 | [Executive research verdict](01_EXECUTIVE_RESEARCH_VERDICT.md) |
| 02 | [Mastermind source census and integration boundaries](02_CURRENT_STATE_NO_REDO.md) |
| 03 | [Dealer inventory identifiability](03_DEALER_INVENTORY_IDENTIFIABILITY.md) |
| 04 | [Competitive mechanism deconstruction: intraday dealer pressure, extrema and the close](04_COMPETITOR_MECHANISMS.md) |
| 05 | [Academic literature review and adjudication](05_ACADEMIC_LITERATURE_REVIEW.md) |
| 06 | [Dealer inventory reconstruction specification](06_INVENTORY_RECONSTRUCTION_SPEC.md) |
| 07 | [Dynamic dealer-pressure specification](07_DYNAMIC_DEALER_PRESSURE_SPEC.md) |
| 08 | [Cross-product dealer-book integration: contract economics and normalization](08_CROSS_PRODUCT_EXPOSURE_SPEC.md) |
| 09 | [Behavioral node specification](09_BEHAVIORAL_NODE_SPEC.md) |
| 10 | [Probabilistic intraday extremes and close-region specification](10_LOD_HOD_EOD_PROBABILISTIC_SPEC.md) |
| 11 | [Closing pressure and auction intelligence specification](11_CLOSING_PRESSURE_AUCTION_SPEC.md) |
| 12 | [Liquidity and options materiality specification](12_LIQUIDITY_CONTROL_SPEC.md) |
| 13 | [Off-exchange liquidity-memory and absorption specification](13_OFF_EXCHANGE_ABSORPTION_SPEC.md) |
| 14 | [Data source, cost, rights and availability matrix](14_DATA_SOURCE_COST_RIGHTS.md) |
| 15 | [Feature and falsifiable-hypothesis catalog](15_FEATURE_HYPOTHESIS_CATALOG.md) |
| 16 | [Empirical validation masterplan](16_EMPIRICAL_VALIDATION_MASTERPLAN.md) |
| 17 | [Failure, kill and unknown ledger](17_FAILURE_KILL_UNKNOWN_LEDGER.md) |
| 18 | [Mastermind integration map](18_MASTERMIND_INTEGRATION_MAP.md) |
| 19 | [Phased implementation roadmap](19_PHASED_IMPLEMENTATION_ROADMAP.md) |
| 20 | [Implementation-ready CEO / Fable handoff](20_CEO_FABLE_HANDOFF.md) |

## Reusable research artifacts

- [Source register](SOURCE_REGISTER.md), [CSV](SOURCE_REGISTER.csv) and [JSON](SOURCE_REGISTER.json): stable URLs, version/retrieval dates, evidence scope and access limits. Records include external literature/documentation and internal source/procedure evidence; they are not 260 independent studies.
- [Claim/evidence ledger](CLAIM_EVIDENCE_LEDGER.csv) and [JSON](specs/claim_evidence_ledger.json): 42 principal adjudications, 17 competitor claims, 37 data-product claims and 72 falsifiable feature hypotheses.
- [Feature CSV](15_FEATURE_HYPOTHESIS_CATALOG.csv) and [JSON](specs/feature_catalog.json): formulas, units, event/known-at clocks, evidence, confounders, falsifiers, missingness and existing owners.
- [Data CSV](14_DATA_SOURCE_COST_RIGHTS.csv): exact product/field/cadence/clock/correction/history/rights/cost/availability and engineering dependencies.
- [First-slice registration template](specs/first_slice_registration.template.json): proposed, not registered or authorized; owner-dependent fields remain null.
- [Synthetic methodology](witnesses/METHOD.md), [script](witnesses/dealer_pressure_witness.py), [results](witnesses/results.json) and [figure](witnesses/dealer_pressure_synthetic.png).
- [Research acceptance crosswalk](COMPLETION_ACCEPTANCE.md), [machine validation](VALIDATION_RECEIPT.json), [file manifest](FILE_MANIFEST.json) and [continuation context](CONTINUATION_CONTEXT.json).

## Reproduce the numerical witness

From this directory, with Python, NumPy, SciPy and Matplotlib:

```bash
python3 witnesses/dealer_pressure_witness.py --outdir witnesses
```

The witness constructs its own book and price/surface paths. It verifies signed-position accounting, nonlinear endpoint demand, cohort and Shapley conservation, path net versus turnover, native product normalization and exact-time/refitted-IV distinctions. It is not a simulated claim about actual dealer holdings or observed alpha.

## Source and publication scope

| Boundary | Exact revision / state |
|---|---|
| Commission's original Macro reference | 7502286c8c15653635896344d632929e1715b6ad |
| Fresh Macro analysis freeze | c9631f8b2469587dec643bec94b16e77c09ef511 |
| Fresh publication base | aafb9e25b0c12390ef99a9b9c4937fa1198b4bf0 |
| Protected Mastermind procedure | a6d40ff648671b03bd4d829d84dd066b58ea8c3f |
| Terminal analysis freeze | ad36a332cd4b53af1d917a94f6fb3a10e27dad84 |
| Additional incumbent | MAS-260 current native record; Macro #7328 remote head 9515f2558a006c913a7c0eb30d966c47fa1a143b; later work explicitly local/unpushed |

The publication base is four commits / fifteen changed paths ahead of the analysis freeze; that bounded comparison did not alter the options/GEX/auction core inspected for this research. Report02's final addendum records the additional Exposure Outlook owner/negative-evidence census.

Canonical intended location: `research/options_intelligence/2026-10-06-dealer-pressure/` in Macro. Publication uses the fresh, isolated `claude/dealer-pressure-research-2026-10-06` research branch. It is a supporting research contribution to observed `WS:MARKET-OS` / `MAS-260`, records-only. This routing neither changes that issue nor replaces #7328, accepts local work, or creates an implementation successor.

**HOLD-FOR-SOL — DO NOT MERGE.** Holding authority: Sol. Release requires an explicit Sol ruling on the exact PR/head after research review and concluded required checks. No auto-merge, implementation, collector, entitlement, trading, portfolio, Prophet, ranking, deployment or operational authority is granted by this package.

## Evidence limits that survive delivery

Current source code, native owner reports, vendor documentation and actual operation are different evidence grades. Exact live rights/retention/coverage remain owner-verification dependencies. Proprietary competitor methods remain unknown where undisclosed. The new market experiments have not been run. The package contains no vendor raw tape, complete external paper PDFs, proprietary source code or parallel operational state.
