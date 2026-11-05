# A12 clock-law session state (SNI-local evidence)

Date: 2026-10-13
Row: A12 — "HK lunch, holidays, halts, and US DST produce session state"
Scope: `research/single_name_intelligence/event_response/s2_clocklaw.py` as consumed through `tests/test_sni_clocklaw_sessions.py`.
This is an SNI-local DRAFT contract that consumes owner-supplied session calendars from engine.qledger (`CLOCK_CALENDARS` → `lib.nyse_calendar` / `lib.hk_calendar`). It does not mint identifiers and does not feed a ranker, gate, sizer, signal, escalation, or trade path.

## Summary

`session_part` classifies a UTC instant on wall-clock time in `America/New_York` or `Asia/Hong_Kong` (zoneinfo; no hand-written DST table). Regular open is 09:30 and regular close is 16:00 on both clocks. HK midday break is 12:00–13:00 HKT. `first_session_after` maps a pre-open instant on a session day to that day and every later part to `next_session_strictly_after`.

Pinned on 2024-06-12 (a Wednesday session on both calendars): HK lunch start is inclusive, lunch end is exclusive, regular open is inclusive of `in_session`, regular close is inclusive of `after_close`. NYSE 2024 closures in the published set (Good Friday, Independence Day, Thanksgiving, Christmas) match `session_dates`. HKEX 2024 Good Friday, Easter Monday, and Christmas/Boxing Day match. HKEX Lunar New Year 2024-02-13 is a FINDING: the published closure is a session in `lib.hk_calendar`, so `first_session_after` of 2024-02-08 16:30 HKT lands on 2024-02-13. US DST 2024-03-10 / 2024-11-03 moves the 09:30 ET open between 14:30Z and 13:30Z. HK open stays 01:30Z on both sides of those US transitions.

`SESSION_SPAN_END` is 2027-12-31. `session_dates` stops there. The underlying calendars continue, so `first_session_after` after that last span session returns 2028-01-04 (HK) and 2028-01-03 (US). `ClockLawFailure` is the fail-closed branch when `next_session_strictly_after` returns None.

Halts, half-day sessions, and typhoon / black-rainstorm closures are named gaps. A12 stays PARTIAL until the M0 market-data owner's session-state test exists.

## Existing-coverage table

Source: `tests/test_sni_s2_clock.py` (untouched). That file covers the main placement cases. This review's tests add lunch-second edges, named holidays, DST transitions, span edges, and the named halt/half-day gaps.

| Test in `test_sni_s2_clock.py` | What it pins |
| --- | --- |
| `test_hkt_to_utc_conversion` | 2026-05-13 17:30 HKT → 09:30Z |
| `test_preopen_maps_to_same_session_us` | 05:30 ET on a session day → same US session |
| `test_packet_anchor_0530_et_case` | news_id 12157537 packet: t_avail 09:30Z, s_US = 2026-05-13, s_HK = 2026-05-14 |
| `test_in_session_and_after_close_map_to_next_session_us` | 10:00 ET → next US session; 20:00 ET → next US session |
| `test_exactly_at_open_is_not_strictly_before` | 09:30:00 ET exactly → next US session |
| `test_hk_midday_break_maps_to_next_session` | 12:30 HKT → `midday_break` and next HK session |
| `test_hk_after_close_maps_to_next_session` | 16:31 HKT → `after_close` / next HK session; same instant US `pre_open` / same US session |
| `test_weekend_release_maps_to_next_week_session` | Sunday 18:06 HKT → Monday on both clocks |
| `test_disclosure_date_maps_strictly_after_on_both_clocks` | `first_session_after_disclosure_date`; Friday disclosure → Monday |
| `test_event_date_quality_is_inadmissible` | EVENT_DATE / SNAPSHOT_DATE / CORRUPTED excluded from ADMISSIBLE_QUALITIES |

Absent from that file: 11:59:59 / 12:00:00 / 12:59:59 / 13:00:00 HKT, named exchange holidays, the two 2024 US DST transitions, span edges, halt input, half-day sessions.

## Edge semantics, quoted from the code

From `session_part` in `s2_clocklaw.py`:

```
if t < _REGULAR_OPEN_LOCAL[market]:
    return "pre_open"
brk = _MIDDAY_BREAK.get(market)
if brk and brk[0] <= t < brk[1]:
    return "midday_break"
if t < _SESSION_END_LOCAL[market]:
    return "in_session"
return "after_close"
```

`_REGULAR_OPEN_LOCAL` is `time(9, 30)` on both markets. `_SESSION_END_LOCAL` is `time(16, 0)` on both. `_MIDDAY_BREAK[MARKET_HK]` is `(time(12, 0), time(13, 0))`.

| Instant (local) | Operator | Label |
| --- | --- | --- |
| 09:29:59 | `t < 09:30` true | `pre_open` |
| 09:30:00 | `t < 09:30` false; then `t < 16:00` true | `in_session` (open inclusive of in_session) |
| 11:59:59 | HK break `12:00 <= t < 13:00` false; `t < 16:00` true | `in_session` |
| 12:00:00 | `12:00 <= t < 13:00` true | `midday_break` (start inclusive) |
| 12:59:59 | `12:00 <= t < 13:00` true | `midday_break` |
| 13:00:00 | `t < 13:00` false; `t < 16:00` true | `in_session` (break end exclusive) |
| 15:59:59 | `t < 16:00` true | `in_session` |
| 16:00:00 | `t < 16:00` false | `after_close` (close inclusive of after_close) |

`session_part` reads `t_avail_utc.astimezone(_TZ_LOCAL[market]).time()` only. It does not consult `cal.is_session`. A holiday or weekend wall-clock 10:00 is still `in_session`.

From `first_session_after`:

```
if cal.is_session(d) and local.time() < _REGULAR_OPEN_LOCAL[market]:
    return d
nxt = next_session_strictly_after(d, market)
if nxt is None:
    raise ClockLawFailure(...)
return nxt
```

Same-day placement uses `local.time() < 09:30` (open exclusive). `next_session_strictly_after` returning None raises `ClockLawFailure`; the function does not return None.

Observed on 2024-06-12 HKT converted via `to_utc(..., "Asia/Hong_Kong")`:

| HKT | UTC | `session_part` |
| --- | --- | --- |
| 09:29:59 | 01:29:59Z | pre_open |
| 09:30:00 | 01:30:00Z | in_session |
| 11:59:59 | 03:59:59Z | in_session |
| 12:00:00 | 04:00:00Z | midday_break |
| 12:59:59 | 04:59:59Z | midday_break |
| 13:00:00 | 05:00:00Z | in_session |
| 15:59:59 | 07:59:59Z | in_session |
| 16:00:00 | 08:00:00Z | after_close |

## Holiday cross-check table

`in calendar?` means the ISO date is in `session_dates(CLOCK_CALENDARS[market])` (a modelled session). `expected` is the published exchange closure. `observed` is `is_session` plus `first_session_after(<previous session> 16:30 local)`.

| date | market | in calendar? | expected | observed |
| --- | --- | --- | --- | --- |
| 2024-02-12 | HK | no | HKEX LNY closure; skip past the LNY cluster | not a session; previous session 2024-02-08; `first_session_after` 16:30 HKT → **2024-02-13** (published closure; FINDING) |
| 2024-02-13 | HK | **yes** | HKEX LNY closure | **FINDING**: `is_session` True; previous session 2024-02-08; `first_session_after` 16:30 HKT → 2024-02-13 |
| 2024-03-29 | HK | no | Good Friday closure | not a session; previous 2024-03-28; `first_session_after` → 2024-04-02 |
| 2024-04-01 | HK | no | Easter Monday closure | not a session; previous 2024-03-28; `first_session_after` → 2024-04-02 |
| 2024-12-25 | HK | no | Christmas Day closure | not a session; previous 2024-12-24; `first_session_after` → 2024-12-27 |
| 2024-12-26 | HK | no | Boxing Day closure | not a session; previous 2024-12-24; `first_session_after` → 2024-12-27 |
| 2024-03-29 | US | no | NYSE Good Friday closure | not a session; previous 2024-03-28; `first_session_after` 16:30 ET → 2024-04-01 |
| 2024-07-04 | US | no | Independence Day closure | not a session; previous 2024-07-03; `first_session_after` → 2024-07-05 |
| 2024-11-28 | US | no | Thanksgiving closure | not a session; previous 2024-11-27; `first_session_after` → 2024-11-29 |
| 2024-12-25 | US | no | Christmas Day closure | not a session; previous 2024-12-24; `first_session_after` → 2024-12-26 |

FINDING (HK 2024 Lunar New Year): `lib.hk_calendar` fallback for 2024 treats LNY first day as 2024-02-10 and closes eve + three lunar days with weekend observance, which yields 2024-02-09 through 2024-02-12 closed and **2024-02-13 open**. Published HKEX closures include 2024-02-12 and 2024-02-13. Tests mark both dates `xfail(strict=True)` with the date in the reason. engine/ and data/ were not edited.

## DST table

US DST 2024: clocks forward Sunday 2024-03-10, back Sunday 2024-11-03. Open is `to_utc(naive 09:30, "America/New_York")`. `session_part` one second before each open is `pre_open`; at the open instant it is `in_session`.

| session day | naive 09:30 ET → UTC | `session_part` at open−1s | `session_part` at open | 13:45Z |
| --- | --- | --- | --- | --- |
| Fri 2024-03-08 | 14:30Z | pre_open | in_session | pre_open (08:45 EST) |
| Mon 2024-03-11 | 13:30Z | pre_open | in_session | in_session (09:45 EDT) |
| Fri 2024-11-01 | 13:30Z | pre_open | in_session | in_session (09:45 EDT) |
| Mon 2024-11-04 | 14:30Z | pre_open | in_session | pre_open (08:45 EST) |

HK (`Asia/Hong_Kong`) on Mon 2024-03-11 and Mon 2024-11-04: `to_utc(naive 09:30, "Asia/Hong_Kong")` is **01:30Z** on both days. The US DST change does not move the HK open.

## Gaps

- **Trading halts (A12-GAP).** `session_part` / `first_session_after` take `(t_avail_utc, market)` only. A declared issuer-level suspension has no input. `test_clk_08_halt_gap_named` is `xfail(strict=True, reason="A12-GAP trading halts not modelled")`. Halt support was not built.
- **Half-day sessions (A12-GAP).** Clock law close is always 16:00 local. `lib.exchange_holidays.early_close` exists for announced 2026/2027 eves and is unused by s2_clocklaw. The 2024 HK fallback calendar treats 2024-02-09 (LNY eve) as a **full-day closure** (`is_session` False); `session_part` at 14:00 HKT is still `in_session` because it ignores `is_session`. `test_clk_03_hk_half_days` is `xfail(strict=True, reason="A12-GAP half-day sessions not modelled")`. Half-day support was not built. US early closes (e.g. 13:00 ET eves) are likewise unmodelled in the clock law.
- **Typhoon / black-rainstorm closures.** `lib.hk_calendar.ONE_OFF_CLOSURES` holds historical full-day weather closures (2016-08-02, 2017-08-23, 2018-09-16, 2023-09-08). The module documents that since September 2024 severe-weather trading, typhoon signals and black rainstorm warnings do not automatically close HKEX, and unannounced closures must be appended by hand. s2_clocklaw has no weather input. New weather closures absent from `ONE_OFF_CLOSURES` read as sessions.
- **HK 2024-02-13 calendar FINDING.** Published LNY closure; modelled as a session. See holiday table.
- **`session_part` on non-sessions.** Holiday and weekend wall-clock times still receive `pre_open` / `in_session` / `midday_break` / `after_close`. Placement onto a session date is `first_session_after`'s job.
- **Span bound is a `session_dates` ruler only.** `first_session_after` walks `cal.is_session` past `SESSION_SPAN_END` (see span section below).

## Where the calendar data comes from

`s2_clocklaw` imports `CLOCK_CALENDARS`, `MARKET_HK`, `MARKET_US`, and `next_session_strictly_after` from `engine.qledger`.

`engine.qledger.CLOCK_CALENDARS` maps `US` → `lib.nyse_calendar` and `HK` → `lib.hk_calendar` (also `CN` → `lib.cn_calendar`, unused by s2_clocklaw). Both calendar modules are stdlib rule engines. **Holiday lookup does not read a file under `data/`.** Tests therefore run in a full-tree depth-1 CI checkout without a data/ skip. A sparse checkout that omits `engine/` or `lib/` cannot import the clock law; that is an import failure, not a skip.

- **US (`lib.nyse_calendar.holidays`).** Rule-computed scheduled closures (New Year's, MLK from 1998, Washington's Birthday, Good Friday, Memorial Day, Juneteenth from 2022, Independence Day, Labor Day, Thanksgiving, Christmas) plus `ONE_OFF_CLOSURES` in that module (Hurricane Sandy 2012-10-29/30, Bush mourning 2018-12-05, Carter mourning 2025-01-09). `lib.nyse_calendar` does not call `lib.exchange_holidays.announced_holidays`. Docstring mentions of `data/cboe/...` describe other stores; they are not holiday inputs.
- **HK (`lib.hk_calendar.holidays`).** For a year present in `lib.exchange_holidays` (`HK` 2026 and 2027), the in-memory announced weekday-closure slate. For 2024 the announced table is absent, so the fallback `_holidays_cached` lunar/solar lookup tables (2014–2030) plus weekend observance apply, plus `ONE_OFF_CLOSURES` for historical typhoons. `lib.exchange_holidays` is an in-module mapping ("No network, filesystem, dependencies"). The `data/hk_breadth/_closes_cache.parquet` path appears only in the hk_calendar docstring as the stale-cache incident that motivated the module; holidays are not read from it.
- **qledger clock support range.** Comments in `engine.qledger`: US floor 2012-10-31 (unscheduled closures before that are incomplete); HK/CN tables 2014-01-01 through 2030-12-31. `s2_clocklaw.SESSION_SPAN_*` is 2019-01-01 .. 2027-12-31 and is used by `session_dates` only.
- **Forward walk.** `next_session_strictly_after` searches at most `_MAX_CLOSED_STRETCH_DAYS` (15) calendar days and returns None when none is a session.

## Span edges (pinned behaviour)

Last ISO date in `session_dates` on both clocks: **2027-12-31** (Friday, `is_session` True).

| market | after-close instant | `first_session_after` | wrap? | None? | `ClockLawFailure`? |
| --- | --- | --- | --- | --- | --- |
| HK | 2027-12-31 16:30 HKT | 2028-01-04 | no (not 2019-01-01) | no | no |
| US | 2027-12-31 16:30 ET | 2028-01-03 | no | no | no |

The calendars extend past `SESSION_SPAN_END` (HK lunar tables through 2030; NYSE rules for any year). `first_session_after` therefore returns the next real session in 2028 rather than raising. `ClockLawFailure` is still the fail-closed path when `next_session_strictly_after` returns None; `test_clk_07_span_edges` pins that raise.

## What this does NOT prove

This is SNI-local clock-law evidence: wall-clock session_part labels, holiday membership in the qledger calendars, DST via zoneinfo, and fail-closed behaviour when the next session is missing.

The M0 market-data owner's session-state test (row A12's named owner task) is not built here. The acceptance row stays PARTIAL until that owner test exists.

This file does not prove live venue state, issuer-level halt state, typhoon procedures, half-day CAS end times, or that a return window in Evaluation/qledger used these labels. Residual statistics elsewhere remain descriptive.
