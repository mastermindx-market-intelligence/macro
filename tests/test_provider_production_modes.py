"""Discriminating tests for the metered production API usage modes (vertical 1).

Every test injects a transport, patches a module-level name, or replaces
``sys.modules["requests"]``/``sys.modules["anthropic"]`` with a recorder.
Nothing here reaches the network, a real provider, the real ledgers, a
subscription rung, or whatever value a secret env var happens to hold.

Round-2 pins added here: the credential DESTINATION is in code (every config
field, one at a time, must be refused), the receipt's error classes are the
INCUMBENT ones from ``engine.provider_health``, ``price_state`` is derived only
from ``lib.ai_costs``, the GLM request body is the provider-owned profile, and
the resolved credential reaches the transports as an argument.

Round-3 pins added here: a 2xx is a success ONLY when its body carried usable
text (an empty or unparseable 200 is ``error``, never a silent ``none`` with
``text=None``), and a ``base_url`` carrying a fragment marker -- even a bare
trailing ``#`` that ``urlsplit`` reports as an empty fragment -- is refused.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import os
import sys
import types
from http import HTTPStatus
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


def _install(
    monkeypatch,
    tmp_path: Path,
    *mutators,
    qualify_glm: bool = True,
) -> Path:
    """Install test config; transport tests opt into a qualified GLM profile."""

    cfg = _config(tmp_path, *mutators)
    monkeypatch.setattr(ppm, "DEFAULT_PATH", cfg)
    if qualify_glm:
        monkeypatch.setattr(
            ppm,
            "GLM_REQUEST_PROFILE",
            dataclasses.replace(
                ppm.GLM_REQUEST_PROFILE,
                qualification=ppm.PROFILE_QUALIFIED_CANARY,
            ),
        )
    return cfg


def test_config_is_the_closed_two_mode_set():
    modes = ppm.load_modes()
    assert set(modes) == {"minimax_payg_api", "glm_general_api"}

    minimax = modes["minimax_payg_api"]
    assert minimax.provider_id == "minimax"
    assert minimax.protocol == "anthropic_compat"
    assert minimax.base_url == "https://api.minimax.io/anthropic"
    assert minimax.default_model == "MiniMax-M3"
    assert minimax.default_model == ppm.MINIMAX_PINNED_MODEL
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
    assert glm.default_model == "glm-5.3-flash"
    assert glm.default_model == ppm.GLM_PINNED_MODEL
    assert glm.secret_ref == "ZAI_API_KEY"
    assert glm.cost_identity == "glm/metered"
    assert glm.cap_id == "prod_api:glm"
    assert glm.enabled is False
    assert glm.subscription_fallback_allowed is False
    assert glm.notes == "distinct from glm-coding-plan (#7103)"

    assert ppm.SCHEMA == "mastermind.provider_production_modes.v1"
    assert json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["schema"] == ppm.SCHEMA
    assert ppm.PRODUCER_PROGRAM == "shared-ai-provider-control"

    # The exact identifiers Sol's pricing PR adds to config/ai_pricing.yml.
    # A rename here would silently stop price_state from ever turning "known",
    # so the strings are pinned rather than compared to themselves.
    assert ppm.MINIMAX_PINNED_MODEL == "MiniMax-M3"
    assert ppm.GLM_PINNED_MODEL == "glm-5.3-flash"
    assert ppm.GLM_REQUEST_PROFILE.qualification == ppm.PROFILE_UNQUALIFIED_PENDING_CANARY

    # The credential destination table is exactly the two shipped modes.
    assert set(ppm._MODE_IDENTITY) == {"minimax_payg_api", "glm_general_api"}
    minimax_identity = ppm._MODE_IDENTITY["minimax_payg_api"]
    assert (minimax_identity.scheme, minimax_identity.authority, minimax_identity.path) == (
        "https", "api.minimax.io", "/anthropic")
    assert minimax_identity.secret_ref == "MINIMAX_API_KEY"
    assert minimax_identity.model == "MiniMax-M3"
    glm_identity = ppm._MODE_IDENTITY["glm_general_api"]
    assert (glm_identity.scheme, glm_identity.authority, glm_identity.path) == (
        "https", "api.z.ai", "/api/paas/v4")
    assert glm_identity.secret_ref == "ZAI_API_KEY"
    assert glm_identity.model == "glm-5.3-flash"


def test_glm_unqualified_refuses_before_credential_resolution_or_transport(
    receipts, monkeypatch, tmp_path
):
    _install(
        monkeypatch,
        tmp_path,
        _enable("glm_general_api"),
        qualify_glm=False,
    )
    credential_reads: list[str] = []

    def credential_spy(mode, env):
        credential_reads.append(mode.mode_id)
        return SECRET_VALUE

    monkeypatch.setattr(ppm, "_resolve_credential", credential_spy)
    transport = FakeTransport("must not run")

    status = ppm.resolve_mode(
        "glm_general_api", env={"ZAI_API_KEY": SECRET_VALUE}
    )
    receipt = ppm.call_mode(
        "glm_general_api",
        "s",
        "u",
        max_tokens=8,
        env={"ZAI_API_KEY": SECRET_VALUE},
        transport=transport,
    )

    assert status.state == "unqualified"
    assert receipt.ok is False
    assert receipt.state == "unqualified"
    assert receipt.error_class == "unsupported"
    assert credential_reads == []
    assert transport.calls == []
    assert receipts["usage"] == []
    assert receipts["health"][0]["error_class"] == "unsupported"


def test_glm_qualification_vocabulary_is_closed_and_drift_refuses_before_credential(
    monkeypatch, tmp_path
):
    assert ppm.REQUEST_PROFILE_QUALIFICATIONS == frozenset(
        {"UNQUALIFIED_PENDING_CANARY", "QUALIFIED_CANARY"}
    )
    with pytest.raises(ppm.ProductionModeConfigError, match="qualification"):
        ppm.RequestProfile(
            model=ppm.GLM_PINNED_MODEL,
            temperature=0.0,
            max_tokens=8,
            qualification="DRIFTED",
        )

    drifted = dataclasses.replace(
        ppm.GLM_REQUEST_PROFILE,
        qualification="UNQUALIFIED_PENDING_CANARY",
    )
    object.__setattr__(drifted, "qualification", "DRIFTED")
    monkeypatch.setattr(ppm, "GLM_REQUEST_PROFILE", drifted)
    _install(
        monkeypatch,
        tmp_path,
        _enable("glm_general_api"),
        qualify_glm=False,
    )

    def forbidden_credential(*_args, **_kwargs):
        raise AssertionError("qualification drift reached credential resolution")

    monkeypatch.setattr(ppm, "_resolve_credential", forbidden_credential)
    with pytest.raises(ppm.ProductionModeConfigError, match="qualification"):
        ppm.resolve_mode(
            "glm_general_api", env={"ZAI_API_KEY": SECRET_VALUE}
        )


def test_qualified_glm_profile_positive_control_reaches_existing_transport(
    receipts, monkeypatch, tmp_path
):
    _install(monkeypatch, tmp_path, _enable("glm_general_api"))
    monkeypatch.setattr(
        ppm,
        "GLM_REQUEST_PROFILE",
        dataclasses.replace(
            ppm.GLM_REQUEST_PROFILE,
            qualification=ppm.PROFILE_QUALIFIED_CANARY,
        ),
    )
    transport = FakeTransport(
        {
            "choices": [{"message": {"content": "qualified glm"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }
    )

    status = ppm.resolve_mode(
        "glm_general_api", env={"ZAI_API_KEY": SECRET_VALUE}
    )
    receipt = ppm.call_mode(
        "glm_general_api",
        "s",
        "u",
        max_tokens=8,
        env={"ZAI_API_KEY": SECRET_VALUE},
        transport=transport,
    )

    assert status.state == "configured"
    assert receipt.ok is True
    assert receipt.text == "qualified glm"
    assert len(transport.calls) == 1
    assert transport.calls[0]["credential"] == SECRET_VALUE


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
    "base_url_with_empty_fragment": _set("glm_general_api", "base_url", "https://api.z.ai/api/paas/v4#"),
    "base_url_with_userinfo": _set("glm_general_api", "base_url", "https://u:p@api.z.ai/x"),
    "missing_secret_ref": lambda raw: raw["modes"]["glm_general_api"].pop("secret_ref"),
    "mode_id_not_an_id": lambda raw: raw["modes"].update({"GLM General": raw["modes"]["glm_general_api"]}),
    "empty_modes": lambda raw: raw.update({"modes": {}}),
    "modes_not_an_object": lambda raw: raw.update({"modes": []}),
    "record_not_an_object": lambda raw: raw["modes"].update({"glm_general_api": "not-a-record"}),
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


#: One mutation per field of the pinned credential destination, for BOTH modes.
#: Each entry is ``(mode_id, mutator)``, applied independently to a copy of the
#: shipped config; every one must be refused before any transport exists.
def _identity_mutations() -> dict[str, tuple[str, object]]:
    cases: dict[str, tuple[str, object]] = {}
    for mode_id, host, path, other_host, other_path, other_provider in (
        ("minimax_payg_api", "api.minimax.io", "/anthropic",
         "api.z.ai", "/api/paas/v4", "glm"),
        ("glm_general_api", "api.z.ai", "/api/paas/v4",
         "api.minimax.io", "/anthropic", "minimax"),
    ):
        base = f"https://{host}{path}"
        cases[f"{mode_id}:wrong_host"] = (mode_id, _set(mode_id, "base_url", f"https://attacker.example{path}"))
        cases[f"{mode_id}:sibling_host"] = (mode_id, _set(mode_id, "base_url", f"https://{host}.attacker.example{path}"))
        cases[f"{mode_id}:other_mode_host"] = (mode_id, _set(mode_id, "base_url", f"https://{other_host}{path}"))
        cases[f"{mode_id}:other_mode_destination"] = (mode_id, _set(mode_id, "base_url", f"https://{other_host}{other_path}"))
        cases[f"{mode_id}:wrong_path"] = (mode_id, _set(mode_id, "base_url", f"https://{host}{path}-v2"))
        cases[f"{mode_id}:path_only"] = (mode_id, _set(mode_id, "base_url", f"https://{host}"))
        cases[f"{mode_id}:port"] = (mode_id, _set(mode_id, "base_url", f"https://{host}:8443{path}"))
        cases[f"{mode_id}:userinfo"] = (mode_id, _set(mode_id, "base_url", f"https://user:pw@{host}{path}"))
        cases[f"{mode_id}:http_scheme"] = (mode_id, _set(mode_id, "base_url", f"http://{host}{path}"))
        cases[f"{mode_id}:query"] = (mode_id, _set(mode_id, "base_url", f"{base}?token=1"))
        cases[f"{mode_id}:fragment"] = (mode_id, _set(mode_id, "base_url", f"{base}#frag"))
        # A bare trailing ``#`` is the same refusal: ``urlsplit`` reports an
        # EMPTY fragment, so only the raw string can see the marker.
        cases[f"{mode_id}:empty_fragment"] = (mode_id, _set(mode_id, "base_url", f"{base}#"))
        # The load-bearing substitution from the review: the OTHER mode's key
        # name on this mode.  It passes every generic validator, so only the
        # pinned destination can refuse it.
        cases[f"{mode_id}:secret_ref_substituted"] = (
            mode_id, _set(mode_id, "secret_ref", "ZAI_API_KEY" if mode_id == "minimax_payg_api" else "MINIMAX_API_KEY"))
        cases[f"{mode_id}:model_legacy"] = (
            mode_id, _set(mode_id, "default_model", "MiniMax-M2" if mode_id == "minimax_payg_api" else "glm-4.6"))
        cases[f"{mode_id}:model_swapped"] = (
            mode_id, _set(mode_id, "default_model", "glm-5.3-flash" if mode_id == "minimax_payg_api" else "MiniMax-M3"))
        cases[f"{mode_id}:provider_id_swapped"] = (mode_id, _set(mode_id, "provider_id", other_provider))
        cases[f"{mode_id}:protocol_swapped"] = (mode_id, _set(mode_id, "protocol", "openai_compat" if mode_id == "minimax_payg_api" else "anthropic_compat"))
        cases[f"{mode_id}:cost_identity_drift"] = (mode_id, _set(mode_id, "cost_identity", f"{mode_id}/metered"))
        cases[f"{mode_id}:cap_id_drift"] = (mode_id, _set(mode_id, "cap_id", f"prod_api:{mode_id}"))

        def rewritten(raw, mode_id=mode_id, path=path):
            # A coherent rename: provider, billing identity, cap id and URL shape
            # all agree with each other, so the PINNED DESTINATION is the only
            # field left that can refuse it.
            record = raw["modes"][mode_id]
            record["provider_id"] = "attacker"
            record["cost_identity"] = f"attacker/{ppm.METERED_BILLING_MODE}"
            record["cap_id"] = f"{ppm.CAP_ID_PREFIX}attacker"
            record["base_url"] = f"https://attacker.example{path}"

        cases[f"{mode_id}:coherent_identity_rewrite"] = (mode_id, rewritten)

    def swapped_mode_ids(raw):
        raw["modes"]["minimax_payg_api"], raw["modes"]["glm_general_api"] = (
            raw["modes"]["glm_general_api"], raw["modes"]["minimax_payg_api"])

    cases["both:mode_records_swapped"] = ("minimax_payg_api", swapped_mode_ids)
    return cases


_IDENTITY_MUTATIONS = _identity_mutations()


@pytest.mark.parametrize(
    ("mode_id", "mutate"), list(_IDENTITY_MUTATIONS.values()), ids=list(_IDENTITY_MUTATIONS)
)
def test_config_drift_from_the_pinned_credential_destination_is_refused(
    receipts, monkeypatch, tmp_path, mode_id, mutate
):
    _install(monkeypatch, tmp_path, _enable_all, mutate)
    env = {"MINIMAX_API_KEY": SECRET_VALUE, "ZAI_API_KEY": SECRET_VALUE}

    # The refusal is a config error, not a receipt: it happens before any state
    # is resolved, so call_mode cannot reach a transport even with a credential
    # present and a transport injected.
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.load_modes(tmp_path / "provider_production_modes.v1.json")

    spy = FakeTransport("must never be called")
    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.call_mode(mode_id, "s", "u", max_tokens=8, env=env, transport=spy)
    assert spy.calls == []

    with pytest.raises(ppm.ProductionModeConfigError):
        ppm.resolve_mode(mode_id, env=env)


def test_the_pinned_identity_table_is_not_the_config_read_back():
    """Negative control: the table is independent code, not derived from JSON."""
    shipped = ppm.load_modes()
    for mode_id, identity in ppm._MODE_IDENTITY.items():
        record = shipped[mode_id]
        assert identity.provider_id == record.provider_id
        assert identity.model == record.default_model
        assert f"{identity.scheme}://{identity.authority}{identity.path}" == record.base_url
    # An identity row for a mode the config does not carry cannot be loaded, and
    # a config record without a row cannot be loaded either.
    assert set(ppm._MODE_IDENTITY) == set(shipped)


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
        "glm", "openai_compat", "glm-5.3-flash", "glm/metered", "prod_api:glm")
    assert (minimax.provider_id, minimax.protocol, minimax.model, minimax.cost_identity, minimax.cap_id) == (
        "minimax", "anthropic_compat", "MiniMax-M3", "minimax/metered", "prod_api:minimax")
    # Price truth is delegated: with the shipped config/ai_pricing.yml (which
    # #7289 may add the rows to) the state follows lib.ai_costs exactly.
    for receipt in (glm, minimax):
        assert receipt.price_state in ppm.PRICE_STATES
        priced = ppm.ai_costs.estimate_cost_usd(receipt.model, 12, 7) is not None
        assert receipt.price_state == ("known" if priced else "unknown")

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
    # The credential crosses the transport boundary as an ARGUMENT (that is the
    # single credential boundary); it must never reach a receipt or a ledger.
    assert call["credential"] == SECRET_VALUE
    receipt = ppm.call_mode(
        "glm_general_api", "SYS", "USR", max_tokens=42,
        env={"ZAI_API_KEY": SECRET_VALUE}, transport=FakeTransport("ok"),
    )
    assert SECRET_VALUE not in repr(receipt)
    assert SECRET_VALUE not in json.dumps(dataclasses.asdict(receipt), default=str)
    assert SECRET_VALUE not in json.dumps(receipts, default=str)


def _glm_usage_result(text: str = "glm answer", prompt: int = 12, completion: int = 7):
    """A real-shaped OpenAI-compatible/GLM payload as an HTTP response."""

    class _Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "choices": [{"message": {"content": text}}],
                "usage": {
                    "prompt_tokens": prompt,
                    "completion_tokens": completion,
                    "total_tokens": prompt + completion,
                },
            }

    return _Response()


def _install_requests_spy(monkeypatch, response):
    """Record every ``requests.post`` the detailed helper makes."""
    calls: list[dict] = []

    class _Requests:
        @staticmethod
        def post(url, *, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return response

    monkeypatch.setitem(sys.modules, "requests", _Requests)
    return calls


def test_glm_default_path_asks_the_detailed_helper_for_usage(receipts, monkeypatch, tmp_path):
    """B4: the detailed helper is the GLM path, and its usage reaches the ledger."""
    from engine import earnings_qual

    _install(monkeypatch, tmp_path, _enable_all)
    seen: dict = {}

    def fake_detailed(system, user, oc_cfg, *, max_tokens, request_profile=None, api_key=None):
        seen.update({
            "system": system, "user": user, "oc_cfg": dict(oc_cfg),
            "max_tokens": max_tokens, "request_profile": dict(request_profile or {}),
            "api_key": api_key,
        })
        return earnings_qual.OpenAICompatResult(
            "glm text", None, {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
            200, None,
        )

    monkeypatch.setattr(earnings_qual, "_call_openai_compat_detailed", fake_detailed)
    receipt = ppm.call_mode("glm_general_api", "SYS", "USR", max_tokens=42, env={"ZAI_API_KEY": SECRET_VALUE})

    assert receipt.ok is True and receipt.text == "glm text"
    assert seen["oc_cfg"] == {
        "base_url": "https://api.z.ai/api/paas/v4",
        "api_key_env": "ZAI_API_KEY",
        "model": "glm-5.3-flash",
        "timeout_s": ppm.DEFAULT_TIMEOUT_S,
    }
    assert seen["max_tokens"] == 42
    assert seen["system"] == "SYS" and seen["user"] == "USR"
    assert seen["request_profile"] == {
        "model": "glm-5.3-flash", "temperature": 0.0, "max_tokens": 42,
    }
    assert seen["api_key"] == SECRET_VALUE
    assert SECRET_VALUE not in json.dumps(seen["oc_cfg"])

    # The provider's own counts, not a character ratio, reach the EXISTING writer.
    assert (receipt.input_tokens, receipt.output_tokens) == (12, 7)
    assert len(receipts["health"]) == 1
    assert len(receipts["usage"]) == 1
    usage = receipts["usage"][0]
    assert usage["provider"] == "glm"
    assert usage["model"] == "glm-5.3-flash"
    assert usage["cost_basis"] == "metered"
    assert usage["key_id"] == "prod_api:glm"
    assert (usage["input_tokens"], usage["output_tokens"]) == (12, 7)


def test_glm_real_shaped_response_body_is_the_profile_and_usage_reaches_the_ledger(
    receipts, monkeypatch, tmp_path
):
    """B4 + B6: one real-shaped HTTP round trip, spied at requests.post."""
    _install(monkeypatch, tmp_path, _enable_all)
    calls = _install_requests_spy(monkeypatch, _glm_usage_result())

    receipt = ppm.call_mode(
        "glm_general_api", "SYS", "USR", max_tokens=32, env={"ZAI_API_KEY": SECRET_VALUE}
    )

    assert receipt.ok is True and receipt.text == "glm answer"
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.z.ai/api/paas/v4/chat/completions"
    assert calls[0]["headers"]["Authorization"] == f"Bearer {SECRET_VALUE}"
    body = calls[0]["json"]
    assert body == {
        "model": "glm-5.3-flash",
        "messages": [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "USR"},
        ],
        "max_tokens": 32,
        "temperature": 0.0,
        "stream": False,
    }
    # The profile is CLOSED: no thinking/reasoning control was invented for an
    # unverified glm-5.3-flash parameter contract, and nothing else was added.
    assert set(body) == {"model", "messages", "max_tokens", "temperature", "stream"}
    # This transport test opts into the explicit test-only qualified profile.
    assert ppm.GLM_REQUEST_PROFILE.qualification == ppm.PROFILE_QUALIFIED_CANARY

    usage = receipts["usage"][0]
    assert usage["provider"] == "glm"
    assert usage["model"] == "glm-5.3-flash"
    assert usage["cost_basis"] == "metered"
    assert (usage["input_tokens"], usage["output_tokens"]) == (12, 7)
    assert receipt.price_state in ppm.PRICE_STATES
    assert SECRET_VALUE not in json.dumps(receipts, default=str)


def test_glm_profile_is_a_max_tokens_ceiling_not_a_caller_field(receipts, monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, _enable_all)
    calls = _install_requests_spy(monkeypatch, _glm_usage_result())
    env = {"ZAI_API_KEY": SECRET_VALUE}

    ppm.call_mode("glm_general_api", "s", "u", max_tokens=1, env=env)
    assert calls[-1]["json"]["max_tokens"] == 1

    ceiling = ppm.GLM_REQUEST_PROFILE.max_tokens
    ppm.call_mode("glm_general_api", "s", "u", max_tokens=ceiling * 4, env=env)
    assert calls[-1]["json"]["max_tokens"] == ceiling

    # No caller kwarg reaches the body: an extra payload field is a TypeError at
    # the call boundary, and an alien profile key is refused by the helper.
    with pytest.raises(TypeError):
        ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env, temperature=0.7)
    with pytest.raises(TypeError):
        ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env, request_profile={"model": "x"})

    from engine import earnings_qual

    with pytest.raises(ValueError):
        earnings_qual._call_openai_compat_detailed(
            "s", "u",
            {"base_url": "https://api.z.ai/api/paas/v4", "model": "glm-5.3-flash"},
            max_tokens=8,
            request_profile={"tool_choice": "none"},
        )


def test_glm_http_statuses_map_to_the_incumbent_classes(receipts, monkeypatch, tmp_path):
    """B3 on the GLM side: the real 401/403/429/5xx path, through the helper."""
    _install(monkeypatch, tmp_path, _enable_all)

    class _Response:
        def __init__(self, status):
            self.status_code = status

        @staticmethod
        def json():
            return {"error": "nope"}

    env = {"ZAI_API_KEY": SECRET_VALUE}
    for status, expected in ((401, "auth"), (403, "auth"), (429, "usage_limit"), (500, "transport"), (503, "transport")):
        _install_requests_spy(monkeypatch, _Response(status))
        receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env)
        assert receipt.ok is False
        assert receipt.error_class == expected, (status, receipt.error_class)
        assert receipt.price_state == "unknown"
    assert receipts["usage"] == []


def _glm_json_response(payload, status: int = 200):
    """A minimal ``requests`` response, so a real status crosses the helper."""

    class _Response:
        status_code = status

        @staticmethod
        def json():
            return payload

    return _Response()


#: Real-shaped GLM 200 bodies carrying NO usable text.  The detailed helper
#: returns each of these WITH ``status_code=200`` and ``error_kind`` ``empty`` /
#: ``bad_shape`` -- the exact shape that used to be booked ``none``/``ok=True``.
_GLM_200_WITHOUT_TEXT = {
    "empty_content": {
        "choices": [{"message": {"content": ""}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7},
    },
    "no_choices": {
        "choices": [],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7},
    },
    "choices_wrong_type": {"choices": "nope"},
    "missing_message": {
        "choices": [{}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7},
    },
    "blank_content": {"choices": [{"message": {"content": "   "}}]},
}


@pytest.mark.parametrize(
    "payload", list(_GLM_200_WITHOUT_TEXT.values()), ids=list(_GLM_200_WITHOUT_TEXT)
)
def test_glm_200_without_usable_text_is_an_error_not_a_success(
    receipts, monkeypatch, tmp_path, payload
):
    """R3/B3: a 2xx is a success ONLY when its body carried usable text."""
    _install(monkeypatch, tmp_path, _enable_all)
    calls = _install_requests_spy(monkeypatch, _glm_json_response(payload))

    receipt = ppm.call_mode(
        "glm_general_api", "s", "u", max_tokens=8, env={"ZAI_API_KEY": SECRET_VALUE}
    )

    # A REAL 200 crosses the helper here, not a status-less mock.
    assert len(calls) == 1
    assert receipt.ok is False
    assert receipt.error_class == "error"
    assert receipt.text is None
    assert receipt.fallback == "none"
    assert (receipt.input_tokens, receipt.output_tokens) == (None, None)
    assert receipt.price_state == "unknown"
    assert receipts["usage"] == []
    assert [row["ok"] for row in receipts["health"]] == [False]
    assert receipts["health"][0]["error_class"] == "error"


def test_glm_200_with_usable_text_is_still_the_success_path(receipts, monkeypatch, tmp_path):
    """Positive control: the same wire path WITH text stays ``none`` and priced."""
    _install(monkeypatch, tmp_path, _enable_all)
    _install_requests_spy(
        monkeypatch,
        _glm_json_response(
            {
                "choices": [{"message": {"content": "glm answer"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 7},
            }
        ),
    )

    receipt = ppm.call_mode(
        "glm_general_api", "s", "u", max_tokens=8, env={"ZAI_API_KEY": SECRET_VALUE}
    )

    assert receipt.ok is True
    assert receipt.error_class == "none"
    assert receipt.text == "glm answer"
    assert (receipt.input_tokens, receipt.output_tokens) == (12, 7)
    assert len(receipts["health"]) == 1 and receipts["health"][0]["ok"] is True
    assert len(receipts["usage"]) == 1


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("openai_compat_http_400", "error"),
        ("openai_compat_http_401", "auth"),
        ("openai_compat_http_403", "auth"),
        ("openai_compat_http_429", "usage_limit"),
        ("openai_compat_http_500", "transport"),
        ("openai_compat_http_503", "transport"),
        ("openai_compat_empty", "error"),
        ("openai_compat_error", "error"),
        ("openai_compat_bad_shape", "error"),
        ("openai_compat_unconfigured", "error"),
    ],
)
def test_glm_helper_reasons_map_to_incumbent_error_classes(receipts, monkeypatch, tmp_path, reason, expected):
    from engine import earnings_qual

    _install(monkeypatch, tmp_path, _enable("glm_general_api"))
    monkeypatch.setattr(
        earnings_qual,
        "_call_openai_compat_detailed",
        lambda *a, **k: earnings_qual.OpenAICompatResult(None, reason, None, None, None),
    )
    receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env={"ZAI_API_KEY": SECRET_VALUE})
    assert receipt.ok is False
    assert receipt.error_class == expected
    assert receipt.text is None
    assert receipt.fallback == "none"
    assert receipts["usage"] == []
    assert receipts["health"][0]["error_class"] == expected


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (ppm.TransportOutcome(status_code=401), "auth"),
        (ppm.TransportOutcome(status_code=403), "auth"),
        (ppm.TransportOutcome(status_code=429), "usage_limit"),
        (ppm.TransportOutcome(status_code=500), "transport"),
        (ppm.TransportOutcome(status_code=503), "transport"),
        (ppm.TransportOutcome(status_code=404), "error"),
        (ppm.TransportOutcome(error_class="timeout"), "timeout"),
        (ppm.TransportOutcome(reason="upstream timeout"), "timeout"),
        (ppm.TransportOutcome(reason="quota exhausted"), "usage_limit"),
        (ppm.TransportOutcome(reason="401 unauthorized"), "auth"),
        (ppm.TransportOutcome(reason="connection reset"), "transport"),
        (ppm.TransportOutcome(reason="openai_compat_empty"), "error"),
        (ppm.TransportOutcome(text=""), "error"),
        (ppm.TransportOutcome(text="   "), "error"),
        (ppm.TransportOutcome(status_code=200), "error"),
        (ppm.TransportOutcome(status_code=200, text="   "), "error"),
        (ppm.TransportOutcome(), "error"),
    ],
)
def test_provider_failures_map_to_the_incumbent_classes(receipts, monkeypatch, tmp_path, outcome, expected):
    """B3 proof table: auth / usage_limit / transport / timeout / residual error."""
    _install(monkeypatch, tmp_path, _enable_all)
    receipt = ppm.call_mode(
        "glm_general_api", "s", "u", max_tokens=8,
        env={"ZAI_API_KEY": SECRET_VALUE}, transport=FakeTransport(outcome),
    )
    assert receipt.ok is False
    assert receipt.error_class == expected
    assert receipt.price_state == "unknown"
    assert receipts["usage"] == []


def test_a_successful_response_is_not_classified_as_a_failure(receipts, monkeypatch, tmp_path):
    """A metered transport reports its 200 status; that is success, not a class."""
    _install(monkeypatch, tmp_path, _enable_all)
    receipt = ppm.call_mode(
        "glm_general_api", "s", "u", max_tokens=8,
        env={"ZAI_API_KEY": SECRET_VALUE},
        transport=FakeTransport(ppm.TransportOutcome(text="ok", status_code=200)),
    )
    assert receipt.ok is True
    assert receipt.error_class == "none"
    assert receipt.text == "ok"
    assert ppm._status_to_error_class(HTTPStatus.OK) == "none"


def test_error_classes_are_the_incumbent_taxonomy_not_an_http_one():
    assert ppm.ERROR_CLASSES == frozenset({
        "none", "disabled", "unconfigured",
        "auth", "usage_limit", "timeout", "transport", "unsupported", "error",
    })
    for removed in ("http_4xx", "http_5xx", "transport_error", "empty"):
        assert removed not in ppm.ERROR_CLASSES
    # The reason-string classifier IS the incumbent decision tree, not a copy.
    for message in ("429 rate limit", "401 unauthorized", "request timed out", "unsupported input"):
        probe = RuntimeError(message)
        assert ppm._incumbent_error_class(message=message) == ph.classify_error(probe)
        assert ppm._incumbent_error_class(message=message) in ppm.ERROR_CLASSES


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
    assert receipt.price_state == "unknown"
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
    assert health["model"] == "MiniMax-M3"
    assert health["ok"] is True
    assert health["error_class"] == ""
    assert health["latency_ms"] >= 0

    usage = receipts["usage"][0]
    assert usage["lane"] == ppm.LANE
    assert usage["provider"] == "minimax"
    assert usage["cost_basis"] == "metered"
    assert usage["key_id"] == "prod_api:minimax"
    assert usage["model"] == "MiniMax-M3"
    assert (usage["input_tokens"], usage["output_tokens"]) == (5, 6)
    assert SECRET_VALUE not in json.dumps(receipts, default=str)

    receipts["health"].clear()
    receipts["usage"].clear()
    bad = ppm.call_mode(
        "minimax_payg_api", "s", "u", max_tokens=8, env=env,
        transport=FakeTransport(ppm.TransportOutcome(reason="http_503")),
    )
    assert bad.ok is False and bad.error_class == "transport"
    assert len(receipts["health"]) == 1
    assert receipts["health"][0]["error_class"] == "transport"
    assert bad.price_state == "unknown"
    assert receipts["usage"] == []


def test_receipt_is_a_frozen_contract():
    expected = {
        "provider_id", "mode_id", "model", "protocol", "ok", "text",
        "input_tokens", "output_tokens", "error_class", "latency_ms",
        "cost_identity", "fallback", "cap_id", "state", "price_state",
    }
    assert {field.name for field in dataclasses.fields(ppm.ProductionCallReceipt)} == expected
    receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=1, env={})
    assert receipt.error_class == "disabled"
    assert receipt.price_state in ppm.PRICE_STATES
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
    for token in (
        "CLAUDE_CODE_OAUTH",
        "CODEX_ACCOUNT",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "_mk_oauth_provider",
    ):
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
    assert captured["create"]["model"] == "MiniMax-M3"
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
    assert receipt.error_class == "unsupported"
    assert receipts["usage"] == []


@pytest.mark.parametrize(
    ("name", "attrs", "expected"),
    [
        ("APIStatusError", {"status_code": 429}, "usage_limit"),
        ("AuthenticationError", {"status_code": 401}, "auth"),
        ("PermissionDeniedError", {"status_code": 403}, "auth"),
        ("InternalServerError", {"status_code": 503}, "transport"),
        ("APITimeoutError", {}, "timeout"),
        ("APIConnectionError", {}, "transport"),
        ("RateLimitError", {}, "usage_limit"),
        ("RuntimeError", {}, "error"),
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


# --- credential boundary (B7) -----------------------------------------------


class _CountingEnv(dict):
    """An ``os.environ`` stand-in that records every name looked up."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookups: list[str] = []

    def get(self, key, default=None):
        self.lookups.append(str(key))
        return super().get(key, default)


def test_transports_send_the_resolved_secret_not_the_environment(
    receipts, monkeypatch, tmp_path
):
    """B7: with os.environ empty (and then decoyed) the injected secret is sent."""
    _install(monkeypatch, tmp_path, _enable_all)
    for name in ("MINIMAX_API_KEY", "ZAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    calls = _install_requests_spy(monkeypatch, _glm_usage_result())
    captured = _fake_anthropic(
        monkeypatch,
        message=types.SimpleNamespace(
            content=[types.SimpleNamespace(text="mm answer")],
            usage=types.SimpleNamespace(input_tokens=3, output_tokens=4),
        ),
    )
    env = {"MINIMAX_API_KEY": SECRET_VALUE, "ZAI_API_KEY": SECRET_VALUE}

    glm_receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env)
    minimax_receipt = ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=8, env=env)

    assert glm_receipt.ok is True and minimax_receipt.ok is True
    assert calls[0]["headers"]["Authorization"] == f"Bearer {SECRET_VALUE}"
    assert captured["client"]["api_key"] == SECRET_VALUE

    # A decoy in os.environ must not beat the injected mapping: the transports
    # receive the credential as an argument and never look it up themselves.
    calls.clear()
    monkeypatch.setenv("ZAI_API_KEY", "zai-decoy-not-a-real-key")
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-decoy-not-a-real-key")
    ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env)
    ppm.call_mode("minimax_payg_api", "s", "u", max_tokens=8, env=env)
    assert calls[0]["headers"]["Authorization"] == f"Bearer {SECRET_VALUE}"
    assert captured["client"]["api_key"] == SECRET_VALUE
    assert "decoy" not in json.dumps(receipts, default=str)
    assert SECRET_VALUE not in json.dumps(receipts, default=str)


def test_environment_only_credential_is_unconfigured_with_an_injected_env(
    receipts, monkeypatch, tmp_path
):
    """B7: an explicit mapping wins over the process environment, both ways."""
    _install(monkeypatch, tmp_path, _enable_all)
    monkeypatch.setenv("ZAI_API_KEY", SECRET_VALUE)
    monkeypatch.setenv("MINIMAX_API_KEY", SECRET_VALUE)
    transport = FakeTransport("must never be called")

    for mode_id in ("minimax_payg_api", "glm_general_api"):
        assert ppm.resolve_mode(mode_id, env={}).state == "unconfigured"
        receipt = ppm.call_mode(mode_id, "s", "u", max_tokens=8, env={}, transport=transport)
        assert receipt.ok is False
        assert receipt.error_class == "unconfigured"
        assert receipt.fallback == "none"
        assert receipt.price_state == "unknown"

    assert transport.calls == []
    assert receipts["usage"] == []
    # ``None`` (not ``{}``) is the documented os.environ boundary.
    assert ppm.resolve_mode("glm_general_api").state == "configured"
    assert ppm.resolve_mode("glm_general_api", None).state == "configured"


def test_call_mode_reads_the_environment_exactly_once_at_its_own_boundary(
    receipts, monkeypatch, tmp_path
):
    _install(monkeypatch, tmp_path, _enable_all)
    monkeypatch.setenv("ZAI_API_KEY", SECRET_VALUE)
    counting = _CountingEnv(os.environ)
    monkeypatch.setattr(os, "environ", counting)
    transport = FakeTransport("ok")

    receipt = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, transport=transport)

    assert receipt.ok is True
    assert counting.lookups.count("ZAI_API_KEY") == 1
    assert transport.calls[0]["credential"] == SECRET_VALUE


# --- price truth (B5) -------------------------------------------------------


def test_price_state_follows_lib_ai_costs_and_nothing_else(
    receipts, monkeypatch, tmp_path
):
    _install(monkeypatch, tmp_path, _enable_all)
    env = {"ZAI_API_KEY": SECRET_VALUE}
    transport = FakeTransport({
        "choices": [{"message": {"content": "x"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7},
    })

    monkeypatch.setattr(ppm.ai_costs, "estimate_cost_usd", lambda *a, **k: 0.25)
    priced = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env, transport=transport)
    assert priced.price_state == "known"
    assert receipts["usage"][-1]["est_cost_usd"] == 0.25

    monkeypatch.setattr(ppm.ai_costs, "estimate_cost_usd", lambda *a, **k: None)
    unpriced = ppm.call_mode("glm_general_api", "s", "u", max_tokens=8, env=env, transport=transport)
    assert unpriced.price_state == "unknown"
    assert receipts["usage"][-1]["est_cost_usd"] is None

    # A failure never claims a price.
    failed = ppm.call_mode(
        "glm_general_api", "s", "u", max_tokens=8, env=env,
        transport=FakeTransport(ppm.TransportOutcome(status_code=503)),
    )
    assert failed.price_state == "unknown"


def test_the_module_keeps_no_price_table_and_no_relative_cost_claim(
    receipts, monkeypatch, tmp_path
):
    source = MODULE_PATH.read_text(encoding="utf-8")
    for token in ("per_mtok", "price_table", "rate_card", "PRICES"):
        assert token not in source
    assert "estimate_cost_usd" in source
    # The shipped pricing table is the ONLY price source; today it prices
    # neither pinned model, and the receipt says so rather than guessing.
    model_transport = FakeTransport({
        "choices": [{"message": {"content": "x"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7},
    })
    _install(monkeypatch, tmp_path, _enable_all)
    env = {"MINIMAX_API_KEY": SECRET_VALUE, "ZAI_API_KEY": SECRET_VALUE}
    for mode_id in ("glm_general_api", "minimax_payg_api"):
        receipt = ppm.call_mode(mode_id, "s", "u", max_tokens=8, env=env, transport=model_transport)
        priced = ppm.ai_costs.estimate_cost_usd(receipt.model, 12, 7) is not None
        assert receipt.price_state == ("known" if priced else "unknown")

    # Assembled from parts so this pin cannot match its own source text.
    forbidden = ("cheap" + "er", "cheap" + "est")
    for path in (MODULE_PATH, CONFIG_PATH, Path(__file__)):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text, f"{token!r} in {path.name}"


# --- shared-helper additivity ------------------------------------------------


def test_legacy_openai_compat_contract_is_unchanged(monkeypatch):
    """The factored helper keeps the exact legacy signature and return shape."""
    from engine import earnings_qual

    signature = inspect.signature(earnings_qual._call_openai_compat)
    assert list(signature.parameters) == ["system", "user", "oc_cfg", "max_tokens"]
    assert signature.parameters["max_tokens"].kind is inspect.Parameter.KEYWORD_ONLY

    calls = _install_requests_spy(monkeypatch, _glm_usage_result())
    legacy = {"base_url": "https://api.z.ai/api/paas/v4", "model": "glm-5.3-flash"}
    assert earnings_qual._call_openai_compat("s", "u", legacy, max_tokens=8) == ("glm answer", None)
    # The legacy path keeps the caller's own max_tokens (no profile ceiling).
    assert calls[-1]["json"]["max_tokens"] == 8

    detailed = earnings_qual._call_openai_compat_detailed("s", "u", legacy, max_tokens=8)
    assert detailed.text == "glm answer"
    assert detailed.reason is None
    assert detailed.usage == {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19}
    assert detailed.status_code == 200
    assert detailed.error_kind is None

    class _Unauthorized:
        status_code = 401

        @staticmethod
        def json():
            return {"error": "nope"}

    _install_requests_spy(monkeypatch, _Unauthorized)
    assert earnings_qual._call_openai_compat("s", "u", legacy, max_tokens=8) == (
        None, "openai_compat_http_401")
    refused = earnings_qual._call_openai_compat_detailed("s", "u", legacy, max_tokens=8)
    assert (refused.reason, refused.status_code, refused.error_kind) == (
        "openai_compat_http_401", 401, "http")


def test_legacy_helper_still_resolves_api_key_env_from_the_environment(monkeypatch):
    from engine import earnings_qual

    monkeypatch.setenv("LEGACY_COMPAT_KEY", "legacy-placeholder-value")
    calls = _install_requests_spy(monkeypatch, _glm_usage_result())
    earnings_qual._call_openai_compat(
        "s", "u",
        {"base_url": "https://api.z.ai/api/paas/v4", "model": "glm-5.3-flash",
         "api_key_env": "LEGACY_COMPAT_KEY"},
        max_tokens=8,
    )
    assert calls[0]["headers"]["Authorization"] == "Bearer legacy-placeholder-value"


def test_the_merge_gate_step_still_names_this_suite():
    ci = (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    assert "tests/test_provider_production_modes.py" in ci
