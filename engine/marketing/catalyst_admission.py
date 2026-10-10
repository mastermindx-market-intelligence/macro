"""Read-only Catalyst source-owner admission port for the existing SEC producer.

Not a source-rights authority, event store, scheduler, publisher or self-granting
EDGAR client. Session 01 packet construction and GMI's *existing* rights registry
remain authoritative. Default is unconfigured / no results.
Only an attended operator/approved source owner may inject callbacks into this
private process-local port. No HTTP route can configure or select a source URL.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.marketing.catalyst_packets import (
    PublicSourceGrant, build_event_packet,
)

_MAX_EVENTS = 20
_LOOKBACK = timedelta(days=7)


@dataclass(frozen=True)
class AdmittedEdgarSource:
    """Read methods of incumbent issuer, filings and rights owners.

    The injected provider does NOT gain rights by being registered; the
    canonical sec_edgar registry must separately allow a public emission and
    each individual source must receive a live, source-specific owner grant.
    """

    issuer_universe: Callable[[datetime], Mapping[str, Mapping[str, object]]]
    recent_events: Callable[[datetime, datetime, int], Sequence[Mapping[str, object]]]
    public_grant: Callable[[str, datetime], PublicSourceGrant | None]


_current: AdmittedEdgarSource | None = None


def configure(source: AdmittedEdgarSource | None) -> None:
    """Private, operator-admitted process wiring; NOT a capability mint."""
    global _current
    if source is not None and (
        not isinstance(source, AdmittedEdgarSource)
        or any(not callable(getattr(source, field, None))
               for field in ("issuer_universe", "recent_events", "public_grant"))
    ):
        raise ValueError("invalid Catalyst source adapter")
    _current = source


def read_qualified_event_context(
    now_utc: datetime,
) -> tuple[Sequence[Mapping], Mapping[str, Mapping]]:
    """Fail closed on absent rights, source, issuer, timezone or owner errors.

    This is the source-owned data *read* only. It never contacts EDGAR itself,
    accepts a browser filename/URL, publishes a file, or opens a database.
    """
    owner = _current
    if owner is None:
        return (), {}
    if not isinstance(now_utc, datetime) or now_utc.tzinfo is None:
        return (), {}
    now = now_utc.astimezone(timezone.utc)
    try:
        # Source rights are stated in ONE canonical registry, not inferred
        # from a sec.gov host or from a model-generated description.
        from engine.theme_graph.rights import assert_public_emission_allowed
        assert_public_emission_allowed("sec_edgar")

        issuers = owner.issuer_universe(now)
        if not isinstance(issuers, Mapping) or not 1 <= len(issuers) <= 10_000:
            return (), {}
        # Do not synthesize or upgrade an issuer identity on this seam.
        # The incumbent issuer registry can also name known unsupported
        # symbols. They must remain NOT_COVERED, not make every otherwise
        # qualified direct issuer temporarily unavailable.
        for symbol, row in issuers.items():
            if (not isinstance(symbol, str) or not isinstance(row, Mapping)
                    or type(row.get("supported")) is not bool):
                return (), {}
            if (row["supported"] is True and
                    (not isinstance(row.get("issuer_id"), str)
                     or not row["issuer_id"].strip())):
                return (), {}

        events = owner.recent_events(now - _LOOKBACK, now, _MAX_EVENTS)
        if not isinstance(events, (list, tuple)) or len(events) > _MAX_EVENTS:
            return (), {}
        packets = []
        for event in events:
            # All source events must originate from the incumbent SEC 8-K
            # earnings producer. A stray media/paid feed is not auto-admitted.
            if not isinstance(event, Mapping) or event.get("source") != "edgar_8k_202":
                return (), {}
            packet = build_event_packet(
                event, issuers=issuers, rights_resolver=owner.public_grant,
                as_of=now, max_age=_LOOKBACK,
            )
            packets.append(packet)
        return tuple(packets), issuers
    except Exception:
        # Never expose owner exception text, private feed paths or licensing
        # internals on the anonymous HTTP boundary. A broken source is 503.
        return (), {}
