"""Shared consumer operations through the actual owner/policy/capability broker.

Only the outbound client is doubled. Qualification and credentials are synthetic;
these tests do not qualify a production pool or establish live VPS admission.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import llm_auth as auth, news_llm
from engine import fabric_inference_client as transport
from engine.marketing import copy_auditor
from tests.test_fabric_application_binding import binding  # noqa: F401

MODEL = "fixture-model"


def response(text="Grounded context.", *, tokens=(11, 7), tools=False):
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    if tools:
        content.append(SimpleNamespace(type="tool_use", id="tool-1", name="read", input={}))
    return SimpleNamespace(model=MODEL, content=content,
        stop_reason="tool_use" if tools else "end_turn",
        usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]) if tokens else None)


def args(model=MODEL):
    return dict(model=model, max_tokens=100, system="Grounded context only.",
                messages=[{"role": "user", "content": "Explain the observation."}])


def invoke(client, model):
    result = client.messages.create(**args(model))
    return result.content[0].text, None, result


@pytest.fixture
def selected(binding, monkeypatch, tmp_path):
    root, row, document, manifest, events, save, make, identity = binding
    manifest["capabilities"][0]["allowed_lanes"] += ["application", "news-llm", "marketing-auditor"]
    save()
    state = SimpleNamespace(root=root, row=row, document=document, manifest=manifest,
                            events=events, save=save, clients=[], calls=[], plans=[], costs=[], health=[])
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_batch")
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    monkeypatch.setattr(auth, "_repo_root", lambda: root)
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: state.costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: state.health.append(kw))
    monkeypatch.setattr(auth, "_oauth_pool_candidates", Mock(side_effect=AssertionError("native discovery")))
    monkeypatch.setattr("lib.config.secret", Mock(side_effect=AssertionError("legacy credential")))
    monkeypatch.setattr(copy_auditor, "_PROVIDER_CACHE", {})

    class Client:
        def __init__(self, **kwargs):
            self.messages = self
            self.calls = []
            state.clients.append(self)

        def create(self, **kwargs):
            self.calls.append(kwargs)
            state.calls.append(kwargs)
            plan = state.plans.pop(0) if state.plans else response()
            if isinstance(plan, BaseException):
                raise plan
            return plan

    monkeypatch.setattr(transport, "FabricInferenceClient", Client)
    return state


def recipe(cfg=None, **kwargs):
    return auth.build_providers(cfg if cfg is not None else {
        "provider_order": ["oauth", "anthropic", "deepseek"], "usage_lane": "application",
        "workload_profile": "site_batch"}, **kwargs)


def test_recipe_defers_real_binding_and_preserves_selected_unavailable(selected):
    providers = recipe()
    assert auth.is_fabric_selection(providers)
    assert providers[0]["client"] is None and not selected.events and not selected.clients
    selected.row["enabled"] = False
    selected.save()
    with pytest.raises(auth.FabricProviderError, match="binding_unavailable"):
        auth.begin_operation(providers)
    assert auth.is_fabric_selection(providers) and not selected.events and not selected.calls


def test_actual_binder_normalizes_transport_and_attaches_real_policy_receipt(selected):
    operation = auth.begin_operation(recipe(), operation_id="shared-proof-1")
    provider = operation.providers[0]
    assert provider["workload_policy"]["profiles"] == ["site_batch"]
    assert provider["workload_policy"]["allowed_order"] == ["fabric"]
    assert provider["provider"] == "fixture-provider" and provider["model"] == MODEL
    assert provider["usage_cycle_id"] == "shared-proof-1"
    assert auth.make_call(operation.providers, invoke)[0] == "Grounded context."
    assert selected.calls[0]["request_id"] == "shared-proof-1:brain:0"
    assert len(selected.costs) == 1 and selected.costs[0]["provider"] == "fixture-provider"
    operation.close()


def test_reused_recipe_allocates_fresh_client_and_identity_per_operation(selected):
    providers = recipe()
    a, b = auth.begin_operation(providers), auth.begin_operation(providers)
    assert a.operation_id != b.operation_id
    auth.make_call(a.providers, invoke)
    auth.make_call(b.providers, invoke)
    assert len(selected.clients) == 2
    assert selected.calls[0]["request_id"] != selected.calls[1]["request_id"]
    a.close()
    b.close()


def test_one_operation_preserves_identity_for_intentional_steps(selected):
    with auth.begin_operation(recipe(), operation_id="two-step") as operation:
        auth.make_call(operation.providers, invoke)
        auth.make_call(operation.providers, invoke)
    assert [row["request_id"] for row in selected.calls] == ["two-step:brain:0", "two-step:brain:1"]
    assert len(selected.clients) == 1 and len(selected.costs) == 2


def test_close_invalidates_a_retained_client_reference(selected):
    operation = auth.begin_operation(recipe())
    provider = operation.providers[0]
    client = provider["client"]
    operation.close()
    operation.close()
    with pytest.raises(auth.FabricProviderError):
        client.messages.create(**args())
    assert operation.providers == [] and not selected.calls


def test_unknown_is_latched_and_close_does_not_claim_settlement(selected):
    selected.plans = [TimeoutError("private detail")]
    operation = auth.begin_operation(recipe())
    provider = operation.providers[0]
    for _ in range(2):
        with pytest.raises(auth.FabricProviderError, match="fabric_effect_unknown"):
            auth.make_call(operation.providers, invoke)
    operation.close()
    assert provider["_fabric_failure"].effect_unknown
    assert auth.fabric_usage(provider)["input_tokens"] is None
    assert len(selected.calls) == 1 and not selected.costs


def test_close_with_pending_effect_retains_uncertainty(selected):
    operation = auth.begin_operation(recipe())
    provider = operation.providers[0]
    auth.fabric_request_kwargs(provider, args())
    operation.close()
    assert provider["_fabric_pending"] and provider["_fabric_failure"].effect_unknown
    assert not selected.calls


def test_recipe_without_operation_refuses_and_does_not_discover(selected):
    assert auth.make_call(recipe(), invoke) == (None, "fabric_operation_required", None)
    assert not selected.calls and not selected.events


@pytest.mark.parametrize("value", ["", " ", "other_mode"])
def test_host_change_invalidates_a_cached_recipe_before_dispatch(selected, monkeypatch, value):
    providers = recipe()
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, value)
    with pytest.raises(auth.FabricProviderError):
        auth.begin_operation(providers)
    assert not selected.calls and not selected.events


def test_host_selection_removal_does_not_retarget_a_cached_recipe(selected, monkeypatch):
    providers = recipe()
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    with pytest.raises(auth.FabricProviderError, match="selection_changed"):
        auth.begin_operation(providers)
    assert not selected.events


def test_cached_native_provider_cannot_bypass_new_host_selection(selected):
    callback = Mock(side_effect=AssertionError("native callback"))
    native = [{"name": "anthropic", "cred": "synthetic", "client": object(), "model": "legacy"}]
    with pytest.raises(auth.FabricProviderError, match="selection_changed"):
        auth.begin_operation(native)
    assert auth.make_call(native, callback) == (None, "fabric_selection_changed", None)
    callback.assert_not_called()


@pytest.mark.parametrize("profile", [None, "", "unknown", "development_agent"])
def test_caller_profile_presence_is_preserved_and_refused_by_real_owner(selected, profile):
    providers = recipe({"provider_order": ["oauth"], "workload_profile": profile})
    with pytest.raises(auth.FabricProviderError, match="binding_unavailable"):
        auth.begin_operation(providers)
    assert not selected.events and not selected.calls


def test_cached_recipe_rechecks_real_capability_revocation(selected):
    providers = recipe()
    auth.begin_operation(providers).close()
    selected.events.clear()
    selected.manifest["capabilities"][0]["kill_state"] = "killed"
    selected.save()
    with pytest.raises(auth.FabricProviderError):
        auth.begin_operation(providers)
    assert not selected.events and len(selected.clients) == 1


def test_explicit_legacy_false_cannot_weaken_host_selection(selected):
    assert auth.is_fabric_selection(recipe(fabric_selected=False))
    with pytest.raises(auth.FabricProviderError, match="owner_required"):
        auth.build_fabric_provider(lambda: {}, request_id="forged")


def test_trusted_selection_precedes_rung_validation_but_order_alone_grants_nothing(selected, monkeypatch):
    providers = recipe({"provider_order": ["fabric"], "workload_profile": "site_batch"})
    auth.begin_operation(providers).close()
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    with pytest.raises(auth.FabricProviderError, match="binding_not_selected"):
        recipe({"provider_order": ["fabric"]})


def test_two_news_batches_use_actual_owner_and_distinct_operations(selected, monkeypatch):
    monkeypatch.setattr(news_llm, "_cfg", lambda: {"enabled": True, "provider_order": ["oauth"]})
    monkeypatch.setattr(news_llm, "_classify_model", lambda: "legacy-model")
    selected.plans = [response(json.dumps([{"i": 0, "summary": "First observation.", "importance": 60}])),
                      response(json.dumps([{"i": 1, "summary": "Second observation.", "importance": 55}]))]
    headlines = [{"title": "First"}, {"title": "Second"}]
    result = news_llm.annotate(headlines, batch_size=1, max_batches=2)
    assert [row["summary"] for row in result] == ["First observation.", "Second observation."]
    assert len(selected.clients) == 2 and len(selected.costs) == 2
    assert selected.calls[0]["request_id"] != selected.calls[1]["request_id"]
    assert news_llm.enabled() and "shared_fabric" in news_llm.provider_label()


def test_invalid_news_selector_does_not_discover_legacy_credentials(selected, monkeypatch):
    monkeypatch.setattr(news_llm, "_cfg", lambda: {"enabled": True})
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    assert news_llm.enabled() and "unavailable" in news_llm.provider_label()
    headlines = [{"title": "Observation"}]
    assert news_llm.annotate(headlines) == headlines
    assert not selected.events and not selected.calls


def test_cached_auditor_recipe_has_independent_turns_and_preserves_invalid_profile(selected):
    post = [{"text": "Measured observation.", "account": "macro", "kind": "context"}]
    reply = response(json.dumps({"verdicts": [{"n": 1, "verdict": "keep", "codes": [], "note": "Supported."}]}))
    selected.plans = [reply, reply]
    a, b = copy_auditor.audit_batch(post), copy_auditor.audit_batch(post)
    assert a["ok"] and b["ok"]
    assert len(selected.clients) == 2 and len(selected.costs) == 2
    assert len(copy_auditor._PROVIDER_CACHE) == 1
    assert selected.calls[0]["request_id"] != selected.calls[1]["request_id"]
    invalid = {"copywriter": {"llm": {"auditor": {"workload_profile": None}}}}
    assert not copy_auditor.audit_batch(post, cfg=invalid)["ok"]
    assert len(selected.calls) == 2


def test_auditor_cache_distinguishes_absent_and_empty_selectors(selected, monkeypatch):
    acfg = copy_auditor._audit_cfg({})
    copy_auditor._providers(acfg)
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    with pytest.raises(auth.FabricProviderError):
        copy_auditor._providers(acfg)
    assert len(copy_auditor._PROVIDER_CACHE) == 1 and not selected.calls


def test_auditor_refuses_unsolicited_tools_without_replay(selected):
    selected.plans = [response(json.dumps({"verdicts": [{"n": 1, "verdict": "keep", "codes": [], "note": "Supported."}]}), tools=True)]
    result = copy_auditor.audit_batch([{"text": "Measured observation.", "account": "macro", "kind": "context"}])
    assert not result["ok"]
    assert len(selected.calls) == 1 and len(selected.costs) == 1


# --------------------------------------------------------------------------- #
# The declared spend sink, carried through the SAME owner.
#
# A trusted caller that owns its spend outside the repository declares
# ``usage_sink: "none"``. The bound operation carries that declaration, and
# only the repository's own ledger row is suppressed: the real completed usage
# and the health accounting both survive. No other value is honoured, so no
# caller can redirect the write.
# --------------------------------------------------------------------------- #
def test_a_declared_sink_none_suppresses_only_the_repository_ledger_row(selected):
    providers = recipe({"provider_order": ["oauth"], "usage_lane": "application",
                        "workload_profile": "site_batch", "usage_sink": "none"})
    operation = auth.begin_operation(providers)
    assert auth.make_call(operation.providers, invoke)[0] == "Grounded context."
    # The repository ledger row is suppressed...
    assert selected.costs == []
    # ...but the health accounting is NOT, and the real usage is NOT discarded.
    assert len(selected.health) == 1
    usage = auth.fabric_usage(operation.providers[0])
    assert usage["input_tokens"] == 11 and usage["output_tokens"] == 7
    assert usage["usage_state"] == "known"
    operation.close()


def test_the_default_sink_records_the_real_usage_once(selected):
    operation = auth.begin_operation(recipe(), operation_id="shared-sink-default")
    assert auth.make_call(operation.providers, invoke)[0] == "Grounded context."
    assert len(selected.costs) == 1
    row = selected.costs[0]
    assert row["lane"] == "application"
    assert row["provider"] == "fixture-provider"
    assert row["model"] == MODEL
    assert row["input_tokens"] == 11 and row["output_tokens"] == 7
    assert row.get("est_cost_usd") is None    # unknown price is not $0.00
    assert len(selected.health) == 1
    operation.close()


@pytest.mark.parametrize("value,honoured", [
    ("none", True), ("None", True), ("NONE", True),
    (" None", False), ("none ", False), ("none-ish", False),
    ("/tmp/elsewhere.jsonl", False), ("", False), (None, False),
])
def test_only_the_incumbent_sink_value_suppresses_the_repository_ledger(
        selected, value, honoured):
    """The comparison is the incumbent translation lane's own one.

    Exactly "none" (lower-cased) suppresses the repository ledger row. Every
    other value — including a path — is ignored, so no caller can redirect the
    write and no row is silently dropped.
    """
    providers = recipe({"provider_order": ["oauth"], "usage_lane": "application",
                        "workload_profile": "site_batch", "usage_sink": value})
    operation = auth.begin_operation(providers)
    assert auth.make_call(operation.providers, invoke)[0] == "Grounded context."
    assert len(selected.costs) == (0 if honoured else 1)
    # The health accounting is never suppressed, whatever the sink says.
    assert len(selected.health) == 1
    operation.close()
