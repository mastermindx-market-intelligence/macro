---
key: FABRIC-LANE-RUNTIME-LOAD-RATIO-FLOOR
claim: >
  After the Chairman's 2026-10-13 thermal-headroom admission policy (ext/hosts.json: load_gate 8 on
  the 32-core ubuntu0/ubuntu2/ubuntu3, exported to lanes as LANE_MAX_LOAD_RATIO=0.2500), every NEW
  fabric lane launched on those hosts died at startup (rc=1, no usage receipt, model never started)
  with `LaneRuntimeConfigError lane_max_load_ratio_out_of_bounds`, because the kit runtime
  `ext/lane_runtime.py` enforced a hardcoded MIN_LOAD_RATIO=0.5 BEFORE admission while the local
  picker (`pool hosts`) still scored the same hosts ELIGIBLE; the floor is now strict-positive
  (0 < ratio <= 1.5, parity with the local registry check) and ships as support generation
  418419b90923b800afadc605988874f4489ee023fb35dd3d70da397fa46b4ce6, which each host installs on
  its first launch.
falsifier: >
  Restore MIN_LOAD_RATIO = 0.5 in the meta-ceo-b kit's ext/lane_runtime.py (backup
  lane_runtime.py.bak-load-ratio-floor-20261013) and have a new lane admitted on ubuntu2 under the
  0.25 policy, or run `python3 -m pytest ext/tests/test_load_ratio_floor_20261013.py` against that
  restored runtime and see all four tests pass; or launch a new lane on ubuntu0/ubuntu2 under the
  418419b9 generation and have it refused with lane_max_load_ratio_out_of_bounds. Any of these
  disproves the claim.
so_what: >
  When `pool hosts <pool>` says ELIGIBLE but every new lane on that host dies rc=1 before the model
  starts, grep the lane .out / ext/state/remote_sub/<run-id>.log for `out_of_bounds|LaneRuntimeConfigError`
  before blaming the model, escalating the tier, or re-placing the work onto mb. Fix runtime bounds in
  the kit and ship a NEW support generation; never hand-patch ~/lanes/support-releases/<digest>/ on a
  host and never clamp the ratio in remote_sub.sh (a 0.5 clamp would loosen the Chairman's load1-8
  gate to 16 because remote_sub_exec.py admits on the exported env value, not on a flag). Place
  bailian/qwen lanes on ubuntu0/ubuntu2, never mb (single-account host -> OUTER_LEASE_ACCOUNT_MISMATCH
  rc=75).
confidence: verified
kind: runtime
verified_at: 2026-10-13
verified_by: >
  OPUS-P2 progress 09:04Z (ce-p03-rev2-1013 on ubuntu2 FAILED AT STARTUP rc=1, lane_runtime
  LaneRuntimeConfigError lane_max_load_ratio_out_of_bounds); kit ext/lane_runtime.py MIN_LOAD_RATIO /
  load_runtime_config bound check and ext/remote_sub_exec.py:169 LaneLease.acquire(env=os.environ)
  with no load_ratio_limit; ext/remote_sub.sh:404 (ratio = load_gate/cores) and :946
  (LANE_MAX_LOAD_RATIO export); new test ext/tests/test_load_ratio_floor_20261013.py (4 tests fail
  with lane_max_load_ratio_out_of_bounds on the backup runtime, pass on the fixed one); live proof
  lane ce-smoke-1013 on ubuntu2 (minimax-m3): SUPPORT_VERSION_READY digest=418419b9..., LAUNCH_ATTEMPT 1,
  REMOTE_DONE rc=0, OUTPUT_CONTRACT_MATCHED, DONE rc=0; `ssh ubuntu2 grep -n "MIN_LOAD_RATIO = "
  ~/lanes/support-releases/418419b9.../ext/lane_runtime.py` -> line 53 `MIN_LOAD_RATIO = 0.0  # exclusive`.
scope:
  - fabric
  - orchestration
  - handoff_kits/meta-ceo-b-2026-09-08/ext/lane_runtime.py
---

Caveats: ext/hosts.json (the Chairman's policy) and the rollback file hosts.json.bak-thermal-headroom-20261013
were not touched; the `--load-ratio` launcher flag reaches only go_remote_run.py in go-codex mode, so
the env export is the sole admission input for grok/glm/qwen/minimax lanes. Two kit test files
(tests/test_remote_admission_backpressure.py and test_remote_sub.py::test_missing_project_worktree_refused_before_provider_lease)
were already red before this change: their fixture copies the support closure and ext/pools.yaml is
absent in this kit layout — a missing fixture, not a regression.
