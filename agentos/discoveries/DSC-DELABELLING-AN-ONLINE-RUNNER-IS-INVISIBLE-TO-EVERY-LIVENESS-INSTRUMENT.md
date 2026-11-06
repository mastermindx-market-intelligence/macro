---
key: DELABELLING-AN-ONLINE-RUNNER-IS-INVISIBLE-TO-EVERY-LIVENESS-INSTRUMENT
claim: >
  A self-hosted runner can lose a custom label while staying `online`/`idle` under
  its ORIGINAL runner id, because `DELETE /orgs/{org}/actions/runners/{id}/labels`
  strips custom labels down to the read-only set `{self-hosted, <OS>, <arch>}` and
  touches nothing else. Every instrument this repo owns then reads green: a host
  census sees the listener online, `check_runner_policy.py` R11 passes because the
  label is still DECLARED, R12 is exempt because the consumer lane is push-only,
  and `check_nightly_liveness.py` is silent because the lane it grades routes a
  different, live label. The wedge that follows is the known queued-job hostage
  (DSC:QUEUED-JOB-HOSTAGE-HOLDS-THE-NIGHTLY-CRON-GROUP) but with NO red anywhere
  and no host to find missing: on 2026-09-23T12:05:04Z-12:05:09Z `render-linux`
  lost its last carrier while pc-render-1 (org runner id 15) stayed online and
  idle, and render.yml, engine-render.yml and sector-intelligence.yml each spent
  the next two days cycling one 24h-killed queued run into one superseded pending
  successor. There was NO clean visible symptom, which is the whole finding: the
  1,479 committed `site/**.html` pages holding pre-#7970 nav bytes look like the
  outage's fingerprint but are NOT - nightly `969883bc973` rewrote 1,485 of 2,736
  `site/stocks/` pages and `2736-1485=1251` is exactly the stale `stocks/` count,
  so a LIVE lane owns them and the dead label only explains why the split persists.
  A de-labelled runner's real signature is the absence of anything: no red, no
  missing host, and no artifact you can attribute to it without arithmetic.
falsifier: >
  `gh api orgs/mastermindx-market-intelligence/actions/runners --jq '.runners[]
  | select(.labels[].name=="render-linux") | {id,name,status,busy}'` returning a
  carrier while a render.yml job is held `queued` would disprove the causal claim;
  a carrier absent while pc-render-1's id is NOT 15 (i.e. the host was
  re-registered rather than de-labelled) would disprove the de-labelling half.
  `python3 scripts/check_runner_queue_hostage.py --selftest` plus
  `python3 -m pytest tests/test_runner_queue_hostage.py -q` is the pinned form.
so_what: >
  Never accept "the host is online" or "the label is declared" as proof a lane can
  run. To answer "can this label still take work", read LIVE job state - a job that
  is `status=queued` with no `runner_name` and a self-hosted `runs-on` for longer
  than any honest wait is the only positive observation of absence - which is what
  `scripts/check_runner_queue_hostage.py` does (8h threshold, 1/3 of GitHub's 24h
  queued-job kill, lane-agnostic so it cannot be exempted by trigger). Corollary
  for diagnosis: on a wedged coalescing lane the `cancelled` runs are NOT evidence
  of a cancel-in-progress livelock - check `startedAt`/`runner_name` first, because
  a superseded PENDING run and a killed in-flight run both conclude `cancelled`.
  Corollary for repair: restoring the label releases the whole backlog at once onto
  a production host, so it is an operator act, not a session act.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  `gh api orgs/mastermindx-market-intelligence/actions/runners` (pc-render-1 id 15
  online/idle, labels self-hosted,Linux,X64; zero carriers of `render-linux`
  anywhere, org or repo pool); render.yml job chain 35676379868 (last success, job
  on pc-render-1 2026-09-22T05:11:10Z) -> 35819881039 (last job ever assigned,
  released the runner 2026-09-23T12:05:08Z) -> 35855143666 (created 12:05:09Z,
  runner_name empty, completed 2026-09-24T12:05:09Z == +24h00m00s) -> 35989213316
  (job 107623716720 created 12:05:10Z, labels [self-hosted, render-linux], still
  queued); engine-render 36095283218 and sector-intelligence 35975623694 in the
  same state; daily.yml healthy on the live `macstudio` label throughout.
  Blast radius measured by grepping committed `site/**.html` for
  `<nav class="site-nav">` (6,920 pages) against `am_edition.html` (5,441).
  Postmortem: research/RENDER_LANE_OUTAGE_2026_09_25_POSTMORTEM.md.
scope: [macro, ".github/workflows/**", ".github/runner-policy.yml", "scripts/check_runner_queue_hostage.py"]
confidence: verified
---

## Why each existing instrument was correctly silent

| Instrument | What it grades | Why it did not fire |
|---|---|---|
| `check_nightly_liveness.py` | the nightly lane's own artifacts | `daily.yml` routes `macstudio`, which never died; the nightly kept baking |
| `freshness_sentinel.py` | data artifact ages | render is a *template/page* bake; the data was fresh |
| `check_runner_policy.py` R11 | every referenced label is DECLARED | `render-linux` is declared; declaration is not liveness |
| `check_runner_policy.py` R12 | a `schedule:` consumer of an `orphaned` label | the wedged lanes are push-only, and the registry said `offline`, not `orphaned` |
| the `cancelled` run count | nothing - it is an artifact | superseded PENDING runs conclude `cancelled` exactly as killed in-flight runs do |

The deeper property: **a declaration gate cannot see a death nobody wrote down.**
`.github/runner-policy.yml` is hand-maintained, so the instant capacity dies the
registry is wrong in the direction that makes the gate pass. That is why the fix
shipped alongside this record is a live-state reader, not another declared rule.

## The 5-second window

`35819881039`'s job finished at `2026-09-23T12:05:08Z` and the successor run was
created at `12:05:09Z` with no runner ever assigned. Capacity therefore ended
inside `12:05:04Z -> 12:05:09Z`, one second after the last job released the host.
Nothing in the repo records a cause, which is why the restore is operator-owned:
the strip may have been deliberate.
