# TTI R1-B v4 Empirical Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute the single registered R1-B v4 corrected-history study from preserved D0 inputs and publish an auditable aggregate result without altering frozen rules.

**Architecture:** Reuse the R1-A D0 loader/calendar path; consume `tactical_exhaustion` for v4 prior normalization, event construction, control matching, and outcome measurement. A new offline runner verifies frozen prereg/config/registration/ledger identity before any input read, writes only a new immutable output directory, and has no live event/trade path.

**Tech Stack:** Python, pandas, numpy, pytest.

**Spec:** `research/species/TTI_R1B_V4_PREREG.md`, `research/species/tti_r1b/config_v4.json`, `REGISTRATION_RECEIPT_V4.json`.

## Global Constraints
- Registration receipt + frozen hashes + exact 60-cell ledger identity must pass before any market input is opened.
- Use the preserved D0 input bytes and existing Terminal qualifier/calendar; no refetch.
- Corrected-history only; historical availability/fills remain unproven.
- Preserve every fire, censor, ambiguity, no-control case, and negative cell.
- No threshold/covariate/universe/horizon/cost change after outcomes.
- No live rank/alert/size/trade/options authority.

## Review Focus
- Admission failure must happen before input reads.
- Missing future bars censor outcomes, never delete fires or substitute later prices.
- Control membership uses candidate-time covariates only; outcome availability cannot select controls.
- Matched-control result is unavailable when the frozen pool or usable residual evidence is below its floor; no widening fallback.
- Primary aggregation averages within date before calendar-week block bootstrap.

### Task 1 — Admission + preserved-input reuse
- RED tests for wrong prereg/config/receipt/ledger and input-read ordering.
- Implement exact admission verifier and reuse R1-A D0 loader helpers.

### Task 2 — Construction/outcomes/controls
- RED synthetic miniature study verifying event preservation, control delay, censoring, and QQQ-sign matching.
- Implement study tables using frozen v4 engine functions.

### Task 3 — Aggregation/publication
- RED tests for 60-cell output, date-mean/week bootstrap, concentration and mechanical prospective-gate inputs.
- Implement immutable JSON/Markdown + private event/outcome/match JSONL outputs.

### Task 4 — Run once
- Verify full Radar/research suites and contract delta.
- Execute on preserved D0 inputs into a new run directory.
- Adversarially inspect denominators/concentration/censoring before publishing aggregate result.
