# R1-B v3 adversarial prereg review — superseded before registration

Status: **V3 NOT REGISTERED, NOT RUN, NO OUTCOME COLUMN OPENED.** V3 remains immutable at `1518ef7dabc74428bd79e7724f080226381b6fe4`; this review supersedes its execution target with v4.

## Finding 1 — contradictory event uniqueness fields

V3 correctly stated `selector_event_uniqueness=first_qualifying_event_per_selector_per_symbol_session`, but it retained the older machine field `first_event_per_symbol_day=true`. An implementation could lawfully choose either interpretation: consume the entire day after the first BASE anchor, or allow the first qualifying event for each selector. Those produce different fires and denominators.

V4 removes the stale global field and makes the law machine-explicit: no global first-event gate; at most one qualifying event per selector/session; an unqualified early anchor does not consume that selector; one selector fire does not consume another. The separate control census remains first lawful BASE anchor per symbol/session/30-minute bin and is not a selector.

## Finding 2 — singular LOD anchor contradicted two declared diagnostics

V3 retained `lod_survival_anchor=candidate_low_strictly_unbroken_through_scheduled_close` while separately declaring candidate-anchor and pre-confirmation episode-low survival. A consumer could incorrectly collapse the two diagnostics back to the candidate low.

V4 removes the singular field and states that both anchors are reported separately with no primary collapse.

## Disposition

No market data or R1-B outcome was inspected. The five selectors, price thresholds, latency, controls, horizons, costs, population and promotion gate are unchanged. V3 is **DO_NOT_RUN**; only separately frozen v4 may be registered.
