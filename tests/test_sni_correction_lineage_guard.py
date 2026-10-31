"""A16 correction-lineage tests: non-append-only histories are refused.

SNI-local DRAFT contract tests. They consume owner-supplied opaque
identity strings (Stock Identity / Data OS) and never mint issuer or
security ids. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority
and trade_authority stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import ast
import copy
import re as _re
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_correction_lineage_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    RECORD_FIELDS,
    LineageVerdict,
    check_lineage,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_correction_lineage_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


class _Omit:
    pass


_OMIT = _Omit()


def _rec(number: int = 1, **overrides):
    record = {
        "record_id": "SYN-REC-1",
        "version_id": f"SYN-VID-{number}",
        "version": number,
        "supersedes_version_id": f"SYN-VID-{number - 1}" if number > 1 else None,
        "content_sha256": f"{number:02d}" * 32,
        "recorded_at": f"2026-01-{10 + number:02d}T09:00:00+00:00",
    }
    record.update(overrides)
    drop = [key for key, val in record.items() if val is _OMIT]
    for key in drop:
        del record[key]
    return record


def _assert_contract(verdict: LineageVerdict) -> None:
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    assert verdict.allowed == (verdict.reasons == ())
    assert verdict.authority_flags is AUTHORITY_FLAGS
    assert isinstance(verdict.reasons, tuple)
    assert isinstance(verdict.appended, tuple)


def _assert_allowed(verdict: LineageVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_refused(verdict: LineageVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict.reasons
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


# ---------------------------------------------------------------------------
# T1 positive controls
# ---------------------------------------------------------------------------


def test_a16_positive_first_write():
    verdict = check_lineage((), (_rec(1),))
    _assert_allowed(verdict)
    assert verdict.appended == ("SYN-VID-1",)


def test_a16_positive_first_write_three_versions():
    verdict = check_lineage((), (_rec(1), _rec(2), _rec(3)))
    _assert_allowed(verdict)
    assert verdict.appended == ("SYN-VID-1", "SYN-VID-2", "SYN-VID-3")


def test_a16_positive_append_one_correction():
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2))
    verdict = check_lineage(prior, proposed)
    _assert_allowed(verdict)
    assert verdict.appended == ("SYN-VID-2",)


def test_a16_positive_second_append():
    prior = (_rec(1), _rec(2))
    proposed = (_rec(1), _rec(2), _rec(3))
    verdict = check_lineage(prior, proposed)
    _assert_allowed(verdict)
    assert verdict.appended == ("SYN-VID-3",)


def test_a16_positive_proposed_equals_prior():
    prior = (_rec(1), _rec(2))
    proposed = copy.deepcopy(prior)
    verdict = check_lineage(prior, proposed)
    _assert_allowed(verdict)
    assert verdict.appended == ()


def test_a16_positive_z_suffix_timestamps():
    first = _rec(1, recorded_at="2026-01-11T09:00:00Z")
    second = _rec(2, recorded_at="2026-01-11T09:00:01Z")
    verdict = check_lineage((), (first, second))
    _assert_allowed(verdict)


# ---------------------------------------------------------------------------
# T2 single-flip tests, one per REASONS entry
# ---------------------------------------------------------------------------


def test_a16_flip_record_field_invalid():
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, recorded_at="2026-01-12T09:00:00"))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "RECORD_FIELD_INVALID")
    assert verdict.reasons == ("RECORD_FIELD_INVALID",)


def test_a16_flip_mixed_record_ids():
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, record_id="SYN-REC-2"))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "MIXED_RECORD_IDS")
    assert verdict.reasons == ("MIXED_RECORD_IDS",)


def test_a16_flip_history_truncated():
    prior = (_rec(1), _rec(2))
    proposed = (_rec(1),)
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "HISTORY_TRUNCATED")
    assert verdict.reasons == ("HISTORY_TRUNCATED",)


def test_a16_flip_history_rewritten():
    prior = (_rec(1),)
    proposed = (_rec(1, content_sha256="ff" * 32), _rec(2))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "HISTORY_REWRITTEN")
    assert verdict.reasons == ("HISTORY_REWRITTEN",)


def test_a16_flip_duplicate_version_id():
    proposed = (_rec(1), _rec(2, version_id="SYN-VID-1"))
    verdict = check_lineage((), proposed)
    _assert_refused(verdict, "DUPLICATE_VERSION_ID")
    assert verdict.reasons == ("DUPLICATE_VERSION_ID",)


def test_a16_flip_fork():
    proposed = (_rec(1), _rec(1, version_id="SYN-VID-1B"))
    verdict = check_lineage((), proposed)
    _assert_refused(verdict, "FORK")
    assert "VERSION_GAP" in verdict.reasons
    assert "VERSION_NOT_INCREASING" in verdict.reasons


def test_a16_flip_version_gap():
    verdict = check_lineage((), (_rec(2),))
    _assert_refused(verdict, "VERSION_GAP")
    assert verdict.reasons == ("VERSION_GAP",)


def test_a16_flip_version_not_increasing():
    proposed = (_rec(2), _rec(1))
    verdict = check_lineage((), proposed)
    _assert_refused(verdict, "VERSION_NOT_INCREASING")
    assert verdict.reasons == ("VERSION_NOT_INCREASING",)


def test_a16_flip_supersedes_mismatch():
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, supersedes_version_id="SYN-VID-0"))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "SUPERSEDES_MISMATCH")
    assert verdict.reasons == ("SUPERSEDES_MISMATCH",)


def test_a16_flip_content_unchanged():
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, content_sha256="01" * 32))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "CONTENT_UNCHANGED")
    assert verdict.reasons == ("CONTENT_UNCHANGED",)


def test_a16_flip_recorded_at_not_monotone():
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, recorded_at="2026-01-11T09:00:00+00:00"))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "RECORDED_AT_NOT_MONOTONE")
    assert verdict.reasons == ("RECORDED_AT_NOT_MONOTONE",)


# ---------------------------------------------------------------------------
# Module tests: rewrite detection per prior-record field (parametrised)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", RECORD_FIELDS)
def test_a16_rewrite_each_prior_field(field):
    prior = (_rec(1),)
    flipped = {
        "record_id": "SYN-REC-9",
        "version_id": "SYN-VID-9",
        "version": 3,
        "supersedes_version_id": "SYN-VID-0",
        "content_sha256": "ff" * 32,
        "recorded_at": "2026-02-01T09:00:00+00:00",
    }
    proposed = (_rec(1, **{field: flipped[field]}), _rec(2))
    verdict = check_lineage(prior, proposed)
    if field == "version_id":
        # the prior record's identity key vanished, so the prior history is
        # no longer extended rather than rewritten in place
        _assert_refused(verdict, "HISTORY_TRUNCATED")
    else:
        _assert_refused(verdict, "HISTORY_REWRITTEN")


# ---------------------------------------------------------------------------
# Module tests: field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_version", [True, "2", 0, 1.0])
def test_a16_version_type_invalid(bad_version):
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, version=bad_version))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "RECORD_FIELD_INVALID")


@pytest.mark.parametrize(
    "bad_sha", ["AB" * 32, "a" * 63, "a" * 65, "g" * 64, 11 * 32, None]
)
def test_a16_content_sha256_invalid(bad_sha):
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, content_sha256=bad_sha))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "RECORD_FIELD_INVALID")


@pytest.mark.parametrize(
    "overrides",
    [
        {"record_id": _OMIT},
        {"version_id": _OMIT},
        {"version": _OMIT},
        {"supersedes_version_id": _OMIT},
        {"content_sha256": _OMIT},
        {"recorded_at": _OMIT},
        {"extra_field": 1},
        {"record_id": ""},
        {"record_id": None},
        {"version_id": ""},
        {"version_id": None},
        {"supersedes_version_id": ""},
    ],
)
def test_a16_record_shape_invalid(overrides):
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, **overrides))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "RECORD_FIELD_INVALID")


def test_a16_proposed_empty_refused():
    verdict = check_lineage((_rec(1),), ())
    _assert_refused(verdict, "RECORD_FIELD_INVALID")
    assert verdict.appended == ()


def test_a16_prior_empty_and_proposed_empty_refused():
    verdict = check_lineage((), ())
    _assert_refused(verdict, "RECORD_FIELD_INVALID")


@pytest.mark.parametrize(
    "bad_time",
    [
        "2026-01-12T09:00:00",
        "2026-01-12",
        "not-a-time",
        None,
        "2026-01-12T09:00:00+99",
    ],
)
def test_a16_recorded_at_requires_offset(bad_time):
    proposed = (_rec(1, recorded_at=bad_time),)
    verdict = check_lineage((), proposed)
    _assert_refused(verdict, "RECORD_FIELD_INVALID")


def test_a16_supersedes_none_on_version_two_mismatch():
    prior = (_rec(1),)
    proposed = (_rec(1), _rec(2, supersedes_version_id=None))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "SUPERSEDES_MISMATCH")


def test_a16_supersedes_set_on_version_one_mismatch():
    verdict = check_lineage((), (_rec(1, supersedes_version_id="SYN-VID-0"),))
    _assert_refused(verdict, "SUPERSEDES_MISMATCH")
    assert verdict.reasons == ("SUPERSEDES_MISMATCH",)


# ---------------------------------------------------------------------------
# Module tests: truncation shapes
# ---------------------------------------------------------------------------


def test_a16_truncated_missing_middle_version():
    prior = (_rec(1), _rec(2), _rec(3))
    proposed = (_rec(1), _rec(3))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "HISTORY_TRUNCATED", "VERSION_GAP")


def test_a16_truncated_same_length_missing_version_id():
    prior = (_rec(1), _rec(2))
    proposed = (_rec(1), _rec(2, version_id="SYN-VID-2B"))
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "HISTORY_TRUNCATED")
    assert "HISTORY_REWRITTEN" not in verdict.reasons


# ---------------------------------------------------------------------------
# Module tests: appended contents and monotone offsets
# ---------------------------------------------------------------------------


def test_a16_appended_contents():
    assert check_lineage((), (_rec(1),)).appended == ("SYN-VID-1",)
    assert check_lineage((_rec(1),), (_rec(1),)).appended == ()
    assert check_lineage((_rec(1),), (_rec(1), _rec(2))).appended == ("SYN-VID-2",)
    assert (
        check_lineage((_rec(1),), (_rec(1), _rec(2), _rec(3))).appended
        == ("SYN-VID-2", "SYN-VID-3")
    )


def test_a16_mixed_offsets_compared_as_instants():
    first = _rec(1, recorded_at="2026-01-11T09:00:00+08:00")
    second = _rec(2, recorded_at="2026-01-11T02:00:00+00:00")
    verdict = check_lineage((), (first, second))
    _assert_allowed(verdict)
    reversed_verdict = check_lineage((), (second, first))
    _assert_refused(reversed_verdict, "VERSION_NOT_INCREASING")


def test_a16_equal_recorded_at_refuses():
    same = "2026-01-11T09:00:00+00:00"
    proposed = (_rec(1, recorded_at=same), _rec(2, recorded_at=same))
    verdict = check_lineage((), proposed)
    _assert_refused(verdict, "RECORDED_AT_NOT_MONOTONE")


# ---------------------------------------------------------------------------
# T3 authority
# ---------------------------------------------------------------------------


def test_a16_authority_refuse_nonfalse_raises():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    for bad in (True, 0, None, ""):
        for name in FLAG_NAMES:
            flags = dict(AUTHORITY_FLAGS)
            flags[name] = bad
            with pytest.raises(ValueError):
                refuse_nonfalse_authority(flags)


def test_a16_authority_flags_frozen_and_false():
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    verdict = check_lineage((), (_rec(1),))
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False


def test_a16_verdict_frozen_dataclass():
    verdict = check_lineage((), (_rec(1),))
    with pytest.raises(FrozenInstanceError):
        verdict.allowed = True
    with pytest.raises(FrozenInstanceError):
        verdict.appended = ("SYN-VID-2",)


# ---------------------------------------------------------------------------
# T4 static scans of the module source
# ---------------------------------------------------------------------------


def test_a16_static_scan_reasons_and_forbidden_text():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert not _re.search(r"\b\d{4,5}\.HK\b", source)
    for ticker in ("BABA", "TCEHY", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"):
        assert ticker not in source, ticker
    for banned in ("datetime.now", "utcnow", "date.today", "time.time", "open("):
        assert banned not in source, banned


def test_a16_static_scan_no_normalisation():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_attr = {"lower", "upper", "casefold", "strip", "replace"}
    attr_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden_attr:
                attr_hits.append((node.lineno, node.func.attr))
    assert attr_hits == [], attr_hits
    import_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root == "re" or "identity" in root.casefold() or root == "dataos":
                    import_hits.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            root = mod.split(".")[0] if mod else ""
            if root == "re" or "identity" in root.casefold() or root == "dataos":
                import_hits.append((node.lineno, mod))
            if any(alias.name == "re" for alias in node.names):
                import_hits.append((node.lineno, "re"))
    assert import_hits == [], import_hits


# ---------------------------------------------------------------------------
# T5 de-dup and REASONS order
# ---------------------------------------------------------------------------


def test_a16_reasons_order_and_dedup():
    prior = (_rec(1),)
    proposed = (
        _rec(1, recorded_at="2026-01-11T08:00:00+00:00"),
        _rec(
            2,
            supersedes_version_id="SYN-VID-0",
            content_sha256="01" * 32,
            recorded_at="2026-01-11T08:00:00+00:00",
        ),
    )
    verdict = check_lineage(prior, proposed)
    expected = (
        "HISTORY_REWRITTEN",
        "SUPERSEDES_MISMATCH",
        "CONTENT_UNCHANGED",
        "RECORDED_AT_NOT_MONOTONE",
    )
    assert verdict.reasons == expected
    assert len(verdict.reasons) == len(set(verdict.reasons))
    _assert_refused(verdict, *expected)


def test_a16_reasons_kitchen_sink():
    prior = (_rec(1),)
    proposed = (
        _rec(1, content_sha256="02" * 32),
        _rec(
            2,
            version_id="SYN-VID-1",
            supersedes_version_id="SYN-VID-0",
            content_sha256="02" * 32,
            recorded_at="2026-01-01T00:00:00+00:00",
        ),
    )
    verdict = check_lineage(prior, proposed)
    _assert_refused(
        verdict,
        "HISTORY_REWRITTEN",
        "DUPLICATE_VERSION_ID",
        "SUPERSEDES_MISMATCH",
        "CONTENT_UNCHANGED",
        "RECORDED_AT_NOT_MONOTONE",
    )
    assert verdict.reasons == tuple(
        code for code in REASONS if code in set(verdict.reasons)
    )


# ---------------------------------------------------------------------------
# T6 adversarial id cases (record_id and version_id)
# ---------------------------------------------------------------------------


def _alpha_rec(number: int = 1, **overrides):
    base = _rec(
        number,
        record_id="syn-rec-alpha",
        version_id=f"syn-vid-{'alpha' if number == 1 else 'beta'}",
    )
    base.update(overrides)
    return base


def test_a16_adversarial_record_id():
    prior = (_alpha_rec(1),)
    for variant in (
        "SYN-REC-ALPHA",  # case change
        "syn-rec-аlpha",  # Cyrillic look-alike "а" (U+0430)
    ):
        proposed = (_alpha_rec(1), _alpha_rec(2, record_id=variant))
        verdict = check_lineage(prior, proposed)
        _assert_refused(verdict, "MIXED_RECORD_IDS")
    # FAMILY TEXT RULE v2: a padded record_id is ABSENT, never a different id.
    for variant in ("syn-rec-alpha ", " syn-rec-alpha"):
        proposed = (_alpha_rec(1), _alpha_rec(2, record_id=variant))
        verdict = check_lineage(prior, proposed)
        _assert_refused(verdict, "RECORD_FIELD_INVALID")


def test_a16_adversarial_version_id():
    prior = (_alpha_rec(1),)
    # case-variant version_id on the prior-matched record drops the prior id
    case_variant = _alpha_rec(1, version_id="SYN-VID-ALPHA")
    verdict = check_lineage(prior, (case_variant, _alpha_rec(2)))
    _assert_refused(verdict, "HISTORY_TRUNCATED")
    # look-alike / case-variant supersedes links do not match the real id
    for variant in (
        "syn-vid-аlpha",  # Cyrillic look-alike "а" (U+0430)
        "SYN-VID-ALPHA",  # case change
    ):
        proposed = (_alpha_rec(1), _alpha_rec(2, supersedes_version_id=variant))
        verdict = check_lineage(prior, proposed)
        _assert_refused(verdict, "SUPERSEDES_MISMATCH")
    # FAMILY TEXT RULE v2: a padded supersedes link is ABSENT, never a
    # different id.
    proposed = (
        _alpha_rec(1),
        _alpha_rec(2, supersedes_version_id="syn-vid-alpha "),
    )
    verdict = check_lineage(prior, proposed)
    _assert_refused(verdict, "RECORD_FIELD_INVALID")


def test_a16_mixed_record_ids_from_prior_side():
    prior = (_rec(1, record_id="SYN-REC-A"),)
    proposed = (_rec(1, record_id="SYN-REC-A"), _rec(2, record_id="SYN-REC-A"))
    other_prior = (_rec(1, record_id="SYN-REC-B"),)
    verdict = check_lineage(other_prior, proposed)
    _assert_refused(verdict, "MIXED_RECORD_IDS", "HISTORY_REWRITTEN")


# ---------------------------------------------------------------------------
# Type errors and completeness
# ---------------------------------------------------------------------------


def test_a16_type_error_inputs():
    with pytest.raises(TypeError):
        check_lineage({"version_id": "SYN-VID-1"}, ())
    with pytest.raises(TypeError):
        check_lineage((), {"version_id": "SYN-VID-1"})
    with pytest.raises(TypeError):
        check_lineage((), ("not-a-mapping",))


def test_a16_completeness_every_reason_within_contract():
    cases = [
        ((), (_rec(1),)),
        ((_rec(1),), (_rec(1), _rec(2))),
        ((_rec(1),), ()),
        ((_rec(1),), (_rec(1, content_sha256="ff" * 32), _rec(2))),
        ((), (_rec(1), _rec(2, version_id="SYN-VID-1"))),
        ((), (_rec(1), _rec(1, version_id="SYN-VID-1B"))),
        ((), (_rec(2),)),
        ((), (_rec(2), _rec(1))),
        ((_rec(1),), (_rec(1), _rec(2, supersedes_version_id=None))),
        ((_rec(1),), (_rec(1), _rec(2, content_sha256="01" * 32))),
        ((_rec(1),), (_rec(1), _rec(2, recorded_at="2026-01-01T00:00:00+00:00"))),
        ((_rec(1),), (_rec(1), _rec(2, recorded_at="naive"))),
        ((_rec(1), _rec(2)), (_rec(1),)),
        ((_rec(1),), (_rec(1, record_id="SYN-REC-2"), _rec(2, record_id="SYN-REC-2"))),
    ]
    for prior, proposed in cases:
        verdict = check_lineage(prior, proposed)
        _assert_contract(verdict)


def test_a16_reasons_tuple_contract():
    assert REASONS == (
        "RECORD_FIELD_INVALID",
        "MIXED_RECORD_IDS",
        "HISTORY_TRUNCATED",
        "HISTORY_REWRITTEN",
        "DUPLICATE_VERSION_ID",
        "FORK",
        "VERSION_GAP",
        "VERSION_NOT_INCREASING",
        "SUPERSEDES_MISMATCH",
        "CONTENT_UNCHANGED",
        "RECORDED_AT_NOT_MONOTONE",
    )
    assert len(REASONS) == len(set(REASONS))
    assert RECORD_FIELDS == (
        "record_id",
        "version_id",
        "version",
        "supersedes_version_id",
        "content_sha256",
        "recorded_at",
    )
