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

**REACH CORRECTED 2026-09-28 — both counts in that table are THIS CLONE'S REGISTRY, not the
roots' populations.** `/Volumes/Mastermind/worktrees` is a mint root shared by **12 distinct git
stores**: 353 directories sit directly under it, 336 of them linked worktrees, and only **140
belong to `Macro Dashboard`** — the clone every instrument in this document reads. The other 196
(58%) are owned by 11 other stores, two of which are self-hosted Actions runner workspaces, and
they **cannot be enumerated from here at all** — there is no registration to read. So "142" was
never the root's population, and neither a `roots` edit nor a host-detection repair can reach the
other 196: a per-clone sweeper structurally cannot govern a shared mint root
(`DSC:A-ONE-MINT-ROOT-IS-SHARED-BY-TWELVE-GIT-STORES`). Governing it would need per-entry owner
resolution plus a removal issued against the OWNING store — the one git shape a worktree-isolated
session may not run — so it belongs in a host-local daemon, not in this script. **Report the
instrument's REACH beside every per-root number from here on.** And the root is far larger
than any figure elsewhere in this document: `du` measures `/Volumes/Mastermind/worktrees` at
**726.4 GiB** (2026-09-28), against the 462 GiB recorded above for `…/agent-workspaces/claude`.
With 58% of its trees owned by stores we cannot enumerate, most of those bytes are not
addressable from this checkout at all.

**A THIRD absent location, found 2026-09-28 — an entire VOLUME that no root and no census
covered.** `/Volumes/Worktrees` (`/dev/disk4s1`, 931 GiB, **130 GiB free / 87% used**) hosts **9
fleet linked worktrees** across 4 stores. Six are owned by `Macro Dashboard` and therefore DO
appear in the same `git worktree list` every figure above is derived from — registry-visible is
not the same as governable — yet they are unreachable three times over: no root covers the volume
(the 7 relative roots are repo-relative session dirs; the 1 absolute root is
`~/.codex/worktrees`), the host-checkout belt refuses the path, and 4 of the 9 are `sol-*`
HUMAN-class that §9 never auto-reclaims. One — `sol-consumer-cyclical-7804` — carries a **dead
registration owned by `/Volumes/mini2/…`, another machine's volume**, so nothing on this host can
ever prune it. The volume also holds the user's own `Backups`/`Companies`/`Documents` and the
operator-protected `.ADSPOWER_GLOBAL`, which makes it **REPORT-ONLY for any sweeper,
permanently.** The correctness worry that prompted the look is **FALSIFIED**: the mount is exFAT
through Darwin 25 `fskit`, where a direct probe shows symlinks and mode bits both honoured, the
repo's one tracked symlink materialized correctly in all 6 trees that carry it, and both stores
set `core.filemode = false` anyway — so **do not migrate these trees for filesystem reasons**
(`DSC:A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED`).

**Full-clone census 2026-09-28 — a NULL result, recorded so nobody re-runs it.** Worktrees are not
the only disk consumer, so the non-worktree git clones were swept too: **331 clones / 163.2 GiB**,
of which essentially nothing is safely reclaimable under §9. **77.1 GiB is DIRTY** (uncommitted
work, led by one 38.9 GiB `sol-biocatalyst-6389-recovery`); **69.7 GiB is clean+pushed but almost
entirely `sol-*` HUMAN-class**, one of them last written **0.1 h** ago; 16.3 GiB is undecidable for
want of an upstream, and 0.1 GiB is unpushed. The result matches §9's shape: what bounds the
reclaimable pool is the judgment gate, not the byte count.

**Scratchpad census 2026-09-28 — a second NULL result, and the safety check earned its keep.**
`/private/tmp/claude-501` holds **216.6 GiB across 924 session scratchpad dirs** on the INTERNAL
data volume (1.5 Ti used / **85%** — the tightest of the three volumes, and the one whose free
space `df /` misreports as 4% because that row is the sealed read-only system snapshot, not
`/System/Volumes/Data`). A scratchpad is a different object from a worktree — scratch files by
contract, no checkout, nothing referenced by `origin/main` — so it looked like the first pool whose
dead entries would be plainly reclaimable. It is not: **the >7-day pure-scratch bucket is 144 dirs
and 0.00 GiB.** The bytes are 160.8 GiB across 431 dirs written within 24 h (live sessions), 1.2 GiB
idle 1–7 d, 0.0 GiB in 254 empty dirs, and **47.0 GiB across 12 dirs that contain a git checkout or
store** — refused on sight, two of them live and over 20 GiB each. A single LIVE session holds
**134.8 GiB**, 62% of the whole pool. Two lessons. The naive reading ("216 GiB of temp files") would
have destroyed live sessions' working state for zero yield. And `/private/tmp` is carrying 47 GiB of
git checkouts although the house rule names `/private/tmp` as a place project work may never live —
a placement question for the operator, never bytes a sweeper may take.

**The largest UNPROVABLE reclaim candidate in the shared mint root is 7.2 GiB, and it fails closed.** (This sentence originally read "The largest clean reclaim candidate on the SSD is 7.2 GiB" and is **CORRECTED 2026-09-28, same day**, by the full-volume attribution below: the largest clean candidate on the SSD is **41.76 GiB** in `/Volumes/Mastermind/tmp`, and unlike this one it is fully PROVABLE.) The shared
mint root's two already-orphaned registrations are both self-hosted runner workspaces whose gitdir
target is gone: `sol-flow-velocity-recovery-proof-20260920` (**7.2 GiB**) and
`prophet-b4-session-policy-repair-20260922-a11` (408 KiB). No store registers them, so no
`worktree prune` anywhere can see them and no configured root covers them; and because the
registration is gone, `git` cannot run inside the tree at all, so landedness is **unprovable** and
§9 fails it closed. Recorded rather than taken — clearing it is an operator judgement ("CI
leftovers, re-derivable from `origin`"), which is precisely the class of call §9 reserves for a
human.

### Full-volume attribution 2026-09-28 — the first complete map, and two pool names that lie

Every per-root figure above was a per-root figure. `du` over all 45 top-level entries of
`/Volumes/Mastermind` finally accounts for the whole 2.9 TiB (**3,069 GiB measured**), and
**58% of it was never in any census**:

| GiB | entry | class |
|---:|---|---|
| 952.7 | `agent-workspaces` | fleet worktrees — the doc's 462 GiB was `…/claude` ALONE, not the root |
| 725.4 | `worktrees` | the 12-store shared mint root (confirms the 726.4 GiB above) |
| 415.2 | `Personal` | operator data — untouchable |
| 233.0 | `transfers` | **not file transfers** — live agent review rounds |
| 214.9 | `tmp` | PR proof/review clones (censused below) |
| 190.7 | `Offloaded` | **not operator offload** — the fleet's own verified backup archive |
| 98.8 / 67.0 / 58.3 / 47.9 / 40.9 | `Mastermind` `ops` `evidence` `repos` `agent-evidence` | repo + 829 dated proof receipts |
| 6.0 / 4.7 / 3.7 / 8.5 | `reviews` `test-tmp` `temp` + 5 loose `sol-*` trees | small; the `sol-*` are HUMAN-class |

**Two names mean the opposite of what they say, and both would mislead a sweeper written from
the directory listing.** `transfers` (233.0 GiB) is not transferable files — it holds
`r15green-*`, `r16red-*`, `r17-red-*`, `r18-astra-*`, `r19q-accepted` review-round scratch,
**all written between 00:58 and 06:25 the same morning**: another lane's live workflow.
`Offloaded` (190.7 GiB) is not the operator's offloaded data.

### `Offloaded` is the fleet's verified backup archive — a FIFTH null result

The hypothesis on opening it was that prior reclaim waves had *moved* bytes instead of
freeing them, making it the largest reclaimable pool on the volume. **That is wrong, and the
archives' own READMEs say why.** `m2-tmp-reap-20260918` bundled 14 scratch dirs' unreachable
history, discovered `--all` had produced **270 GB of bundles** (37–47 GB each), proved 13 of
the 14 redundant by fetching 31,315 refs into the main clone and `cat-file --batch-check`-ing
all 23,665 bundle head objects — **exactly one** was missing — and kept the **2.2 GB thin
equivalent** built with `--not --remotes=origin`. The wave *did* free the space; this is the
irreducible residue, and every archive carries a documented `git fetch` restore path.

Nothing here is reclaimable:

- **`Sol-runs` 74.5 GiB** — HUMAN/Sol class, and **65 files were written in the last 7 days**:
  the lane is live, not archived.
- **~25 GiB of `.bundle` files** — they hold, by construction, "exactly the commits GitHub
  does NOT have" (12,181 heads). That IS the unpushed backlog §9 already refuses.
- **`m2-worktree-dirt-20260917` 8.7 GiB / 220 entries** — 220 trees' preserved uncommitted
  dirt. The only copy.
- **`M1-cleanup-20260911T0735Z` 1.35 GiB** — contains GoLogin 2022 items, under a standing
  operator veto: never deletable.
- The two entries with the largest ENTRY COUNTS (`temp-worktree-gc`, 1,102; `sparse-conversions`,
  315) are ~1 KB JSON receipts — about 1 MB combined. **Directory entry-count reads as bulk and
  is not bulk**; check bytes before believing a listing.

**Incidental, and worth more than the bytes:** `storage-cleanup-20260913-wave2/report.md` had
**already diagnosed the `contract-delta` base-tree leak** — naming
`scripts/check_contract_delta.py`'s `materialize_base_tree()` and its
`tempfile.mkdtemp(prefix="contract-delta-base-")` — on **2026-09-13/14, two weeks before the
reaper shipped**. A verified root-cause analysis sat unread in a directory named `Offloaded`
while the leak regenerated ~7 GiB/day. **Read `Offloaded/*/README*` and `*/report.md` before
diagnosing a fleet storage problem**; prior waves left verified findings there.

### The SSD `tmp` pool: 214.8 GiB of proof clones — a SIXTH null result, and the one PROVEN candidate

`/Volumes/Mastermind/tmp` is **296 dirs / 214.8 GiB** of throwaway PR proof and review
clones (`pr979-…`, `prophet-7457-release-snapshot`, `review-7535-…`), most made for PRs in the
#7000s during 09-19→09-26. Censused read-only against `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`,
byte-weighted (a dir-count table is not a reclaim figure):

| GiB | dirs | verdict |
|---:|---:|---|
| 59.82 | 20 | clean but HEAD not in **that clone's** `origin/main` |
| 43.77 | 21 | landedness undecidable there |
| 33.14 | 11 | HUMAN-class name |
| 20.19 | 203 | not a git clone — needs its own judgement |
| 18.78 | 10 | git unreadable |
| 38.2 | 30 | DIRTY (one tree carries **99,026** dirty paths) |
| **0.55** | 1 | clean + landed |

**The two biggest refusal buckets were instrument artifacts, not findings.** A proof clone
never fetches after birth, so its `origin/main` is frozen at clone time and any HEAD that
landed later reads as unlanded. Re-asked against a CURRENT `origin/main` in a live worktree —
locally, `GIT_NO_LAZY_FETCH=1`, no network — 2 of those 41 dirs are **provably landed**:

- **`pr979-macro-88804-proof` — 41.76 GiB**, origin `macro`, HEAD `88804ed70797`, which lands
  on main as `perf(agentos): batch Git dates and accelerate YAML parsing` (2026-09-27).
  **0 dirty paths, 0 open files.**
- `prophet-7187-proof-clone-20260920` — 2.43 GiB, HEAD `80003197c05d`, likewise clean and
  unattached.

**44.19 GiB satisfying every substantive clause of §9 — landed, clean, nothing attached, not
HUMAN-class — and it is still NOT taken**, because the final clause requires the tree to sit
under a configured root and `/Volumes/Mastermind/tmp` is not one. Note the difference in KIND
from the 7.2 GiB case above: that one fails because landedness is *unprovable*; this one is
proven and lacks only authorization. It is the largest proven-reclaimable find on the volume.

**A REACH correction on this census, for the same reason the roots table needed one.** 23 dirs
answered "HEAD sha not present in this clone", first reported as "never landed, or unreachable
history". Resolving each dir's `origin` remote: **17 are `Mastermind` clones and 1 has no
origin** — a macro clone cannot answer for a Mastermind commit, so for 18 of 23 "not landed"
was never an available answer, and abandonment was over-counted by 18. Only **5** are macro
and genuinely carry history main lacks. A shared temp root looks like one population because
it is one directory; its names come from **four repositories'** PR numbering and nothing in
the path says so. **Partition any cross-tree census by `origin` before counting.** The same
positional mistake sat in the census's own protective screen: the HUMAN-class test matched
name PREFIXES (`sol-`), so `prophet-b4-owner-archeology-20260921-sol-001` — 6.03 GiB, Sol
class by any reading — was admitted as reclaimable until the marker was matched anywhere.

**SEVEN independent pools have now been measured and SIX are null.** Shared mint root 726.4 GiB
(58% unreachable), `/Volumes/Worktrees` 801 GiB (report-only forever), full clones 163.2 GiB,
session scratchpads 216.6 GiB (0.00 GiB dead), `Offloaded` 190.7 GiB (verified backups), SSD
`tmp` 214.8 GiB (0.55 GiB free-and-clear + 44.19 GiB proven-but-unauthorized), and
`transfers` 233.2 GiB (**zero reclaimable**, and holding 195.28 GiB of operator photo data
that no automated path may touch — see below). (This sentence read "Six independent pools … and five are null" with
no `transfers` row, and is **CORRECTED 2026-09-28, same day**: the seventh pool was measured
hours later by a census that then had to be corrected itself.) What bounds
reclaim on this host is not the byte count and not the instruments — it is the judgment gate,
exactly as §9 says.

### The non-git bucket: 20.19 GiB with no landedness question to ask

The 203 non-git dirs in `/Volumes/Mastermind/tmp` are the one bucket
`DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` structurally cannot reach. That law decides on
landedness; a directory with no repository has no HEAD, so there is nothing that could be an
ancestor of anything. The threshold is not the problem — the QUESTION is. For a dir with no
git identity the only honest questions are what it is, whether anything is still writing to
it, and whether its content is **regenerable from something that outlives it**. Profiled
read-only (extension histogram, file count, newest mtime, top-level shape):

| GiB | dirs | class | the question that applies |
|---:|---:|---|---|
| 10.38 | 138 | no git identity of any kind | unprovable → **REFUSED** |
| 7.41 | 25 | HUMAN/Sol marker in the name | never auto-reclaimed → **REFUSED** |
| 1.90 | 6 | virtualenv (`pyvenv.cfg`) | **regenerable by construction** |
| 0.32 | 1 | a **bare** git store (`macro-reconcile.git`) | judge as a git store, not as files |
| 0.18 | 16 | written inside 2 days | live → leave |
| 0.00 | 17 | empty (0 files) | nothing to reclaim |

**Virtualenvs are the one class here where "no git identity" is not a blocker.** A venv is pip
output: nothing authored lives in it, and the thing that outlives it — the requirements file in
some repo — regenerates it. All 6 carry `pyvenv.cfg` and **none has an open file** (`lsof +D`).
That is 1.90 GiB whose refusal would be superstition rather than caution. It is also
**1.9 GiB against a 731 GiB free volume**, which is the honest reason not to spend a
ratification act on it: the class is defensible, the amount is not worth the paperwork. Recorded
so the next census does not re-derive it.

**The 10.38 GiB refusal is the real content of this bucket, and its largest member is a single
7.23 GiB tree**, `prophet-7457-release-snapshot` — 60,618 files, idle 8 days, no `.git`, no
`HEAD`, no `COMMIT_EDITMSG`, no manifest of any kind. It is *probably* a checkout of some
release candidate. "Probably" is exactly what §9 refuses: with no commit to name, no proof
exists that its content is anywhere else, and the same reasoning that protects the 7.2 GiB
`sol-flow-velocity-recovery-proof-20260920` protects this.

**One number moved when the protective screen was repaired, and the direction matters.** Before
the HUMAN-class test matched its marker anywhere in the name, this bucket's unprovable class was
**14.46 GiB** — two 7.23 GiB snapshots. The second, `prophet-7526-current-main-review`, is
HUMAN-class on `review`, so it moved to a different refusal. The verdict on it did not change;
only the REASON did. That is worth stating because a ratification act operates on reasons: an
operator deciding "clear the unprovable snapshots" would have been handed a Sol review tree in
the same list.

### `transfers` — the seventh pool, zero reclaimable, and a census that could not see 84% of it

`/Volumes/Mastermind/transfers` is **71 entries / 233.2 GiB**. Its name says the files are in
transit; its contents are live agent review rounds (`executive-os-convergence-20260918`
28.54 GiB, `mastermind-os-orchestrator-launchpad-20260926-sol-001` 4.70 GiB,
`pr870-task2-prepared-*`, `current-turn-r2-observer-cut-*`) plus checkpoint and handoff scratch.
Nothing in it is reclaimable: the large dirs are HUMAN/Sol-marked or days old, and the rest is
rounding error.

**It is recorded here for the defect, not the bytes.** The census that measured it ran every
instrument this document had already repaired — bare-store detection, marker-anywhere HUMAN
screen, origin-partitioned landedness — and still reported **37.97 GiB for a 233.25 GiB pool**,
because it iterated `x.is_dir()`:

| entries | GiB | share | seen by the census |
|---:|---:|---:|---|
| 57 dirs | 37.97 | 16.3% | yes |
| **14 files** | **195.28** | **83.7%** | **no** |
| 71 total | 233.25 | 100% | — |

**A single file was 84% of the pool** and the instrument's shape made it unobservable — not
misjudged, not refused, absent. It was found by `find -maxdepth 1 -type f`, which is the whole
fix. This is the fifth instance in this document of the same failure mode: an instrument asking
a POSITIONAL question (*what sits at a directory position?*) in place of a semantic one (*what
occupies this pool?*), and returning a clean, plausible, wrong number with no error.

**What that file is, and the sixth instance of this document's own failure mode.**
`runner-fleet-resilience-worktrees-photoslib-20260924.tar` is 195.28 GiB and contains
`Photos Library.photoslibrary/` with `originals/`, `database/`, `resources/` and `scopes/` — the
operator's personal photo library, sitting in a directory whose other 70 entries are agent
scratch, under a name whose first three words are fleet-infrastructure vocabulary. It is
untouched, it must never be deleted, moved or truncated, and `/Volumes/Mastermind/transfers`
joins `/Volumes/Worktrees` as **REPORT-ONLY for every automated path**. Any sweeper deleting
"stale transfer artifacts older than 7 days" would destroy it.

**It is a BACKUP, not the only copy — and getting that wrong was my own reach failure, made
while writing this section.** This paragraph first read:

> There is no `.photoslibrary` in `~/Pictures` and none anywhere on this volume at depth ≤ 3,
> so **this tar appears to be the only copy on the machine.**

Both facts in that sentence are true and the conclusion does not follow, because the search
enumerated two locations and the claim was about a machine. **CORRECTED 2026-09-28, same day:**
the live library is `/Volumes/Worktrees/Documents/Photos Library.photoslibrary` — **247 GB**,
with `database/`, `external/`, `internal/`, `originals/`, `private/`, `resources/`, `scopes/`
all present — and `PREFLIGHT.txt` for the very operation the tar is named after lists it as
`protected=`, i.e. deliberately excluded from that move alongside `Pictures` and `WeChat`; the
operation's actual candidates were `Courses`, `Documents New` and `Jewelry`, two of which halted
`HELD_SOURCE_RACE` with `no_source_removal`. The tar is therefore a 2026-09-24 point-in-time
copy of a library that is still in place and has since grown.

The omitted volume is the one this document had **already classified two sections earlier** as
holding the operator's `Backups`/`Companies`/`Documents` — so the gap was not ignorance of the
volume, it was a search whose scope was never restated as a REACH claim. What survives
unchanged: the file is operator data in the wrong place, it is never deletable, and the pool is
report-only. What changes is urgency and framing — relocating a redundant 195 GiB backup is
housekeeping, whereas relocating an irreplaceable original is an emergency, and reporting the
second when the first is true spends operator attention that the real gaps need. Full record:
`DSC:TRANSFERS-HOLDS-A-195-GIB-OPERATOR-PHOTO-BACKUP-NOT-THE-ONLY-COPY`.

**The genuine hazard the correction exposes is larger than the one it retracts.** Both copies of
the operator's photo data — the 247 GB live library and its 195.28 GiB tar — sit on volumes the
fleet writes to and sweeps: the live one on `/Volumes/Worktrees` (87% full, exFAT, also holding
9 fleet worktrees and the AdsPower payload), the tar on `/Volumes/Mastermind` among PR proof
clones. Neither is on a backup device. That is a real finding, and it is the one to hand an
operator.

Two rules follow, and neither is about this file:

1. **Census files as well as directories, at every level.** A pool measured by directory
   iteration has an unstated precondition — that nothing large is stored as a file — and this
   volume violated it by 195 GiB.
2. **When the largest object in a pool carries an infrastructure name, open it before
   classifying it.** The name described the operation that moved the object, never the object.
   Every neighbour of this tar genuinely is machine residue, which is precisely what made the
   name plausible.
3. **A search reports its REACH, never a machine-wide absence.** "No `.photoslibrary` in
   `~/Pictures` or on `/Volumes/Mastermind` at depth ≤ 3" is a finding; "the only copy on the
   machine" is a claim about three mounted volumes, and the one omitted was already documented
   in this file as holding the operator's `Documents`. Before any absence claim, enumerate the
   mounted volumes (`mount`, `df`) and say which were searched — the same discipline §"A second
   external volume" already imposes on storage totals, applied to existence questions.
4. **The pre-transfer receipts are the authority on what a past operation touched.** `PREFLIGHT.txt`
   in a reclaim directory names `source_volume`, `target_volume`, every `protected=` path, each
   `candidate=`, and a `candidate_status=` per candidate including halts. Reading it costs one
   `cat` and answers questions a `du` census cannot: two of that operation's three candidates
   halted `HELD_SOURCE_RACE|no_source_removal`, so source data it was meant to remove is still
   in place. Read the receipts before inferring intent from a directory name.

### `/Volumes/Worktrees` by BYTES — an eighth pool, and the fleet is 6.5% of it

The volume §"A second external volume" found ungoverned was never size-attributed, so
"9 ungoverned fleet worktrees" silently became "this is where the bloat is". Top-level `du -sxk`
over all 34 entries, files as well as directories:

| share | GiB | entry |
|---:|---:|---|
| **89.0%** | 712.72 | `Documents` — operator personal data |
| 4.5% | 36.08 | `Backups` — operator |
| 6.5% | 51.85 | **all 6 sized fleet/Sol trees combined** |

**Operator data is 93.5% of this volume and the whole fleet is 6.5%** — and 46.43 of those 51.85
GiB are `sol-*` HUMAN-class, which `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` never
auto-reclaims. **Agent-reclaimable on this entire 931 GiB volume is at most ~5.4 GiB.** Inside
`Documents`, the three largest categories are the live photo library (246.65 GiB), a separate
pictures tree (147.02 GiB) and a messaging archive (133.23 GiB); the operator's per-folder
structure is deliberately not enumerated here, for the same reason the pre-transfer manifests'
filenames are not. `.ADSPOWER_GLOBAL` measures **0.00 GiB** — a marker, not a payload; the
operator veto on it stands regardless of size.

**So the 87% fill on this volume is not a fleet problem, and nothing in §9 can touch it.** Not a
roots widening, not arming the sweeper, not the lock-stamp repair, not a population cap — there is
almost nothing there to reclaim. That is the eighth pool measured and the seventh null, and it is
the clearest case yet of the pattern §9 keeps running into: **the measurable thing and the
actionable thing are different, and a governance gap is not a byte attribution.** The genuine
risk inverts: ~130 GiB free, and every worktree the fleet plants here consumes the operator's
remaining headroom for a photo library that is still growing — whose only other copy is the
195.28 GiB tar on `/Volumes/Mastermind`, so **neither copy is on a backup device.** Whether the
fleet should plant worktrees on this volume at all is an operator question, and it is a better one
than any reclaim gate.

### The INTERNAL disk — where the agent bytes actually were, and the only real lever in §9

Seven of the eight pools above are on the two external volumes, and seven of them are null. The
internal data volume — the tighter one, **the volume that actually hit ENOSPC twice** — had never
been censused at all. `du -sxk /` (one filesystem): `/Users` 1089.56 GiB, **`/private` 652.90**,
`/Library` 95.38, `/Applications` 68.27, `/opt` 10.83. That total, 1917.93 GiB, exceeds `df`'s 1501
GiB used because `du` double-counts APFS clones and hard links, so **treat it as an upper bound and
a ranking, never an attribution.** Inside it, two agent/CI pools no policy document mentions:

**Ninth pool — `/private/tmp/claude-501`, 160.43 GiB, of which 0.02 GiB is provably dead.** The
session scratchpad root, 473 keys, and the next entry in all of `/private/tmp` is 0.68 GiB. Each key
is named after the checkout its sessions started in, and **that name is an inverted liveness
signal**: the largest key (81.24 GiB) names a checkout that no longer exists while its one session
— the active FINANCE INTELLIGENCE seat — had written 4 minutes before measurement, because a session
keeps its original key for life. Classified by the signal §0 already calls STRONG, the session
transcript mtime under `~/.claude/projects/<the same key>/<uuid>.jsonl`:

| class | keys | GiB | share |
|---|---:|---:|---:|
| **LIVE <2h** | 6 | **103.91** | **64.8%** |
| RECENT <24h | 7 | 0.17 | 0.1% |
| IDLE 1–7d | 60 | 22.21 | 13.8% |
| **COLD ≥7d** | 48 | **0.02** | **0.0%** |
| NO TRANSCRIPT — undecidable | 61 | 28.39 | 17.7% |
| no project key (mostly the shared `bash-edit-diff` cache) | 291 | 5.73 | 3.6% |

**The bytes are in live sessions and the dead keys are empty**, so an age-gated sweep here frees
0.02 GiB and any widening that frees real space walks into a live seat — the 2026-09-26 incident
class again, now against a target with no lock, no registry entry and no `git status` to refuse on.
That 81.24 GiB is **nine `.git`-less 8.63 GiB full repo trees** (77.7 GiB), the never-measured cost
of this repo's own "prove it in main's bytes" discipline; with no HEAD,
`DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` cannot reach them at all, exactly like the 318 detached
trees. The cheap fix is a session convention — one reusable comparison tree, removed when the claim
is filed — not a sweeper.
`DSC:A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-WHILE-ITS-SESSION-IS-LIVE`.

**Tenth pool — the CI runners' own stores, 177.26 GiB, and 87% of a checkout is `.git`.**
`actions-runner-2` 85.10 GiB, `-3` 68.18, `-4` 15.84, the original 8.14 — more than **3× the entire
fleet worktree footprint on `/Volumes/Worktrees`**. On the idle runner-3: checkout 66.34 GiB, `.git`
**57.70**, working tree 8.6; **136 packs / 57.20 GiB** against 0.47 GiB loose. `actions-runner-2`
holds **two** base-size packs, 31.63 + 28.61 GiB — two copies of the same history in one store.
`_temp` is 0.00 GiB, so the runners already clean the thing everyone assumes is the problem.

**This is where R8's own ratio reverses.** Sparseness omits `data`/`site`/`mockups`/`verify_shots`,
which are 87% of an agent WORKING TREE — and on a runner those same four are 8.02 GiB of 66.34,
**12%**, because there the 87% is the store. So the lever is repack/re-clone, not sparseness, and
**it is an operator act**: a `Runner.Worker` was live during measurement, a mid-job repack can break
the job, and an aggressive repack on a 4-core box contends directly with the nightly's ~67-minute
render budget. Nothing is at risk either way — a runner store is 100% re-fetchable from `origin` —
which is precisely why it is the one bounded, reversible reclaim in this whole triage.
`DSC:A-RUNNER-CHECKOUT-IS-87-PERCENT-GIT-STORE-SO-SPARSENESS-CANNOT-REACH-IT`.

**The standing lesson of ten pools: the bytes were never where the program was looking.** The
ENOSPC remediation aimed at agent worktrees; the agent-attributable bytes on the volume that
crashed are ~337 GiB in two places §9 never named, and the only one with a lever is the one nobody
calls a worktree. Attribute the target volume, and check whether its bytes are tree or store,
before proposing any further storage work here.




**The placement policy moved to the external SSD and the GC's scope never followed.** That
half stands: the roots really are absent, and the 496 trees behind them really are invisible
to the report. What did NOT stand is the size of the act. This paragraph read, from
2026-09-27 until the correction below:

> Adding those roots widens an armed deleter from 227 to 807 trees and is therefore an
> OPERATOR ratification act in its own right, exactly like flipping `armed` was — it must not
> be taken as a consequence of this correction.

**FALSIFIED 2026-09-28 — widening `roots` arms almost nothing, because a second belt refuses
every SSD path before the roots list is ever consulted** (`DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`).
The sweeper does not decide "session tree vs host checkout" from `roots`. It decides it from
repo-RELATIVE path SEGMENTS:

```python
rel_roots = [r for r in cfg["roots"]                      # line ~861
             if not r.startswith("~") and not os.path.isabs(r)]
hosts = host_checkouts(primary, registered, rel_roots)

def path_under_session_root(path, rel_roots) -> bool:     # line 165
    parts = Path(path).parts
    for rel in rel_roots:
        marker = tuple(rel.strip("/").split("/"))         # ('.claude', 'worktrees')
        ...                                               # segment-tuple match
```

`rel_roots` keeps only the seven relative entries — `.claude/worktrees`, `.claire/worktrees`,
`.codex/worktrees`, `.codex-worktrees`, `.cursor/worktrees`, `.grok/worktrees`,
`.warp/worktrees` — and drops both absolute and `~`-prefixed ones. Any registration matching
none of those markers is classified a **host checkout**, and the belt at line ~688 refuses a
host by identity, one check after the "outside configured roots" refusal:

```python
if any(wt.path.resolve() == Path(h).resolve() for h in (hosts or ())):
    summary["errors"].append(f"{wt.path}: refused — host checkout")
    continue
```

`/Volumes/Mastermind/…` can only be named ABSOLUTELY, so it can never enter `rel_roots`, so
every tree under it is a host, so the belt refuses it — whatever `roots` says. Measured over
the live registry (804 registrations, 2026-09-28):

| | hosts | sweep roots | `in_scope` | **reachable by the belt** |
|---|---:|---:|---:|---:|
| `roots` as shipped | 578 | 4,047 | 225 | **225** |
| `roots` + the two SSD subtrees | 578 | 4,049 | **721** | **226** |

Widening buys **+496 trees of REPORTING and +1 tree of deletion.** The single gained tree is
`/Volumes/Mastermind/agent-workspaces/maintenance/.claude/worktrees/ssd-worktree-policy-20260906`,
and it is reachable only because it happens to carry a `.claude/worktrees` segment of its own.

Three consequences, and the second is the one that matters:

1. **Ratifying the wider `roots` is a much smaller act than this document claimed** — it is
   close to inert for deletion and is worth taking mostly for the report. It is also nearly
   pointless alone: making it mean anything needs a companion CODE change so that session-tree
   detection follows the configured roots instead of a hardcoded relative-path pattern. Both
   halves are still operator ratification acts; neither is a consequence of any correction.
2. **The SSD web-session population is protected today by an accident, and the accident is
   load-bearing.** 527 registrations on the SSD — including the entire `sol/`, `review/` and
   `/Volumes/Mastermind/worktrees` web family whose trees died on 2026-09-26 — survive an
   armed deleter because of a naming heuristic, not because anyone decided they should. The
   moment someone "fixes host detection so that widening works", that protection vanishes
   silently and in the same commit. So the explicit `human_driven_roots` deny-list honoured
   ahead of every verdict (§9 “Open ratification gates”, third fix) is MORE necessary
   after this correction, not less, and
   anyone editing `host_checkouts`, `path_under_session_root` or `rel_roots` owes it in the
   same PR.
3. **An absolute-only `roots` list silently disables deletion entirely.** Empty `rel_roots`
   makes `path_under_session_root` return False for everything, so every registration becomes
   a host and every target is refused. It fails CLOSED — the safe direction — but it fails
   quietly: the refusals land in `summary["errors"]`, which `scripts/worktree_gc.py:949`
   counts and never prints. A run reporting `deleted=0 errors=N` with no messages is this.

The `expand_roots` blow-up is worth separating from the widening question: sweep roots are
**already** 4,047 today (7 relative x 578 hosts + 1 absolute), because every SSD registration
is a host and every relative root expands under every host. That cost is pre-existing, and
widening adds 2 entries to it, not 4,000.

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

### The ELEVENTH pool — 201 GiB the sweeper is FORBIDDEN to read, and the only broken thing in §9

**Measured 2026-09-28, prompted by a macOS notification the operator relayed, not by a census.**
`/Users/chriswong/Documents` holds **457.9 GiB**, and inside it
`Cluade/macro-main/.claude` is **201.13 GiB across 203 session worktrees** — larger than the
CI runner stores (177.26 GiB) and larger than the scratchpad pool (160.43 GiB). `Macro Dashboard`
is a further 81.22 GiB and `charting-app` 56.10.

**This CORRECTS the section above.** That section says the internal disk's agent bytes were
`/private/tmp/claude-501` plus `actions-runner*/_work`, "~337 GiB, neither named by any policy
document". Both figures stand, but they were not the whole disk: a third pool, larger than either,
sat in `~/Documents` and was never counted. The sentence to distrust is any reading of that section
as an exhaustive attribution of the internal volume — it was an attribution of what the measuring
session could **read**.

**Why the sweeper never touched it — and why this is not the roots defect.** `.claude/worktrees`
is already in `config/worktree_gc.json` `roots`; the config is `armed: true`; `macro-main` is a host
checkout the GC expands its repo-relative roots under **by design**. Nothing about scope is wrong
here. The blocker is macOS TCC: `~/Documents` is a protected location and the launchd job's
interpreter — `/usr/bin/python3`, resolving to
`/Applications/Xcode.app/Contents/Developer/usr/bin/python3` — holds no Full Disk Access grant.
`storage_floor_guard.py` has logged `REMEDIATOR FAULT: sweeper BLIND: denied: PermissionError:
[Errno 1] Operation not permitted: '/Users/chriswong/Documents'` **16 times since 2026-09-24
05:49:53**, alongside **73 `ESCALATION` lines**; the single remediation that completed (09-26
16:56) reclaimed **−0.1 GiB** and logged `automated reclaim is NOT keeping up`.

**Of the three storage defects this program has found, this is the only one that is broken rather
than undecided.** The roots list (§ above) and the host-checkout belt are scope questions awaiting
operator ratification. This is a working, armed, correctly-scoped sweeper that cannot read its own
target, and repairing it needs no code, no config and no ratification — only a Full Disk Access
grant, **which is a security setting only the operator may make**. `TCC.db` is SIP-protected and no
session may edit it. State the cost honestly when asking: all five storage jobs
(`storage-floor-guard`, `storage-sweeper`, `worktree-gc`, `worktree-salvage`,
`fleet-remote-sweeper`) share `/usr/bin/python3`, so one grant repairs all five and also extends
full disk access to anything else that interpreter runs; a dedicated interpreter for these jobs,
with the grant scoped to it, is the tighter alternative.

**The generalisable failure is REACH, and it is the same one this section keeps recording — except
this time the reach difference is WHICH PROCESS ASKS.** An interactive session inherits its
terminal's TCC grant and reads `~/Documents` fine, which is why every hand census has seen this
pool; `launchd`'s python cannot, which is why no automated sweep ever has. Both answers are correct
about what their principal can see, and neither states its reach — so the hand census under-counted
the internal disk by 201 GiB while the automated sweeper emitted a fault nobody read. **An
automated remediator that cannot see its target fails exactly like one with nothing to do**: the
floor guard prints `OK` between breaches, and the fault line only appears when a breach triggers
remediation. Any reclaim lane must enumerate what it could not read and report that count beside
its verdict, or its silence will be taken for success.

**How much the grant would actually free: 1.81 GiB of 201.13, measured — and that is the whole
honest case.** The `DSC` pre-registered this as its own falsifier and it FIRED. Running the GC's
report over the pool as a principal that can read `~/Documents` (207 registrations = the 203
directories + 4 already-gone checkouts) verdicts `DIRTY 68/95.43G`, `LOCKED 43/40.49G`,
`UNPUSHED 57/27.01G`, `RECENT 11/13.12G`, `OPEN_PR 15/8.48G`, `ORPHAN 5/7.72G`, `LIVE_PROC 1/7.05G`,
`MISSING 4/0G` — and **`SAFE_MERGED` 3 trees / 1.81 GiB, 0.9 %**. Half the pool (103 trees /
99.94 GiB) is HUMAN-class `sol*`/`review*` that `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` never
auto-reclaims; 61 % is `DIRTY`+`UNPUSHED` — content not reproducible from `origin/main`, which is the
accurate phrasing and not the same thing as "work that has not landed". **`DIRTY` was checked rather
than assumed**, because the assumption is how 09-26 happened: `git status --porcelain` in all 68
trees finds **54 trees / 76.95 GiB carrying real tracked modifications (81 % of the DIRTY bytes)**
and 14 / 18.48 GiB untracked-only, of which 8 / 8.41 GiB are also landed. **Those 8 are still not
collectable** — untracked files have no commit, no ref and no remote, so neither `refs/salvage/*` nor
`origin/main` can reconstitute them, and the largest is 2.90 GiB of `mockups/evidence/…`, the exact
class the 09-26 sparse sweep destroyed. A landed `HEAD` proves the commits are safe and says nothing
about the working directory; "landed, therefore collectable" is the inference that caused the
incident. **So do not sell the grant on bytes.** Sell
it on the two things it actually buys: a floor guard whose remediation RUNS (today every breach ends
in `REMEDIATOR FAULT`, so the net is absent, not slow), and reach for the reclaim-at-merge FLOW gate
over the busiest pool in the fleet.

Two follow-on levers die here on measurement, and both die the way §9 keeps predicting — the pool's
composition, not its size, decides. The `worktree_gc.py:501` lock short-circuit is worth 41 trees /
26.6 GiB on the SSD pool because 282 of 285 locks there are the helper's content-free stamp; in THIS
pool **zero of 43 locks is a stamp** — every one carries real seat text — so its ceiling is 17.01 GiB
across 15 non-human locked trees and realistically less. And retrofit-to-sparse is not the lever:
**181 of 207 trees are already sparse (<1 GiB) and still total 88.99 GiB**, while 16 un-sparsified
FULL trees hold 98.41 GiB. This pool is large by COUNT, so the matching lever is the per-root
population cap below, not a thinner tree.

**The floor is not currently breached** — internal free is 316.8 GiB against a floor of 260, last
breach 2026-09-26. The broken thing is the safety net, not the disk, which is exactly how it stayed
broken from 09-24 without being noticed. `DSC:THE-SWEEPER-IS-TCC-BLIND-TO-THE-LARGEST-INTERNAL-
WORKTREE-POOL`.

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
2. **Reap `…/agent-workspaces/tmp` at the mint site — SHIPPED 2026-09-28.** 9 trees, 78% FULL,
   mean 4.79 GiB: machine-generated `contract-delta` base checkouts, the worst per-tree offender
   on the host and the easiest to fix. `scripts/check_contract_delta.py`'s `materialize_base_tree`
   mints one per gate run with `git worktree add --detach` into `base_tree_temp_root()` and removes
   it in a `cleanup()` callable — which never runs when the process is SIGKILLed. Its own docstring
   had recorded the loop for weeks: "wave-2 freed 184 GB of them; it was gone again in ~9 h".
   Measured over six days before the fix: **12 registered leaks / 43.1 GiB plus 8 unregistered /
   15.7 GiB — ~7 GiB/day, regenerating.**

   **The killer is a LOCAL run, not CI — verified 2026-09-28, and it decides where to look.**
   `main()` already converts SIGTERM into an exception precisely so a cancelled CI job unwinds
   and removes its tree, so the surviving leak is specifically the unhandleable SIGKILL. But the
   bytes on this host cannot be CI's at all: the `contract-delta` job runs `ubuntu-latest`, and
   `base_tree_temp_root()` returns the SSD path only while `os.path.ismount()` is true for the
   policy mount — false on every hosted runner, whose own leaked tree then evaporates with the
   VM. The measured trees are minted by fleet sessions running the gate locally to pre-check a
   PR, which is what the external-volume placement exists for. Confirmed on the three leaks that
   had regenerated by the afternoon of 09-28: their gitfiles pointed at
   `/Volumes/Mastermind/tmp/sol-7677-reconcile-20260922-0447` (x2) and
   `/private/tmp/theme7664-current-base.jQA5lM` — local clones, not runner workspaces. So
   "tune the CI timeout" is the wrong response to this leak, and the reaper is correctly placed:
   a local run is both the miner and, now, the collector.

   **Nothing else could ever have collected it, for two independent reasons**, which is why the fix
   belongs at the mint site and not in the sweeper: the directory sits outside every configured
   `root`, AND — even if a root were added — it is refused by the host-checkout belt, because a
   `contract-delta-base-*` path matches no repo-relative session-root segment (the finding above).
   `materialize_base_tree` now calls `reap_stale_base_trees()` **before** it mints, so the process
   that creates the leak is the one that collects it. Safety shape: only names carrying the
   `contract-delta-base-` prefix it mints itself; only entries whose own mtime is older than the
   window (default 6 h, `CONTRACT_DELTA_REAP_HOURS`, off via `CONTRACT_DELTA_NO_REAP`) so a
   concurrent run's tree is never taken; at most 8 per invocation so a huge backlog drains over
   several runs instead of stalling one gate; every failure swallowed, because cleanup must never
   fail the gate. It also unlocks and prunes registrations whose directory is already gone — a
   plain prune SKIPS a locked worktree, which is how 13 content-free `initializing` stamps pinned
   dead registry entries permanently.
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
| 1 | widen `roots` — **to subtrees, not volumes** | add `/Volumes/Mastermind/agent-workspaces/claude` (the policy-mandated seat root) and optionally `…/agent-workspaces/tmp`. **Do NOT add `/Volumes/Mastermind/worktrees`, `…/agent-workspaces` itself, `…/sol` or `…/review`.** | **REVISED 2026-09-28: smaller than stated — an absolute root cannot enter `rel_roots`, so every tree it reaches is classified a host checkout and refused by the belt. Measured: `in_scope` 225→721, belt-reachable 225→**226**. The subtree discipline is still correct, but it is now a REPORTING widening, and the web population's protection is the accidental naming heuristic, not this list** (`DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`) | **~0 on its own** (1 tree, and only because it carries its own `.claude/worktrees` segment); it is the precondition for gate 2 but no longer sufficient — gate 2 now needs host detection to follow `roots` as well |
| 2 | stop treating a content-free lock as operator intent | CODE in `scripts/worktree_gc.py`: a new opt-in config key (default = today's behaviour, honour every lock) exempting only the two provably content-free reasons, **plus** `git worktree unlock` before the `remove --force` at line ~706 | touches `scripts/**`, the CI-authority inventory — a merged head there triggers the authority freeze, clearable only by a green `ci.yml` on a main descendant | 41 trees / 26.6 GiB, all under `…/agent-workspaces/claude`, and it ends the permanent exemption of the whole external-SSD population |

**Gate 2 carries essentially all of the safe yield, and gate 1 is its precondition** — the belt
at line ~682 still refuses a path outside `roots`, and every one of gate 2's 41 trees lives
under `…/agent-workspaces/claude`.

**CORRECTED 2026-09-28 — a THIRD gate sits between these two and neither works without it.**
Gate 1 was described here as worth 6.8 GiB by itself; measured, it is worth ~0, because the
host-checkout belt refuses every absolute-rooted path before `roots` is consulted at all
(§9, “FALSIFIED 2026-09-28”). Gate 2's 41 trees all live under `…/agent-workspaces/claude`,
which is exactly the population the belt calls a host — so unlocking a content-free lock and
adding the root both leave the tree just as undeletable. The missing gate is
**session-tree detection following the configured roots** instead of a hardcoded relative-path
pattern, and it is the DANGEROUS one: it is the single change that would convert the accidental
protection of 527 human-driven SSD checkouts into nothing. It must not be taken without the
`human_driven_roots` deny-list in the same commit. None of the three is a consequence of the
2026-09-27 signal correction; do not infer authorization from it.

**A cheaper fix is implied by the table above:** the GC has no notion of an attachment class,
so nothing in it ever asks whether a human is attached to a checkout. This paragraph read,
until 2026-09-28, that "the only thing standing between an armed deleter and the web population
is the `roots` list being accidentally narrow."

**Refined 2026-09-28: there are TWO such things, and both are accidents.** The `roots` list is
the outer one; the inner one is the host-checkout belt, which refuses every absolute-rooted
path regardless of `roots` (§9, "FALSIFIED 2026-09-28"). That makes the protection sturdier
today than this document claimed — and the conclusion STRONGER, not weaker, because the inner
belt is a naming heuristic whose entire purpose is something else (keeping the sweeper from
deleting the checkouts it sweeps from), and the obvious repair to make gate 1 work is precisely
the change that removes it. A `human_driven_roots` deny-list honoured ahead of every other
verdict is what turns two coincidences into one decision, and it is the thing to ratify FIRST:
it is the only item here that is purely protective, so it needs no yield to justify it and it
cannot delete anything.

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

