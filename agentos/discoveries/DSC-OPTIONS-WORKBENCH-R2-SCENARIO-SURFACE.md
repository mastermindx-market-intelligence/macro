---
key: OPTIONS-WORKBENCH-R2-SCENARIO-SURFACE
claim: >
  Options Workbench R2 now has a bounded typed conditional price-by-future-time
  Greek scenario producer plus JSON machine projection on Macro PR #7306 exact head
  60ba087f7c476fa8b7a564dd191e0f83a004ec8a. It is explicitly separate from
  observed replay history and from a price forecast, reuses the incumbent Greek
  kernel/exposure conventions, and carries source-clock/provenance assumptions.
  Exact-head fences are green; CI and independent review remain open.
falsifier: >
  Run `python3 -m pytest -q tests/test_options_scenario_surface.py`; the R2 candidate
  becomes invalid if that contract fails, or if #7306 silently fabricates observed
  history, predicts the scenario price path, reimplements the Greek/pricing kernel,
  inherits unknown OI/IV clocks from the market clock, serializes non-finite exposure
  values, collapses supported multiple gamma crossings to a single nearest flip, or
  fails its exact-head/current-main owner packs and review.
so_what: >
  Preserve this additive scenario contract as a distinct modeled product. Consume
  #7306 CI and independent review before any release. After accepted source semantics,
  add the Terminal consumer through existing Workbench/linked-pane owners; do not
  create a parallel collector, store, replay clock, calendar or pricing kernel.
kind: runtime
verified_at: 2026-09-18
verified_by: >
  Macro PR #7306 exact head 60ba087f7c476fa8b7a564dd191e0f83a004ec8a;
  implementation operation options-workbench-r2-scenario-surface-20260918-sol-001;
  exact-head scenario tests 11 passed; scenario + incumbent intraday-Greek/GEX pack
  46 passed / 0 failed; compileall and diff check pass; protected-main proof against
  fa085ebb0b2a0ca2b42c5f187b3cc1fd9f6723fb uses merge tree
  b1ef55678c9953b7f54567d617528e0dce5d2dcf and proof-only integrated candidate
  4abc9af2960bc416f0a220008da095fa69ddeb78 with the same 46/0 result; fences
  35336460139 SUCCESS; CI 35336460361 in progress; MastermindX1 requested for
  independent review; parent Terminal #603 is the governing product tracker.
scope:
  - options-intelligence
  - macro:engine/options_scenario_surface.py
  - macro:scripts/build_options_scenario_surface.py
  - terminal:options-workbench
confidence: verified
---

## Mission and authority

Parent Terminal #603 defines R2 as true conditional gamma/charm/vanna fields over
hypothetical price x future time, with expiry filtering, multiple zeros, snapshot-
consistent context and an explicit boundary between observed/restated/scenario data.
Chairman continuation authorized this next independent lane while R0 release carriers
remain frozen on their own gates.

Protected procedure:
`Mastermind@61a2ff79aba4e8a5685e779707ad5c4426cf5cc5`,
Skillpack 1.0.1 / bootstrap major 1.

Carrier:
`claude/options-workbench-r2-scenario-surface-20260918-sol-001`.

Current exact head:
`60ba087f7c476fa8b7a564dd191e0f83a004ec8a`.

Draft PR:
Macro #7306, `feat(options): add typed conditional Greek scenario surface`.

State: **BUILT_NOT_PROVEN / DRAFT / DO NOT MERGE**.

## Capability

`engine/options_scenario_surface.py` emits
`options.scenario_surface/v1` with product kind
`conditional_price_time_scenario`.

The v1 field:
- freezes the supplied contract/OI/IV snapshot and rolls only remaining time forward;
- evaluates GEX/VEX/CEX over an explicit scenario-price x future-time grid;
- reuses `engine.intraday_greeks.bs_greeks_vec` and the incumbent
  multiplier/pct-move/dealer-sign exposure conventions;
- excludes expired contracts at each future horizon;
- uses explicit null cells when no contract remains or an aggregate is numerically
  non-finite, preserving missingness instead of coercing to zero;
- keeps every grid-resolved gamma zero crossing rather than selecting only the nearest;
- supports explicit expiry scope and max-DTE filtering;
- carries separate market observation time, optional IV observation time and optional
  OI vintage; missing clocks remain null rather than borrowing another clock;
- exposes rates, dividend yield, multiplier and pct-move conventions in the payload.

The assumptions are explicit and bounded:
- fixed supplied OI snapshot;
- sticky-strike supplied IV in v1;
- deterministic time roll-forward from supplied `exp_years`;
- incumbent +call/-put assumption-signed dealer basis;
- scenario prices are an axis, not a predicted path;
- observed history is false.

Unsupported sticky-delta is rejected rather than silently approximated.

`scripts/build_options_scenario_surface.py` is a pure JSON machine projection over the
engine. It creates no scheduler, persistent store, publication keyspace or source owner.

## Evidence

The inherited first test was discriminating RED because
`engine.options_scenario_surface` did not exist.

Exact-head proof after implementation/self-review hardening:
- scenario contract: 11 passed;
- scenario + incumbent `test_intraday_greeks.py` + `test_gex_engine.py`: 46 passed;
- changed-source compileall: pass;
- `git diff --check`: pass.

Fresh protected-main compatibility:
- main: `fa085ebb0b2a0ca2b42c5f187b3cc1fd9f6723fb`;
- no protected movement on the material Greek/pricing/calendar/flow dependencies;
- conflict-free merge tree:
  `b1ef55678c9953b7f54567d617528e0dce5d2dcf`;
- proof-only integrated candidate:
  `4abc9af2960bc416f0a220008da095fa69ddeb78`;
- integrated owner pack: 46 passed / 0 failed;
- integrated compileall and diff check: pass.

Exact-head fences `35336460139` are SUCCESS. Exact-head CI `35336460361` is
running at the current checkpoint. `MastermindX1` is the requested independent
reviewer; no submitted review is claimed here.

## Boundaries / non-goals

This slice is not:
- observed strike-time history;
- a price-path forecast;
- measured MM/Firm/BD/Customer inventory;
- a new source collector or entitlement;
- a second Greek/pricing kernel;
- a new replay/freshness/cache/calendar/store plane;
- Terminal production acceptance;
- full #603 or Quanted parity.

The separate R0 Greek field-completeness denominator stays behind #7279 acceptance.
Adaptive/convergence-tested gamma-profile resolution remains on its incumbent R0 owner.

## Continuation

1. Consume #7306 exact-head CI and independent numerical/semantic review without
   rewriting the accepted contract gratuitously.
2. After accepted source semantics, build a bounded Terminal consumer using the
   existing Options Workbench/linked-pane and transport owners.
3. Prove the user journey in real browser EN/ZH and responsive layouts; scenario
   disclosure must remain visible and must not resemble observed replay.
4. Production/natural-market acceptance follows normal authorized release and remains
   distinct from green CI or synthetic fixture proof.
