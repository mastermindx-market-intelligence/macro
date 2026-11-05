---
key: GMI-TAXONOMY-UPGRADE-V2
question: >
  How should the GMI theme graph gain a sub-theme tier and a multi-axis classification
  (SEC industry, geography, macro sensitivity, business model, lifecycle, value chain)
  without minting a second producer, selection store, ThemeState owner, rights resolver or
  publication control plane (Gate #8), and without laundering internal-only vendor
  structure into house-owned output (Gate #2)?
answer: >
  Three parts, all on incumbent owners. (1) An OPTIONAL `sub_theme` tier (kind=theme)
  between `theme` and `micro_theme`, declared in the crosswalk `hierarchy.sub_themes` block,
  with exactly four PARENT_OF adjacencies: macro_category->theme, theme->sub_theme,
  sub_theme->micro_theme and theme->micro_theme. A theme->micro_theme edge without a
  sub_theme stays valid forever. `micro_theme` is not renamed. `value_chain_position` is a
  display attribute held in node `source_meta` only. Present-key semantics keep a crosswalk
  without sub_themes byte-identical. (2) Six PURE READERS under engine/classification_axes/,
  one per axis, each returning the AxisCell v1 contract (cell.py +
  contracts/classification_axes/axis_cell.v1.schema.json). registry.py composes them at read
  time into axis_row.v1. Nothing is persisted and no new store exists. (3) MarketOntology F04
  remains the single canonical downstream and is NOT wired by this decision. The axis set is
  frozen at six: a seventh axis, or wiring F04 to these readers, needs a new DEC plus
  coordination with the MarketOntology owner. The frozen spec text lives at
  research/theme_graph/taxonomy_upgrade_v2/SPEC.md.
rationale: >
  Every axis reads an incumbent owner's artifact (equity_profile, stock_macro_sensitivity,
  the Nasdaq basket membership, the theme-graph store, the security master), so no truth
  plane is duplicated. A missing value is a typed null (status + reason_code), never a zero
  or a guess. `rights_context` is a static per-source constant declared by each reader
  module, never computed, so no rights resolver is minted (Gate #8). Forbidden value keys
  (weight, share, score, rank, exposure_pct) keep every cell display-tier. Subject ids reuse
  engine/theme_graph/identity.py and refuse `ltheme:*` and the finviz_themes / ths_concepts
  suites: "Do not use an internal-only vendor input to launder restricted structure into a
  house-owned output" (Gate #2). This extends DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK rather than
  replacing it.
alternatives:
  - option: Rename micro_theme or re-tier the 93 existing hierarchy rows into the new tier
    why_not: >
      Rejected. It breaks node ids, edge ids and materialized bytes for every existing
      consumer. An optional tier with present-key semantics adds structure with zero churn.
  - option: A new per-ticker classification store or producer
    why_not: >
      Rejected by Gate #8 and DNR:HOLD-TICKER-EXPOSURE-TAGS. Read-time composition over the
      incumbent artifacts gives the same view without a second truth plane.
  - option: A fused composite classification score or rank across the axes
    why_not: >
      Rejected. It turns display context into authority. The gauntlet governs promotion, and
      the forbidden-key rule keeps every cell display-only.
  - option: Seed sub-themes or axis values from Finviz themes or THS concepts
    why_not: >
      Rejected by Gate #2. Both families are internal_only, and their structure may not
      become house output.
  - option: Ticker exposure tags (the dropped W-C7 lane)
    why_not: >
      Rejected. DNR:HOLD-TICKER-EXPOSURE-TAGS holds it; W-C7 stays dropped.
evidence:
  - "Fifteen squash merges, all ancestors of origin/main d89fdf72f85d: #8940 278bafeb8990, #8941 fc6d5db660d2, #8942 45ba77142102, #8945 3df67fd1bcdf, #8948 3f6b822acebd, #8961 8c0e80474bdb, #8974 353c34537123, #8975 676c4f50faf2, #8999 2084b3e579f9, #8969 1a90ccbd8d15, #9000 9f9241641578, #8968 2535ef1de4f5, #8973 3cc23f12948e, #8976 507878b4942e, #8987 254f1ed936eb"
  - "#8987 composed-tree pytest (registry over all six readers on main + head): 443 passed"
  - "Main ci.yml run 38240751035 (head 23426ad7054c, scoped to #8940/#8941/#8942/#8945/#8948/#8961): ci-pack-6 job 114782714105 succeeded with gmi-classification-axes and nw-lobe-unfreeze selected; its only red is ci-pack-9 macro_rates_curves, not GMI. The other nine PRs merged on their own concluded merge-ref CI"
  - "config/theme_crosswalk.yml on d89fdf72f85d: 10 categories, 12 sub_themes, 68 micro_themes, 132 parents (21 category->theme, 12 theme->sub, 27 sub->micro, 72 theme->micro)"
affects:
  - engine/classification_axes/
  - contracts/classification_axes/
  - engine/theme_graph/materialize.py
  - engine/theme_graph/structural_navigation.py
  - engine/theme_graph/probation.py
  - contracts/theme_graph/edges.v1.schema.json
  - contracts/theme_graph/nodes.v1.schema.json
  - contracts/theme_graph/probation_proposal.v1.schema.json
  - config/theme_crosswalk.yml
  - scripts/check_theme_graph_contracts.py
  - .github/ci/legacy-jobs.yml
  - tests/test_ci_pack.py
  - "WS:GMI-THEME-GRAPH"
confidence: high
reversibility: easy
decided_by: GMI Meta-CEO seat 6f14c2da (Opus 5.5) under Chairman max-powers delegation 2026-10-06/07
source_authority: "Chairman delegation 2026-10-06/07 (GMI Meta-CEO, max powers to build a more robust theme/sub-theme and multi-category classification system); Chairman Gates #2 and #8"
decided_at: 2026-10-12
---

## Rulings frozen with this decision (T1–T12)

| # | Ruling |
|---|---|
| T1 | `sub_theme` is an optional tier with kind=theme. `micro_theme` is not renamed. |
| T2 | PARENT_OF allows exactly four adjacencies: macro_category->theme, theme->sub_theme, sub_theme->micro_theme, theme->micro_theme. |
| T3 | No EXPRESSES or MEMBER_OF edge ever points to or from a sub_theme or micro_theme id (NEW_TIER_IN_EXPRESSES_MAP). |
| T4 | `value_chain_position` ∈ {upstream, midstream, downstream, enabler} is a display attribute in `source_meta`, never an edge, score or weight. |
| T5 | Present-key semantics: a crosswalk without `sub_themes` validates and materializes byte-identically. |
| T6 | Probation `child_tier` may be theme, sub_theme or micro_theme. An LLM proposal may propose, never ratify. |
| T7 | AxisCell v1 has exact keys, six statuses with typed reason codes, quality `display_only`, and a point-in-time law (no observation after `as_of`). |
| T8 | Subject ids come from engine/theme_graph/identity.py. `ltheme:*`, `finviz_themes` and `ths_concepts` are refused (Gate #2). |
| T9 | Axis readers are pure: no writes, no network, no LLM, no wall clock, no cross-reader imports. |
| T10 | `rights_context` is a static per-source constant, never resolved at run time (Gate #8). |
| T11 | registry.py composes axis_row.v1 at read time, with typed failure codes and the supply_chain ABSTENTION (reserved edge types, `NO_MAPPING`). |
| T12 | The axis set is frozen at six. F04 MarketOntology is the single downstream, and wiring it needs a new DEC plus owner coordination. |

## Axis readers

| Axis | Lane | PR | Incumbent owner | Artifact |
|---|---|---|---|---|
| sic_industry | L05 | #8974 | collectors/equity_profile.py | data/profile/profiles.parquet |
| geography | L06 | #8976 | scripts/build_security_master.py | data/reference/security_master.parquet |
| macro_sensitivity | L07 | #8975 | engine/stock_macro_sensitivity.py | site/stockdata/<symbol>.json |
| business_model | L08 | #8969 | Nasdaq basket membership | data/baskets_nasdaq/membership.json |
| lifecycle | L09 | #8968 | engine/theme_graph/store.py | data/theme_graph/nodes.parquet |
| value_chain | L10 | #8973 | engine/theme_graph/store.py | data/theme_graph/nodes.parquet |
