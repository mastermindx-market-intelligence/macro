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
verified_by: 'Exact-head GitHub source read and REQUEST_CHANGES review 5242058779 on Terminal #595; source control-flow
  review only, proposed offline reproduction was platform-refused.'
scope:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- terminal:ingest/backfill_intraday.py
- terminal:ops/terminal-data
confidence: verified
---

The existing #595 writer is preserved. This record is about the reviewed candidate source, not evidence of a production run. No updater, network request, source repair, merge or deployment was performed by the reviewing TTI session. Review names exhausted timeout/429/5xx, partial-page, continuation-bound, valid-empty and per-symbol isolation tests.
