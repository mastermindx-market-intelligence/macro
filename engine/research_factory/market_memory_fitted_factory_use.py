"""Static fitted-Factory consumption of the one original COMPLETE query.

The versioned service entry declared inside the existing house source
registration is a STATIC predeclared definition. It names the fixed native
COMPLETE-reader contract, one exact existing trial registration reference, the
selected training binding/method and a bounded ``k``. It carries no
post-COMPLETE digest, no private fitted-binding registration and no mutable
hash pointer; the old contextual Factory binding is not consulted and grants
nothing here.

The compact locator ``{operation_id, intent, sha256, bytes}`` is untrusted
input, never admission. Admission is delegated to exactly this original native
query by the static service entry, the fixed installed owner and verified
source closure, the current clean selected control custody and the original
COMPLETE store record. Normalizer, index, fitted method, membership and result
identities come only from the genuine native owner after it reopens the
completed bytes. The locator's ``value`` field is transport-only: the native
reader requires the five-field reference shape and never reads it, so ``None``
is passed and the payload is never pre-populated from the store.

Public trial bytes are resolved through the original trial owner and the
existing candidate builder. That preserves the exact proposed candidate bytes
and lifecycle flags; it does not prove the original trial query or evaluation.
No activation, enrollment, fit, forecast, study efficacy, training, promotion,
account or emission authority is created or claimed.
"""
from __future__ import annotations

import copy
from hashlib import sha256
from contextvars import ContextVar
from threading import get_ident, local
import os
from pathlib import Path
import re
import sys

from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_fitted_retrieval as fitted_retrieval
from engine.neuralweb import market_memory_forward as forward
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as house
from engine.research_factory import adapter_market_memory as adapter
from engine.research_factory import market_memory_contextual_registration as control
from engine.research_factory import market_memory_e0_installed_control as owner
from engine.research_factory import market_memory_fitted_persistence as persistence
from engine.research_factory import market_memory_fitted_use as use

CONSUMER = "research_factory.fitted_contextual_evidence.v2"
PURPOSE = "fitted_contextual_cited_evidence"
SERVICE_SCHEMA = "market_memory.factory_fitted_binding.v2"
QUERY_ACTION = "retained_fitted_query.v2"
MAX_TRIAL_BYTES = 256 * 1024
_MODULE_PATH = "engine/research_factory/market_memory_fitted_factory_use.py"
_SCHEMA_PATH = "contracts/market_memory/factory_fitted_binding.v2.schema.json"
# The original persistence closure plus this additive module and its contract.
# The deployed selected source commit must contain exactly these bytes.
_SOURCE_PATHS = persistence._SOURCES + (_MODULE_PATH, _SCHEMA_PATH)
_SERVICE_FIELDS = frozenset({"schema", "consumer", "enabled", "purpose",
    "trial_registration_id", "trial_registration_sha256", "trial_record",
    "candidate_created_at", "binding_ref", "eligibility_method_spec",
    "normalization_method", "limit"})
_SPEC_FIELDS = frozenset({"method_spec_id", "purge_calendar_days",
                          "embargo_calendar_days", "mode"})
_INTENT_FIELDS = frozenset({"action", "fit_sha256", "query_id", "generation_id",
                            "generation_sha256", "query_cutoff", "k",
                            "method_spec_id"})
_COMPACT_FIELDS = frozenset({"operation_id", "intent", "sha256", "bytes"})
_SCOPE_KEYS = ("store_id", "generation_id", "generation_sha256", "query_cutoff")
_UTC_MICRO = (r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
              r"\.[0-9]{6}Z")


_ACTION_FRAME = ContextVar("market_memory_fitted_factory_action", default=None)
_FRAME_TOKEN = object()
_ISSUERS = local()


class _ActionFrame:
    """Execution-local dispatch state, never a reusable permission grant."""
    def __init__(self, policy, scope, action, resource_bytes):
        self.policy, self.scope = policy, scope
        self.action, self.resource_bytes = action, resource_bytes
        self.thread, self.nonce, self.active = get_ident(), object(), True
        self.seal = _FRAME_TOKEN


class _FrameIssuer:
    """Synchronous thread-local issuance, independent of copied Context state."""
    def __init__(self, frame):
        self.frame, self.nonce = frame, frame.nonce
        self.policy, self.scope = frame.policy, frame.scope
        self.action, self.resource_bytes = frame.action, frame.resource_bytes
        self.thread, self.pending = get_ident(), True


class FittedFactoryUseError(ValueError):
    """Stable refusal; never payload, private body, path or caller identity."""


def _require(ok, reason):
    if not ok:
        raise FittedFactoryUseError(reason)


def _installed_owner_root(root):
    _require(Path(root).resolve() == owner.INSTALLED_ROOT.resolve(),
             "installed_fitted_factory_owner_required")


def _owner_environment():
    """Fixed installed administrator surface; never a caller-supplied root."""
    _require(sys.platform == "linux" and os.geteuid() == 0
        and Path(__file__).resolve() == owner.INSTALLED_ROOT / _MODULE_PATH,
        "installed_fitted_factory_owner_required")
    _installed_owner_root(owner.INSTALLED_ROOT)
    owner._verify_loaded_sources(paths=_SOURCE_PATHS)


def _trial_bytes(root, service):
    """Bounded public trial bytes; the digest is pinned by the service entry."""
    path = root / service["trial_record"]
    try:
        with path.open("rb") as stream:
            body = stream.read(MAX_TRIAL_BYTES + 1)
    except OSError as exc:
        raise FittedFactoryUseError("trial_registration_unavailable") from exc
    _require(0 < len(body) <= MAX_TRIAL_BYTES, "trial_registration_byte_limit")
    return body


def _fitted_service(root):
    """Current static service entry from the existing source registration."""
    registration, digest = house.load_registration(root)
    consumers = registration.get("service_consumers")
    service = consumers.get(CONSUMER) if type(consumers) is dict else None
    if (type(service) is not dict or set(service) != _SERVICE_FIELDS
            or service["schema"] != SERVICE_SCHEMA or service["consumer"] != CONSUMER
            or service["enabled"] is not True or service["purpose"] != PURPOSE
            or service["normalization_method"] != use.METHOD
            or type(service["limit"]) is not int or not 1 <= service["limit"] <= 8
            or type(service["trial_registration_id"]) is not str
            or re.fullmatch(r"mmtrial_[a-f0-9]{64}", service["trial_registration_id"]) is None
            or type(service["trial_registration_sha256"]) is not str
            or re.fullmatch(r"[a-f0-9]{64}", service["trial_registration_sha256"]) is None
            or service["trial_record"] != "research/market_memory/trials/"
                + service["trial_registration_sha256"] + ".json"
            or type(service["candidate_created_at"]) is not str
            or re.fullmatch(_UTC_MICRO, service["candidate_created_at"]) is None):
        raise FittedFactoryUseError("current_fitted_factory_service_required")
    pinned = service["eligibility_method_spec"]
    if (type(pinned) is not dict or set(pinned) != _SPEC_FIELDS
            or type(pinned["method_spec_id"]) is not str
            or re.fullmatch(r"mmretainedmethod_[a-f0-9]{64}",
                            pinned["method_spec_id"]) is None
            or any(type(pinned[k]) is not int or not 0 <= pinned[k] <= 366
                   for k in ("purge_calendar_days", "embargo_calendar_days"))
            or pinned["mode"] not in registration["modes"]):
        raise FittedFactoryUseError("current_fitted_factory_service_required")
    try:
        binding_ref = control._domain_reference(service["binding_ref"])
    except control.E0ControlError as exc:
        raise FittedFactoryUseError("exact_fitted_training_binding_required") from exc
    if binding_ref["schema"] != use.SCHEMA:
        raise FittedFactoryUseError("exact_fitted_training_binding_required")
    return service, registration, digest


def _resolve_trial(root, service):
    """Bounded public trial bytes through the original owner and candidate builder."""
    body = _trial_bytes(root, service)
    _require(sha256(body).hexdigest() == service["trial_registration_sha256"],
             "trial_registration_bytes_mismatch")
    try:
        trial = forward.load_trial_registration_json(body)
    except forward.MarketMemoryForwardContractError as exc:
        raise FittedFactoryUseError("trial_registration_owner_refused") from exc
    _require(forward.canonical_json_bytes(trial) == body,
             "trial_registration_bytes_mismatch")
    _require(trial["trial_registration_id"] == service["trial_registration_id"],
             "exact_trial_registration_required")
    candidate = adapter.build_market_memory_candidate(
        exact_trial_registration_bytes=body,
        created_at=service["candidate_created_at"])
    return body, trial, candidate


def _qualified_context():
    """Original native control custody first, then the additive source proof.

    The selected bytes are the authenticated native context selection; there is
    no parallel SELECTED.json decoder and no caller path, clock or loader.
    """
    context = persistence._load_context()
    selected = control._domain_json(context.window._selection)
    owner._verify_source(owner.INSTALLED_ROOT, selected.get("source_commit"),
                         paths=_SOURCE_PATHS)
    return context, selected


def _window_binding(context):
    value = control._domain_json(context.window._body)
    binding = value.get("binding")
    if (type(binding) is not dict
            or type(value.get("eligibility_method_spec")) is not dict):
        raise FittedFactoryUseError("selected_training_window_required")
    return value, binding


def _service_binding_gate(root, service, registration, value, binding):
    """Static entry must match the genuine v2 purpose and the native window."""
    ref = control._domain_reference(service["binding_ref"])
    body = cohort.canonical(binding)
    if (ref["sha256"] != sha256(body).hexdigest() or ref["bytes"] != len(body)
            or ref["object_id"] != binding.get("binding_id")):
        raise FittedFactoryUseError("fitted_training_binding_changed")
    purpose, _purpose_body = use._purpose(root)
    if purpose["binding_ref"] != service["binding_ref"]:
        raise FittedFactoryUseError("fitted_training_binding_changed")
    pinned = service["eligibility_method_spec"]
    spec = value["eligibility_method_spec"]
    if (binding.get("purpose") != use.PURPOSE
            or binding.get("normalization_method") != service["normalization_method"]
            or any(spec.get(k) != pinned[k]
                   for k in ("method_spec_id", "purge_calendar_days",
                             "embargo_calendar_days", "mode"))):
        raise FittedFactoryUseError("registered_fitted_method_changed")
    derived = retrieval.RetainedContextMethodSpec(
        registration["method"]["purge_calendar_days"],
        registration["method"]["embargo_calendar_days"], pinned["mode"]).disclosure()
    if derived["method_spec_id"] != pinned["method_spec_id"]:
        raise FittedFactoryUseError("registered_fitted_method_changed")


def _qualify_locator(context, binding, service, reference):
    """Qualify COMPLETE store metadata before any query projection or read.

    Uses the original ReservationStore primitives on the entire current
    binding: the bounded journal chain and head are validated and the result
    file size is checked without reading any result byte. Absent, pending,
    invented or changed records reject here, so the native reader is reached
    only with an exactly matching original COMPLETE record.
    """
    if (type(reference) is not dict or set(reference) != _COMPACT_FIELDS
            or type(reference["operation_id"]) is not str
            or re.fullmatch(r"query_[a-f0-9]{64}", reference["operation_id"]) is None
            or type(reference["sha256"]) is not str
            or re.fullmatch(r"[a-f0-9]{64}", reference["sha256"]) is None
            or type(reference["bytes"]) is not int
            or not 1 <= reference["bytes"] <= persistence.MAX_RESULT_BYTES):
        raise FittedFactoryUseError("compact_query_reference_required")
    intent = reference["intent"]
    if (type(intent) is not dict or set(intent) != _INTENT_FIELDS
            or intent["action"] != QUERY_ACTION
            or type(intent["k"]) is not int or not 1 <= intent["k"] <= service["limit"]
            or any(type(intent[key]) is not str for key in
                   ("fit_sha256", "query_id", "generation_id",
                    "generation_sha256", "query_cutoff", "method_spec_id"))
            or re.fullmatch(r"[a-f0-9]{64}", intent["fit_sha256"]) is None
            or re.fullmatch(r"mmquery_[a-f0-9]{64}", intent["query_id"]) is None
            or re.fullmatch(r"mmgeneration_[a-f0-9]{64}", intent["generation_id"]) is None
            or re.fullmatch(r"[a-f0-9]{64}", intent["generation_sha256"]) is None
            or re.fullmatch(r"mmretainedmethod_[a-f0-9]{64}",
                            intent["method_spec_id"]) is None):
        raise FittedFactoryUseError("compact_query_reference_required")
    cohort.utc_instant(intent["query_cutoff"])
    source = binding["source_owner"]
    _require(intent["generation_id"] != source["generation_id"],
             "later_native_generation_required")
    _require(cohort.utc_instant(intent["query_cutoff"])
        > cohort.utc_instant(binding["fit_cutoff"]), "later_native_query_cutoff_required")
    _require(intent["method_spec_id"]
        == service["eligibility_method_spec"]["method_spec_id"],
        "registered_query_method_changed")
    operation = "query_" + sha256(cohort.canonical(intent)).hexdigest()
    _require(reference["operation_id"] == operation,
             "original_query_operation_mismatch")
    store = persistence._store(context)
    with store._locked() as descriptor:
        state = store._load(descriptor)
        _require(state is not None, "original_query_store_absent")
        _require(state["maximum_looks"] == context.maximum_looks,
                 "retained_fit_accounting_budget_changed")
        record = store._operation(state, operation, store._intent(intent))
        _require(record is not None, "original_query_operation_absent")
        _require(record["result"] is not None, "original_query_not_completed")
        _require(record["result"]["sha256"] == reference["sha256"]
            and record["result"]["bytes"] == reference["bytes"],
            "original_query_result_mismatch")
    return {"operation_id": operation, "intent": dict(intent),
            "sha256": reference["sha256"], "bytes": reference["bytes"]}


def _matches_scope(resource, bound):
    subject = resource.get("subject_id", resource.get("requested_subject_id"))
    return (all(resource.get(key) == bound[key] for key in _SCOPE_KEYS)
            and subject == bound["subject_id"])


class _FittedFactoryScope(house.RetainedHouseUsePolicy):
    """Incumbent exact source scope under the fitted-Factory principal.

    The Factory principal is never a website user: only the principal hook is
    replaced, and every inherited registration, revocation and resource check
    still runs byte-identically on every use, under the incumbent
    source-registration-derived policy_id that feature bodies hash.
    """

    def check(self, action, resource):
        principal = getattr(self, "_owner", None)
        _require(type(self) is _FittedFactoryScope
            and type(principal) is FittedFactoryUsePolicy,
            "fitted_factory_principal_required")
        principal._check_owned_scope(self, action, resource)

    def _enforce_current_principal(self):
        owner_policy = getattr(self, "_owner", None)
        if (type(self) is not _FittedFactoryScope
                or type(owner_policy) is not FittedFactoryUsePolicy):
            raise FittedFactoryUseError("fitted_factory_principal_required")
        owner_policy._enforce_scope_principal(self)


class FittedFactoryUsePolicy:
    """Two exact Factory-owned source scopes over one original COMPLETE query.

    Constructed only from the compact locator under the installed static
    service definition. Every public entry revalidates the installed service,
    trial, source closure, native control custody and both scopes, and every
    single authorization reruns the incumbent registration, revocation and
    resource checks under the incumbent source-derived policy_id.
    ``reopen_registered_fitted_query`` returns the genuine native
    ``FittedRetrievalCapability`` together with this same policy.
    """

    def __init__(self, *, reference):
        _require(type(self) is FittedFactoryUsePolicy, "fitted_factory_policy_required")
        _owner_environment()
        self.root = owner.INSTALLED_ROOT
        self._scopes_ready = False
        self._pending_scope = None
        self._training_scope = None
        self._query_scope = None
        self._install(reference)
        self._scopes_ready = True
        self._validate_scopes()

    def _install(self, reference):
        service, registration, digest = _fitted_service(self.root)
        trial_body, trial, candidate = _resolve_trial(self.root, service)
        context, selected = _qualified_context()
        value, binding = _window_binding(context)
        _service_binding_gate(self.root, service, registration, value, binding)
        compact = _qualify_locator(context, binding, service, reference)
        self._registration_sha256 = digest
        self._authority_sha256 = registration["source_authority"]["sha256"]
        self._service = service
        self._trial_sha256 = service["trial_registration_sha256"]
        self._trial_bytes_body = trial_body
        self._trial = trial
        self._candidate = candidate
        self._candidate_bytes = cohort.canonical(candidate)
        self.binding = binding
        self._window_spec = value["eligibility_method_spec"]
        self._window_body_sha256 = sha256(context.window._body).hexdigest()
        self._source_commit = selected["source_commit"]
        self.policy_id = registration["policy_id"] + ":" + digest
        source = binding["source_owner"]
        training = {"store_id": source["store_id"],
            "generation_id": source["generation_id"],
            "generation_sha256": source["generation_sha256"],
            "subject_id": context.subject_id,
            "query_cutoff": binding["fit_cutoff"], "mode": binding["mode"]}
        intent = compact["intent"]
        query = {**training, "generation_id": intent["generation_id"],
                 "generation_sha256": intent["generation_sha256"],
                 "query_cutoff": intent["query_cutoff"]}
        self._training_bound, self._query_bound = training, query
        self._compact = compact
        for name, fields in (("training", training), ("query", query)):
            scope = _FittedFactoryScope.__new__(_FittedFactoryScope)
            scope._owner = self
            scope.root = self.root
            self._pending_scope = scope
            scope._bind_source_scope(**fields)
            setattr(self, "_" + name + "_scope", scope)
        self._pending_scope = None
        # Final current rereads of service, native control custody and the
        # original COMPLETE store record after every capability was bound.
        final_service, _final_registration, final_digest = _fitted_service(self.root)
        if final_service != service or final_digest != digest:
            raise FittedFactoryUseError("fitted_factory_service_changed")
        final_context, _final_selected = _qualified_context()
        if (final_context.window._body != context.window._body
                or final_context.window._selection != context.window._selection
                or final_context.binding != context.binding
                or final_context.maximum_looks != context.maximum_looks):
            raise FittedFactoryUseError("selected_fitted_control_changed")
        if _qualify_locator(final_context, binding, final_service, compact) != compact:
            raise FittedFactoryUseError("original_query_record_changed")

    def _enforce_scope_principal(self, scope):
        if not self._scopes_ready:
            _require(scope is self._pending_scope,
                     "fitted_factory_principal_required")
            return
        _require(scope is self._training_scope or scope is self._query_scope,
                 "fitted_factory_principal_required")
        frame = _ACTION_FRAME.get()
        if frame is None:
            # Direct principal-hook calls still qualify current custody.
            self._recheck_owner()
            return
        stack = getattr(_ISSUERS, "stack", ())
        issuer = stack[-1] if stack else None
        _require(type(frame) is _ActionFrame and frame.seal is _FRAME_TOKEN
            and frame.active and frame.thread == get_ident()
            and type(issuer) is _FrameIssuer and issuer.pending
            and issuer.thread == get_ident() and issuer.frame is frame
            and issuer.nonce is frame.nonce
            and issuer.policy is self and frame.policy is self
            and issuer.scope is scope and frame.scope is scope
            and issuer.action == frame.action and frame.action in house._ACTIONS
            and type(frame.resource_bytes) is bytes
            and issuer.resource_bytes == frame.resource_bytes,
            "invalid_fitted_factory_action_frame")
        # The fixed synchronous base check invokes this hook exactly once.
        # A copied Context or frame cannot consume the same issuance twice.
        issuer.pending = False
        self._validate_scopes()

    def _recheck_owner(self):
        """Current service, trial, source, control and scope gates."""
        _owner_environment()
        service, registration, digest = _fitted_service(self.root)
        if (service != self._service or digest != self._registration_sha256
                or registration["policy_id"] + ":" + digest != self.policy_id):
            raise FittedFactoryUseError("fitted_factory_service_changed")
        if sha256(_trial_bytes(self.root, service)).hexdigest() != self._trial_sha256:
            raise FittedFactoryUseError("trial_registration_changed")
        context, selected = _qualified_context()
        value, binding = _window_binding(context)
        _service_binding_gate(self.root, service, registration, value, binding)
        if (binding != self.binding
                or value["eligibility_method_spec"] != self._window_spec
                or sha256(context.window._body).hexdigest() != self._window_body_sha256
                or selected["source_commit"] != self._source_commit):
            raise FittedFactoryUseError("fitted_factory_source_changed")
        compact = _qualify_locator(context, binding, service, self._compact)
        _require(compact == self._compact, "original_query_record_changed")
        source = binding["source_owner"]
        training = {"store_id": source["store_id"],
            "generation_id": source["generation_id"],
            "generation_sha256": source["generation_sha256"],
            "subject_id": context.subject_id, "query_cutoff": binding["fit_cutoff"],
            "mode": binding["mode"]}
        query = {**training, "generation_id": compact["intent"]["generation_id"],
                 "generation_sha256": compact["intent"]["generation_sha256"],
                 "query_cutoff": compact["intent"]["query_cutoff"]}
        _require(training == self._training_bound and query == self._query_bound,
                 "fitted_factory_scope_changed")
        self._validate_scopes()

    def _validate_scopes(self):
        _require(self._scopes_ready
            and type(self._training_scope) is _FittedFactoryScope
            and type(self._query_scope) is _FittedFactoryScope
            and self._training_scope is not self._query_scope,
            "fitted_factory_scope_changed")
        _require(self._training_bound["generation_id"]
            != self._query_bound["generation_id"], "fitted_factory_scope_changed")
        for scope, bound in ((self._training_scope, self._training_bound),
                             (self._query_scope, self._query_bound)):
            _require(scope._owner is self and scope.root == self.root
                and scope.mode == bound["mode"]
                and scope.registration_sha256 == self._registration_sha256
                and scope.policy_id == self.policy_id
                and scope.expected == {k: v for k, v in bound.items() if k != "mode"},
                "fitted_factory_scope_changed")

    def _check_owned_scope(self, scope, action, resource):
        # Every action has a fresh owner boundary, including direct scope calls.
        self._recheck_owner()
        _require(action in house._ACTIONS and type(resource) is dict,
                 "named_fitted_house_use_required")
        _require(scope is self._training_scope or scope is self._query_scope,
                 "fitted_factory_principal_required")
        bound = self._training_bound if scope is self._training_scope else self._query_bound
        frozen = cohort.canonical(resource)
        _require(_matches_scope(resource, bound),
                 "only_original_training_or_exact_query_scope_allowed")
        frame = _ActionFrame(self, scope, action, frozen)
        issuer = _FrameIssuer(frame)
        previous = getattr(_ISSUERS, "stack", ())
        _ISSUERS.stack = (*previous, issuer)
        token = None
        try:
            token = _ACTION_FRAME.set(frame)
            # The incumbent rights validator is unchanged. Only its nested
            # principal hook shares this exact owner-dispatched action frame.
            result = house.RetainedHouseUsePolicy.check(scope, action, resource)
            _require(cohort.canonical(resource) == frozen, "fitted_action_resource_changed")
            _require(result is None and issuer.pending is False,
                     "inherited_fitted_house_check_not_completed")
        finally:
            issuer.pending = False
            frame.active = False
            _ISSUERS.stack = previous
            if token is not None:
                _ACTION_FRAME.reset(token)
        self._recheck_owner()

    def check(self, action, resource):
        if action not in house._ACTIONS or type(resource) is not dict:
            raise FittedFactoryUseError("named_fitted_house_use_required")
        for scope, bound in ((self._training_scope, self._training_bound),
                             (self._query_scope, self._query_bound)):
            if _matches_scope(resource, bound):
                return self._check_owned_scope(scope, action, resource)
        # Failed dispatch still checks current source/custody, without creating
        # an exemption frame or routing a direct scope call to the other scope.
        self._recheck_owner()
        raise FittedFactoryUseError("only_original_training_or_exact_query_scope_allowed")

    def disclosure(self):
        self.check("read_retained_generation_metadata", dict(self._training_bound))
        _service, registration, _digest = _fitted_service(self.root)
        value = {"status": "ADMITTED_FOR_NAMED_PURPOSES", "consumer": CONSUMER,
                 "purpose": PURPOSE, "profile": house.PROFILE,
                 "policy_id": self.policy_id,
                 "registration_sha256": self._registration_sha256,
                 "authority_record": house.AUTHORITY_RECORD,
                 "authority_sha256": self._authority_sha256,
                 "purposes": list(registration["purposes"]),
                 "modes": list(registration["modes"]),
                 "method": dict(registration["method"]),
                 "binding_id": self.binding["binding_id"],
                 "source_commit": self._source_commit,
                 "claims": self._claims()}
        self._recheck_owner()
        return value

    def disclose_binding(self):
        self.check("read_retained_generation_metadata", dict(self._training_bound))
        _service, _registration, _digest = _fitted_service(self.root)
        value = {"consumer": CONSUMER, "purpose": PURPOSE,
                 "policy_id": self.policy_id,
                 "registration_sha256": self._registration_sha256,
                 "service": copy.deepcopy(self._service),
                 "binding": copy.deepcopy(self.binding),
                 "eligibility_method_spec": copy.deepcopy(self._window_spec),
                 "training_scope": dict(self._training_bound),
                 "query_scope": dict(self._query_bound),
                 "source_commit": self._source_commit,
                 "trial": {"trial_registration_id":
                               self._service["trial_registration_id"],
                           "trial_registration_sha256": self._trial_sha256,
                           "trial_record": self._service["trial_record"],
                           "bytes": len(self._trial_bytes_body),
                           "trial_key": self._trial["trial_key"],
                           "registered_at": self._trial["registered_at"]},
                 "candidate": {key: copy.deepcopy(self._candidate[key]) for key in
                     ("candidate_id", "created_at", "status", "source",
                      "candidate_type", "authority", "flags",
                      "trial_accounting", "evaluation_plan")},
                 "candidate_sha256": sha256(self._candidate_bytes).hexdigest(),
                 "candidate_bytes": len(self._candidate_bytes),
                 "trial_original_query_provenance": "not_established",
                 "claims": self._claims()}
        self._recheck_owner()
        return value

    @staticmethod
    def _claims():
        return {"contextual_cited_evidence_only": True,
                "operational_study_admission": False, "efficacy_claim": False,
                "fit_eligible": False, "training_eligible": False,
                "promotion_eligible": False,
                "factory_count_or_transition_action": False,
                "historical_fit_or_index_existence_authenticated": False,
                "trial_original_query_or_evaluation_provenance": "not_established"}

    def reopen_registered_fitted_query(self):
        """Read-only native reproduction; returns the capability and this policy."""
        self._recheck_owner()
        context, _selected = _qualified_context()
        if sha256(context.window._body).hexdigest() != self._window_body_sha256:
            raise FittedFactoryUseError("fitted_training_window_changed")
        compact = _qualify_locator(context, self.binding, self._service, self._compact)
        if compact != self._compact:
            raise FittedFactoryUseError("original_query_record_changed")
        # Transport-only key: the native reader requires the five-field
        # reference shape and never reads ``value``; the original COMPLETE
        # payload is read only by the native owner, so None is passed and no
        # pre-read ever populates it.
        reference = {**compact, "value": None}
        reproduced, combined = persistence.reproduce_registered_fitted_query(
            reference, policy=self)
        _require(combined is self
            and type(reproduced) is fitted_retrieval.FittedRetrievalCapability,
            "owner_native_query_required")
        self._recheck_owner()
        return reproduced, combined


def open_fitted_factory_policy(reference):
    """Fixed installed owner entry; no caller root, clock, policy or loader."""
    return FittedFactoryUsePolicy(reference=reference)


def reopen_registered_fitted_query(reference):
    """Read-only reproduction entry over one original COMPLETE fitted query."""
    policy = open_fitted_factory_policy(reference)
    return policy.reopen_registered_fitted_query()
