# Additive premarket and postmarket quote source contract

This source-only P1 composes the existing Terminal Quote Plane into the dossier
API. It preserves `project_regular_quote`, the public regular keys, and the
regular-only batch consumer. `extended_quote` is additive and nullable. The primary hero/sticky price stays regular. A separately labeled pre/post
reading is composed by the existing controller; no provider collection, runtime
activation, deployment or live proof is included.

The Terminal producer is `hub/lib/snapshot.js` plus `hub/lib/store.js`.
The snapshot cache retains price/clock candidates even when zero/missing day
OHLC makes the existing regular parser return null. Each last-trade nanosecond
clock is converted to milliseconds; minute clocks already use milliseconds.
Candidates are filtered individually for positive price, finite nonfuture clock,
same ET date, actual calendar session and age at most 120 seconds before choosing
the newest. An invalid last trade cannot hide a usable minute. The selected
price and `extAsOfMs` remain one observation; `extTs` is its floored seconds.
Snapshot `updated`, polling, regular timestamps and sibling freshness supply no
extended observation age. Missing/zero day OHLC remains missing.

The existing daily-file anchor owner adds `completedRegularClose`,
`completedRegularSessionDate` and internal `completedRegularSource=daily_file`
from the actual matching daily bar. The date must be the most recent completed
regular session at evaluation time. Today's incomplete row is excluded before
its calendar close; unordered/future dates and missing matching bars do not
produce this reference. The existing regular anchor behavior is preserved.
This names an existing reference owner, not a claim that its historical data
originates with Massive or receives new rights. Missing dated provenance leaves
the extended move unavailable rather than reconstructing it from rolled
`prevClose`, `prevSessionChg`, an incomplete day block or a plausible price.

The Store composes only `ext*` fields from that reference and the qualified
snapshot print. A pre/post print cannot replace regular `last`, `chg`, OHLC or
session date. Existing closed-session day-price fallback remains usable.
`/quotes` defaults to the existing full view used by the dossier's existing
loopback URL, now with the existing singleton selector
`extSource=primary_snapshot`. The request suppresses ExtFeed demand and read
before effects, retains the primary snapshot/Polygon/anchor demand, strips all
cached ext fields, and requalifies the tuple through the accepted snapshot and
actual anchor owner at the same request clock. No provider substitution occurs
when primary data is unavailable. Other full/regular/tiingo_boats clients keep
their existing behavior; this is request-local isolation, not global quiescence.
The inherited default/full demand graph can still involve independent legacy
providers for other clients. Filtering public values alone never proved demand
isolation or legacy-provider rights. The existing final `view=regular` projection
strips every `ext*` key. No hub wiring, publisher, socket or demand pass is added.

`extSession` identifies the print; additive `extMarketSession` identifies the
current calendar phase. Their actual windows must agree. Legacy regular
`marketSession` retains its existing weekday-only behavior, including its
shortened-session limitation. It does not override the new tuple's separately
validated market session.

Calendar decisions reuse the immutable
`terminal/lib/usEquitySessionProjection.json` in Terminal and its existing
`lib.nyse_calendar` / `engine.session_digest` owners in Macro. Both refuse the
new tuple outside the shared 2016-01-01 through 2028-12-31 coverage. Premarket is
[04:00, regular open), postmarket is [regular close, 20:00), shortened-session
postmarket ends at 17:00 ET. Holidays and weekends have no tuple. At 09:30 ET
the pre tuple disappears even without an opening regular print. ET midnight
clears the old date. Friday/Monday, holiday gaps and DST use the same owners;
no second calendar registry or fixed UTC offset is introduced.

Macro's `project_extended_quote` independently checks actual session, date,
reference date, price, clock, age and seconds/milliseconds consistency. Only
`polygon-snapshot` / `polygon-snapshot-rt` source values can enter this new
public tuple; Webull, Yahoo, Alpaca and unknown sources are refused. Existing
Massive display/derived-use conditions and public debranding remain binding;
this source change assumes no new entitlement. Source/basis and internal
reference-owner names are removed. The public tuple contains price, currency,
print/market session, completed regular reference price/date, derived absolute
and percentage move, actual millisecond clock/ISO observation and measured
freshness. Invalid or missing extended data is null beside the existing regular
fallback, rather than a new route error.

## Source acceptance and release hold

Offline checks cover the actual daily-file anchor, snapshot/store, real
`handleQuotesRequest` seam and Macro projection with opposite regular/extended
signs; the existing regular-view keys remain identical. Focused suites cover
future trade plus valid minute, own-clock staleness, malformed clocks, holiday,
weekend, midnight, DST, opening/shortened-session boundaries and missing dated
references. All fixtures are synthetic offline inputs.

The current source commission permits draft PR publication and CI consumption.
Both PRs remain unarmed until the root accepts the coupled changes and qualifies
automatic effects. Macro `app/deploy/update.sh` fetches/resets main and matches
`app/.*\.py` for API restart, so merging its app changes can cause a runtime
effect. The Macro PR must remain draft with an explicit no-merge hold. Terminal
`ops/terminal-build.sh` installs the terminal source tree and hub runtime overlay
and restarts quote-hub when hub bytes change; no build/install is authorized by
this source commission. Neither CI nor offline acceptance proves deployment or
an untouched real premarket observation.

## Source-only presentation packet

Job/archetype: Instrument Analyzer (C), existing dossier decision header. The
reader distinguishes the regular move from a named pre/post observation and
its completed-close reference, then sees if that observation remains usable.
Primary hero/sticky prices, regular move, range and regular freshness owner
remain together. The separate reading names session, price and signed move,
completed regular reference price/date and observation age. EN/ZH spans update
together. Direction retains signs and existing locale-specific ink, with no
new live pulse or color-only meaning.

DARK TREATMENT: existing graphite hero/canvas and luminance hierarchy, neutral
heading/reference, contrast-adjusted direction ink and quiet age. No new card,
glow, accent border or material system.

LIGHT TREATMENT: existing cool research canvas, light material hierarchy and
stronger contrast ink. The added typographic reading has no independent
background/elevation requiring inversion; it inherits the existing light art
direction. The intentional theme difference remains the governed material/ink
system; geometry and meaning are shared.

Mobile uses the existing single-column hero reduction and wrapping heading;
reference and age occupy their own lines. Desktop retains right alignment.
The reference remains visible at390px. No new interactive controls or hover-only
receipts are added.

The server adds `valid_until_ms=min(as_of_ms+max_age, actual phase end)`. This is
a policy deadline, never an observation/freshness clock. The client validates
the tuple atomically, advances age from `as_of_ms`, and clears at
`now >= valid_until_ms`, including exact09:30, failed polling and tab reveal.
Unavailable, stale, malformed or future data clears the extended values and
names the regular fallback; missing is never zero.

Evidence: real Chromium source-fixture captures cover dark/light x EN/ZH x
1440px/390px; synthetic data and frozen source clock are explicit. CSP denies
connections; the controller fetch receives an in-memory reply. No live/provider
snapshot or production journey is claimed. Negative-state DOM cases and local
screenshots separately cover unavailable/expired/recovery states. Receipt:
mockups/evidence/dossier-premarket-20261023/EVIDENCE.yml.

The historical entitlement record covers snapshot/trade/aggregate display and
derived use subject to dataset-specific written conditions. It grants no legacy
provider rights and proves no current credential/feed access. Macro template
merge also triggers render publication, in addition to the API restart boundary;
both source PRs retain root-controlled draft/no-merge holds.
