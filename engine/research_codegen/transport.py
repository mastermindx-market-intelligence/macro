"""Dormant trusted Docker transport preparation.

Only trusted owner constants form TransportPlan; no candidate envelope selects
commands, environment, mounts or admission. Real-engine public calls refuse:
qualification issuance does not exist and source constant stays false. The
prepared CLI collector binding is unreachable until a separately reviewed
source change; this guard is not a sandbox or authenticated capability service.

The injected synthetic engine path attaches bounded output, independently
inspects the exact container exit state, and finally cleans that same ID.
Workload outcome survives cleanup and reconciliation. Every attempt remains
single-use; uncertain create never starts or creates a replacement. Caller
must retain original receipts across interruption; there is no new job registry.

Engine/container configuration and namespace labels are not containment proof.
Image origin/default volumes/env/entrypoint qualification, effective host policy,
identity/review controls and RF-16 acceptance remain external reserved gates.
"""
from __future__ import annotations

import enum
import json
import hashlib
import math
import os
import re
import select
import subprocess
import time
import types
from dataclasses import dataclass, replace, asdict
from typing import Optional, Protocol, Sequence, Tuple

__all__ = [
    "AttemptState",
    "EngineCommandResult",
    "ProcessResult",
    "TransportAttempt",
    "TransportDormantError",
    "TransportEngine",
    "TransportEngineError",
    "TransportOrchestrator",
    "TransportPlan",
    "TransportPlanError",
    "TransportQualification",
    "TransportSession",
    "TransportStateError",
    "SubprocessDockerEngine",
    "build_create_argv",
    "build_inspect_argv",
    "build_kill_argv",
    "build_remove_argv",
    "build_start_argv",
    "build_stop_argv",
    "collect_process",
    "parse_container_absence",
    "parse_container_id",
]

# --------------------------------------------------------------------------
# Bounded constants.  All limits are hardcoded module constants; none are read
# from the environment, a file, or a plan field.
# --------------------------------------------------------------------------

_MAX_TEXT_LEN = 4096
_MAX_PATH_LEN = 1024
_MAX_ARGV_ITEMS = 64
_MAX_UID = 2 ** 31 - 1

MAX_MEMORY_BYTES = 2 * 1024 ** 3            # 2 GiB
MAX_PIDS = 1024
MAX_CPUS = 4.0
MAX_WALL_SECONDS = 600.0
MAX_OUTPUT_BYTES = 8 * 1024 * 1024          # 8 MiB
MAX_TMPFS_BYTES = 256 * 1024 * 1024         # 256 MiB
MAX_STOP_TIMEOUT_SECONDS = 120.0

CREATE_DEADLINE_SECONDS = 120.0
START_DEADLINE_SECONDS = 60.0
STOP_DEADLINE_SECONDS = 60.0
KILL_DEADLINE_SECONDS = 60.0
REMOVE_DEADLINE_SECONDS = 60.0
INSPECT_DEADLINE_SECONDS = 30.0

_TMPFS_MOUNT = "/tmp"
_TMPFS_MODE = "rw,noexec,nosuid"

# Closed installed absence grammar for the container-specific inspect path.
# Captured read-only from the admitted host interface (docker CLI 29.1.3,
# `inspect --type container <missing full id>`): rc 1, known empty JSON
# stdout "[]", and the single retained daemon error line below.  The generic
# autodetect "No such object" form is a different protocol and is refused.
CONTAINER_ABSENCE_STDOUT_LINE = b"[]"
CONTAINER_ABSENCE_ERROR_LINE_PREFIX = (
    "Error response from daemon: No such container: "
)

_CONTAINER_ID_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_OPERATION_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_IMAGE_REPO_RE = re.compile(
    r"\A[a-z0-9][a-z0-9._-]*(?::[0-9]+)?(?:/[a-z0-9._-]+)*\Z"
)
_IMAGE_DIGEST_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_NAME_COMPONENT_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")
_ARGV_ITEM_RE = re.compile(r"\A[\x20-\x7e]{1,1024}\Z")

# Fixed minimal environment for any locally spawned helper client.  Nothing is
# inherited from os.environ.
MINIMAL_CLIENT_ENV = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "LANG": "C",
}

# Hard, non-configurable dormancy switch for this preparation wave.  It is a
# module constant with no issuer anywhere: it is never read from the
# environment, a file, argv, or a plan field.
_QUALIFICATION_ISSUED = False


# --------------------------------------------------------------------------
# Typed errors
# --------------------------------------------------------------------------

class TransportError(Exception):
    """Base class for all typed transport failures."""


class TransportPlanError(TransportError):
    """A plan, argv or identifier failed trusted-shape validation."""


class TransportDormantError(TransportError):
    """Explicit typed refusal: the real engine is dormant in this wave."""


class TransportStateError(TransportError):
    """Attempt reuse, identity mismatch or another state-machine violation."""


class TransportPermissionRefusal(TransportError):
    """Trusted engine reports an actual permission boundary; no alternate mutation."""


class TransportEngineError(TransportError):
    """Malformed engine result (retained as uncertainty by the orchestrator)."""


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

def _require_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise TransportPlanError(
            f"{name} must be an exact int, not {type(value).__name__}"
            " (bool is never accepted)"
        )
    if value < minimum or value > maximum:
        raise TransportPlanError(
            f"{name} out of bounded range [{minimum}, {maximum}]: {value}"
        )
    return value


def _require_number(
    value: object, name: str, minimum: float, maximum: float
) -> float:
    if isinstance(value, bool) or type(value) not in (int, float):
        raise TransportPlanError(
            f"{name} must be a finite number, not {type(value).__name__}"
        )
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise TransportPlanError(f"{name} exceeds finite numeric bounds") from None
    if not math.isfinite(number):
        raise TransportPlanError(f"{name} must be finite, got {value!r}")
    if number <= minimum or number > maximum:
        raise TransportPlanError(
            f"{name} out of bounded range ({minimum}, {maximum}]: {value!r}"
        )
    return number


def _require_plain_text(value: object, name: str, maximum: int) -> str:
    if isinstance(value, bool) or type(value) is not str:
        raise TransportPlanError(f"{name} must be a str, got {type(value).__name__}")
    if not value or len(value) > maximum:
        raise TransportPlanError(f"{name} must be 1..{maximum} characters")
    for char in value:
        if ord(char) < 0x20 or ord(char) > 0x7E:
            raise TransportPlanError(
                f"{name} contains control/non-ASCII text at index "
                f"{value.index(char)}"
            )
    return value


def _require_owner_script(value: object, name: str, maximum: int) -> str:
    """Bounded fixed Python source chosen by owner, never from candidate envelopes."""
    if type(value) is not str or not value or len(value) > maximum:
        raise TransportPlanError(name + " must be bounded exact owner text")
    if any((ord(c) < 32 and c not in "\n\t") or ord(c) > 126 for c in value):
        raise TransportPlanError(name + " contains invalid owner text")
    return value


def _validate_abs_path(value: object, name: str) -> str:
    _require_plain_text(value, name, _MAX_PATH_LEN)
    if not value.startswith("/"):
        raise TransportPlanError(f"{name} must be an absolute path: {value!r}")
    for part in value.split("/")[1:]:
        if not part or part in (".", ".."):
            raise TransportPlanError(
                f"{name} contains an empty, '.' or '..' path component: {value!r}"
            )
        if _NAME_COMPONENT_RE.fullmatch(part) is None:
            raise TransportPlanError(
                f"{name} has a component with unsupported characters: {part!r}"
            )
    return value


def _validate_image(value: object) -> str:
    _require_plain_text(value, "image", _MAX_TEXT_LEN)
    if value.count("@") != 1:
        raise TransportPlanError(
            "image must be exactly one '<repo>@sha256:<64 lowercase hex>'"
            f" immutable reference, got: {value!r}"
        )
    repo, _, digest_part = value.partition("@")
    algorithm, sep, digest = digest_part.partition(":")
    if algorithm != "sha256" or not sep:
        raise TransportPlanError(
            f"image digest must use the sha256 algorithm: {value!r}"
        )
    if _IMAGE_DIGEST_RE.fullmatch(digest) is None:
        raise TransportPlanError(
            "image digest must be exactly 64 lowercase hex digits:"
            f" {digest_part!r}"
        )
    if _IMAGE_REPO_RE.fullmatch(repo) is None:
        raise TransportPlanError(f"image repository is not acceptable: {repo!r}")
    for part in repo.split("/"):
        if part in (".", ".."):
            raise TransportPlanError(
                f"image repository contains a '.' or '..' component: {repo!r}"
            )
    return value


def _require_container_id(value: object) -> str:
    if isinstance(value, bool) or type(value) is not str:
        raise TransportPlanError(
            f"container id must be a str, got {type(value).__name__}"
        )
    if _CONTAINER_ID_RE.fullmatch(value) is None:
        raise TransportPlanError(
            "container id must be exactly 64 lowercase hex digits,"
            f" got {value!r}"
        )
    return value


def parse_container_id(stdout: object) -> Optional[str]:
    """Parse the full 64-hex container id from bounded create stdout.

    Returns ``None`` for anything that is not exactly one id (surrounding
    whitespace tolerated): wrong length, non-hex, uppercase, embedded junk,
    non-ASCII or truncated bytes.
    """
    if not isinstance(stdout, (bytes, bytearray)):
        return None
    try:
        text = bytes(stdout).decode("ascii")
    except UnicodeDecodeError:
        return None
    stripped = text.strip()
    if _CONTAINER_ID_RE.fullmatch(stripped) is None:
        return None
    return stripped


def parse_container_absence(stdout: object, stderr: object, cid: object) -> bool:
    """Decide container-specific absence with the closed installed grammar.

    Accepts only the exact retained daemon error line for this exact full
    64-hex id -- ``Error response from daemon: No such container: <cid>`` --
    plus at most the known empty JSON stdout ``[]``.  Any other line, wrong
    id, embedded or partial id, generic ``No such object`` text, extra error
    payload or permission text is refused.  Retained bytes are only split on
    newlines for matching; they are never normalized or re-stamped.
    """
    if type(stdout) is not bytes or type(stderr) is not bytes:
        return False
    if type(cid) is not str or _CONTAINER_ID_RE.fullmatch(cid) is None:
        return False
    error_line = (CONTAINER_ABSENCE_ERROR_LINE_PREFIX + cid).encode("ascii")
    lines = (stdout + stderr).split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    # The installed container-specific command emits one error, optionally
    # preceded by its one empty-JSON stdout line.  Repeated or reordered
    # lines are a different/contradictory control response, never absence.
    return lines in ([error_line], [CONTAINER_ABSENCE_STDOUT_LINE, error_line])


# --------------------------------------------------------------------------
# TransportPlan
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class TransportPlan:
    """Immutable, trusted-owner-selected plan for one bounded operation.

    Construction validates shape only.  Validation is inert: it never grants
    transport admission, never enables the dormant engine, and never replaces
    the absent image/defaultvolumes/env/entrypoint qualification proof.
    """

    operation_id: str
    image: str
    entrypoint: str
    argv: Tuple[str, ...]
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

    def __post_init__(self) -> None:
        operation_id = _require_plain_text(
            self.operation_id, "operation_id", 128
        )
        if _OPERATION_ID_RE.fullmatch(operation_id) is None:
            raise TransportPlanError(
                "operation_id must match [A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
                f" (no leading '-'): {operation_id!r}"
            )
        object.__setattr__(self, "operation_id", operation_id)

        object.__setattr__(self, "image", _validate_image(self.image))
        object.__setattr__(self, "entrypoint", _validate_abs_path(
            self.entrypoint, "entrypoint"
        ))
        if self.entrypoint.rsplit("/", 1)[-1] in {"sh", "bash", "dash", "zsh", "ksh", "fish"}:
            raise TransportPlanError("a shell cannot be the trusted entrypoint")

        argv = self.argv
        if type(argv) is not tuple:
            raise TransportPlanError("argv must be a tuple of str items")
        if len(argv) > _MAX_ARGV_ITEMS:
            raise TransportPlanError(
                f"argv exceeds {_MAX_ARGV_ITEMS} items: {len(argv)}"
            )
        checked_argv = []
        for index, item in enumerate(argv):
            if index > 0 and argv[index - 1] == "-c" and self.entrypoint.rsplit("/", 1)[-1] in {"python3", "python", "env"}:
                _require_owner_script(item, f"argv[{index}]", _MAX_TEXT_LEN)
            else:
                _require_plain_text(item, f"argv[{index}]", _MAX_TEXT_LEN)
            if item.rsplit("/", 1)[-1] in {"sh", "bash", "dash", "zsh", "ksh", "fish"}:
                raise TransportPlanError("shell executable is not an admitted owner argv")
            checked_argv.append(item)
        object.__setattr__(self, "argv", tuple(checked_argv))

        object.__setattr__(self, "docker_binary", _validate_abs_path(
            self.docker_binary, "docker_binary"
        ))

        _require_int(self.uid, "uid", 1, _MAX_UID)
        _require_int(self.gid, "gid", 1, _MAX_UID)
        _require_int(self.pids_limit, "pids_limit", 1, MAX_PIDS)
        _require_int(self.memory_bytes, "memory_bytes", 1, MAX_MEMORY_BYTES)
        _require_int(
            self.output_cap_bytes, "output_cap_bytes", 1, MAX_OUTPUT_BYTES
        )
        _require_int(self.tmpfs_bytes, "tmpfs_bytes", 1, MAX_TMPFS_BYTES)
        _require_number(self.cpus, "cpus", 0.000999, MAX_CPUS)
        _require_number(
            self.wall_clock_seconds, "wall_clock_seconds", 0.0, MAX_WALL_SECONDS
        )
        _require_number(
            self.stop_timeout_seconds,
            "stop_timeout_seconds",
            0.0,
            MAX_STOP_TIMEOUT_SECONDS,
        )


def plan_identity(plan: TransportPlan) -> str:
    if type(plan) is not TransportPlan:
        raise TransportPlanError("exact immutable original TransportPlan required")
    body = json.dumps({"schema": "transport.plan.identity.v1", "fields": asdict(plan)},
                      sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    return hashlib.sha256(body).hexdigest()


# --------------------------------------------------------------------------
# Fixed argv builders (pure, no I/O, never a shell)
# --------------------------------------------------------------------------

def _format_cpus(cpus: float) -> str:
    text = format(cpus, ".9g")
    return text


def _stop_timeout_flag(plan: TransportPlan) -> str:
    seconds = int(math.ceil(plan.stop_timeout_seconds))
    return str(max(1, seconds))


def build_create_argv(plan: TransportPlan) -> Tuple[str, ...]:
    """Build the fixed bounded CREATE argv.  Create and start stay separate."""
    return (
        plan.docker_binary,
        "create",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--no-healthcheck", "--log-driver=none", "--restart=no",
        "--cgroupns=private", "--ipc=private",
        "--user", f"{plan.uid}:{plan.gid}",
        "--pids-limit", str(plan.pids_limit),
        "--memory", str(plan.memory_bytes),
        "--memory-swap", str(plan.memory_bytes),
        "--cpus", _format_cpus(plan.cpus),
        "--tmpfs", f"{_TMPFS_MOUNT}:{_TMPFS_MODE},size={plan.tmpfs_bytes}",
        "--entrypoint", plan.entrypoint,
        "--", plan.image,
    ) + tuple(plan.argv)


def build_start_argv(plan: TransportPlan, container_id: str) -> Tuple[str, ...]:
    return (plan.docker_binary, "start", "--attach", _require_container_id(container_id))


def build_stop_argv(plan: TransportPlan, container_id: str) -> Tuple[str, ...]:
    return (
        plan.docker_binary,
        "stop",
        "--timeout",
        _stop_timeout_flag(plan),
        _require_container_id(container_id),
    )


def build_kill_argv(plan: TransportPlan, container_id: str) -> Tuple[str, ...]:
    return (plan.docker_binary, "kill", _require_container_id(container_id))


def build_remove_argv(plan: TransportPlan, container_id: str) -> Tuple[str, ...]:
    return (plan.docker_binary, "rm", _require_container_id(container_id))


def build_inspect_argv(plan: TransportPlan, container_id: str) -> Tuple[str, ...]:
    return (
        plan.docker_binary,
        "inspect",
        "--type",
        "container",
        _require_container_id(container_id),
    )


# --------------------------------------------------------------------------
# Engine protocol and results
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineCommandResult:
    """Bounded outcome of one engine command.

    ``returncode is None`` means the local client could not be reaped, which
    the orchestrator always treats as unconfirmed.  ``observed_container_id``
    is any container identity the engine itself echoed; a value that differs
    from the tracked id is rejected.
    """

    returncode: Optional[int]
    stdout: bytes
    stderr: bytes
    deadline_seconds: float
    output_cap_bytes: int
    timed_out: bool = False
    output_truncated: bool = False
    observed_container_id: Optional[str] = None
    permission_refused: bool = False
    error_type: Optional[str] = None


class TransportEngine(Protocol):
    """Bounded engine protocol: argv in, bounded result out.  No shell."""

    def run(
        self,
        argv: Sequence[str],
        *,
        deadline_seconds: float,
        output_cap_bytes: int,
    ) -> EngineCommandResult:
        ...


def control_permission_refusal(command: str, returncode: Optional[int], output: bytes) -> bool:
    """Conservative control-channel classifier, never attached workload content.

    This is a prepared CLI error mapping, not authenticated provider authority.
    An eventual real qualification must verify it against that selected interface.
    """
    if command not in {"create", "stop", "kill", "rm", "inspect"} or returncode in (None, 0):
        return False
    lowered = output.lower()
    return any(marker in lowered for marker in (
        b"permission denied", b"access denied", b"authorization denied",
        b"unauthorized", b"forbidden", b"not authorized"))


class TransportQualification:
    """Reserved trusted qualification proof for a later wave.

    No issuer exists in this source tree and construction is refused, so no
    caller -- trusted or otherwise -- can obtain an instance in this wave.
    """

    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object) -> "TransportQualification":
        raise TransportDormantError(
            "TransportQualification cannot be constructed in this wave:"
            " image qualification/defaultvolumes/env/entrypoint proof is"
            " unsettled"
        )


class SubprocessDockerEngine:
    """Prepared real Docker subprocess engine -- DORMANT in this wave.

    Every call raises :class:`TransportDormantError` before any process is
    created or inspected.  The guard is a hardcoded module constant plus the
    unconstructible qualification type; there is no environment switch, plan
    field, config file or method that enables execution.
    """

    def __init__(
        self,
        docker_binary: str,
        *,
        qualification: Optional[TransportQualification] = None,
    ) -> None:
        _validate_abs_path(docker_binary, "docker_binary")
        self._docker_binary = docker_binary
        self._qualification = qualification

    @property
    def dormant(self) -> bool:
        return True

    def run(
        self,
        argv: Sequence[str],
        *,
        deadline_seconds: float,
        output_cap_bytes: int,
    ) -> EngineCommandResult:
        if not _QUALIFICATION_ISSUED or not isinstance(
            self._qualification, TransportQualification
        ):
            raise TransportDormantError(
                "transport engine is dormant: image"
                " qualification/defaultvolumes/env/entrypoint proof absent;"
                " no process call was made"
            )
        # Prepared binding is unreachable through the public API in this wave:
        # false source constant, no qualification issuer, no environment/config switch.
        if (type(argv) is not tuple or len(argv) < 2 or argv[0] != self._docker_binary
                or argv[1] not in {"create", "start", "stop", "kill", "rm", "inspect"}):
            raise TransportPlanError("trusted Docker command binding mismatch")
        captured = collect_process(argv, deadline_seconds=deadline_seconds,
                                   output_cap_bytes=output_cap_bytes)
        # Only failed control commands have a trusted daemon/client error channel.
        # Attached candidate/workload stdout must never classify permissions.
        refused = control_permission_refusal(argv[1], captured.returncode, captured.output)
        return EngineCommandResult(captured.returncode, captured.output, b"",
            deadline_seconds, output_cap_bytes, captured.timed_out,
            captured.output_truncated, permission_refused=refused, error_type=captured.error_type)


# --------------------------------------------------------------------------
# Attempt receipts and sessions
# --------------------------------------------------------------------------

class AttemptState(enum.Enum):
    PLANNED = "planned"
    CREATE_UNCERTAIN = "create_uncertain"
    CLEANED_SUCCESS = "cleaned_success"
    CLEANED_FAILURE = "cleaned_failure"
    CLEANUP_UNCERTAIN = "cleanup_uncertain"


@dataclass(frozen=True)
class TransportAttempt:
    """Immutable receipt: one operation identity, at most one container id."""

    operation_id: str
    container_id: Optional[str]
    state: AttemptState
    reconciliation_required: bool
    detail: str
    engine_events: Tuple[str, ...] = ()
    workload_confirmed: bool = False
    workload_returncode: Optional[int] = None
    workload_output: bytes = b""
    workload_problem: Optional[str] = None
    execution_uncertain: bool = False
    cleanup_confirmed: bool = False
    plan_sha256: str = ""


class TransportSession:
    """Single-use pairing of one plan with at most one attempt.

    Guards the no-second-create rule without any registry, ledger or runtime
    job.  The session retains the original receipt for the caller.
    """

    def __init__(self, plan: TransportPlan) -> None:
        if not isinstance(plan, TransportPlan):
            raise TransportPlanError("session requires a TransportPlan")
        self._plan = plan
        self._consumed = False
        self._attempt: Optional[TransportAttempt] = None

    @property
    def plan(self) -> TransportPlan:
        return self._plan

    @property
    def consumed(self) -> bool:
        return self._consumed

    @property
    def attempt(self) -> Optional[TransportAttempt]:
        return self._attempt

    def mark_consumed(self) -> None:
        self._consumed = True

    def record(self, attempt: TransportAttempt) -> None:
        self._attempt = attempt


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

_MAX_EVENTS = 64


class TransportOrchestrator:
    """Synthetic control path; real engine stays disabled.

    Workload outcome and resource cleanup are independent retained facts.
    Attached start is bounded by the owner's workload deadline/output cap.
    Container exit status is separately inspected before finally cleanup.
    """
    def __init__(self, engine: TransportEngine) -> None:
        self._engine = engine

    def execute(self, session: TransportSession) -> TransportAttempt:
        if type(session) is not TransportSession or session.consumed:
            raise TransportStateError("one original session permits only one create")
        session.mark_consumed()
        plan, events = session.plan, []
        original_plan_sha256 = plan_identity(plan)
        result, problem = self._invoke(build_create_argv(plan), CREATE_DEADLINE_SECONDS,
                                       plan.output_cap_bytes, events, "create")
        cid = None
        if problem is None and self._confirmed(result, None, None):
            cid = parse_container_id(result.stdout)
        contradictory_identity = cid is not None and result.observed_container_id not in (None, cid)
        if cid is None or contradictory_identity:
            receipt = TransportAttempt(plan.operation_id, None, AttemptState.CREATE_UNCERTAIN,
                True, "create effect unknown or identity contradiction; no mutation or replacement", tuple(events),
                workload_problem=problem or "create failed, malformed ID, or contradictory identity", execution_uncertain=True,
                plan_sha256=original_plan_sha256)
            session.record(receipt)
            return receipt
        confirmed, exitcode, output, uncertain = False, None, b"", False
        problem = None
        try:
            if result.observed_container_id not in (None, cid):
                problem, uncertain = "create identity mismatch", True
            else:
                attached, problem = self._invoke(build_start_argv(plan, cid),
                    plan.wall_clock_seconds, plan.output_cap_bytes, events, "start")
                if attached is not None:
                    output = attached.stdout + attached.stderr
                if not self._confirmed(attached, problem, cid):
                    problem = problem or "start failed, timed out, truncated, or wrong identity"
                    uncertain = True  # CLI failure is not a proved container exit outcome.
                    events.append("start not confirmed; original outcome retained")
                else:
                    # Attach completion/CLI rc alone does not prove the container's exit code.
                    argv = (plan.docker_binary, "inspect", "--type", "container", "--format",
                            '[{{json .Id}},{{json .State}}]', cid)
                    state_result, state_problem = self._invoke(argv, INSPECT_DEADLINE_SECONDS,
                        plan.output_cap_bytes, events, "workload_state")
                    if not self._confirmed(state_result, state_problem, cid):
                        problem, uncertain = "container exit inspection unconfirmed", True
                    else:
                        try:
                            state_id, state = json.loads(state_result.stdout)
                            if (state_id != cid or type(state) is not dict
                                    or type(state.get("Running")) is not bool
                                    or type(state.get("ExitCode")) is not int
                                    or type(state.get("OOMKilled")) is not bool
                                    or state["Running"]):
                                raise ValueError("wrong identity or unsettled state")
                            exitcode = state["ExitCode"]
                            confirmed = exitcode == 0 and not state["OOMKilled"]
                            if not confirmed:
                                problem = "container returned nonzero or was OOM killed"
                        except Exception:
                            problem, uncertain = "container exit inspection malformed", True
        except Exception as exc:
            problem, uncertain = "workload exception: " + type(exc).__name__, True
        finally:
            # Every ordinary error after a known ID reaches this same-ID cleanup.
            try:
                cleaned, cleanup_problem = self._cleanup(plan, cid, events)
            except Exception as exc:
                cleaned, cleanup_problem = False, "cleanup exception: " + type(exc).__name__
        receipt = TransportAttempt(plan.operation_id, cid,
            AttemptState.CLEANED_SUCCESS if confirmed and cleaned else
                (AttemptState.CLEANED_FAILURE if cleaned else AttemptState.CLEANUP_UNCERTAIN),
            uncertain or not cleaned, cleanup_problem or problem or "workload completed; cleanup verified",
            tuple(events), confirmed, exitcode, output, problem, uncertain, cleaned, original_plan_sha256)
        session.record(receipt)
        return receipt

    def reconcile(self, plan: TransportPlan, attempt: TransportAttempt) -> TransportAttempt:
        if (type(attempt) is not TransportAttempt or attempt.operation_id != plan.operation_id
                or attempt.plan_sha256 != plan_identity(plan)):
            raise TransportStateError("changed attempt operation or immutable original plan identity rejected")
        if attempt.container_id is None:
            return attempt  # Owner must resolve original create; never guess/create a replacement.
        if attempt.cleanup_confirmed:
            return attempt
        events = []
        try:
            cleaned, problem = self._cleanup(plan, _require_container_id(attempt.container_id), events)
        except Exception as exc:
            cleaned, problem = False, "cleanup exception: " + type(exc).__name__
        # Cleanup reconciliation never changes original workload/timeout/output facts.
        return replace(attempt,
            state=AttemptState.CLEANED_SUCCESS if cleaned and attempt.workload_confirmed else
                  (AttemptState.CLEANED_FAILURE if cleaned else AttemptState.CLEANUP_UNCERTAIN),
            cleanup_confirmed=cleaned,
            reconciliation_required=attempt.execution_uncertain or not cleaned,
            detail=problem or "cleanup reconciled; original workload outcome retained",
            engine_events=attempt.engine_events + tuple(events))

    def _cleanup(self, plan, cid, events):
        stopped, stop_problem = self._invoke(build_stop_argv(plan, cid), STOP_DEADLINE_SECONDS,
                                            plan.output_cap_bytes, events, "stop")
        if stop_problem and "permission refusal" in stop_problem:
            return False, stop_problem + "; cleanup mutation frozen"
        stop_ok = self._confirmed(stopped, stop_problem, cid)
        kill_ok = True
        if not stop_ok:
            killed, kill_problem = self._invoke(build_kill_argv(plan, cid), KILL_DEADLINE_SECONDS,
                                                plan.output_cap_bytes, events, "kill")
            if kill_problem and "permission refusal" in kill_problem:
                return False, kill_problem + "; cleanup mutation frozen"
            kill_ok = self._confirmed(killed, kill_problem, cid)
        removed, remove_problem = self._invoke(build_remove_argv(plan, cid), REMOVE_DEADLINE_SECONDS,
                                               plan.output_cap_bytes, events, "rm")
        if remove_problem and "permission refusal" in remove_problem:
            return False, remove_problem + "; no mutation retry"
        remove_ok = self._confirmed(removed, remove_problem, cid)
        inspected, inspect_problem = self._invoke(build_inspect_argv(plan, cid), INSPECT_DEADLINE_SECONDS,
                                                  plan.output_cap_bytes, events, "inspect")
        absent = (inspect_problem is None and inspected is not None
                  and not inspected.timed_out and not inspected.output_truncated
                  and inspected.observed_container_id in (None, cid)
                  and inspected.returncode == 1
                  and parse_container_absence(inspected.stdout, inspected.stderr, cid))
        complete = (stop_ok or kill_ok) and remove_ok and absent
        failures = []
        if not (stop_ok or kill_ok): failures.append("stop/kill state unknown: " + (kill_problem or "nonzero or unconfirmed"))
        if not remove_ok: failures.append("remove did not confirm: " + (remove_problem or "nonzero or unconfirmed"))
        if not absent: failures.append("absence check failed: " + (inspect_problem or "container still exists or unconfirmed"))
        return complete, None if complete else "; ".join(failures)

    @staticmethod
    def _confirmed(result, error, cid):
        return (error is None and result is not None and not result.timed_out
                and not result.output_truncated and result.returncode == 0
                and (cid is None or result.observed_container_id in (None, cid)))

    def _invoke(self, argv, deadline_seconds, output_cap_bytes, events, label):
        events.append(label + ": bounded same-operation command")
        try:
            result = self._engine.run(tuple(argv), deadline_seconds=deadline_seconds,
                                      output_cap_bytes=output_cap_bytes)
        except TransportPermissionRefusal:
            return None, label + " permission refusal"
        except TransportDormantError:
            if label == "create":
                raise  # Proven source refusal before any real engine effect.
            return None, label + " dormant refusal"
        except Exception as exc:
            return None, label + " engine exception: " + type(exc).__name__
        if (type(result) is not EngineCommandResult or type(result.stdout) is not bytes
                or type(result.stderr) is not bytes or type(result.timed_out) is not bool
                or type(result.output_truncated) is not bool or type(result.permission_refused) is not bool
                or (result.returncode is not None and type(result.returncode) is not int)):
            return None, label + " malformed engine result"
        if result.permission_refused:
            return None, label + " permission refusal"
        if result.error_type is not None:
            return result, label + " client collector error"
        if len(result.stdout) + len(result.stderr) > output_cap_bytes:
            # Do not trust an engine's false truncated flag or reported cap.
            combined = (result.stdout + result.stderr)[:output_cap_bytes]
            return replace(result, stdout=combined, stderr=b"", output_truncated=True), None
        return result, None


@dataclass(frozen=True)
class ProcessResult:
    """Exact retained outcome of one bounded local client run."""

    argv: Tuple[str, ...]
    returncode: Optional[int]
    output: bytes
    timed_out: bool
    output_truncated: bool
    detail: str
    error_type: Optional[str] = None


_MAX_COLLECT_DEADLINE_SECONDS = MAX_WALL_SECONDS


def _terminate_and_reap(proc: subprocess.Popen) -> Tuple[Optional[int], str]:
    """Terminate then kill only the direct child; never our own group."""
    detail = "reaped after natural exit"
    try:
        proc.terminate()
    except PermissionError:
        return proc.poll(), "local terminate permission refusal"
    except OSError:
        pass
    try:
        proc.wait(timeout=5.0)
        detail = "reaped after terminate"
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except PermissionError:
            return proc.poll(), "local kill permission refusal"
        except OSError:
            pass
        try:
            proc.wait(timeout=5.0)
            detail = "reaped after kill"
        except subprocess.TimeoutExpired:
            detail = "child could not be reaped"
    return proc.poll(), detail


def collect_process(
    argv: Sequence[str],
    *,
    deadline_seconds: float,
    output_cap_bytes: int,
) -> ProcessResult:
    """Run one local helper client with an externally enforced deadline.

    ``Popen(argv, shell=False)`` with closed stdin, a fixed minimal trusted
    environment (nothing inherited from ``os.environ``) and combined bounded
    stdout+stderr capture via raw chunked reads.  No line readers, no
    unbounded ``communicate()``, no head-only truncation: on deadline or cap
    the local client is terminated and reaped and the exact bytes, exit code
    and truncation reason are retained.
    """
    if type(argv) not in (tuple, list):
        raise TransportPlanError(
            "argv must be a sequence of str, never a shell string"
        )
    checked_argv = []
    for index, item in enumerate(argv):
        if index > 0 and argv[index - 1] == "-c":
            _require_owner_script(item, f"argv[{index}]", _MAX_TEXT_LEN)
        else:
            _require_plain_text(item, f"argv[{index}]", _MAX_TEXT_LEN)
        if "\x00" in item:
            raise TransportPlanError(f"argv[{index}] contains NUL")
        checked_argv.append(item)
    if not checked_argv:
        raise TransportPlanError("argv must not be empty")
    _require_number(
        deadline_seconds, "deadline_seconds", 0.0, _MAX_COLLECT_DEADLINE_SECONDS
    )
    _require_int(
        output_cap_bytes, "output_cap_bytes", 1, MAX_OUTPUT_BYTES
    )
    client_env = dict(MINIMAL_CLIENT_ENV)

    deadline_at = time.monotonic() + deadline_seconds
    proc = subprocess.Popen(
        checked_argv,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=client_env,
        bufsize=0,
        close_fds=True,
    )
    chunks: list = []
    total = 0
    timed_out = False
    truncated = False
    detail = "exited before deadline"
    error_type = None
    reap_attempted = False
    try:
        assert proc.stdout is not None
        raw_fd = proc.stdout.fileno()
        while True:
            remaining = deadline_at - time.monotonic()
            if remaining <= 0:
                timed_out = True
                detail = "deadline exceeded; local client terminated and reaped"
                break
            if total >= output_cap_bytes:
                truncated = True
                detail = (
                    "output cap reached; local client terminated and reaped"
                )
                break
            ready, _, _ = select.select([raw_fd], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(raw_fd, min(65536, output_cap_bytes - total))
            if not chunk:
                detail = "client closed output before deadline"
                break
            chunks.append(chunk)
            total += len(chunk)
        if timed_out or truncated:
            reap_attempted = True
            returncode, reap_detail = _terminate_and_reap(proc)
            detail = f"{detail}; {reap_detail}"
        else:
            wait_remaining = deadline_at - time.monotonic()
            try:
                proc.wait(timeout=max(0.0, wait_remaining))
            except subprocess.TimeoutExpired:
                timed_out = True
                reap_attempted = True
                returncode, reap_detail = _terminate_and_reap(proc)
                detail = (
                    "deadline exceeded waiting for exit;"
                    f" {reap_detail}"
                )
            else:
                returncode = proc.poll()
    except Exception as exc:
        error_type = type(exc).__name__
        reap_attempted = True
        returncode, reap_detail = _terminate_and_reap(proc)
        detail = "collector error: " + error_type + "; " + reap_detail
    finally:
        if not reap_attempted and proc.poll() is None:
            _terminate_and_reap(proc)
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except OSError:
            pass
    return ProcessResult(
        argv=tuple(checked_argv),
        returncode=returncode,
        output=b"".join(chunks),
        timed_out=timed_out,
        output_truncated=truncated,
        detail=detail,
        error_type=error_type,
    )
