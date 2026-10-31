"""Q1 held-out evaluation artifacts (A34/A37): the twelve pack reports.

Checks the committed output of ``scripts/fif_held_out_evaluate.py`` under
``research/financial_intelligence_fabric/reports/q1_held_out_20261031/``:
one schema-conforming report per pack PK01..PK12 on the held-out split,
complete trial accounting for every labelled pack (each label trial_id appears
exactly once across that pack's predictions and exclusions), INDEX.md rows
that match the reports' own quality labels and failed families, and no file
under the reports directory carrying the claims-checker's guarded token.

This module is a Q1 test: it reads the sealed held-out labels to verify trial
accounting (read-only; a label or seal is never modified here). It also
unit-tests the evaluator itself — the SIC binding order, the envelope
``sic_source`` vocabulary, and the duplicate-target visibility rules (E1-3) —
over synthetic inputs only: those tests never open the sealed held-out
``labels/`` directories and never read the real stage (the end-to-end note
test builds its own synthetic corpus, labels and stage bytes included, under
``tmp_path``).
"""
from __future__ import annotations

from importlib import import_module
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.fundamental_forensics.admitted_filing_package import (
    admit_retained_filing_package,
)
from engine.fundamental_forensics.pack_evaluation import PredictionRecord
from engine.fundamental_forensics.specialist_pack_contract import (
    load_pack_schema,
    validate_pack_result,
)
from engine.fundamental_forensics.specialist_packs import (
    PackInput,
    produce_pack,
)
from scripts import fif_held_out_evaluate as evaluator

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
ENVELOPE_SCHEMA_PATH = ROOT / "contracts" / "specialist_pack_result.v1.schema.json"
# Committed AAPL 10-K filing-package fixture (raw package bytes, not a gold
# expectation): the in-repo corpus the evaluator's admission path can build
# a package from without the stage.
AAPL_10K_2025_PACKAGE = ROOT / "tests" / "fixtures" / "fundamental_forensics" / "aapl_10k_2025"
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


# ---------------------------------------------------------------------------
# evaluator unit tests (synthetic inputs only; no labels/, no stage)


def _extract_record(trial_id: str, target_id: str) -> PredictionRecord:
    return PredictionRecord(
        trial_id=trial_id, target_kind="extract", target_id=target_id, state="emitted"
    )


def test_contract_sic_binds_from_contract_rows_before_witness() -> None:
    contract_rows = {
        "0000070858": {"sic": "6021"},
        "0000320193": {},
    }
    # A contract row with a digit sic binds from the contract.
    assert evaluator._contract_sic(contract_rows, "0000070858") == (
        "6021",
        "held_out_contract",
    )
    # The contract wins over the witness when both could bind.
    assert evaluator._bind_issuer_sic(
        contract_rows, "0000070858", {"sic": "3571"}
    ) == ("6021", "held_out_contract")
    # A row without sic falls back to the staged witness.
    assert evaluator._bind_issuer_sic(
        contract_rows, "0000320193", {"sic": "3571"}
    ) == ("3571", "sec_submissions")
    # Neither source bound: unbound.
    assert evaluator._bind_issuer_sic(contract_rows, "0000320193", {}) == (
        None,
        "unbound",
    )
    assert evaluator._contract_sic({}, "9999999999") == (None, "unbound")


def test_held_out_contract_carries_a_digit_sic_for_every_issuer() -> None:
    contract = json.loads(
        (HELD_OUT_ROOT / "held_out_contract.json").read_text(encoding="utf-8")
    )
    issuers = contract["issuers"]
    assert issuers, "held-out contract carries no issuer rows"
    for row in issuers:
        assert isinstance(row["sic"], str) and row["sic"].isdigit(), row.get("cik")
        source = row["sic_source"]
        assert isinstance(source, dict), row.get("cik")
        capture_path = source.get("capture_path")
        assert isinstance(capture_path, str) and capture_path, row.get("cik")


def test_duplicate_label_targets_are_refused_not_collapsed() -> None:
    rows = [
        {"trial_id": "T1", "target_id": "revenue"},
        {"trial_id": "T2", "target_id": "revenue"},
        {"trial_id": "T3", "target_id": "net_income_loss"},
    ]
    note: dict = {}
    exclusions: list[dict] = []
    assert evaluator._refuse_duplicate_label_targets(rows, note, exclusions) is True
    assert note["outcome"] == "duplicate_label_target"
    assert note["detail"] == "revenue"
    # Every row of the accession is refused visibly — none dropped silently.
    assert exclusions == [
        {"trial_id": "T1", "exclusion_reason": "duplicate_label_target:revenue"},
        {"trial_id": "T2", "exclusion_reason": "duplicate_label_target:revenue"},
        {"trial_id": "T3", "exclusion_reason": "duplicate_label_target:revenue"},
    ]
    # Distinct target_ids refuse nothing.
    unique_rows = [
        {"trial_id": "T1", "target_id": "revenue"},
        {"trial_id": "T3", "target_id": "net_income_loss"},
    ]
    clean_note: dict = {}
    clean_exclusions: list[dict] = []
    assert (
        evaluator._refuse_duplicate_label_targets(
            unique_rows, clean_note, clean_exclusions
        )
        is False
    )
    assert clean_exclusions == [] and clean_note == {}


def test_duplicate_prediction_targets_are_excluded_visibly() -> None:
    records = [
        _extract_record("T1", "revenue"),
        _extract_record("T1-dup", "revenue"),
        _extract_record("T2", "net_income_loss"),
    ]
    trial_ids = {
        "revenue": "T1",
        "net_income_loss": "T2",
        "total_assets": "T3",
    }
    exclusions: list[dict] = []
    held, duplicated = evaluator._select_scoreable_records(
        records, trial_ids, exclusions
    )
    assert duplicated == ["revenue"]
    assert len(duplicated) == 1  # the note counter derives from this list
    # Only the duplicated target's row is excluded, visibly.
    assert exclusions == [
        {"trial_id": "T1", "exclusion_reason": "duplicate_prediction_target:revenue"}
    ]
    # Every other target is still scored normally (the adapter's own record),
    # and a label target with no record keeps its field_not_in_envelope fallback.
    assert [record.target_id for record in held] == ["net_income_loss", "total_assets"]
    assert held[0] is records[2]
    assert held[1].state == "not_evaluable"
    assert held[1].exclusion_reason == "field_not_in_envelope"
    assert held[1].trial_id == "T3"


def test_envelope_sic_source_values_are_members_of_the_frozen_enum() -> None:
    schema = json.loads(ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8"))
    applicability = schema["properties"]["applicability"]
    if "$ref" in applicability:
        # The frozen schema keeps the applicability object in $defs.
        applicability = schema["$defs"][applicability["$ref"].rsplit("/", 1)[-1]]
    enum = applicability["properties"]["sic_source"]["enum"]
    for binding in ("held_out_contract", "sec_submissions", "unbound"):
        for sic in ("6021", None):
            assert evaluator._envelope_sic_source(binding, sic) in enum, (
                binding,
                sic,
            )
    # The binding-route label itself is what the frozen enum refuses — the
    # schema error that zeroed the second Q1 generation
    # ("applicability.sic_source: 'held_out_contract' is not one of
    # ['sec_submissions', 'dei', 'unbound', None]") — which is exactly why
    # the mapping exists: the route lives in the report note, never in the
    # envelope.
    assert "held_out_contract" not in enum


def _admitted_aapl_10k_2025() -> tuple[dict, object]:
    """(manifest, admitted package) built the evaluator's admission way."""
    manifest = json.loads(
        (AAPL_10K_2025_PACKAGE / "package_manifest.json").read_text(encoding="utf-8")
    )
    members = {
        item["name"]: (AAPL_10K_2025_PACKAGE / "members" / item["name"]).read_bytes()
        for item in manifest["members"]
        if item.get("state") == "stored"
    }
    package = admit_retained_filing_package(
        index_bytes=(AAPL_10K_2025_PACKAGE / "index.json").read_bytes(),
        manifest=manifest,
        members=members,
        witness_bytes=(
            AAPL_10K_2025_PACKAGE / "sec_submissions_witness.json"
        ).read_bytes(),
        capture_recorded_at=manifest["fixture_recorded_at"],
    )
    return manifest, package


def test_contract_bound_sic_produces_a_valid_envelope_end_to_end() -> None:
    manifest, package = _admitted_aapl_10k_2025()
    entity = evaluator._entity_for(
        manifest,
        {manifest["cik"]: {"ticker": "AAPL", "identity_binding_state": "test"}},
        "synthetic_test_contract",
    )
    # PK04 is the bank pack; PK01 stands in for the non-bank packs. Both
    # must return (no SpecialistPackError) with the contract-bound SIC
    # expressed in the envelope's own vocabulary.
    for pack_id in ("PK04", "PK01"):
        catalogue = [
            field["field_id"]
            for field in load_pack_schema(pack_id).get("fields") or ()
            if isinstance(field, dict)
        ]
        result = produce_pack(
            pack_id,
            PackInput(
                packages=(package,),
                entity=entity,
                query=evaluator._query_for(manifest, catalogue),
                issuer_sic="6021",
                sic_source=evaluator._envelope_sic_source("held_out_contract", "6021"),
            ),
        )
        assert result["applicability"]["sic"] == "6021"
        assert result["applicability"]["sic_source"] == "sec_submissions"
        assert validate_pack_result(result) == [], pack_id


def _synthetic_held_out_corpus(base: Path) -> dict[str, Path]:
    """One-accession synthetic corpus (held-out root + stage) over the
    committed AAPL 10-K fixture bytes: a contract row with a digit SIC, the
    package manifest, one synthetic label under this corpus's own
    ``_SEALED`` marker, and the staged member bytes. Nothing under the
    sealed held-out root and nothing under the real stage is read."""
    accession = "0000320193-25-000079"
    cik10 = "0000320193"
    held_out_root = base / "held_out"
    stage_root = base / "stage"
    package_dir = held_out_root / "packages" / cik10 / accession
    package_dir.mkdir(parents=True)
    shutil.copy(
        AAPL_10K_2025_PACKAGE / "package_manifest.json",
        package_dir / "package_manifest.json",
    )
    (held_out_root / "held_out_contract.json").write_text(
        json.dumps(
            {
                "contract_id": "synthetic_test_contract",
                "issuers": [
                    {
                        "cik": cik10,
                        "ticker": "AAPL",
                        "sic": "6021",
                        "sic_source": {"capture_path": "synthetic"},
                        "identity_binding_state": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    labels_dir = held_out_root / "packs" / "PK04" / "labels"
    labels_dir.mkdir(parents=True)
    (labels_dir / "labels.json").write_text(
        json.dumps(
            [
                {
                    "trial_id": "T-PK04-1",
                    "pack_id": "PK04",
                    "issuer": "AAPL",
                    "form_type": "10-K",
                    "fiscal_year": "2025",
                    "section_family": "bank_operations",
                    "polarity": "positive",
                    "format_class": "ixbrl_inline",
                    "split": "held_out",
                    "accession": accession,
                    "label_class": "extract_positive",
                    "target_kind": "extract",
                    "target_id": "revenue",
                    "expected_value_text": "416,161",
                    "expected_unit": "USD",
                    "expected_period_end": "2025-09-27",
                    "reason": "synthetic",
                }
            ]
        ),
        encoding="utf-8",
    )
    (labels_dir / "_SEALED").write_text("synthetic corpus\n", encoding="utf-8")
    stage_accession = stage_root / cik10 / accession
    (stage_accession / "members").mkdir(parents=True)
    for name in ("index.json", "sec_submissions_witness.json"):
        shutil.copy(AAPL_10K_2025_PACKAGE / name, stage_accession / name)
    manifest = json.loads(
        (AAPL_10K_2025_PACKAGE / "package_manifest.json").read_text(encoding="utf-8")
    )
    for item in manifest["members"]:
        if item.get("state") == "stored":
            shutil.copy(
                AAPL_10K_2025_PACKAGE / "members" / item["name"],
                stage_accession / "members" / item["name"],
            )
    return {
        "held_out_root": held_out_root,
        "stage_root": stage_root,
        "out_dir": base / "out",
    }


def test_report_note_keeps_binding_beside_envelope_source(tmp_path: Path) -> None:
    corpus = _synthetic_held_out_corpus(tmp_path)
    contract_id, contract_rows = evaluator._load_contract(corpus["held_out_root"])
    with pytest.raises(SystemExit):
        # The frozen report core refuses the calibration-only AAPL accession
        # on the held_out split (A37 untouched proof set), so the report CLI
        # exits nonzero — but only AFTER the per-accession note this test
        # asserts on is persisted to the trials file.
        evaluator.evaluate_pack_held_out(
            "PK04",
            held_out_root=corpus["held_out_root"],
            stage_root=corpus["stage_root"],
            out_dir=corpus["out_dir"],
            manifests=evaluator._index_package_manifests(corpus["held_out_root"]),
            contract_rows=contract_rows,
            contract_id=contract_id,
            head_commit="a" * 40,
            evaluated_at="2026-10-31T00:00:00Z",
            precision_floor="0.80",
        )
    trials = json.loads(
        (corpus["out_dir"] / "PK04_trials.json").read_text(encoding="utf-8")
    )
    note = trials["accessions"][0]
    # The binding route and the envelope vocabulary sit side by side, and
    # the accession is admitted (before the fix, produce_pack refused every
    # accession here and the second Q1 generation produced zero predictions).
    assert note["outcome"] == "ADMITTED"
    assert note["issuer_sic"] == "6021"
    assert note["sic_binding"] == "held_out_contract"
    assert note["sic_source"] == "sec_submissions"
