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


# Existing frozen artifacts, not a new registry or an installation authority.
# Their original bytes include formatting (and, for the guide, Markdown).
_FROZEN_DOMAIN_DIGESTS = {
    "membership": "2b03cb59f2d2f8bca61d5cc7223b1f40c1f58a99df80908a223025e425ff66d6",
    "design": "5821074f0ad1564780759a7e5d7ca6595cd8d411f119629f31ee431f2a481ca6",
    "annotation_guide": "4efc664f6c86f5af6a62ac4fd8b98ae37ae130fa18ecfa7bdf0a88b399a71696",
    "prelabel_binding": "ae8bb3987cce1555851ec91782aeb7e742d3222777ef2762722744f66540b65e",
}
_FROZEN_JSON_SCHEMAS = {
    "market_memory.e0_original_owner_metadata_membership.v1": "membership",
    "market_memory.research_protocol_design.v1": "design",
    "market_memory.e0_prelabel_design_binding.v1": "prelabel_binding",
}
MAX_DOMAIN_OBJECTS = 64
MAX_DOMAIN_OBJECT_BYTES = 4 * 1024 * 1024  # Existing reference-schema ceiling.
MAX_DOMAIN_TOTAL_BYTES = 32 * 1024 * 1024
_DOMAIN_KEYS = ("tasks_ref", "source_coverage_ref", "interval_split_ref", "design_ref",
                "reviewer_plan_ref", "outcome_definition_ref", "metrics_ref", "access_rules_ref")
_REFERENCE_KEYS = {"schema", "object_id", "sha256", "bytes"}
_TASK_SCHEMA = "research_factory.market_memory_e0_tasks.v1"


@lru_cache(maxsize=1)
def _task_validator():
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "market_memory" / "e0_tasks.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return _INTEGER_VALIDATOR(schema, format_checker=FormatChecker())


def _validate_task_bindings(value: object, body: bytes, membership: dict | None) -> dict:
    """Bind supplied task metadata, never certify a question or its answer.

    The frozen corpus contains query candidates, not an actual task selection.
    Questions/facets here are caller-supplied declarations. Neither their digest
    nor a matching source identity establishes answerability, entailment,
    usefulness, independent samples, source rights or prelabel registration.
    """
    detached, canonical = _snapshot(value)
    if next(_task_validator().iter_errors(detached), None) is not None:
        raise E0ControlError("task_schema_violation")
    if canonical != body:
        raise E0ControlError("noncanonical_task_bytes")
    tasks = detached["tasks"]
    identifiers = [detached["object_id"]]
    identifiers += [task["task_id"] for task in tasks]
    identifiers += [facet for task in tasks for facet in task["required_facet_ids"]]
    if any(_ID.fullmatch(identifier) is None for identifier in identifiers):
        raise E0ControlError("task_bounded_identifier_required")
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise E0ControlError("duplicate_task_identity")
    rows = {row["query_id"]: row for row in membership["query_candidates"]} if membership else None
    identity_keys = ("query_id", "context_id", "capture_id", "packet_sha256")

    def source(ref: dict, cutoff: datetime) -> dict:
        row = rows.get(ref["query_id"])
        if row is None or any(ref[key] != row[key] for key in identity_keys):
            raise E0ControlError("task_frozen_source_identity_mismatch")
        if _clock(row["first_available_for_contextual_analysis"]) > cutoff:
            raise E0ControlError("task_source_unavailable_at_cutoff")
        return row

    for task in tasks:
        cutoff = _clock(task["analysis_cutoff"])
        if any(re.fullmatch(r"mmsecurity_[a-f0-9]{64}", task[key]) is None
               for key in ("subject_id", "instrument_id")):
            raise E0ControlError("task_exact_subject_identity_required")
        for ref in [task, *task["original_evidence"]]:
            for key, prefix in (("query_id", "mmquery_"), ("context_id", "mmctx_"),
                                ("capture_id", "mmcapture_"), ("packet_sha256", "")):
                if re.fullmatch(prefix + r"[a-f0-9]{64}", ref[key]) is None:
                    raise E0ControlError("task_exact_source_identity_required")
        if not task["question"].strip():
            raise E0ControlError("task_question_required")
        if hashlib.sha256(task["question"].encode("utf-8")).hexdigest() != task["question_sha256"]:
            raise E0ControlError("task_question_digest_mismatch")
        if rows is not None:
            row = source(task, cutoff)
            if any(task[key] != row["subject"][key] for key in ("subject_id", "instrument_id")):
                raise E0ControlError("task_frozen_subject_identity_mismatch")
            for evidence in task["original_evidence"]:
                source(evidence, cutoff)
    return {"schema": _TASK_SCHEMA, "object_id": detached["object_id"],
            "task_count": len(tasks), "question_bytes_bound": True,
            "frozen_source_bindings_checked": rows is not None,
            "unresolved": [] if rows is not None else ["frozen_membership_bytes"],
            "actual_task_selection_verified": False, "answerability_verified": False,
            "usefulness_verified": False}


def _domain_reference(value: object) -> dict:
    if (type(value) is not dict or set(value) != _REFERENCE_KEYS
            or any(type(value.get(key)) is not str or _ID.fullmatch(value[key]) is None
                   for key in ("schema", "object_id"))
            or type(value.get("sha256")) is not str
            or re.fullmatch(r"[a-f0-9]{64}", value["sha256"]) is None
            or type(value.get("bytes")) is not int
            or not 1 <= value["bytes"] <= MAX_DOMAIN_OBJECT_BYTES):
        raise E0ControlError("exact_domain_reference_required")
    return dict(value)


def _domain_json(body: bytes) -> object:
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise E0ControlError("duplicate_domain_json_key")
            result[key] = value
        return result

    def nonfinite(_value):
        raise E0ControlError("nonfinite_domain_number")

    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        _bounded_tree(value)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise E0ControlError("invalid_domain_json") from exc
    return value


def resolve_e0_domain_references(*, registration: object, objects: object,
                                 prelabel_design: bytes | None = None) -> dict:
    """Resolve supplied exact bytes; never fetch, publish or admit a study.

    ``objects`` is a bounded native dict of SHA-256 -> bytes, NOT paths, URLs,
    readers or grants. Missing referenced bytes are unresolved; inconsistent
    supplied bytes/references raise E0ControlError. New metadata is not
    interpreted without an existing payload contract. Original
    frozen JSON retains its exact pinned representation and is parsed strictly;
    code/text and unknown schemas stay opaque, never imported or executed.
    The optional original prelabel_design bytes are a diagnostic input, never
    a substitute for a registration reference or a reviewer plan. They share
    the object/byte bounds. Only registration references and known guide digest
    links are followed; this is not a recursive object loader.

    The known task contract checks supplied question bytes, exact frozen source
    identities and original availability clocks. It does not select actual tasks
    or establish answerability/usefulness. Splits, reviewers and allocation still
    lack payload contracts; reference closure never certifies admission.
    """
    reg = validate_e0_registration(registration)
    extra = int(prelabel_design is not None)
    if type(objects) is not dict or len(objects) + extra > MAX_DOMAIN_OBJECTS:
        raise E0ControlError("bounded_domain_objects_required")
    if prelabel_design is not None and (type(prelabel_design) is not bytes
            or not 0 < len(prelabel_design) <= MAX_DOMAIN_OBJECT_BYTES):
        raise E0ControlError("bounded_prelabel_design_bytes_required")
    total = len(prelabel_design) if prelabel_design is not None else 0
    if total > MAX_DOMAIN_TOTAL_BYTES:
        raise E0ControlError("aggregate_domain_byte_limit")
    for digest, body in objects.items():
        if (type(digest) is not str or re.fullmatch(r"[a-f0-9]{64}", digest) is None
                or type(body) is not bytes or not 0 < len(body) <= MAX_DOMAIN_OBJECT_BYTES):
            raise E0ControlError("bounded_domain_bytes_required")
        total += len(body)
        if total > MAX_DOMAIN_TOTAL_BYTES:
            raise E0ControlError("aggregate_domain_byte_limit")

    roots = [("corpus.membership_ref", reg["corpus"]["membership_ref"])]
    roots += [(key, reg[key]) for key in _DOMAIN_KEYS]
    roots += [("allocation." + key, reg["allocation"][key])
              for key in ("algorithm_ref", "assignment_ref")]
    roots += [("implementation." + key, reg["implementation"][key])
              for key in ("method_ref", "code_ref", "dependencies_ref")]
    roots += [("implementation.baseline_refs", ref) for ref in reg["implementation"]["baseline_refs"]]
    expected = {"corpus.membership_ref": _FROZEN_DOMAIN_DIGESTS["membership"],
                "design_ref": _FROZEN_DOMAIN_DIGESTS["design"]}
    if any(ref["sha256"] != expected[role] for role, ref in roots if role in expected):
        raise E0ControlError("frozen_domain_reference_mismatch")

    references: dict[str, dict] = {}
    parsed: dict[str, object] = {}
    missing: set[str] = set()
    linked_digests: set[str] = set()

    for _role, ref in roots:
        clean = _domain_reference(ref)
        digest = clean["sha256"]
        frozen_role = next((name for name, pin in _FROZEN_DOMAIN_DIGESTS.items()
                            if pin == digest), None)
        if frozen_role is not None:
            expected_role = {"membership": "corpus.membership_ref", "design": "design_ref"}.get(frozen_role)
            if _role != expected_role:
                raise E0ControlError("frozen_domain_reference_role_mismatch")
            expected_schema = next(schema for schema, role in _FROZEN_JSON_SCHEMAS.items()
                                   if role == frozen_role)
            if clean["schema"] != expected_schema:
                raise E0ControlError("domain_schema_identity_mismatch")
        known = _FROZEN_JSON_SCHEMAS.get(clean["schema"])
        if known is not None and digest != _FROZEN_DOMAIN_DIGESTS[known]:
            raise E0ControlError("frozen_domain_schema_reference_mismatch")
        if clean["schema"] == _TASK_SCHEMA and _role != "tasks_ref":
            raise E0ControlError("task_reference_role_mismatch")
        if digest in references:
            if references[digest] != clean:
                raise E0ControlError("domain_reference_alias_mismatch")
            continue
        references[digest] = clean
        if len(references) > MAX_DOMAIN_OBJECTS:
            raise E0ControlError("domain_reference_count_limit")
        body = objects.get(digest)
        if body is None:
            missing.add(digest)
            continue
        if len(body) != clean["bytes"] or hashlib.sha256(body).hexdigest() != digest:
            raise E0ControlError("domain_reference_bytes_mismatch")
        # No JSON-by-first-character heuristic: source code and unsupported
        # semantic schemas stay opaque. Only known payload contracts are parsed.
        json_digests = {_FROZEN_DOMAIN_DIGESTS[key]
                        for key in ("membership", "design", "prelabel_binding")}
        value = _domain_json(body) if digest in json_digests or clean["schema"] == _TASK_SCHEMA else None
        if type(value) is dict:
            declared_schema = value.get("schema", value.get("document_type"))
            if declared_schema != clean["schema"]:
                raise E0ControlError("domain_schema_identity_mismatch")
            identity = value.get("object_id", value.get("protocol_id"))
            if identity is not None and identity != clean["object_id"]:
                raise E0ControlError("domain_object_identity_mismatch")
        parsed[digest] = value

    binding = None
    if prelabel_design is not None:
        digest = _FROZEN_DOMAIN_DIGESTS["prelabel_binding"]
        if hashlib.sha256(prelabel_design).hexdigest() != digest:
            raise E0ControlError("frozen_prelabel_design_bytes_mismatch")
        binding = _domain_json(prelabel_design)
        parsed[digest] = binding
    if binding is not None:
        # This is the real existing shape: a bare guide digest plus seed
        # metadata, not an invented reviewer-plan/ref envelope or allocation.
        if (binding["annotation_guide_sha256"] != _FROZEN_DOMAIN_DIGESTS["annotation_guide"]
                or binding["protocol_design_sha256"] != _FROZEN_DOMAIN_DIGESTS["design"]
                or binding["actual_membership_sha256"] != reg["corpus"]["membership_sha256"]
                or binding["condition_seed"]["encoding"] != reg["allocation"]["seed_encoding"]
                or binding["condition_seed"]["seed"] != reg["allocation"]["seed_hex"]):
            raise E0ControlError("domain_prelabel_binding_mismatch")
        digest = binding["annotation_guide_sha256"]
        linked_digests.add(digest)
    tasks_ref = reg["tasks_ref"]
    task_value = parsed.get(tasks_ref["sha256"]) if tasks_ref["schema"] == _TASK_SCHEMA else None
    if task_value is not None:
        linked_digests.add(_FROZEN_DOMAIN_DIGESTS["annotation_guide"])
    for digest in linked_digests:
        body = objects.get(digest)
        if body is not None:
            if hashlib.sha256(body).hexdigest() != digest:
                raise E0ControlError("domain_guide_bytes_mismatch")
            parsed[digest] = None  # Markdown, never JSON and never executed.
    if set(objects) - references.keys() - linked_digests:
        raise E0ControlError("unreferenced_domain_object")
    missing_linked = linked_digests - parsed.keys()
    frozen_resolved = sorted(name for name, digest in _FROZEN_DOMAIN_DIGESTS.items()
                             if digest in parsed)
    membership = parsed.get(_FROZEN_DOMAIN_DIGESTS["membership"])
    gaps = []
    if membership is not None:
        rows = membership["ordered_membership"]
        row_bytes = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False).encode("utf-8")
        if (membership["capture_count"] != reg["corpus"]["count"]
                or len(rows) != reg["corpus"]["count"]
                or hashlib.sha256(row_bytes).hexdigest() != reg["corpus"]["membership_sha256"]
                or any(membership["owner"][key] != reg["corpus"][key]
                       for key in ("profile", "store_id", "generation_id", "generation_sha256"))):
            raise E0ControlError("domain_membership_identity_mismatch")
        for field in ("source_measurement_session", "economic_episode_id",
                      "feature_support_interval", "label_interval"):
            count = sum(row[field] is None for row in membership["query_candidates"])
            if count:
                gaps.append({"field": "membership." + field, "missing_rows": count})
    if binding is not None:
        for field in ("actual_task_query_list", "real_reviewer_assignment"):
            if binding[field] is None:
                gaps.append({"field": "prelabel_binding." + field, "missing_rows": 1})
        if binding["condition_seed"]["allocation_hash"] is None:
            gaps.append({"field": "prelabel_binding.condition_allocation", "missing_rows": 1})

    task_checks = []
    if tasks_ref["schema"] == _TASK_SCHEMA and tasks_ref["sha256"] in parsed:
        task_checks.append(_validate_task_bindings(task_value, objects[tasks_ref["sha256"]], membership))

    return {"schema": "research_factory.market_memory_e0_reference_resolution.v1",
            "authority": "display_only", "study_id": reg["study_id"],
            "registration_ref": _record_ref(reg, "registration"),
            "reference_scope": "registration_refs_and_known_domain_digest_links",
            "references_complete": not missing and not missing_linked,
            "resolved_references": [references[key] for key in sorted(parsed) if key in references],
            "missing_references": [references[key] for key in sorted(missing)],
            "frozen_artifacts_resolved": frozen_resolved,
            "missing_frozen_artifacts": sorted(name for name, digest in _FROZEN_DOMAIN_DIGESTS.items()
                                               if digest in missing_linked),
            "unparsed_reference_schemas": sorted({references[key]["schema"] for key in parsed
                if key in references and parsed[key] is None}),
            "frozen_metadata_gaps": gaps,
            "task_binding_checks": task_checks,
            "domain_metadata_complete": False, "operational_admission": False,
            "unresolved_semantics": ["tasks_and_query_selection", "source_coverage_and_feature_intervals",
                "episode_clusters_and_interval_splits", "reviewer_plan_and_independence",
                "condition_allocation", "outcome_definition_and_maturity", "baseline_executables",
                "metrics_and_access_rules"],
            "unverified_obligations": ["authenticated_owner_installation", "independent_prelabel_closure",
                "current_access_history", "exact_durable_reservation"]}
