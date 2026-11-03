# D02 implementation guidance and composition requirements

**For a later authorized build after reference acceptance. No production code is implemented by this packet.** A final composed Paper candidate cannot freeze until the joint F01/F02 shell-system v1 has been verified. This document makes the next build concrete without inventing that release.

## 1. Existing code boundaries to reuse

| Boundary | Reuse / change guidance | Avoid |
| --- | --- | --- |
| dashboard.html.j2 macro region | Keep body.page-macro selectors and existing macro dialog/anchor identities; isolate hierarchy, copy, null guards and inspectors | Global selector replacement or changes to body.page-stocks/D03's equity-scoreboard |
| build_site.py macro VM | Preserve producer fields, eligibility, model/source identities and per-source clocks; adapters can project them without recomputing models | Treating the entire VM as D02-owned; dropping refusal fields; replacing zero by truthiness fallbacks |
| Existing #10485 Signals candidate | Reconcile exact owner/head and consumer contract before any overlap | Parallel implementation of the same evidence popup or promoting its standalone internal route |
| Fourteen thin templates | Reuse _macro_suite_shell.html.j2, lib/macro_suite_view.py, macro_suite.js and shared builder | Fourteen forked layouts, state parsers or bespoke data services |
| Macro Command | Reuse fixed section map, macro_command.js, fragment template and existing exporter classification | A second navigation registry, standalone pages from fragments, eager mounting of all sections |
| Macro Context | Retain existing synthesis/anchors and risk-calibration disclosure; repair lossy reading-state/date/zero projection | Hiding the whole page for one missing source or copying raw unavailable scores |
| Laboratory/queue builders | Reuse existing producer outputs and exact asset/query contracts | Browser-side model refits, new unsupported endpoints, changing event/return definitions |
| Shared host | Consume F01 content/local-nav/inspector slots; keep Terminal's independent chrome | Double app shells, duplicate Brain instances, arbitrary query normalization |
| Design primitives | Consume F02 tokens and common chart/table/state/focus components | A D02 token fork or local mobile bottom bar |

Existing source functions are the implementation entry points; no new component names here imply a released package. A future extractor may create narrowly scoped partials, but must prove identical route/anchor/data behavior before changing hierarchy.

## 2. Geometry: provisional stress fixture, not released v1

F02 Draft #10630 initially supplied the geometry at c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82. Its handshake, first consumed at 21ec752c56222eb747d51950b29892d463c4398b and re-read at f7c25c4b9870cff260c2a4b998be18d6c04d36d0, records candidate concurrence but leaves F01 acceptance of clarified cutoffs/transition rules, joint qualification and review open. F01's refreshed contract at b2d00ddc7e2dfbffdc3c5855e1a4dffe8c4226a5 still specifies a 768px gutter boundary and up-to-400px modal, against F02's 600px boundary and 440px represented overlays. The table below is the F02 stress fixture; its listed integer examples happen to agree on the underlying content width, which does not resolve those differences. This is not a joint v1. See the [exact comparison and native-effect holds](EVIDENCE_AND_DEPENDENCIES.md#8-bounded-foundation-refresh-before-handoff).

| Viewport CSS px | Provisional rail | Side padding | Content width | Proposed inspector behavior |
| --- | --- | --- | --- | --- |
| 320 | none | 16 each | 288 | Overlay; all controls reachable |
| 390 | none | 16 each | 358 | Overlay; answer/path before metadata |
| 768 | none | 20 each | 728 | Overlay/drawer |
| 1024 | 196 | 20 each | 788 | Overlay; docking would leave too little primary width |
| 1280 | 224 | 24 each | 1008 | 320 inspector +24 gap leaves664 primary |
| 1440 | 224 | 24 each | 1168 | 320+24 leaves824 primary |
| 1600 | 224 | 24 each | 1328 | 320+24 leaves984 primary |

Provisional headers are64/56; user-selected compact rail is72; rail absent at≤860. These values are for stress analysis only and must be replaced or confirmed by the exact joint v1 release. The agreed candidate docking arithmetic measures usable content C after actual shell, local reserved chrome and gutters: dock only when C − 320 − 24 ≥ 640, equivalently C ≥ 984. F02 alone proposes the 440px overlay at represented 768/1024 widths, constrained to the available viewport, and full-viewport evidence with internal padding at ≤600. Its continuous candidate boundaries are ≤600, >600–≤860, >860–<1200 and ≥1200; F01 has not accepted those clarifications. At a 700px viewport, F01's 16px gutters leave668px and F02's 20px gutters leave660px. Require the owners to settle that concrete 8px difference and the 40px modal difference; do not silently choose or average them. Fractional CSS widths need explicit testing because historical integer media queries have gaps. Do not automatically compact the user-selected rail to fit a dock. Test expanded and compact nav, inspector open, long EN/ZH labels and400% zoom. Do not qualify a1440 standalone screenshot as the actual1440 content width.

Content behavior is width-driven: summary rows wrap before labels collide; a chart and side evidence become stacked when their useful minimum widths fail; dense tables retain scoped scroll with headers and units; the primary path remains legible. Preserve access to every local view through the released navigation pattern.

### Candidate component and token consumption map

The [F02 handshake at the refreshed checkpoint](https://github.com/mastermindx-market-intelligence/macro/blob/f7c25c4b9870cff260c2a4b998be18d6c04d36d0/research/design_candidates/production_design_20261102/f02/F01_HANDSHAKE_CANDIDATE.md) and retained [candidate.2 token-map baseline](https://github.com/mastermindx-market-intelligence/macro/blob/c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82/research/design_candidates/production_design_20261102/f02/token-map.json) supply design roles, not installed component imports or a released CSS namespace.

| D02 need | F02 candidate role | Existing implementation boundary / token scope |
| --- | --- | --- |
| State, score and change | SectionHeader, MetricValue, ChangeValue; domain DecisionRow/VerdictHero remains separately qualified | Macro/suite Jinja and source VM; numeric alignment and tabular figures; no new score math |
| Per-reading freshness/coverage | FreshnessReceipt, StatePanel, Callout | Typed suite availability and legacy adapters; essential caveats use readable text, not tertiary-only emphasis |
| Driver/metric comparison | DataRow, TableFrame, CountLadder where domain-qualified | Existing tables; source units/counts/sort/export retained |
| Path, rates, breadth and cone | ChartFrame | Existing producer series/plot ownership; actual chart-series semantics preserved |
| Local navigation | Tabs | Macro Command and macro_suite.js exact hashes/keyboard behavior; F01 slot governs fit |
| Evidence | EvidenceTrigger, EvidenceInspector, DetailDisclosure | Existing local inspectors; F01 owns outer layer/focus/scroll; one evidence identity across dock/overlay |
| Source access and D23 action | TierGate, Action, SaveFeedback | Source-rights condition distinguished from user entitlement; D23 owns writes/readback |

Preserve scope-specific aliases: canvas uses existing --bg; panel --panel; raised Macro --panel2 differs from Terminal --panel-2/--panel-3; primary text --text; secondary/tertiary roles map differently across --muted/--ink-2/--ink-3 and Terminal text roles. Link/price direction remain source-owned. The observed Paper --noir-* dark palette and proposed light specimen values are inputs, not permission for a global token replacement. Do not conflate language with health/risk/aggressor/exposure semantics. Resolve --sp-8 and other documented source collisions through F02 rather than spelling-based aliases.

## 3. Required editable Paper work after the foundation gate

Existing file/page identities remain unchanged. D02 made no Paper edits, moves or new file/page claims in Phase 2A. Proposed organization names from the assignment are not created destinations.

The next D02 composition set should cover these semantic cases using the released shell and actual content density:

| Composition | Required content and variants | Existing reusable input |
| --- | --- | --- |
| Macro overview | Loaded regime, meaningful60-session path, support/counter-evidence, invalidation, asset step; phone/narrow/wide | Current source and public response; Risk Radar grammar |
| Risk inspector | Normal qualified estimate; unavailable scare; partial/stale evidence; exact-model unmatched; horizon and same-context return | p-1-0 primary/evidence/mobile plus theme/locale variants |
| Pullback | Observed damage; qualified estimated depth; unqualified estimate; China observed-only referral | p-6-0 US/China examples, explicitly illustrative |
| Breadth evidence | Universe-qualified tape/history/participation/coverage; corrected arithmetic and reachable sources | p-13-1 desktop/mobile/inspector; preserve D03 implementation boundary |
| Command/workspace | Twelve-section local navigation, subtab fragment loading; Current/Drivers/History; stale and contradiction specimens | Existing shared builder/shell/typed data; Liquidity decision-first variant |
| Context/laboratory/queue | At least one normal-data archetype and its distinctive failure/qualification, with all retained controls mapped | Existing source; do not use generic error cards as normal-task proof |

Each materially changed hierarchy/interaction needs an editable composition. At minimum provide representative light/dark, EN/ZH, narrow-content and phone specimens; use an explicit coverage matrix rather than duplicating every screen seven times. Record source fixture, file/page/artboard IDs, observation time and actual shell/system versions. Adjacent annotations must describe control effects, URL/history, source clocks, qualification, focus and return.

Create or reuse a target-scoped **00 · Read me & Build contract** page only after exact destination and overlapping writers are reconciled. It should contain the product/job, normal journey, source packet, owner, foundation versions, limits and real review state. This source packet is ready to supply that content; the in-Paper obligation is still outstanding.

Capture/export supported candidate content and annotations into one immutable source set, with digests. A snapshot token or mutable Paper link is not a document revision or approval. Subsequent canvas changes invalidate affected captures/review evidence.

## 4. Future implementation sequence

1. **Reconcile source custody.** Re-read current D02/#10485/D03/F01/F02/F03 heads and exact active writers. Keep the D02 source carrier and avoid shared return-file collisions. Do not restart another product session.
2. **Consume foundation release.** Verify joint contract, actual widths, token/component mapping, nav/context semantics, outer/embedded scroll and modal ownership, and accepted route-return behavior. Recompose affected references.
3. **Resolve data-truth defects with incumbent owners.** Preserve unavailable scare fields in Macro Context, correct null/zero fallbacks, fix false source clocks, resolve rate basis/date generation and qualified copy. No model threshold changes are included.
4. **Complete reference review.** Freeze editable before/after artifacts and capability/task manifest. Independent product-regression and visual/taste first passes receive only the permitted input set; reveal rationale/constraints after findings freeze. Use actual RIG statuses/receipts.
5. **Implement scoped consumer/template changes.** A later explicit implementation commission is required. Reuse existing validators/adapters and shared template branches. Develop against frozen real fixtures and typed refusal cases.
6. **Verify rendered artifacts and interactions.** Run relevant existing tests plus the discriminating cases in this packet; inspect real host composition, access, history, keyboard/touch/zoom, SSR/no-JS and source generation. Do not accept process exit0 as proof of output.
7. **Roll out by approved family.** Under later authority, use the existing deployment owner and route projection. Verify actual served asset/HTML/model identities, beta deep links and production measurements. No route admission or rollout occurs in this phase.

A builder should not start by replacing all of dashboard.html.j2. The narrow data guards and qualified reading contract precede visual migration, so the new layout cannot copy misleading legacy meanings.

## 5. Performance and rendering

Future programme targets: LCP≤2.5s, INP≤200ms and CLS≤0.1 at p75, assessed separately for mobile and desktop. They are budgets, not measured results from this phase.

Retain server-rendered useful content; hydrate only the necessary interactions. Reserve chart/skeleton dimensions to avoid shifts. Lazy mount hidden heavy charts and Command fragments; do not preload all routes, fourteen workspaces or all Odds matrices. Bound subscriptions and listeners, clean them up on route/overlay changes and prevent duplicated host/embedded handlers. Shared primitives should not force a second plotting bundle.

Measure the deployed path at the accepted release. Separate transferred bytes, server timing, data fetch, main-thread work and chart mount costs before setting a new asset budget. Keep large Odds matrices on the existing data plane. No invented cache TTL or performance score is asserted.

## 6. Accessibility and responsive acceptance

Use the programme's44px house target for important mobile controls. WCAG2.2AA target-size minimum/spacing is24px, with its actual exceptions; do not label44px as that rule. Test normal text contrast≥4.5:1, large text≥3:1, relevant non-text controls/graphics≥3:1 where required, visible focus and non-color state communication. Cite [WCAG target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) and [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html); conduct actual measurements at implementation.

The observed beta meta viewport restricts user scaling. F01 must qualify and repair zoom support on the host; a domain-only CSS fix cannot prove it. Reflow at320CSS pixels /400% zoom except scoped genuinely2D content. Provide accessible chart summaries/data views, real table headings, keyboard-complete dialogs/tabs, input-inclusive focus management, Escape/return and reduced motion.

Light/dark and EN/ZH evidence must be captured on actual rendered content. Existing Paper variants demonstrate design exploration, not automated accessibility compliance or final acceptance.

## 7. Migration, compatibility and rollback

Preserve existing routes, anchors, query parsing and producer/data locations. Use the existing exporter for route projection. Keep eleven fragments excluded as documents; F03 corrects the historical label. Preserve no-JS content and old inbound links through explicit compatible handling approved by their owner.

Roll out one approved archetype/family at a time. A failed shared-template or host change must be revertible through the same authorized source/deployment carrier. Keep the prior known-good template/assets and compatible data contract. If the new consumer cannot validate a snapshot, show retained verified data or typed refusal; do not migrate bad data into a new cache.

Rollback triggers include: lost retained feature/deep link, wrong region/listing, unauthorized payload exposure, overwritten model refusal, inaccessible close/return, whole-page overflow, material performance regression or incompatible source generation. The implementation owner must record exact accepted/release/rollback revisions and served proof; no current release pointer is invented here.

## 8. Review boundary

This is a full Phase 2A product/backend/build specification. It is not an approved migration packet under research/migration_packets, not a RIG approval receipt, and not an implemented or deployed capability. Current candidate state is draft. Final family reference state is **blocked by named foundation/composition/review dependencies**, with concrete data defects requiring revision. Completing this source packet does not waive the remaining Paper, independent review, implementation or served-proof obligations.

