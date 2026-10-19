#!/usr/bin/env bash
# Bounded, fail-closed maintenance of the /opt/macro Git object store.
# Installed as /usr/local/sbin/macro-git-store-maintenance by update.sh and run
# once a day by macro-git-store-maintenance.timer (oneshot service).
#
# Why this exists (2026-10-19 root-disk incident): the 3-minute pull fetches
# every main commit and each fetch lands a new pack, but nothing ever
# consolidated them. `gc.auto=0` has been set in /opt/macro/.git/config since
# late August 2026. No script in this repository ever set it: auto-gc's last
# (failed) run is dated 2026-08-28 (`.git/gc.log`: "fatal: failed to run
# repack") and the setting was already present on 2026-09-06, so it was set by
# hand to stop background auto-gc repacks failing on a near-full disk. By
# 2026-10-19 the store was 41G in 263 packs and the root filesystem was full.
#
# gc.auto stays 0 on purpose: the pull must never spawn a detached repack that
# races it for disk. This job replaces auto-gc with an explicit run that checks
# free space BEFORE it writes, refuses visibly (non-zero exit, failed unit)
# when the space is not there, and never leaves the store half-written.
#
# History is preserved (MO-A-F04): nothing here fetches, deepens, truncates,
# converts or edits history or .git/shallow by hand. Repack only changes how
# the same reachable objects are stored; recently unreachable objects go to a
# cruft pack for the grace period, as `git gc` does.
set -euo pipefail

APP_DIR="${MACRO_GIT_MAINT_APP_DIR:-/opt/macro}"
LOCK="${MACRO_GIT_MAINT_LOCK:-/var/lock/macro-update.lock}"
LOCK_WAIT="${MACRO_GIT_MAINT_LOCK_WAIT:-600}"
# Free space required beyond the repack's own worst-case output (KiB).
MARGIN_KIB="${MACRO_GIT_MAINT_MARGIN_KIB:-3145728}"
# Grace for unreachable objects and loose objects (same default as `git gc`).
GRACE="${MACRO_GIT_MAINT_GRACE:-2.weeks.ago}"
# The droplet also runs macro-api and Terminal production builds; keep the
# repack's own memory small and bounded (the unit adds a cgroup cap on top).
WINDOW_MEMORY="${MACRO_GIT_MAINT_WINDOW_MEMORY:-128m}"
MIN_MEMAVAIL_KIB="${MACRO_GIT_MAINT_MIN_MEMAVAIL_KIB:-786432}"
MEMINFO="${MACRO_GIT_MAINT_MEMINFO:-/proc/meminfo}"

log() { echo "macro-git-store-maintenance: $*"; }
g() { git -C "$APP_DIR" -c gc.auto=0 "$@"; }
store_kib() {
	g count-objects -v | awk '/^size-pack:/{p=$2} /^size:/{l=$2} END{print p + l}'
}

[ -d "$APP_DIR/.git/objects" ] || { log "no Git store at $APP_DIR"; exit 1; }
OBJECTS=$(cd "$APP_DIR/.git/objects" && pwd -P)

# 1. Ref housekeeping under the updater's lock. reflog expire and pack-refs
#    take the ref locks that macro-update's `git reset --hard` needs; holding
#    the updater lock makes a pull tick skip (as it does behind a slow tick)
#    instead of failing on a held HEAD.lock. Seconds, not minutes.
exec 9>"$LOCK"
if ! flock -w "$LOCK_WAIT" 9; then
	log "DEFERRED: updater lock busy for ${LOCK_WAIT}s; nothing written"
	exit 75
fi
g reflog expire --expire-unreachable=now --expire=90.days.ago --all
g pack-refs --all --prune
exec 9>&-

# 2. Remove temporary packs left by a killed repack/pack-objects (a fetch's
#    own temporary pack is minutes old at most).
find "$OBJECTS/pack" -maxdepth 1 -type f \( -name 'tmp_*' -o -name '.tmp-*' \) \
	-mmin +360 -print -delete

# 3. Space and memory gates. A full repack writes its new packs before it
#    deletes the old ones, so the worst case is the whole current store again
#    plus a margin for the pull, which keeps fetching while this runs.
BEFORE_KIB=$(store_kib)
NEED_KIB=$((BEFORE_KIB + MARGIN_KIB))
AVAIL_KIB=$(df --output=avail -k "$OBJECTS" | tail -n 1 | tr -d ' ')
if [ "$AVAIL_KIB" -lt "$NEED_KIB" ]; then
	log "REFUSED: repack needs ${NEED_KIB} KiB free on $OBJECTS, ${AVAIL_KIB} KiB available; nothing written (recovery: app/deploy/README.md, 'Git store maintenance')"
	exit 1
fi
MEMAVAIL_KIB=$(awk '/^MemAvailable:/{print $2}' "$MEMINFO")
if [ "$MEMAVAIL_KIB" -lt "$MIN_MEMAVAIL_KIB" ]; then
	log "DEFERRED: MemAvailable ${MEMAVAIL_KIB} KiB < ${MIN_MEMAVAIL_KIB} KiB (another heavy job is running); nothing written"
	exit 75
fi

# 4. Consolidate. Without the updater lock: like auto-gc, repack is safe next
#    to fetch/reset (new packs it did not list are never deleted, and old packs
#    are removed only after the replacement is in place). -l keeps it local;
#    --cruft keeps recently unreachable objects instead of deleting them.
log "store before: ${BEFORE_KIB} KiB; free: ${AVAIL_KIB} KiB"
nice -n 19 ionice -c 3 git -C "$APP_DIR" -c gc.auto=0 -c pack.threads=1 \
	-c pack.windowMemory="$WINDOW_MEMORY" -c pack.deltaCacheSize=32m \
	repack -d -l --cruft --cruft-expiration="$GRACE"

# 5. Loose-object prune under the lock: a small fetch unpacks loose objects
#    that are unreferenced until its ref update lands, and the lock excludes
#    any in-flight pull. --expire keeps the grace window regardless.
exec 9>"$LOCK"
if flock -w "$LOCK_WAIT" 9; then
	g prune --expire="$GRACE"
	exec 9>&-
else
	log "updater lock busy for ${LOCK_WAIT}s; loose-object prune skipped this run"
fi
rm -f "$APP_DIR/.git/gc.log"

AFTER_KIB=$(store_kib)
log "store after: ${AFTER_KIB} KiB ($(g count-objects -v | awk '/^packs:/{print $2}') packs); free: $(df --output=avail -k "$OBJECTS" | tail -n 1 | tr -d ' ') KiB"
