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

The four failures reproduce existing defects; they are not candidate regressions. Candidate acceptance must turn these green without weakening the assertions or hiding errors.

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
