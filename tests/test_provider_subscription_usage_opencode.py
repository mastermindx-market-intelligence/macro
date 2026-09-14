from engine.provider_subscription_usage_opencode import parse_opencode_go_usage


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
    value["usage"]["rolling"] = {"status": "rate-limited", "percent": 100, "resetsAt": "2026-09-14T10:00:00Z"}
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
