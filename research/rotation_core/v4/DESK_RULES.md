# Rotation desk — rules every worker obeys (Research Director, 2026-11-12)

Governing charter: `/home/ubuntu2/tmp/rotation-core/v4/RESEARCH_CHARTER.md` (read §1, §3, §4). This file condenses what a worker needs.

## The question
Which observable combinations of market, sector, technical, macro and positioning factors give defensible information
about (a) an upcoming sector/asset rotation and (b) a risk-on/risk-off pivot: probability, timing, size, and whether
acting on it beats SPY, RSP and cash after costs. Do not assume a signal exists. A call needs early evidence of the turn
(no knife-catching). Change in breadth matters more than its level. The modern regime (2020+) is the test bed.

## Data blocks (hard) — UPDATED 2026-11-12 01:31Z: D IS OPEN (see v4/RELEASE_D.md and charter §3a)
- **D (discovery): 2020-01-02 .. 2023-12-29, and any earlier period: OPEN for research against outcomes**, under three
  conditions: (1) the trial's ledger row is written BEFORE its result is read; (2) every result is reported with the
  cumulative trial count and against the W2 baselines; (3) walk-forward inside D is purged and embargoed by the label horizon.
- **Forward-looking labels stop at 2023-12-29:** an h-session label's last origin date is h sessions (plus the t+1
  execution lag) before 2023-12-29. No label window may reach 2024-01-02.
- **S (sealed): 2024-01-02 onward.** Features may be computed by code. Never join any signal to any forward return,
  hit rate, label outcome or P&L on S, in any form. Sealed-block eligibility is per candidate (charter §3a); not your call.
- Pre-2020: allowed for checks and as extra discovery history; 2020–2023 stays the primary test bed.
- Never open anything under `/home/ubuntu2/tmp/rotation-core/data/french/sealed_post2019/`.
- Code that evaluates must take its window as an argument and refuse (raise) any evaluation or label window that
  reaches ≥ 2024-01-02. Write this guard; test it.
- Do NOT read the July 2026 "rotation time machine" reports or the July mined list; if you already have, say so.

## Trial ledger
`/home/ubuntu2/tmp/rotation-core/v4/trials.jsonl`, append-only. Before reading the result of any evaluated configuration
on D, append one JSON line: `{"id","card","author","author_read_july_reports" (true/false),"features","label","model_class","grid_size","window","utc"}`.
Never edit or delete a line. Pre-2020 sanity checks are logged too, with `"window":"pre2020-check"`.

## Data and secrets
- Raw vendor prices are never committed to any repository. Cache under `/home/ubuntu2/tmp/rotation-core/data/`.
- Vendor keys: refer to paths only; never print, copy or log a key value. No new spend, no paid credits, no plan change.
- Read existing data in place; do not re-derive what `v3/` and `v4/PANEL.md` already establish.
- FRED: the repository store (Macro checkout) is the source; do not build a new scratch FRED cache.

## Git
- Never push to branch `fable/rotation-core-20261110` or touch PR #11086. The Macro checkout at
  `/home/ubuntu2/.t3/worktrees/Macro/rotation-core` is ON that archive branch: read it, never commit there.
- Desk code lives in `/home/ubuntu2/tmp/rotation-core/v4/` (scratch, not a repo) unless the Director says otherwise.

## Method defaults
- Purged, embargoed walk-forward inside D only (purge ≥ label horizon, embargo ≥ 5 sessions).
- Every candidate reports against the W2 baselines (6m and 12m momentum, 200-session trend, equal weight, SPY, RSP, cash).
- Costs: 10 bp per unit one-way turnover for ETFs base case, 20 bp stress.
- Decide at close t, execute at close t+1; forward windows start at the execution close.
- Publication lags on macro/positioning inputs are mandatory (as-of joins, release-date not reference-date).

## Reporting
Report to the Research Director thread only. One final message: what was built (paths), tests run (counts, pass/fail),
anything that blocks, and anything you were unsure about. No routine status. Never claim a result you did not compute.
