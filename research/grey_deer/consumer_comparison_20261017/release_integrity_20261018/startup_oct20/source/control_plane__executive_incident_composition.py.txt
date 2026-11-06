"""Production-owned, dormant incident composition; no activation knobs.

The code-bound forward policy remains None. Only a later separately reviewed
policy amendment can select the fixed genuine-context producer. This module
does not infer permission from source installation, fixtures, receipts or an
ordinary incident policy, and never invokes the original issuer.
"""
from pathlib import Path
import os
import sys
import time

__all__ = ()
_FOREGROUND_BUDGET_NS = 120_000_000_000


class _ForegroundRunError(RuntimeError):
    def __init__(self, code, *, bootstrap_attempted=False, bootstrapped=False,
                 child_born=False, pump_entered=False):
        self.code = code
        self.bootstrap_attempted = bootstrap_attempted
        self.bootstrapped = bootstrapped
        self.child_born = child_born
        self.pump_entered = pump_entered
        super().__init__(code)


def _require_policy():
    from ops.executive_os import provider_incident_forward as forward

    if forward.PRODUCTION_FORWARD_RECOVERY_POLICY is None:
        raise _ForegroundRunError('FORWARD_PRODUCTION_POLICY_DORMANT')
    try:
        amendment = forward.validate_forward_policy(forward.PRODUCTION_FORWARD_RECOVERY_POLICY)
        if forward.recovery.PRODUCTION_INCIDENT_POLICY is None:
            raise _ForegroundRunError('FORWARD_INCIDENT_POLICY_DORMANT')
        incident = forward.recovery.validate_incident_policy(forward.recovery.PRODUCTION_INCIDENT_POLICY)
    except (forward.ForwardRecoveryError, forward.recovery.RecoveryError) as error:
        raise _ForegroundRunError(error.code) from error
    return amendment, incident


def _loaded_source():
    from ops.executive_os import provider_incident_forward as forward
    from control_plane import executive_privileged_broker as broker

    source = forward.recovery.current_executive_source()
    root = broker._RELEASE_PREFIX / source['release_sha']
    if Path(__file__).resolve(strict=True).parents[1] != root:
        raise _ForegroundRunError('FORWARD_COMPOSITION_SOURCE_MISMATCH')
    return source


def _resolve_production_forward_host_guard(config):
    """Select one source-owned callable; never accept a caller-supplied one."""
    from importlib import import_module

    optional_module = 'ops.executive_os.provider_incident_forward'
    try:
        forward = import_module(optional_module)
    except ModuleNotFoundError as error:
        # Only absence of this optional protocol leaves ordinary v1 startup
        # dormant. Broken imports inside it must still fail before constructor
        # effects; they are not evidence that the protocol is absent.
        if error.name != optional_module:
            raise
        return None

    if forward.PRODUCTION_FORWARD_RECOVERY_POLICY is None:
        return None
    _require_policy()
    source = _loaded_source()
    from control_plane import executive_privileged_broker as broker
    if config.release_root != broker._RELEASE_PREFIX / source['release_sha']:
        raise _ForegroundRunError('FORWARD_BROKER_SOURCE_MISMATCH')
    from control_plane.executive_incident_forward_host import _make_forward_host_context
    return _make_forward_host_context


def _closed_request(source):
    from ops.executive_os import provider_incident_forward as forward

    raw = {
        'schema': forward.FORWARD_REQUEST_SCHEMA,
        'request_id': forward.ORIGINAL_ISSUER_REQUEST_ID,
        'action': forward.FORWARD_RECOVERY_ACTION,
        'args': {
            'original_request_sha256': forward.ORIGINAL_REQUEST_SHA256,
            'original_marker_sha256': forward.ORIGINAL_MARKER_SHA256,
            'original_release_sha': forward.ORIGINAL_RELEASE_SHA,
            'successor_request_id': forward.SUCCESSOR_REQUEST_ID,
            'expected_current_release_sha': source['release_sha'],
            'expected_current_manifest_sha256': source['manifest_sha256'],
        },
    }
    request, _digest = forward.validate_forward_request(raw)
    return request.to_dict()


def _run_foreground_forward():
    """One fresh held origin, bootstrap, child and existing witness pump.

    No parameters select source, IDs, policy, factory, endpoint or a deadline.
    The fixed execution ceiling is not a grant window. The original endpoint
    is passed unchanged into acquisition; the reviewed protocol may only
    tighten it against the child and broker ceilings. No restart/resume exists.
    The canonical maintenance owner must already have established stopped
    custody. This function does not disable, bootout, unlink or repair anything.
    """
    # Dormant production refuses before native reads, custody or any effect.
    policy = _require_policy()
    from control_plane import executive_incident_origin as origin

    budget = origin.release._Budget(time.monotonic_ns() + _FOREGROUND_BUDGET_NS)
    interval = None
    pump_entered = False
    result = None
    error = None
    cleanup_failed = False
    try:
        if sys.platform != 'darwin' or os.geteuid() != 0:
            raise _ForegroundRunError('FORWARD_FOREGROUND_PRINCIPAL_UNQUALIFIED')
        source = budget.call(_loaded_source)
        raw = _closed_request(source)
        # Allocation owns its return-side cleanup. Do not wrap this in
        # budget.call and lose a newly returned context on a deadline fence.
        interval = origin._enter_origin_interval(deadline_monotonic_ns=budget.endpoint)
        if type(interval) is not origin._OriginInterval:
            raise _ForegroundRunError('FORWARD_ORIGIN_CONTEXT_REQUIRED')
        budget.check(force=True)
        if interval.release_commit != source['release_sha']:
            raise _ForegroundRunError('FORWARD_ORIGIN_SOURCE_MISMATCH')
        if budget.call(_require_policy) != policy or budget.call(_loaded_source) != source:
            raise _ForegroundRunError('FORWARD_PREFLIGHT_DRIFT')
        interval.bootstrap_once()
        budget.check(force=True)
        if budget.call(_require_policy) != policy or budget.call(_loaded_source) != source:
            raise _ForegroundRunError('FORWARD_PRESUBMISSION_DRIFT')
        # The factory captures the first native child generation and retains
        # actual Popen/stdio handles. No serialized or substitute context enters.
        child = origin._spawn_origin_client(interval, raw)
        budget.check(force=True)
        pump_entered = True
        result = origin._serve_origin_witnesses(interval, child)
        if type(result) is not origin._OriginResult:
            raise _ForegroundRunError('FORWARD_ORIGIN_RESULT_REQUIRED')
    except BaseException as failure:
        error = failure
    finally:
        # The pump normally owns both closures. Pre-pump failure must still
        # close the newly acquired context and settle a child born before its
        # factory raised; never settle/close the same retained resource twice.
        if type(interval) is origin._OriginInterval:
            try:
                if not interval.closed:
                    interval.close_once()
            except BaseException:
                cleanup_failed = True
            child = interval.child
            if child is not None and not child.settled:
                try:
                    interval._settle_child(child)
                except BaseException:
                    cleanup_failed = True
    if error is not None or cleanup_failed:
        real_interval = type(interval) is origin._OriginInterval
        raise _ForegroundRunError(
            'FORWARD_COMPOSITION_CLEANUP_UNPROVEN' if cleanup_failed else
            getattr(error, 'code', 'FORWARD_FOREGROUND_UNAVAILABLE'),
            bootstrap_attempted=bool(real_interval and interval.bootstrap_attempted),
            bootstrapped=bool(real_interval and interval.bootstrapped),
            child_born=bool(real_interval and interval.child is not None),
            pump_entered=pump_entered,
        ) from error
    return result
