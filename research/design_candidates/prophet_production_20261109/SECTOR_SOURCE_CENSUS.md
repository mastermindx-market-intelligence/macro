# Prophet × Sector Intelligence — source owner architecture extension

**Status:** C3 source analysis and proposed design/contract amendment only. No application implementation, experiments, protected outcome reads, runtime admission, Paper action, external message or GitHub mutation was performed by this adviser.

**Observed source pins:** Macro main **f3a547cc09872d9aaa719759a6a2daa2832edad5**; Terminal protected master **2fe2f02f07d1df8c855388bc556383cd74de44fd**. Source reads 10 November 2026 UTC / 9 November America/Vancouver. Prior Prophet v4 remains the baseline. Fresh source findings require an additive cross-programme amendment, not a new sector project.

## 1. Executive architectural finding

The shared intelligence substrate already exists in substantial pieces. The missed opportunity is the product/consumer and measurement contract joining them. Prophet should become a market → sector/industry/theme → exact security investigation with two-way evidence, while Sector remains the analytical owner of the market/group measurements and Prophet remains the owner of its candidate/strategy/entry/plan semantics.

A material fresh finding is that the **Sector Intelligence implementation is already active in source continuity**. Macro #10922 merged the final Sector plan and execution charter/frontier as f3a547cc…. The frontier names Fable T3 COO thread 2f136a11-91f9-4bca-bf10-8a1d8b7f4e5d and records lanes 1–8 STARTED. This means launched worker threads according to that source, not delivered/merged/served results or an independently observed current runtime state. Do not create competing Sector files, write their donor branches, or silently change their shared APIs.

The Chairman's beta-first intent should become a **product ordering and programme acceptance obligation**: explicitly observe market participation; evaluate sector allocation/rotation against an investable benchmark; only then claim incremental stock-selection value. It is not evidence that current descriptive sector labels forecast returns or that a stock in a leading group has low absolute risk. In particular, the new connection must not bypass the current false ranking/gating/sizing/trading flags on the descriptive projection.

Sources:
- [Sector execution frontier](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/research/sector_completion_20261021/EXECUTION_FRONTIER_2026-11-09.md)
- [Sector execution charter](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/research/sector_completion_20261021/EXECUTION_CHARTER_2026-11-09.md)
- [Final Sector masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/research/sector_completion_20261021/SHARED_SHELL_MASTERPLAN_2026-11-09.md)
- [Final Sector execution packet](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/research/sector_completion_20261021/FINAL_FABLE_T3_PACKET_2026-11-09.md)

## 2. Actual reuse map

| Capability | Existing owner / exact source | What source proves | Boundary / required extension |
|---|---|---|---|
| Regional market state | engine/market_state.py; MarketProfile plus market_state_cn.py / market_state_hk.py | Common display synthesis with market-specific index tape, conditions readers and permitted override families | Observed state/confirmation, not remaining-return or pivot forecast. Preserve local clocks and each source's original authority; do not turn the display blend into new sizing policy |
| Existing Sector Central posture | engine/sector_central.py::_regime_anchor / market_context | Consumes actual incumbent macro_risk gate and separately the Market State headline | The incumbent gate and the descriptive headline have distinct owners/semantics; their values cannot substitute for one another |
| Measured group context | engine/leadership_rotation_context.py | Stateless GroupMeasurement, TransitionObservation, ResearchEstimate, measured_group_read and source/cohort/clock math | Display-only projection; no new store, evaluator, lifecycle or publication owner |
| Full measured Sector projection | engine/sector_central.py::_measured_read | Central already publishes the measured read over the Cycles spine and rotation events | Prophet should consume this owner-qualified object, not parse labels or reconstruct an independent score |
| Sector Pulse | engine/sector_pulse.py::build_pulse / ticker_themes / for_ticker | Shared regional per-theme lifecycle, scores, rank/score deltas, relative performance, breadth and descriptive heat | for_ticker selects strongest theme but also returns all theme_ids. Preserve all affiliations; strongest badge is not exhaustive economic identity. Archive shortfall stays null |
| Group, industry and theme hierarchy | engine/theme_graph/structural_navigation.py::hierarchy_paths | Existing as-known graph endpoint traversal, rights/provenance and adjacent hierarchy | Parent membership does not imply all descendant exposure; recorded context basket references are not complete official classification |
| Company Theme Exposure | engine/company_theme_exposure/contracts.py; existing build/publish/BFF chain | Closed company_theme_exposure.v1 membership projection with source-generation receipts and direct/proxy/context mapping qualifiers | It is not measured revenue exposure or supplier/customer proof. New economic assertion fields need an explicit versioned owner adaptation |
| Prophet Early Leadership | engine/prophet_early_leadership_evidence.py::build_early_leadership_evidence | Six-owner comparable envelope: candidate, leave-issuer-out peers, theme, exposure, setup, geometry; exact time/window/basis/membership checks; arithmetic return decomposition | All action/rank flags false; source reader exclusion proof remains necessary. Its theme_state/v1 and economic-exposure schema are not interchangeable with CTE or Neural Web schemas |
| Existing residual factor math | engine/residual_alpha.py::residuals; engine/residual_momentum.py | Lagged market/sector residual construction and diagnostic generalization | Current residual_alpha sector mean includes the candidate. It cannot serve as independent leave-issuer-out confirmation unchanged. Residual is model-dependent and not proven alpha |
| Portfolio factor model | engine/factor_exposure.py plus existing Portfolio consumers | Existing factor betas and actual-position-weight aggregation, concentration and factor-risk owners | A separate authority from candidate ranking. HK/CN/CA cash equities explicitly unmodeled in this US-clock model |
| HK/CN global exposure | engine/hk_global_beta.py / cn_global_beta.py | Lagged SPY overnight transmission, trailing beta and native exposure roles | Different factor from local HK/China market beta. Local market participation cannot be measured using only this global factor |
| Cycle timing | engine/cycle_rhythm.py / cycle_phase_age.py / sector_cycles.py | Last nonprovisional turn, historical spacing window; actual-session phase-age history | Descriptive window is not a calibrated probability interval; legacy turn confirmation knowledge is incomplete |
| Generation/publication | scripts/build_sector_intelligence.py on main; #10780 sector_generation_contract / sector_native_view / app/sector_generation.py candidate | Main has one strict existing build sequence. Candidate captures five existing documents and binds native projection to existing publisher/authorization | Candidate is unmerged and under active Sector lane 1 integration. Do not add another poller/static fallback or publisher |
| Native transport and navigation | Terminal app/api/sector-intelligence/route.ts; sectorIntelligence.ts; sectorDepthReturn.ts | Existing fixed-origin, private, authenticated 11-family reader; state codec and bounded exact-return semantics | Lane 3 owns integration of shared files. Prophet uses/adds a typed cross-product origin through these owners instead of another global navigation state |
| Durable investigations | Existing Terminal investigation owner, also assigned to active Sector lane 6 | Shared user persistence and receipt system already named by both plans | Prophet D05 v3 additions and Sector investigation extensions must become one additive compatible validator/admission migration, not two conflicting migrations |

### Exact source links and blob identities

All main Macro links below are at f3a547cc…, all Terminal links at 2fe2f02f…:

- [Market State](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/market_state.py), blob d375d69c5f361e348a8f85e73f2da1bc43b71aec.
- [China market profile](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/market_state_cn.py), blob 041df8912f7d9cc154da18f2c9f5e4c0c62cc70e.
- [HK market profile](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/market_state_hk.py), blob 27f98ddfb5966c9c54850c24543afc9ea5d400b0.
- [Leadership measured owner](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/leadership_rotation_context.py), blob 762798dec8155808dfcb80fcecd6d2a07bbb1f40.
- [Sector Central](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/sector_central.py), blob 566798081ba58b6ef97bbe8996221c9ff036a8a7.
- [Sector Pulse](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/sector_pulse.py), blob cf2e658f0baa73a884311ed0c7ae09f6c8e7da63.
- [GMI hierarchy](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/theme_graph/structural_navigation.py), blob 70cfbb1aef5cce09e6a9d60afe115d8ced0bfd54.
- [Company Theme Exposure closed wire](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/company_theme_exposure/contracts.py), blob eb1b5136f220027c746eb086b3403b77e3bbdc13.
- [Prophet Early Leadership compiler](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/prophet_early_leadership_evidence.py), blob a64965bc50febedd9c2afb6f72b6f0a0c8c201aa.
- [Residual alpha owner](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/residual_alpha.py), blob e0afcb355b83b30f3afe5e0f04afd078676fb957; [diagnostic generalization](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/residual_momentum.py), blob 29c86ee13b83d6cd32dfa9fe82957871d65bd06a.
- [Portfolio factor owner](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/factor_exposure.py), blob 52cc784da54d9a3c4659091f275a5c81851625ff.
- [HK global beta](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/hk_global_beta.py), blob 98aadb350fb03a7ca5b62b7b7628db077c275e11; [China global beta](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/cn_global_beta.py), blob 992e37aa23a2f6b3c212d042625b55573bd7a033.
- [Cycle rhythm](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/cycle_rhythm.py), blob 8c6f83e108ef6e6169c89eccbe6a576c83c1fa6f; [phase age](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/cycle_phase_age.py), blob d7f5863da7b00c4e09cab36b9734daf07d4e4167.
- [Strict build sequence](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/scripts/build_sector_intelligence.py), blob b5fb854461e07561cf02720ab2615e6266425b1c.
- [Terminal gateway](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/app/api/sector-intelligence/route.ts), blob 2ebc26e0510907d48ab4b1200217a37da06d876b.
- [Terminal state codec](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/lib/sectorIntelligence.ts), blob 07757d367c69d729b5337d887042496b5e72417f; [depth return](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/lib/sectorDepthReturn.ts), blob 9bfbc63bd83cfc1becf3a8596203e2c6e5a268d6.

## 3. Proposed shared contract under existing owners

This is a semantic field allocation, not a new schema registry or independent service. Add explicit versioned children to the existing Sector projection and Prophet v2 read contract where closed schemas require it. The existing generation reader and Prophet same-read owner compose them.

### 3.1 Market/group context identity

Each context reference needs:

- Source owner and native schema/definition/version.
- Native generation/publication reference and exact member/artifact hash; separate private source identity and permitted consumer content hash.
- Market profile, venue/session calendar, issuer/listing identity where applicable.
- Group ID and kind: sector, industry, curated theme, provider concept, ETF proxy; never treat these as interchangeable.
- Benchmark instrument/index identity, total-return/price-return convention, local/base currency and any currency conversion policy.
- Horizon definition and actual start/end session, weighting/rebalancing convention, cohort and membership revision.
- Source observation/session, source availability/knowledge, computed/publication time and current read/evaluation clock.
- Current/historical reconstruction mode, correction references where native, qualification, rights/access and missingness.
- Expected, eligible, measured, advancing, declining, unchanged and missing counts as relevant; distinct count coverage and weight coverage.
- Existing authority flags unchanged, with explicit semantics for descriptive order, owner-issued signal, qualified predictive estimate and user-selected research filter.

Use the actual GroupMeasurement fields rather than inventing redundant names. Its existing fields already cover group_id/group_kind/cohort_id, membership_source/revision, market/session_end/benchmark/price_basis/currency/window_sessions, observed_at/source_available_at/issued_at, expected/admitted/measured/missing members, weight source/effectiveness/convention, breadth/concentration/overlap/source_roots, evidence_mode/use_rights.

### 3.2 How it joins Prophet without a publication cycle

At the start of an authenticated Prophet read, capture the selected native Sector generation **once** through its existing trusted reader and bind the exact qualified subobjects into Prophet's immutable same-read bundle. Use that same captured context for the list, selected setup, comparison, source drawer and evaluation feature references. Do not read "latest" a second time for the detail or regenerate Sector during a Prophet read.

Sector and Prophet retain distinct native generation IDs. Requiring string-identical generation IDs across independent owners would be a fake coherence rule. The join is an exact tuple of owner refs, source clocks and declared compatibility, with policy-specific time/basis checks. A market close and an earlier filing need not share a timestamp; the consumer must preserve their relation and prove both admissible for the intended cut.

A current refresh may show new market/sector context while retaining the original candidate/Plan context as a separate dated record. It cannot rewrite original D5 membership or the original decision's evidence. Missing original retained context means "original sector context unavailable," not a join to today's sector.

**Important existing API limit:** #10780 app/sector_generation.py accepts only the closed audience query. Callers cannot select arbitrary root/path/URL/generation IDs. If exact saved-generation reopen is not already served by an admitted retained resolver, extend that existing resolver with a closed authorized reference form. Do not claim that passing a generation ID to today's public route works, and do not add a browser-direct archive path. A content hash/read_id is not storage or historical availability.

### 3.3 Current candidate generation source

Fresh PR metadata confirms:

- Macro #10780 OPEN, non-Draft, unmerged at **91add9613ad29dcfb82ff75036dd6519cfc6c06f**.
- Macro #10839 OPEN, non-Draft, unmerged at **3894ea1befb9ffe7f45e3398a1334c6c14b13a51**.
- Macro #10703 OPEN Draft at **9fc460ff36345387c3a2c5435b079852e8488da0**, original HOLD carrier.

#10780's domain member set is exactly:
sectordata/sector_central.json; sectordata/sector_cycles.json; basketdata/baskets.json; basketdata/si_handoff.json; basketdata/action_board.json.

The existing domain contract validates captured bytes and input identity, source and baseline sessions, publication time, session age and developing-at-publication qualification. A later read cannot turn developing bytes into a final close.

Sources:
- [Candidate generation semantics](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/lib/sector_generation_contract.py), blob 34cb737d0a94b185c43dc188e49b8bc512b0f34a.
- [Candidate native projection](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/engine/sector_native_view.py), blob 98b23feacb36b1f9411612475e724c3d852c126d.
- [Candidate API](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/app/sector_generation.py), blob 7ae4eeb4229e743fcb926b105c258b5e7b09803a.
- [Dated-context owner dependency](https://github.com/mastermindx-market-intelligence/macro/blob/3894ea1befb9ffe7f45e3398a1334c6c14b13a51/engine/sector_dated_context.py), blob 00048d668d7b613b330ec6509cb8d5bbf4e9aee8. Its configured-theme/public-risk scope is bounded; it does not already prove general sector causality.

## 4. Truly two-way evidence, without circular confirmation

### Downward: Sector to Prophet

Use qualified market state, measured leadership, breadth, concentration, membership changes, economic evidence and original native transition events to:

1. Explain the market/sector backdrop before the candidate list.
2. Let users focus the full entitled research population by exact sector/industry/theme membership.
3. Compare the selected company's performance and evidence with market and issuer-excluded peers.
4. Carry the context into original-versus-current setup review, Follow and saved investigation.
5. Evaluate whether sector-conditioned selection/entry/management improves the registered outcome.

A deliberate user research filter is not automatic global candidate admission or a new statistical ranker. The unfiltered population remains reachable; out-of-leadership cases and counterevidence remain inspectable. Any production policy that boosts, suppresses, sizes or exits a candidate due to sector conditions must be separately qualified through the existing Strategy/Evaluation/Portfolio/Risk authority.

### Upward: constituent evidence to Sector

The reverse flow should consume **original source-qualified constituent observations**, not Prophet's chosen winners, ranks or final confidence labels. Reuse the existing group/member/earnings evidence producers and add native aggregation fields there. Examples:

- Breadth of compatible earnings improvements across the declared reporting cohort.
- Revision participation, with issuer, fiscal period, publication availability and revision vintage preserved.
- Price participation, widening/narrowing leadership and contribution concentration.
- Industry-specific economic confirmations or contradictions.
- Counts of qualified setup states as a descriptive population view, with the full eligible denominator and exact model/version. A count of selected Prophet candidates is a selection statistic, not sector fundamentals.

For each aggregate, preserve complete point-in-time eligible membership, reported/usable/unknown counts, issuer deduplication, native source-root identities, weighting and window. An absent report is not deterioration or a zero. A currently reclassified company cannot move into the historical group retroactively.

**Self-confirmation rule:** when the aggregate is used as evidence for issuer X, recompute or consume an owner-provided leave-X-out object excluding every same-issuer listing/alias. One company's stock performance must not boost its group score, which then boosts that same company's confidence as "independent support."

**Repeated-evidence rule:** reuse leadership_rotation_context.dedupe_source_roots. Sector trend, theme trend, Prophet excess return and an LLM explanation can all descend from one price series; they are a common evidence family, not four votes. Multi-theme membership and shared constituents likewise need overlap/concentration disclosure.

There must be a directed dependency graph:
original sources → identity/membership/rights → group/constituent facts → consumer projections.
Prophet user selection and model outcomes do not feed the source observations that justified those same decisions. Post-decision research outcomes return only to the existing Evaluation/learning owner with original cohort/protocol identity.

## 5. Beta, relative performance and residual attribution

Keep four different meanings separately visible:

1. **Benchmark-relative price/wealth movement:** a descriptive comparison over an exact window.
2. **Statistical beta exposure:** model-dependent sensitivity with trailing estimation sample, factor, currency, lag, shrinkage and uncertainty/quality.
3. **Portfolio benchmark participation:** measured from actual or explicitly simulated holdings and cash under a fixed investable benchmark and cost convention.
4. **Incremental stock-selection value:** evaluation relative to benchmark/sector baselines after costs, not raw stock gain or a model residual renamed alpha.

Reuse existing relative_wealth and return_difference, and preserve percentage versus percentage-point labels. beta_only_residual already computes residual against a **stated hypothetical past-known beta**; it is not a live beta estimator or causal decomposition. The Early Leadership arithmetic identity stock-minus-market = peer-minus-market + stock-minus-peer is useful and exact on compatible returns, but those components are not factor-adjusted or causal alpha.

Current residual_alpha.residuals uses R[cols].mean(axis=1), including the candidate. Preserve its accepted incumbent behavior; create an explicit qualified leave-issuer-out adaptation at that owner if reusing it for independent candidate confirmation. Do not silently alter the incumbent ranker or claim existing code already satisfies this condition.

The user-facing sequence can be "Market participation → sector choice → company selection," but actual matching/exceeding of the benchmark must be measured by the existing portfolio/evaluation owners. No screenshot or green sector label proves captured beta.

## 6. Cross-market applicability is explicit, not a skin switch

US, China A and HK require native benchmark/calendars/currency, securities and membership conventions.

- US native 5/20/63-session measurements differ from 21/63 dossier RS and 1M heatmap participation. Do not relabel 20 as 21 or 1M as a fixed session count.
- China subsector rotation uses THS concept baskets and curated A-share thematic baskets. The existing broad concept filter has a minimum member rule and source-specific return windows. A concept board is not an official industry classification. Its _members helper produces a top-eight preview; this cannot become the full Prophet selection or coverage denominator.
- HK breadth uses a curated constituent map and equal-weight synthetic sector baskets. Existing source explicitly describes that universe; current curated membership does not prove historical PIT sector classification. Sector baskets and investable sector proxies are different objects.
- HK/CN global_beta use a lagged SPY overnight factor; local benchmark participation and local sector beta need separate native definitions. Do not merge US and Asia closes by calendar date alone.
- The existing portfolio factor engine leaves HK/CN/CA cash equities unmodeled. It cannot be made cross-market merely by displaying those names in a new component.
- A/H listings share an issuer but have different venue, currency, calendar, access and return series. Deduplicate issuer evidence while retaining listing-specific investability and price behavior.
- Historical delistings, suspensions, stale closes, reclassifications, constituent churn and unavailable benchmark total-return histories remain explicit research dependencies.

Sources:
- [China subsector owner](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/subsector_rotation_china.py), blob ed8f9568622e7eb9fd78307f887730b5fb46508b.
- [HK sector legs](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/sector_legs_hk.py), blob de4e917fe3017fab03577403f0dbb06fee931c9a.
- [HK breadth owner](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/collectors/hk_breadth.py), blob c8cf7e480cb9c49ce5165cef16ee349a9c3f7e1e.
- [Sector Round 3 measurement/PIT definitions with final amendment](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/research/sector_completion_20261021/ROUND3_ARCHITECTURE_CONTRACT_2026-11-09.md).

## 7. Cycle stage, remaining opportunity and pivots

The existing contract has useful current measured state, phase-age, historical rhythm windows and a separate ResearchEstimate object. Share these exact objects; do not construct a new universal "remaining upside" gauge from cycle position.

- Phase age: actual-session contiguous age, lower-bound age and unknown/not-logged differ.
- Rhythm window: anchored to the last nonprovisional pivot and historical spacing of the same definition. Today advancing does not move the fixed window edges.
- Pivot knowledge: distinguish pivot date from confirmation/first-known date. Legacy Sector Cycles turn histories do not already prove as-known confirmation timestamps.
- Current hazard/model: existing source retains LIVE_HAZARD_PARITY=PARITY_FAILS. An admitted model estimate needs exact model/feature/direction/basis/epoch/cohort/horizon parity; a displayed historical prior has different meaning.
- Remaining opportunity: first show observed extension, breadth, concentration, contrary evidence and owned entry/management geometry. A probability, return range or expected remaining duration needs a qualified existing model/protocol and its uncertainty definition.

This is a useful product immediately at the descriptive tier while predictive qualification proceeds. It cannot close the user's predictive ambition merely by hiding it; retain the explicit forecast/rotation policy research acceptance.

## 8. Exact integration mapping to active work

| Active Sector lane | Extension request | Prophet packet |
|---|---|---|
| Lane 1 Macro generation | Expose existing group/context identities and retained refs with the current coherent publication; qualify consumer join | P1/P3 |
| Lane 3 Terminal sole integration writer | Shared origin/return props, exact subject/cohort transport and one mounted cross-product context component | P2/P4 |
| Lane 4 full Cycles | Native rhythm/phase-age/confirmation/forecast capabilities and deep links, preserving method and unavailable states | P4/P5 |
| Lane 5 Research v2 + industry evidence | Source-qualified constituent economic evidence and admitted research detail; membership versus economic exposure | P4/P5 |
| Lane 6 durable investigations | One compatible subject/evidence/version/receipt migration for Sector plus Prophet D05 | P2/P6 |
| Lane 7 retained depth | Access to flows, four universes, legacy cases and exact return; no migration by headline alias | P4/P6 |
| Lane 8 analytics/history | Common definitions, PIT cohorts, leave-issuer-out aggregation, attribution and benchmark-first study design | P5/P6 |
| Lane 9 eventual integrated proof | Cross-product real served journey, ordinary refresh, account isolation and failure cases | P7 |

Root should attach this as an integration amendment to the Prophet commission with source links to the active Sector programme. No dispatch or active-lane instruction is made by this report. Any later actual coordination must use the existing eligible Fable receiver and preserve live writer scope.

Paper: work only on Prophet's disjoint page/targets. Sector lane 2 owns its R4 design territory. Include the bidirectional journey and exact build instructions on Prophet's new boards, with links to Sector's accepted design donors.

## 9. Discriminating acceptance additions

1. Today → selected leading sector → full filtered Prophet universe → company → original sector return preserves market, group kind/ID, cohort, metric window, generation, sort and selection.
2. Deliberate cross-filter selection includes a relevant company outside the source preview and keeps unknown/unmapped identities explicit.
3. New Sector generation arriving mid-Prophet read cannot mix list and detail; later refresh changes current context without rewriting original investigation.
4. Same-day membership correction invalidates only affected metrics/references; original-known membership remains retained or unavailable.
5. Replacing one issuer's return/news with a large change does not alter its own leave-issuer-out confirmation. Cross-listed aliases are excluded together.
6. Reusing the same source under sector/theme/Prophet labels adds no independent evidence families.
7. Strong relative sector performance with a negative absolute return is labeled relative resilience, not recovery or positive beta capture.
8. A leading sector with declining breadth/concentrated contribution shows that contradiction; a weak sector's strong individual case remains investigable.
9. Failed context feed preserves unaffected Prophet evidence while withholding dependent policy/forecast claims; no static fallback masquerades as admitted generation.
10. US/HK/CN close alignment respects actual available times; later US close cannot influence earlier Asia decision.
11. Save and reopen recover exact original context or an honest unretained status; a digest alone cannot synthesize the old view.
12. Outcome views separate benchmark participation, sector contribution, stock selection, costs and unknown components, with complete eligible population and qualified holdings/model basis.
13. Sector-state alerts use the existing native event owner, dedupe and private preference/outbox; poll churn and market restamps do not generate transitions.
14. Models/authorities remain unchanged when only descriptive context is added. Any changed rank/gate/size must be named as a qualified policy change with actual evidence.

## 10. Read scope and limitations

This adviser read current default source, the final Sector programme, fresh exact candidate PR metadata and relevant source modules. No installed application/runtime/DB state or live served correctness was verified. Source continuity says worker lanes started; that was not independently checked through runtime. Historical scientific statements in source comments are owner claims, not new validation by this report. No source dataset or forward-return experiment was opened or run. Current product correctness and qualified predictiveness remain distinct implementation and research obligations.


## Accepted root precision amendment

For issuer-exclusion invariance, freeze the captured benchmark, membership, model parameters and all nonissuer inputs before perturbing the candidate across aliases. Raw leave-issuer-out constituents, weights and measures must remain unchanged; a separately recomputed benchmark-mediated effect must be identified and cannot count as independent issuer confirmation. Forecast qualification and withdrawal operate per head; unrelated qualified heads remain available. Fit calibrators on protocol-designated past training/calibration windows, never on the untouched test set, and evaluate calibration on held-out observations. These refinements are accepted C3 quantitative reasoning, not new empirical results or outcome access.
