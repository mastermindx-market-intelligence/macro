# Sector member indices from captured inputs

Source baseline: `7885f75fc27877b5757fdafc860da6552a2f52bf`.
Status: source implementation; no runtime ownership or beta acceptance is implied.

## Existing calculation, explicit input boundary

`engine.basket_index.member_index_from_inputs` accepts detached membership, an
explicit calendar, actual close panels and optional actual volume. It calls the
same close-index kernel as `consolidated_candle`: current-membership masking,
forward fill, the incumbent five-bar stale-tail exit, daily live-set equal weights,
first-return level and cumulative missing-return behavior remain unchanged. The
legacy full-candle entry retains its original OHLC range, dollar-volume, modes,
point-in-time and alpha behavior.

The new entry requires three distinct members with actual closes on the supplied
calendar and at least 300 constructed, cleaned index observations. Three members
is an entry condition, not a new daily live-population threshold. A 300-row raw
price history normally produces only 299 returns and does not satisfy the gate.
The first constructed level retains the original first return; it is not rebased.

No loader, provider, config, store, cache, clock, publication or session-calendar
lookup runs inside the explicit index. Bounds and primitive values use the
existing acquisition limits. No missing open, high or low is invented. Absent
volume remains unavailable; present volume is not filled and only proves actual
positive-volume coverage of the endpoint live population.

## Named private-generation consumer

`CapturedBreadthMemberInputs.member_index_inputs` projects the already verified
thematic resolved panel. The final observed population session uses the existing
membership-mask owner with `pit=False`: ignore `added`, enforce `removed`. A later
price from an ineligible removed member cannot keep the population clock current.
Only a wholly unobserved suffix is clipped; interior gaps and historical columns
retain the existing calculation semantics.

Volume is attached only from the selected primary breadth group and only on dates
where that group's actual close equals the selected close. Extras-selected prices
and donated or mismatched price observations receive no borrowed volume. Returned
evidence separates the bundle session, actual eligible member observation session,
close source, volume source, unavailable volume and captured source basis.

`engine.sector_cycles.member_candle_from_captured_inputs` consumes that projection
and returns the existing `MemberIndexCandle` type. It withholds a current Sector
candle when the population observation session differs from the bundle session,
returning `member_population_session_mismatch` with the actual older date. General
historical explicit-index calculation and the legacy loader remain separate.

This binding covers the captured thematic membership only. A requested symbol
outside that resolved population is rejected as `uncaptured_member_index_population`,
even if the broader capture holds prices for it. Separately owned Nasdaq/Russell
amalgam membership still requires explicit capture and the existing resolver; absence
from a thematic projection must not be represented as absence from all price sources.

## Independent verification

`tests/fixtures/base_basket_index_7885.py` contains literal original calculation
functions from the baseline, not a delegation to the new kernel.

- Original `engine/basket_index.py` SHA256: `92cd14b8224a5444e05dfc79a41612b13fa74cb9d055ff6aa10f8d696abb3151`.
- Literal fixture SHA256: `8d0b5de11e37e538aad51a25da78ea00860de1795565a00b68ec1d6bc1443ec9`.
- Forty-eight complete legacy comparisons cover six tapes across eight mode,
  membership and alpha combinations. Six close-only comparisons use that same
  untouched baseline. Separate assertions cover the first-return denominator,
  actual 300-observation threshold, duplicate membership, missing fields, no ambient
  reads, detached outputs and typed Sector consumption.
- The actual temporary private publisher/read path feeds a 319-observation Sector
  member index with checkout reads forbidden. It verifies actual partial volume,
  source-close mismatch withholding, older population clocks, later tapes from
  removed members and the thematic/amalgam scope boundary.

The first affected run reported 201 passes and one Canadian fallback failure.
The identical failure was reproduced with the exact original basket-index and
Sector-cycle modules loaded from baseline in an isolated process: the synthetic
Canadian test implicitly required an absent production TSX reference parquet.
The test now supplies its own synthetic CA reference through the existing calendar
owner; all original MTF and no-fabricated-flow assertions remain unchanged.
Baseline diagnostic log: `/tmp/mmx-member-index-canada-baseline-20261106.log`,
SHA256 `af86d3a9ccbc642b201c1f63d23a5d55b8120b3d235b523224b747580a4913ab`.

Final affected proof: **204 passed, 6 pytest temporary-directory cleanup warnings**,
exit 0, 142.98 seconds; `git diff --check` exit 0. Log:
`/tmp/mmx-member-index-final-20261106.log`, SHA256
`0bcf1ae6f6bf7ba19e0fa129a0ee8e71d37ccc73f5d6fb7fc328c9835d6c8648`.
The gate covers explicit member inputs, broad/member generation, basket signals,
explicit Sector cycles and the existing index recency guard. The preceding 69-pass
and 201-pass runs overlap this result and are not additional independent totals.

## Remaining delivery obligations

The full producer still needs captured amalgam and sponsor holdings populations,
auxiliary inputs, pure Pulse/basket handoff and canonical board composition, then
one final coherent Sector publication. Legacy writers, updater recovery, CI release,
API installation, Terminal integration and authenticated source-to-screen proof
remain open. This source slice does not transfer production authority or establish
that providers have delivered a newer market observation.
