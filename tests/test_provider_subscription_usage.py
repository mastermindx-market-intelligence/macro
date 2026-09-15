from __future__ import annotations

from engine.provider_subscription_usage import (
    GLM_QUOTA_ENDPOINT,
    MINIMAX_QUOTA_ENDPOINT,
    observe_glm_quota,
    observe_minimax_quota,
    parse_alibaba_usage,
    parse_glm_quota,
    parse_minimax_quota,
)

OBSERVED = "2026-09-13T06:45:00Z"


def _row(observation, horizon, *, scope=None):
    return next(row for row in observation.quota_rows if row["horizon"] == horizon and row["scope"] == scope)


def test_glm_current_credit_rows_keep_five_hour_weekly_and_mcp_distinct():
    observed = parse_glm_quota({"data": {"level": "max", "limits": [
        {"type": "CREDIT_LIMIT", "unit": 3, "percentage": 25, "usage": 28000, "currentValue": 7000},
        {"type": "CREDIT_LIMIT", "unit": 6, "percentage": 10, "usage": 140000, "currentValue": 14000},
        {"type": "TIME_LIMIT", "percentage": 40, "usage": 1000, "currentValue": 400},
    ]}}, observed_at=OBSERVED)
    assert observed.observability == "exact"
    assert observed.plan_level == "max"
    assert _row(observed, "five_hour")["remaining"] == 21000
    assert _row(observed, "weekly")["used_percent"] == 10
    assert _row(observed, "monthly")["metric"] == "mcp_web_calls"


def test_glm_missing_weekly_is_partial_not_unlimited():
    observed = parse_glm_quota({"data": {"limits": [
        {"type": "TOKENS_LIMIT", "percentage": 20},
    ]}}, observed_at=OBSERVED)
    assert observed.observability == "partial"
    assert observed.degraded_codes == ("GLM_WEEKLY_UNKNOWN",)
    assert _row(observed, "five_hour")["limit"] is None


def test_minimax_prefers_reported_remaining_percent_and_zero_counts_do_not_mean_zero_capacity():
    observed = parse_minimax_quota({"model_remains": [{
        "model_name": "MiniMax-M3", "end_time": 1789279200,
        "current_interval_total_count": 0, "current_interval_usage_count": 0,
        "current_interval_remaining_percent": 62, "current_interval_status": 1,
        "current_weekly_total_count": 0, "current_weekly_usage_count": 0,
        "current_weekly_remaining_percent": 41, "current_weekly_status": 1,
        "weekly_end_time": 1789700000,
    }]}, observed_at=OBSERVED)
    five = _row(observed, "five_hour", scope="MiniMax-M3")
    week = _row(observed, "weekly", scope="MiniMax-M3")
    assert five["used_percent"] == 38
    assert five["limit"] is None and five["remaining"] is None
    assert week["used_percent"] == 59
    assert observed.observability == "exact"


def test_minimax_provider_unlimited_status_is_preserved_without_infinite_capacity_inference():
    observed = parse_minimax_quota({"model_remains": [{
        "model_name": "MiniMax-M3", "current_interval_status": 3,
        "current_interval_total_count": 0, "current_interval_usage_count": 0,
        "current_weekly_status": 2, "current_weekly_total_count": 100,
        "current_weekly_usage_count": 100,
    }]}, observed_at=OBSERVED)
    five = _row(observed, "five_hour", scope="MiniMax-M3")
    weekly = _row(observed, "weekly", scope="MiniMax-M3")
    assert five["status"] == "provider_unlimited" and five["used_percent"] is None
    assert weekly["status"] == "exhausted" and weekly["used_percent"] == 100


def test_observers_keep_credentials_out_of_returned_evidence():
    calls = []
    def fake_glm(url, headers, timeout):
        calls.append((url, dict(headers), timeout))
        return {"data": {"limits": [{"type": "CREDIT_LIMIT", "unit": 3, "percentage": 1}, {"type": "CREDIT_LIMIT", "unit": 6, "percentage": 2}]}}
    secret = "fixture-secret-never-serialize"
    result = observe_glm_quota(lambda: secret, http_get=fake_glm, observed_at=OBSERVED)
    assert calls[0][0] == GLM_QUOTA_ENDPOINT and calls[0][1]["Authorization"] == secret
    assert secret not in repr(result)

    calls.clear()
    def fake_minimax(url, headers, timeout):
        calls.append((url, dict(headers), timeout))
        return {"model_remains": []}
    result = observe_minimax_quota(lambda: secret, http_get=fake_minimax, observed_at=OBSERVED)
    assert calls[0][0] == MINIMAX_QUOTA_ENDPOINT
    assert calls[0][1]["Authorization"] == f"Bearer {secret}"
    assert secret not in repr(result)


def test_alibaba_supported_usage_surface_remains_explicitly_partial_until_window_schema_is_proven():
    observed = parse_alibaba_usage({"period": {"days": 7}, "usage": {"modelsCalled": 3}}, observed_at=OBSERVED)
    assert observed.quota_rows == ()
    assert observed.observability == "partial"
    assert observed.degraded_codes == ("ALIBABA_TOKEN_PLAN_WINDOW_TELEMETRY_PARTIAL",)
