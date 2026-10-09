---
key: FABRIC-GLM-CONTROLLER-HEALTH-NOT-WORKER-ADMISSION
claim: >
  At the 2026-10-09 local Fabric examination, the running GLM controller was
  HTTP healthy but did not advertise worker_capabilities=lease-v1. Its running
  process predated the installed gateway-capable source. A separate source-level
  shutdown defect was reproduced: its main-thread SIGTERM handler called
  BaseServer.shutdown() from the serving thread and deadlocked. The local
  controller source and CLI are now repaired and tested, but no production
  restart or Ubuntu GLM worker admission has been performed or accepted.
falsifier: >
  From the installed production controller, a read-only worker-capability check
  reports lease-v1; an approved, uniquely identified Ubuntu GLM-Codex canary then
  completes real provider execution, result retrieval, verified cleanup, and
  broker lease settlement under the existing worker admission path. A healthy
  HTTP status alone or local regression tests do not falsify this live gap.
so_what: >
  Do not count published provider slots, host reachability, or a 200 /health
  response as remotely runnable GLM capacity. Keep the existing Ubuntu GLM
  automatic-qualification hold and avoid copying long-lived provider credentials.
  Perform only the separately admitted controller recovery/release with rollback,
  require worker-capability readiness, and then run one new bounded worker
  canary without replaying the earlier transport-unproven operation. Keep
  Executive OS worker registration and its admission proof separate.
kind: runtime
verified_at: 2026-10-09
verified_by: >
  M2 live controller /health and PID inspection (worker_capabilities ABSENT);
  read-only Fabric provider/host/lease observations; isolated SIGTERM reproduction
  before repair and clean exit after repair; 42 passing focused
  tests/test_glm_shim.py, tests/test_glm_lease_capability.py,
  tests/test_glm_worker_gateway.py tests; read-only gateway startup preflight
  (three healthy controller accounts, two approved models, broker lease schema
  supported); local source SHA256 recorded below. No production restart.
scope:
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

# GLM controller health is not remote-worker admission

## Observed

The existing Fabric controller responds successfully on local `/health`,
while the dedicated worker-capability field is absent. The live process remains
the older generation. An earlier Ubuntu GLM qualification attempt was recorded
as transport-unproven, and its admission hold must not be inferred cleared.

The old main-thread signal handler called `httpd.shutdown()` while running
`serve_forever()`. An isolated fake-credential, ephemeral-loopback reproduction
hung on SIGTERM; no production process was signaled during this diagnosis.

## Local source repair and proof (not a release receipt)

Within the existing local Fabric kit (not the protected Mastermind Git source):

- `ext/glm_shim/glm_shim.py`: SIGTERM/SIGINT unwind via
  `KeyboardInterrupt`, retaining the existing finally-based socket/PID cleanup;
  SHA256 `66349fda0f785eaedc0a22628ae733375e074913cbc2c00807073945764af8c0`.
- `ext/glm_shim/shim_ctl.sh`: `worker-status` independently checks
  `worker_capabilities=lease-v1`; timed-out graceful stops preserve the exact
  process identity instead of using silent SIGKILL; SHA256
  `7061b329384db86624ff8030a23213608e07698a39c569b7cde83cbe5c9136fd`.
- `ext/tests/test_glm_shim.py`: isolated signal, legacy/worker health and
  unresponsive-stop regressions; SHA256
  `ef2ec51dc1058ae560d55625b813ac8e9a657cdd429c71f55e5b7b8d2a374417`.
- Focused three-file controller suite: **42 passed**, eight warnings, exit 0.
  Rollback copies exist locally for the previous controller and CLI source.

The new `worker-status` correctly returns `UNAVAILABLE` on the still-running
legacy controller. The gateway's model registry and existing broker DB passed a
non-mutating constructor/schema preflight. Neither observation proves a
production GLM worker executed.

## Remaining authorization and exact acceptance

1. Reconcile any active controller requests and preserve the installed source
   revision, release permission, current PID identity and rollback procedure.
2. Through the authorized service/release owner, perform a controlled activation
   of the reviewed capability-capable controller. Do not send a blind SIGKILL,
   touch provider credentials, or equate service restart with job acceptance.
3. Verify `worker-status` against the installed service, then prove an exact
   new Ubuntu GLM worker run with sealed request identity, provider lease,
   accepted result, terminal cleanup and lease settlement.
4. Only the existing host/admission owner may release the GLM qualification
   hold after that real-path proof. Executive-backed native worker
   registration remains an independently governed capability.

This discovery records an unresolved live installation gap and verified local
source fixes. It does not authorize a restart, production deployment,
credential migration, worker registration, or retry of an uncertain operation.
