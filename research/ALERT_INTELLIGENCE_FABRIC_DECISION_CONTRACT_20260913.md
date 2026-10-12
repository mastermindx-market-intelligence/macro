# Alert Intelligence Fabric — source-bound decision contract v0.2

**State: SPEC_ONLY / PROPOSED FOR ARCHITECTURE REVIEW.** This is a product and architecture deliverable, not implementation, deployment, a live monitor, or permission to send customer email.

**Lead:** Sol, under Chris's current instruction to continue the architecture before returning to Figma. The two user-shown Alert Center V2 drafts stay untouched. Their screenshots establish that two drafts exist, not their exact file keys or which is canonical. Do not create a third design to avoid resolving that comparison later.

**Continuation carrier:** Macro Draft PR #7135, branch `sol/alert-fabric-architecture-20260913`. The existing implementation remains #7022 at `c83a5771b54e6e487cdb2d06be45ccbf480e560d`; no source-writer transfer or release is made here.

**Research pins:** Macro `ed691eb2e9927b9705abf65273bd4439c54a9ef2`; Terminal `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c`; Mastermind Skillpack 1.0.1 at protected master `91dbdf876f1f1ea10d24342b9d4ea49ba081bfcc` (INDEX, COLD_START, RECONCILE_STATE, CLOSEOUT).

**Companions:** [v0.1 product thesis](ALERT_INTELLIGENCE_FABRIC_ARCHITECTURE_PROPOSAL_20260913.md); [source-bound case manifest](alert_intelligence/source_bound_cases_20260913.json). v0.2 advances v0.1's next step from illustrative scenarios to named source inputs, decision rules, and owner-specific amendments. It does not supersede F08's production law or Prophet's authority boundaries.

## 1. The product decision

Build a proactive intelligence service whose user experience is calm but whose reasoning about changes is deep. It should do four valuable things together: discover owner-issued opportunities; explain developments in context; maintain a user's monitoring intent; and return with meaningful updates rather than repeated headlines.

Prophet remains the flagship opportunity source. Alert Center does not become an alternate stock picker. The broader system should make Prophet more useful through delivery and explanation, while also serving risk review, company developments, catalysts, and user research.

The fundamental unit of value is **a meaningful, evidenced change in what the user should understand or review**. It is not a log row, article, model response, refresh, or colored severity badge.

Every attention-worthy item should answer: what changed from the prior relevant state; why it matters; why this user is seeing it; what the evidence actually supports; what remains uncertain; and what useful next action is available. These answers must be recoverable from the underlying sources, not only from the latest generated prose.

## 2. What real source binding changed

The previous proposal was directionally correct but left important semantics open. Four concrete findings now determine the architecture.

### 2.1 Candidate observation is not opportunity availability

The committed Prophet HEAD points to generation `peg:18dfbb8a9d7152382ca6da8a2ac4177d6ea617dddc7cad082b3645c100fb53a7`. Its September event file contains **2,475 rows: 2,076 OBSERVED and 399 OPENED**. The full file was read into memory and its Git blob hash matched the native tree entry. These are counts of one retained file, not active candidates, current picks, or notifications owed.

The first sampled row carries a source-known/occurred time of May 7 but a recording time of September 13. The final sampled row opens an ADBE candidate episode with September 11 source time and September 13 recording time. The source's asserted known-at clock is preserved; this investigation did not independently establish historical public availability. Neither row proves that an entry is currently available. The same generation's receipt explicitly reports a missing Entry Radar source.

**Decision:** a candidate OPENED event may support a candidate-discovery item. It cannot become ENTRY_OPEN or a buyable plan. An OBSERVED event may update evidence without earning another interruption. Reconciliation time never manufactures a fresh market event. Missing one intake is disclosed as partial coverage, not extrapolated into a claim that all Prophet is broken. [R1–R3]

### 2.2 News tags and classifier labels are not admitted facts

The actual retained `site/news/financial.json` has three sampled market rows in which prime-minister wording is accompanied by ticker `PM`. Another headline anticipates a rate hike but carries classifier type `macro_release`, confidence `high`, from a matching rate-change pattern. These are observations about the repository input, not confirmation of the reported world events and not evidence that users were emailed.

**Decision:** entity disambiguation and the status of a statement—expected, announced, occurred, corrected, withdrawn, commentary—are first-class admission requirements. A reputable publisher, high display rank, or high classifier confidence cannot compensate for an unsupported company join or turn a prediction into a completed event. The original source item remains available in its lawful news context. [R4]

### 2.3 A configured monitor is not necessarily being evaluated

The retained tripwire artifact contains ARMED, MANUAL, DATA_MISSING, and FIRED records, including historical versioned records. It also contains a noncondition `archetype_checks` object; counting every top-level key as a current monitor would be wrong. For example, the memory condition is MANUAL and the housing condition DATA_MISSING. These are not user-specific records.

**Decision:** inventory, evaluation, coverage, event state, and delivery state remain separate. A manual research condition must not appear as an automatic watch. A latest snapshot date does not prove that an old latched event was checked again. [R5]

### 2.4 Existing email code needs an alert-specific reliability contract

The current drain checks a user's category subset only when the payload category is present. The shared mailer can send after a non-duplicate ledger insertion failure, deliberately accepting lost idempotency for older support/operator use cases. Ledger completion after SMTP is best effort. Consequently, an unresolved queued record is not proof that no SMTP effect occurred.

**Decision:** extend the existing mailer and drain for the alert-specific guarantees below, rather than introducing a new sender. These are code-path findings, not a reproduced production duplicate-send incident. Existing support and account-email semantics must not be globally changed by an Alert Center patch. [R6–R7]

## 3. The meaning model: six separate records, not one universal lifecycle

Keep source observations, source events, derived situation views, user monitors, notification decisions, and channel attempts distinct.

A source observation reports a measured or stated fact. A source event identifies an owner-recognized occurrence or change. A situation view brings related evidence together. A monitor expresses what a user wants watched. A notification decision records why a particular development is suitable for a particular channel/user. A channel attempt records what happened while trying to deliver it.

For example, an old company event can have a newly published correction; that correction can create a new notification decision for a previously notified user; the email can then be deferred while the on-site evidence is already corrected. Marking the user-facing card read changes none of those market facts.

The existing source schemas, event identities, alert conditions, outbox and mail statuses remain their owners' truth. New presentation fields below are proposed projections or bounded owner extensions—not a second event bus or lifecycle table.

### Reference anatomy

A usable read-model item must carry references to the owning source namespace, stable source subject/event identity, source revision or immutable evidence locator, event/effective time where supplied, availability/first-seen time where supplied, recording time, source coverage, and authority. A locator is not authorization: the read and send paths still check current access.

Its evidence package records the exact included source revisions and the interpretation version. Its semantic-change reference depends on relevant source facts, not on wording, translation, asset theme, or model temperature. The comparison names its previous relevant source revision and the basis of the comparison. A field absent from the source remains absent; no generic fallback timestamp upgrades it.

A personal projection adds only owner-scoped monitor references, relevance reasons, preference version, and interaction state. Those fields never enter shared/static market artifacts. Shared-but-paid source intelligence retains its existing entitlement boundary.

## 4. Meaningful change and admission policy

A new input passes through source admission, semantic comparison, relevance, and channel policy. These steps should be explainable independently.

### 4.1 Admission precedes importance

Before a direct event assertion or customer notification, require an allowed source use, a supported source contract, the relevant identity resolution, an interpretable time basis, and a recognized event/condition meaning. Failed identity means no affected-company claim, not silently using the nearest ticker. Missing permission excludes the evidence before model context construction and before delivery.

The system can still display narrower useful context. A genuine official event need not disappear because a supplementary graph or transcript is unavailable. The unavailable supplement is a limitation, not an invented corroborator. Unsupported or ambiguous news remains context; it does not silently graduate to urgent alerts.

### 4.2 Separate event family from assertion status

A rate-change *topic* can appear in a forecast, rumor, official announcement, retrospective analysis, or actual scheduled release. These are not interchangeable event states. The same distinction applies to proposed acquisitions versus completed acquisitions, planned offerings versus completed financing, and guidance speculation versus management guidance.

News classifiers can propose types, but the factual-event producer must establish which assertion is supported. Initially, structured owner outputs and explicitly supported official-source event families provide the stronger route. New semantic extraction families enter a measured shadow/adjudication process before automatic notification authority. This is factual extraction validation, not a claim about trading returns.

### 4.3 A comparison must have compatible semantics

A financial change compares the same issuer, metric meaning, units, reporting period and revision policy. A surprise compares the released value with a genuinely pre-release, time-stamped expectation of the same definition. A change versus Mastermind's forecast is labeled as that—not street consensus. Missing consensus means no consensus-beat claim.

A candidate/plan comparison stays at the owner's identity grain. A plan change and a candidate observation are not compared as equivalent states. An identity correction preserves the source's supersession relation; it must not look like a new company opportunity simply because a symbol or listing representation changed.

### 4.4 Initial materiality is family-specific and reviewable

| Family | Meaningful change to recognize | What does not qualify by itself |
|---|---|---|
| Prophet | A supported owner-issued new plan or change to an existing plan/availability state; separately, candidate discovery | B1 OPENED interpreted as buyable, another OBSERVED row, a score copied into a new format |
| User conditions | An actually evaluated supported condition crosses its specified trigger, with the owner's re-arm semantics | A matching topic, manual condition, source read failure, or arbitrary model interpretation |
| Company results | A new source publication/revision and a compatible change in supported financial facts | Unmatched period, different currency/basis, marketing language, a model-created adjusted metric |
| Macro/catalyst | Owner-evidenced schedule change, official release, or revision; expectation versus actual explicitly separated | Static fallback interpreted as live confirmation, anticipated policy action classified as occurred |
| News | A supported new underlying development, correction, or changed attributed claim | A syndicated copy, stronger adjective, extra publisher, or vendor relevance/confidence score |
| Monitoring trust | Loss or recovery of the ability to check a scope the user relies on | Last firing being old while the evaluator is demonstrably healthy |

Numerical trigger thresholds belong to their domain owners or an explicit user rule. This architecture does not invent universal materiality weights. For an official categorical event, usefulness of notification does not require a profitable-return backtest. Any claim about predictive edge remains under the existing validation owner.

### 4.5 Cold start, replays and late discoveries

The first activation or newly added scope establishes a baseline and offers a separate review of existing conditions. It does not emit the complete historical backlog as new alerts. Subsequent fires follow the chosen event or threshold semantics.

A historical backfill is not a current opportunity. However, a genuinely consequential fact first discovered late can deserve a labeled late-discovery research update. The decision must name both the old event time and the recent discovery time. Never silently discard all late information or silently relabel it breaking.

A rerun with the same admitted source and semantic revision is a no-op for notification. A changed model paragraph without new admitted evidence is an interpretation update, not a new fire. Explicitly user-requested reminders are a different function and cannot be simulated by recycling old event IDs.

## 5. Situation intelligence without inventing another graph

The situation should make the evidence easier to think with: core development, before/after comparison, relevant business or market mechanism, corroborating observations, contrary evidence, uncertainty, horizon, and what to monitor next.

### 5.1 Anchor a view, do not mint a replacement market event

For event-centered investigations, the anchor is the existing canonical source event. For ongoing company/theme monitoring, the anchor is the existing canonical subject plus a declared monitoring scope. A situation's member set and interpretation can evolve without pretending that it is a new canonical market event every time.

User following binds to that stable scope or canonical root, never to a title or the current representative of a news-similarity cluster. Grouping/ungrouping articles changes presentation, not the user's subscription. Merging views does not silently subscribe a user to an unrelated issuer. A split retains access to the originally followed scope and explains where evidence moved. An owner-issued identity supersession is followed only through the owner's valid alias/migration relation.

The material-change reference and the explanatory-prose revision remain separate. This lets a Chinese translation, better prose, or expanded evidence drawer improve the page without a duplicate interruption.

### 5.2 Use relationship evidence, not plausible associations

Direct issuer/security relationships use the existing Data OS and company-event identity seams. Financial facts come from the financial-intelligence owner; company/theme relationships from their existing graph owner. A relationship carries its evidence, type, relevant time and limitations.

The initial cross-domain product should support direct and explicitly evidenced one-hop connections. More complex paths are a planned expansion, not forbidden ambition. They require each hop to remain inspectable, and uncertainty must not vanish as the chain gets longer.

Shared theme membership permits an investigation link. It does not establish revenue exposure, causal impact, or a directionally tradable read-through. A duplicated data origin must not be counted as independent evidence even if it appears in price, theme and news panels.

### 5.3 Intelligence must preserve the reason a headline can mislead

The retained company exhibit in case C is a better first intelligence example than the earlier hypothetical guidance cut. Its results text explicitly describes tariff-refund contributions to reported gross margin and earnings. A useful alert should make that source-stated contribution visible alongside reported performance, rather than implying that the whole improvement reflects recurring operations.

The exhibit and transcript fixture hashes still match the earlier E3 source package. That is retained-source integrity, not a fresh check against a live official website or proof that all company contexts are served. No guidance cut, organic-growth calculation, consensus beat, sector impact, or future return is inferred from this fixture. [R8]

This illustrates the target: useful synthesis means correctly qualifying the story, not just gathering provenance or adding an AI synopsis.

## 6. Two-speed intelligence and bounded computation

**Fast path:** a valid owner event or explicit evaluated condition produces a concise, correct source-grounded item immediately through the existing producer/consumer path. It does not wait for a model to write an essay.

**Context path:** gather the relevant previous revision, company/financial/market context and evidence links. Generate or update a bounded explanation and contradiction read. A source-revision dependency index or cache must extend an existing artifact/grounding owner; it is not a new global truth store.

**Deep path:** on user investigation or a genuinely complex eligible development, expand context through existing AI/graph owners within a declared evidence and compute budget. State why the extra context was fetched. Missing evidence produces useful narrower output or an explicit research question.

Shared, permission-compatible explanation work is performed once per relevant source/interpretation version, then reused. Personal holdings and theses are joined afterward within the user boundary; they are not included in a shared cache key or shared model payload. Private context caches remain user-scoped.

A model can compare source passages, propose extracted facts, explain mechanisms, identify disagreements and draft monitors. A model cannot convert its own confidence into event truth, change Prophet admission, create a trade, or silently activate monitoring. Structured arithmetic and exact numerical evidence are validated through the owning fact contracts.

If the model fails, the valid underlying alert still works. If a late model response references superseded evidence, it cannot become the current explanation. A materially new, validated contradiction can support a new decision; mere prose revision cannot. Local/hosted model routing and cost receipts reuse the existing model gateway and cost owner, with no provider purchase or new model stack authorized by this document.

## 7. Personal attention policy

### 7.1 Relevance is stated, not implied

Show distinct reasons such as an explicitly followed subject, a supported user condition, an actual holding, an active thesis, or a broad market subscription. A watchlist is not ownership. A graph neighbor is indirect relevance, not a confirmed portfolio impact.

A portfolio weight is shown only with compatible valuation basis, correct identity and disclosed exclusions. A user with no holdings still receives useful default market and Prophet intelligence according to their choices. Personalization cannot be a prerequisite for basic usefulness.

### 7.2 Ordering is not a new trade ranker

Retain the legacy board's canonical IDs, scores, order and push contract. Personal attention ordering is an explicit extension of the Alert Triage/notification owner, separate from Prophet ranking.

The initial proposed policy uses reasoned bands rather than one opaque number: supported time-sensitive user triggers and material corrections to previously delivered items; other relevant material updates; then contextual discoveries. Within a band, source-native materiality, meaningful recency and direct relevance remain visible reasons. No engagement model can suppress an explicitly requested supported trigger.

For You can be selective while Explore remains complete for the user's accessible scope, with bounded history disclosed. Feed fairness is not proof of independent sources. Important low-volume sources must remain discoverable without manufacturing conviction or filling every source quota.

### 7.3 Interrupt, summarize, retain or withhold

The proposed decision dispositions are presentation/policy outcomes, not replacements for the database's delivery statuses:

- **Interrupt:** supported, material, time-sensitive, currently relevant, authorized, and requested for that channel.
- **Digest:** useful nonurgent changes, related updates, or intentionally deferred developments under the user's policy.
- **Retain:** accessible evidence that is worth preserving or investigating but does not justify another notification.
- **Withhold delivery:** unknown eligibility, invalid identity, unauthorized evidence, unsupported category, quiet-hour deferral, or no proven meaningful change. Preserve the specific reason through the existing decision/outbox owner.

The user chooses interruption level, category, schedule and channel. There is no automatic quiet-hours bypass because a model says critical. The same semantic development matched by two user monitors should produce one channel notification that explains both reasons; their subscriptions are not merged or deleted.

Budgets apply to interruptions, not evidence. An explicit user-requested condition cannot be silently dropped by a generic digest cap. A budget-induced deferral stays visible and follows an agreed rule, rather than disappearing into a ranker.

## 8. Monitor semantics and user interaction state

### 8.1 A monitor must describe an executable capability

The current Terminal alert API already supports a closed set: signal/regime/price/RSI, named options events, suite events, and two-step suite sequences. It rejects unknown types, has an existing limit of 50 explicit alert rows, and makes re-arm a user action. This is source-code evidence, not a fresh production API proof. [R9]

Natural language should compile into an admitted owner condition or propose a source-event subscription supported by that owner's catalog. The confirmation shows scope, condition, data basis, cadence, one-shot/repeat behavior, expiration/re-arm, coverage and channel. Anything not evaluable stays an unarmed research draft with a clear limitation.

General source-event subscriptions require an explicit type/validator/evaluator extension in the existing `alerts` ownership. They must not be stuffed into an unrelated price field or run in a hidden third evaluator. Position monitoring remains F08's implicit book-level composition rather than creating one explicit alert row per position.

A watchlist-scope subscription references the existing watchlist and current authorized membership; it does not copy a second list. New members establish a baseline. Removed members stop future eligibility under the scope. Following a theme uses the canonical theme identity and declared event coverage, not a ticker-shaped placeholder.

### 8.2 Predicate changes are not delivery changes

Keep the meaningful condition version distinct from preference changes. Changing a timezone or email choice does not re-arm a fired condition. Changing the monitored predicate revalidates and explicitly establishes the new baseline; it does not re-fire old history accidentally. Source/schema changes can move a monitor to needs-review rather than leave a false-green active badge.

A threshold can support immediate evaluation on creation only when the user chooses that behavior and it is implemented by the condition owner. The default should not silently present an already-true old condition as a fresh crossing. Native one-shot and sequence semantics remain intact until their owner accepts a versioned extension.

The existing thesis monitor's subject-level match must not be described as proof that an arbitrary user-written sentence was evaluated. Say related evidence changed unless the exact supported predicate binding is known. Preserve user-authored text separately from the system's interpretation.

### 8.3 Read, follow, save and send need different persistence

The email outbox is not the user's complete on-site inbox. A user may inspect an event never emailed, or receive an email without ever opening the on-site evidence. Read state must not alter delivery truth or market-event state.

This pass found thesis-specific saved-view code and a separate research document mentioning another product's `user_alerts/read_at`. Neither establishes a generic Mastermind Alert Center interaction store. The bounded search is not a proof of estate-wide absence. [R10]

**Selected architecture proposal:** the existing F08 user-alert API owner also owns a narrow authenticated presentation-state capability. Reuse an existing equivalent relation if its semantics match; otherwise add a small owner-scoped relation containing references and user actions only. Conceptually its key is user plus existing source/situation anchor, and its fields describe last inspected semantic revision, dismissal/archive choice, and relevant action time. It stores no duplicate source facts, no new market-event lifecycle and no email retry state. Its exact physical mapping and reservation are a required owner review before implementation.

A material new revision becomes unread relative to the last inspected revision. A cosmetic prose change does not. Archive hides an item from the current personal view but does not delete source history or a delivery dedup anchor. Since-last-visit is based on explicit interaction/source revision semantics, not merely the current wall clock. Saved views extend a suitable existing views owner only after confirming the scope; they never automatically become subscriptions.

## 9. Email and correction amendments proposed for F08

These are explicit proposed amendments for review, not claims that F08 already implements them or authority to enable the existing drain.

### 9.1 Require an accountable delivery decision

An alert payload must have an admitted category, source/semantic-change reference, required entitlement/use policy, and meaningful recipient relevance. If a user selected categories and category is missing, the stricter path is unevaluable/no-send, not all categories. Unknown recipient/prefs/entitlement/rights also means no-send with a recoverable reason.

Immediately before a send, recheck the current user policy and permitted source use. A historical read authorization does not grant perpetual email access. The original decision reference remains immutable while the send-time eligibility decision can change. An access-revoked recipient must not receive a private correction merely because they saw an older version; a minimal permissible notice needs its own approved content policy.

### 9.2 Durable claim is mandatory for this alert subtype

The shared mailer's existing fail-open ledger policy is unsuitable as a blanket guarantee for personalized subscription alerts. The alert-specific path must require its existing durable claim before attempting the external effect. Implement inside the current mailer/owner interface with explicit subtype policy, preserving unrelated account/support behavior unless separately approved. No second sender or dedup database.

Distinguish a definite pre-send failure from an unknown external result. SMTP can accept a message while the client loses the final response; retrying can duplicate it. An old queued ledger entry after best-effort completion is similarly ambiguous. Never infer no-send merely from queued status, or mint another attempt key solely to escape uncertainty. Reconcile the existing record/provider evidence where available; otherwise retain a visible unknown-result condition and follow an explicitly approved retry-risk policy. SMTP alone is not an exactly-once guarantee. [R6–R7, X1]

### 9.3 Digest/coalescing does not erase original firings

F08 currently preserves quiet-hour deferral and resumes it. The proposed extension groups eligible updates for the same user/channel/window while preserving member source/decision references. The rendered digest tells the latest material state and meaningful intervening changes; it is not a transcript of every refresh.

A digest is a delivery containing multiple evidence references. Never mark unattempted original events sent just because they were omitted from the summary. Exact member disposition belongs in the existing outbox/mail owner; it requires an explicit schema/interface review, not a parallel queue.

When a pending opportunity has expired, the post-quiet-hours message must not urge a stale action. It can summarize that the earlier window opened and closed, retain it in history, or send the latest relevant correction according to the user's agreed policy. This is an auditable disposition, not silent deletion. A user who explicitly requested every supported threshold occurrence retains that different delivery contract.

### 9.4 Corrections belong to the original investigation

Preserve the original source and delivery references. Append/link the owner's correction or withdrawal, recompute affected derived views, invalidate stale cached interpretation, and show both the message's original meaning and the current corrected view.

Previously notified users are candidates for a corrective update when it materially changes the earlier message. Consent, rights and current channel policy still apply. A correction can deserve prominent attention even when the latest headline is less dramatic. An undelivered outdated message is not sent first merely to make the queue chronological.

Retention must preserve effective replay protection. The existing thesis monitor uses outbox fire identity as its backstop; deleting the only anchor while a latch remains fired can cause re-notification. Archive UX must not delete that durable guard. Any long-term compaction belongs to the current owner and retains a lawful dedup reference, not a new ad hoc ledger.

### 9.5 Display only channel observations actually available

A mailer success indicates the configured transport accepted the operation. It does not by itself prove arrival at the recipient's server or that the person read it. The current drain's duplicate-resolution timestamp is reconciliation time, not measured delivery time. Use truthful labels and preserve separate provider delivery/bounce/delay evidence only where the current provider supports it. SES's documented distinction is a research precedent, not a proposed provider switch. [R6–R7, X2]

Subscription notifications need straightforward unsubscribe/manage choices, kept distinct from essential account messages. Current source limits one-click header handling to the marketing class; that internal label cannot decide the external subscription requirements by itself. Google's bulk-sender guidance covers marketing and subscribed messages and requires one-click and visible unsubscribe when the relevant sending-volume scope applies. Exact classification/authentication/volume readiness must be reviewed for our actual traffic before activation. This document makes no legal classification or claim about current compliance. [R7, X3]

## 10. Source-backed journey matrix

The companion JSON records exact pins, blobs, selected byte hashes, row locators, measurements and caveats. A bound source is not an end-to-end passed journey.

| Journey | Concrete input now bound | Required product result | Remaining proof |
|---|---|---|---|
| A — Prophet discovery/update | Real B1 HEAD, receipt and September event rows | Historical OBSERVED stays historical; OPENED stays candidate discovery; partial intake remains visible | Exact current actionable plan/availability source and its authorized UI/delivery adapter; no B1-to-buy substitution |
| B — user's research monitoring | Real ARMED/MANUAL/DATA_MISSING/historical FIRED entries plus the finite alert API | Show what is truly automated; distinguish subject-related evidence from an exactly evaluated user condition | Consented private thesis binding and condition-owner integration; no private users read in this pass |
| C — company-event interpretation | Retained AAPL event metadata, results exhibit and hash-matched transcript fixture | Report the source event with its nonrecurring contribution visible; offer sourced deeper investigation | Financial/graph context contract, contrary evidence, rights-safe serving; no guidance-cut/beat assertion from this fixture |
| D — catalyst continuity | Existing schedule owner and real expectation-versus-release news counterexample | Scheduled, anticipated, occurred and revised remain distinct | Official released-number/revision packet and retained pre-release baseline; reschedule/mutation controls are still specified cases |
| E — news meaning and repetition | Three actual PM ambiguity rows, anticipated-rate-change classification, and existing qbus synthetic grouping definitions | Reject unsupported company/event claims; group story echoes without confidence promotion | Syndication provenance, cross-language repeats and new-member cluster stability evaluation |
| F — correction after notification | Source reference anatomy and retained historical-inspector browser receipt | Original message opens original evidence plus visible correction/current view | Controlled post-send correction/withdrawal case; sampled September episode file contains no correction example |
| G — source degradation | Actual missing Entry Radar intake, manual/missing tripwires, retained synthetic outage browser receipt | Show partial/not checked without discarding healthy context or implying calm | Current last-attempt/last-success reader and recovery behavior end-to-end |
| H — personal delivery | Actual user-rule, category/prefs, outbox and mailer code | Two users receive only permitted relevant content; unknown effect is reconciled, not blindly resent | Controlled two-user/quiet-hours/revocation/unknown-send tests, followed by explicitly authorized real pilot |

Existing qbus tests are synthetic definitions, not proof of independent journalism. Existing #7022 browser receipts explicitly say production acceptance is false; this turn did not rerun them. The eight scenarios now have clear real, retained-fixture, and synthetic-control boundaries instead of presenting all examples as live data.

## 11. Functional design contract before Figma

The page must express the decisions above without exposing a database console. Keep proposed Now / Explore / Monitors / History as user jobs pending visual comparison with the two actual drafts. Reuse their useful components and source-shaped design states; titles alone do not establish which draft supersedes the other.

**Now:** a concise what-changed briefing and queue, with why-for-you, event timing, meaningful limitation and a direct next action. Separate new opportunity, candidate discovery, material correction and contextual update. Do not use green as proof of a trade or urgency as a substitute for evidence.

**Investigation:** before/after, source facts, interpretation, contrary evidence, impact links with connection reasons, timeline, and next checks. A source-stated one-off contribution belongs beside the main result, not buried under methodology. Personal details load only after auth and are cleared when identity/entitlement changes.

**Monitor confirmation:** exact supported condition/scope, data basis, cadence, re-arm behavior, coverage, channels and quiet hours. Include unsupported, manual, limit-reached, auth-expired, save-failed and evaluation-delayed states. No optimistic active badge until owner readback.

**History:** show what happened and what the user was told, separately. Late discovery, historical replay, correction, quiet-hour defer, digest inclusion, send failure and unknown send result have distinct plain-language explanations. A read action never resolves a market condition.

**Meaningful quiet:** checked scope and last successful/attempted evaluation, with incomplete coverage understandable at a glance. Do not advertise an all-clear headline over a missing-source warning buried below the fold.

Mobile preserves investigation place; desktop preserves queue/filter selection with evidence detail. Dark/light and EN/ZH show the same facts and limits. The full state matrix includes no events, no matches, unavailable source, stale evidence, identity uncertainty, revoked access, future/unknown time, and correction. The supplied screenshots are inventory evidence only; no Figma component acceptance or edit is claimed.

## 12. Delivery architecture: extend existing boundaries

| Responsibility | Existing owner / extension target | Boundary |
|---|---|---|
| Market events and signals | Existing domain engines; Prophet candidate/plan/availability owners | No alert-local signal generation, exact-identity allocation, ranking or trade authority |
| Cross-domain evidence | Company-event, financial packet, Data OS identity, existing theme/relationship graph and grounding owners | References and declared adapters, no scraped dashboard truth or second graph |
| Board and investigation | `engine/alert_triage.py`, #7022 view projection, shared renderer and governed assets | Preserve existing machine/push contract; add compatible read-model capability |
| User conditions | Terminal `alerts` API, existing Python/suite evaluators; thesis owner | Add validated source subscription types in place; no third silent evaluator |
| User interaction projection | Existing F08 alert/account boundary; narrow referenced presentation-state extension subject to owner mapping | No user data in public/static artifacts; no misuse of email outbox as entire inbox |
| Preferences | `app/account_prefs.py`, existing shared user preferences and #6907 work | No second settings database; no settings changes that silently rearm conditions |
| Delivery | `alert_outbox`, `alert_runs`, `engine/alert_delivery_drain.py`, `app/mailer.py`, existing off-render scheduler seam | Explicit amendments for alert-only durable claim, ambiguity, digest and corrections; no new sender |
| Measurement | Existing product analytics, source health, evaluation/replay and cost owners | No new trade-performance grader; no public private-user transcripts |

The reader should receive both the current accessible situation and an immutable source locator for the version being inspected. Reads should not produce fires. No browser-local condition engine becomes authoritative merely to animate the page. Retained public source metadata is not a customer cache.

The exact transport for each source is its existing publication/evaluator seam. Event-driven invalidation or scheduled reconciliation can be used where actually supported; do not label a nightly source real-time because the email drain ticks frequently. The current drain's five-minute cadence/fifteen-minute target are source-declared targets, not measured service levels. Measure source available -> ingested -> evaluated -> visible -> transport result separately from user-requested deferral.

## 13. Evaluation and acceptance

The primary acceptance is a complete useful journey, not a schema or score. Start with a user who can see a source-supported change, understand its qualification, inspect evidence, establish a supported monitor, and receive exactly the intended meaningful follow-up or an honest reason it was deferred/withheld.

Use the case manifest as a predeclared source set. Add clearly labeled synthetic controls for corrupt clocks, changed aliases, missing context, revisions, source echoes, permission revocation, and uncertain sends. No private/customer records are needed for early engineering proofs.

Measure factual correctness, meaningful-change precision and missed material developments against the accessible source universe—not only alerts selected for display. Keep entity errors, false occurrence, stale-newness, repeat interruptions, contradictory evidence omissions, missed corrections, and delivery reliability as separate error families. A click is not a correctness label; a lack of clicking is not proof an alert was useless.

The retained company fixture is development gold, not out-of-sample evidence. Later evaluation includes different issuers, source families and held-out time windows with source availability and policy versions fixed. Historical context uses cutoff-visible facts while access to that context still obeys current permissions. Forecast performance, when claimed, uses the existing PIT/forward-validation owners, not alert engagement.

Before a model-derived extraction family gains automatic factual-notification authority, show source-grounded validation for its actual tasks, including negation/expectation/revision and entity ambiguity. Useful nonpredictive factual alerts must not be blocked merely because no return edge is asserted. Conversely, extraction quality does not grant signal/rank/trade authority.

## 14. What is selected, what remains gated

This pass selects a concrete functional architecture for review: semantic-change admission; canonical-root situation views with independent prose revision; explicit relevance and channel dispositions; finite capability-aware monitors; separate read/follow/delivery state; and alert-specific extensions of the current mail path. It also supplies a retained real-source case packet. These are SPEC_ONLY proposals until accepted; no current production rule is silently replaced.

Two implementation-design seams still need exact owner closure rather than hand-waving:

1. **First flagship notification source:** bind the actual currently served plan/availability contract and the entitled return route. B1 candidate identity is present but is not that proof. If the first pilot is candidate discovery instead, its label and acceptance must say so explicitly; it cannot quietly substitute for an actionable opportunity journey.
2. **User interaction and delivery receipts:** confirm the equivalent existing private interaction relation or reserve the minimal F08-owned extension; specify how digest membership, semantic revision, consent/version and unknown-effect handling map to the existing outbox/mailer without a parallel lifecycle. Proposed fields do not mean tables already exist.

These are bounded architecture dependencies, not a reason to rerun a whole-estate audit or start broad backend implementation. The News and Prophet recovery owners remain responsible for their own production systems; this program specifies and coordinates required consumption seams, not a competing repair service.

## 15. Exact continuation and handoff

**Next primary action:** Sol closes the two named owner-interface seams with an exact field/source/consumer map and submits v0.1 plus v0.2 as the functional architecture freeze candidate for adversarial review and Chairman acceptance. The review must challenge the concrete PM/expectation/backfill/manual-monitor/unknown-send cases and the useful company-result interpretation, not merely check that the document is well organized.

After that architecture boundary, compare the two user-shown Figma drafts by actual file identity, component/page coverage and handoff history. Preserve both until a canonical working file and an archive/reference role are explicitly established. Develop the accepted functional journeys on that file, then reconcile #7022 and implement bounded verticals.

Operator handoff requirements for the later build: mission and persona; why the capability matters; current owner/source authority; exact implementation head and collisions; owned paths and non-goals; chosen source/case and UI route; clock/null/correction/privacy semantics; deterministic versus model behavior; failure controls; producer-consumer implementation order; acceptance evidence; stop at missing authority, changed carrier, or unknown effect; return the exact next action. Do not delegate or deploy from this document alone.

No Figma modifications, runtime Jobs, watcher loops, worker dispatches, customer sends, database migrations, merges or deployments occurred in this architecture pass. The existing implementation remains PARTIAL, and the broader intelligence contract remains SPEC_ONLY.

## Evidence index

All repository paths below are at the exact research pins in the header unless a candidate ref is stated. Line ranges describe the files read; source blob and measured sample hashes are in the case manifest. Existing source comments and older handoffs are not proof of current operation.

- **R1:** `engine/us_candidate_episode.py` lines 1–190; `data/us_prophet_rank/episodes/HEAD.json`.
- **R2:** `data/us_prophet_rank/episodes/generations/peg:18dfbb8a9d7152382ca6da8a2ac4177d6ea617dddc7cad082b3645c100fb53a7/events/2026-09.jsonl`; exact complete-file census and samples in the companion manifest. The canonical generation's full validator/JSON-Parquet comparison was not executed in this pass.
- **R3:** That generation's `latest_receipt.json`; `research/prophet_v4/ARCHITECTURE_FREEZE.md`; `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md`; current B4 implementation status requires its owner check, not a doc-only inference of readiness.
- **R4:** `site/news/financial.json`, JSON pointers `/market/0`, `/market/1`, `/market/7`, `/market/13`; `engine/news_events.py`; `engine/qbus.py`; `tests/test_qbus.py` lines 1–175.
- **R5:** `data/cycle_ontology/tripwire_state.json`; `engine/thesis_condition_monitor.py`; F08 architecture's latest-attempt/last-success and private-state rules.
- **R6:** `engine/alert_delivery_drain.py` lines 274–610, especially `decide_row`, category predicate and duplicate resolution.
- **R7:** `app/mailer.py` lines 170–452, especially `_ledger_insert`, `_ledger_finish`, `send` and `_build_message`.
- **R8:** `tests/fixtures/company_intelligence/aapl_fy2026_q3_filing.json`; `aapl_fy2026_q3_ex99_1.htm`; `aapl_fy2026_q3.json.gz`; `research/earnings_intelligence/e3/E3A_AAPL_SHADOW_EXTRACTION_HANDOFF_2026-08-20.md`. Fixture hashes recomputed, historical expected values matched. No current external issuer claim is made from this research read.
- **R9:** Terminal `terminal/app/api/alerts/route.ts` lines 1–180; existing type catalog, user scoping and explicit re-arm.
- **R10:** Terminal `terminal/lib/savedViews.ts`, `terminal/app/api/thesis-saved-views/route.ts`, `terminal/lib/rmsViews.ts` search hits; Macro `research/momoedge/alerts_infra_spec.md` is adjacent-product research, not Mastermind database evidence. This was a bounded search, not an exhaustive absence proof.
- **R11:** `engine/event_calendar.py` lines 1–130 is a schedule owner; it is not a released-value or revision receipt.
- **R12:** #7022 at `c83a5771b54e6e487cdb2d06be45ccbf480e560d`, `mockups/evidence/alert-center-v2/trust-browser-proof.json`. Retained local synthetic evidence explicitly sets production acceptance false.
- **R13:** `research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md`; `research/prophet_v4/CONTRACT_AND_OWNER_MAP.md`. Owner law remains; historical readiness statements require current evidence.
- **X1:** [RFC 5321, section 4.5.3.2.6](https://www.rfc-editor.org/info/rfc5321/), final DATA acknowledgement timeout and duplicate risk.
- **X2:** [Amazon SES event publishing](https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html), distinct send/delivery/bounce/delay events; reference only, no provider adoption.
- **X3:** [Gmail sender guidelines](https://support.google.com/mail/answer/81126?hl=en), applicable bulk-sender requirements for marketing and subscribed messages and subscription controls. No claim about Mastermind's current sending volume or compliance was established.
