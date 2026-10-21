"""Real private custody/native stores; selected-window/source verifier is test-only.

This is not actual installed E0 admission. Current private control histories are
loaded by the real owner, while synthetic native training inputs stand in for
future qualified registration and temporal bytes. No production data or grants.
"""
import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from engine.research_factory import market_memory_fitted_persistence as persistence
from engine.research_factory import market_memory_fitted_use as use
from engine.research_factory import market_memory_e0_installed_control as owner
from engine.research_factory.market_memory_e0_reservations import ReservationError
from engine.research_factory.market_memory_e0_reserved_read import E0ReservedReadError
from engine.neuralweb import market_memory_fitted_normalization as fitted
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_episode_features as features
from tests.test_market_memory_fitted_normalization import native_training
from tests.test_market_memory_e0_installed_control import selection, records, retain, select, NOW, COMMIT
from tests.test_market_memory_e0_control_records import canonical, record_ref, bundle
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_retained_context_cohort import capture, owner as native_owner, load


def fixture_context(root, template, original=None, *, now=NOW):
    """Explicit substitute ONLY for real source/temporal qualification in tests."""
    captured = {}
    def prepare(fd, selected, current, registration):
        value = copy.deepcopy(template)
        value["selection_sha256"] = sha256(canonical(selected)).hexdigest()
        body = canonical(value)
        original_body = None
        if original is not None:
            old = copy.deepcopy(template)
            old["selection_sha256"] = sha256(original["selection"]).hexdigest()
            original_body = canonical(old)
        body, binding, maximum, resolved = persistence._context_values(
            fd, selected, current, body, original, original_body=original_body)
        captured.update(body=body, binding=binding, maximum=maximum, resolved=resolved)
        return body
    body, selected = owner._load_selected_control(Path(root), "synthetic-study",
        lambda commit: None if commit == COMMIT else pytest.fail("source mismatch"), clock=lambda: now,
        prepare=prepare)
    window = use.TrainingWindowCapability(body, selected, _key=use._TOKEN)
    return persistence._Context(window, Path(root), captured["binding"], captured["maximum"],
        template["binding"]["source_owner"]["subject_id"], captured["resolved"])


@pytest.fixture
def retained_owner(native_training, selection, records, tmp_path, monkeypatch):
    population, query, window, *_ = native_training
    root, selected = selection
    template = json.loads(window._body)
    template["schema"] = "market_memory.selected_training_inputs.v2"
    subject = cohort.disclose_retained_context_cohort(population, policy=Policy())["owner"]["subject_id"]
    now = [NOW]
    def context(original=None):
        value = fixture_context(root, template, original, now=now[0])
        return persistence._Context(value.window, value.directory, value.binding, value.maximum_looks, subject, value.original_window)
    monkeypatch.setattr(persistence, "_load_context", context)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: context().window)
    monkeypatch.setattr(persistence, "_reader", lambda: native_owner(tmp_path)[0])
    monkeypatch.setattr(persistence, "_clock", lambda: now[0])
    monkeypatch.setattr(fitted, "_construction_clock", lambda: now[0])
    persistence.initialize_registered_fit_accounting()
    return root, selected, template, context, now, subject


def test_real_completed_custody_reopens_without_constructing_a_new_fit(retained_owner, monkeypatch):
    _, _, _, context, now, _ = retained_owner
    cap = persistence.persist_registered_fit(policy=Policy())
    before = persistence.disclose_retained_fit(cap)
    assert persistence._store(context()).snapshot()["consumed_looks"] == 1
    now[0] = "2026-10-14T01:01:00.000000Z"
    monkeypatch.setattr(fitted, "fit_registered_normalizer", lambda *a, **k: pytest.fail("refit COMPLETE"))
    monkeypatch.setattr(fitted, "_construction_clock", lambda: pytest.fail("new construction clock"))
    again = persistence.persist_registered_fit(policy=Policy())
    reopened = fitted.reopen_retained_normalizer(again, again._population, policy=Policy())
    assert reopened._body == before["parameters"]
    assert reopened._constructed_at == before["constructed_at"] == NOW
    assert persistence.disclose_retained_fit(again)["receipt"] == before["receipt"]
    assert persistence._store(context()).snapshot()["consumed_looks"] == 1


def test_missing_and_pending_never_reserve_initialize_or_refit_on_open(retained_owner, monkeypatch):
    _, _, _, context, _, _ = retained_owner
    store = persistence._store(context())
    monkeypatch.setattr(fitted, "fit_registered_normalizer", lambda *a, **k: pytest.fail("unexpected fit"))
    with pytest.raises(ReservationError, match="completed_result_unavailable"):
        persistence.open_registered_fit(policy=Policy())
    assert store.snapshot()["consumed_looks"] == store.snapshot()["reserved_looks"] == 0
    operation, intent = persistence._operation(context().window._body)
    store.reserve(operation, intent)
    with pytest.raises(E0ReservedReadError, match="pending_no_replay"):
        persistence.persist_registered_fit(policy=Policy())
    with pytest.raises(ReservationError, match="completed_result_unavailable"):
        persistence.open_registered_fit(policy=Policy())
    assert store.snapshot()["reserved_looks"] == 1


def test_actual_same_epoch_history_advance_preserves_original_definition(retained_owner, records):
    root, selected, _, context, now, _ = retained_owner
    cap = persistence.persist_registered_fit(policy=Policy())
    original = persistence.disclose_retained_fit(cap)
    prior = records["access"]
    current = copy.deepcopy(prior)
    current.update(sequence=1, previous_state_ref=record_ref(prior, "access_state_id"),
                   recorded_at="2026-10-14T00:05:00.000000Z")
    current["budget"].update(consumed_looks=1)
    selected["control_refs"]["access"] = retain(root, current, "access_state_id")
    select(root, selected)
    assert context().window._body != original["window"]
    again = persistence.open_registered_fit(policy=Policy())
    assert persistence.disclose_retained_fit(again)["window"] == original["window"]
    assert fitted.reopen_retained_normalizer(again, again._population, policy=Policy())._body == original["parameters"]


@pytest.mark.parametrize("change", ["revoked", "contaminated", "history_replaced"])
def test_authentication_change_refuses_before_retained_payload_io(retained_owner, records, monkeypatch, change):
    root, selected, _, _, _, _ = retained_owner
    persistence.persist_registered_fit(policy=Policy())
    prior = records["access"]
    current = copy.deepcopy(prior)
    if change == "history_replaced": current["recorded_at"] = "2026-10-14T00:05:00.000000Z"
    else:
        current.update(sequence=1, previous_state_ref=record_ref(prior, "access_state_id"),
                       recorded_at="2026-10-14T00:05:00.000000Z")
        if change == "revoked": current["status"] = "revoked"
        else: current["contamination_state"] = "contaminated"
    selected["control_refs"]["access"] = retain(root, current, "access_state_id")
    select(root, selected)
    # Origin membership can only be checked after original bundle is obtained;
    # private current selection checks still precede every returned capability.
    if change != "history_replaced":
        monkeypatch.setattr(persistence.ReservationStore, "read_completed", lambda *a: pytest.fail("payload before current authority"))
    with pytest.raises((persistence.PersistedFitError, owner.E0InstalledControlError)):
        persistence.open_registered_fit(policy=Policy())


def test_read_right_revocation_prevents_bundle_io_and_reuse(retained_owner, monkeypatch):
    cap = persistence.persist_registered_fit(policy=Policy())
    policy = cap._policy
    policy.denied.add("compare_retained_macro_feature")
    monkeypatch.setattr(persistence.ReservationStore, "read_completed", lambda *a: pytest.fail("payload after source revoke"))
    with pytest.raises((cohort.RetainedContextAccessError, features.EpisodeFeatureAccessError)):
        persistence.disclose_retained_fit(cap)


def test_source_revocation_cannot_consume_an_initial_reservation(retained_owner, monkeypatch):
    policy = Policy()
    policy.denied.add("compare_retained_macro_feature")
    monkeypatch.setattr(persistence.ReservationStore, "reserve", lambda *a: pytest.fail("reservation before source rights"))
    with pytest.raises((cohort.RetainedContextAccessError, features.EpisodeFeatureAccessError)):
        persistence.persist_registered_fit(policy=policy)
    assert persistence._store(retained_owner[3]()).snapshot()["reserved_looks"] == 0


def test_future_training_cutoff_refuses_before_any_reservation(retained_owner, monkeypatch):
    template, context = retained_owner[2:4]
    template["binding"]["fit_cutoff"] = "2027-01-01T00:00:00.000000Z"
    monkeypatch.setattr(persistence.ReservationStore, "reserve", lambda *a: pytest.fail("future-window reservation"))
    with pytest.raises(persistence.PersistedFitError, match="training_cutoff_not_yet_observed"):
        persistence.persist_registered_fit(policy=Policy())
    assert persistence._store(context()).snapshot()["reserved_looks"] == 0


def test_original_generation_is_not_a_later_query(retained_owner, native_training, tmp_path, monkeypatch):
    retained = persistence.persist_registered_fit(policy=Policy())
    reader, pin = native_owner(tmp_path)
    stored = native_training[5]
    cutoff, subject = retained_owner[4][0], retained_owner[5]
    population = load(reader, pin, stored, cutoff=cutoff)
    query = features.read_episode_feature_capability(reader, pin,
        query_id=stored.capture_receipt["query_id"], subject_id=subject,
        query_cutoff=cutoff, policy=Policy())
    monkeypatch.setattr(persistence.ReservationStore, "reserve", lambda *a: pytest.fail("same-generation reservation"))
    with pytest.raises(persistence.PersistedFitError, match="later_native_generation_and_query_cutoff_required"):
        persistence.retain_registered_fitted_query(retained, population, query, policy=Policy(), k=2)


def test_revoke_after_fit_prevents_persist_and_leaves_original_pending(retained_owner, monkeypatch):
    policy = Policy()
    original = fitted.fit_registered_normalizer
    def revoke(*args, **kwargs):
        cap = original(*args, **kwargs)
        policy.denied.add("compare_retained_macro_feature")
        return cap
    monkeypatch.setattr(fitted, "fit_registered_normalizer", revoke)
    with pytest.raises((cohort.RetainedContextAccessError, features.EpisodeFeatureAccessError)):
        persistence.persist_registered_fit(policy=policy)
    context = retained_owner[3]()
    state = persistence._store(context).snapshot()
    assert state["reserved_looks"] == 1 and state["consumed_looks"] == 0
    assert not list((context.directory / "reservations").glob("result-*"))


def test_later_native_append_produces_retained_exact_query_index_without_refit(retained_owner, tmp_path, monkeypatch):
    _, _, _, context, now, subject = retained_owner
    retained = persistence.persist_registered_fit(policy=Policy())
    before = persistence.disclose_retained_fit(retained)
    later = capture(tmp_path, monkeypatch, session="2026-10-14", growth=0.7)
    now[0] = "2026-10-14T11:00:00.000000Z"
    reader, pin = native_owner(tmp_path)
    population = load(reader, pin, later, cutoff=now[0])
    query = features.read_episode_feature_capability(reader, pin,
        query_id=later.capture_receipt["query_id"], subject_id=subject, query_cutoff=now[0], policy=Policy())
    monkeypatch.setattr(fitted, "fit_registered_normalizer", lambda *a, **k: pytest.fail("later query refit"))
    result = persistence.retain_registered_fitted_query(retained, population, query, policy=Policy(), k=2)
    assert result["value"]["index"]["baseline_index"]["expected_capture_count"] == 4
    assert result["value"]["result"]["denominator"]["accounted_captures"] == 4
    assert result["value"]["fit_receipt"] == before["receipt"]
    assert persistence.disclose_retained_fit(retained)["parameters"] == before["parameters"]
    assert persistence._store(context()).snapshot()["consumed_looks"] == 2
    capture(tmp_path, monkeypatch, session="2026-10-14", growth=0.8, seconds=7200)
    now[0] = "2026-10-14T13:00:00.000000Z"
    reproduced, current_policy = persistence.reproduce_registered_fitted_query(result, policy=Policy())
    assert persistence.retrieval.disclose_fitted_retrieval(reproduced, policy=current_policy) == result["value"]["result"]
    assert persistence._store(context()).snapshot()["consumed_looks"] == 2
    changed = copy.deepcopy(result)
    changed["sha256"] = "0" * 64
    with pytest.raises(persistence.PersistedFitError, match="retained_query_bytes_mismatch"):
        persistence.reproduce_registered_fitted_query(changed, policy=Policy())
    monkeypatch.setattr(persistence.retrieval, "retrieve_fitted_contexts", lambda *a, **k: pytest.fail("query replay"))
    assert persistence.retain_registered_fitted_query(retained, population, query, policy=Policy(), k=2) == result
    assert persistence._store(context()).snapshot()["consumed_looks"] == 2


def test_no_dictionary_or_direct_constructor_can_grant_reopen(retained_owner):
    with pytest.raises(persistence.PersistedFitError, match="owner_completed_fit_required"):
        persistence.disclose_retained_fit({"constructed_at": NOW})
    with pytest.raises(persistence.PersistedFitError):
        persistence.RetainedFitCapability(b"{}", {}, None, None, NOW)
    with pytest.raises(use.FittedUseError):
        use.RetainedTrainingWindowCapability(b"{}", None)


def test_new_process_reopens_original_bytes_clock_without_fit_constructor(retained_owner, tmp_path):
    root, _, template, _, now, _ = retained_owner
    retained = persistence.persist_registered_fit(policy=Policy())
    expected = persistence.disclose_retained_fit(retained)
    # Pass only inert fixture metadata/paths. Child has no original Python seals.
    script = r'''
import json,sys
from pathlib import Path
from tests.test_market_memory_fitted_persistence import fixture_context, Policy
from engine.research_factory import market_memory_fitted_persistence as p, market_memory_fitted_use as u
from engine.neuralweb import market_memory_fitted_normalization as f, market_memory_trusted as t
root,native,template=sys.argv[1:]
value=json.loads(template)
p._load_context=lambda original=None: fixture_context(Path(root),value,original,now="2026-10-14T01:01:00.000000Z")
p._reader=lambda:t.TrustedFileAsKnownAtReader(Path(native)/"public"/"trusted-v1")
p._clock=lambda:"2026-10-14T01:01:00.000000Z"
u.prepare_registered_training_window=lambda:p._load_context().window
def forbidden(*a,**k): raise AssertionError("new fit/clock forbidden in fresh process")
f.fit_registered_normalizer=forbidden
f._construction_clock=forbidden
cap=p.open_registered_fit(policy=Policy())
body=p.disclose_retained_fit(cap)
normal=f.reopen_retained_normalizer(cap,cap._population,policy=Policy())
print(json.dumps({"parameters":normal._body.decode(),"constructed_at":normal._constructed_at,"receipt":body["receipt"]},sort_keys=True))
'''
    child = subprocess.run([sys.executable, "-c", script, str(root), str(tmp_path), json.dumps(template)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=60)
    assert child.returncode == 0, child.stderr[-3000:]
    value = json.loads(child.stdout)
    assert value["parameters"].encode() == expected["parameters"]
    assert value["constructed_at"] == expected["constructed_at"]
    assert value["receipt"] == expected["receipt"]


def test_actual_fixed_owner_refuses_before_directory_or_purpose_io(monkeypatch):
    if not (sys.platform == "linux" and persistence.os.geteuid() == 0 and
            Path(persistence.__file__).resolve() == owner.INSTALLED_ROOT / persistence._MODULE):
        monkeypatch.setattr(use, "_purpose", lambda *a: pytest.fail("owner entry before purpose IO"))
        with pytest.raises(persistence.PersistedFitError, match="installed_fit_owner_required"):
            persistence.initialize_registered_fit_accounting()


def test_entitlement_origin_loads_cold_and_refuses_substitution_before_owner_io(monkeypatch):
    # A fresh interpreter proves the actual lazy entitlement import is loaded
    # by this check; its installed-root stand-in is the repository, no controls.
    repository = Path(__file__).resolve().parents[1]
    script = '''
from pathlib import Path
import sys
from engine.research_factory import market_memory_fitted_persistence as p
assert "app.paywall" not in sys.modules
p.owner.INSTALLED_ROOT=Path(sys.argv[1])
p._verify_site_source()
assert Path(sys.modules["app.paywall"].__file__).resolve()==p.owner.INSTALLED_ROOT/"app/paywall.py"
'''
    result = subprocess.run([sys.executable, "-c", script, str(repository)],
        cwd=repository, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr[-2000:]
    from app import paywall
    monkeypatch.setattr(persistence.owner, "INSTALLED_ROOT", repository)
    monkeypatch.setattr(paywall, "__file__", str(repository / "wrong/paywall.py"))
    monkeypatch.setattr(owner, "_directory", lambda *a, **k: pytest.fail("private IO before origin"))
    with pytest.raises(persistence.PersistedFitError, match="installed_site_entitlement_source_required"):
        persistence._verify_site_source()


def test_query_before_retained_fit_observation_refuses_before_accounting(retained_owner, native_training, monkeypatch):
    retained = persistence.persist_registered_fit(policy=Policy())
    population, query, *_ = native_training
    monkeypatch.setattr(persistence.ReservationStore, "reserve", lambda *a: pytest.fail("backdated query reserve"))
    with pytest.raises(persistence.PersistedFitError, match="after_completed_fit_required"):
        persistence.retain_registered_fitted_query(retained, population, query, policy=Policy(), k=1)


@pytest.mark.parametrize("change", ["source_commit", "publication", "installation", "window_method"])
def test_original_immutable_provenance_cannot_be_cast_to_new_selection(retained_owner, records, monkeypatch, change):
    root, selected, template, context, _, _ = retained_owner
    retained = persistence.persist_registered_fit(policy=Policy())
    original = persistence.disclose_retained_fit(retained)
    current = copy.deepcopy(selected)
    body = canonical(template)
    if change == "source_commit": current["source_commit"] = "b" * 40
    if change == "publication": current["control_refs"]["publication"]["sha256"] = "b" * 64
    if change == "installation": current["control_refs"]["installation"]["sha256"] = "b" * 64
    if change == "window_method":
        value = copy.deepcopy(template)
        value["eligibility_method_spec"]["purge_calendar_days"] = 7
        body = canonical(value)
    with owner._directory(root, private=True) as fd:
        with pytest.raises(persistence.PersistedFitError):
            persistence._context_values(fd, current, records, body, original, original_body=original["window"])


def test_whole_retained_bundle_bound_is_not_silently_widened(retained_owner):
    context = retained_owner[3]()
    store = persistence._store(context)
    operation, intent = persistence._operation(context.window._body)
    store.reserve(operation, intent)
    before = {p.name: p.read_bytes() for p in store.directory.iterdir()}
    with pytest.raises(ReservationError, match="bounded_result_bytes_required"):
        store.finish(operation, intent, b"x" * (persistence.MAX_RESULT_BYTES + 1))
    assert {p.name: p.read_bytes() for p in store.directory.iterdir()} == before


def test_closed_native_output_shapes_fit_custody_at_max_population(native_training, selection):
    """Conservative serializer envelope, not 256 actual captures or admission.

    Preserve every field from genuine output, expand all population arrays to
    the native hard cap and selected arrays to MAX_K, and exaggerate numeric
    coordinates to the downstream 400-integer-digit bound. This discriminates
    the review's unreachable 700-800-capture example from this owner's limits.
    Any changed output shape remains visible because templates are real values.
    """
    population, query, window = native_training[:3]
    policy = Policy()
    normalizer = fitted.fit_registered_normalizer(window, population, policy=policy)
    parameters = json.loads(normalizer._body)
    index = fitted.build_fitted_exact_index(normalizer, population, policy=policy)
    cap = persistence.retrieval.retrieve_fitted_contexts(normalizer, population, query,
        policy=policy, k=2, eligibility=persistence.retrieval.baseline.RetainedContextMethodSpec(0, 0, "historical_hypothetical"))
    result = persistence.retrieval.disclose_fitted_retrieval(cap, policy=policy)
    count = cohort.MAX_CAPTURES
    assert count == 256 and persistence.retrieval.baseline.MAX_K == 32
    assert persistence.retrieval.distance.MAX_INTEGER_DIGITS == 400
    for value, key in ((parameters, "training_manifest"),
                       (parameters["qualification_report"], "qualified_native_facts"),
                       (index, "rows"), (index["baseline_index"], "inventory"),
                       (result, "accounting"), (result["audit"], "capture_receipt_sha256")):
        value[key] = [copy.deepcopy(value[key][0]) for _ in range(count)]
    result["selected"] = [copy.deepcopy(result["selected"][0])
                          for _ in range(persistence.retrieval.baseline.MAX_K)]
    longest = "-" + "9" * 400 + "." + "9" * 18
    def enlarge(value, key=""):
        if type(value) is dict:
            return {k: enlarge(v, k) for k, v in value.items()}
        if type(value) is list:
            return [enlarge(v, key) for v in value]
        if type(value) is str:
            if re.fullmatch(r"-?\d+\.\d{18}", value):
                return longest
            if key in {"numerator", "denominator"}:
                return "9" * 400
            if key == "task_id":
                return "t" * 128
        return value
    parameters, index, result = [enlarge(v) for v in (parameters, index, result)]
    bundle = persistence.codec.encode_bundle(canonical(parameters),
        persistence._window_reference(window._body), canonical(selection[1]), NOW)
    query_body = canonical({"schema": "market_memory.retained_fitted_query.v1",
        "fit_receipt": {"binding": {"study_id": "s" * 128, "installation_id": "i" * 128,
            "installation_epoch": "e" * 128, "registration_sha256": "f" * 64,
            "publication_sha256": "f" * 64}, "operation_id": "fit_" + "f" * 64,
            "intent_sha256": "f" * 64, "sha256": "f" * 64, "bytes": len(bundle)},
        "query_cutoff": NOW, "fit_observed_complete_at": NOW,
        "index": index, "result": result})
    assert len(bundle) <= persistence.MAX_RESULT_BYTES
    assert len(query_body) <= persistence.MAX_RESULT_BYTES
    print("closed_shape_bound", len(bundle), len(query_body))


@pytest.fixture
def full_task_blob(bundle):
    """All frozen identities; synthetic questions/evidence are test material only."""
    membership = json.loads(bundle[1][use.control._FROZEN_DOMAIN_DIGESTS["membership"]])
    rows = membership["query_candidates"]
    identities = [{key: row[key] for key in ("query_id", "context_id", "capture_id", "packet_sha256")}
                  for row in rows]
    # Keep all 109 rows and a deliberately large metadata declaration. This is
    # not actual task selection, eligibility, answerability or a native fit.
    body = canonical({"schema": use.control._TASK_SCHEMA, "object_id": "synthetic-full-tasks",
        "tasks": [{"task_id": "synthetic-" + str(i), **identities[i],
                   "question": "Synthetic test-only question. " * 80,
                   "original_evidence": identities[:i + 1]} for i in range(len(rows))]})
    assert len(rows) == 109 and len(body) > persistence.MAX_RESULT_BYTES
    return body


def test_large_original_metadata_resolves_from_exact_immutable_blob_without_bundle_copy(
        selection, records, full_task_blob, monkeypatch):
    root, selected = selection
    body = full_task_blob
    digest = sha256(body).hexdigest()
    path = root / (digest + ".json")
    path.write_bytes(body)
    path.chmod(0o600)
    ref = {"schema": use.control._TASK_SCHEMA, "object_id": "synthetic-full-tasks",
           "sha256": digest, "bytes": len(body)}
    calls = []
    def prepare(fd, selection_value, _records, _registration, _purpose):
        # Test-only domain qualification stand-in. The persistence seam must
        # actually call it for original references, never synthesize old bytes.
        observed = owner._read(fd, ref["sha256"] + ".json", use.control.MAX_DOMAIN_OBJECT_BYTES)
        if len(observed) != ref["bytes"] or sha256(observed).hexdigest() != ref["sha256"]:
            raise use.FittedUseError("training_reference_bytes_mismatch")
        calls.append(sha256(canonical(selection_value)).hexdigest())
        return canonical({"schema": "market_memory.selected_training_inputs.v2",
            "selection_sha256": calls[-1], "reference_sha256": [digest],
            "partition_tasks": json.loads(observed)["tasks"]})
    monkeypatch.setattr(use, "_prepare", prepare)
    with owner._directory(root, private=True) as fd:
        original_body = prepare(fd, selected, records, b"", {})
        original = {"window_reference": persistence._window_reference(original_body),
                    "selection": canonical(selected)}
    previous_selection = copy.deepcopy(selected)
    advanced = copy.deepcopy(records["access"])
    advanced.update(sequence=1, previous_state_ref=record_ref(records["access"], "access_state_id"),
                    recorded_at="2026-10-14T00:05:00.000000Z")
    selected["control_refs"]["access"] = retain(root, advanced, "access_state_id")
    select(root, selected)
    current_records = {**records, "access": advanced}
    with owner._directory(root, private=True) as fd:
        values = persistence._prepare_context(fd, selected, current_records, b"", {}, original)
    assert calls[-2:] == [sha256(canonical(selected)).hexdigest(),
                         sha256(canonical(previous_selection)).hexdigest()]
    assert values[3] == original_body
    assert len(json.loads(values[3])["partition_tasks"]) == 109
    parameters = canonical({"schema": "market_memory.fitted_normalizer.v2"})
    retained = persistence.codec.encode_bundle(parameters, original["window_reference"], original["selection"], NOW)
    assert len(retained) < persistence.MAX_RESULT_BYTES
    assert persistence.codec.decode_bundle(retained)["window"] == original["window_reference"]
    for defect in ("missing", "changed"):
        if defect == "missing": path.unlink()
        else:
            path.write_bytes(body[:-1] + b" ")
            path.chmod(0o600)
        with owner._directory(root, private=True) as fd:
            with pytest.raises((owner.E0InstalledControlError, use.FittedUseError)):
                persistence._prepare_context(fd, selected, current_records, b"", {}, original)


def test_completed_read_checks_original_accounting_limit_before_payload(retained_owner, monkeypatch):
    persistence.persist_registered_fit(policy=Policy())
    snapshot = persistence.ReservationStore.snapshot
    monkeypatch.setattr(persistence.ReservationStore, "snapshot", lambda store: {**snapshot(store), "maximum_looks": 4})
    monkeypatch.setattr(persistence.ReservationStore, "read_completed", lambda *a: pytest.fail("payload before budget binding"))
    with pytest.raises(persistence.PersistedFitError, match="accounting_budget_changed"):
        persistence.open_registered_fit(policy=Policy())


def test_actual_exact_generation_house_policies_support_a_later_query(retained_owner, tmp_path, monkeypatch):
    """Actual closed resource policies; only site login and study metadata are fixtures."""
    from engine.neuralweb import market_memory_retained_use as house
    root, _, template, _, now, subject = retained_owner
    repository = Path(__file__).resolve().parents[1]
    # Explicit installed-source-root stand-in; actual source/private qualification
    # remains supplied by retained_owner, not claimed by this isolated test.
    monkeypatch.setattr(persistence.owner, "INSTALLED_ROOT", tmp_path)
    for rel in (house.REGISTRATION, house.AUTHORITY_RECORD):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((repository / rel).read_bytes())
    registration_path = tmp_path / house.REGISTRATION
    registration = json.loads(registration_path.read_bytes())
    registration["store_id"] = template["binding"]["source_owner"]["store_id"]
    registration_path.write_text(json.dumps(registration))
    monkeypatch.setattr(house, "_enforce_current_site_user", lambda user: None if user == "member" else
        (_ for _ in ()).throw(house.RetainedUseError("fixture_site_denied")))
    original = template["binding"]["source_owner"]
    training_policy = house.RetainedHouseUsePolicy(tmp_path, user_id="member", subject_id=subject,
        store_id=original["store_id"], generation_id=original["generation_id"],
        generation_sha256=original["generation_sha256"], query_cutoff=template["binding"]["fit_cutoff"],
        mode=template["binding"]["mode"])
    retained = persistence.persist_registered_fit(policy=training_policy)
    later = capture(tmp_path, monkeypatch, session="2026-10-14", growth=0.7)
    now[0] = "2026-10-14T11:00:00.000000Z"
    reader, pin = native_owner(tmp_path)
    query_policy = house.RetainedHouseUsePolicy(tmp_path, user_id="member", subject_id=subject,
        store_id=pin.store_id, generation_id=pin.generation_id, generation_sha256=pin.generation_sha256,
        query_cutoff=now[0], mode=template["binding"]["mode"])
    population = load(reader, pin, later, cutoff=now[0], policy=query_policy)
    query = features.read_episode_feature_capability(reader, pin,
        query_id=later.capture_receipt["query_id"], subject_id=subject, query_cutoff=now[0], policy=query_policy)
    result = persistence.retain_registered_fitted_query(retained, population, query, policy=query_policy, k=2)
    assert result["value"]["result"]["denominator"]["accounted_captures"] == 4
    reproduced, combined = persistence.reproduce_registered_fitted_query(result, policy=query_policy)
    assert persistence.retrieval.disclose_fitted_retrieval(reproduced, policy=combined) == result["value"]["result"]
    assert training_policy.expected["generation_id"] != query_policy.expected["generation_id"]
    assert training_policy.policy_id == query_policy.policy_id == combined.policy_id
    unknown = {**query_policy.expected, "generation_id": "mmgeneration_" + "f" * 64}
    with pytest.raises(persistence.PersistedFitError, match="only_original_training_or_exact_query_scope_allowed"):
        combined.check("read_retained_generation_metadata", unknown)
    with pytest.raises(persistence.PersistedFitError, match="actual_exact_house_scopes_required"):
        persistence._ExactHouseScopes(Policy(), query_policy, _key=persistence._TOKEN)
    # Two independently entitled users do not become one comparison principal.
    monkeypatch.setattr(house, "_enforce_current_site_user", lambda user: None)
    another = house.RetainedHouseUsePolicy(tmp_path, user_id="another-member", subject_id=subject,
        store_id=pin.store_id, generation_id=pin.generation_id, generation_sha256=pin.generation_sha256,
        query_cutoff=now[0], mode=template["binding"]["mode"])
    with pytest.raises(persistence.PersistedFitError, match="same_current_house_principal_and_source_required"):
        persistence._comparison_policy(retained, another)
    # Each original identity component is checked before actual policy I/O.
    for name, changed in (("root", tmp_path / "another-root"), ("mode", "current"),
                          ("registration_sha256", "f" * 64), ("policy_id", "another-source")):
        before = getattr(query_policy, name)
        setattr(query_policy, name, changed)
        with pytest.raises(persistence.PersistedFitError, match="same_current_house_principal_and_source_required"):
            combined.check("read_retained_generation_metadata", query_policy.expected)
        setattr(query_policy, name, before)
    for name, changed in (("store_id", "different-store"), ("subject_id", "different-subject")):
        before = query_policy.expected[name]
        query_policy.expected[name] = changed
        with pytest.raises(persistence.PersistedFitError, match="same_registered_training_site_scope_required"):
            persistence._training_policy(retained_owner[3](), query_policy)
        query_policy.expected[name] = before
    query_policy.mode = "current"
    with pytest.raises(persistence.PersistedFitError, match="same_registered_training_site_scope_required"):
        persistence._training_policy(retained_owner[3](), query_policy)
    query_policy.mode = template["binding"]["mode"]
    monkeypatch.setattr(persistence.owner, "INSTALLED_ROOT", tmp_path / "different-installation")
    with pytest.raises(persistence.PersistedFitError, match="installed_house_source_owner_required"):
        persistence._training_policy(retained_owner[3](), query_policy)
    monkeypatch.setattr(persistence.owner, "INSTALLED_ROOT", tmp_path)
    # Actual source registration changes revoke both scopes before disclosure.
    registration["revoked_capture_ids"] = [later.capture_receipt["capture_id"]]
    registration_path.write_text(json.dumps(registration))
    with pytest.raises(house.RetainedUseError, match="^source_use_registration_changed$"):
        combined.check("read_retained_generation_metadata", query_policy.expected)
    with pytest.raises(Exception, match="source_usage_not_admitted"):
        persistence.retrieval.disclose_fitted_retrieval(reproduced, policy=combined)
