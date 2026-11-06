# Original T12 sample freeze and T13 admission — 17 October 2026

**Original input identity and sample construction accepted; T13 fitting is not admitted.** This is a dated admission result under the existing programme. It preserves the T12 builder, the frozen SPY window, seed, helpers and output bytes. It does not rerun the Stage1 study or activate the T13/T14/T19 drafts.

## Exact binding

The retained canonical `massive_stock_day/SPY.parquet` object was read with the existing R2 reader, a one-key HEAD/GET and an ETag condition. The current object contains 1,327 rows; the original cutoff yields exactly 1,321 rows from July 6, 2021 through October 7, 2026. The original normalization and float-hex encoding reproduce OHLCV SHA256 `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb`. No duplicates, missing cells, nonpositive/nonfinite closes or ratio discontinuities were found. This establishes the previously missing input identity; current object modification time is not a historical first-availability clock.

[The input receipt](../T13_SPY_INPUT_IDENTITY_2026-10-17.json) preserves the object hash, ETag, absent VersionId, exact reader and normalization source, and the limited internal-use disposition. The source-rights manifest's Massive entitlement pointer remains controlling. No entitlement text is copied here; public probability publication is not admitted by this receipt.

One call to the original `build_sample` constructed [sample.json](sample.json) with seed `20261013`, horizons 5/10/21 and the original SPY window. Its canonical bytes use `json.dumps(sample, sort_keys=True).encode('utf-8')`, with no trailing newline: **6,359 bytes**, SHA256 `944e0054b724aef775a5073ee8a1537779b464454a304acf4a4b396cd818a583`. The builder's separate close-input hash uses a different encoding and is not the OHLCV hash. [receipt.json](receipt.json) records both and binds the exact original builder, specification, Stage1 and observed-moves helper blobs.

The [Stage1 dependency review](STAGE1_DEPENDENCY_REVIEW_2026-10-17.md) was completed before execution. Root separately bound its transitive observed-moves helpers to the original #9208 merge. Only original pure AST nodes were executed; full module imports, hydration, feature joins, fitting and ledger entry points were excluded. The environment was Python 3.12.3, NumPy 2.5.1 and pandas 3.0.3. The archived `spy_input_identity.py` and `freeze_original_t12_sample.py` are the exact executed orchestration scripts, retained for provenance, not instructions to repeat an already completed experiment.

## Support that the frozen sample actually supplies

| Horizon | Episodes | Positive origins | Controls placed/requested | Episodes with any control | Episodes with all 3 controls |
|---|---:|---:|---:|---:|---:|
| 5 sessions | 6 | 32 | 10/18 | 4/6 | 3/6 |
| 10 sessions | 7 | 99 | 3/21 | 2/7 | 0/7 |
| 21 sessions | 8 | 238 | 1/24 | 1/8 | 0/8 |

The [independent frozen-sample review](T12_FROZEN_SAMPLE_REVIEW_2026-10-17.md) verifies canonical bytes, every shortfall, bounds, control lengths and within-horizon placement. It also records material limitations:

- The only 21-session control has 20 immature origins among 46 sessions. Its associated September 2021 event's four positive origins are all before the T13 draft's required session-index-63 warm-up. Applying that rule leaves this only matched episode without an eligible event origin.
- One 5-session control has four immature origins. Another consists entirely of 27 pre-warm-up origins; one 10-session control consists entirely of 40 pre-warm-up origins.
- All 5- and 10-session episodes with any matched controls are in 2022. Later episodes remain in the sample with their observed missing controls.
- Shorter-horizon windows nest within the eight 21-session windows. Cross-horizon control overlap and horizon-specific event overlap do not create independent replication or generic benign periods. Independent episode N remains null.

The retrospective event/control mixture is not a daily event base rate. T12 supplies no inferential acceptance threshold; Stage1's ten-episode floor cannot silently become a new T13 rule. No control is manufactured, dropped or replaced to improve these findings.

## Source-purpose decision

The [official-source review](T13_FRED_ALFRED_source_purpose_2026-10-17.md) identifies explicit development/training and retention restrictions in the current consolidated FRED terms, a mismatch with the separately served API terms, and ALFRED Help's affirmative forecasting-research description. Root independently opened the current legal/API/help pages and both series' official status pages. `THREEFYTP10` and `STLFSI4` have distinct copyright labels; the latter is not assumed to be Board public-domain data.

**Current Sol disposition: retain the existing model-use UNKNOWN and operational HOLD for the proposed retained-FRED fitting/evaluation and probability-publication purposes.** This is not a ruling that all historical acquisition was unlawful. The earlier pullback manifest's downstream internal-use “recorded” row and generic registry labels do not resolve the current purpose-specific disagreement. The remaining concrete question is which acquisition-date terms or written permission cover continued retention, this exact statistical process and the intended customer output. No source switch, deletion, new collection or raw-data publication was performed.

## Completed October18 metadata admission and next gate

The [separately adopted contract](T13_SAMPLE_USE_CONTRACT_2026-10-18.md) and diagnostic source were committed at9102e6954db145b92dd3d1c32e113405104ce212 before their single execution. Root verified committed input bytes before the run. The [complete result and disposition](T13_SAMPLE_METADATA_RESULT_2026-10-18.md) preserves2,138 original window-origin records and39 cross-horizon intersections. It finds9/2/0 supported event/control pairs at5/10/21 sessions, attached to4/2/0 events. The21-session matched lane refuses for lack of eligible positive support. The other lanes have necessary structural support only, not established power or model admission.

This post-observation diagnostic assigns no labels or scores. The1,901 dates not bound by permitted metadata remain null. No calendar or FRED availability join is inferred, independent N stays null, and source-purpose remains UNKNOWN/HOLD. The [execution receipt](T13_SAMPLE_METADATA_ADMISSION_RECEIPT_2026-10-18.json) and [post-execution review](POST_EXECUTION_REVIEW_2026-10-18.md) are separate from the immutable sample and contract.

Before a feature join or fit, the exact calendar and original daily outcomes, admitted source purpose and availability, same-support comparators, dependence, chronological evaluation, counted fits and power/utility gates remain to be frozen. A changed sampler, additional entitled history or different study is a separately declared revision with this failure retained. No resampling, window shortening or post-outcome exclusion relaxation occurs under the original freeze. T13/T14/T19 trial budgets remain unspent. Recovery, propagation and predictive superiority remain unproved.
