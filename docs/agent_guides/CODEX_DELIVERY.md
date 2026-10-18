## Definition of done

DONE for ordinary substantive, verified work is the full delivery chain, which is
never abandoned partway and never handed back to the operator to finish:

1. commit;
2. push;
3. open a pull request;
4. check CI and resolve genuine failures;
5. same-day squash-merge and delete the remote branch;
6. deploy or wait for the repository's normal deploy lane, then verify the change
   on the real live URL.

**One session owns all six for ordinary work.** There is no earlier "worker done" state — the rule
that let a session terminate on an armed pull request was REMOVED by the project
owner on 2026-08-12 ("ur the owner of this project so u keep it until its
finished, no need for handoff"). It had turned an unfinished job into a
reported-complete one: a session declared itself done while its pull request sat
`merge-blocked` on a red check, and the owner had to reopen the work by hand.
Stopping at a local commit, at an open pull request, or at an armed-but-unmerged
one is abandoned work, not delivered work.

**The one non-merge terminal state is `PARKED / HOLD-FOR-SOL`.** It exists only when
`DEC:SOL-HOLD-IS-A-MERGE-BARRIER` is fully satisfied: exact PR head pushed and local
worktree clean; binding checks concluded green; PR DRAFT; no `merge-on-green` label;
native auto-merge null; title/body/comment holds merge and names Sol as authority plus
a Sol-controlled release condition. PARKED is terminal for the current ship/merge attempt
but is NOT SHIPPED, not deployed/live evidence, and not a retryable `SHIP LOOP BLOCKED`
state. Report it once and stop shipping. Do not poll, arm, mark ready, merge, or re-enter
the ship loop until Sol changes or releases the hold. Ambiguous/incomplete hold state
remains ordinary unfinished work and fails closed.

**That terminality is scoped to the ship attempt, never to the worker**
(`DEC:HOLD-PARKS-SHIP-NOT-DIALOGUE`). The reciprocal worker/Sol child dialogue remains
nonterminal: the same child, carrier, branch and PR resume on a same-carrier Sol
`CONTINUE` / `RULING` / `REQUEST_REPAIR`, and only an explicit same-carrier Sol STOP (or
`ACCEPTED / STOP`, `CLOSED / STOP`) closes the child. Before yielding at PARKED you must
already have posted one exact-carrier `RESULT / HOLD-FOR-SOL` and established a truthful
continuation path — `WATCH_ARMED` only for a real, verified registration, otherwise
`WATCH_UNAVAILABLE` naming the surface checked and the exact failure. "Waiting for Sol"
is not a continuation path, and going silent on the holding authority is not a lawful
stop: the task/wave boundary, the PR merge hold, the reasoning-session yield, the child
STOP and program completion are five distinct facts, and none may be inferred from another.

`merge-on-green` remains available and is still the recommended way to get the
merge PERFORMED for ordinary work — arming it means you do not have to run the merge yourself. It
is not a reason to stop: keep the session alive until the pull request is merged
and the change is verified live. The only holds are an explicit operator request
to hold, a genuine non-spurious failing check, or a real deployment blocker.
For Macro, the `Workers Builds: macro` red X is known-spurious. Template/source
changes must include their paired `site/` artifact when required, and “merged” is
not “live” until the VPS/render path and live marker are verified.

**Healing a red pack: claim the lane FIRST, and heal the WHOLE pack (2026-08-07,
#4850 closed unmerged).** A fleet-wide red is being worked by the whole fleet, so
before writing a line: identify every red job **by name** and confirm its pack
(`python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml
--pack-index N --pack-count 12 --validate-only`) — never trust the pack index in a
failure report, `run_ci_pack.py` rebalances whenever any job's weight moves — then
check `gh pr list --search "<filename>"` and `docs/ACTIVE_BUILD_MAP.md` for an open
lane on the files you are about to touch. The "before proposing new work" rule is
scoped to NEW work and does not cover heals, which is exactly how this was missed.

**A pack is ONE check, so two partial heals DEADLOCK.** With two independent reds
in `ci-pack-3`, the ITR-only PR stayed red from the stale report and the
report-only PR stayed red from ITR: neither could ever go green, so neither could
merge. One PR must carry every fix the pack needs. Cherry-pick a sibling with `-x`
(authorship preserved) rather than rewriting it, and read its diff first — the
sibling's version is often the better one.

Sessions SHOULD heal. The “don’t propose in-flight work” line is for new
features; heals are the exception (this bullet exists because #4850 was missed
that way). One PR per pack stays — different packs still get separate heal PRs.

**Missing hole (2026-08-14, #5715/#5717 deadlock then #5689 absorbed both):**
if TWO (or more) packs are red on main AND required `ci-gate` needs every pack
green AND `gh pr merge --admin` is refused by the repository ruleset, two
whole-pack PRs still cannot land. Then ONE PR labelled `main-red-repair` must
carry every pack heal that `ci-gate` is blocking. Do not wait. Do not open a
second `main-red-repair`. That is not a repeal of one-PR-per-pack; it is the
mutual-block exception.

**Re-fetch `origin/main` and re-run the job line before pushing OR merging.** On a
red main the tree moves in hours (five heal PRs landed mid-session here), and a
`merge-blocked` "real content conflict" on a heal PR usually means the heal already
landed rather than that you must resolve anything. Diff against fresh main
(`git diff --stat origin/main HEAD -- <files>`; empty = already there) and **close
rather than force through** — a superseded regeneration silently reverts the better
fix that landed behind you (#4850's live-cache report would have reverted #4842's
frozen-slice render).

**Merge on CONCLUDED checks, never mid-flight (operator 2026-07-28).** A pending
check is not a pass: an `--admin` squash-merge while the PR's packs are still
running used to fire a `pull_request: closed` event into the live concurrency
group and cancel the PR's own proof run — the merged head then carried
`cancelled` packs forever (PR #3867), unproven merges stacked up red on main, and
every ship-loop session pinned on the next full-CI dispatch (measured 2026-07-28:
100 ci.yml runs in 8h, 6 successes). ci.yml now fences merged-close events into
their own concurrency group so a fast merge no longer destroys its own evidence,
but the discipline stands: wait for the packs to conclude (green, or spurious-only
red) before squash-merging. Do NOT arm `gh pr merge --auto --squash` as the wait:
main carries no branch protection, so auto-merge has no required checks to gate on
and merges IMMEDIATELY (verified PR #3889, 2026-07-28 — merged ~1 min after arming
with packs still pending). That "no protection" is the NORMAL state, not a law of
nature: a repository ruleset can appear at any time and reject even the nightly's
bot pushes with GH013 — `ci-recovery-bootstrap-freeze-2026-08-15` did exactly
that 08-15→08-17 (bypass = org admin only, minted with no DEC record), froze
every Prophet board for three days, and no instrument saw it because the engine
kept BUILDING green and only the push died. When pushes to main mysteriously
fail, `gh api repos/{owner}/{repo}/rulesets` is the FIRST diagnostic, and any
deliberate freeze must ship a DEC record plus an expiry plan
(research/PROPHET_OUTAGE_2026_08_17_POSTMORTEM.md).

**ARM `merge-on-green`, THEN STAY.** After opening an ordinary pull request, run
`gh pr edit <n> --add-label merge-on-green`.
**Arm LAST — never push into an already-armed pull request (measured #8163, 2026-09-29).**
The window between the sweeper deciding to merge and the merge completing is invisible from a
session, so a commit pushed onto an armed PR can land on the far side of it. Measured: the
sweeper merged head `2ff0f92f` at 02:09:24Z while the follow-up commit carries committer time
02:09:24Z, so the push completed at or after the merge. GitHub accepted it with `rc=0`, did not
reopen or amend the PR, and raised nothing — and every field a session can read was identical
to success: `state=MERGED`, a true `mergedAt`, the right `mergeCommit`, and `headRefOid`
reading the merged head, which is also the correct value on a healthy merge. `--json files` is
a second false friend: it reports the MERGED paths, so the obvious check "do the PR's files
appear in the squash?" compares the merged head with itself and passes on a PR that provably
lost two files. No read of a pull request can see a commit that arrived after its merge; only
the branch ref can — **`git fetch origin` FIRST**, then
`git log origin/main..origin/<branch> --name-only`, then a per-path blob comparison against
`origin/main`, which is squash-tolerant because a squash preserves the tree even though it
rewrites the commit. **The fetch is not hygiene, it is the whole test: `origin/main` is a LOCAL
ref**, so a stale one makes every path report missing and this check then tells you to replay
work that already landed — duplicating it. Measured 2026-09-29: the #8169 watcher compared
without fetching, exited `MERGED BUT NOT LANDED`, and both files were byte-identical in main the
entire time. A verifier that cries wolf on every merge is as useless as one that never fires,
and this one fails toward a destructive remedy — so on a MISSING verdict, re-fetch and re-run
before believing it, and cross-check by grepping main's own bytes for a string only your commit
introduced (`git grep <needle> origin/main -- <path>`). **And fetch `main` on its OWN — never
bundled with the branch ref.** The measured mechanism is nastier than a forgotten fetch: GitHub
**deletes the head branch on merge**, so the natural one-liner `git fetch origin main <branch>`
fatals with `couldn't find remote ref <branch>` and, because it aborts, leaves `origin/main`
un-updated — while the stale local `origin/<branch>` survives and keeps the comparison looking
perfectly functional. **The merge's own success is what breaks the check that verifies the
merge.** So: bare `git fetch origin` (or `git fetch origin main` alone), check its exit status
rather than swallowing it, and treat the branch's absence from the remote as the EXPECTED
post-merge state — you are comparing your local `origin/<branch>` against a freshly updated
`origin/main`, and only the latter has to be current. Push every commit the PR needs, THEN add the label; if a
late push is genuinely required, disarm, push, re-arm under the disarming rule below; and treat
`MERGED` as a fact about a pull request, never about your bytes.
`DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS`.
**Current topology (2026-08-21): `.github/workflows/merge-on-green.yml` still runs on
`[self-hosted, macOS, ARM64, merge-control]` on the M2; it is NOT yet GitHub-hosted.**
W1-A's read-only hosted canary is merged, but production authority stays on the M2 until
its required post-merge canary receipts accept W1-B. Do not reason from the planned hosted
cutover as though it already happened. The sweeper runs every 10 minutes and squash-merges
the pull request once every check has CONCLUDED clean, with the known-spurious
`Workers Builds: macro` X excluded. A genuine red or a merge conflict gets the
`merge-blocked` label plus ONE explanatory comment instead of a merge; the
`merge-on-green` label stays armed, so a rerun that greens the head merges on the
next sweep.

Arming it is a BACKSTOP that saves you the merge command — it is not an exit. The
sweeper cannot fix a red, cannot resolve a conflict, and cannot verify the change
live; those are yours, and you will not learn they are needed if you have already
stopped. For ordinary work, `ship_loop_guard.py` blocks a session whose pull request
is armed but not merged, and NAMES the reds the sweeper would refuse, so the answer
to "am I done" is "is it merged". A ratified `HOLD-FOR-SOL` is the explicit exception:
its answer is `PARKED`, never `SHIPPED`, and the forbidden merge is not retried. Merging
by hand on concluded-green stays fully valid and is often faster than waiting a sweep.
After any accidental fast merge, the surviving PR proof run is the merge's evidence —
watch it to conclusion. `--admin` remains only for the spurious Workers X, docs-only
pull requests that trigger no pack checks, and genuine wedges — never to outrun CI.

**A RECORDED HOLD IS A MERGE BARRIER (Sol 2026-08-19, #5974/#5953).** A hold stated in a
PR's body or comments (HOLD-FOR-SOL / "do not merge") binds EVERY merge path — the sweeper,
blanket-arming sessions, and manual merges alike — regardless of label state. Enforce it as
state (no arming label, `autoMergeRequest` null, DRAFT, hold comment naming authority +
release condition), and never arm a PR you did not open without grepping its
title+body+comments for a hold. Once that protocol is complete, the exact head is pushed
and clean, and binding checks are green, the delivery state is `PARKED / HOLD-FOR-SOL`:
terminal for the current ship/merge attempt, not SHIPPED, and not a retryable blocker.
Report once; do not poll, re-arm, mark ready, merge, or re-enter the ship loop until the
holding authority changes or releases the hold — but that is the SHIP attempt ending, not
the child: the worker/Sol dialogue remains nonterminal and only an explicit same-carrier
Sol STOP closes it (`DEC:HOLD-PARKS-SHIP-NOT-DIALOGUE`). Conditional merge authority granted for one PR NEVER
transfers to any other PR (`DEC:SOL-HOLD-IS-A-MERGE-BARRIER`).

**DISARMING IS NEVER SILENT (PR #5291, 2026-08-11).** The sweeper never removes
`merge-on-green`; `scripts/merge_on_green.py` has no code path that does. Every
removal is a session's deliberate act, so treat it as one: taking a pull request
manual — your own or a sibling's — requires, IN THE SAME ACT, a visible marker
(`merge-blocked`, or a PR comment naming your session and what you intend) and
ownership of that pull request through to merged-or-handed-back. A bare
`gh pr edit <n> --remove-label merge-on-green` with no marker is not a hand-off, it
is a disappearance: the sweeper only ever lists LABELED pull requests, so a disarmed
PR leaves its world entirely and no later sweep can label, comment on, or merge it.
PR #5291 was stripped twice in one evening (02:13:34Z, 02:21:36Z) with no marker
either time, sat red and unattributed, and needed a manual `--admin` merge at
02:32:52Z to escape. The sweeper now marks a fresh red within seconds of the failed
run (failure wake-ups run a bounded mark-only pass), but that only shrinks the
window — it cannot make a silent disarm visible.

**A `merge-blocked` backlog means main is UNPROVEN, not that the pull requests are
bad (#5037, 2026-08-08).** The sweeper's base-inherited-red refresh — the mechanism
that drains an armed backlog once main is healed — can only tell an inherited red
from a real one against a RECENT proof of main. `ci.yml` has no `push` trigger, so
main is proven ONLY by a `workflow_dispatch`, while the nightly/wire lanes push ~24
`[skip ci]` commits per 2 hours — so any commit-window heuristic ages out in ~100
minutes. Measured 2026-08-08: main's newest proof sat **117 commits / 12 HOURS**
back, the refresh resolved zero pack names, and 61 pull requests sat armed with 60
of them red on `ci-pack-2`/`ci-pack-3` that main's own last run had proven green.
Three properties now hold and must not be regressed: the proof is resolved from the
newest completed `ci.yml`/`fences.yml` **RUN on main** (velocity-independent, and
cheaper than the walk it replaced); a refresh additionally requires that proof to
**POSTDATE** the pull request's failing checks (correctness — a green that predates
your red does not excuse it — and the loop guard, because `update-branch`'s
422-on-current-head does NOT prevent loops when main moves every few minutes); and
the sweeper **dispatches its own main baseline** when its proof is too stale to
answer the reds it just saw. **Diagnose a fresh backlog from the sweep log first:** a
summary reading `0 main commit(s) classified`, or a proof set carrying no
`ci-pack-*`, means the refresh path is closed no matter how green main is. Operator
lever unchanged: `gh workflow run ci.yml --ref main`.

**But NEVER dispatch over a live baseline (livelock, measured 2026-08-09).**
Main-ref ci.yml dispatches share ONE concurrency group with
`cancel-in-progress: true`, so every re-dispatch KILLS the in-flight proof: the
11:00Z baseline died 44 min in — likely minutes from concluding — to a sibling
session's re-dispatch, whose own run died 4 min later to the next session's. With
several pinned sessions each firing the lever, no proof ever concludes, the
sweeper keeps reading `0 main commit(s) classified`, and the entire fleet stays
pinned — the escape hatch IS the lock. (fences.yml's main-push runs were dying
the same way under main's ~1/min push cadence, closing the other proof source;
structural fix = event-conditional cancel-in-progress, in flight 2026-08-09.)
Preflight before the lever:
`gh run list --workflow ci.yml --branch main --json databaseId,status,createdAt --jq '[.[]|select(.status!="completed")]'`
— anything `queued`/`in_progress` → WATCH it (`gh run watch <id> --interval 60`)
instead of dispatching. Dispatch only over a clear field, or over a run stuck
`queued` >40 min with the pool otherwise moving (orphaned-run escape — your
dispatch is then the mercy kill, not a murder).

### Waiting on CI without jamming every other session

Ordinary sessions wait out their own merge; a ratified PARKED hold does not poll at all. This
is the ONLY thing restraining fleet-wide polling. Treat it as a hard rule, not as advice.

`gh` authenticates as ONE account token, so GitHub REST's 5,000/hr `core` pool is a
single bucket shared by every parallel session, the babysitter lane, and the hooks.
Exhausting it 403s all of them for up to an hour — including `ship_loop_guard.py`,
which spends up to four REST calls per Stop evaluation and **fails closed** when
rate-limited, so over-polling blocks the very Stop the polling was meant to reach.
A ci.yml run here takes 30–34 minutes. Pace the wait to THAT, not to impatience:
one status read per minute is already generous, and a run that has been going four
minutes cannot be finished.

`.claude/hooks/gh_quota_guard.py` (PreToolUse on Bash) denies the shapes that
emptied the pool on 2026-07-26 and 2026-08-09:

- `gh run watch` at its **default `--interval 3`** — nothing on the command line
  says "3 seconds", which is exactly why it passed review. Use `--interval 60`+.
- a `gh` call inside a loop sleeping under 90s (two watchers on one endpoint at 45s
  went 4,488 → 0 in under an hour);
- `--paginate` over check-runs/jobs — ~130 checks per PR, where one page already
  answers "is it still running";
- re-dispatching a main proof workflow (`ci.yml` / `fences.yml` /
  `integration-baseline.yml`) over one already in flight on main.

It also **flags** — never denies — one more shape (7): re-reading the same status
inside 300s, which attaches an `additionalContext` note and lets the call through.

The guard governs HOW you watch, never WHETHER you may: reading your own pull
request's check state is part of owning it through to the merge, and no state
outside the command line makes that read illegal. That rule is older and stronger
than shape 7, which is exactly why shape 7 advises instead of denying — escalating
it to a deny is a RULING for the operator, not a refactor.

**A blocked Stop is not a demand for a fresh poll** (operator 2026-08-24, repeated
2026-08-27). The commonest burn is neither a loop nor a hot interval: it is one
`gh pr checks <n>` per Stop-hook cycle while a 30–45 minute run finishes. Measured
on 2026-08-27: about twenty-five consecutive Stop cycles, one poll each, by a
session that already had a watcher armed at 150s reporting every transition for
free. The mechanism is not laziness — the Stop hook fires on every turn and
escalates to "If the same genuine blocker persists after another attempt, finish
with `SHIP LOOP BLOCKED:`", which reads as pressure to show a fresh attempt. It is
not. Answer a blocked Stop with a one-line hold note and no tool call; waiting on
CI is explicitly not a qualifying blocker for the escape ladder, so there is
nothing to prove by looking again. The tell: three identical bucket counts in a row
means every further read is waste, and an armed watcher makes polling redundant
because its notifications ARE the check. What is on you: preflight
`gh api rate_limit --jq '.resources.core.remaining'` before arming any long watch,
run exactly ONE watcher per endpoint (a second watcher on the same run buys no
information and doubles the burn), and never read an empty or 403 response as a
settled/green result. REST and GraphQL are separate 5,000/hr pools, so `gh pr view`
continuing to work does not mean `gh api` will.

**Hold notes do not end the Stop loop — go quiet through the ladder, not through
repetition** (operator 2026-08-28). A one-line hold note satisfies the quota rule
above but is not terminal to the guard: the Stop hook blocks again seconds later,
and a session that answers every block with another note types near-identical
hold notes in a tight billed loop for hours (about one hundred such turns measured
on 2026-08-28 while a HOLD-FOR-SOL carrier lawfully waited out a queued CI field
under an armed watcher; the cost is context × turns and the notes carry zero
information after the first). When a long external wait is owned by an armed
watcher or cron and the guard keeps blocking, check the escape-ladder threshold
(any code: 10 consecutive / 15 total); once met, end the turn ONCE with the
literal `SHIP LOOP BLOCKED:` evidence report — literal first characters, naming
the PR, exact head, check state, and watcher id plus cadence — then stay quiet:
no per-Stop hold notes, no tailing your own watcher's output file between ticks.
Real events (watcher exit, cron fire, task notification, operator message)
re-invoke the session; that is the only lawful cadence for a parked wait.

When an operating standard changes, update the repository's `AGENTS.md` and
`CLAUDE.md` together so both Codex and every Claude account inherit it.

### GitHub annotations must start the line (CI-guarded)

Emit `::warning` / `::error` / `::notice` with a bare
`print("::warning title=<slug>::<msg>", flush=True)` — never through a logger.
GitHub only parses a workflow command when `::` is the first thing on the line,
and every builder here logs with a prefixing format, so
`log.warning("::warning ...")` emits `WARNING ::warning ...` and the annotation
is silently dropped. The call reviews as an alarm, runs without error, and
produces nothing in the Actions summary — the worst failure mode for a
fail-soft, which ships degraded output with its only signal gone.

This shipped dead five separate times (#3487, #3515, #3562, #3563, #3570) before
#3587 swept 69 sites across 21 modules and added the guard at
`tests/test_gh_annotation_line_start.py`. Notes:

- `flush=True` is load-bearing: stdout is block-buffered when piped in CI, and
  these sit on paths that may precede a crash.
- Modules that never execute inside an Actions step (FastAPI request paths —
  `brain_gateway`, `download_quota`, `view_ratelimit`) are EXEMPT and listed in
  that test; check `app/` / `admin/` imports before converting an `engine/`
  module, because adding a `print` to a request path is wrong.
- Converting breaks any test that asserts the annotation via `caplog`. Switch it
  to `capsys` AND assert `line.startswith("::")`, so the test pins the property
  that was actually broken rather than the message wording.
- To prove an annotation is live, use GitHub's annotations API — it returns only
  lines it actually parsed:
  `gh api "repos/<o>/<r>/actions/runs/<id>/jobs" --jq '.jobs[].id'` then
  `gh api "repos/<o>/<r>/check-runs/<job_id>/annotations"`.

### Shared render-lane safety

`render.yml` is one shared, coalescing deploy lane. A successful push render at
a merge SHA or any later main descendant covers the earlier merge because the
workflow unions every dirty scope since its last covering watermark. Monitor
that shared covering run; do not demand a dedicated successful run for every
merge SHA.

A **paired plain-copy asset PR needs no render at all.** A non-`.j2` file under
`templates/` that also ships as `site/<name>` — the pairs
`scripts/check_template_site_sync.py` enumerates (a growing set; read the count
from the script): `theme.js`, `mm_brain.js`,
`onboard.js`, `index.html`, the `*.css` — has its `site/` copy committed straight
to main, and the VPS `macro-update` cron pulls main every 3 minutes, so it is live
within minutes whether render ever completes or not. render.yml produces only two
things: re-baked `.j2` pages and the `?v=` content-hash re-stamp. Do not wait on a
perpetually superseded render for such a PR, and do not report it as a blocker.
The one thing you forfeit is that re-stamp: the Caddyfile pins `?v=`-carrying
requests to `immutable, max-age=1y` for an enumerated list (`theme.js`, `live.js`,
`theme.css`, `product-nav-icons.css`, `onboard.*`, `landing.css`, `account.js`,
`nav_market.js`, `supabase.js`, `data_base.js`, `chat*.css`,
`assets/{css,landing}/*`), so for those a warm-cache visitor keeps the old body
until a later render re-hashes the pages that reference them. New visitors always
get fresh bytes. `.j2` pages, `scripts/build_*.py`, and the page-rewriting sweeps
(`optimize_assets.py`, `externalize_css.py`, `inject_data_base.py`, `lib/pages.py`)
still require the render before they are live.

Never cancel or manually re-run an in-progress `render`, `engine-render`, or
`daily` solely to unblock a session. A long job inside its declared timeout is
not wedged evidence. Re-run only after the job has concluded unsuccessfully,
the cause has been identified or corrected, and one session owns the recovery.
Parallel sessions must reuse that recovery instead of launching retries of
their own.

**Hook-enforced as of 2026-08-13.** `.claude/hooks/gh_quota_guard.py` shape 6
denies `gh run cancel`, `POST …/actions/runs/<id>/cancel` and `…/force-cancel`
when the run belongs to `daily.yml`, `closing-bell.yml`, `asia-close.yml`,
`render.yml`, `engine-render.yml` or `weekly.yml`; it fails OPEN when the run
cannot be resolved. The paragraph above already said all of this on 2026-08-12
and did not bind: a live fleet session force-cancelled the US nightly's recovery
dispatches six times (receipt: `POST /actions/runs/31583415065/force-cancel`),
and stacked on the #5362 workflow-size strand the night before it served Prophet
US's 2026-08-10 picks for two full sessions before the operator noticed by
looking at the site. **A cancel is invisible to every staleness instrument in
this repo** — a killed bake and a bake that never fired leave the same trace,
which is nothing. The hook binds Claude-fleet sessions; sessions on other agent
accounts are bound by this paragraph alone, so treat killing a production run as
an OPERATOR call and hand it over rather than taking it.

**Recovery etiquette (2026-08-14).** `scripts/prophet_rescue.py`
(`.github/workflows/prophet-rescue.yml`, hourly at :40 from 23:40Z to 13:40Z) is
now the ONLY auto-redispatcher of `daily.yml`, bounded to two attempts per night
counted across all actors. A session that believes the nightly needs a manual
dispatch must first read the open `prophet-outage` issue — the rescue lane's
receipts live there, including attempts whose POST created no run — and must
never dispatch while a `daily.yml` run is queued or in progress. The two watchdog
lanes, `prophet-rescue.yml` and `nightly-liveness.yml`, are themselves in the
hook's protected set: killing a watchdog is worse than killing a bake, because it
removes the only thing that would have noticed.

Claude enforces this contract with `.claude/hooks/ship_loop_guard.py` at SessionStart
and `scripts/ship_loop_hold_wrapper.py` at Stop. The wrapper delegates every ordinary
state to the canonical guard and only turns a fully lawful Sol hold into terminal
`SHIP LOOP PARKED`. A lawful hold whose binding checks are not yet green instead gets
`HOLD-FOR-SOL WAITING`, or `HOLD-FOR-SOL CHECKS RED` when one concluded red — and since
2026-08-28 that applies on `claude/*` as well as `sol/*`. It used to be `sol/*`-only, so
an ordinary held pull request fell through to `unmerged` and was told to squash-merge and
deploy the very pull request `DEC:SOL-HOLD-IS-A-MERGE-BARRIER` forbids merging; PR #6608
took 121 consecutive blocks carrying that impossible instruction. The repair corrects the
ADVICE only — pending and red still block, `parked` remains the one terminal exit and
still requires every binding check concluded green, and waiting on CI still does not
qualify for the escape ladder, so answer such a block with a one-line hold note rather
than a fresh poll or a `SHIP LOOP BLOCKED` report. For ordinary work, the guard snapshots pre-existing dirty files,
then refuses a normal stop while session-created work is uncommitted, unpushed,
unmerged, awaiting a render, or absent from production. `unmerged` is satisfied by an
actually-MERGED pull request and by nothing else; an armed `merge-on-green` pull request
blocks like any other unmerged one. Codex must apply the same state machine semantically
from this file: ordinary unmerged work is unfinished, while a fully ratified Sol hold is
PARKED and must not be re-polled or merged.

A red that is genuinely this head's files `ci_failed_unmerged`, which is deliberately an
INTERNAL code (10 consecutive / 15 total, not the external 2/3): the state this rule
exists to prevent — alive session, armed pull request, red the sweeper will never merge,
head still pushable — must not also be the cheapest state in the guard to leave.
The dirty snapshot judges only this checkout's own work. Untracked entries under
another fleet's worktree roots (`.claude/worktrees/`, `.claire/worktrees/`,
`.codex/worktrees/`, `.codex-worktrees/`) are excluded — a blocked session can neither commit another
session's checkout nor delete it without destroying live work — and a path that
LEAVES `git status`, whether committed or newly ignored, stops counting as
outstanding. Both stay fail-closed: tracked content under those roots gates
normally, and a tracked file the session deleted is still reported by git as
` D`, so it still blocks.
A genuine repeated external blocker must be reported as `SHIP LOOP BLOCKED:` with
concrete evidence; ordinary local cleanup, authentication setup, and waiting are not
blockers. A lawful hold reports `SHIP LOOP PARKED:` instead. The CI gate remains
base-side-aware: a red on the merged head that provably pre-existed on main (same check
failing on ≥2 independent concurrent PR heads pre-merge, or a green ci.yml run on a main
descendant) is excluded by name rather than pinning the session forever; the operator
lever for a healed base is `gh workflow run ci.yml --ref main` — one green dispatched
run clears every pinned merge at once, but preflight for an in-flight baseline first.
Unknown or lone-sibling evidence stays `ci_failed` (fail-closed).

An AUTHORITY-FROZEN merged head is no longer unclearable forever (2026-08-19,
DEC-AUTHORITY-FREEZE-CLEARS-ON-DESCENDANT-BASELINE). A merged head whose semantic
evidence records `authority_changed=true` (any edit in the CI-authority
inventory — `scripts/**`, `.github/ci/**`, `.github/workflows/**`,
`.claude/hooks/**`, top-level `*.py`, conftest/pyproject; see
`scripts/ci_authority_paths.py`) still may not use candidate-era semantic
evidence or descendant unit healing to excuse its red, but it clears through
exactly ONE lever: a completed ci.yml run concluding SUCCESS on a main
descendant of the merge — proof of main under the merged authority itself,
dispatched with the same preflight discipline as above. The scope is the freeze
ALONE: the artifact's only non-clear signals must be the freeze itself (the
emitter's `authority_self_excuse_refused` infrastructure row) with ZERO
classified blocking units — a `pr_regression`/`unknown` unit is the head's own
red and is never blanketed by a baseline. Infrastructure ambiguity stays
outside that path, an unanswerable probe keeps the freeze, and pending checks
still outrank the clearing. Operator-grant markers (labels, comments, grant
files) were evaluated and REJECTED as clearing evidence: the fleet
authenticates as one shared token, so any such marker is mintable by the
session itself — self-excuse by construction.

The PRE-merge path is base-side-aware too, and has to be: ordinary sessions stay through
their own merge, so that path runs on every Stop of every armed ordinary session. Before an
armed head's red is called this session's defect, the guard asks whether main's own newest
concluded `ci.yml`/`fences.yml` run is red on the same job NAME, and failing that whether
the same name is red on ≥2 independent concurrent sibling heads. If either answers, the
block is filed as `unmerged` naming MAIN as the cause and `gh workflow run ci.yml --ref main`
(with the in-flight preflight) as the lever — never "fix the cause and re-run", which is how
several sessions end up healing one pack in parallel, and two partial heals of one pack can
never both go green. A PARKED hold bypasses this polling path entirely until released.
Fail-closed in the safe direction throughout: a stale proof, a lone sibling, an undated red,
or any probe that raises excuses nothing and the red stays this session's, with the gap NAMED.

An IN-FLIGHT covering render DEFERS rather than blocks (operator ruling
2026-07-27): a queued or running render whose head covers this merge satisfies the
render gate and the session proceeds to the live check, because the VPS pulls main
every 3 minutes so the merge is live regardless, the shared lane owns the re-bake,
house law forbids a waiting session from cancelling or re-running it, and the
nightly `scope=all` re-render is the backstop. A render lane that NEVER started
(the dead-wire trap) or that concluded FAILED with no in-flight successor still
blocks. Every blocker also carries an escape ladder so an unsatisfiable gate can no
longer trap a session indefinitely: an EXTERNAL blocker escapes at 2 consecutive OR
3 cumulative external blocks; ANY code (including the internal ones —
unmerged/ci_failed_unmerged/unpushed/uncommitted/unsafe_branch/guard_error)
escapes at 10 consecutive OR 15 total blocks. `.claude/settings.json` sets `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP=15` so Claude's default ninth-block provider override cannot pre-empt that repository-owned ladder; this compatibility ceiling grants no earlier exit. Every escape still requires an explicit `SHIP LOOP BLOCKED:`
evidence report with `stop_hook_active` set, so a session cannot bail on the first
attempt. A ratified ladder exit is REMEMBERED for the exact frozen state it excused
(2026-08-19): once the full ladder has fired for a `ci_failed` merged-head block,
the key `ci_failed:<head>:<merge>:<sha256(reason)[:12]>` passes later Stops
without demanding the identical report again — one evidence report per frozen
state, not one per Stop. The reason digest is load-bearing: a rerun or late cron
that binds a DIFFERENT red to the same shas mints a different key and re-blocks.
A new merge gates fresh; internal codes and evolving states carry no key and are
unchanged.
<!-- Repository-root-relative paths and controls are unchanged by relocation. -->
