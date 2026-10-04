from __future__ import annotations

import contextlib
import http.server
import json
import math
import socket
import threading
from datetime import datetime, timezone

import pytest

from engine.provider_subscription_usage import (
    GLM_QUOTA_ENDPOINT,
    MINIMAX_QUOTA_ENDPOINT,
    SubscriptionUsageError,
    _https_get_json,
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


@contextlib.contextmanager
def _redirect_rig(make_location):
    """Stand up server A on 127.0.0.1 and server B on 127.0.0.1.

    A answers 302 with `Location=make_location(a_port, b_port)` and records
    its own incoming Authorization header into `seen`. B records into `seen`
    as well, but only if a request actually reaches it. Both servers run on
    daemon threads and are shut down on context exit. CROSS-HOST is achieved
    by setting Location=``http://localhost:<b_port>/b`` (urllib treats
    ``127.0.0.1`` and ``localhost`` as different hosts).
    """
    seen: dict[str, object] = {}
    location_holder: list[str | None] = [None]

    class HandlerA(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: D401
            seen["a_hit"] = True
            seen["a_auth"] = self.headers.get("Authorization")
            self.send_response(302)
            self.send_header("Location", location_holder[0] or "")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format, *args):  # noqa: A002
            pass

    class HandlerB(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: D401
            seen["b_hit"] = True
            seen["b_auth"] = self.headers.get("Authorization")
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A002
            pass

    server_b = http.server.HTTPServer(("127.0.0.1", 0), HandlerB)
    b_port = server_b.server_address[1]
    thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
    thread_b.start()

    server_a = http.server.HTTPServer(("127.0.0.1", 0), HandlerA)
    a_port = server_a.server_address[1]
    location_holder[0] = make_location(a_port, b_port)
    thread_a = threading.Thread(target=server_a.serve_forever, daemon=True)
    thread_a.start()

    try:
        yield (a_port, seen)
    finally:
        server_a.shutdown()
        server_a.server_close()
        server_b.shutdown()
        server_b.server_close()
        thread_a.join(timeout=2.0)
        thread_b.join(timeout=2.0)


def test_https_get_json_refuses_cross_host_redirect_and_never_forwards_authorization():
    headers = {
        "Authorization": "Bearer fixture-redirect-sentinel",
        "Accept": "application/json",
    }
    with _redirect_rig(lambda a_port, b_port: f"http://localhost:{b_port}/b") as (a_port, seen):
        with pytest.raises(SubscriptionUsageError) as excinfo:
            _https_get_json(f"http://127.0.0.1:{a_port}/a", headers, 5.0)
    # (a) typed redirect-refusal error
    assert str(excinfo.value) == "PROVIDER_USAGE_REDIRECT_REFUSED"
    # (b) POSITIVE CONTROL: A really did receive the Authorization header
    assert seen["a_auth"] == "Bearer fixture-redirect-sentinel"
    # (c) B was never reached
    assert seen.get("b_hit") is not True
    # (d) B never saw the credential
    assert seen.get("b_auth") is None


def test_https_get_json_redirect_refusal_error_carries_no_credential_or_header_bytes():
    headers = {
        "Authorization": "Bearer fixture-redirect-sentinel",
        "Accept": "application/json",
    }
    with _redirect_rig(lambda a_port, b_port: f"http://localhost:{b_port}/b") as (a_port, _seen):
        with pytest.raises(SubscriptionUsageError) as excinfo:
            _https_get_json(f"http://127.0.0.1:{a_port}/a", headers, 5.0)
    exc = excinfo.value
    assert "fixture-redirect-sentinel" not in str(exc)
    assert "fixture-redirect-sentinel" not in repr(exc)
    assert "Authorization" not in str(exc)
    assert "Bearer" not in str(exc)
    # Raising AFTER the except handler has exited (not inside it with
    # `from None`) leaves `__context__` itself None, so the urllib exception —
    # which carries the request URL and the response headers (including a
    # redirect's `Location`) — is unreachable as `err.__context__`.
    assert exc.__cause__ is None
    assert exc.__context__ is None


def test_https_get_json_refuses_same_host_redirect_too():
    with _redirect_rig(lambda a_port, _b_port: f"http://127.0.0.1:{a_port}/again") as (a_port, _seen):
        with pytest.raises(SubscriptionUsageError) as excinfo:
            _https_get_json(
                f"http://127.0.0.1:{a_port}/a",
                {"Authorization": "Bearer fixture-redirect-sentinel", "Accept": "application/json"},
                5.0,
            )
    assert str(excinfo.value) == "PROVIDER_USAGE_REDIRECT_REFUSED"


def test_https_get_json_transport_failure_is_a_typed_subscription_usage_error():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        dead_port = sock.getsockname()[1]
    finally:
        sock.close()
    with pytest.raises(SubscriptionUsageError) as excinfo:
        _https_get_json(
            f"http://127.0.0.1:{dead_port}/x",
            {"Accept": "application/json"},
            5.0,
        )
    assert str(excinfo.value) == "PROVIDER_USAGE_TRANSPORT_ERROR"
    # Symmetric to the redirect path: the OSError branch must also clear the
    # handled-exception state by exiting it before raising, so neither
    # `__cause__` nor `__context__` carries the OSError's request state.
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None


def test_minimax_reset_timestamps_map_five_hour_to_end_time_and_weekly_to_weekly_end_time():
    end_time_epoch = 1789279200
    weekly_end_epoch = 1789700000
    expected_five = (
        datetime.fromtimestamp(end_time_epoch, timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    expected_week = (
        datetime.fromtimestamp(weekly_end_epoch, timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    observed = parse_minimax_quota({"model_remains": [{
        "model_name": "MiniMax-M3",
        "end_time": end_time_epoch,
        "weekly_end_time": weekly_end_epoch,
        "current_interval_remaining_percent": 62,
        "current_interval_status": 1,
        "current_weekly_remaining_percent": 41,
        "current_weekly_status": 1,
    }]}, observed_at=OBSERVED)
    five = _row(observed, "five_hour", scope="MiniMax-M3")
    week = _row(observed, "weekly", scope="MiniMax-M3")
    assert five["reset_at"] == expected_five
    assert week["reset_at"] == expected_week
    assert five["reset_at"] != week["reset_at"]


def test_minimax_known_tier_without_quantified_counts_is_unknown_not_unbounded():
    # (i) known, limited tier carries no counts and no remaining percent
    observed_known = parse_minimax_quota({"model_remains": [{
        "model_name": "MiniMax-M3",
        "current_interval_status": 1,
        "current_weekly_status": 1,
    }]}, observed_at=OBSERVED)
    five = _row(observed_known, "five_hour", scope="MiniMax-M3")
    week = _row(observed_known, "weekly", scope="MiniMax-M3")
    assert five["limit"] is None and five["remaining"] is None and five["used_percent"] is None
    assert week["limit"] is None and week["remaining"] is None and week["used_percent"] is None
    assert observed_known.observability == "partial"
    assert "MINIMAX_REMAINING_PERCENT_PARTIAL" in observed_known.degraded_codes
    assert all(
        not (isinstance(v, float) and not math.isfinite(v))
        for row in observed_known.quota_rows
        for v in row.values()
    )

    # (ii) empty model_remains
    observed_empty = parse_minimax_quota({"model_remains": []}, observed_at=OBSERVED)
    assert observed_empty.quota_rows == ()
    assert observed_empty.observability == "unknown"
    assert observed_empty.degraded_codes == ("MINIMAX_QUOTA_UNKNOWN",)
    assert all(
        not (isinstance(v, float) and not math.isfinite(v))
        for row in observed_empty.quota_rows
        for v in row.values()
    )
