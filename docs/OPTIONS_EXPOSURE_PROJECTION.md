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
- `input_sha256`: the admitted owner's `exposure_input_digest(greeks, oi, asof,
  root)` over the exact consumed fields, before exclusions. The producer compares
  this with the actual loaded rows; a changed OI/Greek input refuses all values.
  Generating this hash alone does not qualify the inputs or their rights.
- `clocks`: `source_session`, `oi_report_date`, `option_observed_at`,
  `underlying_observed_at`, `greeks_available_at`, `oi_available_at`,
  `available_at` (source selection cutoff). `source_session` and `oi_report_date`
  are exact `YYYY-MM-DD` civil-date labels, not instants to coerce across zones.
  The observation/availability instants must include a timezone.
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
Exclusion reasons describe why qualification was withheld. A malformed input
identity invalidates the source population globally, so that source-level reason
takes precedence over individual Greek diagnostics; `population.invalid_rows`
separately counts the actual malformed inputs.
`economic_expiry_at` is retained only when all member terms agree on the instant.
Next-live and current-exchange-week selections require this clock; a date label
alone cannot establish whether a contract is still economically alive.

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
`cell_count` reports the entire candidate grid. `cells_status=complete` means
all candidate cells are serialized (not that their Greeks qualify). With no
owner context, the grid is withheld as `source_unqualified`, retaining population
counts and aggregate exclusion reasons. No cells are truncated. The existing
nightly publisher measures the entire GEX SSE event (legacy fields and attached
history included) against its unchanged 8 MiB ceiling with a 1 KiB control-frame
reserve. If necessary it withholds the whole optional projection as
`payload_limit`, preserving counts and aggregate qualification metadata. If the
legacy envelope still exceeds the budget, publication is suppressed to preserve
the last-good object. Neither withholding state is an empty book or permission
to promote legacy rows to qualified cells. A separately validated dated legacy
reference retains its own availability and explicit reference status.
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

The existing nightly CLI now accepts an explicit `--exposure-context /path/receipt.json`.
Its envelope is `{"schema":"options_hub.exposure_contexts/v1","roots":{"SPY":{...}}}`;
each entry includes `root` and the owner fields above. There is no default receipt
location, automatic enrollment or new store. Malformed envelopes stop before data
reads/publication. A receipt from a different root/session/input stays unqualified.
Use the existing `--roots SPY --date YYYY-MM-DD --no-publish --out <existing-safe-path>`
dry run first; this flag does not authorize publication, overwrite or source access.

Focused verification: `tests/test_options_exposure_projection.py`, plus existing
Options Hub/contract-v2/nightly-builder tests. Synthetic owner receipts exercise
the accepted and refusal paths; they are not real source or production evidence.


## Version 2 compact wire representation

The producer now emits `schema=options_hub.exposure_projection/v2` with
`cell_encoding=tuple-v1`. Source, clocks, input digest, aggregate metrics,
population, cell count and withholding status retain their previous meanings.
Only cell representation changes; values are neither rounded nor sampled.
Units, status names and identity strings are shared in explicit tables:

```text
metric_order = [gamma, vanna, charm]
metric_statuses = [unavailable, partial, complete_observed, complete_expected]
cell_fields = [expiry_index, strike, population_index, metrics, joint]
metric_fields = [expected, received, qualified, missing, status_index, net, gross,
  known_net, known_gross, qualified_population_index, call, put, exclusions]
joint_fields = [expected, received, qualified, missing, population_index,
  model_index, complete]
```

`expiry_terms` contains `[expiry,economic_expiry_at|null]` pairs. `population_ids`
contains the exact original 64-hex digests; `model_refs` contains exact model
references. Table indices are zero-based integers. A cell has the five fields
above; its `metrics` array has exactly three tuples in `metric_order`.
`metric_units` maps those metric names to their exact existing dollar units.
Each metric tuple has 13 fields and each joint tuple has seven. The joint
`model_index` is null when there is no common model. No table reference may be
coerced, truncated or used outside its table. The field arrays and encoding
version are serialized explicitly so unsupported shapes can be refused.

`expand_projection_cells` is the Python reference expansion, exercised by
lossless round-trip tests. Terminal validates untrusted v2 bytes and expands
them into the same in-memory metric/cell contract; older v1 reads remain a
consumer compatibility responsibility. No duplicate verbose cell array ships.

The native EOD Greek normalizer now retains raw `timestamp` and
`underlying_timestamp` columns when supplied, across order1/2/3 slicing. It
does not infer zones, underlying clocks, first availability or absent columns.
The exact input digest binds either raw clock when present, so changing its
observation invalidates an old receipt. Older rows without the columns retain
their prior digest shape and do not acquire retrospective clocks. Different raw
observation clocks survive full-row dedup; duplicate economic keys must remain
subject to the existing downstream qualification/refusal rule, never summed as
if they were separate contracts. No collector endpoint or service was activated.


## Raw-clock compatibility with dated legacy analytics

The qualified projection consumes the original native Greek/OI rows and their retained
raw clocks before any legacy view. Repeated contract keys remain ambiguous and
refuse qualification even when their numeric Greeks agree. The dated GEX, VEX,
and volatility calculations use the pre-clock normalized row equality: they
ignore the retained raw clock columns and collapse otherwise identical
rows as the original normalizer did. A second clock observation cannot multiply
a legacy contract exposure. No latest-observation selection, time-zone inference,
or qualification is created by this compatibility view.

The native OI normalizer also retains supplied raw `timestamp` text. It remains a
report observation rather than first availability, carries no invented timezone,
and enters the exact input digest when present. Missing columns remain absent.
Both GEX and VEX apply the same legacy row equality before merging OI, so a
repeated OI observation cannot multiply contract exposures.
