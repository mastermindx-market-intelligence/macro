---
key: MM-IDENTITY-INGEST-IDEMPOTENT-OVER-CAPTURED-DATES
question: >
  The hourly identity ingest (scripts/ingest_market_memory_identity.py) replays every tracked
  symbol-directory snapshot from the earliest date and raises the moment the point-in-time
  store refuses a date it already holds with a different digest. One such date exists
  (2026-08-19: a backfill commit was captured at 12:18Z, then the nightly rewrote the dated
  snapshot at 22:50Z), so the store has accrued nothing since 2026-08-19. Does the fix belong
  in the store (a correction/supersession event) or in the ingest (idempotence over dates it
  already captured) — and which observation stays authoritative for 2026-08-19?
answer: >
  The ingest becomes idempotent over already-captured dates: a tracked date whose stored
  observation matches the tracked snapshot digest is a no-op; a tracked date whose stored
  observation DIFFERS emits one typed `upstream_rewrite_after_capture` divergence receipt
  (a line-start `::warning` print, counted in the run summary, never silent), does not raise,
  and the run continues to later dates so forward accrual resumes. The ORIGINAL observation
  (the 12:18Z capture of 2026-08-19) stays authoritative; the store's refusal is correct
  point-in-time behaviour and is not relaxed. A point-in-time correction event class in the
  store (new observed_at, original kept) is deferred OPEN as the store's future correction law,
  not built in this wave.
rationale: >
  The store refusal is the point-in-time guarantee working as designed; the defect is that a
  one-off same-day backfill+nightly collision became a permanent wedge because the ingest
  treats "already captured, now different upstream" as fatal for every later date too. Option
  (a) restores accrual with no change to what the store asserts about any date, keeps the
  divergence visible on every run (a receipt the next reader can count), and is reversible
  in one revert. A store-side correction class is a bigger contract change (new vocabulary,
  reader semantics, tests on every consumer) that must be designed by the market-memory
  program, not slipped into a recovery PR. Recent dated snapshots each carry exactly one
  commit, so the collision is not a standing producer defect and no producer change is owed.
alternatives:
  - option: Add a point-in-time correction/supersession event to market_memory_identity_store.py now
    why_not: >
      Changes the store contract for every reader; needs its own preregistered design and
      review by the market-memory program. Deferred as the follow-on, not rejected.
  - option: Relax the store refusal (accept the rewritten snapshot, overwrite the 08-19 observation)
    why_not: >
      Destroys the point-in-time property the store exists for; a rewritten upstream artifact
      must never silently replace what was observed at capture time.
  - option: Re-create the 2026-08-19 snapshot blob at its captured digest in data/
    why_not: >
      Rewrites a tracked data artifact to fit the store; the nightly's version is the
      canonical dated snapshot on main and other consumers already read it.
evidence:
  - "gh api repos/mastermindx-market-intelligence/macro/commits?path=data/symbol_directory/snapshots/2026-08-19.parquet (ORCH-OPS, 2026-10-11 12:4xZ): 6f3fd8b3ea1f 2026-08-19T12:17:01Z 'data: backfill 2026-08-19' then a6fac4b16a5c 2026-08-19T22:50:55Z 'data: daily collection 2026-08-19' — two commits on one dated snapshot; 10-07/10-08/10-09/09-15 each have exactly one"
  - "VPS journald (macro-market-memory-identity): 'identity store already has a different observation for this date' raised at engine/neuralweb/market_memory_identity_store.py:1537 via scripts/ingest_market_memory_identity.py:195/:252 on every hourly run; store last capture mmidobs_707790b2 observed 2026-08-19T12:18:38Z (snapshot sha 9737a1df…, tracked now 45c4b316…)"
  - "scripts/ingest_market_memory_identity.py:139 and :160-200 iterate every tracked key from the earliest date (read at origin/main 6ba70f04ecbc)"
  - "git grep -ciE 'correction|supersed|restat' -- engine/neuralweb/market_memory_identity_store.py scripts/ingest_market_memory_identity.py = 0 (no existing correction vocabulary)"
  - "No agentos workstream owns either file (git grep across agentos/ = 0 hits); the seat names the owner under program market-memory"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - market-memory
  - scripts/ingest_market_memory_identity.py
  - engine/neuralweb/market_memory_identity_store.py
confidence: high
reversibility: easy
decided_by: coo-fable (seat fd47d431, Chairman 2026-10-11 autonomy directive)
decided_at: 2026-10-11
review_by: 2027-01-11
---

Tests the implementing PR must carry: (T1) a captured date whose tracked digest equals the
stored digest is a no-op; (T2) a captured date whose tracked digest differs emits exactly one
`upstream_rewrite_after_capture` receipt, does not raise, and later uncaptured dates accrue in
the same run; (T3) an uncaptured date behaves exactly as before. The receipt is a line-start
`::warning` print with `flush=True`, never routed through a logger (house law). The store's
refusal path and its test stay untouched.
