#!/usr/bin/env bash
# Install the VPS-owned live plane.
#
# Architecture:
#   macro-live-fast     every ~60s: display quotes, staggered overlay/risk/China
#                       state, 10-min heatmap. It is NOT the release writer any
#                       more — the official release watcher used to run here and
#                       a slow quote/risk leaf decided when a publication was
#                       detected.
#   macro-live-releases every 2s wake: the official release publication lane.
#                       Same incumbent producer (scripts/watch_release_publications),
#                       its own lane and timer, so its timing no longer depends
#                       on the quote/risk leaves. The wake rate is NOT the
#                       request rate: the retained per-source pacing state
#                       decides when a source is actually probed.
#   macro-live-snapshot every ~5m:  full-universe quote snapshot + US/HK baskets
#   macro-live-bars     hourly RTH: external intraday cache + flow pulse
#   macro-live-prophet  every ~5m in the ET session: Prophet Live provisional states
#                       (reads the two lanes above off disk, publishes R2 + the GATED
#                       live/prophet_live.json). Needs R2_* in /etc/macro-live.env.
#   macro-live-closepass every ~5m 20:00-23:59Z: mirrors the evening close-pass
#                       provisional board from R2 to the GATED
#                       live/us_board_provisional.json. Pure transport — it never
#                       computes. Needs R2_* in /etc/macro-live.env.
#   macro-live-breadth  every ~2m across the US session: the live intraday
#                       market-breadth poller (adv/dec/pa50/pa200/net_nh),
#                       writing the CANONICAL live/breadth.json this box serves.
#                       Reads the nightly-baked close caches off disk; a fault
#                       here can never take the served site down (own artifact
#                       only, own atomic rename). Was previously unowned by any
#                       VPS install — only the coarse GH-cron backstop ran it.
#
# All browser artifacts are atomically published to /var/lib/macro-live/public,
# outside /opt/macro and /opt/macro/site.served. Canonical history, forward ledgers,
# calibration and full renders remain on the nightly Mac/PC workflows.
set -euo pipefail

APP_DIR="/opt/macro"
VENV="$APP_DIR/.venv"
BASE_DIR="/var/lib/macro-live"
PUBLIC_DIR="$BASE_DIR/public"
LIVE_DIR="$PUBLIC_DIR/live"
STATE_DIR="$BASE_DIR/state"
log() { echo "[live-setup] $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "live-setup must run as root" >&2
  exit 1
fi

# BEGIN LIVE_SETUP_TRANSACTION
# Preserve the pre-install unit bytes and timer intent on both first install
# and rerun. A failed release handoff must not strand the incumbent fast lane.
initial_install=1
[ ! -e /etc/systemd/system/macro-live-fast.timer ] || initial_install=0
setup_complete=0
handoff_started=0
backup=""
tmp_cron=""
fast_lock_held=0
release_was_present=0
release_was_active=0
unit_names=(
  macro-live-fast.service macro-live-fast.timer
  macro-live-releases.service macro-live-releases.timer
  macro-live-snapshot.service macro-live-snapshot.timer
  macro-live-bars.service macro-live-bars.timer
  macro-live-prophet.service macro-live-prophet.timer
  macro-live-closepass.service macro-live-closepass.timer
  macro-live-breadth.service macro-live-breadth.timer
)
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
lock_fast_lane() {
  [ "$fast_lock_held" -eq 0 ] || return 0
  exec 8>"$STATE_DIR/fast.lock"
  flock -n 8 || return 1
  fast_lock_held=1
}
backup_live_units() {
  backup=$(mktemp -d)
  for unit in "${unit_names[@]}"; do
    # An operator-managed link/mask is not replaced by this installer.
    [ ! -L "/etc/systemd/system/$unit" ] || {
      log "preserving operator-managed $unit; setup stopped"; return 1;
    }
    if [ -f "/etc/systemd/system/$unit" ]; then
      cp "/etc/systemd/system/$unit" "$backup/$unit"
    fi
    case "$unit" in
      *.timer)
        if systemctl is-enabled "$unit" >/dev/null 2>&1; then touch "$backup/$unit.enabled"; fi
        if systemctl is-active "$unit" >/dev/null 2>&1; then touch "$backup/$unit.active"; fi ;;
    esac
  done
  [ ! -f "$backup/macro-live-releases.timer" ] || release_was_present=1
  [ ! -f "$backup/macro-live-releases.timer.active" ] || release_was_active=1
}
restore_live_units() {
  # A fast smoke runs after releasing fast.lock. Re-establish exclusion here;
  # an earlier drain is not proof that a later invocation has finished.
  for unit in "${unit_names[@]}"; do
    case "$unit" in *.timer) stop_live_unit "$unit" || return 1 ;; esac
  done
  for unit in "${unit_names[@]}"; do
    case "$unit" in *.service) stop_live_unit "$unit" || return 1 ;; esac
  done
  lock_fast_lane || return 1
  exec 9>"$STATE_DIR/release_publications.lock"
  flock -n 9 || return 1
  for unit in "${unit_names[@]}"; do
    case "$unit" in
      *.timer)
        if [ -e "/etc/systemd/system/$unit" ]; then
          systemctl disable "$unit" >/dev/null 2>&1 || return 1
        fi ;;
    esac
    if [ -f "$backup/$unit" ]; then
      install -m 0644 "$backup/$unit" "/etc/systemd/system/$unit" || return 1
    else
      rm -f "/etc/systemd/system/$unit" || return 1
    fi
  done
  systemctl daemon-reload || return 1
  if [ "$initial_install" -eq 1 ] && [ -d "$PUBLIC_DIR" ]; then
    failed_dir="$BASE_DIR/public.failed.$(date -u +%Y%m%dT%H%M%SZ)"
    mv "$PUBLIC_DIR" "$failed_dir" || return 1
    log "failed-install artifacts preserved at $failed_dir"
  fi
  # State and its lock inodes are never moved with the public directory.
  exec 9>&-
  exec 8>&-
  fast_lock_held=0
  for unit in "${unit_names[@]}"; do
    case "$unit" in
      *.timer)
        if [ -f "$backup/$unit.enabled" ]; then systemctl enable "$unit" >/dev/null || return 1; fi
        if [ -f "$backup/$unit.active" ]; then systemctl start "$unit" || return 1; fi ;;
    esac
  done
}
fail_safe_exit() {
  rc=$?
  trap - EXIT
  [ -z "$tmp_cron" ] || rm -f "$tmp_cron"
  if [ "$rc" -ne 0 ] && [ "$setup_complete" -eq 0 ] && [ "$handoff_started" -eq 1 ]; then
    if ! restore_live_units; then
      log "rollback held: writer drain or unit restoration failed; timers remain paused"
      log "pre-install units retained at $backup"
      exit "$rc"
    fi
    log "setup failed; previous units and timer intent restored"
  fi
  [ -z "$backup" ] || rm -rf "$backup"
  exit "$rc"
}
trap fail_safe_exit EXIT
# END LIVE_SETUP_TRANSACTION

log "[1/6] runtime + live directories"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y python3-venv rsync >/dev/null 2>&1 || true
test -d "$VENV" || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
# boto3 is the Prophet Live lane's ONLY extra dependency: the armed pack, the previous
# pass's artifact and the event spool are R2 objects, and without it r2io.client()
# returns None, the lane reads the public mirror, publishes nothing and writes no
# served copy. Adding it here is what makes a re-run of this script arm the lane.
"$VENV/bin/pip" install -q pandas pyarrow numpy requests pyyaml jinja2 datasketch boto3
install -d -m 0755 \
  "$PUBLIC_DIR" "$LIVE_DIR" "$PUBLIC_DIR/marketdata" \
  "$BASE_DIR/state" "$BASE_DIR/data" "$APP_DIR/site/live"

log "[2/6] environment"
if [ ! -e /etc/macro-live.env ]; then
  install -m 0600 /dev/null /etc/macro-live.env
fi
chmod 0600 /etc/macro-live.env
if ! grep -q '^MACRO_LIVE_DIR=' /etc/macro-live.env; then
  {
    echo "MACRO_LIVE_DIR=$LIVE_DIR"
    echo "MACRO_LIVE_STATE_DIR=$BASE_DIR/state"
    echo "MACRO_LIVE_DATA_DIR=$BASE_DIR/data"
  } >> /etc/macro-live.env
fi

# R2 credential seeding — the INITIATING FAULT of the 2026-07-30..08-26 US
# Prophet Live force majeure (27 days dark, exit 0 the whole time): this file
# documented "Needs R2_* in /etc/macro-live.env" above but never wrote them,
# and nothing verified the precondition before macro-live-prophet went live.
# /etc/macro-api.env already carries the same R2_* keys for the API's own R2
# reads, so they are durably re-seeded here instead of typed twice by an
# operator. Each key is guarded by ITS OWN presence check in the DESTINATION
# file (the sentinel style the MACRO_LIVE_DIR block above uses), so this is
# safe to run repeatedly: a rerun, or an operator who already set one key by
# hand, never overwrites a value already there, and a box seeded with only
# some of the four keys self-heals the rest on the next run instead of being
# stuck half-seeded forever. NEVER logs a secret VALUE — only a count of keys
# newly copied and, on a gap, which key NAMES are missing — because this
# script's stdout lands in journalctl, which is not a secret store.
R2_SEEDED_COUNT=0
R2_SEED_MISSING=()
for R2_KEY in R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET; do
  if grep -q "^${R2_KEY}=" /etc/macro-live.env; then
    continue
  fi
  if [ -r /etc/macro-api.env ] && grep -q "^${R2_KEY}=" /etc/macro-api.env; then
    grep "^${R2_KEY}=" /etc/macro-api.env | tail -n 1 >> /etc/macro-live.env
    R2_SEEDED_COUNT=$((R2_SEEDED_COUNT + 1))
  else
    R2_SEED_MISSING+=("$R2_KEY")
  fi
done
chmod 0600 /etc/macro-live.env
log "R2 credential seed: ${R2_SEEDED_COUNT} key(s) newly copied from /etc/macro-api.env"
if [ "${#R2_SEED_MISSING[@]}" -gt 0 ]; then
  log "WARNING: R2 credentials are INCOMPLETE — macro-live-prophet and macro-live-closepass will read the public mirror and publish NOTHING until this is fixed (this exact gap produced the 2026-07-30..08-26 force-majeure: 27 days dark, exit 0 throughout)."
  log "WARNING: missing key(s), absent from BOTH /etc/macro-live.env and /etc/macro-api.env: ${R2_SEED_MISSING[*]}"
  log "WARNING: OPERATOR ACTION REQUIRED — add the missing key(s) to /etc/macro-api.env (preferred; shared with the API's own R2 reads) or directly to /etc/macro-live.env (must stay mode 0600), then re-run this script."
fi

# Use the same configured paths as the service, without sourcing credentials.
for setting in MACRO_LIVE_STATE_DIR MACRO_LIVE_DIR; do
  value=$(sed -n "s/^${setting}=//p" /etc/macro-live.env | tail -n 1)
  value=${value#\"}; value=${value%\"}
  [ -z "$value" ] && continue
  case "$value" in /*) ;; *) log "invalid live directory setting"; exit 1 ;; esac
  case "$setting" in MACRO_LIVE_STATE_DIR) STATE_DIR=$value ;; MACRO_LIVE_DIR) LIVE_DIR=$value ;; esac
done
PUBLIC_DIR=$(dirname "$LIVE_DIR")
install -d -m 0755 "$STATE_DIR" "$LIVE_DIR"

log "[3/6] systemd services + timers"
unit_sources=()
for unit in \
  macro-live-fast.service macro-live-fast.timer \
  macro-live-releases.service macro-live-releases.timer \
  macro-live-snapshot.service macro-live-snapshot.timer \
  macro-live-bars.service macro-live-bars.timer \
  macro-live-prophet.service macro-live-prophet.timer \
  macro-live-closepass.service macro-live-closepass.timer \
  macro-live-breadth.service macro-live-breadth.timer
do
  unit_sources+=("$APP_DIR/app/deploy/$unit")
done
systemd-analyze verify "${unit_sources[@]}"
backup_live_units
handoff_started=1
stop_live_unit macro-live-fast.timer
stop_live_unit macro-live-fast.service
lock_fast_lane
stop_live_unit macro-live-releases.timer
stop_live_unit macro-live-releases.service
for unit_source in "${unit_sources[@]}"
do
  unit=$(basename "$unit_source")
  install -m 0644 "$APP_DIR/app/deploy/$unit" "/etc/systemd/system/$unit"
done
systemctl daemon-reload

log "[4/6] drain incumbent release writer, then smoke test publication + fast lane"
# The fast lane used to BE the release writer. The code installed above no
# longer runs the producer there, but a fast service that was ALREADY running
# when this script started still holds the old producer in memory. Drain it —
# and its timer — BEFORE the new release lane is armed in step [5/6], so two
# release writers can never overlap. The fast timer is re-armed in step [5/6].
# The drain and fast.lock acquisition above precede installation as well as smoke.
# Keep the legacy cron writer in place until the replacement has proven that it
# can publish successfully. A failed install therefore leaves the old live path
# intact instead of creating an outage.
release_smoke_rc=0
if [ "$release_was_present" -eq 0 ] || [ "$release_was_active" -eq 1 ]; then
  systemctl start macro-live-releases.service || release_smoke_rc=$?
fi
# The fast service takes this same lock. Release only after dedicated ownership
# is installed; failure restoration reacquires it before removing that marker.
exec 8>&-
fast_lock_held=0
smoke_rc=0
systemctl start macro-live-fast.service || smoke_rc=$?
if [ "$release_smoke_rc" -ne 0 ]; then
  log "release lane smoke test failed; recent service log:"
  journalctl -u macro-live-releases.service -n 30 --no-pager
  exit "$release_smoke_rc"
fi
if [ "$smoke_rc" -ne 0 ]; then
  log "smoke test failed; recent service log:"
  journalctl -u macro-live-fast.service -n 30 --no-pager
  exit "$smoke_rc"
fi
test -s "$LIVE_DIR/orchestrator_status.json"
test -s "$LIVE_DIR/quotes.json"
# The release output is a FIRST-CLASS smoke artifact: the lane that now owns
# the official publication must publish a valid sidecar, not merely exit 0.
if [ "$release_was_present" -eq 0 ] || [ "$release_was_active" -eq 1 ]; then
  "$VENV/bin/python" - "$LIVE_DIR/release_publications.json" <<'PY'
import json, sys
from datetime import datetime, timezone
payload = json.load(open(sys.argv[1]))
assert payload.get("schema") == "release_publications.v2"
for field in ("events", "publications", "due", "source_health"):
    assert isinstance(payload.get(field), list)
built = datetime.fromisoformat(payload["built"].replace("Z", "+00:00"))
assert built.tzinfo is not None
assert -5 <= (datetime.now(timezone.utc) - built).total_seconds() < 120
PY
fi
"$VENV/bin/python" -c \
  'import json,sys; d=json.load(open(sys.argv[1])); assert int((d.get("meta") or {}).get("resolved") or 0) >= 5' \
  "$LIVE_DIR/quotes.json"

log "[5/6] enable replacement timers"
# macro-live-prophet, macro-live-closepass and macro-live-breadth are armed here too,
# but none of the three is part of the fail-safe smoke transaction above: they consume
# what the three lanes publish (or, for breadth, the nightly-baked close caches) and
# write only their own runtime artifacts, so a fault in any of them can never take the
# served site down.
if [ "$release_was_present" -eq 0 ]; then
  systemctl enable --now macro-live-releases.timer
elif [ "$release_was_active" -eq 1 ]; then
  systemctl start macro-live-releases.timer
fi
systemctl enable --now \
  macro-live-fast.timer \
  macro-live-snapshot.timer \
  macro-live-bars.timer \
  macro-live-prophet.timer \
  macro-live-closepass.timer \
  macro-live-breadth.timer >/dev/null

log "[6/6] retire legacy cron writer"
tmp_cron=$(mktemp)
crontab -l 2>/dev/null | grep -v "macro-live\\|build_live_overlay" > "$tmp_cron" || true
crontab "$tmp_cron"
rm -f "$tmp_cron"
tmp_cron=""

setup_complete=1
[ -z "$backup" ] || rm -rf "$backup"
trap - EXIT
log "DONE — live plane installed"
systemctl list-timers \
  macro-live-fast.timer macro-live-releases.timer \
  macro-live-snapshot.timer macro-live-bars.timer \
  macro-live-prophet.timer macro-live-closepass.timer macro-live-breadth.timer \
  --no-pager
log "After production freshness is verified, set GitHub repository variable VPS_LIVE_PRIMARY=true."
