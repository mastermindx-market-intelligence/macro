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


## Native evidence composition in the incumbent builder

`compose_native_exposure_context(greeks, oi, asof, root, context=owner_context)`
is called by `build_root`. No context means no opt-in or change to the dated
reference path. The existing owner-supplied input digest must still match the
exact selected rows. The context may include `contract_reference_observations`,
a list of exact retained successful `options_reference_capability_observation/v1`
responses from the existing reference probe. No provider request is made by this
composition. Existing full `contract_terms` can be combined with matching positive
reference evidence; conflicting economic identifiers or values refuse composition.
Late observations cannot move an explicit selection cutoff forward.

The reference adapter binds the response path, ticker, underlying, expiration,
strike and right. It maps supplied exercise style, shares per contract, extra
deliverables and correction only when actually present. A missing correction is
not zero. Share quantity is not used as a quotation multiplier. The raw omission
of additional deliverables remains recorded as omission; any rule-backed
interpretation must identify the applicable source contract, rather than infer
standardness from a symbol or absent adjustment memo. Authoritative product rules
may legitimately supply currency/quotation conventions when their applicability
is established; those facts need not all be duplicated by the reference provider.
Such independent evidence can be included in existing owner `contract_terms`.

Prospectively, the existing Theta CSV reader records successful complete history
Greek/OI responses in `_theta_acquisition`, a repeated JSON column in the same
normalized rows and Parquet files. Each record contains the actual configured
origin, endpoint, explicitly sent parameters, response-byte SHA256 and an aware
UTC receipt time. It records `availability_basis=collector_observed_known_by`
and `historical_first_availability_established=false`. No missing model version,
rate/dividend parameter or provider-release time is invented. No old file is
relabelled as newly collected. Identical evidence is decoded once per selected
batch; every selected row must carry valid matching root/endpoint/date evidence
before its acquisition time can be composed. Missing members stay unresolved.

The existing input digest binds this receipt text as well as the consumed data.
Legacy GEX/VEX/vol row equality ignores the additive provenance column, so a
second acquisition is not a second contract exposure. The composed known-by
clocks are conservative times for the actually captured batch, not historical
first availability or the provider's OI publication time. A content-derived
snapshot reference is generated only when both selected Greek and OI populations
carry matching complete acquisition evidence. Observation clocks, economic
expiry, deliverable, currency, multiplier, rights, Greek units and model/tenor
semantics are never invented to finish a receipt. The existing qualifier remains
unchanged and can still refuse incomplete composition.

This helper creates no collector, registry, store, endpoint, entitlement or Greek
engine. The current-day snapshot wrapper remains under its existing separate
clock/dedup contract; this history-response change does not silently alter it.

### Dated provider approximation (Gamma only)

An explicit context `kind: dated_provider_approximation` uses the unchanged v2
compact tuple representation, with a separate valuation profile:

```json
{"basis":"provider_eod_approximation","source_session":"YYYY-MM-DD","observation_clock":"session_only","methodology_ref":"https://www.thetadata.net/docs/Articles/Data-And-Requests/Option-Greeks.html","endpoint":"/v3/option/history/greeks/eod","requested_version":"1","serving_build":null,"tenor_policy":"provider_eod_whole_days_0dte_0.15"}
```

Its capabilities are exactly `dated_cells:true`, `instantaneous:false`,
`next_live:false`, `joint_scenario:false`, `repricing:false`,
`historical_pit:false`. Complete matching native Greek and OI acquisitions must
exist; the actual Greek request must specify version1. Existing raw units,
input digest, exact series terms, OI, numerical exclusions and denominator
rules still apply. Source session/report date and aware acquisition known-by
clocks are required. Option/underlying observation instants may be null; an
expiration date is sufficient for this dated class. Missing or later-than-cutoff
capture evidence refuses qualification. It never grants instantaneous/final-hour
interpretation, next-live, joint scenarios or repricing. Vanna/Charm always remain
unavailable, including zero-OI rows, and joint.complete is always false.
The original modeled_exposure class retains all its original clock, economic
expiry and no-floor provenance guards. Rights remain the incumbent separate
pass-through decision; computing a number creates no display/export/save grant.

The optional explicit `term_policy: occ_standard_spy_etf/v1` applies only to
matched SPY reference observations with100shares, American exercise and no
additional deliverables reported. It uses Massive's documented conditional
additional_underlyings semantics and OCC ETF premium-quotation rules. Raw
omissions remain omitted, with interpretation/citations retained separately;
correction does not default to0. Other/adjusted terms remain unsupported.
Exact reference-list observations retain their actual list route/query/digest;
individual rows are not relabeled as separately requested overview responses.

Bounded history calls accept an explicit shared BoundedRequestBudget plus
strike_range<=5 and byte/row caps. They require one expiry/session, skip the
extra health GET, disable redirects and reject retry-enabled adapters. The
reference adapter has a matching bounded contracts-list mode with no next_url
follow. Its maximum budget is three GET attempts, including failed attempts;
refusals, transport uncertainty and cap failures close the budget. Normal
legacy calls retain their existing behavior. Additive receipt construction
failure preserves valid legacy rows and withholds only their new provenance.

### Scoped dated canonical identity

The existing composition interface optionally accepts in-process
`dated_identity_inputs`: captured `IdentityArtifactRead` values for the parsed
Massive reference observation, native security master, native listing snapshot
and its original completion receipt, plus an explicit `decision_at`. It invokes
`engine.intelligence_workspace.options_contract_identity.resolve_dated_spy_contract_identity`.
No path reopening, remote request, alias publication or identifier mint occurs.
The selected Greek/OI keys must match one bounded SPY expiry and exact reference
contracts with the requested historical `as_of`. Adjusted/unknown series refuse.
The canonical target validator is shared with the existing Options-root reader.

The resulting `contract_identity` is retained in the JSON context/projection:
`schema: options.dated_contract_identity/v1`, `scope: selected_contracts`, exact
root/session/contract keys, input digest, canonical target/listing, evidence
artifact digests, one-day effective interval and actual `known_at`.
`root_alias_created` and `historical_first_availability_established` are false.
A current canonical target plus its validated historical listing support is
combined with the actual historical reference observation; the listing is not
relabeled a fresh observation. The parsed-reference artifact digest binds its
exact retained representation. The separately retained HTTP-response digest is
not a claim that this artifact is the original raw HTTP body or authenticated by
an unkeyed hash.

The existing builder can replay a composed JSON context. Producer consumption
rechecks its seal, input digest, root/session, cutoff and selected keys. Added
actual inputs invalidate the binding; expected-but-unbound keys remain missing.
The receipt cannot authorize `modeled_exposure`, next-live, joint/repricing or
any market-wide/root-wide identity claim. It leaves the original October15
root-alias seal and all native registry files unchanged. New underlying symbols,
wider populations and historical PIT eligibility require their own source proof.

### Native nightly/publication bridge for the selected capture

The existing `--exposure-context` envelope can additionally declare per root:

```json
{"source_inputs":{"schema":"options_hub.projection_inputs/v1","greeks":"captured-greeks.parquet","oi":"captured-oi.parquet"}}
```

These are explicit sibling basenames, not path discovery or another store. Each
regular non-symlink file is bounded to1MiB,64rows,64columns and2MiB decoded
Parquet row-group data. The captured pair must match the context input digest
and carry the existing scoped dated identity. Bad/missing descriptors refuse
before any new publication; existing outputs are not removed. File-read custody
has the incumbent reader's limitations and is not an atomic filesystem snapshot.

`build_root` composes that exact projection pair and passes it to the incumbent
`compute_gex`; all legacy calculations continue to consume their original full
store frames. Projection failure or unavailability cannot replace legacy frames
with the selected window. A selected context from another source session is
withheld with `exposure_projection_input.state: withheld_source_session_mismatch`
and the normal legacy projection/reference path is retained. The metadata names
both selected and legacy sessions and the per-contract captured-spot basis.

Dated projections also expose `underlying_reference` with `source_session`,
`currency: USD`, `instantaneous:false` and either the exact uniform positive
captured underlying price (`basis: uniform_selected_contract_underlying_price`)
or a null value (`basis: nonuniform_or_missing_selected_underlying_prices`). It
is a dated display reference; exposure arithmetic continues to use each contract's
own raw source price. Legacy spot_ref remains unchanged, including null when the
retained legacy source is absent. Qualified consumers must not substitute legacy
spot for a missing selected-source reference.

After normal source installation and publication-input custody checks, the
existing native builder can validate the admitted context bundle with explicit
`--roots SPY --date 2026-10-19 --exposure-context <bundle> --no-publish --out <candidate>`.
The ordinary `--publish` path remains the only publication effect; this source
change creates no service, schedule, endpoint, store, automatic probe or activation.

### Explicit full observed-root acquisition

`collectors.thetadata.bounded_observed_root_history(root, day, kind, request_budget=...,
max_bytes=..., max_rows=..., version=...)` makes a single native history GET for
SPY or QQQ, with wildcard expiry and both rights. `kind` is `greeks` or `oi`;
Greeks require explicit version `1`, while OI accepts no model version. The
caller must supply actual response limits, bounded above by 16 MiB and 100,000
raw rows. There is no health request, retry, concurrent window or pagination.
Every successful normalized row retains the acquisition receipt. Refusal,
truncation or parse/limit failure closes that same request budget. This method
does not write the incumbent store, qualify terms/identity, grant rights or
claim full-market completeness. A 14,000-row synthetic multi-expiry acquisition
tests the larger population independently of the unchanged selected-expiry caps.

The installed daily owner deliberately maintains prior-session Greeks/EOD and
current-session OI. Its next normal session run advances that source frontier.
An explicit catch-up remains a separately bounded effect through the incumbent
writer lock and atomic merge; neither this helper nor a projection context
waives those controls or permits a selected capture to replace a full book.


### Full declared observed population and paged exact reference

The optional dated identity v2 receipt (`options.dated_contract_identity/v2`,
`scope: observed_contracts`) binds the entire Greek/OI coordinate union, with
multiple expiries, through the existing native identity owner. The selected v1
receipt and exposure v2 tuple arrays are unchanged. The v2 adapter currently
supports SPY's captured canonical target and the admitted QQQ native target
`SEC:US-XNAS-QQQ` / `US-XNAS-QQQ`. QQQ's completed listing uses normalized
`exchange: NASDAQ`; its canonical effective date is October20,2026. That current
intake cannot bind October16/19 option populations. Both roots require actual
captured canonical/listing evidence, exact matching reference series and native
acquisition/retained-input receipts. The SPY-only selected v1 path is unchanged.
`observed_contract_keys` is the unique full pre-exclusion union (at most100000
members/50000 expiry-strike cells). `contract_keys` is its uniquely exact-reference
bound subset, possibly empty. Omitted or ambiguous reference series remain in the
observed denominator. Adjusted/unknown terms still withhold the dependent metric,
including when OI is zero. No general root alias or PIT grant is created.

The receipt retains exact source session/effective day, actual maximum known-by
clock, semantic input digest, canonical master/listing artifact digests, and
`reference_observation_sha256` of the captured parsed population manifest.
`reference_pages` contains each actual sanitized `params`, raw `response_sha256`,
`completed_at`, `response_bytes` and `contracts` count. These are separate raw-page
hashes; the parsed manifest is not relabeled one raw response. Page0 fixes exact
root/as_of/minimum-expiry selection, later pages retain opaque cursors with only
matching optional scope echoes. Queries and cursors are unique. A complete crawl
has at least one page, even for an empty result, and its bound members cannot
exceed actual reference row counts. Incomplete/capped manifests cannot bind a book.

The existing RestProber's explicit `reference_population` profile allows at most
20GET/pages,20000 reference rows,8MiB total and1MiB/1000rows per page, with15-second
minimum pacing and no retry or redirect. Same-origin HTTPS links are pinned to
the exact contracts-list route, rejecting userinfo, explicit ports, scope changes,
duplicate query keys and malformed cursors. Reflected API keys are discarded.
Only an absent/null next link establishes completion; any malformed value closes
the request budget. The original selected-expiry caps and default probes remain
unchanged. No crawler runs without an explicit bounded caller.

`source_evidence_basis: native_acquisition` uses actual whole-root acquisition
receipts and no artifact pair. `retained_native_store_read` requires exact Greek/OI
Parquet hashes and actual read clocks, checked before decoding against100000 rows,
64columns and128MiB decoded metadata per input. Retained reads establish possession
now, never original endpoint/model version/provider publication or historical
availability. They cannot qualify old numerical rows without separate real evidence.
Both routes preserve the full observed denominator. Per-cell metric/joint qualified
counts cannot exceed its bound reference members; `qualified + missing` sums to the
observed union. `expected` remains null for unknown full-market coverage, while
`received` reports actual metric receipts. Incomplete totals keep gross/net null and
retain explicitly partial known amounts. Full books use normal stored frames, not
the selected source-input descriptor, and remain subject to the existing whole-event
8MiB guard without truncation or partial latest-book replacement.

### Prospective native daily version selection

`bulk_greeks(..., expiration=0, version="1")` now forwards the explicit version to
every native wildcard day window. Omitting it preserves the provider/default
request. After protected installation through the existing dirty-source integration
owner, setting `THETADATA_DATED_GREEKS_V1_ROOTS=SPY,QQQ` in the incumbent daily process
environment selects version1 only for those roots, in both daily and explicit-root
top-up paths. The default is empty; unsupported roots refuse before acquisition.
The installed daily wrapper/service need not change scheduling or writer locks.
Existing stored rows are not reacquired/upgraded by this option, and a previous
unknown HTTP effect is not retried. Terms, canonical identity, actual receipt clocks
and remaining qualification controls still apply independently.

### Scoped archive-only projection repair

The existing `scripts.repair_gex_history` owner accepts explicit `--roots`,
`--date` and `--exposure-context` for an existing dated archive. Without `--apply`
it is a dry run. The receipt must bind the exact full native-store Greek/OI rows;
selected `source_inputs` are rejected. Expiration representation is retained as
read by the native builder so the original semantic input digest remains valid.
Wrong root/session/digest refuses before a replacement write.

```sh
python -m scripts.repair_gex_history --roots SPY --date 2026-10-16 \
  --theta-store <incumbent-store> --exposure-context <owner-bundle>
```

The repaired archive retains `history`, updates the fields owned by `compute_gex`
including the optional `exposure_projection`, and applies the existing whole-event
8MiB transport budget. It never writes `gex/{ROOT}.json`, vol or current boards.
A genuinely empty or over-budget legacy envelope retains its last-good archive.
Maintenance without an explicit owner context also preserves existing dated/modeled
projections, rather than erasing their qualification with an unavailable substitute.
The explicit-context path rejects changed input digests instead of silently
publishing a numerically unavailable substitute.

Only after ordinary writer custody and actual distribution rights are established,
`--apply --publish` uploads the changed exact dated keys. The existing
`publish_gex_history_index` then lists the actual plane and updates `dates.json`
with `heal_budget=0`; unsuccessful uploads do not create invented index members or
trigger unrelated heals. This option is not a rights grant or service activation.
The retained October16 SPY dry run and isolated evidence-copy application preserve
13104 observed /12212 qualified /892 missing,6552 cells in a3994690-byte JSON
artifact. No production archive or current book was changed for that verification.

The QQQ observed-v2 extension uses the same field and tuple layout as SPY, with
explicit root-specific policy `occ_standard_qqq_etf/v1`. It interprets only exact
100-share American QQQ reference contracts with no additional deliverables reported,
retaining raw omission and Massive/OCC citations. Currency/multiplier/deliverable
interpretation does not establish an economic expiry instant, serving model build,
dividend schedule, provider Greek units beyond the admitted dated Gamma class, or
historical first availability. All existing instantaneous/joint/repricing/PIT guards
remain in force. Synthetic QQQ producer output is a contract test, not actual QQQ
market capture or publication.

### Prospective native snapshot provenance

The existing snapshot wrapper retains the same `thetadata.acquisition/v1`
receipt column for first-order Greeks, second-order Greeks and OI snapshots.
This is actual endpoint/parameters/raw-body hash/collector received time; no source
session, provider publication instant, historical availability or rights is inferred.
The history-only numerical receipt reader continues to refuse snapshot endpoints.
`native_snapshot_acquisitions` validates every row's receipt, requested root/scope,
endpoint and known-by cutoff, decoding identical repeated evidence once.

The native snapshot normalizer now retains original `timestamp` and
`underlying_timestamp` text alongside the existing parsed `snapshot_ts`. Missing
underlying clocks remain absent. The existing exact contract-plus-snapshot-time
join preserves first-order evidence and separately names second-order evidence:
`second_order_timestamp`, `second_order_underlying_timestamp`,
`_theta_second_acquisition`, `second_order_underlying_price`,
`second_order_implied_vol`, `second_order_iv_error`, `second_order_bid`, and
`second_order_ask`. Missing or mismatched second-order observations cannot acquire
another row's provenance; first-order values are not overwritten.

`snapshot_greeks(..., version=None)` preserves existing request defaults and records
an omitted requested version as unknown. Explicit `version="1"` or `"latest"` is
forwarded only when the caller supplies it. The source receipt's
`calculation_provenance` labels its basis as requested parameters plus endpoint
documentation, retains a null serving build, and discloses the corresponding
0DTE0.15-day or latest minimum-one-hour floor. It never relabels either as
`economic_expiry_no_floor`. Official source pages:
[first order](https://www.thetadata.net/docs/operations/option_snapshot_greeks_first_order.html),
[second order](https://www.thetadata.net/docs/operations/option_snapshot_greeks_second_order.html).
The current code does not activate the optional version or make any source request.

Provenance failure is lane-local: valid legacy CSV rows survive with the acquisition
receipt omitted, including removal of any untrusted same-named response column.
Unsupported Vanna/Charm units, serving model identity and economic/model horizon
remain unavailable. Q02's American reference remains `RESEARCH_ONLY`; physical
delivery, reference-close marking, last trade, exercise election and model horizon
must not be conflated. This adapter does not qualify instantaneous exposure or
change any projection capabilities, poller schedule, store or publication right.

Admission hardening preserves any explicit conflicting currency, multiplier or
deliverable rather than overwriting it with an ordinary-ETF interpretation. Rule
interpretation accepts only mapped exact HTTPS reference origin/path/hash; source
origin and coordinate provenance still come from the checked reference chain, not
from a URL string alone. QQQ's Oct20 lower bound is enforced both when resolving and
when validating a receipt. OI is not Greek algorithm-versioned: an explicit unsupported
version parameter withholds its acquisition evidence; no version1 is invented for OI.
These guards preserve observed denominators and do not change v2 tuple fields.
