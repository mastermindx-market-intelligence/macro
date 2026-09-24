# International Markets vNext R3 Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Produce an independently reviewable R3 reference for `intl.html` that closes every R2 blocker without weakening accepted engine authority or changing production code.

**Architecture:** Preserve the frozen R2 artifact and create `reference-r3.html` as a new standalone design artifact. R3 keeps the six-act operating flow, restores every displaced user job through visible evidence or real destinations, separates direction from health/status semantics, and models degraded states at organ scope. Production implementation remains gated on RIG approval.

**Tech Stack:** Standalone semantic HTML/CSS/vanilla JavaScript, Playwright Chromium capture, pytest static-contract tests, Mastermind Reference Integrity Gate YAML.

**Spec:** `docs/checkpoints/INTL_VNEXT_RIG_R2_CHECKPOINT_2026-09-24.md`

## Global Constraints

- Do not modify or replace `reference-r2.html`, its screenshots, baseline evidence, or R2 critic receipts.
- Do not edit `templates/intl.html.j2`, `scripts/build_intl.py`, `site/intl.html`, or `site/intl_stocks.html` before RIG approval.
- The World Risk Appetite `66/100` is the only headline 0–100 scalar; no invented confidence, risk-budget, sensitivity, or health score.
- Preserve the canonical site shell and Chairman-directed global overview as production-owned surfaces in the reference contract.
- Keep turn-state, RRG, risk-radar, fragility, and price-direction vocabularies visually and semantically distinct.
- Dark/light and EN/ZH are separate art directions; state/severity colors never flip in ZH.
- R3 must fit a real 390px viewport without page overflow; wide tables scroll only inside their containers.
- `intl_stocks.html` is preserved, not redesigned; evidence must prove that shared mode remains an explicit non-regression obligation.

## Review Focus

- Full universe accounting: ten turn-state markets, seven economy macro rows, complete or counted pressure-flow coverage.
- Organ-local degraded states: loading/empty/error/stale must leave unrelated intelligence visible and truthful.
- Light/Chinese semantics: canonical ink contrast, no status inversion, no Latin tracking on Han labels.
- Reachability: every compacted deep desk goes to a real route or in-page anchor, never a self-link.
- Authority: rotation rank is presented as an engine result; transmission remains non-causal and posture never originates trades.

---
### Task 1: Pin the R3 contract with RED tests

**Files:**
- Create: `tests/test_intl_reference_r3.py`
- Read: `mockups/refs/institutionalize/intl/reference-r2.html`
- Read: `research/reference_integrity/intl-vnext-20260924/reviews/r2_pass1_product_regression.raw.md`
- Read: `research/reference_integrity/intl-vnext-20260924/reviews/r2_pass1_visual_taste.raw.md`

**Interfaces:**
- Consumes: the immutable R2 freeze and exact R2 blocker IDs.
- Produces: static contract tests for the new `reference-r3.html` artifact.

- [x] **Step 1: Write the failing tests**

Create tests that require: six acts; shell/global-overview preservation markers; Dollar Drivers; real deep links; ten turn-state identities; seven comparable macro rows; horizon controls; complete pressure coverage; no at-rest equal-to-base dip odds; no misleading partial rotation derivation; organ-local state hooks; canonical ink tokens; stable state colors in ZH; no sub-10px user copy; no self-links; and explicit stocks-mode preservation.

- [x] **Step 2: Run the tests to verify RED**

Run: `/Users/chriswong/Documents/Cluade/Macro Dashboard/.venv/bin/python -m pytest tests/test_intl_reference_r3.py -q`
Expected: FAIL because `mockups/refs/institutionalize/intl/reference-r3.html` does not exist.

- [x] **Step 3: Commit the RED contract**

Run: `git add tests/test_intl_reference_r3.py docs/superpowers/plans/2026-09-24-intl-vnext-r3-reference.md && git commit -m "test(design): pin international R3 reference contract"`

### Task 2: Build the R3 reference

**Files:**
- Create: `mockups/refs/institutionalize/intl/reference-r3.html`
- Do not modify: `mockups/refs/institutionalize/intl/reference-r2.html`

**Interfaces:**
- Consumes: R2 visual grammar, production fixture values, and Task 1's static contract.
- Produces: one standalone, network-free R3 reference with theme, locale, inspector, horizon, and organ-state controls.

- [x] **Step 1: Copy R2 to the new immutable candidate path**

Run: `cp mockups/refs/institutionalize/intl/reference-r2.html mockups/refs/institutionalize/intl/reference-r3.html`

- [x] **Step 2: Implement the R3 semantic repairs**

Implement the exact R3 obligations from the checkpoint. Keep the six acts, but restore the shell/overview, Dollar Drivers, full market/economy coverage, real links, horizon controls, change-shape evidence, stocks-mode preservation, and organ-local degraded states. Remove tautological odds, unsourced bars, duplicate drag lists, ambiguous `h`, and misleading partial rotation formula evidence.

- [x] **Step 3: Implement the R3 visual-system repairs**

Use `--ink-up`, `--ink-down`, `--ink-warn`, and separate health/status tokens. Reset CJK tracking for every label family, keep user copy at least 10px, remove the fake 390-preview control, and make status colors locale invariant.

- [x] **Step 4: Run the static contract**

Run: `/Users/chriswong/Documents/Cluade/Macro Dashboard/.venv/bin/python -m pytest tests/test_intl_reference_r3.py -q`
Expected: PASS.

- [x] **Step 5: Commit the R3 source**

Run: `git add mockups/refs/institutionalize/intl/reference-r3.html && git commit -m "docs(design): build international vNext R3 reference"`
### Task 3: Capture discriminating browser evidence

**Files:**
- Create: `mockups/refs/reference_integrity/intl-vnext-20260924/proposal-r3-*.png`
- Create: `mockups/refs/reference_integrity/intl-vnext-20260924/stocks-preservation-*.png`

**Interfaces:**
- Consumes: the exact committed R3 HTML and the current committed `site/intl_stocks.html` projection.
- Produces: visual evidence bound to the R3 candidate and a separate stocks-mode preservation receipt.

- [ ] **Step 1: Capture the default matrix**

Use Playwright to capture desktop 1440×900 and mobile 390×844 across dark/light × EN/ZH. Assert `document.scrollWidth == viewport width` and zero console errors for every cell.

- [ ] **Step 2: Capture hidden inspector panels and horizon states**

Capture Japan and United Kingdom inspector states in dark/light and EN/ZH, plus at least two non-default horizon selections. Assert the selected tab/button state is visible and keyboard reachable.

- [ ] **Step 3: Capture organ-local loading, empty, stale, and error states**

Capture both dark and light. Assert unrelated acts remain visible in every degraded state and that stale treatment does not dim the whole page.

- [ ] **Step 4: Capture stocks-mode preservation evidence**

Capture `site/intl_stocks.html` at desktop/mobile × dark/light × EN/ZH. Record it as current-production preservation evidence, not as a redesigned R3 surface.

- [ ] **Step 5: Run interaction and accessibility probes**

Verify theme/language changes, horizon controls, country tabs, ArrowLeft/ArrowRight keyboard navigation, focus visibility, real destination links, reduced-motion behavior, no external network dependency, and no horizontal page overflow.

- [ ] **Step 6: Commit the exact evidence set**

Run: `git add mockups/refs/reference_integrity/intl-vnext-20260924 && git commit -m "docs(evidence): freeze international R3 browser matrix"`

### Task 4: Run fresh RIG review and adjudication

**Files:**
- Update: `research/reference_integrity/intl-vnext-20260924/manifest.yml`
- Update: `research/reference_integrity/intl-vnext-20260924/proposal.yml`
- Create/update: `research/reference_integrity/intl-vnext-20260924/reviews/product_regression.yml`
- Create/update: `research/reference_integrity/intl-vnext-20260924/reviews/visual_taste.yml`
- Create/update: `research/reference_integrity/intl-vnext-20260924/verdict.yml`
- Create on approval only: `research/reference_integrity/intl-vnext-20260924/approval.yml`

**Interfaces:**
- Consumes: immutable R3 SHA, production baseline, R3 browser evidence, and capability ledger.
- Produces: independent dual-review receipts and the design-authority verdict.

- [ ] **Step 1: Bind the manifest/proposal to the exact R3 SHA**

Update artifact paths, screenshot matrix, and capability dispositions without changing the production baseline ledger.

- [ ] **Step 2: Run two fresh rationale-quarantined pass-one reviews**

Use distinct Opus reviewer identities. Neither reviewer may read the design rationale, proposal analysis, prior review conclusions, or verdict before freezing pass-one findings.

- [ ] **Step 3: Repair only material findings on a new candidate SHA**

Any artifact-changing finding invalidates both receipts. Repair on the same branch, recapture affected evidence, freeze a new SHA, and restart both pass-one reviews.

- [ ] **Step 4: Run pass two only after bytes are stable**

Reveal rationale and constraints, collect per-finding amendments, then write the two canonical review receipts.

- [ ] **Step 5: Adjudicate and validate**

Write the verdict and approval receipt only if no surviving blocker remains. Run `/Users/chriswong/Documents/Cluade/Macro Dashboard/.venv/bin/python scripts/check_reference_integrity.py --evaluate intl-vnext-20260924` and require exit 0.

- [ ] **Step 6: Commit the accepted RIG state**

Commit all exact-SHA receipts together. Production implementation remains a later task and must not be started from an unapproved reference.
