# Research Vault — Chunk 19: audience-safe distribution and measurable usefulness

**17 September 2026. Parent customer upgrade: SPEC_ONLY.** This phase examines current public publication and first-party measurement paths, corrects an obsolete implementation-status claim, and specifies the next release criteria. It does not release the Brain candidate, change production content, execute held tests, establish a commercial licence, or purchase accounts.

## 1. Executive decision

The institutional-research product must pass three different questions:

1. **Can Mastermind use this evidence for this purpose and audience?**
2. **Does the displayed analysis faithfully preserve what the source supports?**
3. **Does the resulting experience help an actual user complete a useful task?**

A subscribed PDF, an accurate file fingerprint, a visible excerpt, and an event count each answer only part of that chain.

The selected direction is to keep the existing source, publication, identity, Brain, and first-party analytics owners. Additional acquisition must not automatically become additional public excerpt publication. Original-report access, internal processing, subscriber answers, and public editorial require separately established use configurations. This is an adoption proposal; it does not switch current production policy or grant any use.

The first product remains one permitted company question -> existing Brain -> source-bound answer -> matching source inspection. Public distribution and measurement must be fit for the particular output; a universal full-history graph, custom model, and whole-vault tagging remain unnecessary prerequisites for every simple answer.

## 2. Authority, source and correction of stale status

Protected procedure: `Mastermind@42d210bc07a75234092ff5be71f6038ccacaa884`, compatible Skillpack 1.0.1/bootstrap 1. INDEX/COLD_START/ACTIVE_EXECUTION/WEB_CEO_DELEGATION and CLOSEOUT were read at that pin; compact reads matched previously available immutable bodies. Current live Chairman continuation provides research intent, not a bypass of runtime, source-use, publication or review gates. Direct rationale: PRINCIPAL_JUDGMENT for audience/measurement semantics and LOWER_TOTAL_OVERHEAD for selected-function diagnostics.

The same research carrier is Macro PR #7182, branch `sol/research-vault-intelligence-design-r2-20260915`, starting at `f382ad9b9b78caa3dfaf91530b52ad2671a3d6ac`. Current implementation inspection pin: `e4a154c6390de8ac6fb88b586e9fd399dba557c6`.

**Correct earlier open-PR references:** GitHub reports #7045 merged on **2026-09-16T09:53:06Z**, merge commit `c37c4e37b20ada935f32516a2a31428d558430c3`, head `3f65e5621a3d130b32fed51583a92bc6c2b5a1bb`. It is no longer an open source-collision gate. Its desk-type/summary-hygiene work must not be recreated. Merge is not new browser or deployment proof from this phase. [S1]

#7079 remains open/draft/unmerged at `8271ae320732997be4553957e3e2773d1b9e9f1b`. New work must qualify against current integrated source rather than treating the pre-#7045 client as unchanged. The original reader review, captured-source qualification, R17 code-publication and source-use holds remain. Bounded owner-comment reads after the preceding checkpoint returned no new reply; no universal inactivity or custody-transfer claim follows. [S2]

## 3. The system already has a public research-distribution path

This is not only a future marketing proposal. Source inspection establishes the following implementation:

- `engine/research_vault/excerpt.py` derives opening-page excerpts for public search-indexable report pages.
- The configured excerpt ceiling is **4,200 characters**, normally the first **two** extracted pages, widening up to **four** when the opening is text-sparse.
- `scripts/build_research_pages.py` loads the committed excerpts and supplies them to the individual report template.
- `templates/research_report.html.j2` renders those paragraphs before the membership call to action and labels them “Verbatim from the original PDF — first pages.”
- The source therefore distinguishes public excerpt text from the gated full-report/PDF link. A gated PDF does not mean all report-derived text is gated. [S3–S5]

This phase did not prove which exact build is served at the public origin. A web attempt for one known report URL was refused; it was not retried through another host or tool. Source-level publication behavior must not be mislabeled as a live-content census or legal finding.

The inspected derivation and builder use public catalog membership to decide which material participates; no source-specific commercial grant was established by this investigation. This is not proof no relevant agreement exists elsewhere. The public ZeroHedge terms inspected did not establish all intended automation, pooling, generated customer-output and original-redistribution rights. A licence/contract owner must resolve the actual grant. [W1]

### Product implication

Treat these as different proposed output configurations, not one “Pro” permission:

| Output | Distinct questions to resolve |
|---|---|
| Public metadata/teaser | Which metadata or derived descriptions may be indexed and shown publicly? |
| Public literal excerpt | How much source text, from which documents, under what attribution, retention and withdrawal terms? |
| Internal retrieval/analysis | Are extraction, indexing, embeddings and the actual model processors permitted? |
| Subscriber generated answer | May restricted facts/analysis be delivered in this audience and purpose? |
| Original report viewing/download | Is document redistribution or hosted access specifically permitted? |
| Public original editorial | Does the piece use permitted evidence, add original analysis and avoid restricted reproduction? |

These concepts map onto existing source-use and publication owners; no new independent licence registry or generic policy service is proposed. A capability requested in model JSON is not a grant. A permission applicable to one audience does not automatically apply to the others.

## 4. “Verbatim” output can lose meaningful numbers

The current cleaner removes email, URL and phone-like strings. The phone candidate expression removes runs containing at least nine digits. The source comment reasons that such a run cannot be a prose financial figure. A controlled counterexample demonstrates that this assumption is too strong. [S3]

Selected current operations, with fictional text:

| Input | Output |
|---|---|
| `Annual investment was 120000000 dollars, according to the fictional source.` | `Annual investment was dollars, according to the fictional source.` |
| The same amount written `120,000,000` | Amount preserved. |
| `The model includes years 2025 2026 2027 in the forecast.` | `The model includes years in the forecast.` |
| ISO date `2026-07-25` | Preserved. |
| Year range `2025-2026` | Preserved. |
| Fictional phone `+1 (212) 555-0199` | Removed as intended. |

These are selected-function diagnostic results, not proof that those exact strings occur in current institutional originals or that customers encountered them. No source file or published page was changed.

### Recommended correction boundary

Public presentation cleanup and source evidence must remain separate. A transformed paragraph should not be used as the authoritative operand source for financial calculations. Preserve the original extraction and any mapping; contact redaction should use supported contact context rather than digit count alone. Until literal fidelity is established, the presentation should identify its cleanup/omission limitations instead of making an unconditional verbatim promise.

Simply restoring every phone number is not the proposed fix. Neither is silently rewriting the underlying source to match the cleaned excerpt. The required capability is a faithful, appropriately redacted presentation with inspectable original support and a label that matches the transformation.

## 5. Missing inventory and deliberate withdrawal need different handling

The current excerpt snapshot and page builder deliberately protect against truncated input deleting a large amount of content. These protections have a valid availability purpose and should not simply be removed. [S3–S4]

Their observed selected-path behavior in fresh temporary directories:

| Initial report pages | Incoming catalog | Excerpt snapshot after attempt | Static report files remaining |
|---:|---:|---:|---:|
| 100 | 80 | 80 entries | 80 |
| 100 | 60 | 60 entries | 100 |
| 100 | 40 | Previous 100 retained | 100 |
| 100 | 0 | Previous 100 retained | 100 |

The directory also includes its index page. The first prune refuses removals above its quarter-directory threshold; the second refuses above its 34% threshold. Empty catalog input returns before rendering or pruning. The excerpt snapshot refuses an empty input or one below half the committed count.

The 100-to-60 example demonstrates that catalog/excerpt delisting can occur while old static files survive. Sitemap changes are not proof that a previously known URL stopped serving content. This is not a live withdrawal incident or proof of a CDN’s behavior; the whole build/deploy path was not run.

### Required design

A failed/truncated source enumeration and an **explicitly authorised withdrawal** are not the same event.

An unknown feed failure should preserve the accepted protections. An approved source-use withdrawal needs a source-owner decision identifying the exact affected documents, versions, audiences and purpose, then a controlled change through the current publication/storage owners. The final proof should check affected known URLs and applicable derived outputs, not only absence from a new index.

Where a use is withdrawn but other uses remain permitted, narrow the audience/purpose projection rather than destroy unrelated valid evidence. Where removal is required, account for static pages, committed excerpt snapshots, search visibility, source-view access and affected generated outputs according to the actual agreement. Existing invalidation/event/publication owners should carry this; no second takedown queue or identity plane.

A Git removal does not erase history or third-party caches. Do not promise retroactive recall beyond the system’s control. Establish actual required retention/deletion and what can be attested before offering the product. Prevent a subsequent ingest from unintentionally reintroducing a withdrawn output through the existing source decision, not a disconnected blacklist.

## 6. Actual usage: the connected analytics project is not the product’s measurement owner

A read-only PostHog event-schema request returned only reference events marked not seen in the last 30 days, including page views; no custom research events were returned. That does **not** establish zero customers, zero product activity or absence of all telemetry.

Repository inspection then located the existing owner: `admin/analytics_first_party.py` reads shared Supabase `analytics_events` and `search_events` through the established admin path. It already handles operator exclusions, bots, identities, per-tab/per-origin sessions and stitched visits. Those definitions should be reused, not replaced by a new PostHog funnel. Its default display timezone differs from the Chairman’s America/New_York timezone; a future analysis must explicitly state the interval and grouping timezone. [S6]

The Supabase connector was found available but not installed. An in-product connection suggestion was displayed. It does not establish an authenticated connection or permission to query records. No Supabase records, user identifiers, IPs, prompts or private portfolio data were fetched.

The next useful read is an aggregate report through the existing definitions: relevant path groups, time window, coverage, exclusions and eligible user context. First verify actual event/property names. Do not invent research-specific event names or equate an event catalogue with active instrumentation.

## 7. Existing activation counts are not yet an ordered research funnel

`activation_funnel_report.py` describes visit -> intelligence.viewed -> personal.act -> watchlist.saved, but its inspected stage calculation counts the session set independently for each stage. Ratios divide the sizes of those sets; the calculation does not require the same session to progress through them in order. [S7]

Three controlled datasets clarify the boundary:

- Session A views intelligence; session B acts and saves. Counts show one intelligence session and one action session, giving a ratio of 1.0, but the intersection is zero.
- One session saves, then acts, then views. Its stage totals match a forward-order session.
- A true forward-order session is a working control, but the same totals cannot distinguish it from the reverse-order case.

The inputs are fictional. This is not a claim of a measured 100% real conversion, or proof of a current misleading dashboard seen by users. It establishes that these ratios cannot be treated as conditional ordered conversion without a definition change.

### Measurement contract for the existing owner

Distinguish:
- non-ordered activity counts;
- ordered progression within an explicitly defined session/visit and observation window;
- return use on a later eligible visit;
- qualified useful-answer completion;
- signup/payment outcomes where the existing authorised billing/identity data supports that join.

No collection of those signals alone proves the causal effect of research. Stable exclusion and identity rules, explicit ingestion/occurrence cutoffs, late-arrival handling and a shared comparison design are needed. Preserve unknown identities and unavailable denominators honestly; do not inflate unique people from tab sessions or count internal review traffic as customers.

A source click shows inspection intent, not necessarily correctness or customer value. An AI answer event shows delivery, not usefulness. A “helpful” vote is feedback, not independently verified factual accuracy. Use the existing source-answer evaluation and analytics owners together without exposing private prompts or holdings to a new telemetry destination.

## 8. The revised capital experiment

The original baseline/expanded corpus crossed with existing/improved processing remains useful. This phase adds two explicit requirements:

**Output-use eligibility:** added documents may improve internal discovery without being eligible for public snippets or subscriber originals. Count the benefit only in the permitted product configuration.

**Valid outcome measurement:** stage counts, file volume, impressions and source citations must not substitute for supported useful task completion. Where user outcome data is unavailable, report an offline quality result separately—not projected paying-customer value.

Practical order:

1. Resolve the actual source-use configuration for the first company question.
2. Prove that question in the existing Brain/reader, including correct evidence and inspection.
3. Read first-party baseline aggregates under existing privacy/exclusion definitions; qualify the event gaps needed to evaluate the experience.
4. Run the controlled task comparison and a bounded real-user observation period.
5. Evaluate one separately permitted additional monthly acquisition increment. Each further increment needs its own marginal benefit.

The incremental cost includes subscriptions, eligible source processing, serving, review and required commercial terms. No fresh price, customer margin, revenue count or ROI was measured in this phase. The prior three-account hypothesis is not an order. A larger public excerpt footprint is not itself a benefit.

## 9. Bounded delivery leaves and acceptance

These are owner-adjudication requirements, not dispatched jobs or newly accepted runtime schemas.

### A. Faithful and audience-qualified public research output
Mission: one permitted report produces the correct allowed public presentation; a deliberately authorised change removes or narrows it without mistaking a broken feed for withdrawal.

Existing owners: source-use/business contract, Vault excerpt/catalog, page renderer/publication, current caching and original access. #7045 is merged; consume its current code rather than asking its old branch to start new work.

Acceptance: source values/qualifications preserved; contact removal does not silently delete a valid financial number; output label reflects transformation; audience decision precedes publication; failed inventory preserves availability; an explicit withdrawal reaches known URLs and cannot be reintroduced by a routine rebuild; unaffected sources remain available; lineage and actual retention policy preserved. Browser/CDN proof is required for a live exposure claim. No production deletion or fixture waiver.

### B. Research-use measurement through first-party analytics
Mission: an authorised operator can distinguish actual research use from bots/internal traffic and cross-sectional counts, without reading private prompts or holdings.

Existing owners: first-party Supabase ingestion/admin, growth schema, request/response evidence and privacy controls. Query the current schema before specifying additive fields; do not add a second analytics service.

Acceptance: actual project and coverage established; aggregate time window/zone explicit; counts and ordered conversions labeled differently; reverse/disjoint sessions do not become conversions; cross-origin identity rules reused; missing/no-denominator state remains unknown; sufficient privacy-preserving link to eligible source/answer outcome for the acquisition evaluation. Connector installation alone is not data access or measurement.

### C. First useful Brain answer remains the main product leaf
R18’s first permitted company question and R15’s catalog/default versus source_text interface remain. Preserve current entitlement, private per-read guard and single final debit. Do not copy the blocked R17 library or run the held R14/R16 operations elsewhere. The new audience/measurement work is independent research, not permission to release the reader.

## 10. What was completed and what was not

Completed: current publication and analytics owners were identified; #7045’s merged state corrected the stale open-PR assumption; selected source transformations, anti-collapse/prune boundaries and stage-membership behavior were characterized using fictional data; an output-specific adoption and measurement contract was selected for review.

Method: manually transcribed selected current operations, with comments/logging omitted, temporary files and ordinary Python. No full module import or whole upstream-file local byte parity is claimed. The attached JSON records exact inputs/outputs and source identities. This is not a production test suite, newly fixed defect, measured live incident rate, independent review or model benchmark.

Not completed: live-origin public-content verification; current Supabase usage counts; source licensing; actual publication withdrawal; production repair; Brain integration; original-source acceptance. An exact public-page web read and MarketDesk landing read were refused and not retried. The container tool had an infrastructure gateway error; permitted independent Python diagnostics succeeded. No native host calls or previous blocked-operation repeats.

No subscription, vendor message, model/provider run, new Job/worker/watcher, CI dispatch, source acquisition, production configuration change, merge or deployment occurred. Old historical test totals remain historical.

**Primary continuation:** through the existing source/publication and Brain owners, qualify one report’s allowed audience and literal evidence for the accepted company-answer journey; use the existing first-party analytics connection for aggregate baseline measurement once authorised. Keep all original holds and do not turn this investigation into another disconnected prototype.

## Source register

All implementation observations use `macro@e4a154c6390de8ac6fb88b586e9fd399dba557c6`.

- S1: PR7045 metadata, merged 2026-09-16T09:53:06Z, `c37c4e37b20ada935f32516a2a31428d558430c3`: https://github.com/mastermindx-market-intelligence/macro/pull/7045
- S2: pending #7079 at `8271ae320732997be4553957e3e2773d1b9e9f1b`: https://github.com/mastermindx-market-intelligence/macro/pull/7079
- S3: `engine/research_vault/excerpt.py`, blob `b6180d72cb8baff59b99ba22d8aa92958d747b97`.
- S4: `scripts/build_research_pages.py`, blob `aed7a36d2c8d3e3006b4f7eb306f4ca257d4c356`.
- S5: `templates/research_report.html.j2`, blob `3aaa039a3822a3940fef8a9f3f88d4d16ea8ace1`.
- S6: `admin/analytics_first_party.py`, blob `e7a3dc56435725bf77d5fa09758ade3abe895c9b`.
- S7: `scripts/activation_funnel_report.py`, blob `86801a212365f8f21e4b0ab24ea336709e74983b`.
- W1: https://www.zerohedge.com/terms-of-service — inspected public terms; no complete commercial-use grant established.
- Direct tool observation: connected PostHog event-schema response; reference events marked not seen in 30 days, no current first-party project measurement.
- Direct tool observation: Supabase available/not installed; connection suggestion displayed, no records queried.

The source snippets and diagnostic results do not establish current serving behavior, legal infringement, source authenticity or economic value. Publisher contracts and actual production paths remain separate evidence.
