
## 2026-11-10 (~04:5xZ) — estate red trio root cause: ubuntu0-a runner umask

The boats ×11 / momoedge / selector-capture trio reding PR packs (incl. armed
#10914 at 0a21096→a0ccc18) is NOT any commit: momoedge asserts wrapper mode
0o755 but got 0o775 (assert 509==493); boats' read_regular rejects the same
group-write bit (st_mode & 0o022). Git cannot store group-write, so the mode
comes from checkout umask 0002 on the runner. Red pack-2 (job 129610727898)
ran on self-hosted runner ubuntu0-a; main's green 01:29Z pack (job
129565638573) ran GitHub-hosted; no workflows change in 4057f7f..main —
ubuntu0-a now carries the ubuntu-latest label and packs drift onto it.
Diagnosis posted: #10914 comments 6758492783, 6758514190, 6759309378.
ACTION (runner owner): umask 0022 on ubuntu0-a's runner service or drop its
ubuntu-latest label. Any head whose packs land there reds this exact trio —
charge to runner, not to PRs. My #10918 runs at b81d8d4 may carry the same
trio if they landed on ubuntu0-a; that is not my PR's defect.

Also: same-account GitHub-side merge of main into #10918's branch at
b81d8d4 (custody verified: PR content byte-preserved, flow-surface widening
intact; comment 6759230514). Local branch synced to it.

## 2026-11-11 (~02:2xZ) — C2 accepted, front-run merge, queue mechanics

State: #10918 at head 248edc48e869 (merge of origin/main e3244df-era into
1f9b1f0), armed, custody comment 6785165616. All PR-owned files byte-identical
through both main-merges (verified twice). Tests 23/23 aibrief + 120/120
first-frame at 68c5323. C2 duty acceptance defects fixed on original carrier:
(a) chip consumed raw refresh_days → normalized value now in `_freshness`
annotation; (b) `math.isfinite(10**309)` OverflowError → `_bad_refresh_days`
with OverflowError guard, bounds 0 < rd <= 7. Regressions:
test_oversized_json_int_refresh_days_degrades_not_aborts,
test_visible_cadence_consumes_the_normalized_value.

Chairman asked why a "simple fix" took so long — answered plain-words: the fix
was fast; time went to (1) five fence rounds catching real edge-case defects,
(2) estate CI reds for hours (ubuntu0-a umask + two base defects, all now
fixed/routed), (3) merge-queue congestion + stale-proof rule.

Queue mechanics learned (also saved to memory merge-controller-queue-mechanics):
sweep = 128 of ~225 armed PRs per pass, order rotates every 10 min; main commit
9d9aac1 changed check definitions → controller declares green proofs stale,
auto-merges main into heads, re-CI decides later. Front-run executed: #5291
cycle disarm→merge main→verify→push→rearm, so the deciding CI on 248edc4
started immediately instead of waiting a rotation turn.

Next (successor or wake): green on 248edc4 → controller merges (proof fresh:
9d9aac1 now ancestor) → post-merge live verification (fresh aibrief page +
freshness receipt on deployed site) → record integrated result on #983.
Deferred v2 vertical (separate PR, AFTER #10918 merges — it consumes the
_freshness contract): dashboard/china/hk loaders at build_site.py:4647,
build_china.py:2061, build_hk.py:1561 still pass raw unannotated copies.

## 2026-11-11 (~03:0xZ) — C2 QUALIFIED at 248edc4; quarantine remedied; branch note

C2 duty session (mastermindxryan, comment 6786566022): both corrupt-input
findings CLOSED at head 248edc48e869 — original 15-case discriminator 15/15
(predecessor b81d8d4 still 8F/7P, so the tests discriminate); +232 expanded
cases (126 invalid-cadence, 36 grace-boundary, 54 unannotated byte-preservation
+ overflow isolation). Custody explicitly retained by incumbent writer +
watcher. No repair owed.

Session-root quarantine remedied in-session: mint refused ("identity changed")
because the SSD dest sat on the PR branch, not the recorded
claude/ssd-t3-4f13be30-c4747f2c70fdfd15; fixed by branch -f <recorded>@248edc4
+ checkout, mint then idempotent-succeeded, EnterWorktree confirmed cwd already
the minted path. NOTE for successors: this tree's LOCAL branch is now
claude/ssd-t3-4f13be30-c4747f2c70fdfd15 at 248edc4 (same commit as PR head);
push with `git push origin HEAD:claude/aibrief-truthful-display-20261110`.

Remaining: CI green on 248edc4 (ci/fences already green per C2's hosted
observation; ci-plan/contract-delta were in flight) → controller merges (proof
fresh) → live verification → #983 readback.

## 2026-11-11 — custody: remote ssd branch carries #10902 liveness chain

`origin/claude/ssd-t3-4f13be30-c4747f2c70fdfd15` holds MastermindX1's #10902
liveness work (75a93e4 → 40cb159 → f1d7992 → 35ff3f4 → 162bba7 → 81a98ca →
0841b1b "Merge accepted main admin repairs into qualified liveness branch";
successor proof still pending on their side). NEVER force-push this remote
branch — the local ssd branch in this tree was deliberately repointed to the
aibrief PR head (248edc4) and its stale upstream unset. Ship-loop "unpushed
commits" counts vs that upstream were the artifact; substance: PR branch,
side ref and local head all agree and are pushed.

## 2026-11-11 (~04:2xZ) — ROOT CAUSE of the merge freeze: main baseline red (circuit breaker)

Dispatched the controller's own workflow_dispatch sweep (42958111536); its
verdict on #10918: "source main baseline is red; leaving it armed behind the
circuit breaker." NOT queue rotation, NOT lease starvation — main itself.

Census (comment 6786916452 on #10571, routed to the introducing carrier):
9d9aac1 (#10571 us_board ledger) added to
tests/test_ci_pack.py::test_sa_w4_scope_covers_active_registry_read_paths an
unguarded read of data/experiments/registry_seed.json (line ~5612), but the
integration-baseline job checks out a sparse cone omitting data/ by design.
1/1146 fails (FileNotFoundError); integration-baseline on main red since
01:52Z (green 917c15eb 01:47Z → red 9d9aac1b → red e3244df5 latest). The
breaker holds ALL armed PRs estate-wide (225 at last count). This is also the
true completion of the Chairman's "why so long" answer: since 01:52Z no PR
could merge at all.

Repair shapes offered: (a) materialize the one seed path in the baseline job
via scripts/worktree_sparse.py; (b) read the seed from the git blob
(checkout-independent, honors the test docstring "without opening their
targets"); (c) skip-guard (weakest). Only the seed file is READ; other data
paths are string-compared. Note: ci workflow passed on the same tree at
02:02Z — different checkout profile, so only integration-baseline trips.

Custody: routed per the CI-Lightning-owns-systemic-CI-reds law. #10571 now
watched (owner response wakes this session). If no owner starts the repair by
the next wake/Stop cycle, the no-worker-started invariant authorizes direct
bounded execution: PR choosing shape (b) — ~2 lines in tests/test_ci_pack.py,
blob-read helper, no job-config change, smallest blast radius; regression =
test passes in a data-omitted sparse cone.

#10918 state: armed, fully green since 02:40Z, proof fresh; merges
automatically once the breaker lifts (controller-owned). Watcher + #10571
watch own the wakes. Disarm/rearm cycle executed 04:1xZ (refresh event;
harmless). Sweep deferral evidence: window advancing (03:48 deferred from
#10738 → 04:06 from #10873 → #10918 evaluated in dispatched sweep).

## 2026-11-11 (~04:3xZ) — direct execution: PR #11000 baseline repair shipped

No owner started a repair after the routing, so per the no-worker-started
invariant this session executed the bounded fix directly. PR #11000
(claude/baseline-red-repair-seed-blob-20261111, off c13ee682):
test_sa_w4_scope_covers_active_registry_read_paths now reads
data/experiments/registry_seed.json via `git show HEAD:...` (blob) instead of
the working tree. Proof: failure reproduced in this sparse tree (data/ omitted
= the baseline condition) BEFORE; 22/22 sa_w4 pass AFTER. Labeled
`main-red-repair` + `merge-on-green` per the breaker's documented escape
(integration-baseline.yml header: "Only an explicitly labelled main-red-repair
PR may cross a red baseline, and it must still carry fully green PR checks";
tier-0 admits exactly ONE repair per sweep — scripts/merge_on_green.py:4482).
Custody handback offered on #10571 (comment 6787033473) — supersede-able, one
10-line hunk.

Chain from here (watcher-driven): #11000 checks green → tier-0 merge across
red baseline → integration-baseline re-runs on main (tests/** trigger) →
breaker lifts → #10918 (armed, green since 02:40Z, fresh proof) merges on a
following sweep → render/deploy → live aibrief verification → #983 readback.
Watches: #10918, #10571, #11000.

NOTE: this worktree's branch is claude/baseline-red-repair-seed-blob-20261111
(tracks origin/main) while the aibrief ssd branch sits at 248edc4. After
#11000 merges, checkout claude/ssd-t3-4f13be30-c4747f2c70fdfd15 back for
post-merge aibrief verification. Push for the repair branch is direct
(same-name remote); the ssd branch pushes as
HEAD:claude/aibrief-truthful-display-20261110.

## 2026-11-11 (~10:5xZ) — Chairman asked; front-run via GitHub-side update-branch

Chairman: "ai brief PR failed, diagnose and fix." Diagnosis: PR never failed a
real gate — the visible red X is the by-design merge-queue-pilot (fails on
EVERY PR; excluded from verdicts). Real chain: baseline freeze 01:52Z→04:54Z
(repaired by #11000, MERGED), then the stale-proof rule (main 9a2446a5 changed
check definitions during the freeze), then controller CI-workload slots
saturated (20 runs / cap 8) deferring its own update-branch.

Tactic change (cycle-3 no-delta law): instead of the slow local fetch (60 GB
store, negotiation-bound; still running in background as breh6jysk, non-critical),
executed the server-side update-branch — `gh api -X PUT
repos/.../pulls/10918/update-branch` → head 248edc4 → dc44092 (main merged,
PR-owned files byte-preserved via one compare call), CI started immediately.
#5291 cycle complete: disarm → update-branch → verify → rearm, custody comment
6792632421. When CI greens on dc44092, proof is fresh and the ordinary sweep
merges.

ALSO: 12h-stale zero-byte HEAD.lock (worktrees/t3-a29c64d9, another session's
dead fetch) was blocking shared ref transactions; verified no live holder,
removed per git's documented remedy, and killed my own hung fetch wrapper
(bcczbn2r3) first. Local tree still at 248edc4 until the background fetch
completes — SYNC NOTE: `git merge --ff-only` won't work (diverged by the
server-side merge); use `git reset --hard origin/claude/aibrief-truthful-display-20261110`
after fetch, or `git pull` if clean.

Next: watcher wake on green dc44092 → sweep merges → render/deploy → live
aibrief verification (fresh page + freshness receipt) → #983 readback.

## 2026-11-11 (~20:45Z) — #10918 MERGED; v2 PR #11075 open; time-bomb repaired

MERGED: PR #10918 at 2026-11-11T19:09:15Z, mergeCommit 19fa6c082174, zero
real failures (sole red = by-design pilot). Byte-verified: all four PR-owned
files identical c2e4936→origin/main tip (584b9dd3). The ship-loop hook's
"unmerged" verdict keys on the LOCAL branch name (claude/ssd-t3-…) whose
remote carries #10902's liveness chain — hence hook stayed red past the real
merge. Render auto-dispatched 4s post-merge (workflow render.yml, title
"aibrief: truthful freshness", scope incl. us_pages/build_aibrief), in
progress ~90m at last read; NEVER cancel; live aibrief + receipt readback
still owed for PRODUCTION_PROOF.

QUARANTINE INCIDENT + RECOVERY: a pipe-masked `git checkout -b` failure let
`git rebase origin/main` run on the session branch in the old SSD tree
(t3-4f13be30-c4747f2c70fdfd15) → mid-rebase detached HEAD → root quarantine
(guard allows only mint/worktree/fetch/branch/rev-parse/status; `git rebase
--abort` refused; EnterWorktree path-restricted to .claude/worktrees).
LAWFUL EXIT: `git worktree add ".claude/worktrees/t3-4f13be30-v2" -b
claude/aibrief-freshness-v2-main-20261111 origin/main` → EnterWorktree.
Session now works in that native tree. OLD TREE remains mid-rebase-detached
at 584b9dd3, locked, INERT — no uncommitted work was lost (tree was clean;
rebase never completed); reclaim it via the storage helper later, do NOT
hand-abort it from another session without checking state.

TIME BOMB ROOT-CAUSED + REPAIRED (commit 60e2b291f33b on the v2 branch):
test_main_writes_freshness_receipt_and_stale_page shipped static fixture
dates; the "fresh" macro fixture (2026-11-09T01:00Z) aged past cadence+grace
(1d+1d6h) at 2026-11-11T07:00Z → test fails on UNCHANGED code (reproduced on
bare main 584b9dd3; NOT in integration-baseline scope → no breaker risk, but
in every PR's ci-pack matrix). Fixtures now derived from datetime.now like
the code under test. 23/23 page suite + 105/105 consumer suite green.

V2 PR: cherry-picked builder's 72bf4e9 onto main (clean, 7 files +353/−9)
→ a46d3c73 + repair 60e2b291 → PR #11075 (head
claude/aibrief-freshness-v2-main-20261111), ARMED merge-on-green, watched.
Remote prep branch claude/aibrief-freshness-v2-20261111 (72bf4e9) is
vestigial (no PR ever opened; its local branch is locked in the builder's
worktree agent-aa1decd884fa5efe0).

REMAINING: render completes → live aibrief freshness display + receipt
readback → Mastermind #983 integrated readback (one comment, MERGED +
PRODUCTION_PROOF together) → unwatch #10918 on handback. #11075 merges via
controller when green; its post-merge live chip verification follows the
same render path.
