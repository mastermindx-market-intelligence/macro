"""Definition-linkbase axis member-group reader (frozen spec A.3).

The definition linkbase of an admitted filing package declares, per extended
link role, which members sit directly under each axis's domain. ``dimension-
domain`` arcs bind an axis to its domain and ``domain-member`` arcs build the
member tree under that domain; a GROUP is the tuple of a domain's direct
member children within one role (grandchildren are presentation detail, never
group members). The same axis may be partitioned differently in different
roles (for example a product/service axis split five ways in the revenue note
and two ways on the face of the income statement); every distinct partition is
returned so the A.5 grouped sum identity can evaluate each one.

Laws mirror the rest of the framework: bounded parsing, deterministic output,
no ticker/CIK/accession/issuer literals here. The linkbase bytes always arrive
from the admitted package's member listing (A33), never from a name guessed
from issuer identity.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Mapping

from ..raw_ledger import canonical_json
from ..statement_graph import concept_from_href

_LINKBASE_NS = "http://www.xbrl.org/2003/linkbase"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_DIMENSION_DOMAIN_ARCROLE = "http://xbrl.org/int/dim/arcrole/dimension-domain"
_DOMAIN_MEMBER_ARCROLE = "http://xbrl.org/int/dim/arcrole/domain-member"
_MAX_LINKBASE_BYTES = 8 * 1024 * 1024
_MAX_ARCS = 20_000
_MAX_LOCS = 20_000


def _parse_linkbase(xml_bytes: bytes) -> ET.Element:
    if not xml_bytes or len(xml_bytes) > _MAX_LINKBASE_BYTES:
        raise ValueError("definition linkbase is empty or exceeds the size bound")
    if b"\x00" in xml_bytes:
        raise ValueError("definition linkbase contains NUL")
    upper = xml_bytes.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("definition linkbase declares a DTD or entity")
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("definition linkbase is not well-formed XML") from exc


def parse_axis_member_groups(
    xml_bytes: bytes | None,
) -> dict[str, tuple[tuple[str, ...], ...]]:
    """Return the distinct member groups per axis qname (frozen spec A.3).

    ``None`` or empty bytes (a package without a ``_def.xml`` member) yield an
    empty mapping. Groups are tuples of top-level member qnames in canonical
    sorted order; the per-axis group list keeps only distinct groups across
    roles, ordered by the canonical JSON of each tuple.
    """
    if not xml_bytes:
        return {}
    root = _parse_linkbase(xml_bytes)
    groups_by_axis: dict[str, set[tuple[str, ...]]] = {}
    for link in root.iter(f"{{{_LINKBASE_NS}}}definitionLink"):
        locs: dict[str, str] = {}
        arcs: list[tuple[str, str, str]] = []
        for element in link:
            tag = element.tag
            if tag == f"{{{_LINKBASE_NS}}}loc":
                label = element.get(f"{{{_XLINK_NS}}}label")
                href = element.get(f"{{{_XLINK_NS}}}href")
                if label and href and len(locs) < _MAX_LOCS:
                    locs[label] = concept_from_href(href)
            elif tag == f"{{{_LINKBASE_NS}}}definitionArc":
                if len(arcs) >= _MAX_ARCS:
                    raise ValueError("definition linkbase arc limit exceeded")
                arcs.append(
                    (
                        element.get(f"{{{_XLINK_NS}}}arcrole") or "",
                        element.get(f"{{{_XLINK_NS}}}from") or "",
                        element.get(f"{{{_XLINK_NS}}}to") or "",
                    )
                )
        domains: dict[str, str] = {}
        children: dict[str, set[str]] = {}
        for arcrole, source, target in arcs:
            if arcrole == _DIMENSION_DOMAIN_ARCROLE:
                axis = locs.get(source)
                domain = locs.get(target)
                if axis and domain:
                    domains[target] = axis  # domain label -> axis qname
                    children.setdefault(target, set())
            elif arcrole == _DOMAIN_MEMBER_ARCROLE:
                children.setdefault(source, set()).add(target)
        for domain_label, axis in domains.items():
            members = tuple(
                sorted(
                    {
                        locs[target]
                        for target in children.get(domain_label, ())
                        if locs.get(target)
                    }
                )
            )
            # An empty direct-member set is not a partition; drop it so the
            # A.4 "no group" fallback governs that role's contribution.
            if members:
                groups_by_axis.setdefault(axis, set()).add(members)
    return {
        axis: tuple(
            sorted(distinct, key=lambda group: canonical_json(list(group)))
        )
        for axis, distinct in groups_by_axis.items()
    }


def members_in_any_group(
    groups: Mapping[str, tuple[tuple[str, ...], ...]], axis: str
) -> tuple[str, ...]:
    """Union of every member the axis's groups list, in canonical order."""
    return tuple(sorted({member for group in groups.get(axis, ()) for member in group}))


__all__ = ["members_in_any_group", "parse_axis_member_groups"]
