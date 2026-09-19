# Research Vault — Chunk 8: executed discovery failures and delivery contract

**2026-09-16. Customer capability remains SPEC_ONLY.** This chunk reproduces source-level discovery failures with controlled data. It does not repair production, acquire institutional reports, establish licenses, or prove an authenticated Brain/viewer journey.

## 1. Outcome and exact sources

Human job: from an existing Prophet/company context, find genuinely relevant institutional evidence and know the difference between no qualifying research and failed/incomplete retrieval. Machine job: preserve company identity, source eligibility, result-budget semantics and request context through the existing Vault/Brain path.

Procedure pin: protected `Mastermind@52bb602616504954861d31dc86b9a11f22e7444d`, Skillpack 1.0.1/bootstrap 1. INDEX was read; COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT were fetched at the same pin. Their returned blob identities match the full procedures already loaded in this conversation. No procedure text supplied permissions.

Implementation pin: `macro@e86cf4593d2c2603a695ccab858f98ac4a29abae`.

- `engine/research_vault/corpus.py`: full Git blob **0b035b34489a4efd2ae7a3c59d153b3d1977701a**, **28,591 bytes**. The complete file was reassembled from connector file reads and its exact full-file Git blob verified before import. It is not the transcribed-partial-source mode of R6.
- `app/research.py`: upstream blob **bca9b965057df653607765107ef789692c47dcdc**. The selected `research_search` function was copied from the connector range 519–592; whole API-file byte parity is NOT claimed.
- `site/research_vault_app.js`: upstream blob **1f0b673da6c3d6a44ad3d74b2994f70b9a4311c8**. Selected `laneMatch`, `matchItem` and `onSearchInput` ranges were copied from the connector (596–616 and 765–785); whole client-file byte parity is NOT claimed.

Existing carrier: draft PR #7182, branch `sol/research-vault-intelligence-design-r2-20260915`, starting head `2bf7f349e87d9b905e884d9b693d5654f87a3777`. Direct work reasons: PRINCIPAL_JUDGMENT for cross-layer interpretation; LOWER_TOTAL_OVERHEAD for a small local characterization. No new Job, workstream, worker, watcher or provider call.

## 2. Actual execution and interpretation

Retained local run: **2026-09-16T08:12:48.820436+00:00**, Python 3.13.5, SQLite 3.46.1, Node v22.16.0.

**16 checks: 11 baseline controls met, five proposed product requirements NOT met.** The five failure observations are reproduced gaps, not five repaired features. Exit 0 means the characterization completed and matched its declared expectations; it is not product acceptance.

The corpus ran unmodified against synthetic, disposable SQLite/FTS5 databases. The selected route ran directly after removing only its registration decorator, with controlled catalog/auth helpers and explicitly passed arguments. The selected client functions ran in Node's VM with controlled timers, network responses, input values and render callbacks. No real HTTP server, browser DOM, session, billing or rights decision was exercised. Synthetic company label ACMEQ is not a real identity assertion or an admitted source.

A separate guard challenge changed the corpus bytes by one newline; the source verifier rejected it. This challenge is not added to the 16-case total.

### Reproduced gaps

| Case | Controlled observation | Product consequence |
|---|---|---|
| R8-G1: metadata-only association | Browser fallback initially matches `metadata-only` via its ACMEQ ticker. The actual corpus returns no hits; a successful server response changes visible matches to empty. | Filling a ticker field alone does not deliver server-backed company discovery. |
| R8-G2: index failure becomes available-empty | A deliberately missing FTS table makes the corpus return `[]`; the selected API returns `items:[], count:0, available:true`. | Some failures are indistinguishable from successful no-match at this boundary. |
| R8-G3: unavailable response becomes empty client set | The route correctly reports `available:false` when no connection is supplied. The client still installs an empty hit-set and suppresses a locally matching fixture. | Backend unavailability alone is not enough; the client must preserve and display its meaning. |
| R8-G4: eligibility after result limit | Raw order is `ahead-a`, `ahead-b`, `allowed-report`. With only `allowed-report` admitted and limit 1, the API returns no result. | The filter prevents disclosure, but applying it after limiting loses an eligible match. |
| R8-G5: same query, changed facet, stale reply | The newer DeskB response displays `new`; the older DeskA reply has the same query text and overwrites the hit-set, leaving no visible result. | Query-text equality is not complete request identity. |

G1 is an executed synthetic readiness counterexample: the earlier measured catalog had no ticker annotations. It is not evidence that a real ticker-only report already disappears in production. G2 deliberately damages a test database, not the live index. G4 proves one controlled ordering failure, not its live frequency. G5 is selected-function execution, not proof of actual production UI event timing.

### Working controls

Literal title and body searches work. A healthy unmatched query returns available-empty. Missing catalog or connection is refused by the selected route. Non-admitted and non-preview IDs remain excluded in the controlled cases. Metadata input does not alter literal source columns. HTTP failure preserves the existing client fallback, a valid empty response does not get widened by local union, and a different-query stale response is rejected.

These controls matter: this is not a finding that all search is broken. They are also not an authentication/security audit; access decisions were fixtures.

## 3. Why the original investment decision now has a sharper dependency

The R7 whole-catalog result—2,208 rows, 2,197 summaries, zero populated ticker fields—remains a dated observation, not a new R8 census. R8 tests its proposed downstream use rather than rerunning the inventory.

Three transformations must be evaluated separately:

1. Acquired report to source-supported, correctly identified evidence.
2. Accepted evidence to retrievable results in the user's actual scope.
3. Retrieved evidence to a useful answer, brief or explanation.

More acquisition cannot by itself repair transformations 2 and 3. The result-limit fixture also shows why more candidates can crowd out eligible evidence when filtering comes too late. This is a reason to fix retrieval before the marginal-account experiment, not a measured finding that more MarketDesk accounts currently make the product worse.

Do not train a model or write an enormous graph to compensate for these deterministic problems. Keep acquisition-value evaluation separate from retrieval fixes. Three accounts remains a hypothesis; no current allowance, price, permitted pooling, retention grant or marginal benefit was established here.

## 4. Proposed first implementation leaf: trustworthy company-search outcomes

This is a **build-ready proposal awaiting current source-owner/interface acceptance**, not a new commission or admitted runtime job. It does not expand #7079 or #7045 without their owner.

### Mission and value

Ensure the existing research path returns the best eligible results for its declared scope, distinguishes failed/incomplete search from genuine no-match, and preserves the newest query context. This unlocks useful company evidence and prevents the Brain from interpreting a failed search as institutional silence.

### Authority and source precedence

Live Chairman direction and current protected law govern. Existing Vault owns source/catalog/corpus; existing identity reader owns issuer/security/listing identity; Brain owns orchestration; current auth/entitlement owners own eligibility; current publication owner owns visibility. No new identity, permission, graph, queue, source-store or publication authority.

### Scope and interfaces

Keep the current endpoint and consumer. Preserve compatibility for existing list-based corpus callers while carrying an explicit successful/unavailable/invalid-query outcome to consumers that need it. Exact names and additive schema changes must be frozen with incumbent owners; this document does not claim a deployed `search_result` API.

A genuine empty answer requires a successful query over a known eligible snapshot and declared coverage. An index/connection fault is unavailable; malformed input is not proof of an empty corpus. Return no raw SQL, paths, credentials or restricted existence data in error details.

Derive eligibility from current accepted owners and apply eligibility and subject scope before the final result budget. Do not persist a second authorization mirror or solve misses by simply raising the limit. Large eligibility sets, query plans and deterministic ties need tests on realistic cardinalities before release.

Preserve request identity across query, active facets, subject, catalog/source generation and authorization-context changes. Invalidate in-flight responses when those inputs change, including clear-query and repeat-query transitions. Reuse existing client request-version idioms; do not add a scheduler or background polling system.

An unavailable result must not be installed as an authoritative empty hit-set. A clearly labeled, permission-eligible local fallback may remain useful where the existing contract allows it. Denied access must never be widened through an unrestricted local union. Preserving matches alone is not enough: show the degraded state and scope.

### Data, time, null and correction behavior

Subject association is not literal source text. Preserve issuer versus security and about/compares/mentions roles. Do not inject generated ticker keywords into an institutional summary or PDF body to force matches.

Keep null, absent, unsupported and explicitly removed annotations distinct. A correction is an accepted new source/extraction/annotation version; stale expected versions must not overwrite newer ones. Pin one coherent visible source version per answer. Nothing here creates historical knowledge or establishes the complete institutional universe.

### Method

Eligibility, query ordering, request-version guards and status propagation are deterministic. A model may propose company associations only through an admitted evidence/identity path; no model is required to fix the five reproduced control-flow issues. Retrieval relevance is not Prophet trade-ranking authority.

### Implementation order and proof

1. Add failing cases to existing corpus/API/client test owners using this receipt's inputs and desired outputs. Keep current healthy and denial controls.
2. Preserve query-failure meaning through corpus, route and client; check genuine no-match separately.
3. Apply accepted eligibility before final result limiting, with realistic bounds and no permission widening.
4. Fence stale responses using the full request context and display source/search state honestly.
5. Admit a source-supported company association through the existing late-update path; prove a populated-summary report becomes findable through successful server search, not only fallback.
6. After separate release authorization, prove the actual entitled Brain/viewer journey, correction/removal and bilingual usefulness. Prophet scores, boards, ranks, sizing and execution remain unchanged.

The first four steps can be developed with fixtures without third-party source acquisition. They are not a substitute for step 5–6 product proof. Current writer custody must be accepted before any shared production-path edits.

### Acceptance, stop and continuation

The five failing requirements must meet the accepted contract while the eleven controls remain intact. Add index unavailability, source-generation mismatch, repeat-query and auth-change cases, large eligibility sets, entity ambiguity, denied/quota behavior and actual source opening under existing test owners. These additions are requirements, not executed tests.

Stop the affected lane on source-rights uncertainty, identity/version conflict, writer collision or effect uncertainty. Do not replace incumbent work, retry blocked source access through another actor, or merge on this assay. Return an exact candidate/head, failing/passing case evidence, source and deployment identity, browser proof and unresolveds to the same responsible principal. No worker is assigned by this proposal.

## 5. Owner coordination and current gates

#7079 was reread open/draft/unmerged at `8271ae320732997be4553957e3e2773d1b9e9f1b`. #7045 was reread open/unmerged, with overlapping API/client/ingestion custody. Neither has been modified by this chunk. Existing CI and source-release holds remain with their owners; old fleet state is not reasserted as fresh measurement.

The planned coordination notes are bounded integration advisories, not execution commissions, requests to expand an existing PR, or permission to acquire reports. Publication is not acknowledgment or accepted interface ownership. Their actual comment IDs and delivery outcome belong in the repository receipt/continuation once returned by GitHub.

One admitted current original remains sufficient for a source-attributed reported-change answer; two separately admitted originals remain necessary for independent reconstruction. Original-report binding, source-use/retention decisions and the authenticated consumer remain unproven here.

Current plugin discovery did not expose the expected Executive ingress. It returned an unrelated provider, which was not substituted. This does not establish that the organization-wide fabric is down. No raw provider launch, worker or watcher was created.

## 6. Reproduction and limits

`probe_discovery_r8.py` plus `probe_client_r8.js` and `r8_fragments/` form the research probe. In a checkout with the pinned corpus, run:

```sh
python research/research_vault_expectations_r3/probe_discovery_r8.py \
  --corpus engine/research_vault/corpus.py --output-dir /tmp/rv-r8-proof
```

The tool refuses a different corpus blob. The downloadable package includes that verified corpus as a test dependency; it is not a second runtime corpus or institutional dataset. Only disposable synthetic databases are created. Node is required for the selected-client-function cases. No packages are installed, network called or provider invoked by the probe.

The full corpus was recovered through ordinary GitHub reads. Public raw-download attempts failed to produce bytes and were not used as evidence. Previously platform-blocked Mac/M1/catalog/Brain-source operations were not repeated or rerouted. No native host processes were launched in R8.

Do not add these 16 checks to R5's 111 tests or the unexecuted 120-task model benchmark. No original report, licensed PDF, full catalog or private portfolio is redistributed. The source code and synthetic fixtures are not a financial dataset.

## Source register

- Corpus: https://github.com/mastermindx-market-intelligence/macro/blob/e86cf4593d2c2603a695ccab858f98ac4a29abae/engine/research_vault/corpus.py
- API: https://github.com/mastermindx-market-intelligence/macro/blob/e86cf4593d2c2603a695ccab858f98ac4a29abae/app/research.py
- Client: https://github.com/mastermindx-market-intelligence/macro/blob/e86cf4593d2c2603a695ccab858f98ac4a29abae/site/research_vault_app.js
- Existing research: https://github.com/mastermindx-market-intelligence/macro/pull/7182
- Incumbent Brain: https://github.com/mastermindx-market-intelligence/macro/pull/7079
- Incumbent hygiene: https://github.com/mastermindx-market-intelligence/macro/pull/7045

**Next action:** consume current owners' interface/custody ruling for this one company-discovery leaf and obtain the permitted source reference for its real consumer proof. Do not spend another chunk merely expanding synthetic comparisons or repeating the catalog count; this characterization already supplies concrete failing requirements.
