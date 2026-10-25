---
key: EXECUTIVE-E1-IS-THE-ONLY-RUNNABLE-WORKER-PAIR
claim: >
  At protected Mastermind a7d2b3049e5cdc523e91e61a6e9d70a1cb911157 the installed Executive
  composition can run exactly one worker pair: provider codex, alias coo.sealed, execution
  profile sealed.worker.write.no-extensions.v1, adapter codex-cli, worker codex-01. The COO
  binding loader hard-requires adapter codex-cli, surface codex-exec and a write-capable
  dedicated-worker-account profile; job placement projects only provider and quota class, so
  the read-only research aliases (fast.research, standard.research) are unreachable on the live
  path; the phase1c composition builds exactly one broker client, one adapter and one worker.
  Therefore the first production acceptance milestone (E1) must be a sealed WRITE-class job.
falsifier: >
  A Job constrained to a non-codex provider or to the read-only research profile reaching the
  broker start operation on the installed path without a source change to
  control_plane/executive_service.py::_load_coo_execution_binding or to the single-adapter
  composition in scripts/executive_os_phase1c.py. Also falsified if
  control_plane/executive_runtime.py's placement projection starts carrying an
  execution_profile_id.
so_what: >
  Do not commission a read-only "useful task" as E1 and do not treat a second provider as a
  configuration flip. Choose the E1 task from the sealed write-class profile's declared paths and
  validators. Any second-provider (E2) plan is a source program (see
  DSC:EXECUTIVE-E2-MINIMAX-NEEDS-SIX-GATES-NOT-A-CONFIG-FLIP), and a read-only alias needs its
  own binding/placement change before it can be used for anything.
kind: constraint
verified_at: 2026-09-24
verified_by: >
  control_plane/executive_service.py:2045-2056 (adapter_id == "codex-cli", execution_surface ==
  "codex-exec", write_capable, auth_realm == "dedicated-worker-account");
  control_plane/executive_runtime.py:979-982 (projected["provider"], eligible_quota_classes only);
  scripts/executive_os_phase1c.py:1409-1545 (one WorkerBrokerClient, one RemoteCodexWorkerAdapter,
  worker_id default "codex-01"); config/executive_worker_routes.json (only provider codex enabled,
  production_armed false); re-verified by the Fable delivery principal on 2026-09-24 and recorded
  on Mastermind #600 comment 5807514057.
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - control_plane/executive_service.py
  - scripts/executive_os_phase1c.py
confidence: verified
---

# E1 is the only runnable worker pair

The Executive OS backend at `a7d2b304` composes one Codex worker and refuses every other
provider, adapter or profile at three independent points: the COO binding loader, the placement
projection (provider + quota class only, no profile), and the phase1c composition (one adapter,
one worker). The read-only research aliases exist in the routes policy but cannot be reached.

E1, the first installed production acceptance milestone of the Executive/Capacity Fabric
program, therefore has to be a sealed WRITE-class job through `coo.sealed`. E2 (a second
provider) is a source program, not a config change.
