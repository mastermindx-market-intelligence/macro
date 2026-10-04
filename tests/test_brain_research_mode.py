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
           loop_spy: list | None = None, tier: str = "pro",
           user_plane_unavailable: bool = False, client=None) -> _Turn:
    root = _make_research_root(tmp_path)
    client = client if client is not None else _CapClient(answer)
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
            "tier": tier, "status": "active" if tier == "pro" else "none",
            "current_period_end": None}))
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
            gw, "_user_plane_get",
            side_effect=lambda path, user_jwt, timeout=5: (None if user_plane_unavailable else (user_rows or []))))
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
        return _Turn(reply=result.get("reply", ""), events=[], result=result, client=client, spies=spies)


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


# ---------------------------------------------------------------------------
# 8. r2 repairs — Opus RO review of head 2180a46a (M1/M2, m3–m6, stream GAP)
# ---------------------------------------------------------------------------

MODEL_TRAILER = (
    "\n\nWhat this read used\n- Daily briefing (as of 2026-09-12)\n\n" + CEILING_EN + "\n" + CEILING_ZH
)


def _server_used_list(tmp_path, *, user_jwt: str = "", user_rows: list | None = None) -> str:
    """The list the SERVER prints for the matrix root — recomputed from the same files."""
    with patch.object(gw, "_user_plane_get", side_effect=lambda path, user_jwt, timeout=5: (user_rows or [])):
        corpus = gw._build_research_corpus(tmp_path / "repo", user_jwt=user_jwt)
    return gw._format_used_list(corpus)


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_r2_model_written_used_list_cannot_satisfy_citation(tmp_path, stream):
    """M1: a general-knowledge answer that ends with a dutiful model-written 'What this
    read used' list naming a real artifact is STILL the null form — a list is not a citation."""
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX,
                  message="What is the capital of France?",
                  answer="Paris is the capital of France." + MODEL_TRAILER)
    assert turn.reply.startswith(NULL_EN), turn.reply
    assert NULL_ZH in turn.reply
    assert "Paris" not in turn.reply
    assert turn.reply.count(USED_EN) == 1 and turn.reply.count(USED_ZH) == 1, turn.reply
    assert turn.reply.count(CEILING_EN) == 1 and turn.reply.count(CEILING_ZH) == 1, turn.reply


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_r2_model_written_used_list_is_replaced_by_the_servers(tmp_path, stream):
    """M2: when the prose DOES cite an artifact, the list that ships is the server's — a
    model-written list (markdown heading, numbered, out-of-corpus name, file path) never
    reaches the user."""
    answer = ("The daily briefing says the US session was mixed and breadth was thin.\n\n"
              "## What this read used:\n"
              "1. Daily briefing (as of 2026-09-12)\n"
              "2. Secret internal file /data/neuralweb/world_state.json (as of 2026-09-12)\n\n"
              "**本次阅读用到的内容**\n- 每日简报（截至 2026-09-12）\n\n" + CEILING_EN)
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX, answer=answer)
    assert turn.reply.startswith("The daily briefing says"), turn.reply
    assert "Secret internal" not in turn.reply and "world_state.json" not in turn.reply, turn.reply
    assert _server_used_list(tmp_path) in turn.reply, turn.reply
    assert turn.reply.count(USED_EN) == 1 and turn.reply.count(USED_ZH) == 1, turn.reply
    assert turn.reply.count(CEILING_EN) == 1 and turn.reply.count(CEILING_ZH) == 1, turn.reply


@pytest.mark.parametrize("raw, expected", [
    ("Breadth was thin.\n\nWhat this read used\n- Daily briefing (as of 2026-09-12)\n\n" + CEILING_EN + "\n" + CEILING_ZH,
     "Breadth was thin."),
    ("Breadth was thin.\n\n## What this read used:\n1. Daily briefing (as of 2026-09-12)\n2. Secret /data/x.json\n\n"
     "**本次阅读用到的内容**\n- 每日简报（截至 2026-09-12）",
     "Breadth was thin."),
    ("Breadth was thin.\n\nWhat this read used\n\nDaily briefing (as of 2026-09-12)\n\nMore prose after.",
     "Breadth was thin.\n\nMore prose after."),
    ("What this read used was the daily briefing, which says breadth was thin.",
     "What this read used was the daily briefing, which says breadth was thin."),
    ("Breadth was thin.\n" + JWT_ABSENT_EN + "\n" + JWT_ABSENT_ZH, "Breadth was thin."),
    ("", ""),
], ids=["plain-list", "markdown-numbered", "bare-asof-lines", "prose-phrase-kept", "jwt-sentence", "empty"])
def test_r2_strip_model_trailer_variants(raw, expected):
    assert gw._research_strip_model_trailer(raw) == expected


@pytest.mark.parametrize("raw", [
    "Breadth was mixed.\n- Buy NVDA.",
    "Breadth was mixed.\n\n- Buy NVDA now.",
    "Breadth was mixed.\n1. Sell TSLA.",
    "Breadth was mixed.\n• Buy NVDA today.",
    "- Buy NVDA.\nBreadth was mixed.",
    "Breadth was mixed.\n* Sell TSLA immediately.",
], ids=["dash", "blank-dash", "numbered", "bullet", "leading", "star"])
def test_r2_bulleted_imperative_is_withheld(raw):
    """m5: a list item is a sentence — the trade imperative behind a bullet or a number
    is withheld, the published sentence beside it is kept, and no marker dangles."""
    body, withheld = gw._research_forbidden_filter(raw)
    assert withheld is True, raw
    assert "Buy" not in body and "Sell" not in body, body
    assert body == "Breadth was mixed.", body


def test_r2_wrapped_sentence_is_not_split_at_a_bare_newline():
    raw = "The briefing says breadth was thin.\nIt also notes volume fell."
    assert gw._research_forbidden_filter(raw) == (raw, False)


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_r2_bulleted_imperative_is_withheld_end_to_end(tmp_path, stream):
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX,
                  answer="The daily briefing says breadth was thin.\n- Buy NVDA now.")
    assert "Buy NVDA" not in turn.reply, turn.reply
    assert turn.reply.startswith("The daily briefing says breadth was thin."), turn.reply
    assert WITHHELD_EN in turn.reply and WITHHELD_ZH in turn.reply


@pytest.mark.parametrize("ret, state, en_row", [
    (None, "unavailable", "- Your theses — could not be read this turn"),
    ([], "empty", "- Your theses — none readable this turn"),
    ([{"id": "t1", "current_version": 1, "updated_at": "2026-09-12T00:00:00Z"}], "ok",
     "- Your theses (as of 2026-09-12)"),
], ids=["unavailable", "empty", "ok"])
def test_r2_corpus3_read_outcome_is_printed(tmp_path, ret, state, en_row):
    """m3: `jwt_present` is token presence; what the caller-plane read DID is a separate
    fact, and the used list prints it in plain words."""
    with patch.object(gw, "_user_plane_get", return_value=ret):
        corpus = gw._build_research_corpus(_make_research_root(tmp_path), user_jwt="hdr.pl.sig")
    assert corpus["jwt_present"] is True and corpus["user_read"] == state
    out = gw._format_used_list(corpus)
    assert en_row in out, out
    rows = [ln for ln in out.splitlines() if "Your theses" in ln]
    assert len([r for r in rows if "—" in r]) == (0 if state == "ok" else 1), out
    assert "hdr.pl.sig" not in json.dumps(corpus) + out


def test_r2_corpus3_no_jwt_is_absent_and_reads_nothing(tmp_path):
    with patch.object(gw, "_user_plane_get", return_value=None) as m:
        corpus = gw._build_research_corpus(_make_research_root(tmp_path), user_jwt="")
    assert corpus["user_read"] == "absent" and m.call_count == 0
    assert "Your theses" not in gw._format_used_list(corpus)


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
@pytest.mark.parametrize("unavailable, needle", [
    (True, "could not be read this turn"), (False, "none readable this turn"),
], ids=["unavailable", "empty"])
def test_r2_signed_in_caller_sees_the_read_outcome(tmp_path, stream, unavailable, needle):
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX, user_jwt="header.payload.sig-SECRET",
                  user_plane_unavailable=unavailable, user_rows=None)
    assert needle in turn.reply, turn.reply
    assert JWT_ABSENT_EN not in turn.reply
    assert "SECRET" not in turn.blob()


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_r2_refused_grounded_turn_performs_no_user_plane_read(tmp_path, stream):
    """m4: the corpus (and its caller-plane reads) is built AFTER the eligibility/quota/
    prescreen gates — a turn refused at the pro gate does no user-plane I/O."""
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX, user_jwt="header.payload.sig",
                  tier="free")
    assert turn.spies["user_plane"].call_count == 0
    assert not turn.calls, "the model was called on a refused turn"
    if stream:
        assert any(e.get("type") == "done" for e in turn.events), turn.events
    else:
        assert turn.result.get("quota_exhausted") is True, turn.result


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_r2_allowed_grounded_turn_reads_both_caller_tables_once(tmp_path, stream):
    turn = _drive(tmp_path, stream=stream, context=GROUNDED_CTX, user_jwt="header.payload.sig")
    paths = [c.args[0] for c in turn.spies["user_plane"].call_args_list]
    assert len(paths) == 2 and paths[0].startswith("theses?") and paths[1].startswith("thesis_versions?"), paths


def test_r2_predicate_rejects_panel_and_page_variants():
    """m6: the predicate is exact — the compiler does not normalise case or whitespace, and
    a typed dashboard / cased-analysis route is an ordinary turn."""
    from engine.intelligence_workspace import context_compiler as cc
    assert gw._f11_grounded("research", cc.compile_envelope("q", GROUNDED_CTX)) is True
    for page, panel in [("analysis", "Theses"), ("analysis", " theses"), ("analysis", "theses "),
                        ("Analysis", "theses"), ("dashboard", "theses"), ("analysis", None),
                        ("analysis", ""), ("terminal", "theses")]:
        env = cc.compile_envelope("q", _typed_context(page=page, panel=panel))
        assert gw._f11_grounded("research", env) is False, (page, panel, env.get("ambient_widget_context"))


@pytest.mark.parametrize("stream", [False, True], ids=["chat", "chat_stream"])
def test_r2_global_research_turn_still_sees_client_history(tmp_path, stream):
    """m6: the inverse of the grounded history assertion — off F11 the client's prior USER
    turn reaches the loop and the model exactly as before (the grounded turn hands the
    loop `[]`, see test_research_mode_does_not_consult_client_history)."""
    spy: list = []
    history = [{"role": "user", "content": "Earlier question about breadth."},
               {"role": "assistant", "content": "Unpublished general-knowledge claim."}]
    turn = _drive(tmp_path, stream=stream, context=COMPANY_CTX, history=history, loop_spy=spy)
    _assert_global_deep_research(turn)
    assert spy, "the loop was never called"
    loop_history = spy[0][0][2]
    assert any("Earlier question about breadth" in json.dumps(m, ensure_ascii=False)
               for m in loop_history), loop_history
    assert any("Earlier question about breadth" in json.dumps(kw.get("messages"), ensure_ascii=False)
               for kw in turn.calls), "history did not reach the model"
    grounded_spy: list = []
    _drive(tmp_path, stream=stream, context=GROUNDED_CTX, history=history, loop_spy=grounded_spy)
    assert grounded_spy and grounded_spy[0][0][2] == []


class _ChunkedStreamCtx(_TextStreamCtx):
    """Streams the answer in small SDK-like chunks so the gate's flush policy engages."""

    @property
    def text_stream(self):
        t = self._text
        for i in range(0, len(t), 7):
            yield t[i:i + 7]


class _ChunkedClient(_CapClient):
    def stream(self, **kw):
        self._snap(kw)
        return _ChunkedStreamCtx(self.answer)


LONG_CITING_ANSWER = (
    "The daily briefing says the US session was mixed and breadth was thin. "
    + " ".join(f"The briefing also notes that sector {i} closed near where it opened." for i in range(40))
)


def test_r2_grounded_stream_puts_nothing_on_the_wire_before_the_final_authority(tmp_path):
    """Review GAP: a grounded answer is judged whole, so nothing streams ahead of
    _research_postprocess — one delta, no retract, and the delta IS the final reply."""
    turn = _drive(tmp_path, stream=True, context=GROUNDED_CTX, answer=LONG_CITING_ANSWER,
                  client=_ChunkedClient(LONG_CITING_ANSWER))
    deltas = [e for e in turn.events if e.get("type") == "delta"]
    retracts = [e for e in turn.events if e.get("type") == "retract"]
    assert len(deltas) == 1 and not retracts, (len(deltas), len(retracts))
    assert deltas[0]["text"] == turn.reply
    assert USED_EN in turn.reply and CEILING_EN in turn.reply
    assert turn.reply.startswith("The daily briefing says"), turn.reply
    assert turn.reply.count("sector 39") == 1


def test_r2_global_research_stream_still_streams_incrementally(tmp_path):
    """The hold-all is gated on the F11 predicate: the same chunked client off F11 streams
    more than one delta (Contract S unchanged for Deep Research)."""
    turn = _drive(tmp_path, stream=True, context=COMPANY_CTX, answer=LONG_CITING_ANSWER,
                  client=_ChunkedClient(LONG_CITING_ANSWER))
    deltas = [e for e in turn.events if e.get("type") == "delta"]
    assert len(deltas) >= 2, len(deltas)
    assert turn.reply.startswith("The daily briefing says"), turn.reply


@pytest.mark.parametrize("stream", [False, True], ids=["loop", "loop_stream"])
def test_r2_image_gate_note_is_off_on_a_grounded_turn(tmp_path, stream):
    """A grounded turn drops every attachment by design; the Pro-capability note would
    misstate why, and the grounded directive owns the system prompt. chat() rebuilds the
    server block from server-side facts, so the loops are driven directly here."""
    root = _make_research_root(tmp_path)
    ctx = {gw._SERVER_CONTEXT_KEY: {"image_gated": True}}
    corpus = gw._build_research_corpus(root, user_jwt="")
    seen = {}
    for grounded in (True, False):
        client = _CapClient("The daily briefing says the US session was mixed and breadth was thin.")
        kw = dict(mode="research", f11_grounded=grounded,
                  source_prompt=gw._format_research_grounding(corpus) if grounded else "")
        if stream:
            kw["research_corpus"] = corpus if grounded else None
            list(gw._run_brain_loop_stream("How did the US session look?", "pro", [], ctx, root, tmp_path,
                                           "http://127.0.0.1:3100", client, "claude-test", 500, 1,
                                           {}, [], [], [], **kw))
        else:
            gw._run_brain_loop("How did the US session look?", "pro", [], ctx, root, tmp_path,
                               "http://127.0.0.1:3100", client, "claude-test", 500, 1, **kw)
        assert client.calls, grounded
        seen[grounded] = "image reading is a Pro" in _system_text(client.calls[0])
    assert seen == {True: False, False: True}, seen


# ---------------------------------------------------------------------------
# 9. r3 repairs — Opus RO review of head a3a6772b (N1 B, N2 M, N3–N5 m)
# ---------------------------------------------------------------------------

UNCITED_NEXT_ANSWER = (
    ("Nvidia will rise 30% next quarter on AI demand; this is general knowledge, "
     "not from any artifact. " * 3) + "\n[NEXT]\nWhat else?\n"
)


@pytest.mark.parametrize("answer, cited", [
    (UNCITED_NEXT_ANSWER, False),
    (LONG_CITING_ANSWER + "\n[NEXT]\nWhat else?\n", True),
], ids=["uncited", "cited"])
def test_r3_grounded_stream_hold_survives_the_next_marker(tmp_path, answer, cited):
    """N1 (B): the [NEXT] seal used to release everything before the marker as a delta,
    so an uncited grounded answer streamed its general-knowledge prose and the null form
    arrived as a retract. Under hold-all the seal releases nothing: one delta, no retract,
    and the delta IS the postprocessed reply."""
    turn = _drive(tmp_path, stream=True, context=GROUNDED_CTX, answer=answer,
                  client=_ChunkedClient(answer))
    deltas = [e for e in turn.events if e.get("type") == "delta"]
    retracts = [e for e in turn.events if e.get("type") == "retract"]
    assert len(deltas) == 1 and not retracts, (len(deltas), len(retracts))
    assert deltas[0]["text"] == turn.reply
    assert "[NEXT]" not in turn.reply and "What else?" not in turn.reply, turn.reply
    if cited:
        assert turn.reply.startswith("The daily briefing says"), turn.reply
        assert turn.reply.count("sector 39") == 1
    else:
        assert turn.reply.startswith(NULL_EN), turn.reply
        assert "Nvidia" not in turn.reply and "30%" not in turn.reply, turn.reply
    assert turn.reply.count(USED_EN) == 1 and turn.reply.count(CEILING_EN) == 1, turn.reply


def test_r3_stream_display_cut_hold_all_keeps_prose_behind_the_seal():
    """Unit pin for N1: the marker branch honours hold-all (cut 0, sealed) while a global
    turn keeps its cut at the marker (the prose before [NEXT] streams)."""
    body = "prose\n[NEXT]\nq"
    assert gw._stream_display_cut(body, gw._GROUNDED_STREAM_HOLD_ALL) == (0, True)
    assert gw._stream_display_cut(body, 256) == (5, True)


N2_EVASIONS = {
    "long_head": ("Oil is up on general knowledge.\n\nSources consulted this turn:\n"
                  "- Live market state packet (as of 2026-09-12)\n- Invented Desk Note"),
    "no_markers": ("Oil is up on general knowledge.\n\nWhat this read used:\n"
                   "Live market state packet\nInvented Desk Note"),
    "mid_line": ("Oil is up on general knowledge. What this read used: Live market state packet, "
                 "Daily briefing.\nSummary done."),
    "html": ("Oil is up on general knowledge.<br><b>Sources</b><ul><li>Live market state packet</li>"
             "<li>Invented Desk Note</li></ul>"),
    "alt_head_plus": ("Oil is up on general knowledge.\n\nArtifacts used (this turn):\n"
                      "+ Live market state packet\n+ Invented Desk Note"),
    "bare": "Oil is up on general knowledge.\nLive market state packet\nDaily briefing",
    "refs_inline": "Oil is up on general knowledge.\nReferences: Live market state packet and Daily briefing",
    "head_inline_mixed": ("Oil is up on general knowledge.\nWhat this read used: Live market state packet, "
                          "Invented Desk Note."),
}


def _real_corpus(tmp_path) -> dict:
    corpus = gw._build_research_corpus(_make_research_root(tmp_path), user_jwt="")
    assert any(a.get("plain_en") == "Live market state packet" for a in corpus["artifacts"]), corpus
    return corpus


@pytest.mark.parametrize("key", sorted(N2_EVASIONS), ids=sorted(N2_EVASIONS))
def test_r3_model_source_list_is_recognised_by_content_not_format(tmp_path, key):
    """N2 (M): r2 stripped one exact heading + marker lines, so any other spelling of a
    model-written source list named a real artifact and bought a citation. The strip now
    recognises the list by content — every evasion is the null form, the invented source
    never ships, and the used list that ships is the server's (exactly one)."""
    corpus = _real_corpus(tmp_path)
    body, _ = gw._research_postprocess(N2_EVASIONS[key], corpus)
    assert body.startswith(NULL_EN), body
    assert "Invented Desk Note" not in body and "general knowledge" not in body, body
    assert body.count(USED_EN) == 1 and body.count(CEILING_EN) == 1, body


@pytest.mark.parametrize("answer", [
    "The live market state packet shows breadth was thin.",
    "What this read used was the daily briefing, which says breadth was thin.",
    "Sources: the live market state packet says breadth was thin today.",
], ids=["prose-name", "prose-heading-phrase", "prose-after-colon"])
def test_r3_prose_mention_of_an_artifact_is_still_a_citation(tmp_path, answer):
    """Residual by design: a prose sentence that NAMES an artifact is a citation — the
    closed corpus bounds knowledge; the check is a heuristic on the prose."""
    body, _ = gw._research_postprocess(answer, _real_corpus(tmp_path))
    assert body.startswith(answer), body
    assert body.count("\n" + USED_EN + "\n") == 1, body      # the server's heading, once


@pytest.mark.parametrize("raw, expected", [
    ("Breadth was thin.\n\nWhat this read used\n- Daily briefing (as of 2026-09-12)\nSo, energy led.\nEnd.",
     "Breadth was thin.\n\nSo, energy led.\nEnd."),
    ("Key reads:\nWhat this read used\n- x\nThe briefing (as of 2026-10-01) flagged energy.\nEnd.",
     "Key reads:\nThe briefing (as of 2026-10-01) flagged energy.\nEnd."),
    ("Breadth was thin (as of 2026-09-12). Energy led.", "Breadth was thin (as of 2026-09-12). Energy led."),
], ids=["short-sentence-under-heading-kept", "asof-inside-prose-kept", "asof-mid-sentence-kept"])
def test_r3_strip_never_deletes_punctuated_prose(raw, expected):
    """N3 (m): under a heading, only UNPUNCTUATED short lines are items; a sentence that
    happens to be short, or to carry "(as of …)" inside it, is prose and stays."""
    assert gw._research_strip_model_trailer(raw) == expected


@pytest.mark.parametrize("raw", [
    "Breadth was mixed.\n・Buy NVDA.",
    "Breadth was mixed.\n１．Buy NVDA.",
    "Breadth was mixed.\n(a) Buy NVDA.",
    "Breadth was mixed.\n-Buy NVDA.",
    "Breadth was mixed.\n一、Buy NVDA.",
    "Breadth was mixed. Our view: buy NVDA.",
], ids=["katakana-dot", "fullwidth-number", "paren-letter", "no-space-dash", "zh-numeral", "colon"])
def test_r3_trade_imperative_behind_other_markers_is_withheld(raw):
    """N4 (m): the r2 marker vocabulary missed fullwidth/CJK markers, "(a)", a dash with
    no space, and an imperative introduced by a colon."""
    body, withheld = gw._research_forbidden_filter(raw)
    assert withheld is True, raw
    assert body == "Breadth was mixed.", body


@pytest.mark.parametrize("raw, expected, withheld", [
    ("广度分化。买入英伟达。", "广度分化。", True),
    ("广度分化。请卖出特斯拉。", "广度分化。", True),
    ("广度分化。卖出压力增加。", "广度分化。卖出压力增加。", False),
    ("广度分化。买入意愿减弱。", "广度分化。买入意愿减弱。", False),
    ("Breadth was mixed.\n-5% days were rare.", "Breadth was mixed.\n-5% days were rare.", False),
    ("Breadth was mixed. Buy-side flows were thin.", "Breadth was mixed. Buy-side flows were thin.", False),
    # a dash does not split a sentence: the imperative takes its whole sentence with it
    ("Breadth was mixed — buy NVDA.", "", True),
], ids=["zh-buy-no-space", "zh-polite-sell", "zh-sell-pressure-kept", "zh-buy-intent-kept",
        "negative-number-kept", "buy-side-kept", "em-dash-whole-sentence"])
def test_r3_trade_battery_zh_imperative_and_guarded_compounds(raw, expected, withheld):
    body, flag = gw._research_forbidden_filter(raw)
    assert (body, flag) == (expected, withheld), (body, flag)


def test_r3_partial_caller_read_is_printed_not_implied(tmp_path):
    """N5 (m): one caller table unreadable while the other returned rows was reported as
    "ok". It is a PARTIAL read, and the used list says so in plain words."""
    versions = [{"id": "v1", "thesis_id": "t1", "version": 1,
                 "content": {"title": "Energy leads"}, "system_recorded_at": "2026-09-12T00:00:00Z"}]

    def _plane(path, user_jwt, timeout=5):
        return None if path.startswith("theses?") else versions

    with patch.object(gw, "_user_plane_get", side_effect=_plane) as m:
        corpus = gw._build_research_corpus(_make_research_root(tmp_path), user_jwt="hdr.pl.sig")
    assert m.call_count == 2
    assert corpus["jwt_present"] is True and corpus["user_read"] == "partial", corpus["user_read"]
    assert any(a.get("plain_en") == "Your thesis versions" for a in corpus["artifacts"]), corpus
    out = gw._format_used_list(corpus)
    assert "- Your theses — only partly readable this turn (one source could not be read)" in out, out
    assert "- 您的论点 — 本轮仅部分可读取（有一个来源无法读取）" in out, out
    assert "hdr.pl.sig" not in json.dumps(corpus) + out
    assert gw._format_used_list({"artifacts": [], "jwt_present": True, "user_read": "ok"}).count("partly") == 0


# ---------------------------------------------------------------------------
# 10. r4 repairs — Opus RO review of head 348ff595 (N2 M still open; N6–N8 M; N9–N11 m)
# ---------------------------------------------------------------------------
# r3 recognised a model-written source list by format (one heading vocabulary, list
# markers, "(as of …)" tails) and so (N2) still bought a citation from "Based on: …",
# footnotes, tables, articles and dates; (N6) never closed the block, deleting every
# section after a heading; (N7) deleted a long prose line for ending in "(as of …)";
# (N8) read "<name> — <claim>" as an item; (N9) missed markdown markers before an
# imperative; (N10) withheld reportative "buy programs" / "买入订单"; (N11) left orphan
# headings and fences. r4 is a line classifier: items by content, block closed by the
# first line that reads as prose, server-note-only dash forms, markdown-aware markers.

R4_CORPUS = {"artifacts": [
    {"plain_en": "Desk read", "plain_zh": "研究台读数"},
    {"plain_en": "Daily briefing", "plain_zh": "每日简报"},
    {"plain_en": "Asia close", "plain_zh": "亚洲收盘"},
]}
R4_PROSE = "The Fed usually cuts when unemployment rises above 5%; long bonds then rally."

R4_N2_TAILS = {
    "based-on": "\n\nBased on: Desk read, Daily briefing",
    "table": "\n\n| Source | As of |\n|---|---|\n| Desk read | 2026-10-02 |",
    "footnote-def": "\n\n[^1]: Desk read",
    "article": "\n\n- the Desk read\n- the Daily briefing",
    "zh-basis": "\n\n依据：研究台读数、每日简报",
    "date-tail": "\n\n- Desk read, 2 Oct 2026",
    "per": "\nPer: Desk read",
    "see": "\nSee: Desk read.",
    "equals": "\nSource = Desk read",
    "bracket-number": "\n[1] Desk read",
    "bare-known-name": "\n\nAsia close",
    "server-note-impersonated": "\n\nDaily briefing — not published yet",
    "user-row-impersonated": "\n\nYour theses — none readable this turn",
    "quoted-heading": "\n\n> Sources: Desk read",
    "bold-heading-inline": "\n\n**Sources:** Desk read, Daily briefing",
    "emphasised-names": "\n\nSources: *Desk read*; *Daily briefing*",
    "zh-numbered-invented": "\n\n资料来源：\n1. 研究台读数\n2. 彭博终端",
    "table-under-heading": "\n\nSources:\n| Name | Date |\n|---|---|\n| Invented Desk Note | 2026-10-02 |",
    "fenced-blank-padded": "\n\n```text\n\nSources:\n- Desk read\n\n```",
}


@pytest.mark.parametrize("key", sorted(R4_N2_TAILS), ids=sorted(R4_N2_TAILS))
def test_r4_source_list_tail_is_stripped_whole_and_never_cites(tmp_path, key):
    """N2 (M, still open after r3): every one of the reviewer's surviving tails, plus the
    forms r4 adds (articles, dates, tables, footnotes, "Per:"/"See:"/"=", impersonated
    server rows, quoted/bold headings, fenced lists) strips to the prose alone, and the
    grounded reply is the null form with exactly one server-written used list."""
    assert gw._research_strip_model_trailer(R4_PROSE + R4_N2_TAILS[key], R4_CORPUS) == R4_PROSE
    corpus = _real_corpus(tmp_path)
    body, _ = gw._research_postprocess(R4_PROSE + R4_N2_TAILS[key], corpus)
    assert body.startswith(NULL_EN), body
    assert "彭博终端" not in body and "Invented" not in body, body
    assert body.count("\n" + USED_EN + "\n") == 1 and body.count(CEILING_EN) == 1, body


@pytest.mark.parametrize("raw, expected", [
    ("The Desk read says breadth is thin.\n\nSources:\n- Desk read\n\nWhat to watch:\n"
     "- Breadth needs to widen before the move is trustworthy.\n- The curve needs to stop flattening.",
     "The Desk read says breadth is thin.\n\nWhat to watch:\n"
     "- Breadth needs to widen before the move is trustworthy.\n- The curve needs to stop flattening."),
    ("The Desk read says breadth is thin.\n\nSources: Desk read\nBottom line: watch, don't chase",
     "The Desk read says breadth is thin.\n\nBottom line: watch, don't chase"),
    ("研究台读数显示宽度偏弱。\n\n来源：\n- 研究台读数\n\n结论：宽度偏弱，暂不追高",
     "研究台读数显示宽度偏弱。\n\n结论：宽度偏弱，暂不追高"),
    ("参考\n研究台读数提到宽度偏弱\n这意味着领涨面很窄", "研究台读数提到宽度偏弱\n这意味着领涨面很窄"),
    ("## Sources\nDesk read\n\n## Read\nBreadth is thin\nLeaders are narrow\nThe Desk read flags it.",
     "## Read\nBreadth is thin\nLeaders are narrow\nThe Desk read flags it."),
    ("Sources:\n- Desk read\n\nEnergy led the tape higher.", "Energy led the tape higher."),
    ("Sources:\n- Desk read\n\n| Date | Close |\n|---|---|\n| 2026-10-02 | 100 |",
     "| Date | Close |\n|---|---|\n| 2026-10-02 | 100 |"),
    ("Sources:\n- Desk read\n\n```\nprint('x')\n```", "```\nprint('x')\n```"),
], ids=["what-to-watch", "bottom-line", "zh-conclusion", "zh-bare-heading", "md-sections",
        "prose-after-blank", "data-table-after-list", "code-after-list"])
def test_r4_source_block_closes_at_the_first_prose_line(raw, expected):
    """N6 (M): r3's block closed only on a blank line that was followed by nothing it
    recognised, so a heading with a list deleted every later section. The block now
    ends at the first line that reads as prose — sentence punctuation, a clause break,
    a verb, a "Something:" heading, a markdown heading, a data table, a code block."""
    assert gw._research_strip_model_trailer(raw, R4_CORPUS) == expected


@pytest.mark.parametrize("raw, expected", [
    ("Sources: Desk read\nBreadth narrowed for a third day while leaders kept rising, "
     "which matters for the print (as of 2 Oct)",
     "Breadth narrowed for a third day while leaders kept rising, which matters for the print (as of 2 Oct)"),
    ("Breadth was thin (as of 2026-09-12). Energy led.", "Breadth was thin (as of 2026-09-12). Energy led."),
    ("Breadth was thin.\n\nWhat this read used\n- Daily briefing (as of 2026-09-12)\nSo, energy led.\nEnd.",
     "Breadth was thin.\n\nSo, energy led.\nEnd."),
], ids=["long-prose-asof-tail-in-block", "asof-inside-prose", "prose-after-item"])
def test_r4_asof_tail_never_deletes_a_prose_line(raw, expected):
    """N7 (M): r3 dropped ANY in-block line ending in "(as of …)". A tail is only an
    item's decoration when the rest of the line is a source name."""
    assert gw._research_strip_model_trailer(raw, R4_CORPUS) == expected


@pytest.mark.parametrize("raw, expected", [
    ("- Desk read — breadth is thin and leaders narrow", "- Desk read — breadth is thin and leaders narrow"),
    ("Sources:\n- Desk read — breadth is thin and leaders narrow", "- Desk read — breadth is thin and leaders narrow"),
    ("The Desk read — not published yet, so I used the packet.",
     "The Desk read — not published yet, so I used the packet."),
    ("x.\n- Desk read — not available this turn", "x."),
    ("x.\n- Daily briefing — not published yet", "x."),
    ("x.\n- Your theses — could not be read this turn", "x."),
    ("x.\n- 您的论点 — 本轮仅部分可读取（有一个来源无法读取）", "x."),
], ids=["claim-kept", "claim-under-heading-kept", "note-then-prose-kept",
        "server-note-packet", "server-note-briefing", "server-note-theses", "server-note-zh"])
def test_r4_name_dash_claim_is_prose_and_only_server_notes_are_items(raw, expected):
    """N8 (M): r3 cut everything after a dash before comparing, so "Desk read — breadth
    is thin" was an item. Only the server's own "— note" forms are items; a dash
    followed by a claim is a grounded sentence."""
    assert gw._research_strip_model_trailer(raw, R4_CORPUS) == expected


@pytest.mark.parametrize("tail", [
    "### Buy NVDA", "> Buy NVDA", "**Buy** NVDA", "a) Buy NVDA", "→ Buy NVDA", "1.Buy NVDA",
    "[1] Buy NVDA", "`Buy NVDA`", "- [ ] Buy NVDA", "A. Buy NVDA", "- [x] Sell TSLA", "_Buy NVDA_",
], ids=["h3", "blockquote", "bold", "paren-letter", "arrow", "number-no-space", "bracket-number",
        "code", "checkbox", "letter-dot", "checked-box", "underscore"])
def test_r4_trade_imperative_behind_markdown_markers_is_withheld_cleanly(tail):
    """N9 (m): markdown headings, quotes, emphasis, code, checkboxes, footnote numbers,
    arrows and "1.Buy" hid the imperative from the marker strip, and "A. Buy" left a
    dangling "A.". Every shape is withheld and the prose before it is untouched."""
    body, withheld = gw._research_forbidden_filter("Breadth was thin per the Desk read.\n\n" + tail)
    assert withheld is True, tail
    assert body == "Breadth was thin per the Desk read.", body


@pytest.mark.parametrize("sentence", [
    "Flows: buy programs dominated per the Desk read.",
    "Funds were net sellers: sell volumes rose per the Desk read.",
    "Dealers: buy interest faded into the close.",
    "研究台读数显示，买入订单增加。",
    "研究台读数显示，卖出订单减少。",
    "研究台读数显示，买入资金回流。",
    "研究台读数显示，卖出潮放缓。",
    "研究台读数显示，买入规模扩大。",
    "Call context_search on the repo.",
    "snake_case sell_side flows rose.",
], ids=["buy-programs", "sell-volumes", "buy-interest", "zh-buy-orders", "zh-sell-orders",
        "zh-buy-funds", "zh-sell-wave", "zh-buy-scale", "identifier-still-caught", "identifier-not-a-trade"])
def test_r4_reportative_buy_sell_noun_phrases_are_judged_right(sentence):
    """N10 (m): a sentence-anchored buy/sell heading a noun phrase ("buy programs
    dominated", "买入订单增加") is reportative, not an imperative. The emphasis strip
    that serves N9 removes wrappers at token edges only — an underscore inside an
    identifier (context_search) still names the tool and is still withheld."""
    expected = sentence == "Call context_search on the repo."
    assert gw._research_sentence_forbidden(sentence) is expected, sentence


@pytest.mark.parametrize("sentence", [
    "Our view: buy NVDA.", "广度分化。买入英伟达。", "广度分化。请卖出特斯拉。",
    "Breadth was mixed — buy NVDA.", "Buy NVDA now.", "You should sell TSLA.", "*Our view:* buy NVDA.",
])
def test_r4_imperatives_are_still_withheld_after_the_noun_guards(sentence):
    assert gw._research_sentence_forbidden(sentence) is True, sentence


@pytest.mark.parametrize("raw, expected", [
    ("x.\n\nData used:\n- Desk read", "x."),
    ("x.\n\nInputs:\n- Desk read", "x."),
    ("x.\n\nCited:\n- Desk read", "x."),
    ("x.\n\n```\nSources:\n- Desk read\n```", "x."),
    ("x.\n\n```\nSources:\n- Desk read\nBreadth is thin.\n```\nMore.", "x.\n\nBreadth is thin.\nMore."),
    ("```python\nprint(1)\n```\nSources:\n- Desk read", "```python\nprint(1)\n```"),
], ids=["data-used", "inputs", "cited", "fenced-list", "fenced-list-then-prose", "code-block-before-list"])
def test_r4_orphan_headings_and_fences_go_with_the_list(raw, expected):
    """N11 (m): r3 left "Data used:" / "Inputs:" / "Cited:" and a bare ``` behind the
    list it had removed. The heading vocabulary covers them, and a fence that only
    wrapped a dropped list is dropped with it — a real code block is untouched."""
    assert gw._research_strip_model_trailer(raw, R4_CORPUS) == expected


@pytest.mark.parametrize("raw, expected", [
    ("What this read used was the daily briefing, which says breadth was thin.",
     "What this read used was the daily briefing, which says breadth was thin."),
    ("Sources: the Desk read shows breadth is thin today.", "Sources: the Desk read shows breadth is thin today."),
    ("Based on the Desk read, breadth is thin.", "Based on the Desk read, breadth is thin."),
    ("Per the Desk read, breadth is thin.", "Per the Desk read, breadth is thin."),
    ("Seen from the Desk read, breadth is thin.", "Seen from the Desk read, breadth is thin."),
    ("Perhaps the Desk read is right.", "Perhaps the Desk read is right."),
    ("Inputs were mixed: breadth narrowed, leaders rose.", "Inputs were mixed: breadth narrowed, leaders rose."),
    ("| Date | Close |\n|---|---|\n| 2026-10-02 | 100 |", "| Date | Close |\n|---|---|\n| 2026-10-02 | 100 |"),
    (" What this read used: Desk read, Daily briefing.\nSummary done.", "Summary done."),
], ids=["heading-phrase-as-prose", "sources-colon-prose", "based-on-prose", "per-prose", "seen-prefix",
        "perhaps-prefix", "inputs-prefix", "data-table", "inline-list-then-prose"])
def test_r4_heading_vocabulary_does_not_eat_prose_that_starts_with_it(raw, expected):
    """The widened heading vocabulary ("Based on", "Per", "See", "Inputs", "Cited") binds
    only as a heading — alone on its line, or followed by ":"/"=" and a list of names.
    A sentence that happens to start with one of those words is prose."""
    assert gw._research_strip_model_trailer(raw, R4_CORPUS) == expected


# ---------------------------------------------------------------------------
# §11 — r5: review of r4 (a6f70e06). r4 closed N2/N6–N11 on their inputs but (N12) kept a
# source line that named only invented sources ("Sources: Bloomberg, Reuters"); (N13)
# missed heading words ("Data sources", "This read used", "Evidence"), dates without a
# year or with a comma ("(Oct 2, 2026)") and "&"/"/"/"+" separators; (N14, regression)
# no longer recognised "【来源】研究台读数"; (N15) deleted a section whose title has no
# colon ("Risks", "**Key levels**") after a source block; (N16, regression) excused real
# orders behind the new noun guards ("Buy interest-rate futures", "请买入动能强的股票");
# (N17) left "- Sources" orphans and let "¹ Desk read", "Sources — Desk read", "(p. 2)",
# "[1]", "- Desk read: breadth section" cite; (N18) let a bare "See also" line delete the
# prose after it. Inputs below are the reviewer's, verbatim.
# ---------------------------------------------------------------------------

R5_CORPUS = {"artifacts": [
    {"plain_en": "Desk read", "plain_zh": "研究台读数"},
    {"plain_en": "Daily briefing", "plain_zh": "每日简报"},
]}
R5_PROSE = "The Desk read says breadth is thin."


@pytest.mark.parametrize("tail", [
    "\n\nSources: Bloomberg, Reuters", "\n\n来源：彭博、路透社", "\n\nSource: Bloomberg terminal",
    "\n\nReferences: FactSet", "\n\nSources: Bloomberg.", "\n\n| Source |\n|---|\n| Bloomberg |",
    "\n\nSource: Desk read.\nSource: Bloomberg.",
], ids=["two-invented", "zh-invented", "one-invented", "references-invented", "invented-dot",
        "table-invented", "known-then-invented"])
def test_r5_a_source_line_naming_only_invented_sources_is_stripped(tail):
    """N12 (M): under a STRONG heading ("Sources", "来源", "References") the inline list
    needs no known name — every piece name-like is enough. The block form already went;
    the inline and table forms now go with it."""
    assert gw._research_strip_model_trailer(R5_PROSE + tail, R5_CORPUS) == R5_PROSE


@pytest.mark.parametrize("tail", [
    "\n\nData sources: Desk read", "\n\nThis read used: Desk read", "\n\nWhat I used: Desk read",
    "\n\nSources used in this read: Desk read", "\n\nEvidence: Desk read, Daily briefing",
    "\n\nGrounding: Desk read", "\n\nSources: Desk read (Oct 2, 2026)", "\n\nSources: Desk read (updated 2 Oct)",
    "\n\n- Desk read, 2 Oct", "\n\nSources: Desk read & Daily briefing", "\n\nSources: Desk read / Daily briefing",
    "\n\nSources: Desk read + Daily briefing",
    "\n\n¹ Desk read", "\n\n<sup>1</sup> Desk read", "\n\nSources — Desk read", "\n\nSources - Desk read",
    "\n\nSource: Desk read (p. 2)", "\n\nSources: Desk read [1], Daily briefing [2]", "\n\n**Desk read** (2 Oct)",
    "\n\nSources:\n- Desk read: breadth section",
], ids=["data-sources", "this-read-used", "what-i-used", "sources-used-in-this-read", "evidence", "grounding",
        "paren-date-with-comma", "paren-updated", "date-no-year", "ampersand", "slash", "plus",
        "superscript", "sup-tag", "em-dash-heading", "hyphen-heading", "page-ref", "bracket-refs",
        "bold-name-date", "item-with-section"])
def test_r5_more_heading_shapes_dates_and_separators_never_cite(tail):
    """N13 + N17 (M/m): every one of the reviewer's surviving shapes strips to the prose
    alone and no longer buys a citation."""
    out = gw._research_strip_model_trailer("G." + tail, R5_CORPUS)
    assert out == "G.", out
    assert gw._research_cites_artifact(out, R5_CORPUS) is False


def test_r5_zh_bracket_heading_is_a_source_heading():
    """N14 (M, r4 regression): r4 bound an inline list only after ":"; "【来源】" binds
    with its closing bracket."""
    out = gw._research_strip_model_trailer("研究台读数显示宽度偏弱。\n\n【来源】研究台读数", R5_CORPUS)
    assert out == "研究台读数显示宽度偏弱。", out


@pytest.mark.parametrize("raw, expected", [
    ("The Desk read says breadth is thin.\n\nSources: Desk read\n\nKey points\n- Breadth thin\n- Leaders narrow",
     "The Desk read says breadth is thin.\n\nKey points\n- Breadth thin\n- Leaders narrow"),
    ("Sources: Desk read\n\nRisks\n- Oil shock\n- Credit spreads", "Risks\n- Oil shock\n- Credit spreads"),
    ("Sources: Desk read\n\nWatchlist\n- NVDA\n- TSLA", "Watchlist\n- NVDA\n- TSLA"),
    ("The Desk read says breadth is thin.\n\n参考：研究台读数\n\n要点\n- 宽度收窄\n- 龙头集中",
     "The Desk read says breadth is thin.\n\n要点\n- 宽度收窄\n- 龙头集中"),
    ("Sources: Desk read\n\n**Key levels**\n- SPX 5800\n- 10y 4.1%", "**Key levels**\n- SPX 5800\n- 10y 4.1%"),
], ids=["key-points", "risks", "watchlist", "zh-key-points", "bold-title"])
def test_r5_a_section_title_after_a_blank_line_closes_the_block(raw, expected):
    """N15 (M): a blank line inside a source block followed by an UNMARKED line that is
    not a heading, a table row or a known name ends the block — that line is the next
    section's title and its short bullets are its content, not invented sources."""
    assert gw._research_strip_model_trailer(raw, R5_CORPUS) == expected


@pytest.mark.parametrize("sentence", [
    "Buy interest-rate futures.", "Sell interest rate swaps.", "Buy demand-sensitive cyclicals.",
    "买入需求旺盛的板块。", "请买入动能强的股票。", "卖出情绪过热的题材股。",
    "Our view: buy signals are flashing, so buy NVDA.", "Buy programs now.", "Sell volume into the close.",
    "请卖出价格偏高的龙头。",
])
def test_r5_orders_behind_the_noun_guards_are_still_withheld(sentence):
    """N16 (M, r4 regression): a noun guard excuses buy/sell only when the noun stands
    alone and is followed by a clause end or a reporting verb; "请" is always an order;
    a ZH compound noun whose predicate is attributive ("旺盛的板块") names what to buy."""
    assert gw._research_sentence_forbidden(sentence) is True, sentence


@pytest.mark.parametrize("sentence", [
    "Buy interest is building in semis.", "Sell pressure mounted into the close.",
    "Buy programs dominated the tape.", "Sell volume was heavy in banks.", "买入需求旺盛。", "卖出压力明显。",
    "买入意愿较弱，但卖出压力也不大。", "Sell-side ratings turned cautious.", "Buy signals are flashing on the daily.",
    "Sell pressure.", "Buy interest remains thin.",
])
def test_r5_reportative_noun_phrases_stay_reportative(sentence):
    assert gw._research_sentence_forbidden(sentence) is False, sentence


def test_r5_nested_sources_heading_leaves_no_orphan():
    """N17 (m): "- Sources" is a heading under a bullet; its nested items go with it."""
    assert gw._research_strip_model_trailer("G.\n\n- Sources\n  - Desk read\n  - Bloomberg terminal", R5_CORPUS) == "G."


def test_r5_a_bare_weak_heading_word_is_prose():
    """N18 (m): "See also" / "Per" alone on a line is a sentence opener, not a heading;
    r4 opened a block and deleted the prose line after it."""
    raw = "Breadth is thin per the Desk read.\nSee also\nthe curve section"
    assert gw._research_strip_model_trailer(raw, R5_CORPUS) == raw


# ---------------------------------------------------------------------------
# §12 — r6: review N19–N26 of the r5 head (c407d928). Inputs are the reviewer's verbatim
# probes; every case below failed on the r5 bytes (RED-proved by swapping the gateway).
# ---------------------------------------------------------------------------

R6_CORPUS = R5_CORPUS


@pytest.mark.parametrize("sentence", [
    "Breadth is thin; buy the dip.", "Breadth is thin, buy the dip.", "Breadth is thin—buy the dip.",
    "(Buy NVDA.)", "Our stance (buy the dip) is unchanged.", "Buy: NVDA.", "Levels held. Sell: TSLA into strength.",
])
def test_r6_orders_behind_clause_joins_are_withheld(sentence):
    """N19 (M): r5 anchored buy/sell on a sentence start or so/and/then/but, so an order
    joined by ";" "," "—" or "(" and the label form "Buy: NVDA" passed as prose."""
    assert gw._research_sentence_forbidden(sentence) is True, sentence


@pytest.mark.parametrize("sentence", [
    "Buy interest waned.", "Sell pressure abated.", "Buy orders swelled.", "Buy volume totaled 2M shares.",
    "Sell volumes doubled.", "Buy demand softened.", "Sell orders piled up.", "Sell pressure intensified.",
    "Sell pressure clearly eased.", "Buy interest also rose.",
    "Analysts upgraded and buy ratings now outnumber sells.",
    "Breadth is thin per the Desk read. Buy interest waned into the close. Leaders narrowed.",
])
def test_r6_reportative_noun_phrases_need_no_verb_list(sentence):
    """N21 (M, r5 over-correction): the N16 fix excused a lone noun only before a LISTED
    verb, so "waned" / "abated" / "totaled" / "clearly eased" were withheld as orders.
    Any regular verb form, optionally behind one adverb, is a report."""
    assert gw._research_sentence_forbidden(sentence) is False, sentence


def test_r6_the_filter_keeps_a_reportative_middle_sentence():
    text = "Breadth is thin per the Desk read. Buy interest waned into the close. Leaders narrowed."
    assert gw._research_forbidden_filter(text) == (text, False)


@pytest.mark.parametrize("sentence", [
    "Buy programs now.", "Buy programs across sectors.", "Sell volume into the close.", "Buy orders this week.",
    "Buy programs daily.", "Our view: buy signals are flashing, so buy NVDA.",
])
def test_r6_n16_orders_behind_the_noun_guards_are_still_withheld(sentence):
    """The N16 controls: an adverb or a preposition after the lone noun is not a verb."""
    assert gw._research_sentence_forbidden(sentence) is True, sentence


@pytest.mark.parametrize("sentence", [
    "The desk does not say what to do (buy or sell) here.", "Buy or sell signals were mixed.",
    "Buy: 12 names, Sell: 3 names.", "Buy and sell programs were balanced.",
])
def test_r6_buy_or_sell_is_never_one_order(sentence):
    assert gw._research_sentence_forbidden(sentence) is False, sentence


@pytest.mark.parametrize("sentence", [
    "买入价100元以下的NVDA。", "买入需求旺盛的板块。", "请买入动能强的股票。", "买入资金面宽松受益股。",
    "所以买入NVDA。", "首先买入龙头。", "跌到位后再买入半导体。",
])
def test_r6_zh_orders_are_withheld(sentence):
    """N20 (M): "买入价100元以下的NVDA" is an order — r5's "价(?!格)" guard read every
    "买入价…" as a price report. ZH clause openers ("所以", "先", "再") anchor too."""
    assert gw._research_sentence_forbidden(sentence) is True, sentence


@pytest.mark.parametrize("sentence", [
    "买入价为100元。", "买入价格偏高。", "卖出价格偏低，", "卖出压力减轻。", "买入需求疲软。", "买入兴趣浓厚。",
    "买入力度加强。", "卖出压力骤增。", "买入意愿较弱的时候，市场容易回调。", "卖出压力较大的时候要小心。",
    "买入需求的变化值得关注。", "买入价位在100元附近。", "买入意愿较弱，但卖出压力也不大。",
])
def test_r6_zh_compound_nouns_are_reportative_unless_attributive(sentence):
    """N22 (M, r5 over-correction): a predicate list can never be complete ("减轻", "疲软",
    "浓厚" were withheld), and a "的" opening a clause ("较弱的时候") is not attributive."""
    assert gw._research_sentence_forbidden(sentence) is False, sentence


@pytest.mark.parametrize("raw", [
    "G.\n\nInputs: oil, wages, rents", "G.\n\nMaterials: copper, lithium, nickel",
    "G.\n\nMaterials\n- Copper miners lagged\n- Lithium weak", "G.\n\nRef: 5800 level",
    "G.\n\nArtifacts\n- NVDA\n- TSLA", "G.\n\nReferences: the 1994 bond rout, the 2022 hiking cycle",
    "Per the Desk read, the cost picture matters.\n\nInputs: oil, wages, rents\n\nOutlook: margins compress.",
    "Per the Desk read, sector breadth is mixed.\n\nEnergy\n- Oil rose on supply cuts\n\nMaterials\n"
    "- Copper miners lagged as China demand slowed.\n- Gold miners rallied.\n\nFinancials\n- Banks were steady.",
], ids=["inputs", "materials-inline", "materials-block", "ref", "artifacts", "references-the", "inputs-doc", "sectors-doc"])
def test_r6_generic_heading_words_keep_their_content(raw):
    """N23 (M): "Inputs", "Materials", "Ref", "Artifacts" are a sector, a cost list or a level
    unless qualified ("Inputs used"); and an invented reference must be shaped like a name
    ("the 1994 bond rout" is not one)."""
    assert gw._research_strip_model_trailer(raw, R6_CORPUS) == raw


@pytest.mark.parametrize("tail", [
    "\n\nInputs used: Desk read", "\n\nMaterials consulted: Desk read, Bloomberg", "\n\nArtifacts read: Desk read",
    "\n\nReferences: FactSet", "\n\nReferences: The 1994 Rout", "\n\nRefs: Desk read",
], ids=["inputs-used", "materials-consulted", "artifacts-read", "references-invented", "references-capitalised", "refs-known"])
def test_r6_qualified_heading_words_still_strip(tail):
    assert gw._research_strip_model_trailer("G." + tail, R6_CORPUS) == "G."


@pytest.mark.parametrize("raw, expected", [
    ("G.\n\nSources:\n\nDesk read, Bloomberg", "G."),
    ("G.\n\nSources:\n- Desk read\n\nDesk read, Bloomberg", "G."),
    ("G.\n\nReferences\n\nDesk read; FactSet", "G."),
    ("G.\n\nSources:\n\nDesk read (2 Oct), Bloomberg terminal", "G."),
    ("G.\n\nDesk read, Bloomberg", "G."),
    ("G.\n\nSources:\n\nBloomberg terminal", "G."),
    ("G.\n\nDesk read, breadth and leadership", "G.\n\nDesk read, breadth and leadership"),
    ("G.\n\nSources:\n- Desk read\n\nDesk read, breadth and leadership", "G.\n\nDesk read, breadth and leadership"),
], ids=["after-blank", "after-item-and-blank", "references-semicolon", "with-date", "no-heading",
        "bare-heading-blank-invented", "title-kept", "title-after-list-kept"])
def test_r6_a_list_naming_a_known_source_is_a_source_list(raw, expected):
    """N24 (M): "Desk read, Bloomberg" after a blank line is the source list the heading
    announced, not the next section; the r4 bare-name rule now covers a list with at
    least one known name. A bare heading, a blank and an invented name is still the list."""
    assert gw._research_strip_model_trailer(raw, R6_CORPUS) == expected


def test_r6_an_html_break_blank_is_not_a_section_gap():
    """N25 (M): r5 flagged the WHOLE text as "html" when any break tag appeared, so a
    "<br>" in paragraph one silenced the N15 gap rule and a later Risks list went with the
    source line. Only the blank the tag itself made is markup."""
    raw = "G.<br>\n\nSources: Desk read\n\nRisks\n- Oil shock\n- Credit spreads"
    out = gw._research_strip_model_trailer(raw, R6_CORPUS)
    assert out.startswith("G.") and out.endswith("Risks\n- Oil shock\n- Credit spreads"), out
    assert "Sources" not in out and "\x1e" not in out
    assert gw._research_strip_model_trailer(
        "G.\n\nSources:<ul><li>Desk read</li><li>Bloomberg terminal</li></ul>", R6_CORPUS) == "G."
    assert "\x1e" not in gw._research_strip_model_trailer("G.<br>Risks<br>- Oil shock", R6_CORPUS)


@pytest.mark.parametrize("raw, expected", [
    ("G.\n\nSources: Desk read\n\n- Oil shock", "G.\n\n- Oil shock"),
    ("G.\n\nSources: Desk read\n\n- Oil shock\n- Credit spreads widen", "G.\n\n- Oil shock\n- Credit spreads widen"),
    ("G.\n\nSources:\n- Desk read\n\n- Oil shock", "G."),   # r7 B2: a marked item after a marked item is one loose list
    ("G.\n\nSources:\n\n- Bloomberg terminal", "G."),
    ("G.\n\nSources:\n\n- Desk read\n- Bloomberg terminal", "G."),
    ("G.\n\nSources: Desk read\n\n- Desk read: breadth section", "G."),
], ids=["one-item", "two-items", "after-list", "bare-heading-blank-list", "bare-heading-blank-known-list", "known-item-after-blank"])
def test_r6_a_marked_line_after_a_blank_is_the_next_section(raw, expected):
    """N26 (M): r5's N15 rule kept only an UNMARKED line after a blank, so a bulleted
    section following the source line was deleted. A marked line that is not a known
    item is the next section — unless the heading was bare and nothing sat under it yet,
    in which case the blank is markdown's list separator and the list is the heading's.
    r7 (review #3 B2) narrows "marked line": a marked item after a MARKED item continues
    the list (markdown's loose list); the N26 shape is a bullet after an INLINE source line."""
    assert gw._research_strip_model_trailer(raw, R6_CORPUS) == expected


@pytest.mark.parametrize("sentence", [
    "Buy interest in semis is building.", "Sell pressure in tech was heavy.",
    "Supply rose and buy orders from Asia picked up.", "Tech fell but buy interest in semis held up.",
    "Buy demand for duration faded.", "Sell pressure at the open quickly eased.",
])
def test_r6_a_prepositional_phrase_before_the_verb_is_still_a_report(sentence):
    """r6.1 (the r5 residual the reviewer's N21 probes brushed against): "Buy interest in
    semis is building" has its verb three words on; the lone noun is still reportative."""
    assert gw._research_sentence_forbidden(sentence) is False, sentence


@pytest.mark.parametrize("sentence", [
    "Buy programs across sectors.", "Buy orders from Asia.", "Sell volume into the close.",
    "Buy interest in semis.", "Sell pressure at the open, hard.",
])
def test_r6_a_prepositional_phrase_without_a_verb_is_still_an_order(sentence):
    assert gw._research_sentence_forbidden(sentence) is True, sentence


# ---------------------------------------------------------------------------
# §13 r7 — review #3 (B1/B2 blocking regressions, M1–M4, m1, m2); inputs are the
# reviewer's own, verbatim. RED on r6.1 bytes, GREEN on r7.
R7_CORPUS = R6_CORPUS


@pytest.mark.parametrize("tail", [
    "Sources: Desk read, the WSJ", "Sources: 10-K filing, Desk read", "Sources: Desk read, 13F filings",
    "Sources: 2024 annual report, Desk read", "Sources: Desk read, the Fed statement",
    "Sources: the FT, Bloomberg", "Sources: 13F filings", "References: the WSJ, FactSet",
], ids=["the-wsj", "10k-first", "13f", "annual-report", "fed-statement", "ft-no-known", "13f-alone", "references"])
def test_r7_a_digit_or_determiner_led_invented_source_still_strips(tail):
    """B1 (REGRESSION): r6's name-shape rule (N23) let "the WSJ" / "10-K filing" fail the
    inline list, so the whole trailer survived and the known name inside it read as a
    citation for a body that cited nothing."""
    out = gw._research_strip_model_trailer("Breadth is thin.\n\n" + tail, R7_CORPUS)
    assert out == "Breadth is thin.", (tail, out)
    assert gw._research_cites_artifact(out, R7_CORPUS) is False


@pytest.mark.parametrize("raw", [
    "G.\n\nReferences: the 1994 bond rout, the 2022 hiking cycle", "G.\n\nRef: 5800 level",
    "G.\n\nInputs: oil, wages, rents", "G.\n\nSources: the Desk read shows breadth is thin.",
], ids=["episodes", "level", "inputs", "prose"])
def test_r7_data_and_prose_after_a_heading_word_still_stay(raw):
    assert gw._research_strip_model_trailer(raw, R7_CORPUS) == raw


@pytest.mark.parametrize("raw", [
    "G per the Desk read.\n\nSources:\n\n- Desk read\n\n- Bloomberg terminal",
    "G per the Desk read.\n\nSources:\n\n1. Desk read\n\n2. Reuters",
    "G per the Desk read.\n\nReferences:\n\n- Desk read (2 Oct)\n\n- FactSet estimates\n\n- Bloomberg terminal",
    "G per the Desk read.\n\nSources:\n- Desk read\n\n- Reuters",
    "G per the Desk read.\n\n来源：\n\n- 研究台读数\n\n- 彭博",
    "G per the Desk read.\n\nSources:\n- Desk read\n\n- Oil shock",
], ids=["loose-bullets", "loose-numbered", "loose-three", "tight-then-loose", "zh-loose", "after-list"])
def test_r7_a_loose_list_under_a_source_heading_is_one_list(raw):
    """B2 (REGRESSION): the N26 rule read every marked line after a blank as the next
    section, so a loose markdown list (a blank between items) leaked every item after the
    first. A marked item after a marked item continues the list; after an INLINE source
    line a bullet is still the next section (the N26 one-item shape)."""
    assert gw._research_strip_model_trailer(raw, R7_CORPUS) == "G per the Desk read."


@pytest.mark.parametrize("raw", [
    "G per the Desk read.\n\nSources: Desk read\n\n- Oil shock",
    "G per the Desk read.\n\nSources:\n- Desk read\n\nRisks\n- Oil shock",
    "G per the Desk read.\n\nSources:\n\n- Desk read\n\n- Breadth needs to widen before the move is trustworthy.",
], ids=["inline-then-bullet", "title-after-list", "prose-bullet"])
def test_r7_the_next_section_after_a_list_still_stays(raw):
    out = gw._research_strip_model_trailer(raw, R7_CORPUS)
    assert out.startswith("G per the Desk read.") and out.endswith(raw.split("\n")[-1]), out
    assert "Sources" not in out and "Desk read\n" not in out


@pytest.mark.parametrize("raw", [
    "X per the Desk read.\n\nThe Desk read, Bloomberg and Reuters all flagged it.",
    "X per the Desk read.\n\nDesk read, Bloomberg and Reuters all flagged it.",
    "X per the Desk read.\n\nDesk read, FactSet and Reuters agree on this.",
    "X per the Desk read.\n\nDesk read, Daily briefing and FOMC minutes agree.",
], ids=["the-lead", "bare-lead", "agree-on-this", "two-known"])
def test_r7_prose_that_opens_with_a_known_name_list_is_kept(raw):
    """M1 (REGRESSION): the N24 bare-list rule counted "Reuters all flagged it" as a name."""
    assert gw._research_strip_model_trailer(raw, R7_CORPUS) == raw


@pytest.mark.parametrize("sentence", [
    "外资率先买入科技股。", "北向资金率先卖出银行股。", "机构一再卖出地产股。", "外资不再买入地产股。",
    "外资买入科技股，内资则卖出银行股。", "外资先卖出银行股，然后买入科技股。", "外资趁便宜买入银行股。",
])
def test_r7_zh_flow_narration_is_a_report(sentence):
    """M2 (REGRESSION): r6's one-character openers fired inside words (率先, 一再, 便宜) and
    on narrative sequencers (则, 然后)."""
    assert gw._research_sentence_forbidden(sentence) is False, sentence


@pytest.mark.parametrize("sentence", [
    "若跌破5800，则卖出。", "先买入龙头。", "适宜买入半导体。", "首先买入龙头。", "跌到位后再买入半导体。", "所以买入NVDA。",
])
def test_r7_zh_clause_openers_still_anchor(sentence):
    assert gw._research_sentence_forbidden(sentence) is True, sentence


@pytest.mark.parametrize("sentence", [
    "Historically, buy the dip has worked in uptrends.", "Since 2009, buy and hold has beaten market timing.",
    "Retail tends to buy dips, sell rallies and chase winners.", "Systematic funds buy strength, sell weakness.",
    "The retail reflex (buy the dip) failed in 2022.", "Funds buy strength and sell weakness in this regime.",
])
def test_r7_a_strategy_named_or_a_flow_described_is_not_an_order(sentence):
    """M3 (REGRESSION): the r6 clause-join anchors (",", "(", "and") read the second verb of a
    flow description, and a strategy named as a sentence subject, as orders."""
    assert gw._research_sentence_forbidden(sentence) is False, sentence


@pytest.mark.parametrize("sentence", [
    "Our stance (buy the dip) is unchanged.", "Breadth is thin; buy the dip.", "Buy NVDA and sell TSLA.",
    "First buy the leaders, then sell the laggards.", "Our view: buy signals are flashing, so buy NVDA.",
    "Buy or sell NVDA on a break of 5800.", "Buy orders in size, adding on dips.", "Levels held; buy the dip, sell the rip.",
])
def test_r7_orders_behind_the_new_exclusions_are_still_withheld(sentence):
    """M4 (REGRESSION): "Buy or sell NVDA on a break of 5800" is one order; m1: "Buy orders in
    size, adding on dips" is an order (the clause break ends the prepositional window)."""
    assert gw._research_sentence_forbidden(sentence) is True, sentence


@pytest.mark.parametrize("sentence", [
    "Ratings (buy side) moved up.", "Buy or sell signals were mixed.", "The desk does not say what to do (buy or sell) here.",
])
def test_r7_a_pair_or_a_side_in_parentheses_is_a_report(sentence):
    assert gw._research_sentence_forbidden(sentence) is False, sentence


def test_r7_a_kept_html_blank_is_one_paragraph_break():
    """m2 (NEW, cosmetic): a kept HTML-made blank next to a real one left a triple newline."""
    raw = "G.<br>\n\nSources: Desk read\n\nRisks\n- Oil shock"
    assert gw._research_strip_model_trailer(raw, R7_CORPUS) == "G.\n\nRisks\n- Oil shock"

