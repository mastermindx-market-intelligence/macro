# International macro dashboards — data contract

## Scope

`japan.html`, `south_korea.html`, `euro_area.html`,
`united_kingdom.html`, and `india.html` are five views over one
`international_macro_dashboard.v1` contract. The shared engine is descriptive.
It does not score individual stocks and does not expose Prophet.

The Euro Area route means the currency union, not the European Union. Current
official Eurostat adapters use EA21 composition in 2026. Any legacy EA19/EA20
fallback is identified in provenance. STOXX Europe 600 is broader-Europe market
context and never substitutes for euro-area macro data.

## Normalized contract

Each route receives:

- regime: growth, inflation, confidence, liquidity, recession stress, and the
  engine’s data-limited state;
- decision: a transparent 0–100 descriptive score, component receipt, current
  posture, action, and transition conditions;
- history: the same descriptive score over the latest 60 sessions;
- market: local index and FX context;
- policy and verified central-bank calendar;
- risk: the existing market-specific calibrated forward-pullback probability,
  its measure, scare families, and trajectory;
- metrics: normalized numeric value, display unit, and release period;
- local lenses: explicit country questions with a named authoritative source;
- health and sources: fresh/stale/missing states, access mode, cadence,
  licensing note, fallback role, and source URL.

Missing is a state, not zero. A local lens with no production-verified series
renders “Awaiting verified official adapter.” It cannot vote in the regime.

The descriptive decision score is:

`50 + 22×growth − 10×positive inflation pressure − 0.18×recession stress
+ liquidity adjustment + current calibrated-risk-state adjustment`

It is not a probability. The 21-session pullback probability is separately
calibrated by `engine/risk_radar_intl.py` on each market’s own history.

## Source hierarchy and current production state

| Market | Authoritative sources | Access / cadence | Current operational state |
|---|---|---|---|
| Japan | Bank of Japan; Statistics Bureau; Cabinet Office; METI; Ministry of Finance | BOJ keyless JSON/CSV API plus official downloads; daily to quarterly | Price/FX and OECD/FRED macro fallbacks are live. BOJ’s 2026 API is the preferred next series-by-series adapter. The stale CPI fallback remains visibly stale. |
| South Korea | Bank of Korea ECOS; KOSIS/Statistics Korea; MOTIE | ECOS and KOSIS require registered API keys; MOTIE official releases | Price/FX and configured OECD/FRED fallbacks are live. Key-gated official series remain explicit access blockers. |
| Euro Area | ECB Data Portal; Eurostat; European Commission | Keyless SDMX/Statistics APIs; daily to quarterly | ECB deposit rate and Eurostat EA21 unemployment are official overrides. Other configured FRED series remain documented fallbacks. |
| United Kingdom | Bank of England; ONS; OBR | BoE downloads; keyless ONS v1 beta API; release dependent | Price/FX and configured OECD/FRED fallbacks are live. ONS beta endpoints require dataset-specific release/version adapters before replacing fallbacks. Labour measurement uncertainty is called out in the UI. |
| India | RBI DBIE; MoSPI; Commerce Ministry; IMD | Official downloads, MoSPI CPI API/eSankhyiki, bulletins; daily to quarterly | Price/FX and configured FRED fallbacks are live. Official adapters remain blank until their units and release-period semantics pass fixtures. |

Authoritative documentation:

- BOJ API launch and statistical search:
  <https://www.boj.or.jp/en/statistics/outline/notice_2026/not260218a.htm>
- Bank of Korea ECOS / KOSIS:
  <https://ecos.bok.or.kr/> and
  <https://kosis.kr/openapi/index/index.jsp>
- ECB API / Eurostat API:
  <https://data.ecb.europa.eu/help/api/data> and
  <https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction>
- ONS developer hub:
  <https://developer.ons.gov.uk/>
- MoSPI API / RBI DBIE:
  <https://api.mospi.gov.in/> and
  <https://data.rbi.org.in/DBIE/>

Source reuse remains subject to each linked provider’s terms. The dashboard
stores observations and source metadata, not copyrighted release prose.

## Collection, cache, and failure semantics

`collectors/intl_macro.py` fetches every series independently with bounded
timeouts, exponential backoff, a circuit breaker, and frozen-tail detection.
Official ECB/Eurostat series override the matching FRED operational frame only
after parser and unit validation. Failure preserves the fallback or the
last-known-good parquet and writes the error to
`data/intl_macro/provenance.json`.

Parquets under `data/intl_macro/` are deterministic, upserted observation
caches. The provenance sidecar retains provider, source ID and URL, request and
source timestamps, last observation, unit, release-period semantics, and
official/fallback/missing status.

The series-level provenance status describes the latest fetch outcome, not the
origin of every retained row. Default upserts keep old-only dates and missing
values, and this sidecar is currently written by `fetch()` before the base
adapter commits frames. It is therefore not a successful-store-write receipt.
Historical disclosure must bind actual response date/value coverage and the
committed artifact; a latest `official` label alone cannot certify the full
cache. The bounded witness and current Eurostat comparison are recorded in
`research/paper_international_wave1_wave2/IM06_HISTORY_SOURCE_WITNESS.json`.

Central-bank calendars are hand-verified against official schedules in
`data/intl_risk/cb_calendar.yml`. A past event receives a “released” outcome
state but no fabricated policy decision. The user follows the official link for
the release outcome.

## Update and rendering path

The existing scheduled collector runs `IntlMacroAdapter`. The `intl` renderer
recomputes the shared regime histories and renders the comparative dashboard
plus all five country routes. Template or builder changes are included in the
render scope, and generated `site/*.html` pages are committed with their source
changes where required by the repository’s render contract.

## International index and FX EOD return admission (2026-10-09)

The Chairman has confirmed permission to redistribute user-facing international
price and FX data. This grant is now narrowly recorded in `config.yml` at
`intl.eod_publication` (scope `intl-index-fx-eod-user-facing-v1`).
It does not apply to other providers, raw tick archives, derivative data,
forecasts, or trading execution. Changing `status` away from `confirmed`
withholds new EOD return qualification without disabling legacy research.

The existing normal `scripts/build_intl.py` publisher calls
`lib.intl_eod_publication.build_eod_inputs`, then only the existing
`engine.intl_inputs.qualify_return_records` evaluator can grant a financial
value. The helper binds the **same persisted index/FX parquet bytes** that
`engine.intl_inputs._intl_closes` consumed, the collected-run status, the
configured auto-adjustment basis, an exact content digest, and each selected
observation endpoint. The stored file is read once into bytes and the parsed
close series must agree with the selected calculation frame. One bad/missing
series is withheld independently. A collector success alone never grants it.

The source cannot certify same-day foreign-market closes from a daily Yahoo
timestamp. Therefore the publication selects only dates at least **two
calendar days old**, and requires collector and saved-observation timing and
age checks, rather than treating a developing daily bar as a completed
session. The frontend labels these as **delayed EOD** and shows the actual
calculation windows. No claim of an exchange-certified holiday calendar is
made: the conservative T+2 policy is its admitted observation-time evidence,
not an exchange-issued schedule. The expected snapshot weekday is computed from
the earlier of the evaluation clock and the verified collector receipt clock,
before any stored tail is examined. The receipt must still satisfy a 48-hour *weekday-elapsed* bound (Saturday
and Sunday do not consume the age budget, with a maximum 96-hour wall-clock
window). A wall-clock midnight cannot invent a newer observation obligation
under an unchanged receipt; a newer collector receipt advances that obligation.
This narrowly preserves a Friday snapshot on Sunday, without claiming a
foreign venue holiday exception, extending a stale receipt into Tuesday, or
quietly treating the delayed data as live. Each index and FX
series must independently contain that exact date. A recent aggregate collector
status cannot qualify an older series. Weekend dates move to the preceding
Friday; missing weekday observations remain unavailable, with no invented
foreign-holiday exemption. Adding a faster clock later requires actual
per-market verified session/calendar evidence, independent data-quality
review and preserved before/after coverage cases.

A producer/runtime without fresh `data/run_status.json`, the exact parquet
materializations, the matching hash, or the permitted scope keeps numerical
values `unknown` rather than filling zero or borrowing legacy performance
scores. The original International tools, the macro/regime workspace, Risk
and History remain independently available. No new queue, collector, store,
provider key, paid entitlement, or market-scoring authority is introduced.

## Official ECB deposit-level admission

The existing International publication owner may publish the descriptive
`EZ.policy_rate` level for `official_policy/deposit_facility` from the configured
ECB `FM/D.U2.EUR.4F.KR.DFR.LEV` series. This adoption covers that level and its
source metadata only. Other rates, derived changes, economic-cycle headings,
and third-party series retain their own source decisions.

The [ECB statistical reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html)
permits commercial and noncommercial reuse of its publicly released statistics
subject to attribution and accurate reproduction of statistics and metadata.
The [ECB website disclaimer](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)
also requires a notice that the information is available free from the ECB,
before payment and whenever sold information is accessed. The publication
owner must verify the applicable purchase notice and the source notice at the
point of use before issuing a value decision. Link to the full ECB source;
do not imply ECB endorsement or substitute a transformed rate for its level.
These are publication conditions, not evidence that the current UI has met them.

The existing `engine.cb_desk._STALE_DAYS["daily"]` policy also applies to this
official same-instrument deposit level: age is the supplied UTC evaluation date
minus the observation date; age above that existing threshold is stale. Future
observations are refused. This is the age of the stored observation, not a
claim that no later policy decision exists and not an equity-session calendar.
The helper imports the existing threshold rather than copying it into the UI.

`engine.intl_inputs.admit_ecb_deposit_field` consumes supplied observations,
the matching official provenance entry, the caller's materialized artifact
identity, evaluation time, and an independent publication decision. It does not
read the store, fetch sources, grant disclosure, or manufacture a clock.
The trusted composition owner reads the exact artifact and sidecar together,
checks their identity, and binds its decision to market, field, instrument,
series, both content hashes, observation date, exact level and percent unit.
The helper validates that binding; arbitrary JSON cannot authenticate a caller.
Missing or mismatched decisions withhold the value. Denied metadata withholds
all dynamic source identity, dates, values and references.

`PCPA` represents the already stored percent annual rate; the adapter performs
no multiplication, interpolation or rounding. Native finite integer and
float32/float64 scalar values may be converted losslessly to builtin Python
numbers for JSON; booleans, strings and nonfinite endpoint values are refused.
Preserve the last actual observation and never drop a missing endpoint to find
an older usable value. The separate FRED `ECBDFR` artifact cannot borrow the
official ECB provenance or decision. A different fallback needs its own source
identity and decision.

The official sidecar's `source_updated` is an observation-date alias.
`requested_at` and sidecar `built` are acquisition/serialization clocks. None
is an independently known policy publication time: `calculation_at` and an
unknown release period remain null. Qualification here means permitted and
within the adopted observation-age tolerance, with that limitation visible.


## Byte-bound Japan yield and native annual current-account composition

The normal International publisher reads two additional independently qualified
field materializations. Their existence never supplies disclosure permission.
`intl.field_publication.<field>` is an explicit adopted publisher policy with
`status`, `policy_ref`, `metadata` and `value_permission`; no policy is enabled by
this implementation. The trusted publisher binds an adopted policy to the exact
field and receipt digest before the existing projections may expose a value.

For `JP.yield_10y`, the existing configured FRED series is `IRLTLT01JPM156N`
(OECD Japan long-term government yield, monthly percent, not seasonally
adjusted). `intl.macro.jp_yield_capture: true` opts into retaining the response
already obtained by the incumbent collector; it does not authorize a new request.
No setting is enabled here. Only the post-successful-store callback may retain
response/cache agreement evidence. The response month-start label stays an
observation-month label, never a daily close or publication timestamp. The
existing45-day observation-age tolerance is measured from that original label;
unknown source publication/revision dates stay null. Values are pass-through,
so calculation time is null. Current source access/disclosure must be independently
established; this source change does not clear an observed provider refusal.

The incumbent `ImfWeoAdapter.fetch()` accepts an optional already-acquired native
edition through `imf_weo.native_current_account: {workbook: <data-relative path>,
receipt: <data-relative path>}`. The acquisition receipt binds the actual workbook
hash, original IMF URL and received instant. It selects exactly
`JPN.BCA_NGDPD.A`; the existing alias remains `current_account_pct_gdp`.
Canonical `store.upsert` replaces supplied overlapping values and preserves
old-only rows. Only rows covered by this exact response receive the new edition
evidence. Native Japan is excluded from the same pass's DataMapper writes.
No native input is configured by this change. Failed source/store validation
cannot issue a new successful materialization receipt.

The native annual parser preserves `LATEST_ACTUAL_ANNUAL_DATA`, field-specific
`COUNTRY_UPDATE_DATE`, edition `PUBLICATION_DATE`/`UPDATE_DATE`, source methodology
and the raw `START_END_MONTHS_OF_REPORTING_YEAR` value, including null. Later
years are staff estimates under the WEO FAQ; the actual-year boundary does not
create a separate forecast/projection threshold. The displayed field selects
the latest source-labelled actual, never the legacy maximum year across unrelated
debt/fiscal/current-account rows.

The [October2026 WEO Database Appendix, Data Conventions, page3](https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf#page=3)
states that data refer to calendar years, with the stated TableF exceptions for
national accounts and government finance. This external-account/BPM6 measure
uses that documented calendar-year convention: year2025 maps to
2025-01-01 through2026-01-01 solely as the existing annual field interval. This
is not a claim that a blank reporting-month cell supplied those dates.

The annual measure carries the source country-series update date under the
existing `observation_at` slot and labels it **Source updated / 来源更新** in the
Risk cell. Edition publication remains the separate vintage, field year remains
the economic annual period, and `calculation_at` is null for the pass-through
value. Qualification requires source update ≤ edition publication ≤ actual
response receipt ≤ successful materialization ≤ evaluation, preserving the
source date's day precision. The incumbent annual200-day tolerance is measured
from the country-series update date. A missing source-update date withholds
qualification. Neither evaluation nor publication is substituted for it.

The actual October2026 workbook's Japan2025 actual was used for an internal
source/store/builder/render check. That check and fixture publisher decisions
are not commercial redistribution admission. Native data access, source rights,
scientific interpretation, protected release and authenticated beta behavior
remain separate facts. Existing ECB admission and all unrelated fields retain
their current contracts.

## Official Eurostat EA21 GDP and HICP

The native publication path admits exactly two Eurostat series. GDP uses
`NAMQ_10_GDP / Q / CLV_PCH_SM / SCA / B1GQ / EA21`; its unit is already the
change against the same quarter a year earlier. HICP uses the current
`PRC_HICP_MINR / M / RCH_A / TOTAL / EA21` series under ECOICOP 2. The archived
MANR dataset is not a current substitute. HICP is labeled as harmonized CPI,
rather than silently changing the meaning of the generic CPI family.

`IntlMacroAdapter` collects these configured official series on its ordinary
eligible run. It stores separate `EZ_gdp_yoy_official` and
`EZ_hicp_yoy_official` columns. In particular, the native GDP rate never enters
the incumbent GDP-level `pct_change` calculation. The strict JSON-stat parser
validates the returned dimension sets, selected codes and their positions;
`TOTAL` is selected even when a retained HICP response contains other categories.
Original time labels, source status flags and missingness remain in the capture.

The optional `native_input: {response: <data-relative-path>, receipt:
<data-relative-path>}` on either official-series entry imports a retained
successful response instead of acquiring it again. The import requires the exact
source URL, successful acquisition status and response digest. It uses the same
normal collector, canonical upsert and post-store callback as a current HTTP
response. It is not a manual bypass of the producer or disclosure boundary.
The callback consumes pending source evidence before capture; capture failure
leaves the successful numerical store intact and does not replay acquisition.
Readers check the original content-addressed receipt, original response and
current canonical parquet, including response coverage. Missing dependent blobs
are source failures, not evidence that no source was supplied.

The economic observation clock is the last civil day of the original period:
`2026-Q3` becomes the half-open interval `2026-07-01` to `2026-10-01`, with
`observation_at=2026-09-30`; `2026-09` becomes `2026-09-01` to `2026-10-01`,
with the same September 30 period end. The consumer labels this clock **Period
ended / 统计期结束** and shows the original quarter or month. These normalized
dates are neither publication times nor an assertion that a quarterly value was
observed at its start. Pass-through YoY values have `calculation_at=null`.

The dataset's original offset-aware `updated` timestamp is a separate typed
source clock in immutable capture and the Macro envelope's optional
`field_evidence` projection. It is never put into the economic observation slot
or represented as an individual release vintage. The projection binds the exact
field, instrument, source reference and evidence digest to the permitted measure.
Missing or denied metadata supplies no dynamic source link, update timestamp or
attribution. Other adapters retain their existing clock labels and contracts.
The original HTTP response receipt clock remains unknown when a retained receipt
did not record it; an actual local input-verification clock does not replace it.
The required ordering is dataset update ≤ original source request ≤ local input
verification ≤ successful canonical commit ≤ evaluation. A known HTTP receipt
must additionally fall between its request and local verification.

The principal adopts application display recency tolerances of **120 days after
the economic quarter end for GDP** and **75 days after the economic month end for
HICP**. Values beyond those bounds are stale. These are conservative Mastermind
display policies, not Eurostat release promises, latest-vintage claims or
point-in-time reconstruction. Updating unrelated dataset metadata cannot renew
an old economic period's recency.

The scoped publication decision follows [Eurostat's data reuse conditions](https://ec.europa.eu/eurostat/help/copyright-notice)
for these Eurostat-produced EA21 statistical series. Point-of-use disclosure names
Eurostat, links the exact source data, retains the source-request/access-day
trace, and states that Mastermind normalizes period labels and owns its
presentation, translation and interpretation. The [HICP metadata](https://ec.europa.eu/eurostat/cache/metadata/en/prc_hicp_esms.htm)
identify the harmonized index and current classification. This decision grants
nothing for IMF commercial publication, refused OECD access, other datasets or
unrelated countries. The builder adopts only the explicit source-specific policy
in `intl.field_publication`; readable data and a successful request are not grants.
Installation, publisher generation and authenticated Shared Shell acceptance remain
separate from collector/store and source-composition evidence.
