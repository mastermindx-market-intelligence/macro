# Terminal PR #713 — corrected historical audit record

Historical audit date: **2026-09-22**. Records correction: **2026-11-05 UTC**.

This account applies the [#7731 preservation ruling](https://github.com/mastermindx-market-intelligence/macro/pull/7731#pullrequestreview-5325849962) to the report already protected through #7740. It retains the useful source findings and corrects evidence overclaims throughout. The complete original #7731, #7739 and protected reports remain available at the immutable links below; none is presented as a byte-identical duplicate of another.

**Status: historical source record, not a new product audit or current production acceptance.** Terminal #713's source merge is verified. Historical test, browser, validator and deployment statements remain attributed to their original receipts. No such operation was rerun for this correction. A past `BUILT_NOT_PROVEN` statement describes its dated release boundary; it neither reverses the proven merge nor establishes today's production state.

## Verified target identity and scope

| Field | Verified immutable source |
|---|---|
| Repository / PR | [mastermindx-market-intelligence/mastermind-terminal #713](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/713) |
| Title | feat(chart): upgrade searchable study management and touch access |
| Final PR source head | `8114f2ee9615717d6223219a894dc10b619965b1` |
| Protected merge | [`3b488ce96f2633613e1bd9d873e96693aef20314`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/3b488ce96f2633613e1bd9d873e96693aef20314), **one-parent squash** |
| Sole protected parent | `7f98bfd9868a7a71dfd7a0b90c482793dc13f1b6` |
| Merged at | **2026-09-22 10:40:03 UTC** |
| Earlier feature commit | `bb5097b4f6cdfebcd39df55fb1196f74689c7778`, parent `3b0340bf831f3112575129f3c2f649ced0e00e78`; three later source-branch integrations lead to the final source head |
| Source branch | `claude/terminal-chart-layers-ux-20260922` |
| Complete actual-parent delta | **13 paths, +394/-118**, including **seven PNGs** |

The old protected metadata labeled `8114f2ee` as the protected merge; it is the final PR source head. The earlier semantic feature commit, final source head, historical fixture base and protected merge have different roles. The #7739 report's description of `8114f2ee` as the squash commit is also corrected here.

The complete delta comprises:

| Path / group | Actual-parent delta |
|---|---|
| `terminal/components/ChartObjectTree.tsx` | +107/-118 |
| `terminal/components/ChartObjectTree.module.css` | New, +53/-0 |
| `terminal/lib/__tests__/chartObjectTree.test.tsx` | New, +66/-0 |
| `terminal/e2e/chart-object-tree.spec.ts` | New, +88/-0 |
| `docs/TERMINAL_CHART_LAYERS_UX_2026-09-22.md` | New, +34/-0 |
| `terminal/docs/pr-crops/chart-layers-ux-20260922/EVIDENCE.json` | New, +46/-0 |
| Seven PNGs under the same crop directory | One pre-edit baseline plus six desktop/tablet/mobile EN/ZH crops; binary paths are included in the 13-path total |

The inspected component, CSS, test and browser-source blobs at the protected merge are respectively `49a333e9b5b63009cbec19ea9c3dfb871f5f4b76`, `c1d282504430f27dd88c1e17a78fc5bc2d546584`, `2656b68f546ea547e9359dcc96c60dccd35de2ff` and `76ac47064877144905e065223ebae6ca5a0feab6`.

## Retained source findings

The source change adds search and touch access to the existing chart Object Tree. It does not establish a new indicator-state owner, chart renderer, backend, mathematical signal or translation system.

- **Search remains view state.** The component's local query filters supplied labels and tags, including hidden studies. It uses the existing `onEye`, `onRemove` and `onClose` callbacks for mutations; filtering itself does not mutate the study collection.
- **Focus and empty states are explicit in source.** Search receives focus on open. After removal, focus is directed to a surviving action or the search field. Escape clears a nonempty filter before closing. No-match and no-study states use distinct existing translation keys; a clear-filter action remains available.
- **Removal ownership stays with the caller.** `OTEntry.noRemove` suppresses an entry's remove button. The component has a separate main-series summary without a remove action. The unit source tests a supplied `locked` seed with `noRemove: true`; that seed does **not** establish every TerminalShell assignment, including `_oracle` or comparison entries. No broad shell-ownership audit is claimed.
- **Translated controls keep their existing owner.** Action labels and empty-state copy use `useT`; labels/tags come from the existing caller. Historical reports' string-count and EN/ZH parity assertions remain attributed; this correction does not run a new full LEX census.
- **Narrow layout uses the same DOM/component instance.** Source feature-detects the native manual Popover API, promotes the existing section at widths up to 860px, responds to media changes, and removes the listener/popover state on cleanup. The source contains no portal or second component instance for that path.
- **Legacy-browser fallback remains unproven.** Feature detection and local `z-index:35` do not establish usable fallback behavior when native Popover is unavailable. The historical receipt's claimed Chromium coverage is not cross-browser acceptance, and an untested path is not automatically a demonstrated defect.

These are readings of the immutable source and test definitions, not a fresh interactive verification or claim about deployed behavior.

## Historical fixture evidence and its limits

The [original evidence manifest](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3b488ce96f2633613e1bd9d873e96693aef20314/terminal/docs/pr-crops/chart-layers-ux-20260922/EVIDENCE.json), blob `80a2f264eb2b30f19cfd2c2c60e3daebaeab8b33`, explicitly records:

- `fixture: true` and `productionProof: false`.
- Historical fixture base `3b0340bf831f3112575129f3c2f649ced0e00e78`, capturedAt `2026-09-22T03:09:04.967361+00:00`.
- Declared theme **Terminal dark-only**; EN/ZH crops at **1440x900, 820x1180 and 390x844**.
- Four source-file SHA256 entries, seven crop SHA256 entries, original commands and author-reported results.

Root recomputed the four immutable source-file SHA256 digests and matched all four manifest entries. This establishes that identity relationship only. The PNG digests were **not** recomputed and the images were not recaptured or newly visually accepted. Image hashes identify artifacts; they do not prove focus behavior, state mutation, clipping, motion suppression, browser compatibility or live data.

| Historical manifest field | Reported result, not rerun |
|---|---|
| unit | 379 files; 6088 passed; 4 existing todo |
| component | 7 passed |
| browser | 14 passed; 10 intentional viewport skips; 0 failed; retries 0 |
| layerCases | 7 passed; all target centers reachable; canonical preferences changed by real controls |
| typecheck / scopedLint | PASS / PASS |
| mutation | Initial mobile clipping failed target-center hit test; native top-layer repair passed |

The historical browser command covers **both** the Object Tree and chart-view-reset specs on desktop/tablet/mobile projects. Its combined 14-pass total is not seven viewport definitions or fourteen Object Tree test definitions. The retained Object Tree source has three Playwright test definitions; its responsive round-trip test skips non-desktop projects. The unit source has seven `it` definitions. These static counts do not independently establish execution.

The [browser-test source](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3b488ce96f2633613e1bd9d873e96693aef20314/terminal/e2e/chart-object-tree.spec.ts) contains checks for:

1. Search focus, finding a study, hide/show/remove state, localStorage preference changes, Escape ordering and horizontal overflow.
2. Chinese heading/search/action visibility; on non-desktop projects, control viewport reachability, center-point hit testing and minimum width/height.
3. A desktop-to-mobile-to-desktop filter round trip in the same panel, including native-popover state and preserved query/row count.

Reading these checks is not a new execution. In particular, the source sets `reducedMotion: "reduce"` and then captures a screenshot; it does **not** explicitly assert computed animation or transition suppression. The historical mutation and RED/GREEN claims remain author-reported receipts, not a regression reproduced by this records correction.

## Plain-language findings: keep scan scopes distinct

The reports describe different historical scans and should not be collapsed into one estate-wide green result:

| Report / quoted scope | Historical reported counts | Limit |
|---|---|---|
| Original #7731 sparse-worktree scan | 2 scanned files; 0 blocking, 0 legacy, 0 waived, 0 nulls | The report names the sparse checkout and its missing paths. It is not a 252-file full-census result. |
| Original #7739 full-census report | 252 scanned files; 0 blocking, 6 legacy, 0 waived, 0 nulls | The legacy entries are reported outside the changed component; no fresh census verifies their present state. |
| Protected #7740 report | 252 scanned files; embedded JSON says 0 blocking, 6 legacy, **1 waived**, 0 nulls | Its heading says 0 waived while its embedded JSON/table says 1. This internal discrepancy is preserved in the immutable original and not silently harmonized. |

The sparse report describes fetching the missing i18n source separately for its translation assessment. Its quoted command, scan result, claimed reproduction and translation findings remain attributed evidence. The historical 252-file reports and their six legacy findings are also attributed; this correction does not certify the current vocabulary overlay or rerun the guard.

The retained component source uses existing translation keys for its controls and contains distinct no-match/no-study states. Those useful source findings are retained without adopting blanket statements that every possible caller-supplied label or current product surface has been audited.

## Theme, touch and accessibility findings

The audited change **does alter a Terminal visual surface**: a rewritten component, new CSS module, search, focus treatment and responsive side sheet. Reusing tokens or adding no global palette does not make visual review structurally inapplicable. The manifest's dark-only contract is a dated statement of that candidate's scope; this record does not determine today's design law.

Source reuses existing panel/text/brand/line/danger/font tokens, with a local shadow `rgb(0 0 0 / .24)`, local `z-index:35` and data-driven per-study icon color. There is no new theme-token file or light-mode branch in this target delta. These are source observations, not a rendered theme acceptance.

The CSS specifies 44px action dimensions on narrow/coarse-pointer layouts, a 16px touch input font, safe-area insets, contained overscroll, wrapping names, visible-focus styles and a reduced-motion override. The browser source contains selected control-dimension and reachability assertions. Neither CSS declarations, screenshots nor digests alone establish universal accessibility conformance, iOS behavior or computed motion suppression; no such fresh determination is made.

**Optional future design note:** shadow-token or touch-floor consolidation may be considered only as part of a warranted future change across multiple surfaces. This historical note creates no standalone tokenization task, fallback implementation, new palette or product work.

## Validated-claims scope

The historical reports cite Macro's `check_validated_claims.py` while also stating that its scanned paths exclude Terminal UI. An absent MISS row outside that checker's coverage **cannot establish a Terminal PASS**. The Macro check's unchanged behavior and the target's absence from its input set are coverage limits, not positive validation.

The reports' scoped copy assessments, historical anti-promotion statements and reported absence of specific terms remain attributed conclusions. Disclaimers do not themselves prove correctness or waive required tests or public proof. This chart-management source does not introduce a rank, admission, sizing, execution or trading authority; the archived evidence does not grant one.

## Preserved original records and source custody

The following complete reports remain distinct immutable evidence. This corrected account replaces the misleading active summary at the existing path; it does not embed another full narrative or claim the originals were identical.

| Historical record | Immutable full report | Original blob |
|---|---|---|
| Protected #7740 edition, merged 2026-09-22 21:31:45 UTC | [Full protected report at 0e370dc3](https://github.com/mastermindx-market-intelligence/macro/blob/0e370dc3a3d61e53f92cde6407dee6a9959fb6d0/orch/audits/mastermind-terminal_PR-713.mm.md) | `e86927e4af40941827c572c2e92163133786947e` |
| Original #7731 edition | [Full report at cced4165](https://github.com/mastermindx-market-intelligence/macro/blob/cced4165af78388dd4038c36099dce1a0c22bdfc/orch/audits/mastermind-terminal_PR-713.mm.md) | `07713d37234165dfe5e9e88b5525a1369b012fa9` |
| Original #7739 edition, closed unmerged | [Full report at aa516ddb](https://github.com/mastermindx-market-intelligence/macro/blob/aa516ddbbcddb9fa337a07b9431768713f0b0545/orch/audits/mastermind-terminal_PR-713.mm.md) | `6bf57a39cf767aa66c595f6529bb60def54041b5` |

At correction intake, the protected payload at Macro base `b3134cb2ad3b594c129fd5c6db3f294cf40bfba6` was byte-identical to the #7740 merge. Root re-read both original reports and verified their blob identities; #7739's existing branch still pointed to `aa516ddbbcddb9fa337a07b9431768713f0b0545`. Its 2026 cleanup statement is attributed to its body and is not a current global host/process census.

The historical reports use qwen-auditor-style labels. Their source commits and labels do not establish that an actual qwen worker executed, and their cited older Skillpack pins or IDLE-mode instructions are dated provenance, not current operating law.

The #7739 original dependency-install/proof-refusal record remains in its PR history; it is not silently cleared by this correction. Its closed request, no-force/no-delete boundaries, original report, branch and history remain intact. This records carrier does not resolve unrelated holds, unknown effects, source-workspace custody or live acceptance.

## Result and remaining boundaries

The correction preserves the useful union: searchable study management, existing mutation callbacks, focus retention, distinct empty states, translated controls, touch access, source-owned removal protection, explicit fixture limits and unproven legacy-browser fallback. It corrects identities, scan scopes, visual/checker coverage and unsupported evidence claims in the retained account.

This is a **records correction only**. No new blanket product PASS is issued. Any subsequent source release, deployment or public verification must use its actual current carrier and authority. Historical related-PR notes about #701/#705, #707 and #702 remain in the original reports and do not reassign their work. The parent charting mission's current completion is not adjudicated here.
