# Q04 PREREG amendment 1: wording and disclosure only

- Amends: `PREREG.md`, sha256 `b74dae57b5050fc756a374354409740d09d49808a5d419ddd85fe032acdd88fd`, frozen 2026-10-09T09:32:25Z (FREEZE.log). PREREG.md is not edited.
- Author: finisher session (claude-opus-5-5), acting on the independent audit (PASS_WITH_FIXES, majors=1).
- Written before any new outcome was read. The only planned re-run after this amendment is one `--mode evaluate` call. Its purpose is to record code identity after wording-only edits to the module and logging-only edits to evaluate.py. The decisional numbers are expected to reproduce byte-identically. Any difference would be reported, not tuned.

## Reason

PREREG §2 (E2) calls the bounds [N_id − U, N_id + U] "sharp location-only bounds". It also describes U as the share "whose sign is NOT identified by exact-edge execution location". Mapping an at-ask print to a buyer and an at-bid print to a seller is the quote rule's own premise. Retained data holds no independent aggressor label, so that premise cannot be tested here. The bounds are therefore sharp only under a maintained, untested assumption. Without it they are too narrow, and the reported U understates the true unidentified share. Requirement 1 of the brief forbids exactly this kind of false precision.

## Amended reading (no change to any estimand, formula, cohort, split, threshold or decision rule)

1. **Maintained edge-sign assumption.** All "identified" quantities in E2 are conditional on this assumption: at-ask = buyer-initiated, at-bid = seller-initiated. The module exposes it as `EDGE_SIGN_ASSUMPTION`.
2. **Bounds.** Read "sharp location-only bounds" as "edge-location-conditional bounds". They are sharp only given the assumption, and too narrow if any edge print is mis-signed.
3. **U.** Read U as a lower bound on the true unidentified premium share. Relaxing the assumption can only move edge premium into the ambiguous pool.
4. **Label robustness.** Read "identified-robust" as "robust to the edge-location-conditional bounds". It is not evidence that a label is correct.
5. **Unchanged.** The H1 comparison, the skill bar, the minimum session counts, F1–F3 and the INSUFFICIENT_DATA verdict are untouched. Result keys such as `labeled_identified_robust` keep their names for byte-stable outputs and carry the meaning in item 4.

## Logging changes (evaluate.py; no effect on computation)

- `raw_cache_present` is now logged as `flag raw_cache_present=<bool>`, not as a sha256 field.
- Every RUN entry now opens with `code <path> sha256=<hash>` lines for `engine/flow_sign_uncertainty.py`, `evaluate.py` and this amendment.
