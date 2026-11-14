# PRO-RUN C — implementation plan for the first three Risk Radar slices (Extra High)

You are a senior engineer planning implementation, not strategy.

## Read (public repository mastermindx-market-intelligence/macro, branch fable/risk-radar-masterplan-20261112)
- research/risk_radar/WORLD_CLASS_MASTERPLAN_2026-11.md §1, §2, §4 and §7 (the three slices).
- engine/risk_radar.py (compute, _resolve_state_row, context_gate_live), engine/risk_radar_audit.py (forward-log row writer, issue receipt), engine/risk_radar_backtest.py (state_series), engine/risk_envelope.py, scripts/build_risk_envelope.py, contracts/risk_envelope.schema.json, templates/_risk_radar_card.html.j2, templates/_risk_radar_workspace.html.j2, tests/test_risk_radar*.py.

## Produce, for each of the three slices
1. Exact files to change or add, and the functions involved (cite file:line).
2. The data shapes: new fields, schema additions, the definition file format and how its SHA-256 is computed canonically.
3. Tests to add, named, with what each asserts. Include the guard test for Radar-P that refuses outcome labels after 2019-12-31.
4. Risks: concurrency with other open PRs touching the same templates; nightly render budget; backward compatibility for existing readers of forward_log.jsonl and latest.json.
5. A rough size (lines changed) and whether it still fits one reviewable PR; if not, how to split.

## Limits
- Planning only. Paper-only system; no trading permission, sizing or execution.
- Do not compute, or ask anyone to compute, any relation between a signal and future returns or outcomes on dates from 2024-01-02 onward. Radar-P fitting may use outcome labels dated on or before 2019-12-31 only.
- No secrets or private paths.

## Return
Post ONE comment on https://github.com/mastermindx-market-intelligence/macro/issues/11104 starting with the line `PRO-RUN C`. If you cannot post to GitHub, give the same text here as your final answer and say so on its first line.
