"""Deterministic narrative text-span locator over the primary iXBRL document.

A.1/A.2 of the specialist-pack seat spec: one frozen pipeline turns the primary
``.htm`` member into a whitespace-collapsed narrative string whose every
character carries the byte offset of the raw-document byte (or entity) it came
from, plus the section locator every narrative pack (PK09 first, then PK07,
PK08, PK10, PK12) reads ``text_span`` evidence through.

Laws: standard library only (``html``/``re``/``bisect``); same bytes -> same
``NarrativeText``; no fuzzy matching, no NLP, no network.
"""
from __future__ import annotations

import bisect
import html
import re
from dataclasses import dataclass
from typing import Any

#: Character index pair ``(start, end)`` into ``NarrativeText.text``.
Span = tuple[int, int]

# Subtrees dropped wholesale before any text is read. ``ix:header`` carries the
# XBRL contexts; its local name is matched after namespace-prefix stripping.
_DROP_SUBTREE_TAGS = frozenset({"script", "style", "ix:header"})
# HTML elements that open or close a block: the same names as pk01_debt's
# ``_BLOCK_TAGS`` (copied, not imported — each pack owns its own frozen
# vocabulary). A space emitted for one of these tags is a block break: the
# collapsed character run that contains it bounds a sentence in
# ``block_sentence_span``. Inline markup (``span``, ``a``, ``b``, ``i``,
# ``font``, ...) and namespaced wrappers (``ix:nonNumeric`` — any name
# containing ``:``) sit mid-sentence and never break.
_BLOCK_BREAK_TAGS = frozenset(
    (
        "address article aside blockquote body br caption center dd div dl dt"
        " footer h1 h2 h3 h4 h5 h6 header hr html li ol p pre section table"
        " tbody td tfoot th thead tr ul"
    ).split()
)
# Semicolon-terminated entities only: a bare ``&`` stays literal.
_ENTITY_RE = re.compile(rb"&(#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
# TOC-line fingerprints for the skip rule (A.2).
_ITEM_HEADING_RE = re.compile(r"Item\s+\d+[A-C]?\.")
_PAGE_THEN_ITEM_RE = re.compile(r"\b\d{1,3}\s+Item\b")
_TO_WINDOW_CHARS = 200


@dataclass(frozen=True)
class NarrativeText:
    """One document's narrative text with a per-character raw byte-offset map.

    ``offsets[i]`` is the byte offset in the raw primary document of the byte
    (or entity start) that produced ``text[i]``. A tag-derived space cites the
    tag's first byte; a collapsed whitespace run cites its first byte; an
    entity-derived character cites the entity's ``&``.

    ``block_breaks`` lists the ``text`` indices of the collapsed spaces that
    carry a ``_BLOCK_BREAK_TAGS`` boundary (PK10's block-bounded sentence
    rule); it is derived data — ``text`` and ``offsets`` are unchanged by it.
    """

    document_id: str
    text: str
    offsets: tuple[int, ...]
    block_breaks: tuple[int, ...] = ()


@dataclass(frozen=True)
class SectionSpec:
    """One governing section: a heading regex plus end-heading regexes."""

    heading: str
    end_headings: tuple[str, ...]
    skip_toc: bool = True


def _emit_literal(
    seg: bytes, base: int, chars: list[str], offsets: list[int]
) -> None:
    """Emit one entity-free byte run as characters with byte offsets."""
    decoded = seg.decode("utf-8", errors="replace")
    pos = 0
    for ch in decoded:
        chars.append(ch)
        offsets.append(base + pos)
        pos += len(ch.encode("utf-8", errors="replace"))


def _emit_text_run(
    seg: bytes, base: int, chars: list[str], offsets: list[int]
) -> None:
    """Emit one inter-tag byte run, expanding semicolon entities."""
    pos = 0
    for match in _ENTITY_RE.finditer(seg):
        if match.start() > pos:
            _emit_literal(seg[pos : match.start()], base + pos, chars, offsets)
        entity_at = base + match.start()
        for ch in html.unescape(match.group(0).decode("ascii")):
            chars.append(ch)
            offsets.append(entity_at)
        pos = match.end()
    if pos < len(seg):
        _emit_literal(seg[pos:], base + pos, chars, offsets)


def _tag_end(raw: bytes, start: int) -> int:
    """Index just past the ``>`` closing the tag that starts at ``start``."""
    quote: bytes | None = None
    j = start + 1
    while j < len(raw):
        c = raw[j : j + 1]
        if quote is not None:
            if c == quote:
                quote = None
        elif c in (b'"', b"'"):
            quote = c
        elif c == b">":
            return j + 1
        j += 1
    return len(raw)


def narrative_text_from_bytes(raw: bytes, document_id: str) -> NarrativeText:
    """Build the frozen A.1 narrative text of one raw primary document."""
    chars: list[str] = []
    offsets: list[int] = []
    # Input indices (into ``chars``) of tag spaces emitted for block-level
    # tags: opening, closing and self-closing alike. A namespaced name
    # (anything containing ``:``) never marks.
    block_tag_spaces: set[int] = set()
    i = 0
    n = len(raw)
    while i < n:
        lt = raw.find(b"<", i)
        if lt < 0:
            _emit_text_run(raw[i:], i, chars, offsets)
            break
        if lt > i:
            _emit_text_run(raw[i:lt], i, chars, offsets)
        end = _tag_end(raw, lt)
        tag = raw[lt:end]
        name_match = re.match(rb"<\s*/?\s*([A-Za-z:][\w.:-]*)", tag)
        raw_name = name_match.group(1) if name_match else b""
        # Decode before the compare: the drop set holds str names, while the
        # closing-tag regex below keeps the raw bytes.
        name = raw_name.decode("ascii", "ignore").lower()
        closing = re.match(rb"<\s*/", tag) is not None
        self_closing = tag.rstrip().endswith(b"/>")
        if name in _DROP_SUBTREE_TAGS and not closing and not self_closing:
            close = re.compile(
                rb"</\s*" + re.escape(raw_name) + rb"\s*>", re.IGNORECASE
            ).search(raw, end)
            if close is None:  # unterminated drop subtree: nothing more to read
                break
            i = close.end()
            continue
        # Every other tag becomes one space citing the tag's first byte.
        if ":" not in name and name in _BLOCK_BREAK_TAGS:
            block_tag_spaces.add(len(chars))
        chars.append(" ")
        offsets.append(lt)
        i = end
    out_chars: list[str] = []
    out_offsets: list[int] = []
    # Output indices of collapsed spaces whose run held a block-tag space.
    out_breaks: list[int] = []
    space_at: int | None = None  # output index of the current collapsed space
    space_marked = False
    for idx, (ch, off) in enumerate(zip(chars, offsets)):
        if ch.isspace():
            if out_chars and out_chars[-1] == " ":
                # collapsed run keeps its first byte's offset; a marked tag
                # space dropped here still marks the run's kept space.
                if idx in block_tag_spaces and not space_marked:
                    space_marked = True
                    out_breaks.append(space_at)
                continue
            out_chars.append(" ")
            out_offsets.append(off)
            space_at = len(out_chars) - 1
            space_marked = idx in block_tag_spaces
            if space_marked:
                out_breaks.append(space_at)
        else:
            space_at = None
            space_marked = False
            out_chars.append(ch)
            out_offsets.append(off)
    # A block break separates narrative text on both sides: the block-tag
    # spaces at the very start or end of the document abut no text, so they
    # are not breaks (B1: ``<p>alpha</p><p>beta</p>`` breaks exactly once,
    # between "alpha" and "beta").
    block_breaks = tuple(k for k in out_breaks if 0 < k < len(out_chars) - 1)
    return NarrativeText(
        document_id=document_id,
        text="".join(out_chars),
        offsets=tuple(out_offsets),
        block_breaks=block_breaks,
    )


def primary_document_text(package: Any) -> NarrativeText:
    """Read the primary ``.htm`` member of one filing package (A.1)."""
    from .base import SpecialistPackError  # deferred: base imports this module

    manifest = getattr(package, "manifest", None)
    members = getattr(package, "members", None)
    if not isinstance(manifest, dict) or not isinstance(members, dict):
        raise SpecialistPackError("narrative input is not a filing package")
    primary = str(manifest.get("primary_document") or "")
    raw = members.get(primary)
    if raw is None:
        raise SpecialistPackError(
            "primary document member is not retained: " + primary
        )
    return narrative_text_from_bytes(raw, primary)


def locate_section(nt: NarrativeText, spec: SectionSpec) -> Span | None:
    """Locate one governing section, or ``None`` when it is not supplied."""
    matches = list(re.finditer(spec.heading, nt.text, re.IGNORECASE))
    if not matches:
        return None
    chosen = matches[-1]
    if spec.skip_toc:
        for match in matches:
            window = nt.text[match.end() : match.end() + _TO_WINDOW_CHARS]
            if _ITEM_HEADING_RE.search(window) or _PAGE_THEN_ITEM_RE.search(
                window
            ):
                continue
            chosen = match
            break
    end = len(nt.text)
    for end_heading in spec.end_headings:
        boundary = re.compile(end_heading, re.IGNORECASE).search(
            nt.text, chosen.end()
        )
        if boundary is not None:
            end = min(end, boundary.start())
    return (chosen.start(), end)


def sentence_span(text: str, start: int, end: int, bounds: Span) -> Span:
    """The ``. ``-delimited sentence containing ``[start, end)`` inside bounds."""
    lo, hi = bounds
    before = text.rfind(". ", lo, start)
    sentence_start = before + 2 if before >= 0 else lo
    after = text.find(". ", end, hi)
    sentence_end = after + 1 if after >= 0 else hi
    return (sentence_start, min(sentence_end, hi))


def block_sentence_span(
    nt: NarrativeText, start: int, end: int, bounds: Span
) -> Span:
    """``sentence_span`` clipped to the nearest block breaks around ``[start, end)``.

    The ``. ``-delimited sentence still comes from :func:`sentence_span`; a
    block break then bounds it on both sides — the sentence starts after the
    greatest break before ``start`` and ends at the least break at or after
    ``end`` — so a cadence and a vote mention in different paragraphs or
    table cells never share a sentence. With no recorded breaks the result
    is exactly ``sentence_span``'s.
    """
    sentence_start, sentence_end = sentence_span(nt.text, start, end, bounds)
    breaks = nt.block_breaks
    left = bisect.bisect_left(breaks, start)
    if left > 0 and breaks[left - 1] + 1 > sentence_start:
        sentence_start = breaks[left - 1] + 1
    right = bisect.bisect_left(breaks, end)
    if right < len(breaks) and breaks[right] < sentence_end:
        sentence_end = breaks[right]
    return (sentence_start, sentence_end)


__all__ = [
    "NarrativeText",
    "SectionSpec",
    "Span",
    "block_sentence_span",
    "locate_section",
    "narrative_text_from_bytes",
    "primary_document_text",
    "sentence_span",
]
