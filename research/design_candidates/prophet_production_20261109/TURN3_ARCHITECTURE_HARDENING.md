# Prophet Turn 3 — architecture hardening and implementation contract

**Version:** 3.0 architecture candidate, 9 November 2026, America/Vancouver. **State:** SOURCE_BOUND_ARCHITECTURE_FOR_TURN4; implementation, installed acceptance and scientific promotion are not established by this document. This is the third of the Chairman's four editorial turns. Turn 4 freezes the complete commission for a Fable-led team on the designated T3. No dispatch or release is performed here.

**Parent:** `prophet-production-design-four-turn-20261109-sol-001`, existing `WS:PROPHET-US-V4-RECOVERY` and `WS:PROPHET-US-ENTRY-TIMING`. The contract IDs below are document references, not new runtime entities, owners, workstreams or admission decisions. Preserve R6 B00–B28, Q01–Q24, D01–D12, R01–R36 and activation branches A01–A05.

## 1. Outcome and evidence boundary

The design can be implemented through the existing Prophet owners. The important work is to finish their joins and consumer contracts, selectively integrate the open candidates, and prove the resulting user journeys. The architecture is now grounded in what the actual source accepts and returns, including useful capabilities that already exist and precise differences between those capabilities and the Paper specimens.

This revision makes twelve material decisions:

1. Extend the existing same-read B4 join and give evaluation and presentation one verified request-local owner bundle.
2. Separate live-pass provenance, evidence cutoff, factual assembly and actual evaluation clocks before connecting native geometry.
3. Qualify quote/basis comparability before any price-derived invalidation; preserve authoritative lifecycle and retraction separately.
4. Project policy-specific terms without inventing a separate entry stop, chase boundary or validity interval.
5. Reuse the original Plan source resolver; retain original provenance and current management as different claims.
6. Integrate the Save adapter with its required WatchStore account safeguards; keep observed membership distinct from an uncertain insert's outcome.
7. Extend the existing transient Compare owner into aligned, ordered comparison across supported view and filter changes.
8. Complete the existing B21 email chain; retain assessment-change, B4-change and in-app notifications as explicit, unimplemented extensions.
9. Build Record from native plans, B1 and the effective ledger; a terminal-only projection cannot supply an originating cohort or unresolved count.
10. Close the Earnings per-share provenance gap and prove independent peer production, while retaining Cycle's actual candidate status.
11. Fix F04 and W07 availability semantics at their incumbent owners.
12. Tie completion to the entitled served path, ordinary refresh, truthful failure states and rollback, while preserving independent research-to-watch activation.

### Exact source baseline

| Source | Pinned revision | Meaning in this review |
| --- | --- | --- |
| Mastermind protected procedure | `3652d8907df1738de551dd3032b42aa2a2acb482` | Reused governing pin; current Chairman instructions and Web review waiver apply |
| Macro main | `9a13c64bf69f782332afa29efb09fe48ee30b857` | Fresh backend, producer, presentation and persistence source |
| Terminal master | `1c0bf028cf72539a4d3fcb17fa137ee474d764f9` | Fresh application, BFF, account and migration source |
| Rich product #9495 | `d42d83307948141c05967d7081a6cc7cbeb24a90` | Open Draft/HOLD; substantial candidate source, not merged or installed acceptance |
| D03 #10617 | `927c667714e04ba82db60c15852213ce8660cc9f` | Open Draft; Prophet Phase 2A blob remains `c5f7899e07d7a54b869e60b8090bfafa95b8e74e` |
| F01 #10645 | `dce261d07ebc993e8a9579cca2200e445b6636d4` | Open Draft; candidate.4 provisional, candidate.5 proposed, final joint v1 unreleased |
| Masterplan v2 | `1b44fbe5bf307d624c242a346c81cf8fc877c46c` | Preserved Turn 1 census and Turn 2 review |
| Paper PROPHET | `01M3NT5Y3G5HTJHVR0K5W2MDJM`, page `p-F-0` | Read-only inventory: 23 canvases, 3,308 nodes; 22 reviewed roots and one held partial |

The source dossier appendices contain exact paths, symbols and blobs. Main source, candidate source, schema migration source, installed bytes, runtime configuration, customer behavior and scientific acceptance remain separate evidence levels. No production request, database mutation, notification, browser persistence test, experiment, merge or deployment was run in Turn 3. Component timings in older PR bodies are not fresh endpoint measurements. Historical proof at an older head is not automatically proof for a changed head.

### Affected candidate frontier

| Candidate | Observed head | Integration implication |
| --- | --- | --- |
| #8004 issuer/security binding | `9f66ea9f4dbd9f9f894a9e8be4ebf9f5030433bc` | Open; reconcile existing identity owner work, not a new ticker map |
| #10176 withdrawal projection | `228c25d37617a7217c8f65f1613ade701a2fe01a` | Open Draft; current/withdrawn/stale/unknown semantics remain owned work |
| #10509 board/index epochs | `a40a1c5dfde7bae01e4bc852c182a0d230f048be` | Open Draft; exact publication generation is still material |
| #10202 settlement manifest | `e0c522c968e0f8367e0c313b9b39ef8fa2c9ff3a` | Open Draft/HOLD; do not substitute a digest for full served-byte settlement |
| #9369 request batching | `858e11a4d17f2d9387af720d01c6d84dcc80b49d` | Open Draft; fewer validations, repeated projection scans remain |
| #10824 native read expansion | `0a5fdea7148065ea5d14d099a439308bd2cddcec` | Open; avoids irrelevant row expansion, still reads/decodes/hashes parts |
| #10809 revision-read cost | `b7678072fd17a90806178f298a42e200a524b97c` | Open; prior accepted-head evidence has narrower scope than this current head |
| #8308 Cycle equity | `6b4b5ae5e2307453f2ddc0f2c0dbebe676c793b5` | Open; Cycle equity module absent from inspected main |
| #7399 PERF | `41ca935449b6668c60e0b5ba2a0863703e072d8c` | Open Draft; consumer absent main and terminal-ledger-only even in candidate |
| #10579 writer security | `f690d45e2321f637290d693ddcb446817427dd89` | Open Draft; specific identity/release hold affecting #9495 remains intact |

These observations refresh affected facts only. Appendix A's broader census remains its dated Turn 1 observation. Adoption requires reconciling current ownership and exact diff; this document neither takes over a live writer nor approves an entire candidate by association.

## 2. One coherent read, with explicit authority boundaries

### Existing integration seam

`engine/prophet_b4_same_read.py::evaluate_same_read_entry_availability` already obtains a native factual result, consumes `NativeFactualAssessmentResult.verified_pair()`, binds native quote/basis inputs to the same source relation, and reattests owner bytes. It deliberately passes empty `entry_rows_by_symbol` and `metric_inputs` because those native contracts are not qualified there. Creating another join service would duplicate this responsibility. [T301], [T302]

The actual Today producer, `scripts/build_stock_library.py::read_today_candidate_projection`, separately builds B3 and calls `compose_daily_brief` with `entry_availability`, `plan`, `evidence`, `assembly` and `quote` all `None`. After source and generation guards succeed, the outer result is `PARTIAL / DAILY_BRIEF_OWNER_INPUTS_UNAVAILABLE`, retaining available candidate identity, native provenance and factual `REVIEW_REQUIRED` assessment. Individual rows or B3 reads can still be unavailable. The nested entry decision is unavailable. This is useful research data; HTTP 200 does not turn it into cleared entry. [T303], [T304]

**Implementation decision:** evolve the incumbent gathering seam into one detached, verified request-local bundle consumed by B4 and the presentation compositor. Preserve native verification, source/generation binding and final reattestation. Do not call the current helper inside every Today row merely to rebuild B3. Do not accept a caller-supplied `prevalidated:true`, reconstructed raw B3 JSON or loose receipt as native proof. Keep public schemas closed or version the specific changed projection deliberately. An internal bundle is not a new public opportunity API or cache authority.

### Response and population contracts

| Layer | Existing behavior | Required consumer treatment |
| --- | --- | --- |
| Daily Brief request | Auth first; exact `source_sha256`, `pair_id`, `selection_receipt`; optional `candidate_generation_id` | Retain the caller's exact source binding; no filesystem path or newest-generation substitution |
| Outer response | AVAILABLE/PARTIAL → 200; source/selection mismatch → 409; owner UNAVAILABLE → 503; optional candidate-generation mismatch currently 503 | Preserve the typed owner envelope; do not infer readiness or empty data from status code |
| Query / route boundary | Malformed, unknown or repeated query → 400 `INVALID_QUERY`; admission overlap, import/read/serialization failure → generic 503 `DAILY_BRIEF_UNAVAILABLE` | Generic route failure has less context than a typed unavailable owner response; never fabricate missing rows or expose internal paths |
| Factual assessment | REVIEW_REQUIRED; assembly time does not renew input freshness; model thesis/review lineage unavailable | Label as factual/review-required until its owner supplies a qualified assessment |
| B4 decision | Independent deterministic state and blockers | Missing mandatory input means unavailable entry, while useful research stays visible |
| B03 observations | Full source population, nullable episode relationship, exact ticker/security search before paging | Observations are not admitted episodes; no cap-displaced loss; no invented readiness denominator |
| Plan relation | Exact original-source resolver exists; current Today producer supplies neither Plan input nor current-management assessment | Adapt original proof and independently qualify current management; retained provenance cannot confer current action |

B03 currently accepts ticker/security, offset/limit and snapshot constraints, not family or entry-state filters. Its source/matched/returned counts are not all-family readiness counts. Extend the existing read-model owner to support needed filter semantics before enabling Paper controls. Counts must name the universe, entitlement partition, filters, strategy/horizon/role, snapshot, coverage, exclusions and evaluated population. Unknown is null with a reason; it is not a successful zero. Selected Today buys, all source observations, admitted candidates and B4-evaluated rows are different populations. [T305]

Same-read `state=EVALUATED` means a B4 row exists; nested `availability.state` may still be `UNAVAILABLE_DATA`. Neither EVALUATED nor a CURRENT quote means ready. Missing evaluation and evaluated-unavailable results are separate counts. [T301], [T302]

### Identity grain

Navigation and comparison retain listing/security identity, issuer and epoch where supplied, source observation/event and receipt, exact published selection, nullable episode, episode generation and strategy. A DOM occurrence is a rendering identity, not a durable episode key. A pre-B1 row remains lawful without an episode. Save retains account/list/security membership. Portfolio exposure retains its existing issuer/instrument semantics. These grains must not be collapsed to ticker or to one new Prophet ID.

Exact query/source mismatches preserve the current safe context and explain why it cannot be refreshed coherently. A dated snapshot can remain inspectable only if the source is actually retained and current rights and entitlement permit it. Read-only presentation does not create a right to retain or disclose the data.

## 3. Clocks, entry terms and corrections

### Resolve the clock incompatibility before connecting geometry

The current source has a consequential ordering conflict: B3 records actual assembly time with microseconds; the same-read helper uses the stored `live_pass_ts` as B4 `decision_at`; the runtime composer requires pass time to equal decision time; the evaluator rejects a candidate projection generated after the decision. A stored pass normally precedes a new B3 assembly. After the missing geometry and metric owner adapters are supplied, that otherwise ordinary read can encounter a future-projection refusal. The missing adapters can currently mask this later condition. This is a source-level seam finding, not a reproduced production failure. [T301], [T302], [T306]

**Decision:** preserve live-pass provenance, evidence eligibility cut, factual assembly, native read completion and actual evaluation completion separately. The native reader already exposes `read_completed_at` and `quote_age_at_own_read_min`; it currently truncates completion to seconds, while B3 retains fractional seconds. The evaluation owner must choose a genuine evaluation time after its required inputs are available, re-age/requalify the inputs and gates at that time, preserve timestamp precision, and enforce future-known exclusion for a historical cut. Do not rename an old pass or rewrite B3's assembly time to satisfy an equality.

| Clock | Meaning | What a refresh may change |
| --- | --- | --- |
| Economic event / effective time | When the economic event or asserted economic effect occurred, only where the owner supplies that meaning | New owner-supported event/revision; unknown remains unknown |
| Source public availability | When that particular source version became publicly usable | Actual publication/availability receipt, never borrowed from fiscal period or event date |
| Owner known / recorded | When that owner observed or persisted the source | Actual new owner observation; not a borrowed event date |
| Evidence cutoff | Latest knowledge permitted for the declared assessment | A newly issued assessment with its own evidence membership |
| Live market pass | The stored producer's market pass | Only a new real pass |
| Factual assembly / publication | When the read or artifact was composed/published | A real assembly/publication; freshness remains independently qualified |
| B4 evaluation / quote | Actual evaluation time and the quote used in that decision | A new qualified evaluation; a later display quote alone changes neither decision nor assessment |
| Original Plan / management | Original terms and the management owner's latest assessment | Original terms remain retained; management advances only on an owner-issued result |

### Gate and price precedence

B4 currently checks inactive lifecycle, retraction, then `structural_invalidation == BREACHED` or `price <= invalidation`, before its quote-freshness and corporate-action-basis checks. The native quote reader already refuses stale/basis problems; independent geometry comparability is still unwired. Before joining it, qualify numerical price/geometry comparability explicitly. An owner-issued lifecycle termination, retraction or qualified BREACHED fact can retain its priority. An incomparable or stale numerical price must not become a confident new breach. [T302], [T306]

Numeric invalidation is mandatory for the registered tactical policy. The separate optional structural-invalidation gate may be UNKNOWN without deadlocking eligibility; BREACHED remains non-waivable. Therefore “all nine gates must PASS” is an incorrect implementation rule. Follow the exact registered policy's mandatory facts, not the number of pills in a design.

### Policy-specific terms

| Paper specimen term | Current source | Versioned extension / honest absence |
| --- | --- | --- |
| Entry zone | B4 publishes low/high and basis | Keep owner geometry, receipt, units and policy |
| Chase boundary | Input consumes `chase_above`; output exposes `chase_state` | Publish the owner's accepted numeric term if applicable; never reverse-engineer it from a state |
| Entry stop | Composer maps `entry_signal.stop` into structural invalidation; no separate output term | Require the policy owner to define a distinct stop before displaying one |
| Structural invalidation | Numeric price/kind/basis plus optional structural gate | Preserve actual meaning; unavailable and not-applicable differ |
| Valid through | Session eligibility and market session exist, not an explicit interval | Define owner expiry/revalidation semantics; a session string is not a fabricated expiry timestamp |
| Strategy horizon | Early Leadership `2_15_SESSIONS`, role `new_entry` | Never turn this into an Earnings/Cycle holding law |

These extensions preserve the intended Ready surface while preventing illustrative fields from silently rewriting policy. The registry marks each as an implementation obligation, with unavailable or not-applicable rendering until qualified. [T302], [T307]

### Correction and refresh invariants

One assembled read fixes source SHA, pair/selection, B1 generation, relevant identity receipts and quote/live owner bytes. A material change during assembly refuses the mixed view. Row-local failure remains an ordered unavailable row; generation-wide integrity failure cannot publish a mixed partial batch.

Corrections append evidence and change the current disposition without overwriting the original decision. B03's present lineage is `CURRENT_RECEIPT_ONLY`, with prior receipt and correction availability null; a before/after comparison requires retained revisions from the existing source/history owner. A newer quote cannot renew an older assessment, Plan or B4 decision. A dated fallback remains historical, not current readiness. Existing exact-identity fallback rules remain intact.

## 4. Complete the designed user actions

### Compare, evidence and return

Current #9495 comparison selects two or three live DOM cards inside one Today or Screener grid. “Compare selected” hides other cards in native order; changing grids clears selection. It does not implement the aligned Paper comparison or cross-filter retained selection. Extend that transient owner with exact resolved object references and chosen order separate from source rank. Preserve selection across legitimate table/grid/filter changes, show off-filter selected objects explicitly, and explain an obsolete or unauthorized selection without resolving to a newer same-ticker row. Mobile compares a deliberate pair from the retained set. [T308]

Existing `PVSetupReturn` and `USProphetSource` preserve exact live source nodes and native link, source stamps (`data-source-digest`, `data-as-of`, `data-board-asof`), target Plan, Sources tab, Plan-link focus, dialog scroll and page scroll. This guarded DOM/source-stamp return is a valuable foundation; it does not itself verify the complete B1/selection-pair identity. Canonical listing/occurrence/selection-generation keys are part of the new presentation contract. Exercise a changed Today binding as well as replaced nodes. The Plan target is resolved before leaving; missing or withheld targets leave the investigation intact. Browser history/reload restoration is a new explicit serialization contract, not a claim that current in-memory state is durable. Chart points need stable source/event references, accessible tabular values and a return path to the same selected evidence point; a generated explanation must not invent a source event. [T308]

The original Plan resolver already exists: `scripts/build_prophet.py::read_plan_candidate_source(plan_id, expected_plan_sha256?, expected_candidate_generation_id?)`, schema `prophet.plan_candidate_source_read/v1`. It verifies retained original board bytes, ordinal, row receipt and native B1 relation, including terminal/superseded original lineage. It intentionally reports `current_action_status=UNAVAILABLE`. Adapt this proof into the versioned presentation relation; Daily Brief v1 currently supports only related-security Plan references. Keep original provenance, target access and current management separate. [T309]

### Save, notes and thesis

Main WatchStore already has checked Save and observation-only `symbols.inspect`. Candidate `prophet_save.js` depends on `checkedSession` and account-scope guards that are present in its candidate WatchStore but absent from fresh main. The adapter itself is absent main. Integrate the required owner additions selectively; copying the adapter alone leaves it unusable, while replacing the whole owner file risks losing newer changes. Capture account scope before enqueueing, and fence late private results after account change. [T310], [T311], [T312]

The actual promise is security membership in a user-selected writable list. Confirmation needs owner readback and reopening that destination after ordinary refresh. This does not save a dated thesis, create a model plan, enable Follow or create a holding. Existing annotation fields and per-field compare-and-swap are reusable user-note capabilities, not immutable decision records. D05 still owns the explicit thesis, Pass/reason, milestone and dated investigation contract. [T342], [T343]

`symbols.inspect` always returns `writeRetryAllowed:false`. A present membership proves the desired membership now; it does not resolve attribution or terminal outcome of the earlier uncertain insert. Not-confirmed is not proof of no effect. The candidate's uncertainty custody is page-lifetime memory. Reload-resilient recovery must extend the existing checked Save owner with the original operation reference, immutable target and authoritative reconciliation; it must not fall back to the legacy retry outbox or create another attempt while the original effect remains unresolved. A new attempt requires authoritative no-effect reconciliation and permission from the existing owner. The Terminal schema owner has `0009_watchlist_symbol_unique.sql` and `wls_watchlist_symbol(watchlist_id,symbol)`. Source migration presence is not a fresh installed-schema check; an old Macro comment saying no unique index must not override the actual schema owner. [T310], [T312], [T313]

### Follow: actual initial capability and retained extensions

Main `engine/prophet_journey_notifications.py` is the existing pure B21 producer. It declares `prophet.b21.journey_notifications/v1`, category `prophet_research_journey`, designated list `Prophet Research`, channel `email` and tier `essential`. Eligible kinds are `episode_terminal`, `emergence_triggered`, `corrected_material`, `retracted`, `superseded`. It does no IO. It does not currently emit general assessment changes, OPENED events, quote-refresh events or B4 availability changes. [T314]

The Prophet category is absent from the current preference allowlist. Complete B21's existing preference/enrollment/IO/UI work around the pure producer and existing `not_after` drain guard. Preserve logical dedupe across generation/definition rereads and correction linkage to the original event. Use `public.alert_outbox`, the existing drain, mailer, suppression and entitlement owners. Do not add a subscription table, watcher, delivery queue, scheduler or auth plane. [T315], [T316], [T339], [T340], [T341]

| User-visible state | Required fact |
| --- | --- |
| Preference saved | Actual metadata persistence and account preference readback; `ok:true` or HTTP 200 alone is insufficient |
| Following this security | Deliberate designated-list membership and supported opted-in category/channel, each independently confirmed, with the corresponding producer/delivery capability admitted and available |
| Follow configured · notifications unavailable | Enrollment persists, but the relevant producer or delivery capability is unavailable; do not imply active monitoring |
| Event detected | Eligible source-owner event with exact episode/receipt and logical identity |
| Queued | Existing outbox row; not a send receipt |
| Email sent | Existing transport's observed acceptance; not inbox arrival or reading |
| In-app delivered/read | A separately implemented, qualified capability; no inference from email or outbox resolution |

The Paper design's in-app confirmation and broader event choices remain retained implementation obligations, not initial enabled controls. Never silently change the user's in-app choice to email. Ordinary Save into an arbitrary list must not enroll Follow. Preference success with membership failure, or the reverse, shows the exact partial result. Unknown delivery effects remain on the original carrier and existing quarantine path.

### Current, History and Record

Current attention, model-plan lifecycle, current entry and actual user holdings are distinct. Terminal's legacy ProphetView BEST uses management confidence; active count uses `phase != invalidated`; PERF is a placeholder. Preserve the managed macro/options scope until a qualified replacement proves parity. It cannot become the new research ordering or current-attention definition by changing a label. [T317]

Native `prophet_integrity.py` already owns effective plans and ledger, append-only correction validation and quarantine. #7399 adds a useful terminal-ledger PERF consumer; it is not main and does not supply original eligible populations, unresolved plans, period-basis cohorts or strategy/model/policy-vintage joins. Extend the existing plan/B1/integrity consumer rather than building another evaluation store. [T318], [T319]

Record must expose separate entry disposition, outcome maturity/availability and integrity disposition under its declared population and cutoff. Entry distinguishes proved entry, explicit no-entry and unverified entry. Outcomes distinguish qualified terminal evidence, unresolved/not-yet-mature and missing or unsupported evidence. Integrity separately records inclusion, corrections, quarantine and any owner-supported retraction. Reconcile counts within each declared axis; do not sum overlapping labels into a cohort denominator. An entered plan may still be unresolved or quarantined. A null entry clock is neither explicit NO_ENTRY nor proved entry; absence of a terminal row does not imply zero unresolved plans. Retraction requires its actual entity, generation and effective time: a source/B1 retraction cannot automatically become a retroactive Plan exclusion or rewritten outcome. Retain original versus effective corrections, reconstructed records, source cut, period basis and policy vintage. Raw unweighted underlying returns are not portfolio returns, options P&L, excess returns or alpha. T1/T2 closing outcomes are not ever-hit frequencies. The displayed filter must not secretly reconstruct the historical denominator. [T318], [T319]

## 5. Deeper intelligence without overstating qualification

### Three initial economic investigations

| Investigation | Existing capability | Required source-bound enhancement |
| --- | --- | --- |
| Early Leadership | Compiler checks issuer/security/theme joins, exclusion assertions, matched membership/window/basis and coverage | Prove the peer producer actually excludes the candidate's issuer and all listings; show coverage and confirmed exposure versus membership-only context |
| Quality Earnings | Comparable facts, expectation/revision arithmetic and one admitted D5 vector; fixed Q06 comparator | Bind per-share evidence to issuer/event/time/basis; keep release, call and filing knowledge separate; do not imply a generic consensus feed |
| Cycle Capture | #8308 candidate funding and original-equity scenario mechanics | Integrate accepted candidate and qualified sources; preserve financing assumptions, early breach, dilution and original-security claims |

Early Leadership's descriptive stock/peer/market decomposition remains useful even when the stock trails its peers. Equal-weight peer return, median return and positive share remain null for singleton/empty qualifying peers. Partial pricing stays partial. The current compiler validates exclusion assertions; acceptance must vary the candidate's own return and add another listing of its issuer at the producer, then demonstrate unchanged excluded-peer confirmation. Current membership is not historical membership; theme membership alone is not economic exposure. [T320]

For Earnings, `per_share_bridge` is unbound scalar arithmetic. `factual_dossier` validates its schema/kind/non-authority but lacks the issuer/event/time matching imposed on other children. Qualify income and shares through the incumbent Earnings/D5 owner before attaching the bridge: fiscal periods, GAAP/adjusted basis, currency, units, basic/diluted share basis, revision and availability. A same-period restatement is a correction, not growth; post-release expectations are not pre-release surprise. [T321]

Native D5 source admission requires `source_available_at`, `observed_at` and `generated_at` all at or before the episode's original decision cut, `candidate_episode.opened_at`, verified against the exact B1 cut. A later factual assembly or live B4 reevaluation does not advance that original evidence membership. A current/landmark interpretation needs an explicit owner contract while retaining the original view. `source_effective_at` and `captured_at` are intentionally named nulls here, not aliases to fill from a nearby date. Later revision receipts remain separate from the decision version. `OBSERVED_UNPROJECTABLE` cannot become current. The dossier's original-source-vintage reconstruction is explicitly not an original as-run recommendation. These distinctions must be visible in the deep evidence view, with a concise explanation above it. [T322], [T323]

Cycle needs a dated funding path, accessible/restricted cash, minimum operating floor, financing fees, debt and share changes, and value reaching the original security. A later rescue cannot erase an earlier breach. A surviving business may leave old shares with no value. New capital contributions belong in the scenario return denominator. Canceled original securities need qualified distribution mappings; an assumed replacement share must not be silently spliced into history. Financing cash must not be counted twice in enterprise-to-equity conversion. Conditional scenario arithmetic is not financing access, calibrated survival probability or accepted core/add/exit management. [T324]

### Explain, compare scenarios and show what changed

The advanced experience has four useful layers: a concise owner-supported thesis; the strongest supporting and opposing evidence; the next observable condition or disconfirming event; and deep source/assumption inspection. Use the existing Brain/explanation path only as a cited synthesis consumer. It may summarize qualified owner facts, disclose unavailable inputs and compare explicit scenarios. It cannot generate B4 facts, approve sources, infer a personal position or turn narrative confidence into ranking, sizing or management authority.

Material-change explanations require real original/current source references and a qualified revision. Distinguish changed evidence, changed model/policy, changed price and changed user context. A quote tick is not a new published assessment. Scenario controls retain units, baseline, source dates, assumption versus observation and sensitivity limits; resetting returns to the original owner scenario. If probability is unqualified, show conditional outcomes without probability labels. Context reuses GMI/theme and Portfolio/Risk with common issuer exposure counted once.

### Scientific qualification stays separate

Current strategy source declares Early Leadership `CONTROL_ONLY / SHADOW_ONLY`, Earnings `SPEC_ONLY_FACTUAL_EVIDENCE_BUILDING`, Cycle `SPEC_ONLY`. Early Leadership's `2_15_SESSIONS` is the frozen new-entry identity, not a holding or exit rule; H10/H5/H15 are research endpoints. Earnings H42 with H21/H63 support and Cycle H252 with H126/H504 support remain research proposals rather than printed holding durations. Ranking answers a declared attention task; B4 answers current policy availability; management answers an existing Plan's accepted policy. Each has its own definition, evidence, version and qualification. [T307]

All 24 Q packets are unchanged at blob `47fd83c4b403476a59015cc8fdfb272d6a0d8814`, still `SPECIFIED_NOT_REGISTERED_OR_DISPATCHED`, with protected-outcome permission false. The full endpoint/falsifier matrix accompanies this report. Preserve same-origin comparisons including never-confirmers/no-fill/no-entry, origin versus landmark cohorts, source/model vintage, selected top-K calibration, abstention coverage, overlapping/dependent observations, fair baselines and compute budgets, cost/fill realism and failure-inclusive original equity. A source repair or polished explanation does not promote a head. Missing evidence means unsupported; rejection needs an actual owner disposition or an already binding killed-mechanism ruling. [T325]

## 6. Production truth, access and performance

### F04 and W07

F04's current template treats missing `dislocation` as false and renders “Closed — no dislocation yet.” Its health owner has no dislocation input. Extend that existing health/presentation contract with typed source availability and nullable market verdict. Qualified explicit false may be closed; missing, empty, malformed, unknown or stale input may not. Avoid copy implying continuous detection without a current owner fact. [T326], [T327]

W07's loader collapses missing, malformed, non-dict and stale to `None`; the template then uses warm mode. The age check is six calendar days despite a session-based comment; tape-lag sessions are a separate concept. Resolve clock semantics at the incumbent owner. Preserve valid empty cohort, insufficient evidence, unsupported identity, source failure and stale data as distinct states with actual denominator and as-of. No second Winner Health analytics engine is needed. [T328], [T329]

### Account and source isolation

Terminal already has a thin authenticated observations BFF, strict decoder and one `useProphetObservation(active,userId)` hook in TerminalShell. It preserves Macro authority, private no-store, bounded request/body size, auth/symbol invalidation and visibility-based refresh. Extend that seam; do not introduce another session, fetch/cache or polling authority. [T330], [T336], [T337], [T338]

Authenticate and establish actual entitlement before protected owner reads. Invalidate private detail, comparison, returned selections, source inspectors and in-flight responses on account change. A late account-A response cannot populate account B. Counts, facets, anonymous DOM, JSON, exports, notifications and telemetry must not leak withheld rows. Treat source/provider text and generated explanations as untrusted content for rendering and instruction handling. Preserve escaped text, existing source-link handling and receipt-bound references; never execute source instructions or let a narrative bypass an owner gate.

Public immutable assets and private owner reads have different cache contracts. Do not show cached READY during revalidation of a withdrawn source. Existing B03 already owns one immutable relation-cache entry capped at 4 MiB and keyed to full byte attestation/receipt, with reattestation on reuse. Extend its owner if profiling justifies it; do not add another trust cache or TTL-based bypass. [T305]

### Performance and accessibility acceptance

#9369 reduces repeated full native validation through entry/exit batch checks, but retains O(bindings × generation rows) projection work. #10824 still reads, decodes and hashes all parts before filtering expansion. Measure the actual entitled endpoint, payload, concurrency, peak memory and ordinary-refresh path after integration. Reuse unchanged exact evidence and broaden tests only for concrete risks. An optimization must preserve corruption/change detection and the complete observation population. [T331], [T332]

Retain the plan's proposed server/render budgets as targets to calibrate, not measured SLOs. The browser target is Core Web Vitals at the 75th percentile, separately for mobile and desktop: LCP ≤2.5 seconds, INP ≤200 ms and CLS ≤0.1. Collect real-user evidence through the incumbent telemetry owner after rollout; a local fixture cannot establish those population metrics. [T333]

Progressively render useful verified research, then deeper evidence. Skeletons retain layout; unknown values are not zero; stale and missing states explain a next useful step. Keep visible keyboard focus, meaningful headings/table semantics, text alternatives for chart values, source focus return and reduced-motion behavior. Prove EN/ZH and light/dark at the designed desktop/mobile sizes, 320 CSS-pixel reflow, 200% text zoom and 400% page zoom where applicable. WCAG's two-dimensional content exception permits a genuinely necessary table/chart viewport, not whole-page horizontal overflow. Sticky navigation or banners must not entirely obscure the focused control. These are implementation acceptance requirements; Paper screenshots alone do not prove them. [T334], [T335]

## 7. Dependency-preserving implementation and cutover

The seven existing packets remain the delivery groupings. The machine-readable registry maps every contract and all original B/Q/D/R identities into them. It is documentation, not a second work scheduler. Candidate dispositions and actual release holds are verified at implementation time; no extra reviewer seat or blanket independent-review ceremony is introduced.

| Packet | Concrete end-to-end increment | Critical dependency / proof |
| --- | --- | --- |
| P1 source-to-consumer substrate | One verified request-local read; exact identity/clocks; typed correction and publication outcomes | Current incumbent diffs, owner fields, corruption/change refusal and real endpoint profile |
| P2 research-to-watch | Entitled row → Setup/Sources → aligned Compare → exact Plan/return → checked Save | Preserve #9495 hold, selectively integrate WatchStore, prove membership/readback and uncertain-outcome behavior |
| P3 entry mechanics | Native geometry/gates/metrics → deterministic B4 → applicable terms and honest current assessment | Clock/price precedence cases, actual policy qualification, no model waiver; research journey need not wait |
| P4 three intelligence journeys | Independent peers; comparable Earnings/per-share; source-backed Cycle funding/original equity | Existing compiler/D5/candidate owners and exact missing states; scenario is not science promotion |
| P5 forecasts and management | Individually accepted heads, task ranking and policy versions | Existing Q protocols, rights, registration, protected-outcome controls, calibration/cost/management acceptance |
| P6 attention and outcomes | Actual supported Follow → owner event → existing transport receipt; complete Record and Portfolio context | Category/enrollment/IO proof, original/effective cohort joins, no automatic opt-in or holdings inference |
| P7 integrated production | Accessible responsive served journeys, ordinary refresh, telemetry, compatible rollout and rollback | Actual source/served identities, bounded rollout controls, retained legacy/options/data history, all advertised obligations dispositioned |

P1 and P2 can advance under original A01/A02/A04 while live B4 or some scientific families remain unqualified. A03 historical policy-free research and A05 qualified offline model work retain their independent prerequisites. These branches avoid making one unavailable optional family a global product blockade. They do not erase D03/D06/D07/D08, live-entry, management or release gates. Partial release is a milestone, not full programme acceptance.

### Migration rules

Resolve current writer and source carrier before changing an incumbent candidate. Integrate exact required slices against current main; preserve later work and every unresolved effect. #9495's writer-security hold requires the actual selected GitHub identity to be eligible, distinct from excluded author/coauthor identities, before its allowed release actions. Fable's name alone does not prove eligible identity. Required CI, CODEOWNERS/security/release controls still bind; the current Web waiver removes invented review ceremony, not actual controls.

Reuse shared card/detail templates and authenticated hydration. Preserve the legacy managed macro and options lanes until the new consumer proves their claimed parity. Version actual changed projections; keep compatibility readers until installed consumers are reconciled. Do not run a schema migration simply because its source file exists; inspect the actual migration state through its owner when implementation needs it.

Rollout uses existing flags, publication and deployment controls. A bounded cohort proves the source generation reaches the entitled screen after normal refresh. Rollback restores the prior accepted presentation/reader while retaining user memberships, original Plans, appended corrections and event receipts. It does not rewind financial history, erase queued/uncertain effects or restamp assessments. The exact rollback unit and compatibility window are recorded before rollout.

### Acceptance cases that decide completion

| Case | Observable result required |
| --- | --- |
| Still-fresh same-session market pass preceding new B3, other owners qualified | Truthful distinct clocks; qualified evaluation without false future-clock refusal, including fractional-second boundary; stale/cross-session inputs still refuse |
| Price below invalidation with stale/incomparable basis | No unsupported numeric breach; actual owner retraction or lifecycle termination remains visible |
| Source/B1/quote changes during composition | Coherent old or new result, or explicit refusal; never a mixed readiness view |
| Same ticker, different listing/episode/generation | Correct selection, comparison, original Plan and return; no substitution |
| Missing optional dossier, mandatory entry input absent | Useful research retained; current entry unavailable with the exact missing reason |
| Source correction while detail/Compare is open | Original version remains dated if retained/authorized; current disposition and changed selection are explicit |
| Save response lost | One original attempted effect; exact membership read cannot authorize replay; reload/account-change custody is honest |
| Concurrent Macro/Terminal Save | Existing schema/owner converges on one membership without losing unrelated list/order data |
| Follow partial preference/list failure | Separate readbacks; no false Following, no channel remap; quote ticks do not become events |
| Supported Follow event | Actual eligible source event → existing outbox → authorized transport → exact receipt, including expiry/suppression/unknown states |
| Peers include candidate alias or later membership | Producer qualification fails or excludes it; descriptive evidence does not become entry approval |
| Earnings later filing, revision or mismatched shares | No future-knowledge/comparability leak; original and effective facts remain inspectable |
| Cycle survives after financing but old equity fails | Earlier breach, contribution denominator and original-security value remain correct |
| Terminal-only Record with absent outcome rows | No invented zero unresolved or all-eligible denominator; no-entry/missing-entry clocks remain distinct |
| F04/W07 missing, stale, malformed, valid empty | Exact availability and reason; no false Closed, zero winners or success-rate claim |
| Account switch or access loss during reads | Private content, counts and late results do not cross accounts or survive lost entitlement |
| Ordinary refresh and rollback | Served version/source still coherent; user/history/effect custody preserved; incumbent observer proves the result |
| Keyboard/zoom/mobile/EN-ZH | Investigation, source focus, selected pair, state copy and actions remain understandable and operable |

These are future discriminating proof obligations, not tests claimed executed here. Each worker return names exact source head, changed contract, affected checks, actual consumer path, served version/generation, observed outcomes, unresolved effects and next dependency. Reuse existing proof where the relevant inputs are unchanged; never reuse stale-head evidence as current approval.

## 8. Turn 4 freeze frontier and preserved design custody

Turn 3 resolves the architectural choices above and records the remaining owner decisions explicitly. Turn 4 must consolidate them into final bounded briefs: the exact evaluation/term projection version; source-backed population/filter and Record envelope; D05 dated-thesis versus note persistence; B21 initial capability and retained notification extension slices; selected candidate integration/disposition; and deployment/rollback acceptance tied to the real T3 target. These are implementation specifications and release dependencies, not requests to reopen the completed design direction.

Paper remains the reviewed candidate at page `p-F-0`. Its richer controls are target behavior; this source-bound contract governs what can be enabled and what must show unavailable until implemented. No Paper mutation occurred in this architecture turn. The original mobile Plans operation `prophet-four-turn-t2-20261109-mplans-tabs`, target `1EF3-0` inside `1EEH-0`, remains EFFECT_UNKNOWN after its original transport timeout. No retry, replacement, new carrier, finish or mutation of that subtree is authorized by this document. Two earlier absence reads did not establish terminal no-effect. Original manifest and HTML remain retained. Older ZE5/F01/#9495 effects and holds remain on their original carriers.

Turn 3 completes when this report, the exact contract/program registry, source dossiers and masterplan v3 are saved/read back; the updated PDF is visually checked; and AgentOS carries the exact Turn 4 continuation. The overall four-turn commission and production product remain incomplete. Turn 4 follows the Chairman's next editorial turn. A future handoff is not pickup, START, deployment or acceptance.

## Sources

[T301]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_b4_same_read.py
[T302]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_entry_availability.py
[T303]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/scripts/build_stock_library.py
[T304]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/app/prophet_daily_brief.py
[T305]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_early_observations.py
[T306]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_entry_availability_sources.py
[T307]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_strategy_definition.py
[T308]: https://github.com/mastermindx-market-intelligence/macro/blob/d42d83307948141c05967d7081a6cc7cbeb24a90/templates/theme.js
[T309]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/scripts/build_prophet.py
[T310]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/templates/watchstore.js
[T311]: https://github.com/mastermindx-market-intelligence/macro/blob/d42d83307948141c05967d7081a6cc7cbeb24a90/templates/watchstore.js
[T312]: https://github.com/mastermindx-market-intelligence/macro/blob/d42d83307948141c05967d7081a6cc7cbeb24a90/templates/prophet_save.js
[T313]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/supabase/migrations/0009_watchlist_symbol_unique.sql
[T314]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_journey_notifications.py
[T315]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/lib/user_prefs.py
[T316]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/app/account_prefs.py
[T317]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/components/prophet/ProphetView.tsx
[T318]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_integrity.py
[T319]: https://github.com/mastermindx-market-intelligence/macro/blob/41ca935449b6668c60e0b5ba2a0863703e072d8c/app/hub.py
[T320]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_early_leadership_evidence.py
[T321]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/sue.py
[T322]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_lab/intelligence_vector.py
[T323]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_lab/earnings_dossier.py
[T324]: https://github.com/mastermindx-market-intelligence/macro/blob/6b4b5ae5e2307453f2ddc0f2c0dbebe676c793b5/engine/prophet_cycle_equity.py
[T325]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json
[T326]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/templates/foresight.html.j2
[T327]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/foresight_health.py
[T328]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/scripts/build_winner_health_page.py
[T329]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/templates/winner_health.html.j2
[T330]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/components/TerminalShell.tsx
[T331]: https://github.com/mastermindx-market-intelligence/macro/blob/858e11a4d17f2d9387af720d01c6d84dcc80b49d/engine/prophet_candidate_state.py
[T332]: https://github.com/mastermindx-market-intelligence/macro/blob/0a5fdea7148065ea5d14d099a439308bd2cddcec/engine/us_candidate_episode_intake.py
[T333]: https://web.dev/articles/vitals
[T334]: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
[T335]: https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html
[T336]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/lib/prophetObservationsServer.ts
[T337]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/lib/useProphetObservation.ts
[T338]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/lib/prophetObservations.ts
[T339]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/alert_delivery_drain.py
[T340]: https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/scripts/drain_alert_outbox.py
[T341]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/app/api/alerts/receipts/route.ts
[T342]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/lib/watchlistAnnotations.ts
[T343]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/supabase/migrations/0033_watchlist_annotations.sql
