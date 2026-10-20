# Independent International source-trace review

**Reviewer:** `/root/intl_source_trace_principal` · GPT-6 Astra Pro  
**Reviewed:** 2026-10-20 14:57 UTC  
**Recommendation:** **PASS for the bounded source change.** No material blocking defect found. This is not release, UI, acquisition, or served-site approval.

## Binding

Patch: `intl_source_trace_repair.patch`  
SHA-256: `f38485f3d158183f231da84ac11ad27094d643e86a1158590f723005c8e3a3da`  
Source base fetched independently: `6ad0c377ed80a8ccf07ecbfb6c7b44530b753cf7` in `mastermindx-market-intelligence/macro`.

The patch contains four production Python files and three test files. The four production files applied successfully to independently retrieved base copies. Their resulting SHA-256 identities are:

| File | SHA-256 |
| --- | --- |
| `lib/intl_country_inputs.py` | `a7d9205597b960e72da41c640fc725ddb59716c60b40226f8e3fb79598065108` |
| `lib/intl_country_assessment.py` | `34be50dc9ddda218deeb265aa7090c209a04ddbb00c9b548668ab8041a897919` |
| `engine/intl_equity_risk.py` | `2ab13f6accdeb181fc74475d5f800c11b510a55dc7ac03477fe3d1bbb9fc528d` |
| `scripts/build_intl.py` | `41e2d7c791c4022f9165c267d31fc5cc4b22b188fbfba2c48a9a1980742a61f0` |

## Findings and verified behavior

The new GDP reader ties each supported series to the actual configuration, producer metadata, file column, latest observation date, and reviewed series definition. Its five consecutive quarterly levels span precisely four calendar quarters. The calculation uses the original endpoints and returns the quarter and quarter-end date. Missing or invalid levels, calendar gaps, duplicate quarters, future periods, and mismatched request identities are rejected.

All five GDP definitions and the four FRED unemployment definitions were checked directly against the official FRED series pages. The native units, frequency, seasonal adjustment, provider, and series identifiers match. The Euro Area GDP series is explicitly EA19; the configured Eurostat unemployment request is EA21 with `s_adj=SA`, `age=TOTAL`, `unit=PC_ACT`, and `sex=T`. The helper preserves that distinction and rejects changed dimensions.

The existing qualified official observation retains precedence, including a valid older national observation. A missing, invalid, future, or mismatched official GDP observation allows an independently validated stored fallback. Anonymous legacy values cannot supply the new source-attributed country metric. Original legacy records remain unchanged.

The equity evidence describes the actual rows used by the incumbent calculation. Its window counts and dates, latest close, arithmetic means, recent high and most-recent tied-high date are reproducible. Strict comparison flags use unrounded values; equality is not above. A partial 200-observation mean cannot establish a complete trend. Custom matrices do not inherit canonical provider attribution. Valid older evidence stays available while the current market interpretation is withheld.

I traced the existing production call chain in exact source: `scripts.build_intl.main` calls `engine.intl_run.run`; that run calls `equity_risk_all()` without a supplied matrix; `country_record` preserves the equity mapping; the in-memory result reaches the assessment. The canonical price reader consumes the stored `close` column. The price adapter requests daily Yahoo data with `auto_adjust=True` and `ignore_tz=True`. The new macro reader is explicitly mounted in the builder, using the same evaluation day as the assessment.

The change does not manufacture acquisition or revision custody. `retrieved_at` remains absent, `vintage_custody` is `not_recorded`, and equity session finality remains unverified. Existing `current` fields mean observation-age eligibility only. Request time, render time, and file modification time do not refresh that evidence.

## Executed proof

Four repaired production files passed syntax parsing. **58 independent bounded checks passed, zero failed:** 50 checks of the actual repaired helper/consumer/producer function bodies and eight unemployment identity/dimension checks. Real pandas rolling calculations were compared with the independently recomputed evidence and the unchanged base scalar outputs at 60, 99, 100, 199, 200, 252, and 400 observations.

Evidence:

| Artifact | SHA-256 |
| --- | --- |
| `review_checks.py` | `99c64afdb7e843955f283d1024afe386bfcc5eba782f55110f5febd8abb8af47` |
| `review_checks.json` | `a4b8e9097373e5b48ab752486b2e5796426e24f5509e3137fb7293b07cfcc4fb` |
| `review_unemployment_checks.json` | `838ea360dd5112057f88fd5506d5c392412e41df9424862a7fa3a084fb43d661` |

These checks extracted unchanged function bodies with AST. Unrelated FX, extension and RSI imports were substituted; Parquet decoding was substituted with an explicit local frame. They therefore do not establish full repository imports, actual Parquet decoding, normal builder output, or browser behavior. Root separately reported 262 real repository tests passing with actual Parquet; I did not execute or independently inspect that run.

An initial local patch check failed because the review-copy writer had appended one extra newline to retrieved files. The copied source lengths were reconciled against the exact fetched bodies, then the unchanged patch applied successfully. This was a review-fixture preparation error, not a source-patch defect.

## Remaining integration obligations

Root should bind these four hashes to the actual committed artifact, complete the declared-runtime and full retained-input build checks, and inspect the resulting source disclosures. The UI must retain the calculated GDP label, actual quarter and native-level formula, EA19/EA21 geography distinction, linked source/series identity, dated equity windows, unrounded-comparison explanation and missing-vintage qualification. The false equity flag must read “at or below.” The template integration was described by root but was outside this code review.

Actual acquisition, final immutable-artifact product/visual review, hosted CI, publication, and served acceptance remain with their existing owners. No remote process, remote write, Git publication, or provider data acquisition occurred in this review.
