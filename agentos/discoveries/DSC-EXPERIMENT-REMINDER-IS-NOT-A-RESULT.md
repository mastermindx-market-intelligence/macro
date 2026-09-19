---
key: EXPERIMENT-REMINDER-IS-NOT-A-RESULT
claim: The legacy experiment projection can classify a record as results-ready solely
  because its come-back date has arrived. A live state line does not disambiguate
  that combined ready flag.
falsifier: Run `git show 459eafb838d9944e58e6a65413e282f2a13826ef:admin/experiments.py`
  and evaluate its _decorate against the same pinned site/marketdata/experiments.json
  on 2026-09-16; disprove the 44 legacy-ready count or show explicit per-row
  reader-result provenance in that artifact. The corrected counterexample is
  `python -m pytest tests/test_experiment_followup.py::test_due_seed_does_not_manufacture_results`.

so_what: Separate review_due from strict live-reader result_ready. During migration,
  report legacy result status as unknown rather than claiming zero actual results
  or validating date-driven flags. Keep evaluation and trade authority with their
  existing owners.
kind: landmine
verified_at: '2026-09-16'
verified_by: tests/test_experiment_followup.py; research/evidence/signal-lab-followup-readiness-20260916/legacy-snapshot-comparison.json;
  research/evidence/signal-lab-followup-readiness-20260916/verification.json
scope:
- research-factory
- macro:engine/experiments_registry.py
- macro:admin/experiments.py
confidence: verified
---

# Experiment follow-up semantics

The source repair is a derived projection, not a new experiment registry or scheduler. The isolated corrected legacy projection has 42 reviews due and 275 unknown result states; that is not a claim that no scientific results exist. Producer/admin/notification tests, fault-injection and full-admin browser receipts live in the referenced evidence directory. Source release and installed production proof remain separate. Continuation: research/SIGNAL_LAB_REVAMP_CONTINUATION_2026-09-16.md.
