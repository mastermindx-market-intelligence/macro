#!/usr/bin/env bash
# Install the VPS-owned live plane.
#
# Architecture:
#   macro-live-fast     every ~60s: official release watcher, display quotes,
#                       staggered overlay/risk/China state, 10-min heatmap
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
BASE_DIR="/var/lib/macro-live"
PUBLIC_DIR="$BASE_DIR/public"
LIVE_DIR="$PUBLIC_DIR/live"
log() { echo "[live-setup] $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "live-setup must run as root" >&2
  exit 1
fi
if [ "$#" -eq 0 ]; then
  # All source/runtime mutation enters the one installed updater owner.
  exec /usr/local/bin/macro-update --live-setup
fi
if [ "$#" -ne 2 ] || [ "$1" != --source-attempt ] || [[ ! "$2" =~ ^[0-9a-f]{32}$ ]]; then
  echo "live-setup: expected an original installed-owner invocation" >&2
  exit 2
fi
SETUP_ATTEMPT=$2
CAPSULE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
[ "$CAPSULE_DIR" = "$BASE_DIR/state/source-update-capsules/$SETUP_ATTEMPT/setup" ] || {
  echo "live-setup: script is not the original captured setup member" >&2
  exit 75
}
setup_control() {
  /usr/local/bin/macro-update --live-setup-control "$SETUP_ATTEMPT" "$1"
}
stage=$(setup_control inspect)

# Preserve the incumbent finalizer, but never undo a qualified publication or
# another timer's captured intent. Caddy's existing per-file existence matchers
# retain the legacy fallback for absent external files. Successfully published
# files and the original transaction evidence survive a later setup failure.
setup_complete=0
fail_safe_exit() {
  rc=$?
  trap - EXIT
  if [ "$rc" -ne 0 ] && [ "$setup_complete" -eq 0 ]; then
    log "setup incomplete; preserving original transaction and publication evidence"
    log "reconcile the installed owner's recorded step before resuming this attempt"
  fi
  exit "$rc"
}
trap fail_safe_exit EXIT

if [ "$stage" = PACKAGES ]; then
  log "[1/6] captured runtime + live directories"
  environment=$(setup_control environment)
  environment_mode="${environment%%$'\n'*}"
  VENV="${environment#*$'\n'}"
  if [ "$environment_mode" = prepare ]; then
    # A fresh environment is private to this original capsule until its imports
    # pass. Existing serving environments are never pip-upgraded by setup.
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y python3-venv rsync >/dev/null 2>&1 || true
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q pandas pyarrow numpy requests pyyaml jinja2 datasketch boto3
  elif [ "$environment_mode" = reuse ]; then
    log "reusing the captured environment; dependency changes require its maintenance owner"
  else
    echo "live-setup: invalid captured environment mode" >&2
    exit 75
  fi
  setup_control bind-environment
  VENV="$APP_DIR/.venv"
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

log "[3/6] captured ancillary services + timers"
# The fixed core six were installed and drained by macro-update before this
# script ran. Ancillary consumers retain their existing owner and timer intent.
source "$CAPSULE_DIR/../helpers/market-memory-options-unit-boundary.sh"
unit_sources=()
for unit in \
  macro-live-prophet.service macro-live-prophet.timer \
  macro-live-closepass.service macro-live-closepass.timer \
  macro-live-breadth.service macro-live-breadth.timer
do
  mm_unit_repair_inputs_safe "$CAPSULE_DIR/units/$unit" "/etc/systemd/system/$unit"
  unit_sources+=("$CAPSULE_DIR/units/$unit")
done
systemd-analyze verify "${unit_sources[@]}"
for unit_source in "${unit_sources[@]}"; do
  unit=$(basename "$unit_source")
  install -m 0644 "$unit_source" "/etc/systemd/system/$unit"
done
systemctl daemon-reload
sync -f /etc/systemd/system
setup_control ready
stage=$(setup_control inspect)
fi

if [ "$stage" = READY ]; then
  log "[4/6] new guarded invocation + publication proof"
  setup_control smoke
  stage=$(setup_control inspect)
fi

if [ "$stage" = SMOKED ] || [ "$stage" = ARMED ]; then
  log "[5/6] preserve existing timer intent; arm only captured fresh timers"
  setup_control arm
  stage=$(setup_control inspect)
fi

if [ "$stage" = ARMED ] || [ "$stage" = CRON_RETIRED ]; then
  log "[6/6] retire legacy cron using captured preimage and verified postimage"
  setup_control finish
else
  echo "live-setup: original setup stage cannot complete: $stage" >&2
  exit 75
fi

setup_complete=1
trap - EXIT
log "DONE — original live setup transaction completed"
log "After production freshness is verified, set GitHub repository variable VPS_LIVE_PRIMARY=true."
