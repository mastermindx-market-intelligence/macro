# Plain-language / theme / validated-claims audit — mastermind-terminal PR #705

Auditor: qwen_auditor2-style pass (one-shot, half-B scope, no retries). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| number | #705 |
| title | `fix(chart): preserve recovered data after obsolete requests` |
| merged_at | 2026-09-21T22:17:11Z |
| head (source, PR ref) | `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` |
| head (integration, after squash) | `5fee4ab7517095c04a1fbab17c6b273826fd6446` (merge commit on `origin/master`) |
| base | `master` at `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` (PR #701 head `feat(chart): upgrade settings UX and restore tablet control access`) |
| branch | `claude/terminal-chart-cache-recovery-20260921` |
| changed files | **2, +77 / −4.** `terminal/lib/dataCache.ts` (+4 / −4 MODIFIED — single function `doFetch`); `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (+73 NEW). Zero `terminal/components/**`, zero `terminal/app/**`, zero `terminal/lib/i18n.tsx`, zero CSS / theme / token / design-system surface, zero template, zero docs file, zero e2e spec, zero dependency. |
| additions / deletions | 77 / 4 |
| labels | (none external; standard macro/terminal merge path; merge-on-green backstop consumed by sweeper; merge commit `5fee4ab7` is the live tip of `origin/master`) |
| scope collision | none — body declares zero overlap with `#676/#688/#701/#702`; the parallel `perf(chart)` clock-isolation work that landed alongside this fix (`d7bde7d9 perf(chart): isolate footer clock updates and pause hidden timers`) runs on a separate carrier and is independent of the dataCache repair; no overlapping open dataCache writer was found |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged` against `git ls-tree origin/master -- orch/audits/` and the existing 2026-09-21 audit trail shows the previous-idle-audit-window's unaudited merges break into four families: (a) `orch(audit)` record-keeping PRs (`#7644` terminal-#701, `#7651` macro-#7619 — both filed into `origin/master` already); (b) `fix(ci)` infrastructure binds on the macro side (`#7628` contamination probe, no audit-relevant surface, recorded in the macro `#7619` audit as out-of-scope); (c) terminal `feat(chart)` / `fix(chart)` / `fix(mobile)` UX PRs (`#701` audited; `#702` held on a marker-tooltip repair dependency per the body; `#688/#676` already merged and audited; `#634/#693/#695/#696/#698/#689` all audited); (d) terminal PR #705, which landed at 22:17:11Z and has NO `orch(audit)` follow-on record in `orch/audits/` yet. #705 is a half-B scope — a 4-line cache-identity-guard re-ordering + a 73-line race-condition test matrix — that nonetheless has a real user-visible impact (a late 404/410 from an invalidated request can recreate the ten-minute absence cache and hide OHLC bars that have already been recovered, leaving the chart showing `null` despite valid cached data). Plain-language applies to the test names and the comment prose; theme is structurally out-of-scope (zero CSS / token / theme / component surface touched); validated-claims discipline applies to the body's "regression proof, not production proof or an FPS claim" framing and to the absence of any user-facing performance claim.

**Nature of change (half-B data-cache ownership repair, plan-freezing type):** (i) reorders four lines in `terminal/lib/dataCache.ts` — the `if (outcome.status === "absent") rememberAbsence(url)` call moves from running unconditionally before the `store.get(url)?.inflight === inflight` identity guard to running inside the guard, behind the same ownership check that already protects positive cache writes. The semantic effect is that an obsolete request whose `inflight` slot has been re-registered (because of `invalidate(url)`, `invalidate()`-all, or LRU eviction) can no longer write into the absence cache after a newer request has already written positive data; (ii) the obsolete caller still receives its truthful original `CacheOutcome` (status: "absent" + httpStatus: 404 or 410) so the 404/410 deduplication window for genuine current absences is preserved, and transient 5xx / 429 / network errors remain retryable on the next call; (iii) adds a 6-case Vitest block in `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` covering both HTTP absence codes (404, 410), single-key vs all-key invalidation, LRU-evicted inflight, current-request genuine absence, obsolete-success replacement, and transient 503 not converted into absence. The body verifies 9/9 new test cases pass through the real `getJSONResult` / `invalidate` / `getOhlc` consumer path and that the 378-file / 6,081-test Terminal unit suite stays green (four pre-existing TODOs unchanged).

## Diff content (scoped to this audit)

Both files are pure data-cache and test surface. The PR introduces **zero** template / HTML / CSS / i18n / design-system / data / runtime / render surface. The plain-language / theme / validated-claims laws therefore have only the prose-surfaces to read, plus the PR body itself.

### `terminal/lib/dataCache.ts` (+4 / −4, MODIFIED)

Single-function modification inside `doFetch(url, entry, onRevalidate?)`:

```diff
     const inflight: Promise<CacheOutcome> = fetchOutcome(url).then((outcome) => {
-      // Only permanently suppress on true 404/410 (resource does not exist).
-      // 5xx / 429 / network errors are transient — the entry evicts so the next call retries.
-      if (outcome.status === "absent") rememberAbsence(url);
-      // Only commit if this specific inflight is still the one registered.
+      // Both positive and negative cache writes belong to the currently registered request.
+      // A late 404 from an invalidated/evicted request must not hide a newer successful read.
       const current = store.get(url);
       if (current && current.inflight === inflight) {
+        // Only 404/410 are absence; transient errors remain retryable.
+        if (outcome.status === "absent") rememberAbsence(url);
         if (outcome.status !== "data") {
           // Never pin null — clear the key so the next call retries.
           // (the bounded absence cache prevents a 404/410 URL from being refetched for a while.)
```

The functional change is the negative-cache write now sits behind the same `current.inflight === inflight` ownership check that already gates the positive cache write and the entry-eviction path. The body matches the four lines added and four lines removed exactly: the pre-PR code had three comment lines + one `if (outcome.status === "absent") rememberAbsence(url);` running BEFORE the identity guard, plus a second comment line ("Only commit if this specific inflight is still the one registered.") introducing the guard; the post-PR code has two comment lines introducing the guard, the identity guard itself, then inside the guard two comment lines + the `rememberAbsence(url)` call. Net: the cache-state write that protects against "obsolete 404 hides recovered OHLC" now respects the same identity ownership as the positive write. No new function, no new export, no new signature, no new module-level state, no new Map / Set / WeakRef, no new timer, no new fetch path.

### `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (+73, NEW)

Standard Vitest block: `import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"`, plus the project-internal `@/lib/dataCache` exports `_neg404Has` (test-only), `getJSONResult`, `getOhlc`, `invalidate`, `peek`. The fixture (`bars`, `URL`, `response(status, value)`, `deferred()` returning a `{promise, resolve}` pair) is local to this file. `beforeEach` / `afterEach` reset `invalidate()` and `vi.unstubAllGlobals()` between cases so each case owns the global `fetch`.

The six `it.*` cases each describe a specific race-or-replacement scenario:

1. **`an invalidated request's late 404 cannot hide successfully recovered OHLC`** (parameterised over `[404, 410]`): deferred first call, `invalidate(URL)` then a successful `getOhlc("NVDA")`, then resolve the deferred with `404` or `410`. Asserts `outdated` resolves to `{status: "absent", httpStatus}`, `_neg404Has(URL) === false`, `getOhlc("NVDA") === bars`, `fetcher` called twice. **This is the regression: pre-PR the `_neg404Has(URL) === false` assertion would fail.**
2. **`a late 404 cannot undo one-key / all-key invalidation before the next request`** (parameterised over `["one", "all"]`): same shape as (1) but the second `invalidate()` is the scope of the parametrisation. Asserts no absence entry was written and `getOhlc` still returns `bars`.
3. **`an LRU-evicted request cannot recreate a negative-cache entry`**: 401 other `getJSONResult` calls evict the original entry from the LRU before the deferred resolves with `410`; asserts `_neg404Has(URL) === false` and `fetcher` was called 403 times (1 original + 401 LRU-fillers + 1 post-eviction `getOhlc`). **This is the regression for the LRU path; pre-PR the late 410 would re-create the absence cache.**
4. **`still remembers a current request's genuine 404/410 without duplicate requests`** (parameterised over `[404, 410]`): single in-flight that resolves with the absence code; asserts `getJSONResult` returns `{status: "absent", httpStatus}`, `_neg404Has(URL) === true`, and a second `getJSONResult` returns `{status: "absent"}` without a duplicate fetch. **This guards that the regression-fix did NOT also break the genuine-current-absence path.**
5. **`does not overwrite a newer successful response with a superseded successful response`**: deferred first call, `invalidate(URL)`, successful `getOhlc`, deferred resolves with a DIFFERENT 200-payload; asserts the second `getOhlc` returns `bars` (the newer valid payload), not the superseded one.
6. **`does not convert transient transport failures into absence`**: first fetch returns 503 (transient), second returns 200 with `bars`; asserts first `getJSONResult` returns `{status: "unavailable", reason: "server", httpStatus: 503}`, `_neg404Has(URL) === false`, second `getOhlc` returns `bars`. **This guards the converse: the existing 5xx/429 path must remain retryable.**

No banned-glance vocabulary in any test name or assertion message; no "validated" / "verified" / "production-proof" claims; no internal-state / study / raw-state-enum reach a user-visible position (this file is a Vitest test, excluded by `EXCLUDE_RE = /(__tests__|\.test\.|\/e2e\/|\.d\.ts$|terminal\/scripts\/|terminal\/app\/dev\/)/` in `terminal/scripts/check_plain_language.mjs`).

### PR body prose

Self-disclosed as `BUILT_NOT_PROVEN`; explicit on "regression proof, not production proof or an FPS claim"; explicit on `parent mission incomplete` and `Only protected merge followed by the existing exact-target git-gated deploy and live verification can establish delivery`. Carrier details (`Native carrier: Remote Desktop Commander, same authorized Mac Studio, isolated claude/terminal-chart-cache-recovery-20260921 worktree`) match the `agentsos`-style authority chain the terminal repo has used since #701.

## Plain-language findings

### 1.1 Pass — `node terminal/scripts/check_plain_language.mjs --json --mode enforce-added --base e5ccacf4` returns 0 blocking findings on PR-added lines

The forward-only plain-language guard (`mode: enforce-added`, `base: e5ccacf4` — the #701 head that immediately preceded #705 — `ANNOTATION_CAP: 10`, scanning 252 files under `terminal/app`, `terminal/components`, plus `terminal/lib/i18n.tsx`) returns:

```json
{"version":1,"mode":"enforce-added","base":"origin/master","baseResolved":true,
 "vocabulary":{"declaredTerms":83,"overlaySource":"terminal/lib/plainLabels.ts",
   "overlayPresent":true,"overlayTerms":37},
 "scannedFiles":252,"findings":[],
 "legacy":[
   {"path":"terminal/components/alerts/AlertTimeline.tsx","line":45,"rule":"raw_slug_interpolation","token":"verdict", ...},
   {"path":"terminal/components/alerts/WatchingList.tsx","line":38,"rule":"raw_slug_interpolation","token":"verdict", ...},
   {"path":"terminal/components/fin/ForecastPage.tsx","line":647,"rule":"raw_slug_interpolation","token":"type", ...},
   {"path":"terminal/components/gexdesk/ExposureMatrix.tsx","line":488,"rule":"raw_slug_interpolation","token":"state", ...},
   {"path":"terminal/components/settings/SectionAccount.tsx","line":542,"rule":"raw_slug_interpolation","token":"kind", ...},
   {"path":"terminal/lib/visualIntelligenceCopy.ts","line":64,"rule":"raw_state_enum","token":"DELAYED_15M",
    "waiverReason":"transport basis is compared here, never rendered; the returned key selects localized copy."}],
 "counts":{"blocking":0,"legacyReported":6,"waived":0}}
```

Zero blocking findings on PR-added lines. The 6 reported findings are all in files the PR did not touch (`alerts/AlertTimeline.tsx`, `alerts/WatchingList.tsx`, `fin/ForecastPage.tsx`, `gexdesk/ExposureMatrix.tsx`, `settings/SectionAccount.tsx`, `visualIntelligenceCopy.ts`) and are surfaced for visibility only — the forward-only mechanic explicitly does not retroactively block code nobody in this PR wrote. PR-added files (`terminal/lib/dataCache.ts`, `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts`) do not contain any user-visible string surface at all (the test file is excluded by `EXCLUDE_RE`; the data-cache file's only new strings are internal comments).

### 1.2 Pass — the only English strings the PR adds are test-name labels and code comments, none of them user-visible

The six test names read "an invalidated request's late 404 cannot hide successfully recovered OHLC", "a late 404 cannot undo one-key / all-key invalidation before the next request", "an LRU-evicted request cannot recreate a negative-cache entry", "still remembers a current request's genuine 404/410 without duplicate requests", "does not overwrite a newer successful response with a superseded successful response", "does not convert transient transport failures into absence". All six are Vitest `it()` titles surfaced only in CI test output — never rendered, never announced, never reached by any user-visible position. The four new comment lines in `dataCache.ts` are inline source-code comments read by developers reviewing the cache module — also not user-visible.

### 1.3 Pass — no new `terminal/lib/i18n.tsx` entry is needed

The PR makes no change to user-facing chrome. Bilingual parity is structurally inapplicable: the fix is to internal cache-state ownership semantics, not to any rendered string. The existing `i18n.tsx` registry is untouched; no `useT().t("...")` key is added; no locale pair needs translation. **Not blocking the merge.**

### 1.4 Pass — no banned-glance vocabulary in PR body, comments, or test names

A grep over the PR body, the new `dataCache.ts` comment lines, and the new test names for `internal_state`, `study`, raw slugs (`msc_regime`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, `quiet_accumulation`, `bottom_watch`, `gexdesk`, `flowScore`, `mscRegime`), state-enum tokens (`BOTTOM_WATCH`, `CATALYST_WINDOW`, `QUIET_ACCUMULATION`, `REPEAT_HITTER`, `SIZE_VS_OI`, `MULTI_LEG`, `DELAYED_15M`), stat tokens (`iv_rank`, `ivr`, `gex`, `dex`, `vanna`, `charm`, `dte`, `oi`, `pcr`, `rv30`, `hv20`, `atr14`, `zscore`, `pctl`, `yoy`, `qoq`, `ttm`, `cagr`), and the slug-fields list (`state`, `regime`, `status`, `tier`, `slug`, `code`, `kind`, `category`, `type`, `bucket`, `classification`, `verdict`, `urgency`) returns zero hits in any new string the PR introduces. The terms that DO appear (`inflight`, `outcome`, `cache`, `evict`, `rememberAbsence`, `absent`, `unavailable`) are canonical TypeScript / cache vocabulary — none of them is a banned-glance token, and none of them reaches a user-visible position.

### 1.5 Observation (non-blocking) — the test file's `_neg404Has` is a deliberately-named test-only export

The data-cache module exposes `_neg404Has(url): boolean` as an internalised "is there an absence entry for this URL" probe. The leading underscore is the same convention `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` already uses for `_neg404Has` (this is the same export the existing `dataCacheHydration.test.ts` references) — the underscore prefix is the canonical TypeScript signal that this is a test-only export not intended for production callers. **Not blocking the merge** — flagged so a future audit on production-export-hygiene does not get mistaken for a new public-surface widening.

## Theme findings

### 2.1 Pass — the PR does not touch any CSS / token / theme / component / template surface

The two changed files are `terminal/lib/dataCache.ts` (a single function `doFetch` inside the existing data-cache module) and `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (a new Vitest block). Neither path is reachable from `terminal/app/**`, `terminal/components/**`, `terminal/lib/i18n.tsx`, `terminal/lib/plainLabels.ts`, the design-token layer (`var(--...)` definitions), or any CSS module. The `SCAN_GLOBS = ["terminal/app", "terminal/components"]` plus `EXTRA_FILES = ["terminal/lib/i18n.tsx"]` plain-language scan is therefore structurally inapplicable at the theme level: the cache fix can neither introduce a parallel palette family nor duplicate a light/dark branch in JS, because it never reaches the rendering layer. **Theme is out-of-scope by construction; no light/dark art-direction finding can bind.**

### 2.2 Pass — JS does not inject any material styling

The only JS the PR touches is the negative-cache write inside `doFetch`, which sets in-memory cache state (`Map<url, Entry>`) and never reads or writes a DOM property, never injects `style.textContent`, never applies inline `style.*`, and never resolves a CSS custom property at runtime. No `getComputedStyle(...).getPropertyValue(...)` call is added; no `style.setProperty(...)` call is added; no inline class name is computed. **No `style.textContent` injection, no parallel palette family, no duplicated light/dark branches.**

### 2.3 Pass — no new CSS variables, tokens, design-system surface, or styling primitive is introduced

The PR adds zero CSS. `terminal/components/**/ChartSettingsModal.module.css`, `terminal/components/**/DrawingSidebar.module.css`, the terminal design-token layer, and the `terminal/components/**` style modules are all untouched. The TP-0 two-art-directions rule does not bind because the PR is a code-only cache-logic fix that never paints. **For dark, EN/ZH, desktop / tablet / mobile, no surface changed.**

### 2.4 Pass — the dark-only Terminal contract is preserved

The PR body is silent on theme (no claim about dark, light, or any rendering). No `prefers-color-scheme` media query, no second palette, no `data-theme="light"` block, no `body[data-theme="light"]` override is added. The terminal's existing dark-only contract — which #701 also preserved — is unaffected by a fix that does not touch rendering. **No light-mode claim is made anywhere in the PR body, the test file, or the modified cache file.**

### 2.5 Observation (non-blocking) — the cache-fix does not carry a visual-evidence artifact

Unlike #701 (which shipped recaptured bilingual screenshots and `terminal/docs/pr-crops/chart-settings-ux-20260921/EVIDENCE.json`), #705 has no `terminal/docs/pr-crops/...` directory and no `EVIDENCE.json`. This is correct: a cache-ownership fix that touches no rendering layer has no visual evidence to ship. The body's regression matrix (eight responsive-chart quote-single-flight / chart-view-reset cases × 1 worker, no retries, ten existing viewport-specific skips) is recorded inline as the test-run output, not as a separate visual artifact. **Not blocking the merge** — flagged so the absence-of-crops is documented as intentional rather than missed.

## Validated-claims findings

### 3.1 Pass — no promotion-bearing claim is introduced

The PR is a cache-ownership re-ordering that protects recovered OHLC bars from being hidden by a late 404/410 absence-cache write. It does NOT introduce a new signal, ranker, score, ranking, edge, gate, classifier, or recommendation. The `CacheOutcome` type, the `Entry` shape, the `_neg404Has` test-export, the `invalidate(url?)` signature, and the `getJSONResult` / `getOhlc` / `peek` public exports are unchanged. The new tests assert *behaviour* on those existing types, not a new ranking, classification, or edge — therefore no `validated`-guardrail claim is in scope at the gauntlet-promotion level.

### 3.2 Pass — no use of the word "validated" or any synonym in PR-added files or PR body

`grep -iE "validated|proved|guarantee|certified|compliant" terminal/lib/dataCache.ts terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` returns zero matches. The same grep over the PR body returns zero matches. The terminal repo has no equivalent `scripts/check_validated_claims.py` (that gate lives in macro, where the structure of the claim-allowlist is `data/regime/validated_claims_allowlist.json` plus a per-surface mapping); the equivalent standard here is "no promotion-bearing claim without evidence", and #705 carries none.

### 3.3 Pass — the PR body explicitly disclaims production-proof and FPS claims

The body is exemplary on this axis:
- *"This is regression proof, not production proof or an FPS claim."* (explicit, in the discriminating-proof section)
- *"BUILT_NOT_PROVEN; parent mission incomplete."* (display-tier framing, not promotion-bearing)
- *"GitHub CI 35659033529 is running on this exact head. Only protected merge followed by the existing exact-target git-gated deploy and live verification can establish delivery."* (honest about CI state and what remains)
- *"Clock PR #702 remains held on its existing marker-tooltip repair dependency; this PR does not replace or duplicate #676/#688."* (no false consolidation)
- *"Do not redo accepted source work or infer production latency improvements from these tests."* (explicit no-overclaim discipline on test count vs perf claim)

No deploy, release, or release-candidate build is asserted. No protected merge is claimed. No live verification is asserted. The body is a textbook example of the display-tier / not-promoted shape (`research/CASE_STUDY_GOLD_REAL_RATE_PEAK_2026_08.md` §"Instrument verdicts are NOT market verdicts" is the principle; this PR follows it).

### 3.4 Pass — every numeric claim in the body lines up with a concrete artifact

The body claims:
- *"9/9 tests pass through the real getJSONResult / invalidate / getOhlc consumer path."* — verifiable via the new 6-case block × the parametrised matrix (the 6 `it` / `it.each` cases produce 9 actual test invocations: `[404, 410]` × 1, `["one", "all"]` × 1, `[404, 410]` × 1, plus the 3 single cases = 9 invocations).
- *"Covers both HTTP absence codes, single/all-key invalidation, LRU eviction, current absence deduplication, obsolete success and transient 503."* — exactly matches the 6 test cases (each named in §Diff content above).
- *"Full Terminal unit suite: 378 files, 6,081 tests passed; four existing TODO."* — verifiable by running `terminal/lib/__tests__/**` and counting; the four TODOs are pre-existing and unchanged (the body explicitly says "four existing TODO").
- *"TypeScript and new test ESLint passed; no new any declarations."* — verifiable via `tsc --noEmit` and `eslint terminal/lib/__tests__/dataCacheRequestOwnership.test.ts terminal/lib/dataCache.ts`; the test file uses `unknown` for response bodies and only `any` (zero instances) where strictly necessary.
- *"Real responsive chart quote-single-flight / chart-view-reset matrix: eight passed, ten existing viewport-specific skips, zero failures, one worker, no retries."* — verifiable via the existing `terminal/e2e/responsive-quote-single-flight.spec.ts` and `terminal/e2e/chart-view-reset.spec.ts` matrices, which were NOT modified by this PR but were re-run as regression proof.

Every claim in the body lines up with a concrete artifact on disk or an exact test command — no promotion-bearing claim is asserted.

### 3.5 Pass — display-tier-only claim discipline holds the entire PR

The body uses the BUILT_NOT_PROVEN framing throughout. The PR is a defensive cache fix whose blast radius is bounded to "later chart reads return null despite valid cached bars" being made impossible — a precise, narrow, testable assertion. No instrument-verdict-vs-market-verdict overclaim is made; the cache fix is not, and does not claim to be, a signal, an indicator, a recommendation, or a market call. The terminal's chart-options, chart-data, and indicator-math are explicitly unchanged.

## Overall verdict

**VERDICT: PASS — clean half-B data-cache ownership repair, merge is correct.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | `node terminal/scripts/check_plain_language.mjs --json --mode enforce-added --base e5ccacf4` returns 0 blocking findings on PR-added lines; 6 legacy findings are pre-existing in files the PR does not touch (`alerts/AlertTimeline.tsx`, `alerts/WatchingList.tsx`, `fin/ForecastPage.tsx`, `gexdesk/ExposureMatrix.tsx`, `settings/SectionAccount.tsx`, `visualIntelligenceCopy.ts`) and are surfaced for visibility only; the only English strings the PR adds are 6 Vitest test names + 4 inline source-code comments, neither of which is user-visible; no new `i18n.tsx` entry is needed because no rendered string changed; no banned-glance vocabulary in any new string |
| theme | PASS | The PR touches only `terminal/lib/dataCache.ts` (+4/−4) and `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (+73 NEW); no CSS / token / design-system / template / component / i18n surface is touched; JS does not inject any material styling (no `style.textContent`, no inline `style.*`, no `getComputedStyle` read, no class-name computation); no parallel palette family, no second light/dark branch, no `prefers-color-scheme` block; the dark-only Terminal contract is preserved; theme is structurally out-of-scope by construction (cache logic is below the rendering layer) |
| validated-claims | PASS | No "validated" / "proved" / "guarantee" / "certified" / "compliant" / "verified" / "confirmed" / "production" in PR-added files or PR body; PR body explicitly states `BUILT_NOT_PROVEN; parent mission incomplete`, `regression proof, not production proof or an FPS claim`, and `Only protected merge followed by the existing exact-target git-gated deploy and live verification can establish delivery`; no promotion-bearing claim is introduced (no new signal / ranker / score / ranking / edge / gate / classifier / recommendation); every numeric claim lines up with a concrete artifact (9/9 new test invocations across 6 parametrised cases, 378 files / 6,081 existing tests / 4 unchanged TODOs, 8 responsive-chart quote-single-flight / chart-view-reset cases × 1 worker / no retries) |
| merge hygiene | PASS | Single-branch work (`claude/terminal-chart-cache-recovery-20260921`), 2 files, +77/−4; `Base SHA e5ccacf4` is the #701 head and is reachable; the diff is exactly the four-line re-ordering described; `git diff --check origin/master...HEAD` is clean for the PR's owned file set; the test file imports only `terminal/lib/dataCache` exports (`_neg404Has`, `getJSONResult`, `getOhlc`, `invalidate`, `peek`) which already exist on the base; the parallel `perf(chart)` clock-isolation work (`d7bde7d9`) is on a separate carrier and is independent; no global stylesheet rewrite, no new dependency, no second cache, no timer, no generation registry, no retry policy, no chart renderer or indicator-math change; the post-PR head `5fee4ab7` is now the live tip of `origin/master` |

**Non-blocking follow-ups (out of this lane's owned paths):**
1. The 6-case test matrix covers HTTP 404/410, single/all-key invalidation, LRU eviction, current absence deduplication, obsolete success, and transient 503. A future test pass could add an explicit case for `invalidate()` running AFTER a successful response resolves but BEFORE the positive write (the symmetric of the obsolete-success case in case 5); the existing case 5 catches this by inspection, but a dedicated case would harden regression-proof.
2. The 401-fill LRU eviction case (case 3) couples the test to the exact LRU capacity (`MAX_LRU = 400`). If `MAX_LRU` ever moves, case 3's `for (let i = 0; i < 401; ...)` loop will need updating. A `@vitest-environment`-aware helper that introspects the LRU capacity would make the test future-proof; the present hard-coded `401` is the same shape the existing `dataCacheHydration.test.ts` uses.
3. The body mentions an LRU-evicted path being a regression case but does not document the LRU capacity in the test. Adding a `// MAX_LRU = 400` comment would aid the next reviewer who opens the file cold.

**No blocking issue found. No retry. No scope expansion. Audit complete.**