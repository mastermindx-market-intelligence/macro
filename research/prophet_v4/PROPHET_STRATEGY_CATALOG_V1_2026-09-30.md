# Prophet Strategy Catalog v1 — Eight-Sleeve Roadmap Contract

**Date:** 2026-09-30  
**Base:** `a7e00a9af0f437a4907a32b4591d965e438ca42a`  
**Status:** BUILT_NOT_PROVEN / authority-false source contract. No live ranking, routing, B4, sizing, execution, short, option, or trading authority.

## Product capability

Prophet's machine-readable strategy owner now retains the complete architecture-backed sleeve roadmap instead of exposing only the first tactical definition.

The catalog contains exactly eight governed families:

1. Cyclical Washout Accumulation / Cycle Capture
2. Early Leadership / Sector Rotation
3. Quality Earnings / Expectation Revision
4. Policy and Event Swing
5. Catalyst and Dislocation
6. Liquidity / Debasement / Real Assets
7. Range / Mean Reversion
8. Defensive / Avoidance / Hedge Research

The first three remain the core flagship sleeves. The later five are retained B27 research obligations; catalog inclusion does **not** make them live.

## What the code freezes

Every catalog row carries:

- stable strategy id and human family name;
- core-versus-later roadmap role;
- actual definition status;
- horizon status and whether it is only a research proposal;
- user job and economic mechanism;
- required and optional evidence families;
- lawful regime role;
- entry owner and hold-law boundary;
- concrete falsifiers and kill-law constraints;
- instrument-specific requirements;
- promotion requirements;
- an all-false authority block.

The catalog is closed, content-addressed, validated, and deep-copy safe.

## Crucial distinctions

### Only one strategy has a frozen control definition

`EARLY_LEADERSHIP_SECTOR_ROTATION` remains the only sleeve with the existing accepted control definition. Its `2_15_SESSIONS` value remains a **new-entry identity**, not a universal holding period.

The Earnings H42/H21/H63 and Cycle H252/H126/H504 values are retained only as research proposals. They do not create a hold law.

The five later sleeves have no numeric horizon copied from Early Leadership. Their horizon status is `OWNER_SPEC_REQUIRED`.

### No universal score

A candidate may qualify for several sleeves and those sleeves may disagree. The catalog explicitly forbids:

- a universal score across sleeves;
- using row-constant macro state to rank stocks;
- treating missing evidence as a favorable zero;
- letting the catalog itself set B4 Availability or portfolio allocation.

### Killed research stays killed

Cycle Capture explicitly retains:

- `DNR:KILL-WASHOUT-TURN`
- `DNR:KILL-ROTATION-CYCLE-CONFLUENCE`
- `DNR:KILL-REGIME-SCORECARD`
- `DNR:KILL-FUSED-COMPOSITE`
- `DNR:KILL-PROPHET-POP-MERGE`

Defensive/Hedge research explicitly retains `DNR:KILL-DIRECTIONAL-SHORTING`. No short or option authority is created.

## Sleeve mechanisms

### Cycle Capture

Requires evidence of liquidation, base/pivot repair, genuine cycle economics, survivability/funding/dilution, price incorporation and residual opportunity. A deep drawdown by itself is insufficient.

### Early Leadership / Sector Rotation

Requires company-relative leadership, leave-issuer-out peer support, economic subtheme exposure, setup development/failure state, and remaining opportunity. Sector beta or self-confirming peers are explicit falsifiers.

### Quality Earnings / Expectation Revision

Requires exact event identity, comparable reported financials, source clocks, seasonal EPS strength separated from analyst consensus, pre-release expectations where claimed, matched revisions where claimed, elapsed price response and current entry geometry.

### Policy and Event Swing

Requires public-event authority/timing, exposed-business mapping, reversibility/implementation state and price-response controls. No LLM may mint policy authority.

### Catalyst and Dislocation

Requires a specific dislocation mechanism, source-qualified fundamental state, liquidity/forced-flow evidence and an impairment countercase. A bounce is not sufficient.

### Liquidity / Debasement / Real Assets

Requires instrument-specific transmission. Futures, ETFs and producers cannot share one payoff contract. Carry/roll, producer financing, dilution and hedging matter where applicable.

### Range / Mean Reversion

Requires a qualified non-trending state, predeclared range boundaries, trend-break falsifier and transaction-cost evidence. It is not a general-purpose oversold rule.

### Defensive / Avoidance / Hedge Research

Optimizes risk reduction only after charging missed recovery, hedge carry and slippage. Missing data is not danger. Relative defensiveness is not automatically positive absolute return.

## Verification

The catalog extends the already CI-owned `tests/test_prophet_strategy_definition.py` suite rather than adding a dark test file.

Local exact-branch result:

```
86 passed in 0.51s
```

The tests verify:

- all eight sleeve ids and order;
- exact three core / five retained split;
- only Early Leadership has a frozen control definition;
- research horizons do not become hold laws;
- later sleeves do not inherit `2_15_SESSIONS`;
- macro/regime cannot become a universal stock rank;
- killed Cycle/short constructions remain killed;
- every sleeve has mechanism, evidence, falsifiers and promotion requirements;
- every authority flag remains false;
- stable content identity / deep-copy safety;
- mutation, authority widening and catalog-id mismatch are rejected.

Green tests establish software-contract correctness, not predictive value or production acceptance.

## Next investment-quality step

This catalog removes a major product ambiguity: Prophet now has one canonical machine-readable answer to **what strategies exist and what each is supposed to prove**.

The next scientific/build work can proceed sleeve-by-sleeve instead of forcing every idea into Early Leadership:

- finish Earnings factual/source integration and its same-population predictive comparison;
- complete B09/B10 independent leadership/peer selection;
- advance Cycle B16-B19 source/economic/failure-inclusive evaluation;
- disposition the five retained B27 sleeves with source/readiness research;
- keep B4 and Portfolio/Risk as separate action/capital owners.

No strategy becomes actionable from catalog inclusion alone.
