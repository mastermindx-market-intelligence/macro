"""Extract source-bound, issuer-expected vehicle-delivery guidance.

This pure, unactivated leaf returns the existing guidance_item.v1 shape. It
does not register events, publish data, change history, or authorize a trade.
An assertion must identify an affirmative issuer delivery expectation, integral
bounds and an explicit compatible quarter/year. Context comes only from the
native adjacent introduction or outlook heading; unread material breaks that
relationship. A prior comparison supports a revision only for the same delivery
expectation and period.

Native block/cell coordinates select the original source occurrence. Native
release receipts replay every source window, and the emitted Company
Intelligence span covers the assertion and all context used for its meaning.
No reformatted-number search, report-date inference or historical-availability
claim is made. Unsupported or ambiguous associations are refused.
"""
from __future__ import annotations

import re
from typing import Any, Iterator

from ..earnings_release.binding import BoundRelease
from ..earnings_release.receipts import ReceiptError, receipt_for_char_span
from ..fundamental_forensics.disclosure_diff import BlockKind, _compact_text, normalize_filing
from .documents import DocumentError, text_span

_INT = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_RANGE_RE = re.compile(
    rf"\bbetween\s+({_INT})\s+and\s+({_INT})\s+vehicles?\b"
    rf"|\bdeliveries\s+(?:of\s+)?({_INT})\s+to\s+({_INT})\s+vehicles?\b",
    re.IGNORECASE,
)
_QUARTER_RE = re.compile(
    r"\b(?:q([1-4])|(first|second|third|fourth)[\s-]quarter)"
    r"(?:\s+(?:of\s+|in\s+)?(20\d\d))?\b",
    re.IGNORECASE,
)
_QNAME_TO_NUM = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_COMPARISON_PRELUDE_RE = re.compile(
    r"\b(?:from|versus|vs\.?|compared(?:\s+with|\s+to)?|than|over|"
    r"previous(?:ly)?|prior|earlier|originally)\b[^.]{0,28}$",
    re.IGNORECASE,
)
_RELATIVE_PERIOD_RE = re.compile(
    r"\b(?:next|following|this|upcoming)\s+quarter\b", re.IGNORECASE
)
_INVALID_QUARTER_RE = re.compile(
    r"\b(?:q(?:0|[5-9]\d*)|(?:fifth|sixth|seventh|eighth)[\s-]quarter)\b",
    re.IGNORECASE,
)
_ISSUER_EXPECTATION_RE = re.compile(
    r"\b(?:the\s+company|we)\s+(?:now\s+)?"
    r"(?:expects?|anticipates?|forecasts?|projects?)\b",
    re.IGNORECASE,
)
_PRONOUN_EXPECTATION_RE = re.compile(
    r"\bit\s+(?:also\s+)?(?:now\s+)?"
    r"(?:expects?|anticipates?|forecasts?|projects?)\b",
    re.IGNORECASE,
)
_DELIVERY_RE = re.compile(
    r"\b(?:vehicle\s+deliveries|deliveries(?:\s+of\s+vehicles?)?)\b",
    re.IGNORECASE,
)
_REJECT_MEANING_RE = re.compile(
    r"\b(?:not|never|no|actuals?|delivered|were|was|reported|recorded|"
    r"production|revenue|sales|orders?|capacity|analysts?|competitors?|"
    r"rivals?|suppliers?|customers?|industry|market)\b",
    re.IGNORECASE,
)
_OUTLOOK_HEADING_RE = re.compile(r"\b(?:outlook|guidance|forecast)\b", re.IGNORECASE)
_PRIOR_LINK_RE = re.compile(
    r"\b(?:(?:revised?|updated?|changed?|raised?|lowered?|reduced?|increased?)\s+from"
    r"|compared\s+(?:to|with)\s+(?:the\s+|its\s+)?(?:previous|prior|earlier|original)"
    r"|from\s+(?:the\s+|its\s+)?(?:previous|prior|earlier|original)"
    r"\s+(?:vehicle\s+)?(?:delivery|deliveries|outlook|forecast|guidance))\b",
    re.IGNORECASE,
)
_DIRECT_CHANGE_RE = re.compile(
    r"\b(?:revised?|updated?|changed?|raised?|lowered?|reduced?|increased?)\s+from\b",
    re.IGNORECASE,
)
_PRIOR_FORECAST_RE = re.compile(
    r"\b(?:previous|prior|earlier|original)\b.*"
    r"\b(?:outlook|guidance|forecast|expectation|delivery|deliveries)\b",
    re.IGNORECASE,
)
_SAME_PERIOD_RE = re.compile(r"\b(?:same\s+(?:quarter|period)|that\s+quarter)\b", re.IGNORECASE)


def _parse_int(text: str) -> int:
    return int(text.replace(",", ""))


def _sentences(text: str) -> Iterator[str]:
    """Keep decimals intact; unrelated sentences cannot donate meaning."""
    start = 0
    for match in re.finditer(r"[.!?;](?=\s|$)", text):
        part = text[start:match.end()].strip()
        if part:
            yield part
        start = match.end()
    part = text[start:].strip()
    if part:
        yield part


def _period_marks(text: str, *, comparison: bool = False) -> list[tuple[int | None, int]]:
    marks = []
    for match in _QUARTER_RE.finditer(text):
        if not comparison:
            prelude = text[max(0, match.start() - 32):match.start()]
            if _COMPARISON_PRELUDE_RE.search(prelude):
                continue
        quarter = int(match.group(1)) if match.group(1) else _QNAME_TO_NUM[match.group(2).lower()]
        year = int(match.group(3)) if match.group(3) else None
        marks.append((year, quarter))
    return marks


def _one_period(marks: list[tuple[int | None, int]]) -> tuple[int, int] | None:
    full = {mark for mark in marks if mark[0] is not None}
    if len(full) != 1:
        return None
    period = next(iter(full))
    if any(quarter != period[1] for _, quarter in marks):
        return None
    return period


def _period_compatible(marks: list[tuple[int | None, int]], period: tuple[int, int]) -> bool:
    return all(quarter == period[1] and (year is None or year == period[0])
               for year, quarter in marks)


def _source_unit(bound: BoundRelease, node) -> dict[str, Any] | None:
    """Bind a native-replayed node to the exact raw character and byte window."""
    span = node.source_span
    if (span.source_sha256 != bound.revision.source_sha256
            or bound.document.source_sha256 != bound.revision.source_sha256
            or any(type(value) is not int for value in (
                span.char_start, span.char_end, span.byte_start, span.byte_end))):
        return None
    try:
        receipt = receipt_for_char_span(
            source=bound.source, source_sha256=bound.revision.source_sha256,
            char_start=span.char_start, char_end=span.char_end,
        )
    except ReceiptError:
        return None
    if receipt.byte_start != span.byte_start or receipt.byte_end != span.byte_end:
        return None
    # The caller has verified the complete parsed view through normalize_filing.
    # Receipt visible_text deliberately spaces tags; it is not the parser's
    # text normalization (which preserves words/numbers split by inline markup).
    return {"text": node.text, "start": span.char_start, "end": span.char_end}



def _adjacent(left, right) -> bool:
    return (left.section_id == right.section_id
            and not left.unread_after and not right.unread_before
            and left.source_span.char_end <= right.source_span.char_start)


def _issuer_lead(prefix: str, *, issuer_seen: bool) -> tuple[str, str, bool] | None:
    """Return the delivery lead, its qualified period prelude, and 'now' flag."""
    matches = list(_ISSUER_EXPECTATION_RE.finditer(prefix))
    if issuer_seen:
        matches.extend(_PRONOUN_EXPECTATION_RE.finditer(prefix))
    if not matches:
        return None
    owner = max(matches, key=lambda match: match.start())
    prelude = prefix[:owner.start()]
    if _RELATIVE_PERIOD_RE.search(prelude) or _INVALID_QUARTER_RE.search(prelude):
        return None
    if re.search(
        r"\b(?:if|unless|whether|hypothetical|not|never|denies?|disputes?|"
        r"analysts?|competitors?|rivals?|suppliers?|customers?)\b",
        prelude, re.IGNORECASE,
    ):
        return None
    reduced = _QUARTER_RE.sub("", prelude)
    reduced = re.sub(r"\b(?:for|in|during|the)\b", "", reduced, flags=re.IGNORECASE)
    period_only = not reduced.strip(" \t,:()·•-")
    # An explicit different antecedent must never inherit an earlier issuer.
    if _PRONOUN_EXPECTATION_RE.fullmatch(owner.group()) and not period_only:
        return None
    period_prelude = prelude if period_only else ""
    return (prefix[owner.end():], period_prelude,
            bool(re.search(r"\bnow\b", owner.group(), re.IGNORECASE)))

def _intro_kind(text: str) -> tuple[str, str] | None:
    """Return the immediate introduction kind and its qualified period text."""
    if not text.rstrip().endswith(":") or _RANGE_RE.search(text):
        return None
    lead = _issuer_lead(text, issuer_seen=False)
    if lead is not None:
        meaning, period_prelude, _ = lead
        tail = meaning.rstrip(":").strip()
        if re.fullmatch(
            r"(?:(?:the\s+following)|(?:(?:its|our)\s+)?(?:vehicle\s+deliveries|deliveries\s+of\s+vehicles))?",
            tail, re.IGNORECASE,
        ):
            return "expectation", period_prelude
        if _one_period(_period_marks(tail)) is not None:
            reduced = _QUARTER_RE.sub("", tail)
            reduced = re.sub(r"\b(?:for|in|during|the)\b", "", reduced, flags=re.IGNORECASE)
            reduced = _compact_text(reduced.strip(" ,:"))
            if not reduced or re.fullmatch(
                r"(?:(?:its|our)\s+)?(?:vehicle\s+deliveries|deliveries\s+of\s+vehicles)",
                reduced, re.IGNORECASE,
            ):
                return "expectation", period_prelude + " " + tail
    plain = text.rstrip(":").strip()
    if (re.match(r"^(?:for|in|during)\b", plain, re.IGNORECASE)
            and _one_period(_period_marks(plain)) is not None):
        rest = _QUARTER_RE.sub("", plain)
        if re.fullmatch(r"(?:for|in|during)\s+(?:the\s+)?", rest, re.IGNORECASE):
            return "period", plain
    return None



def _context(bound: BoundRelease, blocks: tuple, index: int) -> tuple[dict | None, dict | None]:
    intro = None
    first = index
    if index > 0:
        previous = blocks[index - 1]
        if previous.kind is BlockKind.PARAGRAPH and _adjacent(previous, blocks[index]):
            unit = _source_unit(bound, previous)
            if unit is not None:
                parts = list(_sentences(unit["text"]))
                last = parts[-1] if parts else ""
                kind = _intro_kind(last)
                if kind is not None:
                    intro = {**unit, "text": last, "kind": kind[0], "period_text": kind[1]}
                    first = index - 1
                    # A short period-only introduction may precede "Company expects:".
                    if kind[0] == "expectation" and first > 0:
                        earlier = blocks[first - 1]
                        if earlier.kind is BlockKind.PARAGRAPH and _adjacent(earlier, previous):
                            period_unit = _source_unit(bound, earlier)
                            period_kind = _intro_kind(period_unit["text"]) if period_unit else None
                            if period_kind is not None and period_kind[0] == "period":
                                intro["text"] = period_unit["text"] + " " + last
                                intro["period_text"] = period_kind[1] + " " + kind[1]
                                intro["start"] = period_unit["start"]
                                first -= 1
    heading = None
    if first > 0:
        previous = blocks[first - 1]
        if previous.kind is BlockKind.HEADING and _adjacent(previous, blocks[first]):
            unit = _source_unit(bound, previous)
            if (unit is not None and _OUTLOOK_HEADING_RE.search(unit["text"])
                    and not _REJECT_MEANING_RE.search(unit["text"])):
                heading = unit
    return intro, heading



def _affirmative_delivery(
    prefix: str, *, issuer_seen: bool, intro: dict | None
) -> tuple[bool, bool, bool, str]:
    """Qualify THIS range's delivery lead and the periods it actually owns."""
    lead = _issuer_lead(prefix, issuer_seen=issuer_seen)
    if lead is not None:
        meaning, period_prelude, says_now = lead
        uses_intro = False
    elif intro is not None and intro["kind"] == "expectation":
        meaning = prefix
        period_prelude = ""
        uses_intro = True
        says_now = bool(re.search(r"\bnow\b", intro["text"], re.IGNORECASE))
    else:
        return False, False, False, ""
    if _REJECT_MEANING_RE.search(meaning):
        return False, False, False, ""
    delivery = _DELIVERY_RE.search(meaning)
    if delivery is None:
        return False, False, False, ""
    before_delivery = _QUARTER_RE.sub("", meaning[:delivery.start()])
    before_delivery = re.sub(r"\b(?:its|our|the|total|for|in|during)\b", "", before_delivery,
                             flags=re.IGNORECASE)
    if before_delivery.strip(" \t,:()·•-"):
        return False, False, False, ""
    # Reject another entity or metric between the delivery noun and its range.
    rest = _QUARTER_RE.sub("", meaning[delivery.end():])
    rest = re.sub(r"\b(?:for|in|during|the|of|vehicles?|to|be|at|range)\b", "", rest,
                  flags=re.IGNORECASE)
    if rest.strip(" \t,:()·•-"):
        return False, False, False, ""
    return True, uses_intro, says_now, period_prelude + " " + meaning



def _delivery_period_text(lead: str, suffix: str) -> str | None:
    """Only a directly attached period can extend the delivery assertion."""
    tail = suffix.strip()
    if tail.startswith(","):
        following = tail[1:].lstrip()
        # A comma can introduce the horizon or an independent clause. Only the
        # explicit period preposition is accepted here.
        tail = following if re.match(r"^(?:for|in|during)\b", following, re.IGNORECASE) else ""
    tail = tail.split(",", 1)[0].strip(" \t.:;")
    if _RELATIVE_PERIOD_RE.search(tail) or _INVALID_QUARTER_RE.search(tail):
        return None
    rest = _QUARTER_RE.sub("", tail)
    rest = re.sub(r"\b(?:for|in|during|the|and|or)\b", "", rest, flags=re.IGNORECASE)
    if not rest.strip(" \t():-"):
        return lead + " " + tail
    # A different metric's date is neither this horizon nor a fallback year.
    if _period_marks(tail):
        return None
    return lead

def _resolve_period(
    assertion: str, intro: dict | None, heading: dict | None, *, uses_intro: bool
) -> tuple[tuple[int, int], str] | None:
    if _RELATIVE_PERIOD_RE.search(assertion) or _INVALID_QUARTER_RE.search(assertion):
        return None
    marks = _period_marks(assertion)
    period = _one_period(marks)
    if period is not None:
        if uses_intro and intro is not None:
            if (_RELATIVE_PERIOD_RE.search(intro["period_text"])
                    or _INVALID_QUARTER_RE.search(intro["period_text"])
                    or not _period_compatible(_period_marks(intro["period_text"]), period)):
                return None
        return period, "assertion"
    # Conflicting explicit periods cannot be replaced by context.
    if any(year is not None for year, _ in marks):
        return None
    for kind, context in (("intro", intro), ("heading", heading)):
        if context is None:
            continue
        text = context["period_text"] if kind == "intro" else context["text"]
        if _RELATIVE_PERIOD_RE.search(text) or _INVALID_QUARTER_RE.search(text):
            return None
        context_marks = _period_marks(text)
        if not context_marks:
            continue
        period = _one_period(context_marks)
        if period is None or not _period_compatible(marks, period):
            return None
        return period, kind
    return None


def _revision_status(
    current: str, prior: str | None, period: tuple[int, int], *, says_now: bool
) -> str | None:
    if prior is None:
        # An unresolved change/baseline must not become a new assertion.
        unresolved_change = re.search(
            r"\b(?:revised?|updated?|changed?|raised?|lowered?|reduced?|increased?)\s+"
            r"(?:(?:its|the)\s+)?(?:vehicle\s+)?(?:delivery|deliveries|outlook|guidance|forecast)\b",
            current, re.IGNORECASE,
        )
        if says_now or _PRIOR_FORECAST_RE.search(current) or unresolved_change:
            return None
        return "introduced"
    ranges = list(_RANGE_RE.finditer(prior))
    if len(ranges) != 1 or not _PRIOR_FORECAST_RE.search(prior):
        return None
    match = ranges[0]
    low, high = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
    if _parse_int(low) > _parse_int(high):
        return None
    if re.search(r"\b(?:revenue|production|sales|orders?|competitors?|rivals?)\b", prior, re.IGNORECASE):
        return None
    marks = _period_marks(prior, comparison=True)
    if (_RELATIVE_PERIOD_RE.search(prior) or _INVALID_QUARTER_RE.search(prior)
            or not _period_compatible(marks, period)):
        return None
    direct_change = bool(_DIRECT_CHANGE_RE.match(prior))
    if not (direct_change or _SAME_PERIOD_RE.search(prior) or _one_period(marks) == period):
        return None
    return "revised"


def _unit_claims(
    unit: dict, intro: dict | None, heading: dict | None
) -> list[dict[str, Any]]:
    claims = []
    issuer_seen = bool(intro is not None and intro["kind"] == "expectation")
    for clause in _sentences(unit["text"]):
        qualified_here = False
        ranges = list(_RANGE_RE.finditer(clause))
        links = [link for link in _PRIOR_LINK_RE.finditer(clause)
                 if any(match.end() <= link.start() for match in ranges)]
        link = links[0] if len(links) == 1 else None
        for match in ranges:
            if link is not None and match.start() > link.start():
                continue
            current = clause[:link.start()] if link is not None else clause
            prior = clause[link.start():] if link is not None else None
            prefix = current[:match.start()]
            if match.group(3) is not None:
                prefix += "deliveries"
            qualified, uses_intro, says_now, period_lead = _affirmative_delivery(
                prefix, issuer_seen=issuer_seen, intro=intro)
            if not qualified:
                continue
            if len(links) > 1 or (len(ranges) > 1 and link is None):
                return []
            low_text, high_text = (
                (match.group(1), match.group(2)) if match.group(1)
                else (match.group(3), match.group(4))
            )
            low, high = _parse_int(low_text), _parse_int(high_text)
            if low > high:
                return []
            period_text = _delivery_period_text(period_lead, current[match.end():])
            if period_text is None:
                return []
            resolved = _resolve_period(period_text, intro, heading, uses_intro=uses_intro)
            if resolved is None:
                return []
            period, period_source = resolved
            status = _revision_status(current, prior, period, says_now=says_now)
            if status is None:
                return []
            start = unit["start"]
            if uses_intro or period_source == "intro":
                start = min(start, intro["start"])
            if period_source == "heading":
                start = min(start, heading["start"])
                # The contiguous introduction is also evidence for a split assertion.
                if uses_intro:
                    start = min(start, intro["start"])
            claims.append({
                "period": period, "low": low, "high": high, "status": status,
                "start": start, "end": unit["end"],
            })
            qualified_here = True
        issuer_seen = issuer_seen or qualified_here
    return claims


def _extract_vehicle_guidance(
    *, bound: BoundRelease, document_id: str, event_id: str
) -> list[dict[str, Any]]:
    document = bound.document
    try:
        replayed = normalize_filing({
            "content": bound.source, "content_type": document.content_type,
            "accession": document.accession, "form": document.form,
            "entity_cik": document.entity_cik, "filed_at": document.filed_at,
            "report_date": document.report_date, "source_url": document.source_url,
        })
    except (TypeError, ValueError):
        return []
    # Reuse the native parser's exact semantics for paragraphs, inline markup,
    # cells and unread boundaries. A modified parsed view cannot stand in for
    # the source, and receipt whitespace is never treated as parser whitespace.
    if replayed != document or replayed.source_sha256 != bound.revision.source_sha256:
        return []
    blocks = replayed.blocks
    claims: dict[tuple[int, int], dict[str, Any]] = {}
    for index, block in enumerate(blocks):
        units = []
        if block.kind is BlockKind.PARAGRAPH:
            unit = _source_unit(bound, block)
            if unit is not None:
                units.append(unit)
        elif block.kind is BlockKind.TABLE and block.table is not None:
            table = block.table
            if (table.nested or table.contains_nested or not table.rows
                    or any(len(row) != 1 for row in table.rows)
                    or any(cell.colspan != 1 or cell.rowspan != 1 or cell.span_overflow
                           for row in table.rows for cell in row)):
                continue
            units = [_source_unit(bound, row[0]) for row in table.rows]
            if any(unit is None for unit in units):
                continue
        else:
            continue
        intro, heading = _context(bound, blocks, index)
        for unit_index, unit in enumerate(units):
            # A later table cell cannot borrow an introduction through another cell.
            context_intro = intro if unit_index == 0 else None
            context_heading = heading if unit_index == 0 else None
            for claim in _unit_claims(unit, context_intro, context_heading):
                period = claim["period"]
                previous = claims.get(period)
                if previous is not None:
                    if ((previous["low"], previous["high"], previous["status"])
                            != (claim["low"], claim["high"], claim["status"])):
                        return []
                    continue
                claims[period] = claim
    items = []
    for (year, quarter), claim in sorted(claims.items()):
        try:
            receipt = receipt_for_char_span(
                source=bound.source, source_sha256=bound.revision.source_sha256,
                char_start=claim["start"], char_end=claim["end"],
            )
            span = text_span(
                document_id=document_id, document_version=1,
                body_sha256=bound.revision.source_sha256, segment_index=0,
                segment_text=bound.source, start_byte=receipt.byte_start,
                end_byte=receipt.byte_end, text=receipt.span_text,
                rights_profile="rp_public_primary_v1",
                display_excerpt=receipt.value_text[:200],
            )
        except (ReceiptError, DocumentError):
            continue
        items.append({
            "schema": "guidance_item.v1", "metric": "vehicle_deliveries",
            "low": claim["low"], "high": claim["high"], "unit": "vehicles",
            "horizon": f"FY{year} Q{quarter}", "status": claim["status"],
            "source_span": span.to_payload(),
        })
    return items


def extract_vehicle_guidance(
    *, bound: BoundRelease, document_id: str, event_id: str
) -> list[dict[str, Any]]:
    """Return the existing eight-field guidance payload; never activate a consumer.

    event_id remains accepted for caller continuity. document_id, version 1 and
    the full bound source as segment 0 follow the existing issuer-profile API.
    Source observations do not establish decision-time history.
    """
    return _extract_vehicle_guidance(
        bound=bound, document_id=document_id, event_id=event_id
    )
