---
key: FS-5-FRAME-BUCKET-BINDING
claim: FS-5 build_geometry_plan must validate the requested model_bucket against BUCKET_HORIZONS and raise frame_bucket_mismatch when df["model_bucket"].iloc[0] contradicts the requested bucket — silent laundering of a 0_7 frame into an 8_90 or 90p plan is a display-tier authority leak.
falsifier: "python -m pytest -q tests/test_fs5_flow_geometry.py -k \"build_geometry_plan_refuses_frame_bucket_mismatch or build_geometry_plan_refuses_8_90_frame_for_90p_secondary\" -- if either test passes by accepting a 0_7 frame for an 8_90 or 90p request, this discovery is falsified."
so_what: "Future rounds that touch lib/flow_score_geometry.py:build_geometry_plan must preserve the validation block at lines 274-282; do not relax frame_bucket_mismatch to a warning, and do not move the model_bucket check below canonical_intervals (which would re-introduce silent laundering because canonical_intervals validates row identity, not row intent). A test added later that builds a 0_7 frame and requests an 8_90 plan must continue to fail loudly."
kind: constraint
verified_at: 2026-10-03
verified_by: "PR #8313 head fb1c73c089e; tests/test_fs5_flow_geometry.py::test_build_geometry_plan_refuses_frame_bucket_mismatch, test_build_geometry_plan_refuses_8_90_frame_for_90p_secondary; lib/flow_score_geometry.py:274-282"
scope: [lib/flow_score_geometry.py, tests/test_fs5_flow_geometry.py]
confidence: verified
---