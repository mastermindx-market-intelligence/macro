# TOI W2-0 Data Plane Census

**Operation:** `TOI-W2-0-DATA-CLOCK-V1`  
**Pins:** Skillpack `9e180aadd0b8930867d304ad62ea27a2f12375cc` · Macro `021b2ae3a4a6a508f3e0fc56d00a85b21adf1be3` · Terminal `a4be9a3f4b51246200cb1b7c4f1d44730066a9a9`  
**Verdict:** `PARTIAL / HOLD`

The broad Weekly/Daily/4H panel is not admitted. Daily depth and Massive rights are real, and the Radar owner already has a causal 09:30-anchored, early-close-aware 4H grid, but the current broad research/product planes do not yet form one causally coherent whole-universe panel.

## Findings

1. `massive_stock_day` is deep and broad: the current manifest reports 21,526 tickers, 2021-07-06→2026-09-10 coverage, 1,353 processed days, zero current weekday holes, and a 1,302-row SPY anchor. It is raw-basis and lacks per-bar historical first-receipt/correction-vintage proof.
2. Macro `data/intraday` is hourly, curated, 15-minute delayed and optional. `engine/mtf_monitor.py` uses pandas `resample("4h")`, not the owner-native session grid.
3. Terminal has deep 1h all-US history and 5m top-N history. Its server-side 4H resample is 09:30 anchored when 5m exists.
4. Production parity measurement: 15/15 regular-session cases, including both sides of the March DST boundary, matched the canonical 4H derivation. Five of five 2025-11-28 early-close cases failed because Terminal admitted a 13:00-stamped 5m row on the 13:00 close.
5. A 20-name production sample without 5m history fell back to six 1h rows beginning 10:00 ET. Exact 09:30-open whole-universe 4H coverage is therefore unproven.
6. Live Entry Radar already owns the correct session-aware 4H semantics and an episode-windowed minute reader. It is an oracle/boundary, not permission for TOI to build a second tactical plane or bulk minute store.
7. Massive research/display/derived-data rights are admitted by the current entitlement record.
8. Data OS identity is live, but the broad historical eligible-universe denominator is partial; S&P1500 PIT membership is useful but not an all-US denominator.

## W2 extension authorized by this HOLD

W2 may extend existing owners only:

- make the research 4H adapter consume the existing Radar session-window/4H semantics rather than pandas clock resampling;
- qualify one same-basis Daily+4H source family with correction and known-at receipts;
- repair Terminal early-close/session filtering under its existing intraday owner, or explicitly version product and research as different bar identities;
- prove the broad historical eligibility denominator through existing Data OS/PIT owners.

No new feed, WebSocket, minute database, identity plane, event store, replay plane or tactical evaluator is authorized.
