# Risk Radar Prospective Validation Readiness — 2026-09-24

## Capability

The prospective probability audit now publishes a machine-readable
`validation_readiness` block for the latest exact Risk Radar model cohort.

It answers whether the evidence is:
- not started;
- not mature;
- mature but refuting; or
- mature and supportive enough for a **separate** promotion review.

It cannot validate the model automatically.

## Frozen bar

Protocol commit: `7bc85b604a130e01b57b45db1e6430c292874a41`.

Common maturity:
- >=252 issued same-model sessions;
- >=300 calendar-day span.

Per H5/H10/H21:
- >=200 graded rows;
- >=20 event rows;
- >=50 non-event rows;
- >=5 overlap-aware event clusters;
- complete paired baseline and clean graded population;
- paired Brier delta < 0 with 90% circular moving-block CI upper bound < 0;
- 90% moving-block CI for mean forecast-minus-outcome residual contains zero.

Bootstrap: 2,000 draws; block length = horizon; fixed seed family 240924+horizon.

## Product/authority boundary

The scorecard emits:
- `authority_h21_supportive` — evidence about the horizon used by Market-State authority;
- `full_surface_supportive`;
- `promotion_review_eligible`.

Even when all are supportive:
- `current_model_validated=false`;
- `public_validation_ready=false`.

No score, state, probability, gate, policy, sizing, ranking, ledger row or capital
authority changes from readiness metadata.

## Real historical proof

The committed forward ledger at method freeze:
- rows: **52**;
- SHA-256: `f42c11c0962d4a1e7f673d6510ec0c071b7e3a34077a03964c444a8d81282e14`;
- prospective same-model rows: **0**;
- excluded as `missing_issue_receipt`: **52**;
- readiness status: **not_started**.

This proves the capability does not backfill or upgrade historical rows.

## Verification

- focused readiness falsifiers: 5 passed;
- full Risk Radar scorecard suite: 80 passed;
- Risk Radar scorecard-card reader suite: 20 passed;
- Python compile: pass;
- `git diff --check`: pass.

Frozen implementation commit: `75d21ff6b478687971126a8790cda825bdd683f7`.
Scorecard SHA-256: `122025b98da098d1da8dc7f9a980fa2d31d5e4e29b128c1481725b9e73583634`.
Test SHA-256: `0386f84b5235017e1a9cdbad50221993806fdb45961ba86472204ba7c7da5c1b`.
Protocol SHA-256: `94dde0082762a62e5212f4826f376583bc082fb34babd46172a310bccdf38840`.
