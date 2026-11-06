"""Explicit synthetic engineering connection; production admission stays disabled.

The assigning owner supplies immutable byte identities, the full schedule and
the test commission independently. None of these shapes authenticates an owner.
No candidate code, acquisition, canonical ledger write or label release occurs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, time
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from zoneinfo import ZoneInfo

from . import accounting_contract, admission, contracts, evaluation
from .input_contract import parse_timestamp, validate_input_envelope
from .output_contract import validate_output_envelope

MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_POSITIONS = 4096
_IDENTITY = ("diagnostic_id", "original_root_id", "candidate_id", "source_sha256",
             "config_sha256", "protocol_sha256", "input_policy_sha256",
             "runtime_sha256", "evaluator_sha256")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
PUBLIC_AGGREGATE_KEYS = (
    "measurement_status", "scheduled_formation_count", "source_excluded_formation_count",
    "source_qualified_formation_count", "provided_formation_count",
    "opportunity_formation_count", "no_opportunity_formation_count", "paired_formation_count",
    "provided_baseline_entry_count", "provided_selected_entry_count", "provided_foregone_entry_count",
    "paired_mean_baseline_adverse_loss", "paired_mean_selected_adverse_loss",
    "paired_mean_improvement", "refusal_count", "scientific_acceptance",
    "inference_state", "procedure_state",
)
_FLAGS = dict(authority="display_only", scope="SYNTHETIC_ENGINEERING_ONLY",
              generation_enabled=False, execution_enabled=False, evaluation_enabled=False,
              authority_granted=False, scientific_acceptance="UNQUALIFIED",
              inference_state="INFERENCE_UNQUALIFIED", procedure_state="NO_QUALIFIED_PROCEDURE",
              owner_origin_and_effective_boundaries="UNQUALIFIED")


class BridgeRefused(ValueError):
    """Closed, non-activating boundary refusal; no partial batch is returned."""


@dataclass(frozen=True)
class SyntheticTestCommission:
    original_root_id: str
    staging_root: str


@dataclass(frozen=True)
class BoundBytes:
    raw: bytes
    sha256: str
    size: int


@dataclass(frozen=True)
class ArtifactBinding:
    artifact_path: str
    artifact_sha256: str
    artifact_bytes: int
    diagnostic_id: str
    original_root_id: str
    candidate_id: str
    source_sha256: str
    config_sha256: str
    protocol_sha256: str
    input_policy_sha256: str
    runtime_sha256: str
    evaluator_sha256: str


@dataclass(frozen=True)
class DiagnosticReadback:
    diagnostic_id: str
    created_at: str
    original_root_id: str
    candidate_id: str
    source_sha256: str
    config_sha256: str
    protocol_sha256: str
    input_policy_sha256: str
    runtime_sha256: str
    evaluator_sha256: str
    artifact_sha256: str
    status: str
    aggregates: tuple[tuple[str, object], ...]
    authority: str = field(default="display_only", init=False)
    scope: str = field(default="SYNTHETIC_ENGINEERING_ONLY", init=False)
    generation_enabled: bool = field(default=False, init=False)
    execution_enabled: bool = field(default=False, init=False)
    evaluation_enabled: bool = field(default=False, init=False)
    authority_granted: bool = field(default=False, init=False)


@dataclass(frozen=True)
class CaptureBinding:
    ticker: str
    source_id: str
    receipt: BoundBytes
    provider_image: BoundBytes
    merged_image: BoundBytes
    receipt_read_completed_at: str
    # Exact trusted date -> session-end UTC mapping; never invented midnight.
    session_clocks: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DecisionBinding:
    calendar_index: int
    node: str
    request: BoundBytes
    capture: CaptureBinding


@dataclass(frozen=True)
class SchedulePosition:
    calendar_index: int
    trigger_date: str
    eligible_nodes: tuple[str, ...]
    # Exactly nine owner dispositions. Any failure excludes both arms before output.
    source_dispositions: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SyntheticRun:
    identity: ArtifactBinding
    created_at: str
    manifest: BoundBytes
    protocol: BoundBytes
    owner_references: BoundBytes
    expected_generation: BoundBytes
    trial_readback: BoundBytes
    positions: tuple[SchedulePosition, ...]
    decisions: tuple[DecisionBinding, ...]
    # Each entity has one fixed schedule and one separately retained candidate output.
    schedules: tuple[BoundBytes, ...]
    outputs: tuple[BoundBytes, ...]
    paths: tuple[evaluation.SourcePath, ...]
    session_dates: tuple[str, ...]


@dataclass(frozen=True)
class PreparedIdentity:
    """The nine immutable identity fields; never an artifact or staging path."""

    diagnostic_id: str
    original_root_id: str
    candidate_id: str
    source_sha256: str
    config_sha256: str
    protocol_sha256: str
    input_policy_sha256: str
    runtime_sha256: str
    evaluator_sha256: str


@dataclass(frozen=True)
class PreparedDecisionInput:
    """One owner decision's exact causal prefix; no label, path or capture image."""

    fold_id: str
    entity_id: str
    decision_id: str
    calendar_index: int
    node: str
    request: BoundBytes
    input_bytes: BoundBytes
    cutoff: str
    trailing_session_dates: tuple[str, ...]
    complete_trailing: bool


@dataclass(frozen=True)
class PreparedOwnerSchedule:
    """The owner's fixed per-entity decision order, retained exactly."""

    fold_id: str
    entity_id: str
    decision_ids: tuple[str, ...]


@dataclass(frozen=True)
class PreparedSyntheticInputs:
    """Frozen per-decision preparation consumed by the connected prefix driver.

    Narrow by construction: no SourcePath, no label, no raw capture image and no
    staging path is carried.  Structural admission here is not authentication and
    grants no generation, execution, evaluation or authority.
    """

    identity: PreparedIdentity
    decisions: tuple[PreparedDecisionInput, ...]
    schedules: tuple[PreparedOwnerSchedule, ...]
    session_dates: tuple[str, ...]


def _require(condition, reason):
    if not condition:
        raise BridgeRefused(reason)


def _sha(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _id(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _pairs(rows):
    result = {}
    for key, value in rows:
        _require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _json(raw, limit=MAX_ARTIFACT_BYTES):
    _require(type(raw) is bytes and 0 < len(raw) <= limit, "BOUNDED_BYTES_REQUIRED")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(BridgeRefused("NONFINITE_JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise BridgeRefused("INVALID_JSON") from exc
    # Independent structural traversal permits the capture's 12,000-row schema
    # without silently applying the smaller contract-envelope limit.
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(depth <= 32 and count <= 150000, "JSON_STRUCTURE_LIMIT")
        if type(item) is dict:
            _require(all(type(k) is str and len(k) <= 256 for k in item), "JSON_KEY_LIMIT")
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            pending.extend((v, depth + 1) for v in item)
        elif type(item) is str:
            _require(len(item) <= 4096, "JSON_STRING_LIMIT")
        elif item is not None and type(item) is not bool:
            _require(_finite(item), "NONFINITE_JSON")
    return value


def _bound(value, limit=MAX_ARTIFACT_BYTES):
    _require(type(value) is BoundBytes, "EXACT_BYTE_BINDING_REQUIRED")
    _require(type(value.raw) is bytes and type(value.size) is int
             and value.size == len(value.raw) and _sha(value.sha256), "INVALID_BYTE_BINDING")
    _require(hashlib.sha256(value.raw).hexdigest() == value.sha256, "BYTE_DIGEST_MISMATCH")
    return _json(value.raw, limit)


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys), "CLOSED_SCHEMA_REQUIRED")


def _commission(value, root):
    _require(type(value) is SyntheticTestCommission, "PRODUCTION_DISABLED_NO_TEST_COMMISSION")
    _require(_id(root) and _id(value.original_root_id) and value.original_root_id == root
             and type(value.staging_root) is str and os.path.isabs(value.staging_root),
             "COMMISSION_IDENTITY_MISMATCH")


def _identity(binding):
    _require(type(binding) is ArtifactBinding, "EXACT_ARTIFACT_BINDING_REQUIRED")
    result = {k: getattr(binding, k) for k in _IDENTITY}
    _require(all(_sha(result[k]) if k.endswith("sha256") else _id(result[k])
                 for k in result), "INVALID_IDENTITY")
    _require(result["candidate_id"].startswith("rf-codegen-"), "INVALID_CANDIDATE_ID")
    return result


def _timestamp(value):
    try:
        return parse_timestamp(value)
    except ValueError as exc:
        raise BridgeRefused("INVALID_TIMESTAMP") from exc


def _capture_input(decision, request, trailing_session_dates):
    capture = decision.capture
    _require(type(capture) is CaptureBinding and type(capture.ticker) is str
             and capture.ticker == decision.node and _id(capture.source_id), "INVALID_CAPTURE_BINDING")
    receipt = _bound(capture.receipt)
    image = _bound(capture.provider_image)
    merged_image = _bound(capture.merged_image)
    _closed(receipt, ("schema", "ticker", "provider_return_image", "merged_capture_image",
                     "provider_available_at", "operation_identity", "source_code_identity",
                     "rights_reference", "clock_attestation", "source_actor_authentication",
                     "calendar_verification", "upstream_revision_history_complete",
                     "historical_original_availability_proven", "canonical_cache_transaction_durability"))
    _require(receipt["schema"] == "yahoo.availability_capture.v1"
             and receipt["ticker"] == capture.ticker and receipt["provider_available_at"] is None,
             "CAPTURE_IDENTITY_MISMATCH")
    provider, merged = receipt["provider_return_image"], receipt["merged_capture_image"]
    _closed(provider, ("sha256", "bytes", "object_ref", "adapter_return_known_by_utc", "basis", "scope"))
    _closed(merged, ("sha256", "bytes", "object_ref", "captured_known_by_utc",
                     "immutable_publication_durable_at_utc", "basis", "scope"))
    _require(provider["sha256"] == capture.provider_image.sha256
             and type(provider["bytes"]) is int and provider["bytes"] == capture.provider_image.size
             and provider["object_ref"] == "objects/" + capture.provider_image.sha256 + ".json"
             and provider["basis"] == "total_return"
             and provider["scope"] == "validated_session_filtered_adapter_output_not_vendor_wire",
             "PROVIDER_IMAGE_MISMATCH")
    _require(merged["sha256"] == capture.merged_image.sha256 and type(merged["bytes"]) is int
             and merged["bytes"] == capture.merged_image.size
             and merged["object_ref"] == "objects/" + merged["sha256"] + ".json"
             and merged["basis"] == "total_return"
             and merged["scope"] == "separate_capture_of_returned_merged_values", "MERGED_REFERENCE_MISMATCH")
    known = _timestamp(provider["adapter_return_known_by_utc"])
    captured = _timestamp(merged["captured_known_by_utc"])
    durable = _timestamp(merged["immutable_publication_durable_at_utc"])
    received = _timestamp(capture.receipt_read_completed_at)
    _require(known <= captured <= durable <= received, "CAPTURE_CLOCK_REGRESSION")
    _require(type(capture.session_clocks) is tuple and all(type(r) is tuple and len(r) == 2
             and type(r[0]) is str and type(r[1]) is str for r in capture.session_clocks), "SESSION_CLOCKS_REQUIRED")
    clocks = dict(capture.session_clocks)
    _require(len(clocks) == len(capture.session_clocks), "DUPLICATE_SESSION_CLOCK")
    _closed(image, ("encoding", "columns", "rows"))
    _require(image["encoding"] == "dated_numeric_frame_json.v1" and type(image["columns"]) is list
             and image["columns"] in (["close"], ["close", "close_price"], ["close", "volume"],
                                       ["close", "close_price", "volume"])
             and type(image["rows"]) is list and 0 < len(image["rows"]) <= 12000,
             "INVALID_CAPTURE_IMAGE")
    _closed(merged_image, ("encoding", "columns", "rows"))
    _require(merged_image["encoding"] == "dated_numeric_frame_json.v1"
             and type(merged_image["columns"]) is list
             and merged_image["columns"] in (["close"], ["close", "close_price"], ["close", "volume"], ["close", "close_price", "volume"])
             and type(merged_image["rows"]) is list and 0 < len(merged_image["rows"]) <= 12000,
             "INVALID_MERGED_IMAGE")
    previous_merged = None
    for row in merged_image["rows"]:
        _require(type(row) is list and len(row) == len(merged_image["columns"]) + 1 and type(row[0]) is str
                 and (previous_merged is None or previous_merged < row[0])
                 and all(v is None or _finite(v) for v in row[1:]), "INVALID_MERGED_ROW")
        try:
            _require(date.fromisoformat(row[0]).isoformat() == row[0] and row[0] <= captured.date().isoformat(), "INVALID_MERGED_DATE")
        except ValueError as exc:
            raise BridgeRefused("INVALID_MERGED_DATE") from exc
        previous_merged = row[0]
    cutoff, observations, previous = _timestamp(request["cutoff"]), [], None
    for row in image["rows"]:
        _require(type(row) is list and len(row) == len(image["columns"]) + 1
                 and type(row[0]) is str and row[0] in clocks, "CAPTURE_SESSION_UNBOUND")
        day = row[0]
        try:
            valid_day = date.fromisoformat(day).isoformat() == day
        except ValueError:
            valid_day = False
        _require(valid_day and (previous is None or previous < day), "CAPTURE_DATE_ORDER")
        previous = day
        _require(all(v is None or _finite(v) for v in row[1:]), "INVALID_CAPTURE_VALUE")
        event = _timestamp(clocks[day])
        _require(event.date().isoformat() == day and event <= known, "UNBOUND_CAPTURE_EVENT")
        # Capture availability means durable known-by, never historical provider release.
        if day in trailing_session_dates and received <= cutoff and event <= cutoff:
            observations.append(dict(source_id=capture.source_id, revision_id=capture.provider_image.sha256,
                                     event_time=clocks[day], available_at=durable.isoformat(),
                                     received_at=received.isoformat(), evidence_class="captured", value=row[1]))
    observations.sort(key=lambda r: (_timestamp(r["available_at"]), _timestamp(r["event_time"]),
                                    r["source_id"], r["revision_id"]))
    envelope = {k: request[k] for k in ("candidate_id", "fold_id", "entity_id", "decision_id", "cutoff", "input_policy_sha256")}
    envelope.update(schema="research_codegen.input.v1", observations=observations)
    _require(not validate_input_envelope(envelope, trusted_request=request), "INVALID_CAUSAL_INPUT")
    return envelope


def _positions(value):
    _require(type(value) is tuple and len(value) <= MAX_POSITIONS, "IMMUTABLE_FULL_SCHEDULE_REQUIRED")
    excluded, supplied = [], []
    for i, p in enumerate(value):
        _require(type(p) is SchedulePosition and type(p.calendar_index) is int
                 and p.calendar_index == i and type(p.trigger_date) is str
                 and type(p.eligible_nodes) is tuple and all(type(n) is str and n in evaluation.COHORT for n in p.eligible_nodes)
                 and len(set(p.eligible_nodes)) == len(p.eligible_nodes), "INVALID_FULL_SCHEDULE")
        _require(type(p.source_dispositions) is tuple and len(p.source_dispositions) == 9
                 and all(type(r) is tuple and len(r) == 2 and type(r[0]) is str and type(r[1]) is str
                         and r[1] in ("qualified", "source_unavailable") for r in p.source_dispositions)
                 and tuple(r[0] for r in p.source_dispositions) == evaluation.COHORT, "EXACT_COHORT_DISPOSITIONS_REQUIRED")
        (excluded if any(r[1] != "qualified" for r in p.source_dispositions) else supplied).append(p)
    return tuple(excluded), tuple(supplied)


def _admission(run, *, commission):
    """Shared structural admission prologue for the evaluator and the preparer.

    Factored out of compute_synthetic_diagnostic with identical checks in the
    identical order.  ``admitted`` is a fixed structural gate, never authority.
    """
    _require(type(run) is SyntheticRun, "EXACT_SYNTHETIC_RUN_REQUIRED")
    identity = _identity(run.identity)
    _commission(commission, identity["original_root_id"])
    _timestamp(run.created_at)
    excluded, supplied = _positions(run.positions)
    _require(type(run.session_dates) is tuple and all(type(d) is str for d in run.session_dates)
             and len(set(run.session_dates)) == len(run.session_dates)
             and evaluation.FORMATION_ANCHOR in run.session_dates, "INVALID_FULL_CALENDAR")
    anchor = run.session_dates.index(evaluation.FORMATION_ANCHOR)
    _require(all(anchor + 26 * p.calendar_index < len(run.session_dates)
                 and run.session_dates[anchor + 26 * p.calendar_index] == p.trigger_date
                 for p in run.positions), "FULL_SCHEDULE_ANCHOR_MISMATCH")
    coverage = dict(scheduled=len(run.positions), excluded=len(excluded), qualified=len(supplied))
    manifest, protocol = _bound(run.manifest), _bound(run.protocol)
    _require(not contracts.validate_manifest(manifest, trusted_protocol=protocol), "MANIFEST_INVALID")
    _require(all(manifest[k] == identity[k] for k in _IDENTITY if k in manifest)
             and manifest["lineage"]["original_root_id"] == identity["original_root_id"], "MANIFEST_IDENTITY_MISMATCH")
    owner = admission.assess_prerequisites(manifest, trusted_protocol=protocol, owner_receipts=_bound(run.owner_references))
    expected, trial = _bound(run.expected_generation), _bound(run.trial_readback)
    account = accounting_contract.assess_accounting_references(expected, trial_readback=trial)
    accounting_bound = (type(expected) is dict and expected.get("original_root_id") == identity["original_root_id"]
                        and expected.get("protocol_sha256") == identity["protocol_sha256"]
                        and expected.get("family") == manifest["trial_family"]
                        and expected.get("vault_required") is False
                        and any(v.get("source_sha256") == identity["source_sha256"]
                                and v.get("config_sha256") == identity["config_sha256"]
                                for v in expected.get("variants", []) if type(v) is dict))
    admitted = bool(owner["status"] == account["status"] == "STRUCTURALLY_COMPLETE_DISABLED"
                    and accounting_bound)
    return identity, supplied, coverage, admitted


def compute_synthetic_diagnostic(run, *, commission=None):
    """Connect trusted retained fixtures; return bytes for the owner's staging writer.

    Candidate failures yield whole-run refusal. Malformed owner bindings raise
    BridgeRefused. The method has no filesystem or candidate execution effect.
    """
    identity, supplied, coverage, admitted = _admission(run, commission=commission)
    known_coverage = tuple(evaluation.CoveragePosition(p.calendar_index, p.trigger_date, len(p.eligible_nodes)) for p in supplied)
    result = evaluation.EvaluationResult("REFUSED", ("PREREQUISITES_INVALID",), known_coverage, ())
    if admitted:
        try:
            result = _evaluate(run, supplied, identity)
        except BridgeRefused:
            # Never expose candidate text or salvage successful cells.
            result = evaluation.EvaluationResult("REFUSED", ("INPUT_OR_OUTPUT_REFUSED",), known_coverage, ())
    artifact = dict(schema="research_codegen.synthetic_diagnostic.v1", identity=identity,
                    created_at=run.created_at, coverage=coverage, evaluation=asdict(result), flags=_FLAGS)
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    _require(len(raw) <= MAX_ARTIFACT_BYTES, "ARTIFACT_LIMIT")
    return raw


def _prepare_decisions(run, supplied, identity):
    """Exact per-decision causal prefix, factored out of _evaluate unchanged.

    Returns the request map, the populated flag map and one narrow preparation
    record per decision in owner order.  No semantic change and no new checks; the
    retained-schedule/output arity guard stays on the whole-run path so that a run
    with stale or absent outputs can still be prepared.
    """
    _require(type(run.decisions) is tuple, "IMMUTABLE_DECISIONS_REQUIRED")
    wanted = {(p.calendar_index, n) for p in supplied for n in p.eligible_nodes}
    requests, populated, keys, tasks = {}, {}, set(), []
    for d in run.decisions:
        _require(type(d) is DecisionBinding and type(d.calendar_index) is int and type(d.node) is str,
                 "EXACT_DECISION_REQUIRED")
        key = (d.calendar_index, d.node)
        _require(key in wanted and key not in keys, "DECISION_SCHEDULE_MISMATCH")
        keys.add(key)
        request = _bound(d.request, contracts.MAX_BYTES)
        # Validate the trusted request before any field access; empty observations are lawful.
        _require(type(request) is dict, "INVALID_REQUEST")
        envelope = {k: request.get(k) for k in ("candidate_id", "fold_id", "entity_id", "decision_id", "cutoff", "input_policy_sha256")}
        envelope.update(schema="research_codegen.input.v1", observations=[])
        _require(not validate_input_envelope(envelope, trusted_request=request), "INVALID_REQUEST")
        _require(request["candidate_id"] == identity["candidate_id"] and request["entity_id"] == d.node
                 and request["input_policy_sha256"] == identity["input_policy_sha256"], "REQUEST_IDENTITY_MISMATCH")
        trigger_index = run.session_dates.index(run.positions[d.calendar_index].trigger_date)
        _require(trigger_index + 1 < len(run.session_dates), "NEXT_SESSION_MISSING")
        next_day = date.fromisoformat(run.session_dates[trigger_index + 1])
        cutoff = datetime.combine(next_day, time(9), ZoneInfo("America/New_York"))
        _require(_timestamp(request["cutoff"]) == cutoff, "NEXT_SESSION_CUTOFF_MISMATCH")
        rid = (request["fold_id"], d.node, request["decision_id"])
        _require(rid not in requests, "DUPLICATE_REQUEST")
        requests[rid] = key
        trailing = run.session_dates[max(0, trigger_index - 62):trigger_index + 1]
        causal = _capture_input(d, request, trailing)
        observations = causal["observations"]
        complete = (len(trailing) == len(observations) == 63
                    and tuple(_timestamp(r["event_time"]).date().isoformat() for r in observations) == trailing
                    and all(_finite(r["value"]) for r in observations))
        populated[rid] = complete
        tasks.append((rid, d, request, causal, cutoff, trailing, complete))
    _require(keys == wanted, "MISSING_DECISION")
    return requests, populated, tasks


def _consume_outputs(run, requests, populated, identity):
    """Whole-run output consumption, factored out of _evaluate unchanged."""
    scores, seen = [], set()
    for sb, ob in zip(run.schedules, run.outputs):
        schedule, output = _bound(sb, contracts.MAX_BYTES), _bound(ob, contracts.MAX_BYTES)
        _require(not validate_output_envelope(output, trusted_schedule=schedule), "OUTPUT_CONTRACT_REFUSED")
        _require(schedule["candidate_id"] == identity["candidate_id"]
                 and schedule["input_policy_sha256"] == identity["input_policy_sha256"], "OUTPUT_IDENTITY_MISMATCH")
        ids = [r for r in requests if r[:2] == (schedule["fold_id"], schedule["entity_id"])]
        _require(schedule["decision_ids"] == [r[2] for r in ids], "OUTPUT_ORDER_MISMATCH")
        for row in output["rows"]:
            rid = (schedule["fold_id"], schedule["entity_id"], row["decision_id"])
            _require(rid in requests and rid not in seen and populated[rid]
                     and row["status"] == "available", "WHOLE_OUTPUT_REFUSED")
            seen.add(rid)
            index, node = requests[rid]
            scores.append(evaluation.FeatureScore(index, node, row["value"]))
    _require(seen == set(requests), "MISSING_OUTPUT")
    return scores


def _evaluate(run, supplied, identity):
    _require(type(run.decisions) is tuple and type(run.schedules) is tuple and type(run.outputs) is tuple
             and len(run.schedules) == len(run.outputs), "IMMUTABLE_DECISIONS_REQUIRED")
    requests, populated, _ = _prepare_decisions(run, supplied, identity)
    scores = _consume_outputs(run, requests, populated, identity)
    formations = tuple(evaluation.Formation(p.calendar_index, p.trigger_date, p.eligible_nodes) for p in supplied)
    return evaluation.evaluate_feature_ordering(paths=run.paths, formations=formations,
        scores=tuple(scores), expected_session_dates=run.session_dates)


def _canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def prepare_synthetic_inputs(run, *, commission=None):
    """Public preparation seam: exact per-decision causal prefixes, zero effects.

    Reuses the accepted manifest/identity/owner/accounting checks and the exact
    full-position, source-exclusion, next-session-cutoff and trailing-63 logic of
    compute_synthetic_diagnostic.  The returned shape is narrow: no SourcePath, no
    label, no raw capture image and no staging path.  Nothing here runs a
    candidate, grants admission or releases a label, and malformed owner bindings
    raise BridgeRefused exactly as the whole-run path does.
    """
    _require(type(run) is SyntheticRun, "EXACT_SYNTHETIC_RUN_REQUIRED")
    _require(type(run.schedules) is tuple, "IMMUTABLE_DECISIONS_REQUIRED")
    identity, supplied, _, admitted = _admission(run, commission=commission)
    _require(admitted, "PREREQUISITES_INVALID")
    requests, _, tasks = _prepare_decisions(run, supplied, identity)
    prepared = []
    for rid, decision, request, causal, cutoff, trailing, complete in tasks:
        raw = _canonical_bytes(causal)
        prepared.append(PreparedDecisionInput(
            rid[0], decision.node, rid[2], decision.calendar_index, decision.node, decision.request,
            BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw)), request["cutoff"],
            tuple(trailing), complete))
    schedules, schedule_keys = [], set()
    for sb in run.schedules:
        schedule = _bound(sb, contracts.MAX_BYTES)
        _require(type(schedule) is dict and type(schedule.get("decision_ids")) is list
                 and all(type(x) is str for x in schedule["decision_ids"]), "INVALID_OWNER_SCHEDULE")
        # Existing output validator owns the exact closed schedule schema. These
        # inert reference rows validate its shape without admitting any output.
        reference = {k: schedule.get(k) for k in ("candidate_id", "fold_id", "entity_id", "input_policy_sha256")}
        reference.update(schema="research_codegen.output.v1", rows=[
            dict(decision_id=d, status="refused", value=None, reason="OWNER_SCHEDULE_REFERENCE")
            for d in schedule["decision_ids"]])
        _require(not validate_output_envelope(reference, trusted_schedule=schedule), "INVALID_OWNER_SCHEDULE")
        group_key = (schedule["fold_id"], schedule["entity_id"])
        _require(group_key not in schedule_keys, "DUPLICATE_OWNER_SCHEDULE")
        schedule_keys.add(group_key)
        _require(schedule["candidate_id"] == identity["candidate_id"]
                 and schedule["input_policy_sha256"] == identity["input_policy_sha256"], "OUTPUT_IDENTITY_MISMATCH")
        ordered = [r[2] for r in requests if r[:2] == (schedule["fold_id"], schedule["entity_id"])]
        _require(schedule["decision_ids"] == ordered, "OUTPUT_ORDER_MISMATCH")
        schedules.append(PreparedOwnerSchedule(schedule["fold_id"], schedule["entity_id"], tuple(ordered)))
    _require(set(requests) == {(s.fold_id, s.entity_id, d) for s in schedules for d in s.decision_ids},
             "INCOMPLETE_OWNER_SCHEDULE")
    return PreparedSyntheticInputs(PreparedIdentity(**{k: identity[k] for k in _IDENTITY}),
                                   tuple(prepared), tuple(schedules), run.session_dates)


def _restore_result(value):
    _closed(value, ("status", "refusal_reasons", "coverage", "pairs", "authority", "scientific_acceptance"))
    _require(value["status"] in ("REFUSED", "DIAGNOSTIC_ONLY") and value["authority"] == "display_only"
             and value["scientific_acceptance"] == "UNQUALIFIED", "INVALID_RESULT_STATUS")
    _require(type(value["refusal_reasons"]) is list and len(value["refusal_reasons"]) <= MAX_POSITIONS * 9
             and all(_id(r) for r in value["refusal_reasons"]), "INVALID_REFUSALS")
    _require(type(value["coverage"]) is list and type(value["pairs"]) is list
             and len(value["coverage"]) <= MAX_POSITIONS, "INVALID_RESULT_COLLECTION")
    coverage, previous = [], -1
    for row in value["coverage"]:
        _closed(row, ("calendar_index", "trigger_date", "opportunities"))
        _require(type(row["calendar_index"]) is int and previous < row["calendar_index"] < MAX_POSITIONS
                 and type(row["opportunities"]) is int and 0 <= row["opportunities"] <= 9
                 and type(row["trigger_date"]) is str, "INVALID_COVERAGE")
        try:
            _require(date.fromisoformat(row["trigger_date"]).isoformat() == row["trigger_date"], "INVALID_COVERAGE_DATE")
        except ValueError as exc:
            raise BridgeRefused("INVALID_COVERAGE_DATE") from exc
        previous = row["calendar_index"]
        coverage.append(evaluation.CoveragePosition(**row))
    pairs = []
    for row in value["pairs"]:
        _closed(row, (f.name for f in fields(evaluation.PairedFormation)))
        _require(type(row["calendar_index"]) is int and 0 <= row["calendar_index"] < MAX_POSITIONS
                 and type(row["trigger_date"]) is str, "INVALID_PAIR_IDENTITY")
        try:
            trigger_day = date.fromisoformat(row["trigger_date"])
            _require(trigger_day.isoformat() == row["trigger_date"], "INVALID_PAIR_DATE")
        except ValueError as exc:
            raise BridgeRefused("INVALID_PAIR_DATE") from exc
        for name in ("selected_nodes", "foregone_nodes"):
            _require(type(row[name]) is list and all(type(n) is str and n in evaluation.COHORT for n in row[name])
                     and len(set(row[name])) == len(row[name]), "INVALID_PAIR_NODES")
        entries = {}
        for name in ("baseline_entries", "candidate_entries"):
            _require(type(row[name]) is list and 0 < len(row[name]) <= 9, "INVALID_ENTRIES")
            entries[name] = []
            for entry in row[name]:
                _closed(entry, (f.name for f in fields(evaluation.MeasuredEntry)))
                _require(type(entry["node"]) is str and entry["node"] in evaluation.COHORT
                         and entry["trigger_date"] == row["trigger_date"] and type(entry["exec_date"]) is str
                         and type(entry["hold_sessions"]) is int and entry["hold_sessions"] == 21
                         and all(_finite(entry[n]) for n in ("mfe", "mae", "ret_exit"))
                         and -1 < entry["mae"] <= entry["ret_exit"] <= entry["mfe"], "INVALID_ENTRY")
                try:
                    exec_day = date.fromisoformat(entry["exec_date"])
                    _require(exec_day.isoformat() == entry["exec_date"] and exec_day > trigger_day, "INVALID_ENTRY_DATE")
                except ValueError as exc:
                    raise BridgeRefused("INVALID_ENTRY_DATE") from exc
                entries[name].append(evaluation.MeasuredEntry(**entry))
        baseline, selected = entries["baseline_entries"], entries["candidate_entries"]
        nodes = tuple(e.node for e in baseline)
        _require(nodes == tuple(sorted(set(nodes))) and tuple(e.node for e in selected) == tuple(row["selected_nodes"])
                 and all(e in baseline for e in selected) and len(selected) == (len(baseline) + 1) // 2
                 and tuple(row["foregone_nodes"]) == tuple(n for n in nodes if n not in row["selected_nodes"]), "INCONSISTENT_PAIR")
        base = math.fsum(max(0, -e.mae) for e in baseline) / len(baseline)
        cand = math.fsum(max(0, -e.mae) for e in selected) / len(selected)
        _require(all(_finite(row[k]) and row[k] == v for k, v in
                     (("baseline_loss", base), ("candidate_loss", cand), ("difference", base - cand))), "INCONSISTENT_EFFECT")
        pairs.append(evaluation.PairedFormation(row["calendar_index"], row["trigger_date"],
            tuple(row["selected_nodes"]), tuple(row["foregone_nodes"]), tuple(baseline), tuple(selected), base, cand, base - cand))
    if value["status"] == "REFUSED":
        _require(bool(value["refusal_reasons"]) and not pairs, "REFUSAL_PAIR_SALVAGE")
    else:
        _require(not value["refusal_reasons"] and
                 [(p.calendar_index, p.trigger_date, len(p.baseline_entries)) for p in pairs]
                 == [(c.calendar_index, c.trigger_date, c.opportunities) for c in coverage if c.opportunities], "INCOMPLETE_PAIR_SET")
    return evaluation.EvaluationResult(value["status"], tuple(value["refusal_reasons"]), tuple(coverage), tuple(pairs))


def _aggregates(result, coverage):
    _closed(coverage, ("scheduled", "excluded", "qualified"))
    _require(all(type(n) is int and 0 <= n <= MAX_POSITIONS for n in coverage.values())
             and coverage["scheduled"] == coverage["excluded"] + coverage["qualified"]
             and len(result.coverage) <= coverage["qualified"]
             and all(c.calendar_index < coverage["scheduled"] for c in result.coverage), "INVALID_FULL_COVERAGE")
    if result.status == "DIAGNOSTIC_ONLY":
        _require(len(result.coverage) == coverage["qualified"], "MISSING_QUALIFIED_COVERAGE")
    good = result.status == "DIAGNOSTIC_ONLY"
    pairs = result.pairs
    values = dict(measurement_status=result.status, scheduled_formation_count=coverage["scheduled"],
                  source_excluded_formation_count=coverage["excluded"], source_qualified_formation_count=coverage["qualified"],
                  provided_formation_count=len(result.coverage), opportunity_formation_count=sum(c.opportunities > 0 for c in result.coverage),
                  no_opportunity_formation_count=sum(c.opportunities == 0 for c in result.coverage),
                  paired_formation_count=len(pairs) if good else None,
                  provided_baseline_entry_count=sum(len(p.baseline_entries) for p in pairs) if good else None,
                  provided_selected_entry_count=sum(len(p.candidate_entries) for p in pairs) if good else None,
                  provided_foregone_entry_count=sum(len(p.foregone_nodes) for p in pairs) if good else None,
                  refusal_count=result.refusal_count, scientific_acceptance="UNQUALIFIED",
                  inference_state="INFERENCE_UNQUALIFIED", procedure_state="NO_QUALIFIED_PROCEDURE")
    for key, attr in (("paired_mean_baseline_adverse_loss", "baseline_loss"),
                      ("paired_mean_selected_adverse_loss", "candidate_loss"), ("paired_mean_improvement", "difference")):
        values[key] = math.fsum(getattr(p, attr) for p in pairs) / len(pairs) if good and pairs else None
    return tuple((k, values[k]) for k in PUBLIC_AGGREGATE_KEYS)


def decode_bound_artifact(raw, *, expected, commission=None):
    identity = _identity(expected)
    _commission(commission, identity["original_root_id"])
    _require(type(raw) is bytes and type(expected.artifact_bytes) is int
             and len(raw) == expected.artifact_bytes and _sha(expected.artifact_sha256)
             and hashlib.sha256(raw).hexdigest() == expected.artifact_sha256, "ARTIFACT_BYTES_MISMATCH")
    value = _json(raw)
    _closed(value, ("schema", "identity", "created_at", "coverage", "evaluation", "flags"))
    _require(value["schema"] == "research_codegen.synthetic_diagnostic.v1" and value["identity"] == identity
             and value["flags"] == _FLAGS and all(type(value["flags"].get(k)) is type(v) for k, v in _FLAGS.items()),
             "ARTIFACT_IDENTITY_OR_FLAGS_MISMATCH")
    _timestamp(value["created_at"])
    result = _restore_result(value["evaluation"])
    return DiagnosticReadback(**identity, created_at=value["created_at"], artifact_sha256=expected.artifact_sha256,
                              status=result.status, aggregates=_aggregates(result, value["coverage"]))


def load_diagnostic_artifact(binding, *, commission=None):
    identity = _identity(binding)
    _commission(commission, identity["original_root_id"])
    _require(type(binding.artifact_path) is str and os.path.isabs(binding.artifact_path)
             and type(binding.artifact_bytes) is int and 0 < binding.artifact_bytes <= MAX_ARTIFACT_BYTES,
             "INVALID_ARTIFACT_PATH_OR_SIZE")
    root = Path(commission.staging_root).resolve(strict=True)
    path = Path(binding.artifact_path)
    _require(path.resolve(strict=True).is_relative_to(root) and not path.is_symlink(), "ARTIFACT_OUTSIDE_STAGING")
    # Walk relative to the admitted directory descriptor; a raced parent symlink
    # cannot redirect this read outside that root after the path check above.
    relative = path.relative_to(root)
    _require(all(part not in ("", ".", "..") for part in relative.parts), "INVALID_ARTIFACT_COMPONENT")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in relative.parts[:-1]:
            next_directory = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        fd = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)
    try:
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and before.st_size == binding.artifact_bytes, "INVALID_ARTIFACT_FILE")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(binding.artifact_bytes + 1)
        after = os.fstat(fd)
        _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                 == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "ARTIFACT_CHANGED_DURING_READ")
    finally:
        os.close(fd)
    return decode_bound_artifact(raw, expected=binding, commission=commission)


def load_diagnostics(bindings=(), *, commission=None):
    _require(type(bindings) is tuple and len(bindings) <= 32, "BOUNDED_IMMUTABLE_BINDINGS_REQUIRED")
    if not bindings:
        return ()
    result = tuple(load_diagnostic_artifact(b, commission=commission) for b in bindings)
    _require(len({r.diagnostic_id for r in result}) == len(result), "DUPLICATE_DIAGNOSTIC")
    return result


def public_diagnostic(readback):
    """Fixed aggregate projection shared by queue and authenticated admin consumers."""
    _require(type(readback) is DiagnosticReadback and type(readback.aggregates) is tuple
             and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                     and (row[1] is None or type(row[1]) in (str, int, float)) for row in readback.aggregates)
             and tuple(k for k, _ in readback.aggregates) == PUBLIC_AGGREGATE_KEYS, "EXACT_READBACK_REQUIRED")
    value = dict(**{k: getattr(readback, k) for k in _IDENTITY}, created_at=readback.created_at,
                artifact_sha256=readback.artifact_sha256, status=readback.status,
                aggregates=dict(readback.aggregates), **_FLAGS)
    return validate_public_projection(value)


def validate_public_projection(value):
    """Screen a published display projection; never infer owner authentication."""
    _require(contracts.is_exact_json(value), "EXACT_PUBLIC_JSON_REQUIRED")
    _closed(value, (*_IDENTITY, "created_at", "artifact_sha256", "status", "aggregates", *_FLAGS))
    _require(all(_sha(value[k]) if k.endswith("sha256") else _id(value[k]) for k in _IDENTITY)
             and _sha(value["artifact_sha256"]) and value["status"] in ("REFUSED", "DIAGNOSTIC_ONLY"), "INVALID_PUBLIC_IDENTITY")
    _timestamp(value["created_at"])
    _require(all(type(value[k]) is type(v) and value[k] == v for k, v in _FLAGS.items()), "INVALID_PUBLIC_FLAGS")
    agg = value["aggregates"]
    _closed(agg, PUBLIC_AGGREGATE_KEYS)
    _require(agg["measurement_status"] == value["status"]
             and all(agg[k] == _FLAGS[k] for k in ("scientific_acceptance", "inference_state", "procedure_state")), "INVALID_PUBLIC_STATUS")
    for k, v in agg.items():
        if k.endswith("count"):
            _require(v is None or type(v) is int and 0 <= v <= MAX_POSITIONS * 9, "INVALID_PUBLIC_COUNT")
        elif k.startswith("paired_mean"):
            _require(v is None or _finite(v) and -1 <= v <= 1, "INVALID_PUBLIC_EFFECT")
    schedule_keys = ("scheduled_formation_count", "source_excluded_formation_count", "source_qualified_formation_count",
                     "provided_formation_count", "opportunity_formation_count", "no_opportunity_formation_count")
    _require(all(type(agg[k]) is int for k in schedule_keys)
             and agg["scheduled_formation_count"] == agg["source_excluded_formation_count"] + agg["source_qualified_formation_count"]
             and agg["provided_formation_count"] <= agg["source_qualified_formation_count"]
             and agg["provided_formation_count"] == agg["opportunity_formation_count"] + agg["no_opportunity_formation_count"],
             "INCONSISTENT_PUBLIC_COVERAGE")
    effects = ("paired_formation_count", "provided_baseline_entry_count", "provided_selected_entry_count",
               "provided_foregone_entry_count", "paired_mean_baseline_adverse_loss", "paired_mean_selected_adverse_loss", "paired_mean_improvement")
    if value["status"] == "REFUSED":
        _require(all(agg[k] is None for k in effects) and type(agg["refusal_count"]) is int and agg["refusal_count"] > 0,
                 "PUBLIC_REFUSAL_SALVAGE")
    else:
        _require(agg["refusal_count"] == 0
                 and agg["provided_formation_count"] == agg["source_qualified_formation_count"]
                 and type(agg["paired_formation_count"]) is int
                 and agg["paired_formation_count"] == agg["opportunity_formation_count"]
                 and all(type(agg[k]) is int for k in effects[:4])
                 and agg["provided_baseline_entry_count"] == agg["provided_selected_entry_count"] + agg["provided_foregone_entry_count"],
                 "INCONSISTENT_PUBLIC_PAIRS")
        if agg["paired_formation_count"] == 0:
            _require(all(agg[k] is None for k in effects[4:])
                     and all(agg[k] == 0 for k in effects[1:4]), "EMPTY_SAMPLE_EFFECT")
        else:
            _require(all(_finite(agg[k]) for k in effects[4:])
                     and 0 <= agg["paired_mean_selected_adverse_loss"] <= agg["paired_mean_baseline_adverse_loss"] * 2
                     and math.isclose(agg["paired_mean_improvement"], agg["paired_mean_baseline_adverse_loss"] - agg["paired_mean_selected_adverse_loss"], abs_tol=1e-14),
                     "INCONSISTENT_PUBLIC_MEANS")
    return {**{k: value[k] for k in value if k != "aggregates"}, "aggregates": dict(agg)}


def decode_published_diagnostics(raw):
    """Read the named display field of the incumbent compiled review queue.

    This preserves an existing publication, never recreates an execution grant,
    ArtifactBinding or synthetic commission from file content.
    """
    value = _json(raw)
    _require(type(value) is dict and value.get("schema") == "research_factory.review_queue.v1"
             and value.get("authority") == "display_only", "INVALID_PUBLISHED_QUEUE")
    rows = value.get("research_diagnostics", [])
    _require(type(rows) is list and len(rows) <= 32, "INVALID_PUBLISHED_COLLECTION")
    projected = tuple(validate_public_projection(r) for r in rows)
    _require(len({r["diagnostic_id"] for r in projected}) == len(projected), "DUPLICATE_PUBLISHED_DIAGNOSTIC")
    state = value.get("research_diagnostics_state", "AVAILABLE" if rows else "DISABLED")
    _require(type(state) is str and state in ("AVAILABLE", "DISABLED", "UNAVAILABLE")
             and bool(rows) == (state == "AVAILABLE"), "INVALID_PUBLISHED_STATE")
    return projected, state
