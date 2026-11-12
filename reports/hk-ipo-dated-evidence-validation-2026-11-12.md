# HK IPO dated evidence and malformed-input isolation

Issue: [#11085](https://github.com/mastermindx-market-intelligence/macro/issues/11085).
Owned F2 claim: [6811200804](https://github.com/mastermindx-market-intelligence/macro/issues/11085#issuecomment-6811200804).
Original acceptance: [6808949737](https://github.com/mastermindx-market-intelligence/macro/pull/3232#issuecomment-6808949737).
F1 carrier: [#11087](https://github.com/mastermindx-market-intelligence/macro/pull/11087), exact commit e94ae79fab0ac05f6e2bc352145b2fa82df8f7ea.

## Result

The HK shelf now shows the selected Southbound observation window, HIBOR observation date, latest source-row date when trailing values are missing, and the separate shared regime snapshot date for peg/risk. It displays the existing input count and limited-coverage state.

Malformed active numeric operands and malformed regime fields withhold only the affected leg. The original 20-nonmissing-observation floor, legitimate zero, finite numeric/string readings, HIBOR thresholds, negative-value policy, rounding and verdict aggregation are preserved. Old malformed values outside the selected window no longer erase a valid current leg. A finite-input sum that overflows is withheld before rounding. Containers, booleans and complex values are not numeric readings.

Date disclosure does not add an age cutoff, exchange-calendar filter, date sorting/deduplication or replacement observation. Explicitly incomplete or relative regime-date text, including “today” and “now”, remains unknown. Peg/risk carry a regime snapshot date; this payload does not establish each underlying component’s observation date. The shelf remains display-only and `SCORED = False`.

## Verification

**186 pytest cases passed, zero skips and zero collection errors:**

| Suite | Passed |
|---|---:|
| Existing `tests/test_ipo.py` | 68 |
| Existing `tests/test_ipo_prospectus_terms.py` | 16 |
| Preserved F1 `tests/test_ipo_hk_missing_copy.py` | 17 |
| New `tests/test_ipo_hk_evidence.py` | 85 |

The same 102-case F1/F2 suite against the original product source gives **67 failures and 35 passing controls**. All 17 F1 cases pass on both versions; their behavioral assertion bodies remain unchanged. F1’s data seam now invokes the full engine with dated store frames, and its VM extractor includes the new HK helper.

The new tests cover dates shifted by ±365 days, five trailing HIBOR gaps, the original 19/20 observation boundary, zero, unchanged thresholds, old versus active malformed values, nonfinite aggregates, actual Parquet list cells, non-dictionary regime JSON, independently malformed peg/risk fields, invalid/relative dates, duplicates, direct reader-seam date faults, and template escaping. Network/DNS attempts remained zero.

The native extension contains **15 consumer executions**: one original-source retained-input control and 14 repaired-source controls. It uses actual Parquet/JSON files, unchanged `lib.store.read`, the full engine, the actual imported VM, and the native bilingual `t` macro, `STATEW` mapping and HK template section.

The healthy retained control contains **2,749 Southbound rows and 6,367 HKMA rows**, both ending 2026-11-11, with regime snapshot 2026-11-10. Every legacy engine field and legacy VM field is exactly equal before/after: four legs, no missing inputs, POOR verdict. Date-only controls change the rendered evidence while preserving their numeric legs and votes. Invalid-leg cases preserve every unrelated leg exactly.

All 22 builder functions outside `_hk_vm` remain AST-identical. The template before and after the HK section is byte-identical. No style-union or lockup hunk is imported.

## CI enrollment

F1’s original run43120916959 failed its contract-delta because its new test suite was not named by a run step. This composition repairs that actual defect in the existing `conviction-profile` CODE/exclusive owner:

```sh
python -m pytest tests/test_ipo_prospectus_terms.py tests/test_ipo_hk_missing_copy.py tests/test_ipo_hk_evidence.py -q
```

The selector count changes **708 → 718**: the two suites and eight existing `engine/fundamental_forensics/` modules actually imported through the complete VM path. Their source is unchanged; no forensic/provider operation is invoked.

The exact incumbent estimator gives **53 → 57**. All other 400 owner definitions, installation commands, top-level configuration, global packing ceilings and the unrun baseline remain unchanged. Every measured first-party import and literal HK-template input is covered.

The exact original `_job_weight` and `OBSERVED_COMMAND_SECONDS` AST nodes were executed from runner blob fdd099b87cf72e8221372ef55de95efa2b7d284e. This is owner-local accounting and measured consumer coverage. Full-tree contract, inferred closure and packing qualification remain required in natural hosted CI.

## Source and custody

Protected Mastermind law pin: c42e812e4a754d7a95efd954441d3f01607a7fb5.
Native source composition: main e752cc8a98a871ce67f4f4a4c98b014f824d0e4a plus the two exact F1 files. The publication preserves the F1 commit in ancestry and leaves its branch untouched while the comprehensive successor qualifies.

The finite HK custody artifact contains 69 exact head/base/merge-base records and 500 unique object queries, with no errors or moved heads. Only F1 #11087, lockup #10890 and style #10654 contribute to the HK target paths; the latter two retain their distinct source/effect/hold boundaries.

CI hunk qualification reuses 326 complete and 17 incomplete retained catalog patches, closes 39 current open-head owner comparisons, and preserves eight compatible same-owner carriers. No examined carrier changes this IPO command or the two suite selectors. A separate eight-module supplement classifies all 53 matching retained added lines as other owners. This is bounded hunk qualification, not a blanket owner takeover or a new estate census.

The initial native preparation omitted literal owning-suite files; its 16 failures and the subsequent 14 prospectus fixture setup errors are retained as preparation evidence. Exact source/data inputs were completed before the successful final run. They are not reported as product regressions or hidden successful tests.

## Evidence and limits

[Machine-readable evidence](hk-ipo-dated-evidence-validation-2026-11-12.json) contains exact source/input bindings, test results and logs, native case receipts, source-scope comparisons, CI accounting, harness source, and losslessly compressed custody records with hashes.

The unchanged store normalises dates and sorts before returning a frame. A malformed date can fail there and be contained to its input; an original numeric index may already have become 1970 timestamps. This consumer repair cannot reconstruct lost original date provenance. No fresh-data assurance, live stale-feed incident or new admission calendar is claimed.

The native extension qualifies the real HK section, not a full page build, interactive browser layout, deployed production behavior or trading effectiveness. The broader existing IPO suite includes its own full-template fixtures. No live provider call, data rewrite, generated site publication, scoring promotion, self-approval, direct merge or external message was performed for the proof.
