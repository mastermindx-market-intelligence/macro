# Policy Behavior Casebook — W1 Preregistration

**Program:** Policy Behavior / Revealed Preference  
**Date:** 2026-10-07  
**State:** PREREGISTERED RESEARCH DESIGN / ZERO AUTHORITY  
**Parent:** `POLICY_BEHAVIOR_REVEALED_PREFERENCE_MASTERPLAN_2026-10-07.md`

## Research question

Can a point-in-time model of **actions + constraints + revealed preference** predict policy and market outcomes more reliably than either:

- taking political / policy rhetoric literally; or
- automatically assuming the opposite of rhetoric?

The casebook is an evidence substrate for that comparison. It is not a hidden-intent oracle.

## Primary baseline race

Freeze three model families before outcome labeling:

### M0 — LITERAL

Use the contemporaneous stated message.

Allowed:
- official statement;
- speech;
- press conference;
- announced objective;
- explicit conditional commitment.

No inferred opposite.

### M1 — INVERTED

Use a mechanical contrarian baseline: invert the directional implication of M0 where a clean inversion exists.

This intentionally tests the naive rule “officials say X, so assume not-X.”

If no clean inversion exists, abstain.

### M2 — ACTIONS_CONSTRAINTS

Use only information known by the episode's decision cut:
- executed action;
- repeated prior choices;
- instrument selected;
- constraints;
- feasible alternatives;
- selective protection;
- counterparties;
- contemporaneous market pricing;
- prior revealed behavior.

Private motive may be represented as competing qualitative hypotheses but may not be injected as a known fact.

## Episode unit

One episode is a **decision-relevant policy / strategic-capital action** with one frozen decision cut.

Do not define an episode around a later market outcome.

Examples:
- Treasury pressure on BOJ;
- joint FX intervention;
- a Fed decision;
- an industrial-policy support agreement;
- a strategic company financing / buyback action when it is being studied as part of public-private market structure.

Repeated articles about one underlying event remain one episode.

## Required schema

Every admitted episode must contain:

### Identity and time
- `episode_id`
- `episode_family`
- `actor_ids`
- `institution_ids`
- `decision_cut_utc`
- `event_time_precision`
- `first_public_evidence_utc`
- `pit_certified`

### Source lineage
For each source:
- `source_id`
- publisher / originator
- URL / native document identity
- publication timestamp or best available precision
- primary / independent-reporting / research / commentary
- source family
- whether it was public before the decision cut
- correction / supersession state

Two websites repeating one Reuters report are one source family.

### Rhetoric
Each statement:
- text span or faithful paraphrase;
- timestamp;
- actor;
- `statement_type`:
  - PREFERENCE
  - FORECAST
  - CONDITIONAL_COMMITMENT
  - NEGOTIATING_THREAT
  - JUSTIFICATION
  - BLAME_ATTRIBUTION
  - OPERATIONAL_GUIDANCE
  - OTHER
- explicit horizon, if any;
- directional implication;
- ambiguity / conditionality.

### Actions
Each action:
- action type;
- instrument;
- announced / authorized / executed / completed;
- reversible / difficult-to-reverse;
- target / counterparty;
- amount / magnitude when supported;
- legal / institutional owner;
- mechanical transmission channels.

An authorization is not an execution receipt. A plan is not a completed flow.

### Constraints and alternatives
- contemporaneous domestic constraints;
- foreign / institutional constraints;
- political / legal constraints;
- market-functioning constraints;
- feasible alternatives known at the cut;
- evidence that an alternative was considered or unavailable, if known.

### Strategic distribution
- direct beneficiaries;
- indirect beneficiaries;
- burden bearers;
- selective relief / protection;
- whether the action changes effective financing cost, demand certainty, supply access or downside risk.

### Competing hypotheses
At least two for consequential episodes.

Each hypothesis carries:
- claim;
- evidence for;
- evidence against;
- assumptions;
- falsifiers;
- what new observation would materially re-rank it.

No episode may encode one motive as certain merely because it fits the outcome.

### Decision-time forecasts
M0 / M1 / M2 must each emit:
- target;
- horizon;
- directional or probabilistic forecast;
- confidence / probability;
- abstention state;
- exact inputs used.

### Outcomes
Stored **after** the decision-time block:
- policy outcome;
- rates / FX / inflation response;
- sector / market response;
- later revisions;
- later implementation evidence.

Outcome fields may never feed decision-time features.

## Target families

Evaluate separately.

### Policy
- next policy-rate direction at 1m / 3m / 6m;
- policy-decision surprise relative to pre-cut pricing.

### Rates
- 2y;
- 10y;
- real yield;
- inflation compensation;
- curve slope.

### FX
- DXY;
- USDJPY;
- JPY trade-weighted where available.

### Inflation / growth
- oil / commodity impulse;
- inflation expectation direction;
- growth-expectation direction.

### Capital allocation
- strategic-sector relative performance;
- revisions breadth;
- credit-spread change;
- breadth / leadership concentration.

No single “was the hidden plan correct?” outcome.

## Required controls

### Time controls
- all input clocks must be before the decision cut;
- later Reuters reconstruction may be used for source archaeology but not as a decision-time input unless its underlying fact was public then;
- corrected sources retain both what was knowable then and what is known now.

### Market controls
- pre-event expectations;
- market / sector state;
- rate regime;
- volatility;
- prior issuer / sector momentum.

### Common-calendar controls
For company / announcement episodes:
- earnings;
- investor day;
- conferences;
- product cycles;
- known regulatory deadlines;
- previously announced close dates.

### Source independence
Count:
- unique underlying facts;
- unique primary origins;
- genuinely independent observations.

Do not count syndication breadth as independent corroboration.

## Rhetoric–action divergence research fields

The casebook may calculate descriptive, non-authoritative features such as:
- `rhetoric_action_direction_relation = ALIGNED | DIVERGENT | MIXED | NOT_COMPARABLE`
- `action_persistence_after_cost_visible = YES | NO | UNKNOWN`
- `selective_relief_present = YES | NO | UNKNOWN`
- `alternative_lower_cost_path_visible = YES | NO | UNKNOWN`

Do **not** calculate a production “deception score,” “puppet score,” “coordination score,” or hidden-intent probability from these fields.

## U.S.–Japan special fields

For Japanese policy / FX episodes capture:
- BOJ domestic inflation / wage information available then;
- BOJ policy expectation before U.S. action;
- Japan MOF stated preference;
- Treasury / White House pressure;
- NY Fed operational involvement;
- intervention action;
- FIMA / dollar-liquidity option;
- JGB / OIS / USDJPY reaction;
- subsequent BOJ action.

The target is the incremental effect of external constraint on the feasible policy set.

## Strategic-announcement special fields

For tech / strategic-company events capture:
- scheduled vs discretionary;
- issuer drawdown before event;
- Nasdaq / sector stress before event;
- breadth;
- government-link evidence;
- financing-link evidence;
- event materiality;
- source independence;
- whether event changes expected cash flows or only attention / capital return;
- subsequent revisions and residual returns.

## Leakage guards

The W1 validator must reject or quarantine:
- later market outcomes inside `decision_time`;
- source timestamps later than the decision cut unless marked archaeology-only;
- deduplicated Reuters copies treated as separate evidence;
- event definitions chosen from subsequent price extremes;
- a “positive news” label inferred from subsequent returns;
- an action marked executed when only authorized or announced;
- a government relationship inferred solely because an issuer outperformed.

## Sample construction

Target **40–60 episodes** before the first baseline comparison.

Minimum composition:
- 8 U.S. Fed / Treasury rate-policy episodes;
- 8 U.S.–Japan / FX / monetary-pressure episodes;
- 8 industrial-policy / strategic-financing episodes;
- 8 geopolitical / energy / tariff episodes;
- 8 strategic-company / AI-capital episodes.

Include:
- rhetoric-action alignment;
- rhetoric-action divergence;
- successful and failed pressure;
- selective support that did not lift equities;
- market stress with no supportive announcement;
- announcements followed by negative market outcomes.

No winner-only casebook.

## Evaluation

For probabilistic targets:
- Brier score;
- log score;
- calibration slope / buckets;
- abstention coverage.

For continuous market targets:
- signed accuracy;
- absolute error;
- rank correlation across comparable episodes;
- matched-control abnormal response.

Report by family and regime before any aggregate.

Cluster uncertainty by underlying event / calendar period.

## Promotion rule

W1 supports **research comparison only**.

Even if M2 wins:
- no LLM policy inference gains rank / gate / size authority;
- no policy-timing oracle is created;
- production integration begins as display/context unless a separate authority owner approves a calibrated deterministic consumer.

## Initial seed

The companion `POLICY_BEHAVIOR_CASEBOOK_SEED_2026-10-07.json` contains candidate episodes from the current research. They are **source seeds, not PIT-certified training rows**.

W1 is not complete until the source clocks, decision cuts and pre-event expectations are reconstructed and verified.
