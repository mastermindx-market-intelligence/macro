"""A full candidate collection is not an HTTP page (Sep-15 publication outage)."""
from copy import deepcopy
from hashlib import sha256

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import government_revenue as api
from engine.government_revenue.candidates import (
    build_candidate_queue, candidate_queue_content_id, is_valid_candidate_queue,
)
from tests.test_government_revenue_candidates import (
    GENERATED_AT, _award_event, _graph, _payload,
)


def _collection(count):
    payload = _payload()
    events = []
    for index in range(count):
        event = _award_event()
        event["event_id"] = f"govawd-cardinality-{index:04d}"
        events.append(event)
    payload["procurement_workspace"]["events"] = events
    return build_candidate_queue(payload, _graph(), generated_at=GENERATED_AT)


@pytest.mark.parametrize("count", [1, 250, 251, 264, 500])
def test_complete_source_collection_is_not_limited_to_one_page(count):
    queue = _collection(count)
    assert is_valid_candidate_queue(queue)
    assert len(queue["candidates"]) == count
    assert len({row["candidate_id"] for row in queue["candidates"]}) == count
    assert queue["counts"]["total"] == count
    assert queue["counts"]["exact_linked"] == count
    assert queue["authority"]["can_originate_signal"] is False


def test_rows_after_250_still_require_evidence_and_display_only_authority():
    queue = _collection(264)
    bad = deepcopy(queue)
    bad["candidates"][-1]["authority"]["can_rank"] = True
    bad["content_id"] = candidate_queue_content_id(bad)
    assert not is_valid_candidate_queue(bad)
    bad = deepcopy(queue)
    bad["candidates"][-1]["source_receipt_refs"] = []
    bad["content_id"] = candidate_queue_content_id(bad)
    assert not is_valid_candidate_queue(bad)
    bad = deepcopy(queue)
    bad["content_id"] = "grcq1-" + sha256(b"wrong-generation").hexdigest()[:24]
    assert not is_valid_candidate_queue(bad)


def test_http_pages_cover_all_264_candidates_without_relaxing_request_limit(monkeypatch):
    queue = _collection(264)
    monkeypatch.setattr(api, "_load_candidate_projection", lambda: {"queue": queue, "ledger": []})
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "cardinality-test"}
    client = TestClient(app)
    cursor, rows, page_sizes = None, [], []
    for _ in range(4):
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        response = client.get("/api/government-revenue/candidates", params=params)
        assert response.status_code == 200
        page = response.json()
        assert page["total"] == 264
        assert page["content_id"] == queue["content_id"]
        assert page["authority"]["can_rank"] is False
        rows.extend(page["items"])
        page_sizes.append(len(page["items"]))
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert cursor is None
    assert page_sizes == [100, 100, 64]
    assert {row["candidate_id"] for row in rows} == {row["candidate_id"] for row in queue["candidates"]}
    assert client.get("/api/government-revenue/candidates", params={"limit": 101}).status_code == 422
