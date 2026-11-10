# Prophet Turn 4 - final owner contracts

**Version 4.0. Frozen implementation specification, 9 November 2026 (America/Vancouver).** Existing source behavior, candidate code and proposed extensions are distinguished below. These specifications create no runtime owner, admission, registration, promotion or installed proof. They amend the retained Turn 3 contracts where more specific; original B/Q/D/R obligations and current governing law remain.

## A. Backend and source composition


**State:** PROPOSED_IMPLEMENTATION_CONTRACTS, not installed source, runtime acceptance, scientific promotion or approval. Frozen 9 November 2026 (America/Vancouver; source reads 10 November UTC) for the Fable commission. Governing Mastermind pin 3652d8907df1738de551dd3032b42aa2a2acb482 remains reused.

## 1. Bounded source refresh

Fresh Macro main is **cae8e01be6ada447c11a6e77c4a46cab2abb69d2**. All twelve previously inspected backend blobs are unchanged from Turn 3 main 9a13c64bf69f782332afa29efb09fe48ee30b857:

| Path | Unchanged Git blob |
| --- | --- |
| engine/prophet_candidate_state.py | 3c56c45fa6e9d0fa1d3ec15f2759ab07e27de852 |
| engine/prophet_entry_availability.py | d49899fa4a3fbb201fc0161b3df3b933c1f075f9 |
| engine/prophet_entry_availability_sources.py | d874affad89886955a25e371680cde50875e6d4d |
| engine/prophet_b4_same_read.py | 86ed30742e17f4da382fe1eed0fe1f350169c6e9 |
| engine/prophet_daily_brief.py | 0c560dda74c8df951ed093ae52747eb28a4097a9 |
| engine/prophet_early_observations.py | 5c7a62b98461dfc10fd364ab18ddf0a3d037956d |
| engine/prophet_strategy_definition.py | 737401daaf29cae2ed26559703a283eeec5bd2b4 |
| engine/us_candidate_episode.py | c2821b4d95e0f116a4bb9db16acdf41c819ce038 |
| scripts/build_stock_library.py | a911a4f000a4caf79d7f9069fe0904f9d4215a3c |
| scripts/build_prophet.py | f62564d44cf349f42abf96b870208b9570e9f6e2 |
| app/prophet_daily_brief.py | a9d223dff1e88a8ac573d3765f8c1642b7d8090e |
| app/prophet_observations.py | 36607175e852440981b3c5b7aa8cb2ad696d4987 |

Direct file SHA checks establish this equality. The broad compare returned its 300-file ceiling, so absence from that list was not treated as proof.

All five candidate heads also remain unchanged and unmerged: #9369 Draft 858e11a4d17f2d9387af720d01c6d84dcc80b49d; #10824 non-Draft 0a5fdea7148065ea5d14d099a439308bd2cddcec; #10176 Draft 228c25d37617a7217c8f65f1613ade701a2fe01a; #10509 Draft a40a1c5dfde7bae01e4bc852c182a0d230f048be; #10202 Draft/HOLD e0c522c968e0f8367e0c313b9b39ef8fa2c9ff3a. Prior exact source reasoning remains usable; none is approval or installed proof. Reconcile accepted #10824 source before integrating #9369 on its original carrier; do not create a second batch implementation.

Additional decisive source reads:

- D5 intelligence_vector blob d4705503a0dfbdcb6b9435382b79fa4c0a69303d is unchanged. Its original cut is exact episode opened_at = max(anchor.time, original OPENED known_at).
- Entry-policy owner blob 0995aba2dc3f3fe0660d5351068d357c73bd511c already supplies session, risk, liquidity and gap/velocity functions.
- entry_signal blob 42f2e8b0069cccb82282ac66fea8ba0c72e42d3c uses a close-to-close volatility proxy and a 2%-of-spot fallback; neither is silently admitted as measured true-range ATR.
- Canonical indicator owners: entry_radar/indicator_core blob 0deb8a8623e095773607671948e112e0a18d4258; stock_technicals blob ca33b18252eb5f08feb5646e0fb904039d80629b.

Correct two registry symbol names during integration: actual names are **read_native_b4_owner_inputs** and **compose_runtime_owner_facts**, not read_native_entry_availability_inputs or compose_runtime_entry_availability_facts.

## 2. Freeze decisions

| Topic | Chosen design |
| --- | --- |
| One bundle | A private immutable request-local result, constructed and sealed by the existing native gathering seam. One native factual result per source binding is shared by B4 and presentation. No HTTP trust token, persistent bundle cache or caller prevalidation flag. |
| Current evaluation | Evaluate at a real microsecond UTC instant sampled after required inputs are captured; preserve the earlier market pass and B3 assembly. Recheck expiration at response completion without moving the decision timestamp. |
| Original D5 | Keep the original episode cut and original receipt membership unchanged. Current entry and any later assessment are separate claims; passing now as a replacement D5 cut is prohibited. |
| Terms | A versioned policy-specific projection with AVAILABLE, NOT_PROVIDED, NOT_APPLICABLE and UNAVAILABLE distinctions. No independent stop or expiry is invented to fill the Paper specimen. |
| Population | Exact native population scope, three-valued filter results, source snapshot distinct from per-request read identity, complete denominators and explicit evaluation coverage. No first-page aggregate. |
| Plan relation | Extend the existing private Plan index with reverse original-source references and verify every proposed exact match with read_plan_candidate_source. Related-security and current management remain independent. |
| Compatibility | Preserve closed v1 readers and schemas. Implement explicit v2 projections/routes for changed semantics; do not silently reinterpret existing v1 fields. |

The interface names below are **proposals** within the existing owners. They are not claims that new fields already exist.

## 3. P1/P3 internal interface: one sealed native read

Place the proposed private type **NativeProphetReadBundle** and factory **read_native_prophet_bundle** in engine/prophet_b4_same_read.py. Refactor the existing helper around it rather than introducing another service.

Factory inputs are trusted server configuration and exact source bindings: captured selection identity, ordered native source-event/receipt pairs, configured native roots, accepted strategy-definition references, and requested component scope. No URL parameter supplies a filesystem path, snapshot object, caller-defined policy, arbitrary evaluation timestamp or trusted-owner flag.

The private type carries:

| Field | Proposed type / meaning |
| --- | --- |
| selection_binding | Existing source_sha256, pair_id, selection_receipt, market_session and ordered original row receipts |
| generation_binding | Canonical B1 generation plus actual native byte token; identity source receipts |
| rows | Ordered immutable tuple of NativeProphetRowRead |
| captured_owner_versions | Fixed owner file/revision digests and policy identities; internal paths never enter public output |
| read_started_at | Actual UTC instant |
| evaluation_asof | Actual UTC instant after input capture, or null when no evaluation was possible |
| read_completed_at | Actual UTC instant after final guards |
| consistency | SEALED or REFUSED with exact reason; only SEALED rows may be returned |
| read_id | Digest of this complete read, including clocks; a presentation identity, never a proof token accepted from a caller |

Each NativeProphetRowRead contains the exact occurrence, nullable episode relation, the native NativeFactualAssessmentResult when available, the qualified native quote result, geometry/metric/gate owner results, original D5 output, Plan relation, current evaluation envelope and typed component refusals. Construction freezes nested data; consumers receive detached revalidated copies. A frozen dataclass containing mutable dictionaries alone is insufficient.

**Execution sequence**

1. Authenticate and establish entitlement before private owner I/O. Capture and validate exact selection bytes, source inventory, identity references and one B1 generation.
2. Split the existing private Today resolver into source-relation resolution and native factual gathering without changing its selection, ordinals, retraction/suppression rules or original Plan behavior.
3. Invoke the existing native factual owner once for the ordered bindings. Integrate #9369's bounded plural entry/exit validation after its dependency is accepted; until then the same incumbent singular owner may be invoked once per binding inside the gatherer. B4 and presentation consume the same returned pair, never separate B3 reconstructions.
4. Capture quote/live, geometry, metric and gate material through existing native owners. Shared file capture can be batched privately inside engine/prophet_entry_availability_sources.py, retaining per-binding validation and final native reattestation. No public prevalidated argument.
5. Sample the genuine evaluation instant; qualify and evaluate current facts as specified below.
6. Reattest captured source, generation, identity and applicable owner bytes. A generation-wide integrity change returns no partial native batch. A row-specific absent fact remains an ordered typed unavailable row. Failed serialization must never leak internal material.
7. Seal, then compose the public view from detached owner outputs. Final response age qualification may withhold current entry even when an earlier deterministic row exists.

The existing pure Daily Brief compositor remains I/O-free. The Today producer remains the selector. B1 remains the lifecycle writer. The bundle neither publishes owner facts nor authorizes ranking, sizing, orders or retries.

## 4. Exact time and evaluation rules

### Current B4

For each coherent batch, sample **evaluation_asof = actual UTC now** after all required captured input clocks and B3 assembly are available. Do not compute max(now, a future input); a future input is a refusal. Preserve microseconds internally and in RFC3339 output.

Change the runtime composer contract from live_pass_ts == decision_at to:

- live_pass_ts <= evaluation_asof;
- quote_observed_at <= live_pass_ts;
- the artifact's recorded quote age still agrees with quote_observed_at at its own pass;
- current freshness is separately recomputed at evaluation_asof using the artifact's disclosed policy;
- B3 assembly and source/owner-known clocks do not exceed evaluation_asof;
- source market session, quote session and the registered decision session remain compatible under the existing policy.

Run evaluate_session_eligibility at evaluation_asof. Bind current confluence validity, native NBBO, basis and other mandatory facts to the same instant. Retain live-pass, quote, B3 assembly, original source and final completion clocks separately.

**Response completion rule:** after evaluation and final byte guards, record read_completed_at and recheck time-sensitive qualification. If the quote, NBBO, source-validity window or session eligibility expired in transit, retain the original evaluated row as dated research but set current_qualification = STALE or UNAVAILABLE with its actual reason. Do not restamp the row or silently recalculate in a retry loop. A new explicit read is a new evaluation.

Proposed current-entry envelope, within prophet.b4.same_read/v2:

- evaluation_state: EVALUATED or NOT_EVALUATED.
- availability: prophet.entry_availability/v2 or null.
- evaluation_asof, read_completed_at, b3_assembled_at, live_pass_ts, quote_observed_at.
- current_qualification: CURRENT, STALE, UNAVAILABLE, or POLICY_NOT_QUALIFIED.
- qualification_reasons, native policy/scientific references and owner receipts.
- terms: prophet.entry_terms/v1.

The availability v2 retains existing native B4 states and common numeric fields but versions the changed temporal and invalidation semantics. EVALUATED means a row exists, not entry readiness. A control-only ENTRY_OPEN remains a control result; public live readiness requires the actual incumbent policy admission and current qualification. No new admission registry is created.

### Invalidation precedence

Choose this order:

1. Qualified canonical inactive lifecycle or exact retraction; independently qualified owner structural BREACHED.
2. Qualify the numeric quote and geometry identity, current freshness and basis relation.
3. Only then evaluate price <= invalidation_price.
4. Apply the remaining registered mandatory facts and deterministic policy ordering.

Unknown optional structural_invalidation remains non-blocking. Missing numeric invalidation remains unavailable under the current tactical contract. Do not turn absence of a confluence, liquidity, source-health or other mandatory fact into PASS.

### Original D5 and later assessments

The existing D5 builder and validator remain unchanged in P1/P3. Its opened_at must equal max(structural_anchor.time, original OPENED known_at). Source revision source_available_at, observed_at and workspace.generated_at must all be <= that original cut.

Expose unmodified D5 under a proposed **original_evidence** section carrying projection_id, original_episode_cut and its native revision/coverage states. A new retrieved_at belongs to the wrapper, not to D5 source clocks or decision version.

A later assessment, if its existing owner qualifies one, is a separate current_assessment with its own assessment_id, evidence_cutoff, model/policy version, source membership and issued_at, referencing the original occurrence. No later source is inserted into the original D5 decision version. Until qualified, current_assessment is unavailable with reason; this does not erase original research. The B4 current-time change is not a historical-replay API and does not authorize arbitrary client cuts.

## 5. Policy-specific terms and the metric adapter

Proposed **prophet.entry_terms/v1**, produced beside the B4 owner result:

- Exact episode/source and strategy_definition_id, strategy_version, horizon_role, entry_policy_version.
- owner_refs and source_receipts.
- entries for entry_zone, chase_boundary, policy_invalidation, separate_entry_stop, separate_structural_falsifier and validity_window.
- Each entry has state, typed value or null, semantic_kind, units, currency where monetary, price_basis, source_time, policy_ref and reason.
- State is AVAILABLE, NOT_PROVIDED, NOT_APPLICABLE, or UNAVAILABLE. NOT_APPLICABLE requires an explicit policy declaration; absence alone is NOT_PROVIDED or UNAVAILABLE.
- Values are projected from the qualified owner, not reconstructed from labels or percentages.

**Chosen mapping:** expose existing stop as the incumbent policy invalidation. Do not display it twice as two independently sourced stops. A distinct entry stop/structural falsifier is absent until its owner actually supplies that distinction. Publish actual numeric chase_above when qualified. Numeric terms must equal those consumed by B4.

The existing session-policy fact already provides session_open, session_close and half-open [open,close) semantics. Expose this as **session eligibility window**, not a guarantee that the decision stays valid through the close. A separate validity interval is published only if a native source/policy supplies it. Quote expiry, correction, changed owner generation and other mandatory gates can end current eligibility earlier. No invented all-day decision lease.

### Exact native metric choice

Use **engine.entry_radar.indicator_core.atr14_prior_confirmed**, which delegates to **engine.stock_technicals.atr**: Wilder ATR(14) over true range, at the prior confirmed session. The proposed metric receipt must bind:

- canonical security/listing, market and currency;
- actual OHLC source-byte receipt, price-adjustment basis and comparability receipt;
- bar/session calendar, latest included confirmed bar and evaluation session;
- exact method reference/version, ATR window and prior-confirmed shift;
- actual finite positive result and source/owner-known clocks.

Use matched prior-confirmed **same-basis OHLC** with real high, low and close. The current entry_signal._atr_pct is a close-to-close proxy, and assess can use 2% of spot; neither may silently satisfy this measured ATR contract. Missing low/high, incomplete bars, unknown basis, absent receipt, insufficient window, null/zero/nonfinite metric or an unavailable prior confirmed session means **UNAVAILABLE**, not a close-only/default fallback.

Align the method to the evaluation session D explicitly. When a native panel contains a D row, atr14_prior_confirmed at D supplies the value through D-1. When the qualified panel ends at the prior confirmed session, use the same canonical unshifted atr14 value at that final confirmed row and bind it as the D prior-confirmed value. Do not shift an already prior-only panel twice to D-2, invent D OHLC, or consume D's eventual range. The receipt records the actual last included session and this alignment.

Freeze the method reference in the versioned metric contract; do not copy the formula. Retain existing evaluate_risk_ceiling, evaluate_liquidity_fillability and evaluate_gap_velocity and their current numerical constants. Their CONTROL_ONLY/SHADOW_ONLY and uncalibrated threshold status remain explicit. This engineering choice does not promote those constants or create a size/capacity claim.

first_trigger_price must be the preserved price on the exact first-trigger owner event; anchor_price must be the exact qualified anchor price/basis. Neither is replaced with current spot or with the other merely to fill a required field. Preserve the current strict required-input behavior until a separately versioned policy explicitly changes it. Prospectively capture absent source facts through their existing producer; genuinely missing historical inputs stay unavailable.

## 6. Complete population and filter envelope

Use one proposed **prophet.population_slice/v1** data shape in existing projection contracts; it is not a universal population service. Keep these scopes distinct:

| Scope | Existing owner and proposed transport |
| --- | --- |
| EARLY_OBSERVATIONS | engine/prophet_early_observations.py; /api/prophet/observations/v2 |
| CANDIDATE_EPISODES | B1 snapshot + B3 projection through existing Prophet Lab owner; bounded /api/prophet/lab/v2/episodes |
| TODAY_SELECTION | Existing Today producer; /api/prophet/daily-brief/v2 |

CANDIDATE_EPISODES is the complete declared B1 generation with explicit lifecycle filter; it is not the complete observed universe. EARLY_OBSERVATIONS includes pre-B1 and cap-displaced source rows. TODAY_SELECTION preserves the publisher's original order. Do not add these totals or union their identities implicitly.

Required envelope:

| Field | Proposed meaning |
| --- | --- |
| population | scope, market, source families, source sessions, entitlement partition identifier, coverage and explicit supported capabilities |
| source_versions | Separate native board, Plan-index if used, B1, identity, classification and evaluated-owner version/receipt references |
| filters | Canonical echoed query; q/ticker/security, lifecycle, strategy IDs and entry-state selector; unsupported filter yields FILTER_UNAVAILABLE, not successful zero |
| population_snapshot_id | Digest of captured source versions, ordered occurrence keys, filter definition and applicable state-membership vector |
| read_id | This request's complete sealed read; changes with actual evaluation/assembly clocks |
| clocks | Source session(s), evaluation_asof where applicable, read_completed_at; original research cuts remain per object |
| counts | total entitled supported rows; known_match; known_nonmatch; unknown_match; returned |
| evaluation_counts | Explicit denominator_ref; evaluated count, not_evaluated count, counts for every native B4 state; current-qualified count separately nullable |
| page | offset, limit <=100, next_offset, snapshot expectation |
| rows | Ordered page of exact native occurrence/episode references with typed missingness |
| errors | Typed component/coverage reasons; no private paths or hidden-population counts |

All counts refer only to the entitled supported population. Authenticated access does not permit totals or facets revealing withheld rows.

**Filter rules:** ANY matches regardless of absent classification. A specific field predicate is MATCH, NO_MATCH or UNKNOWN. For AND, any known false gives NO_MATCH; otherwise any unknown gives UNKNOWN. A requested family must have actual owner-classified membership, not a catalog-derived routing guess. Exact entry-state filters use the recorded native evaluation for the specified strategy definition/horizon role; missing evaluation is UNKNOWN, not NOT_READY. A literal NOT_EVALUATED filter can explicitly select those rows. Unknown family/entry membership is counted separately; zero known matches with unknown_match >0 must not render “nothing matches” or “zero ready”.

Filtering covers the entire declared population before pagination. Stable ordering uses the native order, with source occurrence as deterministic tie-breaker; there is no new ranking model. A name/ticker text search is discovery, not identity joining. Exact security joins still require the canonical identity owner.

Evaluation counts declare their base filter without the entry-state predicate, so the ready count and other native-state counts have one comprehensible denominator. Sum(native_state_counts) = evaluated_count; evaluated_count + not_evaluated_count = the declared base population when coverage is complete. EVALUATED with UNAVAILABLE_DATA belongs in evaluated_count; an absent row does not. Public ready count is null with POLICY_NOT_QUALIFIED until live policy admission exists; a separate explicitly labelled control-state count may be displayed.

**Pagination choice:** exclude volatile assembly timestamps from population_snapshot_id. Include source changes and any current filter-state membership changes, including freshness/session expiry; those return 409 SNAPSHOT_CHANGED for a retained page. Every page is a new fully attested read with its own read_id and clocks. The UI replaces that page and its counts together, and does not claim multiple page responses are one atomic evaluation instant. Retained selection stores exact object references, not an old READY badge. This avoids an endless 409 solely because B3 assembly time changes, without adding a request-bundle cache or a TTL trust bypass.

If the native source cannot establish complete population integrity, return UNAVAILABLE, not partial rows pretending completeness. A valid population with per-object missing research/qualification can return PARTIAL and explicit unknown counts.

## 7. Original Plan adaptation and retention

Add a reverse original-source reference projection to the existing private Plan index in scripts/build_prophet.py. Key by full original source binding plus original ordinal/row receipt; values are plan_id and raw plan_sha256. Retain native index/board versions separately. This is an index projection, not a Plan writer or second store.

For every proposed exact target, invoke the incumbent **read_plan_candidate_source** with expected Plan SHA and, where appropriate, expected current B1 generation. Verify the returned source_origin/source_binding against the requested original occurrence. Preserve all returned clocks, native identity availability and episode lifecycle; do not fill a missing current native identity from a ticker or historic lifecycle object.

Proposed **prophet.daily_brief_plan_relation/v2** separates:

- exact_original: VERIFIED, NONE_PROVEN, or UNAVAILABLE, with zero-or-more verified original occurrence links.
- original_source_state: the actual BOUND/PENDING/SUPPRESSED/RETRACTED/AMBIGUOUS/UNAVAILABLE status.
- related_security_links: separately labelled links, never promoted to exact.
- target_access: accessible/withheld/unavailable, enforced by existing authorization.
- current_management: independent native result or UNAVAILABLE.
- current_action: remains UNAVAILABLE from this source-only reader.
- inventory_coverage and immutable original/source/Plan version references.

NONE_PROVEN requires a complete relevant owned Plan inventory and qualified origin coverage. Legacy Plans with missing source_origin cannot prove absence. A terminal/superseded exact original relation remains inspectable; it does not renew current entry. A retracted exact source occurrence stays explicitly retracted rather than disappearing or becoming a new same-ticker Plan.

**Retention decision:** reuse scripts/build_prophet.py::_freeze_origination_source_board and data/prophet/origination_sources/<raw-sha256>.json.gz for exact Today bytes already archived. It verifies raw-byte equality and refuses collisions/symlinks. Extend native publisher coverage prospectively before promising every durable Today evidence reference; do not cause a read request to archive or mutate.

B03's dated session file is not a revision archive. Extend its incumbent source publisher to retain immutable receipt-addressed prior versions under its existing private episode-input provenance root before publishing durable revision links. Missing retained bytes return SOURCE_VERSION_NOT_RETAINED. No read-time reconstruction or new personal research evidence store.

## 8. Compatibility, scopes and migration

| Surface | Frozen compatibility rule |
| --- | --- |
| Existing v1 Daily Brief/observations/Lab | Preserve closed schemas, query allowlists, status mapping and old consumers. No new enum silently inserted. |
| New v2 transports | Same authentication/private no-store owners; malformed/unknown/repeated query400; explicit expected source/generation/snapshot conflict409; unavailable owner or capacity503; usable AVAILABLE/PARTIAL200. v1 optional generation mismatch remains503. |
| B4 v2 | Version changed evaluation/price-precedence semantics. Keep original v1 result/capture readers available during migration; no relabelling historic v1 rows as v2 proof. |
| Plan relation v2 | Added exact original proof does not change Plan origination or current-management authority. |
| Internal bundle | Never serialized as a reusable authority token; no persistent cache/queue or new lifecycle. |
| Cutover | Capability negotiation/explicit version; strict decoders. Serve old/new consumers from their declared versions until installed source identities and ordinary-refresh proof reconcile. |
| Rollback | Restore prior presentation/reader version through existing flags. Preserve user memberships, original Plans, appended source history, revisions and uncertain effects. Never rewind history. |

**P1 owned path scope:** scripts/build_stock_library.py; engine/prophet_candidate_state.py; existing B1/intake/source-reader seams only as required by accepted #10824/#9369; engine/prophet_b4_same_read.py internal gathering shell; engine/prophet_daily_brief.py; app/prophet_daily_brief.py; engine/prophet_early_observations.py; app/prophet_observations.py; existing engine/prophet_lab contracts/response and app/prophet_lab.py for declared episode-query projection. Plan index/relation adaptation is a coordinated P1/P2 slice in scripts/build_prophet.py, not a concurrent independent rewrite.

**P3 owned path scope after P1 interface integration:** engine/prophet_entry_availability_sources.py; engine/prophet_entry_availability.py; engine/prophet_entry_policy.py; engine/prophet_b4_same_read.py; the bounded producer projection in scripts/build_stock_library.py and engine/entry_signal.py where native geometry lineage must be carried; existing metric/quote/basis/signal owners. Reuse entry_radar.indicator_core and stock_technicals, do not fork formulas. No changes to D5 original-cut semantics, detector selection, user persistence, experiment registry, source rights, entry constants or live admission as incidental work.

Declare shared-file sequencing in the work brief. Do not place P1 and P3 live writers on the same paths simultaneously. Reconcile #10176 withdrawal semantics, #10509 board/index epochs and #10202 publication/served-byte settlement on their incumbent carriers; their open source is not installed readiness. Pure implementation can proceed while the held publication/release action remains separately gated.

No new test framework. Add discriminating cases to the existing candidate/Today, B4/source/same-read, Daily Brief API/compositor, observations and Plan-clock/relation suites. Actual signed-in endpoint, memory/concurrency and ordinary-refresh proof remain owed. #9369 still has O(bindings × generation rows) work; #10824 still reads/decodes/hashes every part. Never claim measured endpoint SLOs from source or old fixture timings.

## 9. Packet falsifiers and reserved boundaries

P1 is falsified by duplicate B3 assembly for the same binding within a read; caller snapshot mutation affecting a sealed row; a generation-wide failure leaking partial batch results; page/count mixing; unknown-match reported as zero; same-ticker Plan substitution; or a historical evidence reference that silently resolves current bytes.

P3 is falsified by restamped live-pass/B3 times; D5 cut advanced to now; false future refusal on a still-fresh same-session earlier pass; stale/incomparable numeric invalidation; optional structural UNKNOWN blocking all results; close-only/default ATR masquerading as measured ATR; current-session eventual high/low leaking into prior-confirmed ATR; different price bases compared without owner proof; or a control result promoted to production Ready.

Test actual still-fresh prior-pass and fractional-second cases, genuine expiry during composition, half-day close, preserved qualified retraction/BREACHED priority, geometry/ATR receipt mismatch, same-source correction, withdrawn and ambiguous Plan relations, complete-versus-unknown zero-result filters, and exact-head API status bodies. Runtime and tests were not executed in this editorial round.

No additional Chairman engineering choice is required for these interfaces. Existing reserved boundaries remain: provider/source-rights expansion, scientific/policy promotion, actual release/security holds, held effects, user-presence/account controls and runtime admission. They are not excuses to leave the concrete authorized implementation undecided.

## Pinned source links

- [Native B3](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_candidate_state.py), [B4 same-read](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_b4_same_read.py), [native inputs](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_entry_availability_sources.py), [deterministic B4](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_entry_availability.py).
- [Today producer](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/scripts/build_stock_library.py), [Daily Brief compositor](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_daily_brief.py), [API](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/app/prophet_daily_brief.py).
- [Original D5 cut](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_lab/intelligence_vector.py), [existing Lab transport](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/app/prophet_lab.py).
- [Policy owner](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_entry_policy.py), [geometry and proxy implementation](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/entry_signal.py), [prior-confirmed ATR](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/entry_radar/indicator_core.py), [canonical true range/Wilder implementation](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/stock_technicals.py).
- [Observation population/cache](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_early_observations.py), [observation transport](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/app/prophet_observations.py), [Plan resolver and source archive](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/scripts/build_prophet.py).



## B. Experience and durable user intent


Source-bound application specification, frozen 9 November 2026 (America/Vancouver; source reads 10 November UTC). This document proposes bounded implementation contracts; it is not implementation, installed-schema evidence, release approval or dispatch. It supersedes the unresolved D05/application decisions in Turn 3, while preserving their acceptance and held effects.

## 1. Source boundary and material delta

Governing pin: `3652d8907df1738de551dd3032b42aa2a2acb482`, with current AGENTS.md and ChatGPT Web waiver. Macro main (M): `cae8e01be6ada447c11a6e77c4a46cab2abb69d2`. Terminal master (T): `90ab4ef7a4c15e023be7d1188c2bd278a61ff266`. Rich candidate (C), Macro #9495: `d42d83307948141c05967d7081a6cc7cbeb24a90`, still open Draft/HOLD. #10579 is also open Draft; its security restrictions and original uncertain/refused effects remain binding.

Direct blob comparison establishes that the WatchStore, B21 producer, preferences, drain, Terminal watchlist/annotation owner, observation BFF, decoder and hook used in Turn 3 are unchanged at these fresh pins. Preserve their existing proof; do not restart broad discovery. Terminal has added a shared-shell /prophet entry through merged #1244, but that route mounts the incumbent model-plan/options workspace. It does not establish that the new Today/Screener/Compare research workspace is shipped.

### Fresh source ledger

All links are source, not deployment or migration application receipts.

| Ref | Exact source | Blob SHA / decisive symbols |
|---|---|---|
| F01 | [M templates/watchstore.js](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/templates/watchstore.js) | `46e95da158fbe8120c9cb3b56d8e7bdff27bf9ab`; saveChecked, symbolInspect, cacheRead/cacheWrite, cacheClear, onAuthUser |
| F02 | [C templates/watchstore.js](https://github.com/mastermindx-market-intelligence/macro/blob/d42d83307948141c05967d7081a6cc7cbeb24a90/templates/watchstore.js); [C templates/prophet_save.js](https://github.com/mastermindx-market-intelligence/macro/blob/d42d83307948141c05967d7081a6cc7cbeb24a90/templates/prophet_save.js) | WatchStore `674f22768b57790e0e558b4d4c9cbe1b9a13a74a`; Save adapter `b8a982152be20efe3ec59421a611488158959c01`. checkedSession/accountScope are candidate additions. |
| F03 | [C templates/theme.js](https://github.com/mastermindx-market-intelligence/macro/blob/d42d83307948141c05967d7081a6cc7cbeb24a90/templates/theme.js) | `387293b4eb317ce9c848f5a3183c3842bd89ab9b`; study state, PVSetupReturn, sourceStamp, studyStamp |
| F04 | [T terminal/lib/investigationContracts.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/investigationContracts.ts); [investigations.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/investigations.ts) | `2060d5f8c92aa749ce1360a0dbd5c3a73bcf6e1f`; `536b971c2b8205fdc44e7e0529c34b83a41f5df3`. InvestigationManifest v2, INVESTIGATION_ADMISSION, parseInvestigationCommand, apply/read operation |
| F05 | [T terminal/lib/investigationSave.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/investigationSave.ts); [investigationJournal.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/investigationJournal.ts) | `a15205f61cb2ca00b0f084d4aee7a1e561d203c3`; `a8b615342e0fbd8ceaec1e2d24c85fd4dc81d36d`. Existing exact-command recovery and `mm.investigation.pending.v2:<owner>` |
| F06 | [T terminal/app/api/investigations/route.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/app/api/investigations/route.ts); [investigationApiAdmission.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/investigationApiAdmission.ts) | `df263ca7160c109ef70d302738b37ef9677cec93`; `6f8a93d5485e1615374f4fd12e3caf323bc0a6e9`. Existing REST owner; literal INVESTIGATION_API_ADMISSION=open required |
| F07 | [T supabase/migrations/0028_investigations.sql](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/supabase/migrations/0028_investigations.sql) | `84733ae4c7cdfc48f3ee13e2aacd3b5d963760af`. investigations, investigation_revisions, investigation_mutation_receipts; apply_investigation_revision_v2 |
| F08 | [T supabase/migrations/0042_investigation_scenario_reference.sql](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/supabase/migrations/0042_investigation_scenario_reference.sql); [0047_investigation_options_selection_evidence.sql](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/supabase/migrations/0047_investigation_options_selection_evidence.sql) | `f05c61020b26c9eab3e7bb8d56ad85307a15fc62`; `dbe2e4aa35613f79696b9c76e8d171e49f6aab7b`. Later validator shapes admit immutable thesis_refs; 0047 is source-marked UNAPPLIED and pins its predecessor |
| F09 | [T terminal/lib/theses.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/theses.ts); [terminal/app/api/theses/route.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/app/api/theses/route.ts) | `eb539804e0a7db91b60ef0b61e3905137d8628ff`; `421f9ea972fd7956d30190f15dbd9fe23e642694`. Existing F11 ThesisContent, ThesisVersion, applyThesisVersion |
| F10 | [T supabase/migrations/0012_thesis_objects.sql](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/supabase/migrations/0012_thesis_objects.sql); [terminal/components/workspaces/ThesisWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/components/workspaces/ThesisWorkspace.tsx) | `906c1d40a04ce277ff2874f321bc3f005179d883`; `4b0150e77f77833d5adf16deb7d81d80f576e422`. theses/thesis_versions; unique(user_id,client_request_id); existing `mm.thesis.pending.v2:<owner>:<clientRequestId>` |
| F11 | [T terminal/lib/watchlistAnnotations.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/watchlistAnnotations.ts); [terminal/lib/watchlists.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/watchlists.ts) | `bf9d1562f9e2d57024619c51558c2c5ff58a875d`; `4b4832866251f142ffc682fc3c051478bb0bf138`. Mutable per-field CAS annotations versus security membership |
| F12 | [T supabase/migrations/0034_api_watchlist_write.sql](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/supabase/migrations/0034_api_watchlist_write.sql); [terminal/lib/apiV1WatchlistWrite.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/lib/apiV1WatchlistWrite.ts) | `3432351bfad05207835d9e118fa0d5896078f71c`; `c18846191669352f337f4caa54994532b265c7ba`. API-key-scoped api_v1_write_receipts and service-role-only api_v1_add_watchlist_symbol |
| F13 | [T terminal/app/(shell)/prophet/page.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/app/(shell)/prophet/page.tsx); [IntelligenceToolWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/components/intelligence/IntelligenceToolWorkspace.tsx) | `beb743e8910c90abf355900c6de8e288c15ed9d2`; `b370be454e82cb07f9ecae6bd2155a188341dd11`. Shared-shell route; Session, useReadingScope, ProphetLanesView |
| F14 | [T terminal/components/mounts/IntelligenceToolMount.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/components/mounts/IntelligenceToolMount.tsx); [terminal/components/TerminalShell.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/components/TerminalShell.tsx) | `0e19ce9467b942da847097feacd96968b017a945`; `d4f8256fced1041dc89f8d4632743588735c1db5`. Existing route/mount and old-shell integration; no second router |
| F15 | [M engine/prophet_journey_notifications.py](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_journey_notifications.py); [lib/user_prefs.py](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/lib/user_prefs.py) | `3a2857595d644c2f6f6a101fd01da1ac1e24475c`; `f29e7782db31d95560ed87862df3e1cda34d9ce6`. Existing pure B21/email event producer; category currently absent from prefs |
| F16 | [M engine/alert_delivery_drain.py](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/alert_delivery_drain.py); [T supabase/migrations/0013_alert_runs_outbox.sql](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/supabase/migrations/0013_alert_runs_outbox.sql); [T terminal/app/api/alerts/receipts/route.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/90ab4ef7a4c15e023be7d1188c2bd278a61ff266/terminal/app/api/alerts/receipts/route.ts) | `fe8e51a7fc720131048159859ec4aabe49d2875e`; `28a7f72af5726fb04bb9ef1bef1684564cdddf64`; `b3eb6687b9387a0fb2928af46617bac4e2503f88`. Existing outbox, unique fire_event_id, email-filtered drain, owner receipt reader |

## 2. D05 decision: three existing objects, distinct promises

| User action | Canonical owner and exact existing fields | Frozen behavior |
|---|---|---|
| Save security | WatchStore / watchlists + watchlist_symbols | Membership in an explicit owned list. No dated thesis, alert, model plan or holding is implied. |
| Edit note / flag | watchlistAnnotations, independent field revision CAS | Mutable user annotation. Do not insert source/model facts or immutable research history into the note. |
| Save dated investigation / Pass / milestone | investigations + investigation_revisions + existing mutation receipts | A versioned research container with exact pinned evidence references and explicit user intent. |
| Author thesis | F11 theses + immutable thesis_versions | Existing ThesisContent statement/catalysts/falsifiers/risks/horizon/effectiveAt/revisionNote; linked by immutable version, never duplicated into WatchStore or Investigation JSON. |

### 2.1 Exact proposed extension

Keep the existing REST /api/investigations command, IDs, expected_revision CAS and operation_id. Add `investigation_manifest.v3` as a backward-compatible *read* extension; preserve v1/v2 readers and all later scenario/options validation. V3 has the v2 fields plus a closed optional `user_decision` object:

- `disposition: "investigate" | "watch" | "pass"`.
- `reason: string`, max 2,000 characters; nonempty for Pass.
- `decided_at: RFC3339 string`, explicitly a user-declared decision time.
- `milestones: []`, at most 20 items, each `{id, criterion, due_on, state, user_observed_at, supporting_evidence_indexes}`.
- Milestone id is a UUID stable across revisions of that investigation; criterion is 1–500 characters; due_on is a valid date or null; state is `open | met | missed | withdrawn`; user_observed_at is a valid timestamp or null and required for met/missed; supporting_evidence_indexes are unique bounded indices into that same revision's pinned evidence_refs.
- No scheduler, monitoring rule or automatic outcome is created by a milestone. A user-marked milestone is labelled as such. Watch is a research disposition, not Follow enrollment or a portfolio holding.

Use existing `intent.title/question/subjects/horizon/research_as_of` for the research question and as-of date. Keep `continuation.next_question/next_observation` as the next human research step. Keep `review.assessment` as confirmed/contradicted/inconclusive review of the baseline; do not overload it to mean Pass.

The existing `committed_at` is the authoritative system record clock. A user-entered decided_at, Thesis effectiveAt or research_as_of is never evidence that source facts were available then. Corrections append a new Investigation revision and, when user thesis text changes, a new Thesis version. Prior content, source references and timestamps remain intact.

### 2.2 Thesis binding, recovery and account fence

The v2 shape already includes `thesis_refs[{thesis_id,version_id,role}]`, where role is primary/alternative/context. Current TS parseInvestigationCommand rejects any nonempty refs. The original 0028 validator also did so, but later 0039/0040/0042/0047 source validators admit the immutable ref shape. Do not claim the latest SQL schema lacks that shape. What remains missing from the examined owner path is integrated TS admission and a transactional same-account join to the exact thesis_versions row.

Add the same-owner, exact thesis_id/version_id check inside the existing apply_investigation_revision_v2 transaction before its first canonical write. Reuse existing tables and operation receipt. Unknown/foreign/mismatched versions return reference_unavailable without exposing another user's record. Do not resolve a version_id to the thesis's current head. Existing snapshot revisions remain valid when a thesis advances, is archived or is invalidated; their UI labels the dated version and current lifecycle separately.

A combined user journey performs two existing owner operations: first create/revise the Thesis; then, after canonical readback of the returned thesis/version (including immutable version UUID), attach it in an Investigation revision. The Thesis POST response currently returns thesisId/version/lifecycleState/replayed, not the immutable version UUID. Read the canonical detail before attachment. If thesis commit succeeds but investigation attachment is uncertain, show “Thesis saved; investigation link unconfirmed.” Do not resubmit the thesis or claim atomic cross-owner save.

Use the existing F11 `mm.thesis.pending.v2:<owner>:<clientRequestId>` journal and exact request replay protocol for Thesis operations. Use `mm.investigation.pending.v2:<owner>` plus existing operation read for Investigation. Receipt misses remain inconclusive; exact same-key replay is lawful only because those owners already define a transactional idempotency contract. Never transpose that replay permission to WatchStore membership.

The current scenario Investigation path carries x-mm-scenario-owner, while the general Investigation and Thesis route examined do not enforce an equivalent expected-account header. The D05 cutover must add an expected immutable auth-UUID header to these existing mutation consumers/handlers, compare it with authenticated getUser before any source preflight/RPC, and reject mismatch. This is an intent fence within existing auth, not another auth system. Update ThesisWorkspace and the D05 consumer together; do not enable new D05 writes until the participating clients and server enforce it. Signout/account replacement invalidates UI immediately and preserves the old account's original recovery envelope without displaying it under the new account.

### 2.3 Pinned Prophet evidence adapter

Add a qualified Prophet evidence adapter to the existing INVESTIGATION_ADMISSION and native server preflight. Proposed namespace is `prophet.research`, with closed object types `today_selection`, `b03_occurrence`, `plan_origin`, `evaluation`. These are reference adapters to existing native owners, not a new episode, source or lifecycle authority.

Each stored evidence_ref remains the existing shape `{owner,object_type,object_id,mode:"pinned",version_ref,fingerprint}`; native readers issue and resolve object_id/version_ref. The owner must bind the complete native listing/occurrence/generation/receipt tuple before returning this compact reference. Do not invent an object_id from a ticker or encode a current session filename as an immutable version.

Backend lane verified scripts/build_prophet.py::_freeze_origination_source_board retains exact us_standouts bytes at `data/prophet/origination_sources/<raw_sha256>.json.gz`, and read_plan_candidate_source verifies source_binding plus original ordinal/receipt. Reuse that archive where exact bytes exist and extend native publisher retention coverage prospectively. It does not prove every Today version was retained. B03's examined lineage is CURRENT_RECEIPT_ONLY; a session-named file is not revision retention. Until the native owner retains and resolves that exact revision, return SOURCE_VERSION_NOT_RETAINED and withhold the dated-evidence save capability for that reference.

For the proposed evaluation object type, enable pinned saving only when an existing native evaluation/capture owner has retained the exact immutable result and can resolve its version and rights. A NativeProphetReadBundle, per-request read_id or digest alone is not durable evaluation evidence. Without native retention, return SOURCE_VERSION_NOT_RETAINED and withhold this evidence-save capability. Do not add a bundle store or archive during a read.

Save-time and read-time native rights/source checks are both required. A hash is integrity, not entitlement. The private source payload stays with its native owner; the Investigation stores references and user-authored text. Revocation can make an old reference unavailable while the user's research record remains. Source correction never automatically changes the user's thesis or silently rebinds a pinned reference.

### 2.4 Compatible migration and release order

1. Add reader/parser support for v3 and explicit unsupported-schema display; preserve v1/v2, scenario and options refs. Keep new writes closed.
2. Reserve an additive migration at the existing Terminal migration owner. Verify the actual installed predecessor/function digest and grants first; do not assume source-marked 0042/0047 is installed or overwrite the validator with 0028.
3. Extend the existing validator, same-owner ref validation and capability readback; retain tables, operation lock order, receipt replay and revision CAS. Existing RPC names can continue with schema-discriminated manifests.
4. Qualify source retention/admission and account-bound readback, then enable v3 writes through the existing admission/capability seam. INVESTIGATION_API_ADMISSION must independently be open.
5. Rollback disables v3 creation but retains a reader capable of displaying already-created v3 records and their histories. No downcast, deletion or replay under a new operation ID.

## 3. U31 checked Save: reload-safe custody without invented reconciliation

### 3.1 Frozen interface and local extension

Keep `WatchStore.symbols.saveChecked(listId,[symbol],opts)` and `symbols.inspect(listId,symbol)`. Selectively integrate candidate checkedSession/accountScope/guardAccount/checked-only-host behavior with current main; copying prophet_save.js alone fails because main lacks checkedSession.

Add a versioned **non-executable recovery envelope inside the existing WatchStore persistence namespace**, alongside the per-list cache rather than inside its item blob. Proposed local key: `mdash.wl.<list_id>.checked_save.v1:<owner_uuid>`. This is client custody owned by WatchStore, not a canonical operation table, subscription store, worker or retry queue. Separate it from the legacy pendingPushes/pendingInserts/tombstones because old cacheRead whitelists fields and cacheWrite can drop unfamiliar metadata.

Envelope fields are `schema:"watchstore.checked_save_recovery/v1"`, owner_uuid, list_id, normalized_symbol, operation_id, immutable request parameters, created_at, phase, request_started_at, and a separately typed last_membership_observation. operation_id is a client correlation token, not a server idempotency key. Phase is prepared/request_started/uncertain/terminal_confirmed/terminal_refused. Store no access token, private research payload, thesis or executable retry command. Bound unresolved records; reaching the bound blocks a new checked mutation rather than evicting an old uncertain one.

Persist and exact-readback the envelope before the request can leave. Storage failure or ambiguous custody means zero write and an explicit unavailable result. A crash between recording request_started and network dispatch conservatively leaves uncertainty. Reload hydrates this owner state before enabling Save. The Save adapter consumes owner state rather than maintaining a separate authoritative unconfirmed array.

Use the browser's same-origin exclusive lock for the checked mutation/recovery envelope, keyed by immutable account; reread custody within the lock. Existing per-list in-process serialization remains. If the required exclusive-lock capability cannot be used, do not enable the new reload-safe write path; observation remains available. This is a bounded browser mutex, not a second scheduler. Preserve the incumbent conservative same-account/security hold across different destination lists while an earlier Save is unresolved; never re-home an uncertain insert to another list.

Normal membership refresh, list-cache cleanup and signout must not erase these unresolved envelopes. They remain hidden and inert until the original account is authenticated again. Unresolved records never expire into retry permission. Existing legacy outbox clearing remains unchanged for its own fields. No timer or storage event sends a write.

### 3.2 Reconciliation truth and limits

`inspect` always keeps writeRetryAllowed:false. Present membership can independently satisfy “in this list now”; it cannot attribute the earlier insert. Not-confirmed, an empty query, timeout, auth failure, deletion of a cache or absence of a client marker is not authoritative no-effect evidence. An original exact terminal response may settle the original operation; otherwise retain it as unresolved.

No current source-backed browser membership operation-status RPC was established. The existing API-key api_v1_write_receipts/API RPC is a different authenticated carrier; do not fabricate an API key or use service-role scope from the browser. The final contract therefore does **not** claim globally reconciled, cross-device operation history. Membership itself remains server-durable and cross-device. Client recovery is explicitly bounded to retained browser storage; ordinary reload must preserve it, clearing storage cannot prove outcome.

A new attempt is allowed only after an original owner terminal refusal/no-effect determination and a fresh deliberate user action, with a new correlation ID. Fresh membership inspection alone never creates that permission. The UI can finish the user's membership goal while still showing the old request's unresolved status; it must not trap “present now” behind a fabricated failure or erase uncertainty to make the screen green.

The database uniqueness owner remains Terminal 0009_watchlist_symbol_unique.sql / wls_watchlist_symbol(watchlist_id,symbol). Its presence in source is not installed-schema proof. Qualify that invariant before cross-client concurrency claims; correct the stale Macro comment without reapplying a migration by assumption.

## 4. Compare and Return: one typed reference, transient serialized view

The incumbent study/PVSetupReturn owner stays. Existing C compares 2–3 live cards within one grid and paints native DOM order; it does not yet implement retained off-filter comparisons or the complete B1 selection tuple on Return. The final extension has these exact rules:

- A selected reference carries native listing identity, occurrence identity and version/generation. For Today include source_sha256, pair_id, selection_receipt, original selection_index and row_receipt. For a B1 occurrence include the native event/episode identity and generation. For pre-admission B03 use the native source/row receipt; do not fabricate an episode. Include a native strategy/version ref only when supplied.
- Canonical equality is a schema-specific tuple of those existing owner values, serialized deterministically. It is a transport/cache key, not a newly minted universal Prophet identity. Missing required identity means unselectable/identity unavailable, never ticker-only fallback.
- `selectionOrder` is an ordered list of at most three exact references. Preserve it independently of native rank, displayed rank, filter membership and mobile visible-column order. Two occurrences of one listing can be distinct selections.
- Freeze a bounded `prophet.view_state/v1` under a namespaced `prophetView` key in the existing browser history.state. Merge other history-state keys. Store account UUID, source-surface kind, filters, presentation sort, grid/table mode, selected refs/order, open detail ref, semantic source/event/field selection, and a semantic focus target plus scroll offset. Do not store source payloads, authorization, arbitrary selectors or executable markup.
- The serialized state is transient view restoration, not durable saved research. Do not put its private tuple/filter state in a public URL. The existing route remains the route owner. Same-page navigation records origin before opening a destination; cross-origin navigation leaves recovery in the original origin's history and does not invent a transferable authorization token.
- On reload/back, reauthenticate the account, recheck entitlement and resolve exact references before showing private details or focus. Filtered-out selections remain selected with an explicit label. Replaced generations are marked unavailable/stale until the user explicitly chooses current research. Never substitute a same-ticker row.
- A dated return is possible only when the native retained revision resolves. Otherwise offer the current authorized research separately, preserving the distinction. No snapshot is synthesized from today's data.
- Restore exact control focus if still present; otherwise focus the appropriate section heading with a concise changed-state explanation. Plan resolution still happens before closing Setup, as in C. Exact Plan-origin relation uses read_plan_candidate_source; related-security links remain labelled as such.

The shared-shell /prophet route uses MMX_SHARED_SHELL, readShellMember and getLiveOptionsAccess. IntelligenceToolWorkspace keys Session by ownerKey/kind, uses useReadingScope and flowInvalidate, and mounts ProphetLanesView. Preserve that existing paid capability and account reset. Add qualified research presentation through the admitted existing workspace/mount when its data contract is ready; do not create a competing /prophet route, new entitlement tier or pretend the existing model-plan screen is the new research implementation.

## 5. B21: frozen capability ladder

### 5.1 P6 initial slice: existing email journey events

Complete the existing B21 IO/enrollment/preference/receipt chain. Initial supported kinds are exactly episode_terminal, emergence_triggered, corrected_material, retracted and superseded. Channel is email, category prophet_research_journey, designated list Prophet Research, tier essential. Preserve v1 logical event identity:

`prophet|kind|episode_id|from->to|b1_event_id|user_id`

Generation and definition era remain provenance, not dedupe identity. Replaying unchanged source must not produce another email.

Add the category to existing lib/user_prefs.py and its current account_prefs consumer. Reuse the existing producer/runner, alert_outbox, alert_runs, drain and mailer. No new subscription table, queue, scheduler or generic watcher. Existing price/RSI/regime/options conditions remain distinct explicit alert jobs; never relabel them as Prophet assessment Follow.

The initial Follow control lists these actual event families and explicitly offers email. It never auto-selects email to fulfill the Paper in-app specimen. Ordinary Save does not enroll Follow. Preference commit, exact designated-list membership, admitted producer availability and actual transport status are separate fields. Only show Following when the selected supported channel/category and membership readbacks are confirmed and the producer/delivery path is admitted; otherwise show configured/unavailable or the exact incomplete step. A settings HTTP ok alone is insufficient: verify metadata write and GET readback. A pending outbox row means queued; SMTP accepted is not recipient read.

### 5.2 Retained assessment-change slice

Extend the existing native assessment/B3 owner to emit a stable material transition reference over retained before/after accepted assessments, then extend B21's closed kinds with assessment_changed. Required transition payload is native episode/occurrence ref, before/after assessment refs, source cause/event ref, changed field set, effective/source-observed clocks, and correction link when applicable.

Only a declared material assessment field change qualifies. Read time, board generation, rank movement, ordinary quote/freshness updates and unchanged semantic state are excluded. Derive the new event ID from the native transition reference, retaining the existing user/episode dedupe pattern and leaving every v1 key unchanged. A new versioned B21 payload decoder must admit the new kind before enrollment advertises it. Absence of retained before/after source or native materiality contract keeps the capability unavailable.

### 5.3 Retained B4-change slice

Existing B4 issues the authoritative current-entry evaluation; B21 must consume its qualified native material transition. Require same episode/strategy/term version, retained prior/current evaluation receipt, from/to actionable availability, actual cause/ref and clocks. Compare semantic decision states, not poll timestamps or quote movement. Changes across strategy/terms become a newly labelled versioned assessment, not a fake within-version availability transition.

Extend B21 with entry_availability_changed only after the B4 owner has qualified and retained this transition. Apply existing not_after/current-rights/fact revalidation immediately before transport; obsolete availability is suppressed or explicitly corrected. An alert does not authorize entry or size a trade. This slice is dependent on P3/native evaluation and retention, not a blocker for honest initial P6 email.

### 5.4 Retained in-app slice: same outbox, separate acknowledgement

Keep one logical alert_outbox row per fire_event_id. Do not make a second notification table or duplicate per-channel event IDs. Add nullable in-app projection/acknowledgement fields to that owner, specifically `in_app_published_at` and `in_app_seen_at`, and an explicit `alert_inapp_optin` boolean in the existing preference owner. Existing email channel/status/delivered_at retain their email meaning.

At qualified event creation, the same producer can publish the in-app projection only for explicitly opted-in channel/category recipients. An in-app-only event's email transport remains suppressed with the actual email-opt-out reason; it must not send mail. The existing drain still selects channel=email and applies email eligibility. Serving the in-app projection rechecks current ownership, rights and event availability rather than treating published_at as a permanent access grant.

Extend the existing /api/alerts/receipts owner to return this projection and accept an owner-fenced, idempotent mark-seen action against the exact fire_event_id; SQL sets in_app_seen_at once for auth.uid()'s existing row and readback confirms it. Opening or rendering a list is not an acknowledgement unless the user invokes the stated acknowledgement action. No new operation receipt is needed for this set-once property. Persisted event availability, email sent and user acknowledged are distinct UI states. Corrections remain linked new events; a read marker never rewrites source history.

This is a concrete proposed additive extension, not existing capability. Qualify installed schema, independent channel preferences, owner/RLS isolation, dedupe, current rights, suppression, readback and correction before the UI says “Available in Alerts” or “Acknowledged.” The existing receipt monitor and two current health lanes alone do not establish this in-app feature or a healthy Prophet producer.

## 6. Bounded path scopes and P2/P6 order

| Slice / writer boundary | Exact owner paths and allowed scope | Dependency / non-overlap |
|---|---|---|
| P2-A membership + transient research interaction | Macro templates/watchstore.js, templates/prophet_save.js, templates/theme.js; necessary consumers in dashboard.html.j2, _us_board_cards.html.j2, _prophet_setup_detail.html.j2 | One owned integration diff against current main; retain C custody/hold. Owns checked Save/recovery and Compare/Return. P6 consumes its published interface and does not fork or concurrently rewrite it. |
| P2-B dated research + thesis link | Terminal lib/investigationContracts.ts, investigations.ts, investigationSave.ts, investigationJournal.ts, app/api/investigations/route.ts; existing lib/theses.ts, app/api/theses/route.ts, components/workspaces/ThesisWorkspace.tsx only where required for exact version binding/account fence; one reserved additive migration | One schema/transaction owner. Existing Thesis and Investigation journals remain separate. Native source retention/preflight is a declared P1/backend dependency. Install reader compatibility before v3 writes. |
| P2-C actual route integration | Terminal app/(shell)/prophet/page.tsx, components/mounts/IntelligenceToolMount.tsx, components/intelligence/IntelligenceToolWorkspace.tsx; existing ProphetLanesView/ProphetView and observation BFF/hook as needed | Preserve shared shell and incumbent plan/options views. No global navigation rewrite or duplicated auth/data provider. Source scope is the actual route, not a preview template. |
| P6-A initial Follow | Macro engine/prophet_journey_notifications.py, lib/user_prefs.py, app/account_prefs.py; existing IO/runner composition, scripts/drain_alert_outbox.py and engine/alert_delivery_drain.py only for qualified integration; Terminal existing alerts/receipts view | Starts after P2 checked membership interface freezes. Use existing WatchStore calls; no concurrent WatchStore or theme.js rewrite. Any shared consumer change is queued to P2's owner. |
| P6-B retained event kinds | Same B21 producer/decoder plus existing native assessment/B4 producer and retention reader | Independent explicit later packets; no UI-only event inference. B4 slice waits for P3 receipts. Preserve v1 dedupe and original email history. |
| P6-C in-app projection | Existing alert_outbox migration owner, preferences, current receipt route/Alerts UI and producer payload adapter | After initial chain proof. Same event row/owner; additive columns and set-once acknowledgement. No new queue/store. Coordinate migrations serially with P2-B; do not reserve the same number or overwrite an installed validator. |

Original C #9495 is integrated by exact owned resolution/selective adoption only after its specific custody/security/release controls permit. Neither this spec nor a green descendant CI clears #10579 or original uncertain effects. Final team commissioning still needs a real receiver/runtime: root's read-only session_targets returned []; T3 is currently the user-designated venue, not a verified running team. No dispatch was performed.

## 7. Discriminating acceptance and proof boundaries

### D05

- Create an Investigation v3 with exact retained Today evidence and an F11 immutable version. Reopen it after ordinary authenticated refresh and from a second session; server revision, thesis UUID and evidence fingerprint must match.
- Two edits with the same expected_revision produce one accepted revision and one version_conflict. Same operation_id/exact command returns the original receipt even after later head changes; different content under that ID is idempotency_conflict.
- Lost Thesis response recovers only through its original journal/key; a saved Thesis followed by an uncertain Investigation link remains a truthful partial success. Account A's pending request cannot execute or display under B.
- A future thesis revision, source correction and removed/unavailable evidence do not rewrite the saved earlier record. Pass and milestones remain user intent, never training outcome labels.
- Unretained B03 history, current-only file reuse, missing native rights, malformed reference, foreign thesis UUID and installed-validator mismatch fail closed. Source presence alone cannot pass the migration/capability gate.
- V1/v2, scenario/options refs and old exact pending envelopes remain readable through upgrade and rollback. No source-only 0047 assumption.

### Save

- Reload after request dispatch but before response preserves the exact unresolved account/list/security record and prevents another insert. Test timeout, malformed response, storage-full, crash-before-network and late response separately.
- Two tabs using the admitted bundle cannot produce two fresh checked attempts for the same held account/security. Stale account generation and logout disable write/readback claims before B's content renders.
- Inspect-present shows current membership with observed time while retaining original unknown attribution; inspect-not-confirmed cannot release the hold. A legitimate known-no-effect refusal can allow a later deliberate new request.
- Ordinary cache refresh, list deletion/cleanup and signout preserve unresolved custody; another account cannot see it. Legacy pendingInserts is never populated as recovery for this path.
- Membership persists in the exact selected owned list after ordinary refresh. No fallback to a default list and no claim that local recovery is a global cross-device operation ledger.

### Compare / Return / route

- Preserve selected order through filter, sort and grid/table change; a hidden selection is not silently removed. Compare different occurrences of one listing without collapsing them.
- A changed row receipt/generation cannot restore to a same-ticker substitute. Back/reload reauthorizes before revealing private content; stale detail returns to a meaningful heading.
- Exact Plan source relation and source-only absence are distinguished from related-security links. Failed Plan resolution leaves Setup/focus intact.
- /prophet maintains incumbent plan/options access, shell member states and owner reset; new research capability is admitted separately. Keyboard, mobile two-column selection, zoom and source-point focus return use real browser proof.

### Follow

- Explicit email/category opt-in plus exact Follow membership is read back; failed settings metadata write does not show Following.
- Unchanged generation/definition reread emits no duplicate. Suppressed/missing source, entitlement loss, quiet hours, stale not_after, correction of unsent/sent/unknown originals and transport ambiguity preserve their actual states.
- Initial UI has no general assessment/B4/in-app enabled promises. Later kind admission tests a real retained transition, no change for quote/read-time churn and current-entry revalidation.
- In-app-only opt-in creates no mail; email-only opt-in creates no in-app acknowledgement. One event row survives both channel views. Cross-account mark-seen fails; repeated exact mark-seen is stable; no “read” inference from SMTP or a painted list.

These are future acceptance obligations, not executed tests in this analysis. Production proof needs installed schema/function/grant receipts, admitted flags/runner, exact deployed bytes and a real authorized account journey after ordinary refresh.

## 8. Reserved boundaries

No canonical write, migration, account mutation, browser/Paper effect, production test, worker dispatch, held-effect inspection or reconciliation polling was executed. Original Paper 1EEH-0/1EF3 and ZE5 custody, F01 provisional custody, #9495/#10579 and final joint v1 unreleased status are unchanged. Root reports no operation-status capability in the original Paper catalog and an active document elsewhere; that does not authorize touching the held target. Native distinct review/release obligations apply only where the governing source actually requires them; this C3 document is advisory reasoning.

## 9. Exact candidate links

- [Macro #9495](https://github.com/mastermindx-market-intelligence/macro/pull/9495)
- [Macro #10579](https://github.com/mastermindx-market-intelligence/macro/pull/10579)
- [C templates/prophet_save.js](https://github.com/mastermindx-market-intelligence/macro/blob/d42d83307948141c05967d7081a6cc7cbeb24a90/templates/prophet_save.js)
- [T merged #1244 commit](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/67e2d515e4e92d2d05ea399f5691b7860fa07bbf)




## C. Intelligence, Record and qualification


## Decision and boundaries

Freeze the architecture and commission now. None of the remaining C3 questions needs another editorial turn. The remaining uncertainty concerns actual source availability, candidate integration, scientific results, runtime installation and consumer acceptance; those are implementation/research dependencies with explicit dispositions, not reasons to leave the product contract vague.

This C3 reasoning note creates no runtime entity, registration, experiment, admission, source mutation, outcome read, dispatch, promotion or approval. It uses Mastermind pin `3652d8907df1738de551dd3032b42aa2a2acb482`, Macro `cae8e01be6ada447c11a6e77c4a46cab2abb69d2`, Terminal `90ab4ef7a4c15e023be7d1188c2bd278a61ff266`, the saved masterplan v3, Turn3 contract registry and intelligence dossier. Proposed API names/enums below are a versioned consumer contract to implement through existing owners; they are not claims that the fields already exist.

## 1. Fresh source delta

All inspected scientific and consumer-boundary blobs are unchanged from Turn3. Fresh branch movement therefore does not remove the identified gaps or promote the initial strategies.

| Owner / path | Fresh blob or candidate status |
|---|---|
| `engine/prophet_strategy_definition.py` | `737401daaf29cae2ed26559703a283eeec5bd2b4`, unchanged |
| `engine/prophet_early_leadership_evidence.py` | `a64965bc50febedd9c2afb6f72b6f0a0c8c201aa`, unchanged |
| `engine/sue.py` | `121f181cf33e14fdbf6d7c9d383625465dc6338d`, unchanged |
| `engine/prophet_lab/intelligence_vector.py` | `d4705503a0dfbdcb6b9435382b79fa4c0a69303d`, unchanged |
| `engine/prophet_lab/earnings_dossier.py` | `c22d638ff6757558129d3e30ad827bc815b023b0`, unchanged |
| `engine/prophet_integrity.py` | `3eee55e8ff3c012fe97e3956bee3e1bbcade4bd6`, unchanged |
| `app/hub.py` | `fa3594206106eecbaa482d4a5489a9be8bc855d2`, unchanged; PERF candidate function/route absent |
| `scripts/build_prophet.py` | `f62564d44cf349f42abf96b870208b9570e9f6e2`; exact source reader, incumbent grading and record summary inspected |
| `engine/us_candidate_episode.py` | `c2821b4d95e0f116a4bb9db16acdf41c819ce038`; native B1 snapshot/events inspected |
| `engine/prophet_candidate_state.py` | `3c56c45fa6e9d0fa1d3ec15f2759ab07e27de852` |
| F04 template / builder / health | `91915538514ce1c6d3f0f754779ebcd02dd946dd` / `c879acf04e810145376cf019cd749f92e89a7053` / `788ee577f26a8c57adb0c050d9ffe8e014f75419`, unchanged |
| W07 builder / template | `fab6390b4c87605d98211e4c09ecc7c842cb2fe5` / `5697744b15c1f50e214071d93ea3aaa63a4269d4`, unchanged |
| All24Q docket | `47fd83c4b403476a59015cc8fdfb272d6a0d8814`, unchanged; all specified/not registered/not dispatched, all protected-outcome permissions false |
| PR7399 | OPEN, draft; actual head `41ca935449b6668c60e0b5ba2a0863703e072d8c`, unchanged |
| PR8308 | OPEN, non-draft; actual head `6b4b5ae5e2307453f2ddc0f2c0dbebe676c793b5`, unchanged; Cycle equity module still absent fresh main (404) |
| Terminal `ProphetView.tsx` / `SignalCard.tsx` | `74379a6b502334ebaff55fb153c3d998d811e0ab` / `a20481e59f96c3d2cc048cc563a215a1fd2188b4`, unchanged |

Source links: [strategy](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_strategy_definition.py), [Early Leadership](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_early_leadership_evidence.py), [Earnings](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/sue.py), [D5](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_lab/intelligence_vector.py), [integrity](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/prophet_integrity.py), [plan owner](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/scripts/build_prophet.py), [B1](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/engine/us_candidate_episode.py), [docket](https://github.com/mastermindx-market-intelligence/macro/blob/cae8e01be6ada447c11a6e77c4a46cab2abb69d2/research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json), [PERF candidate](https://github.com/mastermindx-market-intelligence/macro/blob/41ca935449b6668c60e0b5ba2a0863703e072d8c/app/hub.py), [Cycle candidate](https://github.com/mastermindx-market-intelligence/macro/blob/6b4b5ae5e2307453f2ddc0f2c0dbebe676c793b5/engine/prophet_cycle_equity.py).

## 2. Freeze the advertised capability ladder

These are separate qualification dimensions, not one global score or a new controller. Reuse strategy definition, B4, model/Evaluation, plan/management and Portfolio/Risk owner dispositions. The launch page and every card must describe the capability actually enabled for that exact species/domain/version.

| Capability | Permitted product promise after its implementation acceptance | Required owner proof |
|---|---|---|
| Catalogue and coverage | Explain the strategy's purpose, required evidence, limitations and current support | Existing eight-family definition and source coverage/disposition |
| Production factual research | Inspect comparable evidence, counterevidence, source clocks, revisions, explicit scenarios; compare/save/revisit | Qualified source paths, identity/rights, faithful owner projection, real entitled consumer proof and ordinary refresh |
| Qualified ranking / forecasts | Prioritize for a declared task; show an individually qualified forecast head with uncertainty and abstention | Exact accepted population, horizon, source/model/calibrator vintage, protocol and Evaluation disposition; ranking margin remains a relevance score |
| Current entry availability | Show the existing policy's present entry terms and blockers | Registered strategy/entry policy plus complete native mandatory facts, current basis/quote and deterministic B4 result |
| Strategy-native management | Show what an existing model plan's own accepted policy says now | Original plan/policy preserved and a current owner-issued management assessment; no entry-to-exit inference |
| Portfolio / allocation authority | Show descriptive shared exposure first; any sizing/personalization only under separately accepted authority | Existing Portfolio/Risk and actual authorized holdings; research/save never creates holdings |

**First useful product release:** advertise an evidence-led research workspace with truthful source-backed journeys, comparison, persistence and model-plan record. Enable only those qualified ranking, entry and management capabilities that actually clear their own gates. An all-unavailable sleeve containing only Paper fixtures does not satisfy its promised production research journey. A source-limited pilot can be shown with its named supported domain and measured coverage; it cannot be advertised as complete US coverage.

This is a launch sequence, not a reduction of the programme. The commissioned scope still includes the forecast, ranking, entry, management, portfolio and retained-roadmap work already mapped to B/Q/D/R. A research-only release is a milestone. Full US acceptance requires the original programme's implemented obligations and source-linked dispositions; it cannot be declared by disabling all hard capabilities or relabeling every open item unsupported.

### Sleeve-specific launch and promotion boundaries

| Sleeve | Useful factual launch capability to implement | Existing status / what does not come free | Next qualification obligations |
|---|---|---|---|
| Early Leadership / Sector Rotation | Same-date/window/basis stock–peer–market view; issuer-excluded peers; coverage/concentration; confirmed exposure versus membership; current setup/entry context separately | `CONTROL_ONLY`, `SHADOW_ONLY`; `2_15_SESSIONS` is frozen new-entry identity, not holding law. Descriptive residuals are not proven alpha. | Q03/Q05 group and nomination contribution; Q09–Q12 task ranking/heads; Q04/Q15/Q18 entry; Q16 tactical management. H10/H5/H15 proposed study endpoints stay separate from the frozen identity. |
| Quality Earnings / Expectation Revision | Comparable issuer facts, source-bound per-share transmission, revision timeline, explicit expectation availability, elapsed price response and current geometry | `SPEC_ONLY_FACTUAL_EVIDENCE_BUILDING`; current fixed Q06 comparator is not a general consensus/history feed; reconstructed vintage is not an as-run call | B08/Q01/Q06 source and event species qualification; Q09/Q11/Q13/Q20 heads; Q15 entry economics; Q16 event-native management. H42/H21/H63 remain proposals. |
| Cycle Capture | Named proving domain; dated cash/funding floor, restricted cash and obligations; financing/dilution scenarios; original security's value and recovery hurdle | `SPEC_ONLY`; PR8308 candidate not main. Scenario arithmetic is not financing access, survival probability or accepted hold/core/add rule. | Q07 source/domain readiness; Q08 survival/original-equity economics; Q09/Q11/Q12/Q20 heads; Q15 execution; Q17 core/add/exit. H252/H126/H504 remain proposals. |

### Five retained families

Policy/Event Swing; Catalyst/Dislocation; Liquidity/Debasement/Real Assets; Range/Mean Reversion; Defensive/Avoidance/Hedge Research remain explicit catalogue and Q23/B27 obligations. Freeze a disposition row for each: economic job, instrument/market, existing owner, evidence/rights readiness, killed-equivalence check, next bounded research dependency and accepted status. No automatic inherited Early Leadership coefficient, two-week washout rule, shorting, options, leverage or regional transfer. A missing data feed is a blocked claim, not a negative result. A killed mechanism stays rejected by its actual ruling. CN/HK/CA reuse remains market-native retained work rather than a claim that US contracts generalize unchanged.

## 3. Record population and period — exact freeze

### 3.1 Two distinct population kinds

**Launch `MODEL_PLAN_RECORD`:** the complete retained canonical model-plan inventory read through `load_effective_plans`, keyed by original plan ID, including open and terminal plans. Join canonical effective terminal rows by exact plan ID. Exact candidate/B1 lineage is obtained through `read_plan_candidate_source` where available; missing lineage remains typed. Do not require an exact B1 link merely to display an otherwise valid legacy plan, and do not invent that link from ticker.

Call this “Model-plan record,” with coverage explicitly `RETAINED_NATIVE_PLAN_SET`. It is not all signals, all opportunities, every displayed research candidate or every user's trades. The inventory must prove its own complete captured file set; it cannot imply that absent historical publications were retained. Terminal rows without a retained plan are an explicit orphan/coverage diagnostic, not silently appended to the originating-plan denominator. Repeated management updates or multiple render occurrences do not create new plans.

**`REGISTERED_OPPORTUNITY_COHORT`:** separate research/evaluation view, enabled only with a real existing Evaluation protocol/population reference. Its denominator comes from that protocol's immutable pre-selection eligible population, which may be an observation species or pre-B4 B1 cohort. It must not be reconstructed from closed plans or today's B1 active list. Retain never-confirmers, no-pullback/no-fill/no-entry, gaps, failed issuers and dependent repeated landmarks according to the accepted protocol. This does not create another study registry or backtester.

### 3.2 Default period and supported alternatives

For launch model-plan Record, default `period_basis=PLAN_RECORDED_DATE`, `membership_semantics=CURRENT_EFFECTIVE`, and an initial “All retained” period. A bounded date range applies to the owner-provided effective `recorded_at`; return the original value, any correction IDs and changed-membership count. Use ISO date precision as supplied. Do not fabricate a midnight instant or timezone from a date-only owner field. A record with unknown date appears in an explicit unassignable-period count; “All retained” keeps it inspectable.

This is deliberately called **plan recorded date**, not publication time or actual decision time. The plan owner documents outage reconstruction's `recorded_at` as the replayed origination day. `signal_date` may be a legacy formation alias. `entry_date` is not a safe fill-date alias. `effective_public_plan_date` already uses family-native bases and returns unavailable when that basis is unknown; preserve that helper for the public marker job rather than substituting it for every cohort clock.

Allow a second `period_basis=TERMINAL_CLOSE_DATE` only as a clearly named **closures during period** activity view. It retains its own terminal denominator and cannot be compared as though it were the originating cohort's strategy performance. Do not enable “entry period” or “signal period” filters until their distinct owner meanings are specified and source-qualified.

Filtering occurs on the complete entitled inventory before pagination. Source period filters and statistical eligibility are separate. Unknown strategy/model/management versions remain visible in an explicit legacy/unclassified bucket; no ticker or UI tab may assign them retroactively to one of the new sleeves.

### 3.3 Current as-of versus historical reconstruction

Default `as_of.mode=CURRENT_EFFECTIVE_VIEW`. Return actual request/read completion time separately from source inventory/generation receipts, correction generations, B1 generation, management assessment times and terminal ledger row `asof` values. `max(ledger.asof)` is **latest terminal observation**, not proof that every open plan was evaluated through that date. `complete_evaluation_through` stays null with a reason until an existing owner supplies that coverage fact.

Historical as-of requires an exact retained native source generation/inventory and the then-known correction, event and outcome evidence. Do not implement it by filtering today's corrected records to earlier dates. If that exact source state is unavailable, return typed `HISTORICAL_ASOF_UNAVAILABLE`; keep the current record useful and leave the unsupported historical selector disabled. A source vintage replay must identify itself as reconstruction, not historical as-run publication. Historical-as-of support remains a bounded native-owner extension wherever the advertised product promises it.

An arbitrary date in a UI, a hash, or a later-created manifest does not prove what users saw at that date. Existing B1 snapshots can support their own event/generation claims; they do not, by themselves, establish the matching plan, label and UI publication state.

## 4. Three separate Record axes

These are proposed presentation values mapped from existing owner facts. They do not replace native statuses or infer new events. Each axis partitions the selected inventory independently; rows can occupy one cell on each axis.

| Axis | Minimal values | Qualification rule |
|---|---|---|
| Model entry disposition | `ENTERED`, `NO_ENTRY`, `PENDING`, `UNKNOWN` | ENTERED means the model entry/trigger condition under the disclosed grading policy, not an actual customer fill. NO_ENTRY needs the native explicit disposition. PENDING requires an owner assertion that entry remains pending. Missing terminal/clock/trigger evidence is UNKNOWN. |
| Outcome availability | `TERMINAL_OBSERVED`, `UNRESOLVED_OWNER_CONFIRMED`, `OUTCOME_UNAVAILABLE` | A canonical terminal row supports the first. Current owner lifecycle/evaluation supports the second. Absence of a terminal row alone supports neither; keep unavailable reason. `maturity` is subordinate owner-supplied detail (`NOT_YET_DUE`, `DUE`, `UNKNOWN`), never estimated from an invented hold horizon. |
| Integrity disposition | `INCLUDED`, `QUARANTINED`, `EXCLUDED_BY_OWNER`, `UNVERIFIABLE` | Native quarantine union is authoritative. Any other exclusion needs exact owner reason/receipt. Source retraction retains entity/generation/effective time; it does not automatically erase a plan or rewrite its outcome. |

Correction, reconstruction and strategy/model version are orthogonal provenance fields, not extra mutually exclusive outcome bins. A corrected plan may be included or quarantined. An entered plan may be unresolved. A reconstructed plan can have a legitimate terminal grade under its disclosed method without establishing an original as-run forecast.

Counts reconcile as follows: for each axis, the sum of its cells equals the selected inventory count. Metric denominators identify their exact eligible cells plus per-metric missing-value exclusions. Never sum the three axes into a bigger population. Show cross-tabs when useful—for example entered × unresolved—and preserve exact selected row references in the protected owner response or corresponding native proof.

### Legacy method that must survive migration

`scripts/build_prophet.py::record_summary` already excludes quarantined rows, excludes NO_ENTRY from its scored-return rate and defines wins as positive finite raw stock results. Reconstructed outage plans are deliberately a disclosed split, **not automatic exclusions**. Preserve this method for its legacy descriptive job; do not relabel its rate as a new model's prospective hit rate.

`advance_ledger` stores `entry_date` as the price-basis/outcome-scan clock. `_determine_outcome` checks daily closes, establishes model triggering under its existing convention, records first-observable-close terminal outcomes, and uses the stated entry price for return. Its first T1 close prevents later T2 from becoming the recorded closing outcome; option results are unavailable in that pipeline. A non-null `entry_date` therefore does not prove actual trigger-confirmation time or execution. The new Record shows the grading convention and clock meaning explicitly. Q15/Q18 and a later accepted entry policy can qualify a different convention prospectively; they do not rewrite the legacy record.

Default reconstructed inclusion and source-owner “absent origination_mode means live” semantics remain preserved for this existing descriptive record. A stronger assertion that a research prediction was frozen as-run still requires the specific source/model/prediction receipt; the ledger convention alone is not that proof.

### Minimal metric rules

Each metric supplies `metric_id`, `value|null`, `unit`, `method_ref`, `population_ref`, `numerator_count` where meaningful, `denominator_count`, `excluded_counts_by_reason`, source/as-of references and an unavailable reason. For means, numerator_count need not masquerade as a sum; expose the valid sample count and exact method.

Preserve the incumbent positive-return share only as **positive raw underlying returns among scored closed model plans**, with its actual denominator. T1/T2 terminal counts are closing labels, not ever-hit target rates. No-entry counts remain visible in the originating population and complete policy research; they remain excluded from a closed entered-plan raw-return mean. Unknown returns are not zero. Benchmark/excess, option P&L, portfolio return, capacity, annualization and alpha remain unavailable until their own evidence exists. Cohorts with unqualified strategy/model joins can show honest descriptive history, not performance attribution to those versions.

## 5. Minimal Record interface and implementation owner

Evolve the existing PR7399 consumer under its original owner, preserving `load_effective_plans`, `load_effective_ledger` and the exact plan-source resolver. Do not add another ledger, grader, identity map, lifecycle or evaluation store. Since the new population and semantics exceed terminal-only `prophet.perf_projection/v1`, use an explicit new version, proposed `prophet.perf_projection/v2`, within the same private `/api/hub/prophet/perf` ownership. Final implementation may retain a compatibility response for a pinned v1 consumer; it must not change v1 semantics silently.

Minimum request:

```text
population_kind: MODEL_PLAN_RECORD | REGISTERED_OPPORTUNITY_COHORT
evaluation_protocol_ref: required native owner reference for registered cohort;
                         absent/not applicable for descriptive model-plan record
period_basis: PLAN_RECORDED_DATE | TERMINAL_CLOSE_DATE (model-plan record only)
period_start/end: ISO dates or null for all retained (model-plan record only)
as_of: CURRENT_EFFECTIVE_VIEW or exact supported snapshot reference
strategy/policy/model/provenance filters: only owner-qualified values
snapshot_ref: required when continuing a previous paginated result
offset/limit: pagination only after native full-population selection
```

Minimum response:

```text
schema, status, reason_codes, generated_at
snapshot: projection receipt + native inventory/generation refs
population: kind, coverage basis, membership semantics, exact query/filter echo
period: basis, start/end, owner precision, unassignable count
as_of: mode, requested/supported snapshot, owner watermarks,
       latest_terminal_observation, complete_evaluation_through|null
counts: inventory, matched, returned, each axis, orphan/unknown counts
rows: original plan ID + source binding + nullable native episode/generation,
      original/effective values and correction refs,
      owner strategy/model/entry/management versions or unknown,
      three axes with native reason/evidence refs,
      grading method + source clocks + outcome/return values
metrics: method/population/denominator-qualified objects
capabilities: supported filters, populations, historical-asof and metrics
```

**Pagination binding:** snapshot_ref is the stable digest of native inventory, correction/quarantine and relevant owner versions, the selected original IDs, canonical filter and applicable disposition-membership vector. Exclude request completion/generated_at from this population identity. Each fully attested page has a separate read_id and actual clocks. Real source or selected-membership changes return a typed snapshot conflict; a later read time alone does not. Page rows and counts replace together; multiple pages are not claimed as one evaluation instant.

This is a private projection. Authorization/entitlement is verified by the existing authenticated transport, not asserted by client filters or inferred from receipts. Error details preserve the established private-route sanitization. Querying a missing owner must not become an empty cohort. One request-local verified bundle binds plans, terminal ledger, corrections/quarantine and any B1 relations; changes, incompatible generations or contradictory plan/ledger provenance must not produce apparently coherent mixed-source metrics. A registered cohort's native protocol governs its population and label/decision cuts; model-plan period controls cannot override those definitions.

## 6. Bounded P4 scopes — three intelligence journeys

P4 owns T3C22–27 and T3C37, with source/identity/read dependencies supplied by P1/P2 and current B4 facts by P3. Each sub-slice returns exact source/candidate head, owner projection change, fixture proof, real consumer proof and unsupported reasons. The working IDs below group the commission; they are not new runtime workstreams.

| Slice | Minimal implementation | Acceptance that distinguishes success |
|---|---|---|
| P4.1 Early Leadership | Project existing compiler output and GMI owner metadata; complete the existing peer producer's exclusion/coverage proof | Changing own return or adding an issuer alias cannot change its excluded-peer confirmation; historical membership/window/basis mismatch fails; singleton metrics null; real supported page shows counterevidence without rank/B4 promotion |
| P4.2 Earnings provenance | Source-bound per-share child/adaptor at Earnings/D5; exact release/call/filing/revision projection; preserve original D5 cut | Wrong issuer/fiscal/accounting/currency/share basis and late source/observation/generation fail qualification; same-period correction not growth; valid bridge reconciles comparable source EPS; original decision view remains unchanged by later facts |
| P4.3 Earnings research view | Deep comparable facts→expectations/revisions→elapsed price response, using one admitted owner read | Missing consensus is visible, not invented; source-vintage reconstruction clearly differs from an as-run call; changing contributor roster cannot masquerade as matched revisions; factual view remains useful with current entry unavailable |
| P4.4 Cycle owner integration | Reconcile PR8308 incumbent; wire qualified existing capital/share/identity owners for named pilot domain | Early breach survives a later rescue; cash floor/restricted cash and missing schedule correctly affect availability; proceeds/fees/debt/shares reconcile; observed and scenario assumptions are separate |
| P4.5 Original-equity scenarios and explanations | Qualified original claim mapping, total contributions, scenario reset/sensitivity; cited explanation over owner facts | Surviving issuer with zero old-share value remains zero; no replacement-security price splice; no financing double count; source change invalidates derived explanation; no unqualified probability/size/action |

Original D5 membership remains `opened_at=max(anchor.time,known_at)` with all three source clocks before that cut. Current/landmark evidence is a separate explicit owner extension; a read refresh cannot relabel the original episode. Per-share source repair, scenario arithmetic and high-quality explanation establish factual capability only.

A real source-positive case plus decisive missing/failure cases is required for each advertised slice. Fixtures alone establish contract behavior, not installed production sourcing. Source insufficiency blocks that claimed species/domain; another authorized supported lane can still deliver useful product value under the original activation branches.

## 7. Bounded P5 scopes — qualification and management

P5 owns T3C33/T3C34/T3C38 and preserves all24Q/B dependencies. The final commission authorizes work through the established programme; this document itself registers or runs nothing. Fable uses the existing Evaluation/QLedger/Arena/source/model/strategy owners and their admission/rights/formal-read law. No new parallel registry, shadow promotion controller or guessed numeric acceptance threshold.

| Slice | Concrete deliverable | Gate for advertised capability |
|---|---|---|
| P5.1 Protocol and input readiness | Map every Q to its actual source/program owner, immutable endpoint/population/control, prerequisites and current disposition; preserve #7751 population/duplicate-label treatment | Source/time/model vintage and rights are adequate for the specific claim; exact economic/statistical criteria are declared through the actual owner before protected outcomes, never chosen after results |
| P5.2 Ranking and forecast heads | Versioned task-ranking artifact; individually qualified return/tail/timing heads and calibrators with coverage/abstention | Same-population strong controls; time-ordered and selected top-K calibration; costs, dependence, multiple comparisons and fair information/compute budgets; unsupported heads stay absent |
| P5.3 Tactical/Earnings management | Versioned owner policy, original-plan handling, event/reset/re-entry rules and accepted comparison | Freeze entries when comparing exits; separately registered entry×management interaction; no post-outcome holding horizon, unreachable fills or moving losers to another sleeve |
| P5.4 Cycle management | Separate core, tactical adds, funding/milestone invalidation and maturity policy | Failure-inclusive original-equity cohort; no mechanical averaging down, hold-through-all impairment or survivor-only recovery; allocation remains downstream |
| P5.5 Retained roadmap | Explicit Q23/B27 disposition for all five later families, instrument distinctions and market-native reuse | Killed-equivalence checked; no silent disappearance or renamed killed strategy; actual next dependency or accepted negative outcome is preserved |

### Research disposition taxonomy

Use existing owner status values; project the following meanings without pretending these labels already form a runtime enum:

- **Supported within scope:** source-linked adjudication accepts a named claim for exact strategy/species, horizon, population/domain, model/policy vintage and conditions. It is not universal acceptance of every head or region.
- **Evaluated null / rejected on evidence:** the actual predeclared test and owner adjudication establish lack of support or a falsifier in its declared scope. Retain the result and failed alternatives. A broad claim of impossibility does not follow.
- **Inconclusive:** available evidence is insufficient to discriminate the claim. Neither support nor rejection is asserted; uncertainty and next legitimate evidence need remain explicit.
- **Blocked by input, rights, history or authority:** exact missing prerequisite and owner/action are named. This is not an outcome, and it does not satisfy a required scientific delivery merely by labeling it unsupported.
- **Rejected by binding mechanism ruling:** a real existing killed-equivalence/source decision applies. Do not rename, retune or repackage the mechanism to evade it.
- **Not yet evaluated:** specified work has not run under its proper protocol; current all24Q source remains in this category.

All original Q endpoints remain in the final matrix. Product acceptance Q24 and notification usefulness Q19 do not substitute for Q09–Q11 forecasts or Q16/Q17 management; source repair Q01 does not promote science. Every disposition must include exact source/protocol/evidence refs, claim scope, blockers or falsifier, and what it permits the product to expose. An arbitrary unsupported label is not full-programme completion.

## 8. Bounded P6 scopes — Record, attention and portfolio context

Coordinate P6's attention/Follow sub-slices with the experience owner; preserve its frozen channel/enrollment/delivery contract. C3 freezes the Record/portfolio portion:

| Slice | Implementation | Acceptance |
|---|---|---|
| P6.1 Native inventory and original/effective relation | Reconcile PR7399; join retained native plans and effective ledger by ID; exact source resolver and orphan coverage | Open and terminal plans both present; duplicate IDs fail; legacy absent B1 link stays inspectable and unavailable, not retargeted; original bytes unchanged |
| P6.2 Period/as-of and axes | Implement the exact contract above, full-population filters before paging, explicit snapshot continuity and three-axis mapping | Entered+unresolved is counted once per axis; no-entry, unknown entry, missing terminal, quarantine, correction and reconstruction all reconcile; a past date without an exact snapshot is unavailable |
| P6.3 Metrics and provenance UI | Preserve incumbent grading/record semantics; per-metric denominator/method and honest legacy grouping | Non-null legacy grading clock never claims actual fill; T1/T2 closing labels remain correctly named; unknown return not zero; no generic alpha or pooled headline attributed to a new sleeve |
| P6.4 Registered evaluation view | Consume an already lawful existing Evaluation cohort and frozen prediction/label receipts when qualified | Complete pre-selection cohort and no-entry/never-confirmers retained; source/model/policy/horizon/landmark grain explicit; no protected reads merely because Record shipped |
| P6.5 Portfolio context | Existing authorized holdings and exposure owner; descriptive relation across saved ideas/Plans/holdings | Saved/Follow never becomes position; multiple listings/sleeves share issuer exposure without duplicate capital; no sizing/personalization authority manufactured |

Reconstructed plans stay identified in the model-plan Record according to the incumbent method; prospective model evaluation applies its own accepted provenance eligibility. Source retraction can affect the current explanation and trigger a management review under the actual owner; it cannot automatically delete the historical published decision or assert an execution exit.

## 9. Discriminating release proof for these slices

Use bounded meaningful fixtures and real entitled consumer paths; do not build implementation-mirroring tests or rerun protected studies for UI validation.

1. One source-qualified path for each advertised initial sleeve reaches its deep evidence view with source/clock/coverage visible; supported and opposing facts remain readable on desktop and mobile.
2. Changing a candidate/alias cannot alter excluded-peer support; missing peers and mixed bases never produce a confident label.
3. Late Earnings call/filing/revision or newly generated source cannot improve an original-cut view; the separately labeled current view may show the actual later receipt.
4. Per-share mismatch fails qualification; a valid bridge has traceable source observations and exact arithmetic reconciliation.
5. Cycle financing arriving after the cash breach cannot erase it; canceled old shares and additional contributions retain correct economics.
6. Record inventory has both open and terminal examples; three-axis counts, period changes, unknown dates, corrections, quarantine and reconstruction reconcile under one native generation.
7. Legacy grading `entry_date` is displayed with its real clock meaning; no user fill or executable return is implied.
8. A simulated historical-as-of request without native snapshot support returns typed unavailable, rather than today's corrected facts filtered backward.
9. Original plan terms/policy survive newer research/management versions; a current entry WAIT/RAN state is never displayed as an exit instruction.
10. F04 and W07 keep their Turn3 bounded source-availability fixes in P1/P7: absent dislocation is not Closed; valid empty winner cohort differs from stale/malformed/missing; calendar-day/session policy is owned and explicit.

Actual scientific performance, adequate economic margins and per-head qualification are proved through P5's original protocols, not these product fixtures. Full release also depends on P7's security, accessibility, ordinary refresh, served-version, telemetry and rollback proof. No outcome in this note is claimed executed.

## 10. Final editorial determination

The final commission can freeze now with these choices. No C3 ambiguity requires another editorial round:

- Record population, period meaning, current-versus-historical as-of, three axes, legacy method and minimum interface are fixed.
- The three useful launch journeys and their separate predictive/entry/management boundaries are fixed.
- The five retained families and all24Q endpoints remain mapped; blocked, inconclusive and rejected meanings cannot be interchanged.
- P4/P5/P6 have bounded owner-preserving slices and real acceptance conditions.
- Future scientific results, rights/source readiness and release evidence remain honest implementation dependencies. Another editorial turn cannot legitimately invent them.

If a later exact owner fact contradicts this contract, Fable records a source-linked bounded amendment with its effect on advertised scope and acceptance. Routine implementation choices do not require a new Chairman design round. Actual reserved controls, denied effects and unknown mutations retain their governing handling; this note grants no authority to bypass them.


## D. Cross-contract interpretation

The final delivery commission governs packet sequence and shared-path serialization. Any repeated sub-slice label is local to its named owner section: notification slices are P6.N1-P6.N3; Record slices are P6.1-P6.5. Historical fresh-source statuses remain dated observations. Implement the strict versioned producer/consumer contracts; do not treat proposed names, enums or authoring hashes as existing runtime fields or source authority.
