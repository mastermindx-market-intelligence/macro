# Shared Shell market calendar

The calendar supplies the native season preview, earnings, dividends and economics views. The companion frontend contract is documented in Terminal `terminal/docs/market-calendar-delivery-20261114.md`.

## Existing refresh owner

The existing snapshot lane runs the calendar task every five minutes, including weekends. Weekend runs return before quote/basket work. The calendar uses atomic private state publication and does not add a service, timer, queue or public provider artifact.

The builder retains a rolling 84-day range in daily source partitions. Earnings from two days ago through ten days ahead refresh every 15 minutes. Provider economics from yesterday through two days ahead refresh every five minutes; other dates refresh every three hours. Declared dividends and capitalization/ratio snapshots refresh daily. Missing or partial windows warm incrementally within reserved per-source budgets. Private pagination progress survives transport failures. Oldest-attempt ordering prevents one failing date from blocking the rest. Resumed Yahoo pages revalidate the head identities and total; changing or overlapping pages never claim completion.

Complete prior partitions survive partial or failed refreshes without changing their observation clocks. HTTP 401/403 source failures remain fenced for diagnosis rather than automatically replaying.

## Source contracts

Yahoo's calendar visualization protocol is defined by [yfinance 1.5.1 calendars.py](https://github.com/ranaroussi/yfinance/blob/1.5.1/yfinance/calendars.py). The raw adapter preserves legitimate zero values that the upstream DataFrame cleanup would discard. It pages bounded weekly earnings and economics windows.

Massive's `/stocks/v1/dividends` provides declared dividend actions; `/stocks/financials/v1/ratios` supplies dated capitalization and dividend yield. Acquisition is bulk and paginated, without per-company fanout.

The existing official release model owns verified US publication facts. The producer materializes its network-free schedule, and pure app-owned projection code overlays the current publication sidecar on every request. All request-time calendar modules are covered by the existing app deployment rule. Yahoo economic rows remain separately sourced provider series, with raw actual, consensus, prior and originally reported display values. They do not become official verification, trigger publication alerts or overwrite official actuals. Unknown units, importance and exact times remain explicit.

## Private API contract

`GET /api/market-calendar/v1?from=YYYY-MM-DD&to=YYYY-MM-DD` reuses the existing access dependency before reading private state. Queries allow at most 31 dates and reject unknown or duplicate parameters.

Results use `market-calendar.v1`, bounded 2,000-event pages, a continuation offset and a revision derived from both source artifacts. A changed revision rejects the continuation rather than mixing generations. Byte budgets, a two-reader semaphore and private/no-store headers apply. Provider credentials and internal partition/ratio caches are never projected.

The frontend proxies this fixed API owner using canonical identity. It renders `/discover?tab=calendar` through existing navigation, language, theme and company links. Source timestamps remain separate from screen polling. CSV escapes spreadsheet formulas; ICS preserves date-only events and is explicitly a snapshot.

## Meaning and coverage limits

- Provider US earnings listings are not asserted to be every global stock or unique issuer. ADR/share-class duplicates remain distinct listed securities; company capitalization is not misleadingly summed.
- EPS basis, currency, revenue and explicit date confirmation are unavailable from this earnings contract. Provider surprise values remain labeled. Zero is not missing.
- Market-cap joins use the existing case-exact vendor identity helper. Currency case is preserved: `GBp` differs from `GBP`. Provider yield retains its observation date.
- Dividends are acquired by ex-date. Payment and record-date views can omit actions whose ex-date is outside the acquired window; those views are marked partial.
- Official macro events retain their own units and verified actuals. GDP/claims prior readings are used only when the official parser supplies them. FOMC target bounds remain distinct metrics and render as a range.
- Provider economics add country coverage and sourced consensus without claiming complete global coverage or guessing units/importance. Raw prior and originally reported values remain different fields.
- Critical flags prioritize known USD earnings capitalization of at least $500 billion and selected major official US releases. They are transparent attention rules.

## Qualification

Focused calendar/provider/API suites are registered in the existing code gate. Existing orchestration coverage remains in place, and request-time calendar dependencies remain within the existing app restart scope.

Local qualification passed 28 focused backend calendar/API tests. Hosted checks, deployed refresh/readback and the native browser journey are separate required acceptance stages. This source document does not claim those stages complete.
