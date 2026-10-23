# Leader-reset × rates-context preregistration — v1

Operation: `rates-entry-context-20260919-sol-006`.  
Parent mission: rates-aware opportunity intelligence under the existing RIC / Prophet / Live Entry Radar / Evaluation ownership model.

## Question

For opportunities already selected by the existing Entry Radar replay, does the existing `leader_reset` cohort behave differently when the latest *qualified, decision-date-compatible* 2-year and 10-year nominal-yield observations are both easing versus both rising?

This is a **conditioning** study. Rates do not create candidates, delete candidates, change their detector state, move the entry timestamp, extend the outcome window, or alter the matched-control construction.

## Why this population

`leader_reset` is already frozen in the replay feature law as trailing-120-session return >= +30%. It is therefore an existing leader-like population that can test the Chairman's "strong leader + macro pullback relief" mechanism without inventing a new winner list after outcomes.

It is **not** the final sector/stock leadership model. A future flagship system still needs sector leadership, within-sector relative strength, catalysts and current leadership persistence. This test only asks whether rates add information inside one existing leader-like cohort.

## Clock and evidence law

The new pure adapter consumes `yield_momentum.v1` facts. Prior-dated captured observations may enter corrected-history research. Same-session observations require a timezone-aware availability instant no later than the episode decision instant plus historical-availability qualification. Future or unreceipted same-session rows are unavailable.

Source dates and internal digests are not publication receipts. A corrected-history result can justify a prospective follow-up; it cannot promote rank/gate/size/trade authority.

## Frozen primary comparison

Population:
- existing replay episodes whose frozen cohort is `leader_reset`;
- existing panel, detector, episode identity, era and holdout laws unchanged;
- existing matched-control outcome `excess_net`, primary H=10 trading sessions.

Rates state:
- **both_easing**: last qualified 2y change < 0 and last qualified 10y change < 0;
- **both_rising**: last qualified 2y change > 0 and last qualified 10y change > 0;
- mixed front/long states and flats are diagnostic only;
- no optimized basis-point threshold.

Primary estimand: date-aggregated mean `excess_net` difference, both_easing minus both_rising.

Uncertainty: 5,000 decision-week block-bootstrap resamples, seed 20260919. Minimum 30 distinct decision dates in each primary cell. FIT and TEST primary effects must have the same sign. Practical margin is +50 bp over the 10-session ruler.

A result is only `SUPPORTIVE_FOR_PROSPECTIVE_FOLLOWUP` when the point estimate is positive, the 95% interval lower bound is above zero, the +50 bp margin is met, both date-count gates are met, and FIT/TEST signs agree. Otherwise report the measured result; do not tune the rates threshold or population to rescue it.

## Secondary diagnostics

Secondary outcomes are the existing replay fields `mae`, `false_start`,
`time_to_positive`, and `fwd_ret_net`. Existing source 5/22/63-session yield
changes and acceleration remain descriptive diagnostics. Mixed 2y/10y states,
other tenors, source turn-watch labels, and alternative replay horizons may be
reported but cannot replace the primary comparison.

The analysis must print:
- episode count and **distinct decision-date count** in every state;
- FIT and TEST counts/effects separately;
- unavailable-rate coverage;
- detector/panel composition by state;
- cohort and outcome missingness/censoring;
- the number of same-session rows excluded for missing decision-time receipts.

Do not count five correlated tenors as five independent confirmations. Direction
counts are descriptive coverage, never a score.

## Multiplicity and no-rescue law

This carrier freezes exactly one primary contrast. Do not:
- sweep basis-point cutoffs;
- choose a different tenor pair after seeing results;
- promote whichever mixed state looks best;
- shorten/extend the outcome endpoint to improve the contrast;
- remove no-trigger, unavailable, censored, or losing opportunities;
- select a detector/panel subset because it performs better after outcomes;
- reinterpret source `turn_watch` as independent alpha evidence.

A failed or uncertain result closes only this exact construction. It does not
establish that rates are useless for entries. A supportive result earns only a
separate prospective/shadow hypothesis; it does not promote this corrected-history
join directly.

## Authority and evidence ceiling

This experiment may produce research context and a measured conditional contrast.
It may not rank stocks, create candidates, alter Prophet, gate an entry, size a
position, choose an option, or originate a trade.

Corrected source dates answer “what observation belongs to this dated frame?”
They do not answer “was this information available to the historical live system
before the decision?” unless the existing source owner supplies the required
receipt. Therefore the adapter keeps corrected-history usability separate from
`as_observed_replay_certified`.

## What this experiment does not test

It does **not** test:
- sector selection or semiconductor leadership;
- within-sector alpha-leader selection;
- real-yield momentum;
- Fed-funds/SOFR meeting-path surprise or “priced-in” event repricing;
- intraday FOMC yield turning points;
- price-zone selection, gap fills, VWAP/volume shelves or Elliott waves;
- options flow, packages, positioning, vanna/charm or max-pain increments.

Those are later additive hypotheses. They must not be smuggled into this first
comparison after seeing its results.

## Execution order and existing owners

1. This carrier freezes the pure adapter and preregistration **without opening
   outcomes or registering trial rows**.
2. Preserve the existing Entry Radar episode and outcome owners. There is no
   rates-specific episode store, replay engine, outcome ledger, or evaluator.
3. Before an empirical run, reconcile the current rates producer and historical
   evidence clocks. The study may run as corrected-history research when that
   evidence class is explicit; promotion requires stronger as-observed evidence.
4. Register the exact frozen study through the existing scientific registry /
   TrialLedger owner before the first outcome read. Registration must preserve the
   exact config hash and the incumbent ledger prefix.
5. Execute against the existing episode/outcome ruler with the same H=10 endpoint.
   A delayed or unavailable rates observation does not move that endpoint.
6. If and only if the frozen result is supportive, create a separate prospective
   follow-up under the existing Radar/qledger/Evaluation path.

Existing Tactical R1-A (#7270), R1-B (#7274) and minute resolution (#7275)
remain independent. R1-B's frozen H60 experiment is not amended by this work.
The A V4 / B Round2 / C HardenedV2 rates-research returns remain evidence and
are not rerun here.

## Falsifiers for this design

This adapter/prereg must be repaired or abandoned if:
- attaching rates changes an episode identity or outcome value;
- a future observation is admitted;
- an unreceipted same-session observation is admitted;
- an unavailable rates source removes an otherwise valid episode;
- a rates field gains rank/score/gate/size/trade authority;
- a source-date/digest is represented as a publication receipt;
- an existing canonical owner already supplies an equivalent replay join.

Outcome performance is deliberately **not** a design falsifier. It is the later
scientific result.
