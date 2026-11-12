---
key: PRESSURE-WATCH-EVENT-DATE-IS-NOT-EVALUATION
claim: Pressure Watch's legacy artifact asof identifies the newest event, not the last successfully evaluated price session.
falsifier: Run the quiet-session pipeline and artifact regression in tests/test_price_pressure.py and compare event asof with evaluated_through and the actual panel end.
so_what: Preserve the event-date ledger-restore fence; use completed evaluation and source availability to judge freshness, and refresh the existing page section after the producer.
kind: landmine
verified_at: 2026-09-16
verified_by: "PR #7197; test_quiet_session_evaluation_does_not_redate_events_or_replay_old_day_facts; engine/price_pressure/artifact.py; engine/price_pressure/ledger.py::restore_status"
scope: [macro, price-pressure, engine/price_pressure/, scripts/build_ticker_pages.py]
confidence: verified
---

# Pressure Watch dates have different jobs

The September 2026 incident combined a never-started nightly producer, a stock page
rendered before that producer, and a consumer that inverted a nonempty banner string.
The original event asof is also the restore fence for the R2-canonical ledger.
Changing it to today's date would weaken that fence and misdescribe quiet sessions.

The candidate in Macro PR #7197 adds evaluated_through, preserves event identity,
and distinguishes source delay from downstream processing delay. It is not evidence
of production acceptance. The original motivating record ended September 11 while
actual AAPL and ACVA source bars had reached September 14.

Massive documents next-day stock flat-file availability at about 11:00 ET:
https://massive.com/docs/flat-files/stocks/day-aggregates
The publication deadline is an availability estimate, not proof that a file arrived.
The collector's ingestion-summary date and an R2 Last-Modified timestamp are not
market-observation dates. Acceptance requires content dates through the served page.
