---
workstream: "qualitative-intelligence"
session: "chatgpt/research-vault-ai-fabric-masterplan-20261004"
model: "GPT-5.6-Sol"
ended_because: "orchestration_packet_published"
mission: >
  Harden the existing institutional Research Vault into one canonical, source-bound,
  rights-safe research interface usable by authorized ChatGPT and Deep Research sessions,
  without creating another Research Vault, identity authority, RIO store, auth plane or
  object-store API. Produce an execution-grade Fable CEO packet after current-source census.
state_before: >
  Research Vault already had private-R2 ingestion, a 2,778-report catalog, gated view/download,
  SQLite FTS, deterministic evidence passages, Brain report/search modes and a grounded
  Research Intelligence schema/store. However the current source producer was stale, the
  search/body corpus was known historically incomplete and currently collapsing in excerpt
  derivation, metadata facets were mostly empty, private R2 construction retained a verified
  shared/public fallback landmine, and four useful Research Intelligence PRs were stale and
  diverged from current main.
changed:
  - path: research/research_vault_ai_fabric_20261004/README.md
    what: "Cold-start index, architectural ruling, measured blockers and program DONE_WHEN."
  - path: research/research_vault_ai_fabric_20261004/00_FABLE_CEO_ASSIGNMENT.md
    what: "Principal Fable mission, WHY FABLE, start sequence, delegation envelope, non-goals and escalation boundary."
  - path: research/research_vault_ai_fabric_20261004/01_CURRENT_STATE_CENSUS.md
    what: "Measured 2,778-report estate; source staleness; corpus/excerpt defect; metadata coverage; RIO/MCP state; explicit unknowns."
  - path: research/research_vault_ai_fabric_20261004/02_ARCHITECTURE_AND_MASTERPLAN.md
    what: "Canonical owner architecture, dual PDF/text hash contract, full-text/segment design, metadata identity, read port, MCP and correction/rights law."
  - path: research/research_vault_ai_fabric_20261004/03_WORK_PACKAGES_AND_DAG.md
    what: "F0-F17 dependency DAG, collision-safe work packages, routing/delegation boundaries and concrete acceptance for each phase."
  - path: research/research_vault_ai_fabric_20261004/04_ACCEPTANCE_SECURITY_AND_EVAL.md
    what: "Program DONE_WHEN, denial/privacy tests, retrieval benchmark, tail evidence test, RIO/MCP/ChatGPT/Deep Research real-path gates."
  - path: research/research_vault_ai_fabric_20261004/05_SOURCE_AND_COLLISION_MAP.md
    what: "Canonical source anchors, stale PR salvage boundaries, hot path collisions, planning-carrier precedence and DO_NOT_REDO."
  - path: research/research_vault_ai_fabric_20261004/06_HARDENING_ADDENDUM_AND_FABLE_START_GATE.md
    what: "Controlling clarification of current R2 isolation semantics, body-health census, missing-row vs broken-body repair shapes, planning-carrier collision and exact Fable first-wave gate."
  - path: research/research_vault_ai_fabric_20261004/07_FABLE_ORCHESTRATOR_BRIEF_QA.md
    what: "Mastermind Craft orchestrator authoring QA receipt; intentionally UNBOUND_AUTHORING and non-authoritative."
verified:
  - claim: "The current catalog contains 2,778 reports and metadata cannot currently support the desired ticker/desk/tag filters."
    command: "Read current data/research_vault/catalog.json and compute fill counts."
    result: "summary_points 2751/2778; pages 2673/2778; desk 10/2778; tags 10/2778; tickers 0/2778."
  - claim: "The current upstream research source is stale while publication itself still succeeds."
    command: "Inspect latest completed research-ingest run 37224411920 / job 111500981779."
    result: "ingested=0 skipped=2778 failed=0; corpus_published=True catalog_published=True; source freshness PRODUCER_STALE at 249.152h vs existing 96h ceiling, latest report 2026-09-24T09:28:05Z."
  - claim: "The current body/excerpt derivative is materially collapsed."
    command: "Inspect current data/research_vault/excerpts.json and latest research-ingest logs."
    result: "committed excerpt snapshot has 1497 report keys; current derivation produces 351 and collapse guard refuses 1497 -> 351."
  - claim: "This defect class predates the current run and has an exact known corpus mechanism."
    command: "Read research/RESEARCH_VAULT_WAVE4_CONTINUATION_HANDOFF_2026-08-19.md; search current main for _backfill_corpus_rows."
    result: "2026-08-19 production census had catalog/pdf/receipt=1412, corpus=494, catalog-corpus=918; safe bounded missing-row backfill was recommended but is still absent on current main."
  - claim: "Private Research Vault isolation is not structurally fail-closed in the current factory."
    command: "Read current engine/research_vault/r2_store.py and DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET; reconcile historical discovery wording against current code."
    result: "Current build_store requires an explicit R2_RESEARCH_BUCKET, so the old full-bucket-fallback wording is stale. Endpoint/key/secret may still inherit generic R2 values and no factory assertion rejects R2_RESEARCH_BUCKET == R2_BUCKET. Normal deployment supplies the dedicated research secret family, but the source contract still needs explicit private-plane isolation."
  - claim: "Adjacent source identity uses two different SHA byte domains."
    command: "Read engine/research_vault probe/corpus facts and engine/research_intelligence/extractor.py::_identity."
    result: "Vault content_sha256 binds canonical PDF bytes; RIO v1 document.content_sha256 binds extracted UTF-8 body bytes. Masterplan freezes explicit source_pdf_sha256 vs extracted_text_sha256 compatibility."
  - claim: "The four RIO continuation carriers remain unmerged and should not be merged wholesale."
    command: "Read PR metadata and compare heads to current main."
    result: "#7354, #7461, #7522, #8090 are OPEN/unmerged/non-mergeable and heavily diverged. Packet identifies only still-useful deltas for salvage."
  - claim: "Current OpenAI product supports the proposed private canary architecture."
    command: "Recheck official OpenAI developer-mode MCP, Secure MCP Tunnel, plugin auth and MCP server deployment docs on 2026-10-04."
    result: "Pro developer mode supports MCP read/fetch; Deep Research supports custom-app read/fetch; local-only MCP is not directly reachable; Secure MCP Tunnel supports private developer connectivity; public submission is a separate stable-public-HTTPS class."
unverified:
  - claim: "Current live R2 catalog/PDF/corpus/receipt sets and exact mismatch counts."
    what_would_verify: "Run the existing read-only Research Vault census against the actual private store under current owner and preserve the report; no receipt or object mutation."
  - claim: "Exact current corpus.sqlite size and total full-text/index footprint."
    what_would_verify: "F2 capacity census / deterministic storage measurement."
  - claim: "Why the upstream producer stopped after 2026-09-24."
    what_would_verify: "Trace producer -> private inbox -> ingest listing, preserving source/auth/scheduler distinctions."
  - claim: "Private Research MCP is deployed/connected or a Fable orchestration runtime has STARTed."
    what_would_verify: "Separate runtime/transport pickup and START evidence; this source handoff intentionally does not claim either."
unresolved:
  - "F1 must structurally remove the Research Vault shared/public R2 fallback before new external private retrieval is admitted."
  - "F2/F3 must measure and repair current corpus completeness; 351 current excerpt-derived rows is a symptom, not a complete id-set census. F2 must also measure body/text health because a corpus row can exist with unusable text."
  - "F4 must restore or truthfully classify upstream source freshness."
  - "F5 must establish explicit PDF-byte vs extracted-text-byte identity before durable segment/citation APIs."
  - "F6 must build provenance-bearing metadata identity because source catalog has zero ticker coverage."
  - "F8/F9/F11/F16 must salvage exact useful deltas from stale PRs rather than merge them wholesale."
  - "F12-F14 must use existing protected MCP/auth owners and real private ChatGPT/Deep Research canaries."
next_actions:
  - "Fable/CEO intake: re-pin current protected Mastermind + Macro, reconcile path custody, then execute F1 private-plane isolation and F2 live read-only Vault ID-set plus body-health census as the first critical capability increment."
  - "Advance F8 (#7461 structural claim repair) in parallel if source custody is disjoint; do not begin broad RIO backfill before F5 hash/text contract."
  - "Use research/research_vault_ai_fabric_20261004/00_FABLE_CEO_ASSIGNMENT.md as the principal handoff and the remaining packet as its source map."
do_not_redo:
  - "Do not create a new workstream/program for this packet; parent is existing qualitative-intelligence."
  - "Do not rebuild already-merged Research Intelligence foundations: #7101 RIO v1 (merge 0859610d), #7230 W2 persistence (20454129), #7079 source-bound Brain evidence (0d352926), #8027 rights-safe belief projection (563362ae)."
  - "Do not reopen #8389 or #8430 as competing masterplans; both were unique-evidence checked and closed unmerged as superseded by canonical planning candidate #8438."
  - "Do not build a second Vault/search/identity/RIO/auth/lifecycle owner."
  - "Do not delete receipts or blindly re-ingest the historical Vault to repair corpus rows."
  - "Do not merge #7354/#7461/#7522/#8090 wholesale."
  - "Do not expose raw R2/S3 operations or let model arguments select bucket/root/key/credential."
  - "Do not change RIO v1 content_sha256 semantics in place."
  - "Do not treat RIO synthesis as literal source evidence."
  - "Do not weaken the source freshness guard merely to make research-ingest green."
  - "Do not open public MCP ingress just to prove the private canary; private tunnel comes first."
danger_areas:
  - "Research Vault publication and source-content freshness are different clocks; a fresh catalog republish can contain stale source material."
  - "A green Research Vault ID-set census can still hide a body/text-health collapse; identity completeness and retrieval completeness are separate acceptance axes."
  - "The excerpt collapse guard is protecting a known-better snapshot; editing/deleting it would hide the corpus defect rather than repair it."
  - "Data OS VendorAliasTable is exact security identity owner; engine/entity_resolver is candidate/context resolution only."
  - "Research Intelligence and Research Vault currently overload content_sha256 across different byte domains."
  - "legacy-jobs.yml and brain_market_intel.py are contested/high-collision paths; recover live writer custody before modifications."
prs: [7354, 7461, 7522, 8090]
decisions: []
discoveries:
  - "DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET"
---

# Research Vault AI fabric — durable handoff

This record marks the planning/census package as ready for orchestration. It does **not** claim a Fable receiver has picked it up, that an Executive Job exists, or that any implementation/deployment has started.


## 2026-10-04 continuation delta — F4 producer diagnosis

New canonical packet artifact:

research/research_vault_ai_fabric_20261004/08_F4_PRODUCER_OUTAGE_DIAGNOSIS.md

Verified delta:

- hourly Research Vault publication continued while source population hard-stopped at 2,778 rows;
- the last source timestamp remains 2026-09-24T09:28:05Z;
- accepted incidents #6862 and #7297 prove the same Mac13,1 producer had previously failed from MarketDesk auth expiry and was healthy again on September 18;
- current trickle source can park SessionExpired accounts indefinitely while the process remains alive;
- the current PROVEN_LIVE immediate trigger owner remains com.mastermindx.research-feed from #6949;
- PR #7226 is an unactivated alternative trigger architecture, not current production authority;
- current extractor release verification still freezes the historical recovery manifest, so legitimate F4 source edits require selective port of the dual-manifest / release-receipt evolution model before modifying source-owned runtime bytes.

Remaining F4 proof boundary:

Exact live host cause is still UNPROVEN until read-only Mac13,1 log/profile inspection. If auth loss is confirmed, recovery requires the human single-writer ceremony against the EXISTING persistent MarketDesk profile: stop exactly com.mastermindx.research-trickle, run marketdesk auth, restart the same LaunchAgent, then prove one new natural report traverses producer -> inbox -> canonical PDF/catalog/corpus/receipt and source freshness returns healthy.

DO_NOT_REDO:

- do not weaken the source freshness deadline;
- do not create a second MarketDesk profile/producer/scheduler/queue/bucket;
- do not retire the current feed watcher merely because #7226 exists;
- do not mutate extractor source while the historical frozen-manifest verifier would reject the release;
- do not call process presence producer health after SessionExpired.
