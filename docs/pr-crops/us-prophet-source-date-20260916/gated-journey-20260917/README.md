# Gated candidate/plan date claims — original #7187 continuation

The accepted review `5696643747` identified three EN/ZH controls still borrowing “tonight” from a stale candidate screen or historical plan book. This continuation changes only those six literal strings in the existing dashboard template. Counts, dates, locked populations, markup, styles, source-selection logic and all plan decisions are unchanged. The historical plan wall is source-neutral; the candidate heading keeps its actual `as_of` or explicit unavailability.

## Verification

Fifteen new real-splitter/render cases failed before the six-string amendment. The existing candidate, reader-cache, and workflow-size owners then passed **72 tests**. The cases cover stale/current/missing/null/empty candidate dates, a 3-of-5 gated candidate preview, historical plan rows, and a resolved record reducing the visible plan preview while total arithmetic remains exact.

The real preserved full-build board/book were passed through the existing splitters and dashboard environment. All rendered HTML is identical to the exact preimage except the six reviewed language strings: candidate preview 3 of 42 / 39 withheld; historical plan preview 3 of 415 / 412 withheld. Original input files were not changed. `real-render-comparison.json` binds those inputs, the source template and both output documents. Unrelated view-model fields use the repository's minimal fixture, so this is not a complete canonical-site build.

Eight fresh local-browser cases (EN/ZH × dark/light ×390/1440) pass with the real source-view button, unchanged 3-card previews, the corrected wall text and no page errors or width overflow. The ordinary candidate-to-plan button is clicked once; access tier is never changed and no locked cards are revealed. The candidate dark-English and plan light-Chinese mobile images were visually inspected.

This is anonymous local fixture evidence, NOT authenticated or production serving. All external requests are refused; protected payload/me responses are explicitly 401 and optional live overlays 404. The initial overbroad local fixture had mistakenly served an old repository premium payload, so the walls disappeared; its assertion failed and that run is not accepted evidence. The route was corrected without changing any product source. A diagnostic locator also timed out; no new product defect or paid-access result is inferred.

## Real PR code gate

The actual manifest placed this suite only in a data-gated job. The amendment adds one targeted command to the existing **washout-turn-organ / gate:code** job, selecting the five original heading cases and fifteen gated-journey cases. Its exact command passed **20 tests**. Parsed YAML equality proves every other step, job, dependency, timeout and rule is unchanged; the complete data-gated battery remains. No new CI job, runner, workflow, queue or gate type was introduced.

## Reproduce and boundary

Run the commands stored in `green-result.json` and `code-gate-result.json`. For browser evidence, render `_base_vm` with the hash-identified preserved board/book through the existing splitters and `_us_life_repair_context`, save `real-gated-page.html` beside `real-render-comparison.json`, and run the included verifier with the corresponding installed Playwright/source paths. It uses a fresh isolated browser, never a saved profile. The gate's 401 behavior is fixture-only.

Procedure: Mastermind `8b231e8267f09cfb002ed3e87bec14906dce1720`. Same direct #7187 branch, previously clean/idle, no new worker assignment or source transfer. Core behavior remains BUILT_NOT_PROVEN until independent review, exact-head CI, accepted integration, canonical publication and authorized user-journey proof. Other source owners, including #7206 and #7066, were not edited.
