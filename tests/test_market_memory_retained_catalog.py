"""Authenticated discovery through the actual trusted owner, API and Brain."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app import market_memory as api
from engine.neuralweb import market_memory_retained_catalog as catalog
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_trusted as trusted
from tests.test_market_memory_retained_consumer import original


STAGES = ['authorization', 'authorization', 'generation_pin', 'receipt_authorization',
          'projections', 'response_projection', 'final_authorization']


def _freeze_catalog_clock(monkeypatch):
    class FrozenClock:
        @staticmethod
        def now(_timezone):
            return datetime(2026, 10, 19, tzinfo=timezone.utc)
    monkeypatch.setattr(catalog, 'datetime', FrozenClock)


def test_stage_events_correlate_without_changing_catalog_bytes(original, monkeypatch, caplog):
    _freeze_catalog_clock(monkeypatch)
    expected = catalog.read_catalog(original[0], user_id='member', mode='historical_hypothetical',
                                    offset=0, limit=8)
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    assert discover(original) == expected
    events = [r.args for r in caplog.records if r.getMessage().startswith('market_memory.read.')]
    stages = [fields for event, fields in events if event == 'stage']
    seq = next(fields['seq'] for event, fields in events if event == 'start')
    assert [r['stage'] for r in stages] == STAGES
    assert all(set(r) == {'tag', 'seq', 'stage', 'elapsed_ms', 'thread_cpu_ms',
                          'native_thread_id'} for r in stages)
    assert all(fields['native_thread_id'] == threading.get_native_id()
               for event, fields in events if event in {'start', 'stage', 'finish'})
    assert all(r['seq'] == seq and r['tag'] == 'retained_catalog'
               and r['elapsed_ms'] >= 0 and r['thread_cpu_ms'] >= 0 for r in stages)
    assert next(fields for event, fields in events if event == 'finish')['success'] is True
    assert not api._read_observation_active


def test_stage_durations_attribute_owner_work_without_wallclock_sleep(original, monkeypatch):
    clocks = [100.0, 20.0]
    monkeypatch.setattr(catalog, 'time', SimpleNamespace(
        monotonic=lambda: clocks[0], thread_time=lambda: clocks[1]))
    for name, wall, cpu in [('read_pinned_generation', 0.017, 0.007),
                            ('read_pinned_capture_projections', 0.031, 0.011)]:
        actual = getattr(trusted.TrustedFileAsKnownAtReader, name)
        def measured(*args, _actual=actual, _wall=wall, _cpu=cpu, **kwargs):
            value = _actual(*args, **kwargs)
            clocks[0] += _wall
            clocks[1] += _cpu
            return value
        monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, name, measured)
    events = []
    value = catalog.read_catalog(original[0], user_id='member', mode='historical_hypothetical',
        offset=0, limit=8, stage_observer=lambda *args: events.append(args))
    assert value['selection']['total'] == 5
    timing = {name: (wall, cpu) for name, wall, cpu in events}
    assert timing['generation_pin'] == pytest.approx((17, 7))
    assert timing['projections'] == pytest.approx((31, 11))


@pytest.mark.parametrize('failure', ['logger', 'clock', 'callback'])
def test_observation_failures_preserve_actual_catalog_result_and_permits(
        original, monkeypatch, failure):
    _freeze_catalog_clock(monkeypatch)
    expected = discover(original)
    def fail(*args, **kwargs):
        raise RuntimeError('private observer failure')
    if failure == 'logger':
        monkeypatch.setattr(api._read_observation_log, 'info', fail)
    elif failure == 'callback':
        monkeypatch.setattr(api, '_read_observation_stage', fail)
    else:
        monkeypatch.setattr(catalog, 'time', SimpleNamespace(monotonic=fail, thread_time=fail))
    assert discover(original) == expected
    assert not api._read_observation_active
    assert api._playback_slots.acquire(False)
    assert api._playback_slots.acquire(False)
    api._playback_slots.release()
    api._playback_slots.release()


def test_failed_projection_keeps_original_refusal_and_identifies_stage(original, monkeypatch, caplog):
    def fail(*args, **kwargs):
        from engine.neuralweb import market_memory_pit as pit
        raise pit.MarketMemoryStoreError('private source detail')
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, 'read_pinned_capture_projections', fail)
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    with pytest.raises(HTTPException) as error:
        discover(original)
    assert error.value.status_code == 503
    assert error.value.detail == {'state': 'EXACT_CATALOG_UNAVAILABLE'}
    stages = [r.args[1]['stage'] for r in caplog.records if '.stage ' in r.getMessage()]
    assert stages == STAGES[:5]
    assert "'success': False" in caplog.text and 'private source detail' not in caplog.text
    assert not api._read_observation_active


def discover(original, **spec):
    return api.retained_catalog_for_user(original[0], "member", spec)


def test_catalog_pins_full_authenticated_generation_and_pages(original):
    value = discover(original, limit=2)
    assert value["schema"] == catalog.SCHEMA
    assert value["selection"]["total"] == 5
    assert len(value["entries"]) == 2
    assert value["generation"]["generation_id"] == original[2].generation_id
    assert len(value["methods"]) == 2
    next_page = api.retained_catalog_for_user(original[0], "member", value["selection"]["continuation"])
    assert next_page["generation"] == value["generation"]
    assert not {r["query_id"] for r in value["entries"]} & {r["query_id"] for r in next_page["entries"]}
    assert value["outcomes"]["status"] == "NOT_ATTACHED"


def test_supported_cutoff_is_actual_maximum_clock_then_consumes_real_refs(original):
    value = discover(original)
    query = next(row for row in value["entries"] if row["query_id"] == original[3]["query_id"])
    from engine.neuralweb.market_memory_retained_context_cohort import utc_instant
    assert utc_instant(query["earliest_supported_cutoff"]) == max(map(utc_instant, query["clocks"].values()))
    method = next(m for m in value["methods"] if m["mode"] == value["mode"])
    spec = {key: query[key] for key in ("query_id", "subject_id")}
    spec.update({key: value["generation"][key] for key in ("generation_id", "generation_sha256")})
    spec.update(query_cutoff=query["earliest_supported_cutoff"], method_spec_id=method["method_spec_id"])
    answer = api.retained_macro_for_user(original[0], "member", spec)
    assert answer["source_cards"][0]["context_id"] == query["context_id"]


@pytest.mark.parametrize("spec", [{"offset": 1}, {"limit": True}, {"limit": 21}, {"offset": "01"},
    {"user_id": "admin"}, {"subject_id": "guessed"}, {"mode": "live"}, {"generation_id": "bad"},
    {"stage_observer": "caller supplied"}])
def test_invalid_catalog_request_denied_before_owner(original, monkeypatch, spec):
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", lambda *a, **k: pytest.fail("opened owner"))
    with pytest.raises(HTTPException) as exc:
        discover(original, **spec)
    assert exc.value.status_code == 400


def test_source_use_denied_before_reader_construction(original, monkeypatch):
    path = original[0] / use.REGISTRATION
    value = json.loads(path.read_text()); value["enabled"] = False; path.write_text(json.dumps(value))
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", lambda *a, **k: pytest.fail("opened owner"))
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 403


def test_revoked_unreturned_capture_refuses_count_and_payload(original):
    path = original[0] / use.REGISTRATION
    value = json.loads(path.read_text())
    value["revoked_capture_ids"] = [original[4][0].capture_receipt["capture_id"]]
    path.write_text(json.dumps(value))
    with pytest.raises(HTTPException) as exc:
        discover(original, limit=1)
    assert exc.value.status_code == 403
    assert "entries" not in exc.value.detail and "total" not in exc.value.detail


def test_final_source_registration_change_refuses_whole_disclosure(original, monkeypatch):
    real = use.RetainedHouseUsePolicy.disclosure
    def revoke(self):
        value = real(self)
        path = self.root / use.REGISTRATION
        data = json.loads(path.read_text()); data["enabled"] = False; path.write_text(json.dumps(data))
        return value
    monkeypatch.setattr(use.RetainedHouseUsePolicy, "disclosure", revoke)
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 403


def test_wrong_generation_hash_has_no_substitution(original):
    with pytest.raises(HTTPException) as exc:
        discover(original, generation_id=original[2].generation_id, generation_sha256="0" * 64)
    assert exc.value.status_code == 503


def test_http_headers_duplicates_and_actual_brain_dispatch(original, monkeypatch):
    monkeypatch.setattr(api, "_repo_root", lambda: original[0])
    app = FastAPI(); app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "member"}
    client = TestClient(app)
    for params, expected in (({"limit": 1}, 200), ([("limit", 1), ("limit", 2)], 400)):
        response = client.get("/api/market-memory/v1/macro/retained/catalog", params=params)
        assert response.status_code == expected
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Authorization"
    from engine.neuralweb import brain_gateway as gateway, ask_brain
    result = gateway._dispatch_brain_tool("get_retained_market_catalog", {"limit": 1},
        original[0], original[0], "", user_id="member")
    assert result["schema"] == catalog.SCHEMA and result["selection"]["returned"] == 1
    assert "get_retained_market_catalog" in ask_brain._FAST_VISIBLE_TOOL_FAMILIES["macro_rates"]
    denied = gateway._dispatch_brain_tool("get_retained_market_catalog", {}, original[0], original[0], "", user_id="")
    assert denied["http_status"] == 403 and "entries" not in denied


def test_actual_other_subject_refused_before_payload(original, monkeypatch):
    actual_read = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_receipt
    def other(self, *args, **kwargs):
        receipt = actual_read(self, *args, **kwargs)
        receipt["subject"]["subject_id"] = "mmsecurity_" + "0" * 64
        return receipt
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_receipt", other)
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections",
                        lambda *a, **k: pytest.fail("denied subject loaded payload"))
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 403


def test_catalog_owner_budget_and_shared_slot_refuse_without_counts(original, monkeypatch):
    from engine.neuralweb import market_memory_pit as pit
    def exceed(*a, **k):
        raise pit.OwnerReadBudgetError("test budget")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation", exceed)
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 503 and exc.value.detail["state"] == "OWNER_READ_BUDGET_EXCEEDED"
    assert api._playback_slots.acquire(blocking=False)
    assert api._playback_slots.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as exc:
            discover(original)
        assert exc.value.status_code == 503 and exc.value.detail["state"] == "BUSY"
    finally:
        api._playback_slots.release(); api._playback_slots.release()


def test_comparison_components_are_exact_owner_values(original):
    from decimal import Decimal, ROUND_HALF_EVEN
    value = api.retained_macro_for_user(original[0], "member", original[3])
    assert len(value["neighbors"]) == 2
    for row in value["neighbors"]:
        assert set(row["components_exact_decimal"]) == set(use.FIELDS)
        assert row["comparison_id"].startswith("mmepisodecomparison_")
        parts = {k: Decimal(v) for k, v in row["components_exact_decimal"].items()}
        assert all(v == 0 for k, v in parts.items() if k != "growth_score")
        assert Decimal(row["distance_q18"]) == (sum(parts.values()) / 5).quantize(Decimal("1e-18"), rounding=ROUND_HALF_EVEN)


def test_registered_dependency_mismatch_is_typed_private_api_and_brain_failure(original, monkeypatch):
    from engine.neuralweb import market_memory_episode_retrieval as retrieval, brain_gateway as gateway
    def mismatch(self):
        raise retrieval.EpisodeRetrievalError("registered_dependency_source_mismatch")
    monkeypatch.setattr(retrieval.RetainedContextMethodSpec, "disclosure", mismatch)
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 503 and exc.value.detail["state"] == "EXACT_CATALOG_UNAVAILABLE"
    monkeypatch.setattr(api, "_repo_root", lambda: original[0])
    app = FastAPI(); app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "member"}
    response = TestClient(app).get("/api/market-memory/v1/macro/retained/catalog")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "private, no-store"
    assert "entries" not in response.json()
    result = gateway._dispatch_brain_tool("get_retained_market_catalog", {}, original[0], original[0], "", user_id="member")
    assert result["http_status"] == 503 and result["state"] == "EXACT_CATALOG_UNAVAILABLE"


def test_wrong_configured_store_refuses_before_ancestry_or_payload(original, monkeypatch):
    path = original[0] / use.REGISTRATION
    value = json.loads(path.read_text()); value["store_id"] = "mmstore_" + "0" * 64
    path.write_text(json.dumps(value))
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation",
                        lambda *a, **k: pytest.fail("wrong store opened ancestry"))
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections",
                        lambda *a, **k: pytest.fail("wrong store opened payload"))
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 503 and exc.value.detail["state"] == "EXACT_CATALOG_UNAVAILABLE"


def test_exact_capture_locator_finds_later_page_in_pinned_generation(original):
    first = discover(original, limit=20)
    target = first["entries"][-1]
    pin = {k: first["generation"][k] for k in ("generation_id", "generation_sha256")}
    selected = discover(original, limit=1, query_id=target["query_id"],
                        context_id=target["context_id"], **pin)
    assert selected["selection"]["offset"] == len(first["entries"]) - 1
    assert selected["entries"] == [target]
    assert selected["selection"]["total"] == first["selection"]["total"]


def test_exact_capture_locator_never_substitutes_missing_reference(original):
    first = discover(original)
    pin = {k: first["generation"][k] for k in ("generation_id", "generation_sha256")}
    with pytest.raises(HTTPException) as exc:
        discover(original, query_id="mmquery_" + "0" * 64,
                 context_id=first["entries"][0]["context_id"], **pin)
    assert exc.value.status_code == 404


@pytest.mark.parametrize("selector", [
    {"query_id": "mmquery_" + "0" * 64},
    {"query_id": "mmquery_" + "0" * 64, "context_id": "mmctx_" + "0" * 64},
    {"context_id": "bad"},
])
def test_incomplete_exact_capture_locator_refuses_before_owner(original, monkeypatch, selector):
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", lambda *a, **k: pytest.fail("opened owner"))
    with pytest.raises(HTTPException) as exc:
        discover(original, **selector)
    assert exc.value.status_code == 400


def _row_spec(value, query):
    """The exact catalog-to-context mapping the Brain tool instructions name."""
    method = next(m for m in value["methods"] if m["mode"] == value["mode"])
    spec = {key: query[key] for key in ("query_id", "subject_id")}
    spec.update({key: value["generation"][key]
                 for key in ("generation_id", "generation_sha256")})
    spec.update(query_cutoff=query["earliest_supported_cutoff"],
                method_spec_id=method["method_spec_id"])
    return spec


def _selected_row(original, value):
    return next(row for row in value["entries"]
                if row["query_id"] == original[3]["query_id"])


@pytest.fixture
def fractional_original(tmp_path, monkeypatch):
    from datetime import timedelta
    from engine.neuralweb.market_memory_retained_context_cohort import utc_instant
    actual_capture = trusted.capture_trusted_regime_context
    def capture_with_fractional_completion(*args, **kwargs):
        # Actual writer, with completion one microsecond after the authenticated
        # identity clock used for packet as_known_at. No receipt is rewritten.
        completed = utc_instant(kwargs["identity_evidence"].observed_at) + timedelta(microseconds=1)
        monkeypatch.setattr(trusted, "_utc_now", lambda: completed)
        return actual_capture(*args, **kwargs)
    monkeypatch.setattr(trusted, "capture_trusted_regime_context", capture_with_fractional_completion)
    return original.__wrapped__(tmp_path, monkeypatch)


@pytest.mark.parametrize("clock_name", ["as_known_at", "raw_source_observed_at",
                                      "raw_source_built_at", "feature_as_of"])
def test_premature_cutoff_stays_denied_and_row_earliest_supported_cutoff_succeeds(
        fractional_original, clock_name, caplog):
    original = fractional_original
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    value = discover(original)
    query = _selected_row(original, value)
    spec = _row_spec(value, query)
    from datetime import timedelta
    from engine.neuralweb.market_memory_retained_context_cohort import utc_instant
    exact = utc_instant(query["earliest_supported_cutoff"])
    clocks = {name: utc_instant(stamp) for name, stamp in query["clocks"].items()}
    assert max(clocks.values()) == exact
    premature = {name: stamp for name, stamp in clocks.items() if stamp < exact}
    # The owning fixture spaces captured_at after as_known_at by a fraction of
    # a second, so the newest clock a row shows short of the cutoff is still
    # premature and the two are distinguishable at sub-second resolution.
    gap = clocks["captured_at"] - clocks["as_known_at"]
    assert premature, "catalog row must carry an earlier availability clock"
    assert gap == timedelta(microseconds=1)
    raw_clocks = dict(query["clocks"])
    assert clock_name in premature
    with pytest.raises(HTTPException) as exc:
        api.retained_macro_for_user(original[0], "member",
                                    dict(spec, query_cutoff=raw_clocks[clock_name]))
    assert exc.value.status_code == 503
    assert exc.value.detail == {"state": "EXACT_RETAINED_EVIDENCE_UNAVAILABLE"}
    failures = [record.args[1] for record in caplog.records if ".failure " in record.getMessage()]
    assert [row["category"] for row in failures] == ["CUTOFF_NOT_SUPPORTED"]
    # Availability is proven first: only the cutoff is wrong, so a denial here
    # is a real cutoff refusal, never a silent move to a later clock or a
    # substitution of another row or generation.
    answer = api.retained_macro_for_user(original[0], "member", spec)
    assert answer["source_cards"][0]["context_id"] == query["context_id"]


def test_actual_brain_dispatch_consumes_exact_mapping_and_keeps_premature_denial(
        original, monkeypatch):
    monkeypatch.setattr(api, "_repo_root", lambda: original[0])
    from engine.neuralweb import brain_gateway as gateway
    from engine.neuralweb.market_memory_retained_context_cohort import utc_instant
    value = discover(original)
    query = _selected_row(original, value)
    spec = _row_spec(value, query)
    answer = gateway._dispatch_brain_tool("get_retained_market_context", spec,
        original[0], original[0], "", user_id="member")
    assert answer["source_cards"][0]["context_id"] == query["context_id"]
    raw_clocks = dict(query["clocks"])
    exact = utc_instant(query["earliest_supported_cutoff"])
    premature_name = next(name for name, stamp in raw_clocks.items()
                          if utc_instant(stamp) < exact)
    denied = gateway._dispatch_brain_tool("get_retained_market_context",
        dict(spec, query_cutoff=raw_clocks[premature_name]),
        original[0], original[0], "", user_id="member")
    assert denied["http_status"] == 503
    assert denied["state"] == "EXACT_RETAINED_EVIDENCE_UNAVAILABLE"
    assert "source_cards" not in denied and "context_id" not in denied


def test_concurrent_retained_macro_failures_stay_linked_and_reclaim_both_permits(
        original, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    from concurrent.futures import ThreadPoolExecutor
    from engine.neuralweb import market_memory_pit as pit
    errors = [pit.MarketMemoryContextNotFound("private-a"),
              pit.OwnerReadBudgetError("private-b")]
    barrier = threading.Barrier(2)
    error_lock = threading.Lock()
    def fail(_self, *args, **kwargs):
        with error_lock:
            failure = errors.pop(0)
        barrier.wait(timeout=10)
        raise failure
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader,
                        "read_pinned_generation", fail)

    def run(_index):
        try:
            api.retained_macro_for_user(original[0], "member", original[3])
            return threading.get_native_id(), None
        except HTTPException as exc:
            return threading.get_native_id(), (exc.status_code, exc.detail["state"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    worker_threads = {native for native, _outcome in results}
    assert sorted(outcome for _native, outcome in results if outcome) == [
        (404, "EXACT_CAPTURE_NOT_FOUND"), (503, "OWNER_READ_BUDGET_EXCEEDED")]
    assert "private-a" not in caplog.text and "private-b" not in caplog.text
    failures = [record.args[1] for record in caplog.records
                if ".failure " in record.getMessage()]
    assert {row["category"] for row in failures} == {
        "EXACT_CAPTURE_NOT_FOUND", "OWNER_READ_BUDGET_EXCEEDED"}
    assert len({row["seq"] for row in failures}) == 2
    assert all(row["native_thread_id"] in worker_threads for row in failures)
    assert not api._read_observation_active
    assert api._playback_slots.acquire(blocking=False)
    assert api._playback_slots.acquire(blocking=False)
    api._playback_slots.release()
    api._playback_slots.release()


def test_brain_tool_schemas_name_the_exact_catalog_to_context_mapping():
    from engine.neuralweb import brain_analogues
    catalog_text = brain_analogues.RETAINED_CATALOG_TOOL_SCHEMA["description"]
    context_text = brain_analogues.RETAINED_CONTEXT_TOOL_SCHEMA["description"]
    mapping = ("row.query_id", "row.subject_id", "catalog.generation.generation_id",
               "catalog.generation.generation_sha256", "catalog.methods",
               "method_spec_id", "query_cutoff=row.earliest_supported_cutoff")
    for token in mapping:
        assert token in catalog_text, token
        assert token in context_text, token
    clocks = ("captured_at", "as_known_at", "fraction of a second")
    for token in clocks:
        assert token in catalog_text and token in context_text, token
    guard = ("never move it later", "never substitute another row or generation",
             "never invent a timestamp", "Do not automatically retry on BUSY")
    for token in guard:
        assert token in catalog_text and token in context_text, token
    schema = brain_analogues.RETAINED_CONTEXT_TOOL_SCHEMA["input_schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"query_id", "subject_id", "generation_id",
                                       "generation_sha256", "query_cutoff", "method_spec_id"}
    assert set(schema["properties"]) == set(schema["required"]) | {"limit"}
    assert schema["properties"]["limit"] == {"type": "integer", "minimum": 1, "maximum": 8}
    cutoff = schema["properties"]["query_cutoff"]
    assert cutoff["type"] == "string" and "row.earliest_supported_cutoff" in cutoff["description"]
    assert "never widen" in cutoff["description"]
    assert "limit=2" in context_text and "once" in context_text
    assert "eligible neighbors" in context_text and "Report fewer" in context_text
    assert "no chronological substitutes" in context_text
    assert "Catalog metadata alone proves neither actual field values nor comparability" in context_text


@pytest.mark.parametrize("changes,status,state,category", [
    ({"generation_sha256": "f" * 64}, 503, "EXACT_RETAINED_EVIDENCE_UNAVAILABLE", "GENERATION_MISMATCH"),
    ({"method_spec_id": "mmretainedmethod_" + "f" * 64}, 400, "REGISTERED_METHOD_REQUIRED", "REGISTERED_METHOD_REQUIRED"),
    ({"query_id": "mmquery_" + "f" * 64}, 404, "EXACT_CAPTURE_NOT_FOUND", "EXACT_CAPTURE_NOT_FOUND"),
    ({"subject_id": "mmsecurity_" + "f" * 64}, 403, "SOURCE_USE_NOT_ADMITTED", "SOURCE_USE_NOT_ADMITTED"),
])
def test_actual_macro_refusals_keep_http_state_and_log_only_category(
        original, changes, status, state, category, caplog):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    with pytest.raises(HTTPException) as error:
        api.retained_macro_for_user(original[0], "member", {**original[3], **changes})
    assert error.value.status_code == status and error.value.detail == {"state": state}
    failures = [record.args[1] for record in caplog.records if ".failure " in record.getMessage()]
    assert len(failures) == 1 and failures[0]["category"] == category
    assert set(failures[0]) == {"tag", "seq", "native_thread_id", "category"}
    for value in changes.values():
        assert value not in caplog.text
    assert not api._read_observation_active
    assert api._playback_slots.acquire(False) and api._playback_slots.acquire(False)
    api._playback_slots.release(); api._playback_slots.release()


def test_unclassified_macro_exception_is_not_stringified_or_remapped(original, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    class UnknownFailure(RuntimeError):
        def __str__(self):
            pytest.fail("diagnostic tried to stringify private exception")
    original_error = UnknownFailure("Bearer private-value /private/path")
    def fail(*args, **kwargs):
        raise original_error
    monkeypatch.setattr(api.market_memory, "retained_macro_context", fail)
    with pytest.raises(UnknownFailure) as error:
        api.retained_macro_for_user(original[0], "member", original[3])
    assert error.value is original_error
    failures = [record.args[1] for record in caplog.records if ".failure " in record.getMessage()]
    assert len(failures) == 1 and failures[0]["category"] == "OTHER_TECHNICAL"
    assert set(failures[0]) == {"tag", "seq", "native_thread_id", "category"}
    assert "private-value" not in caplog.text and "UnknownFailure" not in caplog.text
    assert not api._read_observation_active
    assert api._playback_slots.acquire(False) and api._playback_slots.acquire(False)
    api._playback_slots.release(); api._playback_slots.release()
