# MastermindX Public Site Figma Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and acceptance-prove a fully editable, bilingual, responsive Figma baseline of the current MastermindX homepage and three flagship public product pages before any redesign or production code change.

**Architecture:** Use one Figma Design file with locked browser captures as evidence and separate native Figma foundations, components, page frames, and motion-state variants as the editable deliverable. Pin every comparison to `macro@15c01bd991f35d0bb2185ee1e608a05df0805803`; the Figma file is the only design carrier, while GitHub stores the immutable specification, execution plan, source manifest, and completion handoff.

**Tech Stack:** Figma Design, Figma MCP (`create_new_file`, `generate_figma_design`, `use_figma`, metadata/screenshot tools), Figma Plugin API, HTML/CSS/JavaScript source in `mastermindx-market-intelligence/macro`, GitHub branch `sol/public-site-figma-baseline-spec-20260915`.

**Spec:** `docs/superpowers/specs/2026-09-15-public-site-figma-baseline-design.md`

## Global Constraints

- Baseline source is frozen at `15c01bd991f35d0bb2185ee1e608a05df0805803`; later live/source changes do not silently move the target.
- Included surfaces are exactly `/`, `/products/market-terminal.html`, `/products/mastermind-ai.html`, and `/products/market-dashboards.html`.
- No redesign, copy rewrite, product repositioning, code change, template change, stylesheet change, JavaScript change, navigation change, deployment, or production write is authorized during baseline construction.
- The Figma file is named `MastermindX Public Site — Current 1:1 + Revamp` and is created once in the authenticated plan `team::1679263159873159004`.
- `99 — Revamp` remains locked and contains only a gate notice until Chairman acceptance of the complete Current / 1:1 baseline.
- Canonical frame widths are 1440 desktop, 1024 laptop/tablet, and 390 mobile; 375 and 320 are QA probes.
- Desktop and mobile require English and Chinese proof; 1024 requires English proof.
- Figma reconstruction uses editable native nodes, auto layout, variables, styles, components, instances, and variants. Raster captures are locked evidence only.
- Every created or mutated Figma node ID is returned by the tool call that creates or mutates it.
- Every `use_figma` call changes at most one page and performs no more than ten logical operations; complex construction is incremental and validated after each step.
- Text mutations load the exact font before mutation. No font files are copied, uploaded, committed, or shared.
- Colors use 0–1 Figma Plugin API channels. Paint arrays are cloned and reassigned. Variable scopes are explicit.
- Shared semantic roles remain distinct: market direction, success/error, honesty, basis/freshness, preview, illustrative, and lock/tier states cannot be collapsed.
- Meaningful motion is represented as inspectable `idle`, `observe`, `reason`, `resolve`, and `hold` states plus representative prototypes; Figma does not become a duplicate runtime.
- Every animated scene has a settled reduced-motion/static state.
- Completion requires structural, visual, responsive, bilingual, interaction, and motion evidence with zero unexplained material deviations.

---

### Task 1: Create the single Figma carrier and page architecture

**Files:**
- Create in Figma: `MastermindX Public Site — Current 1:1 + Revamp`
- Modify: `docs/superpowers/specs/2026-09-15-public-site-figma-baseline-design.md`
- Create: `docs/design/public-site-figma-baseline-handoff.md` at final closeout

**Interfaces:**
- Consumes: approved specification and Figma plan key `team::1679263159873159004`.
- Produces: one Figma `fileKey`, file URL, and exact page IDs for all later tasks.

- [ ] **Step 1: Update the specification status to approved**

Replace the status line with:

```markdown
**Status:** Approved by Chairman on 2026-09-15; baseline construction authorized
```

Keep every scope and gate unchanged.

- [ ] **Step 2: Create the Figma Design file**

Call `create_new_file` exactly once with:

```json
{
  "planKey": "team::1679263159873159004",
  "fileName": "MastermindX Public Site — Current 1:1 + Revamp",
  "editorType": "design"
}
```

Record `file_key` and `file_url`. Do not create another file after any timeout or ambiguous response without reconciling the first call.

- [ ] **Step 3: Inspect the blank file**

Call `get_metadata` without a node ID. Expected: one default page and no pre-existing product screens or local design-system content.

- [ ] **Step 4: Create and order the ten canonical pages**

Use one `use_figma` call on the default page to rename it and create the remaining pages in this exact order:

```text
00 — Read Me & Acceptance
01 — Foundations
02 — Components
10 — Current · Homepage
11 — Current · Market Terminal
12 — Current · Mastermind AI
13 — Current · Market Dashboards
20 — Motion & Interaction
90 — Reference Captures
99 — Revamp
```

Return all page IDs. Create a locked gate notice frame on `99 — Revamp` reading:

```text
LOCKED — Current / 1:1 baseline acceptance required before redesign.
Source: macro@15c01bd991f35d0bb2185ee1e608a05df0805803
```

- [ ] **Step 5: Validate page architecture**

Call `get_metadata` without a node ID and assert exact page order and names. Take a screenshot of the gate notice frame.

- [ ] **Step 6: Commit repository status change**

Commit only the approved status update and this implementation plan on the existing branch.

**Acceptance:** one Figma file exists, all canonical pages exist in the specified order, the Revamp gate is visible and locked, and no production or site source path changed.

---

### Task 2: Build the authority, manifest, and acceptance page

**Files:**
- Figma page: `00 — Read Me & Acceptance`
- Source references: `site/index.html`, `site/products/market-terminal.html`, `site/products/mastermind-ai.html`, `site/products/market-dashboards.html`, `site/landing.css`, `site/scene-motion.js`, `site/scene-motion.css`

**Interfaces:**
- Consumes: Figma page ID from Task 1 and frozen source/blob SHAs from the specification.
- Produces: read-me frame ID, manifest frame ID, acceptance matrix frame ID, deviation-ledger frame ID.

- [ ] **Step 1: Create the page wrapper and four placeholder sections**

Create a 1440px vertical auto-layout wrapper named `Read Me / Public Site Baseline`, positioned at clear canvas space. Add placeholder sections named:

```text
Authority & Mission
Frozen Source Manifest
Acceptance Matrix
Deviation Ledger
```

Each placeholder uses current page/panel colors and is marked `placeholder=true` until populated.

- [ ] **Step 2: Populate Authority & Mission**

Add the operation ID, repository, source commit, Skillpack commit, approved scope, explicit non-goals, and Current-before-Revamp gate. Use concise visible copy; no hidden instructions.

- [ ] **Step 3: Populate Frozen Source Manifest**

Create a table with these exact rows:

```text
Homepage | site/index.html | 83dc2cdef25f2869465f8492f45aab28a736dd67
Market Terminal | site/products/market-terminal.html | 422d942ad5f8a0d785fd790ddeaab1028cf2845b
Mastermind AI | site/products/mastermind-ai.html | 62bb247e3b381e5fa1f250653f37c510afdc1e19
Market Dashboards | site/products/market-dashboards.html | 2e190241ab91a87be145bdad398f534c28dbe85e
Landing CSS | site/landing.css | 4866885b4abd7fe2da059392c7bc46a703892970
Motion JS | site/scene-motion.js | ea9d810805393ce4d241a28534ee5526f7f9ddda
Motion CSS | site/scene-motion.css | 4731bb71ef7caba99a3ec9b7905c35c5fbe439e0
```

- [ ] **Step 4: Populate Acceptance Matrix**

Create rows for all four pages and columns:

```text
1440 EN | 1440 ZH | 1024 EN | 390 EN | 390 ZH | Motion | Overlay | Deviations
```

Initialize every cell to `NOT STARTED`. Use no green/pass styling before proof exists.

- [ ] **Step 5: Populate Deviation Ledger**

Create columns:

```text
ID | Surface | State | Reference | Figma | Delta | Cause | Disposition | Owner
```

Add one starter row `DEV-000 / NONE RECORDED / OPEN FOR DISCOVERY`. The ledger must not say zero deviations until comparison is complete.

- [ ] **Step 6: Validate and screenshot**

Take a screenshot of the full read-me wrapper and verify all four section names, source rows, and acceptance columns through metadata.

**Acceptance:** a fresh reviewer can recover the mission, authority, frozen inputs, current status, and exact acceptance debt without this chat.

---

### Task 3: Capture the four public pages as locked reference evidence

**Files:**
- Figma page: `90 — Reference Captures`
- External URLs: the four approved public URLs

**Interfaces:**
- Consumes: single Figma file key and `90 — Reference Captures` page ID.
- Produces: capture node IDs and capture-condition labels for each page.

- [ ] **Step 1: Create the reference capture index**

Create four sections named:

```text
Reference / Homepage
Reference / Market Terminal
Reference / Mastermind AI
Reference / Market Dashboards
```

Inside each, create lanes for `1440 EN`, `1440 ZH`, `1024 EN`, `390 EN`, and `390 ZH`, plus a source/capture-condition label.

- [ ] **Step 2: Start one browser capture per URL**

For each URL, call `generate_figma_design` against the same file key, targeting the reference page or the corresponding section. Record each single-use `captureId`. Do not reuse a capture ID.

- [ ] **Step 3: Complete capture in a controlled browser state**

Capture the stable state using the live URL with `?still=1&lang=en` or `?still=1&lang=zh` where supported. For each viewport, record:

```text
URL
viewport width and height
language
motion state (`still=1` or resolved)
capture UTC timestamp
source commit
```

If the capture tool cannot set viewport variants directly, capture the canonical desktop page once, then use browser-controlled screenshots and `upload_assets` for additional evidence frames. Do not substitute a scaled desktop screenshot for a mobile render.

- [ ] **Step 4: Poll each capture**

Poll each `captureId` every five seconds, at most ten times, until `completed`. On timeout, preserve the status and reconcile before starting a replacement capture.

- [ ] **Step 5: Lock and label all capture outputs**

Move/import outputs into their named reference sections, lock every capture subtree, prefix imported capture names with `CAPTURE —`, and prevent them from being mistaken for editable design.

- [ ] **Step 6: Validate capture completeness**

Screenshot each reference section. Confirm all four URLs have a desktop stable capture and at least one mobile render before native page reconstruction begins.

**Acceptance:** every page has locked, source-stamped visual evidence; any missing viewport/language state is explicit, not silently represented by scaling.

---

### Task 4: Create foundation variables and specimen boards

**Files:**
- Figma page: `01 — Foundations`
- Source: `site/landing.css`

**Interfaces:**
- Consumes: `01 — Foundations` page ID and frozen CSS roles.
- Produces: local variable collections, text styles, effect styles, and specimen frame IDs used by all components and pages.

- [ ] **Step 1: Inspect local and linked design-system state**

Run read-only `use_figma` discovery for local variable collections, styles, and components. Because this is a new file, record existing screens as `N/A — blank file`. Call `get_libraries`; do not import unrelated community design systems.

- [ ] **Step 2: Create variable collections**

Create collections:

```text
Color / Public Site
Space / Public Site
Radius / Public Site
Stroke / Public Site
Motion / Public Site
```

Create light/default modes only for the current light-only public family, with explicit variable scopes.

- [ ] **Step 3: Create exact color-role variables**

Create and set variables for:

```text
field/bg #F7F8FA
surface/panel #FFFFFF
surface/panel-2 #FBFCFD
stroke/weak #F0F2F5
stroke/default #EAECF0
stroke/defined #DFE3E9
stroke/strong #CFD6DF
text/ink #1C2430
text/ink-soft #34404F
text/muted #5D6B7E
text/faint #5F6A7A
brand/blue #285FFF
brand/blue-ink #1C47CC
brand/blue-lit #3F74FF
brand/violet #7862E0
brand/teal #0F9D8F
semantic/up #1F8B41
semantic/caution #B07D05
semantic/down #C12F2F
semantic/info #2F63C4
wash/blue #EEF2FF
wash/green #E9F5EC
wash/red #FAECEB
wash/gold #FAF3E2
plate/dark #0B1120
focus/default #285FFF
focus/on-dark #6EA8FF
```

- [ ] **Step 4: Create spatial and motion variables**

Create named variables for radii `6/12/16/20`, max width `1280`, canonical gutters, key section spacing, and motion timings `1250/1750/1900/3200/500` milliseconds. Spacing variables use `GAP` and padding-compatible scopes; radius variables use corner-radius scope.

- [ ] **Step 5: Create text and effect styles**

Create text styles for display hero, section title, feature title, body, body strong, mono kicker, label, microcopy, and figure. Create layered effect styles corresponding to card, lift, float, stage, and dark plate shadows.

- [ ] **Step 6: Build foundation specimen boards**

Create editable specimen boards for colors, typography, spacing/radii, strokes, shadows, honesty labels, basis labels, and motion timing. Bind every specimen to variables/styles rather than local literals.

- [ ] **Step 7: Validate variables and specimens**

Return all variable collection/variable/style IDs. Use metadata to verify collection names/counts and screenshot each specimen board to verify no clipping or fallback-font wrap drift.

**Acceptance:** a representative public-site card and heading can be constructed without hardcoded color, radius, stroke, spacing, or shadow values.

---

### Task 5: Build the shared component system

**Files:**
- Figma page: `02 — Components`

**Interfaces:**
- Consumes: foundation variables/styles from Task 4.
- Produces: local component and component-set keys for shared page assembly.

- [ ] **Step 1: Create component inventory and placeholders**

Create named component groups for:

```text
Chrome/Nav/Desktop
Chrome/Nav/Mobile
Chrome/Nav/Dropdown
Chrome/Settings
Chrome/Footer
Button/Public
Label/Basis
Label/Honesty
Label/Status
Chapter/Ribbon
Section/Feature
Frame/Browser
Card/Signal
Card/DeskTile
AI/ConversationWindow
Pricing/TierCard
```

- [ ] **Step 2: Build public buttons and labels**

Create button variants for primary/secondary and desktop/mobile sizes. Create basis variants `Live`, `15-min delayed`, `End of day`; honesty variants `Preview`, `Illustrative`, `Scripted demo`; and neutral/status variants used by the source. Bind fills, strokes, radii, and text styles to variables.

- [ ] **Step 3: Build navigation and settings components**

Create desktop closed/open dropdown states, mobile closed/open menu states, keyboard-focus states, and settings closed/open states. Preserve three dropdown groups, pricing link, login, primary CTA, and language control.

- [ ] **Step 4: Build content primitives**

Create chapter ribbon, alternating feature section, browser frame, signal card, desk tile, AI conversation window, and tier-card components. Each repeated element is built once and used through instances.

- [ ] **Step 5: Build footer component**

Reconstruct the current footer anatomy and link-column hierarchy. Create desktop and mobile variants without changing IA or copy.

- [ ] **Step 6: Validate component properties**

Inspect component sets and confirm variant/property definitions are legible and non-duplicative. Screenshot each component set at 100% and verify no clipped text.

**Acceptance:** all four pages can be assembled from a common public-site component layer; no major repeated element requires hand-building per page.

---

### Task 6: Reconstruct and prove the homepage baseline

**Files:**
- Figma page: `10 — Current · Homepage`
- Source: `site/index.html`, `site/landing.css`, current homepage capture

**Interfaces:**
- Consumes: foundation variables, component keys, homepage reference captures.
- Produces: homepage wrapper/frame IDs for 1440 EN/ZH, 1024 EN, 390 EN/ZH and comparison frames.

- [ ] **Step 1: Create five homepage wrappers**

Create vertically auto-laid wrappers named:

```text
Homepage / 1440 / EN
Homepage / 1440 / ZH
Homepage / 1024 / EN
Homepage / 390 / EN
Homepage / 390 / ZH
```

Add section placeholders in current order: Nav, Hero, Terminal Band, Prophet Belt, Feature Narratives, AI, Pricing, Closer, Footer.

- [ ] **Step 2: Build the 1440 EN hero and connected card field**

Use component instances and editable vectors. Preserve the masthead hierarchy, CTA row, microcopy, connected product-card field, current product emphasis, and current honesty labels.

- [ ] **Step 3: Build remaining 1440 EN sections top to bottom**

Populate each current section in source order. Preserve the dark Terminal band, Prophet belt, alternating feature narratives, AI analyst band, pricing/tier matrix, closing field, and footer.

- [ ] **Step 4: Close desktop EN fidelity**

Create an overlay comparison frame with locked reference at 50% opacity. Record every >2px or material visual mismatch in the deviation ledger before correction. Resolve differences before language/responsive derivatives.

- [ ] **Step 5: Derive and verify desktop ZH**

Duplicate through components/variants, replace visible text with source Chinese twins, and repair geometry where CJK wrapping differs. Do not shrink type merely to force English geometry.

- [ ] **Step 6: Build 1024 EN and 390 EN/ZH**

Apply actual responsive hierarchy: collapsed grids, hidden desktop annotations, mobile navigation, section stacking, pricing reflow, and footer restructuring. Prove no horizontal overflow.

- [ ] **Step 7: Update acceptance matrix and screenshot evidence**

Set homepage cells to `PASS` only after screenshot/overlay proof exists. Attach desktop/mobile EN/ZH screenshots and list any accepted deviations.

**Acceptance:** homepage is editable, structurally complete, and visually matched at canonical widths/languages with zero unexplained material deviations.

---

### Task 7: Reconstruct and prove the three product pages

**Files:**
- Figma pages: `11 — Current · Market Terminal`, `12 — Current · Mastermind AI`, `13 — Current · Market Dashboards`
- Source: corresponding hand-authored product HTML files and shared landing/motion CSS

**Interfaces:**
- Consumes: shared foundations/components and product-page reference captures.
- Produces: fifteen canonical product-page frames plus comparison evidence.

- [ ] **Step 1: Create canonical wrappers and section placeholders on all three pages**

For each page create 1440 EN/ZH, 1024 EN, and 390 EN/ZH wrappers. Use the exact current section inventory from source and mark placeholders until populated.

- [ ] **Step 2: Build Market Terminal**

Preserve blue accent, chapter ribbon, browser hero, delayed-basis label, watchlist rail, charting, indicator systems, dossier, signal read, options and AI sections, honesty station, closer, and footer.

- [ ] **Step 3: Build Mastermind AI**

Preserve violet accent, grounded conversation hero, receipts/citations, page-aware context, stance separation, section sequence, honesty station, closer, and footer. Do not visually imply model authority over ranking, sizing, gating, or trade origination.

- [ ] **Step 4: Build Market Dashboards**

Preserve teal accent, desk wall, regime, lanes, rotations, filings, flow, China, record, beyond and nightly sections, honesty station, closer, and footer.

- [ ] **Step 5: Run desktop and mobile overlays per page**

Create comparison frames at identical viewport dimensions. Log and resolve every material deviation before marking pass.

- [ ] **Step 6: Update acceptance matrix**

Mark each viewport/language cell only when proof is attached. Keep motion cells pending for Task 8.

**Acceptance:** each product page is a native editable member of one shared family while preserving its real product-specific hierarchy and honesty furniture.

---

### Task 8: Model motion and interaction states

**Files:**
- Figma page: `20 — Motion & Interaction`
- Source: `site/scene-motion.js`, `site/scene-motion.css`, page-specific CSS/markup

**Interfaces:**
- Consumes: completed components/page frames and source motion selectors/timings.
- Produces: scene variant sets, interaction-state components, and prototype flow IDs.

- [ ] **Step 1: Create semantic phase variants**

For each major scene, create `Idle`, `Observe`, `Reason`, `Resolve`, and `Hold` variants. Include at minimum homepage hero/field, Terminal chart+intelligence card, AI evidence conversation, Dashboard regime/lanes, and one representative row/tile scene from each page.

- [ ] **Step 2: Create interaction variants**

Model nav dropdown closed/open, mobile menu closed/open, settings closed/open, EN/ZH language state, pricing selection, focus-visible, and important hover states.

- [ ] **Step 3: Connect representative prototypes**

Create prototype sequences for:

```text
Homepage arrival
Terminal observe → reason → resolve
AI question → evidence → stance
Dashboard observe → cross-check → resolve
Desktop nav dropdown
Mobile nav
Settings/language switch
Pricing period selection
```

- [ ] **Step 4: Create static/reduced-motion proof**

For every animated scene, identify its settled state and provide a direct static frame. No scene may depend on autoplay to communicate its content.

- [ ] **Step 5: Validate motion inventory**

Compare the Figma scene inventory against the selectors in `scene-motion.js`. Every source scene is mapped to a Figma state, explicitly grouped under a representative pattern, or recorded as a non-visual runtime detail.

**Acceptance:** a reviewer can inspect what changes in each semantic phase, play representative flows, and view the same content in a useful static state.

---

### Task 9: Run the baseline acceptance matrix and freeze Current / 1:1

**Files:**
- Figma pages: all Current pages, `00 — Read Me & Acceptance`, `90 — Reference Captures`, `99 — Revamp`
- Update: `docs/design/public-site-figma-baseline-handoff.md`

**Interfaces:**
- Consumes: all completed page, motion, and evidence artifacts.
- Produces: accepted/rejected acceptance matrix, final deviation ledger, immutable Current labels, handoff document.

- [ ] **Step 1: Run structural audit**

Verify section counts/order, component-instance use, layer naming, no full-vignette raster flattening, capture separation, and editable hierarchy.

- [ ] **Step 2: Run visual audit**

At 1440 and 390 for EN/ZH, verify type, wraps, spacing, component bounds, token roles, borders, radii, shadows, and 50% overlay comparison. Record antialiasing-only differences separately from geometry defects.

- [ ] **Step 3: Run responsive and accessibility audit**

Verify no 390 horizontal overflow, desktop-only annotation behavior, mobile nav/settings usability, Chinese clipping/wrapping, focus-visible states, and settled reduced-motion content.

- [ ] **Step 4: Close the deviation ledger**

Every row must be `RESOLVED`, `ACCEPTED WITH RATIONALE`, or `BLOCKING`. There is no generic `KNOWN ISSUE` terminal state.

- [ ] **Step 5: Freeze Current pages**

When all cells pass and no blocking deviation remains, prefix each canonical frame with `ACCEPTED 1:1 —`, append source commit/date, lock accepted top-level frames, and preserve editable children through controlled unlock permissions rather than flattening.

- [ ] **Step 6: Leave Revamp locked pending explicit acceptance**

Do not populate `99 — Revamp`. Update the gate notice to summarize baseline completion and state that redesign still requires the Chairman's explicit acceptance of the completed baseline.

- [ ] **Step 7: Write durable handoff**

Create `docs/design/public-site-figma-baseline-handoff.md` containing mission, file URL/key, source/Skillpack pins, capability ledger, completed waves, deviations, acceptance evidence, exact next action, and explicit non-goals.

**Acceptance:** a fresh session can recover and review the baseline without chat history; Current is frozen; Revamp remains unstarted until Chairman acceptance.

---

### Task 10: Post-acceptance revamp planning boundary

**Files:**
- Future spec: `docs/superpowers/specs/YYYY-MM-DD-public-site-revamp-design.md`
- Future plan: `docs/superpowers/plans/YYYY-MM-DD-public-site-revamp.md`

**Interfaces:**
- Consumes: Chairman acceptance of the completed baseline.
- Produces: a new revamp design specification; this task does not itself redesign or implement anything.

- [ ] **Step 1: Confirm explicit baseline acceptance**

Require a live Chairman directive accepting the completed Current / 1:1 baseline. Specification approval alone is not sufficient.

- [ ] **Step 2: Duplicate accepted Current frames into Revamp**

Only after acceptance, duplicate rather than move accepted frames. Keep accepted Current frames unchanged.

- [ ] **Step 3: Begin a new brainstorming/specification cycle**

Define the improvement thesis, product hierarchy, user journey, alternatives, motion changes, evidence standards, and code delivery boundary in a separate approved spec.

**Acceptance:** the baseline program does not smuggle redesign or production implementation into its completion claim.
