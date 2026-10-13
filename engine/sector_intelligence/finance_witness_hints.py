"""Closed research-hint roster for the Finance company table.

The only state this module returns is ``RESEARCH_HINT_UNVALIDATED``.
``company_node_id`` and ``security_ref`` stay null. It does not read
``research/finance``, and it does not mint a theme-graph id, a price, or a
filing measurement.

BNY stays symbol ``BNY`` with record id ``fin-research-bk-2025``. ``BK`` is
not an alias. The other ten record ids are not transcribed in the finance
design and are ``None`` here; ``None`` is not a preflight record id.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping


_HINT_STATE = "RESEARCH_HINT_UNVALIDATED"

# Symbol order is the finance design's roster. Only BNY's record_id was
# transcribed (preflight symbol BNY, record_id fin-research-bk-2025).
_RECORD_IDS: Mapping[str, str | None] = MappingProxyType(
    {
        "V": None,
        "MA": None,
        "FI": None,
        "FIS": None,
        "CME": None,
        "ICE": None,
        "NDAQ": None,
        "BNY": "fin-research-bk-2025",
        "STT": None,
        "SPGI": None,
        "MCO": None,
    }
)


class FinanceWitnessHintRefusal(ValueError):
    """Typed refusal. ``str(exc)`` is the code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


def hint_binding(symbol: str, *, state: str = _HINT_STATE) -> dict[str, Any]:
    """Return the research-hint binding for one roster symbol.

    A caller asking for any state other than ``RESEARCH_HINT_UNVALIDATED``
    is refused. ``IDENTITY_VALIDATED`` is never returned.
    """
    if state != _HINT_STATE:
        raise FinanceWitnessHintRefusal("validated_upgrade_refused")
    if symbol not in _RECORD_IDS:
        raise FinanceWitnessHintRefusal("unknown_symbol")
    return {
        "state": _HINT_STATE,
        "record_id": _RECORD_IDS[symbol],
        "company_node_id": None,
        "security_ref": None,
        "listing_note": None,
    }
