"""Synthetic private controls/native owners, never actual study or site admission."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from engine.research_factory import market_memory_outcome_use as use
from engine.research_factory import market_memory_e0_installed_control as owner
from engine.research_factory import market_memory_contextual_registration as control
from engine.neuralweb import market_memory_episode_outcomes as outcomes
from engine.neuralweb import market_memory_contextual_observation_store as observations
from tests.test_market_memory_e0_installed_control import records, selection, retain, select, NOW, COMMIT
from tests.test_market_memory_e0_control_records import canonical, record_ref, bundle, task_bundle
from tests.test_market_memory_e0_registered_method import inputs
from tests.test_market_memory_episode_outcomes import corpus, published, DEFINITION, Policy


def domain(root, value, identity):
    body = canonical(value)
    digest = sha256(body).hexdigest()
    path = root / (digest + ".json")
    path.write_bytes(body)
    path.chmod(0o600)
    return {"schema": value["schema"], "object_id": value[identity], "sha256": digest, "bytes": len(body)}


@pytest.fixture
def selected_use(selection, records, inputs):
    root, selected = selection
    records["registration"] = json.loads(inputs["registration"])
    reg = records["registration"]
    for name, ref in (("method_manifest", reg["implementation"]["method_ref"]),
                      ("task_manifest", reg["tasks_ref"]), ("frozen_membership", reg["corpus"]["membership_ref"])):
        path = root / (ref["sha256"] + ".json")
        path.write_bytes(inputs[name])
        path.chmod(0o600)
    definition = DEFINITION.disclosure()
    dr = domain(root, definition, "definition_sha256")
    rules = {"schema": use._RULE, "rules_id": "synthetic-outcome-rules", "study_id": "synthetic-study",
        "purpose": use._PURPOSE, "definition_ref": dr,
        "source_authority": {"path": "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md", "sha256": "a" * 64},
        "technical_store_id": "mmactualstore_" + "a" * 64, "subject_id": "synthetic-subject",
        "scope_location": "current_selected_access.scope_ref", "economic_return": False,
        "corporate_action_adjusted": False, "RTH_close_authenticated": False}
    rules_ref = domain(root, rules, "rules_id")
    records["registration"]["access_rules_ref"] = rules_ref
    rr = record_ref(records["registration"], "study_id")
    records["closure"]["registration_ref"] = rr
    cr = record_ref(records["closure"], "closure_id")
    records["publication"].update(registration_ref=rr, closure_ref=cr)
    pr = record_ref(records["publication"], "publication_id")
    records["installation"].update(registration_ref=rr, closure_ref=cr, publication_ref=pr)
    records["installation"]["permitted_actions"].append("read_registered_outcome_labels")
    records["access"].update(registration_ref=rr, publication_ref=pr)
    binding = {"schema": use._BINDING, "binding_id": "synthetic-outcome-binding",
        "registration_ref": rr, "access_rules_ref": rules_ref,
        "installation_id": records["installation"]["installation_id"],
        "installation_epoch": records["installation"]["installation_epoch"],
        "observation_generation_ref": {"generation_id": "mmcontextualgeneration_" + "b" * 64,
            "sha256": "c" * 64, "bytes": 100},
        "observations": [{"context_id": "synthetic-context", "capture_id": "synthetic-capture",
            "packet_sha256": "a" * 64, "observation_id": None}],
        "permitted_actions": sorted(use._OUTCOME_ACTIONS)}
    records["access"]["scope_ref"] = domain(root, binding, "binding_id")
    for name, (_kind, identity) in owner._CONTROL_KEYS.items():
        selected["control_refs"][name] = retain(root, records[name], identity)
    select(root, selected)
    def load():
        return owner._load_selected_control(root, "synthetic-study",
            lambda commit: None if commit == COMMIT else pytest.fail("source drift"), clock=lambda: NOW,
            prepare=use._prepare)
    return root, selected, records, rules, binding, load


def test_real_private_roles_are_acyclic_exact_and_do_not_admit_a_study(selected_use):
    _, selected, records, rules, binding, load = selected_use
    context, body = load()
    assert context["rules"] == rules and context["binding"] == binding
    assert context["registration_sha256"] == sha256(canonical(records["registration"])).hexdigest()
    assert json.loads(body) == selected
    assert context["binding_ref"] == records["access"]["scope_ref"]
    assert context["rules_ref"] == records["registration"]["access_rules_ref"]
    assert "observation_generation_ref" not in rules  # No registration/observation hash cycle.


@pytest.mark.parametrize("defect", ["rules_missing", "binding_changed", "definition_missing", "wrong_epoch", "wrong_registration"])
def test_missing_changed_or_mismatched_original_roles_refuse(selected_use, defect):
    root, selected, records, rules, binding, load = selected_use
    if defect == "rules_missing": (root / (records["registration"]["access_rules_ref"]["sha256"] + ".json")).unlink()
    elif defect == "definition_missing": (root / (rules["definition_ref"]["sha256"] + ".json")).unlink()
    elif defect == "binding_changed":
        (root / (records["access"]["scope_ref"]["sha256"] + ".json")).write_bytes(b"{}")
    else:
        binding["installation_epoch" if defect == "wrong_epoch" else "registration_ref"] = (
            "another-epoch" if defect == "wrong_epoch" else rules["definition_ref"])
        records["access"]["scope_ref"] = domain(root, binding, "binding_id")
        selected["control_refs"]["access"] = retain(root, records["access"], "access_state_id")
        select(root, selected)
    with pytest.raises((use.OutcomeUseError, owner.E0InstalledControlError)):
        load()


def test_same_epoch_scope_rebinding_is_not_a_new_generation_permission(selected_use):
    root, selected, records, _, binding, load = selected_use
    prior = copy.deepcopy(records["access"])
    binding["observation_generation_ref"]["sha256"] = "d" * 64
    records["access"].update(sequence=1, previous_state_ref=record_ref(prior, "access_state_id"),
        recorded_at="2026-10-14T00:05:00.000000Z", scope_ref=domain(root, binding, "binding_id"))
    selected["control_refs"]["access"] = retain(root, records["access"], "access_state_id")
    select(root, selected)
    from engine.research_factory.market_memory_e0_access_history import E0AccessHistoryError
    with pytest.raises(E0AccessHistoryError): load()


def test_fixed_installed_owner_refuses_before_control_io(monkeypatch):
    if not (sys.platform == "linux" and use.os.geteuid() == 0
            and Path(use.__file__).resolve() == owner.INSTALLED_ROOT / use._MODULE):
        monkeypatch.setattr(owner, "_load_selected_control", lambda *a, **k: pytest.fail("control before installed identity"))
        with pytest.raises(use.OutcomeUseError, match="installed_outcome_owner_required"):
            use._load_context("synthetic-study")


@pytest.fixture
def native_use(selected_use, corpus, published, monkeypatch):
    """Explicit domain/source-owner qualification stand-in, not real registration.

    Frozen v1 registration is 109 real metadata identities; this three-capture
    native fixture cannot pretend to be that cohort. Real private role tests
    above and real native-source tests below prove separate source boundaries.
    """
    _, _, _, _, _, load = selected_use
    context, selected = load()
    original = use.retrieval.disclose_episode_retrieval(corpus[2], policy=Policy())
    query = original["query_owner"]
    context["registration"]["corpus"].update({k: query[k] for k in ("store_id", "generation_id", "generation_sha256")})
    context["rules"]["subject_id"] = query["subject_id"]
    context["rules"]["technical_store_id"] = corpus[1].store_id
    context["registration_sha256"] = "a" * 64  # Native synthetic publisher's registered selector.
    context["registration"]["registered_at"] = "2026-08-20T00:00:00.000000Z"
    context["binding"]["observation_generation_ref"] = published[0]
    manifest = json.loads(published[1]._body)
    context["binding"]["observations"] = [{**{k: entry["context_ref"][k]
        for k in ("context_id", "capture_id", "packet_sha256")}, "observation_id": entry["observation_id"]}
        for entry in manifest["entries"]]
    monkeypatch.setattr(use, "_load_context", lambda study: (copy.deepcopy(context), selected))
    monkeypatch.setattr(use, "_site_policy", lambda policy: policy if type(policy) is Policy else pytest.fail("site owner required"))
    monkeypatch.setattr(use, "_clock", lambda: NOW)
    monkeypatch.setattr(use.technical, "default_technical_actual_output_store_root", lambda _: corpus[0])
    def prepare(lens="later_observed", identity=None):
        return use.prepare_registered_outcome_use("synthetic-study", corpus[2], lens=lens,
            outcome_cutoff="2026-08-20T12:00:00Z" if lens == "then_known" else "2026-08-22T00:00:00Z",
            site_policy=Policy(), expected_use_identity=identity)
    return context, selected, prepare


def test_genuine_native_attachment_preserves_selection_and_exact_generation(native_use):
    context, _, prepare = native_use
    cap = prepare()
    attachment, policy = use.read_registered_outcome_attachment(cap)
    value = outcomes.disclose_contextual_outcomes(attachment, policy=policy)
    descriptor = use.disclose_registered_outcome_use(cap)
    assert descriptor["retrieval_id"] == value["retrieval_id"]
    assert descriptor["selection_sha256"] == value["selection_sha256"]
    assert descriptor["observation_generation_ref"] == context["binding"]["observation_generation_ref"]
    assert descriptor["operational_admission"] is False
    assert use.disclose_registered_outcome_use(prepare(identity=descriptor["outcome_use_identity"])) == descriptor
    with pytest.raises(use.OutcomeUseError, match="identity_changed"):
        prepare(identity="mmoutcomeuse_" + "0" * 64)


def test_then_known_opaque_use_identity_does_not_expose_generation(native_use):
    _, _, prepare = native_use
    cap = prepare("then_known")
    descriptor = use.disclose_registered_outcome_use(cap)
    assert descriptor["observation_generation_ref"] is None
    attachment, policy = use.read_registered_outcome_attachment(cap)
    value = outcomes.disclose_contextual_outcomes(attachment, policy=policy)
    assert value["observation_generation_ref"] is None
    assert all(row["value_q18"] is None for row in value["rows"])


def test_named_read_mark_right_cannot_be_replaced_by_metadata_or_site_access(native_use, monkeypatch):
    context, _, prepare = native_use
    context["binding"]["permitted_actions"].remove("read_retained_source_bar_marks")
    cap = prepare()
    original = use.technical._read_raw
    def tripwire(path, **kwargs):
        assert "observations" not in Path(path).parts, "numerical observation payload before named mark right"
        return original(path, **kwargs)
    monkeypatch.setattr(use.technical, "_read_raw", tripwire)
    with pytest.raises(use.OutcomeUseError, match="current_named_outcome_action_required"):
        use.read_registered_outcome_attachment(cap)


def test_cached_use_never_moves_to_a_different_current_scope(native_use):
    context, _, prepare = native_use
    cap = prepare()
    context["binding_ref"] = {**context["binding_ref"], "sha256": "e" * 64}
    with pytest.raises(use.OutcomeUseError, match="original_outcome_scope_changed"):
        use.disclose_registered_outcome_use(cap)


def test_no_dict_or_site_policy_alone_constructs_registered_outcome_authority():
    with pytest.raises(use.OutcomeUseError): use.RegisteredOutcomeUseCapability(b"{}", None, None, b"{}")
    with pytest.raises(use.OutcomeUseError): use.disclose_registered_outcome_use({})
    with pytest.raises(use.OutcomeUseError, match="existing_request_local_site_owner_required"):
        use._site_policy(Policy())


def test_shipped_selector_is_dormant_and_cannot_grant_a_study():
    body = (Path(__file__).resolve().parents[1] / use._SELECTOR).read_bytes()
    assert use._parse_selector(body) is None
    for bad in ({"schema": "market_memory.retained_outcome_selector.v2", "enabled": False, "selected_study_id": "invented"},
                {"schema": "market_memory.retained_outcome_selector.v2", "enabled": 1, "selected_study_id": "invented"},
                {"schema": "market_memory.retained_outcome_selector.v2", "enabled": True, "selected_study_id": None},
                {"schema": "market_memory.retained_outcome_selector.v2", "enabled": True, "selected_study_id": "study", "grant": True}):
        with pytest.raises(use.OutcomeUseError): use._parse_selector(canonical(bad))


def test_dormant_discovery_reads_no_study_and_cannot_reopen_an_old_reference(monkeypatch):
    monkeypatch.setattr(use, "_routing_selector", lambda: (None, b"dormant"))
    monkeypatch.setattr(use, "_load_context", lambda *a: pytest.fail("dormant private read"))
    assert use.discover_registered_outcome_use(None, lens="then_known", outcome_cutoff="bad", site_policy=None) is None
    with pytest.raises(use.OutcomeUseError, match="original_outcome_use_unavailable"):
        use.discover_registered_outcome_use(None, lens="then_known", outcome_cutoff="bad", site_policy=None,
            expected_use_identity="mmoutcomeuse_" + "a" * 64)


def test_enabled_discovery_authenticates_metadata_without_reading_a_label(native_use, corpus, monkeypatch):
    _, _, _prepare = native_use
    monkeypatch.setattr(use, "_routing_selector", lambda: ("synthetic-study", b"routing"))
    monkeypatch.setattr(observations, "_read_observation", lambda *a, **k: pytest.fail("label during discovery"))
    cap, descriptor = use.discover_registered_outcome_use(corpus[2], lens="later_observed",
        outcome_cutoff="2026-08-22T00:00:00Z", site_policy=Policy())
    assert descriptor == use.disclose_registered_outcome_use(cap)
    assert "study_id" not in descriptor and "binding_ref" not in descriptor


def test_then_known_policy_never_authorizes_future_mark_resources(native_use, published):
    _, _, prepare = native_use
    _, policy = use.read_registered_outcome_attachment(prepare("then_known"))
    entry = json.loads(published[1]._body)["entries"][0]
    with pytest.raises(use.OutcomeUseError, match="original_mark_purpose_resource_required"):
        policy.check("read_retained_source_bar_marks", entry["mark_use_resource"])


def test_metadata_permission_denial_precedes_generation_io(native_use, monkeypatch):
    context, _, prepare = native_use
    context["binding"]["permitted_actions"].remove("read_retained_contextual_observation_metadata")
    cap = prepare()
    monkeypatch.setattr(observations, "_published_chain", lambda *a: pytest.fail("generation before metadata permission"))
    with pytest.raises(use.OutcomeUseError, match="current_named_outcome_action_required"):
        use.read_registered_outcome_attachment(cap)


def test_original_comparison_revocation_precedes_outcome_io(native_use, monkeypatch):
    _, _, prepare = native_use
    cap = prepare()
    cap._site_policy.denied.add("compare_retained_macro_feature")
    monkeypatch.setattr(observations, "_published_chain", lambda *a: pytest.fail("outcome after whole-pool revoke"))
    with pytest.raises(Exception, match="source_usage_not_admitted"):
        use.read_registered_outcome_attachment(cap)


def test_read_owner_never_grants_a_publication_action(native_use):
    context, _, prepare = native_use
    cap = prepare()
    _, policy = use.read_registered_outcome_attachment(cap)
    with pytest.raises(use.OutcomeUseError, match="outcome_read_only_purpose"):
        policy.check("publish_retained_contextual_observations", {})


def test_registered_method_bytes_cannot_be_omitted(selected_use):
    root, _, records, _, _, load = selected_use
    (root / (records["registration"]["implementation"]["method_ref"]["sha256"] + ".json")).unlink()
    with pytest.raises(owner.E0InstalledControlError): load()


def test_genuine_comparison_with_different_registered_method_cannot_attach(native_use):
    context, _, prepare = native_use
    context["method_spec"]["purge_calendar_days"] = 1
    with pytest.raises(use.OutcomeUseError, match="exact_registered_outcome_method_required"):
        prepare()


def test_original_access_record_must_remain_in_real_current_history(native_use, monkeypatch):
    context, _, prepare = native_use
    cap = prepare()
    context["access_history_refs"] = []
    monkeypatch.setattr(observations, "_published_chain", lambda *a: pytest.fail("unrelated history reached source"))
    with pytest.raises(use.OutcomeUseError, match="original_outcome_access_not_in_current_history"):
        use.read_registered_outcome_attachment(cap)


def test_scope_change_refuses_original_public_back_reference(native_use):
    context, _, prepare = native_use
    descriptor = use.disclose_registered_outcome_use(prepare())
    context["binding_ref"] = {**context["binding_ref"], "sha256": "e" * 64}
    with pytest.raises(use.OutcomeUseError, match="original_outcome_use_identity_changed"):
        prepare(identity=descriptor["outcome_use_identity"])


def test_selector_change_during_metadata_advertisement_refuses(native_use, corpus, monkeypatch):
    iterator = iter([("synthetic-study", b"routing"), ("other-study", b"changed")])
    monkeypatch.setattr(use, "_routing_selector", lambda: next(iterator))
    with pytest.raises(use.OutcomeUseError, match="original_outcome_routing_changed"):
        use.discover_registered_outcome_use(corpus[2], lens="later_observed",
            outcome_cutoff="2026-08-22T00:00:00Z", site_policy=Policy())


def test_invalid_back_reference_refuses_before_private_owner_load(native_use, monkeypatch):
    _, _, prepare = native_use
    monkeypatch.setattr(use, "_load_context", lambda *a: pytest.fail("private read for malformed identity"))
    with pytest.raises(use.OutcomeUseError, match="bounded_original_outcome_use_identity_required"):
        prepare(identity={"latest": True})


def test_exact_house_type_cannot_substitute_a_different_source_root(tmp_path):
    from engine.neuralweb.market_memory_retained_use import RetainedHouseUsePolicy
    # A forged/uninitialized object is not a valid policy; this tripwire isolates
    # the additional fixed-origin guard before any current entitlement is used.
    policy = object.__new__(RetainedHouseUsePolicy)
    policy.root = tmp_path
    with pytest.raises(use.OutcomeUseError, match="installed_site_source_owner_required"):
        use._site_policy(policy)
