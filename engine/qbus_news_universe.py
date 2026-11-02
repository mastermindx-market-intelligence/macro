"""Point-in-time qualification for an injected security-universe snapshot.

Pure leaf: this module does not discover constituents or own security identity. It
validates one snapshot from the incumbent owner and exposes deterministic alias
bindings for downstream news routing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True, slots=True)
class QualifiedSecurity:
    security_id: str
    ticker: str
    aliases: tuple[str, ...]
    valid_from: datetime
    valid_to: datetime | None
    known_at: datetime


@dataclass(frozen=True, slots=True)
class AliasBinding:
    alias: str
    security_id: str


@dataclass(frozen=True, slots=True)
class UniverseQualification:
    status: str
    owner: str
    revision: str
    asof: datetime
    count: int
    securities: tuple[QualifiedSecurity, ...]
    alias_bindings: tuple[AliasBinding, ...]
    excluded: tuple[tuple[str, str], ...]
    reason_codes: tuple[str, ...]
    ambiguous_aliases: tuple[str, ...]


def _dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            out = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if out.tzinfo is None or out.utcoffset() is None:
                return None
            return out.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _hold(
    snapshot: Mapping[str, object],
    asof: datetime,
    reasons: list[str],
    *,
    securities: tuple[QualifiedSecurity, ...] = (),
    aliases: tuple[AliasBinding, ...] = (),
    excluded: tuple[tuple[str, str], ...] = (),
    ambiguous: tuple[str, ...] = (),
) -> UniverseQualification:
    return UniverseQualification(
        status="held",
        owner=str(snapshot.get("owner") or ""),
        revision=str(snapshot.get("revision") or ""),
        asof=asof,
        count=len(securities),
        securities=securities,
        alias_bindings=aliases,
        excluded=excluded,
        reason_codes=tuple(dict.fromkeys(reasons)),
        ambiguous_aliases=ambiguous,
    )


def qualify_universe(
    snapshot: Mapping[str, object], *, asof: datetime
) -> UniverseQualification:
    """Qualify an owner-supplied membership snapshot at one decision time.

    Membership intervals are half-open [valid_from, valid_to). Knowledge must
    exist by the supplied as-of time independently of economic validity.
    """
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    a = _dt(asof)
    if a is None:
        raise ValueError("asof must be timezone-aware")

    reasons: list[str] = []
    owner = str(snapshot.get("owner") or "").strip()
    revision = str(snapshot.get("revision") or "").strip()
    if not owner:
        reasons.append("missing_owner")
    if not revision:
        reasons.append("missing_revision")
    if snapshot.get("complete") is not True:
        reasons.append("incomplete_snapshot")
    if snapshot.get("truncated") is True:
        reasons.append("truncated_snapshot")

    effective = _dt(snapshot.get("effective_at"))
    known = _dt(snapshot.get("known_at"))
    fresh = _dt(snapshot.get("fresh_until"))
    if effective is None:
        reasons.append("invalid_effective_at")
    elif effective > a:
        reasons.append("future_snapshot_effective")
    if known is None:
        reasons.append("invalid_known_at")
    elif known > a:
        reasons.append("future_snapshot_knowledge")
    if fresh is None:
        reasons.append("invalid_fresh_until")
    elif fresh < a:
        reasons.append("stale_snapshot")

    rows = snapshot.get("securities")
    if not isinstance(rows, (list, tuple)):
        reasons.append("invalid_securities")
        rows = []
    if reasons:
        return _hold(snapshot, a, reasons)

    qualified: list[QualifiedSecurity] = []
    excluded: list[tuple[str, str]] = []
    seen_ids: set[str] = set()
    malformed = False
    for raw in rows:
        if not isinstance(raw, Mapping):
            malformed = True
            continue
        sid = str(raw.get("security_id") or "").strip()
        ticker = str(raw.get("ticker") or "").strip()
        if not sid or not ticker or sid in seen_ids:
            malformed = True
            continue
        seen_ids.add(sid)
        vf = _dt(raw.get("valid_from"))
        vt = _dt(raw.get("valid_to")) if raw.get("valid_to") is not None else None
        ka = _dt(raw.get("known_at"))
        if (
            vf is None
            or ka is None
            or (raw.get("valid_to") is not None and vt is None)
        ):
            malformed = True
            continue
        if not (vf <= a and (vt is None or a < vt)):
            excluded.append((sid, "not_effective_at_asof"))
            continue
        if ka > a:
            excluded.append((sid, "not_known_at_asof"))
            continue
        raw_aliases = raw.get("aliases")
        if not isinstance(raw_aliases, (list, tuple)):
            malformed = True
            continue
        aliases: list[str] = []
        alias_seen: set[str] = set()
        for alias in raw_aliases:
            if not isinstance(alias, str) or not alias.strip():
                malformed = True
                continue
            token = alias.strip()
            if token not in alias_seen:
                alias_seen.add(token)
                aliases.append(token)
        if ticker not in alias_seen:
            aliases.insert(0, ticker)
        qualified.append(
            QualifiedSecurity(sid, ticker, tuple(aliases), vf, vt, ka)
        )

    if malformed:
        reasons.append("malformed_security_row")

    alias_map: dict[str, list[str]] = {}
    for q in qualified:
        for alias in q.aliases:
            alias_map.setdefault(alias, []).append(q.security_id)
    ambiguous = tuple(
        sorted(k for k, v in alias_map.items() if len(set(v)) > 1)
    )
    if ambiguous and "ambiguous_alias" not in reasons:
        reasons.append("ambiguous_alias")
    if not qualified:
        reasons.append("empty_universe")

    bindings = tuple(
        AliasBinding(alias, ids[0])
        for alias, ids in alias_map.items()
        if len(set(ids)) == 1
    )
    status = "held" if reasons else "qualified"
    return UniverseQualification(
        status=status,
        owner=owner,
        revision=revision,
        asof=a,
        count=len(qualified),
        securities=tuple(qualified),
        alias_bindings=bindings,
        excluded=tuple(excluded),
        reason_codes=tuple(dict.fromkeys(reasons)),
        ambiguous_aliases=ambiguous,
    )
