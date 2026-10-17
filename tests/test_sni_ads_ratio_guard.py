"""A01 ADS-ratio interval-guard tests: unsourced or unacked ratios refused.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings and depositary-ratio interval records (Stock Identity / Capital
Structure) and never mint issuer or security ids or ratios.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_ads_ratio_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    AdsRatioVerdict,
    check_ads_ratio,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_ads_ratio_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AS_OF = "2021-06-01T00:00:00+00:00"
AVAILABLE = "2019-07-10T00:00:00+00:00"

TICKERS = (
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


def _record(**overrides):
    rec = {
        "ratio_record_id": "rr-001",
        "issuer_id": "iss-001",
        "ordinary_per_ads": 8,
        "valid_from": "2010-01-01",
        "valid_to": "2019-07-10",
        "source_ref": "src-cs-001",
        "available_at": AVAILABLE,
    }
    rec.update(overrides)
    drop = [key for key, val in rec.items() if val is _OMIT]
    for key in drop:
        del rec[key]
    return rec


def _later(**overrides):
    rec = _record(
        ratio_record_id="rr-002",
        ordinary_per_ads=4,
        valid_from="2019-07-10",
        valid_to=None,
        source_ref="src-cs-002",
    )
    rec.update(overrides)
    drop = [key for key, val in rec.items() if val is _OMIT]
    for key in drop:
        del rec[key]
    return rec


def _mid(**overrides):
    rec = _record(
        ratio_record_id="rr-003",
        ordinary_per_ads=8,
        valid_from="2015-01-01",
        valid_to="2019-07-10",
        source_ref="src-cs-003",
    )
    rec.update(overrides)
    drop = [key for key, val in rec.items() if val is _OMIT]
    for key in drop:
        del rec[key]
    return rec


def _early_split(**overrides):
    rec = _record(
        valid_from="2010-01-01",
        valid_to="2015-01-01",
    )
    rec.update(overrides)
    drop = [key for key, val in rec.items() if val is _OMIT]
    for key in drop:
        del rec[key]
    return rec


def _request(**overrides):
    req = {
        "issuer_id": "iss-001",
        "on_date": "2020-01-15",
        "acknowledged_ratio_changes": (),
    }
    req.update(overrides)
    drop = [key for key, val in req.items() if val is _OMIT]
    for key in drop:
        del req[key]
    return req


def _positive_records():
    return [_record(), _later()]


def _assert_contract(verdict: AdsRatioVerdict) -> None:
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    assert verdict.reasons == tuple(code for code in REASONS if code in set(verdict.reasons))
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
        assert verdict.authority_flags[name] is not True
    if verdict.allowed:
        assert verdict.reasons == ()
    else:
        assert verdict.reasons


def _assert_refused(verdict: AdsRatioVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_allowed(verdict: AdsRatioVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


# ---------------------------------------------------------------------------
# T1 positive controls
# ---------------------------------------------------------------------------


def test_a01g_positive_adjacent_second_interval():
    verdict = check_ads_ratio(_request(), _positive_records(), as_of=AS_OF)
    _assert_allowed(verdict)
    assert verdict.ratio_record_id == "rr-002"
    assert verdict.ordinary_per_ads == 4


def test_a01g_positive_ratio_change_acknowledged():
    req = _request(
        window_start="2012-06-01",
        acknowledged_ratio_changes=("rr-002",),
    )
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_allowed(verdict)
    assert verdict.ratio_record_id == "rr-002"
    assert verdict.ordinary_per_ads == 4


def test_a01g_positive_same_interval_window():
    req = _request(window_start="2019-12-01")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_allowed(verdict)
    assert verdict.ratio_record_id == "rr-002"


# ---------------------------------------------------------------------------
# T2 one single-flip test per REASON
# ---------------------------------------------------------------------------


def test_a01g_reason_ratio_records_missing():
    verdict = check_ads_ratio(_request(), [], as_of=AS_OF)
    _assert_refused(verdict, "RATIO_RECORDS_MISSING")
    assert verdict.ratio_record_id is None
    assert verdict.ordinary_per_ads is None


def test_a01g_reason_ratio_records_none():
    verdict = check_ads_ratio(_request(), None, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_RECORDS_MISSING")


def test_a01g_reason_ratio_record_unsourced():
    recs = [_record(source_ref=""), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_RECORD_UNSOURCED")


def test_a01g_reason_unsourced_blank_ratio_record_id():
    recs = [_record(ratio_record_id=""), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_RECORD_UNSOURCED")


def test_a01g_reason_ratio_nonpositive():
    recs = [_record(ordinary_per_ads=0), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NONPOSITIVE")


def test_a01g_reason_interval_invalid():
    recs = [_record(valid_to="2010-01-01"), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "INTERVAL_INVALID")


def test_a01g_reason_interval_overlap():
    recs = [_record(valid_to="2019-07-11"), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "INTERVAL_OVERLAP")
    assert verdict.ratio_record_id == "rr-002"
    assert verdict.ordinary_per_ads == 4


def test_a01g_reason_issuer_mismatch():
    recs = [_record(issuer_id="iss-002"), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "ISSUER_MISMATCH")
    assert verdict.ratio_record_id == "rr-002"


def test_a01g_reason_date_invalid():
    req = _request(on_date="2020-01-15T00:00:00")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "DATE_INVALID")


def test_a01g_reason_date_invalid_window_after_on_date():
    req = _request(window_start="2021-01-01")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "DATE_INVALID")


def test_a01g_reason_no_interval_covers_date():
    req = _request(on_date="2000-01-01")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "NO_INTERVAL_COVERS_DATE")
    assert verdict.ratio_record_id is None
    assert verdict.ordinary_per_ads is None


def test_a01g_reason_ratio_not_available_as_of():
    recs = [_record(), _later(available_at="2021-06-02T00:00:00+00:00")]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NOT_AVAILABLE_AS_OF")
    assert verdict.ratio_record_id == "rr-002"


def test_a01g_reason_ratio_change_unacknowledged():
    req = _request(window_start="2012-06-01")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "RATIO_CHANGE_UNACKNOWLEDGED")
    assert verdict.ratio_record_id == "rr-002"
    assert verdict.ordinary_per_ads == 4


# ---------------------------------------------------------------------------
# Adjacency, open-ended, acknowledged change
# ---------------------------------------------------------------------------


def test_a01g_adjacency_boundary_picks_later():
    boundary = check_ads_ratio(
        _request(on_date="2019-07-10"), _positive_records(), as_of=AS_OF
    )
    _assert_allowed(boundary)
    assert boundary.ratio_record_id == "rr-002"
    assert boundary.ordinary_per_ads == 4
    before = check_ads_ratio(
        _request(on_date="2019-07-09"), _positive_records(), as_of=AS_OF
    )
    _assert_allowed(before)
    assert before.ratio_record_id == "rr-001"
    assert before.ordinary_per_ads == 8


def test_a01g_open_ended_covers_far_future():
    verdict = check_ads_ratio(
        _request(on_date="2099-12-31"), _positive_records(), as_of=AS_OF
    )
    _assert_allowed(verdict)
    assert verdict.ratio_record_id == "rr-002"
    assert verdict.ordinary_per_ads == 4


def test_a01g_ratio_change_refused_without_ack():
    req = _request(
        window_start="2012-06-01",
        acknowledged_ratio_changes=(),
    )
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "RATIO_CHANGE_UNACKNOWLEDGED")


def test_a01g_ratio_change_allowed_with_ack():
    req = _request(
        window_start="2012-06-01",
        acknowledged_ratio_changes=("rr-002", "rr-other"),
    )
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_allowed(verdict)


def test_a01g_ack_of_window_record_does_not_cover_on_date_change():
    req = _request(
        window_start="2012-06-01",
        acknowledged_ratio_changes=("rr-001",),
    )
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "RATIO_CHANGE_UNACKNOWLEDGED")


# ---------------------------------------------------------------------------
# Permutation invariance
# ---------------------------------------------------------------------------


def test_a01g_permutation_invariance():
    recs = [_early_split(), _mid(), _later()]
    req = _request()
    base = check_ads_ratio(req, recs, as_of=AS_OF)
    _assert_allowed(base)
    assert base.ratio_record_id == "rr-002"
    for perm in itertools.permutations(recs):
        got = check_ads_ratio(req, perm, as_of=AS_OF)
        assert got == base
        assert got.allowed is True
        assert got.reasons == ()
        assert got.ratio_record_id == "rr-002"
        assert got.ordinary_per_ads == 4


def test_a01g_permutation_invariance_refused():
    recs = [
        _early_split(source_ref=""),
        _mid(ordinary_per_ads=0),
        _later(issuer_id="iss-002"),
    ]
    req = _request()
    base = check_ads_ratio(req, recs, as_of=AS_OF)
    _assert_refused(
        base,
        "RATIO_RECORD_UNSOURCED",
        "RATIO_NONPOSITIVE",
        "ISSUER_MISMATCH",
        "NO_INTERVAL_COVERS_DATE",
    )
    for perm in itertools.permutations(recs):
        got = check_ads_ratio(req, perm, as_of=AS_OF)
        assert got == base
        assert got.reasons == base.reasons


# ---------------------------------------------------------------------------
# ordinary_per_ads refused shapes
# ---------------------------------------------------------------------------


def test_a01g_ordinary_per_ads_true():
    recs = [_record(ordinary_per_ads=True), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NONPOSITIVE")


def test_a01g_ordinary_per_ads_str():
    recs = [_record(ordinary_per_ads="2"), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NONPOSITIVE")


def test_a01g_ordinary_per_ads_zero():
    recs = [_record(ordinary_per_ads=0), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NONPOSITIVE")


def test_a01g_ordinary_per_ads_negative():
    recs = [_record(ordinary_per_ads=-1), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NONPOSITIVE")


def test_a01g_ordinary_per_ads_nan():
    recs = [_record(ordinary_per_ads=float("nan")), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NONPOSITIVE")


def test_a01g_ordinary_per_ads_inf():
    recs = [_record(ordinary_per_ads=float("inf")), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NONPOSITIVE")


# ---------------------------------------------------------------------------
# available_at vs as_of
# ---------------------------------------------------------------------------


def test_a01g_available_at_equal_as_of_allowed():
    recs = [_record(), _later(available_at=AS_OF)]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_allowed(verdict)
    assert verdict.ratio_record_id == "rr-002"


def test_a01g_available_at_one_microsecond_after_refused():
    recs = [
        _record(),
        _later(available_at="2021-06-01T00:00:00.000001+00:00"),
    ]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NOT_AVAILABLE_AS_OF")


def test_a01g_available_at_naive_refused():
    recs = [_record(), _later(available_at="2019-07-10T00:00:00")]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NOT_AVAILABLE_AS_OF")


def test_a01g_as_of_naive_refused():
    verdict = check_ads_ratio(
        _request(), _positive_records(), as_of="2021-06-01T00:00:00"
    )
    _assert_refused(verdict, "RATIO_NOT_AVAILABLE_AS_OF")


def test_a01g_available_at_missing_refused():
    recs = [_record(), _later(available_at=_OMIT)]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "RATIO_NOT_AVAILABLE_AS_OF")


# ---------------------------------------------------------------------------
# T3 authority
# ---------------------------------------------------------------------------


def test_a01g_authority_refuse_nonfalse():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    for bad in (True, 0, None, ""):
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({"rank_authority": bad})
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({"trade_authority": bad})


def test_a01g_authority_flags_literal_false():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
    verdict = check_ads_ratio(_request(), _positive_records(), as_of=AS_OF)
    assert verdict.authority_flags is AUTHORITY_FLAGS
    _assert_contract(verdict)
    refused = check_ads_ratio(_request(), [], as_of=AS_OF)
    assert refused.authority_flags is AUTHORITY_FLAGS
    _assert_contract(refused)


def test_a01g_verdict_allowed_true_iff_reasons_empty():
    allowed = check_ads_ratio(_request(), _positive_records(), as_of=AS_OF)
    assert allowed.allowed is True
    assert allowed.reasons == ()
    forced = AdsRatioVerdict(
        allowed=True,
        reasons=("RATIO_RECORDS_MISSING",),
        ratio_record_id=None,
        ordinary_per_ads=None,
    )
    assert forced.allowed is False
    assert forced.reasons == ("RATIO_RECORDS_MISSING",)


# ---------------------------------------------------------------------------
# T4 static scan
# ---------------------------------------------------------------------------


def test_a01g_static_scan():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    for ticker in TICKERS:
        assert ticker not in source, ticker
    for needle in (
        "datetime.now",
        "utcnow",
        "date.today",
        "time.time",
        "open(",
    ):
        assert needle not in source, needle
    assert REASONS == (
        "RATIO_RECORDS_MISSING",
        "RATIO_RECORD_UNSOURCED",
        "RATIO_NONPOSITIVE",
        "INTERVAL_INVALID",
        "INTERVAL_OVERLAP",
        "ISSUER_MISMATCH",
        "DATE_INVALID",
        "NO_INTERVAL_COVERS_DATE",
        "RATIO_NOT_AVAILABLE_AS_OF",
        "RATIO_CHANGE_UNACKNOWLEDGED",
    )
    assert len(REASONS) == 10
    assert len(set(REASONS)) == 10


# ---------------------------------------------------------------------------
# T5 de-dup and order
# ---------------------------------------------------------------------------


def test_a01g_reasons_dedup_order():
    recs = [
        {
            "ratio_record_id": "",
            "issuer_id": "iss-002",
            "ordinary_per_ads": 0,
            "valid_from": "2010-01-01",
            "valid_to": "2009-01-01",
            "source_ref": "",
            "available_at": AVAILABLE,
        },
        {
            "ratio_record_id": "",
            "issuer_id": "iss-002",
            "ordinary_per_ads": 0,
            "valid_from": "2010-01-01",
            "valid_to": "2009-01-01",
            "source_ref": "",
            "available_at": AVAILABLE,
        },
    ]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(
        verdict,
        "RATIO_RECORD_UNSOURCED",
        "RATIO_NONPOSITIVE",
        "INTERVAL_INVALID",
        "ISSUER_MISMATCH",
        "NO_INTERVAL_COVERS_DATE",
    )
    assert verdict.reasons == (
        "RATIO_RECORD_UNSOURCED",
        "RATIO_NONPOSITIVE",
        "INTERVAL_INVALID",
        "ISSUER_MISMATCH",
        "NO_INTERVAL_COVERS_DATE",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))
    assert list(verdict.reasons) == [c for c in REASONS if c in set(verdict.reasons)]


# ---------------------------------------------------------------------------
# T6 adversarial ids
# ---------------------------------------------------------------------------


def test_a01g_adversarial_trailing_space():
    req = _request(issuer_id="iss-001 ")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "ISSUER_MISMATCH")
    recs = [_record(issuer_id="iss-001 "), _later(issuer_id="iss-001 ")]
    spaced = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(spaced, "ISSUER_MISMATCH")


def test_a01g_adversarial_case_change():
    req = _request(issuer_id="ISS-001")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "ISSUER_MISMATCH")
    recs = [_record(issuer_id="Iss-001"), _later(issuer_id="Iss-001")]
    cased = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(cased, "ISSUER_MISMATCH")


def test_a01g_adversarial_cyrillic_lookalike():
    lookalike = "iss-00" + "\u0430"
    req = _request(issuer_id=lookalike)
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "ISSUER_MISMATCH")
    recs = [
        _record(issuer_id="iss-" + "\u0430" + "aa"),
        _later(issuer_id="iss-" + "\u0430" + "aa"),
    ]
    req_latin = _request(issuer_id="iss-aaa")
    cyr = check_ads_ratio(req_latin, recs, as_of=AS_OF)
    _assert_refused(cyr, "ISSUER_MISMATCH")


def test_a01g_ack_trailing_space_does_not_match():
    req = _request(
        window_start="2012-06-01",
        acknowledged_ratio_changes=("rr-002 ",),
    )
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "RATIO_CHANGE_UNACKNOWLEDGED")


# ---------------------------------------------------------------------------
# covering fields when uncovered / record date invalid
# ---------------------------------------------------------------------------


def test_a01g_covering_fields_none_when_uncovered():
    verdict = check_ads_ratio(_request(on_date="2000-01-01"), _positive_records(), as_of=AS_OF)
    assert verdict.ratio_record_id is None
    assert verdict.ordinary_per_ads is None
    overlap_on_date = [
        _record(valid_to="2021-01-01"),
        _later(),
    ]
    two = check_ads_ratio(_request(), overlap_on_date, as_of=AS_OF)
    _assert_refused(two, "INTERVAL_OVERLAP")
    assert two.ratio_record_id is None
    assert two.ordinary_per_ads is None


def test_a01g_record_date_not_ten_char_iso():
    recs = [_record(valid_from="2010-1-01"), _later()]
    verdict = check_ads_ratio(_request(), recs, as_of=AS_OF)
    _assert_refused(verdict, "DATE_INVALID")


def test_a01g_window_malformed_date_invalid():
    req = _request(window_start="2012/06/01")
    verdict = check_ads_ratio(req, _positive_records(), as_of=AS_OF)
    _assert_refused(verdict, "DATE_INVALID")
