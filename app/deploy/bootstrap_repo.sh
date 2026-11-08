#!/usr/bin/env bash
# Governed authenticated acquisition of the Macro repository (DEC:B1-MACRO-PRIVATE-CUTOVER).
#
# The canonical repo is private. There is no anonymous-clone or curl-raw-file
# path left anywhere in this script — every acquisition and every subsequent
# refresh authenticates as the host's own read-only deploy key. That key must
# already be installed on the box (see MACRO_DEPLOY_KEY below) before this
# script is run; it is never fetched, generated, or embedded here.
#
# Usage: bootstrap_repo.sh [TARGET_DIR]
#   TARGET_DIR defaults to ${MACRO_APP_DIR:-/opt/macro}.
set -euo pipefail

TARGET="${1:-${MACRO_APP_DIR:-/opt/macro}}"

# Configuration — every value below is env-overridable by name.
MACRO_REPO_URL="${MACRO_REPO_URL:-git@github.com:mastermindx-market-intelligence/macro.git}"
MACRO_DEPLOY_KEY="${MACRO_DEPLOY_KEY:-/root/.ssh/macro_ro_selfupdate}"
MACRO_REPO_BRANCH="${MACRO_REPO_BRANCH:-main}"

# Never prompt for credentials on a headless box — fail loudly instead.
export GIT_TERMINAL_PROMPT=0

log() { echo "[bootstrap] $*"; }

# IdentitiesOnly=yes is load-bearing: without it, ssh will silently offer an
# ssh-agent identity or another key under ~/.ssh ahead of ours, so the
# credential that actually authenticates would not be the one we provisioned.
# StrictHostKeyChecking=accept-new lets a fresh box's first connection proceed
# without an interactive prompt while still pinning the host key afterward.
MACRO_SSH_COMMAND="ssh -i ${MACRO_DEPLOY_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

case "$MACRO_REPO_URL" in
	git@*|ssh://*)
		if [ ! -f "$MACRO_DEPLOY_KEY" ]; then
			log "FATAL: MACRO_REPO_URL ($MACRO_REPO_URL) is an SSH remote but no key" \
				"was found at $MACRO_DEPLOY_KEY."
			log "Install a READ-ONLY deploy key for this repository at that path" \
				"(chmod 0600) before running bootstrap_repo.sh — see" \
				"app/deploy/setup.sh's header comment for the one-shot install line."
			log "Refusing to fall back to an anonymous HTTPS clone: the canonical" \
				"repository is private."
			exit 1
		fi
		;;
esac

if [ "$TARGET" = /opt/macro ]; then
    # Borrow an existing updater mutex only when it is the same file description.
    # Keep it through the absence check, package work, reset and owner installation.
    if ! { : >&9; } 2>/dev/null; then
        exec 9>/var/lock/macro-update.lock
    fi
    [ /proc/$$/fd/9 -ef /var/lock/macro-update.lock ] || {
        echo "source provisioning: inherited updater mutex is foreign" >&2; exit 75;
    }
    flock -n 9 || { echo "source provisioning: updater mutex is busy" >&2; exit 75; }
fi

if [ -d "$TARGET/.git" ]; then
	# Existing /opt/macro live readers are governed by the installed updater.
	# Neither a disabled fast timer nor a partial unit set permits direct reset.
	if [ "$TARGET" = /opt/macro ]; then
		for unit in macro-live-fast.service macro-live-fast.timer \
			macro-live-snapshot.service macro-live-snapshot.timer \
			macro-live-bars.service macro-live-bars.timer
		do
			if [ -e "/etc/systemd/system/$unit" ] || [ -L "/etc/systemd/system/$unit" ]; then
				log "FATAL: live-plane footprint present; use /usr/local/bin/macro-update"
				exit 1
			fi
			load_state=$(systemctl show -p LoadState --value "$unit") || exit 1
			[ "$load_state" = not-found ] || {
				log "FATAL: loaded live-plane footprint; use /usr/local/bin/macro-update"; exit 1;
			}
		done
		for footprint in /var/lib/macro-live/public /var/lib/macro-live/state/source-update.pending; do
			if [ -e "$footprint" ] || [ -L "$footprint" ]; then
				log "FATAL: live-plane state present; preserve the original updater transaction"
				exit 1
			fi
		done
	fi
	log "target $TARGET already has a checkout — converging onto the governed remote"
	git -C "$TARGET" remote set-url origin "$MACRO_REPO_URL"
	git -C "$TARGET" config core.sshCommand "$MACRO_SSH_COMMAND"
	# Preserve ancestry on subsequent updates. This does not repair any
	# existing shallow boundary; that remains a separate operation.
	log "fetching $MACRO_REPO_BRANCH (connected, no depth limit)"
	git -C "$TARGET" fetch origin "$MACRO_REPO_BRANCH"
	git -C "$TARGET" reset --hard FETCH_HEAD
else
	# A fresh checkout needs connected history for native revision checks.
	# Keep acquisition on the selected branch and the same deploy-key path.
	log "cloning $MACRO_REPO_URL ($MACRO_REPO_BRANCH, connected single-branch) -> $TARGET"
	git -c core.sshCommand="$MACRO_SSH_COMMAND" \
		clone --single-branch --branch "$MACRO_REPO_BRANCH" "$MACRO_REPO_URL" "$TARGET"
	# Persist the credential into the new checkout's own config. This matters
	# because update.sh later runs `git reset --hard`, which .git/config
	# survives — an ambient env var set only for this process would not.
	git -C "$TARGET" config core.sshCommand "$MACRO_SSH_COMMAND"
fi

test -f "$TARGET/site/index.html" || {
	log "FATAL: $TARGET/site/index.html missing after bootstrap"
	exit 1
}

log "bootstrap complete: $TARGET @ $(git -C "$TARGET" rev-parse --short HEAD)"
