---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/opencode-go-pool
model: sol
ended_because: ci_handoff
mission: >
  Continue draft #7142 as the Executive Capacity Fabric's OpenCode Go composition checkpoint:
  compose the already-tested parser, selector and transport pieces, preserve account-shared usage
  semantics, request-time freshness and exclusion identity, document the exact implementation and
  test receipts, and keep every runtime, enrollment and policy gate explicitly unresolved.
state_before: >
  Three separately tested source pieces had no proven composition. Parser floating-point output was
  rejected by the selector, exclusions had no stable-membership input, freshness was checked only at
  snapshot time, and AuthError triggered account switching.
changed:
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-14-OPENCODE-GO-COMPOSITION.md
    what: >
      This continuation record: the composition checkpoint, the exact Macro and Mastermind
      implementation receipts, the synthetic Linux test result, the unproven native and production
      gates, the policy boundaries, and the exact next action.
  - path: engine/provider_account_pool.py
    what: >
      Compose existing Macro usage rows into account-shared observations; support fractional
      percentages, request-time freshness, exclusions without changing membership identity, reset
      re-observation and exhausted-status precedence; and add transport behavior that freezes request
      state before callbacks, limits forwarded headers, rejects opaque account-scoped replay context,
      suppresses sensitive ordinary repr/tracebacks, and stops on AuthError.
  - path: tests/test_provider_account_pool.py
    what: >
      Add the provider account pool suite exercised in the record's Linux sandbox result.
  - path: tests/test_provider_account_pool_composition.py
    what: >
      Add the combined parser/selector/transport composition suite exercised in the record's Linux
      sandbox result, including the three-turn continuity test.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Wire the two provider account pool suites into a new hermetic `gate: code` job rather than
      appending them to the `gate: data` capability-broker job.
prs: []
verified:
  - claim: "The recorded Linux sandbox run passed 84 synthetic pool, transport and combined parser/selector/transport tests."
    command: >
      In the record's Linux sandbox with Python 3.13.5 / pytest 9.0.2: `python -m pytest
      tests/test_provider_account_pool.py tests/test_provider_account_pool_composition.py -q`
    result: "36 pool tests, 41 transport tests and 7 combined parser/selector/transport tests; 84 passed."
unverified:
  - claim: "The three-turn test preserves one process, temporary workspace marker, model, local tool-result transcript and session across simulated A/B/C successes."
    what_would_verify: >
      Run the named suite on the exact implementation bytes in a controlled environment and compare
      its result and published code/test blob identities to the tested bytes.
  - claim: "Native MacBook workspace workflow readiness."
    what_would_verify: >
      Replay the native workspace check after resolving the recorded platform block; a device ping is
      not readiness.
  - claim: "Real model recall, native installation, account independence or production canary behavior."
    what_would_verify: >
      Satisfy the applicable native, enrollment, policy and runtime gates, then run the bounded real
      coding-agent task and prove its visible workspace result.
  - claim: "Full repository CI, independent review or Agent OS store validation."
    what_would_verify: >
      Run full repository CI, independent source review and current-parent reconciliation, then run
      Agent OS store validation.
unresolved:
  - "The MacBook native workspace check was platform-blocked and was not replayed via another device."
  - "Rotation-safe enrollment identity, canonical refusal/cooling feedback, reservations and accepted pool binding remain pending."
  - "The usage endpoint does not supply an identity witness."
  - "No exception to OpenCode's current Terms restricting multiple-account circumvention was verified."
  - "Training-enabled models remain excluded from proprietary workloads; paid overflow stays outside this approval."
  - "Full repository CI, independent review and Agent OS store validation were not established by the recorded synthetic run."
next_actions:
  - "Sol should complete the reviewed single-account streaming harness binding on the existing #622 carrier after independent source review and current-parent reconciliation."
  - "Use existing provider-home enrollment, transcript custody and broker boundaries."
  - "Only with the applicable native, enrollment, policy and runtime gates satisfied may a bounded real coding-agent task run."
  - "Prove its visible workspace result first; an approved pooled rollout additionally needs real identity, A/B/C continuity, cancellation/partial-stream safety and simultaneous-claim proof."
  - "Preserve existing carriers and retrieve the full checkpoint before continuing."
do_not_redo:
  - "Do not treat device ping as native workflow readiness, or retry a refused effect through a worker or another carrier."
  - "Do not make the kernel a worker-private streaming proxy; it remains buffered/injected source."
  - "Do not treat the selector as an atomic concurrency allocator."
  - "Do not overwrite #583's concurrently owned credential/ACL fixes or substitute older source."
  - "Do not merge or arm #583/#7103/#622/#7142/#7143 through this work."
  - "Do not mark `usage_policy_satisfied` true from registration or acceptance of ban risk."
  - "Do not call these synthetic tests production proof or restore generic AuthError switching."
danger_areas:
  - "Registration is not credential enrollment or independent entitlement proof."
  - "Membership hashing and this record do not grant a post-START pool carrier."
  - "No keys were read/enrolled/copied, provider requests made, services installed or workers launched."
  - "OpenCode's current Terms explicitly restrict multiple-account circumvention; no exception was verified."
  - "Keep strict provider_capacity.v1, placement and existing credential owners unchanged."
---

## Executive Capacity Fabric - OpenCode Go composition checkpoint

Parent: `WS:EXECUTIVE-CAPACITY-FABRIC`; owner Sol; capability state PARTIAL / BUILT_NOT_PROVEN. This is a continuation record on draft #7142, not a new workstream, runtime assignment or final acceptance.

Procedure pin: protected Mastermind `51b815ab9527e15c9218b049f622dc4d3e0bfbc4`, Skillpack 1.0.1 / bootstrap 1. Current Chairman explicitly continued the existing program and reported all three Go registrations ready. Registration is not credential enrollment or independent entitlement proof.

## Source change and evidence

Before: three separately tested source pieces did not have a proven composition; parser floating-point output was rejected by the selector, exclusions had no stable-membership input, freshness was checked only at snapshot time, and AuthError triggered account switching.

After: existing Macro usage rows compose into account-shared observations; selector supports fractional percentages, explicit request-time freshness, exclusions without changing membership identity, reset re-observation and exhausted-status precedence. Existing transport freezes request/model/context before callbacks, limits forwarded headers, rejects opaque account-scoped context for replay, suppresses sensitive ordinary repr/tracebacks, and stops on auth errors. Neither membership hashing nor this record grants a post-START pool carrier.

Exact implementation receipts:
- Macro #7142: `814e6d4e6aaa13d27f9302febf954a780923db6c`.
- Macro #7143: unchanged `d8127bded3a9a35bc501e786d27fa32f0ecdd923`, still stacked on #7103.
- Mastermind #622 implementation: `f68fc0c62552bfd4a4994792698e7064899d008f`.
- Mastermind #622 cross-repo proof: `a2a529e6d633b2e6aa522b294d531fa4db525de0`.
- Full checkpoint: Mastermind `097e1bac090be8f254013a2729e0f7ef69c94054`, `docs/OPENCODE_GO_COMPOSITION_CHECKPOINT_2026-09-14.md`.

Linux sandbox, Python 3.13.5 / pytest 9.0.2: 36 pool tests, 41 transport tests, 7 combined parser/selector/transport tests; **84 passed**. Published code/test blob identities matched tested bytes. The three-turn test preserves one process, temporary workspace marker, model, local tool-result transcript and session across simulated A/B/C successes. All credentials, provider usage and inference outputs are synthetic. No real model recall, native installation, account independence or production canary was proven. Full repository CI, independent review and Agent OS store validation were not established by this run.

## Current gates and non-goals

The MacBook native workspace check was platform-blocked and was not replayed via another device. No keys were read/enrolled/copied, provider requests made, services installed or workers launched. Do not treat device ping as native workflow readiness, and do not retry a refused effect through a worker or another carrier.

The kernel remains buffered/injected source, NOT a worker-private streaming proxy. The selector is not an atomic concurrency allocator. Rotation-safe enrollment identity, canonical refusal/cooling feedback, reservations and accepted pool binding remain pending. The usage endpoint does not supply an identity witness. Keep strict provider_capacity.v1, placement and existing credential owners unchanged.

#583 is concurrently owned and has advanced; do not overwrite its credential/ACL fixes or substitute older source. This work does not merge or arm #583/#7103/#622/#7142/#7143. Older PR body statements about automatic auth rollover are superseded by the narrower implementation and checkpoint, not evidence of live behavior.

OpenCode's current Terms explicitly restrict multiple-account circumvention. Do not mark `usage_policy_satisfied` true from registration or acceptance of ban risk. No exception was verified. Training-enabled models remain excluded from proprietary workloads; paid overflow stays outside this approval.

## Exact next action

Sol should complete the reviewed single-account streaming harness binding on the existing #622 carrier after independent source review/current-parent reconciliation. Use existing provider-home enrollment, transcript custody and broker boundaries. Only with the applicable native, enrollment, policy and runtime gates satisfied may a bounded real coding-agent task run. Prove its visible workspace result first; an approved pooled rollout additionally needs real identity, A/B/C continuity, cancellation/partial-stream safety and simultaneous-claim proof.

No Fable or other worker was commissioned; no watcher is waiting. Preserve existing carriers and retrieve the full checkpoint before continuing. Never call these synthetic tests production proof or restore generic AuthError switching.
