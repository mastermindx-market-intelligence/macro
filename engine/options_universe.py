"""engine/options_universe.py — the underlyings we snapshot option chains / flow for.

ONE place that resolves the effective options universe so the per-strike GEX accrual
(scripts/build_polygon_gex) and the measured-flow desk (scripts/build_options_flow) read
the SAME set. The universe is the config anchors (the index ETFs + mega-caps that always
have to be there) optionally UNIONED with every active single name in the baskets we trade
(data/baskets/membership.json) — so the per-name flow / positioning / GEX reads extend to
the whole optionable set, not just 10 names.

This source-independent resolver is also consumed by the canonical ThetaData T1
maintainer and AD denominator. Selection makes no provider request and proves neither
entitlement nor optionability. The legacy cap/order is unchanged by default. An explicitly
enabled daily_expansion can retain that whole cohort and add equity-index members and
supplied priorities under a separate total-root budget; missing expansion inputs refuse
rather than silently reducing the existing coverage set.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from datetime import date, datetime

from lib import config

log = logging.getLogger(__name__)

# anchors that must always be in the universe even if config omits them (the index-ETF
# gamma backbone + the most-traded single names) — the historical DEFAULT list.
DEFAULT_ANCHORS = ["SPY", "QQQ", "IWM", "DIA", "NVDA", "AAPL", "TSLA", "AMD", "META", "MSFT"]


def baskets_universe() -> list[str]:
    """Active single-name tickers across every thematic basket (data/baskets/membership.json).
    'Active' = not removed (removed is None). Deduped, ordered. [] if the file is absent."""
    try:
        p = config.data_dir() / "baskets" / "membership.json"
        if not p.exists():
            return []
        doc = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001 — a missing/broken file must never break the build
        log.warning("options_universe: membership read failed (%s)", e)
        return []
    baskets = doc.get("baskets") or {}
    items = baskets.values() if isinstance(baskets, dict) else baskets
    seen: dict[str, None] = {}
    for b in items:
        for m in ((b.get("members") if isinstance(b, dict) else None) or []):
            if isinstance(m, dict):
                if m.get("removed"):           # dropped from the basket -> don't accrue it
                    continue
                t = m.get("ticker")
            else:
                t = m
            if t and isinstance(t, str):
                seen.setdefault(t.upper(), None)
    return list(seen)


def gex_symbols(cfg: dict | None = None) -> list[str]:
    """The effective options universe = config anchors (`polygon.gex.symbols`, or the
    DEFAULT_ANCHORS) optionally unioned with the baskets universe (`include_baskets`), deduped
    with anchors first, capped at `max_underlyings`. Anchors are never dropped by the cap (they
    take the first slots). Pure function of config + the membership file."""
    if cfg is None:
        cfg = (config.load().get("polygon", {}) or {}).get("gex", {}) or {}
    anchors = list(cfg.get("symbols") or DEFAULT_ANCHORS)
    out: list[str] = []
    seen: set[str] = set()
    for t in anchors:                          # anchors first — they keep their slots under the cap
        u = str(t).upper()
        if u not in seen:
            seen.add(u); out.append(u)
    n_anchors = len(out)
    if cfg.get("include_baskets", False):
        for t in baskets_universe():
            if t not in seen:
                seen.add(t); out.append(t)
    cap = int(cfg.get("max_underlyings", 400) or 400)
    capped = out[:max(cap, n_anchors)]         # never let the cap drop an anchor
    if len(out) > len(capped):
        log.info("options_universe: %d underlyings capped to %d (max_underlyings=%d)",
                 len(out), len(capped), cap)
    expansion = cfg.get("daily_expansion")
    if expansion is None:
        return capped
    if not isinstance(expansion, dict) or type(expansion.get("enabled", False)) is not bool:
        raise OptionsUniverseError("invalid_config", field="daily_expansion.enabled")
    if not expansion.get("enabled", False):
        return capped
    return plan_daily_expansion(
        expansion, legacy_symbols=capped, anchor_symbols=out[:n_anchors],
    )["symbols"]


# These are safety bounds on one selection, not account/host capacity grants.
_EXPANSION_KEYS = {"enabled", "as_of", "target_stocks", "max_total_roots", "priority_symbols"}
_EQUITY_GROUPS = ("sp500", "sp400", "sp600", "r2000")
_MEMBERSHIP_LIMIT = 20 * 1024 * 1024
_SYMBOL = re.compile(r"[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)?\Z", re.ASCII)
_MEMBERSHIP_CAVEAT = (
    "Uses canonical as_of_members: cold-start and recorded accrual gaps remain "
    "best-effort. Index membership is a stock classification, not proof of "
    "optionability, source freshness, complete chains, or trading authority."
)


class OptionsUniverseError(ValueError):
    """A named pre-collection refusal with non-secret, machine-readable details."""

    def __init__(self, code: str, **details):
        self.code = code
        self.details = details
        super().__init__(f"{code}: {json.dumps(details, sort_keys=True)}")


def _expansion_symbols(values, *, field: str) -> list[str]:
    if not isinstance(values, (list, tuple)) or len(values) > 5000:
        raise OptionsUniverseError("invalid_config", field=field)
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise OptionsUniverseError("invalid_symbol", field=field)
        symbol = value.strip().upper()
        if len(symbol) > 15 or not _SYMBOL.fullmatch(symbol):
            raise OptionsUniverseError("invalid_symbol", field=field)
        if symbol not in seen:
            seen.add(symbol)
            result.append(symbol)
    return result


def _expansion_int(value, *, field: str, ceiling: int) -> int:
    if type(value) is not int or not 1 <= value <= ceiling:
        raise OptionsUniverseError("invalid_config", field=field, maximum=ceiling)
    return value


def _expansion_day(value) -> date:
    from lib import nyse_calendar

    if isinstance(value, datetime) or isinstance(value, bool):
        raise OptionsUniverseError("invalid_session")
    if isinstance(value, str):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value, flags=re.ASCII):
            raise OptionsUniverseError("invalid_session")
        try:
            value = date.fromisoformat(value)
        except ValueError as exc:
            raise OptionsUniverseError("invalid_session") from exc
    if not isinstance(value, date) or not nyse_calendar.is_session(value):
        raise OptionsUniverseError("invalid_session")
    return value


def _expansion_membership(ledger):
    """Read a single immutable input snapshot without the owner's mkdir helper."""
    import pandas as pd

    source = {"path": "data/universe/membership.parquet", "sha256": None,
              "mode": "injected"}
    if ledger is None:
        path = config.data_dir() / "universe" / "membership.parquet"
        try:
            with path.open("rb") as stream:
                raw = stream.read(_MEMBERSHIP_LIMIT + 1)
        except OSError as exc:
            raise OptionsUniverseError("membership_unavailable") from exc
        if len(raw) > _MEMBERSHIP_LIMIT:
            raise OptionsUniverseError("membership_invalid", reason="input_too_large")
        try:
            ledger = pd.read_parquet(io.BytesIO(raw))
        except Exception as exc:
            raise OptionsUniverseError("membership_invalid", reason="unreadable_parquet") from exc
        source.update(sha256=hashlib.sha256(raw).hexdigest(), mode="file_snapshot")
    required = {"ticker", "group", "first_seen", "last_seen"}
    if not isinstance(ledger, pd.DataFrame) or not required.issubset(ledger.columns):
        raise OptionsUniverseError("membership_invalid", reason="missing_columns")
    # Unknown groups do not become stocks merely because a root was observed.
    selected = ledger.loc[ledger["group"].isin(_EQUITY_GROUPS)].copy()
    try:
        selected["ticker"] = [
            _expansion_symbols([value], field="membership.ticker")[0]
            for value in selected["ticker"]
        ]
    except OptionsUniverseError as exc:
        raise OptionsUniverseError("membership_invalid", reason="invalid_ticker") from exc
    try:
        first = pd.to_datetime(selected["first_seen"], errors="raise", utc=True)
        last = pd.to_datetime(selected["last_seen"], errors="raise", utc=True)
    except (TypeError, ValueError) as exc:
        raise OptionsUniverseError("membership_invalid", reason="invalid_dates") from exc
    if (first.isna() | last.isna() | (first > last)).any():
        raise OptionsUniverseError("membership_invalid", reason="invalid_dates")
    source["rows"] = len(ledger)
    return selected, source


def plan_daily_expansion(expansion: dict, *, legacy_symbols: list[str],
                         anchor_symbols: list[str], ledger=None, as_of=None) -> dict:
    """Select an expanded acquisition cohort through existing membership semantics.

    This is also the non-writing preflight interface. It does not test provider
    entitlement/optionability or start collection. A larger stock target never
    permits dropping an incumbent root or exceeding the explicit total budget.
    """
    from engine.universe_history import as_of_members
    from lib import nyse_calendar

    if not isinstance(expansion, dict) or set(expansion) - _EXPANSION_KEYS:
        raise OptionsUniverseError("invalid_config", field="daily_expansion")
    if "enabled" in expansion and type(expansion["enabled"]) is not bool:
        raise OptionsUniverseError("invalid_config", field="daily_expansion.enabled")
    target = _expansion_int(expansion.get("target_stocks", 1000),
                            field="target_stocks", ceiling=1500)
    budget = _expansion_int(expansion.get("max_total_roots"),
                            field="max_total_roots", ceiling=2000)
    configured_day = expansion.get("as_of")
    if as_of is not None and configured_day is not None:
        if _expansion_day(as_of) != _expansion_day(configured_day):
            raise OptionsUniverseError("invalid_session", reason="conflicting_dates")
    selected_day = as_of if as_of is not None else configured_day
    if selected_day is None:
        selected_day = nyse_calendar.expected_last_session()
    selected_day = _expansion_day(selected_day)
    legacy = _expansion_symbols(legacy_symbols, field="legacy_symbols")
    anchors = _expansion_symbols(anchor_symbols, field="anchor_symbols")
    priorities = _expansion_symbols(expansion.get("priority_symbols", []),
                                    field="priority_symbols")
    if not set(anchors).issubset(legacy):
        raise OptionsUniverseError("invalid_config", field="anchor_symbols",
                                   reason="anchor_not_in_legacy_cohort")
    membership, source = _expansion_membership(ledger)
    equities: list[str] = []
    try:
        for group in _EQUITY_GROUPS:
            equities.extend(as_of_members(selected_day, group=group, ledger=membership))
    except Exception as exc:
        raise OptionsUniverseError("membership_invalid", reason="invalid_dates") from exc
    equities = list(dict.fromkeys(equities))
    stock_set = set(equities)
    if len(stock_set) < target:
        raise OptionsUniverseError("stock_target_unreachable", requested=target,
                                   available_membership_stocks=len(stock_set))

    symbols = list(dict.fromkeys(anchors + priorities + legacy))
    seen = set(symbols)
    retained_stock_count = len(seen & stock_set)
    required_roots = len(symbols) + max(0, target - retained_stock_count)
    if required_roots > budget:
        raise OptionsUniverseError("total_root_budget_exceeded", required=required_roots,
                                   budget=budget, retained_and_priority_roots=len(symbols))
    stock_count = retained_stock_count
    for symbol in equities:
        if stock_count >= target:
            break
        if symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
            stock_count += 1
    classified_stocks = [symbol for symbol in symbols if symbol in stock_set]
    unclassified = [symbol for symbol in symbols if symbol not in stock_set]
    legacy_set = set(legacy)
    return {
        "schema": "options_daily_universe_plan.v1",
        "status": "selection_ready",
        "source_session": selected_day.isoformat(),
        "source": source,
        "membership_caveat": _MEMBERSHIP_CAVEAT,
        "selection_policy": "anchors-priorities-retained-sp500-sp400-sp600-r2000",
        "target_stocks": target,
        "max_total_roots": budget,
        "symbols": symbols,
        "selected_root_count": len(symbols),
        "selected_stock_count": len(classified_stocks),
        "membership_stock_count": len(stock_set),
        "classified_stock_symbols": classified_stocks,
        "roots_not_classified_as_stocks": unclassified,
        "retained_legacy_count": len(legacy),
        "added_symbols": [symbol for symbol in symbols if symbol not in legacy_set],
        "priority_symbols": priorities,
        "uncovered_priority_symbols": [symbol for symbol in priorities if symbol not in seen],
        "target_exceeded_by_retention": retained_stock_count > target,
        "collection_started": False,
        "optionability_verified": False,
        "qualified_stock_count": None,
    }
