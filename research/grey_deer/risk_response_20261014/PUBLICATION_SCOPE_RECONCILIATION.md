# Publication-scope reconciliation — 2026-10-15

This corrects an over-broad earlier diagnostic, not a permission change or clearance of a denied action.

## Exact observations

1. The selected Studio Direct `studio_git_publish_status` schema explicitly supports only an existing **Mastermind** attended workspace, accepts only operation_id and forbids a repository selector. Its selected commit/push schemas have the same Mastermind-only scope. A fresh schema read confirms that limitation.
2. The protected runbook `docs/runbooks/managed-multirepo-workspaces.md` at78388ac29f7e54c9dfe7799a8e4769fb46d4aed6 says omission of the new optional repository argument preserves exactly the legacy Mastermind route. It also distinguishes selected tool inventory from installed profile capability.
3. The actual operation is independently registered in **Macro**, at the verified returned path `/Volumes/Mastermind 2/agent-workspaces/macro/web/macro-risk-response-20261014-c1`, branch `sol/web-macro-risk-response-20261014-c1`, local HEAD9e8f22ec1fc03c046bc1f38b3f397d5f6c9965ef. Both effective fetch and push origin are exactly `https://github.com/mastermindx-market-intelligence/macro.git`.
4. A fresh authenticated GitHub resource preflight for `mastermindx-market-intelligence/macro` reports pull/push/maintain/admin permission true, default main. The actual repository workflow in CLAUDE.md uses the ordinary commit/push/PR chain. Source read/write/test work and the installed mmx workspace owner are already working on this same Studio carrier.
5. No Macro commit or push was previously dispatched or refused. The earlier legacy helper response remains REFUSED/NOT_APPLIED. It does not establish that this separate Macro registration was resolved or its publication permission adjudicated. The exact cause inside the legacy precheck remains unproven and is not being probed again.
6. Fresh ordinary Git fetch on the same Macro workspace succeeded. Current main0ce266ab9d2ea6bfc5731a728cbd0e08ef13cb66 changes none of the twelve owned source/test paths versus the acquired base. No primary checkout, foreign branch or source writer is displaced.

## Action-scoped disposition

Keep the legacy Mastermind-only typed helper unavailable for this Macro operation; do not replay it, add unsupported tool arguments, rebind the operation, alter configuration or switch connectors. Its earlier response must not become a fictional global Macro publication denial merely because a caller supplied a Macro operation key to a Mastermind-only schema.

The next candidate-publication step uses the existing ordinary Macro Git workflow through the SAME Studio shell, SAME registered workspace and SAME branch, with an exact expected-HEAD check and no force, tags, remote changes or branch replacement. That is a first Macro source-publication attempt under the current assignment, not replay of a refused Macro write. Any actual safety/permission refusal on that action is final for its effect; an ambiguous dispatched write stays on this original carrier for reconciliation. Authenticated resource permission alone is not a claim that the write has executed or will succeed.

Independent review, CI, release holds, merge and production acceptance remain separate. No source is described as published before exact commit/remote readback. No deployment or existing#8132 HOLD is cleared by this diagnostic correction.
