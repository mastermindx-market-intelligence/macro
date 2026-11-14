COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: Designing a point-in-time risk-state system whose only modern test window was also its tuning window needs long, careful reasoning about validation design, state machines and hazard modelling at once.
WHY_NON_PRO_INSUFFICIENT: Faster modes have produced plans that quietly reuse in-sample evidence as proof; this turn must catch that failure on its own.
PRO_MODE_TASK_CLASS: CROSS_SYSTEM_ARCHITECTURE
EXPECTED_DURATION_MINUTES: 90
STOP_CONDITION: One complete master plan posted as a comment starting "PRO-RUN A" on the GitHub issue named below.

# PRO-RUN A — master plan: Risk Radar as a world-class risk-state awareness system

You are an independent architect. Write a master plan that stands alone. You will not see anyone else's plan.

## Read first (public repository mastermindx-market-intelligence/macro, branch fable/risk-radar-masterplan-20261112)
1. research/risk_radar/CENSUS_2026-11-12.md — measured facts about the system today, each with file and line. Treat it as your ground truth; verify anything you rely on heavily.
2. engine/risk_radar.py (the engine), engine/risk_envelope.py (the public envelope that carries state, hazard and policy as separate fields).
3. research/grey_deer/risk_radar_architecture_contract_20261017.md and agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md (the do_not_redo list, lines 75-81).
4. research/RISK_RADAR_TUNING.md and research/grey_deer/RISK_RADAR_*_RESULTS_*.md (what has already been measured).

## The situation in five lines
- Risk Radar today: 16 legs into 7 scare types, a 5-step ladder (calm/watch/caution/elevated/risk-off), a context gate, and a displayed pullback probability that its own audit calls a gradient, not calibrated odds.
- Its bands, weights, leg thresholds, gate and probability table were chosen on data that includes 2020 onward. The Chairman has ruled that 2020 onward is the product's test bed, with long history only a secondary stability read. So the main test window is already contaminated for the current definition.
- Its forward record has 79 rows (26 with prospective issue receipts) and zero alerts; a frozen readiness bar needs ≥252 receipt-bearing sessions.
- Users: a Macro dashboard (Chinese and English readers), a rotation-research desk that wants a dated risk state as a feature, Prophet (a ranking engine that may read an eligibility sidecar only), and a Shared Shell beta the system will slowly move to.
- Mission it serves: call sector and asset rotations and risk-on / risk-off pivots before they are obvious, without knife-catching.

## Answer these, concretely
1. **Target system.** Define the states (how many, what each means in words a user acts on), the transition hazard (what is forecast, over what horizon, in what units), what would change the call (named observable triggers per state, both directions), and repair / re-entry (when a risk-off state is over, and how to avoid both late re-entry and knife-catching). Keep state, hazard and capital policy as separate outputs.
2. **Inputs.** Which inputs carry information about risk that sector and index prices do not already carry (credit spreads and their velocity, rate volatility, funding and dollar liquidity, options-implied measures, breadth, cross-asset correlation, positioning, macro surprise, etc.)? For each: the evidence needed before it may move the state, and whether point-in-time history exists. Say which current legs you would drop.
3. **Validation when the test bed was also the tuning window.** Give a protocol that is honest: what can still be learned from 2020 onward (e.g. a fixed-rule replication with no re-tuning, simplicity priors, pre-2020 stability reads, synthetic or cross-market checks), what must wait for the forward record, the freeze procedure, what a version change does to the forward record, and how to prevent re-tuning by the back door (a self-retuning loop exists and has proposed changes 22 times, none applied).
4. **World class, in measurable terms.** Name the metrics and the bar for each: e.g. lead time versus drawdown onset, false-alarm rate per year, time spent in loud states, calibration error, Brier skill versus base rate, stability of the state (flip rate), re-entry timing after the trough, data-freshness and point-in-time guarantees, explanation quality. Give numbers a skeptic would accept.
5. **The four-second read.** What a user sees first, in one line and one badge, and the depth behind it.
6. **What to drop.** Elements that add noise, false precision or maintenance cost.
7. **Consumer contract.** A dated, versioned risk-state series that rotation research, Prophet (eligibility sidecar only) and the Shared Shell can read without recomputing: fields, as-of / issued-at semantics, revision rules, and what each consumer may and may not do with it.
8. **Build order.** Ordered slices, each small enough for one pull request, each with the proof that it worked.

## Hard limits (binding)
- Descriptive risk state never becomes automatic trading permission. Paper-only: no position sizing, no execution, no automatic exits.
- No single fused risk score in any authority path; state, hazard and policy stay separate.
- No new event store for risk episodes; no change to Prophet's ranking.
- Do not compute, or ask anyone to compute, any relation between a signal and future returns or outcomes on dates from 2024-01-02 onward. That hold-out is sealed. Reasoning about published facts in the census is fine.
- No secrets, account details or private paths in your answer.

## Return
Post your full answer as ONE comment on https://github.com/mastermindx-market-intelligence/macro/issues/11104. The comment must start with the line `PRO-RUN A`. Then, in order: a one-paragraph verdict; sections 1–8 above; a list of the facts you relied on with their file and line; a list of what you could not verify. If you cannot post to GitHub, put the same text in this chat as your final answer and say so on its first line.
