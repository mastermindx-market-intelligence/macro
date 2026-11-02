# Mastermind AI — Source-Bound Research Evidence R1B

**Status:** APPROVED continuation under the Chairman's Mastermind AI upgrade directive
**Operation:** `mastermind-ai-r1b-source-bound-evidence-20260913-sol-001`
**Program owner:** `macro-mastermind-ai`
**Protected procedure (current repair observation):** `mastermindx-market-intelligence/Mastermind@6061c0b32f1adad56a1282bbc01e70ce7f0a5a44` (Skillpack 1.0.1 / bootstrap 1; the historical operation epoch remains 2026-09-13)
**Predecessor:** R1A bilingual exact lexical catalog retrieval, PR #7079

## 0. Observable outcome

After catalog search identifies a permitted report, a Pro user can ask an exact
question in `mode="report"` and receive one to three deterministic passages
centered on the user's terms. Every passage is bound to the stored source by
document identity, source-PDF SHA-256, stored-body SHA-256, exact character span,
page number when the extraction carries page boundaries, publication time, and a
canonical deep link that opens the same Research Vault document. The link carries
only `doc` (query string) plus an optional `page`/`q` fragment — never publisher
match text — for the still-pending viewer wave.

Blank, stopword/noise-only, and generic summary/argument requests retain the
existing generic full-note path. Generic intent is a CATEGORY/STRUCTURE
classification, punctuation- and position-insensitive, not a sentence table:
Brain removes a named summary/argument/overview intent trigger (EN word, ZH
phrase, or a TL;DR spelling), document-target (including an institution/proper
noun immediately modifying the document word), and polite/question/format
scaffolding, then asks the corpus's existing atom owner whether a real content
topic remains. A residual topic takes the source-bound evidence path. Chinese
generic-intent recognition covers named intent phrases (总结/概括/摘要/分析/
主要观点/论点) and the "what does this say" idiom (讲了什么/说了什么); Chinese
EXACT-QUESTION retrieval, by contrast, is honestly scoped to literal key-term/
key-phrase matching (no sentence segmentation) — the tool schema tells the model
to pass 1-3 literal Chinese terms for a specific factual request, not an
unsegmented sentence.

A passage window is bounded independent of match length: an arbitrarily long
single atom (one unsegmented Han run) is clamped to the configured window, never
exposing the whole match. A source-bound passage also requires an already-
canonical lowercase 64-hex `content_sha256`; case-folding, whitespace trimming,
or any other normalization is forbidden because it would manufacture a source-
identity claim. A missing/malformed/non-string/wrong-length/noncanonical source
hash fails CLOSED to bounded public metadata/excerpt and an honest source-
identity-unverified note — never a scan/extraction claim. Locator offsets, page
numbers, source/stored counts, and page counts are trusted only when supplied as
literal integers of the required sign; numeric strings, floats, booleans, and
malformed passage containers are never coerced into evidence facts. The corpus
accepts publisher `body` only when it is already a string—Python representations
of dicts, lists, tuples, numbers, and booleans are never searchable evidence.
Caller passage windows accept only literal integers and clamp to the frozen safe
`[80, EVIDENCE_WINDOW_CHARS]` interval; nonliteral values use the safe default.

No matching passage, an unavailable body, an unverified source identity, or an
image-only scan is disclosed and does not consume full-text quota. A quota
denial returns no report or evidence text.

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
corpus remains body/source authority and the sole owner of content atoms,
stopwords, passage matching, and source binding; Brain remains the chat intent
and projection owner;
Research Vault remains the source-opening owner.

### 2.1 Successor authority and CI-ownership receipt

R1B explicitly supersedes the earlier lexical R1 two-path/protected-boundary restriction only for `engine/research_vault/corpus.py`, which is the canonical body/source owner required by this capability, and for minimal `.github/ci/legacy-jobs.yml` registration under existing pre-merge `gate: code` owners. `tests/test_brain_research_evidence.py` and the ownership regression `tests/test_mastermind_ai_evidence_ci_ownership.py` belong to `unrun-brain-gateway`; `tests/test_research_evidence_passages.py` belongs to `research-vault-api`. The rejected R9 carrier put the two product suites under `neural-web-core` and `research-vault`, both `gate: data` jobs that `ci.yml` intentionally excludes from the merge gate. `contract-delta` proved the suites were named but did not prove pre-merge execution. R10 moves each suite rather than duplicating it and adds no job, workflow, dependency, gate, or duplicate owner; every other R1 non-goal remains frozen.

The 2026-09-14 collision receipt is historical evidence only; it does not authorize the R10 owner move or the new regression path. Before publication, a fresh open-PR census must prove no independent writer owns any full PR path and patch-level inspection must clear the `unrun-brain-gateway` and `research-vault-api` command anchors plus all three suite tokens. Any collision or unavailable manifest patch remains a release block. Broad manifest-path non-overlap is not claimed.

The deterministic selector applies NFKC/casefold for locating only. ASCII words
and identifiers use exact boundaries; Han phrases use literal matching. Emitted
text is always sliced from the original stored body.

## 3. Contract

`brain.research_evidence.v1` contains:

- `status`: `matched`, `no_matching_passage`, or `body_unavailable`;
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
- After catalog identity and before either generic or evidence document read, the
  existing report-view limiter is peeked using the same identity, scope, and clock
  as the debit. Exhausted users receive the byte-equivalent uniform limit response
  before a reader, selector, source binding, or passage metadata can reveal paid
  body presence or query-conditioned information. A peek storage failure stays
  fail-open; a served body or matched view still takes its existing one-time debit.
- A no-match/unavailable read is unmetered only after that privacy preflight.
  Selector status alone is never debit authority: Brain first performs literal
  projection, strict locator/source-identity validation, body assembly from the
  projected passages, and recursive whole-envelope budgeting. Only a valid,
  nonempty matched envelope that will actually be returned takes one debit.
- Sol's ruling: an entitled query-centered retrieval may search the lawful stored
  corpus beyond the legacy 12,000-character opening prefix. `REPORT_BODY_MAX_CHARS`
  remains a per-response model-context ceiling over every string value—not only
  `body_text`, but excerpts, metadata, URLs, query echoes, passage duplicates,
  matched terms, hashes, notes, and caller-supplied identifiers in error envelopes.
  Budget trimming may duplicate a passage into legacy `body_text` only while the
  evidence status is `matched`; a no-match/unavailable status can never acquire
  publisher text during fitting. Bounded passage count/window, sparse publisher
  quotation, attribution, one debit per served view, no redistribution, and no
  new lifetime ledger remain binding.
- A denied debit returns only the existing limit error and leaks no passage,
  body, hash-derived content, or evidence envelope.
- Catalog publication time remains the visible publication authority. Page and
  character locators describe the stored extraction, not invented document time.
- `content_sha256` binds the source PDF bytes; `stored_body_sha256` binds the
  exact searchable extraction. `coverage` discloses whether the stored text is
  complete, a capped prefix, or unknown. Unknown never carries a source character
  count; a no-match explicitly states that coverage could not be verified and that
  absence is not evidence.
- Corpus refresh/correction uses the existing owner. No evidence result is
  retained, so a corrected row is reflected on the next read.
- Retrieved text is data, never instruction, rank, confidence, forecast, gate,
  size, or trade authority.

## 5. Failure behavior

- `pro_required`: no identity; no corpus read.
- `report_not_found`: catalog does not carry the requested ID; no corpus read.
- `vault_unavailable`: catalog/path failure; no invented content.
- `body_unavailable`: public metadata/excerpt only, honest scan/temporary
  shortfall note, no debit. A missing/malformed source-PDF `content_sha256`
  reuses this same status (no second identity/status plane) but with a distinct
  honest note — a source-identity gap, never described as a scan or extraction
  failure.
- `no_matching_passage`: public metadata/excerpt plus document-opening link, no
  inference from absence; when only a stored prefix was searched, disclose its
  stored/source character counts and that the omitted tail may contain the topic;
  when coverage is unknown, disclose that absence is not evidence. The current
  no-match request is unmetered; a later generic full-note re-call remains
  available and takes the existing one-time debit if a nonempty body is served.
- A selector that reports a match but supplies no usable literal passage text—or
  supplies a malformed non-list passage container—is an honest no-support/body-
  unavailable disclosure, not an exception, scan, or extraction failure, and is
  not charged. Passages attached to an upstream no-match/unavailable status are
  supporting-data corruption and are discarded before projection; they never
  enter either `evidence.passages` or legacy `body_text`.
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
   when known, and a canonical `doc`(+`page`/`q` fragment) deep link that never
   carries publisher match text or a `find=` param. Offsets/counts require literal
   nonnegative integers and page values require literal positive integers; a
   numeric string, float, boolean, or structurally malformed page locator fails
   closed. R1B emits the character-span
   and page locators in the passage payload itself, but the current viewer
   consumes only `doc`; consuming the fragment `page`/`q` remains Repair B and is
   not shipped by this commit.
3. ASCII identifier boundaries reject decoys such as `AAPLX` while still matching
   directly against adjacent Han script (Han is not an ASCII identifier
   continuation); Chinese literal key-term/key-phrase matching remains
   deterministic — Chinese sentence segmentation is out of scope and is not
   claimed.
4. Blank, stopword/noise-only, and generic summary/argument calls use
   `get_document`, preserve the existing full-note projection and quota behavior,
   and return `evidence: null`; a residual topic uses `get_evidence_document`.
5. Meaningful exact-question calls use `get_evidence_document`; the legacy reader
   is not touched.
6. Matched text debits exactly once, only after strict projection and recursive
   whole-response budgeting produce at least one coherent passage and nonempty
   body. No-match, unavailable body, image-only body, an invalid projected
   passage/container, an envelope that cannot be fit safely under the ceiling,
   and a matched selector without usable text debit zero times. Nonmatched budget
   fitting leaves both `evidence.passages` and `body_text` empty, and every error
   envelope bounds caller IDs while accepting quota counts only as literal
   nonnegative integers under the same response ceiling.
7. An exhausted generic or specific request leaks no report, evidence, source text,
   reader access, or selector access.
8. Existing search, clusters, report-rights, exposure-cap, fail-soft, attribution,
   gateway, and tool-schema contracts remain green.
9. Independent review checks source binding, quota order, rights wording,
   whitelisting, correction behavior, and absence of a duplicate retrieval plane.
10. Repair B teaches the existing Research Vault viewer to consume the bounded
    `page`/user-`q` fragment after a fresh collision census; until then the link
    opens the canonical document but does not position it at matching text/page.
11. Merge, deployment, a real entitled Brain call, a working deep link, and final
    acceptance remain distinct gates.

## 8. Stop condition and continuation

Stop R1B when the exact reviewed head is merged and an entitled production Brain
call returns a source-bound passage whose link opens the same deployed Research
Vault document. Matching-text/page viewer behavior is Repair B, not evidence that
this R1B commit already ships it. The next capability is multi-document claim
synthesis over these immutable evidence envelopes—not another corpus or retrieval
implementation.
