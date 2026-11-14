# Q13 forward numerical-consistency revision

Date: 2026-11-11. Scope: issue #11063, under the assigned estate repair in #10912.

## Status and historical boundary

This is a prospective **source-correctness contract**, recorded before its implementation and new synthetic execution. The atom, endpoint and coarse-grid counterexamples in #11063 are already known. Their regressions are development evidence, not blind empirical validation.

The forward report schema is **`options.rn_tail_density/research-v2`**. The prior midpoint estimator and classifier belong to `research-v1`. Frozen PREREG §8 prescribes midpoint interpolation while the density/reintegrator uses discrete atoms; frozen §13 omits reintegration as a classification trigger. This revision resolves those conflicts prospectively.

Historical source remains available at commit [67c8f47e](https://github.com/mastermindx-market-intelligence/macro/tree/67c8f47e5231328fd22f8e05113fc1ea80cd21f4). The frozen PREREG, amendment, requirements, evaluation harness, run/freeze records, results and verdict are preserved. They are not rerun, rewritten or relabeled as evidence of this revision.

Q13 remains `INSUFFICIENT_DATA`, `research_only=true`, `admitted=false`, and a pricing-measure Q diagnostic. M1–M4, the refusal to infer physical probabilities, and the historical once-only evaluation stop rule remain intact. This repair includes no new market-data evaluation, calibration, provider, production consumer or trading use.

## One probability object

The piecewise-linear call curve defines interior atoms at its interior strike knots. The forward CDF is the **right-continuous CDF of those atoms**, not interpolated chord-midpoint values:

`F(x) = left_mass + sum(interior_mass at strikes <= x)`

where the threshold lies in an identified part of the support. A left-limit query uses strictly lower strikes. Public `cdf`, `left_tail_probability`, `q_tail_probability`, report points and perturbation draws must share that object.

The repaired atom construction uses the same bounded monotone slopes returned by the repair. It does not introduce a second finite-difference approximation that can create negative roundoff masses. Raw diagnostics remain available. Invalid or signed measures cannot publish a point CDF by clipping their defects away.

Retain pricing, smoothing, PAVA, quote bands, grid settings, input limits and the existing statistical classifier thresholds. Coarse grids remain accepted inputs; they may yield bounds-only reports.

## Partial identification and endpoints

The underlying support is nonnegative. Left truncation mass lies in `[0, K0]`; right truncation mass lies in `[KN, infinity)`. A tail mean is not an assumed point location.

A query that cuts an unresolved tail has no identified point probability. The low-level CDF APIs raise a dedicated `ValueError` subclass, `ProbabilityUnavailableError`, with a stable reason. A mixed batch containing an unavailable query fails explicitly rather than substituting zeros or returning a silently conditioned subset.

Zero tail mass is identified. Forced endpoint mass is also identified: a feasible left first moment at either support endpoint forces that location; a positive right mass with zero terminal call value is at `KN`. At `KN`, unresolved right mass cannot be omitted from a claimed point CDF merely because it is labeled truncation mass.

Use numerical roundoff, not the broad historical forward tolerance, to identify an endpoint. A positive tail is never discarded because its mass is small. If numerical precision cannot distinguish endpoint from interior placement, retain unavailability.

The exact law with masses .25 at 80, .50 at 100, and .25 at 120 must work on both padded and endpoint grids. On `[80, 100, 120]`, calls `[20, 5, 0]`, F=100 and D=1 force both endpoint locations: CDF(80)=.25, CDF(100)=.75, CDF(120)=1.

## Strict outside-range accounting

For the closed quoted range `[a, b]`, outside mass is:

- Below: `F(a-)`, excluding an atom exactly at a.
- Above: `1 - F(b)`, excluding an atom exactly at b.

Unidentified boundary values are explicit nulls with availability information. Their total is unavailable unless both parts are identified. Preserve component truncation masses as diagnostics and distinguish them from mass strictly outside the closed grid; an endpoint component is not automatically outside mass.

Reintegration retains its declared in-grid domain. Its tail means are sufficient for in-grid call payoffs without locating an unresolved tail.

## Numerical validity before point reporting

The existing `classify_identification` helper and its frozen thresholds remain unchanged. The v2 report adds numerical prerequisites. A full point report requires:

1. Finite, nonnegative probability components with unit total mass within roundoff, valid support, and feasible forward accounting.
2. The existing raw and repaired forward checks passing.
3. An identified finite point in [0,1], inside the report's consistent identified [L,U] within roundoff.
4. Source-compatible reintegration passing at the **existing** declared relative tolerance of 1e-6.
5. Reintegration covering **every supplied quote**, not merely the convenient in-grid subset.
6. Every required uncertainty draw qualifying under the same probability, source-band, coverage and identified-bound conditions.

A failed prerequisite restricts the report to `PRICE_BOUNDS_ONLY`, withholds the point and model interval, and supplies explicit reasons. Keep useful subset reintegration diagnostics while identifying checked and unchecked quote counts. Do not expose an invalid point under another supposedly usable point field.

Numerical roundoff uses 64 times float64 machine epsilon. Probability/mass comparisons use that dimensionless scale; first-moment comparisons scale it by the relevant finite forward, strike and price-over-discount magnitudes, with a unit floor. This is numerical consistency, not a fitted tolerance or an expansion of quote bands. Endpoint identification must remain conservative when both endpoint possibilities fit within that precision.

## Uncertainty draws

Preserve the requested draw count, seed, uniform IV-band sampling and fitter. A draw must define an available probability object compatible with the original call-equivalent bands and complete quote coverage. Do not drop failed draws and report quantiles of the surviving subset as though they were the requested experiment.

Return requested, finite/qualified and unavailable counts with reasons. If any required draw fails, withhold all interval summaries. The report retains this failure accounting and withholds the point/model interval under the rule above. Invalid caller arguments remain input errors; numerical unavailability is distinguished from them.

## Required synthetic qualification

Before source release, demonstrate:

- Exact atom CDFs, atom-side limits, interval masses and zero mass in empty intervals.
- Invariance to redundant collinear strike knots.
- Forced endpoint examples and unresolved tails, including nonzero small tails.
- Correct strict outside-range accounting at both quoted endpoints.
- Consistency with reintegrated calls and the forward basis.
- The retained smooth report fixture at 3, 5, 11, 21, 51, 101, 401 and 801 nodes: incompatible configurations cannot publish a full point; compatible fine-grid controls can.
- Complete versus partial quote coverage.
- Explicit uncertainty-draw failure handling without survivor conditioning.
- Preserved Q/P refusal, research-only/nonadmitted restrictions, bounded inputs and import inertness.

Use the existing hermetic test module and code CI owner. Known fixtures and ordinary source tests do not establish prospective predictive performance. Any later empirical study must identify the revised method and use the existing authorized research process; this repair does not start one.

## Implementation and synthetic qualification

The contract above was committed at `1233c7ce9765691d249ba2ff7250921e5e10ab75` before implementation or new synthetic execution. The following records subsequent source qualification, not a change to that prospective contract.

The original source passed its 27 existing tests. The initial new contract regressions produced **23 failures and one passing input-error control** against that source. The final complete module runs **57 tests, all passing, with zero skips** on Python 3.14.7. The existing code CI owner remains `quant-q13-rn-tail-density`, running the full module without filtering.

The cases cover exact and redundant-knot atom laws, both CDF limits, closed-range accounting, unresolved and tiny positive tails, invalid signed measures, complete quote coverage, and unavailable or finite-but-incompatible uncertainty draws. An exact rational certificate, evaluated only when an endpoint query needs it, prevents rounded products or near-endpoint moments from inventing a forced left atom. A rounded right mean cannot override a positive terminal call.

The retained smooth fixture was tested at 3, 5, 11, 21, 51, 101, 401 and 801 nodes. Its six coarse configurations withhold invalid point estimates. At 401 and 801 nodes the central curve passes reintegration and covers every quote, but all eight requested perturbation draws fail the original source bands; the report therefore retains bounds and the failure counts. Compatible grid-aligned controls at both fine resolutions produce full reports, and separate compatible uniform-band draws preserve deterministic, widening uncertainty intervals. The four older assertions that depended on v1 endpoint or draw assumptions now exercise the explicit v2 behavior.

Pricing, parity and quote-band functions, smoothing, PAVA repair, default grid, model-free bounds, the standalone frozen classifier, and the Q-to-P refusal are unchanged by AST comparison. The empirical evaluation harness and historical research records were not executed or modified. Natural current-head CI and its semantic gate remain necessary release evidence; these synthetic checks confer no admission or predictive-performance claim.
