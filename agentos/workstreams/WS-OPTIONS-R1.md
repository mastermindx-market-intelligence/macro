---
key: OPTIONS-R1
title: "Mastermind Options R1 — rotation, positioning and research continuity"
objective: >
  One continuous journey on existing Terminal owners — Sector Central → holding →
  expiry/strike → chart → matched change → save → watch → review — that surpasses
  GammaPulse's loop on provenance and continuity. Done means every wave is merged,
  deployed through the git-gated VPS build and the full journey is verified signed-in
  on https://app.mastermind-x.com with the W1–W3 crop packets and e2e suites green.
status: active
program: options-intelligence
repos: [terminal, macro]
owner: coo-fable
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - terminal:terminal/components/sector/**
  - terminal:terminal/components/options/**
  - terminal:terminal/components/flowdesk/**
  - terminal:terminal/components/vol/**
  - terminal:terminal/components/investigation/**
  - terminal:terminal/components/eodcontext/**
  - terminal:terminal/docs/OPTIONS_R1_*.md
  - terminal:terminal/docs/pr-crops/options-r1-*/**
  - terminal:terminal/supabase/migrations/0039_investigation_options_evidence.sql
  - terminal:terminal/supabase/migrations/0040_investigation_review.sql
  - scripts/build_sector_holdings_coverage.py
  - engine/rotation_relative_trend.py
waves:
  - id: W1
    title: "Sector Central → holding → options exposure with origin, snapshot references and observed book changes"
    status: done
    pr: 1096
  - id: W2
    title: "Relative-trend rotation map, holdings coverage line, Options evidence continuity (migration 0039)"
    status: awaiting_ci
    pr: [1103, 9991, 9992]
    next_action: >
      When #1103 merges: apply 0039 through scripts/supabase_apply.py --apply --receipt,
      post the receipt on the PR, deploy master with --target-sha and verify an
      options-evidence save on production. Macro #9991 / #9992 land through the
      merge-on-green label after the declared-paths repair.
  - id: W3
    title: "Flow print inspector, volatility comparison with the published band, condition watches and review history (migration 0040)"
    status: awaiting_ci
    pr: #1104
    depends_on: [W2]
    next_action: >
      After the merge: apply 0040 (after 0039) with a receipt, deploy and verify
      the belt method line, the volatility band column and a watch → review round trip.
  - id: W5
    title: "Integrated proof of the full journey on production and the programme record"
    status: todo
    depends_on: [W3]
    next_action: >
      Walk Sector Central → holding → expiry/strike → chart → matched change → save →
      watch → review signed-in on production at the deployed sha; record the result in
      terminal/docs/OPTIONS_R1_PROGRAM.md and the handoff.
decisions:
  - "DEC:OPTIONS-R1-ONE-JOURNEY-ON-EXISTING-OWNERS"
  - "DEC:FABRIC-LANES-DRAFT-BROWSER-PROOF-THE-SEAT-RUNS-IT"
discoveries:
  - "DSC:INVESTIGATION-VALIDATOR-ADMITTED-ONLY-THE-EARNINGS-EVIDENCE-OWNER"
  - "DSC:NEXT16-ONE-DEV-SERVER-LOCK-PER-PROJECT-DIR"
  - "DSC:MACRO-CURATED-EXCLUSIVE-JOB-MUST-DECLARE-ANCESTOR-INITS-AND-MEASURED-CLOSURE"
do_not_redo:
  - Do not build a second options workspace, evaluator, watcher, queue or cron; the alerts engine is the only evaluator and transport.
  - Do not infer a band method, a squeeze probability, a package confirmation or an expected-move confidence; render the owner's absence.
  - Do not re-run the W1–W3 census lanes; the owner maps in the three freeze files carry file:line evidence.
  - Do not apply 0039/0040 with `supabase db push`; only scripts/supabase_apply.py with a receipt, 0040 after 0039.
  - Do not arm Macro producer PRs with native auto-merge; the merge-on-green label only (main is unprotected).
  - Do not describe a recaptured crop packet from a Pillow RGBA getbbox diff; measure in RGB and account for every differing pixel.
artifacts:
  - terminal:terminal/docs/OPTIONS_R1_PROGRAM.md
  - terminal:terminal/docs/OPTIONS_R1_W1_FREEZE.md
  - terminal:terminal/docs/OPTIONS_R1_W2_FREEZE.md
  - terminal:terminal/docs/OPTIONS_R1_W3_FREEZE.md
  - terminal:terminal/docs/pr-crops/options-r1-w2/EVIDENCE.yml
  - terminal:terminal/docs/pr-crops/options-r1-w3/EVIDENCE.yml
next_action: >
  On the #1103 merge notice apply 0039 with a receipt and flip its ledger row for #1104,
  deploy the W2 squash with --target-sha and verify an options evidence save live; then
  stack-merge master into the W3 branch (explicit base 6f1ccb48b, never a rebase), mark
  #1104 ready and arm merge-on-green; after it merges apply 0040, deploy, run the W5
  integrated journey proof on production and close the record. Push the Macro #9991
  repair once its local pack run is green and observe only.
---

## Shape

Three Terminal waves plus two Macro producers, each frozen before build in
`terminal/docs/OPTIONS_R1_W*_FREEZE.md` (binding rules, owner map from read-only census
lanes, lane/seat division, dated amendments). Build lanes ran on the fabric glm pool
where admitted; the seat built directly under the standing policy when the pool refused
(W2 Terminal lanes) and ran every browser proof itself.

## Where the evidence lives

Crop packets under `terminal/docs/pr-crops/options-r1-w2/` and `options-r1-w3/`, the
sha-locked packets (`vol-load-failure`, `options-level-axis-labels`,
`eod-heatmap-flowdesk-load-failure`) recaptured with their unmodified tools, the e2e
suites `terminal/e2e/options-r1-*.spec.ts`, and the PR bodies.
