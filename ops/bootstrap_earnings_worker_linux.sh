#!/bin/bash
# Install/refresh the native-Ubuntu earnings producer using the existing
# scorer, provider waterfall, R2 transport, and inference slice.
# Secrets stay in an operator-provisioned environment file.
set -euo pipefail

OPS_ROOT="${EARNINGS_OPS_ROOT:-/opt/mastermind-earnings/macro}"
VENV_ROOT="${EARNINGS_VENV_ROOT:-/opt/mastermind-earnings/venv}"
RUNTIME_ROOT="${EARNINGS_RUNTIME_ROOT:-/var/lib/mastermind-earnings}"
ENV_FILE="${EARNINGS_ENV_FILE:-/etc/mastermind/earnings-worker.env}"
REMOTE_URL="${EARNINGS_REMOTE_URL:-https://github.com/mastermindx-market-intelligence/macro.git}"
SERVICE_NAME="mastermind-earnings-worker.service"
TIMER_NAME="mastermind-earnings-worker.timer"
CHECK_ONLY=0
RUN_NOW=0

usage() {
  echo "Usage: bootstrap_earnings_worker_linux.sh [--check] [--run-now]"
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --check) CHECK_ONLY=1 ;;
    --run-now) RUN_NOW=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
if [ "$CHECK_ONLY" -eq 1 ] && [ "$RUN_NOW" -eq 1 ]; then
  echo "ERROR: --check and --run-now are mutually exclusive" >&2
  exit 2
fi
for path in "$OPS_ROOT" "$VENV_ROOT" "$RUNTIME_ROOT" "$ENV_FILE"; do
  case "$path" in /*) ;; *) echo "ERROR: paths must be absolute: $path" >&2; exit 1 ;; esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SERVICE="$SCRIPT_DIR/systemd/$SERVICE_NAME"
SOURCE_TIMER="$SCRIPT_DIR/systemd/$TIMER_NAME"
REQ_REL="ops/earnings_worker_requirements.txt"
RUN_REL="ops/launchd/run_earnings_worker.sh"
ENV_WRAPPER_REL="ops/launchd/run_with_env.sh"

validate_clone() {
  [ -d "$OPS_ROOT/.git" ] || { echo "ERROR: missing clone at $OPS_ROOT" >&2; return 1; }
  [ "$(git -C "$OPS_ROOT" rev-parse --show-toplevel)" = "$OPS_ROOT" ] || return 1
  [ "$(git -C "$OPS_ROOT" symbolic-ref --quiet --short HEAD)" = main ] || return 1
  [ "$(git -C "$OPS_ROOT" remote get-url origin)" = "$REMOTE_URL" ] || return 1
  [ -z "$(git -C "$OPS_ROOT" status --porcelain --untracked-files=all)" ] || return 1
}
verify_env_names() {
  [ -f "$ENV_FILE" ] || { echo "ERROR: missing env file: $ENV_FILE" >&2; return 1; }
  local names name
  names="$(awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print $1}' "$ENV_FILE")"
  for name in R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET EARNINGS_LLM_BASE_URL EARNINGS_LLM_MODEL; do
    printf '%s\n' "$names" | grep -Fxq "$name" || { echo "ERROR: missing env name: $name" >&2; return 1; }
  done
  echo "OK: required earnings environment variable names are present"
}

if [ "$CHECK_ONLY" -eq 0 ]; then
  if [ ! -e "$OPS_ROOT" ]; then
    sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 0755 "$(dirname "$OPS_ROOT")"
    git clone --filter=blob:none --sparse --branch main --single-branch "$REMOTE_URL" "$OPS_ROOT"
    git -C "$OPS_ROOT" sparse-checkout set engine lib scripts tools/earnings_worker config ops
  fi
  validate_clone
  git -C "$OPS_ROOT" fetch origin main --quiet
  git -C "$OPS_ROOT" merge --ff-only --quiet origin/main
  test "$(git -C "$OPS_ROOT" rev-parse HEAD)" = "$(git -C "$OPS_ROOT" rev-parse origin/main)"
else
  validate_clone
fi
for rel in "$REQ_REL" "$RUN_REL" "$ENV_WRAPPER_REL"; do
  [ -f "$OPS_ROOT/$rel" ] || { echo "ERROR: missing source file $rel" >&2; exit 1; }
done
[ -f "$SOURCE_SERVICE" ] && [ -f "$SOURCE_TIMER" ] || { echo "ERROR: missing systemd source units" >&2; exit 1; }
verify_env_names
systemctl is-active --quiet mastermind-inference-guard.service || { echo "ERROR: inference guard inactive" >&2; exit 1; }
if [ "$CHECK_ONLY" -eq 0 ]; then
  [ -x "$VENV_ROOT/bin/python" ] || python3 -m venv "$VENV_ROOT"
  REQ_SHA="$(sha256sum "$OPS_ROOT/$REQ_REL" | awk '{print $1}')"
  STAMP="$VENV_ROOT/.earnings-requirements.sha256"
  if [ "$(cat "$STAMP" 2>/dev/null || true)" != "$REQ_SHA" ]; then
    "$VENV_ROOT/bin/python" -m pip install --disable-pip-version-check -r "$OPS_ROOT/$REQ_REL"
    printf '%s\n' "$REQ_SHA" > "$STAMP"
  fi
  sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 0750 "$RUNTIME_ROOT"
  sudo install -o root -g root -m 0644 "$SOURCE_SERVICE" "/etc/systemd/system/$SERVICE_NAME"
  sudo install -o root -g root -m 0644 "$SOURCE_TIMER" "/etc/systemd/system/$TIMER_NAME"
  sudo systemctl daemon-reload
  sudo systemctl enable --now "$TIMER_NAME"
fi
"$VENV_ROOT/bin/python" -c 'import anthropic,boto3,pandas,pyarrow,requests,yaml'
cmp -s "$SOURCE_SERVICE" "/etc/systemd/system/$SERVICE_NAME"
cmp -s "$SOURCE_TIMER" "/etc/systemd/system/$TIMER_NAME"
systemctl is-enabled --quiet "$TIMER_NAME"
systemctl is-active --quiet "$TIMER_NAME"
env EARNINGS_OPS_ROOT="$OPS_ROOT" EARNINGS_PYTHON="$VENV_ROOT/bin/python" EARNINGS_RUNTIME_ROOT="$RUNTIME_ROOT" \
  EARNINGS_LOCK_DIR=/run/lock/mastermind-earnings-worker.lock \
  "$OPS_ROOT/$ENV_WRAPPER_REL" "$ENV_FILE" "$OPS_ROOT/$RUN_REL" --check-env
if [ "$RUN_NOW" -eq 1 ]; then
  sudo systemctl start "$SERVICE_NAME"
  test "$(systemctl show "$SERVICE_NAME" -p Result --value)" = success
fi
echo "OK: native Ubuntu earnings worker is installed and reproducible"
