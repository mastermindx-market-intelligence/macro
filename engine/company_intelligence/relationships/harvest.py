"""M2 harvest pure functions: segmentation, iXBRL facts, cue candidates.

No network, no wall clock, no store: everything here consumes bytes and
returns plain dicts.  The network layer lives in
:mod:`engine.company_intelligence.relationships.edgar`; the CLI wires them
together.  Nothing here scores, ranks, predicts or sizes relationships —
candidates are unjudged byte spans for later lanes.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from bisect import bisect_right

from engine.company_intelligence.relationships.clock import (
    ClockRefused,
    et_acceptance_to_utc,
)
from engine.company_intelligence.relationships.replay import MAX_SPAN_BYTES

# --- frozen input pins (sha256 over the exact bytes) --------------------------

PINS = {
    "curated_aliases_v1.json": (
        "413ea9e26b08a1b2d59099bc86456d9cad1ea0347cfb33bb1f42b11a1b4b8c76"
    ),
    "filing_census_v1.json": (
        "d5deb2764e67e25789452f11b2a4793b8c00eef5431474ad42bfde5a60affaa9"
    ),
    "leaves_v1.json": (
        "8e505316da9ccc1285227eec080a52e5e182f28780401dfa1817dd6c5313adef"
    ),
    "resolver_us_issuers_v1.json": (
        "a18924867fa53f58c0e01ac873d5bc2a8d610a01b69ad333ea6dfb51183303cd"
    ),
}

ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A")
AMENDMENT_FORMS = ("10-K/A", "20-F/A", "40-F/A")
MAX_DOCS_PER_FILING = 12
MAX_DOC_BYTES = 40 * 1024 * 1024
MAX_CANDIDATES_PER_DOCUMENT = 40
MAX_CANDIDATES_PER_FILING = 120
DOC_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.(htm|html)$")

COUNTER_KEYS = (
    "overflow_document",
    "overflow_filing",
    "span_too_large",
    "span_not_utf8",
    "xbrl_fact_hidden",
    "xbrl_fact_no_counterparty_axis",
    "xbrl_fact_unanchored",
    "xbrl_context_too_large",
    "excerpt_self_check_failed",
    "clock_refused",
    "doc_too_large",
    "documents_overflow",
    "cache_integrity_refetch",
    "extension_skipped",
)


class InputPinMismatch(Exception):
    """The four m2_inputs files do not hash to the frozen pins."""


def new_counters() -> dict:
    return {key: 0 for key in COUNTER_KEYS}


def load_inputs(inputs_dir):
    """The four pinned m2_inputs documents, pins verified (rc-2 on drift)."""
    import os

    inputs_dir = str(inputs_dir)
    loaded = {}
    for name, expected in PINS.items():
        path = os.path.join(inputs_dir, name)
        with open(path, "rb") as handle:
            raw = handle.read()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise InputPinMismatch(
                f"{path} hashes to "
                f"{hashlib.sha256(raw).hexdigest()}, pin expects {expected}"
            )
        loaded[name[: -len(".json")]] = json.loads(raw.decode("utf-8"))
    return {
        "leaves": loaded["leaves_v1"],
        "census": loaded["filing_census_v1"],
        "aliases": loaded["curated_aliases_v1"],
        "resolver": loaded["resolver_us_issuers_v1"],
        "sha256": {
            name: PINS[name] for name in PINS
        },
    }


def leaf_issuers(leaves_doc: dict, leaf: str) -> list:
    try:
        return list(leaves_doc["leaves"][leaf])
    except KeyError as error:
        raise ValueError(f"unknown leaf {leaf!r}") from error


def slice_issuers(issuers: list, i: int, n: int) -> list:
    """sorted(issuers)[k] with k % n == i-1 (1-based slice i of n)."""
    if not (1 <= i <= n) or n < 1:
        raise ValueError(f"bad slice {i}/{n}")
    return [
        issuer for k, issuer in enumerate(sorted(issuers)) if k % n == i - 1
    ]


# --- hint filter ---------------------------------------------------------------

_CORP_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd",
    "limited", "plc", "llc", "lp", "sa", "nv", "ag", "se",
}


def norm_text(text) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _strip_suffixes(norm_name: str) -> str:
    tokens = norm_name.split()
    while len(tokens) > 1 and tokens[-1] in _CORP_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def build_hints(resolver_doc: dict, aliases_doc: dict, issuer_id: str):
    """(hints, own_hints): the alias/name filter with the filer's own removed.

    Both sets hold suffix-stripped ``alias_norm``/``sec_name`` forms; the
    filer's own forms never qualify a sentence (H5 rank 1).
    """
    own: set = set()
    all_hints: set = set()
    for row in resolver_doc["rows"]:
        hint = _strip_suffixes(norm_text(row["sec_name"]))
        if len(hint) >= 4:
            (own if row["issuer_id"] == issuer_id else all_hints).add(hint)
    for alias in aliases_doc["aliases"]:
        hint = norm_text(alias["alias_norm"])
        if len(hint) >= 4:
            (own if alias["issuer_id"] == issuer_id else all_hints).add(hint)
    return all_hints - own, own


# --- filing resolution (H1/H2) --------------------------------------------------


def accepted_at_from_header(header: str):
    """(accepted_at, refusal_reason) from the index-header stamp (A24)."""
    try:
        return et_acceptance_to_utc(header), None
    except ClockRefused as error:
        return None, error.args[0] if error.args else "refused"


def form_rejection(index_form, census_form):
    """Rejection reason for the form pair, or None when it passes H2."""
    if index_form != census_form:
        return "FORM_MISMATCH"
    if index_form not in ANNUAL_FORMS:
        return "OUT_OF_CONTRACT_FORM"
    return None


def resolve_filing(*, leaf, issuer_id, cik_str, sec_name, filing_role,
                   census_filing, header, census_fetched_at):
    """Ledger-row base for one filing from its parsed index header.

    State ``pending_documents`` means the form and clock checks passed and the
    document fetches decide collected/partial/rejected/unavailable next.
    """
    row = {
        "leaf": leaf,
        "issuer_id": issuer_id,
        "cik": cik_str,
        "sec_name": sec_name,
        "accession": census_filing["accessionNumber"],
        "form": census_filing["form"],
        "filing_role": filing_role,
        "state": "pending_documents",
        "reason": None,
        "accepted_at": None,
        "sec_index_header_acceptance_et": header.get("acceptance_et"),
        "sec_submissions_acceptance_raw": census_filing.get(
            "acceptanceDateTime"
        ),
        "census_fetched_at": census_fetched_at,
        "filed_at": header.get("filed_as_of_date"),
        "period_of_report": header.get("period_of_report"),
        "notes": [],
        "documents": [],
    }
    refusal = form_rejection(header.get("submission_type"), census_filing["form"])
    if refusal is not None:
        row["state"] = "rejected"
        row["reason"] = refusal
        return row
    accepted_at, clock_reason = accepted_at_from_header(
        header.get("acceptance_et") or ""
    )
    if clock_reason is not None:
        row["state"] = "rejected"
        row["reason"] = f"CLOCK_REFUSED:{clock_reason}"
        return row
    row["accepted_at"] = accepted_at
    return row


def build_unavailable_row(leaf: str, issuer_id: str, census_entry: dict) -> dict:
    """One ``unavailable`` ledger row for a census state that is not OK."""
    return {
        "leaf": leaf,
        "issuer_id": issuer_id,
        "cik": _cik_str(census_entry.get("cik")),
        "sec_name": census_entry.get("sec_name"),
        "accession": None,
        "form": None,
        "filing_role": None,
        "state": "unavailable",
        "reason": census_entry.get("state"),
        "accepted_at": None,
        "sec_index_header_acceptance_et": None,
        "sec_submissions_acceptance_raw": None,
        "census_fetched_at": census_entry.get("fetched_at"),
        "filed_at": None,
        "period_of_report": None,
        "notes": [],
        "documents": [],
    }


def _cik_str(cik) -> str:
    return f"{int(cik):010d}"


def select_documents(header_documents: list, form: str, census_primary: str):
    """(documents, notes) per H2: primary + exhibit classes, capped, filtered."""
    notes: list = []
    by_type = {}
    for entry in header_documents:
        by_type.setdefault(entry["type"], []).append(entry["filename"])
    wanted = [entry for entry in header_documents if entry["type"] == form]
    exhibit_prefix = "EX-13" if form in ("10-K", "10-K/A") else "EX-99"
    exhibits = [
        entry
        for entry in header_documents
        if entry["type"].startswith(exhibit_prefix)
    ]
    ordered = wanted + exhibits
    if census_primary is not None:
        if not wanted or wanted[0]["filename"] != census_primary:
            notes.append("PRIMARY_DOC_MISMATCH")
        primary = {"filename": census_primary, "type": form}
        ordered = [primary] + [
            entry for entry in ordered if entry["filename"] != census_primary
        ]
    selected = []
    for entry in ordered:
        if len(selected) >= MAX_DOCS_PER_FILING:
            break
        if not DOC_NAME_RE.match(entry["filename"]):
            continue
        selected.append({"filename": entry["filename"], "type": entry["type"]})
    return selected, notes


# --- segmentation (H3) ----------------------------------------------------------

TAG_RE = re.compile(rb"<[^>]+>")
TAG_AT_RE = re.compile(rb"<[^>]+>")
ENTITY_RE = re.compile(
    rb"&[a-zA-Z][a-zA-Z0-9]*;|&#[0-9]+;|&#[xX][0-9a-fA-F]+;"
)
ENTITY_AT_RE = ENTITY_RE

BLOCK_TAGS = {
    "p", "div", "br", "td", "th", "tr", "li", "h1", "h2", "h3", "h4", "h5",
    "h6", "table", "thead", "tbody", "ul", "ol", "section", "body",
}
SKIP_TAGS = {"head", "script", "style", "ix:header"}
VOID_TAGS = {
    "br", "img", "meta", "link", "hr", "input", "col", "base", "area",
}
_TAG_NAME_RE = re.compile(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9:._-]*)")
_STYLE_RE = re.compile(r"style\s*=\s*(\"[^\"]*\"|'[^']*')", re.I)

ABBREVS = sorted(
    [
        "Inc.", "Corp.", "Co.", "Ltd.", "No.", "Nos.", "U.S.", "U.K.", "e.g.",
        "i.e.", "Mr.", "Ms.", "Dr.", "St.", "vs.", "Jan.", "Feb.", "Mar.",
        "Apr.", "Jun.", "Jul.", "Aug.", "Sep.", "Sept.", "Oct.", "Nov.",
        "Dec.", "S.A.", "N.V.", "L.P.",
    ],
    key=len,
    reverse=True,
)
_QUOTES = set('"\'“”‘’«„([{')


def sentence_boundaries(text: str) -> list:
    """Char positions just AFTER a sentence-final [.?!] (interior splits)."""
    boundaries = []
    length = len(text)
    for j, char in enumerate(text):
        if char not in ".?!":
            continue
        if j + 1 >= length or not text[j + 1].isspace():
            continue
        head = text[: j + 1]
        abbreviated = False
        for abbr in ABBREVS:
            if head.endswith(abbr):
                before = head[: -len(abbr)]
                if not before or not before[-1].isalnum():
                    abbreviated = True
                break
        if abbreviated:
            continue
        if (
            char == "."
            and j > 0
            and text[j - 1].isdigit()
            and text[j + 1].isdigit()
        ):
            continue
        m = j + 1
        while m < length and text[m].isspace():
            m += 1
        if m >= length:
            continue
        nxt = text[m]
        if nxt.isupper() or nxt.isdigit() or nxt in _QUOTES:
            boundaries.append(j + 1)
    return boundaries


class Sentence:
    __slots__ = ("bs", "be", "text", "block", "cb", "ce")

    def __init__(self, bs, be, text, block, cb, ce):
        self.bs = bs
        self.be = be
        self.text = text
        self.block = block
        self.cb = cb  # char index -> byte offset of char start
        self.ce = ce  # char index -> byte offset just past the char

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"Sentence({self.bs}, {self.be}, {self.text[:40]!r})"


class Segment:
    """Units, sentences, blocks, skipped ranges, cells and rows of one doc."""

    __slots__ = ("raw", "units", "sentences", "blocks", "skip_ranges",
                 "cells", "rows")

    def __init__(self, raw, units, sentences, blocks, skip_ranges, cells, rows):
        self.raw = raw
        self.units = units  # list of (text, bs, be, is_entity)
        self.sentences = sentences
        self.blocks = blocks  # list of [sentence_index, ...]
        self.skip_ranges = skip_ranges
        self.cells = cells
        self.rows = rows

    def sentence_containing(self, pos: int):
        for sent in self.sentences:
            if sent.bs <= pos < sent.be:
                return sent
        return None

    def _in_skip(self, pos: int) -> bool:
        return any(start <= pos < end for start, end in self.skip_ranges)


def _tag_name(tag_bytes: bytes) -> str:
    m = _TAG_NAME_RE.match(tag_bytes.decode("latin-1"))
    return m.group(1).lower() if m else ""


def _is_hidden_style(tag_bytes: bytes) -> bool:
    m = _STYLE_RE.search(tag_bytes.decode("latin-1"))
    if not m:
        return False
    return "display:none" in re.sub(r"\s+", "", m.group(1).lower())


def segment(raw: bytes) -> Segment:  # noqa: C901
    """Byte-exact segmentation per H3: units, sentences, blocks, skips."""
    units: list = []
    breaks: list = []
    skip_ranges: list = []
    cells: list = []
    rows: list = []
    stack: list = []  # (name, is_skip)
    aux: list = []  # open td/th/tr elements: (name, byte_start)
    skip_depth = 0
    skip_start = None
    run_start = None
    i = 0
    n = len(raw)

    def flush_run(end: int) -> None:
        nonlocal run_start
        if run_start is not None and end > run_start and skip_depth == 0:
            units.append(
                (raw[run_start:end].decode("latin-1"), run_start, end, False)
            )
        run_start = None

    while i < n:
        byte = raw[i]
        if byte == 0x3C:  # '<'
            m = TAG_AT_RE.match(raw, i)
            if m:
                flush_run(i)
                tag = m.group(0)
                name = _tag_name(tag)
                closing = tag[1:2] == b"/"
                self_closing = tag.endswith(b"/>")
                if not closing:
                    hidden = _is_hidden_style(tag)
                    will_skip = (
                        name in SKIP_TAGS or hidden
                    )
                    if skip_depth == 0 and will_skip:
                        skip_start = m.start()
                    if will_skip and not self_closing and name not in VOID_TAGS:
                        skip_depth += 1
                        stack.append((name, True))
                    elif not self_closing and name not in VOID_TAGS:
                        stack.append((name, False))
                    if name in ("td", "th", "tr"):
                        aux.append((name, m.start()))
                else:
                    close_name = name
                    # pop through the matching open tag
                    idx = None
                    for k in range(len(stack) - 1, -1, -1):
                        if stack[k][0] == close_name:
                            idx = k
                            break
                    if idx is not None:
                        for k in range(len(stack) - 1, idx - 1, -1):
                            _name, was_skip = stack.pop()
                            if was_skip:
                                skip_depth -= 1
                                if skip_depth == 0 and skip_start is not None:
                                    skip_ranges.append((skip_start, m.end()))
                                    skip_start = None
                    if close_name in ("td", "th", "tr"):
                        for k in range(len(aux) - 1, -1, -1):
                            if aux[k][0] == close_name:
                                start = aux[k][1]
                                del aux[k:]
                                (
                                    rows if close_name == "tr" else cells
                                ).append((start, m.end()))
                                break
                if name in BLOCK_TAGS:
                    breaks.append(len(units))
                i = m.end()
                continue
        m = ENTITY_AT_RE.match(raw, i)
        if m:
            flush_run(i)
            if skip_depth == 0:
                decoded = html.unescape(m.group(0).decode("latin-1"))
                if decoded == "\xa0" or decoded.lower() == "&nbsp;":
                    decoded = " "
                units.append((decoded, i, m.end(), True))
            i = m.end()
            continue
        if run_start is None:
            run_start = i
        i += 1
    flush_run(n)

    # blocks: unit ranges between break marks
    marks = sorted({b for b in breaks})
    block_ranges = []
    prev = 0
    for mark in marks:
        if mark > prev:
            block_ranges.append((prev, mark))
            prev = mark
    if len(units) > prev:
        block_ranges.append((prev, len(units)))

    sentences: list = []
    blocks: list = []
    for block_no, (u0, u1) in enumerate(block_ranges):
        block_first_sentence = len(sentences)
        block_units = units[u0:u1]
        if not block_units:
            continue
        text_parts = [u[0] for u in block_units]
        block_text = "".join(text_parts)
        # char -> (unit_idx, is_entity_unit); plus per-char byte offsets.
        # Plain-run units decode latin-1, so one char == exactly one byte.
        char_map = []
        cb = []
        ce = []
        for ui, (_t, _bs, _be, is_entity) in enumerate(block_units):
            for k in range(len(_t)):
                char_map.append((ui, is_entity))
                if is_entity:
                    cb.append(_bs)
                    ce.append(_be)
                else:
                    cb.append(_bs + k)
                    ce.append(_bs + k + 1)
        cuts = [0]
        for b in sentence_boundaries(block_text):
            left = char_map[b - 1]
            right = char_map[b]
            # never split inside an atomic entity unit
            if left[0] == right[0] and left[1]:
                continue
            cuts.append(b)
        cuts.append(len(block_text))
        for s, e in zip(cuts, cuts[1:]):
            if e <= s:
                continue
            if char_map[s][1] and s > 0 and char_map[s - 1][0] == char_map[s][0]:
                continue  # unreachable (atomic), kept for safety
            sentences.append(
                Sentence(
                    cb[s], ce[e - 1], block_text[s:e], block_no,
                    cb[s:e], ce[s:e],
                )
            )
        if len(sentences) > block_first_sentence:
            blocks.append(
                list(range(block_first_sentence, len(sentences)))
            )
    return Segment(raw, units, sentences, blocks, skip_ranges, cells, rows)


# --- iXBRL facts and contexts (H4) ----------------------------------------------

_FACT_OPEN_RE = re.compile(rb"<ix:nonFraction\b[^>]*>", re.I)
_FACT_CLOSE_RE = re.compile(rb"</ix:nonFraction\s*>", re.I)
_ATTR_RE = re.compile(
    rb"([a-zA-Z:._-]+)\s*=\s*(\"[^\"]*\"|'[^']*')"
)
_CONTEXT_OPEN_RE = re.compile(rb"<((?:xbrli:)?)context\b[^>]*>", re.I)
_CONTEXT_CLOSE_RE = re.compile(rb"</(?:xbrli:)?context\s*>", re.I)
_PERIOD_PARTS = ("startDate", "endDate", "instant")
_MEMBER_RES = (
    re.compile(
        rb"<[a-zA-Z0-9]*:?explicitMember\b[^>]*dimension=\"([^\"]+)\"[^>]*>"
        rb"(.*?)</[a-zA-Z0-9]*:?explicitMember\s*>",
        re.S | re.I,
    ),
    re.compile(
        rb"<[a-zA-Z0-9]*:?typedMember\b[^>]*dimension=\"([^\"]+)\"[^>]*>"
        rb"(.*?)</[a-zA-Z0-9]*:?typedMember\s*>",
        re.S | re.I,
    ),
)


def _attrs(tag_bytes: bytes) -> dict:
    out = {}
    for name, value in _ATTR_RE.findall(tag_bytes):
        key = name.decode("latin-1").lower()
        out[key] = value[1:-1].decode("latin-1")
    return out


def find_facts(raw: bytes) -> list:
    """Every <ix:nonFraction> element with its parsed attributes (H4)."""
    facts = []
    pos = 0
    while True:
        opened = _FACT_OPEN_RE.search(raw, pos)
        if not opened:
            break
        closed = _FACT_CLOSE_RE.search(raw, opened.end())
        if not closed:
            pos = opened.end()
            continue
        attrs = _attrs(opened.group(0))
        inner = raw[opened.end() : closed.start()]
        value = re.sub(rb"<[^>]+>", b"", inner).decode("utf-8", "replace")
        facts.append(
            {
                "concept": attrs.get("name"),
                "context_ref": attrs.get("contextref"),
                "fact_id": attrs.get("id"),
                "decimals": attrs.get("decimals"),
                "scale": attrs.get("scale"),
                "format": attrs.get("format"),
                "sign": attrs.get("sign"),
                "raw_value": html.unescape(value).strip(),
                "element_bs": opened.start(),
                "element_be": closed.end(),
                "content_bs": opened.end(),
            }
        )
        pos = closed.end()
    return facts


def find_contexts(raw: bytes, counters: dict) -> dict:
    """context_ref -> {byte_start, byte_end, raw, period, members} (H4)."""
    contexts = {}
    pos = 0
    while True:
        opened = _CONTEXT_OPEN_RE.search(raw, pos)
        if not opened:
            break
        closed = _CONTEXT_CLOSE_RE.search(raw, opened.end())
        if not closed:
            break
        attrs = _attrs(opened.group(0))
        ref = attrs.get("id")
        start, end = opened.start(), closed.end()
        chunk = raw[start:end]
        if ref is not None:
            if len(chunk) <= MAX_SPAN_BYTES:
                period = {}
                for part in _PERIOD_PARTS:
                    m = re.search(
                        (
                            rb"<(?:xbrli:)?"
                            + part.encode("ascii")
                            + rb"\b[^>]*>(.*?)</(?:xbrli:)?"
                            + part.encode("ascii")
                            + rb"\s*>"
                        ),
                        chunk,
                        re.S | re.I,
                    )
                    if m:
                        period[part] = m.group(1).decode("latin-1").strip()
                members = []
                for member_re in _MEMBER_RES:
                    for dim, value in member_re.findall(chunk):
                        text = re.sub(rb"<[^>]+>", b"", value)
                        members.append(
                            {
                                "dimension": dim.decode("latin-1"),
                                "member": html.unescape(
                                    text.decode("utf-8", "replace")
                                ).strip(),
                            }
                        )
                members.sort(key=lambda m: (m["dimension"], m["member"]))
                try:
                    raw_text = chunk.decode("utf-8")
                except UnicodeDecodeError:
                    raw_text = None
                if raw_text is not None:
                    contexts[ref] = {
                        "context_ref": ref,
                        "byte_start": start,
                        "byte_end": end,
                        "raw": raw_text,
                        "period": (
                            {"start": period["startDate"],
                             "end": period["endDate"]}
                            if "startDate" in period
                            else {"instant": period.get("instant")}
                            if "instant" in period
                            else None
                        ),
                        "members": members,
                    }
            else:
                counters["xbrl_context_too_large"] += 1
        pos = closed.end()
    return contexts


def has_customer_axis(context: dict) -> bool:
    return any(
        member["dimension"].endswith("MajorCustomersAxis")
        for member in (context or {}).get("members") or []
    )


def _enclosing_cells(segment: Segment, pos: int):
    """(innermost td/th range containing pos, tr range containing pos)."""
    cell = None
    row = None
    for start, end in segment.cells:
        if start <= pos < end:
            cell = (start, end)
            break
    for start, end in segment.rows:
        if start <= pos < end:
            row = (start, end)
            break
    return cell, row


def _row_cells_span(segment: Segment, row, fact_cell_end):
    """[first non-empty cell's first text char, fact cell's last text char)."""
    units = [
        u
        for u in segment.units
        if row[0] <= u[1] and u[2] <= row[1] and u[0].strip()
    ]
    if not units:
        return None
    last = units[0][2]
    for u in units:
        if u[1] < fact_cell_end:
            last = u[2]
    return units[0][1], last


# --- cues (H5) -------------------------------------------------------------------

CUE_PATTERNS = (
    (
        "pct_of_revenue",
        re.compile(
            r"accounted for (approximately |about |more than |less than )?"
            r"\d+(\.\d+)?\s?%"
            r"|\d+(\.\d+)?\s?% of (our |its |the company's |total |net |"
            r"consolidated )*(net )?(revenues?|sales|net sales|purchases|"
            r"cost of (revenue|sales))",
            re.I,
        ),
    ),
    (
        "major_customer",
        re.compile(
            r"(largest|significant|major|principal|key|top (five|ten|\d+)) "
            r"customers?",
            re.I,
        ),
    ),
    ("sole_source", re.compile(r"(sole|single|limited)[- ]sources?(d)?", re.I)),
    ("foundry", re.compile(r"foundr(y|ies)", re.I)),
    ("contract_mfg", re.compile(r"contract manufactur\w*", re.I)),
    ("licensing", re.compile(r"licens(e|es|ed|ing|or|ors|ee|ees)\b", re.I)),
    ("distributor", re.compile(r"distributors?\b", re.I)),
    (
        "stream",
        re.compile(
            r"stream(ing)? (agreement|interest|arrangement|transaction)s?", re.I
        ),
    ),
    ("offtake", re.compile(r"off-?take", re.I)),
    (
        "supply_agmt",
        re.compile(
            r"(long-term )?(supply|purchase|wafer supply|capacity) "
            r"(agreement|commitment|arrangement)s?",
            re.I,
        ),
    ),
    ("take_or_pay", re.compile(r"take-or-pay", re.I)),
)

_ORG_SUFFIX_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.,'-]*(?:\s+[A-Z][A-Za-z0-9&.,'-]*)*)\s+"
    r"(Inc|Incorporated|Corporation|Corp|Company|Co|Ltd|Limited|LLC|L\.P\.|"
    r"plc|PLC|N\.V\.|S\.A\.|AG|SE|GmbH|K\.K\.)\b"
)
_ANON_RE = re.compile(
    r"\b(Customer|Distributor|Supplier|Licensee|Client) [A-Z]\b"
)


def _cue_matches(text: str) -> list:
    return sorted({name for name, pattern in CUE_PATTERNS if pattern.search(text)})


def _norm_index(text: str):
    """(norm_text, norm_char -> original_char_index)."""
    out = []
    index = []
    pending_space = False
    for i, char in enumerate(text.lower()):
        if ("a" <= char <= "z") or ("0" <= char <= "9"):
            if pending_space and out:
                out.append(" ")
                index.append(-1)
            pending_space = False
            out.append(char)
            index.append(i)
        else:
            pending_space = True
    while index and index[-1] == -1:
        out.pop()
        index.pop()
    return "".join(out), index


def _hint_matches(sentence_text: str, hints) -> list:
    norm, index = _norm_index(sentence_text)
    matched = []
    for hint in sorted(hints):
        pattern = re.compile(r"\b" + re.escape(hint) + r"\b")
        for m in pattern.finditer(norm):
            origin = index[m.start()]
            if origin >= 0 and sentence_text[origin].isupper():
                matched.append(hint)
                break
    return sorted(set(matched))


def _org_suffix_matches(sentence_text: str, own_names) -> list:
    for m in _ORG_SUFFIX_RE.finditer(sentence_text):
        name = norm_text(m.group(1))
        if not name:
            continue
        own = any(
            name in own_name or own_name in name
            for own_name in own_names
            if own_name
        )
        if not own:
            return [m.group(0).strip()]
    return []


def _anonymous_matches(sentence_text: str) -> list:
    m = _ANON_RE.search(sentence_text)
    return [m.group(0)] if m else []


def _best_rank(sentence_text: str, hints, own_names):
    """(rank, hints, qualifier) for one sentence, or (None, [], None).

    Rank 4 (percent-only) requires the pct_of_revenue cue itself; a sentence
    with no qualifier at all does not qualify.
    """
    matched_hints = _hint_matches(sentence_text, hints)
    if matched_hints:
        return 1, matched_hints, "hint"
    if _org_suffix_matches(sentence_text, own_names):
        return 2, [], "org_suffix"
    if _anonymous_matches(sentence_text):
        return 3, [], "anonymous"
    if CUE_PATTERNS[0][1].search(sentence_text):
        return 4, [], "percent_only"
    return None, [], None


# --- span assembly (H3) -----------------------------------------------------------


def _span_from(sentences, index):
    """Try the H3 choice order for sentence `index`; (bytes-decoder, kind)."""
    sent = sentences[index]
    options = []
    if index - 1 >= 0 and sentences[index - 1].block == sent.block:
        if index + 1 < len(sentences) and sentences[index + 1].block == sent.block:
            options.append(
                (
                    sentences[index - 1].bs,
                    sentences[index + 1].be,
                    "sentence_pm1",
                )
            )
        options.append(
            (sentences[index - 1].bs, sent.be, "sentence_m1")
        )
    if index + 1 < len(sentences) and sentences[index + 1].block == sent.block:
        options.append((sent.bs, sentences[index + 1].be, "sentence_p1"))
    options.append((sent.bs, sent.be, "sentence"))
    return options


def _clause_span(sent, matched_ranges):
    """The comma/semicolon-delimited clause window around the matched tokens."""
    text = sent.text
    earliest = min(r[0] for r in matched_ranges)
    latest = max(r[1] for r in matched_ranges)
    start = 0
    for j in range(earliest - 1, -1, -1):
        if text[j] in ",;:":
            start = j + 1
            while start < len(text) and text[start].isspace():
                start += 1
            break
    end = len(text)
    for j in range(latest, len(text)):
        if text[j] in ",;.":
            end = j + 1
            break
    if start >= end:
        return None
    return sent.cb[start], sent.ce[end - 1]


def _sentence_match_ranges(sentence_text: str, hints):
    """(start, end) char ranges of cues + qualifiers inside one sentence."""
    ranges = []
    for _name, pattern in CUE_PATTERNS:
        for m in pattern.finditer(sentence_text):
            ranges.append(m.span())
    norm, index = _norm_index(sentence_text)
    for hint in hints:
        for m in re.finditer(r"\b" + re.escape(hint) + r"\b", norm):
            origin = index[m.start()]
            if origin >= 0:
                ranges.append((origin, origin + (m.end() - m.start())))
    for m in _ORG_SUFFIX_RE.finditer(sentence_text):
        ranges.append(m.span())
    for m in _ANON_RE.finditer(sentence_text):
        ranges.append(m.span())
    return ranges


def expand_sentence(segment: Segment, sentences: list, index: int,
                    counters: dict, hint_set=frozenset()):
    """(byte_start, byte_end, span_kind) for one sentence, or (None, None, why)."""
    sent = sentences[index]
    for bs, be, kind in _span_from(sentences, index):
        if be - bs <= MAX_SPAN_BYTES:
            try:
                segment.raw[bs:be].decode("utf-8")
            except UnicodeDecodeError:
                counters["span_not_utf8"] += 1
                return None, None, "span_not_utf8"
            return bs, be, kind
    ranges = _sentence_match_ranges(sent.text, hint_set)
    if ranges:
        window = _clause_span(sent, ranges)
        if window is not None and window[1] - window[0] <= MAX_SPAN_BYTES:
            try:
                segment.raw[window[0] : window[1]].decode("utf-8")
            except UnicodeDecodeError:
                counters["span_not_utf8"] += 1
                return None, None, "span_not_utf8"
            return window[0], window[1], "clause"
    counters["span_too_large"] += 1
    return None, None, "span_too_large"


# --- candidate extraction ---------------------------------------------------------


def extract_document_candidates(  # noqa: C901
    raw: bytes,
    *,
    hints,
    own_hints,
    counters,
    amendment_primary: bool = False,
    max_per_doc: int = MAX_CANDIDATES_PER_DOCUMENT,
):
    """All candidates for one document (H3-H6): xbrl, cue, amendment_note."""
    seg = segment(raw)
    contexts = find_contexts(raw, counters)
    facts = find_facts(raw)
    own_names = own_hints if isinstance(own_hints, (set, frozenset)) else set()
    unit_starts = [u[1] for u in seg.units]
    sent_starts = [s.bs for s in seg.sentences]
    candidates: list = []

    def add(bs, be, span_kind, origin, rank, cues, hint_list, fact_list,
            context_refs):
        try:
            span_text = raw[bs:be].decode("utf-8")
        except UnicodeDecodeError:
            counters["span_not_utf8"] += 1
            return None
        cand = {
            "origin": origin,
            "rank": rank,
            "span_kind": span_kind,
            "cues": sorted(set(cues)),
            "hints": sorted(set(hint_list)),
            "xbrl_facts": fact_list,
            "span": {"byte_start": bs, "byte_end": be, "raw": span_text},
            "excerpt_contexts": [],
            "_anchor": (bs, be),
        }
        _merge_contexts(cand, context_refs, contexts)
        candidates.append(cand)
        return cand

    def first_char_unit(content_bs, element_be):
        """The first non-skipped unit overlapping [content_bs, element_be)."""
        idx = bisect_right(unit_starts, content_bs) - 1
        if idx < 0:
            idx = 0
        while idx < len(seg.units):
            unit = seg.units[idx]
            if unit[2] > content_bs:
                if not seg._in_skip(unit[1]) and unit[1] < element_be:
                    return unit
                if unit[1] >= element_be:
                    return None
            idx += 1
        return None

    # --- xbrl facts (rank 0) ---
    for fact in facts:
        if not fact["concept"] or not fact["concept"].endswith(
            "ConcentrationRiskPercentage1"
        ):
            continue  # H4: only concentration-percentage facts are harvested
        if seg._in_skip(fact["element_bs"]):
            counters["xbrl_fact_hidden"] += 1
            continue
        context = contexts.get(fact["context_ref"])
        if not has_customer_axis(context):
            counters["xbrl_fact_no_counterparty_axis"] += 1
            continue
        cell, row = _enclosing_cells(seg, fact["content_bs"])
        anchor = None
        if row is not None:
            if row[1] - row[0] <= MAX_SPAN_BYTES:
                anchor = (row[0], row[1], "table_row")
            elif cell is not None:
                window = _row_cells_span(seg, row, cell[1])
                if window is not None and (
                    window[1] - window[0] <= MAX_SPAN_BYTES
                ):
                    anchor = (window[0], window[1], "table_cells")
            if anchor is None:
                counters["xbrl_fact_unanchored"] += 1
                continue
        else:
            unit = first_char_unit(fact["content_bs"], fact["element_be"])
            if unit is None:
                counters["xbrl_fact_unanchored"] += 1
                continue
            sidx = bisect_right(sent_starts, unit[1]) - 1
            if sidx < 0 or not (
                seg.sentences[sidx].bs <= unit[1] < seg.sentences[sidx].be
            ):
                counters["xbrl_fact_unanchored"] += 1
                continue
            bs, be, kind = expand_sentence(
                seg, seg.sentences, sidx, counters
            )
            if bs is None:
                continue
            anchor = (bs, be, kind)
        fact_entry = {
            key: fact[key]
            for key in (
                "concept", "context_ref", "fact_id", "decimals", "scale",
                "format", "sign", "raw_value",
            )
        }
        fact_entry["fact_byte_start"] = fact["element_bs"]
        fact_entry["fact_byte_end"] = fact["element_be"]
        fact_entry["period"] = (context or {}).get("period")
        fact_entry["members"] = (context or {}).get("members") or []
        existing = None
        for cand in candidates:
            if cand["_anchor"] == anchor[:2]:
                existing = cand
                break
        if existing is not None:
            if all(
                f["fact_id"] != fact_entry["fact_id"]
                for f in existing["xbrl_facts"]
            ):
                existing["xbrl_facts"].append(fact_entry)
                existing["xbrl_facts"].sort(
                    key=lambda f: f["fact_byte_start"]
                )
            _merge_contexts(
                existing,
                {f["context_ref"] for f in existing["xbrl_facts"]},
                contexts,
            )
            continue
        anchor_text = raw[anchor[0] : anchor[1]].decode("utf-8", "replace")
        add(
            anchor[0], anchor[1], anchor[2], "xbrl", 0,
            _cue_matches(anchor_text), [], [fact_entry],
            {fact["context_ref"]},
        )

    # --- cue sentences (rank 1-4) ---
    for index, sent in enumerate(seg.sentences):
        cues = _cue_matches(sent.text)
        if not cues:
            continue
        rank, hint_list, _qual = _best_rank(sent.text, hints, own_names)
        if rank is None:
            continue
        bs, be, kind = expand_sentence(
            seg, seg.sentences, index, counters, set(hint_list)
        )
        if bs is None:
            continue
        existing = None
        for cand in candidates:
            if cand["_anchor"] == (bs, be):
                existing = cand
                break
        if existing is not None:
            existing["cues"] = sorted(set(existing["cues"]) | set(cues))
            existing["hints"] = sorted(set(existing["hints"]) | set(hint_list))
            continue
        add(bs, be, kind, "cue", rank, cues, hint_list, [], set())

    # --- amendment notes (H6, rank 0) ---
    if amendment_primary:
        total_chars = sum(len(u[0]) for u in seg.units)
        limit = max(1, int(total_chars * 0.25))
        pos = 0
        added = 0
        for index, sent in enumerate(seg.sentences):
            start_pos = pos
            pos += len(sent.text)
            if added >= 3 or start_pos >= limit:
                break
            if not re.search(
                r"(sole purpose|purpose of this Amendment|"
                r"is being filed (solely )?to|are filing this Amendment|"
                r"Amendment No\. \d+)",
                sent.text,
            ):
                continue
            bs, be, kind = expand_sentence(seg, seg.sentences, index, counters)
            if bs is None:
                continue
            if add(bs, be, kind, "amendment_note", 0,
                   _cue_matches(sent.text), [], [], set()) is not None:
                added += 1

    # filing-order key arrives later; here the per-document cap applies
    candidates.sort(
        key=lambda c: (c["rank"], c["span"]["byte_start"],
                       c["span"]["byte_end"])
    )
    kept = candidates[:max_per_doc]
    for _ in candidates[max_per_doc:]:
        counters["overflow_document"] += 1
    for cand in kept:
        cand.pop("_anchor", None)
    return kept


def _merge_contexts(cand, context_refs, contexts):
    seen = {c["context_ref"] for c in cand["excerpt_contexts"]}
    for ref in sorted(context_refs):
        context = contexts.get(ref)
        if context is None or ref in seen:
            continue
        cand["excerpt_contexts"].append(
            {
                "context_ref": context["context_ref"],
                "byte_start": context["byte_start"],
                "byte_end": context["byte_end"],
                "raw": context["raw"],
            }
        )
        seen.add(ref)
    cand["excerpt_contexts"].sort(key=lambda c: c["byte_start"])


def apply_filing_caps(cands, counters, max_filing: int =
                      MAX_CANDIDATES_PER_FILING):
    """Filing-level cap keeping lowest rank first, then document order."""
    ordered = sorted(
        cands,
        key=lambda c: (
            c["rank"],
            c.get("_doc_index", 0),
            c["span"]["byte_start"],
        ),
    )
    kept = ordered[:max_filing]
    for _ in ordered[max_filing:]:
        counters["overflow_filing"] += 1
    return kept


def segment_document(raw: bytes) -> Segment:
    """Cached segmentation helper (kept separate for testability)."""
    return segment(raw)

