"""Native synthetic fitted-Factory custody; every deployment stand-in is named.

Positive tests exercise the real owner scopes, the static service gate, the
genuine COMPLETE store record and the original native query reproduction over
sealed native captures. The installed Linux/root environment guard is reduced
to its installed-root equality half and the Git source verifier is a named
synthetic stand-in; the real entries are refused on their true surface by
``test_owner_entry_refuses_uninstalled_deployment``. The native control
directory supplied by the owner's own context is used directly; nothing is
copied and no control record is modified except in explicitly named negative
tests. No production source, label, fit execution or live write.
"""
import copy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from engine.neuralweb import market_memory
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_forward as forward
from engine.neuralweb import market_memory_fitted_normalization as fitted
from engine.neuralweb import market_memory_fitted_retrieval as fitted_retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as house
from engine.research_factory import market_memory_fitted_factory_use as ffi
from engine.research_factory import market_memory_e0_installed_control as owner
from engine.research_factory import market_memory_fitted_persistence as persistence
from engine.research_factory import market_memory_fitted_use as use
from engine.research_factory.market_memory_e0_reservations import ReservationError
from engine.research_factory.market_memory_contextual_registration import E0ControlError
from engine.research_factory.market_memory_e0_access_history import E0AccessHistoryError
from tests.test_market_memory_e0_control_records import canonical, record_ref, records
from tests.test_market_memory_e0_installed_control import (
    COMMIT, retain, select, selection, write,
)
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_fitted_normalization import native_training
from tests.test_market_memory_fitted_persistence import retained_owner
from tests.test_market_memory_retained_context_cohort import (
    capture, load, owner as native_owner,
)

REPO = Path(__file__).resolve().parents[1]
LOCATOR_KEYS = ("operation_id", "intent", "sha256", "bytes")
USER = "factory-fixture"


def _training_spec(mode="historical_hypothetical"):
    # load_registration pins the installed method to 5 calendar days; the
    # synthetic training window must carry that same native eligibility spec.
    spec = persistence.retrieval.baseline.RetainedContextMethodSpec(
        5, 5, mode).disclosure()
    assert spec["purge_calendar_days"] == spec["embargo_calendar_days"] == 5
    return spec


def _binding_ref(binding):
    body = cohort.canonical(binding)
    return {"schema": use.SCHEMA, "object_id": binding["binding_id"],
            "sha256": sha256(body).hexdigest(), "bytes": len(body)}


def _synthetic_trial():
    """Explicit synthetic W2A preregistration, not an exported study claim."""
    return forward.canonical_json_bytes(forward.build_trial_registration(
        trial_key="synthetic.fitted.factory.v1",
        registered_at="2026-08-01T12:00:00.000000Z",
        state_requirements={
            "state_schema": forward.STATE_SNAPSHOT_SCHEMA,
            "context_schema": market_memory.AS_KNOWN_AT_SCHEMA,
            "minimum_observed_domains": 2,
            "required_observed_domains": list(forward.CANONICAL_DOMAINS[:2]),
        },
        target={
            "target_id": "spy.close.return",
            "formula": "outcome_close / input_close - 1",
            "formula_version": "synthetic.v1",
            "value_type": "number",
            "unit": "ratio",
            "categories": [],
        },
        marks={
            "input_mark": "close",
            "outcome_mark": "close",
            "cost_convention": "none",
            "benchmark": "zero_return",
        },
        horizon={
            "anchor": "decision_cutoff",
            "start_offset_seconds": 86_400,
            "end_offset_seconds": 172_800,
            "evaluation_offset_seconds": 172_800,
        },
        distribution={"kind": "scalar", "quantile_levels": [], "categories": []},
        proper_score={"name": "squared_error", "orientation": "lower_is_better"},
        baselines=[{"baseline_id": "zero_return", "baseline_version": "synthetic.v1",
                    "config_sha256": "4" * 64}],
        splits={
            "development_start": "2020-01-01T00:00:00.000000Z",
            "development_end": "2022-01-01T00:00:00.000000Z",
            "test_start": "2022-01-01T00:00:00.000000Z",
            "test_end": "2024-01-01T00:00:00.000000Z",
            "live_forward_start": "2026-08-02T00:00:00.000000Z",
        },
        purge={"enabled": True, "before_seconds": 172_800, "after_seconds": 0},
        embargo={"enabled": True, "duration_seconds": 172_800},
        dependence={
            "keys": ["context_id", "subject_id"],
            "clustering": "effective_event_cluster",
            "cluster_version": "synthetic.v1",
        },
        trial_budget={
            "max_trials": 10,
            "max_variants": 2,
            "family_trials_already_registered": 0,
        },
        abstention={
            "required": True,
            "minimum_observed_domains": 2,
            "allowed_reasons": ["insufficient_domains", "policy_expired",
                                "required_domain_missing"],
        },
        expiry={"expires_at": "2027-01-01T00:00:00.000000Z", "action": "abstain"},
        demotion={"enabled": True,
                  "triggers": ["baseline_underperformance", "broken_lineage",
                               "calibration_decay"]},
        implementation={
            "model_sha256": "5" * 64,
            "code_sha256": "6" * 64,
            "config_sha256": "7" * 64,
        },
    ))


def _service_entry(world):
    trial, spec = world["trial"], world["spec"]
    digest = sha256(world["trial_body"]).hexdigest()
    return {"schema": ffi.SERVICE_SCHEMA, "consumer": ffi.CONSUMER, "enabled": True,
            "purpose": ffi.PURPOSE,
            "trial_registration_id": trial["trial_registration_id"],
            "trial_registration_sha256": digest,
            "trial_record": f"research/market_memory/trials/{digest}.json",
            "candidate_created_at": trial["registered_at"],
            "binding_ref": world["binding_ref"],
            "eligibility_method_spec": {key: spec[key] for key in
                ("method_spec_id", "purge_calendar_days", "embargo_calendar_days", "mode")},
            "normalization_method": use.METHOD, "limit": 8}


def _install_service(world, service=None):
    registration = json.loads(world["registration_path"].read_bytes())
    registration["service_consumers"] = {ffi.CONSUMER: service or world["service"]}
    body = canonical(registration)
    world["registration_path"].write_bytes(body)
    world["registration_bytes"] = body


def _locator(result):
    return {key: copy.deepcopy(result[key]) for key in LOCATOR_KEYS}


def _compact(operation_id, intent, sha256_hex, size):
    return {"operation_id": operation_id, "intent": intent,
            "sha256": sha256_hex, "bytes": size}


@pytest.fixture
def fitted_world(retained_owner, records, tmp_path, monkeypatch, native_training,
                 selection):
    """Real synthetic custody plus named test-only installed-owner stand-ins."""
    root, selected, template, context, now, subject = retained_owner
    template["eligibility_method_spec"] = _training_spec(template["binding"]["mode"])
    # The synthetic window binding stands in for the genuine v2 fitted binding.
    template["binding"].update(purpose=use.PURPOSE,
                               normalization_method=use.METHOD)
    monkeypatch.setattr(ffi.owner, "INSTALLED_ROOT", root)

    def owner_environment():
        ffi._installed_owner_root(ffi.owner.INSTALLED_ROOT)

    monkeypatch.setattr(ffi, "_owner_environment", owner_environment)

    def synthetic_source(_root, commit, *, paths):
        assert commit == COMMIT and set(paths) == set(ffi._SOURCE_PATHS)

    monkeypatch.setattr(ffi.owner, "_verify_source", synthetic_source)
    (root / "config").mkdir(mode=0o700, exist_ok=True)
    trials = root / "research" / "market_memory" / "trials"
    trials.mkdir(parents=True, mode=0o700, exist_ok=True)
    trial_body = _synthetic_trial()
    write(trials / (sha256(trial_body).hexdigest() + ".json"), trial_body)
    for relative in (house.REGISTRATION, house.AUTHORITY_RECORD, use.PURPOSE_PATH,
                     use.BASELINE_PURPOSE_PATH):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes((REPO / relative).read_bytes())
        target.chmod(0o600)
    registration_path = root / house.REGISTRATION
    registration = json.loads(registration_path.read_bytes())
    source = template["binding"]["source_owner"]
    registration["store_id"] = source["store_id"]
    registration["allowed_subject_ids"] = [subject]
    registration_path.write_bytes(canonical(registration))
    purpose_path = root / use.PURPOSE_PATH
    purpose = json.loads(purpose_path.read_bytes())
    purpose.update(enabled=True, selected_study_id="synthetic-study",
                   store_id=source["store_id"], allowed_subject_ids=[subject],
                   binding_ref=_binding_ref(template["binding"]))
    purpose_path.write_bytes(canonical(purpose))
    world = {"root": root, "template": template, "context": context, "now": now,
             "subject": subject, "binding_ref": _binding_ref(template["binding"]),
             "registration_path": registration_path, "purpose_path": purpose_path,
             "trial_body": trial_body,
             "trial": json.loads(trial_body), "spec": template["eligibility_method_spec"]}
    world["service"] = _service_entry(world)
    _install_service(world)
    world["purpose_bytes"] = purpose_path.read_bytes()
    monkeypatch.setattr(house, "_enforce_current_site_user",
                        lambda user: None if user == USER else
                        (_ for _ in ()).throw(house.RetainedUseError("fixture_site_denied")))
    return world


def _house_policy(world, generation_id, generation_sha256, query_cutoff):
    """Real exact-generation House scope; only the site login is a fixture."""
    return house.RetainedHouseUsePolicy(
        world["root"], user_id=USER, subject_id=world["subject"],
        store_id=world["template"]["binding"]["source_owner"]["store_id"],
        generation_id=generation_id, generation_sha256=generation_sha256,
        query_cutoff=query_cutoff,
        mode=world["template"]["binding"]["mode"])


@pytest.fixture
def completed_world(fitted_world, tmp_path, monkeypatch):
    """Full genuine custody: COMPLETE fit, one later native query and policy.

    The static service definition is installed BEFORE the setup fit and query
    and its registration/purpose bytes stay identical through the COMPLETE
    query; the setup bodies all use the same stable House source policy_id.
    """
    world = fitted_world
    source = world["template"]["binding"]["source_owner"]
    world["retained"] = persistence.persist_registered_fit(policy=_house_policy(
        world, source["generation_id"], source["generation_sha256"],
        world["template"]["binding"]["fit_cutoff"]))
    later = capture(tmp_path, monkeypatch, session="2026-10-14", growth=0.7)
    world["now"][0] = "2026-10-14T11:00:00.000000Z"
    reader, pin = native_owner(tmp_path)
    # The whole query body (index/result provenance digests) is computed under
    # one stable House source policy_id, so the later reopen reproduces it.
    query_policy = _house_policy(world, pin.generation_id, pin.generation_sha256,
                                 world["now"][0])
    population = load(reader, pin, later, cutoff=world["now"][0], policy=query_policy)
    query = features.read_episode_feature_capability(
        reader, pin, query_id=later.capture_receipt["query_id"],
        subject_id=world["subject"], query_cutoff=world["now"][0],
        policy=query_policy)
    world["result"] = persistence.retain_registered_fitted_query(
        world["retained"], population, query, policy=query_policy, k=2)
    assert world["result"]["value"]["result"]["denominator"]["accounted_captures"] == 4
    world["locator"] = _locator(world["result"])
    assert world["registration_bytes"] == world["registration_path"].read_bytes()
    assert world["purpose_bytes"] == world["purpose_path"].read_bytes()
    world["policy"] = ffi.FittedFactoryUsePolicy(reference=dict(world["locator"]))
    return world


def store_state(world):
    store = persistence._store(world["context"]())
    return store.snapshot(), {p.name: sha256(p.read_bytes()).hexdigest()
                              for p in store.directory.iterdir()}


def _forbid_query_io(monkeypatch):
    monkeypatch.setattr(persistence.ReservationStore, "read_completed",
                        lambda *a: pytest.fail("payload before qualification"))
    monkeypatch.setattr(cohort, "read_retained_context_cohort",
                        lambda *a, **k: pytest.fail("projection before qualification"))
    monkeypatch.setattr(features, "read_episode_feature_capability",
                        lambda *a, **k: pytest.fail("feature before qualification"))


def test_owner_entry_refuses_uninstalled_deployment():
    installed = (ffi.sys.platform == "linux" and ffi.os.geteuid() == 0
                 and Path(ffi.__file__).resolve()
                 == owner.INSTALLED_ROOT / ffi._MODULE_PATH)
    if installed:
        pytest.skip("real installed owner surface")
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="installed_fitted_factory_owner_required"):
        ffi._owner_environment()
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="installed_fitted_factory_owner_required"):
        ffi._installed_owner_root(Path("/elsewhere"))


def test_shipped_config_has_no_fitted_service_and_refuses_before_private_io(
        fitted_world, monkeypatch):
    shipped = json.loads((REPO / house.REGISTRATION).read_bytes())
    assert set(shipped["service_consumers"]) == {house.FACTORY_CONSUMER}
    shipped_purpose = json.loads((REPO / use.PURPOSE_PATH).read_bytes())
    assert shipped_purpose["enabled"] is False
    assert shipped_purpose["selected_study_id"] is None
    assert ffi._MODULE_PATH in ffi._SOURCE_PATHS
    assert ffi._SCHEMA_PATH in ffi._SOURCE_PATHS
    world = fitted_world
    registration = json.loads(world["registration_path"].read_bytes())
    registration.pop("service_consumers", None)
    world["registration_path"].write_bytes(canonical(registration))
    monkeypatch.setattr(owner, "_directory",
                        lambda *a, **k: pytest.fail("private IO before fitted service"))
    monkeypatch.setattr(persistence, "_load_context",
                        lambda *a, **k: pytest.fail("context before fitted service"))
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="current_fitted_factory_service_required"):
        ffi.FittedFactoryUsePolicy(
            reference=_compact("query_" + "0" * 64, {}, "0" * 64, 1))


@pytest.mark.parametrize("change", ["disabled", "wrong_purpose", "bad_limit",
                                    "extra_field", "wrong_binding_schema",
                                    "wrong_trial_record", "bad_created_at"])
def test_mutated_static_service_refuses_before_private_io(fitted_world, monkeypatch,
                                                          change):
    world = fitted_world
    service = dict(world["service"])
    if change == "disabled":
        service["enabled"] = False
    elif change == "wrong_purpose":
        service["purpose"] = "contextual_cited_evidence"
    elif change == "bad_limit":
        service["limit"] = 9
    elif change == "extra_field":
        service["fitted_binding_ref"] = {}
    elif change == "wrong_binding_schema":
        service["binding_ref"] = {**world["binding_ref"],
                                  "schema": "market_memory.factory_contextual_binding.v1"}
    elif change == "wrong_trial_record":
        service["trial_record"] = "research/market_memory/trials/other.json"
    else:
        service["candidate_created_at"] = "2026-08-01T12:00:00Z"
    _install_service(world, service)
    monkeypatch.setattr(persistence, "_load_context",
                        lambda *a, **k: pytest.fail("context before fitted service"))
    expected = ("exact_fitted_training_binding_required" if change == "wrong_binding_schema"
                else "current_fitted_factory_service_required")
    with pytest.raises(ffi.FittedFactoryUseError, match=expected):
        ffi.FittedFactoryUsePolicy(
            reference=_compact("query_" + "0" * 64, {}, "0" * 64, 1))


@pytest.mark.parametrize("change", ["trial_bytes", "trial_id", "early_candidate",
                                    "disabled_purpose", "changed_binding"])
def test_trial_and_binding_gates_refuse_before_query_io(fitted_world, monkeypatch,
                                                        change):
    world = fitted_world
    if change == "trial_bytes":
        write(world["root"] / world["service"]["trial_record"],
              world["trial_body"][:-1] + b" ")
        monkeypatch.setattr(persistence, "_load_context",
                            lambda *a, **k: pytest.fail("query io before trial gate"))
    elif change == "trial_id":
        _install_service(world, {**world["service"],
                                 "trial_registration_id": "mmtrial_" + "f" * 64})
        monkeypatch.setattr(persistence, "_load_context",
                            lambda *a, **k: pytest.fail("query io before trial gate"))
    elif change == "early_candidate":
        _install_service(world, {**world["service"],
                                 "candidate_created_at": "2026-08-01T11:59:59.000000Z"})
        monkeypatch.setattr(persistence, "_load_context",
                            lambda *a, **k: pytest.fail("query io before trial gate"))
    elif change == "disabled_purpose":
        purpose_path = world["purpose_path"]
        purpose = json.loads(purpose_path.read_bytes())
        purpose.update(enabled=False, selected_study_id=None, binding_ref=None)
        purpose_path.write_bytes(canonical(purpose))

        def purpose_first(*_a, **_k):
            # The real owner entry checks the public purpose before private IO.
            use._purpose(world["root"])
            pytest.fail("context before purpose admission")

        monkeypatch.setattr(persistence, "_load_context", purpose_first)
    else:
        _install_service(world, {**world["service"],
                                 "binding_ref": {**world["binding_ref"],
                                                 "sha256": "f" * 64}})
    with pytest.raises((ffi.FittedFactoryUseError, use.FittedUseError, ValueError,
                        persistence.PersistedFitError,
                        owner.E0InstalledControlError)):
        ffi.FittedFactoryUsePolicy(
            reference=_compact("query_" + "0" * 64, {}, "0" * 64, 1))


def test_no_dependency_on_the_old_contextual_factory_binding(completed_world,
                                                             monkeypatch):
    world = completed_world
    monkeypatch.setattr(house, "_factory_binding",
                        lambda *a, **k: pytest.fail("old contextual binding read"))
    policy = ffi.FittedFactoryUsePolicy(reference=dict(world["locator"]))
    assert not (world["root"] / house.FACTORY_BINDINGS).exists()
    assert policy.disclose_binding()["service"] == world["service"]


def test_source_definition_and_config_bytes_unchanged_across_reopen(completed_world):
    world = completed_world
    policy = world["policy"]
    policy.disclose_binding()
    policy.disclosure()
    policy.reopen_registered_fitted_query()
    assert world["registration_bytes"] == world["registration_path"].read_bytes()
    assert world["purpose_bytes"] == world["purpose_path"].read_bytes()
    assert (REPO / house.REGISTRATION).read_bytes() != world["registration_bytes"]


def test_registered_policy_disclosure_binding_and_native_reopen(completed_world,
                                                                monkeypatch):
    world = completed_world
    policy = world["policy"]
    before = store_state(world)
    for name in ("initialize", "reserve", "finish"):
        monkeypatch.setattr(persistence.ReservationStore, name,
                            lambda *a, **k: pytest.fail(name + " during fitted use"))
    monkeypatch.setattr(fitted, "fit_registered_normalizer",
                        lambda *a, **k: pytest.fail("refit during fitted use"))
    monkeypatch.setattr(fitted, "_construction_clock",
                        lambda: pytest.fail("new construction clock during fitted use"))
    binding = policy.disclose_binding()
    assert binding["binding"]["binding_id"] == "synthetic-owner-window"
    assert binding["eligibility_method_spec"] == world["spec"]
    assert binding["service"] == world["service"]
    assert binding["trial"]["trial_registration_id"] == \
        world["trial"]["trial_registration_id"]
    assert binding["trial"]["bytes"] == len(world["trial_body"])
    assert binding["trial_original_query_provenance"] == "not_established"
    assert binding["candidate"]["candidate_id"].startswith("rf-market-memory-")
    assert binding["candidate"]["status"] == "proposed"
    assert binding["candidate"]["authority"] == "display_only"
    assert binding["claims"]["operational_study_admission"] is False
    assert binding["claims"]["factory_count_or_transition_action"] is False
    assert binding["query_scope"]["generation_id"] != \
        binding["training_scope"]["generation_id"]
    assert binding["query_scope"]["query_cutoff"] > \
        binding["training_scope"]["query_cutoff"]
    disclosure = policy.disclosure()
    assert disclosure["status"] == "ADMITTED_FOR_NAMED_PURPOSES"
    assert disclosure["claims"]["efficacy_claim"] is False
    assert policy.check("read_retained_generation_metadata",
                        dict(policy._training_bound)) is None
    reproduced, combined = policy.reopen_registered_fitted_query()
    assert combined is policy
    assert type(reproduced) is fitted_retrieval.FittedRetrievalCapability
    value = fitted_retrieval.disclose_fitted_retrieval(reproduced, policy=policy)
    assert value == world["result"]["value"]["result"]
    assert value["method"]["eligibility_method_spec"] == world["spec"]
    assert value["method"]["eligibility_method_spec"]["method_spec_id"].startswith(
        "mmretainedmethod_")
    assert value["method"]["method_id"].startswith("mmfittedmethod_")
    assert value["audit"]["cohort_id"].startswith("mmretainedcohort_")
    assert value["requested_k"] == 2
    assert store_state(world) == before
    snapshot, _files = before
    assert snapshot["consumed_looks"] == 2


def test_module_reopen_entry_matches_policy_reopen(completed_world):
    world = completed_world
    reproduced, combined = ffi.reopen_registered_fitted_query(dict(world["locator"]))
    assert combined.policy_id == world["policy"].policy_id
    value = fitted_retrieval.disclose_fitted_retrieval(reproduced, policy=combined)
    assert value == world["result"]["value"]["result"]


def test_both_exact_scopes_only(completed_world):
    policy = completed_world["policy"]
    training, query = policy._training_bound, policy._query_bound
    assert policy.check("read_retained_generation_metadata", dict(training)) is None
    assert policy.check("read_retained_generation_metadata", dict(query)) is None
    third = {**query, "generation_id": "mmgeneration_" + "e" * 64}
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="only_original_training_or_exact_query_scope_allowed"):
        policy.check("read_retained_generation_metadata", third)
    truncated = {k: v for k, v in query.items() if k != "generation_sha256"}
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="only_original_training_or_exact_query_scope_allowed"):
        policy.check("read_retained_generation_metadata", truncated)
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="named_fitted_house_use_required"):
        policy.check("invented_action", dict(query))


@pytest.mark.parametrize("change", ["invented_operation", "wrong_sha", "wrong_bytes",
                                    "pending", "absent_operation", "k_over_limit",
                                    "method_changed", "same_generation"])
def test_hostile_locators_reject_before_query_projections(completed_world, monkeypatch,
                                                          change):
    world = completed_world
    locator = dict(world["locator"])
    if change == "invented_operation":
        locator["operation_id"] = "query_" + "0" * 64
    elif change == "wrong_sha":
        locator["sha256"] = "d" * 64
    elif change == "wrong_bytes":
        locator["bytes"] = 4096
    elif change == "pending":
        intent = {**locator["intent"], "query_cutoff": "2026-10-14T13:00:00.000000Z"}
        locator = _compact("query_" + sha256(cohort.canonical(intent)).hexdigest(),
                           intent, locator["sha256"], locator["bytes"])
        persistence._store(world["context"]()).reserve(locator["operation_id"], intent)
    elif change in ("absent_operation", "k_over_limit", "method_changed",
                    "same_generation"):
        intent = dict(locator["intent"])
        if change == "k_over_limit":
            intent["k"] = 9
        elif change == "method_changed":
            intent["method_spec_id"] = "mmretainedmethod_" + "f" * 64
        elif change == "same_generation":
            intent["generation_id"] = \
                world["template"]["binding"]["source_owner"]["generation_id"]
        else:
            intent["query_cutoff"] = "2026-10-14T13:00:00.000000Z"
        locator = _compact("query_" + sha256(cohort.canonical(intent)).hexdigest(),
                           intent, world["locator"]["sha256"], world["locator"]["bytes"])
    _forbid_query_io(monkeypatch)
    before = store_state(world)
    with pytest.raises((ffi.FittedFactoryUseError, ReservationError)):
        ffi.FittedFactoryUsePolicy(reference=locator)
    if change == "pending":
        snapshot, files = store_state(world)
        assert snapshot["reserved_looks"] == 1
        assert files == before[1]
    else:
        assert store_state(world) == before


def test_source_closure_proof_order_and_additive_change_stops_before_store(
        completed_world, monkeypatch):
    world = completed_world
    order = []
    real_context = persistence._load_context
    real_verify = ffi.owner._verify_source
    real_locked = persistence.ReservationStore._locked

    def spy_context(*arguments, **keywords):
        order.append("context")
        return real_context(*arguments, **keywords)

    def spy_verify(_root, commit, *, paths):
        order.append("verify")
        assert commit == COMMIT
        assert {ffi._MODULE_PATH, ffi._SCHEMA_PATH} <= set(paths)
        return real_verify(_root, commit, paths=paths)

    def spy_locked(store):
        order.append("store")
        return real_locked(store)

    monkeypatch.setattr(persistence, "_load_context", spy_context)
    monkeypatch.setattr(ffi.owner, "_verify_source", spy_verify)
    monkeypatch.setattr(persistence.ReservationStore, "_locked", spy_locked)
    ffi.FittedFactoryUsePolicy(reference=dict(world["locator"]))
    assert order == ["context", "verify", "store", "context", "verify", "store"]

    def changed_additive_source(_root, _commit, *, paths):
        assert {ffi._MODULE_PATH, ffi._SCHEMA_PATH} <= set(paths)
        raise owner.E0InstalledControlError("installed_source_changed")

    with monkeypatch.context() as patch:
        patch.setattr(persistence, "_load_context", real_context)
        patch.setattr(ffi.owner, "_verify_source", changed_additive_source)
        patch.setattr(persistence.ReservationStore, "_locked",
                      lambda store: pytest.fail("store before additive source proof"))
        with pytest.raises(owner.E0InstalledControlError,
                           match="installed_source_changed"):
            ffi.FittedFactoryUsePolicy(reference=dict(world["locator"]))


@pytest.mark.parametrize("change", ["revoked", "contaminated", "expired", "broken"])
def test_current_control_changes_refuse_before_payload(completed_world, monkeypatch,
                                                       records, change):
    world = completed_world
    root = world["root"]
    _forbid_query_io(monkeypatch)
    selected_ref = json.loads((root / "SELECTED.json").read_bytes())
    if change in ("revoked", "contaminated"):
        prior = records["access"]
        current = copy.deepcopy(prior)
        current.update(sequence=1,
                       previous_state_ref=record_ref(prior, "access_state_id"),
                       recorded_at="2026-10-14T11:05:00.000000Z")
        if change == "revoked":
            current["status"] = "revoked"
        else:
            current["contamination_state"] = "contaminated"
        selected_ref["control_refs"]["access"] = retain(root, current, "access_state_id")
        select(root, selected_ref)
    elif change == "expired":
        world["now"][0] = "2026-10-16T00:00:00.000000Z"
    else:
        (root / (selected_ref["control_refs"]["registration"]["sha256"]
                 + ".json")).unlink()
    refusals = (ffi.FittedFactoryUseError, persistence.PersistedFitError,
                owner.E0InstalledControlError, E0ControlError, E0AccessHistoryError)
    with pytest.raises(refusals):
        world["policy"].check("read_retained_generation_metadata",
                              dict(world["policy"]._training_bound))
    with pytest.raises(refusals):
        world["policy"].reopen_registered_fitted_query()


def test_store_binding_and_budget_mismatch_refuses(completed_world, monkeypatch):
    world = completed_world
    locator = dict(world["locator"])
    foreign = {**world["context"]().binding, "installation_id": "foreign-installation"}
    with monkeypatch.context() as patch:
        patch.setattr(persistence, "_store",
                      lambda context: persistence.ReservationStore(
                          context.directory / "reservations", foreign))
        with pytest.raises(ReservationError):
            ffi.FittedFactoryUsePolicy(reference=locator)
    real_load = persistence.ReservationStore._load

    def inflated(store, fd):
        state = real_load(store, fd)
        state["maximum_looks"] = state["maximum_looks"] + 1
        return state

    with monkeypatch.context() as patch:
        patch.setattr(persistence.ReservationStore, "_load", inflated)
        with pytest.raises(ffi.FittedFactoryUseError,
                           match="retained_fit_accounting_budget_changed"):
            ffi.FittedFactoryUsePolicy(reference=locator)


def test_reopen_rechecks_current_gates(completed_world):
    world = completed_world
    policy = world["policy"]
    registration = json.loads(world["registration_path"].read_bytes())
    registration["service_consumers"] = {ffi.CONSUMER: {**world["service"], "limit": 3}}
    world["registration_path"].write_bytes(canonical(registration))
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="fitted_factory_service_changed"):
        policy.reopen_registered_fitted_query()
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="fitted_factory_service_changed"):
        policy.disclosure()
    world["registration_path"].write_bytes(world["registration_bytes"])
    trial_path = world["root"] / world["service"]["trial_record"]
    trial_bytes = trial_path.read_bytes()
    write(trial_path, trial_bytes[:-1] + b" ")
    with pytest.raises(ffi.FittedFactoryUseError, match="trial_registration_changed"):
        policy.reopen_registered_fitted_query()
    write(trial_path, trial_bytes)
    purpose_path = world["purpose_path"]
    purpose = json.loads(purpose_path.read_bytes())
    purpose["binding_ref"] = {**world["binding_ref"], "sha256": "f" * 64}
    purpose_path.write_bytes(canonical(purpose))
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="fitted_training_binding_changed"):
        policy.reopen_registered_fitted_query()
    purpose_path.write_bytes(world["purpose_bytes"])
    policy.reopen_registered_fitted_query()


def test_transport_only_value_and_hostile_values_cannot_change_authority(
        completed_world, monkeypatch):
    world = completed_world
    policy = world["policy"]
    real = persistence.reproduce_registered_fitted_query
    seen = []

    def spy(reference, *, policy):
        assert set(reference) == {"operation_id", "intent", "sha256", "bytes", "value"}
        seen.append(reference["value"])
        return real(reference, policy=policy)

    with monkeypatch.context() as patch:
        patch.setattr(persistence, "reproduce_registered_fitted_query", spy)
        reproduced, combined = ffi.reopen_registered_fitted_query(
            dict(world["locator"]))
    assert combined is not None and seen == [None]
    value = fitted_retrieval.disclose_fitted_retrieval(reproduced, policy=combined)
    assert value == world["result"]["value"]["result"]
    for hostile in ({"native_capability": True}, "returncode", 1, {"policy": "root"}):
        reproduced, _combined = persistence.reproduce_registered_fitted_query(
            {**world["locator"], "value": hostile}, policy=policy)
        assert fitted_retrieval.disclose_fitted_retrieval(
            reproduced, policy=policy) == world["result"]["value"]["result"]
    with pytest.raises((persistence.PersistedFitError, ReservationError)):
        persistence.reproduce_registered_fitted_query(
            {**world["locator"], "sha256": "d" * 64, "value": {"native_capability": True}},
            policy=policy)


def test_fake_capability_dict_subclass_scope_and_policy_reject(completed_world,
                                                               monkeypatch):
    policy = completed_world["policy"]
    with pytest.raises(fitted_retrieval.FittedRetrievalError):
        fitted_retrieval.FittedRetrievalCapability(b"{}", None, None)
    with pytest.raises(fitted_retrieval.FittedRetrievalError):
        fitted_retrieval.disclose_fitted_retrieval({}, policy=Policy())
    subclass = type("Subpolicy", (ffi.FittedFactoryUsePolicy,), {})
    with pytest.raises(ffi.FittedFactoryUseError,
                       match="fitted_factory_policy_required"):
        subclass(reference=dict(completed_world["locator"]))
    fake = type("FakeScope", (ffi._FittedFactoryScope,), {})
    instance = fake.__new__(fake)
    instance._owner = policy
    instance.root = policy.root
    original = policy._training_scope
    policy._training_scope = instance
    try:
        with pytest.raises(ffi.FittedFactoryUseError,
                           match="fitted_factory_scope_changed"):
            policy.check("read_retained_generation_metadata",
                         dict(policy._training_bound))
    finally:
        policy._training_scope = original
    with monkeypatch.context() as patch:
        patch.setattr(persistence, "reproduce_registered_fitted_query",
                      lambda reference, *, policy: (None, Policy()))
        with pytest.raises(ffi.FittedFactoryUseError,
                           match="owner_native_query_required"):
            policy.reopen_registered_fitted_query()


def test_changes_during_disclosure_and_capture_revocation_refuse(completed_world,
                                                                 monkeypatch):
    world = completed_world
    policy = world["policy"]
    real_check = house.RetainedHouseUsePolicy.check

    def revoking(self, action, resource):
        real_check(self, action, resource)
        raise house.RetainedUseError("fixture_current_source_revoked")

    with monkeypatch.context() as patch:
        patch.setattr(house.RetainedHouseUsePolicy, "check", revoking)
        refusal = (house.RetainedUseError, cohort.RetainedContextAccessError,
                   features.EpisodeFeatureAccessError)
        with pytest.raises(refusal):
            policy.check("read_retained_generation_metadata",
                         dict(policy._query_bound))
        with pytest.raises(refusal):
            policy.disclosure()
        with pytest.raises(refusal):
            policy.reopen_registered_fitted_query()
    registration = json.loads(world["registration_path"].read_bytes())
    registration["revoked_capture_ids"] = ["mmcapture_" + "e" * 64]
    world["registration_path"].write_bytes(canonical(registration))
    with pytest.raises((ffi.FittedFactoryUseError, house.RetainedUseError,
                        cohort.RetainedContextAccessError)):
        policy.disclosure()


def test_shipped_surface_and_claims_stay_inert(completed_world):
    world = completed_world
    shipped = json.loads((REPO / house.REGISTRATION).read_bytes())
    assert ffi.CONSUMER not in shipped["service_consumers"]
    shipped_purpose = json.loads((REPO / use.PURPOSE_PATH).read_bytes())
    assert shipped_purpose["enabled"] is False
    assert shipped_purpose["promotion_eligible"] is False
    binding = world["policy"].disclose_binding()
    claims = binding["claims"]
    assert all(claims[key] is False for key in
               ("operational_study_admission", "efficacy_claim", "fit_eligible",
                "training_eligible", "promotion_eligible",
                "factory_count_or_transition_action",
                "historical_fit_or_index_existence_authenticated"))
    assert binding["candidate"]["trial_accounting"]["mode"] == "read_only"
    assert binding["candidate"]["evaluation_plan"]["status"] == "not_run"
    assert all(flag in binding["candidate"]["flags"] for flag in
               ("market_memory_context_only", "w4_episodic_retrieval_join_deferred",
                "w5_operating_cortex_join_deferred"))
    assert binding["candidate"]["authority"] == "display_only"


def test_cached_policy_rechecks_complete_custody_on_every_public_entry(completed_world):
    world = completed_world
    policy = world["policy"]
    store = persistence._store(world["context"]())
    path = store.directory / store._result_name(world["locator"]["operation_id"])
    original = path.read_bytes()
    path.write_bytes(original[:-1])  # Actual synthetic custody corruption.
    try:
        for invoke in (lambda: policy.check("read_retained_generation_metadata", dict(policy._query_bound)),
                       policy.disclosure, policy.disclose_binding, policy.reopen_registered_fitted_query):
            with pytest.raises(ReservationError, match="result_size_mismatch"):
                invoke()
    finally:
        path.write_bytes(original)


def test_scope_fields_cannot_rebind_an_owned_policy_to_a_third_generation(completed_world):
    policy = completed_world["policy"]
    old_bound, old_expected = dict(policy._query_bound), dict(policy._query_scope.expected)
    forged = {**old_bound, "generation_id": "mmgeneration_" + "e" * 64}
    policy._query_bound = forged
    policy._query_scope.expected = {k: v for k, v in forged.items() if k != "mode"}
    try:
        with pytest.raises(ffi.FittedFactoryUseError, match="fitted_factory_scope_changed"):
            policy.check("read_retained_generation_metadata", forged)
    finally:
        policy._query_bound, policy._query_scope.expected = old_bound, old_expected


def test_another_exact_scope_object_cannot_borrow_the_factory_principal(completed_world):
    policy = completed_world["policy"]
    forged = object.__new__(ffi._FittedFactoryScope)
    forged.__dict__.update(policy._query_scope.__dict__)
    with pytest.raises(ffi.FittedFactoryUseError, match="fitted_factory_principal_required"):
        forged.check("read_retained_generation_metadata", dict(policy._query_bound))


def test_authorization_rechecks_real_current_control_after_inherited_rights(completed_world, monkeypatch):
    world = completed_world
    policy = world["policy"]
    real_check = house.RetainedHouseUsePolicy.check
    old_now = world["now"][0]
    def expire_after_rights(scope, action, resource):
        real_check(scope, action, resource)
        world["now"][0] = "2030-01-01T00:00:00.000000Z"
    monkeypatch.setattr(house.RetainedHouseUsePolicy, "check", expire_after_rights)
    try:
        with pytest.raises((owner.E0InstalledControlError, use.control.E0ControlError,
                            persistence.PersistedFitError)):
            policy.check("read_retained_generation_metadata", dict(policy._query_bound))
    finally:
        world["now"][0] = old_now
