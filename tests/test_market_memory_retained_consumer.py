"""Real trusted writer -> registered policy -> existing API and Brain owners."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import market_memory as api
from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_retained_use as use
from tests.test_market_memory_retained_context_cohort import capture, owner, CUTOFF

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def bounded_cohort_reuse(monkeypatch):
    from engine.neuralweb import market_memory_retained_cohort_reuse as reuse
    monkeypatch.setattr(reuse, "_CACHE", reuse.BoundedCohortCache())
    return reuse


@pytest.fixture
def original(tmp_path, monkeypatch):
    old = capture(tmp_path, monkeypatch, session="2026-08-01", growth=0.1)
    edge = capture(tmp_path, monkeypatch, session="2026-08-07", growth=0.3)
    near = capture(tmp_path, monkeypatch, session="2026-08-10", growth=0.2)
    query = capture(tmp_path, monkeypatch, session="2026-08-13", growth=0.2)
    future = capture(tmp_path, monkeypatch, session="2026-08-21", growth=0.2)
    reader, pin = owner(tmp_path)
    for rel in (use.REGISTRATION, use.AUTHORITY_RECORD):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / rel).read_bytes())
    registration = json.loads((tmp_path / use.REGISTRATION).read_text())
    registration["store_id"] = pin.store_id  # Bind the actual independently created fixture store.
    (tmp_path / use.REGISTRATION).write_text(json.dumps(registration))
    monkeypatch.setenv("MARKET_MEMORY_TRUSTED_STORE_DIR", str(reader.root))
    monkeypatch.setattr(use, "_enforce_current_site_user", lambda uid: None if uid == "member" else (_ for _ in ()).throw(HTTPException(403)))
    api._reset_symbol_rate_limit_for_tests()
    method = api.retained_method_catalog(tmp_path)[0]
    spec = {"query_id": query.capture_receipt["query_id"],
            "subject_id": query.packet["subject"]["subject_id"],
            "generation_id": pin.generation_id, "generation_sha256": pin.generation_sha256,
            "query_cutoff": CUTOFF, "method_spec_id": method["method_spec_id"], "limit": 8}
    return tmp_path, reader, pin, spec, (old, edge, near, query, future)


def call(original, **changes):
    root, _reader, _pin, spec, _captures = original
    return api.retained_macro_for_user(root, "member", {**spec, **changes})


def test_real_owner_to_bounded_brain_projection_and_exact_five_day_exclusions(original, monkeypatch):
    monkeypatch.setattr(mm, "macro_context", lambda *a, **k: pytest.fail("recomputed fallback"))
    value = call(original)
    assert value["schema"] == "brain.retained_market_context.v1"
    assert value["status"] == "MATCHES" and value["denominator"]["returned"] == 2
    assert value["denominator"]["expected_captures"] == 5
    assert value["exclusion_counts"] == {"future_capture": 1, "numerically_eligible": 2,
                                         "query_self": 1, "registered_purge": 1}
    assert len(json.dumps(value).encode()) < 64 * 1024
    assert value["method_spec"]["purge_calendar_days"] == 5
    assert value["method_spec"]["embargo_calendar_days"] == 5
    assert value["source_use"]["authority_record"] == use.AUTHORITY_RECORD
    assert not any(value["claims"].values())
    for card in value["source_cards"]:
        assert {f["field"] for f in card["facts"]} == set(use.FIELDS)
        assert all(f["structural_source_closure"] for f in card["facts"])
        assert all(not f["underlying_component_truth_authenticated"] for f in card["facts"])


def test_genuine_existing_gateway_dispatch_consumes_new_owner(original, monkeypatch):
    from engine.neuralweb import brain_gateway as gateway, ask_brain
    root, _reader, _pin, spec, _captures = original
    value = gateway._dispatch_brain_tool("get_retained_market_context", spec, root, root, "", user_id="member")
    assert value["schema"] == "brain.retained_market_context.v1"
    assert value["denominator"]["returned"] == 2
    assert "get_retained_market_context" in ask_brain._FAST_VISIBLE_TOOL_FAMILIES["macro_rates"]
    denied = gateway._dispatch_brain_tool("get_retained_market_context", spec, root, root, "", user_id="")
    assert denied["http_status"] == 403 and "source_cards" not in denied


def test_existing_http_owner_private_headers_and_duplicate_query_rejection(original, monkeypatch):
    root, _reader, _pin, spec, _captures = original
    monkeypatch.setattr(api, "_repo_root", lambda: root)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "member"}
    client = TestClient(app)
    response = client.get("/api/market-memory/v1/macro/retained", params=spec)
    assert response.status_code == 200
    assert response.json()["denominator"]["returned"] == 2
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    duplicated = list(spec.items()) + [("query_id", spec["query_id"])]
    response = client.get("/api/market-memory/v1/macro/retained", params=duplicated)
    assert response.status_code == 400 and response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("changes", [{"user_id": "admin"}, {"source_admitted": True},
                                     {"purge_calendar_days": 0}, {"limit": True},
                                     {"limit": "08"}, {"query_cutoff": "2026-08-20"}])
def test_untrusted_grants_or_noncanonical_inputs_refused_before_owner(original, monkeypatch, changes):
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", lambda *a, **k: pytest.fail("invalid request opened owner"))
    with pytest.raises(HTTPException) as error:
        call(original, **changes)
    assert error.value.status_code == 400


def test_missing_exact_capture_and_generation_never_fall_back(original, monkeypatch):
    monkeypatch.setattr(mm, "macro_context", lambda *a, **k: pytest.fail("fallback"))
    with pytest.raises(HTTPException) as error:
        call(original, query_id="mmquery_" + "f" * 64)
    assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        call(original, generation_sha256="f" * 64)
    assert error.value.status_code == 503


def test_unknown_method_and_subject_cannot_select_other_data(original):
    with pytest.raises(HTTPException) as error:
        call(original, method_spec_id="mmretainedmethod_" + "f" * 64)
    assert error.value.status_code == 400
    with pytest.raises(HTTPException) as error:
        call(original, subject_id="mmsecurity_" + "f" * 64)
    assert error.value.status_code == 403


def test_authority_record_change_refuses_before_owner(original, monkeypatch):
    root = original[0]
    (root / use.AUTHORITY_RECORD).write_text("changed record")
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", lambda *a, **k: pytest.fail("unadmitted owner"))
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 403


def test_revocation_after_actual_payload_prevents_any_disclosure(original, monkeypatch):
    root = original[0]
    read = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    def revoke(*a, **k):
        value = read(*a, **k)
        p = root / use.REGISTRATION
        changed = json.loads(p.read_text())
        changed["enabled"] = False
        p.write_text(json.dumps(changed))
        return value
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", revoke)
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 403


def test_shared_owner_read_budget_and_existing_slots_refuse_without_widening(original):
    with pit.bounded_owner_reads(maximum_bytes=10):
        with pytest.raises(HTTPException) as error:
            call(original)
    assert error.value.detail["state"] == "OWNER_READ_BUDGET_EXCEEDED"
    assert api._playback_slots.acquire(blocking=False)
    assert api._playback_slots.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as error:
            call(original)
        assert error.value.detail["state"] == "BUSY"
    finally:
        api._playback_slots.release()
        api._playback_slots.release()


def test_current_mode_is_separate_identity_and_old_reference_stays_reproducible(original, monkeypatch):
    root, _reader, _pin, spec, _captures = original
    before = call(original)
    current = api.retained_method_catalog(root)[1]
    value = call(original, method_spec_id=current["method_spec_id"])
    assert value["mode"] == "current_contextual_support"
    assert before["mode"] == "historical_hypothetical"
    assert value["method_spec"]["method_spec_id"] != before["method_spec"]["method_spec_id"]
    capture(root, monkeypatch, session="2026-08-22", growth=0.9)
    assert call(original) == before


def test_valid_empty_selection_is_an_observation_not_storage_failure(original):
    root, _reader, _pin, _spec, captures = original
    value = call(original, query_id=captures[0].capture_receipt["query_id"],
                 query_cutoff="2026-08-02T12:00:00Z")
    assert value["status"] == "ABSTAINED" and value["available"] is True
    assert value["denominator"]["returned"] == 0
    assert value["exclusion_counts"] == {"future_capture": 4, "query_self": 1}
    assert len(value["source_cards"]) == 1


def test_revoked_unreturned_source_protects_denominator_before_private_read(original, monkeypatch):
    root, _reader, _pin, _spec, captures = original
    p = root / use.REGISTRATION
    registration = json.loads(p.read_text())
    registration["revoked_source_receipt_ids"] = captures[-1].capture_receipt["source_receipt_ids"]
    p.write_text(json.dumps(registration))
    # Earlier permitted rows may have been read for the query. The revoked future
    # row remains part of the denominator and cannot be ignored as unreturned.
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 403


def test_current_entitlement_is_rechecked_after_actual_source_read(original, monkeypatch):
    read = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    def revoke(*a, **k):
        value = read(*a, **k)
        monkeypatch.setattr(use, "_enforce_current_site_user", lambda uid: (_ for _ in ()).throw(HTTPException(403)))
        return value
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", revoke)
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 403


def test_existing_user_rate_limit_applies_to_both_entry_points(original):
    root, _reader, _pin, spec, _captures = original
    with api._symbol_rate_lock:
        for _ in range(api._PLAYBACK_USER_LIMIT):
            assert api._book_symbol_rate("playback-user:member", limit=api._PLAYBACK_USER_LIMIT,
                                         now=api.time.monotonic())
    with pytest.raises(HTTPException) as error:
        api.retained_macro_for_user(root, "member", spec)
    assert error.value.status_code == 429


def test_exact_cohort_reuse_reduces_owner_reads_and_recomputes_result(original, monkeypatch):
    """One miss/two hits on the same synthetic owner fixture, not a load SLA."""
    import time
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    read = cohort.read_retained_context_cohort
    builds = []
    def counted(*args, **kwargs):
        value = read(*args, **kwargs)
        builds.append(value)
        return value
    monkeypatch.setattr(cohort, "read_retained_context_cohort", counted)
    measurements = []
    results = []
    for phase in ("miss", "exact_hit", "exact_hit"):
        wall, cpu = time.monotonic(), time.thread_time()
        with pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024) as budget:
            results.append(call(original))
        measurements.append({"phase": phase, "wall_ms": (time.monotonic() - wall) * 1000,
            "thread_cpu_ms": (time.thread_time() - cpu) * 1000,
            "owner_bytes": budget.bytes_read, "owner_objects": budget.objects_opened})
    assert len(builds) == 1
    assert results[0] == results[1] == results[2]
    for hit in measurements[1:]:
        assert 0 < hit["owner_objects"] < measurements[0]["owner_objects"]
        assert 0 < hit["owner_bytes"] < measurements[0]["owner_bytes"]
    # A different k must recompute retrieval/output rather than return cached JSON.
    limited = call(original, limit=1)
    assert limited["denominator"]["returned"] == 1
    assert len(builds) == 1
    results[0]["source_cards"].clear()
    assert call(original)["source_cards"]
    print("EXACT_COHORT_FIXTURE_MEASUREMENT " + json.dumps({
        "fixture_only": True, "captures": 5, "samples": measurements,
        "p95_or_concurrency_claim": False}, sort_keys=True))


@pytest.mark.parametrize("action", ["disclose_retained_macro_capture", "verify_retained_macro_retention"])
def test_cached_unreturned_source_rechecks_current_policy_and_never_falls_back(
        original, monkeypatch, bounded_cohort_reuse, action):
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    call(original)
    unreturned = original[-1][-1].capture_receipt
    check = use.RetainedHouseUsePolicy.check
    def deny(self, name, resource):
        check(self, name, resource)
        if name == action and resource.get("capture_id") == unreturned["capture_id"]:
            assert resource["source_receipt_ids"] == unreturned["source_receipt_ids"]
            raise use.RetainedUseError("fixture_current_source_revoked")
    monkeypatch.setattr(use.RetainedHouseUsePolicy, "check", deny)
    monkeypatch.setattr(cohort, "read_retained_context_cohort",
                        lambda *a, **k: pytest.fail("cache denial must not trigger source fallback"))
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 403


@pytest.mark.parametrize("revoke", ["entitlement", "registration"])
def test_current_rights_change_during_cache_hit_fails_closed(original, monkeypatch, bounded_cohort_reuse, revoke):
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    call(original)
    get = bounded_cohort_reuse.BoundedCohortCache.get
    def changing_get(self, key):
        value = get(self, key)
        assert value is not None
        if revoke == "entitlement":
            monkeypatch.setattr(use, "_enforce_current_site_user",
                lambda uid: (_ for _ in ()).throw(HTTPException(403)))
        else:
            path = original[0] / use.REGISTRATION
            changed = json.loads(path.read_text())
            changed["enabled"] = False
            path.write_text(json.dumps(changed))
        return value
    monkeypatch.setattr(bounded_cohort_reuse.BoundedCohortCache, "get", changing_get)
    monkeypatch.setattr(cohort, "read_retained_context_cohort",
                        lambda *a, **k: pytest.fail("refused hit must not become a miss"))
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 403


def test_cached_cohort_does_not_bypass_live_pin_integrity_or_request_budget(original, monkeypatch):
    call(original)
    with pit.bounded_owner_reads(maximum_bytes=10):
        with pytest.raises(HTTPException) as error:
            call(original)
    assert error.value.detail["state"] == "OWNER_READ_BUDGET_EXCEEDED"
    # Fresh pinning still authenticates backing generation bytes on every hit.
    _root, reader, pin, _spec, _captures = original
    pit._generation_path(reader.root, pin.generation_id).write_bytes(b"corrupted generation")
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 503


def test_cached_cohort_preserves_slots_and_current_head_capture_bound(original, monkeypatch):
    call(original)
    assert api._playback_slots.acquire(blocking=False)
    assert api._playback_slots.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as error:
            call(original)
        assert error.value.detail["state"] == "BUSY"
    finally:
        api._playback_slots.release()
        api._playback_slots.release()
    def over_budget(self, *, generation_id=None, maximum_capture_count=None):
        assert maximum_capture_count == 256
        raise pit.MarketMemoryStoreError("fixture_current_head_exceeds_capture_bound")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation", over_budget)
    with pytest.raises(HTTPException) as error:
        call(original)
    assert error.value.status_code == 503


def test_exact_cutoff_mode_and_method_cannot_select_another_cached_cohort(original, monkeypatch):
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    read = cohort.read_retained_context_cohort
    builds = []
    def counted(*args, **kwargs):
        builds.append((kwargs["query_cutoff"], kwargs["policy"].mode))
        return read(*args, **kwargs)
    monkeypatch.setattr(cohort, "read_retained_context_cohort", counted)
    before = call(original)
    current = api.retained_method_catalog(original[0])[1]
    assert call(original, method_spec_id=current["method_spec_id"])["mode"] == "current_contextual_support"
    assert call(original, query_cutoff="2026-08-20T12:00:01Z")["available"] is True
    assert call(original) == before
    assert len(builds) == 3


@pytest.mark.parametrize("policy_type", [use.RetainedFactoryUsePolicy,
    type("OtherHousePolicy", (use.RetainedHouseUsePolicy,), {})])
def test_factory_and_other_application_policies_do_not_enter_site_cache(
        original, monkeypatch, bounded_cohort_reuse, policy_type):
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    from engine.neuralweb import market_memory_episode_retrieval as retrieval
    sentinel = object()
    # Dispatch test only: these uninitialized objects grant no rights.
    policy = object.__new__(policy_type)
    monkeypatch.setattr(cohort, "read_retained_context_cohort", lambda *a, **k: sentinel)
    monkeypatch.setattr(bounded_cohort_reuse, "read_exact_retained_cohort",
                        lambda *a, **k: pytest.fail("nonexact House owner entered site cache"))
    value = policy._read_retained_context_cohort(
        original[1], original[2], subject_id=original[3]["subject_id"],
        query_cutoff=original[3]["query_cutoff"],
        method=retrieval.RetainedContextMethodSpec(5, 5, "historical_hypothetical"))
    assert value is sentinel


def test_generic_owner_policy_uses_original_issuance_without_site_reader(
        original, monkeypatch, bounded_cohort_reuse):
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    from engine.neuralweb import market_memory_episode_retrieval as retrieval
    root, reader, pin, spec, _ = original
    bound = use.RetainedHouseUsePolicy(root, user_id="member", mode="historical_hypothetical",
        **{k: spec[k] for k in ("subject_id", "generation_id", "generation_sha256", "query_cutoff")},
        store_id=pin.store_id)
    class GenericPolicy:
        # This supplies only the incumbent policy protocol, never a reader hook.
        policy_id, expected = bound.policy_id, bound.expected
        check = staticmethod(bound.check)
    policy = GenericPolicy()
    read = cohort.read_retained_context_cohort
    reads = []
    def counted(*args, **kwargs):
        reads.append(kwargs["policy"])
        return read(*args, **kwargs)
    monkeypatch.setattr(cohort, "read_retained_context_cohort", counted)
    monkeypatch.setattr(bounded_cohort_reuse, "read_exact_retained_cohort",
                        lambda *a, **k: pytest.fail("generic owner entered site cache"))
    for _ in range(2):
        selection, packet = mm.compose_retained_macro_capabilities(reader, policy=policy,
            **{k: spec[k] for k in ("query_id", "subject_id", "generation_id", "generation_sha256", "query_cutoff")},
            method=retrieval.RetainedContextMethodSpec(5, 5, "historical_hypothetical"), limit=8)
        assert selection is not None and packet is not None
    assert reads == [policy, policy]


def test_finite_cohort_storage_lru_bytes_replacement_and_identity_discard(original, bounded_cohort_reuse):
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    from tests.test_market_memory_episode_features import Policy
    kwargs = {"subject_id": original[3]["subject_id"], "query_cutoff": original[3]["query_cutoff"],
              "policy": Policy()}
    first = cohort.read_retained_context_cohort(original[1], original[2], **kwargs)
    second = cohort.read_retained_context_cohort(original[1], original[2], **kwargs)
    storage = bounded_cohort_reuse.BoundedCohortCache(max_entries=2)
    assert storage.put(("a",), first)
    assert storage.put(("b",), second)
    assert storage.get(("a",)) is first
    assert storage.put(("c",), second)
    assert storage.get(("b",)) is None
    assert storage.get(("c",)) is second
    # This independently computes the exact retained payload accounting contract.
    def payload_size(capability):
        values = [capability, *(item for item in capability._features if item is not None)]
        return sum(len(item._body) + len(item._resource) + len(item._digest.encode()) for item in values)
    weight = payload_size(first) + len("a".encode())
    exact = bounded_cohort_reuse.BoundedCohortCache(max_entries=2, max_bytes=weight)
    assert exact.put(("a",), first)
    assert exact.put(("a",), second)  # Replacement cannot double-charge bytes.
    assert not exact.put(("too-large-key",), first)
    assert exact.get(("a",)) is second  # An uncacheable value cannot evict it.
    exact.discard(("a",), first)
    assert exact.get(("a",)) is second  # Delayed refusal cannot remove replacement.
    exact.discard(("a",), second)
    assert exact.get(("a",)) is None


@pytest.mark.parametrize("kwargs", [{"max_entries": 0}, {"max_entries": True}, {"max_entries": 9},
    {"max_bytes": 0}, {"max_bytes": True}, {"max_bytes": 16 * 1024 * 1024 + 1}])
def test_cohort_storage_limits_are_fixed_positive_exact_integers(bounded_cohort_reuse, kwargs):
    from engine.neuralweb.market_memory_retained_cohort_cache import BoundedCohortCacheError
    with pytest.raises(BoundedCohortCacheError):
        bounded_cohort_reuse.BoundedCohortCache(**kwargs)
