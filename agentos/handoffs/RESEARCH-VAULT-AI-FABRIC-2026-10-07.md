---
workstream: "WS:RESEARCH-VAULT-AI-FABRIC"
session: "seat 0e657eec-8307-4654-afae-0f4463a1243c (Meta-CEO seat on Opus 5.5; labor via Opus orchestrators driving the ext/ fabric lanes; no native labor children)"
model: "opus"
ended_because: "blocked"
mission: >
  Continue the Research Vault AI Intelligence Fabric from planning carrier PR #8438 as Meta-CEO:
  land F9 deep-read head, the F15 retrieval benchmark fixture, F3-TYPING, F10 (the governed
  ResearchReadService, parts 1 and 2), the F12 ChatGPT MCP contracts (Mastermind), and the
  F5-M / F11 follow-ons that let production fetch and find_evidence answer from stored text -
  without creating a second vault, producer, scheduler, queue, store, auth plane or publication plane.
state_before: >
  At the earlier 2026-10-07 handoff (#8570): F4/F5/F3-guard/stop-guard repairs merged; #8566
  F6-PUBCLOCK and #8569 F3 backfill armed; #8477 F10 consumer activation was Astra's lane;
  F12 unspecified; no F15 fixture, no F9 deep-read head, no read service.
changed:
  - path: engine/research_vault/subjects.py
    what: "F6-PUBCLOCK #8566 merged (squash 32fc0e75343a, 03:39:21Z)."
  - path: engine/research_vault/ingest.py
    what: "F3 backfill #8569 merged (squash c6c0ab36cdbf); F3-TYPING #8593 merged (squash f0ef0fc0451c) with its own CI step at legacy-jobs.yml:10492."
  - path: engine/research_vault/vault_head.py
    what: "F9 deep-read head #8579 merged (squash e20149308a7b, 05:57:51Z), blob-verified."
  - path: tests/fixtures/research_vault/
    what: "F15 retrieval benchmark fixture #8589 merged (squash a0fc9f894fa1); only committed catalog/excerpt text, anchors <= 200 chars, body classes PENDING_HOST_FILL."
  - path: engine/research_vault/read_port.py
    what: "F10 part 1 #8592 merged (squash 7f4405219977): the carry of #8477 plus seat fixes. #8477 was auto-closed by the successor closing reference; its head was never pushed to. Live at 07:38Z (prod /api/health commit 7f440521997)."
  - path: engine/research_vault/read_service.py
    what: "F10 part 2 #8610 (ResearchReadService, Brain/MCP adapter shims, T16 unknown/forbidden-argument refusal): MERGED (squash bd6f27c8, 09:07:52Z) and deployed (production checkout bd6f27c8163 at 09:09:56Z); library only until F11 wires it."
  - path: agentos/workstreams/WS-RESEARCH-VAULT-AI-FABRIC.md
    what: "Waves F9, F15, F3-TYPING, F10, F12, F5-M and F11 added; F6-PUBCLOCK and F3 marked done; next_action refreshed."
  - path: agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-07.md
    what: "This record (supersedes the earlier same-day handoff from #8570)."
verified:
  - claim: "F9, F15, F3-TYPING, F10 part 1, F6-PUBCLOCK and F3 are merged and their files are on origin/main."
    command: "bare git fetch origin (rc 0); per-path git rev-parse origin/main:<path> against each PR head blob"
    result: "identical for every path in #8579, #8589, #8593, #8592; #8566 and #8569 recorded at merge."
  - claim: "F10 part 1 is live."
    command: "curl -sL https://mastermind-x.com/api/health"
    result: "commit = checkout = 7f440521997 at 07:38Z."
  - claim: "F10 part 2 #8610 merged byte-for-byte and is deployed."
    command: "bare fetch of origin (rc 0); rev-parse of <head 5d4fced0>:<path> and origin/main:<path> for the 4 code paths; curl -sL https://mastermind-x.com/api/health"
    result: "all 4 blobs identical; main legacy-jobs.yml:10516 names both new tests; production checkout bd6f27c8163 at 09:09:56Z."
  - claim: "F3 backfill drains in production."
    command: "gh run view 37589824682 --log (research-ingest on main)"
    result: "backfill rows 150, derivable excerpts 351 -> 500; the excerpt snapshot still refuses (collapse 1497 -> 500 under the 50% floor), so writes resume at >= 749."
unverified:
  - claim: "F3 PRODUCTION_PROOF (re-extract checked=0 and the excerpt snapshot writing again)."
    what_would_verify: "A later main research-ingest summary with excerpts >= 749 and re-extract checked=0."
  - claim: "Production fetch / find_evidence answer from stored text."
    what_would_verify: "After F5-M merges and its backfill runs: fulltext_inventory coverage >= 95% and a live fetch returning segments instead of EXTRACTION_UNAVAILABLE."
unresolved:
  - "F4 PRODUCTION_PROOF and the PRODUCER_STALE red are the Mac13,1 EXACT_HUMAN_GATE; never ACK, never re-auth from a session."
  - "F13/F14 (any copyrighted body exposure to ChatGPT) wait on the Chairman H-00 rights ruling (EXACT_HUMAN_GATE)."
  - "The #8438 DONE_WHEN (real authorized ChatGPT + Deep Research path) is not met."
next_actions:
  - "Read #8438 forward from the last counterpart edge before any act; the last seat edge is 6034756871."
  - "F12: carry the Phase C (L1.1 v1.1 contracts) and L2/L3 PRs through the Mastermind merge queue, blob-verifying each landing on fresh origin/master; then launch the L4/L5 lane from the frozen mission (port adapter + runtime under rulings F12-Q-L4-1/2, ops/runbook)."
  - "F5-M: judge the lane return by its artifact, carry the PR to merged, dispatch one research-ingest run after an in-flight preflight, and track fulltext_inventory coverage to >= 95%."
  - "F11: the shared read_runtime composition root; build_read_service() is zero-arg in production with a build-time classifier; merge only at >= 95% F5-M coverage."
  - "F3 PRODUCTION_PROOF: read the next main research-ingest summary for re-extract checked=0 and excerpts >= 749; record it on #8438."
do_not_redo:
  - "Do not re-open #8477; #8592 carried it and merged."
  - "Do not re-litigate F12 rulings M1-M10 + Q-L0-2: the MCP schema is a 1:1 projection of F10; there is no F10 part 3 for F12 v1."
  - "Do not add pdftotext to the VPS or extract on the request path; the fix is the F5-M stored derivative written by the incumbent research-ingest producer."
  - "Do not ACK PRODUCER_STALE to make the F3 proof look green."
danger_areas:
  - "Mastermind master has a GitHub merge queue: gh pr merge only enqueues; MERGED is the queue landing, read via GraphQL isInMergeQueue / mergeQueueEntry."
  - "The macro merge sweeper's update-branch moves an armed PR head; an exact-head watcher must exit HEAD_MOVED and be re-pointed, never merge a head it did not see."
  - "The model routing guard parses section headers as `NAME:` lines; a `SECTION: NAME` label parses as one section named SECTION and the spawn is refused."
prs: [8438, 8566, 8569, 8579, 8589, 8592, 8593, 8610]
discoveries: []
---

# Research Vault AI fabric - seat 0e657eec handoff (2026-10-07, second checkpoint)

This record supersedes the earlier 2026-10-07 handoff from #8570 for the Research Vault AI
fabric. The planning carrier is PR #8438; its branch holds the masterplan chapters and every
seat checkpoint, and this file is the Agent OS pointer a cold stranger starts from.

What landed this checkpoint: the F9 deep-read head, the F15 retrieval benchmark fixture, the
F3 typed re-extract outcomes, F10 part 1 (the carry of #8477 as #8592, live in production) and
F10 part 2 (#8610, the ResearchReadService with its Brain and MCP adapter shims). In the
Mastermind repo, the F12 L1 MCP contracts merged as #1279 through the master merge queue.

What runs next: two Opus orchestrator lanes drive the fabric workers. One carries F12 Phase C
(the v1.1 contracts amendment) with L2 (entitlement) and L3 (the SDK app); the other carries
F5-M (the stored canonical-text derivative, written by the incumbent research-ingest producer)
and then F11 (the shared read_runtime composition root). F12 L4/L5 has a frozen mission and
launches when a lane slot frees. The seat keeps pushes, merges, carrier posts and acceptance.

Rulings that bind the remaining F12 work: M1-M10 and Q-L0-2 (the MCP schema is a 1:1
projection of F10; no F10 part 3), F12-Q-L4-1 (the F10 runtime import closure is stdlib +
boto3/botocore + PyYAML, and the Macro release root never carries .env), and F12-Q-L4-2 (both
repos ship top-level app/scripts/tests packages, so the Macro release root comes first on
sys.path, an AST fence keeps the MCP closure off those names, startup refuses
MACRO_NAMESPACE_COLLISION and LOCAL_STORE_IN_PRODUCTION, and real-F10 tests run in a
subprocess).

What no session can do: F4 production proof and the PRODUCER_STALE red wait on the operator's
Mac13,1 re-authentication; F13/F14 wait on the Chairman H-00 rights ruling; the #8438
DONE_WHEN (a real authorized ChatGPT + Deep Research path) is not met.
