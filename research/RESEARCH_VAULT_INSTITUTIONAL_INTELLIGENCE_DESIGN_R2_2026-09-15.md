# Research Vault — Institutional Expectations and Thesis Intelligence

**Research/design chunk 2 • 15 September 2026, America/New_York**

**Status: SPEC_ONLY — proposed architecture and delivery contract, not implemented or production accepted.**

This document extends the Chairman's Research Vault / MarketDesk investigation. It does not replace the existing Research Vault masterplan, Mastermind AI program, portfolio owner, Market Memory, Chronicle, or media-publication authorities. It creates no Executive Job, new workstream registry, or worker assignment. Recommendations below are design decisions proposed for this program; storage in Git is not implementation approval.

Procedure pin: `mastermindx-market-intelligence/Mastermind@7642aea155d2817219135b24246b55c1d7611c66`, protected master, Skillpack 1.0.1 / bootstrap 1. Implementation inspection pin: `mastermindx-market-intelligence/macro@9579caf3f950f1a2e7b959a9b3b68d26e42e5d06`. Pending Brain evidence candidate: `macro#7079@a0a47535180dc0a60e176818a78ac7ec2c4c462d`.

## 1. Product thesis and the decision being made

The product is **institutional expectations made useful in the user's existing investment workflow**, not a larger PDF shelf or a separately trained financial chatbot.

The human job is: understand what matters to a company, theme, or portfolio; what changed; which credible arguments disagree; and what evidence deserves inspection. The machine job is: preserve source-specific claims, normalize genuinely comparable numbers, detect supported changes, retrieve counterevidence, and supply bounded context to existing products. Prophet remains the flagship. Research adds understanding and challenge; it does not secretly become a new signal model.

The proposed end state has four distinct things: original evidence; source-specific expectations; Mastermind's explicitly labeled analysis; and the user's private research context. None is interchangeable with the others. A source can be accurately quoted and still be economically wrong. An LLM can correctly extract an opinion without earning forecasting or trading authority.

The potential moat is the longitudinal linkage between evidence, assumptions, revisions, relevant official observations, and useful product workflows. The third-party corpus alone is neither unique access nor a guarantee of durable ownership. The moat remains conditional on the actual license, source continuity, evidence quality, and demonstrated user value.

### Capital recommendation

Continue building on the existing corpus. Prefer a provider-approved commercial/bulk allowance when it fits the use case; permitted additional accounts are another purchasing form, not a strategy for bypassing a shared restriction. Treat three total accounts as a planning hypothesis, not an approved order. Evaluate the second, third, and fourth increments separately. Four seats on one provider do not diversify upstream provider risk.

Account growth and product quality must be evaluated independently. More documents can improve coverage while leaving answer quality unchanged; better retrieval can improve answers without another subscription. The crossed experiment in section 12 distinguishes these effects.

## 2. What this chunk newly established

| Finding | Evidence and consequence |
|---|---|
| The pending Brain work is narrower than the complete desired journey. | #7079 supplies source-bound passages and locators, but its R1B design explicitly leaves viewer page/query-fragment consumption for a later repair. Opening a document is not proof of opening the cited passage. [S1] |
| A source-type interpretation defect has an incumbent owner. | At the pinned main, `scripts/build_research_pages.py` maps `side=buy/sell` to `BUY/SELL` badges. Open PR #7045 addresses the desk-type/rating confusion and related hygiene. Do not write a competing fix. [S2–S3] |
| Research-to-media infrastructure already exists. | The triage runbook maps catalog → deterministic triage → optional demotion-only model → press planner and media outputs. It documents disabled/dark controls and a cold-start volume ceiling. That is implementation/contract evidence, not fresh activation evidence. [S4] |
| Chronicle already includes the vault. | Chronicle's deterministic context spine consumes the research catalog and other source-owned events. Do not create another timeline or have the hourly collector advance Chronicle. [S5] |
| Market Memory is not a blank graph database. | Its composition and point-in-time interfaces preserve existing source owners. The inspected immutable-source module has a specific ALFRED CPI intake, not blanket admission for broker PDFs. A research adapter needs its own accepted mapping through the existing owner. [S6–S7] |
| The current corpus reader has a scale-sensitive transfer pattern. | The process-wide read-through cache has a 300-second TTL; an expired copy triggers a whole-corpus byte fetch on a subsequent call. This is a code-path observation, not measured production bandwidth. [S8] |
| The basic live id-set census already exists. | `scripts/research_vault_census.py` compares catalog, PDFs, corpus, and processed receipts. Exit 0 means the census ran, not that every set matched. Reuse it; do not build a duplicate checker. [S9] |

The preceding chunk's 2,196 completed records, 70 recorded downloads in 24 hours, source concentration, and missing historical timestamps remain **earlier measured baseline data**, not freshly remeasured values. A bounded new host-side census request in this chunk was blocked before a result was returned. It was not retried through another carrier. No new claim of live corpus, viewer, or processing health follows from this chunk.

Search did not establish a later canonical Research Vault intelligence workstream record. Keep this as a linked proposal under the existing Research Vault and Mastermind AI owners; do not invent a registered WS identifier. The source-recovery operation closed by Mastermind #631 / macro #7164 is do-not-redo.

## 3. The core unit: a source-bound expectation, not a document summary

A paragraph saying “AI demand remains strong” loses too much information. A useful research object instead says who made which claim, about what, for which period, on which basis, with which evidence, and whether the claim replaced an earlier statement.

Keep the following semantic categories distinct:

| Category | Meaning | Prohibited shortcut |
|---|---|---|
| Source identity / desk type | Publisher, institutional parent, desk, author, aggregator, buy-side/sell-side/independent. | `sell-side` does not mean `sell recommendation`. |
| Reported observation | A source states something happened or was measured. | A bank's statement is not automatically an independently verified fact. |
| Forecast | A source predicts a value/range for a defined period and scenario. | An estimate is not a realized observation. |
| Opinion / thesis | A source advances an interpretation or business argument. | Strong wording is not calibrated confidence. |
| Analyst rating / target | A specifically sourced recommendation using the source's scale and horizon. | Do not derive it from desk type, sentiment, or price-target direction alone. |
| Mastermind calculation | Deterministic arithmetic over named comparable inputs. | A valid calculation does not validate the inputs or imply a trading action. |
| Mastermind synthesis | An interpretation supported by cited source claims. | Do not relabel it as an institutional statement. |
| Mastermind market signal | Output of an existing admitted, evaluated signal owner. | Research context cannot alter that owner implicitly. |

### Minimal claim contract

Use existing canonical document and entity identities. Any new fields or tables remain additions under the Research Vault source/corpus owner; the names below describe concepts, not deployed schemas.

**Identity:** existing report ID; source version/content hash; extraction version; stable claim identity within that version; institutional parent, desk, author when supported; original versus quoted origin; canonical company/segment/theme ID when resolved.

**Meaning:** statement category; original source wording or bounded evidence pointer; normalized metric; accounting definition; consolidated/segment scope; value or range; original unit and currency; fiscal/calendar period; scenario; source-stated assumptions and conditions. Preserve original and normalized representations separately.

**Evidence:** original document/version; page when genuinely known; extraction block or table row/column; exact character span in that extraction; source and extracted-body hashes; evidence method; coverage and unsupported regions. A text locator must open the same version it describes.

**Time:** source-authored time; provider-posted time; first observed metadata time; first accessible source-byte time; derived-object production time; first eligible product availability; target period; correction time. Unknown clocks stay unknown.

**Quality and access:** source-bound verification result; extraction defects; unresolved identity; applicable license/grant reference; audience, purpose, processor, and retention constraints. These are eligibility and evidence properties, not a numeric investment-confidence score.

### Numeric comparison key

A numeric pair is directly comparable only after agreement on:

`entity + scope/segment + metric definition + unit/currency basis + target period + scenario + accounting basis`.

Then attach source and vintage. Same-source changes are revisions; different-source values are disagreements. Different periods or definitions are `not comparable`, not contradictions. Currency conversion, fiscal/calendar alignment, split adjustment, or annualization requires an explicit accepted transform and input vintage. Do not silently interpolate missing quarters.

Null is not zero. No observed new note does not mean a source reaffirmed its old view. Omitted guidance is not an unchanged estimate. A quoted prior value is not a complete independent historical source version unless the system actually holds that version.

## 4. Seven product capabilities from the shared evidence

### 4.1 Company expectations sheet

On the existing company or Prophet detail surface, maintain a compact matrix of captured estimates for the business drivers that matter: revenue, operating margin, capex, deliveries, capacity, orders, or another company-appropriate metric.

Each row shows source, period, basis, current captured estimate, prior comparable estimate when available, exact change, relevant stated assumption, and evidence link. Show a spread or median only for a sufficiently defined comparable captured sample, with the sample count and coverage; never label the sample “the Street” without a defensible coverage basis. Different periods occupy different rows.

**User value:** instantly see where the argument differs, without reading every report. **Learning:** whether users resolve a real comparison task correctly and faster. **Proof:** a real source revision appears correctly, and a noncomparable forecast is excluded from the arithmetic but remains inspectable.

### 4.2 Thesis and counterthesis brief beside Prophet

For a company already selected by Prophet, produce a small research panel: the business thesis, the material change, the strongest captured counterargument, and the next observable item needed to examine the disagreement.

The counterargument is retrieved from actual contrary evidence; it is not invented to make every card symmetrical. When no supported counterargument is available, say the coverage is limited rather than manufacture balance. A major adverse business argument is not suppressed because it conflicts with the existing signal.

**User value:** understand and challenge a signal. **Boundary:** no new rank, conviction blend, entry timing, sizing, or suppress/override gate. **Proof:** research refresh leaves Prophet signal and score artifacts byte-identical while the explanatory panel changes.

### 4.3 Private portfolio assumption map

Extend the existing portfolio brief: identify which held businesses have documented reliance on a shared assumption, such as investment spending, pricing, utilization, input cost, financing, or delivery timing.

The map combines existing, source-owned company relationships with research assertions. It may explain that several holdings share a documented assumption; it does not invent a numerical loss scenario or a new “risk score” from graph connectivity. Existing quantitative exposure, correlation, and portfolio math owners remain authoritative. Keep direct exposure, indirect asserted relationships, and unresolved mappings distinct.

**User value:** discover that apparently different positions may rely on the same business belief. **Privacy:** compose against the user's existing holdings at request time; do not write holdings, position values, private prompts, or portfolio-derived claims to the shared corpus. **Proof:** two users get distinct private briefs with no cross-user cache contamination, and an unsupported ticker is clearly uncovered.

The internal portfolio bot is a separate consumer from the public chatbot. Its first admission is read-only evidence and review context, not execution, sizing, or ranking. An upstream evidence grant must not be inferred from possession of a tool.

### 4.4 Research-aware news and change briefs

For a newly arrived report, distinguish: new external fact; changed estimate; changed argument; first source coverage; corroborating repetition; older research arriving late; extraction repair; and source correction.

Only a supported meaningful change should enter an eligible user-facing research update. Reprinting the same underlying forecast in a note, a news story, and an AI summary does not create three independent confirmations. Ordinary repetitions remain searchable without creating notification noise.

The existing news/press/alert owners determine publication and delivery. Where an existing alert class cannot represent a change, propose an additive source-bound presentation contract to that owner; do not create a private alert system or route an LLM label into a calibrated escalation key.

**User value:** “what changed that matters,” not 200 inbox notifications. **Proof:** repeated summaries produce no additional alert; a correction amends the earlier item through the established publication owner; an old note is labeled late-arriving context, not breaking news.

### 4.5 Earnings and release expectation-versus-observation bridge

Prepare a pre-event sheet from eligible estimates. After a source-owned actual release arrives, compare the same period, metric, and basis and explain where results differed from the captured expectations.

Connect to existing earnings, release-truth, and company financial-data owners. Do not turn broker estimates into the official consensus dataset; do not silently overwrite official figures with numbers quoted in research. Distinguish first-release and revised official observations. A release can support one part of a thesis while leaving another unresolved.

**User value:** explain a surprise in business terms, not simply quote a beat/miss percentage. **Boundary:** institutional narratives do not automatically repair or alter Release Radar's statistical forecast. **Proof:** the comparison uses the correct historical estimate and actual release vintage, with unavailable or mismatched metrics explicitly excluded.

### 4.6 Multi-source Mastermind AI investigation

Keep the existing Brain as the orchestrator. It should choose an evidence plan appropriate to the question: exact lookup; table calculation; same-source revision; cross-source comparison; broad theme synthesis; or historical reconstruction.

Start with the current exact lexical and source-bound read. Add context-preserving passages; evaluate hybrid retrieval and reranking only against failed useful tasks. For broad questions, traverse bounded source-backed relations, collect representative evidence and dissent, and disclose sampling. The planner uses a work budget; it does not recursively generate a research project for every casual question.

Every final material statement should be classifiable as sourced, calculated, or interpreted. Citation validity, support, and completeness are separate checks. A citation that exists can still fail to support the sentence. Multi-step generated intermediate text must remain traceable back to the original evidence; do not verify a summary using only a prior summary. [W1–W5]

**User value:** ask a complicated question without manually selecting all reports. **Proof:** the answer handles evidence gaps, correct arithmetic, contradictory sources, quota limits, and historical timing—not just a successful fluent response.

### 4.7 Original editorial and distribution outputs

Reuse the existing press and media owners. A public piece should contribute an original synthesis, first-party corroboration, or a clear explanatory comparison—not lightly paraphrase an entire restricted report.

The first distribution experiment should have one flagship original brief and one existing product destination, such as a public-safe demonstration leading into a Prophet or portfolio workflow. A new CMS, multiple social brands, and mass daily publishing are not prerequisites. The documented media cold-start ceiling is an upper bound, not a required output target. Do not arm dormant channels as part of this design operation.

Public, subscriber, and internal outputs are independently permissioned. A subscriber brief cannot simply be copied to X. Removing the bank's name or rewording its text does not itself resolve permission questions. Keep human editorial review until both quality and rights handling are established.

**User value/business value:** demonstrate Mastermind's interpretation and useful workflow before requiring a subscription. **Learning:** engaged visit → meaningful product interaction → voluntary signup → repeated use → paid conversion, using existing analytics and consent controls. Views alone do not prove value. **Proof:** one lawful, accurate, useful piece is published through the existing owner and its product path actually works.

## 5. Worked example: why this is more than summarization

**Entirely fictional design fixture. No row below describes a real company, institution, report, or market forecast.** All numbers are USD billions except margins. The fictional company's FY2027 ends September 30, 2027.

| Captured source | Target period | Revenue | Operating margin | Treatment |
|---|---|---:|---:|---|
| Broker A, earlier note | FY2027 | 48 | 31% | Earlier comparable A vintage. |
| Broker A, later note | FY2027 | 51 | 28% | A revision, not an extra current source vote. |
| Broker B, latest note | FY2027 | 49 | 30% | Comparable independent source estimate, subject to source-origin verification. |
| Broker C, latest note | CY2027 | 53 | 32% | Different period: no direct numeric comparison. |
| Article quoting Broker A | FY2027 | 51 | 28% | Secondary citation of A, not independent confirmation. |

Deterministic arithmetic over A's two comparable notes:

- Revenue: `51 / 48 - 1 = +6.25%`.
- Operating margin: `28% - 31% = -3 percentage points = -300 basis points`.
- Implied operating income: `48 × 31% = 14.88` before; `51 × 28% = 14.28` after.
- Change in implied operating income: `-0.60 billion`, or approximately `-4.03%`.

The useful insight is that the higher revenue forecast converts into lower implied operating profit in A's updated model. The system should not summarize it as an unqualified “bullish upgrade.” It must not substitute operating income for EPS or net income, and none of this arithmetic is a trading recommendation.

The same verified change can feed a Prophet explanation, the company expectation sheet, a private portfolio brief, an AI answer, and—only with appropriate rights—an original educational discussion. It is extracted and checked once, then projected under each consumer's own rights and context.

A source correction from `28%` to `29%` would supersede the erroneous extraction/version or source claim as appropriate. All dependent calculations and briefs must be invalidated or regenerated. The original historical answer is not silently rewritten into a record claiming it knew the corrected figure earlier.

## 6. An evidence graph, not a second knowledge authority

Start with relational claim/version/evidence references inside the vault owner. A graph is initially a queryable projection of those references; a separate graph database is not a prerequisite.

Useful relation types are: report-version-of; extracted-from; authored-by; quoted-from; about-entity; same-comparison-key; revises; explicitly-reaffirms; supports; conflicts-with; depends-on; corrected-by; and observed-by-existing-data-source.

Keep relation provenance explicit. Exact source references and normalized numeric keys can be deterministic. Semantic support, contradiction, and dependency extraction are model-assisted proposals until evidence checked. A source's causal argument remains a source's argument, not a proved causal effect. Co-mention edges may help retrieval but are not economic relationships.

Three different notions of independence matter: independent publication identity; independent author/desk; and independent underlying evidence. An analyst team can publish five updates using one management comment. Treat that as one lineage plus updates, not five independent observations. Unknown independence is unknown; a branded publisher name is insufficient proof.

Admit a graph-assisted retrieval approach only when it materially improves the held-out broad-query task family against simpler methods at an acceptable cost. Microsoft's distinction between local and global query needs, and its work deferring expensive graph summarization, are useful precedents—not Mastermind benchmarks or a reason to adopt a new vendor stack. [W3]

## 7. Temporal behavior and correction propagation

The system needs both a view of the world described by a claim and a view of what Mastermind actually knew. Avoid a single ambiguous `date` or `latest` field.

**Current interpretation:** most recent comparable source claim actually captured, eligible, and not superseded or withdrawn. Print its age. This is not a claim that no newer report exists elsewhere.

**Operational point-in-time:** only source bytes and derived material that were available to the relevant system/consumer by the requested instant are eligible. Newly extracting an old PDF today does not prove that its extracted feature was used last month. Explicit replay with today's extractor is a different result from reconstructing the historical production answer.

**Public reconstruction:** may use independently evidenced historical public availability under the existing Market Memory mode and rules. The date printed inside a report is not, by itself, proof of when it was publicly or contractually accessible. Unknown availability must not be backfilled into an operational-PIT claim.

**Corrections:** distinguish a publisher revision, provider metadata correction, our extraction repair, and a rights withdrawal. They have different meanings and affected outputs. Preserve source versions where permitted, append correction lineage through the existing owner, and invalidate only dependent material. Keep retrieval indexes and graph projections rebuildable.

**Publication race:** pin source/corpus/catalog versions per request. A corpus row preceding catalog publication is not authorized visibility. A citation built from one body version must not open another version without a clear changed-source disclosure.

**Retention:** source rights determine what can be kept. Deletion must reach evidence chunks, indexes, embeddings, graph-derived restricted content, cached answers, exports and generated derivatives where applicable. A non-content tombstone is retained only when allowed. Do not promise eternal institutional memory without retention rights.

## 8. Integration map and no-rebuild boundaries

| Existing owner | Proposed contribution | Must remain unchanged without its own accepted amendment |
|---|---|---|
| `collectors/marketdesk_extractor/` | Permitted acquisition capacity, source metadata, selection telemetry. | One collector/queue/profile owner, actual vendor entitlements, no limit bypass. |
| `engine/research_vault/` | Evidence extraction, source versions, comparable claim annotations, source-opening references. | Existing document identity, R2/source custody, catalog visibility and corpus authority. |
| `engine/neuralweb/brain_market_intel.py` / Brain gateway | Bounded evidence planning and multi-source projection. | Existing tool allowlist, entitlements, quota accounting; no new chatbot. |
| Existing Prophet surfaces | Explanatory research panel. | Signal/board/score/rank/sizing unchanged. |
| Existing company/theme owners | Canonical entity/segment/relationship references and verified official inputs. | No generic graph-derived beneficiary or exposure authority. |
| Existing portfolio context/brief owners | Private composition and supported shared-assumption explanations. | Private holdings, RLS, existing quantitative math, no automated order authority. |
| Existing news / Macro Alert Center | Source-bound material-change presentation where admitted. | No private alert/event/score system or novel model escalation key. |
| `engine/chronicle/` | Existing timeline and context-pack consumption. | Nightly advancement remains with its owner; no hourly Chronicle writer. |
| Market Memory | Accepted contextual joins and eventual registered PIT adapter. | No new general market-state history, no automatic broker-source admission. |
| Existing press/media/mailer owners | Rights-cleared original outputs and approved distribution. | Current editorial, consent, suppression, publication, and volume controls. |
| Existing cost/evaluation/analytics owners | Resource spend, quality and useful customer outcomes. | No new cost ledger, lifecycle, or private user telemetry store. |

The operational CXI corpus is not the financial research corpus. Reuse permitted implementation primitives and source/evidence conventions, not internal corpus contents. Public/subscriber AI must not inherit internal-repository retrieval merely because the same Brain orchestrates both.

## 9. Query, entitlement, and evidence-envelope design

Do not mint a public API or new tool prematurely. First specify the additive result needed by existing consumers, then freeze an interface with their owners.

A conceptual analysis envelope carries: subject and question; request mode and cutoff; selected source and extraction versions; allowed source-backed claims; comparable changes; disagreements and noncomparability reasons; deterministic calculations and inputs; coverage and limitations; evidence locators; freshness; and existing authority flags stating context-only/no rank/no size/no trade.

An audience/purpose check occurs before retrieval, with output checking afterward. Mixed-source summaries inherit applicable restrictions from their supporting evidence. Where a claim can be independently supported by an authorized source, regenerate using that authorized basis instead of laundering a restricted summary. This is not a license interpretation rule; the license owner must establish the permissions.

Pro membership is a product entitlement, not proof of upstream redistribution or AI-processing rights. Background global extraction needs an appropriate service-use grant. It must not masquerade as a customer's metered report read. Conversely, an interactive multi-report answer must respect existing per-report access and view accounting; one answer cannot turn several restricted report reads into an unlimited free read.

Caches must be segregated by source versions and access context. Private portfolio responses are not globally shared. Denied requests must not leak restricted counts, snippets, graph edges, embeddings, or query-conditioned existence. The exact no-match/debit behavior of #7079 remains binding until its owner accepts an amendment.

Retrieved text is untrusted data. It may not authorize tools, request secrets, send messages, edit a portfolio, or change access rules. Model-produced query plans operate only within the existing allowlisted tools and bounded budget.

## 10. Cost-aware processing and scale

### Processing stages

Preserve permitted original bytes and metadata under the existing owner. Use native text extraction first, retaining page structure. Use deterministic parsing for units/dates and repeatable checks for numeric normalization. Tables retain headers, footnotes, period labels, and row/column relationships. Image-heavy regions need explicit extraction coverage; use selective visual interpretation where required and OCR only as a last resort. An absent text layer does not justify claiming that a chart contains no information.

Do cheap classification and selection first. Spend deeper model capacity on reports whose content can serve a named product need, close a missing historical link, supply an independent source, or answer a failed query. Preserve the ability to revisit unmodeled source content later. Selection must not filter out bearish evidence just because Prophet currently favors a stock.

Check source identity and math deterministically. Verify high-consequence semantic outputs against the actual source, not only against intermediate summaries. Log extraction/processing cost through existing owners. Reuse source-verified claims across compatible consumers rather than parse each PDF independently for every feature.

### Illustrative monthly workload, not a forecast or vendor quote

Assume 200 acquired documents/day for 30 days. These workload numbers are design assumptions; no new model throughput or pricing benchmark was run.

| Stage | Runs/month | Input tokens/run | Output tokens/run |
|---|---:|---:|---:|
| Lightweight processing | 6,000 | 2,000 | 200 |
| Deeper extraction for 25% | 1,500 | 12,000 | 1,000 |
| Extra difficult-document escalation for 5% | 300 | 20,000 | 2,000 |
| Change comparisons | 900 | 6,000 | 600 |
| Focused evidence verification | 1,500 | 2,000 | 300 |

These stages include additional passes for overlapping documents; their tokens are intentionally counted separately. Total: **44.4 million input tokens and 4.29 million output tokens/month**. At illustrative blended rates of $0.50/$3, $1/$5, or $3/$15 per million input/output tokens, respectively, the modeled generation component is **$35.07, $65.85, or $197.55/month**. These are sensitivity points, not available model prices or quality promises.

The total budget must additionally include subscriptions, embeddings, visual token expansion, retries, user-time answering, storage/transfer, evaluator and editorial labor, and opportunity cost on shared hardware. Consumer subscriptions are not an assumed unlimited unattended batch-compute license. Current model/processor permission and actual provider pricing must be verified before selecting the route.

### Long-term scale scenario

At a hypothetical 200 documents every calendar day: 73,000 documents/year. At an assumed 2 MB per PDF: approximately 146 GB/year of original PDF bytes before replicas. At 15 extracted claims/document: approximately 1.095 million claim rows/year. At 30 embedded chunks/document, 1,024 dimensions, and two bytes/dimension: about 4.49 GB of raw vectors before indexing/metadata/replicas. None of these assumptions has been measured against the live corpus.

This scale does not by itself justify a new platform or hardware purchase. It does justify measuring long-report coverage and the existing whole-corpus refresh pattern. First consider checking a canonical publication generation before unchanged refreshes. If transfer/refresh/reader performance subsequently demands incremental or bounded-shard publication, implement it under the same corpus owner with version-pinned reads and rollback. Do not solve a cache-transfer problem by launching another source-of-truth database.

## 11. Acquisition should optimize marginal coverage, not prestige or volume

Keep the existing allocator as the sole acquisition decision owner. Subject to the vendor's permitted usage, extend its inputs with evidence of product demand and missing coverage—not return predictions.

A candidate's usefulness can come from a missing company/driver, a missing prior report needed for comparison, a genuinely independent viewpoint, an authoritative correction, a relevant longer-horizon thesis, or an unanswered user task. Repetitive summaries, generic aliases, already-covered versions, and low-applicability reports should not consume capacity merely to approach a daily maximum.

A bounded exploratory sample from underrepresented source/topic strata can help reveal what the current prestige/keyword policy systematically misses. Treat allocation weights or sampling proportions as experimental settings requiring evaluation, not newly validated optimal policy. Record selection reasons and coverage denominator. Do not use subsequently observed stock returns to choose which historical notes count as valuable.

Measure separate sets: provider items observed; policy-eligible; acquired source bytes; stored; catalog-admitted; searchable; verified evidence; useful product output. Reuse the existing four-set census for its actual scope, then join collector/extraction/product evidence at a documented watermark. Different generations can produce a legitimate short-lived mismatch. A completed diagnostic command is not proof of set equality.

Recompute demand using actual allowed rolling windows and timezone-aware local calendars. Earlier daily sample averages are not rolling-capacity guarantees. A fourth account may buy freshness or historical continuity even when a monthly volume average fits three accounts; it may add little when relevant coverage is already complete. These are measurable hypotheses.

## 12. Crossed experiment: subscriptions versus intelligence quality

Freeze business questions before selecting incremental reports. Use source-family/company/date-blocked evaluation splits, not random pages from the same report on both sides. Separate permission/conformance tests from research-answer quality.

The acquisition experiment compares a frozen baseline acquisition policy and its realized baseline corpus with the permitted expanded corpus. The processing experiment compares the existing research path with the proposed path. Run the same held-out tasks through all four cells:

| | Existing processing | Improved evidence/comparison processing |
|---|---|---|
| Baseline corpus | A | B |
| Expanded corpus | C | D |

`B - A` estimates the processing contribution on the old corpus. `C - A` estimates the acquisition contribution with old processing. `D - B` estimates the additional-corpus contribution after the improved system. `D - C` estimates the processing contribution on expanded coverage. Differences are conditional on the sample and design, not automatically causal effects for future users; common tasks, frozen routes and blinded grading reduce confounding.

The per-account question is marginal: baseline → second capacity increment; second → third; third → fourth. Do not justify a fourth account with the cumulative benefit of all three additions.

### Evaluation set and metrics

Propose 120 held-out research tasks: 20 exact fact/identifier; 20 numeric/table; 20 cross-source comparison; 20 temporal/revision; 20 bilingual; 20 end-to-end product tasks. Add a separate adversarial/conformance suite for identity, source drift, rights, privacy, quotas, prompt injection, missing coverage, and false authority. This is a proposed test plan, not an existing labeled dataset or executed benchmark.

Primary metrics: supported useful task completion; correctly handled unanswerable tasks; critical factual/numeric/temporal error rate; citation support and completeness; retrieval coverage; time to inspect the evidence; and cost per supported useful completion. Report all denominators and source-family dependence. Grade facts and citations with human adjudication for a representative sealed sample; an LLM judge alone is insufficient proof.

Secondary metrics: uncovered-company reduction; new independent origin coverage; useful revisions recovered; selected-report freshness; source-opening success; repeat user use; and incremental subscription-plus-processing cost. Do not optimize raw claim count, citation count, note count, or generated words.

A zero-error result on a small test set does not establish zero risk. Even with an unrealistic independent-identically-distributed assumption, zero failures in 120 observations gives a one-sided 95% upper failure bound of about 2.47%; clustered financial tasks can provide less independent information. Use observed test results honestly and extend the suite after deployment.

### Proposed purchase rule

Recommend an increment only after the necessary rights are documented, the end-to-end pipeline works, and blinded paired tasks show a material useful coverage/quality or latency improvement at an acceptable total cost. Record a minimum worthwhile improvement and evaluation horizon before the pilot, once the baseline task mix is measured; do not invent an economically universal percentage in advance.

Source records may have long-term option value beyond current usage, but record that strategic value separately from demonstrated customer benefit. Avoid annual commitments until useful consumption and permitted retention are clear, unless the provider's actual offering makes the alternative impossible and a separate decision accepts the trade-off.

## 13. Rights and commercial diligence packet

Public research confirmed the MarketDesk landing uses ZeroHedge Professional login. It did not establish current commercial grants, pooling rights, current prices, a complete worldwide institutional universe, or the claimed private ZeroHedge LLM/graph implementation. Search results for similarly named apps are not applicable evidence. [W6]

The procurement question is not merely “how much is another seat?” Ask the vendor to specify the agreement and permitted source scope for: automated acquisition; pooled/multiple-account usage; a commercial/bulk allowance; retained originals; parsing and embeddings; internal RAG; use of external model processors and their retention; customer-facing generated answers; customer PDF/view/download access; original public commentary; structured derivative datasets; permitted quotation/charts; post-termination retention; and deletion/revocation propagation.

Request separate quotes for (a) internal-only research intelligence, (b) generated customer-facing analysis without original-report redistribution, and (c) original-report access for customers. A provider may authorize only some of these; the architecture and economics must support that outcome rather than assume all three are bundled.

No vendor contact or purchase is performed by this document. A draft request can be prepared, but sending it requires an authorized recipient and explicit communication action. Contract review belongs to the appropriate business/legal owner. Attribution, an internal label, or a Pro gate does not substitute for a documented grant.

Where a use is not licensed, design and tests can use expressly permitted public first-party material or synthetic fixtures. That preserves momentum without transforming rights uncertainty into a license assumption.

## 14. Bounded delivery sequence

These are candidate waves, not dispatched jobs. Each future commission must re-pin source law, reconcile active owners, use the existing admission/routing path, and preserve one carrier. No actual worker has been assigned by this document.

| Wave | One observable capability | Main dependency | Acceptance and production proof |
|---|---|---|---|
| R0 — source/coverage qualification | An operator can distinguish known, acquired, searchable, source-verifiable, and permitted material. | Authorized read path and actual agreement/permissions. | Existing census completes; mismatches classified by generation; selected sample source coverage measured; rights per use recorded. No silent repair. |
| R1 — finish source inspection | A permitted AI answer opens the correct evidence in the existing viewer. | Existing #7079 and #7045 ownership/release reconciliation. | Exact source version/page or honest locator fallback; allowed/denied/no-match/quota paths; EN/ZH; source-label semantics; browser proof. |
| R2 — one comparable revision | User sees a real same-source numeric change with evidence and arithmetic. | R1 plus source-grounded extraction/period normalization for a narrow metric family. | Earlier/later notes compared; different period rejected; correction propagates; no research-inferred rating. |
| R3 — Prophet research companion | Existing Prophet detail explains one material change and supported counterevidence. | R2 and existing Prophet presentation contract. | Real selected company journey; source inspection; stale/absent/conflict states; signal artifacts unchanged. |
| R4 — bounded multi-source answer | Brain answers a comparison across permitted reports and preserves disagreement. | R2 and existing tool/access budgets. | Two or more real sources; no duplicate-origin vote inflation; not-comparable row; citation support; accounting and privacy proof. |
| R5 — private portfolio composition | Existing brief explains a supported shared assumption for actual private holdings. | R3/R4 and existing portfolio schema/rights mapping. | Owner-scoped read; request-time composition; isolation across users; null ticker coverage; no execution path. |
| R6 — acquisition-value pilot | A purchasing decision has marginal coverage/quality/cost evidence. | Rights, R3/R4 usefulness, a permitted expanded sample. | Frozen crossed experiment; selection logs; blinded results; rolling-window coverage; separate second/third/fourth decisions. |
| R7 — news/editorial reuse | Existing publication owner delivers one lawful, useful original output from verified evidence. | Source rights, evidence quality, existing publication/channel gates. | Correction handling, quiet repetition, actual destination journey, and existing analytics receipt. |
| R8 — longitudinal learning | Historical expectation evolution can be queried honestly and studied prospectively. | Admitted Market Memory adapter and sufficient forward data. | Operational PIT and reconstruction distinguished; versioned comparisons; held-out evaluation; no silent signal promotion. |

R1 is not a new competing repair branch. R0, external licensing diligence, synthetic contract examples, and offline evaluation design can advance without modifying the incumbent #7079/#7045 code paths. Cross-company/sector breadth and a giant graph are not prerequisites to the first useful R2→R3 vertical.

### Stop/escalation rules

Stop the affected lane on unresolved source identity, missing required rights, effect uncertainty, conflicting writer custody, corrupted evidence, or an attempted authority expansion. A generic summary is not an acceptable fallback for a fabricated exact number. Never repair a failed data proof by relabeling it complete. Continue independent design/evaluation lanes where safe and authorized.

## 15. Acceptance doctrine and continuation

The first high-value vertical is complete only when a real permitted report change reaches an existing user surface, preserves source/period/units, can be inspected, survives a correction, respects privacy/quotas, and leaves signal authority unchanged. Code, CI, deployment, successful source access, and customer completion are separate evidence steps.

This chunk completes a **design artifact and source-ownership investigation**, not a production feature, an account-expansion decision, or the entire program. The next bounded task is to qualify a small permitted corpus around one company/metric family using the existing census and source-opening path, then freeze the R2 comparable-revision contract and its test cases with the incumbent Brain/Vault owners. Licensing diligence and evaluation labeling remain parallel dependencies. Do not redo the collector recovery, launch another graph/chat system, change #7079/#7045 unilaterally, or buy accounts under this design artifact.

## Source register

Source descriptions distinguish inspected implementation from proposals and vendor/research claims. Repository links are immutable except deliberately identified PR state links.

- **S1:** Pending Brain PR #7079 and its R1B design. https://github.com/mastermindx-market-intelligence/macro/pull/7079 ; https://github.com/mastermindx-market-intelligence/macro/blob/a0a47535180dc0a60e176818a78ac7ec2c4c462d/research/MASTERMIND_AI_SOURCE_BOUND_EVIDENCE_R1B_DESIGN_2026-09-13.md
- **S2:** Current report renderer semantics. https://github.com/mastermindx-market-intelligence/macro/blob/9579caf3f950f1a2e7b959a9b3b68d26e42e5d06/scripts/build_research_pages.py
- **S3:** Existing source-type/facet repair PR, observed open. https://github.com/mastermindx-market-intelligence/macro/pull/7045
- **S4:** Research triage/media runbook; historical quantities are not current measurements. https://github.com/mastermindx-market-intelligence/macro/blob/9579caf3f950f1a2e7b959a9b3b68d26e42e5d06/docs/research_triage.md
- **S5:** Existing Chronicle ownership and consumers. https://github.com/mastermindx-market-intelligence/macro/blob/9579caf3f950f1a2e7b959a9b3b68d26e42e5d06/engine/chronicle/__init__.py
- **S6:** Market Memory composition and temporal interfaces. https://github.com/mastermindx-market-intelligence/macro/blob/9579caf3f950f1a2e7b959a9b3b68d26e42e5d06/engine/neuralweb/market_memory.py
- **S7:** Bounded Market Memory source intake. https://github.com/mastermindx-market-intelligence/macro/blob/9579caf3f950f1a2e7b959a9b3b68d26e42e5d06/engine/neuralweb/market_memory_sources.py
- **S8:** Existing corpus source/body and read-through cache. https://github.com/mastermindx-market-intelligence/macro/blob/9579caf3f950f1a2e7b959a9b3b68d26e42e5d06/engine/research_vault/corpus.py
- **S9:** Existing read-only four-set census. https://github.com/mastermindx-market-intelligence/macro/blob/9579caf3f950f1a2e7b959a9b3b68d26e42e5d06/scripts/research_vault_census.py
- **W1:** Anthropic, Contextual Retrieval, September 19, 2024. Methodological precedent only; benchmark gains are not transferred to Mastermind. https://www.anthropic.com/engineering/contextual-retrieval
- **W2:** AlphaSense, broker-research workflow and structured-financial integration documentation, inspected September 15, 2026 ET. Product claims are not independent proof of accuracy or a license available to Mastermind. https://www.alpha-sense.com/solutions/broker-research-reports/ ; https://help.alpha-sense.com/hc/en-us/articles/48564174120595-Financial-Data-Integration-into-Generative-Search
- **W3:** Microsoft Research, LazyGraphRAG, November 25, 2024, updated June 6, 2025. Architectural precedent; no adoption or performance equivalence claimed. https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/
- **W4:** Gao et al., ALCE, EMNLP 2023. Evaluation distinction between answer correctness and citation quality. https://aclanthology.org/2023.emnlp-main.398/
- **W5:** Microsoft Research, VeriTrail, August 5, 2025; paper arXiv:2505.21786. Multi-step provenance/error-localization precedent, not a deployed Mastermind verifier. https://www.microsoft.com/en-us/research/blog/veritrail-detecting-hallucination-and-tracing-provenance-in-multi-step-ai-workflows/ ; https://arxiv.org/abs/2505.21786
- **W6:** MarketDesk landing, inspected September 15, 2026 ET. Confirms ZeroHedge Professional login only. https://marketdesk.ai/
- **W7:** Islam et al., FinanceBench, 2023. Useful evidence-string/numeric-task evaluation precedent; historical model scores are not current model performance. https://arxiv.org/abs/2311.11944

The arithmetic, workload sensitivities and scale estimates in this document are transparent calculations over explicitly fictional or assumed inputs. They are not observations from live PDFs or performance tests.
