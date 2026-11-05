"""Capital-structure V2 task I1a: retained-byte economic terms (SPEC_I1 §2-§4).

``attach_economic_terms`` is the only path by which a term read out of retained
filing bytes becomes a property of a resolved instrument.  This module owns
three things and nothing else:

* :func:`validate_economic_term_record` — the closed pre-instrument projection
  ``capital_structure.instrument_economic_term.v1`` (§2).  A term occurrence
  carries no key of ``term_integration.INSTRUMENT_IDENTITY_KEYS`` at any depth,
  so it can never mint an identity or a quantity (L444), and it carries no
  float and no non-string number anywhere: an exact decimal string or nothing.
* :func:`validate_term_binding` — ``capital_structure.instrument_term_binding.v1``
  (§3).  Only an ``adjudicated_gold`` binding may join an occurrence to an
  instrument, and only ``instrument_resolution.instrument_id_for`` may name it.
* :func:`attach_economic_terms` — point-in-time visibility, supersession,
  per-(instrument, name) grouping and the admitted / contradicted / unknown
  verdict (§4).

Laws enforced here (gates A09, A19, A25, A27; lines L120, L444):

* Model prose never mints a term.  Only ``canonical_extraction`` — the sealed
  deterministic or deferred procedure — and ``adjudicated_gold`` — an owner
  decision — attach; every other ``fact_origin`` is refused.
* Unknown is never 0 and never unbounded.  A ``deferred`` occurrence (bytes the
  sealed procedure declined to read) surfaces as an ``unknown`` EconomicTerm,
  never as a number, and two values that cannot be ordered by effectiveness
  surface as ONE ``contradicted`` term carrying the union of their evidence:
  this module never picks a winner it cannot justify.
* Attaching is not mutating.  Superseded occurrences stay in the receipt inputs
  as history (A27-compatible), an instrument that receives no term is returned
  byte-identically, and an instrument with no terms at all serialises exactly as
  it did under C0 2.0.0.
* Determinism: any permutation of the records and bindings yields a
  byte-identical InstrumentSet record and receipt.

No score, rank, sizing, probability, capacity or total is produced here, and no
share consequence is computed: :mod:`engine.capital_structure.supply_scenarios`
owns that (SPEC_I1 §5).  ``expiry`` is attached but never evaluated in I1a — a
scenario horizon is not an expiry cut-off.
"""

from __future__ import annotations

import dataclasses
import re
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

from engine.capital_structure.instrument_resolution import instrument_id_for
from engine.capital_structure.issuer_state_contracts import (
    ECONOMIC_TERM_DATE_NAMES,
    ECONOMIC_TERM_EFFECTIVE_NAMES,
    ECONOMIC_TERM_FLAG_NAMES,
    ECONOMIC_TERM_NAMES,
    ECONOMIC_TERM_PRICE_FORMULA_NAMES,
    ECONOMIC_TERM_STRUCTURE_NAMES,
    ECONOMIC_TERM_STRUCTURE_TYPES,
    ECONOMIC_TERM_UNITS,
    TERM_FACT_ORIGINS,
    UNIT_KINDS,
    CalculationReceipt,
    ContractViolation,
    EconomicTerm,
    EvidenceRef,
    InstrumentSet,
    Quantity,
    _DECIMAL,
    _ID,
    sha256_of,
    stable_id,
    structure_from_record,
)
from engine.capital_structure.term_integration import INSTRUMENT_IDENTITY_KEYS

IMPLEMENTATION = "capital_structure.instrument_economics.v1"
TERM_RECORD_SCHEMA = "capital_structure.instrument_economic_term.v1"
TERM_BINDING_SCHEMA = "capital_structure.instrument_term_binding.v1"

#: The only fact origin that may bind an occurrence to an instrument identity.
GOLD_ORIGIN = "adjudicated_gold"

#: Closed key sets (SPEC_I1 §2 and §3).  Anything else is refused, never ignored.
TERM_RECORD_KEYS = (
    "schema",
    "occurrence_id",
    "issuer_id",
    "security_scope",
    "name",
    "value",
    "unit",
    "currency",
    "flag",
    "expression",
    "date_value",
    "evidence",
    "extraction",
    "fact_origin",
    "point_in_time",
    "status",
)
BINDING_RECORD_KEYS = (
    "schema",
    "binding_id",
    "occurrence_id",
    "issuer_id",
    "series_key",
    "instrument_id",
    "fact_origin",
    "decided_at",
    "effective_at",
    "evidence",
    "supersedes",
)
#: I2 (SPEC_I2 §6): an OPTIONAL structured-term reading of an occurrence.  It is
#: deliberately not part of ``TERM_RECORD_KEYS``, which stays the closed set of
#: keys every occurrence carries: a pre-I2 record is byte-identical, and a record
#: with a structure carries exactly one key more.
STRUCTURE_KEY = "structure"
EVIDENCE_KEYS = ("manifest_id", "span_id", "text_sha256")
EXTRACTION_KEYS = ("method", "parser_version")
POINT_IN_TIME_KEYS = ("available_at", "event_time")

EXTRACTION_METHODS = ("deterministic", "deferred")
TERM_RECORD_STATUSES = ("observed", "deferred")

#: Only these instrument statuses may carry economic terms (SPEC_I1 §4.3).
ATTACHABLE_INSTRUMENT_STATUSES = ("outstanding", "amended")
#: Closed reasons a visible binding attaches nothing; each is a receipt fact,
#: never an error and never a new instrument.
UNATTACHED_REASONS = (
    "ambiguous_binding",
    "occurrence_not_visible",
    "retired",
    "unresolved_candidate",
    "absent",
)

#: Mirror of ``term_integration._EXTRACTION_METHOD_ORIGINS``, which is private
#: there and deliberately not imported.  Both sealed procedures carry the
#: canonical origin; ``deferred`` is the procedure declining to read a value, so
#: it is canonical and bears no fact.
EXTRACTION_METHOD_ORIGINS: Mapping[str, str] = {
    "deterministic": "canonical_extraction",
    "deferred": "canonical_extraction",
}

_SHA256_LOWER = re.compile(r"^[0-9a-f]{64}$")
_PARSER_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+:-]{0,99}$")
_PERCENT_NAME = "beneficial_ownership_cap"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


def _identifier(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(_ID.match(value)), f"{label}: identifier required, got {value!r}")
    return value


def _member(value: Any, allowed: tuple, label: str) -> str:
    _require(value in allowed, f"{label}: {value!r} not in {list(allowed)}")
    return value


def _decimal_string(value: Any, label: str) -> str:
    """Exact non-negative decimal string: no float, no exponent, no rounding."""
    _require(isinstance(value, str) and bool(_DECIMAL.match(value)), f"{label}: exact decimal string required, got {value!r}")
    _require(Decimal(value) >= 0, f"{label}: must be nonnegative, got {value!r}")
    return value


def _parsed(value: str, label: str) -> datetime:
    """Timestamps are compared as parsed datetimes, never as strings (C2)."""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractViolation(f"{label}: {value!r} is not an ISO-8601 timestamp") from exc


def _timestamp(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value), f"{label}: ISO-8601 timestamp required")
    parsed = _parsed(value, label)
    _require(parsed.tzinfo is not None, f"{label}: timestamp must carry a timezone")
    return value


def _iso_date(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value), f"{label}: ISO date required")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ContractViolation(f"{label}: {value!r} is not an ISO date") from exc
    return value


def _refuse_numbers(value: Any, path: str = "<root>") -> None:
    """No float and no non-string number anywhere in a pre-instrument record.

    ``bool`` is exempt because ``flag`` is a boolean fact; every other number
    must arrive as an exact decimal string, because a float on this path is a
    silent rounding of a contractual term.
    """
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, (float, int, Decimal, complex)):
        raise ContractViolation(f"{path}: exact decimal strings only, a {type(value).__name__} is refused ({value!r})")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require(isinstance(key, str), f"{path}: non-string key {key!r}")
            _refuse_numbers(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _refuse_numbers(item, f"{path}[{index}]")
        return
    raise ContractViolation(f"{path}: unsupported type {type(value).__name__}")


def _refuse_structure_numbers(value: Any, path: str = "<root>") -> None:
    """No float anywhere in a structured term; exact integers stay exact.

    A structure's day counts, rounding places and period lengths are integers by
    contract (SPEC_I2 §1.5); every MONEY and RATE figure inside one is a
    :class:`Quantity` whose value is an exact decimal string.  A float is still
    refused at every depth, because a float here is a silent rounding of a
    contractual term.
    """
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, (float, Decimal, complex)):
        raise ContractViolation(
            f"{path}: exact integers and decimal strings only, a {type(value).__name__} is refused ({value!r})"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require(isinstance(key, str), f"{path}: non-string key {key!r}")
            _refuse_structure_numbers(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _refuse_structure_numbers(item, f"{path}[{index}]")
        return
    raise ContractViolation(f"{path}: unsupported type {type(value).__name__}")


def _refuse_identity_keys(value: Any, path: str = "<root>") -> None:
    """A term occurrence is pre-instrument: no identity or capacity key at any depth."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require(
                key not in INSTRUMENT_IDENTITY_KEYS,
                f"{path}.{key}: a pre-instrument term record may not carry the instrument identity key {key!r}",
            )
            _refuse_identity_keys(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _refuse_identity_keys(item, f"{path}[{index}]")


def _closed_keys(record: Mapping[str, Any], allowed: tuple, label: str) -> None:
    keys = set(record)
    extra = sorted(keys - set(allowed))
    missing = sorted(set(allowed) - keys)
    _require(not extra, f"{label}: unexpected keys {extra} (closed record)")
    _require(not missing, f"{label}: missing keys {missing} (closed record)")


def _sub_record(value: Any, allowed: tuple, label: str) -> dict[str, Any]:
    _require(isinstance(value, Mapping), f"{label}: mapping required")
    _closed_keys(value, allowed, label)
    return dict(value)


def _evidence_ref(value: Any, label: str) -> dict[str, str]:
    evidence = _sub_record(value, EVIDENCE_KEYS, label)
    manifest_id = _identifier(evidence["manifest_id"], f"{label}.manifest_id")
    span_id = _identifier(evidence["span_id"], f"{label}.span_id")
    text_sha256 = evidence["text_sha256"]
    _require(
        isinstance(text_sha256, str) and bool(_SHA256_LOWER.match(text_sha256)),
        f"{label}.text_sha256: 64 lowercase hex characters required, got {text_sha256!r}",
    )
    return {"manifest_id": manifest_id, "span_id": span_id, "text_sha256": text_sha256}


def _category(name: str) -> str:
    """``quantity``, ``flag``, ``date`` or ``structure``: the categories partition the vocabulary."""
    if name in ECONOMIC_TERM_UNITS:
        return "quantity"
    if name in ECONOMIC_TERM_FLAG_NAMES:
        return "flag"
    if name in ECONOMIC_TERM_DATE_NAMES:
        return "date"
    if name in ECONOMIC_TERM_STRUCTURE_NAMES:
        # I2 (SPEC_I2 §1.3): these five names carry a structure and nothing else.
        return "structure"
    raise ContractViolation(f"economic term name {name!r} has no unit, flag, date or structure category")


def _validated_structure(record: Mapping[str, Any], name: str, label: str) -> Any:
    """Parse and admit one occurrence's ``structure``, or refuse it (SPEC_I2 §6).

    The structure must be the type its name carries, and the five structure-only
    names enter ONLY as ``adjudicated_gold`` (SPEC_I2 §0 item 8): model prose
    never mints a reset, an anti-dilution method, a settlement election, a
    conversion condition or an accrual term.
    """
    raw = record.get(STRUCTURE_KEY)
    if raw is None:
        return None
    _refuse_structure_numbers(raw, f"{label}.{STRUCTURE_KEY}")
    _refuse_identity_keys(raw, f"{label}.{STRUCTURE_KEY}")
    parsed = structure_from_record(raw, f"{label}.{STRUCTURE_KEY}")
    expected = ECONOMIC_TERM_STRUCTURE_TYPES.get(name)
    _require(
        expected is not None,
        f"{label}.{STRUCTURE_KEY}: the term {name!r} carries no structure",
    )
    _require(
        type(parsed).__name__ == expected,
        f"{label}.{STRUCTURE_KEY}: {name!r} carries a {expected}, got {type(parsed).__name__}",
    )
    if name in ECONOMIC_TERM_STRUCTURE_NAMES:
        _require(
            record["fact_origin"] == GOLD_ORIGIN,
            f"{label}.fact_origin: {name!r} enters only as {GOLD_ORIGIN!r}, got {record['fact_origin']!r}",
        )
    elif name in ECONOMIC_TERM_PRICE_FORMULA_NAMES:
        _require(
            parsed.has_market_component or record["value"] is not None,
            f"{label}: an all-fixed price formula states the fixed price it evaluates to",
        )
        _require(
            not parsed.has_market_component or record["value"] is None,
            f"{label}.value: a market price formula is not a fact until the pricing date, "
            "so the occurrence carries its verbatim formula and no value",
        )
    return parsed


def _record_sequence(value: Any, label: str) -> tuple:
    if isinstance(value, (str, bytes, Mapping)):
        raise ContractViolation(f"{label}: a sequence of records is required")
    try:
        return tuple(value)
    except TypeError as exc:
        raise ContractViolation(f"{label}: a sequence of records is required") from exc


def _unique_by(records: tuple, key: str, label: str) -> dict[str, dict[str, Any]]:
    """Index validated records by their digest identity.

    Two different records claiming one identity are a contradiction, never a
    silent last-write: the digest is a function of the record's own identity
    fields, so a collision means one of them is not what it claims to be.
    """
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        _require(isinstance(record, Mapping), f"{label}: mapping required")
        identifier = record[key]
        prior = indexed.get(identifier)
        _require(
            prior is None or prior == dict(record),
            f"{label}: two different records claim {key} {identifier!r}",
        )
        indexed[identifier] = dict(record)
    return indexed


def validate_economic_term_record(record: Any) -> dict[str, Any]:
    """Validate one ``capital_structure.instrument_economic_term.v1`` occurrence.

    Returns a deep copy of the validated record.  Every refusal is a
    :class:`ContractViolation`: a closed record with an exact evidence-derived
    ``occurrence_id``, a unit and currency that follow the term name, a
    ``fact_origin`` the sealed procedure can actually carry, and a payload shape
    that matches its status.  A ``deferred`` record carries no fact at all.
    """
    _require(isinstance(record, Mapping), "instrument_economic_term: mapping required")
    label = "instrument_economic_term"
    _refuse_identity_keys(record)
    has_structure = STRUCTURE_KEY in record
    if has_structure:
        # The structure's own numbers are integers by contract (SPEC_I2 §1.5);
        # every other key keeps the exact-decimal-string-only law.
        _refuse_numbers({key: item for key, item in record.items() if key != STRUCTURE_KEY})
    else:
        _refuse_numbers(record)
    _closed_keys(record, TERM_RECORD_KEYS + ((STRUCTURE_KEY,) if has_structure else ()), label)
    _require(
        record["schema"] == TERM_RECORD_SCHEMA,
        f"{label}.schema: {TERM_RECORD_SCHEMA!r} required, got {record['schema']!r}",
    )
    _identifier(record["issuer_id"], f"{label}.issuer_id")
    _identifier(record["security_scope"], f"{label}.security_scope")
    name = _member(record["name"], ECONOMIC_TERM_NAMES, f"{label}.name")
    category = _category(name)

    value = record["value"]
    if value is not None:
        _decimal_string(value, f"{label}.value")
    unit = record["unit"]
    if category == "quantity":
        expected_unit, _basis = ECONOMIC_TERM_UNITS[name]
        _require(unit == expected_unit, f"{label}.unit: {name!r} is in {expected_unit!r}, got {unit!r}")
    else:
        _require(unit is None, f"{label}.unit: {name!r} carries no unit, got {unit!r}")
    if unit is not None:
        _member(unit, UNIT_KINDS, f"{label}.unit")
    expected_currency = "USD" if unit == "usd" else None
    _require(
        record["currency"] == expected_currency,
        f"{label}.currency: {expected_currency!r} required for unit {unit!r}, got {record['currency']!r}",
    )
    flag = record["flag"]
    if flag is not None:
        _require(isinstance(flag, bool), f"{label}.flag: boolean required, got {flag!r}")
    expression = record["expression"]
    if expression is not None:
        _require(
            isinstance(expression, str) and bool(expression.strip()),
            f"{label}.expression: verbatim formula text required",
        )
    date_value = record["date_value"]
    if date_value is not None:
        _iso_date(date_value, f"{label}.date_value")

    evidence = _evidence_ref(record["evidence"], f"{label}.evidence")
    extraction = _sub_record(record["extraction"], EXTRACTION_KEYS, f"{label}.extraction")
    method = _member(extraction["method"], EXTRACTION_METHODS, f"{label}.extraction.method")
    parser_version = extraction["parser_version"]
    _require(
        isinstance(parser_version, str) and bool(_PARSER_VERSION.match(parser_version)),
        f"{label}.extraction.parser_version: version string required, got {parser_version!r}",
    )
    fact_origin = _member(record["fact_origin"], TERM_FACT_ORIGINS, f"{label}.fact_origin")
    canonical_origin = EXTRACTION_METHOD_ORIGINS[method]
    _require(
        fact_origin in (canonical_origin, GOLD_ORIGIN),
        f"{label}.fact_origin: {fact_origin!r} is neither the {canonical_origin!r} origin of extraction "
        f"method {method!r} nor {GOLD_ORIGIN!r}; model prose never mints a term",
    )

    point_in_time = _sub_record(record["point_in_time"], POINT_IN_TIME_KEYS, f"{label}.point_in_time")
    _timestamp(point_in_time["available_at"], f"{label}.point_in_time.available_at")
    if point_in_time["event_time"] is not None:
        _timestamp(point_in_time["event_time"], f"{label}.point_in_time.event_time")

    status = _member(record["status"], TERM_RECORD_STATUSES, f"{label}.status")
    expected_status = "observed" if method == "deterministic" else "deferred"
    _require(
        status == expected_status,
        f"{label}: extraction method {method!r} requires status {expected_status!r}, got {status!r}",
    )

    occurrence_id = stable_id(
        "econterm",
        {
            "manifest_id": evidence["manifest_id"],
            "span_id": evidence["span_id"],
            "name": name,
            "parser_version": parser_version,
        },
    )
    _require(
        record["occurrence_id"] == occurrence_id,
        f"{label}.occurrence_id: must be the evidence digest {occurrence_id!r}, got {record['occurrence_id']!r}",
    )

    structure = _validated_structure(record, name, label)
    if status == "deferred":
        for field_name, item in (
            ("value", value),
            ("flag", flag),
            ("expression", expression),
            ("date_value", date_value),
            (STRUCTURE_KEY, structure),
        ):
            _require(item is None, f"{label}.{field_name}: a deferred record carries no fact, got {item!r}")
    elif category == "structure":
        _require(structure is not None, f"{label}.{STRUCTURE_KEY}: an observed {name!r} record carries its structure")
        for field_name, item in (
            ("value", value),
            ("flag", flag),
            ("expression", expression),
            ("date_value", date_value),
        ):
            _require(item is None, f"{label}.{field_name}: an observed {name!r} record carries no {field_name}")
    elif category == "quantity":
        _require(flag is None, f"{label}.flag: an observed quantity term carries no flag")
        _require(date_value is None, f"{label}.date_value: an observed quantity term carries no date")
        _require(
            (value is None) != (expression is None),
            f"{label}: an observed quantity term carries exactly one of value or expression, "
            f"got value={value!r} expression={expression!r}",
        )
    elif category == "flag":
        _require(isinstance(flag, bool), f"{label}.flag: an observed permission term carries its boolean")
        _require(value is None, f"{label}.value: an observed permission term carries no quantity")
        _require(expression is None, f"{label}.expression: an observed permission term carries no formula")
        _require(date_value is None, f"{label}.date_value: an observed permission term carries no date")
    else:
        _require(date_value is not None, f"{label}.date_value: an observed expiry carries its ISO date")
        _require(value is None, f"{label}.value: an observed expiry carries no quantity")
        _require(expression is None, f"{label}.expression: an observed expiry carries no formula")
        _require(flag is None, f"{label}.flag: an observed expiry carries no flag")

    if name == _PERCENT_NAME and value is not None:
        # Percentage POINTS (A5): "9.99" means 9.99% = 0.0999, never 9.99x.
        number = Decimal(value)
        _require(
            Decimal(0) < number <= Decimal(100),
            f"{label}.value: a beneficial-ownership cap is percentage points in (0, 100], got {value!r}",
        )
    return deepcopy(dict(record))


def validate_term_binding(record: Any) -> dict[str, Any]:
    """Validate one ``capital_structure.instrument_term_binding.v1`` record.

    A binding is identity, so it follows I0's law: only ``adjudicated_gold`` may
    bind, the ``instrument_id`` must be exactly
    ``instrument_id_for(issuer_id, series_key)`` (never re-derived here), and the
    ``binding_id`` must be the digest of the pair it joins.  Unlike a term
    record, a binding legitimately carries ``instrument_id``.
    """
    _require(isinstance(record, Mapping), "instrument_term_binding: mapping required")
    label = "instrument_term_binding"
    _refuse_numbers(record)
    _closed_keys(record, BINDING_RECORD_KEYS, label)
    _require(
        record["schema"] == TERM_BINDING_SCHEMA,
        f"{label}.schema: {TERM_BINDING_SCHEMA!r} required, got {record['schema']!r}",
    )
    issuer_id = _identifier(record["issuer_id"], f"{label}.issuer_id")
    series_key = _identifier(record["series_key"], f"{label}.series_key")
    occurrence_id = _identifier(record["occurrence_id"], f"{label}.occurrence_id")
    instrument_id = _identifier(record["instrument_id"], f"{label}.instrument_id")
    expected_instrument_id = instrument_id_for(issuer_id, series_key)
    _require(
        instrument_id == expected_instrument_id,
        f"{label}.instrument_id: must be instrument_id_for({issuer_id!r}, {series_key!r}) = "
        f"{expected_instrument_id!r}, got {instrument_id!r}",
    )
    fact_origin = record["fact_origin"]
    _require(
        fact_origin == GOLD_ORIGIN,
        f"{label}.fact_origin: only {GOLD_ORIGIN!r} may bind a term to an instrument, got {fact_origin!r}",
    )
    _timestamp(record["decided_at"], f"{label}.decided_at")
    _timestamp(record["effective_at"], f"{label}.effective_at")

    evidence = record["evidence"]
    _require(
        isinstance(evidence, (list, tuple)) and len(evidence) > 0,
        f"{label}.evidence: a non-empty list of retained-byte references is required",
    )
    for index, item in enumerate(evidence):
        _evidence_ref(item, f"{label}.evidence[{index}]")

    supersedes = record["supersedes"]
    _require(isinstance(supersedes, (list, tuple)), f"{label}.supersedes: a list of binding ids is required")
    for index, item in enumerate(supersedes):
        _identifier(item, f"{label}.supersedes[{index}]")
    superseded_ids = [str(item) for item in supersedes]
    _require(
        len(set(superseded_ids)) == len(superseded_ids),
        f"{label}.supersedes: duplicate binding ids {sorted(superseded_ids)}",
    )

    binding_id = stable_id("termbind", {"occurrence_id": occurrence_id, "instrument_id": instrument_id})
    _require(
        record["binding_id"] == binding_id,
        f"{label}.binding_id: must be the digest {binding_id!r}, got {record['binding_id']!r}",
    )
    _require(binding_id not in superseded_ids, f"{label}.supersedes: a binding may not supersede itself")
    return deepcopy(dict(record))


# ---------------------------------------------------------------------------
# EconomicTerm construction (SPEC_I1 §4.4)
# ---------------------------------------------------------------------------


def _evidence_union(records: Sequence[Mapping[str, Any]]) -> tuple[EvidenceRef, ...]:
    """Deduplicated, sorted union of the members' retained-byte references."""
    keys = {
        (
            record["evidence"]["manifest_id"],
            record["evidence"]["span_id"],
            record["evidence"]["text_sha256"],
        )
        for record in records
    }
    return tuple(EvidenceRef(manifest_id, span_id, text_sha256) for manifest_id, span_id, text_sha256 in sorted(keys))


def _interpretation_version(records: Sequence[Mapping[str, Any]]) -> str:
    return "+".join(sorted({record["extraction"]["parser_version"] for record in records}))


def _fact_origin(records: Sequence[Mapping[str, Any]]) -> str:
    if any(record["fact_origin"] == GOLD_ORIGIN for record in records):
        return GOLD_ORIGIN
    return "canonical_extraction"


def _extreme_timestamp(records: Sequence[Mapping[str, Any]], field: str, *, latest: bool) -> str | None:
    """Verbatim ``available_at``/``event_time`` of one extreme instant.

    Members are walked in ``occurrence_id`` order and the comparison is strict,
    so two records naming the same instant in different spellings always resolve
    to the smallest occurrence id: the output never depends on input order.
    """
    best_instant: datetime | None = None
    best_value: str | None = None
    for record in sorted(records, key=lambda item: item["occurrence_id"]):
        raw = record["point_in_time"][field]
        if raw is None:
            continue
        instant = _parsed(raw, f"point_in_time.{field}")
        if best_instant is None or ((instant > best_instant) if latest else (instant < best_instant)):
            best_instant, best_value = instant, raw
    return best_value


def _earliest_available(records: Sequence[Mapping[str, Any]]) -> str:
    available_at = _extreme_timestamp(records, "available_at", latest=False)
    _require(available_at is not None, "economic term: a member carries no available_at")
    return available_at


def _latest_available(records: Sequence[Mapping[str, Any]]) -> str:
    available_at = _extreme_timestamp(records, "available_at", latest=True)
    _require(available_at is not None, "economic term: a member carries no available_at")
    return available_at


def _effective_at(records: Sequence[Mapping[str, Any]]) -> str | None:
    """The group's effective instant: the latest one any member states."""
    return _extreme_timestamp(records, "event_time", latest=True)


def _structure_key(record: Mapping[str, Any]) -> str | None:
    """The canonical digest of an occurrence's structure, or ``None``.

    Two structures are the same reading only if their canonical JSON is, so a
    conflicting structure at the same ``effective_at`` is a contradiction this
    module reports rather than a winner it picks (SPEC_I1 §4.4, SPEC_I2 §6).
    """
    structure = record.get(STRUCTURE_KEY)
    return None if structure is None else sha256_of(_record_of(structure))


def _record_of(value: Any) -> Any:
    return value.as_record() if hasattr(value, "as_record") else value


def _value_key(record: Mapping[str, Any], name: str) -> tuple:
    """The identity of a stated value, used to decide whether members disagree.

    ``Decimal`` comparison makes "1.50" and "1.5" one value; a formula is
    compared verbatim, because two spellings of a formula are two readings.  An
    I2 structure is part of that identity: the same number under a different
    reset schedule is a different reading of the contract.
    """
    category = _category(name)
    structure = _structure_key(record)
    if category == "structure":
        return ("structure", structure)
    if category == "quantity":
        if record["value"] is not None:
            base: tuple = ("value", Decimal(record["value"]))
        else:
            base = ("expression", record["expression"])
        return base if structure is None else base + ("structure", structure)
    if category == "flag":
        return ("flag", record["flag"])
    return ("date_value", record["date_value"])


def _counts_as_observed(record: Mapping[str, Any], name: str) -> bool:
    """Whether a member states a fact the group may admit.

    A ``deferred`` record states nothing.  An ``observed`` record of a price or
    ratio name with no ``event_time`` also states nothing admissible: an
    undated price cannot be tested against a split (A19), so it is treated
    exactly like a deferred record rather than admitted as a timeless number.
    """
    if record["status"] != "observed":
        return False
    if name in ECONOMIC_TERM_EFFECTIVE_NAMES and record["point_in_time"]["event_time"] is None:
        return False
    return True


def _term_value(name: str, status: str, record: Mapping[str, Any] | None) -> Quantity | None:
    if name not in ECONOMIC_TERM_UNITS:
        return None
    unit, basis = ECONOMIC_TERM_UNITS[name]
    if status == "contradicted":
        return Quantity(unit=unit, status="contradicted", share_basis=basis)
    if status == "unknown":
        return Quantity.unknown(unit, share_basis=basis)
    assert record is not None
    if record["value"] is not None:
        return Quantity.known(record["value"], unit, share_basis=basis)
    # An admitted verbatim formula carries no number: the quantity stays unknown
    # and the formula text is retained exactly as written (I2 owns resets/floors).
    return Quantity.unknown(unit, share_basis=basis)


def _admitted_term(instrument_id: str, name: str, records: Sequence[Mapping[str, Any]]) -> EconomicTerm:
    smallest = min(records, key=lambda item: item["occurrence_id"])
    category = _category(name)
    return EconomicTerm(
        term_id=smallest["occurrence_id"],
        instrument_id=instrument_id,
        name=name,
        status="admitted",
        value=_term_value(name, "admitted", smallest),
        flag=smallest["flag"] if category == "flag" else None,
        expression=smallest["expression"] if category == "quantity" else None,
        date_value=smallest["date_value"] if category == "date" else None,
        evidence=_evidence_union(records),
        fact_origin=_fact_origin(records),
        interpretation_version=_interpretation_version(records),
        available_at=_earliest_available(records),
        effective_at=_effective_at(records),
        structure=_admitted_structure(name, records),
    )


def _admitted_structure(name: str, records: Sequence[Mapping[str, Any]]) -> Any:
    """The structure an admitted term carries, parsed from its winning record."""
    if _category(name) not in ("structure", "quantity"):
        return None
    smallest = min(records, key=lambda item: item["occurrence_id"])
    raw = smallest.get(STRUCTURE_KEY)
    if raw is None:
        return None
    return structure_from_record(raw, f"instrument_economic_term[{smallest['occurrence_id']}].{STRUCTURE_KEY}")


def _contradicted_term(
    instrument_id: str,
    name: str,
    records: Sequence[Mapping[str, Any]],
    effective_at: str | None,
) -> EconomicTerm:
    """ONE term naming the contradiction; a winner is never picked (§4.4)."""
    occurrence_ids = sorted(record["occurrence_id"] for record in records)
    return EconomicTerm(
        term_id=stable_id("econterm-conflict", occurrence_ids),
        instrument_id=instrument_id,
        name=name,
        status="contradicted",
        value=_term_value(name, "contradicted", None),
        flag=None,
        expression=None,
        date_value=None,
        evidence=_evidence_union(records),
        fact_origin=_fact_origin(records),
        interpretation_version=_interpretation_version(records),
        available_at=_latest_available(records),
        effective_at=effective_at,
    )


def _unknown_term(instrument_id: str, name: str, records: Sequence[Mapping[str, Any]]) -> EconomicTerm:
    """Deferred bytes: an ``unknown`` term, never 0 and never unbounded."""
    smallest = min(records, key=lambda item: item["occurrence_id"])
    return EconomicTerm(
        term_id=smallest["occurrence_id"],
        instrument_id=instrument_id,
        name=name,
        status="unknown",
        value=_term_value(name, "unknown", None),
        flag=None,
        expression=None,
        date_value=None,
        evidence=_evidence_union(records),
        fact_origin=_fact_origin(records),
        interpretation_version=_interpretation_version(records),
        available_at=_earliest_available(records),
        effective_at=None,
    )


def _group_term(instrument_id: str, name: str, records: Sequence[Mapping[str, Any]]) -> tuple[EconomicTerm, list[dict[str, Any]]]:
    """One term for one (instrument, name) group plus its superseded history."""
    observed = [record for record in records if _counts_as_observed(record, name)]
    if not observed:
        return _unknown_term(instrument_id, name, records), []
    if len({_value_key(record, name) for record in observed}) == 1:
        return _admitted_term(instrument_id, name, observed), []
    if any(record["point_in_time"]["event_time"] is None for record in observed):
        # Values differ and cannot be ordered by effectiveness: one contradicted
        # term over the whole group, with no effective instant claimed.
        return _contradicted_term(instrument_id, name, observed, None), []
    latest = max(_parsed(record["point_in_time"]["event_time"], "point_in_time.event_time") for record in observed)
    winners = [
        record
        for record in observed
        if _parsed(record["point_in_time"]["event_time"], "point_in_time.event_time") == latest
    ]
    winner_ids = {record["occurrence_id"] for record in winners}
    history = [
        {
            "instrument_id": instrument_id,
            "name": name,
            "occurrence_id": record["occurrence_id"],
            "effective_at": record["point_in_time"]["event_time"],
        }
        for record in observed
        if record["occurrence_id"] not in winner_ids
    ]
    if len({_value_key(record, name) for record in winners}) == 1:
        return _admitted_term(instrument_id, name, winners), history
    # The latest effective instant itself states several values: contradicted,
    # dated at that instant, and the earlier occurrences stay as history.
    return _contradicted_term(instrument_id, name, winners, _effective_at(winners)), history


def attach_economic_terms(
    instruments: InstrumentSet,
    term_records: Any,
    bindings: Any,
    as_of: str,
) -> InstrumentSet:
    """Attach validated, bound, visible term occurrences to resolved instruments.

    Returns a NEW :class:`InstrumentSet` whose instruments carry
    ``economic_terms`` sorted by ``(name, term_id)`` and whose receipt digests
    exactly what was visible, what bound, what attached to nothing and what was
    superseded.  Instruments keep the set's order (an InstrumentSet does not
    sort); an instrument that receives no term is returned byte-identically, and
    no instrument is ever created, retired or mutated here.
    """
    _require(isinstance(instruments, InstrumentSet), "attach_economic_terms.instruments: an InstrumentSet is required")
    as_of = _timestamp(as_of, "attach_economic_terms.as_of")
    cutoff = _parsed(as_of, "attach_economic_terms.as_of")
    snapshot = _parsed(instruments.as_of, "instrument_set.as_of")
    _require(
        cutoff <= snapshot,
        f"attach_economic_terms.as_of: {as_of!r} is later than the instrument snapshot "
        f"{instruments.as_of!r}; a term may not be attached ahead of the identity snapshot",
    )

    occurrences = _unique_by(
        tuple(
            validate_economic_term_record(record)
            for record in _record_sequence(term_records, "attach_economic_terms.term_records")
        ),
        "occurrence_id",
        "instrument_economic_term",
    )
    binding_records = _unique_by(
        tuple(
            validate_term_binding(record)
            for record in _record_sequence(bindings, "attach_economic_terms.bindings")
        ),
        "binding_id",
        "instrument_term_binding",
    )
    for record in occurrences.values():
        _require(
            record["issuer_id"] == instruments.issuer_id,
            f"instrument_economic_term[{record['occurrence_id']}]: issuer {record['issuer_id']!r} differs "
            f"from the instrument set issuer {instruments.issuer_id!r}",
        )
    for record in binding_records.values():
        _require(
            record["issuer_id"] == instruments.issuer_id,
            f"instrument_term_binding[{record['binding_id']}]: issuer {record['issuer_id']!r} differs "
            f"from the instrument set issuer {instruments.issuer_id!r}",
        )

    # §4.2 point-in-time visibility, compared as instants and never as strings.
    visible_occurrences = {
        occurrence_id: record
        for occurrence_id, record in occurrences.items()
        if _parsed(record["point_in_time"]["available_at"], "point_in_time.available_at") <= cutoff
    }
    visible_bindings = {
        binding_id: record
        for binding_id, record in binding_records.items()
        if _parsed(record["decided_at"], "decided_at") <= cutoff
        and _parsed(record["effective_at"], "effective_at") <= cutoff
    }
    # §3: a visible binding named in another visible binding's ``supersedes`` is
    # dropped.  The drop is a receipt fact, never a deletion of the record.
    superseded_names = {name for record in visible_bindings.values() for name in record["supersedes"]}
    superseded_bindings = sorted(binding_id for binding_id in visible_bindings if binding_id in superseded_names)
    effective_bindings = {
        binding_id: record
        for binding_id, record in visible_bindings.items()
        if binding_id not in superseded_names
    }

    # C3: one occurrence bound to two different instruments binds to neither.
    bound_targets: dict[str, set[str]] = {}
    for record in effective_bindings.values():
        bound_targets.setdefault(record["occurrence_id"], set()).add(record["instrument_id"])
    ambiguous = {occurrence_id for occurrence_id, targets in bound_targets.items() if len(targets) > 1}

    by_id = {item.instrument_id: item for item in instruments.instruments}
    unattached: list[dict[str, str]] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for binding_id in sorted(effective_bindings):
        record = effective_bindings[binding_id]
        occurrence_id = record["occurrence_id"]
        instrument_id = record["instrument_id"]
        reason = _unattached_reason(occurrence_id, instrument_id, ambiguous, visible_occurrences, by_id)
        if reason is not None:
            unattached.append({"binding_id": binding_id, "instrument_id": instrument_id, "reason": reason})
            continue
        occurrence = visible_occurrences[occurrence_id]
        groups.setdefault((instrument_id, occurrence["name"]), []).append(occurrence)

    terms_by_instrument: dict[str, list[EconomicTerm]] = {}
    superseded: list[dict[str, Any]] = []
    for instrument_id, name in sorted(groups):
        term, history = _group_term(instrument_id, name, groups[(instrument_id, name)])
        terms_by_instrument.setdefault(instrument_id, []).append(term)
        superseded.extend(history)

    attached_instruments = []
    for instrument in instruments.instruments:
        terms = terms_by_instrument.get(instrument.instrument_id)
        if not terms:
            # Byte-identical: the same frozen object, so the same record digest.
            attached_instruments.append(instrument)
            continue
        ordered = tuple(sorted(terms, key=lambda item: (item.name, item.term_id)))
        attached_instruments.append(dataclasses.replace(instrument, economic_terms=ordered))

    inputs = {
        "instrument_set_receipt_id": instruments.receipt.receipt_id,
        "as_of": as_of,
        "term_ids": sorted(visible_occurrences),
        "binding_ids": sorted(effective_bindings),
        "unattached": sorted(
            unattached,
            key=lambda item: (item["binding_id"], item["instrument_id"], item["reason"]),
        ),
        "superseded": sorted(
            superseded,
            key=lambda item: (
                item["instrument_id"],
                item["name"],
                item["occurrence_id"],
                item["effective_at"] or "",
            ),
        ),
        "superseded_bindings": superseded_bindings,
    }
    receipt = CalculationReceipt.build(
        inputs=inputs,
        rule_digest=sha256_of(ECONOMIC_TERM_NAMES),
        implementation=IMPLEMENTATION,
        computed_at=as_of,
    )
    return dataclasses.replace(instruments, instruments=tuple(attached_instruments), receipt=receipt)


def _unattached_reason(
    occurrence_id: str,
    instrument_id: str,
    ambiguous: set[str],
    visible_occurrences: Mapping[str, Mapping[str, Any]],
    by_id: Mapping[str, Any],
) -> str | None:
    """Why one effective binding attaches nothing; ``None`` when it attaches."""
    if occurrence_id in ambiguous:
        return "ambiguous_binding"
    if occurrence_id not in visible_occurrences:
        return "occurrence_not_visible"
    instrument = by_id.get(instrument_id)
    if instrument is None:
        return "absent"
    if instrument.status not in ATTACHABLE_INSTRUMENT_STATUSES:
        # Exactly "retired" or "unresolved_candidate": neither may carry a term.
        return str(instrument.status)
    return None


__all__ = [
    "ATTACHABLE_INSTRUMENT_STATUSES",
    "BINDING_RECORD_KEYS",
    "EVIDENCE_KEYS",
    "EXTRACTION_KEYS",
    "EXTRACTION_METHODS",
    "EXTRACTION_METHOD_ORIGINS",
    "GOLD_ORIGIN",
    "IMPLEMENTATION",
    "POINT_IN_TIME_KEYS",
    "STRUCTURE_KEY",
    "TERM_BINDING_SCHEMA",
    "TERM_RECORD_KEYS",
    "TERM_RECORD_SCHEMA",
    "TERM_RECORD_STATUSES",
    "UNATTACHED_REASONS",
    "attach_economic_terms",
    "validate_economic_term_record",
    "validate_term_binding",
]
