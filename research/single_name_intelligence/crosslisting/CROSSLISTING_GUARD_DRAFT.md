# SNI Cross-Listing Guard (R1-gated DRAFT)

This is an R1-gated DRAFT of the SNI cross-listing guard: a declared
trading-session, FX-freshness, capital-version, and cross-bind contract for
comparing an HK ordinary counter with a US ADS (Alibaba 09988 HKD / BABA USD;
Tencent 00700 HKD as the ordinary leg). It consumes owner-supplied identity
ids, capital versions, FX quotes, and calendar fixtures. It does not mint
identifiers, does not own calendars or FX, and carries no rank, gate, size,
signal, escalation, or trade authority.

## Purpose

A US ADS / HK ordinary "premium/discount" print is wrong for most of the
day. HK and US cash sessions overlap only in a short window; HK has a lunch
break; either venue may be on holiday or halted; USD/HKD can be stale; the
ADS-to-ordinary share count is a dated capital-structure fact. This module
declares session state at a UTC instant, refuses a comparison when either
leg is not OPEN or the FX quote is stale, and will only form an ADS/ordinary
parity gap against a caller-supplied Capital Structure version.

The ratio, the FX quote, the holiday/halt calendar, and every identity id
are caller-supplied opaque values owned by Capital Structure, the FX owner,
the session-calendar owner, and Stock Identity / Data OS. This file is an
SNI-local draft contract, not a re-implementation of those owners.

## Session-state tokens (A12)

`session_state(venue_mic, ts_utc, *, calendar, local_code=None)` returns one
of:

| Token     | Meaning |
|-----------|---------|
| `OPEN`    | Local clock is inside a declared cash session for a known venue, on a non-weekend, non-holiday, non-halted instant. The only token that may pass a comparison. |
| `LUNCH`   | XHKG local clock is in `[12:00, 13:00)`. |
| `CLOSED`  | Known venue, outside session (including after the HK close and the US close), or weekend. |
| `HOLIDAY` | The venue-local calendar date is in the caller-supplied holiday fixture. Holiday wins over weekend. |
| `HALTED`  | A caller-supplied halt covers this `venue_mic` + `local_code` at `ts_utc`. |
| `UNKNOWN` | The venue MIC is not in the declared table, so no session can be asserted. |

**UNKNOWN means every comparison refuses.** UNKNOWN is an abstain with a
named reason (unknown venue), never a default 50/50, never OPEN, never a
pass through `fx_compare` or `ads_ordinary_parity`. A caller who does not
know the venue does not get a premium/discount number.

### Declared venues (fixtures inline with the coverage profiles)

| MIC   | Timezone            | Sessions (local, half-open) | Lunch |
|-------|---------------------|-----------------------------|-------|
| XHKG  | Asia/Hong_Kong      | `[09:30, 12:00)`, `[13:00, 16:00)` | `[12:00, 13:00)` |
| XNYS  | America/New_York    | `[09:30, 16:00)` | none |
| XNAS  | America/New_York    | `[09:30, 16:00)` | none |

Unknown MIC → `UNKNOWN` (never `OPEN`). Naive `ts_utc` → `ValueError`.
US DST is taken from `zoneinfo` (`America/New_York`). The 2026-03-08 US
spring-forward is the acceptance pair: `2026-03-07T14:35Z` (Saturday, EST)
is `CLOSED`; `2026-03-09T14:35Z` (Monday, EDT) is `OPEN` at the same clock
time of day in UTC. Holidays and halts are caller-supplied fixtures; this
draft does not ship a real exchange calendar.

Worked HK path (local times on a fixture weekday): 11:00 `OPEN`, 12:30
`LUNCH`, 13:30 `OPEN`, 16:30 `CLOSED`. Saturday `CLOSED`. A fixture holiday
date is `HOLIDAY` even during clock hours that would otherwise be a session.
A halt for one local code is `HALTED` while another code at the same venue
and instant may be `OPEN`.

## FX freshness and closed-market refusal (A13)

`fx_compare` converts `px_a` into `ccy_b` using a caller-supplied `FxQuote`
(`base`, `quote`, `rate` as `Fraction`, `as_of_utc`) and returns
`(px_a in ccy_b) / px_b` as a `Fraction`. That ratio is descriptive only.

It refuses:

- `FX_PAIR_MISMATCH` — `fx.base` / `fx.quote` do not match `{ccy_a, ccy_b}`
  in either direction.
- `FX_STALE` — `as_of_utc - fx.as_of_utc > max_age`, or the quote's
  `as_of_utc` is after the comparison instant (then-known: a future quote is
  not known at `as_of_utc`).
- `MARKET_NOT_OPEN` — either `state_a` or `state_b` is not `OPEN`.
  `LUNCH`, `CLOSED`, `HOLIDAY`, `HALTED`, and `UNKNOWN` all refuse.
  `UNKNOWN` never passes.

### Worked closed-market example

Alibaba ordinary `09988` at 16:30 HKT versus ADS `BABA` at 09:45 ET is
refused. Those two local prints are not the same instant: 16:30 HKT is
after the XHKG cash close (`CLOSED`), and a later 09:45 America/New_York
print is an XNYS open against an XHKG evening (`21:45` HKT, `CLOSED`).
Evaluated at a single UTC instant during the US cash morning
(`2026-10-12T13:45Z` = 09:45 EDT / 21:45 HKT) the HK leg is `CLOSED` and
`fx_compare` raises `MARKET_NOT_OPEN`. The guard does not stitch a stale HK
close onto a live US print.

## Capital-version binding (A11)

ADS/ordinary parity is `ads_px_in_ord_ccy / (ord_px * ads_ratio) - 1`,
returned as `parity_gap` (`Fraction`). `ads_ratio` is ordinary shares per
ADS and **must come from Capital Structure with a version id**. It is never
typed in at the call site as a bare integer, never inferred from a ticker,
and never guessed from a name.

`CapitalVersion` is a consumption record: `version_id` (opaque, owner
string), `owner` must be `capital_structure`, `ads_ratio` (`Fraction` > 0),
`effective_from_utc`. If `capital is None` the call raises
`CAPITAL_VERSION_REQUIRED`. If `effective_from_utc > as_of_utc` the call
raises `CAPITAL_VERSION_NOT_EFFECTIVE` (then-known: a version that has not
yet taken effect is not used). The return dict is descriptive only
(`descriptive_only: True`) with all six authority flags false.

A residual gap is descriptive. It is not a news-impact claim, not a
forecast, and not an input to a ranker, gate, sizer, signal, escalation, or
trade path.

## Cross-bind refusals (A01, A04)

Two counters never auto-bind. `bind_counters(a, b, *, receipt)` requires
each side to carry `venue_mic`, `local_code`, `currency` as stated by the
caller (coverage-profile values: XHKG/`09988`/HKD, XNYS/`BABA`/USD,
XHKG/`00700`/HKD). Identity ids, if any, remain caller-supplied opaque
strings; this module never constructs one.

| Situation | Refusal |
|-----------|---------|
| Identical venue + local_code + currency | `SAME_COUNTER` |
| Venue or currency differ, and `receipt is None` | `CROSS_BIND_VENUE_CURRENCY` (A01 / A04) |
| Local codes differ only by leading zeros (`"0700"` vs `"700"`, `"00700"` vs `"700"`), and receipt is missing or `source_owner` is not `stock_identity` | `PADDING_MISMATCH` |
| Valid Stock Identity receipt (`source_owner == "stock_identity"` plus a `receipt_id`) | `{"bound": True, "receipt_id": ..., "descriptive_only": True}` |

A padding-only code pair is not a proof of identity. Only Stock Identity
may attest that two paddings name the same counter, via a receipt this
module does not mint.

## Refusal code table

| Code | A-case | When |
|------|--------|------|
| `MARKET_NOT_OPEN` | A13 / A12 | Either session state is not `OPEN` (`LUNCH`, `CLOSED`, `HOLIDAY`, `HALTED`, `UNKNOWN` included). |
| `FX_STALE` | A13 | FX quote older than `max_age`, or from the future relative to `as_of_utc`. |
| `FX_PAIR_MISMATCH` | A13 | FX base/quote do not match the two price currencies in either direction. |
| `CAPITAL_VERSION_REQUIRED` | A11 | `capital is None`; parity is unestimable and abstains. |
| `CAPITAL_VERSION_NOT_EFFECTIVE` | A11 | Capital version `effective_from_utc` is after `as_of_utc`. |
| `SAME_COUNTER` | A01 / A04 | Bind of a counter to itself. |
| `CROSS_BIND_VENUE_CURRENCY` | A01 / A04 | Venue or currency differ and there is no bind receipt. |
| `PADDING_MISMATCH` | A01 / A04 | Codes differ only by leading zeros without a Stock Identity receipt. |
| `AUTHORITY_FLAG_FORBIDDEN` | program law | A caller attempted to set `rank_authority`, `gate_authority`, `size_authority`, `signal_authority`, `escalation_authority`, or `trade_authority` true. |

Every comparison that cannot be formed abstains by raising `GuardRefused`
with one of these codes. There is no default ratio.

## What this is not

- An R1-gated DRAFT on a lane branch. It is not a product, not a UI, and
  not an admitted owner.
- A real holiday or halt calendar. Holidays and halts are caller-supplied
  fixtures. Half-days, auctions, and odd-lot sessions are out of scope.
- An FX feed, a price store, or a peg. Quotes are caller-supplied
  `Fraction` rates with an `as_of_utc`.
- An identity mint. Unknown identity stays unresolved / null. Canonical
  issuer and security ids are never derived from a ticker, name, code, or
  CIK, and are never constructed here.
- A fork of Data OS identity, Company Event/Earnings, FIF, Capital
  Structure, Stock Identity, Options, Research Vault, or qledger /
  Evaluation.
- A rank, gate, size, signal, escalation, or trade input. All six
  authority flags stay false; setting any true is refused.
- A causal "news impact" (A24) or a 50/50 stand-in for an unestimable
  family (A25). `UNKNOWN` and every refusal code are named abstains.
