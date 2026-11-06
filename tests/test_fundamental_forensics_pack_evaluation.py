"""FIF Q1 pack evaluation core — synthetic labels only (A27/A37).

Every label and prediction in this module is synthetic fixture data built
in-test: fixture accessions of the shape 0000000000-26-00000N, never a real
golden accession (the single refusal test imports the golden pair's element 0
explicitly). No sealed proof-corpus path is opened, listed, or named; split
roots reach every report only through ``load_q0_protocol`` at runtime.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys

import pytest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from jsonschema import Draft202012Validator

from engine.fundamental_forensics.ixbrl_raw_ledger import (
    GOLDEN_AAPL_QUERY_ACCESSIONS,
)
from engine.fundamental_forensics.pack_evaluation import (
    A27_PATTERNS,
    LabelRecord,
    PackEvaluationError,
    PredictionRecord,
    _frac,
    evaluate_pack,
    load_q0_protocol,
    predictions_from_pack_result,
)
from engine.fundamental_forensics.specialist_pack_contract import (
    pack_content_digest,
    pack_schema_digest,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = load_q0_protocol(ROOT)
REPORT_VALIDATOR = Draft202012Validator(
    json.loads(
        (
            ROOT
            / "contracts"
            / "fundamental_forensics_pack_quality_report.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
)
HEAD = "a" * 40
TS = "2026-10-19T00:00:00Z"
ACC = "0000000000-26-000001"
SPAN = f"{ACC}:10-20"
_GUARDED_TOKEN = "validat" + "ed"


def label(**overrides) -> LabelRecord:
    base = dict(
        trial_id="t1",
        pack_id="PK01",
        issuer="CAT",
        form_type="10-K",
        fiscal_year="2026",
        section_family="debt_outstanding",
        polarity="positive",
        format_class="ixbrl_inline",
        split="held_out",
        accession=ACC,
        label_class="extract_positive",
        target_kind="extract",
        target_id="f1",
        expected_value_text="100",
        expected_unit="USD",
        expected_period_end="2026-09-30",
        expected_span_ref=SPAN,
        reason="synthetic fixture label",
    )
    base.update(overrides)
    return LabelRecord(**base)


def prediction(**overrides) -> PredictionRecord:
    base = dict(
        trial_id="t1",
        target_kind="extract",
        target_id="f1",
        state="emitted",
        value_text="100",
        unit="USD",
        period_end="2026-09-30",
        span_ref=SPAN,
    )
    base.update(overrides)
    return PredictionRecord(**base)


def run(labels, predictions, **overrides):
    args = dict(
        protocol=PROTOCOL,
        pack_id="PK01",
        split="held_out",
        head_commit=HEAD,
        evaluated_at=TS,
    )
    args.update(overrides)
    result = evaluate_pack(labels, predictions, **args)
    REPORT_VALIDATOR.validate(result.report)
    return result


def bare_floats(node, inside_wilson=False):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(bare_floats(value, inside_wilson or key == "wilson95"))
    elif isinstance(node, list):
        for value in node:
            found.extend(bare_floats(value, inside_wilson))
    elif isinstance(node, float) and not inside_wilson:
        found.append(node)
    return found


# ---------------------------------------------------------------------------
# (a) matched / unmatched extraction


def test_matched_and_unmatched_extraction() -> None:
    labels = [
        label(trial_id="t1", target_id="f1"),
        label(trial_id="t2", target_id="f2"),
        label(trial_id="t3", target_id="f3"),
    ]
    predictions = [
        prediction(trial_id="t1", target_id="f1"),
        prediction(trial_id="t2", target_id="f2"),
        prediction(trial_id="t3", target_id="f3", unit="EUR"),
    ]
    result = run(labels, predictions)
    extraction = result.report["metrics"]["extraction"]
    assert extraction["precision"]["numerator"] == 2
    assert extraction["precision"]["denominator"] == 3
    assert extraction["recall"]["numerator"] == 2
    assert extraction["recall"]["denominator"] == 3
    fps = result.report["false_positives"]
    assert [fp["error_class"] for fp in fps] == ["wrong_unit"]
    assert fps[0]["fp_id"] == "PK01:t3"
    # The unmatched emission is an FP record but never a false_positive_rate.
    assert extraction["false_positive_rate"]["numerator"] == 0
    assert extraction["false_positive_rate"]["denominator"] == 0


# ---------------------------------------------------------------------------
# (b) emission on an absent label


def test_emission_on_absent_label_blocks_only_this_pack() -> None:
    labels = [
        label(
            trial_id="t1",
            polarity="negative",
            label_class="extract_absent",
            expected_value_text=None,
            expected_unit=None,
            expected_period_end=None,
            expected_span_ref=None,
            reason="family not present in this synthetic filing",
        )
    ]
    predictions = [prediction(trial_id="t1", value_text="50")]
    result = run(labels, predictions)
    fpr = result.report["metrics"]["extraction"]["false_positive_rate"]
    assert (fpr["numerator"], fpr["denominator"]) == (1, 1)
    fp = result.report["false_positives"][0]
    assert fp["error_class"] == "invented_extraction"
    assert fp["alternative_explanation"] == "none stated"
    families = result.report["failed_families"]
    assert [f["section_family"] for f in families] == ["debt_outstanding"]
    reasons = families[0]["reason_codes"]
    assert reasons == ["fp_on_negative", "invented_extraction"]
    assert families[0]["blocks"] == ["PK01"]
    assert families[0]["does_not_block"] == [
        f"PK{i:02d}" for i in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    ]
    assert families[0]["relabel_forbidden"] is True
    assert families[0]["reopen_requires"] == (
        "fresh held-out labels under a new Q0 split decision"
    )
    assert families[0]["disposition"] == "unavailable_research_only"
    blocked = run(labels, predictions, blocked_pack_ids=("PK01",))
    assert blocked.report["failed_families"][0]["disposition"] == "blocked_pack"
    assert blocked.report["quality_label"] == "blocked_pack"


# ---------------------------------------------------------------------------
# (c) abstention sub-counts and refusal recall


def test_abstention_exclusions_and_refusal_recall() -> None:
    labels = [
        label(trial_id="t1", target_id="f1"),
        label(trial_id="t2", target_id="f2"),
        label(
            trial_id="t3",
            target_id="f3",
            polarity="negative",
            label_class="extract_absent",
            expected_value_text=None,
            expected_unit=None,
            expected_period_end=None,
            expected_span_ref=None,
        ),
    ]
    predictions = [
        prediction(trial_id="t1", target_id="f1", state="not_evaluable",
                   value_text=None, unit=None, period_end=None, span_ref=None),
        prediction(trial_id="t2", target_id="f2", state="typed_absence",
                   value_text=None, unit=None, period_end=None, span_ref=None),
        prediction(trial_id="t3", target_id="f3", state="typed_absence",
                   value_text=None, unit=None, period_end=None, span_ref=None),
    ]
    result = run(labels, predictions)
    abstention = result.report["metrics"]["extraction"]["abstention"]
    assert (abstention["numerator"], abstention["denominator"]) == (3, 3)
    assert abstention["exclusions"] == [
        "insufficient_evidence:1",
        "not_applicable:2",
    ]
    refusal = result.report["metrics"]["refusal"]
    assert (refusal["recall"]["numerator"], refusal["recall"]["denominator"]) == (1, 1)
    # t2 typed-absented a POSITIVE label, so refusal precision is 1/2.
    assert (refusal["precision"]["numerator"], refusal["precision"]["denominator"]) == (1, 2)
    assert (refusal["abstention"]["numerator"], refusal["abstention"]["denominator"]) == (0, 1)
    positive_cell = next(
        cell
        for cell in result.report["cells"]
        if cell["polarity"] == "positive"
    )
    assert positive_cell["n_excluded"] >= 1
    assert "not_evaluable" in positive_cell["exclusion_reasons"]


# ---------------------------------------------------------------------------
# (d) findings


def test_findings_block_and_detector_leakage() -> None:
    def finding_label(**overrides) -> LabelRecord:
        base = dict(
            target_kind="finding",
            expected_value_text=None,
            expected_unit=None,
            expected_period_end=None,
            expected_span_ref=None,
        )
        base.update(overrides)
        return label(**base)

    labels = [
        finding_label(trial_id="f1", target_id="d1", polarity="positive",
                      label_class="finding_triggered_expected"),
        finding_label(trial_id="f2", target_id="d2", issuer="CAT",
                      polarity="negative",
                      label_class="finding_clear_expected"),
        finding_label(trial_id="f3", target_id="d3", polarity="negative",
                      label_class="finding_not_evaluable_expected"),
        finding_label(trial_id="f4", target_id="d4", issuer="BAC",
                      polarity="negative",
                      label_class="finding_clear_expected"),
        finding_label(trial_id="f5", target_id="d5", issuer="AAPL",
                      polarity="negative",
                      label_class="finding_clear_expected"),
    ]
    predictions = [
        prediction(trial_id="f1", target_kind="finding", target_id="d1",
                   state="TRIGGERED", value_text=None, unit=None,
                   period_end=None, span_ref=None, finding_id="det-1"),
        prediction(trial_id="f2", target_kind="finding", target_id="d2",
                   state="CLEAR", value_text=None, unit=None,
                   period_end=None, span_ref=None),
        prediction(trial_id="f3", target_kind="finding", target_id="d3",
                   state="NOT_EVALUABLE", value_text=None, unit=None,
                   period_end=None, span_ref=None),
        prediction(trial_id="f4", target_kind="finding", target_id="d4",
                   state="TRIGGERED", value_text=None, unit=None,
                   period_end=None, span_ref=None, finding_id="det-2",
                   alternative_explanation="bank interest misread"),
        prediction(trial_id="f5", target_kind="finding", target_id="d5",
                   state="TRIGGERED", value_text=None, unit=None,
                   period_end=None, span_ref=None, finding_id="det-3"),
    ]
    result = run(labels, predictions)
    findings = result.report["metrics"]["findings"]
    assert (findings["precision"]["numerator"], findings["precision"]["denominator"]) == (1, 3)
    assert (findings["recall"]["numerator"], findings["recall"]["denominator"]) == (1, 1)
    assert (findings["abstention"]["numerator"], findings["abstention"]["denominator"]) == (1, 5)
    assert (findings["false_positive_rate"]["numerator"],
            findings["false_positive_rate"]["denominator"]) == (2, 3)
    by_id = {fp["fp_id"]: fp for fp in result.report["false_positives"]}
    assert set(by_id) == {"PK01:f4", "PK01:f5"}
    assert by_id["PK01:f4"]["error_class"] == "detector_leakage"
    assert by_id["PK01:f4"]["predicted"]["finding_id"] == "det-2"
    assert by_id["PK01:f4"]["alternative_explanation"] == "bank interest misread"
    assert by_id["PK01:f5"]["error_class"] == "invented_extraction"
    reasons = {
        f["section_family"]: f["reason_codes"]
        for f in result.report["failed_families"]
    }
    assert "fp_on_negative" in reasons["debt_outstanding"]
    assert "invented_extraction" in reasons["debt_outstanding"]


# ---------------------------------------------------------------------------
# (e) 0/0 findings and the no-bare-float walk


def test_zero_denominators_and_no_bare_floats() -> None:
    labels = [
        label(trial_id="t1", target_id="f1"),
        label(trial_id="t2", target_id="f2"),
    ]
    predictions = [
        prediction(trial_id="t1", target_id="f1"),
        prediction(trial_id="t2", target_id="f2", state="not_evaluable",
                   value_text=None, unit=None, period_end=None, span_ref=None),
    ]
    result = run(labels, predictions)
    for metric in ("precision", "recall", "abstention"):
        frac = result.report["metrics"]["findings"][metric]
        assert (frac["numerator"], frac["denominator"]) == (0, 0)
        assert frac["wilson95"] is None
    wilsons = []

    def collect_wilsons(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "wilson95" and isinstance(value, list):
                    wilsons.append(value)
                else:
                    collect_wilsons(value)
        elif isinstance(node, list):
            for value in node:
                collect_wilsons(value)

    collect_wilsons(result.report)
    assert wilsons and all(
        isinstance(bound, float) for interval in wilsons for bound in interval
    )
    assert bare_floats(result.report) == []


# ---------------------------------------------------------------------------
# (f) Wilson interval vs the textbook formula


def test_wilson_interval_matches_formula() -> None:
    labels = [
        label(trial_id=f"t{i}", target_id=f"f{i}") for i in range(10)
    ]
    predictions = [
        prediction(trial_id=f"t{i}", target_id=f"f{i}",
                   value_text="100" if i < 8 else "999")
        for i in range(10)
    ]
    result = run(labels, predictions)
    precision = result.report["metrics"]["extraction"]["precision"]
    assert (precision["numerator"], precision["denominator"]) == (8, 10)
    z = Decimal("1.96")
    n, d = Decimal(8), Decimal(10)
    z2 = z * z
    p = n / d
    scale = Decimal(1) + z2 / d
    center = (p + z2 / (2 * d)) / scale
    spread = (z / scale) * ((p * (1 - p) / d + z2 / (4 * d * d)).sqrt())
    lower = (center - spread).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    upper = (center + spread).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    assert precision["wilson95"] == [float(lower), float(upper)]


def test_held_out_measured_when_all_power_rows_hold() -> None:
    # PK01's required issuers are CAT and BAC, so the per-issuer positive
    # minimum (Q1-M3) needs >= 2 positives on each of them.
    labels = [
        label(trial_id="p1", target_id="f1"),
        label(trial_id="p2", target_id="f2"),
        label(trial_id="p3", target_id="f3", issuer="BAC"),
        label(trial_id="p4", target_id="f4", issuer="BAC"),
        label(
            trial_id="n1",
            target_id="f5",
            polarity="negative",
            label_class="extract_absent",
            format_class="unseen_amendment",
            expected_value_text=None,
            expected_unit=None,
            expected_period_end=None,
            expected_span_ref=None,
        ),
    ]
    predictions = [
        prediction(trial_id="p1", target_id="f1"),
        prediction(trial_id="p2", target_id="f2"),
        prediction(trial_id="p3", target_id="f3"),
        prediction(trial_id="p4", target_id="f4"),
        prediction(trial_id="n1", target_id="f5", state="typed_absence",
                   value_text=None, unit=None, period_end=None, span_ref=None),
    ]
    result = run(labels, predictions)
    assert result.report["quality_label"] == "held_out_measured"
    assert result.report["failed_families"] == []
    positive_checks = [
        check
        for check in result.power_checks
        if "polarity=positive" in check["rule"]
    ]
    assert {check["issuer"] for check in positive_checks} == {"CAT", "BAC"}
    assert all(check["observed_n"] == 2 for check in positive_checks)
    format_check = next(
        check
        for check in result.power_checks
        if "format_class" in check["rule"]
    )
    assert (format_check["observed_n"], format_check["minimum_n"]) == (1, 1)
    assert format_check["met"] is True
    assert all(check["met"] for check in result.power_checks)
    # per-issuer positive CAT + BAC, negative, format rows apply to PK01
    assert len(result.power_checks) == 4


# ---------------------------------------------------------------------------
# (g) underpowered


def test_underpowered_cell_and_quality_label() -> None:
    labels = [label(trial_id="t1", target_id="f1")]
    predictions = [prediction(trial_id="t1", target_id="f1")]
    result = run(labels, predictions)
    cell = result.report["cells"][0]
    assert cell["n_labeled"] == 1
    assert cell["meets_minimum_n"] is False
    positive_check = next(
        check
        for check in result.power_checks
        if "polarity=positive" in check["rule"] and check["issuer"] == "CAT"
    )
    assert positive_check["minimum_n"] == 2
    assert positive_check["observed_n"] == 1
    assert positive_check["met"] is False
    # BAC is required for PK01 and carries no label: observed 0 (Q1-M3).
    bac_check = next(
        check
        for check in result.power_checks
        if "polarity=positive" in check["rule"] and check["issuer"] == "BAC"
    )
    assert (bac_check["observed_n"], bac_check["minimum_n"]) == (0, 2)
    assert bac_check["met"] is False
    assert result.report["quality_label"] == "underpowered"


# ---------------------------------------------------------------------------
# (h) refusals


def test_golden_aapl_accession_on_later_split_refused() -> None:
    labels = [label(trial_id="t1", accession=GOLDEN_AAPL_QUERY_ACCESSIONS[0])]
    with pytest.raises(PackEvaluationError):
        run(labels, [])


def test_calibration_only_accession_on_later_split_refused() -> None:
    labels = [
        label(trial_id="t1", accession=PROTOCOL["calibration_only_accessions"][0])
    ]
    with pytest.raises(PackEvaluationError):
        run(labels, [])


def test_builders_read_flag_refused() -> None:
    labels = [label(trial_id="t1")]
    with pytest.raises(PackEvaluationError):
        run(labels, [], builders_read_held_out=True)


def test_split_mismatch_refused() -> None:
    labels = [label(trial_id="t1", split="gold")]
    with pytest.raises(PackEvaluationError):
        run(labels, [])


def test_guarded_token_in_fp_display_copy_refused() -> None:
    labels = [
        label(
            trial_id="t1",
            polarity="negative",
            label_class="extract_absent",
            expected_value_text=None,
            expected_unit=None,
            expected_period_end=None,
            expected_span_ref=None,
        )
    ]
    predictions = [
        prediction(
            trial_id="t1",
            value_text="50",
            display_copy=(f"figure {_GUARDED_TOKEN} by the desk",),
        )
    ]
    with pytest.raises(PackEvaluationError):
        run(labels, predictions)
    # The token on a NON-false-positive trial never raises; it is only counted.
    clean_labels = [label(trial_id="t1")]
    counted = run(
        clean_labels,
        [prediction(trial_id="t1", display_copy=(f"{_GUARDED_TOKEN} figures",))],
    )
    gate = counted.report["language_gate"]
    assert gate["guarded_token_count"] == 1
    assert gate["hyphen_guarded_count"] == 0
    hyphenated = run(
        clean_labels,
        [prediction(trial_id="t1", display_copy=(f"{_GUARDED_TOKEN[:7]}-ed figures",))],
    )
    assert hyphenated.report["language_gate"]["hyphen_guarded_count"] == 1


# ---------------------------------------------------------------------------
# (i) A27 language gate


def test_a27_language_gate() -> None:
    assert A27_PATTERNS[1].search("Alphabet") is None
    assert A27_PATTERNS[1].search("Alpha note") is not None
    clean = run(
        [label(trial_id="t1")],
        [prediction(trial_id="t1", display_copy=("Alphabet segment mix",))],
    )
    for family in clean.report["failed_families"]:
        assert "a27_language" not in family["reason_codes"]
    assert clean.report["language_gate"] == {
        "guarded_token_count": 0,
        "hyphen_guarded_count": 0,
    }
    tripped = run(
        [label(trial_id="t1")],
        [prediction(trial_id="t1", display_copy=("possible fraud pattern",))],
    )
    reasons = {
        f["section_family"]: f["reason_codes"]
        for f in tripped.report["failed_families"]
    }
    assert "a27_language" in reasons["debt_outstanding"]


# ---------------------------------------------------------------------------
# (j) precision floor


def test_precision_floor_gap_and_trigger() -> None:
    labels = [label(trial_id=f"t{i}", target_id=f"f{i}") for i in range(10)]
    predictions = [
        prediction(trial_id=f"t{i}", target_id=f"f{i}",
                   value_text="100" if i < 8 else "999")
        for i in range(10)
    ]
    without_floor = run(labels, predictions)
    assert "precision_floor_not_predeclared" in without_floor.gaps
    with_floor = run(labels, predictions, precision_floor=Decimal("0.9"))
    assert "precision_floor_not_predeclared" not in with_floor.gaps
    reasons = {
        f["section_family"]: f["reason_codes"]
        for f in with_floor.report["failed_families"]
    }
    assert reasons["debt_outstanding"] == ["precision_below_floor"]
    assert with_floor.report["metrics"]["extraction"]["precision"]["wilson95"][0] < 0.9


# ---------------------------------------------------------------------------
# (k) gold split


def test_gold_split_is_calibration_only() -> None:
    gold_acc = "0000000000-26-000003"
    labels = [
        label(trial_id=f"t{i}", target_id=f"f{i}", split="gold",
              accession=gold_acc, expected_span_ref=f"{gold_acc}:10-20")
        for i in range(3)
    ]
    predictions = [
        prediction(trial_id=f"t{i}", target_id=f"f{i}",
                   span_ref=f"{gold_acc}:10-20")
        for i in range(3)
    ]
    result = run(labels, predictions, split="gold")
    assert result.report["quality_label"] == "calibration"
    assert result.report["failed_families"] == []
    assert result.report["split_roots"]["gold"] == (
        PROTOCOL["split_roots"]["calibration"] + "/"
    )


# ---------------------------------------------------------------------------
# input validation and unlabeled predictions


def test_input_validation_and_unlabeled_predictions() -> None:
    with pytest.raises(PackEvaluationError):
        run([label(label_class="bogus")], [])
    with pytest.raises(PackEvaluationError):
        run([label(issuer="MSFT")], [])
    with pytest.raises(PackEvaluationError):
        run([label(polarity="neutral")], [])
    with pytest.raises(PackEvaluationError):
        run([label(trial_id="t1"), label(trial_id="t1", target_id="f2")], [])
    with pytest.raises(PackEvaluationError):
        run([label()], [prediction(state="GUESS")])
    with pytest.raises(PackEvaluationError):
        run([label()], [], head_commit="not-a-sha")
    result = run(
        [label(trial_id="t1"), label(trial_id="t2", target_id="f2")],
        [
            prediction(trial_id="t1"),
            prediction(trial_id="t9", target_id="f9"),
        ],
    )
    precision = result.report["metrics"]["extraction"]["precision"]
    assert (precision["numerator"], precision["denominator"]) == (1, 1)
    assert precision["exclusions"] == ["unlabeled:t9"]


def test_match_rules_decimal_and_folded_text() -> None:
    # "100.0" and "1e2" are numerically equal to "100"; "  ONE  hundred "
    # matches "one hundred" after casefold + whitespace collapse.
    result = run(
        [
            label(trial_id="t1"),
            label(trial_id="t2"),
            label(trial_id="t3", expected_value_text="One  hundred"),
        ],
        [
            prediction(trial_id="t1", value_text="100.0"),
            prediction(trial_id="t2", value_text="1e2"),
            prediction(trial_id="t3", value_text="  ONE  hundred "),
        ],
    )
    precision = result.report["metrics"]["extraction"]["precision"]
    assert (precision["numerator"], precision["denominator"]) == (3, 3)
    # A stated expected span that the prediction misses is a fidelity failure
    # even when the value matched.
    fidelity = run(
        [label(trial_id="t1", expected_span_ref=f"{ACC}:99-100")],
        [prediction(trial_id="t1")],
    )
    frac = fidelity.report["metrics"]["extraction"]["source_fidelity_error"]
    assert (frac["numerator"], frac["denominator"]) == (1, 1)
    reasons = {
        f["section_family"]: f["reason_codes"]
        for f in fidelity.report["failed_families"]
    }
    assert "source_fidelity_error" in reasons["debt_outstanding"]


# ---------------------------------------------------------------------------
# fix-lane repairs 2026-10-19 (Q1-M1..M4, Q1-m1..m3, Q1-n1)


def test_source_fidelity_error_denominator_covers_sff_emissions() -> None:
    # 2 source_fidelity_fail emissions over 1 positive emission raised a raw
    # decimal.InvalidOperation on BASE; the denominator is emissions on
    # extract_positive plus emissions on source_fidelity_fail (Q1-M2).
    labels = [
        label(trial_id="p1", target_id="f1"),
        label(trial_id="s1", target_id="f2", label_class="source_fidelity_fail"),
        label(trial_id="s2", target_id="f3", label_class="source_fidelity_fail"),
    ]
    predictions = [
        prediction(trial_id="p1", target_id="f1"),
        prediction(trial_id="s1", target_id="f2", span_ref=f"{ACC}:1-2"),
        prediction(trial_id="s2", target_id="f3", span_ref=f"{ACC}:1-2"),
    ]
    result = run(labels, predictions)
    frac = result.report["metrics"]["extraction"]["source_fidelity_error"]
    assert (frac["numerator"], frac["denominator"]) == (2, 3)
    families = {
        f["section_family"]: f["numerator_denominator"]
        for f in result.report["failed_families"]
    }
    assert families["debt_outstanding"]["source_fidelity_error"] == "2/3"


def test_frac_refuses_numerator_above_denominator() -> None:
    with pytest.raises(PackEvaluationError):
        _frac(2, 1, [])


def test_per_issuer_positive_power_missing_required_issuer() -> None:
    # 5 positives all on CAT; BAC is required for PK01 and carries zero, so
    # the per-issuer minimum is unmet and the pack is underpowered (Q1-M3).
    labels = [
        label(trial_id=f"p{i}", target_id=f"f{i}") for i in range(5)
    ] + [
        label(
            trial_id="n1",
            target_id="f9",
            polarity="negative",
            label_class="extract_absent",
            format_class="unseen_amendment",
            expected_value_text=None,
            expected_unit=None,
            expected_period_end=None,
            expected_span_ref=None,
        ),
    ]
    predictions = [
        prediction(trial_id=f"p{i}", target_id=f"f{i}") for i in range(5)
    ] + [
        prediction(trial_id="n1", target_id="f9", state="typed_absence",
                   value_text=None, unit=None, period_end=None, span_ref=None),
    ]
    result = run(labels, predictions)
    issuer_checks = {
        check["issuer"]: check
        for check in result.power_checks
        if "polarity=positive" in check["rule"]
    }
    assert set(issuer_checks) == {"CAT", "BAC"}
    assert issuer_checks["CAT"]["observed_n"] == 5
    assert issuer_checks["CAT"]["met"] is True
    assert (issuer_checks["BAC"]["observed_n"], issuer_checks["BAC"]["minimum_n"]) == (0, 2)
    assert issuer_checks["BAC"]["met"] is False
    assert result.report["quality_label"] == "underpowered"


def test_pk12_negative_power_per_issuer_all_five() -> None:
    # "PK12 x all five issuers | 1 negative each": negatives on AAPL only
    # leave the other four coverage-contract issuers at 0 (Q1-M3).

    def pk12_label(**overrides) -> LabelRecord:
        base = dict(
            pack_id="PK12",
            issuer="AAPL",
            form_type="10-K",
            section_family="cash_runway_disclosure",
            polarity="negative",
            label_class="extract_absent",
            expected_value_text=None,
            expected_unit=None,
            expected_period_end=None,
            expected_span_ref=None,
        )
        base.update(overrides)
        return label(**base)

    labels = [
        pk12_label(trial_id="n0", target_id="f0", format_class="unseen_amendment"),
        pk12_label(trial_id="n1", target_id="f1"),
        pk12_label(trial_id="n2", target_id="f2"),
    ]
    predictions = [
        prediction(trial_id=f"n{i}", target_id=f"f{i}", state="typed_absence",
                   value_text=None, unit=None, period_end=None, span_ref=None)
        for i in range(3)
    ]
    result = run(labels, predictions, pack_id="PK12")
    issuer_checks = {
        check["issuer"]: check
        for check in result.power_checks
        if "PK12" in check["rule"]
    }
    assert set(issuer_checks) == {"AAPL", "SNOW", "CAT", "BAC", "GOOGL"}
    assert issuer_checks["AAPL"]["observed_n"] == 3
    assert issuer_checks["AAPL"]["met"] is True
    assert issuer_checks["GOOGL"]["observed_n"] == 0
    assert issuer_checks["GOOGL"]["met"] is False
    assert result.report["quality_label"] == "underpowered"


def test_silent_pack_with_declared_floor_cannot_be_held_out_measured() -> None:
    # 5 held-out positives, every prediction a typed absence, floor 0.9: zero
    # emissions means no defined precision lower bound, and an undefined bound
    # cannot clear a declared floor (Q1-M4).
    labels = [
        label(trial_id=f"p{i}", target_id=f"f{i}",
              issuer="CAT" if i < 3 else "BAC")
        for i in range(5)
    ]
    predictions = [
        prediction(trial_id=f"p{i}", target_id=f"f{i}", state="typed_absence",
                   value_text=None, unit=None, period_end=None, span_ref=None)
        for i in range(5)
    ]
    result = run(labels, predictions, precision_floor=Decimal("0.9"))
    assert result.report["quality_label"] != "held_out_measured"
    reasons = {
        f["section_family"]: f["reason_codes"]
        for f in result.report["failed_families"]
    }
    assert "precision_below_floor" in reasons["debt_outstanding"]


def test_prediction_target_mismatch_refused() -> None:
    # The join is keyed by trial_id only on BASE, so a prediction for a
    # different target silently scores against its label's row (Q1-m1).
    with pytest.raises(PackEvaluationError):
        run(
            [label(trial_id="t1", target_id="f1")],
            [prediction(trial_id="t1", target_id="f2")],
        )
    with pytest.raises(PackEvaluationError):
        run(
            [label(trial_id="t1", target_kind="extract", target_id="f1")],
            [
                prediction(
                    trial_id="t1",
                    target_kind="finding",
                    target_id="f1",
                    state="TRIGGERED",
                    value_text=None,
                    unit=None,
                    period_end=None,
                    span_ref=None,
                    finding_id="d1",
                )
            ],
        )


def test_wilson_lower_bound_of_zero_is_positive_zero() -> None:
    # 0/16 quantizes to Decimal('-0.0000') on BASE, whose float() is -0.0
    # (Q1-m2).
    labels = [label(trial_id=f"t{i}", target_id=f"f{i}") for i in range(16)]
    predictions = [
        prediction(trial_id=f"t{i}", target_id=f"f{i}", value_text="999")
        for i in range(16)
    ]
    result = run(labels, predictions)
    lower = result.report["metrics"]["extraction"]["precision"]["wilson95"][0]
    assert lower == 0.0
    assert math.copysign(1, lower) == 1


def test_extract_positive_without_expected_value_refused() -> None:
    # On BASE a None expected value auto-matched every emission (Q1-m3).
    with pytest.raises(PackEvaluationError):
        run([label(trial_id="t1", expected_value_text=None)], [])


def test_non_finite_values_never_match_and_never_raise() -> None:
    # On BASE, Infinity == Infinity matched and an sNaN comparison raised a
    # raw decimal.InvalidOperation (Q1-m3).
    labels = [
        label(trial_id="t1", expected_value_text="Infinity"),
        label(trial_id="t2", expected_value_text="sNaN"),
    ]
    predictions = [
        prediction(trial_id="t1", value_text="Infinity"),
        prediction(trial_id="t2", value_text="sNaN"),
    ]
    result = run(labels, predictions)
    precision = result.report["metrics"]["extraction"]["precision"]
    assert (precision["numerator"], precision["denominator"]) == (0, 2)


def test_precision_floor_must_be_finite_within_unit_interval() -> None:
    labels = [label(trial_id="t1")]
    predictions = [prediction(trial_id="t1")]
    run(labels, predictions, precision_floor=Decimal("0"))
    run(labels, predictions, precision_floor=Decimal("1"))
    for bad in ("1.5", "-0.1", "NaN", "Infinity", "not-a-number"):
        with pytest.raises(PackEvaluationError):
            run(labels, predictions, precision_floor=bad)


def test_evaluated_at_must_be_a_real_timestamp() -> None:
    labels = [label(trial_id="t1")]
    for bad in ("2026-13-19T00:00:00Z", "2026-10-32T00:00:00Z"):
        with pytest.raises(PackEvaluationError):
            run(labels, [], evaluated_at=bad)


# ---------------------------------------------------------------------------
# envelope adaptation


def _field_row(**overrides) -> dict:
    row = {
        "field_id": "probe_field",
        "name": "probe",
        "type": "decimal",
        "unit": "USD",
        "period": {"kind": "instant", "end": "2025-09-27"},
        "value": None,
        "text_value": None,
        "non_value_state": "missing",
        "evidence_kind": "xbrl_fact",
        "required_evidence_kind": "xbrl_fact",
        "source_occurrence_ids": [],
        "source_span": None,
        "table_cell": None,
        "concept": None,
        "taxonomy": None,
        "dimensions": [],
        "mapping_rule_id": None,
        "mapping_rule_digest": None,
        "formula_rule_id": None,
        "dependency_field_ids": [],
        "quality_state": "missing",
        "coverage_state": "unmapped",
        "reason": "missing_standard_fact:us-gaap:Assets",
    }
    row.update(overrides)
    return row


def _pack_result_envelope(fields: list[dict]) -> dict:
    obj = {
        "schema": "specialist_pack_result.v1",
        "pack_id": "PK01",
        "pack_schema_id": "pack.pk01/v1",
        "pack_schema_digest": pack_schema_digest("PK01"),
        "packet_id": "fip_" + "a" * 24,
        "entity": {
            "entity_id": "ISS:US-TEST-SP01",
            "cik": "0000000001",
            "ticker": "SP01",
            "name": "SPECIALIST PACK FIXTURE CORP",
            "identity_basis": "specialist_pack_contract_fixture",
            "source_entity_id": "0000000001",
        },
        "query": {
            "policy": "as_reported",
            "source_event_cutoff": "2025-12-31T23:59:59Z",
            "system_recorded_cutoff": "2026-08-05T12:00:02Z",
            "requested_metrics": ["total_assets"],
            "requested_periods": ["FY2025"],
            "evaluation_mode": "historical_replay",
        },
        "applicability": {
            "state": "applicable",
            "reason": "applicability_rule_satisfied",
            "rule_id": "specialist_pack.fixture_applicable",
            "sic": None,
            "sic_source": None,
        },
        "fields": fields,
        "checks": [],
        "coverage": {
            "valued_fields": 0,
            "missing_fields": 0,
            "unsupported_fields": 0,
            "not_applicable_fields": 0,
            "not_evaluable_fields": 0,
            "disclosure_coverage_state": "not_supplied",
        },
        "limitations": [
            "Synthetic adapter fixture; not an evaluation of any real issuer."
        ],
        "receipts": [],
        "authority": {"class": "context_only", "display_only": True},
    }
    counts = {
        "valued_fields": 0,
        "missing_fields": 0,
        "unsupported_fields": 0,
        "not_applicable_fields": 0,
        "not_evaluable_fields": 0,
    }
    mapping = {
        "valued": "valued_fields",
        "missing": "missing_fields",
        "unsupported": "unsupported_fields",
        "not_evaluable": "not_evaluable_fields",
        "not_applicable": "not_applicable_fields",
    }
    for row in fields:
        counts[mapping[row["quality_state"]]] += 1
    obj["coverage"].update(counts)
    obj["pack_content_sha256"] = pack_content_digest(obj)
    return obj


def test_predictions_from_pack_result_adapts_rows() -> None:
    # Field ids come from the PK01 catalogue: the envelope validator refuses
    # a field the pack does not declare.
    accession = "0000000000-26-000002"
    envelope = _pack_result_envelope(
        [
            _field_row(
                field_id="total_debt",
                quality_state="valued",
                value="125.50",
                text_value=None,
                non_value_state=None,
                source_occurrence_ids=["occ-1"],
                concept="us-gaap:Assets",
                coverage_state="source_trace_complete",
                reason=None,
            ),
            _field_row(
                field_id="covenant_term_observation",
                type="text",
                unit=None,
                quality_state="valued",
                value=None,
                text_value="covenant text here",
                non_value_state=None,
                evidence_kind="text_span",
                required_evidence_kind="text_span",
                source_span={
                    "accession": None,
                    "document_id": "doc-1",
                    "start_offset": 5,
                    "end_offset": 22,
                },
                coverage_state="source_trace_complete",
                reason=None,
            ),
            _field_row(field_id="short_term_debt", quality_state="missing",
                       non_value_state="missing"),
            _field_row(field_id="long_term_debt",
                       quality_state="not_evaluable",
                       non_value_state="not_evaluable"),
            _field_row(field_id="debt_fair_value",
                       quality_state="unsupported",
                       non_value_state="unsupported"),
            _field_row(field_id="current_assets", quality_state="missing",
                       non_value_state="missing"),
        ]
    )
    records, unmapped = predictions_from_pack_result(
        envelope,
        accession=accession,
        trial_ids={
            "total_debt": "t-val",
            "covenant_term_observation": "t-text",
            "short_term_debt": "t-missing",
            "long_term_debt": "t-noteval",
            "debt_fair_value": "t-unsup",
        },
    )
    assert unmapped == ("current_assets",)
    by_trial = {record.trial_id: record for record in records}
    assert set(by_trial) == {"t-val", "t-text", "t-missing", "t-noteval", "t-unsup"}
    assert by_trial["t-val"].state == "emitted"
    assert by_trial["t-val"].value_text == "125.5"
    assert by_trial["t-val"].unit == "USD"
    assert by_trial["t-val"].period_end == "2025-09-27"
    assert by_trial["t-val"].span_ref is None
    assert by_trial["t-text"].state == "emitted"
    assert by_trial["t-text"].value_text == "covenant text here"
    assert by_trial["t-text"].span_ref == f"{accession}:5-22"
    assert by_trial["t-missing"].state == "typed_absence"
    assert by_trial["t-missing"].exclusion_reason is None
    # Q1-M1: only missing / not_applicable are an honest typed refusal;
    # unsupported and not_evaluable abstain as not_evaluable and keep their
    # original non_value_state as the exclusion reason.
    assert by_trial["t-noteval"].state == "not_evaluable"
    assert by_trial["t-noteval"].exclusion_reason == "not_evaluable"
    assert by_trial["t-unsup"].state == "not_evaluable"
    assert by_trial["t-unsup"].exclusion_reason == "unsupported"
    assert all(record.target_kind == "extract" for record in records)
    broken = _pack_result_envelope(
        [_field_row(field_id="total_debt", quality_state="valued", value="9.9",
                    text_value=None, non_value_state=None,
                    source_occurrence_ids=["occ-1"], concept="us-gaap:Assets",
                    coverage_state="source_trace_complete", reason=None)]
    )
    broken["fields"][0]["value"] = "1.1"  # digest no longer matches
    with pytest.raises(PackEvaluationError):
        predictions_from_pack_result(
            broken, accession=accession, trial_ids={"total_debt": "t-val"}
        )


# ---------------------------------------------------------------------------
# (l) determinism and the CLI round trip


def test_determinism() -> None:
    labels = [label(trial_id=f"t{i}", target_id=f"f{i}") for i in range(3)]
    predictions = [
        prediction(trial_id=f"t{i}", target_id=f"f{i}",
                   value_text="100" if i < 2 else "77")
        for i in range(3)
    ]
    first = run(labels, predictions)
    second = run(labels, predictions)
    assert json.dumps(first.report, sort_keys=True) == json.dumps(
        second.report, sort_keys=True
    )


def test_cli_help_and_round_trip(tmp_path) -> None:
    help_run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "fif_pack_quality_report.py"),
         "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert help_run.returncode == 0
    assert "fif_pack_quality_report" in help_run.stdout
    labels = [
        label(trial_id="t1", target_id="f1"),
        label(trial_id="t2", target_id="f2"),
        label(trial_id="t3", target_id="f3"),
    ]
    predictions = [
        prediction(trial_id="t1", target_id="f1"),
        prediction(trial_id="t2", target_id="f2"),
        prediction(trial_id="t3", target_id="f3", unit="EUR",
                   display_copy=["senior notes outstanding"]),
    ]
    labels_path = tmp_path / "labels.json"
    predictions_path = tmp_path / "predictions.json"
    labels_path.write_text(
        json.dumps([vars(record) for record in labels]), encoding="utf-8"
    )
    predictions_path.write_text(
        json.dumps([vars(record) for record in predictions]), encoding="utf-8"
    )
    out_path = tmp_path / "report.json"
    cli_run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_pack_quality_report.py"),
            "--protocol-root",
            str(ROOT),
            "--pack",
            "PK01",
            "--split",
            "held_out",
            "--labels",
            str(labels_path),
            "--predictions",
            str(predictions_path),
            "--head-commit",
            HEAD,
            "--evaluated-at",
            TS,
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert cli_run.returncode == 0, cli_run.stderr
    assert "GAP: precision_floor_not_predeclared" in cli_run.stdout
    written = json.loads(out_path.read_text(encoding="utf-8"))
    REPORT_VALIDATOR.validate(written)
    engine_result = run(labels, predictions)
    assert written == engine_result.report
    power = json.loads(
        (tmp_path / "report.json.power.json").read_text(encoding="utf-8")
    )
    assert isinstance(power, list) and power == list(engine_result.power_checks)
    refused_run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fif_pack_quality_report.py"),
            "--protocol-root",
            str(ROOT),
            "--pack",
            "PK01",
            "--split",
            "gold",
            "--labels",
            str(labels_path),
            "--predictions",
            str(predictions_path),
            "--head-commit",
            HEAD,
            "--evaluated-at",
            TS,
            "--out",
            str(tmp_path / "never.json"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert refused_run.returncode == 1
    assert "refused" in refused_run.stderr
    assert not (tmp_path / "never.json").exists()
