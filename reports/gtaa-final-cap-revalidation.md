# GTAA final per-name cap revalidation

Issue: #11003. Frozen repository input pin: `3d277257801f2d22f54924cfab73f7cf48ec4ca8`. Measurement date: 2026-11-11. Price window: **2007-05-01 through 2026-11-10**, 4,935 rows and the unchanged nine-asset universe.

## Decision and repaired contract

The English and Chinese product describe an unqualified per-name limit. The allocator now enforces that final limit **after volatility scaling and the existing gross-exposure scaling**. It leaves unused capacity unallocated and does not redistribute or scale capped weights back up to force the volatility target. Conservative/Moderate/Aggressive remain 30%/40%/55% per name, with gross limits 1.2/1.6/2.5.

The four conviction inputs, risk targets, 300-calendar-day warm-up, five-trading-day hold, next-bar execution, 3-bp turnover cost, bill yield and 1% financing spread are unchanged. The residual uninvested fraction earns the native modeled bill yield; a book above 100% still incurs the native borrowing charge.

## Discriminating repair proof

Against the original engine, the complete active-allocation campaign had **10 failures and17 passes**. Six failures reproduced the one/two-trend cap breach, three reproduced the amplified changing-signal weights, and the actual builder emitted the excessive allocation into JSON. The nine-trend controls and other retained controls passed.

The initial repaired allocator/hub campaign passed51 tests. The final campaign covers83 native tests across active allocation, hub/detail and Signal Lab, including the measured-quote correspondence guard in the code-owned active-allocation module. They include all three profiles with one/two/nine rising trends, zero conviction, absent and newly arriving assets, flat/volatile prices, changing signals, warm-up, weekly hold, entry/exit next-bar timing and costs. Actual native builder output agrees across the portfolio, bot-facing v2 JSON and English/Chinese allocation rows. This is source/rendered-HTML proof; no deployed browser or live portfolio is asserted.

| Rising trends | Conservative maximum | Moderate maximum | Aggressive maximum |
|---|---:|---:|---:|
| One |30%|40%|55%|
| Two |30%|40%|55%|
| Nine, diversified control |13.333%|17.778%|27.778%|

## Historical recalculation

The old and corrected native engines used the same frozen store. All configured Yahoo and FRED inputs were found; the fixture contains501 source/data files,39,256,254 bytes. Native features and condition gauges were explicitly evaluated before the backtests:25,793 feature rows/148 columns, with non-null recession/drawdown/RORO gauge histories of15,509/14,944/14,506 rows. The complete per-file source/input manifest is in the companion JSON.

| Profile | Old → corrected CAGR | Old → corrected Sharpe | Old → corrected maximum drawdown | Old → corrected maximum name weight |
|---|---:|---:|---:|---:|
| Conservative |7.74% →7.88%|1.10 →1.13|−17.3% →−14.8%|90.00% →30.00%|
| Moderate |11.19% →11.19%|1.04 →1.06|−24.2% →−21.6%|98.69% →40.00%|
| Aggressive |16.54% →16.01%|0.96 →0.98|−35.0% →−31.7%|143.91% →55.00%|

Conservative is compared with the native60/40 benchmark (CAGR8.20%, Sharpe0.75, maximum drawdown−31.4%). The other profiles use SPY (CAGR10.64%, Sharpe0.61, maximum drawdown−55.2%). Every profile's existing `oos.robust` flag remains false: this flag means **CAGR beats the benchmark in both historical halves**, and establishes no broader statistical or prospective robustness.

## Moderate diagnostics and unchanged classification

The native `scripts/mastermind_moderate_phase0.py` now reads the existing `mastermind_moderate_phase0` Trial Ledger family, with effective **N=8**. It refuses an absent family instead of silently evaluating N=1. No ledger entry or budget was changed. The historical bootstrap/fold/crisis definitions are unchanged, and the source no longer prints an unconditional promotion or “no look-ahead” conclusion.

- DSR:0.9992, N=8, raw T=4,935; native annual Sharpe1.0581.
- Native block bootstrap:21-row blocks,5,000 draws; Sharpe95% interval0.59–1.54; maximum-drawdown95% interval−32.9% to−13.0%. These are the existing harness's historical diagnostics.
- Corrected Moderate Sharpe exceeds SPY in **4/5** fixed purged folds (63-row embargo), not the old5/5 claim.
- Its Sharpe and maximum-drawdown differences versus SPY remain positive after each of the six fixed crisis omissions.
- Without the macro regime component, the existing renormalized sensitivity gives CAGR10.59%, Sharpe0.98 and maximum drawdown−22.2%. This sensitivity is not a release-vintage test.

The adversarial control uses the **same corrected native chassis**, replacing only conviction with1: same universe, warm-up, inverse-volatility sizing, final per-name/gross limits, cadence, costs and financing. Its CAGR is11.3944%, Sharpe1.00166 and maximum drawdown−27.4057%. The four-factor conviction adds only **0.05649 Sharpe and5.7850 percentage points of drawdown improvement** on the full history. Its Sharpe increment is negative in **3/5 folds**, and also after omitting2008 or2022. The strategy remains **CONFIRMER**; no new classification threshold or promotion is introduced.

The separate TSMOM overlay's historical DSR0.9952 and existing tier are unchanged. Signal Lab explicitly identifies that number as belonging to the separate60/40+30% trend-overlay experiment; it cannot certify the corrected GTAA strategy.

## Qualification and reproducibility

The macro frame uses revised observations with a two-business-day lag. This is **not** a historical release-vintage reconstruction, prospective validation, or authorization to size/execute trades. The historical universe, configured data availability and crisis definitions remain subject to their original selection limitations. Historical half comparisons and raw-T DSR are descriptive diagnostics.

The companion `gtaa-final-cap-revalidation.json` binds the original source/input manifest, exact corrected engine/builder/Phase0 blobs, old/new scorecards and allocations, all diagnostics, unchanged ledger digest, and the native builder's HTML digests and JSON snapshot. The core source blobs are:

- Allocator: `d10d02396696794e8d3f8b5f822af0c842250271`.
- Builder: `d626c45ab201f154a9c6e0484520cf15c0f4a7b3`.
- Phase0: `598626698e8f31a3d6b56c410bd68acb9e539325`.
- Unchanged return accounting: `e72f916889c9e6f2d3eaabbf83f8b3ff7e363d9d`.
- Frozen trial ledger: `0dda3d14723dd5d9b2a136ca623f50fb3f3636c5`.

Reproduce in an isolated checkout with the manifest's frozen inputs: run `python -m pytest tests/test_active_alloc.py tests/test_masterminds_hub.py -q`, `python -m scripts.build_masterminds` for temporary native output, and `python -m scripts.mastermind_moderate_phase0` for the fixed historical diagnostics. The builder writes to that checkout's configured site/data paths. No shared host checkout, committed historical price store, production publisher or live book was modified by this qualification.
