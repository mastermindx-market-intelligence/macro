# Proposed additive Risk Envelope contract — 2026-10-17

**Status: PROPOSED; NOT IMPLEMENTED.** Supporting annex to the existing Grey Deer continuation and architecture freeze. This proposal grants no predictive, warning, ranking, policy, allocation or execution authority.

Source baseline: Macro 3ab3382af89242c7b7fe8c65360bd883a7dd3504; Mastermind a552a5e506ae808efa575c2e13cb56f478c72b87; Terminal b8a694357e2c5cf7c2921d2260732b8a757a90d9. Findings and exact implementation links are in the [completed source audit](risk_radar_source_consumer_audit_20261017.md). Governing design remains the [existing Envelope freeze](https://github.com/mastermindx-market-intelligence/macro/blob/3ab3382af89242c7b7fe8c65360bd883a7dd3504/research/grey_deer/GREY_DEER_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE_2026-08-19.md).

## 1. Compatibility and ownership

Propose an optional exposure_assessments collection within the existing Envelope contract, subject to compatibility review. Preserve measured_state, hazard_summary, policy_summary, rotation_context, confluence, market_transition and their current meanings. Existing consumers retain their current outputs; they must not derive replacement headline states from the extension.

Keep envelope_may_rank, envelope_may_gate, envelope_may_size and envelope_may_execute false. Individual policies retain their own authority. Macro owns market intelligence; Portfolio owns mandates, book constraints, numerical allocation and execution. Prophet retains raw rank, admission and board bytes; any future eligibility disposition uses the existing board-hash-bound sidecar design.

Chronicle owns episode history, the Reflex Registry owns registered triggers, and QLedger owns claim/evidence lifecycle. Entries reference those owners; this annex introduces no alternate episode machine, trial ledger or policy registry. The existing #8132 warning path remains the single publisher, subject to its original custody and release constraints.

## 2. Exposure and horizon identity

Each assessment binds:

- exposure_id and type: country, index, sector, subsector, theme, factor or company; parent exposures and benchmark;
- membership_version and effective dates, historical-membership qualification, currency, hedging convention and price/total-return basis;
- horizon value, unit and role: observation lookback, forecast horizon or policy validity;
- source_session, decision_time, definition_id, source hashes and owner references.

A 21-session loss forecast cannot inherit the qualification of a monthly macro label. Current-cohort history remains current-cohort evidence. Missing members, unavailable prices and immature outcomes remain explicit denominators.

## 3. Independent assessment fields

Every field carries native values, evidence references, coverage, qualification and clocks. Null means unavailable or unqualified, accompanied by reasons; it never means calm.

| Field | Question and permissible content | Separate qualification |
|---|---|---|
| environment | What growth, inflation, liquidity and policy setting surrounds this exposure? | Native regime definition, release vintages and applicable country/horizon. |
| vulnerability | What could amplify a shock? Breadth concentration, leverage, positioning, valuation or funding dependence. | Observed condition versus validated future-loss association. |
| current_damage | What has already broken? Drawdown, trend/breadth loss, earnings impairment or funding stress. | Absolute/relative basis, peak/lookback definition, coverage and observation session. |
| propagation | Is damage reaching another exposure? Origin, recipient, channel, sequence and competing explanations. | Co-movement, directed predictive transmission and causal evidence are different grades. |
| future_loss | What additional loss is forecast from this decision origin? Target, threshold, horizon, probability/interval and baseline. | Exact model/surface, calibration population, out-of-sample evidence and maturity. Withhold unsupported numbers. |
| recovery | What is stabilizing, repairing or regaining leadership? Further-low risk and recovery opportunity remain distinct. | Observed stabilization, validated re-entry evidence and failed-recovery counterexamples. Declining hazard alone is not repair. |
| action_eligibility | Which source-supported actions may the established policy owner consider, and under what conditions? | Policy reference, authorized scope, entry condition, invalidation, expiry and evidence gaps. Numerical sizing stays outside this contract. |

Relative strength and absolute capital preservation require separate measures. Defensive outperformance while prices fall supports “falling less,” not inflows or preservation. Price ratios cannot establish investor transfers.

## 4. Clocks and evidence semantics

Each dependency preserves event_time, available_at/release_time, observed_at, produced_at, source_session and stale_after where applicable. A decision-time reconstruction admits only inputs available then. Publication time never refreshes source evidence. Corrections reference the superseded record and the affected claims through existing owners.

Qualification distinguishes: readable source; cadence freshness; feature availability; session compatibility; membership/PIT quality; historical source-family validation; exact-surface predictive calibration; and permitted consumer authority. Confidence must identify its target and derivation. Radar intensity divided by 100 is intensity metadata, not calibrated forecast confidence.

Independent fields may display different dated observations. A combined inference requires its declared dependencies to qualify; incompatible required sessions withhold that inference while preserving independently usable facts. Delayed macro releases retain their actual release clocks rather than pretending to be same-session prices.

Priority regression: October 16 Market State, October 15 Envelope and committed SPY history, and October 14 leadership observations must remain distinguishable. The newer regime snapshot may derive from an ephemeral price observation; its stamp alone cannot reproduce every component’s knowledge.

## 5. Exposure alerts and systemic escalation

Store exposure scope separately from escalation scope. A healthy SPY may coexist with severe technology damage and defensive strength. The intelligence should show both contained rotation and spreading danger as competing pathways, with the observations that would discriminate them.

Broad-index confirmation is a preregistered comparator for systemic escalation, not an automatic gate on independently qualified exposure evidence. Earlier exposure warnings require their own validation and policy/publisher admission. Neither systemic escalation nor early exposure-action authority is granted here.

## 6. Existing Paper experience and delivery

Retain Paper p1 artboard 1-0 as the primary experience and p6 A5I-0 as the observed-damage/forecast-withheld reference. Add explicit exposure, horizon and source dates; keep current damage, future loss and recovery visually separate. Surface material unavailable inputs and mixed sessions beside the conclusion. Forecast withholding must preserve useful observed facts and conditional next observations.

Paper’s current catalog reports accepted_for_write:false; this annex is a design specification only.

The single publisher should distinguish issued warning, below-threshold observation, expired warning and unavailable source. It preserves native scope, qualifications, source identity and policy references. Refresh long-open pages through the existing channel with single-flight requests, bounded deadlines, focus/visibility refresh and expiry handling. A transport failure cannot silently certify calm or keep an expired warning current. Dismissal and deduplication follow the existing publisher’s material-update identity.

Use current entitlements throughout. Premium evidence remains gated; any public summary requires its own approved field allowlist. Capture source event → qualification → publication → authenticated response → browser paint receipts, including the displayed exposure and clocks.

## 7. Proposed acceptance matrix

| Case | Required result |
|---|---|
| Mixed source sessions | October 16/15/14 evidence remains dated; unavailable joint inference cannot borrow the newest stamp. |
| Healthy index, damaged sector | Sector damage remains visible; no unsupported systemic escalation. |
| Benign broadening / contained rotation | Record the alternative, absolute returns and confirming observations; do not label contagion from ratios. |
| Defensive assets fall less | Relative opportunity remains separate from absolute preservation and fund-flow claims. |
| Missing required versus optional input | Withhold only affected conclusions; retain independently qualified facts and original missing-data reasons. |
| Forecast and confidence | Exact target/surface/evidence binds every numerical forecast; intensity and family approval do not substitute. |
| Rebound followed by new low | Stabilization and re-entry are graded separately; preserve failed recoveries and costs. |
| Lifecycle and authority | Existing owner references resolve; four Envelope flags remain false; Prophet board and Portfolio numerical outputs remain unchanged. |
| Browser left open, expiry, failed fetch | Material updates arrive without reload; expiry and unavailable states are visible; no duplicate publisher. |
| Entitlements and real delivery | Authorized user receives correct source-bound content; unauthorized access follows existing controls; production clocks reach actual paint. |

Source tests establish contract behavior only. Scientific acceptance additionally requires preregistered out-of-sample incremental value, calibration, lead time, false-alarm/missed-damage burden, whipsaws, recovery capture and costs at the declared exposure/horizon. Product acceptance requires real delivery evidence; preserved prior accepted proofs are not rerun without a changed risk.

