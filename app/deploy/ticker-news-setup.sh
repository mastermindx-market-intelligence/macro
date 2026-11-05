#!/usr/bin/env bash
# Manual operator boundary for the low-latency ticker-news writer.
#
# This script reuses the existing VPS/systemd owner. It creates no scheduler,
# secret store, or deployment plane. Default --check is network-dark. --install
# installs the reviewed unit disabled. Only an explicit --arm enables/starts it.
set -euo pipefail

ACTION="${1:---check}"
APP_DIR=/opt/macro
PY=/opt/macro-api/.venv/bin/python
UNIT_SOURCE="$APP_DIR/app/deploy/macro-ticker-news.service"
UNIT_INSTALLED=/etc/systemd/system/macro-ticker-news.service
ENV_FILE=/etc/macro-ticker-news.env
RIGHTS_FILE=/etc/macro-ticker-news-rights.json
STATE_DIR=/var/lib/macro-ticker-news
UNIVERSE="$STATE_DIR/news_universe.json"
HEALTH="$STATE_DIR/health.json"
DATABASE="$STATE_DIR/qbus.sqlite3"

log() { printf "[ticker-news-setup] %s\n" "$*"; }
fail() { log "ERROR: $*" >&2; exit 2; }

[ "$(id -u)" -eq 0 ] || fail "must run as root on the Macro API VPS"
[ -d "$APP_DIR" ] || fail "canonical checkout missing: $APP_DIR"
[ -x "$PY" ] || fail "macro API runtime missing: $PY"

# Serialize with /usr/local/bin/macro-update and api-setup.sh. The same lock
# already owns mutations of /opt/macro, /opt/macro-api and systemd fragments.
exec 9>/var/lock/macro-update.lock
flock 9

require_private_file() {
  local path=$1 owner mode
  [ -f "$path" ] && [ ! -L "$path" ] || fail "required regular file missing: $path"
  owner=$(stat -c "%u" "$path")
  [ "$owner" = 0 ] || fail "file must be root-owned: $path"
  mode=$(stat -c "%a" "$path")
  case "$mode" in
    600|400) ;;
    *) fail "file must be mode 600 or 400: $path" ;;
  esac
}

load_provider_token() {
  local line count
  require_private_file "$ENV_FILE"
  count=$(grep -c -E "^BENZINGA_API_KEY=" "$ENV_FILE" || true)
  [ "$count" = 1 ] || fail "expected exactly one BENZINGA_API_KEY line in $ENV_FILE"
  line=$(grep -E "^BENZINGA_API_KEY=" "$ENV_FILE")
  [ -n "$line" ] || fail "BENZINGA_API_KEY missing from $ENV_FILE"
  BENZINGA_API_KEY=${line#BENZINGA_API_KEY=}
  [ -n "$BENZINGA_API_KEY" ] || fail "BENZINGA_API_KEY is empty"
  case "$BENZINGA_API_KEY" in *$'\n'*|*$'\r'*) fail "BENZINGA_API_KEY contains newline" ;; esac
  export BENZINGA_API_KEY
}

load_alpaca_credentials() {
  local line count
  require_private_file "$ENV_FILE"
  count=$(grep -c -E "^ALPACA_API_KEY_ID=" "$ENV_FILE" || true)
  [ "$count" = 1 ] || fail "expected exactly one ALPACA_API_KEY_ID line in $ENV_FILE"
  line=$(grep -E "^ALPACA_API_KEY_ID=" "$ENV_FILE")
  ALPACA_API_KEY_ID=${line#ALPACA_API_KEY_ID=}
  [ -n "$ALPACA_API_KEY_ID" ] || fail "ALPACA_API_KEY_ID is empty"
  case "$ALPACA_API_KEY_ID" in *$'\n'*|*$'\r'*) fail "ALPACA_API_KEY_ID contains newline" ;; esac
  count=$(grep -c -E "^ALPACA_API_SECRET_KEY=" "$ENV_FILE" || true)
  [ "$count" = 1 ] || fail "expected exactly one ALPACA_API_SECRET_KEY line in $ENV_FILE"
  line=$(grep -E "^ALPACA_API_SECRET_KEY=" "$ENV_FILE")
  ALPACA_API_SECRET_KEY=${line#ALPACA_API_SECRET_KEY=}
  [ -n "$ALPACA_API_SECRET_KEY" ] || fail "ALPACA_API_SECRET_KEY is empty"
  case "$ALPACA_API_SECRET_KEY" in *$'\n'*|*$'\r'*) fail "ALPACA_API_SECRET_KEY contains newline" ;; esac
  export ALPACA_API_KEY_ID ALPACA_API_SECRET_KEY
}

# Provider dispatcher: benzinga (default) or alpaca, from the same root env
# file. Values are exported, never printed.
load_provider_credentials() {
  local provider count
  require_private_file "$ENV_FILE"
  count=$(grep -c -E "^QBUS_NEWS_PROVIDER=" "$ENV_FILE" || true)
  if [ "$count" = 0 ]; then
    provider=benzinga
  elif [ "$count" = 1 ]; then
    provider=$(grep -E "^QBUS_NEWS_PROVIDER=" "$ENV_FILE")
    provider=${provider#QBUS_NEWS_PROVIDER=}
  else
    fail "expected at most one QBUS_NEWS_PROVIDER line in $ENV_FILE"
  fi
  case "$provider" in
    benzinga) ;;
    alpaca) ;;
    *) fail "QBUS_NEWS_PROVIDER must be benzinga or alpaca" ;;
  esac
  export QBUS_NEWS_PROVIDER="$provider"
  if [ "$provider" = alpaca ]; then
    load_alpaca_credentials
  else
    load_provider_token
  fi
}

check_activation() {
  require_private_file "$RIGHTS_FILE"
  [ -f "$UNIT_SOURCE" ] && [ ! -L "$UNIT_SOURCE" ] || fail "reviewed unit missing"
  install -d -m 0700 "$STATE_DIR"
  load_provider_credentials

  # Verify the exact production interpreter has the sync WebSocket API before
  # touching systemd. This imports only; it opens no provider connection.
  "$PY" -c "from websockets.sync.client import connect; assert connect"

  # Derived current membership artifact only. No provider call and no DB/health
  # write occurs in --check-activation.
  cd "$APP_DIR"
  "$PY" scripts/build_qbus_news_universe.py \
    --output "$UNIVERSE" --write >/dev/null
  "$PY" scripts/run_qbus_news.py --check-activation \
    --database "$DATABASE" \
    --universe-snapshot "$UNIVERSE" \
    --rights-receipt "$RIGHTS_FILE" \
    --health-path "$HEALTH"
  log "activation prerequisites qualified; provider network remains unopened"
}

install_unit() {
  check_activation
  if systemctl is-active --quiet macro-ticker-news.service; then
    fail "writer is active; disarm before installing a reviewed unit"
  fi
  [ ! -L "$UNIT_INSTALLED" ] || fail "refusing symlinked installed unit"
  systemd-analyze verify "$UNIT_SOURCE"
  install -m 0644 "$UNIT_SOURCE" "$UNIT_INSTALLED"
  systemctl daemon-reload
  [ "$(systemctl show -p NeedDaemonReload --value macro-ticker-news.service)" = no ] || \
    fail "systemd manager state remains stale"
  log "unit installed disabled/inactive unless it was already operator-armed"
}

arm_unit() {
  install_unit
  systemctl enable --now macro-ticker-news.service
  systemctl is-active --quiet macro-ticker-news.service || \
    fail "macro-ticker-news did not become active"
  log "macro-ticker-news is armed; verify health/API before acceptance"
}

disarm_unit() {
  if [ ! -e "$UNIT_INSTALLED" ] && [ ! -L "$UNIT_INSTALLED" ]; then
    log "unit is not installed; already disarmed"
    return 0
  fi
  systemctl disable --now macro-ticker-news.service >/dev/null 2>&1 || true
  if systemctl is-active --quiet macro-ticker-news.service; then
    fail "macro-ticker-news remains active after disable --now"
  fi
  log "macro-ticker-news is disabled and stopped"
}

status_unit() {
  printf "installed=%s\n" "$([ -f "$UNIT_INSTALLED" ] && echo yes || echo no)"
  printf "enabled=%s\n" "$(systemctl is-enabled macro-ticker-news.service 2>/dev/null || echo not-installed)"
  printf "active=%s\n" "$(systemctl is-active macro-ticker-news.service 2>/dev/null || echo inactive)"
}

case "$ACTION" in
  --check) check_activation ;;
  --install) install_unit ;;
  --arm) arm_unit ;;
  --disarm) disarm_unit ;;
  --status) status_unit ;;
  *)
    echo "usage: $0 [--check|--install|--arm|--disarm|--status]" >&2
    exit 2
    ;;
esac
