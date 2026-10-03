# R1-B v2 adversarial prereg review — superseded before registration

Status: **V2 NOT REGISTERED, NOT RUN, NO OUTCOME COLUMN OPENED.** V2 remains immutable at `1348a238c8fbcb79b617478311f2ce0e1e37d4c0`; this review supersedes its execution target with v3.

## Finding — zero processing-latency price reference

V2 described entry as the next five-minute bar open after a candidate or confirming bar. In timestamp terms that open is the same boundary instant at which the completed decision bar becomes knowable. That creates an optimistic zero-processing-latency reference and conflicts with the predecessor contract in `EXHAUSTION_AND_CONTINUATION_DESIGN.md`: `e(t)` is the earliest admissible entry **after decision/processing latency**.

R1-A already separated decision and price reference by nonzero time. R1-B should not gain an execution advantage simply because its decision cadence is five minutes.

## V3 correction

V3 freezes one full five-minute latency bar after every candidate/confirmation decision. If decision or confirmation is knowable at time T, the bar starting at T is the processing/latency bar; the price-reference entry is the open at T+5m. Matched controls receive the identical confirmation-delay plus processing-latency treatment.

All market-state thresholds, selector definitions, control covariates, horizons and cost cells are unchanged. No market data or outcomes were inspected in making this correction.

## Disposition

V2 is **DO_NOT_RUN**. Only separately committed v3 may be registered. This correction is execution realism, not parameter search.
