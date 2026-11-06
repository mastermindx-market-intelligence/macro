"""Opt-in structural eligibility over unchanged PDF extraction bytes.

The trusted extraction caller supplies the record and Poppler bbox-layout XML.
Hashes prove consistency, not that arbitrary XML originated from that PDF.
Never accept a model/user supplied scope as a source-origin attestation. This
module performs no I/O and does not change quotations or establish entailment.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from . import fulltext

SCHEMA = "research_vault.pdf_block_scope.v1"
MAX_XML_BYTES = 16 * 1024 * 1024
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_BLOCKS = 10000
MAX_TOKENS = 500000
MAX_UNITS = 2048
MAX_COMPARISONS = 20000000
# Independent token-alignment and per-pass byte-verification bounds. The two
# selector catalog passes still reserve at most the existing128MiB allowance.
# Per-dimension caps above are joint limits, not a promise of every product.
MAX_ELIGIBILITY_COMPARISONS = 64 * 1024 * 1024
_NS = "{http://www.w3.org/1999/xhtml}"
_SHA = re.compile(r"[a-f0-9]{64}\Z")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


class _BoundedTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.nodes = 0

    def start(self, tag, attrs):
        self.nodes += 1
        if self.nodes > 1000000:
            raise ValueError("layout XML node bound exceeded")
        return super().start(tag, attrs)


def build_layout_scope(record, layout_xml: bytes, *, expected_layout_sha256: str):
    """Align complete PDF blocks uniquely to exact whitespace tokens per page.

    Comparisons are charged before each candidate comparison. The rarest word
    anchors a block; repeated/ambiguous occurrences never authorize a span.
    Offsets address original UTF-8 bytes, including form-feed page separators.
    """
    if type(record) is not dict or type(record.get("byte_count")) is not int or record["byte_count"] > MAX_BODY_BYTES:
        raise ValueError("layout source body bound exceeded")
    if type(record.get("text")) is not str or len(record["text"]) > MAX_BODY_BYTES:
        raise ValueError("layout source body bound exceeded")
    raw = fulltext._validate_extracted_text(record)
    if len(raw) > MAX_BODY_BYTES or not raw:
        raise ValueError("layout source body bound exceeded")
    if record["extractor_name"] != "pdftotext" or record["extractor_version"] != fulltext.EXTRACTOR_VERSION_READING_ORDER_V2:
        raise ValueError("layout requires the explicit reading-order v2 source")
    if (type(layout_xml) is not bytes or len(layout_xml) > MAX_XML_BYTES
            or type(expected_layout_sha256) is not str or not _SHA.fullmatch(expected_layout_sha256)
            or _sha(layout_xml) != expected_layout_sha256):
        raise ValueError("layout XML identity or bound invalid")
    xml = layout_xml.decode("utf-8")
    # Poppler's external XHTML declaration is inert under ElementTree. Internal
    # subsets/entities are refused before parsing, including unused declarations.
    if re.search(r"<!ENTITY", xml, re.I):
        raise ValueError("layout entities refused")
    for declaration in re.findall(r"<!DOCTYPE[^>]*>", xml, re.I):
        if "[" in declaration or "]" in declaration:
            raise ValueError("layout internal DTD refused")
    try:
        tree = ET.fromstring(xml, parser=ET.XMLParser(target=_BoundedTree()))
    except ET.ParseError as exc:
        raise ValueError("layout XML malformed") from exc
    if tree.tag != _NS + "html":
        raise ValueError("layout XML root invalid")
    pages = list(tree.iter(_NS + "page"))
    boundaries = record["page_boundaries"]
    if len(pages) != len(boundaries) or record["page_count"] != len(pages):
        raise ValueError("layout page count mismatch")
    blocks, unresolved, work, token_count, block_count = [], 0, 0, 0, 0
    for page_number, (page, boundary) in enumerate(zip(pages, boundaries), 1):
        page_raw = raw[boundary["start_byte"]:boundary["end_byte"]]
        text = page_raw.decode("utf-8")
        matches = list(re.finditer(r"\S+", text))
        token_count += len(matches)
        if token_count > MAX_TOKENS:
            raise ValueError("layout token bound exceeded")
        tokens = [m.group() for m in matches]
        positions = defaultdict(list)
        # One UTF-8 prefix walk avoids quadratic encoding of every prefix.
        offsets, cursor, previous = [], 0, 0
        for index, match in enumerate(matches):
            cursor += len(text[previous:match.start()].encode("utf-8"))
            start = cursor
            cursor += len(match.group().encode("utf-8"))
            offsets.append((boundary["start_byte"] + start, boundary["start_byte"] + cursor))
            previous = match.end()
            positions[match.group()].append(index)
        for block_number, block in enumerate(page.iter(_NS + "block")):
            block_count += 1
            if block_count > MAX_BLOCKS:
                raise ValueError("layout block bound exceeded")
            words = []
            for word in block.iter(_NS + "word"):
                for token in (word.text or "").split():
                    token_count += 1
                    if token_count > MAX_TOKENS:
                        raise ValueError("layout token bound exceeded")
                    words.append(token)
            found = []
            if words:
                anchor = min(range(len(words)), key=lambda i: len(positions.get(words[i], ())))
                for position in positions.get(words[anchor], ()):
                    start = position - anchor
                    if start < 0 or start + len(words) > len(tokens):
                        continue
                    work += len(words)
                    if work > MAX_COMPARISONS:
                        raise ValueError("layout comparison budget exceeded")
                    if tokens[start:start + len(words)] == words:
                        found.append((offsets[start][0], offsets[start + len(words) - 1][1]))
                        if len(found) > 1:
                            break
            if len(found) == 1:
                a, b = found[0]
                blocks.append({"page": page_number, "block": block_number, "start_byte": a, "end_byte": b})
            else:
                unresolved += 1
    core = {"schema": SCHEMA, "report_id": record["report_id"],
            "source_pdf_sha256": record["source_pdf_sha256"],
            "content_sha256": record["extracted_text_sha256"],
            "extractor_version": record["extractor_version"],
            "layout_sha256": expected_layout_sha256, "blocks": blocks,
            "unresolved_blocks": unresolved, "comparison_work": work,
            "coverage": "PARTIAL_SOURCE_CONTEXT"}
    return {**core, "scope_sha256": _sha(_canonical(core)), "layout_xml": xml}


def eligible_evidence_ids(record, catalog, scope):
    """Recompute scope from retained XML; never trust caller-provided offsets."""
    if (type(scope) is not dict or type(scope.get("layout_xml")) is not str
            or len(scope["layout_xml"]) > MAX_XML_BYTES):
        raise ValueError("layout scope invalid")
    rebuilt = build_layout_scope(record, scope["layout_xml"].encode("utf-8"), expected_layout_sha256=scope.get("layout_sha256"))
    if scope != rebuilt:
        raise ValueError("layout scope derived spans or binding changed")
    if (type(catalog) is not dict or type(catalog.get("document")) is not dict
            or catalog["document"].get("id") != record["report_id"]
            or catalog["document"].get("content_sha256") != record["extracted_text_sha256"]
            or type(catalog.get("units")) is not list or len(catalog["units"]) > MAX_UNITS):
        raise ValueError("layout catalog source mismatch")
    raw = record["text"].encode("utf-8")
    allowed, seen, work = [], set(), 0
    for unit in catalog["units"]:
        if (type(unit) is not dict or set(unit) != {"evidence_id", "text"}
                or type(unit["evidence_id"]) is not str or unit["evidence_id"] in seen
                or type(unit["text"]) is not str or not unit["text"] or len(unit["text"]) > 1600):
            raise ValueError("layout catalog unit invalid")
        seen.add(unit["evidence_id"])
        needle = unit["text"].encode("utf-8")
        work += len(raw) + len(rebuilt["blocks"])
        if work > MAX_ELIGIBILITY_COMPARISONS:
            raise ValueError("layout eligibility budget exceeded")
        start = raw.find(needle)
        if start < 0 or raw.find(needle, start + 1) >= 0:
            continue
        end = start + len(needle)
        containing = [b for b in rebuilt["blocks"] if b["start_byte"] <= start and end <= b["end_byte"]]
        if len(containing) == 1:
            allowed.append(unit["evidence_id"])
    binding = {key: rebuilt[key] for key in ("schema", "report_id", "source_pdf_sha256", "content_sha256", "extractor_version", "layout_sha256", "scope_sha256")}
    return {"allowed_evidence_ids": allowed, "omitted_layout": len(catalog["units"]) - len(allowed), "binding": binding}
