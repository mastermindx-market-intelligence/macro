# Compact comparison matrix: full readings at narrow widths

## Outcome

The current two-asset snapshot fits inside the existing comparison drawer at 320px and 390px. Both observation dates and signed values remain complete at the existing 12.5px type size. The 320px drawer has a 280px reading area; the table now uses that area instead of forcing a 370px table.

The matrix remains a native table in the existing keyboard-focusable scroll region. A larger cohort still scrolls horizontally, with the measure column fixed in place. No asset-count-specific controller, truncation, smaller type or data transformation was added.

Source parent: `32ad0bc508b50afefa3dc485f970423733a42c54`. Candidate asset version: `1bbbd2258e94`.

## Layout and ownership

Only the existing `templates/crypto_intelligence_r4.css` owner changes runtime behavior. The same CSS is copied to the served asset. Both saved HTML pages change only their two asset-version references; JavaScript, HTML template, projection, producer, view JSON and shared shell stay exact to the parent.

At viewport widths of 400px or less:

| Element | Rule | Reason |
|---|---|---|
| Measure column | width and minimum width 98px | Leave room for two complete asset columns; field labels may wrap. |
| Asset columns | minimum width 91px | Dates need 74.421875px plus 16px horizontal padding in the measured native font. |
| Cell side padding | 8px each | Preserve readable separation within the existing 280px area. |
| Observation dates | no wrapping | Keep each date unbroken; intrinsic table sizing can overflow if future text or fonts require more width. |
| Larger cohorts | existing native horizontal scroll | Preserve every asset and the sticky measure context. |

The table remains automatically sized. At 390px its columns expand into the available 350px; at 320px the layout is 98 + 91 + 91 = 280px. These are minimum dimensions, not clipping boxes. The supported larger-cohort fixture uses 371px inside a 280px region.

The existing header, Close target, comparison disclosure, full-cohort semantics, theme, focus return and navigation stay with their current owners. No alternative mobile card representation or duplicated reading-state owner was introduced.

## Native measured result

Chrome 157.0.8103.39, Playwright 1.62.0, existing isolated SSD verifier, ephemeral loopback origin. The fixtures use retained historical data and explicit synthetic null/zero/larger-cohort variants.

| Case | Parent table | Candidate table | Region | Type/content |
|---|---:|---:|---:|---|
| Two assets, EN/ZH, 320px | 370px | 280px | 280px | Exact text, font size and family retained |
| Two assets, EN/ZH, 390px | 370px | 350px | 350px | Exact text, font size and family retained |
| Zero + unavailable/history, EN/ZH, 320px | 370px | 280px | 280px | 0.0% and supplied Building history remain distinct |
| Three assets, EN/ZH, 320px | 490px | 371px | 280px | Native keyboard scroll reaches the final asset |

Native Range measurements verify complete single-line headers, dates and signed values within the two-asset region. The unavailable text also fits. Before/after text, font size and font family are identical across all eight measured variants. The page itself has no horizontal overflow. The larger-cohort test reaches the far edge with real ArrowRight input and checks sticky measure position and focus.

Four new native crops were inspected: English and Chinese two-asset layouts, English unavailable/zero history, and the Chinese larger-cohort far edge. English uses the dark theme; Chinese uses the light theme and touch contexts in these cases.

## Verification and corrected harness

1. Parent baseline: **8 failed, 122 deselected**, 17.49s pytest / 17.850s subprocess. Six failures reproduce the two-asset fit problem. Two larger-cohort failures came from an insufficient fixed five-arrow test sequence, not a new production defect.
2. Corrected larger-cohort parent check: **2 passed, 128 deselected**, 3.91s / 4.198s. The harness uses sixteen real arrow inputs and waits for the measured far edge. Parent runtime remained `d4393a5d0e55`.
3. Candidate: **12 passed, 118 deselected**, 9.50s / 9.768s. Eight new cases plus four existing full-cohort cases. Twelve browser contexts and twelve pages; zero page errors, external requests or WebSocket traffic.

The four existing full-cohort cases now exercise keyboard scrolling only when the region actually overflows. Their cohort, values, origin/return and page-width checks remain.

The earlier complete **161-case run** belongs to the prior comparison implementation and remains retained evidence for unchanged owners. This phase ran the twelve affected cases. It does not claim a new 169-case or complete-suite run.

The first publication-metadata script stopped before writing output because its capture glob also included the four existing cohort crops. It was corrected to select the four new `compact-*.png` files; no test/runtime mutation was replayed. The corrected manifest completed with exit 0. The initial cloud layout estimate of a 100px measure column and 90px asset columns was revised to 98/91 after native text measurement, before candidate runtime upload.

## Builder acceptance and remaining work

Keep these layout invariants when new assets or translations arrive:

- Preserve complete dates, numerical signs and unavailable labels. If intrinsic content needs more width, retain native horizontal scrolling.
- Retain the native table, sticky measure column, keyboard focus and full-cohort action.
- Never convert missing relative data to zero or hide otherwise usable asset evidence.
- Keep calculation explanations in the existing collapsed basis disclosure.
- Keep paired-window receipts explicitly proposed until the producer emits real paired dates/counts and Bitcoin basis.

The next bounded integrity fix is in the existing projection: an unavailable relative number must not retain a directional state label. This phase does not change that logic, producer classification, observations, H5/model, alerts, route cutover, admission, release or production acceptance.

## Evidence

- [Exact source, runs and qualifiers](COMPACT_MATRIX_VALIDATION.json)
- [Parent baseline](compact/BASELINE.txt), [exact initial test input](compact/BASELINE_TEST_INPUT.py), [corrected parent scroll check](compact/BASELINE_CORRECTION.txt)
- [Candidate JUnit](compact/CANDIDATE_RESULTS.xml)
- [Native before/after metrics](compact/METRICS.json)
- [Source conservation receipt](compact/SOURCE_RECEIPT.json)
- [Native run and capture receipt](compact/CAPTURE_RECEIPT.json)
- [Inspected captures](compact/captures)
