"""Commercial BytePlus ModelArk Responses transport: no live network or secret reads."""
from __future__ import annotations

import dataclasses
import json
import sys
import types

import pytest

from engine import provider_production_modes as ppm


MODELS = {
    "modelark_glm_flash_api": "glm-5-3-flash-260828",
    "modelark_deepseek_flash_api": "deepseek-v4-1-flash-261017",
    "modelark_dola_coding_api": "dola-seed-2-1-turbo-260628",
}
FAKE_CREDENTIAL = "offline-mock-only-value"


@pytest.fixture(autouse=True)
def safe_telemetry(monkeypatch, tmp_path):
    monkeypatch.setenv("PROVIDER_HEALTH_DISABLED", "1")
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(tmp_path / "cost"))
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(tmp_path / "health"))


def prepare(monkeypatch, tmp_path, mode_id, *, qualify=False):
    source = json.loads(ppm.DEFAULT_PATH.read_text())
    source["modes"][mode_id]["enabled"] = True
    target = tmp_path / "modes.json"
    target.write_text(json.dumps(source))
    monkeypatch.setattr(ppm, "DEFAULT_PATH", target)
    if qualify:
        profiles = dict(ppm.MODELARK_RESPONSES_PROFILES)
        profiles[mode_id] = dataclasses.replace(
            profiles[mode_id], qualification=ppm.PROFILE_QUALIFIED_CANARY,
        )
        monkeypatch.setattr(ppm, "MODELARK_RESPONSES_PROFILES", profiles)


def spy_http(monkeypatch, *, model, text="mock answer", response_status="completed",
             http_status=200, input_tokens=11, output_tokens=5,
             error=None, bad_json=False):
    calls = {"mount": [], "post": [], "closed": 0}

    class FakeResponse:
        status_code = http_status

        def json(self):
            if bad_json:
                raise ValueError("no JSON")
            return {
                "model": model,
                "status": response_status,
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": text}]},
                ],
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            calls["mount"].append({"prefix": prefix, "adapter": adapter})

        def post(self, url, **kwargs):
            calls["post"].append({"url": url, **kwargs})
            if error is not None:
                raise error
            return FakeResponse()

        def close(self):
            calls["closed"] += 1

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(
        Session=FakeSession,
        adapters=types.SimpleNamespace(HTTPAdapter=lambda **kw: kw),
    ))
    return calls


def test_shipped_provider_is_commercial_off_and_model_locked():
    assert dict(ppm.MODELARK_MODELS) == MODELS
    modes = ppm.load_modes()
    for mode_id, model in MODELS.items():
        mode = modes[mode_id]
        profile = ppm.MODELARK_RESPONSES_PROFILES[mode_id]
        assert mode.enabled is False
        assert mode.default_model == profile.model == model
        assert profile.qualification == ppm.PROFILE_UNQUALIFIED_PENDING_CANARY
        assert (mode.provider_id, mode.protocol) == ("byteplus", ppm.PROTOCOL_RESPONSES)
        assert mode.base_url == "https://ark.ap-southeast.bytepluses.com/api/v3"
        assert mode.secret_ref == "BYTEPLUS_MODELARK_API_KEY"
        assert mode.cost_identity == "byteplus/metered"
        assert mode.cap_id == "prod_api:byteplus"
        assert mode.subscription_fallback_allowed is False
        assert "/api/coding" not in mode.base_url


@pytest.mark.parametrize("mode_id", MODELS)
def test_shadow_off_does_not_read_key_or_start_transport(monkeypatch, mode_id):
    monkeypatch.setattr(
        ppm, "_resolve_credential",
        lambda *_: pytest.fail("disabled path read a secret"),
    )
    receipt = ppm.call_mode(
        mode_id, "sys", "user", max_tokens=8,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
        transport=lambda **kw: pytest.fail("disabled path made request"),
    )
    assert (receipt.ok, receipt.state, receipt.error_class) == (False, "disabled", "disabled")
    assert receipt.fallback == "none"


@pytest.mark.parametrize("mode_id", MODELS)
def test_enabled_config_alone_does_not_qualify_or_read_key(monkeypatch, tmp_path, mode_id):
    prepare(monkeypatch, tmp_path, mode_id)
    monkeypatch.setattr(
        ppm, "_resolve_credential",
        lambda *_: pytest.fail("unqualified profile read a secret"),
    )
    assert ppm.resolve_mode(mode_id).state == "unqualified"
    receipt = ppm.call_mode(
        mode_id, "sys", "user", max_tokens=8,
        transport=lambda **kw: pytest.fail("unqualified profile made request"),
    )
    assert (receipt.ok, receipt.state, receipt.error_class) == (False, "unqualified", "unsupported")


@pytest.mark.parametrize("field,value", [
    ("base_url", "https://ark.ap-southeast.bytepluses.com/api/coding"),
    ("base_url", "https://evil.example/api/v3"),
    ("base_url", "https://ark.ap-southeast.bytepluses.com/api/v3?redirect=1"),
    ("base_url", "https://ark.ap-southeast.bytepluses.com/api/v3#"),
    ("secret_ref", "BYTEPLUS_CODING_PLAN_KEY"),
    ("default_model", "glm-5-2-260617"),
    ("cost_identity", "byteplus/subscription"),
    ("protocol", "openai_compat"),
    ("subscription_fallback_allowed", True),
])
def test_destination_or_billing_tamper_fails_before_credential(tmp_path, field, value):
    cfg = json.loads(ppm.DEFAULT_PATH.read_text())
    cfg["modes"]["modelark_glm_flash_api"][field] = value
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(cfg))
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.load_modes(path)


@pytest.mark.parametrize("mode_id", MODELS)
def test_qualified_fixture_uses_one_pinned_responses_request(monkeypatch, tmp_path, mode_id):
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    calls = spy_http(monkeypatch, model=MODELS[mode_id])
    receipts = []
    monkeypatch.setattr(ppm.ai_costs, "record_usage", lambda **kw: receipts.append(kw))
    result = ppm.call_mode(
        mode_id, "system", "user", max_tokens=32,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
    )
    assert result.ok is True
    assert result.text == "mock answer"
    assert (result.input_tokens, result.output_tokens) == (11, 5)
    assert result.fallback == "none"
    assert result.price_state in {"known", "unknown"}
    assert result.cost_identity == "byteplus/metered"
    assert len(calls["mount"]) == len(calls["post"]) == calls["closed"] == 1
    assert calls["mount"][0] == {"prefix": "https://", "adapter": {"max_retries": 0}}
    request = calls["post"][0]
    assert request["url"] == "https://ark.ap-southeast.bytepluses.com/api/v3/responses"
    assert request["headers"]["Authorization"] == "Bearer " + FAKE_CREDENTIAL
    assert request["headers"]["Content-Type"] == "application/json"
    assert request["allow_redirects"] is False
    assert request["timeout"] == ppm.DEFAULT_TIMEOUT_S
    assert request["json"] == {
        "model": MODELS[mode_id],
        "input": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ],
        "max_output_tokens": 32,
        "store": False,
    }
    assert len(receipts) == 1
    assert receipts[0]["provider"] == "byteplus"
    assert receipts[0]["model"] == MODELS[mode_id]
    assert FAKE_CREDENTIAL not in repr(result)
    assert FAKE_CREDENTIAL not in repr(receipts)


@pytest.mark.parametrize("served", [None, "wrong-model"])
def test_provider_served_model_must_be_exact(monkeypatch, tmp_path, served):
    mode_id = "modelark_glm_flash_api"
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    spy_http(monkeypatch, model=served)
    usages = []
    monkeypatch.setattr(ppm.ai_costs, "record_usage", lambda **kw: usages.append(kw))
    receipt = ppm.call_mode(
        mode_id, "s", "u", max_tokens=10,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
    )
    assert receipt.ok is False
    assert receipt.error_class == "unsupported"
    assert receipt.text is None
    assert usages == []


@pytest.mark.parametrize("status,text", [
    ("incomplete", "partial"), ("failed", "partial"), ("completed", " "),
])
def test_incomplete_or_empty_is_not_success(monkeypatch, tmp_path, status, text):
    mode_id = "modelark_glm_flash_api"
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    spy_http(monkeypatch, model=MODELS[mode_id], response_status=status, text=text)
    receipt = ppm.call_mode(
        mode_id, "s", "u", max_tokens=10,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
    )
    assert receipt.ok is False and receipt.error_class == "error"
    assert receipt.text is None


@pytest.mark.parametrize("status,error_class", [
    (401, "auth"), (429, "usage_limit"), (503, "transport"), (302, "transport"),
])
def test_http_error_is_single_attempt_and_existing_taxonomy(monkeypatch, tmp_path, status, error_class):
    mode_id = "modelark_deepseek_flash_api"
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    calls = spy_http(monkeypatch, model=MODELS[mode_id], http_status=status)
    receipt = ppm.call_mode(
        mode_id, "s", "u", max_tokens=10,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
    )
    assert receipt.ok is False and receipt.error_class == error_class
    assert len(calls["post"]) == calls["closed"] == 1
    assert calls["post"][0]["allow_redirects"] is False
    assert FAKE_CREDENTIAL not in repr(receipt)


def test_invalid_json_fails_closed_without_content_or_usage(monkeypatch, tmp_path):
    mode_id = "modelark_glm_flash_api"
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    spy_http(monkeypatch, model=MODELS[mode_id], bad_json=True)
    receipt = ppm.call_mode(mode_id, "s", "u", max_tokens=10,
                            env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL})
    assert receipt.ok is False and receipt.error_class == "error"
    assert receipt.text is None
    assert receipt.input_tokens is None and receipt.output_tokens is None


def test_null_usage_remains_unknown_without_fabricated_cost(monkeypatch, tmp_path):
    mode_id = "modelark_glm_flash_api"
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    spy_http(monkeypatch, model=MODELS[mode_id], input_tokens=None, output_tokens=None)
    usages = []
    monkeypatch.setattr(ppm.ai_costs, "record_usage", lambda **kw: usages.append(kw))
    receipt = ppm.call_mode(
        mode_id, "s", "u", max_tokens=10,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
    )
    assert receipt.ok is True
    assert receipt.price_state == "unknown"
    assert receipt.input_tokens is None and receipt.output_tokens is None
    assert usages == []


@pytest.mark.parametrize("bad_count", [-1, True, "12", 1.5, 2**31, None])
def test_malformed_provider_usage_does_not_enter_cost_ledger(monkeypatch, tmp_path, bad_count):
    mode_id = "modelark_glm_flash_api"
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    spy_http(monkeypatch, model=MODELS[mode_id], input_tokens=bad_count, output_tokens=5)
    usage_rows = []
    monkeypatch.setattr(ppm.ai_costs, "record_usage", lambda **kw: usage_rows.append(kw))
    result = ppm.call_mode(
        mode_id, "s", "u", max_tokens=15,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
    )
    assert result.ok is True  # Transport is separate from provenance of usage.
    assert result.price_state == "unknown"
    assert result.input_tokens is None and result.output_tokens is None
    assert usage_rows == []


@pytest.mark.parametrize("bad_max", [0, -1, True, "32", 513, 10**10])
def test_invalid_output_ceiling_refuses_before_credential(monkeypatch, tmp_path, bad_max):
    mode_id = "modelark_glm_flash_api"
    prepare(monkeypatch, tmp_path, mode_id, qualify=True)
    monkeypatch.setattr(ppm, "_resolve_credential",
        lambda *_: pytest.fail("invalid output limit touched commercial credential"))
    result = ppm.call_mode(
        mode_id, "s", "u", max_tokens=bad_max,
        env={"BYTEPLUS_MODELARK_API_KEY": FAKE_CREDENTIAL},
        transport=lambda **kw: pytest.fail("invalid ceiling sent a request"),
    )
    assert result.ok is False
    assert result.error_class == "unsupported"
    assert result.fallback == "none"

