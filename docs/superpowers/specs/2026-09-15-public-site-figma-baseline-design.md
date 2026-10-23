# MastermindX Public Site — Figma 1:1 Baseline and Revamp Design

**Status:** Approved by Chairman on 2026-09-15; baseline construction authorized
**Operation:** `public-site-figma-baseline-20260915-sol-001`  
**Owner:** Sol  
**Repository:** `mastermindx-market-intelligence/macro`  
**Source snapshot:** `15c01bd991f35d0bb2185ee1e608a05df0805803`  
**Skillpack authority:** `mastermindx-market-intelligence/Mastermind@19b6111891ffd742ceec7c96f437a2a890847c92`  
**Skillpack schema:** `mastermind.sol_skillpack.v1`, version `1.0.1`, bootstrap major `1`

## 1. Mission

Create a faithful, editable Figma representation of the current MastermindX anonymous public experience before making any redesign decision. The first accepted artifact is not a concept, moodboard, screenshot collection, or partial reconstruction. It is a frozen **Current / 1:1** design baseline for the four flagship public pages:

1. `https://www.mastermind-x.com/`
2. `https://www.mastermind-x.com/products/market-terminal.html`
3. `https://www.mastermind-x.com/products/mastermind-ai.html`
4. `https://www.mastermind-x.com/products/market-dashboards.html`

Only after the Chairman accepts that baseline may the work duplicate it into a separate **Revamp** design space. Only after the revamp is approved may code change. The existing public pages remain the product authority until that final delivery wave is accepted in production.

### Primary user job

A prospective active investor should immediately understand that MastermindX is a connected market-intelligence desk centered on proactive signals and decision support, then be able to inspect the Terminal, AI and Dashboard product pillars without visual or conceptual discontinuity.

### Machine/design job

Translate the current browser-rendered system into a reusable Figma model that preserves:

- exact page composition and content hierarchy;
- shared tokens, typography, spacing, radii, borders and shadows;
- bilingual English and Chinese states;
- responsive behavior at the actual design breakpoints;
- meaningful navigation and interaction states;
- the public site's semantic motion language;
- honest basis, freshness, preview and illustrative labels;
- enough component structure that a later redesign can be made without redrawing or rediscovering the current system.

### 10/10 end state

A reviewer can place each Figma frame over the corresponding production capture and see the same design, can inspect the layers and understand how it is assembled, can switch language and responsive states without rebuilding the page, and can review the important motion phases in prototypes. The accepted current-state pages are then locked and preserved as the immutable comparison point for the redesign and later code delivery.

## 2. Current capability state

| Capability | State | Evidence / meaning |
|---|---|---|
| Four public pages in production | `PROVEN_LIVE` | Existing user-visible website and hand-authored source pages. |
| Shared public design system in code | `PROVEN_LIVE` | Landing tokens, page chrome, product-page family and motion runtime ship today. |
| Editable Figma baseline | `NOT_BUILT` | No accepted 1:1 Figma reconstruction exists. |
| Motion model in Figma | `NOT_BUILT` | Motion exists in code, not yet as inspectable Figma variants/prototypes. |
| Revamped public-site design | `NOT_BUILT` | Deliberately held until baseline acceptance. |
| Revamp implementation in code | `NOT_BUILT` | Deliberately held until design acceptance and a separate implementation plan. |

## 3. Frozen source manifest

The baseline is anchored to one repository commit so a moving live site cannot silently redefine “1:1” during construction.

| Surface | Repository path | Blob SHA at source snapshot |
|---|---|---|
| Homepage | `site/index.html` | `83dc2cdef25f2869465f8492f45aab28a736dd67` |
| Market Terminal | `site/products/market-terminal.html` | `422d942ad5f8a0d785fd790ddeaab1028cf2845b` |
| Mastermind AI | `site/products/mastermind-ai.html` | `62bb247e3b381e5fa1f250653f37c510afdc1e19` |
| Market Dashboards | `site/products/market-dashboards.html` | `2e190241ab91a87be145bdad398f534c28dbe85e` |
| Shared landing design | `site/landing.css` | `4866885b4abd7fe2da059392c7bc46a703892970` |
| Motion controller | `site/scene-motion.js` | `ea9d810805393ce4d241a28534ee5526f7f9ddda` |
| Motion styling | `site/scene-motion.css` | `4731bb71ef7caba99a3ec9b7905c35c5fbe439e0` |

The live URLs and the Chairman-provided full-page homepage capture are visual evidence against this source snapshot. If live production and source differ, the discrepancy is recorded rather than averaged away:

- repository source owns implementation intent and exact authored values;
- current live rendering owns what users actually see;
- the baseline records any material difference and identifies which state is represented;
- no silent “cleanup” is allowed in **Current / 1:1**.

## 4. Scope

### Phase 1 included

- Full-page desktop and mobile reconstruction of all four flagship pages.
- Shared public navigation, dropdown panels, settings control, footer and CTA patterns.
- Homepage hero, Terminal band, Prophet belt, feature bands, AI section, pricing area and closer.
- Product-page chapter ribbons, heroes, artifacts, alternating feature sections, honesty stations and closers.
- English and Chinese visual states.
- Responsive composition at canonical desktop, laptop/tablet and mobile sizes.
- Important hover, focus, open, selected, expanded, language and mobile-menu states.
- Semantic motion phases and representative prototype sequences.
- A native Figma component/variable layer sufficient for later editing.
- Locked production captures used as comparison references.

### Explicit non-goals during baseline construction

- No new visual direction.
- No copy rewrite or product repositioning.
- No removal, addition or consolidation of sections.
- No code, template, stylesheet, JavaScript, asset, navigation or production change.
- No attempt to reconstruct every public page outside the four flagship URLs.
- No replacement lifecycle, design-system or source-of-truth plane.
- No invented live data, product claim, price, result, freshness state or interaction.
- No conversion of illustrated or delayed product examples into claims of live data.

The broader anonymous estate may be added after the four-page baseline is accepted, but it cannot block the flagship reconstruction or authorize redesign before the flagship gate passes.

## 5. Chosen reconstruction approach

### Chosen: dual-track capture plus native rebuild

Each page is represented in Figma in two forms:

1. **Locked reference capture** generated from the live page and/or the frozen source preview.
2. **Editable native reconstruction** built with Figma frames, text, vectors, auto layout, variables, components and variants.

The capture is evidence, not the deliverable. It remains hidden or locked beneath the editable frame for overlays and difference review.

For the first capture of each page, the Figma web-capture path supplies the pixel-accurate reference. The editable path is built separately through Figma's design API and refined against that reference. This avoids both failure modes:

- screenshot-only files that cannot support redesign;
- hand-built interpretations that drift because the operator cannot compare them against the actual page.

### Rejected: screenshot-only mockup

A screenshot is not a design model. It cannot expose component structure, tokens, language variants, responsive behavior or motion states and would force rediscovery during the revamp.

### Rejected: redesign directly from source

Starting with improvements before a baseline exists makes every later comparison subjective, risks deleting strengths of the current site, and prevents a clean determination of what actually changed.

### Rejected: automatic one-click HTML conversion as the final artifact

HTML-to-Figma capture may preserve pixels but typically produces brittle, anonymous layer trees. It is useful as reference evidence, not as the final editable system. Shared structures must be normalized into understandable components after capture.

## 6. Figma file architecture

The working file is named:

`MastermindX Public Site — Current 1:1 + Revamp`

The authenticated Figma plan and destination are resolved through the current Figma account at implementation time; no team, project or permission is guessed.

### Pages

| Page | Purpose |
|---|---|
| `00 — Read Me & Acceptance` | Authority pins, source manifest, status, review instructions, deviation ledger and acceptance matrix. |
| `01 — Foundations` | Variables, color roles, typography, grid, spacing, radius, border, shadow and motion timing primitives. |
| `02 — Components` | Shared chrome, buttons, chips, labels, cards, tabs, tables, browser frames, page furniture and responsive variants. |
| `10 — Current · Homepage` | Editable homepage baseline and canonical responsive/language frames. |
| `11 — Current · Market Terminal` | Editable Terminal product-page baseline. |
| `12 — Current · Mastermind AI` | Editable AI product-page baseline. |
| `13 — Current · Market Dashboards` | Editable Dashboards product-page baseline. |
| `20 — Motion & Interaction` | Phase variants, prototype flows, dropdowns, language switching, mobile menu and representative scene sequences. |
| `90 — Reference Captures` | Locked production/source captures, crops and overlay comparison frames. |
| `99 — Revamp` | Initially locked and empty except for a gate notice. Populated only after baseline acceptance. |

### Layer and component naming

Names must describe product meaning rather than visual accident. Examples:

- `Chrome/Nav/Desktop`
- `Chrome/Nav/Mobile`
- `Hero/SignalCard`
- `Terminal/BrowserFrame`
- `AI/ConversationWindow`
- `Dashboards/DeskTile`
- `Label/Basis/Delayed`
- `Label/Honesty/Illustrative`
- `Scene/Phase=Observe`

Generated names such as `Frame 482`, `Group 37`, or anonymous import names are not accepted in the reusable layer. They may remain only inside the locked capture references.

## 7. Foundations and token model

Figma variables reproduce the current design roles, not merely sampled colors. The code remains canonical for authored values during the baseline.

### Core color roles

- page field and panel hierarchy;
- four stroke tiers: weak, default, defined and strong;
- ink, soft ink, muted and faint text;
- house blue, violet and teal;
- semantic green, gold, red and blue;
- blue, green, red and gold washes;
- dark product plate;
- focus-ring and dark-band focus values.

Direction-sensitive market colors remain semantically separate from generic success/error states. Chinese red-up/green-down behavior is preserved where the current page uses it; health or honesty states must not be reinterpreted as market direction.

### Typography

- Display and figure voice: San Francisco on Apple systems, with Inter as the cross-platform fallback represented in Figma.
- Body voice: Inter.
- Instrument labels: system mono/SF Mono equivalent.
- Chinese fallback: PingFang SC or the available platform-equivalent CJK face.

No font file is added to the repository or shared from the host. Figma uses available licensed/platform fonts. A font substitution that changes line wrapping is a recorded deviation and must be corrected with an approved available fallback rather than by changing copy.

### Spatial system

The Figma variable layer records the current spacing, radii, content width and gutters as named roles. It also records layered shadow roles for cards, lifted vignettes, floating hero artifacts, stages and dark plates. A flat single-shadow approximation is not sufficient where the existing composition uses layered depth.

## 8. Responsive and language matrix

Every flagship page receives these canonical frames:

| View | Width | Languages | Purpose |
|---|---:|---|---|
| Desktop | 1440 px | EN + ZH | Primary full-fidelity reference and section rhythm. |
| Laptop/tablet | 1024 px | EN | Breakpoint integrity, grid collapse and navigation behavior. |
| Mobile | 390 px | EN + ZH | Canonical phone design floor and Chinese wrapping. |

Additional 375 px and 320 px checks are QA probes, not separate full-page deliverables unless they reveal a material layout state not represented at 390 px.

Acceptance requires:

- the same authored line breaks at 1440 px where the page uses explicit breaks;
- equivalent natural wrapping at 390 px;
- no horizontal overflow;
- no clipped label, CTA, price, card or browser artifact;
- correct section ordering and alternating layout behavior;
- correct mobile menu and collapsed navigation treatment;
- Chinese state that is designed, not merely translated text pasted into English geometry.

## 9. Page-specific reconstruction contract

### Homepage

The baseline preserves the complete page order and its product thesis:

1. public navigation and hero;
2. connected intelligence/card field;
3. dark Terminal product band;
4. Prophet/card belt;
5. alternating feature narratives and illustrated evidence;
6. Mastermind AI analyst band;
7. pricing/tier area and matrix;
8. closing band and footer.

The current flagship proposition remains intact: proactive Prophet signals and connected intelligence, not a generic research-tool landing page. The baseline cannot reinterpret the hierarchy to emphasize AI chat, dashboards or manual research above the present product story.

### Market Terminal

Preserve the blue-accent chapter, full browser artifact, delayed-basis honesty, watchlist rail, chart/indicator systems, dossier, signal read, options and AI sections. Product illustrations remain illustrative where the source labels them as such.

### Mastermind AI

Preserve the violet-accent chapter, grounded conversation artifact, receipts/citations, page-aware research context, stance separation and its section-specific motion. The baseline may not imply that an LLM independently ranks, sizes, gates or originates trades.

### Market Dashboards

Preserve the teal-accent chapter, desk wall, regime, lanes, rotation, filings, flow, China, record, beyond and nightly scenes. Dense dashboard miniatures remain structured product evidence rather than decorative generic charts.

## 10. Motion and interaction architecture

The source motion system is semantic. Its canonical phases are:

1. `idle`
2. `observe`
3. `reason`
4. `resolve`
5. `hold`
6. `reset`

The controller currently uses approximately:

- observe: 1250 ms;
- reason: 1750 ms;
- resolve: 1900 ms;
- hold: 3200 ms;
- reset: 500 ms.

Figma represents motion in two layers.

### Inspectable phase variants

Every meaningful scene gets component or frame variants for at least `idle`, `observe`, `reason`, `resolve`, and `hold`. These variants expose what changes and why: row arrival, scan, comparison, gauge movement, route drawing, stance resolution, citation appearance or product output.

### Representative prototype sequences

Prototype flows demonstrate the important narrative sequences without pretending Figma is the production runtime. At minimum:

- homepage hero/field arrival;
- Terminal chart plus intelligence-card resolution;
- AI question → evidence/receipt → stance answer;
- Dashboard observe → cross-check → resolve sequence;
- navigation dropdown open/close;
- settings/language switch;
- mobile navigation;
- pricing period selection where present.

Continuous ambient loops, data refreshes and intersection-observer timing remain implementation behavior. Figma models their meaningful states and transition intent rather than rebuilding a second animation engine.

### Static and accessibility states

Every animated component has a useful settled state matching the source's reduced-motion, Save-Data and `?still` behavior. The static state cannot be blank, half-built or dependent on autoplay.

## 11. Truth, data and correction behavior

The Figma baseline is a time-stamped product snapshot, not a live data consumer.

- Visible prices, scores, tickers and chart geometry reproduce the frozen source or production capture.
- Delayed, end-of-day, preview, illustrative and scripted-demo labels remain attached to the evidence they qualify.
- Basis and freshness labels cannot be removed because they look visually noisy.
- Null or unavailable states remain explicit where the source represents them.
- No number is updated merely because newer production data exists during reconstruction.
- A correction to the source snapshot is recorded as a new baseline revision, not silently painted over.

## 12. Fidelity and acceptance gates

A page is not complete merely because it looks broadly similar.

### Structural gate

- Every current section is present, in current order.
- Shared navigation, footer, CTA and settings structures are represented as components.
- Editable layers are grouped and named by meaning.
- No entire product vignette is flattened into a raster image.
- Reference captures are separate, locked and clearly labeled.

### Visual gate

At 1440 px and 390 px:

- text content and hierarchy match;
- typography size, weight, line height and wrapping match;
- section boundaries, grids and component bounds target ±2 px of the reference;
- any deviation larger than 2 px is documented and reviewed rather than hidden;
- token colors, borders, radii and shadow roles match authored values;
- no obvious difference remains at 100% zoom in a 50% opacity overlay review.

Minor antialiasing differences between browser and Figma text rendering are not defects when bounds, wrap and weight match. Font substitution that changes geometry is a defect.

### Responsive gate

- No horizontal overflow at 390 px.
- Desktop-only annotations disappear where the source removes them.
- Grids collapse in the same order and maintain the same information hierarchy.
- Navigation and settings states are usable at desktop and mobile sizes.
- Chinese text does not clip or force a different section hierarchy.

### Motion gate

- Each source scene has a mapped settled state.
- Major scenes have inspectable semantic phase variants.
- Representative prototypes communicate the same observe/reason/resolve story.
- Reduced-motion/static proof is complete.

### Comparison evidence

For each flagship page, acceptance evidence includes:

- production/source reference capture;
- editable Figma screenshot at the same viewport;
- overlay or difference frame;
- desktop EN and ZH proof;
- mobile EN and ZH proof;
- motion-state/prototype proof;
- recorded deviations, with zero unexplained deviations at freeze.

## 13. Work waves

### Wave 0 — capture and manifest freeze

- Resolve the Figma plan and create the working file.
- Record the source manifest and production capture timestamp.
- Capture all four pages at canonical desktop/mobile states.
- Record live/source differences.

**Exit:** reference page is complete, locked and reproducible.

### Wave 1 — foundations

- Create variables for colors, type roles, spacing, radii, strokes, shadows and motion timing.
- Build grids and responsive frame templates.

**Exit:** foundations can reproduce a representative section without local literal drift.

### Wave 2 — shared chrome and components

- Build navigation, dropdowns, settings, buttons, chips, labels, card shells, browser frames, feature section anatomy and footer.
- Add desktop/mobile and EN/ZH variants where geometry changes.

**Exit:** all four pages can assemble from one shared chrome/component system.

### Wave 3 — homepage baseline

- Reconstruct the homepage top to bottom.
- Add canonical desktop/mobile and bilingual frames.
- Compare and close deviations.

**Exit:** homepage passes all structural, visual and responsive gates.

### Wave 4 — product-page baselines

- Reconstruct Terminal, AI and Dashboards using the shared family.
- Preserve each product's accent, artifact and feature anatomy.

**Exit:** all three pass structural, visual and responsive gates.

### Wave 5 — motion and interaction

- Build phase variants and representative prototypes.
- Build nav, settings, language and mobile interaction states.
- Add static/reduced-motion states.

**Exit:** motion gate passes for all four pages.

### Wave 6 — baseline freeze

- Run the full acceptance matrix.
- Resolve or adjudicate every deviation.
- Lock and label Current pages as `Accepted 1:1` with source commit and date.

**Exit:** explicit Chairman acceptance of the baseline.

### Wave 7 — revamp design

- Duplicate accepted current frames into `99 — Revamp`.
- Define the improvement thesis and alternatives against the preserved baseline.
- Design and review the upgrade without changing the accepted current pages.

**Entry gate:** Wave 6 accepted. This specification does not pre-approve the revamp direction.

### Wave 8 — code delivery

- Write a separate implementation plan against current repository truth.
- Reconcile open PR collisions and updated production behavior.
- Implement one useful capability per PR where practical.
- Prove in a real browser through production paths.

**Entry gate:** Revamp design explicitly accepted. Code changes are outside this baseline design specification.

## 14. Collision and change control

The site and its landing family continue to evolve while the Figma baseline is built. Therefore:

- The baseline remains pinned to the manifest in Section 3.
- Later repository commits do not silently move the target.
- Material product corrections may trigger an explicit baseline revision after review.
- Active PRs touching landing copy, mobile overflow, chrome, pricing, motion or product pages are reconciled before any Revamp-to-Code work begins.
- Figma work does not authorize merging, closing or superseding existing code work.
- One Figma file is the design carrier for this operation; no parallel current-state file is created unless the first becomes inaccessible and its effect is reconciled.

## 15. Failure handling

| Failure | Required behavior |
|---|---|
| Live page differs from frozen source | Record both, identify material difference, choose the represented state explicitly. |
| Figma capture fails on animation or lazy content | Use a controlled source preview or static `?still` state and record capture conditions. |
| Imported layers are unusable | Keep them only as locked reference and rebuild native components. |
| Required font is unavailable | Use the approved fallback, measure wrapping, record any unresolved geometry. |
| Browser/Figma text antialiasing differs | Judge bounds, wrap, weight and hierarchy; do not distort typography to match raster noise. |
| A page changes during work | Keep current baseline pinned; evaluate the change as a later revision, not an implicit target change. |
| A motion loop cannot be reproduced exactly in Figma | Preserve semantic states, timing intent and representative prototype; do not build a duplicate runtime. |
| Permissions or Figma destination are unclear | Stop at the exact access gate; do not guess a team or create duplicate files in multiple plans. |

## 16. Completion and stop conditions

The baseline is complete only when:

1. all four pages exist as editable native Figma frames;
2. the desktop/mobile and bilingual matrix is present;
3. shared foundations and components are reusable;
4. meaningful motion phases and interactions are inspectable;
5. comparison evidence is attached;
6. every material deviation is closed or explicitly accepted;
7. the Current pages are locked and marked with the frozen source commit;
8. the Chairman explicitly accepts the Current / 1:1 baseline.

Until all eight are true, the capability state remains `PARTIAL` and the Revamp page remains locked. Acceptance of this specification authorizes construction of the baseline, not redesign and not production code changes.

## 17. Exact next action after specification approval

Create the single Figma working file in the authenticated plan, establish the page architecture above, and capture the four frozen public pages into `90 — Reference Captures`. Then build `01 — Foundations` from the source tokens before reconstructing the homepage. The first review checkpoint is the completed foundations plus shared chrome and one fully reconstructed homepage hero—not a redesign concept.
