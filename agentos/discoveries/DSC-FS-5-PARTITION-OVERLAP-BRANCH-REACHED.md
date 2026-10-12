---
key: FS-5-PARTITION-OVERLAP-BRANCH-REACHED
claim: lib/flow_score_geometry.py:validate_population_partition MUST check the global cross-root inclusive label-window union BEFORE the dict-order or chronological checks; a violated cross-population label-window overlap is partition_label_window_overlap, never partition_not_chronological — the chronology branch is reserved for actual order or gap violations, not overlap.
falsifier: "python -m pytest -q tests/test_fs5_flow_geometry.py -k \"calibration_crossing_refuses\" -- if the test now reports partition_not_chronological instead of partition_label_window_overlap, or if moving the overlap check below the chronology check still passes the test, this discovery is falsified."
so_what: "Future rounds that touch validate_population_partition must preserve the leading overlap loop at lines 306-314; the duplicate trailing loop at lines 397-400 is unreached-dead-code and may be removed in a cleanup pass, but the leading loop is load-bearing for the overlap branch. Adding a new ordered-population must include its inclusive label-window interval in the same overlap iteration, never in a chronology-only step."
kind: constraint
verified_at: 2026-10-03
verified_by: "PR #8313 head fb1c73c089e; tests/test_fs5_flow_geometry.py::test_calibration_crossing_refuses; lib/flow_score_geometry.py:306-314"
scope: [lib/flow_score_geometry.py, tests/test_fs5_flow_geometry.py]
confidence: verified
---