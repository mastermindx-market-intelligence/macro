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


## 2026-10-05 05:01 ET — planned context-rotation checkpoint

```text
FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
ROTATION_REASON: MANUAL_RETIREMENT / Chairman requested checkpoint + fresh-session handoff
UNRESOLVED_EFFECTS: none
```

### Current source/procedure pins

- protected Mastermind: `7eac3ec252475600147ec9a376b8ca16403ac4c5`
- Skillpack: `mastermind.sol_skillpack.v1` 1.0.1
- observed Macro main: `8a3310cdf03bc16704d51235172a5bbcf1f9a73e`
- canonical planning / continuity carrier: PR #8438, branch `sol/research-vault-ai-fabric-masterplan-20261004`

A successor must re-pin both repositories before effects. These pins establish this checkpoint only.

### Verified capability ledger at rotation

#### Merged / do not redo

- F1 private R2 source isolation: PR #8442 merged as `94228ca2555c898a183e9d6f99c23e8eeefd5f64`.
- F2 body-health census + separate read-only operator workflow: PR #8443 merged as `1d0c17cf298643e3d62a1632815decc8bef74691`.
- RIO claim-array identity repair: PR #8446 is merged. Do not resurrect #7461.
- MarketDesk recovery-vs-release lineage split: PR #8452 is merged. Historical recovery provenance stays immutable while current release bytes may evolve under the release manifest/receipt.

#### Active / one writer per carrier

- F5 exact full-text/segment contract: PR #8453, head `4895b47660d817889556757560c004d00951db80`, draft/open.
  - hosted CI is broadly green, including `research-vault-contract`.
  - principal review is still blocking on two contract defects:
    1. segment artifacts/replay must bind `extractor_name`, not only extractor version;
    2. `replay_segment()` must prove the supplied row equals the canonical deterministic segment for its declared index/version/max-bytes, not merely any valid byte slice.
  - required adversarial tests: mutate extractor_name, segment_index, segmenter_version, and a recomputed alternate valid byte window; canonical replay must refuse all four.
  - DO NOT create a second chunk/span abstraction.

- F4 producer auth-health recurrence repair: PR #8472, head `4df909395c2ef2bd1e4c27f23051940b3823c54a`, draft/open.
  - architecture is accepted directionally: existing MarketDesk SQLite meta + existing feed_probe/feed watcher; no second health DB/scheduler/auth service.
  - `ci-pack-10 / research-vault-source-lineage` is red: 3 failed / 357 passed.
  - exact repairs required on the same carrier:
    1. lineage test must preserve immutable `RECOVERY_SHA256SUMS`, while current `SHA256SUMS` must match `RELEASE_RECEIPT.manifest_sha256` and current payload bytes;
    2. empty-vault feed fixture must emit the new 7-field typed-auth probe contract;
    3. canonical-dispatch fixture must emit the same new contract so dispatch is actually reached.
  - even after source CI passes, production acceptance still requires Mac13,1 readback + exact auth state + human single-writer re-auth only if needed + one natural new report end to end.

- F6 subject/Data OS identity bridge: PR #8475, head `310cd7b9a707af798b1595b5bfbf592b6f428410`, draft/open.
  - `ci-gate` is currently red because `contract-delta` is red; other observed CI packs are green.
  - no review comment was present at this checkpoint.
  - first successor action on this carrier is to inspect the exact `contract-delta` failure; do not guess/fix broadly.
  - architectural law already frozen: exact report-symbol semantics should use the Data OS `exchange` historical alias namespace, not silently substitute `membership` or `yahoo`; exact Data OS builder custody must be reconciled before adding that namespace.

### F4 producer diagnosis — accepted read-only findings

The September 24 cutoff is upstream of hourly Research Vault ingestion.

Observed hard stop:

```text
catalog count grew to 2778 by generated_at 2026-09-24T12:12:47Z
last admitted source published_at = 2026-09-24T09:28:05Z
later catalog generations keep advancing generated_at but never exceed 2778
```

Accepted prior incident #6862 proves the same external symptom previously came from MarketDesk persistent-session auth expiry while hourly ingest kept republishing an unchanged catalog.

Current source proves the recurrence mechanism:

```text
SessionExpired
  -> account.authed = false
  -> producer process stays alive
  -> discovery/downloads skip indefinitely
  -> dead-driver watchdog never fires because no attempts occur
  -> feed watcher historically sees process presence, not authenticated producer health
```

Thus process presence is not producer health.

This is a **high-confidence recurrence class**, not proof that the current Mac13,1 profile is definitely expired. The native host tunnel was unavailable during diagnosis, so the exact live cause remains a host/human gate.

PR #7226 is closed/unmerged and was never production-activated. Do not revive it wholesale or treat it as current trigger authority. The incumbent immediate trigger remains `com.mastermindx.research-feed`.

### Live F2 measurement remains owed

The merged F2 workflow is a dedicated manual read-only proof lane. This session did not produce a live R2 census receipt.

Do not start F3 repair from historical counts or the 351-excerpt symptom alone.

Required order:

```text
run live read-only F2 census
  -> classify:
       A missing corpus rows
       B existing rows with unusable body
       typed no-text scans
       mixed
  -> admit only the measured F3 repair class
```

Do not use `research-ingest.yml run_census=true` as read-only acceptance; that workflow also owns ingest/publication effects.

### Exact successor start order

1. Re-pin protected Mastermind + Macro and read this handoff plus `research/research_vault_ai_fabric_20261004/08_EXECUTION_CHECKPOINT_2026-10-05.md`.
2. Reconcile live heads/custody of #8453, #8472, #8475 before any write.
3. Advance the smallest ready source blocker:
   - #8472: repair the three exact source-lineage fixture/test failures;
   - #8453: repair extractor-name + canonical-segment replay identity;
   - #8475: inspect and fix only the exact contract-delta failure after current-source review.
4. Independently obtain the merged F2 live read-only census receipt when an authorized workflow-dispatch surface is available.
5. Classify/admit F3 only from that receipt.
6. When Mac13,1 host access is available, inspect exact auth/log/launchd state. If the existing profile is expired, perform the human single-writer ceremony only:
   - stop exact `com.mastermindx.research-trickle`;
   - run `marketdesk auth` against the same existing profile;
   - install the accepted release through the incumbent installer;
   - restart the same existing LaunchAgents;
   - prove one natural report traverses MarketDesk -> private inbox -> ingest -> catalog/corpus -> API/product;
   - prove source freshness returns `SOURCE_FRESH`.
7. Continue toward F5 materialization / canonical Research Read port only after source/text identity and measured corpus truth are accepted.

### DO_NOT_REDO / danger laws

- Do not create a new Research Vault, corpus authority, vector authority, auth plane, lifecycle, scheduler, queue, producer, MarketDesk profile, health DB or publication plane.
- Do not redo merged #8442/#8443/#8446/#8452.
- Do not merge or copy stale #7354/#7522/#8090 wholesale; salvage only reviewed unique deltas when their dependency waves arrive.
- Do not weaken the source-freshness deadline.
- Do not delete receipts or replay the historical inbox to force corpus repair.
- Do not equate catalog freshness with source freshness.
- Do not equate corpus-row presence with usable text.
- Do not equate a running `marketdesk trickle` process with authenticated producer health.
- Do not automate MarketDesk login; re-auth is human/single-writer by source contract.
- Do not reinterpret RIO v1 `document.content_sha256`; it remains extracted-text SHA, while Vault PDF SHA is a separate byte domain.
- Do not expose raw R2/S3 operations or model-selectable bucket/root/key/credential.
- Do not claim Fable pickup, MCP deployment, ChatGPT installation, Deep Research acceptance, or production recovery without their separate evidence.

### Parent mission DONE_WHEN remains unchanged

Mission remains incomplete until the real path proves authorized ChatGPT + Deep Research can discover institutional reports, find tail evidence beyond the old 60k prefix, fetch replayable literal evidence with explicit PDF/text revision identity, distinguish literal source from RIO synthesis, respect entitlements/rights, deny private leakage to unauthorized callers, share one canonical Research Read contract with Brain, and survive source correction with stale derivatives detectably invalidated.

### Fresh-session instruction

Recover from canonical source, not chat history. Treat this checkpoint as durable organizational continuity, not execution authority or source custody. Continue the exact existing carriers; do not restart completed waves.
