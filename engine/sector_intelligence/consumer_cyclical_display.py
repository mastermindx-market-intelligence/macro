"""Display packet for the PLNT reader.

A later page can mount this packet. It copies the explanation lead,
``advertising_net_change`` and the document's ``availability`` verdict from
``project_economic_change`` and records whether the shared curation contract
is importable. An ``unavailable`` document stays ``unavailable`` on the
packet, and a withheld advertising row is reported as withheld, not absent.
The packet is the synthetic fixture's reading: ``filing_claim`` is false,
``provenance`` is ``synthetic_fixture``, and a fact with ``native_admitted``
true raises a Cyclical-owned refusal instead of returning a packet. This
module does not present that lead as a filing, and the projection does not
import it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from engine.sector_intelligence.consumer_cyclical_projection import (
    RESULT_KEY_ADVERTISING_NET_CHANGE,
    project_economic_change,
)
from engine.sector_intelligence.consumer_cyclical_shared_contract import (
    ConsumerCyclicalResearchRefusal,
    shared_contract,
)


class ConsumerCyclicalDisplayRefusal(Exception):
    """A typed, Cyclical-owned refusal. ``code`` is ``native_admitted``."""

    CODES: tuple[str, ...] = ("native_admitted",)

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in self.CODES:
            raise ValueError(f"unknown refusal code {code!r}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _facts(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    return [fact for fact in value if isinstance(fact, Mapping)]


def _refuse_if_native_admitted(facts: Any) -> None:
    """Raise before a packet exists when any fact is native-admitted."""
    admitted = [fact for fact in _facts(facts) if fact.get("native_admitted") is True]
    if not admitted:
        return
    keys = ", ".join(str(fact.get("key") or "") for fact in admitted)
    raise ConsumerCyclicalDisplayRefusal(
        "native_admitted",
        "a display packet is not returned when native_admitted is true "
        f"({keys})",
    )


def _shared_contract_status() -> str:
    """``present`` when the shared probe returns a callable, else ``unavailable``.

    The returned callable is not invoked. Calling it would ask the shared
    owner to certify this synthetic packet, which this builder does not do.
    """
    try:
        probe = shared_contract()
    except ConsumerCyclicalResearchRefusal as exc:
        if exc.code != "shared_contract_unavailable":
            raise
        return "unavailable"
    if callable(probe):
        return "present"
    return "unavailable"


_AVAILABILITY = ("ready", "unavailable")


def _availability(document: Mapping[str, Any]) -> str:
    """The projection's own verdict; anything else reads ``unavailable``."""
    value = document.get("availability")
    return value if value in _AVAILABILITY else "unavailable"


def _advertising_net_change(
    document: Mapping[str, Any],
) -> tuple[str | None, str, str | None]:
    """``(value_text, status, withheld_reason)`` for the advertising row.

    ``status`` is ``ready`` when the row carries a value, ``withheld`` when
    the row is present without one, and ``absent`` when the projection
    emitted no row because its inputs were missing.
    """
    for row in _facts(document.get("results")):
        if row.get("key") != RESULT_KEY_ADVERTISING_NET_CHANGE:
            continue
        value = row.get("value_text")
        if isinstance(value, str):
            return value, "ready", None
        reason = row.get("withheld_reason")
        return None, "withheld", reason if isinstance(reason, str) else None
    return None, "absent", None


def _lead(document: Mapping[str, Any]) -> str:
    explanation = document.get("explanation")
    if not isinstance(explanation, Mapping):
        return ""
    lead = explanation.get("lead")
    return lead if isinstance(lead, str) else ""


def display_packet(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return the synthetic PLNT display packet for ``case``.

    Raises
    ------
    ConsumerCyclicalDisplayRefusal
        When any fact on the case, or any fact the projection copied, has
        ``native_admitted`` true. No packet is returned.
    """
    _refuse_if_native_admitted(case.get("facts"))
    document = project_economic_change(case)
    _refuse_if_native_admitted(document.get("facts"))
    status = _shared_contract_status()
    value, value_status, withheld_reason = _advertising_net_change(document)
    return {
        "availability": _availability(document),
        "lead": _lead(document),
        "advertising_net_change": value,
        "advertising_net_change_status": value_status,
        "advertising_net_change_withheld_reason": withheld_reason,
        "filing_claim": False,
        "provenance": "synthetic_fixture",
        "shared_contract_status": status,
        "facts": [dict(fact) for fact in _facts(document.get("facts"))],
    }


__all__ = [
    "ConsumerCyclicalDisplayRefusal",
    "display_packet",
]
