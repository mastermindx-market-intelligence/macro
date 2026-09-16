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
- [ ] Commit only the named files, push claude/vps-site-fabric-20260915-sol, and open a Draft
  PR with HOLD-FOR-SOL. No merge-on-green label and no native auto-merge.
- [ ] Fresh-read the incumbent Fable thread after final evidence, then send the exact head,
  PR and tests for independent review/composition. Delivery is not acknowledgement.
- [ ] Keep production profile activation, credential changes and live canaries held until
  approved eligible providers, budgets, current runtime gates and rollback are proven.
