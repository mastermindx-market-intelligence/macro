---
key: RESEARCH-VAULT-AI-FABRIC
title: Research Vault AI Intelligence Fabric (planning carrier PR #8438; Sol/Astra masterplan, Fable meta-CEO execution)
objective: >
  Turn the private Research Vault (MarketDesk producer -> private inbox -> ingest -> catalog/corpus
  -> API/product) into a governed, deterministic intelligence fabric without creating a second
  vault, producer, auth plane, queue or publication plane. Done means every #8438 phase F1-F6 is
  merged and production-proven, the live F2 read-only R2 census receipt gates an F3 corpus repair
  that leaves zero unusable catalog rows, the Mac13,1 producer returns SOURCE_FRESH through the
  incumbent path, and the real authorized ChatGPT + Deep Research path meets the #8438 DONE_WHEN.
status: active
program: qualitative-intelligence
repos: [macro]
owner: fable-ceo
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-05.md
  - agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-07.md
  - agentos/workstreams/WS-RESEARCH-VAULT-AI-FABRIC.md
discoveries:
  - "DSC:A-RERUN-REPLAYS-THE-STALE-MERGE-COMMIT-REFRESH-THE-BRANCH-INSTEAD"
  - "DSC:LANE-HOST-CLONE-MUST-FETCH-THE-PR-BRANCH-PREFIX"
  - "DSC:LANE-KIT-HARDCODED-ZSH-KILLED-EVERY-LINUX-LANE-AT-POPEN"
  - "DSC:MARKETDESK-SOURCE-VERIFIER-FAILS-ON-PYCACHE-FROM-A-LOCAL-PYTEST-RUN"
do_not_redo:
  - "F1 #8442, F2 #8443, RIO identity #8446, MarketDesk lineage split #8452 are MERGED and accepted; never re-implement."
  - "The F2 live census receipt is workflow run 37289367732 (MIXED: 2,425 missing corpus rows + 2 thin-body rows); never re-run the normal ingest workflow as read-only proof."
  - "Never run the Mac13,1 `marketdesk auth` ceremony from a session; it is the operator's act, and process presence or catalog staleness alone never justifies it."
  - "Never merge #7354 / #7522 / #8090 wholesale; never reinterpret RIO v1 hash semantics; never expose raw R2 operations."
  - "F6 #8475 is MERGED (squash e2be81444d4c); never re-implement the subject bridge or re-open the PR."
  - "The ci-pack-0 red inherited by #8475 is healed by #8484 (squash 20eb503a09ae); never re-widen those six paths: lists or re-run run 37293056579."
  - "F4 #8472 is MERGED (squash 0ae4fa250956, 2026-10-06 22:15:06Z, on concluded-green head 74bc480e after HOLD-RELEASED 6026434249); never re-repair the lineage tests or re-refresh SHA256SUMS/RELEASE_RECEIPT."
  - "F5 #8453 is MERGED (squash a80e6ff8ff77, 2026-10-06 23:13:00Z, head bfef2c75 after seat HOLD-RELEASED 6027150323); the fulltext replay ends in canonical build_segments()[index] equality. Never re-open it."
  - "The F3 empty-corpus recurrence guard is MERGED as #8551 (squash bde684c6, cherry-pick -x of Astra 93e9b38b, authorship preserved); never re-carry it."
  - "The stop-guard repairs are MERGED: #8503 (610889a4, a sync-only fast-forward of macro-main no longer files unsafe_branch) and #8564 (481d67119c85, a quarantined session may repair itself with EnterWorktree). Never re-fix either."
  - "Never set the research-ingest source-freshness outage ACK to quiet the PRODUCER_STALE red; that red IS the F4 Mac13,1 human gate."
  - "F9 #8579, F15 #8589, F3-TYPING #8593, F10 part 1 #8592 (the carry of #8477) and F10 part 2 #8610 are MERGED; never re-implement or re-open #8477."
  - "F12 rulings M1-M10, Q-L0-2, F12-Q-L4-1 and F12-Q-L4-2 are settled: the MCP schema is a 1:1 projection of F10 and there is no F10 part 3."
  - "Never add pdftotext to the VPS or extract on the request path; production text comes from the F5-M stored derivative written by the incumbent research-ingest producer."
waves:
  - id: F1-F2
    title: Private-R2 isolation + read-only body-health census lane
    status: done
    pr: [8442, 8443]
  - id: RIO-LINEAGE
    title: RIO claim-array identity + MarketDesk recovery/release lineage split
    status: done
    pr: [8446, 8452]
  - id: F4
    title: MarketDesk producer auth-health (hosted lineage tests repaired; Mac13,1 readback posted)
    status: done
    pr: 8472
    depends_on: [RIO-LINEAGE]
    next_action: >
      MERGED 0ae4fa250956. PRODUCTION_PROOF is an EXACT_HUMAN_GATE: the operator clears the Mac13,1
      storage wedge, re-authenticates only if the auth meta reads expired, and one natural report
      proves SOURCE_FRESH through the incumbent path. Sessions never run the re-auth.
  - id: F5
    title: Exact full-text/segment contract
    status: done
    pr: 8453
    next_action: "MERGED a80e6ff8ff77. #8477 (F10 consumer activation) is Astra's lane: never touch it, never launch rv_f5_segment_*."
  - id: CI-PACK-0-HEAL
    title: Heal the inherited ci-pack-0 red (six curated exclusive scopes widened by #8069's Q06 JSON)
    status: done
    pr: 8484
  - id: F6
    title: Subject / Data OS identity bridge
    status: done
    pr: 8475
    depends_on: [RIO-LINEAGE, CI-PACK-0-HEAL]
    next_action: "MERGED e2be81444d4c; PRODUCTION_PROOF is the first consumer run (F10 #8477) that resolves subjects through engine/research_vault/subjects.py; record it on #8438 when observed."
  - id: F6-PUBCLOCK
    title: Validate the full publication timestamp before taking its date (accepted defect 6029030377)
    status: done
    pr: 8566
    depends_on: [F6]
  - id: F3-GUARD
    title: Empty-corpus recurrence guard (Astra 93e9b38b)
    status: done
    pr: 8551
  - id: F3
    title: Corpus repair - bounded in-run backfill of catalog rows missing from the corpus
    status: done
    pr: 8569
    depends_on: [F1-F2, F5, F3-GUARD]
    next_action: >
      MERGED c6c0ab36cdbf. Backfill drains in production (run 37589824682: 150 rows, derivable
      excerpts 351 -> 500). PRODUCTION_PROOF closes when a main research-ingest summary shows
      re-extract checked=0 and the excerpt snapshot writing again (excerpts >= 749). The
      source-freshness red is the F4 human gate, never ACKed.
  - id: F3-TYPING
    title: Typed re-extract outcomes with their own CI step
    status: done
    pr: 8593
  - id: F9
    title: Deep-read vault head
    status: done
    pr: 8579
  - id: F15
    title: Retrieval benchmark fixture (committed catalog/excerpt text only)
    status: done
    pr: 8589
  - id: F10
    title: Governed ResearchReadService (part 1 read port = carry of #8477; part 2 service + Brain/MCP shims)
    status: done
    pr: [8592, 8610]
    depends_on: [F5, F6]
    next_action: "Part 1 MERGED 7f440521 and live. Part 2 #8610 MERGED bd6f27c8 and deployed (checkout bd6f27c8163); library only until F11."
  - id: F5-M
    title: Stored canonical-text derivative written by the incumbent research-ingest producer
    status: in_progress
    depends_on: [F5, F10]
    next_action: >
      Orchestrator lane. On merge, one research-ingest dispatch after an in-flight preflight, then
      track fulltext_inventory coverage to >= 95%. Never extract on the request path.
  - id: F11
    title: Shared read_runtime composition root (zero-arg build_read_service in production)
    status: todo
    depends_on: [F5-M]
    next_action: "Merges only at >= 95% F5-M coverage (ruling F12-Q-L4-2 (f))."
  - id: F12
    title: ChatGPT MCP read surface (Mastermind) - L1 contracts, L1.1 v1.1, L2 entitlement, L3 SDK app, L4 port adapter + runtime, L5 ops
    status: in_progress
    depends_on: [F10]
    next_action: >
      L1 Mastermind #1279 MERGED a2254b29 (merge queue). Phase C (v1.1 contracts) + L2/L3 run in one
      Opus orchestrator lane; L4/L5 launch after them. Rulings M1-M10, Q-L0-2, F12-Q-L4-1/2 bind.
  - id: F13-F14
    title: Body exposure to ChatGPT / Deep Research canary and acceptance
    status: todo
    depends_on: [F12, F11]
    next_action: "EXACT_HUMAN_GATE: Chairman H-00 rights ruling, then H-02..H-15 operator acts."
    wait:
      kind: external_action
      review_after: 2026-10-10
      condition: "Chairman H-00 rights ruling on copyrighted body exposure to ChatGPT; sessions never override it."
next_action: >
  Read #8438 forward from the last counterpart edge before any act. Carry F12 Phase C + L2/L3
  through the Mastermind merge queue, then launch L4/L5 from the frozen mission; carry F5-M to
  merged and track fulltext coverage to >= 95% before F11 merges; record F3 PRODUCTION_PROOF
  from the next main research-ingest summary. F4 and H-00 stay human gates.
---

# Research Vault AI Intelligence Fabric

Planning carrier: PR #8438 (`sol/research-vault-ai-fabric-masterplan-20261004`), whose branch
holds the masterplan chapters, the 2026-10-04 Sol handoff and execution checkpoint 08. This
record is the Agent OS pointer so that seat handoffs on main resolve to a workstream; the
program narrative stays on the carrier.

Seat continuity: `agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-07.md` (latest) and
`agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-05.md`.
