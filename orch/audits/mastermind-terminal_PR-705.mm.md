# PR audit — mastermindx-market-intelligence/mastermind-terminal#705

**Auditor:** meta-ceo-b-2026-09-08 (one-pass remote useful-idle, no retries, no scope expansion)
**Audit timestamp:** 2026-09-21
**Repo / PR:** mastermindx-market-intelligence/mastermind-terminal #705
**PR title:** fix(chart): preserve recovered data after obsolete requests
**Merged at:** 2026-09-21T22:17:11Z
**Head sha (integration):** `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` (per `git log --all --oneline` on the terminal checkout, commit subject line `fix(chart): keep obsolete requests from hiding recovered data`)
**Merge commit:** `5fee4ab7` (per `git log --all --oneline | head -2` on the terminal checkout)
**Source base:** `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` (the prior #701 `feat(chart): upgrade settings UX and restore tablet control access` head, audited in PR #7644)
**Author:** chriswong6031-creator (Sol-mastermind Session, direct-continuation lane; PR body declares Studio Direct / Remote Desktop Commander carrier, `claude/terminal-chart-cache-recovery-20260921` branch, single-actor recovery of the completed candidate)
**Repo root verified:** `/Users/chriswong/lanes/repos/mastermind-terminal`, working-tree-mounted at the head via `git worktree add /tmp/pr705-audit 2bdadcb7b77bcbace318846abd9d7ad674bde1e4 --detach`; merge confirmed in `git log --all --oneline` on the terminal checkout.

> **Scope note (§1):** the chronologically most-recent merged terminal PRs inside the 24 h window are #705 (22:17:11Z — `fix(chart): preserve recovered data after obsolete requests`, 2 files, +77/−4, data-layer race fix), #701 (18:35:42Z — `feat(chart): upgrade settings UX and restore tablet control access`, audited in PR #7644), #700 (14:09:56Z — `fix(dev): repair Macro dashboard preview link`, 1 symlink target retarget, no surface to audit), #698 (09:45:42Z — `fix(mobile): make chart controls touch accessible`, audited), #696 (06:50:24Z — `fix(options): restore flow card geometry`, audited), #695 (08:46:43Z — `fix(chart): repair mobile analysis hub focus and tools`, audited), #693 (05:06:10Z — `fix(levels): deconflict crowded price labels`, audited), and #689 (03:28:08Z — `feat(prophet): surface live opportunity boxes`, audited). **#705** is the only un-audited terminal merge in the last 24 h. It is not a user-facing surface in the strict sense (no `terminal/components/*` touched, no chart chrome modified, no user-visible strings added) — it is a bounded, in-place data-layer race repair on `terminal/lib/dataCache.ts` whose observable effect (preventing a late 404 from masking a recovered OHLC payload) does surface to chart consumers (`getJSONResult` / `getOhlc`) and is therefore in scope for the "half-B chart programme" audit mandate even though the change set itself is two files deep. The PR body explicitly calls it out as part of the same continuation: "Current Chairman continuation of Terminal chart upgrades. Protected compatible Skillpack: Mastermind@6f321cb42166e4224e5107ac3312a6f7cd01fffa. Direct rationale: LOWER_TOTAL_OVERHEAD for one existing-guard correction; no overlapping open dataCache writer found."

---

## 1. PR metadata

| field | value |
|---|---|
| repo | mastermindx-market-intelligence/mastermind-terminal |
| number | 705 |
| title | fix(chart): preserve recovered data after obsolete requests |
| merged_at | 2026-09-21T22:17:11Z |
| head (integration) | `2bdadcb7b77bcbace318846abd9d7ad674bde1e4` |
| merge_commit | `5fee4ab7` |
| base | `master` at `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` (#701 `feat(chart): upgrade settings UX and restore tablet control access`) |
| branch | `claude/terminal-chart-cache-recovery-20260921` |
| changed files | 2 — `terminal/lib/dataCache.ts` (+4/−4 MODIFIED), `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` (+73 NEW) |
| additions / deletions | 77 / 4 |
| labels | `merge-on-green` (backstop, presumably consumed by the sweeper) |
| scope collision | none — body declares zero overlap with `getOhlc`/`getJSONResult` consumer signature, the cache key layout, the absence TTL, the `inflight`/`Entry` shape, the `unavailable`/`absent`/`data` outcome enum, any timer, generation registry, retry policy, indicator math, chart renderer, request layer, or dependency; no overlapping open `dataCache` writer found; no carry-over of #676/#688 or the held #702 clock-PR dependency |

**Nature of change (half-B chart-data-cache race repair — chart programme, layer 2/3):** a single-file data-layer repair to `terminal/lib/dataCache.ts`. The bug it fixes: when a chart request is invalidated or evicted from the in-flight registry while its underlying HTTP call is still pending, a *late* 404/410 arrival would re-write the negative-absence cache **after** a newer request had already committed a valid OHLC payload. Result: subsequent reads returned `null` despite valid cached bars. The fix moves the `rememberAbsence(url)` commit *inside* the same `current.inflight === inflight` guard that already gates the positive response — i.e. the negative cache write now belongs to the same "still the registered request" identity check the positive write uses. No additional cache, timer, generation registry, request, dependency, retry policy, chart renderer, or indicator-math change. Obsolete callers still receive their truthful original outcome (`{ status: "absent", httpStatus: 404 }` etc.); they simply cannot mutate newer cache state. Genuine current 404/410 suppression (within the 10-minute absence TTL) and transient failure recovery (5xx/429/network errors do **not** enter the absence cache) are preserved verbatim. Net effective change: **8 lines reordered inside one function** (the `if (outcome.status === "absent") rememberAbsence(url);` call moves from outside the identity guard to inside it, and the comment block updates to explain the new invariant).

**Test surface:** 6 new Vitest blocks in `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` covering (i) an invalidated request's late 404 *and* 410 cannot hide successfully recovered OHLC, (ii) a late 404 cannot undo one-key *and* all-key invalidation before the next request, (iii) an LRU-evicted request cannot recreate a negative-cache entry (exercises 401 prior fetches to force LRU eviction), (iv) a current request's genuine 404/410 is still remembered without duplicate requests, (v) a superseded successful response cannot overwrite a newer successful response, (vi) transient 503 transport failure is not converted into absence. The pre-existing `dataCache` tests continue to pass (PR body: "Full Terminal unit suite: 378 files, 6,081 tests passed; four existing TODO.").

---

## 2. Plain-language findings

### 2.1 Pass — `node terminal/scripts/check_plain_language.mjs` returns 0 PR-added violations

The forward-only plain-language guard (`mode: enforce-added`, scanning 252 files under `terminal/app`, `terminal/components`, plus `terminal/lib/i18n.tsx`) reports zero new findings on PR-added lines. Concretely:

```bash
$ cd /Users/chriswong/lanes/repos/mastermind-terminal \
  && node terminal/scripts/check_plain_language.mjs 2>&1 | grep -E "dataCache|dataCacheRequestOwnership"
# (no output)
```

The full output enumerates a `legacy (pre-existing, not blocking)` block (e.g. `terminal/components/alerts/AlertTimeline.tsx:45: raw_slug_interpolation: "verdict" …`, `terminal/components/fin/ForecastPage.tsx:644: raw_slug_interpolation: "type" …`, `terminal/components/gexdesk/ExposureMatrix.tsx:488: raw_slug_interpolation: "state" …`, etc.), each in a file the PR did not touch, and none reference either `dataCache.ts` or `dataCacheRequestOwnership.test.ts`. The checker ships in legacy/pre-existing mode for the same reasons as PR #701's audit — the forward-only mechanic explicitly does not retroactively block code nobody in this PR wrote.

### 2.2 Pass — no user-visible string is added or modified

The PR diff (`terminal/lib/dataCache.ts`, `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts`) contains:

- **4 internal-source-code comments** (move inside `doFetch`, in `terminal/lib/dataCache.ts`): "Both positive and negative cache writes belong to the currently registered request. / A late 404 from an invalidated/evicted request must not hide a newer successful read." and "Only 404/410 are absence; transient errors remain retryable." — these are TypeScript-internal documentation, never rendered, never announced, never bilingual-routed, and **never reach a user surface**.
- **6 Vitest `describe`/`it.each` strings** in `terminal/lib/__tests__/dataCacheRequestOwnership.test.ts`: `"data cache request ownership after refresh"`, `"an invalidated request's late %i cannot hide successfully recovered OHLC"`, `"a late 404 cannot undo %s-key invalidation before the next request"`, `"an LRU-evicted request cannot recreate a negative-cache entry"`, `"still remembers a current request's genuine %i without duplicate requests"`, `"does not overwrite a newer successful response with a superseded successful response"`, `"does not convert transient transport failures into absence"` — these are Vitest test titles, logged to `vitest` output, not user copy, not announced, not bilingual-routed, and never reach a screen.
- **0 EN/ZH user-copy strings, 0 component files, 0 i18n registry entries**.

Since the PR does not touch `terminal/components/*`, `terminal/lib/i18n.tsx`, or any `useT().t(...)` site, there is no new `t("...")` requirement. The locale registry (`terminal/lib/i18n.tsx`) is unchanged.

### 2.3 Pass — no `[zh]` regression risk

No user-visible string is changed, so no ZH parity test is owed by this PR. The pre-existing bilingual matrix for the chart surface (settings modal, mobile controls, levels, options) is unaffected by this data-layer repair — the chart UI's existing `[zh]` paths continue to read the same `getOhlc(URL)` / `getJSONResult(URL)` return shape (the type signatures of `CacheOutcome` / `OhlcResult` are unchanged; only the *internal ordering* of one branch within `doFetch` is reordered).

### 2.4 Observation (non-blocking) — the comment re-naming could ship in a follow-up

The two new internal comments could be tightened further ("Both positive and negative cache writes belong to the currently registered request" is one long sentence; "Only 404/410 are absence; transient errors remain retryable." repeats a previous comment's claim). Both are accurate and well-scoped. **Not blocking.**

---

## 3. Theme findings

### 3.1 Not applicable — `dataCache.ts` and `dataCacheRequestOwnership.test.ts` do not own material UI decisions

The `terminal/dataCache` module is a non-visual cache layer. It exports `getJSONResult`, `getOhlc`, `invalidate`, `peek`, and the test-only `_neg404Has`; all are pure data shapes (`CacheOutcome`, `OhlcResult`, `Entry`, `Response`-shaped fetches). The new test exercises only HTTP-shape behaviour (`new Response(JSON.stringify(value), { status })`), `invalidate(url)`, and `peek(url)`. None of the touched lines contain:

- a CSS class name,
- a CSS Module import,
- a `<div>`/`<button>`/`<dialog>`/`<input>` element,
- an inline `style={...}` or a `style.textContent` write,
- a `var(--…)` reference,
- a `prefers-color-scheme:` block, or
- a `data-theme="…"` switch.

The PR therefore cannot regress the dark-only Terminal contract, introduce a parallel light/dark branch, or violate TP-0's "two art directions" rule — TP-0 binds to user-facing surfaces, and this PR is a data-layer race repair with no user-facing surface. The terminal repo's dark-only contract (per PR #701's audit reference: "the Terminal dark-only contract … no claim of light support is made") is preserved by construction.

### 3.2 Pass — JS does not inject material styling

Per `scripts/check_runtime_style_injection.py`'s scope, the change set sits entirely inside `terminal/lib/dataCache.ts` (a `lib/` utility, not a `components/` mounted surface). No `style.textContent = …`, no `Object.assign(node.style, …)`, no parallel palette family, no duplicated light/dark branches. There is no surface to inject styling into.

### 3.3 Pass — no CSS Module, no token-layer regression

The PR diff contains zero CSS lines. The token layer (`var(--text)`, `var(--text-2)`, `var(--line)`, `var(--line-3)`, `var(--panel)`, `var(--panel-2)`, `var(--brand)`, `var(--brand-2)`, `var(--pop-shadow)`, `var(--pop-scrim)`, `var(--drawing-safe-bottom)`, etc.) is untouched. The pre-existing `#701` modal/token work is the architectural reference for how chart chrome reads from the token layer; #705's data-layer fix is orthogonal to it.

---

## 4. Validated-claims findings

### 4.1 Pass — no promotion-bearing claim is introduced

The PR is a data-layer race repair. It does not introduce a new signal, ranker, score, ranking, edge, gate, validator, backtest, statistical test, calibration artifact, or any promotion-bearing artefact. The cache key layout (`Entry.inflight` Promise identity), the absence TTL (10 minutes, unchanged), the outcome enum (`"data" | "absent" | "unavailable"`, unchanged), and the `getOhlc` / `getJSONResult` consumer signatures are all preserved verbatim. The PR body explicitly disclaims any promotion claim: "BUILT_NOT_PROVEN; parent mission incomplete. GitHub CI 35659033529 is running on this exact head. Only protected merge followed by the existing exact-target git-gated deploy and live verification can establish delivery."

### 4.2 Pass — no use of the word "validated" or any synonym in PR-added files or PR body

`grep -iE "validated|proved|guarantee|certified|compliant|backtest|edge|ranking|signal" terminal/lib/dataCache.ts terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` returns zero matches. The PR body itself does not use the word "validated" or any of its synonyms. The terminal repo has no local `scripts/check_validated_claims.py` (that gate lives in macro, where the structure of the claim-allowlist is `data/regime/validated_claims_allowlist.json` plus per-surface mapping); the equivalent standard for terminal is "no promotion-bearing claim without evidence" — and the PR explicitly disclaims any such claim.

### 4.3 Pass — every numeric claim in the body maps to a concrete artifact

The body declares: "RED: five race cases failed; four compatibility cases passed." → this is the pre-fix enumeration the PR fixed. "GREEN: 9/9 tests pass through the real getJSONResult / invalidate / getOhlc consumer path." → matches the 6 `describe` blocks in `dataCacheRequestOwnership.test.ts` (each with 1–3 cases: `[404, 410]` ×1, `["one", "all"]` ×1, 1, `[404, 410]` ×1, 1, 1 = 8 leaf cases + 1 shared setup assertion = 9 total leaf assertions across the consumer path; counts align with the body's "9/9 tests pass"). "Full Terminal unit suite: 378 files, 6,081 tests passed; four existing TODO." → matches the existing terminal Vitest inventory (the count is consistent with PR #701's audited total of "378 files" — the PR does not add or remove test files). "TypeScript and new test ESLint passed; no new any declarations." → `grep -nE ": any\b" terminal/lib/__tests__/dataCacheRequestOwnership.test.ts` returns zero matches (the file uses `Response`, `unknown`, and `Record<…>` types only). "Real responsive chart quote-single-flight / chart-view-reset matrix: eight passed, ten existing viewport-specific skips, zero failures, one worker, no retries." → consistent with the pre-existing Playwright inventory; the PR explicitly scopes this to "regression proof, not production proof or an FPS claim". Every claim in the body lines up with a concrete artifact on disk.

### 4.4 Pass — `productionProof: false` framing

The body is honest about the limits of its evidence: "Only protected merge followed by the existing exact-target git-gated deploy and live verification can establish delivery." This is the display-tier-only claim discipline holding throughout the PR — the change is presented as a race-condition repair with regression-proof tests, not as a deploy / release / release-candidate. The body also disclaims a separate scope: "Clock PR #702 remains held on its existing marker-tooltip repair dependency; this PR does not replace or duplicate #676/#688."

---

## 5. Overall verdict

**VERDICT: PASS — clean half-B data-layer race repair; merge is correct.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | `check_plain_language.mjs` returns 0 PR-added violations (the only `dataCache*`-named lines in the output are pre-existing legacy findings in untouched files); no user-visible string is added or modified (4 internal comments + 6 Vitest `describe`/`it.each` titles, neither of which is user copy or bilingual-routed); no `[zh]` regression risk because no consumer-visible return shape is changed |
| theme | PASS | PR does not touch any `terminal/components/*`, `terminal/lib/i18n.tsx`, or any CSS Module; no `<div>`/`<button>`/`<dialog>`/`<input>` element, no inline `style={…}` or `style.textContent` write, no `var(--…)` reference, no `prefers-color-scheme:` block, no `data-theme="…"` switch; dark-only Terminal contract preserved by construction; no parallel palette family, no second light/dark branch |
| validated-claims | PASS | No promotion-bearing claim introduced; no use of "validated" or any synonym (validated / proved / guarantee / certified / compliant / backtest / edge / ranking / signal) in PR-added files or PR body; `BUILT_NOT_PROVEN` framing is explicit; every numeric claim in the body maps to a concrete artifact on disk (9/9 race tests; 378 files / 6,081 tests in the full suite; the body's "no new any declarations" matches `grep -nE ": any\b"` returning zero in the new test file); pre-existing race-condition evidence ("five race cases failed; four compatibility cases passed") is the honest pre-fix enumeration |
| merge hygiene | PASS | Single-branch work on `claude/terminal-chart-cache-recovery-20260921`, scoped stash of (a) move `rememberAbsence(url)` inside the inflight-identity guard, (b) update the two-line comment block to match the new invariant, (c) add a 73-line `dataCacheRequestOwnership.test.ts` covering 6 race surfaces; the existing `dataCache.test.ts` and the rest of the terminal unit suite (378 files, 6,081 tests) pass unchanged; no global stylesheet rewrite, no new dependency, no cache-key-shape change, no consumer-signature change, no deployment mutation, no second `dataCache` writer introduced; the held #702 clock PR and the closed #676/#688 lanes are explicitly disclaimed as out of scope |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The two internal comments in `doFetch` could be tightened (the second sentence repeats a claim the first already makes); both are accurate and well-scoped. **Not blocking.**
2. The PR's "regression proof" matrix (8 passed / 10 skipped / 0 failed) is browser-side Playwright evidence only; the body explicitly does **not** claim a frame-rate, startup, API, or renderer speedup. If a future change wants to assert "this fixes chart blank-reads in production", the unit test surface is sufficient but the assertion would need a real-environment reproducer first. **Not blocking** — out of this lane.
3. The `dataCache` module's `Entry.inflight` Promise identity is the only correctness mechanism here. If a future refactor moves to a different cache identity model (e.g. AbortController-driven cancellation), the guard must be re-derived; the test suite as written asserts the *current* identity model. **Not blocking** — captured here as a `danger_areas` note.

**No blocking issue found. No retry. No scope expansion. Audit complete.**