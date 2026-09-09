---
key: REGIME-FILTERED-HISTORY-USES-LATER-FIT
claim: >
  RegimeOne historical forward-filtered probabilities use parameters fitted on the entire supplied frame;
  the reconstructed history is not an immutable record of earlier issued beliefs.
falsifier: >
  Run tests/test_regime_one.py::test_hmm_history_discloses_reconstruction_after_future_extension;
  a source change that fits each historical point only on its available prefix and makes unchanged
  prefix estimates invariant to later observations would supersede this construction-specific finding.
so_what: >
  Do not use history_filtered or its momentum as historical as-issued evidence. Read the existing
  regime_fwd_hmm.jsonl record through read_hmm_issuance; missing or ambiguous dates stay unavailable.
  Recorded predictions and timestamps still do not certify source-vintage eligibility.
kind: landmine
verified_at: 2026-09-09
verified_by: >
  engine/regime_one.py at c3d7f1d4149176e35abf6077c18c96513abe6600; synthetic seed90210
  prefix-extension experiment changed all132 shared historical rows, maximum absolute delta0.7111;
  regression and real-ledger read-only CLI evidence in research/artifacts/regime_history_honesty_20260909/.
scope: [macro, market-regime-risk, engine/regime_one.py, engine/quad_vector.py]
confidence: verified
---

The current endpoint can remain a valid current estimate when its inputs were available by issuance.
This finding does not establish that any live portfolio consumed leaked probabilities or quantify an
actual investment loss. W0 preserves numeric estimates and adds explicit reconstruction semantics.
The inspected main-pinned prediction ledger contains40 rows, June30–September8, without historical
issuance/model metadata; these remain useful saved observations, not retroactively certified forecasts.
The original research's HMM-baseline description was corrected: main passes0.25, not the helper's0.5.
