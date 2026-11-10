"""Read-only qualification against an exact, complete Macro source snapshot.

This is an evidence command, not a replacement compiler or a membership owner.
Usage: python verify_current_universe.py /path/to/isolated/full/macro
Keep classification_census.json and workstream_sources.json beside this file.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_current_universe.py FULL_ISOLATED_MACRO_ROOT")
    repo = Path(sys.argv[1]).resolve(strict=True)
    evidence = Path(__file__).resolve().parent
    sources = json.loads((evidence / "workstream_sources.json").read_text())
    census = json.loads((evidence / "classification_census.json").read_text())
    expected = {row["path"]: row["git_blob"] for row in sources["entries"]}
    observed = {path.relative_to(repo).as_posix(): git_blob(path.read_bytes())
                for path in (repo / "agentos/workstreams").glob("WS-*.md")}
    if observed != expected:
        raise SystemExit("exact current workstream universe changed; refresh the census")
    sys.path.insert(0, str(repo))
    from scripts import linear_portfolio_plan as projects
    from scripts import linear_initiative_plan as initiatives

    # The incumbent Project compiler validates the complete original store.
    # No filtered universe, mocked store, swallowed schema failure or new classifier.
    project_plan, project_receipt = projects.compile_plan(
        repo / "agentos", programs=projects.agentos._load_programs(),
    )
    assert project_receipt["record_counts"]["workstreams"] == 115
    assert len(project_plan["active_projects"]) + len(project_plan["review_candidates"]) == 97
    expected_failures = [
        {"code": "strategy_unmapped_active_workstream", "workstream_key": row["workstream_key"]}
        for row in census["unmapped_active_or_candidate"]
    ]
    assert len(expected_failures) == 43
    try:
        initiatives.compile_initiative_plan(
            project_plan=project_plan,
            strategy_path=repo / "config/linear_initiative_portfolio.v1.json",
        )
    except initiatives.InitiativePlanError as refusal:
        key = lambda row: json.dumps(row, sort_keys=True)
        assert sorted(refusal.failures, key=key) == sorted(expected_failures, key=key), refusal.failures
    else:
        raise AssertionError("incomplete current Initiative coverage was accepted")
    print(json.dumps({
        "source_revision": sources["revision"],
        "record_counts": project_receipt["record_counts"],
        "project_semantic_hash": project_plan["semantic_hash"],
        "active_or_candidate_workstreams": 97,
        "initiative_refusal": "strategy_unmapped_active_workstream",
        "unmapped_workstreams": [row["workstream_key"] for row in expected_failures],
        "complete_current_classification": False,
        "linear_mutation": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
