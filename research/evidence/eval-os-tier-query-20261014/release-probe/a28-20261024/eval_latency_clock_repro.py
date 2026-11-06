from datetime import datetime, timezone, timedelta
import pytest
@pytest.fixture(autouse=True)
def crossing_second(monkeypatch, request):
    if request.node.name != "test_f_recorder_failure_never_changes_status_or_body":
        return
    import app.forensics as api
    class Advancing(datetime):
        tick = 0
        @classmethod
        def now(cls, tz=None):
            cls.tick += 1
            return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=cls.tick)
    monkeypatch.setattr(api, "datetime", Advancing)
