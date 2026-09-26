# Design-system readability repair — 2026-09-26

**Scope:** existing design-system PR #7394; supporting evidence and bounded projection/consumer contract, not another design constitution. **State: candidate / R4_NATIVE_APPLIED_AND_VISUALLY_INSPECTED / NOT_DEPLOYED.** No production CSS, component renderer, score, data, permission or trade authority changes in this document.

The Chairman assigned this session to the shared design system while other sessions specialize in individual pages. The product should supply prepared intelligence and a useful next step without removing analytical depth. Content authority remains `docs/DESIGN_DOCTRINE.md`; visual/composition authority remains `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`; migration and acceptance remain `research/DESIGN_MIGRATION_FACTORY_V1.md` and the existing Reference Integrity Gate. The pending human-first amendment is #8041, inspected at `920c87a793efffa7993fdb156deaf10b2fadd671`; this record does not merge it or duplicate its decision.

**R3 historical reconciliation:** another session added the source-derived light
warning/up/down/link ink aliases to the same Paper file. Reuse the existing
`--mx-light-ink-warn=#7D5922`; do not execute the older create-token example while
that name exists. The rounded alias measures 6.317604:1 on white (5.580043:1 on
raised light; 5.945232:1 on the canvas). The 6.326019:1 figure below remains the
unrounded source-mixture calculation. At R3, node `13N-0` still used raw amber. R4 below supersedes that unapplied
consumer state; retain the original calculations as baseline evidence.

The existing contrast helper is now repaired in test-only commit
`fe7b900e4c28ba2d4a4d327bb996526f09019753`: whole-selector admission plus 13
regressions, not a new checker or palette. Tests-first RED and old-parser mutation
each produced 10 failed / 3 passed; repaired full-file qualification passed 100
tests against current-main and separately against the older branch theme.
Existing CI already invokes that same file. These are isolated source tests, not
whole-repository, browser, native-edit or human-comprehension acceptance.

## 1. What changes for a page author

A primitive is not complete because it has the right radius and palette. It must carry an understandable meaning, a data-state contract, an interaction/result contract and appropriate evidence.

| Existing primitive | At rest | On inspection | Completion/result requirement |
|---|---|---|---|
| Decision header | Subject and owned assessment; consequential limitation beside the claim | Supporting and conflicting evidence, clock and basis | User can identify the main read and useful continuation without reconstructing it from scattered tiles |
| Comparison row | Comparable values, units and the same stated period/baseline | Full series, constituent coverage and methodology | Missing or differently timed evidence cannot masquerade as a valid comparison |
| Decision row/card | Exact company/group identity and owner-issued state | Why this item matters, readiness versus leadership, evidence | Inspection returns to the originating selection/filter/position; no silent identity substitution |
| State panel | What is unavailable or changed, its consequence and a useful recovery | Detailed source/coverage information | Loading, true zero, filtered-empty, stale, partial, denied and failure stay distinct |
| Primary action | One visually prioritized verb and destination | Legitimate secondary actions remain reachable | Request, success and failure are different; a saved or active state requires the real owner result |
| Lens/disclosure | A meaningful opening label, not a vague 'More' or another introductory paragraph | The information promised by that label | Keyboard/touch opening, dismissal and return; no mandatory nested-overlay maze |

These are authoring checks for existing components, not a new component registry. An unfamiliar intended user should understand the subject, main assessment and next useful step in approximately four seconds. This is an orientation target, not a promise to understand a dossier instantly or a substitute for actual cold-reader evidence.

### Prepared defaults, not forced simplification

Start with a useful task state: the relevant comparison, prioritized changes or owner-ranked results. A user should not need to configure widgets or write an expert prompt to obtain the first useful answer. Preserve the complete population, advanced controls and direct full-research destination. Frequently used comparisons belong together rather than behind separate disclosures.

A title may supply the conclusion, a chart the decisive comparison, and an action the continuation. Do not add a subtitle, description and footer to every component simply because a template has room. Remove repeated explanation; never remove a consequential caveat, unit, denominator or time basis to satisfy a word budget. The budgets are ceilings, not quotas.

Illustrative copy patterns, **not live assessments**:

| Situation | Prepared first read | Useful continuation | Must remain visible |
|---|---|---|---|
| Index gains but weak participation | 'Index up. Breadth weak.' with a same-window index/equal-weight comparison | Inspect participating sectors | Partial coverage or incompatible observation periods |
| Strong business, no accepted entry | 'Strong business. Entry not ready.' only when the respective owners supply those states | Inspect the setup | Leadership does not grant entry authority |
| No current qualifying results | 'No setups qualify today.' only when the current complete source establishes a genuine zero | Review the next monitoring step | A source failure must never produce this sentence |
| Filters exclude available results | 'No matches for these filters.' | Clear the relevant filters | Keep the unfiltered population and active filters understandable |
| Coverage is behind | 'Latest update unavailable.' | Inspect the last confirmed evidence | Its observation time; do not present the last value as current |

Avoid customer copy such as 'runtime', 'hydration', 'admission', CI/PR identifiers or internal confidence enums. Keep that information in the existing engineering/evidence surface. Strong is not ready; fresh is not bullish; unknown is not neutral; locked identity is not missing data.

## 2. Baseline projection defect and bounded correction — R2/R3

Editable identity: Paper file `01M2WGNCX9475G79JRKJTCM08P`, system page `p-1-0`, light component atlas `126-0`. The R2-observed token hash was `5ae876bc` with 79 projected tokens; R3 additions are noted above. This hash and the bridge snapshot are **not** file revisions or writer leases.

Fresh native readback found text node **`13N-0`**, 'STALE', at **10px / weight 600**, bound to `var(--mx-light-warn)` = `#B9791A`. Its transparent ancestors `13M-0` and `13K-0` sit within white panel `13H-0`. The general text-safe and solid-label fill roles already present in the source theme are absent from the Paper projection.

The large 46px 'STRETCHED' node `12F-0` uses the same raw amber but is a different, large-text use. Do not darken the whole amber palette or change that hero as a side effect of repairing the small label.

### The three color uses are not interchangeable

| Use | Existing source role | Rule |
|---|---|---|
| Graphic mark or restrained tint | `--warn`, `--up`, `--down`, other semantic hues | A graphic/fill role is not automatically safe as small text |
| Text on a surface | `--ink-*`, or ordinary `--text` when a specific semantic pair fails | Measure the actual surface, including hue-tinted backgrounds |
| Solid control carrying a light label | `--fill-*` with the intended label color | Do not put white text on a raw hue just because a different pairing passed |

Source-derived light warning ink is `color-mix(in srgb, var(--warn) 62%, var(--text))`, resolving to **`rgb(125.34, 88.70, 34.36)`** on the inspected source. The raw amber remains unchanged.

| Surface | Raw amber as small text | Source warning ink as small text |
|---|---:|---:|
| White panel | 3.612765:1 — fail | 6.326019:1 — pass |
| Raised light panel | 3.190985:1 — fail | 5.587475:1 — pass |
| Light canvas | 3.399821:1 — fail | 5.953150:1 — pass |

The normal-text comparison uses the unrounded 4.5:1 threshold. These are computed opaque color-pair results, not a claim of Paper application, browser rendering, readability at every font size or full accessibility conformance.

### Prepared native label correction — do not execute without custody

First reconcile the single modifying owner of the **entire file across hosts**. During this continuation another M1 session performed `news-intelligence-paper-vnext-20260926-sol-001` / `rename_nodes` with APPLIED_RESPONSE_OBSERVED. This session did not modify the canvas or shared tokens. A separate page assignment does not remove that collision.

After lawful file custody, re-read the current source role, exact file identity, current tokens and target styles. The prepared additive role is a one-way projection of the existing source role, not a new brand palette:

```json
{
  "fileId": "01M2WGNCX9475G79JRKJTCM08P",
  "tokens": [{
    "type": "color",
    "name": "--mx-light-ink-warn",
    "value": "rgb(125.34, 88.70, 34.36)",
    "description": "Projection of templates/theme.css --ink-warn, light: 62% warn plus 38% text in sRGB. Text role; source owns the value. Re-measure changed source or backgrounds."
  }]
}
```

Use the actual guarded `create_tokens` schema only if the name is absent. Upstream allows duplicate names: absence must be checked explicitly. If an equivalent role already exists, reuse it; if it differs, reconcile its owner/value before writing. Do not create a duplicate or overwrite another session's token.

Then, as a separately reconciled guarded operation with a fresh snapshot:

```json
{
  "fileId": "01M2WGNCX9475G79JRKJTCM08P",
  "updates": [{
    "nodeIds": ["13N-0"],
    "styles": {"color": "var(--mx-light-ink-warn)"}
  }]
}
```

The payloads are documentation, not dispatched operations. A snapshot or operation ID must be obtained at execution, never copied from this record. Preserve the large hero, other pages and unrelated token roles. Capture the exact changed atlas after application, inspect the pixels, re-read the computed binding and measure its actual surface. Do not call the defect repaired until those results exist.

For buttons, project the existing `--fill-info` role and retain a real light-label pairing. Inspected source resolves dark fill-info to `rgb(58.24, 99.20, 153.60)` and light fill-info to `rgb(25.60, 60.80, 163.20)`. Target button node identities, state backgrounds and complete interaction matrix must be inspected before any patch. No button patch is implied here.

## 3. Wider measurement prevented a false blanket fix

The source-role audit evaluated eight roles, both themes, both languages and explicit surface combinations. The 9%/13% tint compositions below are **stress cases**, not proof those exact combinations appear in production.

| Pair family | Passed / examined | Important limit |
|---|---:|---|
| Raw semantic hues as normal text on three flat surfaces | 62 / 96 | Raw hue is not a general text role |
| Text-grade inks on three flat surfaces | 94 / 96 | Dark `--ink-act` on `--panel2` fails in both languages at 4.250667:1 |
| White labels on existing solid-fill roles | 32 / 32 | Minimum measured ratio 5.109280:1; intended white label only |
| Text-grade ink on its own 9%/13% hue tint over panel | 58 / 64 | Six failures; an ink name alone is not a universal guarantee |

The six tint failures are dark down/red at 13% in EN and its up/red counterpart in ZH (4.328310:1), plus dark act at 9% (4.194758:1) and 13% (3.997252:1) in both languages.

**Consumer disposition:** do not spread the failing combinations into new primitives. A state panel can use ordinary primary text for its label while retaining the semantic icon/rail and explicit state word. That preserves meaning without inventing a new red or changing a shared palette without a source-owned design review. Any proposed shared ink retune is a separate source/consumer change requiring current custody, affected-consumer measurement and visual review; this docs-only wave does not make it.

No blanket light/dark/locale pass is asserted. Direction swaps with the existing language convention; health/severity and freshness must not follow that swap. The role calculations separately checked those invariants.

## 4. Evidence method and falsifiers

Inspected source: Macro `bd23cfbd3f192389166bef37e490003fadd6d453`.

- `templates/theme.css`: blob `41f0c3bdea3979faf4a57f2a98e31a4df54a5973`, SHA256 `d58d35e93758ada2123553f88ea6652e66ec11c116b031679a82b80951f8a478`.
- Existing `tests/test_prophet_verb_ink_contrast.py`: blob `6d6a15bb43e43e0b14e271ff93cd4ff80c331132`.
- Existing `templates/_prophet_card.html.j2`: blob `713e0e49b037e9f2b8c2a716265bff6f900a2c9e`.
- Corrected 288-pair calculation output: SHA256 `c655cf379429eed4b2f8de26967be3cacbeb3cc1a729f8eb7da0bb6daa5a0d8c`.

The calculation reuses the existing color-expression resolver, expands source percentage variables, and selects only top-level `:root` and exact html theme/language selectors. Descendant component remaps and conditional nested rules are not global baseline tokens. The calculation uses the sRGB transfer threshold 0.04045 and does not round a failure upward.

Two diagnostic errors were caught before using the result as a repair contract. First, the helper did not expand `--fill-mix`; the source percentage must be resolved explicitly. Second, the helper's permissive selector matcher admitted `html[data-lang="zh"] .rrx` and `html[data-lang="zh"] :is(.igx, .igs)` as global overrides. A negative-control fixture with descendant and nested-media overrides proved the scope error; exact top-level filtering corrected it. The earlier report `8ae96f8f7abaf273316e14d996e957c5932f6c62f93387b36b11f22048b69863` is superseded and must not be used. At that R2 boundary no repository parser or shared test implementation had changed; the R3 repair above supersedes that historical state.

At the R2 baseline the **then-unchanged Prophet test file** was run against exact extracted source with pytest's project conftest and automatic plugins disabled: **87 passed, exit 0**. This is a targeted source test, not a full repository test or validation of a new Paper effect.

Falsifiers before rollout: a changed source blob/role or target background; a different target binding; a duplicate projected token; a locale-dependent health color; a tinted/focus/hover pairing below its applicable threshold; or an actual browser result disagreeing with the arithmetic. Any of these invalidates the affected projection/consumer claim rather than being averaged into a pass.

Reference basis: W3C WCAG 2.2, Understanding SC 1.4.3 (Contrast Minimum), SC 2.5.8 (Target Size Minimum) and SC 2.5.5 (Target Size Enhanced). Normal text requires 4.5:1 and large text 3:1 subject to the criteria's exceptions. A comfortable 44px target is our product preference; the AA minimum is 24 CSS pixels subject to documented exceptions. A contrast result does not prove target size, readability, cognitive accessibility or overall conformance.

## 5. Carry this into the existing migration packet

Use the existing packet fields rather than another checklist store:

- **Field 4:** intended first reading order; subject/main assessment/useful next action; visible consequential limitation. Do not demand a subtitle or three new boxes.
- **Field 6:** every demotion's actual destination and whether the normal task still works without extra reconstruction. Preserve direct expert access.
- **Field 3B:** source role and projected role separately; actual foreground/background/state pairs; neutral-label disposition for unsupported combinations.
- **Field 3C:** the interaction state changes that can change readability or meaning, not only a resting screenshot.
- **Field 11:** technical, design, cold-reader and real-journey evidence recorded separately, including unperformed evidence.
- **Field 12:** intended task completes with real result feedback, deeper/adverse evidence access and context-preserving return. No saved/active state from a mere request.

The primary task can be an investigation, comparison, monitoring setup or honest decision to wait. It does not require a newly invented trade recommendation. Long analytical content uses normal document scrolling; purposeful chart-workspace panes retain their existing archetype. Sticky controls must not obscure focused content or the primary assessment.

## 6. Remaining delivery boundary

Procedure pin: Mastermind protected `763ec8f920177fdf48b18df1b8e37b61ab482ef0`, compatible Skillpack 1.0.1/bootstrap 1. Existing source carrier is #7394 / `sol/design-system-editable-reference-20260919`; original semantic head `bc01b258609cb4fcab0a3cf8089fdc5b7e21f803` remains historical evidence, not a review of this addition.

Completed R4 native slice: existing warning-role binding, eight neutral-button state specimens and working-template synchronization, with exact after-images/JSX and readbacks below. Remaining: current-head source review/checks, broader component/state/locale qualification, filled-control cases, real implementation fidelity and intended-user journey/comprehension proof. This changes none of the #7394/#8041/#7630 release holds. No source merge, live UI change, specialist consumption, worker START or automatic wake is claimed.


## 7. R4 — applied native system slice

M1, guarded Paper v4, file `01M2WGNCX9475G79JRKJTCM08P`, system page `p-1-0`.

**Warning label:** `13N-0` now binds `var(--mx-light-ink-warn)`, the existing
`#7D5922` alias. Its white-panel arithmetic is **6.317604:1**, versus
**3.612765:1** before. Readback kept large hero `12F-0` and parent panel unchanged.
No token was created or overwritten.

**Neutral buttons:** eight existing default/hover/focus/disabled specimens on
`ZJ-0` and `126-0` now use `minHeight/minWidth: var(--sp-8)` (44px), border-box and
centered content. Their original colors remain. Enabled default/hover/focus
text/background calculations are **11.564708:1** dark and **13.796661:1** light.
Disabled opacity is deliberately retained and excluded from that enabled-text
claim. These are static intended states, not runtime, keyboard, tap-target or
focus-ring certification. No filled-button role was added unnecessarily.

**Working authoring template:** existing `19T-0` now leads with **“Make the answer
obvious. Keep the depth.”** An explicitly illustrative, non-live example precedes
the fields for intended reader, useful default, material caveat, primary step and
direct full-research route. Existing sections also record earned copy, actual
information destinations, consumer pairs, four distinct proof types, and real
result/return behavior. Stop/reference qualifications were moved to the handoff
footer, not removed. This is the existing repository guidance's working projection,
not a second packet, component registry or approval store.

Structure remained **870 nodes / 10 artboards / 83 tokens**. No new board, page,
palette, component identity or specialist-page edit. Figma was not accessed;
historical reference identities were preserved. All three final images were
opened and visually examined; no visible clipping or overlap was found in the
touched areas. Author inspection is not independent acceptance or a user study.

### Immutable evidence attachments

Files live under `mockups/refs/design_system/paper-readability-r4-20260926/`:

| Native target | Image | SHA256 |
|---|---|---|
| `126-0` Light atlas | `atlas-light.jpg` | `b99086a6eb20124ab939c11385d4377c50f5b540b1d6e59b70c698f8a606c27d` |
| `ZJ-0` Dark atlas | `atlas-dark.jpg` | `f713c3241d2c78463afa2c06a0cfb38573e73619b789853d11519434b674eded` |
| `19T-0` Working template | `prepared-answer-template.jpg` | `432d38222b1e1b8cfc526e79527af16eedea0dca7c954fca19f0e63a73b2b2d3` |

Adjacent `.jsx` files are actual Paper exports, implementation input only.
`native-receipts.json`, before/after bindings, control styles, template text and
pair calculations are ordinary evidence attachments, not an approval manifest.

Four separately reconciled operations returned `APPLIED_RESPONSE_OBSERVED`:
`design-system-r4-warning-binding-20260926-001`,
`design-system-r4-prepared-template-text-20260926-001`,
`design-system-r4-controls-template-style-20260926-001`, and
`design-system-r4-finish-own-nodes-20260926-001`.
All sixteen template texts and eight minimum-size bindings were read back.
The finish action released only the **27 named touched nodes**, not all working
indicators. No unresolved effect remains from these operations.

### Recovery and next action

Protected source pin: `Mastermind@a31f49f4056943124cc0e7e42349e46feee444c7`;
required procedure/runtime blobs matched the previous verified revision. Recovery
reconciled earlier named phase-ending receipts and the latest M1 Forex modifier's
observed finish and final verification. No later native modifier appeared in the
retained M1 history; no guarded edit process was executing on M1 or the exposed
Studio host. That supported a short foreground action under the current assignment,
not a timeout-based lease expiry, universal-lock claim or live-writer displacement.
Pre-effect/result record: #7394 comment `5849865112`.

No denied action, uncertain effect, Figma route or specialist artifact was replayed.
Next native work requires fresh custody and exact-target checks. Historical
create-token and label-patch examples above must **not** be replayed against the
now-corrected target. R4 did not rerun or widen R3's 100-test result or R2's
288-pair campaign. Remaining work is broader component and filled-control states,
locale/mobile parity, independent review, real journeys and human comprehension;
production implementation and release remain separate obligations.
