"""SNI-local DRAFT census that CONSUMES owner paths; no authority.

This module is an SNI-local DRAFT contract for the A01-A40 acceptance
evidence matrix. It consumes owner-supplied identity, event, market,
evaluation, and publication paths from Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options,
Research Vault, and qledger/Evaluation. It does not re-implement those
owners. Identity ids are caller-supplied opaque strings; unknown
identity stays UNRESOLVED / null.

Nothing in this census feeds a ranker, gate, sizer, signal, escalation,
or trade path. All six authority flags stay false; load_matrix refuses
a true flag at any depth.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

AUTHORITY_FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

ALLOWED_STATUS = ("DONE", "PARTIAL", "GATED", "NOT_STARTED")
ALLOWED_REF = ("main", "census")
TEST_SNI_RE = re.compile(r"^tests/test_sni_[^/]+\.py$")
RUNS_PREFIX = "research/single_name_intelligence/runs/"

REFUSAL = "authority flags must stay false; a true flag is refused"


def _walk_authority(obj: Any) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in AUTHORITY_FLAGS and value is True:
                raise ValueError(REFUSAL)
            _walk_authority(value)
    elif isinstance(obj, list):
        for item in obj:
            _walk_authority(item)


def load_matrix(path: Path) -> dict:
    """Load a matrix JSON and refuse any true authority flag at any depth."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    _walk_authority(doc)
    return doc


def _is_done_evidence_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if TEST_SNI_RE.fullmatch(normalized):
        return True
    return normalized.startswith(RUNS_PREFIX)


def check_main_evidence_paths(doc: dict, repo: Path) -> None:
    """Status law (a): every main evidence path exists as a file in the tree."""
    for case in doc["cases"]:
        for item in case["evidence"]:
            if item["ref"] != "main":
                continue
            target = repo / item["path"]
            if not target.is_file():
                raise AssertionError(
                    f"{case['id']} main evidence missing: {item['path']}"
                )


def check_done_status_law(doc: dict, repo: Path | None = None) -> None:
    """Status law (b): DONE has gated_on null and a test or run artifact."""
    del repo
    for case in doc["cases"]:
        if case["status"] != "DONE":
            continue
        if case.get("gated_on") is not None:
            raise AssertionError(
                f"{case['id']} DONE but gated_on is {case.get('gated_on')!r}"
            )
        ok = False
        for item in case["evidence"]:
            if item["ref"] == "main" and _is_done_evidence_path(item["path"]):
                ok = True
                break
        if not ok:
            raise AssertionError(
                f"{case['id']} DONE without a tests/test_sni_*.py or runs/ artifact"
            )


def check_gated_status_law(doc: dict) -> None:
    """Status law (c): GATED has gated_on R1 and a gap naming the R1 release."""
    for case in doc["cases"]:
        if case["status"] != "GATED":
            continue
        if case.get("gated_on") != "R1":
            raise AssertionError(
                f"{case['id']} GATED but gated_on is {case.get('gated_on')!r}"
            )
        gap = case.get("gap") or ""
        if not gap.strip():
            raise AssertionError(f"{case['id']} GATED with empty gap")
        if "R1" not in gap:
            raise AssertionError(
                f"{case['id']} GATED gap does not say what R1 must release"
            )


def check_non_done_gaps(doc: dict) -> None:
    """Status law (d): a non-DONE case has a non-empty gap; DONE gap is empty."""
    for case in doc["cases"]:
        gap = case.get("gap")
        if not isinstance(gap, str):
            raise AssertionError(f"{case['id']} gap must be a string")
        if case["status"] == "DONE":
            if gap != "":
                raise AssertionError(f"{case['id']} DONE gap must be empty")
        elif not gap.strip():
            raise AssertionError(f"{case['id']} {case['status']} missing gap")


def check_counts(doc: dict) -> None:
    """Status law (e): counts equal the per-status tally and sum to 40."""
    computed = {name: 0 for name in ALLOWED_STATUS}
    for case in doc["cases"]:
        status = case["status"]
        if status not in computed:
            raise AssertionError(f"{case['id']} unknown status {status!r}")
        computed[status] += 1
    if doc.get("counts") != computed:
        raise AssertionError(f"counts {doc.get('counts')!r} != {computed!r}")
    if sum(computed.values()) != 40:
        raise AssertionError(f"status tally sums to {sum(computed.values())}, not 40")


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _evidence_cell(case: dict) -> str:
    parts = [f"{item['ref']}:{item['path']}" for item in case["evidence"]]
    return "; ".join(parts)


def _gated_on_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def render(doc: dict) -> str:
    """Render the matrix markdown deterministically from the JSON document."""
    sources = doc["sources"]
    lines: list[str] = []
    lines.append("# SNI acceptance evidence matrix")
    lines.append("")
    lines.append(
        "SNI-local DRAFT census that CONSUMES owner paths; no authority. "
        f"Census `{sources['census_ref']}` (`{sources['census_path']}`). "
        f"Supersedes `{sources['supersedes']}`. "
        f"Base `{sources['base_ref']}`. "
        f"As of `{doc['as_of_utc']}`."
    )
    lines.append("")
    lines.append(
        "| ID | Title | Status | Owner | Gated on | Evidence | Gap |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for case in doc["cases"]:
        row = [
            _cell(case["id"]),
            _cell(case["title"]),
            _cell(case["status"]),
            _cell(case["owner_task"]),
            _cell(_gated_on_cell(case.get("gated_on"))),
            _cell(_evidence_cell(case)),
            _cell(case.get("gap") or ""),
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    counts = doc["counts"]
    for name in ALLOWED_STATUS:
        lines.append(f"- {name}: {counts[name]}")
    lines.append("")
    lines.append("## Gated on R1")
    lines.append("")
    gated_ids = [case["id"] for case in doc["cases"] if case["status"] == "GATED"]
    if gated_ids:
        lines.append(", ".join(gated_ids) + ".")
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Closest to DONE")
    lines.append("")
    closest = [
        case
        for case in doc["cases"]
        if case["status"] == "PARTIAL" and ";" not in (case.get("gap") or "")
    ]
    if closest:
        for case in closest:
            lines.append(f"- **{case['id']}**: {case['gap']}")
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    json_path = Path(__file__).resolve().parent / "ACCEPTANCE_EVIDENCE_MATRIX.json"
    md_path = json_path.with_suffix(".md")
    doc = load_matrix(json_path)
    md_path.write_text(render(doc), encoding="utf-8")


if __name__ == "__main__":
    main()
