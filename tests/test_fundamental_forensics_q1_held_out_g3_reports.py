"""Q1 held-out evaluation artifacts, third generation (A34/A37): the twelve
``_g3`` pack reports.

Checks the committed output of ``scripts/fif_held_out_evaluate.py`` under
``research/financial_intelligence_fabric/reports/q1_held_out_20261031_g3/``
(generation three under
DEC:FIF-Q0-SPLIT-DECISION-2-SECOND-LABELING-WAVE-20261031: wave-one plus
wave-two labels — the 45 split-decision-2 accessions labelled by independent
labeler lanes — re-measured on the same predeclared 0.80 floor, over the
kernel/evaluator repairs that generation two measured). The five artifact
tests mirror the generation-one module
``tests/test_fundamental_forensics_q1_held_out_evaluate.py`` (one
schema-conforming report per pack PK01..PK12 on the held-out split, one shared
head commit matching INDEX.md, complete trial accounting for every labelled
pack, INDEX rows matching the reports, no guarded token under the directory);
the two binding tests pin the generation-three non-vacuity — the trials files
record the contract-first SIC binding order, and every labelled pack measures
at least one admitted accession whose SIC bound from the held-out contract and
travelled in the envelope's own ``sic_source`` vocabulary — and the wave test
pins the generation's scope: every label file of every labelled pack, wave one
AND wave two, is accounted for exactly once, so no file may hide behind the
later-wave skip that scoping a generation to its own accession universe allows.

This module is a Q1 test: it reads the sealed held-out labels and the held-out
contract read-only (a label or seal is never modified here). The
generation-one record under ``reports/q1_held_out_20261031/`` and the
generation-two record under ``reports/q1_held_out_20261031_g2/`` are committed
history and are never opened for writing.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

# Helpers and constants exposed by the generation-one module; this file copies
# only what that module does not expose (the ``_g3``-bound path accessors).
from tests.test_fundamental_forensics_q1_held_out_evaluate import (
    HELD_OUT_ROOT,
    HELD_OUT_SPLIT_ROOT,
    PACK_IDS,
    REPORT_SCHEMA_PATH,
    _GUARDED_TOKEN,
    _families_text,
)
from tests.test_fundamental_forensics_q1_held_out_evaluate import (
    _label_trials as _label_trials_in,
)

REPORTS_DIR = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "financial_intelligence_fabric"
    / "reports"
    / "q1_held_out_20261031_g3"
)
SIC_BINDING_ORDER = ["held_out_contract", "sec_submissions_witness"]


def _label_trials(pack_id: str) -> list[str]:
    """Label trials inside generation three's own accession universe."""
    return _label_trials_in(pack_id, REPORTS_DIR)


def _report_path(pack_id: str) -> Path:
    return REPORTS_DIR / f"{pack_id}_pack_quality_report.json"


def _report(pack_id: str) -> dict:
    return json.loads(_report_path(pack_id).read_text(encoding="utf-8"))


def _trials(pack_id: str) -> dict:
    return json.loads(
        (REPORTS_DIR / f"{pack_id}_trials.json").read_text(encoding="utf-8")
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
        predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
        trials = _trials(pack_id)
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
            offenders.append(path.as_posix())
    assert offenders == [], f"guarded token present in report files: {offenders}"


def test_trials_record_the_sic_binding_order() -> None:
    # Every trials file carries the run-level binding provenance the evaluator
    # records beside the closed report schema: contract first, staged
    # sec_submissions witness second.
    for pack_id in PACK_IDS:
        trials = _trials(pack_id)
        assert trials["sic_binding"]["order"] == SIC_BINDING_ORDER, pack_id
        assert trials["sic_binding"]["contract_id"], pack_id


def test_admitted_accessions_bind_sic_from_the_held_out_contract() -> None:
    contract = json.loads(
        (HELD_OUT_ROOT / "held_out_contract.json").read_text(encoding="utf-8")
    )
    contract_sics = {row["cik"]: row["sic"] for row in contract["issuers"]}
    assert len(contract_sics) == 5, sorted(contract_sics)
    for pack_id in PACK_IDS:
        trials = _trials(pack_id)
        if trials["labels_status"] != "labelled":
            continue
        admitted = [
            note for note in trials["accessions"] if note["outcome"] == "ADMITTED"
        ]
        # Non-vacuity of the third generation: every labelled pack measures at
        # least one admitted accession with the SIC bound from the held-out
        # contract and expressed in the envelope's own sic_source vocabulary,
        # across wave one AND wave two accessions.
        assert admitted, f"{pack_id}: zero admitted accessions"
        for note in admitted:
            assert note["cik"] in contract_sics, (pack_id, note["accession"])
            assert note["sic_binding"] == "held_out_contract", (
                pack_id,
                note["accession"],
            )
            assert note["sic_source"] == "sec_submissions", (
                pack_id,
                note["accession"],
            )
            assert note["issuer_sic"] == contract_sics[note["cik"]], (
                pack_id,
                note["accession"],
            )


def test_every_label_file_of_both_waves_is_accounted_for_exactly_once() -> None:
    """Generation three measures the whole sealed root: wave one AND wave two.

    The accounting pins above scope a generation to its own accession universe
    (a later sealing wave is skipped, not counted). This pin refuses that
    escape for ``_g3``: the generation's universe must hold every label file
    of every labelled pack — wave-one files and the 45 split-decision-2
    wave-two files alike — and every trial of every file must be accounted for
    exactly once across that pack's predictions and exclusions. A wave-two
    file skipped here would mean the evaluator measured generation two's
    accessions over again and called it generation three.
    """
    for pack_id in PACK_IDS:
        labels_dir = HELD_OUT_ROOT / "packs" / pack_id / "labels"
        if not labels_dir.is_dir():
            continue
        trials = _trials(pack_id)
        assert trials["labels_status"] == "labelled", pack_id
        universe = {row["accession"] for row in trials["accessions"]}
        predictions = json.loads(
            (REPORTS_DIR / f"{pack_id}_predictions.json").read_text(encoding="utf-8")
        )
        accounted = Counter(
            [row["trial_id"] for row in predictions]
            + [row["trial_id"] for row in trials["exclusions"]]
        )
        files = sorted(labels_dir.glob("*.json"))
        assert files, f"{pack_id}: labelled pack with no label files"
        file_accessions: set[str] = set()
        for path in files:
            rows = json.loads(path.read_text(encoding="utf-8"))
            accessions = {row["accession"] for row in rows}
            # The file sits inside the generation's measured universe...
            assert accessions <= universe, (pack_id, path.name)
            file_accessions |= accessions
            # ...and every one of its trials is accounted for exactly once.
            for row in rows:
                assert accounted[row["trial_id"]] == 1, (
                    pack_id,
                    path.name,
                    row["trial_id"],
                )
        # Every measured accession traces back to a label file: the universe
        # is exactly the sealed label files, neither shrunk nor invented.
        assert file_accessions == universe, pack_id
