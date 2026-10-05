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
  - agentos/workstreams/WS-RESEARCH-VAULT-AI-FABRIC.md
discoveries:
  - "DSC:A-RERUN-REPLAYS-THE-STALE-MERGE-COMMIT-REFRESH-THE-BRANCH-INSTEAD"
  - "DSC:LANE-HOST-CLONE-MUST-FETCH-THE-PR-BRANCH-PREFIX"
  - "DSC:LANE-KIT-HARDCODED-ZSH-KILLED-EVERY-LINUX-LANE-AT-POPEN"
  - "DSC:MARKETDESK-SOURCE-VERIFIER-FAILS-ON-PYCACHE-FROM-A-LOCAL-PYTEST-RUN"
do_not_redo:
  - "F1 #8442, F2 #8443, RIO identity #8446, MarketDesk lineage split #8452 are MERGED and accepted; never re-implement."
  - "The F2 live census receipt is workflow run 37289367732 (MIXED: 2,425 missing corpus rows + 2 thin-body rows); never re-run the normal ingest workflow as read-only proof."
  - "The three research-vault-source-lineage reds on #8472 are repaired at head 74bc480e1d6a (ACCEPT with recorded deviation, comment 5992497324); never re-repair or re-refresh SHA256SUMS/RELEASE_RECEIPT there."
  - "Never run the Mac13,1 `marketdesk auth` ceremony on process presence or catalog staleness alone; the 2026-10-05 readback (comment 5992501774) shows a storage stall (EINTR on /Volumes/STORAGE, 31 GiB free vs 100 GiB floor) and 0 SessionExpired."
  - "Never merge #7354 / #7522 / #8090 wholesale; never reinterpret RIO v1 hash semantics; never expose raw R2 operations."
  - "F6 #8475 is MERGED (squash e2be81444d4c, 2026-10-05 12:03:48Z; engine/research_vault/subjects.py, tests/test_research_vault_subjects.py and the research-vault legacy job blob-verified on origin/main); never re-implement the subject bridge or re-open the PR."
  - "The ci-pack-0 red inherited by #8475 (Q06 JSON from #8069 missing in six curated exclusive scopes) is healed by #8484 (squash 20eb503a09ae); never re-widen those six paths: lists or re-run run 37293056579."
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
    status: in_progress
    pr: 8472
    depends_on: [RIO-LINEAGE]
    next_action: >
      CI concluded green on head 74bc480e1d6a (rung posted as #8472 comment 5992916802); the PR
      stays DRAFT under the blocking review 5990516197 until the operator clears the Mac13,1
      storage wedge and one natural report proves SOURCE_FRESH (EXACT_HUMAN_GATE). Nobody
      readies, arms or merges it before that release.
  - id: F5
    title: Exact full-text/segment contract (ceded to Astra, #8453 / #8477)
    status: in_progress
    pr: [8453, 8477]
    next_action: "Astra's lane; this seat never launches rv_f5_segment_* nor edits #8453/#8477."
  - id: CI-PACK-0-HEAL
    title: Heal the inherited ci-pack-0 red (six curated exclusive scopes widened by #8069's Q06 JSON)
    status: done
    pr: 8484
  - id: F6
    title: Subject / Data OS identity bridge
    status: done
    pr: 8475
    depends_on: [RIO-LINEAGE, CI-PACK-0-HEAL]
    next_action: "MERGED e2be81444d4c; PRODUCTION_PROOF is the first consumer run that resolves subjects through engine/research_vault/subjects.py (record it on #8438 when observed; do not claim it before)."
  - id: F3
    title: Corpus repair over the F2 census classification (bounded strict-ingest lane, single writer)
    status: todo
    depends_on: [F1-F2, F5]
    next_action: "Wait for Astra's frozen F3 packet on #8438, then commission ONE fabric lane (never m1 while the storage hold stands)."
next_action: >
  Consume #8438 from counterpart edge 5992482136 and #8472 from 5992352691 before any act.
  F6 is merged and F4 is green-and-held, so the only open lanes are external: commission ONE
  F3 fabric lane the moment Astra's corpus recurrence guard (93e9b38b, on no remote ref at
  12:0xZ) is merged and the F3 packet is frozen on #8438; route the Mac13,1 storage recovery
  to the operator as an exact human gate; record F6 PRODUCTION_PROOF on #8438 once observed.
---

# Research Vault AI Intelligence Fabric

Planning carrier: PR #8438 (`sol/research-vault-ai-fabric-masterplan-20261004`), whose branch
holds the masterplan chapters, the 2026-10-04 Sol handoff and execution checkpoint 08. This
record is the Agent OS pointer so that seat handoffs on main resolve to a workstream; the
program narrative stays on the carrier.

Seat continuity: `agentos/handoffs/RESEARCH-VAULT-AI-FABRIC-2026-10-05.md`.
