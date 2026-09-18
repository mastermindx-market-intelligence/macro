"""Discriminating tests for the metered production API usage modes (vertical 1).

Every test injects a transport or patches a module-level name.  Nothing here
reaches the network, a real provider, the real ledgers, a subscription rung, or
whatever value a secret env var happens to hold.
"""
from __future__ import annotations

import ast
import dataclasses
import json
import sys
import types
from pathlib import Path

import pytest

from engine import provider_capacity as pc
from engine import provider_health as ph
from engine import provider_production_modes as ppm
from engine.neuralweb import key_pool

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "provider_production_modes.v1.json"
MODULE_PATH = ROOT / "engine" / "provider_production_modes.py"

#: A string that looks like a live credential.  It is configured as a value
#: nowhere; it exists so the tests can prove it is never read, stored, logged
#: or receipted.
SECRET_VALUE = "sk-live-0000000000000000000000000000000000000000"


@pytest.fixture(autouse=True)
def _no_real_state(monkeypatch, tmp_path):
    """Third line of defence against a test dirtying the checkout's ledgers."""
    monkeypatch.setenv("PROVIDER_HEALTH_DISABLED", "1")
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(tmp_path / "ai_costs_state"))
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(tmp_path / "provider_health.jsonl"))


@pytest.fixture
def receipts(monkeypatch):
    """Capture the existing receipt writers instead of appending real rows."""
    rows: dict[str, list[dict]] = {"health": [], "usage": []}
    monkeypatch.setattr(ph, "record_attempt", lambda **kw: rows["health"].append(kw))
    monkeypatch.setattr(ppm.ai_costs, "record_usage", lambda **kw: rows["usage"].append(kw))
    return rows


class FakeTransport:
    """The documented injectable transport, with call bookkeeping and no I/O."""

    def __init__(self, result=None, exc: BaseException | None = None):
        self.result = result
        self.exc = exc
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc is not None:
            raise self.exc
        return self.result


def _config(tmp_path: Path, *mutators) -> Path:
    """A copy of the real config with the given mutators applied."""
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for mutate in mutators:
        mutate(raw)
    path = tmp_path / "provider_production_modes.v1.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def _enable(*mode_ids: str):
    def mutate(raw):
        for mode_id in mode_ids:
            raw["modes"][mode_id]["enabled"] = True
    return mutate


def _enable_all(raw):
    _enable(*raw["modes"])(raw)


def _set(mode_id: str, key: str, value):
    def mutate(raw):
        raw["modes"][mode_id][key] = value
    return mutate


def _install(monkeypatch, tmp_path: Path, *mutators) -> Path:
    cfg = _config(tmp_path, *mutators)
    monkeypatch.setattr(ppm, "DEFAULT_PATH", cfg)
    return cfg


def test_config_is_the_closed_two_mode_set():
    modes = ppm.load_modes()
    assert set(modes) == {"minimax_payg_api", "glm_general_api"}

    minimax = modes["minimax_payg_api"]
    assert minimax.provider_id == "minimax"
    assert minimax.protocol == "anthropic_compat"
    assert minimax.base_url == "https://api.minimax.io/anthropic"
    assert minimax.default_model == "MiniMax-M2"
    assert minimax.secret_ref == "MINIMAX_API_KEY"
    assert minimax.usage_class == "production_api"
    assert minimax.billing_mode == "metered"
    assert minimax.cost_identity == "minimax/metered"
    assert minimax.cap_id == "prod_api:minimax"
    assert minimax.enabled is False
    assert minimax.subscription_fallback_allowed is False
    assert minimax.docs_ref and minimax.pricing_ref
    assert "minimax-token-plan" in minimax.notes
    assert "production_backend_allowed=false" in minimax.notes

    glm = modes["glm_general_api"]
    assert glm.provider_id == "glm"
    assert glm.protocol == "openai_compat"
    assert glm.base_url == "https://api.z.ai/api/paas/v4"
    assert glm.default_model == "glm-4.6"
    assert glm.secret_ref == "ZAI_API_KEY"
    assert glm.cost_identity == "glm/metered"
    assert glm.cap_id == "prod_api:glm"
    assert glm.enabled is False
    assert glm.subscription_fallback_allowed is False
    assert glm.notes == "distinct from glm-coding-plan (#7103)"

    assert ppm.SCHEMA == "mastermind.provider_production_modes.v1"
    assert json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["schema"] == ppm.SCHEMA
    assert ppm.PRODUCER_PROGRAM == "shared-ai-provider-control"


_REJECTIONS = {
    "unknown_record_key": lambda raw: raw["modes"]["glm_general_api"].update({"api_key": "x"}),
    "unknown_top_level_key": lambda raw: raw.update({"api_ladder": []}),
    "wrong_schema": lambda raw: raw.update({"schema": "mastermind.provider_capacity.v1"}),
    "wrong_producer_program": lambda raw: raw.update({"producer_program": "other"}),
    "secret_value_as_secret_ref": _set("glm_general_api", "secret_ref", SECRET_VALUE),
    "secret_ref_lowercase": _set("glm_general_api", "secret_ref", "zai_api_key"),
    "secret_ref_with_equals": _set("glm_general_api", "secret_ref", "ZAI_API_KEY=abc"),
    "secret_ref_too_short": _set("glm_general_api", "secret_ref", "ZAI"),
    "secret_ref_is_a_long_hex_key": _set("glm_general_api", "secret_ref", "a" * 48),
    "subscription_fallback_true": _set("glm_general_api", "subscription_fallback_allowed", True),
    "subscription_fallback_not_bool": _set("glm_general_api", "subscription_fallback_allowed", "false"),
    "enabled_string_false": _set("glm_general_api", "enabled", "false"),
    "enabled_int": _set("glm_general_api", "enabled", 1),
    "usage_class_subscription": _set("glm_general_api", "usage_class", "subscription"),
    "billing_mode_subscription": _set("glm_general_api", "billing_mode", "subscription"),
    "unknown_protocol": _set("glm_general_api", "protocol", "oauth_compat"),
    "subscription_provider_id": _set("glm_general_api", "provider_id", "oauth"),
    "cost_identity_mismatch": _set("glm_general_api", "cost_identity", "glm/subscription"),
    "cap_id_mismatch": _set("glm_general_api", "cap_id", "prod_api:minimax"),
    "cap_id_without_prefix": _set("glm_general_api", "cap_id", "glm"),
    "base_url_not_https": _set("glm_general_api", "base_url", "http://api.z.ai/api/paas/v4"),
    "base_url_with_query": _set("glm_general_api", "base_url", "https://api.z.ai/api/paas/v4?key=1"),
    "base_url_with_userinfo": _set("glm_general_api", "base_url", "https://u:p@api.z.ai/x"),
    "missing_secret_ref": lambda raw: raw["modes"]["glm_general_api"].pop("secret_ref"),
    "mode_id_not_an_id": lambda raw: raw["modes"].update({"GLM General": raw["modes"]["glm_general_api"]}),
    "empty_modes": lambda raw: raw.update({"modes": {}}),
    "modes_not_an_object": lambda raw: raw.update({"modes": []}),
    "record_not_an_object": lambda raw: raw["modes"].update({"glm_general_api": "glm-4.6"}),
    "notes_not_a_string": _set("glm_general_api", "notes", 7),
}


@pytest.mark.parametrize("mutate", list(_REJECTIONS.values()), ids=list(_REJECTIONS))
def test_closed_set_rejections(tmp_path, mutate):
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.load_modes(_config(tmp_path, mutate))


def test_missing_or_corrupt_config_is_a_config_error(tmp_path):
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.load_modes(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.load_modes(bad)


def test_unknown_mode_id_is_rejected(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable_all)
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.resolve_mode("minimax_token_plan", env={"MINIMAX_API_KEY": SECRET_VALUE})
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.call_mode("glm_coding_plan", "s", "u", max_tokens=4, env={})


def test_resolve_mode_three_states_without_returning_the_value(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable("minimax_payg_api"))
    assert ppm.resolve_mode("glm_general_api", env={}).state == "disabled"
    assert ppm.resolve_mode("minimax_payg_api", env={}).state == "unconfigured"
    assert ppm.resolve_mode("minimax_payg_api", env={"MINIMAX_API_KEY": ""}).state == "unconfigured"
    assert ppm.resolve_mode("minimax_payg_api", env={"MINIMAX_API_KEY": "   "}).state == "unconfigured"

    status = ppm.resolve_mode("minimax_payg_api", env={"MINIMAX_API_KEY": SECRET_VALUE})
    assert status.state == "configured"
    assert status.secret_ref == "MINIMAX_API_KEY"
    assert status.cap_id == "prod_api:minimax"
    assert status.cost_identity == "minimax/metered"
    assert SECRET_VALUE not in repr(status)
    assert SECRET_VALUE not in json.dumps(dataclasses.asdict(status))


def test_shadow_off_and_missing_secret_make_no_transport_call(receipts, monkeypatch, tmp_path):
    transport = FakeTransport("text")
    disabled = ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=8, env={}, transport=transport)
    assert disabled.ok is False
    assert disabled.error_class == "disabled"
    assert disabled.state == "disabled"
    assert disabled.fallback == "none"
    assert disabled.text is None
    assert transport.calls == []

    _install(monkeypatch, tmp_path, _enable_all)
    unconfigured = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env={}, transport=transport)
    assert unconfigured.ok is False
    assert unconfigured.error_class == "unconfigured"
    assert unconfigured.fallback == "none"
    assert transport.calls == []

    assert [row["ok"] for row in receipts["health"]] == [False, False]
    assert [row["error_class"] for row in receipts["health"]] == ["disabled", "unconfigured"]
    assert receipts["usage"] == []


def test_openai_and_anthropic_payloads_normalize_to_the_same_receipt(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable_all)
    env = {"MINIMAX_API_KEY": SECRET_VALUE, "ZAI_API_KEY": SECRET_VALUE}
    glm_transport = FakeTransport({
        "choices": [{"message": {"content": "glm answer"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7},
    })
    minimax_transport = FakeTransport({
        "content": [{"type": "text", "text": "mini"}, {"type": "text", "text": "max answer"}],
        "usage": {"input_tokens": 12, "output_tokens": 7},
    })

    glm = ppm.call_mode("glm_general_api", "s", "u", max_tokens=64, env=env, transport=glm_transport)
    minimax = ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=64, env=env, transport=minimax_transport)

    assert glm.text == "glm answer"
    assert minimax.text == "minimax answer"
    for receipt in (glm, minimax):
        assert receipt.ok is True
        assert receipt.error_class == "none"
        assert receipt.fallback == "none"
        assert (receipt.input_tokens, receipt.output_tokens) == (12, 7)
        assert receipt.state == "configured"
        assert receipt.latency_ms >= 0
    assert (glm.provider_id, glm.protocol, glm.model, glm.cost_identity, glm.cap_id) == (
        "glm", "openai_compat", "glm-4.6", "glm/metered", "prod_api:glm")
    assert (minimax.provider_id, minimax.protocol, minimax.model, minimax.cost_identity, minimax.cap_id) == (
        "minimax", "anthropic_compat", "MiniMax-M2", "minimax/metered", "prod_api:minimax")

    assert json.loads(json.dumps(receipts["usage"], default=str))  # both calls booked a row
    assert {row["provider"] for row in receipts["usage"]} == {"glm", "minimax"}
    assert {row["cost_basis"] for row in receipts["usage"]} == {"metered"}
    assert SECRET_VALUE not in json.dumps(receipts, default=str)


def test_transport_receives_the_mode_and_bounded_arguments(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable("glm_general_api"))
    transport = FakeTransport("ok")
    ppm.call_mode("glm_general_api", "SYS", "USR", max_tokens=42, env={"ZAI_API_KEY": SECRET_VALUE}, transport=transport)
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["system"] == "SYS" and call["user"] == "USR"
    assert call["max_tokens"] == 42
    assert call["timeout_s"] == ppm.DEFAULT_TIMEOUT_S
    assert call["mode"].mode_id == "glm_general_api"
    assert call["mode"].secret_ref == "ZAI_API_KEY"
    assert SECRET_VALUE not in json.dumps({k: str(v) for k, v in call.items()})


def test_glm_default_path_reuses_call_openai_compat_unchanged(receipts, monkeypatch, tmp_path):
    from engine import earnings_qual

    _install(monkeypatch, tmp_path, _enable("glm_general_api"))
    seen: dict = {}

    def fake_call(system, user, oc_cfg, *, max_tokens):
        seen.update({"system": system, "user": user, "oc_cfg": dict(oc_cfg), "max_tokens": max_tokens})
        return "glm text", None

    monkeypatch.setattr(earnings_qual, "_call_openai_compat", fake_call)
    receipt = ppm.call_mode("glm_general_api", "SYS", "USR", max_tokens=42, env={"ZAI_API_KEY": SECRET_VALUE})

    assert receipt.ok is True and receipt.text == "glm text"
    assert seen["oc_cfg"] == {
        "base_url": "https://api.z.ai/api/paas/v4",
        "api_key_env": "ZAI_API_KEY",
        "model": "glm-4.6",
        "timeout_s": ppm.DEFAULT_TIMEOUT_S,
    }
    assert seen["max_tokens"] == 42
    assert seen["system"] == "SYS" and seen["user"] == "USR"
    assert SECRET_VALUE not in json.dumps(seen["oc_cfg"])
    # The shared helper returns no usage block: tokens stay unknown, never invented.
    assert (receipt.input_tokens, receipt.output_tokens) == (None, None)
    assert len(receipts["health"]) == 1
    assert receipts["usage"] == []


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("openai_compat_http_400", "http_4xx"),
        ("openai_compat_http_429", "http_4xx"),
        ("openai_compat_http_503", "http_5xx"),
        ("openai_compat_empty", "empty"),
        ("openai_compat_error", "transport_error"),
        ("openai_compat_bad_shape", "transport_error"),
        ("openai_compat_unconfigured", "transport_error"),
    ],
)
def test_glm_helper_reasons_map_to_bounded_error_classes(receipts, monkeypatch, tmp_path, reason, expected):
    from engine import earnings_qual

    _install(monkeypatch, tmp_path, _enable("glm_general_api"))
    monkeypatch.setattr(earnings_qual, "_call_openai_compat", lambda *a, **k: (None, reason))
    receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env={"ZAI_API_KEY": SECRET_VALUE})
    assert receipt.ok is False
    assert receipt.error_class == expected
    assert receipt.text is None
    assert receipt.fallback == "none"
    assert receipts["usage"] == []
    assert receipts["health"][0]["error_class"] == expected


_BOUNDED_FAILURES = {
    "reason_http_500": FakeTransport(ppm.TransportOutcome(reason="http_500")),
    "status_404": FakeTransport(ppm.TransportOutcome(status_code=404)),
    "status_503": FakeTransport(ppm.TransportOutcome(status_code=503)),
    "reason_timeout": FakeTransport(ppm.TransportOutcome(reason="upstream timeout")),
    "reason_empty": FakeTransport(ppm.TransportOutcome(reason="openai_compat_empty")),
    "blank_text": FakeTransport(ppm.TransportOutcome(text="")),
    "none_result": FakeTransport(None),
    "empty_dict": FakeTransport({}),
    "bad_shape_dict": FakeTransport({"result": "no known shape"}),
    "raises_timeout": FakeTransport(exc=TimeoutError("slow")),
    "raises_generic": FakeTransport(exc=RuntimeError("boom")),
    "raises_status": FakeTransport(exc=type("APIStatusError", (Exception,), {"status_code": 403})("no")),
}


@pytest.mark.parametrize("transport", list(_BOUNDED_FAILURES.values()), ids=list(_BOUNDED_FAILURES))
def test_provider_failures_are_bounded_never_raise(receipts, monkeypatch, tmp_path, transport):
    _install(monkeypatch, tmp_path, _enable_all)
    env = {"MINIMAX_API_KEY": SECRET_VALUE, "ZAI_API_KEY": SECRET_VALUE}
    receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env, transport=transport)
    assert receipt.ok is False
    assert receipt.error_class in ppm.ERROR_CLASSES - {"none", "disabled", "unconfigured"}
    assert receipt.text is None
    assert (receipt.input_tokens, receipt.output_tokens) == (None, None)
    assert receipt.fallback == "none"
    assert receipt.state == "configured"
    assert receipts["usage"] == []
    assert receipts["health"][0]["error_class"] == receipt.error_class


def test_half_known_token_pair_is_not_priced(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable("glm_general_api"))
    transport = FakeTransport({
        "choices": [{"message": {"content": "text"}}],
        "usage": {"prompt_tokens": 9},
    })
    receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env={"ZAI_API_KEY": SECRET_VALUE}, transport=transport)
    assert receipt.ok is True
    assert (receipt.input_tokens, receipt.output_tokens) == (None, None)
    assert receipts["usage"] == []


def test_production_mode_never_borrows_a_subscription_rung(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable_all)
    for name in (
        "CLAUDE_CODE_OAUTH_TOKEN_1",
        "CLAUDE_CODE_OAUTH_TOKEN_7",
        "CODEX_ACCOUNT",
        "CODEX_ACCOUNT_2",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.setenv(name, SECRET_VALUE)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)

    transport = FakeTransport("must never be called")
    receipt = ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=8, transport=transport)

    assert transport.calls == []
    assert receipt.ok is False
    assert receipt.error_class == "unconfigured"
    assert receipt.fallback == "none"
    assert "oauth" not in (receipt.text or "")
    assert SECRET_VALUE not in repr(receipt)

    saved = sys.modules.pop("engine.llm_auth", None)
    try:
        ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=8, transport=transport)
        assert "engine.llm_auth" not in sys.modules
    finally:
        if saved is not None:
            sys.modules["engine.llm_auth"] = saved


def test_receipts_carry_production_identity_and_no_secret(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable_all)
    env = {"MINIMAX_API_KEY": SECRET_VALUE, "ZAI_API_KEY": SECRET_VALUE}
    ok = ppm.call_mode(
        "minimax_payg_api", "s", "u", max_tokens=8, env=env,
        transport=FakeTransport({"content": [{"text": "hi"}], "usage": {"input_tokens": 5, "output_tokens": 6}}),
    )
    assert ok.ok is True
    assert len(receipts["health"]) == 1
    assert len(receipts["usage"]) == 1

    health = receipts["health"][0]
    assert health["lane"] == ppm.LANE
    assert health["context"] == "minimax_payg_api"
    assert health["rung"] == "minimax"
    assert health["cap_id"] == "prod_api:minimax"
    assert health["model"] == "MiniMax-M2"
    assert health["ok"] is True
    assert health["error_class"] == ""
    assert health["latency_ms"] >= 0

    usage = receipts["usage"][0]
    assert usage["lane"] == ppm.LANE
    assert usage["provider"] == "minimax"
    assert usage["cost_basis"] == "metered"
    assert usage["key_id"] == "prod_api:minimax"
    assert usage["model"] == "MiniMax-M2"
    assert (usage["input_tokens"], usage["output_tokens"]) == (5, 6)
    assert SECRET_VALUE not in json.dumps(receipts, default=str)

    receipts["health"].clear()
    receipts["usage"].clear()
    bad = ppm.call_mode(
        "minimax_payg_api", "s", "u", max_tokens=8, env=env,
        transport=FakeTransport(ppm.TransportOutcome(reason="http_503")),
    )
    assert bad.ok is False and bad.error_class == "http_5xx"
    assert len(receipts["health"]) == 1
    assert receipts["health"][0]["error_class"] == "http_5xx"
    assert receipts["usage"] == []


def test_receipt_is_a_frozen_contract():
    expected = {
        "provider_id", "mode_id", "model", "protocol", "ok", "text",
        "input_tokens", "output_tokens", "error_class", "latency_ms",
        "cost_identity", "fallback", "cap_id", "state",
    }
    assert {field.name for field in dataclasses.fields(ppm.ProductionCallReceipt)} == expected
    receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=1, env={})
    assert receipt.error_class == "disabled"
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.ok = True


def test_source_has_no_subscription_or_oauth_client_path():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    strings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)

    forbidden_modules = {"engine.llm_auth", "llm_auth", "engine.codex_provider", "codex_provider"}
    assert not (imported & forbidden_modules)
    assert not any("build_providers" in name for name in imported)
    joined = "\n".join(strings)
    for token in ("CLAUDE_CODE_OAUTH", "CODEX_ACCOUNT", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        assert token not in joined
    assert "api.anthropic.com" not in joined


def test_capacity_v1_and_7103_semantics_are_untouched():
    from engine import provider_capacity

    assert provider_capacity.SCHEMA == "mastermind.provider_capacity.v1"
    assert len(provider_capacity.SUPPORTED_SLOTS) == 12
    slot_cap_ids = {slot.capability_id for slot in provider_capacity.SUPPORTED_SLOTS}
    assert len(slot_cap_ids) == 12
    slot_providers = {slot.provider for slot in provider_capacity.SUPPORTED_SLOTS}
    assert slot_providers == {"claude", "codex", "deepseek"}

    modes = ppm.load_modes()
    assert len(modes) == 2
    for mode in modes.values():
        assert mode.cap_id not in slot_cap_ids
        assert mode.cap_id not in key_pool.POOL_CAPABILITY_IDS
        assert mode.cap_id not in key_pool.PROVIDER_CAPABILITY_IDS
        assert mode.provider_id not in slot_providers
        assert mode.cap_id.startswith("prod_api:")

    assert ppm.SCHEMA != provider_capacity.SCHEMA
    assert not (ROOT / "config" / "provider_subscription_plans.v1.json").exists()
    assert not (ROOT / "engine" / "provider_subscription_plans.py").exists()
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for record in raw["modes"].values():
        # #7103 plan semantics are never adopted as a production-mode key; the
        # only mention allowed is the provenance note pointing back at #7103.
        assert "production_backend_allowed" not in record
        for key, value in record.items():
            if key != "notes":
                assert "production_backend_allowed" not in str(value)
    assert "#7103" in raw["modes"]["glm_general_api"]["notes"]


def _fake_anthropic(monkeypatch, *, message=None, exc: BaseException | None = None) -> dict:
    """Install a fake ``anthropic`` module whose client records its arguments."""
    recorded: dict = {}

    class _Messages:
        def create(self, **kwargs):
            recorded["create"] = kwargs
            if exc is not None:
                raise exc
            return message

    class _Client:
        def __init__(self, **kwargs):
            recorded["client"] = kwargs
            self.messages = _Messages()

    module = types.ModuleType("anthropic")
    module.Anthropic = _Client
    monkeypatch.setitem(sys.modules, "anthropic", module)
    return recorded


def test_minimax_default_path_uses_the_anthropic_sdk_at_the_mode_base_url(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable("minimax_payg_api"))
    monkeypatch.setenv("MINIMAX_API_KEY", SECRET_VALUE)
    message = types.SimpleNamespace(
        content=[types.SimpleNamespace(text="mm answer")],
        usage=types.SimpleNamespace(input_tokens=3, output_tokens=4),
    )
    captured = _fake_anthropic(monkeypatch, message=message)

    receipt = ppm.call_mode("minimax_payg_api", "SYS", "USR", max_tokens=9)

    assert receipt.ok is True
    assert receipt.text == "mm answer"
    assert (receipt.input_tokens, receipt.output_tokens) == (3, 4)
    assert captured["client"] == {"api_key": SECRET_VALUE, "base_url": "https://api.minimax.io/anthropic"}
    assert captured["create"]["model"] == "MiniMax-M2"
    assert captured["create"]["max_tokens"] == 9
    assert captured["create"]["system"] == "SYS"
    assert captured["create"]["messages"] == [{"role": "user", "content": "USR"}]
    assert SECRET_VALUE not in repr(receipt)
    assert SECRET_VALUE not in json.dumps(receipts, default=str)


def test_minimax_missing_sdk_is_a_bounded_error(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable("minimax_payg_api"))
    monkeypatch.setenv("MINIMAX_API_KEY", SECRET_VALUE)
    monkeypatch.setitem(sys.modules, "anthropic", None)
    receipt = ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=8)
    assert receipt.ok is False
    assert receipt.error_class == "transport_error"
    assert receipts["usage"] == []


@pytest.mark.parametrize(
    ("name", "attrs", "expected"),
    [
        ("APIStatusError", {"status_code": 429}, "http_4xx"),
        ("AuthenticationError", {"status_code": 401}, "http_4xx"),
        ("InternalServerError", {"status_code": 503}, "http_5xx"),
        ("APITimeoutError", {}, "timeout"),
        ("APIConnectionError", {}, "transport_error"),
        ("RateLimitError", {}, "http_4xx"),
        ("RuntimeError", {}, "transport_error"),
    ],
)
def test_minimax_sdk_exceptions_map_to_bounded_error_classes(
    receipts, monkeypatch, tmp_path, name, attrs, expected
):
    _install(monkeypatch, tmp_path, _enable("minimax_payg_api"))
    monkeypatch.setenv("MINIMAX_API_KEY", SECRET_VALUE)
    exc_type = type(name, (Exception,), attrs)
    _fake_anthropic(monkeypatch, exc=exc_type("boom"))

    receipt = ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=8)

    assert receipt.ok is False
    assert receipt.error_class == expected
    assert receipt.text is None
    assert receipt.fallback == "none"
    assert receipts["usage"] == []
    assert receipts["health"][0]["error_class"] == expected


# --- independent pins for the two validators review found unpinned ----------


#: The canonical subscription rungs a metered production mode must never
#: masquerade as.  Asserted as a floor of its own, because a test that only
#: rode the live set would go green the moment the set were emptied.
_SUBSCRIPTION_RUNG_PROVIDER_IDS = (
    "oauth",
    "codex",
    "claude",
    "claude_code_oauth",
    "claude_oauth",
    "anthropic_oauth",
)


def _provider_id_of(provider_id: str):
    """Re-point the glm record at ``provider_id`` with a CONSISTENT identity.

    ``cost_identity`` and ``cap_id`` are derived from ``provider_id``, so a
    forbidden id arrives at the ban check with every other validator already
    satisfied — the ban is the only thing left that can refuse it.
    """

    def mutate(raw):
        record = raw["modes"]["glm_general_api"]
        record["provider_id"] = provider_id
        record["cost_identity"] = f"{provider_id}/{ppm.METERED_BILLING_MODE}"
        record["cap_id"] = f"{ppm.CAP_ID_PREFIX}{provider_id}"

    return mutate


def test_the_subscription_rung_ban_is_neither_empty_nor_shrunk():
    assert ppm._FORBIDDEN_PROVIDER_IDS, "the subscription-rung ban must never be emptied"
    dropped = sorted(set(_SUBSCRIPTION_RUNG_PROVIDER_IDS) - ppm._FORBIDDEN_PROVIDER_IDS)
    assert dropped == [], f"subscription-rung ids missing from the ban: {dropped}"


def test_subscription_provider_id_is_refused_when_every_other_field_matches(tmp_path):
    for provider_id in _SUBSCRIPTION_RUNG_PROVIDER_IDS:
        with pytest.raises(ppm.ProductionModeConfigError):
            ppm.load_modes(_config(tmp_path, _provider_id_of(provider_id)))


def test_metered_provider_id_of_the_same_shape_still_loads(tmp_path):
    """Negative control: the refusals above are the ban, not the field shapes."""
    modes = ppm.load_modes(_config(tmp_path, _provider_id_of("glm")))
    assert modes["glm_general_api"].provider_id == "glm"


#: Values that satisfy SECRET_REF_RE's env-var NAME shape yet are still secret
#: VALUES, so only the value detector can refuse them.
_SECRET_VALUE_LOOKALIKES = (
    "AKIAIOSFODNN7EXAMPLE",  # AWS-style access key id
    "DEADBEEF" * 4,  # 32 uppercase hex characters
    "A" * 40,  # 40 characters of the hex/base64 alphabet
)


def test_secret_value_lookalike_is_refused_even_when_the_name_shape_matches(tmp_path):
    for value in _SECRET_VALUE_LOOKALIKES:
        assert ppm.SECRET_REF_RE.match(value), f"{value!r} must pass the NAME shape"
        assert ppm._looks_like_secret_value(value), f"{value!r} must trip the VALUE detector"
        with pytest.raises(ppm.ProductionModeConfigError):
            ppm.load_modes(_config(tmp_path, _set("glm_general_api", "secret_ref", value)))


def test_secret_value_lookalike_is_refused_outside_secret_ref(tmp_path):
    value = "AKIAIOSFODNN7EXAMPLE"
    assert ppm.SECRET_REF_RE.match(value), "the value must pass the NAME shape"
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.load_modes(_config(tmp_path, _set("glm_general_api", "default_model", value)))
