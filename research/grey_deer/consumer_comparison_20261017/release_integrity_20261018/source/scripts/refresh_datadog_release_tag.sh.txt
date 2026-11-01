#!/usr/bin/env bash
# Keep Datadog Unified Service Tag `version` aligned with the exact deployed release.
set -euo pipefail

SHA="${1:-}"
SERVICE="${MASTERMIND_SERVICE:-mastermind.service}"
SYSTEMD_ROOT="${SYSTEMD_ROOT:-/etc/systemd/system}"
SYSTEMCTL_BIN="${SYSTEMCTL_BIN:-systemctl}"
DROPIN_DIR="${SYSTEMD_ROOT}/${SERVICE}.d"
BASE_DROPIN="${DROPIN_DIR}/80-datadog.conf"
VERSION_DROPIN="${DROPIN_DIR}/81-datadog-version.conf"

if [[ ! "$SHA" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'invalid release SHA for Datadog version tag\n' >&2
  exit 2
fi

# Datadog is optional. A host not onboarded must keep deploying normally.
[[ -f "$BASE_DROPIN" ]] || exit 0

tmp="$(mktemp "${VERSION_DROPIN}.tmp.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
printf '[Service]\nEnvironment=DD_VERSION=%s\n' "$SHA" > "$tmp"
chmod 0644 "$tmp"
mv -f "$tmp" "$VERSION_DROPIN"
trap - EXIT
"$SYSTEMCTL_BIN" daemon-reload
