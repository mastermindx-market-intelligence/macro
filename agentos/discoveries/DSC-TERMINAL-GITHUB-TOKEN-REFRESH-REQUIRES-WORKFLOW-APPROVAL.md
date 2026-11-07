---
key: TERMINAL-GITHUB-TOKEN-REFRESH-REQUIRES-WORKFLOW-APPROVAL
claim: GitHub's default workflow token creates approval-required pull-request runs after automated branch refreshes, while head-only dispatch success does not clear the blocked PR workflow.
falsifier: >-
  After an eligible existing-controller GITHUB_TOKEN branch refresh, inspect its PR run using `gh api repos/mastermindx-market-intelligence/mastermind-terminal/actions/runs/RUN_ID`; an unapproved run automatically starting with jobs, or revised GitHub documentation removing the gate, disproves this observation.
so_what: Use an enrolled repository-scoped GitHub App identity for the existing merge controller and prove its fresh-head CI and protected merge; do not ask the Chairman to approve every automatic refresh or accept an older approved head.
kind: runtime
verified_at: 2026-10-08
verified_by: >-
  Terminal #839 at94dff/a496; `gh api repos/mastermindx-market-intelligence/mastermind-terminal/actions/runs/37707997477`; historical run37650481196 attempt2; current official GitHub GITHUB_TOKEN documentation.
scope: [terminal, WS:TERMINAL-REPAIR-AUDIT20-2026-10]
confidence: verified
---

The controller uses its ephemeral GITHUB_TOKEN for update-branch and dispatches CI separately. Both observed PR-triggered runs had actor github-actions[bot] and action_required with zero jobs. The Chairman approved the earlier94dff run, which resumed with triggering actor chriswong6031-creator. The controller had already refreshed the branch to a496; the newer PR run remained action_required. Its dispatch run also failed a real Seasonal SVG hover interception, so neither stale approval nor bypassing checks establishes merge readiness.

GitHub documents the default-token approval gate and the separate App/PAT identity path: https://docs.github.com/en/actions/concepts/security/github_token . Its official agentic-workflow documentation states that github.token cannot approve approval-required runs itself: https://github.github.com/gh-aw/reference/safe-outputs-pull-requests/ .

No new App has been installed by this continuation, repository secret metadata lists no configured secret, and organization secret visibility is unavailable to the current CLI account. Draft Terminal #850 preserves the reviewed source change atc47ee8e, with40 parent tests passed; identity enrollment is not claimed live. The existing three required checks, trusted App15368 binding, protected merge and source custody remain authoritative.
