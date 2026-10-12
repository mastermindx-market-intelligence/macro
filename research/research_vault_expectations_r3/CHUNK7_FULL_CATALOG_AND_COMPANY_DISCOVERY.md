# Research Vault — Chunk 7: full-catalog measurement and company discovery

**September 16, 2026. Overall institutional-intelligence product: SPEC_ONLY.** This chunk completed a whole committed-catalog measurement and a source-level consumer investigation. It did not admit original PDFs, deploy company search, run a model benchmark, or authorize subscription expansion.

## 1. Decision and useful outcome

The next bounded delivery candidate is **company-qualified institutional evidence that remains findable through the real server-backed search path**, then opens the same permitted source. It is not merely “fill the ticker field.”

The human job is to open an existing Prophet/company context and find research genuinely about that company, with clearly separated related mentions and evidence that explains why it belongs. The machine job is to connect admitted source material to existing issuer/security identities, preserve that association through enrichment and corrections, and expose it through the existing Vault/Brain consumers.

The full vision remains source-grounded expectations, revisions, disagreement, private portfolio relevance, news context and original editorial. This leaf unlocks those uses; it does not replace them with a generic search project. Research remains context, not signal/rank/size/trade authority.

**Capital ruling remains a proposal, not an order:** improve the usable-evidence path on the existing subscription first. Additional accounts must demonstrate marginal useful coverage or timeliness after the same quality and permission checks. Three total accounts remains a hypothesis; the fourth needs its own marginal justification.

## 2. Exact scope, sources and operation

Protected procedure pin: `Mastermind@0fe8074ff953b2ced9025ed40f0f66019c759967`, compatible Skillpack 1.0.1/bootstrap 1. INDEX was loaded and required COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT were reread at this same pin, with blob identities matching the fully loaded procedures already in this conversation.

Implementation/data pin: `macro@459eafb838d9944e58e6a65413e282f2a13826ef`.

Existing research carrier: draft PR #7182, `sol/research-vault-intelligence-design-r2-20260915`; starting head `0633cdb0c8a0753c6940c7df0159a56b51e93eea`. No competing branch, workstream, Job, worker, watcher, provider invocation or runtime authority was created.

Direct-work rationale: PRINCIPAL_JUDGMENT for source/identity/search integration, LOWER_TOTAL_OVERHEAD for one bounded catalog measurement. No background executor or delegated result is implied.

The successful native process was PID 30386, exit 0. It read one pinned public-repository catalog into an isolated temporary research directory, checked its full Git blob identity, parsed the JSON, and returned bounded aggregate results. It did not use the previously blocked M1 route, inspect credentials, change a worktree, alter source data or perform a customer read. Source version, record count and source permission remain different questions.

## 3. Whole committed-catalog measurement

Catalog: `data/research_vault/catalog.json`.
Expected and measured Git blob: `54ed63983248afad543ff46ed327a076d67475b4`.
Bytes: **2,715,583**.
Catalog generation: **2026-09-16T06:09:42.758496+00:00**.
Measurement: **2026-09-16T06:26:52.518547+00:00**.

| Property | Observed count | Share of 2,208 rows |
|---|---:|---:|
| Declared and parsed records | 2,208 | 100% |
| Distinct raw ID values | 2,208 | 100% |
| Nonempty `summary_points` | 2,197 | 99.50% |
| Nonempty `tickers` | **0** | **0%** |
| Nonempty `tags` | 9 | 0.41% |
| Nonempty `desk` | 9 | 0.41% |
| Nonempty `pages` | 2,103 | 95.24% |
| Nonempty `language` | 2,103 | 95.24% |
| `needs_metadata is True` | 0 | 0% |

There are 95 distinct raw institution-field values. The leading raw labels are Goldman Sachs (888), S&T (221), J.P. Morgan (191), UBS (166), Other (109), Deutsche Bank (83), Bank of America (71), and Morgan Stanley (64). Goldman Sachs's label accounts for 40.22% of records, but no alias merge or independent-origin count was performed. In particular S&T was not merged into Goldman Sachs.

The stored `published_at` strings range from July 20, 2026 through September 16, 2026. This is the metadata range, not a verified history of original publication, acquisition or operational availability.

### What the measurement proves

The earlier small-sample concern is now a whole-snapshot field-presence result: **no record in this pinned catalog has a populated ticker field**. The source bytes matched the expected immutable repository blob before the analysis ran.

### What it does not prove

- This is the complete committed catalog, not the canonical live R2 catalog/PDF/corpus/receipt census.
- Field presence is not semantic validity, correct typing, source accuracy, or extraction quality.
- Zero ticker annotations does not mean the text lacks company names or that existing keyword search cannot find companies.
- Not every macro, currency, strategy or sector report should have a stock ticker. The denominator of reports that ought to have company links is still unknown.
- The nine tag rows and nine desk rows were counted separately; this does not establish they are the same nine records.
- Zero `needs_metadata is True` does not make the narrower flag an analytical-quality certification.
- A distinct raw ID value is not proof of a valid canonical ID, unique original PDF, or independent evidence.
- The source-label distribution does not establish the full provider universe, the vendor's daily output, or an unbiased institutional sample.

The exact method and limitations are retained in `catalog_measurement_r7.json`. The raw catalog is not redistributed in this package.

## 4. The consumer problem is larger than the missing annotations

### Server corpus

At the pinned main, `engine/research_vault/corpus.py` defines FTS fields for **title, summary, body and institution**. Its `upsert` copies document ID, those text fields, side, dates and measured PDF metadata. It does not store ticker/tag/desk fields in the searchable row.

Its `search` accepts text, institution and date facets. There is no existing issuer/security subject filter in that function signature. This is implementation evidence, not a claim that no other research-related product has company search.

### API route

`app/research.py::research_search` delegates to that corpus search, then narrows results to catalog-admitted IDs and, for non-Pro users, the fixed preview set. A new subject association must reach an eligible search candidate path, not merely become another catalog field.

The current SQL limit is applied before the route's membership/preview narrowing. A proposed company-retrieval path must account for eligibility and requested subject before its final result budget, otherwise ineligible or unrelated candidates can crowd out eligible results. This is a design requirement; this chunk did not demonstrate a current user-visible starvation incident.

### Browser

`site/research_vault_app.js::matchItem` includes `tickers`, `tags`, and `desk` in its local substring fallback. But when `SEARCH_HITS` is populated, it returns membership in that server-produced ID set instead.

Therefore the fallback and server search consume different fields. Merely enriching the catalog can make an item match the local fallback without making it a server result.

### Concrete, unexecuted counterexample

Assume a fictional report has an admitted annotation `tickers=["ACMEQ"]`, while its title, body, summary and institution contain no literal ACMEQ. With a search for ACMEQ:

1. The local fallback can match the ticker annotation.
2. The current corpus's text search cannot match that annotation alone because it was not stored in its indexed fields.
3. When an empty server-hit object replaces the fallback, the browser no longer admits the report as a hit.

This follows from the inspected code paths. **It was not run against a browser or claimed as an observed production incident.** With zero ticker annotations in the measured snapshot, it is especially important as a regression boundary for the proposed enrichment feature. A ticker that already appears in the source text can still match existing full-text search.

### R6 boundary remains relevant

The ingestion source at this pin still has blob `d005c052ebb76c465d45818db0df8d0b3db79c00`: `_refresh_sidecars` candidacy keys on missing `summary_points`, not on late ticker annotations. Thus the proposed path has two separate gaps:

**Enrichment must propagate into accepted data, and accepted associations must participate in the search the customer actually uses.**

The old code comment that tags/desk are empty everywhere is not a current inventory measurement; R7 measured nine nonempty rows for each. The implemented summary-only trigger is unchanged.

## 5. Use the existing identity owner, not a ticker dictionary

The declared identity seam registry is `config/identity_seams.yml`. It names `lib/dataos/identity.py`, the security master, vendor alias table, issuer master and correction/migration artifacts. Its canonical reader includes issuer/security relationships; it is not permission to mint new identities from research text.

Research should preserve:

- **Issuer-level meaning:** operating performance, business drivers and issuer financial statements.
- **Security/listing-level meaning:** source-specific ratings, share-class price targets and instrument-specific claims.
- **Raw source labels:** the actual ticker/name as written, with source context.
- **Resolved identity evidence:** which existing identity and alias version supports the mapping.
- **Ambiguity:** unresolved or conflicting identity is not silently converted into a confirmed company association.

The registry explicitly limits parts of issuer resolution to current identity rather than general historical issuer lineage. A historical research view cannot blindly apply today's issuer grouping and claim historical proof.

Some source mentions are comparable company peers, suppliers, customers or incidental context. An issuer resolution does not make every mention the subject of the report, and a mention does not establish an exposure or investment recommendation.

The Research Vault should not invoke identity allocators to create a new issuer because a model found a name. Any newly introduced identity-resolving seam must be enrolled under the existing registry's procedure. Identity adoption and source-use permissions remain independent gates.

## 6. Proposed company-evidence contract

This section is a design candidate for existing owners, not a deployed schema or new public API.

### The minimum association

An association ties an existing document/version and a bounded source locator to an existing issuer or security reference. It also carries the original label, supported subject role, identity-evidence version, annotation version, review/verification result, and availability/correction lineage where known.

The initial roles should be narrow and evidence-backed:

- the report or passage is **about** the entity;
- it **compares** the entity with another;
- it **mentions** the entity without establishing it as the subject.

A source-stated dependency may later be carried explicitly as an attributed claim. Do not turn co-mention into an economic edge or a scored beneficiary relationship. These role names are proposed presentation semantics, not newly validated classifiers.

Evidence locations must refer to the source text, not a newly generated summary used to verify itself. A title that unambiguously names a company can support a title-scope association; it does not verify all claims in the body.

### Preserve source text

Do not append ticker keywords to the PDF body or institutional summary to make retrieval work. That would contaminate source evidence, distort search weights and create a misleading source representation.

Store or project accepted associations inside the **existing** corpus/source owner, with explicit metadata semantics and rebuildable indexes. A narrow relation table or equivalent owner-approved representation may be appropriate; no separate vector store, company master, graph authority, permission store or search service is required for this leaf.

### Retrieval order

For a company-specific request, resolve the caller's subject through the existing permitted identity seam; establish source/catalog/tier eligibility; find accepted subject associations plus separately labeled text evidence; apply the requested scope and result budget; then use the existing report reader for exact source support.

Do not mix source-quality, text relevance and market-signal scores into one number. A subject association can determine retrieval eligibility without obtaining trading authority. A plain text match remains useful, but must not be presented as a verified subject association.

If the company cannot be resolved, keep that limitation visible. Broader text search may still help under existing permissions, but is not a secretly successful identity match.

### One result contract across consumers

The server and client should agree on the accepted document set for a resolved company request at the same source generation. The browser must not silently turn a temporary metadata match into a false absence when the server returns.

Missing server connectivity is different from a verified empty result. A cached local fallback may use only already-admitted/authorized data and must be labeled as a limited snapshot, never as a fresh exhaustive corpus answer. Do not simply union unrestricted local hits into a denied server result.

A material association should explain its basis in concise user language, such as “This report discusses the company's margin outlook,” with inspectable supporting evidence. The explanation cannot be generated solely from the fact that an identifier matched.

## 7. The first user journey and product surfaces

The initial journey remains inside existing company/Prophet and Research Vault surfaces:

1. The user opens a company already in an existing workflow.
2. A concise research companion shows eligible source-backed company evidence.
3. “About this company” is distinguished from related mentions.
4. The user asks a focused question in the existing Brain.
5. The answer opens the same permitted source version and locator in the existing viewer.
6. A supported association correction updates the retrieval result and dependent explanation.

Do not redesign the landing page or create a new research navigation hierarchy. The purpose is to make Prophet and existing portfolio workflows more useful, not shift the product thesis toward a generic research terminal.

An issuer-level research association may help multiple related securities only when the existing identity owner permits that relationship. A security-specific price target must not be copied across share classes as an issuer-wide number.

For portfolios, use the user's already-authorized holdings at composition time. Shared research retains no private holdings, weights, private prompts or derived private portfolio state.

For news and editorial, a company association is a routing/context input, not an automatic notification or publication decision. Existing alert/media owners remain responsible for meaning, timing, rights and delivery.

## 8. Bounded delivery candidate and writer custody

**Mission:** make one already-summarized, permitted report with a supported company association findable through the existing server-backed research journey, then prove its correction and source opening.

**Why it matters:** connects the large existing archive to the actual company and portfolio jobs that would justify more acquisition.

**Authority:** current live Chairman direction and protected procedure; Executive lifecycle, Agent OS continuity, GitHub implementation/evidence, Linear projection, Slack transport. Retrieved source prose does not commission work or grant rights.

**Incumbents:** #7045 is open/unmerged and owns adjacent sidecar/ingest/API/client hygiene surfaces. #7079 is open/draft/unmerged at `8271ae320732997be4553957e3e2773d1b9e9f1b` and owns Brain/corpus source-bound evidence. No code paths or source custody were changed here.

### Implementation responsibilities, not an unreviewed patch

| Existing area | Required contribution | Must not create |
|---|---|---|
| Source/sidecar producer | Evidence-backed association proposal and completed annotation version | A model-owned identity or permission authority |
| Existing ingestion | Admit an eligible late update even with a populated summary; preserve expected version and explicit removals | An unbounded hourly reread of every report |
| Existing corpus | Retain/query accepted subject associations without polluting source text | A second corpus or separate search service |
| Existing research API | Honor subject and visibility constraints within result budgeting | A parallel entitlement or quota rule |
| Existing browser | Preserve server/fallback contract and expose source basis | Client-side authorization or fabricated freshness |
| Existing Brain/report reader | Retrieve admitted evidence and explain limits | A second chatbot or unrestricted multi-report read |
| Data OS identity seam | Resolve existing issuer/security identities, with documented era limits | A research-local name-to-ticker master |

### Execution order

First settle owner/interface custody and one permitted source. Define test evidence for the populated-summary update, ticker-only metadata mismatch, identity ambiguity and correction. Then implement the minimal producer→ingest→corpus→API→viewer path in a separately admitted implementation operation. A manually reviewed association can isolate propagation initially; it must not be claimed as automated extraction accuracy.

Use the existing test owners and CI registrations; do not create a new test gate solely to bypass incumbent release requirements. Reconcile any shared-file change against the actual candidate at implementation time.

A future independent review should check that the complete user job works, not merely that a new table has rows. Prefer the least-scarce capable bounded implementation worker when admission is available; Fable is not the default. No worker was dispatched by this document.

## 9. Acceptance criteria: no new benchmark claimed

These are concrete obligations to map into the **existing** R2 evaluation and current product-test owners, not a new competing evaluation program. None was executed in R7.

1. An admitted report whose source text does not contain the ticker is returned through a verified subject association.
2. The populated-summary late-update case actually reaches the corpus and consumer.
3. A same-name wrong company and an ambiguous ticker do not become confirmed associations.
4. Issuer-level and security-specific evidence remain distinct.
5. An older alias/date or current-only issuer mapping does not acquire unsupported historical authority.
6. A supported removal withdraws the wrong company association without losing the source.
7. A stale expected annotation version cannot overwrite a newer accepted association.
8. Repeating an accepted update adds no duplicate association, debit or notification.
9. Client pending/fallback and successful server states do not disagree about the accepted subject hit at one generation.
10. Denied or unavailable server evidence cannot be widened by a client-side union.
11. Eligibility and subject filtering do not lose valid items merely because an earlier global top-k was filled by other records.
12. The answer opens the same source version, or honestly reports changed/unavailable evidence.
13. English and Chinese requests are evaluated for actual cross-language usefulness, not merely token support.
14. No association or explanation changes Prophet signals, rankings, sizing, holdings or execution.

A developer fixture is not source authenticity, license evidence or browser proof. A manually selected pilot does not estimate whole-corpus accuracy. The original-source, 120-task model benchmark and incremental-subscription experiment remain separately uncompleted.

## 10. Pilot and subscription decision

Use a small source-qualified cohort within the existing evaluation set: direct company reports, multi-company comparisons, and negative/ambiguous mentions. Include old-symbol/current-identity distinctions and one correction. Select from available permitted sources after source qualification; no actual cohort was selected by the blocked bulk analysis in this turn.

Do not optimize toward ticker annotations on all 2,208 reports. Some are macro/FX/sector material where “not applicable” is the right result. The applicable denominator and supported associations must be measured before presenting company-coverage percentages.

The useful measures are: source-supported company task completion; correct rejection of wrong-company material; source-opening success; correction propagation; repeat use of the existing company/portfolio workflow; and all-in cost per supported useful result.

For the proposed account pilot, hold the processing route and quality rules constant. Measure separately whether an extra acquisition increment adds a new relevant company, an independent origin, a missing earlier version, better source evidence, or useful timeliness. Source-label count and downloaded-file count are not substitutes.

The 40.22% Goldman-label share is an observed acquisition-profile characteristic, not proof the current allocation is wrong. Additional seats running the same selection policy could reinforce the same profile; diversification is a hypothesis to test, not an automatic benefit of buying more accounts.

## 11. Boundaries, failures and continuation

Successful: one complete pinned catalog was downloaded, byte-verified and measured; corpus/API/client source contracts were traced; the existing identity owner was identified; the correct company-discovery scope was made concrete.

Blocked: an additional native request to fetch the excerpt corpus and Brain source, then a distinct native request for additional local catalog analytics, were blocked because OpenAI could not determine safety status. Neither blocked operation was retried, rewritten for evasion, or routed through another tool/actor. No results are attributed to them. No additional native process was launched after those blocks. Independent bounded repository reads continued.

A Files search for two named reports returned unrelated results, not an original report. Search absence is not evidence that the vault lacks those reports.

Not established: original source/body hashes, source-use grant, exact original report admission, live four-set reconciliation, entity annotation applicability/accuracy, live browser/Brain behavior or marginal acquisition benefit. No new R3/R5 test run, model benchmark, customer read, MarketDesk pull, purchase, provider message or production write.

The raw catalog remains a temporary native research artifact, not a new serving corpus; this report and the aggregate JSON are the durable research result. Do not distribute the entire source archive as part of a research receipt.

**Next action:** reconcile the existing Vault/#7045 and Brain/#7079 source owners and admit one permitted source for the company-qualified discovery leaf. Its first acceptance must include the successful server response replacing the browser fallback, not just local metadata display. Once this path is working, deepen source-attributed revision answers and private portfolio composition through the same evidence owner.

The blocked original-source lane remains explicit. Do not turn another unchanged comparison run into a substitute for source/consumer proof. Do not redo collector recovery (#7164 / Mastermind#631), replace the ongoing CI operation, create an identity registry, or purchase accounts on the strength of field presence alone.

## Source register

All implementation observations below are pinned at `459eafb838d9944e58e6a65413e282f2a13826ef`; PR state is separately observed and mutable.

- `data/research_vault/catalog.json`, blob `54ed63983248afad543ff46ed327a076d67475b4`; whole-file native measurement and connector metadata agree.
- `engine/research_vault/ingest.py`, blob `d005c052ebb76c465d45818db0df8d0b3db79c00`; lines 365–394 reread; prior full inspected helper semantics retained.
- `engine/research_vault/corpus.py`, blob `0b035b34489a4efd2ae7a3c59d153b3d1977701a`; lines 1–425.
- `app/research.py`, blob `bca9b965057df653607765107ef789692c47dcdc`; lines 360–625.
- `site/research_vault_app.js`, blob `1f0b673da6c3d6a44ad3d74b2994f70b9a4311c8`; especially lines 550–690.
- `lib/dataos/identity.py`, blob `d9d5018aac47910bf2c802b1a74114a99511f74f`; lines 1–190.
- `config/identity_seams.yml`, blob `d9de4f2570e94ec80994e0a9c9224c69b253d719`; lines 1–135.
- Current read: https://github.com/mastermindx-market-intelligence/macro/pull/7045
- Current read: https://github.com/mastermindx-market-intelligence/macro/pull/7079
- Research carrier: https://github.com/mastermindx-market-intelligence/macro/pull/7182

For any source path above, the immutable URL is `https://github.com/mastermindx-market-intelligence/macro/blob/459eafb838d9944e58e6a65413e282f2a13826ef/<path>`. This is a citation template, not a new runtime route or acquisition instruction.
