# TOI W1 Report — 2026-09-13

## Verdict

`PARTIAL` — the core P0/P1 Compression → Release and adjacent context census is normalized and machine-checkable at 23 passports, but W1 as commissioned is not complete and W3 remains blocked.

## Capability gained

Before this carrier, W1 had no current machine-readable TOI method passport set. This branch now provides:

- 23 method passports using `toi.method_passport.v1` — 12 P0 and 11 P1;
- creator/official/primary source receipts with explicit rights class;
- alias/equivalence normalization distinct from dependency clustering across all 23 current passports;
- exact local implementation paths and signal IDs for 20 methods and explicit `missing` state for 3;
- crosswalks to Terminal display, Setup Species, Signal Foundry, and Live Entry Radar ownership;
- fail-closed validators plus hostile tests for schema, source, rights and equivalence corruption.

This materially shrinks W3's rediscovery/search space while preserving negative evidence and missing implementations instead of manufacturing completeness.

## Current method set

### P0 — first-vertical core (12)

`toi.bb_bandwidth`, `toi.bb_kc_squeeze`, `toi.natr_percentile`, `toi.hvr`, `toi.nr7`, `toi.range_expansion`, `toi.donchian_breakout`, `toi.donchian_fakeout`, `toi.fractal_swing_structure`, `toi.benchmark_rs`, `toi.cmf`, `toi.rvol`.

### P1 — adjacent controls/context (11)

`toi.support_resistance`, `toi.adx_dmi`, `toi.choppiness`, `toi.momentum_12_1`, `toi.momentum_acceleration`, `toi.high52`, `toi.obv`, `toi.inside_bar`, `toi.ulcer`, `toi.round_levels`, `toi.short_reversal`.

Twenty of 23 are exact local implementations. Three are intentionally `missing`: support/resistance, round-number level controls, and short-horizon reversal. Missing means not implemented, not rejected and not unimportant.

## Source state

P0/P1 source law is machine-enforceable: every current P0/P1 passport resolves at least one registered source receipt, and licensed receipts require an explicit repository rights reference. The source registry now includes creator/official Bollinger material, TA-Lib formula documentation, primary momentum/reversal/52-week literature, New York Fed support/resistance/order-clustering evidence, public bar-grammar methodology, Fibonacci negative evidence, and the Massive internal rights receipt.

The inside/outside-bar passport still cites the broad formula catalog in its current record; `SRC-STRAT-PUBLIC` is now registered as the stronger methodology receipt and the passport should be source-upgraded when the JSONL expansion is next rewritten. That source-quality refinement is visible debt, not a hidden green.

## Equivalence and dependency state

Equivalence classes answer "same method / subtype / alias?" while dependency clusters answer "likely overlapping evidence family?" They remain separate. The 23 methods resolve into 20 equivalence classes: Donchian breakout/fakeout, support-resistance/round-level control, and medium-term momentum/acceleration are explicit family relationships rather than independent votes.

Dependency clusters now expose the important overlap sets for later ablation: volatility regime, volatility range, breakout channel, pattern structure, money flow, multi-horizon momentum, trend strength/efficiency, downside path risk, and short-horizon reversal.

## DNR and ownership state

`DNR:KILL-OUTCOME-AUDITION` is explicitly attached to the short-reversal passport. It forbids per-name best-of-grid timer selection while leaving generic reversal measurement available as a research control. Future adaptive/cycle/path passports must preserve the same construction-versus-measurement distinction.

Owner boundaries remain unchanged:

- Setup Species is the sole scientific species registry.
- Live Entry Radar owns true tactical 5m/RTH entry events.
- Terminal is display/parity evidence, not TOI occurrence authority.
- Signal Foundry / Research Factory remains the candidate automation harness.
- W1 creates no second registry, event store, minute plane, replay system or promotion clock.

## Unresolved gates

W1 cannot be accepted until all of the following are closed:

- populate the remaining P2/archive/blocked families: MA/ribbon/oscillator variants, adaptive filters, gaps/imbalance, geometric patterns, cycle transforms, Fibonacci controls, ordered-path/Elliott representation, breadth/peer context, regime-conditioned behavior and sequence challengers;
- upgrade weaker source receipts when a stronger original/official method source is available;
- bind every relevant prior kill with stable `DNR:<KEY>` identifiers while preserving surviving measurements separately from killed constructions;
- classify tactical-intraday overlap to Radar and Terminal-only visuals to Terminal;
- complete the required independent skeptical reproduction of at least 20 sampled passports across source, formula and local implementation;
- run `python3 scripts/agentos.py validate`, all three W1 validators, `pytest tests/test_toi_w1_census.py -q`, and `git diff --check` on the exact return head.

## W3 gate

`HOLD`.

W3 Compression Release outcome testing still requires accepted W1 and accepted W2-0. No current census artifact authorizes an outcome read, model fit, parameter search, rank, gate, size, Prophet input or trade.

## Exact next action

Continue this same W1 carrier with the P2/archive/blocked census, prioritizing method families that can otherwise inflate the W3 search family through synonyms or hidden overlap. Then execute the >=20-passport reproduction review and exact W1 validation battery. W2-0 proceeds independently on PR #7094; W3 remains held until both predecessors are accepted.
