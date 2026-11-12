# Metabolism → Capacity Fabric cutover — handoff (2026-11-12)

Chairman order 2026-11-12: all estate AI routing moves to the Capacity Fabric
`unified_router`. This record covers the metabolism loop, which is the largest
dead consumer in the estate.

## State

| Fact | Value |
|---|---|
| Adapter | `lib/fabric_client.py` — shipped in **PR #11160** |
| Metabolism cutover | **PR #11177**, stacked on #11160 |
| Branch | `claude/metabolism-fabric-cutover-20261112` |
| Default | **INERT** — no behaviour change unless `FABRIC_ROUTER_TOKEN` is in the process env |
| Kill-switch | `MACRO_METABOLISM_FABRIC=0` |

## Why the loop was dead

The metabolism legacy waterfall's primary pool — `CLAUDE_CODE_OAUTH_TOKEN_1..7` —
has been `auth_failed` / `rate_limited` since 2026-11-06. Every stage therefore
degraded to floor-only output. Flipping the `AUTONOMY_PAUSED` repo variable to
`false` without this cutover only re-runs a dead ladder.

## What the cutover touches

`engine/metabolism/fabric_lane.py` (new) is the single router entry point.
Nine call sites branch into it; `engine/llm_auth.py` is **not** modified, so the
neural-web / cortex / brain lane, `engine/master_brain.py` and marketing are
untouched.

| stage | file | lane |
|---|---|---|
| attention | `engine/metabolism/attention.py` | fast |
| agenda | `engine/metabolism/agenda.py` | fast |
| propose | `engine/metabolism/propose.py` | fast |
| adjudicate | `engine/metabolism/adjudicate.py` | balanced |
| audit | `engine/metabolism/audit.py` | balanced |
| standout cohort audit | `engine/metabolism/standout_auditor.py` | fast |
| prophet pick autopsy | `engine/metabolism/standout_auditor.py` | fast |
| dream resummary | `scripts/metabolism_dream.py` | fast |
| shadow-cycle agenda | `scripts/metabolism_agenda.py` path | fast |

`audit` and `adjudicate` take **balanced** because they are fail-closed
production-protection gates; the rest are advisory generation.

## Invariants worth not re-litigating

- **One request, no local retry.** The router owns provider selection, cooldown
  and pooling. The PR-R8 Opus retry ladders are bypassed on the fabric path and
  left intact for the legacy path.
- **`FabricUnavailable` falls through** to the legacy ladder (nothing was served,
  nothing billed). Any other router error degrades the stage and never retries.
- **Fail-closed stays fail-closed**: an empty/unparseable audit or adjudicate
  reply still blocks the merge.
- **Token-free paths stay token-free**: `allow_fabric=False` guards the attention
  stage-local structural heal (`effective_allocation`) and the shadow harness's
  `--no-llm` mode.
- **Usage**: `Completion.usage` mapped onto the `lib.ai_costs` row shape;
  `provider="fabric"` is treated as non-metered in `scripts/metabolism_propose.py`
  so the $25 metered circuit breaker is not charged for a router-billed call.

## Wiring (no workflow edit needed)

`metabolism-cycle.yml` / `metabolism-agenda.yml` and the brief job all run on
`[self-hosted, macstudio]`, the host that exports `FABRIC_ROUTER_TOKEN` for the
loopback router. Absent that export, the lane is simply inert.

Verified from this session: the router answers on `127.0.0.1:8313` (401 without
a token, so it is up and enforcing auth). The token was **not** present in the
build host's shell environment, so live verification of a routed metabolism call
was not possible from here — it must be done on the render host or with the
token exported.

## Remaining work (not in #11177)

1. **BUILD stage dispatch.** `scripts/metabolism_dispatch.py` prints
   `CHOSEN_KEY=claude_code_oauth_1` — the BUILD step launches a headless Claude
   Code session keyed by the capability broker, not an API call, so
   `fabric_client` cannot serve it. Reviving the loop end-to-end still needs a
   working key for that one surface, or an explicit decision to leave BUILD inert.
2. **`budget_gate` blind-burn guard.** `engine/metabolism/budget_gate.py:184`
   parses `anthropic-ratelimit` headers for key-pool accounting. Fabric-routed
   calls emit none, so `known_readings` can be 0 and `metabolism-cycle.yml`'s
   R-V12-9 guard refuses to chain in `5h_max` / `weekly_max` modes. Only bites
   auto-run burn modes; the default `off` mode uses the pace gate.
3. **Arming.** `AUTONOMY_PAUSED` is a GitHub repository variable
   (`gh variable set AUTONOMY_PAUSED --body false`), operator-only. Do not arm
   until #11160 and #11177 are merged AND the token is confirmed on the runner —
   otherwise the loop re-runs a dead ladder with no signal.

## Verification performed

`tests/test_metabolism_fabric_cutover.py` — 30 tests, all stub-based, green.
Full metabolism sweep: 459 passed, 2 failed; both failures are this sparse
worktree's `var/` path fault (`[Errno 20] Not a directory: 'var'`) in
`test_register_contracts_writes_trial_ledger` and
`test_propose_end_to_end_injected`, neither of which touches the cutover.
