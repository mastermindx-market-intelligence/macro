# W2 common-shrinkage / Spearman erratum — 2026-10-04

## 0. Scope and acceptance

This is an append-only correction of an explanatory statement in the incumbent W2
exposure-axis measurement record. It does not reopen the preregistration, replace
historical results, select a new estimator, rerun W2 outcomes, or grant predictive
or decision authority. The raw-beta probe choice, qualified historical verdicts,
input receipts, reconstruction-era membership limits, economic-share honest null,
and refused or limited attention constructions remain intact.

Original source custody, inspected at Macro
`15af4b7fc1d5216542a4e0970e34f40233975c3d`:

- [W2 preregistration](../W2_EXPOSURE_AXES_PREREG.md), section 2.
- [W2 probe report](W2_PROBE_REPORT.md), deviation 9.
- [Probe implementation](../../../scripts/probe_theme_exposure_axes.py),
  `VASICEK_W = 0.66`, `vasicek_shrink`, and `spearman_rho`.

The preregistration's SHA-256 before and after this correction is
`fa5237922bcc112e6c97e61593f634a3db959f69dbee64bbc66f8ac6311b2eb3`.
Its bytes are preserved, including the historically incorrect explanation.
The report's original bytes are preserved as a prefix; its correction is appended.

## 1. Corrected explanation

The report and implementation docstring stated that the display companion's
common shrinkage would inflate H3 rank stability. That explanation is incorrect.

Raw beta remains the preregistered quantity. At the implemented common weight,
the display transform within each cross-section is

```text
b'_i = 0.66 * b_i + 0.34 * mean(b)
b'_i - b'_j = 0.66 * (b_i - b_j)
```

The coefficient 0.66 is positive and the mean term is common to every observation
in that cross-section. Each ordering and tie is therefore preserved in exact
arithmetic. Dispersion decreases, while the cross-sectional ranks remain the same.

W2 H2 and H3 use tie-corrected Spearman ranks. On identical observations, applying
this common positive affine transform preserves those ranks and hence their
Spearman statistics. Different common means in two cross-sections do not change
this conclusion: each cross-section retains its own rank vector.

This correction changes the interpretation of the display transform, not the
historical H1/H2/H3 calculations or results. Those calculations continue to use
raw beta; the numerical implementation is unchanged.

## 9. Verification and interpretation limits

A tiny pure synthetic diagnostic used these five-element vectors, including a tie:

```text
x = [-0.2, 0.3, 0.3, 1.4, 2.0]
y = [-0.1, 0.5, 0.1, 1.1, 1.8]
ranks(x) = ranks(shrink(x)) = [1, 2.5, 2.5, 4, 5]
ranks(y) = ranks(shrink(y)) = [1, 3, 2, 4, 5]
Spearman(raw) = Spearman(shrunk) = 0.9746794344808964
```

The diagnostic uses exact rational arithmetic for the common affine transform and
average tied ranks, then computes the correlation of those rank vectors. It
reads no market data, source tape, W2 outcome sample or confirmation sample.
An AST comparison excluding docstrings verifies that the implementation is
unchanged. No W2 probe rerun or replacement data artifact accompanies this erratum.

The claim is limited to a common positive affine transform on identical
observations in exact arithmetic. Heterogeneous shrinkage weights or targets,
rounding, clipping, numerical pathologies, changed missingness, and differing
sample sets require separate analysis; this erratum does not certify them.

The separately executed pinned QLedger metric-validity selftest passed 7/7
synthetic controls during the GMI evaluation review. That fixture result is not
market evidence, qualified capture, W2 replication, or predictive validation.
