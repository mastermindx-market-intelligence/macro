# SLR-P0 — development admission result, not an outcome study

Commission: 2026-10-07. **OUTCOME_BLIND_AUDIT_COMPLETE / STRICT_PRIMARY_NOT_ADMITTED / HYPOTHESES_NOT_TESTED.**

This file exists to make the negative execution decision unmistakable. It contains no SLR return estimate, p-value, backtest, empirical power estimate, trading recommendation or prospective read. The full report and exact protocol are companions. The source audit and power illustration are machine-readable.

## What was actually executed

A read-only source/code/manifest census and one explicitly column-restricted Parquet read were completed. The parent file was checked against SHA-256 `3eda29d5ca26b77bc0780ed5ddf1a31f24b9784d2eadf644baf5ec8304eaab81`. The only row columns read were:

`ticker, t0, sector, benchmark_fallback, price_source, gap_leg_crossed, survivorship_biased, basis_mismatch`.

Forward column names were visible in the Parquet schema, but their values were not read. CR1, AF1 and RH1 prospective states/outcomes were not inputs. Published internal historical studies were read as already-consumed evidence, not as new SLR labels.

## Observed parent counts

| Measure | Observed count |
|---|---:|
| All retained onset rows | 2,650 |
| All names | 457 |
| Broad 2014–2025 parent rows | 1,837 |
| Broad-parent names | 409 |
| Nonblank sector / blank sector | 915 / 922 |
| Yahoo / Massive parent-row source | 1,825 / 12 |
| Gap flag true / false | 854 / 983 |
| Basis mismatch true | 12 |
| Distinct onset dates | 996 |
| `-USD` ticker-pattern rows | 39 |
| Technology among mapped rows | 356 of 915 |

These precede the registered end cutoff, historical security-type/identity checks, classification, continuation, first-shock, factor/control and label-quality filters. They are not SLR sample sizes or independent common shocks. The pattern count is not a substitute for instrument-type qualification. See SOURCE_DATA_AUDIT_2026-10-07.json for all era, sector and top-name counts.

## Admission decision and falsified premises

The current-sector collector explicitly declares that it has no membership-era sector channel and sets `era_correct=False`. The inspected coverage receipt reports zero era-correct labels and 802 unlabeled leavers out of 1,083. Historical membership is not historical classification. [M16]

The following premises were contradicted by observed source evidence:

- That the supplied “PIT sectors” artifact is an era-correct classification plane.
- That the existing residual engine is already an exact issuer-excluded implementation of this study's expected-move ruler.
- That the compatibility peer function's fallback remains ex-self and same-sector.
- That 2,650 retained onsets constitute 2,650 independent qualified SLR equity challenges.

**Additional analytical finding:** shared mean-estimation error creates positive covariance between a challenge residual and a future label adjusted with the same fitted mean, even under an independent-return null. The coefficient-free peer-relative primary was selected before any outcome access to avoid this. This is a mathematical design correction, not an empirical SLR test. See METHODS_DERIVATION.json.

**Not falsified:** H1 continuation, H2 tail protection, H3 beta explanation, H4 panic reversal, H5 second-landmark increment, H6 flow increment or H7 shock specificity. None was tested. A source-admission failure is not a statistical null.

Additional qualifications remain unresolved: historical security/issuer type and ticker reuse, actual-window source adjustments/gaps, required PIT size and event controls, terminal return coverage, and enough independent first-shock cells. Current-map or ETF alternatives cannot silently substitute for the frozen primary. They would require a different declared estimand and explicit amendment before outcomes.

## Power illustration—not measured power

Assume a 21-session outcome standard deviation of 8%, residualized predictor variance one, 915 independent observations and normal critical-value sum 2.8. Then an 80%-power detectable slope is about 0.74 percentage points per unit Z. A 0.50-point effect requires about 2,008 independent-equivalent observations under those assumptions; at 10% outcome volatility, 3,136. These are transparent illustrations, not an estimate that the archive contains such information. Dependence, filtering and controls can worsen the requirement.

The registered population has not been constructed. Its event incidence, effective information, outcome volatility and empirical precision remain unknown. Do not manufacture them from the parent manifest.

## Exact result status

| Requested quantity | Status |
|---|---|
| 21-session primary slope / interval | NOT_TESTED |
| Secondary returns, MAE, tail, MFE and state transitions | NOT_TESTED |
| Beta/path/reversal incremental comparison | NOT_TESTED |
| Panic-state laggard comparison | NOT_TESTED |
| Two-landmark R×U increment | NOT_TESTED |
| Generic-residual versus shock-specific increment | NOT_TESTED |
| Flow-conditioned absorption | NOT_OPENED |
| Qualified event and independent-shock counts | NOT_CONSTRUCTED |
| Prospectively validated signal | NONE |
| Production changes | NONE |

## Next gate

The research-to-build handoff authorizes no new effect by itself. Under a current accepted research assignment, the incumbent data owner should first qualify historical classifications and stable identities—or document that no already-authorized source satisfies them. Then freeze an outcome-blind event manifest and assess whether the stipulated inference/power conditions are attainable. Only after all inputs and mechanical fixtures qualify may the frozen historical development run begin. No threshold, horizon, peer source or sign may be chosen after seeing returns.
