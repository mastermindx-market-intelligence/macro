# RD2: contract-preserving policy-path change

Parent: WS:RATES-INFLATION-COMMAND; continuation of Macro PR #7909.
Operation: rates-policy-constituents-20260924-sol-002.
Source base: b7d6914db7d8ef6e810500926764e18b85f01348.
Procedure: Mastermind 1a7d400294b0d37c460b963b8865b40a23173b58,
compatible Skillpack 1.0.1 / bootstrap 1.
Chairman standing delegation and current continue instruction authorize this slice.
Direct principal reason: PRINCIPAL_JUDGMENT for contract/clock semantics and
LOWER_TOTAL_OVERHEAD for the bounded producer-to-consumer implementation.
No worker has started. No new model trial or provider purchase is authorized here.

## Capability and boundary

Extend the existing rate_futures collector/store and RIC builder to distinguish
changes in the SAME contracts from rolling-horizon reweighting. Preserve existing
numeric horizon values; add constituent identity, weights, reference periods,
capture clocks and a cross-file generation token. Do not create another collector,
archive, calendar, forecast service, score, trial ledger or control plane.

The extra table stays inside data/rate_futures under the existing adapter. It is
latest-vintage measurement evidence, NOT an immutable historical knowledge archive.
A source capture timestamp is not the publisher's historical release timestamp.
Generation mismatch, missing endpoints/components, stale/future/incomplete bars,
unsupported schema and incompatible rate families must withhold attribution.

For weights w and rates r, the symmetric exact attribution is:
change(w*r) = average(w)*change(r) + average(r)*change(w).
Absent entering/exiting quotes at either cut mean incomplete attribution; never
zero-fill a missing rate or renormalize partial coverage into complete coverage.

## Exchange conventions verified September 24

ZQ averages EFFR across the named calendar month, including nonbusiness days.
SR3's named month begins its reference period on its third Wednesday; the period
ends, exclusively, on the third Wednesday three months later. Its final rate is
compounded, not an arithmetic average. Delivery month is not named contract month.
An in-progress reference period mixes realized fixings and forward expectations;
matched-contract change is NOT a pure future-policy shock.

Primary sources:
https://www.cmegroup.com/education/courses/understanding-stir-futures/introduction-to-fed-fund-futures
https://www.cmegroup.com/education/articles-and-reports/understanding-sofr-futures
https://www.cmegroup.com/education/articles-and-reports/three-month-sofr-futures-rates-and-future-sofr-levels

The incumbent whole-month + centre-offset coordinates remain explicitly labelled
legacy approximations. This slice does not silently change them to date-exact
forward-rate estimates, strip futures risk premia, infer meeting probabilities,
or treat Yahoo daily Close as authenticated exchange settlement.

Held #7521/#7593 remain unchanged and unaccepted. The new RIC field is additive,
outside their policy normalization and all existing scoring/stance calculations.
