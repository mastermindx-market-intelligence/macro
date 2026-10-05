# Research Vault — source qualification and comparable-change contract

## Status and decision

Chunk 3 advances the institutional-research program from a broad proposal to a manually source-checked control case, a reproducible offline numerical-contract assay, and a precisely bounded implementation frontier. **The overall product remains SPEC_ONLY.** The reference assay is executable; it is not a parser, production service, permission system, or deployed feature.

Current source procedure: protected Mastermind `7642aea155d2817219135b24246b55c1d7611c66`, Skillpack 1.0.1/bootstrap 1. Current implementation inspection: Macro `52380b870218b61865fb56458500cac00ce4932b`. Continue the existing research carrier, PR #7182 / `sol/research-vault-intelligence-design-r2-20260915`, rather than starting a second project or branch. The prior draft head was `a15cebd56092eb0efbde9287ad54acb56d27d555`.

**Decision proposed for implementation:** source-origin qualification is a prerequisite to multi-source convergence claims. The first comparison primitive must distinguish revisions, reaffirmations, representation changes, cross-source differences, reported actuals and different target periods. It must not reduce everything to a sentiment change or a before/after number.

## 1. What was directly established

### Institutional source-origin ambiguity

At the pinned Macro revision, two generated Research Vault pages carry the same NVIDIA-related digest title, August 12, 2026 displayed date, six-page count and repeated displayed report excerpt. Their institution labels differ: `Goldman Sachs` versus `S&T`. Their document identifiers are respectively `marketdesk-glzyuqbhs8f-19abb4` and `marketdesk-mpicbjrjxou-16a699`.

The page blobs are `607c28879edac38387025f019f51f8eefbda0d6d` and `afaca7e930946f98ed640741152aec24dbde2301`. These are HTML blob identities, **not original PDF hashes**. No full-PDF equality, ingestion duplication rate, present live-cluster membership, or global source-count error is claimed.

The inspected `_research_clusters` aggregation in `engine/neuralweb/brain_market_intel.py` forms a set of the `institution` strings of member records to count houses. It does not resolve source origin at that step. The observed pair is a concrete counterexample to treating distinct labels as evidence of independent publication or analysis. The current cluster path's freshness/filtering and catalog inclusion must still be tested with the actual current source data before asserting a live erroneous cluster.

**Required treatment:** preserve both source records; flag likely common origin; resolve using source-owned evidence; and do not add an independent-confirmation claim merely because the labels differ. Do not delete a report on title similarity. Do not map every `S&T` record to Goldman: it is a generic desk label and requires record-specific origin evidence.

The existing #7045 source-type/hygiene owner remains relevant; this chunk does not change its paths. #7079 remained open/draft/unmerged at `a0a47535180dc0a60e176818a78ac7ec2c4c462d` when reread and continues to own source-bound Brain retrieval. No competing repair was started.

### Public numerical control series

I selected Alphabet's management-stated 2025 capital-expenditure sequence because it supplies several semantic cases without needing unverified broker-PDF access. This is explicitly **issuer guidance**, not institutional consensus or a broker forecast series.

| Source event | Target and value | Classification |
|---|---|---|
| February 4, 2025: Q4 2024 earnings call | Full-year 2025, approximately $75 billion | Initial guidance. |
| April 24, 2025: Q1 2025 earnings call | Same target, approximately $75 billion | Explicit reaffirmation. |
| July 23, 2025: Q2 2025 earnings call | Same target, approximately $85 billion | Same-source, same-period revision. |
| October 29, 2025: Q3 2025 earnings call | Same target, $91–93 billion | Revision from a point estimate to a range. |
| February 4, 2026: Q4 2025 earnings call | Full-year 2025 reported CapEx, $91.4 billion | Actual, at the transcript's rounded precision; not a new forecast revision. |
| Same February 2026 call | Full-year 2026 guidance, $175–185 billion | New target year; not another 2025 revision. |

Five source documents yield six manually normalized observations. All public sources were read on the official investor-relations site. The Q3 2025 PDF's **printed page 12 of 23** was visually inspected and matches the stated $91–93 billion range and $85 billion prior estimate. Other locators are descriptive HTML sections; transient read-tool line references are audit navigation, not durable page identities. Full source-byte hashes and historical system-availability timestamps were not captured and stay null.

The arithmetic at the stated precision is: $75→$85 billion, a $10 billion change or approximately 13.3%; $85→$91–93 billion, a $6–8 billion change or approximately 7.1–9.4%. The later reported $91.4 billion falls inside the last stated range. This is not a forecast accuracy score, investment signal, claim about the current outlook, or evidence of institution-wide predictive skill.

**The public control does not substitute for the required original broker-source pair.** It proves that the proposed semantics can be exercised against real statements while the licensed-source admission and runtime-census lanes remain unresolved.

## 2. The executable result—and its limits

The attached stdlib-only research reference consumes manual-normalized examples and adversarial fixtures. It makes no network, credential, LLM, database, workflow, order, or production call.

Tests were written first. The inert-reference run had 38 tests and 35 assertion failures; three non-behavioral invariants already passed. The first implementation passed all 38. Fifteen additional challenges produced a 53-test run with nine failures. Six concerned the new locator precondition; three exposed semantic corrections:

1. An unchanged range must have a zero revision. It is not two independent draws whose difference spans a nonzero interval.
2. Cross-source comparisons on the same date do not require ordering as a same-source revision would.
3. Changing the expression from approximate to exact while retaining identical numeric endpoints is a representation change, not a numerical forecast revision.

After repair, **53 tests passed, zero failed, zero errored, zero skipped**. The `run_assay.py` entrypoint reproduces the cases and emits a timestamped receipt with script/test/fixture hashes. The real-case operational-availability probe rejects all six observations because `available_at` is unknown. That is intentional: the exercise does not manufacture historical knowledge.

The 53 cases are not the earlier proposed 120-task answer-quality benchmark or 26-case production conformance suite. No automated financial extraction, model synthesis, deployed code, viewer, account expansion, real-time replay or customer journey has been evaluated by this pass. A structural hash/locator check using synthetic hashes is not verification of real source bytes.

## 3. Frozen numerical semantics

A comparison key contains existing canonical entity binding; consolidated/segment scope; metric definition; accounting basis; original currency and scale; target-period start/end; and scenario. Production identity must come from existing owners. The human-readable entity label in the control fixture is not a new identity registry.

Different periods, segments, definitions, currencies or accounting bases are not silently normalized into one number. Missing is not zero. Booleans, floats, NaN, reversed ranges and malformed source fields are not accepted as literal evidence. Any supported normalization or conversion must be an explicit versioned transform owned by the relevant existing data system.

| Condition | Required output meaning | Not allowed |
|---|---|---|
| Same source, same comparable target, new numeric value | Revision with supported magnitude and period. | Implied analyst upgrade, conviction change or trade. |
| Explicit same-value reaffirmation | Reaffirmation, zero numeric revision. | New independent estimate or false positive change alert. |
| Equal values without explicit reaffirmation | Unchanged captured value. | Claiming the source reaffirmed. |
| Identical endpoints with changed point/range/precision expression | Representation change. | Claiming a numerical upgrade/downgrade. |
| Distinct origins, comparable metric | Cross-source comparison. | Same-source revision or independent-data claim without provenance. |
| Forecast followed by a comparable reported actual | Realization/expectation-versus-observation comparison. | A new forecast revision or invented forecast accuracy. |
| Same original document, a different source version | Amendment requiring source/extraction-origin classification. | Treating a repair as a fresh economic thesis change. |
| Same claim identity and source version, contradictory values | Conflict requiring investigation. | Quietly choosing the newest row. |
| Same-day distinct records from one origin, date-only timing | Ordering unknown unless separately evidenced. | Inventing an intraday sequence. |

Keep ranges as ranges. No unrequested midpoint. Difference bounds are arithmetic bounds, not a probability distribution. A positive sign in a spending forecast is not a positive stock-return forecast. Preserve source approximation in the output and display sensible precision.

## 4. Source and time qualification before richer graphs

Differentiate four quantities in future presentation: number of acquired records; number of source versions; resolved publication origins; and what is known about independence of underlying evidence. They answer different questions. A resolved publisher identifier alone does not prove independent facts or independent analytical reasoning.

The origin rule is not a global alias dictionary guessed by an LLM. Strong source-owned identity and explicit citation lineage take precedence. Duplicate excerpt/title/date evidence can flag a candidate without authorizing deletion, merged identity, a second independent vote, or a claim of byte equality.

Production claims need a trusted chain from existing document ID and immutable version to source bytes, extracted body version, and the exact supported field. A page number supplied by an extractor is checked against the actual version; unknown pages stay unknown. Where the source changed after an answer was produced, source opening must disclose drift or retrieve the appropriately retained authorized version. Hash-shaped strings alone do not grant source authenticity.

Event publication, acquisition and derived availability remain separate. Selecting the latest current claim uses the source's chronology among eligible records, not whichever old report was downloaded most recently. A request for historical operational context excludes records that were unavailable then and excludes unknown availability. An event date printed on a source is not an acquisition receipt. The control series is retrospective public-source analysis, not operational PIT.

## 5. Correction propagation and actionable reuse

Corrections are dependency-driven. A repaired source/extraction version invalidates calculations that cite it, then derived cards/answers that cite those calculations. A correction to one source must not invalidate unrelated company briefs or silently rewrite earlier historical answers. Use existing source/corpus/caching/publication owners, not a new correction scheduler or state store.

The offline assay exercises transitive dependency closure, unrelated-output isolation and termination when dependency metadata contains a cycle. It does not write, delete, republish, or repair actual outputs.

One source-verified revision can be projected as:

- **Prophet:** an explanatory research change beside an existing name, with the signal artifact unchanged.
- **Mastermind AI:** an exact source-specific before/after answer, with the missing evidence and limits stated.
- **Existing portfolio brief:** a private relevance explanation using current holdings without copying positions into the shared corpus.
- **Existing alert/news owner:** a deduplicated source-bound material-change item, not every arriving document.

These are consumers of one evidence result—not four independent extraction pipelines. Public editorial use is separately rights-gated.

## 6. Smallest build contract and original-source admission

The next production-facing slice should **not** begin with full-corpus embeddings, institutional scoring, a giant graph or four accounts. It should admit one original-source pair and complete source inspection before permitting an institutional revision card.

### Input boundary

Consume two already-lawful source records through the current Research Vault/Brain contract. Preserve existing report IDs, source-PDF and stored-body versions, publication generation, exact evidence spans or table cells, unit/period/basis, source attribution, and existing access decisions. Do not fabricate data currently absent from those owners. The R1B contract in #7079 and its quota behavior remain controlling.

The full four-set census is performed by `scripts/research_vault_census.py`. The source subset must be catalog-admitted, have the intended original PDF, have a correctly bound searchable extraction, and have a classified processing receipt at a recorded publication generation. A command exiting successfully is not proof those sets agree. No automatic repair during qualification.

### Calculation boundary

A pure comparison function may live as an additive leaf under the existing `engine/research_vault/` owner after its source/writer agreement is accepted. The exact JSON and oracle in this chunk define numerical semantics, not production authentication or trusted-source admission. No copying the assay's `allowed_for_assay` or `review_state` fixture labels into a product authorization gate.

### Consumer boundary

Continue the existing Brain and Research Vault viewer; do not introduce a separate reader. Before a Prophet projection, prove source opening from an actual entitled answer to the correct document/version and known page. Unknown page uses honest document-level fallback; a newer PDF must not be silently opened as the cited old version. UI integration is a subsequent path-cleared wave and does not bypass #7079 or the #7045 hygiene owner.

The minimal output carries: relation kind; entity/metric/period; before/after stated values and approximation; deterministic change when comparable; evidence references; origin-resolution and coverage limitations; source/derivation versions; and the existing context-only authority flags. It excludes an invented stock direction, confidence, score, trade, or absence-of-risk inference.

### Acceptance

One original issuer/broker class must be clearly stated—do not relabel issuer guidance as broker estimates. A genuine later same-period source revision reaches the existing answer/viewer path, a different-period case is refused, a correction round-trip behaves correctly, and allowed/denied/no-match/quota behavior remains correct. Customer acceptance requires browser proof; fixture success is not enough. Prophet rankings/sizing and private-position storage must remain unchanged.

## 7. Capital-allocation implication

The origin ambiguity gives us a specific additional reason to measure **marginal independent usable evidence**, not raw documents or raw institutional labels, before increasing accounts. A missing predecessor report needed for a revision can be more valuable than another near-duplicate current digest. That is a purchasing/acquisition-policy hypothesis to test, not a request to change the existing allocator today.

The public control also shows that the core numerical semantics can be developed before expanded subscriptions. Original-source qualification, rights, consumer usefulness and later marginal-capacity tests remain separate. Three total accounts remains a planning hypothesis; no purchase or quota pooling is authorized by this artifact.

## 8. Access limits and next action

The pinned large catalog read returned empty content with a nonempty Git blob identity; it was not treated as an empty vault. Sandbox attempts to obtain the explicit repository snapshots could not resolve the host. The earlier verified natural-ingest run `35033160225` has no downloadable artifacts in the GitHub response. The prior blocked M1 command lane was not retried. Consequently this chunk does not close the live four-set census or original broker-PDF pair.

**Exact next action:** admit and inspect one existing original-source pair through an approved read path at a recorded source generation, fill real hash/locator/availability fields, and rerun the newly specified distinctions against the existing Brain response and viewer. An authorized read capability and the use-specific source grant are the gates. Keep #7079/#7045 with their incumbent owners; do not fork their repair or start another collector. Labeling the larger research-answer evaluation can continue independently with appropriately permitted source material.

No account purchase, new MarketDesk extraction, vendor outreach, production code/configuration edit, signal change, customer-content publication, Executive Job or worker dispatch occurred in this chunk.

## Source register

- P0: Alphabet Q4 2024 earnings call, February 4, 2025: https://abc.xyz/investor/events/event-details/2025/2024-Q4-Earnings-Call/
- P1: Alphabet Q1 2025 earnings call, April 24, 2025: https://abc.xyz/investor/events/event-details/2025/2025-Q1-Earnings-Call/default.aspx
- P2: Alphabet Q2 2025 earnings call, July 23, 2025: https://abc.xyz/investor/events/event-details/2025/2025-Q2-Earnings-Call/
- P3: Alphabet Q3 2025 earnings call, October 29, 2025: https://abc.xyz/investor/events/event-details/2025/2025-Q3-Earnings-Call-2025-4OI4Bac_Q9/default.aspx
- P3 PDF, printed page 12 visually inspected: https://s206.q4cdn.com/479360582/files/doc_events/2025/Oct/29/2025_Q3_Earnings_Transcript.pdf
- P4: Alphabet Q4 2025 earnings call, February 4, 2026: https://abc.xyz/investor/events/event-details/2026/2025-Q4-Earnings-Call-2026-Dr_C033hS6/default.aspx
- R0: Macro `52380b870218b61865fb56458500cac00ce4932b`, `engine/neuralweb/brain_market_intel.py`, inspected source lines 850–1070, blob `306f1bb49797520bf46b5e2c8148801ddee18124`.
- R1/R2: Same pin, `site/research/gs-tmt-spec-sales-ai-complex-and-semis-benefit-from-nvidia-19abb4.html` and `...-16a699.html`, source identities above. The rendered pages are evidence about current repository content, not verification of the market claims inside the excerpt.
- R3: Existing Brain evidence PR https://github.com/mastermindx-market-intelligence/macro/pull/7079 and its design at head `a0a47535180dc0a60e176818a78ac7ec2c4c462d`.
- R4: Existing research carrier https://github.com/mastermindx-market-intelligence/macro/pull/7182.
