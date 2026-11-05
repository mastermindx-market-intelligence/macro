---
key: GMI-NEURAL-WEB-THEME-STATE-REGISTRY-UNCHANGED-THROUGH-STEP-7
claim: >
  Recovery steps 2 through 7 (#9423, #9645, #9644, #9670, #9652, #9641, #9745 and the
  step-7 diagnostic and operating-proof lanes) added no Neural Web artifact and no
  producer. On origin/main 04cc542a51d8 the config/synapse.yml entries theme-state
  (data/neuralweb/theme_state.json) and site-theme-state still name
  scripts/build_thematic_state.py as the sole producer with known_extra_writers [],
  tier display, weights none; the GRAPH_SHADOW_STATE generation is read only through
  engine/theme_graph/theme_state_owner_readers.py (StateQualificationReader) and the
  diagnostic-only publication_applicability in engine/theme_graph/theme_state.py; no
  third ThemeState producer or store exists. The A2 activity-membership history fold
  in engine/theme_graph/materialize.py is a pure function that no nightly job calls.
falsifier: >
  On a current origin/main run git grep -n "neuralweb" -- engine/theme_graph/ scripts/
  and python3 -m pytest tests/test_synapse_registry.py tests/test_synapse_registry_contract.py
  tests/test_synapse_read_gate.py -q. A new synapse.yml entry whose producer lives under
  engine/theme_graph/ or scripts/*theme_graph*, a non-empty known_extra_writers on
  theme-state, a data/neuralweb path written by a GMI module, or a nightly job step that
  calls the ACTIVITY_HISTORY fold refutes the claim.
so_what: >
  The development closeout law's "Neural Web state authority reconciled" condition is
  satisfied by inspection and the registry suite, not by a migration: the LEGACY
  theme_state.json stays the display organ, the shadow generation stays an owner-read
  diagnostic, and the one open ThemeState obligation is the producer-side wiring (history
  fold into the build, GRAPH_SHADOW_STATE mode in the off-render job), which is a source
  change with production effect owned by the ThemeState producer path, never a records
  edit. Do not add a synapse.yml entry for the history fold until a job actually writes it.
kind: architecture
verified_at: 2026-10-19
verified_by: >
  Fable Meta-CEO seat 6f14c2da: git show origin/main:config/synapse.yml theme-state and
  site-theme-state blocks; git grep of engine/theme_graph for neuralweb paths (none);
  pytest of the three synapse registry suites on 04cc542a51d8 in the sparse records
  worktree, 52 passed; read of materialize.py ACTIVITY_HISTORY_* constants and
  theme_state_owner_readers.py.
scope:
  - macro
  - config/synapse.yml
  - data/neuralweb/theme_state.json
  - engine/theme_graph/materialize.py
  - engine/theme_graph/theme_state_owner_readers.py
  - engine/theme_graph/theme_state.py
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
  - DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19
---

The W-G3 census (#8552) found the same registry consistency on 04514a2c51a0; this record
re-verifies it after six more merged steps and names the exact producer-side act still owed,
so a later session does not mistake "no new producer" for "nothing left to wire".
