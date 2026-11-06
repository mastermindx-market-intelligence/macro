# Ordering diagnostics independent review

Operation: `MMX-CN-PROPHET-CENSUS-REVIEW-ORDERING-20261009`  
Reviewer: native child `/root/pipeline_census`  
Final verdict: **PASS — requested arithmetic correction verified; no outstanding material changes.**

The central coverage diagnosis, frozen-public 4/24 shortlist-overlap result, corrected component-ablation calculation and explicit public/candidate coherence receipt pass this bounded review. Qualification, historical performance and deployment remain outside this operation's acceptance scope.

## Reviewed identities and access boundary

- Macro source pin: `3d90aad6d83152dfeeaf8345bc995826ac9d3139`.
- Accepted parent script: `deliverable/research/cn_prophet_audit/census_20261009/ordering_diagnostics.py`, SHA256 `e9b0a0cdb2ad8e831b5071ab831ffddeb6dc0884bf2037ff1be7a16efb731368`.
- Accepted parent result: `ordering_diagnostics.json`, SHA256 `527ece9b344c34d64d184ff5fb67dbaafbe6efe557b794b03b08a908b03dde86`.
- Independent candidate subset: `historical_autopsy/last_cap_qualified_rows.json`, SHA256 `78f1a1658bc6a0960c8e0479394ced5a63d20d76e6afd1b5d4677e461be30381`.

Only local source inspection and isolated in-memory calculations were used for this review. The reviewer did not invoke the host, mutate the parent script, write a canonical repository, or access production. The parent supplied the successful host execution result; the reviewer independently reran the extracted source controls and candidate-subset sensitivity locally.

## Resolved correction

The first reviewed script sorted component ablations by `prophet_score - removed_points`, where `prophet_score` was already rounded to two decimal places and component points retained four decimals. This differed from the pinned score arithmetic. The source first sums the component points, clips to 0–100, then rounds the total to two decimals: [engine/china_board_rank.py, lines 902–906](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_board_rank.py#L902-L906). The source then sorts that rounded score and ticker at lines 943–945.

The accepted script now sums the remaining **published** `prophet.points`, applies the source's 0–100 clipping and two-decimal rounding, then uses the existing ticker tiebreak and cap allocation. It preserves the same 125 frozen-qualified names. A new positive control checks that each complete published component-point sum reproduces its published score before any ablation is attempted.

This correction affects a reported count. In the independent candidate subset, removing runway previously gave `603279.SS` an unrounded adjusted 57.750 and `600406.SS` an adjusted 57.749. Source-style rounding ties both at 57.75 and the ticker tiebreak admits the latter. The refreshed output from the actual published component-point maps reports runway overlap **20/24**, replacing 21/24. The reviewer extracted the corrected sorting lambda from the accepted script and independently executed this exact cutoff regression; it passes. Signal, entry, bottom-quality and reversal-member comparisons retain overlaps 23, 21, 23 and 20 respectively. The refreshed theme-timing result is 18/24; its full public-point-map execution is covered by the parent run, while the independent candidate subset lacks the full theme-timing point map for a separate reconstruction.

The initial REQUEST_CHANGES applied to script SHA256 `856d0224c03f228b00c465ad97fc3afad5835910904187b63fe9326378bced1f` and result SHA256 `f9156f0f6d3959be785600ef5572c719a281931fdbfd7e02b740cc830d9ac9c7`. It is resolved by the accepted identities above. The parent reported refreshed host PID 26049, exit 0; the reviewer verified the exact refreshed JSON hash locally.

## Checks that pass

### Exact source extraction and controls

The local ranker snapshot has one extra terminal LF from transport. Removing exactly that byte produces SHA256 `504478d0a54919f6b471eace9e395294afdb91b00d0987d34cdf5b6201621e39`, identical to the raw Git blob hash recorded in the parent's JSON. No implementation difference remains. An AST census found no duplicate module-level function or constant definitions.

All nine selected functions are unique and retain their original ASTs: `_finite_float` (236–241), `_attach_intel` (471–505), `intel_order_key` (508–525), `intel_interest_is_measured` (528–536), `intel_coverage_summary` (539–560), `order_provenance` (568–597), `emit_intel_coverage_warning` (600–615), `_stamp_order_provenance` (618–645), and `apply_v4_board_order` (648–673). The selected constants include the actual 24-name featured cap and four-name sector cap.

Independent execution reproduces every stated positive control: measured zero stays measured and keeps complete intelligence ordering; `None`, NaN and the tested nonnumeric string become fallback records; the complete two-row example orders B before A; adding the unbuyable unavailable row switches the entire order to A, B, UNBUYABLE. These are source-semantic checks, not claims that every finite “measured” upstream value has sound economics or complete provenance.

### Qualification population and caps

The published population rule is source-equivalent for this frozen exercise: the featured lane plus only `more_actionable` rows whose nonempty reasons are entirely `featured_cap`/`sector_cap`. In the source, those cap reasons occur only after all buyability, execution, stage and featured-shortfall checks have passed: [the partition implementation, lines 1257–1309](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_board_rank.py#L1257-L1309).

The independent ledger subset contains 125 unique names: 24 featured, seven excluded by sector cap and 94 excluded by featured cap. All 125 have measured intelligence, including 48 measured zeros. Parent's positive control requires exact 24-name public v3 order parity before reporting a result. The cap-only helper preserves the source admission ordering at the fixed positive caps.

### Coverage and central sensitivity

The parent's 1601 scored / 1597 measured count agrees with the independently captured committed board metadata. The 180 raw-eligible count agrees with the four public lanes; the 164 buyable count agrees with featured + more-actionable + late lanes. The JSON reports raw-eligible 179/180 measured and buyable 164/164 measured. All four unavailable records are unbuyable, three also raw-ineligible; their stated reason is `no_edge_evidence`.

An independent sort of the separate candidate subset reproduces 4/24 overlap, all 20 entrant names and all 20 displaced names in the same reported relative order, and both sector-count maps. The JSON arithmetic is correct: overlap 16.67%, replaced 83.33%, Jaccard 4/44 = 9.09%; both selected lists and sector totals contain 24 names. Removing only the sector cap gives overlap 18/24 and ten Basic Materials names, also independently reproduced.

## Integration qualifications

The public artifact and candidate ledger are **not value-identical merely because both are dated October 9**. The accepted script makes this separation explicit in `population_sources` and emits a complete same-date coherence receipt: all 180 public rows are present in the candidate snapshot, with no lane or v3-score disagreements, but **37 intelligence-score disagreements**. The reviewer checked the comparison code, all 37 receipt entries for distinct tickers and real numeric differences, and independently matched the candidate values for the 23 disagreement entries present in the separate 125-name subset. Of the 40 entrant/displaced rows, nine scores differ; examples include `000973.SZ` public 29.80 / candidate 29.88 and `600827.SS` public 33.30 / candidate 33.71. Those differences do not change the independent shortlist result above. Shortlist sensitivity correctly uses public artifact values; coverage separately uses the candidate ledger and is count-checked against the public artifact. Full vintage parity and first-publication timing are not established by matching dates.

The 4/24 finding demonstrates material same-day selection sensitivity to ordering within the already qualified population. It does not show that intelligence ordering improves returns, that qualification should move before the global coverage check, that a mixed ordering mode should be deployed, or that current serving infrastructure matches the pinned committed artifact. The script's explicit no-alpha/no-PIT/no-deployment claim boundary is appropriate.

The requested fix is complete. Final acceptance is **PASS** for the identified script and result, with the observational and publication-vintage limits preserved. No outstanding changes or watchers apply to this bounded review.
