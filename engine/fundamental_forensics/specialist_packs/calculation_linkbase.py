"""Calculation-linkbase parent/children reader (frozen spec A.2).

The calculation linkbase of an admitted filing package declares, per extended
link role, which child concepts sum into a parent concept and with what arc
weight. ``parse_parent_children`` selects the role that actually declares a
parent's reconciliation children — the role with the most children whose
qname starts with ``child_prefix``, ties broken by the lexically smallest
role URI — and returns that role's ``(child_qname, weight)`` arcs in the
parser's document order. The chosen role's FULL child tuple is returned, not
only the prefix-matching subset: an issuer may alias an extension concept
into the reconciliation through its own calculation arc, and that arc is the
issuer's own declaration that the line belongs to the total.

Recorded reading (A.2): an extension child carrying a fact is a VALUED row.
The issuer's calculation arc aliases it as a component of the reconciliation,
so the line is nameable and evaluable without a frozen us-gaap alias; the
row's ``taxonomy`` reports the extension prefix the arc itself carries.

Laws mirror the rest of the framework: bounded parsing through
``statement_graph.parse_calculations`` (never a second XML walker),
deterministic output, no ticker/CIK/accession/issuer literals here. The
linkbase bytes always arrive from the admitted package's member listing
(A33), never from a name guessed from issuer identity.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ..statement_graph import parse_calculations


def calculation_linkbase_bytes(package: Any) -> bytes | None:
    """The package's stored ``_cal.xml`` member bytes, or ``None``.

    Located through the package's member listing only (A33): the name is
    matched by its ``_cal.xml`` suffix — the same lookup style as the
    definition-linkbase reader's ``_def.xml`` — never by issuer identity.
    """
    names = sorted(
        str(item.get("name") or "")
        for item in package.manifest.get("members") or []
        if isinstance(item, dict)
        and item.get("state") == "stored"
        and str(item.get("name") or "").endswith("_cal.xml")
    )
    if not names:
        return None
    return package.members.get(names[0])


def parse_parent_children(
    xml_bytes: bytes | None,
    parent_concept: str,
    child_prefix: str,
) -> tuple[tuple[str, Decimal], ...]:
    """Return the chosen role's ``(child_qname, weight)`` arcs (frozen A.2).

    A role qualifies when ``parent_concept`` has children in it and at least
    one child qname starts with ``child_prefix``; the qualifying role with
    the MOST prefix-matching children wins (tie: lexically smallest role
    URI). No qualifying role — including empty or absent linkbase bytes —
    yields ``()``. Weights are returned as ``Decimal`` in the parser's order.
    """
    if not xml_bytes:
        return ()
    networks = parse_calculations(xml_bytes)
    qualifying: list[tuple[int, str]] = []
    for role, parents in networks.items():
        children = parents.get(parent_concept) or ()
        matching = sum(
            1 for qname, _weight in children if qname.startswith(child_prefix)
        )
        if matching:
            qualifying.append((matching, role))
    if not qualifying:
        return ()
    best = max(count for count, _role in qualifying)
    chosen = min(role for count, role in qualifying if count == best)
    arcs: list[tuple[str, Decimal]] = []
    for qname, weight in networks[chosen][parent_concept]:
        try:
            arcs.append((qname, Decimal(weight)))
        except InvalidOperation as exc:
            raise ValueError(
                f"calculation arc weight is not a decimal: {weight!r}"
            ) from exc
    return tuple(arcs)


__all__ = ["calculation_linkbase_bytes", "parse_parent_children"]
