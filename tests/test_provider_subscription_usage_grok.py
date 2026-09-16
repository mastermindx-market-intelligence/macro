import dataclasses
import json

import pytest

from engine.provider_subscription_usage import SubscriptionUsageError
from engine.provider_subscription_usage_grok import (
    GROK_BILLING_METHOD,
    GROK_WEEKLY_PERIOD_TYPE,
    GROK_WEEKLY_SCOPE,
    _run_grok_billing_acp,
    observe_grok_build_usage,
    parse_grok_build_billing,
)


def billing_payload(*, used=1.0, tier="SuperGrok Heavy", end="2026-09-21T05:54:40.520376+00:00"):
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "config": {
                "creditUsagePercent": used,
                "currentPeriod": {
                    "type": GROK_WEEKLY_PERIOD_TYPE,
                    "start": "2026-09-14T05:54:40.520376+00:00",
                    "end": end,
                },
                "billingPeriodStart": "2026-09-14T05:54:40.520376+00:00",
                "billingPeriodEnd": end,
            },
            "subscription_tier": tier,
        },
    }


def test_parses_heavy_weekly_shared_capacity():
    result = parse_grok_build_billing(
        billing_payload(), observed_at="2026-09-16T05:00:00Z"
    )
    assert result.provider == "xai"
    assert result.plan_level == "heavy"
    assert result.observability == "exact"
    assert result.degraded_codes == ()
    assert len(result.quota_rows) == 1
    row = result.quota_rows[0]
    assert row["horizon"] == "weekly"
    assert row["metric"] == "provider_allocation"
    assert row["scope"] == GROK_WEEKLY_SCOPE
    assert row["used_percent"] == 1.0
    assert row["reported_remaining_percent"] == 99.0
    assert row["reset_at"] == "2026-09-21T05:54:40Z"
    assert row["limit"] is None and row["used"] is None and row["remaining"] is None


def test_100_percent_is_exhausted():
    result = parse_grok_build_billing(
        billing_payload(used=100), observed_at="2026-09-16T05:00:00Z"
    )
    assert result.quota_rows[0]["status"] == "exhausted"
    assert result.quota_rows[0]["reported_remaining_percent"] == 0


def test_missing_usage_fails_closed_without_row():
    value = billing_payload()
    del value["result"]["config"]["creditUsagePercent"]
    result = parse_grok_build_billing(value, observed_at="2026-09-16T05:00:00Z")
    assert result.observability == "unknown"
    assert result.quota_rows == ()
    assert "GROK_BUILD_USAGE_PERCENT_UNKNOWN" in result.degraded_codes


def test_nonweekly_period_fails_closed_without_row():
    value = billing_payload()
    value["result"]["config"]["currentPeriod"]["type"] = "USAGE_PERIOD_TYPE_DAILY"
    result = parse_grok_build_billing(value, observed_at="2026-09-16T05:00:00Z")
    assert result.quota_rows == ()
    assert "GROK_BUILD_WEEKLY_PERIOD_UNKNOWN" in result.degraded_codes


def test_stale_reset_fails_closed_without_row():
    result = parse_grok_build_billing(
        billing_payload(end="2026-09-16T04:59:59Z"),
        observed_at="2026-09-16T05:00:00Z",
    )
    assert result.quota_rows == ()
    assert "GROK_BUILD_RESET_STALE" in result.degraded_codes


def test_unknown_tier_does_not_gain_capacity():
    result = parse_grok_build_billing(
        billing_payload(tier="future-secret-tier"), observed_at="2026-09-16T05:00:00Z"
    )
    assert result.plan_level is None
    assert result.quota_rows == ()
    assert "GROK_BUILD_TIER_UNKNOWN" in result.degraded_codes


def test_observer_uses_injected_prompt_free_billing_runner():
    calls = []

    def runner(binary, timeout):
        calls.append((binary, timeout))
        return billing_payload(used=12)

    result = observe_grok_build_usage(
        grok_binary="grok-test",
        timeout_seconds=4,
        observed_at="2026-09-16T05:00:00Z",
        billing_runner=runner,
    )
    assert calls == [("grok-test", 4)]
    assert result.quota_rows[0]["used_percent"] == 12
    assert "grok-test" not in repr(result)


def test_rpc_method_is_private_billing_not_model_prompt():
    assert GROK_BILLING_METHOD == "_x.ai/billing"


def test_subprocess_runner_uses_initialize_then_billing(monkeypatch):
    sent = []

    class FakeStdin:
        def write(self, value):
            sent.append(json.loads(value))
        def flush(self):
            pass
        def close(self):
            pass

    class FakeStdout:
        def __init__(self):
            self.responses = [
                json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": 1}}) + "\n",
                json.dumps(billing_payload()) + "\n",
            ]
        def readline(self):
            return self.responses.pop(0)

    class FakeProcess:
        def __init__(self, *args, **kwargs):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout()
            self._done = False
        def poll(self):
            return 0 if self._done else None
        def terminate(self):
            self._done = True
        def wait(self, timeout=None):
            self._done = True
            return 0
        def kill(self):
            self._done = True

    monkeypatch.setattr("engine.provider_subscription_usage_grok.subprocess.Popen", FakeProcess)
    monkeypatch.setattr("engine.provider_subscription_usage_grok.select.select", lambda r, w, x, timeout: (r, [], []))
    result = _run_grok_billing_acp("grok", 5)
    assert [item["method"] for item in sent] == ["initialize", "_x.ai/billing"]
    assert all("prompt" not in item["method"].lower() for item in sent)
    assert result["result"]["subscription_tier"] == "SuperGrok Heavy"


def test_rpc_error_is_not_capacity():
    def runner(_binary, _timeout):
        raise SubscriptionUsageError("GROK_BUILD_BILLING_RPC_ERROR")

    with pytest.raises(SubscriptionUsageError, match="GROK_BUILD_BILLING_RPC_ERROR"):
        observe_grok_build_usage(billing_runner=runner)


def test_observation_is_secret_free_shape():
    result = parse_grok_build_billing(
        billing_payload(), observed_at="2026-09-16T05:00:00Z"
    )
    encoded = json.dumps(dataclasses.asdict(result), sort_keys=True)
    assert "Authorization" not in encoded
    assert "token" not in encoded.lower()
