# Risk Radar Prospective Validation Readiness — Preregistration

Status: frozen before any receipt-bearing prospective Risk Radar outcome exists.

Parent prospective-identity candidate: `9d4e1a27c28fec379651da3324d90b2f9495c94b`.
Protected procedure: `mastermindx-market-intelligence/Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1.

## Job

Turn the future receipt-bearing forward ledger into an executable answer to:

> Is the latest exact Risk Radar model cohort statistically mature and supportive enough to deserve a separate promotion review?

This wave **cannot** set `current_model_validated=true`, change Market-State authority, alter probabilities, recalibrate the model, or promote anything automatically.

The output vocabulary is only:
- `not_started`
- `not_mature`
- `mature_refuting`
- `mature_supportive`

A `mature_supportive` result means “eligible for a separate human/CEO promotion decision,” not “validated.”

## Evidence population

Use only rows admitted by `probability_audit.prospective` for the latest exact:
- prospective epoch;
- `model_fingerprint`;
- issue-receipt contract;
- nightly first-writer lane.

Never backfill historical rows and never mix prior model fingerprints.

Evaluation uses the same issued H5/H10/H21 probability and paired unconditional baseline stored on each admitted row. Outcomes are the existing forward grader’s >=5% maximum-loss booleans.

## Frozen maturity floor

The latest exact model cohort is not mature until all hold:

1. at least **252 issued sessions**;
2. first-to-latest issue span >= **300 calendar days**;
3. each horizon has at least **200 graded rows**;
4. each horizon has at least **20 event rows** and **50 non-event rows**;
5. each horizon contains at least **5 distinct event clusters**.

An event cluster groups event-positive issue rows whose positions are separated by no more than that horizon’s observation length. This deliberately treats overlapping daily warning windows around one selloff as one episode-like cluster rather than independent events.

These are evidence floors, not fit parameters. They may not be changed after prospective outcomes are observed.

## Frozen statistical tests

For each H5, H10 and H21, on the exact same admitted rows:

### 1. Paired Brier skill
Compute row-level:

`delta_i = (issued_probability_i - outcome_i)^2 - (base_probability_i - outcome_i)^2`

Require:
- mean paired Brier delta < 0; and
- 90% circular moving-block bootstrap CI upper bound < 0.

Block length = horizon observations (5, 10 or 21).
Bootstrap draws = **2000**.
Seed = **240924 + horizon**.

### 2. Calibration-in-the-large
Compute residual `issued_probability - outcome`.

Require the 90% circular moving-block bootstrap CI for its mean to contain 0.

This asks whether the cohort shows detectable systematic over/under-forecasting without fitting a recalibrator to the same sample.

### 3. Complete pairing
Every graded row used by the evaluator must carry a valid paired baseline. Any missing baseline makes that horizon not ready.

## Frozen readiness outputs

Per horizon:
- `mature`
- `brier_supportive`
- `calibration_supportive`
- `supportive = all three`

Aggregate:
- `authority_h21_supportive` = H21 supportive only. This is evidence about the horizon used by Market-State authority, **not authority activation**.
- `full_surface_supportive` = H5, H10 and H21 all supportive.
- `status`:
  - no receipt cohort -> `not_started`
  - maturity floor incomplete -> `not_mature`
  - mature but any statistical test fails -> `mature_refuting`
  - all three horizons supportive -> `mature_supportive`

Always emit:
- `current_model_validated=false`
- `public_validation_ready=false`

Public-page first-publication timing is outside this evidence source and cannot be inferred from the ledger issue receipt.

## Integrity

The evaluator must:
- fail closed on malformed/duplicate conflicting rows;
- preserve exact model-fingerprint cohort boundaries;
- report issue/grade exclusions;
- never write the forward ledger, scorecard, calibration overlay or runtime state;
- have discriminating synthetic tests for supportive, refuting, immature, mixed-model and overlapping-event cases.

No second threshold set or alternate readiness candidate may be fit to the first real prospective results in this wave.
