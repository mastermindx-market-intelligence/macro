"""Closed, bounded byte codec for market memory persisted fit bundles.

This module is pure and closed: it converts bytes between an exact canonical
JSON wire form and an exact in-memory dict form. It performs no IO, owns no
paths, flags, callbacks or capability claims, and touches no remote, source
or permission state. Inner object semantics beyond the required ``schema``
marker belong to the owner and stay opaque here.

Wire object (exact keys; canonical UTF-8 JSON: sorted keys, compact
separators, ensure_ascii=False, allow_nan=False)::

    {
      "schema": "market_memory.persisted_fit_bundle.v1",
      "parameters": {"value": <object>, "sha256": "<64 lowercase hex>",
                     "bytes": <exact positive int>},
      "window":     {... same member shape ...},
      "selection":  {... same member shape ...},
      "constructed_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ"
    }

Bounds: whole wire <= MAX_BUNDLE_BYTES enforced before any parsing,
recursion depth <= MAX_DEPTH and tree nodes <= MAX_NODES across a decoded
tree. Overflow is refused with one fixed error text and no payload or path
leakage. Nothing is truncated, chunked or compressed, and no global
runtime, integer or decimal state is modified.

Requires Python 3.11+ and the standard library only.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date

__all__ = [
    "BundleError",
    "MAX_BUNDLE_BYTES",
    "MAX_DEPTH",
    "MAX_NODES",
    "WIRE_SCHEMA",
    "PARAMETERS_SCHEMA",
    "WINDOW_SCHEMA",
    "SELECTION_SCHEMA",
    "ERROR_INPUT",
    "ERROR_LIMIT",
    "ERROR_JSON",
    "ERROR_UTF8",
    "ERROR_CANONICAL",
    "ERROR_DUPLICATE",
    "ERROR_NONFINITE",
    "ERROR_CLOCK",
    "ERROR_WIRE",
    "ERROR_MEMBER",
    "ERROR_DIGEST",
    "ERROR_INNER_SCHEMA",
    "decode_bundle",
    "encode_bundle",
]

MAX_BUNDLE_BYTES = 1048576
MAX_DEPTH = 32
MAX_NODES = 100000

WIRE_SCHEMA = "market_memory.persisted_fit_bundle.v1"
PARAMETERS_SCHEMA = "market_memory.fitted_normalizer.v2"
WINDOW_SCHEMA = "market_memory.selected_training_inputs.v2"
SELECTION_SCHEMA = "research_factory.market_memory_e0_selected_control.v1"

_ROLE_SCHEMAS = (
    ("parameters", PARAMETERS_SCHEMA),
    ("window", WINDOW_SCHEMA),
    ("selection", SELECTION_SCHEMA),
)
_ROLE_SCHEMA_MAP = dict(_ROLE_SCHEMAS)

_ERROR_PREFIX = "market_memory.fit_bundle: "
ERROR_INPUT = _ERROR_PREFIX + "input has the wrong exact type"
ERROR_LIMIT = _ERROR_PREFIX + "bounded size, depth or node limit exceeded"
ERROR_JSON = _ERROR_PREFIX + "input is not a JSON document"
ERROR_UTF8 = _ERROR_PREFIX + "input is not valid UTF-8"
ERROR_CANONICAL = _ERROR_PREFIX + "input is not in canonical JSON form"
ERROR_DUPLICATE = _ERROR_PREFIX + "input contains a duplicate object key"
ERROR_NONFINITE = _ERROR_PREFIX + "input contains a nonfinite number"
ERROR_CLOCK = _ERROR_PREFIX + "constructed_at is not an exact UTC timestamp"
ERROR_WIRE = _ERROR_PREFIX + "wire object has unexpected keys or schema"
ERROR_MEMBER = _ERROR_PREFIX + "role member has unexpected keys or value types"
ERROR_DIGEST = _ERROR_PREFIX + "declared sha256 or byte size does not match"
ERROR_INNER_SCHEMA = _ERROR_PREFIX + "inner object schema does not match the role"

_WIRE_KEYS = frozenset(
    {"schema", "parameters", "window", "selection", "constructed_at"}
)
_MEMBER_KEYS = frozenset({"value", "sha256", "bytes"})
_HEX = frozenset("0123456789abcdef")

_NUMBER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?")
_CLOCK_RE = re.compile(
    r"\A([0-9]{4})-([0-9]{2})-([0-9]{2})"
    r"T([0-9]{2}):([0-9]{2}):([0-9]{2})\.([0-9]{6})Z\Z"
)

_SIMPLE_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}
_WS = " \t\n\r"


class BundleError(ValueError):
    """Raised for any rejected fit-bundle bytes, clock or shape.

    Messages are fixed per failure class and never embed payload, path or
    environment detail.
    """


# --------------------------------------------------------------------------
# bounded canonical JSON parsing
# --------------------------------------------------------------------------


class _Parser:
    """Strict JSON reader with node, depth and duplicate-key bounds.

    Cycles cannot exist in parsed text; the node and depth bounds give the
    same guarantee against adversarially wide or deep documents.
    """

    __slots__ = ("_nodes", "_pos", "_text")

    def __init__(self, text: str) -> None:
        self._text = text
        self._pos = 0
        self._nodes = 0

    def parse(self):
        value = self._value(1)
        self._skip_ws()
        if self._pos != len(self._text):
            raise BundleError(ERROR_JSON)
        return value

    # -- accounting ------------------------------------------------------

    def _count(self) -> None:
        if self._nodes >= MAX_NODES:
            raise BundleError(ERROR_LIMIT)
        self._nodes += 1

    def _skip_ws(self) -> None:
        text, pos, n = self._text, self._pos, len(self._text)
        while pos < n and text[pos] in _WS:
            pos += 1
        self._pos = pos

    def _peek(self) -> str:
        if self._pos >= len(self._text):
            raise BundleError(ERROR_JSON)
        return self._text[self._pos]

    # -- grammar ---------------------------------------------------------

    def _value(self, depth: int):
        if depth > MAX_DEPTH:
            raise BundleError(ERROR_LIMIT)
        self._count()
        self._skip_ws()
        ch = self._peek()
        if ch == "{":
            return self._object(depth)
        if ch == "[":
            return self._array(depth)
        if ch == '"':
            return self._string()
        if ch == "t":
            return self._literal("true", True)
        if ch == "f":
            return self._literal("false", False)
        if ch == "n":
            return self._literal("null", None)
        if ch == "N" and self._text.startswith("NaN", self._pos):
            raise BundleError(ERROR_NONFINITE)
        if ch == "I" and self._text.startswith("Infinity", self._pos):
            raise BundleError(ERROR_NONFINITE)
        if ch == "-" or "0" <= ch <= "9":
            return self._number()
        raise BundleError(ERROR_JSON)

    def _object(self, depth: int) -> dict:
        self._pos += 1
        obj: dict = {}
        self._skip_ws()
        if self._peek() == "}":
            self._pos += 1
            return obj
        while True:
            self._skip_ws()
            self._count()
            if self._peek() != '"':
                raise BundleError(ERROR_JSON)
            key = self._string()
            if key in obj:
                raise BundleError(ERROR_DUPLICATE)
            self._skip_ws()
            if self._peek() != ":":
                raise BundleError(ERROR_JSON)
            self._pos += 1
            obj[key] = self._value(depth + 1)
            self._skip_ws()
            ch = self._peek()
            if ch == ",":
                self._pos += 1
                continue
            if ch == "}":
                self._pos += 1
                return obj
            raise BundleError(ERROR_JSON)

    def _array(self, depth: int) -> list:
        self._pos += 1
        items: list = []
        self._skip_ws()
        if self._peek() == "]":
            self._pos += 1
            return items
        while True:
            items.append(self._value(depth + 1))
            self._skip_ws()
            ch = self._peek()
            if ch == ",":
                self._pos += 1
                continue
            if ch == "]":
                self._pos += 1
                return items
            raise BundleError(ERROR_JSON)

    def _string(self) -> str:
        text = self._text
        n = len(text)
        pos = self._pos + 1
        chunks: list = []
        start = pos
        while True:
            if pos >= n:
                raise BundleError(ERROR_JSON)
            ch = text[pos]
            if ch == '"':
                chunks.append(text[start:pos])
                self._pos = pos + 1
                return "".join(chunks)
            if ch == "\\":
                chunks.append(text[start:pos])
                pos = self._escape(pos + 1, chunks)
                start = pos
                continue
            if ch < " ":
                raise BundleError(ERROR_JSON)
            pos += 1

    def _escape(self, pos: int, chunks: list) -> int:
        text = self._text
        if pos >= len(text):
            raise BundleError(ERROR_JSON)
        ch = text[pos]
        simple = _SIMPLE_ESCAPES.get(ch)
        if simple is not None:
            chunks.append(simple)
            return pos + 1
        if ch != "u":
            raise BundleError(ERROR_JSON)
        code = self._hex4(pos + 1)
        if 0xD800 <= code <= 0xDBFF:
            if text[pos + 5 : pos + 7] != "\\u":
                raise BundleError(ERROR_JSON)
            low = self._hex4(pos + 7)
            if not 0xDC00 <= low <= 0xDFFF:
                raise BundleError(ERROR_JSON)
            chunks.append(chr(0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)))
            return pos + 11
        if 0xDC00 <= code <= 0xDFFF:
            raise BundleError(ERROR_JSON)
        chunks.append(chr(code))
        return pos + 5

    def _hex4(self, pos: int) -> int:
        chunk = self._text[pos : pos + 4]
        if len(chunk) != 4:
            raise BundleError(ERROR_JSON)
        try:
            return int(chunk, 16)
        except ValueError:
            raise BundleError(ERROR_JSON) from None

    def _number(self):
        match = _NUMBER_RE.match(self._text, self._pos)
        if match is None:
            if self._text.startswith("-Infinity", self._pos):
                raise BundleError(ERROR_NONFINITE)
            raise BundleError(ERROR_JSON)
        token = match.group(0)
        self._pos = match.end()
        if "." in token or "e" in token or "E" in token:
            value = float(token)
            if not math.isfinite(value):
                raise BundleError(ERROR_NONFINITE)
            return value
        try:
            return int(token)
        except ValueError:
            raise BundleError(ERROR_JSON) from None

    def _literal(self, token: str, value):
        if self._text.startswith(token, self._pos):
            self._pos += len(token)
            return value
        raise BundleError(ERROR_JSON)


def _dumps(value) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        raise BundleError(ERROR_JSON) from None


def _decode_utf8(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise BundleError(ERROR_UTF8) from None


def _parse_canonical_text(text: str):
    value = _Parser(text).parse()
    if _dumps(value) != text:
        raise BundleError(ERROR_CANONICAL)
    return value


# --------------------------------------------------------------------------
# shared validation
# --------------------------------------------------------------------------


def _require_bytes(value) -> None:
    if type(value) is not bytes:
        raise BundleError(ERROR_INPUT)


def _validate_clock(value):
    if type(value) is not str:
        raise BundleError(ERROR_CLOCK)
    match = _CLOCK_RE.match(value)
    if match is None:
        raise BundleError(ERROR_CLOCK)
    year, month, day, hour, minute, second = (
        int(match.group(index)) for index in range(1, 7)
    )
    try:
        date(year, month, day)
    except ValueError:
        raise BundleError(ERROR_CLOCK) from None
    if hour > 23 or minute > 59 or second > 59:
        raise BundleError(ERROR_CLOCK)
    return value


def _require_inner_schema(value, schema: str) -> None:
    if type(value) is not dict or value.get("schema") != schema:
        raise BundleError(ERROR_INNER_SCHEMA)


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------


def encode_bundle(
    parameters: bytes, window: bytes, selection: bytes, constructed_at: str
) -> bytes:
    """Encode three canonical inner bodies plus a clock into wire bytes.

    Each input body must already be exact, canonical UTF-8 JSON bytes whose
    object carries the schema required for its role; altered or noncanonical
    bodies are refused, never silently normalized. The returned wire is
    canonical and strictly bounded by MAX_BUNDLE_BYTES.
    """
    bodies: dict = {}
    values: dict = {}
    for name, raw in (
        ("parameters", parameters),
        ("window", window),
        ("selection", selection),
    ):
        _require_bytes(raw)
        if len(raw) == 0:
            raise BundleError(ERROR_INPUT)
        if len(raw) > MAX_BUNDLE_BYTES:
            raise BundleError(ERROR_LIMIT)
        value = _parse_canonical_text(_decode_utf8(raw))
        _require_inner_schema(value, _ROLE_SCHEMA_MAP[name])
        bodies[name] = raw
        values[name] = value
    clock = _validate_clock(constructed_at)
    wire: dict = {"schema": WIRE_SCHEMA, "constructed_at": clock}
    for name, _schema in _ROLE_SCHEMAS:
        raw = bodies[name]
        wire[name] = {
            "value": values[name],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    body = _dumps(wire).encode("utf-8")
    if len(body) > MAX_BUNDLE_BYTES:
        raise BundleError(ERROR_LIMIT)
    return body


def decode_bundle(body: bytes) -> dict:
    """Decode wire bytes into the exact four-key fit-bundle dict.

    The whole body is size-bounded before any parsing, then parsed as
    canonical JSON with duplicate, nonfinite, depth and node refusal. Each
    role member's declared sha256 and byte size are verified against the
    canonical form of its parsed value before anything is returned. The
    returned members are the canonical original byte bodies.
    """
    _require_bytes(body)
    if len(body) > MAX_BUNDLE_BYTES:
        raise BundleError(ERROR_LIMIT)
    if len(body) == 0:
        raise BundleError(ERROR_JSON)
    wire = _parse_canonical_text(_decode_utf8(body))
    if (
        type(wire) is not dict
        or set(wire.keys()) != _WIRE_KEYS
        or wire["schema"] != WIRE_SCHEMA
    ):
        raise BundleError(ERROR_WIRE)
    decoded: dict = {}
    for name, schema in _ROLE_SCHEMAS:
        decoded[name] = _decode_member(wire[name], schema)
    clock = _validate_clock(wire["constructed_at"])
    decoded["constructed_at"] = clock
    return decoded


def _decode_member(member, schema: str) -> bytes:
    if type(member) is not dict or set(member.keys()) != _MEMBER_KEYS:
        raise BundleError(ERROR_MEMBER)
    size = member["bytes"]
    if type(size) is not int or size <= 0:
        raise BundleError(ERROR_MEMBER)
    digest = member["sha256"]
    if type(digest) is not str or len(digest) != 64 or not _HEX.issuperset(digest):
        raise BundleError(ERROR_MEMBER)
    value = member["value"]
    if type(value) is not dict:
        raise BundleError(ERROR_MEMBER)
    if value.get("schema") != schema:
        raise BundleError(ERROR_INNER_SCHEMA)
    inner = _dumps(value).encode("utf-8")
    if len(inner) != size or hashlib.sha256(inner).hexdigest() != digest:
        raise BundleError(ERROR_DIGEST)
    return inner
