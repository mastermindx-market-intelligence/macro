#!/bin/sh
# ops/launchd/run_options_matrix.sh
#
# Runner for the nightly options-matrix builder (Package E).
# Invoked by com.macro.optionsmatrix.plist via run_with_env.sh.
#
# FRESHNESS GATE
# ─────────────────────────────────────────────────────────────────────────────
# Before running the matrix builder, this script verifies that SPY has a
# coherent publishable session: same-date OI, EOD and finite positive-spot Greeks.
# The resolver also enforces main's five-NYSE-session publication-skew limit.
# The builder uses the same canonical resolver, so scheduling and publication
# cannot disagree when the daily maintainer advances OI to D ahead of settled
# Greeks/EOD on S=D-1.
#
# Logic:
#   1. Ask lib/nyse_calendar.expected_last_session() for the expected date, then
#      require the session BEFORE it because the matrix's OI plane is T+1 and
#      the engine computes delta_oi from OI[t-1] and OI[t-2].
#   2. Ask engine.thetadata_store.latest_options_matrix_session() for SPY's
#      newest bounded date shared by OI, EOD and finite positive-spot Greeks.
#   3. If coherent >= required → FRESH.  The calendar date is a floor, not a
#      ceiling, so an honestly advanced coherent store does not false-fail.
#   4. Otherwise sleep 20 min and retry (max 6 attempts = 2h window).
#   5. After 6 failures, exit 1 without running or publishing the builder.
#
# BYPASS
# ─────────────────────────────────────────────────────────────────────────────
# Set MATRIX_FRESHNESS_BYPASS=1 to skip the freshness wait loop and run the
# builder immediately regardless of store freshness.
#
# DRY-RUN (no publish)
# ─────────────────────────────────────────────────────────────────────────────
# Set MATRIX_NO_PUBLISH=1 to run the builder without --publish.  The builder
# writes local JSON to data/live_flow_out/options_matrix/ but does NOT upload
# to R2.  Use this for smoke / integration checks where you want to verify
# the build pipeline without touching live artifacts.
#
# USAGE (smoke / dry-run — builds locally, no R2 publish):
#   source /Users/chriswong/flow-ops-wt/.env
#   MATRIX_FRESHNESS_BYPASS=1 MATRIX_NO_PUBLISH=1 \
#     ops/launchd/run_options_matrix.sh
#
# USAGE (full publish — same as the nightly launchd run):
#   source /Users/chriswong/flow-ops-wt/.env
#   MATRIX_FRESHNESS_BYPASS=1 \
#     ops/launchd/run_options_matrix.sh
#
# LOG TAILING:
#   tail -f /tmp/optionsmatrix.stdout.log /tmp/optionsmatrix.stderr.log

set -eu

# ── paths ─────────────────────────────────────────────────────────────────────
# Empty or unset keeps the historical lane. ${VAR:-default} treats an empty
# string as unset, so it cannot become the current directory.
REPO="${MACRO_OPTIONS_MATRIX_ROOT:-/Users/chriswong/flow-ops-wt}"
PYTHON="/opt/homebrew/Caskroom/miniconda/base/bin/python"
STORE="${THETADATA_STORE:-/Users/chriswong/theta-ops-wt/data/thetadata_eod}"

# Refuse a relative or missing code root before the freshness helper or the build.
case "$REPO" in
    /*) ;;
    *)
        echo "[options_matrix] ERROR: REPO must be an absolute existing directory, not '$REPO'"
        exit 1
        ;;
esac
if [ ! -d "$REPO" ]; then
    echo "[options_matrix] ERROR: REPO is not an existing directory: $REPO"
    exit 1
fi
if [ ! -f "$REPO/scripts/build_options_matrix.py" ]; then
    echo "[options_matrix] ERROR: REPO is not the options-matrix code checkout (missing scripts/build_options_matrix.py): $REPO"
    exit 1
fi
# Imports come from this checkout. A stale PYTHONPATH must not win.
export PYTHONPATH="$REPO"

# ── freshness check helper ────────────────────────────────────────────────────
# Prints "fresh" if SPY has a coherent session at the readiness floor, else "stale".
_check_freshness() {
    "$PYTHON" - "$STORE" "$REPO" <<'PYEOF'
import sys
from datetime import timedelta

store = sys.argv[1]
repo = sys.argv[2]

# Resolve the calendar and canonical matrix-session truth from the same source
# modules used by the builder.  OI may already be on D while Greeks/EOD remain
# on settled S=D-1; only their latest positive-spot intersection is publishable.
sys.path.insert(0, repo)
from engine.thetadata_store import latest_options_matrix_session
from lib.nyse_calendar import expected_last_session, last_session_on_or_before

expected = expected_last_session()
required = last_session_on_or_before(expected - timedelta(days=1))
coherent = latest_options_matrix_session("SPY", store=store)

if coherent is not None and coherent >= required.isoformat():
    print("fresh")
else:
    print("stale")
PYEOF
}

# Bounded freshness read. Sets status to the first stdout line (fresh/stale),
# "timeout", or "error". The first 20 stderr lines are copied to the job log.
# A child in uninterruptible sleep cannot be killed; the marker still lets the
# retry budget move on, and that child may outlive the job.
_read_freshness_bounded() {
    _gate_dir=$(mktemp -d "${TMPDIR:-/tmp}/options_matrix_gate.XXXXXX")
    (
        _check_freshness
    ) > "$_gate_dir/out" 2> "$_gate_dir/err" &
    _gate_reader_pid=$!

    (
        _gate_elapsed=0
        while [ "$_gate_elapsed" -lt "$GATE_READ_TIMEOUT_SECS" ]; do
            if ! kill -0 "$_gate_reader_pid" 2>/dev/null; then
                exit 0
            fi
            sleep 1
            _gate_elapsed=$((_gate_elapsed + 1))
        done
        if ! kill -0 "$_gate_reader_pid" 2>/dev/null; then
            exit 0
        fi
        touch "$_gate_dir/timeout"
        # Snapshot children before TERM. Killing the reader reparents them, so a
        # later pkill -P cannot see a child that ignored TERM.
        _gate_kids=$(pgrep -P "$_gate_reader_pid" 2>/dev/null || true)
        pkill -TERM -P "$_gate_reader_pid" 2>/dev/null || true
        for _gate_kid in $_gate_kids; do
            kill -TERM "$_gate_kid" 2>/dev/null || true
        done
        kill -TERM "$_gate_reader_pid" 2>/dev/null || true
        sleep 10
        pkill -KILL -P "$_gate_reader_pid" 2>/dev/null || true
        for _gate_kid in $_gate_kids; do
            kill -KILL "$_gate_kid" 2>/dev/null || true
        done
        kill -KILL "$_gate_reader_pid" 2>/dev/null || true
        exit 0
    ) >/dev/null 2>&1 &
    _gate_watch_pid=$!

    _gate_rc=0
    wait "$_gate_reader_pid" 2>/dev/null || _gate_rc=$?
    if [ -f "$_gate_dir/timeout" ]; then
        wait "$_gate_watch_pid" 2>/dev/null || true
    else
        kill -TERM "$_gate_watch_pid" 2>/dev/null || true
        wait "$_gate_watch_pid" 2>/dev/null || true
    fi

    if [ -f "$_gate_dir/timeout" ]; then
        status=timeout
    elif [ "$_gate_rc" -eq 0 ]; then
        status=""
        IFS= read -r status < "$_gate_dir/out" || true
    else
        status=error
    fi

    _gate_n=0
    _gate_line=""
    if [ -f "$_gate_dir/err" ]; then
        while IFS= read -r _gate_line; do
            _gate_n=$((_gate_n + 1))
            if [ "$_gate_n" -gt 20 ]; then
                break
            fi
            printf '%s\n' "[options_matrix] gate stderr: ${_gate_line}"
        done < "$_gate_dir/err"
    fi

    rm -rf "$_gate_dir"
    return 0
}

# ── freshness gate ────────────────────────────────────────────────────────────
if [ "${MATRIX_FRESHNESS_BYPASS:-0}" = "1" ]; then
    echo "[options_matrix] MATRIX_FRESHNESS_BYPASS=1 — skipping freshness gate"
else
    MAX_ATTEMPTS=6
    SLEEP_SECS=1200   # 20 min
    GATE_READ_TIMEOUT_SECS=600

    attempt=1
    while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
        _read_freshness_bounded
        if [ "$status" = "fresh" ]; then
            echo "[options_matrix] store fresh (attempt $attempt/$MAX_ATTEMPTS) — proceeding"
            break
        fi
        if [ "$status" = "timeout" ]; then
            echo "[options_matrix] freshness read timed out after ${GATE_READ_TIMEOUT_SECS}s (attempt $attempt/$MAX_ATTEMPTS)"
        fi
        echo "[options_matrix] store not fresh yet (attempt $attempt/$MAX_ATTEMPTS) — sleeping ${SLEEP_SECS}s"
        if [ "$attempt" -eq "$MAX_ATTEMPTS" ]; then
            echo "[options_matrix] ERROR: store still not fresh after $MAX_ATTEMPTS attempts — aborting"
            exit 1
        fi
        sleep "$SLEEP_SECS"
        attempt=$((attempt + 1))
    done
fi

# ── run builder ───────────────────────────────────────────────────────────────
if [ "${MATRIX_NO_PUBLISH:-0}" = "1" ]; then
    echo "[options_matrix] MATRIX_NO_PUBLISH=1 — launching build_options_matrix (local only, no R2 publish)"
    cd "$REPO"
    "$PYTHON" -m scripts.build_options_matrix
    BUILD_RC=$?
else
    echo "[options_matrix] launching build_options_matrix --publish"
    cd "$REPO"
    "$PYTHON" -m scripts.build_options_matrix --publish
    BUILD_RC=$?
    # GEX_STATE_PUBLICATION_OWNER=com.mastermind.gexstate-mirror
    # Public gex_state projection is intentionally absent here. This job runs
    # from the mixed-vintage flow-ops tree; allowing it to write that prefix
    # raced the clean publisher and reintroduced July payloads in August.
fi

exit "$BUILD_RC"
