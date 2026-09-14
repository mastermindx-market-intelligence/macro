# Mastermind AI — Source-Bound Research Evidence R1B

**Status:** APPROVED continuation under the Chairman's Mastermind AI upgrade directive  
**Operation:** `mastermind-ai-r1b-source-bound-evidence-20260913-sol-001`  
**Program owner:** `macro-mastermind-ai`  
**Protected procedure:** `mastermindx-market-intelligence/Mastermind@dfa518c079bca971ae55d53a1a6cd67d7128a039`  
**Predecessor:** R1A bilingual exact lexical catalog retrieval, PR #7079

## 0. Observable outcome

After catalog search identifies a permitted report, a Pro user can ask an exact
question in `mode="report"` and receive one to three deterministic passages
centered on the user's terms. Every passage is bound to the stored source by
document identity, source-PDF SHA-256, stored-body SHA-256, exact character span,
page number when the extraction carries page boundaries, publication time, and a
deep link that opens the same Research Vault document at the matching text.

Blank or one-character/noise queries retain the existing generic full-note path.
No matching passage, an unavailable body, or an image-only scan is disclosed and
does not consume full-text quota. A quota denial returns no report or evidence
text.

## 1. User and machine jobs

**User job:** Ask “What does this note actually say about AAPL demand?” and get
the relevant source text with a one-click route to inspect it, rather than a
12,000-character opening slice that may never reach the answer.

**Machine job:** Use the existing entitled corpus row, normalize only for
matching, select bounded exact-source slices deterministically, bind every slice
to source bytes and offsets, meter only content actually served, and expose a
whitelisted answer contract that cannot inherit arbitrary corpus fields.

## 2. Architecture and no-rebuild boundary

This wave extends the existing `engine/research_vault/corpus.py` owner and
`engine/neuralweb/brain_market_intel.py` consumer.

It does **not** add an embedding store, vector database, reranker, model call,
query log, cache, entitlement plane, quota ledger, document store, citation
database, or UI fork. Catalog search remains the report-discovery owner; the
corpus remains body/source authority; Brain remains the chat projection owner;
Research Vault remains the source-opening owner.

The deterministic selector applies NFKC/casefold for locating only. ASCII words
and identifiers use exact boundaries; Han phrases use literal matching. Emitted
text is always sliced from the original stored body.

## 3. Contract

`brain.research_evidence.v1` contains:

- `status`: `matched`, `no_matching_passage`, `query_too_short`, or
  `body_unavailable`;
- original `query`, `report_id`, and `published_at`;
- zero to three passages with exact text, matched source text, supported terms,
  locator, and source-opening URL;
- source binding with source-PDF hash, stored-body hash, complete/partial/unknown
  coverage, source/stored character counts, omitted-tail fact, text layer, and
  page count;
- access decision (`allowed` or `not_served`) and whether a view was metered;
- a canonical Research Vault deep link.

The legacy `report` object keeps its frozen field whitelist. In evidence mode,
`body_text` is only the selected passages and `body_truncated` states whether
any stored/source text lies outside those spans. In generic mode the existing
12,000-character cap and marker remain unchanged.

## 4. Rights, entitlement, quota, null, time, and correction law

- Missing signed-in identity fails closed before catalog or corpus access.
- An unknown report ID never probes the corpus.
- The existing Pro gateway and hourly view ledger remain the owners.
- Passage selection happens before metering so no-match/unavailable reads are
  free; the debit happens before matched text is returned.
- A denied debit returns only the existing limit error and leaks no passage,
  body, hash-derived content, or evidence envelope.
- Catalog publication time remains the visible publication authority. Page and
  character locators describe the stored extraction, not invented document time.
- `content_sha256` binds the source PDF bytes; `stored_body_sha256` binds the
  exact searchable extraction. `coverage` discloses whether the stored text is
  complete, a capped prefix, or unknown.
- Corpus refresh/correction uses the existing owner. No evidence result is
  retained, so a corrected row is reflected on the next read.
- Retrieved text is data, never instruction, rank, confidence, forecast, gate,
  size, or trade authority.

## 5. Failure behavior

- `pro_required`: no identity; no corpus read.
- `report_not_found`: catalog does not carry the requested ID; no corpus read.
- `vault_unavailable`: catalog/path failure; no invented content.
- `body_unavailable`: public metadata/excerpt only, honest scan/temporary
  shortfall note, no debit.
- `query_too_short`: public metadata/excerpt only, ask for a specific question,
  no debit.
- `no_matching_passage`: public metadata/excerpt plus document-opening link, no
  inference from absence, no debit.
- `view_limit_reached`: no report/evidence payload and no source-text leakage.

## 6. Product boundary

R1B closes the first trust-critical answer loop: discover report → ask exact
question → inspect supporting source. It does not yet synthesize multiple
reports, adjudicate disagreements, create claim graphs, or rank evidence.

UI files with active writers remain untouched. The response contract and public
deep link make the capability independently useful through the existing Brain
tool surface; a later collision-cleared UI wave may render evidence cards
without changing this contract.

## 7. Acceptance and proof

1. A full-width `ＡＡＰＬ demand` question returns the exact original `AAPL demand`
   passage rather than opening boilerplate.
2. The passage carries stable hashes, character offsets, supported terms, page
   when known, and a canonical `doc/find/page` deep link.
3. ASCII identifier boundaries reject decoys such as `AAPLX`; Chinese phrase
   matching remains deterministic.
4. Blank/noise calls use `get_document`, preserve the existing full-note
   projection and quota behavior, and return `evidence: null`.
5. Meaningful exact-question calls use `get_evidence_document`; the legacy reader
   is not touched.
6. Matched text debits exactly once. No-match, unavailable body, image-only body,
   and too-short evidence query debit zero times.
7. Denial leaks no report, evidence, or source text.
8. Existing search, clusters, report-rights, exposure-cap, fail-soft, attribution,
   gateway, and tool-schema contracts remain green.
9. Independent review checks source binding, quota order, rights wording,
   whitelisting, correction behavior, and absence of a duplicate retrieval plane.
10. Merge, deployment, a real entitled Brain call, a working deep link, and final
    acceptance remain distinct gates.

## 8. Stop condition and continuation

Stop R1B when the exact reviewed head is merged and an entitled production Brain
call returns a source-bound passage whose link opens the same deployed Research
Vault document. The next capability is multi-document claim synthesis over these
immutable evidence envelopes—not another corpus or retrieval implementation.
