---
key: REGIME-HMM-FORWARD-GATE-MIS-SPECIFIED
claim: >
  The current regime_fwd_hmm grading path cannot establish HMM +21 predictive skill: it stores a
  contemporaneous filtered state posterior but scores its modal state against a later quad, reads the
  realized state from mutable rewritten regime_history, and uses a raw-row Wilson gate despite overlapping
  +21-observation horizons. The live RegimeOne status projection additionally reads a doubled /regime path.
falsifier: >
  Superseded only by accepted source proving a prospective issuance-time +21 distribution from the frozen
  information set, correction-safe as-issued outcome maturity, strong same-cutoff baselines, dependence-aware
  uncertainty, and a correct canonical ledger status read, followed by natural production evidence.
so_what: >
  Treat the existing HMM ledger as saved current-state/persistence-probe evidence, not forward HMM admission
  evidence. Finish #7015 temporal honesty without widening it; build explicit anticipation as a later bounded
  W2 carrier. Do not enable or promote the existing grader to manufacture a GO.
kind: landmine
verified_at: 2026-09-13
verified_by: >
  Macro main a6939ca6f8e6bfea6e4e765d2cfe8e16ec607fdb and PR #7015 pre-addendum head
  0bd578085ee2e51e27de6b8610794a88cbbc28f8. Current ledger has 43 rows through 2026-09-11 with
  realized_quad_at_21d null; committed regime_one.json reports grading n=0. Research freeze is
  research/HMM_PROSPECTIVE_ADMISSION_CONTRACT_2026-09-13.md.
scope: [macro, market-regime-risk, engine/regime_one.py, scripts/validate_regime_fwd.py]
confidence: verified
---

The parent HMM research already required `p_(t+h|t) = p_t A^h`, proper probabilistic scoring, strong
baselines, and accounting for overlapping horizons. This discovery records that current source has not yet
implemented those requirements in the forward-grade path.

US `engine.run` rewrites `data/regime/regime_history.parquet`, so later reconstruction must not become the
sole realized target authority. `data/regime/freshness_ledger.jsonl` is an existing append-only candidate for
the as-issued target state, subject to exact target-date and degradation handling in W2.

No trading authority follows from this discovery. A published null remains an acceptable final result if a
proper prospective W2 forecast fails the frozen evidence gate.