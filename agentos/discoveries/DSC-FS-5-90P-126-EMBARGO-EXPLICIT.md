---
key: FS-5-90P-126-EMBARGO-EXPLICIT
claim: config/flow_score.yml.embargo_days.90p is the observed config value 126 for the 90p bucket, and BUCKET_HORIZONS["90p"] in lib/flow_score_geometry.py is registered at (63, 126). The trainer pins the actual embargo at fit time to max(configured, max((63, 126))) = 126 in the train_bucket body of scripts/ops_train_flow_score.py (lines 761-764), so a configured 63 would be raised to 126 at fit time; the config currently mirrors 126 for clarity, not because the trainer rejects 63.
falsifier: "python -m pytest -q tests/test_fs4_flow_trainer.py::test_90p_embargo_days_explicit_126 tests/test_fs4_flow_trainer.py::test_90p_horizons_registered_secondary_126 -- both must pass. Reading lib/flow_score_geometry.py:BUCKET_HORIZONS for 90p must show (63, 126). Reading config/flow_score.yml:embargo_days.90p must show 126. scripts/ops_train_flow_score.py must compute embargo as max(configured, max(BUCKET_HORIZONS[bucket])) for the 90p bucket."
so_what: "Future rounds that touch config/flow_score.yml must keep embargo_days.90p at 126 (numeric value parsed by test_90p_embargo_days_explicit_126). BUCKET_HORIZONS in lib/flow_score_geometry.py must remain {0_7: (5,), 8_90: (21,), 90p: (63, 126)}; adding a new bucket is an amendment, not a config edit. The trainer's max(configured, max(horizons)) clamp is the actual binding mechanism — config drift is caught by the numeric assertion, not by inferring runtime behavior from comment wording."
kind: constraint
verified_at: 2026-10-03
verified_by: "PR #8313 head fb1c73c089e; tests/test_fs4_flow_trainer.py::test_90p_embargo_days_explicit_126, test_90p_horizons_registered_secondary_126; config/flow_score.yml:57-64; lib/flow_score_geometry.py:32-38; scripts/ops_train_flow_score.py:761-764"
scope: [config/flow_score.yml, lib/flow_score_geometry.py, scripts/ops_train_flow_score.py, tests/test_fs4_flow_trainer.py]
confidence: verified
---