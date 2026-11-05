"""Pure native APT 0.2 JSON-hook transaction contract.

normalize_transaction(raw) freezes a COMPLETE APT 0.2 JSON-hook
"org.debian.apt.hooks.install.pre-prompt" / "...package-list" transaction
into a canonical dict; every action row and every origin field is preserved
except the internal "id" integers.  assert_same_transaction(expected,
observed) requires exact normalized equality.  parse_preinstall_v3(raw)
parses the strict, bounded DPkg::Pre-Install-Pkgs "VERSION 3" text protocol
and returns package-action rows only; the CONFIG section is consumed and is
never returned, stored or echoed, including in error messages.

stdlib only, no I/O, no executor, no subprocess.  These pure records are
freeze/compare evidence for a forthcoming cold same-origin native APT
parallel-download candidate.  They are NOT authentication, custody, or
origin-authenticity authority: origins are preserved verbatim and are never
reduced to a boolean.  A parse_preinstall_v3 result does not by itself claim
to be the same transaction; the parent must cross-check expected inputs and
the archive mapping of both sides under the native lock before any equality
claim.  No payload or cache hit is a semantic PASS for that candidate.
"""

import json
import re

__all__ = [
    "normalize_transaction",
    "assert_same_transaction",
    "parse_preinstall_v3",
]

_MAX_RAW = 1024 * 1024
_MAX_PACKAGES = 128
_MAX_SEARCH_TERMS = 64
_MAX_STRING = 160
_MAX_PATH = 4096
_MAX_INT = 2 ** 53

_METHODS = (
    "org.debian.apt.hooks.install.pre-prompt",
    "org.debian.apt.hooks.install.package-list",
)
_MODES_INSTALL = ("install", "upgrade", "downgrade", "reinstall")
_MODES_REMOVE = ("deinstall", "purge")
_MODES = _MODES_INSTALL + _MODES_REMOVE

ERR_TOO_LARGE = "APT_TXN_RAW_TOO_LARGE"
ERR_NOT_UTF8 = "APT_TXN_NOT_UTF8"
ERR_BAD_JSON = "APT_TXN_BAD_JSON"
ERR_DUPLICATE_KEY = "APT_TXN_DUPLICATE_JSON_KEY"
ERR_NONFINITE = "APT_TXN_NONFINITE_NUMBER"
ERR_HUGE_INT = "APT_TXN_HUGE_INTEGER"
ERR_TOO_DEEP = "APT_TXN_TOO_DEEP"
ERR_BAD_ENVELOPE = "APT_TXN_BAD_ENVELOPE"
ERR_BAD_PARAMS = "APT_TXN_BAD_PARAMS"
ERR_BAD_COMMAND = "APT_TXN_BAD_COMMAND"
ERR_BAD_SEARCH_TERMS = "APT_TXN_BAD_SEARCH_TERMS"
ERR_BAD_UNKNOWN_PACKAGES = "APT_TXN_BAD_UNKNOWN_PACKAGES"
ERR_BAD_PACKAGES = "APT_TXN_BAD_PACKAGES"
ERR_BAD_ROW = "APT_TXN_BAD_PACKAGE_ROW"
ERR_DUPLICATE_ROW = "APT_TXN_DUPLICATE_ROW"
ERR_MISSING_VERSION = "APT_TXN_MISSING_VERSION_FOR_MODE"
ERR_BAD_VERSION_BLOCK = "APT_TXN_BAD_VERSION_BLOCK"
ERR_BAD_ORIGIN = "APT_TXN_BAD_ORIGIN"
ERR_CHANGED = "APT_TXN_TRANSACTION_CHANGED"
ERR_PREINSTALL_TOO_LARGE = "APT_TXN_PREINSTALL_TOO_LARGE"
ERR_PREINSTALL_BAD_VERSION = "APT_TXN_PREINSTALL_UNSUPPORTED_VERSION"
ERR_PREINSTALL_MALFORMED = "APT_TXN_PREINSTALL_MALFORMED"
ERR_PREINSTALL_BAD_FIELD = "APT_TXN_PREINSTALL_BAD_FIELD"
ERR_PREINSTALL_ERROR_ACTION = "APT_TXN_PREINSTALL_ERROR_ACTION"
ERR_PREINSTALL_DUPLICATE_ROW = "APT_TXN_PREINSTALL_DUPLICATE_ROW"

_REASONS = frozenset({
    ERR_TOO_LARGE, ERR_NOT_UTF8, ERR_BAD_JSON, ERR_DUPLICATE_KEY,
    ERR_NONFINITE, ERR_HUGE_INT, ERR_TOO_DEEP, ERR_BAD_ENVELOPE,
    ERR_BAD_PARAMS, ERR_BAD_COMMAND, ERR_BAD_SEARCH_TERMS,
    ERR_BAD_UNKNOWN_PACKAGES, ERR_BAD_PACKAGES, ERR_BAD_ROW,
    ERR_DUPLICATE_ROW, ERR_MISSING_VERSION, ERR_BAD_VERSION_BLOCK,
    ERR_BAD_ORIGIN, ERR_CHANGED, ERR_PREINSTALL_TOO_LARGE,
    ERR_PREINSTALL_BAD_VERSION, ERR_PREINSTALL_MALFORMED,
    ERR_PREINSTALL_BAD_FIELD, ERR_PREINSTALL_ERROR_ACTION,
    ERR_PREINSTALL_DUPLICATE_ROW,
})

_NAME_RE = re.compile(r"\A[a-z0-9][a-z0-9+.\-]{1,127}\Z")
_ARCH_RE = re.compile(r"\A[a-z0-9][a-z0-9\-]{0,31}\Z")
_VERSION_RE = re.compile(r"\A[0-9][0-9A-Za-z.+:~\-]{0,199}\Z")
_SELECTOR_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9+.:_\-]{0,127}\Z")


def _fail(code):
    raise ValueError(code)


def _no_constant(_token):
    _fail(ERR_NONFINITE)


def _bounded_int(text):
    value = int(text)
    if value > _MAX_INT or value < -_MAX_INT:
        _fail(ERR_HUGE_INT)
    return value


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail(ERR_DUPLICATE_KEY)
        result[key] = value
    return result


def _load_json(raw):
    if not isinstance(raw, (bytes, bytearray)):
        _fail(ERR_NOT_UTF8)
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError:
        _fail(ERR_NOT_UTF8)
    # Decoder recursion limits differ across supported Python versions. Bound
    # structural depth explicitly before decoding; quoted brackets do not count.
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 64:
                _fail(ERR_TOO_DEEP)
        elif char in "]}":
            depth -= 1
    try:
        return json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_no_constant,
            parse_int=_bounded_int,
        )
    except ValueError as exc:
        if str(exc) in _REASONS:
            raise
        _fail(ERR_BAD_JSON)
    except RecursionError:
        _fail(ERR_TOO_DEEP)


def _match(regex, value, code):
    if type(value) is not str or regex.match(value) is None:
        _fail(code)
    return value


def _plain_string(value, code):
    if type(value) is not str or len(value) > _MAX_STRING:
        _fail(code)
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        _fail(code)
    return value


def _list_of(value, item_normalizer, code):
    if type(value) is not list:
        _fail(code)
    return [item_normalizer(item) for item in value]

_ORIGIN_FIELDS = ("archive", "codename", "version", "origin", "label", "site")
_ORIGIN_KEY_SET = frozenset(_ORIGIN_FIELDS)
_VERSION_KEY_SET = frozenset({"id", "version", "architecture", "pin", "origins"})
_ROW_KEY_SET = frozenset(
    {"id", "name", "architecture", "mode", "automatic", "versions"}
)


def _normalize_origin(raw):
    if type(raw) is not dict or set(raw) != _ORIGIN_KEY_SET:
        _fail(ERR_BAD_ORIGIN)
    return {field: _plain_string(raw[field], ERR_BAD_ORIGIN)
            for field in _ORIGIN_FIELDS}


def _normalize_version_entry(raw):
    if type(raw) is not dict or set(raw) != _VERSION_KEY_SET:
        _fail(ERR_BAD_VERSION_BLOCK)
    if type(raw["id"]) is not int:
        _fail(ERR_BAD_VERSION_BLOCK)
    pin = raw["pin"]
    if type(pin) is not int:
        _fail(ERR_BAD_VERSION_BLOCK)
    return {
        "version": _match(_VERSION_RE, raw["version"], ERR_BAD_VERSION_BLOCK),
        "architecture": _match(
            _ARCH_RE, raw["architecture"], ERR_BAD_VERSION_BLOCK),
        "pin": pin,
        "origins": _list_of(raw["origins"], _normalize_origin,
                            ERR_BAD_VERSION_BLOCK),
    }


def _normalize_row(raw):
    if type(raw) is not dict or set(raw) != _ROW_KEY_SET:
        _fail(ERR_BAD_ROW)
    if type(raw["id"]) is not int:
        _fail(ERR_BAD_ROW)
    mode = raw["mode"]
    if mode not in _MODES:
        _fail(ERR_BAD_ROW)
    if type(raw["automatic"]) is not bool:
        _fail(ERR_BAD_ROW)
    versions_raw = raw["versions"]
    if type(versions_raw) is not dict:
        _fail(ERR_BAD_VERSION_BLOCK)
    if set(versions_raw) - frozenset({"candidate", "install", "current"}):
        _fail(ERR_BAD_VERSION_BLOCK)
    versions = {key: _normalize_version_entry(versions_raw[key])
                for key in versions_raw}
    if mode in _MODES_INSTALL and "install" not in versions:
        _fail(ERR_MISSING_VERSION)
    if mode in _MODES_REMOVE and "current" not in versions:
        _fail(ERR_MISSING_VERSION)
    return {
        "name": _match(_NAME_RE, raw["name"], ERR_BAD_ROW),
        "architecture": _match(_ARCH_RE, raw["architecture"], ERR_BAD_ROW),
        "mode": mode,
        "automatic": raw["automatic"],
        "versions": versions,
    }


def normalize_transaction(raw):
    """Freeze a complete APT 0.2 JSON-hook install transaction.

    Returns {"command", "search-terms", "packages"} with packages sorted by
    (name, architecture) and every internal "id" dropped.  Rejects anything
    else with ValueError(<fixed reason code>); error messages never echo the
    body, parameters or origins of the input.
    """
    if not isinstance(raw, (bytes, bytearray)):
        _fail(ERR_NOT_UTF8)
    if len(raw) > _MAX_RAW:
        _fail(ERR_TOO_LARGE)
    document = _load_json(raw)
    if type(document) is not dict:
        _fail(ERR_BAD_ENVELOPE)
    if set(document) - frozenset({"jsonrpc", "method", "params", "id"}):
        _fail(ERR_BAD_ENVELOPE)
    if document.get("jsonrpc") != "2.0" or document.get("method") not in _METHODS:
        _fail(ERR_BAD_ENVELOPE)
    params = document.get("params")
    if type(params) is not dict or set(params) != frozenset({
            "command", "search-terms", "unknown-packages", "packages"}):
        _fail(ERR_BAD_PARAMS)
    if params["command"] != "install":
        _fail(ERR_BAD_COMMAND)
    selectors = _list_of(
        params["search-terms"],
        lambda item: _match(_SELECTOR_RE, item, ERR_BAD_SEARCH_TERMS),
        ERR_BAD_SEARCH_TERMS)
    if not 1 <= len(selectors) <= _MAX_SEARCH_TERMS:
        _fail(ERR_BAD_SEARCH_TERMS)
    if params["unknown-packages"] != []:
        _fail(ERR_BAD_UNKNOWN_PACKAGES)
    packages = _list_of(params["packages"], _normalize_row, ERR_BAD_PACKAGES)
    if len(packages) > _MAX_PACKAGES:
        _fail(ERR_BAD_PACKAGES)
    packages.sort(key=lambda row: (row["name"], row["architecture"]))
    identities = {(row["name"], row["architecture"]) for row in packages}
    if len(identities) != len(packages):
        _fail(ERR_DUPLICATE_ROW)
    return {
        "command": params["command"],
        "search-terms": selectors,
        "packages": packages,
    }


def assert_same_transaction(expected, observed):
    """Require exact normalized equality of two frozen transactions.

    Anything at all that differs except the JSON-RPC id and the hook method
    raises ValueError(APT_TXN_TRANSACTION_CHANGED): version strings,
    architectures, modes, the automatic flag, dependency/upgrade shape,
    origin fields and search terms are never normalized away.
    """
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        _fail(ERR_CHANGED)

    def canon(value):
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False)

    try:
        same = canon(expected) == canon(observed)
    except (TypeError, ValueError):
        _fail(ERR_CHANGED)
    if not same:
        _fail(ERR_CHANGED)


_MULTIARCH = ("same", "foreign", "allowed", "none", "no")
_DIRECTIONS = ("<", ">", "=")
_CONFIGURE = "**CONFIGURE**"
_REMOVE = "**REMOVE**"


def _action_path(action):
    if not action.startswith("/") or not action.endswith(".deb"):
        _fail(ERR_PREINSTALL_BAD_FIELD)
    if len(action) > _MAX_PATH:
        _fail(ERR_PREINSTALL_BAD_FIELD)
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in action):
        _fail(ERR_PREINSTALL_BAD_FIELD)
    return action


def _action_side(version, arch, multi):
    if multi not in _MULTIARCH:
        _fail(ERR_PREINSTALL_BAD_FIELD)
    if version == "-":
        if arch != "-" or multi not in ("none", "no"):
            _fail(ERR_PREINSTALL_BAD_FIELD)
        return
    _match(_VERSION_RE, version, ERR_PREINSTALL_BAD_FIELD)
    _match(_ARCH_RE, arch, ERR_PREINSTALL_BAD_FIELD)


def parse_preinstall_v3(raw):
    """Parse the strict bounded DPkg::Pre-Install-Pkgs "VERSION 3" stream.

    First line must be VERSION 3; the CONFIG section up to the first blank
    line is consumed and never returned, stored or echoed; each following
    line carries exactly 9 whitespace-separated action fields
    (name oldversion oldarch oldmulti direction newversion newarch newmulti
    action).  Only package-action fields are returned, in file order.
    Equality with a JSON-hook transaction is NOT claimed here: the parent
    must cross-check expected inputs and archive mapping under the native
    lock.
    """
    if not isinstance(raw, (bytes, bytearray)):
        _fail(ERR_PREINSTALL_MALFORMED)
    raw = bytes(raw)
    if len(raw) > _MAX_RAW:
        _fail(ERR_PREINSTALL_TOO_LARGE)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail(ERR_PREINSTALL_MALFORMED)
    if "\r" in text or "\x00" in text:
        _fail(ERR_PREINSTALL_MALFORMED)
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0] != "VERSION 3":
        _fail(ERR_PREINSTALL_BAD_VERSION)
    index = 1
    while index < len(lines) and lines[index] != "":
        index += 1
    if index == len(lines):
        _fail(ERR_PREINSTALL_MALFORMED)
    rows = []
    seen = set()
    for line in lines[index + 1:]:
        if line == "":
            _fail(ERR_PREINSTALL_MALFORMED)
        fields = line.split()
        if len(fields) != 9:
            _fail(ERR_PREINSTALL_MALFORMED)
        (name, oldversion, oldarch, oldmulti, direction,
         newversion, newarch, newmulti, action) = fields
        _match(_NAME_RE, name, ERR_PREINSTALL_BAD_FIELD)
        if direction not in _DIRECTIONS:
            _fail(ERR_PREINSTALL_BAD_FIELD)
        _action_side(oldversion, oldarch, oldmulti)
        _action_side(newversion, newarch, newmulti)
        if action == "**ERROR**":
            _fail(ERR_PREINSTALL_ERROR_ACTION)
        if action not in (_CONFIGURE, _REMOVE):
            _action_path(action)
        identity = tuple(fields)
        if identity in seen:
            _fail(ERR_PREINSTALL_DUPLICATE_ROW)
        seen.add(identity)
        rows.append({
            "name": name,
            "oldversion": oldversion,
            "oldarch": oldarch,
            "oldmulti": oldmulti,
            "direction": direction,
            "newversion": newversion,
            "newarch": newarch,
            "newmulti": newmulti,
            "action": action,
        })
    return tuple(rows)
