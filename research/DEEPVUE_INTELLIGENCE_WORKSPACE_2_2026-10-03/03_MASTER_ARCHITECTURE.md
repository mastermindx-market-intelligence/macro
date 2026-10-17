# Mastermind Intelligence Workspace 2.0 — Master Architecture

Status: **implementation-ready recommended architecture, not an implemented capability or a new grant of authority**. Date: 2026-10-03. Applies to existing `WS:DEEPVUE-INTELLIGENCE-WORKSPACE`. Read [census/source limits](01_CENSUS_AND_SOURCES.md) and [alternative analysis](02_RESEARCH_AND_THESIS.md). All new schema/API/table names below are **proposed additions**, not claims that these objects already exist.

## 1. Architecture decision record

Choose **Investigation-over-layout, with a typed reference/argument projection**. Preserve layout-only workflows. The new durable identity owns research intent and references; existing owners continue to own facts, documents, beliefs, alerts, queries, portfolio membership and calculations.

This decision must be accepted in the existing architecture/organizational home before schema work. Two explicit reconciliations are required: the portable-context decision permits saved state only through existing Terminal user services; the September macro architecture regards `workspace_layout.v1`/`chart_layouts` as the canonical layout owner and places saved scenario assumptions in layout state. This proposal keeps the layout owner, but lifts durable research intent above it and moves research-only assumptions by a lossless, explicit migration. It does not quietly override either source. [I24,I25]

**Falsifier:** if pickup finds an existing owner with durable general questions, revisioned references, tenancy and outcome-aware writes, adapt that owner instead of creating the proposed aggregate. Similar names are not sufficient. The first commission must document its storage/API identity and demonstrate semantic compatibility.

### Allowed extension versus forbidden parallel plane

Allowed: a small new aggregate and its revisions **inside the existing Terminal user-services persistence, migrations, authentication, tenancy, resource grants and write-outcome conventions**, because no inspected entity owns a question independent of layout and Thesis. Extend the existing layout owner with immutable revisions. The same service boundary serves both existing and new consumers.

Forbidden: a new research database/service, universal Evidence graph, generic vector-memory authority, second fact cache, duplicate Thesis engine, alert scheduler, identity resolver, collaboration service, browser-only persistence source, or company execution lifecycle. Adding a table is not automatically a new plane; creating competing ownership is. Conversely, putting all data in one existing JSON column does not make duplication safe.

## 2. Noun and owner map

| Concept | Canonical owner / representation | Workspace relationship | Explicit boundary |
|---|---|---|---|
| Investigation identity, question, subject set, continuation, research lifecycle | Proposed bounded aggregate within Terminal user services | Persistent research unit | Not an execution Job or Brain thread |
| Named Workspace / `workspace_layout.v1` | Existing `chart_layouts` + layout contract | A saved visual arrangement; one Investigation may reference several | Does not own research truth |
| Unnamed `mm.ws` | Existing device-local continuity | Disposable working arrangement; explicit save/attach | Not cross-device durable research |
| Analysis Workspace | Existing route composition | Entry point and reusable view | No automatic Investigation creation |
| Thesis Workspace | Existing Thesis/RMS UI | Lens over canonical hypotheses/beliefs | Not replaced or copied |
| Hypothesis/thesis, human conclusion, historical belief | Existing `theses`/`thesis_versions`; extend typed subjects/content where necessary | Versioned references, possibly several competing hypotheses | Preserve original authors, effective and recorded clocks |
| Human notes/decisions beyond current Thesis fields | Explicit typed extension of existing research-authoring/Thesis owner | Referenced versioned authored entries | Do not pretend a general journal API already exists; no parallel note lifecycle |
| Timed forecast Claim | Existing Claims owner and resolver | Referenced scorable prediction | Not a generic evidence assertion; no hidden probability fabrication |
| Argument relation | Investigation-owned annotation between exact owner references | Supports / weakens / contradicts / unresolved / discriminates | User interpretation, not canonical Evidence or Native Fact |
| Native facts, identities, units, relationships | Existing Data OS/security/theme and W1-A owners | Qualified read references/receipts | No second registry, resolver or canonical cache |
| Evidence content and lineage | Existing domain producers, Company Intelligence, Vault and other admitted evidence owners | Federated evidence-reference ledger | No copied provider payloads or universal graph assumption |
| Evidence qualification/diff | Deterministic projection over owner receipts | Read result, optionally referenced as reviewed baseline receipt | Cannot freshen sources or confer rights |
| Source vintages/corrections | Source/producer owner | Pinned version reference and clocks | Missing historical retention is disclosed, not synthesized |
| Scenario assumptions | Versioned, typed user-authored recipe within the existing research-authoring/user-services boundary | Bounded research configuration; refs to base evidence and calculator | No scenario database/lifecycle; no rewrite of live facts |
| Scenario outputs | Existing domain calculator/producer | Derived result receipt, or explicit unavailable | Never Native Fact or an execution instruction |
| Saved search/screen | Existing or explicitly extended query owner | Saved query reference plus evaluated membership receipt | Do not copy watchlist/portfolio membership |
| Watchlists/portfolios | Existing owners | Reference, read-only scope input | Membership and decisions stay owner-native |
| Alerts/watch conditions | Existing alert owner/outbox | Explicit user-created referenced object | Reopen/context/AI cannot activate it |
| Brain conversation/run | Existing Brain/run owner | Related analysis output and visible context receipt | Conversation history is not durable research authority |
| Replay clock | Existing replay owner, adapted into investigation temporal context | One temporal coordinator, per-widget capability | No rival scheduler or promise all widgets replay |
| Company Intelligence | Existing generation-pinned context BFF | View, widget and investigation entry | Field lineage can be valid while paragraph citation is pending |
| Research Vault | Existing content/ingestion/catalog/FTS owner | Evidence source and capture destination | Rights and document bodies remain there |
| Market Ontology / Theme intelligence | Existing entity/relationship/metric owners | Subject resolver, widgets, templates and entry points | No duplicate ontology or membership database |
| Prophet / Options Alpha | Existing candidate/fire/shadow/readiness owners | Reference an exact candidate/evaluation vintage | No signal promotion, selection rewrite or new trade authority |
| R10 Saved Research design | Generalizable interaction pattern | Question, qualification, diff and continuation template | Country/measure rules remain domain-specific |
| Collaboration/visibility | Existing tenancy/resource-grant owner, extended to new resource kind | Private/team, head/revision grants, fork | No new role system or transitive entitlement |

One Investigation can reference one company, multiple securities, a theme, an event and a regime. That does not make those identities interchangeable. For example, issuer identity and a listed security are distinct; option contract, underlying and expiry are distinct; a theme's membership is not a portfolio's membership.

## 3. Target contracts and durable state

### 3.1 Investigation head and revision

Proposed `investigation.v1` head:

```text
id: UUID
scope: existing user/team scope reference
owner_ref: opaque existing principal reference
head_revision_id: UUID
lifecycle: open | concluded | archived
created_at, updated_at: server clocks
```

Proposed `investigation_revision.v1`:

```text
revision_id, investigation_id, parent_revision_id
sequence: owner-assigned monotonic integer
author_ref, recorded_at, operation_id
intent: { title, question, subjects[], horizon?, research_as_of? }
layout_refs[]: { layout_id, layout_revision_id, digest, role }
thesis_refs[]: { thesis_id, version_id, role }
evidence_refs[]: EvidenceRef
argument_relations[]: ArgumentRelation
scenario_recipes[]: ScenarioRecipe
query_refs[], alert_refs[], related_investigation_refs[]
review_baseline_ref?: owner-supported immutable comparison basis
continuation: { next_question?, next_observation?, last_reviewed_at? }
change_reason?: user-authored explanation
```

These are separate validated subcontracts, not an untyped metadata bag. Fact values, source documents, market series, model transcripts and portfolio membership are forbidden. Human-authored hypothesis content is not embedded; it is referenced through the Thesis authoring owner. A question can exist without a Thesis.

Initial proposed release limits: title 160 characters, question 2,000, 16 subjects, 4 layout refs, 16 Thesis refs, 128 active evidence refs, 128 argument relations, 8 scenario recipes, 32 parameters per recipe, and a 64 KiB serialized revision manifest. These are engineering ceilings to benchmark, not scientific truths. Reject oversize writes with an exact reason; never silently truncate. History may contain thousands of older references through paged immutable revisions. Expanding active-set limits requires a measured owner-local storage/read design, not unbounded JSON growth.

A long investigation can archive older working evidence into retained revisions and keep a focused active set. The UI must distinguish “not in current active set” from “deleted.” References remain navigable through history subject to rights/retention. A mandatory fit-to-cap operation must be explicit and lossless; the system cannot silently discard older evidence to save a new note.

### 3.2 Subjects and identity admission

Proposed typed subject vocabulary: `security`, `issuer`, `industry`, `subtheme`, `theme`, `regime`, `economy`, `event`, `portfolio`, `option_underlying`, `option_contract`, `policy_question`.

Each carries an existing owner namespace, opaque/canonical ID and optional version/cutoff. This vocabulary is a target, not an assertion that all corresponding current owners are integrated. Every kind needs an adapter declaring resolution, rights, time support and missingness. An unsupported kind remains unsupported; the UI can save a free-form question but cannot manufacture a canonical ID. `policy_question` is research intent, not a market entity with invented facts.

Current W1-C and layout v1 support narrower types. Introduce version negotiation and paired Python/TypeScript golden vectors. Never coerce a theme to a security string or append new types into a closed v1 validator. [I05,I06,I08]

### 3.3 Evidence references and qualification

Proposed `evidence_ref.v1`:

```text
owner, object_type, object_id
version_ref?: immutable owner version
selection?: safe field/span/record selector
mode: pinned | follow_head
fingerprint?: owner-supported digest
source_clocks?: { observed_at?, released_at?, first_known_at?, revised_at? }
recorded_reference_at
qualification_ref?: owner receipt identity
```

The client cannot assert provenance, first-known time, license or qualification. The server resolves the owner reference and supplies subscriber-safe metadata. Digests are identifiers/integrity checks, not access tokens or proof that the content is true. A timestamp alone is not a retrievable vintage.

Qualification has three independent levels:

1. **Readable:** the current principal may retrieve this reference and the payload passes its schema/identity checks.
2. **Comparable:** units, definitions, entities, periods, vintages and required coverage support the requested comparison.
3. **Answerable:** the necessary evidence for this question/claim is present and qualified. This can remain false when two out of three cards are readable.

Each projection reports `qualified`, `stale`, `missing`, `rights_blocked`, `unsupported`, `incompatible`, `historical_unavailable` or an explicit source error as appropriate. Do not collapse these into null/zero. Rights-blocked evidence cannot be counted as evidence against a hypothesis.

### 3.4 Contradictions and competing hypotheses

`ArgumentRelation` links exact source/hypothesis references and contains `relation`, `author_kind`, `author_ref`, `rationale`, `recorded_at`, optional discrimination criterion and review state. Relation vocabulary: `supports`, `weakens`, `contradicts`, `unresolved_interpretation`, `discriminates_between`. Missing/stale/rights-blocked are evidence states, not automatic argument edges.

An AI-proposed relation remains a proposal; a user can accept it as an attributed interpretation. Direct factual contradiction requires comparable propositions about the same entity, metric, period and definition. “Revenue grew while the share price fell” is not a contradiction. Two analysts' explanations may conflict without either source fact being false.

Maintain multiple Thesis references rather than forcibly one current truth. No automatic weighted voting or probability aggregation. A user-stated confidence may be retained with scale/meaning and author; calibrated model probabilities require their own validated method, horizon and scoring record. Do not reuse timed Claims as the storage schema for all argument edges. [I15,I17]

## 4. Persistence and writes

### 4.1 Existing-owner extension

Proposed tables, subject to current namespace reservation and architecture acceptance:

* `investigations`: identity, scope, lifecycle, current revision pointer.
* `investigation_revisions`: immutable validated research-intent manifests and parent linkage, in the same user-services database.
* `chart_layout_revisions`: immutable snapshots owned by the existing layout service, keyed by layout UUID and revision UUID.

No new database, independently deployed write service or generic event store. Transactional operation outcomes belong to the existing user-services request-ID/outcome convention. Extend that convention where it is not already reusable; do not claim that the saved-view optional UUID provides it. [I09,I15,I16]

`chart_layouts` remains the current layout head. Existing writes append a version through the layout owner and update the head in the same transaction. Migrating an existing layout creates a truthful “first retained snapshot at migration,” not fabricated historical versions. Immutable research references never point only to a mutable name or CAS integer.

### 4.2 Command contract

Proposed existing-BFF route family `/api/investigations` and `/api/investigations/[id]`, with revision and operation-outcome subroutes. Treat names as proposed route surfaces; use current framework conventions at implementation.

```text
commitInvestigation(command, actor) -> CommitOutcome
command = { operation_id, expected_head_revision_id?, action, manifest }
action = create | revise | conclude | archive | reopen | fork
outcome = applied | replayed | conflict | rejected | pending_unknown
```

For create, `expected_head_revision_id` is absent and the client-generated object ID/request identity is stable. For mutations it is mandatory. Same operation ID and same canonical payload digest return the same committed result; same ID with different payload is rejected. A conflict returns a safe current-head receipt and never overwrites it. Unknown effect prompts exact operation readback; transport timeout is not “nothing saved.” IDs and request bodies are scoped to the authenticated actor/resource, with CSRF and size protections consistent with current routes.

Creation/ref writes and head movement are transactional. Validation failure writes nothing. Creation caps are enforced transactionally, not a pre-read count. Multi-resource lock order is stable. If saving a working layout together with an Investigation, use the existing layout-owner transaction capability or a composite transaction within the same approved service boundary; do not advertise atomicity across external owners. An independently saved Thesis is an explicit successful authoring action before its version is attached; a later attach failure does not erase or misreport the Thesis write.

### 4.3 Read is not write

Opening, reading, comparing, resizing, scrolling, scrubbing replay, expanding a receipt and asking Brain do not advance the reviewed research baseline. Ephemeral UI context can change without creating a research revision. Explicit Save/Review/Commit changes durable state. Optional autosave is limited to clearly labeled drafts and must not silently become a reviewed belief or activate a monitor.

Three state machines remain distinct: inventory read, evidence refresh, write outcome. A timeout in one does not turn another into empty/success. No logical retries on uncertain mutations; reconcile operation outcome through the same owner/carrier.

## 5. Redesigned W2-B semantic context

### 5.1 One logical context system, existing buses as adapters

Extend the existing Chart Bus boundary with a typed mounted-session coordinator. Existing Options replayBus/ReplayProvider becomes a temporal adapter with one elected publisher, not a second investigation clock. Existing Brain context provider consumes the same accepted context snapshot. No persistent context event database or alternative transport is introduced. [I06,I21]

A context group has an explicit purpose/type, typed value, membership/ports, group revision and visible label. Initial kinds: entity selection, entity set, time/horizon, historical cutoff and scenario selection. Expand subject types only when owner adapters are admitted.

```text
ContextDelta = {
  schema: semantic_context_delta.v1,
  session_epoch, group_id, base_revision,
  mutation_id, origin_id,
  patch, cause: user_action | explicit_restore
}
ContextReceipt = {
  mutation_id, accepted_revision, applied_ports[],
  pinned_ports[], rejected_ports[], collisions[],
  missing_adapters[], temporal_mismatches[]
}
```

Group revisions are monotonic within a session epoch. Remount creates a new epoch; persisted snapshots restore values, not event sequence authority. Reject unsafe numeric overflow. Origin IDs and mutation IDs are bounded opaque values, never permissions.

### 5.2 Propagation algorithm

1. Validate the delta against the group's closed contract and current epoch. Admit only a deliberate emitting action or explicit restore; data arrival/receipt acknowledgments are not emitters.
2. Serialize mutations through the mounted coordinator. Deduplicate `(epoch, mutation_id)` and require the expected group revision. Reject a stale externally submitted base with a collision receipt rather than last-writer-wins.
3. Build a deterministic target set from declared input ports. One input has at most one group per context dimension unless a named join adapter defines behavior. Type equality is not enough to authorize semantic conversion.
4. Compute the accepted context transaction before publishing. Pinned/localized/read-only ports remain unchanged with reasons. Unsupported ports remain visibly unsupported; they do not guess a security from a theme.
5. Publish one new context generation and one receipt. Widgets may hydrate independently, but no old data may appear under the new entity/time label. Hide or clearly label the prior frame while new reads are pending.
6. Cancel superseded reads and reject late results whose entity/time/scenario/entitlement generation no longer matches. A matching data result is not another context mutation.

A user selecting a new security changes linked security ports only. Deriving its industry/theme requires the existing relationship owner and an explicit transform adapter, not coercion. A time change does not replace a scenario. Multiple simultaneous groups are allowed; the UI always shows the group each widget follows. Unlink preserves the widget's current local selection. Re-link previews the target value before applying it.

### 5.3 Edge cases

Ordinary duplicate-symbol chart restrictions and drawing ownership remain as currently enforced; multi-timeframe panes are the existing explicit exception. This program does not broaden drawing writes just to demonstrate linking. A read-only widget may consume without emitting. A pinned widget never changes silently because an Investigation's primary subject changed.

On mobile, group controls are tap/keyboard accessible; there is no hover-only source of truth. Context receipts are concise by default, with reasons available on demand. A full timeline of pointer movement is not persisted. A group update never creates an alert, changes portfolio membership, executes a screen mutation, revises a Thesis or submits a trade.

### 5.4 Reconciliation with W1-C

Retain `explicit request > pinned > active > ambient` and the rule that competing precedence levels do not silently merge. Current v1 remains security-only and backward compatible. The generalized proposal is a negotiated `ai_context_client.v2` / `ai_context_envelope.v2` under the existing Brain request/context channel, with one server compiler and shared golden vectors.

Explicit text in an AI question changes that **request's effective context**, not the whole Investigation or every linked widget. It can propose “switch investigation scope,” which requires a user action. The receipt distinguishes research subject set, active visual selection and effective request scope. The native fact lane retains its own admitted field/entity constraints. Unsupported generalized context cannot silently fall back to a seemingly complete security answer.

## 6. Brain architecture without hidden state

Pipeline:

`authenticated request + exact investigation revision + accepted visual context → deterministic scope compiler → owner rights/qualification reads → bounded evidence manifest → existing Brain lane → answer + context/evidence receipts`.

The pure scope compiler makes precedence/type decisions; I/O qualification is a separate stage. The model cannot choose canonical identities, elevate rights, set source clocks or turn inference into fact. It receives current question, selected hypotheses, relevant evidence, known contradictions, recipe assumptions, source clocks and explicit exclusions. Retrieval expansion beyond curated sources is visible and bounded; it cannot secretly change the user's research scope.

A receipt records investigation/revision, visual context generation, included references/versions, exclusions with reasons, source completeness/answerability, temporal mode, relevant hypothesis versions, scenario version, actual available model/run identity and output status. Never fabricate unavailable model metadata. Public receipts contain safe identifiers rather than internal paths or provider credentials.

Output sections distinguish facts, calculations, interpretations, scenario results, unresolved alternatives and suggested next observations. Every supported factual assertion links to an exact qualified reference; incomplete paragraph/span lineage is marked as such. Claims about why an answer changed must cite changed inputs or explicitly say the difference may be model variability, not invent a causal explanation.

Persist AI runs and historical outputs in the existing Brain/run owner, referenced from research when explicitly retained. To turn AI-assisted text into a human-authored Thesis revision, show the proposed text/basis and use the canonical authoring action, preserving assistance attribution. A source attachment or chat message is never hidden authority to mutate user research.

### Degradation

Show the question and prior reviewed basis immediately. Deterministic facts render as owner reads complete. Deeper synthesis can load, fail or be unavailable without blocking evidence inspection or saving the question. A timeout exposes its scope and does not substitute stale analysis as current. Do not stream empty progress tokens as “first value.” Historical W1-B latency is a constraint to investigate, not evidence of current performance. [I04]

## 7. Temporal continuity and replay

### 7.1 Separate clocks and modes

For relevant evidence retain, where owners actually provide them: economic/observation period, source release time, first-known-to-Mastermind time, source revision time, user reference-recorded time, analytical calculation time and UI render time. Unknown stays unknown. A newly rendered card cannot become fresh merely because the request succeeded.

Modes:

* **LIVE:** follow current owner heads; compare against a saved reviewed baseline without overwriting it.
* **PINNED BASELINE:** display exact retained owner versions supporting a saved research revision.
* **AS-KNOWN RECONSTRUCTION:** only evidence genuinely available by the chosen knowledge cutoff, with compatible observation periods and retained source vintages.
* **CURRENT REANALYSIS OF PAST PERIOD:** use revised/current information about an earlier period; label it separately from what was known then.
* **SCENARIO:** counterfactual assumptions over an identified baseline, not current reality.

An owner version must be retrievable to claim historical reproduction. `observed_at <= cutoff` alone is insufficient if the value was released or ingested later. Distinguish what was publicly available from what Mastermind had ingested; do not promise the former when only the latter is recorded.

### 7.2 Widget temporal capability

Each adapter declares `live_only`, `recorded_snapshot`, `as_known_history`, `revised_period_history` or an explicitly supported subset. A historical workspace never invokes a live-only adapter as a hidden fallback. It renders “not available for this historical mode” and excludes it from historical Brain context.

A user may intentionally open a separately labeled current-comparison panel next to historical evidence. It has a distinct temporal group and is excluded from the historical answer unless the request explicitly asks to compare then and now. This is stricter than merely placing a small stale badge on present-day data. Preserve existing Options at-head versus live distinction; the last frame of an archived session is not the present. [I21]

### 7.3 Evidence diff semantics

Compare stable semantic identities, not display labels or array positions. Result classes: added, removed-from-active-set, source-corrected, value-revised, newly-stale, recovered, unavailable, rights-changed, incomparable and unchanged-qualified. Missing baseline means **comparison unavailable**, never zero changes.

Numeric comparison requires consistent units, metric definitions, entity scope, periods, currency and vintage policy. A changed fingerprint can indicate a source revision without proving an economically meaningful delta. Expose both. Never normalize percent/fraction/basis-point units by guessing.

Example of required arithmetic: if a signed country spread changes from -3.0 to -2.5 percentage points, its signed delta is +0.5 pp / +50 bp, while absolute divergence narrowed by 50 bp. Do not label this “widening” without defining the comparison. This is a design/test example, not a market observation. [I26]

A reviewed baseline advances only on an explicit review/save action. Background evidence reads may update the current projection but cannot erase the evidence basis of last week's belief. Source corrections retain their temporal relationship to the old belief; evaluation asks whether that belief was reasonable on its then-available evidence, not merely whether it agrees with revised data now.

## 8. Scenarios and decisions

A `scenario_recipe.v1` contains an existing calculator/method reference and version, base evidence references, typed assumption parameters with units, target horizon, author and recorded time. It has no independent scheduler or lifecycle. Preserve any existing saved layout assumptions losslessly when lifting them into this typed authoring contract, with explicit migration receipts.

Each parameter is marked `sourced`, `user_assumption` or `model_proposal`; accepted model proposals remain assumptions. Calculator outputs name units, sensitivity scope, method/version, base vintages and missingness. Existing Options market-structure calculations retain their sign convention and truncation disclosures. A recipe whose method/version or historical input is unavailable is inspectable but not reproducibly executable. [I20,I24]

Compare scenarios through delta outputs, not by rewriting the baseline values. No inferred probability is attached to a scenario unless a qualified probability model supplies it. A user may record an investment decision as an authored historical judgment; any actual portfolio, alert or trade change still requires its separate owner-native command and permissions.

## 9. Collaboration, sharing and fork semantics

Distinct actions:

| Action | Meaning |
|---|---|
| Share layout | Existing whole-config visual arrangement sharing; no automatic access to attached research |
| Share Investigation live head | Current authorized research head, changing as permitted edits commit |
| Share fixed revision | Stable research revision/reference vector; source rights still checked at every read |
| Duplicate layout | New owner-native visual arrangement under existing semantics |
| Fork Investigation | New identity with parent revision and attribution; source refs remain refs, mutable authored objects are copied only by explicit owner actions |
| Collaborative edit | Existing team roles/grants plus optimistic revision checks; no implied real-time co-edit engine |

The initial collaboration mode is optimistic concurrency with compare/reload/fork, not character-level CRDT editing. Team owner/admin behavior must match current tenancy law; do not invent roles. Sharing a private Investigation is not allowed to grant access to private Thesis, Vault or licensed evidence transitively. A share preflight enumerates which items are shareable, redacted or blocked without leaking unauthorized metadata to recipients. Titles and annotations can themselves contain sensitive information and need the same review.

A stable citation identifies a revision, not a guarantee that revoked/licensed content remains readable forever. On revocation, preserve an authorized tombstone or reference metadata only where policy allows. Recheck list, detail, Brain assembly, exports, forks and cached responses against current rights. Pinned means version-pinned, not rights-pinned.

For a fork, default to a private new Investigation and layout copy/reference as selected, retain original authorship and fork parent, and do not duplicate alerts or activate monitors. Referenced Thesis revisions remain attributed originals unless explicitly copied through that owner. A shared head moving later does not mutate the fork's initial baseline.

## 10. Invariants for implementation review

1. Every displayed market value has one canonical owner and a declared time/qualification basis.
2. Layout mutation cannot corrupt or silently revise authored research.
3. Research revision cannot change source facts, alert lifecycle, portfolio membership or execution state.
4. A saved question survives without a successful AI answer or an authored Thesis.
5. A historical belief and its exact available evidence basis are distinguishable from current synthesis.
6. Context propagation is explicit, typed, deduplicated and receipt-visible; response arrival cannot emit a loop.
7. A rights change applies to old revisions and new projections; no transitive sharing shortcut exists.
8. A missing baseline, source or adapter is a visible limitation, never empty success or fabricated certainty.
9. Source/knowledge time and render time never substitute for one another.
10. Completion means real authenticated product journeys and cross-owner acceptance, not only schemas, screenshots or green fixtures.

These invariants are mapped to concrete negative tests and production gates in [the build program](05_BUILD_PROGRAM_AND_ACCEPTANCE.md). The [first commission](06_FIRST_IMPLEMENTATION_COMMISSION.md) intentionally delivers a useful private question-resumption loop before the generalized platform is complete.
