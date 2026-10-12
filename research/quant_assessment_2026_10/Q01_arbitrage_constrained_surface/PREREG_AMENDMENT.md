# Q01 pre-registration amendment A1

AMENDS_PREREG_SHA256=9e152194440979b96b9ee80658c844b699ce065bd9f6c25e2a610c03c568f60b

Written after the freeze of `PREREG.md` (FREEZE.log, Fri Oct 9 10:03:55 UTC 2026) and before
`evaluate.py` was run for the first time. No evaluation outcome had been read when this was written.
Its own sha256 is appended to `FREEZE.log` with a `date -u` timestamp; `evaluate.py` refuses to run
if this file's hash differs from that record or if `AMENDS_PREREG_SHA256` differs from the frozen
PREREG hash.

## A1 — exhaustive schema sweep added to S2 (eligibility census)

Reason: the S2 candidate list in PREREG §5 was assembled by the author from `DATA_MAP.md` and a
schema census. An INSUFFICIENT_DATA verdict should rest on a demonstrated absence across the whole
retained data root, not on an author-curated list.

Change: S2 additionally walks every file under the data root
(`/Users/chriswong/Documents/Cluade/macro-main/data`, vintage `cdab6268`, read only):

* each `*.parquet`: read the schema footer only (column names);
* each `*.csv`, `*.json`, `*.jsonl` of at most 20 MiB: read the first 64 KiB only and search for
  field tokens.

A file is a quote-chain candidate when it shows a bid-like field AND an ask/offer-like field AND a
strike-like field AND an expiry-like field. Every candidate is hashed (sha256) and checked against the
§4 eligibility contract (European index roots, per-contract quote clock, condition, settlement/style,
forward/discount). Non-candidates are reported only as counts plus one sha256 digest of the sorted
(relative path, byte size) listing; nothing beyond their footer/header is read or used.

Unchanged: estimand, unit, clocks, cohort contract, data gate, hypotheses, competitors, effect bars,
trial family, holdout design, chronological split, uncertainty method, falsifier and stop rule.
