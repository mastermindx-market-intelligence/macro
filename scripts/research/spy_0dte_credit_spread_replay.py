#!/usr/bin/env python3
"""Read-only forensic replay helpers for SPY 0DTE vertical credit spreads.

Research only: no signal, sizing, order, or trade authority. The module consumes
ThetaData v3 option-history quote payloads and applies conservative side-specific
NBBO accounting. Raw licensed payloads are never persisted by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

FIRM_OPRA_QUOTE_CONDITIONS = frozenset(
    {0, 1, 3, 4, 5, 7, 8, 12, 13, 14, 15, 16, 42, 48, 49, 50, 51, 52, 53, 54, 56}
)
KNOWN_THETA_EXCHANGES = frozenset(set(range(1, 78)) - {74, 76})
SYNCHRONY_GRID_SECONDS = (
    Decimal("0.1"), Decimal("1"), Decimal("5"), Decimal("10")
)


class ReplayError(ValueError):
    pass


@dataclass(frozen=True)
class Contract:
    root: str
    expiration: str
    strike: Decimal
    right: str


@dataclass(frozen=True)
class Quote:
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    bid_size: int
    ask_size: int
    bid_exchange: int
    ask_exchange: int
    bid_condition: int
    ask_condition: int


@dataclass(frozen=True)
class PackageQuote:
    timestamp: datetime
    short_quote_at: datetime
    long_quote_at: datetime
    leg_age_seconds: Decimal
    value: Decimal
    long_liquidation_zero: bool = False


def _decimal(value: Any, label: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except Exception as exc:
        raise ReplayError(f"{label} is not decimal") from exc
    if not out.is_finite():
        raise ReplayError(f"{label} is not finite")
    return out


def _source_rows(payload: Any, contract: Contract) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping) or set(payload) != {"response"}:
        raise ReplayError("Theta quote payload wrapper is not exact")
    groups = payload["response"]
    if (
        not isinstance(groups, list)
        or len(groups) != 1
        or not isinstance(groups[0], Mapping)
    ):
        raise ReplayError("Theta quote payload must contain one contract group")
    group = groups[0]
    if set(group) != {"contract", "data"}:
        raise ReplayError("Theta contract group fields are not exact")
    identity = group["contract"]
    if not isinstance(identity, Mapping):
        raise ReplayError("Theta contract identity is malformed")
    if (
        str(identity.get("symbol", "")).upper() != contract.root.upper()
        or str(identity.get("expiration")) != contract.expiration
        or _decimal(identity.get("strike"), "source strike") != contract.strike
        or str(identity.get("right", "")).lower() != contract.right.lower()
    ):
        raise ReplayError("Theta response returned a different exact contract")
    rows = group["data"]
    if not isinstance(rows, list):
        raise ReplayError("Theta quote data is not a list")
    return rows


def _parsed_quotes(payload: Any, contract: Contract) -> list[Quote]:
    out: list[Quote] = []
    for raw in _source_rows(payload, contract):
        if not isinstance(raw, Mapping):
            raise ReplayError("Theta quote row is malformed")
        try:
            ts = datetime.fromisoformat(str(raw["timestamp"]))
            bid = _decimal(raw["bid"], "bid")
            ask = _decimal(raw["ask"], "ask")
            bid_size, ask_size = int(raw["bid_size"]), int(raw["ask_size"])
            bid_ex, ask_ex = int(raw["bid_exchange"]), int(raw["ask_exchange"])
            bid_cond, ask_cond = int(raw["bid_condition"]), int(raw["ask_condition"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReplayError("Theta quote row fields are malformed") from exc
        out.append(
            Quote(
                ts,
                bid,
                ask,
                bid_size,
                ask_size,
                bid_ex,
                ask_ex,
                bid_cond,
                ask_cond,
            )
        )
    out.sort(key=lambda quote: quote.timestamp)
    return out


def _quote_state_valid(quote: Quote) -> bool:
    return (
        quote.bid >= 0
        and quote.ask >= 0
        and not (quote.bid > 0 and quote.ask > 0 and quote.ask < quote.bid)
    )


def _positive_firm_side(quote: Quote, side: str) -> bool:
    if not _quote_state_valid(quote):
        return False
    if side == "bid":
        return (
            quote.bid > 0
            and quote.bid_size > 0
            and quote.bid_condition in FIRM_OPRA_QUOTE_CONDITIONS
            and quote.bid_exchange in KNOWN_THETA_EXCHANGES
        )
    if side == "ask":
        return (
            quote.ask > 0
            and quote.ask_size > 0
            and quote.ask_condition in FIRM_OPRA_QUOTE_CONDITIONS
            and quote.ask_exchange in KNOWN_THETA_EXCHANGES
        )
    raise ReplayError("side must be bid or ask")


def source_quotes(payload: Any, contract: Contract) -> list[Quote]:
    """Return every structurally parsed source quote, including invalidating states."""
    return _parsed_quotes(payload, contract)


def exit_side_executable(quote: Quote, role: str) -> bool:
    if role == "short":
        return _positive_firm_side(quote, "ask")
    if role == "long":
        return _positive_firm_side(quote, "bid") or (
            quote.bid == 0 and _positive_firm_side(quote, "ask")
        )
    raise ReplayError("role must be short or long")


def qualifying_quotes(
    payload: Any, contract: Contract, *, needed_side: str
) -> list[Quote]:
    if needed_side not in {"bid", "ask"}:
        raise ReplayError("needed_side must be bid or ask")
    return [
        quote
        for quote in _parsed_quotes(payload, contract)
        if _positive_firm_side(quote, needed_side)
    ]


def qualifying_exit_quotes(
    payload: Any, contract: Contract, *, role: str
) -> list[Quote]:
    """Return source-present executable exit rows without imputing a long bid.

    A short leg still requires a positive firm ask. A long leg normally requires
    a positive firm bid. If the source row instead carries an exact zero bid but
    a positive firm ask, the row is admitted only for conservative short-only
    close accounting: the long receives zero liquidation credit and remains
    residual positive optionality. Missing/malformed rows never become zero.
    """
    if role not in {"short", "long"}:
        raise ReplayError("role must be short or long")
    return [
        quote for quote in _parsed_quotes(payload, contract)
        if exit_side_executable(quote, role)
    ]


def _package_from_state(
    now: datetime,
    short_quote: Quote,
    long_quote: Quote,
    *,
    action: str,
    max_leg_age_seconds: Decimal,
) -> PackageQuote | None:
    age = Decimal(
        str(
            max(
                (now - short_quote.timestamp).total_seconds(),
                (now - long_quote.timestamp).total_seconds(),
            )
        )
    )
    if age < 0 or age > max_leg_age_seconds:
        return None
    if action == "entry":
        if not (
            _positive_firm_side(short_quote, "bid")
            and _positive_firm_side(long_quote, "ask")
        ):
            return None
        value = short_quote.bid - long_quote.ask
        if value <= 0:
            return None
        long_zero = False
    elif action == "exit":
        if not _positive_firm_side(short_quote, "ask"):
            return None
        long_zero = (
            long_quote.bid == 0 and _positive_firm_side(long_quote, "ask")
        )
        if not (_positive_firm_side(long_quote, "bid") or long_zero):
            return None
        value = short_quote.ask - long_quote.bid
        if value < 0:
            return None
    else:
        raise ReplayError("action must be entry or exit")
    return PackageQuote(
        now,
        short_quote.timestamp,
        long_quote.timestamp,
        age,
        value,
        long_zero,
    )


def package_quotes(
    short_quotes: Sequence[Quote],
    long_quotes: Sequence[Quote],
    *,
    action: str,
    max_leg_age_seconds: Decimal,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[PackageQuote]:
    """Return causal executable package states from full source quote streams.

    Every source row updates current state, including zero/non-firm/crossed rows,
    so a stale previously firm side cannot survive a newer invalidating quote.
    Equal-timestamp leg updates are applied together before package evaluation.
    When ``start_at`` is supplied, all prior rows seed state and one package is
    evaluated exactly at that timestamp before later events are processed.
    """
    if action not in {"entry", "exit"}:
        raise ReplayError("action must be entry or exit")
    if end_at is not None and start_at is not None and end_at < start_at:
        raise ReplayError("package end precedes start")
    events = sorted(
        [(q.timestamp, 0, q) for q in short_quotes]
        + [(q.timestamp, 1, q) for q in long_quotes],
        key=lambda row: (row[0], row[1]),
    )
    latest: dict[int, Quote] = {}
    out: list[PackageQuote] = []
    index = 0

    def apply_timestamp(timestamp: datetime) -> None:
        nonlocal index
        while index < len(events) and events[index][0] == timestamp:
            _, leg, quote = events[index]
            latest[leg] = quote
            index += 1

    def maybe_emit(now: datetime) -> None:
        if len(latest) != 2:
            return
        package = _package_from_state(
            now, latest[0], latest[1],
            action=action, max_leg_age_seconds=max_leg_age_seconds,
        )
        if package is not None:
            out.append(package)

    if start_at is not None:
        while index < len(events) and events[index][0] <= start_at:
            apply_timestamp(events[index][0])
        maybe_emit(start_at)

    while index < len(events):
        now = events[index][0]
        if start_at is not None and now <= start_at:
            apply_timestamp(now)
            continue
        if end_at is not None and now > end_at:
            break
        apply_timestamp(now)
        maybe_emit(now)
    return out


def first_package_quote(
    short_quotes: Sequence[Quote],
    long_quotes: Sequence[Quote],
    *,
    action: str,
    max_leg_age_seconds: Decimal,
) -> PackageQuote | None:
    """Return the first executable package from full source quote streams."""
    packages = package_quotes(
        short_quotes, long_quotes, action=action,
        max_leg_age_seconds=max_leg_age_seconds,
    )
    return packages[0] if packages else None


def first_target_debit(
    short_quotes: Sequence[Quote],
    long_quotes: Sequence[Quote],
    *,
    target_debit: Decimal,
    max_leg_age_seconds: Decimal,
) -> PackageQuote | None:
    for package in package_quotes(
        short_quotes, long_quotes, action="exit",
        max_leg_age_seconds=max_leg_age_seconds,
    ):
        if package.value <= target_debit:
            return package
    return None


def net_pnl_per_spread(
    entry_credit: Decimal,
    exit_debit: Decimal,
    *,
    fee_per_contract_side: Decimal,
) -> Decimal:
    # 2 legs at entry + 2 legs at exit = four contract-sides per 1-lot vertical.
    return (
        (entry_credit - exit_debit) * Decimal(100)
        - fee_per_contract_side * Decimal(4)
    )


def infer_spread_count(
    reported_net_pnl: Decimal, net_per_spread: Decimal
) -> tuple[int, Decimal]:
    if reported_net_pnl <= 0 or net_per_spread <= 0:
        raise ReplayError("P&L inputs must be positive")
    count = max(
        1,
        int((reported_net_pnl / net_per_spread).to_integral_value()),
    )
    residual = reported_net_pnl - net_per_spread * count
    return count, residual


def structural_max_loss_per_spread(
    width: Decimal, entry_credit: Decimal
) -> Decimal:
    if width <= 0 or entry_credit <= 0 or entry_credit >= width:
        raise ReplayError("width/credit are invalid")
    return (width - entry_credit) * Decimal(100)
