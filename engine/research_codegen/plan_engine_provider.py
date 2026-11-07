"""Inert per-plan composition over the pinned canonical transport.

No transport qualification, process executor or activation is supplied here.
The fixed qualification harness continues to consume its original transport bytes.
"""
import math

from .transport import (
    CREATE_DEADLINE_SECONDS, STOP_DEADLINE_SECONDS, KILL_DEADLINE_SECONDS,
    REMOVE_DEADLINE_SECONDS, INSPECT_DEADLINE_SECONDS, EngineCommandResult,
    TransportPlanError, TransportDormantError, TransportStateError,
    TransportPermissionRefusal, TransportEngineError, plan_identity,
    build_create_argv, build_start_argv, build_stop_argv, build_kill_argv,
    build_remove_argv, build_inspect_argv, parse_container_id,
)

__all__ = ["PlanBoundEngineProvider"]


class PlanBoundEngineProvider:
    """Inert owner-injected composition, not an executor or admission issuer.

    The trusted caller supplies an inert factory and its existing CID receipt
    sink. Each operation is reserved before factory selection, including failed
    selection. Keep this original provider and receipts after uncertainty; a new
    Python object is not durable retry authority. No process/default executor,
    qualification, candidate-controlled selection or persistent registry exists.
    """

    def __init__(self, *, executor_for_plan=None, retain_container=None):
        if executor_for_plan is not None and (not callable(executor_for_plan)
                                              or not callable(retain_container)):
            raise TransportPlanError("explicit executor factory and CID receipt sink required")
        self._factory = executor_for_plan
        self._retain = retain_container
        self._selected = {}
        self._permission_refused = False

    def _check_permission(self):
        if self._permission_refused:
            raise TransportPermissionRefusal("original provider permission refusal; all engines frozen")

    def engine_for(self, plan):
        self._check_permission()
        digest = plan_identity(plan)
        if self._factory is None:
            raise TransportDormantError("no per-plan executor supplied; no process call")
        if plan.operation_id in self._selected:
            raise TransportStateError("original operation already selected; no replacement engine")
        self._selected[plan.operation_id] = digest
        try:
            executor = self._factory(plan)
        except (TransportPermissionRefusal, PermissionError) as exc:
            self._permission_refused = True
            raise TransportPermissionRefusal("executor selection permission refused") from exc
        except Exception as exc:
            raise TransportEngineError("inert executor selection failed; original selection retained") from exc
        if executor is None or not callable(getattr(executor, "run", None)):
            raise TransportPlanError("explicit plan executor required")
        return _PlanBoundEngine(plan, executor, self._retain, self)

class _PlanBoundEngine:
    """Exact canonical plan/CID command boundary around an injected executor.

    Runtime image, host policy and supervision qualification remain the actual
    executor owner's obligations. This boundary cannot confer those facts.
    """

    def __init__(self, plan, executor, retain, provider):
        self._plan, self._executor, self._retain = plan, executor, retain
        self._provider = provider
        self._cid = None
        self._created = self._started = self._frozen = False
        self._cleanup_started = False
        self._receipt_ok = False

    def run(self, argv, *, deadline_seconds, output_cap_bytes):
        self._provider._check_permission()
        if self._frozen:
            raise TransportPermissionRefusal("original executor permission refusal; frozen")
        plan = self._plan
        if type(argv) is not tuple or any(type(item) is not str for item in argv):
            raise TransportPlanError("exact command tuple of plain strings required")
        if argv == build_create_argv(plan):
            kind, limit = "create", CREATE_DEADLINE_SECONDS
            if self._created:
                raise TransportStateError("create already attempted; no replacement")
        else:
            if self._cid is None:
                raise TransportPlanError("no settled original CID; no lifecycle command")
            cid = self._cid
            commands = {
                build_start_argv(plan, cid): ("start", plan.wall_clock_seconds),
                build_stop_argv(plan, cid): ("stop", STOP_DEADLINE_SECONDS),
                build_kill_argv(plan, cid): ("kill", KILL_DEADLINE_SECONDS),
                build_remove_argv(plan, cid): ("rm", REMOVE_DEADLINE_SECONDS),
                build_inspect_argv(plan, cid): ("inspect", INSPECT_DEADLINE_SECONDS),
                (plan.docker_binary, "inspect", "--type", "container", "--format",
                 '[{{json .Id}},{{json .State}}]', cid): ("state", INSPECT_DEADLINE_SECONDS),
            }
            if argv not in commands:
                raise TransportPlanError("command does not match original plan and settled CID")
            kind, limit = commands[argv]
            if kind == "start" and (self._started or self._cleanup_started or not self._receipt_ok):
                raise TransportStateError("start already attempted or CID receipt unconfirmed")
        if (type(deadline_seconds) not in (int, float)
                or not math.isfinite(deadline_seconds) or not 0 < deadline_seconds <= limit
                or type(output_cap_bytes) is not int
                or not 0 < output_cap_bytes <= plan.output_cap_bytes):
            raise TransportPlanError("command exceeds original deadline or output bounds")
        if kind == "create":
            self._created = True
        if kind == "start":
            self._started = True
        if kind in {"stop", "kill", "rm", "inspect"}:
            self._cleanup_started = True
        try:
            result = self._executor.run(argv, deadline_seconds=deadline_seconds,
                                        output_cap_bytes=output_cap_bytes)
        except (TransportPermissionRefusal, PermissionError):
            self._frozen = True
            self._provider._permission_refused = True
            raise TransportPermissionRefusal("injected executor permission refusal") from None
        if (type(result) is not EngineCommandResult
                or type(result.stdout) is not bytes or type(result.stderr) is not bytes
                or type(result.timed_out) is not bool or type(result.output_truncated) is not bool
                or type(result.permission_refused) is not bool
                or (result.returncode is not None and type(result.returncode) is not int)):
            raise TransportEngineError("canonical bounded result required")
        if result.permission_refused:
            self._frozen = True
            self._provider._permission_refused = True
        if kind == "create" and (not result.permission_refused and result.error_type is None
                and not result.timed_out and not result.output_truncated and result.returncode == 0
                and len(result.stdout) + len(result.stderr) <= output_cap_bytes):
            cid = parse_container_id(result.stdout)
            if cid is not None and result.observed_container_id in (None, cid):
                self._cid = cid
                try:
                    # True is a caller receipt acknowledgement, not a claim that
                    # this source module authenticated durable external storage.
                    self._receipt_ok = self._retain(plan, cid) is True
                except (TransportPermissionRefusal, PermissionError) as exc:
                    self._frozen = True
                    self._provider._permission_refused = True
                    raise TransportPermissionRefusal("original CID receipt permission refused") from exc
                except Exception:
                    self._receipt_ok = False
        return result
