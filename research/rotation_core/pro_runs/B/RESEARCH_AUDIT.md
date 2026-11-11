# Research audit and deviations

## Rule integrity

Ten allocation rules were frozen before any strategy outcome. No thresholds,
lookbacks, costs, group memberships or candidate rules changed after outcomes.
The preregistration commit is `ba5ae1e353c6f9738bbf8936b9032e71c747b9ba`.
Pre-outcome diagnostics were clarified at `da384adb882181ecd33d3a0802f8c2d22f53d1d9`;
the initial source and synthetic checks at `48f6f195579db5d734b4e2c0c587e4c25693bdd3`;
missing-data identifiability was clarified at `85f299a57d3f36fad9994a69d84853e3f07a5604`.

The first historical run aborted in the held-missing-input guard before producing
strategy results. French's official TXT counterpart confirmed the CSV holes. The
repair isolates unknown returns instead of zeroing them; later normalized weights
can become known after exact rebalancing. R7/R8 propagate feasible state sets.
Unknown full-era paths retain NA and p=1; descriptive segments are separated.

## Source and interpretation review

A distinct native methodological adviser reviewed the frozen design and source
without outcomes, then checked the derived result tables after execution. This
was an independent methodological read, not a GitHub approval or production gate.

Findings adopted before results: true stock-EW is absent; common-sample H1 is
required; exact next-close accounting; passive C/D control; conservative vintage
labels; per-field episode missingness; PRE exit lead/follow rows; no NaN-as-negative
lead classification; follower status depends on the preceding relative move.

After results, a table-formatting repair created an explicit 30-slot full-era file
with NA for nine incomplete paths and a separate segment file. No return or
allocation changed. The source parser discards later date rows before converting
returns; an adversarial invalid-numeric future-row fixture proves this behavior.

## Executed validation

Twelve synthetic integrity tests pass: cutoff-first parse, missing sentinels,
next-close trade/first earned return, cost-era boundary, both sides of a sleeve
switch, pretrade weight drift, causal exposure, monthly known dates/source gaps,
strict held-missing failure, unknown-return preservation/weight restoration,
known 100% exposure during ambiguous C/D states, Holm arithmetic/initial drawdown,
and deterministic paired block behavior (some test cases cover multiple assertions).

An independent vectorized implementation reproduces every identified daily
R1-R4 return exactly (maximum absolute difference zero); the receipt lists row
counts. E49 was independently recompounded from the existing cutoff-checked audit
cache: its large gross return is not a percent-unit or annualization mistake. This
does not establish exact stock-EW identity or investability, and no constituent
evidence attributes its magnitude to a particular microstructure mechanism.

## Acceptance limits

The final mathematical review identified a limitation in the frozen cost
convention, not a divergence from its implementation. With target equity weights
w, pretrade equity weights p and per-side cost c, the implemented fee fraction is
f0 = c * sum(abs(w - p)). Exact post-fee traded-notional financing would solve
f = c * sum(abs((1 - f) * w - p)). The difference is second order in c and is
not universally conservative. The original outcomes are retained, and both
README and report disclose this approximation. No allocation or numerical cost
formula changed after outcomes. A descriptive module docstring was corrected to
avoid an exact self-financing claim.

The manifest's code_sha256 records the source at the final numerical run.
Post-run documentation changes are separately hashed in that manifest; these
cover the simulator docstring and report presentation, not the numerical engine.

The record is a research return. No primary superior-return test passes. Missing
source cells, unavailable stock-EW data, current-vintage macro, theoretical
portfolios and short early macro samples remain unresolved; favorable descriptive
episodes do not cure them. The programme can adjudicate this return and freeze a
second protocol without promoting any allocation rule to live use.
