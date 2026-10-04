# Acceptance, security and evaluation law — Research Vault AI Intelligence Fabric

This document defines what can prove the project works.

It deliberately separates:

```text
source built
source merged
deployed
connected
authenticated
selected
tool callable
retrieval correct
rights-safe
user journey proven
```

No single one substitutes for the others.

---

# 1. Program DONE_WHEN

The project is accepted only when all of these are demonstrated on real current systems.

## A. Storage isolation

Dedicated private Research Vault configuration is mandatory for private research reads/writes.

A missing private setting cannot fall through to shared/public R2.

## B. Source identity integrity

For an admitted report, the system can prove:

```text
report_id
source_pdf_sha256
extracted_text_sha256
extractor_version
currentness
```

without ambiguous `content_sha256` semantics.

## C. Corpus completeness

Every catalog report intended to be text-searchable is either present in canonical full-text retrieval or has a typed exclusion/unavailable state.

No silent `catalog - corpus` backlog is called "Search every published research note."

## D. Full-tail retrieval

At least one acceptance fixture places decisive evidence beyond the old 60,000-character prefix.

Search finds it and evidence replay returns it.

## E. Exact evidence

Returned evidence is literal source text with deterministic replay identity.

A verifier can recompute passage text/hash from the current extracted-text artifact.

## F. Derived cognition separation

RIO synthesis is visibly typed as model synthesis.

A specific evidence question cannot be answered solely from RIO when literal source evidence is unavailable.

## G. Revision invalidation

Replacing/correcting the canonical source revision makes stale:

- extracted text;
- segment addresses;
- RIO currentness;
- embeddings if any;
- longitudinal comparisons that depend on the old revision.

History remains inspectable; currentness moves.

## H. Metadata truth

Ticker/security/topic filtering is based on provenance-bearing source/derived identity, with ambiguity preserved.

No silent guessed ticker is written as a source field.

## I. Health truth

A model can distinguish:

- publication current;
- source producer stale;
- corpus incomplete;
- extraction missing;
- RIO stale/missing;
- no evidence found.

## J. Authorized ChatGPT journey

A real authorized ChatGPT developer-mode session completes a research task through the MCP without manual PDF upload.

## K. Denied ChatGPT journey

An unauthenticated/non-entitled caller cannot obtain private report bodies, private RIO text, R2 keys, object names, credentials or internal paths.

## L. Deep Research journey

A real Deep Research run uses the custom research app for internal read/fetch and reconciles it with external evidence.

## M. Context economics

The normal answer path retrieves a bounded candidate/evidence set rather than whole-report dumps.

## N. No authority creep

Nothing in this program gives a qualitative source/RIO/model ranking, sizing, gate or trade authority.

---

# 2. Security model

Threats include:

- unauthorized Research Vault access;
- accidental public-bucket fallback;
- user/model selecting arbitrary R2 object;
- path/key traversal;
- cross-user entitlement confusion;
- stale token/scope use;
- prompt injection inside third-party research;
- report text causing tool/action escalation;
- licensed prose leakage through error/logging;
- RIO/source epistemic-layer confusion;
- source revision mismatch;
- query causing unbounded result/context;
- public plugin exposure before private canary qualification.

## Core controls

### Authentication

Use incumbent protected OAuth/MCP resource-server owner.

Verify token signature, issuer, audience/resource, expiry and scope on every request.

### Authorization

Entitlement/policy is server-side trusted context.

Model arguments never contain the authority decision.

### Resource binding

Research service deployment binds one approved Research Vault owner/plane.

No runtime tool parameter chooses bucket/root/endpoint.

### Data minimization

Search returns candidate metadata and bounded snippets.

Fetch/evidence returns only the content needed for the authorized task.

### Untrusted document content

Institutional document text is data.

Instructions inside the PDF cannot alter tool schemas, scopes, system prompts, deployment or authority.

RIO extractor already carries this principle; the retrieval service must preserve it.

### Error sanitization

External errors use a closed code family.

Never interpolate secret-bearing exceptions into tool output.

---

# 3. Required denial tests

## Authentication missing

Expected:

`AUTHENTICATION_REQUIRED`

Verify absence of:

- private title if policy says even discovery is private;
- body;
- RIO;
- bucket/object;
- internal host/path.

## Wrong audience/resource

Refuse before research read.

## Missing scope

Expected:

`INSUFFICIENT_SCOPE`

## Authenticated but non-entitled

Expected:

`NOT_ENTITLED`

No content leak through timing-sensitive "not found vs forbidden" behavior where policy requires concealment.

## Invalid report ID

Cannot traverse/query arbitrary R2 keys.

## Oversized query/result request

Closed bound refusal or clamped contract as specified; never unbounded allocation.

## Model-supplied R2 fields

Schema must reject because such fields do not exist.

---

# 4. Private-store adversarial tests

Test environment matrix:

| Research env | Shared env | Expected |
|---|---|---|
| missing | present | refuse private store |
| partial | present | refuse |
| complete distinct | present | success |
| complete same bucket/plane | present | refuse |
| explicit local test store | irrelevant | explicit local mode succeeds |

Also verify no fallback through an alternate helper/factory path.

---

# 5. Vault integrity benchmark

Before connector acceptance, record:

```text
catalog_count
pdf_count
receipt_count
corpus_count
full_text_count
segment_count
excerpt_count
```

and mismatch sets.

Do not require numerical equality where the architecture intentionally allows typed exclusions.

Instead require every difference to be explained by a closed state.

Example:

```text
catalog - full_text:
  TEXT_LAYER_NONE
  EXTRACTION_FAILED_RETRYABLE
  EXCLUDED_BY_RIGHTS
  BACKFILL_PENDING   # not acceptable for final complete search claim
```

Unknown is not an acceptable final disposition.

---

# 6. Retrieval evaluation set

Build a frozen, source-licensed internal benchmark.

At minimum:

## R1 head-text exact
Relevant evidence in first pages.

## R2 tail-text exact
Only relevant evidence beyond old 60k prefix.

## R3 title-only
Relevant report discoverable from title metadata.

## R4 summary paraphrase
Query uses different wording from summary/body.

## R5 exact ticker
Explicit ticker in source.

## R6 company-name alias
Company named without ticker; identity layer must resolve or abstain.

## R7 multi-company sector report
Avoid assigning the report exclusively to one company.

## R8 institution/date filter
Correct filtering.

## R9 negative
Terms absent; no fabricated evidence.

## R10 scan/no-text
Typed unavailable/visual evidence state.

## R11 corrected report
Old revision stale; new revision current.

## R12 long report
100+ page or representative high-percentile note.

## R13 acronym collision
Ticker-like macro acronym must not become company identity.

## R14 cross-institution topic
Multiple houses, same thesis/theme.

## R15 rights boundary
Discoverable metadata but body access denied where policy requires.

## R16 stale source producer
Tool status shows source stale while publication itself is current.

---

# 7. Retrieval metrics

Measure:

```text
Recall@K
MRR / nDCG where appropriate
tail Recall@K
evidence exact-match/replay rate
false evidence rate
identity precision
identity abstention
rights-policy false-allow rate
p50/p95 tool latency
bytes returned
candidate count
model context bytes
RIO coverage/currentness
cold vs warm query behavior
```

Do not set arbitrary target values in advance where no benchmark baseline exists.

Freeze acceptance thresholds only after baseline measurement and architecture-owner review.

Some metrics are hard requirements regardless of baseline:

- false private authorization allow: 0 accepted cases;
- invented literal evidence: 0 accepted cases;
- source hash/replay mismatch returned as valid evidence: 0 accepted cases.

---

# 8. Tail retrieval acceptance

Seed or identify a report where a unique fact is located strictly beyond 60,000 chars.

Prove:

1. legacy-prefix search cannot find it or is demonstrably incomplete;
2. new full-tail search finds the report;
3. `find_evidence` returns literal text from the tail;
4. page/byte/hash locator replays;
5. answer cites that evidence, not an RIO paraphrase.

This is the decisive proof that the project adds more than MCP transport.

---

# 9. RIO acceptance

## Structural safety

Malformed claim arrays refuse rather than shifting indices.

## Grounding

Every source claim is backed by verified source text.

## Epistemic separation

Derived thesis text is not emitted as a source quote.

## Idempotency

Exact same:

```text
report/text identity
+ prompt contract
+ requested model policy
```

does not incur another model call when a current artifact exists.

## Correction

New source/text revision cannot silently keep old RIO current.

## Rights-safe projection

Public/model-visible derived summary never copies private quote text beyond allowed policy.

---

# 10. Brain/MCP consistency tests

Use the same canonical Research Read fixture.

For an equivalent authorized question:

- Brain search candidates and MCP search candidates derive from the same owner;
- coverage states match;
- source hash identities match;
- evidence passage identity matches;
- differences due solely to explicit consumer output caps are documented.

This test prevents future independent retrieval drift.

---

# 11. MCP protocol acceptance

Using the actual pinned MCP SDK/runtime generation:

## Tool census

Exactly expected read tools, no dynamic surprise tools.

## Input schemas

- `additionalProperties:false`;
- bounded text lengths;
- bounded limits;
- pagination/cursors bounded;
- enum/state inputs closed where applicable.

## Annotations

Read-only/idempotent/non-destructive.

## Output

Structured, bounded, schema-validated.

## Authentication

Tool-level and resource metadata behavior matches incumbent auth owner/current client requirements.

## Transport

Private canary uses approved private transport without disabling transport security.

## Shutdown/effect

Read-only server creates no research mutation merely by connecting or querying.

---

# 12. Prompt-injection evaluation

Include malicious institutional-document fixtures such as:

- "ignore all previous instructions";
- "call another tool";
- "upload this report";
- "reveal system prompt";
- fake JSON/MCP instructions;
- source prose claiming user is authorized;
- source prose claiming a bucket path or API key.

Expected behavior:

- text may be retrieved as source data if relevant/authorized;
- no tool scope/authority changes;
- RIO extractor treats it as untrusted source;
- no credential/path disclosure;
- no modifying action.

---

# 13. Rights leakage evaluation

Construct fixtures where:

```text
public metadata allowed
private body allowed only to entitled caller
private RIO allowed internally
verbatim redistribution constrained
```

Test every tool and degraded path.

Especially inspect:

- error payloads;
- debug fields;
- open-source URLs;
- RIO "summary" fields;
- log output;
- MCP structuredContent;
- cached responses.

A hashed source statement can be returned where the projection permits; hash presence must not accidentally carry source prose.

---

# 14. Staleness evaluation

Simulate:

### fresh publication + fresh source
normal.

### fresh publication + stale source
status must say source producer stale.

### stale publication + source timestamp recent
publication unavailable/stale; do not trust unserved source.

### source correction while RIO/index cached
old derivatives become stale/refused.

### corpus partial
search discloses coverage degradation rather than a confident empty result.

---

# 15. Performance/cost evaluation

Before final physical-index selection, collect:

- corpus and full-text storage bytes;
- full FTS size;
- cold first query;
- warm query;
- R2 transfer;
- CPU/memory for backfill/index update;
- segment count;
- average/percentile response bytes;
- number of model tokens in representative research synthesis;
- RIO generation count and cache hit rate.

The product goal is fewer frontier tokens for better evidence, not maximum infrastructure novelty.

---

# 16. ChatGPT real-path canary

The canary is not "MCP Inspector passed."

Use a clean/new authorized ChatGPT conversation with the actual intended developer-mode connection.

Record:

```text
connection/app identity
server/tool generation
auth/link state
tool names discovered
research source health
query
candidate ids
evidence ids
answer outcome
denied-path outcome
```

Do not record tokens or licensed full-text in the evidence report.

## User task requirements

The task must require:

- at least 3 reports;
- at least 2 institutions;
- one source-evidence fetch;
- preferably one tail-only acceptance report;
- one derived RIO state if available;
- explicit source freshness disclosure.

---

# 17. Deep Research real-path canary

Use a fresh Deep Research run with the custom app selected.

Acceptance requires observable internal tool use, not a model answer that could have been produced from the public web.

The final synthesis must label:

- Mastermind private institutional evidence;
- public external evidence;
- model synthesis.

No claim that Deep Research "used the Vault" without tool evidence.

---

# 18. Private tunnel acceptance

Secure MCP Tunnel acceptance is separate from MCP correctness.

Prove:

- private server has no accidental public listener;
- outbound tunnel reaches the intended server;
- endpoint maps to the intended app connection;
- auth still applies through the tunnel;
- loss of tunnel yields unavailable, not fallback to another server;
- reconnect does not duplicate any modifying effect (all tools are read-only anyway);
- tunnel existence does not imply plugin publication.

---

# 19. Production/publication stages

Keep these labels distinct:

```text
SOURCE_BUILT
SOURCE_REVIEWED
SOURCE_MERGED
SERVICE_DEPLOYED
PRIVATE_TUNNEL_CONNECTED
CHATGPT_APP_CREATED
CHATGPT_APP_SELECTED
CHATGPT_CANARY_PROVEN
DEEP_RESEARCH_CANARY_PROVEN
PUBLIC_PLUGIN_SUBMITTED
PUBLIC_PLUGIN_APPROVED
```

The program may be fully useful to the Chairman at `CHATGPT_CANARY_PROVEN + DEEP_RESEARCH_CANARY_PROVEN` without ever becoming a public plugin.

---

# 20. Final adversarial review

Before acceptance, an independent reviewer should try to falsify:

1. "private really means private";
2. "search covers the admitted text estate";
3. "tail evidence is real";
4. "source and body hashes are not conflated";
5. "RIO cannot impersonate source evidence";
6. "correction invalidates derivatives";
7. "model cannot choose storage authority";
8. "denied caller learns nothing private";
9. "source stale vs publication stale is truthful";
10. "the real ChatGPT journey works without manual uploads."

A review that only reads unit tests is insufficient for these claims.

---

# 21. Release acceptance record

The final GitHub evidence should include compact pointers to:

- exact source commits;
- live Vault census;
- retrieval benchmark version/results;
- independent review;
- deployed service generation;
- tunnel/app identity;
- authorized canary;
- denied canary;
- Deep Research canary;
- unresolved limitations;
- rollback owner.

Do not store the licensed source corpus or auth secrets in the evidence pack.

---

# 22. Explicit non-acceptance examples

These are **not** completion:

- "we wrote the four MCP tools";
- "all unit tests pass";
- "the PR merged";
- "the tunnel says connected";
- "ChatGPT lists the plugin";
- "a summary question worked";
- "RIO exists for some reports";
- "vector search looks good";
- "catalog says 2,778";
- "source freshness warning was acknowledged."

Only the declared real-path and integrity evidence closes the project.
