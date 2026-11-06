"""History read outages must never become an empty successful research history."""
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app, require_user
from engine.neuralweb import brain_gateway as gw

TID = "11111111-1111-1111-1111-111111111111"
THREAD = {"id": TID, "title": "Retained inquiry", "lane": "fast"}
MESSAGE = {"role": "assistant", "content": "Retained answer", "created_at": "2026-10-05T06:57:26Z"}

@pytest.fixture
def client():
    app.dependency_overrides[require_user] = lambda: {"id": "userA"}
    try:
        with TestClient(app) as result:
            yield result
    finally:
        app.dependency_overrides.clear()

@pytest.mark.parametrize("bad", [None, {}, "unavailable", [None], [THREAD, None]])
@pytest.mark.parametrize("stage", ["list", "owner", "messages"])
def test_failed_read_never_reports_empty_or_missing(client, bad, stage):
    path = "/api/brain/threads" + ("" if stage == "list" else "/" + TID)
    reads = [bad] if stage != "messages" else [[THREAD], bad]
    with patch.object(gw, "_sb_get", side_effect=reads), \
         patch.object(gw, "_sb_post") as post, \
         patch.object(gw, "_sb_patch") as update, \
         patch.object(gw, "_sb_delete") as delete:
        response = client.get(path)
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "research history temporarily unavailable"}
    post.assert_not_called(); update.assert_not_called(); delete.assert_not_called()

@pytest.mark.parametrize("path,reads,status,body", [
    ("/api/brain/threads", [[]], 200, {"threads": []}),
    ("/api/brain/threads/" + TID, [[]], 404, {"detail": "thread not found or not authorized"}),
    ("/api/brain/threads/" + TID, [[THREAD], []], 200, {"thread": THREAD, "messages": []}),
    ("/api/brain/threads/" + TID, [[THREAD], [MESSAGE]], 200, {"thread": THREAD, "messages": [MESSAGE]}),
])
def test_successful_empty_absent_and_retained_reads_stay_distinct(client, path, reads, status, body):
    with patch.object(gw, "_sb_get", side_effect=reads) as get:
        response = client.get(path)
    assert response.status_code == status
    assert response.json() == body
    assert "user_id=eq.userA" in get.call_args_list[0].args[0]
    if len(reads) == 1:
        assert get.call_count == 1

@pytest.mark.parametrize("path", ["/api/brain/threads", "/api/brain/threads/" + TID])
def test_history_read_remains_authenticated(client, path):
    app.dependency_overrides.clear()
    with patch.object(gw, "_sb_get") as get:
        assert client.get(path).status_code == 401
    get.assert_not_called()

@pytest.mark.parametrize("bad", ["not-a-uuid", "abc%20def", "x" * 65, "t1,user_id.neq.x"])
def test_invalid_thread_read_never_queries_store(client, bad):
    with patch.object(gw, "_sb_get") as get:
        assert gw.get_thread(bad, "userA") is None
    get.assert_not_called()
