# Technical Opportunity Intelligence W2-0 Report

**Operation:** `TOI-W2-0-DATA-CLOCK-V1`  
**Skillpack:** `Mastermind@9e180aadd0b8930867d304ad62ea27a2f12375cc`  
**Macro base:** `021b2ae3a4a6a508f3e0fc56d00a85b21adf1be3`  
**Terminal evidence pin:** `a4be9a3f4b51246200cb1b7c4f1d44730066a9a9`  
**State:** `PARTIAL`  
**W3 gate:** `HOLD`

W2-0 is complete as an archaeology/admission wave: the result is a lawful HOLD, not an unfinished audit.

## What is proven

- the current Massive daily manifest is broad and current enough to be a real candidate substrate: 21,526 tickers, coverage 2021-07-06 through 2026-09-10, 1,353 processed days, zero current weekday holes, and a 1,302-row SPY anchor;
- the current Massive entitlement record admits research, derived storage, display, redistribution, retention and AI/ML use;
- Data OS remains the identity owner and explicitly models symbol continuity/ticker reuse;
- Live Entry Radar already owns the causal US session clock and 09:30-anchored 4H grid, including early closes;
- production Terminal 4H matched an independent 09:30-anchored resample in 15/15 regular-session cases, including observations on both sides of the March DST boundary.

## What blocks ADMIT

- production Terminal parity failed in 5/5 measured 2025-11-28 early-close cases: the deep 5m path returned 43 rows through a 13:00-stamped row on a 13:00 close, whereas the canonical session-close rule admits 42 rows through 12:55; the extra row changed close and/or volume in every measured 4H bar;
- Terminal whole-universe 4H is not source-homogeneous: when 5m history is absent it falls back to provider-built 1h history; a 20-symbol sample without 5m history exposed six hourly rows beginning at 10:00 ET, so exact 09:30-open whole-universe coverage is not proven;
- Macro's existing optional hourly store is curated, 15-minute delayed and its `mtf_monitor` consumer uses pandas `resample("4h")`, not the owner-native session grid;
- the deep Massive daily store is raw-basis while current intraday owners use `adjusted=true`; no same-basis Daily+4H family with historical first-receipt/correction-vintage proof has been accepted;
- canonical identity exists, but a broad all-US historical eligible-universe denominator is still partial. S&P1500 PIT membership is useful but is not the whole-US denominator.

## Exact next action

Run W2 as a bounded existing-owner repair/qualification wave. First make the actual exchange close load-bearing in Terminal/research 4H parity and re-prove at least 20 production parity cases including early closes. Then qualify one same-basis Daily+4H source family and the historical eligibility denominator. Keep W3 and every market-outcome read held.

No outcome, model, Prophet, ranking, sizing, trade, execution or production-signal authority is created by this report.
