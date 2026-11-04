# Provider Workload Guard Implementation Plan

> For agentic workers: use superpowers:executing-plans for this bounded inline slice.

**Goal:** prevent explicitly profiled product inference from consuming native developer
subscription credentials through the existing Macro provider waterfall.

**Architecture:** extend Shared AI Provider Control with a pure, secret-free workload
transport decision. Filter the existing builder before credentials/account discovery;
keep existing routing, models, cooling and legacy migration behavior. No new execution,
account, quota or lifecycle owner.

**Tech Stack:** Python standard library, JSON, existing pytest and LLM provider CI job.

**Spec:** docs/superpowers/specs/2026-09-15-vps-site-fabric-integration.md.

## Global constraints

No provider calls, credential reads in the guard, enrollment, deployment or new spending.
No native worker spawning, fixture admission or API fallback manufactured by this patch.
Only trusted server configuration can select a workload. Host restrictions are a floor.
No default behavior change until explicit profile adoption. Invalid opted-in config fails
closed. A purpose/transport receipt does not prove entitlement, quota or production use.
A Draft/HOLD-FOR-SOL source PR is not deployed and requires independent review.

## Task 1: establish baseline and write failing integration tests

Files: tests/test_provider_workload_policy.py; unchanged tests/test_llm_auth.py.

- [x] Run `MM_DATA_GUARD=1 python3 -m pytest tests/test_llm_auth.py -q` in the isolated
  workspace: 80 tests passed. Shared pytest garbage cleanup emitted inherited permission
  warnings; do not change or clean another operation's directories.
- [x] Create isolated test fixtures for SDK construction, native account discovery and
  provider-health recording. Assert on actual builder output and boundary calls.
- [x] Run the new tests before implementation. Required failing behavior:

```python
def test_site_profile_does_not_build_subscription_rungs(monkeypatch):
    from engine.llm_auth import build_providers
    providers = build_providers({
        "workload_profile": "site_interactive",
        "provider_order": ["oauth", "codex"],
    })
    assert providers == []
```

The test fixture makes any credential read or native-account discovery observable without
using actual credentials. Additional red tests require unknown profiles to raise ValueError,
prevent implicit Codex on API-only order and preserve a deliberately empty list.

## Task 2: implement the policy and compose the existing builder

Create config/provider_workloads.v1.json and engine/provider_workload_policy.py.
Modify engine/llm_auth.py only at the provider-construction boundary.

Interfaces:
- `load_policy(path: Path) -> dict`: bounded JSON parse, duplicate-key and closed-schema
  validation; fixed error codes without echoing untrusted document values.
- `decide_workload(cfg: Mapping[str, Any], *, host_profile: str | None = None,
  policy_path: Path | None = None) -> WorkloadDecision | None`: returns None only when
  both selectors are absent; otherwise intersects declared profiles and configured rungs.
- `WorkloadDecision.receipt() -> dict`: closed non-secret projection, policy hash/revision,
  applied profiles and allowed/denied transport names. No clients, secrets or authority.

The manifest shape is fixed:

```json
{
  "schema": "mastermind.provider_workloads.v1",
  "revision": 1,
  "owner_program": "shared-ai-provider-control",
  "profiles": {
    "site_interactive": {
      "execution_surface": "inference",
      "allowed_providers": ["anthropic", "deepseek", "ollama"]
    }
  }
}
```

Use the same inference shape for site_batch, portfolio_analysis and lobe_analysis.
Declare development_agent, fable_orchestration and lobe_maintenance with native_agent and
an empty allowed_providers list. The inference builder refuses those profiles rather than
spawning a worker. Manifest validation may not permit oauth or codex in an inference row.

- [x] Reject unknown, null/empty or malformed selectors, malformed provider_order, duplicate
  JSON keys, unknown document fields, unsupported schemas and broadening transport edits.
- [x] Load the reviewed manifest for each opted-in call; canonical SHA-256 binds content.
  Do not claim this implements trusted deployment or rollback/generation enforcement.
- [x] Integrate before `_config.secret` or `_codex.available_accounts`. Apply the server
  floor from MM_PROVIDER_WORKLOAD_PROFILE. In profiled mode require explicit provider_order,
  use only decision.allowed_order and skip the legacy automatic Codex insertion.
- [x] Attach the safe decision receipt under `workload_policy` on opted-in descriptors.
  Keep existing cooling and usage-attribution machinery unchanged.
- [x] Run targeted red tests again and require green.

## Task 3: adversarial regression and existing CI composition

Files: tests/test_provider_workload_policy.py and .github/ci/legacy-jobs.yml.

- [x] Add tests for host/caller intersection, no caller broadening, malformed manifest,
  duplicate keys, oversized JSON, unknown surface/provider, closed receipts, same-process
  policy reload, no inserted metered/local rung, invalid config before secret access,
  required native execution and legacy compatibility.
- [x] Extend the EXISTING job command containing tests/test_llm_auth.py with the new test
  file. Do not create a parallel workflow or alter another program's required-check logic.
- [x] Run the existing full LLM provider job test list plus the new suite with data guard
  and an operation-local pytest temp root. No full repository suite in this sparse tree.
- [x] Run compile checks and `git diff --check`; inspect exact diff and tracked/untracked
  status. Separate inherited environment/fixture failures from this change, with evidence.

## Task 4: reviewable delivery and integration return

- [x] Write an Agent OS handoff in the canonical Macro home, validate its schema and record
  the exact source-only proof and remaining consumer/native-runtime gaps.
- [x] Commit only the named files, push claude/vps-site-fabric-20260915-sol, and open a Draft
  PR with HOLD-FOR-SOL. No merge-on-green label and no native auto-merge.
- [x] Fresh-read the incumbent Fable thread after final evidence, then send the exact head,
  PR and tests for independent review/composition. Delivery is not acknowledgement.
- [x] Keep production profile activation, credential changes and live canaries held until
  approved eligible providers, budgets, current runtime gates and rollback are proven.

## Hosted CI return: shared dependency coverage repair

The first published head 610df529ee32de1c3c712a796678bd886abe203e produced five
new contract-delta closure findings: biocatalyst-history, biocatalyst-serving,
flow-surface, unrun-government-revenue-grader and unrun-picks-boards reach the
new module through llm_auth but their exclusive paths did not declare it.

- [x] Reproduce with five discriminating manifest tests: five failed before repair.
- [x] Add only engine/provider_workload_policy.py to those five existing job scopes.
  All five already cover config/**. Assert every other manifest field unchanged.
- [x] Rerun the full provider group: 285 passed in 12.12 seconds (52 new tests total).
- [x] Compile checks and git diff --check passed again.
- [x] Complete the existing full differential contract-delta script against the exact
  checked main base; keep its result distinct from hosted CI acceptance.
- [x] Publish the correction on the SAME PR and supersede the exact-head review binding.
  Published as 85a9d127b6e9a9b9e07708f8912046f40051795f; independent R1 found the
  separate gate-selection defect below.

No runtime/provider code changed in this repair, no checks were weakened, no
second CI workflow was created, and production activation remains held.

Full contract-delta result against 52bd0cde0669cd8ea396dfbe692399261dd5cfe5:
exit 0; 0 introduced, 0 inherited. The native checker created and cleaned its
own sparse temporary base carrier; no active worker checkout was modified.


## Independent review R7179-R1: pull-request execution repair

Review: Macro #7179 comment 5690266059, bound to 85a9d127. Verdict was
REQUEST_CHANGES for B1 only. The source policy passed all seven substantive
criteria and reviewer mutants; the data-gated capability-broker job did not
run in any PR code pack. The earlier paths-only repair did not fix this.

- [x] Reproduce through the real gate loader/partitioner: zero code executions.
- [x] Add a discriminating regression before changing CI: 1 failed, 52 deselected;
  failure was the expected zero executable PR steps, not an import error.
- [x] Add one lightweight pytest step to the existing code-gated ruling-graph job,
  after minimal dependency installation. Do not modify its existing final routing
  step (the incumbent #7114 writer owns that adjacent work).
- [x] Preserve capability-broker as gate:data and retain its existing suite.
- [x] Verify the dedicated suite: 53 passed. Complete provider group: 286 passed
  in 7.60 seconds. Use an operation-specific temporary directory OUTSIDE the
  repository: the first whole-group attempt used an in-repository temp directory
  and correctly hit the existing AI_COSTS_STATE_ROOT guard in two ledger tests;
  no product code was changed to weaken that guard.
- [x] Complete differential contract-delta against current observed main
  7c3b2e19c0bffe8aca9a7bfa91e610c1ca3b7149: exit 0, zero introduced and zero
  inherited findings (209.54 seconds). Post-commit merge-tree proof remains separate.
- [ ] Publish this exact repair, obtain fresh independent review, and conclude
  the new head's hosted binding checks. Earlier-head review/checks are not release.

This repair changes no provider behavior, credentials, running service, profile
activation, model selection, budget or admission authority. Direct Sol execution
is LOWER_TOTAL_OVERHEAD / CRITICAL_PATH_SHORTCUT on the retained writer; Fable
continues principal integration and independent review coordination.


Additional deterministic proof: real inferred scopes select ruling-graph when
any of engine/provider_workload_policy.py, engine/llm_auth.py,
config/provider_workloads.v1.json, or tests/test_provider_workload_policy.py
changes. On isolated manifest copies, changing the job to gate:data, removing
its step, or commenting out the pytest command each yields zero code executions;
the original manifest remains unchanged. This tests executable reachability, not
merely a string occurring somewhere in a gate-free manifest.
