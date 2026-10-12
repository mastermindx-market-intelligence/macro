# Research Vault — Chunk 12: a working isolated source-discovery bridge

**2026-09-16. Customer upgrade remains SPEC_ONLY.** The review implementation now demonstrates discovery -> exact captured source -> literal passage with an actual synthetic PDF. This is not the deployed Brain, an authentic entitlement check, original institutional evidence, a model answer or customer acceptance.

## 1. Outcome and why it matters

The decisive passage is absent from the catalog title and summary. An explicitly permitted source-text request discovers its report ID, without returning body text in the discovery response. A separately checked read verifies the current PDF bytes and stored extraction, calls the incumbent source-bound passage selector, and returns the literal page-two support. After a fixture source update, the old selection is refused; rediscovery reaches the new version.

This changes the R11 result from a diagnosed missing connection into a runnable review candidate. The ordinary Brain metadata path is not edited. No new chatbot, search index, identity dictionary, authorization ledger or publication service is created. Prophet remains the flagship; research supplies evidence, not scores, rankings, sizing or execution.

## 2. Source and carrier

Procedure: protected Mastermind@5ee11ab1e993616f3568cfca4069cb21fa61fd8f; INDEX plus COLD_START/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT loaded at the same commit, compatible Skillpack1.0.1/bootstrap1. Companion blobs match procedures already fully loaded. Live Chairman continuation supplies research intent, not release/rights exceptions.

Research carrier: Macro PR7182, branch sol/research-vault-intelligence-design-r2-20260915, starting head8e7ecadc009a514122adbc4dd742c89b0b6eea3a. Main ref observed89bdc314a0e096759553f669cc6483b34d89bf7b. Pending Brain evidence PR7079 remains draft/unmerged at8271ae320732997be4553957e3e2773d1b9e9f1b. No new writer, Job, workstream, worker, watcher or runtime lease was created. Direct rationale: PRINCIPAL_JUDGMENT for the permitted discovery/read boundary, LOWER_TOTAL_OVERHEAD for this isolated test implementation.

Complete code dependencies:
- Existing baseline corpus:28,591 bytes; Git blob0b035b34489a4efd2ae7a3c59d153b3d1977701a.
- Pending #7079 corpus:42,504 bytes; Git blob1bc0aacd46d8ec0ad25d3b53341040a3e6aa1af8. Reconstructed from the verified baseline plus connector-read changes, then matched in full to the upstream Git blob. This is not a transcription-only selector.
- Existing R9 scoped/strict search proposal: Git blobd9593533dad00251a97d0813f6598ea1fffb8236, unchanged. Applying its search hunks to the pending corpus, while preserving its additional hashlib import, produces review-only SHA25658bfdaf91f1cb7f9a4f7e1f700bd90be3269fe9ea7d6cc156661a9a456b89d6f.

The two source snapshots under upstream/ are immutable test dependencies pointing to existing Git blobs, not alternative runtime authorities. The composite exists only in isolated review output. Neither PR7079 nor production engine files are modified.

## 3. Demonstration: actual PDF bytes, not a hand-entered body fixture

ReportLab authors an explicitly labeled two-page synthetic report. Every company, source and forecast is fictional. Poppler pdftotext extracts it; the existing corpus upsert stores the extracted text and measured source digest. Its catalog says only Industrial operations review and general manufacturing developments; it contains neither Orionquartz nor margin.

The query `orionquartz margin` produces one ID from the existing scoped FTS. Discovery returns no passage, price/estimate, body excerpt or relevance score. The selected read uses the exact #7079 `find_evidence_passages` implementation and returns page2, including:

> Orionquartz margin outlook for FY2027 is revised from 31% to 28%.

The same literal passage retains the invented cost explanation, schedule condition, and explicit no-real-research disclaimer. No LLM generates a financial interpretation.

Actual fixture PDF SHA256:e5c73cf8c17917e421a34d2d90fe7a270fd053f7cca8b95c7fb1d254d1e35bfb.
Actual extracted text SHA256:dbe55b614bb249ade89ca31d2ff364dd2b2e4a5724402eeae65f40bb33356bfa.
The emitted passage equals its indicated substring of extracted text. The source-file hash is measured from actual PDF bytes, not filled with a hash-shaped example. Both pages were rendered and visually inspected locally. This is PDF-render inspection, not an authenticated website/browser test.

The fixture then publishes a corrected PDF changing28% to29%, using existing corpus upsert plus updated controlled owner state. Old selection returns `selection_stale` before accounting; new discovery/read returns the revised support. Two successful reads invoke the accounting stand-in twice. This proves receiver behavior under changed versions, not automatic sidecar correction propagation or real quota accounting.

## 4. What the reference implements

`r12/bridge.py` has two review entry points, not registered runtime tools.

**discover:** requires explicit source_text scope; calls the injected scope owner before opening the corpus; uses its eligible IDs before final result budgeting; returns bounded report metadata and a versioned selection reference. Empty access set avoids the corpus. Healthy no-match says stored_corpus_text and never claims complete-original search. Database failure stays unavailable.

**read_selected:** rechecks permission and selected generation; verifies catalog-selected PDF and body identities against the current row; reads the original through the supplied source owner; verifies the actual bytes; reuses the incumbent selector; accounts only after usable evidence exists; and prevents disclosure if access changed during accounting.

A selection is not a bearer authorization token. Guessing or replaying one does not supply permission. It holds the bounded query and expected versions so the next read can detect drift. No new retained identity/permission state is introduced.

The scope provider and accounting callbacks are deliberate unresolved integration seams. In tests they return controlled fixtures, not real entitlements or licensing decisions. Production adoption must map them to the EXISTING gateway/source/accounting owners. The read callback's error state must not silently override an existing approved fail-open policy: the proposal conservatively withholds text and records uncertainty; the actual owner must adjudicate its production mapping.

If an accounting call raises, it may already have had an effect. The reference does not repeat it. If access changes after a successful accounting response, it withholds the passage without inventing a refund. Reconciliation belongs to the existing ledger owner.

## 5. Actual verification

Initial feature-first test run against the unimplemented reference scaffold:28 cases,27 assertion failures. That is a missing-reference baseline, not27 broken production behaviors. The first implementation passed28/28. Four added review cases exposed one additional access-change-during-accounting failure; that was repaired and the final suite passed32/32.

The self-contained final reproduction runs32 checks, zero failures/errors. Six direct mutations are rejected: implicit source escalation; removal of eligibility before budgeting; ignored stored-body identity; ignored PDF identity; ignored generation; and ignored access change after accounting. They are direct local challenge, not independent external review or six additional tests. Exact execution timestamp/environment and source/code identities are in verification_r12.json.

Coverage includes body-only discovery; no unmetered body in discovery; exact page/substring/hash binding; denial before database access; resolver failure; no implicit metadata escalation; valid no-match vs missing FTS; ineligible candidate crowd-out; stale generation; revoked/removed access; source/body drift; missing original; no-match without accounting; denial/unknown accounting; corrected-version rediscovery; invalid identifiers/limits/query budgets; bounded results; and unchanged source/signal authority.

The declared-prefix test deliberately changes fixture metadata to verify that partial coverage is disclosed. It does not validate real extractor completeness. Hash/version integrity does not independently certify semantic extraction, chart/table interpretation or publisher authenticity.

No older test total is rerun or added. The120-task model benchmark remains NOT_RUN. No actual Brain gateway, #7079 full `_research_report` function, real auth, live ledger, institutional source, browser or model is executed. The reused unit is the complete corpus module and its original passage selector.

## 6. Implementation handoff: one real consumer, no wider platform

Mission: a permitted source-text question reaches an inspectable passage without needing the user to identify the PDF. Why: directly unlocks institutional Q&A, then evidence for Prophet and private briefs.

Authority: live Chairman/current procedure; existing Brain gateway/tools and source-use owner; existing Vault/catalog/corpus/publication; existing accounting and identity. PR7079's writer/release remains incumbent. The research proposal does not self-assign runtime custody.

Order: settle the explicit source-text eligibility and accounting contract; qualify complete current gateway/Brain files; integrate the narrow bridge into the existing tool; preserve metadata behavior and legacy callers; run owner suites and staging failure cases; admit one real permitted source and its extraction; prove actual gateway -> selected reader -> viewer; then validate answer quality and company-qualified associations.

Input/version rules: original publication, actual acquisition, extraction and product availability remain distinct. No backdated historical knowledge. A corrected PDF or extraction invalidates old selections. Re-resolution is required, not an automatic source substitution. Null/unknown permission is not allow. The30MB review source-byte bound is a local fixture safety setting, not a new product download entitlement or production size policy.

Acceptance: real source absent from catalog summary is discovered in explicitly authorized scope; no unauthorized content-conditioned result; bounded readable evidence; compatible source/body/version; actual accounting and denied states; correct source opening; source/correction behavior; preservation of Essential metadata access; existing Prophet signal/rank/sizing/execution artifacts unchanged. A returned FTS candidate is not necessarily an answer or a correctly qualified company association.

Stop: missing upstream use rights, unresolved writer custody, unavailable original, incompatible generation, or effect uncertainty. Do not bypass those with a fixture permission or a new model/provider. No source download, entitlement edit, merge or deployment is authorized by this report.

## 7. Investment consequence

The practical new option is to discover existing evidence before commissioning an expensive model or buying a larger archive. The prototype does not require a new embedding service or graph database. It still does not prove that lexical retrieval is sufficient for paraphrases, cross-language questions, long scanned reports or independent-source comparisons.

Preserve the crossed acquisition/processing evaluation. The new consumer gives the pilot a place to measure whether additional permitted documents yield additional supported answers. Do not convert this32-case mechanical result into a subscription ROI claim. No new purchase, price, allowance, pooled-account grant, retention decision or institutional-content license was established. Three accounts remains an unapproved hypothesis.

## 8. Current holds and continuity

The bounded GitHub comment read after the prior checkpoint returned no later #7079 response. That is not a universal activity census. #7079 was reread draft/unmerged at its same head. An attempted sandbox raw-source read failed DNS; GitHub connector reads and hash reconstruction succeeded. No previously platform-blocked native or administrative browser action was retried or rerouted. No native host tools, provider/model calls, worker/Job/watch, CI dispatch, source acquisition, vendor communication, subscription or runtime changes occurred.

Next primary action: the incumbent Brain/Vault owner adopts or amends the explicit source-discovery/access/accounting seams and maps this candidate into complete current source, followed by one real permitted source through the authenticated consumer. The local demonstration is complete; the parent product is not.

## 9. Reproduction

With installed Python, ReportLab, Git and pdftotext, run from the research directory:

```sh
python r12/run_review.py --output-dir /tmp/rv-r12-new-review
```

Use a new output directory. Defaults use the pinned upstream/ snapshots and existing corpus_search_r9.patch; optional arguments specify other local copies but hashes must match. Nothing is downloaded, installed or written to runtime. The package includes synthetic PDFs, source text, all test code, dependency snapshots, raw results and the source preview. The same artifact does not require a missing prior chat ZIP.
