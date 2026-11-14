# Mastermind Alert Intelligence Fabric — architecture proposal v0.1

**Status: PROPOSED / SPEC_ONLY. Not a design freeze, implementation commission, release decision, or production claim.**

**Product/architecture lead:** Sol, under Chairman Chris's current September 13, 2026 instruction to expand Alert Center into an intelligent cross-product alert system, complete the thinking before Figma, and proceed across multiple turns. Chris remains final business authority.

**Existing implementation carrier:** Macro PR [#7022](https://github.com/mastermindx-market-intelligence/macro/pull/7022), operation `MMX-ALERT-CENTER-V2-ASTRA-20260908`, branch `claude/alert-center-v2-astra-20260908`, head `c83a5771b54e6e487cdb2d06be45ccbf480e560d`. That candidate remains PARTIAL and Draft/HOLD-FOR-SOL. This separate research-only branch does not transfer its source writer, resolve its Source Continuity checkpoint, or replace its implementation.

**Research pins:** Macro `dce7bc25a7148fc0dba4e5b9480c494daf3aedd0`; Terminal `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c`; procedural Skillpack 1.0.1 from Mastermind `dfa518c079bca971ae55d53a1a6cd67d7128a039` (INDEX, COLD_START, RECONCILE_STATE, CLOSEOUT). These are investigation snapshots, not a claim that moving branches will remain at those heads.

## 1. Product thesis

Mastermind should do more than collect alerts. It should notice important changes across its existing intelligence, explain what changed and why it matters, relate that change to the user's declared interests or holdings, and choose whether to interrupt, summarize, or simply preserve it for investigation.

**Understand broadly. Interrupt selectively. Explain precisely. Remember what changed.**

Prophet remains the flagship. Alerts should make its owner-issued opportunities and meaningful state changes conveniently available, not dilute Mastermind into a generic research inbox. Macro, company fundamentals, earnings, sector relationships, news, and the user's own research should add explanation and situational awareness without silently changing Prophet's scores or trading authority.

The primary user job is: "Keep me informed about important opportunities, risks, and changes without making me inspect every dashboard, and give me the evidence when I need it." The machine job is source-grounded change detection, relationship-aware interpretation, permission-safe relevance, reliable delivery, and measurable learning.

The Alert Center is the investigation and control interface. The alert fabric is a composition capability across existing owners, not a second source of market truth and not an autonomous trading engine.

A successful alert answers: what changed; compared with what; when it happened and became known; why this user is seeing it; what supports or contradicts the interpretation; what can be investigated next. A successful quiet period answers what was actually checked and what was not covered.

## 2. What has actually been recovered

| Capability | Evidence recovered | Assessment for this program |
|---|---|---|
| Alert Center V2 investigation workspace | PR #7022 has the assembler projection, renderer, inspector, filters, permalinks, firing history, and retained browser evidence. Its retained snapshot exposes 641 signals versus the unchanged 60-row legacy queue. | PARTIAL; useful candidate, not shipped or accepted. Snapshot counts are not current market counts. [S1] |
| Cross-domain situations | #7022 groups 131 same-source explicit subjects on its retained inputs; it explicitly excludes richer cross-domain interpretation. | NOT_BUILT within that candidate. Same-source bundles must not be renamed into completed intelligence. [S1] |
| F08 portfolio, monitoring, preferences, and delivery architecture | Existing owner freeze, source clocks, private/public boundary, run receipts, outbox, and user-control law. | Existing architecture to extend, not a new alert service mandate. Its original census is historical; individual implementations require fresh reads. [S2] |
| Per-user email delivery | #6906 is merged; current source includes the off-render drain and `app.mailer` integration. It is designed dormant by default. | BUILT_NOT_PROVEN for the expanded end-to-end journey. No fresh production enablement or received-email proof was obtained in this investigation. [S3] |
| Alert preferences | #6907 remains open and unmerged at `01d14795b2ebdc016c4c3263b46c9b415236918f`; includes opt-in, categories, timezone, and quiet hours. | BUILT_NOT_PROVEN candidate; an integration dependency, not a replacement settings project. [S4] |
| Durable user fire/outbox schema | Terminal's migration ledger records `alert_runs` and `alert_outbox` applied September 7, with a PR #513 readback reference. | Historical application evidence exists; not a fresh database/runtime check this turn. [S5] |
| Thesis monitoring | Existing monitor composes the tripwire latch with active user theses and queues into the same outbox. | Existing source integration to reuse; current end-user delivery not proven here. [S6] |
| News normalization and deduplication | Current financial-news code uses qbus, event classification, timestamp-quality fields, and entity-resolution helpers. | Existing code substrate; not proof that every feed is live, rights-complete, or ready for high-priority alerts. [S7–S10] |
| Company-event and financial context contracts | `company_event.v1`, financial-intelligence packet decisions, exact identity and theme-graph owners exist. | Reuse their actual contracts and declared coverage. Do not infer worldwide coverage from one issuer or one contract. [S11–S13] |

The July news-problem audit is useful historical context, not the current capability ledger. Current code already contains changes beyond that audit, including wider entity resolution and qbus integration. Conversely, finding a module does not establish its production adoption.

The historical Figma key `QO3CthsB5KzPVKdgfcVPMI` was retried and is still inaccessible to the connected identity. The connection reports a Professional plan with a Full seat. Chris reports newer Alert Center project files visible in that account; their exact file key has not yet been recovered. Therefore the old key is not declared the newest design, and no canvas has been edited or replaced. File identity/access is a later design-entry dependency, not a blocker to this research.

## 3. Architectural alternatives

**A — Reskin the existing ranked feed.** Lowest implementation cost and retains the existing backend, but cannot by itself supply personal relevance, meaningful updates, cross-domain interpretation, or dependable delivery. Retain useful UI work; reject this as the whole program.

**B — Build one large AI agent that reads every dashboard and decides all alerts.** Broad apparent intelligence, but it would duplicate facts and authority, repeatedly re-read unchanged material, mix private and shared context, and make semantic novelty, identity, escalation, and replay dependent on opaque model behavior. Reject as the execution architecture.

**C — Compose source-owned intelligence, governed situations, and personal attention. Recommended.** Domain owners emit or expose versioned observations and valid state changes. Existing identity and relationship owners support bounded joins. A composition layer assembles evidence and interpretation. Existing user-monitor and notification owners make auditable routing decisions and deliver through existing channels. The page, contextual cards, and email read consistent evidence references.

These are logical responsibilities, not a demand for new microservices. Begin with modules and existing build/evaluator/off-render seams. No new universal bus, scheduler, portfolio book, identity allocator, notification database, or message vendor is justified by this proposal.

## 4. Six concepts that must remain distinct

An **observation** is something a source reported or measured. A **material change** is an owner-supported difference from a defined earlier state or expectation. A **situation** is a bounded, evidence-linked interpretation of related changes over time. A **monitor** is the user's standing request to evaluate supported conditions or follow a subject. An **alert decision** is the reason a particular user should be notified or see a change in a digest. A **delivery** is a channel attempt and its observed outcome.

A news article is not automatically a new event. A new event is not automatically important to every user. A situation is not automatically a trade. An alert firing is not proof that an email arrived. Opening an alert is not evidence that the market condition resolved.

Likewise, source evidence status, user-rule state, delivery state, and personal read/archive state must not be compressed into one status badge. Extend each existing owner's vocabulary; do not construct a replacement universal lifecycle.

## 5. Logical architecture and ownership

### Source-owned observations and changes

Consume structured owner outputs rather than screen text. Prophet supplies its valid candidate/plan/availability changes; macro and cross-asset engines supply their own conditions; company-event and financial owners supply disclosures and revisions; news supplies documents and typed events; user theses supply the user's own standing research conditions.

An adapter must name its source contract/version, authority, subject identity, event and availability clocks, coverage, revision/correction behavior, allowed uses, and deep-link destination. Unsupported sources remain visibly unsupported. The integration does not silently become their collector or detector.

### Context assembly and relationships

Assemble a bounded evidence package on a relevant source revision, not an unconstrained copy of the entire dashboard. Reuse exact Data OS identity and the established company/theme graph bridges. A graph match is useful only when the edge's type, evidence, effective period, and rights support the particular statement being made. A theme membership is not proof of revenue exposure or causal impact. [S13]

Initial relationship journeys should be direct issuer/security links and explicitly evidenced one-hop relationships. The full design permits richer multi-hop investigation, but each added hop must carry its own evidence and uncertainty rather than turning a plausible narrative into a factual affected-stock list.

The shared context and a user's personal context are different planes. Shared does not mean public: paid owner artifacts retain their existing access controls. Personal holdings, theses, monitor conditions, delivery state, and interest preferences must stay in authenticated owner-scoped reads; they must not be baked into static HTML, public JSON, or shared R2 objects. [S2]

### Situation interpretation

A situation should carry the main development, meaningful changes since its previous revision, supporting facts, contrary facts, unknowns, affected subjects with connection reasons, relevant horizon, and source pointers. It is a derived view over existing facts, not a new event truth store.

Persisted following, revision linkage, or merge/split aliases must be adopted by an existing identity/event/monitor owner before subscriptions depend on them. Do not use title text or the current news-cluster representative as an assumed permanent situation identity.

### Personal attention and notification

Separate the evidence interpretation from the decision to interrupt. Use existing account preferences, explicit alert conditions, theses, holdings, and watchlists according to their different semantics. Evaluate subscriptions server-side. Store decisions and delivery references through the existing alert/outbox/mail owners rather than a parallel user-event system. [S2, S5, S6]

The existing operator Telegram/Discord broadcast path remains operator-only. It must not acquire private customer payloads or become a substitute for per-user email. [S2]

### Product and learning

Alert Center, source-page contextual alerts, monitor management, and emails should point to the same logical event and relevant revision. Existing analytics and evaluation owners should measure usefulness, correctness, missed changes, duplication, and delivery behavior. No new trade-performance scoreboard is created by this product.

## 6. What makes the system intelligent

**Change understanding.** Compare compatible facts: the same metric, period, units, subject, and available vintage. Distinguish a new filing from a revision to old evidence, a scheduled date change from an event occurrence, and a new valid Prophet state from a repaint of yesterday's plan. A numeric change is not automatically economically material; the domain's rule and baseline must explain the relevance.

**Cross-domain synthesis.** Explain how an official guidance update relates to the issuer's financial context, a sector's evidence, and a user's stated research. Do not merely attach five unrelated panels. Every connection should say why these facts belong together and whether it is an observed relationship or a proposed interpretation.

**Contradiction sensitivity.** Preserve evidence against the leading interpretation. A demand improvement with weakening margins is a mixed situation, not a higher-confidence bullish alert because two feeds fired. The system should sometimes say that the evidence is becoming less clear.

**Meaningful novelty.** New facts, changed numbers, an official confirmation, a correction, or a changed supported state can justify an update. More publishers repeating a wire story, a model rewriting its summary, or a re-run of an unchanged artifact do not.

**Continuity.** Explain what changed since the user last received or inspected the situation. Use event/source revision references and the existing delivery/read owners, not a language model's impression of what it remembers. Late-observed old events must be distinguished from newly occurred events.

**Useful abstention.** Missing financial context should produce a narrower, useful alert with the limitation stated, not a fabricated explanation or total loss of an otherwise valid critical signal. Unavailable identity or permissions block the unsafe join. A source outage is a monitoring problem, not evidence that nothing happened.

**Anticipatory monitoring.** A known upcoming catalyst can be followed before it occurs, with changes to its schedule, release, official revisions, and subsequent evidence connected into one journey. This is calendar/condition awareness, not an invented forecast of the market reaction. Claims that an expected event did not occur require both a defined expectation and adequate source coverage.

## 7. Deterministic and model responsibilities

Deterministic/source-owned work includes identities, typed facts, units, clocks, revisions, approved threshold conditions, eligibility, source caps, entitlements, quiet hours, outbox operations, and delivery reconciliation. It also includes the supported user-rule representation and its actual evaluation cadence.

Model work can include citation-bound explanation, comparison of documents, extraction proposals, hypotheses about related evidence, contradiction summaries, and plain-language monitor drafting. Numerical fields and material factual claims must be checked against source evidence. An extraction confidence score is not an event's importance, and neither is a probability of a profitable trade.

A model may draft: "Tell me when this company's reported demand assumptions deteriorate." The product must translate that into supported, explicit conditions and disclose what it can actually check. The user reviews scope, source, trigger, cadence, expiration/re-arm behavior, and delivery before activation. Unsupported narrative conditions remain research requests, not falsely active automatic monitors.

AI explanations must not sit on the critical path of an already-valid urgent alert. Deliver a useful source-grounded template first when needed; add analysis later without sending another interruption just because wording changed. A model outage must not disable deterministic monitors.

News and retrieved documents are untrusted evidence, never instructions to tools or permission to act. Reuse the existing model/grounding/auth path. No extra provider account, autonomous browsing agent, or permission expansion is introduced here.

Existing F08's LLM/score/authority ceiling remains controlling. Proposed factual news-to-notification admission requires a separately ratified owner contract; there is no direct LLM-to-escalation route in this proposal. [S2]

## 8. Attention policy: importance is not one magic score

Keep separate dimensions: factual support; source freshness and coverage; event materiality; relevance to the user; time sensitivity; meaningful novelty; and delivery eligibility. A return forecast, when a validated owner has one, remains a separate owner-issued object with its horizon and limitations.

A confirmed guidance cut can be important to an owner of the stock without any validated claim about tomorrow's return. Conversely, a measured signal's historical hit rate does not establish that its current data is fresh. The interface must communicate these distinctions without forcing users through methodological prose.

Initially preserve the old board's scores, IDs, source-assigned authority, and push semantics. A future personal attention ordering must be versioned and evaluated separately; it cannot silently rewrite legacy signal priority. Explicit user-requested conditions cannot be discarded by an opaque engagement ranker.

Suggested presentation language is **Review now**, **Material update**, and **On your radar**. These are proposed attention labels, not replacements for a producer's act/watch/context semantics and not buy/sell instructions.

The selection policy should group echoes and related updates, preserve visibility of important smaller sources, and offer an uncapped investigative view with disclosed technical history limits. Source diversity is a display objective, never additional evidence of truth.

Quiet hours, interruption budgets, digest cadence, and temporary snoozes are user controls. No quiet-hours override is implied by the word critical. An outage recovery or historical backfill must not produce a burst of old alerts presented as current opportunities.

## 9. News integration is an explicit dependency, not a second news platform

The current news estate already has ingestion, normalized items, deterministic event classification, entity links, and qbus deduplication. qbus stores first-seen items and groups similar headlines; its source/desk breadth is distribution context, not proof of independent confirmation. [S7–S10]

A news integration must distinguish original reporting, a company or regulator's statement, syndication, commentary, estimates, rumors, corrections, and withdrawals where evidence supports that classification. It must also expose headline-only versus fuller source access. We must not infer a claim about an article's unseen contents from its title.

Two concrete source concerns must be addressed before stronger alert admission. The optional AI-feed normalizer substitutes processing time for some missing or malformed publication dates; such a value cannot become a breaking-event timestamp. It also normalizes vendor importance, relevance, or confidence into a common display number; that number must not silently become alert urgency or factual confidence. These are code-path observations, not proof of a current production incident or an enabled provider. [S10]

The read flow should retain the news item's existing identity, source/first-seen clocks, document access level, and correction links, then relate it to known company events and context. It should not create another news corpus or duplicate first-print ledger.

First-party releases and already-lawful licensed/public inputs can support the first useful news-alert vertical. The complete News-page revamp need not finish first. Global breadth, deeper article bodies, translation, and second-order relationships expand only with explicit coverage and rights. A source being readable on the web does not by itself grant redistribution rights for email excerpts or model context.

## 10. Personalization and monitors

Offer distinct lenses for followed companies/themes, actual holdings, explicit user alerts, active theses, and broad market developments. A watchlist entry is interest, not ownership. A holding requires the canonical portfolio record; weights and totals require a compatible value basis and visible exclusions. [S2]

Suggested monitors can make setup convenient, but are not silently activated. Provide sensible monitoring packs around Prophet changes, owned-name material events, upcoming catalysts, and thesis changes; each pack exposes the conditions and coverage it enables.

A source-page **Monitor this** action should prefill the same canonical monitor flow used by Alert Center. A saved investigation view is a reusable filter, not automatically a standing alert. Chat can help draft a supported monitor but cannot silently turn conversation content into subscriptions or pretend that an unsupported idea is being watched.

User reading should not permanently suppress disconfirming evidence. Explicit feedback such as wrong company, repetitive, stale, useful, or not relevant should be distinguishable. Learning may improve suggestions and digest presentation only within declared authority and with recall/quality checks, not merely maximize clicks.

The system should remember what was delivered through existing delivery evidence. Following a situation means notify on meaningful revisions, not every refreshed card. Re-arm, expiration, watchlist membership changes, and position closures must have explicit behavior; existing one-shot alert semantics remain intact until their owner ratifies an extension.

## 11. Email: complete the existing journey

The desired journey is source change -> canonical fire -> user policy -> existing outbox -> existing mailer -> observed channel result -> authenticated evidence deep link. #6906, #6907, the Terminal outbox, and the thesis monitor are dependencies of this one journey, not competing products. [S3–S6]

Before pilot activation, prove opted-in and opted-out users, source categories, permissions and entitlement at send time, user timezone/DST and quiet-hours resumption, duplicate input, failed send, ambiguous send outcome, and revoked access. Do not send to real users merely to test an architecture proposal.

The existing source declares a five-minute drain and a fifteen-minute p95 fire-to-send target. Those are implementation design targets, not verified production service levels and not a promise that every input is real-time. A nightly detector stays nightly even with a frequent mail drain. Measure source availability -> ingestion -> evaluation -> UI visibility -> send separately, with requested deferral shown separately. [S3]

Email needs concise what-changed / why-it-matters / evidence content, a clear way to manage notification choices, and an exact return path. The return path must show what the message referred to and whether newer evidence corrected it. Avoid private portfolio amounts in email subjects by default. Do not put access credentials in links.

Outbox pending, deferred, failed, suppressed, and sent are existing states, not interchangeable delivery success. Provider acceptance, recipient-server delivery, bounce, and user interaction are separate observations when supported. Amazon SES's official event model makes this distinction explicit; it is research precedent, not a decision to replace our mailer or adopt SES. [S16]

There is an existing retention concern: the thesis monitor uses the existing outbox's unique fire identity as its replay backstop. Removing the only dedup anchor while a source latch remains fired can allow re-notification. Retention/archiving must preserve that guarantee under the current owner; it does not justify an independent dedup database. [S6]

**Explicit amendments needed before implementation:** F08 currently defers quiet-hour alerts and delivers them when the window opens. Coalescing them into a digest, expiring stale actionable copy, or replacing a withdrawn alert with a correction must be ratified as an auditable policy, not silently implemented as dropping rows. Preserve original firings and reasoned decisions even when the user receives one combined update. Likewise, additional per-user push/webhook channels require their existing owners and an explicit delivery contract.

## 12. Experience structure to validate before Figma

Recommended primary navigation: **Now / Explore / Monitors / History**. This is a proposal, not a forced rename of an existing accepted contract.

**Now** opens with a small, evidence-grounded What Matters Now briefing and a scannable queue. For You and Across Markets are lenses, not disconnected products. Show the meaningful change, relevance reason, source timing, and one useful next action. Prophet opportunities remain prominent when genuinely eligible. Do not turn the top of the page into a large opaque pressure gauge.

**Explore** supports Situations and All Signals, source/subject/time filters, search, and deep links. The complete accessible population remains inspectable even when a concise queue selects only a few items. Related observations and truly grounded cross-domain situations must be visibly distinguishable until the richer capability is proven.

**Monitors** shows what is being watched, why, supported source/condition, scope, last attempted/successful check, coverage, re-arm/expiration behavior, and notification settings. The glance-level message is plain language; raw run IDs and detailed diagnostics are secondary. A failed check must not look like a functioning quiet monitor.

**History** separates original firings and revisions from user deliveries and read/archive actions. It explains whether an item was sent, deferred, suppressed, failed, or later corrected. Historical views remain anchored to historical evidence rather than repainting old events with today's explanation.

A desktop evidence inspector should preserve the queue, filters, and selection. Mobile uses a full-height detail view with a reliable return path. Detail should contain what changed, why it matters, evidence and disagreement, affected subjects with connection reasons, timeline, and notification rationale.

Every relevant dashboard can offer consistent contextual alert previews and Monitor this actions. This does not authorize unilateral changes to the shared header or reintroducing an old notification bell without its own shared-navigation design review.

Dark and light are separate material treatments under the same design tokens and hierarchy. EN/ZH, keyboard/focus behavior, long titles, reduced motion, and 390px mobile are acceptance states, not later polish. Missing evidence, permission-limited evidence, no matches, genuine quiet, source outage, corrected events, unsupported monitors, and delivery failure must be designed before release.

## 13. Golden journeys and adversarial counterexamples

The following are **illustrative acceptance scenarios, not observed market events, actual user holdings, or completed tests**. The next architectural step binds them to retained real producer inputs where available and clearly labeled synthetic failure controls.

| Journey | Required behavior | Counterexample that must fail |
|---|---|---|
| A. A watched Prophet opportunity changes to a newly valid owner-issued state | Preserve candidate/plan identity, source state, quote/data vintage, authority, and direct return to the owner. Explain the change and route under user policy. | The alert layer invents eligibility, re-scores a stock from news, or announces an old reconstructed plan as new. |
| B. Evidence relevant to a user's thesis changes | Preserve the user's actual condition separately from the engine's evidence; use the existing thesis/latch/outbox path when the supported condition fires. | An LLM substitutes its own thesis, silently activates a monitor, or treats an unsupported semantic condition as evaluated. |
| C. An issuer changes guidance while financial and sector evidence provide context | Show the official change, comparable historical values, supportive and contrary context, and grounded relevance. Distinguish fact from interpretation. | Shared sector membership becomes a claimed causal hit to every related stock, or an earnings surprise uses a post-release consensus vintage. |
| D. A scheduled macro catalyst is moved, released, and revised | Link the revisions and distinct clocks; contextualize using owner facts; keep original and current views distinguishable. | Rebuild time is called event time, a revised release is treated as the original surprise, or an upcoming event is claimed to explain an earlier move. |
| E. Many sites repeat the same wire report | Group echoes, show original provenance where known, update coverage without escalating factual confidence. | Thirty copies become thirty independent confirmations or thirty customer emails. |
| F. A previously delivered report is corrected or withdrawn | Preserve the original delivery reference, show the correction on the same investigation path, and make a reasoned update decision. | Silent deletion, an unchanged stale email link, or a cosmetic summary revision becomes a major new alert. |
| G. One source fails while the rest remain usable | Distinguish partial monitoring from no events; preserve useful checked evidence and name the unavailable scope. | Last week's success masks the latest failure, or an old last firing alone is used to declare the feed broken. |
| H. Two users have different holdings, permissions, and quiet hours | Separate relevance and delivery, honor current consent/entitlement, and prove no private data in shared outputs. | Cross-user cache exposure, bypassed quiet hours, an expired source entitlement, or a duplicate send after retry. |

These cases also require bilingual and mobile paths, source-revision history, identity changes, and an explicit no-match/unsupported outcome. Passing a hand-selected golden set is not a production precision/recall claim.

## 14. Learning, replay, and proof

Quality has four independent dimensions: Truth (correct source, subject, time, revision, rights); Intelligence (useful comparison and synthesis, meaningful relationships, preserved disagreement); Product (fast comprehension, investigation and controls that really work); Learning (evidence that the system improves relevance and reduces missed important developments without spamming).

Replay must be as known at the time, including source availability, identity mappings, evidence revisions, user subscriptions, and policy/model versions. Financial packets already have cutoff-visible governance decisions; reuse that discipline rather than answering historical questions from today's corrected facts. [S12]

Evaluate missed important developments against a retained accessible source population, not only the few alerts the product chose to show. Use adjudicated event-family cases and held-out periods; track false urgency, wrong entity, source-clock errors, echoes, correction propagation, and duplicate interruptions separately. Establish numerical operating thresholds after measuring the actual baseline, not by printing arbitrary accuracy percentages in this proposal.

Suggested product measures are time to understand the main change, successful evidence drill-through and return, useful-monitor creation, source-coverage comprehension, meaningful-alert feedback, and missed-event reports. Click-through/open rate alone is not the optimization objective. Notification usefulness and source correctness are not a validated return edge.

Instrument through existing analytics/evaluation owners. Preserve source/input/output bindings and policy versions without creating another outcome grader or storing private prompts in public artifacts. Shadow policy decisions must not silently become live customer sends.

## 15. Build sequence after architecture and design approval

**First, freeze the right product contract.** Bind the golden journeys, source owners and exact schemas, identity/correction rules, supported monitor semantics, attention policy, and notification amendments. Identify genuinely missing adapters and current production gaps. The first-pass proposal does not claim these decisions are all closed.

**Second, complete the editable Figma experience.** Resolve the actual newest accessible file, preserve its original/reference pages, then design the complete primary journeys and failure states using the shared design system. High-fidelity screens should use actual source-shaped examples, not invented confidence or simulated unavailable features. Prototype Now -> evidence -> follow -> relevant update, plus delivery and correction paths.

**Third, deliver bounded product verticals.** Preserve and reconcile #7022 rather than restart the implementation. The first flagship integration should carry a valid source-owned Prophet change through a useful Alert Center investigation journey; a missing source contract is an explicit adapter dependency, not permission to synthesize a replacement signal. Preserve the all-signal explorer and historical evidence.

**Fourth, connect user monitoring and email.** Reconcile #6907 with the existing F08 delivery/outbox/thesis work, then prove one consented user journey end-to-end. Real delivery, user isolation, failure states, and evidence return are separate gates from merge or local tests.

**Fifth, prove one genuinely cross-domain situation and a bounded news join.** One issuer, one official event, relevant existing financial/sector evidence, contrary evidence, and one meaningful update/correction cycle. This is the minimum credible intelligence vertical, not a renamed same-source bundle.

**Then expand breadth and refinement.** Add sources, regions, mechanism-grounded read-through, more monitor conditions, and calibrated attention improvements through their owners. Do not wait for a complete News overhaul to deliver useful alert intelligence, and do not claim world-market coverage from a US example.

Each PR should unlock one observable capability with producer, consumer, relevant UI/machine projection, tests, and proof. No infrastructure-only epic is allowed to stand in for a usable workflow. The complete ambition is preserved while the releases stay bounded.

## 16. Open design decisions and gates

The recommended direction is firm enough to evaluate, but not ready to be called perfected. Before visual freeze, close: the exact newest Figma file; source-owner contract and readiness for the first Prophet journey; stable situation anchoring and merge/split behavior; categorical admission for factual news; measurable per-family attention/materiality rules; supported monitor grammar and re-arm behavior; digest/deferred-correction semantics; rights-safe email content; existing-owner persistence for read/follow state; and the production proof path for preferences/outbox/drain.

No Figma edits, new runtime Jobs, workers, watch loops, production sends, schema changes, shared-navigation changes, merges, or deployments are authorized by this research document. The current Chairman mandate authorizes the program's architecture/design progression, while implementation and release still obey their applicable source and permission gates.

A behind-commit count alone is not an instruction to rebase #7022. Reconcile material owned/dependency changes and the existing source carrier before any code integration. Do not displace other active owners merely because this research coordinates their user-facing journey.

## 17. Exact continuation

**Next primary action: Sol binds journeys A–H to a source-owner/capability/decision matrix with retained real inputs and labeled failure controls, adjudicates the specific policy amendments above, and presents the resulting product contract for Chairman acceptance.** Only after that boundary should the latest Figma be developed into the accepted visual specification.

The durable delta of this turn is an expanded, source-grounded architecture proposal and recovered dependencies. It is not a live alert capability. The existing UI candidate remains PARTIAL; the broader new intelligence design remains SPEC_ONLY.

## Source index

Repository references below are evidence/ownership anchors, not blanket runtime acceptance. Historical details in a document remain historical even when the document is on current main.

- **S1:** [Alert Center V2 PR #7022](https://github.com/mastermindx-market-intelligence/macro/pull/7022); [candidate continuation](https://github.com/mastermindx-market-intelligence/macro/blob/c83a5771b54e6e487cdb2d06be45ccbf480e560d/research/ALERT_CENTER_V2_CONTINUATION_20260909.md); [candidate design freeze](https://github.com/mastermindx-market-intelligence/macro/blob/c83a5771b54e6e487cdb2d06be45ccbf480e560d/research/ALERT_CENTER_V2_DESIGN_FREEZE_20260909.md).
- **S2:** [F08 architecture and owner freeze](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md).
- **S3:** [Email delivery PR #6906](https://github.com/mastermindx-market-intelligence/macro/pull/6906); [current delivery drain](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/alert_delivery_drain.py).
- **S4:** [Preferences PR #6907](https://github.com/mastermindx-market-intelligence/macro/pull/6907).
- **S5:** [Terminal migration ledger](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c/supabase/migrations/README.md); [existing outbox schema](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c/supabase/migrations/0013_alert_runs_outbox.sql).
- **S6:** [Thesis condition monitor](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/thesis_condition_monitor.py).
- **S7:** [Financial news](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/financial_news.py).
- **S8:** [qbus](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/qbus.py).
- **S9:** [News event classification](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/news_events.py); [news-vector first-print store](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/news_vector.py).
- **S10:** [Optional AI news-feed normalizer](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/news_ai_feed.py).
- **S11:** [Company-event spine](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/engine/company_intelligence/events.py).
- **S12:** [FIF packet freeze](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/agentos/decisions/DEC-FIF-1-V1-FROZEN.md); [cutoff-visible governance](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/agentos/decisions/DEC-FIF-PACKET-GOVERNANCE-IS-CUTOFF-VISIBLE.md).
- **S13:** [Prophet contract and owner map](https://github.com/mastermindx-market-intelligence/macro/blob/dce7bc25a7148fc0dba4e5b9480c494daf3aedd0/research/prophet_v4/CONTRACT_AND_OWNER_MAP.md). Its original implementation-status descriptions are dated; use the map for ownership and refresh the actual capability before integration.
- **S14:** [AlphaSense saved searches and contextual email alerts](https://help.alpha-sense.com/hc/en-us/articles/41815267178899-Save-Searches-and-Create-Email-Alerts-in-AlphaSense); [TradingView dynamic watchlist alerts](https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/). Workflow research only; no competitor code, assets, or proprietary content is adopted.
- **S15:** [Google SRE practical alerting](https://sre.google/sre-book/practical-alerting/): aggregation with inspectable component detail is a useful systems precedent, not a market-validation method.
- **S16:** [AWS SES event semantics](https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html): send, delivery, bounce, and delay are distinct observations; no vendor adoption is proposed.
