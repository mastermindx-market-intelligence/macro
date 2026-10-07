# Cash-market holidays and retained data

Assessment date: 2026-10-07. Scope: mainland China cash equities (SSE/SZSE/BSE), Hong Kong cash equities, US cash equities (NYSE/Nasdaq schedule), and Canadian cash equities (TSX/TSXV). Stock Connect eligibility is separately projected because a Hong Kong trading day is not necessarily a Connect trading day.

This is maintenance of the existing exchange calendars, collectors, stores, freshness checks, and live publication/client. It creates no scheduler, persistent calendar service, risk-sizing rule, signal, allocation policy, or new data plane.

## Outcome and time contract

A verified exchange closure pauses the expected completed-session clock. Healthy retained observations keep their actual provider date and value. A successful retrieval during a closure is not a new trade, a new daily bar, or evidence that a previously missing session has recovered.

For mainland China on October 7, 2026:

- National Day closes the exchange October 1–7; the last completed session is September 30.
- The next cash opening is October 8 at 09:30 Asia/Shanghai.
- A valid September 30 observation remains current throughout the break.
- September 29 data is still one session late. Missing, invalid and late data do not become healthy because the exchange closes.
- A valid developing October 8 quote can resume live display after opening. The expected *completed* daily observation advances only after the incumbent 17:00 local completion buffer.
- Government make-up working weekends remain closed stock-market days.

Dates and calendars attach to the listing/observation venue. A Hong Kong listing remains governed by HK, a US-listed ADR by US, and a Canadian listing by CA even when the issuer is Chinese. News, filings, macro releases, retrieval heartbeats, FX, futures and crypto retain their own cadence.

## Official 2026 closure assessment

Dates in the China table include adjacent weekend days in the announced break. Reopening means the next actual exchange session, including intervening weekends.

| Mainland holiday | Announced break | Next session |
|---|---|---|
| New Year | January 1–3 | January 5 |
| Spring Festival | February 15–23 | February 24 |
| Qingming | April 4–6 | April 7 |
| Labour Day | May 1–5 | May 6 |
| Dragon Boat | June 19–21 | June 22 |
| Mid-Autumn | September 25–27 | September 28 |
| National Day | October 1–7 | October 8 |

The following table lists weekday exchange closures, rather than every public holiday or weekend.

| Exchange family | 2026 closed weekdays |
|---|---|
| HK | January 1; February 17–19; April 3, 6, 7; May 1, 25; June 19; July 1; October 1, 19; December 25 |
| US | January 1, 19; February 16; April 3; May 25; June 19; July 3; September 7; November 26; December 25 |
| CA | January 1; February 16; April 3; May 18; July 1; August 3; September 7; October 12; December 25, 28 |

Distinct cases retained in regression tests:

- HK September 25, September 28 and December 28 are open in 2026. Legacy date approximations incorrectly closed some of these dates.
- US July 2 is a full session in 2026; July 3 is the observed Independence Day closure.
- US October 12 and November 11 are cash-equity trading days despite federal/banking holidays.
- Canada September 30 and November 11 are cash-equity trading days; Canadian Thanksgiving closes October 12.
- China make-up workdays on January 4, February 14/28, May 9, September 20 and October 10 do not create stock sessions.

### Half sessions

| Market | 2026 dates | Cash close used | Daily data due |
|---|---|---|---|
| HK | February 16, December 24, December 31 | 12:10 HKT, allowing closing auction | 13:30 HKT |
| US | November 27, December 24 | 13:00 ET | 14:00 ET |
| CA | December 24 | 13:00 ET | 14:00 ET |

Half sessions are valid trading dates. Regular completion buffers remain CN 17:00, HK 17:30 and US/CA 17:00 local time. DST is handled by exchange timezones, not fixed UTC offsets. The CN advisory window includes the SSE/SZSE fixed-price after-hours session through 15:30; that does not advance the daily completion buffer.

### Stock Connect

The 2026 Connect calendar uses the verified intersection of CN and HK trading dates. Both directions are closed on October 7 while HK local equities trade. Its completed-day expectation waits for both venue completion buffers. The displayed intraday window is the conservative joint cash window, not a directional Northbound/Southbound order-routing timetable; on HK half sessions it does not assert an afternoon joint opening. No order admission depends on this display.

## Coverage and uncertain years

`lib/exchange_holidays.py` records immutable annual slates, English/Chinese names, early closes and source URLs. Complete incorporated notices are CN 2026, HK 2026–2027, US 2026–2027 and CA 2026. The published CA January 1, 2027 date is partial evidence, not a complete 2027 slate. Connect has complete incorporated eligibility for 2026.

A complete CN 2027 or CA 2027 slate is not claimed. Future annual notices must be incorporated through this same table and its tests when published; adding a date without its official annual source does not make the year verified.

Existing historical calendar APIs and one-off-closure hooks remain available for compatibility. Approximate historical calendars may support lag arithmetic, but cannot destructively delete a real provider weekday. In particular, the old HK fallback falsely classified December 28, 2021 as closed. The actual-date acceptance policy now preserves provider weekdays in an unverified observation year while always rejecting malformed dates, weekends and dates after the exchange-local current date. Verified-year holiday weekdays are rejected.

Unknown comparison-year coverage is explicitly unverified. It grants no holiday freshness exemption or live cash-price authority. HK sentinel aggregation remains within its existing error/degraded states and carries the explicit calendar uncertainty separately.

## Implementation ownership

| Existing owner | Change |
|---|---|
| Four `lib/*_calendar.py` modules | Use complete official annual slates and early-close completion buffers while preserving public APIs and historical compatibility |
| `lib/market_session.py` | Pure shared session status, expiry, timezone, expected completed session, cash-symbol routing and observation freshness projection |
| `lib/market_observations.py` | Shared actual-date acceptance, provider/query-date agreement and whole-adjusted-column acceptance helpers |
| `collectors/base.py` and explicit cash adapters | Filter actual observations before persistence; grade retained observations by missed sessions; keep noncash cadence and provider failure behavior |
| `lib/store.py` | Refuse empty or older adjusted refreshes before replacing a complete stored window |
| CN/CA/HK universe writers | Guard independent inner writes, stale per-column adjustment windows and unsuccessful full-history repair downloads |
| Tushare latest/history writers and HK southbound writer | Preserve provider trade/holding dates and retain last-good data on invalid, empty, mismatched or older responses |
| HK and Tushare freshness; Canada tailwind gate | Use exchange-session expectations while preserving actual observation dates and existing consumer contracts |
| Existing overlay and quote builders | Publish shared calendar receipts; validate real quote clocks; keep historical baseline truth independent from retrieval time |
| `templates/live.js` and paired `site/live.js` | Render bilingual market status and apply the same hold/expiry rules to polling and WebSocket display updates |

The minute-by-minute quote snapshot is the around-the-clock status carrier. The existing full overlay only runs during US hours, so it cannot be the sole calendar publisher for Asia. The quote snapshot adds the same pure status projection without another provider request or timer. The client consumes those receipts and the overlay by their own checked-at time; an older overlay cannot undo a newer reopening.

Regional historical readers reuse the existing stock stores and wide panels. They select the freshest complete adjusted series without stitching different adjustment bases. US and unrelated-asset readers retain their existing Yahoo-before-stocks precedence. Regional baseline metadata comes from the existing `chinastockdata`, `hkstockdata` and `canadastockdata` directories.

## Failure and correction behavior

1. **Empty/holiday-only response:** do not write an empty replacement; retain valid stored observations and expose missing/late data separately.
2. **Older adjusted window:** retain the whole last-good column, including its adjustment basis. Do not replace only the overlapping dates and leave a split seam.
3. **Repair download raises:** record all requested columns as unaccepted before the request. Restore each complete prior column unless a valid current full rebase succeeds.
4. **Legitimate correction:** current complete adjusted rebases and valid historical corrections remain possible. Freeze means no fabricated market observation, not refusal of all source corrections.
5. **Provider/query date mismatch:** reject before assigning the requested date or accruing history. Retrieval date never replaces trade date.
6. **Missing, synthetic, malformed or future quote clock:** no actionable live cash update. A zero vendor-latency hint cannot reset elapsed observation age.
7. **Invalid quote with healthy retained baseline:** keep baseline data health distinct from rejected quote quality.
8. **Expired/missing calendar receipt:** show status unverified and retain the carried display; never extend authority through a failed request or old WebSocket message.
9. **Reopening:** a current valid quote resumes updates; the next daily expected date advances at the venue completion buffer. Existing slow conviction, sizing and allocation policies remain unchanged.

Session receipts include `checked_at`, `valid_until`, `calendar_verified`, `state`, `data_frozen`, `expected_session`, `next_open`, timezone and source URLs. Data records separately carry actual through-date, baseline/history health and quote health. The typed `quote_clock_invalid` fact survives a simultaneous bad-print rejection; an artificial or otherwise invalid old clock cannot outrank a valid incoming provider observation. No retrieval timestamp is presented as a completed market observation.

## Verification contract

The regression suite exercises real inner persistence paths in isolated stores, not only calendar lookup helpers. Required cases include Golden Week retention and reopening; preholiday outages; missing/invalid rows; HK versus Connect; US/CA half sessions; synthetic/future quote clocks; older adjusted windows; raised full-repull errors; valid full rebases; historical HK weekday preservation; unknown annual coverage; and derivative/FX/crypto exclusion.

The client gate executes actual `live.js` with controlled network, clock, DOM and WebSocket inputs. Browser checks use actual stock/macro page DOM and CSS across 390/1440 widths, EN/ZH and light/dark. The same source file is shipped in both template and served-asset locations. The CI registration uses existing calendar and HK robustness job owners and the incumbent Node 20 profile.

A local passing suite establishes implementation behavior. Release completion additionally requires an immutable PR head, current-base integration/hosted checks, independent review, a governed merge, and actual deployed quote receipts and visible status on the live regional pages. Controlled fixtures do not substitute for that live proof.

## Primary sources

- [SSE 2026 closure notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml)
- [SZSE 2026 closure notice](https://www.szse.cn/disclosure/notice/t20251222_618087.html)
- [BSE 2026 notice via CNINFO](https://dataclouds.cninfo.com.cn/sjother2/regulatory/2025/20251222/55875a9937374da4ae2d4999dfda2722.pdf)
- [HKEX 2026 cash-market calendar](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2025/ce_SEHK_CT_075_2025.pdf)
- [HKEX 2027 cash-market calendar](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2026/ce_SEHK_CT_077_2026.pdf)
- [HKEX 2026 Connect calendar](https://www.hkex.com.hk/-/media/HKEX-Market/Mutual-Market/Stock-Connect/Reference-Materials/Trading-Hour,-Trading-and-Settlement-Calendar/2026-Calendar_pdf_e.pdf)
- [NYSE holidays and hours](https://www.nyse.com/trade/hours-calendars)
- [Nasdaq holiday schedule](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule)
- [TMX trading calendar, including the December 24 TSX/TSXV early close](https://www.tsx.com/en/trading/calendars-and-trading-hours/calendar)
- [HKEX official 2021 calendar](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2020/ce_SEHK_CT_038_2020.pdf)
- [SSE 2021 Southbound arrangement, including December 28 reopening](https://www.sse.com.cn/services/hkexsc/disclo/announ/c/c_20201224_5287208.shtml)
