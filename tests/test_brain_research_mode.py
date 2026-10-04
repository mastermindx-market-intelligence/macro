"""B-F11-6 / MO-PAID-031 — F11-GROUNDED research turn (Sol 5967105152 recompose of #7100).

RED-first suite. Uses the gateway's existing LLM test doubles (tests/test_brain_gateway.py
_MockBlock/_MockResponse/_sse), no network, no data/ or site/ from the checkout — fixtures
write their own briefing under tmp.

What is closed is ONE turn, not a mode: ``mode="research"`` from the Terminal Analysis
thesis workspace, identified ONLY by a VALID typed ``ai_context`` client block compiled by
the W1-C context compiler (``origin.legacy is False``, not malformed, ambient
``page="analysis"``/``panel="theses"``). Every other research turn — dashboard, company
panel, chart Terminal, a legacy/raw ``page=analysis,panel=theses`` context, a malformed
block — keeps today's global Deep Research path byte-for-byte (DEEP PASS directive, W6b
budget, approved tool exposure, exact-source behaviour).

Coverage:
  1. Outside coverage → exact null form (EN+ZH) + plain list of what was checked.
  2. Ceiling sentence on every grounded answer (verbatim EN + ZH).
  3. 'What this read used' list of plain names + asof dates (never file paths).
  4. JWT-absent prints the unsigned-in null (EN+ZH); user-plane reads use anon+Bearer only.
  5. Forbidden-output filter: judgement scores, falsifier/refuted/证伪, allowlist tool
     names, imperative buy/sell/size/target.
  6. An answer that cites no used artifact is replaced by the null form.
  7. Sol §9 discriminating matrix for BOTH chat() and chat_stream() — see the last section.

RETIRED from the archived suite (the GLOBAL research-mode override was never ported):
  test_research_mode_does_not_add_tools — asserted the global directive and a frozen
      len(_BRAIN_TOOLS)==63 (Sol: no frozen global count).
  test_research_mode_offers_no_retrieval_tools / test_research_mode_dispatch_refuses_vault_and_world_state
      — global empty tool schemas + dispatcher refusal; Deep Research keeps its tools.
  test_research_mode_does_not_raise_w6b_tool_budget — global budget clamp; the W6b budget
      is retained for every non-grounded research turn (asserted below instead).
  test_internals_allowlist_identity_and_length_unchanged — frozen allowlist identity.
  test_widget_exposes_research_toggle_plain_copy / test_widget_slash_research_does_not_insert_w6b_deep_dive
      — widget relabel not ported (templates/site mm_brain.js untouched).
  test_corpus3_selects_frozen_f11_columns_and_fetches_monitors — asserted columns that do
      not exist on mastermind-terminal master (version_number/title/claim/recorded_at,
      notes, thesis_condition_links); replaced by test_corpus3_reads_only_measured_terminal_columns.
  test_research_user_artifacts_monitor_state_* — read a table (thesis_condition_links)
      that does not exist on master; corpus 3 no longer reads monitors.
"""
from __future__ import annotations

import inspect
import json
import os
import pathlib
import sys
from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine.neuralweb import brain_gateway as gw  # noqa: E402
from tests.test_brain_gateway import _MockBlock, _MockResponse, _sse  # noqa: E402


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


def _client_block(*, origin_id: str = "analysis-mount-1", context_revision: int = 1,
                  captured_at: str | None = None, pinned: list | None = None,
                  active: dict | None = None, ambient: dict | None = None) -> dict:
    """A VALID ai_context_client.v1 block — the shape the Terminal's AnalysisBrainHost
    provider (Lane T, PR #798) emits. Same helper shape as the context-compiler suite."""
    return {
        "schema": "ai_context_client.v1",
        "origin_id": origin_id,
        "context_revision": context_revision,
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pinned": pinned if pinned is not None else [],
        "active": active,
        "ambient": ambient if ambient is not None else
        {"symbol": None, "timeframe": None, "page": "analysis", "panel": "theses"},
    }


def _typed_context(*, page: str = "analysis", panel: str | None = "theses",
                   symbol: str | None = None) -> dict:
    """context carrying a VALID typed block for the given ambient route."""
    return {"ai_context": _client_block(
        ambient={"symbol": symbol, "timeframe": None, "page": page, "panel": panel})}


GROUNDED_CTX = _typed_context()                                   # /analysis?view=theses
COMPANY_CTX = _typed_context(panel="company", symbol="NVDA")      # ordinary Analysis
TERMINAL_THESES_CTX = _typed_context(page="terminal", panel="theses")  # Sol: a DEAD tuple
LEGACY_CTX = {"page": "analysis", "panel": "theses", "symbol": "NVDA"}  # raw, untyped
MALFORMED_CTX = {"ai_context": {"schema": "ai_context_client.v1", "origin_id": "x"}}


def _research_chat(tmp_path, reply_text: str, message: str = "What is the capital of France?",
                   user_jwt: str = "", company_source_span: dict | None = None,
                   history: list[dict] | None = None, images: list[str] | None = None, *,
                   with_briefing: bool = True, context: dict | None = None):
    """Drive gw.chat(mode='research') from the Analysis thesis workspace (a VALID typed
    client block) with the gateway's loop replaced by a double."""
    root = _make_research_root(tmp_path, with_briefing=with_briefing)
    ctx = GROUNDED_CTX if context is None else context

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
                                company_source_span=company_source_span,
                                history=history,
                                images=images,
                                context=ctx,
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


def test_research_mode_does_not_resolve_exact_source_attachment(tmp_path):
    """MO-PAID-031 closed corpus: company_source_span is not a research input."""
    with patch.object(
        gw,
        "_resolve_company_source_attachment",
        side_effect=AssertionError("research mode must not resolve exact-source attachments"),
    ) as resolver:
        result = _research_chat(
            tmp_path,
            "The daily briefing says the US session was mixed and breadth was thin.",
            message="How did the US session look?",
            company_source_span={"forbidden": "exact-source"},
        )
    resolver.assert_not_called()
    assert "Daily briefing" in result["reply"]
    assert CEILING_EN in result["reply"]


def test_research_mode_does_not_resolve_images(tmp_path):
    """Images are normal-chat inputs, not one of MO-PAID-031 corpora 1-3."""
    with patch.object(
        gw,
        "_image_blocks",
        side_effect=AssertionError("research mode must not resolve image attachments"),
    ) as resolver:
        result = _research_chat(
            tmp_path,
            "The daily briefing says the US session was mixed and breadth was thin.",
            message="How did the US session look?",
            images=["data:image/png;base64,Zm9yYmlkZGVu"],
        )
    resolver.assert_not_called()
    assert "Daily briefing" in result["reply"]


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


def test_chat_mode_prompt_still_omits_research_directive():
    prompt = gw._build_system_prompt("chat")
    assert "RESEARCH MODE" not in prompt


# ---------------------------------------------------------------------------
# 7. Widget copy
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 10. Round-2 majors — closed corpus, F11 schema, filter over-match, slash copy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sentence",
    [
        "The daily briefing says the US session was mixed and breadth was 40%.",
        "Funds continued to buy.",
        "The confidence interval widened.",
        "The Fed target of 2 percent is unchanged.",
    ],
)
def test_forbidden_filter_does_not_overmatch_published_facts(sentence):
    """Spec (4) is judgement % / conviction rank / imperative trade — not any % or buy."""
    assert gw._research_sentence_forbidden(sentence) is False
    kept, withheld = gw._research_forbidden_filter(sentence)
    assert withheld is False
    assert sentence.rstrip(".") in kept or sentence in kept


def test_postprocess_keeps_grounded_answer_that_cites_a_published_percent():
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed. Breadth was thin."),
        ],
        "jwt_present": False,
    }
    body, withheld = gw._research_postprocess(
        "The daily briefing says the US session was mixed and breadth was 40%.",
        corpus,
    )
    assert NULL_EN not in body
    assert "daily briefing" in body.lower()
    assert "40%" in body
    assert withheld is False
    assert CEILING_EN in body


def test_published_price_target_is_kept_and_does_not_null():
    """H1: a citing sentence that reports a published price target must be kept;
    the postprocess must not treat a drop as 'no artifact cited' and must not
    replace the reply with the null form.
    """
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed. A published price target of 240."),
        ],
        "jwt_present": False,
    }
    body, withheld = gw._research_postprocess(
        "The daily briefing listed a published price target of 240.",
        corpus,
    )
    assert withheld is False, body
    assert not body.startswith(NULL_EN), body
    assert "price target" in body.lower()
    assert CEILING_EN in body


def test_published_price_target_is_not_forbidden_in_filter():
    """H1: filter over-match — published/reported price targets are NOT imperative."""
    raw = "The daily briefing listed a published price target of 240."
    kept, withheld = gw._research_forbidden_filter(raw)
    assert withheld is False
    assert "price target" in kept.lower()


@pytest.mark.parametrize(
    "raw",
    [
        # H1: published/reported price targets stay kept.
        "The daily briefing listed a published price target of 240.",
        "Analysts reported a target price of 280.",
        "The note mentioned a published target price of 200.",
    ],
)
def test_published_price_target_variants_keep_through_filter(raw):
    kept, withheld = gw._research_forbidden_filter(raw)
    assert withheld is False
    # Sentence (modulo terminal punctuation) survives the filter.
    assert raw.rstrip(".") in kept or raw in kept


@pytest.mark.parametrize(
    "raw",
    [
        # H1: imperative trade targets stay filtered.
        "Set a price target of 240 on the name.",
        "Place a target price at 280 now.",
    ],
)
def test_imperative_price_target_still_filtered(raw):
    kept, withheld = gw._research_forbidden_filter(raw)
    assert withheld is True
    assert raw.strip().rstrip(".") not in kept


# ---------------------------------------------------------------------------
# MAJOR 1 RED-first: reportative published price-target prose must NOT be
# withheld; object-interposed imperative "Give NVDA a price target of 240
# now." must be forbidden.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sentence,expect_forbidden",
    [
        # Reportative: cite a briefing that "hit a target" — must be kept.
        ("The daily briefing said the index hit a target of 4800.", False),
        # Reportative: cite a briefing that "gave a price target" — must be kept.
        ("The daily briefing gave a price target of 240.", False),
    ],
)
def test_m1_reportative_price_target_sentences_not_withheld(sentence, expect_forbidden):
    """MAJOR 1 RED: a citing sentence that *reports* a published price target
    ("hit a target", "gave a price target") must NOT be filtered. The EN
    price-target branch is sentence-anchored so a mid-sentence reportative
    verb does not match. `_research_postprocess` keeps the sentence and adds
    no "withheld" disclosure.
    """
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed. Index hit a target of 4800."),
        ],
        "jwt_present": False,
    }
    body, withheld = gw._research_postprocess(sentence, corpus)
    assert withheld is False, body
    assert sentence.rstrip(".") in body or sentence in body, body
    assert WITHHELD_EN not in body, body
    assert WITHHELD_ZH not in body, body


def test_m1_object_interposed_imperative_price_target_forbidden():
    """MAJOR 1 RED: "Give NVDA a price target of 240 now." is an imperative
    with an object token ("NVDA") between the verb and "price target"; it must
    be forbidden. The sentence-anchored branch absorbs 0-3 intervening tokens
    so the object does not block the match.
    """
    sentence = "Give NVDA a price target of 240 now."
    assert gw._research_sentence_forbidden(sentence) is True
    kept, withheld = gw._research_forbidden_filter(sentence)
    assert withheld is True
    assert sentence not in kept


# ---------------------------------------------------------------------------
# MAJOR 2 RED-first: ZH judgement-% shapes must be forbidden when originated.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sentence",
    [
        # Ruling exact strings (no trailing 。 — (?!\S) requires word-end or string-end)
        "每日简报说成功率80%",        # 成功率80%
        "每日简报说我有80%的把握",   # 我有80%的把握
        "每日简报说80%把握",         # 80%把握
        "每日简报说八成把握",        # 八成把握
    ],
)
def test_m2_zh_judgment_percent_forbidden(sentence):
    """MAJOR 2 RED: ZH originated confidence/conviction percentages —
    成功率80%, 我有80%的把握, 80%把握, 八成把握 — are forbidden when
    originated. `_research_sentence_forbidden` returns True; end-to-end the
    postprocess returns withheld=True and appends the disclosure.
    """
    assert gw._research_sentence_forbidden(sentence) is True
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed."),
        ],
        "jwt_present": False,
    }
    body, withheld = gw._research_postprocess(
        f"每日简报说市场分化。{sentence}",
        corpus,
    )
    assert withheld is True, body
    assert WITHHELD_EN in body, body
    assert WITHHELD_ZH in body, body


def test_m2_en_judgment_percent_still_green():
    """MAJOR 2: the existing EN "80% confident" case stays green."""
    kept, withheld = gw._research_forbidden_filter("I have 80% confidence this works.")
    assert withheld is True, kept
    assert "80%" not in kept


# ---------------------------------------------------------------------------
# H2: judgement % attached to 'confident', ZH sentence split, ZH trade verbs
# ---------------------------------------------------------------------------

def test_research_percent_matches_confident():
    """H2: judgement % attached to 'confident' must be filtered as a judgement %."""
    kept, withheld = gw._research_forbidden_filter("I'm 80% confident this setup works.")
    assert withheld is True, kept
    assert "80%" not in kept
    assert "confident" not in kept


def test_research_sentence_split_on_cjk_period_without_whitespace():
    """H2: a ZH clause after a CJK period is its own sentence (split, not joined)."""
    parts = gw._RESEARCH_SENTENCE_SPLIT.split("每日简报说美国交易时段表现分化。请买入 NVDA。")
    # The ZH clause after 。 must be its own sentence, not appended to the prior one.
    assert any(p == "请买入 NVDA。" for p in parts), parts
    for p in parts:
        if "请买入" in p:
            assert "每日简报说" not in p, p
            assert "分化" not in p, p


def test_research_trade_matches_zh_instruction_verbs():
    """H2: ZH imperative buy/sell instructions are filtered."""
    for sentence in (
        "请买入 NVDA。",
        "买入 NVDA。",
        "卖出 AAPL。",
    ):
        kept, withheld = gw._research_forbidden_filter(sentence)
        assert withheld is True, (sentence, kept)
        assert sentence not in kept, (sentence, kept)


def test_zh_postprocess_drops_zh_instruction_verb():
    """H2 RED: the measured ZH string drops the buy instruction and is withheld."""
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed."),
        ],
        "jwt_present": False,
    }
    body, withheld = gw._research_postprocess(
        "每日简报说美国交易时段表现分化。请买入 NVDA。",
        corpus,
    )
    assert withheld is True, body
    assert "请买入 NVDA" not in body
    assert "daily briefing" in body.lower()
    assert WITHHELD_EN in body
    assert WITHHELD_ZH in body


# ---------------------------------------------------------------------------
# H3: ZH used-list fallback writes '日期不明' (no ASCII letters on the ZH line)
# ---------------------------------------------------------------------------

def test_format_used_list_zh_fallback_uses_chinese():
    """H3: the ZH used-list fallback must use '日期不明', not ASCII 'unknown date'."""
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", asof=""),
        ],
        "jwt_present": False,
    }
    out = gw._format_used_list(corpus)
    # The ZH artifact line carries the asof in CJK parentheses — when asof is
    # empty, the fallback inside the CJK parentheses must be '日期不明', never
    # ASCII 'unknown date'.
    zh_lines = [ln for ln in out.splitlines() if ln.startswith("- 每日简报")]
    assert zh_lines, out
    zh_line = zh_lines[0]
    assert "（截至 日期不明）" in zh_line, zh_line
    # No ASCII letters on the ZH used-list line.
    assert not any(c.isascii() and c.isalpha() for c in zh_line), zh_line


def test_packet_level_gaps_attached_as_null_disclosure(tmp_path, monkeypatch):
    """Tier-2 null disclosure includes packet-level gaps from build_packet."""
    def fake_build(_root):
        return {
            "version": 1,
            "gaps": ["tape: missing quotes", "events: no item inside the freshness window"],
            "tape": None,
        }

    monkeypatch.setattr("engine.neuralweb.market_packet.build_packet", fake_build)
    arts = gw._research_packet_artifacts(tmp_path)
    joined = " ".join(
        f"{a.get('plain_en')} {a.get('null_disclosure')}" for a in arts
    )
    assert "tape: missing quotes" in joined
    assert "Live market state packet" in joined


# ---------------------------------------------------------------------------
# Heal-round 3 — ZH reportative keep, ZH ceiling rejoin, empty-body floor,
# EN abbreviation preservation, multiple-adverb percent.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw",
    [
        # MAJOR 1: reportative flow facts must stay kept, even though they
        # contain 买入/卖出. The ZH trade branch is now imperative-anchored
        # (clause-initial + object), so a reportative verb in the middle of
        # a clause is not matched by the filter.
        "每日简报说资金持续买入。",
        "每日简报说南向资金继续买入港股。",
        "每日简报说外资净买入债券。",
    ],
)
def test_zh_reportative_flow_verbs_are_kept_through_filter(raw):
    """MAJOR 1 RED-on-previous-head: 持续/继续/净 + 买入 are reportative,
    not imperative; the filter must not drop them and the postprocess must
    not treat the drop as a coverage null.
    """
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed. Funds continued to buy."),
        ],
        "jwt_present": False,
    }
    body, withheld = gw._research_postprocess(raw, corpus)
    assert withheld is False, body
    assert not body.startswith(NULL_EN), body
    # The reportative clause must still be present somewhere in the reply.
    # Use substring checks that tolerate the used-list and ceiling that the
    # postprocess appends.
    if "买入" in raw or "卖出" in raw:
        # The verb must still be present (it was kept by the filter).
        assert "买入" in body or "卖出" in body, body
    # The used-list carries the artifact plain name and the ceiling sentence
    # is appended as required by spec (2).
    assert USED_EN in body
    assert USED_ZH in body
    assert CEILING_EN in body


def test_zh_ceiling_rejoin_injects_no_ascii_space():
    """MAJOR 2 RED-on-previous-head: a model-emitted ZH ceiling stays
    byte-identical. `_RESEARCH_SENTENCE_SPLIT` split on `。` without trailing
    whitespace, and `_research_forbidden_filter` rejoined the kept pieces
    with `" ".join`, which injected an ASCII space between the two ZH
    sentences of the ceiling. Now the rejoin walks the original text so the
    boundary character (`。`) is followed directly by the next clause.
    """
    raw = "每日简报说市场分化。这是我们已发布内容的解读。这不是信号、不是评级、也不是建议。"
    kept, withheld = gw._research_forbidden_filter(raw)
    assert withheld is False
    # The two ZH sentences of the ceiling are joined with NO ASCII space.
    assert "解读。这不是信号" in kept, kept
    # And the kept body is byte-identical (modulo strip) to the source.
    assert kept == raw.strip(), kept


def test_zh_ceiling_present_verbatim_end_to_end(tmp_path):
    """MAJOR 2: a model-emitted ZH ceiling reaches the user verbatim."""
    result = _research_chat(
        tmp_path,
        "每日简报说市场分化。这是我们已发布内容的解读。这不是信号、不是评级、也不是建议。",
        message="How did the US session look?",
    )
    reply = result["reply"]
    assert "解读。这不是信号" in reply, reply
    # The full ZH ceiling sentence is present.
    assert CEILING_ZH in reply, reply


def test_en_sentence_split_preserves_u_s_and_e_g():
    """MINOR 1 RED-on-previous-head: mid-sentence abbreviations like U.S. /
    e.g. / Inc. / Waiting... must not be split apart. The ASCII branch only
    splits on `[.!?] + whitespace + uppercase letter`.
    """
    for raw, expected in (
        ("The daily briefing says the U.S. session was mixed.", "U.S. session was mixed."),
        ("The note flagged e.g. a recovery in flows.", "e.g. a recovery in flows."),
        ("Yesterday Acme, Inc. announced earnings.", "Acme, Inc. announced earnings."),
        ("Waiting... the daily briefing says flows were flat.", "Waiting... the daily briefing says flows were flat."),
    ):
        kept, withheld = gw._research_forbidden_filter(raw)
        assert withheld is False
        assert expected in kept, (raw, kept)


def test_postprocess_empty_body_fallback_fires_when_filter_ate_everything():
    """MAJOR 3 RED-on-previous-head: when the forbidden-output filter ate
    every citing sentence, the reply must NOT be blank. A plain EN+ZH
    sentence (distinct from the spec 3 coverage null) takes its place so
    the user sees a real sentence, then the used-list and ceiling, then the
    withholding disclosure.
    """
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed."),
        ],
        "jwt_present": False,
    }
    # The input cites the artifact (carries "daily briefing") but EVERY
    # sentence is filterable:
    #   - "Buy NVDA on the daily briefing." — sentence-initial Buy + an
    #     object token matches the trade filter (after H1 the EN branch
    #     requires `buy|sell` followed by a non-word, non-dash char and
    #     then `\s+\S`; "Buy NVDA" still matches while "Buy-side" no
    #     longer does).
    #   - "Score this a 0.9." — the 0-1 score filter.
    # The original body cited the artifact (so `_research_cites_artifact`
    # returns True), but after filtering every sentence is dropped and the
    # kept body is empty.
    raw = "Buy NVDA on the daily briefing. Score this a 0.9."
    body, withheld = gw._research_postprocess(raw, corpus)
    assert withheld is True, body
    # The plain-language floor must be present — NOT the spec 3 coverage null.
    assert not body.startswith(NULL_EN), body
    assert "relevant sentences from the published reading were filtered" in body.lower(), body
    assert "已发布读数中相关的句子因读起来像信号而被隐去" in body, body
    # The used-list, ceiling, and WITHHELD disclosure still ride along.
    assert USED_EN in body
    assert USED_ZH in body
    assert CEILING_EN in body
    assert WITHHELD_EN in body
    assert WITHHELD_ZH in body


@pytest.mark.parametrize(
    "raw",
    [
        # MINOR 3: a percentage attached to a judgement with multiple leading
        # adverbs. The previous regex `(?:of\s+|is\s+|at\s+)?` consumed only
        # one of `is` / `at`, leaving the second ad-hoc. Now the noun-form
        # alternative permits any number of `of|is|at|about|...` adverbs.
        "Confidence is at 70%.",
        "Confidence of about 70% is the read.",
        "Conviction is at around 70%.",
    ],
)
def test_research_percent_matches_multiple_adverbs(raw):
    """MINOR 3: judgement % after multiple adverbs must be filtered."""
    kept, withheld = gw._research_forbidden_filter(raw)
    assert withheld is True, (raw, kept)


# ---------------------------------------------------------------------------
# H1 (heal round): EN buy/sell branch keeps reportative compound adjectives
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sentence",
    [
        # H1 RED-on-previous-head: a published desk prose that uses a
        # `Buy-side` / `Sell-side` compound adjective was over-matched by
        # the EN trade regex (`(?:^|(?<=[.!?。！？]\s))(?:buy|sell)\b`
        # fires on the `y|-` boundary of the compound). The new branch
        # requires `(?![\w-])\s+\S` so the compound is kept.
        "Buy-side flows were strong according to the daily briefing.",
        "Sell-side positioning was thin in the daily briefing.",
        "The daily briefing reported buy-side and sell-side flows were mixed.",
    ],
)
def test_research_trade_keeps_buy_side_sell_side_compound(sentence):
    """H1: EN buy/sell branch keeps reportative `Buy-side` / `Sell-side`."""
    assert gw._research_sentence_forbidden(sentence) is False
    kept, withheld = gw._research_forbidden_filter(sentence)
    assert withheld is False, (sentence, kept)
    assert sentence.rstrip(".") in kept or sentence in kept


@pytest.mark.parametrize(
    "sentence",
    [
        # H1 imperative cases must STILL be filtered after the fix.
        "Buy NVDA now.",
        "You should buy NVDA.",
        "Sell NVDA immediately.",
        "Sell the position and size it down.",
        "Buy NVDA on the daily briefing.",
    ],
)
def test_research_trade_still_filters_imperative(sentence):
    """H1: imperative buy/sell stays filtered after the EN branch fix."""
    kept, withheld = gw._research_forbidden_filter(sentence)
    assert withheld is True, (sentence, kept)
    assert sentence not in kept, (sentence, kept)


# ---------------------------------------------------------------------------
# H2 (heal round): `confidence interval` / `置信区间` excluded from
# judgement-% filter
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sentence",
    [
        # H2 RED-on-previous-head: a published 95% CI is a quantitative
        # read, not a judgement; the keep-list says so and the contract
        # names it as a published fact the read may carry. The judgement-%
        # filter must NOT swallow it.
        "The daily briefing reports a 95% confidence interval for the estimate.",
        "95% confidence interval for the read.",
        "The 80% confidence interval was wide.",
        "Confidence interval of 95%.",
        "每日的95%置信区间在收窄。",  # ZH
    ],
)
def test_research_percent_keeps_published_confidence_interval(sentence):
    """H2: `confidence interval` / `置信区间` must NOT be filtered as judgement-%."""
    assert gw._RESEARCH_PERCENT.search(sentence) is None, sentence
    assert gw._research_sentence_forbidden(sentence) is False
    kept, withheld = gw._research_forbidden_filter(sentence)
    assert withheld is False, (sentence, kept)


# ---------------------------------------------------------------------------
# m3 (heal round): model-emitted verbatim ZH ceiling must NOT be duplicated
# ---------------------------------------------------------------------------

def test_research_postprocess_does_not_duplicate_model_emitted_zh_ceiling():
    """m3: if the model emits the verbatim ZH ceiling alone, the
    postprocessor must append only the missing EN ceiling, not duplicate
    the ZH one.
    """
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed."),
        ],
        "jwt_present": False,
    }
    raw = "每日简报说市场分化。\n\n" + gw._RESEARCH_CEILING_ZH
    body, withheld = gw._research_postprocess(raw, corpus)
    assert body.count(gw._RESEARCH_CEILING_ZH) == 1, body
    assert body.count(gw._RESEARCH_CEILING_EN) == 1, body


def test_research_postprocess_does_not_duplicate_model_emitted_en_ceiling():
    """m3 mirror: a model-emitted verbatim EN ceiling is not duplicated either."""
    corpus = {
        "artifacts": [
            gw._research_artifact("Daily briefing", "每日简报", "2026-09-12",
                                  "US session mixed."),
        ],
        "jwt_present": False,
    }
    raw = "The daily briefing says the US session was mixed.\n\n" + gw._RESEARCH_CEILING_EN
    body, withheld = gw._research_postprocess(raw, corpus)
    assert body.count(gw._RESEARCH_CEILING_EN) == 1, body
    assert body.count(gw._RESEARCH_CEILING_ZH) == 1, body


# ---------------------------------------------------------------------------
# m4 (heal round): monitor state outside the four §7.7 plain words falls
# back to a plain EN+ZH sentence, not the raw status enum
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Adapted from the archive — the boundary is the F11 predicate, not `mode`
# ---------------------------------------------------------------------------

def test_f11_predicate_is_private_and_discriminating():
    """Spec item 2: ONE predicate; legacy/raw, malformed, company, chart-Terminal all False."""
    from engine.intelligence_workspace import context_compiler as cc
    env = cc.compile_envelope("How did the US session look?", GROUNDED_CTX)
    assert env["origin"]["legacy"] is False and env["context_flags"]["malformed"] is False
    assert gw._f11_grounded("research", env) is True
    assert gw._f11_grounded("chat", env) is False
    for ctx in (LEGACY_CTX, MALFORMED_CTX, COMPANY_CTX, TERMINAL_THESES_CTX, {}, None):
        assert gw._f11_grounded("research", cc.compile_envelope("q", ctx)) is False, ctx
    assert gw._f11_grounded("research", None) is False
    assert gw._f11_grounded("research", {}) is False


def test_research_mode_exact_source_gate_covers_chat_and_stream():
    """Spec items 1+4: compile → predicate → resolver, in BOTH public entrypoints."""
    guard = "if company_source_span is not None and not _grounded:"
    for fn in (gw.chat, gw.chat_stream):
        src = inspect.getsource(fn)
        assert guard in src
        assert src.index("_ctx_envelope = _ctx_compiler.compile_envelope(clean_msg, context)") \
            < src.index("_grounded = _f11_grounded(mode, _ctx_envelope)") < src.index(guard)
        assert src.index("clean_msg, err = _sanitize_brain_message(message, max_len=2000)") \
            < src.index("_ctx_envelope = _ctx_compiler.compile_envelope(clean_msg, context)")


def test_research_mode_closed_corpus_guards_cover_both_entrypoints():
    """Non-streaming and streaming share the same fail-closed boundary, keyed on the predicate."""
    for fn in (gw.chat, gw.chat_stream):
        src = inspect.getsource(fn)
        assert "image_blocks = [] if _grounded else _image_blocks(images)" in src
        assert "if thread_id and not _grounded" in src
        assert "active_history = [] if _grounded else" in src
        assert "None if _grounded or _selected_ontology or images" in src
        assert "_selected_ontology = False if _grounded else _ontology_selection_requested(context)" in src
        assert '_selection_notice = "" if _grounded else _ontology_preflight_notice(' in src


def test_research_mode_does_not_consult_client_history(tmp_path):
    """Prior chat may contain general knowledge; it cannot become research grounding."""
    seen = {}

    def _mock_loop(*args, **kwargs):
        seen["history"] = args[2]
        seen["kwargs"] = kwargs
        return "The daily briefing says the US session was mixed and breadth was thin.", [], [], [], {}, [], []

    root = _make_research_root(tmp_path)
    with patch.object(gw, "_brain_quota_dir", return_value=tmp_path), \
         patch.object(gw, "_build_lane_providers", return_value=[{"client": MagicMock(), "model": "m"}]), \
         patch.object(gw, "_resolve_tier", return_value={"tier": "pro", "status": "active", "current_period_end": None}), \
         patch.object(gw, "_ensure_thread", return_value=None), \
         patch.object(gw, "_run_brain_loop", side_effect=_mock_loop), \
         patch("lib.ai_costs.record_usage", return_value=True):
        result = gw.chat("How did the US session look?", "user_research", mode="research", root=root,
                         context=GROUNDED_CTX,
                         history=[{"role": "assistant", "content": "Unpublished general-knowledge claim."}])
    assert seen["history"] == []
    assert seen["kwargs"].get("f11_grounded") is True
    assert seen["kwargs"]["source_prompt"].startswith("[GROUNDED RESEARCH CORPUS")
    assert "Unpublished general-knowledge claim" not in result["reply"]


def test_grounded_system_prompt_forbids_general_knowledge_and_names_ceiling():
    prompt = gw._build_grounded_system_prompt()
    assert "RESEARCH MODE — GROUNDED READ" in prompt
    assert CEILING_EN in prompt
    assert NULL_EN in prompt
    assert "证伪" not in prompt
    assert "DEEP PASS" not in prompt
    # No chart/inline-chart, doctrine or analyst addenda ride on a grounded turn.
    assert gw._INLINE_CHART_SYSTEM_DIRECTIVE not in prompt
    assert gw._CHART_COMMAND_SYSTEM_DIRECTIVE not in prompt
    # The base prompt + contradiction block every mode carries are still there.
    assert gw._CONTRADICTION_DIRECTIVE in prompt


def test_global_research_directive_is_untouched():
    """Global Deep Research regression: _build_system_prompt('research') is today's prompt."""
    prompt = gw._build_system_prompt("research")
    assert prompt.startswith(gw._RESEARCH_SYSTEM_DIRECTIVE)
    assert "DEEP PASS" in gw._RESEARCH_SYSTEM_DIRECTIVE
    assert "GROUNDED READ" not in prompt
    assert CEILING_EN not in prompt


# ---------------------------------------------------------------------------
# Corpus 3 — the MEASURED Terminal schema (0012_thesis_objects.sql), nothing else
# ---------------------------------------------------------------------------

def test_corpus3_reads_only_measured_terminal_columns(monkeypatch):
    """Owner-only reads name only columns/tables that exist on mastermind-terminal master."""
    paths: list[str] = []

    def _fake_get(path, user_jwt, timeout=5):
        paths.append(path)
        if path.startswith("theses?"):
            return [{"id": "t-1", "current_version": 3, "lifecycle_state": "active",
                     "updated_at": "2026-10-01T12:00:00Z"}]
        if path.startswith("thesis_versions?"):
            return [{"id": "v-3", "thesis_id": "t-1", "version": 3,
                     "content": {"title": "Copper tightness into Q4"},
                     "system_recorded_at": "2026-10-01T12:00:00Z"}]
        raise AssertionError(f"unexpected user-plane path {path!r}")

    monkeypatch.setattr(gw, "_user_plane_get", _fake_get)
    arts = gw._research_user_artifacts("header.payload.sig")
    assert paths == [
        "theses?select=id,current_version,lifecycle_state,updated_at&order=updated_at.desc&limit=20",
        "thesis_versions?select=id,thesis_id,version,content,system_recorded_at&order=system_recorded_at.desc&limit=20",
    ]
    blob = json.dumps(arts, ensure_ascii=False)
    for absent in ("notes", "thesis_condition_links", "monitor", "version_number", '"recorded_at"', "current_version_id"):
        assert absent not in blob, absent
    assert "Copper tightness into Q4" in blob
    assert "t-1" not in blob.replace("thesis_id", "")  # never a row id in plain copy
    assert "header.payload.sig" not in blob


def test_corpus3_untitled_version_never_prints_a_row_id(monkeypatch):
    def _fake_get(path, user_jwt, timeout=5):
        if path.startswith("theses?"):
            return [{"id": "abc-123", "current_version": 1, "lifecycle_state": "draft", "updated_at": "2026-10-01T00:00:00Z"}]
        return [{"id": "v-1", "thesis_id": "abc-123", "version": 1, "content": {"body": 42}, "system_recorded_at": "2026-10-01T00:00:00Z"}]

    monkeypatch.setattr(gw, "_user_plane_get", _fake_get)
    blob = json.dumps(gw._research_user_artifacts("jwt"), ensure_ascii=False)
    assert "abc-123" not in blob and "v-1" not in blob
    assert "untitled" in blob.lower() or "version 1" in blob


# ---------------------------------------------------------------------------
# Sol §9 discriminating matrix — BOTH chat() and chat_stream(), end to end
# ---------------------------------------------------------------------------

ANSWER = "The daily briefing says the US session was mixed and breadth was thin."
JWT = "header.payload.sig-SECRET"


class _TextStreamCtx:
    def __init__(self, text: str):
        self._text = text

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def text_stream(self):
        yield self._text

    def get_final_message(self):
        return _MockResponse([_MockBlock("text", self._text)], "end_turn")


class _CapClient:
    """Permissive LLM double: records every create()/stream() kwargs, answers one text turn."""

    def __init__(self, answer: str = ANSWER):
        self.answer = answer
        self.messages = self
        self.calls: list[dict] = []

    def _snap(self, kw: dict) -> None:
        # The loop appends the assistant turn to the SAME list after the call; snapshot
        # the request as it was sent so the assertions judge what the model saw.
        rec = dict(kw)
        rec["messages"] = list(kw.get("messages") or [])
        self.calls.append(rec)

    def create(self, **kw):
        self._snap(kw)
        return _MockResponse([_MockBlock("text", self.answer)], "end_turn")

    def stream(self, **kw):
        self._snap(kw)
        return _TextStreamCtx(self.answer)


def _fake_attachment():
    att = MagicMock()
    att.failure = None
    att.resolved.prompt_block = "[EXACT SOURCE] the attached passage"
    att.resolved.receipt = {"ok": True, "kind": "test"}
    att.receipt_json = json.dumps(att.resolved.receipt)
    return att


class _Turn:
    def __init__(self, *, reply, events, result, client, spies):
        self.reply, self.events, self.result, self.client, self.spies = reply, events, result, client, spies

    @property
    def calls(self):
        return self.client.calls

    def blob(self) -> str:
        return json.dumps({"calls": self.calls, "events": self.events, "result": self.result,
                           "reply": self.reply}, default=str, ensure_ascii=False)


def _drive(tmp_path, *, stream: bool, context, message: str = "How did the US session look?",
           answer: str = ANSWER, user_jwt: str = "", company_source_span: dict | None = None,
           history: list[dict] | None = None, images: list[str] | None = None,
           thread_id: str | None = None, user_rows: list | None = None,
           loop_spy: list | None = None) -> _Turn:
    root = _make_research_root(tmp_path)
    client = _CapClient(answer)
    providers = [{"name": "anthropic", "model": "claude-test", "client": client}]
    spies: dict = {}
    real_loop = gw._run_brain_loop
    real_stream = gw._run_brain_loop_stream

    def _loop_rec(*a, **k):
        if loop_spy is not None:
            loop_spy.append((a, k))
        return real_loop(*a, **k)

    def _stream_rec(*a, **k):
        if loop_spy is not None:
            loop_spy.append((a, k))
        return real_stream(*a, **k)

    with ExitStack() as st:
        st.enter_context(patch.object(gw, "_brain_quota_dir", return_value=tmp_path))
        st.enter_context(patch.object(gw, "_build_lane_providers", return_value=providers))
        st.enter_context(patch.object(gw, "_resolve_tier", return_value={
            "tier": "pro", "status": "active", "current_period_end": None}))
        st.enter_context(patch.object(gw, "_ensure_thread", return_value=("thread-1" if thread_id else None)))
        st.enter_context(patch.object(gw, "_append_message", return_value=None))
        st.enter_context(patch("lib.ai_costs.record_usage", return_value=True))
        st.enter_context(patch.object(gw, "_run_brain_loop", side_effect=_loop_rec))
        st.enter_context(patch.object(gw, "_run_brain_loop_stream", side_effect=_stream_rec))
        spies["dispatch"] = st.enter_context(patch.object(gw, "_dispatch_brain_tool", return_value={"ok": True}))
        spies["resolver"] = st.enter_context(patch.object(
            gw, "_resolve_company_source_attachment", side_effect=lambda *a, **k: _fake_attachment()))
        spies["preflight"] = st.enter_context(patch.object(gw, "_ontology_preflight_notice", return_value=""))
        spies["selected"] = st.enter_context(patch.object(gw, "_ontology_selection_requested", return_value=False))
        spies["history"] = st.enter_context(patch.object(gw, "_load_thread_history", return_value=[
            {"role": "assistant", "content": "Unpublished general-knowledge claim."}]))
        spies["user_plane"] = st.enter_context(patch.object(
            gw, "_user_plane_get", side_effect=lambda path, user_jwt, timeout=5: (user_rows or [])))
        kwargs = dict(mode="research", root=root, user_jwt=user_jwt, company_source_span=company_source_span,
                      history=history, images=images, context=context, thread_id=thread_id)
        if stream:
            events = _sse(list(gw.chat_stream(message, "user_research", **kwargs)))
            reply = ""
            for e in events:
                if e.get("type") == "delta":
                    reply += e.get("text", "")
                elif e.get("type") == "retract":
                    reply = e.get("text", "")
            return _Turn(reply=reply, events=events, result=None, client=client, spies=spies)
        result = gw.chat(message, "user_research", **kwargs)
        return _Turn(reply=result["reply"], events=[], result=result, client=client, spies=spies)


def _system_text(kw: dict) -> str:
    return json.dumps(kw.get("system"), default=str, ensure_ascii=False)


def _user_messages(kw: dict) -> list[str]:
    out = []
    for m in kw.get("messages") or []:
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, str):
            out.append(c)
        else:
            out.append("".join(
                (b.get("text") or "") if isinstance(b, dict) and b.get("type") == "text"
                else json.dumps(b, default=str, ensure_ascii=False)
                for b in (c or [])))
    return out


def _assert_grounded(turn: _Turn, *, jwt: str = ""):
    assert turn.calls, "the model was never called"
    for kw in turn.calls:
        assert not kw.get("tools"), kw.get("tools")                       # (f) zero tools offered
        assert "GROUNDED READ" in _system_text(kw) and "DEEP PASS" not in _system_text(kw)
        msgs = _user_messages(kw)
        assert len(kw.get("messages") or []) == 1 and len(msgs) == 1     # (g) no history
        assert msgs[0].startswith("[GROUNDED RESEARCH CORPUS")           # no ambient digest ahead of it
        assert "[USER QUESTION]" in msgs[0]
        assert "Unpublished general-knowledge claim" not in msgs[0]
        assert "[EXACT SOURCE]" not in msgs[0]
    assert turn.spies["dispatch"].call_count == 0                         # (f) zero dispatched
    assert turn.spies["resolver"].call_count == 0                         # (d)
    assert turn.spies["preflight"].call_count == 0                        # (e)
    assert turn.spies["selected"].call_count == 0                         # (e)
    assert turn.spies["history"].call_count == 0                          # (g)
    assert CEILING_EN in turn.reply and USED_EN in turn.reply             # (j)
    assert "Daily briefing" in turn.reply
    if jwt:
        assert turn.spies["user_plane"].call_count >= 1
        assert all((c.kwargs.get("user_jwt") or c.args[1]) == jwt
                   for c in turn.spies["user_plane"].call_args_list)      # (h) the CALLER's token
        assert JWT_ABSENT_EN not in turn.reply
        assert jwt not in turn.blob()                                      # never in prompt/response
    else:
        assert turn.spies["user_plane"].call_count == 0
        assert JWT_ABSENT_EN in turn.reply and JWT_ABSENT_ZH in turn.reply  # (i)


def _assert_global_deep_research(turn: _Turn):
    first = turn.calls[0]
    assert first.get("tools"), "global Deep Research must keep its approved tool exposure"
    assert "DEEP PASS" in _system_text(first) and "GROUNDED READ" not in _system_text(first)
    assert turn.spies["selected"].call_count >= 1                         # preflight path consumed as today
    assert CEILING_EN not in turn.reply and USED_EN not in turn.reply     # no grounded post-processing
    assert "[GROUNDED RESEARCH CORPUS" not in "".join(_user_messages(first))


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_matrix_a_validated_analysis_theses_enters_closed_corpus(tmp_path, stream):
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX,
                  company_source_span={"forbidden": "exact-source"},
                  images=["data:image/png;base64,Zm9yYmlkZGVu"],
                  history=[{"role": "assistant", "content": "Unpublished general-knowledge claim."}],
                  thread_id="thread-1")
    _assert_grounded(turn)
    if not stream:
        assert turn.result["ok"] is True
        assert "Unpublished general-knowledge claim" not in json.dumps(turn.result, default=str)
    else:
        assert any(e.get("type") == "context_receipt" for e in turn.events)
        assert any(e.get("type") == "done" for e in turn.events)


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_matrix_h_signed_in_caller_reads_own_theses_through_their_jwt(tmp_path, stream):
    rows = [{"id": "t-1", "current_version": 1, "lifecycle_state": "active", "updated_at": "2026-10-01T00:00:00Z"}]
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX, user_jwt=JWT, user_rows=rows)
    _assert_grounded(turn, jwt=JWT)


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
@pytest.mark.parametrize("ctx_name", ["LEGACY_CTX", "COMPANY_CTX", "MALFORMED_CTX", "TERMINAL_THESES_CTX"])
def test_matrix_bc_non_f11_research_keeps_global_deep_research(tmp_path, stream, ctx_name):
    ctx = globals()[ctx_name]
    turn = _drive(tmp_path, stream=stream, context=ctx)
    _assert_global_deep_research(turn)


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_matrix_d_exact_source_behaviour_remains_current_off_f11(tmp_path, stream):
    turn = _drive(tmp_path, stream=stream, context=LEGACY_CTX, company_source_span={"doc": "x", "span": [0, 10]})
    assert turn.spies["resolver"].call_count == 1
    assert any("[EXACT SOURCE]" in m for m in _user_messages(turn.calls[0]))
    _assert_global_deep_research(turn)


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_matrix_f_tool_budget_one_round_grounded_and_w6b_budget_kept_globally(tmp_path, stream):
    spy: list = []
    _drive(tmp_path, stream=stream, context=GROUNDED_CTX, loop_spy=spy)
    assert len(spy) == 1
    args, kwargs = spy[0]
    assert args[10] == 1 and kwargs.get("f11_grounded") is True and args[2] == []
    assert kwargs.get("image_blocks") == []
    spy.clear()
    _drive(tmp_path, stream=stream, context=LEGACY_CTX, loop_spy=spy)
    args, kwargs = spy[0]
    assert args[10] > 1, "the W6b research budget must survive off the grounded turn"
    assert "f11_grounded" not in kwargs and "source_prompt" not in kwargs


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_matrix_j_filters_hold_on_the_grounded_turn(tmp_path, stream):
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX,
                  answer=ANSWER + " I have 80% confidence this setup works. You should buy NVDA immediately.")
    assert "80% confidence" not in turn.reply and "buy NVDA" not in turn.reply
    assert WITHHELD_EN in turn.reply
    assert CEILING_EN in turn.reply and USED_EN in turn.reply


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_matrix_j_uncited_grounded_answer_is_the_null_form(tmp_path, stream):
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX,
                  answer="Generally speaking, markets were mixed.")
    assert turn.reply.startswith(NULL_EN) and NULL_ZH in turn.reply
    assert "Generally speaking" not in turn.reply


def test_matrix_grounded_suggestions_never_carry_an_action(tmp_path):
    turn = _drive(tmp_path, stream=False, context=GROUNDED_CTX,
                  answer=ANSWER + "\n\n[NEXT]\n- Buy NVDA now\n- What did the briefing say about breadth?")
    sugg = turn.result.get("suggestions") or []
    assert all("buy" not in s.lower() for s in sugg), sugg


def test_app_main_passes_the_verified_caller_token_and_extracts_nothing_new():
    """Spec item 5: app/main.py hands gw.chat/chat_stream the token require_user already
    injected — a guest passes the empty string — and adds no new header parsing."""
    src = pathlib.Path(__file__).resolve().parent.parent.joinpath("app", "main.py").read_text()
    needle = 'user_jwt="" if is_guest else (user.get("_access_token") or ""),'
    assert src.count(needle) == 2
    # The only writer of `_access_token` is require_user; the two gateway hand-offs read it.
    assert src.count('record["_access_token"] = token') == 1
    assert src.count("_access_token") == src.count('record["_access_token"] = token') \
        + src.count('user.get("_access_token")') + src.count("_mm_supabase_access_token") \
        + src.count("`_access_token`")
