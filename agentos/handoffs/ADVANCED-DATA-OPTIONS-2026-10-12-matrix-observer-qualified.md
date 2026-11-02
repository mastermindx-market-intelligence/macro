---
workstream: WS:ADVANCED-DATA-OPTIONS
session: 01a10340-ddc1-7e41-9b42-9c8543c28c3d
model: codex
ended_because: ci_handoff
mission: Qualify merged Matrix diagnostics and retain the remaining natural-session acceptance obligations.
state_before: PR 8884 was pending controller merge and merged-observer qualification; natural Matrix acceptance
  was unproven.
changed:
- path: scripts/observe_options_matrix_publication.py
  what: Merged reviewed diagnostic accepted in one read-only all-12-root baseline observation.
- path: scripts/qualify_options_matrix_older_snapshot.py
  what: Merged reviewed isolated harness installed outside the producer; genuine older/newer invocation
    remains pending.
prs:
- 8884
- 8960
- 9010
- 9012
verified:
- claim: PR 8884 merged with current proof and reviewed diagnostic/test byte parity.
  command: Exact-head CI and incumbent controller log; git object and parsed manifest comparison.
  result: 343022b7a074223a571f66986a5c92c5141ccfb3 at 16:55:37Z; CI 38278294891 all 12 packs and gate
    SUCCESS; four files byte-identical to reviewed 188ae9 and tested 76129.
- claim: One merged observer execution read all 12 publications successfully without modifying the producer.
  command: qualify-merged-matrix-observer-on-m1.py with actual merge; retain qualification and observation
    receipts.
  result: 17:18Z October 12; complete/stable October 8 baseline; all 12 local/R2 head/history bytes equal;
    source clocks, positive spots and observed-side membership retained; runtime/plist unchanged.
- claim: The same heartbeat is restored to weekdays at 17:00 America/Vancouver.
  command: automation_update plus local TOML readback.
  result: ACTIVE; original thread and automation identity retained; no duplicate watcher.
unverified:
- claim: Two distinct advancing natural Matrix source sessions are accepted.
  what_would_verify: Actual natural weekday 16:00 launchd invocations with separate job/log provenance
    and complete four-way equality plus advancing source sessions across all 12 roots.
- claim: A genuine older/newer withholding proof is accepted.
  what_would_verify: Reviewed isolated harness using retained real older/newer snapshot bytes, immutable
    version references, exact publisher source and real provenance bound outside the harness.
unresolved:
- 'Natural Matrix sessions accepted: 0 of 2; Sunday manual publication and Flow count zero.'
- The isolated harness has not yet been exercised with a genuine older/newer retained pair.
- Whole-program and Terminal PR 723 acceptance remain independent.
next_actions:
- After the natural 16:00 invocation, retain job/log provenance and observe all 12 roots with a unique
  new receipt using the installed observer.
- Require two distinct advancing source sessions; if the source does not advance, diagnose the actual
  source/job failure without fabricating dates or forcing publication.
- Qualify a genuine retained older/newer pair with the reviewed isolated harness; bind exact source and
  real provenance separately.
- Delete the existing weekday heartbeat only after both natural sessions and genuine negative proof are
  accepted.
do_not_redo:
- Do not rerun the initial installer/qualification script, producer, launchd reload or one-use conditional-create
  test.
- Do not repeat accepted Flow recovery or alter September 28 quarantine.
- Do not retry refused public R2 or artifact exports through another tool or identity.
- Do not claim the whole Fable project complete from source, CI, merge or baseline observation alone.
danger_areas:
- Snapshot timestamps alone do not prove natural launchd execution.
- A new build of the same source session is not an advancing session.
- Merged main has a newer engine/options_structure.py; it was not installed. Preserve the accepted deployed
  6361 runtime inventory.
---

PR [8884](https://github.com/mastermindx-market-intelligence/macro/pull/8884) is merged and its two diagnostic scripts are qualified on M1. The [evidence record](../../research/options_intelligence/2026-10-12/FABLE_MATRIX_OBSERVER_QUALIFICATION_343022B7.json) retains the original source, CI, controller, observation and pre-natural invocation receipts. The canonical accepted return is [comment 6129204619](https://github.com/mastermindx-market-intelligence/macro/pull/8884#issuecomment-6129204619).

The incumbent controller accepted current proof and merged the exact tested head. The four diagnostic/test files equal the independently reviewed source. The integrated manifest equals the tested head and changes only the intended options-matrix-code job relative to the merge parent. The one observer invocation completed at 17:18Z, preserved deployed runtime 6361f5e0 and its 12-file inventory/plist, and installed only the two diagnostic files outside the live producer. All 12 local heads, local immutable history objects, R2 heads and R2 immutable history objects matched. The full observation retains per-root references, hashes, lengths, source clocks, positive spots and observed-side membership.

This remains an October 8 source baseline and counts zero natural sessions. At 10:24 Pacific on October 12 the loaded com.macro.optionsmatrix job had zero runs, had never exited, and both configured log paths were absent. The next natural weekday invocation is scheduled for 16:00 Pacific. The same follow-up now runs at 17:00 Pacific weekdays. Its future reads must use unique receipts and separately bind launchd/log provenance; the initial installation script must not run again.

An initial local preparation check incorrectly required merged-main producer bytes to equal the older deployed runtime. It failed before remote execution. The corrected qualification preserved the installed runtime and read through it; main's newer engine/options_structure.py was not deployed. The embedded source receipt precedes execution, while the later observer receipt proves the single successful invocation.

This supplements the earlier Matrix/live-flow handoff and the accepted Flow natural-recovery handoff. Flow and its records PR 9010 remain accepted. PR 8960 is merged, with its recorded external-actor/freshness limitation; the actual dependency repairs previously landed via 8810. PR 9012's conditional conflict preflight behavior is accepted by a natural controller run, without a claim of unconditional queue liveness. None of those results substitutes for the two advancing natural Matrix sessions or the genuine older/newer withholding proof.
