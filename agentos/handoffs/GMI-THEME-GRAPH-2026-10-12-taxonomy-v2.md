---
workstream: "WS:GMI-THEME-GRAPH"
session: "claude-code 6f14c2da-02a9-467e-9f37-7c2ebaccfe09 (GMI Meta-CEO seat, Opus 5.5, Taxonomy V2 wave 2026-10-07 to 2026-10-12 under the Chairman max-powers delegation)"
model: opus
ended_because: ci_handoff
mission: >
  Upgrade the GMI theme graph's classification depth without minting a rival truth plane: add an
  optional sub_theme tier between theme and micro_theme, add six display-tier classification axes
  (SEC industry, geography, macro sensitivity, business model, lifecycle, value chain) as pure
  readers composed into one registry row, and populate the first real sub_theme rows, all through
  the GLM/Grok subagent fabric with the seat judging every return by its artifact.
state_before: >
  origin/main carried three tiers (macro_category, theme, micro_theme) with 93 PARENT_OF rows, no
  sub_theme vocabulary, no AxisCell contract, and no classification-axis readers. F04
  MarketOntology already walked theme-graph ancestors read-only. D2E #8540 and #8960 were merged
  and production-proven from the earlier wave (handoff GMI-THEME-GRAPH-2026-10-06).
changed:
  - path: engine/theme_graph/materialize.py
    what: "sub_theme tier: four PARENT_OF adjacencies, value_chain_position display attribute, present-key validation semantics (#8940, #8941, #8942, #8945, #8948)"
  - path: engine/theme_graph/probation.py
    what: "hierarchy proposals accept child_tier sub_theme; LLM-originated proposals still never ratify (#8942)"
  - path: engine/classification_axes/
    what: "cell.py (AxisCell v1, #8961) plus six pure readers: sic_industry #8974, geography #8976, macro_sensitivity #8975, business_model #8969, lifecycle #8968, value_chain #8973; registry.py composes axis_row.v1 (#8987)"
  - path: contracts/classification_axes/
    what: "axis_cell.v1 and axis_row.v1 JSON schemas (#8961, #8987)"
  - path: config/theme_crosswalk.yml
    what: "first population: 12 sub_themes and 27 sub->micro rows, all asserted_on 2026-10-13, direct theme->micro rows kept (#8999, #9000)"
  - path: .github/ci/legacy-jobs.yml
    what: "gmi-classification-axes job (gate code) carries the axis suites; theme-graph suites stay in unrun-intl-libraries (gate data)"
verified:
  - claim: "All fifteen Taxonomy V2 squash merges are ancestors of origin/main"
    command: "git merge-base --is-ancestor <squash> d89fdf72f85d for 278bafeb8990 fc6d5db660d2 45ba77142102 3df67fd1bcdf 3f6b822acebd 8c0e80474bdb 353c34537123 676c4f50faf2 2084b3e579f9 1a90ccbd8d15 9f9241641578 2535ef1de4f5 3cc23f12948e 507878b4942e 254f1ed936eb"
    result: "15/15 rc 0"
  - claim: "The 18 Taxonomy V2 and theme-graph suites pass on main except two known reds"
    command: "TZ=UTC pytest -q tests/test_classification_axes_*.py tests/test_theme_graph_{crosswalk,hierarchy_contract,hierarchy_paths,hierarchy_population,hierarchy,hierarchy_withdrawal,identity,identity_resolution,probation_hierarchy,tier_guard}.py on a detached d89fdf72f85d checkout (ubuntu0)"
    result: "817 passed, 2 failed in 16.08s; failures are test_mapping_curation_parity_when_subject_node_absent (clock bomb) and test_the_committed_bake_is_reproducible_from_the_committed_inputs (master_generated_at 2026-10-09T05:05:32 baked vs 2026-10-11T16:03:17 current)"
  - claim: "The registry composes all six readers on main plus its own head"
    command: "composed-tree pytest for #8987 (git merge-tree --write-tree origin/main head, commit-tree, detached checkout, pytest)"
    result: "443 passed"
  - claim: "Main proof covers six of the fifteen PRs and its red is not GMI"
    command: "gh run view 38240751035 --json headSha,jobs (head 23426ad7054c)"
    result: "ci-pack-6 job 114782714105 success with gmi-classification-axes selected; only red is ci-pack-9 macro_rates_curves; the other nine PRs merged on their own concluded merge-ref CI"
  - claim: "Crosswalk population on main"
    command: "yaml.safe_load(git show d89fdf72f85d:config/theme_crosswalk.yml) hierarchy counts"
    result: "10 categories, 12 sub_themes, 68 micro_themes, 132 parents (21 category->theme, 12 theme->sub, 27 sub->micro, 72 theme->micro); 27/27 double chains consistent"
  - claim: "Sub-tier rows cannot materialize before 2026-10-13"
    command: "read materialize.build_hierarchy (belief_date = belief_time[:10], skips asserted_on > belief_date) and scripts/build_theme_graph.py:318 (belief_time = materialize.utc_today())"
    result: "every sub-tier row is asserted_on 2026-10-13, so the first nightly with UTC run date >= 2026-10-13 is the first that can emit them"
unverified:
  - claim: "The nightly materializes 12 sub_theme nodes and 132 PARENT_OF rows (93 + 39)"
    what_would_verify: "after the first nightly with UTC run date >= 2026-10-13: read data/theme_graph/nodes.parquet and edges.parquet on origin/main, count tier == sub_theme nodes and type == PARENT_OF current edges"
  - claim: "F04 consumes the sub tier without a code change"
    what_would_verify: "F04 exposure_map ancestor walk run against the post-nightly graph; entries keyed by (node-id chain, edge-id chain) show both chains for each of the 27 micros and no duplicate exposure rows"
  - claim: "The identity-resolution bake is re-baked by an existing producer"
    what_would_verify: "find the producer of the committed identity-resolution artifact and confirm it runs after a security-master regeneration; otherwise commission a re-bake lane"
unresolved:
  - "Clock bomb: tests/test_theme_graph_probation_hierarchy.py:449 make_proposal stamps a wall-clock created while the test pins asof 2026-10-08; heal lane w3h1 pins created to 2026-10-07T00:00:00Z (tests only)"
  - "Identity-resolution reproducibility red since the 2026-10-11 security master regeneration without a re-bake (data-health lane, issue 5979)"
  - "Theme-graph suites run only in the data-health lane (DSC:GMI-THEME-GRAPH-SUITES-RUN-ONLY-IN-THE-DATA-HEALTH-LANE); moving the hermetic ones to a code-gate job is an open seat decision"
  - "27 RELATION_WITHDRAW events that would retire the direct theme->micro rows need a human ratifier"
next_actions:
  - "Land the records lane (this handoff, two DECs, five DSCs, WS wave TAXONOMY-V2), the docs lane (taxonomy_upgrade_v2/SPEC.md, F04 note section, program registry roots) and the clock-bomb heal lane"
  - "After the first nightly with UTC run date >= 2026-10-13, prove the sub tier in production and flip wave TAXONOMY-V2 to done"
  - "Census then build L12 hierarchy-breadth and L13 micro RS-proxy display readers (labels proxy_not_micro_membership; no rank-like keys)"
  - "Coordinate F04 consumption of the axis registry with the MarketOntology owner; no wiring without a new DEC"
  - "Hierarchy browse page through the design lane (designer agent, both themes, EN/ZH)"
do_not_redo:
  - "The fifteen merged Taxonomy V2 PRs (#8940 #8941 #8942 #8945 #8948 #8961 #8974 #8975 #8999 #8969 #9000 #8968 #8973 #8976 #8987); accepted, do not re-spec or re-implement"
  - "W-C7 ticker exposure tags are DROPPED (DNR:HOLD-TICKER-EXPOSURE-TAGS)"
  - "L15 is DROPPED; registry ABSTENTIONS cover it"
  - "#8643 is CLOSED"
  - "Do not rename micro_theme or re-tier existing nodes (DEC:GMI-TAXONOMY-UPGRADE-V2)"
  - "Do not replace direct theme->micro rows when adding sub-tier rows (DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD)"
danger_areas:
  - "DSC:EXCLUSIVE-SUITE-PATH-LITERALS-PULL-IMPORT-CLOSURE"
  - "DSC:CONTRACT-DELTA-TRIPS-TWICE-ON-NEW-MODULE-PLUS-NEW-SUITE"
  - "DSC:CONTRACT-DELTA-UNRUN-SUITE-GATE-IS-LITERAL-MATCH"
  - "DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML"
  - "DSC:GMI-CROSSWALK-ROW-DELETION-NEVER-CLOSES-PARENT-OF: deleting a crosswalk row leaves its PARENT_OF current forever; retire with RELATION_WITHDRAW"
  - "DSC:GMI-THEME-GRAPH-STORE-NON-STRICT-READ-MASKS-CORRUPTION"
  - "Owned by #7870, never edit: engine/theme_graph/{rights,admission,curation_assertion}.py, config/theme_sources.yml, contracts/theme_graph/{README.md,curation_assertion.v1.schema.json,evidence.v1.schema.json}"
  - "Gate 2: finviz_themes, ths_concepts and ltheme:* are internal-only and never a subject, input or output of the axes"
prs: [8940, 8941, 8942, 8945, 8948, 8961, 8974, 8975, 8999, 8969, 9000, 8968, 8973, 8976, 8987]
decisions:
  - "DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK"
  - "DEC:GMI-TAXONOMY-UPGRADE-V2"
  - "DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD"
discoveries:
  - "DSC:GMI-THEME-GRAPH-SUPPLY-EDGE-TYPES-HAVE-ZERO-ROWS"
  - "DSC:GMI-MACRO-SENSITIVITY-AXIS-READS-GITIGNORED-STOCKDATA"
  - "DSC:GMI-THEME-GRAPH-STORE-NON-STRICT-READ-MASKS-CORRUPTION"
  - "DSC:GMI-CROSSWALK-ROW-DELETION-NEVER-CLOSES-PARENT-OF"
  - "DSC:GMI-THEME-GRAPH-SUITES-RUN-ONLY-IN-THE-DATA-HEALTH-LANE"
---

## Cold-stranger summary

Taxonomy V2 is merged. The theme graph now accepts an optional `sub_theme` tier between `theme`
and `micro_theme`, and `engine/classification_axes/` holds six display-tier readers that each
return one `axis_cell.v1` record; `registry.py` composes them into one `axis_row.v1` per
subject. Everything is display or context tier: no weights, scores, ranks or exposure
percentages, and a missing value is a typed null with a reason.

The first 12 sub-themes are in `config/theme_crosswalk.yml`, but they are dated 2026-10-13 and
the nightly stamps its belief date from the UTC run date, so nothing in the committed graph
changes until the first nightly on or after 2026-10-13. Expect 12 new `sub_theme` nodes and
39 new `PARENT_OF` rows (132 in total). The 27 micro-themes under a sub-theme keep their direct
theme link as well, so they have two consistent chains. F04 keys ancestors by the full node and
edge chain, so it reports both without double counting, and it needs no code change. Retiring
the direct links is a human ratification (`RELATION_WITHDRAW`), never a crosswalk row deletion.

Two reds sit in the data-health lane and do not block merges. One is a test clock bomb with a
tests-only heal in flight. The other is the identity-resolution bake predating the 2026-10-11
security-master regeneration. Next work: the production proof after the 2026-10-13 nightly, the
L12/L13 display readers, F04 coordination, and a hierarchy browse page.
