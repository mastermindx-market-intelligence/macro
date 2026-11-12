"""The metabolism loop routes through the Capacity Fabric when configured.

Chairman order 2026-11-12: all estate AI routing moves to the Capacity Fabric
``unified_router``. The metabolism loop's legacy waterfall is dead (its OAuth key
pool has been auth_failed / rate_limited since 2026-11-06), so every metabolism
LLM call site gains an env-gated fabric branch:

  * configured (``FABRIC_ROUTER_TOKEN`` present) and ``MACRO_METABOLISM_FABRIC``
    != "0"  -> ONE ``fabric_client.complete`` call, no local retry;
  * not configured, kill-switch set, or an unreachable router
    (``FabricUnavailable``) -> the EXACT legacy ladder, byte-for-byte unchanged;
  * ``AUTONOMY_PAUSED`` still wins over everything: the stage no-ops before any
    fabric call is considered.

All stub-based: no network, no API keys, no sparse-omitted directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.metabolism import (  # noqa: E402
    adjudicate, agenda, attention, audit, fabric_lane, propose, standout_auditor,
)
from lib import fabric_client as fc  # noqa: E402

_AUDIT_REPLY = (
    '{"verdict": "approve", "confidence": 0.9, "findings": [], "rationale": "ok"}'
)
_JUDGMENTS_REPLY = '[{"proposal_id": "p1", "approve": true, "rationale": "fine"}]'


class _Raw:
    """Minimal stand-in for the SDK Message object the adapter wraps."""

    def __init__(self, stop_reason: str = "end_turn"):
        self.stop_reason = stop_reason


def _completion(text: str = "router reply", model: str = "deepseek-v4.1-flash") -> fc.Completion:
    return fc.Completion(
        text=text,
        model_served=model,
        route_id="route-1",
        provider="deepseek",
        usage={
            "input_tokens": 11,
            "output_tokens": 7,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 2,
        },
        raw=_Raw(),
    )


class _Recorder:
    """List-like record of router calls plus the reply the stub should return."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.state = {"reply": _AUDIT_REPLY}

    def __len__(self) -> int:
        return len(self.calls)

    def __getitem__(self, index):
        return self.calls[index]

    def __iter__(self):
        return iter(self.calls)

    def __eq__(self, other):
        return self.calls == other

    def __bool__(self) -> bool:
        return bool(self.calls)


@pytest.fixture
def fabric_calls(monkeypatch):
    """Router configured; record every complete() call; reply is caller-chosen."""
    rec = _Recorder()

    def fake_complete(messages, **kwargs):
        rec.calls.append({"messages": messages, **kwargs})
        return _completion(rec.state["reply"])

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_METABOLISM_FABRIC", raising=False)
    return rec


@pytest.fixture
def fabric_off(monkeypatch):
    """Router NOT configured: complete() must never be reached."""
    calls: list[dict] = []

    def fake_complete(messages, **kwargs):  # pragma: no cover - asserted unused
        calls.append(kwargs)
        return _completion()

    monkeypatch.setattr(fc, "is_configured", lambda: False)
    monkeypatch.setattr(fc, "complete", fake_complete)
    monkeypatch.delenv("MACRO_METABOLISM_FABRIC", raising=False)
    return calls


@pytest.fixture
def fabric_unavailable(monkeypatch):
    """Router configured but unreachable: the legacy ladder must run instead."""
    def boom(messages, **kwargs):
        raise fc.FabricUnavailable("router is not listening")

    monkeypatch.setattr(fc, "is_configured", lambda: True)
    monkeypatch.setattr(fc, "complete", boom)
    monkeypatch.delenv("MACRO_METABOLISM_FABRIC", raising=False)


@pytest.fixture
def legacy_ladder(monkeypatch):
    """Stub engine.llm_auth so the legacy path is observable without network."""
    import engine.llm_auth as llm_auth

    seen: list[str] = []

    def fake_build_providers(cfg, **kwargs):
        seen.append("build_providers")
        return [{"name": "stub", "client": None, "model": "stub-model"}]

    def fake_make_call(providers, call_fn, *, context="", attempts=None):
        seen.append(context)
        return "legacy reply", None, "oauth"

    monkeypatch.setattr(llm_auth, "build_providers", fake_build_providers)
    monkeypatch.setattr(llm_auth, "make_call", fake_make_call)
    return seen


# ── the shared lane helper ────────────────────────────────────────────────────

class TestFabricLaneGate:
    def test_off_without_token(self, monkeypatch):
        monkeypatch.delenv("FABRIC_ROUTER_TOKEN", raising=False)
        monkeypatch.delenv("MACRO_METABOLISM_FABRIC", raising=False)
        assert fabric_lane.enabled("propose") is False

    def test_on_with_token(self, monkeypatch):
        monkeypatch.setenv("FABRIC_ROUTER_TOKEN", "token")
        monkeypatch.delenv("MACRO_METABOLISM_FABRIC", raising=False)
        assert fabric_lane.enabled("propose") is True

    def test_kill_switch_beats_token(self, monkeypatch):
        monkeypatch.setenv("FABRIC_ROUTER_TOKEN", "token")
        monkeypatch.setenv("MACRO_METABOLISM_FABRIC", "0")
        assert fabric_lane.enabled("propose") is False

    def test_unknown_stage_stays_legacy(self, monkeypatch):
        monkeypatch.setenv("FABRIC_ROUTER_TOKEN", "token")
        monkeypatch.delenv("MACRO_METABOLISM_FABRIC", raising=False)
        assert fabric_lane.enabled("no-such-stage") is False

    def test_session_id_carries_stage_and_suffix(self):
        assert fabric_lane.session_id("audit") == "macro-metab-audit"
        assert fabric_lane.session_id("agenda", "cyc-1") == "macro-metab-agenda-cyc-1"


class TestAttribution:
    def test_project_session_and_client(self, fabric_calls):
        fabric_calls.state["reply"] = "hello"
        fabric_lane.call(stage="audit", system="s", user="u", max_tokens=123)
        assert len(fabric_calls) == 1
        kw = fabric_calls[0]
        assert kw["project_id"] == "macro-dashboard"
        assert kw["session_id"] == "macro-metab-audit"
        assert kw["max_tokens"] == 123
        assert kw["system"] == "s"
        # default client is a member of the router's closed CLIENTS set
        assert kw.get("client", fc.DEFAULT_CLIENT) in fc.CLIENTS

    def test_fail_closed_gates_take_balanced_lane(self, fabric_calls):
        fabric_calls.state["reply"] = "hello"
        fabric_lane.call(stage="audit", system="s", user="u")
        fabric_lane.call(stage="adjudicate", system="s", user="u")
        fabric_lane.call(stage="propose", system="s", user="u")
        assert [c["lane"] for c in fabric_calls] == ["balanced", "balanced", "fast"]

    def test_usage_maps_onto_ai_costs_row(self, fabric_calls):
        fabric_calls.state["reply"] = "hello"
        usage: list[dict] = []
        fabric_lane.call(stage="propose", system="s", user="u", usage_out=usage)
        assert usage == [{
            "input_tokens": 11,
            "output_tokens": 7,
            "cache_read_tokens": 3,
            "cache_creation_tokens": 2,
            "model": "deepseek-v4.1-flash",
        }]


class TestNoRetry:
    def test_router_error_degrades_with_single_request(self, monkeypatch):
        calls: list[int] = []

        def boom(messages, **kwargs):
            calls.append(1)
            raise RuntimeError("502 from router")

        monkeypatch.setattr(fc, "is_configured", lambda: True)
        monkeypatch.setattr(fc, "complete", boom)
        text, reason, provider = fabric_lane.call(stage="propose", system="s", user="u")
        assert text is None
        assert reason and reason.startswith("llm_error")
        assert provider == "fabric"
        assert len(calls) == 1, "the router owns fallback: one logical call = one request"

    def test_unavailable_is_re_raised_for_the_legacy_ladder(self, fabric_unavailable):
        with pytest.raises(fc.FabricUnavailable):
            fabric_lane.call(stage="propose", system="s", user="u")

    def test_empty_reply_is_a_degraded_reason(self, fabric_calls):
        fabric_calls.state["reply"] = ""
        text, reason, provider = fabric_lane.call(stage="propose", system="s", user="u")
        assert text is None and reason == "empty_reply" and provider == "fabric"


# ── per-site cutover ─────────────────────────────────────────────────────────

class TestAttention:
    def test_routes_through_router(self, fabric_calls):
        fabric_calls.state["reply"] = "{}"
        text, reason, provider = attention._call_llm([], "sys", "usr")
        assert (text, reason, provider) == ("{}", None, "fabric")
        assert len(fabric_calls) == 1
        assert fabric_calls[0]["session_id"] == "macro-metab-attention"

    def test_unconfigured_keeps_legacy(self, fabric_off, legacy_ladder):
        text, _reason, provider = attention._call_llm([{"x": 1}], "sys", "usr")
        assert text == "legacy reply" and provider == "oauth"
        assert fabric_off == []

    def test_unreachable_router_keeps_legacy(self, fabric_unavailable, legacy_ladder):
        text, _reason, provider = attention._call_llm([{"x": 1}], "sys", "usr")
        assert text == "legacy reply" and provider == "oauth"

    def test_structural_only_heal_never_spends(self, fabric_calls, tmp_path):
        attention.build_attention(
            cycle_id="c1", root=tmp_path, providers=None, allow_fabric=False)
        assert fabric_calls == []

    def test_agenda_stage_allows_fabric_without_providers(self, fabric_calls, tmp_path):
        # an empty provider list must not be read as "no LLM wanted"
        assert attention.build_attention(
            cycle_id="c1", root=tmp_path, providers=None).get("cycle_id") == "c1"


class TestAgenda:
    def test_routes_through_router(self, fabric_calls):
        fabric_calls.state["reply"] = '{"items": []}'
        text, reason, provider = agenda._call_llm([], "sys", "usr", cycle_id="cyc-9")
        assert (text, reason, provider) == ('{"items": []}', None, "fabric")
        assert fabric_calls[0]["session_id"] == "macro-metab-agenda-cyc-9"

    def test_no_llm_mode_stays_token_free(self, fabric_calls, tmp_path):
        agenda.build_agenda(
            cycle_id="cyc-1", root=tmp_path, providers=[], allow_fabric=False)
        assert fabric_calls == []


class TestPropose:
    def test_routes_through_router_without_retry_ladder(self, fabric_calls, monkeypatch, tmp_path):
        monkeypatch.setattr(propose, "_build_system_prompt", lambda lobe, root: "SYS {max_n}")
        monkeypatch.setattr(propose, "_build_user_prompt", lambda ctx, n: "USER")
        fabric_calls.state["reply"] = '[{"title": "x"}]'
        text, provider, reason, usage = propose._invoke_llm({}, 3, root=tmp_path)
        assert text == '[{"title": "x"}]'
        assert provider == "fabric" and reason is None
        assert usage["model"] == "deepseek-v4.1-flash"
        assert len(fabric_calls) == 1, "PR-R8 retry ladder must be bypassed on the fabric path"

    def test_unreachable_router_keeps_legacy(self, fabric_unavailable, legacy_ladder, monkeypatch, tmp_path):
        monkeypatch.setattr(propose, "_build_system_prompt", lambda lobe, root: "SYS {max_n}")
        monkeypatch.setattr(propose, "_build_user_prompt", lambda ctx, n: "USER")
        text, provider, _reason, _usage = propose._invoke_llm({}, 3, root=tmp_path)
        assert text == "legacy reply" and provider == "oauth"


class TestAdjudicate:
    def test_routes_through_router(self, fabric_calls, monkeypatch):
        monkeypatch.setattr(adjudicate, "_build_role_user", lambda role, docket, law: "USER")
        fabric_calls.state["reply"] = _JUDGMENTS_REPLY
        parsed, reason, usage = adjudicate._invoke_role_llm("adv", {}, {})
        assert parsed and "p1" in parsed
        assert reason is None and usage["output_tokens"] == 7
        assert len(fabric_calls) == 1

    def test_unparseable_reply_stays_fail_closed(self, fabric_calls, monkeypatch):
        monkeypatch.setattr(adjudicate, "_build_role_user", lambda role, docket, law: "USER")
        fabric_calls.state["reply"] = "I cannot help with that."
        parsed, reason, _usage = adjudicate._invoke_role_llm("adv", {}, {})
        assert parsed is None, "a bad reply must never become an approval"
        assert reason == "empty_or_unparseable_reply"


class TestAudit:
    def test_routes_through_router(self, fabric_calls, monkeypatch):
        monkeypatch.setattr(audit, "_build_user_prompt",
                            lambda p, d, i: "diff")
        verdict, confidence, findings, rationale, err = audit._call_llm_auditor(
            {"proposal_id": "p1"}, "diff text", [])
        assert (verdict, err) == ("approve", None)
        assert confidence == pytest.approx(0.9) and findings == []
        assert len(fabric_calls) == 1

    def test_unparseable_reply_fails_closed(self, fabric_calls, monkeypatch):
        monkeypatch.setattr(audit, "_build_user_prompt", lambda p, d, i: "diff")
        fabric_calls.state["reply"] = "no json here"
        verdict, _c, _f, _r, err = audit._call_llm_auditor({"proposal_id": "p1"}, "d", [])
        assert verdict is None and err, "a bad audit reply must block the merge"

    def test_unreachable_router_keeps_legacy(self, fabric_unavailable, legacy_ladder, monkeypatch):
        monkeypatch.setattr(audit, "_build_user_prompt", lambda p, d, i: "diff")
        # the stubbed legacy ladder returns a non-JSON reply -> fail closed, no raise
        verdict, _c, _f, _r, err = audit._call_llm_auditor({"proposal_id": "p1"}, "d", [])
        assert verdict is None and err == "llm_error"


class TestStandoutAuditor:
    def test_cohort_audit_routes_through_router(self, fabric_calls):
        fabric_calls.state["reply"] = '{"picks": []}'
        text, provider = standout_auditor._invoke_auditor_llm({}, "us", "cyc-1")
        assert text == '{"picks": []}' and provider == "fabric"
        assert fabric_calls[0]["session_id"] == "macro-metab-standout"

    def test_autopsy_routes_through_router(self, fabric_calls, tmp_path):
        fabric_calls.state["reply"] = "[]"
        picks = [{"ticker": "AAA", "as_of": "2026-11-01"}]
        out = standout_auditor._invoke_autopsy_llm("us", picks, "cyc-1", None, tmp_path)
        assert out == []
        assert len(fabric_calls) == 1
        assert fabric_calls[0]["session_id"] == "macro-metab-autopsy"


class TestDreamResummary:
    def test_routes_through_router(self, fabric_calls, tmp_path):
        from scripts import metabolism_dream

        fabric_calls.state["reply"] = "a short summary"
        assert metabolism_dream._request_llm_summary("old lessons", tmp_path) == "a short summary"

    def test_unreachable_router_keeps_legacy(self, fabric_unavailable, legacy_ladder, tmp_path):
        from scripts import metabolism_dream

        # the stubbed make_call returns "legacy reply"; the fabric branch must not swallow it
        assert metabolism_dream._request_llm_summary("old lessons", tmp_path) == "legacy reply"


class TestPausePrecedence:
    def test_paused_stage_no_ops_before_any_fabric_call(self, fabric_calls, monkeypatch, tmp_path):
        from scripts import metabolism_dream

        monkeypatch.delenv("AUTONOMY_PAUSED", raising=False)  # unset == paused
        assert metabolism_dream.main(["--root", str(tmp_path), "--dry-run"]) == 0
        assert fabric_calls == [], "the kill switch must win over the fabric lane"
