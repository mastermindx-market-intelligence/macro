# Homepage connected-research rollout

## 0. Acceptance gates

Status: Chairman-approved direction; implementation and production acceptance remain separate. The live Chairman approved the September 9 homepage audit and assigned Sol end-to-end leadership in the same conversation. This document records that direction; it creates no runtime, lease, deployment permission, or signal authority.

A release is not accepted until the changed user journey works in production, English and Chinese remain equivalent, both requested theme preferences render deliberately, 320/360/390/430px mobile and 1440px desktop retain readable content, and the exact code, tests, screenshots and production observation are recoverable. Current, historical, illustrative, stale and unavailable data must not be conflated. Prices and access must agree with their canonical authority. Tests, merge and publication alone are not product acceptance.

## 1. Outcome and scope

Primary persona: a serious self-directed investor investigating markets and companies across fragmented tools. User job: understand a change, inspect its evidence and limitations, continue into the relevant company workspace, and retain useful personal context. Machine job: serve trustworthy existing research and measure genuine user outcomes through the existing growth plane. Moat: connected research and useful synthesis, not an unexplained collection of dashboards or source links alone.

The 10/10 end state is an immediately understandable, credible homepage leading to a real first research action and a reason to return. Conversion and retention improvement are hypotheses until measured; no uplift percentage is promised.

Sol owns direction, decomposition, collision adjudication and acceptance. The canonical program `marketing-intelligence` owns product messaging and audience evidence; existing product, entitlement, market-data and analytics owners retain their contracts. No new lifecycle, queue, identity, model-scoring, analytics or publication plane.

## 2. Source pins and preserved work

Procedure: `mastermindx-market-intelligence/Mastermind@f3f2d9155796876009f2d427bfdecc7ee7b63e74`, compatible Skillpack 1.0.1 / bootstrap 1. Commission base: `macro@a4d33f32dad140acdfa081b21f55ad6d8dcb94d4`. Terminal read pin: `690f65900993b0495441c51392a93f1fade72927`. Refresh before release; do not infer deployed versions from these pins.

Existing macro #6842 remains the Acquisition Truth Bridge carrier at `70815229c55963598d4441eef07ca3949d097b3b`; it owns derived preview freshness/coverage, demo-label repairs and tech-jitter removal. It is an open held draft with failed checks at inspection, not a shipped fix. Existing #6988 at `e122539a1613fa307313742a16f083c3388f4122` owns public navigation branding. Do not recreate either or overwrite their source branches. Review and reconcile before overlapping release.

The source writer for this rollout uses `claude/homepage-connected-research-20260909-sol`. One logical modifying operation remains on its carrier until reconciled. No merge-on-green or native auto-merge may release a held sibling. Freshly read the relevant carrier before a substantive ruling.

## 3. Approved experience direction

Hero candidate: “See what changed. Understand why it matters.” Keep MastermindX discoverable in the single H1. Support with one concise description of connected market/company research and evidence-aware AI. Primary: “Create my free desk”; secondary: “Explore an example”. Free-plan reassurance must match actual access; do not blur permanent Free with the card-required Pro trial.

Replace competing miniature hero cards with one readable connected company-research example. Its first frame must contain useful substance, with the example's date/status visible. Optional motion explains relationships; it does not fabricate market updates. The actual click-through must retain the company/question and reach existing product evidence. No mockup-only seamless capability may be marketed as live.

Page sequence: outcome and example; substantiated proof; daily research workflow; three capability groups (understand the backdrop, investigate the company, work through the thesis); a substantive research case; clear plans; objections and final action. Preserve breadth but stop asking a new visitor to reconstruct the connections.

Art direction: retain the deliberately light public-page canvas, white research surfaces, existing restrained blue action color, typography and dark terminal/closing bands. A dark browser preference must not trigger an invented automatic inversion; `color-scheme:only light` remains. Both preference captures are required to prove readability. Do not add font downloads or a parallel token palette. Mobile is a composition, not scaled-down desktop. Reflow instead of hiding important content.

## 4. Bounded implementation waves

### H1 — Read the entire homepage on a narrow screen

Capability: a visitor at 320–390 CSS pixels can read the situation examples and reach every footer destination without sideways document scrolling. Scope: `templates/landing.css`, paired `site/landing.css`, the referencing index CSS stamps, a regression in existing `tests/test_landing_navigation.py`, and evidence/continuity records. No marketing copy, price, auth, menu inventory, data producer or score changes.

Root causes reproduced on source and production: four nonwrapping footer columns force a 406px document at 390px; after a two-column footer probe, a nonwrapping situation-meter row still forces 354px at 320px. Implementation order: (1) failing regression for both source copies; (2) within the existing 680px breakpoint, reflow footer columns to `repeat(2,minmax(0,1fr))`, allow intrinsic-width shrink, and wrap the situation meter/early label; (3) mirror the plain pair and refresh its existing content-derived CSS stamp; (4) test source contracts and the real browser width/locale/preference matrix; (5) generate the existing page-evidence manifest/receipt, inspect screenshots, review the changed-path collision, then conclude CI and verify the natural production publication. Never mask the defect with a body overflow rule.

Stop H1 on a residual overflow, lost link/label, changed price or disclosure, a new JavaScript error, an unclassified CI failure, an overlapping source-owner conflict or publication ambiguity. H1 is not the redesign's completion.

### H2 — Trust and commercial agreement

Independently review #6842 on its exact head and current composition; repair through its established owner/carrier rather than a replacement. Reconcile home/plan claims against `app/paywall.py`, `app/billing.py`, existing entitlement policy and real access. Verify the institutional relationship claim or remove it without alleging it false. Do not change commercial entitlements or fabricate customer counts. Completion requires the actual public claim and access to agree, not merely edited prose.

### H3 — The connected first impression

Freeze the exact hero/example markup and responsive design before bounded implementation. Preserve one H1, the existing ad-experiment registry (`data/marketing/ad_central/arenas.jsonl`) and its inline contract; do not silently overwrite a historic experiment identity or let a stale arm restore retired copy. Use an existing real company dossier and supported section destinations. AAPL's anonymous dossier was observed rendering company event evidence and a security-state panel; this is a candidate, not blanket acceptance of every datum on that page.

### H4 — Flow, packaging and first-use continuity

Group the remaining feature depth around user jobs; bring the meaningful AI/result demonstration forward; keep the complete plan comparison accessible without forcing it onto the initial reading path. Align the Free/trial expectation and preserve selected-company context through entry. Any auth or billing UI change is a separately tested Terminal slice; homepage approval does not authorize weakening gates, changing prices or purchasing a subscription.

### H5 — Learning and final acceptance

Recover `config/growth_events.yml` and the existing first-party `/api/collect` implementation before adding emitters. Trace qualified visit -> actual intelligence -> personal action -> account -> activation -> paid/retained use. A click, pageview, trial or long dwell is not activation. Instrumentation proof and mature cohort results are distinct; no fresh pipeline or invented result to make the program look complete.
