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


def qualifying_quotes(
    payload: Any, contract: Contract, *, needed_side: str
) -> list[Quote]:
    if needed_side not in {"bid", "ask"}:
        raise ReplayError("needed_side must be bid or ask")
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
        if bid < 0 or ask < 0 or (bid > 0 and ask > 0 and ask < bid):
            continue
        bid_ok = (
            bid > 0
            and bid_size > 0
            and bid_cond in FIRM_OPRA_QUOTE_CONDITIONS
            and bid_ex in KNOWN_THETA_EXCHANGES
        )
        ask_ok = (
            ask > 0
            and ask_size > 0
            and ask_cond in FIRM_OPRA_QUOTE_CONDITIONS
            and ask_ex in KNOWN_THETA_EXCHANGES
        )
        if (needed_side == "bid" and not bid_ok) or (
            needed_side == "ask" and not ask_ok
        ):
            continue
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


def first_package_quote(
    short_quotes: Sequence[Quote],
    long_quotes: Sequence[Quote],
    *,
    action: str,
    max_leg_age_seconds: Decimal,
) -> PackageQuote | None:
    """Return first causal package-ready NBBO from two asynchronous quote streams.

    ``entry`` sells the short at bid and buys the long at ask (credit).
    ``exit`` buys the short at ask and sells the long at bid (debit).
    """
    if action not in {"entry", "exit"}:
        raise ReplayError("action must be entry or exit")
    events = sorted(
        [(q.timestamp, 0, q) for q in short_quotes]
        + [(q.timestamp, 1, q) for q in long_quotes],
        key=lambda row: (row[0], row[1]),
    )
    latest: dict[int, Quote] = {}
    for now, leg, quote in events:
        latest[leg] = quote
        if len(latest) != 2:
            continue
        short_quote, long_quote = latest[0], latest[1]
        age = Decimal(
            str(
                max(
                    (now - short_quote.timestamp).total_seconds(),
                    (now - long_quote.timestamp).total_seconds(),
                )
            )
        )
        if age > max_leg_age_seconds:
            continue
        value = (
            short_quote.bid - long_quote.ask
            if action == "entry"
            else short_quote.ask - long_quote.bid
        )
        if value <= 0:
            continue
        return PackageQuote(
            now, short_quote.timestamp, long_quote.timestamp, age, value
        )
    return None


def first_target_debit(
    short_quotes: Sequence[Quote],
    long_quotes: Sequence[Quote],
    *,
    target_debit: Decimal,
    max_leg_age_seconds: Decimal,
) -> PackageQuote | None:
    events = sorted(
        [(q.timestamp, 0, q) for q in short_quotes]
        + [(q.timestamp, 1, q) for q in long_quotes],
        key=lambda row: (row[0], row[1]),
    )
    latest: dict[int, Quote] = {}
    for now, leg, quote in events:
        latest[leg] = quote
        if len(latest) != 2:
            continue
        short_quote, long_quote = latest[0], latest[1]
        age = Decimal(
            str(
                max(
                    (now - short_quote.timestamp).total_seconds(),
                    (now - long_quote.timestamp).total_seconds(),
                )
            )
        )
        if age > max_leg_age_seconds:
            continue
        debit = short_quote.ask - long_quote.bid
        if debit >= 0 and debit <= target_debit:
            return PackageQuote(
                now, short_quote.timestamp, long_quote.timestamp, age, debit
            )
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
