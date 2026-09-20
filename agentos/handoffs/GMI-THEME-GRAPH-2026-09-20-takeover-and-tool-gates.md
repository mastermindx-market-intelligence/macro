---
workstream: WS:GMI-THEME-GRAPH
session: sol/gmi-d2d-ontology-neighborhood-20260919
model: sol
ended_because: ci_handoff
mission: Build useful GMI research capabilities while release CI is pending; preserve canonical graph, curation and investment authority.
state_before: At 20e6b0322b466466d127190a97bb0f8d18f8efb4 exact node/proposal readers were built, but researchers had no evidence-preserving historical change brief.
changed:
  - {path: engine/theme_graph/change_report.py, what: Compare two existing neighborhood documents with explicit effective-date versus knowledge-revision labels and JSON plus readable Markdown output.}
  - {path: scripts/explain_theme_changes.py, what: Add a real bounded file-to-report CLI that rejects malformed or mismatched inputs and never overwrites input or existing output files.}
  - {path: contracts/theme_graph/ontology_change_report.v1.schema.json, what: Strict report contract references existing neighborhood and relation/proposal definitions.}
  - {path: tests/test_theme_graph_local_plane.py, what: Add 17 hosted tests for membership/evidence/proposal separation, missing-baseline abstention, stable ordering, input protection and readable correction details.}
  - {path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-20-takeover-and-tool-gates.md, what: Preserve real build progress and the independently deferred discovery prototype.}
verified:
  - {claim: Historical comparison is a working capability rather than a release-status artifact., command: "python3 -m pytest tests/test_theme_graph_local_plane.py -q -k gmi_change_report", result: "Initial 14 failures before implementation; one missing human status detail reproduced separately and repaired. All new cases included in final 540-test owner pass."}
  - {claim: Existing graph and downstream consumers remain compatible., command: "Nine-module pytest owner command in change-report/owner-final.log and verification.json", result: "540 passed; owner-final.exit=0. Existing strict graph guard exit 0."}
  - {claim: Real history is preserved without graph mutation., command: "25 real local-theme comparisons at 2026-08-14 versus 2026-08-15, fixed cutoff 2026-09-20; verification.json binds final working blobs", result: "26 recorded membership removals across 25 themes; original input hashes unchanged. Cloud Databases report identifies co:us:CFLT with old evidence IDs."}
  - {claim: Real default CLI produces both machine and human results., command: "python3 scripts/explain_theme_changes.py --baseline <evidence>/cloud-baseline.json --target <evidence>/cloud-target.json [--format markdown]", result: "Both modes exit 0; JSON equals verified history. GOLD report labels KNOWLEDGE_REVISION and names status canonical to retired; SNDK reports nine recorded membership additions."}
unverified:
  - {claim: Exact new-head integration and independent release acceptance., what_would_verify: "Immutable current-base composition, binding checks and actual independent review; source publication is not acceptance."}
  - {claim: Full GMI production outcome including discovery and remaining D2D breadth., what_would_verify: "Lawful unblocked implementation and acceptance of remaining curation/structural/discovery work, D2C natural proof, then D2E/W3B/W3C."}
unresolved: [Discovery append platform-refused and preserved rather than rerouted, independent review still owed, shared registration dependency on incumbent 7511, natural D2C engine cancelled without published proof]
next_actions: [Publish this verified independent history-report capability on the same PR, consume exact-head independent review without repeating old repairs, preserve deferred discovery evidence until its authoring gate is resolved, continue remaining lawful D2D capabilities]
do_not_redo: [Merged 6809 and 7458, accepted PIT replay and no-op, repaired lifecycle and UTC and mixed-clock readers, dismissed addressed reviews, any replacement GMI graph or carrier]
danger_areas: [Recorded membership changes are not capital flows, input digests are not source authenticity or coverage proof, no curation decisions or graph data writes, no duplicate state store or discovery service, missing comparison is not zero membership]
prs: [7462, 6809, 7458, 7511]
---
