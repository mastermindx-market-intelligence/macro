# ALFRED CPI/payroll local projections — retained research appendix

This retrospective diagnostic exercises the existing local-projection estimator and
native CSV consumer. It does not establish a CPI causal effect, a forecast, predictive
utility, a trade, or a current-regime conclusion. The product card has all five decision
authorities withheld and remains `ARTIFACT_INCOMPLETE` because the original requested
recent source window could not be qualified.

The frozen study is `ALFRED_CPI_PAYROLL_V2_STUDY_SPEC.json`, SHA-256
`d70bbc156dc892dfbcf538dc712a5772ec2fb43cb5a3af3c41b7d0a5af7c4871`.
The 332-row CSV is
`data/experiments/local_projection_alfred_cpi_payroll_v2_panel.csv`, SHA-256
`4456ebeff9ebd0e218d5d3b58b643c9a4fdc2e96b8cecabca55736287e7d14a6`.
Both were committed at `a44faea61cfcf8ca9e7e017f3bba0a54b5da5814` before any
estimation. The questions, transformations, horizon, cutoff and three lag settings were
fixed before estimation; the source metadata and transformed numerical rows had already
been inspected. This is a retrospective engineering qualification, not an unseen-data test.

## Producer custody and honest coverage

The existing FRED/ALFRED release-target producer at protected source
`d52827f26b062f67d594350a65becf406710d4d1` retained complete-manifest vintage files:

| Series | Existing producer path | SHA-256 |
|---|---|---|
| CPIAUCSL | `data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet` | `eabad732825e9d6820774f067e8f86791cc3f64a6a81b655522af621c851f22c` |
| PAYEMS | `data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet` | `572f0ebcbea40c98c90e6a1a100d38f5cbb3de15e9e436676bc3aa317785b98b` |

The producer was collected on 2026-10-16 before the fixed information cutoff
2026-10-17T00:00:00Z. These mutable working paths are historical source locators at that
protected commit; a later collector refresh is not a replacement historical receipt.
The frozen input and row-level custody record are the study snapshot. No new data API,
API key, current-revised substitution, external account or held W3 input was used.

The original V1 requested January 1998–September 2026: 345 months. Actual prerequisite
testing refused September 2025: its CPI anchor was 2025-10-24, while the first retained
PAYEMS vintage was 2025-11-20. The archive also had no CPI observation period for
October 2025. `ALFRED_CPI_PAYROLL_V1_SOURCE_REFUSAL.json` and the original V1 specification
remain retained. No model was estimated and no model trial was registered on that
unqualified input.

The disclosed availability-only V2 amendment preserves the largest contiguous prefix
from the original start: January 1998–August 2025, 332 months. It excludes all 13 months
September 2025–September 2026. The boundary was selected from clock qualification before
any estimate, not from coefficient, significance, forecast outcome or best-specification
selection. There is no imputation, gap filling, extrapolation or current-regime claim.

For each economic month the pure assembler selects the earliest retained CPI vintage
strictly after month end and within 45 calendar days. Prior-month CPI and current-month
payroll values must have vintage dates no later than that anchor. The declared
`known_at` is the anchor date plus two days at 00:00 UTC, a conservative bound on
date-only availability. It is not an invented intraday release time, and the earliest
retained vintage is not certified as the true original first release. The custody file
retains the economic month, each selected component vintage and the conservative bound
for every CSV row. Invalid, duplicate, missing, late or nonpositive inputs refuse the
whole requested sample.

## Fixed model family and interpretation

The unchanged `engine.local_projections.impulse_response` estimates horizons 0–3,
embargo 1 and minimum 60 usable observations. The primary uses four lags; prespecified
sensitivity configurations use two and eight lags. All three share the single honest
family `f10_lp_alfred_cpi_payroll_descriptive`; no versioned family resets or winner
selection are permitted. All four horizons and all three complete run envelopes,
including nulls and typed abstentions, are retained.

The supplied response series is log PAYEMS. The native estimator's dependent variable
at horizon h is **log(PAYEMS[t+h]) − log(PAYEMS[t−1])**. The shock is
100 × (log CPI[current] − log CPI[prior]), using both CPI values available at the same
anchor. Coefficients are log payroll changes per percentage point of CPI monthly
change, conditional on the selected lagged log-payroll and shock controls. They are
not stock returns, event-weighted returns or causal treatment effects. Horizons count
monthly observations; the dates in the CSV are availability anchors.

Each fitted horizon retains the native Newey–West Bartlett standard error, requested
and actual HAC lag count, normal-reference 95% interval, raw two-sided p value, usable
row count and dependent-horizon Benjamini–Yekutieli q value. Search N=3 is disclosed
separately. It does not apply an additional specification-search p-value adjustment,
and it is not an independent sample or episode count. Independent episode N remains
null with a typed reason in the card. No scientific acceptance follows from an interval
excluding zero or from a BY rejection.

## Validity threats and robustness limits

- CPI changes and payroll share macro drivers and endogenous policy responses. Bias
  can act in either direction; this design does not identify its sign or a causal effect.
- Persistent log levels, trends and changing macro regimes can generate spurious or
  unstable estimates and optimistic precision. Three lag settings expose sensitivity;
  they do not validate the model or search for a winning lag.
- Source-supplied date-only vintage clocks and conservative two-day bounds do not
  certify exact historical dissemination or intraday tradability. Archive retention can
  differ from first publication even with the 45-day guard.
- The unavailable 13-month recent window can differ materially from the retained
  sample. The direction of that coverage bias is unknown; current validity is untested.
- The study supplies no instrument, randomized shock, counterfactual identification,
  unseen holdout, independent episode count or forecast comparison. No omitted
  diagnostic is silently treated as passed.

## Native registration and consumer receipts

Execution is prepared in `reproduce_alfred_cpi_payroll_v2.py`. It first verifies the
frozen input and StudySpec digests and the exact protected harness source. The existing
TrialLedger owner interface registers the entire three-configuration grid in one durable
batch before the first native CLI process. A cold read verifies all three rows. Each
CLI process must then deduplicate that same complete registration and report search
N=3; it may not append another trial. The native API floors `effective_n` at one even
for an unseen family, so the absence preflight uses `literal_n` and `families`.

The generated registration receipt will retain original row objects, pre/post canonical
ledger digests, the frozen source commit, protected harness merge, execution source head
and driver digest. The retained result bundle will contain all three raw native
envelopes, exact input/spec/registration/code digests, runtime versions and the coverage
exclusion. These are generated only by the original execution, never fabricated by the
read-only adapter. The adapter verifies immutable receipts and the original three rows
in `data/trial_ledger.jsonl`; unrelated family appends remain legal, while missing,
duplicated, changed or additional same-family registrations refuse display.

The existing internal Measurement Research Implications section is the named consumer.
Its synthetic-control and HINCL2 cards retain their original adapter bodies and card IDs.
The LP card adds this research diagnostic in fixed method order with monthly/log-change
units, all three lag specifications, typed missingness and withheld authority. It creates
no Workbench, Analog Lab, Evaluation OS, source registry, promotion route or trading plane.

Native execution, retained results, protected publication and actual authenticated
consumer acceptance remain pending until their original receipts are present.
