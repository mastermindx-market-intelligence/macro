"""Tests for lib/mastermind_response_log.py — the shared write contract for the
Mastermind AI response log (both Macro brain + Terminal copilot surfaces)."""
from __future__ import annotations

import json

import pytest

from lib import mastermind_response_log as mm


# ---------------------------------------------------------------------------
# Env isolation: default every test to NO sink unless it opts in.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET",
              "MASTERMIND_RESPONSE_LOG_LOCAL_DIR", "MASTERMIND_RESPONSE_LOG_DISABLED"):
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------------------
# hash_user_ref — privacy
# ---------------------------------------------------------------------------
def test_hash_user_ref_guest_collapses():
    assert mm.hash_user_ref(is_guest=True) == "guest"
    assert mm.hash_user_ref("abc", is_guest=True) == "guest"


def test_hash_user_ref_never_leaks_raw_id_or_email():
    uid = "3f0c-user-uuid"
    email = "someone@example.com"
    ref = mm.hash_user_ref(uid, email)
    assert ref.startswith("u_")
    assert uid not in ref
    assert email not in ref
    # Stable + deterministic.
    assert ref == mm.hash_user_ref(uid, email)


def test_hash_user_ref_anon_when_empty():
    assert mm.hash_user_ref("", "", False) == "anon"


# ---------------------------------------------------------------------------
# build_row — schema shape
# ---------------------------------------------------------------------------
def test_build_row_shape_and_provider_inference():
    row = mm.build_row(
        surface="macro", question="what is spx doing?", answer="It is up 1%.",
        model="claude-opus-4-8", lane="pro", mode="chat", user_id="u1",
        latency_ms=1234, input_tokens=10, output_tokens=20,
        context={"page": "dashboard", "symbol": "SPY", "junk": {"x": 1}},
    )
    assert row["schema"] == "mastermind.response_log.v1"
    assert row["surface"] == "macro"
    assert row["provider"] == "claude_api"          # inferred from claude* model
    assert row["user_ref"].startswith("u_")
    assert row["question"] == "what is spx doing?"
    assert row["answer"] == "It is up 1%."
    assert row["latency_ms"] == 1234
    assert row["input_tokens"] == 10 and row["output_tokens"] == 20
    # context keeps only known scalar keys
    assert row["context"] == {"page": "dashboard", "symbol": "SPY"}
    assert set(row["flags"]) == {"filtered", "degraded", "error", "screened"}
    assert row["id"]


def test_build_row_deepseek_provider_and_terminal_surface():
    row = mm.build_row(surface="terminal", question="q", answer="a", model="deepseek-chat")
    assert row["surface"] == "terminal"
    assert row["provider"] == "deepseek"


def test_build_row_unknown_surface_defaults_macro():
    row = mm.build_row(surface="weird", question="q", answer="a")
    assert row["surface"] == "macro"


def test_build_row_clips_long_answer():
    long = "x" * 40000
    row = mm.build_row(surface="macro", question="q", answer=long)
    assert row["answer"].endswith("…[truncated]")
    assert len(row["answer"]) < len(long)


# ---------------------------------------------------------------------------
# thinking — the reasoning trace (contradiction-assessment corpus)
# ---------------------------------------------------------------------------
def _seg(text="thought", round_=1, phase="tool", model="deepseek-v4-flash", **kw):
    seg = {"round": round_, "phase": phase, "model": model, "text": text}
    seg.update(kw)
    return seg


def test_build_row_thinking_defaults_to_empty_list():
    # Old callers pass nothing; the field must still exist so readers never branch.
    row = mm.build_row(surface="macro", question="q", answer="a")
    assert row["thinking"] == []


def test_build_row_keeps_thinking_segments():
    row = mm.build_row(surface="macro", question="q", answer="a", thinking=[
        _seg("weighing the two reads", round_=1, phase="tool"),
        _seg("they disagree", round_=2, phase="synthesis", model="claude-opus-5"),
    ])
    assert [s["phase"] for s in row["thinking"]] == ["tool", "synthesis"]
    assert row["thinking"][1]["model"] == "claude-opus-5"
    assert row["thinking"][1]["round"] == 2


def test_build_row_clips_each_thinking_segment():
    long = "y" * 40000
    row = mm.build_row(surface="macro", question="q", answer="a",
                       thinking=[_seg(long), _seg(long)])
    for seg in row["thinking"]:
        assert seg["text"].endswith("…[truncated]")
        assert len(seg["text"]) < len(long)
        # Bound is per-segment, not per-trace: a 2-segment trace clips twice.
        assert len(seg["text"]) <= mm._THINKING_TEXT_CAP + 32


def test_build_row_caps_thinking_keeping_the_head_and_the_last_segment():
    """FIRST (N-1) + LAST. A chain of thought frames the conflict up front, but the
    SYNTHESIS segment rides last and is the decision the corpus exists to show — a plain
    head-truncation would drop exactly that. Middle tool rounds are what gets dropped."""
    row = mm.build_row(surface="macro", question="q", answer="a",
                       thinking=[_seg(f"step {i}", round_=i) for i in range(60)])
    assert len(row["thinking"]) == mm._THINKING_MAX_SEGMENTS
    assert row["thinking"][0]["text"] == "step 0"
    assert row["thinking"][-2]["text"] == f"step {mm._THINKING_MAX_SEGMENTS - 2}"
    assert row["thinking"][-1]["text"] == "step 59"


def test_build_row_cap_keeps_the_synthesis_segment_of_a_long_trace():
    """The load-bearing case: a long tool-heavy turn whose synthesis is the last block."""
    segs = [_seg(f"tool {i}", round_=i, phase="tool") for i in range(80)]
    segs.append(_seg("here is the call", round_=81, phase="synthesis",
                     model="claude-opus-5"))
    row = mm.build_row(surface="macro", question="q", answer="a", thinking=segs)
    assert len(row["thinking"]) == mm._THINKING_MAX_SEGMENTS
    assert row["thinking"][-1]["phase"] == "synthesis"
    assert row["thinking"][-1]["text"] == "here is the call"


def test_build_row_thinking_under_the_cap_is_untouched():
    """No phantom duplicate of the last segment when the trace already fits."""
    n = mm._THINKING_MAX_SEGMENTS - 1
    row = mm.build_row(surface="macro", question="q", answer="a",
                       thinking=[_seg(f"step {i}", round_=i) for i in range(n)])
    assert [s["text"] for s in row["thinking"]] == [f"step {i}" for i in range(n)]


def test_build_row_thinking_exactly_at_the_cap_is_untouched():
    n = mm._THINKING_MAX_SEGMENTS
    row = mm.build_row(surface="macro", question="q", answer="a",
                       thinking=[_seg(f"step {i}", round_=i) for i in range(n)])
    assert [s["text"] for s in row["thinking"]] == [f"step {i}" for i in range(n)]


def test_build_row_redacted_thinking_survives_with_empty_text():
    row = mm.build_row(surface="macro", question="q", answer="a",
                       thinking=[_seg("", redacted=True), _seg("")])
    # The redacted one is kept (evidence the model reasoned); the plain empty is dropped.
    assert len(row["thinking"]) == 1
    assert row["thinking"][0]["text"] == ""
    assert row["thinking"][0]["redacted"] is True


def test_build_row_drops_non_dict_thinking_segments():
    row = mm.build_row(surface="macro", question="q", answer="a",
                       thinking=["a bare string", None, 7, _seg("real")])
    assert [s["text"] for s in row["thinking"]] == ["real"]


def test_build_row_thinking_coerces_types():
    row = mm.build_row(surface="macro", question="q", answer="a",
                       thinking=[{"round": "3", "phase": 9, "model": None, "text": "t"}])
    seg = row["thinking"][0]
    assert seg["round"] == 3 and isinstance(seg["round"], int)
    assert seg["phase"] == "9" and seg["model"] == ""


def test_build_row_thinking_non_list_is_empty():
    assert mm.build_row(surface="macro", question="q", answer="a",
                        thinking="not a list")["thinking"] == []


def test_thinking_round_trips_through_the_local_sink(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTERMIND_RESPONSE_LOG_LOCAL_DIR", str(tmp_path))
    assert mm.log_response(surface="macro", question="q", answer="a",
                           thinking=[_seg("the two reads disagree")]) is True
    written = json.loads(list(tmp_path.rglob("*.json"))[0].read_text())
    assert written["thinking"][0]["text"] == "the two reads disagree"


# ---------------------------------------------------------------------------
# object_key — R2 layout
# ---------------------------------------------------------------------------
def test_object_key_layout():
    row = mm.build_row(surface="terminal", question="q", answer="a", row_id="abc123")
    key = mm.object_key(row)
    assert key.startswith("mastermind_response_logs/terminal/")
    assert key.endswith("/abc123.json")
    # date segment between surface and id
    parts = key.split("/")
    assert len(parts) == 4 and parts[2][:4].isdigit()


# ---------------------------------------------------------------------------
# enabled() gating
# ---------------------------------------------------------------------------
def test_enabled_false_without_any_sink():
    assert mm.enabled() is False


def test_enabled_true_with_local_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTERMIND_RESPONSE_LOG_LOCAL_DIR", str(tmp_path))
    assert mm.enabled() is True


def test_disabled_flag_overrides_sink(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTERMIND_RESPONSE_LOG_LOCAL_DIR", str(tmp_path))
    monkeypatch.setenv("MASTERMIND_RESPONSE_LOG_DISABLED", "1")
    assert mm.enabled() is False


# ---------------------------------------------------------------------------
# write_row / log_response — local mirror sink
# ---------------------------------------------------------------------------
def test_write_row_local_mirror(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTERMIND_RESPONSE_LOG_LOCAL_DIR", str(tmp_path))
    row = mm.build_row(surface="macro", question="hi", answer="hello", row_id="rid1")
    assert mm.write_row(row) is True
    files = list(tmp_path.rglob("*.json"))
    assert len(files) == 1
    written = json.loads(files[0].read_text())
    assert written["id"] == "rid1"
    assert written["answer"] == "hello"
    # path mirrors the R2 key layout (minus the prefix)
    assert files[0].parent.parent.name == "macro"


def test_log_response_noop_when_disabled():
    # No sink configured → best-effort no-op, returns False, never raises.
    assert mm.log_response(surface="macro", question="q", answer="a") is False


# ---------------------------------------------------------------------------
# brain_gateway integration — surface is derived from context.page so ONE
# instrumentation point covers BOTH surfaces (Macro widget + Terminal widget,
# both run mm_brain.js against /api/brain/stream; page='terminal' on the Terminal).
# ---------------------------------------------------------------------------
def test_surface_derived_from_context_page(monkeypatch, tmp_path):
    monkeypatch.setenv("MASTERMIND_RESPONSE_LOG_LOCAL_DIR", str(tmp_path))
    from engine.neuralweb import brain_gateway as bg

    captured: dict = {}
    monkeypatch.setattr(mm, "log_response_async", lambda **kw: captured.update(kw))

    bg._log_brain_response(question="q", answer="a", context={"page": "terminal", "symbol": "AAPL"})
    assert captured.get("surface") == "terminal"

    captured.clear()
    bg._log_brain_response(question="q", answer="a", context={"page": "dashboard"})
    assert captured.get("surface") == "macro"

    captured.clear()
    bg._log_brain_response(question="q", answer="a", context={})
    assert captured.get("surface") == "macro"  # missing page → macro

    captured.clear()
    bg._log_brain_response(question="q", answer="   ", context={"page": "terminal"})
    assert captured == {}  # empty answer → not a response, no write


# ---------------------------------------------------------------------------
# _clean_native_numeric_verification — native numeric verification telemetry
# (internal QA only; the sanitized record is the only thing build_row stores)
# ---------------------------------------------------------------------------
def _nnv(**kw):
    """A minimal well-formed not_assessed record; tests mutate from there."""
    rec = {"status": "not_assessed", "reason": "internal_error",
           "checked_count": 0, "references": [], "internal_qa_only": True}
    rec.update(kw)
    return rec


def _nnv_ref(field_id="market.price.last", fingerprint=None):
    if fingerprint is None:
        fingerprint = "a" * 64
    return {"field_id": field_id, "fact_fingerprint": fingerprint}


def _nnv_verified(count, refs):
    return _nnv(status="verified", reason="numeric_response_verified",
                checked_count=count, references=refs)


def test_clean_native_numeric_verification_positive_verified():
    refs = [_nnv_ref("market.price.last", "0" * 64),
            _nnv_ref("stage.current", "1" * 64),
            _nnv_ref("industry.rank.percentile", "2" * 64)]
    out = mm._clean_native_numeric_verification(_nnv_verified(3, refs))
    assert out is not None
    # exactly the five schema keys, in order, nothing echoed from the caller
    assert list(out) == ["status", "reason", "checked_count", "references",
                         "internal_qa_only"]
    assert out["status"] == "verified"
    assert out["reason"] == "numeric_response_verified"
    assert out["checked_count"] == 3
    assert isinstance(out["checked_count"], int)
    assert out["references"] == refs          # projects exactly the two keys
    assert out["internal_qa_only"] is True


def test_clean_native_numeric_verification_positive_not_assessed_and_mismatch():
    out = mm._clean_native_numeric_verification(_nnv())
    assert out == {"status": "not_assessed", "reason": "internal_error",
                   "checked_count": 0, "references": [],
                   "internal_qa_only": True}
    out = mm._clean_native_numeric_verification(
        _nnv(status="mismatch", reason="answer_mismatch"))
    assert out["status"] == "mismatch"
    assert out["reason"] == "answer_mismatch"
    assert out["checked_count"] == 0 and out["references"] == []


def test_clean_native_numeric_verification_malformed_returns_none():
    bad = [
        None, "verified", 42, 3.5, [], {}, ("verified",),
        # missing pieces
        {k: v for k, v in _nnv().items() if k != "status"},
        {k: v for k, v in _nnv().items() if k != "reason"},
        {k: v for k, v in _nnv().items() if k != "checked_count"},
        {k: v for k, v in _nnv().items() if k != "references"},
        # unknown status
        _nnv(status="assessed"),
        _nnv(status="verified "),
        # the success reason is reserved for the verified status
        _nnv(status="verified", reason="internal_error"),
        _nnv(status="mismatch", reason="numeric_response_verified"),
        _nnv(status="not_assessed", reason="numeric_response_verified"),
        # a verified claim with no references behind it
        _nnv(status="verified", reason="numeric_response_verified"),
        # references that cannot back the verified claim
        _nnv_verified(1, [{"field_id": "market.price.last"}]),
        _nnv_verified(1, [{"fact_fingerprint": "a" * 64}]),
        _nnv_verified(1, [_nnv_ref(field_id="Market.Price.Last")]),   # uppercase
        _nnv_verified(1, [_nnv_ref(field_id="1market.price")]),       # leading digit
        _nnv_verified(1, [_nnv_ref(field_id="market price")]),        # space
        _nnv_verified(1, [_nnv_ref(fingerprint="A" * 64)]),           # upper hex
        _nnv_verified(1, [_nnv_ref(fingerprint="a" * 63)]),           # short
        _nnv_verified(1, [_nnv_ref(fingerprint="g" * 64)]),           # not hex
        _nnv_verified(1, [_nnv_ref(fingerprint="")]),                 # empty
        _nnv_verified(3, [_nnv_ref("f.1", "0" * 64), _nnv_ref("f.2", "1" * 64)]),
        # a mismatch/not_assessed record must arrive already empty
        _nnv(status="mismatch", reason="answer_mismatch", checked_count=2),
        _nnv(status="mismatch", reason="answer_mismatch", references=[_nnv_ref()]),
        _nnv(status="not_assessed", reason="internal_error", checked_count=1),
    ]
    for rec in bad:
        assert mm._clean_native_numeric_verification(rec) is None, rec


def test_clean_native_numeric_verification_rejects_wrong_types():
    # bool is an int subclass: it is NOT a count
    for bad_count in (True, False, 3.0, "3", None):
        assert mm._clean_native_numeric_verification(
            _nnv_verified(bad_count, [_nnv_ref()])) is None, bad_count
    # references must be a real list
    for bad_refs in (None, {}, (_nnv_ref(),), "refs", 7):
        assert mm._clean_native_numeric_verification(
            _nnv_verified(1, bad_refs)) is None, bad_refs
    # status/reason are type-checked BEFORE any set membership
    for bad_status in (1, True, ["verified"], {"status": "verified"}):
        assert mm._clean_native_numeric_verification(
            _nnv(status=bad_status)) is None, bad_status
    for bad_reason in (7, ["internal_error"], True):
        assert mm._clean_native_numeric_verification(
            _nnv(reason=bad_reason)) is None, bad_reason
    # A reference that is not a dict rejects the entire record.
    assert mm._clean_native_numeric_verification(
        _nnv_verified(2, [_nnv_ref(), "market.price.last"])) is None


def test_clean_native_numeric_verification_never_raises_on_hostile_input():
    class _HostileDict(dict):
        def get(self, *a, **k):
            raise RuntimeError("hostile payload")

    class _HostileList(list):
        def __getitem__(self, item):
            raise RuntimeError("hostile slice")

    assert mm._clean_native_numeric_verification(_HostileDict()) is None
    assert mm._clean_native_numeric_verification(
        _nnv_verified(1, _HostileList([_nnv_ref()]))) is None


def test_clean_native_numeric_verification_bounds():
    def refs(n, start=0):
        return [_nnv_ref(field_id=f"field.{i}", fingerprint=f"{i:064x}")
                for i in range(start, start + n)]

    # 12 distinct references is the ceiling and is accepted
    out = mm._clean_native_numeric_verification(_nnv_verified(12, refs(12)))
    assert out is not None and len(out["references"]) == 12
    # 13 is one too many
    assert mm._clean_native_numeric_verification(_nnv_verified(13, refs(13))) is None
    # verified requires at least one reference
    assert mm._clean_native_numeric_verification(
        _nnv_verified(0, [])) is None
    assert mm._clean_native_numeric_verification(
        _nnv_verified(-1, refs(1))) is None
    # field_id: 128 chars passes, 129 is malformed and sinks the claim
    long_id = "a" + "b" * 127
    assert mm._clean_native_numeric_verification(
        _nnv_verified(1, [_nnv_ref(field_id=long_id)])) is not None
    assert mm._clean_native_numeric_verification(
        _nnv_verified(1, [_nnv_ref(field_id=long_id + "c")])) is None
    # Oversized inputs are rejected before iteration, even when extras are malformed.
    big = refs(12) + [{"field_id": f"Junk.{i}", "fact_fingerprint": "f" * 64}
                      for i in range(200)]
    out = mm._clean_native_numeric_verification(_nnv_verified(12, big))
    assert out is None
    # well-formed but UNDECLARED references are a different matter: the kept
    # count must equal the claim exactly, so extras sink the record
    assert mm._clean_native_numeric_verification(_nnv_verified(
        12, refs(12) + refs(3, start=90))) is None


def test_clean_native_numeric_verification_duplicate_references():
    dup = [_nnv_ref("market.price.last"), _nnv_ref("market.price.last"),
           _nnv_ref("stage.current", "3" * 64)]
    # the claim says 3 checked but only 2 are distinct — never coerced to fit
    assert mm._clean_native_numeric_verification(_nnv_verified(3, dup)) is None
    # Neither an adjusted count nor a different fingerprint can excuse a duplicate field.
    assert mm._clean_native_numeric_verification(_nnv_verified(2, dup)) is None
    assert mm._clean_native_numeric_verification(_nnv_verified(
        2, [_nnv_ref("market.price.last", "4" * 64),
            _nnv_ref("market.price.last", "5" * 64)])) is None


def test_clean_native_numeric_verification_unknown_reason_rejected():
    for bad in ("numeric_response_verified ", "NUMERIC_RESPONSE_VERIFIED",
                "answer_wrong", "unknown", ""):
        assert mm._clean_native_numeric_verification(_nnv(reason=bad)) is None, bad
    # every non-success code in the module vocabulary fits not_assessed
    for reason in sorted(mm._NATIVE_NUMERIC_REASONS - {"numeric_response_verified"}):
        assert mm._clean_native_numeric_verification(
            _nnv(reason=reason)) is not None, reason
    # ...and the success code fits verified alone
    assert mm._clean_native_numeric_verification(
        _nnv_verified(1, [_nnv_ref()]))["reason"] == "numeric_response_verified"


def test_clean_native_numeric_verification_does_not_mutate_input():
    record = _nnv_verified(2, [
        _nnv_ref("market.price.last", "6" * 64),
        {"field_id": "stage.current", "fact_fingerprint": "7" * 64,
         "raw_answer": "the actual number"},
    ])
    snapshot = json.loads(json.dumps(record))
    out = mm._clean_native_numeric_verification(record)
    assert out is not None and len(out["references"]) == 2
    assert record == snapshot  # input untouched; the extra ref key is still there
    # a rejected record is left exactly as it arrived, too
    rejected = _nnv_verified(5, [_nnv_ref()])
    rejected_snapshot = json.loads(json.dumps(rejected))
    assert mm._clean_native_numeric_verification(rejected) is None
    assert rejected == rejected_snapshot


def test_clean_native_numeric_verification_suppresses_extra_secret_keys():
    secret = "sk-live-9f3a1c77-do-not-leak"
    record = _nnv_verified(1, [{
        "field_id": "market.price.last", "fact_fingerprint": "8" * 64,
        "raw_answer": "4.1913", "prompt": secret,
    }])
    record.update(api_key=secret, authorization=f"Bearer {secret}",
                  source={"envelope": {"inner": secret}},
                  narrative="the model said the wrong number")
    out = mm._clean_native_numeric_verification(record)
    assert out is not None
    assert set(out) == {"status", "reason", "checked_count", "references",
                        "internal_qa_only"}
    assert set(out["references"][0]) == {"field_id", "fact_fingerprint"}
    dumped = json.dumps(out)
    assert secret not in dumped
    assert "4.1913" not in dumped
    for leaked in ("api_key", "authorization", "narrative", "source", "prompt",
                   "raw_answer"):
        assert leaked not in dumped, leaked
    # Missing or false internal-only claims are rejected, never restamped.
    for flag in (False, None, "no", 1):
        assert mm._clean_native_numeric_verification(_nnv(internal_qa_only=flag)) is None
    missing = _nnv()
    missing.pop("internal_qa_only")
    assert mm._clean_native_numeric_verification(missing) is None
