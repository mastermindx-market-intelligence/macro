# Taiwan / India observed GDP: bounded integration handoff

**Prepared:** 2026-10-20 20:44 UTC  
**Status:** implementation design and local diagnostic only; not an acquisition receipt, production admission, patch application, or release gate.  
**Workspace inspected read-only:** `/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018`.

## Recommendation

Extend the existing country-input collector and its admission/view path. Do not add a second adapter, a render-time request, or a fabricated FRED mapping. Taiwan's exact official August release is already fetched by the existing collector. Its parser currently extracts only annual forecasts. India's national PDF needs one explicitly registered source in the same injected-fetch path.

Keep the currently honest release independent. Five connected changes are required for a complete follow-up: national-release parsing; quarterly admission and revision selection; preserved evidence in the assessment view; a distinct national-release evidence presentation; and tests covering the entire collector-to-render path. A parser-only or allowlist-only patch is insufficient.

## 1. Observations supported by the prior source investigation

| Field | Taiwan | India |
| --- | --- | --- |
| Provider | Directorate-General of Budget, Accounting and Statistics (DGBAS) | National Statistics Office, Ministry of Statistics and Programme Implementation (MoSPI) |
| Published rate | 12.93% real GDP year over year | 7.8% real GDP year over year |
| Publication date | 2026-08-14 | 2026-08-31 |
| Normalized calendar quarter | 2026-Q2 | 2026-Q2 |
| Reference interval | 2026-04-01 through 2026-06-30 | 2026-04-01 through 2026-06-30 |
| Native quarter | 2026 Q2 | Q1 FY 2026–27 (April–June 2026) |
| Comparison | Same quarter of previous year | Q1 FY 2025–26 (April–June 2025) |
| Source release label | Preliminary Estimate | Quarterly Estimates; subject to revision |
| Existing status vocabulary | provisional | provisional, with the native label separately retained |
| Price convention | Real GDP; do not infer the precise reference-year basis from a separately listed SA table | Constant 2022–23 prices |
| Revision context | 0.01 percentage point above the prior advance estimate, implying 12.92% previously | New base-2022–23 series, released 2026-02-27; August publication also revises prior annual and quarterly estimates |
| Seasonal basis safe to claim from retained evidence | Headline y/y is distinct from the explicitly SA annualized sequential series. August headline's precise adjustment label still needs native-source qualification. | No explicit SA/NSA label found for the headline in the reviewed release. Preserve that limitation. |
| Inputs available | Published rate; no qualified pair of native GDP levels retained in this investigation | GDP constant-price levels: ₹8,136,153 crore current; ₹7,546,230 crore same quarter previous year |
| Useful cross-check | Do not confuse headline 12.93 with the separately published 5.70% q/q SAAR | (8,136,153 / 7,546,230 − 1) × 100 = 7.817453218362025%; rounds to the source's 7.8% |
| Next official event found | 2026-10-30, 16:00 local: Q3 advance briefing | 2026-11-30: Q2 FY 2026–27 (July–September 2026) |

The displayed metric should use the **published rate**, including its published precision, while retaining the India levels as a reproducible cross-check. The India observation is calendar Q2 but fiscal Q1. It must never be described simply as India's Q2 without the calendar convention. Neither observation is an IMF/RBI projection.

### Primary sources and retrieval evidence

- Taiwan release: <https://eng.dgbas.gov.tw/News_Content.aspx?n=4438&s=236587>. Official publisher text was retrieved through the search index, including the August 14 date, the preliminary Q2 section, 12.93% y/y and 5.70% SAAR. Direct opens failed. This is research evidence, **not a retained HTML wire artifact**.
- Taiwan Chinese corroboration: <https://www.stat.gov.tw/News_Content.aspx?n=2677&s=236591> and <https://www.stat.gov.tw/News_Content.aspx?n=3703&s=236591>.
- Taiwan next briefing calendar: <https://www.stat.gov.tw/ConferenceInfo.aspx?n=4672&s=49391>.
- India official release PDF, successfully opened and extracted by the web reader: <https://www.mospi.gov.in/uploads/latestReleases/latest_release_1788172583113_d65a77cf-240e-4491-82ee-59f78618fa41_Press_Note_on_GDP_Estimates_for_Q1_2026-27.pdf>.
- India official methods PDF, successfully opened: <https://www.mospi.gov.in/uploads/documents/pressRelease/1789976245319-Sources%20and%20Methods%20for%20Compilation%20of%20National%20Accounts%20Statistics.pdf>. Printed Table 30.1, page 343, gives the fiscal-quarter convention; Table 30.4, page 345, gives publication cadence.

India's release has the headline on web-extracted page P3, revision/next-release discussion on P7, and constant-price Statements 1 and 2 / GDP row on P8. **Confirm physical PDF page numbering against the acquired bytes before persisting a browser `#page=` link**; those web page indices are not a final physical-page contract.

No native source bytes or source-wire SHA-256 were retained by this worker. Do not derive a source hash from search snippets or from the web reader's extracted text.

## 2. Existing sanctioned code path and exact gaps

### Acquisition already exists

`collectors/intl_macro.py::IntlMacroAdapter._refresh_country_inputs` injects `fetch_bytes` into `collect_country_inputs`, reads previous `data/intl_macro/country_inputs.json`, merges, then atomically replaces that file.

The injected fetch uses existing `self.http_get`, one retry, a 20-second request timeout, streamed 65,536-byte chunks, a maximum byte budget, and a 45-second elapsed budget checked while streaming. Do not describe the elapsed check as a guaranteed hard wall-clock deadline. No render-time acquisition is needed.

`collectors/intl_country_sources.py` already defines `TW_PAGE` as the exact official August 14 URL. `collect_country_inputs` fetches it under a 4 MB ceiling. The current `parse_taiwan_release` bounds decoded HTML at 2 million characters, requires the August date, and extracts annual 2026/2027 forecasts. It emits no quarterly observation.

### Admission independently blocks GDP in three places

In `collectors/intl_country_sources.py`:

1. `merge_country_inputs` accepts official metric keys only `inflation` and `policy`.
2. `_valid_incoming` assigns `% y/y` only to inflation; GDP falls through to `%`.
3. Every official metric period is validated with the monthly-only `_source_clock(..., monthly=True)`.

Its current period ordering also assumes monthly strings. Changing only the key allowlist would expose the existing erroneous GDP validation branch, accepting monthly `%` records.

### Existing view can display a scalar, but loses national evidence

`lib/intl_country_assessment.py::_period_end` already understands `YYYY-Qn`. `_metric` already prefers an admitted official GDP receipt over the stored-series fallback and uses a 220-day observation-age horizon for GDP.

However, `_metric` carries detailed `evidence` only for the stored-series fallback. A national receipt currently becomes a value, period and source link; its publication date, vintage, native fiscal label, price base and retrieval metadata disappear from the view.

`lib/intl_country_inputs.py` deliberately has stored GDP mappings only for JP/KR/AU/GB/EZ. Those mappings require the actual configured FRED identity and five consecutive quarterly level observations. Do not add TW/IN to that path to disguise national release observations as a stored series.

### Existing template would make incorrect claims if reused verbatim

`templates/intl_country_cockpit.html.j2`:

- The note for any detailed evidence says acquisition dates were not retained.
- Each macro evidence block unconditionally says **Seasonally adjusted**.
- The block expects a stored-series identifier, observations and a series request URL.
- Vital and ledger values use two decimals, even when the source rate is published to one.
- The ledger shows normalized period only.

Add a distinct branch for national-release evidence. Keep the current stored-series explanation for stored-series evidence. Show India as “Apr–Jun 2026 · FY 2026/27 Q1” alongside normalized internal calendar Q2. Preserve the published 7.8% precision. Unknown seasonal labeling should be stated honestly without inventing NSA or SA.

## 3. Minimal implementation specification

### Parser and fetch integration

Use one small national-GDP parser module or equivalent focused functions in the existing collector. Register the exact provider, URL, publication date, native period and expected measurement convention for each release.

For Taiwan, parse the observed preliminary-Q2 section from the **same bytes already fetched for the forecast**. Qualify observation and forecast independently so a failure in one does not discard valid evidence for the other. Require the release identity, the preliminary section, same-period-previous-year semantics and a unique rate. Reject accidental matches to the outlook paragraph, the previous advance rate, or the SAAR series. Exclude script/style text. Hash the original bytes, not decoded/re-encoded text.

For India, use the existing `pdfplumber` dependency and bounded-PDF parsing pattern demonstrated by `collectors/intl_weo.py` and `collectors/intl_policy_sources.py`. Check PDF signature, byte/page/text limits, release date, fiscal quarter, base year, constant-price GDP row, column order and headline agreement. Retain Statements 1/2 identity and the verified physical page. Reject the nominal GDP row and the old-base series. The 7.8 rate is reported; the level pair is supporting calculation evidence.

### Receipt fields

Keep the existing outer metric contract:

`metric=gdp`, `unit=% y/y`, `status=provisional`, `period=2026-Q2`, `provider`, `source_url`, `value`.

Extend its evidence metadata with:

- schema/kind identifying an official national release;
- publication date and exact native release status;
- native reporting label, calendar start/end and comparison interval;
- real/nominal and growth-basis identity;
- explicit price base when verified;
- seasonal basis plus an explicit unknown/not-stated value;
- published precision;
- original source URL, verified source table/page and parser version;
- actual acquisition `retrieved_at`, actual first admission clock and original-byte `source_sha256`;
- for India, current/prior native levels with unit, base and native periods;
- prior/replaced release identity where a reviewed revision supersedes it.

Do not invent values for missing wire hashes, acquisition timestamps, page identifiers or seasonal labels. The research findings above are not sufficient to instantiate a production receipt.

### Admission and revision selection

Add an explicit GDP branch: exact quarterly period validation; finite numeric published rate; % y/y; observed/provisional only; real GDP identity; completed reference period; source identity; publication no earlier than the reference-period end; valid acquisition/publication order; qualified source metadata. Do not loosen the monthly CPI/policy branches.

Compare the normalized quarter first and the registered publication/revision identity second. Do not let arrival order replace a newer reviewed vintage. A changed payload at the same URL/publication identity should retain the last qualified value and raise an explicit review-needed error unless the corrected publication has been qualified. A later registered publication may carry a reviewed same-quarter revision.

Preserve first-admission custody during render/load. Existing `load_country_inputs` already calls `merge_country_inputs(..., preserve_custody=True)`; GDP must honor that boundary.

### Hash and retention custody

`collect_country_inputs` and the existing policy/WEO collectors hash actual fetched bytes. The existing `sources` history keys by URL and SHA-256, so distinct payload hashes can remain distinguishable. The merger bounds that history at 100 entries and the serialized country-input file at 1.5 MB.

The inspected collector stores receipts, **not the original wire payloads**. Before claiming a replayable source audit, retain the exact bounded HTML/PDF fixture through the project's established evidence-artifact location and reconcile its hash with the receipt. Do not create a parallel source ledger or duplicate acquisition service. A normalized-text or row hash is an additional parser aid, never a substitute for the raw artifact hash.

## 4. Required verification for the follow-up

1. One Taiwan fetch supplies independent forecast and observation parsers; parser output keeps 12.93% observed separate from annual forecasts and 5.70% SAAR.
2. India fixture verifies 7.8%, current/prior constant-price GDP levels, base 2022–23, fiscal Q1/calendar Q2, native units and actual PDF page/table.
3. Wrong nominal row, old base year, wrong quarter, forecast text, duplicated/conflicting rates, malformed/future dates, missing hash or bad acquisition clocks fail qualification.
4. Refresh failures preserve prior good GDP; a TW failure cannot remove India/BIS/WEO/policy data.
5. Quarter ordering and same-quarter revisions are tested; same-publication changed bytes do not silently overwrite a qualified observation.
6. The full collector → merge → loader → assessment → template test displays publication, native period and limitations. No false SA claim, missing-acquisition claim, or fiscal/calendar mislabel.
7. Source hash uses raw bytes. Render/load does not mint a new retrieval or first-admission timestamp.
8. Existing stored GDP, official precedence, CPI/policy and forecast archive tests remain green.
9. Production-like build uses retained real fixtures plus bounded actual acquisition evidence. Synthetic parser tests alone do not establish source admission.

Existing `tests/test_intl_country_cockpit.py` covers direct official-GDP precedence and stored-series trace validation, but its direct-view fixture bypasses the collector/merger gap. A repository test search found no direct reference to `parse_taiwan_release`.

## 5. Cadence and maintenance

Register actual releases instead of silently advancing by scraping an index. Taiwan's next Q3 advance release and India's next fiscal-Q2 release need new qualified vintages when published. Preserve Taiwan's advance/preliminary/revised distinction and India's base-series/revision convention.

The adapter's 45-day stale horizon and assessment's 220-day GDP observation horizon are not publisher release schedules. The read daily workflow declares an 18:30 America/New_York cadence through DST-paired crons, but this worker did not establish or observe the full workflow-to-collector invocation chain. No claim is made about the latest production acquisition run or CI state.

## 6. Local evidence and exact completion state

- `collector_snapshot.py`: complete read-tool text snapshot of the 404-line current collector, not a raw source-data artifact.
- `admission_probe.py`: AST-executes only selected unchanged pure functions from that snapshot and inspects the merge allowlist. No production imports or network.
- Probe run: **6 checks passed**, process exit 0.
- Snapshot text SHA-256: `9e51a27575659140fed98b7d5cc88d11e1812e8994b7b24c0dab13f1ae82b5c7`. This identifies the local code snapshot only.

No remote process, edit, source/config write, production admission or release action occurred. No new public-source request was made during this implementation-design follow-up. All native file-search handles inspected are complete.

The earlier Firecrawl scrape of the Taiwan URL returned “aborted by user after 18863.1s”; no content, job ID or completion receipt was returned. Its server-side completion remains unknown. It was not repeated, rerouted or used as acquisition evidence.

### Next three steps

1. Parent reconciles the earlier effect-unknown read and checks whether exact source bytes already exist in established evidence storage; obtains missing bytes only through an authorized existing acquisition path.
2. Implement the focused collector/admission/view/template change and the nine verification cases above in a separate coverage follow-up.
3. Run a retained-fixture and actual-receipt build, review the national-release evidence at desktop/mobile sizes, then admit and publish the two observations with their true custody.

**Why no production-ready patch is attached:** the current missing actual source artifacts prevent fixture-qualified parser implementation, and the source/view boundary requires several connected changes. The local diagnostic proves the real gaps without pretending a partial parser or merge edit completes the feature. This does not block the honest current UI release.

