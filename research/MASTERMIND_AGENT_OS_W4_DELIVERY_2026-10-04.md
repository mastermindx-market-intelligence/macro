# Agent OS W4 report-only ship-boundary delivery

Operation: `agent-os-v1-closure-20261003-astra-001`.
Decision: `DEC:AGENTOS-W4-CAPTURE-BOUNDARY`.
Source pickup: Macro `f9ed175800257b228166dabe8b3ac9a55e74e237`.

## Accepted implementation boundary

The adapter observes successful, explicit, literal PR creation and captures the PR on
one exact existing workstream/wave. Current exact branch claim takes precedence; without
one, every changed path must resolve to the same sole owner. The canonical PR header must
agree. Unsupported commands and unknown/ambiguous/conflicting ownership do not mutate.
The capture edits only `pr` and a `todo`/`in_progress` wave to `awaiting_ci`, then reports
that the record remains uncommitted. The ordinary commit/push/merge route supplies durable
knowledge and Git-derived `updated`. No generated date is authored.

Stop is a separate read-only reminder. It accepts only a valid tracked, clean handoff for
the same branch/workstream whose newest reachable commit is at or after the current
claim. Old branch-reuse handoffs cannot suppress the new reminder. Neither adapter alters
Stop enforcement or ship-loop state. Missing/malformed data always fails open. Native
Stop errors emit `{}`; the shell also absorbs a missing interpreter/helper exit. Delegation
is read-only, one-hop and same-Git-store only. There is no service, new lifecycle record,
lease, heartbeat, scheduler, queue, priority logic, runtime grant or Linear writer.

## Collision adjudication

The initial complete 561-open-PR file census and 560-open refresh (nine moved heads, no
failed pages) were paired with local worktree/branch/process evidence before editing the
fleet hook. MAS-129 is Canceled; its old carriers are not revived and its historical
MAS-130 dependency is not a live lease.

- #8107 remains open at `22a5d577f0b4427309348ce7e8a9360b039a1650`. Its published source
  affects root admission, PreToolUse and quarantine. It is not an ancestor of this base;
  no matching local modifier was found. W4 changes the distinct PostToolUse dispatch and
  adds a separate advisory Stop entry. This does not accept or absorb #8107.
- #7084/#7060 expose inherited hook paths, but have no new hook hunk against their merge
  bases with this pickup. #7488 owns compile-context tests, which this wave leaves alone.
- #7114 is draft/HOLD at `abf7a354e4ed36c937027d81d8a50cbdf47e7f60`: its settings hunk adds
  PreToolUse model routing, disjoint from these PostToolUse/Stop additions.
- #7799 remains draft at `e8727ff50dc527b49493d2ca029e5f1b3ea1b630`; its wrapper source is
  unchanged here. The existing settings test now explicitly requires exactly one original
  enforcement wrapper (same delegate and >=540s timeout) plus one specific advisory hook.
- #6980 is an unaccepted design precursor, not an execution lease or implementation.

## Discriminating local proof

Tests were written and observed failing before implementation/repair. They cover missing
helper/CLI integration, exact current claim and sole-path binding, multiple claims/owners,
missing/malformed stores, unsafe and renamed paths, body/repository/branch mismatch,
unsupported commands, occupied/null PR fields, idempotency, claim release, and preservation
of every noncaptured field. Later RED tests exposed and bounded the handoff parser arity,
Stop primary-source/worktree mismatch, malformed native error output, stale same-branch
handoff, and a locally wider Wave grammar. The final grammar comes from the frozen manifest.

Final focused hook command:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_agentos_ship_capture.py tests/test_ship_loop_guard.py tests/test_ship_loop_semantic.py tests/test_ship_loop_hold_wrapper.py
```

Result: **385 passed, 1 skipped, 158.62 seconds**. The pre-existing skip is retained.
The high-blast reviewer independently reran the earlier helper/hold subset (83 passed)
and approved the subsequent temporal/grammar repairs by source inspection. A separate
CI dependency audit confirmed the existing full-checkout self-mod-fence job has PyYAML,
helper/validator/manifest/hook imports and the new explicit suite selection. No job or
workflow is added.

The provider protocol was checked against https://code.claude.com/docs/en/hooks on
2026-10-04. Contract tests are not a receipt that every fleet client has installed these
bytes. This wave's acceptance still requires exact committed review, hosted checks,
merge, actual capture publication and a cold-session recovery receipt. Those are recorded
in the canonical workstream/handoff when they occur; this document does not predeclare them.


## Attended filesystem latency correction

The real explicit CLI observation exposed the native three-second Git budget on a slow
external SSD. A discriminating local Git shim delayed the diff by 3.2 seconds and the
pre-repair explicit capture returned CAPTURE_UNRECORDED without editing a record.
The bounded correction permits at most 60 seconds per Git read only in attended
non-hook commands (branch/path discovery and committed-handoff verification). Native hooks retain the three-second Git default and five-second
helper boundary. Missing or timed-out evidence still produces an advisory no-op; no
fallback observation or identity is invented. A PR description with unheaded prose was
also correctly refused by the canonical parser and repaired as author input.


## Cold recovery authoring correction

An independent fresh reader recovered the current state from committed records at
`13ef310358d80f0c8cc9e586174c523baed8a613`, including the captured PR8407/calibration wave,
Git-derived update time, and the exact unfinished W4 acceptance path. The machine compiler
then exposed an authoring mismatch: the new handoff filename ended in `-v1-closure`, while
`HANDOFF_DATE_RE` in `scripts/agentos.py` recognizes a trailing `-YYYY-MM-DD`. It consequently
selected a historical August handoff and listed the new one as older. Renaming this wave's
own record to canonical `agentos/handoffs/AGENT-OS-2026-10-04.md` corrects the author input.
No compiler, incumbent compile test, historical handoff or ranking policy is changed.
The before artifact is `/tmp/agentos-w4-cold-context.json`; the corrected compiler read is
completed at 6870247e131192e18564fad069fb9d387b90fd83 and independently passed the required
workstream/PR/update/latest-handoff recovery. The exact canonical handoff is selected.
The compiler still exceeds its requested token budget and omits broader discovery/artifact
sections; those existing completeness limitations remain separate maintenance.


## Actual W4 capture and handoff observation

The explicit `ship-capture --pr 8411 --body-file /tmp/agentos-w4-pr.md` command returned
CAPTURE_UNCOMMITTED with exact claim binding, W4 and PR8411. Its only workstream edits
were PR8411 and awaiting_ci; Git supplies the update clock when this normal commit ships.
The independent reader can recover this published record without the originating chat.

Actual `ship-report` found a valid tracked committed handoff but its deep Git diff/log
reads timed out at three seconds and falsely returned HANDOFF_REMINDER. Two discriminating
RED tests reproduced the fault: a native TimeoutExpired and an actual 3.2-second attended
Git subprocess both returned the missing-handoff result. The repair passes the attended
60-second allowance through all three handoff Git reads and returns HANDOFF_UNAVAILABLE
for native timeout. Native three-second reads/five-second child boundaries are preserved;
no unknown evidence is promoted to a missing or successful handoff.

The repaired helper/hold-wrapper subset passed **90 tests in 26.76 seconds**; the
pre-repair discriminating run failed both timeout cases (four existing cases passed).
