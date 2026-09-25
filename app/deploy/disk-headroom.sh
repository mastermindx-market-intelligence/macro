#!/usr/bin/env bash
# Fail-closed disk headroom gate for the high-frequency Macro deploy checkout.
# This guard only observes storage/Git shape; it never performs repository GC.
set -euo pipefail

APP_DIR="${MACRO_APP_DIR:-/opt/macro}"
MIN_FREE_KIB="${MACRO_UPDATE_MIN_FREE_KIB:-12582912}"

case "$MIN_FREE_KIB" in
  ''|*[!0-9]*)
    echo "macro-update: invalid MACRO_UPDATE_MIN_FREE_KIB=$MIN_FREE_KIB" >&2
    exit 64
    ;;
esac

FREE_KIB=$(df -Pk "$APP_DIR" | awk 'NR == 2 {print $4}')
case "$FREE_KIB" in
  ''|*[!0-9]*)
    echo "macro-update: unable to read disk headroom for $APP_DIR" >&2
    exit 74
    ;;
esac

if [ "$FREE_KIB" -lt "$MIN_FREE_KIB" ]; then
  STATS=$(git -C "$APP_DIR" count-objects -v 2>/dev/null || true)
  PACKS=$(printf '%s\n' "$STATS" | awk '$1 == "packs:" {print $2}')
  PACK_KIB=$(printf '%s\n' "$STATS" | awk '$1 == "size-pack:" {print $2}')
  echo "macro-update: LOW_DISK_HOLD free_kib=$FREE_KIB min_free_kib=$MIN_FREE_KIB git_packs=${PACKS:-unknown} git_size_pack_kib=${PACK_KIB:-unknown}; refusing fetch/reset" >&2
  exit 75
fi
