# Options Hub qualified exposure projection

`options_hub.gex/v1.exposure_projection` is an additive, dollar-valued joint
strike × expiration projection produced by `compute_gex`. Legacy headline,
profile and marginal meanings remain their existing contract. The nightly
`build_root` threads an optional `exposure_context` owner receipt to that call.
There is no new endpoint, persistence store, collector or Greek calculation.

The projection consumes the union of the selected session's original Greek and
OI keys, plus supplied expected keys, **before** positive-OI or IV exclusions.
The tuple `(root, expiration, strike, right)` joins provider rows; the owner must
bind it to exact economic series terms. A duplicate key refuses its exposure
rather than multiplying rows in an OI join. A foreign root or malformed identity
is recorded and prevents complete qualified totals. Missing OI stays missing.
An observed integer OI zero qualifies exposure zero without requiring a Greek or
spot, once its source and economic series have qualified.

## Calling the existing producer

```python
payload = compute_gex(greeks_asof, oi_report_asof, asof, root,
                      exposure_context=owner_receipt)
# Or use the existing nightly composition:
vol, gex, vex = build_root(root, asof, theta_store,
                           exposure_context=owner_receipt)
```

The context is a JSON-compatible existing-owner receipt with these fields:

- `source_snapshot_ref`: immutable source reference for the actual rows, and
  `security_id`: exact underlying binding. A row key alone does not prove it.
- `clocks`: `source_session`, `oi_report_date`, `option_observed_at`,
  `underlying_observed_at`, `greeks_available_at`, `oi_available_at`,
  `available_at` (source selection cutoff). Instants must include a timezone.
  Observation dates must match the selected New York source session; no input
  availability may exceed the cutoff. Greek availability cannot predate its
  observation. `oi_position_session`, `published_at`, `correction_ref` may be
  null and remain null. The existing asof OI report already represents previous
  close positions: this projection performs **no second shift**. It never
  fabricates a per-contract first-known time from an EOD date.
- `contract_terms`: records with `root`, `expiration`, `strike`, `right`,
  `series_id`, `security_id`, `terms_ref`, `deliverable_ref`, `available_at`,
  `currency`, `multiplier`, `deliverable`, `economic_expiry_at`,
  `exercise_style`, optional `discrete_dividend_before_expiry`.
  Terms must have been available by the cutoff. `series_id` cannot bind multiple
  keys. This v1 admits only positively sourced USD `100_underlying_shares` with
  multiplier 100, the domain of the incumbent exposure arithmetic. Missing,
  adjusted, cash-settled, or other terms remain unavailable; absence of an OCC
  adjustment memo does not qualify standardness. Economic expiry must have the
  exact series' New York expiration date and follow the Greek observation.
- `greek_provenance`: keyed by `gamma`, `vanna`, `charm`, each with `source_ref`
  equal to the snapshot reference, nonempty `model_ref`, `method`, `unit`, and
  `tenor_policy="economic_expiry_no_floor"`. Supported methods are
  `provider_observed` and `engine.intraday_greeks`; the latter also passes the
  existing `kernel_applicability` rule using the exact seconds to economic
  expiry. American puts, American calls with an unknown/intervening dividend,
  expired contracts and sub-minute model clocks retain the owner's refusals.
  This module consumes provided Greeks; it does not calculate missing values.
- `expected_contracts`: optional list of exact provider row keys for the declared
  population. Without that owner-supplied membership the denominator is unknown.
  Unexpected observed keys or invalid/duplicate expected keys invalidate the
  supplied expected denominator and are disclosed. `rights_decision_ref` is
  passed through; calculating exposure does not mint display/export/save rights.

Raw unit strings are exactly `delta_per_underlying_price_unit` for Gamma,
`delta_per_1.00_vol` for Vanna, and `delta_per_elapsed_calendar_year` for Charm.
The latter means elapsed-time drift, not derivative with respect to remaining
maturity. Missing provenance, floor-based tenors and unknown units never qualify
positive-OI exposures. A finite feed Gamma needs no fallback IV; a present
sub-floor IV is a degenerate quote and remains an exclusion. A missing Greek is
never replaced by zero or by Matrix's median/default-IV or tenor sentinel.

## Consumer semantics

Every cell exposes `gamma`, `vanna`, `charm` summaries. Each metric has
`expected` (null unless membership is supplied), `received` (unique Greek rows),
`qualified`, `missing` (known member keys lacking qualification), `exclusions`,
`call`, `put`, `net`, `gross`, `known_net`, `known_gross`,
`qualified_population_id`, `status`, and its exact output unit.

`net`/`gross` require all member keys and both sides to be known. An absent side
is unknown for an observed-only population; supplied expected membership can
positively establish an empty side with contribution zero. `known_*` are
qualified-subset sums and are null when no member qualifies. Genuine arithmetic
cancellation remains numeric zero. Gross is the sum of absolute **contract**
exposures, never absolute net. No rounding or million/billion scaling is applied.

The output units are USD delta per +1% spot (Gamma), per +1 vol point (Vanna),
and per +1 elapsed calendar day (Charm). All arithmetic delegates to
`engine.exposure_math.dealer_exposures`, once. Its assumed dealer position is
long call / short put; it is not measured inventory. With dollar-valued fields,
local hedge demand is `-(G*spot_percent + V*iv_vol_points + C*calendar_days)`.
20% to 21% IV is one point. A nonzero shock may not use an unavailable term.

`joint.complete` requires all three metrics for the exact cell member set, both
known sides, the same source and one common model reference. Disjoint metric
subsets do not create a Combined value. Per-metric qualified membership digests
also let a consumer compare the exact intersection for a smaller nonzero shock
set; check both membership and model/source provenance. No calibrated probability
or nonlinear scenario qualification is implied.

Population scope is `observed_population` or `supplied_expected_population`.
Even complete supplied membership is **not** full-market coverage:
`full_universe_expected` stays null and `full_universe_complete` stays false.
Counts and digests are independent of viewport/legacy marginal windowing.
Correction/source identity changes alter the membership digest. A historical
source keeps its historical session and expiry, regardless of viewing time.

## Current integration limit

The existing EOD loader does not supply exact per-series terms, model/unit/tenor
receipts or all first-availability clocks. Therefore the normal producer now
emits explicit unavailable qualification and counts, with `net`/`gross` null,
until its incumbent source owner supplies those existing receipts through
`exposure_context`. This source change is not evidence of a new live snapshot,
publication, rights admission, final-hour qualification, or product acceptance.
The projection must not be populated from Matrix net marginals, unsigned Matrix
Vanna, a generic 100-share assumption, or held research branches.

Focused verification: `tests/test_options_exposure_projection.py`, plus existing
Options Hub/contract-v2/nightly-builder tests. Synthetic owner receipts exercise
the accepted and refusal paths; they are not real source or production evidence.
