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

## Executed qualification and latest-date behavior

The selected rates/RIC/yield suites now pass 140 tests (301 warnings). New tests
proved and repaired two concrete source defects: stale inputs cannot become fresh
through an older board date, and flat batch responses without contract identity
cannot be copied into many apparently distinct futures instruments.

The exact held #7521 fed_path/RIC source at
8da98209ad4a34450745780666c48b6999f2bfb2 was privately composed with the additive
RIC field. Qualified policy evidence exercised its normalizer; ALL legacy RIC
fields stayed exactly equal. This is same-author synthetic compatibility proof,
not a non-author review, permission to merge, or mutation of that held carrier.

A native fetch at 2026-09-24T09:54Z returned 65 ZQ dated rows and one SR3 dated row.
The Yahoo client was installed only in this operation's isolated evidence venv,
as already declared by requirements.txt (yfinance>=0.2.50); no shared interpreter
or production source was changed. Exact observed versions: Python 3.14.7,
yfinance 1.7.0, pandas 3.0.5. The earlier system-Python attempt failed at import,
before a market-data request, and its receipt is preserved separately.

Current-day ZQ attribution correctly refused the incomplete daily bar. SR3
refused insufficient endpoints. That is NOT a successful current market call.
The producer, native validate/upsert path and real RIC consumer ran only against
an isolated evidence store; natural deployed production is still unproven.

The reader now preserves a separately labelled last_completed_observation_context
only when current refusal is the explicit incomplete-bar condition. It uses the
same two captured tables without rereading them, keeps current status unavailable,
and exposes the older observation dates plus false historical/trading authority.
Corrupt, stale or future-source failures do NOT silently fall back to older data.
Completion here means the observation date preceded the capture's New York
calendar date; exchange settlement remains unverified. This gives useful dated
context without presenting yesterday's observation as a fresh current quote.

Evidence root: /Volumes/Mastermind/evidence/rates-policy-constituents-20260924-sol-002/.
Initial native receipt: native-564f86e8/receipt.json (missing dependency, no fetch).
Native source receipt: native-564f86e8-env1/receipt.json (isolated real-input path).
Compatibility: held_7521_composition.json; scripts and environment freeze retained.

## Real captured observation result (not a forecast)

On the same provider capture, the separately dated ZQ context spans September 22
to September 23, 2026. Under the incumbent interpolation convention:

| Policy-path horizon | Published path change | Matched-contract contribution | Roll |
|---|---:|---:|---:|
| 1 month | -0.12 bp | -0.124741 bp | 0 bp |
| 3 months | +3.50 bp | +3.499985 bp | 0 bp |
| 6 months | +5.75 bp | +5.750275 bp | 0 bp |
| 12 months | +12.00 bp | +11.999893 bp | 0 bp |

The small residuals are the incumbent published curve's four-decimal rounding,
not an unexplained market contribution. These are policy-path interpolation
horizons, NOT Treasury maturities or forecast holding horizons. The one-month
basket includes a reference period already underway. No row is a causal shock,
a forecast issued before the move, or proof of forecasting skill.

The CURRENT ZQ result remains unavailable for the forming September 24 daily bar;
SR3 remains unavailable because the retrieved source has only one dated endpoint.
The earlier context is separately labelled, never substituted as a live result.

Retained native frames also traversed the actual shared run_adapter -> store ->
RIC path in an isolated replay: status ok, 132 TABLE rows across four tables,
no error, and family outputs exactly equal to the direct read. This count includes
companion rows and is not an independent-observation count. No new network request
or production mutation occurred.

Full compact qualification: RATES_POLICY_CONSTITUENTS_PROOF_2026-09-24.json.
Production source commit: 5c92d778ae73f557fd4d3d91ea99aa175331e388.
Board SHA256: 45cd5d38ff0c1bf01e83e20e98d6437f4a619543cd4436b0f05f293f8dbbc650.

## Next scientific dependency

The existing MRI owner already supplies ALFRED initial-print selection through
engine.release_forecast.knowable_series and data/fred_vintage/vintages.parquet.
Its documented filter uses realtime_start <= a date. That date-level filter alone
is not an intraday pre-release knowledge receipt, nor an archived market-consensus
estimate. Preserve MRI and its experiments; qualify the existing release-time and
consensus owners before any surprise-response rate model. No claim that every
other company archive is absent is made by this bounded source inspection.
