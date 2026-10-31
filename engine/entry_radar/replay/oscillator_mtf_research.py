"""Read-only session-native 120m/180m RSI-MACD research consumer.

This is NOT a new market collector, candle archive, PIT/identity/calendar owner,
Radar detector, signal bus, trading instruction, or vendor-data admission. It
calls an injected *existing* qualified Macro minute-aggregate read contract.
No historical observed-market outcome or live signal is emitted here.
"""
from __future__ import annotations

from datetime import date
from numbers import Real
from typing import Any, Callable, Mapping
import math

import numpy as np
import pandas as pd

from engine import canon

NY = "America/New_York"
ALLOWED_GRAINS = frozenset({120, 180})
INDICATORS = frozenset({"CANON_RSI_MACD", "PRICE_MACD_RSI_PROXY", "SUPPLIED_LINES"})


def _instant(value: Any) -> pd.Timestamp:
    if not isinstance(value, (str, pd.Timestamp)):
        raise ValueError("UTC-aware source timestamp required")
    try:
        t = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid source timestamp") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("naive/display timestamp forbidden")
    return t.tz_convert("UTC")


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _session(day: date, bounds: tuple[Any, Any]) -> tuple[pd.Timestamp, pd.Timestamp]:
    if type(day) is not date or not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise ValueError("owner calendar requires exact session date and clock pair")
    opening, closing = _instant(bounds[0]), _instant(bounds[1])
    ny0, ny1 = opening.tz_convert(NY), closing.tz_convert(NY)
    if (ny0.date() != day or ny1.date() != day or
            (ny0.hour, ny0.minute, ny0.second) != (9, 30, 0) or
            (ny1.hour, ny1.minute, ny1.second) > (16, 0, 0) or
            opening >= closing or (closing - opening).total_seconds() % 60):
        raise ValueError("invalid exchange-calendar owner window")
    return opening, closing


def _approved_ohlcv(value: Any) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    keys = ("open", "high", "low", "close", "volume")
    if any(not isinstance(value.get(k), Real) or isinstance(value.get(k), (bool, np.bool_))
           or not math.isfinite(value[k]) for k in keys):
        return None
    o, h, l, c, v = (float(value[k]) for k in keys)
    if not (0 < l <= min(o, c) <= max(o, c) <= h and v >= 0):
        return None
    return dict(zip(keys, (o, h, l, c, v)))


def aggregate_owner_windows(*, symbol: str, calendar: Mapping[date, tuple[Any, Any]],
                            decision_utc: str, minutes: int,
                            read_aggregate: Callable[[str, str, str, str], Mapping[str, Any]]
                            ) -> list[dict[str, Any]]:
    """Build only native FULL RTH windows using injected Macro owner receipts.

    Reader contract is the existing _aggregate shape:
    availability, start/end, expected_minutes, observed_minutes, ohlcv,
    known_at, input_revision_sha256. We validate consistency, NOT authenticity.
    No reader call occurs for future, incomplete, or trailing stub windows.
    """
    if not isinstance(symbol, str) or not symbol.strip() or minutes not in ALLOWED_GRAINS:
        raise ValueError("nonempty symbol and 120m/180m grain required")
    if not isinstance(calendar, Mapping) or not calendar or not callable(read_aggregate):
        raise ValueError("owner calendar and owner-read callback required")
    cutoff = _instant(decision_utc)
    rows = []
    for day, pair in sorted(calendar.items()):
        opening, closing = _session(day, pair)
        if opening > cutoff:
            continue
        n, stub = divmod(int((closing-opening).total_seconds() // 60), minutes)
        for i in range(n):
            start = opening + pd.Timedelta(minutes=i*minutes)
            end = start + pd.Timedelta(minutes=minutes)
            row = {"schema": "macro.rs_oscillator_mtf_bars.v1", "symbol": symbol,
                   "session_date": day.isoformat(), "grain_minutes": minutes,
                   "bar_start_utc": start.isoformat(), "bar_end_utc": end.isoformat(),
                   "known_at_utc": None, "source_sha256": None, "ohlcv": None,
                   "status": "NOT_YET_OBSERVED", "refusals": [],
                   "source_admitted": False}
            if end <= cutoff:
                source = read_aggregate(symbol, start.isoformat(), end.isoformat(), cutoff.isoformat())
                if not isinstance(source, Mapping):
                    raise ValueError("owner reader must return a structured receipt")
                reasons = list(source.get("refusals", []))
                if source.get("availability") != "available":
                    row.update(status="UNAVAILABLE", refusals=sorted(set(map(str, reasons)) or
                                                              {"OWNER_WINDOW_UNAVAILABLE"}))
                else:
                    prices = _approved_ohlcv(source.get("ohlcv"))
                    try:
                        known = _instant(source.get("known_at"))
                        src_start, src_end = _instant(source.get("start")), _instant(source.get("end"))
                    except ValueError:
                        known = None
                        src_start = src_end = None
                    good = (not reasons and prices is not None and known is not None and
                            end <= known <= cutoff and src_start == start and src_end == end and
                            type(source.get("expected_minutes")) is int and
                            type(source.get("observed_minutes")) is int and
                            source["expected_minutes"] == source["observed_minutes"] == minutes and
                            _sha(source.get("input_revision_sha256")))
                    if good:
                        row.update(status="FULL_KNOWN", ohlcv=prices,
                                   known_at_utc=known.isoformat(),
                                   source_sha256=source["input_revision_sha256"])
                    else:
                        row.update(status="UNAVAILABLE", refusals=["INVALID_OR_LATE_OWNER_RECEIPT"])
            rows.append(row)
        if stub:
            # The stub is a calendar fact, not an observed bar or a trade entry.
            start = opening + pd.Timedelta(minutes=n*minutes)
            rows.append({"schema": "macro.rs_oscillator_mtf_bars.v1", "symbol": symbol,
                         "session_date": day.isoformat(), "grain_minutes": minutes,
                         "bar_start_utc": start.isoformat(), "bar_end_utc": closing.isoformat(),
                         "known_at_utc": None, "source_sha256": None, "ohlcv": None,
                         "status": "STUB_EXCLUDED", "stub_minutes": stub,
                         "refusals": ["NONFULL_SESSION_STUB"], "source_admitted": False})
    return rows


def _indicator_segment(closes: list[float], kind: str) -> tuple[pd.Series, pd.Series, pd.Series]:
    s = pd.Series(closes, dtype=float)
    if kind == "CANON_RSI_MACD":
        line, signal = canon.rsi_macd(s)
        flag = pd.Series(True, index=s.index)
    elif kind == "PRICE_MACD_RSI_PROXY":
        line = canon.ema(s, 12) - canon.ema(s, 26)
        signal = canon.ema(line, 9)
        flag = canon.rsi(s, 14) <= 40
    else:
        raise ValueError("supplied indicator lines use a different input path")
    return line, signal, flag


def oscillator_events(*, bars: list[dict[str, Any]], indicator: str,
                      eligibility: Mapping[tuple[str, str], Mapping[str, Any]],
                      decision_cutoff_utc: str,
                      supplied: Mapping[tuple[str, str], Mapping[str, Any]] | None = None
                      ) -> list[dict[str, Any]]:
    """Emit null-safe descriptive crossover states, never live trading signals.

    Same opportunity clock and prior-day leader must be supplied; this module
    neither ranks RS leaders nor applies the incumbent tactical Entry Engine.
    A missing full 2H/3H window resets oscillator history rather than silently
    treating missing prices as no-trade or carrying a fabricated signal.
    """
    if indicator not in INDICATORS or not isinstance(eligibility, Mapping):
        raise ValueError("frozen known oscillator species and eligibility map required")
    if indicator == "SUPPLIED_LINES" and not isinstance(supplied, Mapping):
        raise ValueError("exact exported indicator lines must be supplied explicitly")
    cutoff = _instant(decision_cutoff_utc)
    lines = []
    events = []
    sorted_bars = sorted(bars, key=lambda b: (b["symbol"], b["bar_end_utc"]))
    grains: dict[str, int] = {}
    observed_keys: set[tuple[str, str]] = set()
    for idx, bar in enumerate(sorted_bars):
        if bar.get("schema") != "macro.rs_oscillator_mtf_bars.v1":
            raise ValueError("unexpected bar schema")
        status = bar.get("status")
        if status not in {"FULL_KNOWN", "UNAVAILABLE", "NOT_YET_OBSERVED", "STUB_EXCLUDED"}:
            raise ValueError("unexpected source status")
        sym, grain = bar.get("symbol"), bar.get("grain_minutes")
        if not isinstance(sym, str) or not sym.strip() or type(grain) is not int or grain not in ALLOWED_GRAINS:
            raise ValueError("invalid symbol or 120m/180m research grain")
        if sym in grains and grains[sym] != grain:
            raise ValueError("cannot mix 120m and 180m oscillator bars for one symbol")
        grains[sym] = grain
        bar_key = (sym, bar.get("bar_end_utc"))
        if bar_key in observed_keys:
            raise ValueError("duplicate observed bar identity")
        observed_keys.add(bar_key)
        # The caller must retain every full source interval, including failed
        # ones. Otherwise dropping a missing candle can splice the previous
        # oscillator sample directly to a future one and mint a false cross.
        start, finish = _instant(bar.get("bar_start_utc")), _instant(bar.get("bar_end_utc"))
        try:
            local_day = date.fromisoformat(bar["session_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("bar/session NY date invalid") from exc
        if (start.tz_convert(NY).date() != local_day or
                finish.tz_convert(NY).date() != local_day or finish <= start):
            raise ValueError("bar/session NY date mismatch")
        prev = sorted_bars[idx-1] if idx else None
        if prev is None or prev["symbol"] != sym or prev["session_date"] != bar["session_date"]:
            if (start.tz_convert(NY).hour, start.tz_convert(NY).minute) != (9, 30):
                raise ValueError("missing opening full bar from session")
        elif _instant(prev["bar_end_utc"]) != start:
            raise ValueError("missing or overlapping RTH bar observations")
        if idx and sorted_bars[idx-1]["symbol"] != bar["symbol"]:
            lines = []
        if status != "FULL_KNOWN":
            if status != "STUB_EXCLUDED":
                lines = []
            events.append({"symbol": bar["symbol"], "bar_end_utc": bar["bar_end_utc"],
                           "indicator": indicator, "state": "SOURCE_" + status,
                           "signal": None, "issued_at_utc": None, "source_admitted": False})
            continue
        key = (bar["symbol"], bar["bar_end_utc"])
        ending = _instant(bar["bar_end_utc"])
        known = _instant(bar.get("known_at_utc"))
        if (known < ending or known > cutoff or _approved_ohlcv(bar.get("ohlcv")) is None or
                ending - _instant(bar.get("bar_start_utc")) != pd.Timedelta(minutes=grain) or
                not _sha(bar.get("source_sha256")) or bar.get("refusals")):
            raise ValueError("inconsistent full bar/availability")
        lines.append(bar)
        ready = False
        oscillator_known = known
        if indicator == "SUPPLIED_LINES":
            obs = supplied.get(key)
            if isinstance(obs, Mapping) and all(type(obs.get(k)) in (int, float)
                                                and math.isfinite(obs[k]) for k in ("fast", "slow")) \
                    and type(obs.get("oversold")) is bool and \
                    obs.get("source_sha256") == bar.get("source_sha256"):
                try:
                    oscillator_known = _instant(obs.get("known_at_utc"))
                    ready = known <= oscillator_known <= cutoff
                except ValueError:
                    ready = False
                if ready:
                    # Same original bar revision/basis is required for the
                    # previous indicator input. A digest tests consistency,
                    # never authenticates the upstream source.
                    previous_bar = lines[-2] if len(lines) > 1 else None
                    prev = (supplied.get((previous_bar["symbol"], previous_bar["bar_end_utc"]))
                            if previous_bar is not None else None)
                    if (isinstance(prev, Mapping) and
                            prev.get("source_sha256") == previous_bar.get("source_sha256") and
                            all(type(prev.get(k)) in (int, float) and math.isfinite(prev[k])
                                for k in ("fast", "slow"))):
                        try:
                            prev_known = _instant(prev.get("known_at_utc"))
                            ready = (_instant(previous_bar["known_at_utc"]) <= prev_known <= cutoff)
                        except ValueError:
                            ready = False
                        if ready:
                            line, sig, p_line, p_sig = (obs["fast"], obs["slow"], prev["fast"], prev["slow"])
                            oscillator_known = max(oscillator_known, prev_known)
                            flag = obs["oversold"]
                    else:
                        ready = False
        else:
            line_s, sig_s, flags = _indicator_segment([x["ohlcv"]["close"] for x in lines], indicator)
            if len(lines) >= 2 and all(math.isfinite(z) for z in
                                       (line_s.iloc[-1], sig_s.iloc[-1], line_s.iloc[-2], sig_s.iloc[-2])):
                line, sig, p_line, p_sig = (line_s.iloc[-1], sig_s.iloc[-1],
                                            line_s.iloc[-2], sig_s.iloc[-2])
                flag = bool(flags.iloc[-1])
                ready = True
        if not ready:
            state, cross = "WARMUP_OR_OSCILLATOR_UNAVAILABLE", None
        else:
            cross = bool(p_line <= p_sig and line > sig and line < 0 and sig < 0 and flag)
            state = "CROSS_OBSERVED" if cross else "NO_CROSS"
        candidate = eligibility.get(key)
        issued = oscillator_known
        if not isinstance(candidate, Mapping):
            state, cross = "ELIGIBILITY_UNAVAILABLE", None
        else:
            try:
                owner_known = _instant(candidate.get("known_at_utc"))
                asof = date.fromisoformat(candidate["asof_session"])
            except (ValueError, TypeError, KeyError):
                state, cross = "ELIGIBILITY_UNAVAILABLE", None
            else:
                if (type(candidate.get("is_leader")) is not bool or
                        candidate.get("expected_prior_session") != candidate.get("asof_session") or
                        asof >= date.fromisoformat(bar["session_date"]) or
                        not _sha(candidate.get("receipt_sha256")) or owner_known > cutoff):
                    state, cross = "ELIGIBILITY_UNAVAILABLE", None
                else:
                    issued = max(known, oscillator_known, owner_known)
                    if not candidate["is_leader"]:
                        state, cross = "NOT_LEADER", None
                    # Signal availability is the last source receipt, not bar close.
                    # Do not infer a tradable fill from descriptive crossover state.
        events.append({"symbol": bar["symbol"], "bar_end_utc": bar["bar_end_utc"],
                       "indicator": indicator, "state": state, "signal": cross,
                       "issued_at_utc": issued.isoformat() if cross is not None else None,
                       "source_admitted": False})
    return events
