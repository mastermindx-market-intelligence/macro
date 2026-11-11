# Terminal copilot market-risk contract repair

Program: WS:GREY-DEER-RISK-INTELLIGENCE / MAS-258 / Macro #8128.
Current Chairman commission authorizes this independent bounded integration. It is not execution of restricted Macro #8132, a new envelope/policy, or an OracleDash UI edit.

## Outcome and source

The canonical Python bridge emits flat market_risk/v1 fields, but terminal/lib/copilotTools.ts:curateMarketRisk expects nested display.verdict. A valid bridge object therefore becomes no_data. The legacy parser also makes missing/invalid build clocks stale=false.

Source base: mastermindx-market-intelligence/mastermind-terminal@d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a. Existing copilotTools.ts blob 699c2acc462553b3d0b487156a59e8a4cd2d4436. Existing 31 copilot unit tests passed in the admitted private validation workspace. Existing #620 owns OracleDash UI paths, which are excluded.

## Design decision: availability is not current freshness

Do not fix no_data by inventing a built timestamp from a session date or by copying the Python five-day budget into TypeScript. The flat v1 source has no issue/expiry timestamp. Return its real dated report and source-stale marker, but represent independently current freshness as unknown when the only positive evidence is a producer stale=false flag. An explicit stale/invalid marker or invalid/future session is stale=true. Unknown must never become stale=false.

For legacy nested display input, preserve the existing 48-hour artifact-age compatibility test, but require an actual strictly formatted zoned timestamp and reject malformed/impossible/future timestamps. Compare unrounded elapsed time at the boundary. Explicit producer stale/invalid metadata remains protective. State clearly that build age is not quote freshness.

This is a no-data/false-freshness repair, not completion of GD-8B. A future qualified envelope mirror must carry its source-owned issue/expiry contract and entitlement rather than inherit confidence from this compatibility adapter.

## Interface and files

- Create terminal/lib/marketRiskContext.ts, pure function curateMarketRiskContext(raw: unknown, nowMs: number): Record<string, unknown>.
- Keep public curateMarketRisk(raw, nowMs) signature in terminal/lib/copilotTools.ts; delegate only this function to the helper. All other curators/executors remain byte-unchanged.
- Create terminal/lib/__tests__/marketRiskContext.test.ts; invoke the existing exported curateMarketRisk so tests prove the actual consumer path is wired, not merely a dead helper.

Return source_schema, verdict, finite score, bounded label, actual asof/built when known, artifact age when truly measured, stale (boolean or null), freshness_basis/status, explicit source_reported_stale/realtime, compact Radar pressure/state, is_display_only=true and a freshness limitation. Never copy may_rank/may_gate/may_size/may_execute/may_exit_modulate or numerical forecast fields from source data.

Accept the exact flat market_risk/v1 shape and the existing legacy nested display shape with absent schema or risk_state.v1. Unsupported explicit schemas and invalid/missing verdicts return no_data. Retain valid zero. Do not recompute market risk, normalize market score or change portfolio behavior.

## Red-first acceptance

Test actual flat bridge shape without display/built; source-stale and malformed markers; invalid/future session; legacy fresh/old/absent/malformed/future timestamp and exact 48-hour boundary; invalid scalar slots; immutable input; unsupported payloads; authority stripping. Observe failures on unchanged curator, then implement minimal pure helper and delegation.

Run new and existing copilot suites, focused TypeScript checks/lint where supported, and source diff checks. Prove all code outside the import and original function body is unchanged. Publish on a separate bounded Terminal carrier so #849's current independent review identity remains stable.

No browser, production request, model API, source collector or restricted Macro execution is needed for these pure tests. Full authenticated model-facing production proof remains a separate release gate. Never call unit-test success end-to-end completion.

## Ownership and release

Source publication remains GitHub on one exact new branch. The admitted native workspace is a validation copy, not an alternate publisher. Shared node_modules is not modified; dependencies were installed from the operation's lockfile into its own workspace with install scripts disabled.

Independent review, required CI, normal git-gated deployment and permitted live consumer proof remain owed. No Codex/Work, Vercel or new provider spend. A missing eligible reviewer is not permission for self-approval.
