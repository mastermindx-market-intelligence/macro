# Crypto R4 comparison basis and asset workflows

Status: implemented and natively verified in the isolated PR #10901 candidate. This is a display and navigation change. Public-route replacement, model acceptance and release remain separate.

## Problem and resulting behavior

The asset producer computes relative change in an asset/BTC price ratio across 90 shared observation steps. The previous interface described this as a 90-day return and invited users to compare the same published horizon. The payload supplies neither each paired window's endpoints nor its Bitcoin price basis. Those calendar and common-window implications were unsupported.

R4 now uses **Asset/BTC ratio change** and **Price change**. A single bilingual **Comparison basis** disclosure explains the verified calculation rule and separately identifies the missing result metadata. Its collapsed summary says **Paired window not supplied**. The same server-rendered disclosure is reused in Markets, asset inspection and comparison.

Markets opens in the supplied asset order. Relative and price-change sorts remain explicit options, including existing `sort=relative` and `sort=return` links. These are orderings of reported values, not a certification that assets share equal comparison windows. The existing Leading Bitcoin filter retains the producer's state predicate; it is not silently redefined as a positive percentage filter.

A single **Compare all N assets** action opens the full snapshot cohort, including when search has filtered the list to zero results. Closing follows the existing origin/history rules and preserves unrelated parameters, including scenario horizon, chart window and filters.

No price, ratio, trend, risk, observation date or JSON contract is recomputed by this change.

## Current ownership

| Concern | Existing owner | This change |
|---|---|---|
| Asset and Bitcoin history selection | `engine/eth_state.py::build_states` and existing store | Unchanged. No additional provider or fetch path. |
| Relative measure | `_relative_state` → `_pct_change(ratio, 90)` | Unchanged numerical result and state thresholds. |
| Own-price measure | `_pct_change(asset, 30)` | Unchanged numerical result. |
| Asset contract publication | `scripts/build_crypto.py` → `crypto_asset_states.json` | Unchanged. |
| Schema/availability projection | `lib/crypto_intelligence_view.py::build_view` | Unchanged. Consumed existing `contracts.asset_states`, asset availability and null fields. |
| Candidate rendering | `scripts/build_crypto_intelligence_r4.py::render_view` | Existing renderer called with the exact retained view JSON. No `build()`, producer run or source refresh. |
| Visible wording and disclosure markup | Markets section of `templates/crypto_intelligence_r4.html.j2` | One bilingual markup owner; drawer instances clone it without its ID. |
| Routing, Close and history | Existing `state/update/open/close/apply` functions | Reused. No replacement router, return stack or local-storage record. |
| Shared navigation/settings | Existing shared theme/navigation code | Unchanged. Crypto's own dialog geometry avoids the underlying hover trigger. |

The producer's legacy `change_90d_pct` and `change_30d_pct` field names remain compatible. UI wording does not change their serialized names.

### What the calculation actually means

The asset producer normalizes dated prices, sorts them and removes duplicate dates. For the relative measure it joins asset and Bitcoin observations on their dates, drops unmatched rows, forms the asset/BTC price ratio and compares the latest ratio to the ratio 90 positions earlier. A usable result therefore requires 91 matched observations. Missing dates can make that interval exceed 90 calendar days.

The own-price calculation compares the latest asset observation with the observation 30 positions earlier. Its interval is likewise an observation-step interval; it is not certified as 30 calendar days by the published record.

The UI describes **91 as a calculation requirement**, not as an emitted per-asset count. It does not derive paired endpoints from `asset.as_of`, aggregate `asset_as_of`, chart dates, scenario horizons, asset-history coverage counts or the current clock. The chart's independently validated continuous daily segment and the 7/30-day research scenarios retain their existing terminology.

The source also selects the Bitcoin history independently of each asset's provider. An asset's coverage source does not establish the actual Bitcoin comparison source, execution venue or UTC close.

## Availability and recovery

| Observed input | User-facing result | Available action |
|---|---|---|
| Nonempty asset projection; filter matches some rows | Matching assets and shown/total count | Inspect an asset or compare the complete snapshot cohort. |
| Nonempty asset projection; filter matches zero rows | No matching assets | Reset filters or compare the complete cohort. |
| Accepted asset schema; zero projected asset rows | No assets in this snapshot | Data and coverage. No table scaffold or Reset control. |
| Missing or mismatched asset contract | Asset data unavailable | Data and coverage. No assertion of a known-empty source. |
| Requested asset absent from an accepted projection | Asset unavailable; this asset is not present in the snapshot | Data and coverage. |
| Requested asset cannot be resolved because the contract is unavailable | Asset unavailable; this snapshot could not provide asset readings | Data and coverage. |
| Asset exists, relative number is null | Unavailable for that measure; supplied history state remains visible | Keep price, structure, risk and asset inspection usable. |
| Reported relative number is zero | 0.0% | Preserve zero; do not treat it as absence. |

“Accepted” is the projection's schema check. It does not certify that every raw asset entry was valid; non-object records can be skipped before projection. Empty-state copy therefore describes this snapshot's displayable projection, not the whole market or every raw source record.

There is no synthesized Bitcoin zero row. If a future supplied Bitcoin record has a null relative value, the UI preserves null. A missing relative number does not erase useful own-asset evidence or authorize a leading/tracking/lagging state fabricated by the UI.

## Interaction and implementation details

### Stable list controls

All existing DOM hooks remain present in empty states, so initialization and locale updates do not encounter missing controls. Controls and scaffolds are hidden when they cannot help. Numeric and symbol sorting is performed on a copy of `data.assets`; the comparison collection and original payload retain their order and contents.

Rows are moved only when their target DOM order actually changes. An ordinary locale refresh therefore leaves a surviving asset button attached and focused.

Reset moves focus to the existing search field **before** hiding the recovery button. It then verifies that a focus callback has not changed the URL, language or active element. Only then does it clear `q`, `filter` and `sort`, using the existing replacement navigation. It yields to a newer destination rather than overwriting it.

### Disclosure reuse and locale continuity

`comparisonBasis()` clones the Markets disclosure, removes the outer ID, starts a newly opened drawer disclosure closed, and binds the cloned coverage button directly to the existing `open()` function. The dialog is a sibling of the main element, so its cloned action cannot rely on the main element's delegated click handler. The clone is passed as its own trigger; the original main-page opener remains the external return target.

The source disclosure contains no descendant IDs or native details grouping name. Its bilingual spans retain the existing language owner. Asset coverage text and the lack of supplied conditional levels live inside the disclosure rather than as generic direction-giving paragraphs above the useful measurements.

For a language change, the existing `apply()` path preserves disclosure state only when both the exact panel and rendered address still match, and the language actually changed. It restores reading position independently of whether the disclosure owned focus. If a cloned summary/action owned focus, the corresponding new control receives focus; the function returns immediately after that focus call so a synchronous callback can own a newer destination. Incoming unrelated navigation does not inherit the outgoing basis state.

Scroll anchoring is disabled only for drawers containing this disclosure, preventing the bilingual span swap from shifting the position before the existing render path captures it. No new observer, storage schema or per-entry history owner is introduced.

### Comparison matrix and pointer modes

The matrix retains native table semantics with scoped column/row headings. It shows every reported asset, preserves each asset's own observation date, and uses an accessible horizontal scroll region. The measure column remains visible during horizontal scrolling with an opaque panel background. Missing values remain explicit.

Narrow layouts use the full available width. On a touch-only device the drawer remains full-height. On a narrow fine-pointer desktop, the dialog starts below the shared navigation hover target. This prevents Close from disappearing under a stationary mouse and exposing the Settings popup, which could otherwise intercept the subsequent Compare click. The shared settings controller, classes, ARIA and hover behavior are unchanged.

## Build plan for the remaining paired-window receipt

This patch does **not** implement the proposed receipt pictured in Paper. The following work belongs to the existing asset-state producer and projection, not to the UI:

1. Have the existing history selector retain the actual Bitcoin input identity alongside the selected series. An asset's provider must not stand in for the benchmark provider.
2. Extend the existing relative calculation's return contract with a comparison receipt from the exact joined data used for that result. Candidate fields are window basis, requested step count, actual paired start/end, observations used, common observations available, benchmark identity/source/price basis and an explicit unavailability reason.
3. Keep existing percentage/state outputs byte- or value-equivalent for unchanged inputs. Do not quietly replace observation-step arithmetic with calendar reindexing, fill missing dates or select a second benchmark.
4. Preserve additive compatibility through `crypto_asset_states.json` and `build_view`. Legacy snapshots without the receipt must continue to show “Paired window not supplied.”
5. Validate each emitted receipt against the rows actually used. Test unequal asset dates, matched-date gaps, sufficient own history with insufficient shared history, provider fallback, zero/null results and unavailable inputs.
6. Only after that source proof should the proposed Paper receipt fields become implemented runtime UI. Cross-asset equal-window qualification requires matching, evidenced endpoints and compatible price bases; a common aggregate timestamp is insufficient.

The synthetic Paper examples such as 82/91 shared observations or 120 own-asset observations remain design fixtures. They must not be inserted into the current payload, reconstructed in JavaScript or presented as current readings.

## Validation and release boundary

**161 cases passed in one complete native run**: 39 contract cases and 122 browser cases, including all previous 86 browser cases plus 36 additions. Chrome 157.0.8103.39 exercised 123 fresh contexts and 129 pages with zero page errors, external requests or WebSockets.

The initial candidate returned 152 passed / 4 failed. Two failures were an incorrect End-key scroll assumption in the harness; two were real Settings hover interceptions. Additional native falsifiers showed locale scroll shifts. The final runtime fixes the pointer geometry and restores basis reading position; all 161 cases pass.

A final unchanged-runtime run passed eight focused/capture cases: six overlap the complete suite and two are visual readback cases. It uses the corrected first-visible-row pointer path and captures the comparison before keyboard scrolling. Thirteen final native crops were inspected across desktop/narrow, English/Chinese, fine-pointer/touch, asset/detail/empty states and a saved-case regression view.

Exact-parent falsifiers are retained: the original 27-case baseline, two corrected Reset-focus failures and two corrected pointer-hover failures. The first pointer baseline was confounded by row choice and new-title expectations; it is archived but is not counted as a hover reproduction. The original Reset baseline's duplicate-selector stop is likewise qualified.

Node syntax passes. Recorded source transformations invert to the exact parent. Thirteen other original inputs—including the view JSON, builder, projection, contract tests and shared assets—remain unchanged. Both saved HTML pages are exact outside Markets after normalizing the asset-version references. Template/served JS and CSS match. Runtime version: `d4393a5d0e55`.

The final narrow fine-pointer inset intentionally affects all R4 drawers. Prior saved-snapshot behavior remains covered by the passing suite; the previous phase's exact narrow geometry claim remains scoped to its earlier commit.

See [COMPARISON_VALIDATION.json](COMPARISON_VALIDATION.json), [comparison evidence](comparison) and [inspected captures](comparison/captures).

The source packet includes the exact input hashes, baseline and candidate results, source transforms, browser observations and inspected captures. Source publication remains on the existing draft PR #10901 branch. It does not inherit model, production, public-route, independent visual acceptance or merge/release authorization from the incumbent PR #9580.

## Source references

- Inspected producer: `engine/eth_state.py` at `7308f6d706777a49009437554dd35fe42ae163dd` (same producer blob as the incumbent), blob `481c04ad243c11abd8482a22b1845be1cd2a518d`.
- Projection and candidate parent: `7308f6d706777a49009437554dd35fe42ae163dd`.
- Retained view JSON SHA-256: `807839328e14080902df593408c9001d958b69be70d74d09fadbdc811d859401`.
- Source PR: https://github.com/mastermindx-market-intelligence/Macro/pull/10901
- Paper file: `01M6Y3F0NXNDPAKJMJGCAD759Z`, comparison study page `p-3-0`.
