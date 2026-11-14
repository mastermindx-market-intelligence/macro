# Forecast producer and consumer diagnostics

Observed on 4 November 2026. These fixtures execute source behavior from Terminal `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9`. Every bundled input is checked against its Git blob identity, SHA-256 and byte length before use. [Exact inputs](sources.json)

## Reproduce

Run from this directory with Node 24 and Python 3.

```sh
node probe-consumer.mjs > consumer-results.actual.json
python probe-producer.py > producer-results.actual.json
cmp consumer-results.json consumer-results.actual.json
cmp producer-results.json producer-results.actual.json
```

The consumer probe executes three unchanged function bodies from `ForecastPage.tsx` through native TypeScript stripping. It imports the unchanged formatter and statement helpers. The producer probe compiles only the unchanged `_f` and `build_estimates` definitions through Python AST selection. It supplies controlled data directly and does not execute the producer's fetching or file-writing entry point.

| Run | Cases | Functional assertions | Input integrity checks | Evidence |
| --- | ---: | ---: | ---: | --- |
| Consumer functions | 13 | 32 | 15 | [Saved result](consumer-results.json) |
| CN producer definitions | 6 | 16 | 3 | [Saved result](producer-results.json) |

Both runs have zero component-render assertions and zero browser assertions. A separate attempt to mount the real React component stopped during dependency installation with npm E403 for `registry.npmjs.org/esbuild`. The setup used package versions pinned in the inspected Terminal package. The controlled component-render suite remains open. Actual served positive-path observations are recorded separately. [Live browser receipt](../../../baseline/continuation-20261104/README.md)

## Findings and required interpretation

| Cases | Reproduced behavior | Product/data requirement |
| --- | --- | --- |
| FC01–04, FP01–03 | Three, two, one and sparse annual target sets survive the helpers. The producer selects present consensus keys from its literal 2026/2027/2028 target list. | Retain every supplied target and its actual fiscal label. Source target selection remains the producer's responsibility. Keep sparse missing years visible as missing coverage when relevant. |
| FC05 | `eps_q=null` preserves available actual quarters and unavailable estimates. | Explain annual-only estimate coverage when Quarterly is selected. Annual targets do not fill quarter slots. |
| FC06/07/13, FP04/06 | A missing estimate object differs from an object containing known periods with null values. Helpers can retain actual rows. Source inspection shows `ActualsTab` returns `AnalystEmpty` early when the estimate object is absent. | Retain actual history within the comparison workflow and access to Financials. Explain coverage separately for EPS, revenue, ratings and price targets. |
| FC08, FP06 | Actual and estimate zeroes, negative EPS, null values and zero-denominator surprise remain distinct. | Preserve signs and unknowns. Show the comparison's unavailable reason without converting it to zero. |
| FC09 | A current forward mean of 8 fills a same-label historical row whose actual EPS is 10 and whose historical estimate is null. The helper produces 25% surprise. | This is an undesirable baseline. Qualify an estimate vintage before giving the arithmetic a pre-event or PIT interpretation. |
| FC10 | Raw period labels `FY2026` and `2026` remain separate in the union. | Normalize only with source-owned fiscal identity. A display-label resemblance cannot establish identical period coverage. |
| FC11, FP05 | A consensus mean of 6 can coexist with per-report low 8, high 9 and count 2. Both reports can come from the same firm. | Label the report population and observation window. Consensus means, report ranges and report counts can have different populations. A count of reports cannot become a count of unique institutions. |
| FC12 | The Chinese count label is `预测机构数` while this source aggregates reports. | Use source-specific report-count semantics in both locales. Unknown count remains unavailable. |

The producer's report-year attribution and available EPS observations determine the range/count subset. Reports without a consensus-map record do not independently create an estimates block. Revenue is transported in raw CNY, with unavailable range/count retained. Successive fiscal targets are a cross-section. They do not supply estimate-revision history.

The live UI uses `EstimatesAsOf` with `fund.asof`. Existing producer evidence identifies this as the file-build date. Acquisition, filing, provider observation and forecast vintage retain separate meanings. These diagnostics establish neither rights nor a provider observation clock. [Semantic tasks S05–S08](../../../SEMANTIC_TASKS.md)
