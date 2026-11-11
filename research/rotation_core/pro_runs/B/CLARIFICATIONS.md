# Pre-outcome implementation clarifications

Recorded after protocol v1 commit ba5ae1e353c6f9738bbf8936b9032e71c747b9ba, before any outcome run. No allocation definition, threshold, universe, cost or candidate changes; trial count remains 10.

1. "Turnover" in report tables means annual gross equity traded notional (sum of absolute equity purchases plus sales / years). It is not halved conventional one-way turnover. C-to-D is 2 units.
2. "Near an episode" means every executed on-to-off transition within that episode's declared calendar window, with no selection on subsequent results. Include a separate designated peak-to-trough exit row even when PRE. Prior/next63 relative returns are measured around the execution close; a preceding63 interval ends at that close, and the next63 begins after it.
3. Rate-conditioning diagnostics sample the last observed session of each month with complete next63-session C/D returns. Report, separately by era, the mean and median next63 D-minus-C cumulative return, sample months and counts of distinct labeled episodes, in each state of: nominal yield above prior12-month mean; backward-looking real yield above prior36-month median; credit stress; and Shiller nominal long yield minus TB3MS <=0. Use the same known-date lags as the protocol (both nominal series m+2 for the curve). These overlapping, retrospective diagnostic cells have no p-values or predictive/causal acceptance.
4. ON-at-trough re-entry rows also retain the last executed re-entry date and its negative signed session offset when present, so premature re-entries are visible.
5. If an unavailable rule has no eligible calm years, false pivots/year is NA, not zero. Era/pooled returns never backfill an unavailable signal.
6. Passive C/D/mix diagnostics use identical eligible industry targets, delay and costs, and are evaluated on the candidate's exact scored dates. They are fixed references, not allocation-rule trials.

