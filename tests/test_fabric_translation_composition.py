"""Translation consumers composed through the incumbent Fabric application owner.

Only the EXTERNAL transport is synthetic. The owner document, the workload
policy, the capability broker and the shared llm_auth wrapper are the real
incumbent code, and no request ever leaves the process. No production
application mode is enrolled or qualified by these tests: the shipped owner
document stays empty, and the fixture transport is a synthetic QUALIFICATION
of the actual owner, not a configuration change.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from engine import fabric_inference_client as client_module
from engine import llm_auth
from engine import news_translate as nt
from engine import provider_production_modes as owner
from engine import translate as tr
from lib import config as lib_config
from tests.test_fabric_gateway_composition import gateway_module  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]

TRANSPORT_BASE_URL = "http://127.0.0.1:8311/v1"
SECRET_REF = "TEST_FABRIC_PROXY_TOKEN"
PROVIDER_ID = "fixture-provider"
MODEL = "fixture-model"
CAP_ID = "fabric:fixture"
CAPABILITY_ID = "fixture_capability"
LANES = ("news-translate", "translate-profiles")

#: The paired gateway proof needs the pinned Mastermind source (the owner
#: gateway module is loaded from it and its bytes are checked by the fixture).
GATEWAY_SOURCE_ROOT = os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT")
needs_gateway = pytest.mark.skipif(
    not GATEWAY_SOURCE_ROOT, reason="paired Mastermind checkout required")


@pytest.fixture
def fabric(tmp_path, monkeypatch):
    """The real owner, composed against a temp root, with a synthetic transport."""
    root = tmp_path
    cfgdir = root / "config"
    cfgdir.mkdir()
    (cfgdir / "provider_workloads.v1.json").write_text(
        (ROOT / "config/provider_workloads.v1.json").read_text())
    document = json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())
    manifest = {"capabilities": [{"capability_id": CAPABILITY_ID,
                                  "secret_ref": SECRET_REF, "kill_state": "active",
                                  "allowed_lanes": list(LANES)}]}
    transport = owner._ApplicationFabricTransport(
        TRANSPORT_BASE_URL, SECRET_REF, PROVIDER_ID, MODEL, "unknown", CAP_ID,
        CAPABILITY_ID, qualified=True, application_allowed=True,
    )
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", transport)
    row = {k: getattr(transport, k) for k in owner._APPLICATION_IDENTITY_FIELDS}
    row.update(transport_id="fixture_v1", enabled=True, application_allowed=True,
               qualification=owner.PROFILE_QUALIFIED_CANARY,
               qualification_ref="fixture:qualified-source-only",
               qualified_until=time.time() + 3600)
    document["application_fabric_modes"] = {"shared_fabric": row}
    (cfgdir / "provider_production_modes.v1.json").write_text(json.dumps(document))
    (cfgdir / "capability_manifest.yml").write_text(yaml.safe_dump(manifest))
    # The owner reads its document from the lane's own configured root; the
    # repository's own config/ is never written and never consulted.
    monkeypatch.setattr(lib_config, "ROOT", root)

    rec: dict = {
        "init": [], "create": [], "reply": "[]", "stop_reason": "end_turn",
        "usage": SimpleNamespace(input_tokens=11, output_tokens=7),
        "error": None, "tools": False,
    }
    events: list[str] = []
    _real_secret = owner._resolve_credential

    def _secret(mode, env):
        events.append("credential")
        return _real_secret(mode, env)

    monkeypatch.setattr(owner, "_resolve_credential", _secret)

    class _FakeFabricClient:
        def __init__(self, **kwargs):
            events.append("client")
            rec["init"].append(dict(kwargs))
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            rec["create"].append(dict(kwargs))
            if rec["error"] is not None:
                raise rec["error"]
            content = [SimpleNamespace(type="text", text=rec["reply"])]
            if rec["tools"]:
                content.append(SimpleNamespace(type="tool_use", id="tool-1",
                                               name="lookup", input={}))
            return SimpleNamespace(model=kwargs.get("model"), content=content,
                                   stop_reason=rec["stop_reason"], usage=rec["usage"])

    monkeypatch.setattr(client_module, "FabricInferenceClient", _FakeFabricClient)
    monkeypatch.setenv(SECRET_REF, "synthetic-proxy-token-for-offline-test")
    # The host selects the shared Fabric application transport. A test that
    # exercises the caller-config selection removes it again.
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "shared_fabric")
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.delenv("RENDER_NO_DRIP", raising=False)
    # The cost and health ledgers are redirected outside the repository: a unit
    # test must never write a production ledger.
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(root / "state"))
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(root / "health.jsonl"))

    def save():
        (cfgdir / "provider_production_modes.v1.json").write_text(json.dumps(document))
        (cfgdir / "capability_manifest.yml").write_text(yaml.safe_dump(manifest))

    def set_transport(**over):
        """Re-qualify the synthetic transport and its owner document row."""
        fields = {"base_url": TRANSPORT_BASE_URL, "secret_ref": SECRET_REF,
                  "provider_id": PROVIDER_ID, "model": MODEL, "cost_basis": "unknown",
                  "cap_id": CAP_ID, "capability_id": CAPABILITY_ID}
        fields.update(over)
        new = owner._ApplicationFabricTransport(
            qualified=True, application_allowed=True, **fields)
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", new)
        new_row = {k: getattr(new, k) for k in owner._APPLICATION_IDENTITY_FIELDS}
        new_row.update(transport_id="fixture_v1", enabled=True, application_allowed=True,
                       qualification=owner.PROFILE_QUALIFIED_CANARY,
                       qualification_ref="fixture:qualified-source-only",
                       qualified_until=time.time() + 3600)
        row.clear()
        row.update(new_row)
        save()
        return new

    return SimpleNamespace(rec=rec, events=events, root=root, document=document,
                           row=row, manifest=manifest, transport=transport,
                           save=save, set_transport=set_transport)


def _nt_cfg(tmp_path, **over):
    cfg = {"enabled": True, "cache_dir": str(tmp_path / "cache"),
           "model": "deepseek-chat", "batch_size": 16, "usage_lane": "news-translate"}
    cfg.update(over)
    return cfg


def _tr_cfg(tmp_path, **over):
    cfg = {"enabled": True, "model": "deepseek-chat", "batch_size": 20, "max_tokens": 4000}
    cfg.update(over)
    return cfg


def _no_native_credential(monkeypatch):
    """Fail loudly if a native credential is read."""
    def _probe(name):
        pytest.fail(f"native credential {name!r} was read while Fabric was selected")
    monkeypatch.setattr(lib_config, "secret", _probe)


def _ledger_rows(tmp_path):
    path = tmp_path / "state" / "data" / "ai_costs" / "usage.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _health_rows(tmp_path):
    path = tmp_path / "health.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _cache_files(tmp_path):
    cdir = tmp_path / "cache"
    return sorted(p.name for p in cdir.glob("*.json")) if cdir.exists() else []


# --------------------------------------------------------------------------- #
# The consumer outcome: a selected host reaches Fabric, and nothing else.
# --------------------------------------------------------------------------- #
def test_ordinary_translation_reaches_fabric_through_the_incumbent_owner(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == ["美联储降息"]
    assert len(fabric.rec["init"]) == 1
    # The owner composed the transport; no caller supplied a factory or a URL.
    assert fabric.rec["init"][0]["base_url"] == TRANSPORT_BASE_URL
    assert fabric.rec["init"][0]["model"] == MODEL
    assert len(fabric.rec["create"]) == 1


def test_the_lane_composes_against_its_own_config_root_not_the_repository_root(
        fabric, tmp_path, monkeypatch):
    """The owner root is the lane's explicit config.ROOT.

    The repository's own shipped owner document has NO enrolled application
    mode, so a translation that works at all proves the lane composed against
    the configured root. The owner's internal repository root is never used.
    """
    shipped = json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())
    assert shipped["application_fabric_modes"] == {}
    monkeypatch.setattr(
        llm_auth, "_repo_root",
        lambda: pytest.fail("the lane used the owner's internal repository root"))
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    assert nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path)) == ["美联储降息"]


def test_request_carries_the_owners_model_and_the_incumbent_request_identity(
        fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path, model="attacker-model"))
    call = fabric.rec["create"][0]
    assert call["model"] == MODEL                  # the owner's model, not the cfg's
    assert call["request_id"].startswith("news-translate:")
    assert call["request_id"].endswith(":brain:0")  # the shared wrapper's own stamp


def test_source_and_output_order_count_and_language_are_retained(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["第一", "第二"], ensure_ascii=False)
    out = nt.translate_to_zh(["First headline", "Second headline"], _nt_cfg(tmp_path))
    assert out == ["第一", "第二"]
    payload = json.loads(fabric.rec["create"][0]["messages"][0]["content"].split("\n", 1)[1])
    assert payload == ["First headline", "Second headline"]
    assert "Simplified Chinese" in fabric.rec["create"][0]["system"]


def test_zh_to_en_direction_keeps_its_own_language_semantics(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["PBOC announces a 50bp RRR cut"])
    out = nt.translate_to_en(["央行宣布降准0.5个百分点"], _nt_cfg(tmp_path))
    assert out == ["PBOC announces a 50bp RRR cut"]
    assert "into concise, natural English" in fabric.rec["create"][0]["system"]
    assert "into concise, natural Simplified Chinese" not in fabric.rec["create"][0]["system"]


def test_native_language_passthrough_and_empty_source_are_preserved(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    out = nt.translate_to_zh(["已经是中文", "", "Fed cuts rates"], _nt_cfg(tmp_path))
    assert out[0] == "已经是中文"      # already in the target language
    assert out[1] is None               # an empty source stays empty
    assert out[2] == "美联储降息"
    # The empty source is never sent upstream, exactly as on the legacy path.
    payload = json.loads(fabric.rec["create"][0]["messages"][0]["content"].split("\n", 1)[1])
    assert payload == ["Fed cuts rates"]


def test_profile_translation_consumer_reaches_fabric(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["苹果公司是一家科技公司。"], ensure_ascii=False)
    out = tr.translate_to_zh(["Apple is a tech company."], _tr_cfg(tmp_path))
    assert out == ["苹果公司是一家科技公司。"]
    assert len(fabric.rec["create"]) == 1
    assert fabric.rec["create"][0]["model"] == MODEL
    assert fabric.rec["create"][0]["request_id"].startswith("translate-profiles:")


# --------------------------------------------------------------------------- #
# Host and caller selection: the incumbent's CURRENT semantics.
# --------------------------------------------------------------------------- #
def test_a_caller_cfg_selection_reaches_the_incumbent_owner(fabric, tmp_path, monkeypatch):
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE", raising=False)
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path, application_fabric_mode="shared_fabric")
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert len(fabric.rec["create"]) == 1


def test_the_host_selection_wins_over_the_caller_cfg_selection(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "shared_fabric")
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    # The caller names another mode; the host's selection is the one in force.
    cfg = _nt_cfg(tmp_path, application_fabric_mode="other_mode")
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert len(fabric.rec["create"]) == 1


@pytest.mark.parametrize("mode", ["", "not-a-mode", "shared_fabric ", "SHARED_FABRIC"])
def test_a_present_but_invalid_host_selection_refuses(fabric, tmp_path, monkeypatch, mode):
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", mode)
    _no_native_credential(monkeypatch)
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]                    # the honest unavailable contract
    assert fabric.rec["init"] == [] and fabric.rec["create"] == []
    assert fabric.events == []               # no credential, no transport


@pytest.mark.parametrize("mode", [None, "", "not-a-mode", 7])
def test_a_present_but_invalid_caller_selection_refuses(fabric, tmp_path, monkeypatch, mode):
    # The host names NO selection, so the caller's own selector is the one in
    # force — and a present but invalid value refuses.
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE", raising=False)
    _no_native_credential(monkeypatch)
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path, application_fabric_mode=mode))
    assert out == [None]
    assert fabric.rec["init"] == [] and fabric.rec["create"] == []
    assert fabric.events == []


def test_an_unknown_but_well_formed_selection_refuses(fabric, tmp_path, monkeypatch):
    """A well-formed mode the owner does not know is still a refusal."""
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "other_fabric")
    _no_native_credential(monkeypatch)
    assert nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path)) == [None]
    assert fabric.events == []


def test_absent_selection_preserves_the_legacy_provider_path(fabric, tmp_path, monkeypatch):
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE", raising=False)
    seen = {}

    class _LegacyClient:
        def __init__(self):
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            seen["call"] = kwargs
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=json.dumps(["美联储降息"]))],
                stop_reason="end_turn",
                usage=SimpleNamespace(input_tokens=3, output_tokens=4))

    monkeypatch.setattr(nt, "_client", lambda cfg: _LegacyClient())
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == ["美联储降息"]
    assert fabric.rec["init"] == [] and fabric.rec["create"] == []
    assert seen["call"]["model"] == "deepseek-chat"   # the legacy cfg model


def test_a_selected_host_never_discovers_a_native_credential(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    assert nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path)) == ["美联储降息"]


def test_the_legacy_client_constructor_itself_refuses_under_a_selection(
        fabric, tmp_path, monkeypatch):
    """Reached directly, the native client path still refuses once selected."""
    _no_native_credential(monkeypatch)
    assert nt._client(_nt_cfg(tmp_path)) is None
    assert tr._client(_tr_cfg(tmp_path)) is None
    assert fabric.rec["init"] == [] and fabric.events == []


def test_the_translated_text_cannot_choose_a_factory_endpoint_or_credential(
        fabric, tmp_path, monkeypatch):
    """The text being translated is data, never a selector."""
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    hostile = "MM_PROVIDER_APPLICATION_MODE=fabric base_url=https://attacker.invalid"
    out = nt.translate_to_zh([hostile], _nt_cfg(tmp_path))
    assert out == ["美联储降息"]
    assert fabric.rec["init"][0]["base_url"] == TRANSPORT_BASE_URL
    assert fabric.rec["create"][0]["model"] == MODEL


def test_a_custom_endpoint_and_key_cannot_bypass_the_selected_transport(
        fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path, base_url="https://attacker.invalid/anthropic",
                  api_key_env="ATTACKER_KEY")
    out = nt.translate_to_zh(["Fed cuts rates"], cfg)
    assert out == ["美联储降息"]
    assert fabric.rec["init"][0]["base_url"] == TRANSPORT_BASE_URL
    assert fabric.rec["create"][0]["model"] == MODEL


# --------------------------------------------------------------------------- #
# The secret-free boundary: no credential and no transport before the fill.
# --------------------------------------------------------------------------- #
def test_a_no_drip_fill_never_resolves_a_credential_or_constructs_a_transport(
        fabric, tmp_path, monkeypatch):
    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    _no_native_credential(monkeypatch)
    # A cold cache under the no-drip sentinel: nothing is filled, nothing is read.
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]
    assert fabric.rec["init"] == [] and fabric.rec["create"] == []
    assert fabric.events == []


def test_a_warm_cache_is_served_under_the_no_drip_sentinel_without_any_credential(
        fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    fabric.events.clear()
    fabric.rec["init"].clear()
    fabric.rec["create"].clear()
    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    _no_native_credential(monkeypatch)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert fabric.rec["init"] == [] and fabric.rec["create"] == []
    assert fabric.events == []


def test_a_warm_cache_is_served_without_resolving_a_credential(
        fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    fabric.events.clear()
    fabric.rec["init"].clear()
    fabric.rec["create"].clear()
    _no_native_credential(monkeypatch)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert fabric.rec["init"] == [] and fabric.rec["create"] == []
    assert fabric.events == []


def test_a_disabled_lane_never_resolves_a_credential(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path, enabled=False))
    assert out == [None]
    assert fabric.events == []


def test_a_missing_credential_prevents_the_later_fill_but_not_the_cached_output(
        fabric, tmp_path, monkeypatch):
    """The identity is knowable without the secret; the FILL is not ready.

    A warm cache is still served under the lane's own identity, and the
    readiness check reports the truth — it is never fabricated from the
    credential-free inspection.
    """
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    monkeypatch.delenv(SECRET_REF, raising=False)
    fabric.events.clear()
    fabric.rec["init"].clear()
    fabric.rec["create"].clear()
    # The cached output is still served, and no credential is resolved for it.
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert fabric.events == [] and fabric.rec["create"] == []
    # Readiness is the truth: without the credential the transport is not ready.
    ready, reason = nt.translator_ready(cfg)
    assert ready is False and "not eligible" in reason


# --------------------------------------------------------------------------- #
# The operation contract: one identity per batch, and every exit closes.
# --------------------------------------------------------------------------- #
def test_two_independent_batches_use_separate_identities(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    nt.translate_to_zh(["Fed cuts rates"], cfg)
    nt.translate_to_zh(["Other headline"], cfg)
    assert len(fabric.rec["init"]) == 2        # a fresh turn-scoped client
    ids = [c["request_id"] for c in fabric.rec["create"]]
    assert len(set(ids)) == 2 and ids[0] != ids[1]
    assert all(i.startswith("news-translate:") for i in ids)


def test_one_logical_batch_keeps_one_identity_across_its_steps(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["第一"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path, batch_size=1)
    nt.translate_to_zh(["First headline", "Second headline"], cfg)
    ids = [c["request_id"] for c in fabric.rec["create"]]
    assert len(ids) == 2
    assert ids[0].rsplit(":brain:", 1)[0] == ids[1].rsplit(":brain:", 1)[0]
    assert ids[0].endswith(":brain:0") and ids[1].endswith(":brain:1")
    assert len(fabric.rec["init"]) == 1        # ONE transport for the whole batch


def test_every_exit_closes_the_bound_provider(fabric, tmp_path, monkeypatch):
    """Success, refusal and exception all close the local binding."""
    providers = []
    original = llm_auth.build_fabric_provider

    def _build(factory, **kwargs):
        provider = original(factory, **kwargs)
        providers.append(provider)
        return provider

    monkeypatch.setattr(llm_auth, "build_fabric_provider", _build)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)

    # success
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert providers[-1].get("_fabric_closed") is True

    # exception
    fabric.rec["error"] = RuntimeError("upstream refused")
    assert nt.translate_to_zh(["Other headline"], cfg) == [None]
    assert providers[-1].get("_fabric_closed") is True


def test_a_refused_binding_opens_no_provider(fabric, tmp_path, monkeypatch):
    fabric.row["enabled"] = False
    fabric.save()
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]
    assert fabric.rec["init"] == [] and fabric.events == []


# --------------------------------------------------------------------------- #
# Exactly one upstream attempt; an unknown execution stops the operation.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("failure", ["timeout", "typeerror", "empty", "malformed", "truncated"])
def test_exactly_one_upstream_attempt_after_a_failed_reply(fabric, tmp_path, monkeypatch, failure):
    _no_native_credential(monkeypatch)
    if failure == "timeout":
        fabric.rec["error"] = TimeoutError("read timed out")
    elif failure == "typeerror":
        fabric.rec["error"] = TypeError("unexpected keyword argument")
    elif failure == "empty":
        fabric.rec["reply"] = ""
    elif failure == "truncated":
        fabric.rec["stop_reason"] = "max_tokens"
    else:
        fabric.rec["reply"] = "not json at all"
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]
    assert len(fabric.rec["create"]) == 1
    assert len(_health_rows(tmp_path)) == 1    # one attempt, one attempt row


def test_a_failed_batch_stops_the_operation_rather_than_resending(fabric, tmp_path, monkeypatch):
    fabric.rec["error"] = RuntimeError("upstream refused")
    cfg = _nt_cfg(tmp_path, batch_size=1)
    out = nt.translate_to_zh(["First headline", "Second headline"], cfg)
    assert out == [None, None]
    assert len(fabric.rec["create"]) == 1      # the second batch never went upstream
    assert len(fabric.rec["init"]) == 1
    assert len(_health_rows(tmp_path)) == 1


def test_an_unknown_execution_is_not_repeated_and_does_not_poison_the_next_batch(
        fabric, tmp_path, monkeypatch):
    fabric.rec["error"] = TimeoutError("read timed out")
    cfg = _nt_cfg(tmp_path)
    assert nt.translate_to_zh(["First headline"], cfg) == [None]
    assert len(fabric.rec["create"]) == 1
    fabric.rec["error"] = None
    fabric.rec["reply"] = json.dumps(["第二条"], ensure_ascii=False)
    assert nt.translate_to_zh(["Second headline"], cfg) == ["第二条"]
    ids = [c["request_id"] for c in fabric.rec["create"]]
    assert len(set(ids)) == 2                 # a separate identity, never a repeat
    assert len(fabric.rec["init"]) == 2


def test_a_malformed_reply_stops_the_operation(fabric, tmp_path, monkeypatch):
    """A well-formed transport reply that breaks the JSON-array contract still
    ends the operation: there is no second upstream attempt."""
    fabric.rec["reply"] = json.dumps(["多了一条", "又多了一条"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path, batch_size=1)
    out = nt.translate_to_zh(["First headline", "Second headline"], cfg)
    assert out == [None, None]
    assert len(fabric.rec["create"]) == 1


def test_an_unsolicited_tool_is_refused(fabric, tmp_path, monkeypatch):
    fabric.rec["tools"] = True
    fabric.rec["reply"] = "[]"
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]
    assert len(fabric.rec["create"]) == 1


def test_there_is_no_native_fallback_after_a_failed_fabric_call(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["error"] = RuntimeError("upstream refused")
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]
    assert len(fabric.rec["create"]) == 1      # no fallback, no second attempt


# --------------------------------------------------------------------------- #
# Cache identity, eligibility and revocation.
# --------------------------------------------------------------------------- #
def test_cache_identity_names_the_actual_provider_model_and_capability(
        fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    files = _cache_files(tmp_path)
    assert len(files) == 1
    assert files[0] != f"{nt._key('Fed cuts rates')}.json"   # no legacy label collision


def test_a_legacy_cache_entry_is_never_served_to_a_selected_transport(
        fabric, tmp_path, monkeypatch):
    cfg = _nt_cfg(tmp_path)
    cdir = tmp_path / "cache"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / f"{nt._key('Fed cuts rates')}.json").write_text(json.dumps(
        {"text": "Fed cuts rates", "text_zh": "旧缓存条目"}, ensure_ascii=False))
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    out = nt.translate_to_zh(["Fed cuts rates"], cfg)
    assert out == ["美联储降息"]               # not the legacy entry
    assert len(fabric.rec["create"]) == 1


def test_a_warm_fabric_cache_serves_without_an_upstream_call(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert len(fabric.rec["create"]) == 1
    fabric.rec["reply"] = json.dumps(["不应被调用"], ensure_ascii=False)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    assert len(fabric.rec["create"]) == 1     # the cache served it


def test_a_different_model_is_a_different_cache_identity(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    nt.translate_to_zh(["Fed cuts rates"], cfg)
    warm = _cache_files(tmp_path)
    # The same text under a DIFFERENT provider/model/capability is a different
    # entry: the first translation must not be served to the other transport.
    fabric.set_transport(provider_id="other-provider", model="other-model",
                         cap_id="fabric:other")
    fabric.rec["reply"] = json.dumps(["另一条"], ensure_ascii=False)
    out = nt.translate_to_zh(["Fed cuts rates"], cfg)
    assert out == ["另一条"]
    assert len(fabric.rec["create"]) == 2      # the second call missed the cache
    assert len(_cache_files(tmp_path)) == 2 and warm != _cache_files(tmp_path)


def _change_valid_policy_without_revision(fabric):
    path = fabric.root / "config/provider_workloads.v1.json"
    policy = json.loads(path.read_text())
    # Fabric remains allowed. This is a valid content change with the same
    # revision, so the receipt's content hash is the only changed policy ID.
    policy["profiles"]["site_batch"]["allowed_providers"].remove("ollama")
    path.write_text(json.dumps(policy))


@pytest.mark.parametrize("change", ["model", "capability", "policy"])
@pytest.mark.parametrize("target", ["zh", "en"])
def test_valid_identity_change_after_inspection_refuses_before_any_fill(
        fabric, tmp_path, monkeypatch, change, target):
    _no_native_credential(monkeypatch)
    original = owner.ApplicationFabricFactory.inspect
    snapshots = []

    def inspect_then_change(factory, caller_cfg=None):
        snapshot = original(factory, caller_cfg)
        snapshots.append(snapshot)
        if change == "model":
            fabric.set_transport(model="other-valid-model")
        elif change == "capability":
            capability = dict(fabric.manifest["capabilities"][0])
            capability["capability_id"] = "other_valid_capability"
            fabric.manifest["capabilities"].append(capability)
            fabric.set_transport(cap_id="fabric:other", capability_id=capability["capability_id"])
        else:
            _change_valid_policy_without_revision(fabric)
        # Both A and B are genuinely eligible under the same owner checks.
        # An ordinary revocation-only test would not catch this race.
        assert original(factory, caller_cfg) != snapshot
        return snapshot

    monkeypatch.setattr(owner.ApplicationFabricFactory, "inspect", inspect_then_change)
    fabric.rec["reply"] = '["must never be stored"]'
    call, text = (nt.translate_to_zh, "Fed cuts rates") if target == "zh" else (
        nt.translate_to_en, "央行降准")
    assert call([text], _nt_cfg(tmp_path)) == [None]
    assert len(snapshots) == 1
    assert fabric.events == []
    assert fabric.rec["create"] == []
    assert _cache_files(tmp_path) == []
    assert _ledger_rows(tmp_path) == []


def test_same_revision_policy_change_cannot_read_the_previous_warm_cache(
        fabric, tmp_path, monkeypatch):
    cfg = _nt_cfg(tmp_path)
    fabric.rec["reply"] = json.dumps(["原有策略输出"], ensure_ascii=False)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["原有策略输出"]
    first_files = _cache_files(tmp_path)
    _change_valid_policy_without_revision(fabric)
    fabric.rec["reply"] = json.dumps(["当前策略输出"], ensure_ascii=False)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["当前策略输出"]
    assert len(fabric.rec["create"]) == 2
    assert len(_cache_files(tmp_path)) == 2
    assert _cache_files(tmp_path) != first_files


def test_the_two_directions_have_different_cache_identities(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    fabric.rec["reply"] = json.dumps(["PBOC cuts RRR"], ensure_ascii=False)
    nt.translate_to_en(["央行降准"], _nt_cfg(tmp_path))
    assert len(_cache_files(tmp_path)) == 2


def test_owner_ineligibility_is_checked_before_a_cached_entry_is_served(
        fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    # Revoke the owner: the warm cache must not claim a healthy selection.
    fabric.row["qualified_until"] = 1
    fabric.save()
    out = nt.translate_to_zh(["Fed cuts rates"], cfg)
    assert out == [None]
    assert len(fabric.rec["create"]) == 1      # no upstream call either


def test_a_missing_capability_revokes_the_binding(fabric, tmp_path, monkeypatch):
    fabric.manifest["capabilities"][0]["kill_state"] = "killed"
    fabric.save()
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]
    assert fabric.rec["init"] == []


def test_a_revoked_capability_refuses_a_warm_cached_entry(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path)
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]
    fabric.manifest["capabilities"][0]["kill_state"] = "killed"
    fabric.save()
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == [None]
    assert len(fabric.rec["create"]) == 1


# --------------------------------------------------------------------------- #
# The caller's own purpose survives the transport selection.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("profile", [None, "", "unknown-profile", "development_agent"])
def test_an_invalid_caller_profile_is_not_erased_by_the_selection(
        fabric, tmp_path, monkeypatch, profile):
    _no_native_credential(monkeypatch)
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path, workload_profile=profile))
    assert out == [None]
    assert fabric.rec["create"] == []
    assert fabric.events == []


def test_a_valid_caller_profile_still_composes(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path, workload_profile="site_batch")
    assert nt.translate_to_zh(["Fed cuts rates"], cfg) == ["美联储降息"]


# --------------------------------------------------------------------------- #
# Cost and health: one writer, real usage, no fabricated zero.
# --------------------------------------------------------------------------- #
def test_the_incumbent_writers_record_real_usage_once(fabric, tmp_path, monkeypatch):
    _no_native_credential(monkeypatch)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    rows = _ledger_rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["lane"] == "news-translate"
    assert row["provider"] == PROVIDER_ID
    assert row["model"] == MODEL
    assert row["input_tokens"] == 11 and row["output_tokens"] == 7
    assert row["cost_basis"] == "unknown"
    assert row["est_cost_usd"] is None          # unknown price is not $0.00
    health = _health_rows(tmp_path)
    assert len(health) == 1 and health[0]["rung"] == "fabric"


def test_the_lane_own_usage_writer_never_also_runs(fabric, tmp_path, monkeypatch):
    """One writer: the incumbent llm_auth capture, never this lane's own."""
    monkeypatch.setattr(nt, "_record_usage",
                        lambda *a, **k: pytest.fail("the lane's own usage writer ran"))
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == ["美联储降息"]
    assert len(_ledger_rows(tmp_path)) == 1


def test_the_declared_sink_none_suppresses_only_the_repository_ledger_row(
        fabric, tmp_path, monkeypatch):
    """The trusted caller's declared sink travels with the bound operation."""
    providers = []
    original = llm_auth.build_fabric_provider

    def _build(factory, **kwargs):
        provider = original(factory, **kwargs)
        providers.append(provider)
        return provider

    monkeypatch.setattr(llm_auth, "build_fabric_provider", _build)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path, usage_sink="none")
    out = nt.translate_to_zh(["Fed cuts rates"], cfg)
    assert out == ["美联储降息"]
    # The repository ledger row is suppressed...
    assert _ledger_rows(tmp_path) == []
    # ...but the health accounting is NOT, and the real usage is NOT discarded.
    assert len(_health_rows(tmp_path)) == 1
    usage = llm_auth.fabric_usage(providers[-1])
    assert usage["input_tokens"] == 11 and usage["output_tokens"] == 7
    assert usage["usage_state"] == "known"


def test_the_default_sink_records_the_row_once(fabric, tmp_path, monkeypatch):
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert len(_ledger_rows(tmp_path)) == 1
    assert len(_health_rows(tmp_path)) == 1


def test_an_arbitrary_sink_value_never_redirects_the_ledger(fabric, tmp_path, monkeypatch):
    """Only the explicit "none" is honoured; no value is a path."""
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    cfg = _nt_cfg(tmp_path, usage_sink="/tmp/somewhere-else.jsonl")
    nt.translate_to_zh(["Fed cuts rates"], cfg)
    assert len(_ledger_rows(tmp_path)) == 1
    assert not (tmp_path / "somewhere-else.jsonl").exists()


def test_unknown_usage_is_not_recorded_as_zero(fabric, tmp_path, monkeypatch):
    fabric.rec["usage"] = SimpleNamespace(input_tokens=None, output_tokens=None)
    fabric.rec["reply"] = json.dumps(["美联储降息"], ensure_ascii=False)
    out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == ["美联储降息"]
    for row in _ledger_rows(tmp_path):
        assert not (row["input_tokens"] == 0 and row["output_tokens"] == 0)
        assert row.get("note") != "" or row["est_cost_usd"] is None


# --------------------------------------------------------------------------- #
# The PAIRED proof: consumer -> shared client -> gateway -> synthetic upstream.
#
# Nothing here is doubled except the gateway's own external HTTP transport.
# The real FabricInferenceClient, the real shared llm_auth wrapper and the real
# owner gateway run over a loopback bridge, and the synthetic upstream never
# leaves the process. No live provider and no real credential are involved.
# --------------------------------------------------------------------------- #
@needs_gateway
def test_the_translation_consumer_reaches_the_shared_client_and_the_real_gateway(
        gateway_module, tmp_path, monkeypatch):
    from tests.test_fabric_gateway_composition import (
        configure_owned_application, owner_gateway, packet as gateway_packet,
    )

    reply = gateway_packet()
    reply["choices"][0]["message"]["content"] = json.dumps(["美联储降息"], ensure_ascii=False)
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(tmp_path / "state"))
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(tmp_path / "health.jsonl"))
    monkeypatch.setattr(lib_config, "ROOT", tmp_path)
    with owner_gateway(gateway_module, tmp_path, [reply]) as (url, calls, wire, asgi):
        path, manifest = configure_owned_application(monkeypatch, tmp_path, url)
        manifest["capabilities"][0]["allowed_lanes"] += ["news-translate"]
        path.write_text(yaml.safe_dump(manifest))
        out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == ["美联储降息"]
    # The synthetic upstream was called exactly once, through the gateway.
    assert len(calls) == len(wire) == 1
    # The shared client's own request identity reached the gateway.
    key = calls[0]["headers"]["idempotency-key"]
    assert key.startswith("news-translate:") and key.endswith(":brain:0")
    # The accounting owner wrote the real usage once; the lane's own writer did not.
    rows = _ledger_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 11 and rows[0]["output_tokens"] == 7
    assert rows[0]["lane"] == "news-translate"
    assert len(_health_rows(tmp_path)) == 1
    # The entry is cached under the SELECTED transport's own identity.
    assert len(_cache_files(tmp_path)) == 1


@needs_gateway
def test_the_selected_translation_refuses_a_revoked_owner_at_the_gateway(
        gateway_module, tmp_path, monkeypatch):
    """The gateway is real; the owner is revoked before the request goes out."""
    import yaml as _yaml

    from tests.test_fabric_gateway_composition import (
        configure_owned_application, owner_gateway, packet as gateway_packet,
    )

    reply = gateway_packet()
    reply["choices"][0]["message"]["content"] = json.dumps(["美联储降息"], ensure_ascii=False)
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(tmp_path / "state"))
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(tmp_path / "health.jsonl"))
    monkeypatch.setattr(lib_config, "ROOT", tmp_path)
    with owner_gateway(gateway_module, tmp_path, [reply]) as (url, calls, wire, asgi):
        path, manifest = configure_owned_application(monkeypatch, tmp_path, url)
        manifest["capabilities"][0]["allowed_lanes"] += ["news-translate"]
        manifest["capabilities"][0]["kill_state"] = "killed"
        path.write_text(_yaml.safe_dump(manifest))
        out = nt.translate_to_zh(["Fed cuts rates"], _nt_cfg(tmp_path))
    assert out == [None]
    assert calls == [] and wire == []
    assert _ledger_rows(tmp_path) == []
