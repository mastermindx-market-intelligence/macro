---
workstream: WS:GMI-THEME-GRAPH
session: sol/gmi-d2d-ontology-neighborhood-20260919
model: sol
ended_because: ci_handoff
mission: Build usable GMI research and curation evidence through existing graph and proposal owners; parent mission remains incomplete.
state_before: At 939d1bef1e55693959e0185bbfcbcdc65ae6220c exact readers and historical briefs existed, but proposal overlap required manually comparing all endpoint membership rows.
changed:
  - {path: engine/theme_graph/membership_evidence.py, what: Pure exact-member overlap drilldown preserving both sides of each membership and original proposal statistics separately.}
  - {path: scripts/explain_theme_overlap.py, what: JSON or readable Markdown CLI consuming existing proposal-review exports without graph access or overwrites.}
  - {path: contracts/theme_graph/ontology_overlap_evidence.v1.schema.json, what: Research-internal projection referencing the existing relation contract with explicit unavailable states.}
  - {path: tests/test_theme_graph_local_plane.py, what: Twelve additional hosted cases for exact counts, duplicate evidence, clock and identity binding, stable ordering, immutability, and CLI protection.}
  - {path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-20-takeover-and-tool-gates.md, what: Cumulative build and gate checkpoint; no source or reviewer transfer.}
verified:
  - {claim: The new consumer discriminates the missing capability., command: "python3 -m pytest tests/test_theme_graph_local_plane.py -k gmi_overlap -q", result: "12 failed before implementation; 12 passed after implementation."}
  - {claim: Existing graph and consumers remain compatible., command: "Nine-module pytest owner command recorded in overlap-evidence/verification.json", result: "552 passed; owner.exit=0. Graph selftest and strict audit both exit 0."}
  - {claim: Exact real membership evidence is preserved., command: "PYTHONPATH=$PWD python3 <evidence-root>/overlap-evidence/audit_overlap.py <evidence-root>/overlap-evidence/corpus.json", result: "234/234 packets schema-valid; 801 distinct graph member IDs; all six canonical input hashes unchanged."}
  - {claim: Real CLI works in both output modes., command: "python3 scripts/explain_theme_overlap.py --review <evidence-root>/overlap-evidence/utilities-review.json [--format markdown]", result: "Both exit 0 and equal corpus output; Utilities has 31 source IDs, 9 target IDs, 9 shared, 22 source-only, 0 target-only."}
  - {claim: Shared dashboard suite registration now exists., command: "git grep tests/test_unified_dashboard_b1.py 2042b2f4ca5bcd84da47f0937f3b6a1e3d488b77 -- .github/ci/legacy-jobs.yml", result: "Registered at line 2929; incumbent 7511 merged. Fresh binding CI is still required, not inferred."}
unverified:
  - {claim: Exact amended-head integration, independent review and release., what_would_verify: "Immutable integration and binding checks plus actual independent review; no reviewer START has returned."}
  - {claim: Missing-data and null-peer regression coverage for this increment., what_would_verify: "The specific attempted test append was platform-refused, read back NOT_APPLIED and not retried; those proposed fixtures remain absent."}
  - {claim: Full D2D and GMI production acceptance., what_would_verify: "Remaining governed curation and structural breadth, accepted natural D2C output, then D2E/W3B/W3C."}
unresolved: [Independent exact-head acceptance, new binding CI, absent refused regression appendix, previously refused discovery and structural actions, natural D2C proof absent at last reconciliation]
next_actions: [Publish tested overlap capability on same PR 7462, qualify current-main integration, consume independent review and binding gates, retain explicit untested negative-path coverage rather than retrying its refused edit]
do_not_redo: [Merged 6809 and 7458, PIT replay and no-op proof, repaired reader clocks and dismissed addressed reviews, accepted source proof for exact proposal and history readers, any replacement GMI carrier]
danger_areas: [Overlap is not mapping approval, node IDs are not normalized securities, zero recorded memberships is not coverage completeness, no curation or graph-data write, no public-display or investment authority]
prs: [7462, 6809, 7458, 7511]
---
