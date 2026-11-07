# Market Ontology F04 exposure_map — additive ancestors note

- Date: 2026-10-07
- Status: ADDITIVE CONTRACT NOTE / RECORDS_ONLY / NO PRODUCT EFFECT
- Workstream: WS:GMI-THEME-GRAPH
- Decision: DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK
- Producer: W-C6 (PR #8612, `hierarchy_paths`)

## What changed

`ThemeExposure` has one optional final field, `ancestors`, and the JSON composer emits it only when at least one ancestor chain exists. Each chain names the macro-category path above a theme, its `PARENT_OF` edge identifiers, and public bilingual node names. The field is display-only and additive: an empty value is omitted rather than serialized as an empty array.

`compose_exposure_map` accepts an injected `hierarchy_reader`. A caller may pass `engine.theme_graph.structural_navigation.hierarchy_paths` from W-C6; the default remains `None`, emits no ancestors, and leaves the map byte-identical. The module does not import the reader, so its import surface is unchanged. Eligible canonical-theme rows use one private snapshot of the node, edge, and lifecycle rows that the composer has already read.

Ancestor reads are point-in-time through the same effective date and knowledge cutoff as the map. A refused read becomes the typed `HIERARCHY_REFUSED` abstention and never escapes the composer. An ancestor whose rights receipt is absent, withheld, or refused is removed with its whole chain so no withheld node identifier leaks.

## What did not change

No production caller injects the reader in this wave. No MarketOntology caller, payload renderer, user interface, provenance key, or sibling market-ontology module changes. Existing constructors and consumers remain valid without edits.

## Ledger position

MO-DELTA-004 remains PARTIAL. The F00C ledger CSV is not edited because F04 closure map §2.1 acceptance requires a real product surface with shock → accepted owner edges → company exposure, typed refusal, and evidence links. This note adds a contract and tests, not that product surface.

## Known limitation

The default store view exposes no node-lifecycle reader, so node visibility relies on `computed_at` and `birth_date` plus the belief time of each `PARENT_OF` edge. Callers with lifecycle rows can supply a snapshot-capable store view, but F04 itself does not add that reader.

## F0 — hierarchy edges excluded from the walk

`PARENT_OF` rows are dropped from the exposure walk before edge collapse. They cannot make a theme count as having edges, change a row state, or attach a clock abstention. The injected hierarchy reader still receives every hierarchy row. A production hierarchy must leave every existing exposure_map output byte-identical; the regression test proves that boundary.

## 2026-10-12 — sub_theme tier (Taxonomy V2)

- Producer: Taxonomy V2 (DEC:GMI-TAXONOMY-UPGRADE-V2, DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD; the 15 merged PRs are listed in WS:GMI-THEME-GRAPH wave TAXONOMY-V2). `config/theme_crosswalk.yml` gains an optional `hierarchy.sub_themes` block, so the hierarchy now admits `theme -> sub_theme -> micro_theme` beside the existing `theme -> micro_theme` edge.
- Timing: every sub-tier crosswalk row is `asserted_on: 2026-10-13`, and the nightly materializes with its UTC run date as the belief date. The sub tier therefore first appears in the first nightly whose UTC run date is 2026-10-13 or later: 12 `sub_theme` nodes, and PARENT_OF hierarchy rows go from 93 to 132.
- Two chains per re-parented micro: the 27 micro_themes placed under a sub_theme keep their direct `theme -> micro_theme` row (keep-add rule) until a human-ratified RELATION_WITHDRAW retires it. Until then each carries two consistent ancestor chains: the direct one and the one through its sub_theme.
- F04 effect: `exposure_map._ancestor_entries` keys each entry by (node-id chain, edge-id chain), so both chains appear as distinct entries and neither is counted twice. The F0 rule above still holds: PARENT_OF rows stay out of the exposure walk, so exposure outputs do not change.
- No F04 code change. Ledger position unchanged (MO-DELTA-004 PARTIAL).
