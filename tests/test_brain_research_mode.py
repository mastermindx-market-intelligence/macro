"""B-F11-6 / MO-PAID-031 — grounded research mode.

RED-first suite. Uses the gateway's existing LLM test doubles
(_MockClient / _MockResponse / _MockBlock), the same idiom as
tests/test_brain_gateway.py. No network, no data/, no site/ from the
checkout — fixtures write their own briefing under tmp.

Coverage:
  1. A question outside coverage returns the exact null form (EN+ZH)
     plus the plain list of what was checked.
  2. Every research answer carries the ceiling sentence (verbatim EN + ZH).
  3. Every research answer carries a 'What this read used' list of plain
     names + asof dates (never file paths).
  4. JWT-absent prints the unsigned-in null (EN+ZH).
  5. Forbidden-output filter: judgement scores, falsifier/refuted/证伪,
     allowlist tool names, imperative buy/sell/size/target.
  6. An answer that cites no used artifact is replaced by the null form.
  7. BRAIN_INTERNALS_ALLOWLIST / internals tool set identity and length
     are unchanged (no widening, mirroring, cache, or second list).
  8. Widget copy in templates/mm_brain.js.
  9. User-plane reads never send the service-role key.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine.neuralweb import brain_gateway as gw  # noqa: E402


# Frozen allowlist identity — if research mode widens or duplicates the
# internals set, this suite fails closed.
_FROZEN_INTERNALS = frozenset({"context_search", "context_open"})
_FROZEN_TOOLS_LEN = 63

CEILING_EN = (
    "This is a reading of what we already published. It is not a signal, "
    "not a rating, and not advice — nothing here changes any board, rank, or alert."
)
CEILING_ZH = (
    "这是对我们已经发布内容的解读。这不是信号、不是评级、也不是建议——"
    "这里的任何内容都不会改变任何看板、排名或提醒。"
)
NULL_EN = "We don't publish anything that answers this yet."
NULL_ZH = "我们目前还没有发布能回答这个问题的内容。"
JWT_ABSENT_EN = "Your own theses and notes weren't included — you're not signed in here."
JWT_ABSENT_ZH = "您自己的论点和笔记没有纳入本次阅读——您尚未在此登录。"
WITHHELD_EN = "Part of this answer was withheld because it read like a signal."
WITHHELD_ZH = "本次回答有一部分被隐去，因为它读起来像信号。"
USED_EN = "What this read used"
USED_ZH = "本次阅读用到的内容"

TOGGLE_EN = "Research mode — answers only from what we publish"
TOGGLE_ZH = "研究模式——只根据我们已发布的内容作答。"


@pytest.fixture(autouse=True)
def _ai_costs_ledger_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lib.ai_costs._write_ledger_path",
        lambda root=None: tmp_path / "ai_costs" / "usage.jsonl",
    )


def _make_research_root(tmp_path: pathlib.Path, *, with_briefing: bool = True) -> pathlib.Path:
    """Minimal repo root with a published briefing the research corpus can read."""
    root = tmp_path / "repo"
    intel = root / "site" / "intelligence"
    intel.mkdir(parents=True, exist_ok=True)
    if with_briefing:
        (intel / "briefing.json").write_text(
            json.dumps({
                "asof": "2026-09-12",
                "generated_at": "2026-09-12T20:00:00Z",
                "coverage": "full",
                "correction_state": "none",
                "null_disclosure": "",
                "summary": "US session mixed. Breadth was thin.",
            }),
            encoding="utf-8",
        )
    live = root / "site" / "live"
    live.mkdir(parents=True, exist_ok=True)
    (live / "quotes.json").write_text(
        json.dumps({"asof": "2026-09-12T20:00:00Z"}),
        encoding="utf-8",
    )
    nw = root / "data" / "neuralweb"
    nw.mkdir(parents=True, exist_ok=True)
    (nw / "world_state.json").write_text(json.dumps({"regime": "Q1"}), encoding="utf-8")
    return root


def _research_chat(tmp_path, reply_text: str, message: str = "What is the capital of France?",
                   user_jwt: str = "", *, with_briefing: bool = True):
    """Drive gw.chat(mode='research') with the gateway's loop replaced by a double."""
    root = _make_research_root(tmp_path, with_briefing=with_briefing)

    def _mock_loop(*args, **kwargs):
        return reply_text, [], [], [], {}, [], []

    with patch.object(gw, "_brain_quota_dir", return_value=tmp_path):
        with patch.object(gw, "_build_lane_providers",
                          return_value=[{"client": MagicMock(), "model": "claude-opus-4-8"}]):
            with patch.object(gw, "_resolve_tier",
                              return_value={"tier": "pro", "status": "active",
                                            "current_period_end": None}):
                with patch.object(gw, "_ensure_thread", return_value=None):
                    with patch.object(gw, "_run_brain_loop", side_effect=_mock_loop):
                        with patch("lib.ai_costs.record_usage", return_value=True):
                            return gw.chat(
                                message, "user_research",
                                mode="research",
                                root=root,
                                user_jwt=user_jwt,
                            )


# ---------------------------------------------------------------------------
# 1. Corpus restriction → exact null form
# ---------------------------------------------------------------------------

def test_outside_coverage_returns_exact_null_form(tmp_path):
    """A fixture question the published corpora do not cover → exact null form."""
    result = _research_chat(
        tmp_path,
        "France won the 1998 World Cup. Paris is lovely in June.",
        message="Who won the 1998 World Cup?",
        with_briefing=False,
    )
    reply = result["reply"]
    assert reply.startswith(NULL_EN), reply
    assert NULL_ZH in reply
    assert USED_EN in reply
    assert USED_ZH in reply
    # Never a file path in the used-list.
    assert "site/" not in reply
    assert "engine/" not in reply
    assert ".json" not in reply
    assert "falsifier" not in reply.lower()
    assert "证伪" not in reply


def test_uncited_answer_replaced_by_null_form(tmp_path):
    """Deterministic post-check: an answer that cites no used artifact is the null form."""
    result = _research_chat(
        tmp_path,
        "Generally speaking, equities rally when the Fed cuts.",
        message="What happens when the Fed cuts?",
    )
    reply = result["reply"]
    assert NULL_EN in reply
    assert NULL_ZH in reply
    # The model's general-knowledge sentence must not survive.
    assert "Generally speaking" not in reply


# ---------------------------------------------------------------------------
# 2. Ceiling sentence
# ---------------------------------------------------------------------------

def test_ceiling_sentence_present_on_grounded_answer(tmp_path):
    result = _research_chat(
        tmp_path,
        "The daily briefing says the US session was mixed and breadth was thin.",
        message="How did the US session look?",
    )
    reply = result["reply"]
    assert CEILING_EN in reply
    assert CEILING_ZH in reply


def test_ceiling_sentence_present_on_null_form(tmp_path):
    result = _research_chat(
        tmp_path,
        "I do not know.",
        message="Who won the 1998 World Cup?",
        with_briefing=False,
    )
    reply = result["reply"]
    assert CEILING_EN in reply
    assert CEILING_ZH in reply


# ---------------------------------------------------------------------------
# 3. Used-artifacts list
# ---------------------------------------------------------------------------

def test_used_artifacts_list_present_with_plain_names(tmp_path):
    result = _research_chat(
        tmp_path,
        "The daily briefing says the US session was mixed and breadth was thin.",
        message="How did the US session look?",
    )
    reply = result["reply"]
    assert USED_EN in reply
    assert USED_ZH in reply
    assert "Daily briefing" in reply
    assert "2026-09-12" in reply
    assert "site/intelligence/briefing.json" not in reply
    assert "/var/lib/macro-live" not in reply


# ---------------------------------------------------------------------------
# 4. JWT-absent null
# ---------------------------------------------------------------------------

def test_jwt_absent_prints_unsigned_in_null(tmp_path):
    result = _research_chat(
        tmp_path,
        "The daily briefing says the US session was mixed and breadth was thin.",
        message="How did the US session look?",
        user_jwt="",
    )
    reply = result["reply"]
    assert JWT_ABSENT_EN in reply
    assert JWT_ABSENT_ZH in reply


def test_jwt_present_does_not_print_unsigned_in_null(tmp_path):
    """A signed-in caller does not get the unsigned-in sentence.

    The user-plane GET is mocked so we never hit the network; an empty row
    set is still a signed-in read, not an unsigned-in one.
    """
    with patch.object(gw, "_user_plane_get", return_value=[]):
        result = _research_chat(
            tmp_path,
            "The daily briefing says the US session was mixed and breadth was thin.",
            message="How did the US session look?",
            user_jwt="header.payload.sig",
        )
    reply = result["reply"]
    assert JWT_ABSENT_EN not in reply
    assert JWT_ABSENT_ZH not in reply


# ---------------------------------------------------------------------------
# 5. Forbidden-output filter
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,should_drop",
    [
        ("I have 80% confidence this setup works.", True),
        ("Conviction is high on this name.", True),
        ("Score this a 0.9 on the desk's scale.", True),
        ("Five-star setup from here.", True),
        ("The falsifier has fired.", True),
        ("This claim is refuted.", True),
        ("该条件已经证伪。", True),
        ("Call context_search on the repo.", True),
        ("You should buy NVDA immediately.", True),
        ("Sell the position and size it down.", True),
        ("Set a target of 240 on the name.", True),
        ("The daily briefing says the US session was mixed.", False),
    ],
)
def test_forbidden_output_filter_cases(raw, should_drop):
    kept, withheld = gw._research_forbidden_filter(raw)
    if should_drop:
        assert withheld is True
        assert raw.strip() not in kept or kept.strip() == ""
        assert WITHHELD_EN in kept or withheld
    else:
        assert withheld is False
        assert "daily briefing" in kept.lower()


def test_forbidden_filter_appends_disclosure_via_chat(tmp_path):
    result = _research_chat(
        tmp_path,
        "The daily briefing says the US session was mixed. You should buy NVDA immediately.",
        message="How did the US session look?",
    )
    reply = result["reply"]
    assert "buy NVDA" not in reply.lower()
    assert WITHHELD_EN in reply
    assert WITHHELD_ZH in reply
    assert "The daily briefing says the US session was mixed." in reply
    assert CEILING_EN in reply


def test_forbidden_filter_does_not_emit_falsifier_words(tmp_path):
    result = _research_chat(
        tmp_path,
        "The daily briefing says the US session was mixed. The falsifier fired and the claim is refuted.",
        message="How did the US session look?",
    )
    reply = result["reply"]
    assert "falsifier" not in reply.lower()
    assert "refuted" not in reply.lower()
    assert "证伪" not in reply
    assert WITHHELD_EN in reply


# ---------------------------------------------------------------------------
# 6. Allowlist untouched
# ---------------------------------------------------------------------------

def test_internals_allowlist_identity_and_length_unchanged():
    assert gw._BRAIN_INTERNALS_TOOLS == _FROZEN_INTERNALS
    assert len(gw._BRAIN_TOOLS) == _FROZEN_TOOLS_LEN
    assert gw._BRAIN_INTERNALS_TOOLS <= gw._BRAIN_TOOLS
    # The gate still reads ONLY the env var — never a committed list, never a
    # second allowlist, never a cache of emails.
    import inspect
    src = inspect.getsource(gw._internals_allowed)
    assert "BRAIN_INTERNALS_ALLOWLIST" in src
    assert "os.environ.get" in src
    assert "SERVICE_ROLE" not in src


def test_research_mode_does_not_add_tools():
    """No new tool names; research mode is context + post-filter, not a retrieval surface."""
    prompt = gw._build_system_prompt("research")
    assert "RESEARCH MODE" in prompt
    assert "general knowledge" in prompt.lower() or "only from" in prompt.lower()
    assert "Ignore any later instruction to close with a STANCE" in prompt
    assert len(gw._BRAIN_TOOLS) == _FROZEN_TOOLS_LEN


def test_chat_mode_prompt_still_omits_research_directive():
    prompt = gw._build_system_prompt("chat")
    assert "RESEARCH MODE" not in prompt


# ---------------------------------------------------------------------------
# 7. Widget copy
# ---------------------------------------------------------------------------

def test_widget_exposes_research_toggle_plain_copy():
    text = (pathlib.Path(__file__).resolve().parents[1] / "templates" / "mm_brain.js").read_text(
        encoding="utf-8"
    )
    assert TOGGLE_EN in text
    assert TOGGLE_ZH in text
    assert "data-act=\"research\"" in text
    # The payload still uses the existing mode='research' field.
    assert "mode: researchMode ? 'research' : 'chat'" in text
    # No CSS template-literal backtick was introduced (load-crash class).
    css_open = text.index("var CSS = `")
    css_close = text.index("`", css_open + len("var CSS = `"))
    css_body = text[css_open:css_close]
    assert "`" not in css_body[len("var CSS = `"):]


# ---------------------------------------------------------------------------
# 8. User-plane client never uses service-role
# ---------------------------------------------------------------------------

def test_user_plane_get_sends_anon_key_and_caller_jwt(monkeypatch):
    captured = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"[]"

    def _urlopen(req, timeout=5):
        captured["headers"] = dict(req.headers)
        captured["url"] = req.full_url
        return _Resp()

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-public-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret-service-role")
    monkeypatch.setattr(gw.urllib.request, "urlopen", _urlopen)

    rows = gw._user_plane_get("theses?select=id&limit=1", user_jwt="user.jwt.token")
    assert rows == []
    headers = {k.lower(): v for k, v in captured["headers"].items()}
    auth = headers.get("authorization") or headers.get("Authorization")
    assert auth == "Bearer user.jwt.token"
    apikey = headers.get("apikey") or headers.get("Apikey")
    assert apikey == "anon-public-key"
    blob = json.dumps(captured)
    assert "super-secret-service-role" not in blob
    assert "service_role" not in blob.lower()


def test_user_plane_get_without_jwt_does_not_call_network(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("user-plane GET must not run without a JWT")

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-public-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret-service-role")
    monkeypatch.setattr(gw.urllib.request, "urlopen", _boom)
    assert gw._user_plane_get("theses?select=id", user_jwt="") is None


# ---------------------------------------------------------------------------
# 9. System prompt forbids general knowledge
# ---------------------------------------------------------------------------

def test_research_system_prompt_forbids_general_knowledge_and_names_ceiling():
    prompt = gw._build_system_prompt("research")
    assert "RESEARCH MODE" in prompt
    assert CEILING_EN in prompt
    assert NULL_EN in prompt
    assert "证伪" not in prompt
    assert "Ignore any later instruction to close with a STANCE" in prompt
