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
#     is the runner — it (1) refreshes the dedicated checkout, (2) asserts
#     the refreshed checkout is clean (BLOCKER-2 revisit: B2 cure moves the
#     assertion to its own step between refresh and any hydration/write),
#     (3) hydrates data/options_skew from R2 (the durable home; this
#     checkout is disposable), (4) gates on ThetaData EOD freshness, (5)
#     verifies the W2-1b --accrue flag exists in source, (6) calls the W2-1b
#     accrue command, (7) verifies the ledger has at least one row that grew
#     under the accrue, and (8) publishes data/options_skew to R2.
#   W2-3 (later)
#     cuts render over to the emit command. Out of scope here.
#
# Nothing in this packet may change live behavior: it adds files and tests,
# and registers a directory in publish_r2's data-dir registry — it does NOT
# alter any workflow step. The lane is OFF by default (no plist loaded on the
# host) until the seat installs it per the runbook.
#
# STEP ORDER (load-bearing — each step gates the next on a non-zero exit)
#   1. step_refresh                — fetch + detach + reset --hard + clean -fd
#   2. step_assert_clean_tree      — refuses any post-refresh dirty state
#   3. step_hydrate_ledger         — restore options_skew from R2 (durable)
#   4. step_freshness_gate         — SPY eod >= T-1 NYSE session
#   5. step_precheck_w21b          — W2-1b --accrue flag exists in source
#   6. step_accrue                 — append today's skew to the ledger
#   7. step_verify_ledger          — ledger has at least one row AND grew
#                                     (BLOCKER-2; skipped on rc 3)
#   8. step_publish                — publish to R2 (skipped on rc 3 OR SKEW_DRY_RUN=1)
#
# Dry-run (SKEW_DRY_RUN=1) performs steps 1-7 and skips step 8 — the ledger is
# written locally, the R2 leg is dropped. Used for smoke / integration checks
# where you want to verify the build pipeline without touching live artifacts.
#
# RUN-STATE FILES (B2 cure, 2026-09-22)
# ─────────────────────────────────────────────────────────────────────────────
# Every run-state artifact (pre-accrue row count, gate/precheck/verify status
# files, run logs) lives OUTSIDE the checkout under a sibling state directory
# ($SKEW_STATE_DIR, default /Users/chriswong/skew-ops-state) — never inside
# $REPO. Stale run-state files inside $REPO would dirty the post-refresh
# checkout and fail step_assert_clean_tree, which is what made the runner
# un-repeatable from one launchd tick to the next. The state dir is the
# durable home for ephemeral per-run state; $REPO is the disposable, R2-
# owned bytestream that gets reset --hard + clean -fd on every run.
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
# LEDGER VERIFY (BLOCKER-3 fix; A-F03-W2-8 refines the caught-up case)
# ─────────────────────────────────────────────────────────────────────────────
# The W2-1b snapshot() can return 0 without writing rows (chain=None, no
# rows, or dedup-only). Two distinct outcomes are now treated differently:
#
#   1. Zero-row accrue under a REAL run (a non-zero fresh session S that the
#      store resolved and backfill_from_store processed): the verify helper's
#      BLOCKER-2 rule refuses `post_rows <= pre_rows` → runner logs `ABORT at
#      step_verify_ledger` and exits 5. A zero-row accrue must NOT publish:
#      the R2 leg would advertise a no-op put, polluting audit_r2's freshness
#      anchor. scripts.skew_accrual_verify_ledger is unchanged.
#
#   2. Zero-row accrue under a CAUGHT-UP ledger (the complete store session
#      S is already on the ledger byte-for-byte, so the backfill receipt
#      reports `dates_backfilled == len(dates)` AND `rows_added + rows_replaced == 0`
#      — see scripts/build_options_skew.py for the discriminator; the spec's
#      "`catch_up_sessions` returns `[]`" line is misleading, the helper
#      always returns at least the target session itself): the runner logs
#      `NOOP_CAUGHT_UP run_tag=… ledger=…`, SKIPS step_verify_ledger AND
#      step_publish, and exits 0. The seat ruling treats this as a lawful
#      no-op — the daily maintainer's session already landed, the lane did
#      its job, and the operator wants a clean rc-0 exit, not a launchd
#      failure for every weekday-after-holiday tick. See A-F03-W2-8
#      (2026-09-23) for the full ruling.
#
# BYPASS
# ─────────────────────────────────────────────────────────────────────────────
# Set SKEW_FRESHNESS_BYPASS=1 to skip the freshness wait loop and run the
# accrual immediately regardless of store freshness.
#
# DRY-RUN (no publish)
# ─────────────────────────────────────────────────────────────────────────────
# Set SKEW_DRY_RUN=1 to run steps 1-7 (refresh, assert, hydrate,
# freshness, precheck, accrue, verify) WITHOUT step 8 (publish to R2).
# The ledger is written locally (data/options_skew/snapshots.parquet) but
# does NOT upload to R2. Use this for smoke / integration checks where you
# want to verify the build pipeline without touching live artifacts.
#
# USAGE (smoke — refresh+assert+hydrate+accrue+verify, no R2 publish):
#   set -a; source /Users/chriswong/skew-ops-wt/.env; set +a
#   SKEW_FRESHNESS_BYPASS=1 SKEW_DRY_RUN=1 \
#     /Users/chriswong/skew-ops-wt/ops/launchd/run_skew_accrual.sh
#
# USAGE (full — same as the nightly launchd run):
#   set -a; source /Users/chriswong/skew-ops-wt/.env; set +a
#   SKEW_FRESHNESS_BYPASS=1 \
#     /Users/chriswong/skew-ops-wt/ops/launchd/run_skew_accrual.sh
#
# LOG TAILING (when installed as com.macro.skewaccrual — launchd writes into
# the sibling state dir, the same $SKEW_STATE_DIR default this runner uses):
#   tail -f /Users/chriswong/skew-ops-state/logs/skewaccrual.stdout.log \
#           /Users/chriswong/skew-ops-state/logs/skewaccrual.stderr.log
#
# HOST CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────
# The dedicated lane checkout is /Users/chriswong/skew-ops-wt (NOT the M1
# flow-ops-wt or theta-ops-wt trees — both are stale/dirty by design and would
# undermine a "checkout is clean" assertion). The runner refreshes the checkout
# itself before any work: `git fetch origin && git checkout --detach origin/main
# && git reset --hard && git clean -fd` followed by step_assert_clean_tree. A
# dirty or stale checkout is REFUSED — that is the lane's load-bearing safety
# property (a dirty tree would publish someone's WIP). The lane NEVER pushes to
# git; the only outbound is publish_r2, and that is gated on the dedup'd
# ledger contents.

set -eu

# ── paths ─────────────────────────────────────────────────────────────────────
REPO_DEFAULT="/Users/chriswong/skew-ops-wt"
REPO="${SKEW_OPS_ROOT:-$REPO_DEFAULT}"
PYTHON="${SKEW_PYTHON:-/opt/homebrew/Caskroom/miniconda/base/bin/python}"
STORE="${THETADATA_STORE:-/Users/chriswong/theta-ops-wt/data/thetadata_eod}"
LEDGER_DEFAULT="$REPO/data/options_skew/snapshots.parquet"
LEDGER="${SKEW_LEDGER_PATH:-$LEDGER_DEFAULT}"
# Sibling state directory — every run-state artifact lives here, OUTSIDE the
# checkout (B2 cure, 2026-09-22). Stale files inside $REPO from a prior run
# would dirty the post-refresh checkout and fail step_assert_clean_tree, which
# is exactly the un-repeatability the round-1 review flagged. The default
# /Users/chriswong/skew-ops-state is a sibling of /Users/chriswong/skew-ops-wt
# (by design — not under the tree). Override with SKEW_STATE_DIR for tests.
STATE_DIR_DEFAULT="/Users/chriswong/skew-ops-state"
STATE_DIR="${SKEW_STATE_DIR:-$STATE_DIR_DEFAULT}"

# Ensure the state dir (and its logs/ child, the launchd StandardOut/ErrPath
# parent) exist — every run-state file write below targets it. On the M1 ops
# host the install runbook (research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE
# _2026-09-22.md §3.3) creates logs/ BEFORE `launchctl bootstrap`, because
# launchd opens its log files before this script runs; this mkdir covers every
# later run and tests that point SKEW_STATE_DIR at a not-yet-existing tmp_path.
mkdir -p "$STATE_DIR" "$STATE_DIR/logs"

# Per-pid run-state files. Using $$ means two launches of the runner can run
# in parallel without clobbering; old files in $STATE_DIR from a prior process
# are stale inputs, not polluting writes (they are READ-only at step_verify).
RUN_TAG="$$"
GATE_STATUS_FILE="$STATE_DIR/.skew_gate_status.$RUN_TAG"
PRECHECK_STATUS_FILE="$STATE_DIR/.skew_precheck_status.$RUN_TAG"
PRECHECK_STDERR_FILE="$STATE_DIR/.skew_precheck_stderr.$RUN_TAG"
VERIFY_STATUS_FILE="$STATE_DIR/.skew_verify_status.$RUN_TAG"
VERIFY_STDERR_FILE="$STATE_DIR/.skew_verify_stderr.$RUN_TAG"
PRE_ROWS_FILE="$STATE_DIR/.skew_pre_rows.$RUN_TAG"

log() {
    # One-line receipt at line start — the runbook points operators here.
    printf '[%s] skew_accrual: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

# ── step 1: refresh the dedicated checkout ─────────────────────────────────────
step_refresh() {
    if [ ! -d "$REPO/.git" ]; then
        log "ERROR: dedicated checkout $REPO does not exist or is not a git worktree"
        log "  → see research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md install runbook"
        return 1
    fi
    cd "$REPO"
    # Belt-and-suspenders (B2 cure, 2026-09-22): the refresh IS destructive.
    # The dedicated skew-ops-wt checkout is disposable by design — its durable
    # state lives in R2 (snapshots.parquet, manifest, gate receipts). Every
    # run's refresh therefore:
    #   1) fetches origin (network),
    #   2) detaches onto origin/main (read-only by design),
    #   3) resets --hard (collapses any local commit),
    #   4) cleans -fd (removes any untracked / ignored bytes).
    # This makes the cycle repeatable: a stale .skew_pre_rows sidecar from a
    # prior tick inside $REPO will be wiped here, and a fetch_r2 hydrate
    # from step 3 always lands onto the freshly-detached origin/main.
    if ! git fetch origin >/dev/null 2>&1; then
        log "ERROR: git fetch origin failed (network? rate limit?) — refusing to run"
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
    # Detach on origin/main so the next run's fetch does not collide with a
    # local branch that is no longer at HEAD. A detached HEAD is the canonical
    # shape for read-only nightly lanes.
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

# ── step 2: clean-tree assertion (BEFORE any hydrate or write) ─────────────────
# B2 cure (2026-09-22): the previous design bundled the dirty-tree check into
# step_refresh_checkout, which caught dirtyness caused by the runner itself
# (a stale .skew_pre_rows from a prior tick). The fix is to assert AFTER the
# destructive refresh and BEFORE any hydration or write, so the only thing
# that can dirty the tree is the hydration step. A red here means a sibling
# session is mid-edit on $REPO — refuse, do not auto-clean.
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

# ── step 3: hydrate the live ledger from R2 (durable home) ─────────────────────
# B2 cure (2026-09-22): the dedicated checkout is disposable; its durable
# bytes live in R2 (see scripts/publish_r2._DATA_DIRS['options_skew']). Every
# run hydrates the latest options_skew ledger from R2 BEFORE the accrue step,
# so the accrue operates on the union of prior publishes plus today's accrual.
# A non-zero exit from fetch_r2 means DO NOT accrue and DO NOT publish — the
# fresh R2 state may be unwritable / network down / R2 creds expired; the
# attention restore/publish pairing is documented in scripts/fetch_r2.py's
# docstring (and is the contract publish_r2._DATA_DIRS['options_skew'] assumes).
step_hydrate_ledger() {
    cd "$REPO"
    set +e
    "$PYTHON" -m scripts.fetch_r2 --dirs options_skew >/dev/null 2>&1
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        log "ERROR: fetch_r2 hydrate of options_skew failed (rc=$rc) — refusing to accrue and publish"
        return "$rc"
    fi
    log "options_skew hydrated from R2 (rc=$rc)"
    return 0
}

# ── step 4: freshness gate ────────────────────────────────────────────────────
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
        # 2026-09-23 defect (first scheduled run): the gate prints ONE verdict
        # word on stdout and ONE `::gate-info::` line on stderr, but this
        # capture merged both streams into the status file and matched the
        # whole file against `FRESH` — so a FRESH store read as STALE on every
        # attempt and the lane aborted after 6×20 min. Capture stdout only;
        # keep the info line in the lane log (it is the receipt's evidence);
        # parse the verdict as the last line that IS a verdict word.
        ( cd "$REPO" && "$PYTHON" -m scripts.skew_accrual_gate \
            --store "$STORE" --repo "$REPO" >"$GATE_STATUS_FILE" 2>"$GATE_STATUS_FILE.err" )
        gate_rc=$?
        gate_info=$(tail -n1 "$GATE_STATUS_FILE.err" 2>/dev/null || true)
        [ -n "$gate_info" ] && log "gate: $gate_info"
        status=$(grep -E '^(FRESH|STALE|RESOLVE_ERROR|USAGE_ERROR)$' "$GATE_STATUS_FILE" 2>/dev/null | tail -n1 || true)
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

# ── step 5: W2-1b precheck — does --accrue exist in source? ───────────────────
# The precheck is BLOCKER-1's load-bearing safety property: on a pre-W2-1b
# tree, calling `python -m scripts.build_options_skew --accrue` either
# silently runs main() (which writes site/options_skew/latest.json and
# races the render-host side W2-1b pinned to legacy) or argparse rejects
# the unknown flag with exit 2. Both outcomes corrupt the lane. Detect the
# missing flag here so the operator sees a one-line named-reason failure
# instead of a silent pollution.
step_precheck_w21b() {
    cd "$REPO"
    # Capture stdout/stderr to files in $STATE_DIR so the rc-must-be-captured-
    # before pattern works (BLOCKER-2 fix carries through here too).
    set +e
    ( "$PYTHON" -m scripts.skew_accrual_precheck --repo "$REPO" \
        >"$PRECHECK_STATUS_FILE" 2>"$PRECHECK_STDERR_FILE" )
    precheck_rc=$?
    set -e
    status=$(cat "$PRECHECK_STATUS_FILE" 2>/dev/null || true)
    if [ "$precheck_rc" -ne 0 ]; then
        # Precheck exit 4 → FLAG_MISSING. The named reason lives on stderr.
        log "ERROR: W2-1b precheck failed (rc=$precheck_rc, status=$status)"
        while IFS= read -r line; do
            log "  $line"
        done <"$PRECHECK_STDERR_FILE"
        return 4
    fi
    log "W2-1b precheck passed ($status) — --accrue flag exposed by scripts.build_options_skew"
    return 0
}

# ── step 6: call --accrue ──────────────────────────────────────────────────────
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
# successful publish for an unchanged ledger. The pre_rows file lives in
# $STATE_DIR (B2 cure, 2026-09-22): it must NOT be inside $REPO or it would
# dirty the checkout and fail step_assert_clean_tree on the next tick.
#
# A-F03-W2-8 (2026-09-23): the builder distinguishes the CAUGHT-UP no-op from
# a real accrue by exiting 3 when the accrue leg was the ONLY selected leg
# AND the ledger was already caught up to the store's complete session.
# The launchd runner treats that rc as a one-line receipt + rc-3 return so
# the main sequence can SKIP verify AND publish — a caught-up ledger is
# exactly what the verify step's BLOCKER-2 rule was written to refuse
# (post_rows <= pre_rows), but refusing the publish under "nothing to
# accrue" is the wrong outcome: the daily maintainer's session has already
# landed, the lane did its job, and the operator wants a clean rc-0 exit,
# not a launchd failure for every weekday-after-holiday tick.
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
    printf '%s\n' "$pre_rows" > "$PRE_ROWS_FILE"
    log "launching python -m scripts.build_options_skew --accrue (W2-1b)"
    # Explicit rc-capture BEFORE any control flow. The `|| rc=$?` form
    # swallows the python non-zero exit (including rc 3) at the call site
    # so `set -e` does not abort the function — the main sequence reads
    # `accrue_rc` and branches on it explicitly. (The main sequence uses
    # the `set +e … rc=$? … set -e` shape below; both patterns are valid.
    # Inside step_accrue we use `|| rc=$?` only because the function body
    # keeps executing past the python call, so the explicit form is
    # cleaner than bracketing the python call with set +e/set -e.)
    rc=0
    "$PYTHON" -m scripts.build_options_skew --accrue || rc=$?
    if [ "$rc" -eq 3 ]; then
        # A-F03-W2-8: caught-up no-op. The ledger already carries the
        # complete store session S, so the accrue step has nothing to
        # write. Propagate rc 3 to the main sequence so it can SKIP
        # verify AND publish — a caught-up ledger would refuse the
        # verify step's BLOCKER-2 rule (post_rows <= pre_rows), but
        # the publish-skip is the seat-ruled correct outcome here.
        log "accrue: NOOP_CAUGHT_UP — complete store session already on the ledger; nothing to accrue"
        rm -f "$PRE_ROWS_FILE"
        return 3
    fi
    if [ "$rc" -ne 0 ]; then
        log "ERROR: build_options_skew accrue step failed with exit $rc"
        return "$rc"
    fi
    log "accrue completed (rc=0)"
    return 0
}

# ── step 7: verify ledger has content AND grew under the accrue step ─────────
# W2-1b's snapshot() can return 0 without writing rows (chain is None, no
# rows, dedup-only, or byte-equal rewrite). A no-op accrue must NOT publish —
# the R2 leg would advertise an unchanged ledger under a fresh
# Last-Modified stamp, polluting audit_r2's freshness anchor. The verify
# step reads the pre-accrue row count from the $STATE_DIR pre_rows file
# (recorded in step_accrue) and refuses any post-state that has not
# strictly grown.
step_verify_ledger() {
    cd "$REPO"
    log "verifying ledger content: $LEDGER"
    pre_rows=0
    if [ -f "$PRE_ROWS_FILE" ]; then
        pre_rows=$(cat "$PRE_ROWS_FILE" 2>/dev/null || echo 0)
    fi
    log "verify pre-accrue rows: $pre_rows"
    set +e
    "$PYTHON" -m scripts.skew_accrual_verify_ledger \
        --ledger "$LEDGER" --pre-rows "$pre_rows" \
        >"$VERIFY_STATUS_FILE" 2>"$VERIFY_STDERR_FILE"
    rc=$?
    set -e
    status=$(cat "$VERIFY_STATUS_FILE" 2>/dev/null || true)
    if [ "$rc" -ne 0 ]; then
        log "ERROR: ledger verification failed (rc=$rc, status=$status)"
        while IFS= read -r line; do
            log "  $line"
        done <"$VERIFY_STDERR_FILE"
        return 5
    fi
    log "ledger verified ($status)"
    rm -f "$PRE_ROWS_FILE"
    return 0
}

# ── step 8: publish to R2 ─────────────────────────────────────────────────────
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
log "starting skew_accrual: repo=$REPO state_dir=$STATE_DIR store=$STORE bypass=${SKEW_FRESHNESS_BYPASS:-0} dry_run=${SKEW_DRY_RUN:-0}"

if ! step_refresh; then
    log "ABORT at step_refresh"
    exit 1
fi
if ! step_assert_clean_tree; then
    log "ABORT at step_assert_clean_tree"
    exit 1
fi
if ! step_hydrate_ledger; then
    log "ABORT at step_hydrate_ledger (R2 restore failed — refusing to accrue/publish)"
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
# A-F03-W2-8 (2026-09-23): the builder distinguishes the CAUGHT-UP no-op from
# a real accrue by exiting 3 when the accrue leg was the ONLY selected leg
# AND the ledger was already caught up to the store's complete session. The
# launchd runner treats that rc as a one-line receipt + rc-3 return so the
# main sequence can SKIP verify AND publish (a caught-up ledger is exactly
# what the verify step's BLOCKER-2 rule was written to refuse, but refusing
# the publish under "nothing to accrue" is the wrong outcome: the daily
# maintainer's session has already landed, the lane did its job, and the
# operator wants a clean rc-0 exit, not a launchd failure for every
# weekday-after-holiday tick). Steps 7 and 8 are byte-identical for rc 0
# and any other non-zero rc (those still abort loud with the named reason).
set +e
step_accrue
accrue_rc=$?
set -e
if [ "$accrue_rc" -eq 3 ]; then
    log "NOOP_CAUGHT_UP run_tag=$RUN_TAG ledger=$LEDGER"
    log "done (caught-up no-op: verify + publish skipped)"
    exit 0
fi
if [ "$accrue_rc" -ne 0 ]; then
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
