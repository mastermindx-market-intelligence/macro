COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: An adversarial review of a risk-state master plan must find statistical, contract and product errors across many files; it needs long careful reasoning.
WHY_NON_PRO_INSUFFICIENT: The author already self-checked; a faster pass tends to agree with the author instead of breaking the plan.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 90
STOP_CONDITION: One complete critique posted as a comment starting "PRO-RUN B" on the GitHub issue named below.

# PRO-RUN B — adversarial critique of the Risk Radar master plan

You are a hostile but fair reviewer. Your job is to break the plan, not to improve its prose.

## Read (public repository mastermindx-market-intelligence/macro, branch fable/risk-radar-masterplan-20261112)
1. research/risk_radar/WORLD_CLASS_MASTERPLAN_2026-11.md — the plan under review.
2. research/risk_radar/CENSUS_2026-11-12.md — the measured facts it claims to rest on.
3. engine/risk_radar.py, engine/risk_radar_audit.py, engine/risk_radar_backtest.py, engine/risk_envelope.py, contracts/risk_envelope.schema.json.
4. research/RISK_RADAR_TUNING.md, research/grey_deer/RISK_RADAR_*_RESULTS_*.md, research/grey_deer/risk_radar_architecture_contract_20261017.md, agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md (do_not_redo, lines 75-81).

## Attack these, with file and line for every point
1. **Evidence.** Any claim in the plan or census that the files do not support, or that overstates the evidence. Any 2020+ number used as if it were validation.
2. **Validation design.** Is "freeze + forward record" plus "Radar-P fitted on outcomes ≤ 2019-12-31" actually clean? Look for leaks: inputs or percentile windows that reach past 2019 during the fit, leg *choices* (not just constants) that were selected using 2020+ evidence, survivorship in which legs exist at all, the 504-session percentile window, regime differences pre/post 2020. Say what Radar-P can and cannot honestly claim.
3. **The four public states.** Does collapsing calm+watch into CLEAR and showing caution as GUARDED lose information or mislead? Would a user act wrongly on any of them? Is the 5-session step-down rule a disguised tuning choice?
4. **Metrics and bars.** Which proposed bars are unmeasurable on the available record, mutually inconsistent, or easy to game? Propose better ones with numbers.
5. **Consumer contract.** Point-in-time holes in the series (issued_at vs session, late data, replay rows, version changes). Can a consumer misuse it to create trading permission or to leak future information? Does the series violate the do_not_redo item "no new event store / forward ledger for risk episodes"?
6. **Slices.** Is each truly one PR? Is each proof sufficient? What is the most likely way each slice fails in production? Is the order right by user value?
7. **PR recommendations.** Any that are wrong given the PR's evident content.
8. **What is missing** that a world-class risk-state system would have.

## Hard limits (binding)
- Paper-only. Descriptive state never becomes trading permission, sizing, execution or automatic exits.
- Do not compute, or ask anyone to compute, any relation between a signal and future returns or outcomes on dates from 2024-01-02 onward.
- No secrets, account details or private paths.

## Return
Post ONE comment on https://github.com/mastermindx-market-intelligence/macro/issues/11104 starting with the line `PRO-RUN B`. Then: a one-paragraph verdict (ship as is / ship with changes / rework); findings ranked most severe first, each with severity (blocker / major / minor), file:line evidence and a concrete fix; then what you could not verify. If you cannot post to GitHub, give the same text here as your final answer and say so on its first line.
