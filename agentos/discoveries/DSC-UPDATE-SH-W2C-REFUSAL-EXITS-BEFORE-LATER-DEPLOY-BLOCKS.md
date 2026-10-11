---
key: UPDATE-SH-W2C-REFUSAL-EXITS-BEFORE-LATER-DEPLOY-BLOCKS
claim: >
  `app/deploy/update.sh` (origin/main 102ac7ee5bb1, 2478 lines) ends the WHOLE deploy run when
  the W2C owner chain refuses: under `MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE -eq 3`, a failed
  `w2c_start_owner_chain` reaches `echo "macro-update: refusing W2C activation before owner
  replay completion" >&2; exit 1` at top level (L1528-1529; blame metabolism-immune[bot]
  69268b06502c, 2026-08-23). Every block after `# END W2C_RUNTIME_ATTESTATION` (L1549) is then
  skipped on that run: production-records units (L1551+), the option-OI canary (L1610+), W1B5
  timer finalization (L1758-1847), live-plane units (L1849+), prophet / breadth / cnprophet /
  closepass / sentinel / entry-radar / AM-edition / customer-backup (L1874-2290), press-feeds
  (L2292-2310), ticker-news (L2312-2344, the `TICKER_NEWS_RUNTIME_REGEX` restart), BioCatalyst
  (L2348+), unit reconcile (L2392+) and daemon modules (L2464+). Because `CHANGED` (L264-271)
  is the diff of THIS run's pull, a restart skipped this way is never retried — the next run
  sees no change. The EXIT trap `options_fail_closed_on_exit` (L436-447, cleared only at
  L1846) also fires on that exit, so every refusing run calls `disarm_options_timer` (L196).
  Measured on the VPS 2026-10-11: `macro-market-memory-technicals.service` fails every 3-min
  run on `store ticker count does not match the publish manifest` (by design until the 10-12
  nightly), the refusal line is the LAST line of every run in /var/log/macro-update.log (the
  log has no run delimiters — the manifest / "publication deferred" lines after it belong to
  the NEXT run's early blocks, L380-398), the log holds zero `ticker-news` lines ever, and
  PR #8848 (squash 1f45d70041e6, pulled 19:06:30Z, changing `scripts/run_qbus_news.py`, which
  matches the regex) left `macro-ticker-news.service` on the old bytes until the seat
  restarted it by hand at 19:24:36Z under the updater lock.
falsifier: >
  A /var/log/macro-update.log run that prints the refusal line AND, in the SAME run (delimit
  by the L264-271 fetch lines), any `macro-update:` line emitted by a block after L1549
  (ticker-news, press-feeds, biocatalyst, unit reconcile); or an origin/main update.sh in which
  the L1528-1529 `exit 1` has become a lane flag that lets later blocks run.
so_what: >
  While ANY W2C owner replay fails, every source-service restart, timer re-arm and unit
  reconcile that sits after the W2C block is silently skipped, and the options timer is
  disarmed every 3 minutes. A deploy that pulled new writer bytes is therefore NOT a restart:
  verify the unit's `ExecMainStartTimestamp` against the pull time, and while the refusal is
  live restart the affected unit by hand under `/var/lock/macro-update.lock` (`flock -w 40 9`,
  short critical section; update.sh itself takes it `-n` at L16-17) after sha-matching the
  deployed files to origin/main. Structural fix = the ORCH-D lane (seat fd47d431, branch
  `claude/mi-update-sh-w2c-lane-freeze-20261011`): the refusal freezes only its lane (flag +
  continue, final exit status 1 preserved so tests/test_market_memory_experience_deploy.py
  L1124-1125 still pin the refusal), lane-independent blocks run, and a new test proves the
  ticker-news restart fires on a refusing run. Never "fix" this by starting the technicals
  unit manually or by editing `w2c_*` semantics; never resolve it inside Sol's #7992.
kind: runtime
scope: [macro, app/deploy/update.sh, /usr/local/bin/macro-update]
confidence: verified
verified_at: 2026-10-11
verified_by: >
  seat fd47d431: `git show origin/main:app/deploy/update.sh | sed -n 1494,1549p` (refusal and
  `exit 1` at L1528-1529), `… | sed -n 436,447p` (EXIT trap), `… | sed -n 2312,2344p`
  (ticker-news block), `git blame -L1528,1529 origin/main -- app/deploy/update.sh`
  (69268b06502c); VPS `grep -c ticker-news /var/log/macro-update.log` = 0 and a `tail` of the
  log with the refusal as the last line of each run; `systemctl show macro-ticker-news.service
  -p MainPID,ExecMainStartTimestamp` before (3071073, 18:20Z) and after (3111697,
  19:24:41Z) the seat restart; `cmp` of /usr/local/bin/macro-update against app/deploy/update.sh.
affects:
  - WS:MARKET-MEMORY-W2C
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - WS:LIVE-ENTRY-RADAR
  - app/deploy/update.sh
  - tests/test_market_memory_experience_deploy.py
---

The refusal is correct W2C semantics and stays; what is wrong is its blast radius. The deploy
script has one exit for a lane-local condition, so one failing owner replay (expected for a
whole day after a manifest regeneration) turns every later, unrelated deploy step into a no-op
and leaves no trace that it did — the skipped restart is invisible to `CHANGED` on every later
run. The repair is a lane freeze, not a weaker W2C gate.
