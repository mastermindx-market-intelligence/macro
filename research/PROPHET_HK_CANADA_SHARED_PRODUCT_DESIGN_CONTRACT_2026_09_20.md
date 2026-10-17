# Prophet HK + Canada shared product design contract — R1

**Status:** `DESIGN_AUTHORITY_REPAIR_COMPLETE / EDITABLE_REFERENCE_FROZEN_AT_e3077bf50c / RIG_IN_REVIEW / PRODUCTION_NOT_PROVEN`
**Operation:** `prophet-hkca-shared-design-contract-r1-20260920-sol-001`  
**Parent:** `WS:PROPHET-HK-CA-REVAMP`  
**Source assignment:** `D_SHARED_PRODUCT_DESIGN_AND_UI(1).md`, V2, September 19, 2026  
**Protected procedure:** `Mastermind@8300950ac10a6c4c9e613ef26da42e67fb5c2dc8`, Skillpack 1.0.1/bootstrap 1
**Macro build base:** `86634cb89ad4e7253b44a049b6e5712406899f90`
**Current Macro compatibility pin:** `e84dc749411dd1cba6ef17453761d86fd43fb798`

This contract turns the accepted HK/Canada roster, continuity, card, and state requirements into one bounded product-design handoff for the existing Hong Kong and Canada carriers. It does not change producer truth, rank, thresholds, entitlement, access policy, publication authority, or portfolio action.

The current design authority approved the paired Paper geometry, component anatomy, states, themes, locales, counts, and roster/authority semantics. Session A then accepted those dimensions and required one bounded repair: remove fixture, programme, and source-authority vocabulary from user-facing Tier 1 while preserving every product invariant. The replacement Paper boards and evidence bundle in this commit complete that copy repair. Paper still does not become a repository-global design authority, satisfy Reference Integrity or independent review, prove either production route, or establish natural-publication continuity. Exact implementation, browser, access, integration, and natural-update proof remain separate gates.

The prior RIG review target `eca7c779c26e7eaaca04fc33b6b42b8ba2d8a6a1` is superseded. RIG reference `prophet-hkca-shared-r1` now binds the immutable replacement `e3077bf50c69063f5d80275fa33dd415dae76fa9`. No product-regression receipt, visual/taste receipt, design-authority RIG verdict, or `approval.yml` has been earned for this replacement; it remains provisional and non-canonical until fresh independent review and approval complete.

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

## 3. Approved editable source trace

The approved implementation projection is the governed Paper file:

- file: `Mastermind Product Design System — Agentic Lab`;
- file id: `01M2WGNCX9475G79JRKJTCM08P`;
- page: `Prophet · HK + Canada`;
- page id: `p-2-1`;
- Paper MCP server observed: `0.5.9`;
- final token content hash: `5ae876bc`;
- final page inventory: `3,102` nodes / `22` artboards.

The shared contract is artboard `1F-1`. The prior incomplete Canada shell remains only as the
explicitly named superseded audit artifact `9N-1`; B/C must not implement from it.

Exact primary implementation artboards:

| Market | Locale | Theme | 1440 | 390 |
|---|---|---|---|---|
| Hong Kong | EN | dark | `55-1` | `28U-1` |
| Hong Kong | EN | light | `24V-1` | `2GS-1` |
| Hong Kong | ZH | dark | `2OQ-1` | `34M-1` |
| Hong Kong | ZH | light | `2SP-1` | `38L-1` |
| Canada | EN | dark | `1MN-1` | `2CT-1` |
| Canada | EN | light | `20W-1` | `2KR-1` |
| Canada | ZH | dark | `2WO-1` | `3CK-1` |
| Canada | ZH | light | `30N-1` | `3GJ-1` |

Targeted variants:

- dark roster/access/history/interaction matrix: `3KI-1`;
- light roster/access/history/interaction matrix: `3PM-1`;
- Canada 320px ZH long-name + expanded-evidence stress: `3UN-1`;
- Hong Kong 320px ZH long-name + expanded-evidence stress: `3YW-1`.

The exact committed evidence bundle is:

`mockups/evidence/prophet-hkca-shared-design-20260920/`

Its `manifest.json` SHA-256 is
`65e9099da2d8b8b671b0016e4ac155598e280ee3313124de5b3fc6112f3d75cb`.
It binds each accepted artboard to a screenshot digest and a Paper `get_jsx`
`inline-styles` snapshot digest; `SHA256SUMS` binds every committed evidence byte. The replacement keeps all artboard IDs, declared geometry, tokens, node count, and state coverage unchanged. Publication-wide dates now appear once at board level; row dates remain only when genuinely row-specific. User-facing JSX contains none of the rejected fixture, Branch-B, owner-current/owner-visible, screening-authority, or corresponding Chinese architecture labels; exact source and authority provenance remains in this contract and RIG evidence.

### 3.1 Design-authority disposition — `APPROVED_FOR_BOUNDED_IMPLEMENTATION`

The design authority reviewed every accepted board after mutation, including both themes,
both languages, both primary widths, both market-specific 320px long-name cases, and the
state/interaction matrices. The review passed spacing, typography, contrast, alignment,
artboard fit, deliberate responsive recomposition, and no horizontal overflow at 390/320.

The accepted product decisions are:

- The Hong Kong reference epoch demonstrates `39` current names and an explicit two-name Top
  subset without making the subset appear to be the whole board. Production derives the total
  from the current reconciled roster; an independent anonymous probe later observed `40`.
- The Canada reference epoch demonstrates `17` current screen/watch names and `Top Picks 0`, while
  preserving Branch-B screen authority rather than inventing official picks or entry permission.
  Production derives both counts from the current screen/watch owner; neither number is a quota.
- Grid/Table, search, stage, recently changed, research attention, and evidence/record share
  one information architecture and card grammar across both themes and languages.
- Mobile is a deliberate single-column recomposition rather than squeezed desktop geometry.
- Chinese copy is native-shaped, wraps rather than clips, and carries no raw English state names.
- Historical rows remain visibly non-actionable; missing history never becomes an inferred exit.
- State designs distinguish singleton, Top-empty/All-nonempty, valid zero, watch-only, blocked,
  stale, source failure, unauthenticated, entitlement expired, filter empty, incomplete history,
  correction, expanded, focus-visible, disabled/locked, and recovered.

This approval preserves the exact artboards as the replacement design candidate, but it does **not**
yet release B/C to begin the new R1 visual migration. The replacement must first be rebound to the
Reference Integrity Gate and receive fresh independent review. It does not grant repository-global
canonical reference status or authorize merge, deployment, access-policy change, rank/signal change,
or publication.
A forced state proves intended presentation only unless the real producer/runtime emitted it.

The Figma file `IKqTiq7jeVBJusBfoHnPsH` remains a secondary design-system projection and is not
the implementation source for this paired reference. Paper is the preferred governed web-design
surface for this lane; repository tokens/components remain the authority it projects.

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
2. **Current state:** the market-native stage and plain-language stance; exact source identity stays in details.
3. **Why shown:** a plain-language reason for inclusion; source provenance stays in Tier-2 receipts.
4. **Timing:** current permission/block and dated freshness.
5. **Next trigger:** only when the current producer supplies one; otherwise honest unavailability.
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
and architecture terms stay out of Tier 1. In particular, implementation-source boards may not expose
`REFERENCE FIXTURE`, `BRANCH-B`, `OWNER CURRENT`, `owner-current`, `owner-visible`,
`Screening authority`, `参考样本`, `当前归属`, `B 分支筛选`, or generic owner/source labels as
default user copy. Those exact identities remain available in Tier-2 evidence and repository receipts.
A publication-wide as-of appears once at board level; a card repeats a date only when that date is
row-specific.

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

The editable design now covers all sixteen primary cells. Its displayed `39`/`17` counts are
reference-epoch examples only; implementation must render current producer-derived totals:

```text
2 markets × EN/ZH × dark/light × 1440/390 = 16/16
```

It also covers two market-specific 320px ZH long-name/expanded-detail cases and paired dark/light
state/interaction boards. The committed evidence bundle and manifest named in §3 are the source for
all visual implementation references; chat images and the superseded shell are not source.

Covered design states include populated, singleton, Top-empty/All-nonempty, valid zero, watch-only,
blocked, stale, source-failed, unauthenticated, entitlement-expired, filter-empty, incomplete history,
recent change, correction, focus-visible, expanded/open, disabled/locked, touch dismissal, and
fresh→stale→failed→recovered transition treatment.

Implementation still owes real-path proof for:

- the inherited production card DOM and real controls rather than Paper nodes;
- repair of the measured HK baseline where `source=all` Grid represented `40` current identities
  (`32` board + `8` watch) but Table exposed only three stocktable rows;
- Grid/Table/search/stage/filter identity and deterministic-order round trips, including
  Grid→Table→Grid with no identity or order loss;
- native keyboard, touch, Escape/focus-return, and popover/navigation behavior;
- loading skeletons and live quote/layout stability;
- access-policy enforcement and absence of hidden paid identities in delivered bytes;
- actual producer-emitted stale/failure/correction states where available;
- no horizontal page overflow at 390 and targeted 320 in a browser;
- dark/light contrast on the painted production surfaces;
- publisher template/site mirror parity and successor evidence.

A forced Paper state proves intended presentation only unless the real producer path emitted it.
New semantics require successor evidence; old P0B screenshots may not be relabelled as a new browser
run. Production acceptance also requires two successive natural market publications so continuity,
transition, correction, and exit behaviour are observed rather than inferred.

## 14. Implementation order

1. **REPAIR COMPLETE — Session D:** paired Paper geometry, component anatomy, state coverage, and
   artboard IDs remain frozen; the plain-language Tier-1 replacement is evidence-bound in this commit.
   RIG rebinding and fresh independent review are the next gate before R1 implementation release.
2. The shared-card incumbent grants or denies an exact lease for any required partial change.
3. B implements the HK route on `#7163` without seizing Canada or shared paths.
4. C implements the Canada route on `#7018` without weakening Branch-B screen semantics.
5. Each lane captures its own successor evidence and returns exact head/tree/test receipts.
6. Session H / the current independent-review owner adjudicates the immutable design and integrated
   implementation; Reference Integrity remains a release gate where applicable.
7. A integrates compatible heads and owns deployment/publication sequencing.
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
- the frozen Paper implementation reference or secondary Figma projection disagrees with repository design law.

## 16. Acceptance boundary

Session D's **design-contract repair is complete and frozen on this commit** at the Paper/evidence
identities in §3: exact implementation artboards, measurements, plain-language copy, state transitions,
screenshot receipts, and JSX digests are durable; the shared-card writer boundary and B/C carriers remain
explicit. The earlier RIG target and its review requests are superseded and confer no acceptance on this
replacement.

The following are deliberately **not** claimed by that result:

- repository-global canonical/RIG approval;
- independent Session H acceptance;
- implementation by either market carrier;
- browser, access-policy, publisher-mirror, deployment, or natural-publication proof;
- completion of the parent HK/Canada Prophet upgrade.

The product outcome is not complete when this document, a Paper/Figma file, a CSS patch, or CI alone
exists. Completion requires the real HK and Canada routes to implement the design, preserve truth and
access boundaries, pass independent and browser review, and establish continuity across two natural
publications. B/C remain held from the new R1 visual migration until the replacement reference is
rebound to RIG, independently reviewed, and explicitly released; lawful R0 restoration on already
accepted styling remains independent.
