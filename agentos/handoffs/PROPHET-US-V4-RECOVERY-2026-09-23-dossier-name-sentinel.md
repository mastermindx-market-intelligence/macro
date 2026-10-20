---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: dossier-canonical-name-sentinel-20260923
model: sol
ended_because: ci_handoff
prs: []
mission: >
  Unblock legitimate stock-dossier publication while preserving every actual
  non-finite-value and identity guard, within the Chairman's recovery mandate.
state_before: >
  Native render35709199694 failed its integrity step on nine occurrences of
  Infinity in the same canonical issuer name; R2 and site publication were skipped.
changed:
  - path: scripts/check_stock_dossier_integrity.py
    what: Reuse canonical same-hub identity for exact multiword text spans; never exempt numeric values or pages.
  - path: tests/test_check_stock_dossier_integrity.py
    what: Twelve cases distinguish legitimate identity text from true sentinel leakage and wrong/missing canonical identity.
verified:
  - claim: Existing sentinel and end-to-end identity owner tests pass; true invalid values still fail on the same named page.
    command: python3 -m pytest -q tests/test_check_stock_dossier_integrity.py tests/test_dossier_identity_end_to_end.py
    result: 59 passed on Python3.14; same59pass under3.12. Original candidate-positive fixture failed before correction.
unverified:
  - claim: Current-source independent acceptance and normal deployed publication.
    what_would_verify: Actual review, hosted CI and original publisher integrity/commit/readback evidence after release.
unresolved:
  - Source-main packing regression126>125 remains a separate real release gate with owner issue6351.
  - Already missing stock assessments are not restored by this source change.
next_actions:
  - Obtain independent exact-source review, conclude CI, release through the existing merge owner and observe the normal publisher.
do_not_redo:
  - Do not duplicate or rerun the terminated render blindly; its site/R2 publication steps were skipped.
  - Do not remove the Infinity pattern, whitelist INR, exempt a whole page or weaken identity/sentinel checks.
  - Do not retry the separate denied UK-scope worker's Python commands through another carrier.
danger_areas:
  - A source guard correction is not proof of restored live stock coverage.
---

Procedure: Mastermind@a5aa42d15c3e5cbfe785b415511de188cff66bd0.
Source: macro@1d784190ee690959cfca62af65ab6eea766f053e.
Carrier: sol/dossier-canonical-name-sentinel-20260923.
Evidence and exact negative controls: research/stock_dossier_sentinel_20260923/.
Original production failure and source diagnostic boundary returned to#6351/comment5790985223.
No new model/entry/score/price/data-access/runner/publication authority.
MISSION_COMPLETE:false. Current capability BUILT_NOT_PROVEN.
