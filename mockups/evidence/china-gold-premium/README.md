# China Gold Premium — visual evidence

This corpus captures the actual `commodities.html.j2` with the new Gold-only China physical-premium partial at semantic head `17eceee3dcfb59294c0b12b997fd6e5b6c4d430a`.

## States

- **available** — deterministic, fixture-only entitled inputs are passed through the production `engine.china_gold_premium` math. The final intraday fixture reproduces the screenshot arithmetic: Shanghai USD-eq 4398.94 versus London 4391.59 = +0.1674%.
- **unavailable** — required live source rows are absent. The panel remains visible and explicitly refuses to substitute futures, an ETF, or an unofficial web quote.

The canonical manifest contains the intraday, unavailable, and no-compatible-history routes across dark/light × EN/ZH × desktop 1440/mobile 390: **24/24 captured**. The friendly `panel-*.png` files are supplemental element crops of the Gold panel itself.

## Mobile overflow finding

The exact feature base already has a commodities-page mobile document overflow: 517px in the EN fixture at a requested 390px viewport. That defect is owned by open commodity safety R1 PR #7198 and is not rebuilt here.

`panel_checks.json` compares every new-feature cell against the exact carrier-base template. Across all 16 panel crops:

- feature worsened document overflow: **0**
- Gold premium panel overflow: **0**
- page errors: **0**
- requested theme/language mismatch: **0**

The inherited whole-page overflow remains owned by R1 #7198. This feature acceptance is bounded to its own panel plus zero document-width regression versus the feature-free base; this corpus proves both without relabelling adjacent debt as fixed.

## Source honesty

No live SGE/LBMA benchmark data is claimed here. Available-state inputs are fixtures used only to prove UI behavior and calculation wiring. The official SHAUPM/LBMA-AM method remains unavailable until its own entitled mapping exists; the separate close-proxy source path has been wired but still awaits its first natural secret-bearing nightly effect.

## Interactive mode proof

`interaction_checks.json` exercises the live chart controls rather than inspecting only the default frame:

- premium → spread → price mode transitions;
- English and Chinese legend updates;
- 1M → Max range changes;
- CNY proxy and USD intraday units;
- moving-average/reference legend visibility by mode;
- non-empty chart paths, correct zero-line behavior, zero browser errors, and contained desktop/mobile geometry.

Eight interaction screenshots accompany the machine receipt.
