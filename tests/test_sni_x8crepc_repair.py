"""X8CREPC repair-r1 tests.

Closes X8C-03, 04, 05, 06, 07, 11 in the KPI-missingness and ADS-ratio
DRAFT guards. Each closed defect has exactly one ``test_r1_<nn>_<slug>``
case here. Existing tests in ``tests/test_sni_kpi_missingness_guard.py``
and ``tests/test_sni_ads_ratio_guard.py`` are not edited.

SNI-local DRAFT contract tests. They consume owner-supplied opaque
identity strings and KPI / depositary-ratio interval records and never
mint issuer or security ids or ratios. HISTORICAL-DESCRIPTIVE only:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures
are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import random
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_ads_ratio_guard as ads_mod  # noqa: E402
from sni_ads_ratio_guard import (  # noqa: E402
    REASONS as ADS_REASONS,
    AdsRatioVerdict,
    check_ads_ratio,
    refuse_nonfalse_authority,
)
import sni_kpi_missingness_guard as kpi_mod  # noqa: E402
from sni_kpi_missingness_guard import (  # noqa: E402
    REASONS as KPI_REASONS,
    KpiSeriesVerdict,
    check_kpi_series,
)


# --- Helpers / fixtures ----------------------------------------------------


ADS_PERIODS = {
    "issuer_id": "iss-x8crepc",
    "on_date": "2020-06-30",
}


def _ads_record(
    ratio_record_id="rr-001",
    issuer_id="iss-x8crepc",
    ordinary_per_ads=8,
    valid_from="2010-01-01",
    valid_to=None,
    source_ref="src-001",
    available_at="2019-07-10T00:00:00+00:00",
):
    return {
        "ratio_record_id": ratio_record_id,
        "issuer_id": issuer_id,
        "ordinary_per_ads": ordinary_per_ads,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "source_ref": source_ref,
        "available_at": available_at,
    }


def _ads_two_records_for_unack_test():
    return (
        _ads_record(
            ratio_record_id="rr-001",
            ordinary_per_ads=8,
            valid_from="2010-01-01",
            valid_to="2019-07-10",
            available_at="2019-07-10T00:00:00+00:00",
        ),
        _ads_record(
            ratio_record_id="rr-002",
            ordinary_per_ads=4,
            valid_from="2019-07-10",
            valid_to=None,
            available_at="2019-07-10T00:00:00+00:00",
        ),
    )


KPI_PERIODS = ("SYN-P-1", "SYN-P-2", "SYN-P-3", "SYN-P-4")


def _kpi_record(period_id, value, state="reported"):
    return {"period_id": period_id, "state": state, "value": value}


def _positive_kpi_series():
    return tuple(
        _kpi_record(pid, v) for pid, v in zip(KPI_PERIODS, (10, 20, 30, 40))
    )


# ===========================================================================
# X8C-03 — verdict.reported_periods follows expected_periods order
# ===========================================================================


def test_r1_03_reported_periods_in_expected_periods_order_under_shuffle():
    """Shuffle the records and assert reported_periods matches PERIODS order."""
    series = _positive_kpi_series()
    rng = random.Random(7)
    diffs = 0
    for _ in range(20):
        shuffled = list(series)
        rng.shuffle(shuffled)
        verdict = check_kpi_series(tuple(shuffled), expected_periods=KPI_PERIODS)
        assert verdict.allowed is True
        if verdict.reported_periods != KPI_PERIODS:
            diffs += 1
    assert diffs == 0, (
        "reported_periods drifted from expected_periods order across shuffles"
    )


# ===========================================================================
# X8C-07 — PIN test: check_kpi_series docstring carries the
#          "expected_periods order" phrase (and KpiSeriesVerdict field
#          comment does the same).
# ===========================================================================


def test_r1_07_check_kpi_series_docstring_documents_expected_order():
    """PIN: the docstring of ``check_kpi_series`` declares the order of
    ``reported_periods`` is the ``expected_periods`` order."""
    src = (ROOT / "research" / "single_name_intelligence" / "common"
           / "sni_kpi_missingness_guard.py").read_text(encoding="utf-8")
    # find the def line for check_kpi_series and grab the docstring.
    m = re.search(
        r'def check_kpi_series\([^)]*\)\s*->\s*[A-Za-z_.| ]+:\s*"""(?P<body>.*?)"""',
        src,
        flags=re.DOTALL,
    )
    assert m is not None, "no check_kpi_series definition found"
    body = m.group("body")
    assert "expected_periods order" in body, (
        "check_kpi_series docstring must document that reported_periods "
        "follows expected_periods order"
    )


def test_r1_07_kpi_series_verdict_field_comment_documents_expected_order():
    """PIN: the ``reported_periods`` field comment on KpiSeriesVerdict
    documents the same ordering."""
    src = (ROOT / "research" / "single_name_intelligence" / "common"
           / "sni_kpi_missingness_guard.py").read_text(encoding="utf-8")
    # Reported_periods: tuple[object, ...] declaration must have an
    # inline comment containing the phrase.
    m = re.search(
        r"(?P<field>reported_periods\s*:\s*tuple\[[^\]]+\])\s*(?P<comment>#.*\n)?",
        src,
    )
    assert m is not None, "no reported_periods declaration found"
    comment = m.group("comment") or ""
    assert "expected_periods order" in comment, (
        "KpiSeriesVerdict.reported_periods must carry a comment naming "
        "expected_periods order"
    )


# ===========================================================================
# X8C-04 — _as_date / _iso_date accept ONLY (a) an exact 10-char YYYY-MM-DD
#          that parses, or (b) a string that datetime.fromisoformat parses
#          in full (then .date()). Everything else -> None.
# ===========================================================================


def test_r1_04_as_date_garbage_suffix_returns_none():
    """Long strings with a valid 10-char prefix + garbage are NOT parsed."""
    assert ads_mod._as_date("2026-08-20garbage") is None  # type: ignore[attr-defined]
    assert ads_mod._as_date("2026-08-20 extra") is None  # type: ignore[attr-defined]


def test_r1_04_as_date_datetime_parseable_returns_date():
    """A string datetime.fromisoformat parses fully returns its .date()."""
    # exact 10-char is still accepted (and date.fromisoformat parses)
    assert ads_mod._as_date("2026-08-20") == __import__("datetime").date(2026, 8, 20)  # type: ignore[attr-defined]


def test_r1_04_as_date_non_string_returns_none():
    """Non-str values return None (no raise, no implicit coercion)."""
    assert ads_mod._as_date(None) is None  # type: ignore[attr-defined]
    assert ads_mod._as_date(20260820) is None  # type: ignore[attr-defined]
    assert ads_mod._as_date(["2026-08-20"]) is None  # type: ignore[attr-defined]


def test_r1_04_iso_date_x8c_inputs_refused():
    """X8C-04 RE-CHECK inputs are refused: garbage suffix, trailing extras,
    any non-str. The 10-char YYYY-MM-DD form is still accepted."""
    import datetime as _dt
    # Exact 10-char YYYY-MM-DD: still accepted (option a).
    assert ads_mod._iso_date("2026-08-20") == _dt.date(2026, 8, 20)  # type: ignore[attr-defined]
    # Garbage suffix / trailing extras: refused.
    assert ads_mod._iso_date("2026-08-20garbage") is None  # type: ignore[attr-defined]
    assert ads_mod._iso_date("2026-08-20 extra") is None  # type: ignore[attr-defined]
    # Non-str: refused.
    assert ads_mod._iso_date(None) is None  # type: ignore[attr-defined]
    assert ads_mod._iso_date(20260820) is None  # type: ignore[attr-defined]


def test_r1_04_check_ads_ratio_refuses_garbage_suffix_valid_from():
    """The 19/20 surprise: a valid_from with garbage suffix is refused."""
    rec = _ads_record(
        valid_from="2010-01-01 12:34:56 garbage",
    )
    verdict = check_ads_ratio(
        ADS_PERIODS,
        [rec],
        as_of="2021-06-01T00:00:00+00:00",
    )
    # With X8C-04 closed the record is refused (DATE_INVALID or
    # INTERVAL_INVALID), not silently truncated.
    assert verdict.allowed is False
    refused = set(verdict.reasons)
    assert refused & {"DATE_INVALID", "INTERVAL_INVALID"}, (
        "garbage-suffix valid_from must refuse via DATE_INVALID or "
        "INTERVAL_INVALID; got reasons=" + repr(verdict.reasons)
    )


# ===========================================================================
# X8C-05 — PIN: an as_of that is None, non-str, or unparseable is refused
#          as RATIO_NOT_AVAILABLE_AS_OF. Behaviour kept; document it.
# ===========================================================================


def test_r1_05_pin_as_of_none_refused_as_ratio_not_available_as_of():
    rec = _ads_record(available_at="2019-07-10T00:00:00+00:00")
    verdict = check_ads_ratio(ADS_PERIODS, [rec], as_of=None)
    assert verdict.allowed is False
    assert verdict.reasons == ("RATIO_NOT_AVAILABLE_AS_OF",), (
        f"as_of=None must refuse as RATIO_NOT_AVAILABLE_AS_OF; "
        f"got reasons={verdict.reasons!r}"
    )


def test_r1_05_pin_as_of_int_zero_refused_as_ratio_not_available_as_of():
    rec = _ads_record(available_at="2019-07-10T00:00:00+00:00")
    verdict = check_ads_ratio(ADS_PERIODS, [rec], as_of=0)
    assert verdict.allowed is False
    assert verdict.reasons == ("RATIO_NOT_AVAILABLE_AS_OF",)


def test_r1_05_pin_as_of_garbage_refused_as_ratio_not_available_as_of():
    rec = _ads_record(available_at="2019-07-10T00:00:00+00:00")
    verdict = check_ads_ratio(ADS_PERIODS, [rec], as_of="garbage")
    assert verdict.allowed is False
    assert verdict.reasons == ("RATIO_NOT_AVAILABLE_AS_OF",), (
        f"as_of='garbage' must refuse as RATIO_NOT_AVAILABLE_AS_OF; "
        f"got reasons={verdict.reasons!r}"
    )


def test_r1_05_check_ads_ratio_docstring_documents_as_of_refusal():
    """PIN: docstring of ``check_ads_ratio`` says None / non-str /
    unparseable as_of -> RATIO_NOT_AVAILABLE_AS_OF."""
    src = (ROOT / "research" / "single_name_intelligence" / "common"
           / "sni_ads_ratio_guard.py").read_text(encoding="utf-8")
    m = re.search(
        r'def check_ads_ratio\([^)]*\)\s*->\s*[A-Za-z_.| ]+:\s*"""(?P<body>.*?)"""',
        src,
        flags=re.DOTALL,
    )
    assert m is not None, "no check_ads_ratio definition found"
    body = m.group("body")
    assert "RATIO_NOT_AVAILABLE_AS_OF" in body
    # Must mention None OR non-str OR unparseable to be exact.
    needle = "None" in body or "unparseable" in body or "non-str" in body
    assert needle, (
        "check_ads_ratio docstring must document that None / non-str / "
        "unparseable as_of is refused as RATIO_NOT_AVAILABLE_AS_OF"
    )


# ===========================================================================
# X8C-06 — Only text-present str ids count in acknowledged_ratio_changes.
#          bytes / ints never match. Document. PIN test with b"rr-002"
#          -> RATIO_CHANGE_UNACKNOWLEDGED.
# ===========================================================================


def test_r1_06_pin_bytes_ack_refused_as_ratio_change_unacknowledged():
    """b\"rr-002\" does not acknowledge a record with ratio_record_id=rr-002."""
    request = {
        "issuer_id": "iss-x8crepc",
        "on_date": "2020-01-15",
        "window_start": "2012-06-01",
        "acknowledged_ratio_changes": b"rr-002",
    }
    verdict = check_ads_ratio(
        request, list(_ads_two_records_for_unack_test()),
        as_of="2021-06-01T00:00:00+00:00",
    )
    assert verdict.allowed is False
    assert verdict.reasons == ("RATIO_CHANGE_UNACKNOWLEDGED",), (
        f"bytes ack must refuse as RATIO_CHANGE_UNACKNOWLEDGED; "
        f"got reasons={verdict.reasons!r}"
    )


def test_r1_06_pin_int_ack_refused_as_ratio_change_unacknowledged():
    """An int ack is also refused — bytes and ints are ABSENT, not matches."""
    request = {
        "issuer_id": "iss-x8crepc",
        "on_date": "2020-01-15",
        "window_start": "2012-06-01",
        "acknowledged_ratio_changes": 1,
    }
    verdict = check_ads_ratio(
        request, list(_ads_two_records_for_unack_test()),
        as_of="2021-06-01T00:00:00+00:00",
    )
    assert verdict.allowed is False
    assert verdict.reasons == ("RATIO_CHANGE_UNACKNOWLEDGED",)


def test_r1_06_check_ads_ratio_docstring_documents_text_only_ack():
    """PIN: docstring states only text-present str ids count in
    acknowledged_ratio_changes."""
    src = (ROOT / "research" / "single_name_intelligence" / "common"
           / "sni_ads_ratio_guard.py").read_text(encoding="utf-8")
    m = re.search(
        r'def check_ads_ratio\([^)]*\)\s*->\s*[A-Za-z_.| ]+:\s*"""(?P<body>.*?)"""',
        src,
        flags=re.DOTALL,
    )
    assert m is not None
    body = m.group("body")
    assert "acknowledged_ratio_changes" in body
    # Must state the bytes/int/non-str exclusion plainly.
    assert (
        "bytes" in body or "int" in body or "non-str" in body
    ), "check_ads_ratio docstring must state bytes/int ack is refused"


# ===========================================================================
# X8C-11 — ADS-ratio source_ref and ratio_record_id follow the FAMILY TEXT
#          RULE. Lists, dicts, ints, padded strings -> ABSENT and refused
#          with the same reason the module emits for a blank of that field.
# ===========================================================================


def test_r1_11_list_source_ref_refused_as_ratio_record_unsourced():
    """source_ref=[...] is a list -> not text-present -> refused."""
    request = {**ADS_PERIODS, "on_date": "2020-01-15"}
    rec = _ads_record(
        source_ref=["src-a", "src-b"],
        available_at="2019-07-10T00:00:00+00:00",
        valid_from="2010-01-01",
        valid_to="2019-07-10",
    )
    verdict = check_ads_ratio(request, [rec],
                              as_of="2021-06-01T00:00:00+00:00")
    assert verdict.allowed is False
    assert "RATIO_RECORD_UNSOURCED" in verdict.reasons


def test_r1_11_int_source_ref_refused_as_ratio_record_unsourced():
    """source_ref=42 is an int -> not text-present -> refused."""
    request = {**ADS_PERIODS, "on_date": "2020-01-15"}
    rec = _ads_record(
        source_ref=42,
        available_at="2019-07-10T00:00:00+00:00",
        valid_from="2010-01-01",
        valid_to="2019-07-10",
    )
    verdict = check_ads_ratio(request, [rec],
                              as_of="2021-06-01T00:00:00+00:00")
    assert verdict.allowed is False
    assert "RATIO_RECORD_UNSOURCED" in verdict.reasons


def test_r1_11_dict_source_ref_refused_as_ratio_record_unsourced():
    """source_ref={...} is a dict -> not text-present -> refused."""
    request = {**ADS_PERIODS, "on_date": "2020-01-15"}
    rec = _ads_record(
        source_ref={"id": "src-a"},
        available_at="2019-07-10T00:00:00+00:00",
        valid_from="2010-01-01",
        valid_to="2019-07-10",
    )
    verdict = check_ads_ratio(request, [rec],
                              as_of="2021-06-01T00:00:00+00:00")
    assert verdict.allowed is False
    assert "RATIO_RECORD_UNSOURCED" in verdict.reasons


def test_r1_11_whitespace_only_source_ref_refused_as_ratio_record_unsourced():
    """source_ref='   ' is whitespace-only -> not text-present -> refused."""
    request = {**ADS_PERIODS, "on_date": "2020-01-15"}
    rec = _ads_record(
        source_ref="   ",
        available_at="2019-07-10T00:00:00+00:00",
        valid_from="2010-01-01",
        valid_to="2019-07-10",
    )
    verdict = check_ads_ratio(request, [rec],
                              as_of="2021-06-01T00:00:00+00:00")
    assert verdict.allowed is False
    assert "RATIO_RECORD_UNSOURCED" in verdict.reasons


def test_r1_11_padded_source_ref_refused_as_ratio_record_unsourced():
    """source_ref='  src  ' has leading/trailing whitespace -> refused."""
    request = {**ADS_PERIODS, "on_date": "2020-01-15"}
    rec = _ads_record(
        source_ref="  src  ",
        available_at="2019-07-10T00:00:00+00:00",
        valid_from="2010-01-01",
        valid_to="2019-07-10",
    )
    verdict = check_ads_ratio(request, [rec],
                              as_of="2021-06-01T00:00:00+00:00")
    assert verdict.allowed is False
    assert "RATIO_RECORD_UNSOURCED" in verdict.reasons


def test_r1_11_list_ratio_record_id_refused_as_ratio_record_unsourced():
    """ratio_record_id=list is also refused as the same reason."""
    request = {**ADS_PERIODS, "on_date": "2020-01-15"}
    rec = _ads_record(
        ratio_record_id=["rr-001"],
        available_at="2019-07-10T00:00:00+00:00",
    )
    verdict = check_ads_ratio(request, [rec],
                              as_of="2021-06-01T00:00:00+00:00")
    assert verdict.allowed is False
    assert "RATIO_RECORD_UNSOURCED" in verdict.reasons


# ===========================================================================
# Authority / reasons invariant — never trust our own tests.
# ===========================================================================


def test_r1_reasons_tuples_unchanged():
    refuse_nonfalse_authority()
    assert ADS_REASONS == (
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
    assert KPI_REASONS == (
        "PERIOD_ID_MISSING",
        "DUPLICATE_PERIOD",
        "STATE_UNKNOWN",
        "REPORTED_VALUE_INVALID",
        "MISSING_CARRIES_VALUE",
        "PERIOD_ABSENT",
        "UNEXPECTED_PERIOD",
        "CARRY_FORWARD_DECLARED",
        "IMPUTATION_DECLARED",
    )
