# D04 — US List performance and lifecycle

## Result and scope

This extends the complete List-access implementation published at `61844ffd1b6e53d8e63122141b1125b3d6219bd3`. The measured repairs preserve all supplied companies and Theme members, existing Map/List presentation, per-map state, native disclosures, keyboard access and return ownership.

The final JavaScript source and generated twin have SHA256 `d72dc15379b621d65d5fd9cd631dc69060642d51c85d89f327e42510244d60ec`. Product changes are bounded to the existing US history/List paths:

1. History capture stops at the first visible item instead of checking every item.
2. When the normal-flow List lies completely outside the visible return band, capture retains the existing no-visible-item fallback without checking every hidden/offscreen row. This is the important phone case when the map selector is onscreen and results are below it.
3. List filtering no longer repeats its already-completed positioning/status work.
4. Native toggle notifications from restored or filtered disclosure nodes do not serialize history again when their state is already recorded. A real user disclosure change still updates the same owner.

No observer, shared overlay, refresh owner, field budget, source payload, store, route or authorization behavior was replaced. No CSS or visible List markup was redesigned.

## Measured action cost

Chromium 151.0.7922.34 on Apple M2 Ultra / macOS 26.5, with **4× CPU throttling**, loopback assets, reduced motion and external requests blocked. These are instrumented lab observations; the host was not a controlled field-device cohort. Each value measures an actual input/click event to its second subsequent animation frame. It is **not production INP, LCP, CLS, a p75 field sample or a physical-phone result**.

The probe used the unchanged committed snapshots: **503 S&P companies, 268 Theme subsectors and 2,339 Theme/member contexts**. Source dates remain November 2 and November 3; these are not current production freshness claims.

| Themes → S&P List | Samples | Median | Range | Item bounds checks per switch |
| --- | ---: | ---: | ---: | ---: |
| Published baseline, desktop 1440 | 8 | 1,076.60 ms | 923.2–1,102.6 ms | 2,608 |
| Final desktop 1440 | 8 | 186.95 ms | 163.3–198.9 ms | 2 |
| Final phone 390 | 8 | 183.15 ms | 162.7–215.5 ms | 0 |
| Final phone 320 | 8 | 201.90 ms | 164.5–222.1 ms | 0 |

The phone result means zero **item** bounds checks when the entire List is outside the band; the container bounds and fallback position still have their normal reads. Desktop median fell about 83% in these two measured runs. Scheduling noise and the small local sample limit any general performance claim.

All measured query events in the final 100-action matrix write history **once**. The baseline produced 23–65 writes for several filtered/expanded Theme input cases, because native disclosure notifications repeated state serialization.

Complete expanded Theme-list reconstruction remains expensive: the largest observed expanded-query action was approximately **823 ms / 972 ms / 803 ms** at 1440 / 390 / 320 under 4× throttling. This is an explicitly retained performance gap, not a field-budget pass. The full supplied scope remains available; no rows were removed or silently truncated to improve the numbers.

[Published-code baseline](../../../ux-evidence/d04-us-heatmap-return-20261104/performance-before.json) · [Final timing observations](../../../ux-evidence/d04-us-heatmap-return-20261104/performance-qualified.json)

## Retirement and profiler attribution

The timing driver's first memory counters grew while live DOM, refresh-listener balance and polling registrations stayed flat. A controlled map-only comparison reproduced the growth. The actual heap retaining path rooted a retired AAPL row through **GC roots → Global handles → DevTools console**, then its old group and List container.

Discarding console entries through the additional profiling session did not release the other driver's retained target handles. The raw failed retention assertions remain in [that instrumented run](../../../ux-evidence/d04-us-heatmap-return-20261104/performance-final.json); they have not been changed into passes. The [extracted heap path](../../../ux-evidence/d04-us-heatmap-return-20261104/retention-path.json) and [unwrapped locator comparison](../../../ux-evidence/d04-us-heatmap-return-20261104/retention-diagnostic.json) retain the diagnosis. The large raw heap is a temporary diagnostic, not a required published artifact.

A second mode drives the same generated document through **by-value CDP calls**, without locator/expect target handles or timing/event wrappers. Its controls still execute the existing application handlers; the resulting evidence is lifecycle proof, not new trusted-input acceptance. It uses a weak reference to the retired List and compares the identical warmed S&P List state after garbage collection.

The final-source run completed **three full S&P↔Themes plus Terminal open/close cycles at each of 1440, 390 and 320 pixels**:

- Retired List collected after each sampled cycle.
- **Zero growth** in live document elements, live heatmap nodes, retained DOM nodes, document count and event-listener count.
- One initial request per encountered heatmap feed; no repeated request from remounting.
- Zero page errors.

An earlier eight-cycle matrix at all three widths also passed before the final offscreen-capture guard. Its inputs and source hashes remain separate. JS heap readings rose by roughly 128–130 KB in the final bounded run; these observations do not prove the absence of every possible memory leak, field allocation issue or long-session problem.

[Final-source clean retention](../../../ux-evidence/d04-us-heatmap-return-20261104/retention-qualified.json) · [Earlier eight-cycle matrix](../../../ux-evidence/d04-us-heatmap-return-20261104/retention-final.json) · [Small independent clean control](../../../ux-evidence/d04-us-heatmap-return-20261104/retention-cdp-only.json)

The timing mode records balanced `hm-refresh` registrations, stable interval count and no extra heatmap fetches. The current owner intentionally retains one ten-minute interval per encountered feed. Short-run registration checks do not prove the full polling cadence or every hidden-tab/network-failure path.

## Browser destination and cache boundary

The committed S&P snapshot supplies absolute app-origin Terminal links. A local default Terminal base is a different origin, so the probe explicitly uses the **existing** `MM_TERMINAL_BASE` configuration seam to match those links. The browser intercepts that origin with a labelled controlled fixture. No request reaches a real account or production Terminal; no payload URL is rewritten.

The native overlay's existing symbol transport, history guard and close handling execute in these controlled contexts. Real production Terminal rendering, entitlement, cross-origin policy and owner-qualified D07/F01 composition remain unproven.

The generated page's heatmap asset fingerprint is checked through the existing `scripts.optimize_assets.make_optimizer` owner before publication. The final validation records the exact requested URL and generated bytes.

## Regression, visual proof and reproduction

Current regression evidence is in [lifecycle-validation.json](lifecycle-validation.json) and the [affected browser report](../../../ux-evidence/d04-us-heatmap-return-20261104/lifecycle-functional/browser-report.json). Source hashes are explicit. The 24 accepted rest/focus/hover captures remain the List visual baseline; this repair changes work and lifecycle behavior, not CSS or visible row markup. Fresh affected functional screenshots cover the final served page and return/search/disclosure states.

Run the existing functional driver and the new finite probe from the original managed workspace:

```sh
python3 scripts/verify_us_heatmap_return_browser.py --out ux-evidence/d04-us-heatmap-return-20261104/lifecycle-functional
python3 scripts/verify_us_heatmap_lifecycle_browser.py --cycles 8 --out ux-evidence/d04-us-heatmap-return-20261104/performance-qualified.json
python3 scripts/verify_us_heatmap_lifecycle_browser.py --retention-only --cycles 3 --out ux-evidence/d04-us-heatmap-return-20261104/retention-qualified.json
```

Timing-mode raw global memory counters are explicitly **UNQUALIFIED** because that driver retains queried targets. Use the separate retention mode for collection assertions. This is one finite evidence helper, not a new product lifecycle owner or background runner.

**Acceptance:** scoped A061/A063 evidence and causal source repairs only. All 75 whole-D04 acceptance cases remain unpromoted. The original packet, accepted Confluence work, regional owners, D23 persistence, provisional F01/F02 composition and all release holds remain in force.
