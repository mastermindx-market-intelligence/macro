#!/usr/bin/env bash
# Idempotent provisioning for the mastermind-x.com static origin (DO droplet, Ubuntu).
# Serves the prebuilt site/ via Caddy behind Cloudflare. Safe to re-run.
#
# The canonical repo is PRIVATE (DEC:B1-MACRO-PRIVATE-CUTOVER). A fresh box
# needs a READ-ONLY deploy key installed at /root/.ssh/macro_ro_selfupdate
# first (provisioned out of band — never embedded in this repo), then bootstrap
# is a governed authenticated clone, one shot. The clone is --single-branch
# with NO --depth (MO-A-F04): bootstrap must land connected selected-branch
# history, because depth-one tips are severed from the installed HEAD and
# defeat the native accepts_revision ancestry gate on every later update.
#   install -m 0600 <key> /root/.ssh/macro_ro_selfupdate && git -c core.sshCommand='ssh -i /root/.ssh/macro_ro_selfupdate -o IdentitiesOnly=yes' clone --single-branch --branch main git@github.com:mastermindx-market-intelligence/macro.git /opt/macro && bash /opt/macro/app/deploy/setup.sh
# Or, after the repo is already cloned:  bash /opt/macro/app/deploy/setup.sh
set -euo pipefail

APP_DIR="${MACRO_APP_DIR:-/opt/macro}"
DOMAIN="mastermind-x.com"

log() { echo "[setup] $*"; }

# First adoption never executes bootstrap_repo.sh or resets the mutable checkout.
# The candidate is one exact local Git object; its own embedded owner performs
# the fd9-serialized, pending-refusing, atomic install and exact readback.
if [ "$#" -ne 0 ]; then
	if [ "$#" -ne 3 ] || [ "$1" != --install-source-owner ] ||
	   [ "$2" != --source-revision ] || [[ ! "$3" =~ ^[0-9a-f]{40}$ ]]; then
		echo "setup: expected --install-source-owner --source-revision <qualified-40-SHA>" >&2
		exit 2
	fi
	[ "$APP_DIR" = /opt/macro ] || { echo "setup: installed source owner is bound to /opt/macro" >&2; exit 2; }
	candidate=$(mktemp /usr/local/bin/.macro-source-owner.XXXXXX)
	if ! git -C "$APP_DIR" show "$3:app/deploy/update.sh" >"$candidate" ||
	   ! bash -n "$candidate"; then
		rm -f "$candidate"
		echo "setup: exact source-owner candidate is unavailable or invalid" >&2
		exit 1
	fi
	chmod 0755 "$candidate"
	if bash "$candidate" --install-source-owner "$3"; then
		rm -f "$candidate"
		log "source owner installed and read back; run /usr/local/bin/macro-update as a separate invocation"
		exit 0
	else
		rc=$?
		rm -f "$candidate"
		exit "$rc"
	fi
fi

# Borrow an existing updater mutex only when it is the same file description.
# Keep it through the absence check, package work, reset and owner installation.
if ! { : >&9; } 2>/dev/null; then
    exec 9>/var/lock/macro-update.lock
fi
[ /proc/$$/fd/9 -ef /var/lock/macro-update.lock ] || {
    echo "source provisioning: inherited updater mutex is foreign" >&2; exit 75;
}
flock -n 9 || { echo "source provisioning: updater mutex is busy" >&2; exit 75; }

# Full provisioning must not bypass the enrolled/partial live plane by reaching
# bootstrap's direct reset. Routine refresh belongs to the installed updater.
# Any ambiguous manager read refuses before package or source mutation.
for unit in macro-live-fast.service macro-live-fast.timer \
	macro-live-snapshot.service macro-live-snapshot.timer \
	macro-live-bars.service macro-live-bars.timer
do
	if [ -e "/etc/systemd/system/$unit" ] || [ -L "/etc/systemd/system/$unit" ]; then
		echo "setup: live-plane footprint present; refresh through /usr/local/bin/macro-update" >&2
		exit 1
	fi
	load_state=$(systemctl show -p LoadState --value "$unit") || {
		echo "setup: cannot establish live-plane absence" >&2; exit 1;
	}
	[ "$load_state" = not-found ] || {
		echo "setup: loaded live-plane footprint; refresh through /usr/local/bin/macro-update" >&2; exit 1;
	}
done
for footprint in /var/lib/macro-live/public /var/lib/macro-live/state/source-update.pending; do
	if [ -e "$footprint" ] || [ -L "$footprint" ]; then
		echo "setup: existing or partial live-plane state; preserve it and use the installed owner" >&2
		exit 1
	fi
done

log "[1/6] base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl git ufw gnupg rsync

log "[2/6] Caddy (official repo)"
if ! command -v caddy >/dev/null 2>&1; then
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
		| gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
		> /etc/apt/sources.list.d/caddy-stable.list
	apt-get update -y
	apt-get install -y caddy
fi

log "[3/6] clone/refresh repo (connected selected-branch history, governed authenticated remote)"
mkdir -p "$(dirname "$APP_DIR")"
BOOTSTRAP_SCRIPT="$(dirname "${BASH_SOURCE[0]}")/bootstrap_repo.sh"
if [ ! -f "$BOOTSTRAP_SCRIPT" ]; then
	# Piped/stdin invocation: BASH_SOURCE isn't a real file, so fall back to the
	# copy inside an existing checkout. On a truly empty box neither path exists
	# — that case is the governed clone in the header comment, which must run
	# first; failing here is correct, not a regression.
	BOOTSTRAP_SCRIPT="$APP_DIR/app/deploy/bootstrap_repo.sh"
fi
bash "$BOOTSTRAP_SCRIPT" "$APP_DIR"

# Publish the served tree ATOMICALLY into a dir OUTSIDE the git work-tree, so the
# `git reset --hard` in update.sh can never expose a 0-byte file to Caddy/the CDN
# (2026-07-03 white-page incident). Caddy's root is $APP_DIR/site.served (see
# Caddyfile); it MUST exist + be populated before Caddy starts below, or the site
# 404s until the first cron pull. rsync is atomic per-file (temp-write + rename).
log "[3b/6] publish served tree -> $APP_DIR/site.served (atomic)"
mkdir -p "$APP_DIR/site.served"
rsync -a --delete "$APP_DIR/site/" "$APP_DIR/site.served/"

log "[4/6] install + validate Caddyfile"
install -m 0644 "$APP_DIR/app/deploy/Caddyfile" /etc/caddy/Caddyfile
caddy fmt --overwrite /etc/caddy/Caddyfile || true
caddy validate --config /etc/caddy/Caddyfile

log "[5/6] firewall: SSH + HTTP/HTTPS"
ufw allow 22/tcp >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

log "[6/6] enable Caddy + fast pull-if-changed cron"
systemctl enable caddy >/dev/null 2>&1 || true
systemctl restart caddy
bash "$APP_DIR/app/deploy/update.sh" --install-source-owner "$(git -C "$APP_DIR" rev-parse HEAD)"
# Track main within minutes: pull-if-changed every 3 min (cheap no-op when unchanged),
# so render.yml's fast template renders AND the nightly data build reach the domain
# quickly — instead of a once-a-night pull. `|| true`: on a box with no crontab yet,
# `crontab -l`+`grep -v` both "fail" on empty input and would abort under
# `set -e -o pipefail` before the echo — keep them harmless.
{ crontab -l 2>/dev/null | grep -v 'macro-update' || true ; \
  echo "*/3 * * * * /usr/local/bin/macro-update >> /var/log/macro-update.log 2>&1" ; } | crontab -

# Rotate the cron + Caddy logs so they can never fill the droplet disk.
install -m 0644 "$APP_DIR/app/deploy/logrotate-macro-vps" /etc/logrotate.d/macro-vps 2>/dev/null || true
# Same for the persistent journal (2026-10-19 root-disk incident). The Git store
# maintenance timer is self-armed by macro-update on the macro-api box.
install -D -m 0644 "$APP_DIR/app/deploy/journald-macro-vps.conf" /etc/systemd/journald.conf.d/10-macro-vps-cap.conf \
	&& systemctl restart systemd-journald || log "journald cap not applied (non-fatal)"

# Lock the web origin to Cloudflare IPs only (close the direct-to-origin bypass). Fail-open:
# a CF-fetch failure leaves provisioning intact rather than blocking the deploy.
bash "$APP_DIR/app/deploy/firewall-cloudflare.sh" || log "firewall step skipped (non-fatal)"

log "DONE — Caddy serving https://$DOMAIN from $APP_DIR/site.served (atomic mirror of $APP_DIR/site)"
log "HEAD: $(git -C "$APP_DIR" rev-parse --short HEAD)"
systemctl --no-pager status caddy | head -4 || true

# ── Site Access Gate runtime dir ─────────────────────────────────────────────
# The gate store lives at SITE_GATE_STATE (default /var/lib/macro-api/site_gate.json).
# /var/lib/macro-api is already used for the per-user quota ledger; ensure it exists
# with the correct permissions.  The store file itself is created on the first save
# via the admin panel (/api/site_gate/save); an absent file is treated as
# {enabled:false} → allow everyone (fail-open).
mkdir -p /var/lib/macro-api
chmod 700 /var/lib/macro-api
log "Runtime dir /var/lib/macro-api is present (SITE_GATE_STATE default lives here)."

# Optional: download the MaxMind GeoLite2-Country database for origin-side
# country detection (CDN header detection works without it).  Skipped when
# MAXMIND_LICENSE_KEY is absent.
if [ -n "${MAXMIND_LICENSE_KEY:-}" ]; then
    bash "$APP_DIR/app/deploy/geoip-setup.sh" || log "geoip-setup skipped (non-fatal)"
else
    log "MAXMIND_LICENSE_KEY not set — GeoIP country detection unavailable (CDN header still works)."
    log "See app/deploy/geoip-setup.sh for setup instructions."
fi
