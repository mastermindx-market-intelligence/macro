# Research Vault — Chunk 6: correction and enrichment readiness

**September 16, 2026. Customer capability: SPEC_ONLY.** This is source investigation, a narrow local characterization, and a proposed follow-on contract. No production repair, source admission, original report binding, model benchmark, account purchase or customer proof.

## Mission and exact source

Make permitted institutional evidence useful and correctable across the existing Brain, Prophet explanation, company research and private portfolio paths. More acquired PDFs are not the same capability as current, source-bound, company-relevant intelligence. Prophet remains the flagship; research gets no signal, rank, sizing or trading authority.

Procedure: protected Mastermind@0fe8074ff953b2ced9025ed40f0f66019c759967, Skillpack 1.0.1/bootstrap 1. INDEX/COLD_START/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT were reread at this pin; immutable blob IDs match the previously fully loaded procedures.

Implementation: Macro@e625ea15c3f511f6c5f445e28acb69df5c148d50. `engine/research_vault/ingest.py` Git blob: `d005c052ebb76c465d45818db0df8d0b3db79c00`. Inspected ranges: 1–175, 340–595, 730–950, 990–1165; focused reread 381–557. This establishes the inspected paths' behavior, not the absence of every possible operator recovery tool.

Same research carrier: draft #7182 / `sol/research-vault-intelligence-design-r2-20260915`, starting head 74788a8ac3d45b21dd87a9a67f8e082ec8a79727. Direct reasons: PRINCIPAL_JUDGMENT for correction/publication semantics; LOWER_TOTAL_OVERHEAD for the bounded characterization. No new WS, Job, worker, watcher or provider call.

## 1. Newly established capability boundary

**Missing-data recovery, late enrichment and corrections are different capabilities.** Preserve the existing fill-only safeguards; do not mistake them for a general correction path.

- The main loop skips already-receipted inbox PDF keys. A change at an already-receipted key is not by itself a general update trigger in that loop.
- `_refresh_sidecars` candidates key on missing `summary_points`, a recoverable source key, and a dated 14-day lookback, capped at 500. Unknown dates remain eligible. Tickers, tags and desk are only opportunistically filled when a selected sidecar is read.
- A populated summary therefore prevents a later ticker/tag/desk enrichment from being fetched by this helper. Merely adding a producer will not connect those existing records to company and portfolio consumers.
- Refresh copies a field only when its previous value is empty and the incoming value is nonempty. A corrected populated summary is outside this path. That is intentional recovery behavior, not a violation of the helper's existing contract.
- `_resync_corpus_summaries` copies available catalog summaries only into NULL/empty corpus summaries. Two different populated summaries are not reconciled there.
- `_reextract_bodies` preserves already-present body text. It repairs missing extraction/measurement; it is not a general new-parser or full-tail migration.
- The main loop reports but retains byte-identical PDFs arriving under different source keys, explicitly allowing the same bytes to carry corrected metadata. Do not solve the previous GS/S&T origin ambiguity by deleting by title or assuming every duplicate is redundant. Original PDF equality in that case is still unproven.

Catalog generated time, a successful cron, receipt existence and needs_metadata have narrower meanings than 'all analytical content is correct and current'. Do not overload them.

## 2. Actual local characterization

The probe selected the two existing refresh function bodies through Python AST, supplied the inspected constants, and used a real in-memory SQLite summary table with controlled sidecar/store adapters. For this run the function bodies were transcribed from connector output, not downloaded as the full upstream source. The receipt explicitly says `input_mode=transcribed_source_excerpt` and `full_upstream_byte_match_verified=false`.

The runner supports a full-source mode that rejects any Git blob except d005c052ebb76c465d45818db0df8d0b3db79c00 before selecting those functions. **That full-file mode was not executed here.** Do not claim exact whole-upstream byte parity or a production ingestion test.

| Controlled case | Observed result |
|---|---|
| Recent missing summary, incoming summary + ticker | One sidecar read; catalog/corpus summary and ticker filled. |
| Existing old populated summary, incoming correction | Zero sidecar reads; old summary retained. |
| Existing populated summary, incoming late entity fields | Zero sidecar reads; ticker/tag/desk remain empty. |
| Corrected populated catalog summary, old populated corpus summary | Zero resyncs; old corpus summary retained. |
| Populated catalog summary, empty corpus summary, old report | One local resync, zero sidecar reads. |
| Missing summary on a dated 20-day-old report | Zero sidecar reads; remains missing. |
| Selected sidecar carries changed institution | Summary filled; original institution retained. |

Seven expected behaviors observed. These are characterization cases, not seven newly functioning production capabilities. Normalization is a controlled adapter for well-formed fixtures; no FTS, object store, PDF extraction, publication, quota, actual source or UI is exercised. The older 111-test assay was not rerun or combined with these cases; the 120-task model evaluation remains NOT_RUN.

Local diagnostic hashes: excerpt 08a4dc67794bb6e3a9262c127f024e0921c4d7d26609e2912b002ce7488ae35c; runner 9522a004db0089308354abd29c530118502372c48889feee5fd3241a6508423e; result 18f8d23e14370e8c619d9f11f65044a577fca0718224ce88ff1bc33af838dc3c. These identify the local diagnostic artifacts, not full upstream source bytes or institutional PDFs. The downloadable research package contains those artifacts and reproduction instructions; the compact repository receipt preserves results and limitations.

## 3. Proposed contract under existing owners

### Separate three change types

Original source bytes, extraction output and annotation output have separate versions. A corrected ticker does not create a new PDF or independent institutional opinion. A new PDF at the same URL is not necessarily the same source version. Preserve existing document identity and raw received labels; add version/provenance references within the existing source owner where needed.

### Trigger work on an eligible change, not permanent emptiness

Use producer-declared completed annotation versions or available source-object version/digest metadata through the existing ingestion owner. Inspect actual store capabilities before selecting an implementation API; an ETag is not automatically a PDF SHA-256. No new queue, scraper, full-corpus poller or cost ledger.

A known eligible producer change or a bounded admitted backfill should trigger processing. A field without a producer must not keep an hourly poll alive. Measure through the existing cost and run owners.

### Expected-prior-version updates

Each proposed change must target the exact document/source and prior annotation version. A stale expected version returns to reconciliation rather than overwriting newer accepted data. Repeating the same accepted generation must not add another effect.

Omitted fields differ from an explicit authorized clear. A partial sidecar must not erase valid fields. A supported incorrect ticker needs a removal path, not only fill-only addition. Identity and date corrections require their proper source owners and evidence. A model proposal is not a permission or source-authenticity authority.

### Validate and limit the correction

Numerical assertions retain metric, unit, period, basis and source support. Arithmetic inconsistency is an unresolved issue, not permission to guess the corrected value. The earlier Daily Asia number remains uncorrected and its faulting component unknown.

Entity mappings use existing canonical security/company identities; wrong-company lookalikes and obsolete mappings need negative tests. Generated interpretation must be checked against the source, not solely against an earlier generated summary. Keep source statement, extraction, calculation and synthesis distinct.

### Publish a coherent version

Corpus-before-catalog visibility protects admission of new IDs. A same-ID correction has a different risk: both old and new generations already contain that ID, so membership alone does not bind metadata, body and PDF to one version.

Under the SAME publication owner, stage and validate the new source/extraction/annotation version, then switch the visible reference when ready. Readers must use a pinned coherent version, a permitted last-known-good bound version, or an honest changed-source/unavailable response—not old metadata plus new body bytes. This is a requirement for adding corrections, not an observed production race. Do not add a second publication authority; the exact schema/storage amendment needs the current owner.

### Update dependent consumers only

| Change | Update | Boundary |
|---|---|---|
| Corrected company/segment | Research discovery, company links, relevant private portfolio explanation | Do not alter holdings or Prophet selection. |
| Corrected summary number | Dependent calculation, answer and research card | Preserve unrelated supported content. |
| New institutional estimate | New comparable claim and justified user update | Not a new trading or escalation authority. |
| Repeated known revision | Retrieval history and genuinely new interpretation | No duplicate alert just because a new PDF arrived. |
| New extraction version | Spans, locators, dependent evidence | No invented historical availability. |
| Source-use withdrawal | Applicable retrieval, indexes, caches and derivatives | No restricted-content leakage through graph edges. |

Use existing event, cache, editorial and delivery owners. A correction is not a separate alert service. Private portfolio values/queries remain outside shared research state.

An active answer should expose material correction/version information. Use existing editorial/delivery policy for already-delivered material; punctuation fixes are not thesis alerts. Preserve historical acquisition, extraction and product-availability clocks. Retain prior material only when permitted.

## 4. Alternatives and implementation order

**Keep fill-only and acquire more:** useful baseline, but does not deliver corrections or late entity enrichment for populated-summary records.
**Reprocess and overwrite everything:** not recommended; wastes unchanged work, can regress recovered fields, and creates version/history problems.
**Incremental version-aware change path under current owners:** recommended proposal. Keep existing recovery; add narrowly authorized changes and a bounded field-specific backfill, with consistent publication and dependent-only invalidation.

### First bounded leaf: late company enrichment reaches the existing consumer

Mission: an already-summarized report receives one verified company annotation and becomes findable in the existing company research path without losing the summary or changing source identity. This unlocks company/Prophet/portfolio usefulness rather than a disconnected annotation store.

Scope: existing sidecar producer, Vault ingestion/catalog/corpus and Brain discovery owners. Reconcile #7045's adjacent ingestion/hygiene writer and #7079 before assigning work; do not expand either PR silently. No new collector, index, quota, source identity or signal authority.

Method: deterministic source/version and canonical-entity checks; permitted model assistance may propose annotations. An initially manual admitted annotation may isolate propagation but does not prove extraction automation.

Acceptance: demonstrate the populated-summary failure before the intended change; then real permitted producer→ingest→existing search success; wrong-company and removed-annotation behavior; stale-generation refusal; idempotent rerun; preserved source summary; unchanged signal artifacts. Require actual consumer/browser proof after separately admitted implementation/release.

Stop on source/version/rights uncertainty, custody collision, or need for a new authority. Return to the existing principal rather than widening the PR.

### Second bounded leaf: one populated correction propagates

Show old evidence and an accepted source-backed correction; both nonempty catalog/corpus values reconcile through the authorized path; same-version inspection works; unrelated content remains; rerun adds no effect. Inject failed catalog publication in staging and prove partial corrected evidence is not served. No unapproved production fault injection.

### Third: reuse, then expand acquisition

After the original-source answer and update paths work, reuse the result in the Prophet explanation and private brief. Measure additional MarketDesk capacity against newly usable evidence, independence, continuity and timeliness—not generated annotation count. Three accounts remains a hypothesis; no account purchase here.

## 5. Future acceptance cases (not executed product tests)

1. Existing missing-summary recovery remains intact.
2. Populated summaries do not hide a completed eligible company annotation.
3. Fields without producers do not generate indefinite reads.
4. Omitted fields and explicitly authorized clears differ.
5. Older generations cannot overwrite newer accepted data.
6. Two nonempty catalog/corpus values reconcile after an admitted correction.
7. Same-ID changes never mix source versions in an answer/viewer.
8. Retry creates no duplicate revision, notification, debit or publication.
9. Wrong old company relevance is removed while correct new relevance appears.
10. A correction changes dependent calculations, not unrelated claims.
11. Denial leaks no restricted facts or query-conditioned content.
12. Viewer opens the correct source/locator or discloses changed/unavailable evidence.
13. Chinese-over-English retrieval is evaluated as cross-language work, not merely Han tokenization.
14. No research update changes signals, ranks, sizing or execution.

## 6. Release/access facts and next action

#7079 was reread open/draft/unmerged at 8271ae320732997be4553957e3e2773d1b9e9f1b. Its owner checkpoint dated 2026-09-16T04:42:29Z, comment 5692148771, reports PC CI offline, existing run 35056156631 pending, new evidence functions not deployed, and body/hash coverage unverified. This is dated owner evidence, not a fresh independent fleet audit here. Runner recovery stays with WS:RUNNER-FLEET-RESILIENCE; no relabel, new run, merge, restart or recovery was attempted.

The same checkpoint reports 2,204 catalog rows and zero Han-bearing searchable title/institution/summary rows at that observation. Do not equate Chinese lexical support with useful Chinese-language corpus coverage. This chunk did not remeasure those counts.

Native M2 file reads succeeded. One bounded local file-only Python read terminated with FileNotFoundError at the old recorded proof-worktree catalog path; no source was changed. The previously OpenAI-blocked M1 SSH command was not retried or rerouted. Current GitHub catalog metadata was read (blob 20fbb7c734b1e5233acafb8f0e87edbc3a3969d0, 2,713,264 bytes); sandbox download failed DNS. No full catalog analysis, live four-set census, source hash or customer proof is claimed. Further stale-path retries were stopped.

Public terms lookup did not establish the intended MarketDesk commercial permissions; similarly named unrelated products were excluded. No vendor communication, subscription purchase or full-source redistribution.

**Next positive production action:** the existing source owner admits one permitted current original with actual catalog ID, PDF/body identity, locator and source-use decision, followed by the incumbent Brain/viewer proof after its release gate. **New required follow-on:** freeze the late-company-enrichment leaf and correction publication contract with the Vault/Brain/#7045 owners, proving a populated-summary report through the real consumer.

Do not redo the 111-case reference or collector recovery (#7164 / Mastermind #631). Do not blindly remove fill-only guards, use duplicate redrops as the normal correction architecture, or call this characterization production intelligence.

## Sources

- https://github.com/mastermindx-market-intelligence/macro/blob/e625ea15c3f511f6c5f445e28acb69df5c148d50/engine/research_vault/ingest.py
- https://api.github.com/repos/mastermindx-market-intelligence/macro/contents/data/research_vault?ref=e625ea15c3f511f6c5f445e28acb69df5c148d50
- https://github.com/mastermindx-market-intelligence/macro/pull/7079#issuecomment-5692148771
- https://github.com/mastermindx-market-intelligence/macro/pull/7079
- https://github.com/mastermindx-market-intelligence/macro/pull/7182
- https://www.zerohedge.com/terms-of-service (public text inspected; not a complete commercial-use grant)
