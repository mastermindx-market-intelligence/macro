# Prophet shared-shell design migration — final handoff

Observed: 2026-11-10 13:36:00 UTC

## Outcome and exact completion boundary

The eligible Prophet screen families in Paper have been migrated to the existing MastermindX shared shell. **193 screen boards received shell changes**, and **22 embedded phone examples across 11 additional boards** received the compact shared header. The central integration guide was replaced, one review guide was added, and the file now has **19 pages and 278 top-level boards**, compared with 17 pages and 277 boards at entry.

The current-root and current-page map reconciles all 277 original boards. No mapped root is missing and no migrated root is on an unexpected page. All 281 mutation receipts from this session returned `APPLIED_RESPONSE_OBSERVED`; the observed empty-frame no-op and ineffective position requests were reconciled before the alternative page layout was applied. This session did not create a new uncertain effect.

**Literal all-target MISSION_COMPLETE: false.** The two exact prior-operation holds below remain. The eligible design migration is verified; the remaining held-target work has the finalization boundary **ALL_SCOPED_LANES_BLOCKED**. This does not report the wider Prophet production programme complete.

The user assigned repair of the Prophet Paper file and its pages so they can fit into Beta's shared shell. The assigned session carried that repair through the available safe scope. This handoff does not transfer recovery to an old chat or author and does not request a new blanket approval.

### Exact remaining holds

| Target | Preserved condition | Work performed nearby | Required next proof |
| --- | --- | --- | --- |
| `ZE5-0`, old R8 full dark desktop, page `p-C-0` | Unresolved earlier palette-operation effect; entire root untouched. | Other eligible R7/R8 screens migrated. This reference is explicitly excluded from current extraction. | Reconcile the original operation's effect through its original lawful carrier before any edit or replay of this root. |
| `1EF3-0` inside `1EEH-0`, original mobile Plans content, page `p-F-0` | Unresolved prior `prophet-four-turn-t2-20261109-mplans-tabs` operation; content fragment untouched. | Only the disjoint shared header was updated. | Reconcile the original operation and target before replay or claiming that content fragment complete. |

The reviewed adapter catalog does not expose an operation-status API. A successful current read proves that a target exists; it does not retrospectively settle the effect of its prior operation. No cross-carrier replay was attempted. These exclusions are also visible in the Paper Start Here guide.

SX05 (`1G21-0`) and SX12 (`1GPK-0`) retain the source-accepted v5.2 content. SX05 received disjoint shell chrome only. SX12 remained unchanged. The new central guide corrects stale older whole-root hold wording without replaying historical SX05 attribution or finish operations.

## Start here

- [Current Prophet shared-shell integration guide](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-G-0) — root `2600-0`.
- [Current workspace family](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-F-0).
- [Sector connection family](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-H-0).
- [Shared Shell reference](https://app.paper.design/file/01M6Y2GT8S3YP4TK052PPESZEC/p-2-0), read only.
- [Complete migration manifest](https://github.com/mastermindx-market-intelligence/macro/blob/09e7bd4b39fcad07b773408d6527c1a3da02ed18/research/design_candidates/prophet_production_20261109/SHARED_SHELL_MANIFEST.json) — source-to-current node mapping, page roles, operation receipts, exact holds, and verification details.

Paper file ID: `01M3NT5Y3G5HTJHVR0K5W2MDJM` (PROPHET).

## What changed and why

The former independent page chrome left less implementation certainty about navigation ownership and usable workspace width. The updated designs use the shared navigation hierarchy and fit Prophet content into the shell's actual content region.

Desktop screens use the shared rail and top bar. Compact screens use one shared header, a drawer entry, search and account controls. Prophet remains selected under Market Intelligence. Product-specific Today, Screener, Plans and saved-list navigation stays inside Prophet; a local Today tab does not select the global Today job.

The content work goes beyond a chrome swap:

- Opportunity tables and the eight-column, 12-row Screener retain their fields within the 1168px desktop content region.
- Complete cards reflow into two columns where needed, preserving identity, quote, chart, release, cautions, entry terms and return context.
- Comparison rows retain aligned candidate columns.
- Setup decision summaries fit their labels, values and actions.
- Quote/assessment layouts preserve the before, receipt and after structure while stacking supporting panels.
- Timing charts preserve their original SVG path geometry, line styles and data semantics. Coordinate annotations were rebuilt as editable SVG text after Paper's HTML positioning did not preserve the required positions.
- English/Chinese and light/dark variants retain their content and theme behavior. Dark account/footer text was corrected where the imported chrome initially inherited black text.
- Embedded phone examples received the same compact shared header while retaining local navigation and OS status bars.

The larger desktop boards needed more vertical space after reflow. Nine boards were moved, with node identity preserved, onto two clearly named expanded-desktop pages. This removed canvas collisions without reducing content or shrinking type. The review page has a new 1440 × 292px internal guide.

## Shared-shell contract for Beta implementation

| Condition | Contract |
| --- | --- |
| Desktop viewport ≥1200px | 224px rail; 64px top bar |
| Desktop viewport 861–1199px | 196px rail |
| Compact desktop rail | 72px |
| Viewport ≤860px | One 56px shared header with shared drawer |
| Compact controls | At least 44px |
| 1440px viewport | 1216px remaining workspace; 1168px content with 24px gutters |
| Phone content | 16px gutters |
| Existing tablet content specimens | 20px gutters |
| Content sizing | `min-width: 0`; no whole-page horizontal overflow |

Reuse the existing `AppShell`, `SharedShellPrimaryNav` and `IntelligenceNav` owners. Extract Prophet's content region and mount it inside that shell. Do not recreate global navigation, search, account, appearance, language or drawer ownership separately for each page.

The six primary jobs remain Today, Discover, Analysis, Monitor, Research and Portfolio. Market Intelligence remains Overview, Macro Dashboard, **Prophet**, Sector Cycles and Sector Intelligence.

### Routes remain distinct

The complete opportunity workspace remains **`/us_stocks.html`**. Native **`/prophet`** remains the separately entitled model-plan/options desk; this visual migration does not authorize a route replacement or a newly unified route. Related destinations remain `/intelligence`, `/macro.html`, `/sector_cycles.html` and `/sectors`.

Preserve candidate/episode identity, independent quote and assessment clocks, Plan relationships, source-health states, null/unknown meanings and original return context. The original 38-contract B/Q/D/R programme remains controlling.

## Whole-file page directory

Every original page is assigned an implementation role. Historical captures, rejected directions, internal contracts and isolated component studies remain available with explicit roles; they are not mislabeled as current full-screen product UI.

| Page | ID | Top-level boards | Role |
| --- | --- | ---: | --- |
| [00 · START HERE · Shared shell handoff](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-G-0) | p-G-0 | 1 | Current integration contract, coverage, exact limits and source receipts. |
| [01 · Workspace · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-F-0) | p-F-0 | 23 | Flagship Today, setup, evidence, screener, compare, plans, record and source-health screens. The mobile Plans body hold is explicit. |
| [02 · Sector connection · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-H-0) | p-H-0 | 12 | Market → sector → company journeys. SX09–SX12 are state/disclosure/build references; preserve the evaluation definitions. |
| [03 · Opportunities · Shared shell refs](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-C-0) | p-C-0 | 30 | R7/R8 opportunities, lenses, setup, comparison and saved-list flows. The held ZE5-0 reference is excluded from extraction. |
| [04 · Rich cards · Shared shell refs](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-A-0) | p-A-0 | 32 | Complete-card, strategy and mobile journeys. Keep identity, quote, chart, release, cautions, entry terms and return context. |
| [04a · Expanded desktop · Opportunities](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-I-0) | p-I-0 | 6 | Expanded desktop cards, comparison, early leadership and the no-entry state. Larger boards are separated from compact examples to prevent overlap. |
| [05 · Daily brief & recovery · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-1-0) | p-1-0 | 19 | Daily brief, change history, comparisons, first-failure and history-unknown recovery. Retain each independent clock. |
| [06 · Today, setup & plans · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-3-0) | p-3-0 | 20 | R2 Today, setup and model-plan behavior, tablets, mobile and plan-guide examples. |
| [07 · Screener & compare · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-4-0) | p-4-0 | 8 | Table, grid and comparison designs. All columns remain; narrow views use the existing compact specimens. |
| [08 · Hong Kong & Canada · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-2-1) | p-2-1 | 19 | 18 visible regional variants in English/Chinese and light/dark at 1440, 390 and 320. The hidden superseded Canada board stays excluded. |
| [09 · Evidence & playbooks · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-7-0) | p-7-0 | 21 | Evidence, source details, playbooks, independent quote/assessment clocks and return paths. Larger desktop reviews continue on 10a. |
| [10 · Quote & assessment · Shared shell](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-8-0) | p-8-0 | 9 | Fresh, stale, failed and unchanged-assessment states. The expanded failed-refresh desktop is on 10a. |
| [10a · Expanded desktop · Reviews](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-J-0) | p-J-0 | 4 | Expanded failed-refresh, setup/timing and playbook desktop layouts; source definitions and chart geometry are preserved. |
| [11 · Build contracts & compact states](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-D-0) | p-D-0 | 33 | D03 compact screens use the shared header. Internal contracts and state atlases remain documentation; this current shell contract supersedes provisional geometry. |
| [12 · Shared contracts & state coverage](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-5-0) | p-5-0 | 8 | Behavior, coverage, overlays and degraded-state references. Mount component specimens inside the existing shell route. |
| [13 · Build · Clarity preservation](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-E-0) | p-E-0 | 1 | Preservation rules for meaningful content and research depth. Internal build documentation is excluded from product extraction. |
| [14 · Component studies · Host contract](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-9-0) | p-9-0 | 8 | Isolated card studies. Mount them in the Prophet content region beneath local context; do not manufacture a separate global shell for a component. |
| [ARCHIVE · Rejected directions · Do not build](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-B-0) | p-B-0 | 23 | Retained rejected directions, for historical comparison only. Use the current workspace and complete-card references. |
| [SOURCE · Historical capture · Do not build](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-6-0) | p-6-0 | 1 | The original live-baseline capture is preserved as source evidence. It is not a current shared-shell implementation target. |

### Coverage accounting

| Category | Count | Treatment |
| --- | ---: | --- |
| Screen boards with shell changes | 193 | Includes the mobile Plans root whose content fragment remains held |
| Additional galleries with phone header updates | 11 | 22 embedded phone examples |
| Original central guide replaced | 1 | Current page directory, shell contract, routes and exact holds |
| Original top-level boards touched | 205 | Unique original roots |
| Original boards preserved with explicit disposition | 72 | Build/state/component references, archive, source, hidden superseded reference, blank frame and the held R8 root |
| New review guide | 1 | Internal documentation on expanded review page |
| Final total | 278 | 277 mapped originals plus one added guide |

The preserved 72 comprise 17 internal build documents, 19 state/component specimens, eight isolated component studies, 23 rejected archive boards, one source capture, one hidden superseded Canada reference, one blank frame, one accepted SX12 disclosure component and the held R8 root. Existing component specimens should be mounted in their shared-shell host; adding an independent shell to every isolated card would create misleading implementation input.

## Verification and its limits

### Verified in Paper

- Final census: 19 pages and 278 top-level boards.
- Every original board maps to a current root and current page; all 205 changed original roots are present.
- Rendered dimensions were measured for 66 materially resized boards. After the native page moves, the checked expanded layouts have zero remaining canvas overlap conflicts.
- The added review guide is 292px tall and remains clear of the next board at y=1400.
- Representative screenshot review covered the flagship, sector connection, regional English/Chinese variants, narrow 320px comparison, mobile header/local navigation, Screener, complete cards, daily brief, setup/timing, comparison, Plans, evidence and quote/assessment layouts.
- Focused follow-up review verified the repaired comparison columns, light and dark setup summaries, chart annotation geometry, dark account contrast, embedded phone example, central guide and expanded review guide.
- The complete list of scoped screenshot readbacks is in the manifest. Coverage includes existing 320/390/768/1440 design families; this does not claim exhaustive pixel inspection of every board.

Scoped `finish_working_on_nodes` completed for 204 owned current roots. Held roots and the historical SX05/SX12 finish scope were excluded.

### Not asserted by this design work

No runtime source, PR, merge, deployment or Beta acceptance was performed. A live Beta browser proof was not obtained. Paper screenshots are design evidence, not evidence of deployed navigation, persistence, keyboard behavior, entitlements or economic validity. The original economic/quantitative evaluation definitions remain unchanged.

For the separate Beta implementation mission, prove the real route and shell once at relevant widths, keyboard/focus return, drawer behavior, theme/language propagation, saved-state behavior, negative states, source clocks and preservation of the original workflow. Green CI alone would not establish those outcomes.

## Current nodes for focused implementation

Use the manifest's `currentId` and `currentPageId` rather than superseded source roots.

| Example | Current node |
| --- | --- |
| Flagship workspace | `1CC5-0` |
| R7 Today | `1LDU-0` |
| Screener | `1LPB-0` |
| Complete cards | `1M0Y-0` |
| Setup / timing, light | `1OYM-0` |
| Setup / timing, dark | `1P73-0` |
| Comparison | `1SDZ-0`; aligned panel `20Y2-0` |
| Plans desktop | `23OF-0` |
| Evidence desktop | `1Y81-0` |
| Quote before/receipt/after | `1MCU-0` |
| R3 playbook | `1YEL-0`; final chart `214N-0` |
| Central integration guide | `2600-0` |
| Expanded review guide | `263T-0` |

## Source pins and durable evidence

- Governing Mastermind source: `f2b60761e65fdaa2338720f242d022ee4234f199`.
- Macro doctrine source: `e11afd6d8549eede47182a3fdac0c29f4fca4cfb`.
- Parent Prophet source: branch `sol/prophet-production-design-20261109`, commit `14a4b1c327db8dd0201f9ccffbc484dc8393929c`; [original masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/14a4b1c327db8dd0201f9ccffbc484dc8393929c/research/prophet_v4/PROPHET_PRODUCTION_MASTERPLAN_2026-11-09.md).
- Terminal source: `839bace1e89dd6def9311d3a410786c73a6332aa`; [shared-shell.css](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/839bace1e89dd6def9311d3a410786c73a6332aa/terminal/components/chrome/shared-shell/shared-shell.css) and [intelligenceNavigation.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/839bace1e89dd6def9311d3a410786c73a6332aa/terminal/lib/shared-shell/intelligenceNavigation.ts).
- Evidence branch: `sol/prophet-shared-shell-design-20261110` in `mastermindx-market-intelligence/macro`.
- Final manifest commit: `09e7bd4b39fcad07b773408d6527c1a3da02ed18`.
- Final manifest blob: `0133096a975f9c82bf2ed879475d0d2d59cf5c67`.
- Manifest readback matched the exact written content before this handoff was created.

The Paper adapter's snapshot hash is an identity/token drift guard. It is not an immutable revision hash of the design. GitHub commits provide the immutable evidence record; the Paper file is the editable deliverable.

## Continuation and do-not-redo

The next held-target action is reconciliation of the original effects, not replay of the old mutations. Independent Beta implementation may consume the eligible current designs through a separately assigned implementation mission.

Do not rerun completed migration operations, use replaced root IDs, recreate the expanded pages, retry HTML left/top placement, reapply old held effects, or replay SX05 attribution/finish. Do not alter the source-accepted SX05/SX12 content, turn archive/source/component pages into product screens, or treat this handoff as a replacement for the original programme.

No new watcher, queue, background runner, release authorization or external message was created. There is no promised asynchronous continuation or delegated worker awaiting return. The saved evidence and current Paper guide contain the complete implementation map and exact remaining boundary.
