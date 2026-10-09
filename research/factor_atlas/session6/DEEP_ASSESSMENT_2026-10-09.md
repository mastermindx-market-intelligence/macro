# Factor Atlas S6 — deeper scientific and instrument audit

Status: IN_PROGRESS / NOT_READY_FOR_EMPIRICAL_FREEZE. This is a self-audit of the S6 evaluation instrument, not independent acceptance of this author's code or of Sessions 1–5. All novel market hypotheses remain untested. No historical holdout, source data, score, deployment or source-owner admission is changed.

## Recovered source

- Original draft PR: macro#8696; branch research/factor-atlas-s6-empirical-20261009.
- Audited predecessor: fbaa3812510a67e879c17defa270e16f717d3ce3.
- Protected Mastermind: 7d82b9adb839d54e4ab25378ca333e498dd83fcc; skillpack 1.0.1/bootstrap 1. Current INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY and WEB_CEO_DELEGATION loaded. Source-only continuation under the current Chairman's deeper-assessment request.
- Source guard exact Git blob: f7a595cf330da68276f9eb6522c2fa96bd910625. The locally executed UTF-8 bytes matched this Git blob exactly, not merely after deleting whitespace. SHA-256: 4962c6dedca08d2b4558c224125f9e5b1228c46a0535445e8acd04f9f8d72594.
- Direct work rationale: PRINCIPAL_JUDGMENT for scientific design and LOWER_TOTAL_OVERHEAD for this bounded pure synthetic instrument audit. No worker dispatch or runtime admission is claimed.

## Confirmed new findings

### D1. The generic 2% primary-loss gate is not defined well enough

For synthetic realized variance y=1 and fixed forecasts f_A=2, f_C=1.8, the same QLIKE forecast ranking gives an absolute paired gain 0.0498049601. Relative improvement is 4.1743% under log(f)+y/f, 25.7860% under y/f-log(y/f)-1, and 0.4450% after adding a forecast-independent constant 10 to the first score. None of these changes the forecast ranking. The proposed 2% gate changes solely with scoring normalization. The exact loss, treatment of zero realized variance and utility margin must be frozen before any empirical run. A robust loss difference is preferable to an unspecified percentage of QLIKE.

### D2. The predecessor structural suite misses malformed inputs

Twenty-nine targeted counterexamples were run against the exact predecessor source. All 29 exposed an unhandled invariant: NaN knowledge/cutoff/label/quote clocks passed as structurally clean; floats and bools were accepted as nanoseconds; missing mandatory clocks or an empty history with a zero floor raised exceptions instead of typed rejection; blank/numeric identity passed; an empty aggregation returned numeric zero; shared-member corporate-action and signed-pressure conflicts were not checked; context-rounded Decimal abs hid pressure exceeding gross; Decimal aggregation depended on row order at sufficiently large precision.

These are 29 deliberately selected adversarial cases across several defect classes, not an estimated real-world defect rate. All returned financial/publication authority flags remained false. No customer exposure is demonstrated. The existing 36 passing tests do not cover these new cases.

### D3. Readiness correction

The previous statement that all scoped lanes were blocked was too broad for continued assessment. Real-data admission and independent product acceptance remain gated, but the evaluator itself has useful, safe, unblocked repair and scientific work. The original report and inactive candidate must not be activated unchanged.

## Current frontier

Persist the exact counterexamples and an outcome-free synthetic experiment specification; repair only S6-owned structural code; run original and added tests; quantify dependence/power and partial-observation bounds; complete the revised hypothesis, multiplicity, matched-baseline and human-value design. Preserve the original inactive preregistration, all spent Factor Intelligence/K3E/Trend Persistence trials and S1/S2 custody. Continue in this turn; this checkpoint is not a release or a terminal acceptance.
