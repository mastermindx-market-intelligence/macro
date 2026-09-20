---
workstream: WS:GMI-THEME-GRAPH
session: sol/gmi-d2d-ontology-neighborhood-20260919
model: sol
ended_because: ci_handoff
mission: Continue Chairman-directed GMI ownership with exact-ID, read-only graph and proposal review on the existing PR.
state_before: Source 7a04aa4e2c4472f134d6a70833c1965f373ad46c had the verified UTC reader but no exact-proposal CLI; all 12 packs passed while the main-inherited dashboard registration gate stayed red.
changed:
  - {path: engine/theme_graph/ontology.py, what: Add exact-proposal evidence review using the existing clock, graph, probation and rights readers; no adjudication or graph mutation.}
  - {path: contracts/theme_graph/ontology_proposal_review.v1.schema.json, what: Add a strict read projection that references the existing neighborhood schema rather than copying its node/proposal contracts.}
  - {path: scripts/query_theme_ontology.py, what: Add mutually exclusive --proposal-id mode while retaining existing --node-id behavior.}
  - {path: tests/test_theme_graph_local_plane.py, what: Add 28 hosted checks for truth separation, exact pairs, clocks, unsupported subjects, one-read table views, default rights and CLI compatibility.}
  - {path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-20-takeover-and-tool-gates.md, what: Preserve actual feature delta, proof, ownership and held release gates.}
verified:
  - {claim: New consumer tests discriminate the absent capability and actual rights-default defect., command: "pytest tests/test_theme_graph_local_plane.py -k proposal_review; then the same full module", result: "Initial 25 failures; real CLI exposed the default-resolver defect, whose added test failed before repair. Final full module 125 passed."}
  - {claim: Existing graph and downstream consumer battery passes with the new read path., command: "python3 -m pytest tests/test_theme_graph_identity.py tests/test_theme_graph_materialize.py tests/test_theme_graph_contracts.py tests/test_theme_graph_lifecycle.py tests/test_theme_graph_crosswalk.py tests/test_theme_graph_local_plane.py tests/test_market_ontology_exposure_map.py tests/test_finviz_tree_refresh.py tests/test_theme_sources_registry.py -q", result: "507 passed; owner-final.exit is 0."}
  - {claim: All committed proposals remain hypotheses in schema-valid review packets., command: "PYTHONPATH=$PWD python3 <evidence-root>/proposal-review/audit_proposal_review.py <evidence-root>/proposal-review/corpus-final.json", result: "234 of 234 valid; 234 proposed; 234 RELATION_ABSENT; all six canonical input hashes unchanged; corpus-final.exit is 0."}
  - {claim: Real CLI traverses both exact endpoints through default rights handling., command: "python3 scripts/query_theme_ontology.py --proposal-id prop:4f5e710b2c995d2b --asof 2026-09-20 --knowledge-cutoff 2026-09-20 --out <evidence-root>/proposal-review/cli-review-final.json", result: "Exit 0; Utilities basket and energybaseutilities endpoints OK; proposal-only and exact relation absent."}
  - {claim: Existing strict graph guards remain valid., command: "python3 -m scripts.check_theme_graph_contracts --selftest and --strict; git diff --check", result: "Both guards exit 0; no graph or source-rights data diff."}
unverified:
  - {claim: New-head integration, independent acceptance, release and production deployment., what_would_verify: "Immutable integrated candidate, concluded binding checks, independent exact-head review, merge and required production readback."}
  - {claim: Natural D2C and full D2D acceptance., what_would_verify: "Accepted-source natural graph generation plus remaining curation and structural-owner breadth."}
unresolved: [Shared dashboard registration now on incumbent PR 7511, independent review not yet executed, older refused structural-owner scan and workstream edit not retried, full D2D and D2E/W3B/W3C remain incomplete]
next_actions: [Publish this verified extension on the same PR 7462, qualify immutable current-base integration, request and consume independent exact-head review, consume incumbent dashboard registration repair before release, verify the original natural D2C pipeline]
do_not_redo: [Merged PRs 6809 and 7458, accepted PIT replay and no-op proof, original reader repairs and four resolved threads, completed UTC 97/479 proof, any replacement GMI branch or PR]
danger_areas: [No proposal approval or graph writes, no inferred mapping from overlap or labels, no second store or rights owner, no trade authority, no blanket CI waiver, no denied-request retries]
prs: [7462, 6809, 7458, 7511]
---

Procedure pin: Mastermind@bceb5e1593b1dd7e9e34c3bccbceb02e6ccd5a26 (compatible 1.0.1 / bootstrap 1).
Evidence root: /Volumes/Mastermind/agent-evidence/gmi-d2d-takeover-20260920-sol; this extension's receipts are in proposal-review/.
Same-carrier scope ruling: macro PR 7462 comment 5748771045. Shared registration impact is on incumbent PR 7511 comment 5748769911.
The earlier UTC repair and original node-query semantics are preserved; this is an additive proposal selector, not a curation writer or a new ontology.
A combined read-only diagnostic call was platform-refused and not retried. The observed real CLI error and its failing test were sufficient to repair the independent default-resolver wiring; no permission, account, or safety configuration changed.
The actual default-rights CLI was rerun successfully after repair. The final whole-corpus proof is tied to code blob IDs, not a claim that a pre-commit HEAD already contained the extension.
Sol retains the next action. Current native Executive review dispatch is not proven available; a GitHub reviewer request is attention only until an actual independent review returns.
Original natural D2C run 35478395992 / engine 106014432012 remains the proof path; no duplicate run, cancellation, or production acceptance is issued here.
