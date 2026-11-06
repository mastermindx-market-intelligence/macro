"""A31 view-state-guard tests: EN/ZH and viewport transitions preserve identity.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings and view-state mappings from the product page state owner; they
never mint issuer or security ids. HISTORICAL-DESCRIPTIVE only:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures
are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_view_state_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    AXES,
    LANGS,
    REASONS,
    VIEWPORTS,
    ViewTransitionVerdict,
    check_view_transition,
    persist_across,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_view_state_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

ISSUER_ID = "SYN-ISSUER-1"
COUNTER_ID = "SYN-CTR-A"
LENS = "SYN-LENS-1"
AS_OF = "2026-10-13T08:00:00+00:00"
AS_OF_REFORMATTED = "2026-10-13T16:00:00+08:00"

US_TICKER_LITERALS = (
    "BABA",
    "TCEHY",
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
)


class _Omit:
    pass


_OMIT = _Omit()


def _base(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "counter_id": COUNTER_ID,
        "lens": LENS,
        "as_of": AS_OF,
        "lang": "en",
        "viewport": "desktop",
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _after(before, **overrides):
    body = dict(before)
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _assert_contract(verdict: ViewTransitionVerdict) -> None:
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
        assert verdict.authority_flags[name] is not True
    if verdict.allowed:
        assert verdict.reasons == ()
    else:
        assert verdict.allowed is False
        assert verdict.reasons
    for axis in verdict.changed_axes:
        assert axis in AXES, (axis, verdict.changed_axes)
    assert list(verdict.changed_axes) == [
        axis for axis in AXES if axis in verdict.changed_axes
    ]


def _assert_refused(verdict: ViewTransitionVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_allowed(verdict: ViewTransitionVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_only(verdict: ViewTransitionVerdict, code: str) -> None:
    _assert_refused(verdict, code)
    assert verdict.reasons == (code,), verdict.reasons


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_a31_positive_lang_en_to_zh():
    before = _base(lang="en")
    after = persist_across(before, lang="zh")
    verdict = check_view_transition(before, after, change="lang")
    _assert_allowed(verdict)
    assert verdict.changed_axes == ("lang",)
    assert LANGS == ("en", "zh")


def test_a31_positive_lang_zh_to_en():
    before = _base(lang="zh")
    after = persist_across(before, lang="en")
    verdict = check_view_transition(before, after, change="lang")
    _assert_allowed(verdict)
    assert verdict.changed_axes == ("lang",)


def test_a31_positive_viewport_desktop_to_mobile():
    before = _base(viewport="desktop")
    after = persist_across(before, viewport="mobile")
    verdict = check_view_transition(before, after, change="viewport")
    _assert_allowed(verdict)
    assert verdict.changed_axes == ("viewport",)
    assert VIEWPORTS == ("desktop", "tablet", "mobile")


def test_a31_positive_viewport_desktop_to_tablet():
    before = _base(viewport="desktop")
    after = persist_across(before, viewport="tablet")
    verdict = check_view_transition(before, after, change="viewport")
    _assert_allowed(verdict)
    assert verdict.changed_axes == ("viewport",)


def test_a31_positive_viewport_tablet_to_mobile():
    before = _base(viewport="tablet")
    after = persist_across(before, viewport="mobile")
    verdict = check_view_transition(before, after, change="viewport")
    _assert_allowed(verdict)
    assert verdict.changed_axes == ("viewport",)


def test_a31_positive_zero_change():
    before = _base()
    after = dict(before)
    verdict = check_view_transition(before, after, change=None)
    _assert_allowed(verdict)
    assert verdict.changed_axes == ()


def test_a31_positive_zero_change_declared_lang():
    before = _base()
    after = dict(before)
    verdict = check_view_transition(before, after, change="lang")
    _assert_allowed(verdict)
    assert verdict.changed_axes == ()


def test_a31_positive_declared_issuer_id_change():
    before = _base()
    after = _after(before, issuer_id="SYN-ISSUER-2")
    verdict = check_view_transition(before, after, change="issuer_id")
    _assert_allowed(verdict)
    assert verdict.changed_axes == ("issuer_id",)


# ---------------------------------------------------------------------------
# One single-flip test per REASONS entry
# ---------------------------------------------------------------------------


def test_a31_reason_field_missing():
    before = _base(issuer_id="")
    after = _base(issuer_id="")
    verdict = check_view_transition(before, after, change=None)
    _assert_only(verdict, "FIELD_MISSING")
    assert verdict.changed_axes == ()


def test_a31_reason_lang_unknown():
    before = _base()
    after = _after(before, lang="fr")
    verdict = check_view_transition(before, after, change="lang")
    _assert_only(verdict, "LANG_UNKNOWN")
    assert verdict.changed_axes == ("lang",)


def test_a31_reason_viewport_unknown():
    before = _base()
    after = _after(before, viewport="watch")
    verdict = check_view_transition(before, after, change="viewport")
    _assert_only(verdict, "VIEWPORT_UNKNOWN")
    assert verdict.changed_axes == ("viewport",)


def test_a31_reason_change_undeclared():
    before = _base(lang="en")
    after = persist_across(before, lang="zh")
    verdict = check_view_transition(before, after, change=None)
    _assert_only(verdict, "CHANGE_UNDECLARED")
    assert verdict.changed_axes == ("lang",)


def test_a31_reason_multiple_axes_changed():
    before = _base()
    after = persist_across(before, lang="zh", viewport="mobile")
    verdict = check_view_transition(before, after, change="lang")
    _assert_refused(verdict, "MULTIPLE_AXES_CHANGED")
    assert "CHANGE_UNDECLARED" in verdict.reasons
    assert verdict.changed_axes == ("lang", "viewport")


def test_a31_reason_issuer_changed():
    before = _base()
    after = _after(before, issuer_id="SYN-ISSUER-2")
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "ISSUER_CHANGED")
    assert "CHANGE_UNDECLARED" in verdict.reasons
    assert verdict.changed_axes == ("issuer_id",)


def test_a31_reason_counter_changed():
    before = _base()
    after = _after(before, counter_id="SYN-CTR-B")
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "COUNTER_CHANGED")
    assert "CHANGE_UNDECLARED" in verdict.reasons
    assert verdict.changed_axes == ("counter_id",)


def test_a31_reason_lens_changed():
    before = _base()
    after = _after(before, lens="SYN-LENS-2")
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "LENS_CHANGED")
    assert "CHANGE_UNDECLARED" in verdict.reasons
    assert verdict.changed_axes == ("lens",)


def test_a31_reason_as_of_changed():
    before = _base()
    after = _after(before, as_of="2026-10-13T09:00:00+00:00")
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "AS_OF_CHANGED")
    assert "CHANGE_UNDECLARED" in verdict.reasons
    assert verdict.changed_axes == ("as_of",)


# ---------------------------------------------------------------------------
# persist_across round trips
# ---------------------------------------------------------------------------


def test_a31_roundtrip_lang_en_zh_en():
    original = _base(lang="en")
    zh = persist_across(original, lang="zh")
    back = persist_across(zh, lang="en")
    assert back == original
    mid = check_view_transition(original, zh, change="lang")
    _assert_allowed(mid)
    assert mid.changed_axes == ("lang",)
    end = check_view_transition(zh, back, change="lang")
    _assert_allowed(end)
    assert end.changed_axes == ("lang",)


def test_a31_roundtrip_viewport_desktop_mobile_desktop():
    original = _base(viewport="desktop")
    mobile = persist_across(original, viewport="mobile")
    back = persist_across(mobile, viewport="desktop")
    assert back == original
    mid = check_view_transition(original, mobile, change="viewport")
    _assert_allowed(mid)
    assert mid.changed_axes == ("viewport",)
    end = check_view_transition(mobile, back, change="viewport")
    _assert_allowed(end)
    assert end.changed_axes == ("viewport",)


def test_a31_persist_across_only_replaces_lang():
    before = _base()
    out = persist_across(before, lang="zh")
    assert out["lang"] == "zh"
    assert out["viewport"] == before["viewport"]
    assert out["issuer_id"] == before["issuer_id"]
    assert out["counter_id"] == before["counter_id"]
    assert out["lens"] == before["lens"]
    assert out["as_of"] == before["as_of"]


def test_a31_persist_across_only_replaces_viewport():
    before = _base()
    out = persist_across(before, viewport="tablet")
    assert out["viewport"] == "tablet"
    assert out["lang"] == before["lang"]
    assert out["issuer_id"] == before["issuer_id"]
    assert out["counter_id"] == before["counter_id"]
    assert out["lens"] == before["lens"]
    assert out["as_of"] == before["as_of"]


def test_a31_persist_across_preserves_other_keys():
    before = _base()
    before["owner_note"] = "SYN-NOTE"
    out = persist_across(before, lang="zh")
    assert out["owner_note"] == "SYN-NOTE"
    assert set(out) == set(before) | {"lang"}
    assert out["lang"] == "zh"


def test_a31_persist_across_does_not_mutate_before():
    before = _base()
    snapshot = copy.deepcopy(before)
    persist_across(before, lang="zh", viewport="mobile")
    assert before == snapshot


# ---------------------------------------------------------------------------
# as_of exact-string law
# ---------------------------------------------------------------------------


def test_a31_as_of_format_change_refuses():
    before = _base(as_of=AS_OF)
    after = persist_across(before, lang="zh")
    after["as_of"] = AS_OF_REFORMATTED
    verdict = check_view_transition(before, after, change="lang")
    _assert_refused(
        verdict,
        "CHANGE_UNDECLARED",
        "MULTIPLE_AXES_CHANGED",
        "AS_OF_CHANGED",
    )
    assert verdict.changed_axes == ("as_of", "lang")
    assert verdict.reasons == (
        "CHANGE_UNDECLARED",
        "MULTIPLE_AXES_CHANGED",
        "AS_OF_CHANGED",
    )


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def test_a31_refuse_nonfalse_authority():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"gate_authority": 0})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"size_authority": None})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"signal_authority": ""})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"escalation_authority": 0})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority(
            {
                "rank_authority": False,
                "gate_authority": False,
                "size_authority": False,
                "signal_authority": False,
                "escalation_authority": False,
                "trade_authority": True,
            }
        )
    for name in FLAG_NAMES:
        one = dict(AUTHORITY_FLAGS)
        one[name] = True
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)
        one[name] = 0
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)
        one[name] = None
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)
        one[name] = ""
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)


def test_a31_authority_flags_immutable():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["trade_authority"] = False
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
        assert AUTHORITY_FLAGS[name] is not 0  # noqa: F632
        assert AUTHORITY_FLAGS[name] is not None


def test_a31_verdict_authority_flags_property():
    allowed = check_view_transition(_base(), _base(), change=None)
    refused = check_view_transition(
        _base(),
        persist_across(_base(), lang="zh"),
        change=None,
    )
    for verdict in (allowed, refused):
        assert verdict.authority_flags is AUTHORITY_FLAGS
        for name in FLAG_NAMES:
            assert verdict.authority_flags[name] is False


def test_a31_allowed_true_iff_reasons_empty():
    allowed = check_view_transition(_base(), _base(), change=None)
    assert allowed.allowed is True
    assert allowed.reasons == ()
    coerced = ViewTransitionVerdict(
        allowed=True,
        reasons=("FIELD_MISSING",),
        changed_axes=(),
    )
    assert coerced.allowed is False
    assert coerced.reasons == ("FIELD_MISSING",)


# ---------------------------------------------------------------------------
# Static source contract
# ---------------------------------------------------------------------------


def test_a31_module_source_reasons_and_no_tickers():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    for ticker in US_TICKER_LITERALS:
        assert ticker not in source, ticker
    for needle in ("datetime.now", "utcnow", "date.today", "time.time", "open("):
        assert needle not in source, needle


def test_a31_reasons_tuple_order_and_unique():
    assert AXES == (
        "issuer_id",
        "counter_id",
        "lens",
        "as_of",
        "lang",
        "viewport",
    )
    assert LANGS == ("en", "zh")
    assert VIEWPORTS == ("desktop", "tablet", "mobile")
    assert REASONS == (
        "FIELD_MISSING",
        "LANG_UNKNOWN",
        "VIEWPORT_UNKNOWN",
        "CHANGE_UNDECLARED",
        "MULTIPLE_AXES_CHANGED",
        "ISSUER_CHANGED",
        "COUNTER_CHANGED",
        "LENS_CHANGED",
        "AS_OF_CHANGED",
    )
    assert len(REASONS) == len(set(REASONS))
    assert len(REASONS) == 9


# ---------------------------------------------------------------------------
# De-dup and REASONS order
# ---------------------------------------------------------------------------


def test_a31_verdict_dedup_and_order():
    before = _base()
    after = _after(
        before,
        issuer_id="SYN-ISSUER-2",
        counter_id="SYN-CTR-B",
        as_of="2026-10-13T09:00:00+00:00",
    )
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(
        verdict,
        "CHANGE_UNDECLARED",
        "MULTIPLE_AXES_CHANGED",
        "ISSUER_CHANGED",
        "COUNTER_CHANGED",
        "AS_OF_CHANGED",
    )
    assert verdict.reasons == (
        "CHANGE_UNDECLARED",
        "MULTIPLE_AXES_CHANGED",
        "ISSUER_CHANGED",
        "COUNTER_CHANGED",
        "AS_OF_CHANGED",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))
    assert verdict.changed_axes == ("issuer_id", "counter_id", "as_of")


def test_a31_changed_axes_in_axes_order():
    before = _base()
    after = _after(before, viewport="mobile", lang="zh", lens="SYN-LENS-2")
    verdict = check_view_transition(before, after, change=None)
    assert verdict.changed_axes == ("lens", "lang", "viewport")
    _assert_refused(verdict, "MULTIPLE_AXES_CHANGED", "LENS_CHANGED")


# ---------------------------------------------------------------------------
# Adversarial id cases (exact string; no case-fold/strip/normalise)
# ---------------------------------------------------------------------------


def test_a31_issuer_trailing_space():
    before = _base()
    after = _after(before, issuer_id=ISSUER_ID + " ")
    verdict = check_view_transition(before, after, change=None)
    # FAMILY TEXT RULE v2: a padded id is ABSENT, never a different valid id.
    _assert_only(verdict, "FIELD_MISSING")
    assert verdict.changed_axes == ()


def test_a31_issuer_case_mismatch():
    before = _base()
    after = _after(before, issuer_id="syn-issuer-1")
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "ISSUER_CHANGED")
    assert verdict.changed_axes == ("issuer_id",)


def test_a31_issuer_cyrillic_lookalike():
    latin = "SYN-ISSUERa"
    cyrillic = "SYN-ISSUER" + "\u0430"
    assert latin != cyrillic
    before = _base(issuer_id=latin)
    after = _after(before, issuer_id=cyrillic)
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "ISSUER_CHANGED")
    assert verdict.changed_axes == ("issuer_id",)


def test_a31_counter_trailing_space():
    before = _base()
    after = _after(before, counter_id=COUNTER_ID + " ")
    verdict = check_view_transition(before, after, change=None)
    # FAMILY TEXT RULE v2: a padded id is ABSENT, never a different valid id.
    _assert_only(verdict, "FIELD_MISSING")
    assert verdict.changed_axes == ()


def test_a31_counter_case_mismatch():
    before = _base()
    after = _after(before, counter_id="syn-ctr-a")
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "COUNTER_CHANGED")
    assert verdict.changed_axes == ("counter_id",)


def test_a31_counter_cyrillic_lookalike():
    latin = "SYN-CTRa"
    cyrillic = "SYN-CTR" + "\u0430"
    assert latin != cyrillic
    before = _base(counter_id=latin)
    after = _after(before, counter_id=cyrillic)
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "COUNTER_CHANGED")
    assert verdict.changed_axes == ("counter_id",)


# ---------------------------------------------------------------------------
# Additional field / lang / viewport edges
# ---------------------------------------------------------------------------


def test_a31_field_missing_omitted_key():
    before = _base(lens=_OMIT)
    after = _base(lens=_OMIT)
    verdict = check_view_transition(before, after, change=None)
    _assert_only(verdict, "FIELD_MISSING")


def test_a31_blank_lang_field_missing_and_unknown():
    before = _base(lang="")
    after = _base(lang="")
    verdict = check_view_transition(before, after, change=None)
    _assert_refused(verdict, "FIELD_MISSING", "LANG_UNKNOWN")
    assert verdict.reasons == ("FIELD_MISSING", "LANG_UNKNOWN")


def test_a31_lang_trailing_space_unknown():
    before = _base()
    after = _after(before, lang="en ")
    verdict = check_view_transition(before, after, change="lang")
    # FAMILY TEXT RULE v2: a padded lang is ABSENT as well as unknown.
    _assert_refused(verdict, "FIELD_MISSING", "LANG_UNKNOWN")
    assert verdict.reasons == ("FIELD_MISSING", "LANG_UNKNOWN")


def test_a31_viewport_case_unknown():
    before = _base()
    after = _after(before, viewport="Desktop")
    verdict = check_view_transition(before, after, change="viewport")
    _assert_only(verdict, "VIEWPORT_UNKNOWN")


def test_a31_undeclared_viewport_change():
    before = _base()
    after = persist_across(before, viewport="mobile")
    verdict = check_view_transition(before, after, change=None)
    _assert_only(verdict, "CHANGE_UNDECLARED")
    assert verdict.changed_axes == ("viewport",)


def test_a31_extra_keys_ignored():
    before = _base()
    before["owner_note"] = "SYN-NOTE-A"
    after = _base()
    after["owner_note"] = "SYN-NOTE-B"
    verdict = check_view_transition(before, after, change=None)
    _assert_allowed(verdict)
    assert verdict.changed_axes == ()


def test_a31_lang_change_with_silent_issuer_refuses():
    before = _base()
    after = persist_across(before, lang="zh")
    after["issuer_id"] = "SYN-ISSUER-2"
    verdict = check_view_transition(before, after, change="lang")
    _assert_refused(
        verdict,
        "CHANGE_UNDECLARED",
        "MULTIPLE_AXES_CHANGED",
        "ISSUER_CHANGED",
    )
    assert verdict.changed_axes == ("issuer_id", "lang")
