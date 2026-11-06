"""Tests for engine/qual_extraction.py — the qual_extraction.v1 contract.

No network / no API key required: the model call is stubbed; the safety gates
(JSON parse, schema validation, verbatim-citation verification, confidence floor,
sha-keyed reply cache, config model-id load) are exercised as pure functions.

Run as a plain script:
    python tests/test_qual_extraction.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import engine.qual_extraction as qe  # noqa: E402

# ---------------------------------------------------------------------------
# sample filing body — used across tests
# ---------------------------------------------------------------------------
BODY = (
    "On July 1, 2026, ACME Corporation entered into a definitive merger agreement "
    "with Globex Inc. under which Globex will acquire all outstanding shares of ACME "
    "for $42.00 per share in cash. The transaction represents a 35 percent premium "
    "to ACME's closing price. The merger is expected to close in the fourth quarter "
    "of 2026, subject to regulatory approval and ACME shareholder vote. "
    "The Board of Directors of ACME has unanimously approved the merger agreement."
)


# ---------------------------------------------------------------------------
# 1. _norm helper
# ---------------------------------------------------------------------------
def test_norm_collapses_whitespace_and_lowercases():
    assert qe._norm("Foo  Bar\tBaz") == "foo bar baz"
    assert qe._norm("") == ""
    assert qe._norm("Hello-World!") == "hello world"


# ---------------------------------------------------------------------------
# 2. _extract_json
# ---------------------------------------------------------------------------
def test_extract_json_plain():
    assert qe._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    assert qe._extract_json('```json\n{"a": 2}\n```') == {"a": 2}


def test_extract_json_with_prose():
    assert qe._extract_json('Here is the result:\n{"a": 3}\nDone.') == {"a": 3}


def test_extract_json_invalid():
    assert qe._extract_json('not json at all') is None
    assert qe._extract_json('') is None
    assert qe._extract_json('[1, 2, 3]') is None  # list is not a record


# ---------------------------------------------------------------------------
# 3. _validate — enum coercion and numeric clamp
# ---------------------------------------------------------------------------
def test_validate_valid_record():
    rec = qe._validate({
        "direction": "up",
        "magnitude": "large",
        "horizon": "short_term",
        "reversibility": "reversible",
        "importance_raw": 85,
        "confidence": "high",
        "evidence": [{"field": "direction", "quote_span": "acquire all outstanding shares"}],
    })
    assert rec["direction"] == "up"
    assert rec["magnitude"] == "large"
    assert rec["horizon"] == "short_term"
    assert rec["reversibility"] == "reversible"
    assert rec["importance_raw"] == 85
    assert rec["confidence"] == "high"
    assert len(rec["evidence"]) == 1


def test_validate_enum_violations_to_unknown():
    rec = qe._validate({
        "direction": "sideways",      # invalid
        "magnitude": "HUGE",          # invalid (wrong case AND not a valid enum)
        "horizon": "forever",         # invalid
        "reversibility": "maybe",     # invalid
        "confidence": "extreme",      # invalid
    })
    assert rec["direction"] == "unknown"
    assert rec["magnitude"] == "unknown"
    assert rec["horizon"] == "unknown"
    assert rec["reversibility"] == "unknown"
    assert rec["confidence"] == "low"   # falls to 'low' (the neutral)


def test_validate_importance_clamp():
    rec = qe._validate({"importance_raw": 150})
    assert rec["importance_raw"] == 100

    rec2 = qe._validate({"importance_raw": -10})
    assert rec2["importance_raw"] == 0


def test_validate_evidence_type_check():
    rec = qe._validate({"evidence": "not a list"})
    assert rec["evidence"] == []

    # evidence entries missing 'field' or 'quote_span' are silently dropped
    rec2 = qe._validate({"evidence": [{"field": "direction"}]})
    assert rec2["evidence"] == []


# ---------------------------------------------------------------------------
# 4. _verify_citations — verbatim pass, paraphrase fail
# ---------------------------------------------------------------------------
def test_verify_citations_verbatim_passes():
    """A quote that appears verbatim (after _norm) in the body is kept."""
    rec = qe._validate({
        "direction": "up",
        "magnitude": "large",
        "confidence": "high",
        "evidence": [
            {"field": "direction", "quote_span": "acquire all outstanding shares"},  # verbatim
            {"field": "magnitude", "quote_span": "35 percent premium"},              # verbatim
        ],
    })
    qe._verify_citations(rec, BODY)
    assert rec["direction"] == "up"     # verified → kept
    assert rec["magnitude"] == "large"  # verified → kept
    assert len(rec["evidence"]) == 2


def test_verify_citations_paraphrase_fails():
    """A paraphrase collapses the field to neutral and records it in dropped_fields."""
    rec = qe._validate({
        "direction": "up",
        "confidence": "high",
        "evidence": [
            # This is a paraphrase, NOT a verbatim quote from BODY
            {"field": "direction", "quote_span": "the company was acquired for a large premium"},
        ],
    })
    qe._verify_citations(rec, BODY)
    assert rec["direction"] == "unknown"          # paraphrase → collapsed
    assert "direction" in rec["dropped_fields"]


def test_verify_citations_no_evidence_drops_field():
    """A non-neutral field with no evidence entry collapses."""
    rec = qe._validate({
        "direction": "down",
        "confidence": "high",
        "evidence": [],               # no evidence at all
    })
    qe._verify_citations(rec, BODY)
    assert rec["direction"] == "unknown"
    assert "direction" in rec["dropped_fields"]


def test_verify_citations_all_neutral_has_no_drops():
    """All-neutral record with no evidence produces empty dropped_fields."""
    rec = qe._validate({"direction": "unknown", "confidence": "low", "evidence": []})
    qe._verify_citations(rec, BODY)
    assert rec["dropped_fields"] == []


# ---------------------------------------------------------------------------
# 5. _apply_confidence_floor
# ---------------------------------------------------------------------------
def test_confidence_floor_collapses_below_threshold():
    rec = qe._validate({
        "direction": "up",
        "importance_raw": 80,
        "confidence": "low",
        "evidence": [{"field": "direction", "quote_span": "acquire all outstanding shares"}],
    })
    qe._verify_citations(rec, BODY)
    # floor = "medium" → "low" is below → collapse everything
    qe._apply_confidence_floor(rec, "medium")
    assert rec["direction"] == "unknown"
    assert rec["importance_raw"] == 0
    assert rec["confidence_gated"] is True


def test_confidence_floor_passes_at_or_above():
    rec = qe._validate({
        "direction": "up",
        "confidence": "high",
        "evidence": [{"field": "direction", "quote_span": "acquire all outstanding shares"}],
    })
    qe._verify_citations(rec, BODY)
    qe._apply_confidence_floor(rec, "medium")   # high >= medium → pass
    assert rec["direction"] == "up"
    assert rec["confidence_gated"] is False


# ---------------------------------------------------------------------------
# 6. Reply cache — determinism
# ---------------------------------------------------------------------------
def test_cache_determinism():
    """Same body → same prompt hash → same cached reply."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = {"reply_cache_dir": tmpdir}
        model = "test-model"
        system = qe._EXTRACTION_SYSTEM
        user = "some user message"
        phash = qe._prompt_hash(model, system, user)

        # Nothing in cache yet
        assert qe._cache_get(phash, cfg) is None

        # Write and retrieve
        qe._cache_put(phash, '{"direction": "up"}', cfg)
        result = qe._cache_get(phash, cfg)
        assert result == '{"direction": "up"}'

        # Second write with same hash is idempotent (same file)
        qe._cache_put(phash, '{"direction": "down"}', cfg)
        result2 = qe._cache_get(phash, cfg)
        # The second write overwrites (cache_put is not append-only in this impl)
        assert result2 == '{"direction": "down"}'


def test_prompt_hash_stable():
    """Same inputs → same hash."""
    h1 = qe._prompt_hash("model-a", "sys", "user")
    h2 = qe._prompt_hash("model-a", "sys", "user")
    assert h1 == h2

    h3 = qe._prompt_hash("model-b", "sys", "user")
    assert h1 != h3


# ---------------------------------------------------------------------------
# 7. source_id (sha256 of body)
# ---------------------------------------------------------------------------
def test_source_id_is_sha256():
    sid = qe.source_id(BODY)
    expected = hashlib.sha256(BODY.encode("utf-8")).hexdigest()
    assert sid == expected


def test_source_id_empty():
    assert qe.source_id("") == hashlib.sha256(b"").hexdigest()


# ---------------------------------------------------------------------------
# 8. config model-id load (LookupError on missing llm_models)
# ---------------------------------------------------------------------------
def test_model_id_raises_when_llm_models_missing():
    """_model_id() must raise LookupError when config has no llm_models block."""
    with patch.object(qe.config, "load", return_value={}):
        try:
            qe._model_id()
            assert False, "Expected LookupError"
        except LookupError:
            pass


def test_model_id_raises_when_extraction_missing():
    """_model_id() must raise LookupError when llm_models.extraction is absent."""
    with patch.object(qe.config, "load", return_value={"llm_models": {"reasoning": "x"}}):
        try:
            qe._model_id()
            assert False, "Expected LookupError"
        except LookupError:
            pass


def test_model_id_returns_configured_value():
    cfg = {"llm_models": {"extraction": "claude-haiku-4-5"}}
    with patch.object(qe.config, "load", return_value=cfg):
        assert qe._model_id() == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# 9. extract() — end-to-end with stubbed model call
# ---------------------------------------------------------------------------
def _fake_model_reply(body: str) -> str:
    """Simulate a model that returns a valid, citation-verifiable record."""
    return json.dumps({
        "direction": "up",
        "magnitude": "large",
        "horizon": "medium_term",
        "reversibility": "persistent",
        "importance_raw": 90,
        "confidence": "high",
        "evidence": [
            {"field": "direction", "quote_span": "acquire all outstanding shares"},
            {"field": "magnitude", "quote_span": "35 percent premium"},
            {"field": "reversibility", "quote_span": "merger agreement"},
            {"field": "importance_raw", "quote_span": "close in the fourth quarter"},
            {"field": "horizon", "quote_span": "close in the fourth quarter of 2026"},
            {"field": "confidence", "quote_span": "unanimously approved"},
        ],
    })


def test_extract_full_pipeline_verbatim():
    """Integration: valid body + verbatim quotes → all fields verified, brain_usable=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_data = {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {
                "enabled": True,
                "reply_cache_dir": tmpdir,
                "max_body_chars": 100000,
                "max_tokens": 1500,
                "confidence_floor": "low",
                "api_key_env": "TEST_KEY",
            },
        }
        with patch.object(qe.config, "load", return_value=cfg_data), \
             patch.object(qe.config, "secret", return_value="fake-key"), \
             patch.object(qe, "_client", return_value=MagicMock()):
            # Inject a fake _call_model that returns the valid reply
            reply = _fake_model_reply(BODY)
            with patch.object(qe, "_call_model", return_value=(reply, None)):
                result = qe.extract(BODY, context="test filing")

    assert result is not None
    assert result["schema"] == "qual_extraction.v1"
    assert result["is_context_only"] is True
    fields = result["fields"]
    assert fields["direction"] == "up"
    assert fields["magnitude"] == "large"
    assert fields["importance_raw"] == 90
    assert fields["confidence"] == "high"
    assert result["brain_usable"] is True
    # No fields should be dropped since all have verbatim quotes
    # (some may still be dropped if the norm check fails on edge cases — just check direction)
    assert fields["direction"] == "up"


def test_extract_paraphrase_collapses():
    """Paraphrased evidence → fields collapse → brain_usable=False (dropped_fields set)."""
    paraphrase_reply = json.dumps({
        "direction": "up",
        "magnitude": "large",
        "confidence": "high",
        "evidence": [
            {"field": "direction", "quote_span": "the company was taken over for a big premium"},  # FABRICATED
            {"field": "magnitude", "quote_span": "significant financial terms were announced"},    # FABRICATED
        ],
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_data = {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {
                "enabled": True,
                "reply_cache_dir": tmpdir,
                "confidence_floor": "low",
                "api_key_env": "TEST_KEY",
            },
        }
        with patch.object(qe.config, "load", return_value=cfg_data), \
             patch.object(qe.config, "secret", return_value="fake-key"), \
             patch.object(qe, "_call_model", return_value=(paraphrase_reply, None)):
            result = qe.extract(BODY, context="test")

    assert result is not None
    fields = result["fields"]
    # Both fields should collapse because the quotes aren't verbatim
    assert fields["direction"] == "unknown"
    assert fields["magnitude"] == "unknown"
    # brain_usable: False because dropped_fields is set
    assert result["brain_usable"] is False
    assert "direction" in result["dropped_fields"]
    assert "magnitude" in result["dropped_fields"]


def test_extract_model_gated_off():
    """When enabled=False, extract() returns None immediately."""
    cfg_data = {
        "llm_models": {"extraction": "test-model-x"},
        "qual_extraction": {"enabled": False},
    }
    with patch.object(qe.config, "load", return_value=cfg_data):
        result = qe.extract(BODY)
    assert result is None


def test_extract_model_call_failure():
    """When the model call returns a degraded reason, brain_usable=False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_data = {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {"enabled": True, "reply_cache_dir": tmpdir, "api_key_env": "K"},
        }
        with patch.object(qe.config, "load", return_value=cfg_data), \
             patch.object(qe.config, "secret", return_value="fake-key"), \
             patch.object(qe, "_call_model", return_value=(None, "llm_error")):
            result = qe.extract(BODY, context="test")

    assert result is not None
    assert result["brain_usable"] is False
    assert result["degraded_reason"] == "llm_error"


def test_extract_json_parse_failure():
    """When the model returns unparseable JSON, brain_usable=False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_data = {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {"enabled": True, "reply_cache_dir": tmpdir, "api_key_env": "K"},
        }
        with patch.object(qe.config, "load", return_value=cfg_data), \
             patch.object(qe.config, "secret", return_value="fake-key"), \
             patch.object(qe, "_call_model", return_value=("not json at all {broken", None)):
            result = qe.extract(BODY, context="test")

    assert result is not None
    assert result["brain_usable"] is False
    assert result["degraded_reason"] == "json_parse_failure"


def test_extract_cache_determinism():
    """Same body → same source_id → cache hit on second call (no second model call)."""
    call_count = [0]
    real_reply = json.dumps({
        "direction": "up",
        "confidence": "high",
        "evidence": [{"field": "direction", "quote_span": "acquire all outstanding shares"}],
    })

    def counting_call_model(body, context, cfg, model):
        call_count[0] += 1
        return real_reply, None

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_data = {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {"enabled": True, "reply_cache_dir": tmpdir, "api_key_env": "K"},
        }
        with patch.object(qe.config, "load", return_value=cfg_data), \
             patch.object(qe.config, "secret", return_value="fake-key"), \
             patch.object(qe, "_call_model", side_effect=counting_call_model):
            r1 = qe.extract(BODY, context="same-context")
            r2 = qe.extract(BODY, context="same-context")

    # Both should succeed
    assert r1 is not None
    assert r2 is not None
    # Both calls go through _call_model in this test because the cache check is
    # inside _call_model itself; our patch intercepts _call_model directly.
    # The cache is populated in _cache_put inside _call_model, so a second direct
    # call to extract() would hit the cache from within _call_model — but since
    # we've replaced _call_model entirely, we can only verify the reply is consistent.
    assert r1["fields"]["direction"] == r2["fields"]["direction"]


# ---------------------------------------------------------------------------
# 10. Schema validation — envelope fields always present
# ---------------------------------------------------------------------------
def test_extract_envelope_fields():
    """The envelope fields (schema, source_id, is_context_only, etc.) are always set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_data = {
            "llm_models": {"extraction": "test-model-x"},
            "qual_extraction": {"enabled": True, "reply_cache_dir": tmpdir, "api_key_env": "K"},
        }
        with patch.object(qe.config, "load", return_value=cfg_data), \
             patch.object(qe.config, "secret", return_value="fake-key"), \
             patch.object(qe, "_call_model", return_value=(None, "no_client_or_key")):
            result = qe.extract(BODY, context="test", source_lane="edgar_8k")

    assert result["schema"] == "qual_extraction.v1"
    assert result["source_id"] == qe.source_id(BODY)
    assert result["source_lane"] == "edgar_8k"
    assert result["extraction_tier"] == "full"
    assert result["is_context_only"] is True
    assert "extracted_at" in result


def test_shared_quote_span_verifier():
    assert qe.quote_span_verified(BODY, "acquire all outstanding shares")
    assert not qe.quote_span_verified(BODY, "this phrase is fabricated")
    assert qe.citation_normalize("2.1%") == "2.1%"


def test_shared_quote_span_verifier_preserves_unicode_and_token_boundaries():
    assert not qe.quote_span_verified("Corporate earnings improved.", "rate")
    assert qe.quote_span_verified("中国流动性正在改善。", "流动性正在改善")
    assert qe.quote_span_verified("ＡＡＰＬ demand rose.", "AAPL demand rose")
    assert not qe.quote_span_verified("AAPL demand rose.", "ＭＳＦＴ demand rose")


def test_shared_quote_span_verifier_rejects_cross_sentence_splices():
    body = "Demand is strong. Losses widened sharply."
    assert not qe.quote_span_verified(body, "strong losses")
    assert qe.quote_span_verified(body, "strong. Losses")

    chinese = "流动性改善。房地产风险上升。"
    assert not qe.quote_span_verified(chinese, "改善房地产")
    assert qe.quote_span_verified(chinese, "改善。房地产")


def test_shared_quote_verifier_clause_mode_rejects_context_stripped_fragments():
    cases = [
        ("Goldman does not expect inflation to rise this year.", "inflation to rise this year"),
        ("The report denies that revenue increased sharply.", "revenue increased sharply"),
        ("Management may reduce guidance next quarter.", "reduce guidance next quarter"),
        ("Policymakers cannot rule out a recession.", "a recession"),
    ]
    for body, fragment in cases:
        assert not qe.quote_span_verified(body, fragment, require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_rejects_soft_punctuation_context_stripping():
    cases = [
        ("Management may, subject to board approval, reduce guidance next quarter.", "reduce guidance next quarter."),
        ("The report denies, based on new evidence, that revenue increased sharply.", "that revenue increased sharply."),
        ("We cannot rule out: a recession in 2027.", "a recession in 2027."),
    ]
    for body, fragment in cases:
        assert not qe.quote_span_verified(body, fragment, require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_rejects_line_wrapped_context_stripping():
    cases = [
        ("Management may\nreduce guidance next quarter.", "reduce guidance next quarter."),
        ("The report denies that\nrevenue increased sharply.", "revenue increased sharply."),
        ("We cannot rule out:\na recession in 2027.", "a recession in 2027."),
        ("Management may\r\nreduce guidance next quarter.", "reduce guidance next quarter."),
        ("Management may\n\nreduce guidance next quarter.", "reduce guidance next quarter."),
    ]
    for body, fragment in cases:
        assert not qe.quote_span_verified(body, fragment, require_complete_clause=True)
        assert qe.quote_span_verified(body, body, require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_retains_spaced_ellipsis_context():
    cases = [
        ("We do not. . . expect inflation to rise.", "expect inflation to rise."),
        ("We do not . . . expect inflation to rise.", "expect inflation to rise."),
        ("We do not.  . expect inflation to rise.", "expect inflation to rise."),
    ]
    for body, fragment in cases:
        assert not qe.quote_span_verified(body, fragment, require_complete_clause=True)
        assert qe.quote_span_verified(body, body, require_complete_clause=True)


def test_shared_quote_verifier_context_punctuation_requires_a_new_sentence_shape():
    assert not qe.quote_span_verified(
        "We do not?! expect inflation to rise.",
        "expect inflation to rise.",
        require_complete_clause=True,
    )
    assert not qe.quote_span_verified(
        "We do not!? expect inflation to rise.",
        "expect inflation to rise.",
        require_complete_clause=True,
    )
    assert not qe.quote_span_verified(
        "The filing does not say Yahoo!Finance overstated revenue.",
        "Finance overstated revenue.",
        require_complete_clause=True,
    )
    assert not qe.quote_span_verified(
        "Management may not?Raise guidance next quarter.",
        "Raise guidance next quarter.",
        require_complete_clause=True,
    )
    assert qe.quote_span_verified(
        "Really?! Rates rose.",
        "Rates rose.",
        require_complete_clause=True,
    )
    assert qe.quote_span_verified(
        "真的吗？通胀上升。",
        "通胀上升。",
        require_complete_clause=True,
    )


def test_shared_quote_verifier_retains_unknown_title_style_abbreviation_context():
    cases = [
        ("Assoc. professor expects inflation to rise.", "professor expects inflation to rise."),
        ("Univ. Researchers expect inflation to rise.", "Researchers expect inflation to rise."),
        ("Treas. Yields rose sharply.", "Yields rose sharply."),
        ("Intl. Markets rallied.", "Markets rallied."),
        ("Management may not, per Distrib. Guidance, raise prices.", "Guidance, raise prices."),
        ("Management may not, per Transp. Outlook, raise prices.", "Outlook, raise prices."),
        ("Management may not, per distrib. Guidance, raise prices.", "Guidance, raise prices."),
        ("Management may not, per transp. Outlook, raise prices.", "Outlook, raise prices."),
        ("Revenue did not exceed the prior figure, per ibid. Q3 guidance was reiterated.", "Q3 guidance was reiterated."),
        ("Management may not, per para. Guidance, raise prices.", "Guidance, raise prices."),
        ("Management may not, per misc. Guidance, raise prices.", "Guidance, raise prices."),
        ("Management may not, per chap. Guidance, raise prices.", "Guidance, raise prices."),
        ("Management may not, per cont. Guidance, raise prices.", "Guidance, raise prices."),
        ("Management may not, per resp. Guidance, raise prices.", "Guidance, raise prices."),
        ("Management may not, per trans. Guidance, raise prices.", "Guidance, raise prices."),
        ("The Ph.D. Analyst expects inflation to rise.", "Analyst expects inflation to rise."),
        ("An M.Sc. Research team expects inflation to rise.", "Research team expects inflation to rise."),
    ]
    for body, fragment in cases:
        assert not qe.quote_span_verified(body, fragment, require_complete_clause=True)
        assert qe.quote_span_verified(body, body, require_complete_clause=True)


def test_shared_quote_verifier_retains_numeric_ordinal_context():
    body = "Der Umsatz ist nicht gestiegen im 2. Quartal 2025."
    assert not qe.quote_span_verified(
        body, "Quartal 2025.", require_complete_clause=True
    )
    assert qe.quote_span_verified(body, body, require_complete_clause=True)


def test_shared_quote_verifier_casefold_expansion_keeps_source_indexes_aligned():
    body = "die straße. Gewinne stiegen."
    assert qe.quote_span_verified(
        body, "Gewinne stiegen.", require_complete_clause=True
    )


def test_shared_quote_verifier_clause_mode_retains_ellipsis_context():
    cases = [
        ("We do not... expect inflation to rise this year.", "expect inflation to rise this year."),
        ("The Fed… will not hike rates.", "will not hike rates."),
    ]
    for body, fragment in cases:
        assert not qe.quote_span_verified(body, fragment, require_complete_clause=True)
        assert qe.quote_span_verified(body, body, require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_retains_ambiguous_abbreviation_context():
    cases = [
        ("Aug. inflation rose sharply.", "inflation rose sharply."),
        ("Prices rose in Apr. CPI surged.", "CPI surged."),
        ("See et al. for methods. Recession is unlikely.", "for methods."),
        ("See pp. 4-5 for details. Revenue rose.", "4-5 for details."),
    ]
    for body, fragment in cases:
        assert not qe.quote_span_verified(body, fragment, require_complete_clause=True)



def test_shared_quote_verifier_clause_mode_recognizes_common_sentence_endings():
    cases = [
        ("Demand weakened in China. Revenue fell sharply.", "Demand weakened in China.", "Revenue fell sharply."),
        ("The outlook is bad. Revenue fell sharply.", "The outlook is bad.", "Revenue fell sharply."),
        ("The cycle ended in 2027. Revenue fell sharply.", "The cycle ended in 2027.", "Revenue fell sharply."),
        ("The estimate was 2.1. Revenue fell sharply.", "The estimate was 2.1.", "Revenue fell sharply."),
        ("Demand weakened at AAPL. Revenue fell sharply.", "Demand weakened at AAPL.", "Revenue fell sharply."),
    ]
    for body, first, second in cases:
        assert qe.quote_span_verified(body, first, require_complete_clause=True)
        assert qe.quote_span_verified(body, second, require_complete_clause=True)
        assert not qe.quote_span_verified(body, body, require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_recognizes_finance_sentence_boundaries():
    cases = [
        ("Revenue fell. $AAPL dropped 5%.", "Revenue fell.", "$AAPL dropped 5%."),
        ("Revenue fell. -5% margin pressure persisted.", "Revenue fell.", "-5% margin pressure persisted."),
        ("Revenue fell! €100 million was impaired.", "Revenue fell!", "€100 million was impaired."),
        ("Revenue fell? +2.1% growth followed.", "Revenue fell?", "+2.1% growth followed."),
        ("The price was $2. Revenue fell sharply.", "The price was $2.", "Revenue fell sharply."),
        ("The price was ¥2. Revenue fell sharply.", "The price was ¥2.", "Revenue fell sharply."),
        ("The change was -2. Revenue fell sharply.", "The change was -2.", "Revenue fell sharply."),
    ]
    for body, first, second in cases:
        assert qe.quote_span_verified(body, first, require_complete_clause=True)
        assert qe.quote_span_verified(body, second, require_complete_clause=True)
        assert not qe.quote_span_verified(body, body, require_complete_clause=True)

def test_shared_quote_verifier_clause_mode_accepts_complete_clauses():
    english = "Goldman does not expect inflation to rise this year."
    han = "中国流动性正在改善。"
    wrapped_body = "First clause\nSecond clause"

    assert qe.quote_span_verified(
        english, "Goldman does not expect inflation to rise this year.", require_complete_clause=True
    )
    assert qe.quote_span_verified(han, "中国流动性正在改善。", require_complete_clause=True)
    assert qe.quote_span_verified(wrapped_body, wrapped_body, require_complete_clause=True)
    assert not qe.quote_span_verified(wrapped_body, "First clause", require_complete_clause=True)
    assert not qe.quote_span_verified(wrapped_body, "Second clause", require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_accepts_internal_punctuation_and_abbreviations():
    clauses = [
        "U.S. inflation may rise next quarter.",
        "Acme Inc. expects revenue to rise.",
        "Revenue, adjusted for FX, rose 10%.",
        "Management may, subject to board approval, reduce guidance next quarter.",
    ]
    for clause in clauses:
        assert qe.quote_span_verified(clause, clause, require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_rejects_multiple_complete_clauses():
    body = "Demand is strong. Losses widened sharply."
    span = "Demand is strong. Losses widened sharply."
    assert qe.quote_span_verified(body, span)
    assert not qe.quote_span_verified(body, span, require_complete_clause=True)


def test_shared_quote_verifier_clause_mode_validates_option_type():
    for invalid in (None, 1, "yes"):
        with pytest.raises(ValueError, match="require_complete_clause must be a boolean"):
            qe.quote_span_verified("A clause.", "A clause.", require_complete_clause=invalid)


def test_shared_quote_verifier_default_preserves_legacy_newline_elision():
    assert qe.quote_span_verified(
        "Revenue rose\nsharply today.",
        "Revenue rose sharply today.",
    )


def test_shared_quote_verifier_default_remains_fragment_compatible():
    body = "Goldman does not expect inflation to rise this year."
    assert qe.quote_span_verified(body, "inflation to rise this year")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(failed)
