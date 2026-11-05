---
key: GMI-THEME-HIERARCHY-ON-CROSSWALK
question: >
  How should Mastermind gain a granular theme / sub-theme / multi-category classification
  (macro category -> theme -> micro-theme, plus sector/industry and market axes) without
  minting a rival vocabulary, store, producer, or rights plane, and without laundering
  internal-only vendor taxonomies (Finviz themes, THS concepts) into house-owned output?
answer: >
  Hierarchy is a GMI capability on the INCUMBENT theme-graph producer. Store it as an
  additive optional `hierarchy:` block (categories, micro_themes, parents) in
  config/theme_crosswalk.yml (version stays 3; the document date is never bumped; every
  entry carries its own asserted_on >= 2026-10-07). engine/theme_graph/materialize.py emits
  tiered kind=theme nodes (tier in macro_category | theme | micro_theme) and curated
  PARENT_OF edges (src = parent, dst = child, adjacent tiers only, DAG, <= 3 parents, no
  weight/share/count), with typed refusals. New-tier nodes carry no EXPRESSES/MEMBER_OF
  until consumers are tier-guarded. Vendor taxonomies are not nominators in V1; vendor
  parents remain source_meta only. Admission = nominator -> optional probation kind
  `hierarchy` -> human/delegated ratification -> reviewed crosswalk PR (the only act that
  materializes an edge). Ticker classification is composed at read time
  (structural_navigation hierarchy_paths), never stored per ticker. Incumbent vertical
  vocabularies federate by identical slug with parity tests (#7870 slices), never by copy.
  Full frozen spec: research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md.
rationale: >
  PARENT_OF already exists in the edges.v1 enum and the incumbent producer, crosswalk,
  rights family (mastermind_curated, direct_display_ok) and readers already carry
  kind=theme nodes, so a tier field plus curated PARENT_OF rows give a three-level house
  taxonomy with zero new planes (Gate #8) and one canonical vocabulary (G0.9). The 2026-08-27
  freeze retired standalone GMI W4, which left the stale "PARENT_OF edges are W4's" note in
  materialize.py with no owner; hierarchy is therefore GMI-owned on the incumbent producer.
  Per-entry asserted_on avoids re-iding every EXPRESSES edge (edge_id embeds valid_from)
  and keeps PIT. House-only nominators honour Gate #2 ("Do not use an internal-only vendor
  input to launder restricted structure into a house-owned output"). Read-time composition
  honours DNR:HOLD-TICKER-EXPOSURE-TAGS and G0.13 (semantic membership is group-level).
alternatives:
  - option: Seed micro-themes from basket membership and wire basket -> micro EXPRESSES immediately (design "signal-lift")
    why_not: >
      Rejected. A basket is a construction, not a theme (vocabulary N+1, G0.9), and new
      EXPRESSES targets silently change F04 exposure, selection-cohort and ThemeState inputs
      before any consumer is tier-aware. Deferred until the W-C2b tier guard lands.
  - option: A federated registry with pathway-role edges and a theme_context re-key (design "federation")
    why_not: >
      Rejected as a whole. Pathway-role edges are a new edge semantic and the re-key breaks
      existing consumers; its useful grafts (seat-frozen macro categories, PARENT_OF
      direction, category != canonical theme note on #7283) were adopted.
  - option: Build hierarchy from Finviz sub-themes / THS concept parents
    why_not: >
      Rejected. Both families are internal_only; their structure may not become house
      output (Gate #2). Vendor parents stay source_meta per W3A.
  - option: A new standalone hierarchy store, producer, or GMI W4 relationship graph
    why_not: >
      Rejected by Gate #8 and DEC:GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING.
  - option: Make basket `category` labels canonical categories as-is (15 labels)
    why_not: >
      Rejected as-is: overlapping labels (Semiconductors vs Semiconductors & Hardware, AI &
      Technology vs Artificial Intelligence) and "US Sectors (EW)" is a construction. The
      seat freezes a merged house category set instead; basket category stays a display
      label (#7283).
evidence:
  - "origin/main e20149308a7b: config/theme_crosswalk.yml version 3 dated 2026-07-09, 18 themes; top-level keys version/date/note/themes/cn_concepts/unmapped_baskets."
  - "contracts/theme_graph/edges.v1.schema.json enumerates PARENT_OF with generic src/dst (no direction convention); nodes.v1 tier is a free string."
  - "edge_id grammar <type>:<src>-><dst>@<valid_from> (materialize.py) — a document-date bump re-ids every crosswalk EXPRESSES edge."
  - "Readers accept any theme: id — theme_state.py:164, exposure_map.py:86, selection_cohort.py:164, ontology.py:609 — hence the W-C2b tier guard precedes any basket->micro wiring."
  - "ontology.py:5-6 ratification never creates an edge; materialize.py:1686-1688 v2 relation events only withdraw/redirect curated-crosswalk priors — the crosswalk PR is the real admission path."
  - "#7870 VerticalRegistration(anchor_theme_id, slice_keys): semis anchor ai_semiconductors with slices hbm_packaging, sic_gan_specialty."
  - "Seat design panel 2026-10-07 (3 designs + red-team judge): minimal 5/5/2/5/4/4, signal-lift 3/3/5/4/2/3, federation 4/4/3/5/5/4 on law/build/lift/rights/no-rival/PIT; minimal spine with grafts."
affects:
  - "WS:GMI-THEME-GRAPH"
  - "config/theme_crosswalk.yml"
  - "engine/theme_graph/materialize.py"
  - "contracts/theme_graph/nodes.v1.schema.json"
  - "contracts/theme_graph/edges.v1.schema.json"
  - "engine/theme_graph/structural_navigation.py"
  - "engine/market_ontology/exposure_map.py (F04 ancestors, MO amendment)"
  - "research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md"
confidence: medium
reversibility: easy
decided_by: GMI Meta-CEO seat 6f14c2da (Fable/Opus) under Chairman max-powers delegation 2026-10-06/07
source_authority: "Chairman delegation 2026-10-06/07 (GMI Meta-CEO, max powers to build the theme/sub-theme/multi-category classification); Chairman Gates #2 and #8"
decided_at: 2026-10-07
---

## Rulings frozen with this decision (R1–R10)

| # | Ruling |
|---|---|
| R1 | Keep the `theme:` id prefix for every tier; distinguish by `tier`. |
| R2 | Macro categories are a seat-frozen merge of the basket `category` labels, excluding "US Sectors (EW)". |
| R3 | The crosswalk is canonical for micro-theme ids; #7870 vertical slices must be a subset under their anchor (parity test; #7870 owner countersign pending). |
| R4 | Per-entry `asserted_on`, never before 2026-10-07 and never before the merge that adds it; the crosswalk document date is never bumped. |
| R5 | Add probation kind `hierarchy` now (review queue only; never an edge source). |
| R6 | At most 3 parents per node; a theme without a category is allowed. |
| R7 | A read-time, basket-keyed path is group-level semantic membership (G0.13), not a per-ticker tag. |
| R8 | Finance R11 slices stay unfederated until the owner-status conflict is resolved. |
| R9 | Post a "basket category != canonical theme" note on #7283 (STSI display surface). |
| R10 | Finviz/THS taxonomies are not nominators in V1 (Gate #2); micro-themes come only from house sources. |

Wave plan, refusals, consumer order and pre-mortem tripwires: the frozen spec §§3–9.
