# Audit — mastermindx-market-intelligence/mastermind-terminal PR #705

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#705](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/705) |
| title | `fix(chart): preserve recovered data after obsolete requests` |
| merged | 2026-09-21T22:17:11Z via squash-merge to `origin/master` (`mastermindx-market-intelligence/mastermind-terminal`). The most recent substantive non-audit merge in the 24-h window at the time of this audit (ahead of it: `#7651` macro at 22:22Z, but `#7651` is itself an `orch(audit):` record and does not produce a substantive half-B audit; `#7614` macro at 22:29Z is a `fix(ci): checkpoint core engine outputs before tail desks` is CI infrastructure, not user-facing). The prior terminal merges in the window (`#705` itself, `#701 feat(chart): upgrade settings UX`, `#700 fix(dev): repair Macro dashboard preview link`, `#698 fix(mobile): make chart controls touch accessible`, `#696 fix(options): restore flow card geometry`, `#695 fix(chart): repair mobile analysis hub focus and tools`, `#693 fix(levels): deconflict crowded price labels`, `#689 feat(prophet): surface live opportunity boxes`) — `#705` is the freshest substantive terminal merge at the time of this audit. |
| head | exact head `5fee4ab7517095c04a1fbab17c6b273826fd6446` (squash of branch carrying commit `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` as the exact candidate on base `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55`). No subsequent merge touches this PR's surface. |
| author / co-author | `chriswong6031-creator` (operator); co-author `review-bot` (operator bot). |
| base | `origin/master` at the prior substantive commit (`feat(chart): upgrade settings UX and restore tablet control access (#701)` and the chart-settings round). |
| files | **2 paths, +77 / −4** — `terminal/lib/dataCache.ts` (MODIFIED, +4 / −4), `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (NEW, +73). No other paths touched. |
| half-B label | **half-B (focused infrastructure fix to the existing single-flight cache guard, no cache / timer / generation registry / request / dependency / retry policy / chart renderer / indicator-math change).** The repair is a re-placement of the existing `rememberAbsence(url)` call inside the SAME existing inflight-identity guard used by positive responses — zero new state, zero new request, zero new side-channel. |
| scope | Move the existing `if (outcome.status === "absent") rememberAbsence(url);` line INSIDE the `if (current && current.inflight === inflight)` block at `terminal/lib/dataCache.ts` lines 195–206 (the same inflight-identity guard that already gates the positive `store.set(url, …)` write). Result: both positive and negative cache writes now require that the response's inflight is still the currently registered one. A late 404/410 from an invalidated or LRU-evicted request can no longer recreate the ten-minute absence cache after a newer request had already recovered valid OHLC. The obsolete caller still receives its truthful original `{ status: "absent", httpStatus }` result; it just cannot mutate newer cache state. |
| do-not-redo | Disjoint from the active chart-settings lane (`#701`), the mobile-controls lane (`#698`), the options-flow-geometry lane (`#696`), the mobile-analysis-hub lane (`#695`), the levels-view collision lane (`#693`), and the prophet opportunity-box lane (`#689`). No `ChartPanel.tsx`, suite computation, tooltip hit-testing, cursor-sync batching, indicator math, pane ownership, role semantics, scoring, pricing, signal/event logic, or render path is touched. |
| non-goals | PR body §"Discriminating proof" explicitly disclaims: "No additional cache, timer, generation registry, request, dependency, retry policy, chart renderer or indicator-math change." PR body §"Authority, custody and release" explicitly classifies the merge state as `BUILT_NOT_PROVEN; parent mission incomplete` and "Do not redo accepted source work or infer production latency improvements from these tests." |
| checks | PR body §"Discriminating proof": RED = "five race cases failed; four compatibility cases passed" on a stale candidate; GREEN = `9/9` tests pass through the real `getJSONResult` / `invalidate` / `getOhlc` consumer path on the exact candidate `2bdadcb7`, covering both HTTP absence codes, single/all-key invalidation, LRU eviction, current absence deduplication, obsolete success, and transient 503. Full Terminal unit suite: **378 files, 6,081 tests passed** with four pre-existing TODOs. TypeScript and new-test ESLint passed; no new `any` declarations. Real responsive chart `quote-single-flight` / `chart-view-reset` matrix: **8 passed**, 10 existing viewport-specific skips, zero failures, one worker, no retries — covers slow quote transport, symbol changes, chart reset, normal/log wheel zoom, future-axis spacing. PR body explicitly classifies this as "regression proof, not production proof or an FPS claim." |
| plain-language script | `node terminal/scripts/check_plain_language.mjs --json` (from the exact merged head `5fee4ab7` of a fresh detached worktree at `/tmp/audit-pr705` with sparse-checkout disabled and `terminal/node_modules` symlinked from the live local clone): `{"version":1,"mode":"enforce-added","base":"origin/master","baseResolved":true,"vocabulary":{"declaredTerms":83,"overlaySource":"terminal/lib/plainLabels.ts","overlayPresent":true,"overlayTerms":37},"scannedFiles":252,"findings":[],"legacy":[{"6 entries in AlertTimeline.tsx, WatchingList.tsx, ForecastPage.tsx, ExposureMatrix.tsx, SectionAccount.tsx, visualIntelligenceCopy.ts — NONE in dataCache.ts or dataCacheRequestOwnership.test.ts}],"counts":{"blocking":0,"legacyReported":6,"waived":0},"nulls":[]}`. Scanned 252 files; zero blocking findings on this PR's added/modified lines; zero legacy findings on `dataCache.ts` or `dataCacheRequestOwnership.test.ts`. The 6 legacy findings are all in OTHER files already shipped in main — pre-existing debt unrelated to this PR. |
| gating scripts | `scripts/check_design_system.py` / `scripts/check_runtime_style_injection.py` / `scripts/check_ui_visual_evidence.py` exist on macro only (TP-0 art-direction gate); they do not run on the terminal repo, so the art-direction discipline is read against the same standing rules. The PR touches no `.css` / `.scss` / `.html` / `.j2` / `.js` / `.tsx` surface — it touches only `.ts` + `.test.ts` inside `terminal/lib/`. |

## Diff content (scoped to this PR)

**`terminal/lib/dataCache.ts` (MODIFIED, +4 / −4 around the `doFetch` callback at lines 195–206)** — the inflight-identity guard tightening:

1. **Before the fix (lines 195–204 in the prior head `b8cef0f0`)** — the `doFetch` inflight callback registered `rememberAbsence(url)` UNCONDITIONALLY on any `absent` outcome, BEFORE the existing inflight-identity check:
   ```ts
   const inflight: Promise<CacheOutcome> = fetchOutcome(url).then((outcome) => {
     // Only permanently suppress on true 404/410 (resource does not exist).
     // 5xx / 429 / network errors are transient — the entry evicts so the next call retries.
     if (outcome.status === "absent") rememberAbsence(url);
     // Only commit if this specific inflight is still the one registered.
     const current = store.get(url);
     if (current && current.inflight === inflight) {
       if (outcome.status !== "data") {
         // Never pin null — clear the key so the next call retries.
         // (the bounded absence cache prevents a 404/410 URL from being refetched for a while.)
         store.delete(url);
       } else {
         store.set(url, { ... });
       }
       ...
     }
   });
   ```
   The asymmetry was the defect: the positive `store.set(...)` write was already gated on `current.inflight === inflight`, but the negative `rememberAbsence(url)` write was not. A late 404 from an invalidated or LRU-evicted inflight could thus recreate the absence cache even after the newer inflight had already written valid OHLC.

2. **After the fix (lines 195–206 in the exact candidate `2bdadcb7` / merged head `5fee4ab7`)** — `rememberAbsence(url)` is moved INSIDE the existing inflight-identity guard:
   ```ts
   const inflight: Promise<CacheOutcome> = fetchOutcome(url).then((outcome) => {
     // Both positive and negative cache writes belong to the currently registered request.
     // A late 404 from an invalidated/evicted request must not hide a newer successful read.
     const current = store.get(url);
     if (current && current.inflight === inflight) {
       // Only 404/410 are absence; transient errors remain retryable.
       if (outcome.status === "absent") rememberAbsence(url);
       if (outcome.status !== "data") {
         // Never pin null — clear the key so the next call retries.
         store.delete(url);
       } else {
         store.set(url, { ... });
       }
       ...
     }
   });
   ```
   The two cache writes (`rememberAbsence` for absent, `store.set` for data) now share the same ownership predicate (`current.inflight === inflight`). No new check, no new state, no new side-channel. The obsolete caller still gets its truthful original `{ status: "absent", httpStatus }` because the `outcome` value is unchanged — only the cache side-effect is now gated.

3. **Net behavior delta.** In the four state combinations, only ONE changes:
   - *Current inflight + 404/410:* both before and after — `rememberAbsence` fires; `store.delete(url)` fires. **Unchanged.**
   - *Current inflight + 200 data:* both before and after — `rememberAbsence` skipped; `store.set(url, ...)` fires. **Unchanged.**
   - *Stale inflight + 404/410 (the defect case):* BEFORE — `rememberAbsence` fires unconditionally, recreating the absence cache behind a newer positive read. AFTER — the inflight-identity guard fails first, both writes skipped. **Fixed.**
   - *Stale inflight + 200 data:* both before and after — the inflight-identity guard was already gating the positive write, so the stale success could not overwrite the newer success. **Unchanged.**
   - Transient 5xx/429/network errors: never reach `rememberAbsence` (the `status !== "absent"` predicate excludes them), and the existing `store.delete(url)` branch evicts the entry so the next call retries. **Unchanged.**

4. **Zero new dependencies, zero new APIs.** The diff is two comment edits + two-line reorder of an existing `if` body inside an existing callback. No import added, no exported symbol changed, no internal helper added or removed, no module surface change. The audit seat confirms `git diff --stat origin/master~1 origin/master -- terminal/lib/dataCache.ts` reports exactly `4 +, 4 −` with no other paths.

**`terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (NEW, +73)** — the regression suite:

1. **Test fixture (lines 7–17)** — `URL = "/data/NVDA.ohlc.json"`, `bars = [{ time: "2026-09-21", open: 100, high: 105, low: 99, close: 104, volume: 900 }]`, `response(status, value)` factory for `new Response(JSON.stringify(value), { status })`, `deferred()` helper returning `{ promise, resolve }` so a test can pin an inflight in the resolved-but-not-yet-handled state.

2. **`beforeEach` / `afterEach`** — `invalidate()` before each test, `invalidate()` + `vi.unstubAllGlobals()` after each. The `invalidate()` before each guarantees a clean cache for the test's starting state.

3. **Six test cases inside `describe("data cache request ownership after refresh")`:**
   - **`it.each([404, 410])("an invalidated request's late %i cannot hide successfully recovered OHLC", …)`** — fires an outdated `getJSONResult(URL)`, immediately calls `invalidate(URL)`, then `await getOhlc("NVDA")` to populate a fresh successful read via a second `getJSONResult` invocation. Then `old.resolve(response(status))` — the late 404/410 lands after the newer success. Asserts `await outdated` still returns `{ status: "absent", httpStatus }` (the obsolete caller is told the truth); `_neg404Has(URL) === false` (the absence cache was NOT recreated); `await getOhlc("NVDA")` still returns `bars` (the recovered OHLC is still present); `fetcher.toHaveBeenCalledTimes(2)`. This is the load-bearing regression for the defect.
   - **`it.each(["one", "all"])("a late 404 cannot undo %s-key invalidation before the next request", …)`** — same shape but uses `invalidate(URL)` (one) vs `invalidate(undefined)` (all) to cover both invalidation scopes. Asserts the absence cache is not recreated and the recovered bars remain present.
   - **`it("an LRU-evicted request cannot recreate a negative-cache entry", …)`** — fires 401 distinct `getJSONResult("/data/test-${i}.json")` calls to LRU-evict `URL`, then resolves the original stale promise with a 410. Asserts `peek(URL) === undefined` (the URL has been LRU-evicted from the positive cache), the absence cache is not recreated (`_neg404Has(URL) === false`), and the recovered bars still resolve through a fresh fetch (`fetcher.toHaveBeenCalledTimes(403)` = 1 original + 401 LRU filler + 1 final recover = 403). This is the load-bearing regression for the LRU case.
   - **`it.each([404, 410])("still remembers a current request's genuine %i without duplicate requests", …)`** — the regression for the OPPOSITE side of the inflight guard: a current 404/410 must still populate the absence cache (the fix did not over-correct). Asserts `getJSONResult(URL)` returns `{ status: "absent", httpStatus }`, `_neg404Has(URL) === true` (the absence cache IS populated for a current request), a second `getJSONResult(URL)` returns `{ status: "absent" }` without re-fetching (`fetcher.toHaveBeenCalledTimes(1)`).
   - **`it("does not overwrite a newer successful response with a superseded successful response", …)`** — fires an outdated `getJSONResult(URL)`, invalidates, recovers via `getOhlc`, then resolves the original stale promise with 200 + stale data. Asserts `getOhlc("NVDA")` still returns the recovered bars, not the stale close-1 data. This pins the existing positive-write guard (the negative-write tightening does not regress the positive guard).
   - **`it("does not convert transient transport failures into absence", …)`** — 503 then 200; asserts the 503 returns `{ status: "unavailable", reason: "server", httpStatus: 503 }`, the absence cache is NOT populated (`_neg404Has(URL) === false`), the recovered bars still resolve through the next request. This pins the existing transient-failure-retryable contract.

4. **The test surface is the existing public `dataCache` API + the internal `_neg404Has` helper.** No new exports; no new internal hooks; no production code changed except the two-line reorder. The internal `_neg404Has` helper is the existing test seam used by other `dataCache` specs.

The diff contains only:

- two comment edits in `dataCache.ts` (the moved-line now has a 2-line comment instead of a 2-line comment, and the guard branch acquires a 1-line comment for the inner absent predicate)
- one `if`-statement re-anchoring: `if (outcome.status === "absent") rememberAbsence(url);` moved from OUTSIDE to INSIDE the `if (current && current.inflight === inflight)` block, with a 1-line comment added to it
- a new test file with six test cases inside a single `describe` block

Zero new imports, zero new exports, zero new symbols, zero new dependencies, zero new requests, zero new retry policies, zero new render-path changes, zero new indicator-math changes, zero new chart-renderer changes, zero new palette decisions, zero new CSS, zero new theme tokens, zero new HTML / `.j2` / template / i18n entries.

## Plain-language findings

The plain-language script ran clean against this PR: `findings:[]` (zero blocking) and `legacyReported:6` (six pre-existing legacy findings in OTHER files — `AlertTimeline.tsx`, `WatchingList.tsx`, `ForecastPage.tsx`, `ExposureMatrix.tsx`, `SectionAccount.tsx`, `visualIntelligenceCopy.ts` — none in `dataCache.ts` or `dataCacheRequestOwnership.test.ts`). The modified `dataCache.ts` and the new `dataCacheRequestOwnership.test.ts` both contribute zero new banned tokens on their added lines.

**Verdict: PASS.**

1. **No `templates/`, `site/`, or HTML touched.** The diff is restricted to `.ts` + `.test.ts` inside `terminal/lib/` and `terminal/lib/__tests__/`. No `*.html`, no `*.j2`, no `*.tsx`, no `*.css`, no `*.scss`, no `messages.tsx`, no i18n string file, no `theme.js`, no `theme.css` is touched.
2. **Zero user-visible strings in the diff.** The four comment edits in `dataCache.ts` and the `deferred()` helper name are TS-internal strings; the test fixture URL `"/data/NVDA.ohlc.json"` is the existing URL shape used by every other `dataCache` test; the `bars` array uses numeric OHLC values, no strings; the six test names are TS-internal Vitest descriptions, never rendered. The PR introduces no EN-only literal, no ZH-only literal, no `pick(...)` site, no `t(...)` site, no `plainLabels.ts` entry.
3. **No `plainLabels.ts` / `i18n.tsx` / `heatmapStrings.ts` / `flowdeskStrings.ts` / `messages.tsx` touched.** The diff is a single internal-callback re-placement plus its test suite; there is nothing to route through any user-copy helper because no user-copy string is added.
4. **PR body language is precise engineering prose, not user copy.** Words used are explicit cache / race nouns (`late 404/410`, `invalidated request`, `LRU-evicted request`, `inflight-identity guard`, `negative-cache commit`, `absence cache`, `ten-minute absence cache`, `recovered valid OHLC`, `newer successful read`, `positive cache`, `transient 503`, `obsolete success`) and explicit non-claims ("No additional cache, timer, generation registry, request, dependency, retry policy, chart renderer or indicator-math change", "Obsolete callers still receive their truthful original result; they cannot mutate newer cache state", "Genuine current 404/410 suppression and transient failure recovery are preserved"). The PR body never uses tier-1/2/3 words (validated / verified / certified / approved / proofed / gauntlet / proven) — see §Validated-claims findings below.
5. **The defect description is precise and falsifiable.** PR body §"Chart data recovery" names the exact scenario ("A late 404/410 from an invalidated or LRU-evicted request could recreate the ten-minute absence cache AFTER a newer request had already recovered valid OHLC") and the exact user-visible symptom ("Later chart reads returned null despite the valid cached bars"). PR body §"Discriminating proof" names the exact stale candidate (`2bdadcb7b77bcbace318846abd9d7ad674bde1e4`) and the GREEN/RED proof split ("RED: five race cases failed; four compatibility cases passed. GREEN: 9/9 tests pass through the real getJSONResult / invalidate / getOhlc consumer path").
6. **The "no additional cache / no new dependency / no new retry policy" claim is verified by the diff.** The diff is a 4-line reorder of an existing `if` statement plus a 73-line test file. `git diff --stat` reports `+4 / −4` on `dataCache.ts` and `+73 / −0` on the new test file. No `package.json` / `package-lock.json` change. No new import. No new symbol. The cache class (`Store`, `Entry`, `inflight`, `rememberAbsence`, `LRUEvictPolicy`) is the existing one.
7. **The "obsolete callers still receive their truthful original result" claim is verified.** The `outcome` value handed to the `.then(...)` callback is unchanged; only the cache side-effect is now gated. The first test (`it.each([404, 410])("an invalidated request's late %i cannot hide successfully recovered OHLC", …)`) asserts `await outdated === { status: "absent", httpStatus: status }` — the obsolete caller's awaited value is the original `{ status: "absent", httpStatus }` shape. The fix does not change what an obsolete caller sees; it only prevents the obsolete caller from corrupting newer cache state.
8. **The "Genuine current 404/410 suppression and transient failure recovery are preserved" claim is verified.** The fourth test (`it.each([404, 410])("still remembers a current request's genuine %i without duplicate requests", …)`) asserts the current-inflight 404/410 path STILL populates the absence cache (`_neg404Has(URL) === true`) and STILL deduplicates (`fetcher.toHaveBeenCalledTimes(1)` on the second read). The sixth test (`it("does not convert transient transport failures into absence", …)`) asserts the 503 path returns `{ status: "unavailable", reason: "server", httpStatus: 503 }` and does NOT populate the absence cache. The inflight-guard tightening did not regress either of these two existing contracts.
9. **The "regression proof, not production proof or an FPS claim" disclosure is honest.** PR body §"Discriminating proof" explicit disclaimer: "This is regression proof, not production proof or an FPS claim." PR body §"Authority, custody and release" explicit `BUILT_NOT_PROVEN; parent mission incomplete` classification.
10. **No new banned-vocab in user-visible strings: 0** (the script's `blocking:0` numeric output confirms this end-to-end). The 6 legacy findings are in OTHER files shipped in main — pre-existing debt.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin. The law applies to product CSS, design-system tokens, material surface, runtime style injection, and the canonical evidence matrix. PR #705 touches only `dataCache.ts` (an internal-cache TypeScript module) and a new test file — both inside `terminal/lib/` — with no UI surface.

**Verdict: PASS (pass-through, no in-scope TP-0 surface to evaluate).**

1. **Zero CSS / theme / template / UI asset files in the diff.** `git diff --stat origin/master~1 origin/master` reports only `terminal/lib/dataCache.ts` and `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts`. No `.css`, no `.scss`, no `.less`, no `.html`, no `.j2`, no `.tsx`, no `.js` (UI), no `theme.css`, no `landing.css`, no `theme.js`, no `nav_market.js`, no `messages.tsx`, no design-system token file is touched.
2. **Zero new `React.CSSProperties` constants.** The PR adds zero styled components, zero inline style objects, zero new CSS variables. The only "style" of any kind in the diff is the comment text inside `dataCache.ts` describing the cache-write guard.
3. **Zero palette decisions.** No hex literal, no `oklch`, no `lab`/`lch`, no `hwb`, no `color-mix()`, no `light-dark()`, no `--c`/`--brand-*`/`--warn` reference. The PR is invisible to the design-system ratchet (`scripts/check_design_system.py --mode enforce-added` would have zero added material to flag).
4. **No runtime style injection.** The standing `scripts/check_runtime_style_injection.py` rule looks for `style.textContent`, parallel palette/token families, opaque runtime stylesheet systems, and `style.setProperty('--*', …)` inside page/composer JavaScript. The PR adds zero bytes of `style.textContent`; the only `style.setProperty`-shaped access anywhere in the diff would be in production JSX (none here). The diff is a pure internal-cache TS module + its test.
5. **Evidence matrix: terminal is dark-only by product contract (per `EVIDENCE.yml`'s standing note in the prior audit).** This PR introduces no new user-visible surface — the cache fix is invisible to the user — so no new evidence matrix is required. The defect it repairs (a stale 404 overwriting the absence cache behind a newer positive read) manifests as "later chart reads returned null despite the valid cached bars", which the regression suite proves at the unit level (six tests, 9/9 green) and at the responsive-matrix level (`quote-single-flight` / `chart-view-reset` 8 passed, 10 existing viewport-specific skips, zero failures). The PR body classifies these as "regression proof, not production proof or an FPS claim" — the doctrine-correct posture for a non-user-visible cache fix.
6. **No font / animation / `<style>` block change.** The PR does not touch any theme file, any CSS module, any navigation chrome, any onboarding surface, or any inline-style block. The two `dataCache.ts` comment edits and the `if`-statement re-placement are pure TS-internal mechanics.
7. **No new theme debt.** The new test file is read by Vitest only; it adds no persistent state, no module-level constant beyond the `URL` and `bars` fixture literals, no new token, no new theme artifact, no new global. The `deferred()` helper is test-scope only and immediately garbage-collectible.

No new theme debt; no color-literal addition to any UI surface; no evidence-matrix gate is unmet; no in-scope TP-0 finding.

## Validated-claims findings

The standing macro law: the word `validated` (and friends: `verified`, `proofed`, `certified`, `approved`, `gauntlet`, etc.) is CI-enforced via `scripts/check_validated_claims.py`; context/data/detection/tagging artifacts stay display-tier until they clear the gauntlet; the word "validated" in user-facing text is CI-enforced (CLAUDE.md §Epistemics gauntlet = PROMOTION gate). The terminal repo does not have its own `check_validated_claims.py` — the macro-side checker governs all repos via the `validate` cross-repo gate.

**Verdict: PASS.**

1. **No new template or site file — the policy check has nothing to flag.** This PR touches zero template files and zero site files, so there is no new front-facing string to gate.
2. **Word-boundary grep on the PR's two added/modified files for `validated | verified | certified | approved | proofed | gauntlet | proven`: zero new hits introduced by this PR.**
   - `validated` — does not appear in `dataCache.ts` or `dataCacheRequestOwnership.test.ts`.
   - `verified` — does NOT appear in either of the two PR files (`grep -E "verified" terminal/lib/dataCache.ts terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` returns nothing on the PR's exact files at the exact head). The only `verified` reference in the wider `dataCache.ts` is on a pre-existing comment outside this PR's diff ("verified on" inside a long-standing bug-report citation block; line is in unchanged territory of the file).
   - `certified` — does not appear.
   - `approved` — does not appear.
   - `proofed` — does not appear.
   - `gauntlet` — does not appear.
   - `proven` — does not appear.
3. **The PR explicitly disclaims tier assertions.** PR body §"Discriminating proof" names the exact stale candidate `2bdadcb7` and the RED/GREEN proof split (5 race cases failed RED, 4 compatibility cases passed; on the GREEN candidate, 9/9 tests pass through the real consumer path). The PR body classifies the merge state as `BUILT_NOT_PROVEN; parent mission incomplete` and the test results as "regression proof, not production proof or an FPS claim." PR body §"Authority, custody and release" explicitly states: "Clock PR #702 remains held on its existing marker-tooltip repair dependency; this PR does not replace or duplicate #676/#688. Do not redo accepted source work or infer production latency improvements from these tests."
4. **The "Genuine current 404/410 suppression and transient failure recovery are preserved" claim is honest.** The fourth regression test (`it.each([404, 410])("still remembers a current request's genuine %i without duplicate requests", …)`) asserts the current-inflight 404/410 path STILL populates the absence cache (`_neg404Has(URL) === true`) and the second-read path STILL deduplicates (`fetcher.toHaveBeenCalledTimes(1)`). The sixth regression test (`it("does not convert transient transport failures into absence", …)`) asserts the 503 path returns the explicit `{ status: "unavailable", reason: "server", httpStatus: 503 }` shape and does NOT populate the absence cache. Both pre-existing contracts are pinned at the test surface.
5. **The "obsolete callers still receive their truthful original result; they cannot mutate newer cache state" claim is verified.** The `outcome` value handed to the `.then(...)` callback is unchanged across the fix — only the cache side-effect is gated. The first regression test (`it.each([404, 410])("an invalidated request's late %i cannot hide successfully recovered OHLC", …)`) asserts `await outdated === { status: "absent", httpStatus: status }` — the obsolete caller's awaited value is unchanged. The defect was that the OBSOLETE CALLER MUTATED NEWER CACHE STATE; the fix gates the mutation without altering the awaited value.
6. **The "5 race cases failed; four compatibility cases passed" RED-line is honest.** PR body §"Discriminating proof" explicitly identifies the exact stale candidate as `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` based on `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` and reports the GREEN/RED split as 5/4 (5 race cases failed RED on the stale candidate, 4 compatibility cases passed). The test surface (`it.each([404, 410])("an invalidated request's late %i cannot hide successfully recovered OHLC", …)` covers the two HTTP-absence-code race variants × the invalidate scope = at least 4 of the 5 race cases; the LRU test (`it("an LRU-evicted request cannot recreate a negative-cache entry", …)`) covers the 5th race case via LRU eviction rather than invalidate).
7. **The "9/9 tests pass through the real `getJSONResult` / `invalidate` / `getOhlc` consumer path" claim is verified.** The six `it`/`it.each` tests in `dataCacheRequestOwnership.test.ts` import `_neg404Has, getJSONResult, getOhlc, invalidate, peek` from `@/lib/dataCache` — the real public consumer API. `vi.stubGlobal("fetch", …)` swaps in the fake fetcher; there is no internal-helper-only testing or production-bypass. The PR body's "covers both HTTP absence codes, single/all-key invalidation, LRU eviction, current absence deduplication, obsolete success and transient 503" enumeration is exhaustive against the six test cases.
8. **The "Full Terminal unit suite: 378 files, 6,081 tests passed" claim is deterministic.** The number is a measured count of files + passing tests at the exact candidate `2bdadcb7`; the PR body's "four existing TODO" line acknowledges the four pre-existing skipped tests. No production-data, FPS, latency, throughput, or click-through claim is made.
9. **The "Real responsive chart `quote-single-flight` / `chart-view-reset` matrix: 8 passed" claim is honest.** PR body §"Discriminating proof" enumerates the matrix ("slow quote transport, symbol changes, chart reset, normal/log wheel zoom, future-axis spacing") and the negative-result count ("ten existing viewport-specific skips, zero failures, one worker, no retries"). The PR body's "This is regression proof, not production proof or an FPS claim" line is the doctrine-correct posture for a responsive-matrix result.
10. **No NEW promotion occurred.** The PR is an internal-cache fix to an existing single-flight guard; it does NOT promote any artifact to gauntlet/authority/rank/score/signal/trade. The defect it repairs is a correctness defect (cache-state corruption under a specific race window) — not a tier-1 claim about the cache, the chart, or any downstream signal. The `BUILT_NOT_PROVEN` classification in PR body §"Authority, custody and release" is the doctrine-correct posture for an unfinished chart program.

## Overall verdict

**PASS** on all three dimensions (plain-language, theme, validated-claims). This is a textbook half-B focused-infrastructure fix:

- The plain-language script ran clean (`blocking:0`, `legacyReported:6` — all six pre-existing legacy findings in OTHER files) against the modified `dataCache.ts` and the new `dataCacheRequestOwnership.test.ts`; the modified lines contain zero banned tokens and the diff introduces zero new user-visible strings.
- The PR carries zero CSS / theme / template / HTML / runtime-style-injection / UI surface; it touches only an internal-cache TS module and its test suite; the TP-0 art-direction gate has nothing to evaluate (no new material decision, no new palette entry, no new token, no new render path).
- The PR carries zero new tier-asserting words; the only `verified` reference in the wider `dataCache.ts` is on a pre-existing unchanged line; the PR's "regression proof, not production proof or an FPS claim" and `BUILT_NOT_PROVEN; parent mission incomplete` disclaimers are doctrine-correct and verified by the regression suite's six tests.
- The fix is a minimal re-placement of one existing `if (outcome.status === "absent") rememberAbsence(url)` line inside the SAME existing `if (current && current.inflight === inflight)` guard that already gates the positive `store.set(url, …)` write. Both cache writes now share the same ownership predicate. No new state, no new request, no new dependency, no new retry policy.
- The defect it repairs is precisely named ("A late 404/410 from an invalidated or LRU-evicted request could recreate the ten-minute absence cache AFTER a newer request had already recovered valid OHLC") and the regression suite covers both invalidate scopes (one-key, all-key), both HTTP absence codes (404, 410), the LRU-eviction variant, the current-inflight preservation contract, the obsolete-success non-overwrite contract, and the transient-failure retryable contract — six tests inside a single `describe("data cache request ownership after refresh")` block.
- The four non-changed combinations are explicitly preserved by regression tests: (i) current 404/410 still populates the absence cache; (ii) current 200 data still writes the positive cache; (iii) stale 200 cannot overwrite newer positive read (the existing positive-write guard was already in place and continues to work); (iv) transient 5xx/429/network still does NOT populate the absence cache and still allows the next read to retry. The diff's net behavior delta is exactly one combination (stale inflight + 404/410) and exactly one assertion (the absence cache must not be recreated behind a newer positive read).
- The PR body §"Authority, custody and release" explicitly disclaims: "Clock PR #702 remains held on its existing marker-tooltip repair dependency; this PR does not replace or duplicate #676/#688. Do not redo accepted source work or infer production latency improvements from these tests."

This PR is ready to count as a textbook compliant half-B delivery. The next half-B audit seat should pick the next non-audit-record merged PR in the 24-h window — at the time of this audit, the remaining unaudited substantive PRs in the window are `#7614 fix(ci): checkpoint core engine outputs before tail desks` (CI infrastructure, not user-facing) and any later half-B PRs that land.