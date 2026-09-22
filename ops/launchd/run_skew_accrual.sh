#!/bin/sh
# ops/launchd/run_skew_accrual.sh
#
# Runner for the ThetaData skew-accrual lane (MO-PAID-013 W2-2 — A-F03-W2-2).
# Invoked by com.macro.skewaccrual.plist via run_with_env.sh.
#
# WHAT THIS LANE DOES
# ─────────────────────────────────────────────────────────────────────────────
# The skew engine (engine/options_skew.py) accrues a per-underlying IV-skew
# snapshot every NYSE session into data/options_skew/snapshots.parquet. Once the
# panel is wide/long enough, scripts/validate_options_skew.py can earn a verdict
# for the skew leg. THIS lane is the ThetaData producer that feeds that ledger.
#
# Sequence law (FROZEN, MO-PAID-013):
#   W2-1b (sibling, in flight on claude/mo-a-2-a-f03-w2-1)
#     ships `scripts/build_options_skew.py` with the accrue flag plus a
#     source-stamped ledger upsert (per-row `source` in {polygon_gex,
#     thetadata}, canonical-wins). W2-1b pins the render hosts to the legacy
#     source so nothing flips prematurely.
#   W2-2 (THIS packet)
#     builds the store-host producer that will feed the ledger via R2. This
#     is the runner — it (1) refreshes the dedicated checkout, (2) gates on
#     the ThetaData EOD store, (3) calls the W2-1b accrue command against the
#     ledger on the store host, (4) publishes the resulting data/options_skew
#     dir to R2 so the W2-3 cutover can flip render hosts to the emit command.
#   W2-3 (later)
#     cuts render over to the emit command. Out of scope here.
#
# Nothing in this packet may change live behavior: it adds files and tests,
# and registers a directory in publish_r2's data-dir registry — it does NOT
# alter any workflow step. The lane is OFF by default (no plist loaded on the
# host) until the seat installs it per the runbook.
#
# FRESHNESS GATE
# ─────────────────────────────────────────────────────────────────────────────
# Before running the accrual, this script verifies that the ThetaData EOD store
# contains SPY data for the expected last NYSE session. The ThetaData EOD store
# is a T+1 plane: at run time it carries the session BEFORE today (observed
# ~11:30Z daily refresh; see ops/launchd/com.macro.thetadata-r2sync.plist). The
# gate reads only the 'date' column of the current-year SPY EOD parquet shard
# (column-pruned; never loads the full store) and asks whether the latest date
# in that shard is at or after the T-1 expected session.
#
# Logic (delegated to scripts/skew_accrual_gate.py so the gate is unit-testable):
#   1. Resolve the store from --store / $THETADATA_STORE.
#   2. Resolve the floor from lib.nyse_calendar.expected_last_session() (T-1).
#   3. Read SPY eod shard's 'date' column.
#   4. If latest >= required → FRESH (gate exit 0).
#   5. Otherwise sleep 20 min and retry (max 6 attempts = 2h window).
#   6. After 6 failures, log and exit 1 without running the accrual.
#
# BYPASS
# ─────────────────────────────────────────────────────────────────────────────
# Set SKEW_FRESHNESS_BYPASS=1 to skip the freshness wait loop and run the
# accrual immediately regardless of store freshness.
#
# DRY-RUN (no publish)
# ─────────────────────────────────────────────────────────────────────────────
# Set SKEW_DRY_RUN=1 to run the accrual WITHOUT the publish_r2 step. The
# ledger is written locally (data/options_skew/snapshots.parquet) but does NOT
# upload to R2. Use this for smoke / integration checks where you want to
# verify the build pipeline without touching live artifacts.
#
# USAGE (smoke — accrues locally, no R2 publish):
#   set -a; source /Users/chriswong/skew-ops-wt/.env; set +a
#   SKEW_FRESHNESS_BYPASS=1 SKEW_DRY_RUN=1 \
#     /Users/chriswong/skew-ops-wt/ops/launchd/run_skew_accrual.sh
#
# USAGE (full — same as the nightly launchd run):
#   set -a; source /Users/chriswong/skew-ops-wt/.env; set +a
#   SKEW_FRESHNESS_BYPASS=1 \
#     /Users/chriswong/skew-ops-wt/ops/launchd/run_skew_accrual.sh
#
# LOG TAILING (when installed as com.macro.skewaccrual):
#   tail -f /tmp/skewaccrual.stdout.log /tmp/skewaccrual.stderr.log
#
# HOST CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────
# The dedicated lane checkout is /Users/chriswong/skew-ops-wt (NOT the M1
# flow-ops-wt or theta-ops-wt trees — both are stale/dirty by design and would
# undermine a "checkout is clean" assertion). The runner refreshes the checkout
# itself before any work: `git fetch origin && git checkout --detach origin/main`
# with a `git status --porcelain` empty check. A dirty or stale checkout is
# REFUSED — that is the lane's load-bearing safety property (a dirty tree would
# publish someone's WIP). The lane NEVER pushes to git; the only outbound is
# publish_r2, and that is gated on the dedup'd ledger contents.

set -eu

# ── paths ─────────────────────────────────────────────────────────────────────
REPO_DEFAULT="/Users/chriswong/skew-ops-wt"
REPO="${SKEW_OPS_ROOT:-$REPO_DEFAULT}"
PYTHON="${SKEW_PYTHON:-/opt/homebrew/Caskroom/miniconda/base/bin/python}"
STORE="${THETADATA_STORE:-/Users/chriswong/theta-ops-wt/data/thetadata_eod}"

log() {
    # One-line receipt at line start — the runbook points operators here.
    printf '[%s] skew_accrual: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

# ── step 1: refresh the dedicated checkout ─────────────────────────────────────
step_refresh_checkout() {
    if [ ! -d "$REPO/.git" ]; then
        log "ERROR: dedicated checkout $REPO does not exist or is not a git worktree"
        log "  → see research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md install runbook"
        return 1
    fi
    cd "$REPO"
    # Belt-and-suspenders: refuse to operate on a dirty working tree. A dirty
    # checkout means a sibling session is mid-edit; publishing from here would
    # race their bytes. The exception is `git status` itself creating noise —
    # untracked entries under the four fleet worktree roots are excluded by
    # ship_loop_guard; we mirror that posture with a stricter surface here.
    dirty=$(git status --porcelain --untracked-files=all 2>/dev/null || true)
    if [ -n "$dirty" ]; then
        log "ERROR: dedicated checkout $REPO is dirty — refusing to run"
        log "  porcelain: $(echo "$dirty" | head -5 | tr '\n' ';')"
        return 1
    fi
    if ! git fetch origin >/dev/null 2>&1; then
        log "ERROR: git fetch origin failed (network? rate limit?) — refusing to run"
        return 1
    fi
    # Detach on origin/main so the next run's fetch does not collide with a
    # local branch that is no longer at HEAD. A detached HEAD is the canonical
    # shape for read-only nightly lanes.
    if ! git checkout --detach origin/main >/dev/null 2>&1; then
        log "ERROR: git checkout --detach origin/main failed — refusing to run"
        return 1
    fi
    log "checkout refreshed — HEAD=$(git rev-parse --short HEAD)"
    return 0
}

# ── step 2: freshness gate ────────────────────────────────────────────────────
step_freshness_gate() {
    if [ "${SKEW_FRESHNESS_BYPASS:-0}" = "1" ]; then
        log "SKEW_FRESHNESS_BYPASS=1 — skipping freshness gate"
        return 0
    fi
    MAX_ATTEMPTS=6
    SLEEP_SECS=1200   # 20 min

    attempt=1
    while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
        status=$(cd "$REPO" && "$PYTHON" -m scripts.skew_accrual_gate \
            --store "$STORE" --repo "$REPO" 2>/dev/null || true)
        case "$status" in
            FRESH|RESOLVE_ERROR)
                # RESOLVE_ERROR is fatal: a missing tier is not a wait-and-retry
                # condition, it is an operator-fixable store-path problem.
                if [ "$status" = "RESOLVE_ERROR" ]; then
                    log "ERROR: store resolve failed — store=$STORE tier=eod root=SPY"
                    log "  → check that THETADATA_STORE points at a tree with eod/SPY/<YYYY>.parquet"
                    return 2
                fi
                log "store fresh (attempt $attempt/$MAX_ATTEMPTS) — proceeding"
                return 0
                ;;
            USAGE_ERROR)
                log "ERROR: gate usage error — repo=$REPO missing lib.nyse_calendar?"
                return 3
                ;;
            STALE|""|*)
                if [ "$attempt" -eq "$MAX_ATTEMPTS" ]; then
                    log "ERROR: store still not fresh after $MAX_ATTEMPTS attempts — aborting"
                    return 1
                fi
                log "store not fresh yet (attempt $attempt/$MAX_ATTEMPTS) — sleeping ${SLEEP_SECS}s"
                sleep "$SLEEP_SECS"
                attempt=$((attempt + 1))
                ;;
        esac
    done
}

# ── step 3: call --accrue ──────────────────────────────────────────────────────
# W2-1b ships `scripts/build_options_skew.py` with the accrue flag (a source-
# stamped ledger upsert into data/options_skew/snapshots.parquet). On the
# pre-W2-1b tree the flag is unknown; argparse will print
# `unrecognized arguments: <flag>` and exit 2. We MUST fail loud here — never
# silently fall back to a full run, because a full run writes
# site/options_skew/latest.json (the EMIT half) and would race the render-host
# side that W2-1b pinned to legacy.
step_accrue() {
    cd "$REPO"
    log "launching python -m scripts.build_options_skew (W2-1b accrue flag)"
    if ! "$PYTHON" -m scripts.build_options_skew --accrue; then
        rc=$?
        # Detect argparse's "unrecognized arguments" exit (code 2 with that
        # phrase on stderr). That is the SHIPPED state for pre-W2-1b trees.
        if [ "$rc" = "2" ]; then
            log "ERROR: W2-1b accrue flag is unrecognized — W2-1b has not landed on origin/main yet."
            log "  W2-2 requires the accrue flag (the source-stamped ledger upsert) from W2-1b."
            log "  Falling back to a full run would write site/options_skew/latest.json and"
            log "  race the render-host side that W2-1b pinned to legacy — DO NOT do that."
            log "  Wait for W2-1b to merge, then re-run."
        else
            log "ERROR: build_options_skew accrue step failed with exit $rc"
        fi
        return "$rc"
    fi
    log "accrue completed"
    return 0
}

# ── step 4: publish to R2 ─────────────────────────────────────────────────────
# Skipped under SKEW_DRY_RUN=1 (the ledger is still written locally; the R2
# leg is the only thing dropped).
step_publish() {
    if [ "${SKEW_DRY_RUN:-0}" = "1" ]; then
        log "SKEW_DRY_RUN=1 — skipping publish_r2 (ledger written locally only)"
        return 0
    fi
    cd "$REPO"
    log "launching python -m scripts.publish_r2 (options_skew dir, no-manifest)"
    # --no-manifest on the FIRST run only: data/options_skew is a single parquet
    # (snapshots.parquet) plus sidecars; the manifest guard would shrink-refuse
    # the first publish because there is no remote manifest to compare against.
    # Subsequent runs (steady state) get a real manifest put.
    if ! "$PYTHON" -m scripts.publish_r2 --dirs options_skew --no-manifest; then
        rc=$?
        log "ERROR: publish_r2 for options_skew failed with exit $rc"
        return "$rc"
    fi
    log "publish completed"
    return 0
}

# ── main ───────────────────────────────────────────────────────────────────────
log "starting skew_accrual: repo=$REPO store=$STORE bypass=${SKEW_FRESHNESS_BYPASS:-0} dry_run=${SKEW_DRY_RUN:-0}"

if ! step_refresh_checkout; then
    log "ABORT at step_refresh_checkout"
    exit 1
fi
if ! step_freshness_gate; then
    log "ABORT at step_freshness_gate"
    exit 1
fi
if ! step_accrue; then
    log "ABORT at step_accrue"
    exit 1
fi
if ! step_publish; then
    log "ABORT at step_publish"
    exit 1
fi

log "done"
exit 0