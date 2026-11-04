# D05 — current CI and painted-contrast follow-through

## Outcome and ownership

The D05 source implementation remains at **0c4493c7025f7c1c0f9e558860d5e4ba33457cd1** in [Draft #10703](https://github.com/mastermindx-market-intelligence/macro/pull/10703). The two nine-step composed Company-return journeys and separate Nasdaq/Russell proofs remain qualified at that exact source. This addendum records newly observed failures rather than treating the implementation as accepted.

At **2026-11-04 12:50:53 UTC**, seven CI packs had passed, four had failed, and pack 11 was still running. The contract-delta repair passed hosted CI. Full CI success is not claimed. The incumbent D05 source lead retains all Macro repairs, EW-P4 refresh and the separately assigned Theme Tree work. This programme/Dossier lane performed read-only diagnosis, an isolated in-memory harness reproduction, and new browser measurements. It did not modify Macro application source or dispatch another worker.

[Machine-readable CI record](verification/ci_failure_triage_0c4493.json) · [Original run](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41824389478) · [Same-thread owner handoff](https://mastermindxgroup.slack.com/archives/C0CBC6AEAQZ/p1793796400767899?thread_ts=1793768002.626429&cid=C0CBC6AEAQZ).

## Hosted CI: exact findings and bounded corrections

| Pack / logical job | Finding | Required correction |
|---|---|---|
|2 / design-governance | Two added Dossier radius literals,12px and10px; other 25,321 findings are inherited/nonblocking | Use the applicable existing radius-token contract. Retain the forward-only ratchet. |
|3 / reference-integrity | Old “enough data to time” fragments conflict with current scored/not-scored semantics | Require both current EN/ZH disclosure clauses and retained unscored rows. Make each mutation effective; preserve price-history versus volume-coverage distinctions. |
|3 / basket-staleness-warn | Canadian member-link matcher assumes adjacent class/href attributes | Parse anchors structurally; require exactly 8 members and each native Canadian destination. Preserve all expanded base regional tests and unavailable/date/benchmark assertions. |
|3 / EW-P4 | Actual Sector Central render input no longer matches the screenshot receipt | Existing source lead completes the already-owned recapture and source-equivalence receipt. Do not edit hashes without new render evidence. |
|4 / public-render-fastlane | Node VM omits URL and location.href; the real delayed loader throws | Supply the browser host fields while retaining all routing assertions, real fallback and product source/identity checks. |
|6 / ftr-tape-surfaces | Generated basket pages retain old static sort styles | Synchronize only the owned presentation fragments with unrelated payload bytes preserved. Retain all-region style parity and keyboard checks. |
|6 / ftr-tape-surfaces | Exact wrapper-string check rejects added attributes; the new aria-label also embeds HTML | Keep the immediate ts/tbl-scroll parent invariant, repair the plain accessible name, and verify the late wrapper pass preserves focus/node/scroll. |

The CI-tested merge is **969df7bda4f3db57e25e5c2abdd3f4175e3fb28a**, composing the candidate with base **56868dfeb13821d583e8a83a213d4cef0ba89423**. In particular, the expanded regional test in that composition must not be replaced by the older candidate's compact-cycle test.

The Members label is a product defect: the existing L helper returns bilingual span markup, which is unsafe inside a quoted aria-label attribute. The accessible name must be plain localized text or use aria-labelledby. This finding does not justify removing the focusable scroll region or weakening its tests.

### Isolated router-host reproduction

The unchanged source/test blobs reproduce the hosted URL exception after the 3-second fallback. Adding only the real URL implementation and a stable absolute page address **in memory** makes both existing replay cases pass: all six route/target pairs are retained. No source file was modified.

This proves the minimal harness diagnosis. It does not prove script payload loading: the existing DOM stubs deliberately do not fire script-load events. Preserve that scope. [Raw result](verification/ci_pack4_harness_reproduction_0c4493.json) · [Exact executed reproducer](verification/reproduce_ci_router_host.py).

## D05-RESP-11: actual painted heatmap contrast

The current source preview lacked marketdata/sp500_heatmap.json. The browser harness supplied one explicitly labelled, hashed **10-tile controlled fixture** through the request boundary; it did not change heatmap code, theme assets or application DOM. All57 previously qualified emitted assets matched. The original flow table is absent, so this is **heatmap-only partial evidence**.

Each case used the actual Next/shared-shell page, native Breadth & money navigation, settled fonts, EN, reduced motion, an observed theme and viewport, and the existing renderer. The pointer was moved outside the measured iframe before text capture; the final receipt reports zero hovered targets and no ancestor filters.

| Case | Text instances measured | Below strict minimum probe target | Lowest ratio |
|---|---:|---:|---:|
|1440 dark EN|22|2|4.2484:1|
|1440 light EN|22|1|4.4443:1|
|390 dark EN|22|2|4.1449:1|
|390 light EN|22|2|3.3942:1|

**Strongest counterexample:** the light 390 sector-return header is 11.9px, has no text shadow, and measures 3.3942:1 minimum /3.4191:1 fifth percentile against its actual painted gradient background. It falls below the 4.5:1 normal-text target. Some 18px ticker and 12px return labels also have under-target minimum samples despite their existing shadows.

The instrument captures the actual viewport, then temporarily makes only target ink transparent while retaining computed text shadows and geometry. Paired images identify glyph coordinates; the user-agent foreground is compared with the actual composited substrate at those coordinates. Actual raster-core contrast is recorded separately. Initial diagnostic runs are explicitly rejected: V1 mishandled unit sRGB serialization; V2 corrected that, and V3 additionally removed incidental pointer hover. **Only V3 is the accepted measurement.**

W3C guidance distinguishes normal and large text and treats actual foreground/background colors separately from antialiasing. The probe's tile-edge minima are conservative and do not constitute a blanket WCAG conformance judgment. They provide exact counterexamples for the existing heatmap/F02 owner to resolve. The light phone header remains a clear, stable failure within the tested presentation. [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) · [W3C G18](https://www.w3.org/WAI/WCAG21/Techniques/general/G18).

[Complete measurement receipt](verification/painted_contrast_0c4493.json) · [Exact final runner](verification/verify_painted_contrast.py).

### Keyboard and visual limits

Native Breadth & money focus was reached by keyboard in all four cases. Desktop Expand focus was also reached. Their painted changes include pixels exceeding 3:1, but this is selected-control evidence, not full focus-area/perimeter or whole-page keyboard conformance. Expand is intentionally hidden at 390 and was not forced visible.

Actual captures and the transparent-ink substrate were inspected. Screenshot paths and hashes are retained in the original owned proof directory and recorded in the receipt; PNGs were not republished through an alternate publisher. The full flow table, ZH Cartesian cases, zoom, screen readers, real-account authorization and shared F02 acceptance remain separate.

## Exact next actions and retained holds

The source lead should compose the named CI/product corrections on the existing source branch, preserve the current-source journey contracts and expanded base tests, and consume the existing EW-P4/Theme Tree operations through their original owners. The heatmap/F02 owner must resolve the new contrast finding and recapture the affected presentations.

Terminal #1244 still needs supported selected-content publication of its 14 qualified files while preserving 486 inherited paths. The compact Dossier #10707 candidate remains in its original publisher after a reconciled NOT_APPLIED refusal. No workaround, re-home or denied retry was attempted.

**Classification: CHECKPOINTED_CONTINUATION.** The source and programme are durable; named source/publisher/design actions remain. There is no claim that all 119 acceptance cases passed, that a worker request proves START, or that this attended session monitors work after ending. F01/F02, Paper and all merge/Ready/queue/relabel/deploy restrictions remain held.
