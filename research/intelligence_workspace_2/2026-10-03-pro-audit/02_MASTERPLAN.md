# Mastermind Intelligence Workspace 2.0 — hardened masterplan

Version: 1.0, 2026-10-03. Status: **implementation planning specification; not production acceptance**.

Goal: make a multi-day market investigation resumable, inspectable and shareable without moving domain truth into layouts, chat memory or a competing research database.

Architecture: a thin Investigation capability in Terminal's existing authenticated user-state responsibility; owner-native layouts, beliefs, facts, evidence, calculations and operational objects; explicit reference retention, temporal and permission contracts. Macro remains the owner of deterministic market intelligence and the existing Brain compiler/gateway. See [audit](01_AUDIT_AND_RECENSUS.md) for corrections and [source ledger](05_SOURCE_LEDGER.md) for evidence IDs. Exact execution tasks and tests are in [03_EXECUTION_AND_ACCEPTANCE.md](03_EXECUTION_AND_ACCEPTANCE.md).

## 1. Product thesis and boundaries

**Save the inquiry and the evidence of what was believed. Refresh what can change. Explain the difference.**

An Investigation is the durable record of a question, its subjects, the canonical objects used to study it, authored research history and the explicitly saved baseline. It is not a verdict, an AI chat thread, a portfolio, an alert, or a synonym for every dashboard.

The user must be able to answer: What was I trying to understand? Which belief version did I hold? What evidence and assumptions supported it? What contradicted it? Which sources changed or became inaccessible? What is current versus historical? What would discriminate between explanations? What should I investigate next?

A normal monitoring layout remains a normal layout. Do not require a thesis or question merely to open charts. Offer explicit “Continue as Investigation” from an existing layout or owner-native surface. Do not batch-convert saved layouts, fabricate research intent, automatically publish a Thesis, or promote a Prophet candidate. [U01; S05–S08]

### Product hypothesis and falsification

The hypothesis is not that more persistent panels improve judgment. It is that retaining meaningful intent, provenance and comparison state reduces resumption error and makes changed evidence easier to interpret. Test against the existing saved-layout/notes workflow using the same tasks and information. Use interrupted investigations and delayed returns, not only first-use demos.

Primary outcomes: correct recovery of the original question and belief version; accurate distinction between baseline/current/unknown; recognition of contradictions and missing comparison inputs; time to a correct next research action. Also measure workload, navigation effort and unwanted context changes. A small formative study can identify failure modes but cannot establish investment-performance benefits or broad statistical superiority. Predefine the scoring rubric and report the sample and uncertainty. Failure means simplifying the shell or persistence burden, not adding more panels. Explanation visibility is not sufficient evidence of calibrated reliance. [E01–E09]

## 2. ADR-01: architecture selection

| Alternative | Strongest case | Main risk | Decision |
|---|---|---|---|
| Extend layout into a research super-object | Lowest initial storage change; existing save UI | Couples geometry migration to belief/evidence/ACL history; hides inquiry identity in chart JSON | Reject for durable research ownership |
| Extend Thesis into the root of every inquiry | Existing immutable versions and recovery | Forces unresolved questions and multi-subject investigations into a belief lifecycle; current subject union is narrow | Keep Thesis canonical for beliefs, not the universal root |
| Thin Investigation with typed references | Explicit intent/history; reuses owners; bounded migration | Reference retention, permission and consistency work must be real | **Selected** |
| Typed reference graph over existing owners | Flexible relations without copying payloads | Relation semantics and UX can become unnecessarily general | Use as a bounded representation inside Investigation, not a separate graph service |
| Universal graph database/research store | General querying and arbitrary relationships | Duplicates evidence, identities and lifecycle; high migration and operational cost | Not justified for this program |

These are qualitative judgments, not measured scores. Selection is conditional on G0 confirming that no current canonical owner already supplies the missing inquiry semantics. If one does, extend it and document that resolution; do not mint a duplicate table because this plan supplied an illustrative name. This is a bounded owner check, not a license to restart architecture indefinitely. [S01–S02; S08; S12; S19]

### Hard invariants

One layout owner; one published Thesis owner; one deterministic Brain context compiler; existing fact/evidence/calculation/alert/portfolio owners; no automatic operational writes on reopen; no current data presented as historical; no AI-generated inference promoted into Native Fact. No new generic queue, identity service, ACL authority, fact cache or vector-memory source of research truth.

## 3. Owner and noun map

| Concept/surface | Role in the product | Ownership and integration |
|---|---|---|
| Investigation | Durable inquiry identity, intent, reference membership, authored history, lineage | Terminal user-state responsibility; new semantic extension only after ADR-01 |
| Named Workspaces / chart_layouts | Visual composition | Existing layout service; add owner-native retention when required |
| workspace_layout.v1 | Frozen composition contract | Keep readable/exportable and lossless; never silently broaden enum meanings |
| mm.ws / unnamed continuity | Local unsaved working session | Existing local owner; no automatic durable promotion |
| AnalysisWorkspace | Entry point and research view | Existing URL/cursor composer; attach/continue inquiry without wrong-symbol reset |
| ThesisWorkspace | Editor for formal beliefs | Existing Thesis owner and immutable versions |
| Saved Thesis research views | Collection filters | Existing personal saved-view owner; never accept Investigation payload through its whitelist |
| R10 Saved Research | Question/evidence-oriented projection | Bind to Investigation, not another saved-research store |
| Company Intelligence | Owner-native evidence and analytical view | Reference its current objects/contracts; do not copy company facts |
| Research Vault | Document discovery and entitled evidence | Existing catalog/search/view API and document identity |
| Market Ontology / Theme intelligence / macro suite | Context and domain lenses | Existing Macro producers; Terminal composes |
| Prophet candidate | Referenced candidate and entry context | Preserve candidate identity/status and promotion governance |
| Options investigations | Source snapshot and domain view | Existing observed root/expiry/source context; no nearest-expiry substitution |
| Screen/search | Query, result generation and entry point | Existing query owner; preserve AST/version/cohort/result clocks |
| Watchlist / portfolio | Referenced operational state | Existing owners; membership is never copied into Investigation |
| Alert / watch condition | Explicit separate operational lifecycle | Existing rule owner and exact rule revision; attach reference only |
| Brain conversation | Interaction history, not hidden durable research state | Existing Brain gateway/run owner |
| AI artifact | Dated derived output with exact used-input manifest | Extend existing Brain artifact/run responsibility; do not assume run-buffer retention is archival retention |
| Scenario | Explicit assumptions plus a domain calculation | Existing domain calculator; persist user assumption specification with an admitted owner and reference owner-native results |
| Template | Reusable starting composition | No user research identity, alert, belief or history until explicit creation |
| Replay | A requested temporal policy | Negotiated across owner capabilities; not a new market-data store |

Sources and coverage limits: S07–S21. Unknown adapter specifics are qualification tasks, not permission to invent current APIs.

## 4. Durable model and reference contract

### 4.1 Identity and revisions

Proposed API schema identifier: `mastermind.investigation/v1`. It is a new proposal, not an existing shipped contract.

A small mutable head contains identity, current revision, lifecycle index and ownership references. An immutable revision contains question/title, typed subjects, canonical object references, authored notes/decisions, reference relations, scenario specifications or references, temporal intent, explicit baseline receipt references and lineage. Lifecycle transitions are revisioned; the head is an index, not a competing history.

Initial proposed bounds to freeze in G0: title 160 Unicode scalar values; primary question 4,000; at most 16 subjects, 128 object references and 256 relation entries; total canonical revision JSON at most 128 KiB. User-authored notes and decision text have explicit per-field and total limits within that envelope. Evidence/source documents, market-value arrays, layout configuration and rendered AI prose are excluded. These are engineering starting limits, not measured capacity claims; benchmark them before release. Large source histories remain in their owners and are paginated.

Required server invariants: strict discriminated schemas, known fields only on writes, canonical normalization shared by validators, stable opaque identifiers, no silently stripped research fields, no unsupported subject coerced to a nearby security, no client-supplied owner principal or privileged truth flags. Unknown future versions open read-only with an explicit reason rather than being rewritten by an older client.

### 4.2 Reference identity and retention

A reference records an allowlisted owner/namespace, object kind, stable identity, desired policy (`follow_head` or `pin_revision`), an exact owner revision when pinned, and the relevant owner capability. The identity resolver—not a display ticker—settles listing/issuer distinctions and aliases. A display label is not evidence and may itself be restricted.

A resolution receipt records what was actually returned: owner object/version, content identity, available clocks, authorization/availability result, temporal capability and capture generation. It distinguishes `RESOLVED`, `NOT_FOUND`, `NOT_ENTITLED`, `UNAVAILABLE`, `UNSUPPORTED_VERSION` and `HISTORICAL_UNAVAILABLE` without inventing values. Error exposure follows the owner's anti-enumeration policy.

A pin is accepted only when the owner can resolve that exact retained version. A digest alone cannot satisfy retention. A live binding in an old Investigation revision remains a live binding and is labeled as such; it is not falsely advertised as an as-seen baseline.

### 4.3 Layout retention and composition evolution

The inspected layout service has CAS but no admitted arbitrary read-by-old-revision contract. G1 must qualify or add retention **inside the layout owner**. An owner-native retained-layout record is permissible; copying layout JSON into Investigation is not. Snapshot creation uses the expected current layout identity/revision so a concurrent update cannot be captured under the wrong label. Attaching/opening an inquiry leaves the existing current layout row, config and revision unchanged. Compare canonical stored JSON/hash, not arbitrary JSONB whitespace; existing export/golden-vector byte contracts remain unchanged. [S07–S08]

General multi-domain widgets cannot be smuggled into v1's chart/brain-only vocabulary. G3 includes a separately versioned layout composition contract when new widget kinds or saved context declarations require it; the expected successor is `workspace_layout.v2`, finalized under the existing owner. It uses the same persistence service, explicit migration preview and retained original v1. Old clients refuse unsupported writes. The initial G1 vertical needs no v2. Native owner views may first appear as existing adjacent surfaces, but a new persistent placement model must not be hidden in Investigation as a second layout store.

### 4.4 Notes, beliefs, contradictions and decisions

Investigation may own bounded user-authored question notes, research steps and decision records. A published hypothesis with its own belief lifecycle remains a Thesis. For subjects beyond issuer/theme, extend the canonical Thesis subject contract under its current owner; do not create a shadow generic Thesis table. One inquiry can link multiple competing Thesis versions. [S12]

Relations such as supports, weakens, contradicts, relevant and unresolved are attributed research interpretations with author, target belief version and source references. They are not new canonical facts. Missing evidence is a research requirement, not a fake source item. A relation may itself be contested. No universal numeric confidence is synthesized from coverage, item counts or an LLM.

A decision record states who chose what, when, why, and which inquiry/belief/evidence/scenario versions were considered. It is not a trade instruction and does not invoke operational owners.

### 4.5 Scenarios without a new calculation engine

A scenario specification names an existing calculator/model version, baseline owner references, explicit user assumptions with units/horizon and an output reference. User assumptions are not copied current facts. Results identify the exact inputs/model and remain deterministic outputs or clearly labeled model interpretations; they are never new observations.

G0 must determine whether a suitable user-state scenario record already exists. Default when none exists: a bounded, versioned scenario specification is authored in the Investigation revision, while calculation and result retention are extensions of the named domain owner. Reusable/global scenario lifecycle is not minted by default. Existing valuation/options calculators are adapters, not evidence of a universal scenario service. Unsupported causal or historical computations must refuse; AI prose cannot fill missing deterministic outputs. [S18]

## 5. Mutations, consistency and migration

Proposed mutation interface: `applyInvestigationRevision(principal, action, investigationId, expectedRevision, clientRequestId, content)`. Create uses expected revision 0; other actions name the known current revision. This interface and the following result states are specification proposals: `created`, `advanced`, `replayed`, `revision_conflict`, `idempotency_conflict`, `invalid_payload`, `invalid_transition`, `not_found` and `unavailable`.

The existing database/RPC mechanism must atomically validate authority, bind request identity and canonical payload hash, insert the immutable revision, advance the head and record the mutation result. Same principal/operation/key/payload returns the original result after current authorization checks; same key/different payload conflicts. Replays are resolved before applying a new stale-head check. No separate universal retry service is needed. [S12–S13]

On a lost response, preserve the draft and original request ID; read the original operation/result and current head. Do not issue another logical write under a new key. A stale edit shows a human-readable field diff and offers deliberate reconciliation or fork; it never discards the draft. Unavailable inventory is not an empty library. Autosave of local drafts is labeled local and is cleared or partitioned correctly on account changes.

Across owners there is no claimed distributed transaction. An as-seen capture produces a vector of owner versions with completeness and failures. Only an explicitly accepted complete or partial capture advances the baseline. A changed layout or evidence owner during capture produces a disclosed version boundary, not fabricated global atomicity.

Existing layouts, saved Thesis filters and mm.ws remain untouched. Explicit “Continue as Investigation” attaches their owner references. Existing Thesis versions remain canonical. No automatic backfill creates inquiry records. Versioned expand/contract migrations preserve older clients; reserve legal migration prefixes from the current namespace mechanism, never from a number printed in an old plan. Backup/restore and forward repair precede any destructive cleanup.

## 6. Semantic context and Brain

### 6.1 One context session, not a new truth service

Use an ephemeral session reducer integrated with the existing Chart Bus and owner surface adapters. Static declarations describe supported ports and groups; runtime state records current values, origin action, session epoch and monotonic group revision. Apply logically related dimensions as an atomic bundle when validity requires it, such as options underlying plus expiry.

Each dimension has an explicit follow, pin or local behavior. Read-only consumers never emit. Incoming propagation is not a new user action and cannot re-enter the same causal chain. Duplicate events, stale revisions and results from previous session epochs are ignored with inspectable receipts. Late A→B→A network responses must not masquerade as the current A generation. A late subscriber receives a current-state snapshot before deltas. Bound causal histories and event queues.

Ordinary local direct actions are serialized deterministically. Do not introduce disruptive conflict modals for two clicks in one event loop. Cross-tab edits to saved intent use CAS; collaborators' current viewports are independent unless a separately specified follow-presenter mode is explicitly enabled. Unsupported cross-type mappings refuse; no automatic theme→security or nearest-expiry substitution.

Persist intentionally saved follow/pin/local bindings and view state in the composition owner, not the event log. Preserve the effective value on unlink/localize. Context changes refetch only affected consumers. A visible receipt reports who followed, who stayed pinned, what was rejected and why.

### 6.2 Same Brain compiler, explicit evolution

W1-C remains the single precedence authority: explicit request, then explicit pin, then active selection, then ambient context. Existing v1 accepts only security edge symbols. A new multi-domain request/envelope version must be explicitly negotiated and compiled by the existing Macro compiler; old clients and security fixtures remain unchanged. Unsupported clients get a declared limitation, not hidden context loss. [S09–S11]

The Investigation's primary subject is research intent, not an automatic higher-precedence Brain pin. A user must deliberately pin it under the canonical pin owner. The context inspector distinguishes saved inquiry subjects, current widget context and the exact effective scope of this request. It shows exclusions, precedence decisions, temporal scope and capability limitations. Canonical identity resolution remains with the existing identity owner.

### 6.3 AI artifacts and safe continuation

A durable AI artifact references the inquiry revision, exact server context receipt, inputs actually used, owner vintages, assumptions/model versions, exclusions, produced-at time and observable provider/run metadata. Offered context and used context are different lists; truncation and entitlement filtering are disclosed. Do not claim hidden provider internals or reproduce an answer solely from a model name.

Old artifacts open without rerunning. “Analyze current evidence” is an explicit action producing a new artifact. A comparison distinguishes changed inputs, changed assumptions/model and unexplained output variation; prose difference alone is not evidence that market conditions changed. Save human beliefs separately from generated output. An AI suggestion does not publish Thesis, modify a scenario, create an alert or alter a portfolio.

During deep-provider failure, question/history/qualified deterministic evidence remain usable. Source documents and retrieved text are data, never permission to call tools, reveal private prompts or mutate objects. Provider data handling and source rights are checked before context submission. Derived-artifact permissions are re-evaluated on read and export.

## 7. Temporal and evidence architecture

### Temporal modes

- **Live:** current authorized owner versions; previously captured artifacts remain visibly historical.
- **Saved baseline:** the inquiry revision plus the exact capture vector, including any disclosed gaps. It is not automatically a complete market reconstruction.
- **Replay:** a requested cutoff and knowledge policy, negotiated across owners. Distinguish public-release availability, platform-known availability and user-seen history where supported.

Relevant clocks include economic validity/event time, observation period, source release, owner correction/version, platform first observation, user capture, inquiry revision and artifact production. Missing clocks remain missing. `saved_at` is not `as_of`.

Every adapter declares current-only, retained-snapshot or point-in-time capability with a precise definition. Point-in-time reads exclude releases/corrections unavailable under the selected cutoff. Current-only widgets visibly refuse historical reconstruction; operational controls cannot silently act on live data while appearing historical. An explicitly opened live comparison is separately labeled and does not enter the replay receipt. [E04; U01]

### Evidence refresh and review

A refresh reads current owner state without changing the saved question, prior capture or authored belief. Cache only through allowed owner mechanisms. A refresh generation is scoped to the query, reference set and temporal policy.

Classify independently: membership, payload/version change, qualification, availability/rights and interpretation. `ADDED` and `REVISED` require identity/version evidence. `REMOVED` requires a successful complete comparable set or owner tombstone. An incomplete search page, changed top-K boundary or outage is not proof of removal. Stale, excluded, denied and unavailable remain separate. Never zero-fill missing observations.

Keep selected-data coverage separate from analytical readiness. The live R10 design correctly shows that qualified Japanese rate data alone cannot answer whether a cross-country gap widened. A comparison needs both subjects, compatible measures/units and aligned start/end observations. Signed gap and absolute widening are different questions. Preserve this guard across all adapters. [P01]

Baseline advancement is an explicit review action with a new revision/capture reference. A background refresh cannot erase the comparison target. Long histories are paginated; source corrections and entitlement changes remain visible without copying source payloads into the manifest.

## 8. Collaboration, security and rights

Different operations require different labels: share current live inquiry, share fixed inquiry revision, fork inquiry, duplicate layout, and export an authorized artifact. A fixed inquiry revision freezes its manifest, not perpetual entitlement to its dependencies. A fork records exact source revision and permissible lineage, then separates mutable composition before edits. It never silently modifies the source inquiry's layout or grants access to underlying sources.

Reuse existing team identity/membership. Investigation policies protect head, revisions, notes, captures and mutation receipts consistently. Current membership and owner rights are checked at resolution. An idempotent receipt is not a way to retrieve data after permission revocation. Cross-account denial includes direct guessed IDs, exports, revision history and derived artifacts. Existing chart_layouts team policies are a precedent, not a complete permission contract for every new object. [S14–S15]

Restrict AI summaries, previews, document titles, aggregate counts and cached content where their source policy requires it. Sharing a summary is not automatically permitted because raw text is omitted. Rights changes may leave a structural tombstone only when that metadata is itself allowed. Purge or isolate client/server caches on logout, tenant changes and revocation; do not put restricted evidence in public manifests, URLs, analytics or browser persistent storage.

First release is private-only. Design sharing semantics and threat tests immediately, but enable team access only after real approved principals and a real team are available and exercised. This plan does not authorize creating paid accounts, teams, invitations or credentials to manufacture test evidence.

## 9. UX system, Paper and seven journeys

### Shell and component grammar

The default opening view answers the question before showing a flexible canvas: inquiry title/revision; temporal mode; current evidence/readiness; saved-versus-current change queue; belief/falsifier; next evidence. Desktop may use a library/history rail, central owner-native analysis and one switchable evidence/context/Brain inspector. Tablet uses drawers. Mobile presents one expensive module at a time with accessible sheets, persistent question/time state and preserved return focus. Do not make hidden hover controls the only way to inspect provenance.

Keep canonical host navigation, token system and language behavior. Terminal follows its admitted dark-only doctrine; Macro/R10 follows its host's light/dark art directions. A token palette in Paper does not authorize a new global stylesheet. Validate EN/ZH, long translated strings, keyboard flow, screen-reader labels, touch and reduced motion. [S21; P01]

Reuse R10 boards before adding new ones. Add or adapt states for historical belief/artifact, exact owner reference and retention inspection, conflicting hypotheses, unavailable replay, derived-content redaction, field-level stale-write recovery and fork detachment. Existing comparison and responsive specimens must be assessed, not duplicated from scratch. Designers supply implementation annotations naming owner, action, persistence, failure and proof boundary on the artboard. Paper remains design evidence, not a release receipt.

### Journey scripts

**J01 — Security versus theme:** From Company Intelligence or a named layout, create “Why is NVDA weakening despite AI breadth?” Capture resolved listing/issuer plus theme identity and an existing layout. Link owner evidence and an existing Thesis version; distinguish breadth from institutional flow. Brain receives the effective scope through the same compiler. Compare an explicitly supported valuation/market assumption scenario, never invent causal numbers. Save an as-seen capture. On return, show changed inputs before a new synthesis. Fork at the saved revision with detached mutable layout; archive with an authored conclusion or next evidence, not a trade.

**J02 — Optical networking versus memory:** Start from Theme/industry intelligence with both canonical subthemes and comparable membership universes. Add comparison charts and an owner-native saved screen. Store query/version/cohort separately from historical result references. Present counterevidence and membership drift. A scenario may alter a declared assumption only through an admitted domain calculator. On reopen, current results are not labeled the old screen cohort. Collaborators can inspect the exact saved comparison or fork it. Close with a documented interpretation; do not equate price return with capital flow.

**J03 — Real-rate/liquidity regime:** Start from Macro/Market Ontology with region, relevant regime and rate/liquidity measures. Capture release and known-at clocks. Link a canonical Thesis once its subject contract supports the regime. Compare explicit model assumptions with sourced observations; unsupported causal forecasts remain unavailable. Brain discloses excluded historical inputs. Reopen shows revisions and newly released evidence separately from genuine economic changes. Share only the authorized fixed capture; archive or retain open with discriminating next releases.

**J04 — Earnings dislocation or thesis break:** Start from a company/event view and the Thesis version that preceded the release. Attach exact event/source references and competing belief versions. Review falsifiers and contradictory cash/earnings/conditions evidence before asking for synthesis. Run only owner-supported valuation assumptions. Save both pre-event and reviewed capture references. Reopening preserves what was believed then, even if the current Thesis changed. A collaborator forks the inquiry without publishing a belief revision. Close by explicit human Thesis action and an inquiry decision record; no automatic trade or alert.

**J05 — Prophet falsifier:** Enter from the exact candidate identity and release/candidate clocks, not just ticker. Preserve the owner's status and governance. Attach the proposed falsifier, source-backed evidence and relevant Thesis version. Brain may suggest further research but cannot change ranking, timing, entry, size or promotion. Compare only supported scenarios. Reopen displays candidate lifecycle changes separately from the saved belief. Fixed sharing/forking preserves lineage and rights. Archive an invalidated inquiry without changing candidate authority; an explicit alert remains a separate owner action.

**J06 — Options warning:** Enter the existing Options investigation retaining underlying, exact expiry/contract when supplied and source snapshot clocks. Attach the measured observation, underlying chart and price-action hypothesis. Do not infer package intent or a trade recommendation. Scenario output must identify the actual options model, inputs and temporal limitations. Current refresh cannot overwrite the opened historical observation; missing smile/expiry remains missing. Brain shows its scope and exclusions. Fork preserves lawful observation references and detached layout. Close as a research interpretation, with optional explicit existing watchlist action and readback.

**J07 — Japan policy divergence:** Start from R10's saved question. Require a named comparator economy, compatible rate definitions/units, comparison direction and two aligned dates before interpreting widening. Preserve source clocks, exclusions and the human policy Thesis. A rate-assumption comparison is labeled a scenario, not policy fact. On reopen distinguish new releases, corrections, lost qualification and unresolved inputs. Brain cannot replace a missing comparator with an inference. Fixed sharing preserves the comparison specification; fork changes assumptions explicitly. Close or leave open with the next discriminating evidence. Retain the existing Paper analytical-readiness warning. [P01]

Every journey must exercise create, capture, leave, fresh-session resume, evidence change, historical/current distinction, explicit AI, scenario or honest unsupported state, contradiction, authorized sharing/forking and archive/reopen. Honest unsupported states are necessary, but cannot silently discharge an explicitly required build capability; unresolved capabilities stay on the program denominator with an owner.

## 10. Performance and operational design

Render authorized inquiry metadata and layout skeleton without waiting for facts or AI. Hydrate visible deterministic data progressively, refresh evidence behind visible generation state, then load offscreen modules on demand. Cancel superseded reads and reject late generations. Owner-query deduplication keys include principal/entitlement scope, query, temporal policy, owner version and relevant context; a shared ticker-only cache is unsafe.

Initial proposed budgets: warm authorized manifest plus shell p95 <=500 ms; local context reducer/application p95 <=50 ms excluding network; 128 KiB maximum revision payload; no full-history fetch on open; one active expensive mobile module. The earlier 1.5 s first-fact aspiration is conditional on a fresh owner-waterfall benchmark and is not claimed achieved. Deep AI has separate timing and token budgets and is never a shell gate. Report cold/warm, sample count, device/network, p50/p95, bytes, request count and owner bottlenecks rather than a single screenshot time. [S05; U02]

Feature flags separate private inquiry, retention, multi-domain context, replay, artifacts and sharing. Readers deploy before writers; migrations are additive and prefix-reserved. Recovery disables the affected exposure without deleting user revisions or reverting to a writer that cannot preserve them. Backups and restore tests include head/revision consistency and source-retention dependencies. Telemetry records opaque IDs, outcome classes and timings, not private source text. Use existing observability and release systems.

## 11. Re-cut downstream scope

The table is a scope disposition, not a claim that every old wave was fully re-audited. G0/G8 bind each row to its exact current owner/carrier and current capability state. No row can disappear merely because it belongs to another lane.

| ID | Old concept | Disposition and accountable outcome |
|---|---|---|
| D01 | W2-B semantic linking | Required; redesign and implement through existing bus/Brain owners, explicit contract evolution |
| D02 | W2-C and versioned saved/shareable work | Split layout retention from inquiry live/fixed/fork semantics; preserve existing sharing |
| D03 | Theme Tracker++ | Consumer adapter using existing theme producers; current exact widget parity must be checked |
| D04 | Screener AST/NL query | Query owner remains canonical; preserve query/operator/unit/cohort/result version; no prose execution |
| D05 | Rating vintages | Domain retention adapter; no new composite score or Prophet authority |
| D06 | Mini visualizations | Reusable owner-native widgets under versioned composition, not new calculations |
| D07 | Rule grammar/alerts | Existing rule lifecycle; exact revision and explicit create/confirm/readback; no reopen side effects |
| D08 | Analyst-action data | Licensed financial analyst events remain a separate data requirement; research activity provenance does not replace it |
| D09 | Combo lists/watchlists | Existing user-state membership; reference or explicit owner action, never copied membership |
| D10 | Workspace templates | Starter lenses with no automatic research identity, alert or belief |
| D11 | Prompt library | Reusable Brain interaction templates; not authoritative research memory |
| D12 | Cited investigations | Core exact-revision/capture/artifact manifests and permission-aware distribution |
| D13 | Replay | Core temporal capability and known-at/correction work; no live contamination |
| D14 | Mobile capture | Common owner and recoverable draft/save/resume; no second mobile backend |
| D15 | Neural Web observation packets | Existing evidence/context producers; no new authority transfer |
| D16 | Prophet shadow research | Consumer integration only; scientific validation/promotion remain separately governed |

## 12. Execution decisions and remaining qualifications

The architecture above is the recommended implementation default. G0 is bounded to current owner/collision checks, exact contract freeze, retention/rights feasibility and proof-resource qualification. It is not a new broad research program. An existing owner with equivalent semantics wins over a proposed new record. Otherwise extend the stated responsibility with the bounded model here and record the ADR.

Open qualifications are exact current adapter APIs and retention, current migration namespace, cross-domain Thesis/Brain version design, current live writers, and approved production QA identities. Each has a gate/owner in the execution document. Resolve what source inspection can settle without asking the user. Escalate only genuine authority, rights, destructive-change or unavailable-principal boundaries, and continue independent work.

Completion means all G0–G9 outcomes, J01–J07 journeys, D01–D16 dispositions and applicable T01–T32 proofs have accepted evidence or an explicit owner-approved change of scope. The first vertical, an open PR, green fixtures, a static design, or a documentation upload is not end-to-end product completion.
