# FINRA paired-volume admission and reader qualification

## Outcome and release scope

The producer repair passes **116 native tests, zero skips**. On the complete pinned panel, all **1,545 signal payloads and 1,545 positioning payloads are byte-identical** to the original implementation. The input panel contains **171,946 rows**, covers **2026-05-26 through 2026-11-10**, and has zero invalid paired-volume rows in this snapshot. Defect discriminators use explicit fixtures; they are not evidence that this pinned live panel is corrupt.

Source/input pin: `cdb3144ea48f2a69f814560f2248123f02c97ff3`. Publication parent: `1be0661c6b7edfe4088fee71ada89a6b454ba095`. All 36 distinct source, data and CI inputs matched their pinned preimages at the publication parent.

This is the producer/parser portion of [issue #11050](https://github.com/mastermindx-market-intelligence/macro/issues/11050). The separate live [consumer PR #11061](https://github.com/mastermindx-market-intelligence/macro/pull/11061) must compose scoped EN/ZH disclosure, and natural PR CI must qualify the resulting source before release. This report establishes native parser/adapter/Parquet/reader/positioning behavior; browser, deployed-page and whole-issue acceptance remain outstanding.

## Input admission and retained data

1. Resolve FINRA raw-symbol case collisions before numeric admission. The uppercase common-share winner remains the selected security even when its numeric text is malformed or truncated.
2. Apply the tracked-universe filter, then require finite paired volumes with 0 <= short volume <= total volume. A selected missing, unparseable, infinite, negative or above-total pair rejects the staged refresh before any live-panel or restatement-witness write.
3. Reject an all-invalid or mixed-validity attempt as the existing failed adapter outcome. A valid earlier response cannot partially commit before a later invalid response. The retained cache and ingest observation clock remain unchanged on rejection.
4. Preserve genuine 0/0 as no observation, the legitimate cache-only heartbeat, and the existing change-only witness. A subsequent valid correction records the displaced row once; an identical reread appends nothing.

The repair adds no stored raw-data column, quarantine sidecar, new outcome vocabulary, retention policy or restatement store. Existing malformed cached rows are retained and qualified in memory. The frozen panel/deep-prefix custody and unrelated short-interest schema remain unchanged.

## Calculation contract

Readable file state remains distinct from usable numeric observations. `panel_state()` flags each retained pair in an ephemeral `_pair_state` column; `signal_map(panel=...)` independently reclassifies the actual operands so callers cannot pass stale flags. Invalid dates retain the file-level parse-error outcome.

| Field | Required observations |
|---|---|
|`ratio_recent`|Every paired operand in the original recent slice.|
|`ratio_baseline`|Every paired operand in the original baseline slice.|
|`trend_pp`|Both admitted VW ratios.|
|`short_ratio`, stored latest present|A valid latest pair and a finite, bounded stored ratio consistent within four-decimal quantization.|
|`short_ratio`, optional latest absent|The unchanged fallback to the qualified recent VW ratio.|
|`ratio_z`|The existing minimum-five/latest-stored-ratio prerequisites, valid historical pairs, and valid nonmissing stored ratios.|

Rows are selected before qualification. No invalid or missing row is dropped to pull an older row into the original five/twenty-row windows. `n_days`, the minimum-three signal rule, minimum-twenty partial rule, full-history nanmean/nanstd estimator, optional stored-ratio absence, zero-sigma result and empty requested-window behavior remain intact. Ordinary finite-sum arithmetic is preserved; scaling is used only when otherwise-valid finite sums overflow.

An optional `coverage` object records only affected calculation scopes: `latest`, `recent`, `baseline`, and `history_z`. Invalid inputs yield `parse_error`; an entirely unobserved slice yields `no_observation`; an incomplete mixed slice yields `unavailable`. Counts are disjoint, and an independently invalid operand wins over a missing counterpart. Here `n_missing` counts unavailable paired observations, including a genuine 0/0 row, rather than treating that row as a measured ratio.

Scope reasons distinguish `paired_operands` from `stored_ratio`. Sound active-window ratios remain available when only an old pair or cached ratio invalidates the historical z-score. Missing optional stored ratios retain the existing nan-aware behavior. The canonical ticker-state precedence is parse error, unavailable, no observation, then the existing partial/observed-zero/observed rules.

Measured zero requires actual zero admitted recent numerators. A positive ratio that rounds to zero remains observed, without the genuine-zero qualification. The internal rounded-positive flag is not projected into positioning. `_positioning()` preserves null numeric values and forwards coverage instead of converting null to 0.0%.

## Executed discriminators

The expanded suite against original source produced **55 failures and 21 passing controls**. The corrected native run produced **116 passes** across the short-volume, C19 consumer-state and superseded-generation suites. Coverage includes malformed/missing paired values, the reported false trends, exact window membership, optional-ratio compatibility, invalid stored ratios, overflow, true versus rounded-positive zero, security-identity precedence in both line orders, truncated winning rows, rejected all-invalid/mixed/valid-then-invalid refreshes with and without cache, unchanged observation clocks/witness bytes, and valid correction/reread behavior.

Tests execute the real adapter runner with fixture HTTP responses and temporary data roots. Reader proof uses actual Parquet, `panel_state()`, `signal_map()`, `_load_short_volume()` and `_positioning()`; the direct nonempty map must equal the real catch-all loader result. Strict JSON serialization is required.

| Native example | Original result | Corrected result |
|---|---|---|
|Four missing recent numerators|False -30pp trend|Trend and dependent ratios withheld; unavailable|
|Four missing recent totals|False +187.5pp trend|Trend and dependent ratios withheld; unavailable|
|All numerators missing|False observed-zero state|No observation; null measurements|
|Infinite latest total|False observed-zero state|Parse error; dependent measurements withheld|
|Invalid pair outside both active windows|Unqualified historical z|Only history_z withheld; valid active metrics retained|
|Inconsistent latest cached ratio|Displayed inconsistent ratio|Latest/history_z withheld; sound paired VW metrics retained|
|Actual zero with positive totals|Observed zero|Unchanged|
|Positive 1/100000000 ratio rounded to zero|Observed zero|Observed; no false measured-zero note|
|Optional latest cached ratio absent|Recent VW fallback; no z|Unchanged|
|Complete constant 50/100 history|Fully observed|Unchanged|

All ten exact before/after signal, state and positioning payloads are in the companion JSON, together with the executable audit/example harnesses.

## Complete retained-panel comparison

| Measurement | Original | Corrected |
|---|---:|---:|
|Retained rows|171,946|171,946|
|Ticker signals|1,545|1,545|
|Positioning payloads|1,545|1,545|
|Observed states|1,540|1,540|
|Existing partial states|5|5|
|Invalid raw pairs in this input|0|0|
|Changed serialized signal payloads|—|0|
|Changed serialized positioning payloads|—|0|

Signal-map SHA-256: `de0b1738d797f1bcec9a2d3ea8e196eb64d0f18921dfdb9d319e306ba3f35dec`. Positioning SHA-256: `1450a8574935684fc7dc22dd30443d05947583e93d49046bc44f15c20d018f30`. Both hashes match before and after. The panel bytes were not changed.

## Existing CI owner enrollment

`tests/test_short_volume.py` is enrolled in the existing CODE owner `c19-wp24-consumer-states` alongside its existing test command. Its collector/test selectors are added, and only its grandfathered unrun-baseline entry is removed. The real loader preserves 401 owners, 328 CODE owners, and all other 400 definitions and weights. This owner's unchanged estimator measures **4 -> 6**: two commands, one -> two test paths, 134 -> 161 joined characters.

The three existing planning ceilings receive only this +2 contribution: **5966/5989/5724 -> 5968/5991/5726**. Job ceilings 137/138/131 and maximum ten packs are unchanged. No other pending carrier's cost is included. This is isolated metadata/owner accounting; full-tree selection, packing and contract qualification belong to the natural CI run.

## Consumer composition required

#11061 currently handles existing partial and genuine-zero notes. Its live writer must compose the optional scoped coverage into EN/ZH: latest qualifies the ratio; recent/baseline qualify the trend; history_z must remain visibly qualified even when numeric z is null. Valid unaffected numbers stay visible. Absent coverage preserves the healthy/legacy behavior. No whole-issue close or merge enrollment is justified by producer proof alone.

Concrete unavailable-ratio payload from the actual corrected positioning function:

```json
{
  "asof": "2026-10-28",
  "coverage": {
    "baseline": {
      "n_invalid": 0,
      "n_missing": 4,
      "n_rows": 20,
      "reason": "paired_operands",
      "state": "unavailable"
    },
    "history_z": {
      "n_invalid": 0,
      "n_missing": 4,
      "n_rows": 20,
      "reason": "paired_operands",
      "state": "unavailable"
    },
    "latest": {
      "n_invalid": 0,
      "n_missing": 1,
      "n_rows": 1,
      "reason": "paired_operands",
      "state": "no_observation"
    },
    "recent": {
      "n_invalid": 0,
      "n_missing": 4,
      "n_rows": 5,
      "reason": "paired_operands",
      "state": "unavailable"
    }
  },
  "n_days": 20,
  "ratio_z": null,
  "short_ratio_pct": null,
  "state": "unavailable",
  "trend_pp": null
}
```

## Source and proof identity

| Candidate path | Git blob |
|---|---|
|collectors/finra_short_volume.py|`4a9b85499f8038e54474609d773180f9a27dc8fa`|
|engine/short_volume.py|`e5a3a23ce9021c41d101d970ed57f3f9ee27dac9`|
|engine/stock_fundamentals.py|`fed5fe31aeeda8d3665d294167483c725a4e752e`|
|tests/test_short_volume.py|`10e86b86632bf7563afeebd89989e5c845f0fac2`|
|.github/ci/legacy-jobs.yml|`b50db94c6710e01677f9e301ad10ce5e2be4661f`|
|config/unrun_test_baseline.json|`076391dac43d579f2f6f1cb6f8df28d8626a16ac`|
|tests/test_ci_pack.py|`0359805feb7eb25a016eee928ed604d88294c961`|

Native test-log SHA-256: `98dbb46bf2d251a7dcd354e715f080ee4d3f81a6a6fcd3134263775f469bb36a`. Original-source red-log SHA-256: `feb6ce6482a4acd81929bcf73b8f1b385478b00a59adf66839520d4cd7128f29`. The [companion JSON](finra-paired-volume-validation-2026-11-11.json) contains the complete input inventory, 36-parent-preimage readback, native metadata, ten finite consumer examples, audit source and CI enrollment receipt.
