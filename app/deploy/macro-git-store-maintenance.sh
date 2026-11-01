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
#
# Kept tier (2026-11-01 second refill): the connected history is almost all
# reachable, so a nightly full repack would rewrite the whole store (tens of
# GiB) to reclaim nearly nothing, and needs that much free space on root.
# Instead, every consolidated non-cruft pack of at least PROMOTE_KIB gets a
# `.keep` and becomes part of a frozen base tier. `git repack` never rewrites
# or deletes a kept pack (on this non-bare, bitmap-less clone it honors
# .keep), so each night only rewrites the packs added since the last
# promotion: about one day of pulls plus at most PROMOTE_KIB. Unreachable
# objects inside a kept pack are never reclaimed; a full recovery repack
# (README) reclaims them if that ever matters.
#
# Space fallback: when even the non-kept packs do not fit (nights of missed
# runs, or a consolidated pack just under PROMOTE_KIB), the job freezes non-kept,
# non-cruft packs into the kept tier, largest first, until the repack fits, at
# most FALLBACK_MAX of them. If freezing that many would still not make it fit,
# it freezes nothing and refuses. Each freeze is logged. The memory check runs
# before any freeze, so a deferred run leaves the kept tier as it found it.
# Orphaned packs (a `.pack` with no `.idx` and no `.keep`, older than 6 h, which
# Git never reads) are removed and do not count toward the space the repack
# needs. Free space, MemAvailable and every numeric setting must read as whole
# numbers, or the job refuses before it writes anything.
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
# A consolidated non-cruft pack at least this large joins the kept base tier
# (KiB; 2 GiB). It bounds what each night rewrites and must free on root.
PROMOTE_KIB="${MACRO_GIT_MAINT_PROMOTE_KIB:-2097152}"
# Most packs the space fallback may freeze in one run (0 disables it). Each
# frozen pack stays in the kept tier until a full recovery repack.
FALLBACK_MAX="${MACRO_GIT_MAINT_FALLBACK_MAX:-16}"

log() { echo "macro-git-store-maintenance: $*"; }
for setting in LOCK_WAIT MARGIN_KIB MIN_MEMAVAIL_KIB PROMOTE_KIB FALLBACK_MAX; do
	if ! [[ ${!setting} =~ ^[0-9]+$ ]]; then
		log "REFUSED: $setting='${!setting}' is not a whole number; nothing written"
		exit 1
	fi
done
g() { git -C "$APP_DIR" -c gc.auto=0 "$@"; }
store_kib() {
	g count-objects -v | awk '/^size-pack:/{p=$2} /^size:/{l=$2} END{print p + l}'
}
pack_kib() { echo $(( $(wc -c < "$1") / 1024 )); }
# KiB of every pack a repack would rewrite: all indexed packs without a .keep
# (the cruft pack included, since it is rewritten to age its objects out). A
# pack without an .idx is invisible to Git, so the repack never rewrites it.
unkept_pack_kib() {
	local p sum=0
	for p in "$OBJECTS"/pack/pack-*.pack; do
		[ -e "$p" ] || continue
		[ -e "${p%.pack}.keep" ] && continue
		[ -e "${p%.pack}.idx" ] || continue
		sum=$((sum + $(pack_kib "$p")))
	done
	echo "$sum"
}
kept_pack_count() {
	local p n=0
	for p in "$OBJECTS"/pack/pack-*.keep; do
		[ -e "$p" ] && n=$((n + 1))
	done
	echo "$n"
}
# Freeze large consolidated packs into the kept tier. Skips cruft packs
# (.mtimes: they must stay rewritable to expire), packs without an index yet,
# and any pack that already has a .keep: a .keep written by someone else
# (an in-flight index-pack) is never touched, here or anywhere in this job.
promote_large_packs() {
	local p base kib
	for p in "$OBJECTS"/pack/pack-*.pack; do
		[ -e "$p" ] || continue
		base=${p%.pack}
		[ -e "$base.keep" ] && continue
		[ -e "$base.mtimes" ] && continue
		[ -e "$base.idx" ] || continue
		kib=$(pack_kib "$p")
		[ "$kib" -ge "$PROMOTE_KIB" ] || continue
		echo "macro-git-store-maintenance kept tier $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$base.keep"
		log "kept tier: ${base##*/} (${kib} KiB) frozen as a base pack"
	done
}
# Print "<KiB> <path without .pack>" for every pack the space fallback may
# freeze (same eligibility as promote_large_packs, any size), largest first.
fallback_candidates() {
	local p base
	for p in "$OBJECTS"/pack/pack-*.pack; do
		[ -e "$p" ] || continue
		base=${p%.pack}
		[ -e "$base.keep" ] && continue
		[ -e "$base.mtimes" ] && continue
		[ -e "$base.idx" ] || continue
		echo "$(pack_kib "$p") $base"
	done | sort -rn
}
# Remove orphaned packs. Git finds a pack only through its .idx, so a .pack
# without one is never read, whatever left it there (an interrupted write or an
# interrupted removal). A .keep means someone owns it (an in-flight fetch writes
# its .keep first): never touched. Six hours excludes any write still in
# progress.
remove_orphan_packs() {
	local p base ext
	while IFS= read -r p; do
		base=${p%.pack}
		[ -e "$base.idx" ] && continue
		[ -e "$base.keep" ] && continue
		for ext in pack rev mtimes bitmap; do
			if [ -e "$base.$ext" ]; then
				rm -f "$base.$ext"
				log "removed orphan ${base##*/}.$ext (no .idx, older than 6 h)"
			fi
		done
	done < <(find "$OBJECTS/pack" -maxdepth 1 -type f -name 'pack-*.pack' -mmin +360)
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
remove_orphan_packs

# 3. Memory gate, kept tier, then the space gate. The memory gate comes first so
#    a deferred run freezes nothing. A repack writes its new packs before it
#    deletes the old ones, so the worst case is every pack it will rewrite (the
#    non-kept ones) plus the loose objects, again, plus a margin for the pull,
#    which keeps fetching while this runs. Kept packs are never rewritten, so
#    they do not count. A .keep is only metadata: writing one is safe even when
#    the gate then refuses. When the non-kept packs do not fit, the space
#    fallback freezes the largest ones until it fits, or nothing.
MEMAVAIL_KIB=$(awk '/^MemAvailable:/{print $2}' "$MEMINFO" 2>/dev/null) || MEMAVAIL_KIB=""
if ! [[ $MEMAVAIL_KIB =~ ^[0-9]+$ ]]; then
	log "REFUSED: could not read MemAvailable from $MEMINFO (got '${MEMAVAIL_KIB}'); no pack written"
	exit 1
fi
if [ "$MEMAVAIL_KIB" -lt "$MIN_MEMAVAIL_KIB" ]; then
	log "DEFERRED: MemAvailable ${MEMAVAIL_KIB} KiB < ${MIN_MEMAVAIL_KIB} KiB (another heavy job is running); no pack written"
	exit 75
fi
promote_large_packs
BEFORE_KIB=$(store_kib)
LOOSE_KIB=$(g count-objects -v | awk '/^size:/{print $2}')
UNKEPT_KIB=$(unkept_pack_kib)
NEED_KIB=$((UNKEPT_KIB + LOOSE_KIB + MARGIN_KIB))
AVAIL_KIB=$(df --output=avail -k "$OBJECTS" 2>/dev/null | tail -n 1 | tr -d ' ') || AVAIL_KIB=""
if ! [[ $AVAIL_KIB =~ ^[0-9]+$ ]]; then
	log "REFUSED: could not read free space on $OBJECTS (got '${AVAIL_KIB}'); no pack written"
	exit 1
fi
if [ "$AVAIL_KIB" -lt "$NEED_KIB" ]; then
	# Plan first, freeze only if the plan fits: largest first, at most
	# FALLBACK_MAX packs.
	FALLBACK_PLAN=()
	PLAN_NEED_KIB=$NEED_KIB
	while read -r kib base; do
		if [ "${#FALLBACK_PLAN[@]}" -ge "$FALLBACK_MAX" ]; then break; fi
		FALLBACK_PLAN+=("$kib $base")
		PLAN_NEED_KIB=$((PLAN_NEED_KIB - kib))
		if [ "$PLAN_NEED_KIB" -le "$AVAIL_KIB" ]; then break; fi
	done < <(fallback_candidates)
	if [ "${#FALLBACK_PLAN[@]}" -gt 0 ] && [ "$PLAN_NEED_KIB" -le "$AVAIL_KIB" ]; then
		for entry in "${FALLBACK_PLAN[@]}"; do
			read -r kib base <<<"$entry"
			echo "macro-git-store-maintenance kept tier (space fallback) $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$base.keep"
			log "kept tier fallback: ${base##*/} (${kib} KiB) frozen so the repack fits in ${AVAIL_KIB} KiB"
		done
		UNKEPT_KIB=$(unkept_pack_kib)
		NEED_KIB=$((UNKEPT_KIB + LOOSE_KIB + MARGIN_KIB))
	else
		log "kept tier fallback: freezing up to ${FALLBACK_MAX} packs would not make the repack fit; nothing frozen"
	fi
fi
if [ "$AVAIL_KIB" -lt "$NEED_KIB" ]; then
	log "REFUSED: repack needs ${NEED_KIB} KiB free on $OBJECTS (${UNKEPT_KIB} KiB of non-kept packs, ${LOOSE_KIB} KiB loose, ${MARGIN_KIB} KiB margin), ${AVAIL_KIB} KiB available; no pack written (recovery: app/deploy/README.md, 'Git store maintenance')"
	exit 1
fi

# 4. Consolidate. Without the updater lock: like auto-gc, repack is safe next
#    to fetch/reset (new packs it did not list are never deleted, and old packs
#    are removed only after the replacement is in place). -l keeps it local;
#    --cruft keeps recently unreachable objects instead of deleting them.
#    Objects already in a kept pack are left there (repack.packKeptObjects is
#    pinned false here), so the new pack holds only the newer objects.
log "store before: ${BEFORE_KIB} KiB ($(kept_pack_count) kept packs; rewriting ${UNKEPT_KIB} KiB of non-kept packs and ${LOOSE_KIB} KiB loose); free: ${AVAIL_KIB} KiB"
nice -n 19 ionice -c 3 git -C "$APP_DIR" -c gc.auto=0 -c pack.threads=1 \
	-c pack.windowMemory="$WINDOW_MEMORY" -c pack.deltaCacheSize=32m \
	-c repack.packKeptObjects=false \
	repack -d -l --cruft --cruft-expiration="$GRACE"
promote_large_packs

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
log "store after: ${AFTER_KIB} KiB ($(g count-objects -v | awk '/^packs:/{print $2}') packs, $(kept_pack_count) kept); free: $(df --output=avail -k "$OBJECTS" | tail -n 1 | tr -d ' ') KiB"
