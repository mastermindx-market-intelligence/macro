from engine.provider_subscription_usage_opencode import (
    OPENCODE_GO_USAGE_ENDPOINT,
    observe_opencode_go_usage,
    parse_opencode_go_usage,
)


def payload():
    return {
        "usage": {
            "rolling": {"status": "ok", "percent": 25, "resetsAt": "2026-09-14T10:00:00Z"},
            "weekly": {"status": "ok", "percent": 40, "resetsAt": "2026-09-20T00:00:00Z"},
            "monthly": {"status": "ok", "percent": 10, "resetsAt": "2026-10-14T00:00:00Z"},
        }
    }


def test_parses_all_three_shared_windows():
    result = parse_opencode_go_usage(payload(), observed_at="2026-09-14T05:00:00Z")
    assert result.provider == "opencode"
    assert result.plan_level == "go"
    assert result.observability == "exact"
    assert [row["horizon"] for row in result.quota_rows] == ["five_hour", "weekly", "monthly"]
    assert all(row["scope"] == "account_shared" for row in result.quota_rows)
    assert all(row["limit"] is None for row in result.quota_rows)


def test_rate_limited_window_is_exhausted():
    value = payload()
    value["usage"]["rolling"] = {
        "status": "rate-limited",
        "percent": 100,
        "resetsAt": "2026-09-14T10:00:00Z",
    }
    result = parse_opencode_go_usage(value, observed_at="2026-09-14T05:00:00Z")
    assert result.quota_rows[0]["status"] == "exhausted"
    assert result.quota_rows[0]["reported_remaining_percent"] == 0


def test_missing_window_stays_partial_not_free():
    value = payload()
    del value["usage"]["weekly"]
    result = parse_opencode_go_usage(value, observed_at="2026-09-14T05:00:00Z")
    assert result.observability == "partial"
    assert "OPENCODE_GO_WEEKLY_UNKNOWN" in result.degraded_codes
    assert not any(row["horizon"] == "weekly" for row in result.quota_rows)


def test_authenticated_observer_uses_bearer_without_returning_secret():
    captured = {}

    def fake_get(url, headers, timeout_seconds):
        captured["url"] = url
        captured["headers"] = dict(headers)
        captured["timeout"] = timeout_seconds
        return payload()

    result = observe_opencode_go_usage(
        lambda: "private-test-token",
        http_get=fake_get,
        observed_at="2026-09-14T05:00:00Z",
        timeout_seconds=7.0,
    )
    assert captured["url"] == OPENCODE_GO_USAGE_ENDPOINT
    assert captured["headers"]["Authorization"] == "Bearer private-test-token"
    assert captured["headers"]["User-Agent"] == "mastermind-provider-control/1.0"
    assert captured["timeout"] == 7.0
    assert "private-test-token" not in repr(result)


def test_observer_loads_credential_once():
    calls = []

    def loader():
        calls.append("load")
        return "private-test-token"

    observe_opencode_go_usage(loader, http_get=lambda *_args: payload())
    assert calls == ["load"]
