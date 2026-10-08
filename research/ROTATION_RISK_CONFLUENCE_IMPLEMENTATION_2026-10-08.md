# Rotation and risk confluence — implementation master plan

Operation: rotation-risk-confluence-20261008. Chairman instruction: assess, architect, implement and integrate the rotation/risk connection across the existing system. Source pins: Macro 7e6ce338a9f88aaa60834bdeaf5ee2fe90dab477; Terminal 54f97dda68a76a55ba0813afc9433ef54aaf401c; Mastermind implementation f74e912d3efa3b67cae40ba04f9e558d579096e9. Existing program homes: Rotation Command / Leadership Migration (Mastermind #1194) and WS:GREY-DEER-RISK-INTELLIGENCE. This document is a source design and acceptance plan, not a new workstream, risk authority, or runtime ledger.

## 0. Acceptance gates

The work is not complete merely because a detector or document exists.

1. Existing native market-state, rotation, and policy outputs retain their independent meanings and authorities. No universal risk score, multiplied conviction, automatic exits, ranking change, or newly promoted capital gate.
2. Ratio Lens computes all historical observations only from source sessions at or before the requested cutoff. Reconstructed observations are never described as historically available without a recorded availability clock.
3. The existing Rotation Command artifact includes a separate early relative-strength context. Confirmed events remain distinct. A relative defensive gain can occur while both legs rise or while the receiver falls less; neither proves distribution, net fund inflow, or a same-investor transfer.
4. The canonical Risk Envelope carries the market backdrop, rotation context, recorded transition attribution, source clocks, and a dependency audit. Repeated evidence cannot increase a score or audit count. Unknown lineage remains unknown.
5. Macro's existing Risk Radar details, shared Neural Web world state, Brain/Cortex grounding, Terminal's existing market-risk bridge, Oracle risk chip, Copilot tool, and relevant sector context must consume the same native facts. The interface cannot silently drop the new context. Portfolio consumes the optional native envelope through its existing Neural Web context reader; its decision_signals arithmetic is unchanged.
6. Missing, stale, future, malformed, and revised inputs have explicit behavior. A fresh build timestamp cannot refresh old source observations. Inactive live overlays cannot replace settled explanations.
7. Tests cover the real producer-to-consumer route, duplicate/permutation invariance, dependency cycles and transitive overlap, stale/future rejection, null versus zero, unchanged policy and severity, and healthy rotation under Risk-on.
8. UI uses existing components/tokens in existing information locations, with EN/ZH, light/dark and responsive checks. Technical lineage lives in detail, not a new prominent warning badge.
9. Independently review changed semantics, conclude required CI, merge through existing source gates and verify delivered bytes/behavior. Source acceptance and production proof are separate receipts.

## 1. Evidence and motivating defects

The Oct 5–8 investigation supports an early defensive relative-strength watch, not proof that one institution sold technology and purchased defensives. WMT/COST/XLP underperformed QQQ on Monday; the stronger relative evidence emerged Tuesday. FINRA is unsigned, WMT's participation anomaly was not shared by COST, contemporaneous options/skew coverage was inadequate, and issuer-derived XLP redemptions alongside XLK creations contradicted a simple fund-flow story.

The first-writer market-state history was RISK_ON 61 on Sep 29, MIXED 54 on Sep 30, and remained Mixed during the rally (48 Oct 5; 51 Oct 6). The initial change was primarily the risk-appetite component. It must therefore enter the episode as a prior backdrop; the settled record does not establish a new event-week flip or minute of browser delivery.

Verified source defects:
- Terminal's bridge emits flat market_risk/v1 while its Copilot tool and Oracle chip expect nested raw display fields.
- The bridge ignores native freshness and may mix an inactive live headline with a settled verdict.
- Ratio Lens's requested as_of labels output without slicing prices before computation.
- Rotation and market context are compacted through existing readers that currently discard relevant attribution.
- Existing latest-table flow receipts and chain selection can admit future records during historical reconstruction.
- Adjacent #8412 owns scratch alert-write isolation; #8476 owns sector_cycles history. Do not overwrite those carriers or silently recreate their patches.

## 2. Architecture and ownership

The dependency graph is one-way:

qualified source observations -> existing source-native organs -> Risk Envelope -> product and machine readers.

Market State owns the measured RISK_ON/MIXED/RISK_OFF reading. Ratio Lens owns ratio mathematics. Rotation Command owns relative leadership observations and confirmed rotation events. Risk Envelope owns the descriptive combined view. Existing individual policy owners retain actionability and capital authority. Terminal mirrors; it does not recompute market intelligence. Brain and Cortex explain source artifacts; they cannot originate scores or elevate authority.

The frozen legacy risk_state fused score remains compatibility-only and is not a model for this integration. Its existing overlapping inputs are recorded for a separately qualified review, not silently retuned here. The Risk Envelope continues selecting the maximum stage individually justified by a competent source; two FRAGILE reads never make TRANSMITTING.

## 3. Rotation context contract

Add an early_context object to rotation_events.v1. Its schema is rotation_early_context/v1, with a definition_id, as_of, produced_at/availability metadata when actually known, display_only=true, state, reason_codes, coverage, pair observations, and source lineage.

Pair observations are descriptive short-horizon returns computed in Ratio Lens from the registered pair definitions, with inner-joined source sessions and no forward filling. Carry 1/2/5/20-session relative and absolute leg returns, their actual window endpoints, direction and BOTH_UP / RECEIVER_UP_DONOR_DOWN / BOTH_DOWN / RECEIVER_DOWN_DONOR_UP shape. Registered defensive sectors and WMT/COST company comparisons are separate categories from DIA/IWM/RSP broadening proxies. None of the broad index proxies asserts a prior-loser constituent portfolio.

Early state is a transparent description of a positive short-horizon relative shift, not a calibrated forecast or automatic trade alert. Missing or stale legs make that pair unknown. Existing confirmed active events and their severity retain their original rules and lifecycle. Early context never enters theme_context's sector_rotation_agrees confirmation bit, the confirmed event ledger, or a severity sum.

The exact short-horizon definition and category registry are versioned. Existing Ratio Lens state assignment and long-horizon coordinates do not change. An as_of cutoff applies before every pair computation, including long-horizon and basket paths.

## 4. Joint envelope and evidence dependency contract

Extend mastermind.risk_envelope/v1 additively with rotation_context and confluence. Rotation arrives as a ROLE_CONTEXT SourceRead; it cannot cast a hazard vote. The envelope carries the qualified native context and identifies whether the measured backdrop is Risk-on, Mixed, Risk-off, or unavailable.

Confluence is an evidence audit and explanation, not a confidence score or probability:
- state describes the combination of native readings, not a stronger severity;
- no arithmetic feeds measured_state, hazard_summary, policy_summary, authority, rank, or sizing;
- the absence of recorded overlap is never called statistical independence;
- conflicts and missing coverage remain visible.

SourceRead.detail.lineage contains definition_id, status (COMPLETE/PARTIAL/UNKNOWN), roots (stable economic observation identities), dependency_groups, and derived_from source IDs. Observation roots exclude publication/rebuild timestamps; revisions are separate identities. Pairwise relationships: SHARED when roots, dependencies, or ancestry overlap; DISTINCT_RECORDED_ROOTS only when both lineages are complete and disjoint; UNKNOWN otherwise. Compute shared connected components transitively. Exact aliases do not inflate component counts. If any incomplete lineage prevents a total, the nonredundant total is null and known clusters/unknown sources are still reported. Reject self/cyclic declared derivation rather than turning it into corroboration.

A broad price dependency group is deliberately conservative: XLP/XLK, breadth and a price-derived risk-appetite summary may describe one mechanism. Dark-pool participation is unsigned context, not a buying vote; options require genuine source freshness and qualification before any directional claim.

## 5. Market transition provenance

Carry native raw_score, score, verdict, capped, score_source, score_caps, score_ceiling, score_gap, overrides, components, vintages and freshness without reinterpretation. A transition requires two genuinely recorded ordered snapshots; current Mixed alone does not imply a previous Risk-on state.

Use the existing first-writer market_state forward log for before/after context. Surface the recorded date, previous/current state, unchanged-versus-transition, and native component movements. Do not backfill an envelope onset from a reconstructed source onset. A cap, data availability change, or revision cannot masquerade as independent deterioration. Same-day rebuilt snapshots remain separately attributable to the producer; no new forward ledger is created.

## 6. Integration and migration

Wave A — clock and adapter correctness:
- Terminal shared normalizer accepts canonical flat bridge plus explicitly labeled legacy nested compatibility.
- Ingest selects qualified settled/live source coherently, carries native provenance and optional envelope context, and fails closed on malformed/future clocks.
- Ratio Lens historical cutoffs are enforced before math.
- Rotation flow receipts reject future selections and label unavailable/stale, without pretending missing history was recovered. The separate options-chain selector repair is explicitly held by #8191; see §9.

Wave B — descriptive rotation context:
- Extend existing ratio owner and pair registry with explicit defensive and broadening comparisons.
- Extend rotation_events output and its existing compact reader, preserving confirmed-event rules.
- Add qualified optional rotation context to settled and live Risk Envelope builders without raising competence ceilings or bypassing live dwell.

Wave C — actual consumers:
- Extend the existing Risk Radar detail view, no new standalone dashboard panel.
- Extend the world-state owner's bounded summaries with envelope/rotation/native cause data; Cortex consumes the same world state.
- Reuse the existing Brain entitlement gate in both actual chat loops. Read the canonical context directly without a new cache; preserve raw tool reads for Cortex and redact the additions before guest tool access. Avoid the held #8257 market_packet and #8306 evidence owners.
- Extend Terminal's existing bridge, Oracle chip, Copilot and authenticated sector-intelligence route with the canonical context. Keep existing coordinates and ranking logic.
- Inspect Mastermind Portfolio consumers; mirror the descriptive envelope into existing context only where required, never arm posture_decider or create an execution rule.

Wave D — review and delivery:
- Run focused behavioral and round-trip tests; use motivating and negative-control fixtures.
- Review the implementation independently with adversarial duplication, timing and coverage cases.
- Publish source and durable program/decision records in their existing owners.
- Conclude CI and deliver through the existing git-gated release paths. Verify live artifacts and actual readers; report any exact external blocker without substituting code existence for delivery.

## 7. Counterfactual and research qualification

The October episode is a motivating case, not an independent validation set. Preserve the observed XLP-vs-tech shift, no blanket Dow/RUT prior-loser claim, and fund-flow counterevidence. Evaluate historical cutoff behavior using frozen fixtures with added post-cutoff shocks. Availability-aware studies must separately establish recorded_at/available_at; date truncation alone is not PIT.

Prospective signal promotion is a separate test: freeze definitions before outcomes, evaluate episodes and false positives, compare a price-only baseline against incremental qualified flow/credit/volatility evidence, account for overlapping windows and universe history, and keep uncalibrated scores out of sizing. No claim of guaranteed early detection, perfect operation, or predicted selloff is authorized by this source integration.

## 8. Source custody and release boundaries

Root owns this operation and final cross-system acceptance. Native child assignments are bounded local source work, not claimed Executive jobs. One isolated clean branch per repository was created from fresh defaults; primary checkouts and unrelated held branches are untouched. Workers do not merge or deploy their own first pass.

Existing holds and denials remain scoped to their exact operations. In particular the denied #8257 production artifact capture is not retried, repackaged or delegated. Source-only work does not depend on a writable Executive runtime. Release permission and actual release capability are checked at the concrete final action, with current source, CI, custody and deployment evidence.


## 9. Integration acceptance and explicit held repair

The owned Macro integration suites concluded with 289 passing tests and no failures (host process 92766). The broader rotation owner regression concluded 270 passing tests with 11 pre-existing artifact-dependent skips. These populations overlap and must not be summed. The registry validator accepts the existing 647 artifacts with zero violations; the work extends the registered `risk-envelope-settled`, `site-marketdata-rotation-events` and `market-state-forward-log` relationships rather than inventing artifact identities. The existing CI jobs now invoke the four new behavioral suites.

Independent reviewers corrected three classes of defects before acceptance: native source-clock formats and NYSE dates, live numerical provenance versus a debounced display label, and a fresh legacy wrapper without an observation clock. The common World State build CLI refreshes the existing envelope owner before composing its consumers; custom diagnostic output does not write the canonical envelope. This repairs the observed nightly/render ordering seam without another scheduler.

Terminal integrates the actual installed `ops/terminal-data` lane and manual refresh with the same bridge. It qualifies the native descriptive envelope independently, updates existing Oracle/Copilot/sector consumers, and leaves the 21/63-session coordinate mathematics intact. Source review and fixture browser tests do not prove production scheduler execution.

Prophet already exposes the shared risk detail through its existing board-wide B4 link to `macro.html#dlg-risk`, and entitled Prophet Brain explanations use the same guarded canonical context as the other Brain routes. Static plan thesis, origination, management state, ranks and population remain with their existing owners. No GD-6 policy sidecar is fabricated. A redundant static B4 summary is unnecessary for this descriptive integration.

### Held options selector: concrete handoff, no claimed repair

At the inspected `scripts/build_options_flow.py` source, `_chain_pair` can select the latest chain when every chain is later than the requested as-of date. The existing #8191 carrier is OPEN/DRAFT/HOLD at `6753d5622555e110a107bd4fd706f478f73b1d24`; its exact final regression and production-source inspection were denied, and its same-carrier receipt says ALL_SCOPED_LANES_BLOCKED. This operation does not edit that file, remove its CI marker, run the denied test set elsewhere, capture the denied data, or route around the hold.

The minimal pending owner repair is to return `(None, None, None, None)` when no admissible chain index exists, preserve the actual selected chain source date (currently discarded as `_gd`), and test empty, all-future, same/prior-session and appended-future cases after the authorized owner resolves the hold. The complete proposed cases and exact source observation are retained in the operation's independent flow review. They were not executed as a substitute for the denied validation.

Historical options/skew freshness and actual depth-of-book coverage remain data prerequisites. NBBO/trades do not become Level 2 merely because a consumer can read them. No options-position, dealer-gamma or institutional distribution confidence is promoted by this implementation.

## 10. Release and learning requirements

Implementation verification, protected-source publication, production deployment, scheduled observation and prospective forecasting evidence are separate states. Each repository release must bind its accepted head, concluded required checks, merge commit and normal deployment receipt. Actual source sessions and canonical bundle IDs must match in downstream readback where that read is permitted. A denied production capture stays denied even after source publication.

For prospective learning, use the existing Chronicle/Reflex/QLedger owners and the existing Grey Deer promotion gates. Record observations before outcomes; compare qualified incremental evidence against price-only descriptions; assess false positives and useful lead time by independent episodes. Do not create a duplicate ledger or claim this October motivating episode validates the detector. This implementation changes descriptive context and source integrity, not automated portfolio policy.
