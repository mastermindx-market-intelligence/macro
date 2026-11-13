COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: Judging whether a rolling walk-forward refit on about six years of one regime can prove a fitting procedure needs careful statistical reasoning about small samples, overlapping labels and parameter search.
WHY_NON_PRO_INSUFFICIENT: Faster modes tend to bless walk-forward as automatically out-of-sample and miss episode-count and search-depth problems.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 90
STOP_CONDITION: One complete critique posted as a comment starting "PRO-RUN D" on the GitHub issue named below.

# PRO-RUN D — attack the walk-forward design of the Risk Radar master plan (v2)

You are a hostile but fair statistical reviewer.

## Context (decided, not up for debate)
The owner has ruled: Risk Radar is fitted to the modern regime (2020 onward) by design and refit on a schedule. What must be proven is the FITTING PROCEDURE, by rolling walk-forward refit inside the modern regime (fit to end-2021, score 2022; to end-2022, score 2023; ... to today), compared with simple baselines (SPY under its 200-session average, VIX level, credit-spread change). 2024 onward may be scored as the Radar's own already-seen history, labelled as such. Stress reads of 2008 and 2018 are descriptive only.

## Read (public repository mastermindx-market-intelligence/macro, branch fable/risk-radar-masterplan-20261112)
1. research/risk_radar/WORLD_CLASS_MASTERPLAN_2026-11.md — especially §3 (procedure, folds, metrics) and Slice 1 in §7.
2. research/risk_radar/CENSUS_2026-11-12.md.
3. engine/risk_radar.py, engine/risk_radar_backtest.py, research/RISK_RADAR_TUNING.md, research/grey_deer/RISK_RADAR_GATE_LATENCY_RESULTS_2026-09-21.md, research/grey_deer/RISK_RADAR_PROBABILITY_WALKFORWARD_RESULTS_2026-09-23.md.

## The question to attack
**Is walk-forward refit with this little history informative, and what would make it more so?** Be concrete:
1. How many independent drawdown episodes (>=5%, >=8%, >=10% SPY) fall in each scoring year 2022-2026? What can five folds of this size distinguish (e.g. procedure vs best baseline), with what power? Give rough numbers.
2. Search depth: how many effective parameters does the procedure tune, and how much does that inflate in-fold fit? What search/shrinkage/objective would keep the out-of-sample read honest?
3. Leakage: overlapping H21 labels across the fit/score boundary (is a 21-session embargo enough?), trailing 504-session percentiles, the fixed leg set that was itself chosen with 2020+ evidence, and the analyst having seen 2022-2026 already. What can the report honestly claim given these?
4. Better designs: e.g. monthly or quarterly refits, episode-level rather than day-level scoring, combinatorial purged cross-validation, multi-market replication (other countries' indices, same procedure), synthetic or block-bootstrap null distributions, a "keep current constants" baseline, pre-declared minimum detectable effect. Rank them by information gained per unit of effort.
5. Metrics: which of the plan's bars (§3.6) can actually be estimated from five folds, and which should be reported only as descriptive?
6. Anything in Slice 1's proofs that would not catch a leak.

## Hard limits
Paper-only; descriptive state never becomes trading permission, sizing or execution. No secrets or private paths. Do not compute any new relation between a rotation or breadth signal and returns yourself; reason from the published files.

## Return
Post ONE comment on https://github.com/mastermindx-market-intelligence/macro/issues/11104 starting with the line `PRO-RUN D`. Then: a one-paragraph verdict; findings ranked most severe first (blocker/major/minor), each with file:line evidence and a concrete fix; a recommended Slice 1 design in at most 20 lines; what you could not verify. If you cannot post to GitHub, give the same text here as your final answer and say so on its first line.
