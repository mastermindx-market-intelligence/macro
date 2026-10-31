# 2H/3H RSI-MACD Research Consumer — source-only implementation

**2026-10-30** · Parent `WS:LIVE-ENTRY-RADAR` / existing RS Pullback Launch.
**Status: BUILT_NOT_PROVEN** (synthetic deterministic conformance tests only).
[Distinct pre-registration](../OSCILLATOR_MTF_PREREG_2026_10_30.md)
and [adjacent Mastermind #1888](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1888).

## Purpose and exact source interface

`engine/entry_radar/replay/oscillator_mtf_research.py` contains two pure,
research-only functions:

1. `aggregate_owner_windows(symbol, calendar, decision_utc, minutes, read_aggregate)`
   constructs **120-minute or 180-minute, full RTH bars** with supplied NYSE
   session open/close. The `calendar` argument is a caller-supplied
   `{date: (aware_open_utc, aware_close_utc)}` from the existing Macro
   calendar-owner read path, not an independently authenticated calendar.
   `read_aggregate(symbol, start_utc, end_utc, cutoff_utc)` must be provided
   by the already-admitted owner reader and return the existing
   `rs_pullback_launch_data._aggregate` result shape:
   `availability`, `start`, `end`, `expected_minutes`,
   `observed_minutes`, `known_at`, `ohlcv`,
   `input_revision_sha256`, `refusals`.
   The function checks self-consistency and does **not** authenticate
   receipt signatures, source rights, security identity or basis. An
   owner-compatible adapter must preserve those existing refusals; it may
   not silently manufacture a boolean `source_admitted`.
2. `oscillator_events(bars, indicator, eligibility, decision_cutoff_utc,
   supplied=None, prior_session_by_day=None)` classifies known full-bar
   oscillator crossovers using
   a caller-supplied previous-session leader receipt.
   `eligibility[(symbol, bar_end_utc)]` supplies
   `is_leader`, `known_at_utc`, `asof_session`,
   `expected_prior_session` and `receipt_sha256`. The expected prior
   session comes from the existing exchange calendar owner; the candidate's
   `asof_session` must equal it. Unknown/stale/future leader source remains
   `ELIGIBILITY_UNAVAILABLE`, not a negative trade label. For *multi-session*
   oscillator history, the optional owner-supplied `prior_session_by_day`
   must map each observed session to its actual preceding exchange session.
   Missing observed sessions then refuse the population; without this map,
   additional sessions abstain as `SOURCE_OWNER_PREDECESSOR_UNKNOWN`.
   These are consistency checks, not independent authentication of an owner
   calendar or of the historical identity/basis receipts.

## Frozen indicator species

| Indicator identity | Formula | Meaning |
| --- | --- | --- |
| `CANON_RSI_MACD` | `engine.canon.rsi_macd`: Wilder RSI14 → EMA(RSI,14) - EMA(RSI,60) → EMA(5) signal | Incumbent *canonical* Macro RSI-MACD (not necessarily initial Prophet served-series parity) |
| `PRICE_MACD_RSI_PROXY` | EMA(close,12)-EMA(close,26), EMA(signal,9) and Wilder RSI14 <=40 | Explicit price-MACD research challenger, **not** MACD of RSI |
| `SUPPLIED_LINES` | Caller-provided `fast, slow, oversold, known_at_utc, source_sha256` per completed bar, plus prior bar | Diagnostics of an exact outside indicator *only if its independent Pine/settings/export parity is separately established* |

Cross condition: previous fast <= previous slow; current fast > current
slow; **both current lines below zero**; oversold qualifier true.
Only fully known completed bars are scored. `issued_at_utc` is no
earlier than the last observable bar, oscillator, and leader receipts.
No next-open fill, order, rank, risk, probability or live alert follows
from `CROSS_OBSERVED`.

## Clock and missingness

A 390-minute RTH session yields **three 120m bars + a 30m excluded
stub**, or **two 180m bars + a 30m excluded stub**; native 210-minute
early closes yield one 120m + 90m stub or one 180m + 30m stub.
Every full window demands all expected owner minute slots, exact
start/end and revision digest, valid OHLCV, and `bar_end <= known_at
<= decision_cutoff`. The owner reader supplies actual historical
minute receipts; a complete bar count is not historical first-seen
proof. Excluded stubs are calendar states, not price candles.

`UNAVAILABLE`, `NOT_YET_OBSERVED`, `STUB_EXCLUDED` and
`WARMUP_OR_OSCILLATOR_UNAVAILABLE` are explicit. Missing full windows
reset oscillator continuity. Observed sessions must retain their complete
series of full bars and trailing stub. Missing terminal full windows and
stubs are refused; multi-day history must retain an owner-derived
predecessor mapping or abstain instead of treating a missing whole day
as a bullish signal. A recursively computed historical RSI-MACD or price-MACD
result whose **earlier input was revised after the purported event known-at**
is `SOURCE_HISTORICAL_REVISION_UNAVAILABLE`, not a fabricated historical
`CROSS_OBSERVED` or `NO_CROSS`. These checks do not replace immutable
per-event first-seen receipts from the incumbent source owner. Periodic date
changes, ET DST and exceptional session close are evaluated from
owner-supplied calendar boundaries, not a fixed UTC offset.

## Offline reproduction (no external connection)

```sh
python -m pytest -q tests/test_entry_radar_oscillator_mtf_research.py tests/test_rs_mtf_revision_prefix_qa.py tests/test_entry_radar_oscillator_owner_integration.py
python -m compileall -q engine/entry_radar/replay/oscillator_mtf_research.py
```

The latest isolated source qualification returned **44 passing synthetic
tests** across the oscillator conformance and delayed-revision QA suites,
with a local surrogate of the incumbent `engine.canon` implementation.
Eight native-owner integration tests now live under
`tests/test_entry_radar_oscillator_owner_integration.py`. They use the
real `rs_pullback_launch_data._aggregate` and its existing
`_metadata_errors` source refusal guard before reading synthetic minute
slots, including negative first-seen, identity and basis witnesses.
A new immutable-source M2 Studio run of the **repaired exact source head**
`b55f71772ed9df97adabcd918febf7bbbc10a8ef` completed with process
exit code 0: **52 passing synthetic tests, plus two unittest subtests**
(44 standalone oscillator/revision regressions + 8 native owner integration
tests). The source was copied with `git archive` into a fresh private
temporary scratch folder; only public code and synthetic fixtures were
used, with no private Parquet/credentials/real market dataset. No
genuine source entitlement or historical-adjustment vintage was proven.
All three suites are enrolled in the original existing `research-price-panel`
CODE-gate CI manifest, with no additional workflow or new source authority;
current complete hosted CI and independent exact-head review are still separate
acceptance gates.
These are software falsifiers, not market trials, strategy win rates,
a point-in-time data audit or Pine parity.

## Next consumer and proof

Use the existing Macro owner `rs_pullback_launch_data` to bind real
one-minute bars, prior-day leader, source-calendar, stable security
identity, corporate-action basis and known-at receipts. Independently
qualify the exact historical population before running the paired
evaluation in Mastermind #1888; later product research display should
reuse Terminal's already shipped #879 pivot explorer rather than
creating another data store/alert engine. A scientific reviewer must
accept the disjoint exact-code head and source panel before an empirical
result can enter the incumbent Evaluation OS.

No vendor data was collected, copied, authenticated or tested here.
No privileged signal publication, trading authority, or source
admission is granted.
