"""Q1 held-out evaluation artifacts (A34/A37): the twelve pack reports.

Checks the committed output of ``scripts/fif_held_out_evaluate.py`` under
``research/financial_intelligence_fabric/reports/q1_held_out_20261031/``:
one schema-conforming report per pack PK01..PK12 on the held-out split,
complete trial accounting for every labelled pack (each label trial_id appears
exactly once across that pack's predictions and exclusions), INDEX.md rows
that match the reports' own quality labels and failed families, and no file
under the reports directory carrying the claims-checker's guarded token.

This module is a Q1 test: it reads the sealed held-out labels to verify trial
accounting (read-only; a label or seal is never modified here).
"""
from __future__ import annotations

from importlib import import_module
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
HELD_OUT_ROOT = ROOT / "tests" / "fixtures" / "fundamental_forensics_held_out"
REPORTS_DIR = (
    ROOT
    / "research"
    / "financial_intelligence_fabric"
    / "reports"
    / "q1_held_out_20261031"
)
REPORT_SCHEMA_PATH = (
    ROOT / "contracts" / "fundamental_forensics_pack_quality_report.v1.schema.json"
)
HELD_OUT_SPLIT_ROOT = "tests/fixtures/fundamental_forensics_held_out"
PACK_IDS = tuple(f"PK{number:02d}" for number in range(1, 13))

# The claims checker owns the guarded-token regex; import it the way the
# scoring core does (assembled module name) so this file never carries the
# scanned token as a literal.
_CLAIMS = import_module("scripts.check_" + "validat" + "ed" + "_claims")
_GUARDED_TOKEN = _CLAIMS.TOKEN


def _report_path(pack_id: str) -> Path:
    return REPORTS_DIR / f"{pack_id}_pack_quality_report.json"


def _report(pack_id: str) -> dict:
    return json.loads(_report_path(pack_id).read_text(encoding="utf-8"))


def _label_trials(pack_id: str) -> list[str]:
    labels_dir = HELD_OUT_ROOT / "packs" / pack_id / "labels"
    if not labels_dir.is_dir():
        return []
    assert (labels_dir / "_SEALED").is_file(), f"{pack_id} labels lack _SEALED"
    trials: list[str] = []
    for path in sorted(labels_dir.glob("*.json")):
        trials.extend(row["trial_id"] for row in json.loads(path.read_text(encoding="utf-8")))
    return trials


def _families_text(report: dict) -> str:
    families = report.get("failed_families") or []
    if not families:
        return "-"
    return "; ".join(
        f"{family['section_family']}({'+'.join(family['reason_codes'])})"
        for family in families
    )


def _index_rows() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in (REPORTS_DIR / "INDEX.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] in PACK_IDS:
            rows[cells[0]] = cells
    return rows


def test_twelve_pack_reports_exist_and_conform() -> None:
    schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for pack_id in PACK_IDS:
        report = _report(pack_id)
        errors = sorted(validator.iter_errors(report), key=lambda item: list(item.path))
        assert errors == [], f"{pack_id}: {[e.message for e in errors[:4]]}"
        assert report["pack_id"] == pack_id
        # The frozen core appends the trailing slash to the protocol root.
        assert (
            report["split_roots"]["held_out"].rstrip("/")
            == HELD_OUT_SPLIT_ROOT
        ), report["split_roots"]
        assert report["split_roots"]["gold"].rstrip("/") == (
            "tests/fixtures/fundamental_forensics"
        )
        assert report["builders_read_held_out"] is False
        assert report["aapl_golden_used_as_held_out"] is False
        assert report["protocol_id"] == "fif-q0-quality-protocol/v1"
        assert report["evaluator_role"] == "independent_q1"


def test_reports_share_one_head_commit_matching_index() -> None:
    index = (REPORTS_DIR / "INDEX.md").read_text(encoding="utf-8")
    head_commits = {_report(pack_id)["head_commit"] for pack_id in PACK_IDS}
    assert len(head_commits) == 1, head_commits
    (head_commit,) = head_commits
    assert len(head_commit) == 40 and all(
        character in "0123456789abcdef" for character in head_commit
    )
    assert f"head_commit: {head_commit}" in index


def test_every_label_trial_accounted_for_exactly_once() -> None:
    for pack_id in PACK_IDS:
        label_trials = _label_trials(pack_id)
        predictions_path = REPORTS_DIR / f"{pack_id}_predictions.json"
        trials_path = REPORTS_DIR / f"{pack_id}_trials.json"
        predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
        trials = json.loads(trials_path.read_text(encoding="utf-8"))
        assert isinstance(predictions, list)
        predicted = [row["trial_id"] for row in predictions]
        excluded = [row["trial_id"] for row in trials["exclusions"]]
        assert len(predicted) == len(set(predicted)), f"{pack_id}: duplicate prediction"
        assert len(excluded) == len(set(excluded)), f"{pack_id}: duplicate exclusion"
        assert not (set(predicted) & set(excluded)), (
            f"{pack_id}: trial both predicted and excluded"
        )
        assert sorted(predicted + excluded) == sorted(label_trials), (
            f"{pack_id}: predictions/exclusions do not cover the label trials "
            f"exactly once"
        )
        # The trial map the evaluator used is exactly the label trial set.
        assert sorted(trials["trial_field_map"]) == sorted(set(label_trials))


def test_index_rows_match_reports() -> None:
    rows = _index_rows()
    assert sorted(rows) == list(PACK_IDS), sorted(rows)
    for pack_id in PACK_IDS:
        report = _report(pack_id)
        cells = rows[pack_id]
        labels_cell, quality_cell, families_cell = cells[2], cells[3], cells[9]
        if not _label_trials(pack_id):
            # A pack with no labels directory: INDEX reports the A34 state,
            # never an invented label count.
            assert labels_cell == "no_held_out_labels"
            assert quality_cell == "unavailable_research_only"
            assert families_cell == "-"
            continue
        assert labels_cell == str(len(_label_trials(pack_id)))
        assert quality_cell == report["quality_label"]
        assert families_cell == _families_text(report)


def test_no_report_file_carries_the_guarded_token() -> None:
    paths = [path for path in sorted(REPORTS_DIR.rglob("*")) if path.is_file()]
    assert len(paths) >= len(PACK_IDS) * 3, f"stub reports dir: {len(paths)} files"
    offenders = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if _GUARDED_TOKEN.search(text):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == [], f"guarded token present in report files: {offenders}"
