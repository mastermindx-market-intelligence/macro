# Event hedging research: deterministic diagnostics and paired evaluation

This is a bounded research extension of the existing Options scenario producer and Options workspace. It is not a live dealer-inventory monitor, a new market-data service, a calibrated directional model or trading authority. Parent: Macro #7925. Full delivery plan: `research/options_intelligence/2026-10-03/EVENT_HEDGING_DELIVERY_2026-11-04.md`.

## What is usable in this source slice

1. Matched-window event-variance diagnostics against an explicitly supplied counterfactual.
2. Remaining hedge-target change along two compatible endpoints from the existing whole-book SPX/SPXW repricing owner.
3. Paired first-touch forecast scoring using existing multiclass loss functions, with missingness and event clustering retained.
4. Explicit-input CLI modes and a display-only, bilingual research panel in the existing Options workspace.

There is no automatic collector, scheduler, event-resolution inference, publication, probability fitting, order execution or portfolio influence. Input references and content hashes identify supplied evidence but do not independently authenticate it. A valid calculation does not certify the input source, event causality or forecasting skill.

## Existing command interface

All analytical modes use the incumbent command and write to stdout by default:

```bash
python -m scripts.build_options_scenario_surface --mode event-variance --input variance-request.json
python -m scripts.build_options_scenario_surface --mode hedge-path --input paired-endpoints.json
python -m scripts.build_options_scenario_surface --mode event-scorecard --input paired-forecasts.json
```

Use `--input -` for stdin and `--output PATH` for an explicit local output. The existing `surface` and `hedge-target` modes retain their semantics. Duplicate JSON members and nonfinite constants are refused.

To inspect a variance or hedge-path artifact in the existing page renderer:

```bash
python -m scripts.build_options_command \
  --event-hedging-input research-artifact.json \
  --out /tmp/options-event-research.html
```

The input option is explicit and local. Normal scheduled builds do not acquire an event-hedging feed or show the panel unless a caller supplies an artifact. `render(..., event_hedging=artifact, now=aware_datetime)` is the same in-memory integration path used by the tests. The renderer verifies the artifact hash and non-authoritative contract, then formats values without recalculating the model. The panel is labeled a recorded research snapshot, never live flow. A caller remains responsible for any display/export entitlement.

## Matched event variance

`engine.event_hedging_diagnostics.build_event_variance_diagnostic` accepts the selected event identity/time/known-at/source, decision clock, observed variance receipt, counterfactual receipt, overlap evidence and an explicit freshness limit.

Each variance receipt declares `security_id`, `window_start`, `window_end`, `variance_basis`, `return_basis`, `unit`, `method_ref`, `value`, `source_ref`, `source_revision`, `observed_at` and `known_at`. Both receipts must share the instrument, exact window, valuation clock, variance basis and return basis. Observation precedes availability, which cannot exceed the decision. The selected event remains ahead of the decision and inside the priced window.

Supported variance bases are `risk_neutral_integrated_variance` and the explicitly weaker `atm_iv_squared_time_proxy`. Return basis is `log_return` or `simple_return`. Values are integrated variance in `return_decimal_squared`, not annualized volatility or vol points.

The arithmetic is observed variance minus the counterfactual. Negative differences remain negative and are flagged. The isolated-event value is withheld unless overlap coverage is explicitly complete and the supplied overlap list is empty. Even then, isolation is conditional on the supplied baseline and coverage; it is not an identified causal effect. The square root, multiplied by 100, is an RMS move scale, not expected absolute return, physical probability, direction or price target.

No model-free option-surface integration or term interpolation is invented here. Qualified variance observations and counterfactual generation remain upstream work.

## Conditional remaining hedge target

`compare_hedge_path_targets` consumes two hash-verified `options.hedge_target_change/v1` outputs from the existing `build_hedge_target_change` owner, plus a caller-supplied path reference. It requires complete and comparable source, universe, anchor book, initial inventory, pricing assumptions and decision clocks, with an ordered future checkpoint and terminal endpoint.

Remaining adjustment is terminal hedge-target change minus checkpoint hedge-target change, in SPX index-equivalent risk units. Reference notional is the terminal SPX level times that remaining adjustment. It is not the difference between two dollar-marked books, executable shares, ES contracts, actual executed volume or path turnover.

Endpoint spot, IV and ending inventory may differ along the caller's assumed path. This supports sensitivity research without pretending that an actual dealer has followed that path. Unknown/incomplete endpoints or incompatible anchors remain unavailable. Actual exhaustion probability stays null.

## Forecast evaluation without a new model or ledger

`engine.event_hedging_evaluation.score_event_hedging_forecasts` accepts a declared registration and complete eligible-origin roster, paired issued forecast receipts and owner-produced outcome receipts. Only the generic `brier_score` and `mean_log_loss` functions are reused from `engine.k3e_eval1_forward`; that module's 21-session study identity and promotion law do not apply to these intraday targets.

The class order is `UPPER_FIRST`, `LOWER_FIRST`, `NEITHER`. Horizons are distinct continuous 30-, 60- and 120-minute research strata. Actual session eligibility, barriers, bar completeness and same-bar ambiguity remain responsibilities of the existing outcome owner; a path reference alone is not exchange-calendar proof.

The scorecard requires registration before the test interval, feature and training-label availability before issuance, issuance by the decision, exact target duration, mature outcomes and no declared event overlap between model development and evaluation. Missing records, abstentions and pending/censored outcomes stay in the denominator. Censoring never becomes `NEITHER`.

Both row-weighted and equal-event-weighted scores are reported. Many minute observations around one event are not many independent events. A zero probability for the realized class gives an explicitly infinite log-loss state rather than a flattering clipped value. No significance, calibration certificate, prospective-validation claim or promotion follows from the scorecard.

The initial source includes only synthetic metric/conformance tests. No market-performance result is claimed.

## Verification and current gaps

The focused source run completed with **783 passed, 5 skipped** across the new suites and incumbent numerical/Options consumer suites. Skips are retained rather than converted to passes. The real Options template was exercised in a local Chromium browser at 1440px and 390px, in EN and ZH, with source-details interaction and no panel overflow. Those inputs are explicitly synthetic; this is not installed or live-market proof.

`reports/event_hedging_20261104/` retains synthetic inputs/results, local browser evidence and the source-separation receipt. No licensed quote corpus is included.

Still required for the complete mission: event-to-scenario composition (original EH1 worker reservation), qualified current source/contract clocks, event-surface premium estimation, inventory uncertainty, current machine/Terminal integration, registered real-data forecasts and outcomes, protected release, installation and actual source-to-user proof. No added component creates ranking, sizing, trading, automatic exits or live-alert authority.
