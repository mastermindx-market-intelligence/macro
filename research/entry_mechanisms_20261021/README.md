# Mechanism-led entry research — October 21, 2026

[Read the complete assessment](REPORT.md). This continues the [durable-pivot study](../durable_pivots_20261021/README.md) without changing its frozen core or selection.

The research separates **security selection, entry timing, path risk and exits**. It combines a pinned census of relevant internal results with an executable-outcome audit of 34 existing finalists and one fixed leadership/reset experiment. It is exploratory on already exposed, survivor-selected history. No production signals, portfolio rules, rankings, sizing or orders change.

## Findings

- Late crossovers can identify positive-return recovery cohorts while failing to locate an early bottom. Their incremental benefit over comparable ordinary entries remains uncertain.
- The tested leader-pullback construction increased recent average payoff without increasing the fraction of profitable trades. Semiconductor concentration explained much of its peer-relative advantage.
- Requiring weekly or daily Stoch confirmation did not demonstrate a stable reliability improvement on the original price-event roster. Favorable sparse weekly conditional and nonoverlap indications are retained, not suppressed.
- Positive fixed-horizon fractions fell materially under the same-entry, gap-aware 3-ATR stop diagnostic. This is one risk policy, not an optimized or recommended stop.
- All 17 top rules had negative average recent 63-session cash-exit benefit under the stated zero-cash-yield assumption.
- Prior defensive V11 evidence remains a cohort-specific reliability lead. Sector recovery is a new post-hoc candidate. Fundamental-information branches require qualified as-of inputs.

## Reproduction

Use Python with numpy, pandas and pyarrow. Retain the original baseline's licensed input snapshot and `results/base_events.parquet`; its manifest verifies price hashes. Raw vendor data are not republished here.

Run, from this directory:

```bash
python verify.py
python analyze.py --baseline ../durable_pivots_20261021
python review_supplement.py
python build_figures.py
```

The first outcome run's frozen protocol/code commit is `636fb729f9e0bf5dc81847da7a5195eca895c149`. It preceded calculation of the continuation tables. `results/registration.json` and `run_summary.json` record hashes and execution timestamps. The review supplement completes reporting gaps while verifying that all original CSV result hashes remain unchanged. The protocol has not been retroactively rewritten to reflect favorable outcomes.

Figure rendering additionally requires matplotlib. `build_pdf.py` uses ReportLab, Pillow and the indicated DejaVu fonts; it renders the report for conversation delivery. The repository report uses SVGs. PDF/PNG exports and transient transfer files are excluded from Git.

## Data and interpretation

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) before interpreting the tables, especially `net20` (20 basis points of cost, **not** a 20-session horizon), top-row counterfactual long outcomes, and the two different nonoverlap conventions. [VERIFICATION.md](VERIFICATION.md) records mechanical and method review. [mechanism_decisions.json](mechanism_decisions.json) is a research decision record, not a production configuration.

The 2020–2026 period has already informed research. Calendar intervals are exploratory and not multiplicity-adjusted; event counts are not independent observations or portfolio returns. Complete frozen-rule results and rejected oscillator events are included.
