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
# The repo root is wherever `git rev-parse --show-toplevel` lands for THIS
# macro clone — for the operator's designated local root see CLAUDE.md.
REPO_ROOT="$(git rev-parse --show-toplevel)"
echo "source repo root: $REPO_ROOT"

# Create the dedicated lane checkout off fresh origin/main.
git clone --no-local --no-checkout --origin origin \
    "$REPO_ROOT" /Users/chriswong/skew-ops-wt
cd /Users/chriswong/skew-ops-wt
git checkout --detach origin/main
git config core.sparseCheckout true
git sparse-checkout init --cone
git sparse-checkout set engine scripts lib config ops data/options_skew
# data/options_skew IS sparse-included: the launchd job writes the parquet
# there and the publish_r2 leg reads it. The other 87% of `data/` (3.31 GiB of
# 3.8 GiB repo) stays out of the checkout per the R8 sparse policy
# (scripts/worktree_sparse.py).
```

### 3.2 Stage the .env file

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
log entirely. The directory itself does not need to be created at install
time — the runner's `mkdir -p "$STATE_DIR"` (line 159 of
`run_skew_accrual.sh`) creates it on the first run, and launchd writes
append-style so a missing parent dir is fatal until the first run.

### 3.4 First-run smoke (dry-run)

```sh
set -a
source /Users/chriswong/skew-ops-wt/.env
set +a

# Dry-run: skip the freshness wait loop AND skip the publish_r2 leg.
# The ledger WILL accrue locally; the only thing skipped is the R2 upload.
SKEW_FRESHNESS_BYPASS=1 SKEW_DRY_RUN=1 \
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
set -a
source /Users/chriswong/skew-ops-wt/.env
set +a

SKEW_FRESHNESS_BYPASS=1 \
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

## 4. Reading the receipt log

The plist's `StandardOutPath` is `/tmp/skewaccrual.stdout.log`,
`StandardErrorPath` is `/tmp/skewaccrual.stderr.log`. Every receipt line
starts with `[<UTC>] skew_accrual: ...` so a `grep '^\\[.*\\] skew_accrual:'`
narrows the stream to the lane's own log lines.

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

## 7. Test surface

All tests use `tmp_path` fixtures only — no real store / R2 / network access.

| File | Asserts |
|------|---------|
| `tests/test_skew_accrual_gate.py` | `scripts/skew_accrual_gate.py` resolves fresh / stale / resolve-error / usage-error paths against a synthetic `eod/SPY/<YYYY>.parquet`; respects `--required-date` override; respects T+1 floor (T-1 calendar) |
| `tests/test_skew_accrual_launchd.py` | Plist parses (plutil), pins runner path / env keys / schedule (Hour==5 after BLOCKER-4 fix); runner script `sh -n` clean; ProgramArguments chain resolves to files that will exist in the dedicated checkout; refresh-checkout refuses on a dirty / stale tree; freshness gate retry loop honours bypass; precheck step fails loud (rc=4) when `--accrue` is unknown; accrue step fails loud (rc=1) on a non-zero exit; verify-ledger step fails loud (rc=5) on missing/empty ledger; publish step fails loud (rc=1) on a non-zero exit; dry-run skip publish_r2; happy-path emits the documented line-start receipts |
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