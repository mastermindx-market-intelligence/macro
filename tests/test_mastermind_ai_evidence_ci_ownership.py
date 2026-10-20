"""R10: source-bound evidence suites must execute in the pre-merge code gate."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts import run_ci_pack as ci_pack


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"


@pytest.mark.parametrize(
    ("suite", "expected_owner"),
    (
        ("tests/test_brain_research_evidence.py", "unrun-brain-gateway"),
        ("tests/test_research_evidence_passages.py", "research-vault-api"),
        (
            "tests/test_mastermind_ai_evidence_ci_ownership.py",
            "unrun-brain-gateway",
        ),
    ),
)
def test_source_bound_evidence_suites_are_premerge_code_gated(
    suite: str,
    expected_owner: str,
) -> None:
    jobs = (yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}).get("jobs") or {}
    code_job_ids = {
        job.job_id for job in ci_pack.load_legacy_jobs(MANIFEST, gate="code")
    }
    assert expected_owner in code_job_ids, (
        f"{expected_owner!r} is not selected by the real pre-merge "
        f"load_legacy_jobs(..., gate='code') path"
    )

    receipts: list[tuple[str, object]] = []
    for job_id, definition in jobs.items():
        if not isinstance(definition, dict):
            continue
        for step in definition.get("steps") or ():
            if isinstance(step, dict) and suite in str(step.get("run") or ""):
                receipts.append((str(job_id), definition.get("gate")))

    assert receipts == [(expected_owner, "code")], (
        f"{suite} must have exactly one pre-merge gate:code owner "
        f"{expected_owner!r}; actual receipts={receipts!r}"
    )
