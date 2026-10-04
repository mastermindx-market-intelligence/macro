#!/bin/bash
# ============================================================================
# The "feeding tube" watcher — v2 (2026-07-29).
#
# The extractor's `trickle` daemon (com.mastermindx.research-trickle) now owns
# ALL browser work: discovery (15-min narrow + daily wide self-heal pass),
# quota-paced downloads (rolling 24h cap, priority-first), and vault publishing.
# This script therefore no longer opens MarketDesk at all — two processes
# sharing one Chromium profile would deadlock.
#
# Its one remaining job: watch the DB for freshly vaulted papers and trigger
# the dashboard ingest workflow the moment something new lands (the hourly
# research-ingest cron remains the backstop). Run every ~15 min by launchd
# (com.mastermindx.research-feed).
# ============================================================================
DEST="$HOME/mastermind-research"
APP="$DEST/marketdesk_paper_extractor"
LOG="$DEST/feed.log"
WATERMARK="$DEST/.feed_vault_watermark"
REPO="mastermindx-market-intelligence/macro"

ts() { date -u +%FT%TZ; }

# Serialize the whole probe/dispatch cycle. mkdir is atomic + portable.
LOCK="$DEST/.feed.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "$(ts) feed: previous run still going — skip" >>"$LOG"; exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

LAST="$(cat "$WATERMARK" 2>/dev/null)"
[ -n "$LAST" ] || LAST="1970-01-01T00:00:00+00:00"

# Resolve the canonical DB and query it through one read-only, hard-deadlined
# probe. This prevents an external-volume open from wedging the launch agent and
# avoids silently reading the stale pre-migration internal database.
if ! PROBE="$(cd "$APP" 2>>"$LOG" &&   ./.venv/bin/python -m marketdesk_extractor.feed_probe   "$LAST" --timeout 10 2>>"$LOG")"; then
  echo "$(ts) feed: vault-state probe failed — retrying next tick" >>"$LOG"
  exit 0
fi
IFS='|' read -r DB NEWEST COUNT <<<"$PROBE"
case "$COUNT" in
  ''|*[!0-9]*)
    echo "$(ts) feed: malformed vault-state probe output" >>"$LOG"
    exit 0
    ;;
esac

if [ -n "$NEWEST" ] && [ "${COUNT:-0}" -gt 0 ] 2>/dev/null; then
  echo "$(ts) feed: $COUNT new vault publish(es) since $LAST → triggering ingest" >>"$LOG"
  if command -v gh >/dev/null 2>&1 && gh workflow run research-ingest.yml -R "$REPO" >>"$LOG" 2>&1; then
    echo "$NEWEST" > "$WATERMARK"
    echo "$(ts) feed: ingest triggered (watermark → $NEWEST)" >>"$LOG"
  else
    # leave the watermark so the next tick retries; hourly cron is the backstop
    echo "$(ts) feed: gh trigger unavailable — hourly cron will ingest within the hour" >>"$LOG"
  fi
else
  echo "$(ts) feed: nothing new" >>"$LOG"
fi

# Health note: warn (once per tick) if the trickle daemon isn't running.
if ! pgrep -f "marketdesk trickle" >/dev/null 2>&1; then
  echo "$(ts) feed: WARNING trickle daemon not running (launchctl list | grep research-trickle)" >>"$LOG"
fi
