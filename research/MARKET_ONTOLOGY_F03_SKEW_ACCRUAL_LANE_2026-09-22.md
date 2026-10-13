# MO-A3 W2-2 — ThetaData skew-accrual lane install runbook

**Lane:** MO-PAID-013 / F03-OPTIONS-EXPRESSION
**Packet:** A-F03-W2-2 (claude/mo-a-3-a-f03-w2-2-skew-accrual-lane)
**Date:** 2026-09-22
**Author:** META-CEO A seat, packet builder
**Companion DEC:** `agentos/decisions/DEC-SKEW-ACCRUAL-ON-THE-STORE-HOST.md`

---

## 1. What this lane is

The ThetaData skew-accrual lane (W2-2) is the **store-host producer** that
feeds the options-skew forward ledger (MO-PAID-013 F03).

```
                     ┌─────────────────────────────────────┐
                     │  M1 ops host (theta-ops-wt on disk) │
                     │  /Users/chriswong/                  │
                     │    theta-ops-wt/data/thetadata_eod/ │
                     │    (60 GB, 380 roots, 2012→2026)    │
                     └────────────────┬────────────────────┘
                                      │ read
                                      ▼
        ┌───────────────────────────────────────────────────┐
        │  launchd com.macro.skewaccrual                    │
        │  ProgramArguments:                                │
        │    run_with_env.sh                                │
        │      skew-ops-wt/.env                             │
        │      run_skew_accrual.sh                          │
        └────────────┬─────────────────────┬───────────────┘
                     │                     │
       step 1: git fetch + checkout ─detach│  step 2: freshness gate (SPY eod)
                     │                     │
                     ▼                     ▼
            ┌────────────────────────────────────┐
            │ step 3: python -m scripts.         │
            │   build_options_skew --accrue      │
            │   (W2-1b flag)                    │
            │ → appends to data/options_skew/   │
            │   snapshots.parquet (source-      │
            │   stamped canonical-wins)         │
            └────────────────┬───────────────────┘
                             │
                             ▼
                ┌────────────────────────────────┐
                │ step 4: python -m scripts.     │
                │   publish_r2 --dirs            │
                │   options_skew                │
                │   (writes manifest every run) │
                │ → data/options_skew/ on R2     │
                │   key prefix: options_skew/    │
                └──────────────┬─────────────────┘
                               │
                               │ (W2-3, future cutover)
                               │   python -m scripts.fetch_r2 --dirs options_skew
                               │   → restores ledger into render hosts'
                               │     data/options_skew/, where
                               │   --emit writes site/options_skew/latest.json
                               ▼
```

### 1.x Which session the lane accrues (seat ruling 2026-09-23)

The store writes TWO different panels for two different sessions. The lane
must accrue the FULL panel, never the partial one:

- **Early priority set (~04:30 local)**: a 12-root priority set for the
  newest calendar date `D`. This is the panel the lane WOULD pick if it
  naively used `max(date)` across the greeks tier.
- **T1 daily maintainer (13:20 / 14:30 / 16:00 / 18:00 local)**: the FULL
  panel (372-378 roots) for `S = nyse_calendar.session_n_back(D, 1)` —
  the session BEFORE the last completed one. The manifest
  `_manifest.json` carries `daily_refresh.S` and `daily_refresh.greeks_S_roots`
  so the lane can confirm the maintainer ran.

The lane LAGS the store's early set by one session BY DESIGN — the live
emit reads the FULL S panel, not the partial D panel. Measured 2026-09-23
on the store host: 48 roots through 2026-08-20, 372-378 roots from
2026-08-21 to 2026-09-21, 12 on 2026-09-22.

**Resolver rule** (`engine/options_skew.complete_store_session`):
two sources are consulted and the newer ISO date wins; `method` is
`"manifest"` when the manifest value tied or won, `"breadth"` otherwise.

| Source | Definition |
|--------|------------|
| `breadth_session` | The NEWEST date whose distinct greeks root count is at least `_COMPLETE_SESSION_MIN_FRACTION` (0.5) of the widest panel |
| `manifest_session` | `daily_refresh.S` when it is a 10-char ISO date AND `daily_refresh.greeks_S_roots` is at least the same fraction of the widest panel (or `>= 1` when the store is empty) |

The chosen session is what `load_chain()` defaults to when called without
an explicit argument; the partial newest date is named in a single
`::notice title=options-skew-session::` line. Note: the notice fires only
on `load_chain()`'s default-asof path (gate/snapshot callers) — the
`--accrue` lane calls `backfill_from_store`, which uses the explicit-asof
path. The lane's own evidence of the skip is its `accrual sessions=[…]`
log line (the dates it actually wrote to), not a separate `::notice` line.

**Catch-up cap** (`engine/options_skew.catch_up_sessions`):
`scripts.build_options_skew --accrue` does not just write today's session —
it walks NYSE sessions BACKWARD from the complete store session to the
ledger's newest COMPLETE thetadata session (exclusive), and calls
`backfill_from_store` on every date in that range, capped at
`_CATCH_UP_MAX_SESSIONS` (5) dates. A caught-up ledger backfills zero rows.
Juneteenth / weekends / holidays are skipped by `session_n_back`.

**Emit guard** (`engine/options_skew.emit_from_ledger`):
the per-date row counts in the ledger are walked newest-first; any date
whose row count is below `_THIN_SESSION_MIN_FRACTION` (0.5) of the widest
count among the up-to-10 dates immediately older than it is dropped, and
the skipped dates are reported in
`source_detail["partial_sessions_skipped"]` / `partial_rows_skipped` (always
present, possibly empty/zero).

**Diagram correction**: the §1 ASCII diagram's step 3 says
`scripts.build_options_skew --accrue` "appends to data/options_skew/
snapshots.parquet" without naming the catch-up walk. The arrow under that
step is the FULL catch-up: today's complete session AND every missed
session between it and the ledger's newest complete session, up to the cap.
A caught-up ledger's arrow is a single no-op.

**Older holes** beyond the cap (a 6+ session outage, a holiday stretch)
are the seat-owned repair: `python -m scripts.build_options_skew
--backfill FROM TO` (the §3.7 runbook), then publish per §3.8.
`backfill_from_store` already replaces `polygon_gex` rows with `thetadata`
rows for the same `(date, underlying)` and skips weekends, so the command
is the durable repair.

## 2. Sequencing law (FROZEN — DO NOT REORDER)

| Wave | Branch | Owns |
|------|--------|------|
| **W2-1b** (sibling, in flight) | `claude/mo-a-2-a-f03-w2-1` | `scripts/build_options_skew.py --accrue \| --emit` + source-stamped ledger upsert; pins render hosts to the legacy source |
| **W2-2** (THIS packet) | `claude/mo-a-3-a-f03-w2-2-skew-accrual-lane` | The producer: launchd job, runner, gate helper, audit tool, R2 registry entry |
| **W2-3** (later) | TBD | Render cutover to `--emit`; `fetch_r2 --dirs options_skew` restore |

The render hosts stay pinned to `polygon_gex` (legacy) until W2-3. This packet
does NOT touch `engine/options_skew.py`, `scripts/build_options_skew.py`, or
any workflow step — it adds files and tests, and registers a directory in
`publish_r2._DATA_DIRS`. Live behavior is unchanged.

## 3. Install runbook (seat executes on the M1 ops host)

### 3.1 Create the dedicated lane checkout

The M1 ops host has two existing checkouts that **must not** carry the lane:

- `flow-ops-wt`: detached at 2026-07-17, 7,985 commits behind, 395 files
  modified — stale AND dirty.
- `theta-ops-wt`: on main@08-23, 26k dirty entries — current but dirty.

The lane needs a clean-tree check (`git status --porcelain` empty) on every
run, and the runner refreshes its own checkout. The dedicated checkout is the
canonical surface that satisfies both requirements:

```sh
# As the mac user who owns the M1 ops host (NOT root).
# ORIGIN MUST BE GITHUB, never a local checkout (seat correction 2026-09-22,
# W2-3): the runner's `git fetch origin && git checkout --detach origin/main`
# follows whatever `origin` names, and a clone taken from a local repo root
# makes `origin/main` that root's stale LOCAL main (theta-ops-wt sits at
# 08-23), so the lane would never see a merged change. Blobless + a
# dissociated reference to the existing clone keeps the object download
# small (~305 MB measured) without leaving an alternates dependency.
export GIT_TERMINAL_PROMPT=0
git clone --filter=blob:none --no-checkout --origin origin \
    --reference-if-able /Users/chriswong/theta-ops-wt --dissociate \
    https://github.com/mastermindx-market-intelligence/macro.git \
    /Users/chriswong/skew-ops-wt
cd /Users/chriswong/skew-ops-wt
git sparse-checkout init --cone
git sparse-checkout set engine scripts lib config ops data/options_skew
git checkout --detach origin/main
git remote get-url origin   # must print the github.com URL
# data/options_skew IS sparse-included: the launchd job writes the parquet
# there and the publish_r2 leg reads it. The other 87% of `data/` (3.31 GiB of
# 3.8 GiB repo) stays out of the checkout per the R8 sparse policy
# (scripts/worktree_sparse.py).
```

### 3.2 Stage the .env file

**Seat install 2026-09-22 (what was actually done):** the M1 producers already
run through `ops/launchd/run_with_env.sh /Users/chriswong/flow-ops-wt/.env`,
and that file carries every key this lane needs (`R2_ENDPOINT`,
`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `THETADATA_STORE`,
`THETA_API_KEY`, `GITHUB_TOKEN` — names only; values never leave the host).
The lane checkout's `.env` is therefore a symlink, not a second secret file:

```sh
ln -sfn /Users/chriswong/flow-ops-wt/.env /Users/chriswong/skew-ops-wt/.env
```

`.env` is gitignored and the runner's `git clean -fd` carries no `-x`, so the
symlink survives every refresh. Stage a standalone file (below) only on a host
without an existing producer env.

Required keys (names only — values live in 1Password / the operator's
secrets manager, never in the repo):

```sh
install -m 0600 /dev/null /Users/chriswong/skew-ops-wt/.env
cat >> /Users/chriswong/skew-ops-wt/.env <<'EOF'
R2_ENDPOINT=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
THETADATA_STORE=/Users/chriswong/theta-ops-wt/data/thetadata_eod
THETA_API_KEY=
GITHUB_TOKEN=
EOF
chmod 0600 /Users/chriswong/skew-ops-wt/.env
```

THETADATA_STORE points at the canonical store path on the M1 host. The
plist also pins it in `EnvironmentVariables` as a belt-and-suspenders for
the freshness-gate Python snippet (the .env value wins because
`run_with_env.sh` exports it first).

### 3.3 Install the plist

```sh
# The plist's StandardOutPath/StandardErrorPath live under the sibling state
# dir. launchd opens those log files BEFORE it executes the runner and does
# not create parent directories, so the logs dir must exist at install time
# (the runner's own `mkdir -p` only runs once launchd has already started it).
mkdir -p /Users/chriswong/skew-ops-state/logs

cp /Users/chriswong/skew-ops-wt/ops/launchd/com.macro.skewaccrual.plist \
   ~/Library/LaunchAgents/

# launchctl bootstrap (the modern macOS command; load is deprecated on
# recent macOS for per-user agents in the Aqua session).
launchctl bootstrap gui/$(id -u) \
    ~/Library/LaunchAgents/com.macro.skewaccrual.plist

# Verify
launchctl print gui/$(id -u)/com.macro.skewaccrual | head -40
```

The plist is OFF by default until this command runs. Once bootstrapped, it
fires weekdays at **05:30 LOCAL** (= 13:30Z during PST / 12:30Z during PDT,
both safely AFTER the observed 11:30Z ThetaData EOD refresh year-round).
launchd has no UTC mode; the local time is the tightest safe point that
buys at minimum one hour of headroom on either side of the DST switch.

**Round-6 log destinations (sibling state dir):** the plist's
`StandardOutPath` and `StandardErrorPath` point at
`/Users/chriswong/skew-ops-state/logs/skewaccrual.{stdout,stderr}.log` —
the SAME `$SKEW_STATE_DIR` default the runner uses (`/Users/chriswong/skew-ops-state`).
launchd paths are literal (no env-var expansion), so the destination is
hardcoded to the default. If you override `SKEW_STATE_DIR` at install time
to a non-default path, also update `StandardOutPath` and `StandardErrorPath`
in the plist to match — otherwise launchd writes to the default path while
the runner reads from your override, and the operator-actionable tail
(`tail -f $SKEW_STATE_DIR/logs/skewaccrual.stdout.log`) misses the launchd
log entirely. The logs directory MUST exist before `launchctl bootstrap`
(the `mkdir -p /Users/chriswong/skew-ops-state/logs` line above): launchd
opens `StandardOutPath`/`StandardErrorPath` before it executes the runner
and never creates parent directories, so a missing dir fails the very first
scheduled launch before `run_skew_accrual.sh` gets to run its own
`mkdir -p "$STATE_DIR" "$STATE_DIR/logs"` (which covers every LATER run and
any `SKEW_STATE_DIR` override the runner sees).

### 3.3b Seed R2 once before the first run (seat correction 2026-09-22, W2-3)

`scripts/fetch_r2.py` exits 1 on `ZERO objects under options_skew/ on R2`,
and `step_hydrate_ledger` refuses to accrue or publish on any non-zero
hydrate — so a fresh bucket can never be bootstrapped by the runner itself.
Publish the committed bootstrap ledger ONCE from the lane checkout before
the first run (the `options_skew` floor in `scripts/publish_r2.py` clears on
this bootstrap — pinned by
`tests/test_skew_accrual_launchd.py::test_publish_r2_options_skew_floor_clears_actual_bootstrap`):

```sh
cd /Users/chriswong/skew-ops-wt
ops/launchd/run_with_env.sh .env \
    /opt/homebrew/Caskroom/miniconda/base/bin/python -m scripts.publish_r2 --dirs options_skew
# Prove the hydrate now succeeds (rc=0) before installing the plist:
ops/launchd/run_with_env.sh .env \
    /opt/homebrew/Caskroom/miniconda/base/bin/python -m scripts.fetch_r2 --dirs options_skew
```

Measured on the seat install 2026-09-22: seed → `options_skew hydrated from
R2 (rc=0)` on the very next runner start, `pre-accrue row count: 12375`.

### 3.4 First-run smoke (dry-run)

The runner reads its env exactly the way launchd does — through the wrapper —
so use the wrapper rather than `source`-ing the file into an interactive
shell (nothing below prints a secret):

```sh
# Dry-run: skip the freshness wait loop AND skip the publish_r2 leg.
# The ledger WILL accrue locally; the only thing skipped is the R2 upload.
/Users/chriswong/skew-ops-wt/ops/launchd/run_with_env.sh /Users/chriswong/skew-ops-wt/.env \
    /usr/bin/env SKEW_FRESHNESS_BYPASS=1 SKEW_DRY_RUN=1 \
    /Users/chriswong/skew-ops-wt/ops/launchd/run_skew_accrual.sh
```

Expected line-start receipts on stdout (every step emits one):

```
[<UTC>] skew_accrual: starting skew_accrual: repo=... store=... bypass=1 dry_run=1
[<UTC>] skew_accrual: checkout refreshed — HEAD=...
[<UTC>] skew_accrual: SKEW_FRESHNESS_BYPASS=1 — skipping freshness gate
[<UTC>] skew_accrual: launching python -m scripts.build_options_skew --accrue
[<UTC>] skew_accrual: accrue completed
[<UTC>] skew_accrual: SKEW_DRY_RUN=1 — skipping publish_r2 (ledger written locally only)
[<UTC>] skew_accrual: done
```

### 3.5 First-run with publish (full)

After the dry-run exits 0, drop the dry-run flag to publish:

```sh
/Users/chriswong/skew-ops-wt/ops/launchd/run_with_env.sh /Users/chriswong/skew-ops-wt/.env \
    /usr/bin/env SKEW_FRESHNESS_BYPASS=1 \
    /Users/chriswong/skew-ops-wt/ops/launchd/run_skew_accrual.sh
```

The publish leg runs `python -m scripts.publish_r2 --dirs options_skew`
with no manifest flag. The M1 ops host holds the FULL
`data/options_skew/` tree (snapshots.parquet + tracked sidecars), so
the publish_r2 manifest guard's shrink-guard cannot trip on a full
tree. Every run writes a real manifest, which is what bulk consumers
(`fetch_r2` / `audit_r2`) read for the freshness anchor.

### 3.6 Uninstall

```sh
launchctl bootout gui/$(id -u) \
    ~/Library/LaunchAgents/com.macro.skewaccrual.plist
rm ~/Library/LaunchAgents/com.macro.skewaccrual.plist
```

### 3.7 One-time backfill (seat act)

Section 3.6 above is Uninstall. This step is the one-time backfill. It is
not on the daily schedule. Run it inside the lane checkout, after the ledger
has been copied down, and then publish that directory. Keep the one-line
JSON receipt the command prints.

Hydrate first:

```sh
cd /Users/chriswong/skew-ops-wt
ops/launchd/run_with_env.sh .env \
    /opt/homebrew/Caskroom/miniconda/base/bin/python -m scripts.fetch_r2 --dirs options_skew
```

Recompute the covered legacy window from the store. A thetadata row replaces
a polygon_gex row for the same date and name. Weekend dates are skipped.

```sh
cd /Users/chriswong/skew-ops-wt
/Users/chriswong/skew-ops-wt/ops/launchd/run_with_env.sh /Users/chriswong/skew-ops-wt/.env /usr/bin/env THETADATA_STORE=/Users/chriswong/theta-ops-wt/data/thetadata_eod python -m scripts.build_options_skew --backfill 2026-06-21 2026-08-13
```

Publish the ledger, then copy the printed JSON receipt into the state
directory (for example
`/Users/chriswong/skew-ops-state/receipts/skew-backfill-2026-06-21_2026-08-13.json`).

```sh
cd /Users/chriswong/skew-ops-wt
ops/launchd/run_with_env.sh .env \
    /opt/homebrew/Caskroom/miniconda/base/bin/python -m scripts.publish_r2 --dirs options_skew
```

### 3.8 Restore the shared checkout after ANY manual session (seat correction 2026-09-23)

Every manual step in §3.4–§3.7 runs inside `/Users/chriswong/skew-ops-wt`, the
checkout BOTH launchd lanes (`com.macro.skewaccrual`, `com.macro.payofflab`)
refresh at the start of every run. A manual hydrate/backfill leaves the tracked
`data/options_skew/snapshots.parquet` MODIFIED and a dry-run leaves
`data/options_payoff_lab/` untracked. Measured 2026-09-23 12:30Z: the scheduled
accrual aborted at `step_refresh` ("git checkout --detach origin/main failed —
refusing to run") because the runner detached BEFORE its own reset/clean and git
refused to overwrite the dirty tracked file; the day's session would have been
silently skipped. The runners now reset/clean before the detach as well
(2026-09-23 hardening), but the manual discipline stands — finish every seat
session in that checkout with:

```bash
cd /Users/chriswong/skew-ops-wt
git fetch origin && git reset --hard && git clean -fd && git checkout --detach origin/main && git reset --hard && git clean -fd
git status --short | wc -l   # must print 0
```

The durable state is on R2 (`publish_r2 --dirs options_skew`), never in this
checkout, so discarding local bytes loses nothing once the publish step has
run. Recovery when a scheduled run has already aborted: restore the checkout as
above, then `launchctl kickstart gui/$(id -u)/com.macro.skewaccrual` (same
receipt log) — the accrual is idempotent for the session it targets.

## 4. Reading the receipt log

The plist's `StandardOutPath` is
`/Users/chriswong/skew-ops-state/logs/skewaccrual.stdout.log`,
`StandardErrorPath` is
`/Users/chriswong/skew-ops-state/logs/skewaccrual.stderr.log` — the same
`$SKEW_STATE_DIR` default the runner uses (round-6 amendment; was
`/tmp/skewaccrual.*.log` in round 1). Every receipt line starts with
`[<UTC>] skew_accrual: ...` so a `grep '^\\[.*\\] skew_accrual:'` narrows
the stream to the lane's own log lines. The launchd pair captures the
WHOLE process lifetime (ProgramArguments chain → `run_with_env.sh` →
`run_skew_accrual.sh`), so it includes the run_with_env wrapper's
`.env` sourcing output AND the runner's stdout — the runner's own stderr
status lines (`::gate-info::`, `ABORT at step_*`) are interleaved on the
runner-stderr file under `$STATE_DIR`, not on the launchd stderr file;
tail BOTH when chasing a failure.

Failure receipts name the failing step explicitly:

| Receipt | Meaning | Remediation |
|---------|---------|-------------|
| `ERROR: dedicated checkout ... is dirty` | A sibling session left edits in the checkout | Re-clone via the install runbook; the runner NEVER pushes so a dirty tree is always foreign |
| `ERROR: git fetch origin failed` | Network blip / GitHub rate limit | Wait 5 min and let the next scheduled launchd retry fire (ThrottleInterval 60) |
| `ERROR: store resolve failed` | THETADATA_STORE points at a tree with no `eod/SPY/<YYYY>.parquet` | Confirm the store path; this is an operator-fixable path problem, NOT a stale-data retry condition |
| `ERROR: store still not fresh after 6 attempts` | ThetaData EOD store did not refresh in 2 h | Check `com.macro.thetadata-r2sync` — that lane is the upstream producer and a missed nightly would cause this |
| `ERROR: --accrue flag is unrecognized` (or W2-1b precheck rc=4) | W2-1b has not landed on `origin/main` yet | Confirm `git ls-remote origin claude/mo-a-2-a-f03-w2-1`; this lane cannot run until W2-1b merges |
| `ERROR: build_options_skew --accrue failed` | Accrue step returned non-zero | Check the builder's own log; the runner does not modify the ledger on a non-zero exit |
| `ERROR: publish_r2 --dirs options_skew failed` | R2 upload rejected (quota? bytes floor?) | Check `scripts/publish_r2._DATA_DIR_MIN_BYTES['options_skew']` (= 10_000) — a bare-tree publish would be refused |

## 5. The audit tool

`scripts/audit_options_skew_overlap.py` measures the real-overlap between
legacy `polygon_gex` rows and the new ThetaData recompute on rows that EXIST
in both. The seat runs this on the M1 after W2-1b merges:

```sh
# Full audit on the live ledger
python -m scripts.audit_options_skew_overlap

# Smoke on the first 50 keys
python -m scripts.audit_options_skew_overlap --limit 50

# Custom ledger / store / output paths
python -m scripts.audit_options_skew_overlap \
    --ledger /Users/chriswong/skew-ops-wt/data/options_skew/snapshots.parquet \
    --store /Users/chriswong/theta-ops-wt/data/thetadata_eod \
    --out research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_2026-09-22.md
```

The tool emits a JSON summary to stdout (keys_compared, sign_agreement_rate,
|delta skew| p50/p90/max, 10 worst keys) AND a markdown receipt at the
`--out` path. Exit codes:

| Exit | Meaning |
|------|---------|
| 0 | Audit ran (even on 0 keys / empty ledger) |
| 1 | MISSING_ENGINE — engine.thetadata_store.make_chain_provider OR engine.options_skew.compute_skew could not be imported |

The MISSING_ENGINE branch is the load-bearing safety property: the audit is
re-runnable on a pre-W2-1b tree without crashing — it reports the gap.

## 6. The DEC record

`agentos/decisions/DEC-SKEW-ACCRUAL-ON-THE-STORE-HOST.md` records the
producer-on-the-M1-store-host choice with three rejected alternatives:

- CI label `m1-theta` (org-level runner; label-cascade risk)
- Git narrow-commit delivery from a stale ops checkout
  (`scripts/launchd/theta_surface_accrual.sh` — dead precedent; plist not
  loaded on the host)
- Hydrating the ~60 GB ThetaData store to render hosts (breaks the 67-min
  render budget AND would race the WP-RESOLVER empty-stub branch)

Confidence is high; reversibility is easy (delete the plist + the dedicated
checkout). The decision date is 2026-09-22.

The DEC record's evidence block is the load-bearing test-count quote the
seat and the runner reference. The round-6 amendment (commit `d8eb9219bc`)
refreshed the count from 71 → 73 and named the two round-6 test additions
explicitly (`test_plist_log_paths_live_outside_repo_in_sibling_state_dir`
for MAJOR-1, `test_run_with_env_wrapper_exists_on_origin_main` for
MINOR-1) so the DEC record's evidence block matches the pytest tail in the
PR body and the §7 test-surface table above. Without that refresh the DEC
record would claim 71 while the suite reports 73 — a discrepancy the
seat-install runbook's §1 install-receipt would surface.

The PR body for this lane carries a "Round 6/N Meta-CEO A seat — fixes
applied this round" table that names every round-6 commit by hash; the
§9 amendments table above is the runbook-side mirror of that body table.
If the two ever disagree (runbook newer than body, or vice versa), the
PR body is the source of truth — the body is updated LAST after every
push, while the runbook lands in named-file commits.

## 7. Test surface

All tests use `tmp_path` fixtures only — no real store / R2 / network access.

| File | Asserts |
|------|---------|
| `tests/test_skew_accrual_gate.py` | `scripts/skew_accrual_gate.py` resolves fresh / stale / resolve-error / usage-error paths against a synthetic `eod/SPY/<YYYY>.parquet`; respects `--required-date` override; respects T+1 floor (T-1 calendar) |
| `tests/test_skew_accrual_launchd.py` | Plist parses (plutil), pins runner path / env keys / schedule (Hour==5 after BLOCKER-4 fix); runner script `sh -n` clean; ProgramArguments chain resolves to files that will exist in the dedicated checkout; refresh-checkout refuses on a dirty / stale tree; freshness gate retry loop honours bypass; precheck step fails loud (rc=4) when `--accrue` is unknown; accrue step fails loud (rc=1) on a non-zero exit; verify-ledger step fails loud (rc=5) on missing/empty ledger; publish step fails loud (rc=1) on a non-zero exit; dry-run skip publish_r2; happy-path emits the documented line-start receipts; round-5 B2 cure: two-run cycle admitted via real `git init` + `runstate_files_live_outside_repo` prove the B2 state-dir split; round-6: `test_plist_log_paths_live_outside_repo_in_sibling_state_dir` pins the MAJOR-1 launchd pair under `$SKEW_STATE_DIR` (and proves neither lives inside `$REPO`), `test_run_with_env_wrapper_exists_on_origin_main` pins the MINOR-1 wrapper the plist's ProgramArguments chain references |
| `tests/test_skew_accrual_precheck.py` | RED-first tests for the W2-1b precheck helper: detects/accepts the literal `'--accrue'` token in `scripts/build_options_skew.py` source; refuses a docstring-only mention; CLI exit codes are load-bearing (0=ok, 4=flag-missing) |
| `tests/test_skew_accrual_verify_ledger.py` | RED-first tests for the post-accrue ledger verifier: refuses missing/empty/zero-row parquets; exit codes are load-bearing (0=ok, 5=no-ledger) |
| `tests/test_audit_options_skew_overlap.py` | Synthetic ledger + synthetic chain provider produces expected agreement numbers and the markdown receipt; `--limit N` caps the input; MISSING_ENGINE branch reports without crashing; bare/empty ledger reports honestly |

## 8. What this packet did NOT change

- `engine/options_skew.py` (W2-1b owns)
- `scripts/build_options_skew.py` (W2-1b owns)
- Any `.github/workflows/*.yml` step (verified: `git diff --stat origin/main
  HEAD -- .github` is empty)
- `data/` (sparse tree — no write)
- `site/` (sparse tree — no write)
- Any other PR (in particular #6923 / branch `claude/mo-a-2-a-f03-w2-1`,
  which this packet READS but never writes)

## 9. Round-6 amendments (Meta-CEO A binding ruling, 2026-09-22)

The round-6 binding ruling audited the round-5 head (`d61d200c72`) and
named one MAJOR-1 finding (launchd logs in `/tmp`), one MAJOR-2 finding
(strong sys.path pin missing in 3 entry scripts), and one MINOR-1 finding
(no test pins the existence of `ops/launchd/run_with_env.sh` on
`origin/main`). All three were cured with named-file commits:

| Finding | Commit | Change |
|---------|--------|--------|
| **MAJOR-1** launchd logs to sibling state dir | `50c494e2ef` | `StandardOutPath`/`StandardErrorPath` in `ops/launchd/com.macro.skewaccrual.plist` redirected from `/tmp/skewaccrual.{stdout,stderr}.log` to `/Users/chriswong/skew-ops-state/logs/skewaccrual.{stdout,stderr}.log` — the same `$SKEW_STATE_DIR` default the runner uses. launchd paths are literal (no env-var expansion), so the destination is hardcoded to the default; an operator override of `$SKEW_STATE_DIR` must update both keys (see §3.3 above). |
| **MAJOR-1 test** | `8425a434d7` | New test `test_plist_log_paths_live_outside_repo_in_sibling_state_dir` pins BOTH the destinations match the runner's default AND that neither path starts with `/Users/chriswong/skew-ops-wt/` (the dedicated lane checkout the runner's `git reset --hard && git clean -fd` wipes on every run). |
| **MAJOR-2** strong top-level sys.path pin | `9d55fcd1dd` | `scripts/skew_accrual_precheck.py` and `scripts/skew_accrual_verify_ledger.py` now carry the exact named-form pin (`_ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(_ROOT))`) at module load. `scripts/audit_options_skew_overlap.py`'s one-liner pin was refactored to the named form. `test_unpinned_entry_scripts_only_shrink` stays green — three new pins shrink the affected set. |
| **MINOR-1** run_with_env.sh existence | `8425a434d7`, `77c5a73c54` | New test `test_run_with_env_wrapper_exists_on_origin_main` runs `git ls-tree origin/main -- ops/launchd/run_with_env.sh` and asserts a 100755-mode entry exists. CI-widening commit extends the `skew-accrual-lane` job's `paths:` to cover `ops/launchd/run_with_env.sh` so wrapper edits actually trigger the job. |

The DEC record test count was refreshed from 71 to 73 (commit `d8eb9219bc`)
to match the pytest tail in the PR body. The install-runbook §3.3 paragraph
above (commit `0954661a4f`) documents the round-6 sibling-state-dir log
destination change at the seat-install level.

## 10. Caught-up no-op (holiday / re-landed session) — A-F03-W2-8 (2026-09-23)

Placed at the end of this doc by seat ruling (A-F03-W2-8 seat round 4,
2026-09-23): the §2 runner step list is the numbered contract and stays
untouched; the caught-up case is a behavior appended here.

**The case.** On a Mon-morning invocation where Friday's complete session
S is already on the ledger, or a holiday-rerun where the maintainer's
backfill range resolves to a session the ledger already carries byte-for-byte,
`scripts/build_options_skew.py --accrue`'s underlying receipt carries
`rows_added=0 AND rows_replaced=0` from `engine.options_skew.backfill_from_store`.
That case is the **caught-up no-op** — the daily maintainer wrote zero
rows because the ledger was already current.

**Why a dedicated exit code.** Pre-W2-8, a zero-row backfill fell
through to `main()`'s rc 0 default, indistinguishable from a fresh
session write that also landed 0 rows because the chain parsed empty.
The runner then ran the verify + publish leg (BLOCKER-2 would refuse the
publish, ABORT at the verify step with rc 5 — see
`ops/launchd/run_skew_accrual.sh::step_verify_ledger`). That was a
`2.2:00 PM` lane fault: holiday Mondays logged an "ABORT at verify"
line for a perfectly fine ledger. The fix is a distinct exit code
from `--accrue`-only so the runner can branch (one-line receipt +
skip verify + skip publish + exit 0) WITHOUT touching the verify
helper's BLOCKER-2 rule (that rule still refuses a no-op under the
sole-leg `--emit` call where the ledger did not grow). The runner
only invokes `--accrue` (`ops/launchd/run_skew_accrual.sh` step 6), so
BLOCKER-2 only ever fires under the `--accrue` leg it actually runs;
an `--emit`-only caller (the render hosts) is the regional-desk flow
the rc-3 branch deliberately does NOT touch.

**The contract.** The constant is `ACCRUE_NOOP_EXIT = 3` in
`scripts/build_options_skew.py`. Five callsites read it:

| Callsite | Reads | Behavior |
|---|---|---|
| `scripts/build_options_skew.py::accrue()` | writes `(0, "caught_up")` to `accrual_state` | One `::notice title=options-skew-accrual::caught up — complete session S already on the ledger; nothing to accrue` line at LINE START (the GitHub annotation parser requirement, `tests/test_gh_annotation_line_start.py`). |
| `scripts/build_options_skew.py::emit()` | maps the builder's `caught_up` vocabulary to the engine's legacy `ledger_only` vocabulary | The on-disk payload `accrual_state` stays `ledger_only` (the engine contract `emit_from_ledger` raises on any value outside `accrued_today \| ledger_only`). The mapping happens in the BUILDER, not the engine. |
| `scripts/build_options_skew.py::main()` | returns `ACCRUE_NOOP_EXIT` when `do_accrue AND NOT do_emit AND NOT do_backfill AND accrual_state == "caught_up"` | The rc-3 surface is STRICTLY `--accrue` alone. `--accrue --emit` and `--backfill …` keep exiting 0 / 2 — render hosts and regional desks keep seeing rc 0 on a caught-up ledger. |
| `ops/launchd/run_skew_accrual.sh::step_accrue` | captures rc via `\|\| rc=$?` (not nested `set +e`/`set -e`, which leaks globally in POSIX shell) | rc 3 → log `accrue: NOOP_CAUGHT_UP …`; rc ≠ 0 and ≠ 3 → log `ABORT at step_accrue`, exit 1 (preserves the existing launchd test contract). |
| `ops/launchd/run_skew_accrual.sh` main sequence | branches on `accrue_rc` | `accrue_rc == 3` → log `NOOP_CAUGHT_UP run_tag=… ledger=…` + log `done (caught-up no-op: verify + publish skipped)` + exit 0. Other non-zero → unchanged ABORT. |

**Detection.** The receipt-driven check fires on BOTH conjuncts
`dates and dates_backfilled == len(dates) and rows_added + rows_replaced == 0`.
The original spec language ("`catch_up_sessions(...)` returns `[]`")
does not match the engine: `catch_up_sessions` always returns at least
the target session itself, even on an already-caught-up ledger — the
helper's contract is the date RANGE to walk backwards, not the work to
do inside that range. The receipt is the truthful signal: it reflects
`_backfill_row_counts`'s diff against the prior ledger, which uses dict
equality on the `_normalize_ledger`-projected row. A byte-equal rewrite
reports `rows_unchanged = N, rows_added = 0, rows_replaced = 0`; a
shifted floating-point (e.g. `otm_put_iv=0.4001` vs `0.4`) reports
`rows_replaced = N` and falls through to the ordinary write path.

The `dates_backfilled == len(dates)` conjunct is what excludes the
store-miss failure mode. When the backfill is asked for `[D2]` but the
store's greeks only cover D1, `dates_not_in_store=1, dates_backfilled=0,
rows_added=0, rows_replaced=0` — `rows_added + rows_replaced == 0`
holds but `dates_backfilled == len(dates)` does NOT (0 ≠ 1). The
builder therefore returns the rc-0 path on a store-miss, and the
runner's BLOCKER-2 verify step sees the call and aborts loud — the
exact outcome the round-2 loose rule (`if dates and rows_touched == 0`)
silently broke.

**Ledger-bytes contract unchanged.** The caught-up no-op is byte-for-byte
a no-op on `data/options_skew/snapshots.parquet`. Pre-Rows sidecar
(`.skew_pre_rows.<pid>`) is removed by the runner on the no-op path so
the next run starts fresh. The runner DOES NOT touch the verify ledger
helper (`scripts/skew_accrual_verify_ledger.py`) — that helper still
refuses a non-growth outcome, and a `--emit`-only caller that the
builder marks as caught-up still has BLOCKER-2 in effect (the ledger
did not grow, but `--emit` is a re-render of an existing ledger, not a
publish — the runner never invokes verify on that path).

**Tests.** Four new W2-8 tests are added to existing homes (no CI
exemption rows):

- `tests/test_options_skew.py::test_accrue_sole_leg_exits_3_when_caught_up`
  — seeds D1+D2 with values `compute_skew` would emit for the chain
  (skew=0.10, otm_put_iv=0.40, atm_call_iv=0.30, n_strikes=4); asserts
  `main(["--accrue"]) == 3`, the `::notice` lands at line start, the
  ledger sha is unchanged. The VALUES MATTER: a seed with a different
  skew (e.g. the `0.10 + i*0.001` jitter from the prior tests) is, by
  definition, NOT caught-up and would force the receipt to report
  `rows_replaced > 0`.
- `tests/test_options_skew.py::test_accrue_with_emit_exits_0_when_caught_up`
  — same seed, `main(["--accrue","--emit"]) == 0`, payload
  `accrual_state == "ledger_only"` (the engine vocabulary mapping), every
  seeded name surfaces in the rendered payload (n=6).
- `tests/test_options_skew.py::test_accrue_sole_leg_exits_0_when_a_session_was_written`
  — empty ledger; `--accrue` writes 6 rows for D2 (the complete session
  S, since `catch_up_sessions` returns `[S]` when there is no theta
  history to walk back through); rc stays 0. Pins the symmetric
  behavior — the rc-3 exit is STRICTLY the caught-up case.
- `tests/test_options_skew.py::test_accrue_sole_leg_returns_0_when_store_misses_complete_session`
  — RED on the round-2 head, GREEN on this head. Store greeks cover
  D1 only; manifest claims S=D2 with `greeks_S_roots=6`
  (under `_COMPLETE_SESSION_MIN_FRACTION × widest=0.95×6=5.7`); the
  ledger holds D1 only. `complete_store_session` resolves S=D2 via
  the manifest method; `catch_up_sessions(D2, hist)` returns `[D2]`
  (lone-date "have" rule makes D1 complete); `backfill_from_store([D2])`
  reports `dates_not_in_store=1, dates_backfilled=0, rows_added=0,
  rows_replaced=0`. Without the strict discriminator, the prior
  round's `if dates and rows_touched == 0:` would fire and `main`
  would return rc 3 (caught-up) on a real failure — the runner
  would skip BLOCKER-2 verify and the operator would never see the
  store-miss. With the strict discriminator
  (`dates_backfilled == len(dates)` AND `rows_touched == 0`),
  `main(["--accrue"])` returns rc 0, the receipt's failure signature
  surfaces in the receipt log, and the runner's BLOCKER-2 step sees
  the call.
- `tests/test_skew_accrual_launchd.py::test_runner_caught_up_noop_exits_zero_and_skips_verify_and_publish`
  — FAKE_ACCRUE_NOOP exits 3; asserts rc=0, the `NOOP_CAUGHT_UP` receipt
  line, the verify + publish markers absent, the pre_rows sidecar gone.
- `tests/test_skew_accrual_launchd.py::test_runner_zero_growth_under_a_real_accrue_still_aborts_at_verify`
  — FAKE_ACCRUE_NO_GROWTH exits 0 (a real accrue that just happened to
  add zero rows under a missing chain); asserts rc=5 (ABORT at
  step_verify_ledger) and `NOOP_CAUGHT_UP` absent. Pins that the rc-3
  branch is reserved for the CATCH-UP STATE, not every zero-row
  outcome — a fresh zero-row backfill under a missing chain still goes
  through BLOCKER-2.

**The two-case contract.** A zero-row accrue on a day with a NEW
complete session (the store resolved a fresh S, but the backfill still
returned 0 rows because the chain parsed empty, or the manifest and
the store disagree on coverage) still aborts at step 7
(`step_verify_ledger` → `BLOCKER-2`) — the rc-3 branch is reserved for
the byte-equal CATCH-UP STATE only. Cite: PR #7832 (W2-6
`complete_store_session` resolution + the receipt-driven row diff) and
this PR (PR #7844, A-F03-W2-8 caught-up no-op).

**Why extend, not waive.** `tests/test_skew_accrual_launchd.py` runs on
the `skew-accrual-lane` job and `tests/test_options_skew.py` runs on
the `options-skew-engine` job (verified:
`tests/test_skew_accrual_launchd.py` at `.github/ci/legacy-jobs.yml`
on the `skew-accrual-lane` job, `tests/test_options_skew.py` on the
`options-skew-engine` job), so adding W2-8 cases to those homes
delivers CI coverage without widening the run line — coverage exists
on both jobs either way.
