#!/usr/bin/env bash
# Stop the VPS live plane and recover the pre-cutover live path.
#
# This is intentionally non-destructive: externally published artifacts are
# moved to a timestamped backup so Caddy immediately falls back to the last
# site.served copies, and private state/data remain available for diagnosis.
set -euo pipefail

BASE_DIR="/var/lib/macro-live"
PUBLIC_DIR="$BASE_DIR/public"
LEGACY_CRON='*/5 1-21 * * 1-5 /usr/local/bin/macro-live >> /var/log/macro-live.log 2>&1'
log() { echo "[live-rollback] $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "live-rollback must run as root" >&2
  exit 1
fi

log "[1/3] stop replacement timers"
# Every lane writing into PUBLIC_DIR must be drained before it is moved.
# A failed stop is not evidence of absence, and manual producer invocations
# are excluded through the same durable lock inodes used during publication.
stop_live_unit() {
  local unit=$1 state main control
  if ! systemctl stop "$unit" >/dev/null 2>&1; then
    [ ! -e "/etc/systemd/system/$unit" ] && [ ! -L "/etc/systemd/system/$unit" ] || return 1
    [ "$(systemctl show -p LoadState --value "$unit")" = not-found ]
    return
  fi
  state=$(systemctl show -p ActiveState --value "$unit") || return 1
  main=$(systemctl show -p MainPID --value "$unit") || return 1
  control=$(systemctl show -p ControlPID --value "$unit") || return 1
  case "$state" in inactive|failed) ;; *) return 1 ;; esac
  case "$main:$control" in 0:0|:) ;; *) return 1 ;; esac
}
lanes=(fast releases snapshot bars prophet closepass breadth)
for lane in "${lanes[@]}"; do
  unit="macro-live-$lane.timer"
  stop_live_unit "$unit"
  if [ -e "/etc/systemd/system/$unit" ] || [ -L "/etc/systemd/system/$unit" ]; then
    systemctl disable "$unit" >/dev/null
  fi
done
for lane in "${lanes[@]}"; do stop_live_unit "macro-live-$lane.service"; done
STATE_DIR="$BASE_DIR/state"
if [ -r /etc/macro-live.env ]; then
  value=$(sed -n 's/^MACRO_LIVE_STATE_DIR=//p' /etc/macro-live.env | tail -n 1)
  value=${value#\"}; value=${value%\"}
  [ -z "$value" ] || STATE_DIR=$value
  value=$(sed -n 's/^MACRO_LIVE_DIR=//p' /etc/macro-live.env | tail -n 1)
  value=${value#\"}; value=${value%\"}
  [ -z "$value" ] || PUBLIC_DIR=$(dirname "$value")
fi
case "$STATE_DIR:$PUBLIC_DIR" in /*:/*) ;; *) exit 1 ;; esac
mkdir -p "$STATE_DIR"
exec 8>"$STATE_DIR/fast.lock"
flock -n 8 || { log "rollback held by an active fast invocation"; exit 1; }
exec 9>"$STATE_DIR/release_publications.lock"
flock -n 9 || { log "rollback held by an active release producer"; exit 1; }

log "[2/3] restore legacy cron writer if needed"
tmp_cron=$(mktemp)
cleanup() { rm -f "$tmp_cron"; }
trap cleanup EXIT
crontab -l 2>/dev/null > "$tmp_cron" || true
if ! grep -qF '/usr/local/bin/macro-live' "$tmp_cron"; then
  echo "$LEGACY_CRON" >> "$tmp_cron"
  crontab "$tmp_cron"
fi
cleanup
trap - EXIT

log "[3/3] withdraw external browser artifacts"
if [ -d "$PUBLIC_DIR" ]; then
  backup_dir="$BASE_DIR/public.rollback.$(date -u +%Y%m%dT%H%M%SZ)"
  mv "$PUBLIC_DIR" "$backup_dir"
  log "external artifacts preserved at $backup_dir"
fi
# The last-good release sidecar travels with the public directory above, and
# the producer's retained state (release_publications_state.json, its pacing
# rows and its single-writer lock) stays in $BASE_DIR/state — so re-arming
# the release lane later resumes with the SAME retained pacing instead of
# starting from an empty state.

log "DONE — legacy cron is primary; private state/data were retained"
