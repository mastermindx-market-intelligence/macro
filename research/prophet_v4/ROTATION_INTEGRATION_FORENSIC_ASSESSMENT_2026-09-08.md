# Prophet rotation integration — forensic assessment and recovery delta

Date of assessment: 2026-09-08. Author: Sol. Operation: `prophet-rotation-assessment-20260908-sol-001`.

**Disposition: verified source/artifact findings plus a recommended recovery sequence. Not a new Prophet version, not an implementation completion, not a live ranking change, and not a worker assignment.**

## 1. Outcome and executive finding

The user job is to discover an emerging sector or industry move, identify suitable companies before a late confirmation funnel hides the opportunity, distinguish research attention from an entry actually available now, and receive continuing instructions about expiration, invalidation, deterioration and an existing position. Earlier discovery must be evaluated alongside false starts, adverse excursion, transaction costs and the practical ability to exit; an earlier alert is not automatically a better trade.

The machine job is to connect existing market, sector, theme, company, entry, plan and risk owners through their existing identities, clocks and correction paths. The moat is the combination of differentiated evidence, timely detection, usable decision support and a measured learning loop, not another composite score or another dashboard.

The central finding is **partial integration and broken decision coherence**, not an absence of intelligent engines. China already has a theme-timing component and a separate intelligence-first ordering design, but the inspected current artifact is running the old ordering. The US live ranker explicitly lacks an active theme-structure family and a fundamental-quality family; macro regime is reserved for interactions/routing rather than cross-sectional voting. Existing lifecycle and management machinery exists, but the complete authoritative entry/withdrawal/product contract is unfinished. HK and Canada have different authority and validation states and must not be represented as equivalent copies of US Prophet.

We should integrate the suite, but not by adding points to every stock in a green sector. A relative leader can still be falling in absolute price, a sector turn can precede or outlast an individual stock's entry, and an attractive company can be temporarily unenterable. Those distinctions must survive integration.

## 2. Evidence boundary and exact pins

Procedure: protected `mastermindx-market-intelligence/Mastermind@2bf0266d5476c8e75dae4afa87cca67a8f12a838`; `docs/sol_skills/INDEX.md`, schema `mastermind.sol_skillpack.v1`, version 1.0.1, minimum bootstrap major 1. COLD_START, RECONCILE_STATE and CLOSEOUT were read at that same commit. The source pin was rechecked during continuation.

Implementation and committed-artifact observation: `mastermindx-market-intelligence/macro@eb9e91961ddc4f3043d0dad358602525e66eccda`, tree `ca30ef120ab7d7dca0396e6b04e5a4c04658e23f`. Main was rechecked during continuation and remained at that SHA. Local working-tree HEAD was not used as implementation truth: successful read-only probes used `git show <exact SHA>:<path>`.

Sources include the Chairman's supplied screenshots, immutable engine/builder files, four committed board artifacts, China rotation and sector-central artifacts, current GitHub issues/PRs, current Agent OS records and relevant historical postmortems. The artifact observations below are **not authenticated production-byte acceptance**. The screenshots support the reported UI failure but do not prove every current private API response. The available Opera connector returned browser-not-connected; no authenticated end-to-end browser proof was obtained. A later optional host diagnostic was blocked before execution; its attempted parquet/detail expansion is not evidence. No blocked command was retried through another carrier.

No live score, threshold, model, gate, size, order, production service, generated data, worker process or existing source branch was modified by the investigation. No sealed US comparative W3 outcome study was opened. An older Executive read was explicitly fixture/degraded and is not production Job/Worker liveness evidence.

## 3. Verified findings

### F1 — China V4 intelligence ordering is present in code but inactive in the inspected board

`site/factordata/china_standouts.json`, as_of 2026-09-07, declares `board_definition=cn_prophet_v4`. Its actual ordering receipt says:

```text
requested_order_basis = intel_interest_then_v3_score
effective_order_basis = cn_prophet_v3_score
order_mode = v3_coverage_fallback
intel_order_active = false
fallback_reason = incomplete_intel_interest_coverage
ranked rows = 1620
measured intelligence rows = 1616
unavailable rows = 4
unavailable reason = no_edge_evidence (4)
```

The requested and effective methods are different. This is not speculation based on a version label: the artifact discloses the fallback. `engine/china_board_rank.py:528-596` requires every ranked row to have a finite measured intelligence score. `scripts/build_china_library.py:3387-3440` builds the interest map for the candidate rows and attaches it before scoring. A measured 0.0 is legitimate; missing evidence is not zero.

The top five featured names in this artifact have intelligence scores 3.31, 43.22, 0.0, 0.0 and 15.81, while their legacy Prophet scores are 91.95, 90.86, 88.58, 86.95 and 85.4. This explains how the screen can look strongly ranked without actually using its intended intelligence-first ordering. It does not show that the hypothetical intelligence order would have made money.

`engine/china_intel_interest.py:284-314` defines `no_edge_evidence` as a leading desk observation without enough price/overhang/crowding evidence to compute the remaining-edge component. Its trajectory loader delegates to the existing China Intelligence price reader. The exact identities and upstream failure mechanisms of the four unavailable rows remain unresolved: the optional full-ledger probe did not complete. Do not claim they are ineligible, repairable price gaps, or bad names until their actual records are inspected.

**First source repair candidate:** restore genuine missing upstream evidence, where legitimately available, without changing the ranker. Reconsidering the global fallback denominator is a separate method decision. Never manufacture four zeros, silently drop four names, mix incomparable scores, or rename a fallback bake as intelligence-active.

### F2 — China is not wholly disconnected from sector/theme intelligence

`engine/china_board_rank.py` already gives `theme_timing` 15 points within the existing heuristic. Early basket phase plus rising oscillator, or a WARMING narrative state, can contribute through this specific channel. `sector_turn` itself remains zero-authority in that scorer. Intelligence interest is a separate ordering input, not an extra addition to the same score.

The four canonical published lanes contain 84 unique rows: 24 featured, 37 more_actionable, 18 late_or_unfillable and 5 forming. Only 15 of those 84 carry `basket_cycle`; all 15 joined cycle records are dated 2026-09-04 while the board is dated 2026-09-07. This is a measured coverage/clock gap, not proof that the source is unlawfully stale: its intended cadence and allowed lag still need reconciliation. Narrative coverage is a different channel and must not be confused with basket-cycle coverage.

The China rotation artifact contains 233 subsectors and 22 themes for 2026-09-07. The sector-central artifact contains 31 sectors and 22 baskets. The ETF modal, Shenwan sector table, curated baskets and THS concepts therefore do not describe one interchangeable population. Some rotation `members` lists are display samples: the Duty-Free Retail row reports 11 members but serializes eight. Do not use that displayed list as the complete membership universe for recall statistics or candidate intake.

### F3 — Candidate/featured/live labels are not equivalent to new-entry availability

In the China featured lane, the underlying `entry_signal.status` distribution is:

```text
buy_now: 7
partial: 7
bounce_wait: 8
wait_pullback: 2
```

Thus ten of the 24 featured rows explicitly describe waiting rather than an unconditional present entry. The first five shown in the artifact all carry either `wait_pullback` or `bounce_wait`. The screenshot's broad Live signals/glow language needs reconciliation with these actual owner states. Do not treat a featured flag, `stage=ENTRY`, a high priority number, or a raw eligible count as proof of enterability.

The US artifact has 65 rows in its legacy `buy` array and seven featured rows; the seven include three `partial`, one `buy_now` and three `bounce_wait`. This is another population-versus-action distinction, not proof that all 65 are current buys.

The live-state predecessor is also explicit: `engine/prophet_live/live_states.py` defines `near` as inside the probed band but below the trigger, or not yet debounce-confirmed. `forming` is the state in which the gate is satisfied at the observed price. China reuses these public states with market-specific overlays. A current browser test is still required to prove exactly which live states receive the glow; the screenshot alone cannot establish the JavaScript predicate.

**Immediate product requirement:** the most prominent instruction must answer a single question for a named strategy and timestamp. A waiting candidate may remain visible and important without being colored or described as an entry open now. Distinguish data unavailable from invalidated, and distinguish no new entry from an instruction to exit an existing position.

### F4 — US cross-family intelligence is thinner than the broader estate

`site/factordata/us_standouts.json`, as_of 2026-09-04, reports `us_prophet_v3`. Its active families are F1 technical confluence, F2 momentum/extension, F4 catalyst/event, F5 flow/positioning and F8 attention/crowding. It reports F3 theme structure, F6 macro regime and F7 fundamental quality as abstaining.

`engine/us_prophet_fusion.py:166-202` explains why. F3 has no registered theme/basket/relay evidence columns in the ranking frame. F7 has no admissible fundamental-quality member in that frame. F6 is structurally excluded because a single market-wide value shared by all stocks cannot differentiate their cross-sectional rank; it belongs in a router or exposure interaction.

This does not imply that macro or theme information is absent everywhere in the product. Existing conviction, spotlight, theme chips and other gates can contain context. The specific verified defect in integration is that these rich upstream observations do not become the differentiated company-level evidence the current canonical fusion ranker would need. Its construction remains an unfitted, equal-weight family vote, not a calibrated return forecast.

The correct extension is not a constant hawkishness bonus or penalty. It is a point-in-time combination of the current macro scenario and each company's economic exposures, earnings/cash-flow trajectory, valuation sensitivity and market-native evidence, introduced under the existing Fusion promotion law. The Chairman's rates/semiconductors/miners/crypto example is a testable scenario, not an invariant to hard-code.

### F5 — HK and Canada are not equally mature signal systems

The HK artifact is `hk_prophet_v2`, as_of 2026-09-07, with six buy-lane and three featured rows. Its current priority heuristic excludes theme and sector-turn score authority. The receipt reports unknown extension for all six rows, including three featured rows; current source law explicitly permits unknown extension with disclosure. That is a meaningful data-quality/UX limitation to assess, not evidence that the existing code violates a fail-closed rule it never claimed.

Canada is `ca_prophet_branch_b_v1`, as_of 2026-09-04, with `authority=screen` and `official_pick_authority=false`. The ten rows in its legacy `buy` key are a screening population: two partial, six await_confluence and two extended. This must not be marketed as ten validated actionable recommendations. Existing HK/Canada shadow and era-clean evaluation work should be reused, not reset or pooled with prior definitions.

Assess freshness on each exchange's session calendar and source cadence, not the wall-clock difference between September 4 and September 7.

### F6 — Exit/withdrawal machinery exists, but the complete user journey is unfinished

The estate already includes Prophet plan state, `engine/prophet_management.py`, stop/zone geometry, intraday faded/at_risk states, and market-native live overlays. Management state is explicitly separate from pick ranking. Therefore the remedy is not a new exit engine beside the old one.

The missing product contract is a continuous explanation of whether a signal remains valid, whether an entry is still open, what changed, and what an existing holder should monitor. It must distinguish an expired entry window, a retracted source trigger, thesis deterioration, a price invalidator, a normal pullback, a position-management event, and unreadable data. A removed card is not an adequate withdrawal notice.

Existing issue #6805 correctly names B2 correction-safe evidence, B3 independent lifecycle/emergence/maturity axes, and B4 one deterministic Availability authority. These canonical capabilities remain SPEC_ONLY/NOT_BUILT in that source; their predecessors are not completion.

### F7 — Prior upgrades have not all vanished; the portfolio is fragmented and records lag implementation

Current GitHub issue #6797 identifies D5 implementation PR #6705 as merged at `f4fbfa19f4e8e9f02efb320c93aecd21099bb8ce`, with authenticated positive and typed-unresolved production proof still owed. The existing workstream text still contains a pre-delivery next action saying D5 is unmerged. GitHub owns merge truth. Reconcile the record instead of recommissioning the same implementation.

Issue #6817 already owns the four-market cockpit recovery. PR #6832 is an open Draft/HOLD first-frame repair, not a completed intelligence or lifecycle upgrade. Its latest inspected Slack carrier includes a separately started test-only release-guard repair, with no later result in that inspected tail. Do not take over its branch or infer abandonment from elapsed time. PR #6954 is another existing recovery/continuity records carrier and must be collision-checked before changes to shared program records.

Issue #6805 is an existing Entry Truth architecture carrier, not completed B2/B3/B4 code. D5 production proof must not serialize unrelated B2/B3 work or China upstream repair. First-frame polish must not become the completion criterion for rotation intelligence.

The July 14 and July 16 rotation-miss postmortems already documented the same classes: different clocks, different populations, buried fast evidence, incompatible action language and context that did not reach useful decisions. These are historical source findings, not fresh performance validation of today's engines. The important organizational conclusion is to close the last producer-to-user connection rather than generate another replacement roadmap.

## 4. Capability ledger at this evidence pin

| Capability | State | Boundary |
|---|---|---|
| Rich China sector/basket/concept observations | PARTIAL | Built and visible in supplied screenshots; coverage, clock and predictive authority differ by producer |
| China bounded theme-timing score channel | PARTIAL | Implemented; sparse basket-cycle joins in the inspected published population |
| China intelligence-first current ordering | DARK_OR_DISCONNECTED | Implemented, but the inspected bake is explicitly in v3 coverage fallback |
| US canonical family ranker | PARTIAL | Five active families; no active F3/F7 and no differentiated macro router in this ranking contract |
| HK/CA parity with a proven US/CN investment model | NOT_BUILT | Market-native screens/heuristics and shadow studies are not transferable validation |
| Common authoritative entry/withdrawal workflow | SPEC_ONLY | Existing #6805 plus predecessors; no acceptance of canonical B2/B3/B4 in this assessment |
| Existing stop/management/live-state components | PARTIAL | Present in code; complete cross-market product journey not proven |
| Four-market cockpit recovery | BUILT_NOT_PROVEN | Existing bounded first-frame work is held; full program remains product-unaccepted |
| Better earlier net outcomes from a new integrated model | NOT_BUILT | Requires predeclared replay and prospective evaluation; no alpha improvement claimed |

The ledger intentionally separates code, committed output, transport receipts, served production, product acceptance and predictive evidence.

## 5. Recommended connected workflow, not one giant score

Use the existing authority chain:

```text
market-native sector/theme observation and transitions
  -> point-in-time constituent/issuer exposure links
  -> existing candidate owner: research nomination + evidence attachment
  -> existing company evidence/Fusion owner: differentiated priority
  -> existing entry owner: deterministic strategy-specific availability
  -> existing plan/portfolio owner: monitoring, invalidation and management
  -> existing publication/alert owners: visible transitions and delivery
  -> existing evaluation owner: decision-time and forward outcome measurement
```

The connection should preserve at least four independent questions: what is emerging; why this company; whether entry is available now; and whether a held position's thesis or risk state has changed. It should retain sector, industry, concept and curated basket identities rather than force them into a single label.

A transition such as weak-and-falling to improving should cause a bounded reevaluation of the actual constituent universe and existing candidate episodes. It need not create an order, a new plan, a new episode identity, or a higher live score. A developing rotation should appear in a research/early-discovery lane before entry confirmation, while an unavailable trade remains unavailable. Production reranking or new signal authority follows the existing per-market validation/promotion contract.

For one security in several themes, retain the relevant memberships and their point-in-time provenance. Do not award several independent votes for the same underlying price move echoed by an ETF, basket, breadth calculation and a summary. Distinguish absolute return, market beta, group return and stock-specific contribution: stripping the group effect everywhere can erase the very sector rotation the user is trying to participate in, while attributing it all to stock-selection alpha is equally wrong.

Macro scenarios should interact with exposures rather than dictate sector allocations. For example, a rates shock should lead the system to examine profitability, revisions, valuation, refinancing exposure, pricing power, currency and demand sensitivity where supported. The direction and usefulness of those interactions must be measured, not assumed from the current narrative. LLMs may synthesize evidence and explain competing hypotheses; they do not independently set rank, size, entry, stop or order authority.

## 6. Recovery sequence with observable returns

### A. Contain misleading action semantics, through existing cockpit and Entry Truth owners

Deliver one useful slice in which the primary candidate instruction, its entry details and its current state agree. Preserve discovery visibility; do not solve the contradiction by hiding all waiting candidates. Existing-entry geometry and live-state owners remain the calculation sources. New copy alone must not assert B4 authority before B4 exists.

Proof: actual featured-but-waiting examples, stale quotes, unknown extension, partial data, trigger failure, expiry and a held-position case through a real entitled browser. Assert that waiting/unavailable is never rendered as an open entry. Show the timestamp, strategy/horizon, next condition and reason for change. No ranking retune is needed to make truthful action language useful.

### B. Repair China evidence liveness without changing the formula

Identify the exact four unavailable interest records and trace their producer inputs. Recover genuine missing evidence through the accepted readers if available; otherwise preserve typed missingness and accurately display fallback. Quantify which current eligible/featured rows actually depend on the coverage decision before proposing a denominator change.

Proof: the same natural producer path emits an honest requested/effective ordering receipt; restored data activates the existing order only when its existing requirements are satisfied; missing, malformed, measured-zero and source-correction controls behave correctly; served order matches its disclosed method. This proves method activation, not improved returns.

### C. Connect a real rotation to the existing candidate workflow

Choose one China group with complete lawful member coverage and one US group supported by the existing graph/identity owner. Publish a research-only view of newly strengthening groups and their actual current candidate members, including members not yet admitted by the slow entry gate. Show the full funnel: source members, identity-resolved members, scanned members, early candidates, entry-open candidates, excluded names and typed reasons. A healthy zero must be distinguishable from disconnected coverage.

Proof: a real owner transition changes a real candidate projection, links back to the exact sector observation, and is visible in the existing cockpit. A stale group observation, retracted transition, membership correction and missing quote must not fabricate an entry. Start with one market per independently useful PR; common contracts do not imply common factor weights.

### D. Complete signal life and withdrawal, reusing B2/B3/B4 and plan management

Adopt and reconcile existing episode, entry, live-state and management predecessors. Track source event time, first observed time, first user publication, current valid-until/invalidator, and correction/withdrawal. An entry window can close while a longer thesis remains valid; an existing holding can remain hold/no-add while a new purchase is refused. Reentry must follow a versioned policy and preserve old decisions rather than reset history.

Proof: an actual published opportunity moves from research to entry availability, then to an unavailable/expired/invalidated state with a visible reason and event history. An existing position receives its separate management projection. The existing alert plane delivers qualifying state changes without repeated copies or silent disappearance.

### E. Earn differentiated sector/macro/company ranking authority

Extend the existing Fusion registry and market-native China/HK/Canada research lanes. Supply real theme-structure and quality evidence, not placeholders. Start with a transparent baseline, add contextual exposure interactions only when estimable, and keep challenger outputs separate from incumbent authority. Do not give every new family an automatic equal vote merely because a producer was wired.

Proof: point-in-time replay, family/lineage ablations, realistic entry and exit assumptions, forward paired observations and market-specific promotion. Only after these gates can the new evidence change live rank, gate or size. More intelligent explanations can ship earlier without pretending they prove alpha.

### F. Extend the accepted vertical market by market

Apply the same user grammar to HK and Canada but keep their benchmark, instrument identity, session clock, liquidity and current screen authority explicit. Require native candidate/event ownership; U.S. B1 is not a global episode registry. Do not transplant US factor weights or China calibration. Do not reset existing historical or shadow eras to make the scorecard look clean.

## 7. Evaluation: earlier, useful and safer rather than simply noisier

Pre-register the hypothesis and target population before outcome inspection. Compare the incumbent with: rotation discovery alone, stock-entry improvement alone, a simple sector/industry momentum baseline, the full proposed integration, and each important family removed. Measure both group selection and company selection within the group so sector beta is not mislabeled as company alpha.

Primary outcomes should include detection-to-user latency; recall near a causally defined rotation onset; median and tail lead time relative to the current board; false-start rate; price extension and remaining risk/reward at first actionable display; maximum adverse and favorable excursion after the first actually tradable observation; net expectancy and drawdown after realistic costs; missed-rotation opportunity cost; invalidation-to-user latency; stale active-signal duration; and alert fatigue. Report denominators, abstentions and confidence intervals. Tune neither to one winning screenshot nor to a selected handful of missed winners.

Use original publication and observation clocks, historical constituent membership, source revisions and corporate-action basis. A retrospective bottom marker is not what a user knew in real time. No centered/smoothed future-looking cycle marker may determine decision-time onset. No same-bar close fill unless that execution was genuinely available. Model gaps, illiquidity, limits, suspensions and venue-specific restrictions under current source rules. Keep current-definition, reconstructed and prospective cohorts separate.

The inspected China track artifact reports 75 matured current-definition observations across five board days, 10-session excess expectancy -0.5%, profit factor 0.85 and a wide expectancy interval of -3.18% to +2.31%. This is a concern and a reason to measure carefully, not a statistically established description of every user's P&L or proof that a particular replacement works. It is not a US W3 comparative outcome read.

A price stop is an invalidation/trigger policy, not a guaranteed exit price. The product must not promise that early unrealized gains provide permanent protection. Investor.gov explicitly warns that stop execution can differ materially from the stop price and that a stop-limit may not execute.

## 8. Research and product references

Moskowitz and Grinblatt's industry-momentum research supports investigating group information in stock selection, but its intermediate-horizon results do not validate a five-day China rotation alert or this implementation. Daniel and Moskowitz's momentum-crash research is a reminder that recent strength can fail badly in particular regimes. StockCharts' own RRG documentation explicitly treats rotation graphs as a visualization, not a predefined trading system. These references support a measured investigation, not copying proprietary formulas, branding or datasets.

Useful reference workflows to preserve with original implementation are: a sector map with tails and benchmark context; a complete constituent drill-down; a watch condition distinct from an entry alert; saved opportunities with state-change history; and a clear invalidator/expiry. They should converge in the existing cockpit, not require another page or another independent monitoring service.

Primary external sources consulted:

- https://www.aqr.com/Insights/Research/Journal-Article/Do-Industries-Explain-Momentum
- https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146
- https://www.aqr.com/Insights/Research/Journal-Article/Momentum-Crashes
- https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts
- https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15

## 9. Continuation and ownership boundaries

Sol owns the product outcome, cross-system design and final acceptance. Preserve existing source writers and native operation bindings. The integration umbrella remains WS:PROPHET-US-V4-RECOVERY; it consumes existing US Entry Timing, Conditional Fusion, Radar, Identity, GMI, Earnings and Evaluation owners. HK/Canada reuse WS:PROPHET-HK-CA-REVAMP. Exact China code/organizational writer custody must be recovered before a China modification; a similar workstream title is not sufficient authority.

The next implementation commission is not created by this document. No concrete worker is assigned here; no ACK, START, runtime Job, watcher or background execution is claimed. Normal unbound work stays WAITING_CAPACITY/needs_placement in existing projections; the Chairman is not asked to allocate routine accounts. Source safety and permission refusals remain fences, not reasons to switch carriers or borrow another worker's worktree.

Before any source change, read the current owning operation, current protected Skillpack and current branch/path/effect state. Keep the existing #6832 repair sticky until its current owner reconciles it. Reconcile D5's stale organizational next action to merged implementation plus proof owed. Do not let the D5 browser gate block independent Entry Truth archaeology or China evidence diagnosis.

**Exact next bounded action:** identify and explain the four China `no_edge_evidence` rows under the existing source owner, including their eligibility and whether the missing inputs are genuinely recoverable; return a minimal source-repair proposal or an explicit method-decision request. In parallel, the current Entry Truth/cockpit owners should use the verified featured-but-waiting cases as mandatory regression fixtures. Neither path may silently change rank/entry/size authority.

A later handoff must include mission, why it matters, exact authority/source precedence, current state and PRs, scope/non-goals, complete normal and degraded user journeys, identity/time/null/correction behavior, deterministic versus statistical/model method, ordered steps, acceptance/browser proof, stop condition and exact continuation. Acceptance is a demonstrated user capability, not another architecture document.

## 10. Source index for reproduction

All file paths below refer to Macro commit `eb9e91961ddc4f3043d0dad358602525e66eccda` unless explicitly noted.

- `site/factordata/china_standouts.json`: ordering, input_coverage, lane_counts, individual entry_signal.status, basket_cycle, track_ledger.
- `site/factordata/us_standouts.json`: ranking.fusion, buy/featured, entry_signal.status.
- `site/factordata/hk_standouts.json`: ranking, extension coverage, featured and market-native evidence.
- `site/factordata/canada_standouts.json`: board_definition, authority, official_pick_authority, legacy population and entry states.
- `site/marketdata/subsector_rotation_china.json`: n_subsectors, themes, actual member-list length versus n_members.
- `site/chinasectordata/sector_central.json`: sector/basket populations and state/conviction decomposition.
- `engine/china_board_rank.py:1-76,119-187,338-410,508-596,762-902,1211-1393`.
- `engine/china_intel_interest.py:284-314,402-467`.
- `scripts/build_china_library.py:3079-3090,3194-3246,3387-3440,3969-3980`.
- `engine/us_prophet_fusion.py:1-45,166-202`; `engine/us_board_rank.py` theme linkage and canonical sort/feature rules.
- `engine/prophet_live/live_states.py:1-45`; `engine/prophet_live/cn_states.py:1-21`; `engine/prophet_management.py:1-21`.
- `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md`; `WS-PROPHET-CONDITIONAL-FUSION.md`; `WS-PROPHET-US-ENTRY-TIMING.md`; `WS-PROPHET-HK-CA-REVAMP.md`.
- `research/prophet_v4/PROPHET_STRATEGY_PLATFORM_AND_CYCLE_CAPTURE_ARCHITECTURE_FREEZE_2026-08-30.md` and its owner-boundary amendment: preserve existing Long-Hold, Thesis Funnel, Winner Autopsy and market-native identity owners.
- `research/POSTMORTEM_20260714_ROTATION_MISS_BY_FABLE.md`; `research/POSTMORTEM_20260716_DEFENSIVE_ROTATION_MISS_BY_FABLE.md`: historical architectural failure classes only.
- Current GitHub carriers: Macro #6797/#6705 (D5), #6805 (Entry Truth), #6817/#6832 (cockpit), #6954 (continuity records). Existing Slack repair tail inspected at C0BSBM78V1N/1788798247.628639; no execution state is inferred from transport alone.

## 11. Completion boundary for this assessment

Completed: intent recovery; pinned source/artifact inspection; four-market method and action-state census; identification of the actual China fallback; separation of US missing evidence from legitimate macro cross-sectional exclusion; recovery of existing programs; and a bounded recommended recovery delta.

Not completed: exact four-row upstream root cause; full point-in-time rotation-to-stock recall census; authenticated current production-byte and browser matrix; implementation or release; independently validated return improvement; worker placement or durable unattended continuation. These remain explicit next actions, not hidden behind the report's existence.
