# Expectations: comparable readouts and stable chart selection

This candidate fixes two consumer defects in the existing Expectations explorer. It does not alter the observation ledger, financial influence, admission, routing, data schema or builder. It has local source, DOM and actual Chromium proof; merge, incumbent rendering and deployed-route proof remain separate stages.

## User behavior

The comparison readout now follows the same period rule as the existing builder. It considers the immediately previous point with a non-null average within the selected ticker, metric and raw horizon. It never skips a different fiscal period to find an older matching period.

| Selected / previous point | Readout | Tone |
| --- | --- | --- |
| Both averages, equal known `period_end`, previous average nonzero | `(selected − previous) / abs(previous)` | Existing positive, negative or neutral tone |
| Selected average absent | No average / 本期无平均值 | Neutral |
| No previous valid average | Em dash; accessible No prior session / 无上一期 | Neutral |
| Either period unknown | Period unknown / 财期未知 | Neutral |
| Different periods | Period changed / 财期已变 | Neutral |
| Previous average zero | Zero prior / 上期为零 | Neutral |

Missing selected average takes precedence over comparison availability. Period identity takes precedence over zero-prior handling. A prior zero remains a valid prior observation; it is not skipped. Every render clears the previous comparison's tone. Both visible reasons and the first-point screen-reader explanation respond to a live language change.

The reason replaces the percentage in the existing readout. It does not add a paragraph, badge stack or extra navigation step. The smaller UI-font treatment and wrapping preserve the six existing fields on desktop and the three-column arrangement on mobile.

## Loading and interaction contract

The existing 150 ms loading placeholder temporarily removes and later reinserts the same chart DOM node. Its event listeners survive. Previously `restoreNodes()` called `wireChart()` a second time, so one ArrowRight ran two callbacks and skipped the middle session.

`wireChart()` now marks the chart object with a private `__esChartWired` boolean and returns on subsequent bindings of that same node. This guards the existing keyboard, pointer move, click and pointer leave handlers together. A newly constructed element does not inherit the JavaScript property and can receive its own handlers. No serialized attribute, extra state owner, event bus or disposal system is introduced.

Keyboard selection remains committed. Pointer movement previews a session; pointer leave restores the committed selection. Home and End retain their existing meanings. The fix does not reset selection, clear focus or recreate the chart during loading.

## Exact source and proof

Base: `macro@071ed19f5ce87927f078f94f3e126c24d8a0307e`. Governance: `Mastermind@5c3d3885234358aefb97ecdbc59be0864df14f8b`.

| File | Git blob |
| --- | --- |
| Candidate template | `ec0909bf01e0e4740f1feaaec23ad7576c0a5d59` |
| Candidate test file | `d3478ea0d5e0f716d6ee5f2e8ee6cb73ad6c48a4` |
| Unchanged builder | `1b39e3a519a548d2187130498dd05b58a256ccdd` |
| Unchanged canonical capture tool | `78ba651d2996a64231c738a133ed465d73dd8caf` |
| Original template used for negative proof | `51d99c9ac76557e2dce356a53231416f5fe84a44` |

`qualification.json` binds the actual rendered fixture hash, source blobs, evidence manifest hash and bounded results. The XML files retain exact test names. `browser-check.json` records the eight consumer workflows. `duplicate-bind-after.json` records two real delayed placeholder/restore cycles. `duplicate-bind-before.json` records the actual two-handler skip before the wiring fix; that negative witness already had the percentage fix, and identifies that intermediate template blob explicitly.

### Source and DOM regression proof

`python -m pytest tests/test_build_expectation_surface.py -q` passes **40 tests, zero skipped**. The 25 existing tests remain. Fifteen additional cases execute the actual rendered readout and handlers through a minimal Node DOM with accumulating event listeners. They cover rollover, equal periods, either/both unknown periods, zero and negative prior values, increase/decrease/flat values, no backward jump to an older matching period, missing averages, first point, live EN/ZH change, stale tone removal and repeated chart binding.

Running those 15 cases against the unchanged original production template yields **10 failures and 5 passes**. The repeated-binding case observes indices `[0, 2]` instead of `[0, 1]`; the period cases expose false percentages. The DOM harness does not claim browser layout, fetch correctness or chart geometry proof.

### Actual browser proof

Chromium **149.0.7827.0**, Playwright **1.61.0**. A synthetic `RO` fixture is emitted by the unchanged builder: averages 100 and 110 for period 2026-12-31, then 121 for period 2027-03-31, observed on three consecutive synthetic sessions. No real market data, account or premium payload is used.

The existing canonical `capture_page_evidence.py` produces all **8 of 8** cells: 1440×900 and 390×844; dark/light; EN/ZH. The exact existing visual-evidence gate identifies the material template path and returns no findings. The canonical manifest and screenshots are preserved, rather than replacing them with a custom capture format.

In every cell, the actual page bootstraps and fetches its fixture. Home selects 100; one ArrowRight selects 110 and +10.0%; End selects 121 and the neutral period-change reason. Pointer preview shows the comparable middle point, then pointer leave restores the committed final point. Live language changes update the reason without a new readout render. The reason's scroll width fits its client width. All eight readout crops were visually inspected for glyphs, clipping, overlap and tone.

A separate browser check delays the real ticker request **300 ms** twice, first on initial open and then through the actual search interaction. Both loading placeholders remove and restore the **same** chart object. After both cycles, all four handler types have exactly one registration, and Home → one ArrowRight produces **100 → 110 / +10.0%**. The corresponding old handler produced 121 after one ArrowRight. This is proof of the affected loading/selection path, not general asynchronous response ordering.

### Capture environment and limits

The ordinary browser ZIP endpoint returned a 195-byte unavailable-site HTML response. The isolated check used the pinned `@sparticuz/chromium@149.0.0` distribution through the canonical driver's existing `driver_factory` seam. Its shipped Brotli archives were decoded in the local dependency directory without restoring archive ownership. Browser binary SHA-256: `434d2607c55941dcaa7fdd19b0800ee90488922fd9744a6642ef527ba8fabf63`.

The first CJK font setup did not render Chinese glyphs and its captures were rejected. The final setup uses `@fontsource/noto-sans-sc@5.2.8` Chinese-simplified WOFFs converted to TrueType containers with fontTools, without glyph edits, through private fontconfig. The exact source and converted hashes are in `font-provenance.json`. Canonical captures were repeated after that correction. Inter assets are the exact incumbent repository files. No runtime dependency or product font change is included.

This isolated fixture omits the unrelated global `account.js` and `terminal_overlay.js`; their 404s and console errors remain visible in `manifest.json`. The actual readout code, chart interactions, builder output, language/theme code, styles and fonts are present. The evidence does **not** establish authentication, the full shared shell, every page state, deployment or live market behavior. Full-page screenshots provide context; visual acceptance here is the affected readout and interaction.

## Builder's next steps

1. Merge through the repository's existing exact-head delivery controls. Do not change generated `site/expectation_surface.html` by hand or publish this synthetic fixture as market output.
2. Let the incumbent render process consume the template, then verify the deployed explorer's comparable, period-change and delayed-load keyboard paths. Source CI and fixture proof do not replace that deployed proof.
3. Continue the existing period-binding discovery. The chart still connects raw-horizon observations across fiscal periods; line/range segmentation and an explicit selected fiscal-period field remain separate work. Exact mover period/snapshot binding, silent horizon fallback, obsolete asynchronous response protection, atomic context retirement and complete return metadata are still open.

The emitted point has one `period_end`. This patch intentionally uses that existing producer contract; it does not infer provenance for separate average/median/range fields. A later geometry change must account for singleton segments and the producer's first-non-null-field period assignment before claiming comprehensive fiscal-period integrity.

The existing discovery remains `agentos/discoveries/DSC-EXPECTATIONS-EXPLORER-PERIOD-BINDING-GAP-20261109.md` in the Paper audit delivery. Do not duplicate it or mark the whole discovery closed based on this bounded repair.
