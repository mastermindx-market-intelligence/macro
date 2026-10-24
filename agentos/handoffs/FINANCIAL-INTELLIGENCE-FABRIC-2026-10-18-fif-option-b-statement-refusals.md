---
workstream: "WS:FINANCIAL-INTELLIGENCE-FABRIC"
session: claude/fif-optb-integ-20261018 (FIF Meta-CEO seat 96dc937a, Option B)
model: opus
ended_because: ci_handoff
mission: >
  Record Option B (ruling v3.1): typed per-statement refusals in the kernel and
  publisher, cohort withholding (A35-W1), desk withheld-statement blocks, and
  the C2 coverage freeze. BAC and CAT now publish with 12 pinned refused
  statements instead of whole-issuer exclusion. Knowledge plane only: nothing
  here gates, dispatches or proves liveness.
state_before: >
  After wave 3 (handoff FINANCIAL-INTELLIGENCE-FABRIC-2026-10-14-fif-e2e-wave3)
  a five-issuer publish exited 0 but BAC and CAT were whole-issuer exclusions
  (displayed_table_absent / displayed_columns_absent). Live /api/health still
  reports the golden dataset mode; the VPS production flip (A0) is held.
prs: [9609]
decisions: []
changed:
  - path: engine/fundamental_forensics/statement_graph.py
    what: >
      Per-statement refusal entries {statement_type, role_uri, title, columns
      [], rows [], row_count 0, refusal {code}} instead of one accession-wide
      raise; codes only, never the message.
  - path: engine/fundamental_forensics/peer_cohort.py
    what: >
      A35-W1 withheld MetricObservation (value None, period_end R_m,
      withheld True); a withheld anchor yields anchor_end R_m.
  - path: scripts/publish_fif_production_datasets.py
    what: >
      Refusal pin config/fundamental_forensics/statement_refusals.v1.json (11
      BAC + 1 CAT rows); classification order regressed_from_latest → pin →
      pinned_code_changed → first_publication → golden_accession → absent or
      already refused in latest → fail. All-refused issuers are excluded with
      the first refusal in (accession, income/balance/cash_flow) order and a
      stderr warning. A pin without golden_accessions fails closed.
  - path: templates/fundamental_forensics.js
    what: >
      Withheld-statement block per refused statement and an accession-level
      notice when all three are refused; no code, message or raw identity in
      the DOM. Site copies byte-identical.
  - path: research/financial_intelligence_fabric/FIF_C2_COVERAGE_FREEZE.md
    what: C2 coverage census frozen (250 deep / 1,000 core) with a measured tier proposal.
  - path: agentos/workstreams/WS-FINANCIAL-INTELLIGENCE-FABRIC.md
    what: next_action replaced with the post-Option-B ladder; one do_not_redo entry appended.
verified:
  - claim: "A scratch five-issuer publish over real cached SEC packages reports 12 refused statements, all pinned, 0 unpinned, and AAPL/SNOW/GOOGL generation ids unchanged from base."
    command: "Seat scratch tree (git archive of the branch + cached packages), python -m scripts.publish_fif_production_datasets publish --coverage-file config/fundamental_forensics/coverage/five_issuer_v1.json under env -i with no R2_* env."
    result: "rc 0; BAC and CAT published; accession_all_refused 0000070858-24-000122 and 0000070858-26-000157; stderr refusal warning present."
  - claim: "Acceptance 4 cutoff replay changes 0 AAPL/SNOW/GOOGL member rows; BAC net_income_loss at the 2026-05-01 cutoff is valid at 2026-03-31; A35-W1 rows carry period_end."
    command: "Seat scratchpad optb_cut/after_rows_w1.py over the after/<cutoff>/store stores; summarize_cut.py."
    result: "1350 rows, 127 A35-W1, 0 with blank period_end. Table (codes and period ends only, no values) is in the PR #9609 body."
  - claim: "Withheld block and all-refused notice pass the dual-theme matrix."
    command: "Browser pane on site-static, desk JS re-evaluated through its opt-in test seam; light/dark × 1440/390 × EN/ZH × mixed/all-refused."
    result: "16/16: even 1px dashed border on all four sides, no shadow, text contrast 6.33 (light) / 5.33 (dark), no page overflow, no filing link above the statement panel, no code/slug/message in the DOM."
  - claim: "Publisher, T1 seal and desk tests pass."
    command: "pytest tests/test_fundamental_forensics_production_publisher.py tests/test_fundamental_forensics_t1_compatibility_seal.py; node --test tests/fundamental_forensics_statement_withheld.test.mjs"
    result: "See the PR #9609 body for counts at the merged head."
unverified:
  - "Production proof: the VPS flip (A0) is still held, so no live page serves BAC/CAT production statements yet."
unresolved:
  - >
    A0: the API still serves the golden corpus (live /api/health reports
    fif_financial_dataset_mode golden). The A45 receipt chain and a post-flip
    natural-cycle witness are still owed.
  - >
    BAC keeps 11 pinned refused statements and CAT keeps 1. They lift only by a
    parser change that reconstructs them, which the pin then reports as
    regressed or changed, never silently.
next_actions:
  - "#9609: single body edit with the acceptance-4 table, then ready, ONE watcher, hand merge with --match-head-commit on concluded green, land check, main ci.yml baseline after preflight."
  - "A0: set FIF_FINANCIAL_DATASET_MODE=production through the reviewed macro-api.service fragment (never /etc/macro-api.env), verify /api/health, collect the A45 receipts from an existing entitled browser profile, then record the next schedule run as the natural-cycle witness."
  - "Then G1–G4, A1, the 12 specialist packs (K1–K4 prep-only until A1), API/Excel, coverage tiers per FIF_C2_COVERAGE_FREEZE.md, independent acceptance."
do_not_redo:
  - "Do not rebuild typed per-statement refusals, the refusal pin, its classification order (ruling v3.1), A35-W1 withholding or the desk withheld blocks."
  - "Do not re-mint the BAC parent-company income role or rewrite BAC parent-only manifests to consolidated."
  - "Do not re-run the C2 coverage census without cause."
danger_areas:
  - "The producer must stay off the golden layer and free of ticker or CIK literals, including docstrings and comments; its guard tests enforce both."
  - "Golden AAPL output must stay byte-identical (0000320193-25-000079 sha256 4af34778…704d, 0000320193-26-000020 sha256 4abd06e1…b461)."
  - "A refusal pin without golden_accessions fails the publish closed; keep the key when editing the pin."
  - "Non-AAPL SEC filing bytes and values never enter git; the acceptance tables carry codes and period ends only."
---

Option B lands BAC and CAT as published issuers with typed, pinned per-statement
refusals instead of whole-issuer exclusions. The next rung is A0 (production
flip), then the specialist packs, API/Excel and the 250/1,000 coverage tiers
from the C2 freeze.
