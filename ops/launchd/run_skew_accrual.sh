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
#     the ThetaData EOD store, (3) verifies the W2-1b --accrue flag exists
#     in source, (4) calls the W2-1b accrue command against the ledger on
#     the store host, (5) verifies the ledger has content, (6) publishes
#     the resulting data/options_skew dir to R2 so the W2-3 cutover can
#     flip render hosts to the emit command.
#   W2-3 (later)
#     cuts render over to the emit command. Out of scope here.
#
# Nothing in this packet may change live behavior: it adds files and tests,
# and registers a directory in publish_r2's data-dir registry — it does NOT
# alter any workflow step. The lane is OFF by default (no plist loaded on the
# host) until the seat installs it per the runbook.
#
# STEP ORDER (load-bearing — each step gates the next on a non-zero exit)
#   1. step_refresh_checkout    — dedicated checkout, refuses dirt / failure
#   2. step_freshness_gate      — SPY eod >= T-1 NYSE session
#   3. step_precheck_w21b       — W2-1b --accrue flag exists in source
#   4. step_accrue              — append today's skew to the ledger
#   5. step_verify_ledger       — ledger has at least one row before publish
#   6. step_publish             — publish to R2 (skipped under SKEW_DRY_RUN=1)
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
# PRECHECK (W2-1b sibling gate)
# ─────────────────────────────────────────────────────────────────────────────
# The --accrue flag is shipped by the W2-1b sibling. On the pre-W2-1b tree the
# flag does not exist; calling `--accrue` would either silently run main()
# (which writes site/options_skew/latest.json and races the render-host side
# W2-1b pinned to legacy) or fail late in argparse with exit 2. The runner
# detects the missing flag via scripts/skew_accrual_precheck (a source-grep
# for the literal '--accrue') BEFORE invoking the accrue step. Precheck exit
# 4 (FLAG_MISSING) → runner aborts loud with the named reason.
#
# LEDGER VERIFY (BLOCKER-3 fix)
# ─────────────────────────────────────────────────────────────────────────────
# The W2-1b snapshot() can return 0 without writing rows (chain=None, no
# rows, or dedup-only). A zero-row accrue must NOT publish — the R2 leg
# would advertise a no-op put. scripts.skew_accrual_verify_ledger checks
# data/options_skew/snapshots.parquet has at least one row after the accrue
# step; exit 5 (NO_LEDGER) → runner aborts loud.
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
LEDGER_DEFAULT="$REPO/data/options_skew/snapshots.parquet"
LEDGER="${SKEW_LEDGER_PATH:-$LEDGER_DEFAULT}"

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
        # Capture the gate's exit code BEFORE the if: `if ! cmd` resets $?
        # inside the body, so the rc-must-be-captured-before pattern is the
        # only way to keep failure rc's intact (BLOCKER-2 fix).
        ( cd "$REPO" && "$PYTHON" -m scripts.skew_accrual_gate \
            --store "$STORE" --repo "$REPO" >/tmp/.skew_gate_status 2>/tmp/.skew_gate_stderr )
        gate_rc=$?
        status=$(cat /tmp/.skew_gate_status 2>/dev/null || true)
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

# ── step 3: W2-1b precheck — does --accrue exist in source? ───────────────────
# The precheck is BLOCKER-1's load-bearing safety property: on a pre-W2-1b
# tree, calling `python -m scripts.build_options_skew --accrue` either
# silently runs main() (which writes site/options_skew/latest.json and
# races the render-host side W2-1b pinned to legacy) or argparse rejects
# the unknown flag with exit 2. Both outcomes corrupt the lane. Detect the
# missing flag here so the operator sees a one-line named-reason failure
# instead of a silent pollution.
step_precheck_w21b() {
    cd "$REPO"
    # Capture stdout/stderr to files so the rc-must-be-captured-before
    # pattern works (BLOCKER-2 fix carries through here too).
    ( "$PYTHON" -m scripts.skew_accrual_precheck --repo "$REPO" \
        >/tmp/.skew_precheck_status 2>/tmp/.skew_precheck_stderr )
    precheck_rc=$?
    status=$(cat /tmp/.skew_precheck_status 2>/dev/null || true)
    if [ "$precheck_rc" -ne 0 ]; then
        # Precheck exit 4 → FLAG_MISSING. The named reason lives on stderr.
        log "ERROR: W2-1b precheck failed (rc=$precheck_rc, status=$status)"
        while IFS= read -r line; do
            log "  $line"
        done </tmp/.skew_precheck_stderr
        return 4
    fi
    log "W2-1b precheck passed ($status) — --accrue flag exposed by scripts.build_options_skew"
    return 0
}

# ── step 4: call --accrue ──────────────────────────────────────────────────────
# W2-1b ships `scripts/build_options_skew.py` with the accrue flag (a source-
# stamped ledger upsert into data/options_skew/snapshots.parquet). On the
# pre-W2-1b tree the flag is unknown — step_precheck_w21b above catches that
# branch; this step runs only when the precheck has confirmed --accrue exists.
# The runner MUST capture the cmd rc BEFORE the if: `if ! cmd; then rc=$?`
# does NOT work — POSIX resets $? to 0 inside the then-block of `if !`.
#
# Pre-state (row count) is recorded BEFORE the call so step_verify_ledger
# can refuse a no-op accrue (BLOCKER-2). The snapshot() can return 0
# without writing rows (chain=None, no rows, dedup-only, or byte-equal
# rewrite); without the pre_rows check the launchd log would report a
# successful publish for an unchanged ledger.
step_accrue() {
    cd "$REPO"
    # Record pre-state — the row count the ledger has TODAY, before the
    # accrue. Missing ledger → 0 (the verify step will treat that as
    # "no pre-existing content" and only pass if the post-state grew).
    if [ -f "$LEDGER" ]; then
        pre_rows="$("$PYTHON" -c "
import sys
try:
    import pandas as pd
    df = pd.read_parquet('$LEDGER')
    print(int(len(df)))
except Exception:
    print(0)
" 2>/dev/null || echo 0)"
    else
        pre_rows=0
    fi
    log "pre-accrue row count: $pre_rows"
    printf '%s\n' "$pre_rows" > "$REPO/.skew_pre_rows"
    log "launching python -m scripts.build_options_skew --accrue (W2-1b)"
    # Explicit rc-capture BEFORE any control flow:
    set +e
    "$PYTHON" -m scripts.build_options_skew --accrue
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        log "ERROR: build_options_skew accrue step failed with exit $rc"
        return "$rc"
    fi
    log "accrue completed (rc=0)"
    return 0
}

# ── step 5: verify ledger has content AND grew under the accrue step ─────────
# W2-1b's snapshot() can return 0 without writing rows (chain is None, no
# rows, dedup-only, or byte-equal rewrite). A no-op accrue must NOT publish —
# the R2 leg would advertise an unchanged ledger under a fresh
# Last-Modified stamp, polluting audit_r2's freshness anchor. The verify
# step reads the pre-accrue row count from .skew_pre_rows (recorded in
# step_accrue) and refuses any post-state that has not strictly grown.
step_verify_ledger() {
    cd "$REPO"
    log "verifying ledger content: $LEDGER"
    pre_rows=0
    if [ -f "$REPO/.skew_pre_rows" ]; then
        pre_rows=$(cat "$REPO/.skew_pre_rows" 2>/dev/null || echo 0)
    fi
    log "verify pre-accrue rows: $pre_rows"
    set +e
    "$PYTHON" -m scripts.skew_accrual_verify_ledger \
        --ledger "$LEDGER" --pre-rows "$pre_rows" \
        >/tmp/.skew_verify_status 2>/tmp/.skew_verify_stderr
    rc=$?
    set -e
    status=$(cat /tmp/.skew_verify_status 2>/dev/null || true)
    if [ "$rc" -ne 0 ]; then
        log "ERROR: ledger verification failed (rc=$rc, status=$status)"
        while IFS= read -r line; do
            log "  $line"
        done </tmp/.skew_verify_stderr
        return 5
    fi
    log "ledger verified ($status)"
    rm -f "$REPO/.skew_pre_rows"
    return 0
}

# ── step 6: publish to R2 ─────────────────────────────────────────────────────
# Skipped under SKEW_DRY_RUN=1 (the ledger is still written locally; the R2
# leg is the only thing dropped).
step_publish() {
    if [ "${SKEW_DRY_RUN:-0}" = "1" ]; then
        log "SKEW_DRY_RUN=1 — skipping publish_r2 (ledger written locally only)"
        return 0
    fi
    cd "$REPO"
    log "launching python -m scripts.publish_r2 (options_skew dir)"
    # The M1 ops host holds the FULL store tree under data/options_skew/
    # (snapshots.parquet plus the tracked sidecars) — the publish_r2
    # manifest guard's shrink-guard cannot trip on a full tree. We do NOT
    # pass --no-manifest: every publish writes a real manifest, which is
    # what bulk consumers (fetch_r2 / audit_r2) read for the freshness
    # anchor. Passing --no-manifest was the previous design and locked the
    # first publish in steady state silently; see MAJOR-3 fix.
    set +e
    "$PYTHON" -m scripts.publish_r2 --dirs options_skew
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
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
if ! step_precheck_w21b; then
    log "ABORT at step_precheck_w21b (--accrue flag missing in source — W2-1b not on origin/main)"
    exit 4
fi
if ! step_accrue; then
    log "ABORT at step_accrue"
    exit 1
fi
if ! step_verify_ledger; then
    log "ABORT at step_verify_ledger (ledger has 0 rows / missing — refusing to publish)"
    exit 5
fi
if ! step_publish; then
    log "ABORT at step_publish"
    exit 1
fi

log "done"
exit 0