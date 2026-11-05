"""Settled-session generation guard for rotation artifacts (packet SIC-D-B02).

Two rotation artifacts may be combined only when they carry the SAME settled
daily session.  Wall-clock age is deliberately never a freshness gate: a
Friday artifact read on Monday is aligned, a holiday gap is aligned (both
sides carry the last settled session), and a stale artifact at the wrong
session is rejected with a typed reason instead of being silently accepted or
silently dropped.  Mirrors the as_of discipline of
``engine/leadership_rotation_context.py`` (rotation_events.v1).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from collections.abc import Mapping

# Typed reasons, in evaluation order of session_alignment().
REASONS = (
    "aligned",
    "as_of_mismatch",          # artifact session is OLDER than the consumer's
    "artifact_newer_than_consumer",  # artifact session is NEWER (un-settled)
    "future_session",          # artifact session is after the known calendar day
    "missing_session",         # a side carried no session value at all
    "invalid_session",         # a side carried a value that is not a session date
    "missing_input",           # status-level: an input was absent
    "invalid_payload",         # status-level: an input could not be interpreted
)

_CLOCK = "settled_daily_session"


def cycle_spine_identity(payload) -> dict | None:
    """Fingerprint the actual sector spine consumed by a projection.

    This is content identity, not a point-in-time vintage or an approval. The
    existing Central producer and Cycles publisher call the same pure function
    on their own inputs. Unrelated basket-family changes do not invalidate the
    sector cohort; sector values, history, methodology and parity changes do.
    """
    if not isinstance(payload, Mapping):
        return None
    meta, sectors = payload.get("meta"), payload.get("sectors")
    if not isinstance(meta, Mapping) or not isinstance(sectors, list) or not sectors:
        return None
    session = meta.get("asOf")
    parsed_session = parse_session(session)
    if not isinstance(session, str) or not parsed_session or session != parsed_session.isoformat():
        return None
    ids = [row.get("id") if isinstance(row, Mapping) else None for row in sectors]
    if any(not isinstance(eid, str) or not eid for eid in ids) or len(set(ids)) != len(ids):
        return None
    tickers = [row.get("ticker") for row in sectors if row.get("ticker") is not None]
    if any(not isinstance(ticker, str) or not ticker for ticker in tickers) or len(set(tickers)) != len(tickers):
        return None
    region = meta.get("region") or "us"
    scope = "us_sectors_11" if region == "us" else str(region) + ":sectors"
    spine = {
        "schema": "sector_cycles.sector_spine.v1", "scope": scope,
        "meta": {k: v for k, v in meta.items() if k not in {"n_baskets", "families", "publication"}},
        "phases": payload.get("phases"),
        "sectors": sorted(sectors, key=lambda row: row["id"]),
    }
    try:
        raw = json.dumps(spine, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return {"schema": spine["schema"], "scope": scope, "sha256": hashlib.sha256(raw).hexdigest()}


def parse_session(value) -> "_dt.date | None":
    """Parse a settled daily session from ``value``.

    Accepts ``YYYY-MM-DD`` strings and ISO datetimes (the DATE part is taken —
    never the wall clock), plus ``datetime.date``/``datetime.datetime``
    objects.  Returns None for anything else.
    """
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return _dt.date.fromisoformat(text[:10]) if len(text) >= 10 else None
    except ValueError:
        # Full ISO datetimes that don't prefix-match a date (e.g. with a
        # compact form) — try the full string as a datetime, date part only.
        try:
            return _dt.datetime.fromisoformat(text).date()
        except ValueError:
            return None


def _fmt(d: "_dt.date | None") -> "str | None":
    return d.isoformat() if d is not None else None


def session_alignment(artifact_session, consumer_session, *, today=None) -> dict:
    """Compare the artifact's settled session against the consumer's.

    Returns ``{"status", "reason", "artifact_session", "consumer_session",
    "clock"}`` with ``status`` one of aligned | incompatible_generation |
    missing_input | invalid_payload and ``reason`` one of REASONS.  No
    wall-clock age rule is applied anywhere — weekends and holidays need no
    special case because both sides carry the same settled session.
    """
    out = {"clock": _CLOCK}

    # 1) Artifact side first: absent, then unparseable.
    if artifact_session is None or (isinstance(artifact_session, str) and not artifact_session.strip()):
        return {**out, "status": "missing_input", "reason": "missing_session",
                "artifact_session": None, "consumer_session": _fmt(parse_session(consumer_session))}
    art = parse_session(artifact_session)
    if art is None:
        return {**out, "status": "invalid_payload", "reason": "invalid_session",
                "artifact_session": None, "consumer_session": _fmt(parse_session(consumer_session))}

    # 2) Calendar sanity: an artifact claiming a session after the known day
    #    is from the future — never combinable regardless of the consumer.
    if today is not None:
        t = today if isinstance(today, _dt.date) else parse_session(today)
        if isinstance(t, _dt.datetime):
            # RB02 #1: datetime is a date subclass; `date > datetime` raises TypeError.
            t = t.date()
        if t is not None and art > t:
            return {**out, "status": "incompatible_generation", "reason": "future_session",
                    "artifact_session": _fmt(art), "consumer_session": _fmt(parse_session(consumer_session))}

    # 3) Consumer side: absent, then unparseable.
    if consumer_session is None or (isinstance(consumer_session, str) and not consumer_session.strip()):
        return {**out, "status": "missing_input", "reason": "missing_session",
                "artifact_session": _fmt(art), "consumer_session": None}
    con = parse_session(consumer_session)
    if con is None:
        return {**out, "status": "invalid_payload", "reason": "invalid_session",
                "artifact_session": _fmt(art), "consumer_session": None}

    # 4) Same settled session or not — typed either way.
    if art < con:
        status, reason = "incompatible_generation", "as_of_mismatch"
    elif art > con:
        status, reason = "incompatible_generation", "artifact_newer_than_consumer"
    else:
        status, reason = "aligned", "aligned"
    return {**out, "status": status, "reason": reason,
            "artifact_session": _fmt(art), "consumer_session": _fmt(con)}
