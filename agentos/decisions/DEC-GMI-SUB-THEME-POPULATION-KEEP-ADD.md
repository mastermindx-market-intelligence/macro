---
key: GMI-SUB-THEME-POPULATION-KEEP-ADD
question: >
  When the first sub_theme population lands, should the 27 micro_themes placed under a new
  sub_theme KEEP their existing direct theme->micro_theme PARENT_OF rows and gain the new
  theme->sub_theme->micro_theme chain beside them (KEEP+ADD), or should the direct rows be
  REPLACED by the chain?
answer: >
  KEEP+ADD. #8999 added 12 sub_theme declarations, 12 theme->sub_theme rows and 27
  sub_theme->micro_theme rows, every one asserted_on 2026-10-13, and kept all 93 existing
  rows. The crosswalk now carries 10 categories, 12 sub_themes, 68 micro_themes and 132
  parents (21 category->theme, 12 theme->sub, 27 sub->micro, 72 theme->micro). Each of the 27
  micro_themes therefore has two consistent parent chains (the sub_theme's own parent theme
  equals the micro_theme's direct theme parent, 27 of 27). The direct rows stay until a human
  ratifies RELATION_WITHDRAW events for them. `value_chain_position` is set on four
  sub_themes only (satellite_connectivity_services=downstream; robot_arm_systems,
  glp1_therapy_products and ai_clinical_data_devices=midstream). Because every sub row is
  asserted_on 2026-10-13 and the producer's belief date is the UTC run date
  (scripts/build_theme_graph.py `belief_time = materialize.utc_today()`, with
  materialize.build_hierarchy skipping any entry or parent whose asserted_on is after it),
  the sub tier first materializes on the first nightly whose UTC run date is 2026-10-13 or
  later.
rationale: >
  The graph store is write-once and point-in-time (append_rows keeps the first row), so
  deleting a crosswalk row closes nothing. Only a ratified RELATION_WITHDRAW or
  DESTINATION_CHANGE event in the untracked relation_events.v2.jsonl closes an edge
  (materialize.apply_relation_events), and
  tests/test_theme_graph_hierarchy_withdrawal.py::test_w5_row_deleted_without_event_does_not_close
  pins exactly that. REPLACE by deletion would therefore leave the old edges open while the
  crosswalk claimed they were gone. theme->micro_theme stays a legal adjacency
  (DEC:GMI-TAXONOMY-UPGRADE-V2 T2), so the double chain is valid structure, not drift. F04
  is unaffected: exposure_map._ancestor_entries keys its entries by the pair (node-id chain,
  edge-id chain), so identical paths collapse and distinct chains stay distinct entries, and
  the F04 exposure walk drops PARENT_OF rows before edge collapse, so exposure outputs stay
  byte-identical. No F04 code changes.
alternatives:
  - option: REPLACE — delete the 27 direct theme->micro_theme rows in the same change
    why_not: >
      Rejected. Row deletion never closes a PARENT_OF edge in the write-once store, so the
      graph would keep the old edges while the crosswalk said otherwise. Closing them needs
      ratified RELATION_WITHDRAW events, which an agent may not author as ratified.
  - option: Defer the sub_theme population until withdrawal events are ratified
    why_not: >
      Rejected. The tier is valid and useful now. The double chain is consistent, and
      deferring would block display readers on a human act with no correctness benefit.
  - option: Let an LLM ratify the RELATION_WITHDRAW events
    why_not: >
      Rejected. Existing probation law lets an LLM propose but never ratify. A human
      ratifier owns the withdrawals.
evidence:
  - "#8999 squash 2084b3e579f9 (config/theme_crosswalk.yml, tests/test_theme_graph_crosswalk.py, tests/test_theme_graph_hierarchy_population.py)"
  - "tests/test_theme_graph_hierarchy_population.py pins categories == 10 (:276), micro_themes == 68 (:277), parents == 132 (:283) and 12 sub rows (:550)"
  - "tests/test_theme_graph_hierarchy_withdrawal.py:226 test_w5_row_deleted_without_event_does_not_close"
  - "Seat crosswalk check on origin/main d89fdf72f85d: 27/27 sub->micro chains consistent with the direct theme parent; all 39 sub-tier rows asserted_on 2026-10-13"
  - "engine/theme_graph/materialize.py build_hierarchy: belief_date = self.belief_time[:10]; entries and parents with asserted_on > belief_date are skipped. scripts/build_theme_graph.py:318 belief_time = materialize.utc_today()"
  - "engine/market_ontology/exposure_map.py:925 _ancestor_entries keys entries by (node-id chain, edge-id chain)"
affects:
  - config/theme_crosswalk.yml
  - engine/theme_graph/materialize.py
  - "WS:GMI-THEME-GRAPH"
confidence: high
reversibility: costly
decided_by: GMI Meta-CEO seat 6f14c2da (Opus 5.5) under Chairman max-powers delegation 2026-10-06/07
source_authority: "Chairman delegation 2026-10-06/07 (GMI Meta-CEO, max powers to build a more robust theme/sub-theme and multi-category classification system)"
decided_at: 2026-10-12
---

## What a successor must not do

- Do not delete the 27 direct theme->micro_theme rows from the crosswalk. Deletion closes
  nothing (DSC:GMI-CROSSWALK-ROW-DELETION-NEVER-CLOSES-PARENT-OF).
- Do not author RELATION_WITHDRAW events as ratified. A human ratifies them.
- Do not read the sub tier's absence from a graph built before UTC 2026-10-13 as a defect.
  The point-in-time gate excludes rows asserted after the belief date by design.
