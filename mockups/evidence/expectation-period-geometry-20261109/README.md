# Expectations: period-qualified geometry and recoverable interaction

## Current status

**This branch publishes the build contract and Paper continuation. The four geometry implementation files and their executable evidence have not been published.** They were implemented and exercised in the attended workspace before that environment became unavailable. Do not treat this branch's inherited product files as the geometry implementation.

The parent repair is [PR #10880](https://github.com/mastermindx-market-intelligence/macro/pull/10880), head `29d785794dcd86408ac4c9ae546fdfccd20ecc65`. It fixes comparable percentage readouts and duplicate chart handlers. Its [immutable implementation contract](https://github.com/mastermindx-market-intelligence/macro/blob/60fdcc41c30ef5db81f04f30ad8991de1cb527ea/mockups/evidence/expectation-readout-20261109/README.md) remains the published source/proof owner.

This continuation uses governance pin `Mastermind@5c3d3885234358aefb97ecdbc59be0864df14f8b`. It extends the existing Expectations period-binding discovery; it does not create another discovery, loader, router, retry service or data owner.

## User experience

A user selects a ticker, metric and horizon, then inspects successive captures. The explorer should make three facts easy to distinguish: when a value was captured, the fiscal period it describes, and whether the adjacent observations can be compared.

The locally qualified candidate adds one short selected-period line beneath the existing readout. It joins chart values only inside a known common fiscal period. A period change leaves a visible gap and an isolated point. Unknown period metadata also breaks the path; it is not presented as evidence of a rollover.

The existing “Show the numbers” action reveals the raw values and each capture's period. On a phone, the table scrolls inside its existing container, keeps the capture-date column visible, and gives keyboard users a labelled region with a visible focus ring. The low/high readout wraps without overlapping the analyst count. No new navigation page or explanation panel is added to the product.

### Behavior contract

| Situation | Geometry | Readout and table |
| --- | --- | --- |
| Adjacent values have the same known common period | Connect the available series within that contiguous run | Show the selected period; the parent's percentage rules apply |
| Fiscal period changes | End the old run and start a separate run | Keep the new value; show Period changed when it is the comparison reason |
| Common period is unknown | Keep individual average/median markers; do not connect them | Show that the estimate period is not established |
| Low and high exist, but no common period is established | Draw no range band or singleton range | Preserve both raw bound values |
| A qualified low/high observation stands alone | Draw its short vertical range | Keep its capture and period context |
| Average is absent but qualified median/range exists | Preserve the available median/range geometry | Show No average for the average comparison |
| Selected metric has no captures | Clear the old chart, period and live announcement; remove the inert chart tab stop and hint | Use the existing empty state; restore chart focus and hint when data returns |

## Producer ownership and data policy

The existing [builder](https://github.com/mastermindx-market-intelligence/macro/blob/29d785794dcd86408ac4c9ae546fdfccd20ecc65/scripts/build_expectation_surface.py) remains the output owner. Its per-ticker point keys stay frozen:

`{at, period_end, average, median, high, low, analysts}`

The candidate changes the meaning of the common `period_end` qualification without introducing a second per-field schema:

1. Retain the same last-per-field rows used to emit the values. Discarded duplicates cannot lend their fiscal period to the retained row.
2. A retained value with a non-null `missingness_reason` emits null.
3. Consider only retained, present average, median, high and low values. Zero is present; absent values do not disqualify the values that remain.
4. Emit a common period only when all these present estimate values have a known, equal period. Otherwise emit null.
5. Analyst counts and unrelated observation types cannot supply or qualify an estimate's period. Counts remain observations at the capture.

This is intentionally conservative. If the average has a valid period but another present estimate does not, the combined display can withhold an otherwise valid average comparison. Likewise, an unrelated conflicting estimate field can suppress a range whose own bounds might agree. The frozen combined schema cannot prove those narrower field-level relationships.

The existing valid-average owners for breadth, comparable pairs and movers remain unchanged. One regression explicitly preserves a +10% average-based mover while the stricter combined display withholds its comparison. Do not “repair” that distinction by changing the mover mathematics to match the display.

Null common period means “not established.” It does not distinguish missing from conflicting metadata, and it does not prove that a rollover occurred.

## Consumer implementation seams

The existing [explorer template](https://github.com/mastermindx-market-intelligence/macro/blob/29d785794dcd86408ac4c9ae546fdfccd20ecc65/templates/expectation_surface.html.j2) remains the consumer owner.

- `runsOf()` splits on missing series values, changed periods and unknown periods, preserving original capture indices. A → B → A never reconnects the two A observations across B.
- Average and median singleton runs become individual markers. A range requires both bounds and a known common period, including singleton ranges.
- The vertical scale includes median values. Its rounded lower and upper extents contain every plotted value; the same final extent drives values, tick labels and grid lines. The median 500 / range 550–620 case previously exposed an out-of-bounds range.
- The selected-period line, raw-value table, chart caption and announcement derive from the selected point. Pointer preview returns to the committed keyboard/click selection.
- The existing delayed announcement captures document, metric, horizon, point array and selected index, then verifies them before delivery. `renderView()` cancels an old announcement and clears the live region.
- Empty-state cleanup removes the actual `.es-empty-t` overlay. It suppresses the chart's tab stop and keyboard hint while empty, and restores them when points return.
- Nested metric and horizon substitutions are constructed separately for English and Chinese captions. A live locale change must not leave English “revenue” or “Current Q” inside the Chinese branch.
- The parent's per-node chart binding guard remains intact. A restored chart must retain exactly one keyboard, pointer move, click and pointer-leave handler.

### Mobile table ownership

Use the existing `.tbl-scroll` mechanism. Mark the existing numbers container with that class so shared `wrapTables()` does not create a nested scroll container. Give `#es-ticker-panel`, the intermediate grid child, `min-width:0`; applying a scrolling rule only to its descendant does not prevent the grid track from widening.

The qualified local design uses a 560px minimum table, a 120px sticky first column, and nonwrapping capture dates. The existing numbers container receives `tabindex="0"`, `role="region"` and `aria-labelledby="es-ntable-cap"`. Its 2px focus treatment is a material interaction style and must pass the repository's existing focus-evidence gate.

Do not add another scrolling service, observer or global wrapper. Do not suppress unrelated shell controls to make a screenshot look cleaner.

## Observed local qualification

These results were observed before environment loss. The executable receipts and image files are still **not canonically published**; the following is a continuity record, not a substitute for those artifacts.

| Proof | Observed result |
| --- | --- |
| Full affected Python/Node rendered-consumer suite | 64 passed, zero failed/skipped |
| The 24 new cases against the parent implementation | 20 failed, 4 passed; 40 existing cases deselected |
| Actual browser workflow matrix | 8 cells passed: 1440×900 / 390×844 × dark/light × EN/ZH |
| Additional browser fixtures | Mixed estimate periods, conflicting low/high periods, median/range bounds and nested caption translation passed |
| Final mobile table checks | No readout overflow; date on one line; one scroll owner; keyboard scrolling; capture-date column retained |
| Visual inspection | All eight final workflow crops inspected; Chinese glyphs, range gap, labels and mobile focus/table layout visible |
| Canonical rest captures | 8 of 8 captured with the unchanged canonical capture module |
| Existing UI evidence gate | Correctly remains open: new focus CSS requires canonical forced-focus captures |

The final local core-file Git blobs were:

| Local implementation path | Git blob |
| --- | --- |
| `scripts/build_expectation_surface.py` | `b2b3e9d641b6d0b0f06e624181b1b534812dfe6f` |
| `templates/expectation_surface.html.j2` | `6620aefef92ec7b4aca6508eba2acb3acf903890` |
| `tests/test_build_expectation_surface.py` | `05ebf1077670e1896a694eb8397a2239e25b4022` |
| `research/alpha_intelligence/expectation_market_dynamics/EXPECTATION_SURFACE_PAGE_CONTRACT_2026-10-21.md` | `60ecebc84b9b68b06eeeda9855c1f02d2609e8d9` |

These hashes identify local content; they are not claims that these objects are present in GitHub.

The real browser was Chromium 149.0.7827.0 with Playwright 1.61.0. The pinned browser binary SHA-256 was `434d2607c55941dcaa7fdd19b0800ee90488922fd9744a6642ef527ba8fabf63`. Canonical capture module blob: `78ba651d2996a64231c738a133ed465d73dd8caf`. The isolated fixture used repository Inter assets and the previously verified Noto Chinese fallback. No product dependency or font change is part of the candidate.

The fixtures are synthetic RO, MX, MC and RX. They do not establish live market, authentication or deployed acceptance. The canonical manifest retains the omitted account/overlay asset 404s. The fixture's mover lists are empty, so these results do not prove mover-origin navigation.

## Reconcile, publish and prove

The unavailable workspace was `/workspace/scratch/9825befc0cf0/expectation_period_phase/`. Product files are in `candidate/`; the baseline, test XML, browser receipts, fixture and capture tools are siblings.

1. Recover that original workspace if available. Read the four core files and verify the hashes above before treating the local implementation as recovered. Do not reconstruct it from memory and attach the old tests' claim to newly written bytes.
2. Reconcile the interrupted local operation before replay. Cell 207 was stopped after the environment became unavailable while appending keyboard preparation to `run_capture.py`. The adapter change, following archive step and proposed focus run were not read back. This is a local uncertainty; no geometry GitHub source publication or Paper mutation had been attempted at that boundary.
3. Finish the canonical focus capture through the real existing button: focus “Show the numbers,” press Enter, then let the canonical `focus(#es-num)` operation apply. Assert active element, `:focus-visible` and 2px outline at capture time. Preserve all 8 rest and 8 focused theme/locale/viewport cells. Do not merely label a rest screenshot as focused.
4. Run the existing `scripts/check_ui_visual_evidence.py` on the actual four-file diff and retained evidence. The earlier rest-only manifest correctly failed this gate; do not edit its outcome or lower the requirement.
5. Publish the exact implementation, test XML, browser/capture receipts, selected screenshots and complete contract on this owned continuation branch. Preserve parent PR #10880's delivery lane and any actual hold. Re-read the current parent/main and resolve only owned overlap before preparing the final PR.
6. Use ordinary affected CI and the existing merge controller. Do not hand-edit generated `site/expectation_surface.html` or publish fixture output as market data.
7. After merge, let the incumbent render owner produce the page and verify the deployed comparable, changed/unknown period, raw-table and empty-return paths. Source tests and fixture screenshots do not replace that proof.

The parent CI dependency-path repair has passed its contract-delta check. A separate pack failed in `actions/setup-python` while downloading Python 3.12.13 with HTTP 504, before semantic tests. The first targeted retry request was rejected because the rest of that run was still active. This is not a reason to change the Python version, weaken a gate or replay through a different carrier.

## Next safe implementation: loader ownership and error recovery

A read-only review of the existing loader identified a separate concrete failure. Each `open(T, opts)` invocation has loading, timeout, success and failure effects, but those effects do not verify that their request still owns the current selection. A stale loading timer or error can replace a newer successful result. Comparing ticker strings is insufficient: the first A request in A → B → A can reset the third A's selection.

The smallest next repair belongs inside the existing `open()`, `cur`, `saveBody()` / `restoreNodes()` and `afterLoad()` seams:

- Give each valid open attempt a unique current identity and capture its own target/options.
- Retire the previous attempt's timers. Fetch abort may save work, but correctness must survive ignored aborts and JSON delivery already in progress.
- Fence loading, restoration, errors, busy state and final commit to the current identity. Validate that the delivered document's ticker matches the requested ticker.
- Preserve the original body before showing an active error. Fast failures currently discard it without saving; slow failures restore it and then discard it. A subsequent retry can otherwise leave missing chart/readout nodes or preserve the error panel itself.
- Cancel a queued announcement when a new ticker selection starts. The geometry phase's callback guard sees the old committed document until delivery.
- Give metric/horizon changes during a pending ticker load an explicit policy. If controls are temporarily disabled, restore each horizon's real availability through `updateRadios()`; do not indiscriminately enable all of them.

Required proof should deliver older success, loading and failure after a newer success; A → B → A; an active fast and slow error followed by successful retry; and headers received while JSON remains pending. Every successful recovery must restore the original chart and one-step keyboard movement.

This would prove latest-open ownership and recoverable errors. It would not complete all navigation/refresh semantics.

### Remaining navigation work

Search currently drops the selected horizon. `pickHorizon()` can silently substitute +1y or another available horizon. Distinguish an absent preference from an explicitly requested horizon; retain explicit choices and use the existing empty state when unavailable.

Mover entries already contain metric, horizon, fiscal period and capture timestamps, but the consumer discards some context and selects the latest series point. Its ticker-only URL reloads into EPS. Preserve metric/horizon through the existing URL owner, then match the mover's existing period and capture timestamps to the loaded series. Show missing or ambiguous context rather than silently substituting a different point.

Current points do not carry collection-session IDs or a source-generation identity. Matching existing timestamps and period can strengthen semantic binding; it cannot prove exact source-generation binding. Keep that limitation visible in the original discovery, and use a generated mover fixture for the later navigation proof.
