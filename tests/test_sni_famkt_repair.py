"""FAMKT repair tests — FAMILY TEXT RULE v2 for kpi/then_known id fields.

These are the fail-first tests for the FAMKT repair round. Each closed
defect from the FROZEN REPAIR SPEC has exactly one test function, named
``test_r1_<nn>_<slug>`` per the lane spec. Each test reproduces the
EVIDENCE block from the spec and asserts the refusal FAMILY TEXT RULE v2
demands:

  def _text_present(value: object) -> bool:
      return (
          isinstance(value, str)
          and value != ""
          and not value[0].isspace()
          and not value[-1].isspace()
      )

Defects closed here (per FROZEN REPAIR SPEC, defect -> test):

  FAMKT-01  KPI: canonical v2 _text_present lives at module level.
  FAMKT-02  KPI: a padded / non-str / unhashable record period_id is
            ABSENT and emits PERIOD_ID_MISSING; never compared, never
            added to present_ids, never added to reported_present.
  FAMKT-03  KPI: expected_periods only text-present entries are
            membership-tested; a non-text-present expected entry yields
            PERIOD_ABSENT and never raises (unhashable expected entries
            no longer raise TypeError on ``in reported_present``).
  FAMKT-04  KPI: _blank and _present deleted (no external callers).
  FAMKT-05  Then_known: canonical v2 _text_present lives at module level;
            _fact_id_absent is ``not _text_present``; padded fact_id now
            emits FACT_ID_MISSING; X8B-02 padded half is CLOSED.
  FAMKT-06  Then_known: known_ids and supersedes edges hold text-present
            fact ids only.
  FAMKT-07  Then_known: supersedes -- None/"" stays "no link";
            non-text-present -> SUPERSEDES_UNKNOWN; text-present not in
            known_ids -> SUPERSEDES_UNKNOWN; edge creation only for
            text-present values; nothing here ever raises.

The tests import the modules the same way the existing SNI guard tests
do: a sys.path insert of research/single_name_intelligence/common, then
``from sni_<x>_guard import (...)  # noqa: E402``. They do NOT pop,
delete, or replace any sys.modules key.

HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and
trade_authority stay literal False. Fixtures are synthetic; fact ids,
period ids, and supersedes refs are caller-supplied opaque strings,
never minted here.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_kpi_missingness_guard import (  # noqa: E402
    AUTHORITY_FLAGS as KPI_AUTHORITY_FLAGS,  # noqa: E402
    KPI_STATES,
    REASONS as KPI_REASONS,
    KpiSeriesVerdict,
    aggregate_sum,
    check_kpi_series,
    kpi_value,
    refuse_nonfalse_authority as kpi_refuse_nonfalse_authority,
)
from sni_then_known_guard import (  # noqa: E402
    AUTHORITY_FLAGS as TK_AUTHORITY_FLAGS,  # noqa: E402
    REASONS as TK_REASONS,
    ThenKnownView,
    clock_triplet,
    refuse_nonfalse_authority as tk_refuse_nonfalse_authority,
    then_known_view,
)

KPI_MODULE_PATH = (
    ROOT / "research" / "single_name_intelligence" / "common"
    / "sni_kpi_missingness_guard.py"
)
TK_MODULE_PATH = (
    ROOT / "research" / "single_name_intelligence" / "common"
    / "sni_then_known_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

CUTOFF = "2026-06-01T00:00:00+00:00"

PERIODS = ("SYN-P-1", "SYN-P-2", "SYN-P-3", "SYN-P-4")

JUNK_VALUES: tuple[object, ...] = (
    None,
    "",
    " ",
    "SYN-P-1 ",
    1,
    True,
    1.0,
    b"x",
    ["x"],
    {"x": 1},
)

JUNK_FACT_VALUES: tuple[object, ...] = (
    None,
    "",
    " ",
    "SYN-FACT-1 ",
    1,
    True,
    1.0,
    b"x",
    ["x"],
    {"x": 1},
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _kpi_record(period_id, state="reported", value=10, **overrides):
    rec = {"period_id": period_id, "state": state, "value": value}
    rec.update(overrides)
    return rec


def _kpi_positive_series():
    values = (10, 20, 30, 40)
    return tuple(
        _kpi_record(period_id, value=value)
        for period_id, value in zip(PERIODS, values)
    )


def _assert_kpi_refused(verdict: KpiSeriesVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)


def _assert_kpi_allowed(verdict: KpiSeriesVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()


def _tk_item(**overrides):
    body = {
        "fact_id": "SYN-FACT-1",
        "economic_time": "2026-01-15T00:00:00+00:00",
        "owner_known_at": "2026-03-02T10:05:00+00:00",
        "published_at": "2026-03-01T08:00:00+00:00",
        "retrieved_at": "2026-03-02T11:00:00+00:00",
        "supersedes": None,
        "vintaged": False,
    }
    body.update(overrides)
    return body


def _assert_tk_refused(view: ThenKnownView, *codes: str) -> None:
    assert view.allowed is False, view
    got = set(view.reasons)
    for code in codes:
        assert code in got, (code, view.reasons)


def _assert_tk_allowed(view: ThenKnownView) -> None:
    assert view.allowed is True, view.reasons
    assert view.reasons == ()


# ---------------------------------------------------------------------------
# FAMKT-01 / FAMKT-05: canonical v2 _text_present lives in both modules
# ---------------------------------------------------------------------------


def test_r1_01_kpi_module_defines_text_present_helper():
    """FAMKT-01: the canonical v2 _text_present sits at module level in
    sni_kpi_missingness_guard. It uses no normalisation method and only
    calls isinstance() and str.isspace()."""
    source = KPI_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    helpers = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_text_present"
    ]
    assert len(helpers) == 1, (
        f"expected exactly one _text_present in kpi module, found {len(helpers)}"
    )
    helper = helpers[0]
    body = helper.body
    # The return expression is a BoolOp with four operands (chained and).
    returns = [n for n in ast.walk(helper) if isinstance(n, ast.Return)]
    assert len(returns) == 1
    ret_value = returns[0].value
    assert isinstance(ret_value, ast.BoolOp) and isinstance(ret_value.op, ast.And)
    assert len(ret_value.values) == 4, (
        "v2 _text_present must chain exactly four AND conditions"
    )
    # No normalisation calls.
    forbidden = {"lower", "upper", "casefold", "strip", "replace"}
    hits = [
        (n.lineno, n.func.attr) for n in ast.walk(helper)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in forbidden
    ]
    assert hits == [], hits


def test_r1_05_then_known_module_defines_text_present_helper():
    """FAMKT-05: the canonical v2 _text_present sits at module level in
    sni_then_known_guard. Same shape as the kpi version."""
    source = TK_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    helpers = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_text_present"
    ]
    assert len(helpers) == 1, (
        f"expected exactly one _text_present in then_known, found {len(helpers)}"
    )
    helper = helpers[0]
    returns = [node for node in ast.walk(helper) if isinstance(node, ast.Return)]
    assert len(returns) == 1
    ret_value = returns[0].value
    assert isinstance(ret_value, ast.BoolOp) and isinstance(ret_value.op, ast.And)
    assert len(ret_value.values) == 4
    forbidden = {"lower", "upper", "casefold", "strip", "replace"}
    hits = [
        (n.lineno, n.func.attr) for n in ast.walk(helper)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in forbidden
    ]
    assert hits == [], hits


def test_r1_05_then_known_text_present_used_by_fact_id_absent():
    """FAMKT-05: _fact_id_absent(value) is now ``not _text_present(value)``.
    The docstring no longer claims the padded half stays open."""
    import sni_then_known_guard as tk_mod
    assert tk_mod._fact_id_absent("SYN-FACT-1") is False
    assert tk_mod._fact_id_absent(None) is True
    assert tk_mod._fact_id_absent("") is True
    assert tk_mod._fact_id_absent(" ") is True
    # Padded fact_id -> ABSENT (X8B-02 padded half CLOSED).
    assert tk_mod._fact_id_absent("SYN-FACT-1 ") is True
    assert tk_mod._fact_id_absent(" SYN-FACT-1") is True
    assert tk_mod._fact_id_absent(1) is True
    assert tk_mod._fact_id_absent(True) is True
    assert tk_mod._fact_id_absent(1.0) is True
    assert tk_mod._fact_id_absent(b"x") is True
    assert tk_mod._fact_id_absent(["x"]) is True
    assert tk_mod._fact_id_absent({"x": 1}) is True


def test_r1_05_then_known_docstring_marks_padded_half_closed():
    """FAMKT-05: _fact_id_absent docstring no longer claims padded stays
    open; it says padded is CLOSED under FAMILY TEXT RULE v2."""
    source = TK_MODULE_PATH.read_text(encoding="utf-8")
    assert "X8B-02" in source
    # Old wording must be gone; new wording must be present.
    assert "stays open" not in source
    assert "padded half is CLOSED" in source or "padded half is closed" in source.lower()


# ---------------------------------------------------------------------------
# FAMKT-02: padded / non-str / unhashable record period_id -> ABSENT
# ---------------------------------------------------------------------------


def test_r1_02_kpi_padded_period_id_emits_period_id_missing():
    """FAMKT-02: a padded period_id in a record is ABSENT and emits
    PERIOD_ID_MISSING. It must NOT match the unpadded expected id."""
    series = list(_kpi_positive_series())
    series[0] = _kpi_record(PERIODS[0] + " ", value=10)
    verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
    _assert_kpi_refused(verdict, "PERIOD_ID_MISSING")
    assert aggregate_sum(tuple(series), periods=PERIODS) is None


def test_r1_02_kpi_padded_period_id_never_added_to_reported_present():
    """FAMKT-02: a padded period_id is excluded from reported_periods and
    yields PERIOD_ABSENT for its expected slot, not a 'present' slot."""
    series = list(_kpi_positive_series())
    series[0] = _kpi_record(PERIODS[0] + " ", value=10)
    verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
    assert PERIODS[0] not in verdict.reported_periods


def test_r1_02_kpi_unhashable_record_period_id_never_raises():
    """FAMKT-02: an unhashable period_id (e.g. a list) must not raise
    TypeError from reported_present.add; the record is ABSENT and emits
    PERIOD_ID_MISSING only."""
    series = list(_kpi_positive_series())
    series[0] = _kpi_record(["SYN-P-1"], value=10)
    try:
        verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
    except TypeError as exc:
        pytest.fail("unhashable period_id raised TypeError: %s" % exc)
    _assert_kpi_refused(verdict, "PERIOD_ID_MISSING")
    assert verdict.allowed is False


# ---------------------------------------------------------------------------
# FAMKT-03: expected_periods only text-present entries are tested
# ---------------------------------------------------------------------------


def test_r1_03_kpi_expected_padded_period_id_yields_period_absent():
    """FAMKT-03: an expected period_id that is padded ("SYN-P-5 ") is
    ABSENT for membership testing and yields PERIOD_ABSENT; it never
    matches a present unpadded id like SYN-P-5."""
    series = _kpi_positive_series()
    expected = PERIODS + ("SYN-P-5 ",)
    verdict = check_kpi_series(series, expected_periods=expected)
    _assert_kpi_refused(verdict, "PERIOD_ABSENT")


class _AlwaysEqual:
    """A non-text expected entry whose ``__eq__`` claims equality with
    everything. ``str.__eq__`` returns NotImplemented for it, so Python
    falls back to this reflected ``__eq__`` and an ``==`` scan would call
    it present."""

    def __eq__(self, other):
        return True

    __hash__ = None


def test_r1_03_kpi_expected_always_equal_object_yields_period_absent():
    """FAMKT-03 (seat kill): the explicit ``_text_present`` gate on the
    expected walk is load-bearing, not redundant with ``_contains``. A
    non-text expected entry that compares equal to every present id
    must still yield PERIOD_ABSENT and must never be reported."""
    series = _kpi_positive_series()
    expected = PERIODS + (_AlwaysEqual(),)
    verdict = check_kpi_series(series, expected_periods=expected)
    _assert_kpi_refused(verdict, "PERIOD_ABSENT")


def test_r1_03_kpi_expected_unhashable_period_never_raises():
    """FAMKT-03: an unhashable expected entry (e.g. ["SYN-P-5"]) must
    never raise from ``in reported_present``. It yields PERIOD_ABSENT
    (and nothing else)."""
    series = _kpi_positive_series()
    expected = PERIODS + (["SYN-P-5"],)
    try:
        verdict = check_kpi_series(series, expected_periods=expected)
    except TypeError as exc:
        pytest.fail("unhashable expected period raised TypeError: %s" % exc)
    _assert_kpi_refused(verdict, "PERIOD_ABSENT")


def test_r1_03_kpi_expected_non_str_int_yields_period_absent():
    """FAMKT-03: a non-str expected entry (1, True, 1.0, b"x") is
    ABSENT and yields PERIOD_ABSENT; never matched, never raises."""
    for value in (1, True, 1.0, b"x"):
        series = _kpi_positive_series()
        expected = PERIODS + (value,)
        try:
            verdict = check_kpi_series(series, expected_periods=expected)
        except TypeError as exc:
            pytest.fail("expected %r raised TypeError: %s" % (value, exc))
        _assert_kpi_refused(verdict, "PERIOD_ABSENT")


# ---------------------------------------------------------------------------
# FAMKT-04: _blank and _present removed from kpi module
# ---------------------------------------------------------------------------


def test_r1_04_kpi_blank_and_present_removed():
    """FAMKT-04: _blank and _present are deleted from
    sni_kpi_missingness_guard (no external callers exist)."""
    source = KPI_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn_names = {
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "_blank" not in fn_names, (
        "kpi module still defines _blank; delete per FAMKT-04"
    )
    assert "_present" not in fn_names, (
        "kpi module still defines _present; delete per FAMKT-04"
    )


# ---------------------------------------------------------------------------
# FAMKT-06 / FAMKT-07: then_known text-present checks on supersedes and edges
# ---------------------------------------------------------------------------


def test_r1_06_then_known_padded_fact_id_emits_fact_id_missing():
    """FAMKT-05/FAMKT-06: a padded fact_id is ABSENT and emits
    FACT_ID_MISSING. The X8B-02 padded half is CLOSED."""
    items = [_tk_item(fact_id="SYN-FACT-1 ")]
    view = then_known_view(items, cutoff=CUTOFF)
    _assert_tk_refused(view, "FACT_ID_MISSING")
    assert view.included == ()


def test_r1_06_then_known_unhashable_fact_id_never_raises():
    """FAMKT-06: an unhashable fact_id never raises; emits FACT_ID_MISSING."""
    items = [_tk_item(fact_id=["x"])]
    try:
        view = then_known_view(items, cutoff=CUTOFF)
    except TypeError as exc:
        pytest.fail("unhashable fact_id raised TypeError: %s" % exc)
    _assert_tk_refused(view, "FACT_ID_MISSING")
    assert view.included == ()


def test_r1_06_then_known_unhashable_fact_id_dict_never_raises():
    """FAMKT-06: a dict-valued fact_id never raises; FACT_ID_MISSING."""
    items = [_tk_item(fact_id={"x": 1})]
    try:
        view = then_known_view(items, cutoff=CUTOFF)
    except TypeError as exc:
        pytest.fail("dict fact_id raised TypeError: %s" % exc)
    _assert_tk_refused(view, "FACT_ID_MISSING")


def test_r1_06_then_known_non_str_fact_id_int_emits_fact_id_missing():
    """FAMKT-06: a non-str fact_id (1, True, 1.0, b"x") is ABSENT and
    emits FACT_ID_MISSING."""
    for value in (1, True, 1.0, b"x"):
        items = [_tk_item(fact_id=value)]
        try:
            view = then_known_view(items, cutoff=CUTOFF)
        except TypeError as exc:
            pytest.fail("fact_id=%r raised TypeError: %s" % (value, exc))
        _assert_tk_refused(view, "FACT_ID_MISSING")


def test_r1_07_then_known_blank_supersedes_still_short_circuits():
    """FAMKT-07: None and "" stay the 'no supersedes' short-circuit
    (pinned by test_a07g_blank_supersedes_treated_as_absent)."""
    items = [
        _tk_item(fact_id="SYN-FACT-1", supersedes=None),
        _tk_item(fact_id="SYN-FACT-2", supersedes=""),
    ]
    view = then_known_view(items, cutoff=CUTOFF)
    _assert_tk_allowed(view)
    assert view.included == ("SYN-FACT-1", "SYN-FACT-2")


def test_r1_07_then_known_padded_supersedes_emits_supersedes_unknown():
    """FAMKT-07: a padded supersedes that does not match any text-present
    fact_id emits SUPERSEDES_UNKNOWN (never raises, never added to edges)."""
    items = [
        _tk_item(fact_id="SYN-FACT-1"),
        _tk_item(fact_id="SYN-FACT-2", supersedes="SYN-FACT-1 "),
    ]
    view = then_known_view(items, cutoff=CUTOFF)
    _assert_tk_refused(view, "SUPERSEDES_UNKNOWN")


def test_r1_07_then_known_unhashable_supersedes_never_raises():
    """FAMKT-07: an unhashable supersedes (list, dict, set) never raises;
    emits SUPERSEDES_UNKNOWN."""
    for value in ([1, 2], {"k": 1}, {1, 2}):
        items = [_tk_item(fact_id="SYN-FACT-1", supersedes=value)]
        try:
            view = then_known_view(items, cutoff=CUTOFF)
        except TypeError as exc:
            pytest.fail("supersedes=%r raised TypeError: %s" % (value, exc))
        _assert_tk_refused(view, "SUPERSEDES_UNKNOWN")


def test_r1_07_then_known_non_str_supersedes_int_emits_supersedes_unknown():
    """FAMKT-07: a non-str supersedes (1, True, 1.0, b"x") never raises;
    emits SUPERSEDES_UNKNOWN."""
    for value in (1, True, 1.0, b"x"):
        items = [_tk_item(fact_id="SYN-FACT-1", supersedes=value)]
        try:
            view = then_known_view(items, cutoff=CUTOFF)
        except TypeError as exc:
            pytest.fail("supersedes=%r raised TypeError: %s" % (value, exc))
        _assert_tk_refused(view, "SUPERSEDES_UNKNOWN")


def test_r1_07_then_known_padded_supersedes_with_padded_target_emits_unknown():
    """FAMKT-07: a padded supersedes whose target is also a padded fact_id
    (neither text-present) emits SUPERSEDES_UNKNOWN without raising."""
    items = [
        _tk_item(fact_id="SYN-FACT-1 "),
        _tk_item(fact_id="SYN-FACT-2", supersedes="SYN-FACT-1 "),
    ]
    try:
        view = then_known_view(items, cutoff=CUTOFF)
    except TypeError as exc:
        pytest.fail("padded->padded path raised TypeError: %s" % exc)
    _assert_tk_refused(view, "SUPERSEDES_UNKNOWN")


# ---------------------------------------------------------------------------
# FAMKT contract invariants: REASONS and AUTHORITY_FLAGS unchanged
# ---------------------------------------------------------------------------


def test_r1_08_kpi_reasons_and_authority_flags_unchanged():
    """REASONS and AUTHORITY_FLAGS are frozen; no new reason codes; every
    authority flag stays literal False."""
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
    assert KPI_STATES == (
        "reported",
        "not_reported",
        "not_applicable",
        "withheld",
    )
    for name in FLAG_NAMES:
        assert KPI_AUTHORITY_FLAGS[name] is False
    kpi_refuse_nonfalse_authority()
    with pytest.raises(TypeError):
        KPI_AUTHORITY_FLAGS["rank_authority"] = True


def test_r1_08_then_known_reasons_and_authority_flags_unchanged():
    """REASONS and AUTHORITY_FLAGS are frozen; no new reason codes; every
    authority flag stays literal False."""
    assert TK_REASONS == (
        "FACT_ID_MISSING",
        "DUPLICATE_FACT_ID",
        "ECONOMIC_TIME_INVALID",
        "OWNER_KNOWN_INVALID",
        "PUBLISHED_INVALID",
        "RETRIEVED_INVALID",
        "OWNER_KNOWN_BEFORE_PUBLISHED",
        "RETRIEVED_BEFORE_PUBLISHED",
        "SUPERSEDES_UNKNOWN",
        "SUPERSEDES_CYCLE",
    )
    for name in FLAG_NAMES:
        assert TK_AUTHORITY_FLAGS[name] is False
    tk_refuse_nonfalse_authority()
    with pytest.raises(TypeError):
        TK_AUTHORITY_FLAGS["rank_authority"] = True


# ---------------------------------------------------------------------------
# Junk-input sweep across period_id, expected, fact_id, supersedes
# ---------------------------------------------------------------------------


def test_r1_09_kpi_junk_period_id_sweep_no_exception():
    """Junk period_id in a record: no exception, allowed False, ABSENT
    reason for every kind of junk."""
    for value in JUNK_VALUES:
        series = list(_kpi_positive_series())
        series[0] = _kpi_record(value, value=10)
        try:
            verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
        except Exception as exc:
            pytest.fail("period_id=%r raised %s" % (value, exc))
        assert verdict.allowed is False, (value, verdict.reasons)
        assert "PERIOD_ID_MISSING" in verdict.reasons, (value, verdict.reasons)


def test_r1_09_kpi_junk_expected_period_sweep_no_exception():
    """Junk expected entry: no exception, allowed False, ABSENT reason."""
    for value in JUNK_VALUES:
        series = _kpi_positive_series()
        expected = PERIODS + (value,)
        try:
            verdict = check_kpi_series(series, expected_periods=expected)
        except Exception as exc:
            pytest.fail("expected=%r raised %s" % (value, exc))
        assert verdict.allowed is False, (value, verdict.reasons)
        assert "PERIOD_ABSENT" in verdict.reasons, (value, verdict.reasons)


def test_r1_09_then_known_junk_fact_id_sweep_no_exception():
    """Junk fact_id: no exception, allowed False, FACT_ID_MISSING."""
    for value in JUNK_FACT_VALUES:
        items = [_tk_item(fact_id=value)]
        try:
            view = then_known_view(items, cutoff=CUTOFF)
        except Exception as exc:
            pytest.fail("fact_id=%r raised %s" % (value, exc))
        assert view.allowed is False, (value, view.reasons)
        assert "FACT_ID_MISSING" in view.reasons, (value, view.reasons)


def test_r1_09_then_known_junk_supersedes_sweep_no_exception():
    """Junk supersedes (non-None, non-""): no exception, allowed False,
    SUPERSEDES_UNKNOWN."""
    for value in JUNK_FACT_VALUES:
        if value is None or value == "":
            continue  # those stay the 'no link' short-circuit
        items = [_tk_item(fact_id="SYN-FACT-1", supersedes=value)]
        try:
            view = then_known_view(items, cutoff=CUTOFF)
        except Exception as exc:
            pytest.fail("supersedes=%r raised %s" % (value, exc))
        assert view.allowed is False, (value, view.reasons)
        assert "SUPERSEDES_UNKNOWN" in view.reasons, (value, view.reasons)


# ---------------------------------------------------------------------------
# Static scans: no normalisation in either module
# ---------------------------------------------------------------------------


def test_r1_10_kpi_no_normalisation_static_scan():
    """No .lower/.upper/.casefold/.strip/.replace attribute calls in kpi."""
    source = KPI_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"lower", "upper", "casefold", "strip", "replace"}
    hits = [
        (n.lineno, n.func.attr) for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in forbidden
    ]
    assert hits == [], hits


def test_r1_10_then_known_no_normalisation_static_scan():
    """No .lower/.upper/.casefold/.strip/.replace attribute calls in
    then_known (already enforced elsewhere; this is a belt-and-braces
    FAMKT re-check that the v2 plumbing did not regress it)."""
    source = TK_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"lower", "upper", "casefold", "strip", "replace"}
    hits = [
        (n.lineno, n.func.attr) for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in forbidden
    ]
    assert hits == [], hits