# Calendar correction: measured phase risk, not a live patch

## Question and exact scope

Does correcting the independently documented 2007-01-02 market closure merely repair an old gap, or does it change later multi-day grouping?

The native `engine/confluence_tiers._tf_bars` at macro `b4f95f98ef80b8cbb4636afbd723b5091658e1f1` computes `session_positions(date, market) // n`. The US reference epoch is 1950-01-03. There is no later reference-date subtraction that would automatically cancel an old calendar correction.

An isolated in-memory counterfactual removed ONLY 2007-01-02 from the existing native reference sessions. The exact `_tf_bars` function body was executed twice, once with the incumbent position function and once with positions from that single-date-corrected reference. No repository calendar, global running service, historical artifact, policy or live decision was changed. Inputs were the same pinned SPY `close` series already used by the pilot; no returns or trading signals were calculated.

## Actual results

The original 2006-2025 SPY session sequence had one native-reference discontinuity. Removing the phantom session eliminates that discontinuity. Comparing native bar END dates in the 2007-01-03 through 2025-12-31 event range:

| Grain | Incumbent end dates | Corrected end dates | Shared end dates |
|---|---:|---:|---:|
| 2 sessions | 2,390 | 2,390 | 0 |
| 3 sessions | 1,594 | 1,593 | 0 |

First incumbent 2D end dates: 2007-01-04, 2007-01-08, 2007-01-10, 2007-01-12.
First corrected 2D end dates: 2007-01-03, 2007-01-05, 2007-01-09, 2007-01-11.

First incumbent 3D end dates: 2007-01-03, 2007-01-08, 2007-01-11, 2007-01-17.
First corrected 3D end dates: 2007-01-04, 2007-01-09, 2007-01-12, 2007-01-18.

These counts describe bar endpoints, NOT changed indicator signals, failed candidates or lost trades. Neither the original ETF pilot nor the factorial result was recomputed on the corrected grid. The reference remains unchanged in production.

## What this resolves

The migration warning is real. A one-line historical holiday correction would phase-shift later absolute-grid multi-day bars under this owner. The correction must be versioned, compared against existing golden events and coordinated with Temporal Grain/Prophet consumers rather than hot-patched as a supposedly isolated historical repair.

Slice invariance and calendar correctness remain separate. The accepted 0/60 leading-slice result is still true for its incumbent grid. This test does not invalidate that result; it proves that a reference-calendar change is a distinct invalidator.

There is no evidence here that this old omission caused deterioration starting in September 2026. A stable existing convention can be historically imperfect without explaining a new economic change. Also, multi-day phase itself is a convention; fixing the session calendar does not prove that a different 2D/3D phase has better predictive performance.

This is only a single-closure counterfactual. It does not certify every historical holiday, early close, feed, international market, intraday clock or full US calendar since 1950. Those are the existing calendar/Temporal Grain owner's qualification scope.

## Reproducibility

Source commit `b4f95f98ef80b8cbb4636afbd723b5091658e1f1`.
Inputs: `data/yahoo/SPY.parquet`, `engine/confluence_tiers.py`, `engine/session_anchor.py`, `engine/technicals.py`, `lib/nyse_calendar.py`; all match the earlier pilot source receipts.

Core reference transformation: `fixed = reference_sessions('US')[reference_sessions('US') != Timestamp('2007-01-02')]`. The counterfactual position function normalizes dates with the exact native `_normalize`, refuses non-US/out-of-reference inputs, and uses `fixed.searchsorted(dates, side='left')`. The native `_tf_bars` AST was executed in an isolated namespace with only that function binding replaced. The original namespace and all source files remain unchanged.

Retained result:
`/Volumes/Mastermind/research/prophet-regime-indicator-program-20261002/factorial-bd7a4c63a6ef/calendar-phase-counterfactual.json`
SHA-256 `6f0658fb1ae15d1e601d66974194688254f29a93b096520605891d5b355a13ef`.
The artifact includes the five input hashes, reference epoch, before/after continuity checks, all endpoint counts/example dates and explicitly false rank/entry/size/trade/promotion/calendar-migration flags.

Primary closure evidence and the original failed run are preserved in CALENDAR_PILOT_AMENDMENT.md. Existing proof is sufficient to require a migration review, not to approve a new calendar or a new trading strategy.
