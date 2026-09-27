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
  - claim: "The `codex` waiver's stated mechanism is falsified by its own lane: the queued run is the group HOLDER and is never superseded, so the lane is hostage-taking after all."
    command: "gh api repos/mastermindx-market-intelligence/macro/actions/workflows/codex-research.yml/runs?per_page=8 --jq '.workflow_runs[]|{id,status,conclusion,created_at,updated_at}'"
    result: >
      35994988547 (created 2026-09-24T11:46:30Z) is still `queued` 22h later and
      holds the group; 36032578502, 36062008421 and 36078078689 each entered
      `pending` behind it and were superseded 1s after the next firing was created;
      36109614790 (2026-09-25T07:49:21Z) holds the pending slot now. The waiver's
      original reason - that a single-job run's queued firing would be superseded
      rather than hold the group for 24h - describes the `pending` successors, not
      the holder. Corrected in `.github/runner-policy.yml` in this PR; the waiver
      is KEPT, because restore is genuinely operator-owned (CRX-R7/CRX-R8), but its
      reason no longer claims the lane is harmless.
  - claim: "1,479 committed site pages carry the shared nav but not the Morning Edition entry."
    command: "grep -rl 'class=\"site-nav\"' site --include='*.html' | wc -l; grep -rl 'am_edition.html' site --include='*.html' | wc -l"
    result: >
      6,920 nav-bearing pages against 5,441 carrying `am_edition.html`, so 1,479
      are stale: 1,251 under `stocks/`, 111 top-level (china/hk/intl/canada/start/
      options/sector_central/crypto/ai_desk/aibrief/mastermind and every
      `strategy_*`), 41 under `sectors/`, 76 basket families, 4 under `basket/`.
      The nav entry is only the probe - every template/CSS/builder change merged
      since 2026-09-23T12:05Z is equally unpropagated. COUNT VERIFIED BY SET
      DIFFERENCE, not subtraction: `comm -23` over the two sorted lists gives 1,479
      (the 5,441 figure is the INTERSECTION; the full `am_edition.html` population is
      11,150, because many carriers use a different nav family).
  - claim: "The 1,479 pages are NOT the render lane's exclusive estate - the proximate cause is a PARTIAL 2026-09-25 nightly."
    command: "git show --format='' --name-only 969883bc973 -- site/stocks | grep -c '^site/stocks/'; git show --format='' --name-only fab3ad33b72 -- site/stocks | grep -c '^site/stocks/'; ls site/stocks/*.html | wc -l"
    result: >
      The 2026-09-25 nightly `969883bc973` rewrote 1,485 of 2,736 `site/stocks/`
      pages; the 2026-09-24 nightly `fab3ad33b72` rewrote 2,687 of the same 2,736.
      `2736 - 1485 = 1251` is EXACTLY the stale `stocks/` count, and the prior night
      covered 2,687 of them, so these pages are inside `daily.yml`'s estate, not the
      render lane's. Sampled stale dossiers ABAT/ABEO/ABOS last baked at
      `fab3ad33b72` (09-24T09:39Z); A/AA at `969883bc973` (09-25T07:52Z). A
      content-identity optimisation cannot explain the gap, because #7970's nav entry
      changes every rebuilt page's bytes. WHY the 09-25 nightly went partial is NOT
      established here and belongs to the `daily.yml` lane. The render outage explains
      why the split PERSISTS (only `scope=all` sweeps the whole estate in one act),
      not why each page is behind. An earlier revision of the postmortem asserted the
      opposite and is corrected in this PR.
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
      set difference (`comm -23`) over the nav/am_edition lists reaching 0.
      The mechanism is render.yml's per-region `(scope=X, from=SHA)` watermarks in
      its `pick` step, which union the dirty scopes of every skipped push; a watermark
      this far behind forces the defensive `scope=all` at render.yml:583, and scope=all
      is what rewrites the whole estate in one act. NOTE the justification is "one act
      sweeps everything", NEVER "these pages have no other baker" - the nightly bakes
      them too, just partially (see the partial-nightly claim under `verified`).
  - claim: "The live www surface is staler than the committed tree, so a restored render alone would not reach users."
    what_would_verify: >
      Committed `site/advanced.html` is 106,475 bytes with the am_edition entry; live
      `https://www.mastermind-x.com/advanced.html` returns 200 at 105,775 bytes with
      ZERO am_edition hits, and that page last baked at `969883bc973` 2026-09-25T07:52Z
      - so the VPS is serving bytes from before 07:52Z. Consistent with the recorded
      `# MMX-DISK-TRIAGE-HOLD` on the VPS pull cron since 2026-09-25T04:00Z, but this
      session did NOT open a VPS shell, so the hold itself is unconfirmed here. Verify
      with `crontab -l` on the VPS. Meanwhile `/live/staleness.json` (served from the
      separate `/var/lib/macro-live/public` root, generated_at 2026-09-25T10:12:05Z)
      reports `ok:false`, stale `hub`/`r2_massive_stock_day`/`us_stocks` and blind
      `entry_radar_live`/`prophet_us`/`us_standouts`, with `hub` at bake_age 36.6h
      against a 26h budget - the site's own content sentinels ARE firing, which is
      independent corroboration and does not contradict the workflow-liveness watchdog
      being correctly silent.
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
    PR #8011's two reds are MAIN's, proven by name on main's own baseline
    `36115669812` (ref main, 6c9465c7e) which concluded `failure` 2026-09-25T11:44:44Z:
    job 108011795656 = `nyse-calendar-freshness` / "nyse + tsx calendar rules,
    first-party imported-name resolution"; job 108011795620 =
    `market-os-macro-suite-pages` / "Market OS macro suite pages - shell, labels,
    view model, builder". Both match #8011's Stop-hook evidence on LOGICAL JOB and
    PROOF ID, which is the identity the guard keys on - never compare ci-pack-N,
    run_ci_pack.py rebalances. Do NOT re-derive this; read the two
    `check-runs/<job>/annotations` payloads.
  - >
    CRITICAL PATH - SUPERSEDED, read the correction below before acting. I published
    "#7870 lands -> ci-pack-4 greens -> #6930 lands -> main greens" and posted that
    receipt on #7870 (5831855744) and #6930 (5831860668). The pack-4 half was undone
    by a route I did not anticipate: `e5512ef66a7 Revert "Merge #7908: Robotics Theme
    Intelligence implementation carrier" (#8013)` landed 2026-09-25T11:01:33Z, so
    `nyse-calendar-freshness` is green WITHOUT #7870 landing and that carrier is no
    longer any part of the fleet's blocker. Retracted to its owner in 5835036878.
    Durable residue: a vertical importing #7870-only modules must not merge ahead of
    it, which is exactly what #7908 did. Remaining main red WAS
    `market-os-macro-suite-pages`, which I attributed to #6930's copy decision. That
    attribution of the CARRIER was wrong too - see the 2026-09-26 entry below. Do NOT
    open a `main-red-repair` for it: it is already healed, and allowlisting is recorded
    as the wrong remedy for the import sweep.
  - >
    A RED CAN BE ALREADY FIXED ON MAIN AND STILL RED ON YOUR HEAD, because CI grades
    the MERGE REF at the moment it is taken. Run 36131411907 took its merge ref
    2026-09-25T11:48:29Z and failed `ontology-explorer`; the fix
    `6e83609d94d fix(ci): strip the nightly's banner tag in the ontology byte guard
    (#8029)` landed 13:35:57Z, i.e. AFTER. The three ontology suites passed locally at
    that same head (66 passed), which is the tell: tests green locally + red in CI +
    an upstream fix timestamped after your merge ref = stale base, not a defect. The
    remedy is `git merge origin/main`, never debugging the test. Do not spend a cycle
    re-deriving this; compare the fix commit's `%cd` against the run's `createdAt`.
  - >
    Main's ci.yml proof was livelocked again 2026-09-25T14:44-15:28Z: 36149551398,
    36150758771 and 36152965360 all concluded `cancelled` with 36154418482 pending -
    sibling sessions re-dispatching over each other, the documented 2026-08-09 shape
    where the escape hatch IS the lock. Never dispatch to "help"; 36154418482 is on
    8f978feedf3, which is #8011's merged base, so if it survives it proves this base.
  - >
    The `codex` lane's wedge itself is still open and still operator-owned: the
    declaration was corrected, the carrier was not. Expect 35994988547 to be killed
    at 2026-09-25T11:46:30Z and 36109614790 to be promoted and re-wedge seconds
    later; do not read that kill as a recovery.
  - >
    Remove `render-linux`'s `automatic_use_waiver` in the same act that restores the
    carrier, and set `status: live` with the real `carried_by` - the waiver text says
    so explicitly.
  - >
    RESOLVED 2026-09-26: main is GREEN and #8011's last inherited red is gone. Four
    consecutive `completed/success` ci.yml baselines, newest 36239122567 (created
    2026-09-26T11:32:03Z, sha bd23cfbd3f1). The heal was NOT #6930 - it shipped as
    `1f2b713e37e fix(macro): stale-source next action drops banned copy; its tests stop
    reading the day's data (#8032)`, and #6930 is still open. Retracted to that owner in
    5847985820. DURABLE LESSON, earned TWICE in this one session: a red correctly
    attributed to MAIN heals by whichever PR reaches main first, so naming the carrier
    is a separate and far weaker claim than naming the owner-of-the-red. I published a
    carrier twice (#7870, then #6930) and was wrong both times, each time planting a
    false critical path on somebody else's PR. Attribute a red by logical job name;
    state the remedy as "main must green", never as "<PR> must land".
  - >
    #8011 was carried forward onto that green base: `git merge origin/main`
    (c54b1f2e807) clean with a clean tree, head d89988a3727 -> d1dee8989a1, 183 commits
    of base picked up, the stale `merge-blocked` label removed, `merge-on-green` left
    armed. Recorded on the PR in 5847982610. That makes THREE reds on this one PR
    cleared by a base merge and none by a code change - nyse-calendar-freshness via
    #8013, ontology-explorer via #8029, market-os-macro-suite-pages via #8032. When a
    red's fix is timestamped after your run's merge ref, the base merge IS the fix.
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
    A SESSION WORKTREE'S NAME IS NOT ITS BRANCH NAME. This tree is
    `.claude/worktrees/recursing-villani-ee565f` but the PR head branch is
    `claude/render-lane-dead-label-detector`. I pushed
    `HEAD:worktree-recursing-villani-ee565f` from the worktree name and silently
    created a NEW remote branch instead of updating #8011 - the push "succeeded",
    printed a create-a-pull-request hint, and left the PR's head untouched. Read the
    branch from `gh pr view <n> --json headRefName` or `git rev-parse --abbrev-ref
    HEAD`, never from the directory. I deleted the stray ref in the same minute.
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
predecessors, zero reds, and 1,479 committed pages holding the pre-#7970 nav (at the 2026-09-24T09:39Z nightly bake, not frozen at the outage - see the partial-nightly correction) template
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
