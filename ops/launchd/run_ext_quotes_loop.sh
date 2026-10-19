#!/bin/sh
# ops/launchd/run_ext_quotes_loop.sh — one finite overnight BOATS session runner.
#
# Called by com.macro.extquotes.plist (via run_with_env.sh) ONCE per evening at
# 17:00 in the Mac's real timezone (America/Vancouver), which is 20:00 ET.  It
# execs the bounded Python session runner (scripts.run_boats_session), which
# covers one real overnight session (20:00→04:00 ET) as sequential bounded
# incumbent publish_boats_stream segments and then exits.
#
# There is deliberately NO polling loop and NO self-rescheduling here: launchd
# fires the next session at the next StartCalendarInterval.  A crashed or
# refused run is NOT retried — the Python runner's permanent per-session start
# receipt blocks any same-session replay until lawful manual reconciliation.
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
[ -d "$REPO_ROOT" ] || fail_closed "repo root missing: $REPO_ROOT"
[ -f "$REPO_ROOT/scripts/run_boats_session.py" ] || fail_closed "runner module missing in repo"
[ -r "$BOATS_SYMBOLS_FILE" ] || fail_closed "symbols file not readable: $BOATS_SYMBOLS_FILE"
[ -d "$BOATS_ARCHIVE_ROOT" ] || fail_closed "archive root missing: $BOATS_ARCHIVE_ROOT"

# One finite session: validate config, then hand over to the bounded Python
# runner via exec so its exit status is launchd's exit status.
cd "$REPO_ROOT" || fail_closed "cannot enter repo root"
log "starting one bounded overnight BOATS session (messages=$BOATS_TOTAL_MAX_MESSAGES)"
PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m "$MODULE" \
    --publish \
    --symbols-file "$BOATS_SYMBOLS_FILE" \
    --archive-root "$BOATS_ARCHIVE_ROOT" \
    --total-max-messages "$BOATS_TOTAL_MAX_MESSAGES" \
    --max-segments "${BOATS_MAX_SEGMENTS:-32}" \
    --segment-max-seconds "${BOATS_SEGMENT_MAX_SECONDS:-3600}"
