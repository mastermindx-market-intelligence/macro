"""Closed research-hint roster for the Finance company table.

The only state this module returns is ``RESEARCH_HINT_UNVALIDATED``.
``company_node_id`` and ``security_ref`` stay null. It does not read
``research/finance``, and it does not mint a theme-graph id, a price, or a
filing measurement.

Record ids are plain strings transcribed from the R12 preflight witness
triples. BNY stays symbol ``BNY`` with record id ``fin-research-bk-2025``.
``BK`` is not an alias. This module does not read the preflight file.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping


_HINT_STATE = "RESEARCH_HINT_UNVALIDATED"

# Symbol order and record ids are the R12 preflight witness roster, stored
# as plain strings. This module does not open the preflight file.
_RECORD_IDS: Mapping[str, str] = MappingProxyType(
    {
        "V": "fin-research-v-2025",
        "MA": "fin-research-ma-2025",
        "FI": "fin-research-fi-2025",
        "FIS": "fin-research-fis-2025",
        "CME": "fin-research-cme-2025",
        "ICE": "fin-research-ice-2025",
        "NDAQ": "fin-research-ndaq-2025",
        "BNY": "fin-research-bk-2025",
        "STT": "fin-research-stt-2025",
        "SPGI": "fin-research-spgi-2025",
        "MCO": "fin-research-mco-2025",
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
