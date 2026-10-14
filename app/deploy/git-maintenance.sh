#!/usr/bin/env bash
# Bounded maintenance for the production VPS shallow pull clone.
# See DSC-VPS-PULL-CLONE-REFLOG-PINS-PACK-DUPLICATION.
set -euo pipefail

APP_DIR="${MACRO_APP_DIR:-/opt/macro}"
MIN_FREE_KIB="${MACRO_GIT_MAINT_MIN_FREE_KIB:-12582912}"
MAX_PACKS="${MACRO_GIT_MAINT_MAX_PACKS:-48}"
MAX_PACK_KIB="${MACRO_GIT_MAINT_MAX_PACK_KIB:-8388608}"

exec 9>/var/lock/macro-update.lock
flock -w 1800 9

FREE_KIB=$(df -Pk "$APP_DIR" | awk 'NR == 2 {print $4}')
STATS=$(git -C "$APP_DIR" count-objects -v)
PACKS=$(printf '%s\n' "$STATS" | awk '$1 == "packs:" {print $2}')
PACK_KIB=$(printf '%s\n' "$STATS" | awk '$1 == "size-pack:" {print $2}')

for value in "$FREE_KIB" "$PACKS" "$PACK_KIB"; do
  case "$value" in ''|*[!0-9]*) echo "macro-git-maintenance: invalid preflight" >&2; exit 74;; esac
done

if [ "$FREE_KIB" -lt "$MIN_FREE_KIB" ]; then
  echo "macro-git-maintenance: HOLD free_kib=$FREE_KIB min_free_kib=$MIN_FREE_KIB; operator headroom required" >&2
  exit 75
fi

if [ "$PACKS" -lt "$MAX_PACKS" ] && [ "$PACK_KIB" -lt "$MAX_PACK_KIB" ]; then
  echo "macro-git-maintenance: no-op packs=$PACKS size_pack_kib=$PACK_KIB"
  exit 0
fi

echo "macro-git-maintenance: START packs=$PACKS size_pack_kib=$PACK_KIB free_kib=$FREE_KIB"
git -C "$APP_DIR" reflog expire --expire=now --expire-unreachable=now --all
git -C "$APP_DIR" -c pack.threads=1 -c pack.windowMemory=256m repack -adq --window=10 --depth=50
git -C "$APP_DIR" prune --expire=now
git -C "$APP_DIR" count-objects -vH
df -h "$APP_DIR"
echo "macro-git-maintenance: COMPLETE"
