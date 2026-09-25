---
workstream: "WS:RUNNER-FLEET-RESILIENCE"
session: "claude/render-lane-livelock-diagnosis"
model: opus
ended_because: complete
mission: >
  Diagnose why the page-bake lanes on main stopped producing successful runs after
  2026-09-22, name the exact mechanism with run-id evidence, enumerate the blast
  radius of stale committed pages, and ship the instrument that would have caught
  it. The commission's own hypothesis (an unconditional `cancel-in-progress`
  livelock, as documented for main-ref ci.yml dispatches) was to be verified before
  acting, not assumed.
state_before: >
  render.yml's last success was run 35676379868 (2026-09-22T01:36:23Z); roughly 25
  runs since had concluded `cancelled` and run 35989213316 had been `queued` since
  2026-09-24T10:46:56Z. engine-render.yml was in the same state (36095283218
  pending since 2026-09-25T02:42:52Z). daily.yml was healthy on its ~01:35Z
  schedule. PR #7970 had merged a Morning Edition entry into
  `templates/_navlinks.html.j2` on 2026-09-25T04:38Z; `site/markets.html` still
  lacked it hours later and PR #7996 had healed that ONE page by splicing the
  two-line hunk into the stamped page. `.github/runner-policy.yml` declared
  `render-linux` as `offline`, carried by pc-render-2/3/4, "verified against the
  live pool 2026-08-17"; this workstream's own landmines said pc-render-1 was no
  longer in the registry at all (census 2026-08-25).
changed:
  - path: scripts/check_runner_queue_hostage.py
    what: >
      NEW lane-agnostic dead-man switch. Lists live `queued` then `in_progress`
      runs, age-filters to runs at or older than `now - 8h` before expanding jobs
      (exact, because a job's `created_at` can never precede its run's), and fails
      only on a positive observation of absence: `status == "queued"` AND no
      `runner_name` AND a self-hosted-addressed `runs-on` AND queued for >= 8h.
      8h is three times the worst honest wait measured on this fleet and one third
      of GitHub's 24h queued-job kill, so it pages with ~16h of margin. Blindness
      (no token, API error, run bound exceeded, undated rows) is INDETERMINATE:
      `::warning`, exit 0 - never a false green and never a false alarm. Enriches
      the breach message with the registry's own status for the dead label and
      best-effort notifies via `engine.alert_triage.push_ops_alert`.
  - path: tests/test_runner_queue_hostage.py
    what: >
      NEW, 14 tests. Replays run 35989213316's real job row as a breach (asserting
      "19.9h" and "orphaned" reach the message), proves a long queue behind a LIVE
      pool is not a breach, pins the threshold's margin under the 24h kill, pins
      the shapes that must never alarm, pins blindness as INDETERMINATE, proves a
      missing registry does not blind the check, proves the age filter cannot drop
      a hostage, proves the watchdog never routes to the pool it watches, and pins
      that the workflow checks out what the guard reads.
  - path: scripts/check_runner_policy.py
    what: >
      Widened the dead-label gate from `schedule` to every AUTOMATIC trigger
      (`schedule`, `push`, `repository_dispatch`) as new rule R15, because the
      lanes that wedged are push-only and were exempt by trigger. R12 (schedule)
      keeps its identity and message; R15 names the fired triggers. Either
      `scheduled_use_waiver` or `automatic_use_waiver` satisfies the gate and both
      require a `reason` AND a `since` date. Docstring now states plainly that a
      declaration gate cannot see an unrecorded death and points at the live-state
      checker.
  - path: .github/runner-policy.yml
    what: >
      Corrected to the 2026-09-25 live receipt: `render-linux` -> `orphaned`,
      `carried_by: []`, with the run-id receipts and "RESTORE IS OPERATOR-OWNED" in
      its note plus a dated `automatic`-scope waiver that explicitly waives only
      the DECLARATION gate because the new hostage checker pages regardless.
      `Linux`/`X64` -> `live` on pc-ci-1/2/3 + pc-render-1, `m1-theta` -> `live` on
      m1-nightly-2, `self-hosted` -> the 11 audited hosts. pc-ci-4 stays out of
      every live roster per R14 (its platform labels remain only in
      `pool_topology.pc-ci.pending_labels`). `pool_topology.pc-render` keeps
      `slots: 1` because R7 requires that architectural reservation, and expresses
      the real gap through a new `missing_labels: [render-linux]` key.
  - path: .github/workflows/nightly-liveness.yml
    what: >
      Added a second job `queue-hostage` on `ubuntu-latest` (load-bearing: a
      watchdog must never route to the pool it watches) with a blobless sparse
      checkout of exactly `scripts`, `engine` and `.github/runner-policy.yml`.
      Kept as a separate job rather than a step of `liveness` so a wedged fleet
      cannot take the alarm down with it.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Registered the new guard's `--selftest` and `tests/test_runner_queue_hostage.py`
      by explicit name, because the pack manifest runs tests by name and an
      unregistered test is dark in CI.
  - path: tests/test_runner_policy.py
    what: >
      +6 tests: every automatic trigger onto an orphaned label is refused (push and
      repository_dispatch -> R15, schedule -> R12), manual-only use stays allowed,
      either dated waiver key satisfies the gate, an undated waiver does not,
      `render-linux` is declared orphaned with no carriers, and the render
      reservation never silently claims a routable slot.
  - path: research/RENDER_LANE_OUTAGE_2026_09_25_POSTMORTEM.md
    what: >
      NEW. What was NOT the cause (the falsified hypothesis, with the concurrency
      table and the supersede signature), what the cause was (live pool listing,
      the job-level chain, why the site went stale and the 1,479-page table), why
      every instrument stayed silent, what this PR changes, and what still needs
      operator authority.
  - path: agentos/discoveries/DSC-DELABELLING-AN-ONLINE-RUNNER-IS-INVISIBLE-TO-EVERY-LIVENESS-INSTRUMENT.md
    what: >
      NEW discovery: a runner can lose a custom label while staying online/idle
      under its original id, so host-liveness and declaration gates both read green
      while the lane is wedged behind the 24h queued-job kill.
verified:
  - claim: "Both wedged lanes already carried `cancel-in-progress: false`, so the commission's livelock hypothesis is false."
    command: "sed -n '233,246p' .github/workflows/render.yml; sed -n '66,74p' .github/workflows/engine-render.yml"
    result: >
      `group: pipeline-render` / `cancel-in-progress: false` with a comment
      recording the 2026-07-17 starvation postmortem ("`true` cancelled 27 of 30
      renders"), and `group: pipeline-engine-render` / `cancel-in-progress: false`.
  - claim: "The ~25 `cancelled` runs are superseded PENDING runs, not killed in-flight bakes."
    command: "gh run list --workflow render.yml --json databaseId,status,conclusion,createdAt,updatedAt,startedAt --limit 40"
    result: >
      Every `cancelled` run has an empty `startedAt` and no `runner_name`, and each
      one's `updatedAt` equals the next run's `createdAt` - the supersede instant.
      This is the coverage mechanism render.yml's own concurrency comment relies on.
  - claim: "Zero online runners carry `render-linux`, in either the org or the repo pool."
    command: "gh api orgs/mastermindx-market-intelligence/actions/runners; gh api repos/mastermindx-market-intelligence/macro/actions/runners"
    result: >
      pc-render-1 is org runner id 15, online and idle, with labels
      `self-hosted,Linux,X64` only; pc-render-2/3/4 are absent from the live pool
      entirely. `render-linux` is the only referenced label in the repo with zero
      carriers anywhere. The stable low id 15 proves the host was de-labelled, not
      re-registered.
  - claim: "Capacity died inside a five-second window on 2026-09-23, one second after the last job released the host."
    command: "gh api repos/mastermindx-market-intelligence/macro/actions/runs/35819881039/jobs; .../35855143666/jobs; .../35989213316/jobs"
    result: >
      35819881039's job ran on pc-render-1 and finished 2026-09-23T12:05:08Z (a
      REAL red at step 19, "guard - stock dossier integrity (sentinel + identity)"
      - not infra); 35855143666 was created 12:05:09Z with `runner_name` empty and
      completed 2026-09-24T12:05:09Z, exactly +24h00m00s (GitHub's queued-job
      kill); 35989213316's job 107623716720 was created 12:05:10Z with labels
      `[self-hosted, render-linux]` and is still queued.
  - claim: "Three lanes are wedged on this mechanism and a fourth is wedged on a different dead label; daily.yml is unaffected by design."
    command: "gh run list --workflow engine-render.yml; --workflow sector-intelligence.yml; --workflow codex-research.yml; --workflow daily.yml"
    result: >
      engine-render 36095283218 pending with all predecessors cancelled;
      sector-intelligence last success 35807731340 (2026-09-23T01:47:20Z), 35975623694
      queued since 09-24T08:30:16Z; codex-research 35994988547 queued 17.1h on the
      `codex` label; daily.yml healthy at ~01:35Z daily because it routes the live
      `macstudio` label - which is exactly why the per-lane nightly watchdog was
      correctly silent.
  - claim: "1,479 committed site pages carry the shared nav but not the Morning Edition entry."
    command: "grep -rl 'class=\"site-nav\"' site --include='*.html' | wc -l; grep -rl 'am_edition.html' site --include='*.html' | wc -l"
    result: >
      6,920 nav-bearing pages against 5,441 carrying `am_edition.html`, so 1,479
      are stale: 1,251 under `stocks/`, 111 top-level (china/hk/intl/canada/start/
      options/sector_central/crypto/ai_desk/aibrief/mastermind and every
      `strategy_*`), 41 under `sectors/`, 76 basket families, 4 under `basket/`.
      The nav entry is only the probe - every template/CSS/builder change merged
      since 2026-09-23T12:05Z is equally unpropagated.
  - claim: "The new guard flags the real 2026-09-25 hostage and passes its own selftest."
    command: "python3 scripts/check_runner_queue_hostage.py --selftest; python3 -m pytest tests/test_runner_queue_hostage.py -q"
    result: "selftest OK; 14 passed."
  - claim: "R15 fires on all three wedged lanes when the waiver is removed, and the corrected registry passes the policy gate."
    command: "python3 -m pytest tests/test_runner_policy.py -q; python3 scripts/check_runner_policy.py"
    result: "73 passed; `OK`."
  - claim: "The annotation, import-pinning, workflow-size and nightly-liveness contracts still hold over the edits."
    command: "python3 -m pytest tests/test_nightly_liveness.py tests/test_gh_annotation_line_start.py tests/test_check_script_import_pinning.py tests/test_workflow_file_size.py -q"
    result: "97 passed."
unverified:
  - claim: "Restoring `render-linux` to pc-render-1 would release the backlog and re-bake all 1,479 pages in one run."
    what_would_verify: >
      An operator `POST /orgs/mastermindx-market-intelligence/actions/runners/15/labels`
      with `render-linux`, then one render.yml run concluding success and a fresh
      `grep -rl am_edition.html site --include='*.html' | wc -l` reaching 6,920.
      The mechanism is render.yml's per-region `(scope=X, from=SHA)` watermarks in
      its `pick` step, which union the dirty scopes of every skipped push.
  - claim: "The guard's live path (`main()`, not the imported functions) behaves correctly end to end."
    what_would_verify: >
      Its first scheduled run inside nightly-liveness.yml. It was deliberately NOT
      run locally: the breach path calls `_notify` -> `push_ops_alert`, and firing a
      production ops alert from a session is a self-inflicted side effect. Local
      validation imported the module and called `fetch_live_jobs` + `evaluate`
      directly against the live API instead.
  - claim: "Whether the 2026-09-23 label strip was deliberate."
    what_would_verify: >
      An operator statement, or a GitHub audit-log read for
      `self_hosted_runner.remove_label` / `.update` on runner id 15 around
      2026-09-23T12:05Z. Nothing in the repo records a cause.
unresolved:
  - >
    `render-linux` still has zero carriers. The lanes stay wedged until an operator
    restores the label (or stands up a labelled render host); this PR makes the
    condition LOUD, it does not clear it.
  - >
    Run 35819881039 is a REAL red at "guard - stock dossier integrity (sentinel +
    identity)" on a healthy runner. It was the last job ever assigned, so that red
    is still unfixed and will resurface on the first restored bake.
  - >
    `codex-research.yml` is wedged on the dead `codex` label under an existing dated
    waiver whose premise ("the route is dormant") is contradicted by its own queued
    run 35994988547. The waiver should be re-judged, not renewed.
  - >
    `.github/workflows/nightly-liveness.yml` is not in any workstream's
    `owns_paths`; this session added a job to it as the only watchdog host that runs
    on hosted capacity. If a future wave claims that file, claim the new job with it.
next_actions:
  - >
    OPERATOR: decide whether `render-linux` returns to pc-render-1 (org runner id
    15) or moves to a new labelled host. Restoring it releases a `scope=all` bake
    plus a three-day backlog onto a production host in one act, which is why no
    session should do it.
  - >
    After the label returns, watch ONE render.yml run to conclusion (`gh run watch
    <id> --interval 60`) and expect the 35819881039 dossier-integrity red to
    resurface; fix that guard red separately.
  - >
    Re-judge `codex-research.yml`'s `scheduled_use_waiver` against its own queued
    run rather than renewing it.
  - >
    Remove `render-linux`'s `automatic_use_waiver` in the same act that restores the
    carrier, and set `status: live` with the real `carried_by` - the waiver text says
    so explicitly.
do_not_redo:
  - >
    Do not re-test the `cancel-in-progress` livelock hypothesis on render.yml or
    engine-render.yml. Both carry `cancel-in-progress: false` and have since the
    2026-07-17 starvation postmortem; the `cancelled` runs are superseded PENDING
    runs. Check `startedAt`/`runner_name` before ever calling a cancelled run a
    killed bake.
  - >
    Do not re-point render.yml's push default at `render-heavy`. mac-builder-light
    also carries `macstudio`, so render traffic would contend with the nightly,
    closing-bell and asia-close lanes, and ci.yml's own comments record render
    traffic starving merge-on-green. W3 is Sol-accepted with "preserve the
    render-linux default and the M2 as rollback-only".
  - >
    Do not open a heal PR that splices template hunks into the other 1,479 stale
    pages. PR #7996 did that for ONE page under a byte-guard deadline; at this scale
    it would commit 1,479 unstamped pages and fight the next real bake. One
    successful render re-bakes the whole backlog through the scope-union watermarks.
  - >
    Do not add pc-ci-4 to any `live` `carried_by` roster to make the registry look
    complete. R14 refuses it without a separate audited carrier and an online/idle
    receipt; its platform labels belong only in
    `pool_topology.pc-ci.pending_labels`.
  - >
    Do not set `pool_topology.pc-render.slots: 0` to express the missing capacity.
    R7 requires exactly one reserved slot - it is an architectural reservation, not
    a liveness claim. Use `missing_labels` instead.
  - >
    Do not run `scripts/check_runner_queue_hostage.py` without `--selftest` from a
    session to "check the fleet". Its breach path pushes a production ops alert.
    Import the module and call `fetch_live_jobs` + `evaluate` instead.
danger_areas:
  - >
    `.github/runner-policy.yml` is a hand-maintained DECLARATION. Every rule in
    `check_runner_policy.py` reads it, so the moment capacity dies the file is wrong
    in the direction that makes the gate pass. Treat R11-R15 as declaration hygiene
    and the live-state checker as the actual switch.
  - >
    A watchdog that routes a self-hosted label can be taken down by the very outage
    it watches. `queue-hostage` is pinned to `ubuntu-latest` and
    `tests/test_runner_queue_hostage.py` asserts it never routes to the pool it
    watches - do not "consolidate" it onto fleet capacity.
  - >
    Editing `.github/workflows/**` or `.github/ci/**` selects the FULL job set, so
    this PR runs every pack and every inherited main red surfaces on it.
  - >
    Threshold coupling: the 8h `MAX_QUEUE` only works because it is well under
    GitHub's 24h queued-job kill. Raising it past ~20h makes the alarm fire after
    the evidence has already been destroyed by the kill.
prs: [7996, 7970]
discoveries:
  - DSC:DELABELLING-AN-ONLINE-RUNNER-IS-INVISIBLE-TO-EVERY-LIVENESS-INSTRUMENT
  - DSC:QUEUED-JOB-HOSTAGE-HOLDS-THE-NIGHTLY-CRON-GROUP
---

## One-paragraph orientation for a cold stranger

The page-bake lanes on main were not livelocked by workflow concurrency. They were
starved of a runner. On 2026-09-23 at 12:05Z the label `render-linux` lost its last
carrier while the host that used to carry it, pc-render-1, stayed online and idle
under its original org runner id 15. From that second on, every push to main created
a render.yml run whose single job could never be assigned: the run stayed alive
holding the `pipeline-render` concurrency group until GitHub's 24-hour queued-job
kill, and each firing behind it was superseded and concluded `cancelled`. Two days of
that produced exactly one `queued` run, a rolling `pending` successor, ~25 `cancelled`
predecessors, zero reds, and 1,479 committed pages frozen at pre-2026-09-23 template
bytes. The same shape wedged engine-render.yml and sector-intelligence.yml;
codex-research.yml is wedged the same way on a different dead label. daily.yml stayed
healthy because it routes `macstudio`, which is why the nightly kept baking data and
the per-lane liveness watchdog was correctly silent.

## What this PR does and does not do

It ships the instrument that would have caught this in under eight hours instead of
two days, widens the declaration gate from `schedule` to every automatic trigger, and
corrects `.github/runner-policy.yml` from a 2026-08-17 declaration to the 2026-09-25
live receipt. It does not restore capacity. Restoring `render-linux` releases a
`scope=all` bake plus a three-day dirty-scope backlog onto a production host in a
single act, the 2026-09-23 strip has no recorded cause so it may have been
deliberate, and `.claude/hooks/gh_quota_guard.py` shape 6 exists precisely because
sessions have taken production-lane decisions like this before. That act is the
operator's.

## Why no heal PR for the 1,479 pages

render.yml's `pick` step carries per-region `(scope=X, from=SHA)` watermarks, so one
successful render unions the dirty scopes of every skipped push and re-bakes the
entire backlog with correct `?v=` stamps. Splicing template hunks into 1,479 stamped
pages by hand would commit unstamped bytes that the first real bake then has to
fight. PR #7996 did that for a single page under a byte-guard deadline; it is a
deadline remedy, not a recovery strategy.
