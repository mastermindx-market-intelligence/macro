"""Actual writer -> observed readback helper, synthetic Supabase transport only."""
import copy
from datetime import date

import pytest
from engine import recurring_briefs as rb

SUB = "30000000-0000-4000-8000-000000000001"
OWNER = "10000000-0000-4000-8000-000000000001"
DELIVERY = "40000000-0000-4000-8000-000000000001"
ROW = {"subscription_id": SUB, "slot_asof": "2026-11-04", "state": "ready",
       "degraded_reason": None, "artifact_asof": "2026-11-04T00:00:00Z", "body": {"authored": "Brief"}}


def transport(calls, *, lost=False):
    persisted = None
    def pg(method, path, *, body=None, prefer=None, timeout=6, response_limit=None):
        nonlocal persisted
        calls.append((method, path, response_limit))
        if method == "POST":
            persisted = {**copy.deepcopy(body), "delivery_id": DELIVERY,
                         "brief_subscriptions": {"user_id": OWNER}}
            if lost:
                raise TimeoutError("transport response lost")
            return None
        return [copy.deepcopy(persisted)]
    return pg


@pytest.mark.parametrize("lost", [False, True])
def test_real_wrapper_uses_one_bounded_same_identity_write_read(monkeypatch, lost):
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "synthetic-fixture-only")
    calls = []
    monkeypatch.setattr(rb, "_pg", transport(calls, lost=lost))
    observed = rb.write_delivery_observed(copy.deepcopy(ROW), OWNER)
    assert observed.receipt.delivery_id == DELIVERY
    assert [call[0] for call in calls] == ["POST", "GET"]
    assert all(call[2] == 393216 for call in calls)
    assert f"brief_subscriptions.user_id=eq.{OWNER}" in calls[1][1]


def test_missing_provisioned_source_client_or_dry_run_touches_no_network(monkeypatch):
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "")
    def forbidden(*args, **kwargs):
        pytest.fail("no source operation permitted")
    monkeypatch.setattr(rb, "_pg", forbidden)
    assert rb.write_delivery_observed(copy.deepcopy(ROW), OWNER) is None
    assert rb.write_delivery_observed(copy.deepcopy(ROW), OWNER, dry_run=True).receipt is None


def test_existing_run_can_collect_observation_without_a_second_legacy_post(monkeypatch, capsys):
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "synthetic-fixture-only")
    monkeypatch.setattr(rb, "load_published_artifact", lambda *a, **kw: {"as_of": "2026-11-04"})
    monkeypatch.setattr(rb, "read_subscriptions", lambda *a: rb.SubscriptionReadResult(rows=({
        "subscription_id": SUB, "user_id": OWNER, "cadence": rb.CADENCE_DAILY, "state": "active"},)))
    monkeypatch.setattr(rb, "read_target", lambda *a: rb.TargetReadResult(target={"tickers": []}))
    monkeypatch.setattr(rb, "classify", lambda *a: ("ready", None))
    monkeypatch.setattr(rb, "compose_body", lambda *a, **kw: copy.deepcopy(ROW["body"]))
    monkeypatch.setattr(rb, "load_monitors_for_target", lambda *a: [])
    calls = []
    monkeypatch.setattr(rb, "_pg", transport(calls))
    monkeypatch.setattr(rb, "write_delivery", lambda *a, **kw: pytest.fail("a second legacy POST is forbidden"))
    result = rb.run(cadence=rb.CADENCE_DAILY, dry_run=False, run_date=date(2026, 11, 4),
                    collect_delivery_observations=True)
    assert result.error_n == 0
    assert len(result.delivery_observations) == 1
    assert result.delivery_observations[0].delivery_id == DELIVERY
    assert [call[0] for call in calls] == ["POST", "GET"]
    assert capsys.readouterr().out == ""


def test_real_source_client_enforces_response_budget_before_json_and_bounds_invalid_before_io(monkeypatch):
    import io
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "synthetic-fixture-only")
    calls = []
    def urlopen(request, timeout):
        calls.append(request.method)
        return io.BytesIO(b"[" + b" " * 200 + b"]")
    monkeypatch.setattr(rb.urllib.request, "urlopen", urlopen)
    with pytest.raises(ValueError, match="over budget"):
        rb._pg("GET", "brief_deliveries", response_limit=64)
    assert calls == ["GET"]
    with pytest.raises(ValueError, match="invalid response bound"):
        rb._pg("GET", "brief_deliveries", response_limit=0)
    assert calls == ["GET"]
