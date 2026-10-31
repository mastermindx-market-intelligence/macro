#!/usr/bin/env python3
"""FIF Q1 — independent held-out evaluation driver (A34/A37, protocol v1).

The ONLY reader of the sealed held-out labels. For every pack PK01..PK12 this
script (a) reads the pack's labels under the held-out root (refusing a labels
directory without its ``_SEALED`` marker), (b) admits the staged held-out
filing bytes for each labelled accession through
``admit_retained_filing_package``, (c) produces the pack envelope with exactly
one ``produce_pack`` call per accession, (d) adapts the envelope into
prediction records with ``predictions_from_pack_result`` (constructing a
``not_evaluable``/``field_not_in_envelope`` record for a labelled field the
envelope carries no row for), and (e) writes the frozen per-pack quality
report through the existing CLI ``scripts/fif_pack_quality_report.py``.

Outputs per pack (under ``--out-dir``):
``PKxx_predictions.json`` (the prediction-record list the CLI scored),
``PKxx_trials.json`` (the trial_id -> field_id map, per-accession admission
outcomes, and the excluded trials with their exclusion reasons), and
``PKxx_pack_quality_report.json`` (+ its ``.power.json`` companion, written by
the CLI). One ``INDEX.md`` row per pack summarises the twelve reports.

A pack with no ``labels/`` directory is produced over an empty label set and
marked ``no_held_out_labels`` in INDEX.md (labels are never invented). An
accession whose retained members are missing from the stage is reported as
``package_unavailable``; an accession whose bytes refuse admission excludes
every one of its trials with ``package_admission_refused:<code>``. The
manifest and members are never patched to make an accession admit.

No network, no environment reads, no wall clock: determinism follows from the
command-line arguments alone.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.fundamental_forensics.admitted_filing_package import (  # noqa: E402
    AdmittedFilingPackageError,
    admit_retained_filing_package,
)
from engine.fundamental_forensics.specialist_pack_contract import (  # noqa: E402
    PACK_IDS,
    load_pack_schema,
)
from engine.fundamental_forensics.specialist_packs import (  # noqa: E402
    PackInput,
    SpecialistPackError,
    produce_pack,
)
from engine.fundamental_forensics.statement_graph import (  # noqa: E402
    StatementGraphError,
)
from engine.fundamental_forensics.pack_evaluation import (  # noqa: E402
    PredictionRecord,
    predictions_from_pack_result,
)

HELD_OUT_DEFAULT = _ROOT / "tests" / "fixtures" / "fundamental_forensics_held_out"
STAGE_DEFAULT = Path.home() / "lanes" / "stage" / "fif-heldout"
OUT_DEFAULT = (
    _ROOT
    / "research"
    / "financial_intelligence_fabric"
    / "reports"
    / "q1_held_out_20261031"
)
LABELS_STATUS_LABELLED = "labelled"
LABELS_STATUS_NONE = "no_held_out_labels"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fif_held_out_evaluate",
        description=(
            "Independent Q1 held-out evaluation of the FIF specialist packs "
            "(A34/A37); the only reader of the sealed held-out labels."
        ),
    )
    parser.add_argument(
        "--held-out-root",
        default=str(HELD_OUT_DEFAULT),
        help="held-out fixture root (labels under packs/PKxx/labels)",
    )
    parser.add_argument(
        "--stage-root",
        default=str(STAGE_DEFAULT),
        help="read-only staged filing bytes root (<cik10>/<accession>)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DEFAULT),
        help="report output directory",
    )
    parser.add_argument("--head-commit", required=True, help="40-hex evaluated commit")
    parser.add_argument(
        "--evaluated-at", required=True, help="ISO-8601 UTC run timestamp"
    )
    parser.add_argument(
        "--precision-floor",
        required=True,
        help="predeclared extraction-precision Wilson lower-bound floor",
    )
    parser.add_argument(
        "--pack",
        action="append",
        default=[],
        metavar="PKnn",
        help="restrict to one pack id (repeatable); default: PK01..PK12",
    )
    return parser


# ---------------------------------------------------------------------------
# held-out inputs


def _load_contract(held_out_root: Path) -> tuple[str, dict[str, dict]]:
    """(contract_id, issuer rows keyed by canonical CIK)."""
    contract = json.loads(
        (held_out_root / "held_out_contract.json").read_text(encoding="utf-8")
    )
    return contract["contract_id"], {row["cik"]: row for row in contract["issuers"]}


def _index_package_manifests(held_out_root: Path) -> dict[str, tuple[str, Path]]:
    """accession -> (cik10, manifest path) over packages/<cik10>/<accession>/."""
    packages = held_out_root / "packages"
    index: dict[str, tuple[str, Path]] = {}
    for manifest_path in sorted(packages.glob("*/*/package_manifest.json")):
        index[manifest_path.parent.name] = (
            manifest_path.parent.parent.name,
            manifest_path,
        )
    return index


def _read_labels(held_out_root: Path, pack_id: str) -> tuple[str, list[dict]]:
    """(labels_status, label rows) for one pack; refuses an unsealed dir."""
    labels_dir = held_out_root / "packs" / pack_id / "labels"
    if not labels_dir.is_dir():
        return LABELS_STATUS_NONE, []
    if not (labels_dir / "_SEALED").is_file():
        raise SystemExit(
            f"{labels_dir} holds label JSON without a _SEALED marker; "
            "refusing to read it"
        )
    rows: list[dict] = []
    for path in sorted(labels_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise SystemExit(f"{path}: expected a JSON list of label records")
        rows.extend(payload)
    rows.sort(key=lambda item: item["trial_id"])
    return LABELS_STATUS_LABELLED, rows


def _cli_label_rows(rows: Sequence[Mapping]) -> list[dict]:
    """Label rows as the report CLI takes them (fiscal_year as its declared str)."""
    out = [dict(row) for row in rows]
    for item in out:
        item["fiscal_year"] = str(item["fiscal_year"])
    return out


# ---------------------------------------------------------------------------
# staged bytes


def _admit_staged(
    stage_root: Path, cik10: str, accession: str, manifest: Mapping
) -> tuple[str, str, object]:
    """(outcome, detail, admitted package).

    outcome: ``ADMITTED`` | ``package_unavailable`` | ``package_admission_refused``.
    Checks the read-only stage for every retained member BEFORE admission; the
    manifest and members are never patched to make an accession admit.
    """
    stage_dir = stage_root / cik10 / accession
    index_path = stage_dir / "index.json"
    witness_path = stage_dir / "sec_submissions_witness.json"
    if not index_path.is_file():
        return "package_unavailable", "stage_index_missing", None
    if not witness_path.is_file():
        return "package_unavailable", "stage_witness_missing", None
    members: dict[str, bytes] = {}
    for item in manifest["members"]:
        if item.get("state") != "stored":
            continue
        member_path = stage_dir / "members" / item["name"]
        if not member_path.is_file():
            return "package_unavailable", f"stage_member_missing:{item['name']}", None
        members[item["name"]] = member_path.read_bytes()
    try:
        package = admit_retained_filing_package(
            index_bytes=index_path.read_bytes(),
            manifest=manifest,
            members=members,
            witness_bytes=witness_path.read_bytes(),
            capture_recorded_at=manifest["fixture_recorded_at"],
        )
    except AdmittedFilingPackageError as exc:
        return "package_admission_refused", exc.code, None
    return "ADMITTED", "", package


def _witness_sic(witness: Mapping) -> tuple[str | None, str]:
    """(issuer_sic, sic_source) from the staged sec_submissions witness."""
    sic = witness.get("sic") if isinstance(witness, dict) else None
    if isinstance(sic, str) and sic.isdigit():
        return sic, "sec_submissions"
    return None, "unbound"


# ---------------------------------------------------------------------------
# packet inputs


def _entity_for(
    manifest: Mapping,
    contract_rows: Mapping[str, Mapping],
    contract_id: str,
) -> dict:
    row = contract_rows.get(manifest["cik"])
    if row is None:
        raise SystemExit(
            f"the held-out contract carries no issuer row for CIK "
            f"{manifest['cik']}; cannot build the packet entity"
        )
    return {
        "entity_id": manifest["entity_id"],
        "cik": manifest["cik"],
        "ticker": row["ticker"],
        "name": manifest["legal_name"],
        "identity_basis": f"{contract_id}:{row['identity_binding_state']}",
        "source_entity_id": manifest["cik"],
    }


def _query_for(manifest: Mapping, requested_metrics: Sequence[str]) -> dict:
    return {
        "policy": "as_reported",
        "source_event_cutoff": manifest["source_accepted_at"],
        "system_recorded_cutoff": manifest["fixture_recorded_at"],
        "requested_metrics": list(requested_metrics),
        "requested_periods": [manifest["period_of_report"]],
        "evaluation_mode": "historical_replay",
    }


# ---------------------------------------------------------------------------
# one pack


def _prediction_row(record: PredictionRecord) -> dict:
    return {
        "trial_id": record.trial_id,
        "target_kind": record.target_kind,
        "target_id": record.target_id,
        "state": record.state,
        "value_text": record.value_text,
        "unit": record.unit,
        "period_end": record.period_end,
        "span_ref": record.span_ref,
        "finding_id": record.finding_id,
        "display_copy": list(record.display_copy),
        "alternative_explanation": record.alternative_explanation,
        "exclusion_reason": record.exclusion_reason,
    }


def evaluate_pack_held_out(
    pack_id: str,
    *,
    held_out_root: Path,
    stage_root: Path,
    out_dir: Path,
    manifests: Mapping[str, tuple[str, Path]],
    contract_rows: Mapping[str, Mapping],
    contract_id: str,
    head_commit: str,
    evaluated_at: str,
    precision_floor: str,
) -> dict:
    """Run one pack end to end; returns the summary row for INDEX.md."""
    labels_status, label_rows = _read_labels(held_out_root, pack_id)
    by_accession: dict[str, list[dict]] = {}
    for row in label_rows:
        by_accession.setdefault(row["accession"], []).append(row)

    catalogue = [
        field["field_id"]
        for field in load_pack_schema(pack_id).get("fields") or ()
        if isinstance(field, dict) and isinstance(field.get("field_id"), str)
    ]

    predictions: list[PredictionRecord] = []
    exclusions: list[dict] = []
    trial_field_map: dict[str, str] = {}
    accessions_note: list[dict] = []
    for accession in sorted(by_accession):
        rows = by_accession[accession]
        for row in rows:
            trial_field_map[row["trial_id"]] = row["target_id"]
        note = {
            "accession": accession,
            "cik": "",
            "form": rows[0]["form_type"],
            "period_of_report": "",
            "outcome": "",
            "detail": "",
            "applicability_state": None,
            "applicability_reason": None,
            "issuer_sic": None,
            "sic_source": "unbound",
            "labels": len(rows),
            "predictions": 0,
            "prediction_states": {},
            "unmapped_pack_fields": [],
        }
        accessions_note.append(note)
        entry = manifests.get(accession)
        if entry is None:
            note["outcome"] = "package_unavailable"
            note["detail"] = "manifest_missing"
            _exclude_all(rows, "package_unavailable:manifest_missing", exclusions)
            continue
        cik10, manifest_path = entry
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        note["cik"] = cik10
        note["period_of_report"] = manifest["period_of_report"]
        outcome, detail, package = _admit_staged(
            stage_root, cik10, accession, manifest
        )
        note["outcome"] = outcome
        note["detail"] = detail
        if outcome != "ADMITTED":
            _exclude_all(rows, f"{outcome}:{detail}", exclusions)
            continue
        witness = json.loads(
            (stage_root / cik10 / accession / "sec_submissions_witness.json").read_text(
                encoding="utf-8"
            )
        )
        issuer_sic, sic_source = _witness_sic(witness)
        note["issuer_sic"] = issuer_sic
        note["sic_source"] = sic_source
        try:
            result = produce_pack(
                pack_id,
                PackInput(
                    packages=(package,),
                    entity=_entity_for(manifest, contract_rows, contract_id),
                    query=_query_for(manifest, catalogue),
                    issuer_sic=issuer_sic,
                    sic_source=sic_source,
                ),
            )
        except (SpecialistPackError, StatementGraphError, ValueError, KeyError) as exc:
            note["outcome"] = "pack_production_refused"
            note["detail"] = f"{type(exc).__name__}"
            _exclude_all(rows, f"pack_production_refused:{type(exc).__name__}", exclusions)
            continue
        applicability = result.get("applicability")
        if isinstance(applicability, dict):
            note["applicability_state"] = applicability.get("state")
            note["applicability_reason"] = applicability.get("reason")
        trial_ids = {row["target_id"]: row["trial_id"] for row in rows}
        records, unmapped = predictions_from_pack_result(
            result, accession=accession, trial_ids=trial_ids
        )
        adapted = {record.target_id: record for record in records}
        for field_id in sorted(trial_ids):
            if field_id in adapted:
                continue
            adapted[field_id] = PredictionRecord(
                trial_id=trial_ids[field_id],
                target_kind="extract",
                target_id=field_id,
                state="not_evaluable",
                exclusion_reason="field_not_in_envelope",
            )
        held = [adapted[field_id] for field_id in sorted(adapted)]
        predictions.extend(held)
        states: dict[str, int] = {}
        for record in held:
            states[record.state] = states.get(record.state, 0) + 1
        note["predictions"] = len(held)
        note["prediction_states"] = dict(sorted(states.items()))
        note["unmapped_pack_fields"] = sorted(unmapped)

    predictions.sort(key=lambda record: record.trial_id)
    prediction_rows = [_prediction_row(record) for record in predictions]

    out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = out_dir / f"{pack_id}_predictions.json"
    predictions_path.write_text(
        json.dumps(prediction_rows, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    trials_payload = {
        "pack_id": pack_id,
        "labels_status": labels_status,
        "label_count": len(label_rows),
        "trial_field_map": dict(sorted(trial_field_map.items())),
        "exclusions": sorted(exclusions, key=lambda item: item["trial_id"]),
        "accessions": accessions_note,
    }
    (out_dir / f"{pack_id}_trials.json").write_text(
        json.dumps(trials_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report_path = out_dir / f"{pack_id}_pack_quality_report.json"
    with tempfile.TemporaryDirectory(prefix="fif_q1_") as tmp:
        labels_path = Path(tmp) / "labels.json"
        labels_path.write_text(
            json.dumps(
                _cli_label_rows(label_rows),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            str(_ROOT / "scripts" / "fif_pack_quality_report.py"),
            "--protocol-root",
            str(_ROOT),
            "--pack",
            pack_id,
            "--split",
            "held_out",
            "--labels",
            str(labels_path),
            "--predictions",
            str(predictions_path),
            "--head-commit",
            head_commit,
            "--evaluated-at",
            evaluated_at,
            "--out",
            str(report_path),
            "--precision-floor",
            precision_floor,
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise SystemExit(
                f"{pack_id}: report CLI refused (exit {completed.returncode}): "
                f"{completed.stderr.strip()}"
            )
        for line in completed.stdout.splitlines():
            if line.startswith("GAP:"):
                print(f"{pack_id} {line}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "pack_id": pack_id,
        "pack_name": report["pack_name"],
        "labels_status": labels_status,
        "label_count": len(label_rows),
        "report": report,
        "accessions": accessions_note,
    }


def _exclude_all(rows: Sequence[Mapping], reason: str, exclusions: list[dict]) -> None:
    for row in rows:
        exclusions.append({"trial_id": row["trial_id"], "exclusion_reason": reason})


# ---------------------------------------------------------------------------
# INDEX.md


def _rate(frac: Mapping) -> str:
    wilson = frac.get("wilson95")
    if wilson is None:
        return f"{frac['numerator']}/{frac['denominator']}"
    return f"{frac['numerator']}/{frac['denominator']} [{wilson[0]:.4f}, {wilson[1]:.4f}]"


def _families_text(report: Mapping) -> str:
    families = report.get("failed_families") or []
    if not families:
        return "-"
    return "; ".join(
        f"{family['section_family']}({'+'.join(family['reason_codes'])})"
        for family in families
    )


def _pack_disposition(summary: Mapping) -> str:
    if summary["labels_status"] == LABELS_STATUS_NONE:
        return "unavailable_research_only"
    report = summary["report"]
    families = report.get("failed_families") or []
    if any(family["disposition"] == "blocked_pack" for family in families):
        return "blocked_pack"
    if families:
        return "unavailable_research_only"
    return report["quality_label"]


def _write_index(
    out_dir: Path,
    summaries: Sequence[Mapping],
    *,
    stage_root: Path,
    head_commit: str,
    evaluated_at: str,
    precision_floor: str,
) -> None:
    lines: list[str] = []
    lines.append("# FIF Q1 held-out pack quality index (A34/A37)")
    lines.append("")
    lines.append(
        "- protocol: fif-q0-quality-protocol/v1; report schema "
        "fundamental_forensics.pack_quality_report/v1; evaluator role "
        "independent_q1"
    )
    lines.append(f"- head_commit: {head_commit}")
    lines.append(f"- evaluated_at: {evaluated_at}")
    lines.append(
        "- precision floor (predeclared seat ruling 2026-10-31, before any "
        "held-out result was observed): extraction-precision Wilson lower "
        f"bound {precision_floor} for every pack and cell"
    )
    lines.append(
        "- split root: tests/fixtures/fundamental_forensics_held_out (sealed "
        "labels; this lane is their only reader; pack builders never read them)"
    )
    lines.append(f"- staged bytes (read-only): {stage_root}")
    lines.append(
        "- every rate is numerator/denominator with Wilson 95% bounds "
        "[lower, upper]; a bare numerator/denominator holds where the report "
        "carries no interval"
    )
    lines.append(
        "- quality vocabulary is the Q0 set only: held_out_measured, "
        "underpowered, unavailable_research_only, blocked_pack"
    )
    lines.append("")
    lines.append(
        "| pack | name | labels | quality_label | cells | precision | recall | "
        "abstention | FP rate | failed families | disposition | "
        "package unavailable |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for summary in summaries:
        report = summary["report"]
        if summary["labels_status"] == LABELS_STATUS_NONE:
            labels_cell = LABELS_STATUS_NONE
            quality_cell = "unavailable_research_only"
            cells_cell = "0"
            rates = ["-"] * 4
            families_cell = "-"
        else:
            metrics = report["metrics"]["extraction"]
            labels_cell = str(summary["label_count"])
            quality_cell = report["quality_label"]
            cells_cell = str(len(report.get("cells") or []))
            rates = [
                _rate(metrics["precision"]),
                _rate(metrics["recall"]),
                _rate(metrics["abstention"]),
                _rate(metrics["false_positive_rate"]),
            ]
            families_cell = _families_text(report)
        unavailable = sorted(
            note["accession"]
            for note in summary["accessions"]
            if note["outcome"] == "package_unavailable"
        )
        lines.append(
            f"| {summary['pack_id']} | {summary['pack_name']} | {labels_cell} | "
            f"{quality_cell} | {cells_cell} | {rates[0]} | {rates[1]} | "
            f"{rates[2]} | {rates[3]} | {families_cell} | "
            f"{_pack_disposition(summary)} | "
            f"{'; '.join(unavailable) if unavailable else '-'} |"
        )
    lines.append("")
    lines.append("## Failed-family detail (frozen scoring core)")
    lines.append("")
    any_family = False
    for summary in summaries:
        for family in summary["report"].get("failed_families") or []:
            any_family = True
            rates = family.get("numerator_denominator") or {}
            lines.append(
                f"- {summary['pack_id']} {family['section_family']}: reasons "
                f"{'+'.join(family['reason_codes'])}; disposition "
                f"{family['disposition']}; blocks {family['blocks']}; "
                f"precision {rates.get('precision')}, recall "
                f"{rates.get('recall')}, abstention {rates.get('abstention')}, "
                f"fp {rates.get('false_positive_rate')}; relabelling is "
                "forbidden and reopening requires a fresh Q0 split decision"
            )
    if not any_family:
        lines.append("- none")
    lines.append("")
    lines.append("## Per-accession admission and production outcomes")
    lines.append("")
    for summary in summaries:
        for note in summary["accessions"]:
            detail = f" ({note['detail']})" if note.get("detail") else ""
            applicability = ""
            if note.get("applicability_state"):
                applicability = (
                    f"; applicability {note['applicability_state']}"
                    f" ({note['applicability_reason']})"
                )
            lines.append(
                f"- {summary['pack_id']} {note['accession']}: "
                f"{note['outcome']}{detail}; {note['labels']} labels, "
                f"{note['predictions']} predictions{applicability}"
            )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for summary in summaries:
        if summary["labels_status"] == LABELS_STATUS_NONE:
            lines.append(
                f"- {summary['pack_id']} has no labels/ directory under the "
                "held-out root: reported unavailable_research_only with "
                "reason no_held_out_labels; its report was produced over an "
                "empty label set (the frozen core labels that report "
                "underpowered over zero labels); no label was invented"
            )
    lines.append(
        "- power checks come from the protocol minimum_n rows; every labelled "
        "pack carries ixbrl_inline labels only in this label generation, so "
        "the format-generalization minimum (one non-inline label per pack) is "
        "unmet and the frozen core assigns the underpowered quality label "
        "pack-wide"
    )
    lines.append("")
    (out_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pack_ids = sorted(set(args.pack)) if args.pack else list(PACK_IDS)
    for pack_id in pack_ids:
        if pack_id not in PACK_IDS:
            raise SystemExit(f"unknown pack id {pack_id!r} (expected one of PK01..PK12)")
    held_out_root = Path(args.held_out_root)
    stage_root = Path(args.stage_root)
    out_dir = Path(args.out_dir)
    contract_id, contract_rows = _load_contract(held_out_root)
    manifests = _index_package_manifests(held_out_root)
    summaries = []
    for pack_id in pack_ids:
        print(f"== {pack_id}")
        summaries.append(
            evaluate_pack_held_out(
                pack_id,
                held_out_root=held_out_root,
                stage_root=stage_root,
                out_dir=out_dir,
                manifests=manifests,
                contract_rows=contract_rows,
                contract_id=contract_id,
                head_commit=args.head_commit,
                evaluated_at=args.evaluated_at,
                precision_floor=args.precision_floor,
            )
        )
    _write_index(
        out_dir,
        summaries,
        stage_root=stage_root,
        head_commit=args.head_commit,
        evaluated_at=args.evaluated_at,
        precision_floor=args.precision_floor,
    )
    for summary in summaries:
        report = summary["report"]
        print(
            f"{summary['pack_id']}: {report['quality_label']} "
            f"({len(report.get('cells') or [])} cells, "
            f"{len(report.get('false_positives') or [])} false positives, "
            f"{len(report.get('failed_families') or [])} failed families)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
