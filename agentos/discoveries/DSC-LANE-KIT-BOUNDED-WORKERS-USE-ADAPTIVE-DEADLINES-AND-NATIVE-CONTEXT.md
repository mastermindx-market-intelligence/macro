---
key: LANE-KIT-BOUNDED-WORKERS-USE-ADAPTIVE-DEADLINES-AND-NATIVE-CONTEXT
claim: >
  The account-local Meta-CEO external-worker kit used several independent premature worker limits:
  standalone Grok had a fixed 1800 second owned-process timeout, native remote work could be reduced
  to an approximately 200 second child window with a 600 second native-admission ceiling, provider
  leases were fixed at 900 seconds, stale callers could still force complex work back to 240-600
  seconds, Claude-harness MiniMax/GLM/Go-Claude paths had an unconditional 200k context ceiling,
  and the OpenCode-free wrapper still carried a separate 900 second inner alarm. The live kit now
  treats deadlines as custody/recovery fuses rather than productivity targets: long bounded work is
  allowed up to a two-hour hard ceiling, complex/frontier classifications receive runtime floors,
  provider leases cover the owned child plus settlement headroom, slot-owned provider sessions are
  reconciled through the canonical process-census owner, qualified large-context Claude-Code-backed
  workers use their qualified window with late native client compaction, and no second fabric
  transcript/memory plane is introduced.
falsifier: >
  `K=~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08; grep -nE 'timeout=1800|REMOTE_SUB_MAX_SECS:-210.*NATIVE|assert 1 <= timeout <= 600|CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000|OC_FREE_TIMEOUT:-900' "$K"/ext/sub.sh "$K"/ext/remote_sub.sh "$K"/ext/native_remote.py "$K"/ext/oc_free_exec.sh`
  returning an active regression, a C2/C3 remote request being reduced below its reviewed floor, a
  slot timeout leaving a descendant process alive, or a 7200-second remote dry-run no longer deriving
  a provider lease TTL near the owned-worker deadline falsifies this record.
so_what: >
  A timed-out worker is not evidence that the model was incapable of the task. Long but bounded
  commissions can now finish without old controller ceilings silently killing useful work, while
  hung CLIs still cannot retain scarce slots indefinitely. Context-window size is separated from
  task scope: inexpensive large-context workers may retain relevant evidence for their current
  bounded commission, but unrelated cross-job history is not injected or preserved merely because
  the model supports a large window.
kind: runtime
verified_at: 2026-10-07
verified_by: >
  Sol red-team continuation on m2studio against the installed ~/.local/bin/pool carrier and
  account-local kit. Protected Mastermind procedure pin
  c7e47c859eb2925c5626931fd511800773ba09ac, Skillpack v1.0.1. Current live SHA-256:
  ext/sub.sh ea56fe81c19527450717a2f17f4ad29f35b58bef07dfaa4906b8d23b87868005;
  ext/remote_sub.sh d3d909877c03e79d53d5d25852c11221e3580dde0381a160050c9afc7e02c30a;
  ext/native_remote.py 3821d9d11684e97622103416ffd88f6f9955df3121389183af8eb6f5ac931e36;
  ext/remote_sub_exec.py e3d583218f16995315005469d0f4aa11f0221eec2d30823f7e4f3360dada917d;
  ext/lane_runtime.py 0a49c645d72824a57d6c1b68304abc13c410513cc45a2968a599d2aba1cf9796;
  ext/lane2.py d25d7a259202dc44af149e7acf9e2eef8d8e80489f0fb0bb8d7c0df35942a9e1;
  ext/slot.py 37b334366d90e22076add744714488b1b86f51185d5d34d43dfd16131c7d53f4;
  ext/oc_free_exec.sh 0024fbfaf2ce4b9d80e029e219ac43c791f3d80b5bcd10a5526c4a3c99ec6a21;
  ext/codex_glm/config.toml 811b8f5bafc2e97ddfe53ad617a8ef1f9588a80528b9d0ed93792317b23cbf64;
  ext/codex_minimax/config.toml 7bde4dac1c9773c27395db513006055e6dc9605f93adf8141c7de6186dded8aa;
  ext/pick.py a5b07eaa2f005340293f026e8db447a785f65036181ff7283f94602cee6eddfe;
  ext/glm_codex_exec.sh fd521b24950a9f8e5f81263037a531f34000b75189fa451ff7e42ee057869bec;
  ext/mm_codex_exec.sh 2589edc96fa1056fd06056be355400557a755ab90931cd9f62a324e94dba93f2.
  Latest focused red-team regression: 175 tests passed plus 7 subtests. Earlier installed-pool
  dry-runs proved adaptive lease TTLs of 3890 seconds at the native 3600-second default and 7490
  seconds at the 7200-second max.
scope: [macro, fleet-lane-hosts, meta-ceo-kit, executive-capacity-fabric]
confidence: verified
---

## Current implementation

The executable kit is account-local at
`~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08`;
it is not tracked in this repository. This discovery is the durable Agent OS continuity/evidence
record for the live implementation. It does not itself arm, route, schedule, compact, or grant a
worker.

### Runtime and lease policy

- Standalone local Grok defaults to 3600 seconds and admits an explicit
  `POOL_CHILD_TIMEOUT_SECONDS` from 60 through 7200.
- Native remote work defaults to 3600 seconds; non-native remote work retains a 7200-second default.
  The universal normal remote hard ceiling is 7200 seconds.
- `C2_COMPLEX_BOUNDED` receives a 3600-second floor and `C3_FRONTIER_JUDGMENT` a 7200-second
  floor. Legacy unclassified non-go-codex callers also receive a 3600-second floor, preventing old
  300/600-second launch overrides from silently truncating real worker labor. C0/C1 may still choose
  short bounded probes deliberately.
- The special go-codex profile remains intentionally short and separately bounded; this repair does
  not silently widen that different product contract.
- Provider lease TTL is derived as owned-child timeout plus 300 seconds of settlement/reconciliation
  headroom, bounded to 900-7500 seconds. Native admission verifies that the held lease covers the
  requested worker window plus settlement margin.
- Lane2 validates fix/review deadlines before creating lane state: fix defaults to 3600, review to
  2400, both accept 60-7200, and their C2/C3 task classifications apply the same floors.

Historical lane evidence is why the floors exist rather than merely changing defaults. On 2026-10-06
multiple useful GLM workers ended `rc=124 signal=timeout reason=owned_child_timeout` under stale
300-600 second outer budgets, including `rs_20261006T121443Z_48029`,
`rs_20261006T205642Z_47176`, `rs_20261006T211612Z_90859`, and
`rs_20261006T212744Z_18957`. A C2 GLM-5.3 review was also observed under a 240-second outer budget.
The repaired policy therefore protects classified long work from stale callers while retaining a
hard upper fuse.

### Slot/process red-team result

A first attempt at slot-level wall-clock enforcement exposed an orphan hazard: terminating only the
direct wrapper PID could leave a background grandchild alive. The current slot implementation no
longer owns ad-hoc descendant cleanup. It creates the provider wrapper as an exact process session and
delegates timeout, lease-loss, parent-signal, and normal-exit reconciliation to
`lane_runtime.settle_owned_process_session`, which reuses the incumbent verified process-census /
termination owner.

Hermetic tests prove timeout returns rc=124 with the descendant gone, prove a wrapper that exits 7
cannot leave a background descendant behind, and prove parent SIGTERM reconciles the exact nested
provider session. These process-cleanup regressions are included in the latest 175-test focused pack.

### Context and compaction policy

The fabric does not create a second transcript or memory authority. Workers receive fresh bounded
task-local packets. For qualified Claude-Code-backed MiniMax M3 and GLM 5.3 workers the current kit
sets a 1,000,000-token context window and lets the existing Claude Code client compact late, defaulting
its native auto-compact window to 900,000 tokens. MiniMax M3 / GLM Flash get a larger default
Claude-worker turn fuse of 240; the general Claude-backed default is 120 and the explicit hard maximum
is 400.

`POOL_MAX_CONTEXT_TOKENS`, `POOL_AUTO_COMPACT_WINDOW_TOKENS`, and `POOL_MAX_TURNS` may tighten
one commission; lane-local equivalents exist where applicable. Context overrides above the currently
qualified 1M window fail closed. A compaction override must be within 100K-1M and cannot exceed its
known context window. The remote launcher forwards these controls. MiniMax lane settings are applied
to a copied child environment rather than mutating the long-lived lane driver, preventing provider
context/auth settings from leaking into a later reviewer.

The installed Claude Code 2.1.287 binary recognizes both `CLAUDE_CODE_MAX_CONTEXT_TOKENS` and
`CLAUDE_CODE_AUTO_COMPACT_WINDOW`; this policy therefore uses the provider client's existing
compaction facility rather than adding a fabric transcript store or summarization lifecycle.

The Codex-backed MiniMax/GLM routes needed the same treatment. MiniMax-M3 and GLM-5.3 are absent from
Codex CLI 0.159.3's 11-model bundled catalog, while the binary exposes the top-level
`model_context_window` and `model_auto_compact_token_limit` configuration keys. The live
`codex_minimax/config.toml` and `codex_glm/config.toml` now bind the qualified 1,000,000-token
window and 900,000-token late-compaction limit explicitly. Both wrappers copy those configs into their
private scratch CODEX_HOME before `codex exec`, so the policy is task-local. Redacted `codex doctor
--json` readback reports `config.load status=ok` for both profiles with the intended custom model
and provider; no inference/provider dispatch was needed for that proof.

### Additional stale inner ceiling found

The OpenCode-free wrapper still had `OC_FREE_TIMEOUT:-900`, which could terminate a useful worker
after 15 minutes even though slot custody allowed substantially longer bounded work. The live source
now defaults that inner call fuse to 3600 seconds, defaults C3 frontier work to 7200 seconds, and
accepts only explicit integer values from 60 through 7200 before slot admission. Source tests for the
legacy-default removal and invalid-value refusal are present.

The OpenCode-free timeout validation now has executable post-edit proof in the latest focused
regression pack. Invalid timeout values fail before slot/provider admission; the legacy 900-second
default is absent from the live wrapper.


### Go short-capability boundary

Go is intentionally different from the long-runtime pools. Its current remote bearer capability keeps
the child at <=240 seconds and the transport capability at <=300 seconds. That security lifetime was
not widened to fit long work. Instead, `pick.launch_policy` refuses `go` / `go-codex` for
`C2_COMPLEX_BOUNDED` and `C3_FRONTIER_JUDGMENT` with typed reason
`go_short_capability_only_for_c0_c1`, while preserving registered C0/C1 leaf work. `sub.sh` and
`remote_sub.sh` both pass task complexity into the launch-policy gate before provider execution.

The independent launch-policy regression passed and is included in the latest focused pack. One UX
residual remains fail-closed: the automatic execute candidate walk can still choose Go first for a
C2/C3 request, after which launch policy refuses it, instead of transparently selecting the next
long-runtime-capable pool. That does not permit a too-short provider effect, but can waste one routing
attempt.

### Turn-continuation budget

A separate red-team pass found that long Codex-backed GLM/MiniMax workers could hit the wrapper's
fixed two-resume auto-continue ceiling even when the outer wall-clock budget and context window still
had room. The wrappers now derive bounded defaults from task complexity: 2 resumes for ordinary work,
4 for C2, 8 for C3, with any explicit override capped at 12. The lane driver forwards fix/review task
complexity in a copied child environment so settings do not leak into the parent process.

Auto-continue exhaustion is fail-closed: if no terminal `STATUS: COMPLETE` / `STATUS: BLOCKED` (or
the special PONG canary) appears when the bounded resume budget is exhausted, the wrappers now return
typed rc=77 rather than false-success rc=0. This is deliberately distinct from rc=76, which the runtime
reserves for lease/cleanup uncertainty. `remote_sub.sh` settles a cleanup-proven rc77 normally and
records `reason=terminal_status_missing`; rc76 retains effect-unknown/lease-loss semantics. This fixes
a red-team finding where report exhaustion could unnecessarily preserve a provider lease and be
misdiagnosed as lease loss. The focused wrapper/context/remote taxonomy pack passed **113 tests**.


### 2026-10-08 continuation hardening

A further local-Grok audit found that the direct `sub.sh grok` path still defaulted every worker to
3600 seconds even when the commission was already classified `C3_FRONTIER_JUDGMENT`. The live
account-local source now derives the direct Grok worker timeout from the same reviewed complexity
semantics as remote execution: ordinary/C2 defaults remain 3600 seconds, C3 defaults to 7200 seconds,
and stale explicit short overrides are lifted to 3600 for C2 or 7200 for C3. C0/C1 callers may still
intentionally request shorter bounded windows. Source SHA-256 is
`3ac95f16be472483fcd7f1957a4c9837174a23fa9b012733e971e38b0026c697`.
The direct Grok path now also treats turn count as a bounded productivity fuse rather than a hidden
short-task default: 140 turns for ordinary work, 240 for C2, and 400 for C3, while an explicit
`POOL_MAX_TURNS` may tighten one commission and values outside 1..400 fail before provider launch.

The same principle now applies to Claude-backed MiniMax/GLM workers. Existing ordinary defaults remain
120 turns, or 240 for the cheap MiniMax-M3 / GLM Flash profiles. C2 receives at least 240 turns and C3
receives 400, while explicit `POOL_MAX_TURNS` still tightens a single commission and values outside
1..400 fail closed. This removes another hidden short-task ceiling without turning bounded workers
into unbounded agents. The combined context/Grok policy regression passed **87 tests**; the dedicated
Grok suite alone remains **59 tests**. Current policy-test SHA-256:
`cb85f1feb71acc4bd0fd2a9aecc01fac3ed4cda2b66082f611a028d50f09aab8`.

Live carrier evidence also confirms that the widened remote policy is being consumed by real workers,
not only hermetic tests: a C2 Grok review on ubuntu2 ran approximately 327 seconds and settled rc=0
under a 3600-second native window, while a C2 MiniMax-M3 build on mini2 ran approximately 902 seconds
and settled rc=0 under a 7200-second controller window. Both exceed historical short ceilings that
previously terminated useful work.

The ordinary non-native remote controller source has also been tightened for completion visibility:
its default completion poll interval is now 30 seconds rather than 150 seconds while preserving the
same 7200-second hard controller ceiling. That source change is readback-installed but remains
**BUILT_NOT_PROVEN by executable post-edit regression** because the bounded validation invocation was
explicitly safety-blocked before dispatch. No alternate carrier or equivalent retry was used.

Two fail-closed residuals remain known. First, the leased `glm-codex` branch in `sub.sh` still
forces `GLM_CODEX_MAX_CONTINUES=0`, suppressing the newer bounded same-session continuation policy on
that entry path; the direct repair attempt was safety-blocked before dispatch and has not been retried.
Second, automatic execute selection may still choose the intentionally short Go capability for C2/C3
and then be refused by launch policy rather than preselecting the next long-runtime-capable pool.
Neither residual permits a too-short long worker to run silently, but both remain hardening targets.

### Return-code taxonomy hardening

The worker/controller boundary now separates three materially different end states instead of
overloading rc76: rc124 is a proven wall-clock child timeout; rc76 remains reserved for lease/cleanup
uncertainty or capture paths that require reconciliation; rc77 is a cleanup-proven worker result whose
bounded same-session continuation budget ended without a required terminal status. GLM Codex,
MiniMax Codex, Go Codex, Qwen, and OpenCode-free wrappers all use rc77 for
`terminal_status_missing`. This lets the controller release capacity on a known failure instead of
holding a lease as if execution state were uncertain.

Current relevant SHA-256 after this taxonomy pass:
`glm_codex_exec.sh 87727f94b2f555ed3426f8ccadf808b8a0dcdb6f746dc13ad96a808f8c2784cf`;
`mm_codex_exec.sh 3a48e82a58fd647db2d8a71cea58a6961fb8fd42e2ba2c5d428502229ad522ef`;
`go_codex_exec.sh c557ec6db7e8a2d02dcb0746192ee50a6df6368c7b607195dfd57c4a204ae02c`;
`qwen_exec.sh b4f7d934ae987636770db5254a7837014551d7331b079aeb723741bbf1eec16a`;
`oc_free_exec.sh 279842e54d6095276b087fd78eae9268026db3079add4b61e474119ce08d3783`;
`remote_sub.sh 2dab8b40c5bad1acbb07eac7298090d5b9ae4bf8d9fac33cd2c8041167bdff66`.

### Lane-driver turn-budget hardening

The long-lived lane driver also had hidden fixed direct-CLI turn ceilings independent of its already
repaired wall-clock floors: Grok was hardcoded to 140 turns and the generic Claude fallback to 200.
The live `lane2.py` now derives those direct CLI budgets from the fix/review task-complexity field:
Grok remains 140 for ordinary work, C2 gets 240, and C3 gets 400; Claude remains 200 for ordinary
work, C2 gets 240, and C3 gets 400. An explicit `LANE_MAX_TURNS` may tighten the current lane to
1..400; invalid values fail closed. The MiniMax direct path was already at 400.

The helper is shared by fix and review steps but consumes the correct `task_complexity` or
`review_task_complexity` field for that step. Python compile plus the lane context/routing regression
completed **60 passed**. Current SHA-256:
`lane2.py c42bc5d75d06ec78280ea3c8dff87fb8be7da6c1d5892bff4d4f6c48ae77a4bc`;
`test_worker_context_policy.py ef34d79d0c78d79a718812bb55335a3c2ed5bd39966a1b199925fda2ab4fbcd0`.

### Review-only lane complexity controls

The standalone `review_lane.py` path also had independent fixed ceilings: Grok was hardcoded to
140 turns and the review subprocess defaulted to 2400 seconds regardless of known complexity. It now
accepts an explicit `--task-complexity` (or existing `POOL_TASK_COMPLEXITY` environment value) and
derives the same long-work floors without changing unclassified legacy behavior: C2 gets at least
3600 seconds and 240 Grok turns; C3 gets 7200 seconds and 400 turns. `--max-turns` may tighten one
review within 1..400 and `--timeout` remains bounded to 60..7200; invalid settings fail closed before
provider work.

Python compile plus the review-lane regression completed **17 passed**. Current SHA-256:
`review_lane.py 9f9417f04af067f2758bb9cc9d97e485aaec124af28ee4a36b93781657780778`;
`test_r22_job_class.py 52ebdf060dc81c3d44008cbbde9d59e162909a96a2fd5a3c8bf6bf6899f59ce0`.

### Qwen second-opinion ownership and runtime hardening

The independent `qwen_review.py` second-opinion path still wrapped `qwen_exec.sh` in a raw
`subprocess.run(..., timeout=3600)`. That created two problems for long work: C3 reviews could be
killed at one hour even though the fabric permits two hours, and killing only the wrapper did not use
the incumbent exact-process cleanup owner. The path now derives complexity from
`review_task_complexity`, `task_complexity`, or `POOL_TASK_COMPLEXITY`; C2 retains a 3600-second
floor and C3 gets 7200 seconds. `QWEN_REVIEW_TIMEOUT` may set a bounded 60..7200 value, but cannot
silently reduce an already-classified C2/C3 job below its floor.

The Qwen reviewer now runs through `lane_runtime.run_owned_process` with a per-review process receipt,
typed rc124 on wall-clock timeout, and rc76 on unproven cleanup or truncated result capture. It forwards
task complexity into `qwen_exec.sh`, so the wrapper's 2/4/8 same-thread continuation policy is active
for classified reviews. This reuses the incumbent process-census/cleanup owner rather than creating a
new retry or lifecycle plane.

Python compile plus the worker-context regression completed **43 passed**. Current SHA-256:
`qwen_review.py 0792849a1e33f2283a8ed9ce5b9bde70dfbf1791a083c8bc0d3cead03b57b5cc`;
`test_worker_context_policy.py 97847fc04624c17f55d8bbb9e0c5666d908ce872fcfb791b82251fec7df8e790`.

### Remote-lane provider-custody fencing

A deeper controller-failure audit found an older custody bug in `remote_lane_v8.sh`. The Studio-side
broker lease represented provider work executing under a remote `nohup lane2.py`, but the lease was
recorded against the Studio broker host and the Studio controller PID. Broker GC therefore could treat
controller death as proof that the remote provider worker died and immediately free capacity even
while that remote process was still running.

The live remote-lane acquisition now binds the provider lease to `HOST_KEY` (the remote worker host)
instead of the Studio controller host, and uses a 7500-second recovery TTL: one maximum 7200-second
owned child plus 300 seconds of settlement headroom. The existing 300-second controller heartbeat
continues renewing the lease while the controller is healthy, and the existing EXIT/INT/TERM/HUP trap
still releases it on a normal controller exit. If the Studio controller disappears without cleanup,
local PID death no longer falsifies remote-worker death; provider capacity stays fenced until the
remote-host lease actually expires.

Hermetic broker/source regressions prove a dead Studio PID does not reap a lease bound to a different
remote host, that the lease expires after its 7500-second no-heartbeat TTL, and that
`remote_lane_v8.sh` carries `--host "$HOST_KEY"`, `--ttl 7500`, heartbeat, and release-trap
semantics. The two new focused tests passed. A broader host-registry run had **36 passes / 3 failures**,
but all three failures are pre-existing registry expectation drift (mb/bmb max_active and m1 roles),
not failures of this change; they are not counted as green evidence for this lane.

Current SHA-256:
`remote_lane_v8.sh aaae84dfd05ce6c6cdfa1c9fbfcc16a025c5ca4cddd9c1a7494f1450fd75b5c5`;
`test_lease_broker.py fc137497c55d57ffbb50fc4b9be1d131d274c10278f028ea2963bc61178be061`;
`test_hosts_registry.py 5ed3f5d5f1e81acfe3f89e0e3e9f3ccbc0b6868dccf170a802a556581e8fc258`.

### 2026-10-08 direct source-writer reconciliation and lease-TTL red team

The GitHub PR writer identity is `mastermindx-2` (the connector GitHub account used for this
evidence carrier), not proof that a separate human or live AI session owns an exclusive source lease.
The PR has no recorded issue/review comments or source-writer lock. At inspection the M2 kit
`ext/active` directory had only its admission-lock file, and no Git commit/push/merge process
was observed. The ongoing remote workers were unrelated and were left untouched. This new delta
was reconciled against PR head `8af58e3a297d72cdd25eb85023447c4a7189abcf` using exact
file-revision compare-and-swap, without overwriting the other retained source evidence.

Additional live account-local `sub.sh` behavior for direct Grok workers is complexity-aligned:
ordinary jobs retain bounded defaults; C2 uses a minimum 3600-second worker deadline and 240 turns,
C3 uses a minimum 7200-second deadline and 400 turns, with explicit turn tightening only inside
1–400 and fail-closed invalid values. The previously accepted direct-Grok regression suite passed
59 tests. The Claude-backed worker context regression was run again and passed **43 tests**,
covering qualified 1M/900K context/late-compaction settings, context override bounds, long
complexity turns and independent Qwen/OpenCode-free checks.

A new independent slot-custody red-team found that `slot.py` could accept a non-finite lease
heartbeat grace (e.g. NaN or infinity). That can prevent the unknown-broker expiry comparison
from ever firing. The live account-local slot implementation now refuses invalid/unbounded
`LANE_LEASE_TTL_S` grace before host/provider admission, refuses it inside direct heartbeat
execution, and treats an invalid or above-7500-second held broker TTL as typed
`broker_ttl_invalid` lease loss. The maximum valid grace corresponds to the 7200-second
owned child plus 300 seconds of settlement headroom. Local source SHA-256:
`ext/slot.py 783db4d518e3f2768a321b779b540516d84cd553513b48edfdd488767241464d`;
`ext/tests/test_lease_typed_loss.py
4ff2f1be1ae88554c5a8aa78971483494ed523545f624bcb9c4d01be3214d724`.
A focused Python compile and the lease-loss tests passed **26 tests**.
A subsequent *broader* slot regression command was explicitly refused before dispatch by the
tool safety boundary; it was not replayed through another carrier and is **NOT VERIFIED**.
There is no evidence of failure of the focused 26-test set, but the broader sweep is not
claimed as green. Eight pytest Chromium temporary-cleanup warnings were unrelated.

The implementation is currently **LOCAL_VERIFIED; SELECTED_ON_UBUNTU2 / NOT FLEET-WIDE
PROVEN**. PR #8535 is an Agent OS evidence-only draft, not the executable kit's source
distribution. GitHub CI and fences on this discovery do not establish installation/selection
across all fleet hosts or production acceptance of each new failure branch. An observed C2
Grok remote launch for `paper-01a1101f-im05-summary-repair-r2` logged `SCP
support=executor-surface`, `SUPPORT_VERSION_READY`, a native 3600-second deadline,
and successful `NATIVE_SSH_RETURN rc=0`; its support manifest includes the exact new
`slot.py` SHA-256 `783db4d5...` and updated `sub.sh` SHA-256 `3ac95f16...`.
That proves the newest source package was selected and transported for that Ubuntu2 run,
**not** that the new lease-invalidity branch executed or that every fleet host has updated.
The controller/worker was not restarted or duplicated. A separate older remote worker
still had the earlier slot SHA in its own immutable launch manifest. Prior permission/
safety-denied automatic Go reroute and leased-GLM edits remain fenced; this evidence update
is not an authorization to retry them.

### Import-time configuration refusal follow-through

A later inspection found a narrower input-handling issue in the already hardened `slot.py`:
an invalid **non-numeric** `LANE_LEASE_TTL_S` raised an import-time `ValueError`
before the existing typed admission guard could run. This was fail-closed but lacked the
intended stable refusal result. The source now handles that parse error as a sentinel
non-finite TTL and lets its incumbent pre-host-admission guard return
`rc=78 admission_denied reason=lease_ttl_invalid`.

One direct local CLI canary with malformed TTL confirmed **rc=78** and the exact
typed denial before any host/provider admission. Python compilation and the
unchanged 26-test focused lease-loss regression also passed after this edit.
A separate attempted *new test-file append* was safety-refused **before dispatch**;
the new regression source was **not** installed and that denied write was not
retried through another tool. Do not equate the direct CLI canary with a new
committed regression test. Current local slot SHA-256:
`0d8c574c54d227361c523f51384ca8eab797362c5552f4caf7cb8df3160e1fd6`.
This newer hash supersedes the earlier `783db4d5...` slot hash only for **subsequent
launches**; the already launched Ubuntu2 worker retains its immutable, older
`783db4d5...` support-package receipt.

### 2026-10-08 remote Codex configuration parity — verified local repair

A follow-up red-team showed **remote Codex configuration parity was not established by
M2's local TOML files**: `ubuntu1`, `ubuntu2`, and `mini2` each retained
host-stable `codex_glm/config.toml` and `codex_minimax/config.toml` files
that lacked `model_context_window=1000000` and
`model_auto_compact_token_limit=900000`. All three reported matching stable
config SHA prefixes (`999f2b0146dd` for GLM and `74b450758efa` for MiniMax).
The incumbent `support_bundle.py` intentionally versions `mm_codex_exec.sh`/
`glm_codex_exec.sh` but symlinks those config directories back to host-stable
files; therefore the earlier `codex doctor` proof on M2 alone was not enough to
claim remote 1M/900K compaction selection.

The two **existing** M2 worker entrypoints have now been repaired, without
creating a new compaction or control plane. For qualified `MiniMax-M3`,
`glm-5.3`, and `glm-5.3-flash` models, both initial `codex exec`
and `codex exec resume` explicitly receive the bounded Codex
`-c model_context_window=1000000` and
`-c model_auto_compact_token_limit=900000` settings. Caller-supplied
`POOL_MAX_CONTEXT_TOKENS` and `POOL_AUTO_COMPACT_WINDOW_TOKENS` remain
per-task bounds, may tighten within known limits, and are validated before
provider execution. Invalid, non-decimal/leading-zero, oversized, or
above-context overrides return typed rc78; unqualified models cannot claim
the qualified 1M policy. The wrappers do not change authentication, model
admission, lease scope, provider credentials, or the security-limited Go bearer.

**Verification:** shell syntax plus the pre-final edit hermetic wrapper suite
passed **46** tests. After rejecting ambiguous leading-zero inputs, a
focused set of **22** context-specific tests passed with **46** other tests
deselected. The hermetic fake Codex CLI logs both initial and resumed argv and
proves that the `-c` flags are present even when a copied CODEX_HOME config
contains no context keys; override/bounds/error cases are also covered.
The first targeted run exposed two test-only expectation mismatches for
the raw `0` refusal reason; the assertions were corrected and the focused
set passed on rerun. No paid provider inference or remote canary was dispatched.
The ordinary pytest temporary Chromium cleanup warnings do not change these
behavior assertions.

Current M2 local SHA-256 (new source, not yet a GitHub code distribution):
`ext/mm_codex_exec.sh
b402b232c87ec97339c690000257cd78759b9f7d7cb445174d6e6d12cb6f2db0`;
`ext/glm_codex_exec.sh
36afcaffedb614fe2ec9bbb81d77b7150ada950b2076c279ddce1fe31aea0508`;
`ext/tests/test_codex_exec_autocontinue.py
cc49a2148832d2c888846ea5714e4e55c4d262b4823c055f62876df060ef5413`.
The already established immutable per-launch support pipeline lists both
wrappers. Their new hashes can be selected by a **future** qualified launch
without changing existing workers, but remote **selection of the new hashes and
actual provider compaction remain NOT PROVEN**. This evidence update is not an
instruction to launch duplicate/premium canaries or overwrite stable host configs.

A bounded historical scan of 38 recent remote-controller logs found 31
`rc=0`, two still active at sampling, three `rc=75`, one `rc=124`,
and one `rc=1`. The timeout was a C1 DeepSeek/Go request using its
intentionally short capability. Two `rc=75` responses identified
`active_count=2, max_active=2` host admission (not worker timeout);
the rc1 MiniMax trace showed `ECONNRESET` (transport/provider failure).
This is diagnostic evidence, **not** Executive OS's authoritative live job
state or acceptance of the other worker outputs.

### 2026-10-08 live GLM source selection and MiniMax-Codex private receipt parity

**New real-worker source-selection evidence.** The previously dispatched C2
`glm-codex` commission `paper-01a1101f-im06-history-projector-build-r1`
on `mini2` selected an immutable support release whose manifest contains
`glm_codex_exec.sh
36afcaffedb614fe2ec9bbb81d77b7150ada950b2076c279ddce1fe31aea0508`.
It used a 7200-second controller window. A separate read-only Mini2 process
argv observation found active Codex commands containing **both**
`model_context_window=1000000` and
`model_auto_compact_token_limit=900000` as CLI overrides.
The argv observation could not securely bind those particular process
flags to the named run. Subsequent more granular live worker inspection was
explicitly safety-blocked pre-dispatch, not retried or routed elsewhere.
Do **not** claim terminal provider acceptance, real auto-compaction, or
token capacity proof merely from source selection and argv sampling.
No new paid worker was dispatched.

**Additional independent instrumentation defect fixed locally:** the existing
`mm_codex_exec.sh` MiniMax Codex cleanup omitted the private cumulative
`codex_usage.py` receipt produced by GLM's sibling wrapper. This prevented
typed native usage visibility after MiniMax completion even with correct model
context overrides. The incumbent MiniMax EXIT trap now writes a same-directory
0600 temporary receipt before deleting its private CODEX_HOME, atomically
moves it to the runtime-provided `POOL_USAGE_FILE` on success, removes
temporary artifacts, and preserves the provider's original exit code on
usage capture failure. It uses **only** the existing Codex usage parser and
remote usage-receipt consumer; no new transcript/memory/ledger/control plane
was created.

The existing hermetic usage capture tests now cover GLM **and** MiniMax on
`rc=0` / `rc=3`, observed/missing/unwritable usage. The first run found
an independent old fixture mismatch: a simulated 2-second remote task was
left unclassified, correctly triggering the real runtime's >=3600s
unclassified floor and exceeding the fixture's 20-second timeout. That
**test-only** task was explicitly classified `C1_ROUTINE_BOUNDED`;
production runtime floors were unchanged. Final usage/capture/transport
and parser suite: **45 passed + 32 subtests**, eight unrelated old pytest
Chromium temporary-cleanup warnings. Current M2 SHA-256:
`ext/mm_codex_exec.sh
ae5962207fed30d2db85b720bbc0fe77663005f9503a64cae59bff859fcd163b`;
`ext/tests/test_usage_capture_chain.py
3c15ad25b05c35d0778701147c8ec5d19c9507537015c90eae986e2d59a6b2dc`.

**Acceptance:** this is locally source-installed and test-verified.
A future naturally qualified MiniMax Codex remote release must select the
new `ae5962...` wrapper, settle the worker normally, and present a validated
native usage receipt before labeling that path `PROVEN_LIVE`. Existing
immutable in-flight manifests cannot be reinterpreted as selecting new code.
The older safety-denied Go preselection, leased-GLM override and slot
regression paths remain fenced. This evidence-only draft is not a production
deployment, merge or permission grant.

### Verification boundary

Directly observed current green evidence:

- Focused timeout/context/lease/process/launch-policy/auto-continue pack:
  **175 passed, 7 subtests passed** (only unrelated pytest temp-cleanup warnings).
- Wrapper/routing continuation subset after the C2/C3 resume-budget change:
  **65 passed**.
- Installed `pool` dry-run lease calculations:
  **3890** seconds at the native 3600-second default and **7490** at the 7200-second maximum,
  without acquiring a real provider lease.
- Codex CLI 0.159.3 bundled-catalog inspection: **MiniMax-M3 absent, glm-5.3 absent, 11 bundled
  models**; redacted doctor readback then reported **config.load=ok** for both custom profiles after
  adding the explicit 1M/900K context policy.

A wider legacy kit run previously reached 1467 passes with 33 failures in other fixture/policy areas;
it is not evidence that the entire kit is globally green.

The core timeout, lease, process-cleanup, context, OpenCode-free, Go complexity guard, bounded
auto-continue, and direct-Grok complexity floor changes are now executable-post-edit verified on the original m2studio carrier. The
remaining known in-scope defect is routing ergonomics: automatic execute selection may choose Go for
C2/C3 and then be refused at the launch-policy gate instead of preselecting the next eligible
long-runtime pool.
