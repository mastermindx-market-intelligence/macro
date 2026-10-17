# Frozen shared-MTF renderer witnesses

These JSON fixtures are verbatim values extracted from the data-mtf HTML attribute
in the following committed Macro hosts. They are historical presentation witnesses,
not current market data and not claims of forecast validity.

Repository: mastermindx-market-intelligence/macro
Exact commit: 4f0801283edf5d2aff9e894e557bbef756bdfd9f

- 512980.SS-mtf.json: site/sectors/512980.SS.html, Git blob 181d78271678a6e6b83cc23f42ac69ed5e3cdeea
- XIT.TO-mtf.json: site/sectors/XIT.TO.html, Git blob 35ccf479b8a6f729ddd62a155da5eeee707931a4

The first host supplies D.macd_days_to_cross=0 and D.macd_bars_to_cross=0.5.
The second supplies D.macd_days_to_cross=6 and D.macd_bars_to_cross=5.9.
Both hosts load the shared mtf.js renderer and hydrate data-mtf through its public
DOMContentLoaded/hydrateMTF entry. The test also exercises direct renderMTF callers.

The producer engine/cycles.py:mtf_snapshot owns conversion from timeframe bars to
integer trading days. Its _daily_trigger explicitly treats a zero-day ETA as valid.
This regression changes only display selection, with no producer or scoring change.
