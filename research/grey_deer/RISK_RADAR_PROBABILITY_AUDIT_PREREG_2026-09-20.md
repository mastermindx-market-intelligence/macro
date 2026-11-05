# Risk Radar probability audit — frozen descriptive protocol

Authority: Chairman's current instruction to upgrade Risk Radar, risk research and models.
Operation: risk-radar-forecast-evidence-20260920. Owner: Sol; no worker START or transfer.
Protected Skillpack: Mastermind b75a491db408892dfe6fe7c4bb9d40cfad8efcb3, v1.0.1/bootstrap 1.
Base: macro 9a481ef520e397853c9f5a8edd120cfff528ce16. Freeze before inspecting ledger outcomes.
Direct execution: PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD for one bounded diagnostic.

## Capability and boundaries
Extend the existing risk_radar_scorecard owner; consume its result inside the existing
Risk Radar Method & track record disclosure. No new ledger, scheduler or grading owner.
US-only first slice: do not consume or release PR6989's held international candidate.
No new probability, tuning, rank/size/gate/execute authority or GD-5 promotion is permitted.

## Fixed evaluation
Target: the recorded >=5% SPY close-relative pullback within h5/h10/h21 sessions,
not intraday loss, peak-to-trough maximum drawdown, or an alert classification.
Use only recorded drawdown_prob[horizon], base_[horizon] and graded.hit[horizon].dd5.
No recomputation or repair of outcomes, no substituting today's base rates or calibration.
Require explicit SPY/5% target, valid ISO date, finite numeric probabilities in [0,1],
boolean outcome, and ordered timezone-aware logged/graded receipts no later than audit date.
A receipt order is NOT proof of publication before the first outcome bar; disclose that gap.
Deduplicate exact identical dates once; exclude all conflicting duplicates. Never pick a winner.
Report per-horizon eligible/excluded counts, mean forecast, observed frequency, binary Brier
loss and SAME-ROW recorded-base Brier comparison. Missing baselines do not erase model rows.
Fixed bins: [0,.1), [.1,.2), [.2,.4), [.4,.6), [.6,1]. Existing min-n=5 disclosure floor;
this is not a statistical validation threshold. Show null, never zero, below the floor.
Daily overlapping forecasts are not independent episodes: no p-values, confidence intervals,
independent-N claim, significance, calibration PASS or trading permission from this audit.

## Acceptance
Existing scorecard fields unchanged; additive US probability_audit only. Deterministic,
input-immutable helper, hostile/missing-data tests, exact matched-denominator oracle,
discrimination against parent, real-ledger diagnostic, and consumer render/browser proof.
Source ledger hashes must remain unchanged. Research result is historical/descriptive,
not proof of current-model validity or natural-time out-of-sample performance.
UI uses existing typography, surfaces and collapsed detail; dark/light x EN/ZH x 1440/390.

## Method references
Gneiting & Raftery (2007), Strictly Proper Scoring Rules, Prediction, and Estimation:
https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf
Scikit-learn, probability calibration and probabilistic scoring documentation:
https://scikit-learn.org/stable/modules/calibration.html
These justify probabilistic loss/reliability checks, not a financial predictive-edge claim.
