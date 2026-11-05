# Options Workbench R2 — Conditional Greek Scenario Surface

Date: 2026-09-18
Operation: `options-workbench-r2-scenario-surface-20260918-sol-001`
Parent: Terminal #603 Options Workbench recovery
Carrier: Macro PR #7306 / `claude/options-workbench-r2-scenario-surface-20260918-sol-001`
Protected Skillpack: Mastermind `61a2ff79aba4e8a5685e779707ad5c4426cf5cc5` (1.0.1/bootstrap 1)
State: **BUILT_NOT_PROVEN** until independent review, exact-head CI, Terminal consumption and production proof.

## Capability delta

Before this slice, Mastermind had observed strike × session-time surfaces and spot-repriced gamma profiles, but no typed conditional field answering:

> Given the information frozen at this observation, how would modeled Gamma/Vanna/Charm exposure change across hypothetical underlying prices and later times?

`engine/options_scenario_surface.py` now produces `options.scenario_surface/v1`, a **conditional price × future-time scenario**, explicitly not observed history and not a predicted price path.

The engine:
- reuses `engine.intraday_greeks.bs_greeks_vec` and the incumbent exposure units/sign convention;
- can consume an already frozen per-contract IV snapshot (`provided_iv`) **or**, when explicitly selected, consume the real mid+OI contract shape and reuse incumbent `implied_vol_vec` (`solve_from_mid`);
- freezes the resulting per-contract IV and supplied OI for the scenario;
- deterministically rolls remaining time forward and excludes expired contracts;
- evaluates GEX, VEX and CEX on explicit scenario-price × horizon grids;
- emits zero-crossing coordinates for **each** selectable metric (GEX/VEX/CEX), with the legacy Gamma alias retained for compatibility;
- retains all zero crossings instead of collapsing to a single nearest flip;
- preserves explicit market / IV / OI clocks, scope, conventions, units, assumptions and source-count diagnostics;
- fails cells closed to `null` on numerical overflow and emits honest null rows after the frozen contract set has expired.

## Fixed assumptions — not hidden inference

V1 deliberately supports only:
- fixed input OI snapshot;
- sticky-strike frozen IV;
- deterministic elapsed-time roll-forward;
- incumbent assumption-based long-call / short-put dealer-sign convention;
- scenario prices supplied by the caller, **not** a forecast distribution or predicted path.

`sticky_delta` and other volatility dynamics are rejected rather than approximated. The scenario layer does not create a collector, store, scheduler, replay owner, price forecast, trade signal, score or execution authority.

## Actual live-data seam

The first candidate required callers to pre-solve IV. That was insufficient for the real Terminal job because the current live options path owns mids + prior-session OI and the IV solver already exists in `engine.intraday_greeks`.

The review-hardening adds explicit `iv_source="solve_from_mid"`. In that mode, the engine uses the **same** `implied_vol_vec` as the incumbent intraday Greek path at the observation spot, drops unsolved contracts honestly, freezes only the successfully solved IVs, and then reuses the same `bs_greeks_vec` / exposure formulas for the scenario.

A discriminating horizon-zero test builds real mids from Black-Scholes, sends mid+OI contracts through the new mode, and compares the aggregate GEX/VEX/CEX against `compute_greek_grids`. With asymmetric call/put OI the values match to floating precision, proving the new path is not a second pricing kernel.

### Point-in-time source law

The conditional field freezes one lawful information set; source metadata is not decorative.

- `iv_observed_at` may never be later than `market_observed_at`.
- `solve_from_mid` requires an explicit `iv_observed_at`; an unknown IV source clock is rejected rather than inherited from the market wrapper.
- when `oi_vintage` is supplied it must be a valid ISO date **strictly before** the observation's ET date. Same-day OI is rejected under the existing lagged-OI law.
- unknown OI vintage remains null rather than being fabricated. The production consumer is still responsible for passing the exact vintage supplied by the accepted OI owner.

These checks constrain the information set only; they do not change IV, Greek or exposure calculations.

### Canonical live-contract adapter

The accepted intraday quote producer (#7279) emits contract expiry as `exp_str`, not
`expiry`, and carries per-contract `trade_at` / `quote_at` provenance. R2 now consumes
that shape directly rather than forcing Terminal to translate or silently losing scope.

- `exp_str` is accepted as the canonical expiry alias; a supplied `expiry` remains
  supported for generic callers.
- if both expiry aliases are present and disagree, that contract is rejected as invalid.
- expiry scope / 0DTE-style filtering therefore works on the actual live quote objects.
- contributing trade and NBBO clocks are summarized into
  `trade_at_first/last` and `quote_at_first/last`.
- those envelopes use the incumbent fail-closed rule: if any contributing member has an
  unknown/malformed clock, the aggregate pair is null rather than a misleading known-only range.
- a known contract source clock after `market_observed_at` is an impossible information set
  and raises rather than being backdated.

This is an adapter inside the scenario engine, not a new quote collector or provenance plane.

## Contours

The returned field now includes:
- `zero_crossings.gex[]`
- `zero_crossings.vex[]`
- `zero_crossings.cex[]`

Each horizon entry carries all interpolated price-axis crossings for that metric. This is the numerical input a later Terminal renderer can connect into white zero-contour branches for whichever Greek the user selects. `gamma_zero_crossings` remains an additive compatibility alias over GEX.

## Verification

TDD review hardening:
- RED: Gamma-only contour contract and no `iv_source` seam caused **3 focused failures**.
- GREEN: those three cases pass after the bounded contour/live-input repair.
- RED: same-day OI was accepted by the subsequent source-clock guard.
- GREEN: source-clock/PIT + live-input/contour focused set is **4 passed / 0 failed**; same-day OI and mid-solved IV without an explicit IV clock are now refused.
- RED: the actual #7279 `exp_str` live shape was omitted by expiry scoping, source-clock envelopes were absent, and conflicting expiry aliases were accepted.
- GREEN: canonical live-contract adapter set is **3 passed / 0 failed**; `exp_str` scopes correctly, clock envelopes survive with mixed-unknown fail-closed semantics, and conflicting/future identities are refused.

Fresh candidate proof:
- scenario + incumbent intraday-Greek + GEX + options-matrix owner pack: **91 passed / 0 failed**;
- changed-source `compileall`: pass;
- `git diff --check`: pass.

Fresh protected-main proof:
- protected Macro main: `36fbbbfcc045fa422ba3be94f3c29e5206d2e35d`;
- proof-only integrated commit: `d7b6514128bfcfe4eb11fc2f4c15797531080587`;
- proof tree: `b558ae1b0d34671edd9979f70b38be4fe5653fdc`;
- parents: current main + pre-live-adapter #7306 head `6f2df12fe79d73a9b57feba4f62734551b956b59`;
- integrated owner pack: **91 passed / 0 failed**;
- integrated compileall/diff check: pass.

Compact red/green and owner-pack receipts live under:
`research/evidence/options-workbench-r2-scenario-surface-20260918/`.

## Non-claims / next vertical

This does **not** make the Options Workbench Quanted-level complete. It does not prove:
- production deployment or live source freshness;
- measured participant/MM inventory;
- predictive edge;
- the separate full-chain Greek field-completeness denominator;
- Terminal rendering, linked-pane UX, responsive browser behavior or end-to-end replay/scenario composition.

Next after source acceptance: a separate Terminal consumer slice under the existing Workbench/linked-pane owners that can render observed history left of NOW and this conditional scenario field right of NOW, with metric-local zero contours, explicit scenario labeling, source clocks, expiry scope and the existing shared replay context. That consumer must not reinterpret scenario values as realized history or a predicted price path.
