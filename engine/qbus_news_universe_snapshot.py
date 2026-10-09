"""Compose the current S&P news universe from incumbent membership and identity owners.

Pure leaf: no filesystem, pandas, network, ambient clock, or source discovery.

Inputs are already-read rows from the current S&P 500 roster owner, S&P PIT
membership owner, Data OS vendor aliases, and Data OS security master.

The builder refuses rather than guesses. Current breadth and active PIT membership
must agree exactly; every member must resolve through the canonical membership
alias namespace to an active security-master row; and every resolved security must
have a current yahoo_fetch alias for present-market/provider routing.

Observation time is knowledge evidence and freshness policy, never content identity:
the revision digest excludes known_at and fresh_until.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from typing import Iterable, Mapping

from lib.dataos.identity import IdentityError, IssuerMaster, VendorAliasTable

from engine.qbus_news_universe import qualify_universe

OWNER = "breadth.sp500+reference.security_master"
SCHEMA = "qbus.news_universe_snapshot.v1"


class NewsUniverseSnapshotError(ValueError):
    """Fail-closed snapshot composition error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"qbus_news_universe_snapshot:{code}")


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise NewsUniverseSnapshotError("observed_at_invalid")
    return value.astimezone(timezone.utc)


def _is_nullish(value: object) -> bool:
    if value is None:
        return True
    try:
        unequal = value != value
        if isinstance(unequal, bool) and unequal:
            return True
    except Exception:
        pass
    return str(value).strip().lower() in {"", "nat", "nan", "none", "<na>"}


def _date_value(value: object, code: str, *, nullable: bool = False) -> date | None:
    if _is_nullish(value):
        if nullable:
            return None
        raise NewsUniverseSnapshotError(code)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    to_pydatetime = getattr(value, "to_pydatetime", None)
    if callable(to_pydatetime):
        try:
            converted = to_pydatetime()
        except Exception:
            converted = None
        if isinstance(converted, datetime):
            return converted.date()
        if isinstance(converted, date):
            return converted
    raw = str(value).strip()
    try:
        if "T" in raw or " " in raw:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        return date.fromisoformat(raw)
    except ValueError:
        raise NewsUniverseSnapshotError(code) from None


def _midnight_utc(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _symbol(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise NewsUniverseSnapshotError(code)
    out = value.strip().upper()
    if not out or len(out) > 64 or "\x00" in out:
        raise NewsUniverseSnapshotError(code)
    return out


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _revision(securities: list[dict[str, object]]) -> str:
    identity = {
        "schema": SCHEMA,
        "owner": OWNER,
        "securities": [
            {
                "security_id": row["security_id"],
                "ticker": row["ticker"],
                "aliases": row["aliases"],
            }
            for row in sorted(securities, key=lambda item: str(item["security_id"]))
        ],
    }
    digest = hashlib.sha256(_stable_json(identity).encode("utf-8")).hexdigest()
    return f"sp500-news-{digest}"


def _current_symbols(rows: Iterable[Mapping[str, object]]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise NewsUniverseSnapshotError("current_roster_row_invalid")
        token = _symbol(
            raw.get("symbol") if raw.get("symbol") is not None else raw.get("ticker"),
            "current_roster_symbol_invalid",
        )
        if token in seen:
            raise NewsUniverseSnapshotError("current_roster_duplicate")
        seen.add(token)
        out.append(token)
    return tuple(out)


def _active_pit(
    rows: Iterable[Mapping[str, object]],
    *,
    on: date,
) -> dict[str, date]:
    active: dict[str, date] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise NewsUniverseSnapshotError("pit_row_invalid")
        if str(raw.get("src") or "").strip().lower() != "sp500":
            continue
        ticker = _symbol(raw.get("ticker"), "pit_ticker_invalid")
        start = _date_value(raw.get("start_date"), "pit_start_invalid")
        assert start is not None
        end = _date_value(raw.get("end_date"), "pit_end_invalid", nullable=True)
        if end is not None and end <= start:
            raise NewsUniverseSnapshotError("pit_interval_invalid")
        if start <= on and (end is None or on < end):
            if ticker in active:
                raise NewsUniverseSnapshotError("pit_active_duplicate")
            active[ticker] = start
    return active


def build_news_universe_snapshot(
    current_rows: Iterable[Mapping[str, object]],
    pit_rows: Iterable[Mapping[str, object]],
    alias_rows: Iterable[Mapping[str, object]],
    security_rows: Iterable[Mapping[str, object]],
    *,
    observed_at: datetime,
    fresh_for: timedelta = timedelta(hours=36),
    min_count: int = 400,
) -> dict[str, object]:
    """Build one exact current S&P 500 news-universe snapshot."""

    observed = _aware_utc(observed_at)
    if not isinstance(fresh_for, timedelta) or fresh_for <= timedelta(0):
        raise NewsUniverseSnapshotError("fresh_for_invalid")
    if isinstance(min_count, bool) or not isinstance(min_count, int) or min_count < 1:
        raise NewsUniverseSnapshotError("min_count_invalid")

    current = _current_symbols(current_rows)
    if len(current) < min_count:
        raise NewsUniverseSnapshotError("current_roster_suspicious")

    active_pit = _active_pit(pit_rows, on=observed.date())

    cleaned_alias_rows: list[dict[str, object]] = []
    for raw in alias_rows:
        if not isinstance(raw, Mapping):
            raise NewsUniverseSnapshotError("alias_table_invalid")
        rec = dict(raw)
        for field in ("valid_from", "valid_to"):
            value = rec.get(field)
            if _is_nullish(value):
                rec[field] = None
            else:
                parsed = _date_value(value, f"alias_{field}_invalid")
                rec[field] = None if parsed is None else parsed
        cleaned_alias_rows.append(rec)

    try:
        aliases = VendorAliasTable.from_records(cleaned_alias_rows)
    except (IdentityError, TypeError, ValueError):
        raise NewsUniverseSnapshotError("alias_table_invalid") from None

    historical_alias_spaces = frozenset(
        {"membership", "yahoo", "yahoo_fetch", "store", "ledger"}
    )
    historical_security_ids: dict[str, set[str]] = {}
    for row in aliases.rows:
        if row.vendor not in historical_alias_spaces:
            continue
        token = _symbol(row.vendor_symbol, "historical_alias_invalid")
        historical_security_ids.setdefault(token, set()).add(row.security_id)

    pit_start_by_security: dict[str, date] = {}
    pit_unresolved = 0
    for ticker, start in active_pit.items():
        candidates = historical_security_ids.get(ticker, set())
        if len(candidates) != 1:
            pit_unresolved += 1
            continue
        sid = next(iter(candidates))
        prior = pit_start_by_security.get(sid)
        if prior is None or start < prior:
            pit_start_by_security[sid] = start

    try:
        security_master = IssuerMaster.from_records(list(security_rows))
    except (IdentityError, TypeError, ValueError):
        raise NewsUniverseSnapshotError("security_master_invalid") from None

    master_rows = {row.security_id: row for row in security_master.rows}
    securities: list[dict[str, object]] = []
    seen_security_ids: set[str] = set()

    for ticker in sorted(current):
        security_id = aliases.resolve("membership", ticker, observed.date())
        if not security_id:
            raise NewsUniverseSnapshotError("membership_alias_unresolved")
        if security_id in seen_security_ids:
            raise NewsUniverseSnapshotError("duplicate_security_resolution")
        seen_security_ids.add(security_id)

        if security_id not in master_rows:
            raise NewsUniverseSnapshotError("security_master_unresolved")
        if security_master.security_state_of(security_id):
            raise NewsUniverseSnapshotError("security_master_superseded")

        market_alias = aliases.vendor_symbol_for(
            "yahoo_fetch", security_id, observed.date()
        )
        if not market_alias:
            raise NewsUniverseSnapshotError("market_alias_unresolved")
        market_alias = _symbol(market_alias, "market_alias_invalid")

        row_aliases = [ticker]
        if market_alias not in row_aliases:
            row_aliases.append(market_alias)

        start = pit_start_by_security.get(security_id)
        membership_basis = "pit_identity_match"
        if start is None:
            start = observed.date()
            membership_basis = "current_observation"
        securities.append(
            {
                "security_id": security_id,
                "ticker": ticker,
                "aliases": row_aliases,
                "valid_from": _midnight_utc(start).isoformat(),
                "valid_to": None,
                "known_at": observed.isoformat(),
                "membership_basis": membership_basis,
            }
        )

    if not securities:
        raise NewsUniverseSnapshotError("empty_universe")

    effective_at = max(
        datetime.fromisoformat(str(row["valid_from"])) for row in securities
    )
    current_security_ids = {
        str(row["security_id"]) for row in securities
    }
    matched_security_ids = current_security_ids.intersection(pit_start_by_security)
    snapshot: dict[str, object] = {
        "schema": SCHEMA,
        "owner": OWNER,
        "revision": _revision(securities),
        "complete": True,
        "truncated": False,
        "effective_at": effective_at.isoformat(),
        "known_at": observed.isoformat(),
        "fresh_until": (observed + fresh_for).isoformat(),
        "current_membership_authority": "breadth.current_sp500",
        "pit_context_authority": "breadth.sp1500_pit_membership",
        "pit_context_active_count": len(active_pit),
        "pit_context_matched_security_count": len(matched_security_ids),
        "current_observation_only_count": len(current_security_ids - matched_security_ids),
        "pit_context_stale_only_count": len(
            set(pit_start_by_security) - current_security_ids
        ),
        "pit_context_unresolved_count": pit_unresolved,
        "securities": securities,
    }

    qualified = qualify_universe(snapshot, asof=observed)
    if qualified.status != "qualified" or qualified.count != len(securities):
        raise NewsUniverseSnapshotError("qualification_failed")
    return snapshot
