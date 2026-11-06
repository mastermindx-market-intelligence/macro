---
key: GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION
claim: >
  In production, the ENGINE step still runs `scripts/build_thematic_state.py` in LEGACY mode:
  `.github/workflows/daily.yml:4646` invokes `python -m scripts.build_thematic_state` with no
  `--mode`, and both `build(..., mode="LEGACY")` (line 143) and argparse (lines 251-252)
  default to LEGACY. `generation.publish_generation(root, plan)` (line 171) is reached only
  under `if mode != "LEGACY":` (line 159), and no production step runs SHADOW or SUCCESSOR,
  so the generation publish path never executes in production. The LEGACY branch writes its
  artifacts directly with `generation.write_atomic` inside `generation.family_lock(root)`
  (lines 193-201). Since #8539 (gate #8 G1) a second production invocation exists:
  `daily.yml:5183` runs `--mode GRAPH_SHADOW_STATE` in the off-render oracle_offrender job.
  Its branch (lines 152-156) returns before the entry preflight and the publish path, and it
  writes only `data/theme_graph/shadow_theme_state.v1.json`, through `generation.write_atomic`
  inside `generation.family_lock` (`_write_shadow_graph_state`, lines 64-99).
falsifier: >
  Any of the following on origin/main:
  - `git grep -n -- "--mode SHADOW\|--mode SUCCESSOR" origin/main -- .github/ scripts/ engine/`
    returns a production invocation;
  - the engine job's thematic-state step in daily.yml passes any `--mode` (the separate
    `--mode GRAPH_SHADOW_STATE` step in oracle_offrender is expected and does not falsify);
  - `build()` or argparse in `scripts/build_thematic_state.py` gets a non-LEGACY default;
  - `publish_generation` is called on a path reachable when mode is LEGACY or
    GRAPH_SHADOW_STATE.
so_what: >
  Anything hooked only into `publish_generation`, or into the SHADOW/SUCCESSOR branches,
  never runs nightly and produces no production artifact. A new nightly artifact from this
  script gets its own narrow mode, invoked as its own step in an off-render job, and writes
  through `generation.write_atomic` inside `generation.family_lock`; G1's
  `--mode GRAPH_SHADOW_STATE` step (#8539, seat ruling G1-RC1) is the worked example. Never
  flip the production default mode to make a hook fire: that is a separate migration
  decision with its own owner.
kind: landmine
verified_at: 2026-10-06
verified_by: >
  `git show origin/main:scripts/build_thematic_state.py | grep -n "LEGACY\|GRAPH_SHADOW_STATE\|publish_generation\|family_lock\|write_atomic"`
  at origin/main f8d4da2aceadf15df41329c71a15b8071b3ca7ae (lines 51, 64-99, 143, 150-159, 171, 193-201, 251-252).
  `git grep -n "build_thematic_state" origin/main -- .github/workflows/` finds two production
  calls: daily.yml:4646 (engine job, no --mode) and daily.yml:5183 (oracle_offrender,
  --mode GRAPH_SHADOW_STATE). The SHADOW/SUCCESSOR git grep returns nothing. First verified
  at 79b566f5c0cc, before #8539.
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

Amended the same day after #8539 landed. The shadow file now comes from the dedicated
GRAPH_SHADOW_STATE step, so the OWNER_UNAVAILABLE consequence above is expected to clear on
the first nightly that commits it. That stays unverified until the 2026-10-07 nightly receipt.
