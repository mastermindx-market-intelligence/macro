# TOI W1 Report — 2026-09-13

## Verdict

`PARTIAL / REPAIR_APPLIED_AWAITING_REREVIEW` — the 32-passport active census and 10-family residual disposition are normalized. The first independent reproduction returned **18 PASS / 2 FAIL** on immutable head `accd7c6a296fd038ae863d071fa44244c4796e0a`. Both findings are repaired on this carrier without reading market outcomes or changing live signal behavior. W1 still requires fresh bounded independent verification of those repaired findings plus the exact return-head validation/integration proof before Sol acceptance.

## Capability gained

This carrier now provides:

- **32 `toi.method_passport.v1` passports**: 12 P0, 10 P1, 8 P2, 2 archive;
- **10 residual-family dispositions** that route or block the remaining method tail without expanding the first W3 trial family;
- primary/official/creator source receipts and explicit rights classes;
- alias/equivalence normalization separate from dependency clustering;
- **26 exact local implementations, 1 explicit partial local implementation, and 5 missing implementations**;
- owner routing for Setup Species, CPI, Live Entry Radar, Terminal, breadth/universe, regime, and later-context path research;
- fail-closed passport/source/equivalence/residual validators plus hostile tests;
- a deterministic 20-passport independent-reproduction sample with no outcome-derived selection.

This is evidence architecture, not a performance result.

## Independent review result and repair

Operation `toi-w1-20-passport-independent-review-20260913-sol-001` completed against exact head `accd7c6a296fd038ae863d071fa44244c4796e0a`. The independent reviewer reproduced the frozen 20-passport sample and returned **18 PASS / 2 FAIL**.

### Finding 1 — Connors RSI provenance

The passport previously cited only broad TA-Lib primitives even though the local method is the specific ConnorsRSI `(3,2,100)` composite.

Repair:

- added `SRC-STOCKCHARTS-CONNORS-RSI`, an official-platform method-specific formula receipt;
- bound `toi.connors_rsi` to that receipt;
- pinned the three components as 3-period RSI of price, 2-period RSI of streak, and 100-period price-change percent rank, averaged together;
- retained `P2 / terminal_display` and the existing RSI-family entry-stack block.

No W3 authority was added.

### Finding 2 — RVOL source/local mismatch

The prior passport called the local implementation exact, but `engine/volume_flow_signals.py::_rvol` uses `rolling(20).mean()` including the current bar, while the receipted RVOL methodology compares the current bar to an average of prior completed bars.

Repair:

- added `SRC-STOCKCHARTS-RVOL`, which explicitly defines current volume relative to the average over a configurable number of prior bars;
- froze the passport method as current volume divided by the prior 20 completed bars, excluding the current bar;
- downgraded the current local implementation from `exact` to `partial` instead of changing live signal behavior inside a records-only wave;
- recorded the inclusive-current local denominator as a load-bearing mismatch that W3 must repair or explicitly version before using RVOL.

This keeps the P0 method scientifically available while preventing a false parity claim.

## Active passport universe

### P0 — first-vertical core (12)

`toi.bb_bandwidth`, `toi.bb_kc_squeeze`, `toi.natr_percentile`, `toi.hvr`, `toi.nr7`, `toi.range_expansion`, `toi.donchian_breakout`, `toi.donchian_fakeout`, `toi.fractal_swing_structure`, `toi.benchmark_rs`, `toi.cmf`, `toi.rvol`.

### P1 — adjacent controls/context (10)

`toi.support_resistance`, `toi.adx_dmi`, `toi.choppiness`, `toi.momentum_12_1`, `toi.momentum_acceleration`, `toi.high52`, `toi.obv`, `toi.ulcer`, `toi.round_levels`, `toi.short_reversal`.

### P2 — later/context/control families (8)

`toi.inside_bar`, `toi.ma_trend`, `toi.rsi_oscillator`, `toi.kama_er`, `toi.supertrend`, `toi.connors_rsi`, `toi.geometric_double_pattern`, `toi.ordered_path_elliott`.

### Archive/comparator (2)

`toi.macd_stoch_incumbent`, `toi.fibonacci_retracement`.

## Local implementation truth

- **26/32 exact local**.
- **1/32 partial local:** `toi.rvol` because current local inclusive-window math does not exactly reproduce the source-defined prior-bar baseline.
- **5/32 missing:** causal support/resistance, round-level controls, short reversal, Fibonacci retracement, ordered-path/Elliott.
- Priority/local reconciliation: P0 = 11 exact + 1 partial; P1 = 7 exact + 3 missing; P2 = 7 exact + 1 missing; archive = 1 exact + 1 missing.
- Missing or partial does not mean rejected and does not authorize W1 to implement the method.

## Residual-family disposition

The residual census remains unchanged and outcome-blind:

- generic FVG/imbalance is later-context and not the killed PM3 gap-map construction;
- divergence remains later-context pending explicit causal confirmation semantics;
- broad candlestick-name enumeration is archived;
- cycle/phase/transition stays CPI-owned;
- breadth/peer context reuses the canonical breadth/universe owner;
- regime conditioning consumes the existing regime plane and may not create a fused score;
- sequence learning remains later/not-built behind simpler causal baselines;
- exhaustion/extension follows a proven setup→release occurrence;
- opaque fused vendor methods and undisclosed pivot methods remain blocked.

## Cycle/path ruling

`toi.ordered_path_elliott` remains `P2 / toi_later_context / missing`. Its contract requires causal confirmed pivots, multiple candidate parses or abstention under ambiguity, and an equal-budget generic causal swing baseline. `DNR:KILL-OUTCOME-AUDITION` forbids per-name best-count selection. Fibonacci specificity remains a separate archive/control family.

This preserves the long-term cycle-forecasting thesis without widening the first Compression Release experiment.

## Ownership and authority

- Setup Species remains the sole scientific species registry.
- CPI remains cycle phase/turn/hazard owner.
- Live Entry Radar retains tactical 5m/RTH ownership.
- Terminal remains display/parity evidence, not canonical occurrence authority.
- existing breadth/universe and market/regime planes remain canonical.
- Signal Foundry / Research Factory remains the research automation harness.

No market outcomes were read. No model was fit. No W3 trial is registered. No Prophet, rank, gate, size, execution, or trading authority is created.

## Remaining acceptance gates

1. Obtain fresh **bounded independent verification of the two repaired findings** on the repaired immutable W1 head. The prior review child is terminal and cannot be silently continued.
2. Run `python3 scripts/agentos.py validate`, the W1 passport/source/equivalence validators, `pytest tests/test_toi_w1_census.py -q`, and `git diff --check` on that same immutable head.
3. Reconcile the records-only CI waiver against current protected main if needed and obtain current-base merge/integration proof plus hosted checks.
4. Return exact repaired head and proof to Sol for W1 acceptance.

## W3 gate

`HOLD`.

W3 Compression Release outcome testing remains blocked until W1 and W2-0 are both accepted. Elliott/cycle outcomes remain later still.
