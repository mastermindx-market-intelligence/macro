---
key: LANE-KIT-BOUNDED-WORKERS-USE-ADAPTIVE-DEADLINES-AND-NATIVE-CONTEXT
claim: >
  The account-local Meta-CEO external-worker kit previously imposed several independent
  premature limits on bounded subagents: standalone Grok used a fixed 1800 second owned-process
  timeout, native remote workers used an approximately 200 second child window with a 600 second
  native-admission maximum, provider leases were fixed at 900 seconds, and Claude-harness MiniMax,
  GLM, and Go-Claude paths forced CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000. On 2026-10-06 these were
  repaired without removing the custody/recovery fuse: standalone Grok now defaults to 3600 seconds
  and admits an explicit 60-7200 second bound; native remote workers default to 3600 seconds and are
  hard-capped at 7200; non-native remote workers retain the 7200 second default; the special short
  go-codex profile remains bounded separately; provider lease TTL is derived from the owned child
  deadline plus settlement headroom; and the forced 200k context ceiling was removed in favor of
  provider/client native capacity with an explicit caller-supplied context ceiling when needed.
falsifier: >
  `K=~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08; grep -nE 'timeout=1800|REMOTE_SUB_MAX_SECS:-210.*NATIVE|assert 1 <= timeout <= 600|CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000' "$K"/ext/sub.sh "$K"/ext/remote_sub.sh "$K"/ext/native_remote.py`
  returning an active regression, or the installed pool-controller dry-run with
  `REMOTE_SUB_MAX_SECS=7200` no longer deriving a provider lease TTL near the owned-worker deadline,
  falsifies this record.
so_what: >
  A subagent timeout is a fabric safety/custody boundary, not evidence that the model cannot do long
  work. Long but bounded commissions can now receive useful runtime while preserving exact-process
  cleanup, one-carrier reconciliation, and a hard upper fuse. The fabric deliberately does not add a
  second transcript-compaction or memory plane for fresh bounded workers: large-context inexpensive
  models may retain task-local evidence up to their provider/client capacity, while packets remain
  bounded and unrelated cross-job history is not retained merely because a large context window exists.
kind: runtime
verified_at: 2026-10-06
verified_by: >
  Sol implementation on m2studio against the installed ~/.local/bin/pool carrier and account-local
  kit. Protected Mastermind procedure pin a6d40ff648671b03bd4d829d84dd066b58ea8c3f. Post-change
  SHA-256: ext/sub.sh 2ca8cb8515a99ee43cbb528519b2d0705b530c9f849e983466ed5b556f4cf36e;
  ext/remote_sub.sh 8fc4c8a4e2aa2832157d5eaee019e97ae0255475501dfba5f1f03173ca1187d2;
  ext/native_remote.py 59b9faac90ea2b96886e819b9d75396b26546827ec1d2c2971739c5a2ccb0d6c;
  ext/lane2.py 568617902bba8b6e410b2974a236c95501c4a50c2dc5ae517ce6ab0f470bd921.
  Syntax/compile plus targeted regression verification passed 117 tests and 7 subtests. Installed
  pool-wrapper dry-run canaries derived provider TTL 3890 for the 3600-second native default and
  7490 for REMOTE_SUB_MAX_SECS=7200, without acquiring a real provider lease.
scope: [macro, fleet-lane-hosts, meta-ceo-kit, executive-capacity-fabric]
confidence: verified
---

## Detail

The executable kit is account-local at
`~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08`;
it is not tracked in this repository. This discovery is the durable Agent OS continuity/evidence
record for the live implementation and does not itself arm, route, schedule, compact, or grant a
worker.

### Runtime policy after the repair

- Standalone local Grok: default 3600 seconds. `POOL_CHILD_TIMEOUT_SECONDS` may set 60-7200.
- Native remote modes other than the special go-codex profile: default 3600 seconds, maximum 7200.
- Non-native remote modes: existing 7200 second default retained.
- go-codex: its deliberately short profile and child ceiling remain intact.
- Provider lease TTL: `child_timeout + 300` seconds, bounded to 900-7500, so lease custody covers
  the worker and settlement/reconciliation headroom.
- Native admission accepts a matching deadline up to 7200 seconds. Timeout still follows the
  existing owned-process process-group cleanup and typed receipt path; a timeout is never evidence
  that a modifying effect did not occur.

### Context policy after the repair

The fabric does **not** implement its own automatic transcript compactor. Workers are commissioned
with fresh, bounded task-local contexts. Within a commission, active MiniMax/GLM/Go-Claude launch
paths no longer impose the old unconditional 200k ceiling. `POOL_MAX_CONTEXT_TOKENS` can explicitly
bound Claude-harness workers for a particular commission, and lane2 also accepts
`LANE_MAX_CONTEXT_TOKENS`.

This is intentional: context-window size and task scope are separate controls. A large model context
can preserve relevant task evidence during a difficult bounded job, but it is not a reason to inject
unrelated prior jobs or keep a worker alive indefinitely. If a future persistent/multi-phase worker
requires semantic context reduction, that should reuse the canonical checkpoint/continuation owners
and be justified by observed context pressure rather than introducing a parallel memory/session plane.

### Verification boundary

The changed-path regression set is green: 117 tests plus 7 subtests, in addition to shell syntax and
Python compile checks. A wider account-local kit run completed 1467 passes with 33 failures in
unrelated/current-fixture-policy areas; it is therefore not claimed as globally green. One
remote_sub_exec timeout test was red under the loaded broad run but green in the targeted regression
set, consistent with host-load sensitivity already covered by the owned-process cleanup tests.

No paid provider canary was used for this policy change because current host admission did not expose
an automatically eligible Grok remote target. The installed `pool` wrapper was nevertheless exercised
through its real controller in `--dry-run` mode, proving the live timeout-to-lease calculations without
creating a provider effect.
