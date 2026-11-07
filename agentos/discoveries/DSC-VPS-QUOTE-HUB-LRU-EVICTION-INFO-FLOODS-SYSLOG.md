---
key: VPS-QUOTE-HUB-LRU-EVICTION-INFO-FLOODS-SYSLOG
claim: >
  On the production VPS, quote-hub (node hub.js from /opt/terminal/hub) logs one INFO line
  per subscription eviction ("yahoo ext subscription LRU-evicted <SYM>" and "webull
  subscription LRU-evicted <SYM>"), about 500,000 lines and 70 MB of /var/log/syslog on a
  busy day; in the week to 2026-11-01 it wrote 2,965,049 lines (412 MB), 68% of the 609 MB
  week, and because rsyslog's logrotate uses delaycompress that week sat uncompressed on
  the root disk for a further 7 days.
kind: runtime
verified_at: 2026-11-01
verified_by: >
  Read-only on 146.190.142.17, 2026-11-01: zgrep -h 'LRU-evicted' /var/log/syslog.2.gz |
  wc -lc; the same piped through 'cut -c1-10 | sort | uniq -c' for lines per day;
  grep -c 'LRU-evicted' /var/log/syslog; systemctl show quote-hub.service -p MainPID
  -p ActiveEnterTimestamp -p NRestarts -p WorkingDirectory; cat /etc/logrotate.d/rsyslog;
  logrotate -d -f /etc/logrotate.d/rsyslog (dry run only). Source read in the Terminal repo:
  hub/lib/extfeed.js lines 619 and 975-980.
scope:
  - terminal
  - "terminal:hub/lib/extfeed.js"
  - "VPS quote-hub.service (146.190.142.17)"
  - "VPS /var/log/syslog (root disk)"
  - WS:MARKET-OS
confidence: verified
type: discovery
status: active
workstream: MARKET-OS
summary: >
  The second-largest writer to the VPS root disk after /opt/macro/.git is a log line, not
  data. ExtFeed.demand() is called for every US symbol on every /quotes request and keeps a
  capped LRU of subscriptions; each time a request pushes a symbol out, lruTouch's callback
  logs at INFO. When clients request more symbols than the cap, nearly every request evicts,
  and the line count follows demand rather than market hours: 426,644 lines on Sunday
  2026-10-25 and about 504,000 a day 10-27 to 10-30, then it quieted at 2026-10-31 22:18:43Z
  (7 lines between 2026-11-01 00:00Z and 07:33Z). The process (pid 3316887) has run since
  2026-10-24 05:12:22Z with 0 restarts, so the quiet spell reflects demand, not a fix.
  rsyslog rotates weekly with rotate 4 and delaycompress, so on a busy week about 600 MB of
  plain text stays on / for two weeks before it is gzipped to about 50 MB. During the
  2026-10-31 ENOSPC window it also added to the noise: rsyslogd logged 53,359 write failures.
evidence:
  - >
    /var/log/syslog.2.gz (the week 2026-10-25T00:00:10Z to 2026-11-01T00:00:06Z, compressed
    on 2026-11-01 from the 609,008,499-byte syslog.1): 'zgrep -h LRU-evicted | wc -lc' =
    2,965,049 lines, 412,221,668 bytes. Per day: 10-25 426,644; 10-26 328,179;
    10-27 504,140; 10-28 503,898; 10-29 503,424; 10-30 503,866; 10-31 194,898. Last line
    2026-10-31T22:18:43.629Z "[INFO] yahoo ext subscription LRU-evicted KRUS" from
    node[3316887].
  - >
    'systemctl show quote-hub.service': WorkingDirectory=/opt/terminal/hub,
    ExecStart /usr/bin/node hub.js, MainPID=3316887, NRestarts=0,
    ActiveEnterTimestamp=Sat 2026-10-24 05:12:22 UTC.
  - >
    Terminal repo hub/lib/extfeed.js: line 619 'log.info("webull subscription LRU-evicted",
    old)' inside WebullFeed.demand(); lines 975 and 980 'log.info("yahoo fallback
    subscription LRU-evicted", old)' and 'log.info("yahoo ext subscription LRU-evicted",
    old)' inside ExtFeed.demand(), whose doc comment says it "Must be called for every US sym
    on each /quotes request". Similar INFO evictions exist at extfeed.js:319 (alpaca),
    polygon.js:640 and macrofeed.js:511.
  - >
    /etc/logrotate.d/rsyslog covers syslog, mail.log, kern.log, auth.log, user.log and
    cron.log with 'rotate 4', 'weekly', 'compress', 'delaycompress'. The dry run
    'logrotate -d -f /etc/logrotate.d/rsyslog' showed a forced rotation would shift
    .4.gz to .5.gz and then delete it, dropping the oldest kept week of all six logs.
falsifier: >
  On 146.190.142.17: (a) 'zgrep -h LRU-evicted /var/log/syslog.2.gz | wc -l' (after
  2026-11-08, the next archive) well below 1,000,000 for a week of normal traffic refutes
  the volume; (b) in the Terminal repo, 'grep -n "LRU-evicted" hub/lib/extfeed.js' showing
  log.debug or a rate limit instead of log.info means the flood is fixed and this record is
  stale; (c) 'cat /etc/logrotate.d/rsyslog' without delaycompress refutes the two-week
  uncompressed residency.
so_what: >
  When the VPS root disk is tight, check syslog size before assuming everything is git: a
  busy week of quote-hub adds about 0.5 GB of plain text. Do not reclaim it with
  'logrotate -f /etc/logrotate.d/rsyslog'; that deletes the oldest kept week of syslog,
  auth.log and kern.log. Compress only the stale syslog.1 into a free .N.gz slot (gzip to a
  temp name, compare 'zcat | sha256sum' with the original, keep owner syslog:adm 0640 and
  the mtime, then remove syslog.1), which is what was done on 2026-11-01. The real fix is in
  the Terminal repo: demote the per-eviction lines in hub/lib/extfeed.js (and the sibling
  feeds) to debug or log an aggregated count per interval, then deploy quote-hub through its
  normal release.
related:
  - "DSC:VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED"
  - "WS:MARKET-OS"
---

After `/opt/macro/.git`, the next-largest writer to the production VPS root disk is
quote-hub's eviction logging. `ExtFeed.demand()` runs for every US symbol on every `/quotes`
request and keeps a capped LRU of subscriptions. Each eviction logs an INFO line, so a busy
day writes about 500,000 lines (about 70 MB) to `/var/log/syslog`. In the week to
2026-11-01 these lines were 412 MB of a 609 MB syslog.

rsyslog rotates weekly with `delaycompress`, so that week stays uncompressed on `/` for
another week. `logrotate -f` is not a safe way to reclaim it, because a forced rotation
deletes the oldest kept week of every rsyslog log. The fix belongs in the Terminal repo:
demote or aggregate the eviction lines in `hub/lib/extfeed.js`.
