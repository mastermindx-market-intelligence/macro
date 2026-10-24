"""Connected per-decision prefix driver; source-only engineering primitive.

The driver consumes the public ``bridge.prepare_synthetic_inputs`` result and, for
exactly one owner decision at a time, opens one fresh bounded transport session
through the accepted ``TransportOrchestrator(engine).execute(TransportSession(plan))``
path.  It never constructs a real engine, a qualification, a subprocess, a dynamic
candidate import, a shell, a filesystem discovery or an arbitrary callable runner:
the engine is always supplied by the caller, and with no engine the driver refuses
before any I/O.

The candidate ``feature`` source is opaque bounded UTF-8 bytes.  It is carried to
the container through the existing argv-only channel and is never imported,
compiled or executed by this process.  The fixed owner runner below is source text
only in this wave; it can only ever run inside an independently qualified
container, and no test here executes it.  A successful fake-transport return is
source semantics only and is never physical or scientific acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import base64
import hashlib
import json
import math
import time

from . import bridge as bridge_module
from . import transport as transport_module
from .bridge import BoundBytes
from .output_contract import validate_output_envelope

__all__ = [
    "PrefixAttempt",
    "PrefixDriverOutcome",
    "PrefixDriverRefused",
    "PrefixTransportSpec",
    "MAX_CARRIER_BYTES",
    "MAX_CHUNKS",
    "MAX_CHUNK_CHARS",
    "MAX_INPUT_BYTES",
    "MAX_SOURCE_BYTES",
    "RUNNER_SOURCE",
    "build_carrier",
    "build_header",
    "decision_operation_id",
    "run_prefix_driver",
]

CARRIER_SCHEMA = "research_codegen.prefix_carrier.v1"
HEADER_SCHEMA = "research_codegen.prefix_header.v1"
OPERATION_SCHEMA = "research_codegen.prefix_operation.v1"
INPUT_SCHEMA = "research_codegen.input.v1"
OUTPUT_SCHEMA = "research_codegen.output.v1"
SCHEDULE_SCHEMA = "research_codegen.schedule.v1"

# Engineering refusal ceilings for the argv-only carrier.  These are not a
# scientific sample floor; they exist so the carrier always fits the accepted
# transport plan limits (4096 characters per item, at most 64 argv items).
MAX_SOURCE_BYTES = 16384
MAX_INPUT_BYTES = 98304
MAX_CARRIER_BYTES = 131072
MAX_CHUNK_CHARS = 4096
MAX_CHUNKS = 43
_MAX_ARGV_ITEMS = 64
_MAX_ATTEMPTS = 4096
_MAX_REASON_CHARS = 128
_ROW_KEYS = frozenset({"decision_id", "status", "value", "reason"})
_ROW_STATUSES = ("available", "missing", "warmup", "refused", "failed")
_HEADER_KEYS = frozenset({"schema", "carrier_bytes", "carrier_sha256", "carrier_b64_chars",
                          "carrier_b64_sha256", "chunks", "source_bytes", "source_sha256",
                          "input_bytes", "input_sha256"})
_CARRIER_KEYS = frozenset({"schema", "source_b64", "input_b64"})

# Fixed ASCII owner runner for the image's ``python -c`` entrypoint.  It has the
# fixed ``feature(input_envelope)`` interface, no label or config filesystem path,
# and emits one closed output envelope on stdout.  Source text only in this wave.
RUNNER_SOURCE = """\
import base64, hashlib, json, math, sys
HEADER_KEYS = {"schema", "carrier_bytes", "carrier_sha256", "carrier_b64_chars",
               "carrier_b64_sha256", "chunks", "source_bytes", "source_sha256",
               "input_bytes", "input_sha256"}
CARRIER_KEYS = {"schema", "source_b64", "input_b64"}
ROW_KEYS = {"decision_id", "status", "value", "reason"}
ROW_STATUS = ("available", "missing", "warmup", "refused", "failed")
def _reject(_):
    raise ValueError("NONFINITE_JSON")
def pairs(rows):
    out = {}
    for key, value in rows:
        if key in out:
            raise SystemExit("DUPLICATE_KEY")
        out[key] = value
    return out
def bounded(text):
    return json.loads(text, object_pairs_hook=pairs, parse_constant=_reject)
def parse_header(text):
    header = bounded(text)
    if type(header) is not dict or set(header) != HEADER_KEYS or header["schema"] != "research_codegen.prefix_header.v1":
        raise SystemExit("HEADER_SCHEMA")
    return header
def finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False
def main(argv):
    if len(argv) < 3:
        raise SystemExit("ARGV_REQUIRED")
    header = parse_header(argv[1])
    body = "".join(argv[2:])
    if len(argv) - 2 != header["chunks"] or len(body) != header["carrier_b64_chars"]:
        raise SystemExit("CARRIER_COUNT")
    if hashlib.sha256(body.encode("ascii")).hexdigest() != header["carrier_b64_sha256"]:
        raise SystemExit("CARRIER_HASH")
    carrier = base64.b64decode(body.encode("ascii"), validate=True)
    if len(carrier) != header["carrier_bytes"]:
        raise SystemExit("CARRIER_HASH")
    if hashlib.sha256(carrier).hexdigest() != header["carrier_sha256"]:
        raise SystemExit("CARRIER_HASH")
    parts = bounded(carrier.decode("utf-8"))
    if set(parts) != CARRIER_KEYS or parts["schema"] != "research_codegen.prefix_carrier.v1":
        raise SystemExit("CARRIER_SCHEMA")
    source = base64.b64decode(parts["source_b64"].encode("ascii"), validate=True)
    payload = base64.b64decode(parts["input_b64"].encode("ascii"), validate=True)
    if len(source) != header["source_bytes"]:
        raise SystemExit("SOURCE_HASH")
    if hashlib.sha256(source).hexdigest() != header["source_sha256"]:
        raise SystemExit("SOURCE_HASH")
    if len(payload) != header["input_bytes"]:
        raise SystemExit("INPUT_HASH")
    if hashlib.sha256(payload).hexdigest() != header["input_sha256"]:
        raise SystemExit("INPUT_HASH")
    envelope = bounded(payload.decode("utf-8"))
    if envelope.get("schema") != "research_codegen.input.v1":
        raise SystemExit("INPUT_SCHEMA")
    scope = {"__name__": "candidate_feature"}
    exec(compile(source.decode("utf-8"), "<owner-carried-source>", "exec"), scope)
    feature = scope.get("feature")
    if not callable(feature):
        raise SystemExit("FEATURE_REQUIRED")
    row = feature(envelope)
    if type(row) is not dict or set(row) != ROW_KEYS or row["status"] not in ROW_STATUS:
        raise SystemExit("ROW_SCHEMA")
    if type(row["decision_id"]) is not str or not 0 < len(row["decision_id"]) <= 128:
        raise SystemExit("ROW_ID")
    status, value, reason = row["status"], row["value"], row["reason"]
    if status == "available":
        if not finite(value) or reason is not None:
            raise SystemExit("ROW_VALUE")
    elif value is not None or type(reason) is not str or not 0 < len(reason) <= 512:
        raise SystemExit("ROW_REASON")
    print(json.dumps({"schema": "research_codegen.output.v1",
        "candidate_id": envelope["candidate_id"], "fold_id": envelope["fold_id"],
        "entity_id": envelope["entity_id"],
        "input_policy_sha256": envelope["input_policy_sha256"], "rows": [
        {"decision_id": row["decision_id"], "status": status,
         "value": value if status == "available" else None,
         "reason": None if status == "available" else reason}]},
        sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=True))
main(sys.argv)
"""


class PrefixDriverRefused(ValueError):
    """Closed, non-activating driver refusal raised before any transport effect."""


def _require(condition, reason):
    if not condition:
        raise PrefixDriverRefused(reason)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _pairs(rows):
    result = {}
    for key, value in rows:
        _require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _nonfinite(_):
    raise PrefixDriverRefused("NONFINITE_JSON")


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _bytes(value, limit, name):
    _require(type(value) is bytes and 0 < len(value) <= limit, name + "_BYTES_REQUIRED")
    return value


def _walk(value, limit):
    """Refuse anything that is not a bounded tree of exact built-in JSON types."""
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(depth <= 16 and count <= limit, "JSON_STRUCTURE_LIMIT")
        if type(item) is dict:
            _require(all(type(k) is str and len(k) <= 128 for k in item), "JSON_KEY_LIMIT")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _require(len(item) <= 4096, "JSON_STRING_LIMIT")
        elif item is not None and type(item) is not bool:
            _require(_finite(item), "NONFINITE_JSON")


def build_header(source_raw, input_raw, carrier_raw, carrier_b64):
    """Fixed carrier header; count, raw byte and digest identities are closed."""
    return _canonical({"schema": HEADER_SCHEMA,
                       "carrier_bytes": len(carrier_raw),
                       "carrier_sha256": hashlib.sha256(carrier_raw).hexdigest(),
                       "carrier_b64_chars": len(carrier_b64),
                       "carrier_b64_sha256": hashlib.sha256(carrier_b64.encode("ascii")).hexdigest(),
                       "chunks": -(-len(carrier_b64) // MAX_CHUNK_CHARS),
                       "source_bytes": len(source_raw),
                       "source_sha256": hashlib.sha256(source_raw).hexdigest(),
                       "input_bytes": len(input_raw),
                       "input_sha256": hashlib.sha256(input_raw).hexdigest()}).decode("ascii")


def build_carrier(source_raw, input_raw):
    """Canonical bounded ASCII argv carrier; no stdin, mount or extra flag."""
    _bytes(source_raw, MAX_SOURCE_BYTES, "SOURCE")
    _bytes(input_raw, MAX_INPUT_BYTES, "INPUT")
    carrier = _canonical({"schema": CARRIER_SCHEMA,
                          "source_b64": base64.b64encode(source_raw).decode("ascii"),
                          "input_b64": base64.b64encode(input_raw).decode("ascii")})
    _require(len(carrier) <= MAX_CARRIER_BYTES, "CARRIER_LIMIT")
    encoded_carrier = base64.b64encode(carrier).decode("ascii")
    chunks = tuple(encoded_carrier[offset:offset + MAX_CHUNK_CHARS]
                   for offset in range(0, len(encoded_carrier), MAX_CHUNK_CHARS))
    _require(0 < len(chunks) <= MAX_CHUNKS, "CHUNK_COUNT")
    header = build_header(source_raw, input_raw, carrier, encoded_carrier)
    argv = ("-c", RUNNER_SOURCE, header, *chunks)
    _require(len(argv) <= _MAX_ARGV_ITEMS, "ARGV_COUNT")
    return argv, header, carrier


def decision_operation_id(prepared, task, carrier):
    """Stable operation identity from root, candidate, fold, entity, decision, input.

    Deterministic, so uncertainty is never resolved by minting a replacement
    identity: an owner retry of the same decision keeps the same operation id.
    """
    body = _canonical({"schema": OPERATION_SCHEMA,
                       "original_root_id": prepared.identity.original_root_id,
                       "candidate_id": prepared.identity.candidate_id,
                       "source_sha256": prepared.identity.source_sha256,
                       "config_sha256": prepared.identity.config_sha256,
                       "fold_id": task.fold_id, "entity_id": task.entity_id,
                       "decision_id": task.decision_id,
                       "input_sha256": task.input_bytes.sha256,
                       "request_sha256": task.request.sha256,
                       "carrier_sha256": hashlib.sha256(carrier).hexdigest()})
    return "prefix-" + hashlib.sha256(body).hexdigest()


@dataclass(frozen=True)
class PrefixTransportSpec:
    """Owner-selected exact resources.  Every field is required on purpose: the
    driver supplies no default that could activate an effect or a runtime flag
    coming from the candidate."""

    image: str
    entrypoint: str
    docker_binary: str
    uid: int
    gid: int
    pids_limit: int
    memory_bytes: int
    cpus: float
    wall_clock_seconds: float
    output_cap_bytes: int
    tmpfs_bytes: int
    stop_timeout_seconds: float
    max_attempts: int
    total_wall_seconds: float


@dataclass(frozen=True)
class PrefixAttempt:
    """Frozen receipt of one bounded per-decision transport attempt."""

    operation_id: str
    plan_sha256: str
    container_id: str | None
    state: str
    workload_confirmed: bool
    workload_returncode: int | None
    execution_uncertain: bool
    reconciliation_required: bool
    cleanup_confirmed: bool
    output_sha256: str | None
    output_bytes: int
    fold_id: str
    entity_id: str
    decision_id: str
    input_sha256: str
    detail: str
    transport_plan: transport_module.TransportPlan
    transport_attempt: transport_module.TransportAttempt


@dataclass(frozen=True)
class PrefixDriverOutcome:
    """Frozen per-decision driver receipt; never a scientific acceptance."""

    identity: bridge_module.PreparedIdentity
    attempts: tuple[PrefixAttempt, ...]
    outputs: tuple[BoundBytes, ...]
    completed: bool
    refusal_reasons: tuple[str, ...]
    source_sha256: str
    config_sha256: str
    total_wall_seconds: float


def _transport_error(exc):
    return PrefixDriverRefused("TRANSPORT_PLAN_REFUSED:" + type(exc).__name__)


def _plan_for(spec, operation_id, argv):
    try:
        return transport_module.TransportPlan(
            operation_id=operation_id, image=spec.image, entrypoint=spec.entrypoint,
            argv=tuple(argv), docker_binary=spec.docker_binary, uid=spec.uid, gid=spec.gid,
            pids_limit=spec.pids_limit, memory_bytes=spec.memory_bytes, cpus=spec.cpus,
            wall_clock_seconds=spec.wall_clock_seconds, output_cap_bytes=spec.output_cap_bytes,
            tmpfs_bytes=spec.tmpfs_bytes, stop_timeout_seconds=spec.stop_timeout_seconds)
    except transport_module.TransportError as exc:
        raise _transport_error(exc) from exc


def worst_case_attempt_seconds(plan):
    """Reserve the same immutable plan's maximum command envelope.

    Accepted transport b6d36717 has CREATE, attached workload, workload-state
    INSPECT, STOP, conditional KILL, REMOVE, and absence INSPECT: seven calls.
    collect_process additionally permits two 5-second direct-client reap waits
    per call after its deadline. Include that existing allowance; grant nothing.
    A supplied engine violating these bounds still fails the final elapsed guard.
    """
    _require(type(plan) is transport_module.TransportPlan, "EXACT_TRANSPORT_PLAN_REQUIRED")
    return (transport_module.CREATE_DEADLINE_SECONDS + plan.wall_clock_seconds
            + 2 * transport_module.INSPECT_DEADLINE_SECONDS
            + transport_module.STOP_DEADLINE_SECONDS
            + transport_module.KILL_DEADLINE_SECONDS
            + transport_module.REMOVE_DEADLINE_SECONDS + 7 * (5.0 + 5.0))


def _parse_output(raw, cap):
    """Exact bounded UTF-8 JSON: no duplicate key, trailing text, nonfinite or subclass."""
    _require(type(raw) is bytes and 0 < len(raw) <= cap, "OUTPUT_BYTES_REQUIRED")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PrefixDriverRefused("INVALID_OUTPUT_JSON") from exc
    _walk(value, 4096)
    return value


def _one_decision_schedule(identity, task):
    return {"schema": SCHEDULE_SCHEMA, "candidate_id": identity.candidate_id,
            "fold_id": task.fold_id, "entity_id": task.entity_id,
            "input_policy_sha256": identity.input_policy_sha256,
            "decision_ids": [task.decision_id]}


def _owner_schedule(identity, group):
    return {"schema": SCHEDULE_SCHEMA, "candidate_id": identity.candidate_id,
            "fold_id": group.fold_id, "entity_id": group.entity_id,
            "input_policy_sha256": identity.input_policy_sha256,
            "decision_ids": list(group.decision_ids)}


def _adopt(attempt, plan, identity, task, cap):
    """Adopt only a fully confirmed, identity-matching, clean single-row envelope."""
    if not (attempt.state is transport_module.AttemptState.CLEANED_SUCCESS
            and attempt.workload_confirmed is True and attempt.workload_returncode == 0
            and attempt.execution_uncertain is False and attempt.reconciliation_required is False
            and attempt.cleanup_confirmed is True and attempt.workload_problem is None
            and attempt.operation_id == plan.operation_id
            and attempt.plan_sha256 == transport_module.plan_identity(plan)
            and type(attempt.container_id) is str):
        raise PrefixDriverRefused("TRANSPORT_ATTEMPT_NOT_CONFIRMED")
    envelope = _parse_output(attempt.workload_output, cap)
    schedule = _one_decision_schedule(identity, task)
    _require(not validate_output_envelope(envelope, trusted_schedule=schedule),
             "OUTPUT_CONTRACT_REFUSED")
    return envelope["rows"][0]


def run_prefix_driver(prepared, *, source, engine, spec, config_sha256=None):
    """Run the exact per-decision prefix workload and return grouped owner outputs.

    ``source`` is opaque bounded UTF-8 candidate bytes bound to the retained source
    identity; it is never imported, compiled or executed here.  ``engine`` is always
    caller-supplied: with no engine the driver refuses before any I/O and constructs
    nothing.  Every task is validated and planned before the first attempt, new
    attempts stop on any uncertain outcome, permission refusal, budget cap or
    non-adopted receipt, and the exact attempts are retained.  Non-available rows
    keep their original status; nothing is zero-filled, dropped, salvaged or ranked.
    """
    _require(type(prepared) is bridge_module.PreparedSyntheticInputs,
             "EXACT_PREPARED_INPUTS_REQUIRED")
    _require(type(source) is BoundBytes, "EXACT_BYTE_BINDING_REQUIRED")
    _require(type(spec) is PrefixTransportSpec, "EXACT_TRANSPORT_SPEC_REQUIRED")
    _require(engine is not None and not callable(engine)
             and callable(getattr(engine, "run", None)), "TRANSPORT_ENGINE_REQUIRED")
    identity = prepared.identity
    _require(type(identity) is bridge_module.PreparedIdentity, "INVALID_PREPARED_IDENTITY")
    _require(type(config_sha256) is str and len(config_sha256) == 64
             and all(c in "0123456789abcdef" for c in config_sha256),
             "CONFIG_IDENTITY_REQUIRED")
    _require(config_sha256 == identity.config_sha256, "CONFIG_IDENTITY_MISMATCH")
    _require(source.sha256 == identity.source_sha256
             and source.size == len(source.raw) and 0 < source.size <= MAX_SOURCE_BYTES,
             "SOURCE_IDENTITY_MISMATCH")
    _require(hashlib.sha256(source.raw).hexdigest() == source.sha256, "SOURCE_DIGEST_MISMATCH")
    try:
        source.raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PrefixDriverRefused("SOURCE_UTF8_REQUIRED") from exc
    _require(type(prepared.decisions) is tuple and type(prepared.schedules) is tuple
             and type(prepared.session_dates) is tuple, "INVALID_PREPARED_COLLECTION")
    _require(len(prepared.decisions) <= _MAX_ATTEMPTS, "DECISION_COUNT_LIMIT")
    _require(type(spec.max_attempts) is int and 0 < spec.max_attempts <= _MAX_ATTEMPTS,
             "ATTEMPT_BUDGET_INVALID")
    _require(type(spec.total_wall_seconds) is float or type(spec.total_wall_seconds) is int,
             "ATTEMPT_BUDGET_INVALID")
    _require(_finite(spec.total_wall_seconds)
             and 0 < spec.total_wall_seconds <= transport_module.MAX_WALL_SECONDS,
             "ATTEMPT_BUDGET_INVALID")
    # Validate and plan every task before the first transport effect.
    tasks = []
    for task in prepared.decisions:
        _require(type(task) is bridge_module.PreparedDecisionInput, "EXACT_PREPARED_TASK_REQUIRED")
        _bytes(task.input_bytes.raw, MAX_INPUT_BYTES, "INPUT")
        _require(task.input_bytes.sha256 == hashlib.sha256(task.input_bytes.raw).hexdigest()
                 and task.input_bytes.size == len(task.input_bytes.raw), "INPUT_DIGEST_MISMATCH")
        argv, header, carrier = build_carrier(source.raw, task.input_bytes.raw)
        tasks.append((task, argv, header, carrier,
                      decision_operation_id(prepared, task, carrier)))
    plans = tuple((task, argv, header, carrier, operation, _plan_for(spec, operation, argv))
                  for task, argv, header, carrier, operation in tasks)
    started = time.monotonic()
    attempts, rows, reasons = [], [], []
    for task, argv, header, carrier, operation, plan in plans:
        if len(attempts) >= spec.max_attempts:
            reasons.append("ATTEMPT_BUDGET_EXHAUSTED")
            break
        elapsed = time.monotonic() - started
        if (spec.total_wall_seconds - elapsed) < worst_case_attempt_seconds(plan):
            reasons.append("WALL_BUDGET_EXHAUSTED")
            break
        try:
            attempt = transport_module.TransportOrchestrator(engine).execute(
                transport_module.TransportSession(plan))
        except transport_module.TransportError as exc:
            reasons.append("TRANSPORT_REFUSED:" + type(exc).__name__)
            break
        adopted = None
        problem = None
        try:
            adopted = _adopt(attempt, plan, identity, task, spec.output_cap_bytes)
        except PrefixDriverRefused as exc:
            problem = str(exc)
        record = PrefixAttempt(
            operation_id=attempt.operation_id, plan_sha256=attempt.plan_sha256,
            container_id=attempt.container_id, state=attempt.state.value,
            workload_confirmed=attempt.workload_confirmed,
            workload_returncode=attempt.workload_returncode,
            execution_uncertain=attempt.execution_uncertain,
            reconciliation_required=attempt.reconciliation_required,
            cleanup_confirmed=attempt.cleanup_confirmed,
            output_sha256=(hashlib.sha256(attempt.workload_output).hexdigest()
                           if attempt.workload_output else None),
            output_bytes=len(attempt.workload_output),
            fold_id=task.fold_id, entity_id=task.entity_id, decision_id=task.decision_id,
            input_sha256=task.input_bytes.sha256,
            detail=(problem or attempt.detail)[:_MAX_REASON_CHARS],
            transport_plan=plan, transport_attempt=attempt)
        attempts.append(record)
        if adopted is None:
            reasons.append(record.detail)
            break
        rows.append((task, adopted))
    grouped, order = {}, []
    for task, row in rows:
        group = (task.fold_id, task.entity_id)
        if group not in grouped:
            grouped[group] = []
            order.append(group)
        grouped[group].append(row)
    elapsed_total = time.monotonic() - started
    if not _finite(elapsed_total) or elapsed_total > spec.total_wall_seconds:
        if "WALL_BUDGET_EXHAUSTED" not in reasons:
            reasons.append("WALL_BUDGET_EXHAUSTED")
    outputs, complete = (), len(rows) == len(prepared.decisions) and not reasons
    if complete:
        for group in prepared.schedules:
            members = grouped.get((group.fold_id, group.entity_id), [])
            envelope = {"schema": OUTPUT_SCHEMA, "candidate_id": identity.candidate_id,
                        "fold_id": group.fold_id, "entity_id": group.entity_id,
                        "input_policy_sha256": identity.input_policy_sha256,
                        "rows": list(members)}
            _require(not validate_output_envelope(envelope, trusted_schedule=_owner_schedule(identity, group)),
                     "GROUPED_OUTPUT_CONTRACT_REFUSED")
            raw = _canonical(envelope)
            outputs = (*outputs, BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw)))
    return PrefixDriverOutcome(identity, tuple(attempts), outputs, complete,
                               tuple(reasons), source.sha256, config_sha256,
                               elapsed_total)


def connect_prepared_outputs(run, outcome, *, commission=None):
    """Replace only the run's outputs with driver results and recompute.

    The parent keeps ``run.paths``, the evaluation labels and every other retained
    fixture; no future or evaluator value ever enters the workload carrier.  An
    incomplete driver outcome never replaces outputs, so the whole-run diagnostic
    refuses instead of settling unknown cells by dropping rows.
    """
    _require(type(run) is bridge_module.SyntheticRun, "EXACT_SYNTHETIC_RUN_REQUIRED")
    _require(type(outcome) is PrefixDriverOutcome, "EXACT_DRIVER_OUTCOME_REQUIRED")
    prepared = bridge_module.prepare_synthetic_inputs(run, commission=commission)
    _require(type(outcome.identity) is bridge_module.PreparedIdentity
             and outcome.identity == prepared.identity
             and outcome.source_sha256 == prepared.identity.source_sha256
             and outcome.config_sha256 == prepared.identity.config_sha256,
             "DRIVER_OUTCOME_IDENTITY_MISMATCH")
    _require(outcome.completed and len(outcome.outputs) == len(run.schedules),
             "DRIVER_OUTCOME_INCOMPLETE")
    return bridge_module.compute_synthetic_diagnostic(
        replace(run, outputs=outcome.outputs), commission=commission)
