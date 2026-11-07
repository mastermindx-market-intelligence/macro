# Grey Deer all-date exposure census — frozen v1

**Status:** retrospective descriptive research, accepted within its declared scope. No predictive claim, allocation, rank, gate or execution authority. Parent programme incomplete.

## Entry points

- [Findings, dated action map and acceptance boundary](../RISK_RADAR_META_CEO_ACCEPTANCE_2026-10-17.md).
- [Existing continuation masterplan, current §0A](../GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md).
- [Protocol](PROTOCOL_2026-10-17.json): frozen in commit ea26bc964314a80badcb29d836acfde06475f8d4 before the new outcome computation; SHA-256 317cd3b906438aa30995fb6a7bd24854af4c0cc83d094eb0726be35c045d3153.
- [Manifest](v1/manifest.json): source 3ab3382af89242c7b7fe8c65360bd883a7dd3504; executed code 4a06cd4a6b323312d2a59d6130efdb60997fe149; all 36 source and imported-method hashes.
- [Parent review](PARENT_REVIEW_2026-10-17.md): repaired findings, rejected Fabric advice and evidence limits.

## Artifacts and meanings

| Artifact | Content / qualification |
|---|---|
| v1/origins.csv.gz | 305,496 exposure/date rows: observed features, missing/immature reasons and separate future outcome labels. 8,486 SPY-reference dates × 36 ETFs. |
| v1/rotation.csv.gz | Absolute component returns alongside ratios and a shape label. measured_flow is always false. |
| v1/summary.json | Per-exposure and aggregate denominators; dependence-support components; verified independent episodes remain null. |
| v1/episodes.json | T12 recipient outcome episodes, post-outcome annotations. Not a new episode lifecycle or production event store. |
| v1/september_october_origins.csv | Every case date/exposure, September 1–October 15, 2026. |
| v1/september_october_rotation.csv | Every declared case ratio/origin/horizon; no future-best destination selection. |
| RECORDED_VERSIONS_2026-10-17.json | 128 selected source records over 32 origins; exact versions chosen under recorded Git committer cutoffs. Availability/delivery/execution unknown. |
| RECORDED_FIELDS_ADDENDUM_2026-10-17.json | Correct native state_ungated and gate_clamped read from the original blobs; initial spelling error is not native missingness. |
| CALENDAR_COVERAGE_ADDENDUM_2026-10-17.json | Original rule-calendar comparison, seven differences. |
| ../risk_radar_calendar_qualification_20261017.md | Documentary reconciliation of those seven closures, with 1994 document-hosting qualification; no shared calendar modification. |
| PEAK_AGING_ADDENDUM_2026-10-17.json | Observed 63/252-session peaks and drawdowns for selected case dates. |
| PEAK_AGING_CALENDAR_QUALIFICATION_2026-10-17.json | Reference-calendar verification and September 28 observation; original values agree and no off-reference source rows exist. |
| CI_OWNED_CLOSURE_2026-10-17.json | The new suite is reachable through the existing Grey Deer CI job, with no direct trigger gaps. Not a substitute for PR CI. |
| T13_METADATA_ADMISSION_2026-10-17.{md,json} | Completed metadata-only T13 intake; H2 missing 348/1,321 reference origins, batch-selection rule and actual remaining admission boundaries. Zero fits, sample regeneration or ledger writes. |
| CURRENT_BASE_COMPATIBILITY_2026-10-17.json | Current-main trial merge and owned-path comparison; generated updates are not a census rerun or a substitute for hosted CI. |
| risk_radar_september_october_2026.png | Descriptive figure; script plot_census_case.py uses the stored case CSV. |

The calendar addendum's original unresolved label is retained as the initial machine comparison; the separately dated documentary memo supplies its resolution. Neither file certifies worldwide exchange calendars, intraday executions or historical membership.

## Definitions that must survive reuse

close is the source's split- and dividend-adjusted total-return close. close_price is split-adjusted, dividend-unadjusted price. Returns and future loss labels use the former; structural drawdowns/averages use the latter. Both must be valid throughout a label's support. No forward fill or common-intersection deletion.

A damage-day is not a preemptive warning. A future-loss origin is not the time at which the loss was known. Recipient counts and pooled overlap groups do not establish independent crises. Positive price ratios do not establish investor flows. A trailing peak can expire without recovering an older peak.

DIA, BIL, SGOV and ARKK end October 14 at this pin; all other declared prices end October 15. All scanned history is exploratory. Stage-1 and stage-1b remain frozen and were not rerun; prior failed claims stay failed.

## Validation and reproduction

Run only the focused synthetic suite when checking implementation:

```bash
python3 -m pytest -q tests/test_grey_deer_exposure_census.py
```

Reproduce the figure from the stored case output (requires pandas and matplotlib):

```bash
python3 research/grey_deer/all_date_census/plot_census_case.py \
  --input research/grey_deer/all_date_census/v1/september_october_origins.csv \
  --output /tmp/grey-deer-case-figure.png
```

The frozen run command, for source provenance, was:

```text
python3 scripts/research/grey_deer_exposure_census.py
  --protocol research/grey_deer/all_date_census/PROTOCOL_2026-10-17.json
  --expected-protocol-sha 317cd3b906438aa30995fb6a7bd24854af4c0cc83d094eb0726be35c045d3153
  --source-repo <isolated source checkout>
  --output research/grey_deer/all_date_census/v1
```

The runner refuses an existing output directory and mismatched source/method/protocol hashes. Read the frozen outputs for these results. A changed universe, source vintage, configuration or scientific claim needs its own declared revision and output; it cannot overwrite v1 or become an untouched holdout.

The next fitted research document is a proposed design with execution bindings outstanding. It is not a release, a new trial ledger or a claim that forecast qualification has been completed.
