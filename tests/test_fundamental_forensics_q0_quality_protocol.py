"""Pin the FIF Q0 quality protocol manifest and pack quality report schema.

Reads the protocol document, machine manifest, and report schema. Never opens
a path under tests/fixtures/fundamental_forensics_held_out.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from pathlib import PurePosixPath

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_JSON = ROOT / "research" / "financial_intelligence_fabric" / "FIF_Q0_QUALITY_PROTOCOL.json"
PROTOCOL_MD = ROOT / "research" / "financial_intelligence_fabric" / "FIF_Q0_QUALITY_PROTOCOL.md"
SCHEMA_PATH = ROOT / "contracts" / "fundamental_forensics_pack_quality_report.v1.schema.json"
LEDGER_PATH = ROOT / "engine" / "fundamental_forensics" / "ixbrl_raw_ledger.py"

FROZEN_TOP_LEVEL_KEYS = [
    "schema",
    "protocol_id",
    "frozen_at_commit",
    "split_roots",
    "calibration_only_accessions",
    "issuers",
    "packs",
    "kernel_family",
    "minimum_n",
    "label_classes",
    "quality_labels",
    "metrics",
    "failed_family_disposition",
    "operator_rules",
    "report_schema",
]
ISSUERS = ["AAPL", "SNOW", "CAT", "BAC", "GOOGL"]
PACK_IDS = [f"PK{i:02d}" for i in range(1, 13)]
APPLICABILITY_ENUM = {"required", "optional", "negative"}
LABEL_CLASSES = [
    "extract_positive",
    "extract_absent",
    "extract_present_out_of_scope",
    "finding_triggered_expected",
    "finding_clear_expected",
    "finding_not_evaluable_expected",
    "source_fidelity_fail",
    "relevance_review",
]
QUALITY_LABELS = [
    "calibration",
    "display_tier",
    "held_out_measured",
    "accepted",
    "unavailable_research_only",
    "blocked_pack",
    "typed_absence",
    "underpowered",
]
METRIC_NAMES = [
    "precision",
    "recall",
    "abstention",
    "source_fidelity_error",
    "false_positive_rate",
]
_GUARDED_TOKEN = "validat" + "ed"
_SCRIPT_FILENAME = "check_" + _GUARDED_TOKEN + "_claims.py"
NUMERATOR_DENOMINATOR_NOTE = (
    "Every rate is numerator/denominator with exclusions listed; "
    "truthful refusal is excluded from positive coverage."
)


def _load_protocol() -> dict:
    return json.loads(PROTOCOL_JSON.read_text(encoding="utf-8"))


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _ast_assign(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name and node.value is not None:
                return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {path}")


def _zero_frac() -> dict:
    return {"numerator": 0, "denominator": 0, "exclusions": []}


def _rate_block() -> dict:
    return {
        "precision": _zero_frac(),
        "recall": _zero_frac(),
        "abstention": _zero_frac(),
    }


def _minimal_pk01_report() -> dict:
    return {
        "schema": "fundamental_forensics.pack_quality_report/v1",
        "pack_id": "PK01",
        "pack_name": "Debt, liquidity, covenants and maturities",
        "protocol_id": "fif-q0-quality-protocol/v1",
        "head_commit": "5267c66846e7733bc1eb30edc1524daff51598ca",
        "evaluated_at": "2026-10-12T00:00:00Z",
        "evaluator_role": "independent_q1",
        "quality_label": "display_tier",
        "split_roots": {
            "gold": "tests/fixtures/fundamental_forensics/",
            "held_out": "tests/fixtures/fundamental_forensics_held_out/",
        },
        "builders_read_held_out": False,
        "aapl_golden_used_as_held_out": False,
        "language_gate": {
            "guarded_token_count": 0,
            "hyphen_guarded_count": 0,
        },
        "cells": [],
        "metrics": {
            "extraction": _rate_block(),
            "findings": _rate_block(),
            "refusal": _rate_block(),
        },
        "false_positives": [],
        "failed_families": [],
        "numerator_denominator_note": NUMERATOR_DENOMINATOR_NOTE,
    }


def _object_schema_paths(node, path="$"):
    if isinstance(node, dict):
        types = node.get("type")
        type_is_object = types == "object" or (
            isinstance(types, list) and "object" in types
        )
        if type_is_object or "properties" in node:
            yield path, node
        for key, child in node.items():
            yield from _object_schema_paths(child, f"{path}.{key}")
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from _object_schema_paths(child, f"{path}[{index}]")


def test_manifest_parses_with_exactly_the_frozen_top_level_keys() -> None:
    protocol = _load_protocol()
    assert list(protocol.keys()) == FROZEN_TOP_LEVEL_KEYS
    assert protocol["schema"] == "fundamental_forensics.quality_protocol/v1"
    assert protocol["protocol_id"] == "fif-q0-quality-protocol/v1"
    assert protocol["frozen_at_commit"] == "5267c66846e7733bc1eb30edc1524daff51598ca"
    assert protocol["report_schema"] == (
        "contracts/fundamental_forensics_pack_quality_report.v1.schema.json"
    )
    assert protocol["issuers"] == ISSUERS
    assert protocol["kernel_family"] == {
        "family_id": "kernel_detectors_v1",
        "detector_pack": "fundamental-forensics-five/v1",
        "mandatory_negative_issuers": ["BAC"],
    }


def test_calibration_only_accessions_match_golden_query_accessions() -> None:
    protocol = _load_protocol()
    golden = _ast_assign(LEDGER_PATH, "GOLDEN_AAPL_QUERY_ACCESSIONS")
    assert tuple(protocol["calibration_only_accessions"]) == tuple(golden)
    assert list(protocol["calibration_only_accessions"]) == [
        "0000320193-25-000079",
        "0000320193-26-000020",
    ]


def test_split_roots_disjoint_and_held_out_not_nested_under_calibration() -> None:
    protocol = _load_protocol()
    roots = protocol["split_roots"]
    assert set(roots) == {"calibration", "held_out"}
    cal = PurePosixPath(roots["calibration"])
    held = PurePosixPath(roots["held_out"])
    assert cal.as_posix() == "tests/fixtures/fundamental_forensics"
    assert held.as_posix() == "tests/fixtures/fundamental_forensics_held_out"
    assert cal != held
    assert cal not in held.parents


def test_twelve_packs_pk01_pk12_each_issuer_applicability_enum() -> None:
    packs = _load_protocol()["packs"]
    assert [p["pack_id"] for p in packs] == PACK_IDS
    for pack in packs:
        assert set(pack["applicability"]) == set(ISSUERS)
        for issuer in ISSUERS:
            assert pack["applicability"][issuer] in APPLICABILITY_ENUM
        assert pack["name"]
        assert pack["section_family_ids"]
        assert pack["forms"]
        conditions = pack.get("applicability_conditions", {})
        assert set(conditions).issubset(set(ISSUERS))
        for value in conditions.values():
            assert isinstance(value, str) and value


def test_pk10_forms_are_def_14a_only() -> None:
    pk10 = next(p for p in _load_protocol()["packs"] if p["pack_id"] == "PK10")
    assert pk10["forms"] == ["DEF 14A"]
    assert all(pk10["applicability"][issuer] == "required" for issuer in ISSUERS)


def test_pk11_and_pk12_applicability_frozen() -> None:
    by_id = {p["pack_id"]: p for p in _load_protocol()["packs"]}
    pk11 = by_id["PK11"]
    assert pk11["applicability"]["BAC"] == "required"
    for issuer in ("AAPL", "SNOW", "CAT", "GOOGL"):
        assert pk11["applicability"][issuer] == "negative"
    pk12 = by_id["PK12"]
    assert all(pk12["applicability"][issuer] == "negative" for issuer in ISSUERS)
    pk04 = by_id["PK04"]
    assert pk04["applicability"]["BAC"] == "negative"
    assert pk04["applicability_conditions"]["BAC"] == "bank interest vs contract"
    pk07 = by_id["PK07"]
    assert pk07["applicability"]["AAPL"] == "negative"
    assert pk07["applicability_conditions"]["AAPL"] == "negative unless a deal year"


def test_minimum_n_rows_equal_section_3_2_by_value() -> None:
    rows = _load_protocol()["minimum_n"]
    assert len(rows) == 7
    for row in rows:
        assert set(row) >= {"split", "cell", "minimum_n", "if_below"}

    def n_for(split: str, *needles: str) -> int:
        matched = [
            row
            for row in rows
            if row["split"] == split and all(needle in row["cell"] for needle in needles)
        ]
        assert len(matched) == 1, (split, needles, matched)
        return matched[0]["minimum_n"]

    gold_positive = next(
        row
        for row in rows
        if row["split"] == "gold" and "positive" in row["cell"]
    )
    assert gold_positive["minimum_n"] == 3
    assert "2 issuers" in gold_positive["cell"]
    assert n_for("gold", "negative") == 2
    assert n_for("held_out", "positive") == 2
    assert n_for("held_out", "polarity=negative") == 1
    assert n_for("held_out", "format_class") == 1
    assert n_for("held_out", "PK11") == 1
    assert n_for("held_out", "PK12") == 1


def test_exactly_eight_label_classes_and_eight_quality_labels() -> None:
    protocol = _load_protocol()
    classes = [row["label_class"] for row in protocol["label_classes"]]
    labels = [row["label"] for row in protocol["quality_labels"]]
    assert classes == LABEL_CLASSES
    assert labels == QUALITY_LABELS
    for row in protocol["label_classes"]:
        assert row["counted_in"]
    for row in protocol["quality_labels"]:
        assert row["may_appear_on"]
        assert row["forbidden_uses"]


def test_failed_family_disposition_scope_is_pack_only() -> None:
    disp = _load_protocol()["failed_family_disposition"]
    assert disp["scope"] == "pack_only"
    assert "unavailable_research_only" in disp["states"]
    assert "blocked_pack" in disp["states"]


def test_every_metric_names_numerator_denominator_exclusions_field() -> None:
    metrics = _load_protocol()["metrics"]
    assert [row["metric"] for row in metrics] == METRIC_NAMES
    for row in metrics:
        assert row["numerator"]
        assert row["denominator"]
        assert row["exclusions_field"] == "exclusions"


def test_report_schema_draft202012_additional_properties_false_on_every_object() -> None:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == (
        "https://mastermind-x.com/contracts/"
        "fundamental_forensics_pack_quality_report.v1.schema.json"
    )
    assert schema["properties"]["pack_id"]["enum"] == PACK_IDS
    assert schema["properties"]["quality_label"]["enum"] == QUALITY_LABELS
    assert schema["properties"]["aapl_golden_used_as_held_out"]["const"] is False
    assert schema["properties"]["builders_read_held_out"]["const"] is False
    missing = []
    for path, node in _object_schema_paths(schema):
        if node.get("additionalProperties") is not False:
            missing.append(path)
    assert missing == [], f"object schemas missing additionalProperties false: {missing}"


def test_minimal_pk01_report_passes_schema() -> None:
    schema = _load_schema()
    Draft202012Validator(schema).validate(_minimal_pk01_report())


def test_pack_id_pk13_is_rejected() -> None:
    schema = _load_schema()
    report = _minimal_pk01_report()
    report["pack_id"] = "PK13"
    try:
        Draft202012Validator(schema).validate(report)
    except ValidationError:
        return
    raise AssertionError("PK13 must be rejected")


def test_report_missing_split_roots_is_rejected() -> None:
    schema = _load_schema()
    report = _minimal_pk01_report()
    del report["split_roots"]
    try:
        Draft202012Validator(schema).validate(report)
    except ValidationError as exc:
        assert "split_roots" in str(exc)
        return
    raise AssertionError("missing split_roots must be rejected")


def test_aapl_golden_used_as_held_out_true_is_rejected() -> None:
    schema = _load_schema()
    report = _minimal_pk01_report()
    report["aapl_golden_used_as_held_out"] = True
    try:
        Draft202012Validator(schema).validate(report)
    except ValidationError:
        return
    raise AssertionError("aapl_golden_used_as_held_out true must be rejected")


def test_bare_float_rate_is_rejected() -> None:
    schema = _load_schema()
    report = _minimal_pk01_report()
    report["metrics"]["extraction"]["precision"] = 0.91
    try:
        Draft202012Validator(schema).validate(report)
    except ValidationError:
        return
    raise AssertionError("bare float rate must be rejected")


def test_protocol_doc_manifest_and_schema_omit_guarded_token() -> None:
    for path in (PROTOCOL_MD, PROTOCOL_JSON, SCHEMA_PATH):
        text = path.read_text(encoding="utf-8")
        stripped = text.replace(_SCRIPT_FILENAME, "")
        assert _GUARDED_TOKEN not in stripped, path
        assert "已验证" not in text
        assert "经验证" not in text


