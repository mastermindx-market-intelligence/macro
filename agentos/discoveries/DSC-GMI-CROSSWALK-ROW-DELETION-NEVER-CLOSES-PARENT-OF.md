---
key: GMI-CROSSWALK-ROW-DELETION-NEVER-CLOSES-PARENT-OF
claim: >
  Deleting a hierarchy parent row from config/theme_crosswalk.yml does not close the
  corresponding PARENT_OF edge. The theme-graph store is write-once (append_rows keeps the
  first row) and point-in-time, so an edge stays open until a ratified RELATION_WITHDRAW or
  DESTINATION_CHANGE event in the untracked relation_events.v2.jsonl closes it through
  materialize.apply_relation_events.
falsifier: >
  tests/test_theme_graph_hierarchy_withdrawal.py::test_w5_row_deleted_without_event_does_not_close
  fails, or a materialization after deleting a parent row shows the edge with a valid_to set.
so_what: >
  Re-parenting is an event, not an edit. Any change that moves a micro_theme under a
  sub_theme must keep the old row (KEEP+ADD, DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD) or pair
  the deletion with a human-ratified withdrawal. The 27 direct theme->micro_theme rows stay
  until such events are ratified.
kind: landmine
verified_at: 2026-10-12
verified_by: >
  GMI Meta-CEO seat 6f14c2da: read of test_w5 (tests/test_theme_graph_hierarchy_withdrawal.py:226)
  and materialize.apply_relation_events on origin/main d89fdf72f85d.
scope:
  - macro
  - config/theme_crosswalk.yml
  - engine/theme_graph/materialize.py
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

An agent may propose a withdrawal through probation but may never author one as ratified.
