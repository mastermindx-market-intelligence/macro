# Rate-shock driver transition v1 — pre-outcome contract

Parent: WS:RATES-INFLATION-COMMAND / PR 7909 / rates-direction-20260924-sol-001.

Procedure pin: Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1.

## Question

After the 10-year Treasury has already made an unusually large five-session move,
does the *composition of that move* improve the probability estimate of what happens
next: continuation, reversal, or neither?

This is deliberately different from RD1's unconditional endpoint forecast and from
the failed two-hour oscillator studies. It tests the Chairman's operational problem:
after a rate impulse has become visible, decide whether it is more likely to extend
or reset. Oscillator phase is NOT part of this first driver study.

## Information boundary

Historical target/proxy:
- DGS10 market-observed 10-year nominal Treasury yield.
- DGS2, DFII10, T10YIE, DCOILWTICO and BAMLH0A0HYM2 are historical market
  observations. They are latest local FRED copies used as historical market proxies;
  corrections are not versioned.
- Kim-Wright THREEFYTP10 is consumed through engine.pit release-basis ALFRED
  availability, not reference-stamped hindsight. Its on-disk vintage coverage begins
  in 2016.
- Treasury auction demand is computed only from auction results on/before the
  decision date and each auction is standardized against PRIOR same-tenor auctions.

Excluded from this v1:
- zq_path/SOFR futures. Current history starts only in March 2026 and rolling horizon
  changes can be contract-roll rather than genuine policy repricing; RD2 must qualify
  constituent repricing first.
- release_forecast macro-surprise ledger. Its genuine forward history begins in
  mid-2026, too short for this retrospective transition study. It belongs in
  prospective shadow.
- current September 23/24 motivating outcome. Evaluation ends 2025-12-31.

No source here is promoted to live trade authority.

## Origin definition

Daily business dates 2017-01-03 through 2025-12-31.

At date t:
- impulse = DGS10[t] - DGS10[t-5], in bp.
- rolling threshold = max(15 bp, the 80th percentile of absolute five-session
  impulses over the PRIOR 252 observations). The percentile is shifted one row so
  today's move cannot set its own threshold.
- an event begins only when abs(impulse) is at/above the threshold and the prior
  date was below its then-current threshold.
- require finite nominal, real, breakeven and volatility inputs.
- no second event is admitted until the prior event's ten-session outcome window
  ends. This makes the event catalog non-overlapping by construction.

The event direction is sign(impulse).

## Outcome

Starting with the next business observation, look ten DGS10 observations forward.

Symmetric barrier:
max(10 bp, 20-session std of one-session DGS10 bp changes * sqrt(5)).

For an upward impulse:
- continuation = DGS10 reaches origin + barrier first.
- reversal = DGS10 reaches origin - barrier first.
For a downward impulse the signs mirror.
- no_hit = neither barrier by ten observations.
- ambiguous = both barriers touched on the same daily observation.
- censored = ten future observations are unavailable.

Decision time is the origin close; future target starts at t+1.

## Frozen driver states

All five-session changes end at t.

1. driver_state from nominal/real/breakeven decomposition after multiplying real
   and breakeven changes by the impulse direction:
   - REAL: signed real contribution > 0 and >=1.5x the positive inflation contribution.
   - INFLATION: signed breakeven contribution >0 and >=1.5x positive real contribution.
   - MIXED: both signed contributions >0 but neither dominates 1.5x.
   - CONFLICT: otherwise.

2. term_premium_state: five-business-day change in the latest PIT-available
   Kim-Wright term premium, expressed in bp relative to impulse direction:
   CONFIRM >= +5bp, OPPOSE <= -5bp, else FLAT. Missing = UNKNOWN.

3. credit_state: five-observation HY OAS change:
   WIDEN >= +10bp, TIGHTEN <= -10bp, else FLAT.

4. oil_state: five-observation WTI percent change:
   UP >= +3%, DOWN <= -3%, else FLAT.

5. curve_state: five-observation 2s10s change:
   STEEPEN >= +10bp, FLATTEN <= -10bp, else FLAT.

6. auction_state: most recent nominal coupon auction on or before t and within
   three calendar days, scored with the incumbent Treasury-supply formula using
   trailing=8, min_trailing=5, strong_z=0.6. SOFT / STRONG / INLINE / NONE.

No threshold sweep is authorized inside v1.

## Models and hierarchy

Three-class probabilities: reversal / no_hit / continuation.

Every forecast uses only prior non-overlapping events whose outcome window ended
strictly before the current origin. Laplace smoothing is applied at the unconditional
level, then each exact-state layer shrinks to its parent with weight 12.

- unconditional
- impulse_direction: event direction only
- decomposition: + driver_state
- decomp_term PRIMARY: + term_premium_state
- crossasset: + credit_state + oil_state + curve_state
- full: + auction_state

Primary comparison is decomp_term versus impulse_direction using three-class
sum Brier loss on the 2022-01-01 through 2025-12-31 partition. That partition is
not pristine: the program has already examined 2021-2025 rates history in RD1.
It is therefore a seen-history research partition, never promotion evidence.

Secondary outputs: log loss, calibration by class, event counts, outcome counts,
direction asymmetry, driver-state counts, and exact event rows.

Minimum descriptive floor: 50 scored primary events overall and 20 events for any
subgroup-specific interpretation. Falling below the floor yields INSUFFICIENT_SAMPLE.

## Falsifier and next authority gate

The central hypothesis is falsified for this construction if decomp_term fails to
improve Brier over impulse_direction or the primary sample is below 50 events.

Even a positive result would only justify a candidate prospective shadow. Production
rates intelligence requires independent review, current-source integration, and
genuinely forward issuance/outcome evaluation. Rank, size, gate, alert and trade
authority remain none.
