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

## Incumbent US transmission derived summary

Status: finite source-owned product/audience decision approved by the Shared Shell
root, matching D-RISK-DERIVED-SCOPE-20261105. This declaration is adopted in the sole integrator's local source composition;
normal protected release remains required and no runtime activation is granted.
Decision: https://github.com/mastermindx-market-intelligence/macro/pull/7949#issuecomment-6589273748
(verified existing body 3fb4e3c8, 2026-11-05T12:45:01Z). The existing publisher defaults withheld
unless its exact `intl.risk_summary_publication` declaration is confirmed. This is
a narrow declaration for the existing native derived output, not a general policy
framework or an extension of the EOD or named macro-field grants.

Audience: anonymous and registered readers of the existing open `intl.html`
document. Public fields are the incumbent transmission `state`, its evidence
references and reported diagnostic state, calculation time, actual observation
dates and origin coverage. No additional raw series values, parquet/vendor wire
data, probabilities, forecasts, issuer exposure, country-credit changes, model
thresholds, portfolio action, PIT or historical availability are granted. The
existing Yahoo commercial-use attestation and native FRED/Yahoo read/use remain
separate facts; UNKNOWN provenance coverage alone is not a licensing refusal.
No actual provider/refusal or source-specific restriction is overridden.

The normal `scripts/build_intl.py` owner must successfully write its existing
`data/intl_risk/latest.json` and verify exact readback. Its typed successful-write
identity must match the same passed Risk payload; failure cannot reuse an older
file even if otherwise identical. Evidence references bind the SHA256 of those
exact published bytes and their JSON paths. A returned data object alone never
creates publication eligibility.

Required source eligibility: the exact native `em_stress` result must match the
state handed to `two_tier_read`, retain its own built time and per-origin-leg
observation dates, and satisfy the incumbent minimum three of six origin inputs.
Three observed inputs are model-qualified partial coverage, not all-six normal.
The four mandatory transmission legs are `us_hy_oas_vel`, `kre_spy_rs`,
`move_pctile`, and `sofr_iorb_corridor`. Each must have an available finite native
calculation, exact boolean matching the published hot count/state, source IDs,
actual source observation dates and calculation-frame identity. The aligned
calculation-through date remains separate from individual KRE/SPY or SOFR/IORB
source dates. Optional safety-bid output never fills a required slot.

The source frames are the already-consumed FRED BAMLH0A0HYM2, Yahoo KRE/SPY,
Yahoo MOVE, and FRED SOFR/IORB reads. Frame fingerprints identify the numerical
calculation inputs; they are not vendor-wire or parquet hashes. No second store
read, collector, feed, acquisition, new file registry or endpoint is introduced.
Origin and transmission generation clocks are not observation, release,
acquisition, publication-availability or independently certified freshness times.

The Risk caption must say Transmission assessment / 传导评估, show calculation
time separately from observation dates and origin coverage, provide inspectable
per-input dates in the existing disclosure, and explicitly state that market
freshness is not established by generation time. Missing dates remain unavailable;
no new freshness threshold or score is inferred. An origin with three to five of
six observed inputs may satisfy the incumbent model, but must carry an explicit
partial-origin label and actual coverage. An origin below the incumbent minimum,
or any incomplete/unavailable mandatory transmission leg, is withheld. Failed,
refused, invalid or unsupported publication/input receipts remain withheld.
Protected release still owes the coherent source/consumer composition and normal
checks; source tests do not certify current
data, actual runtime/availability, Paper or live account behavior.

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

## Official Eurostat EA21 annual current account

The additional annual Risk source is `TIPSBP20`, selected by the complete native
identity `A / PC_GDP / CA / S1 / S1 / BAL / EXT_EA21 / NSA / EA21`, in returned
axis order. `EXT_EA21` is the extra-euro-area21 counterpart; a returned
`WRL_REST`, `EXT_EU27_2020` or `EXT_EA20` category is not a substitute. EA21 is
the source's current composition of 21 countries, not a reconstruction of point-in-time
historical membership. `PC_GDP` already means percentage of GDP. The native annual
value is passed through without a ratio, annualization or forecast classification.

The native source supplies annual labels and a dataset update timestamp. It does
not supply an individual observation-release clock, a revision vintage or an
actual/estimate/projection classification. The accepted support variant therefore
uses `observation_type=statistical`, `vintage=null` and
`observation_clock_basis=period_end`. For field year 2025, the economic interval is
`2025-01-01` to `2026-01-01` and `observation_at=2025-12-31`. Dataset update stays
a separate offset-aware clock. It is never copied into observation or vintage.
The original actual/estimate/projection support contract remains unchanged.

This source's explicit application display tolerance is 400 days after the economic
year end. It is a conservative period-based display policy, not a vendor release
schedule, freshness promise or latest-vintage claim. Newer dataset metadata cannot
renew the economic year. Source update, actual request/receipt, local input
verification, successful canonical commit and evaluation remain separately bound
and ordered in the immutable materialization. Pass-through calculation time stays
null. Missing publication policy or denied metadata withholds dynamic source and
clock evidence through the same existing boundary.

The consumer labels this source as an annual statistic, shows the economic period
end and explicitly retains an unknown vintage. Permitted disclosure names Eurostat
and the exact native source; it does not call this an IMF actual, an EA20 statistic,
a Japan field or a composite country-risk verdict. The exact source-scoped
Eurostat statistical reuse decision and existing commercial/nonresponsibility
conditions apply. This branch supplies no permission for the separate IMF field.

## Official BoE Bank Rate admission

The incumbent configured `IntlMacroAdapter` official override `GB_bank_rate_official`
collects only Bank of England IUDBEDR, the daily Official Bank Rate in percent.
It is a nominal administered policy point (`bank_rate`), distinct from the
existing SONIA carry leg, a market rate or a range midpoint. The source is the
Bank's native IADB revised-data XML endpoint, with one calendar-year request.
An explicit data-relative `native_input: {response, receipt}` on that configured
series imports the exact retained official edition through the same ordinary
collector, successful `store.upsert` and post-store evidence path without a fetch.
It validates original successful acquisition status/hash/URL, the native series
and requested dates, and request ≤ response receipt ≤ local verification ≤
successful commit ≤ evaluation. Post-store evidence failure is contained by the
existing base adapter and never retries acquisition.

The immutable capture binds original XML and current canonical stored bytes.
A reader checks the selector against its original content-addressed sidecar and
revalidates native observed rows against storage. Historical cache rows outside
the native response do not become authenticated source observations, and an
explicit withheld native row cannot expose an older stored value. Exact dated
policy comparison requires actual endpoint membership; it never fills or picks
a nearest date. Current display reuses the existing daily 12-day application
age rule. Deliberately selected historical endpoints are separately labeled
latest-vintage reads, with no original-known claim or current-display age loan.

Economic observation dates remain dates. Per-row `LAST_UPDATED` is retained as
raw source text with **unknown timezone**, not converted to UTC or substituted
for publication time. Revision-vintage, independent release and numerical
calculation clocks remain null where not supplied. Collection/commit/build clocks
are distinct. Acquisition success supplies no disclosure decision.

The source-specific publication policy is scoped to Bank-origin IUDBEDR under
[the Bank's database terms](https://www.bankofengland.co.uk/legal), which grant
Open Government Licence reuse for the database subject to listed exclusions.
This binding does not extend to FX, SONIA or third-party series. Required
attribution is “Source: Bank of England. Contains public sector information
licensed under the Open Government Licence v3.0.” Link the Bank's terms and the
licence at point of use; imply no endorsement. The publisher adopts the policy
only for the exact field and immutable receipt. Metadata or value permission
that is missing, unknown or denied cannot be inferred from that notice, a source
URL, a successful request or the stored numbers.

The existing `engine.intl_rates.compare_policy_points` remains the numerical
owner for ECB deposit facility versus BoE official Bank Rate comparisons. Both
source labels and fixed dates must be explicit. A supported nominal-point mapping
is an application method decision, not an assertion of identical operating
frameworks or an economic stance comparison. No Saved admission, user identity,
authentication, source-generation installation or permission to apply SQL is
created by this producer contract.

## Official ECB BoE policy comparison

The native source composition invokes the unchanged
`engine.intl_rates.compare_policy_points` through
`lib.intl_policy_publication.compare_native_policy_points`. Only the explicit
`intl-ecb-boe-nominal-policy-point-v1` mapping of ECB deposit facility and BoE
Official Bank Rate is adopted here. The separate
`intl.policy_comparison_publication` policy binds method, exact pair, selected
fixed dates and actual ECB materialization/BoE receipt identity. Unknown or denied
mapping/source permission, incompatible identity or any missing exact endpoint
withholds every comparison number and reference. Current field freshness remains
independent of a deliberately historical latest-vintage comparison.

The retained actual-source fixed-date proof is 2026-08-28 to 2026-09-30.
Exact qualified native endpoint membership is required for a selected date pair;
no horizon, nearest-row search or user URL supplies an observation. The normal
producer never supplies a principal, Saved ID, revision or user question. The
existing native controlled preview owns authenticated same-record context and
all Save/reopen/undo operations. A source result is not native admission, an
authenticated preview, an installed feed or a Saved write. No date-pair grid or
client-side arithmetic is introduced. The existing authenticated Macro service
family is the callable host; source wiring does not activate or restart it.

## International generation feeds and native policy preview

The incumbent `build_intl` publisher exports only its admitted native field
contracts, before presentation mounts drop their permission evidence. The
`intl.workspace_generation.v1` artifact carries the actual workspace nonce,
explicit native contexts and field roster, original source clocks, receipt-bound
content/qualification identities, and policy section digests. Negative rows have
explicit null content, qualification and policy identities and no dynamic value,
source URL or source clock. An empty configured context has no invented fields.
Public artifacts contain no account, question, private Saved state or user query.
The existing optional private `IntlResolvedPacket` sink remains independent.

Local source files live under `data/intl/publication/generations/`. The existing
`build_feeds` plane copies them byte for byte to flat `site/feeds/` names:
`intl_generation_<uuid>_<sha256>.json`, its hash-bound
`intl_generation_descriptor_<sha256>.json` witness, and
`intl_generation_current.json`. A missing or failed build declares unavailable;
readers do not substitute an earlier generation. The existing R2 publisher
uploads exact immutable dependencies before committing the validated current
bytes. An unrelated feed failure still withholds the full feed manifest but does
not prevent an otherwise complete International pointer or revocation. A partial
fixture must use the incumbent no-manifest path and never replace a full manifest.

An optional `policy_points_ref` names one same-generation immutable
`intl_policy_points_<uuid>_<sha256>.json` with its byte length, mapping identity
and source qualification identity. This is the original ECB deposit-facility and
BoE Bank Rate daily evidence, including explicitly withheld original rows,
separate collection/store clocks and unknown provider publication/vintage clocks.
It is not a grid of comparisons. The exact native instrument references are
`EZ.policy_rate` and `GB.policy_rate`; their instrument IDs remain
`deposit_facility` and `bank_rate`. This projection requires the separately
configured `intl.policy_comparison_publication` decision above and both source
policies. A readable file or successful acquisition is not that decision.

The existing authenticated FastAPI service exposes
`POST /api/macro/policy-preview`. It accepts generation/fingerprint and the native
settings selectors, authenticates before source reads, and returns private,
no-store responses. It maps `revision_policy` explicitly to the unchanged Python
comparator's `vintage_policy`. Only exact supplied fixed dates and latest-vintage
source points can qualify this source mapping; missing dates, owner horizons and
original-known requests remain unavailable. The service computes no client-side
or alternate arithmetic, stores no Saved record, and returns no credential.

The service reads the existing deployment-owned R2 origin with the same
precedence as the incumbent feed plane: `R2_PUBLIC_BASE` when present, otherwise
`r2_data_plane.public_base` through the existing narrow `lib.config.load` reader. It appends only fixed flat feed names beneath
`/feeds/`. Reads are bounded, HTTPS-only and request-local, with no redirects,
retry, stale cache, arbitrary request URL or Git/filesystem fallback. It verifies
the exact pinned generation and referenced points, checks the fresh current
policies, and rechecks the current descriptor before returning a result. R2
publication does not imply that these gitignored feeds exist in `site.served`.

A qualified release therefore includes the generated International page, its
immutable generation/point feeds before the current descriptor, and the API code
and mount through the normal `app/deploy/update.sh` service path. That updater's
existing verified `macro-api` restart includes the exact policy reader/comparator
import closure, including source-only helper changes. Source checks, local
transport doubles, feed publication, service restart, authenticated native use
and protected installation remain separate proof boundaries. No new service,
credential, Caddy JSON route, SQL activation or second data plane is introduced.

### 2026-11-05 original official-source join: exact History configuration identity

The same confirmed finite History product decision at Macro #7949 comment
6589273748 adopts configuration SHA256
`4c4086708c9823025c9e61d38fd19874ca7444fec792eb801443aa4db4a59d24`.
Its only countries/macro/yahoo change from the previously reviewed `07a2cf4a…`
identity is the four original BoE/Eurostat `official_series` declarations.
The classifier's fixed country metric/extras inputs do not consume those four
columns. The whole-configuration fail-closed guard stays unchanged. Original
seven-artifact/source/method/universe proof retains its original identity; this
is source-join compatibility, not a relabelled receipt or a new materialization,
provider-origin, freshness, original-known or runtime claim.

After qualified installation, the four source declarations select the existing
native parsers during an ordinary collector execution. This source join does
not execute collection, add retained-input paths, activate Japanese inputs or
grants, replay an acquisition, or attest a future successful store/capture.

### 2026-11-07 accepted History consumer recovery: current source identity

The Shared Shell root's same-scope integration ruling adopts the existing finite
History output decision prospectively against actual configuration SHA256
`07a2cf4a7958d845969ce0bdf2ef1ab9b127fadfd516883b757c421dbcc11d20`.
The decision remains the original Macro #7949 comment 6589273748 above; this
source integration neither enlarges its audience nor supplies a materialization.

Only JP, KR, TW, IN, AU, GB and EZ current-reconstruction History is admitted:
`observation_at`, `growth_score`, `inflation_score`, with `artifact_ref`, `read_at`,
`method_ref` and `universe_ref` metadata, for anonymous and registered Intl HTML
readers. Events, graded track records, provider wire, source publication vintage,
forecasts and portfolio actions receive no additional permission.

The four `official_series` declarations in the earlier 4c408 join are not restored
to obtain its digest. The native writer's `country_record` passes the fixed
`intl_inputs._macro_frame` into `country_frame` and `intl_regime.classify`. Its
fixed country metric names and extras do not select `GB_bank_rate_official`,
`EZ_gdp_yoy_official`, `EZ_hicp_yoy_official` or
`EZ_current_account_gdp_official`. Country, Yahoo and engine settings are unchanged.
This is the same already-reviewed score input subset, not four new collectors.

The whole countries/macro/yahoo equality guard is preserved, including changes
outside that score subset. Actual successful materialization, source/method
postimages, market, frame and universe still must match before any value appears.
Absent, malformed, failed or binding-mismatched receipts remain unavailable.
The persistent `intl.history_materialization.v1` descriptor has no TTL or expiry
rule. Its `materialized_at` is a successful-write clock; `read_at` records the
artifact read. A newer read clock does not establish provider freshness, renew
source evidence or prove what was originally known. Eligibility still requires
the actual artifact/frame, implementation, configuration and universe bindings.

The original seven-run qualification reports say their full receipt bodies were
available only in the original temporary evidence scope. That evidence-retention
limit is not an expiry mechanism on persistent reconstruction descriptors.
Retained payloads and read-result facts cannot reconstruct successful-write
attestations or qualify the present source by themselves. No historical receipt
is relabelled as current, and local consumer observations remain controlled
fixtures. Source publication, future actual producer execution, complete-feed
delivery and real date-selection/return are separate acceptance boundaries.
