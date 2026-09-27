# Worktree GC policy — fleet session-checkout sweeper

**Status: PROPOSED — awaiting operator ratification. Nothing has been deleted.**
Tool: `scripts/worktree_gc.py` (shipped disarmed: `config/worktree_gc.json` → `"armed": false`).

## §0 Ratification box (operator decisions)

| # | Decision | Default shipped | Operator act | Measured effect today |
|---|---|---|---|---|
| R1 | Arm deletion of `SAFE_MERGED` + `SAFE_REMOTE` and set `min_age_days` — **recommend 2** (3 = conservative, 7 = insurance-only) | disarmed, 7 d | flip `"armed": true` + set `"min_age_days"` in `config/worktree_gc.json` (one-line PR) | at 2 d: **51.3 GiB** now + caps the leak tail forever; at 7 d: ~0 today (nothing unpinned survives 7 d — see §5) |
| R2 | Install the daily launchd sweeper on the Studio | not installed | `bash scripts/install_worktree_gc_launchd.sh` on the Studio | keeps the tail drained daily |
| R3 | Same for the M1 host when it returns (unreachable at audit time, runners offline) | not installed | same installer over ssh; feed `--pr-states-file` if gh is unauthenticated there | unknown until reachable |
| R4 | Reclaim `ORPHAN` husks (unregistered dirs under the roots) | off | `"include_orphans": true` | ~0 GiB (4 empty husks) |
| R5 | Reclaim clean+pushed worktrees of OPEN PRs (branch/PR survive; only the local checkout goes) | off | `"include_open_pr": true` | small; open lanes are mostly RECENT anyway |
| R6 | charting-app: same sweep for its 103 GiB `.claude/worktrees` | report-only | arm a `config/worktree_gc.json` there (tool takes `--repo-root`) | **9.6 GiB** at 7 d already (16 trees); more at 2 d |
| R7 | Session-closing hygiene: **24 open sessions / 78.1 GiB** have their PR already squash-merged at the worktree head but stay pinned by their processes. Closing finished sessions releases them to the sweeper (all 62 pinned trees are < 2 d strong-active, so this is workflow, not archaeology) | keep all pinned | close finished sessions in FleetView as a habit | ~78 GiB now; keeps the done-pool draining |
| R8 | Structural: each checkout is 3.27 GiB, of which `data/` 2.10 + `site/` 0.67 = **85 %**. The ~0–2 d active window (~330 GiB at the measured ~40 sessions/day cadence) is a capacity requirement GC cannot reduce — a sparse-checkout session profile could cut it ~5×. **SHIPPED 2026-08-13** (operator-ratified during the disk-pressure incident) | sparse by default | `config/sparse_worktree.json` → `"enabled": false` reverts to full checkouts | ~7–11× per tree; see §8 |

First armed run on the Studio: suggest `--apply --dry-run` once, eyeball the log, then `--apply`.
`max_delete_per_run: 200` caps a single pass; the daily schedule drains any remainder.

## 1. The problem (measured 2026-08-05, Studio)

Disk at **96 %** (1.7 Ti / 1.8 Ti, 89 Gi free). The fleet worktree roots hold:

| Root | Entries | Size |
|---|---:|---:|
| Macro `.claude/worktrees/` | 186 dirs (217 registrations repo-wide) | **597.5 GiB** |
| Macro `.codex-worktrees/` | 13 | 37.0 GiB |
| `~/.codex/worktrees/` (legacy home root) | 14 | 34.4 GiB |
| Macro `.claire/worktrees/` | 3 husks | ~0 |
| charting-app `.claude/worktrees/` | 130 | 103.3 GiB |
| **Fleet sprawl total** | | **≈ 772 GiB** |

**Corrected model (what the audit actually found):** this is *not* months of quiet
accumulation. The harness already recycles most closed sessions (at the measured
cadence of ~40 session worktrees/day, two months of pure leakage would be ~2,400
trees — only 186 exist). The pile decomposes into three different problems:

1. **The active window** — ~132 unpinned trees / ~417 GiB with strong activity
   < 3 d, plus 62 process-pinned trees / 203 GiB that are ALL < 2 d strong-active
   too (49 carry a live `claude` process). Fleet cadence × 3.27 GiB per checkout.
   GC cannot shrink the genuinely-working part; only R8 can.
2. **The done-but-still-here pool** — sessions whose PR is already squash-merged
   at exactly the worktree head: **64 idle trees / 201.4 GiB** (aging toward the
   min_age bar; 17 / 51.3 GiB past 2 d today) plus **24 still-open trees /
   78.1 GiB** whose processes pin them until the session is closed (→ R7).
   This ~280 GiB pool is what the sweeper + session hygiene continuously drain.
3. **The leak tail** — 4 DIRTY trees / 8.7 GiB idle 7–60 d holding uncommitted
   files (operator-review pile, listed in the report; never auto-deleted).

A typical checkout is 3.27 GiB: `data/` 2.10 + `site/` 0.67 (85 %) + code.
The M1 runner host (mac-builder-1/2/3) hit **ENOSPC 2026-08-04**, killing the
runner Worker mid-collect (run 30960328285) and severing the nightly collection
lane; it likely carries its own mix of the same three piles plus runner `_work`
churn. As of this audit the M1 is unreachable over ssh (Tailscale timeout) and
its three runners are offline; Studio spares mac-builder-4/5 are online carrying
the load.

## 2. Safety model (what "provably safe to remove" means)

Deleting a worktree directory can lose exactly two things: **uncommitted files** and
**commits reachable only from its local branch**. The branch ref itself lives in the
shared `.git` and is deleted only under its own proof. So a worktree is safe iff it is
**not in use** and **holds no unique content**:

**Liveness (all must clear):**
- No `git worktree lock` (sessions annotate locks with pid — honored unconditionally).
- No process with cwd inside (one global `lsof -d cwd` pass; never per-tree `+D` descents over 600 GiB).
- No STRONG activity within `min_age_days` (7 d). Strong = the last reflog **entry's embedded
  epoch** (real HEAD movement) and the harness session dir `~/.claude/projects/<path-slug>/`
  newest mtime. File mtimes are recorded but never gate — the audit caught two systematic
  stampers that would otherwise hold the gate shut forever: a repo-global `reflog expire`
  rewrote all 186 trees' `logs/HEAD` at 2026-08-04 15:38:24 (every dead tree read "0.2 d
  old"), and observer sweeps (`git status` from dashboards writes the index; Finder drops
  `.DS_Store`) kept 137/143 dead trees under 2 d by index/HEAD/dir mtimes while their
  reflog entries and transcripts sat weeks old. House law is same-day merge; 7 d without
  ref movement or transcript writes is dead by a wide margin — and the content proofs
  below, not the age gate, are the actual loss-prevention layer.

**Content (any one proof suffices):**
- `HEAD` is an **ancestor of `origin/main`** — nothing unique by construction; or
- a **MERGED PR exists whose `headRefOid` equals `HEAD` exactly** — squash-merge proof.
  Ancestry cannot see squashes and `delete_branch_on_merge=true` erases the remote branch,
  so PR state (via `gh pr list`, 3 quota-cheap calls) is the only sound proof here.
  Oid-exact matching means a head that moved past the merged commit stays kept; or
- `HEAD` is **contained in a still-existing origin branch** and **no PR is open** for it
  (`SAFE_REMOTE`: the checkout is a cache; content survives on the remote).

**Fail-closed everywhere:** any probe error/timeout, unreadable config, missing PR data,
stale remote refs after a failed `git fetch --prune`, or an unavailable lsof scan ⇒ KEEP
(and apply mode refuses outright without liveness data). Verdicts for kept trees:
`LOCKED / LIVE_PROC / RECENT / DIRTY / OPEN_PR / UNPUSHED / ERROR / ORPHAN`.

**Never candidates:** the primary checkout, the sweeper's own cwd, anything outside the
configured roots (`~/hub-ops-wt`, `/private/tmp` scratch registrations are out of scope;
dead registrations get `git worktree prune`d, which is metadata-only).

## 3. Mechanism

`git worktree remove --force` from the primary root (our proofs are stricter than git's;
`--force` only clears gitignored build junk objections), then one `git worktree prune`.
Local branch `git branch -D` **only** when the merge proof held and the branch tip still
equals the proven head. `ORPHAN` husks (dir without registration — git cannot status them)
use `rm -rf` and are **off by default** (R4). Every deletion appends a JSONL row
(path/branch/head/size/verdict/proof) to `~/Library/Logs/macro_worktree_gc/ledger.jsonl`.

## 4. Scheduling: launchd per host, not a repo workflow

The failure mode this tool exists for — disk full — **takes the host's own runners
offline** (that is how the M1 died), so a runner-scheduled workflow can never save the
host that needs it. GitHub cron also delivers ~15 % of slots in this repo. Hence
per-host launchd (`scripts/worktree_gc.launchd.plist` via the installer, daily 05:17
local, `Nice 15`, logs under `~/Library/Logs/macro_worktree_gc/`). Installing before R1
is safe: apply self-gates to report-only while disarmed. `scripts/metabolism_gc.py`
(wf_* autonomy-loop trees, journal-based proofs) stays as is — different scope; its
inverted ancestry check is flagged separately.

## 5. Measured classification & reclaim estimate (Studio, 2026-08-05)

Receipts: `research/worktree_gc/2026-08-05_studio_*.{md,json}` (full per-tree verdicts).

**Macro root** (186 trees + husks; shipped default min_age 7 d; verdicts stable across
three audit passes):

| verdict | count | GiB | note |
|---|---:|---:|---|
| RECENT | 143 | 450.6 | strong activity < 7 d (histogram below) |
| LIVE_PROC | 62 | 203.0 | all < 2 d strong-active; 49 with live `claude` proc |
| DIRTY | 4 | 8.7 | idle 7–60 d, uncommitted files — operator-review pile |
| LOCKED | 1 | 3.3 | `x-growth-overhaul`, session lock honored |
| ORPHAN / SELF / MISSING | 4 / 1 / 1 | ~0 | husks; metadata prune only |
| **SAFE now (7 d)** | **0** | **0.0** | nothing unpinned survives 7 d — see below |

Strong-age histogram of unpinned trees (count / GiB): <1 d 36/117 · 1–2 d 68/215 ·
2–3 d 28/85 · 3–5 d 7/22 · 5–7 d 4/12 · ≥7 d 4/8.7 (the DIRTY pile).

**Why 7 d reclaims zero here and why that is not failure:** the harness already
recycles most closed sessions; what remains is the live fleet plus the done-pool.
The done-pool is real and measured — **64 idle trees / 201.4 GiB are oid-exact
squash-merged** (of which 17 / **51.3 GiB** already ≥ 2 d idle) and **24 pinned
trees / 78.1 GiB** more are merged but still open. R1 at min_age 2 d harvests the
idle half continuously; R7 releases the pinned half.

**charting-app root** (130 trees, min_age 7 d): SAFE_MERGED 14 + SAFE_REMOTE 2 =
**9.6 GiB reclaimable immediately**; RECENT 93 / 76.6 GiB; DIRTY 19 / 9.7 GiB;
UNPUSHED 14 / 7.1 GiB; LIVE_PROC 4. A smaller, older fleet → a genuine dead tail;
validates every verdict class on a second repo.

**Detector integrity (why the first two audit passes were discarded):** pass 1
read all trees "0.2 d old" — a repo-global `reflog expire` had stamped every
`logs/HEAD` file at 2026-08-04 15:38:24; pass 2 still read 137/143 "fresh" off
index/HEAD/dir file mtimes written by observer sweeps (`git status` from
dashboards, Finder `.DS_Store`). Both stampers are now regression-pinned in
`tests/test_worktree_gc.py`; the shipped probe gates on reflog ENTRY epochs +
session transcript mtimes only.

## 6. M1 plan (R3)

When reachable: `scp scripts/worktree_gc.py m1:` and run `--report --repo-root <primary>`
with `--pr-states-file pr_states_macro.json` (map emitted on the Studio) if `gh` is not
authenticated there — offline hosts consume Studio-fetched PR proofs; a failed fetch
marks remote refs stale and `SAFE_REMOTE` fails closed, but merged-PR and
ancestor-of-last-known-main proofs (both under-approve, never over-approve) still land.
If its disk is still wedged at 100 %, the report run needs no free space to speak of;
present its numbers, then arm.

## 7. Explicitly out of scope (v1)

- `git gc` / repack of the shared 29 GiB `.git` (concurrent-session risk; separate ask).
- Runner `_work` directories (bounded per-workflow reuse; separate lever).
- Killing processes that pin `LIVE_PROC` trees — the sweeper only reports them (R7 is
  operator hygiene; a rule change would be its own ratified PR).
- Shrinking the active window — a capacity question, not GC. Shipped separately as the
  sparse session profile (§8), which is the only lever that reaches the active window.
- Steady state with R1 armed at 2 d ≈ active window (~330 GiB) + parked pile until R7
  acted on. The tail no longer grows; the window tracks fleet cadence.

## §8. Sparse session-worktree profile (R8 — shipped 2026-08-13)

Operator-ratified during the same disk-pressure incident that armed the sweeper.
GC reclaims FINISHED trees; this shrinks LIVE ones, which is why both were needed.

**Claude mechanism.** `.claude/hooks/worktree_create_sparse.py` runs on the
harness's `WorktreeCreate` event, wired in the checked-in
`.claude/settings.json`. It fetches
`origin/main`, adds the worktree `--no-checkout`, sets a cone-mode sparse profile
holding every tracked top-level directory except those in
`config/sparse_worktree.json`, then `read-tree -mu HEAD` to populate it. A name of
the form `pr-<N>` bases the tree on that PR's head instead. It replaces an
unversioned zsh prototype that lived in `~/.local/bin` and was wired through
`.claude/settings.local.json` — globally gitignored, so the behaviour existed on one
host but could never ship, be reviewed, or be tested.

**Codex mechanism (shipped 2026-08-15).** The default local environment at
`.codex/environments/environment.toml` runs `python3
scripts/worktree_sparse.py auto` when Codex creates a worktree. The checked-in
`.codex/hooks.json` `SessionStart` hook is the fallback when no environment was
selected. `auto` refuses the primary checkout, honors the same profile and off
switch, and preserves any existing sparse selection so a session's explicit
`add site` is not undone. Codex requires one-time trust for a new or changed
project-local hook definition. Current Codex lifecycle events are post-checkout,
not a pre-checkout replacement for Claude's `WorktreeCreate`: the steady-state
tree reaches the same 0.35–0.57 GiB, while initial creation may transiently write
the full checkout before the setup removes the excluded paths.

**Cursor IDE mechanism (shipped 2026-08-15).** Cursor has no pre-checkout
`WorktreeCreate`. `.cursor/hooks.json` runs `python3 scripts/worktree_sparse.py
auto` on `sessionStart` and `workspaceOpen`. `auto` converts only a linked
worktree under a session root (`.claude/worktrees/` and siblings). That extra
path check exists because the operator's designated local project root is
itself a linked worktree of the occupied primary — a SessionStart hook keyed
only on `git-dir != common-dir` would sparsify that 3.8 GiB tree on every
Cursor chat.

**Cursor CLI + Grok mechanism (shipped 2026-08-15; AionUi mint 2026-08-18).**
Cursor CLI / Agents Window runs `.cursor/worktrees.json` `setup-worktree-unix`
after it creates the worktree. Grok Build runs
`.grok/hooks/session_start_sparse.py` on `SessionStart` (unknown Claude events
such as `WorktreeCreate` are skipped). When the session already sits in a
linked session worktree the hook calls `python3 scripts/worktree_sparse.py
auto`, sharing the post-checkout thinning, session-root refusal, and "do not
re-apply over an existing sparse selection" rule. AionUi launches Grok in an
empty `~/.aionui/conversations/.../grok-temp-*` directory that is not a git
worktree, so the project hook never loads; the always-trusted
`~/.grok/hooks/` copy of the same script mints a sparse tree under
`.grok/worktrees/<name>/` with `git worktree add --no-checkout` (Claude's
pre-checkout shape) and writes `.session-worktree` in the temp dir. Grok
project hooks still need one-time `/hooks-trust`. `--worktree` / `-w` still
bases on current HEAD unless the session passes `--ref origin/main` (Grok) or
`--worktree-base origin/main` (Cursor).

**Warp/Oz mechanism (shipped 2026-08-22).** Warp has no SessionStart or
`WorktreeCreate` event. `.warp/hooks/session_start_sparse.py` is the mint;
`.agents/skills/macro-sparse-worktree` is how a Warp session discovers it and
must run it before editing. If the session already sits in a linked session
worktree the hook calls `python3 scripts/worktree_sparse.py auto`. Otherwise it
mints under `.warp/worktrees/<name>/` with `git worktree add --no-checkout`
(Claude's pre-checkout shape) and prints `WORKSPACE=<path>`. It never sparsifies
the occupied primary or the operator local root, and it never writes
`.session-worktree` into a git checkout.

**Host migration (one operator step, AFTER this merges).** The Studio's legacy wiring
was deliberately left alone by the shipping session: repointing it before the merge
would have aimed it at a script not yet on `main` and broken worktree creation for
the whole fleet. Once merged, remove the `WorktreeCreate` block from
`/Users/chriswong/Documents/Cluade/Macro Dashboard/.claude/settings.local.json` (and
delete `~/.local/bin/claude-macro-sparse-worktree-create.zsh`) so the checked-in
wiring is the only one. Until that is done both may fire; the Python hook is
idempotent — an existing destination that is already a registered worktree is
reported as success — but the older zsh prototype is not, and it exits non-zero on a
destination that already exists, so leaving both wired indefinitely risks a failed
spawn depending on which runs second.

**Measured 2026-08-13 (Studio).** Full session worktree **3.8 GiB**: `data/` 2.3 +
`site/` 0.73 + `mockups/` 0.23 + `verify_shots/` 0.05 = 3.31 GiB (**87 %**). Sparse
tree **0.35–0.57 GiB** — an ~7–11× cut, better than R8's ~5× estimate because
`mockups/`+`verify_shots/` join R8's two named dirs (same class: committed rendered
artifacts and screenshot evidence, not code). At ~40 new trees/day the standing
active window drops from ~330 GiB toward ~30–50 GiB as trees turn over.

**Escape hatches.** `python3 scripts/worktree_sparse.py full` opts one worktree into
a full checkout (worktree-scoped — `core.sparseCheckout` lives in `config.worktree`,
so siblings are untouched); `… add <dir>` materialises one tree; `… status` reports
state and any stray files a local tool wrote into an omitted tree. Repo-wide revert
is `"enabled": false` in `config/sparse_worktree.json`; it disables both Claude
creation and Codex automatic conversion.

**Honesty properties (the reason this is more than a setup script).** A sparse tree
must never make a guard or test pass for the wrong reason:

- `scripts/check_template_site_sync.py` enumerates its own pair list by walking
  `site/`. Absent `site/`, it printed `sync OK (0 pairs checked)` and exited 0 — a
  vacuous pass on the law protecting the render lanes (`render.yml` carries a long
  comment about the same failure mode reaching the lane: "would render, guard and
  COMMIT whatever subset of the tree it found — a truncated publish, not a red X").
  It now REFUSES and names the opt-in command.
- pytest prints the omitted trees plus that command in its header and in the summary
  of any failing run, skips only tests explicitly marked `needs_full_checkout`, and
  annotates other failures whose traceback names an omitted tree — a wrong answer
  stays red, it just stops being a mystery. Verified visible under `-q`,
  `-q --tb=short`, `-q --tb=line` and the house `-q --tb=no -rf` (where the header and
  the per-failure sections are both suppressed and the terminal-summary NOTE is the
  one that lands — which is why that hook exists alongside the header).
  **DO NOT run the full suite in a sparse worktree.** Measured 2026-08-13: it produces
  **1,281 failures + 419 errors across 247 distinct test files** (against 68,776
  passes) purely as artifacts of the missing trees. Marking those 247 files
  `needs_full_checkout` was considered and REJECTED — it would be an unmaintainable
  diff that permanently masks real regressions in a tenth of the suite. The marker
  stays available for surgical use; the honest instruction is to opt into a full
  checkout first, which is also what every CI lane running the suite already has.
  Nine of those files read an omitted tree at MODULE level and therefore die during
  COLLECTION, before any marker can apply — the terminal-summary NOTE still fires on a
  collection error, which is why the notice is wired to the summary and not only to
  per-test reporting. `tests/test_ship_loop_guard.py::test_the_pair_list_is_the_ci_gate_s_own_enumeration`
  is the one test marked here: it asserts its pair list is non-empty and builds it by
  walking `site/`, so unmarked it fails with a bare `assert set()`.
- **THE ANNOTATOR CANNOT SEE A *SWALLOWED* FileNotFoundError (found 2026-08-19).**
  The bullet above promises a wrong answer "stays red, it just stops being a
  mystery" — but attribution is by name match against the omitted trees in the
  TRACEBACK, so it only fires when the error propagates. Production code that
  catches the missing-reference error ON PURPOSE defeats it completely.
  `hk_board_rank.confirmation_move()` is the worked example: it derives the HK
  vetoed/ran lanes' confirmation close through
  `signal_quality.confirmation_date(..., market="HK")`, which anchors on the
  committed `data/hk/_HSI.parquet`, and it narrowly catches that FileNotFoundError
  because a missing reference is its documented **disclosed-null** case, not a crash
  the nightly should take. That contract is correct and unchanged. Its side effect in
  a sparse tree is that every vetoed row comes back `pct_since: null`, no traceback
  ever names `data/`, no NOTE is attributed — and the HK board pair prints
  **18 clean assertion failures that read exactly like engine-vs-fixture drift**
  (`tests/test_hk_board_ui.py` 5, `tests/test_hk_board_rank.py` 13). Measured on
  origin/main f69f224c9723: 18 failed sparse; `git sparse-checkout add data/hk` on
  the same bytes and nothing else, 0 failed. A session was commissioned to heal them
  as deterministic main reds while main's own ci.yml ran green — the cost this
  records. All eighteen now carry `needs_full_checkout("data")`: this is the
  surgical use the paragraph above reserves, not a retreat from it, and the
  distinguishing test is whether the annotator CAN fire. Where a traceback names the
  omitted tree, leave it red and opt into a full checkout; where production swallows
  the error, the failure is unattributable and marking is the only honest signal.

- Detection reads git's sparse state, never `Path.is_dir()`: `data/` survives
  `git reset --hard` as a **0-byte husk**, so presence checks report it materialised
  while it holds none of its 2.3 GiB. `scripts/worktree_sparse.missing_dirs()` is the
  single detector all callers share.
- A write into an omitted tracked path still reaches `git status` (verified in
  `tests/test_sparse_worktree_profile.py`), so `ship_loop_guard.py`'s dirty snapshot
  keeps working and nothing becomes silently committable.

**VACUOUS-PASS RETROFIT — the seven affirmative-OK guards now REFUSE (fixed 2026-08-13).**
21 `scripts/check_*.py` read `site/` or `data/`. Run in a sparse tree, **12 exit 0**,
and seven of those printed an affirmative OK over an empty set rather than failing.
All seven now refuse instead; the table records what each one used to print, which is
what a regression here would look like again:

| guard | what it printed with the tree absent (now refuses) |
|---|---|
| `check_site_js` | `OK — all standalone JS bundles under site/ parse cleanly` |
| `check_nav_gap` | `OK — every menu page under site/ keeps a ≥14px top gap` |
| `check_nav_mega` | `OK — every shared-nav page under site/ carries the Research mega-menu` |
| `check_badge_passport` | `OK: site dir <abs>/site absent (nothing rendered yet)` — and, over a husk `site/`, `OK: every desk brief carries a passport (0 checked, 0 grandfathered)`; it has TWO vacuous paths and both now refuse |
| `check_cycle_consistency` | `PASS — 0 same-tape group(s) agree` |
| `check_ms_board_coherence` | `ms-board coherence: OK (0 page(s) scanned)` |
| `check_ohlc_basis_coherence` | `no breadth panel carries the ... triple — nothing to check` |

The other nine fail loudly (FileNotFoundError and friends), which was already honest.
`check_template_site_sync` was fixed first, because it is the one the paired plain-copy
asset law depends on; it refuses unconditionally, which is safe only because its callers
were verified to be full checkouts. **A blanket entry-refusal is NOT safe as a sweep**:
several CI lanes check out partial trees on purpose, so a guard that refused whenever
`site/` is not fully present would red a lane working exactly as designed. So the seven
above take the other form — per-guard and **conditional on an EMPTY result set**:

> refuse only when *I checked ZERO items* **AND** *a tree I read is sparse-omitted*.

Both halves are load-bearing. Zero items in a FULL checkout is an honest zero and still
passes; a run that found real items in a partial tree still passes. `scripts/sparse_guard.py`
owns that conjunction (`refuse_if_vacuous`), deriving the trees it needs from the path the
guard was actually pointed at — so a guard aimed at a `tmp_path` stays inert — and
answering `None` on every detector failure, because the detector may never be the thing
that breaks a guard. `tests/test_sparse_guard_refusals.py` pins all seven against a
synthetic repo sparsed with real cone-mode `git sparse-checkout`, and covers both
negative cases so the conditional can never silently become a blanket one.

Callers were audited before the retrofit: **all seven guards are invoked only from full
checkouts** (`ci-pack` in `ci.yml`, `pages.yml`, `ci-main-heartbeat.yml`, and the render
family — `render.yml`, `engine-render.yml`, `earlyclose.yml`, `closing-bell.yml`,
`asia-close.yml`, `daily.yml`, `public-render.yml`). The 13 workflows that DO take a
partial tree — `live-quotes.yml`, `marketing-press-wire.yml`, `marketing-hot-tape.yml`,
`marketing-earnings-wire.yml`, `marketing-x-intel.yml`, `earnings-story-packets.yml`,
`earnings-story-press-stage.yml`, `earnings-evidence-graph.yml`, `company-intelligence.yml`,
`prophet-live.yml`, `key-pool-probe.yml`, `merge-on-green.yml`,
`daily-engine-setup-retry.yml` — invoke none of them.

Standing rule regardless: **a green from a `site/`/`data/` guard in a sparse worktree
means nothing** — run them after `python3 scripts/worktree_sparse.py full`, which is also
what CI does.

## §9. Only a POSITIVE completion signal authorizes reclaim (R9 — incident 2026-09-26)

`DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`.

**The law.** Absence of a signal — an idle window, no process holding a cwd, a stale
reflog — may NEVER authorize a destructive act on a shared worktree. Only a positive
completion signal may.

> ### CORRECTION 2026-09-27 — the signal is the MERGED PR, not `HEAD ⊆ origin/main`
>
> As first written, this section named **`HEAD` an ancestor of `origin/main`** as *the*
> canonical signal. **That test is wrong for this repository and is corrected in place
> here rather than superseded elsewhere.** This repo squash-merges every PR, and a squash
> REWRITES the commit — so the branch tip of a cleanly merged PR is *not* an ancestor of
> main. Measured on PR #8086: its squash commit `f9425697` IS an ancestor of
> `origin/main` (`merge-base --is-ancestor` exit 0) while its branch tip `0a47bc1f` is NOT
> (exit 1). An ancestry-only gate therefore fires for almost nothing except trees that
> never committed at all, and it silently misfiles finished work as abandoned.
>
> **The corrected signal, in the order `scripts/worktree_gc.py` already applies it** — that
> tool was right before this section was written, and this correction brings the prose back
> in line with the code rather than the reverse:
>
> 1. `HEAD` an ancestor of `origin/main` (fast-forward / sits on main), **or**
> 2. **a MERGED PR whose `headRefOid` equals this tree's `HEAD`** — the load-bearing case,
>    and the one the original text omitted, **or**
> 3. `HEAD` contained in `refs/remotes/origin/<branch>` with no open PR (pushed-and-safe).
>
> Unknown PR state fails CLOSED. The PRINCIPLE — only a positive signal, never an absence —
> is unchanged and was never in doubt; only its implementation was wrong.
>
> **A detached HEAD can satisfy none of the three.** It has no branch, so it can carry no
> PR and be contained in no remote ref, so this law structurally cannot reach it — see
> "What this law cannot reach" below. That is a real gap, not a conservative default.

**What it cost to learn.** On 2026-09-26 at 05:31 a host-local sparse sweep converted 59
FULL worktrees, stripping `data/`, `site/`, `mockups/`, `verify_shots/` off disk on an
"idle ≥ 24 h" gate. 34 were under the ungoverned mint root `/Volumes/Mastermind/worktrees/`
— 12 named `sol-*`, 13 `review-*`/`pr*`. Essentially every ChatGPT-web session died in the
early AM and most were unrecoverable: a web session hits a path that is suddenly absent,
cannot diagnose it, wedges, and errors cascade. No commits were lost — omitted paths stay
tracked in the index (verified: 62,071 `data/` + 19,511 `site/` + 6,573 `mockups/` + 445
`verify_shots/` files still tracked, `git status` clean) — but the SESSIONS were, and those
are the more expensive asset.

**Why the obvious fix is the wrong one.** "Use 72 h instead" preserves the defect and only
lowers its firing rate. Idleness means two incompatible things and a sweeper cannot tell
them apart:

| Session kind | Shell between tool calls | What 24 h of silence means |
|---|---|---|
| Claude Code / Codex / fabric lane | exits | genuinely dead |
| **ChatGPT web conversation (Sol reviews)** | **no shell at all; resumes when its human replies** | **nothing whatsoever — no threshold is safe** |

**Why the positive signal is also cheaper.** It arrives for free the moment a PR
squash-merges. It needs no TTL, no polling and no `du`. And it collapses a step: a landed tree needs **no `refs/salvage/*` ref at
all** — `origin/main` already references its commits, so durability is automatic rather
than purchased (contrast §"salvage" for DETACHED trees, which remains necessary there).

**THE SIGNAL PROTECTS THE WORK, NOT THE SESSION.** This is the correction that matters
most, because getting it wrong reproduces the incident in a new form. "Landed" proves the
BYTES are reproducible; it says nothing about whether someone is standing in the directory.
Deleting a checkout destroys the working directory of anything attached to it exactly as
thinning it did. So reclaim requires landed **and** nothing attached — and since a
resumable web conversation is undetectable by construction (no process, no shell, no
reflog: it lives in a browser tab), **roots that host web sessions must never be
auto-reclaimed at all.** A live-process scan is there to REFUSE, never to grant.

**Three enforcement points; none asks "is anyone still there".**

1. **At birth — cheap by default.** Measured 2026-09-26: **359 of 380 trees born in 7 days
   were already sparse (93%)**, ~0.45 GiB vs ~7.5 GiB full. The `WorktreeCreate` /
   `SessionStart` hooks (§8) do this. The ChatGPT-web path drives raw shell and has no hook
   surface — do not chase it with instructions; let point 2 absorb it.
2. **At merge — reclaim the landed checkout.** Gate: any one of the three proofs in the
   CORRECTION box above (ancestry **or** merged-PR-at-exact-head **or** pushed-with-no-open-PR)
   **and** `git status --porcelain` empty **and** nothing attached. This is the only
   mechanism that produces real outflow. It is also useless unless the tree sits under a
   configured root — see "Why the armed sweeper freed almost nothing" below.
3. **At a ceiling — a hard per-root population cap**, evicting landed-and-clean trees
   oldest-first. This is what converts unbounded growth into a bounded steady state, and it
   is the pattern GitHub enforces for Codespaces (org-level retention period + maximum idle
   timeout) precisely because per-user discipline does not hold at fleet scale.

**Sparsification is a one-time backlog drain, not a lever.** Re-measured with the corrected
gate: **0.0 GiB** reclaimable across the 27 remaining FULL trees (20 carry local changes, 5
are unlanded, 1 active, 1 in a web-session root). The reckless version looked valuable only
because it was counting trees it had no right to touch.

**Measured pool — RE-DERIVED 2026-09-27 (807 trees), correcting the 2026-09-26 census.**
The first census applied the ancestry-only gate and reported **638 UNLANDED / "79% of
worktrees never land their work", concluding that the bloat is unmerged WORK rather than
uncollected garbage and that no sweeper could ever reach it. THAT CONCLUSION WAS WRONG**,
and wrong in the direction that makes the problem look unfixable. Re-derived with PR state
instead of SHA ancestry:

| class | trees | what it actually is |
|---|---|---|
| **Detached HEAD — no branch at all** | **318** | cannot ship by construction; never meant to |
| Open PR right now | 107 | in flight, correctly not landed |
| **Merged PR** | **69** | landed — the ancestry gate misfiled these |
| Closed PR | 7 | genuinely abandoned |
| **No PR, inside the decidable window** | **60** | genuinely did work and never shipped |
| No PR, older than 2026-09-10 | 43 | UNDECIDABLE — see the two horizons below |
| Zero commits ahead of main | 154 | tree minted, nothing ever committed |
| Squash detected by commit-subject match | 47 | landed |

**Real abandonment is 60 confirmed — 67–110 counting the closed and the undecidable — i.e.
8–14%, not 79%.** The fleet ships roughly **61 PRs/day against ~54 trees/day minted**: it
*is* finishing. Nothing removes the tree afterward. It is uncollected garbage after all, and
a completion-signal sweeper is exactly the right instrument.

**Two measurement horizons, both of which bias toward calling work abandoned.** Quote
neither number without them: the clone is **shallow at 2026-08-21**, so a squash that landed
before that date cannot be matched by commit subject (10 of 604 affected); and a bulk
`gh pr list --limit 1000` reaches only back to **PR #7046, 2026-09-10**, so a branch whose PR
predates that window reads as "no PR" when it may well have merged (43 trees). Both push the
count of "never shipped" UP, which is the safe direction for a storage policy and the unsafe
direction for a claim about how the fleet behaves.

**Why the armed sweeper freed almost nothing — the actual root cause.** `config/worktree_gc.json`
has been `armed: true` since 2026-08-13 and its logic was already correct. It nevertheless
freed **1.5 GiB out of a 308 GiB population**, and the reason is scope, not judgment:
**580 of 807 registered trees (72%) sit OUTSIDE the configured `roots`**, and
`scripts/worktree_gc.py` line ~682 refuses any target "outside configured roots". The tool
classifies every registered tree (it reads `git worktree list` regardless of the list), so a
correct `SAFE_MERGED` verdict is reached and then cannot be acted on — the config's own
`_comment` predicted exactly this failure mode. The two absent roots:

| root absent from `roots` | trees | note |
|---|---|---|
| `/Volumes/Mastermind/agent-workspaces` | **354** | **mandated** by the global SSD worktree-placement policy; `…/claude` alone measures **462 GiB** |
| `/Volumes/Mastermind/worktrees` | **142** | the ungoverned mint root; hosts the web/Sol review trees |

**The placement policy moved to the external SSD and the GC's scope never followed.** Adding
those roots widens an armed deleter from 227 to 807 trees and is therefore an OPERATOR
ratification act in its own right, exactly like flipping `armed` was — it must not be taken
as a consequence of this correction.

**A SECOND, larger scope defect: a blanket lock stamp that carries no operator intent.**
A report-only run over the widened roots verdicted **364 trees / 305.2 GiB `LOCKED`** — which
looks like legitimate operator parking and is not. `scripts/worktree_gc.py:501` short-circuits
unconditionally:

```python
if wt.locked:
    wt.verdict = "LOCKED"
    wt.reasons.append(wt.lock_reason or "git worktree lock present")
    return
```

so for a locked tree the tool never computes landedness, dirtiness, or live processes at all.
Grouping those 364 by reason:

| lock reason | trees | GiB |
|---|---:|---:|
| `mastermind-external-storage: removable volume protection` | **282** | **215.8** |
| `initializing` | 3 | 5.8 |
| genuine seat/operator text (e.g. "Active Sol China participation context; release PR7592 untouched") | 79 | 83.6 |

The first string is stamped by the SSD worktree helper on **every** tree it mints, so it
encodes zero information about the work — yet it exempts the entire external-SSD population
from retention permanently. Joining that 285-tree pool back to the PR-state census and then
running by hand the three checks the short-circuit skipped found **41 trees / 26.6 GiB that are
clean, unoccupied and provably landed** (MERGED-PR or squash-matched), on top of the 60.8 GiB
the same run already classified SAFE.

Two implementation facts constrain any fix, and neither is a config flip:

- `worktree_gc.py` has **no lock-reason config key**. Its whole surface is `roots`, `armed`,
  `min_age_days`, `include_open_pr`, `include_orphans`, `max_delete_per_run`,
  `delete_local_branches`, `pr_limit`. Honouring the 79 real locks while ignoring the two
  content-free strings requires a code change plus a new opt-in key (default = today's
  behaviour, honour every lock).
- Deletion at line ~706 uses a single `git worktree remove --force`, which **refuses a locked
  tree** (`fatal: cannot remove a locked working tree`). An explicit `git worktree unlock`
  must precede removal — preferred over `-f -f`, because an unlock is a visible, auditable act
  while a double force would also steamroll a lock added after the gate ran.

Like the roots list, changing this is an OPERATOR ratification act, and it only pays off if the
roots are widened too, since the belt at line ~682 still refuses those paths.

**What this law cannot reach.** The 318 detached trees satisfy no proof in the CORRECTION box
and never will: 150 are `mo-ext-rev-*` / `mo-ext-fix-*` external CLI labour lanes minted
per-task by an orchestrator seat, whose output is collected and shipped from the SEAT's
carrier branch. Their commits are *supposed* to stay unlanded. 191 of 192 such lanes are
already born sparse, so this is ~0.45 GiB each rather than ~7.5 — a bounded but permanent
leak that grows with orchestration volume. They need a **lane-exit receipt** (a positive
"my output was consumed" signal written by the lane itself), not a merge. Until that exists
they are correctly, and permanently, KEEP. `refs/salvage/*` (534 refs) still matters for this
bucket — it decouples *preserving the commits* from *reclaiming the checkout* for ~40 bytes
each — but it licenses nothing under an attached session.

### STOCK vs FLOW — measured 2026-09-27, and the reason neither reclaim gate is the answer

Headroom at the time of measurement: `/Volumes/Mastermind` **792 GiB free of 3,725 (79% used)**,
which is **492 GiB above the 300 GiB `min_free_bytes` admission floor**; internal `/` has 332 GiB
free. **No active incident** — worth stating, because every figure below is otherwise easy to read
as urgent.

**Stock side (deletion).** 51 trees / **37.7 GiB** safe, per the gates below. At the burn rate
recorded in `~/.config/mastermind/worktree-storage.json` (**21.9 GiB/h**, measured 09-24→09-25
over 27 h) that is **about 1.7 hours of runway.**

**Footprint side (sparsify — reclaims bytes without deleting anything, because omitted paths stay
tracked).** 711 registered trees hold **861.9 GiB**, mean 1.21 GiB. Only **73 trees are FULL**
(≥3 GiB, i.e. `data/`/`site/`/`mockups/`/`verify_shots/` present) but they hold **409.5 GiB of
excess** over a ~0.6 GiB sparse baseline — 11× the whole deletion pool. Tempting, and mostly
untouchable:

| verdict | class | trees | excess GiB | thinnable? |
|---|---|---:|---:|---|
| DIRTY | HUMAN | 12 | 75.9 | **no** — truncates uncommitted work AND wedges the conversation |
| DIRTY | AGENT | 11 | 62.4 | **no** — a write into an omitted tree TRUNCATES the committed artifact |
| LOCKED | AGENT | 12 | 55.8 | only if landed — needs the lock-stamp fix |
| RECENT | HUMAN | 8 | 44.4 | no |
| RECENT | AGENT | 7 | 39.1 | no — active work |
| UNPUSHED | HUMAN | 5 | 29.7 | no |
| LOCKED | HUMAN | 6 | 29.2 | no |
| OPEN_PR | HUMAN | 4 | 22.2 | no |
| LIVE_PROC | AGENT | 3 | 22.1 | no — occupied |
| SAFE_* | HUMAN | 3 | 19.6 | no — human-driven |
| SAFE_MERGED | AGENT | 1 | 5.6 | delete outright |
| ORPHAN | AGENT | 1 | 3.5 | separate ratification |

**~61 GiB of the 409.5 is touchable; 283 GiB is structurally untouchable** (dirty, unpushed, or
human-driven). This CONFIRMS the earlier "a correctly-gated retrofit yields ~0.0 GiB" measurement
rather than contradicting it: the excess is overwhelmingly held by trees that cannot be thinned
safely, which is exactly why retrofit was a one-time backlog drain and never a lever.

**So neither stock nor footprint is the answer. The flow is.** Mean size and FULL-rate by mint
root:

| mint root | trees | total | mean | FULL |
|---|---:|---:|---:|---:|
| `/Volumes/Mastermind/worktrees` (**ungoverned — no sparse hook**) | 139 | 283.4 GiB | **2.04 GiB** | **21%** |
| `…/agent-workspaces/claude` (governed by the SSD helper) | 282 | 214.3 GiB | **0.76 GiB** | **3%** |
| `macro-main/.claude/worktrees` (governed by `WorktreeCreate`) | 206 | 202.7 GiB | 0.98 GiB | 8% |
| `…/agent-workspaces/tmp` (CI `contract-delta` scratch) | 9 | 43.1 GiB | **4.79 GiB** | **78%** |

The governed roots work: 3% FULL, mean 0.76 GiB. The ungoverned mint root runs **7× the FULL rate
and 2.7× the mean size**, and it is the same root that hosts the human-driven web trees — so it is
simultaneously the biggest per-tree emitter and the one population no sweeper may touch. At 54
trees/day that difference, not the 37.7 GiB of deletable stock, is what fills the volume.

**Ranked by GiB/day of burn averted rather than GiB reclaimed once:**

1. **Give `/Volumes/Mastermind/worktrees` a sparse mint path.** It is the only lever that compounds,
   it deletes nothing, it touches nothing anyone is attached to, and it needs no ratification act —
   closing the 2.04 → 0.76 GiB gap over 139 trees is ~180 GiB of footprint and a permanently lower
   slope. The reason it has none today is that nothing owns that root (see below).
2. **Sparse-or-TTL `…/agent-workspaces/tmp`.** 9 trees, 78% FULL, mean 4.79 GiB — machine-generated
   `contract-delta` base checkouts, the worst per-tree offender on the host and the easiest to fix.
3. The two reclaim gates below — 37.7 GiB, real but ~1.7 h of runway.

### Open ratification gates as of 2026-09-27 — both are OPERATOR acts, neither is taken

Measured inventory of what they unlock: `research/WORKTREE_RECLAIM_CANDIDATES_2026_09_27.md`
(**51 trees / 37.7 GiB safe**, every row with its landed proof AND its attachment class). For
contrast the armed sweeper at its shipped scope freed **1.5 GiB**.

**`roots` cannot express the human-driven exclusion at volume granularity, and that is the
first thing to get right.** `/Volumes/Mastermind/agent-workspaces` holds BOTH the agent-driven
Claude seat lanes (`claude/<seat>/…`) and the ChatGPT-web family (`sol/`, `review/`, plus loose
`*-sol` trees planted at its top level). Classifying the candidates by subtree:

| scope | pool A (SAFE) | pool B (behind lock stamp) | class |
|---|---:|---:|---|
| `/Volumes/Mastermind/worktrees` | 22 trees / 43.8 GiB | — | **HUMAN — never auto-reclaim** |
| `…/agent-workspaces/sol`, `/review`, loose `*-sol` | 9 trees / 5.8 GiB | — | **HUMAN — never auto-reclaim** |
| `…/agent-workspaces/claude` | — | 41 trees / 26.6 GiB | AGENT |
| `…/agent-workspaces/tmp` (CI scratch) | 2 trees / 6.8 GiB | — | AGENT |
| internal roots already in `roots` | 8 trees / 4.3 GiB | — | AGENT |

So **49.6 of pool A's 60.8 GiB is HUMAN-class**, and a valid landed proof on those rows is not
permission: reclaim needs landed **and** nothing attached, and a ChatGPT web conversation's
attachment is undetectable (no process, no shell, no reflog). Adding the two volume roots
wholesale would point an **armed deleter** at exactly the population the 2026-09-26 incident
killed — and that sweep only sparsified, where this one removes.

| # | gate | exact change | blast radius | unlocks |
|---|---|---|---|---|
| 1 | widen `roots` — **to subtrees, not volumes** | add `/Volumes/Mastermind/agent-workspaces/claude` (the policy-mandated seat root) and optionally `…/agent-workspaces/tmp`. **Do NOT add `/Volumes/Mastermind/worktrees`, `…/agent-workspaces` itself, `…/sol` or `…/review`.** | scope grows by the agent-driven SSD lanes only; the web population stays out of reach of an armed deleter | 2 trees / 6.8 GiB on its own (`tmp`); it is the precondition for gate 2's 26.6 GiB |
| 2 | stop treating a content-free lock as operator intent | CODE in `scripts/worktree_gc.py`: a new opt-in config key (default = today's behaviour, honour every lock) exempting only the two provably content-free reasons, **plus** `git worktree unlock` before the `remove --force` at line ~706 | touches `scripts/**`, the CI-authority inventory — a merged head there triggers the authority freeze, clearable only by a green `ci.yml` on a main descendant | 41 trees / 26.6 GiB, all under `…/agent-workspaces/claude`, and it ends the permanent exemption of the whole external-SSD population |

**Gate 2 carries essentially all of the safe yield, and gate 1 is its precondition** — the belt
at line ~682 still refuses a path outside `roots`, and every one of gate 2's 41 trees lives
under `…/agent-workspaces/claude`. Gate 1 scoped correctly is worth only 6.8 GiB by itself.
Neither is a consequence of the 2026-09-27 signal correction; do not infer authorization from it.

**A third, cheaper fix is implied by the table above:** the GC has no notion of an attachment
class, so today the only thing standing between an armed deleter and the web population is the
`roots` list being accidentally narrow. That is not a safeguard, it is a coincidence. A
`human_driven_roots` deny-list honoured ahead of every other verdict would make the protection
explicit and survive a future well-meaning widening.

A third item is **design work, not a gate**: the 318 detached lanes need a lane-exit receipt (a
positive "my output was consumed" signal written by the lane itself). Nothing in this law can
reach them until one exists.

**No program in `config/mastermind_programs.yml` owns fleet worktree storage.** That is why
this doc, `scripts/worktree_gc.py`, `config/worktree_gc.json`, the sparse hooks and the
host-local `~/.local/lib/mastermind/storage-cleanup/**` have no accountable seat, and why the
two gates above have sat open while the volume kept filling. Assigning an owner is a
prerequisite for the per-root population cap in R6, not a separate nicety —
a cap is a standing policy and a standing policy needs someone to hold it.

**Why accumulation is the real problem.** ~810 worktrees registered; **54 minted per day
sustained**, and approximately none removed. Two independent causes, and only the first is
about sessions: sessions do not close their own worktrees and that is not fixable by
instruction; and for 72% of them no sweeper is permitted to, because they sit outside the
configured roots (above). Reporting an idle age, a live cwd, or a
reflog epoch stays useful — for a human reading a report, or to narrow an action the
positive signal has already authorized. It is never the authorization.

