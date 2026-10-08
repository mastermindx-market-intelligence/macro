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
the special PONG canary) appears when the bounded resume budget is exhausted, the wrappers return typed
rc=76 rather than false-success rc=0. Hermetic wrapper/routing tests covering larger C2/C3 budgets,
explicit tightening, the hard cap, and terminal-status exhaustion passed in the current focused pack.


### 2026-10-08 continuation hardening

A further local-Grok audit found that the direct `sub.sh grok` path still defaulted every worker to
3600 seconds even when the commission was already classified `C3_FRONTIER_JUDGMENT`. The live
account-local source now derives the direct Grok worker timeout from the same reviewed complexity
semantics as remote execution: ordinary/C2 defaults remain 3600 seconds, C3 defaults to 7200 seconds,
and stale explicit short overrides are lifted to 3600 for C2 or 7200 for C3. C0/C1 callers may still
intentionally request shorter bounded windows. Source SHA-256 is
`a780a9b5e790c236e30d0f338b51b1d6a97179382a63c14d7437955053352a19`.
The dedicated Grok dispatch suite, including new C2/C3 floor regressions, passed **53 tests**.

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
