<!-- Source evidence appendix from bounded Turn 3 C3 read. Integrated architecture report and contract registry govern the final interpretation; this appendix does not grant implementation, review, admission or release authority. -->

# Prophet Turn 3 — backend contracts and consequential gaps

## Scope and evidence boundary

Scratch architecture analysis for root integration, 9 November 2026. This is a bounded source review, not the canonical user deliverable. Fresh Macro main: **9a13c64bf69f782332afa29efb09fe48ee30b857**. Protected Mastermind pin reused: **3652d8907df1738de551dd3032b42aa2a2acb482**. Turn 2 demands were read from masterplan v2, section 13.10, at **1b44fbe5bf307d624c242a346c81cf8fc877c46c**.

No runtime, production evaluation, HTTP, signed-in browser, CI, or deployment proof was performed. No external mutations, workers, watchers, Paper edits, or release changes. #9495 remains Draft/HOLD at d42d83307948141c05967d7081a6cc7cbeb24a90. Held Paper 1EEH/1EF3 and ZE5 were untouched.

## Consequential architecture conclusions

1. **The same-read B4 join already exists.** Extend engine/prophet_b4_same_read.py and its incumbent owners; do not commission another join service. It currently supplies empty entry geometry and metric maps deliberately, so it cannot support the reviewed Ready specimen through that path.
2. **The real Today API still supplies a partial research read.** Its producer passes no B4, Plan, evidence, assembly, or latest-quote owner into the compositor. This is a concrete consumer integration gap, not evidence that the existing deterministic B4 evaluator is absent.
3. **One bundle must serve B4 and presentation.** Today already performs a B3 owner read. The same-read helper performs its own B3 read and returns IDs/binding/availability, but not the assessment and qualified quote inputs needed by the compositor. Naively calling it inside the current Today loop duplicates reads and does not establish one shared owner result.
4. **Two consequential B4 clock/precedence issues require explicit owner decisions before geometry is connected.** Fresh B3 assembly time can be later than the stored live-pass time that the same-read helper uses as decision time. Separately, price-derived invalidation is evaluated before quote/basis availability. These are source-level seam findings, not claims of a reproduced deployed defect.
5. **Exact original Plan provenance already has an owner reader.** scripts/build_prophet.py::read_plan_candidate_source proves retained original selection bytes and the exact native relation. It deliberately grants no current action. Daily Brief v1 still supports only related-security Plan references; the missing adaptation should reuse this reader.
6. **B03 has an incumbent bounded attested cache and server-first exact search.** Preserve it. It is an observation population with nullable B1 relation, not an all-strategy readiness aggregate.
7. **Performance proposals must retain their narrow claims.** #9369 reduces repeated native validation within one request but retains O(bindings × generation rows) projection work. #10824 still reads, decodes, and hashes every part; it avoids expansion of irrelevant rows. Neither establishes an end-to-end latency or memory target.

## Contract and gap matrix

| Demand | Existing exact source contract | Missing or materially narrower behavior | Minimal incumbent-owner extension |
| --- | --- | --- | --- |
| U08: identity and return | B1 episode_id binds security_id + identity_epoch + canonical structural anchor + episode generation. B1 row retains company_id, ticker_at_observation, identity specification, correction_state, superseded_by. Today selection binds source_sha256, pair_id, selection_receipt, original selection_index and row_receipt; candidate binding adds episode_id, candidate_generation_id and market_session. | No one ticker can identify an occurrence. The Daily Brief binding is narrower than the proposed complete listing/issuer/observation UI envelope. Pre-B1 observation identity must not be forced into a B1 episode. A new generation is not silently interchangeable with a retained selection. | Carry incumbent identity references and exact occurrence/source selection into navigation and owner requests. Keep episode nullable for B03. Version any projection that needs additional issuer/listing/market/currency/basis metadata; resolve it through existing identity owners. No new Prophet identity table. |
| U10: clocks | B1 separates occurred_at, known_at, recorded_at. Native B3 asof/projection.generated_at is actual assembly time and explicitly does not renew freshness. Native quote read separates source_known_at, snapshot_asof/ts, live_pass_ts, quote_observed_at, read_completed_at and disclosed freshness policy. Daily Brief has eight clock slots. | Model assessment issuance, evidence cutoff, validity interval and management assessment time are not supplied by the present Today producer. Source-only Plan read has original clocks, not current management assessment. See clock conflict below. | Project owner-named clocks with explicit unavailable/applicability state. Preserve original facts, current research assessment, current quote, publication/read assembly, and management assessment as different fields. A refresh may advance only the clocks actually re-read or recomputed by their owner. |
| U21: exact candidate-to-Plan relation | read_plan_candidate_source(plan_id, expected_plan_sha256?, expected_candidate_generation_id?) returns prophet.plan_candidate_source_read/v1 with exact source bytes/ordinal/row receipt/native relation. It keeps source_relation_status separate from current_action_status, which is always UNAVAILABLE. | Daily Brief v1 accepts Plan state RELATED_SECURITY, NONE, or UNAVAILABLE, and requires exact_relation = unavailable. No native producer for the Daily Brief Plan envelope was found by targeted search. Existing original-source reader is not itself a management or current-entry API. | Adapt the existing Plan source reader into a versioned presentation relation. Preserve exact original plan_id and plan_sha256 plus source_origin/source_binding/native_identity. Current assessment/terms/eligibility remain separately owned and separately clocked. Never infer a Plan from a ticker match or relabel original provenance as current qualification. |
| U24: strategy/horizon | prophet.strategy_definition/v1 describes Early Leadership, CONTROL_ONLY, SHADOW_ONLY, primary 2_15_SESSIONS, new_entry. The eight-sleeve strategy catalog has all authority flags false and explicit definition/horizon status. B4 validator accepts only the registered Early Leadership identity. | Catalog presence is roadmap truth, not a routing/entry/hold policy. Earnings/Cycle horizons and readiness cannot inherit Early Leadership's numeric horizon or gates. | Resolve owner-supplied strategy_definition_id, strategy_id/version, horizon/role, entry_policy_version and scientific status. Unknown or unqualified families retain useful research evidence and explicit missing policy. Preserve disagreements and multi-sleeve matches without universal scores. |
| U34: aggregate readiness | B03 query_observations filters the full source population before pagination and returns source/matched/returned counts bound to snapshot_id. Today outer read returns selected candidate rows, with row-specific availability. | Neither inspected owner supplies all-family aggregate readiness. B03 query accepts security_id/ticker/offset/limit/snapshot only; it has no family/entry filter. B03 source count is not a B4-evaluated denominator. The actual Today read is selected-buy population, not all candidates. | Extend the existing population/read-model owner with exact supported universe, filters, strategy/horizon/role, snapshot generation, coverage and native-state counts. Filtering precedes pagination. State whether counts cover observations, qualified candidates, B4-evaluated rows, or presented selections. No frontend-derived full-population readiness. |
| Current entry facts | Existing B4 closed facts include quote, geometry, nine named gate dimensions, metric inputs, source receipts; output has deterministic state, owner geometry, quote clock, strategy identity, blockers and availability_id. Native quote/basis reader reattests real files and re-ages at its own completion. | Same-read path deliberately supplies geometry and metric maps empty. Composer leaves independently produced entry geometry basis UNKNOWN and unwired mandatory gate owners UNKNOWN. B3 retains B4_NOT_AVAILABLE. | Qualify native geometry/metric/gate inputs through their incumbent producers, with clock, price basis, source receipt and source-session semantics. Wire one verified request-local owner bundle to deterministic evaluation and presentation. Do not fabricate PASS or attach loose receipts. |
| Progressive UI | GET /api/prophet/daily-brief/v1 authenticates first, validates exact binding query, and returns the producer's model. Outer PARTIAL is HTTP 200. Native candidate input/provenance and factual REVIEW_REQUIRED assessment can be retained. | Each nested brief remains decision UNAVAILABLE while required owners are absent. Outer PARTIAL does not mean partially cleared entry. UNAVAILABLE is HTTP 503; exact source/selection mismatch is HTTP 409. Optional candidate-generation mismatch currently remains 503. | Show retained research facts and their provenance alongside precise missing-owner state. Do not turn useful partial research into an empty error screen, or HTTP 200 into readiness. Preserve actual route semantics unless a versioned API change is deliberately implemented. |

## Exact fields and state distinctions to freeze

### B1/B3 and occurrence identity

- engine/us_candidate_episode.py::episode_id produces pe:{security_id}:{identity_epoch}:{anchor_token}:{generation}. The canonical anchor includes kind, time, decimal price, and basis; its source receipt is provenance, not part of canonical anchor identity.
- Native relation matching uses source_system/source_schema/source_event_id/source_receipt. Withdrawn, suppressed, ambiguous, terminal, wrong-receipt and missing relations are distinct. A current same-ticker observation cannot stand in for another receipt.
- scripts/build_stock_library.py::_today_native_source_candidates preserves selected ordinal and row receipt before resolving native identity. candidate_input has security_id, episode_id, candidate_generation_id, market_session, owner_ref, asof, source_receipt, selection_receipt and display. native_provenance adds source_event_id/source_receipt, original selection_source_emit, generation_recorded_at and exact relation clocks.
- NativeFactualAssessmentResult freezes and re-verifies its detached assessment/projection pair. Its factual assessment is REVIEW_REQUIRED, with model_thesis/review_lineage unavailable and source_freshness = NOT_RENEWED_BY_ASOF. It is not a CURRENT model recommendation.

### B03 observation population, correction and coverage

engine/prophet_early_observations.py::load_observations preserves every valid source row, including unscored/cap-displaced rows. A broken identity or B1 join degrades that relationship while retaining observations; invalid source bytes invalidate the population rather than manufacturing successful zero.

Each row exposes source_event_id, source_receipt, ticker, nullable security_id, identity_basis, source_session, triggers_fired, source_visibility, source_evidence, lineage, episode_relation and authority. Identity basis is CURRENT_REFERENCE_ONLY or UNRESOLVED; it does not claim a historically available alias map.

Lineage is presently CURRENT_RECEIPT_ONLY, with prior_receipt = null and correction_available_at = null. A correction comparison UI cannot infer the historical version or its availability time from this payload. Extend the incumbent source/history owner to supply retained revisions and their clocks; where missing, render unavailable.

The source coverage partition is verified only when the producer's public artifact receipt, session, full ticker population and deck/beyond-cap counts agree. Unknown coverage is null, not zero. Query counts are source/matched/returned; source and matched become null on failed source read.

snapshot_id binds source receipt, rows, coverage, B1 generation and identity receipts. Query snapshot mismatch is refused. Search is exact ticker (including unresolved rows) or canonical security_id; it is not fuzzy global text search. Do not promise family/current-entry filters without extending this contract.

### B4 inputs, outputs and policy-specific terms

Current facts schema requires these closed components:

| Component | Fields / semantics |
| --- | --- |
| quote | price, asof, freshness, basis_version, source_receipt |
| geometry | owner_status, zone_low, zone_high, chase_above, invalidation_price, basis_version, source_receipt |
| deterministic_gates | owner_confluence, risk_ceiling, liquidity_fillability, gap_velocity, source_health, corporate_action_basis, session_eligibility, event_status, structural_invalidation |
| metric_inputs | first_trigger_price, anchor_price, atr |
| envelope | decision_at, market_session, source_receipts |

The present registered strategy requires numeric invalidation_price. The separate structural_invalidation gate is an optional additional thesis/falsifier extension: BREACHED is non-waivable, but UNKNOWN intentionally does not deadlock the strategy. A requirement that all nine gate dimensions must equal PASS is incorrect.

Output exposes zone.low/high/basis, current_price/current_price_basis, quote_asof/quote_age_seconds, invalidation.price/kind/basis, distance_to_zone_pct, risk_to_invalidation_pct, move_since_first_trigger_pct, move_since_anchor_pct, extension_atr, chase_state, owner_status, blockers/reasons, strategy/policy identity and availability_id.

The Ready Paper specimen needs a careful presentation extension:

| Paper term | Current source behavior | Required architecture decision |
| --- | --- | --- |
| Chase boundary | Numeric geometry.chase_above is consumed; output publishes only chase_state. | Publish the accepted owner's actual boundary through a versioned term projection when applicable. Do not reconstruct it from a displayed state. |
| Entry stop vs structural invalidation | Runtime composer maps entry_signal.stop into geometry.invalidation_price; output labels its kind structural. There is no distinct entry_stop term. | Preserve the incumbent meaning until the policy owner qualifies separate terms. If a strategy has no independent entry stop or structural term, show not provided/not applicable. Paper's two prices do not create a universal policy requirement. |
| Valid through session | market_session and session_eligibility gate are present; there is no output validity interval. | Obtain actual source/decision validity from the applicable policy owner. A session check or assembly timestamp is not a fabricated expiry. A policy can legitimately lack a separate interval, but current action eligibility must still respect its real qualified gates. |
| Ready | B4 state ENTRY_OPEN is one registered policy result; same-read wrapper state EVALUATED means a B4 row exists, not necessarily ENTRY_OPEN. | Preserve native state, scientific/policy qualification, binding and current consumer health independently. Never count wrapper EVALUATED or a CURRENT quote as entry readiness. |

A versioned owner term projection should carry policy-specific applicability and provenance rather than make all visual fields mandatory in every sleeve.

## B4 clock and precedence findings

### A. Assembly clock versus stored live-pass clock

Confirmed source chain:

1. build_native_factual_assessment_result uses the actual owner assembly instant for assessment.asof and projection.generated_at.
2. evaluate_same_read_entry_availability chooses decision_at from owner_read.clocks.live_pass_ts.
3. compose_runtime_owner_facts requires live_meta.pass_ts == decision_at.
4. evaluate_entry_availability rejects candidate_projection.generated_at > decision_at.

An ordinary stored live artifact whose pass preceded the request's new B3 assembly is therefore incompatible once the currently missing geometry/metric inputs are connected. Missing geometry can refuse earlier and hide this later check. This is not a live reproduction claim.

**Minimal design decision:** keep live-pass provenance, source known/recorded clocks, B3 read assembly and actual B4 decision time distinct. The native reader already exposes read_completed_at and quote_age_at_own_read_min after re-aging against the artifact's own policy. The incumbent owners can define a genuine current evaluation completion, validate pass-time facts, and qualify applicable gates at that current decision time; a historical evaluation instead needs a real knowledge cutoff. Never overwrite B3 generated_at, pretend a historical pass happened now, or reproject a different source session to satisfy equality. Preserve timestamp precision: B3 can carry fractional seconds while native read_completed_at currently truncates to seconds.

**Discriminating acceptance:** with a stable live artifact passed before the request, valid source evidence and qualified geometry, the real consumer reaches the correct current state with truthful clocks. A source fact known after a historical decision remains excluded/refused. Boundary within one second must not create a false future-clock refusal through truncation.

### B. Numeric invalidation before quote/basis checks

evaluate_entry_availability currently checks non-ACTIVE lifecycle, RETRACTED event, then structural_invalidation == BREACHED or price <= invalidation before checking quote freshness and corporate-action basis.

Lifecycle, retraction and an actual owner-issued BREACHED fact may legitimately retain priority. A price-derived breach needs an explicit qualified quote/basis decision. Current native quote read rejects stale/native-basis problems, but the independent geometry relation remains UNKNOWN in the runtime composer. Once geometry is introduced, this precedence must not convert incomparable numbers into a confident invalidation.

**Discriminating acceptance:** pair valid lifecycle with price below invalidation but stale quote or unknown/ambiguous geometry basis; obtain the owner-policy-defined unavailable result rather than an unsupported price-derived breach. Then prove that an actual retraction/lifecycle termination/qualified BREACHED fact remains visible. This does not make optional structural UNKNOWN a blanket blocker.

## Owner composition and consistency

The current same-read helper returns a closed prophet.b4.same_read/v1 result with state, availability, b3_projection_id, episode_id, binding, owner_read_schema, nbbo_quality, unavailable_reasons and receipts. It internally builds exactly one native B3 result, consumes verified_pair(), reads native B4 inputs for the same source relation, checks binding, and reattests quotes_full and prophet_live bytes.

The Today producer independently builds B3, then passes entry_availability=None, plan=None, evidence=None, assembly=None, quote=None into compose_daily_brief. Its final status is PARTIAL / DAILY_BRIEF_OWNER_INPUTS_UNAVAILABLE.

**Integration requirement:** evolve the existing owner-gathering seam to make one detached, verified request-local result available to both B4 and presentation. Keep the current public schema closed or version it deliberately. Do not accept a caller's prevalidated flag, raw reconstructed B3 JSON or loose receipt as native proof. Do not duplicate B3 just to satisfy two call sites. Preserve every final generation/source/owner-byte guard before publishing the complete view.

Consistency invariants:

- Source SHA/pair/selection and B1 generation remain fixed for one read. A changed source, UCV inventory/receipt, B1 HEAD/generation, quote owner bytes or relevant identity projection refuses the assembled mixed read.
- A correction or withdrawal invalidates the affected current view and any derived aggregate keyed to it. Retained original evidence remains visibly dated; no in-place rewriting of original Plan facts.
- A previous accepted view is read-only fallback, never current readiness. Daily Brief currently permits fallback only when previous.identity equals current.identity exactly.
- Latest quote and B4 quote clocks remain distinct. The compositor accepts a genuinely newer quote without recomputing B4; it refuses an older latest quote or same-time price/basis contradiction. Therefore a newer quote cannot renew an old assessment, original Plan or entry decision.
- Native B4 receipt binds quote file, live artifact, disclosed freshness policy, identity and read clocks. NBBO quality is evidence-only here and cannot stand in for the incumbent liquidity/fillability gate.
- HTTP status, outer read status, per-row status, same-read envelope state, B4 state, scientific qualification and presentation health are different fields. Keep each visible at its proper layer.

## Performance and cache sequencing

Main native B1 integrity owner hashes every actual generation file on attestation and fully validates semantic payload on snapshot load. Native B3 currently repeats full disk/semantic validation and canonical equality for each selected binding. The Today producer surrounds the aggregate with initial/final source and B1 guards.

B03 already has _AttestedRelationCache: one immutable minimal relation index, at most 4 MiB; key is resolved root + full byte attestation token + source receipt. It re-reads all B1 bytes on every reuse. Cold reads fully validate and reattest after derivation; any failure clears the entry. This is an established derivative cache, not trust in an mtime or HEAD alone.

Current candidate PR source:

| Candidate | Exact inspected behavior | Scope that remains unproven |
| --- | --- | --- |
| #9369 at 858e11a4d17f2d9387af720d01c6d84dcc80b49d | engine/prophet_candidate_state.py::build_native_factual_assessment_results(snapshot, bindings=tuple(...)) fully validates at entry/exit, detaches native data, indexes TURN WATCH once, returns ordered NativeFactualAssessmentResult or None per binding. Generation-wide failure returns no partial batch. | Still explicitly O(bindings × generation rows) for projection; no cross-request cache, no sublinear claim, no merged/installed/latency claim. |
| #10824 at 0a5fdea7148065ea5d14d099a439308bd2cddcec | engine/us_context_vector.py::read_today_candidate_source_rows adds market_session to each incumbent intake read. engine/us_candidate_episode_intake.py::_records_snapshot reads bytes and pd.read_parquet first, then filters canonical session before wide to_dict/normalization. | Every part is still fully read, decoded and receipted. No bounded total bytes, endpoint p95, peak RSS or concurrent-request proof follows from reduced row expansion. |

Daily Brief API uses nonblocking BoundedSemaphore(1) per API process. An overlap returns 503. This limits overlap within one process; it does not cap one read's memory or all deployment processes.

**Acceptance should exercise the actual signed-in endpoint and ordinary page refresh** with representative retained history, cold/warm native state, and actual selected population. Measure latency distribution, peak memory and concurrency/refusal behavior, plus B1/UCV read/validation counts. Keep native byte-corruption/change detection intact. Do not declare production performance from a helper benchmark or an old PR-body head. Resolve the known O(bindings × generation rows) cost only if measured budget requires it, through an incumbent validated index or generation projection; never introduce a trust-cache shortcut.

## Discriminating real-consumer acceptance set

| Case | Required observation at API and UI |
| --- | --- |
| Mixed-generation Today read | Move source selection or B1 generation between captured input and final guard. No mixed cards, counts or entry result escapes; explicit current failure while permitted dated research fallback remains marked. |
| Correction or retraction | Same security, different source receipt cannot silently replace the selected occurrence. Original Plan provenance stays inspectable; current withdrawal/retraction and downstream aggregate effects are explicit. |
| Unresolved/cap-displaced observation | Exact search finds the full entitled observation before pagination; episode remains null with reason, rank remains null where absent, source/matched counts are correct. |
| Cross-page snapshot change | A changed alias, source receipt or B1 relation invalidates the retained snapshot cursor. No duplicate/omitted rows from mixing old and new pages. |
| Qualified B4 path | One actual request-local native B3/quote/geometry/gate chain reaches the real consumer under accepted strategy/policy, with correct owner state and clocks. Missing facts remain typed unavailable. |
| Clock conflict | Stable earlier live pass plus later B3 assembly follows the explicitly chosen current/historical evaluation contract, with no forged timestamp; fractional-second boundary behaves correctly. |
| Numeric breach uncertainty | Price below invalidation with stale or incomparable basis cannot manufacture a price-derived breach; authoritative lifecycle/retraction/BREACHED still retains its intended priority. |
| Exact original Plan | Two same-ticker selections/occurrences and later terminal episode return the right original Plan/source relation. Current eligibility remains separately unavailable unless its own owner qualifies it. |
| Latest quote and old assessment | Quote refresh changes only quote fields. Assessment, original Plan, management and B4 clocks remain their own; neither CURRENT quote nor outer HTTP 200 turns them current. |
| U34 aggregate | Page size/order cannot change totals. State counts bind one evaluated population, filter set, strategy/horizon/role and generation. Same-read EVALUATED, nested B4 UNAVAILABLE_DATA and a missing evaluation stay distinct; no page tally is presented as full-population readiness. |
| Entitlement | Unauthenticated/insufficient user is refused before private owner reads. Private source/Plan/quote fields do not leak through public index, error body or cache. |
| Performance under real consumption | Ordinary signed-in refresh stays inside the explicitly approved latency/memory/concurrency budgets while corrupt/changed bytes still refuse. No benchmark-only acceptance. |

## Pinned source references

All main-source links below use the fresh pin, not mutable main:

- [B1 episode identity and integrity owner](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/us_candidate_episode.py): episode_id, _row_from_open, validate_candidate_episode_generation, attest_candidate_episode_store_bytes, load_candidate_episode_store_snapshot.
- [B3 native factual owner](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_candidate_state.py): NativeFactualAssessmentResult, build_native_factual_assessment_result, _row.
- [B4 deterministic evaluator](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_entry_availability.py): evaluate_entry_availability, validate_entry_availability.
- [Native B4 owner readers and composer](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_entry_availability_sources.py): read_native_b4_owner_inputs, compose_runtime_owner_facts.
- [Existing same-read join](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_b4_same_read.py): evaluate_same_read_entry_availability.
- [Today native producer and original-source relation core](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/scripts/build_stock_library.py): today_selection_source_binding, _today_native_source_candidates, _read_original_selection_native_relation, read_today_candidate_projection.
- [Daily Brief pure compositor](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_daily_brief.py): compose_daily_brief, _quote_owner, _plan_presentation.
- [Daily Brief HTTP transport](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/app/prophet_daily_brief.py).
- [Original Plan source owner](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/scripts/build_prophet.py): read_plan_candidate_source.
- [B03 projection/query/cache](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_early_observations.py): _AttestedRelationCache, load_observations, query_observations.
- [B03 HTTP transport](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/app/prophet_observations.py).
- [Strategy definition and governed catalog](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/engine/prophet_strategy_definition.py).
- [#9369 exact candidate native batch](https://github.com/mastermindx-market-intelligence/macro/blob/858e11a4d17f2d9387af720d01c6d84dcc80b49d/engine/prophet_candidate_state.py).
- [#10824 exact candidate source reader](https://github.com/mastermindx-market-intelligence/macro/blob/0a5fdea7148065ea5d14d099a439308bd2cddcec/engine/us_context_vector.py) and [intake](https://github.com/mastermindx-market-intelligence/macro/blob/0a5fdea7148065ea5d14d099a439308bd2cddcec/engine/us_candidate_episode_intake.py).

Metadata received from root (not reinterpreted as approval): #8004 open non-Draft 9f66ea9f4dbd9f9f894a9e8be4ebf9f5030433bc; #10176 Draft 228c25d37617a7217c8f65f1613ade701a2fe01a; #10509 Draft a40a1c5dfde7bae01e4bc852c182a0d230f048be with unresolved conflicts/review; #10202 Draft/HOLD e0c522c968e0f8367e0c313b9b39ef8fa2c9ff3a; #10824 open non-Draft 0a5fdea7148065ea5d14d099a439308bd2cddcec; #9369 Draft 858e11a4d17f2d9387af720d01c6d84dcc80b49d. No merge, installed acceptance, or approval carries forward from those labels.

