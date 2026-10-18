# T13 metadata admission — 17 October 2026

**Disposition: metadata read complete; research execution not admitted.** This dated addendum belongs to the existing Grey Deer programme and T13 intake. Sol is the current methodology owner. It preserves the original [T13 draft](../PREREG_DRAFT_T13_MECHANISMS_2026-10-13.md), its proposed 12 cells, and T14/T19. It does not create a new claim, trial, publication or policy owner. No feature–outcome join, fit, price hydration, T12 regeneration, registration or forecast issuance occurred.

## Immutable source and result

The read used `git show 3ab3382af89242c7b7fe8c65360bd883a7dd3504:data/fred_vintage/vintages.parquet` into memory. The 233,300-byte source has Git blob `f029ac2c7429196747bf826b8f2647e4996848b5` and SHA256 `4f44f23f00c15712fd67032e99def458b97a85cbff1856a1e3951b13a063e52f`. It contains 16,532 rows with `series, period, value, realtime_start, realtime_end`. The [machine receipt](T13_METADATA_ADMISSION_2026-10-17.json) records the exact schema and all counts.

The pinned collector `collectors/fred.py`, blob `3773441b958e202bceea8746426d27e56545f13a`, requests `output_type=4` (lines 139–195): initial-release-only rows. This supports the cached release-date interpretation. It does not establish intraday first availability, actual programme delivery, or a full matrix of subsequent revisions. The collector can replace the store wholesale and allows partial success (lines 153–225); the presence and hash check must therefore be repeated on any different source bytes before admission.

| Metadata | H1: THREEFYTP10 | H2: STLFSI4 |
|---|---:|---:|
| Rows / distinct observation periods | 2,633 / 2,633 | 205 / 205 |
| Observation-period range | 2016-04-01–2026-10-09 | 2022-11-11–2026-10-09 |
| Cached release-date range | 2016-08-11–2026-10-13 | 2022-11-17–2026-10-14 |
| Release dates | 361 | 205 |
| Release dates containing multiple periods | 361 | 0 |
| Largest release batch | 68 periods | 1 period |
| Origins with a prior cached release, on the 1,321-date reference calendar | 1,321 | 973 |
| Origins without any prior cached release | 0 | 348 |
| First origin with a prior release | 2021-07-06 | 2022-11-18 |

For both series: zero missing value cells, missing clock cells, release dates before observation periods, end-before-start clocks, duplicate rows, duplicate period/release rows, or conflicting period/release values in these pinned bytes. These are structural checks, not an assessment of completeness against the provider's full archive or an endorsement of a predictive mechanism.

The reference dates are the frozen census's SPY dates in 2021-07-06–2026-10-07. **They are not a verification of T13's Massive RAW price input.** Presence counts precede warm-up, maturity, staleness, episode selection and baseline-common-support restrictions. They are not counts of eligible fitted rows or independent episodes.

At the last reference origin, October 7, the latest admissible H1 release is October 6, containing September 28–October 2 observations; H2's is September 30, containing the September 25 observation. Same-day October 7 release stamps are excluded. These dates are source metadata; no feature value was joined to an outcome.

## Methodology decisions made by the current seat

Keep H1 as the **Kim–Wright** ten-year term-premium level and H2 as the STLFSI4 level, preserving their positive precommitted directions. THREEFYTP10 must not be renamed ACM. H3–H9 remain ineligible.

A date-only `realtime_start` must be strictly earlier than the origin's calendar date. For the next executable freeze, choose the maximum eligible release date and then the maximum observation period within that release batch. This resolves a real ambiguity in the draft: “latest release” alone is not a unique row for H1. Duplicate/conflicting identity rows require an explicit refusal or qualification, never whichever row happens to appear last. This selection rule is specified before any H1/H2 fitting; it has not generated a model input/output table here.

The first 348 STLFSI4 origins abstain. Do not fill them from the revised series or quietly change the July 2021 sample start. A declared, separately reported coverage revision may be considered before execution; it cannot convert missing historical availability into knowledge.

## Why fitting is still not admitted

1. **Source-purpose disposition remains unresolved.** The upstream `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md` records FRED model use as UNKNOWN / not a source. The downstream `PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md` rows 4/5 say “recorded” for internal fitting, but its own upstream-condition rule and G6 require a model-use determination. The current [FRED terms](https://fred.stlouisfed.org/legal/) were inspected on October 17; the stated internal-use permission is subject to separate prohibited-use terms. This checkpoint does not resolve that conflict by inventing a license interpretation or substituting an endpoint. Existing internal metadata was inspected; no permission request was sent to another person.
2. **Actual T12 input and sample identity are unverified.** Preserve Massive RAW SPY, the 2021-07-06–2026-10-07 window, expected 1,321 normalized rows and SHA256 `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb`. T12 code blob is `0a0eecb98e743b780db1ee3b0382e268d592fa67`; spec blob `fe68838867982e845297aeb0daf518e0387120f9`; seed 20261013, horizons 5/10/21, three controls and 63-session exclusion stay unchanged. No Yahoo substitution. The canonical sample digest is the SHA256 of `json.dumps(sample, sort_keys=True).encode()`, without a CLI trailing newline, after actual qualified input read. No digest is claimed here.
3. **Execution/inference binding is incomplete.** T12 supplies episode windows, not a full daily fitted-origin table. The runner, exact sample projection, calibration, minimum evidence and counted fits must be frozen. T13 leave-one-episode-out can train on episodes that occur later in history; it is a diagnostic validation design and does not demonstrate chronological executable lead.

Current Sol owns these methodological decisions; no imaginary outside methodology approval is awaited. Data-purpose qualification, immutable input identity and existing numerical policy authority remain actual boundaries. A failed intake is useful evidence; it is not a null forecast result or a burned fitted trial.

## Transport and reproducibility

The delegated worker submitted only a read-only Python dependency probe through `remote_desktop_commander`; that tool aborted after 1,036 seconds without a process handle. Whether the probe completed is unknown. No parquet-analysis or modifying command was submitted through that transport, and no metadata result from that worker was accepted. The parent completed the bounded read through `studio_direct`, using the existing Python/pandas runtime. The worker is stopped; no watcher remains.

To reproduce the source metadata without running an estimator, read the pinned bytes through `git show`, load them with `pandas.read_parquet(BytesIO(raw))`, verify the SHA256, and group only the named two series by observation period and release date. For the presence counts, project only `ticker,date` from frozen `v1/origins.csv.gz`, select SPY in the declared window, and count dates strictly after each series' earliest cached release. Do not read outcome columns into this check. The recorded last-origin batch uses maximum release strictly before October 7 and maximum period within that batch.

**Next admitted work:** finish the existing source carrier and unchanged-policy consumer comparison; resolve the exact price/source-purpose bindings before any T13 join or fit. Preserve the original W5 refusals and wait for genuine issuance through its existing owner before prospective grading.
