---
workstream: WS:GMI-THEME-GRAPH
session: sol/gmi-d2d-ontology-neighborhood-20260919
model: sol
ended_because: blocked
mission: Deliver the existing GMI ontology and curation research workflow without a second graph, queue, identity
  or approval authority.
state_before: Published 8684bc; 14 uncommitted paths preserved; canonical worklist CLI blocked on strict owner-reader
  integration; seven tests failing.
changed:
- path: engine/theme_graph/proposal_worklist.py
  what: Build a read-only typed-row worklist with exact filters
  cutoff-aware status: null
  UTC ordering: null
  digest-bound pages and existing review-query arguments.: null
- path: contracts/theme_graph/proposal_worklist.v1.schema.json
  what: Add the worklist projection referencing the existing proposal contract.
- path: engine/theme_graph/ontology.py
  what: Preserve proposal-origin notes before adjudication; expose separately clocked optional adjudication_note
    only when known.
- path: contracts/theme_graph/ontology_neighborhood.v1.schema.json
  what: Add optional decision-note projection; ordinary proposal note is creation content.
- path: contracts/theme_graph/probation_proposal.v1.schema.json
  what: Add optional adjudication_note without rewriting any queue records.
- path: engine/theme_graph/probation.py
  what: Complete opt-in strict JSONL reading; preserve legacy forgiving default; missing, malformed, duplicate-key
    and non-object inputs cannot masquerade as an empty or partial worklist.
- path: scripts/explain_theme_overlap.py
  what: Reuse existing 8 MiB duplicate-key-rejecting loader from explain_theme_changes and return structured
    refusal on excess recursion.
- path: tests/test_theme_graph_local_plane.py
  what: All seven formerly failing cases pass; five additional controls pin forgiving-default parity, nested
    duplicates, partial-file refusal, document bounds and no-output refusal.
- path: scripts/list_theme_proposals.py
  what: Existing CLI now operational through the strict canonical proposal owner; no replacement wrapper or
    queue.
verified:
- claim: All prior uncommitted work was recovered without loss.
  command: SHA256 comparison with proposal-worklist/verification.json; git diff --cached --name-only; git ls-files
    -u
  result: All 14 source identities matched, staging empty, no unmerged entries or MERGE_HEAD; byte backups
    under strict-input-continuation-20260921/source-before/.
- claim: The strict reader and overlap loader close the seven regressions.
  command: pytest tests/test_theme_graph_local_plane.py -k strict_queue/worklist_cli_pages/overlap_duplicate
    selection; exact invocations in evidence logs
  result: 'RED: 7 failed. GREEN: 7 passed; all seven retained and unskipped.'
- claim: The coherent local candidate passes the existing nine-module owner battery.
  command: Same nine-module owner command recorded in strict-input-continuation-20260921/verification.json;
    owner.log
  result: 630 passed, exit 0; includes five added boundary controls. Strict graph audit and contract selftest
    both exit 0.
- claim: The actual canonical-file worklist-to-review-to-overlap CLI works.
  command: python3 strict-input-continuation-20260921/real-cli-proof.py (absolute evidence-root path); real-cli-verification.json
  result: 15 subprocess CLI commands exit 0; 234 raw-file proposals across 10 pages, zero missing/duplicate
    IDs; exact Utilities filter returns 2; prop:4f5e710b2c995d2b resolves to RELATION_ABSENT; overlap source31/target9/shared9/source-only22/target-only0.
    All 8 canonical input-file hashes unchanged.
- claim: The separate identity-owner baseline is still red, not waived.
  command: python3 -m pytest tests/test_theme_graph_identity_resolution.py -q; identity-baseline.log
  result: '52 passed / 4 failed: two 2806-versus-2807 count assumptions, committed-bake reproducibility, and
    already-present VMRK sidecar assumption.'
unverified:
- claim: Changed-candidate current-base integration, publication and independent acceptance.
  what_would_verify: Freeze and qualify an immutable integrated candidate, publish normally on existing PR
    7462, then exact-head review and concluded binding CI without weakening HOLD.
- claim: Natural graph publication and full GMI parent completion.
  what_would_verify: Existing producer result and canonical graph receipt under original run ownership; complete
    remaining D2D breadth and gated D2E/W3B/W3C.
unresolved:
- Independent exact-head acceptance and release remain pending.
- Four identity-owner baseline failures remain unwaived.
- Historical tool-refusal cause remains unknown; this session has direct same-carrier APPLIED readback for
  the two source edits.
next_actions:
- Qualify immutable current-base integration of the preserved and repaired candidate.
- Publish on the original PR/branch only through a normal same-carrier fast-forward push and read back the
  exact head.
- Obtain changed-head independent review and concluded binding checks before any release ruling.
do_not_redo:
- Published 8684bc exact ontology/history/overlap readers and accepted predecessor work
- Preserved count comparison, exact security navigation, worklist core/CLI and separate creation/adjudication
  notes
- Completed strict-reader/overlap-loader integration and canonical 234-row CLI proof
- Merged 6809/7458, accepted PIT replay, or another queue/graph/identity authority
danger_areas:
- Proposals and browsing order confer no approval, ranking, trade or public-display authority.
- Never hide the four identity baseline failures behind the 630-test selected-owner result.
- No reset, force, rebase, stash, ancestry-only conflict concealment or duplicate graph producer.
- No blind retry or carrier change for any newly ambiguous/refused mutation.
prs:
- 7462
- 6809
- 7458
- 7511
---

MISSION_COMPLETE: false. This is the cumulative working checkpoint for the same Chairman-directed
operation gmi-theme-ontology-d2d-20260827-sol-001 and PR 7462. Sol retains source/release custody.
Protected procedure pin: Mastermind@6a24ed038774afff0bbab2982f420ef0e66e5b5f, Skillpack 1.0.1/bootstrap 1.
Direct execution: LOWER_TOTAL_OVERHEAD for two frozen reader integrations; no worker was spawned.

Evidence root: /Volumes/Mastermind/agent-evidence/gmi-d2d-takeover-20260920-sol/strict-input-continuation-20260921/.
Recovery manifest: proposal-worklist/verification.json SHA256
167f84122b94e57e4daaf0785b22f9d1e97656cbac9aea71f586763805c93c43.
All 14 prior working files were hash-verified and backed up before edits; the existing count,
security, worklist and note capabilities were preserved rather than rebuilt. Historical refusals
were NOT_APPLIED. Current same-Studio-carrier edits returned APPLIED and were read/test verified;
no account, permission, transport, provider or safety-setting change occurred.

The checkpoint's mergeable=false is no longer current: GitHub returned mergeable=true, and direct
merge-tree probes of published 8684bc against both fetched main 96e5b35ae123d196694d4576d9c4f94fc7767971
and GitHub's reported base af92792954e1ad8a4812cf0e73a2dc54dac0672a concluded without conflict.
Those are published-head probes, NOT proof of the new working candidate. No unnecessary ancestry
merge was made. Changed-candidate integration/publication receipts must be read from the current
verification.json and canonical cumulative PR checkpoint comment 5755209687.

Real CLI proof uses the original canonical proposal path with no substituted data root or mocked
reader. The first proof-driver attempt completed paging but used a case-mismatched Utilities label;
that driver failure is retained under real-cli-attempt-1/. The corrected driver uses the recorded
exact subject basket:baskets:us_sector_utilities and all 15 subprocess commands passed. Relation
state is read from exact-review.json#/relation/state, not a fabricated top-level field.

The separate identity baseline remains 52 passed / four failed; no fixture, identity owner or data
was rewritten to green it. No graph producer/rerun/cancellation or curation act was invoked.
The last locally observed graph generation remains 2026-09-18T17:42:29Z; a running or finished
workflow alone is not new graph proof. Prior Codex findings were against published 8684bc;
both repairs are now locally tested, not yet independently accepted. A pending reviewer request
is not evidence of a running worker. Draft/HOLD-FOR-SOL and RESEARCH_INTERNAL_ONLY remain binding.
Full D2D structural/curation breadth, deferred security history, D2E, ThemeState W3B and cohort W3C
remain unfinished. Continue from the current canonical checkpoint and exact evidence, not old chat.
