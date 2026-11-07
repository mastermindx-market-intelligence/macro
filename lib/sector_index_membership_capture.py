"""Bound actual index membership to the existing breadth acquisition receipt.

This is a value contract. It neither reads files nor creates a basket, price
store, selector or publication owner. Original membership bytes and unknown
source revisions survive the handoff; observation is not historical availability.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import hashlib
import json
import math
import re

import pandas as pd

SCHEMA = "sector_index_membership.v1"
FAMILIES = ("nasdaq", "russell")
MAX_SOURCE_BYTES = 1024 * 1024
MAX_MEMBER_ROWS = 50_000
MAX_MEMBERS = 5_000
_SYMBOL = re.compile(r"[A-Z][A-Z0-9.-]{0,23}\Z")


def _fail(code):
    raise ValueError("index_membership_" + code)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def _nonfinite(value):
    _fail("nonfinite_json")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        _fail("nonfinite_json")
    return result


def decode_index_membership(capture, *, before):
    """Validate a closed adjunct and return its actual documents and bytes."""
    from lib.yahoo_generation_contract import _instant

    before = _instant(before)
    if (type(capture) is not dict or set(capture) != {"schema", "sources"}
            or capture["schema"] != SCHEMA or type(capture["sources"]) is not dict
            or set(capture["sources"]) != set(FAMILIES)):
        _fail("capture_invalid")
    documents, raw_sources, population, row_count = {}, {}, set(), 0
    for family in FAMILIES:
        item = capture["sources"][family]
        keys = {"origin", "source_revision", "captured_at", "byte_length", "sha256", "content"}
        if (type(item) is not dict or set(item) != keys
                or type(item["origin"]) is not str or not 0 < len(item["origin"]) <= 2048
                or any(ord(char) < 32 or ord(char) == 127 for char in item["origin"])
                or (item["source_revision"] is not None and
                    (type(item["source_revision"]) is not str
                     or re.fullmatch(r"[0-9a-f]{40}", item["source_revision"]) is None))
                or _instant(item["captured_at"]) > before
                or type(item["byte_length"]) is not int
                or not 0 < item["byte_length"] <= MAX_SOURCE_BYTES
                or type(item["sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
                or type(item["content"]) is not str
                or len(item["content"]) > MAX_SOURCE_BYTES):
            _fail("source_invalid")
        try:
            raw = item["content"].encode("utf-8", errors="strict")
        except UnicodeError:
            _fail("source_encoding")
        if len(raw) != item["byte_length"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            _fail("source_identity_mismatch")
        try:
            document = json.loads(raw, object_pairs_hook=_unique, parse_constant=_nonfinite,
                                  parse_float=_float)
        except (UnicodeError, json.JSONDecodeError, RecursionError):
            _fail("source_malformed")
        specs = document.get("amalgamations") if type(document) is dict else None
        if type(specs) is not dict or len(specs) > 512:
            _fail("document_invalid")
        for key, spec in specs.items():
            if (type(key) is not str or not 0 < len(key) <= 128 or type(spec) is not dict
                    or type(spec.get("members")) is not list or len(spec["members"]) > MAX_MEMBERS):
                _fail("specification_invalid")
            seen = set()
            for row in spec["members"]:
                ticker = row.get("ticker") if type(row) is dict else None
                if type(ticker) is not str or not _SYMBOL.fullmatch(ticker) or ticker in seen:
                    _fail("member_invalid")
                seen.add(ticker)
                population.add(ticker)
                row_count += 1
                if len(population) > MAX_MEMBERS or row_count > MAX_MEMBER_ROWS:
                    _fail("population_bound")
                for field in ("added", "removed"):
                    value = row.get(field)
                    if value is not None:
                        try:
                            if type(value) is not str or date.fromisoformat(value).isoformat() != value:
                                raise ValueError
                        except ValueError:
                            _fail("member_date_invalid")
                if row.get("added") and row.get("removed") and row["removed"] <= row["added"]:
                    _fail("member_interval_invalid")
        documents[family], raw_sources[family] = document, raw
    return documents, raw_sources


def capture_index_membership(sources: Mapping, *, before):
    """Seal the real bounded observations supplied by the existing file owner."""
    from lib.sector_auxiliary_capture import CapturedAuxiliarySource
    if not isinstance(sources, Mapping) or set(sources) != set(FAMILIES):
        _fail("observations_required")
    result = {"schema": SCHEMA, "sources": {}}
    for family in FAMILIES:
        item = sources[family]
        raw = getattr(item, "raw_bytes", None)
        if (not isinstance(item, CapturedAuxiliarySource) or item.outcome != "present" or type(raw) is not bytes
                or not 0 < len(raw) <= MAX_SOURCE_BYTES):
            _fail("present_observation_required")
        try:
            content = raw.decode("utf-8", errors="strict")
        except UnicodeError:
            _fail("source_encoding")
        result["sources"][family] = {
            "origin": item.origin, "source_revision": item.source_revision,
            "captured_at": item.captured_at.isoformat(), "byte_length": item.byte_length,
            "sha256": item.sha256, "content": content,
        }
    decode_index_membership(result, before=before)
    return result


def index_population(capture, *, primary, before):
    """Keep index eligibility separate from thematic basket populations."""
    from lib.closes_panel import population_observation

    documents, _ = decode_index_membership(capture, before=before)
    if not isinstance(primary, pd.DataFrame) or primary.empty:
        _fail("primary_required")
    requested, active, required_end, populations = set(), set(), {}, {}
    for family, document in documents.items():
        populations[family] = {}
        for key, spec in document["amalgamations"].items():
            for row in spec["members"]:
                ticker = row["ticker"]
                requested.add(ticker)
                eligible = primary.index
                if row.get("added"):
                    eligible = eligible[eligible >= pd.Timestamp(row["added"])]
                if row.get("removed"):
                    eligible = eligible[eligible < pd.Timestamp(row["removed"])]
                if len(eligible):
                    required_end[ticker] = max(required_end.get(ticker, eligible[-1]), eligible[-1])
            observed = population_observation(primary, spec["members"], primary.index[-1])
            populations[family][key] = observed["configured_members"]
            active.update(observed["configured_members"])
    return requested, active, required_end, populations
