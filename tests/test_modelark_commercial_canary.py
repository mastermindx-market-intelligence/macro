"""ModelArk commercial operator canary: source-only, all provider I/O mocked."""
from __future__ import annotations

import dataclasses
import hashlib
import json

import pytest

from engine import modelark_commercial_canary as canary
from engine import provider_production_modes as ppm

MODE = "modelark_glm_flash_api"
MODEL = "glm-5-3-flash-260828"
TEST_KEY = "canary-synthetic-fixture-never-live"


@pytest.fixture(autouse=True)
def redirect_real_ledgers(monkeypatch, tmp_path):
    monkeypatch.setenv("PROVIDER_HEALTH_DISABLED", "1")
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(tmp_path / "cost"))
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(tmp_path / "health"))


def _sha(path=None):
    return hashlib.sha256((path or ppm.DEFAULT_PATH).read_bytes()).hexdigest()


def _run(monkeypatch, *, mode=MODE, text="CANARY_OK", supplied_env=None):
    monkeypatch.setattr(ppm.ai_costs, "estimate_cost_usd", lambda *a, **kw: 0.0005)
    monkeypatch.setattr(ppm.ai_costs, "record_usage", lambda **kw: None)
    actual_calls = []

    def transport(**kw):
        actual_calls.append(kw)
        return ppm.TransportOutcome(
            text=text, input_tokens=12, output_tokens=5,
            status_code=200,
        )

    original_path = ppm.DEFAULT_PATH
    original_profiles = ppm.MODELARK_RESPONSES_PROFILES
    result = canary.run_canary(
        mode_id=mode, armed_mode=mode,
        expected_source_sha256=_sha(),
        execute=True, env=supplied_env or {"BYTEPLUS_MODELARK_API_KEY": TEST_KEY},
        transport=transport,
    )
    assert ppm.DEFAULT_PATH == original_path
    assert ppm.MODELARK_RESPONSES_PROFILES is original_profiles
    assert len(actual_calls) == 1
    assert actual_calls[0]["mode"].mode_id == mode
    assert actual_calls[0]["credential"] == TEST_KEY
    assert actual_calls[0]["max_tokens"] == canary.MAX_TOKENS
    return result


def test_source_preflight_never_reads_credentials():
    info = canary.source_preflight(expected_source_sha256=_sha())
    assert info["all_modes_off"] is True
    assert info["pinned_model_count"] == 3
    assert info["credentials_read"] is False
    assert info["provider_calls"] == 0
    assert info["production_activation"] is False
    assert info["source_sha256"] == _sha()


@pytest.mark.parametrize("bad_sha", ["", "e" * 64, "ABC", None])
def test_source_pin_mandatory(bad_sha):
    with pytest.raises(canary.CanaryRefusal):
        canary.source_preflight(expected_source_sha256=bad_sha)


def test_any_enabled_mode_blocks_operator_canary(monkeypatch, tmp_path):
    doc = json.loads(ppm.DEFAULT_PATH.read_text())
    doc["modes"][MODE]["enabled"] = True
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(doc))
    with pytest.raises(canary.CanaryRefusal, match="ALL_MODES_OFF"):
        canary.source_preflight(source_path=path, expected_source_sha256=_sha(path))


@pytest.mark.parametrize("arm,execute", [
    ("some-other-mode", True), (MODE, False), (None, True),
])
def test_not_armed_or_not_executing_refuses_before_credentials(monkeypatch, arm, execute):
    monkeypatch.setattr(ppm, "_resolve_credential",
                        lambda *_: pytest.fail("refused probe read a secret"))
    with pytest.raises(canary.CanaryRefusal):
        canary.run_canary(
            mode_id=MODE, armed_mode=arm,
            expected_source_sha256=_sha(), execute=execute,
        )


@pytest.mark.parametrize("estimate", [None, -0.01, 0.011, float("nan"), float("inf"), True])
def test_unknown_or_overcap_price_refuses_before_credential(monkeypatch, estimate):
    monkeypatch.setattr(ppm.ai_costs, "estimate_cost_usd", lambda *a, **kw: estimate)
    monkeypatch.setattr(ppm, "_resolve_credential",
                        lambda *_: pytest.fail("pricing refusal read secret"))
    with pytest.raises(canary.CanaryRefusal, match="PRICING_NOT_QUALIFIED"):
        canary.run_canary(
            mode_id=MODE, armed_mode=MODE,
            expected_source_sha256=_sha(), execute=True,
        )


def test_canary_rehearsal_never_claims_authenticated_issuer(monkeypatch):
    result = _run(monkeypatch)
    assert result["schema"] == canary.SCHEMA
    assert result["canary_observation_passed"] is False
    assert result["injected_transport_rehearsal_passed"] is True
    assert result["effect_state"] == "INJECTED_TRANSPORT_UNVERIFIED"
    assert result["response_match"] is True
    assert result["accounting_known"] is True
    assert result["production_activation"] is False
    assert result["capacity_or_worker_granted"] is False
    assert result["provider_registration_effect"] is False
    assert result["same_operation_replay_allowed"] is False
    assert result["source_mode_enabled"] is False
    assert TEST_KEY not in json.dumps(result)


def test_wrong_text_does_not_qualify_even_rehearsal(monkeypatch):
    result = _run(monkeypatch, text="CANARY_FAIL")
    assert result["injected_transport_rehearsal_passed"] is False
    assert result["response_match"] is False
    assert result["canary_observation_passed"] is False


@pytest.mark.parametrize("mode", sorted(ppm.MODELARK_MODELS))
def test_all_three_modes_use_single_rehearsal_attempt(monkeypatch, mode):
    result = _run(monkeypatch, mode=mode)
    assert result["model"] == ppm.MODELARK_MODELS[mode]
    assert result["mode_id"] == mode
    assert result["one_request_ceiling"] == 1
    assert result["preflight_cost_estimate_usd"] <= canary.MAX_ESTIMATED_USD


def test_concurrent_process_refuses_before_price_or_key(monkeypatch):
    monkeypatch.setattr(canary.threading, "active_count", lambda: 2)
    monkeypatch.setattr(ppm.ai_costs, "estimate_cost_usd",
                        lambda *a: pytest.fail("concurrent probe priced provider"))
    with pytest.raises(canary.CanaryRefusal, match="EXCLUSIVE_PROCESS"):
        canary.run_canary(mode_id=MODE, armed_mode=MODE,
                          expected_source_sha256=_sha(), execute=True)


def test_cli_without_execute_is_nonbillable(capsys):
    code = canary._main(["--mode", MODE, "--source-sha256", _sha()])
    assert code == 64
    output = json.loads(capsys.readouterr().out)
    assert output["canary_observation_passed"] is False
    assert output["reason"] == "CANARY_EXECUTE_FLAG_REQUIRED"
