# Cross-Session Narrative Handoff — Data Capability Census

Date: 2026-09-25
State: SOURCE_CAPABILITY_CENSUS / RESEARCH_ONLY / NO NEW DATA PLANE
Operation family: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Parent preregistration: research/CROSS_SESSION_NARRATIVE_HANDOFF_PREREG_2026-09-25.md
Source head before this artifact: 1ea5969e7ede55215970f9ae21cad3fb3e2ce7ee

## 1. Decision

Do not implement cross-session price outcomes by inventing a research-owned exchange calendar
or by silently treating daily stores as minute stores.

The current estate can support the source-side research immediately, but native regional
first-five-minute price handoff is uneven:

- United States: historical minute path exists; session calendar has known early-close caveat.
- Mainland China: an explicit TuShare historical minute-plane implementation and exact
  trade-calendar owner exist in code, but minute-store materialization is not proven on the
  current canonical M2 checkout.
- Hong Kong: deep daily OHLC exists; no admitted historical minute plane or authoritative
  holiday/half-day calendar was found in this census.
- Japan: daily/index coverage exists; no admitted historical minute plane or authoritative
  exchange calendar was found.
- Europe: regional daily/live context exists; current region-hours logic is advisory and
  explicitly not an exchange holiday/half-day calendar.

Therefore the primary cross-session first-5m Asia-handoff outcome remains source-gated.
The research lane may not fill these gaps by creating another market-data or calendar plane.

## 2. United States

### Historical minute path

Existing Massive/Polygon U.S.-stocks minute aggregates are already used by the bounded
event-microstructure replay adapter and by other accepted research/live consumers.

This is sufficient for:
- USO / XLE oil-proxy response;
- QQQ / SMH U.S. equity response;
- U.S. premarket / regular / after-hours price observations where vendor bars exist.

It is not direct WTI/Brent futures authority.

### Calendar state

lib/nyse_calendar.py is the estate's real NYSE calendar owner, but prior repository census
documents that early closes are not fully modeled there.

Disposition:
- ordinary-session XNYS classification: usable through the canonical owner;
- half-day/early-close-sensitive events: require explicit exception handling or exclusion;
- no new research calendar.

## 3. Mainland China

### Historical minute implementation

collectors/tushare_minutes_plane.py is a separately reviewed bulk historical A-share
minute-bar plane over TuShare stk_mins.

The code establishes:
- 1/5/15/30/60-minute frequencies;
- Shanghai local-time session segmentation;
- immutable keep-first partitions;
- explicit nominal, unadjusted intraday price basis;
- no fabricated absent bars;
- a coverage ledger and reconciliation contract;
- collection authority = context_display_only.

The plane is intentionally gated and does not become a signal authority merely because its
collector exists.

### Trading calendar

The TuShare full-A spine owns SSE/SZSE trade_cal history and already carries exact
exchange-session records rather than weekday-only inference.

This is the strongest native regional calendar candidate for the cross-session study.

### Current materialization proof

On the current canonical M2 Macro checkout:
- config.data_dir() = /Users/chriswong/Documents/Cluade/Macro Dashboard/data
- data/tushare_minutes does not exist.

This proves only that the current checkout does not materialize that minute store.
It does not prove that no private/VPS/other lawful materialization exists elsewhere.

Disposition:
- source/session classification from the canonical TuShare calendar owner: potentially
  available after live-store read-path reconciliation;
- first-5m A-share historical response: **MATERIALIZATION / COVERAGE GATE**;
- do not execute a bulk backfill from this research PR;
- do not create a second China minute store.

## 4. Hong Kong

Repository evidence establishes deep daily price stores and HK-specific collectors, including:
- data/hk benchmark histories such as _HSI;
- per-name daily OHLC stores such as data/hk_stocks;
- HK stock/index collectors and downstream research.

No dedicated historical HK minute plane was found in this census.

engine/live_overlay.py contains Hong Kong local session windows, but its own contract says
those regional windows are ADVISORY only:
- no exchange holiday calendar;
- no half-day calendar;
- intended only to distinguish likely closed-market staleness from live-feed failure.

Disposition:
- daily previous-close / next-open research may be possible through existing daily owners
  after a separate exact-session-source ruling;
- native first-5m HK response: **BLOCKED BY MINUTE SOURCE + AUTHORITATIVE CALENDAR**;
- advisory region hours may be used only as labeled exploratory sensitivity, never the
  preregistered primary session classifier.

## 5. Japan

The estate has Japan/index context and daily international price surfaces, and
engine/live_overlay.py carries an advisory Tokyo session window.

This census found:
- no admitted historical Japan minute plane;
- no authoritative XTKS holiday/half-day calendar owner;
- no exchange_calendars / pandas_market_calendars dependency in the repo.

Disposition:
- first-5m Japan handoff: **BLOCKED BY MINUTE SOURCE + AUTHORITATIVE CALENDAR**;
- daily/index context remains descriptive only for this study.

## 6. Europe

The estate has European/global market context and advisory local session windows in
engine/live_overlay.py.

That same module explicitly says the windows are not exchange-holiday or half-day calendars.

Disposition:
- no primary cross-session timing classification from those wall-clock windows;
- no first-5m Europe handoff until an admitted regional minute + session owner exists;
- use existing Data OS / regional data owner if one is later admitted, never a research-local
  replacement.

## 7. Why the advisory clock is not enough

The cross-session study asks whether an event arrived after a real market's cash close and
how the next real open absorbed it.

A weekday + local-hour rule fails exactly where this question is most sensitive:
- exchange holidays;
- unscheduled closures;
- half-days;
- lunch/break rules;
- DST transitions across regions;
- market-specific exceptional sessions.

Therefore engine/live_overlay.market_session() is explicitly insufficient for primary
classification under this preregistration.

## 8. Minimum lawful data states

Each region is classified independently.

### READY_NATIVE_INTRADAY

Requires:
- authoritative session calendar;
- lawful point-in-time historical intraday substrate;
- exact source clock;
- known price/corporate-action basis;
- coverage/missingness receipt.

### READY_DAILY_GAP_ONLY

Requires:
- authoritative session calendar;
- lawful previous-close and next-open daily OHLC;
- no claim about first-5m behavior.

### SOURCE_GATE

Calendar or price authority is missing/unreconciled.

### DATA_GAP

Owner exists but the event/session is not covered.

Current census:

| Region | Calendar | Historical minute | Daily OHLC | Current research state |
|---|---|---|---|---|
| U.S. | canonical NYSE owner; early-close caveat | yes, U.S. stocks/ETFs | yes | READY_NATIVE_INTRADAY with half-day guard |
| Mainland China | TuShare trade_cal owner in spine | code implemented; current checkout store absent | yes | SOURCE_GATE until materialization/coverage reconciled |
| Hong Kong | advisory hours only in current census | none found | yes | SOURCE_GATE |
| Japan | advisory hours only in current census | none found | yes | SOURCE_GATE |
| Europe | advisory hours only in current census | none admitted here | yes/context | SOURCE_GATE |

## 9. Architectural ownership

This research PR must not own:
- a new multi-exchange calendar service;
- a second China minute plane;
- a new HK/JP/Europe market-data collector;
- a durable cross-session price store.

The correct next owner is the existing Data OS / regional data architecture. Research should
consume a capability only after that owner can provide a point-in-time read contract and
coverage receipt.

If no owner exists for an exchange calendar, the architecture decision belongs to Data OS
rather than this event-study branch.

## 10. What can proceed now

Independent work that does NOT require blocked regional minute data:

1. Build the exhaustive fixed-window source census for the timing-frequency hypothesis.
2. Assign source-side region/session labels only where an authoritative calendar exists.
3. Preserve unresolved HK/JP/Europe labels as unknown rather than approximate primary data.
4. Define the cross-session event manifest and contamination rules.
5. Continue same-session U.S. V2 code/tests and source-side feature work.
6. Reconcile whether the existing China minute/calendar stores are materialized on the
   canonical production data owner before any collection request.

## 11. Exact next technical gate

Before native Asia first-5m outcome computation:

- prove the canonical read path and current coverage for TuShare trade_cal + stk_mins;
- identify an existing lawful HK intraday/calendar owner, or classify HK as unavailable;
- identify an existing lawful Japan intraday/calendar owner, or classify Japan as unavailable.

No bulk collection or new provider integration is authorized by this census.
