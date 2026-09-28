#!/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.mastermind.runner-connectivity-watchdog"
DEST_DIR="$HOME/.local/share/mastermind-runtime/runner-watchdog"
DEST_SCRIPT="$DEST_DIR/runner_connectivity_watchdog.py"
DEST_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

mkdir -p "$DEST_DIR" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
install -m 0755 "$HERE/runner_connectivity_watchdog.py" "$DEST_SCRIPT"
sed "s|__HOME__|$HOME|g"   "$HERE/com.mastermind.runner-connectivity-watchdog.plist.template" > "$DEST_PLIST"
plutil -lint "$DEST_PLIST" >/dev/null

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$DEST_PLIST"
launchctl kickstart "$DOMAIN/$LABEL"

echo "installed $LABEL"
echo "script: $DEST_SCRIPT"
echo "plist:  $DEST_PLIST"
