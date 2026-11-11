COMMISSION PRO-RUN A - adversarial audit of a backtest harness before its results are accepted

COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: every later rotation claim in Mastermind rests on this harness; one undetected look-ahead or accounting error invalidates all of them.
WHY_NON_PRO_INSUFFICIENT: two shorter reviews already ran on this code; the second found defects the first missed (commits c03f87f27a, a809c227e7), so a deeper independent pass is warranted.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 90
STOP_CONDITION: one comment posted on macro issue #11014 beginning "PRO-RUN A", or the full report returned in this chat if posting is impossible.

Commissioned by the Prophet programme CEO under the Chairman's direction of 2026-11-11 that deep research runs go to Pro sessions and post their results to GitHub. This is read-only review work. It authorizes exactly one issue comment and nothing else: no pull request, no push, no edit to any branch.

WHAT TO AUDIT
Repository (public): mastermindx-market-intelligence/macro
Branch: fable/rotation-core-20261110, pinned commit a809c227e76afc42c678bb6b2f83a7a663d51591
- research/rotation_core/protocol_header_v1.json (the frozen protocol; sha256 af2a09886132bb784535e21134b63c2c86c579e186c248b20bb617fc77580f32) and PROTOCOL_HEADER_v1.md
- research/rotation_core/PHASE2_PLAN.md, PHASE2_ADDITIONS_v1.md, HOLDOUT_ACCESS_RULING_v1.md
- engine/rotation_core_evaluation.py, engine/rotation_core_j4.py
- scripts/run_rotation_core_v1.py, scripts/rotation_core_report.py
- tests/test_rotation_core_evaluation.py

BACKGROUND
The protocol was frozen before any candidate outcome was computed. It tests whether simple rules can (J1) move between US equity and cash on a risk state, (J2) rotate among the sector SPDR ETFs, (J3) rotate across seven asset sleeves, (J4) show that single-name strength pays more inside leading sectors, (J5) stack these. 36 configurations, 38 tests, five Holm families. Decisions are made at the close of day t and executed at the close of t+1. Costs are 5 bp per side for ETFs and 10 bp for stocks, with a 2x stress. Cash earns the 3-month bill rate. Development data ends 2019-12-31. Everything from 2020-01-02 on is a sealed hold-out that only the programme CEO may open. Stage D (development) results are about to be produced and I must decide whether to trust them.

YOUR JOB
Find every defect that could make a Stage D number wrong or flattering. Assume the authors made mistakes. Check at least:
1. Look-ahead, signal by signal: trend (index below its 200-day average), credit (high-yield spread above its 252-observation average, lagged one day), macro (real-time Sahm rule - is a real-time vintage actually used, or today's revised series?), the multi-timeframe share, 63-day relative strength and its 21-day change. For each, state the last date of data a decision at t can see, from the code, with file and line.
2. Execution timing and return alignment: is the t+1 rule applied consistently to every book, baseline and reference? Any off-by-one between weights and returns?
3. Costs, turnover, drifted weights and cash accrual: is the accounting identity exact? Are costs charged on both sides and on baselines too?
4. The exposure-matched reference: is the exposure it matches computed from the full period (a look-ahead) or causally?
5. The bootstrap (stationary, mean block 21, 10,000 draws), p-value conventions, Holm families, and the trial count used for the deflated Sharpe ratio. Does the code match the JSON?
6. The hold-out seal: is it enforced in code, or only by convention? Can any Stage D path read, compute on, or leak a statistic from 2020-01-02 onward (including through rolling windows, normalisation, full-sample parameters, or report code)?
7. ETF inception: nine sector ETFs start 1998-12-22, real estate 2015-10-08, communication services 2018-06-19. How does each book handle a sleeve that does not exist yet?
8. J4: survivorship and delisting handling, the statistical sector assignment (uses only prices up to t?), identity-suspect masking, and whether its coverage cap is honoured in what gets reported.
9. Conformance: for each of the 36 configurations, does the code implement exactly what the JSON defines? List every divergence, however small.
10. The tests: what does each one actually prove, and which claims in the plan have no test behind them?

You may run the unit tests and build small synthetic probes. Do not compute any statistic on real market data dated 2020-01-02 or later.

WHAT TO RETURN
Post one comment on https://github.com/mastermindx-market-intelligence/macro/issues/11014 whose first line is "PRO-RUN A". If you cannot post, return the same text as your final message here.
- Verdict in the first three lines: SAFE TO ACCEPT STAGE D / SAFE EXCEPT THESE RESULTS / NOT SAFE.
- A findings table: severity (BLOCKER, MAJOR, MINOR, NOTE) | file:line | what is wrong | a concrete input that produces a wrong number | the fix | which configurations or tests it voids.
- What you checked and found correct, one line each, so I know the coverage.
- What you could not check and why.
Be blunt. A finding without a file and line, or without a concrete failing scenario, is a suspicion: label it as one. Do not soften a blocker, and do not invent one.
