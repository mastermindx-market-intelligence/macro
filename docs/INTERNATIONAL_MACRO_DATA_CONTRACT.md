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

## Current-reconstruction History derived-output adoption

**Source adoption, 2026-11-05.** The assigned Shared Shell root
`01a15e6c-42f8-7941-ac2b-296021932fbb`, exercising Chris's delegated delivery
authority, approved the exact finite product/audience declaration reviewed at
`6cb1cfc4b9d76530e7fcd33d5ffd1a37fbd2c92b` / receipt `d8ffc125`.
`intl.history_publication` is confirmed with the existing canonical
[Shared Shell mission reference](https://github.com/mastermindx-market-intelligence/macro/pull/7949#issuecomment-6589273748).
The root saved and read back this decision in that existing mission comment
on 2026-11-05 (comment body SHA256
`2838f697360d3abaee1c6b9ffe9099de44f4865625c5eb5e2f67bd23d9e4405d`).
It records the product/source decision, not a vendor-issued grant. Normal source
qualification, protected release and actual native materialization remain
separate. This is Mastermind derived-output authorization, not vendor/raw-data
rights, provider-coverage proof, PIT or runtime activation. EOD/index/FX and
ECB-level declarations above remain independent.

The adopted audience is **anonymous and registered readers of `intl.html`**:
the mounted data is inline HTML, so a client-side entitled view cannot narrow that
audience. The finite output is the existing seven configured markets' descriptive
`observation_at`, `growth_score` and `inflation_score`, plus the reconstruction
artifact reference, actual read clock, method hash and country/config/input-column
universe hash. Full supplied reconstruction is permitted only within that scope;
there is no arbitrary date-range or provider-data endpoint. Two blank native date
selectors submit exact supplied observations; selection never supplies permission.
The five existing country-page reads are reused once; Taiwan and Australia are
collected once through the same typed reader for this seven-market catalogue.
They do not acquire country pages, a second store or an endpoint. Missing, invalid
or undisclosed native inputs retain their own read/withheld state.

The native input classes are configured Yahoo/yfinance index/FX closes (`intl`),
shared Yahoo commodity closes/ratios (`yahoo`), and configured `intl_macro`
FRED/OECD/central-bank fallback series with matching ECB/Eurostat official
column overrides. The source configuration hash binds the actual `intl.countries`,
`intl.macro` and `intl.yahoo` bytes as canonical JSON. A configuration change does
not inherit this declaration. The named Yahoo commercial route remains
`APPROVED_BY_CHAIRMAN_ATTESTATION`. This adoption is a finite Mastermind derived
score/audience decision, not a claim that keyless access, official-source status,
readiness or the legacy composite spark grants every underlying series' raw
redistribution. No explicit prohibition on these derived score fields was found
in the retained native source contract. A complete per-row provider-response and
materialization/reuse witness is **unknown**; that fact is neither concealed nor
converted into a new provider grant. An actually applicable third-party
restriction remains a restriction and requires the affected source to stay
withheld; this adoption cannot overrule one.

Admission requires the successful native Parquet materialization descriptor,
verified bytes/dated score geometry, the same typed reader/projector, current
classifier source hashes, matching native engine/country configuration and the
exact finite declaration. Legacy files without a descriptor, failed or changed
writes, incompatible identities, absent/proposed/denied/changed-scope decisions
and malformed input stay unknown. Descriptor `disclosure_authority=none` remains
unchanged: identity metadata is not the decision.

At the comparison point the page states **current reconstruction**, descriptive
classifier scores, not investment returns, forecasts or what was known then.
Actual read time is explicitly not first-known time. Provider-origin coverage
remains unknown even when input-matrix/row coverage and source hashes are known.
The newly retained official GDP/HICP response receipts are not inputs to this
History model and confer no score coverage or permission. Raw provider series,
response bodies, event/turn records, track records, Saved context, original-known
vintages, PIT/backtest claims and trading authority are excluded. Scenario retains
its existing blank/manual assumptions and confirmed context; comparison scores
and dates never become manual returns or a scenario horizon.

Dark uses the existing graphite control/panel materials; light uses white
research surfaces, neutral hairlines and shadow. Both use the same labelled
44px native controls, full focus outlines, EN/ZH content, and stacked mobile
composition. Local source DOM tests establish intent/dispatch and failure
semantics only. Original History/Comparison browser and capture holds remain
separate from this source adoption and its later normal release.

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
