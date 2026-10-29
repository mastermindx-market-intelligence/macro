# Research Vault — Chunk 22: converge on the existing Research Intelligence organism

**18 September 2026. Parent institutional-intelligence upgrade remains SPEC_ONLY / unaccepted. This chunk is an architecture + capacity decision, not a new semantic store, source collector, model run, subscription order, or production release.**

## Executive ruling

Do **not** build the parallel claim graph / research memory plane contemplated in early #7182 drafts.

The canonical semantic path is now:

```
Research Vault source/body
  -> W1 Research Intelligence Object (RIO) [merged #7101]
  -> W2 immutable/versioned private Research Intelligence artifact [#7230]
  -> W3 existing Brain/Research Vault consumer [planned on the existing #7079 path]
  -> existing Prophet/company/private-portfolio/editorial consumers under their own gates
```

Any future institutional-expectation, revision, source-independence, company-association, or longitudinal-belief capability must extend/project this organism and existing identity/source owners. No second RAG truth store, graph authority, source archive, permission plane, queue, chatbot, correction plane, or lifecycle.

This does not mean RIO v1 is sufficient for every desired user job. It means missing semantics are additive requirements on the existing organism, not justification for another one.

## Current source pins

- protected procedure: Mastermind@61a2ff79aba4e8a5685e779707ad5c4426cf5cc5 / Skillpack 1.0.1 / bootstrap 1.
- Macro catalog measurement pin: main@8d614027688c8f37e36800c42b545af213251e54.
- current catalog blob: b6900293dc9281124d3018d2fc5eda52873dc04a, generated 2026-09-18T10:37:44.200123+00:00.
- R7 catalog baseline blob: 54ed63983248afad543ff46ed327a076d67475b4, generated 2026-09-16T06:09:42.758496+00:00.
- W1 merged PR #7101; merge 0859610dd27e032eba3a34f515cf239110aa35f8.
- W2 current PR #7230 head fc4c12a1ca073c2ecf6f5e0cc75429259d84ade2 at this investigation.
- source-bound Brain reader #7079 head 8271ae320732997be4553957e3e2773d1b9e9f1b.
- shared release prerequisite #7287 head db088894ba2b77a028981630f9b1165f23fa79ce.

## 1. Current acquisition is genuinely capacity-bound

Complete-catalog identity diff, R7 -> current:

| Measure | Result |
|---|---:|
| old rows | 2,208 |
| current rows | 2,354 |
| IDs added | **146** |
| IDs removed | **0** |
| net growth | **146** |
| added reports published after the R7 snapshot | **117** |
| older/backfill additions | **29** |
| elapsed snapshot time | about **52.47 hours** |
| net catalog growth rate | about **66.8 reports/day** |

This is net catalog growth, not a fresh live R2/discovery/download census. However it sits very close to the configured single-account 70-per-24h allowance and is consistent with a saturated account rather than a low-volume feed.

The allocator source itself records a measured 175-day MarketDesk arrival profile of approximately **208 weekday posts/day** and **85 weekend posts/day**, while enforcing the rolling per-account cap.

Nominal raw weekday capacity:

| Total accounts | nominal 24h capacity | capacity / measured weekday posts |
|---:|---:|---:|
| 1 | 70 | 33.7% |
| 2 | 140 | 67.3% |
| 3 | 210 | **101.0%** |
| 4 | 280 | 134.6% |

This is not a promise that three accounts capture every report. Bursts, rolling-window timing, outages, filters, exclusions, login/provider policy, and permitted account pooling still matter. But **three total accounts is now the structural near-full-weekday raw-flow planning target**, not an arbitrary round number. A fourth account is primarily peak-day, backlog, resilience, and faster-backfill headroom.

## 2. Raw source-label counts overstate independent institutional coverage

Current catalog concentration:

- Goldman Sachs raw label: 943.
- S&T raw label: 245.
- J.P. Morgan: 211.
- top 3 raw labels: 1,399 / 2,354 = **59.43%**.
- top 5 raw labels (adding UBS and Other): 1,688 / 2,354 = **71.71%**.

More importantly, **219 of 245 S&T titles (89.39%) explicitly contain GS/Goldman wording**. Among the 146 newly added records, 24 are labelled S&T and **23 of those 24 explicitly identify GS** in the title.

Therefore a raw count of 95 institution labels must never be presented as 95 independent institutional viewpoints. Source type/desk label, publication brand, original analytical origin, and underlying evidence lineage are separate dimensions.

Exact-title collisions across institution labels are comparatively small (15 exact-title cross-label groups / 38 records in the current snapshot), so title equality alone is also not a useful source-origin resolver.

### Acquisition consequence

The second/third account should optimize **marginal evidence**, not raw report count:

1. missing predecessor needed to reconstruct a revision;
2. genuinely independent source/origin;
3. missing current report for a company/portfolio question;
4. dissenting assumption versus already-captured dominant source;
5. event/earnings expectation needed for later actual comparison;
6. underrepresented source/topic exploratory sample;
7. freshness when the same useful evidence currently arrives late;
8. historical backfill only after current useful gaps.

Do not infer source independence from MarketDesk's raw `institution` string.

## 3. Existing metadata corrections prove why versioned semantic artifacts matter

Between the two catalog snapshots:

- **2,196 existing IDs changed `summary_points`**;
- **19 existing IDs changed institution labels**;
- no IDs were removed.

The summary changes are mostly normalization/repair (for example markdown emphasis removal and previously split phrases being rejoined). Institution changes include canonicalization such as `Commbank -> CommBank`.

This is evidence that catalog metadata can materially improve while the report identity remains stable. It does **not** prove the underlying PDF/body changed and it does not prove current corpus/RIO state is stale.

### Required distinction

W3's planned freshness test correctly compares W2's analyzed-body hash with the current stored-body hash. That protects semantic content freshness.

But W2 also stores prompt-time document metadata (institution, desk, title, published_at). A body-hash match alone does not establish that those metadata fields still equal the current catalog.

Initial W3 safe-summary use is low-risk because the rights-safe projection does not expose private claim text or its stored institution label, and the Brain can continue displaying current catalog metadata. Still, the producer/reader contract must distinguish:

- **content freshness** — analyzed body hash matches current stored body;
- **catalog identity freshness** — prompt-time identity fields remain compatible with current catalog;
- **PDF/source binding** — #7079 source-PDF fingerprint separately matches its current source;
- **historical availability** — none of the above establishes when the information was known in the past.

Do not collapse these hashes/clocks into one `fresh` boolean.

## 4. W1/RIO already owns most of the semantic extraction we were planning

Merged W1 / `mastermind.research_intelligence.v1` already includes:

### Source claims
- exact extractive statement;
- grounded quote evidence;
- numbers;
- entities;
- horizon;
- explicit/implicit flag.

### Analysis
- thesis summary, direction, mechanism, conviction;
- assumptions;
- forecasts;
- catalysts;
- falsifiers;
- counterarguments;
- implications;
- belief delta;
- consensus relation;
- uncertainties.

Every analysis row points to grounded claim indices. Claim text must survive exact qualitative citation verification. Authority is forced to `descriptive_research_only`.

The rights-safe projection already avoids copying private claim/quote text, exposes hashes/lineage, and marks extracted entity mentions as unresolved quote mentions.

### What remains genuinely missing

Do not answer these gaps by building a parallel graph:

1. **Canonical entity resolution** — issuer/security/listing/segment mapping remains unresolved; use Data OS identity owners.
2. **Comparable numerical dimensions** — metric definition, unit/currency, scope/segment, target period, scenario, accounting basis, point/range representation.
3. **Deterministic revision relation** — same-source comparable prior/current claim, explicit reaffirmation, correction, repeated revision.
4. **Source-origin/independence lineage** — publication brand versus desk versus original analyst/evidence source.
5. **Complete temporal clocks** — source-authored, provider-posted, first observed, source-byte acquired, derived, first product-available.
6. **Rights/audience disposition** — source-use and audience remain external existing-owner decisions.
7. **Evidence locator binding** — RIO quote text and #7079 source-bound passage/page semantics must stay related but distinct.
8. **Complete-long-report input** — RIO can only analyze the exact body W1 receives; a truncated corpus prefix cannot become complete research intelligence merely because its RIO is grounded.

A later institutional-expectation projection, if justified by real tasks, belongs under the existing Research Intelligence owner and should be derived from grounded claims + deterministic transforms. It is not a second source of truth.

## 5. W2 already owns versioning/corrections; do not recreate them

#7230 provides content-addressed immutable artifacts plus one existing-store compare-and-swap `latest` pointer.

Its contract already covers:

- exact source-body identity;
- frozen extraction prompt/model provenance;
- idempotent replay;
- explicit predecessor for corrections;
- historical immutable versions;
- exact readback;
- stale/conflicting predecessor;
- effect-unknown reconciliation;
- rights-safe versus private reader projections.

Therefore #7182's early proposals for a new correction database, graph version store, or latest-pointer service are superseded.

## 6. W3 is already the correct Brain integration

The incumbent #7079 continuation contract defines W3 after #7230 + #7079 release:

- same Brain -> Research Vault report path;
- join by current Research Vault report ID;
- W2 source hash compared to current stored body hash, never PDF hash;
- RIO lookup only after existing identity/catalog/quota gates;
- no second corpus read;
- generic mode may expose only W2 rights-safe summary projection;
- evidence-question mode exposes RIO state only and must still use literal source-bound evidence;
- bounded available/missing/stale/invalid/unavailable states;
- no new store/cache/index/identity/entitlement/retry plane.

That should remain the integration direction.

## 7. Missing operational capability: no continuous W1 -> W2 producer exists

Current code search found `analyze_document` / `analyze_vault_report` only inside the Research Intelligence implementation and tests. The W2 operator CLI accepts an **already successful W1 analysis** and exact source body; it does not itself produce W1 analysis.

So even after W2 and W3 release, the system can legitimately report `missing` for most reports unless an operational producer exists.

### Proposed operational producer seam — design only; NOT W4

The frozen Qualitative Research architecture already reserves **W4 for the ZeroHedge qualitative adapter, W5 for longitudinal belief memory, and W6 for cross-document synthesis**. Do not reuse those wave identities. Add one bounded operational producer seam under the existing Research Vault / Research Intelligence runtime owner:

```
eligible current Vault report
 -> compare current body + catalog identity to latest RIO receipt
 -> if missing/stale and admitted: run W1 once
 -> W2 validate + persist
 -> W3 consumes later
```

No new queue/store. Reuse the existing scheduler/process owner and existing W2 idempotency/CAS semantics.

Start **selective**, not full-corpus:

Priority analysis candidates:
1. reports already selected for Prophet/company/user questions;
2. watchlist/private-portfolio relevant reports, composed without writing private holdings into shared state;
3. earnings/guidance/revision/initiation/catalyst notes;
4. macro/policy reports relevant to current regime/release questions;
5. independent/dissenting origins underrepresented in the current corpus;
6. missing predecessors required for a revision pair;
7. editorial/news tasks with an actual approved output need.

Once cost/quality are measured, expand to full captured flow if warranted.

## 8. Compute is unlikely to be the main cost bottleneck

Current Macro config assigns the generic extraction lane to **Claude Haiku 4.5**. W1 accepts an explicit model ID; the operating owner still must freeze the admitted model/route.

Current official Anthropic list pricing for Haiku 4.5 is $1/M input and $5/M output tokens standard, or $0.50/M and $2.50/M in batch processing, subject to actual route/eligibility.

Current catalog page distribution:
- 2,249 reports with page counts;
- mean 12.49 pages overall;
- recent Sep reports mean **12.94** pages;
- median 9;
- recent p90 25;
- recent p95 34.

Illustrative full-flow model, **not measured token usage**:

Assume:
- 200 reports/day;
- 12.94 pages/report;
- 500–800 input tokens/page;
- 2,000 output tokens/report;
- 30 days.

Then monthly input is about **38.8–62.1M tokens**, output about **12M tokens**.

At the official standard Haiku rate this is roughly **$99–122/month**. If an eligible batch route preserves required quality/latency, roughly **$49–61/month**. At 3,000 output tokens/report, standard cost would be roughly **$129–152/month**.

Actual source lengths, prompts, retries, provider fallback, visual/table processing, failed parses and user-time reads can move this materially. Measure real token receipts before budgeting.

### Capital implication

At the previously established public Professional planning price of about $150/account/month, the **access cost is likely larger than the first-pass extraction compute cost**.

This changes the earlier compute-vs-subscription tradeoff: once the pipeline is useful, raw institutional access becomes the scarcer marginal input. Spending $150 on another source allowance can be rational even when compute is still precious, because the acquired evidence can be analyzed for roughly cents per report on the intended extraction tier.

## 9. Purchase sequence

**Do not buy three/four total accounts immediately.**

### Stage A — use what is already paid for
Release/qualify:
1. #7287 shared baseline repair;
2. #7079 same-head fresh current-base proof/release;
3. #7230 W2 release;
4. existing W3 Brain consumer;
5. one bounded W1→W2 operational producer seam (unnumbered; not frozen W4);
6. one permitted real company question -> useful answer -> original inspection.

### Stage B — second account monthly pilot
Only after vendor/source-use terms allow the intended collection/processing.

The second total account raises nominal raw capacity from 70 -> 140/day. Freeze the evaluation questions before the incremental source is selected and measure:
- previously unacquired evidence now captured;
- newly answerable supported tasks;
- independent-origin gain;
- revision-history continuity;
- timeliness;
- processing cost;
- useful customer outcome when real usage is available.

### Stage C — third total account
If account two remains capacity-bound and meaningful eligible gaps remain, three total accounts are the structural near-full raw weekday target: 210/day versus the allocator's measured ~208/day weekday arrival rate.

### Stage D — fourth account
Not the default target. Require evidence that peak bursts, backlog, resilience, or historical continuity create enough extra value beyond three accounts to justify 280/day nominal capacity.

No purchase or vendor message was performed in this chunk.

## 10. Release frontier remains external to this records-only decision

At the current checkpoint:
- #7287 is the shared repair prerequisite for #7079 and remains under its own CI/release owner.
- #7079 remains BUILT_NOT_PROVEN and must not absorb the #7287 fix.
- #7230 W2 actual head is fc4c12a... and remains under its own current exact-head CI/release owner.
- R20 ordered analytics remains separate and does not prove product usefulness.
- source-use/pooling/retention remains unresolved.

Do not poll or rerun unchanged external release gates as a substitute for work. Consume material returns when they occur.

## Exact continuation

After the incumbent release gates move, consume them in dependency order and commission/adopt W3 under the existing Brain/Vault owner.

Independent now: freeze the unnumbered W1→W2 producer contract against W1/W2 and the frozen Qualitative Research architecture, and prepare a small real-task corpus that contains (a) one current company question, (b) one revision pair, (c) one independent-source disagreement, and (d) one long-report qualification. Do not implement a second semantic plane.

The parent mission remains MORE_WORK_EXISTS / unaccepted.


## 11. Operational producer contract frozen

Detailed design: `R22_W1_W2_OPERATIONAL_PRODUCER_CONTRACT.md`.
Machine shape: `r22/producer_contract_r22.json`.
Gold cases: `r22/gold_corpus_r22.json`.
Wave ownership: `r22/gold_stage_matrix_r22.json`.
Account evaluation: `r22/account_pilot_scorecard_r22.json`.

The recommended first producer is **not** a new frozen wave. It is an unnumbered operational seam between W1 and W2.

Selected shape:
- explicit permitted report IDs first;
- exact existing stored corpus body as the W1 source;
- no PDF re-download or independent extraction;
- no source-ingest mutation;
- no new model router/cost ledger/store/queue;
- W1's existing provider waterfall + usage ledger;
- W2's exact predecessor/correction/effect semantics;
- current unchanged W2 state -> zero model call;
- summary_points/tags/tickers/top_pick-only changes -> zero model call;
- body or W1 prompt identity change -> reanalysis/correction;
- source-use denial -> zero model call.

### Long-report coverage law

The producer must not pretend the 60,000-character corpus body is the entire report.

Vault ingest already measures full-extraction `char_count` before truncation. The existing corpus row owns that fact; the current `get_document` projection does not expose it.

The future accepted integration should expose the minimal measured facts needed to distinguish:
- complete stored body;
- prefix-only body;
- unknown coverage;
- no text layer;
- extraction unavailable.

Do not put a second extraction store in the producer. Under the current W3 hash contract, W1 must analyze the exact stored body. A separate accepted Vault extension is needed before complete-tail RIOs can use a different canonical analyzed-body identity.

### Gold cases are stage-scoped

The four frozen cases deliberately span several waves:
- G1 producer extracts each issuer disclosure faithfully; later comparison adjudicates the definition change.
- G2 producer extracts each ING forecast faithfully; frozen W5 owns revision/repetition across documents.
- G3 producer extracts each Amundi/ING view; frozen W6 owns independent-source disagreement synthesis.
- G4 current producer/consumer must report prefix-only/partial when late qualifications are outside the stored body; full-tail support is a Vault follow-up.

A producer implementation that invents cross-document memory to make G2/G3 pass is a failure of scope.

## 12. Current price and cost sensitivity

The current public ZeroHedge signup page observed 2026-09-18 lists Professional at **$150 monthly** or **$125/month billed annually ($1,500/year)** and explicitly includes the research catalog. This is an advertised consumer price, not a bulk/pooled/commercial-processing quote.

Subscription-only nominal totals:

| accounts | month-to-month | annual billed upfront | incremental monthly vs one |
|---:|---:|---:|---:|
| 1 | $150 | $1,500 | — |
| 2 | $300 | $3,000 | $150 |
| 3 | $450 | $4,500 | $300 |
| 4 | $600 | $6,000 | $450 |

At the Chairman's current $75/customer/month planning price:
- one additional $150 account equals two customers of gross monthly revenue;
- at an illustrative 70% contribution margin it is about 2.86, i.e. three customers' contribution;
- moving from one to three accounts adds $300/month: four customers gross, about six at that illustrative margin.

These are sensitivity calculations, not measured margins, CAC, churn, source-processing cost, or a recommendation to annual-prepay before rights/usefulness are proven.

Current Anthropic public list pricing confirms Haiku 4.5 at $1/M input and $5/M output standard, with $0.50/M and $2.50/M batch pricing. The R22 token-volume model remains explicitly illustrative. The account pilot must replace it with the existing ai_costs ledger's actual usage.

## 13. Recommendation at this point

There is now enough evidence to say **the expanded institutional feed is strategically worth building toward**.

The reason is not document resale. The existing architecture can turn a report into grounded claims, assumptions, forecasts, counterarguments and versioned derived intelligence, then later into longitudinal/source-disagreement memory under the already frozen W5/W6 program.

There is also enough evidence **not** to buy all remaining capacity immediately:
- the current source-use/pooling grant is unresolved;
- W2/W3 are not released;
- there is no operational W1->W2 producer;
- full-tail coverage is incomplete;
- independent-source lineage is not yet reliable;
- no real customer usefulness/ROI has been measured.

The capital sequence is therefore asymmetric:
1. finish the current organism;
2. prove one real permitted answer;
3. add account #2 monthly and measure it;
4. if useful gaps remain, account #3 is the structural full-weekday target;
5. account #4 must prove peak/backfill/resilience value of its own.

This preserves the user's AI-compute budget while recognizing that, once a cheap grounded extraction path works, **licensed/source access rather than first-pass model tokens is likely the scarcer marginal input**.
