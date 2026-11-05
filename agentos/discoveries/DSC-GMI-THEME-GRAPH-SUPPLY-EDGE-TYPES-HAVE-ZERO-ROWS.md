---
key: GMI-THEME-GRAPH-SUPPLY-EDGE-TYPES-HAVE-ZERO-ROWS
claim: >
  contracts/theme_graph/edges.v1.schema.json enumerates 13 edge types, but the committed
  data/theme_graph/edges.parquet on origin/main (blob 4d6ca3f037, last changed 2026-10-09)
  carries only four: MEMBER_OF 22432, EXPRESSES 2592, PARENT_OF 93 and TRACKS 77. The
  supply-relationship types SUPPLIES, ENABLES, BOTTLENECK_OF and BENEFITS_FROM have zero
  rows by design. engine/classification_axes/registry.py declares the gap as the
  supply_chain ABSTENTION (status not_populated, label NO_MAPPING, those four types listed
  as reserved_edge_types).
falsifier: >
  Run python3 -c "import pandas as pd; print(pd.read_parquet('data/theme_graph/edges.parquet')['type'].value_counts())"
  in a full checkout. Any non-zero count for SUPPLIES, ENABLES, BOTTLENECK_OF or
  BENEFITS_FROM refutes the claim (and the registry ABSTENTION must then be revisited).
so_what: >
  Never read supply-chain relationships from the theme graph. They do not exist there yet.
  `value_chain_position` on sub_themes is a display attribute, not an edge. Economic
  relationships remain candidates under DEC:GMI-ECONOMIC-RELATIONSHIP-CANDIDATE-EXECUTION
  until that program promotes them. A reader that needs them returns the typed
  NO_MAPPING abstention instead of inferring links.
kind: data
verified_at: 2026-10-12
verified_by: >
  GMI Meta-CEO seat 6f14c2da: value_counts on the origin/main edges.parquet (column `type`),
  read of the edges.v1 enum, and read of registry.py ABSTENTIONS on d89fdf72f85d.
scope:
  - macro
  - data/theme_graph/edges.parquet
  - contracts/theme_graph/edges.v1.schema.json
  - engine/classification_axes/registry.py
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

The PARENT_OF count of 93 is the pre-sub-tier hierarchy. It rises when the first nightly
with a UTC run date of 2026-10-13 or later materializes the sub_theme rows
(DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD). The supply types stay at zero until a separate
decision populates them.
