"""master_brain provider ladder — DeepSeek must not be the only rung.

engine/master_brain.py::_call_model used to hand-build a ONE-RUNG provider
list pointed only at DeepSeek. When the operator's DeepSeek balance ran out,
that single rung failed and the AI Daily Brief (site/aibrief.html) did not
render at all — engine/ai_desk.py inherits the same failure via
_mb._call_model. _call_model now builds a multi-rung ladder (codex -> oauth
-> anthropic -> deepseek) via engine.llm_auth.build_providers() whenever the
lane's legacy llm_* config describes DeepSeek's endpoint (_is_deepseek_lane),
after translating the legacy keys into build_providers' vocabulary
(_ladder_cfg). An operator who pinned some OTHER endpoint keeps the historic
single-provider descriptor untouched.

All stub-based — no network, no real API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import llm_auth as llm_auth_mod  # noqa: E402
from engine import master_brain as mb  # noqa: E402

# The shipped config.yml shape for master_brain/ai_desk before the ladder keys
# were added: only the legacy llm_* keys are present.
_SHIPPED_CFG = {
    "api_key_env": "DEEPSEEK_API_KEY",
    "llm_base_url": "https://api.deepseek.com/anthropic",
    "llm_model": "deepseek-v4-pro",
}

# A lane that deliberately pins a non-DeepSeek endpoint (e.g. an operator who
# swapped master_brain straight to Claude via the legacy llm_* keys).
_CUSTOM_ENDPOINT_CFG = {
    "api_key_env": "ANTHROPIC_API_KEY",
    "llm_base_url": "https://api.anthropic.com",
    "llm_model": "claude-opus-4-8",
}


class _FakeBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, text: str):
        self.stop_reason = None
        self.content = [_FakeBlock(text)]
        self.usage = None


class _FakeMessages:
    def __init__(self, text: str | None = None, exc: BaseException | None = None):
        self._text = text
        self._exc = exc

    def create(self, **kw):
        if self._exc is not None:
            raise self._exc
        return _FakeResponse(self._text)


class _FakeClient:
    def __init__(self, text: str | None = None, exc: BaseException | None = None):
        self.messages = _FakeMessages(text=text, exc=exc)


def _fake_provider(name: str, *, text: str | None = None,
                    exc: BaseException | None = None) -> dict:
    return {
        "name": name,
        "env_var": f"FAKE_{name.upper()}_ENV",
        "cred": "present",
        "client": _FakeClient(text=text, exc=exc),
        "model": f"{name}-fake-model",
        "usage_lane": "test-ladder",
        "usage_stage": "",
    }


# --------------------------------------------------------------------------- #
# 1. _ladder_cfg on the shipped config shape
# --------------------------------------------------------------------------- #
def test_ladder_cfg_translates_shipped_deepseek_key():
    out = mb._ladder_cfg(_SHIPPED_CFG)
    # THE regression this guards: master_brain's api_key_env has always named
    # the DEEPSEEK key. Handed over untranslated, build_providers would read
    # it as the ANTHROPIC key and build a client against api.anthropic.com
    # holding a DeepSeek credential — a rung that 401s on every call.
    assert out["deepseek_key_env"] == "DEEPSEEK_API_KEY"
    assert out["api_key_env"] == "ANTHROPIC_API_KEY"
    assert out["api_key_env"] != "DEEPSEEK_API_KEY"
    assert out["deepseek_base_url"] == "https://api.deepseek.com/anthropic"
    assert out["deepseek_model"] == "deepseek-v4-pro"
    assert out["provider_order"] == ["codex", "oauth", "anthropic", "deepseek"]


# --------------------------------------------------------------------------- #
# 2. _call_model on a DeepSeek-shaped cfg calls build_providers with the
#    operator-mandated rung order.
# --------------------------------------------------------------------------- #
def test_call_model_builds_ladder_via_build_providers(monkeypatch):
    captured: dict = {}

    def _fake_build_providers(cfg, *, opus_model=None, deepseek_model=None, **kw):
        captured["cfg"] = cfg
        captured["opus_model"] = opus_model
        captured["deepseek_model"] = deepseek_model
        return [_fake_provider("codex", text="codex reply"),
                _fake_provider("deepseek", text="deepseek reply")]

    monkeypatch.setattr(llm_auth_mod, "build_providers", _fake_build_providers)

    text, reason = mb._call_model("sys", "user", dict(_SHIPPED_CFG))

    assert captured["cfg"]["provider_order"] == ["codex", "oauth", "anthropic", "deepseek"]
    assert text == "codex reply"
    assert reason is None


# --------------------------------------------------------------------------- #
# 3. Fallthrough — a non-auth failure on rung 1 (codex) must not blank the
#    brief; rung 2 (deepseek) still serves. This is the exact failure that
#    killed the AI Daily Brief when the DeepSeek account ran out of balance
#    (mirrored here on the FIRST rung to prove the waterfall, not the config).
# --------------------------------------------------------------------------- #
def test_call_model_falls_through_a_failed_rung(monkeypatch):
    providers = [
        _fake_provider("codex", exc=RuntimeError("402 Insufficient Balance")),
        _fake_provider("deepseek", text="deepseek saved the brief"),
    ]
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: providers)

    text, reason = mb._call_model("sys", "user", dict(_SHIPPED_CFG))

    assert text == "deepseek saved the brief"
    assert reason is None


# --------------------------------------------------------------------------- #
# 4. Empty ladder (no credentials anywhere) preserves the early-return
#    contract: (None, "no_client_or_key").
# --------------------------------------------------------------------------- #
def test_call_model_empty_ladder_returns_no_client_or_key(monkeypatch):
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: [])

    text, reason = mb._call_model("sys", "user", dict(_SHIPPED_CFG))

    assert text is None
    assert reason == "no_client_or_key"


# --------------------------------------------------------------------------- #
# 5. A non-DeepSeek lane (operator pinned a custom endpoint) must NOT call
#    build_providers — it keeps the historic single-descriptor path.
# --------------------------------------------------------------------------- #
def test_call_model_custom_endpoint_bypasses_ladder(monkeypatch):
    called = {"n": 0}

    def _fake_build_providers(*a, **kw):
        called["n"] += 1
        return []

    monkeypatch.setattr(llm_auth_mod, "build_providers", _fake_build_providers)

    client_calls: list = []

    def _sentinel_client(cfg):
        client_calls.append(True)
        return None  # None -> "no_client_or_key" via the legacy path

    # monkeypatch.setattr restores mb._client automatically at test teardown.
    monkeypatch.setattr(mb, "_client", _sentinel_client)
    text, reason = mb._call_model("sys", "user", dict(_CUSTOM_ENDPOINT_CFG))

    assert called["n"] == 0, "build_providers must not be called for a custom endpoint"
    assert client_calls, "_client() must be called on the legacy single-provider path"
    assert text is None
    assert reason == "no_client_or_key"


# A clean reply with no banned-style tokens (no snake_case, no Q1-4 quad codes, no
# sigma/z-score/percentile forms) so the style lint accepts it on the FIRST pass —
# keeps the served-by/model assertions below independent of the rewrite-retry path.
_CLEAN_REPLY = {
    "summary": "Backdrop stays low risk; liquidity contracting.",
    "regime_read": "Low macro risk with FX risk-on.",
    "conflicts": ["FX risk-on vs contracting liquidity"],
    "rotation_check": "Partly tracking.",
    "transmission": ["liquidity drain -> crypto first"],
    "watch_items": ["FOMC meeting ahead"],
    "confidence": "medium",
}
_STATE = {"macro": {"date": "2026-01-05", "quad": "steady"}}


# --------------------------------------------------------------------------- #
# 6. synthesize() records served_by + the SERVING rung's model — not always
#    "deepseek-v4-pro" — so the load balancer is verifiable from the artifact
#    itself (the coordinator's follow-up concern: nobody could tell from the
#    brief whether Codex served or DeepSeek quietly took every call).
# --------------------------------------------------------------------------- #
def test_synthesize_records_served_by_and_serving_model(monkeypatch):
    providers = [_fake_provider("codex", text=json.dumps(_CLEAN_REPLY))]
    monkeypatch.setattr(llm_auth_mod, "build_providers", lambda *a, **kw: providers)

    brief = mb.synthesize(dict(_STATE), dict(_SHIPPED_CFG), lens="macro")

    assert brief["served_by"] == "codex"
    assert brief["model"] == "codex-fake-model"
    assert brief["model"] != "deepseek-v4-pro"


# --------------------------------------------------------------------------- #
# 7. An OLD-signature `_call_model` stub (3 positional args, no `served` kwarg —
#    the shape several existing tests monkeypatch, e.g.
#    tests/test_master_brain_producer.py:45) must still drive synthesize()
#    without raising; brief["model"] falls back to the cfg value.
# --------------------------------------------------------------------------- #
def test_synthesize_tolerates_old_signature_call_model_stub(monkeypatch):
    def _old_stub(system, user, cfg):   # no `served` kwarg — the pre-follow-up shape
        return json.dumps(_CLEAN_REPLY), None

    monkeypatch.setattr(mb, "_call_model", _old_stub)

    cfg = dict(_SHIPPED_CFG)
    brief = mb.synthesize(dict(_STATE), cfg, lens="macro")

    assert brief["degraded_reason"] is None
    assert brief["summary"] == _CLEAN_REPLY["summary"]
    assert brief["model"] == cfg.get("llm_model", "deepseek-v4-pro")
    assert brief["served_by"] is None   # unknown — the stub never populated `served`


# --------------------------------------------------------------------------- #
# 8. An empty reply must eventually FALL THROUGH to the next rung.
#
# llm_auth.make_call only walks the waterfall on an EXCEPTION — a returned
# (None, "empty_reply") counts as that rung having served, so every retry
# re-enters the ladder at rung 1 and draws the same rung again. With one rung
# that was survivable; with Codex leading the ladder it is not, because the
# Codex adapter takes **kwargs and ignores unknown ones, so the seed nudge
# cannot change its output. A rung stuck returning empty text would blank the
# brief with healthy providers sitting behind it — the exact symptom the ladder
# exists to prevent. _call_model retries the same rung ONCE (the seed nudge is
# what recovered the China lens on 2026-07-20) and then marks it dead so the
# remaining attempts fall through.
# --------------------------------------------------------------------------- #
class _EmptyMessages:
    """Returns a 200 with no text blocks — the shape that blanked china_brief."""

    def __init__(self, seen: list):
        self._seen = seen

    def create(self, **kw):
        self._seen.append("empty-rung")

        class _Resp:
            stop_reason = "end_turn"
            content = []          # no text blocks -> _do_call reports empty_reply
            usage = None

        return _Resp()


class _EmptyClient:
    def __init__(self, seen: list):
        self.messages = _EmptyMessages(seen)


def test_call_model_empty_reply_falls_through_to_the_next_rung(monkeypatch):
    seen: list = []
    dead_rung = {
        "name": "codex", "env_var": "FAKE_CODEX_ENV", "cred": "present",
        "client": _EmptyClient(seen), "model": "codex-fake-model",
    }
    good_rung = _fake_provider("oauth", text=json.dumps(_CLEAN_REPLY))

    monkeypatch.setattr(llm_auth_mod, "build_providers",
                        lambda cfg, **kw: [dead_rung, good_rung])
    monkeypatch.setattr(mb, "_is_deepseek_lane", lambda cfg: True)
    llm_auth_mod.clear_dead()
    try:
        served: dict = {}
        text, reason = mb._call_model(
            "sys", "user", dict(_SHIPPED_CFG), served=served)

        # Same rung twice (seed nudge preserved), THEN the ladder advances.
        assert seen == ["empty-rung", "empty-rung"], seen
        assert text is not None and reason is None
        assert served.get("provider") == "oauth"
        # Would have been None/blank before the fall-through — the reported bug.
        assert json.loads(text)["summary"] == _CLEAN_REPLY["summary"]
    finally:
        llm_auth_mod.clear_dead()


# --------------------------------------------------------------------------- #
# 9. A PARTIALLY swapped config must never send the Anthropic key to DeepSeek.
#
# _is_deepseek_lane accepts a lane on the base URL OR the key name, so the
# documented one-line Opus swap (module docstring) applied to api_key_env/
# llm_model but NOT llm_base_url arrives here mixed. Blind `or api_key_env`
# fallbacks then set deepseek_key_env=ANTHROPIC_API_KEY, and build_providers
# would construct anthropic.Anthropic(api_key=<the Anthropic key>,
# base_url="https://api.deepseek.com/anthropic") — transmitting a live
# credential to a third party. That is the mirror of the collision _ladder_cfg
# exists to close, and strictly worse: the other direction merely 401s.
# --------------------------------------------------------------------------- #
_PARTIAL_SWAP_CFG = {
    "api_key_env": "ANTHROPIC_API_KEY",              # swapped
    "llm_model": "claude-opus-4-8",                  # swapped
    "llm_base_url": "https://api.deepseek.com/anthropic",   # NOT swapped
}


def test_ladder_cfg_never_routes_a_non_deepseek_key_to_deepseek():
    out = mb._ladder_cfg(_PARTIAL_SWAP_CFG)

    # The credential must not follow the stale DeepSeek base URL.
    assert out["deepseek_key_env"] == "DEEPSEEK_API_KEY"
    assert out["deepseek_key_env"] != "ANTHROPIC_API_KEY"
    # A Claude model id must not be served to DeepSeek under its own name.
    assert out["deepseek_model"] == "deepseek-v4-pro"
    # It belongs to the Claude rungs instead.
    assert out["opus_model"] == "claude-opus-4-8"
    assert out["api_key_env"] == "ANTHROPIC_API_KEY"


def test_ladder_cfg_shipped_shape_is_unchanged_by_that_guard():
    """The leak guard must not disturb the shipped DeepSeek-shaped config."""
    out = mb._ladder_cfg(_SHIPPED_CFG)
    assert out["deepseek_key_env"] == "DEEPSEEK_API_KEY"
    assert out["deepseek_base_url"] == _SHIPPED_CFG["llm_base_url"]
    assert out["deepseek_model"] == "deepseek-v4-pro"
    assert out["opus_model"] == "claude-opus-4-8"


# VPS-SITE-BRIEF-W1: real Brief consumer + shared provider builder, with all
# external credential/provider/usage boundaries inert. No network or publication.
import types
import pytest


@pytest.fixture
def policy_boundary(monkeypatch, tmp_path):
    from engine import codex_provider, provider_health, provider_workload_policy as policy
    from engine.neuralweb import key_pool
    from lib import ai_costs, config

    events = {"secrets": [], "native": [], "custom": [], "calls": [],
              "after_call": None, "reply": json.dumps({"summary": "Synthetic brief."})}
    monkeypatch.delenv(policy.HOST_PROFILE_ENV, raising=False)
    document = json.loads(policy.DEFAULT_POLICY_PATH.read_text())
    path = tmp_path / "workload-policy.json"
    path.write_text(json.dumps(document))
    monkeypatch.setattr(policy, "DEFAULT_POLICY_PATH", path)

    class Client:
        def __init__(self, **kwargs):
            self.messages = self
        def create(self, **kwargs):
            events["calls"].append(kwargs["model"])
            if events["after_call"]:
                events["after_call"]()
            if events.get("exception") is not None:
                raise events["exception"]
            return types.SimpleNamespace(stop_reason=None, usage=None,
                content=[types.SimpleNamespace(type="text", text=events["reply"])])

    sdk = types.ModuleType("anthropic")
    sdk.Anthropic = Client
    sdk.DefaultHttpxClient = lambda **kwargs: object()
    monkeypatch.setitem(sys.modules, "anthropic", sdk)
    monkeypatch.setattr(config, "secret", lambda name:
        events["secrets"].append(name) or "synthetic-test-credential")
    monkeypatch.setattr(codex_provider, "available_accounts", lambda:
        events["native"].append("codex") or [])
    monkeypatch.setattr(llm_auth_mod, "_oauth_pool_candidates", lambda *a, **k:
        events["native"].append("oauth") or [])
    monkeypatch.setattr(mb, "_client", lambda cfg:
        events["custom"].append("custom") or Client())
    for name, value in [("discover_present_keys", []), ("is_enabled", True),
                        ("is_cooling", False), ("window_load", 0), ("record_session", None)]:
        monkeypatch.setattr(key_pool, name, lambda *a, _v=value, **k: _v)
    monkeypatch.setattr(provider_health, "record_waterfall", lambda **kwargs: None)
    monkeypatch.setattr(provider_health, "record_attempt", lambda **kwargs: None)
    monkeypatch.setattr(key_pool, "mark_cooling", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_costs, "record_usage", lambda *a, **k: None)
    monkeypatch.setattr(mb, "_collect_style_violations", lambda parsed: [])
    monkeypatch.setattr(llm_auth_mod, "_dead_providers", set())
    yield events, path, document


def _policy_cfg(**updates):
    return {**_SHIPPED_CFG, "workload_profile": "site_batch",
            "provider_order": ["oauth", "codex", "anthropic", "deepseek"],
            "emit_theses": False, "reply_cache_dir": "brief-cache", **updates}


@pytest.mark.parametrize("host_only", [False, True])
def test_profiled_brief_custom_endpoint_refuses_before_client(policy_boundary, monkeypatch, host_only):
    events, _, _ = policy_boundary
    cfg = {**_CUSTOM_ENDPOINT_CFG, "provider_order": ["anthropic"]}
    if host_only:
        monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_batch")
    else:
        cfg["workload_profile"] = "site_batch"
    text, reason = mb._call_model("system", "user", cfg)
    assert text is None and reason == "workload_policy:WORKLOAD_CUSTOM_ENDPOINT_UNSUPPORTED"
    assert not any(events[k] for k in ("secrets", "native", "custom", "calls"))


def test_profiled_brief_requires_original_explicit_provider_order(policy_boundary):
    events, _, _ = policy_boundary
    cfg = _policy_cfg(); del cfg["provider_order"]
    text, reason = mb._call_model("system", "user", cfg)
    assert text is None and reason == "workload_policy:WORKLOAD_PROVIDER_ORDER_REQUIRED"
    assert not any(events[k] for k in ("secrets", "native", "custom", "calls"))


@pytest.mark.parametrize("profile,code", [("", "WORKLOAD_PROFILE_INVALID"),
    (None, "WORKLOAD_PROFILE_INVALID"), ("unknown", "WORKLOAD_PROFILE_UNKNOWN"),
    ("lobe_maintenance", "NATIVE_AGENT_PATH_REQUIRED")])
def test_brief_policy_refusal_precedes_cache_and_provider(policy_boundary, monkeypatch, tmp_path, profile, code):
    events, _, _ = policy_boundary
    cache_reads = []
    monkeypatch.setattr(mb, "_mb_reply_cache_get", lambda *a, **k:
        cache_reads.append(True) or events["reply"])
    result = mb.synthesize({}, _policy_cfg(workload_profile=profile), root=tmp_path)
    assert result["degraded_reason"] == "workload_policy:" + code
    assert result["raw_text"] is None and result["served_by"] is None
    assert cache_reads == [] and events["calls"] == [] and events["secrets"] == []


@pytest.mark.parametrize("order", [[], ["oauth", "codex"]])
def test_brief_denied_order_does_not_reuse_cache(policy_boundary, monkeypatch, tmp_path, order):
    events, _, _ = policy_boundary
    monkeypatch.setattr(mb, "_mb_reply_cache_get", lambda *a, **k: events["reply"])
    result = mb.synthesize({}, _policy_cfg(provider_order=order), root=tmp_path)
    assert result["degraded_reason"] == "workload_policy:WORKLOAD_NO_ELIGIBLE_PROVIDER"
    assert result["raw_text"] is None and events["calls"] == []


def test_brief_real_builder_produces_safe_receipt(policy_boundary, tmp_path):
    events, _, _ = policy_boundary
    result = mb.synthesize({}, _policy_cfg(), root=tmp_path)
    assert result["summary"] == "Synthetic brief."
    assert result["degraded_reason"] is None and result["served_by"] == "anthropic"
    assert events["native"] == [] and events["custom"] == [] and len(events["calls"]) == 1
    receipt = result["workload_policy"]
    assert set(receipt) == {"schema", "policy_revision", "policy_hash", "profiles",
                           "execution_surface", "allowed_order", "denied_order"}
    assert receipt["profiles"] == ["site_batch"]
    assert receipt["allowed_order"] == ["anthropic", "deepseek"]
    assert "synthetic-test-credential" not in json.dumps(result)


def test_brief_profile_cache_is_separate_from_legacy_and_reused(policy_boundary, tmp_path):
    events, _, _ = policy_boundary
    cfg = _policy_cfg(provider_order=["anthropic"])
    legacy = {k: v for k, v in cfg.items() if k != "workload_profile"}
    mb.synthesize({}, legacy, root=tmp_path)
    events["native"].clear()
    result = mb.synthesize({}, cfg, root=tmp_path)
    assert result["served_by"] == "anthropic" and len(events["calls"]) == 2
    cached = mb.synthesize({}, cfg, root=tmp_path)
    assert cached["served_by"] == "cache" and len(events["calls"]) == 2
    assert cached["workload_policy"] == result["workload_policy"]


def test_brief_new_policy_does_not_reuse_old_reply(policy_boundary, tmp_path):
    events, path, document = policy_boundary
    cfg = _policy_cfg()
    first = mb.synthesize({}, cfg, root=tmp_path)
    document["revision"] += 1
    document["profiles"]["site_batch"]["allowed_providers"] = ["deepseek"]
    path.write_text(json.dumps(document))
    second = mb.synthesize({}, cfg, root=tmp_path)
    assert len(events["calls"]) == 2 and second["served_by"] == "deepseek"
    assert second["workload_policy"]["policy_hash"] != first["workload_policy"]["policy_hash"]


def test_brief_model_change_invalidates_profiled_cache(policy_boundary, tmp_path):
    events, _, _ = policy_boundary
    cfg = _policy_cfg(opus_model="synthetic-model-one")
    mb.synthesize({}, cfg, root=tmp_path)
    second = mb.synthesize({}, {**cfg, "opus_model": "synthetic-model-two"}, root=tmp_path)
    assert events["calls"] == ["synthetic-model-one", "synthetic-model-two"]
    assert second["model"] == "synthetic-model-two"


def test_brief_policy_change_during_call_discards_result_without_retry(policy_boundary, tmp_path):
    events, path, document = policy_boundary
    def retire():
        document["revision"] += 1
        document["profiles"]["site_batch"]["allowed_providers"] = []
        path.write_text(json.dumps(document))
    events["after_call"] = retire
    result = mb.synthesize({}, _policy_cfg(), root=tmp_path)
    assert result["raw_text"] is None and result["summary"] is None
    assert result["degraded_reason"].startswith("workload_policy:")
    assert len(events["calls"]) == 1 and not list(tmp_path.glob("brief-cache/*.txt"))


def test_profiled_brief_typeerror_does_not_replay_model_call(policy_boundary, monkeypatch, tmp_path):
    calls = []
    def broken(*args, **kwargs):
        calls.append(True)
        raise TypeError("synthetic provider error after possible effect")
    monkeypatch.setattr(mb, "_call_model", broken)
    result = mb.synthesize({}, _policy_cfg(), root=tmp_path)
    assert len(calls) == 1
    assert result["raw_text"] is None and result["degraded_reason"] == "llm_error"



def test_profiled_cache_preserves_actual_served_model(policy_boundary, tmp_path):
    events, _, _ = policy_boundary
    cfg = _policy_cfg(opus_model="synthetic-served-model")
    first = mb.synthesize({}, cfg, root=tmp_path)
    second = mb.synthesize({}, cfg, root=tmp_path)
    assert second["served_by"] == "cache" and len(events["calls"]) == 1
    assert first["model"] == second["model"] == "synthetic-served-model"
    assert second["cache_origin_provider"] == "anthropic"


def test_profiled_cache_rejects_wrong_policy_receipt(policy_boundary, tmp_path):
    events, _, _ = policy_boundary
    cfg = _policy_cfg()
    mb.synthesize({}, cfg, root=tmp_path)
    cache = next(tmp_path.glob("brief-cache/*.txt"))
    cache.write_text(json.dumps({"schema": "master_brief_cache.v1", "text": events["reply"],
        "provider": "oauth", "model": "synthetic-forbidden", "workload_policy": {}}))
    result = mb.synthesize({}, cfg, root=tmp_path)
    assert result["served_by"] == "anthropic" and len(events["calls"]) == 2
    assert result["model"] != "synthetic-forbidden"


def test_brief_rewrite_policy_change_discards_original_and_cache(policy_boundary, monkeypatch, tmp_path):
    events, path, document = policy_boundary
    calls = []
    def style(parsed):
        calls.append(True)
        return ["token: synthetic"] if len(calls) == 1 else []
    def retire_on_rewrite():
        if len(events["calls"]) == 2:
            document["revision"] += 1
            document["profiles"]["site_batch"]["allowed_providers"] = []
            path.write_text(json.dumps(document))
    monkeypatch.setattr(mb, "_collect_style_violations", style)
    events["after_call"] = retire_on_rewrite
    result = mb.synthesize({}, _policy_cfg(), root=tmp_path)
    assert len(events["calls"]) == 2
    assert result["raw_text"] is None and result["summary"] is None
    assert result["degraded_reason"].startswith("workload_policy:")
    assert not list(tmp_path.glob("brief-cache/*.txt"))



def _policy_run(monkeypatch, tmp_path, cfg):
    cfg.update(enabled=True, translate_zh=False, interval_days=7)
    monkeypatch.setattr(mb, "_cfg", lambda: cfg)
    monkeypatch.setitem(mb.LENSES, "macro", {**mb.LENSES["macro"],
        "state_fn": lambda root: {"macro": {"asof": "2026-09-15"}}})
    (tmp_path / "site").mkdir(exist_ok=True)


def test_brief_run_interval_cannot_hide_policy_change(policy_boundary, monkeypatch, tmp_path):
    events, path, document = policy_boundary
    cfg = _policy_cfg(); _policy_run(monkeypatch, tmp_path, cfg)
    first = mb.run(root=tmp_path)
    stable = mb.run(root=tmp_path)
    assert stable["generated_at"] == first["generated_at"] and len(events["calls"]) == 1
    document["revision"] += 1
    document["profiles"]["site_batch"]["allowed_providers"] = ["deepseek"]
    path.write_text(json.dumps(document))
    newer = mb.run(root=tmp_path)
    assert newer["served_by"] == "deepseek" and len(events["calls"]) == 2
    assert newer["workload_fingerprint"] != first["workload_fingerprint"]


def test_brief_run_interval_cannot_hide_model_change(policy_boundary, monkeypatch, tmp_path):
    events, _, _ = policy_boundary
    cfg = _policy_cfg(opus_model="synthetic-model-one"); _policy_run(monkeypatch, tmp_path, cfg)
    mb.run(root=tmp_path)
    cfg["opus_model"] = "synthetic-model-two"
    newer = mb.run(root=tmp_path)
    assert newer["model"] == "synthetic-model-two" and len(events["calls"]) == 2


def test_brief_run_new_denial_replaces_prior_artifact(policy_boundary, monkeypatch, tmp_path):
    events, _, _ = policy_boundary
    cfg = _policy_cfg(); _policy_run(monkeypatch, tmp_path, cfg)
    mb.run(root=tmp_path)
    cfg["provider_order"] = []
    newer = mb.run(root=tmp_path)
    published = json.loads((tmp_path / "site/master_brief.json").read_text())
    assert newer == published and len(events["calls"]) == 1
    assert published["summary"] is None and published["raw_text"] is None
    assert published["workload_refusal_code"] == "WORKLOAD_NO_ELIGIBLE_PROVIDER"


@pytest.mark.parametrize("persist", [True, False])
def test_brief_run_rechecks_policy_after_translation(policy_boundary, monkeypatch, tmp_path, persist):
    events, path, document = policy_boundary
    cfg = _policy_cfg(); _policy_run(monkeypatch, tmp_path, cfg)
    def retire(brief, cfg, lens):
        document["revision"] += 1
        document["profiles"]["site_batch"]["allowed_providers"] = []
        path.write_text(json.dumps(document))
        brief["zh"] = {"summary": "synthetic obsolete translation"}
    monkeypatch.setattr(mb, "_translate_brief", retire)
    result = mb.run(persist=persist, root=tmp_path)
    assert result["raw_text"] is None and result["summary"] is None
    assert "zh" not in result and len(events["calls"]) == 1
    assert result["workload_refusal_code"]


def _render_policy_brief(brief):
    import jinja2
    from engine import i18n
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(Path(mb.__file__).parents[1] / "templates"))
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env.get_template("aibrief.html.j2").render(
        as_of="2026-09-15", master_brief=brief,
        ctx_strip={"absent": True},
        fwd_panel={"absent": True, "events": [], "rebal_note_en": None, "rebal_note_zh": None},
        record_panel={"absent": True})


def test_brief_real_run_publishes_policy_result_to_existing_template(policy_boundary, monkeypatch, tmp_path):
    events, _, _ = policy_boundary
    cfg = _policy_cfg(); _policy_run(monkeypatch, tmp_path, cfg)
    result = mb.run(root=tmp_path)
    data = json.loads((tmp_path / "data/regime/master_brief.json").read_text())
    published = json.loads((tmp_path / "site/master_brief.json").read_text())
    assert result == data == published
    assert published["workload_policy"]["profiles"] == ["site_batch"]
    assert "Synthetic brief." in _render_policy_brief(published)
    assert events["native"] == [] and len(events["calls"]) == 1


def test_brief_policy_degraded_template_hides_internal_codes(policy_boundary, tmp_path):
    brief = mb.synthesize({}, _policy_cfg(provider_order=[]), root=tmp_path)
    html = _render_policy_brief(brief)
    assert "WORKLOAD_NO_ELIGIBLE_PROVIDER" not in html and "workload_policy:" not in html
    assert "AI provider settings need review" in html
    assert "AI 服务配置需要检查" in html



def test_brief_retired_policy_cannot_try_the_next_provider(policy_boundary):
    events, path, document = policy_boundary
    def retire():
        document["revision"] += 1
        document["profiles"]["site_batch"]["allowed_providers"] = []
        path.write_text(json.dumps(document))
    events["after_call"] = retire
    events["exception"] = RuntimeError("401 Unauthorized")
    text, reason = mb._call_model("system", "user", _policy_cfg())
    assert text is None and reason.startswith("workload_policy:")
    assert len(events["calls"]) == 1


def test_brief_sdk_typeerror_does_not_retry_or_fail_over(policy_boundary):
    events, _, _ = policy_boundary
    events["exception"] = TypeError("synthetic ambiguous SDK effect")
    text, reason = mb._call_model("system", "user", _policy_cfg())
    assert text is None and reason == "workload_policy:WORKLOAD_PROVIDER_EFFECT_UNKNOWN"
    assert len(events["calls"]) == 1


def test_shared_waterfall_propagates_policy_refusal_without_fallback(policy_boundary):
    from engine.provider_workload_policy import ProviderWorkloadPolicyError
    calls = []
    def refuse(client, model):
        calls.append(model)
        raise ProviderWorkloadPolicyError("WORKLOAD_POLICY_CHANGED")
    providers = [_fake_provider("anthropic"), _fake_provider("deepseek")]
    with pytest.raises(ProviderWorkloadPolicyError, match="WORKLOAD_POLICY_CHANGED"):
        llm_auth_mod.make_call(providers, refuse)
    assert len(calls) == 1


def test_profiled_brief_uses_strict_messages_signature(policy_boundary, monkeypatch):
    """The real SDK rejects seed before a request; a **kwargs fake hid that."""
    events, _, _ = policy_boundary

    def create(self, *, model, max_tokens, system, messages):
        events["calls"].append(model)
        return types.SimpleNamespace(
            stop_reason=None, usage=None,
            content=[types.SimpleNamespace(type="text", text=events["reply"])],
        )

    monkeypatch.setattr(sys.modules["anthropic"].Anthropic, "create", create)
    served = {}
    text, reason = mb._call_model("system", "user", _policy_cfg(), served=served)
    assert text == events["reply"] and reason is None
    assert len(events["calls"]) == 1
    assert served["provider"] == "anthropic"


def test_client_tuning_uses_the_installed_sdk_timeout_type(monkeypatch):
    """SDK 1.x uses httpx2; a separately installed httpx type is incompatible."""
    import sys
    import types
    from engine.llm_auth import _client_tuning_kwargs

    class SdkTimeout:
        def __init__(self, value, *, connect):
            self.read = value
            self.connect = connect

    sdk = types.ModuleType("anthropic")
    sdk.Timeout = SdkTimeout
    monkeypatch.setitem(sys.modules, "anthropic", sdk)
    result = _client_tuning_kwargs({"client_timeout_s": 45})
    assert isinstance(result["timeout"], SdkTimeout)
    assert result["timeout"].read == 45.0
    assert result["timeout"].connect == 5.0
    assert "max_retries" not in result
