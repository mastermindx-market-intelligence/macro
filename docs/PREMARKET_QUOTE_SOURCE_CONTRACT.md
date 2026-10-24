# Additive premarket and postmarket quote source contract

This source-only P1 composes the existing Terminal Quote Plane into the dossier
API. It preserves `project_regular_quote`, the public regular keys, and the
regular-only batch consumer. `extended_quote` is additive and nullable. Existing
page JavaScript still renders the regular quote; no new page display, provider
collection, runtime activation, deployment or live proof is included.

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
loopback URL. The existing final `view=regular` projection strips every `ext*`
key. No hub wiring, new publisher, timer, socket or demand pass is added.

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
