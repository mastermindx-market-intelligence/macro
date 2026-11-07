# Explicit breadth acquisition: adjusted four-field archive

Source continuation over `c3cd9bb6256ae7ea5943d226691a9b290e475f9e` in the original
Macro #10780 carrier. Status: qualified source, not activated. This is part of the
pinned always-on migration; it does not create a new collector, retry owner,
calendar, writer, scheduler, selector or publication plane.

## Existing ownership and changed seam

`BreadthAdapter.acquire_adjusted_prices` now accepts captured membership, explicit
prior matrices, delisted exclusions, vendor aliases and an aware evaluation
instant. Explicit construction takes detached breadth/Yahoo configurations and
has no legacy cache pathname. Small-cap and mid-cap adapters inherit this seam.
Legacy construction, `fetch`, membership acquisition and cache writes remain with
their original adapters. An explicitly constructed instance refuses legacy fetch.

The captured fields are **adjusted close, high, low and volume**. This contract does
not claim to capture open. The provider call remains `auto_adjust=True` and
`group_by="column"`. The new path and legacy `_download_closes` share the incumbent
batch/retry implementation, including request options, exponential backoff and
inter-batch pause. The runtime path never consults `_last_extras`, writes caches,
seeds proxy symbols or reads configuration, files or the delisting ledger after
explicit inputs are supplied.

Request settings are frozen before the first request and reused for bounded
recovery. Evaluation derives one completed US target through `market_session`;
both the evaluation-local year and target year require that owner's verified
calendar coverage. In-progress rows after that target are excluded before span
and coverage construction. Vendor publication and first-availability clocks remain
explicitly unknown.

## Membership and qualification

Repair uses the existing canonical ticker/name transformations with captured
fixups and delisted exclusions. Its deduplication and exclusions precede the
existing active-population floors: **400 large-cap, 450 small-cap, 350 mid-cap**.
Runtime membership admits string identities/names and string or explicitly missing
scalar sectors; nested values refuse before provider access. Alias mappings are
captured only for requested canonical names, reject vendor collisions, use the
same 24-character bound as the capture decoder, and remap back to canonical keys.
A global inverse cannot rename an unrelated requested symbol.

Current qualification requires `ceil(active_members * 0.8)` active names with
observed target values in all four fields. A returned old observation, a prior-filled
target value, a departed/archive column, or an unresolved repair cannot satisfy
that count. Zero volume is retained as a legitimate observed value; missing volume
is not replaced by zero. The private result records repaired, unresolved, current
and departed members plus initial/accepted spans and requested vendor identities.

The configured moving-average/new-high windows determine the breadth history
requirement used to repair shallow histories. This is a breadth qualification;
it is **not** a blanket history minimum for new basket IPO members. No minimum
ETF-cycle history is imposed on this contract.

## Whole-archive and adjustment behavior

`lib.adjusted_price_capture` contains value-only validation and merge operations.
It detaches numeric matrices, preserves the union of dates and columns, and refuses
nonfinite/negative prices, negative volume, malformed dates, ambiguous symbols,
unsupported values and oversized matrices. Bounds are 50,000 rows, 5,000 columns,
and five million cells per field and union; these are engineering ceilings, not
claims about observed production maxima. No rolling deletion is applied to the
archive. A consumer must select the repaired active membership when computing
current breadth; retained departed columns are not an active universe.

A captured fresh span owns its nulls and omitted dates in every field. The merge
never uses old values to fill holes inside that span. Positive-price basis
comparisons reuse `store.compare_basis(strict=True)` for close, high and low with
the captured tolerance; this detects changes below the legacy split detector's
5% threshold without changing that legacy threshold. The existing recent
residual-seam scan is also reused.

Any missing, shallow, incomplete, uncomparable or adjustment-conflicting member
requires one bounded full-history recovery through the same downloader. A repair
must reach the target, preserve each field's prior non-null observation dates,
and meet the required number of jointly observed four-field sessions. A repaired
symbol replaces all four columns together. Thin, failed or incomplete repair
retains the **original prior** columns and remains unresolved; a partly refreshed
mixed-basis candidate is never represented as repaired. A full-history request
uses the same qualification without issuing a second recovery request.

## Proof

Command:

```text
python -m pytest -q tests/test_breadth_price_acquisition.py tests/test_breadth_constituents_repair.py tests/test_breadth_split_seam.py tests/test_breadth_updown.py tests/test_universe_split_seam.py tests/test_collector_freshness_disclosure.py tests/test_basket_index_recency_guard.py
```

Result: **114 passed, 14 warnings**, exit 0; `git diff --check` returned 0.
Log: `/tmp/mmx-breadth-capture-qualified-20261106.log`.

The focused checks cover no ambient reads/writes, detached policy/frames,
post-repair population floors, exact 80% target boundary, departed/stale prior
exclusion, small adjustment corrections, four-field replacement, failed/thin
recovery, observation-date preservation despite unchanged counts, joint history,
null/gap ownership, aliases, malformed provider shapes, completed-session cutoff,
zero volume, declared spans and pre-allocation bounds.

The literal legacy `_download_closes` method is frozen from the base source in
`tests/fixtures/base_breadth_download_c3cd.py`; method SHA-256
`ca8435027f01f41696ad391cb82319de3d889a6bf4eb2b6b598803667202d3a9`.
Controlled single/multiple-symbol, retry and absent-extras cases compare both
output and request/backoff events against that source. Counts overlap the earlier
51/110-test runs and must not be summed.

## Remaining product obligations

No actual provider freshness, private production generation, global ownership
transfer or browser result is claimed. The next source work is the existing
basket-extras acquisition seam and qualified private broad/member publication,
then the data-only basket handoff/action-board assembly and complete Sector
composition. Runtime lane wiring, source updater recovery/first-install fencing,
legacy writer drain and anti-downgrade, API/Terminal binding, CI capability-owner
policy resolution, protected release and authenticated beta acceptance remain
open. The wider 353-entry dashboard migration remains open.

The basket resolver already chooses later observed columns and lets extras win
same-date ties. A newly corrected primary series cannot silently be claimed as
the selected thematic series when retained extras win that tie. The extras seam
must reuse that resolver and qualify the actual chosen observations, while
preserving its deliberate partial-history support for recent IPOs.
