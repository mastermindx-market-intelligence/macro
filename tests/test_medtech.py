"""MedTech source integrity, PIT, publication, and authenticated consumer regressions.

All rows in this file are synthetic fixtures, not claims about actual devices.
Live acquisition is exercised separately by the bounded worker qualification.
"""
from copy import deepcopy
from datetime import datetime, timezone
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from collectors.medtech.openfda import MAX_PAGE_BYTES, SourceBatch, fetch_batch, request_url
from engine.medtech.events import EVENT_ID_RE, MedTechError, normalize_record
from engine.medtech.publication import (
    publish_snapshot, read_snapshot, record_attempt, validate_snapshot,
)
from engine.medtech.store import EventStore

T1 = "2026-10-10T12:00:00.000000Z"
T2 = "2026-10-11T12:00:00.000000Z"
T3 = "2026-10-12T12:00:00.000000Z"


def row(dataset="510k", **changes):
    result = {
        "applicant": "Fixture Devices (test only)", "decision_date": "2026-10-01",
        "date_received": "2026-01-02", "product_code": "ABC",
    }
    result.update({"k_number": "K260001", "device_name": "Fixture monitor",
                   "decision_code": "SESE", "decision_description": "Substantially Equivalent"}
                  if dataset == "510k" else
                  {"pma_number": "P260001", "supplement_number": "",
                   "trade_name": "Fixture implant", "decision_code": "APPR",
                   "supplement_type": "", "supplement_reason": ""})
    result.update(changes)
    return result


def batch(rows=None, *, dataset="510k", when=T1):
    rows = [row(dataset)] if rows is None else rows
    raw = json.dumps({
        "meta": {"last_updated": "2026-10-05",
                 "results": {"skip": 0, "limit": 1000, "total": len(rows)}},
        "results": rows,
    }).encode()
    if not rows:
        raw = b'{"error":{"code":"NOT_FOUND","message":"No matches found!"}}'
    return SourceBatch(dataset, "2026-10-01", "2026-10-05", when,
                       "2026-10-05" if rows else "", len(rows), (raw,),
                       (request_url(dataset, "2026-10-01", "2026-10-05", 0, page_size=1000),))


def snapshot(tmp_path):
    with EventStore(tmp_path / "private" / "events.sqlite3", create=True) as store:
        store.ingest(batch())
        return store.snapshot(as_of=T1)


def normal(dataset="510k", **kwargs):
    return normalize_record(dataset, row(dataset, **kwargs),
                            observed_at=T1, dataset_updated_at="2026-10-05")


@pytest.mark.parametrize("code,status", [
    ("APPR", "approved"), ("WTDR", "withdrawn"), ("DENY", "denied"),
    ("LE30", "notice_accepted"), ("APWD", "approval_withdrawn"),
    ("GT30", "notice_pending"), ("OK30", "unmapped"), ("FUTURE", "unmapped"),
])
def test_pma_exact_codes_do_not_infer_approval(code, status):
    observed = normal("pma", decision_code=code, supplement_number="S001")
    assert observed.event["decision"]["status"] == status
    assert observed.event["pathway"] == "pma_supplement"
    assert observed.event["next_milestone"] is None
    assert observed.event["company_link"] == {"status": "not_joined"}



@pytest.mark.parametrize("dataset,changes,event_id,pathway,status,url_suffix", [
    ("510k", {"k_number": "DEN260001", "decision_code": "DENG"},
     "fda-510k-DEN260001", "de_novo", "granted", "/cfpmn/denovo.cfm?id=DEN260001"),
    ("pma", {"pma_number": "N12345", "supplement_number": "S001", "decision_code": "OK30"},
     "fda-pma-N12345-S001", "other_device_submission", "unmapped", "/cfpma/pma.cfm?id=N12345S001"),
])
def test_observed_native_id_shapes_publish_and_resolve_exact_subject(
        tmp_path, api, dataset, changes, event_id, pathway, status, url_suffix):
    client, _, root, _ = api
    with EventStore(tmp_path / "native.sqlite3", create=True) as store:
        store.ingest(batch([row(dataset, **changes)], dataset=dataset, when=T2))
        payload = store.snapshot(as_of=T2)
    generation = publish_snapshot(root, payload)
    assert read_snapshot(root) == (payload, generation)
    detail = client.get(f"/api/medtech/events/{event_id}?snapshot_id={generation}")
    assert detail.status_code == 200
    event = detail.json()["event"]
    assert event["event_id"] == event_id
    assert event["pathway"] == pathway
    assert event["decision"]["status"] == status
    assert event["source"]["url"].endswith(url_suffix)
    subject = client.get(f"/api/medtech/subjects/event/{event_id}?snapshot_id={generation}")
    assert subject.status_code == 200
    assert subject.json()["allowed_triggers"] == ["record_changed"]
    wrong = deepcopy(payload)
    wrong["events"][0]["source"]["url"] = (
        "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K260001"
    )
    with pytest.raises(MedTechError, match="PUBLIC_SCHEMA_INVALID"):
        validate_snapshot(wrong)


@pytest.mark.parametrize("number,code", [("DEN260001", "SESE"), ("K260001", "DENG")])
def test_de_novo_grant_and_510k_clearance_codes_do_not_cross_pathways(number, code):
    assert normal(k_number=number, decision_code=code).event["decision"]["status"] == "unmapped"


@pytest.mark.parametrize("dataset,changes", [
    ("510k", {"k_number": "DEN26001"}),
    ("510k", {"k_number": "N12345"}),
    ("pma", {"pma_number": "DEN260001"}),
    ("pma", {"pma_number": "P12345"}),
    ("pma", {"pma_number": "N1234"}),
])
def test_native_id_expansion_keeps_dataset_and_length_constraints(dataset, changes):
    with pytest.raises(MedTechError):
        normal(dataset, **changes)


@pytest.mark.parametrize("event_id", [
    "fda-pma-DEN260001", "fda-510k-N12345", "fda-510k-DEN260001-S001",
    "fda-510k-K260001-S001", "fda-pma-P12345", "fda-pma-N12345-S001\n",
])
def test_event_id_grammar_rejects_cross_dataset_or_ambiguous_ids(event_id):
    assert EVENT_ID_RE.fullmatch(event_id) is None


def test_parent_supplement_and_other_application_are_distinct():
    original = normal("pma")
    supplement = normal("pma", supplement_number="S001", supplement_type="Panel Track")
    other = normal("pma", pma_number="N970003", supplement_number="S311", decision_code="OK30")
    assert len({x.event_id for x in (original, supplement, other)}) == 3
    assert original.event["pathway"] == "pma_original"
    assert supplement.event["pathway"] == "pma_panel_track_supplement"
    assert supplement.event["parent_submission_id"] == "P260001"
    assert other.event["pathway"] == "other_device_submission"
    assert other.event["decision"]["status"] == "unmapped"


@pytest.mark.parametrize("changes", [
    {"decision_date": "2026-11-01"}, {"decision_date": "2026-02-30"},
    {"date_received": "2026-10-03"}, {"k_number": "../../secret"},
    {"device_name": ["unexpected", "array"]},
])
def test_invalid_source_records_fail_closed(changes):
    with pytest.raises(MedTechError):
        normal(**changes)


def test_publication_time_is_not_fabricated():
    observed = normal()
    assert observed.event["source"]["source_published_at"] is None
    assert observed.event["decision"]["date_precision"] == "day"
    assert observed.observed_at == T1
    assert observed.dataset_updated_at == "2026-10-05"


def test_first_observation_unchanged_refetch_and_reversion(tmp_path):
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        first = store.ingest(batch())
        assert first["new_versions"] == 1
        assert store.ingest(batch())["replayed"] is True
        assert store.ingest(batch(when=T2))["new_versions"] == 0
        assert store.snapshot(as_of=T2)["events"][0]["last_observed_at"] == T2
        corrected = row(device_name="Corrected fixture monitor")
        store.ingest(batch([corrected], when=T3))
        t4 = "2026-10-13T12:00:00.000000Z"
        store.ingest(batch(when=t4))
        present = store.snapshot(as_of=t4)["events"][0]
        assert len(present["history"]) == 3
        assert present["first_observed_at"] == T1
        assert present["history"][0]["kind"] == "first_observed"
        assert present["history"][0]["changes"] == []
        assert present["device"]["name"] == "Fixture monitor"
        assert store.snapshot(as_of=T2)["events"][0]["device"]["name"] == "Fixture monitor"
        assert store.snapshot(as_of=T3)["events"][0]["device"]["name"] == "Corrected fixture monitor"
        assert store.snapshot(as_of="2026-10-09T00:00:00Z")["events"] == []
        change = present["history"][1]["changes"][0]
        assert change["before_value"] == "Fixture monitor"
        assert change["after_value"] == "Corrected fixture monitor"
        assert change["change_family"] == "device"
        assert store.db.execute("SELECT count(*) FROM source_pages").fetchone()[0] == 4


def test_raw_private_and_cosmetic_changes_are_not_product_updates(tmp_path):
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        store.ingest(batch())
        store.ingest(batch([row(device_name="  Fixture  monitor ", contact="PRIVATE CONTACT")], when=T2))
        payload = store.snapshot(as_of=T2)
        assert len(payload["events"][0]["history"]) == 1
        assert "PRIVATE CONTACT" not in json.dumps(payload)
        assert store.db.execute("SELECT count(*) FROM source_pages").fetchone()[0] == 2


def test_clock_regression_and_duplicate_identity_rollback(tmp_path):
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        store.ingest(batch(when=T2))
        with pytest.raises(MedTechError, match="CLOCK_REGRESSION"):
            store.ingest(batch(when=T1))
        with pytest.raises(MedTechError, match="SOURCE_DUPLICATE_ID"):
            store.ingest(batch([row(), row(device_name="Conflicting")], when=T3))
        assert store.db.execute("SELECT count(*) FROM acquisitions").fetchone()[0] == 1


def test_missing_records_do_not_tombstone_history(tmp_path):
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        store.ingest(batch())
        store.ingest(batch([], when=T2))
        payload = store.snapshot(as_of=T2)
        assert len(payload["events"]) == 1
        assert payload["events"][0]["last_observed_at"] == T1
        assert payload["sources"][0]["coverage"]["records"] == 0


def test_incomplete_batch_is_never_committed(tmp_path):
    original = batch()
    obj = json.loads(original.pages[0])
    obj["meta"]["results"]["total"] = 2
    bad = SourceBatch(original.dataset, original.start, original.end, original.observed_at,
                      original.dataset_updated_at, 2, (json.dumps(obj).encode(),),
                      original.request_urls)
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        with pytest.raises(MedTechError):
            store.ingest(bad)
        assert store.db.execute("SELECT count(*) FROM acquisitions").fetchone()[0] == 0


def test_existing_unreadable_or_wrong_schema_store_is_not_replaced(tmp_path):
    path = tmp_path / "bad.sqlite3"
    path.write_bytes(b"retained evidence, not a valid database")
    with pytest.raises(MedTechError):
        EventStore(path, create=True)
    assert path.read_bytes() == b"retained evidence, not a valid database"


def test_verified_generation_and_failed_refresh_keep_last_good(tmp_path):
    root, payload = tmp_path / "public", snapshot(tmp_path)
    generation = publish_snapshot(root, payload)
    assert read_snapshot(root) == (payload, generation)
    invalid = deepcopy(payload)
    invalid["events"][0]["secret"] = "worker path"
    with pytest.raises(MedTechError):
        publish_snapshot(root, invalid)
    assert read_snapshot(root)[1] == generation
    older = deepcopy(payload)
    older["generated_at"] = "2026-10-09T12:00:00Z"
    with pytest.raises(MedTechError):
        publish_snapshot(root, older)
    assert read_snapshot(root)[1] == generation
    assert publish_snapshot(root, payload) == generation


@pytest.mark.parametrize("mutate", [
    lambda p: p["events"][0]["device"].update({"raw_path": "/private/file"}),
    lambda p: p["events"][0]["source"].update({"url": "http://127.0.0.1/secret"}),
    lambda p: p["events"][0].update({"next_milestone": {"date": "2026-11-01"}}),
    lambda p: p["events"][0].update({"company_link": {"ticker": "GUESS"}}),
    lambda p: p["events"][0].update({"last_observed_at": "2027-01-01T00:00:00Z"}),
])
def test_public_projection_rejects_private_or_invented_facts(tmp_path, mutate):
    payload = snapshot(tmp_path)
    mutate(payload)
    with pytest.raises(MedTechError):
        validate_snapshot(payload)


def test_digest_and_symlink_fail_closed(tmp_path):
    root, payload = tmp_path / "public", snapshot(tmp_path)
    generation = publish_snapshot(root, payload)
    target = root / "generations" / (generation + ".json")
    target.write_bytes(b"{}")
    with pytest.raises(MedTechError):
        read_snapshot(root)
    target.unlink()
    secret = tmp_path / "secret.json"
    secret.write_text("{}")
    target.symlink_to(secret)
    with pytest.raises(MedTechError):
        read_snapshot(root)


class Response:
    def __init__(self, obj, status=200):
        self.status_code, self.raw = status, json.dumps(obj).encode()
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def iter_content(self, chunk_size):
        yield self.raw


class Session:
    def __init__(self, responses):
        self.responses, self.calls = responses, []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def fetch(session, **kwargs):
    return fetch_batch("510k", start="2026-10-01", end="2026-10-05", session=session,
                       clock=lambda: datetime(2026, 10, 10, 12, tzinfo=timezone.utc),
                       pause=lambda _: None, **kwargs)



class PagedSession:
    def __init__(self, records):
        self.records, self.calls = records, []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        query = parse_qs(urlsplit(url).query)
        skip, limit = int(query["skip"][0]), int(query["limit"][0])
        return Response({
            "meta": {"last_updated": "2026-10-05",
                     "results": {"skip": skip, "limit": limit, "total": len(self.records)}},
            "results": self.records[skip:skip + limit],
        })


def test_bulky_source_records_complete_multiple_bounded_pages(tmp_path):
    # The former 1,000-record request exceeds 8 MiB for this ordinary source
    # shape. Smaller requests must retain every row and the final partial page.
    records = [row(k_number=f"K{260000 + i:06d}", extra_source_detail="x" * 17000)
               for i in range(501)]
    session = PagedSession(records)
    captured = fetch(session)
    queries = [parse_qs(urlsplit(url).query) for url, _ in session.calls]
    assert [query["skip"] for query in queries] == [["0"], ["250"], ["500"]]
    assert all(query["limit"] == ["250"] for query in queries)
    assert captured.page_size == 250
    assert captured.total == 501
    assert all(len(page) <= MAX_PAGE_BYTES for page in captured.pages)
    assert [record["k_number"] for record in captured.records()] == [
        record["k_number"] for record in records
    ]
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        assert store.ingest(captured)["new_versions"] == 501
        assert len(store.snapshot(as_of=T1)["events"]) == 501


def test_retained_thousand_record_pages_keep_their_original_request_evidence(tmp_path):
    records = [row(k_number=f"K{260000 + i:06d}") for i in range(1001)]
    session = PagedSession(records)
    urls = tuple(request_url("510k", "2026-10-01", "2026-10-05", offset, page_size=1000)
                 for offset in (0, 1000))
    pages = tuple(session.get(url).raw for url in urls)
    captured = SourceBatch("510k", "2026-10-01", "2026-10-05", T1,
                           "2026-10-05", len(records), pages, urls)
    assert captured.page_size == 1000
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        assert store.ingest(captured)["new_versions"] == 1001
        assert store.db.execute("SELECT count(*) FROM source_pages").fetchone()[0] == 2
    assert captured.pages == pages and captured.request_urls == urls


@pytest.mark.parametrize("fault", ["page_size", "second_offset"])
def test_retained_page_width_and_offsets_must_match_before_commit(tmp_path, fault):
    captured = fetch(PagedSession([row(k_number=f"K{260000 + i:06d}") for i in range(251)]))
    if fault == "page_size":
        captured = replace(captured, page_size=1000)
    else:
        captured = replace(captured, request_urls=(captured.request_urls[0],
            request_url("510k", "2026-10-01", "2026-10-05", 249)))
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        with pytest.raises(MedTechError, match="SOURCE_REQUEST_MISMATCH"):
            store.ingest(captured)
        assert store.db.execute("SELECT count(*) FROM acquisitions").fetchone()[0] == 0


@pytest.mark.parametrize("page_size", [True, 0, 1001])
def test_retained_page_size_rejects_invalid_bounds(tmp_path, page_size):
    with EventStore(tmp_path / "store.sqlite3", create=True) as store:
        with pytest.raises(MedTechError, match="SOURCE_PAGE_SIZE_INVALID"):
            store.ingest(replace(batch(), page_size=page_size))
        assert store.db.execute("SELECT count(*) FROM acquisitions").fetchone()[0] == 0


def test_one_oversized_source_record_still_fails_without_retry():
    session = PagedSession([row(extra_source_detail="x" * MAX_PAGE_BYTES)])
    with pytest.raises(MedTechError, match="SOURCE_RESPONSE_TOO_LARGE"):
        fetch(session)
    assert len(session.calls) == 1


def test_http_empty_is_explicit_and_has_no_invented_dataset_clock():
    session = Session([Response({"error": {"code": "NOT_FOUND", "message": "No matches found!"}}, 404)])
    captured = fetch(session)
    assert captured.total == 0
    assert captured.dataset_updated_at == ""
    assert captured.page_size == 250
    assert parse_qs(urlsplit(captured.request_urls[0]).query)["limit"] == ["250"]
    assert len(session.calls) == 1
    assert session.calls[0][1]["allow_redirects"] is False


@pytest.mark.parametrize("status", [301, 401, 403, 429, 500, 503])
def test_http_failures_do_not_retry_or_become_empty(status):
    session = Session([Response({"error": {"code": "FAIL"}}, status)])
    with pytest.raises(MedTechError, match="SOURCE_HTTP_"):
        fetch(session)
    assert len(session.calls) == 1


def test_short_page_is_rejected_before_extra_requests():
    obj = json.loads(batch().pages[0])
    obj["meta"]["results"]["total"] = 2000
    session = Session([Response(obj)])
    with pytest.raises(MedTechError):
        fetch(session)
    assert len(session.calls) == 1


@pytest.fixture
def api(tmp_path, monkeypatch):
    from app import medtech
    root, payload = tmp_path / "public", snapshot(tmp_path)
    publish_snapshot(root, payload)
    monkeypatch.setenv("MEDTECH_PUBLIC_ROOT", str(root))
    app = FastAPI()
    app.include_router(medtech.router)
    app.dependency_overrides[medtech.require_medtech_user] = lambda: {"id": "fixture-user"}
    return TestClient(app), app, root, payload


def test_list_search_detail_and_changes_share_generation(api):
    client, _, _, _ = api
    listing = client.get("/api/medtech/events?q=FIXTURE").json()
    assert listing["total"] == 1
    generation = listing["snapshot_id"]
    event_id = listing["items"][0]["event_id"]
    detail = client.get(f"/api/medtech/events/{event_id}?snapshot_id={generation}").json()
    assert detail["event"]["event_id"] == event_id
    assert detail["latest_change"]["kind"] == "first_observed"
    changes = client.get(f"/api/medtech/events/{event_id}/changes").json()
    assert changes["items"][0]["changes"] == []
    assert "history" not in listing["items"][0]
    assert client.get("/api/medtech/events?q=missing").json()["total"] == 0


def test_generation_mismatch_and_unbound_pagination_are_explicit(api):
    client, _, _, _ = api
    assert client.get("/api/medtech/events?snapshot_id=" + "0" * 64).status_code == 409
    assert client.get("/api/medtech/events?offset=1").status_code == 400
    assert client.get("/api/medtech/events?limit=101").status_code == 400
    assert client.get("/api/medtech/events?pathway=invented").status_code == 400


def test_auth_happens_before_publication_read_and_errors_are_private(api, monkeypatch):
    from app import medtech
    client, app, _, _ = api
    read = []
    monkeypatch.setattr(medtech, "read_snapshot", lambda _: read.append(True))
    def denied():
        raise HTTPException(401, "secret upstream detail")
    app.dependency_overrides[medtech.require_medtech_user] = denied
    for endpoint in ("/health", "/events", "/events/fda-510k-K260001",
                     "/events/fda-510k-K260001/changes"):
        response = client.get("/api/medtech" + endpoint)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
        assert "secret" not in response.text
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Authorization, Cookie"
    assert not read


def test_refresh_failure_is_visible_without_losing_data(api):
    client, _, root, _ = api
    record_attempt(root, observed_at=T2, status="failed", code="SOURCE_HTTP_503")
    health = client.get("/api/medtech/health").json()
    assert health["state"] == "refresh_failed"
    assert health["retained_snapshot_available"] is True
    assert client.get("/api/medtech/events").json()["total"] == 1


def test_unavailable_publication_is_not_an_empty_watchdesk(api):
    client, _, root, _ = api
    (root / "current.json").unlink()
    response = client.get("/api/medtech/events")
    assert response.status_code == 503
    assert response.json()["code"] == "MEDTECH_UNAVAILABLE"
    assert str(root) not in response.text


def ranged_batch(rows, *, dataset="pma", when=T2, end="2026-10-11"):
    raw = json.dumps({
        "meta": {"last_updated": end, "results": {"skip": 0, "limit": 1000, "total": len(rows)}},
        "results": rows,
    }).encode()
    return SourceBatch(dataset, "2026-10-01", end, when, end, len(rows), (raw,),
                       (request_url(dataset, "2026-10-01", end, 0, page_size=1000),))


def test_typed_watch_subject_and_baseline_exclude_initial_indexing(api):
    client, _, _, _ = api
    event_id = "fda-510k-K260001"
    subject = client.get("/api/medtech/subjects/event/" + event_id).json()
    assert subject["allowed_triggers"] == ["record_changed"]
    assert subject["baseline_revision"]
    result = client.get("/api/medtech/changes", params={
        "subject_type": "event", "subject_id": event_id, "since": "2026-10-01T00:00:00Z",
    })
    assert result.status_code == 200
    assert result.json()["items"] == []
    assert client.get("/api/medtech/subjects/symbol/EXMD").status_code == 400
    assert client.get("/api/medtech/subjects/pma_application/fda-pma-N970003").status_code == 400


def test_pma_watch_distinguishes_new_supplements_backfills_and_later_corrections(api, tmp_path):
    client, _, public, _ = api
    parent = row("pma")
    old = row("pma", supplement_number="S001", decision_date="2026-10-01", trade_name="Initially indexed old record")
    same_day = row("pma", supplement_number="S002", decision_date="2026-10-10")
    new = row("pma", supplement_number="S003", decision_date="2026-10-11", trade_name="Name at first observation")
    with EventStore(tmp_path / "pma.sqlite3", create=True) as store:
        store.ingest(ranged_batch([parent], when=T1, end="2026-10-10"))
        store.ingest(ranged_batch([parent, old, same_day, new]))
        store.ingest(ranged_batch([
            parent, {**old, "decision_date": "2026-10-11"},
            same_day, {**new, "decision_date": "2026-10-12", "trade_name": "Corrected name"},
        ], when=T3, end="2026-10-12"))
        snapshot_id = publish_snapshot(public, store.snapshot(as_of=T3))
    params = {"subject_type": "pma_application", "subject_id": "fda-pma-P260001", "since": T1}
    subject = client.get("/api/medtech/subjects/pma_application/fda-pma-P260001").json()
    assert subject["allowed_triggers"] == ["record_changed", "new_supplement"]
    assert subject["baseline_revision"] is None
    found = client.get("/api/medtech/changes", params={**params, "trigger": "new_supplement"}).json()
    assert found["total"] == 1
    item = found["items"][0]
    assert item["event_id"] == "fda-pma-P260001-S003"
    assert item["kind"] == "new_supplement_record"
    assert item["decision_date"] == "2026-10-11"
    assert item["device_name"] == "Name at first observation"
    corrections = client.get("/api/medtech/changes", params={**params, "trigger": "record_changed"}).json()
    assert corrections["total"] == 2
    exact = client.get("/api/medtech/changes", params={
        **params, "revision_id": item["revision_id"], "snapshot_id": snapshot_id,
    }).json()
    assert exact["items"] == [item]
    assert client.get("/api/medtech/changes", params={**params, "offset": 1}).status_code == 400
    assert client.get("/api/medtech/changes", params={**params, "trigger": "commercial_launch"}).status_code == 400
    assert client.get("/api/medtech/changes", params={**params, "snapshot_id": "0" * 64}).status_code == 409


def test_parser_identity_is_retained_and_normalization_change_is_explicit(tmp_path, monkeypatch):
    from engine.medtech import store as module
    initial_parser = module.PARSER_VERSION
    with EventStore(tmp_path / "events.sqlite3", create=True) as store:
        store.ingest(batch())
        monkeypatch.setattr(module, "PARSER_VERSION", "fixture_parser_v2")
        store.ingest(batch([row(device_name="Reinterpreted fixture")], when=T2))
        payload = store.snapshot(as_of=T2)
        assert payload["events"][0]["history"][-1]["kind"] == "source_and_normalization_changed"
        versions = [r[0] for r in store.db.execute("SELECT parser_version FROM acquisitions ORDER BY observed_at")]
        assert versions == [initial_parser, "fixture_parser_v2"]


def test_mutated_private_state_is_rejected_before_publication(tmp_path):
    with EventStore(tmp_path / "events.sqlite3", create=True) as store:
        store.ingest(batch())
        store.db.execute("UPDATE observations SET event_json=?", (b'{"corrupted":true}',))
        store.db.commit()
        with pytest.raises(MedTechError, match="STORE_STATE_DIGEST_MISMATCH"):
            store.snapshot(as_of=T1)


@pytest.mark.parametrize("mutation", ["nested_value", "unknown_path", "missing_key", "initial_change", "source_clock", "coverage_clock"])
def test_publication_rejects_private_diff_and_clock_corruption(tmp_path, mutation):
    with EventStore(tmp_path / "events.sqlite3", create=True) as store:
        store.ingest(batch())
        store.ingest(batch([row(device_name="Changed fixture")], when=T2))
        payload = store.snapshot(as_of=T2)
    revision = payload["events"][0]["history"][-1]
    if mutation == "nested_value":
        revision["changes"][0]["after_value"] = {"private_receipt_path": "/secret"}
    elif mutation == "unknown_path":
        revision["changes"][0]["json_path"] = "/device/private_contact"
    elif mutation == "missing_key":
        del revision["changes"][0]["op"]
    elif mutation == "initial_change":
        payload["events"][0]["history"][0]["changes"] = revision["changes"]
    elif mutation == "source_clock":
        payload["sources"][0]["dataset_updated_at"] = "2099-01-01"
    else:
        payload["sources"][0]["coverage"]["end"] = "2099-01-01"
    with pytest.raises(MedTechError):
        validate_snapshot(payload)


def test_unchanged_parser_upgrade_does_not_hide_next_source_change(tmp_path, monkeypatch):
    from engine.medtech import store as module
    with EventStore(tmp_path / "events.sqlite3", create=True) as store:
        store.ingest(batch())
        monkeypatch.setattr(module, "PARSER_VERSION", "fixture_parser_v2")
        assert store.ingest(batch(when=T2))["new_versions"] == 0
        store.ingest(batch([row(device_name="FDA record changed")], when=T3))
        assert store.snapshot(as_of=T3)["events"][0]["history"][-1]["kind"] == "source_record_changed"


def test_identical_raw_record_requires_parser_identity_for_changed_interpretation(tmp_path, monkeypatch):
    from engine.medtech import store as module
    validate = module.validate_batch
    def reinterpret(captured):
        observations = validate(captured)
        observations[0].event["device"]["name"] = "Parser interpretation fixture"
        return observations
    with EventStore(tmp_path / "events.sqlite3", create=True) as store:
        store.ingest(batch())
        monkeypatch.setattr(module, "validate_batch", reinterpret)
        with pytest.raises(MedTechError, match="UNVERSIONED_NORMALIZATION_CHANGE"):
            store.ingest(batch(when=T2))
        assert len(store.snapshot(as_of=T2)["events"][0]["history"]) == 1
        monkeypatch.setattr(module, "PARSER_VERSION", "fixture_parser_v2")
        store.ingest(batch(when=T2))
        assert store.snapshot(as_of=T2)["events"][0]["history"][-1]["kind"] == "normalization_changed"


def test_different_equal_cutoff_publication_cannot_replace_current(tmp_path):
    before = snapshot(tmp_path)
    with EventStore(tmp_path / "other.sqlite3", create=True) as store:
        store.ingest(batch([row(device_name="Different complete source capture")]))
        other = store.snapshot(as_of=T1)
    root = tmp_path / "public"
    current_id = publish_snapshot(root, other)
    assert publish_snapshot(root, other) == current_id
    with pytest.raises(MedTechError, match="PUBLICATION_CLOCK_CONFLICT"):
        publish_snapshot(root, before)
    assert read_snapshot(root)[1] == current_id
