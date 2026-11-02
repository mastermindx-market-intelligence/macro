---
workstream: "WS:ADVANCED-DATA-OPTIONS"
session: claude/ad1t2b-drained-store-refusal
model: opus
ended_because: blocked
mission: >
  MACRO-04 — run the AD-1 Options Intelligence brief producer on the host that owns its canonical
  ThetaData store, with honest success/failure and source-to-screen proof. Adopt the existing
  #7889 carrier rather than duplicating it.
state_before: >
  site/options_intel_brief.json frozen at built_at_utc=2026-08-22T19:10:32Z, as_of_session=2026-08-19
  — 38 days stale on 2026-09-29. PR #7889 open, DRAFT, head ff11820b52be, zero reviews, branch
  untouched since 2026-09-23, its sibling worktree clean with only a content-free lock stamp (no
  active writer). Its accepted diagnosis was PLACEMENT: the producer's only scheduled invocation is
  a step in daily.yml's `engine` job, which runs on store-less M2 runners, so the resolver returns
  None, the producer takes its documented off-host self-skip, and the step records success.
changed:
  - path: engine/thetadata_store.py
    what: >
      `_has_store_content()` now requires a tier to actually HOLD A ROOT, not merely to exist as a
      directory. Root must be a directory, matching `roots()`, so a stray .DS_Store or lock file
      cannot revive the false positive. Added diagnostic-only `_drained_store()` and a distinct
      line-start ::error separating a PLACEMENT fault ("no store on this host") from a DATA fault
      ("store is here but drained"), which the single old `resolved store=NONE` message conflated.
  - path: tests/test_thetadata_resolver.py
    what: >
      `_mk_store` rewritten to build the real {store}/{tier}/{ROOT}/{YEAR}.parquet layout — its old
      docstring literally encoded the hole ("a directory that passes the content check (>=1 tier
      subdir)"). Added TestDrainedStoreIsNotAStore (5 cases) incl. a positive control that a
      one-root store still resolves, and a stray-file case.
  - path: tests/test_index_gex_history.py
    what: >
      Same fixture defect in its local `_mk_store`; rewritten to the real layout. Strengthening,
      not weakening — these fixtures were asserting against a store shape that cannot exist.
  - path: agentos/discoveries/DSC-A-DRAINED-STORE-PASSES-A-SHAPE-CHECK-AND-PUBLISHES-A-BLANK-BOARD.md
    what: new discovery record for the resolver hole and the false green it produces
  - path: agentos/discoveries/DSC-A-STORE-MANIFEST-IS-A-WRITERS-INTENT-NOT-AN-OBSERVATION-OF-THE-STORE.md
    what: new discovery record — the store manifest advertises health a drained store does not have
  - path: engine/thetadata_store.py
    what: >
      ROUND 2 — three repairs on top of the above, all found by adversarial review of my own fix.
      (a) FAIL-OPEN IS NO LONGER SILENT: resolving on `_UNKNOWN` now emits a line-start
      `::warning title=thetadata-store-unverified::`. Without it the guard was bypassed on exactly
      the host and conditions it was written for (DSC:A-SILENT-FAIL-OPEN-REPRODUCES-THE-INCIDENT-IT-PREVENTS).
      (b) THE PROBE CAN NO LONGER MAKE RESOLUTION RAISE: `Thread.start()` raises RuntimeError when
      the process cannot create a thread; that is now caught and treated as `_UNKNOWN`, preserving
      the never-raises contract its callers document (engine/options_skew.py load_chain).
      (c) `_probe_budget()` replaces a bare module-scope `float(os.environ.get(...))`, which raised
      ValueError at IMPORT on an empty workflow `env:` value and took the whole build with it; NaN
      gets its own `v != v` branch because it passes every `<= 0` comparison and then makes
      `Thread.join(nan)` raise (DSC:HARDENING-A-UNIVERSAL-RESOLVER-AT-MODULE-SCOPE-CAN-BREAK-EVERY-IMPORT).
  - path: scripts/backfill_thetadata_eod.py
    what: >
      Hoisted `drained_store_candidates` / `resolve_thetadata_store` from a function-level import to
      module scope. The function-level import sat on the fresh-install branch, so the one path that
      most needs to distinguish fresh-install from drained-canonical was importing its discriminator
      lazily, inside the branch, at the moment of the decision.
  - path: scripts/audit_options_surface_coverage.py
    what: routed through the canonical resolver rather than re-deriving a store path locally
  - path: agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md
    what: wave row for this repair
verified:
  - claim: The tightening is discriminating, not blanket — it refuses emptiness and still accepts thinness.
    command: "python3 -m pytest tests/test_thetadata_resolver.py tests/test_index_gex_history.py::TestStorePathRoutesThroughTheResolver -q, run on base 942956ea69f6 with and without engine/thetadata_store.py reverted via git checkout origin/main -- engine/thetadata_store.py"
    result: "25 passed with the fix; 4 failed + 1 passed with it reverted. The 1 that passes both ways is test_one_real_root_is_thinness_and_still_resolves — the positive control."
  - claim: No regression across the producer, timings, workflow-size and resolver suites.
    command: "python3 -m pytest tests/test_options_intel_brief.py tests/test_nightly_timings.py tests/test_workflow_file_size.py tests/test_thetadata_resolver.py tests/test_index_gex_history.py -q"
    result: "238 passed, 1 skipped in 159.40s"
  - claim: The store on the store-bearing host is drained while its manifest claims health.
    command: "ssh m1 — per-tier root count over $P/{eod,oi,greeks} with a same-host control on data/yahoo"
    result: "0 / 0 / 0 roots against _manifest.json complete_t1_roots=372 status=healthy finished_at=2026-09-25; control data/yahoo=728 entries, so the null is real and not a glob/permissions/sparse artifact"
  - claim: "#7889's central premise has inverted: m1-theta has no carrier, so runner-policy.yml's `orphaned` record is currently CORRECT and R6 blocks correctly."
    command: "gh api repos/mastermindx-market-intelligence/macro/actions/runners"
    result: "total=4 — mac-builder-3 (theta-m1), mac-builder-4, mac-builder-light, mac-builder-5. m1-nightly-2 absent; nothing carries m1-theta."
  - claim: "#7889 is a genuine dark launch — its M1 job cannot run as merged."
    command: "gh api repos/mastermindx-market-intelligence/macro/actions/variables"
    result: "10 variables, AD1_M1_LANE not among them, so `vars.AD1_M1_LANE == 'on'` is false and the `!= 'on'` in-engine step stays live exactly as today"
  - claim: A second options product is already frozen by the same drained store.
    command: "read site/options_skew/latest.json on origin/main"
    result: "generated_utc=2026-09-29T05:03Z (fresh) against ledger_asof=2026-09-23, accrual_state=ledger_only, n=372 — the same 372 the store manifest claims"
  - claim: agentos records are schema-clean.
    command: "python3 scripts/agentos.py validate"
    result: "1386 records — 0 errors, 109 warnings (all pre-existing review-overdue on other workstreams)"
  - claim: The tightening cannot report an unreadable-but-intact store as drained, and cannot hang the resolver.
    command: "python3 -m pytest tests/test_thetadata_resolver.py::TestUnreadableIsNeverDrained -q, plus two mutations — _RESOLVABLE narrowed to (_HAS_ROOT,) and th.join(_STORE_PROBE_S) replaced by th.join()"
    result: "5 passed clean; fail-closed mutant -> 4 failed; unbounded mutant -> the bound test failed after 18.86s against its <3s assertion"
  - claim: No regression across the resolver, store, topup, options-intel, skew and payoff-lab suites after the repair.
    command: "python3 -m pytest tests/test_thetadata_resolver.py tests/test_index_gex_history.py tests/test_thetadata_store.py tests/test_topup_thetadata_daily.py tests/test_topup_thetadata_legacy.py tests/test_options_intel_brief.py tests/test_options_skew.py tests/test_options_payoff_lab.py -q"
    result: "424 passed, 1 skipped, 1 failed — the failure is pre-existing test_f15_writer_lock_gitignored, which reads a hardcoded absolute path into a stale sibling worktree and is unrelated to these files"
  - claim: >
      Fail-open is no longer silent, and the annotation is the shape GitHub actually renders.
    command: "python3 -m pytest tests/test_thetadata_resolver.py::TestFailingOpenIsNeverSilent -q, plus two mutations"
    result: >
      3 passed. Mutation A — route the annotation through log.warning instead of a bare print -> 1 failed
      (this is the house-law defect that makes GitHub drop the line silently). Mutation B — fire it
      unconditionally rather than only on _UNKNOWN -> 1 failed. NOTE a third mutant (delete the print)
      was INVALID: it leaves a dangling `if`, so pytest reports a collection ERROR, not a failure —
      that mutant never ran and proved nothing.
  - claim: A malformed probe budget cannot break the import of the canonical resolver.
    command: "python3 -m pytest tests/test_thetadata_resolver.py::TestAMalformedProbeBudgetNeverBreaksTheImport -q"
    result: >
      parametrized over "", "abc", "nan", "  ", "1e", "None" — all fall back to 10.0. Direct mechanism
      check re-run 2026-09-29: float("") -> ValueError; nan <= 0 -> False; nan != nan -> True;
      Thread(...).join(float("nan")) -> ValueError. The empty string is the realistic shape (a workflow
      `env:` key declared with no value), not a typo.
  - claim: The probe cannot make resolution raise even when the OS refuses a thread.
    command: "python3 -m pytest tests/test_thetadata_resolver.py::TestTheProbeNeverMakesResolutionRaise -q"
    result: "2 passed, incl. monkeypatching threading.Thread.start to raise RuntimeError; the resolver returns _UNKNOWN and resolves"
  - claim: Two pre-existing chmod(0o000) tests were NOT discriminating and are now.
    command: "switched their fixture from _mk_store(roots=('SPY',)) to _mk_drained_store, hoisted monkeypatch.setenv above the pre-check, then removed the chmod as a mutation"
    result: >
      Before: the assertion held whether or not the chmod happened. After: the pre-check
      `resolve_thetadata_store(purpose='pre') is None` proves the fixture refuses while still readable,
      and deleting the chmod now FAILS the test. Caught in my own work by the same review that
      flagged this class of defect — I had written a trivially-true assertion above the setenv,
      so the resolver was never pointed at the fixture.
  - claim: No regression across the eight consumer suites after round 2.
    command: "python3 -m pytest tests/test_thetadata_resolver.py tests/test_index_gex_history.py tests/test_thetadata_store.py tests/test_topup_thetadata_daily.py tests/test_topup_thetadata_legacy.py tests/test_options_intel_brief.py tests/test_options_skew.py tests/test_options_payoff_lab.py -q"
    result: >
      565 passed. 2 failures remain and touch none of this PR's nine files:
      test_f15_writer_lock_gitignored (hardcoded absolute path into a stale sibling worktree) and
      test_publish_r2.py::test_min_files_override_does_not_loosen_the_other_data_dirs (a pin that has
      been stale on main since 2026-09-23 — source carries 4 override entries, the test pins 2).
      Deliberately NOT healed here: it is a different pack and splitting attention across two ship
      chains is how one of them is abandoned. Recorded on the PR for another session.
  - claim: ROLLBACK is a config flip, not a revert — measured, not asserted.
    command: "THETADATA_STORE_PROBE_S=0 against a drained store, a stub, a real store, and a hanging readdir"
    result: >
      0 restores pre-PR semantics exactly (drained ACCEPTED, stub REFUSED, real ACCEPTED) and returns
      before the thread is created, so it needs no revert and no deploy. Against a hanging readdir:
      probe on -> 10.3s then ACCEPTED (fail-open confirmed under the real failure mode); kill switch
      -> 0.3s ACCEPTED. Disclosed cost: at most ONE probe timeout per resolve, because the loop
      short-circuits on the first _RESOLVABLE verdict and _UNKNOWN is resolvable;
      drained_store_candidates() can pay 3x but sits only on backfill's guard path.
  - claim: The merged bytes are in origin/main — verified against the branch ref, not the PR's fields.
    command: "bare `git fetch origin` first, then per-path blob comparison of all nine paths against origin/main, then a needle grep"
    result: >
      All nine LANDED (blob-identical). Squash 54f62e4d4b25c4e475ece482aff856d052e42e67 is an ancestor
      of origin/main; `thetadata-store-unverified` and `_probe_budget` are present in main's own bytes.
      The PR's own fields are not evidence here — `--json files` reports the MERGED paths, so comparing
      a PR against itself passes even when a commit landed after the merge.

unverified:
  - claim: That refilling the store would let the AD-1 producer emit a real brief.
    what_would_verify: "a store with non-zero roots on a registered m1-theta runner, then two natural post-daily executions per the MACRO-04 §6 bar"
  - claim: Why the M1's store lost its roots (reclaimed, never flushed, or volume removed).
    what_would_verify: "operator access to the host once it is no longer wedged; the store's writer owns this, a reader cannot answer it"
unresolved:
  - "The store-bearing M1 is wedged: ping 0% loss and Tailscale up, SSH authenticates, but every command dies with `exec request failed on channel 0` — it cannot fork. Preceded by 96% disk / \"pressure\": \"emergency\" on 2026-09-17 (canary exit 78), after which its runner left the registry."
  - "#7889 carries an explicit hold — title `[HELD — needs W4 admission]`, body `The red check is the hold`, release condition owned by W4. My evidence says that admission should NOT be granted, because the premise it rested on has inverted."
  - "#7889's staleness receipt is self-refuting: it cites mac-builder-3 carrying `theta-m1` as proof that `m1-theta` is not orphaned — the exact label reversal its own `Label trap` section documents."
  - "#7889's body claims 6 files / +468 and cites scripts/ci/ad1_store_preflight.sh, which is not on the branch; actual diff is 5 files / +446."
next_actions:
  - "DONE 2026-09-29: #8203 squash-merged at 19:11:26Z, merge 54f62e4d4b25c4e475ece482aff856d052e42e67, all nine paths verified blob-identical in origin/main. `ci-authority/codex/merge-queue-pilot` FAILS BY DESIGN on any main-based PR — it fails the inactive base context deliberately; `ci-authority/main` is the one that must be green, and was."
  - "The producer-level AD-1T2b drained-store tests are PARKED, not lost: commit 64ed54bf4c5e9e224922cb65c41503ff4cdc2166 on `origin/claude/ad1t2b-producer-tests-parked` (119 lines in tests/test_options_intel_brief.py). They were NOT pushed to #7889 because they depend on `--require-store`, which is still absent from main (0 occurrences) and lives only in #7889's held branch — and because pushing to a held PR spends CI on a carrier whose own hold text says `The red check is the hold`. Land them WITH #7889 whenever W4 admits it, or rebase them onto whatever branch carries `--require-store`. Their base commit 98fc020a7863 is my own superseded round-1 resolver fix, so they need a cherry-pick, not a fast-forward."
  - "Correct #7889's body ONCE (file count, the inverted runner receipt, the self-refuting label citation). One edit only — two `gh pr edit --body-file` calls inside one ci-authority run's lifetime make the second cancel the first."
  - "Do NOT release #7889's hold or drive a W4 admission. The R6 red is correct on today's receipts."
  - "Refilling the M1 store is owned by its writer, not by this workstream. Recovering the host is an operator act."
do_not_redo:
  - "Do not re-diagnose the stale brief as purely a placement fault. It is BOTH a placement fault and a data fault, and the data fault dominates: with the store drained, moving the job to the M1 would have published a blank board rather than a real one. Fixing placement alone makes it worse."
  - "Do not 'fix' the resolver by loosening it back to a container check because something fails to resolve. The positive control (test_one_real_root_is_thinness_and_still_resolves) exists precisely to distinguish a legitimate refusal from an over-tightening."
  - "Do not add a health gate that reads `_manifest.json`. It advertised status=healthy with complete_t1_roots=372 over a store holding zero roots; such a gate passes on a completely empty store."
  - "Do not target `theta-m1` for anything needing the store. That label is the M2 (mac-builder-3) and has no store. The store host's label is `m1-theta`. #7889 already gets this right — do not 'correct' it."
  - "Do not put the options-intel job inside daily.yml. Prior adversarial review established that a job queued on a single-slot label with no live runner holds its workflow's cron concurrency group up to 24h (DSC-QUEUED-JOB-HOSTAGE); #7889's own workflow with `concurrency: group: options-intel` is the settled shape."
  - "Do not silence R6, relabel the M2 as the M1, or bypass the missing admission."
danger_areas:
  - "engine/thetadata_store.py is THE single canonical resolver — every ThetaData consumer routes through it, so a false negative here silently disables a production data path across several nightly lanes. `scripts/backfill_thetadata_eod.py:560` is safe under the tightening only because a clean None is its explicit fresh-install exception; any NEW writer that resolves before it writes needs the same exception or it cannot bootstrap an empty store."
  - "`_has_store_content` counts only directory children as roots, matching the real enumerators `universe()` and `iv_coverage()` (`_load_parquets()` then globs inside a root). There is no `roots()` function — an earlier draft cited one. If any tier ever stores roots as files, or the layout departs from {store}/{tier}/{ROOT}/{YEAR}.parquet, this predicate must change with it."
  - "THE landmine in this area: a content check is a readdir, the shape check it replaced was a stat. The three tier dirs are SYMLINKS onto an external volume (scripts/publish_r2.py::_walk_files), and listing them is what hangs or is denied under launchd — build_options_hub_nightly.preflight_store bounds it in a daemon thread and exits 4, and it runs AFTER resolution. Any emptiness check in the resolver must therefore be BOUNDED and FAIL OPEN. `_RESOLVABLE = (_HAS_ROOT, _UNKNOWN)` is that rule in one place; narrowing it to `(_HAS_ROOT,)` reports every unreadable-but-intact store as missing across all nightly lanes. Mutation-tested both ways."
  - "`resolve_thetadata_store() is None` is now AMBIGUOUS — it means fresh-install OR drained-canonical. Any writer that reads None as a fresh-install permit must consult `drained_store_candidates()` first or it will mint a second store beside the drained one."
  - "The ::error must stay a bare print(..., flush=True) at line start. Routing it through a logger emits `WARNING ::error ...`, which GitHub silently drops — the call reviews as an alarm and produces nothing."
  - "Both `_mk_store` fixtures are shared by other tests in their files; changing them changes what those tests assert against."
  - "FAIL-OPEN MUST STAY LOUD. `_RESOLVABLE = (_HAS_ROOT, _UNKNOWN)` is correct and must not be narrowed — but on `_UNKNOWN` the resolver returns a real Path, and the consumer's own alarm in scripts/build_options_intel_brief.py:166-171 fires only when `store is None`. So the fail-open branch has NO alarm of its own downstream; the `::warning title=thetadata-store-unverified::` in the resolver is the only one. Deleting it, or routing it through a logger, restores the exact silent blank-board incident this workstream exists to fix. It cannot be reached from an interactive shell (ssh lists the tier symlinks fine) — only under launchd — so `I checked on the host` is not evidence about this branch."
  - "engine/thetadata_store.py is on a UNIVERSAL import path, so anything at module scope has build-wide blast radius. `_probe_budget()` exists because a bare `float(os.environ.get('THETADATA_STORE_PROBE_S', '10'))` raises ValueError at IMPORT when the variable is present-but-empty — the shape an under-specified workflow `env:` key produces — breaking every lane that imports the module, including lanes that never set it. Keep the `v != v` NaN branch: NaN passes `<= 0`, `< 0` and `== 0` alike and then raises inside `Thread.join(nan)`."
  - "The never-raises contract is load-bearing and is NOT automatic just because the body has no `raise`. Callers document it (engine/options_skew.py load_chain). `Thread.start()` raises RuntimeError when the process cannot create a thread, so the bounded probe itself must be wrapped — and the catch must return _UNKNOWN, not None: refusing to resolve because the PROBE could not start is the same false-RED the probe exists to avoid."
prs: [8203, 7889]
discoveries:
  - "DSC:A-DRAINED-STORE-PASSES-A-SHAPE-CHECK-AND-PUBLISHES-A-BLANK-BOARD"
  - "DSC:A-STORE-MANIFEST-IS-A-WRITERS-INTENT-NOT-AN-OBSERVATION-OF-THE-STORE"
  - "DSC:A-SILENT-FAIL-OPEN-REPRODUCES-THE-INCIDENT-IT-PREVENTS"
  - "DSC:HARDENING-A-UNIVERSAL-RESOLVER-AT-MODULE-SCOPE-CAN-BREAK-EVERY-IMPORT"
---

## The one-sentence version

The brief was not stale only because the producer ran on the wrong host; it was stale because the
store on the *right* host is empty, and the resolver could not tell an empty store from a full one
— so the fix everyone was about to ship would have replaced an honestly stale artifact with a
confidently blank one.

## Status at close

The code half is MERGED and verified in main's bytes: PR #8203, squash
`54f62e4d4b25c4e475ece482aff856d052e42e67`, 2026-09-29T19:11:26Z, all nine paths blob-identical to
`origin/main`. Rollback is a config flip (`THETADATA_STORE_PROBE_S=0`), measured against a hanging
readdir, needing no revert and no deploy. The producer-level tests are parked at
`origin/claude/ad1t2b-producer-tests-parked` (`64ed54bf4c5e`) pending `--require-store`.

The MISSION half is not done, and `blocked` is the honest word for it — see below.

## Why this handoff says `blocked` rather than `complete`

The code half is done and proven. The MACRO-04 §6 acceptance bar is not reachable from here: it
requires admitted store-host placement, exactly one active producer, successful natural executions
on two qualifying cycles, and a real served brief readback. Two independent external boundaries
each block that on their own — the host cannot fork, and the store has no roots — and neither is a
reader's to repair.
