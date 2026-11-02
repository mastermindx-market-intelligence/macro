---
key: FS-5-FOLD-GEOMETRY-NO-FIT-GUARD
claim: scripts/ops_train_flow_score.py:train_bucket MUST wrap _group_fold_splits in a GeometryError no-fit guard that returns make_no_fit_health("method_geometry_unavailable:fold_geometry_invalid:<reason>") BEFORE any feature, estimator, or calibrator fit; an invalid fold geometry (k_folds=0, embargo violation, group imbalance) is a hard no-fit, never a swallowed-then-fitted call.
falsifier: "python -m pytest -q tests/test_fs4_flow_trainer.py -k \"zero_fold_request_returns_no_fit\" -- if estimator_calls or calibrator_calls is non-empty when k_folds=0, or if the trainer returns a fitted model with method_geometry: available instead of method_geometry: unavailable, this discovery is falsified. Also: a manual monkey-patch that deletes the GeometryError catch around _group_fold_splits and observes any subsequent .fit would falsify it."
so_what: "Future rounds that touch scripts/ops_train_flow_score.py must keep the GeometryError-except branch immediately around _group_fold_splits; do not move the import of build_geometry_plan out of the file (train_bucket uses it for plan construction before fold-grouping), and do not relax the guard to log-and-proceed. Adding a new fold-grid branch beyond session_atomic / chronological / disjoint must also sit behind the same guard, never in front of it."
kind: constraint
verified_at: 2026-10-03
verified_by: "PR #8313 head fb1c73c089e; tests/test_fs4_flow_trainer.py::test_zero_fold_request_returns_no_fit_and_trainer_canaries_never_fit; scripts/ops_train_flow_score.py:train_bucket"
scope: [scripts/ops_train_flow_score.py, tests/test_fs4_flow_trainer.py]
confidence: verified
---