# TOI W2 Daily-first source and clock ruling — 2026-10-06

Program: WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE
Original W2 carrier: Macro #7094 / TOI-W2-0-DATA-CLOCK-V1 at 5bb1bc68c99146fab040aade04bbf1903c51e5b7.
Current Macro source: 59b83048bd3d782b707ec6a4ca857415409fd776. Current Terminal source: 64c1ea5e25a335a0b0636e73e7fdbe0f8beb7b0e.
Disposition: DAILY_FIRST_PATH_NARROWED / DATA_ADMISSION_STILL_HOLD. MISSION_COMPLETE:false.

This ruling reconciles the original broad W2 Daily/Weekly/4H gate with the later 22-slot Daily-first study. It does not rewrite #7094's broad-panel HOLD, accept an experiment, read market outcomes, select a model, register a trial, modify a data store, or promote a consumer.

## Decision: 4H is not a prerequisite for the first 22-slot study

The supplied recommissioning report states that the critical path is a same-basis, identity-safe, versioned Daily/Weekly substrate and that a Daily/Weekly study need not wait indefinitely for 4H. The later #8332 22-slot narrowing explicitly holds standalone Weekly, 4H-CLOCK and 195M-RTH outside the first primary wave.

For the first 22-slot candidate, qualify Daily source plus completed-Weekly context derived from the same Daily source. 4H and 195M are not dependencies. The original broad Daily/Weekly/4H W2 panel remains HOLD, and later intraday arms keep their own source/clock/basis/parity gates. #7094 also still needs its independent current-base records recompose and acceptance.

## Proposed source family: one raw Daily substrate

Current massive_stock_day stores raw Daily OHLC as floats and volume/transactions as integers; latest write wins on a date tie. Current committed manifest d6ad060e3d0af3296757883f43e955012f9564d8 reports 21,673 ticker files, 2021-07-06→2026-10-02, 1,369 processed dates and zero manifest-reported weekday gaps. SPY carries 1,318 rows across the same endpoints.

For the first study this raw Daily family is the source candidate for Daily occurrence geometry/features and for completed-Weekly context derived from those Daily closes. Economic outcomes get a separately frozen basis only after corporate-action handling is accepted. The manifest is not per-member coverage, historical first-receipt proof, a corporate-action transform, or a historical identity proof.

Volume is load-bearing: the persisted store casts volume to int64. A volume-sensitive P1 feature must explicitly bind that representation inside its native config or use a separately receipted alternative. Persisted integer volume and live fractional provider values are not silently equivalent.

## Completed-Weekly contract: label, known date, completion

The weekly contract carries three different facts:
- W-FRI label = calendar bucket identity;
- weekly_known_date = last actual Daily date present in that bucket;
- weekly_complete = no canonical US cash-equity session exists after weekly_known_date through the W-FRI label.

A raw W-FRI last resample is insufficient because an in-progress Wednesday bucket already receives Friday's label. Existing research code already maps W-FRI buckets to the maximum actual Daily date. Use that with the existing lib.nyse_calendar session owner; do not create another calendar.

Synthetic validation proves:
- normal Friday complete;
- Wednesday before ordinary Friday incomplete;
- Thursday before a full-day Friday closure complete;
- Thursday before an early-close Friday incomplete on Thursday because Friday still has a session.

Early-close wall-clock time is unnecessary for deciding whether a Daily weekly bucket has another session. It remains required for intraday/4H. Source publication/correction time remains separate from the bar calendar.

The earlier weekly diagnostic receipts were executed at ca00b1c549733b562aae33d15f070300de3fb21e; the exact helper/calendar/source blobs are unchanged at current Macro 59b83048bd3d782b707ec6a4ca857415409fd776.

## Proposed denominator: PIT S&P 1500 from the Daily-store start

Current Data OS correctly refuses to fabricate U.S. listing dates from earliest bars. Whole-market historical eligibility remains unavailable, but the first bounded study need not claim the whole market.

Committed S&P1500 PIT membership blob ec7085bc7460aca4a07661fa5983c424e1559be8 contains 3,286 membership intervals / 2,589 unique ticker strings: SP500 1,255, SP400 969, SP600 1,062; 1,780 intervals are closed. 2,205 intervals / 1,924 tickers overlap 2021-07-06 or later.

The reconstruction source documents SP400 history from roughly 2012 and SP600 from roughly 2020, so the common 2021-07-06 Daily-store start is within those stated history ceilings.

Proposed population: PIT S&P1500 membership x dates >= 2021-07-06, retaining every member-date denominator cell. Missing or ambiguous price/identity becomes explicit unavailable/missingness, never a silent exclusion. This is a proposed scientific amendment for owner adoption, not an admission. A result would initially generalize to this bounded population, not all U.S. equities.

Ticker-string membership is not full historical security identity. Current security-master source says effective_at is not a listing date and historical issuer lineage is unavailable. Rename/ticker-reuse resolution remains a gate; current-symbol aliases must not be backdated over leavers.

## Historical evidence ceiling: RETROSPECTIVE unless proven stronger

latest-write-wins Daily history does not prove which corrected value existed at every historical decision. The repository's accepted evidence vocabulary calls a known construction with an unprovable historical knowledge boundary RETROSPECTIVE; OBSERVED_AS_RUN requires a writer-stamped capture clock and pinned generation.

A future accepted first retrospective run should therefore bind an immutable source_archive_vintage/digest and feature dates <= decision date, but must set historical_original_receipt_claim=false and cap the evidence class at RETROSPECTIVE unless stronger receipts exist. RETROSPECTIVE is diagnostic/research evidence, not ranking, sizing or promotion, and cannot replace the later untouched/prospective stage.

## Remaining first-wave data gates

| Gate | State | Closure |
|---|---|---|
| Population | PROPOSED / HOLD | Adopt PIT S&P1500 window; census every member-date's price and identity status before outcomes. |
| Daily geometry basis | SOURCE IDENTIFIED / HOLD | Pin exact archive generation/digest and accept raw-unadjusted geometry semantics. |
| Weekly context | CONTRACT QUALIFIED / NOT STUDY-ADMITTED | Bind label + known_date + canonical-session completion in admitted harness. |
| Volume | HOLD | Freeze persisted-int64 or separately receipted representation inside native config. |
| Economic outcome basis | HOLD | Freeze split/corporate-action handling and return basis. |
| Historical knowledge | RETROSPECTIVE ceiling proposed | Pin archive vintage and disclose absent original receipt/correction clocks. |
| Price/identity coverage | HOLD | Explicit available/missing/ambiguous census including rename/ticker-reuse cases. |
| Per-use admission | HOLD | Existing source/scientific/Evaluation owners return ADMIT/HOLD/REJECT. |

Intraday live_tail, stored 5m/1h and provider-hourly paths are outside this first-wave table. They remain held for later 4H/chart uses.

## Consequence

This ruling removes 4H as an unnecessary dependency but does not open W3. Sequence remains W1 acceptance -> W2 records acceptance -> bounded Daily source/population adoption -> exact 22-config scientific/evaluation manifest -> TrialLedger registration -> admitted outcome run -> prospective accrual -> consumer-specific acceptance.

No market outcome, fitted model, real trial registration, production mutation, Prophet rank/gate, sizing or trading authority follows.
