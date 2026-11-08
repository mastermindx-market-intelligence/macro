---
key: GMI-MICRO-EXPANSION-2026-10-21-ADDITIVE-FROZEN-68
question: >
  The Chairman's 2026-10-21 commission requires micro-themes to go "immensely and
  aggressively" beyond the original master plan. Fabric research lanes proposed 303 new
  micro_themes and 53 new sub_themes across 18 themes (C1 121, C2 97, C3 85). How do these
  rows enter the house taxonomy without changing the GMI acceptance boundaries, and what
  happens to the frozen 68-micro R-C3 set that the coverage proof and the owner-reviewed
  disposition gate measure?
answer: >
  The expansion is ADDITIVE and DISPLAY-TIER. Ratified rows are appended to the existing
  `hierarchy:` block of config/theme_crosswalk.yml (version stays 3) with
  `asserted_on: 2026-10-21` and `nominated_from` = the research record that proposed them,
  through the normal reviewed-crosswalk PR path (DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK).
  The frozen 68 (every micro_theme row with asserted_on < 2026-10-21) REMAINS the
  acceptance set: scripts/gmi_coverage_proof.py keeps DECLARED_MICRO_COUNT = 68 and the
  "68 micro dispositions owner-reviewed" boundary is unchanged; coverage against the
  expansion rows is reported separately and never substituted. Tests that pin the micro
  tier at 68 become date-scoped (frozen set == 68) rather than total-count pins. Where two
  independent lanes researched the same theme group, a union-and-dedupe lane produced one
  spine (variant B) with exact and mechanism-true duplicates merged and A-only rows
  grafted; the seat, acting curator under handoff D6, ratified each union by artifact.
  Ratification grants no issuer membership, no EXPRESSES/MEMBER_OF edges, no evaluation
  authority and no rights change.
rationale: >
  Acceptance boundary (2) of the 2026-10-21 handoff names the 68 owner-reviewed
  dispositions; re-baselining the declared count to 371 would silently relax that gate
  with zero new owner reviews. Additive dated rows preserve PIT (edge_id embeds
  valid_from), keep the document date unbumped, and reuse the existing hierarchy
  withdrawal path for reversal. Discarding one of two valid lane variants would throw
  away roughly 65 validated micros per group against an explicit Chairman instruction to
  expand aggressively; a union with a precision rule (merge only same-mechanism rows, keep
  both when the mechanisms differ and each carries a distinct_from) keeps breadth without
  duplicate ids. validate_theme_hierarchy ran clean on every ratified set
  (DUPLICATE_ID / CROSS_TIER_REUSE / BLOCK_SHAPE all absent) before ratification.
alternatives:
  - option: Re-baseline DECLARED_MICRO_COUNT and the 68 pins to the new total (371)
    why_not: >
      Rejected. It would redefine acceptance boundary (2) without the owner reviews that
      boundary requires and would make the coverage proof report against rows no owner has
      dispositioned.
  - option: Keep only one research variant per theme group (first lane wins)
    why_not: >
      Rejected. Both variants validated; overlap was ~65% by mechanism, so each variant
      held 25 to 27 micros the other lacked. The Chairman asked for aggressive expansion.
  - option: Let the research lanes ratify their own rows
    why_not: >
      Rejected by taxonomy law: LLM proposals may PROPOSE but never ratify
      (research/theme_graph/taxonomy_upgrade_v2/SPEC.md). The seat judged each artifact
      and signed the receipts.
  - option: Hold all 303 rows until the Chairman names a curator
    why_not: >
      Rejected. Handoff D6 lets the seat act as curator with one Chairman ask maximum; the
      rows are display-tier and reversible, so holding them buys no safety.
evidence:
  - "C3: PR #9984 head 0e6e7f9846179a322a25bdb4323788097a5ff529, squash-merged to origin/main c6bbf9bf7a04; validate_rows.py -> VALIDATED micro_themes 153 (68+85), sub_themes 25, no dup/clash; 85 H3 sections == 85 YAML rows; issuer-name heuristic 0 hits."
  - "C1 union: PR #10006 head 029e62b621282458440311af2eceec8c533b7023 (lane gmi-micro-u1-20261021-r1); 121 micros / 20 sub_themes / 240 parents; VALIDATED micro_themes 189; ledger 60 MERGE, 5 KEEP-BOTH, 27 grafted, 3 sub_themes carried."
  - "C2 union: PR #10007 head 1b578e9a2c4b2d9e09d843c13889247ce90b8dee (lane gmi-micro-u2-20261021-r1, seat bundle-published); 97 micros / 20 sub_themes / 213 parents; VALIDATED micro_themes 165; ledger 40 MERGE, 10 KEEP-BOTH, 27 grafted, 1 sub_theme carried."
  - "Superseded single-variant PRs #9978, #9985, #9983 closed with explanatory comments."
  - "Pins that must become date-scoped: tests/test_theme_graph_hierarchy_population.py (frozen R-C3 table and micro_theme tier counts), tests/test_theme_graph_micro_member_addendum.py existing_micro_count, tests/test_theme_graph_micro_membership_research.py micro_definitions; tests/test_gmi_coverage_proof.py declared_micro_count == 68 stays."
  - "Seat ratification receipts: research/theme_graph/micro_expansion_20261021/RATIFICATION_RECEIPTS.md (lands with the integration PR)."
affects:
  - "WS:GMI-THEME-GRAPH"
  - "config/theme_crosswalk.yml"
  - "scripts/gmi_coverage_proof.py (DECLARED_MICRO_COUNT unchanged by rule)"
  - "scripts/build_theme_tree_page.py (tree must stay legible at 371 micros)"
  - "research/theme_graph/micro_expansion_20261021/"
confidence: high
reversibility: easy
decided_by: GMI COMPLETION Meta-CEO seat 6f14c2da (Fable 5.1) acting curator under handoff D6
source_authority: "Chairman commission 2026-10-21 (micro-themes must go immensely beyond the master plan); Fable_Execution_Handoff_2026-10-21.md D6 and acceptance boundary (2); DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK"
decided_at: 2026-10-21
---

# Micro-theme expansion 2026-10-21 is additive; the frozen 68 stay the acceptance set

The 303 ratified micro_themes and 53 sub_themes join the crosswalk hierarchy as dated
display-tier rows. Nothing about acceptance boundary (2), the coverage proof's declared
count, membership, rights or evaluation changes. Integration lands through one reviewed
crosswalk PR carrying the ratification receipts verbatim.
