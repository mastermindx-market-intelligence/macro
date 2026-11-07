"""Negative Macro scenario-HTTP admission and request lifetime only.

The incumbent app installer captures a boot ceiling; observing CLOSED latches
new source/capture admission closed for that app process. These are denial
conditions, never authentication, a receipt issuer, current-set membership or a
native-effect inventory. Ending an HTTP lifetime cannot settle R2/SQL effects.
The existing native operation owner alone records claim/completion facts.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import os
import threading

_SLOT = "options_scenario_http_admission"
_ACTIVE = ContextVar("macro_scenario_http_request", default=None)


class AdmissionClosed(ValueError):
    def __init__(self):
        super().__init__("scenario_http_admission_closed")


def _enabled(name):
    value = os.environ.get(name)
    return type(value) is str and value == "1"


class _ProcessAdmission:
    def __init__(self, app):
        self._app = app
        self._lock = threading.RLock()
        self._source_ceiling = _enabled("OPTIONS_SCENARIO_SOURCE_ENABLED")
        self._capture_ceiling = _enabled("OPTIONS_SCENARIO_CAPTURE_ENABLED")
        self._source_closed = not self._source_ceiling
        self._capture_closed = not self._capture_ceiling

    def _observe_locked(self):
        if not _enabled("OPTIONS_SCENARIO_SOURCE_ENABLED"):
            self._source_closed = True
        if not _enabled("OPTIONS_SCENARIO_CAPTURE_ENABLED"):
            self._capture_closed = True

    def _require_locked(self, capture=False):
        self._observe_locked()
        if (not self._source_ceiling or self._source_closed or
                capture and (not self._capture_ceiling or self._capture_closed)):
            raise AdmissionClosed()

    def require_source(self):
        with self._lock:
            self._require_locked()

    def capture_for_installation(self):
        with self._lock:
            self._require_locked()
            return self._capture_ceiling and not self._capture_closed


class _Lifetime:
    def __init__(self, guard, bindings):
        self._guard = guard
        self._bindings = bindings
        self._active = True
        self._original = None
        self._canonical = None
        self._claim_entry_used = False

    def _require_locked(self):
        if (not self._active or _ACTIVE.get() is not self or
                getattr(self._guard._app.state, "options_scenario_source_bindings", None) is not self._bindings):
            raise AdmissionClosed()


def install_http_admission(app):
    """Called by the incumbent installer before any opt-in/store early return.

    Repeated installation cannot replace the first boot ceiling or a latch.
    No host/process probe, generation, credentials, network or persistent state.
    """
    existing = getattr(app.state, _SLOT, None)
    if existing is None:
        existing = _ProcessAdmission(app)
        setattr(app.state, _SLOT, existing)
    if type(existing) is not _ProcessAdmission or existing._app is not app:
        raise AdmissionClosed()
    return existing


@contextmanager
def request_lifetime(request, bindings):
    """Private installed HTTP origin only; no caller attestation entrance.

    The shared object's finally-ended fact also revokes copied async contexts.
    No count/list of requests is retained or offered as a drain observation.
    """
    app = request.app
    guard = getattr(app.state, _SLOT, None)
    if (type(guard) is not _ProcessAdmission or guard._app is not app or
            _ACTIVE.get() is not None or bindings is None or
            getattr(app.state, "options_scenario_source_bindings", None) is not bindings):
        raise AdmissionClosed()
    with guard._lock:
        guard._require_locked()
        lifetime = _Lifetime(guard, bindings)
    token = _ACTIVE.set(lifetime)
    try:
        yield
    finally:
        with guard._lock:
            lifetime._active = False
            lifetime._original = lifetime._canonical = lifetime._bindings = None
        _ACTIVE.reset(token)


def bind_capture_request(principal, operation_id, canonical_request):
    """Bind only the actual route's already-fresh actor and parsed original key.

    This does not verify or issue authentication. The route's uncached owner
    checks and the existing native SQL claim still supply their own authority.
    """
    lifetime = _ACTIVE.get()
    if type(lifetime) is not _Lifetime:
        raise AdmissionClosed()
    with lifetime._guard._lock:
        lifetime._require_locked()
        lifetime._guard._require_locked(capture=True)
        actor = (principal.principal_id, principal.principal_issuer, principal.auth_epoch, operation_id)
        if (lifetime._original is not None or any(type(value) is not str or not value for value in actor) or
                type(canonical_request) is not dict or canonical_request.get("principal") != actor[0]):
            raise AdmissionClosed()
        lifetime._original = actor
        lifetime._canonical = deepcopy(canonical_request)


def require_claim_admission(authority, binding, canonical_request):
    """Immediately before the existing claim, veto missing/ended/foreign scope.

    One local entry-use bit prevents reentrant/repeated claim dispatch; it is
    never a claim result, native-phase fact, pending count or retry decision.
    Factual record_retained is deliberately outside this gate and unchanged.
    """
    from app.investigation_native_capture import CaptureBinding, NativeCaptureAuthority, _same_json
    lifetime = _ACTIVE.get()
    if (type(lifetime) is not _Lifetime or type(authority) is not NativeCaptureAuthority or
            type(binding) is not CaptureBinding):
        raise AdmissionClosed()
    with lifetime._guard._lock:
        lifetime._require_locked()
        lifetime._guard._require_locked(capture=True)
        if (lifetime._claim_entry_used or authority is not getattr(lifetime._bindings, "native_capture_authority", None) or
                (binding.actor, binding.issuer, binding.auth_epoch, binding.operation_id) != lifetime._original or
                not _same_json(canonical_request, lifetime._canonical)):
            raise AdmissionClosed()
        lifetime._claim_entry_used = True
