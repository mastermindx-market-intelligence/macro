"""Unit tests for lib/fabric_client.py — the Capacity Fabric adapter.

No network. The Anthropic SDK is replaced at the adapter's own `_make_client`
seam, so these tests assert the REQUEST SHAPE the router receives (lane/model,
attribution, betas, max_tokens) and the one-call discipline, not SDK behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import fabric_client as fc  # noqa: E402


# --------------------------------------------------------------------------- #
# fakes
# --------------------------------------------------------------------------- #
class _Block:
    def __init__(self, text, type="text"):
        self.text = text
        self.type = type


class _Usage:
    def __init__(self):
        self.input_tokens = 11
        self.output_tokens = 22

    def model_dump(self):
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens}


class _Response:
    def __init__(self, headers):
        self.headers = headers


class _Message:
    def __init__(self, text="hello", model="deepseek-v4.1-flash", headers=None):
        self.content = [_Block(text)]
        self.model = model
        self.usage = _Usage()
        self._response = _Response(headers or {})


class _FakeMessages:
    def __init__(self, recorder, message=None, error=None, events=None):
        self._recorder = recorder
        self._message = message
        self._error = error
        self._events = events or []

    def create(self, **kwargs):
        self._recorder.append(kwargs)
        if self._error is not None:
            raise self._error
        if kwargs.get("stream"):
            return _FakeStream(self._events)
        return self._message


class _FakeStream:
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        return iter(self._events)

    def __exit__(self, *exc):
        return False


class _FakeSDK:
    def __init__(self, **kw):
        self.init_kwargs = kw
        self.messages = _FakeMessages(
            kw["_recorder"], message=kw.get("_message"),
            error=kw.get("_error"), events=kw.get("_events"))


class _Recorder(list):
    """List of create() kwargs that also carries the fake's response state."""

    state: dict


@pytest.fixture
def recorder(monkeypatch):
    """Install a fake SDK seam and return the list of create() kwargs."""
    calls = _Recorder()
    state: dict = {}

    def fake_make_client(base_url, timeout):
        state["base_url"] = base_url
        state["timeout"] = timeout
        return _FakeSDK(
            _recorder=calls, _message=state.get("message"),
            _error=state.get("error"), _events=state.get("events"),
            api_key="tok")

    monkeypatch.setattr(fc, "_make_client", fake_make_client)
    monkeypatch.setenv(fc.TOKEN_ENV, "test-token")
    calls.state = state
    return calls


# --------------------------------------------------------------------------- #
# is_configured
# --------------------------------------------------------------------------- #
def test_is_configured_reads_token_env(monkeypatch):
    monkeypatch.delenv(fc.TOKEN_ENV, raising=False)
    assert fc.is_configured() is False
    monkeypatch.setenv(fc.TOKEN_ENV, "   ")
    assert fc.is_configured() is False
    monkeypatch.setenv(fc.TOKEN_ENV, "abc")
    assert fc.is_configured() is True


# --------------------------------------------------------------------------- #
# resolve_model: precedence + failures
# --------------------------------------------------------------------------- #
def test_resolve_model_default_lane_is_fast():
    assert fc.resolve_model() == "fabric/fast"


def test_resolve_model_lane_map():
    assert fc.resolve_model(lane="fast") == "fabric/fast"
    assert fc.resolve_model(lane="balanced") == "fabric/balanced"
    assert fc.resolve_model(lane="frontier") == "fabric/frontier"
    assert fc.resolve_model(lane="kimi") == "fabric/kimi-preferred"
    assert fc.resolve_model(lane="auto") == "auto"
    # full lane id passes through
    assert fc.resolve_model(lane="fabric/kimi-preferred") == "fabric/kimi-preferred"


def test_resolve_model_provider_and_difficulty_maps():
    assert fc.resolve_model(provider="deepseek") == "deepseek-v4.1-flash"
    assert fc.resolve_model(provider="glm") == "glm-5.3"
    assert fc.resolve_model(provider="kimi") == "kimi-k3.1-pro"
    assert fc.resolve_model(provider="qwen") == "qwen3.8-max"
    assert fc.resolve_model(provider="claude") == "claude-opus-5-5"
    assert fc.resolve_model(provider="gpt") == "gpt-6.1-sol"
    assert fc.resolve_model(difficulty="flash") == "fabric/fast"
    assert fc.resolve_model(difficulty="medium") == "fabric/balanced"
    assert fc.resolve_model(difficulty="hard") == "fabric/frontier"


def test_resolve_model_precedence_model_provider_difficulty_lane():
    everything = dict(model="glm-5.3", provider="deepseek",
                      difficulty="frontier", lane="fast")
    assert fc.resolve_model(**everything) == "glm-5.3"
    assert fc.resolve_model(**{k: v for k, v in everything.items()
                              if k != "model"}) == "deepseek-v4.1-flash"
    assert fc.resolve_model(provider=None, difficulty="frontier",
                            lane="fast") == "fabric/frontier"


def test_resolve_model_unknown_values_raise():
    with pytest.raises(ValueError):
        fc.resolve_model(provider="mistral")
    with pytest.raises(ValueError):
        fc.resolve_model(difficulty="impossible")
    with pytest.raises(ValueError):
        fc.resolve_model(lane="turbo")


# --------------------------------------------------------------------------- #
# request shape
# --------------------------------------------------------------------------- #
def test_complete_sends_lane_and_required_max_tokens(recorder):
    recorder.state["message"] = _Message("brief text")
    comp = fc.complete([{"role": "user", "content": "hi"}], lane="fast")
    kw = recorder[0]
    assert kw["model"] == "fabric/fast"
    assert kw["max_tokens"] == 2048            # required for router admission
    assert kw["messages"] == [{"role": "user", "content": "hi"}]
    assert comp.text == "brief text"


def test_complete_requires_max_tokens_argument_forwarded(recorder):
    recorder.state["message"] = _Message()
    fc.complete([{"role": "user", "content": "x"}], max_tokens=777)
    assert recorder[0]["max_tokens"] == 777


def test_complete_sends_attribution_headers_and_body(recorder):
    recorder.state["message"] = _Message()
    fc.complete(
        [{"role": "user", "content": "x"}],
        client="T3", session_id="s-1", agent_id="a-1",
        parent_agent_id="p-1", project_id="macro-dashboard")
    kw = recorder[0]
    headers = kw["extra_headers"]
    assert headers["x-fabric-client"] == "T3"
    assert headers["x-fabric-session-id"] == "s-1"
    assert headers["x-fabric-agent-id"] == "a-1"
    assert headers["x-fabric-parent-agent-id"] == "p-1"
    assert headers["x-fabric-project-id"] == "macro-dashboard"
    fabric = kw["extra_body"]["metadata"]["fabric"]
    assert fabric == {"client": "T3", "session_id": "s-1", "agent_id": "a-1",
                      "parent_agent_id": "p-1", "project_id": "macro-dashboard"}


def test_complete_rejects_unknown_client(recorder):
    with pytest.raises(ValueError):
        fc.complete([{"role": "user", "content": "x"}], client="MyScript")
    assert recorder == []                      # rejected before any request


def test_betas_go_in_top_level_body_key_not_a_header(recorder):
    recorder.state["message"] = _Message()
    fc.complete([{"role": "user", "content": "x"}], betas=["interleaved-thinking"])
    kw = recorder[0]
    assert kw["extra_body"]["betas"] == ["interleaved-thinking"]
    assert "anthropic-beta" not in kw["extra_headers"]


def test_task_complexity_only_for_auto_model(recorder):
    recorder.state["message"] = _Message()
    fc.complete([{"role": "user", "content": "x"}], lane="fast",
                task_complexity="hard")
    assert "task_complexity" not in recorder[0]["extra_body"]["metadata"]
    fc.complete([{"role": "user", "content": "x"}], model="auto",
                task_complexity="hard")
    assert recorder[1]["extra_body"]["metadata"]["task_complexity"] == "hard"


def test_base_url_defaults_and_override(recorder):
    recorder.state["message"] = _Message()
    fc.complete([{"role": "user", "content": "x"}])
    assert recorder.state["base_url"] == fc.DEFAULT_BASE_URL == "http://127.0.0.1:8313"
    fc.complete([{"role": "user", "content": "x"}], base_url="http://10.0.0.5:8313")
    assert recorder.state["base_url"] == "http://10.0.0.5:8313"


def test_complete_reads_route_headers_best_effort(recorder):
    recorder.state["message"] = _Message(
        "ok", model="glm-5.3",
        headers={"x-fabric-route-id": "r-42", "x-fabric-provider": "glm"})
    comp = fc.complete([{"role": "user", "content": "x"}])
    assert comp.model_served == "glm-5.3"
    assert comp.route_id == "r-42"
    assert comp.provider == "glm"
    assert comp.usage["output_tokens"] == 22
    assert comp.raw is not None


def test_complete_without_route_headers_returns_none_not_error(recorder):
    recorder.state["message"] = _Message("ok")
    comp = fc.complete([{"role": "user", "content": "x"}])
    assert comp.route_id is None and comp.provider is None


# --------------------------------------------------------------------------- #
# the one-call discipline: the adapter NEVER retries or fails over
# --------------------------------------------------------------------------- #
def test_sdk_error_propagates_and_is_called_exactly_once(recorder):
    recorder.state["error"] = RuntimeError("router exhausted its ladder")
    with pytest.raises(RuntimeError, match="router exhausted"):
        fc.complete([{"role": "user", "content": "x"}])
    assert len(recorder) == 1                  # no retry, no second provider


def test_missing_token_raises_without_a_request(monkeypatch):
    # Deliberately does NOT use the fake seam: the token check lives in the real
    # _make_client, so nothing must be constructed (and no request made) without it.
    monkeypatch.delenv(fc.TOKEN_ENV, raising=False)
    with pytest.raises(RuntimeError, match=fc.TOKEN_ENV):
        fc.complete([{"role": "user", "content": "x"}])


# --------------------------------------------------------------------------- #
# streaming
# --------------------------------------------------------------------------- #
class _Delta:
    def __init__(self, text):
        self.type = "content_block_delta"
        self.delta = type("D", (), {"text": text})()


class _Other:
    type = "message_start"
    delta = None


def test_stream_yields_text_deltas_only(recorder):
    recorder.state["events"] = [_Other(), _Delta("Hel"), _Delta("lo"), _Other()]
    out = list(fc.stream([{"role": "user", "content": "x"}], lane="fast"))
    assert out == ["Hel", "lo"]
    assert recorder[0]["stream"] is True
    assert recorder[0]["model"] == "fabric/fast"


def test_stream_error_is_not_retried(recorder):
    recorder.state["error"] = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        list(fc.stream([{"role": "user", "content": "x"}]))
    assert len(recorder) == 1
