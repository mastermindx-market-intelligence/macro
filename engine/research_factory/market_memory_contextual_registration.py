"""Strict, outcome-blind E0 control metadata validation.

These pure functions validate grammar, byte identity and inter-record joins. They
do not read private stores, authenticate an owner, issue a capability, publish a
registration or authorize label access. Operational admission additionally needs
complete domain manifests, a genuine installed owner and independent closure,
current access history, and exact durable reservations. A syntactically valid
record set is never evidence that any of those effects occurred.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker, validators

from .ledger import _freeze_exact_json_object


KINDS = ("registration", "installed_binding", "publication", "prelabel_closure", "access_state")
SCHEMAS = {kind: f"research_factory.market_memory_e0_{kind}.v1" for kind in KINDS}
MAX_CONTROL_BYTES = 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 20000
_CLOCK = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z")
_ID_KEYS = {
    "study_id", "closure_id", "publication_id", "installation_id", "namespace_id",
    "installation_epoch", "access_state_id", "object_id", "schema",
}
_CLOCK_KEYS = {"registered_at", "closed_at", "published_at", "installed_at", "expires_at", "recorded_at"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_INTEGER_VALIDATOR = validators.extend(
    Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", lambda _checker, value: type(value) is int
    ),
)


class E0ControlError(ValueError):
    """E0 metadata is malformed or its identities/clocks disagree."""


def _clock(value: object) -> datetime:
    if type(value) is not str or _CLOCK.fullmatch(value) is None:
        raise E0ControlError("canonical_microsecond_utc_clock_required")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise E0ControlError("invalid_calendar_clock") from exc
    if parsed.isoformat(timespec="microseconds").replace("+00:00", "Z") != value:
        raise E0ControlError("clock_roundtrip_mismatch")
    return parsed


def _bounded_tree(value: object) -> None:
    active: set[int] = set()
    nodes = 0

    def visit(item: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise E0ControlError("control_metadata_complexity_limit")
        if type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise E0ControlError("invalid_unicode") from exc
            if len(item) > MAX_CONTROL_BYTES:
                raise E0ControlError("control_string_limit")
            return
        if item is None or type(item) in (bool, int):
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise E0ControlError("nonfinite_number")
            return
        if type(item) not in (dict, list):
            raise E0ControlError("exact_json_native_types_required")
        identity = id(item)
        if identity in active:
            raise E0ControlError("cyclic_metadata")
        active.add(identity)
        try:
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        raise E0ControlError("exact_string_keys_required")
                    visit(key, depth + 1)
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
        finally:
            active.remove(identity)

    visit(value, 0)


def _snapshot(value: object) -> tuple[dict, bytes]:
    _bounded_tree(value)
    try:
        detached, body = _freeze_exact_json_object(value, label="e0_control")
    except ValueError as exc:
        raise E0ControlError("exact_control_object_required") from exc
    if len(body) > MAX_CONTROL_BYTES:
        raise E0ControlError("control_metadata_byte_limit")
    return detached, body


@lru_cache(maxsize=len(KINDS))
def _validator(kind: str):
    if kind not in SCHEMAS:
        raise E0ControlError("unsupported_control_kind")
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "market_memory" / f"e0_{kind}.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return _INTEGER_VALIDATOR(schema, format_checker=FormatChecker())


def validate_e0_control_record(value: object, *, kind: str) -> dict:
    """Return detached validated metadata; this never establishes admission."""
    if type(kind) is not str or kind not in SCHEMAS:
        raise E0ControlError("unsupported_control_kind")
    detached, _body = _snapshot(value)
    error = next(_validator(kind).iter_errors(detached), None)
    if error is not None:
        # Do not echo supplied bodies, identifiers, paths or arbitrary values.
        raise E0ControlError("control_schema_violation")

    def semantics(item: object) -> None:
        if type(item) is list:
            for child in item:
                semantics(child)
        elif type(item) is dict:
            if set(item) == {"schema", "object_id", "sha256", "bytes"}:
                if re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is None:
                    raise E0ControlError("exact_reference_digest_required")
            for key, child in item.items():
                if key in _ID_KEYS and (type(child) is not str or _ID.fullmatch(child) is None):
                    raise E0ControlError("bounded_identifier_required")
                if key in _CLOCK_KEYS:
                    _clock(child)
                semantics(child)

    semantics(detached)
    if kind == "installed_binding":
        if _clock(detached["installed_at"]) >= _clock(detached["expires_at"]):
            raise E0ControlError("installation_expiry_order")
        if not {"read_e0_registration", "disclose_e0_registration"} <= set(detached["permitted_actions"]):
            raise E0ControlError("registration_metadata_actions_required")
    elif kind == "access_state":
        budget = detached["budget"]
        used = budget["consumed_looks"] + budget["reserved_looks"]
        if used > budget["maximum_looks"]:
            raise E0ControlError("access_budget_overcommitted")
        if (detached["sequence"] == 0) != (detached["previous_state_ref"] is None):
            raise E0ControlError("access_predecessor_required")
    elif kind == "prelabel_closure":
        refs = detached["checked_objects"]
        if len({r["sha256"] for r in refs}) != len(refs):
            raise E0ControlError("closure_duplicate_object_digest")
    return detached


def validate_e0_registration(value: object) -> dict:
    """Validate the frozen study's control envelope, not domain completeness."""
    return validate_e0_control_record(value, kind="registration")


def parse_e0_control_record(body: bytes, *, kind: str) -> dict:
    """Parse exact canonical bytes, rejecting duplicates and representation drift."""
    if type(body) is not bytes or not 0 < len(body) <= MAX_CONTROL_BYTES:
        raise E0ControlError("bounded_control_bytes_required")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise E0ControlError("duplicate_json_key")
            result[key] = value
        return result

    def nonfinite(_value):
        raise E0ControlError("nonfinite_number")

    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise E0ControlError("invalid_control_json") from exc
    detached = validate_e0_control_record(value, kind=kind)
    if _snapshot(detached)[1] != body:
        raise E0ControlError("noncanonical_control_bytes")
    return detached


def _record_ref(record: dict, kind: str) -> dict:
    id_key = {"registration": "study_id", "prelabel_closure": "closure_id", "publication": "publication_id"}[kind]
    _detached, body = _snapshot(record)
    return {"schema": SCHEMAS[kind], "object_id": record[id_key],
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def validate_e0_control_join(*, registration: object, closure: object,
                             publication: object, installation: object,
                             access: object, as_of: str) -> dict:
    """Check five-record consistency without authenticating or granting access.

    The explicit as_of is a caller's diagnostic time, not trusted owner time.
    References to domain/provenance objects are intentionally not resolved here.
    """
    supplied = {"registration": registration, "prelabel_closure": closure,
                "publication": publication, "installed_binding": installation,
                "access_state": access}
    records = {kind: validate_e0_control_record(value, kind=kind) for kind, value in supplied.items()}
    reg = records["registration"]
    closed = records["prelabel_closure"]
    pub = records["publication"]
    bound = records["installed_binding"]
    state = records["access_state"]
    now = _clock(as_of)
    if any(record["study_id"] != reg["study_id"] for record in records.values()):
        raise E0ControlError("study_identity_mismatch")
    expected_reg = _record_ref(reg, "registration")
    expected_closure = _record_ref(closed, "prelabel_closure")
    expected_publication = _record_ref(pub, "publication")
    if any(record["registration_ref"] != expected_reg for record in (closed, pub, bound, state)):
        raise E0ControlError("registration_reference_mismatch")
    if any(record["closure_ref"] != expected_closure for record in (pub, bound)):
        raise E0ControlError("closure_reference_mismatch")
    if any(record["publication_ref"] != expected_publication for record in (bound, state)):
        raise E0ControlError("publication_reference_mismatch")
    if pub["namespace_id"] != bound["namespace_id"] or any(record["installation_epoch"] != bound["installation_epoch"] for record in (pub, state)):
        raise E0ControlError("installed_namespace_epoch_mismatch")
    if any(state[key] != bound[key] for key in ("installation_id", "access_state_id")):
        raise E0ControlError("access_installation_mismatch")
    if any(record["owner_principal_ref"] != bound["owner_principal_ref"] for record in (pub, state)):
        raise E0ControlError("owner_identity_mismatch")
    times = [_clock(reg["registered_at"]), _clock(closed["closed_at"]),
             _clock(pub["published_at"]), _clock(bound["installed_at"]),
             _clock(state["recorded_at"]), now]
    if times != sorted(times) or now >= _clock(bound["expires_at"]):
        raise E0ControlError("control_clock_order_or_expiry")
    return {"schema": "research_factory.market_memory_e0_control_consistency.v1",
            "authority": "display_only", "study_id": reg["study_id"],
            "registration_ref": expected_reg, "closure_ref": expected_closure,
            "publication_ref": expected_publication,
            "metadata_consistent": True, "operational_admission": False,
            "unverified_obligations": ["complete_domain_manifests", "authenticated_owner_installation",
                "independent_prelabel_closure", "current_access_history", "exact_durable_reservation"]}
