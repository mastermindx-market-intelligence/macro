---
key: GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION
claim: >
  In production, `scripts/build_thematic_state.py` always runs in LEGACY mode. The nightly
  step `.github/workflows/daily.yml:4646` invokes `python -m scripts.build_thematic_state`
  with no `--mode`, and both `build(..., mode="LEGACY")` (line 65) and argparse (line 168)
  default to LEGACY. `generation.publish_generation(root, plan)` (line 88) is reached only
  under `if mode != "LEGACY":` (line 76). So the generation publish path never executes in
  production. The LEGACY branch writes its artifacts directly with
  `generation.write_atomic` inside `generation.family_lock(root)` (lines 110-118).
falsifier: >
  Any of the following on origin/main:
  - `git grep -n -- "--mode SHADOW\|--mode SUCCESSOR" origin/main -- .github/ scripts/ engine/`
    returns a production invocation;
  - the daily.yml thematic-state step passes a non-LEGACY `--mode`;
  - `build()` or argparse in `scripts/build_thematic_state.py` gets a non-LEGACY default;
  - `publish_generation` is called on a path reachable when mode == "LEGACY".
so_what: >
  Anything hooked only into `publish_generation`, or into the SHADOW/SUCCESSOR branches,
  never runs nightly and produces no production artifact. Example: a gate #8 shadow
  ThemeState file that `engine/theme_graph/selection_cohort_reads.py` loads. A new
  nightly artifact from this script must be written in the LEGACY branch, inside the
  existing family lock, through `generation.write_atomic` (the G1 design on PR #8324's
  gate #8 Phase 2). Do not flip the production default mode to make a hook fire: that is a
  separate migration decision with its own owner.
kind: landmine
verified_at: 2026-10-06
verified_by: >
  `git show origin/main:scripts/build_thematic_state.py | grep -n "LEGACY\|publish_generation\|family_lock\|write_atomic"`
  at origin/main 79b566f5c0cc (lines 65, 72, 76, 88, 110-118, 168). Running
  `git grep -n "build_thematic_state" origin/main -- .github/workflows/` finds a single
  production call (daily.yml:4646, no --mode). The SHADOW/SUCCESSOR git grep returned nothing.
scope:
  - macro
  - scripts/build_thematic_state.py
  - engine/theme_graph/
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

Found on 2026-10-06 while scoping gate #8 Phase 2 (G1). The qualified-reads owner,
`selection_cohort_reads.py`, returns OWNER_UNAVAILABLE whenever
`data/theme_graph/shadow_theme_state.v1.json` is absent. If that file were written only
from the generation publish, it would stay absent in production forever, and every
qualified read would fail closed, without any error being raised.
