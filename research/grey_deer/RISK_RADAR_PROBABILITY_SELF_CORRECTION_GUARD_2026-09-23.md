# Risk Radar Probability Self-Correction Guard — 2026-09-23

## Capability delta

Before: `engine/risk_radar_review.py` could propose `prob_cal` changes, but the
apply decision in `compare_calib()` judged only alert F1 plus the validated-leg
gate. A probability surface could therefore piggyback on a classification win even
if its displayed probabilities became numerically worse.

After: any proposal that changes `prob_cal` must pass a separate probability
do-no-harm gate in addition to the existing alert gate.

## Probability gate

For H5, H10 and H21, on both full usable history and the fixed 2020+ slice:

1. base and proposed evaluations must score the same native-price outcome population;
2. proposed Brier score must be no worse in every one of the six horizon/window cells;
3. at least one of those six Brier cells must improve strictly;
4. the H21 state-only authority partition relative to the shipped unconditional base
   rate must remain byte-for-byte equivalent in meaning.

The last constraint matters because `_market_state_authority()` uses the state-only
H21 above-base flag as one of its independent prerequisites for binding authority.
A calibration proposal is therefore not allowed to change which states can qualify
for veto authority as an accidental side effect of probability tuning.

The existing validated-leg gate and full/2020+ alert-F1 predicate remain controlling.
Band/leg-only proposals do not pay the probability-evaluation cost and preserve their
existing acceptance law.

## Real negative control

The preregistered pre-2020 state-only refit from PR #7715 was replayed through the
new guard. It preserves the authority partition and improves five of the six paired
Brier cells, but worsens modern H21 Brier by about +0.000965. The guard rejects it
with `reason=probability_brier_worse`.

That candidate therefore remains NOT promotion-eligible. No live probability,
calibration overlay, state machine, policy, sizing, ranking or capital authority
was changed by this work.

## Verification

- focused probability-guard / quality-report / review-evidence tests: 6 passed;
- full `tests/test_risk_radar_review.py`: 25 passed;
- `tests/test_risk_radar.py tests/test_risk_radar_scorecard.py`: 129 passed;
- Python compile: pass;
- `git diff --check`: pass;
- real OOS candidate guard replay: rejected for modern H21 Brier harm, identical
  outcome populations, authority partition preserved.

Evidence: `research/grey_deer/evidence/probability-guard-20260922/oos-candidate-gate.json`.

## Evidence ceiling

This is evaluator/governance hardening, not a new probability model. It does not
claim the existing probability surface is precision-grade and it does not authorize
a replacement surface. Issued/prospective forecast evidence remains a separate and
higher-authority calibration source.
