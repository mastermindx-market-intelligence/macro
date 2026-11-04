# Responsive, accessibility and visual requirements

F01-F02-SHELL/1.0.0-candidate.4 and F02-SYSTEM/1.0.0-candidate.2 are consumed provisionally. Final shared design acceptance is held. Values below are the inspected candidate contracts, not a claim that the foundation has shipped. [S08](SOURCE_EVIDENCE.md#s08--shared-foundation-candidates)

## 1. Container geometry

| Viewport | Navigation | Header | Content gutters | Useful width | Inspector behavior |
|---:|---:|---:|---:|---:|---|
| 320 | Modal, 0 when closed | 56 | 16 each | 288 | Fullscreen; body remains one column |
| 390 | Modal, 0 when closed | 56 | 16 each | 358 | Fullscreen; safe areas and visible close/return |
| 768 | Modal, 0 when closed | 56 | 20 each | 728 | 440 modal, focus trapped; no dock |
| 1024 | 196 expanded | 64 | 20 each | 788 | 440 modal; backdrop prevents background interaction |
| 1280 | 224 expanded | 64 | 24 each | 1008 | Dock possible: 664 primary + 24 gap + 320 inspector |
| 1440 | 224 expanded | 64 | 24 each | 1168 | 824 primary + 24 gap + 320 inspector |
| 1600 | 224 expanded | 64 | 24 each | 1328 | 984 primary + 24 gap + 320 inspector |

Expanded navigation is 224 at >=1200 and 196 above 860 below 1200. <=860 uses modal navigation. Explicit compact navigation is 72; do not auto-compact it to make an inspector fit.

Generic dock eligibility requires useful width >=984: 640 minimum primary + 24 gap + 320 inspector. Expanded-nav viewport threshold is therefore 1256; compact-nav threshold 1096. Domain content can require more; measure the container rather than copying a viewport breakpoint. At 1280, the leadership table retains exact values and may remove redundant bars below 760 primary width. If a chosen view needs a wider primary, use the modal inspector instead of truncating columns.

A04 proves the 1024 modal composition; A01 the 1440 dock; A05 the 768 single-column taxonomy; A03/A02 390 regional/cycle flows; A08 320 ZH states; A10 1280 dense flows; A09 1600 documentation layout. These are representative Paper compositions, not a complete seven-width browser proof.

## 2. Density and reflow

- Page heading 28px desktop/26px phone by default; body 14px; data table 13px; metadata 12px. Retained R4 hero may be larger. Use Inter with tabular figures; PingFang SC fallback for ZH.
- Desktop compact rows can be 40px when no tiny standalone control requires a larger hit area. Standard/interactive rows use 52px. Important touch controls are at least 44px in the programme's house standard.
- At 320/390, show selected period + entity/return/source, with accessible full-table and period controls. Do not shrink eight horizons into unreadable text.
- Dense heatmap/flow tables may scroll inside an explicitly labelled region with a pinned entity column. The page itself must not acquire horizontal overflow.
- Charts have a labelled exact-value table and meaningful textual summary. On phones, preserve a selected-coordinate list and optional chart/fullscreen; provide pan/zoom controls without requiring a gesture.
- Long EN names, ZH labels, negative signs, missing values and large numbers must be fixture-tested. Truncate only with a full-name reveal accessible to keyboard and touch.
- No fixed-height panel may clip error copy, expanded methods, 200% text or localized controls. Paper's fit-content candidates are specifications for flexible implementation, not fixed screenshots to scale down.

## 3. Tokens and state signals

| Role | Light | Dark |
|---|---|---|
| Canvas | #f6f6f3 | #080808 |
| Navigation | #efefec | #0c0c0c |
| Panel | #ffffff | #121212 |
| Raised | #f0f0ed | #191919 |
| Selected | #e2e2dc | #292929 |
| Primary text | #1a1c20 | #f3f3f3 |
| Secondary text | #51555b | #b8b8b8 |
| Divider | #cbccc7 | #343434 |
| Control border | #85877f | #6f6f6f |
| Accent | #66543b | #c9b99b |
| Link | #235b8e | #a7c9f1 |

Light price up/down roles are #256341/#a62d43; regional price convention belongs to F02's semantic mapping, not a global recoloring of meaning. Flow positive/negative uses invariant blue/purple roles, including dark #70cbdc/#d9a6ef; a locale change must not reverse inflow/outflow. Always show signed text and units.

Selection, focus, entry state, missingness, stale data, price direction and flow direction are distinct channels. No colored container stripe is needed. A focused company action has a clear outline, not merely a color change.

Paper R4 had no shared tokens; explicit role values are provisional. F02's shared file and original tokens were not edited. Source implementation must bind accepted token names when released, not establish a D05 token fork.

## 4. Keyboard, screen reader and touch

- One page H1, landmarks, descriptive section headings and skip link to content. Heading hierarchy reflects task hierarchy, not arbitrary card styling.
- Native buttons/links for actions. Every icon-only control has a localized accessible name; “View” includes the entity in its accessible label.
- Visible focus remains within the viewport and is not covered by sticky headers or modal chrome. Escape closes a modal and returns focus to its opener; preserve scroll.
- Modal inspector: dialog semantics, labelled title, focus containment, background inertness and deterministic return. Docked inspector: non-modal complementary region, no focus trap.
- Taxonomy tree: arrows navigate/expand/collapse, Home/End, Enter opens; search announces result count and preserves ancestors. Empty child list, unavailable proxy coverage and no result are different states.
- Data tables: real headers, scope, sort state, keyboard-sort actions, unit/currency caption, selected-row state. Row action targets remain reachable when horizontally scrolled.
- Chart: keyboard-select points/series, announce date/value/unit once, table alternative, no hover-only source information.
- Announce loading/error/save status politely without reading every live number or moving focus on refresh. Urgent form errors are associated with their control.
- Touch: 44px major targets, enough spacing, inline charts allow page scroll; fullscreen gesture capture has a visible exit and accessible buttons.
- Reduced motion: static selection and no numeric tween. Otherwise short approximately 120ms state changes; motion never delays access to evidence.
- At 200% zoom and narrow reflow, no loss of action, label or exact-value alternative. Instrumental contrast and assistive-technology proof remain required on the built surface.

## 5. Locale and accessibility proof matrix

For the primary journey and high-risk states, verify EN/light, EN/dark, ZH/light and ZH/dark at 1440 and 390. Add 320 ZH long-copy, 768 keyboard tree, 1024 modal, 1280 dense flow, and 1600 expanded density. Cover keyboard-only, touch-only, reduced motion and 200% zoom.

Source dates retain calendar meaning across locale. Localize labels and month names, not observation identity. Separate date precision: month-only historical projection cannot become a precise day. Keep the inherited 来源抽屉 pointer unbroken at 1440/390.

Contrast verification must measure actual painted heatmap/table substrates with text and focus indicators. A token calculation or a screenshot impression cannot discharge SIC-APR-01. Do not claim WCAG conformance from this design package.

## 6. Performance and resilience targets

Targets, not measured results: stable first meaningful shell; SSR scope/date where source available; lazy heavy series/narratives/DNA; only visible-view mounts; no duplicate event handlers; coherent request cancellation/fencing; no layout shift when a late source arrives; bounded lists/virtualization only when access and keyboard semantics survive.

Keep native payload splitting and defer chart mount until visible/nonzero width. Do not set arbitrary freshness TTLs or add a second polling mechanism. Measure actual bytes, render time, interaction responsiveness and memory during the implementation gate before setting release budgets.

