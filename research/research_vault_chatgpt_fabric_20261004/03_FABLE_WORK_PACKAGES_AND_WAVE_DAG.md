# 03 — Fable work packages and wave DAG

**Purpose:** decomposition for a receiving Fable principal.  
**Important:** these packages are authoring targets, not dispatched workers. Re-check current Capacity, providers, hosts, source custody and budgets before every actual commission.

## 0. Orchestration principle

Fable should operate as principal architect/integrator, not as the default coder.

Use Fable for:

- unresolved cross-owner architecture;
- current-state/custody adjudication;
- private-data/security decisions;
- rights/product boundary decisions;
- held-carrier acceptance;
- integration across Macro and protected Mastermind;
- acceptance of real ChatGPT/Deep Research behavior.

Delegate when a bounded worker can receive exact inputs and return checkable evidence without deciding one of those questions.

Every child package must include:

- exact source pin;
- exact write paths;
- non-goals;
- input identities;
- time/null/correction/rights behavior;
- deterministic vs model method;
- failure behavior;
- acceptance;
- stop condition;
- durable return location.

Do not send the entire CEO conversation as a worker prompt.

## 1. Dependency matrix

| Package | Mission | Dominant task class | Depends on | May run in parallel with |
|---|---|---|---|---|
| F0 | source/custody reconciliation | C3 principal judgment | deliberate pickup | none initially |
| S1 | private R2 isolation | C2 bounded security engineering | F0 | V1, U1 |
| V1 | live Vault id-set/corpus census | C1/C2 bounded data investigation | F0 | S1, U1 |
| U1 | source-producer freshness diagnosis | C2 investigation | F0 | S1, V1 |
| R1 | excerpt-collapse/corpus restore root cause | C2 hard debugging | V1 partial evidence | S1, U1 |
| T1 | full-text size/economics measurement | C1 data engineering | V1 sufficiently healthy corpus | P1 |
| P1 | #7461 RIO claim-identity adjudication | C2 correctness | F0 | T1, U1 |
| T2 | canonical text artifact + segment contract | C2 architecture/implementation | T1, S1 | P2 preparation |
| T3 | full-tail retrieval implementation | C2 engineering | T2 | M1 |
| M1 | metadata enrichment benchmark | C2 data/research | V1, F0 | T2/T3 |
| P2 | #7354 deep-read producer reconciliation | C2 engineering | P1, T2 enough to choose body owner | T3/M1 |
| P3 | #7522 Brain consumer reconciliation | C2 engineering | P1, accepted W2 store, read contract direction | T3/M1 |
| C1 | canonical Research Read Service | C3 integration then C2 implementation | T3, P2/P3 semantics | M1 |
| A1 | Research MCP adapter | C2 engineering | C1, deployment profile decision | independent MCP schema review |
| A2 | deployment/app enrollment | C3 integration + operator gates | A1 | benchmark prep |
| Q1 | retrieval/security benchmark | C2 data/review | T3/C1/A1 depending test | A2 |
| X1 | ChatGPT authorized/denied canary | C3 product verification | A2, Q1 minimum gates | Deep Research prep |
| X2 | Deep Research canary | C3 product verification | A2, healthy source | X1 if independent |
| L1 | #8090 longitudinal belief continuation | C2 research/engineering | P1/P2, source identity | after MVP critical path |

Fable may reorder only when dependencies remain true.

## 2. F0 — source, authority and custody reconciliation

### Why principal-owned

A wrong decision here creates duplicate implementations or steals a held carrier.

### Inputs

- current protected Mastermind INDEX and enrolled procedures;
- current Macro main;
- this packet;
- PR #7461;
- PR #7354;
- PR #7522;
- PR #8090;
- current Research Vault workflow state;
- any live Agent OS/Slack/Executive ownership evidence relevant to those carriers.

### Required actions

1. inspect exact PR heads, dependencies, reviews, requested reviewers, open threads and current-base path changes;
2. identify any explicit HOLD or release authority;
3. identify any EFFECT_UNKNOWN operation associated with a modifying path;
4. map write custody per path;
5. classify each carrier:
   - REUSE;
   - REPAIR_IN_PLACE;
   - REBASE/RECONCILE;
   - SUPERSEDED_WITH_EVIDENCE;
   - INDEPENDENT / DEFER;
6. record DO_NOT_REDO evidence.

### Return

A compact carrier/custody ledger and the first safe implementation packages.

### Stop

Any unresolved concurrent modifying owner on the same path blocks that path.

## 3. S1 — Research Vault private-store isolation

### Suggested route

Bounded security/backend engineer, independently reviewed by a security/adversarial reviewer. Fable adjudicates architecture, not line edits.

### Source

- engine/research_vault/r2_store.py
- tests/test_research_vault.py and relevant store tests
- config/r2 delivery-plane classification owner
- DSC-RESEARCH-VAULT-FALLS-BACK-TO-SHARED-PUBLIC-BUCKET.md
- PR #6625 as design precedent only

### Mission

Make the Research Vault's private R2 production path structurally incapable of silently binding to the shared/public delivery plane.

### Non-goals

- no bucket migration;
- no credential rotation;
- no rewrite of all R2 clients;
- no merge of Radar #6625;
- no new secret store;
- no customer product change.

### Acceptance

- explicit research-private config required for production R2;
- partial config refuses;
- known shared/public destination refuses;
- no fallback writes;
- local explicit test store remains;
- existing strict conditional Research Intelligence store can still operate through the canonical private store;
- relevant tests prove no secret leakage.

### Independent review questions

- Can a combination of missing env vars still construct a shared client?
- Can a caller select a bucket?
- Does a read path accidentally widen even if writes are fixed?
- Are local/test behaviors explicit rather than inferred from unsafe env fallback?

## 4. V1 — live Vault integrity census

### Suggested route

Bounded data/backend investigator. No writes to production state.

### Mission

Measure the real current relationship among admitted documents, stored PDFs, corpus rows and processed receipts.

### Required output

At minimum:

- catalog count/hash/time;
- PDF object count;
- corpus row count;
- receipt count;
- set-difference counts and bounded samples;
- body empty/nonempty;
- text_layer states;
- content_sha256 coverage;
- pages/char_count coverage;
- excerpt derivable count;
- current corpus object bytes/hash if available;
- current local restore bytes/hash;
- whether the 1,497 -> 351 anomaly reproduces.

### Required classifications

No generic “mismatch.” Use typed categories.

### Non-goals

- no automatic repair;
- no object deletion;
- no receipt rewrite;
- no catalog mutation.

### Fable decision after return

Choose which corrections are safe and which need their own carrier.

## 5. U1 — source producer freshness diagnosis

### Suggested route

Bounded operations/data investigator.

### Mission

Find the exact upstream boundary that stopped admitting reports after September 24.

### Questions

- Is the upstream source producing files?
- Is the Research Vault inbox receiving them?
- Are sidecar/PDF pairs present but already receipted?
- Are upstream credentials/collector sessions dead?
- Is MarketDesk intentionally down?
- Is a scheduler/run disabled?
- Is the source writing another bucket/prefix?
- Is the source publishing malformed timestamps that sort incorrectly?

### Evidence

Use source-owner logs/artifacts and R2/listing facts; do not guess from catalog age alone.

### Acceptance

One falsifiable root cause and either:

- restored producer admission; or
- explicit current outage owner/state with downstream health reporting kept red/degraded.

## 6. R1 — corpus restore/excerpt-collapse root cause

### Suggested route

Hard-debugging engineer, independent reviewer.

### Mission

Explain the 1,497 -> 351 derivation event and prove current restore correctness.

### Inputs

- V1 census;
- engine/research_vault/excerpt.py;
- engine/research_vault/ingest.py restore/publish path;
- corpus object/current local copy;
- retained workflow logs if needed.

### Required experiment

Compare:

- catalog IDs;
- corpus IDs;
- body/text-layer state;
- derive(body) success;
- object hash/size across source and restored copy.

### Acceptance

The exact cause is established and the next hourly/manual non-destructive run no longer produces an unexplained collapse.

### Stop

If repairing the canonical corpus would overwrite or republish uncertain state, stop and move correction to a separately reviewed write carrier.

## 7. T1 — full-text economics measurement

### Suggested route

Data engineer/data scientist.

### Mission

Measure the actual cost of replacing prefix-only retrieval with full-document retrieval.

### Required outputs

Distribution table:

- PDF bytes;
- extracted full-text bytes;
- pages;
- current stored body chars;
- truncation rate;
- full-text compression;
- projected full FTS bytes.

Operational measurements:

- current corpus bytes;
- restore/download duration;
- SQLite open time;
- representative FTS warm latency;
- representative cold latency;
- local disk/memory.

### Decision table

Compare:

A. one full SQLite FTS;  
B. R2 canonical + persistent API-host synchronized index;  
C. physical shards behind one service.

Do not select by architectural fashion. Select the simplest one meeting measured safety/latency/cost bounds.

### Return

A recommendation plus the raw measurements and falsifier.

## 8. P1 — #7461 claim-identity correctness

### Suggested route

Research Intelligence owner/reviewer; bounded implementation if accepted.

### Mission

Adjudicate the structural claim-index bug and land the minimum correct fix through the incumbent owner/carrier.

### Required proof

- a malformed row cannot shift support identity;
- analyzer returns typed invalid output rather than “repairing” an ambiguous model response;
- valid arrays remain valid;
- quote grounding remains exact;
- current-base tests pass;
- compatibility consequences stated.

### Non-goals

- no RIO v2 redesign;
- no mass backfill;
- no new evidence store.

## 9. T2 — canonical text + segment contract

### Suggested route

Backend/data engineer; Fable freezes contract; independent evidence-contract review.

### Mission

Implement the canonical full-text artifact and deterministic research segment representation selected by the W2 architecture.

### Tests

Use fixtures covering:

- ASCII/UTF-8;
- form-feed pages;
- long paragraphs;
- page-crossing claims;
- tables/captions;
- image-only PDF;
- extraction failure;
- corrected source bytes;
- same source bytes rerun;
- segmenter version change;
- very long report.

### Acceptance

- same source + version -> byte-stable text/segment identities;
- changed source -> new identity/stale old derivative;
- a cited span replays exactly;
- page locators are only claimed when derivable;
- address-only state remains explicit for non-replayable visual evidence.

## 10. T3 — full-tail retrieval

### Suggested route

Backend search engineer plus retrieval reviewer.

### Mission

Make a known fact beyond 60,000 characters discoverable through the canonical retrieval service.

### Required benchmark fixture

Include at least:

- a long real-shaped report where a target phrase/economic claim occurs beyond the current prefix;
- a near-duplicate distractor in the head;
- a paraphrastic query;
- institution/date filters.

### Acceptance

- relevant report appears at declared K;
- evidence fetch reaches the tail source span;
- exact receipt replays;
- result discloses full-document vs partial coverage;
- old 60k-only path demonstrably misses the same fact.

## 11. M1 — metadata enrichment

### Suggested route

Data/research lane, not merged into T3 by default.

### Mission

Determine which facets can be added accurately enough to justify product filters.

### Frozen sample design

Stratify by:

- institution size;
- report length;
- single-company vs macro/multi-topic;
- equity vs macro/credit/flow;
- language if non-English examples exist;
- current summary presence.

### Candidate outputs

- canonical security IDs/tickers;
- company entities;
- theme/subtheme IDs;
- topic/desk family.

### Evaluation

For each facet report:

- coverage;
- precision;
- false-positive patterns;
- abstention rate;
- source-vs-derived provenance;
- time-identity correctness.

### Admission

A facet becomes a user/MCP filter only after its owner accepts the benchmark. Until then search remains lexical/metadata-limited.

## 12. P2 — #7354 institutional deep-read producer

### Suggested route

Incumbent Research Intelligence engineer/owner.

### Mission

Recover, reconcile and finish the existing producer rather than building a new one.

### Key preserved semantics

- deterministic top-N cognition head;
- hard report-count bound;
- canonical full source;
- exact-currentness cache;
- W1 -> W2;
- correction requires predecessor;
- EFFECT_UNKNOWN stops batch.

### Integration decision

If T2 canonical text artifacts are available, prefer consuming those exact artifacts over re-running pdftotext per analysis, unless current #7354 proof shows a stronger reason to retain direct PDF extraction.

### Live acceptance

One real report producer-to-store roundtrip and exact rerun with zero new model call.

## 13. P3 — #7522 Brain consumer

### Suggested route

Incumbent Brain/Research Intelligence engineer.

### Mission

Finish the existing source-bound RIO consumer and align it with the canonical read service.

### Required tests

- available;
- missing;
- stale;
- invalid;
- unavailable;
- blank body;
- denied quota/auth;
- evidence query with literal passage;
- evidence absent with RIO present;
- private-field widening;
- one-debit semantics where current product requires it.

### Acceptance

Brain never returns RIO synthesis as literal evidence.

## 14. C1 — canonical Research Read Service

### Why Fable owns contract freeze

This is the interface that prevents future duplication.

### Suggested implementation route

Backend/integration engineer after Fable freezes exact schemas.

### Required operations

- status;
- search;
- fetch;
- find evidence.

### Mandatory invariants

- source admission gate applies universally;
- rights/entitlement come from canonical owner;
- typed degraded states;
- no raw storage locator;
- exact source/currentness identity;
- bounded output;
- RIO projection optional and explicitly derived;
- same semantics usable by Brain and MCP.

### Acceptance

Brain adapter and MCP adapter can call the same underlying service behavior without importing each other's transport/runtime code.

## 15. A1 — Research MCP adapter

### Suggested route

Mastermind MCP/backend engineer.

### Source custody note

The Research domain code belongs in Macro; protected Mastermind owns reusable MCP/auth source patterns. Fable must choose the cross-repo seam deliberately rather than copying packages.

Possible seam options:

1. Mastermind MCP process calls a narrow internal Macro Research Read service.
2. Macro hosts a Research MCP edge while importing/reusing an accepted shared auth package through an approved dependency mechanism.
3. A small protected Mastermind adapter speaks to a source-owned Macro endpoint.

Select the option with least duplication and clearest deployment ownership.

### Tool snapshot

Exactly:

- research_status;
- research_search;
- research_fetch;
- research_find_evidence.

### Required tests

- schemas closed;
- oversize request;
- oversize response;
- unknown tool;
- missing auth;
- wrong resource/scope;
- entitlement denial;
- source stale;
- corpus degraded;
- private error sanitization;
- prohibited input fields;
- tool annotations;
- no write methods.

## 16. A2 — deployment and app enrollment

### Principal-owned decisions

Fable/authorized operator decides the target profile after current platform review.

Do not let a builder silently choose Business vs Pro, private tunnel vs authenticated HTTPS, or internal-seat vs customer-product semantics.

### Separate proof states

- SOURCE_BUILT
- SERVER_DEPLOYED
- ENDPOINT/TUNNEL_REACHABLE
- AUTH_POLICY_ACTIVE
- APP_CREATED
- APP_PUBLISHED if applicable
- APP_CONNECTED
- TOOL_SNAPSHOT_DISCOVERED
- AUTHORIZED_CALL_PROVEN
- DENIED_CALL_PROVEN
- PRODUCT_ACCEPTED

Do not collapse them.

## 17. Q1 — retrieval, rights and security benchmark

### Suggested route

Independent reviewer/data scientist.

### Mission

Try to falsify the product claims.

### Benchmark families

- head vs tail evidence;
- short vs long reports;
- large vs small institutions;
- exact vs paraphrase;
- multi-topic reports;
- source correction;
- scan/no text;
- stale producer;
- degraded corpus;
- current/stale/missing RIO;
- entitlement denial;
- injection-like source text;
- malformed tool args.

### Security attacks

Try to obtain:

- bucket name;
- internal object key;
- credential;
- private source beyond permitted bound;
- another user's entitlement;
- raw error traceback;
- stale/private RIO via evidence endpoint;
- report not admitted by catalog.

### Acceptance

No critical boundary failure; retrieval targets in 04 met.

## 18. X1 — authorized/denied ChatGPT canary

### Principal verification

Use the actual intended ChatGPT surface, not a mock client.

### Authorized task

Prefer a real current/historical institutional question that needs multiple reports and at least one deep/tail source.

Proof must capture:

- app/tool identity;
- source health call;
- search;
- report fetch;
- evidence;
- synthesis;
- provenance;
- response bounds.

### Denied task

Use the intended denied principal/state and prove the typed refusal.

A test client or unit test is not this proof.

## 19. X2 — Deep Research canary

### Mission

Prove the custom app participates in a real Deep Research read/fetch workflow.

Suggested task:

> Reconstruct the earliest discoverable institutional evidence for one recent sector/subtheme leadership move. Compare Vault reports with company releases and public/government evidence, and identify the first source-confirmed change in assumptions.

Acceptance:

- custom Research app used;
- no manual PDF upload;
- source classes separated;
- Vault citations/evidence exact;
- external citations remain external;
- source-health caveat present when applicable.

## 20. L1 — longitudinal institutional belief

### State

Post-MVP unless it independently unblocks another product.

### Start

Reconcile #8090.

### Follow-on packages

- exact two-RIO transition comparator;
- immutable transition artifact;
- query layer: “who changed first / what changed / when”;
- evaluation against known report sequences.

Keep descriptive/context authority.

## 21. Independent review routing

Consequential packages needing independent review:

- S1 private-store security;
- R1 corpus root cause;
- P1 RIO claim identity;
- T2 evidence receipts;
- T3 retrieval correctness;
- C1 service contract;
- A1 MCP/auth;
- Q1 security/retrieval benchmark;
- production canaries.

Reviewers do not merge/release merely by approving.

Preferred review questions are falsifiers, not style critique.

## 22. Repair law

For a returned defect:

1. number the defect;
2. identify exact artifact/source path;
3. name discriminating re-check;
4. send the same owner a bounded repair if effect state is known;
5. after two equivalent attempts with no new evidence, change tactic/route or escalate to Fable.

Never blind-relaunch an uncertain modifying operation.

## 23. Persistence law

At each material milestone preserve:

- source pin;
- carrier/PR;
- confirmed effects;
- DO_NOT_REDO;
- unresolveds;
- current blockers;
- next dependency;
- real-path proof state.

Use GitHub and existing Agent OS owners; do not make this folder a second live task database.

## 24. Fable's principal loop

Repeat:

1. choose highest-value unblocked dependency;
2. decide direct principal judgment vs delegated bounded work;
3. execute/dispatch through current lawful owner;
4. verify return;
5. persist material delta;
6. reassess full mission;
7. start the next safe dependency in the same turn/session while healthy.

Do not stop merely because:

- a PR was opened;
- tests passed;
- one wave finished;
- an MCP server started;
- an app appeared;
- a worker is waiting.

Stop only under the acceptance/real-gate conditions in 04 or at genuine continuity/platform risk with a verified frontier.
