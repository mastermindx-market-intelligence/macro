# TOI W1 Report — 2026-09-13

## Verdict

`PARTIAL` — the P0 Compression → Release method slice is normalized and machine-checkable, but W1 as commissioned is not complete and W3 remains blocked.

## Capability gained

Before this carrier, W1 had no current machine-readable TOI method passport set. This branch now provides:

- 12 P0 method passports using `toi.method_passport.v1`;
- creator/official/primary source receipts with explicit rights class;
- alias/equivalence normalization distinct from dependency clustering;
- exact local implementation paths and signal IDs;
- crosswalks to Terminal display, Setup Species, Signal Foundry, and Live Entry Radar ownership;
- fail-closed validators plus hostile tests for schema, source, rights and equivalence corruption.

This is enough to stop W3 from rediscovering or double-counting the core compression/breakout/participation vocabulary, but not enough to close W1.

## P0 priority set

The 12 P0 passports are:

1. `toi.bb_bandwidth`
2. `toi.bb_kc_squeeze`
3. `toi.natr_percentile`
4. `toi.hvr`
5. `toi.nr7`
6. `toi.range_expansion`
7. `toi.donchian_breakout`
8. `toi.donchian_fakeout`
9. `toi.fractal_swing_structure`
10. `toi.benchmark_rs`
11. `toi.cmf`
12. `toi.rvol`

They cover setup, trigger, participation, context and risk/failure jobs. The priority is based on product/mechanism relevance and local causal availability, **not** historical return performance.

## Source state

P0/P1 source law is now enforceable: at least one primary or official receipt must resolve for every P0/P1 passport. The current P0 slice uses John Bollinger's official documentation, TA-Lib's BSD-licensed official formula catalog, primary momentum literature, and local source code receipts. Later source additions must extend the same registry rather than embed untracked URLs in prose.

## Equivalence and dependency state

Equivalence classes answer "same method / subtype / alias?". Dependency clusters answer "likely overlapping evidence family?". They are intentionally separate. For example normalized ATR and short/long realized-volatility ratio both live in `volatility_regime` for dependency accounting but are not treated as aliases or algebraic duplicates.

## Owner state

- TOI/W3 may later test the normalized P0 representations under preregistration.
- Setup Species remains the only scientific species registry.
- Live Entry Radar remains the only true tactical 5m/RTH entry owner.
- Terminal remains display/parity evidence, not occurrence authority.
- Signal Foundry / Research Factory remains the candidate automation harness.

## Unresolved gates

W1 cannot be accepted until all of the following are closed:

- populate the remaining P1/P2/archive/blocked method families;
- bind every P0/P1 to primary/official receipts and every licensed input to a rights receipt;
- bind relevant prior kills with stable `DNR:<KEY>` identifiers and preserve any surviving measurement separately from killed constructions;
- classify all tactical-intraday overlap to Radar and Terminal-only visuals to Terminal;
- complete the independent skeptical reproduction of at least 20 sampled passports across source, formula and local implementation;
- run `python3 scripts/agentos.py validate`, all three W1 validators, `pytest tests/test_toi_w1_census.py -q`, and `git diff --check` on the exact return head.

## W3 gate

`HOLD`.

W3 Compression Release outcome testing still requires both accepted W1 and accepted W2-0. Nothing in this P0 census authorizes an outcome read, model fit, parameter search, rank, gate, size, Prophet input or trade.

## Exact next action

Continue the same W1 carrier by normalizing P1/P2/archive/blocked families, starting with the highest-value gaps for the first vertical: support/resistance controls, inside-bar/price structure, ADX/trend-efficiency, 12-1/52-week momentum context, OBV/path risk, short reversal, then the explicitly lower-priority named-pattern/cycle families. After the full passport set is complete, run the independent sample review and return to Sol for acceptance.
