"""Quality validators + annotation emission (Data OS §D8) — ``lib/dataos/quality.py``.

Every validator here is tested FAIL-THEN-PASS: a checker that returns findings for
everything and a checker that returns findings for nothing both pass a one-sided
test, and only one of those is a guard.  So each family gets a pathological input
that MUST be flagged and a clean input that MUST NOT be.

Two properties get their own tests because both have already shipped dead in this
repo in some form:

* ``check_validity_ohlc`` must SKIP a row with a null leg rather than raise —
  ``data/stocks`` has no ``open`` column at all (§D4), so a validator demanding four
  legs would fail on every row of a real store and be switched off within a day;
* ``emit_annotations`` must print at column 0 with ``flush`` — a logger's prefixing
  format pushes ``::`` off column 0, GitHub drops the annotation, and the alarm looks
  right in review while producing nothing (shipped dead five times: #3487, #3515,
  #3562, #3563, #3570).

Pure unit tests; ``now`` is injected everywhere and nothing reads ``data/``.

Run: .venv/bin/python -m pytest tests/test_dataos_quality.py -q
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lib.dataos.quality import (
    CheckFamily,
    Finding,
    Severity,
    annotation_line,
    check_completeness,
    check_freshness,
    check_referential,
    check_temporal_integrity,
    check_uniqueness,
    check_validity_ohlc,
    emit_annotations,
)
from lib.dataos.temporal import TemporalProfile

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
NAN = float("nan")

CLEAN_BAR = {"ticker": "NVDA", "date": "2024-06-03", "open": 114.0, "high": 116.0,
             "low": 113.5, "close": 114.8, "volume": 1_000_000}
IMPOSSIBLE_BAR = {"ticker": "NVDA", "date": "2024-06-04", "open": 114.0, "high": 110.0,
                  "low": 113.5, "close": 114.8, "volume": 1_000_000}


# ── the vocabulary ───────────────────────────────────────────────────────────
def test_the_nine_families_and_four_severities_are_exactly_the_spec_sets() -> None:
    assert {f.value for f in CheckFamily} == {
        "completeness", "freshness", "uniqueness", "validity", "continuity",
        "distribution", "cross_source_reconciliation", "referential_integrity",
        "temporal_integrity",
    }
    assert {s.value for s in Severity} == {"INFO", "WARN", "DEGRADED", "BLOCK"}


# ── validity: the OHLC fail-then-pass pair ───────────────────────────────────
def test_check_validity_ohlc_flags_the_pathological_row_and_passes_the_clean_one() -> None:
    assert check_validity_ohlc([CLEAN_BAR]) == []

    findings = check_validity_ohlc([IMPOSSIBLE_BAR], dataset_id="equity.bars.daily.stocks")
    assert findings, "a high below the low is an impossible bar and must be flagged"
    assert any("high 110.0 < low 113.5" in f.message for f in findings)
    assert all(f.family is CheckFamily.VALIDITY for f in findings)
    assert all(f.dataset_id == "equity.bars.daily.stocks" for f in findings)


def test_check_validity_ohlc_catches_a_high_below_low() -> None:
    findings = check_validity_ohlc([{"high": 1.0, "low": 2.0}])
    assert len(findings) == 1
    assert findings[0].evidence == {"row_index": 0, "high": 1.0, "low": 2.0}


@pytest.mark.parametrize(
    "row",
    [
        {"high": 10.0, "low": 5.0, "close": 11.0},   # close above high
        {"high": 10.0, "low": 5.0, "open": 4.0},     # open below low
        {"high": 10.0, "low": 5.0, "volume": -1},    # negative volume
    ],
)
def test_each_ohlc_invariant_is_actually_enforced(row: dict) -> None:
    assert check_validity_ohlc([row])


@pytest.mark.parametrize("missing", ["open", "high", "low", "close", "volume"])
def test_a_row_with_a_none_field_is_skipped_not_flagged_and_never_raises(missing: str) -> None:
    """``data/stocks`` has no ``open`` column at all — a validator that demanded four
    legs would fail on every row of a real store."""
    row = dict(CLEAN_BAR)
    row[missing] = None
    assert check_validity_ohlc([row]) == []


@pytest.mark.parametrize("missing", ["open", "high", "low", "close", "volume"])
def test_a_row_with_an_absent_field_is_skipped_too(missing: str) -> None:
    row = {k: v for k, v in CLEAN_BAR.items() if k != missing}
    assert check_validity_ohlc([row]) == []


def test_a_nan_leg_is_skipped_rather_than_compared() -> None:
    """NaN comparisons are all False, so an un-skipped NaN is a SILENT pass — worse
    than a crash.  Skipping it explicitly makes it a null question, not a validity one."""
    assert check_validity_ohlc([{**CLEAN_BAR, "high": NAN}]) == []
    assert check_validity_ohlc([{**CLEAN_BAR, "low": NAN, "high": NAN}]) == []


def test_a_null_leg_does_not_mask_a_real_defect_elsewhere_in_the_same_row() -> None:
    findings = check_validity_ohlc([{"open": None, "high": 1.0, "low": 2.0}])
    assert len(findings) == 1


def test_severity_is_the_callers_decision() -> None:
    findings = check_validity_ohlc([IMPOSSIBLE_BAR], severity=Severity.WARN)
    assert findings and all(f.severity is Severity.WARN for f in findings)


# ── uniqueness ───────────────────────────────────────────────────────────────
def test_check_uniqueness_flags_a_duplicated_grain_key_and_passes_a_clean_frame() -> None:
    rows = [
        {"ticker": "NVDA", "date": "2024-06-03"},
        {"ticker": "NVDA", "date": "2024-06-04"},
    ]
    assert check_uniqueness(rows, ["ticker", "date"]) == []

    dupes = rows + [{"ticker": "NVDA", "date": "2024-06-03", "close": 1.0}]
    findings = check_uniqueness(dupes, ["ticker", "date"])
    assert len(findings) == 1
    assert findings[0].family is CheckFamily.UNIQUENESS
    assert findings[0].severity is Severity.BLOCK
    assert findings[0].evidence["count"] == 2


def test_uniqueness_reports_each_offending_key_once_not_once_per_row() -> None:
    rows = [{"id": "a"}] * 3 + [{"id": "b"}] * 2
    findings = check_uniqueness(rows, ["id"])
    assert len(findings) == 2
    assert [f.evidence["count"] for f in findings] == [3, 2]


def test_an_empty_frame_is_unique() -> None:
    assert check_uniqueness([], ["ticker"]) == []


# ── freshness ────────────────────────────────────────────────────────────────
def test_check_freshness_passes_inside_the_sla_and_flags_outside_it() -> None:
    inside = datetime(2026, 8, 12, 4, 0, tzinfo=timezone.utc)     # 8h old
    assert check_freshness(inside, sla_hours=26, now=NOW) == []

    outside = datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)    # 56h old
    findings = check_freshness(outside, sla_hours=26, now=NOW, dataset_id="macro.fred.observations")
    assert len(findings) == 1
    assert findings[0].family is CheckFamily.FRESHNESS
    assert findings[0].evidence["age_hours"] == pytest.approx(56.0)


def test_freshness_is_pure_and_reads_the_injected_clock_not_the_wall_clock() -> None:
    ts = "2026-08-12T11:00:00+00:00"
    assert check_freshness(ts, sla_hours=2, now=NOW) == []
    assert check_freshness(ts, sla_hours=0.5, now=NOW)


def test_an_empty_dataset_is_a_freshness_failure_with_an_unbounded_age() -> None:
    """``age_hours: None`` deliberately, not a magic number a consumer could average."""
    findings = check_freshness(None, sla_hours=26, now=NOW)
    assert len(findings) == 1
    assert findings[0].evidence["age_hours"] is None


# ── completeness ─────────────────────────────────────────────────────────────
def test_check_completeness_distinguishes_absent_from_null() -> None:
    rows = [
        {"ticker": "NVDA", "close": 1.0},
        {"ticker": "AMD", "close": None},
        {"ticker": "INTC"},
    ]
    findings = check_completeness(rows, ["ticker", "close"])
    assert len(findings) == 2
    assert findings[0].evidence == {"row_index": 1, "key": "close", "present": True}
    assert findings[1].evidence == {"row_index": 2, "key": "close", "present": False}


def test_a_complete_frame_produces_nothing() -> None:
    assert check_completeness([{"a": 1, "b": 2}], ["a", "b"]) == []


# ── referential integrity ────────────────────────────────────────────────────
def test_check_referential_flags_a_member_the_master_does_not_carry() -> None:
    """The MMC incident from the other side: a basket of 19 whose price store answers
    for 18, with nothing anywhere comparing the two."""
    known = {"SEC:US-XNYS-MMC", "SEC:US-XNAS-FISV"}
    rows = [{"security_id": "SEC:US-XNYS-MMC"}, {"security_id": "SEC:US-XNYS-GHOST"}]
    findings = check_referential(rows, "security_id", known)
    assert len(findings) == 1
    assert findings[0].family is CheckFamily.REFERENTIAL
    assert findings[0].evidence["value"] == "SEC:US-XNYS-GHOST"

    assert check_referential(rows[:1], "security_id", known) == []


def test_a_null_id_is_a_completeness_question_not_a_referential_one() -> None:
    assert check_referential([{"security_id": None}], "security_id", {"SEC:X"}) == []


# ── temporal integrity ───────────────────────────────────────────────────────
def test_a_known_at_in_the_future_is_flagged() -> None:
    rows = [{"published_at": "2026-08-20T00:00:00+00:00", "ingested_at": "2026-08-20T01:00:00+00:00"}]
    findings = check_temporal_integrity(rows, TemporalProfile.REVISABLE_RELEASE, now=NOW)
    assert len(findings) == 1
    assert "FUTURE" in findings[0].message
    assert findings[0].family is CheckFamily.TEMPORAL_INTEGRITY


def test_a_known_at_in_the_past_is_clean() -> None:
    rows = [{"published_at": "2026-08-10T00:00:00+00:00"}]
    assert check_temporal_integrity(rows, TemporalProfile.REVISABLE_RELEASE, now=NOW) == []


def test_effective_at_before_period_end_is_flagged() -> None:
    """Information cannot become applicable before the interval it describes closed."""
    rows = [{
        "ingested_at": "2026-07-02T00:00:00+00:00",
        "effective_at": "2026-06-15T00:00:00+00:00",
        "period_end": "2026-06-30T00:00:00+00:00",
    }]
    findings = check_temporal_integrity(rows, TemporalProfile.SNAPSHOT_SERIES, now=NOW)
    assert len(findings) == 1
    assert "precedes period_end" in findings[0].message


def test_effective_at_on_or_after_period_end_is_clean() -> None:
    rows = [{
        "ingested_at": "2026-07-02T00:00:00+00:00",
        "effective_at": "2026-06-30T00:00:00+00:00",
        "period_end": "2026-06-30T00:00:00+00:00",
    }]
    assert check_temporal_integrity(rows, TemporalProfile.SNAPSHOT_SERIES, now=NOW) == []


def test_a_row_whose_known_at_is_unanswerable_becomes_a_finding_not_a_crash() -> None:
    """A checker that dies on row 3 tells you nothing about rows 4..n."""
    rows = [{"value": 1.0}, {"published_at": "2026-08-10T00:00:00+00:00"}]
    findings = check_temporal_integrity(rows, TemporalProfile.REVISABLE_RELEASE, now=NOW)
    assert len(findings) == 1
    assert findings[0].evidence["row_index"] == 0
    assert "unanswerable" in findings[0].message


def test_now_is_keyword_only_and_has_no_default_so_the_check_stays_pure() -> None:
    with pytest.raises(TypeError):
        check_temporal_integrity([], TemporalProfile.BARS)      # type: ignore[call-arg]


# ── annotations ──────────────────────────────────────────────────────────────
ANNOTATION_CASES = [
    (Severity.INFO, "::notice"),
    (Severity.WARN, "::warning"),
    (Severity.DEGRADED, "::warning"),
    (Severity.BLOCK, "::error"),
]


@pytest.mark.parametrize("severity, prefix", ANNOTATION_CASES)
def test_each_severity_maps_to_a_github_annotation_level(severity, prefix) -> None:
    line = annotation_line(Finding(CheckFamily.VALIDITY, severity, "ds", "boom", {}))
    assert line.startswith(prefix)
    assert "title=validity-" in line


def test_emit_annotations_writes_at_column_zero_and_flushes(capsys) -> None:
    """A logger's prefixing format pushes ``::`` off column 0 and GitHub drops the
    annotation entirely — the failure guarded by tests/test_gh_annotation_line_start.py."""
    findings = check_validity_ohlc([IMPOSSIBLE_BAR], dataset_id="equity.bars.daily.stocks")
    count = emit_annotations(findings)
    out = capsys.readouterr().out.splitlines()

    assert count == len(findings) == len(out)
    for line in out:
        assert line.startswith("::"), f"annotation not at column 0: {line!r}"
        assert "::error title=validity-block::" in line
        assert "equity.bars.daily.stocks" in line


def test_an_annotation_is_a_single_line_even_when_the_message_wraps() -> None:
    """A multi-line annotation body silently truncates in the Actions summary."""
    finding = Finding(CheckFamily.FRESHNESS, Severity.DEGRADED, "ds",
                      "a message\nthat wrapped\n   across lines", {})
    line = annotation_line(finding)
    assert "\n" not in line
    assert "a message that wrapped across lines" in line


def test_emitting_nothing_prints_nothing(capsys) -> None:
    assert emit_annotations([]) == 0
    assert capsys.readouterr().out == ""


# ── C03: cross-source agreement inspector ──
import dataclasses  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
from decimal import Decimal  # noqa: E402
from fractions import Fraction  # noqa: E402

from lib.dataos.quality import (  # noqa: E402
    AgreementInspection,
    AgreementState,
    AgreementTolerance,
    DiscrepancyCause,
    InspectionOutcome,
    PairObservation,
    RatioStep,
    SourceSemantics,
    agreement_findings,
    inspect_agreement,
)


def _c03_sem(**over) -> SourceSemantics:
    """A fully declared source; everything can be overridden per test."""
    declared = dict(
        source_id="vendor_a", generation="g1", instrument="NVDA@XNYS",
        session="REGULAR", currency="USD", price_type="CONSOLIDATED_CLOSE",
        timestamp_convention="SESSION_CLOSE_LOCAL", basis="SADJ",
        adjustment_reference="actions@2026-06-30", unit="USD/share",
    )
    declared.update(over)
    return SourceSemantics(**declared)


def _c03_rows(pairs) -> list[dict]:
    return [{"date": d, "close": v} for d, v in pairs]


_C03_TOL = AgreementTolerance(precision="0.0001", within="0.0005", minor="0.005")


def _c03_inspect(left_pairs, right_pairs, *, left_sem=None, right_sem=None,
                 keys=("date",), value_col="close", tol=None, min_overlap=1):
    return inspect_agreement(
        _c03_rows(left_pairs),
        left_sem if left_sem is not None else _c03_sem(),
        _c03_rows(right_pairs),
        right_sem if right_sem is not None else _c03_sem(source_id="vendor_b"),
        keys=keys if isinstance(keys, str) else list(keys), value_col=value_col,
        tolerance=tol if tol is not None else _C03_TOL, min_overlap=min_overlap)


def test_C03_agreement_vocabulary_is_exactly_the_section_7_set() -> None:
    assert [(s.name, s.value) for s in AgreementState] == [
        (name, name) for name in (
            "AGREE", "WITHIN_TOLERANCE", "DISCREPANT_MINOR",
            "DISCREPANT_MAJOR", "UNRESOLVED",
        )
    ]


def test_C03_outcome_and_cause_vocabularies_are_closed() -> None:
    assert [o.name for o in InspectionOutcome] == [
        "COMPARED", "INCOMPATIBLE", "INSUFFICIENT_OVERLAP", "DUPLICATE_KEY"]
    assert [c.name for c in DiscrepancyCause] == ["SEMANTIC_DIFFERENCE", "UNKNOWN"]
    for vocabulary in (InspectionOutcome, DiscrepancyCause):
        for member in vocabulary:
            for banned in ("VENDOR", "ERROR", "WRONG", "FACTOR"):
                assert banned not in member.name


def test_C03_declarations_are_keyword_only_without_defaults() -> None:
    params = inspect.signature(inspect_agreement).parameters
    for name in ("keys", "value_col", "tolerance", "min_overlap"):
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, name
        assert params[name].default is inspect.Parameter.empty, name


@pytest.mark.parametrize("kwargs, exc", [
    ({"precision": 0.0001}, TypeError),
    ({"within": True}, TypeError),
    ({"precision": Fraction(-1, 100)}, ValueError),
    ({"within": "0.5", "minor": "0.1"}, ValueError),
    ({"precision": "not a number"}, ValueError),
    ({"precision": Decimal("NaN")}, ValueError),
])
def test_C03_tolerance_refuses_inexact_or_incoherent_declarations(kwargs, exc) -> None:
    declared = {"precision": "0.0001", "within": "0.0005", "minor": "0.005"}
    declared.update(kwargs)
    with pytest.raises(exc, match=r"precision|within|minor"):
        AgreementTolerance(**declared)


def test_C03_tolerance_normalises_exactly_to_fractions() -> None:
    tol = AgreementTolerance(precision=1, within=Decimal("0.0005"),
                             minor=Fraction(1, 200))
    assert type(tol.precision) is Fraction and tol.precision == Fraction(1)
    assert tol.within == Fraction("0.0005") == Fraction(1, 2000)
    assert tol.minor == Fraction(1, 200)
    assert AgreementTolerance("0.0001", "1/2000", "0.005") == AgreementTolerance(
        Fraction(1, 10000), Decimal("0.0005"), Fraction(1, 200))


@pytest.mark.parametrize("field", [
    "source_id", "generation", "instrument", "session", "currency",
    "price_type", "timestamp_convention", "basis", "unit",
])
def test_C03_semantics_refuse_an_empty_declaration(field) -> None:
    with pytest.raises(ValueError, match=field):
        _c03_sem(**{field: "   "})


def test_C03_semantics_allow_an_empty_adjustment_reference_only() -> None:
    assert _c03_sem(adjustment_reference="").adjustment_reference == ""
    for field in ("source_id", "generation", "instrument", "session", "currency",
                  "price_type", "timestamp_convention", "basis", "unit"):
        with pytest.raises(ValueError):
            _c03_sem(**{field: ""})
    with pytest.raises(ValueError):
        _c03_sem(currency=5)


@pytest.mark.parametrize("kwargs, exc", [
    ({"keys": []}, ValueError),
    ({"keys": "date"}, TypeError),
    ({"value_col": "date"}, ValueError),
    ({"min_overlap": 0}, ValueError),
    ({"min_overlap": True}, TypeError),
    ({"min_overlap": 1.0}, TypeError),
    ({"tolerance": ("0.0001", "0.0005", "0.005")}, TypeError),
    ({"left_sem": ("vendor_a", "g1")}, TypeError),
])
def test_C03_malformed_call_declarations_raise(kwargs, exc) -> None:
    with pytest.raises(exc):
        _c03_inspect([("2026-06-01", 100)], [("2026-06-01", 100)], **kwargs)


# ── C03.01: a replay of one generation must agree within precision ──────────
def test_C03_01_same_generation_replay_agrees_within_precision() -> None:
    pairs = [(f"2026-06-0{d}", Decimal("100.00") + d) for d in range(1, 6)]
    insp = _c03_inspect(pairs, pairs, right_sem=_c03_sem())
    assert insp.outcome is InspectionOutcome.COMPARED
    assert insp.same_generation is True
    assert insp.state is AgreementState.AGREE
    assert insp.cause is None
    assert all(o.state is AgreementState.AGREE for o in insp.observations)
    assert agreement_findings(insp) == []


def test_C03_01_same_generation_beyond_precision_is_major() -> None:
    insp = _c03_inspect(
        [("2026-06-01", Decimal("100.00"))],
        [("2026-06-01", Decimal("100.01"))],
        right_sem=_c03_sem(),
    )
    assert insp.same_generation is True
    assert insp.outcome is InspectionOutcome.COMPARED
    assert insp.state is AgreementState.DISCREPANT_MAJOR
    assert insp.cause is DiscrepancyCause.UNKNOWN
    assert insp.observations[0].state is AgreementState.DISCREPANT_MAJOR


def test_C03_01_the_same_difference_between_independent_sources_is_within_tolerance() -> None:
    insp = _c03_inspect(
        [("2026-06-01", Decimal("100.00"))],
        [("2026-06-01", Decimal("100.01"))],
    )
    assert insp.same_generation is False
    assert insp.outcome is InspectionOutcome.COMPARED
    assert insp.state is AgreementState.WITHIN_TOLERANCE
    assert insp.cause is None
    assert insp.observations[0].state is AgreementState.WITHIN_TOLERANCE


def test_C03_01_independent_discrepancy_is_retained_unresolved() -> None:
    first_left, first_right = 100.0, 100.5
    insp = _c03_inspect(
        [("2026-06-01", first_left), ("2026-06-02", 200.0)],
        [("2026-06-01", first_right), ("2026-06-02", 220.0)],
    )
    assert insp.outcome is InspectionOutcome.COMPARED
    assert insp.state is AgreementState.UNRESOLVED
    assert insp.cause is DiscrepancyCause.UNKNOWN
    assert [o.state for o in insp.observations] == [
        AgreementState.DISCREPANT_MINOR, AgreementState.DISCREPANT_MAJOR]
    # the raw values are retained exactly as given — identity, not a copy
    assert insp.observations[0].left is first_left
    assert insp.observations[0].right is first_right
    assert insp.counts() == {"AGREE": 0, "WITHIN_TOLERANCE": 0,
                             "DISCREPANT_MINOR": 1, "DISCREPANT_MAJOR": 1,
                             "UNRESOLVED": 0}


def test_C03_01_band_boundaries_are_inclusive_and_exact() -> None:
    base = [("2026-06-01", Fraction(100))]
    # d == within * m exactly:  b = a / (1 - within)
    within_edge = Fraction(200000, 1999)
    insp = _c03_inspect(base, [("2026-06-01", within_edge)])
    assert insp.observations[0].state is AgreementState.WITHIN_TOLERANCE
    assert insp.observations[0].rel_diff == _C03_TOL.within
    # d == minor * m exactly:  b = a / (1 - minor)
    minor_edge = Fraction(20000, 199)
    insp = _c03_inspect(base, [("2026-06-01", minor_edge)])
    assert insp.observations[0].state is AgreementState.DISCREPANT_MINOR
    assert insp.observations[0].rel_diff == _C03_TOL.minor
    # one unit beyond the minor band → the next band
    insp = _c03_inspect(base, [("2026-06-01", Fraction(101))])
    assert insp.observations[0].state is AgreementState.DISCREPANT_MAJOR


# ── C03.02: semantics first; values across a difference are never compared ──
def test_C03_02_raw_against_split_adjusted_is_incompatible() -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100)], [("2026-06-01", 100)],
        right_sem=_c03_sem(source_id="vendor_b", basis="RAW",
                           adjustment_reference=""),
    )
    assert insp.outcome is InspectionOutcome.INCOMPATIBLE
    assert insp.state is AgreementState.UNRESOLVED
    assert insp.cause is DiscrepancyCause.SEMANTIC_DIFFERENCE
    assert insp.explanation[0] == ("basis", "SADJ", "RAW")
    assert insp.overlap is None and insp.observations == ()
    assert agreement_findings(insp)[0].family is CheckFamily.CROSS_SOURCE


def test_C03_02_total_return_adjusted_is_never_compared_with_a_printed_price() -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100)], [("2026-06-01", 100)],
        left_sem=_c03_sem(basis="TRADJ"),
        right_sem=_c03_sem(source_id="vendor_b", basis="RAW",
                           adjustment_reference=""),
    )
    assert insp.outcome is InspectionOutcome.INCOMPATIBLE
    assert insp.cause is DiscrepancyCause.SEMANTIC_DIFFERENCE
    assert insp.explanation[0] == ("basis", "TRADJ", "RAW")


def test_C03_02_closing_auction_against_consolidated_is_incompatible() -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100)], [("2026-06-01", 100)],
        right_sem=_c03_sem(source_id="vendor_b", price_type="CLOSING_AUCTION"),
    )
    assert insp.outcome is InspectionOutcome.INCOMPATIBLE
    assert insp.explanation == (
        ("price_type", "CONSOLIDATED_CLOSE", "CLOSING_AUCTION"),)


@pytest.mark.parametrize("field, other", [
    ("instrument", "NVDA@XNAS"),
    ("session", "EXTENDED"),
    ("currency", "GBX"),
    ("price_type", "CLOSING_AUCTION"),
    ("timestamp_convention", "UTC_STAMPED"),
    ("basis", "RAW"),
    ("adjustment_reference", "actions@2026-09-30"),
    ("unit", "USD"),
])
def test_C03_02_any_single_semantic_difference_is_incompatible(field, other) -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100)], [("2026-06-01", 100)],
        right_sem=_c03_sem(source_id="vendor_b", **{field: other}),
    )
    assert insp.outcome is InspectionOutcome.INCOMPATIBLE
    assert insp.cause is DiscrepancyCause.SEMANTIC_DIFFERENCE
    assert insp.explanation == ((field, getattr(_c03_sem(), field), other),)


def test_C03_02_two_generations_of_one_source_are_incompatible() -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100)], [("2026-06-01", 100)],
        right_sem=_c03_sem(generation="g2"),
    )
    assert insp.same_generation is False
    assert insp.outcome is InspectionOutcome.INCOMPATIBLE
    assert insp.explanation == (("generation", "g1", "g2"),)
    assert insp.explanation[-1][0] == "generation"


def test_C03_02_incompatible_rows_are_never_examined() -> None:
    class _Boom:
        def __iter__(self):
            raise AssertionError("rows must never be examined for an incompatible pair")

    insp = inspect_agreement(
        _Boom(), _c03_sem(), _Boom(),
        _c03_sem(source_id="vendor_b", basis="RAW", adjustment_reference=""),
        keys=["date"], value_col="close", tolerance=_C03_TOL, min_overlap=1)
    assert insp.outcome is InspectionOutcome.INCOMPATIBLE
    assert insp.observations == () and insp.overlap is None


def test_C03_02_the_inspection_carries_no_consensus_value() -> None:
    assert [f.name for f in dataclasses.fields(AgreementInspection)] == [
        "outcome", "state", "cause", "same_generation", "explanation", "overlap",
        "left_only", "right_only", "left_unkeyed", "right_unkeyed",
        "duplicate_keys", "observations", "ratio_step",
    ]
    insp = _c03_inspect([("2026-06-01", 100)], [("2026-06-01", 100.5)])
    banned = ("score", "consensus", "golden", "value", "mean", "average",
              "winner", "preferred", "reconciled", "best")
    for attr in dir(insp):
        for word in banned:
            assert word not in attr.lower(), attr


def test_C03_02_the_verdict_is_symmetric() -> None:
    left_pairs = [("2026-06-01", 100), ("2026-06-02", 200)]
    right_pairs = [("2026-06-01", 100.5), ("2026-06-02", 220)]
    vendor_b = _c03_sem(source_id="vendor_b")
    forward = _c03_inspect(left_pairs, right_pairs)
    backward = inspect_agreement(
        _c03_rows(right_pairs), vendor_b, _c03_rows(left_pairs), _c03_sem(),
        keys=["date"], value_col="close", tolerance=_C03_TOL, min_overlap=2)
    assert backward.outcome is forward.outcome
    assert backward.state is forward.state
    assert backward.cause is forward.cause
    assert [o.state for o in backward.observations] == \
        [o.state for o in forward.observations]
    assert backward.left_only == forward.right_only
    assert backward.right_only == forward.left_only


# ── C03.03: overlap, history depth and step boundaries ──────────────────────
def test_C03_03_disjoint_sampled_dates_are_insufficient_overlap() -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100), ("2026-06-02", 101), ("2026-06-03", 102)],
        [("2026-06-08", 100), ("2026-06-09", 101), ("2026-06-10", 102)],
    )
    assert insp.outcome is InspectionOutcome.INSUFFICIENT_OVERLAP
    assert insp.state is AgreementState.UNRESOLVED
    assert insp.cause is DiscrepancyCause.UNKNOWN
    assert insp.overlap == 0 and insp.left_only == 3 and insp.right_only == 3
    assert insp.left_unkeyed == 0 and insp.right_unkeyed == 0
    assert insp.observations == () and insp.ratio_step is None


def test_C03_03_min_overlap_is_the_declared_threshold() -> None:
    pairs = [(f"2026-06-0{d}", 100) for d in range(1, 4)]
    at_threshold = _c03_inspect(pairs, pairs, min_overlap=3)
    assert at_threshold.outcome is InspectionOutcome.COMPARED
    below_threshold = _c03_inspect(pairs, pairs, min_overlap=4)
    assert below_threshold.outcome is InspectionOutcome.INSUFFICIENT_OVERLAP


def test_C03_03_deeper_history_on_one_side_never_funds_a_step() -> None:
    left_pairs = [(f"2026-05-{d:02d}", 200) for d in range(1, 8)] + \
        [("2026-06-01", 100), ("2026-06-02", 100)]
    insp = _c03_inspect(left_pairs, [("2026-06-01", 100), ("2026-06-02", 100)])
    assert insp.outcome is InspectionOutcome.COMPARED
    assert insp.state is AgreementState.AGREE
    assert insp.ratio_step is None
    assert insp.left_only == 7
    assert insp.overlap == 2


def test_C03_03_a_step_boundary_is_the_interval_between_sampled_keys() -> None:
    keys = ["2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22"]
    insp = _c03_inspect(
        [(k, 100) for k in keys],
        [(keys[0], 200), (keys[1], 200), (keys[2], 100), (keys[3], 100)],
    )
    step = insp.ratio_step
    assert isinstance(step, RatioStep)
    assert step.boundary == (("2026-06-08",), ("2026-06-15",))
    assert (step.first_run, step.second_run) == (2, 2)
    assert step.before == Fraction(2) and step.after == Fraction(1)
    # the boundary is an interval, never an inferred event date
    assert len(step.boundary) == 2


def test_C03_a_one_sided_factor_shows_a_step_but_names_no_cause() -> None:
    keys = ["2026-06-01", "2026-06-02", "2026-06-03",
            "2026-06-04", "2026-06-05", "2026-06-06"]
    insp = _c03_inspect(
        [(k, 100) for k in keys],
        [(k, 200) for k in keys[:3]] + [(k, 100) for k in keys[3:]],
    )
    assert insp.outcome is InspectionOutcome.COMPARED
    assert [o.state for o in insp.observations[:3]] == \
        [AgreementState.DISCREPANT_MAJOR] * 3
    assert [o.state for o in insp.observations[3:]] == [AgreementState.AGREE] * 3
    assert insp.state is AgreementState.UNRESOLVED
    assert insp.cause is DiscrepancyCause.UNKNOWN
    step = insp.ratio_step
    assert step is not None
    assert step.before == Fraction(2) and step.after == Fraction(1)
    assert step.first_run == 3 and step.second_run == 3
    message = agreement_findings(insp)[0].message
    for word in ("factor", "split", "adjustment", "cause"):
        assert word not in message.lower()


# ── C03.04: unknown causes stay unknown; a missing value is never zero ──────
def test_C03_04_irregular_discrepancies_have_no_step_and_no_named_cause() -> None:
    offsets = ["0.05", "-0.03", "0.9", "0.1", "0.02"]
    insp = _c03_inspect(
        [(f"2026-06-{d:02d}", Fraction(100)) for d in range(1, 6)],
        [(f"2026-06-{d:02d}", Fraction(100) + Fraction(offsets[i]))
         for i, d in enumerate(range(1, 6))],
    )
    assert insp.outcome is InspectionOutcome.COMPARED
    assert insp.state is AgreementState.UNRESOLVED
    assert insp.cause is DiscrepancyCause.UNKNOWN
    assert insp.ratio_step is None
    assert insp.counts()["DISCREPANT_MAJOR"] == 1   # 0.9
    assert insp.counts()["DISCREPANT_MINOR"] == 1   # 0.1
    assert insp.counts()["WITHIN_TOLERANCE"] == 3


@pytest.mark.parametrize("bad", [None, NAN, True, "ABSENT"])
def test_C03_04_a_missing_value_is_unresolved_never_zero(bad) -> None:
    left_rows = [{"date": "2026-06-01", "close": 0}]
    right_rows = (
        [{"date": "2026-06-01"}] if bad == "ABSENT"
        else [{"date": "2026-06-01", "close": bad}])
    insp = inspect_agreement(
        left_rows, _c03_sem(), right_rows, _c03_sem(source_id="vendor_b"),
        keys=["date"], value_col="close", tolerance=_C03_TOL, min_overlap=1)
    obs = insp.observations[0]
    assert obs.state is AgreementState.UNRESOLVED
    assert obs.abs_diff is None and obs.rel_diff is None
    assert insp.state is AgreementState.UNRESOLVED
    assert insp.cause is DiscrepancyCause.UNKNOWN


# ── grain, exactness, inputs ────────────────────────────────────────────────
def test_C03_duplicate_keys_are_a_finding_not_a_crash() -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100), ("2026-06-01", 101), ("2026-06-02", 100)],
        [("2026-06-03", 100), ("2026-06-03", 100), ("2026-06-02", 100)],
    )
    assert insp.outcome is InspectionOutcome.DUPLICATE_KEY
    assert insp.state is AgreementState.UNRESOLVED
    assert insp.cause is DiscrepancyCause.UNKNOWN
    assert insp.duplicate_keys == (
        ("left", ("2026-06-01",)), ("right", ("2026-06-03",)))
    assert insp.observations == () and insp.overlap is None
    findings = agreement_findings(insp, dataset_id="tape")
    assert len(findings) == 1
    assert findings[0].family is CheckFamily.CROSS_SOURCE
    assert findings[0].evidence["duplicate_key_count"] == 2


def test_C03_unkeyed_rows_are_counted_not_compared() -> None:
    insp = _c03_inspect(
        [("2026-06-01", 100), (None, 999)],
        [("2026-06-01", 100.5)],
    )
    assert insp.outcome is InspectionOutcome.COMPARED
    assert insp.left_unkeyed == 1 and insp.right_unkeyed == 0
    assert len(insp.observations) == 1
    assert all(o.key != (None,) for o in insp.observations)


def test_C03_float_values_compare_by_shortest_repr_exactly() -> None:
    # 114.8 / 57.4 is exactly Fraction(2) under shortest-repr conversion
    keys = ["2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22"]
    insp = _c03_inspect(
        [(k, 57.4) for k in keys],
        [(keys[0], 114.8), (keys[1], 114.8), (keys[2], 57.4), (keys[3], 57.4)],
    )
    assert insp.ratio_step is not None
    assert insp.ratio_step.before == Fraction(2)
    assert insp.ratio_step.after == Fraction(1)
    # 0.1 + 0.2 vs 0.3: an exact comparison, within the declared precision
    insp = _c03_inspect([("2026-06-01", 0.1 + 0.2)], [("2026-06-01", 0.3)])
    obs = insp.observations[0]
    assert obs.state is AgreementState.AGREE
    assert obs.abs_diff == Fraction(4, 10 ** 17)


def test_C03_generators_are_accepted_and_inputs_are_not_mutated() -> None:
    left_rows = [{"date": "2026-06-01", "close": 100},
                 {"date": "2026-06-02", "close": 101}]
    right_rows = [{"date": "2026-06-01", "close": 100.5},
                  {"date": "2026-06-02", "close": 101}]
    # a deepcopy before/after (rows are JSON scalars, so a json round-trip is one)
    left_before = json.loads(json.dumps(left_rows))
    right_before = json.loads(json.dumps(right_rows))
    insp = inspect_agreement(
        (row for row in left_rows), _c03_sem(),
        (row for row in right_rows), _c03_sem(source_id="vendor_b"),
        keys=["date"], value_col="close", tolerance=_C03_TOL, min_overlap=1)
    assert insp.outcome is InspectionOutcome.COMPARED
    assert left_rows == left_before and right_rows == right_before
    assert isinstance(insp.observations[0], PairObservation)


# ── findings ────────────────────────────────────────────────────────────────
def test_C03_findings_are_cross_source_with_bounded_json_evidence() -> None:
    keys = [f"2026-06-{d:02d}" for d in range(1, 13)]
    insp = _c03_inspect([(k, 100) for k in keys], [(k, 200) for k in keys])
    findings = agreement_findings(insp, dataset_id="tape")
    assert len(findings) == 1
    finding = findings[0]
    assert finding.family is CheckFamily.CROSS_SOURCE
    assert finding.severity is Severity.WARN
    assert finding.dataset_id == "tape"
    evidence = finding.evidence
    assert set(evidence) == {
        "outcome", "state", "cause", "same_generation", "explanation", "overlap",
        "left_only", "right_only", "left_unkeyed", "right_unkeyed",
        "duplicate_keys", "duplicate_key_count", "counts", "sample", "ratio_step",
    }
    assert len(evidence["sample"]) == 5  # 12 discrepant observations, bounded
    assert evidence["sample"][0][3] == AgreementState.DISCREPANT_MAJOR.value
    assert json.dumps(evidence)  # JSON-serialisable
    assert annotation_line(finding).startswith("::")


def test_C03_agreement_yields_no_finding() -> None:
    pairs = [("2026-06-01", 100), ("2026-06-02", 101)]
    assert agreement_findings(_c03_inspect(pairs, pairs)) == []
    near = _c03_inspect(
        [("2026-06-01", 100)], [("2026-06-01", 100.01)])
    assert near.state is AgreementState.WITHIN_TOLERANCE
    assert agreement_findings(near, dataset_id="tape") == []


def test_C03_finding_severity_is_the_callers_declaration() -> None:
    insp = _c03_inspect([("2026-06-01", 100)], [("2026-06-01", 200)])
    (finding,) = agreement_findings(insp, dataset_id="tape",
                                    severity=Severity.BLOCK)
    assert finding.severity is Severity.BLOCK
    assert annotation_line(finding).startswith(
        "::error title=cross_source_reconciliation-block::")


def test_C03_finding_text_names_no_cause_or_winner() -> None:
    incompatible = _c03_inspect(
        [("2026-06-01", 100)], [("2026-06-01", 100)],
        right_sem=_c03_sem(source_id="vendor_b", basis="RAW",
                           adjustment_reference=""))
    unresolved = _c03_inspect(
        [("2026-06-01", 100), ("2026-06-02", 200)],
        [("2026-06-01", 100.5), ("2026-06-02", 220)])
    banned = ("consensus", "golden", "score", "wrong", "error by", "vendor is",
              "factor", "split", "cause")
    for insp in (incompatible, unresolved):
        message = agreement_findings(insp)[0].message
        assert "not in agreement; retained, not reconciled" in message or \
            "the declarations differ on" in message
        for word in banned:
            assert word not in message.lower(), word
