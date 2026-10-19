"""Focused tests for the closed, bounded fit-bundle byte codec.

Only codec behavior is exercised: roundtrip, canonical identity, shape,
digest/size, clock, bound and type refusals. No source, auth or domain
semantics are tested; inner objects are minimal synthetic schema markers,
never real fits. The module under test is imported straight from this
artifact directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest

_ARTIFACT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ARTIFACT_DIR not in sys.path:
    sys.path.insert(0, _ARTIFACT_DIR)

from engine.research_factory import market_memory_fit_bundle as mmb

CLOCK = "2026-10-19T12:34:56.789012Z"

P_BODY = b'{"schema":"market_memory.fitted_normalizer.v2"}'
W_BODY = b'{"schema":"market_memory.selected_training_inputs.v2"}'
S_BODY = b'{"schema":"research_factory.market_memory_e0_selected_control.v1"}'


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def canonical(value) -> bytes:
    """The module's canonical JSON form, built independently."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def role_body(inner: bytes) -> str:
    """Canonical role-member text wrapping an exact inner body."""
    member = {
        "bytes": len(inner),
        "sha256": hashlib.sha256(inner).hexdigest(),
        "value": json.loads(inner.decode("utf-8")),
    }
    return canonical(member).decode("utf-8")


def role_body_raw(inner: bytes) -> str:
    """Role-member text embedding inner bytes verbatim (may be malformed)."""
    return (
        '{"bytes":%d,"sha256":"%s","value":%s}'
        % (
            len(inner),
            hashlib.sha256(inner).hexdigest(),
            inner.decode("utf-8"),
        )
    )


def raw_wire(
    parameters: str | None = None,
    window: str | None = None,
    selection: str | None = None,
    clock: str = CLOCK,
) -> bytes:
    """Canonical wire text built from raw role texts, keys in sorted order."""
    parts = {
        "parameters": parameters if parameters is not None else role_body(P_BODY),
        "window": window if window is not None else role_body(W_BODY),
        "selection": selection if selection is not None else role_body(S_BODY),
    }
    return (
        '{"constructed_at":"%s","parameters":%s,"schema":"%s","selection":%s,"window":%s}'
        % (clock, parts["parameters"], mmb.WIRE_SCHEMA, parts["selection"], parts["window"])
    ).encode("utf-8")


def wire_bytes(
    parameters: bytes | None = None,
    window: bytes | None = None,
    selection: bytes | None = None,
    clock: str = CLOCK,
) -> bytes:
    """Canonical wire bytes from inner bodies (each may be None = default)."""
    return raw_wire(
        parameters=None if parameters is None else role_body(parameters),
        window=None if window is None else role_body(window),
        selection=None if selection is None else role_body(selection),
        clock=clock,
    )


def rejects(wire, message: str | None = None):
    with pytest.raises(mmb.BundleError) as excinfo:
        mmb.decode_bundle(wire)
    if message is not None:
        assert str(excinfo.value) == message
    return excinfo


def deep_inner(levels: int) -> bytes:
    """Canonical inner body with `levels` nested arrays of opaque padding."""
    return (
        '{"deep":' + "[" * levels + "0" + "]" * levels + ',"schema":"%s"}'
        % mmb.PARAMETERS_SCHEMA
    ).encode("utf-8")


def padded_inner(pad: int, schema: str = mmb.PARAMETERS_SCHEMA) -> bytes:
    """Canonical inner body with an opaque ASCII padding string."""
    return canonical({"pad": "p" * pad, "schema": schema})


# ---------------------------------------------------------------------------
# surface and positive behavior
# ---------------------------------------------------------------------------


def test_module_surface():
    assert mmb.MAX_BUNDLE_BYTES == 1048576
    assert mmb.MAX_DEPTH == 32
    assert mmb.MAX_NODES == 100000
    assert issubclass(mmb.BundleError, ValueError)


def test_roundtrip_minimal():
    encoded = mmb.encode_bundle(P_BODY, W_BODY, S_BODY, CLOCK)
    decoded = mmb.decode_bundle(encoded)
    assert set(decoded) == {"parameters", "window", "selection", "constructed_at"}
    assert decoded["parameters"] == P_BODY
    assert decoded["window"] == W_BODY
    assert decoded["selection"] == S_BODY
    assert decoded["constructed_at"] == CLOCK
    for name in ("parameters", "window", "selection"):
        assert type(decoded[name]) is bytes
    assert type(decoded["constructed_at"]) is str


def test_wire_shape_is_exact():
    encoded = mmb.encode_bundle(P_BODY, W_BODY, S_BODY, CLOCK)
    wire = json.loads(encoded)
    assert set(wire) == {"schema", "parameters", "window", "selection", "constructed_at"}
    assert wire["schema"] == mmb.WIRE_SCHEMA
    assert wire["constructed_at"] == CLOCK
    for name, body in (
        ("parameters", P_BODY),
        ("window", W_BODY),
        ("selection", S_BODY),
    ):
        member = wire[name]
        assert set(member) == {"value", "sha256", "bytes"}
        assert member["sha256"] == hashlib.sha256(body).hexdigest()
        assert type(member["bytes"]) is int
        assert member["bytes"] == len(body) > 0
        assert member["value"] == json.loads(body)
    assert encoded == canonical(wire)


def test_encode_is_stable_and_roundtrip_idempotent():
    first = mmb.encode_bundle(P_BODY, W_BODY, S_BODY, CLOCK)
    second = mmb.encode_bundle(P_BODY, W_BODY, S_BODY, CLOCK)
    assert first == second
    decoded = mmb.decode_bundle(first)
    again = mmb.encode_bundle(
        decoded["parameters"],
        decoded["window"],
        decoded["selection"],
        decoded["constructed_at"],
    )
    assert again == first


def test_roundtrip_with_non_ascii_opaque_content():
    body = canonical({"pad": "café ✓ ü", "schema": mmb.PARAMETERS_SCHEMA})
    decoded = mmb.decode_bundle(mmb.encode_bundle(body, W_BODY, S_BODY, CLOCK))
    assert decoded["parameters"] == body


def test_inputs_are_not_modified():
    p, w, s = bytes(P_BODY), bytes(W_BODY), bytes(S_BODY)
    before = (p, w, s)
    encoded = mmb.encode_bundle(p, w, s, CLOCK)
    assert (p, w, s) == before
    decoded = mmb.decode_bundle(encoded)
    assert decoded["parameters"] == p
    assert decoded["window"] == w
    assert decoded["selection"] == s
    assert CLOCK == "2026-10-19T12:34:56.789012Z"


# ---------------------------------------------------------------------------
# role and inner-schema refusals
# ---------------------------------------------------------------------------


def test_encode_rejects_wrong_role_bodies():
    for args in (
        (W_BODY, W_BODY, S_BODY),
        (P_BODY, P_BODY, S_BODY),
        (P_BODY, W_BODY, W_BODY),
        (P_BODY, W_BODY, P_BODY),
        (W_BODY, P_BODY, S_BODY),
    ):
        with pytest.raises(mmb.BundleError):
            mmb.encode_bundle(*args, CLOCK)


def test_encode_rejects_missing_or_wrong_inner_schema():
    for body in (
        b"{}",
        b"[]",
        b"null",
        b'{"schema":"market_memory.fitted_normalizer.v3"}',
        b'{"schema":"market_memory.selected_training_inputs.v2"}',
        b'{"schema":"research_factory.market_memory_e0_selected_control.v1"}',
        b'{"Schema":"market_memory.fitted_normalizer.v2"}',
    ):
        with pytest.raises(mmb.BundleError):
            mmb.encode_bundle(body, W_BODY, S_BODY, CLOCK)


def test_extra_opaque_inner_keys_are_accepted_and_preserved():
    body = canonical(
        {"owner_state": {"k": [1, 2, {"deep": True}]}, "schema": mmb.PARAMETERS_SCHEMA}
    )
    decoded = mmb.decode_bundle(mmb.encode_bundle(body, W_BODY, S_BODY, CLOCK))
    assert decoded["parameters"] == body


def test_decode_rejects_wrong_role_inner_schema():
    for kwargs in (
        {"parameters": W_BODY},
        {"window": S_BODY},
        {"selection": P_BODY},
        {"selection": W_BODY},
    ):
        rejects(wire_bytes(**kwargs), mmb.ERROR_INNER_SCHEMA)


def test_decode_rejects_wrong_wire_schema_and_keys():
    wire = json.loads(wire_bytes())
    wire["schema"] = "market_memory.persisted_fit_bundle.v2"
    rejects(canonical(wire), mmb.ERROR_WIRE)
    wire = json.loads(wire_bytes())
    del wire["schema"]
    rejects(canonical(wire), mmb.ERROR_WIRE)
    wire = json.loads(wire_bytes())
    wire["extra"] = 1
    rejects(canonical(wire), mmb.ERROR_WIRE)
    wire = json.loads(wire_bytes())
    del wire["constructed_at"]
    rejects(canonical(wire), mmb.ERROR_WIRE)
    wire = json.loads(wire_bytes())
    del wire["selection"]
    rejects(canonical(wire), mmb.ERROR_WIRE)
    rejects(b"[]", mmb.ERROR_WIRE)
    rejects(b"null", mmb.ERROR_WIRE)
    rejects(b'"text"', mmb.ERROR_WIRE)
    rejects(b"42", mmb.ERROR_WIRE)


# ---------------------------------------------------------------------------
# member shape, digest and size refusals
# ---------------------------------------------------------------------------


def test_decode_rejects_member_key_and_type_errors():
    cases = []
    wire = json.loads(wire_bytes())
    wire["parameters"]["extra"] = 1
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    del wire["parameters"]["sha256"]
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    del wire["parameters"]["bytes"]
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    del wire["parameters"]["value"]
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["window"]["bytes"] = True
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["window"]["bytes"] = 0
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["window"]["bytes"] = -3
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["window"]["bytes"] = 5.0
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["window"]["bytes"] = "5"
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["window"]["value"] = ["not", "an", "object"]
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["selection"]["sha256"] = hashlib.sha256(S_BODY).hexdigest().upper()
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["selection"]["sha256"] = "z" * 64
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["selection"]["sha256"] = "a" * 63
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    wire = json.loads(wire_bytes())
    wire["selection"]["sha256"] = 123
    cases.append((canonical(wire), mmb.ERROR_MEMBER))
    for text, message in cases:
        rejects(text, message)


def test_decode_rejects_digest_and_size_mismatch():
    wire = json.loads(wire_bytes())
    wire["parameters"]["sha256"] = "0" * 64
    rejects(canonical(wire), mmb.ERROR_DIGEST)
    wire = json.loads(wire_bytes())
    wire["window"]["bytes"] = wire["window"]["bytes"] + 1
    rejects(canonical(wire), mmb.ERROR_DIGEST)
    wire = json.loads(wire_bytes())
    wire["selection"]["bytes"] = wire["selection"]["bytes"] - 1
    rejects(canonical(wire), mmb.ERROR_DIGEST)


# ---------------------------------------------------------------------------
# canonicality, duplicates, nonfinite, UTF-8, non-JSON
# ---------------------------------------------------------------------------


def test_decode_rejects_duplicate_keys_anywhere():
    dup_inner = (
        b'{"schema":"market_memory.fitted_normalizer.v2",'
        b'"schema":"market_memory.fitted_normalizer.v2"}'
    )
    rejects(raw_wire(parameters=role_body_raw(dup_inner)), mmb.ERROR_DUPLICATE)
    good = raw_wire().decode("utf-8")
    top_dup = good[:1] + '"schema":"%s",' % mmb.WIRE_SCHEMA + good[1:]
    rejects(top_dup.encode("utf-8"), mmb.ERROR_DUPLICATE)
    padded = (
        '{"bytes":2,"sha256":"%s","value":{"a":1,"a":2}}'
        % hashlib.sha256(b'{"a":1,"a":2}').hexdigest()
    )
    rejects(raw_wire(window=padded), mmb.ERROR_DUPLICATE)


def test_decode_rejects_noncanonical_wire():
    rejects(raw_wire().replace(b'{"constructed_at"', b'{ "constructed_at"'), mmb.ERROR_CANONICAL)
    rejects(raw_wire().replace(b'"constructed_at":"', b'"constructed_at" : "'), mmb.ERROR_CANONICAL)
    rejects(raw_wire().replace(b'\n', b"") + b"\n", mmb.ERROR_CANONICAL)
    # unsorted keys: window text moved before selection
    wire = raw_wire().decode("utf-8")
    start_s = wire.index('"selection"')
    start_w = wire.index('"window"')
    swapped = wire[:start_s] + wire[start_w:-1] + "," + wire[start_s : start_w - 1] + "}"
    rejects(swapped.encode("utf-8"), mmb.ERROR_CANONICAL)
    assert swapped.index('"window"') < swapped.index('"selection"')


def test_encode_rejects_noncanonical_input_bodies():
    for body in (
        b' {"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"schema":"market_memory.fitted_normalizer.v2"} ',
        b'{"schema": "market_memory.fitted_normalizer.v2"}',
        b'{"schema":"market_memory.fitted_normalizer.v2",}',
        b'{"pad":"a","schema":"market_memory.fitted_normalizer.v2","pad":"a"}',
        b'{"n":1.50,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":1e2,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":-0,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":01,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":+1,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":.5,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":5.,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"schema":"market_memory.fitted_normalizer.v2","pad":"\\u0041"}',
        b'{"pad":"a","pad":"a","schema":"market_memory.fitted_normalizer.v2"}',
        b'{"PAD":1,"PAD":1,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":1,"n":1,"schema":"market_memory.fitted_normalizer.v2"}',
        b'{"n":1,"schema":"market_memory.fitted_normalizer.v2"}\n',
    ):
        with pytest.raises(mmb.BundleError):
            mmb.encode_bundle(body, W_BODY, S_BODY, CLOCK)


def test_decode_rejects_noncanonical_number_and_escape_forms():
    rejects(
        raw_wire(parameters=role_body_raw(
            b'{"n":1.50,"schema":"market_memory.fitted_normalizer.v2"}')),
        mmb.ERROR_CANONICAL,
    )
    rejects(
        raw_wire(window=role_body_raw(
            b'{"n":1e2,"schema":"market_memory.selected_training_inputs.v2"}')),
        mmb.ERROR_CANONICAL,
    )
    rejects(
        raw_wire(selection=role_body_raw(
            b'{"n":-0,"schema":"research_factory.market_memory_e0_selected_control.v1"}')),
        mmb.ERROR_CANONICAL,
    )


def test_decode_rejects_non_json_and_truncated_input():
    for text in (
        b"",
        b"{",
        b"}",
        b"[",
        b'{"a":}',
        b'{"a":1,}',
        b"[1,2",
        b"[1,]",
        b"tru",
        b"nul",
        b"01",
        b'"unterminated',
        b'{"a":1}{"b":2}',
        b"{} {}",
        b"0" * mmb.MAX_BUNDLE_BYTES,
    ):
        with pytest.raises(mmb.BundleError):
            mmb.decode_bundle(text)


def test_decode_rejects_invalid_utf8():
    rejects(b"\xff" + wire_bytes(), mmb.ERROR_UTF8)
    body = canonical({"pad": "café", "schema": mmb.PARAMETERS_SCHEMA})
    encoded = mmb.encode_bundle(body, W_BODY, S_BODY, CLOCK)
    truncated = bytearray(encoded)
    cut = encoded.index(b"caf\xc3\xa9") + 4  # second byte of é
    del truncated[cut]
    rejects(bytes(truncated), mmb.ERROR_UTF8)
    rejects(wire_bytes()[:-1] + b"\x80", mmb.ERROR_UTF8)


def test_decode_rejects_nonfinite_numbers():
    rejects(
        raw_wire(parameters=role_body_raw(
            b'{"n":NaN,"schema":"market_memory.fitted_normalizer.v2"}')),
        mmb.ERROR_NONFINITE,
    )
    rejects(
        raw_wire(window=role_body_raw(
            b'{"n":Infinity,"schema":"market_memory.selected_training_inputs.v2"}')),
        mmb.ERROR_NONFINITE,
    )
    rejects(
        raw_wire(selection=role_body_raw(
            b'{"n":-Infinity,"schema":"research_factory.market_memory_e0_selected_control.v1"}')),
        mmb.ERROR_NONFINITE,
    )
    rejects(
        raw_wire(parameters=role_body_raw(
            b'{"n":1e999,"schema":"market_memory.fitted_normalizer.v2"}')),
        mmb.ERROR_NONFINITE,
    )


def test_decode_rejects_raw_control_chars_in_strings():
    rejects(
        raw_wire(parameters=role_body_raw(
            b'{"pad":"a\x01b","schema":"market_memory.fitted_normalizer.v2"}')),
        mmb.ERROR_JSON,
    )


# ---------------------------------------------------------------------------
# clock refusals
# ---------------------------------------------------------------------------


BAD_CLOCKS = [
    "2026-10-19T12:34:56Z",
    "2026-10-19T12:34:56.1234567Z",
    "2026-10-19T12:34:56.12345",
    "2026-10-19T12:34:56.123456",
    "2026-10-19 12:34:56.123456Z",
    "2026-10-19T12:34:56,123456Z",
    "2026-02-30T12:34:56.123456Z",
    "2027-02-29T12:34:56.123456Z",
    "2026-13-01T00:00:00.000000Z",
    "2026-00-10T00:00:00.000000Z",
    "0000-01-01T00:00:00.000000Z",
    "2026-10-19T24:00:00.000000Z",
    "2026-10-19T12:60:00.000000Z",
    "2026-10-19T12:34:60.000000Z",
    "2026-10-19T12:34:56.123456z",
    "2026-10-19t12:34:56.123456Z",
    "",
    "2026-10-19T12:34:56.123456Z ",
    " 2026-10-19T12:34:56.123456Z",
]


@pytest.mark.parametrize("bad", BAD_CLOCKS)
def test_decode_rejects_bad_clocks(bad):
    rejects(raw_wire(clock=bad), mmb.ERROR_CLOCK)


@pytest.mark.parametrize("bad", BAD_CLOCKS)
def test_encode_rejects_bad_clocks(bad):
    with pytest.raises(mmb.BundleError):
        mmb.encode_bundle(P_BODY, W_BODY, S_BODY, bad)


def test_encode_rejects_non_str_clock_types():
    for bad in (None, 123, True, b"2026-10-19T12:34:56.789012Z", ["x"], {"a": 1}):
        with pytest.raises(mmb.BundleError):
            mmb.encode_bundle(P_BODY, W_BODY, S_BODY, bad)


def test_leap_day_clock_is_accepted_when_real():
    encoded = mmb.encode_bundle(
        P_BODY, W_BODY, S_BODY, "2028-02-29T23:59:59.999999Z"
    )
    assert mmb.decode_bundle(encoded)["constructed_at"] == "2028-02-29T23:59:59.999999Z"


# ---------------------------------------------------------------------------
# exact type refusals
# ---------------------------------------------------------------------------


class _BytesSub(bytes):
    pass


class _StrSub(str):
    pass


def test_decode_rejects_wrong_body_types():
    for bad in (
        bytearray(P_BODY),
        memoryview(P_BODY),
        _BytesSub(wire_bytes()),
        wire_bytes().decode("utf-8"),
        123,
        None,
        True,
        [],
        {},
        1.5,
    ):
        with pytest.raises(mmb.BundleError):
            mmb.decode_bundle(bad)


def test_encode_rejects_wrong_body_types():
    class Case:
        pass

    for bad in (
        bytearray(P_BODY),
        memoryview(P_BODY),
        _BytesSub(P_BODY),
        P_BODY.decode("utf-8"),
        None,
        True,
        1,
        [],
        {},
    ):
        with pytest.raises(mmb.BundleError):
            mmb.encode_bundle(bad, W_BODY, S_BODY, CLOCK)
    with pytest.raises(mmb.BundleError):
        mmb.encode_bundle(P_BODY, bytearray(W_BODY), S_BODY, CLOCK)
    with pytest.raises(mmb.BundleError):
        mmb.encode_bundle(P_BODY, W_BODY, _BytesSub(S_BODY), CLOCK)
    with pytest.raises(mmb.BundleError):
        mmb.encode_bundle(P_BODY, W_BODY, S_BODY, _StrSub(CLOCK))
    with pytest.raises(mmb.BundleError):
        mmb.encode_bundle(P_BODY, W_BODY, S_BODY, None)


def test_empty_bodies_are_refused_on_encode():
    for args in (
        (b"", W_BODY, S_BODY),
        (P_BODY, b"", S_BODY),
        (P_BODY, W_BODY, b""),
    ):
        with pytest.raises(mmb.BundleError):
            mmb.encode_bundle(*args, CLOCK)


# ---------------------------------------------------------------------------
# bounds: size, depth, nodes
# ---------------------------------------------------------------------------


def test_decode_enforces_wire_size_before_parsing():
    limit = mmb.MAX_BUNDLE_BYTES
    rejects(b"0" * (limit + 1), mmb.ERROR_LIMIT)
    rejects(b'{"a":"' + b"x" * limit + b'"}', mmb.ERROR_LIMIT)
    rejects(b"0" * limit, mmb.ERROR_JSON)


def test_encode_enforces_body_size_before_parsing():
    limit = mmb.MAX_BUNDLE_BYTES
    huge = (
        b'{"pad":"' + b"x" * limit + b'","schema":"'
        + mmb.PARAMETERS_SCHEMA.encode("utf-8") + b'"}'
    )
    assert len(huge) > limit
    with pytest.raises(mmb.BundleError) as excinfo:
        mmb.encode_bundle(huge, W_BODY, S_BODY, CLOCK)
    assert str(excinfo.value) == mmb.ERROR_LIMIT


def test_exact_one_mib_wire_is_accepted_and_plus_one_refused():
    limit = mmb.MAX_BUNDLE_BYTES

    def member_of(inner: bytes) -> dict:
        return {
            "bytes": len(inner),
            "sha256": hashlib.sha256(inner).hexdigest(),
            "value": json.loads(inner.decode("utf-8")),
        }

    pad = 0
    exact = None
    for _ in range(10):
        sel = padded_inner(pad, mmb.SELECTION_SCHEMA)
        wire = {
            "constructed_at": CLOCK,
            "parameters": member_of(P_BODY),
            "schema": mmb.WIRE_SCHEMA,
            "selection": member_of(sel),
            "window": member_of(W_BODY),
        }
        text = canonical(wire)
        gap = limit - len(text)
        if gap == 0:
            exact = text
            break
        pad += gap
    assert exact is not None
    body = padded_inner(pad, mmb.SELECTION_SCHEMA)
    encoded = mmb.encode_bundle(P_BODY, W_BODY, body, CLOCK)
    assert len(encoded) == limit
    assert encoded == exact
    decoded = mmb.decode_bundle(encoded)
    assert decoded["parameters"] == P_BODY
    assert decoded["window"] == W_BODY
    assert decoded["selection"] == body
    over = padded_inner(pad + 1, mmb.SELECTION_SCHEMA)
    with pytest.raises(mmb.BundleError) as excinfo:
        mmb.encode_bundle(P_BODY, W_BODY, over, CLOCK)
    assert str(excinfo.value) == mmb.ERROR_LIMIT
    rejects(raw_wire(selection=role_body_raw(over) + " "), mmb.ERROR_LIMIT)


def test_depth_limit_boundary():
    # wire(1) + member(2) + value(3) + levels arrays + innermost scalar:
    # max depth is 4 + levels, so 28 levels sits exactly at MAX_DEPTH.
    ok = raw_wire(parameters=role_body_raw(deep_inner(28)))
    decoded = mmb.decode_bundle(ok)
    assert decoded["parameters"] == deep_inner(28)
    rejects(raw_wire(parameters=role_body_raw(deep_inner(29))), mmb.ERROR_LIMIT)
    rejects(raw_wire(parameters=role_body_raw(deep_inner(64))), mmb.ERROR_LIMIT)


def _wide_inner(count: int) -> bytes:
    return (
        '{"items":[' + ",".join(["0"] * count) + '],"schema":"%s"}'
        % mmb.PARAMETERS_SCHEMA
    ).encode("utf-8")


def test_node_limit_boundary():
    # ~100013 nodes on the wire: over the 100000 node bound.
    over = raw_wire(parameters=role_body_raw(_wide_inner(100000)))
    assert len(over) < mmb.MAX_BUNDLE_BYTES
    rejects(over, mmb.ERROR_LIMIT)
    under = raw_wire(parameters=role_body_raw(_wide_inner(50000)))
    decoded = mmb.decode_bundle(under)
    assert decoded["parameters"] == _wide_inner(50000)


# ---------------------------------------------------------------------------
# error hygiene
# ---------------------------------------------------------------------------


def test_error_messages_never_leak_payload():
    sentinel_inner = canonical(
        {"pad": "SENTINEL-7f3a-secret", "schema": mmb.PARAMETERS_SCHEMA}
    )
    wire = json.loads(wire_bytes(parameters=sentinel_inner))
    wire["parameters"]["sha256"] = "0" * 64
    with pytest.raises(mmb.BundleError) as excinfo:
        mmb.decode_bundle(canonical(wire))
    assert "SENTINEL-7f3a-secret" not in str(excinfo.value)
    secret = b"TOPSECRET-9be1-payload"
    with pytest.raises(mmb.BundleError) as excinfo:
        mmb.decode_bundle(secret + wire_bytes())
    assert secret not in str(excinfo.value).encode("utf-8")
    assert b"\xff" not in str(excinfo.value).encode("utf-8", "replace")


def test_depth_and_node_overflow_share_the_fixed_limit_text():
    texts = set()
    for wire in (
        raw_wire(parameters=role_body_raw(deep_inner(40))),
        raw_wire(parameters=role_body_raw(_wide_inner(100000))),
    ):
        with pytest.raises(mmb.BundleError) as excinfo:
            mmb.decode_bundle(wire)
        texts.add(str(excinfo.value))
    assert texts == {mmb.ERROR_LIMIT}
