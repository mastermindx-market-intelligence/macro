"""Extract vehicle-delivery guidance from a bound EX-99.1 release body.

Scope
-----
``extract_vehicle_guidance`` is a PURE extractor over a
:class:`~engine.earnings_release.binding.BoundRelease`: it reads issuer-EXPECTED
vehicle-delivery ranges out of the release body and returns ``guidance_item.v1``
payloads.  It performs no activation and is wired to nothing: no profile is
activated, no event is registered, no guidance store or event-key table is
created or updated, and no caller in ``event_workspace_build`` invokes it yet —
integration/activation is a separate, later unit.  Each call is stateless and
side-effect free (no network, no file writes, no clock reads).

Status semantics: ``introduced`` vs ``revised`` describes the ISSUER'S
EXPECTATION as published in THIS document — an expectation asserted without
revision language is ``introduced``; one that explicitly revises a previous
outlook is ``revised``.  Neither value asserts anything about which versions
this estate previously served; the same-quarter revision chain is
owner-governed elsewhere.

Evidence contract — a candidate requires ALL of the following or is dropped:

* a vehicle-delivery range asserted as a CURRENT expectation (actual delivered
  counts and prior-outlook comparison ranges are excluded);
* valid non-negative integral bounds — US grouping ``100,000`` or plain digits
  (``1,00,000`` and other malformed groupings, fractional tails, and reversed
  bounds are rejected); an EQUAL low == high IS a valid single-point
  expectation;
* an explicit quarter AND year inside the assertion, its expectation
  introducer, or an unambiguous adjacent outlook heading — NEVER derived from
  the filing's ``report_date``;
* a verified byte-replay span over the ORIGINAL raw body bytes: the literal
  range phrase must occur exactly once in the tag-masked raw source, the body
  SHA-256 must validate, and the minted receipt must replay — any failure
  refuses the candidate (fail closed).

Return ``[]`` for missing, ambiguous, conflicting, malformed, actual-only, or
non-replayable evidence.
"""
from __future__ import annotations

import re
from typing import Any, Iterator

from ..earnings_release.binding import BoundRelease
from ..earnings_release.receipts import (
    ReceiptError,
    mask_markup,
    receipt_for_char_span,
)
from ..fundamental_forensics.disclosure_diff import BlockKind
from .documents import DocumentError, text_span

# A delivery range: "between 100,000 and 103,000 vehicles" or "deliveries of
# 100,000 to 103,000 vehicles".  Grouping is validated BY THE PATTERN:
# ``\d{1,3}(?:,\d{3})+|\d+`` cannot match "1,00,000" or "10,0,000", and a
# fractional tail ("76,000.5") breaks the required following whitespace, so a
# malformed phrase fails to match at all instead of half-matching.
_INT = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_RANGE_RE = re.compile(
    rf"\bbetween\s+({_INT})\s+and\s+({_INT})\s+vehicles?\b"
    rf"|\bdeliveries\s+(?:of\s+)?({_INT})\s+to\s+({_INT})\s+vehicles?\b",
    re.IGNORECASE,
)

# Explicit quarter AND year, named or numeric: "first quarter of 2024",
# "first-quarter of 2024", "Q1 2024", "Q1 of 2024".  A quarter without a year
# in the same phrase is not a usable horizon.
_PERIOD_RE = re.compile(
    r"\b(?:q([1-4])|(first|second|third|fourth)[\s-]quarter)\s+(?:of\s+|in\s+)?(20\d\d)\b",
    re.IGNORECASE,
)
_QNAME_TO_NUM = {"first": 1, "second": 2, "third": 3, "fourth": 4}

# A period phrase preceded (within a short window) by comparison language
# names the BASELINE the expectation is measured against ("an increase of …
# from the first quarter of 2023"), not the expectation's own horizon.
_COMPARISON_PRELUDE_RE = re.compile(
    r"\b(?:from|versus|vs\.?|compared(?:\s+with|\s+to)?|than|over|"
    r"previous(?:ly)?|prior|earlier|originally)\b[^.]{0,28}$",
    re.IGNORECASE,
)

# Expectation language gates a range as guidance rather than reported actuals.
_EXPECTATION_RE = re.compile(
    r"\b(?:expect\w*|outlook|forecast\w*|anticipat\w*|guidance|project\w*)\b",
    re.IGNORECASE,
)

# Explicit revision language is REQUIRED for status="revised".
_REVISION_RE = re.compile(
    r"\b(?:revis\w+|now\s+expect\w*|updat\w+\s+(?:its\s+)?(?:\w+\s+){0,3}outlook|previously)\b",
    re.IGNORECASE,
)

# A range whose lead-in names the prior outlook is the PREVIOUS range being
# compared against, never the current expectation.
_PRIOR_RANGE_PRELUDE_RE = re.compile(
    r"\b(?:revised?\s+from|previous(?:ly)?|prior|earlier|original)\b",
    re.IGNORECASE,
)

# An adjacent heading may donate the horizon only when it is an outlook
# heading; a results/financial heading must not.
_OUTLOOK_HEADING_RE = re.compile(r"\b(?:outlook|guidance|forecast)\b", re.IGNORECASE)

# Whitespace or unresolved HTML entities between tokens of the raw source.
_RAW_SEP = r"(?:\s|&#\d+;|&[a-zA-Z][a-zA-Z0-9]*;)+"

_MAX_GROUP_LOOKBACK = 2
_HEADING_WINDOW = 3
_PERIOD_PRELUDE_WINDOW = 32
_PRIOR_WINDOW = 80


def _parse_int(text: str) -> int:
    """Parse a grouping-validated integer string (see ``_INT``)."""
    return int(text.replace(",", ""))


def _explicit_periods(text: str) -> Iterator[tuple[int, int]]:
    """Yield non-comparison explicit ``(year, quarter)`` phrases in *text*."""
    for m in _PERIOD_RE.finditer(text):
        prelude = text[max(0, m.start() - _PERIOD_PRELUDE_WINDOW):m.start()]
        if _COMPARISON_PRELUDE_RE.search(prelude):
            continue
        if m.group(1):
            quarter = int(m.group(1))
        else:
            name = re.split(r"[\s-]", m.group(2).lower())[0]
            quarter = _QNAME_TO_NUM.get(name)
            if quarter is None:
                continue
        yield int(m.group(3)), quarter


def _current_ranges(text: str) -> list[tuple[int, int]]:
    """Return the CURRENT expectation ranges in *text* (prior comparisons excluded)."""
    ranges: list[tuple[int, int]] = []
    for m in _RANGE_RE.finditer(text):
        if m.group(1) is not None:
            low_str, high_str = m.group(1), m.group(2)
        else:
            low_str, high_str = m.group(3), m.group(4)
        prelude = text[max(0, m.start() - _PRIOR_WINDOW):m.start()]
        if _PRIOR_RANGE_PRELUDE_RE.search(prelude):
            continue
        ranges.append((_parse_int(low_str), _parse_int(high_str)))
    return ranges


def _group_indices(blocks: tuple, assert_index: int) -> list[int]:
    """The assertion block plus contiguous expectation-introducing predecessors.

    An issuer commonly splits the assertion across blocks: "For the first
    quarter of 2024, the Company expects:" followed by a bullet carrying the
    range.  A predecessor joins the group only when it introduces the
    expectation (ends with ":" or carries expectation language), carries no
    range of its own, and sits in the same section.
    """
    indices = [assert_index]
    lookback = 0
    j = assert_index - 1
    while j >= 0 and lookback < _MAX_GROUP_LOOKBACK:
        block = blocks[j]
        if block.kind is not BlockKind.PARAGRAPH or block.section_id != blocks[assert_index].section_id:
            break
        if _current_ranges(block.text):
            break
        if block.text.rstrip().endswith(":") or _EXPECTATION_RE.search(block.text):
            indices.insert(0, j)
            lookback += 1
        else:
            break
        j -= 1
    return indices


def _adjacent_heading_text(blocks: tuple, first_index: int) -> str | None:
    """Nearest preceding HEADING block within a small window, if any."""
    for j in range(first_index - 1, max(0, first_index - _HEADING_WINDOW) - 1, -1):
        if blocks[j].kind is BlockKind.HEADING:
            return blocks[j].text
    return None


def _resolve_period(group_texts: list[str], heading_text: str | None) -> tuple[int, int] | None:
    """Resolve one explicit horizon, or None (never from ``report_date``).

    Exactly one distinct non-comparison period must appear in the assertion
    group; otherwise an unambiguous adjacent OUTLOOK heading may supply it.
    """
    periods: set[tuple[int, int]] = set()
    for text in group_texts:
        periods.update(_explicit_periods(text))
    if len(periods) == 1:
        return next(iter(periods))
    if periods:
        return None
    if heading_text is None or not _OUTLOOK_HEADING_RE.search(heading_text):
        return None
    heading_periods = set(_explicit_periods(heading_text))
    if len(heading_periods) == 1:
        return next(iter(heading_periods))
    return None


def _unique_raw_span(
    masked: str, source: str, low: int, high: int
) -> tuple[int, int, str] | None:
    """Locate the range phrase's UNIQUE occurrence in the raw source.

    The search runs over the tag-masked source (offsets preserved) and
    tolerates intervening tags/entities via ``_RAW_SEP``; the returned literal
    is the ORIGINAL raw byte slice, tags included, so the receipt addresses
    and replays actual original bytes.  Zero or multiple occurrences refuse.
    """
    low_raw, high_raw = f"{low:,}", f"{high:,}"
    pattern = re.compile(
        rf"\bbetween{_RAW_SEP}{re.escape(low_raw)}{_RAW_SEP}and{_RAW_SEP}"
        rf"{re.escape(high_raw)}{_RAW_SEP}vehicles?\b"
        rf"|\bdeliveries{_RAW_SEP}(?:of{_RAW_SEP})?{re.escape(low_raw)}{_RAW_SEP}"
        rf"to{_RAW_SEP}{re.escape(high_raw)}{_RAW_SEP}vehicles?\b",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(masked))
    if len(matches) != 1:
        return None
    m = matches[0]
    return m.start(), m.end(), source[m.start():m.end()]


def _extract_vehicle_guidance(
    *,
    bound: BoundRelease,
    document_id: str,
    event_id: str,
) -> list[dict[str, Any]]:
    """Extract vehicle-delivery guidance entries from a bound release document.

    Paragraph and one-column-table blocks (the two shapes real EX-99.1 bodies
    use for outlook bullets) are matched semantically for guidance assertions;
    every emitted item carries a byte-replay ``source_span`` minted from the
    ORIGINAL raw body bytes.  Returns ``[]`` when no unique, well-formed,
    explicitly-dated expectation replays.
    """
    blocks = bound.document.blocks
    if not blocks:
        return []

    source = bound.source
    source_sha256 = bound.revision.source_sha256
    masked = mask_markup(source)

    # period -> claim; conflicting values for one period poison the document.
    claims: dict[tuple[int, int], dict[str, Any]] = {}
    conflict = False

    for index, block in enumerate(blocks):
        # Issuers lay outlook bullets out as prose paragraphs OR as one-column
        # layout tables (the real EX-99.1 shape measured on the 2024-02-26
        # release); heading blocks only ever donate an adjacent horizon.
        if block.kind not in (BlockKind.PARAGRAPH, BlockKind.TABLE):
            continue
        ranges = _current_ranges(block.text)
        if not ranges:
            continue

        group = _group_indices(blocks, index)
        group_texts = [blocks[j].text for j in group]
        heading_text = _adjacent_heading_text(blocks, group[0])

        gated = any(_EXPECTATION_RE.search(t) for t in group_texts)
        if not gated and heading_text is not None:
            gated = bool(_EXPECTATION_RE.search(heading_text))
        if not gated:
            continue

        period = _resolve_period(group_texts, heading_text)
        if period is None:
            continue

        status = (
            "revised"
            if any(_REVISION_RE.search(t) for t in group_texts)
            else "introduced"
        )
        for low, high in ranges:
            if low > high:
                continue
            prior = claims.get(period)
            if prior is None:
                claims[period] = {"low": low, "high": high, "status": status}
            elif (prior["low"], prior["high"]) != (low, high):
                conflict = True

    if conflict or not claims:
        return []

    items: list[dict[str, Any]] = []
    for (year, quarter), claim in sorted(claims.items()):
        located = _unique_raw_span(masked, source, claim["low"], claim["high"])
        if located is None:
            continue
        char_start, char_end, literal = located
        try:
            receipt = receipt_for_char_span(
                source=source,
                source_sha256=source_sha256,
                char_start=char_start,
                char_end=char_end,
            )
            span = text_span(
                document_id=document_id,
                document_version=1,
                body_sha256=source_sha256,
                segment_index=0,
                segment_text=source,
                start_byte=receipt.byte_start,
                end_byte=receipt.byte_end,
                text=literal,
                rights_profile="rp_public_primary_v1",
                display_excerpt=receipt.value_text[:200],
            )
        except (ReceiptError, DocumentError):
            # Fail closed: unreplayable or non-validating evidence is refused.
            continue
        items.append({
            "schema": "guidance_item.v1",
            "metric": "vehicle_deliveries",
            "low": claim["low"],
            "high": claim["high"],
            "unit": "vehicles",
            "horizon": f"FY{year} Q{quarter}",
            "status": claim["status"],
            "source_span": span.to_payload(),
        })
    return items


def extract_vehicle_guidance(
    *,
    bound: BoundRelease,
    document_id: str,
    event_id: str,
) -> list[dict[str, Any]]:
    """Public API: extract vehicle-delivery guidance from a bound release.

    Returns a list of ``guidance_item.v1`` dictionaries (keys: ``schema``,
    ``metric``, ``low``, ``high``, ``unit``, ``horizon``, ``status``,
    ``source_span``) suitable for insertion into an event workspace's
    ``guidance`` list.  ``event_id`` is accepted for caller continuity; the
    emitted payload keys are fixed and carry no event identity.

    Returns ``[]`` for missing, ambiguous, conflicting, malformed, actual-only,
    or non-replayable evidence.  No network, storage, clock, identity, or event
    registration side effects.
    """
    return _extract_vehicle_guidance(
        bound=bound, document_id=document_id, event_id=event_id
    )
