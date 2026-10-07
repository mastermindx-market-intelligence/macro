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
    status: in_progress
    pr: 8566
    depends_on: [F6]
    next_action: "Seat-owned; must land before F10 #8477 activates a consumer. Armed merge-on-green; on merge, blob-verify engine/research_vault/subjects.py and tests/test_research_vault_subjects.py on origin/main."
  - id: F3-GUARD
    title: Empty-corpus recurrence guard (Astra 93e9b38b)
    status: done
    pr: 8551
  - id: F3
    title: Corpus repair - bounded in-run backfill of catalog rows missing from the corpus
    status: in_progress
    pr: 8569
    depends_on: [F1-F2, F5, F3-GUARD]
    next_action: >
      The in-run _backfill_missing_rows pass (cap 150 rows, 150 s budget, newest first, strict store,
      never raises) runs after _reextract_bodies under not dry_run. On merge, PRODUCTION_PROOF is a
      main research-ingest run whose summary shows backfill_rows > 0, the corpus count rising run over run
      toward the 2,778-row catalog, and the excerpt guard no longer refusing. While the producer is stale
      the job stays red on source-freshness only; that red is the F4 human gate, never ACKed.
next_action: >
  Read #8438 forward from counterpart edge 6029030377 (last seat edge 6029985312) before any act.
  Carry #8566 (F6 pub-clock) and the F3 backfill PR to merged with blob verification, then watch the
  next main research-ingest summary for backfill_rows and a rising corpus count (F3 PRODUCTION_PROOF).
  F4 production proof is the operator's Mac13,1 act. F6 production proof arrives with Astra's F10 #8477.
---

# Research Vault AI Intelligence Fabric

Planning carrier: PR #8438 (`sol/research-vault-ai-fabric-masterplan-20261004`), whose branch
holds the masterplan chapters, the 2026-10-04 Sol handoff and execution checkpoint 08. This
record is the Agent OS pointer so that seat handoffs on main resolve to a workstream; the
program narrative stays on the carrier.

Seat continuity: `agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-07.md` (latest) and
`agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-05.md`.
