---
key: TERMINAL-INTRADAY-REFRESH-FAILURE-MASKING
claim: 'At Terminal #595 head ba7c48cf58b2a04deb5b566655e8e61721caca3b, exhausted aggregate transport failures return
  an empty envelope that can be counted as unchanged, and a failed later page returns the accumulated prefix that
  can be written as a successful refresh.'
falsifier: Read git show ba7c48cf58b2a04deb5b566655e8e61721caca3b:ingest/backfill_intraday.py and trace _get, fetch_polygon_intraday
  and main.work. A typed failure propagated through those exact paths or rejection of unfinished pagination would
  refute the corresponding source claim; a new head is new evidence, not a rewrite of this observation.
so_what: The refresh owner must separate successful empty responses from transport/pagination failures, preserve
  prior store bytes on incomplete fetches, count failure honestly and prove these paths before claiming a permanent
  freshness repair.
kind: landmine
verified_at: '2026-09-17'
verified_by: >
  Exact-head source plus executable no-network reproduction on ba7c48cf58b2a04deb5b566655e8e61721caca3b;
  source SHA256 1490b14de3e4222a9a815aaa908fcd30f77e61a259d2975ae25fc6a3e97a3c1f; Terminal #595
  review 5242058779, reproduction comment 5723524041 and tested repair-spike comment 5723554467. Five synthetic
  503 retries classified unchanged/failed=0; page-1 success plus page-2 failure published a prefix as written/failed=0.
  Disposable repair patch SHA256 b3166e533b0beb18beb8406d23e8b05444294a264b0800bf4e9d28a0b42e53d2: six
  discriminating failure tests passed and the full refresh/nightly set returned 47 passed; source effect remained NONE.
scope:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- terminal:ingest/backfill_intraday.py
- terminal:ops/terminal-data
confidence: verified
---

The existing #595 writer is preserved. The reproduction used the exact candidate file with a dummy key, injected local transport and a temporary data directory: no provider request, credential, production store, source edit, merge or deployment occurred. It proves the failure classification on the candidate's real fetch→refresh path, not a production outage. Required regressions remain exhausted timeout/429/5xx, later-page failure, pagination/incomplete termination, valid-empty and per-symbol isolation.

## Repair progression — 2026-09-19

The historical claim above remains true for `ba7c48cf...`, but the same #595 carrier now has repaired head `7b98ad64ac0de95522e7e9eb99747ea350ecf653`. Exhausted retries raise instead of becoming `{}`; invalid/later-page envelopes and unfinished pagination fail explicitly; a genuine `status=OK` empty response remains lawful; existing worker failure handling preserves old store bytes. Fresh exact-carrier verification: `tests/test_backfill_intraday.py` + `tests/test_nightly_wiring.py` = **47 passed**. The old-head CHANGES_REQUESTED review was dismissed only after this repair verification; hosted CI, fresh independent review and production/nightly freshness proof remain separate gates.
