# Final ranking-metrics review

**Verdict: PASS for numerical accuracy, preserved cohort controls, and the stated conditional diagnostic interpretation. No material correction is required in the reviewed versions.**

Reviewer: `/root/china_research`, 2026-10-09. This is the separately commissioned final metrics review. It covers `RANK_METRICS_ADDENDUM.md`, its Python script, result JSON and pool input, the new precision/decile/tie-break text in `REPORT.md` §C, and the new “Validation time and operating cost” subsection in `IMPLEMENTATION_HANDOFF.md`. Previous historical and integrated reviews retain their own scope and acceptance. This review does not modify or supersede `FINAL_REVIEW.md`.

## Independent verification

I inspected the calculation and independently reconstructed the selections and statistics from the local input matrix, using pandas sorting and sector group counts rather than invoking the author's script. The independent selection frame contained only ticker, sector and the four ranking features; status and return fields were joined after choices were fixed. I did not run the author's `main()`, regenerate prices or outcomes, contact a host, or perform new public research. Only this review file was written.

The supplied input contains 1,488 distinct date/ticker rows over 29 dates: 949 observed, 537 immature and two missing-exact-session outcomes. All rows satisfy the declared V4/H10 cap-qualified predicate. Empty feature values remain missing, observed outcomes are finite, and stock return minus benchmark return reproduces excess return. Local hashes and the embedded source/manifest cross-links match the supplied receipts.

| Control and source location | Independent result |
|---|---|
| Frozen feature selection and missingness: `rank_metrics_addendum.py` lines 94–132, 207–234 | Four-feature common pools are formed without filtering outcomes; all five choices are fixed before completeness checks. All 29 date gates and every recorded frozen selection reproduce. |
| Original comparison: script lines 235–268; addendum §§“Source, selection rules and precision definition” and “Accepted precision@6” | All 55 arm/date counts, precisions, mean stock returns and mean excess returns agree with accepted `v4_review_rows.json` values. The new membership receipts independently reproduce from the input. Each arm has six observed selections on the same 11 dates. |
| Unresolved selections: addendum lines 77–79 and 100–114 | August 31 retains unresolved `601059.SS` in the original score top six and remains excluded; there is no replacement. September 1 has 45/46 observed pool members but complete six-name selections, so it remains in precision@6 and is excluded from the complete-pool decile comparison. |
| Vintage exclusion: script lines 201–204 and 216–217 | All five pre-existing discordant dates remain quarantined. Four occur in the 29-date input; September 4 has no qualified input rows. It has not silently become admissible. |
| Decile construction: script lines 311–329; addendum lines 49–63 | K is fixed as `ceil(original common-feature pool size / 10)`, with no sector cap. Choices precede outcome completeness. All arms use the same ten complete original pools, 35 selected observations per arm and 320 pool observations. All ten complete-pool controls match the accepted historical values. |
| Precision denominator and weighting: script lines 135–163 and 337–355; addendum lines 19–47 and 65–75 | Hits require strictly positive excess. Original precision uses all six selections. Decile precision is averaged equally across dates; the separate pooled hit count and ratio of date-weighted precisions reproduce. Varying decile K is not mistaken for a constant denominator. |
| Paired return lift: script lines 166–184 and 330–365 | Recomputed each date's selected mean excess minus that same pool's mean excess. Independently generated the 10,000 shared date draws with Python seed 20261009 and used NumPy linear percentile endpoints. All five means and both endpoints agree within 1e-10 percentage points. |
| Intended intel tie-break: script lines 269–310; addendum lines 81–98 | Intel descending, v3 score descending, then ticker ascending gives exactly the same ordered six names on all 11 dates as the stored-intel/ticker baseline. There are zero replacements, zero order changes and no newly unresolved selection. |

The date gates reproduce as 11 accepted, four existing vintage exclusions, five dates with fewer than six common-feature names, one incomplete frozen selection and eight dates with no observed H10 outcomes.

## Numerical receipt

Precision@6 has 66 selected observations per arm over 11 dates. The decile results below use the separate ten-date, 35-selection-per-arm comparison against 320 full-pool observations. These columns describe different K/cap/date constructions and must retain those labels.

| Ordering | Positive outcomes / 66 | Precision@6 | Decile mean excess lift | Descriptive paired date-cluster 95% interval for lift |
|---|---:|---:|---:|---:|
| Score | 28/66 | 42.4242% | −0.3285 pp | [−2.8919, +2.1094] pp |
| Stored intel; ticker tie-break | 29/66 | 43.9394% | +0.1251 pp | [−1.9153, +2.2050] pp |
| Momentum | 33/66 | 50.0000% | +0.5377 pp | [−2.1966, +3.5272] pp |
| Reversal | 33/66 | 50.0000% | +0.3075 pp | [−3.5201, +3.1882] pp |
| Quality | 31/66 | 46.9697% | −1.3127 pp | [−2.2262, −0.2421] pp |

The complete-pool equal-date mean excess is +0.2011977310 pp. Score's decile mean is −0.1273342869 pp; its paired lift is −0.3285320179 pp. **Quality's interval is wholly negative; the other four span zero.** The quality result is retained in the report, with the same small-cohort, serial overlap and multiplicity limitations. No result in this addendum establishes a reliable positive improvement.

Both intel tie conventions produce 29/66 positive outcomes, 43.9394% precision and −0.5631223172 pp mean gross excess on the paired 11 dates. This equality is a deterministic result for the recorded six-name cohort and does not establish equality of the complete published board or future policy behavior.

## Interpretation and integrated wording

`REPORT.md` §C, lines 108 and 110, accurately separates the stored-intel baseline from the intended tie convention; reports the reproduced precision, decile denominators and return lift; preserves the adverse quality interval; explains September 1's different admissibility; and explicitly prevents a direct aggregate comparison between the six-name and decile constructions. No new causal or alpha claim is introduced.

`IMPLEMENTATION_HANDOFF.md` lines 40–53 correctly presents validation dependencies and operating-cost considerations. Correctness receipts can be checked before future horizon labels mature; one matured batch does not supply statistical validation. Prospective promotion still depends on untouched temporal evidence and the existing power/overlap gates. Source cadence, source history, event diversity, latency and capacity are measurement dependencies. The subsection makes no delivery-date, currency-budget, model-performance or new-vendor commitment.

The addendum's scope remains conditional on the accepted common-feature, cap-qualified and completeness-filtered cohort. Frozen selection here means that this calculation uses recorded features before inspecting outcomes; it does not recover publication-time receipts or certify point-in-time feature availability. The unchanged labels use current adjusted-price, matched next-session-close entry and ten subsequent benchmark sessions, as defined in the accepted historical evaluation. They do not regrade production H10. Serially overlapping horizons and repeated issuers remain dependent; the resampling is by single date and is not a serial block bootstrap or multiplicity correction. Intraday execution, costs, portfolio accounting, terminal security outcomes and executable alpha remain outside the evidence.

Provenance boundary: this review independently verifies the supplied subset's bytes, predicates, local accepted inputs, embedded receipt consistency and derived calculations. The complete original archive CSV was not part of this bounded review, so the parent's verified extraction receipt remains the authority for the subset's exhaustive correspondence with that archive. This is an evidence boundary, with no contradiction found in the supplied records.

## Final reviewed hashes

The following exact versions were inspected and checked unchanged before and after the independent computation.

| Reviewed file | SHA256 |
|---|---|
| `RANK_METRICS_ADDENDUM.md` | `639aca43549f80e974701d5a9e2b1920fd224233eaf00ba5ed7e21c223ad0bae` |
| `rank_metrics_addendum.py` | `da214bd49e4e7f37975463d6cf891696ae95e767ef112562f08826295f42ce39` |
| `rank_metrics_addendum.json` | `d514efe4c8bcb624603d32ab6c0ece6b3ef2292c858f83ebc1e55e8834985dbc` |
| `rank_metrics_pool_input.json` | `1f6708ca0e8ec12d2983900f5d5d0313a9272e726730d7a91a220b4165bb6976` |
| `REPORT.md` | `b6c9a044fcbe7422b539b1267ae3b82bbd68faae047cfd107f34e4f7ff46dec3` |
| `IMPLEMENTATION_HANDOFF.md` | `968a4c4307645aa51c02f2179088d560ddb71eca9139157d352c7475f10ba5e3` |
| Accepted input `v4_review_rows.json` | `626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830` |
| Accepted input `historical_evidence.json` | `8b651cf4df19736f66a3cf184c5a47478ffe0bf2fc62a24bb5452c01b836e54d` |

**Disposition: terminal PASS for this bounded review. Parent acceptance and canonical persistence remain with the parent. No further experiment or implementation is requested by this review.**
