# Prophet HK + Canada shared product design contract — R1

**Status:** `DESIGN_AUTHORITY_REVIEWED / REFERENCE_REWORK_REQUIRED / IMPLEMENTATION_CONTRACT_DRAFT`
**Operation:** `prophet-hkca-shared-design-contract-r1-20260920-sol-001`  
**Parent:** `WS:PROPHET-HK-CA-REVAMP`  
**Source assignment:** `D_SHARED_PRODUCT_DESIGN_AND_UI(1).md`, V2, September 19, 2026  
**Protected procedure:** `Mastermind@f3d187976e083f9b102fc49696395b5c1521ebb5`, Skillpack 1.0.1/bootstrap 1  
**Macro base:** `86634cb89ad4e7253b44a049b6e5712406899f90`

This contract turns the accepted HK/Canada roster, continuity, card, and state requirements into one bounded product-design handoff for the existing Hong Kong and Canada carriers. It does not change producer truth, rank, thresholds, entitlement, access policy, publication authority, or portfolio action.

The visual reference remains provisional until the current design authority approves it and the implementation is proven on both production routes. This document is executable implementation law for the named B/C lanes only after that approval; until then, it is the exact review target and gap register.

## 1. Authority, carriers, and non-goals

- Session D owns shared product design and component convergence.
- Hong Kong implementation remains with the incumbent `#7163` carrier:
  `templates/hk.html.j2`, `site/hk-stock-v36.js`, and its successor evidence.
- Canada implementation remains with the incumbent `#7018` carrier:
  `templates/canada.html.j2`, `site/canada-stock-v36.js`,
  `scripts/build_canada.py`, `scripts/canada_theme_action_map.py`, and its successor evidence.
- Sparse-card geometry remains isolated on `#7303`; do not widen that CSS patch into this redesign.
- The shared card partial is `templates/_prophet_card.html.j2`. No lane may modify it without an exact incumbent/source-writer lease.
- Integration and release remain with Session A. Independent visual/semantic acceptance remains with Session H.

Out of scope:

- no threshold loosening, candidate fabrication, era restamping, or new ranking authority;
- no challenger publication into `hk_standouts.json`;
- no new lifecycle, candidate store, ledger, retry, auth, navigation, or publication plane;
- no `theme.js`, global navigation, provider-data, or access-policy rewrite;
- no inferred exit reason or continuous tenure from absence;
- no synthetic HK/Canada Plans workflow.

## 2. Governing design law

Content law is `docs/DESIGN_DOCTRINE.md`. Visual/composition law is
`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`. Migration and evidence law is
`research/DESIGN_MIGRATION_FACTORY_V1.md`. On conflict, content law wins.

Reuse the existing repository vocabulary:

- `.pvcard` / `pv_css()` for Prophet cards;
- `.dtp` and `.dtp-asof` for freshness and one as-of;
- LENS `data-tip-en/zh` for evidence receipts;
- `.mx-sec` for section headers;
- `.mx-empty` + `.mx-empty-why` for truthful empty states;
- `.mx-tbl` for the table view when available on the target route;
- `_icons.html.j2` for controls and state icons;
- repository tokens only; no new root, literal palette, font stack, or page-local material system.

A missing primitive is a `DESIGN-SYSTEM GAP`, not permission for B or C to invent a route-local fork.

## 3. Editable source trace

Governed Paper projection:

- file: `Mastermind Product Design System — Agentic Lab`;
- file id: `01M2WGNCX9475G79JRKJTCM08P`;
- page: `Prophet · HK + Canada`;
- page id: `p-2-1`;
- token content hash observed at recovery: `d61e4858`;
- artboard `1F-1`: `10 · Shared Contract · Dark · EN`;
- artboard `55-1`: `20 · Hong Kong · Daily Workspace · Dark · EN · 1440`;
- artboard `9N-1`: `21 · Canada · Daily Workspace · Light · EN · 1440`.

Observed file state: 291 nodes and three 1440px artboards. Paper MCP server `0.5.9`
returns `WEEKLY_LIMIT` for tree reads and editing. A fresh read-only public-browser render was
captured at 3× device scale on September 20, 2026 and all three artboards were visually reviewed.
That render proves the pixel projection only; exact node provenance, editable variants, and
reference approval remain unverified.

### 3.1 Design-authority review — `REWORK_REQUIRED`

The current visual reference is **not approved for R1 implementation**. The useful direction is
preserved, but the pair is materially incomplete against the assignment and sixteen-cell bar.

What stands:

- The shared contract separates Current, Research, Changed, and Record, and distinguishes current
  authority from a non-actionable historical row.
- The Hong Kong board communicates `39 current names / 2 live`, exposes Top versus All, Grid/Table,
  search, stage totals, and owner-native cards with why-shown, timing, price, and evidence.
- The Canada header truthfully says Branch-B screen, `17 current names`, `Top Picks 0`, and no
  confirmed entry instead of fabricating scarcity or action.

Blocking gaps:

1. Canada is only a header and Top/All toggle shell. It lacks search, Grid/Table, stage/watch counts,
   current cards, reasons, timing, evidence, recent changes, record, and designed degraded states.
2. Only three desktop artboards exist: shared dark EN, HK dark EN, and Canada light EN. The required
   market × locale × theme × width matrix has no ZH, no 390/320, and no opposite-theme market pairs.
3. No complete interaction or permission-state variants are shown for keyboard focus, expanded
   evidence, loading, stale, source failure, unauthenticated, expired entitlement, or filter-empty.
4. Exact approved component-variant and node/version identifiers cannot be handed to B/C while the
   editable tree remains quota-blocked.

Ordered remediation:

1. Complete Canada to semantic parity with HK while preserving its screen and watch-only authority.
2. Compose deliberate HK-light and Canada-dark treatments, then EN/ZH 390 variants for both markets.
3. Add one governed state/interaction board covering the required failure, permission, history, and
   input modalities without inventing another evidence plane.
4. Re-open the editable tree, record exact approved node/version identifiers, and capture the primary
   sixteen cells plus targeted 320/history/permission evidence before releasing R1 source work.

This R1 reference gap does not block lawful R0 truth/roster restoration using already accepted
styling. B/C must not begin the new R1 visual migration from these provisional boards.

Draft Figma projection named in `#7394`:

- file key: `IKqTiq7jeVBJusBfoHnPsH`.

`#7394` remains draft and change-requested at the source observation. The Figma file key is not
an approved Prophet reference, and exact Prophet node/version identifiers were not verified in
this lane. B/C must not implement from the key alone.

## 4. Daily user job

A user must be able to answer, in seconds:

1. What is currently worth inspecting?
2. What timing is permitted or blocked?
3. Why was this name shown?
4. What changed since the previous publication?
5. Where did a name go?
6. What source or coverage is missing?

The first viewport shows session/state, the selected count, and useful actions. Internal
producer/entitled/current/visible diagnostics stay behind evidence disclosure and only appear
when access policy permits them.

## 5. Information architecture

### 5.1 Current opportunities

`All Candidates` is the complete entitled current owner-visible roster, across every currently
owned lifecycle stage. It is never a BUY-only list or research spotlight.

`Top` is an owner-selected subset of `All`. It may be empty while `All` remains useful. The UI
must never imply that a featured subset is the whole board.

Grid and Table are two projections of the same identity set and order. Search, stage, selection,
and page filters preserve identity and deterministic order. Stage changes card content and stance,
not the card anatomy.

### 5.2 Research attention

Optional selected ideas from existing approved research owners live in a separately labelled
surface. Research attention does not define `All`, current rank, lifecycle, or entry permission.
Missing research cannot empty or reorder the current board.

### 5.3 Recently changed

This is a read-only continuity projection from positive prior evidence and the latest comparable
membership. It may show last-seen date, current reassessment, and an owner-supplied reason.

A historical row is never allowed to retain stale BUY, rank, quote, plan, timing, or entry state.
Unknown completeness, reason, and exit time remain explicitly unknown. A source outage never means
all prior candidates exited.

### 5.4 Evidence & Record

Current-definition metrics and historical eras remain separate. No pooled success headline.
Track Record is integrated into the journey but never becomes current action authority.

Plans appear as a separate workflow only when the market has a verified plan owner and real plan
identity. Otherwise the UI states that Plans are unavailable.

## 6. Roster and identity contract

The implementation reconciles this chain exactly:

```text
producer_current
→ entitled_current
→ current_by_stage
→ top_picks_subset
+ recent_transition_rows from existing fossils/ledgers
→ selected_view
→ rendered_DOM
```

Required invariants:

- `Top ⊆ All Candidates`;
- each current identity appears once in `All`;
- Grid identity/order equals Table identity/order for the same filter;
- filter counts derive from the reconciled roster, never a separate recount;
- a row absent from today’s producer can appear only as a non-actionable recent transition;
- diagnostic fixtures may not mutate the owner population;
- no display-only identity is written into a graded board ledger.

## 7. Shared card contract

Every current card has the same seven regions:

1. **Identity:** market, listing/ticker, company/display name.
2. **Owner state:** the current owner-native stage and plain-language stance.
3. **Why shown:** owner-supplied reason, translated for Tier 1.
4. **Timing:** current permission/block and dated freshness.
5. **Next trigger:** only when the owner supplies one; otherwise honest unavailability.
6. **Compact evidence:** the few facts that explain the card without exposing an internal dump.
7. **Details:** keyboard/touch-accessible evidence and receipts.

Canada’s selection label remains a **screen** even when timing is open. A screen is not a
validated official pick. Timing, sector context, and issuer-selection evidence remain distinct.

Historical cards use a visibly non-actionable treatment: neutral border/ink, transition label,
last-seen date, and no live CTA. Missing quotes show `Unavailable` or a dated last observation,
never zero. The browser may not reconstruct financial geometry.

## 8. Field ownership

| Field | Canonical owner | UI rule |
|---|---|---|
| current identity, stage, reason | market-native producer | render exactly once; translate labels, not meaning |
| rank, quote, action state | current producer publication | never carry onto historical rows |
| entitlement | existing access owner | hidden is not removed |
| Top membership | owner-selected subset | never positional “first N” masquerading as product truth |
| filter/search/page counts | reconciled current roster | deterministic derivation only |
| recent membership / last seen | existing ledgers, snapshots, fossils | positive evidence only |
| exit/change reason | current owner-supplied evidence | unknown when absent; never inferred |
| research attention | approved research owner | separate, optional, zero action authority |
| plan identity | verified market plan owner | otherwise unavailable |
| display copy and layout | product design / route templates | may not create financial or lifecycle truth |

## 9. Theme and layout contract

### Dark treatment — command center

Use the existing dark tokens: graphite canvas, luminance-separated panels, hairline structure,
and restrained semantic ink. Hue appears only for direction, health/severity, action/wayfinding,
provisional state, or locks. No decorative glow on data rows.

### Light treatment — research workspace

Use the existing cool canvas, white material panels, clear hairlines, and controlled shadow.
Light is not a token-swapped dark screen. Accent rows use quiet tint plus a structural rail;
locked/disabled content remains legible without a dirty blur.

### Desktop 1440

- retain each route’s existing PageShell and navigation;
- use token spacing: 24px section rhythm and 16px card interior as the default;
- HK owner grid: start-aligned flexible tracks, 260–300px;
- Canada owner grid: start-aligned flexible tracks, 280–320px;
- keep the shared card anatomy byte/semantic-equivalent across markets;
- dense detail belongs in the Table or LENS receipt, not a taller first-viewport wall.

### Mobile 390 and targeted 320

- one full-width owner column at `≤680px`;
- no card or page horizontal overflow;
- wide tables scroll inside their container;
- names and bilingual copy wrap, never clip;
- disclosure/action targets are at least 40×40 effective;
- expanded details recompose below the summary, not as an off-screen side panel.

## 10. Tier-1 labels and copy

| EN | ZH |
|---|---|
| Current opportunities | 当前机会 |
| Top | 精选 |
| All candidates | 全部候选 |
| Research attention | 研究关注 |
| Recently changed | 最近变化 |
| Evidence & record | 证据与记录 |
| Grid | 卡片 |
| Table | 表格 |
| Clear filters | 清除筛选 |
| View evidence | 查看证据 |
| Last seen | 最后出现 |
| Timing blocked | 时机受阻 |
| Screen | 筛选结果 |

Copy stays within doctrine budgets. Raw ranks, scores, internal state slugs, statistical receipts,
and architecture terms stay out of Tier 1.

## 11. Required data and permission states

| State | EN Tier-1 copy | ZH Tier-1 copy |
|---|---|---|
| singleton | `1 current candidate` | `1 个当前候选` |
| Top empty, All nonempty | `No Top picks now. All candidates are still available.` | `当前暂无精选，全部候选仍可查看。` |
| full valid zero | `No current candidates in this publication.` | `本次发布暂无当前候选。` |
| watch-only | `Nothing is ready to act on. Watch candidates remain visible.` | `暂无可操作机会，观察候选仍可查看。` |
| blocked | `Timing is blocked. Wait for the stated trigger.` | `时机受阻，请等待卡片所列触发条件。` |
| stale | `Data is dated. Do not treat this as a current entry.` | `数据已过期，请勿视为当前入场指引。` |
| fresh-source failure | `Today’s source failed. Last confirmed roster is context—not action.` | `今日数据源失败。上次确认名单仅供参考，不构成操作指引。` |
| unauthenticated | `Sign in to view the entitled roster.` | `登录后查看有权限的候选名单。` |
| entitlement expired | `Access expired. Current candidates are hidden, not removed.` | `访问权限已到期。当前候选已隐藏，并非被移出名单。` |
| filter empty | `No candidates match these filters.` | `没有候选符合当前筛选。` |
| incomplete history | `History is incomplete. Exit time and reason may be unknown.` | `历史记录不完整，退出时间和原因可能未知。` |
| plans unavailable | `Plans are not available for this market.` | `该市场暂无可验证的计划功能。` |
| corrected | `Updated after correction.` | `已更正更新。` |

Loading uses skeletons at true geometry and never prints zero or an em dash as a placeholder.
Refreshing a failed source and clearing filters are separate actions.

## 12. Interaction contract

- Mouse, keyboard, and touch expose the same evidence.
- Hover is enhancement only; no evidence is hover-only.
- `Enter`/`Space` opens details; `Escape` closes and returns focus to the trigger.
- Focus-visible is unmistakable in both themes.
- Expanded card and Table row expose the same fields and receipts.
- Tooltip/popover triggers never collide with navigation or card selection.
- Selection, active filter, expanded, disabled, locked, loading, stale, error, and corrected
  treatments are materially distinct where supported.
- Layout remains stable while loading or quotes update.
- Reduced-motion users receive no shimmer, breathing, or transition dependency.

## 13. Evidence matrix

Primary visual acceptance is exactly sixteen cells:

```text
2 markets × EN/ZH × dark/light × 1440/390
```

Add targeted evidence rather than a huge Cartesian expansion:

- 320px long-name and expanded-detail checks for both markets;
- populated, singleton, Top-empty/All-nonempty, valid-zero, watch-only, blocked;
- stale, source-failed, unauthenticated, entitlement-expired, filter-empty;
- incomplete-history and recent-transition rows;
- hover, keyboard focus, expanded/open, disabled/locked where supported;
- Grid/Table/filter identity and order round trips;
- dark/light contrast and no horizontal page overflow.

Evidence uses the real inherited card DOM and real controls, not isolated decorative boxes.
A forced state proves presentation only unless the actual producer path emitted it. New semantics
require successor evidence; old P0B screenshots may not be relabelled as a new run.

Production acceptance also requires two successive natural market publications so continuity,
transition, correction, and exit behaviour are observed rather than inferred.

## 14. Implementation order

1. Session D obtains design-authority approval of the paired reference or records exact gaps.
2. The shared-card incumbent grants or denies an exact lease for any required partial change.
3. B implements the HK route on `#7163` without seizing Canada or shared paths.
4. C implements the Canada route on `#7018` without weakening Branch-B screen semantics.
5. Each lane captures its own successor evidence and returns exact head/tree/test receipts.

6. A integrates compatible heads and owns deployment/publication sequencing.
7. H reviews the immutable integrated result against this contract and the sixteen-cell matrix.
8. Natural publications establish continuity proof before parent acceptance.

Urgent R0 restoration may continue in the existing accepted style. R1 does not block a truthful
current-roster repair that requires no new visual language.

## 15. Stop and escalation conditions

Stop the affected lane and return to Session D/A when:

- a required canonical component is missing;
- a shared partial has an incumbent writer or unknown effect;
- the design would expose source population beyond access policy;
- Grid and Table cannot preserve one identity/order contract;
- a historical row would need inferred exit truth;
- Canada would be presented as validated official picks;
- the market has no verified Plans owner;
- implementation requires a new auth, lifecycle, ledger, candidate, or publication plane;
- the provisional Paper/Figma projection disagrees with repository design law.

## 16. Acceptance boundary

This document is complete as a design contract only when:

- the current design authority has reviewed the actual editable reference;
- exact approved editable node/version identifiers replace provisional identifiers;
- B/C acknowledge the field, variant, measurement, copy, and state contract;
- the shared-card writer boundary is explicit;
- implementation and evidence paths are named;
- all unresolved gaps have an owner and stop condition.

The product outcome is not complete when this document, a Figma/Paper file, a CSS patch, or CI
alone exists. Completion requires the real HK and Canada routes to implement the design, preserve
truth and access boundaries, and pass browser plus natural-publication proof.
