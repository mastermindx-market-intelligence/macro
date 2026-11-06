#!/bin/sh
# ops/launchd/run_options_payoff_lab.sh
#
# Store-host producer for the options payoff lab (MO-A3 W2-5a).
# Sibling of ops/launchd/run_skew_accrual.sh. This file does not modify
# that lane. Both lanes share the checkout /Users/chriswong/skew-ops-wt
# and the state directory /Users/chriswong/skew-ops-state.
#
# STEP ORDER
#   0. step_collision_guard   — if run_skew_accrual.sh is live, sleep 300s
#                               up to 6 times, then abort. Runs BEFORE any
#                               git command so the two lanes do not reset
#                               the shared checkout at the same time.
#   1. step_refresh           — fetch + detach origin/main + reset + clean
#   2. step_assert_clean_tree — refuse a dirty tree after the refresh
#   3. step_hydrate           — fetch_r2 --dirs options_payoff_lab.
#                               Zero objects is not fatal: the first run
#                               has nothing to restore. Log that and continue.
#                               Any other hydrate failure aborts.
#   4. step_accrue            — python -m scripts.build_options_payoff_lab --accrue
#   5. step_verify            — latest.json parses and its asof equals the
#                               store's latest session date
#   6. step_publish           — publish_r2 --dirs options_payoff_lab
#                               (skipped when PAYOFF_DRY_RUN=1)
#
# The lane never pushes to git. PAYOFF_STATE_DIR (default
# /Users/chriswong/skew-ops-state) holds logs. Override PAYOFF_OPS_ROOT
# and PAYOFF_PYTHON in tests.

set -eu

REPO_DEFAULT="/Users/chriswong/skew-ops-wt"
REPO="${PAYOFF_OPS_ROOT:-$REPO_DEFAULT}"
PYTHON="${PAYOFF_PYTHON:-/opt/homebrew/Caskroom/miniconda/base/bin/python}"
STORE="${THETADATA_STORE:-/Users/chriswong/theta-ops-wt/data/thetadata_eod}"
STATE_DIR_DEFAULT="/Users/chriswong/skew-ops-state"
STATE_DIR="${PAYOFF_STATE_DIR:-$STATE_DIR_DEFAULT}"

mkdir -p "$STATE_DIR" "$STATE_DIR/logs"

log() {
    printf '[%s] payoff_lab: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

step_collision_guard() {
    # Sleep 300s up to 6 times while the skew runner is live, then abort.
    # The check runs before git refresh so the shared checkout is not reset
    # underneath the other lane.
    attempt=1
    max_sleeps=6
    while pgrep -f run_skew_accrual.sh >/dev/null 2>&1; do
        if [ "$attempt" -gt "$max_sleeps" ]; then
            log "ERROR: skew runner still live after ${max_sleeps} waits of 300s — aborting"
            return 1
        fi
        log "skew runner live (attempt ${attempt}/${max_sleeps}) — sleeping 300s"
        sleep 300
        attempt=$((attempt + 1))
    done
    log "no live skew runner — proceeding"
    return 0
}

step_refresh() {
    if [ ! -d "$REPO/.git" ]; then
        log "ERROR: dedicated checkout $REPO does not exist or is not a git worktree"
        return 1
    fi
    cd "$REPO"
    if ! git fetch origin >/dev/null 2>&1; then
        log "ERROR: git fetch origin failed — refusing to run"
        return 1
    fi
    # 2026-09-23 abort (12:30Z skew accrual): a tracked file left MODIFIED by a
    # manual session in this shared checkout (the seat's one-time backfill left
    # data/options_skew/snapshots.parquet dirty) makes `git checkout --detach`
    # refuse BEFORE the reset/clean below could ever run, and the lane aborts
    # for the day. The checkout is disposable by design (durable state is R2),
    # so discard local bytes FIRST, then detach, then reset/clean again.
    if ! git reset --hard >/dev/null 2>&1; then
        log "ERROR: pre-detach git reset --hard failed — refusing to run"
        return 1
    fi
    if ! git clean -fd >/dev/null 2>&1; then
        log "ERROR: pre-detach git clean -fd failed — refusing to run"
        return 1
    fi
    if ! git checkout --detach origin/main >/dev/null 2>&1; then
        log "ERROR: git checkout --detach origin/main failed — refusing to run"
        return 1
    fi
    if ! git reset --hard >/dev/null 2>&1; then
        log "ERROR: git reset --hard failed — refusing to run"
        return 1
    fi
    if ! git clean -fd >/dev/null 2>&1; then
        log "ERROR: git clean -fd failed — refusing to run"
        return 1
    fi
    log "checkout refreshed — HEAD=$(git rev-parse --short HEAD)"
    return 0
}

step_assert_clean_tree() {
    cd "$REPO"
    dirty=$(git status --porcelain --untracked-files=all 2>/dev/null || true)
    if [ -n "$dirty" ]; then
        log "ERROR: dedicated checkout $REPO is dirty — refusing to run"
        log "  porcelain: $(echo "$dirty" | head -5 | tr '\n' ';')"
        return 1
    fi
    log "checkout clean — proceeding to hydrate"
    return 0
}

step_hydrate() {
    cd "$REPO"
    set +e
    hydrate_out=$("$PYTHON" -m scripts.fetch_r2 --dirs options_payoff_lab 2>&1)
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        printf '%s\n' "$hydrate_out" | head -20 | while IFS= read -r line; do
            log "  hydrate: $line"
        done
        if printf '%s\n' "$hydrate_out" | grep -q "ZERO objects"; then
            log "fetch_r2 found zero options_payoff_lab objects — first run, continuing"
            return 0
        fi
        log "ERROR: fetch_r2 hydrate of options_payoff_lab failed (rc=$rc) — refusing to accrue and publish"
        return "$rc"
    fi
    log "options_payoff_lab hydrated from R2 (rc=$rc)"
    return 0
}

step_accrue() {
    cd "$REPO"
    log "launching python -m scripts.build_options_payoff_lab --accrue"
    set +e
    "$PYTHON" -m scripts.build_options_payoff_lab --accrue
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        log "ERROR: build_options_payoff_lab accrue step failed with exit $rc"
        return "$rc"
    fi
    log "accrue completed (rc=0)"
    return 0
}

step_verify() {
    cd "$REPO"
    art="$REPO/data/options_payoff_lab/latest.json"
    if [ ! -f "$art" ]; then
        log "ERROR: payoff lab artifact missing: $art"
        return 1
    fi
    set +e
    verify_out=$(PAYOFF_ARTIFACT="$art" THETADATA_STORE="$STORE" "$PYTHON" -c '
import json, os, sys
from pathlib import Path
art = Path(os.environ["PAYOFF_ARTIFACT"])
try:
    payload = json.loads(art.read_text())
except Exception as exc:
    print("PARSE_FAIL %s" % exc)
    sys.exit(1)
asof = payload.get("asof")
store = os.environ.get("THETADATA_STORE", "")
if not store:
    print("STORE_UNSET")
    sys.exit(1)
from engine.options_skew import _latest_store_date
latest = _latest_store_date(Path(store))
if not asof or str(asof) != str(latest):
    print("MISMATCH asof=%s latest=%s" % (asof, latest))
    sys.exit(1)
print("OK asof=%s" % asof)
' 2>&1)
    rc=$?
    set -e
    log "verify: $verify_out"
    if [ "$rc" -ne 0 ]; then
        log "ERROR: artifact verification failed (rc=$rc)"
        return 1
    fi
    log "artifact verified ($verify_out)"
    return 0
}

step_publish() {
    if [ "${PAYOFF_DRY_RUN:-0}" = "1" ]; then
        log "PAYOFF_DRY_RUN=1 — skipping publish_r2 (artifact written locally only)"
        return 0
    fi
    cd "$REPO"
    log "launching python -m scripts.publish_r2 --dirs options_payoff_lab"
    set +e
    "$PYTHON" -m scripts.publish_r2 --dirs options_payoff_lab
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        log "ERROR: publish_r2 for options_payoff_lab failed with exit $rc"
        return "$rc"
    fi
    log "publish completed"
    return 0
}

log "starting payoff_lab: repo=$REPO state_dir=$STATE_DIR store=$STORE dry_run=${PAYOFF_DRY_RUN:-0}"

if ! step_collision_guard; then
    log "ABORT at step_collision_guard"
    exit 1
fi
if ! step_refresh; then
    log "ABORT at step_refresh"
    exit 1
fi
if ! step_assert_clean_tree; then
    log "ABORT at step_assert_clean_tree"
    exit 1
fi
if ! step_hydrate; then
    log "ABORT at step_hydrate"
    exit 1
fi
if ! step_accrue; then
    log "ABORT at step_accrue"
    exit 1
fi
if ! step_verify; then
    log "ABORT at step_verify"
    exit 1
fi
if ! step_publish; then
    log "ABORT at step_publish"
    exit 1
fi

log "done"
exit 0
