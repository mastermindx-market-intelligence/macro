"""Dormant fixed-owner composition for selected, published archived marks.

Two existing private roles avoid a hash cycle: registration.access_rules_ref
freezes purpose/definition, while current access.scope_ref binds a generation
published afterwards. Metadata alone and ordinary site entitlement grant no
outcome use. Only the authenticated installed administrator owner composes this
capability; no route, publication, source acquisition or study is activated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from . import market_memory_contextual_registration as control
from . import market_memory_e0_installed_control as owner
from . import market_memory_e0_task_evidence as registered_tasks
from engine.neuralweb import market_memory_episode_outcomes as outcomes
from engine.neuralweb import market_memory_contextual_observation_store as observations
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_technical_store as technical
from engine.neuralweb import market_memory_price_metadata_use as price_use

_TOKEN = object()
_MODULE = "engine/research_factory/market_memory_outcome_use.py"
_SCHEMA = "contracts/market_memory/outcome_use_binding.v2.schema.json"
_RULE = "market_memory.outcome_access_rules.v2"
_BINDING = "market_memory.outcome_use_binding.v2"
_DEFINITION = "market_memory.retained_archived_bar_outcome_definition.v1"
_PURPOSE = "read_published_archived_mark_comparisons_after_selection"
_MAX = 256 * 1024
_SELECTOR = "config/market_memory_retained_outcome_use.v2.json"
_SOURCES = owner._TASK_SOURCE_PATHS + (_MODULE, _SCHEMA,
    _SELECTOR,
    "engine/neuralweb/market_memory_episode_outcomes.py",
    "engine/neuralweb/market_memory_contextual_observation_store.py",
    "engine/neuralweb/market_memory_episode_retrieval.py",
    "engine/neuralweb/market_memory_retained_context_cohort.py",
    "engine/neuralweb/market_memory_technical_store.py",
    "engine/neuralweb/market_memory_technical_observation.py",
    "engine/neuralweb/market_memory_price_metadata_use.py",
    "engine/neuralweb/market_memory_retained_use.py", "app/paywall.py",
    "config/market_memory_retained_use.v1.json",
    "research/licenses/MARKET_MEMORY_HOUSE_MACRO_REUSE_2026-10-13.md",
    "config/market_memory_technical_price_basis.v1.json",
    "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md")
_OUTCOME_ACTIONS = frozenset(("read_retained_contextual_observation_metadata",
    "read_registered_contextual_outcome_labels", "read_retained_contextual_observation",
    "disclose_retained_contextual_observation", "read_retained_source_bar_marks",
    "disclose_retained_source_bar_marks", "read_retained_source_bar_generation_metadata",
    "read_retained_source_bar_metadata", "disclose_retained_source_bar_metadata"))


class OutcomeUseError(ValueError):
    """Fixed refusal only; no private objects, paths, account or numerical data."""


def _require(ok, reason):
    if not ok:
        raise OutcomeUseError(reason)


def _clock():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse(body, ref, role):
    from jsonschema import FormatChecker
    ref = control._domain_reference(ref)
    _require(ref["schema"] == role and ref["bytes"] <= _MAX
        and type(body) is bytes and len(body) == ref["bytes"]
        and sha256(body).hexdigest() == ref["sha256"], "exact_outcome_role_bytes_required")
    value = control._domain_json(body)
    schema = json.loads((Path(__file__).resolve().parents[2] / _SCHEMA).read_text())
    _require(control._domain_snapshot(value)[1] == body and
        next(control._INTEGER_VALIDATOR(schema, format_checker=FormatChecker()).iter_errors(value), None) is None,
        "closed_outcome_role_required")
    identity = "rules_id" if role == _RULE else "binding_id"
    _require(value["schema"] == role and value[identity] == ref["object_id"], "outcome_role_identity_mismatch")
    return value


def _prepare(fd, selected, records, registration):
    reg, access, installed = records["registration"], records["access"], records["installation"]
    _require(access["status"] == "active" and access["contamination_state"] == "clean"
        and "read_registered_outcome_labels" in installed["permitted_actions"],
        "current_registered_outcome_access_required")
    refs = {"rules": control._domain_reference(reg["access_rules_ref"]),
            "binding": control._domain_reference(access["scope_ref"])}
    _require(refs["rules"]["schema"] == _RULE and refs["binding"]["schema"] == _BINDING
        and refs["rules"]["sha256"] != refs["binding"]["sha256"], "distinct_selected_outcome_roles_required")
    bodies = {name: owner._read(fd, ref["sha256"] + ".json", _MAX) for name, ref in refs.items()}
    rules = _parse(bodies["rules"], refs["rules"], _RULE)
    binding = _parse(bodies["binding"], refs["binding"], _BINDING)
    _require(rules["study_id"] == reg["study_id"] and rules["purpose"] == _PURPOSE
        and binding["registration_ref"] == selected["control_refs"]["registration"]
        and binding["access_rules_ref"] == refs["rules"]
        and binding["installation_id"] == installed["installation_id"]
        and binding["installation_epoch"] == installed["installation_epoch"], "exact_selected_outcome_scope_required")
    cases = binding["observations"]
    _require(len({row["capture_id"] for row in cases}) == len(cases)
        and len({row["context_id"] for row in cases}) == len(cases), "unique_outcome_context_bindings_required")
    definition_ref = control._domain_reference(rules["definition_ref"])
    _require(definition_ref["schema"] == _DEFINITION and definition_ref["bytes"] <= _MAX,
        "registered_archived_mark_definition_required")
    definition_body = owner._read(fd, definition_ref["sha256"] + ".json", _MAX)
    _require(len(definition_body) == definition_ref["bytes"]
        and sha256(definition_body).hexdigest() == definition_ref["sha256"], "outcome_definition_bytes_mismatch")
    declared = control._domain_json(definition_body)
    _require(type(declared) is dict and {"first_session", "last_session", "observation_deadline"} <= set(declared),
             "complete_native_outcome_definition_required")
    definition = outcomes.RetainedArchivedBarOutcomeDefinition(
        declared["first_session"], declared["last_session"], declared["observation_deadline"])
    _require(definition.disclosure() == declared and definition_ref["object_id"] == declared["definition_sha256"],
        "native_archived_mark_definition_required")
    for name, ref in refs.items():
        _require(owner._read(fd, ref["sha256"] + ".json", _MAX) == bodies[name], "outcome_role_changed")
    _require(owner._read(fd, definition_ref["sha256"] + ".json", _MAX) == definition_body,
        "outcome_definition_changed")
    role_refs = {"method_manifest": reg["implementation"]["method_ref"], "task_manifest": reg["tasks_ref"],
                 "frozen_membership": reg["corpus"]["membership_ref"]}
    role_bytes = {}
    for name, ref in role_refs.items():
        ref = control._domain_reference(ref)
        _require(ref["bytes"] <= control.MAX_DOMAIN_OBJECT_BYTES, "bounded_registered_outcome_method_required")
        body = owner._read(fd, ref["sha256"] + ".json", control.MAX_DOMAIN_OBJECT_BYTES)
        _require(len(body) == ref["bytes"] and sha256(body).hexdigest() == ref["sha256"],
                 "registered_outcome_method_bytes_mismatch")
        role_bytes[name] = body
    method, _joins = registered_tasks.resolve_registered_task_inputs(registration=registration, **role_bytes)
    for name, body in role_bytes.items():
        _require(owner._read(fd, role_refs[name]["sha256"] + ".json", control.MAX_DOMAIN_OBJECT_BYTES) == body,
                 "registered_outcome_method_changed")
    history, ref = [], selected["control_refs"]["access"]
    while ref is not None:
        _require(ref not in history and len(history) < owner.MAX_ACCESS_RECORDS,
                 "bounded_original_outcome_history_required")
        history.append(ref)
        body = owner._read(fd, ref["sha256"] + ".json", control.MAX_CONTROL_BYTES)
        _require(len(body) == ref["bytes"] and sha256(body).hexdigest() == ref["sha256"],
                 "original_outcome_access_bytes_mismatch")
        ref = control.parse_e0_control_record(body, kind="access_state")["previous_state_ref"]
    return {"rules": rules, "binding": binding, "definition": declared,
        "registration": reg, "registration_sha256": selected["control_refs"]["registration"]["sha256"],
        "rules_ref": refs["rules"], "binding_ref": refs["binding"], "access_history_refs": history,
        "method_spec": method.disclosure()}


def _load_context(study_id):
    _require(sys.platform == "linux" and os.geteuid() == 0
        and Path(__file__).resolve() == owner.INSTALLED_ROOT / _MODULE, "installed_outcome_owner_required")
    _require(type(study_id) is str and control._ID.fullmatch(study_id) is not None, "exact_outcome_study_required")
    owner._verify_loaded_sources(paths=_SOURCES)
    directory = owner.CONTROL_ROOT / sha256(study_id.encode()).hexdigest()
    context, selected = owner._load_selected_control(directory, study_id,
        lambda commit: owner._verify_source(owner.INSTALLED_ROOT, commit, paths=_SOURCES), clock=_clock,
        prepare=_prepare)
    try:
        price_use.verify_installed_price_metadata_closure(owner.INSTALLED_ROOT,
            expected_head=control._domain_json(selected)["source_commit"])
    except price_use.MarketMemoryPriceMetadataPolicyError as exc:
        raise OutcomeUseError("current_original_source_authority_required") from exc
    license_ref = context["rules"]["source_authority"]
    with owner._directory(owner.INSTALLED_ROOT / "research/licenses", private=False) as fd:
        license_body = owner._read(fd, "MASSIVE_ENTITLEMENT_RECORD.md", 64 * 1024, private=False)
    _require(sha256(license_body).hexdigest() == license_ref["sha256"], "current_original_source_authority_required")
    return context, selected


def _site_policy(policy):
    from engine.neuralweb.market_memory_retained_use import RetainedHouseUsePolicy
    _require(type(policy) is RetainedHouseUsePolicy, "existing_request_local_site_owner_required")
    _require(isinstance(getattr(policy, "root", None), Path)
        and policy.root.resolve() == owner.INSTALLED_ROOT.resolve(), "installed_site_source_owner_required")
    return policy


@dataclass(frozen=True, slots=True, init=False, repr=False)
class RegisteredOutcomeUseCapability:
    _body: bytes
    _selection: object
    _site_policy: object
    _control: bytes
    _seal: object

    def __init__(self, body, selection, site_policy, selected_control, *, _key=None):
        _require(_key is _TOKEN, "installed_outcome_use_required")
        for name, value in (("_body", body), ("_selection", selection), ("_site_policy", site_policy),
                            ("_control", selected_control), ("_seal", _TOKEN)):
            object.__setattr__(self, name, value)


def _use_identity(context, selected):
    value = control._domain_json(selected)
    identity = {"source_commit": value["source_commit"],
        "controls": {key: ref for key, ref in value["control_refs"].items() if key != "access"},
        "rules_ref": context["rules_ref"], "binding_ref": context["binding_ref"]}
    return "mmoutcomeuse_" + sha256(cohort.canonical(identity)).hexdigest()


def prepare_registered_outcome_use(study_id, selection, *, lens, outcome_cutoff, site_policy,
                                   expected_use_identity=None):
    """The study is a selector, never authority; no caller generation or policy callback."""
    _require(expected_use_identity is None or (type(expected_use_identity) is str
        and len(expected_use_identity) == len("mmoutcomeuse_") + 64
        and expected_use_identity.startswith("mmoutcomeuse_")
        and all(c in "0123456789abcdef" for c in expected_use_identity.removeprefix("mmoutcomeuse_"))),
        "bounded_original_outcome_use_identity_required")
    site_policy = _site_policy(site_policy)
    selected = retrieval.disclose_episode_retrieval(selection, policy=site_policy)
    context, control_bytes = _load_context(study_id)
    identity = _use_identity(context, control_bytes)
    _require(expected_use_identity is None or expected_use_identity == identity,
             "original_outcome_use_identity_changed")
    query = selected["query_owner"]
    corpus = context["registration"]["corpus"]
    _require(all(query[key] == corpus[key] for key in ("store_id", "generation_id", "generation_sha256"))
        and query["subject_id"] == context["rules"]["subject_id"], "exact_registered_outcome_population_required")
    _require(selected["method_spec"] == context["method_spec"], "exact_registered_outcome_method_required")
    cutoff, query_cutoff = outcomes._clock(outcome_cutoff), outcomes._clock(query["query_cutoff"])
    _require(lens in ("then_known", "later_observed") and cutoff <= outcomes._clock(_clock())
        and ((lens == "then_known" and cutoff == query_cutoff)
             or (lens == "later_observed" and cutoff >= query_cutoff)), "registered_outcome_lens_required")
    by_capture = {row["capture_id"]: row for row in context["binding"]["observations"]}
    ids = []
    for row in selected["selected"]:
        candidate = row["candidate"]
        record = by_capture.get(candidate["capture_id"])
        _require(record is not None and all(record[key] == candidate[key]
            for key in ("context_id", "capture_id", "packet_sha256")), "registered_selected_observation_required")
        ids.append(record["observation_id"])
    body = cohort.canonical({"schema": "market_memory.registered_outcome_use.v2", "study_id": study_id,
        "outcome_use_identity": identity,
        "retrieval_id": selected["retrieval_id"], "selection_sha256": selected["selection_sha256"],
        "query_cutoff": query["query_cutoff"], "outcome_cutoff": outcome_cutoff, "lens": lens,
        "definition_sha256": context["definition"]["definition_sha256"],
        "rules_ref": context["rules_ref"], "binding_ref": context["binding_ref"], "observation_ids": ids,
        "operational_admission": False})
    result = RegisteredOutcomeUseCapability(body, selection, site_policy, control_bytes, _key=_TOKEN)
    _refresh(result)
    return result


def _refresh(capability):
    _require(type(capability) is RegisteredOutcomeUseCapability and capability._seal is _TOKEN
        and type(capability._body) is bytes and len(capability._body) <= _MAX, "installed_outcome_use_required")
    value = control._domain_json(capability._body)
    context, selected_bytes = _load_context(value["study_id"])
    before, after = (control._domain_json(body) for body in (capability._control, selected_bytes))
    _require(set(before) == set(after) and all(before[key] == after[key] for key in before if key != "control_refs")
        and all(before["control_refs"][key] == after["control_refs"][key]
            for key in before["control_refs"] if key != "access")
        and context["rules_ref"] == value["rules_ref"] and context["binding_ref"] == value["binding_ref"],
        "original_outcome_scope_changed")
    _require(before["control_refs"]["access"] in context["access_history_refs"]
        and _use_identity(context, selected_bytes) == value["outcome_use_identity"],
        "original_outcome_access_not_in_current_history")
    selected = retrieval.disclose_episode_retrieval(capability._selection, policy=_site_policy(capability._site_policy))
    _require(selected["retrieval_id"] == value["retrieval_id"]
        and selected["selection_sha256"] == value["selection_sha256"]
        and selected["query_owner"]["query_cutoff"] == value["query_cutoff"], "original_outcome_selection_changed")
    return value, context


class _OutcomePolicy:
    """Trusted owner only: exact closed native resources; site rights stay additive."""
    def __init__(self, cap, context, *, _key=None):
        _require(_key is _TOKEN, "installed_outcome_use_required")
        self.cap, self.context, self.entries = cap, context, []
        self.policy_id = "mm.outcome-use.v2:" + sha256(cap._body).hexdigest()

    def check(self, action, resource):
        _value, current = _refresh(self.cap)
        _require(current == self.context, "current_outcome_scope_changed")
        if action not in _OUTCOME_ACTIONS:
            _require(not action.startswith("publish_") and not action.startswith("append_"), "outcome_read_only_purpose")
            return self.cap._site_policy.check(action, resource)
        _require(action in current["binding"]["permitted_actions"], "current_named_outcome_action_required")
        namespace = {"profile": technical.STORE_PROFILE, "store_id": current["rules"]["technical_store_id"],
                     "namespace": observations._NAMESPACE}
        if action == "read_retained_contextual_observation_metadata":
            _require(resource == namespace, "exact_outcome_namespace_required")
            return None
        observation_resources = [{**namespace, "definition_sha256": entry["definition_sha256"],
            "e0_registration_sha256": entry["e0_registration_sha256"],
            "observation_id": entry["observation_id"], "context_ref": entry["context_ref"]} for entry in self.entries]
        marks = [entry["mark_use_resource"] for entry in self.entries if entry["mark_use_resource"] is not None]
        if action == "read_registered_contextual_outcome_labels":
            _require(resource in observation_resources + marks, "exact_registered_label_resource_required")
        elif action in ("read_retained_contextual_observation", "disclose_retained_contextual_observation"):
            _require(resource in observation_resources, "exact_registered_observation_resource_required")
        elif action in ("read_retained_source_bar_marks", "disclose_retained_source_bar_marks"):
            _require(resource in marks, "original_mark_purpose_resource_required")
        else:
            sources = [entry["source_resource"] for entry in self.entries if entry["source_resource"] is not None]
            _require(any(all(resource.get(key) == source[key] for key in
                ("profile", "store_id", "generation_id", "generation_sha256")) for source in sources),
                "original_source_metadata_generation_required")
            expected = {"profile", "store_id", "generation_id", "generation_sha256"}
            if action != "read_retained_source_bar_generation_metadata": expected.add("source_observation_id")
            _require(set(resource) == expected, "closed_source_metadata_resource_required")
        return None


def _pin_registered_observations(capability):
    value, context = _refresh(capability)
    policy = _OutcomePolicy(capability, context, _key=_TOKEN)
    root = technical.default_technical_actual_output_store_root(owner.INSTALLED_ROOT)
    reference = context["binding"]["observation_generation_ref"]
    pin = observations.pin_contextual_observation_generation(root,
        technical_store_id=context["rules"]["technical_store_id"], exact_generation_ref=reference, policy=policy)
    manifest = observations._disclose_pin(pin, policy)
    ids = tuple(value["observation_ids"])
    entries = {row["observation_id"]: row for row in manifest["entries"]}
    selected_entries = [entries[identity] for identity in ids if identity is not None and identity in entries]
    _require(all(identity is None or identity in entries for identity in ids), "original_published_observation_missing")
    _require(all(entry["definition_sha256"] == value["definition_sha256"]
        and entry["e0_registration_sha256"] == context["registration_sha256"]
        and outcomes._clock(context["registration"]["registered_at"]) <= outcomes._clock(entry["published_at"])
        for entry in selected_entries),
        "original_published_outcome_registration_required")
    # Future metadata can authenticate the exact read pin, but cannot grant a
    # then-known label/mark read through the composed policy returned below.
    policy.entries = [entry for entry in selected_entries
        if outcomes._clock(entry["published_at"]) <= outcomes._clock(value["outcome_cutoff"])]
    namespace = {"profile": technical.STORE_PROFILE, "store_id": context["rules"]["technical_store_id"],
                 "namespace": observations._NAMESPACE}
    for entry in policy.entries:
        resource = {**namespace, "definition_sha256": entry["definition_sha256"],
            "e0_registration_sha256": entry["e0_registration_sha256"],
            "observation_id": entry["observation_id"], "context_ref": entry["context_ref"]}
        for action in ("read_registered_contextual_outcome_labels", "read_retained_contextual_observation",
                       "disclose_retained_contextual_observation"):
            policy.check(action, resource)
        if entry["mark_use_resource"] is not None:
            technical._marks_authorization(policy, entry["mark_use_resource"])
            technical._marks_authorization(policy, entry["mark_use_resource"], disclose=True)
    _refresh(capability)
    return pin, policy, ids


def read_registered_outcome_attachment(capability):
    value, _context = _refresh(capability)
    pin, policy, ids = _pin_registered_observations(capability)
    attachment = outcomes.attach_contextual_outcomes(capability._selection, pin, observation_ids=ids,
        definition_sha256=value["definition_sha256"], lens=value["lens"], outcome_cutoff=value["outcome_cutoff"], policy=policy)
    _refresh(capability)
    return attachment, policy


def disclose_registered_outcome_use(capability):
    """Public inert descriptor. Then-known never leaks a future generation identity."""
    value, context = _refresh(capability)
    return {key: value[key] for key in ("schema", "outcome_use_identity", "retrieval_id", "selection_sha256", "query_cutoff",
        "outcome_cutoff", "lens", "definition_sha256", "operational_admission")} | {
        "observation_generation_ref": None if value["lens"] == "then_known" else
            context["binding"]["observation_generation_ref"]}


def _routing_selector():
    _require(sys.platform == "linux" and os.geteuid() == 0
        and Path(__file__).resolve() == owner.INSTALLED_ROOT / _MODULE, "installed_outcome_owner_required")
    with owner._directory(owner.INSTALLED_ROOT / "config", private=False) as fd:
        body = owner._read(fd, "market_memory_retained_outcome_use.v2.json", 16384, private=False)
    return _parse_selector(body), body


def _parse_selector(body):
    _require(type(body) is bytes and 0 < len(body) <= 16384, "bounded_outcome_selector_required")
    value = control._domain_json(body)
    _require(type(value) is dict and set(value) == {"schema", "enabled", "selected_study_id"}
        and control._domain_snapshot(value)[1] == body
        and value["schema"] == "market_memory.retained_outcome_selector.v2"
        and type(value["enabled"]) is bool, "closed_outcome_routing_selector_required")
    if not value["enabled"]:
        _require(value["selected_study_id"] is None, "dormant_outcome_selector_required")
        return None
    _require(type(value["selected_study_id"]) is str
        and control._ID.fullmatch(value["selected_study_id"]) is not None, "exact_outcome_routing_study_required")
    return value["selected_study_id"]


def discover_registered_outcome_use(selection, *, lens, outcome_cutoff, site_policy, expected_use_identity=None):
    """Fixed source routing, never a customer study ID or a grant from config.

    None means only that routing is explicitly dormant. Configured but denied,
    missing or changed authority fails closed; callers may show unavailable.
    The returned sealed use/descriptor promises authorized metadata, not a
    visible numerical observation or scientific study admission.
    """
    study_id, routing = _routing_selector()
    if study_id is None:
        _require(expected_use_identity is None, "original_outcome_use_unavailable")
        return None
    cap = prepare_registered_outcome_use(study_id, selection, lens=lens, outcome_cutoff=outcome_cutoff,
        site_policy=site_policy, expected_use_identity=expected_use_identity)
    _pin_registered_observations(cap)
    _require(_routing_selector() == (study_id, routing), "original_outcome_routing_changed")
    return cap, disclose_registered_outcome_use(cap)
