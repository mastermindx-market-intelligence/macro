# D03 T48 — static Paper text-contrast receipt (not WCAG certification)

Date 2026-11-04 UTC. Native file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, page `p-D-0`, eight exact artboards bound in `matrix.json`. The contrast check follows the **final** JSX re-export after guarded fixes; affected screenshots were regenerated. No served CSS, browser interaction or production assertions are inferred.

## Measured result

- Initial light-theme audit: **18 below-AA small-text pairs per board**, 72 across 390/320 × EN/ZH. All dark-theme text pairs passed.
- Targeted repair: changed the 72 initially failing text nodes to accessible `#53647B` on their existing light surfaces; a margin pass adjusted 52 additional light text instances (neutral `#53647B`, amber `#735418`, blue `#406183`) without changing production code or data.
- Final audit: **568 / 568 measured text-node pairs pass** their 4.5:1 normal / 3:1 large threshold. Light minimum **5.02:1**; dark minimum **5.93:1**. Counts are **71 text nodes per board × 8 boards**. The final light screenshots and exact node-bound JSX replace earlier lower-contrast proof.

| Board state | Text nodes | Below threshold | Minimum |
|---|---:|---:|---:|
| 390-light-en | 71 | 0 | 5.02:1 |
| 390-dark-en | 71 | 0 | 5.93:1 |
| 390-light-zh | 71 | 0 | 5.02:1 |
| 390-dark-zh | 71 | 0 | 5.93:1 |
| 320-light-en | 71 | 0 | 5.02:1 |
| 320-dark-en | 71 | 0 | 5.93:1 |
| 320-light-zh | 71 | 0 | 5.02:1 |
| 320-dark-zh | 71 | 0 | 5.93:1 |

## Method and boundaries

Native JSX style walk: for each text `div` with explicit color, select its closest explicit background from its ancestor stack, convert both six-digit hex colors to sRGB linear luminance, then compute `(Lighter+0.05)/(Darker+0.05)`. Standard-size text is required to reach 4.5:1; large type (>=24px or >=18.66px bold) is required to reach 3:1. The resulting node-level counts and thresholds are in `CONTRAST_AUDIT.json`.

This is **source-style contrast**, not browser-verified WCAG. It does not yet test non-text icons, foreground overlays, CSS state changes, focus rings, external font metrics, screen readers, touch keyboard, reduced motion, live content, failure/permission states, authenticated flows or runtime DOM contrast. Those remain D03 acceptance gates. All boards remain PROVISIONAL/DRAFT, and no held T49 or release effect was touched.
