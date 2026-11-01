#!/usr/bin/env python3
"""FIF Q0 — counts-only label-conformance gate for held-out splits (pre-seal).

Checks a held-out label set against the frozen Q0 quality protocol BEFORE the
set is sealed: per-pack issuer applicability (section 5 — a positive label on
a ``negative``-applicability issuer is a labeling error) and the held-out
minimum-N rows (section 6), including the format-generalization row. The
minimum-N checks mirror ``engine/fundamental_forensics/pack_evaluation.py``
and, like it, count a label as positive or negative by its ``polarity`` field
(the label_class buckets are reported but never feed a floor), so a
conforming set meets the evaluator's per-cell floors. The report is
counts-only: it carries counts, protocol vocabulary and fixed sentinels, never
record payloads (no trial ids, accessions, targets, expected values, reasons,
fiscal years, format classes or out-of-vocabulary polarities).

The on-disk layout mirrors ``scripts/fif_held_out_evaluate.py``: each pack's
labels live in ``<held-out-root>/packs/<PACK_ID>/labels/*.json`` (one JSON
list of label records per file) beside a ``_SEALED`` marker file. Unsealed
labels are read by default — that is the pre-seal labeler use;
``--require-sealed`` restores the sealed-only reading rule.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.fundamental_forensics.pack_evaluation import (  # noqa: E402
    NEGATIVE_LABEL_CLASSES,
    POLARITIES,
)

SCHEMA = "fif_q0_label_conformance.v1"
DEFAULT_PROTOCOL_PATH = (
    REPO_ROOT
    / "research"
    / "financial_intelligence_fabric"
    / "FIF_Q0_QUALITY_PROTOCOL.json"
)
SEALED_MARKER = "_SEALED"
OUTSIDE_PROTOCOL_KEY = "<outside_protocol>"
OUTSIDE_PACK_KEY = "<outside_pack>"
OUTSIDE_VOCABULARY_KEY = "<outside_vocabulary>"
# A pack whose section 5 ``forms`` or ``section_family_ids`` list is empty or
# absent places no restriction on that field: its labels are tallied under
# this sentinel and never counted as outside the pack.
UNRESTRICTED_KEY = "<unrestricted>"
# Held-out minimum-N row identifiers (Q0 protocol section 6). The two generic
# rows are matched by their frozen cell wording. The format row ("pack,
# format_class != <primary>") is parsed so the primary format comes from the
# protocol. The per-pack negative rows are the held-out rows whose cell is
# "<PACK> x <group>" (today "PK11 x non-bank issuers" and "PK12 x all five
# issuers"); as in the evaluator, an "all ..." group is one check per
# protocol issuer and any other group is one aggregate check over the issuers
# whose applicability for that pack is not "required". Pack ids, groups and
# minimum-N values always come from the protocol rows; none is hardcoded here.
HELD_OUT_SPLIT = "held_out"
POSITIVE_ISSUER_CELL = "pack, applicable issuer, polarity=positive"
PACK_NEGATIVE_CELL = "pack, polarity=negative"
FORMAT_ROW_RE = re.compile(r"^pack, format_class != (\S+)$")
NEGATIVE_ISSUER_ROW_RE = re.compile(r"^(PK\d\d) x (.+)$")
# The only record keys this gate reads; every other LabelRecord field is
# ignored and never reaches the output.
REQUIRED_RECORD_KEYS = (
    "pack_id",
    "issuer",
    "form_type",
    "section_family",
    "label_class",
    "polarity",
    "format_class",
)
# Positive label classes of the Q0 vocabulary (section 5): the extract and
# finding classes a negative-applicability issuer must never carry.
POSITIVE_LABEL_CLASSES = frozenset(
    {
        "extract_positive",
        "finding_triggered_expected",
    }
)


def _fail(message: str) -> None:
    """Exit 2 (usage/input error); messages carry paths and key names only."""
    print(f"fif_q0_label_conformance: error: {message}", file=sys.stderr)
    raise SystemExit(2)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Counts-only Q0 label-conformance gate for held-out splits "
            "(pre-seal): checks per-pack issuer applicability and the "
            "held-out minimum-N rows before a label set is sealed."
        )
    )
    parser.add_argument(
        "--held-out-root",
        required=True,
        type=Path,
        help="held-out split root (<root>/packs/<PACK_ID>/labels/*.json); "
        "required, no default — the gate never looks for labels on its own",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=DEFAULT_PROTOCOL_PATH,
        help="Q0 quality protocol JSON (default: the repo's frozen protocol)",
    )
    parser.add_argument(
        "--packs",
        nargs="+",
        metavar="PK",
        default=None,
        help="pack ids to check (default: every pack_id in the protocol)",
    )
    parser.add_argument(
        "--require-sealed",
        action="store_true",
        help="refuse a labels dir that holds *.json without a _SEALED marker",
    )
    parser.add_argument(
        "--min-positive-per-family",
        type=int,
        default=None,
        metavar="N",
        help="also require >= N positive labels per section family of a pack",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the JSON report here instead of stdout",
    )
    return parser.parse_args(argv)


def _load_protocol(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            protocol = json.load(handle)
    except OSError as exc:
        _fail(f"cannot read protocol file {path}: {exc.strerror or exc}")
    except json.JSONDecodeError as exc:
        _fail(f"protocol file {path} is not valid JSON: {exc.msg}")
    if not isinstance(protocol, dict):
        _fail(f"protocol file {path}: top level is not a JSON object")
    for key in ("protocol_id", "issuers", "packs", "label_classes", "minimum_n"):
        if key not in protocol:
            _fail(f"protocol file {path}: missing key {key}")
    if not isinstance(protocol["issuers"], list):
        _fail(f"protocol file {path}: issuers is not a list")
    for entry in protocol["label_classes"]:
        if not isinstance(entry, dict) or not isinstance(
            entry.get("label_class"), str
        ):
            _fail(
                f"protocol file {path}: bad label_classes entry "
                "(missing key label_class)"
            )
    for pack in protocol["packs"]:
        if not isinstance(pack, dict) or not isinstance(pack.get("pack_id"), str):
            _fail(f"protocol file {path}: bad packs entry (missing key pack_id)")
    for row in protocol["minimum_n"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("cell"), str)
            or not isinstance(row.get("minimum_n"), int)
        ):
            _fail(
                f"protocol file {path}: bad minimum_n row "
                "(missing key cell or minimum_n)"
            )
    return protocol


def _read_label_rows(labels_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(labels_dir.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except OSError as exc:
            _fail(f"cannot read label file {path}: {exc.strerror or exc}")
        except json.JSONDecodeError:
            _fail(f"label file {path} is not valid JSON")
        if not isinstance(payload, list):
            _fail(f"label file {path}: expected a JSON list of label records")
        for record in payload:
            if not isinstance(record, dict):
                _fail(f"label file {path}: record is not a JSON object")
            for key in REQUIRED_RECORD_KEYS:
                if key not in record:
                    _fail(f"label file {path}: record missing key {key}")
        rows.extend(payload)
    return rows


def _row_minimum(rows: list[dict], cell: str) -> int | None:
    for row in rows:
        if row["cell"] == cell:
            return row["minimum_n"]
    return None


def _held_out_gates(protocol: dict) -> dict:
    """Minimum-N needs derived from the protocol's held_out rows only."""
    held_out_rows = [
        row for row in protocol["minimum_n"] if row.get("split") == HELD_OUT_SPLIT
    ]
    format_cell = None
    for row in held_out_rows:
        match = FORMAT_ROW_RE.match(row["cell"])
        if match:
            format_cell = (match.group(1), row["minimum_n"])
            break
    return {
        "positive_cell": _row_minimum(held_out_rows, POSITIVE_ISSUER_CELL),
        "pack_negative": _row_minimum(held_out_rows, PACK_NEGATIVE_CELL),
        "format_cell": format_cell,
        "negative_issuer": {
            match.group(1): (
                match.group(2).startswith("all "),
                row["minimum_n"],
            )
            for row in held_out_rows
            if (match := NEGATIVE_ISSUER_ROW_RE.match(row["cell"]))
        },
    }


def _issuer_cell(applicability: str | None) -> dict:
    return {
        "applicability": applicability,
        "positive": 0,
        "negative": 0,
        "other": 0,
        "polarity": {},
    }


def _class_cell() -> dict:
    return {"positive": 0, "negative": 0, "other": 0, "polarity": {}}


def _empty_pack_report() -> dict:
    return {
        "labels_present": False,
        "sealed": False,
        "n_labels": 0,
        "by_issuer": {},
        "by_family": {},
        "by_form": {},
        "format_nonprimary": 0,
        "violations": {},
        "shortfalls": [],
    }


def _pack_shortfalls(
    pack_id: str,
    applicability: dict,
    family_ids: list[str],
    issuers: list[str],
    by_issuer: dict,
    by_family: dict,
    pack_negatives: int,
    format_nonprimary: int,
    min_positive_per_family: int | None,
    gates: dict,
) -> list[dict]:
    shortfalls: list[dict] = []
    positive_need = gates["positive_cell"]
    if positive_need is not None:
        # Applicable issuers, as in the evaluator: every "required" issuer,
        # plus each "optional" issuer that carries at least one label (every
        # label adds exactly one polarity tally to its issuer's cell). Every
        # floor counts by polarity, as the evaluator does.
        for issuer in issuers:
            state = applicability.get(issuer)
            labeled = sum(by_issuer[issuer]["polarity"].values()) > 0
            if state == "required" or (state == "optional" and labeled):
                have = by_issuer[issuer]["polarity"].get("positive", 0)
                if have < positive_need:
                    shortfalls.append(
                        {
                            "code": "positive_cell_short",
                            "scope": issuer,
                            "have": have,
                            "need": positive_need,
                        }
                    )
    negative_need = gates["pack_negative"]
    if negative_need is not None and pack_negatives < negative_need:
        shortfalls.append(
            {
                "code": "negative_cell_short",
                "scope": "pack",
                "have": pack_negatives,
                "need": negative_need,
            }
        )
    format_cell = gates["format_cell"]
    if format_cell is not None and format_nonprimary < format_cell[1]:
        shortfalls.append(
            {
                "code": "format_cell_short",
                "scope": "pack",
                "have": format_nonprimary,
                "need": format_cell[1],
            }
        )
    issuer_row = gates["negative_issuer"].get(pack_id)
    if issuer_row is not None:
        per_issuer, issuer_row_need = issuer_row
        if per_issuer:
            for issuer in issuers:
                have = by_issuer[issuer]["polarity"].get("negative", 0)
                if have < issuer_row_need:
                    shortfalls.append(
                        {
                            "code": "negative_issuer_short",
                            "scope": issuer,
                            "have": have,
                            "need": issuer_row_need,
                        }
                    )
        else:
            have = sum(
                by_issuer[issuer]["polarity"].get("negative", 0)
                for issuer in issuers
                if applicability.get(issuer) != "required"
            )
            if have < issuer_row_need:
                shortfalls.append(
                    {
                        "code": "negative_group_short",
                        "scope": "pack",
                        "have": have,
                        "need": issuer_row_need,
                    }
                )
    if min_positive_per_family is not None:
        for family in family_ids:
            have = by_family[family]["polarity"].get("positive", 0)
            if have < min_positive_per_family:
                shortfalls.append(
                    {
                        "code": "family_positive_short",
                        "scope": family,
                        "have": have,
                        "need": min_positive_per_family,
                    }
                )
    return shortfalls


def _scan_pack(
    pack_id: str,
    config: dict,
    issuers: list[str],
    issuer_set: set[str],
    vocabulary: set[str],
    labels_dir: Path,
    require_sealed: bool,
    min_positive_per_family: int | None,
    gates: dict,
) -> dict:
    if not labels_dir.is_dir():
        return _empty_pack_report()
    sealed = (labels_dir / SEALED_MARKER).is_file()
    label_files = sorted(labels_dir.glob("*.json"))
    if require_sealed and label_files and not sealed:
        _fail(
            f"{labels_dir}: holds label JSON without a {SEALED_MARKER} marker "
            "while --require-sealed is set"
        )
    rows = _read_label_rows(labels_dir)

    applicability = config.get("applicability", {})
    family_ids = list(config.get("section_family_ids", []))
    family_set = set(family_ids)
    form_ids = list(config.get("forms", []))
    form_set = set(form_ids)

    by_issuer = {issuer: _issuer_cell(applicability.get(issuer)) for issuer in issuers}
    by_family = {family: _class_cell() for family in family_ids}
    by_form = {form: 0 for form in form_ids}
    violations: dict[str, int] = {}
    pack_negatives = 0
    format_nonprimary = 0
    primary_format = gates["format_cell"][0] if gates["format_cell"] else None

    def count(code: str) -> None:
        violations[code] = violations.get(code, 0) + 1

    for record in rows:
        issuer = record["issuer"]
        label_class = record["label_class"]
        if record["pack_id"] != pack_id:
            count("pack_mismatch")
        if label_class in POSITIVE_LABEL_CLASSES:
            bucket = "positive"
        elif label_class in NEGATIVE_LABEL_CLASSES:
            bucket = "negative"
        elif label_class in vocabulary:
            bucket = "other"
        else:
            bucket = None
            count("label_class_outside_vocabulary")
        if issuer in issuer_set:
            issuer_key = issuer
        else:
            issuer_key = OUTSIDE_PROTOCOL_KEY
            count("issuer_outside_protocol")
        if bucket == "positive" and applicability.get(issuer) == "negative":
            count("positive_on_negative_issuer")
        cell = by_issuer.setdefault(
            issuer_key, _issuer_cell(applicability.get(issuer))
        )
        if bucket is not None:
            cell[bucket] += 1
        polarity = record["polarity"]
        if polarity in POLARITIES:
            polarity_key = polarity
        else:
            polarity_key = OUTSIDE_VOCABULARY_KEY
            count("polarity_outside_vocabulary")
        cell["polarity"][polarity_key] = cell["polarity"].get(polarity_key, 0) + 1
        if polarity_key == "negative":
            pack_negatives += 1

        if primary_format is not None and record["format_class"] != primary_format:
            format_nonprimary += 1

        section_family = record["section_family"]
        if not family_set:
            family_key = UNRESTRICTED_KEY
        elif section_family in family_set:
            family_key = section_family
        else:
            family_key = OUTSIDE_PACK_KEY
            count("section_family_outside_pack")
        family_cell = by_family.setdefault(family_key, _class_cell())
        if bucket is not None:
            family_cell[bucket] += 1
        family_cell["polarity"][polarity_key] = (
            family_cell["polarity"].get(polarity_key, 0) + 1
        )

        form_type = record["form_type"]
        if not form_set:
            form_key = UNRESTRICTED_KEY
        elif form_type in form_set:
            form_key = form_type
        else:
            form_key = OUTSIDE_PACK_KEY
            count("form_outside_pack")
        by_form[form_key] = by_form.get(form_key, 0) + 1

    return {
        "labels_present": True,
        "sealed": sealed,
        "n_labels": len(rows),
        "by_issuer": by_issuer,
        "by_family": by_family,
        "by_form": by_form,
        "format_nonprimary": format_nonprimary,
        "violations": violations,
        "shortfalls": _pack_shortfalls(
            pack_id,
            applicability,
            family_ids,
            issuers,
            by_issuer,
            by_family,
            pack_negatives,
            format_nonprimary,
            min_positive_per_family,
            gates,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.held_out_root.is_dir():
        _fail(f"held-out root {args.held_out_root}: directory does not exist")
    protocol = _load_protocol(args.protocol)
    issuers = list(protocol["issuers"])
    issuer_set = set(issuers)
    vocabulary = {entry["label_class"] for entry in protocol["label_classes"]}
    packs_by_id = {pack["pack_id"]: pack for pack in protocol["packs"]}
    requested = list(args.packs) if args.packs else list(packs_by_id)
    for pack_id in requested:
        if pack_id not in packs_by_id:
            _fail(f"unknown pack id {pack_id}: not defined by protocol {args.protocol}")
    gates = _held_out_gates(protocol)

    pack_reports = {}
    for pack_id in requested:
        labels_dir = args.held_out_root / "packs" / pack_id / "labels"
        pack_reports[pack_id] = _scan_pack(
            pack_id,
            packs_by_id[pack_id],
            issuers,
            issuer_set,
            vocabulary,
            labels_dir,
            args.require_sealed,
            args.min_positive_per_family,
            gates,
        )

    totals = {
        "violations": sum(
            sum(pack["violations"].values()) for pack in pack_reports.values()
        ),
        "shortfalls": sum(len(pack["shortfalls"]) for pack in pack_reports.values()),
    }
    conforming = totals["violations"] == 0 and totals["shortfalls"] == 0
    report = {
        "schema": SCHEMA,
        "protocol_id": protocol["protocol_id"],
        "require_sealed": args.require_sealed,
        "min_positive_per_family": args.min_positive_per_family,
        "packs": pack_reports,
        "totals": totals,
        "conforming": conforming,
    }
    payload = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.out is not None:
        try:
            args.out.write_text(payload, encoding="utf-8")
        except OSError as exc:
            _fail(f"cannot write report file {args.out}: {exc.strerror or exc}")
    else:
        sys.stdout.write(payload)
    return 0 if conforming else 1


if __name__ == "__main__":
    sys.exit(main())
