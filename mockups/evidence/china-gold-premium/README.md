# China Gold Premium — visual evidence

This corpus captures the actual `commodities.html.j2` with the new Gold-only China physical-premium partial at semantic head `cddde2c93bf603b245478dc8174615067fd05e25`.

## States

- **available** — deterministic, entitled fixture inputs are passed through the production `engine.china_gold_premium` math. The final intraday fixture reproduces the screenshot arithmetic: Shanghai USD-eq 4398.94 versus London 4391.59 = +0.1674%.
- **unavailable** — no entitled source is configured. The panel remains visible and explicitly refuses to substitute futures, an ETF, or an unofficial web quote.

The canonical manifest contains both routes across dark/light × EN/ZH × desktop 1440/mobile 390: **16/16 captured**. The friendly `panel-*.png` files are supplemental element crops of the Gold panel itself.

## Mobile overflow finding

The exact feature base already has a commodities-page mobile document overflow: 517px in the EN fixture at a requested 390px viewport. That defect is owned by open commodity safety R1 PR #7198 and is not rebuilt here.

`panel_checks.json` compares every new-feature cell against the exact carrier-base template. Across all 16 panel crops:

- feature worsened document overflow: **0**
- Gold premium panel overflow: **0**
- page errors: **0**
- requested theme/language mismatch: **0**

The final production acceptance gate remains: after the incumbent R1/mobile fix is integrated, the complete page must fit the 390px document width. This corpus proves the new panel itself is contained; it does not relabel the inherited page defect as fixed.

## Source honesty

No live SGE/LBMA provider data is claimed here. Available-state inputs are fixtures used only to prove UI behavior and calculation wiring. Production remains honestly unavailable until entitled source references are configured.
