---
key: PRESS-FEEDS-RESTART-AFTER-AN-AUTH-GAP-NEEDS-THE-ALPACA-CURSOR-REPRIMED
claim: >
  marketing-press-feeds.service reads /etc/macro-live.env only at process start, so a
  credential refresh reaches it only through a restart — and a BARE restart after an auth
  gap wider than one page replays history: AlpacaNewsProvider's cursored polls are
  contiguous (`sort=asc` + `start=<cursor>`, limit 50, the cursor advancing to the newest of
  the OLDEST page; engine/marketing/press_providers.py L908-923 and L940-942), so with the
  cursor frozen at 2026-08-04T04:04:42Z the daemon would have walked ~2 months of Benzinga
  history into the press desk at 50 items per tick as if it were live news. Only an EMPTY
  cursor takes the provider's cold-start path (one `sort=desc` page, nothing ingested, the
  cursor primed to the newest timestamp, `::notice title=alpaca-cold-start`; L896-907). The
  lawful resume after a long gap is therefore stop -> back up
  data/marketing/press/state.json -> delete providers.alpaca.since -> start, under the
  updater lock. Emission is double-gated (scripts/marketing_fastlane_daemon.py L511-542:
  `--dry-run` OR MARKETING_PUBLISH_ENABLED unset -> `[NO-OP]`, no outbox write), so with
  MARKETING_PUBLISH_ENABLED absent from /etc/macro-live.env the restart's blast radius is
  confined to data/marketing/press/.
falsifier: >
  `journalctl -u marketing-press-feeds.service --since "<restart>" | grep -c alpaca-page-catchup`
  returning 0 after a bare restart over a cursor older than one page while the provider's
  cursor jumps straight to the present (`python3 -c "import json;print(json.load(open('/opt/macro/data/marketing/press/state.json'))['providers']['alpaca'])"`);
  or engine/marketing/press_providers.py:940 building `sort=desc` while `since` is set;
  or a file appearing under data/marketing/outbox while
  `grep -c '^MARKETING_PUBLISH_ENABLED=' /etc/macro-live.env` prints 0
  (scripts/marketing_fastlane_daemon.py:542).
so_what: >
  (1) The post-refresh press-feeds restart is a seat-remediable act under the updater lock,
  not a Chairman/marketing-owner dispatch — the W9-3 belief "its catch-up is bounded to one
  newest-first page of <=50 items" is true ONLY of the cold start. (2) The
  `deploy-alpaca-secrets.yml -f restart_press_feeds=true` input performs a BARE
  `systemctl try-restart` (workflow L83): after any gap wider than one page it replays, so
  re-prime the cursor first or add a prime step to the workflow before that input is used
  again. (3) The seen-ledger (data/marketing/press/seen.json, 371 entries, 0 alpaca-keyed)
  does not protect against the replay — dedupe is per item id and the history items were
  never seen. (4) The twitterapi.io `press_stream` websocket 403 is a separate billed X push
  lane and is untouched by this restart.
kind: runtime
verified_at: 2026-10-11
verified_by: >
  seat fd47d431 — origin/main 58814e17322d bytes: press_providers.py L887-923 (cold-start vs
  cursored branch), L940-942 (`sort` / `start` params); marketing_fastlane_daemon.py
  L511-542, L181/L191 (state load/save); .github/workflows/deploy-alpaca-secrets.yml L82-88.
  VPS act 2026-10-11T19:56:24Z under /var/lock/macro-update.lock (flock -w 40): old MainPID
  3789179 (running since 2026-10-03 08:15:39Z, before the 18:01Z pair refresh) stopped;
  backup state.json.bak-alpaca-prime-20261011T195624Z (6,261,571 B); providers.alpaca.since
  popped (was 2026-08-04T04:04:42+00:00; last_poll/primed_at kept; tmp + os.replace,
  indent=2); new MainPID 3129081 with 2 ALPACA_API_* names in its environ; journal
  19:56:27Z `alpaca-cold-start ... primed to 2026-10-11T19:45:06+00:00 from 50 history
  item(s) — none ingested`; ticks 19:56:30Z and 19:57:46Z `[NO-OP] emitted=0`; 401 lines
  since the restart 0; MARKETING_PUBLISH_ENABLED lines in /etc/macro-live.env 0 (names and
  counts only, values never read).
scope: macro/engine/marketing/press_providers.py/scripts/marketing_fastlane_daemon.py/app/deploy/marketing-press-feeds.service/.github/workflows/deploy-alpaca-secrets.yml//opt/macro/data/marketing/press/state.json
confidence: verified
---

Found while closing the Alpaca 401 (DSC:VPS-ALPACA-CREDENTIALS-SILENTLY-REJECTED-SINCE-2026-08-04;
pair refreshed at 18:01Z under DEC:VPS-ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW):
the daemon process pre-dated the refresh, so the 401 loop ran on the old environ for two hours
after the fix landed on disk. The seat held the restart until the cursor semantics were read from
bytes, because the earlier "one page" belief would have licensed a bare restart that the code
does not bound. The backup is the reversal path (stop, restore the file, start). The alarm gap
named in the sibling discovery (its so_what 2) is unchanged: nothing in the press lane
distinguishes a two-month 401 loop from a quiet feed, and nothing warns that a restart over a
stale cursor is a replay.
