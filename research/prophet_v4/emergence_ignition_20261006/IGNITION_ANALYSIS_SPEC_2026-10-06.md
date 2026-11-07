# Frozen implementation choices for the ignition replication

Research only. Source PR head `770918cb266b5d884978e31d61670b4efd789eaf`; legacy ledger blob `b0ee089e86269854b699f4667b47dd10a469374c`. This specification is an analysis implementation log, not a new prospective preregistration. All observations through 2026-10-06 are discovery data.

The registered primary exposure remains fresh T2 plus at least two independent, point-in-time-valid families. No legacy flag is promoted to this exposure. Strict estimation requires event/decision clocks and evidence lineage; otherwise its effect is non-estimable.

The historical diagnostic uses unchanged `news_burst + sue_fresh + smartmoney_add >= 2` in `rank_by=us_prophet_v3`, buy lane. Missing flags remain unknown. First T2 per ticker across the H5 ledger is the fixed issuer sensitivity, with that same date held constant for later horizons; it is not a canonical episode ID. All-row estimates reproduce the parent only and are labelled correlated nightly observations.

H5 is primary, H3/H10/H21 secondary. Return outcomes retain the frozen ledger's next-session-close plus H sessions clock; reconstructed next-session-open outcomes are separate conditional hypothetical execution sensitivities. No supplied publication timestamp means no executable-trade claim. All prices are frozen Git objects with final-vintage adjustment caveats. Price reconstruction never overwrites accepted ledger returns.

Clock clarification for future accrual: the frozen preregistration specifies five sessions after the episode decision cut. The prospective evaluation owner must separately pin that decision cut's session boundary and entry/end observations before accrual; the legacy grader's next-close-plus-H convention remains this historical diagnostic and cannot silently add a session to the registered prospective primary.

Report absolute, SPY and sector excess; close MFE/MAE/MDD; daily high/low excursions where coherent OHLC exists; losses at <= -5% and <= -10% (descriptive reporting cuts, not optimized thresholds); H5-to-H10/H21 persistence. No available or mature price is not a zero or a loss.

Controls: same-date T2 with 0/1 flags, same-date/sector and same-date/Entry Availability sensitivity, and fixed first-T2 controls. Covariates: board alpha, off-high proximity, composite-z rank proxy, plus final-vintage trailing 5/21-session momentum and 21-session SPY relative strength. Momentum and same-window RS are collinear under date fixed effects; do not pretend their coefficients identify independent mechanisms. Nearest-control matching uses same-date/sector, standardized covariates, one nearest control and ticker lexical tie break, chosen before reading matching results.

Uncertainty: Wilson intervals for descriptive win rates; date-block mean differences with Student-t intervals and seeded cluster bootstrap; leave-one-ticker/date/sector sensitivities. Four independent exposure dates cannot support precise inference. Repeated/overlapping sessions and post-selection defeat confirmatory interpretation of p-values.

Negative controls: first T1 plus convergence, non-T2 buy plus convergence, watch convergence, same-date top-decile composite-z with zero evidence flags, and legacy SUE-only or news-only/ownership-only attribution. Stale/unclocked evidence stays typed as such and never enters the strict primary. Report every specified comparison, including failed and non-estimable cells.
