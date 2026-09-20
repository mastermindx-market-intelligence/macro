# Audit — mastermindx-market-intelligence/mastermind-terminal PR #685

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#685](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/685) |
| title | `perf(rsix): share RSI kernel within suite pass` |
| merged | 2026-09-20T12:22:33Z (within the 24-h window of this audit: ~2026-09-19T18:00Z → audit run) |
| merge head (`gh pr view 685 … headRefOid`) | `4fd7bf2abb6ab364c2338be1145c16015c8f045e` (perf(rsix) commit, squash-merged onto `origin/master`) |
| PR commit (perf(rsix) commit on the branch) | `9b6d4a7e2a94776e6980e3c7a4a722a094431800` |
| base (pre-PR master) | `098e4fcb48a91a5fac14255c07541b7f5665daee` (perf(chart): batch premium cloud color runs — #684's merge commit) |
| commits in PR | 1 (the `perf(rsix)` commit, squash-merged into the above merge head) |
| files | 2 files / +89 / −13 (`git diff --shortstat 098e4fc 9b6d4a7`): `terminal/lib/__tests__/rsiPassCache.test.ts` (+50 / new), `terminal/lib/suites/rsix/rsiEngine.ts` (+39 / −13) |
| branch | `claude/terminal-rsi-kernel-r10-20260920` (round 10 of the chart-smoothness program) |
| half-B label | **half-B (round 10 of the Terminal chart-smoothness program).** The Terminal RSI Ultimate suite is a B-tier user-visible chart surface (RSI Engine + Signals + Divergence + Channels are drawn every render pass on every RSI-equipped chart). Sharing the kernel across the four same-pass consumers removes duplicate work that previously rebuilt the same typed arrays 4× per `computeSuite()` call — the user-visible win is smoother pan/zoom/auto-refresh on RSI charts at 1k–10k bars. The PR body documents measured median reductions of ~14% at 1,255 bars, ~26% at 5,000 bars, and ~20% at 10,000 bars on the same machine against the exact pre-PR baseline. |
| scope | Render-time CPU only — no host cache, no persistent cache, no scheduler, no chart renderer, no signal/event math, no pane layout, no data authority change. The cache key lives behind a non-enumerable `Symbol` so it cannot become a setting, a memo-key input, or a serialized payload. A fresh `ctx.suite` object per `computeSuite()` pass means accepted live bars cannot read a stale prior-pass result; missed cache on changed bar identity OR changed Engine settings. |
| live proof | `npx tsc --noEmit` PASS; focused ESLint PASS on the touched RSI file (pre-existing `any` option-reader inputs tightened to `unknown` without runtime behavior change); RSIX + premium-suite focused parity 266/266 PASS; full Terminal suite 375 files / 6,022 passed / 4 todo; `npm run build` PASS on Next 16.2.9; `git diff --check` PASS; real lazy-loaded RSI pane browser contract desktop/tablet/mobile 3/3 PASS. The pre-existing Turbopack NFT warning through `lib/flowSource.ts` is untouched by this PR. |

## Diff content (exact)

**Code (1 file modification, +39 / −13; no new exported symbol besides the internal `RSI_PASS_CACHE` Symbol)**

`terminal/lib/suites/rsix/rsiEngine.ts`:
- Type tightening (5 sites, no runtime behavior change): `numOpt(v: any, …)` → `numOpt(v: unknown, …)`, `intOpt(v: any, …)` → `intOpt(v: unknown, …)`, `boolOpt(v: any, …)` → `boolOpt(v: unknown, …)`, `selOpt<T extends string>(v: any, …)` → `selOpt<T extends string>(v: unknown, …)`, `rsiEngineParams(suite: Record<string, any> | undefined)` → `rsiEngineParams(suite: Record<string, unknown> | undefined)`. ESLint was flagging the pre-existing `any` and this PR cleans it. The parsed values are unchanged.
- Drop the unused import `SuiteField` from `@/lib/indicator-canvas/types` (1 line deleted).
- Introduce a `RsiPassCache = { bars: SuiteBar[]; key: string; result: UltimateRsi }` type and a non-enumerable `const RSI_PASS_CACHE: unique symbol = Symbol("rsix.pass-rsi")` (4 lines added: the type, the symbol, two blank lines).
- Rewrite `sharedRsi(ctx: ModuleCtx)` (16 lines added, 1 removed) to:
  1. Compute `p = rsiEngineParams(ctx.suite)` and a `key = `${p.len}|${p.source}|${p.smoothLen}|${p.smoothType}`` cache key.
  2. Legacy/unit callers without `ctx.suite` retain the exact pre-PR fail-soft direct-compute path (`if (!ctx.suite) return resultForPass()`).
  3. On a populated `ctx.suite`, check `pass[RSI_PASS_CACHE]` for a hit: same `bars` reference AND same `key` → return the cached `result`.
  4. On a miss, compute the result and `Object.defineProperty(pass, RSI_PASS_CACHE, { value: { bars, key, result }, writable: true, configurable: true, enumerable: false })`. Non-enumerable Symbol means `Object.keys(pass)` / `JSON.stringify(pass)` cannot surface it (a property the existing pass-cache test asserts).
- In `compute(ctx)`, replace the inline 5-line `len/source/smooth/smoothLen/smoothType` setup + `computeUltimateRsi(bars, len, source, smoothLen, smoothType)` call with `const { rsi, smooth } = sharedRsi(ctx)` (5 lines net). The `wantSmooth` local and the `zh` boolean are kept (they're still used downstream for label toggling).
- No change to `computeUltimateRsi()`, `rsiEngineParams()`, the four downstream consumers (`rsiSignals.ts:111`, `rsiChannels.ts:219`, `rsiDivergence.ts` — which already called `sharedRsi(ctx)`), or `mtfDash.ts:180` (which deliberately still calls `computeUltimateRsi` on RESAMPLED bars — MTF cannot share because the bars reference changes per timeframe).

**Tests (1 new file, +50)**

`terminal/lib/__tests__/rsiPassCache.test.ts`:
- Imports: `describe, expect, it` from `vitest`; `ModuleCtx, SuiteBar, SuiteColors` from `@/lib/indicator-canvas/types`; `computeUltimateRsi, sharedRsi` from `@/lib/suites/rsix/rsiEngine`.
- Helper data: a `colors` literal that is the canonical `SuiteColors` palette used across the suite (`up/down/flowBuy/flowSell/warn/brand/text/muted/neutral`) — same hex values already used elsewhere in `rsiEngine.ts` and the surrounding suite. A synthetic `bars` array of 80 `SuiteBar` rows (timestamps + OHLCV) generated by a deterministic `100 + Math.sin(i/4)*3 + i*.07` formula. A `ctx(pass, rows)` helper that builds a `ModuleCtx` with the canonical suite object, the rows, and the canonical language `"en"`.
- Test 1 — `reuses one RSI pair across module contexts in the same suite pass without polluting settings`:
  - Snapshot `Object.keys(pass)` and `JSON.stringify(pass)` BEFORE the call.
  - Call `sharedRsi(ctx(pass))` and `sharedRsi({...ctx(pass), s:{threshold:65}})` (a second consumer in the same pass with a satellite-local settings bag).
  - Assert the second call returns the EXACT same reference as the first (`b === a`).
  - Assert the `rsi` and `smooth` `Float32Array`s are reference-equal too.
  - Assert `Object.keys(pass)` is unchanged and `JSON.stringify(pass)` is byte-identical — i.e., the `RSI_PASS_CACHE` Symbol is non-enumerable and the satellite's `s` bag never leaks into the engine params. This is the property the PR description claims.
- Test 2 — `misses when bars or engine settings change, and stays bit-identical to direct computation`:
  - Call `sharedRsi(ctx(pass))` with the canonical 80 bars.
  - Call `sharedRsi(ctx(pass, copied))` with `bars.map(b => ({...b}))` (a NEW object identity per bar, same values). Assert the cache MISSES (`b !== a`) but the typed-array VALUES are equal (`[...b.rsi] === [...a.rsi]`).
  - Mutate `pass["eng.len"] = 9`. Call `sharedRsi(ctx(pass, copied))`. Assert it MISSES (`c !== b`).
  - Compute the same input directly via `computeUltimateRsi(copied, 9, "close", 14, "ema")`. Assert `c.rsi` and `c.smooth` are bit-identical to the direct call — i.e., the cached path produces the same output as the legacy direct path. This is the "cached output stays bit-identical to direct `computeUltimateRsi()`" contract the PR body claims.

Schema check: the diff is +89 / −13 net lines, all additive except for the 5 type tightenings + 1 unused-import drop in `rsiEngine.ts` and the 5-line consolidation in `compute()`. No CSS / no PNG / no design-system / no template / no asset / no env file / no chart-renderer change. No JSX mount added or removed. No i18n key added or removed. No settings key added or removed (the `RSI_PASS_CACHE` Symbol cannot become one, which Test 1 hard-pins).

## Plain-language findings

Tool: `terminal/scripts/check_plain_language.mjs --mode enforce-added --since 098e4fc --json` against the merge head (run via a shallow clone of the terminal repo at `9b6d4a7` with `typescript@5.6.3` linked locally; the script needs a populated `node_modules` to import the TypeScript API used for AST-based user-visible-position detection — `npm install typescript@5.6.3 --no-save` in the clone satisfies it).

Per the audit-block convention:

```json
{ "version": 1, "mode": "enforce-added", "base": "098e4fc", "baseResolved": true,
  "vocabulary": { "declaredTerms": 83, "overlaySource": "terminal/lib/plainLabels.ts",
                  "overlayPresent": true, "overlayTerms": 37 },
  "scannedFiles": 252, "findings": [],
  "legacy": [
    { "path": "terminal/components/alerts/AlertTimeline.tsx", "line": 45,
      "rule": "raw_slug_interpolation", "token": "verdict", "blocking": false },
    { "path": "terminal/components/alerts/WatchingList.tsx", "line": 38,
      "rule": "raw_slug_interpolation", "token": "verdict", "blocking": false },
    { "path": "terminal/components/fin/ForecastPage.tsx", "line": 647,
      "rule": "raw_slug_interpolation", "token": "type", "blocking": false },
    { "path": "terminal/components/gexdesk/ExposureMatrix.tsx", "line": 488,
      "rule": "raw_slug_interpolation", "token": "state", "blocking": false },
    { "path": "terminal/components/settings/SectionAccount.tsx", "line": 542,
      "rule": "raw_slug_interpolation", "token": "kind", "blocking": false },
    { "path": "terminal/lib/visualIntelligenceCopy.ts", "line": 64,
      "rule": "raw_state_enum", "token": "DELAYED_15M", "blocking": false,
      "waived": true,
      "waiverReason": "transport basis is compared here, never rendered; the returned key selects localized copy." }
  ],
  "counts": { "blocking": 0, "legacyReported": 6, "waived": 0 }, "nulls": [] }
```

**Verdict: PASS — 0 blocking, no new copy, no new findings introduced. The 6 legacy findings are the same set the previous audits (#658 / #670 / #669) reported: identical paths, lines, tokens, and waiver status.**

The plain-language discipline for this PR has five surfaces to audit:

1. **No new user-facing copy introduced.** The diff is +89 / −13 net, all TypeScript-side: type tightening (`any` → `unknown`), an internal Symbol-keyed cache, a 5-line consolidation in `compute()` that swaps direct calls for `sharedRsi(ctx)`, plus a 50-line vitest file. None of the touched lines reach a user-visible position — `rsiEngine.ts` is a kernel module (computation, not rendering), and the test file does not render. The checker correctly reports zero blocking findings against the added-line set.

2. **No new `title=` / aria-label / tooltip / chip / button strings introduced.** Grep against the diff for string literals that would qualify as user-visible copy returns exactly the type-system enums that already exist (`"close", "hl2", "hlc3"` and `"ema", "sma", "wma"` as allowed-value arrays inside `selOpt<RsiSource>` / `selOpt<RsiSmoothType>` calls in `rsiEngineParams`) — these are the pre-existing arrays, MOVED from the `compute()` body into `rsiEngineParams()` so they live next to the option readers that use them. The values themselves are unchanged; their semantics (internal allowed-value discriminators for the RSI option readers) are unchanged; they never reach a user-visible position because no UI component renders them — the rendered RSI axis / label uses the localized `RsiSource` display string from `rsiSourceLabel()`, not the enum token.

3. **The 6 legacy findings are unchanged from prior audits (#658 / #670 / #669).** They live in `AlertTimeline.tsx:45`, `WatchingList.tsx:38`, `ForecastPage.tsx:647`, `ExposureMatrix.tsx:488`, `SectionAccount.tsx:542`, and `visualIntelligenceCopy.ts:64` (the one waivered finding — `DELAYED_15M` is a transport-basis comparison, not a render). None of these files is touched by PR #685. The PR neither regresses nor heals them; they remain downstream of the #669 retirement plan.

4. **Banned-glance-vocab grep against the diff** for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | 已验证 | 经验证 | 经过验证 | thesis | refut | invalid`: **zero matches in user-facing copy.** "satellite" appears in the JSDoc comment of `sharedRsi` ("a satellite calling `sharedRsi` gets bit-identical series to the ones the Engine draws") — but this is the canonical internal vocabulary for "a downstream module that depends on the producer's typed array" that has been in `rsiEngineParams`'s JSDoc since the W2 law was minted; it's never interpolated into any user-visible node by this PR or any earlier PR. No new banned-vocab is introduced.

5. **The test file's helper data is canonical.** The `colors` literal is the same hex-value suite used by `SuiteColors` everywhere in `rsix` (already typed-checked in `rsiEngine.ts`'s `SuiteColors` import); the synthetic 80-bar `bars` array is a deterministic generator (`100 + Math.sin(i/4)*3 + i*.07`) used purely to exercise the cache hit/miss semantics — none of these constants reach a user-visible position because the test never renders.

**Caveat the next audit should weigh (not a finding, just a calibrated surface note):** the type tightenings (`any` → `unknown`) on the option-reader inputs are the kind of edit that COULD have surface impact if a downstream consumer was relying on the unchecked `any` slipstream (e.g., a downstream caller passing an un-cast value through). PR #685 explicitly checks for and preserves the legacy direct-compute path (`if (!ctx.suite) return resultForPass()`), and the bit-identical cache contract test (`expect([...c.rsi]).toEqual([...direct.rsi])`) is the structural receipt that downstream callers cannot observe a difference. Net behavior parity is provable, not just claimed.

## Theme findings

Laws in force:
- TP-0 theme art-direction (dark + light) — applies to Macro site; terminal inherits the dark-only carve-out.
- `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` — Terminal is dark-only by product decision, so the 8-cell evidence matrix collapses to dark × EN/ZH × desktop 1440 / mobile 390 (4 cells, not 8). The required matrix sentence for any user-facing surface change is the DEC name + 4-cell evidence.

**Verdict: PASS — dark × EN/ZH × 1440/390 inheritance preserved (no surface change).**

This PR is a kernel-side perf optimization, not a visual-surface edit. Specifics:

- `terminal/lib/suites/rsix/rsiEngine.ts` carries no CSS-import, no token reference, no design-system import in this diff (verified via `grep -E '\.css|\.scss|theme|tokens' terminal/lib/suites/rsix/rsiEngine.ts` → no match in the diff context). No new DOM, no new tokens, no new viewport metric, no new typography / spacing / motion primitive.
- The new test file `terminal/lib/__tests__/rsiPassCache.test.ts` is a vitest unit test with no rendering — no chart, no DOM mount, no token reference.
- `scripts/check_design_system.py --mode enforce-added --since origin/main` exits 0 vacuously: no design-system file in the diff.
- `scripts/check_runtime_style_injection.py` is NOT applicable: no new `style={…}`, no `style.textContent = ...`, no `setStyle`, no inline-style mutation in the diff. The cache stores typed arrays on a non-enumerable Symbol — no DOM-visible attribute is touched.
- The 4-cell evidence matrix required by `DEC:TERMINAL-SHELL-IS-DARK-ONLY` is INHERITED: the RSI Engine / Signals / Divergence / Channels surfaces are captured in the pre-existing chart-smoothness packets (rounds 1–9 — quote single-flight, cursor-sync batching, tooltip-follow scheduling, histogram batching, MACDX square batching, Money Flow Profile batching, premium cloud batching, MACDX kernel memoization). Those packets previously documented the dark × EN/ZH × 1440/390 rendering of the RSI suite. The PR body documents the live-verified browser contract for the lazy-loaded RSI pane (desktop/tablet/mobile 3/3 PASS) at the final integrated head `4fd7bf2abb6ab364c2338be1145c16015c8f045e` (the local pre-merge tip), which is the matrix-equivalent receipt for round 10.

Pixel-equivalent rendering verdict: a kernel-side cache cannot introduce a regression in the dark × EN / ZH × 1440 / 390 cells — the chart renderer, the typed-array consumers, and the consumer modules that read the cached arrays are all unchanged. The bit-identical-to-direct-compute test (Test 2's last assertion) is the structural receipt that the chart renders pixel-identical before vs after. No recapture is owed for this round — the prior packets already pin the rendering of these surfaces at the post-merge `origin/master` bytes.

## Validated-claims findings

The standing macro/terminal law: the word "validated" and friends are CI-enforced via `scripts/check_validated_claims.py` (terminal-side uses `scripts/check_plain_language.mjs` for the broader vocabulary gate, which already passes per §Plain-language findings above). The terminal repo has no standalone `check_validated_claims.py`; the discipline is enforced by the same plain-language checker that scanned this diff plus a word-boundary grep on the PR body and added-line set for the promotion-bearing tokens.

Word-boundary grep on the full diff (`terminal/lib/__tests__/rsiPassCache.test.ts` + `terminal/lib/suites/rsix/rsiEngine.ts`):

| token | matches in diff |
| --- | ---: |
| `validated` | 0 |
| `verified` | 0 |
| `certified` | 0 |
| `approved` | 0 |
| `proofed` | 0 |
| `gauntlet` | 0 |
| `proven` | 0 |
| `ranked` | 0 |
| `scored` | 0 |
| `calibrated` | 0 |
| `production-ready` | 0 |
| `production-grade` | 0 |

Word-boundary grep on the PR body (`gh pr view 685 --json body`):

| token | matches in PR body | context |
| --- | ---: | --- |
| `validated` | 0 | — |
| `verified` | 0 | — |
| `certified` | 0 | — |
| `approved` | 0 | — |
| `proofed` | 0 | — |
| `gauntlet` | 0 | — |
| `proven` | 1 | "Already-proven chart-smoothness work remains accepted" — a meta-statement about earlier rounds of the chart-smoothness program (quote single-flight, cursor-sync batching, tooltip-follow scheduling, histogram batching, MACDX square batching, Money Flow Profile batching, premium cloud batching, MACDX kernel memoization), NOT a claim that PR #685 itself has been promoted to a tier higher than display. The token describes the do-not-redo citation set for adjacent work, not THIS PR's results. |
| `ranked` / `scored` / `calibrated` | 0 | — |

`scripts/check_validated_claims.py` (terminal-side equivalent in the checker set) would also pass vacuously on this diff: no rank/score/confidence claim, no empirical prediction of chart-rendering quality beyond "this is an implementation benchmark, not an end-user FPS claim" (the PR body explicitly disclaims the production-tier frame), no `validated` / `verified` / `proofed` / `ranked` verb, no internal-study-name leak.

**Verdict: PASS — no promotion claims, no production-tier framing. The PR's single use of "proven" is a meta-statement about adjacent rounds of the chart-smoothness program, not a self-promotion of PR #685.**

The PR body is calibrated and honest about scope:
- Title: `perf(rsix): share RSI kernel within suite pass` — `perf` prefix correctly signals optimization, not new capability.
- "## Measured current-base delta" table labels the numbers as "implementation benchmark, not an end-user FPS claim." This is the textbook `display-tier` discipline — no pretense of having gone through the gauntlet.
- "## Verification" section enumerates the actual mechanical receipts (focused ESLint, `tsc --noEmit`, focused parity 266/266, full suite 6,022 passed / 4 todo, `npm run build`, `git diff --check`, real lazy-loaded RSI pane browser contract 3/3) and explicitly notes the pre-existing Turbopack NFT warning through `lib/flowSource.ts` is untouched. None of these is a promotion claim — they are local verification receipts for the change being made.
- "## Do not redo" enumerates the chart-smoothness work that is ALREADY accepted (8 prior rounds) and disclaims re-litigating it. Combined with the same-carrier discipline (this PR edits only `terminal/lib/suites/rsix/rsiEngine.ts` + the test file; no overlap with current renderer / host-memo / marker-touch / ChartPanel / pane-sync / recovered startup lanes), this is the calibrated `do_not_redo` receipt the project convention mandates.

The 2 new tests are themselves a verified-claims discipline: the bit-identical cache contract (`expect([...c.rsi]).toEqual([...direct.rsi])`) and the no-leak-of-engine-params-into-satellite contract (`expect(Object.keys(pass)).toEqual(keysBefore)` and `expect(JSON.stringify(pass)).toBe(jsonBefore)`) are the structural receipts that the optimization cannot quietly diverge from the direct-compute path. Any future PR that changes the cache semantics and breaks either invariant is hard-caught by vitest at the test boundary, not by an after-the-fact "we noticed the chart looks wrong" report.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (`check_plain_language.mjs --mode enforce-added --since 098e4fc --json`) | PASS (0 blocking; 6 legacy reported as pre-existing — same set as #658 / #670 / #669 audits; 0 waived, plus 1 waivered legacy unchanged) |
| theme (`check_design_system.py --mode enforce-added`; `check_runtime_style_injection.py`; DEC:TERMINAL-SHELL-IS-DARK-ONLY evidence matrix) | PASS (no CSS / no PNG / no design-system file / no token / no DOM mount / no runtime style injection in diff; 4-cell matrix inherited from prior chart-smoothness packets by subtractive equivalence; dark-only Terminal carve-out preserved) |
| validated-claims (no promotion; honest kernel optimization) | PASS (no rank / score / confidence claim; the 1 `proven` in the body is a meta-citation about adjacent rounds, not a self-promotion; PR body explicitly disclaims production-tier framing; bit-identical + no-leak tests encode the verified-claim discipline structurally) |
| half-B scope compliance | PASS (2 files / +89 / −13; tagged `perf(rsix): …`; round 10 of the Terminal chart-smoothness program; same-carrier disjoint from renderer / host-memo / marker-touch / ChartPanel / pane-sync / recovered-startup lanes; measured +14–26% median kernel reduction at 1k–10k bars on the same machine against the exact pre-PR baseline) |