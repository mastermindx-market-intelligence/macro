# Alert Intelligence Fabric — functional freeze candidate v0.3

**Status: SPEC_ONLY / CANDIDATE_FOR_ARCHITECTURE_ACCEPTANCE.** Design decisions are selected below; no new route, table, evaluator, delivery capability or production result is claimed implemented. Independent review and Chairman acceptance are outstanding. This is not permission to send customer email.

**Lead:** Sol. Current mandate: continue the intelligent cross-product Alert Center architecture before editing either of the two user-shown Figma drafts.

**Carrier:** Macro Draft PR #7135, `sol/alert-fabric-architecture-20260913`; pickup head `36a002e4c31279befdb18aa3eebd85593019b0a9`. Existing UI implementation #7022 remains at `c83a5771b54e6e487cdb2d06be45ccbf480e560d`, with no writer transfer, checkpoint resolution or release.

**Read pins:** Macro `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2`; Terminal `3db34e7a8e8eca4bef1ca12eba90daab6cc0c10c`; compatible Mastermind Skillpack 1.0.1 at protected master `e8f755d1db35f29a227aaac7335caa86fa2b02c4` (INDEX, COLD_START, RECONCILE_STATE, CLOSEOUT). Source inspections are not deployed-service tests.

## 1. Decision and precedence

Build one coherent attention experience over source-owned intelligence: notice meaningful changes, explain their context and limits, preserve the user's monitoring intent, and deliver material updates without manufacturing urgency. Prophet remains the flagship opportunity source. The alert system does not become a second stock picker, portfolio engine or news corpus.

v0.1 remains the product-thesis background. v0.2 remains the semantic-admission and source-case background. On the two previously open integration seams, this candidate supplies the more specific design: the plan adapter and evidence routes in sections 3–4; the user-state and delivery mapping in sections 5–7. Nothing here silently supersedes accepted F08, Prophet, identity, publication, privacy or notification authority. Proposed amendments are listed explicitly in section 10.

**Source qualification correction:** v0.2's journey-C table says “nonrecurring contribution.” The retained exhibit establishes a tariff-refund contribution, not its recurrence. The required wording is **source-stated contribution, with recurrence unestablished**. Do not infer organic growth, a consensus beat, adjusted earnings, a guidance cut, or a forward return from that case. Historical fixture hashes remain unchanged.

**Route clarification:** F08 section 9 assigns holdings-coupled monitoring and user triage to the existing Terminal shell; it does not authorize a new authenticated portfolio surface in Macro. That requirement controls this design. The actual Terminal `/alerts` page and cockpit already exist. [S1, S2]

## 2. One product experience, existing application boundaries

The shared market investigation remains Macro `alerts.html`, using the existing Alert Triage assembler and #7022's compatible explorer/detail work. It must remain useful without a portfolio or dozens of custom rules. Prophet developments, company events, macro conditions and news context remain available according to their source entitlements; shared does not mean public.

Personal Now, Monitors, user delivery History and holdings/thesis relevance extend Terminal's existing `/alerts` route, inside its existing shell. The two surfaces use one vocabulary, compatible evidence cards and stable source references. A contextual “Monitor this” action on Macro carries an allowlisted source reference to the existing authenticated Terminal workflow. Return navigation restores the originating investigation. No private holdings or user-notice payloads enter Macro's published HTML/JSON, and no new header family or separate alert application is created.

This is a deployment boundary, not two independent alert products. The functional Now / Explore / Monitors / History design describes user jobs; visual design must explain which lens requires the signed-in workspace. Moving private monitoring into a Macro-hosted authenticated client later requires an explicit amendment to F08's route boundary. It is not a prerequisite to the first complete journey.

The existing Terminal cockpit already composes its monitoring answer, timeline, watched conditions, inability-to-check states, detail and condition management. It reads `/api/alerts` and `/api/alerts/receipts`; the new notice view must extend this composition rather than mount a competing second main container or duplicate create form. [S2, S3]

## 3. Exact flagship source adapter

### 3.1 What the source currently provides

`scripts/build_prophet.py` writes original `prophet.trade_plan/v1` plan files, mutable current state files and `prophet.index/v1`. The index is explicitly `nightly-EOD` and `authority_tier=display`. Its `active_count` includes closed plans; `open_count` and each row's `closed` field distinguish the live subset. Original plan admission and the current ticker entry read are different questions. [S4]

`engine/prophet_board_read.py` supplies `prophet.board_read/v1`, with `scope=ticker`, a per-field source/state/value/reason, and source lineage. The measurement can fan out to multiple plans, but applicability remains per plan. `available`, `blocked_data`, and `not_applicable` remain distinct. [S5]

There is a source/consumer disagreement: `scripts/build_site.py::us_stance_projection` prefers a truthy `entry_status` over the board read; the card template describes that basis as fresh. The source contract identifies `entry_status` as the frozen origination admission stamp. The helper also maps unknown nonempty statuses to `wait`. This is code-path evidence, not a measured production incident. **Do not use the rendered verb or tooltip as the alert's source truth.** Alignment of the existing consumer belongs in the relevant owner build/review before release. [S6]

### 3.2 Field-to-meaning map

| Alert meaning | Exact existing field/source | Selected rule |
|---|---|---|
| Plan identity | `plans[].id`; original plan file ID | Preserve the owner's plan ID and namespace. Never collapse all plans with the same ticker. |
| Instrument label and join | `plans[].asset`, `board_read.ticker`, source identity bridge | Ticker is a label/join hint, not globally unique identity. Resolve market/listing through the existing identity owner before private holdings or cross-market joins. Conflicts block that join. |
| Original signal history | `formation_date`, `signal_date`, `confirmed_date`, `observed_date`, `signal_date_basis`, `signal_provisional` | Preserve source precision, basis and provisional state. An absent date stays absent. |
| Original admission | `entry_status`, `admission_class`, `selection_era` | Historical detail only. It cannot establish present availability. |
| Current entry read | `board_read.fields.status.state/value/source/reason` | Use an available recognized owner value with its actual source vintage. Never substitute `recommended_action`, a card verb, or a score. |
| Plan applicability | `closed`, owner lifecycle state and closure evidence | Closed wins over a current ticker read. Closed is not missing data; no fresh entry instruction. Missing explicit applicability is unknown, not open. |
| Source time | `board_read.as_of`, matching `board_read_lineage.sources[].as_of`, underlying source receipt | Match the clock to the source that supplied the status. A library timestamp cannot freshen a fallback board value. |
| Whole-input health | `source_asof`, `source_board_asof`, `source_delayed`, `source_unknown`, `source_mixed_vintage`, `source_basis` | Use for bounded source health, not as invented per-field timestamps. Publication `asof/recorded_at` never prove freshness. |
| Price/basis | `price_basis_date`, available `price_frame`, relevant source price/basis receipt | Inconsistent or unknown basis cannot support an entry-window claim. Do not recalculate entry eligibility in Alert Center. |
| Plan levels | `entry`, `entry_zone`, `invalidation`, `targets`, `entry_basis` | Quote the owner's permitted values and vintage; no alert-local stop, target or position-size formula. |
| Reconstruction/integrity | `origination_mode`, `origination_note`, `backfill_executed_at`, `integrity_status/reason` and owner correction records | Reconstruction is not new opportunity origination. Unknown integrity is not silently passed for stronger notification claims. |
| Attention context | Source `_priority_score` and declared `plans_sort_key` | Retain source order in the source view. It is not a win probability or permission for the alert system to rerank trades. |
| Management explanation | `state.change_reason`, `pulse`, `thesis`, bilingual source copy | Explain the plan within its authority. These fields do not originate the entry trigger. |
| Evidence revision | Accepted source publication reference, artifact hash, exact plan ID and relevant correction lineage | A mutable latest file or a browser URL alone cannot reconstruct the version that caused a past notification. |

A board read can fall back field-by-field. Its single block `as_of` does not always identify the source of every field. The adapter requires a source-specific receipt for the field used in a transition; where current lineage cannot disambiguate that receipt, the producer must add it under the existing publication owner. The alert displays a narrower dated read or unavailable state until this is satisfied. No blind use of the latest timestamp. [S5]

### 3.3 First meaningful change, not invented buyability

The first flagship vertical is a **source-issued plan publication or material plan/current-read change → useful alert → exact evidence**. A current-read item says what the latest eligible source observation changed to and names its completed-session basis. It does not claim intraday availability or the future V4 `ENTRY_OPEN` contract merely because a legacy status sounds actionable.

A new B1 candidate remains candidate discovery. An unchanged observation remains evidence. A closure/retraction is distinct from an entry-state change. Missing from a capped display list is not a source closure. A fresh source failure is a monitoring limitation, not a negative investment signal.

For an inferred transition, compare the same plan and approved field set across two eligible accepted source publications. Use the owner's native event identity when one exists. Otherwise extend the existing source adapter's deterministic change projection: `(owner namespace, plan ID, previous publication, current publication, transition kind, method version)`. This is a derived comparison key, not a new market-event registry. Hashing only the latest value is insufficient for an A→B→A sequence. Cosmetic fields, source array order, prose, translation and model version do not create a transition.

A newly enabled monitor establishes its baseline without mailing the past. An absent predecessor supports “current baseline,” not “just changed.” If several source periods were missed and their intermediate revisions are unavailable, present a net change since the last successful check; do not invent the intervening events. Source retention and freshness gates are prerequisites for automatic transition delivery, not deferred cleanup.

### 3.4 One source reader and history owner

Reuse the canonical local plan-index root and source-reading ownership already used by `app/prophet_lab.py` and `engine/prophet_lab/sources.py`. Factor a typed reusable reader there rather than having the alert adapter scrape the Lab response or create another loader/configuration ladder. The existing `read_prophet_index` returns `{}` for unreadable input, so its legacy wrapper is not sufficient to establish an empty healthy board; the new typed read must preserve unavailable versus valid empty without silently breaking its old consumers. [S7]

Original plans already have immutable publication behavior, while current index/state files change. Historical current-read evidence therefore requires the existing Prophet publication owner to retain and resolve the exact accepted artifact revisions used by notices. Reuse an existing accepted archive when it satisfies this; otherwise add bounded revision retention to that owner. No user database becomes a second copy of Prophet market truth. The new resolver receives an opaque approved revision reference and plan ID, never an arbitrary path or URL supplied by a browser.

This is an implementation dependency with a chosen owner and interface, not a claim that current production already supports historical retrieval. No source archive means no automatic historical-transition promise. A controlled pilot must read back the original revision through the real serving path before sending.

## 4. Exact customer routes and evidence behavior

**Existing routes:** Macro `alerts.html` for shared investigation; Terminal `/alerts` for authenticated personal monitoring; Terminal `/api/alerts` for user conditions and `/api/alerts/receipts` for existing monitoring/delivery data. Existing current-plan cards have `pv-<plan_id>` DOM IDs on the stock board and a stock/ticker destination. [S2, S3, S8]

**Selected extensions, not currently implemented endpoints:**

| User/API action | Owning location and contract |
|---|---|
| Open a personal alert | Terminal `/alerts?notice=<notice_id>`; add selection/return behavior to the existing page/cockpit. |
| Read exact notice + evidence | Terminal `GET /api/alerts/notices/<notice_id>`; authenticated owner read, then source-entitled revision resolution through the existing private backend channel. |
| List personal notices | Terminal `GET /api/alerts/notices`; stable pagination and snapshot boundary, explicit availability, no mutation on read. |
| Mark inspected or archive | Terminal `PATCH /api/alerts/notices`; allowlisted action and explicit IDs actually presented, with owner checks and action-version conflict handling. |
| Create/follow a supported scope | Existing Terminal `/api/alerts` extended with a finite source-subscription condition; no new registry or hidden evaluator. |
| Change notification preferences | Existing account-preference owner and its existing Terminal connection; no second preference store. |
| Inspect today's source board | Existing Macro `us_stocks.html#pv-<encoded_plan_id>` as a current-view jump, only after hydration/selection behavior is proven. It is not the historical notice route. |

The detail response separates `at_notice` from `current`: original permitted source references and interpretation version versus today's independently resolved source. It also carries relevant owner corrections, personal relevance references and separate delivery observations. Missing original evidence returns “original evidence unavailable,” with an optional separately labeled current view; latest data is never substituted into the original slot.

Auth is checked before private data is assembled. Evidence authorization is rechecked on both original and current reads. A user-owned notice ID is a locator, not a bearer credential. Source-use revocation can withhold details even when the notice exists. Private responses are not shared-cacheable; account changes clear cached personal responses. No authentication token, private holding amount or arbitrary fetch URL is embedded in a link.

Opening a URL, rendering a list, a mail-client link preview, or an HTTP GET does not mark anything read, activate a monitor or send email. The user inspection acknowledgment is a separate explicit mutation after the relevant detail is actually presented. The original notice remains selected through login, language change and return navigation. Shared-source links may be shared; personal notice links still enforce ownership.

Macro and Terminal require compatible navigation, but not a new auth system. Cross-app session continuity must be demonstrated via existing sign-in behavior rather than assuming shared cookies. A temporary signed-out step preserves the safe intended destination. No iframe or new generic cross-origin message channel is required by this design.

## 5. Selected private data mapping

### 5.1 Minimal extension, not another alert backend

Current schema has `alerts` for conditions, `alert_runs` for evaluation receipts and `alert_outbox` for pending/delivered channel work. None is the complete record of things a user can inspect without email. The source-schema census did not identify an equivalent generic notice/read relation; this is not an exhaustive live database claim. Thesis saved views are a different domain. [S9, S10]

**Select one new F08-owned relation: `alert_notices`, inside the existing Supabase user-data plane.** It stores a user's notice of a source change and references, not a duplicate market event. No new database, scheduler or sender. Before implementation the schema owner reconciles the actual catalog/reservations and reserves the next migration by the established process; no migration number is guessed or reserved here.

| Concern | Exact selected physical home |
|---|---|
| User condition/follow scope | Existing `alerts.condition`, with the versioned extension below |
| Source facts, history and shared interpretation revisions | Existing source/publication/grounding owners, referenced by notice |
| Personal meaningful notice and interaction | New `alert_notices` under F08 |
| Channel delivery grouping and due work | Existing `alert_outbox`, with a recognized bundle payload |
| External email attempt/result | Existing `email_log`, with alert-subtype effect metadata |
| Evaluation and delivery run health | Existing `alert_runs`; no private notice content in global run receipts |
| User channel choices and schedule | Existing account preferences |

### 5.2 Notice row semantics

Proposed fields are `id`, `user_id`, `source_namespace`, `anchor_ref`, `semantic_change_ref`, `evidence_revision_refs`, `notice_kind`, `decision_version`, `decision_at`, `relevance_refs`, `monitor_version_refs`, `preference_fingerprint`, `decision_basis`, `initial_channel_plan`, nullable `corrects_notice_id`, `read_at`, `archived_at`, `interaction_version`, and nullable `email_outbox_id`.

The uniqueness key is `(user_id, source_namespace, semantic_change_ref)`. The source namespace prevents unrelated domains colliding; the user key prevents one recipient's notice silencing another's. `source_namespace` and references use approved source adapters, not a second identifier allocator.

The source/decision columns are immutable. User actions update only explicit interaction fields through allowlisted owner mutations. Delivery assignment is service-owned and can reference only a same-user email outbox row; direct owner UPDATE of decision or assignment fields is not permitted merely because the user can read their row. `corrects_notice_id` is same-user and follows actual owner correction lineage. A subsequent source correction makes a new notice rather than rewriting the original decision.

`decision_basis` is a bounded receipt of the actual notification policy and supported predicate definitions used, not just their hashes. If an owner provides a retrievable immutable version, reference it; if its current preference/condition row is mutable, preserve only the needed alert-specific values and finite rule definition in this private decision receipt. A hash alone cannot reconstruct a deleted predicate or earlier quiet-hour choice. This is historical decision evidence, not a second writable preference or monitor registry. No unrelated user metadata is copied.

Relevance stores references to the authorized holding/watchlist/thesis/monitor used, and the reason category. It does not copy a portfolio book or private source body. User-supplied arbitrary rows are not accepted as system-generated notices. The reader can show current relevance separately; adding a new monitor after an old decision does not rewrite who/what justified that earlier decision or cause a retroactive send.

Notice creation, channel assignment when requested and monitor progress advancement occur in the same database transaction. The complete set of matches for a user/change is resolved against the same subscription/membership snapshot. Concurrent duplicate evaluation reconciles the existing unique row. An enqueue failure cannot consume the progress marker and lose the change.

This replaces v0.2's suggested aggregate “last inspected revision per anchor” with a precise per-notice acknowledgment. **No separate aggregate attention-state table is selected for v1.** A situation card derives its unread count from its notice members. A late insertion or concurrently arriving change cannot be swallowed by acknowledging everything before an approximate timestamp.

### 5.3 Read, archive and follow behavior

Opening notice N1 acknowledges N1, not a later N2 that arrived while the drawer was open. For a group inspection, submit the explicit rendered notice IDs and their interaction versions. No “mark whatever is latest now” mutation. A stale conflicting archive/unarchive change returns a conflict/readback, not silent last-writer wins; reading can be idempotent without rewriting decision facts.

Archiving hides the selected notices from the personal active view. It does not stop a monitor, delete source history, clear email deduplication or archive future revisions. A newly material revision is unread even when the previous item was archived. Follow/unfollow changes the existing monitor, not `read_at`. A prose or translation improvement does not create a new notice.

Keep notice/source-reference retention sufficient for the declared user history. Account deletion and rights-driven removal follow the existing account/data policy; “append-only” is not permission to retain personal data indefinitely. No queue purge or archive action removes the only replay guard while its source/monitor remains capable of replaying the event. Existing-source tombstone/retention rules must be reconciled before compaction.

### 5.4 Source-subscription condition in the existing alerts owner

Choose a versioned `source_subscription` condition in `alerts`, admitted by the same existing condition API and handled in the existing Python alert-evaluation lane, not a third evaluator. Its definition names `source_namespace`, supported event kinds, typed `scope`, `predicate_version`, baseline policy and requested delivery behavior. The source-subscription adapter must pass the owner-validated source-publication/change contract, including an explicit no-change or unavailable result; it does not execute arbitrary model instructions or user-provided URLs. Scope is a discriminated reference to plan, security/listing, company, theme or an existing authorized watchlist; unsupported scope/family combinations cannot activate.

The current SQL requires `alerts.symbol` to be nonnull. **Do not encode a theme or plan ID as a fake ticker.** The selected schema amendment allows `symbol=null` only for the validated source-subscription subtype with a complete typed scope; legacy conditions retain their required symbol and existing behavior. API and evaluators must be deployed with subtype support before these rows can be created.

Predicate definition and service-owned evaluation state must be separated inside the owner's versioned condition envelope or an equivalent accepted existing field. Only the evaluator advances its `last_consumed_source_ref`/scope-baseline facts through a guarded update against the expected predicate version. Client preferences cannot overwrite that state. This is progress for the existing monitor, not a replacement scheduler lifecycle.

Creating a subscription establishes a baseline; it does not replay all retained source history. Watchlist membership is read from its existing authorized owner. Each newly included member gets a baseline and removed members lose future scope eligibility. Membership access loss is unavailable, not an empty healthy watchlist. Legacy one-shot alerts retain explicit re-arm; continuous event following does not silently alter that contract. Implicit portfolio monitoring remains book-level F08 composition and does not create one explicit alert row per holding.

## 6. Email and digests remain one delivery system

### 6.1 Bundle mapping

Keep the existing `alert_outbox` status vocabulary and global `fire_event_id` uniqueness. Existing legacy fire identities are unchanged. New notice deliveries use a distinctly versioned `alert_notice_bundle/v1` payload and a namespaced key including user, channel and bundle identity. One immediate message is a one-member bundle; a digest is a multi-member bundle in the same queue.

The outbox payload contains the exact member notice IDs and decision/evidence references, intended schedule window, user-timezone interpretation, preparation state, content hash and per-member presentation disposition. The reciprocal `alert_notices.email_outbox_id` prevents the same notice from independently joining both an immediate email and a digest. The new subtype's aggregate `alert_id` may be null rather than impersonating one of several user conditions. Legacy readers must distinguish subtype explicitly.

Collecting a digest and binding new members happen transactionally through F08-owned database operations. Use a unique user/channel/window group and consistent row-lock order. Locking and unique constraints provide the database coordination mechanism; they do not prove an external email effect. [X1]

**No duplicate queue:** from creation, a notice with email scheduled is assigned to an existing outbox row, possibly deferred until the digest window. There is no separate notice scheduler polling a second queue. A grouping transaction either creates/joins the intended collecting outbox row or finds that a competing transaction already assigned the notice.

A collector cannot append to a sealed envelope. A genuinely later eligible change gets the next eligible window, or an explicitly permitted immediate path for that new notice. Do not manufacture a burst of same-window digests when a content limit is reached. A digest can summarize and link a bounded set while preserving clear counts and member dispositions; a user who requested each supported occurrence retains a different, explicit contract. Size limits and overflow behavior are tested against the chosen existing mail renderer before activation.

### 6.2 Seal, authorize, send

At window close, the existing drain rechecks recipient, current consent, category, entitlement, source rights and current relevance/expiry policy for each proposed member. Unknown required facts mean no-send or narrower permitted content, with a reason. Missing category is not “all categories.” A shared digest inherits the strictest required access of the content actually included; unauthorized members are removed before model context and message generation.

Prepare the permitted member set and source references, render the allowed template, and seal membership/content with a checked version update. Rights/consent are checked again at the actual send boundary. If they changed before any effect, recomposition requires a new checked preparation revision of the same unsent bundle. A model must not retain the removed member in prose. If a model response is late relative to its referenced sources or permissions, discard it and use a valid source-only template or defer.

Once an external attempt may have begun, the attempted envelope is immutable. Later changes are represented as a new correction or later update, not editing what the user may already have received.

`covered_in_summary`, `linked_only`, `withheld`, and `no_longer_relevant` are content dispositions, not substitutes for outbox delivery status. A sent digest does not mean every underlying fact was explicitly stated, read, or still actionable. Original notice history retains how each member was handled. A headline/summary can never encourage entry into a window known to have expired while delivery was deferred.

### 6.3 Alert-subtype effect contract in the current mailer

For the new subtype, extend `email_log` with the minimum typed attempt metadata: delivery policy/subtype, bundle/content reference, effect state and relevant observation times. Use the existing ledger and transport; do not create another email ledger. Original mailer `STATUSES` remain intact for current consumers.

Effect observations distinguish `not_attempted`, `attempting`, `accepted`, `definitely_not_accepted`, and `unknown`. These describe the external attempt, not a new work scheduler. The selected policy is:

- A durable unique claim and durable pre-effect `attempting` transition are mandatory before this subtype calls SMTP.
- A failed durable claim produces no send. The existing support/account fail-open policy is not changed by accident.
- A definite pre-acceptance failure can use the existing bounded retry scheme and a new attempt reference after proof that the prior attempt had no accepted effect.
- A timeout after possible acceptance, a crash after `attempting`, or an unresolvable queued claim is **unknown**, not an excuse to mint another attempt key.
- An unknown bundle remains withheld from new send attempts while the same ledger/provider evidence is reconciled. With no resolving evidence, show uncertainty and require the declared operator/user resend-risk decision; automatic retry is not authorized solely by elapsed time.
- `accepted` means the configured relay accepted the message. Recipient delivery, bounce and personal read require separately supported observations. No success inferred from an outbox status copied without evidence.

SMTP explicitly has a final-acknowledgment ambiguity that can cause duplicate delivery; this design does not promise external exactly-once delivery. [X2] The current mailer's generic queued/retry behavior must not reach the new subtype until these rules and every relevant drain/reader are integrated. Unknown is projected through existing pending status plus typed subtype metadata and excluded from send selection, not invented as an unsupported value of the old status column.

Subscriptions require clear manage/unsubscribe behavior through the existing preference and unsubscribe owners. Applicable subscribed-message sender requirements are an activation check, not determined solely by calling a template transactional. No sender-volume, legal-compliance or inbox-placement claim was verified here. [X3]

## 7. Corrections, continuity and useful intelligence

A source correction invalidates affected shared interpretation versions through the existing grounding/publication owner. The notice remains tied to its original evidence reference. A material corrective notice can point back to it, with current user access and channel choices rechecked. Previously seeing a paid source does not authorize emailing revoked source text now.

An undelivered obsolete bundle is not sent first to preserve chronological order. Before any external effect it may be recomposed or withheld with member reasons. A possibly sent or accepted envelope is never edited; send a supported correction as a separate linked notice when policy permits.

Situations remain source-rooted views, not free-floating model memories. Each contains: the principal development; a comparable before/after; useful mechanism or relationship with evidence; source-stated qualifications; contrary observations; relevant unknowns; horizon and next checks. Direct source facts, computed facts and model interpretation are visibly distinguishable without making the default page a methodology report.

The fast path works without a model. Contextual synthesis may add insight, including a genuinely evidenced contradiction, but an improved paragraph does not reset unread state or interrupt again. Shared explanation reuse is allowed only for identical evidence/use permissions; private holdings and research remain user-scoped. Official-source structure, negation/expectation/revision handling and entity disambiguation are required before model-extracted event families gain automatic factual-notification authority.

The company case from v0.2 should display the source-stated refund contribution beside reported performance, and keep recurrence unknown. The PM ambiguity cases remain no company-specific notification. The anticipated-rate headline remains an attributed expectation, not a completed policy event. This is intelligence that qualifies and connects information, not merely attaches a citation list.

## 8. Adversarial design walkthrough — not executed product tests

These are predeclared expected behaviors for implementation. No browser, database, SMTP or model acceptance pass is claimed by this table.

| Case | Required outcome |
|---|---|
| 1. Old admission says eligible, current board read unavailable | Historical admission remains visible; current entry unavailable; no current-availability alert from the old stamp. |
| 2. Current status came from board fallback but block date came from library | Require source-matched vintage; no freshness upgrade from the unrelated clock. |
| 3. One ticker has two plans, one closed | Preserve both IDs; closed plan has no current entry instruction. |
| 4. Valid new plan, no historical state predecessor | New owner-issued publication can be reported with its own evidence; no invented transition history. |
| 5. Latest source read fails after prior success | Monitoring degraded; retain old dated evidence; no empty/current claim. |
| 6. A→B→A within retained source revisions | Distinct source transitions remain distinguishable; a latest-value hash cannot suppress the return transition. Missing intermediate revisions are disclosed. |
| 7. Old email N1 opened while N2 arrives | N1 acknowledged only; N2 stays unread. GET/prefetch acknowledges neither. |
| 8. Two monitors match the same user's change | One personal notice and one channel assignment; both contemporaneous reasons can be recorded. |
| 9. Two users match the same source event | Separate user-owned notices and delivery keys; no cross-user suppression or leakage. |
| 10. Immediate and digest workers race | Transaction/constraint yields one assignment; loser reconciles existing state rather than sends. |
| 11. Digest seals while another notice arrives | Sealed membership unchanged; later notice receives a valid later/immediate disposition. |
| 12. Consent or source rights revoked before send | Recheck; exclude/withhold before effect; no private fact persists in generated summary. |
| 13. SMTP accepted but acknowledgement/ledger update lost | Unknown result; no blind retry or new key; reconcile. |
| 14. Condition is manual, unsupported, or its predicate changed | No false active-evaluation badge; definition version and baseline reconciled under owner. |
| 15. Archived item later materially corrected | Original preserved; corrective notice unread; archive did not unfollow or delete deduplication. |
| 16. Model timeout, stale response, or translation-only revision | Valid source-only experience survives; no invented fact and no duplicate interruption. |
| 17. News says an action is expected; ambiguous PM token present | No completed-event/company assertion solely from classifier/type/rank. |
| 18. Historical evidence no longer retrievable | Original slot says unavailable; separate current view is not a retrospective substitute. |

Prototype these outcomes in source-shaped desktop/mobile and EN/ZH states. Use actual retained inputs from the existing case manifest for applicable examples; synthetic races and failures must be labeled synthetic. Product measurements include time to understand a change, successful evidence return, supported monitor completion, useful versus repetitive notifications, missed eligible developments and correction propagation. Click rate is not factual correctness or trading edge.

## 9. Bounded implementation order after acceptance

**V1 — One trustworthy Prophet change on site.** Extend source-specific revision/freshness mapping, create one typed alert projection, render its current and historical evidence on the existing surfaces, and reconcile the original-admission/current-read consumer mismatch. Producer, reader, UI, failure behavior and proof belong together. Candidate discovery cannot stand in for the intended plan/current-read journey.

**V2 — Follow and return.** Extend the existing condition API/evaluator with the selected scope; add the minimal notice relation and exact read/archive actions; prove a real next eligible change through the existing authenticated `/alerts` composition. Include two-user isolation, baseline/no-backlog, false-empty and old-notice/new-notice cases. No email activation needed for this first personal capability.

**V3 — Reliable immediate email.** Extend the existing outbox/mailer and related readers for recognized bundle/effect semantics, preferences and source-safe content. Prove opted-in versus opted-out, unknown-result reconciliation, authentic evidence return and unsubscribe. Only then an explicitly authorized controlled recipient pilot, followed separately by production acceptance.

**V4 — One intelligent developing situation.** One source-backed company event plus relevant financial/relationship context, qualification, contrary evidence, a meaningful update and correction. Use the existing news/event and company-intelligence paths. A renamed same-source bundle does not complete this vertical. Model-independent fallback and retained revision identity are required.

**V5 — Digests and broader monitoring.** Extend the same queue with transactional grouping and send-time membership/content reconciliation. Expand event families and regions through native owners, including China Prophet, without assuming US plan identity or US exchange calendars apply universally. A nightly source remains nightly until its owner supplies and proves another cadence.

Schema rollout is expand → compatible subtype-aware readers/drains → disabled producers → integrated tests → controlled activation. Older consumers must reject or safely withhold unknown bundle/subscription types. No schema-only or API-only PR is final user acceptance. Migration reservation/application, repo merge, deployment, source readiness, actual delivery and final acceptance are separate facts.

## 10. Explicit amendments and no-rebuild limits

The selected recommendations require review of these precise amendments, not a blanket replacement of F08:

1. A minimal F08 `alert_notices` relation for personal notice/reference/interaction state.
2. A typed source-subscription extension of the existing condition/evaluation owner, including constrained nullable symbol and protected evaluation baseline state.
3. Versioned bundles/digest membership inside `alert_outbox`, alert-specific effect metadata in `email_log`, and conservative unknown-effect handling.
4. Source-owned revision retention/resolution and per-field lineage needed for faithful alert history.
5. Existing board-consumer precedence reconciliation so a historical admission stamp does not masquerade as the current source read.

Preserved: Terminal ownership of holdings-coupled UI; existing macro board assembler and #7022 carrier; native Prophet/News/event/identity/graph authority; source/timing/null/correction law; account-preference owner; current outbox/mail owner and legacy IDs; operator/customer separation; no trading authority from model synthesis; no second portfolio, bus, evaluator, sender, scheduler or general memory system.

Proposed API names and column names identify an implementation design, not deployment. If an equivalent accepted relation/interface is discovered at implementation pickup, reconcile and reuse it before migration. Do not create both. Scope reduction needed for a bounded first release does not erase the full intelligence/region ambition.

## 11. Self-review disposition and remaining gates

Sol's adversarial self-review found and addressed: historical/current source precedence; source-mismatched dates; unsupported recurrence language; hidden Macro-versus-Terminal route expansion; generic outbox mistaken for an on-site inbox; read acknowledgments swallowing a concurrent revision; competing instant/digest assignments; unknown SMTP result treated as a safe retry; and typed-scope IDs disguised as tickers. These are design repairs and source findings, not implemented fixes. No independent reviewer is claimed.

**Architecture-level closure:** the two open seams from v0.2 now have selected source fields, route owners, record homes, mutation/transaction semantics, failure behavior and acceptance cases. They are no longer unspecified. The candidate is ready to be challenged as a functional whole.

**Still separate:** independent architecture/owner review and Chairman acceptance; schema catalog/reservation/application; private source-history serving; renderer and evaluator implementation; exact-head CI and controlled interaction/delivery tests; production proof. The existing #7022 remains PARTIAL and the expanded capability remains SPEC_ONLY. No false-green projection or release follows this document.

**Next primary action:** review this exact candidate against the 18 cases and accepted owner law; on acceptance, compare the two actual Figma files and complete one canonical visual specification for these journeys. Preserve both drafts until their actual IDs, component coverage and lineage determine the working/reference roles. Do not start a third design or let an attractive component showcase substitute for a complete user journey.

## Source anchors

Repository locators below are pinned evidence, not current production attestations. v0.2's source manifest remains the reference for its retained-data cases.

- **S1:** Macro `research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md`, sections 1–9, at the Macro read pin. In particular section 9's Terminal route boundary and sections 5–8's user-data/delivery ownership.
- **S2:** Terminal `terminal/app/(shell)/alerts/page.tsx`, blob `583191e487ebcb320c6ff1ec02b0aec88d17c686`; actual `/alerts` shell composition.
- **S3:** Terminal `terminal/components/alerts/AlertsCockpit.tsx`, blob `27eab37c8f3a92602d524567788687e51bf98b61`, lines 1–170; current condition/receipt reader and cockpit composition.
- **S4:** Macro `scripts/build_prophet.py`, blob `239319d023383800681a96f4a8454d1fa3f2936c`, lines 2275–2385, 2440–2555 and 2727–2745; plan/index/time/authority/board-read mappings.
- **S5:** Macro `engine/prophet_board_read.py`, blob `00395ac9e3db7c22bccec5f993259e75ce075032`, status selection plus lines 390–end; ticker-scope applicability and source clocks.
- **S6:** Macro `scripts/build_site.py`, blob `9a62e3f66df3d92ff3516d2f3428538eeef22483`, lines 4954–4977; `templates/_us_prophet_plan_cards.html.j2`, blob `62acc73378fa7be188b72ce6af1f9a3de508912e`, stance call and tooltip.
- **S7:** Macro `app/prophet_lab.py`, blob `acba294f9c0a948ec32d4c14b6f25644b501453e`, existing auth/private reader roots; `engine/prophet_lab/sources.py`, blob `3f5ded9cec2e1e9ce19881b08c175e993efd6673`, lines 628–645, unreadable-to-empty compatibility wrapper.
- **S8:** Macro `_us_prophet_plan_cards.html.j2`, same blob as S6; `_prophet_card.html.j2`, blob `713e0e49b037e9f2b8c2a716265bff6f900a2c9e`, line 592, `pv-` ID; `scripts/build_site.py::_write_us_payload`, lines 5307–5415, paid hydration from the same partial. Anchor presence is not a browser proof.
- **S9:** Terminal `supabase/migrations/0001_init.sql`, blob `faedc215bde11d751d8054f1766ffb0dd2b461d7`; `0013_alert_runs_outbox.sql`, blob `28a7f72af5726fb04bb9ef1bef1684564cdddf64`. Directory/source declaration census is not a live schema census.
- **S10:** Terminal `terminal/app/api/thesis-saved-views/route.ts`, blob `5807a90ce7623824017058daee83e0b4d7608acd`; this is thesis-scoped, not evidence of a generic notice relation.
- **S11:** Macro `engine/alert_delivery_drain.py`, blob `ae8aa4b6ff2bde0867ad24793cd731e207903a06`, and `app/mailer.py`, blob `83e8971a0ff9dc75bfb323f33bcc1b771f18a9b0`; current category, status, ledger and retry behavior as inspected in v0.2. Fresh implementation pickup must re-read before editing.
- **X1:** PostgreSQL official [explicit-locking documentation](https://www.postgresql.org/docs/current/explicit-locking.html), database row-lock semantics. No production database version or concurrency test is asserted.
- **X2:** [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321.html), section 4.5.3.2.6, SMTP final-acknowledgment duplicate risk.
- **X3:** Google [Email sender guidelines](https://support.google.com/mail/answer/81126?hl=en), subscribed-message requirements where applicable; no legal classification, sending volume or delivery-reputation assessment performed.
