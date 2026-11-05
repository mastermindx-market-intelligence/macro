"""Native B wire boundaries on numeric loopback; no live pool or credentials."""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import socket
import threading
import time

import pytest

from engine import fabric_inference_client as transport
from tests.test_fabric_inference_client import completion, request, server, MODEL

TOKEN = "fixture-native-service-credential-0123456789"
TURN = "turn-1"
STEP = "turn-1:brain:0"


def client(url, **kwargs):
    return transport.FabricInferenceClient(base_url=url, proxy_token=TOKEN, model=MODEL,
        protocol=transport.NATIVE_PROTOCOL, operation_id=kwargs.pop("operation_id", TURN), **kwargs)


def success(**changes):
    value = {"json": completion(), "headers": {
        "X-MM-Application-Disposition": "terminal",
        "X-MM-Application-Turn-ID": TURN, "X-MM-Application-Request-ID": STEP}}
    value.update(changes)
    return value


def envelope(disposition, *, status=None, close=False, usage=None, model=MODEL, code=None):
    statuses = {"refused": 429, "pending": 409, "effect_unknown": 503,
                "terminal": 502, "terminal_receipt_only": 409, "closed": 200}
    state = {"schema": transport.NATIVE_SCHEMA, "disposition": disposition,
        "turn_id": TURN, "request_id": None if close else STEP,
        "dispatch_permitted": False, "effect_unknown": disposition in {"pending", "effect_unknown"}}
    if usage is not None:
        state.update(usage={"input_tokens": usage[0], "output_tokens": usage[1]}, serving_model=model)
    payload = {"application": state}
    if code:
        payload["error"] = {"type": code, "message": "application request unavailable"}
    headers = {"X-MM-Application-Disposition": disposition, "X-MM-Application-Turn-ID": TURN}
    if not close:
        headers["X-MM-Application-Request-ID"] = STEP
    return {"status": status or statuses[disposition], "json": payload, "headers": headers}


def send(handler, plan, *, extra_headers=()):
    raw = json.dumps(plan["json"]).encode()
    handler.send_response(plan.get("status", 200))
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Connection", "close")
    for name, value in (*plan.get("headers", {}).items(), *extra_headers):
        handler.send_header(name, value)
    handler.end_headers()
    handler.wfile.write(raw)
    handler.wfile.flush()
    handler.close_connection = True


def test_original_turn_step_and_one_explicit_close_use_native_wire(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    with server(success(), envelope("closed", close=True)) as (url, calls):
        native = client(url)
        response = native.messages.create(**request())
        result = native.close()
        assert native.close() == result
        with pytest.raises(transport.FabricInferenceError, match="operation_closed"):
            native.messages.create(**request(request_id="turn-1:brain:1"))
    assert response.usage.input_tokens == 13 and response.usage.output_tokens == 7
    assert result == {"disposition": "closed", "closed": True, "effect_unknown": False, "attempted": True}
    assert [c["path"] for c in calls] == ["/v1/chat/completions", "/application-turns/close"]
    assert calls[0]["headers"]["X-MM-Application-Turn-ID"] == TURN
    assert calls[0]["headers"]["Idempotency-Key"] == STEP
    assert calls[0]["body"]["stream"] is False and "stream_options" not in calls[0]["body"]
    assert calls[1]["body"] == {"turn_id": TURN}
    assert all(c["headers"]["Authorization"] == "Bearer " + TOKEN for c in calls)
    assert all("X-MM-Pool-Account" not in c["headers"] for c in calls)


@pytest.mark.parametrize("identifier", [None, "", "turn/other", "bad\nheader", "x" * 129])
def test_native_original_identity_is_never_rewritten(identifier):
    with server() as (url, calls):
        with pytest.raises(transport.FabricInferenceError, match="identity_invalid"):
            client(url, operation_id=identifier)
        assert calls == []


def test_native_step_and_stream_refuse_before_bytes_and_close_is_local():
    with server() as (url, calls):
        native = client(url)
        with pytest.raises(transport.FabricInferenceError, match="identity_invalid"):
            native.messages.create(**request(request_id="original/step"))
        assert native.close()["attempted"] is False
        native = client(url)
        with pytest.raises(transport.FabricInferenceError, match="stream_unsupported"):
            with native.messages.stream(**request()):
                pytest.fail("native stream entered")
        assert native.close()["attempted"] is False
        assert calls == []


@pytest.mark.parametrize("token", ["x" * 31, "v1." + "x" * 40, "app1." + "x" * 40])
def test_worker_and_short_credentials_cannot_be_native_service_bindings(token):
    with pytest.raises(transport.FabricInferenceError, match="binding_invalid"):
        transport.FabricInferenceClient(base_url="http://127.0.0.1:1/v1", proxy_token=token,
            model=MODEL, protocol=transport.NATIVE_PROTOCOL, operation_id=TURN)


@pytest.mark.parametrize("disposition,unknown", [("refused", False), ("pending", True),
    ("effect_unknown", True), ("terminal_receipt_only", False)])
def test_native_dispositions_latch_without_answers_or_usage(disposition, unknown):
    with server(envelope(disposition)) as (url, calls):
        native = client(url)
        with pytest.raises(transport.FabricInferenceError) as caught:
            native.messages.create(**request())
        error = caught.value
        assert error.disposition == disposition and error.effect_unknown is unknown
        assert error.observed_usage is None
        with pytest.raises(transport.FabricInferenceError):
            native.messages.create(**request(request_id="new-step"))
        assert len(calls) == 1


@pytest.mark.parametrize("disposition", ["terminal", "effect_unknown"])
def test_observed_usage_is_independent_of_native_settlement(disposition):
    with server(envelope(disposition, usage=(11, 7), model="actually-served-model")) as (url, calls):
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url).messages.create(**request())
    error = caught.value
    assert (error.observed_usage.input_tokens, error.observed_usage.output_tokens) == (11, 7)
    assert error.serving_model == "actually-served-model" and error.request_id == STEP
    assert error.effect_unknown is (disposition == "effect_unknown") and len(calls) == 1


@pytest.mark.parametrize("status", [301, 400, 401, 403, 409, 429, 500, 503])
def test_unrecognized_native_http_status_never_proves_absence_or_follows_redirect(status):
    with server({"status": status, "json": {"error": "provider secret " + TOKEN},
                 "headers": {"Location": "http://example.invalid/steal"}}) as (url, calls):
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url).messages.create(**request())
    assert caught.value.effect_unknown and TOKEN not in str(caught.value) and len(calls) == 1


@pytest.mark.parametrize("change", ["dispatch", "unknown", "schema", "extra", "turn", "step",
    "header", "no_header", "status", "receipt_usage", "null_error", "mixed_null"])
def test_conflicting_native_envelope_is_unknown(change):
    plan = envelope("pending")
    state = plan["json"]["application"]
    if change == "dispatch": state["dispatch_permitted"] = True
    elif change == "unknown": state["effect_unknown"] = False
    elif change == "schema": state["schema"] = "unqualified.v2"
    elif change == "extra": state["lease"] = "caller-asserted"
    elif change == "turn": state["turn_id"] = "another-turn"
    elif change == "step": state["request_id"] = "another-step"
    elif change == "header": plan["headers"]["X-MM-Application-Request-ID"] = "other-step"
    elif change == "no_header": del plan["headers"]["X-MM-Application-Disposition"]
    elif change == "status": plan["status"] = 400
    elif change == "receipt_usage": plan = envelope("terminal_receipt_only", usage=(11, 7))
    elif change == "null_error": plan["json"]["error"] = None
    elif change == "mixed_null":
        plan = envelope("refused", code="application_request_invalid")
        plan["json"]["application"]["turn_id"] = None
        del plan["headers"]["X-MM-Application-Turn-ID"]
    with server(plan) as (url, calls):
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url).messages.create(**request())
    assert caught.value.effect_unknown and len(calls) == 1


def test_actual_preparse_refusal_allows_only_absent_original_correlation():
    plan = envelope("refused", status=401, code="application_unauthorized")
    plan["json"]["application"].update(turn_id=None, request_id=None)
    plan["headers"] = {"X-MM-Application-Disposition": "refused"}
    with server(plan) as (url, calls):
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url).messages.create(**request())
    assert not caught.value.effect_unknown and caught.value.disposition == "refused" and len(calls) == 1


@pytest.mark.parametrize("header", ["X-MM-Application-Disposition", "X-MM-Application-Turn-ID",
    "X-MM-Application-Request-ID", "Content-Length"])
def test_duplicate_native_success_headers_are_unknown(header):
    plan = success()
    value = plan["headers"].get(header, str(len(json.dumps(plan["json"]).encode())))
    with server(lambda handler: send(handler, plan, extra_headers=((header, value),))) as (url, calls):
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url).messages.create(**request())
    assert caught.value.effect_unknown and len(calls) == 1


@pytest.mark.parametrize("header", ["X-MM-Application-Disposition", "X-MM-Application-Turn-ID",
    "X-MM-Application-Request-ID"])
def test_missing_native_success_headers_are_unknown(header):
    plan = success()
    del plan["headers"][header]
    with server(plan) as (url, calls):
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url).messages.create(**request())
    assert caught.value.effect_unknown and len(calls) == 1


@pytest.mark.parametrize("count,expected", [(10**12, 10**12), (10**12+1, None),
    (True, None), (-1, None), (None, None)])
def test_raw_native_success_and_envelope_share_incumbent_count_bound(count, expected):
    plan = success()
    plan["json"]["usage"] = {"prompt_tokens": count, "completion_tokens": 7}
    with server(plan) as (url, calls):
        result = client(url).messages.create(**request())
    assert result.usage.input_tokens == expected and result.usage.output_tokens == 7
    with server(envelope("terminal", usage=(count, 7))) as (url, calls):
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url).messages.create(**request())
    assert caught.value.observed_usage.input_tokens == expected
    assert caught.value.observed_usage.output_tokens == 7


@pytest.mark.parametrize("phase", ["headers", "error_body"])
def test_absolute_native_deadline_covers_slow_headers_and_error_body(phase):
    def trickle(handler):
        if phase == "headers":
            handler.wfile.write(b"HTTP/1.1 503 Service Unavailable\r\nX-Trickle: ")
        else:
            handler.wfile.write(b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nContent-Length: 9999\r\n\r\n")
        handler.wfile.flush()
        try:
            for _ in range(100):
                handler.wfile.write(b" ")
                handler.wfile.flush()
                threading.Event().wait(0.02)
        except OSError:
            pass
        handler.close_connection = True
    with server(trickle) as (url, calls):
        start = time.monotonic()
        with pytest.raises(transport.FabricInferenceError) as caught:
            client(url, timeout_s=0.08).messages.create(**request())
        assert time.monotonic() - start < 1
    assert caught.value.effect_unknown and len(calls) == 1


def test_prebyte_connection_failure_and_pristine_close_have_no_native_close(monkeypatch):
    with server() as (url, calls):
        assert client(url).close()["attempted"] is False
        native = client(url)
        def unavailable(_):
            raise ConnectionRefusedError("synthetic connection unavailable")
        monkeypatch.setattr(transport._NativeConnection, "connect", unavailable)
        with pytest.raises(transport.FabricInferenceError) as caught:
            native.messages.create(**request())
        assert not caught.value.effect_unknown
        assert native.close()["attempted"] is False and calls == []


@pytest.mark.parametrize("close_plan,disposition", [(envelope("pending", close=True), "pending"),
    ({"disconnect": True}, "effect_unknown"), (envelope("effect_unknown", close=True), "effect_unknown")])
def test_close_is_once_bounded_and_not_a_fabricated_release(close_plan, disposition):
    with server(success(), copy.deepcopy(close_plan)) as (url, calls):
        native = client(url, close_timeout_s=0.1)
        result = native.messages.create(**request())
        close = native.close()
        assert native.close() == close
    assert result.usage.input_tokens == 13
    assert close["disposition"] == disposition and not close["closed"]
    assert len(calls) == 2


def test_close_while_active_does_not_cancel_or_erase_late_original_response():
    arrived, release = threading.Event(), threading.Event()
    def held(handler):
        arrived.set()
        assert release.wait(2)
        send(handler, success())
    try:
        with server(held, envelope("pending", close=True)) as (url, calls):
            native = client(url)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(native.messages.create, **request())
                assert arrived.wait(1)
                close = native.close()
                assert close["disposition"] == "pending" and not close["closed"]
                release.set()
                result = future.result(timeout=2)
            assert result.usage.input_tokens == 13 and len(calls) == 2
            assert native.close() == close and len(calls) == 2
    finally:
        release.set()
