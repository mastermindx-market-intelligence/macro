# Research Vault — R22 Operational W1→W2 Producer Contract

**Status: DESIGN_ONLY / NOT IMPLEMENTED.** This is the missing operational seam between merged W1 and pending W2. It does not create a new Qualitative Research wave. Frozen W4/W5/W6 remain ZeroHedge adapter / longitudinal belief memory / cross-document synthesis.

## User/machine outcome

A permitted Research Vault report should be able to acquire one current, quote-grounded Research Intelligence Object without an operator manually manufacturing a W1 JSON file.

The producer must:
1. read one existing Vault report identity and the exact current stored corpus body;
2. disclose whether that body covers the complete extracted text or only the stored prefix;
3. decide whether an existing W2 artifact is current for both body and W1 prompt identity;
4. invoke merged W1 only when an analysis is actually missing/stale;
5. persist only a successful W1 envelope through W2's existing strict CAS/correction semantics;
6. record actual provider/model/token/cost through the existing llm_auth/ai_costs owner;
7. never block or mutate the hourly source-ingest transaction.

This unlocks W3. A schema, queue or scheduled job without a real RIO consumer is not completion.

## Authority and existing owners

Program: existing `qualitative-intelligence` in `config/mastermind_programs.yml`, context-only authority.

Reuse:
- Research Vault: report identity, catalog, source PDF, corpus body, measured extraction facts.
- W1/#7101: RIO schema, prompt, model call, quote grounding, provider provenance.
- W2/#7230: immutable artifact, current-pointer CAS, correction/replay/effect handling, safe/private reader.
- #7079: report evidence reader and source-PDF/source-body binding.
- llm_auth/lib.ai_costs: provider route and actual usage ledger.
- Data OS identity: any issuer/security resolution after extracted mention.
- source-use owner: positive eligibility by audience/purpose.

No new store, model router, cost ledger, candidate queue, entitlement registry, correction plane, graph authority or source archive.

## Three operating approaches considered

### A. Synchronous W1 inside a Brain question
Rejected for the initial product.
- Adds long model latency to a user request.
- Couples customer availability to model/provider availability.
- Repeated questions can create duplicate spend.
- Makes source-text access, quota, model spend and answer allowance harder to reason about in one request.

Brain should consume an already-built RIO and truthfully report `missing`/degraded when absent.

### B. W1 inside hourly `research-ingest.yml`
Rejected.
- The hourly lane is the fail-closed source/corpus publication owner.
- It has a 15-minute budget and is intentionally model-free.
- Provider or model failures must never delay source admission, receipts, corpus/catalog publication or source-freshness alarms.
- Ingest's rollback/idempotency semantics are source semantics, not derived-cognition semantics.

### C. Separate derived producer using existing W1/W2 — **recommended**
Phase 1 is an explicit-ID canary/operator surface. Phase 2 may become a separate bounded scheduled derived consumer only after rights, gold quality and cost are accepted.

It reads source state; it does not write the Research Vault catalog/corpus/PDF. Its only durable write is W2 through the existing strict store.

## Source body contract

### Initial production source = exact current stored corpus body

The producer must analyze the exact `document["body"]` returned by the existing Research Vault corpus reader.

Reason: W3's accepted freshness law compares W2 `source_content_sha256` to the current stored corpus-body hash. Re-extracting the full PDF inside the producer would create a different content identity for long reports and make a valid RIO look stale immediately.

Do not re-download or independently extract the PDF in this producer.

### Coverage is a separate truth

Vault ingest already measures `char_count` against the complete pdftotext extraction before applying the 60,000-character corpus cap.

Proposed additive existing-corpus projection:
- `pages` (measured nullable);
- `char_count` (measured nullable; complete extracted character count).

The current document reader already owns this row and already selects measured `text_layer`. Adding these two measured fields is preferable to a second metadata read/store. Adoption belongs to the existing Vault/Brain owner.

Derived coverage state:

| state | condition | meaning |
|---|---|---|
| `complete_stored_body` | char_count known and char_count <= len(stored body) | W1 saw all extracted text |
| `prefix_only` | char_count known and char_count > len(stored body) | W1 saw only the searchable prefix |
| `coverage_unknown` | char_count unavailable | do not assert whole-report coverage |
| `no_text` | text_layer=none | no machine-readable body found |
| `extraction_unavailable` | text_layer empty/unavailable | our extraction is not qualified/current |

A prefix-only RIO can support claims grounded inside its analyzed prefix. It **cannot** support "the report does not mention X", "these are all the risks", or any answer whose decisive requested evidence may live outside the prefix.

Do not change W1/W2 schemas merely to store this state. W3 can combine current corpus coverage facts with the W2 artifact at read time. If later Vault work safely stores complete extraction sections, that same owner can supersede this boundary.

## Currentness / correction contract

W1 prompt identity contains:
`id, source_type, source_name, institution, desk, title, published_at, content_sha256`.

### Reanalysis required when
- current stored-body SHA-256 differs from W2 source hash;
- W2 artifact is missing/invalid;
- W1 prompt contract/version makes the stored artifact invalid under W2;
- any current W1 prompt identity field differs from the artifact receipt: source name/institution, desk, title or published_at.

A same-body institution/title/date/desk correction therefore gets a new RIO artifact through W2's explicit predecessor path. W2 history preserves the old artifact.

### Reanalysis NOT required solely when
- catalog `summary_points` change;
- tags/tickers/top_pick change;
- browser presentation fields change;
- a rights-safe current catalog spelling changes in a field that is not part of W1 prompt identity.

The R7→R22 catalog diff demonstrates why this matters: 2,196 rows changed summary_points, but only 19 changed institution. The producer must not spend thousands of model calls on display-summary normalization.

### Correction mechanics
- read latest W2 artifact;
- if reanalysis is needed, freeze its exact current artifact SHA-256;
- run W1 against the current stored body and current prompt identity;
- persist with `expected_current_artifact_sha256=<frozen predecessor>`;
- on predecessor mismatch: return conflict for fresh reconciliation, no blind retry;
- on effect unknown: preserve W2 typed effect-unknown state, no second write/carrier.

## Rights/access contract

The producer receives an eligibility decision from the existing source-use owner. It does not infer permission from:
- a Pro subscription;
- presence in the catalog;
- a public URL;
- a report already downloaded;
- a W1/W2 fixture flag;
- a provider/institution name.

Canary inputs should be public/right-cleared controls or institutional originals whose internal-model-processing use has been positively established.

Audience permission remains separate from internal processing permission. W2 private storage does not grant public/subscriber redistribution.

## Model / spend contract

Use W1's existing `analyze_vault_report` and `llm_auth` path.

The operational caller supplies the admitted `model_id`; it never reimplements provider fallback.

Phase 1 candidate model may be the current configured extraction tier `claude-haiku-4-5`, but adoption requires the gold corpus to establish acceptable grounding/recall and actual usage receipts.

W1 already records:
- requested model;
- actually served provider/model;
- prompt identity/hashes;
- token usage through existing `lib.ai_costs` when the provider exposes usage.

No estimate is substituted for actual cost once a real run exists.

## Candidate-selection policy

### Phase 1 — explicit-ID canary
No ranking. Operator/test names exact permitted report IDs. Maximum small batch. This proves semantics without selection bias.

### Phase 2 — all eligible captured flow if cheap-tier gold quality passes
Because current access is already capacity-bound and first-pass extraction cost appears modest, the least biased default is to analyze every eligible text-bearing captured report rather than only popular/bullish/top-pick material.

Use a bounded per-run document cap and resume from W2 state; do not create a new queue.

### Phase 2 fallback — selective only if quality/cost requires stronger models
If the cheap tier fails the gold threshold or real measured cost is materially higher than expected, use deterministic current-demand selection:
- report IDs requested by Brain/Prophet/company workflows;
- earnings/guidance/revision/initiation/catalyst classes;
- current macro/policy questions;
- independent/dissenting source origins;
- missing predecessors;
- approved editorial/research tasks.

Do **not** reuse the Press Research W-score as Research Intelligence truth. Press triage optimizes writeability/relevance/attention/novelty for media production; it is not the semantic importance authority for investor cognition.

Do not select only current Prophet winners or bullish evidence. Counterevidence must remain eligible.

## Proposed operator interface (design, not code)

Extend the existing `scripts/research_intelligence_store.py` rather than minting a second operator CLI.

Candidate shape:

```
python -m scripts.research_intelligence_store analyze-vault \
  --document-id <id> [--document-id <id> ...] \
  --model-id <admitted-id> \
  --max-documents <small-bound> \
  --dry-run
```

After the canary is accepted, the same library path may be called by one existing scheduler-owned derived workflow. Do not schedule model calls inside `research-ingest.yml`.

Possible per-document outcomes:
- `created`
- `unchanged`
- `corrected`
- `skipped_current`
- `skipped_not_eligible`
- `skipped_no_text`
- `prefix_only_created` / equivalent separate coverage field
- `providers_unavailable`
- `call_failed`
- `invalid_model_output`
- `predecessor_conflict`
- `effect_unknown`
- `store_unavailable`

Use existing W1/W2 typed failures where they already exist; do not create synonymous state machines.

Aggregate receipt names counts, report IDs only where permitted, model/provider/token/cost via existing ledger reference, source generations, and coverage-state counts. No private holdings/prompts.

## Four frozen golden tasks

Consume `r22/gold_corpus_r22.json`.

1. G1 Microsoft definition change — tests dimensional/accounting interpretation.
2. G2 ING fixed-target revision/repetition — tests same-source chronology.
3. G3 Amundi vs ING Fed view — tests source independence/disagreement.
4. G4 IEA CC BY4.0 long report — tests late qualification and prefix-only honesty.

The automated producer does not get a pass by merely finding the report.

**Use `r22/gold_stage_matrix_r22.json` to preserve wave boundaries.** The W1→W2 producer is judged on per-document grounding/provenance/coverage, not on cross-document synthesis it does not own:

- G1: each Microsoft source independently preserves the spending/lease definition and numeric claims. The later cross-document like-for-like adjudication is not producer scope.
- G2: each ING source independently preserves fixed-target/rolling-horizon values, quoted prior and rationale. Same-source longitudinal revision/repetition classification is frozen W5 scope.
- G3: each Amundi/ING source independently preserves its policy forecast and rationale. Independent-source disagreement synthesis is frozen W6 scope.
- G4: current producer/consumer must **abstain/degrade honestly** when decisive late evidence lies outside the stored prefix. Complete-tail support is an existing-Vault follow-up, not producer scope.

Later W5/W6/deep-evidence work can make the relational/long-tail cases fully supported without changing their source identities. Never add a graph or cross-document store to the producer merely to make those gold cases green early.

## Implementation acceptance (future PR)

Not complete unless:
1. legacy W1/W2 tests stay green;
2. explicit-ID canary uses existing Vault/W1/W2 only;
3. zero writes to catalog/corpus/PDF/source receipts;
4. missing/denied source-use cannot trigger a model call;
5. current unchanged artifact causes zero model call;
6. summary-only normalization causes zero model call;
7. prompt-identity change causes a correction with exact predecessor;
8. stale predecessor refuses with no blind retry;
9. no-text/unavailable extraction makes zero model call;
10. prefix-only coverage is visible to the consumer;
11. actual provider/model and token/cost receipt survive;
12. source body/prompt/model provenance exactly revalidates through W2;
13. G1–G4 behave according to their **producer-stage** expectations in `gold_stage_matrix_r22.json`; later W5/W6 obligations are not falsely claimed;
14. W3 consumes one produced artifact after its own release gates;
15. actual customer/source/browser proof remains separate from fixture success.

## Do-not-build

No second:
- queue;
- candidate database;
- source text store;
- vector/FTS service;
- correction ledger;
- entity resolver;
- permission mirror;
- cost ledger;
- model router;
- Brain tool;
- graph authority.

## Exact implementation boundary

This design requires explicit Chairman acceptance before code changes under the brainstorming approval gate.

The smallest future implementation should change the existing Research Intelligence operator path plus its current owner tests, and—only if accepted by the Vault owner—the minimal measured corpus projection required for coverage. It must not edit #7079/#7230 carriers directly while they are active.

Until those releases land, design/tests can target their immutable accepted interfaces; production integration waits for canonical release.
