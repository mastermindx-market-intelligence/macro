---
key: FS-5-90P-126-EMBARGO-EXPLICIT
claim: config/flow_score.yml.embargo_days.90p is the gate config value 126 for the 90p bucket, and BUCKET_HORIZONS["90p"] is locked at (63, 126); the trainer's max(configured, max((63, 126))) = 126 binding target is the registered horizon, and a configured value below 126 must NOT silently raise to 126 at fit time — config drift here breaks the test_90p_requires_primary_and_secondary_horizons embargo floor.
falsifier: "python -m pytest -q tests/test_fs4_flow_trainer.py -k \"90p_embargo_days_explicit_126 or 90p_horizons_registered_secondary_126\" -- if either test fails, or if the trainer ever accepts embargo_days.90p=63 as a complete binding, this discovery is falsified. Reading lib/flow_score_geometry.py:BUCKET_HORIZONS for 90p must show (63, 126)."
so_what: "Future rounds that touch config/flow_score.yml must keep embargo_days.90p at 126 with the load-bearing comment substring '# ≥ 126 NYSE sessions; 90p secondary 126-session target' (test_90p_embargo_days_explicit_126 asserts on a substring of that comment). BUCKET_HORIZONS in lib/flow_score_geometry.py must remain {0_7: (5,), 8_90: (21,), 90p: (63, 126)}; adding a new bucket is an amendment, not a config edit."
kind: constraint
verified_at: 2026-10-03
verified_by: "PR #8313 head fb1c73c089e; tests/test_fs4_flow_trainer.py::test_90p_embargo_days_explicit_126, test_90p_horizons_registered_secondary_126; config/flow_score.yml:60-64; lib/flow_score_geometry.py:32-38"
scope: [config/flow_score.yml, lib/flow_score_geometry.py, tests/test_fs4_flow_trainer.py]
confidence: verified
---