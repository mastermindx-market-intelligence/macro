#!/bin/sh
# ops/launchd/run_ext_quotes_loop.sh — one finite overnight BOATS session runner.
#
# Calendar candidates at 17:00 and 18:00 Vancouver cover permanent UTC-7
# and older host timezone data. --scheduled admits only the candidate just
# after 20:00 New York; it cannot relaunch a failed or completed session.
# One admitted run covers the finite 20:00-04:00 ET overnight window.
#
# There is deliberately NO polling loop and NO self-rescheduling here: launchd
# fires the next session at the next StartCalendarInterval.  A crashed or
# refused run is NOT retried — the Python runner's permanent per-session start
# receipt blocks any same-session replay until lawful manual reconciliation.
# Reconciliation retains both receipts and the original run: inspect its final
# result, archive and publication evidence and confirm no live lock holder.
# Missing final evidence is an unknown effect. Never delete or move the start
# receipt to rerun this session; the next calendar session has a distinct receipt.
#
# DEPLOYMENT CONFIGURATION (fail closed): every value below must be present,
# either in the environment exported by run_with_env.sh from .env, or set here.
# The runner refuses to start when any is missing; it never installs itself and
# never writes outside the configured archive.
#   BOATS_SYMBOLS_FILE          bounded line-oriented BOATS coverage file
#   BOATS_ARCHIVE_ROOT          the existing mounted Tiingo archive root
#   BOATS_TOTAL_MAX_MESSAGES    explicit night message budget (<= 80000000)
#   BOATS_MAX_SEGMENTS          optional, default 32 (hard cap 32)
#   BOATS_SEGMENT_MAX_SECONDS   optional, default 3600 (hard cap 3600)
#
# R2 credentials are still sourced from .env by run_with_env.sh and are used
# only by the incumbent storage client inside the incumbent publisher.  This
# script never sees, moves or copies them.
#
# PYTHONPATH must include the repo root (set in the plist EnvironmentVariables).

PYTHON="${BOATS_PYTHON:-/opt/homebrew/Caskroom/miniconda/base/bin/python}"
MODULE="scripts.run_boats_session"
REPO_ROOT="${BOATS_REPO_ROOT:-/Users/chriswong/Documents/Cluade/Macro Dashboard}"

log() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S') [boats-night] $*"
}

fail_closed() {
    log "refusing to start: $1"
    exit 1
}

[ -n "$BOATS_SYMBOLS_FILE" ] || fail_closed "BOATS_SYMBOLS_FILE is not configured"
[ -n "$BOATS_ARCHIVE_ROOT" ] || fail_closed "BOATS_ARCHIVE_ROOT is not configured"
[ -n "$BOATS_TOTAL_MAX_MESSAGES" ] || fail_closed "BOATS_TOTAL_MAX_MESSAGES is not configured"
[ -x "$PYTHON" ] || fail_closed "python interpreter missing: $PYTHON"
[ -x /usr/bin/caffeinate ] || fail_closed "macOS power assertion helper missing"
[ -d "$REPO_ROOT" ] || fail_closed "repo root missing: $REPO_ROOT"
[ -f "$REPO_ROOT/scripts/run_boats_session.py" ] || fail_closed "runner module missing in repo"
[ -r "$BOATS_SYMBOLS_FILE" ] || fail_closed "symbols file not readable: $BOATS_SYMBOLS_FILE"
[ -d "$BOATS_ARCHIVE_ROOT" ] || fail_closed "archive root missing: $BOATS_ARCHIVE_ROOT"

# One finite session: validate config, then hand over to the bounded Python
# runner via exec so its exit status is launchd's exit status.
cd "$REPO_ROOT" || fail_closed "cannot enter repo root"
log "starting one bounded overnight BOATS session (messages=$BOATS_TOTAL_MAX_MESSAGES)"
# Hold the power assertion only for this bounded command; no power settings change.
PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" exec /usr/bin/caffeinate -i -s "$PYTHON" -m "$MODULE" \
    --publish --scheduled \
    --symbols-file "$BOATS_SYMBOLS_FILE" \
    --archive-root "$BOATS_ARCHIVE_ROOT" \
    --total-max-messages "$BOATS_TOTAL_MAX_MESSAGES" \
    --max-segments "${BOATS_MAX_SEGMENTS:-32}" \
    --segment-max-seconds "${BOATS_SEGMENT_MAX_SECONDS:-3600}"
