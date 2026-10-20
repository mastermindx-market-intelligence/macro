from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.biocatalyst as api
from engine.company_intelligence.contracts import canonical_json_sha256
from engine.company_intelligence.events import project_catalyst_event
from engine.biocatalyst.publication import PublicGenerationPublisher
import scripts.biocatalyst_worker as worker
from tests.test_biocatalyst_wmn_publication import (
    CIK, COMPANY, CUTOFF, _wmn_inputs, _admit, _alias_correction,
    _environment_for_wmn, _published_fence, _run_fenced,
)
from tests.test_biocatalyst_worker import (
    FakeCollectorFactory, MemoryStore, NOW as _WORKER_NOW,
)

NOW = datetime(2026, 8, 1, 15, 0, 4, tzinfo=timezone.utc)
GENERATION = "ctgov_run_abcdef1234567890"


def _projection(inputs, generation_id: str = GENERATION):
    generation = SimpleNamespace(generation_id=generation_id, schema_version="1.9.0")
    return SimpleNamespace(generation=generation, what_matters_next_inputs=inputs)


def _two_event_inputs() -> dict:
    inputs = _wmn_inputs()
    first = inputs["events"][0]
    second = project_catalyst_event(
        company_id=COMPANY,
        issuer_cik=CIK,
        source_namespace="issuer_disclosure",
        native_event_key="doc_2026_08_01#claim/readout_second",
        event_family="issuer_readout_guidance",
        revision_ref="doc_2026_08_01:r1-second",
        revision_is_current=True,
        occurrence="uncorroborated",
        timing=deepcopy(first["timing"]),
        source_available_at="2026-08-01T14:00:00Z",
        observed_at="2026-08-01T14:00:02Z",
        document_refs=["doc_2026_08_01:r1-second"],
        public_evidence=[],
        asset_mentions=[],
        relationship_claims=[],
        generation_cutoff=CUTOFF,
    )
    inputs["events"].append(second)
    inputs["identity_projection"][second["event_id"]] = deepcopy(
        inputs["identity_projection"][first["event_id"]]
    )
    inputs["input_cut"]["members"].append({
        "contract_id": "company_catalyst_event.v1",
        "ref": second["event_id"],
        "sha256": canonical_json_sha256(second),
        "observed_at": second["observed_at"],
        "accepted_at": second["observed_at"],
        "availability": "available",
    })
    inputs["coverage"]["family_states"]["issuer_readout_guidance"]["observed_count"] = 2
    return inputs


@contextmanager
def _app(read_bundle, *, auth=None):
    application = FastAPI()
    application.include_router(api.router)
    application.dependency_overrides[api.require_site_full_user] = auth or (lambda: {"id": "paid"})
    original = api._read_bundle
    original_recheck = api._recheck_wmn_current
    api._read_bundle = read_bundle
    # This existing harness proves pure handler/composer behavior with supplied
    # owner artifacts. Disk admission and final rechecks are exercised through
    # the real publisher in test_biocatalyst_wmn_publication.py.
    api._recheck_wmn_current = lambda _projection: None
    try:
        with TestClient(application) as client:
            yield client
    finally:
        api._read_bundle = original
        api._recheck_wmn_current = original_recheck


def _private(response) -> None:
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def test_wmn_auth_denies_before_generation_read(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    def deny():
        raise HTTPException(401, "missing credentials", headers=api._PRIVATE_HEADERS)
    def forbidden_read():
        raise AssertionError("generation read must not occur")
    with _app(forbidden_read, auth=deny) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next")
    assert response.status_code == 401
    _private(response)


def test_wmn_old_generation_returns_owner_input_unavailable_without_breaking_trial_projection(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(None), {}
    with _app(read) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next")
    assert calls == 1
    assert response.status_code == 503
    assert response.json() == {"detail": "OWNER_INPUT_UNAVAILABLE"}
    _private(response)


def test_wmn_ready_request_reads_once_and_returns_closed_generation_bound_page(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    calls = 0
    inputs = _wmn_inputs()
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    with _app(read) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next?q=AMLX&horizon_days=90&limit=50")
    assert calls == 1
    assert response.status_code == 200
    _private(response)
    payload = response.json()
    assert payload["contract_id"] == "biocatalyst_what_matters_next.v1"
    assert payload["generation_id"] == GENERATION
    assert payload["evaluation_cutoff"] == "2026-08-01T15:00:04Z"
    assert payload["anchor_date"] == "2026-08-01"
    assert payload["query"] == {
        "view": "upcoming", "horizon_days": 90, "q": "amlx",
        "event_family": None, "lane": None, "limit": 50,
    }
    assert payload["pagination"] == {"limit": 50, "total": 1, "next_cursor": None}
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["links"]["stock_research"][0]["href"] == "stock.html?ticker=AMLX"


def test_wmn_invalid_filter_and_malformed_or_foreign_cursor_fail_before_data_io(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    def forbidden_read():
        raise AssertionError("invalid request must not read generation")
    with _app(forbidden_read) as client:
        invalid = client.get("/api/biocatalyst/v1/what-matters-next?view=bogus")
        malformed = client.get("/api/biocatalyst/v1/what-matters-next?cursor=not-a-real-cursor")
        foreign = api._encode_wmn_cursor(
            generation_id=GENERATION,
            query={"view": "upcoming", "horizon_days": 90, "q": None, "event_family": None, "lane": None, "limit": 50},
            evaluation_cutoff="2026-08-01T15:00:04Z",
            anchor_date="2026-08-01",
            last_key={"lane": "ACT_NOW", "upper_date": "2026-09-01", "lower_date": "2026-09-01", "last_material_revision_known_at": None, "event_fact_ref": "evt", "row_key": {"event_fact_ref": "evt", "issuer_id": None}},
            purpose="trial_milestones.v1",
        )
        foreign_response = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={foreign}")
    for response in (invalid, malformed, foreign_response):
        assert response.status_code == 400
        assert response.json() == {"detail": "INVALID_REQUEST"}
        _private(response)


def test_wmn_query_change_and_midnight_rollover_require_reload_before_data_io(monkeypatch) -> None:
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    query = {"view": "upcoming", "horizon_days": 90, "q": None, "event_family": None, "lane": None, "limit": 50}
    cursor = api._encode_wmn_cursor(
        generation_id=GENERATION,
        query=query,
        evaluation_cutoff="2026-08-01T15:00:04Z",
        anchor_date="2026-08-01",
        last_key={"lane": "ACT_NOW", "upper_date": "2026-09-01", "lower_date": "2026-09-01", "last_material_revision_known_at": None, "event_fact_ref": "evt", "row_key": {"event_fact_ref": "evt", "issuer_id": None}},
    )
    def forbidden_read():
        raise AssertionError("reload decision must not read generation")
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    with _app(forbidden_read) as client:
        changed = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={cursor}&q=changed")
    assert changed.status_code == 409
    assert changed.json() == {"detail": "RELOAD_REQUIRED"}

    monkeypatch.setattr(api, "_wmn_now", lambda: datetime(2026, 8, 2, 0, 0, 1, tzinfo=timezone.utc))
    with _app(forbidden_read) as client:
        midnight = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={cursor}")
    assert midnight.status_code == 409
    assert midnight.json() == {"detail": "RELOAD_REQUIRED"}


def test_wmn_generation_change_requires_reload_after_one_pointer_bound_read(monkeypatch) -> None:
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    query = {"view": "upcoming", "horizon_days": 90, "q": None, "event_family": None, "lane": None, "limit": 50}
    cursor = api._encode_wmn_cursor(
        generation_id="ctgov_run_old",
        query=query,
        evaluation_cutoff="2026-08-01T15:00:04Z",
        anchor_date="2026-08-01",
        last_key={"lane": "ACT_NOW", "upper_date": "2026-09-01", "lower_date": "2026-09-01", "last_material_revision_known_at": None, "event_fact_ref": "evt", "row_key": {"event_fact_ref": "evt", "issuer_id": None}},
    )
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(_wmn_inputs(), generation_id=GENERATION), {}
    with _app(read) as client:
        response = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={cursor}")
    assert calls == 1
    assert response.status_code == 409
    assert response.json() == {"detail": "RELOAD_REQUIRED"}


def test_wmn_cursor_paginates_by_last_complete_stable_key_not_offset(monkeypatch) -> None:
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _two_event_inputs()
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    with _app(read) as client:
        first = client.get("/api/biocatalyst/v1/what-matters-next?limit=1")
        assert first.status_code == 200
        p1 = first.json()
        assert len(p1["rows"]) == 1 and p1["pagination"]["total"] == 2
        assert p1["pagination"]["next_cursor"]
        decoded = api._decode_wmn_cursor(p1["pagination"]["next_cursor"])
        assert "offset" not in decoded
        assert set(decoded["last_key"]) == {"lane", "upper_date", "lower_date", "last_material_revision_known_at", "event_fact_ref", "row_key"}
        second = client.get(f"/api/biocatalyst/v1/what-matters-next?limit=1&cursor={p1['pagination']['next_cursor']}")
        assert second.status_code == 200
        p2 = second.json()
    assert calls == 2
    assert len(p2["rows"]) == 1
    assert p2["pagination"] == {"limit": 1, "total": 2, "next_cursor": None}
    assert p1["rows"][0]["event_fact_ref"] != p2["rows"][0]["event_fact_ref"]


def test_wmn_detail_returns_same_generation_company_event_and_related_rows(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _two_event_inputs()
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    event_id = inputs["events"][0]["event_id"]
    with _app(read) as client:
        response = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": GENERATION, "event_fact_ref": event_id},
        )
    assert calls == 1
    assert response.status_code == 200
    _private(response)
    payload = response.json()
    assert payload["contract_id"] == "biocatalyst_wmn_detail.v1"
    assert payload["generation_id"] == GENERATION
    assert payload["event"]["event_fact_ref"] == event_id
    assert payload["trial"] is None
    assert payload["reason_codes"] == ["non_registry_event"]
    assert len(payload["related_events"]) == 1
    assert payload["related_events"][0]["event_fact_ref"] != event_id


def test_wmn_detail_generation_race_and_absent_event_are_typed(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _wmn_inputs()
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    with _app(read) as client:
        race = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": "ctgov_run_old", "event_fact_ref": inputs["events"][0]["event_id"]},
        )
        missing = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": GENERATION, "event_fact_ref": "evt_source_" + "f" * 64},
        )
    assert calls == 2
    assert race.status_code == 409 and race.json() == {"detail": "RELOAD_REQUIRED"}
    assert missing.status_code == 404 and missing.json() == {"detail": "EVENT_NOT_IN_GENERATION"}
    _private(race); _private(missing)


def test_wmn_detail_owner_contract_error_is_503_not_invalid_request(monkeypatch) -> None:
    inputs = _wmn_inputs()
    projection = _projection(inputs)
    monkeypatch.setattr(api, "_wmn_now", lambda: datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc))
    _build_detail, contract_error = api._wmn_detail_runtime()
    monkeypatch.setattr(
        api,
        "_wmn_detail_runtime",
        lambda: (lambda *args, **kwargs: (_ for _ in ()).throw(contract_error("bad owner cut")), contract_error),
    )
    with _app(lambda: (projection, {})) as client:
        response = client.get(
            f"/api/biocatalyst/v1/what-matters-next/detail?generation_id={GENERATION}&event_fact_ref=evt"
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "OWNER_INPUT_UNAVAILABLE"}


def test_wmn_detail_invalid_request_and_auth_fail_before_generation_read(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    def forbidden_read():
        raise AssertionError("must not read generation")
    with _app(forbidden_read) as client:
        invalid = client.get("/api/biocatalyst/v1/what-matters-next/detail")
    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "INVALID_REQUEST"}

    def deny():
        raise HTTPException(401, "missing credentials", headers=api._PRIVATE_HEADERS)
    with _app(forbidden_read, auth=deny) as client:
        denied = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": GENERATION, "event_fact_ref": "evt_source_" + "a" * 64},
        )
    assert denied.status_code == 401
    _private(denied)


def _registry_projection(inputs):
    fixture = Path(__file__).resolve().parents[1] / "data/biocatalyst/fixtures/clinicaltrials/trial_snapshot.v1.valid.json"
    snapshot = json.loads(fixture.read_text(encoding="utf-8"))
    generation = SimpleNamespace(generation_id=GENERATION, schema_version="1.9.0")
    return SimpleNamespace(
        generation=generation,
        what_matters_next_inputs=inputs,
        trials=(snapshot,),
        history_models_by_nct={},
        change_tapes_by_nct={},
    )


def test_wmn_registry_milestone_is_same_generation_reconcile_row_and_detail(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _wmn_inputs()
    calls = 0

    def read():
        nonlocal calls
        calls += 1
        return _registry_projection(inputs), {}

    with _app(read) as client:
        page = client.get(
            "/api/biocatalyst/v1/what-matters-next",
            params={"view": "reconcile", "event_family": "registry_primary_completion"},
        )
        assert page.status_code == 200
        payload = page.json()
        registry_rows = [
            row for row in payload["rows"]
            if row["event_family"] == "registry_primary_completion"
        ]
        assert len(registry_rows) == 1
        row = registry_rows[0]
        assert row["event_fact_ref"] == "nct:NCT00000001:primary_completion"
        assert row["event_revision_ref"] == "trial_snapshot_NCT00000001_after"
        assert row["occurrence"] == "uncorroborated"
        assert row["timing"]["source_class"] == "registry_schedule"
        assert row["issuer"]["state"] == "unresolved"
        assert row["links"]["stock_research"] == []
        assert row["research_priority"]["lane"] == "RECONCILE"
        assert payload["coverage"]["family_states"]["registry_primary_completion"]["state"] == "supported"

        detail = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={
                "generation_id": GENERATION,
                "event_fact_ref": row["event_fact_ref"],
            },
        )
    assert calls == 2
    assert detail.status_code == 200
    _private(page)
    _private(detail)
    dossier = detail.json()
    assert dossier["event"]["event_fact_ref"] == row["event_fact_ref"]
    assert dossier["trial"]["nct_id"] == "NCT00000001"
    assert dossier["trial"]["brief_title"] == "Synthetic Phase 2 Study"
    assert dossier["reason_codes"] == []



def test_selected_legacy_v1_keeps_trial_api_readable_but_refuses_current_wmn(tmp_path, monkeypatch):
    from tests.test_biocatalyst_wmn_publication import _install_legacy_v1_generation

    public_root = tmp_path / "public"
    capture = _install_legacy_v1_generation(public_root)
    monkeypatch.setattr(api, "_PUBLIC_ROOT", public_root)
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    before_pointer = (public_root / "current.json").read_bytes()
    # Use the real pointer-bound reader and historical artifact materialization.
    # This existing harness replaces authentication and the new admission gate
    # to isolate R9's current-composer refusal of v1. Fence migration itself is
    # tested below with _disk_wmn_client and the actual eligibility gate.
    with _app(api._read_bundle) as client:
        trial_before = client.get("/api/biocatalyst/v1/trials")
        page = client.get("/api/biocatalyst/v1/what-matters-next")
        detail = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": capture["generation_id"], "event_fact_ref": "evt_source_" + "a" * 64},
        )
        trial_after = client.get("/api/biocatalyst/v1/trials")
    assert trial_before.status_code == 200
    assert trial_after.status_code == 200
    assert trial_after.json() == trial_before.json()
    trials = trial_before.json()["trials"]
    assert len(trials) == 1 and trials[0]["nct_id"] == "NCT00000001"
    assert trials[0]["brief_title"] == "Synthetic Phase 2 Study"
    for response in (page, detail):
        assert response.status_code == 503
        assert response.json() == {"detail": "OWNER_INPUT_UNAVAILABLE"}
        _private(response)
    assert (public_root / "current.json").read_bytes() == before_pointer


# Real publisher and API correction-fence witnesses.

def _disk_wmn_client(monkeypatch, public_root):
    from contextlib import contextmanager
    from datetime import timedelta
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.biocatalyst as api
    from engine.biocatalyst.publication import PublicationError

    @contextmanager
    def client():
        application = FastAPI()
        application.include_router(api.router)
        # Synthetic entitlement and runtime-import seams only. The generation,
        # admission state, real bundle reader, composer and final gate are used.
        application.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-paid"}
        with monkeypatch.context() as patch:
            patch.setattr(api, "_PUBLIC_ROOT", public_root)
            patch.setattr(api, "_publication_runtime",
                          lambda: (PublicationError, PublicGenerationPublisher))
            patch.setattr(api, "_wmn_now", lambda: _WORKER_NOW + timedelta(minutes=1))
            with TestClient(application) as connection:
                yield connection

    return client()


def _detail_query(page):
    row = page["rows"][0]
    query = {
        "generation_id": page["generation_id"],
        "event_fact_ref": row["event_fact_ref"],
    }
    if row.get("issuer_id") is not None:
        query["issuer_id"] = row["issuer_id"]
    return query


def _assert_wmn_unavailable(client, detail_query):
    for route, params in (
        ("/api/biocatalyst/v1/what-matters-next", {}),
        ("/api/biocatalyst/v1/what-matters-next/detail", detail_query),
    ):
        response = client.get(route, params=params)
        assert response.status_code == 503
        assert response.json() == {"detail": "OWNER_INPUT_UNAVAILABLE"}
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Authorization"


def test_correction_admits_while_old_build_locked_and_failed_replacement_stays_unavailable(
    tmp_path, monkeypatch
):
    from engine.biocatalyst.publication import PublicationError

    state_root, public_root, environ = _environment_for_wmn(tmp_path)
    owner_path = tmp_path / "owner-inputs.json"
    inputs = _wmn_inputs()
    owner_path.write_text(json.dumps(inputs), encoding="utf-8")
    monkeypatch.setattr(worker, "_SERVICE_STATE_ROOT", state_root)
    monkeypatch.setattr(worker, "_SERVICE_PUBLIC_ROOT", public_root)
    monkeypatch.setattr(worker, "_SERVICE_WMN_INPUTS_PATH", owner_path)
    first_run = worker.run_from_environment(
        environ, collector_factory=FakeCollectorFactory(),
        store_factory=lambda _: MemoryStore(), now_fn=lambda: _WORKER_NOW,
    )
    assert first_run.exit_code == worker.EXIT_SUCCESS
    cfg = worker.load_environment(environ).config
    publisher = PublicGenerationPublisher(public_root)
    first = publisher.capture_wmn_admission()
    pointer_before = publisher.pointer_path.read_bytes()
    corrected = _alias_correction(inputs)
    observed = {}

    with _disk_wmn_client(monkeypatch, public_root) as client:
        first_page = client.get("/api/biocatalyst/v1/what-matters-next")
        assert first_page.status_code == 200
        detail_query = _detail_query(first_page.json())

        class InterveningPublisher(PublicGenerationPublisher):
            def write_pointer(self, prepared):
                observed["prepared"] = prepared
                owner_path.write_text(json.dumps(corrected), encoding="utf-8")
                busy = worker.run_from_environment(
                    environ, collector_factory=FakeCollectorFactory(),
                    store_factory=lambda _: MemoryStore(), now_fn=lambda: _WORKER_NOW,
                )
                assert busy.status == "locked"
                observed["second"] = self.capture_wmn_admission()
                assert observed["second"].sequence == first.sequence + 1
                super().write_pointer(prepared)

        obsolete = _run_fenced(
            cfg, inputs, first, watermark="2026-08-01T15:00:10Z",
            publisher_factory=InterveningPublisher,
        )
        assert obsolete.error_code == "WMN_ADMISSION_CHANGED"
        assert publisher.pointer_path.read_bytes() == pointer_before

        def failed_collection(**_):
            raise OSError("offline corrected collection fault")

        failed = worker.run_from_environment(
            environ, collector_factory=failed_collection,
            store_factory=lambda _: MemoryStore(), now_fn=lambda: _WORKER_NOW,
        )
        assert failed.exit_code == worker.EXIT_FAILED
        assert publisher.pointer_path.read_bytes() == pointer_before
        restarted = PublicGenerationPublisher(public_root)
        assert restarted.capture_wmn_admission() == observed["second"]
        assert restarted.read_trial_projection().trials
        _assert_wmn_unavailable(client, detail_query)
        assert client.get("/api/biocatalyst/v1/trials").status_code == 200

        replacement = _run_fenced(
            cfg, corrected, observed["second"], watermark="2026-08-01T15:00:20Z"
        )
        assert replacement.exit_code == worker.EXIT_SUCCESS
        assert client.get("/api/biocatalyst/v1/what-matters-next").status_code == 200
        with pytest.raises(PublicationError, match="WMN_ADMISSION_CHANGED"):
            restarted.write_pointer(observed["prepared"])


@pytest.mark.parametrize("detail", [False, True], ids=["list", "detail"])
def test_api_rejects_correction_admitted_during_composition(tmp_path, monkeypatch, detail):
    import app.biocatalyst as api

    cfg, publisher, inputs, _ticket = _published_fence(tmp_path)
    with _disk_wmn_client(monkeypatch, cfg.public_root) as client:
        initial = client.get("/api/biocatalyst/v1/what-matters-next")
        assert initial.status_code == 200
        params = _detail_query(initial.json()) if detail else {}
        runtime = api._wmn_detail_runtime() if detail else api._wmn_runtime()
        observed = []

        def correcting_composer(*args, **kwargs):
            payload = runtime[0](*args, **kwargs)
            observed.append(_admit(publisher, _alias_correction(inputs)))
            return payload

        target = "_wmn_detail_runtime" if detail else "_wmn_runtime"
        monkeypatch.setattr(api, target, lambda: (correcting_composer, *runtime[1:]))
        route = "/api/biocatalyst/v1/what-matters-next" + ("/detail" if detail else "")
        response = client.get(route, params=params)
        assert len(observed) == 1
        assert response.status_code == 503
        assert response.json() == {"detail": "OWNER_INPUT_UNAVAILABLE"}
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Authorization"


def test_pointer_rollback_never_rolls_back_the_admitted_correction(tmp_path, monkeypatch):
    cfg, publisher, inputs, _first = _published_fence(tmp_path)
    before = publisher.pointer_path.read_bytes()
    corrected = _alias_correction(inputs)
    second = _admit(publisher, corrected)

    def fail_after_replace(_path):
        raise OSError("post-replace durability fault")

    result = _run_fenced(
        cfg, corrected, second, watermark="2026-08-01T15:00:10Z",
        publisher_factory=lambda path: PublicGenerationPublisher(
            path, pointer_after_replace_hook=fail_after_replace
        ),
    )
    assert result.error_code == "POINTER_WRITE_FAILED"
    assert publisher.pointer_path.read_bytes() == before
    restarted = PublicGenerationPublisher(cfg.public_root)
    assert restarted.capture_wmn_admission() == second
    projection = restarted.read_trial_projection()
    assert projection.trials
    with _disk_wmn_client(monkeypatch, cfg.public_root) as client:
        _assert_wmn_unavailable(client, {
            "generation_id": projection.generation.generation_id,
            "event_fact_ref": inputs["events"][0]["event_id"],
        })


@pytest.mark.parametrize("damage", ["missing", "malformed"])
def test_admission_state_loss_is_not_reinitialized_and_does_not_erase_trial_facts(
    tmp_path, monkeypatch, damage
):
    from engine.biocatalyst.publication import PublicationError

    cfg, publisher, inputs, _ticket = _published_fence(tmp_path)
    if damage == "missing":
        publisher.wmn_admission_path.unlink()
    else:
        publisher.wmn_admission_path.write_text("{}", encoding="utf-8")
    restarted = PublicGenerationPublisher(cfg.public_root)
    with pytest.raises(PublicationError, match="WMN_ADMISSION_STATE_"):
        restarted.initialize_wmn_admission()
    projection = restarted.read_trial_projection()
    assert projection.trials
    with _disk_wmn_client(monkeypatch, cfg.public_root) as client:
        _assert_wmn_unavailable(client, {
            "generation_id": projection.generation.generation_id,
            "event_fact_ref": inputs["events"][0]["event_id"],
        })
        assert client.get("/api/biocatalyst/v1/trials").status_code == 200


def test_old_pointer_with_v2_artifact_requires_fenced_republication(tmp_path, monkeypatch):
    cfg, publisher, inputs, ticket = _published_fence(tmp_path)
    pointer = json.loads(publisher.pointer_path.read_text())
    artifact = (cfg.public_root / "generations" / pointer["generation_id"]
                / "what_matters_next_inputs.json")
    original_artifact = artifact.read_bytes()
    pointer.pop("wmn_admission")
    pointer["schema_version"] = "1.0.0"
    publisher.pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
    assert publisher.read_trial_projection().trials
    assert artifact.read_bytes() == original_artifact
    with _disk_wmn_client(monkeypatch, cfg.public_root) as client:
        _assert_wmn_unavailable(client, {
            "generation_id": pointer["generation_id"],
            "event_fact_ref": inputs["events"][0]["event_id"],
        })
        result = _run_fenced(
            cfg, inputs, ticket, watermark="2026-08-01T15:00:10Z"
        )
        assert result.exit_code == worker.EXIT_SUCCESS
        assert client.get("/api/biocatalyst/v1/what-matters-next").status_code == 200
