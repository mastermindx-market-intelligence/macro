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

## Adversarial repair on the same carrier

The published continuation at 100cf1edd70ebbdebc26348bd694aac74efe8f70
reconciled the formerly dirty writer: local/remote source was clean, no external
child or unresolved modifying effect was recorded, and candidate repair was the
next authorized action. PR comment 5812272237 records same-carrier continuation;
no replacement branch, worktree, collector, provider or review identity was created.

Exact-source cross-check 5812118161 reproduced two release-blocking defects:
finite but corrupted extreme quotes could overflow bp arithmetic and return an
available result containing Infinity/NaN; an empty second-family batch could
throw away valid first-family output. Six new cases preserve the initial RED,
then prove the repaired native collector/Parquet/RIC path. The empty-family
regression was strengthened to call the actual _download retry layer with a
synthetic vendor response; this caught and repaired the terminal empty-response
exception, not merely an unreachable post-download guard. Only the typed empty
outcome is isolated; other download exceptions and unidentified nonempty batches
still fail. The existing retry budget and backoff owner are unchanged.

Current local qualification: 147 passed, 301 warnings across test_rates_command,
test_fed_path and test_yield_momentum. The old and repaired consumers returned
identical objects on the same retained real-quote capture at its recorded
2026-09-24 evaluation cut, with strict JSON serialization and unchanged four
Parquet hashes. This replay made no new vendor request and did not alter a live
store. It is not an independent review, live deployment or forecasting result.
The existing proof JSON preserves prior evidence and appends post_review_repair
with source/log hashes, native parity and the following input-eligibility audit.

## Next forecasting-input gap: first prints are not the GDPNow update path

At parent research snapshot 748067a3631959e2dd6ffe25ebc7675ed82395ee, the existing
initial-release vintage store contains 41 GDPNOW rows and 41 distinct reference
quarters, versus 356 CPIAUCSL, 356 CPILFESL, 357 PAYEMS and 903 ICSA periods.
Those are metadata counts, not new empirical trials. GDPNOW availability dates
in that named file end 2026-07-30; it cannot reconstruct within-quarter revisions.
The nearby current-vintage GDPNOW series cannot repair that historical knowledge
loss by backfilling its latest values. Date-only ALFRED vintage labels also do
not establish knowledge before an intraday release.

The source capability already exists: collectors.fred.fetch_all_vintages uses
ALFRED output_type=2; the first-print collector uses output_type=4. Reuse that
source owner instead of creating a new GDPNow collector. The current native
source environment reports FRED_API_KEY unavailable (presence only checked; no
credential value read or exposed). This is local source eligibility, not proof
that existing CI/data-owner environments lack their authorized credential.
The dedicated release-target cohort/normalizer must not be widened casually:
GDPNow is a changing nowcast feature, not the CPI/PAYEMS release-target contract.
Related held #7165 remains a distinct date-level Macro Turnaround research owner;
its reviewed code and source/continuity gates are not changed or reimplemented.

Primary public-source checks on 2026-09-24:
- https://fred.stlouisfed.org/docs/api/fred/series_observations.html documents all-vintage versus initial-release output.
- https://fred.stlouisfed.org/series/GDPNOW labels the FRED series quarterly.
- https://www.atlantafed.org/research-and-data/data/gdpnow describes multiple updates per month, publisher tracking archives, and update times following underlying data releases. Its pre-live deep archives must not be treated as contemporaneously public forecasts.
- https://www.atlantafed.org/terms-of-use separates Bank and third-party rights. Do not infer commercial redistribution permission from a public workbook link.

No workbook was imported or republished. The existing MRI artifact explicitly
reports street_consensus unavailable; a residual versus an internal benchmark
must remain a separately named estimand, never be relabelled a market surprise.
The next scientific slice must bind complete same-quarter vintage updates and
conservative knowledge cuts before registering a new rates hypothesis. No new
model fit, forecast, trial, scoring authority or retrospective holdout reset
occurred during this repair and metadata audit.

## New York contract-calendar repair

A later same-author adversarial check found one additional source-clock defect before
independent acceptance: the collector generated its live contract strip from the UTC
calendar date. At `2026-10-01 01:00 UTC`, New York was still `2026-09-30 21:00`, so a
month-end manual run could request the October-forward strip several hours before the
U.S. market calendar actually rolled. The new regression first reproduced the wrong
`2026-10-01` as-of date, then passed after contract generation was bound to
`America/New_York`. Capture timestamps remain UTC; only contract-calendar identity is
localized. The selected suite is now 147 passed, 301 warnings. No vendor request,
model trial, production-store write or forecast promotion occurred in this repair.
