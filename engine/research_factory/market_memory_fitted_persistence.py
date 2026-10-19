"""Fixed-study custody and current-authority reopening of retained normalization.

Existing reservation result custody owns the bytes. No alternate store, latest
fit pointer, caller clock/path, website entitlement or operational E0 grant is
introduced. Installed configuration remains disabled until genuinely selected.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from . import market_memory_fitted_use as use
from . import market_memory_e0_installed_control as owner
from . import market_memory_fit_bundle as codec
from .market_memory_e0_reservations import ReservationStore, MAX_RESULT_BYTES
from .market_memory_e0_reserved_read import _run_reserved_read
from engine.neuralweb import market_memory_fitted_normalization as fitted
from engine.neuralweb import market_memory_fitted_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_episode_features as features

_TOKEN = object()
_MODULE = "engine/research_factory/market_memory_fitted_persistence.py"
_SOURCES = use._SOURCE_PATHS + (_MODULE,
    "engine/research_factory/market_memory_fit_bundle.py",
    "engine/research_factory/market_memory_e0_reserved_read.py",
    "engine/neuralweb/market_memory_retained_use.py", "app/paywall.py")


class PersistedFitError(ValueError):
    """Stable refusal, never private bodies, arbitrary paths or credentials."""


def _require(ok, reason):
    if not ok:
        raise PersistedFitError(reason)


def _clock():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _immutable_window(body):
    value = use.control._domain_json(body)
    return cohort.canonical({k: v for k, v in value.items() if k != "selection_sha256"})


def _operation(window):
    digest = sha256(_immutable_window(window)).hexdigest()
    return "fit_" + digest, {"action": use.PURPOSE, "definition_sha256": digest}


def _window_reference(body):
    digest = sha256(body).hexdigest()
    return cohort.canonical({"schema": "market_memory.selected_training_inputs.v2",
        "object_id": "mmtrainingwindow_" + digest, "sha256": digest, "bytes": len(body)})


def _verify_original_window(body, selected_body, original):
    ref = use.control._domain_reference(use.control._domain_json(original["window_reference"]))
    _require(ref["schema"] == "market_memory.selected_training_inputs.v2"
        and ref["object_id"] == "mmtrainingwindow_" + ref["sha256"]
        and ref["bytes"] <= use.control.MAX_DOMAIN_OBJECT_BYTES
        and len(body) == ref["bytes"] and sha256(body).hexdigest() == ref["sha256"]
        and use.control._domain_json(body)["selection_sha256"] == sha256(selected_body).hexdigest(),
        "original_training_blob_missing_or_changed")


def _prove_continuation(fd, selected, records, current_window, original):
    """Original reference must be in the actual, already validated private chain."""
    before = use.control._domain_json(original["selection"])
    after = selected
    _require(set(before) == set(after) and all(before[k] == after[k] for k in before if k != "control_refs")
        and set(before["control_refs"]) == set(after["control_refs"])
        and all(before["control_refs"][k] == after["control_refs"][k]
                for k in before["control_refs"] if k != "access"), "immutable_fit_selection_changed")
    target = before["control_refs"]["access"]
    ref = after["control_refs"]["access"]
    seen = set()
    found = None
    while ref is not None:
        _require(ref["sha256"] not in seen and len(seen) < owner.MAX_ACCESS_RECORDS,
                 "retained_access_history_limit")
        seen.add(ref["sha256"])
        body = owner._read(fd, ref["sha256"] + ".json", use.control.MAX_CONTROL_BYTES)
        _require(len(body) == ref["bytes"] and sha256(body).hexdigest() == ref["sha256"],
                 "retained_access_reference_mismatch")
        state = use.control.parse_e0_control_record(body, kind="access_state")
        if ref == target:
            found = state
        ref = state["previous_state_ref"]
    _require(found is not None, "original_fit_access_not_in_current_history")
    return found
    # _load_selected_control validates the entire chain before this callback,
    # rereads all its exact bytes and selection afterwards, and checks final time.


@dataclass(frozen=True, slots=True)
class _Context:
    window: use.TrainingWindowCapability
    directory: Path
    binding: dict
    maximum_looks: int
    subject_id: str
    original_window: bytes | None = None


def _prepare_context(fd, selected, records, registration, purpose, original):
    body = use._prepare(fd, selected, records, registration, purpose)
    original_body = None
    if original is not None:
        previous = _prove_continuation(fd, selected, records, body, original)
        original_selected = use.control._domain_json(original["selection"])
        # Resolve the SAME original immutable method/tasks/membership/coverage/
        # split bytes via their actual references. Historical access is provenance
        # only; the current private chain was checked before and after callback.
        original_body = use._prepare(fd, original_selected, {**records, "access": previous},
                                     registration, purpose)
    return _context_values(fd, selected, records, body, original, original_body=original_body)


def _context_values(fd, selected, records, body, original, *, original_body=None):
    _require(records["access"]["status"] == "active"
        and records["access"]["contamination_state"] == "clean", "current_clean_training_access_required")
    if original is not None:
        _prove_continuation(fd, selected, records, body, original)
        _require(type(original_body) is bytes, "original_training_blob_resolution_required")
        _verify_original_window(original_body, original["selection"], original)
        _require(_immutable_window(original_body) == _immutable_window(body),
                 "immutable_training_definition_changed")
    return body, {"study_id": records["registration"]["study_id"],
        "installation_id": records["installation"]["installation_id"],
        "installation_epoch": records["installation"]["installation_epoch"],
        "registration_sha256": selected["control_refs"]["registration"]["sha256"],
        "publication_sha256": selected["control_refs"]["publication"]["sha256"]}, records["access"]["budget"]["maximum_looks"], original_body


def _load_context(original=None):
    _require(sys.platform == "linux" and os.geteuid() == 0
        and Path(__file__).resolve() == owner.INSTALLED_ROOT / _MODULE,
        "installed_fit_owner_required")
    purpose, purpose_body = use._purpose(owner.INSTALLED_ROOT)
    from engine.neuralweb import market_memory_retained_use  # Fixed owner, never generic native core.
    _verify_site_source()
    owner._verify_loaded_sources(paths=_SOURCES)
    _require(len(purpose["allowed_subject_ids"]) == 1, "single_registered_fit_subject_required")
    directory = owner.CONTROL_ROOT / sha256(purpose["selected_study_id"].encode()).hexdigest()
    values, selection = owner._load_selected_control(directory, purpose["selected_study_id"],
        lambda commit: owner._verify_source(owner.INSTALLED_ROOT, commit, paths=_SOURCES), clock=_clock,
        prepare=lambda fd, selected, records, registration: _prepare_context(
            fd, selected, records, registration, purpose, original))
    _require(use._purpose(owner.INSTALLED_ROOT)[1] == purpose_body, "fit_purpose_changed")
    body, binding, maximum, original_body = values
    window = use.TrainingWindowCapability(body, selection, _key=use._TOKEN)
    return _Context(window, directory, binding, maximum, purpose["allowed_subject_ids"][0], original_body)


def _verify_site_source():
    # The existing loaded-source verifier deliberately checks engine modules
    # only. This fixed application owner also executes the entitlement module.
    from app import paywall
    origin = getattr(paywall, "__file__", None)
    _require(type(origin) is str
        and Path(origin).resolve() == owner.INSTALLED_ROOT / "app/paywall.py",
        "installed_site_entitlement_source_required")


def _store(context):
    directory = context.directory / "reservations"
    with owner._directory(directory, private=True):
        pass
    return ReservationStore(directory, context.binding)


def _read_completed(context, operation, intent):
    store = _store(context)
    _require(store.snapshot()["maximum_looks"] == context.maximum_looks,
             "retained_fit_accounting_budget_changed")
    return store.read_completed(operation, intent)


def initialize_registered_fit_accounting():
    """Explicit fixed administrator action; not called by fit/open/query."""
    context = _load_context()
    with owner._directory(context.directory, private=True) as fd:
        try:
            os.mkdir("reservations", mode=0o700, dir_fd=fd)
            os.fsync(fd)
        except FileExistsError:
            pass
    current = _load_context()
    _require(current.binding == context.binding
        and current.window._body == context.window._body, "fit_accounting_selection_changed")
    return _store(current).initialize(current.maximum_looks)


def _reader():
    return features.trusted.TrustedFileAsKnownAtReader(
        features.trusted.default_trusted_store_root(owner.INSTALLED_ROOT))


def _training_population(context, policy):
    value = use.control._domain_json(context.window._body)
    source = value["binding"]["source_owner"]
    resource = {**source, "subject_id": context.subject_id,
                "query_cutoff": value["binding"]["fit_cutoff"]}
    for action in ("read_retained_macro_cohort", "verify_retained_macro_retention",
                   "use_retained_house_output_cohort_for_contextual_comparison"):
        cohort.authorize(policy, action, resource)
    reader = _reader()
    pin = reader.read_pinned_generation(generation_id=source["generation_id"],
                                       maximum_capture_count=cohort.MAX_CAPTURES)
    _require(pin.store_id == source["store_id"] and pin.generation_sha256 == source["generation_sha256"],
             "original_fit_generation_changed")
    return cohort.read_retained_context_cohort(reader, pin, subject_id=context.subject_id,
        query_cutoff=value["binding"]["fit_cutoff"], policy=policy)


def _rights(population, policy):
    cohort.disclose_retained_context_cohort(population, policy=policy)
    for cap in cohort.read_cohort_feature_capabilities(population, policy=policy):
        if cap is not None:
            features.disclose_episode_features(cap, policy=policy, for_comparison=True)


def _training_policy(context, policy):
    """Rebind only a genuine site's same principal to this authenticated window.

    The original request policy remains exact-generation-bound and unchanged.
    Existing non-site study policies retain their own established protocol.
    """
    from engine.neuralweb.market_memory_retained_use import RetainedHouseUsePolicy
    if type(policy) is not RetainedHouseUsePolicy:
        return policy
    _require(policy.root.resolve() == owner.INSTALLED_ROOT.resolve(), "installed_house_source_owner_required")
    policy.disclosure()  # Current real entitlement and unchanged source record.
    value = use.control._domain_json(context.window._body)
    source, binding = value["binding"]["source_owner"], value["binding"]
    _require(policy.expected["store_id"] == source["store_id"]
        and policy.expected["subject_id"] == context.subject_id and policy.mode == binding["mode"],
        "same_registered_training_site_scope_required")
    return RetainedHouseUsePolicy(policy.root, user_id=policy.user_id,
        store_id=source["store_id"], generation_id=source["generation_id"],
        generation_sha256=source["generation_sha256"], subject_id=context.subject_id,
        query_cutoff=binding["fit_cutoff"], mode=binding["mode"])


class _ExactHouseScopes:
    """Two actual same-principal House scopes; never a wider House permission."""
    def __init__(self, training, query, *, _key=None):
        from engine.neuralweb.market_memory_retained_use import RetainedHouseUsePolicy
        _require(_key is _TOKEN and type(training) is RetainedHouseUsePolicy
            and type(query) is RetainedHouseUsePolicy, "actual_exact_house_scopes_required")
        self._policies = (training, query)
        self._principal = training.user_id
        self._root = training.root.resolve()
        _require(self._root == owner.INSTALLED_ROOT.resolve(), "installed_house_source_owner_required")
        self._registration = training.registration_sha256
        self._mode = training.mode
        self.policy_id = training.policy_id
        self._scopes = cohort.canonical([training.expected, query.expected])
        self._current()

    def _current(self):
        from engine.neuralweb.market_memory_retained_use import RetainedHouseUsePolicy
        _require(all(type(p) is RetainedHouseUsePolicy and p.user_id == self._principal
            and p.root.resolve() == self._root and p.registration_sha256 == self._registration
            and p.mode == self._mode and p.policy_id == self.policy_id for p in self._policies),
            "same_current_house_principal_and_source_required")

    def check(self, action, resource):
        self._current()
        _require(type(resource) is dict, "exact_house_resource_required")
        matched = False
        for policy, scope in zip(self._policies, json.loads(self._scopes), strict=True):
            if (all(resource.get(k) == scope[k] for k in
                    ("store_id", "generation_id", "generation_sha256", "query_cutoff"))
                    and resource.get("subject_id", resource.get("requested_subject_id")) == scope["subject_id"]):
                policy.check(action, resource)  # Actual current entitlement and source-registration checks.
                matched = True
        _require(matched, "only_original_training_or_exact_query_scope_allowed")


def _comparison_policy(retained, query_policy):
    from engine.neuralweb.market_memory_retained_use import RetainedHouseUsePolicy
    if type(query_policy) is RetainedHouseUsePolicy or type(retained._policy) is RetainedHouseUsePolicy:
        return _ExactHouseScopes(retained._policy, query_policy, _key=_TOKEN)
    return query_policy


@dataclass(frozen=True, slots=True, init=False, repr=False)
class RetainedFitCapability:
    _body: bytes
    _digest: str
    _binding: dict
    _population: object
    _policy: object
    _observed_at: str
    _seal: object

    def __init__(self, body, binding, population, policy, observed_at, *, _key=None):
        _require(_key is _TOKEN, "owner_completed_fit_required")
        for key, value in (("_body", body), ("_digest", sha256(body).hexdigest()),
            ("_binding", binding), ("_population", population), ("_policy", policy),
            ("_observed_at", observed_at), ("_seal", _TOKEN)):
            object.__setattr__(self, key, value)


def disclose_retained_fit(capability):
    _require(type(capability) is RetainedFitCapability and capability._seal is _TOKEN
        and type(capability._body) is bytes and len(capability._body) <= MAX_RESULT_BYTES
        and sha256(capability._body).hexdigest() == capability._digest, "owner_completed_fit_required")
    original = codec.decode_bundle(capability._body)
    original["window_reference"] = original["window"]
    current = _load_context(original)
    _require(current.binding == capability._binding, "retained_fit_installation_changed")
    _rights(capability._population, capability._policy)
    operation, intent = _operation(current.window._body)
    body = _read_completed(current, operation, intent)
    _require(body == capability._body, "original_completed_fit_changed")
    _load_context(original)
    _rights(capability._population, capability._policy)
    return {**original, "window": current.original_window, "observed_complete_at": capability._observed_at,
            "receipt": {"binding": current.binding, "operation_id": operation,
                        "intent_sha256": sha256(cohort.canonical(intent)).hexdigest(),
                        "sha256": capability._digest, "bytes": len(body)}}


def _disclose_retained_window(window):
    original = disclose_retained_fit(window._retained)
    _require(original["window"] == window._body, "retained_training_window_changed")
    return use.control._domain_json(window._body)


def open_registered_fit(*, policy):
    """Only COMPLETE: no initialize/reserve/load/refit on missing or pending."""
    context = _load_context()
    policy = _training_policy(context, policy)
    population = _training_population(context, policy)
    _rights(population, policy)  # Before persisted numerical bytes are read.
    operation, intent = _operation(context.window._body)
    body = _read_completed(context, operation, intent)
    original = codec.decode_bundle(body)
    original["window_reference"] = original["window"]
    current = _load_context(original)
    _require(current.binding == context.binding, "retained_fit_installation_changed")
    now = _clock()
    _require(cohort.utc_instant(original["constructed_at"]) <= cohort.utc_instant(now),
             "retained_construction_clock_in_future")
    result = RetainedFitCapability(body, current.binding, population, policy, now, _key=_TOKEN)
    # Validate native source/parameter reproduction without the fitting constructor.
    fitted.reopen_retained_normalizer(result, population, policy=policy)
    disclose_retained_fit(result)
    return result


def persist_registered_fit(*, policy):
    """Exactly one original accounted fit; no refit on COMPLETE or PENDING."""
    context = _load_context()
    _require(cohort.utc_instant(use.control._domain_json(context.window._body)["binding"]["fit_cutoff"])
        <= cohort.utc_instant(_clock()), "training_cutoff_not_yet_observed")
    policy = _training_policy(context, policy)
    origin = {"window_reference": _window_reference(context.window._body), "selection": context.window._selection}
    operation, intent = _operation(context.window._body)
    operation_identity = _operation
    store = _store(context)
    loaded_population = []
    constructed = []
    def authorize(_phase, _operation, _intent):
        current = _load_context(origin)
        _require(current.binding == context.binding, "fit_installation_changed")
        _require(store.snapshot()["maximum_looks"] == current.maximum_looks, "fit_accounting_budget_changed")
        if not loaded_population:
            loaded_population.append(_training_population(current, policy))
        _rights(loaded_population[0], policy)
    def load():
        population = loaded_population[0]
        normalizer = fitted.fit_registered_normalizer(context.window, population, policy=policy)
        value = fitted.disclose_fitted_normalizer(normalizer, policy=policy)
        constructed.append(normalizer)
        return codec.encode_bundle(normalizer._body, _window_reference(context.window._body),
                                   context.window._selection, value["construction"]["constructed_at"])
    def qualify(body, _operation, _intent):
        decoded = codec.decode_bundle(body)
        decoded["window_reference"] = decoded["window"]
        if constructed:
            cap = constructed[0]
            fitted.disclose_fitted_normalizer(cap, policy=policy)
            _require(decoded["parameters"] == cap._body
                and decoded["constructed_at"] == cap._constructed_at
                and decoded["window"] == _window_reference(context.window._body)
                and decoded["selection"] == context.window._selection,
                "original_fit_receipt_construction_mismatch")
        qualified = _load_context(decoded)
        _require(_operation == operation and _intent == intent
            and _operation == operation_identity(qualified.window._body)[0],
            "completed_fit_definition_mismatch")
    _run_reserved_read(store, operation, intent, authorize=authorize, load=load, qualify=qualify)
    return open_registered_fit(policy=policy)


def retain_registered_fitted_query(retained, population, query, *, policy, k):
    """Retain one genuine later native query; exact repeats use COMPLETE.

    Native owner capabilities, not caller feature dictionaries or loaders,
    supply query/candidate identity. The caller retains those exact inputs for
    any same-operation recovery; no new clock or generation is substituted.
    """
    _require(type(k) is int and 1 <= k <= retrieval.baseline.MAX_K, "finite_query_k_required")
    original = disclose_retained_fit(retained)
    context = _load_context(original)
    _rights(population, policy)
    projected = features.disclose_episode_features(query, policy=policy, for_comparison=True)
    actual = cohort.disclose_retained_context_cohort(population, policy=policy)
    cutoff = projected["owner"]["query_cutoff"]
    now = _clock()
    _require(cohort.utc_instant(retained._observed_at) <= cohort.utc_instant(cutoff)
        <= cohort.utc_instant(now), "genuine_query_after_completed_fit_required")
    source = use.control._domain_json(original["window"])["binding"]
    _require(cohort.utc_instant(cutoff) > cohort.utc_instant(source["fit_cutoff"])
        and actual["owner"]["generation_id"] != source["source_owner"]["generation_id"],
        "later_native_generation_and_query_cutoff_required")
    _require(actual["owner"] == {key: projected["owner"][key] for key in actual["owner"]},
             "query_exact_population_required")
    combined = _comparison_policy(retained, policy)
    normalizer = fitted.reopen_retained_normalizer(retained, retained._population, policy=combined)
    spec = use.control._domain_json(original["window"])["eligibility_method_spec"]
    method = retrieval.baseline.RetainedContextMethodSpec(
        spec["purge_calendar_days"], spec["embargo_calendar_days"], spec["mode"])
    intent = {"action": "retained_fitted_query.v2", "fit_sha256": retained._digest,
        "query_id": projected["owner"]["query_id"], "generation_id": actual["owner"]["generation_id"],
        "generation_sha256": actual["owner"]["generation_sha256"], "query_cutoff": cutoff, "k": k,
        "method_spec_id": spec["method_spec_id"]}
    operation = "query_" + sha256(cohort.canonical(intent)).hexdigest()
    store = _store(context)
    def authorize(_phase, _operation, _intent):
        current = _load_context(original)
        _require(current.binding == retained._binding
            and store.snapshot()["maximum_looks"] == current.maximum_looks,
            "query_accounting_binding_changed")
        disclose_retained_fit(retained)
        _rights(population, policy)
        features.disclose_episode_features(query, policy=policy, for_comparison=True)
    def load():
        cap = retrieval.retrieve_fitted_contexts(normalizer, population, query,
                                                policy=combined, k=k, eligibility=method)
        return cohort.canonical({"schema": "market_memory.retained_fitted_query.v1",
            "fit_receipt": original["receipt"], "query_cutoff": cutoff,
            "fit_observed_complete_at": retained._observed_at,
            "index": fitted.build_fitted_exact_index(normalizer, population, policy=combined),
            "result": retrieval.disclose_fitted_retrieval(cap, policy=combined)})
    def qualify(body, _operation, _intent):
        value = use.control._domain_json(body)
        _require(value["fit_receipt"] == original["receipt"] and value["query_cutoff"] == cutoff,
                 "retained_query_reference_mismatch")
    body = _run_reserved_read(store, operation, intent, authorize=authorize, load=load, qualify=qualify)
    return {"operation_id": operation, "intent": intent, "sha256": sha256(body).hexdigest(),
            "bytes": len(body), "value": use.control._domain_json(body)}


def reproduce_registered_fitted_query(reference, *, policy):
    """Explicit deterministic reproduction of an existing COMPLETE query only.

    This never initializes/reserves, refits, replaces a generation, or calls an
    original effect loader. Newly minted native caps authenticate the original
    query/index content under current rights; no serialized dict gains authority.
    Return the genuine retrieval cap and owner-made policy limited to the exact
    original training and query scopes, both checked against the same principal.
    """
    _require(type(reference) is dict and set(reference) ==
        {"operation_id", "intent", "sha256", "bytes", "value"}, "retained_query_reference_required")
    retained = open_registered_fit(policy=policy)
    original = disclose_retained_fit(retained)
    context = _load_context(original)
    intent = reference["intent"]
    _require(type(intent) is dict and set(intent) == {"action", "fit_sha256", "query_id",
        "generation_id", "generation_sha256", "query_cutoff", "k", "method_spec_id"}
        and intent["action"] == "retained_fitted_query.v2" and intent["fit_sha256"] == retained._digest
        and type(intent["k"]) is int and 1 <= intent["k"] <= retrieval.baseline.MAX_K,
        "exact_retained_query_intent_required")
    operation = "query_" + sha256(cohort.canonical(intent)).hexdigest()
    _require(reference["operation_id"] == operation, "retained_query_operation_mismatch")
    _require(all(type(intent[key]) is str and 0 < len(intent[key]) <= 128 for key in
        ("query_id", "generation_id", "generation_sha256", "query_cutoff", "method_spec_id"))
        and intent["generation_id"].startswith("mmgeneration_")
        and type(reference["sha256"]) is str and len(reference["sha256"]) == 64,
        "bounded_original_query_identity_required")
    _require(cohort.utc_instant(original["constructed_at"]) <= cohort.utc_instant(intent["query_cutoff"])
        <= cohort.utc_instant(_clock()), "retained_query_clock_mismatch")
    source = use.control._domain_json(original["window"])["binding"]
    _require(cohort.utc_instant(intent["query_cutoff"]) > cohort.utc_instant(source["fit_cutoff"])
        and intent["generation_id"] != source["source_owner"]["generation_id"],
        "later_native_generation_and_query_cutoff_required")
    reader = _reader()
    pin = reader.read_pinned_generation(generation_id=intent["generation_id"],
                                       maximum_capture_count=cohort.MAX_CAPTURES)
    _require(pin.generation_sha256 == intent["generation_sha256"], "original_query_generation_changed")
    _require(pin.store_id == use.control._domain_json(original["parameters"])["source_owner"]["store_id"],
             "original_query_store_changed")
    population = cohort.read_retained_context_cohort(reader, pin, subject_id=context.subject_id,
        query_cutoff=intent["query_cutoff"], policy=policy)
    query = features.read_episode_feature_capability(reader, pin, query_id=intent["query_id"],
        subject_id=context.subject_id, query_cutoff=intent["query_cutoff"], policy=policy)
    _rights(population, policy)
    body = _read_completed(context, operation, intent)
    _require(type(reference["bytes"]) is int and reference["bytes"] == len(body)
        and reference["sha256"] == sha256(body).hexdigest(), "retained_query_bytes_mismatch")
    value = use.control._domain_json(body)
    _require(set(value) == {"schema", "fit_receipt", "query_cutoff", "fit_observed_complete_at", "index", "result"}
        and value["schema"] == "market_memory.retained_fitted_query.v1"
        and value["fit_receipt"] == original["receipt"] and value["query_cutoff"] == intent["query_cutoff"],
        "retained_query_reference_mismatch")
    _require(cohort.utc_instant(original["constructed_at"]) <= cohort.utc_instant(value["fit_observed_complete_at"])
        <= cohort.utc_instant(intent["query_cutoff"]) <= cohort.utc_instant(_clock()),
        "retained_query_clock_mismatch")
    combined = _comparison_policy(retained, policy)
    normalizer = fitted.reopen_retained_normalizer(retained, retained._population, policy=combined)
    spec = use.control._domain_json(original["window"])["eligibility_method_spec"]
    _require(intent["method_spec_id"] == spec["method_spec_id"], "original_query_method_changed")
    method = retrieval.baseline.RetainedContextMethodSpec(
        spec["purge_calendar_days"], spec["embargo_calendar_days"], spec["mode"])
    reproduced = retrieval.retrieve_fitted_contexts(normalizer, population, query,
        policy=combined, k=intent["k"], eligibility=method)
    _require(value["result"] == retrieval.disclose_fitted_retrieval(reproduced, policy=combined)
        and value["index"] == fitted.build_fitted_exact_index(normalizer, population, policy=combined),
        "original_query_index_or_result_changed")
    disclose_retained_fit(retained)
    _rights(population, policy)
    # A single-generation request policy cannot disclose both the original fit
    # and later query. Return the genuine native cap with this exact owner-made
    # policy, matching the existing internal attachment-consumer convention.
    return reproduced, combined
