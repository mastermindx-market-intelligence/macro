# D08B — Levels unknown-regime integration packet

**Status: PROPOSED_NOT_APPLIED / NOT_RUNTIME_VERIFIED.** This packet is a one-file display patch for D08 and the established Levels integrator. It has not been applied to the managed Mac, a repository checkout, GitHub, or Paper. No build, component test, browser run, screenshot, PR transition, or deployment was performed by this task.

Prepared 2026-11-05 UTC. Protected Mastermind pin reused from the parent session: `70187bb1660e8a7c3038271bb9f8924b5e525cb0`. All original release holds remain.

## Decision and exact ownership boundary

An existing `levels.v1` regime object whose `label` is null must display **Unknown / 未知** with neutral ribbon styling. Only the exact labels `sticky` and `slippery` receive their existing classified copy and sign colors.

The proposal changes only `terminal/components/levels/LevelsView.tsx` at the incumbent #1248 source below. It leaves the regime's source-authored ribbon, all map and rail geometry, exact prices, node semantics, calculations, scores, sources, clocks, selection, routes, and read lifecycle untouched. It introduces no economic regime or producer method.

#1248 overlaps this file. That is an integration boundary, **not proof of an active writer, lease, or exclusive custody**. D08 must establish the current integrator and base before applying. This child does not take over the file, claim a lease, or open another PR. No D08C or D08D route, parser, contract-selection, flow, or chain component is touched.

## Exact source bindings

| Role | Immutable reference | LevelsView Git blob |
| --- | --- | --- |
| Patch base: incumbent [Terminal #1248](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1248) | `98ffa891116ccc9e6be58a64148dbe45591e6ce8` | `03211be2aa72b3d602f20aa4f495fb84e129c7b3` |
| Read-only comparison: D08B [Terminal #1266](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1266) | `5903c07acf867366659cec689e6547b08c00ee87` | `430a2b84a1a78edffd68f522fa56e22e3d2c2ca8` |
| Proposed result, if applied to the exact patch base | Local proposal only | `539e4099c8d06780967b40b77f9377f0a2dc4414` |

The exact path is [terminal/components/levels/LevelsView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/98ffa891116ccc9e6be58a64148dbe45591e6ce8/terminal/components/levels/LevelsView.tsx). The two original source copies in `reference/` have been byte-checked against their Git blob identities. #1248 was observed open on branch `sol/web-options-workspace-surface-flow-ux-20261103-c3`; its lifecycle state does not authorize this packet to change it.

The parent independently inspected Paper B14, node `1QGP-0`, in Terminal file `01M3NSZGE8JWN2EZCSF0DT05RM`, and reported that a null regime is explicitly **Unknown**. This child relies on that attributed design observation and made no Paper call or edit.

## What the actual source establishes

The consumer declares `regime` itself nullable and declares `regime.label` as `"sticky" | "slippery" | null`. The current render derives only `isSticky = regime?.label === "sticky"`, then uses a two-way ternary for the label, left border, label color, and tag border. Consequently a present regime with `label:null` inherits Slippery text and all slippery colors. This defect is present in both bound source copies.

The file already distinguishes sign-unknown nodes: `nodeColor` returns `palette.neutralVar` for a null node sticky flag. Both normal and colorblind palettes define this neutral token as `var(--text-2)`. The patch reuses that palette for the unknown ribbon and the existing `var(--line)` outline token. Known sticky and slippery color expressions remain exactly the same.

The file already imports and uses the bilingual [pick helper](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/98ffa891116ccc9e6be58a64148dbe45591e6ce8/terminal/lib/finFormat.ts), whose signature is `pick(zh, en, cn)`. The shared [i18n lexicon](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/98ffa891116ccc9e6be58a64148dbe45591e6ce8/terminal/lib/i18n.tsx) contains the existing `lvSticky` and `lvSlippery` translations, but no Levels-specific Unknown key. Unrelated origin/authentication Unknown keys would import the wrong domain. The proposal therefore uses the already-imported helper for `Unknown / 未知`, leaving shared i18n ownership unchanged.

## Patch

Apply only after integration ownership and the current blob are established.

- [levels-unknown-regime.patch](levels-unknown-regime.patch): two hunks, one file, 10 inserted lines and 4 removed lines.
- [LevelsView.proposed.tsx](LevelsView.proposed.tsx): complete proposed file for inspection.
- [reference/LevelsView.owner.tsx](reference/LevelsView.owner.tsx): exact incumbent patch base.
- [reference/LevelsView.d08b.tsx](reference/LevelsView.d08b.tsx): exact D08B comparison source.
- [source-binding.json](source-binding.json): machine-readable source and artifact bindings.

The only new decisions are:

```tsx
const isSlippery = regime?.label === "slippery";
const regimeColor = isSticky ? palette.stickyVar
  : isSlippery ? palette.slipperyVar : palette.neutralVar;
const regimeBorderColor = isSticky ? `rgba(${palette.stickyRGB},0.4)`
  : isSlippery ? `rgba(${palette.slipperyRGB},0.4)` : "var(--line)";
```

The label follows the same exact known-value branches and otherwise uses `pick(lang === "zh", "Unknown", "未知")`. No truthy/falsy classification, case normalization, sign inference, gamma threshold, score conversion, or fabricated economic meaning is added.

A null or absent regime object continues to render no regime ribbon because the existing `{regime && (...)}` gate is unchanged. Unknown is the presentation of an unclassified **present** regime, not a replacement for load error, missing map, or absent regime states.

## Source, method, and backend contract

The existing board reads `/api/flow?f=levels:{ROOT}` through shared `flowGetResult`. Its expected schema is `levels.v1`. Visibility-based polling, root clearing, sequence fencing, manual retry, and stale-read treatment are untouched.

The bound [source tests](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/98ffa891116ccc9e6be58a64148dbe45591e6ce8/terminal/lib/__tests__/levelsSource.test.ts) identify the backend `/api/hub/levels/SPY`, public R2 key `levels/SPY.json`, root validation, and no cross-root fixture substitution. The bound [fixture](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/98ffa891116ccc9e6be58a64148dbe45591e6ce8/terminal/public/data/levels_fixture.json) supplies a SPY `levels.v1` map through `FLOW_FIXTURE=1`. It currently contains a sticky example; derive isolated variants for checks instead of changing production data or treating that example as null-state proof.

Dealer-sign convention remains an assumption; open interest remains a daily snapshot. Neither the number nor the sign of `net_gamma` is used to fill a missing label. Node sticky flags, brightness, weights, confluence, voids, flip, all role labels, spot markers, exact-price tick positions and label-collision geometry remain unchanged. Source schema, as-of, convention and note are retained verbatim. The existing stale badge still uses ET calendar days; this patch does not recast it as exchange-session age.

### Safety and remaining uncertainty

No source-contract or method reason was found that makes this narrow correction unsafe: null is explicitly supported by the consumer type, and the fix removes an unsupported inference. This is a source review conclusion, not runtime validation.

The producer's role/brightness formulas and full producer classification logic were not re-audited. They are unnecessary to the exact-value display decision and remain outside this patch's claims. The source comment references `engine/levels_engine.py`; this packet does not assert that its current implementation or location was independently inspected.

The existing `levelsFor` reader casts accepted objects without complete structural validation. An omitted, empty, or unsupported runtime label therefore receives Unknown defensively, but the patch does not certify that malformed payload as schema-valid. A malformed ribbon or malformed node payload remains the source owner's validation concern. Do not add another parser or feed reader while integrating this fix.

The source-authored `regime.ribbon` remains untouched. If upstream publishes a missing label alongside prose asserting Sticky or Slippery, that inconsistency must be recorded and resolved by the producer/source owner; this patch does not rewrite source evidence or infer which field is correct.

## Focused integration and acceptance

These are **instructions for future verification**, not checks already passed.

1. Read the current owner PR head and exact LevelsView blob. If the file still has blob `03211be2aa72b3d602f20aa4f495fb84e129c7b3`, inspect and apply the patch in the established owner checkout. If it drifted, inspect the changed region and integrate the same narrow rule manually. Do not blindly apply it to D08B's different blob, reset another writer, force a checkout, or create a competing carrier.
2. Review the diff for the two display-only hunks. Confirm that JSX structure, ribbon source text, nullable-regime gate and all unrelated calculations remain unchanged.
3. Use the existing [Levels failure-state suite](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/98ffa891116ccc9e6be58a64148dbe45591e6ce8/terminal/lib/__tests__/levelsLoadFailureState.test.tsx) as the read-path seam: it exercises actual `flowClientCache` with controlled `/api/flow` responses and derives data from the committed fixture. Add focused rendered-ribbon coverage there or an adjacent suite. Keep variants isolated from the fixture baseline.
4. Give each variant a unique source ribbon sentinel and scope assertions to its containing ribbon. The board's permanent legend legitimately includes Sticky and Slippery; a whole-page assertion that “Slippery never appears” would be wrong.
5. In the owner's terminal package, run the focused new test plus `lib/__tests__/levelsLoadFailureState.test.tsx`, `lib/__tests__/levelsLabels.test.ts` and `lib/__tests__/levelsSource.test.ts` using the established `npm test -- ...`/Vitest runner. Run the owner's existing compilation/typecheck gate. Do not silently count this packet's static inspection as those checks.
6. Verify the real local browser route `?tab=levels&symbol=SPY`, using the existing fixture/interception seam. The bound [Levels navigation helper](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/98ffa891116ccc9e6be58a64148dbe45591e6ce8/terminal/components/levels/levelsNavigation.ts) reads exactly one validated `symbol` value; preserve the owner’s current canonical route if its parser has changed. Inspect the following cases and retain actual browser evidence.

| Case | Expected rendered ribbon and retained behavior |
| --- | --- |
| Exact `sticky` | Existing localized Sticky text, sticky left border/text, existing translucent sticky tag border. |
| Exact `slippery` | Existing localized Slippery text, slippery left border/text, existing translucent slippery tag border. |
| `label:null` | Unknown / 未知; neutral left border and text; neutral outline; source ribbon preserved. |
| Omitted, empty, unsupported or differently cased runtime label | Defensive Unknown, never inferred Sticky or Slippery; record malformed-schema status separately. |
| Null label with positive, negative, zero or null net gamma | Same Unknown display in every case; no numeric inference. |
| Null or missing regime object | Existing no-ribbon behavior. Existing map, loading, absence and error behavior unchanged. |
| Normal and blue/orange palettes; dark and light themes | Known colors retain their existing meaning. Unknown remains explicitly labeled and neutral; inspect actual contrast. |
| English and Chinese | Correct copy; source-provided ribbon retains its original text. |
| 320px, 390px and desktop | Ribbon badge/prose remain readable; verify no new clipping and no hidden source clocks or research controls. This patch does not claim to repair pre-existing global phone layout defects. |
| Dense map, repeated clusters, voids, selected node, root switch, failed refresh | Exact prices, roles, geometry, selected details, source clocks and existing failure-state distinctions remain unchanged. |

The badge is a static text label; it adds no focus target or keyboard interaction. It must communicate Unknown without depending on neutral color. Preserve existing keyboard navigation and reduced-motion behavior. Regressions in layout, calculations or source fidelity must be fixed or explicitly returned as unverified before claiming acceptance.

## Evidence status and return boundary

**Completed here:** immutable-source reads, exact local reference blob checks, review of the nullable label and all four affected ribbon properties, existing localization/palette/read-path inspection, and generation of the bound proposal.

**Not completed here:** source application, compilation, component tests, browser paths, responsive screenshots, Paper edits, owner integration acceptance, merge or production proof. No evidence is invented for those stages.

Patch SHA-256: `1be5efe068ba19f76ce60ef86468af7bc961d539593b72b530ef8901a471dc44`.

Proposed source SHA-256: `4bdb4f87367aec6a1d63cf831cfe2bb6edda4ce563bb4778445d98c794c63075`.

The exact next action is D08/coordinator custody confirmation and owner integration against a freshly read blob, followed by the focused verification above. This packet does not request release-state changes and preserves every existing merge, Ready, un-draft, enqueue, held-relabel, uncertain-operation and deployment hold.
