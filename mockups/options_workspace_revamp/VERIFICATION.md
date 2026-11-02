# Verification record — options workspace reference

Status: supporting source reference, NOT_APPLIED_TO_PAPER. No production replacement accepted.

## Reproducible baseline

Source candidate before implementation: macro@20b3599ba79bd635f49d3dac6a2efb81a2f64f8b (production template still unchanged from initial base).

Focused Python baseline:
`python3 -m pytest tests/test_build_options_command.py tests/test_options_intel_brief_ui.py tests/test_render_options_workspace_scope.py -q`
Result: 189 passed, 3 skipped in 18.49s. See baseline_pytest.txt.

Isolated source-native Chromium tests use a new ephemeral browser context, a loopback-only HTTP server, synthetic repository test fixtures, and blocked external egress. They do not attach to a user browser/profile and do not use data: navigation. Fixture output is under this directory, never site/data. These checks are synthetic behavior evidence, not evidence of current market records or production service health.

Run render_acceptance_fixture.py, serve the repository through the owned localhost fixture server, then run verify_workspace.py --label baseline.

| Baseline check | Result |
|---|---|
| Filtered Scanner CSV contains the filtered row | Pass |
| Scanner clear restores all fixture rows | Pass |
| Flow, Leaders and Ticker load meaningful content | Pass |
| ArrowRight selects the next task tab | Fail: remains Brief |
| Latest ticker response owns displayed values | Fail: URL QQQ, stale SPY result displayed |
| Reentering pending Scanner deduplicates requests | Fail: 2 requests |
| Hanging Scanner request offers usable timeout/retry | Fail: no recovery action |
| Leaders research stamp uses its market session | Fail: November build date replaces August source date |

The five failures reproduce existing defects; they are not candidate regressions. Candidate acceptance must turn these green without weakening the assertions or hiding errors.

## Reference visual review

verify_reference.py produced 12 main-content captures, including Brief at 1440/390 x light/dark x EN/ZH and desktop light EN previews of the other four tasks. reference-report.json recorded no page-wide horizontal overflow or page errors in these captures.

The principal visually inspected V4 desktop light EN, mobile dark EN and mobile light ZH. The compact unavailable notice, genuine source dates, readable two-line mobile level legend, one-day move horizon, five visible task labels, and corrected disclosure row were inspected. These are content-area reference observations, not shared-shell or complete-workflow acceptance. Reference Flow/Scanner/Ticker/Leaders previews demonstrate composition only; all production capabilities must be preserved in implementation.

Initial risk: the actual shared assistant orb can overlap mobile right-column content at some scroll positions. Integrated full-page checks must establish readable/reachable controls and evidence. Do not hide the assistant or crop away the issue merely to manufacture acceptance.

## Independent principal risk review

After candidate integration, prioritize:
1. Slow prior ticker success AND failure cannot overwrite or clear a newer successful selection, heading, chart, loading or error state.
2. Leaving/reentering a pending task does not duplicate requests or listeners; recovery cannot be overwritten by the original late response.
3. Current Brief -> dated history -> Ticker -> Back/Forward/reload retains honest source/session context. A recent render/fetch never promotes old data.
4. Every supported task deep link and ticker query initializes and restores meaningful state without redundant history or transient default-SPY claims.
5. Arrow keys, Home/End, tab focus, hidden panels, typeahead, and disclosure destination focus work in a pointer-free journey.
6. Full 390px page in both themes/locales keeps all tasks, source receipts, critical evidence and retry controls readable/reachable with the real assistant present.

## Remaining gates

- Paper exact catalog qualification and actual editable artboards/screenshot/JSX proof.
- Integrated source implementation, candidate behavior and full visual matrix.
- Independent non-author source/reference review, required CI, release receipts and real production journey proof.

## Follow-up verification

The separate clock-baseline check fails as expected: three Leaders research stamps show the fixture build date November 2 instead of its session_date August 12. See runtime-clock-baseline.json. Source provenance is in SOURCE_AUDIT.md.

prepare_published_fixture.py recovered all 17 inputs at e4009c94d75770739844240b22f5fc915668aa9b into the ignored QA fixture tree. capture_published_workspace.py records full viewports including the shared navigation and assistant; its baseline three views pass overflow/page-error checks. The helper can run the full five-task x two-width x two-theme x two-language matrix against the integrated candidate. No production data writes or provider requests occur.

The supporting reference also now has two true initial-viewport captures (scroll reset to zero) with the shared navigation. Independent principal visual review finds all five mobile tasks discoverable and the first current index closes within the initial viewport. This still does not accept other task layouts, expanded states, Paper or the eventual integrated build.

Reference reachability check: 1440 light EN and 390 dark ZH both expose every SPY price/regime/level/move item after normal scroll placement; Source details takes keyboard focus, opens with Enter, and has an unobstructed activation point. The first probe sampled a smooth scroll before it settled; deterministic scroll placement corrected the harness timing, without changing the page or hiding the assistant. See visual/reference-reachability.json and reachable-spy images. No global assistant change is warranted by this reference evidence. Repeat the boundary on the integrated candidate.

## Navigation and fixture integrity — 2026-11-02

verify_navigation.py exercises the actual search controls, direct links/reload, scoped slash shortcut, Back/Forward, hash changes, and both slow-success and slow-failure ticker races. Original source: 4 pass / 5 fail. The failures are missing active-descendant exposure in typeahead, collapsed task history, no visible-task update after a hash change, and both older SPY outcomes overwriting a newer QQQ choice. See navigation-baseline.json. These are acceptance targets, not candidate regressions.

The QA fixture previously inserted a document-wide base element for source-tree assets. That also redirected relative history URLs to /templates/. fixture_assets.py now rebinds only script/link/image asset attributes, preserving each fixture document's real URL semantics. The navigation failures were reproduced again after this correction. The current three-view published fixture capture still has no overflow or page errors; no production source was altered.

Source boundary reviewed: build_indexes takes each index interpretation from its own gex summary.regime and meta.asof, not the separate market_structure posture. All four published index records are Oct30 short-regime model estimates, with regime_passport basis=assumption and verdict=display-only. The Oct20 market-wide posture must keep its own date; the current index interpretation may remain beside its own Oct30 levels with model-estimate context.


## Candidate implementation acceptance — 2026-11-02 06:20 UTC

The principal implementation now passes **199 tests, 3 environment/data skips** across test_build_options_command, test_options_intel_brief_ui, and test_render_options_workspace_scope. Existing scientific, ranking, enum, bilingual and full-capability protections remain. Old literal layout pins were replaced by semantic source-receipt, main-landmark, current-vs-historical Brief, and preserved-lazy-workspace checks. Ten additional cases cover independent dates, missing/nonfinite diagram values, source clocks, and complete retained Brief behavior.

Real isolated Chromium: runtime-candidate-final.json **10/10**, navigation-candidate-final.json **9/9**, recovery-candidate.json **7/7**. Coverage includes hung-request retry, invalid successful-JSON retry, supporting-data retry preserving primary evidence, duplicate in-flight suppression, old success and old failure races, history and bare-ticker routes, research-origin/focus restoration, aria-activedescendant, Escape and ArrowDown reopening, filtered/sorted CSV and clear, and Leaders session clock distinct from rebuild time.

visual-candidate-final/report.json records **40 views** at 1440×1000 and 390×844, light/dark, EN/ZH, all five tasks. No document overflow or JS errors. The real shared shell is included. Exact published-data source is e4009c94d75770739844240b22f5fc915668aa9b (17 immutable JSON blobs; no producer/site-data writes). Fixture manifest records source/template/builder fingerprints; no data dates are substituted. The working source received an EOF/trailing-blank cleanup after the final behavior proof; semantic source is unchanged. CI/reviewer will qualify the committed source independently.

Parent visually reviewed desktop Brief/Scanner/Flow/Ticker/Leaders and mobile Brief/Scanner/Ticker across themes and locales, then tightened mobile header and corrected Ticker search localization. The two dated clocks inside the payoff fold remain visible. Component error/partial-recovery captures are in visual-candidate-states.

**Remaining release gates:** actual editable Paper implementation with screenshot/JSX proof; independent committed-candidate review; exact-head hosted checks; normal narrow Macro publication; production URL interaction/layout proof. These receipts do not claim deployment or upstream data freshness.

## Expanded production-candidate review — 2026-11-02 06:42 UTC

verify_expanded_views.py now records **74/74** checks in visual-candidate-expanded/report.json at desktop light EN and mobile dark ZH / light EN. This checks actual published-data states: source/history keyboard disclosures and focus, dual-date payoff details, full-row mobile payoff layout, index evidence reachability with the shared assistant, real history versus unavailable intraday record, all 21 advanced numeric controls, each of three horizontally scrollable Scanner views, lazy raw-structure SVG rendering, exact selected-symbol Terminal return route, Leaders expansion, document containment and page errors. The report fingerprints the exact template/builder working bytes on d633 plus the final refinement; it is not falsely represented as the untouched d633 tree.

A fresh focused source run after those refinements passed **199 tests, 3 skips** in 31.99s. Five warnings came from pytest cleanup of a pre-existing unrelated temporary-directory tree; the session did not alter that tree.

The principal visually inspected the expanded mobile payoff in Chinese after widening the card and increasing essential numeric/footnote text. Original full-matrix evidence remains as historical proof of the unchanged workspaces; the expanded report proves the subsequently adjusted layout and copy.

extract_paper_samples.py captures actual dated panel text, the first eight visible Scanner rows and four Ticker SVGs from the same 17 exact published JSON blobs. paper_actual_samples.json is design input with provenance, not a new market dataset or a claim that Paper is already applied.