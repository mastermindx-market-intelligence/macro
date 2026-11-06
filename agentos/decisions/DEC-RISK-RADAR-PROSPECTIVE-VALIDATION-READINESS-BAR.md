---
key: RISK-RADAR-PROSPECTIVE-VALIDATION-READINESS-BAR
question: >
  What evidence must the latest exact US Risk Radar model cohort accumulate before
  prospective probability results may be presented for a separate model-promotion review?
answer: >
  Use the preregistered prospective validation-readiness bar frozen before any
  receipt-bearing outcomes existed. The latest exact epoch+model-fingerprint cohort
  must span at least 252 issued sessions and 300 calendar days; each H5/H10/H21
  horizon must have at least 200 graded rows, 20 event rows, 50 non-event rows and
  5 overlap-aware event clusters; baseline pairing and grading integrity must be
  complete; paired Brier delta versus the issued unconditional baseline must be
  negative with a 90% circular moving-block CI whose upper bound is below zero; and
  the 90% moving-block CI for calibration-in-the-large must contain zero.
  Passing these checks yields only promotion_review_eligible=true. It never sets
  current_model_validated, public_validation_ready, or any market authority.
rationale: >
  Historical reconstruction and two preregistered retrospective recalibration
  attempts showed useful risk-gradient information but did not justify precision
  claims or a live probability retune. The new prospective ledger receipts create
  higher-authority evidence, but a statistical bar frozen after outcomes arrive
  would invite goalpost movement. Overlapping daily loss windows also require
  block-aware uncertainty and episode-like event clustering rather than raw row
  counts.
alternatives:
  - option: Promote once raw prospective n reaches a convenient sample size
    why_not: >
      Daily H5/H10/H21 windows overlap heavily; row count alone can turn one selloff
      into many apparent observations and says nothing about calibration or skill.
  - option: Let current_model_validated flip automatically when the bar passes
    why_not: >
      Statistical readiness is evidence for a separate promotion decision, not
      authority to rewrite model or Market-State validation state.
  - option: Tune thresholds after the first prospective results arrive
    why_not: >
      That destroys the preregistration value and would allow the observed sample to
      choose its own acceptance law.
evidence:
  - "research/grey_deer/RISK_RADAR_PROSPECTIVE_VALIDATION_READINESS_PREREG_2026-09-24.md"
  - "engine/risk_radar_scorecard.py — risk_radar_prospective_validation_readiness.v1"
  - "tests/test_risk_radar_scorecard.py — supportive/refuting/immature/overlap falsifiers"
affects:
  - "WS:GREY-DEER-RISK-INTELLIGENCE"
  - "engine/risk_radar_scorecard.py"
  - "data/risk_radar/forward_log.jsonl"
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-24
---

## Non-authority boundary

The evaluator may emit not_started, not_mature, mature_refuting or
mature_supportive. Even mature_supportive leaves current_model_validated=false and
public_validation_ready=false. Any future validation/promotion is a separate effect.
