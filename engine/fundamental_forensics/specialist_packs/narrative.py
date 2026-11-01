"""Deterministic narrative text-span locator over the primary iXBRL document.

A.1/A.2 of the specialist-pack seat spec: one frozen pipeline turns the primary
``.htm`` member into a whitespace-collapsed narrative string whose every
character carries the byte offset of the raw-document byte (or entity) it came
from, plus the section locator every narrative pack (PK09 first, then PK07,
PK08, PK10, PK12) reads ``text_span`` evidence through.

Laws: standard library only (``html``/``re``); same bytes -> same
``NarrativeText``; no fuzzy matching, no NLP, no network.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

#: Character index pair ``(start, end)`` into ``NarrativeText.text``.
Span = tuple[int, int]

# Subtrees dropped wholesale before any text is read. ``ix:header`` carries the
# XBRL contexts; its local name is matched after namespace-prefix stripping.
_DROP_SUBTREE_TAGS = frozenset({"script", "style", "ix:header"})
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
    """

    document_id: str
    text: str
    offsets: tuple[int, ...]


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
        name = name_match.group(1).lower() if name_match else b""
        closing = re.match(rb"<\s*/", tag) is not None
        self_closing = tag.rstrip().endswith(b"/>")
        if name in _DROP_SUBTREE_TAGS and not closing and not self_closing:
            close = re.compile(
                rb"</\s*" + re.escape(name) + rb"\s*>", re.IGNORECASE
            ).search(raw, end)
            if close is None:  # unterminated drop subtree: nothing more to read
                break
            i = close.end()
            continue
        # Every other tag becomes one space citing the tag's first byte.
        chars.append(" ")
        offsets.append(lt)
        i = end
    out_chars: list[str] = []
    out_offsets: list[int] = []
    for ch, off in zip(chars, offsets):
        if ch.isspace():
            if out_chars and out_chars[-1] == " ":
                continue  # collapsed run keeps its first byte's offset
            out_chars.append(" ")
            out_offsets.append(off)
        else:
            out_chars.append(ch)
            out_offsets.append(off)
    return NarrativeText(
        document_id=document_id,
        text="".join(out_chars),
        offsets=tuple(out_offsets),
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


__all__ = [
    "NarrativeText",
    "SectionSpec",
    "Span",
    "locate_section",
    "narrative_text_from_bytes",
    "primary_document_text",
    "sentence_span",
]
