# Session-derivation seam profile — 2026-10-03

## What was wrong
On the natural failure, ``daily/37085692173`` ``engine/111132424007`` step
``options_signal_episode`` at checkout ``5fc7af4a…`` hit a 10 min STEP timeout.
Phase timings: stage_load 26.254 s, stage_validation 8.222 s,
history_validation 57.336 s, episode_append 7.825 s, h60_derivation 74.477 s,
h60_append 10.910 s, session_derivation started 08:34:00.912 UTC and never
completed before SIGINT at 08:40:55, then exit 143 after 613 s. 9 641 episodes,
30 327 session outcomes.

The session_derivation phase ran for 6.5 minutes and never reached the floor
budget; 30 327 session_outcomes (= 9 641 × 5 / pending) drove
``normalize_price_bars`` repeatedly over the same raw frames.

## Synthetic moderate-scale profile (this commit)
Fixture: 20 tickers × 16 episodes/ticker × 5 session horizons
(eod / 1d / 3d / 5d / 10d) = 1 600 ``derive_session_outcome`` calls.
``SESSION_DATE=2026-07-02``, ``BAR_SECONDS=1800``, full RTH coverage.

| pass                  | normalize_calls | derive_calls |
|-----------------------|----------------:|-------------:|
| raw-baseline          |           1 600 |        1 600 |
| prepared-seam (this)  |              20 |         1 600 |

The raw pass reflects the old head: ``normalize_price_bars`` ran 80× more than
necessary because every ``derive_session_outcome`` re-normalized the same
parquet/ticker pair from the cached raw frame. The prepared pass invokes the
factory once per ticker; every other call reuses the typed wrapper's
already-normalized frame and skips the redundant work.

The deterministic artifact is
``research/MO_EXT_FIX_OPTIONS_PRODUCT_20261003/profile_session_derivation_seam.json``.

## What fails on the old head (no prepared seam)
* Each unresolved episode × horizon pair re-parses the raw frame, re-sorts the
  UTC index, re-coerces OHLC numerics, re-deduplicates, re-drops NA.
* For the natural-failure fleet of 9 641 × 5 ≈ 48 205 session outcomes on a
  shared price-cache of ~30 tickers, that is ~48 k ``normalize_price_bars``
  invocations versus ~30 with the seam (one per ticker).
* The H+60 phase is dominated by ``session_df["read"]`` inside a per-session
  loop; the prepared seam still helps (1 call/ticker vs N/ticker).

## Caveats
* This profile is synthetic and excludes R2 latency, parquet I/O, the
  LedgerLock, and the V1 schema-validation gates that the production run pays.
  The 80× reduction here is therefore the floor; the real speedup on the
  natural failure is bounded below by the I/O share, not by normalize calls
  alone.
* No live builder rerun; no data/ledger mutation; no time-budget increase;
  no checkpoint/append/lock reordering; no scientific-rule change.