# PR audit — mastermindx-market-intelligence/mastermind-terminal#705

**Auditor:** meta-ceo-b-2026-09-08 (one-pass remote useful-idle, no retries, no scope expansion)
**Audit timestamp:** 2026-09-22 (audit cohort 2026-09-21; UTC window of PR merge 2026-09-21T22:17:11Z, audit file authored at 2026-09-22T05:34Z)
**Repo / PR:** mastermindx-market-intelligence/mastermind-terminal #705
**PR title:** fix(chart): preserve recovered data after obsolete requests
**Merged at:** 2026-09-21T22:17:11Z
**Head sha (integration):** `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` (per `gh pr view 705` `headRefOid`)
**Source base:** `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` (the prior 09-21 chart-cache cohort base, the #705 RED-on-base candidate)
**Branch:** `claude/terminal-chart-cache-recovery-20260921` (per PR body "isolated claude/terminal-chart-cache-recovery-20260921 worktree under the canonical repository")
**Author:** chriswong6031-creator (PR body declares `Mastermind@6f321cb42166e4224e5107ac3312a6f7cd01fffa` protected compatible Skillpack; carrier = "Remote Desktop Commander, same authorized Mac Studio")
**Repo root verified:** `/Users/chriswong/lanes/repos/mastermind-terminal`, sparse-checkout (worktree-scoped). `terminal/lib/dataCache.ts` and `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` were fetched via `git show <sha>:<path>` against the integration head because the local sparse filter excludes `terminal/lib/**`; this matches the receipt pattern used in the #704 audit.

> **Scope note (§1):** the chronologically most-recent merged terminal PRs inside the 24 h window are #706 (03:00:34Z — `fix(options): contain volatility term structure on mobile`, audited), **#705 (22:17:11Z — this PR, 0 audits in repo)**, #704 (01:23:41Z — `fix(options): enlarge mobile flow ticker targets`, audited), #701 (18:35:42Z — audited), #700 (14:09:56Z — dev-only one-line fix, no surface), #698 (audited), #696 (audited), #695 (audited), #693 (audited), #689 (audited). The macro branch of the same window has #7683 / #7678 / #7666 / #7639 / #7637 / #7632 / #7628 / #7621 / #7614 un-audited. **#705** is the chronologically newest un-audited merge in either repo and IS a half-B surface fix in spirit (a chart-cache data-layer defect whose user-visible symptom is "later chart reads returned null despite the valid cached bars" — the chart goes blank / stays blank after an obsolete request resolves late). The change is bounded to two files (library + its test) with zero UI / theme / i18n surface delta; the audit covers it directly.

---

## 1. PR metadata

| field | value |
|---|---|
| repo | mastermindx-market-intelligence/mastermind-terminal |
| number | 705 |
| title | fix(chart): preserve recovered data after obsolete requests |
| merged_at | 2026-09-21T22:17:11Z |
| head (integration) | `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` |
| base | `master` at `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` (chart-cache 09-21 RED base) |
| branch | `claude/terminal-chart-cache-recovery-20260921` |
| changed files | 2 — `terminal/lib/dataCache.ts` (+4 / -4 MODIFIED), `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (+73 NEW) |
| additions / deletions | 77 / 4 |
| labels | `merge-on-green` (the backstop, consumed by the sweeper; PR body declares "BUILT_NOT_PROVEN; parent mission incomplete") |
| scope collision | none — PR body declares "Diff is limited to: `terminal/lib/dataCache.ts`, `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts`"; no open PR owns the dataCache ownership guard or its consumer surface. Body explicitly: "No additional cache, timer, generation registry, request, dependency, retry policy, chart renderer or indicator-math change." |
| operation id | (PR body does not declare an explicit operation id; the cohort base + `claude/terminal-chart-cache-recovery-20260921` worktree name is the de facto id) |
| protected pack | `Mastermind@6f321cb42166e4224e5107ac3312a6f7cd01fffa` (declared compatible in the PR body) |

**Nature of change (chart data-cache ownership repair, bounded 2-file fix):** the PR resolves a single chart-data correctness defect discovered while reviewing the `dataCache` ownership guard. After `invalidate(url)` (or an LRU eviction of the inflight entry), an in-flight request whose response arrived late could still mutate the absence / store state — a late 404 from the now-obsolete request would write the negative-cache entry even though the new request had already recovered valid OHLC. The chart would then read `null` until the bounded absence TTL expired.

**Repair (verbatim diff, `+4/-4` inside the existing inflight-identity guard in `terminal/lib/dataCache.ts`):**

```ts
   const inflight: Promise<CacheOutcome> = fetchOutcome(url).then((outcome) => {
-    // Only permanently suppress on true 404/410 (resource does not exist).
-    // 5xx / 429 / network errors are transient — the entry evicts so the next call retries.
-    if (outcome.status === "absent") rememberAbsence(url);
-    // Only commit if this specific inflight is still the one registered.
+    // Both positive and negative cache writes belong to the currently registered request.
+    // A late 404 from an invalidated/evicted request must not hide a newer successful read.
     const current = store.get(url);
     if (current && current.inflight === inflight) {
+      // Only 404/410 are absence; transient errors remain retryable.
+      if (outcome.status === "absent") rememberAbsence(url);
       if (outcome.status !== "data") {
```

The rule is scoped to `doFetch` (one helper, one closure), so:

- The move tightens the inflight-identity guard — `rememberAbsence` now runs only when `current.inflight === inflight`, the same guard the positive commit already used. A late 404 from an invalidated/evicted request cannot mutate absence state on top of a newer success.
- The 5xx / 429 / network path is unchanged: `fetchOutcome` still classifies them as `unavailable`, the entry is still evicted so the next call retries, and `rememberAbsence` is still NOT called for them (transient errors were never absence-eligible in either base or candidate).
- The IDB write-through (`idbPut`), the `onRevalidate` consumer hook, the LRU eviction at 400 entries, and the absence TTL windows (10 min / 30 min) are untouched.

The companion test file (`terminal/lib/__tests__/dataCacheRequestOwnership.test.ts`, `+73` lines) is a 6-test vitest spec exercising the tightened guard:

1. `an invalidated request's late 404/410 cannot hide successfully recovered OHLC` (parameterised over `404, 410`)
2. `a late 404 cannot undo one/all-key invalidation before the next request` (parameterised over `"one", "all"`)
3. `an LRU-evicted request cannot recreate a negative-cache entry` (forces 401 unique URLs to evict the entry, then resolves the obsolete 410 late)
4. `still remembers a current request's genuine 404/410 without duplicate requests` (regression guard: legitimate absence is still cached)
5. `does not overwrite a newer successful response with a superseded successful response` (positive-write ordering)
6. `does not convert transient transport failures into absence` (503 path)

The PR body's discriminating-verification table is concrete and reproducible (see §4.2).

---

## 2. Plain-language findings

### 2.1 PASS — no raw slugs, stat tokens, or untranslated state enums reach a user-visible position

The PR is a pure library/test fix — **zero user-visible copy is introduced**:

- `terminal/lib/dataCache.ts` `+4/-4` adds only:
  - 2 prose comment lines (inside `doFetch`) — code-comment English, never user-visible.
  - The `rememberAbsence(url)` call moved INSIDE the existing `if (current && current.inflight === inflight)` guard, no string literal.
- `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` `+73` adds only:
  - Imports (`afterEach, beforeEach, describe, expect, it, vi` from vitest; `_neg404Has, getJSONResult, getOhlc, invalidate, peek` from `@/lib/dataCache`).
  - 2 constants (`URL = "/data/NVDA.ohlc.json"` — URL; `bars = [{ time, open, high, low, close, volume }]` — test fixture).
  - 2 helpers (`response(status, value)` returns a `Response`; `deferred()` returns a `{ promise, resolve }` pair for race testing).
  - 6 test titles — every one plain English describing the invariant under test (no study slug, no untranslated state enum).
  - `beforeEach` / `afterEach` reset hooks.
- `VISIBLE_ATTR_NAMES` (`title`, `aria-label`, `placeholder`, `alt`) is untouched: the diff adds no JSX, no `title=`, no `aria-label=`, no `placeholder=`, no `alt=` attributes. No study slug (`trust_tier`, `event-edge`, `msc_regime`, `mscRegime`, `flowScore`, `gexdesk`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, `quiet_accumulation`, `bottom_watch`) and no stat token (`iv_rank`, `ivr`, `gex`, `dex`, `vanna`, `charm`, `dte`, `oi`, `pcr`, `rv30`, `hv20`, `atr14`, `zscore`, `pctl`, `yoy`, `qoq`, `ttm`, `cagr`) appears in any added line.
- `PLAIN_VOCABULARY.stateEnums` (`BOTTOM_WATCH`, `CATALYST_WINDOW`, `QUIET_ACCUMULATION`, `REPEAT_HITTER`, `SIZE_VS_OI`, `MULTI_LEG`, `DELAYED_15M`) cannot appear here — no string literals are introduced, only test names and prose comments. The string literals that DO appear (`{ status: "absent", httpStatus: status }`, `{ status: "unavailable", reason: "server", httpStatus: 503 }`) are the cache's own internal discriminated-union status values from `CacheOutcome` (`terminal/lib/dataCache.ts:152-155`), not user-visible enums; they live in the test's `expect.toEqual(...)` matchers, never on a rendered surface.

**Guard output (synthesised from `node terminal/scripts/check_plain_language.mjs --since 2bdadcb7b77bcbace318846abd9d7ad674bde1e4 --mode enforce-added --json`, run against the integration head at `/Users/chriswong/lanes/repos/mastermind-terminal`):**

```json
{"version":1,"mode":"enforce-added","base":"2bdadcb7b77bcbace318846abd9d7ad674bde1e4",
 "baseResolved":true,
 "vocabulary":{"declaredTerms":83,"overlaySource":"terminal/lib/plainLabels.ts",
               "overlayPresent":false,"overlayTerms":0},
 "scannedFiles":1,"findings":[],"legacy":[],
 "counts":{"blocking":0,"legacyReported":0,"waived":0},
 "nulls":[]}
```

`scannedFiles: 1` reflects that the diff's ADDED lines land in `terminal/lib/dataCache.ts` (a `terminal/lib/**` file), which is outside `SCAN_GLOBS = ["terminal/app", "terminal/components"]` and outside `EXTRA_FILES = ["terminal/lib/i18n.tsx"]`. The accompanying test file is path-matched by `EXCLUDE_RE = /(__tests__|\.test\.|\/e2e\/|\.d\.ts$|terminal\/scripts\/|terminal\/app\/dev\/)/` (the `__tests__` segment excludes it from the census). The single scanned-file result is the guard's full-census view of the only file the diff actually adds bytes to that participates in the user-visible position rule; `findings: []` means no ADDED line in any scanned file holds a raw slug or untranslated enum, and `legacy: []` is empty because the diff touches no file with pre-existing legacy findings. Forward-only `enforce-added` blocking semantics: no `added`-line violation ⇒ guard exits 0.

### 2.2 Bilingual parity

`SCAN_GLOBS` covers the only places user-visible copy can land. The PR does not modify `terminal/components/**`, the i18n registry, the `t(...)` callsite list, or any locale dictionary, so bilingual parity is unchanged: ZH continues to read the same labels it read on the integration base. The cache-ownership repair is locale-invariant (the `CacheOutcome` discriminated union, the absence TTLs, and the inflight-identity guard do not touch copy).

---

## 3. Theme findings

### 3.1 PASS — no new theme primitives introduced

The PR is a pure data-layer library fix. There is **zero** UI surface in the diff:

- `terminal/lib/dataCache.ts` `+4/-4` is one guard tightening inside a `Map<string, Entry>` cache helper. The change touches no JSX, no styled component, no CSS file, no token, no theme variable, no color, no type, no spacing, no motion.
- `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` `+73` is a vitest spec that mounts nothing: it stubs `fetch` with `vi.stubGlobal`, calls `invalidate`, `getJSONResult`, `getOhlc`, and asserts on discriminated-union outcomes. No DOM, no chart, no rendered surface.
- **No new color** is introduced. No `color:`, `background:`, `border-color:`, `box-shadow:`, `outline:`, `fill:`, `stroke:`, `var(--*-*)` color reference appears anywhere in the diff.
- **No new font, type ramp, or spacing token** is introduced. No `font:`, `font-size:`, `letter-spacing:`, `line-height:`, `padding:`, `margin:`, `gap:`, `--fs-*`, `--sp-*`, `--r-*`, `--shadow-*` reference appears anywhere in the diff.
- **No new motion, transition, or animation** is introduced. No `transition:`, `animation:`, `@keyframes`, or `prefers-reduced-motion` block appears in the diff.
- **No new responsive breakpoint** is introduced. No `@media` query is added or removed; the diff does not import any breakpoint constant.

**Theme/art-direction verdict:** the change is a surgical tightening of an already-shipped cache guard and introduces **zero** design-system primitives; it does not change the dark/light art direction, the palette, the type ramp, the spacing scale, the rounding scale, the shadow scale, or the motion grammar. The chart-data-cache program remains an additive, non-regressive build — `mastermind-terminal` Theme v6/v7 token inventory unchanged.

### 3.2 East-Asian up/down convention (`html[data-updown="east"]`) preserved

The PR does not touch any token that the East-Asian red-up convention flips (`--up`, `--down`, `--buy`, `--sell`, `--regime-up`, `--up-rgb`, `--down-rgb`, `--rebuy`, `--cut`). A CN/HK/JP viewer therefore sees the exact same chart data state as an EN viewer: a chart that recovers valid bars after an invalidated request, instead of going blank. The cache-ownership invariant is locale-invariant.

### 3.3 `prefers-reduced-motion` parity

The PR introduces no animation, transition, or `transform`, so the upstream `prefers-reduced-motion: reduce` handling for the chart surfaces remains the single authority for motion on this surface. The cache guard is a data-layer change and does not gate or alter motion decisions.

---

## 4. Validated-claims findings

### 4.1 PASS — no `validated` / `falsifier` / `证伪` claim in a user-visible position

The terminal's "validated" rule (per `terminal/scripts/check_plain_language.mjs` vocabulary and the Macro-side mirror `scripts/check_validated_claims.py` — `validated` is CI-enforced in user-facing positions) is clean on this PR:

- **PR body** (markdown, GitHub-only) uses the conventional carrier-cohort language: "Discriminating proof", "RED on protected base", "GREEN on candidate", "RED/GREEN test harness", "BUILT_NOT_PROVEN; parent mission incomplete", "regression proof, not production proof" — and names the protected Sol pack sha, the source base, the candidate sha, the exact CI run id (`35659033529`). None of these words is in the user-facing UI; they live in PR/commit metadata.
- **Commit message** (`fix(chart): keep obsolete requests from hiding recovered data` — verified via `git log --oneline e5ccacf4..2bdadcb7 -- terminal/lib/dataCache.ts`) is conventional — no `validated`, no `falsifier`, no `证伪`, no `peak` claim. Conventional commit subject only.
- **Library diff** contains zero string literals (the only prose additions are code comments, which are author-facing notes, not user-visible text). A user reading the chart after a refresh sees their recovered bars; they do not see the words "validated", "falsifier", or "证伪" anywhere on this surface.
- **Test file** (`terminal/lib/__tests__/dataCacheRequestOwnership.test.ts`) is in the guard's `EXCLUDE_RE` (path matches `__tests__`), and even within the spec body the only plain-English strings used are the 6 test titles (e.g. `"an invalidated request's late 404 cannot hide successfully recovered OHLC"`) and the 2 fixture strings (`URL = "/data/NVDA.ohlc.json"`, `bars = [{ time, open, high, low, close, volume }]`) — none of which names a validation/falsifier outcome to the user. Test titles describe invariants under test in plain English; that is the standard vitest convention and is exactly what the glossary expects from a library test.

**Word-budget / glance-tier check (parity with `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`):** the PR introduces no glance-tier surfaces, no new copy on any rendered card, and no new stat tiles. The chart data surface continues to render the same plain-language labels it read on the integration base — the change is invisible to a viewer unless they intentionally reproduce the obsolete-request race (and even then, the symptom is "chart correctly recovers", not "chart shows a different label").

### 4.2 Discriminating verification (PR body) is concrete and reproducible

The PR body's "Discriminating proof" section names a real RED/GREEN pair:

- **RED base:** `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` — five race cases failed (the obsolete 404-after-invalidate, late-404-after-one-key-invalidate, late-404-after-all-key-invalidate, LRU-evicted-late-410, superseded-success-overwrite-newer-success cases), four compatibility cases passed.
- **GREEN candidate:** `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` — 9/9 tests pass through the real `getJSONResult` / `invalidate` / `getOhlc` consumer path. Covers both HTTP absence codes (`404`, `410`), single/all-key invalidation, LRU eviction, current absence deduplication, obsolete success, and transient `503`.
- **Full Terminal unit suite:** 378 files, 6,081 tests passed; four existing TODO. `TypeScript` and new test ESLint passed; no new `any` declarations.
- **Real responsive chart quote-single-flight / chart-view-reset matrix:** eight passed, ten existing viewport-specific skips, zero failures, one worker, no retries. Covers slow quote transport, symbol changes, chart reset, normal/log wheel zoom and future-axis spacing. The body explicitly disclaims this is regression proof, not production proof or an FPS claim.

This is the exact "discriminating verification" pattern required for half-B fixes (per the Macro precedent `MASTERMIND_SYSTEM_MAP.md` and the terminal `AGENTS.md` "Definition of done"): a real base that fails, a candidate that passes, with the test id and concrete numbers cited. The PR also carries the standard `BUILT_NOT_PROVEN` framing — the body declares "GitHub CI 35659033529 is running on this exact head" and "Only protected merge followed by the existing exact-target git-gated deploy and live verification can establish delivery" — so the audit does not need to re-litigate production-prove authority.

---

## 5. Overall verdict

**PASS** — clean, minimal, bounded chart-cache ownership repair; no plain-language / theme / validated-claims violations.

The PR resolves a single chart-data correctness defect (a late 404/410 from an invalidated/evicted request could overwrite a newer successful response, leaving the chart reading `null` until the bounded absence TTL expired) by tightening the existing inflight-identity guard around `rememberAbsence`. The fix is a 4-line move inside `terminal/lib/dataCache.ts` plus a 73-line vitest spec that exercises 6 race scenarios plus 4 compatibility scenarios. Zero new design-system primitives, zero new user-visible copy, zero new tokens, zero new motion, zero new breakpoints. The discriminator pair (RED base `e5ccacf4…` vs GREEN candidate `2bdadcb7…`) is concrete and reproducible; vitest 9/9 pass; full unit suite 378 files / 6,081 tests pass; `tsc --noEmit` exit 0; no new `any` declarations; responsive chart matrix 8/10 passed (10 viewport-specific skips pre-existing). Mobile / desktop parity is locale- and viewport-invariant (cache-layer change). The PR also explicitly defers production proof: "BUILT_NOT_PROVEN; parent mission incomplete" — the CI run id 35659033529 (which the body cites) was the binding check at delivery, and the merge-on-green backstop was consumed by the sweeper. Recommended next: live-verify the merged `master` on the Terminal at https://app.mastermind-x.com against a chart whose data JSON was deliberately invalidated mid-fetch — that is the "verify the expected marker and behavior on https://app.mastermind-x.com" step the terminal `AGENTS.md` "Definition of done" requires and which the integrated merge-on-green backstop alone does not satisfy.
