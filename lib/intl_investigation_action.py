"""Pure ingress URL projection for the International Investigate action.

This module turns one *admitted* International generation - the published
generation contract and the ready current descriptor that binds it - into the
single native action the workspace may offer: a relative ingress URL that
carries the reference fields (context, generation, fingerprint and the
selected field ids) into the International Investigate view.

It owns one thing and nothing else: the projection from an admitted
publication to an action dictionary.  The parent controller owns the UI, the
renderer, the bridge catalog and the product URL policy; this module reaches
for none of them and implements no math of its own.

Guarantees:

* the action exists only for a *ready* descriptor whose generation, artifact
  digest, artifact size and current policies all bind the canonical
  serialization of the supplied contract - a generation uuid alone is never
  enough, and a contract that merely *claims* a generation is refused;
* the context must exist exactly once in the contract, and the selected field
  ids must be non-empty, bounded, distinct and actual members of that
  context;
* every selected field must be qualified, metadata- and value-allowed, and
  carry the content, qualification and policy identities that the accepted
  projection helpers derive from the published bytes;
* the fallback return URL must be a canonical International product URL with
  an ordinary application query - no credential, no question, no account, no
  record, no token and no shell transport ever reaches the action;
* the reference fields never depend on the return URL, so the parent
  controller may replace the return with the admitted current product URL
  without invalidating the action;
* a withheld, unknown, denied, stale, missing, unbound, malformed or
  oversized input yields no action at all: the projection fails closed.

The module performs no I/O, no clock reading, no network access and no
configuration lookup.  It never widens the bridge catalog and it never
invents a grant.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import quote, urlsplit

from lib.intl_generation_publication import (
    _validate_descriptor,
    serialize_generation,
)
from lib.intl_investigation_projection import (
    _canonical_json,
    _content_identity,
    _decision_ok,
    _qualification_identity,
    _receipt_ok,
    _sha256_hex,
)

#: The only origin a fallback return may name.
RETURN_ORIGIN = "https://www.mastermind-x.com"

#: The existing native ingress accepts this one product return route.
RETURN_PATHS = ("/intl.html",)

#: The canonical International application query vocabulary.
APP_QUERY_FIELDS = (
    "view", "market", "pins", "horizon", "basis", "return_basis", "group")

#: The only return basis the International workspace admits.
APP_RETURN_BASIS = "price"


#: An upper bound on the selected field ids of one action.
MAX_SELECTED_MEASURE_IDS = 128

#: An upper bound on the native action URL, in bytes.
MAX_ACTION_URL_BYTES = 2048

#: An upper bound on the fallback return URL, in bytes.
MAX_RETURN_URL_BYTES = 2048

#: An upper bound on the application query of a fallback return, in units.
MAX_APP_QUERY_UNITS = 2048

#: An upper bound on the application query pairs of a fallback return.
MAX_APP_QUERY_PAIRS = 16

#: An upper bound on the pinned markets of an application query.
MAX_APP_PINS = 4

#: An upper bound on a scalar application value, in units.
MAX_APP_SCALAR_UNITS = 128

_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_FIELD_RE = re.compile(r"^[A-Z]{2}\.[a-z][a-z0-9_]{0,63}$")
_APP_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,2047}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")

#: Parameters that may never reach an action, even under another name.
FORBIDDEN_APP_PARAMETERS = frozenset({
    "question", "account", "record", "token", "auth", "saved", "principal",
    "owner", "mmx_shell", "mmx_generation"})


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _encode(value):
    """Percent-encode one query value.

    This is the ``encodeURIComponent`` equivalent for every alphabet this
    module emits: letters, digits and ``_.-~`` stay as they are and every
    other character - including ``:``, ``/``, ``?``, ``&``, ``=`` and ``#`` -
    becomes its percent escape.
    """
    return quote(value, safe="")


def _decode_query_part(value):
    """Strictly decode one application query part, or return ``None``.

    ``+`` is a space, a percent escape must carry two hex digits, the result
    must decode as UTF-8 and it may not carry a control character.  This is
    the strict decoder of the workspace state reducer; a malformed escape is
    a refusal, never a silent passthrough.
    """
    raw = bytearray()
    index = 0
    text = value.replace("+", " ")
    while index < len(text):
        char = text[index]
        if char == "%":
            digits = text[index + 1:index + 3]
            if len(digits) != 2 or digits[0] not in _HEX_DIGITS \
                    or digits[1] not in _HEX_DIGITS:
                return None
            raw.append(int(digits, 16))
            index += 3
            continue
        if ord(char) > 0xff:
            return None
        raw.append(ord(char))
        index += 1
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    for char in decoded:
        unit = ord(char)
        if unit <= 0x1f or unit == 0x7f or 0x80 <= unit <= 0x9f:
            return None
    return decoded


def _app_value_ok(value):
    """True for an ordinary application value."""
    return bool(_APP_VALUE_RE.match(value))


# ---------------------------------------------------------------------------
# The application query
# ---------------------------------------------------------------------------

def _app_query_ok(query):
    """True only for an ordinary International application query.

    The vocabulary is closed and every key must appear at most once: an
    unknown key or a repeated key is refused, which is what keeps a question,
    an account, a record, a token or a shell transport out of the action.
    """
    if len(query) > MAX_APP_QUERY_UNITS:
        return False
    if "#" in query:
        return False
    pairs = query.split("&")
    if len(pairs) > MAX_APP_QUERY_PAIRS:
        return False
    values = {}
    for pair in pairs:
        separator = pair.find("=")
        if separator == -1:
            return False
        key = _decode_query_part(pair[:separator])
        if key is None:
            return False
        if key in FORBIDDEN_APP_PARAMETERS or key not in APP_QUERY_FIELDS:
            return False
        if key in values:
            return False
        if key == "pins":
            encoded = pair[separator + 1:]
            if encoded == "":
                values[key] = []
                continue
            pins = encoded.split(",")
            if len(pins) > MAX_APP_PINS:
                return False
            decoded = []
            for pin in pins:
                value = _decode_query_part(pin)
                if value is None or value == "" or "," in value:
                    return False
                decoded.append(value)
            values[key] = decoded
            continue
        value = _decode_query_part(pair[separator + 1:])
        if value is None:
            return False
        values[key] = value

    # The workspace admits exactly one return basis and no empty dimension.
    if "view" in values and values["view"] == "":
        return False
    if "horizon" in values and values["horizon"] == "":
        return False
    if "basis" in values and values["basis"] == "":
        return False
    if "return_basis" in values and values["return_basis"] != APP_RETURN_BASIS:
        return False
    for key in ("view", "market", "horizon", "basis", "return_basis", "group"):
        value = values.get(key)
        if value is None or value == "":
            continue
        if not _app_value_ok(value):
            return False
    for key in ("market", "group"):
        value = values.get(key)
        if value is not None and len(value) > MAX_APP_SCALAR_UNITS:
            return False
    pins = values.get("pins")
    if pins is not None:
        if len(set(pins)) != len(pins):
            return False
        for pin in pins:
            if not _app_value_ok(pin) or len(pin) > MAX_APP_SCALAR_UNITS:
                return False
    return True


# ---------------------------------------------------------------------------
# The fallback return
# ---------------------------------------------------------------------------

def _return_url_ok(return_url, contract):
    """True only for a canonical International product URL.

    The URL must be absolute, canonical, credential-free and free of control
    characters and backslashes; its path must be the admitted intl.html page;
    its complete application query must select Macro or Risk with no group;
    and it must have no fragment or percent-encoded inner-query bytes.
    """
    if type(return_url) is not str or not return_url:
        return False
    if len(return_url.encode("utf-8")) > MAX_RETURN_URL_BYTES:
        return False
    for char in return_url:
        if not ("!" <= char <= "~"):
            return False
    if "\\" in return_url or "%" in return_url:
        return False
    parts = urlsplit(return_url)
    if parts.scheme != "https":
        return False
    if parts.netloc != RETURN_ORIGIN[len("https://"):]:
        # An exact netloc also refuses credentials, a port and any other host.
        return False
    if parts.path not in RETURN_PATHS:
        return False
    if parts.query and not _app_query_ok(parts.query):
        return False
    from urllib.parse import parse_qsl
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    contexts = contract["contexts"]
    dimensions = {"market": {c["market"] for c in contexts},
                  "horizon": {c["horizon"] for c in contexts},
                  "basis": {c["currency_basis"] for c in contexts}}
    for key, values in dimensions.items():
        if query.get(key) and query[key] not in values:
            return False
    if any(pin not in dimensions["market"] for pin in query.get("pins", "").split(",") if pin):
        return False
    if query.get("view") and query["view"] not in {
            "overview", "compare", "macro", "risk", "history", "library", "scanner",
            "dislocations", "transmission", "dossier", "scenario", "replay", "coverage"}:
        return False
    if parts.fragment:
        return False
    if set(query) != set(APP_QUERY_FIELDS) or query.get("view") not in {"macro", "risk"} or query.get("group") != "":
        return False
    return True


# ---------------------------------------------------------------------------
# The admitted publication
# ---------------------------------------------------------------------------

def _bound_publication(contract, descriptor):
    """Return ``(generation, canonical_bytes)`` for a bound publication.

    The descriptor must be ready and must bind the canonical serialization of
    the contract in its generation, its artifact digest, its artifact size and
    its current policies.  Anything else is unbound and yields no action.
    """
    try:
        checked = _validate_descriptor(descriptor)
        payload = serialize_generation(contract)
    except (TypeError, ValueError, KeyError, RecursionError):
        return None
    if checked["state"] != "ready":
        return None
    generation = contract["generation"]
    if checked["generation"] != generation:
        return None
    if checked["artifact_sha256"] != hashlib.sha256(payload).hexdigest():
        return None
    if checked["artifact_bytes"] != len(payload):
        return None
    if checked["current_policies"] != contract["policies"]:
        return None
    points = contract.get("policy_points_ref")
    expected_point_policy = ({"metadata": "allowed", "value_permission": "allowed", "mapping_identity": points["mapping_identity"]}
                             if points is not None else None)
    if checked.get("current_policy_points") != expected_point_policy:
        return None
    return generation, payload


def _selected_context(contract, context_id):
    """Return the one contract context that carries this identifier."""
    if type(context_id) is not str or not _IDENTITY_RE.match(context_id):
        return None
    matches = [context for context in contract["contexts"]
               if context["id"] == context_id]
    if len(matches) != 1:
        return None
    return matches[0]


def _selected_fields(context, selected_measure_ids):
    """Return the ordered, distinct, admitted field ids of this context."""
    if type(selected_measure_ids) is not list:
        return None
    if not selected_measure_ids:
        return None
    if len(selected_measure_ids) > MAX_SELECTED_MEASURE_IDS:
        return None
    members = set(context["measure_ids"])
    seen = set()
    for sid in selected_measure_ids:
        if type(sid) is not str or not _FIELD_RE.match(sid):
            return None
        if sid in seen:
            return None
        seen.add(sid)
        if sid not in members:
            return None
    return list(selected_measure_ids)


def _field_admitted(contract, generation, sid):
    """True only for a qualified, allowed and policy-bound field."""
    entry = contract["measures"].get(sid)
    if entry is None:
        return False
    native = entry["native_measure"]
    if native["quality"] != "qualified":
        return False
    if native["metadata"] != "allowed" or native["value_permission"] != "allowed":
        return False
    for key in ("content_identity", "qualification_identity"):
        value = entry[key]
        if type(value) is not str or not _SHA256_RE.match(value):
            return False
    policy = contract["policies"].get(sid)
    if policy is None:
        return False
    if policy["metadata"] != "allowed" or policy["value_permission"] != "allowed":
        return False
    if policy["policy_ref"] is None or policy["policy_document_sha256"] is None:
        return False
    policy_identity = policy["policy_identity"]
    if type(policy_identity) is not str or not _SHA256_RE.match(policy_identity):
        return False
    if "policy_identity" in entry:
        # A publication that carries the adopted policy identity on the
        # measure itself must agree with the contract policies.
        if entry["policy_identity"] != policy_identity:
            return False
    receipt = entry["native_evidence"]["receipt_identity"]
    decision = entry["native_evidence"]["publication_decision"]
    if not _receipt_ok(receipt, sid):
        return False
    if not _decision_ok(decision, sid, native, receipt, generation):
        return False
    if entry["content_identity"] != _content_identity(sid, native, receipt):
        return False
    if entry["qualification_identity"] != _qualification_identity(
            sid, decision, receipt):
        return False
    return True


# ---------------------------------------------------------------------------
# The action
# ---------------------------------------------------------------------------

def _build_href(context_id, generation, fingerprint, field_ids, return_url):
    """The relative native action URL of one International investigation."""
    parts = [
        "view=investigations",
        "intl_context=" + _encode(context_id),
        "intl_generation=" + _encode(generation),
        "intl_fingerprint=" + _encode(fingerprint),
    ]
    for sid in field_ids:
        parts.append("intl_field=" + _encode(sid))
    parts.append("intl_return=" + _encode(return_url))
    return "/analysis?" + "&".join(parts)


def build_intl_investigation_action(*, contract, descriptor, context_id,
                                    selected_measure_ids, return_url):
    """Project one admitted generation into the International action.

    ``contract`` is the published International generation contract and
    ``descriptor`` is the ready current descriptor that binds it; both are
    local producer objects, not a user permission.  ``context_id`` must name
    exactly one context of the contract and ``selected_measure_ids`` must be
    the non-empty, ordered, distinct and bounded list of fields that the
    context actually admits.  ``return_url`` is the fallback product URL the
    parent controller may replace on activation.

    Returns the action dictionary - exactly ``href``, ``context_id``,
    ``generation``, ``fingerprint`` and ``field_ids`` - or ``None`` when the
    publication is unbound, the context is unknown, any selected field is
    withheld, the return URL is not an ordinary International product URL or
    the action URL would be oversized.  No refusal ever yields a partially
    enabled action.
    """
    bound = _bound_publication(contract, descriptor)
    if bound is None:
        return None
    generation, _payload = bound

    context = _selected_context(contract, context_id)
    if context is None:
        return None

    field_ids = _selected_fields(context, selected_measure_ids)
    if field_ids is None:
        return None

    for sid in field_ids:
        if not _field_admitted(contract, generation, sid):
            return None

    if not _return_url_ok(return_url, contract):
        return None
    from urllib.parse import parse_qsl
    navigation = dict(parse_qsl(urlsplit(return_url).query, keep_blank_values=True))
    if (navigation["horizon"] != context["horizon"] or navigation["basis"] != context["currency_basis"]
            or navigation["return_basis"] != context["return_basis"]):
        return None

    fingerprint = hashlib.sha256(_payload).hexdigest()
    href = _build_href(context_id, generation, fingerprint, field_ids, return_url)
    if len(href.encode("utf-8")) > MAX_ACTION_URL_BYTES:
        return None

    return {
        "href": href,
        "context_id": context_id,
        "generation": generation,
        "fingerprint": fingerprint,
        "field_ids": list(field_ids),
    }


__all__ = ["build_intl_investigation_action"]
