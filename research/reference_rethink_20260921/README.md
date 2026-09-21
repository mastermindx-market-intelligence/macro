# Market Guide — reference experience redesign

**Status: working design candidate, not a production release.**

This packet responds to Chris's September 21 brief: the current `reference.html` is confusing, unattractive, text-heavy, and disconnected from the “Look Up” links on Macro. The replacement must make the product easier to understand, not just put prettier cards around the same glossary.

## What this experience is for

Help someone understand a Mastermind signal, recognize its interpretation limits, and return to the actual instrument without losing context. It is not another market dashboard, a stream of live recommendations, or an encyclopedia the user must read before using the product.

The existing page's useful asset is its maintained bilingual registry. Its weak point is that the first screen exposes the registry's internal organization—46 entries, ten families, kind filters, alphabet navigation and coverage exceptions—rather than a clear user task.

### The replacement has two entry points

**Contextual explanation on Macro.** A named, keyboard- and touch-accessible help button belongs beside the signal it explains. It opens a short explanation, an interpretation visual, one important limitation, and an optional full-guide action. Closing returns focus and scroll to the trigger. Remove the separate six-link “LOOK UP” rack only when the corresponding in-context triggers are implemented and verified; do not temporarily strand those explanations.

**A visual Market Guide at the existing route.** Keep `/reference.html` and stable entry IDs. Lead with three questions: “How strong is the market?”, “Is risk building?”, and “What is driving the backdrop?” Provide immediate local search and a secondary full-library view. The full catalog and expert caveats stay available, but not expanded at rest.

### Reading hierarchy

At rest: one plain-language definition; a visual or categorical explanation appropriate to the indicator; one essential limitation; one clear route back to the owning dashboard. Deeper explanation, full caveats, related indicators and public sources belong in progressive disclosure. Do not truncate the underlying source content or invent formulas to fill gaps.

The developed exemplar is Market State Score. It explicitly applies to US equities. Its six named ingredients are trend, cross-asset risk appetite, volatility, breadth, liquidity and stress. Examples illustrate lower, mixed and higher readings without inventing numerical thresholds, component weights, live values or predictive claims. The complete instrument-specific visual treatment for Risk Radar, Regime Quadrant and other measure types remains a next implementation/design packet, not a claimed completed redesign of all 46 explanations.

## Deliverables in this directory

`prototype.html` is a self-contained, functional review prototype. Open it in a browser. Its toolbar is a review control, not a proposed replacement for the product's shared navigation. It compiles all 46 entries from `config/market_reference.yml`; it does not create a second editorial database. Source is `compile_prototype.py`, `prototype.css`, and `prototype.js`.

`paper-manifest.json` identifies the editable Paper file, its 20 native artboards, token snapshot, exported native source and screenshot hashes. The file is **Mastermind · Market Guide · Re-envisioning**. The artboards cover home and score detail in light/dark × EN/ZH × desktop/mobile, plus the contextual-help component in both themes and languages. `paper-source/` contains native Paper JSX exports for inspection; these are not application components and must not be blindly imported into production.

`paper-snapshots/` contains native Paper captures. `browser-*.png` contains 24 browser captures of home, detail and contextual help across the eight theme/language/width combinations. The prototype is an interaction test bed, not a pixel-parity or independently approved migration.

`browser-test-receipt.json` records 16 passing browser check groups. They include alias search in both languages, query persistence, empty and unknown-link states, all 46 definitions, all 46 detail routes at EN desktop and ZH mobile, history, help-state switching, Escape/focus/scroll restoration, no-JavaScript fallback, no horizontal page overflow, no uncaught browser errors, and zero external requests during the exercised flows. Owner links were **not** followed; these checks do not prove production anchor liveness.

### Rebuild and test

From this directory:

```sh
python3 compile_prototype.py
node --check prototype.js
python3 test_prototype.py
```

The browser test starts a loopback-only ephemeral server and shuts it down. It does not deploy, call a model, invoke market-data services or alter production. Dependencies used were already installed on the Studio: PyYAML and Playwright/Chromium.

The Paper authoring scripts are historical one-shot composition tools, not idempotent build commands. Do not rerun `build_paper.py first` or `refine_paper.py` against the frozen file. Read the exact existing native nodes/export instead; start a new candidate file for a new composition. Raw temporary tool receipts and unrelated Paper-file metadata are excluded from the PR.

## Art direction and component boundaries

**Light:** cool research-workspace canvas, white surfaces, restrained blue action ink, visible hairlines, light elevation on interactive cards, and white selected-state material. Preserve breathing room and generous main-column width. The selected example is distinguished without a saturated data-status color.

**Dark:** instrument-like canvas with three deliberate luminance planes, stronger panel outlines, quieter blue ink, no transplanted light-mode drop shadows, and a recessed selected-state surface. Information architecture, semantic color meanings, order and behavior remain identical.

Use the canonical font stack, spacing/type/radius scales and semantic tokens from `templates/theme.css`. The standalone prototype and Paper file contain **design snapshots**, not permission to add a parallel runtime palette. The production page must use the existing `_site_nav.html.j2` family and its genuine responsive behavior. Paper's representative header and the prototype review toolbar are explicitly outside the migration's replaceable scope.

Mobile uses stacked question rows and a single reading column. The actual quick-help dialog is height-bounded and internally scrollable. Bilingual copy must retain instrument scope, caveats and reference-only authority; no English-only accessibility labels. Direction colors and data-health colors remain separate. No animation is required to understand any example.

## Backend and delivery contract

### Retain, do not rewrite blindly

Keep the existing closed registry and its fail-closed validation. `scripts/build_market_reference.py` already validates definitions, relations, allowed source/owner references and ownership visibility. Preserve `authority_ceiling: reference_only`, active/deprecated semantics, stable entry IDs, aliases, related IDs, and the existing `q`/hash navigation behavior. Coordinate with the incumbent query/route-evidence repair rather than replacing it.

### Extend one source into multiple consumers

Compile a small, versioned guide/help manifest from the same registry. It should expose ID, locale content, short explanation, visible caveat, unit/basis, related IDs, approved owner target, source references, status and a declared presentation type. Search keys should be deterministic and precomputed. Add curated question/topic metadata in the governed content source, not duplicated hard-coded production JavaScript lists.

Presentation types must distinguish composite score, risk measure, two-axis quadrant, confirmation state and ordinary term. A categorical state must never be forced into an up/down gauge. A rising risk reading must not inherit the “higher is supportive” explanation used by Market State Score. Numeric thresholds or weights require actual engine-owned evidence; a design cannot mint them.

Both the standalone guide and contextual help consume the same compiled record. No runtime LLM or database is needed to search this catalog. Do not store user queries in new analytics or create a new admin console merely to support this feature.

### Required production behavior

- Keep existing direct links and query text working. Preserve browsing/search state when opening an explanation and navigating back. Validate any return target against same-origin, approved product routes; do not accept arbitrary URLs or blindly call browser back on a cold external arrival.
- Reuse or reconcile the shared help affordance work. Provide a named button, visible focus, appropriate dialog labeling, Escape dismissal, focus restoration and touch-sized controls. Verify inside the real dashboard, not only in this isolated prototype.
- Keep a server-rendered/no-JavaScript reading fallback. Search with zero matches must explain what to try next. Unknown, retired and coverage-alias entries need distinct, useful recovery rather than a technical exceptions dump. The prototype covers empty/unknown and ordinary entries; coverage-alias recovery is not implemented here.
- Do not put a fabricated fresh/live badge on reference content. Content version and last editorial review are different from market-data timestamps. When enrichment fails, preserve readable definitions and make missing interaction/enrichment explicit.
- Retain full official-source links and methodology/caveats in the production detail view. The prototype is not a substitute for the owning engine's methodology or source allowlist checks.
- Preserve authentication, subscriptions, engine outputs, risk thresholds, event status and global navigation. No changes to market calculations, sales surfaces, workers, deployment configuration or control-plane authority are in scope.

### Performance and acceptance

The current self-contained prototype is approximately 147 KB uncompressed / 44 KB gzip, including bilingual registry content and the no-JavaScript fallback. This is a measured artifact size, not a claim of faster production performance. Search and help make no external requests in the exercised browser tests. Proposed production guardrail: no framework/charting-runtime dependency for the guide; incremental guide/help assets below 50 KB gzip unless an independently reviewed need justifies a larger budget. Measure the actual integration; never load Plotly merely to draw a conceptual diagram.

Before release, require production source/asset synchronization, the full registry validator against real rendered owner pages, route/alias/coverage tests, shared-help integration tests, CSP and return-target checks, source link verification, keyboard/screen-reader review, the full dual-theme/bilingual/mobile matrix and independent visual adjudication. The prototype's passing tests do not replace these gates.

## Custody and next packet

Entry authority: protected `Mastermind/master@6f321cb42166e4224e5107ac3312a6f7cd01fffa`, skillpack 1.0.1, bootstrap major 1. INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT were loaded from that same pin.

Macro base: `ff90f9beacb5109e43848faf0a76e45060bd07f9`. Carrier: `claude/reference-rethink-20260921`; all changed files stay under `research/reference_rethink_20260921/`.

The open incumbent `macro#6792@7853ffeaca41d4d8f33995b1453db2be134ce8a3` owns reference template/builder/tests and route evidence. The open shared-help `macro#7610@54d103a2741cd32e8d64bf61a883242e5df0a1e7` owns adjacent keyboard/touch behavior. Both were read back as OPEN during closeout. This packet is path-disjoint and does not seize their source custody.

**Next executable packet:** independently adjudicate this candidate; reconcile the reference and shared-help carriers; freeze instrument-type and alias/degraded-state decisions; implement the approved reusable manifest, guide page and in-context Macro help in fresh isolated production work; run the real acceptance matrix; then follow normal protected merge/deploy/live verification. Do not treat the candidate PR as authorization to self-approve a flagship migration.

**Mission complete: false. Production changed: false.** The completed unit is the design, working interaction prototype, source audit and reviewable implementation contract.
