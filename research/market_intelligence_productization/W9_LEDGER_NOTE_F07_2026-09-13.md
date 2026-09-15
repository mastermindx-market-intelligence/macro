# W9 LEDGER NOTE — F07 slice, LEDGER_MOVES #4–6 (not applied)

**Date:** 2026-09-13
**Packet:** W9B_REC_F07
**Status:** PROPOSED, NOT APPLIED — moves #4–6 are pasted here as a research note only.
**CSV owner:** PR #7014 owns the F00C granular closure ledger (`research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`). This packet writes no row to that file.

## Why this note exists

The records stack has reserved moves #4, #5 and #6 for the F07 valuation-scenario slice. This document captures what those moves would say, in the order the records stack would paste them, against the four F07 rows that the F00C CSV already carries. No row is moved here. The CSV at `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` is byte-identical to its `origin/main` form (ancestor tip `321da62b3b0163b6ab5a287fb9847a13ed7f3ed2`); every quoted row below is read from that file and is therefore the same bytes that any consumer of the main branch sees today.

The records stack pastes these moves only after the F07 valuation-source ruling lands; until then the moves sit here, in plain language, so the records lane can lift them verbatim.

## Scope of this note

This note covers four F07-VALUATION-SCENARIO rows in the F00C CSV. The proposed `capability_state_c2` value for every row in this slice is `NOT_BUILT`. The proposed `granular_disposition` values are recorded for completeness — `BLOCKED_RIGHTS` is the only disposition a move would write here, and only for the three rows whose consensus-estimate dependency is verified negative. `PROVEN_LIVE` is never set.

The capability state vocabulary this note uses is exactly `{NOT_BUILT, PARTIAL, BUILT_NOT_PROVEN, SPEC_ONLY, PROVEN_LIVE}`. Of those, only `NOT_BUILT` is proposed; the others are listed for vocabulary pinning only.

## LEDGER_MOVE #4 — MO-PAID-035

- **Row id:** `MO-PAID-035`
- **Family:** F07-VALUATION-SCENARIO
- **Quoted stale text (verbatim from F00C CSV, ancestor tip `321da62b3b01`):**
  - `granular_disposition`: `NEW_BOUNDED_BUILD`
  - `capability_state_c2`: `NOT_BUILT`
  - `state_delta`: `UNCHANGED (stock_fundamentals.py:1815: consensus 'remain unwired')`
  - `next_bounded_child`: `DOCKETED_TERMINAL_HALF_B; DEFER — dependency FIF-3A4R separate commission + F07 valuation-source ruling`
- **Merge citation + ancestor claim:** the row sits at `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`, line 59 against ancestor tip `321da62b3b01`; this packet touches none of its cells. The verification at `engine/stock_fundamentals.py:1815` ("consensus 'remain unwired'") is the negative evidence the records stack cites for this move.
- **Proposed `capability_state_c2`:** `NOT_BUILT`. The valuation baseline is unbuilt because no consensus-estimate source exists; moving the row to any built state would require a build block, which is not proposed here.
- **Proposed `granular_disposition` (out-of-vocabulary record only):** `BLOCKED_RIGHTS`, reflecting the verified-negative consensus source.
- **Proposed `next_bounded_child`:** `DOCKETED_TERMINAL_HALF_B; DEFER — dependency FIF-3A4R separate commission + F07 valuation-source ruling`. The child is unchanged; the move only records the disposition.

## LEDGER_MOVE #5 — MO-PAID-022 and MO-PAID-026 (combined)

This move is a pair. The records stack groups both rows because MO-PAID-026 depends on MO-PAID-022 and on MO-PAID-035.

### MO-PAID-022

- **Row id:** `MO-PAID-022`
- **Family:** F07-VALUATION-SCENARIO
- **Quoted stale text (verbatim from F00C CSV, ancestor tip `321da62b3b01`):**
  - `granular_disposition`: `NEW_BOUNDED_BUILD`
  - `capability_state_c2`: `NOT_BUILT`
  - `state_delta`: `UNCHANGED`
  - `next_bounded_child`: `BLOCKED_RIGHTS adjacency: F07 valuation-source decision (F00B fanout item 3) precedes any build`
- **Merge citation + ancestor claim:** the row sits at `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`, line 57 against ancestor tip `321da62b3b01`; this packet touches none of its cells. The `next_bounded_child` already names the dependency on a valuation-source decision that has not been taken.
- **Proposed `capability_state_c2`:** `NOT_BUILT`. The event-to-assumption-to-valuation path is unbuilt because consensus-estimate source rights are not cleared.
- **Proposed `granular_disposition` (out-of-vocabulary record only):** `BLOCKED_RIGHTS`, mirroring the dependency that MO-PAID-035 already pins.
- **Proposed `next_bounded_child`:** `BLOCKED_RIGHTS adjacency: F07 valuation-source decision (F00B fanout item 3) precedes any build`. The child is unchanged; the move only records the disposition.

### MO-PAID-026

- **Row id:** `MO-PAID-026`
- **Family:** F07-VALUATION-SCENARIO
- **Quoted stale text (verbatim from F00C CSV, ancestor tip `321da62b3b01`):**
  - `granular_disposition`: `NEW_BOUNDED_BUILD`
  - `capability_state_c2`: `NOT_BUILT`
  - `state_delta`: `UNCHANGED`
  - `next_bounded_child`: `DEFER — dependency MO-PAID-022/035`
- **Merge citation + ancestor claim:** the row sits at `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`, line 58 against ancestor tip `321da62b3b01`; this packet touches none of its cells. The `next_bounded_child` already names the two-row dependency that this move records.
- **Proposed `capability_state_c2`:** `NOT_BUILT`. The scenario engine is unbuilt because the valuation baseline (rows 022 and 035) is unbuilt.
- **Proposed `granular_disposition` (out-of-vocabulary record only):** `BLOCKED_RIGHTS`, inherited through the 022+035 dependency.
- **Proposed `next_bounded_child`:** `DEFER — dependency MO-PAID-022/035`. The child is unchanged; the move only records the disposition.

## LEDGER_MOVE #6 — MO-DELTA-017 (no row movement)

This move records the row without moving it. The records stack reads the F00C CSV as a two-part row: a consensus half (which would move to `BLOCKED_RIGHTS` once MO-PAID-035 moves) and a FIF half (which still needs a build block). Because the row cannot be moved atomically without splitting it, the move is a record-only consolidation.

- **Row id:** `MO-DELTA-017`
- **Family:** F07-VALUATION-SCENARIO
- **Quoted stale text (verbatim from F00C CSV, ancestor tip `321da62b3b01`):**
  - `granular_disposition`: `NEW_BOUNDED_BUILD`
  - `capability_state_c2`: `NOT_BUILT`
  - `state_delta`: `UNVERIFIED->CONFIRMED UNCHANGED (FIF catalog consolidated_only; no consensus source landed; K3-E adjacent-not-equivalent)`
  - `next_bounded_child`: `DEFER — F07 valuation-source ruling + FIF pipeline past fixture-only`
- **Merge citation + ancestor claim:** the row sits at `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`, line 56 against ancestor tip `321da62b3b01`; this packet touches none of its cells. The FIF catalog status and the negative consensus search are the two halves the move records.
- **Proposed `capability_state_c2`:** `NOT_BUILT`. The full company workspace (statements + consensus + adjusted valuation + assumption trail) is unbuilt; the FIF half is fixture-only and the consensus half has no source.
- **Proposed `granular_disposition` (out-of-vocabulary record only):** `NEW_BOUNDED_BUILD`. No move; the row stays in its current disposition because the FIF half is still a build block.
- **Proposed `next_bounded_child`:** `DEFER — F07 valuation-source ruling + FIF pipeline past fixture-only`. The child is unchanged; the move only records the two-part reading.

## Summary

| LEDGER_MOVE | Row | Proposed `granular_disposition` | Proposed `capability_state_c2` | Notes |
|---|---|---|---|---|
| #4 | MO-PAID-035 | `BLOCKED_RIGHTS` | `NOT_BUILT` | Consensus source verified negative at `engine/stock_fundamentals.py:1815`. |
| #5 | MO-PAID-022 | `BLOCKED_RIGHTS` | `NOT_BUILT` | BLOCKED_RIGHTS adjacency; child unchanged. |
| #5 | MO-PAID-026 | `BLOCKED_RIGHTS` | `NOT_BUILT` | Inherits through the 022+035 dependency; child unchanged. |
| #6 | MO-DELTA-017 | `NEW_BOUNDED_BUILD` (no move) | `NOT_BUILT` | Two-part reading wins: FIF half is still a build block. |

## What this packet does NOT do

This packet does not apply any of the moves above. The CSV at `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` is not edited by this packet; every row in the F07 slice is byte-identical to the ancestor tip. PR #7014 (the records stack) owns the CSV; the records lane pastes the moves above only after the F07 valuation-source ruling lands. The companion F07 note (proposed in this packet's PR body) is the only new artifact this packet adds to the ledger slice.