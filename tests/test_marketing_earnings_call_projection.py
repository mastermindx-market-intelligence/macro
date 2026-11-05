"""Runtime wiring tests for Chronicle earnings-call -> Marketing outbox."""
from __future__ import annotations

import re
from pathlib import Path

from scripts import marketing_earnings_call_projection as runner


ROOT = Path(__file__).resolve().parents[1]


def _healthy() -> dict:
    return {
        "input_rows": 4,
        "eligible_rows": 1,
        "stale_rows": 3,
        "capped_rows": 0,
        "gap": None,
        "integrity_blocked": False,
        "results": [{"event_id": "evt-1", "status": "queued", "reason": "", "item": {}}],
        "queued": 1,
        "dry_run": 0,
        "duplicates": 0,
        "corrections_required": 0,
    }


def test_runner_passes_real_marketing_config_and_tracked_outbox(
    tmp_path: Path, monkeypatch,
):
    cfg = tmp_path / "config" / "marketing.yml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        """
wire_routing:
  default: flagship
  classes:
    earnings: mastermind_news
publish:
  require_approval: true
""".lstrip(),
        encoding="utf-8",
    )

    seen = {}

    def fake_run_ledger(**kwargs):
        seen.update(kwargs)
        return _healthy()

    monkeypatch.setattr(runner.lane, "run_ledger", fake_run_ledger)
    result, code = runner.run(
        root=tmp_path,
        dry_run=False,
        max_call_age_days=2,
        max_events=8,
    )

    assert code == 0
    assert result["queued"] == 1
    assert seen["cfg"]["wire_routing"]["classes"]["earnings"] == "mastermind_news"
    assert seen["cfg"]["publish"]["require_approval"] is True
    assert seen["spool"] is False
    assert seen["dry_run"] is False
    assert seen["max_call_age_days"] == 2
    assert seen["max_events"] == 8



def test_runner_refuses_missing_operator_earnings_route(
    tmp_path: Path, monkeypatch, capsys,
):
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "marketing.yml").write_text("{}\n", encoding="utf-8")

    def must_not_run(**_kwargs):
        raise AssertionError("projection ran after routing config failed closed")

    monkeypatch.setattr(runner.lane, "run_ledger", must_not_run)
    result, code = runner.run(
        root=tmp_path,
        dry_run=False,
        max_call_age_days=2,
        max_events=8,
    )

    output = capsys.readouterr().out
    assert code == 2
    assert result["config_blocked"] is True
    assert "::error title=earnings-call-marketing-config-invalid::" in output
    assert "wire_routing.classes.earnings is required" in output

def test_runner_fails_job_on_committed_ledger_integrity_gap(
    tmp_path: Path, monkeypatch, capsys,
):
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "marketing.yml").write_text(
        "wire_routing:\n  classes:\n    earnings: mastermind_news\n",
        encoding="utf-8",
    )

    blocked = _healthy()
    blocked.update(
        {
            "eligible_rows": 0,
            "gap": "duplicate id in committed ledger",
            "integrity_blocked": True,
            "results": [],
            "queued": 0,
        }
    )
    monkeypatch.setattr(runner.lane, "run_ledger", lambda **_kwargs: blocked)

    _result, code = runner.run(
        root=tmp_path,
        dry_run=False,
        max_call_age_days=2,
        max_events=8,
    )

    output = capsys.readouterr().out
    assert code == 2
    assert "::error title=earnings-call-ledger-integrity::" in output
    assert "duplicate id in committed ledger" in output


def test_correction_is_visible_but_does_not_abort_other_safe_rows(
    tmp_path: Path, monkeypatch, capsys,
):
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "marketing.yml").write_text(
        "wire_routing:\n  classes:\n    earnings: mastermind_news\n",
        encoding="utf-8",
    )
    result = _healthy()
    result["results"] = [
        {"event_id": "evt-safe", "status": "queued", "reason": "", "item": {}},
        {
            "event_id": "evt-corrected",
            "status": "correction_required",
            "reason": "prior_revision_requires_explicit_supersede",
            "prior_item_id": "old-item",
            "prior_status": "queued",
            "item": None,
        },
    ]
    result["corrections_required"] = 1
    monkeypatch.setattr(runner.lane, "run_ledger", lambda **_kwargs: result)

    _result, code = runner.run(
        root=tmp_path,
        dry_run=False,
        max_call_age_days=2,
        max_events=8,
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "::warning title=earnings-call-correction-held::" in output
    assert "evt-corrected" in output


def test_existing_earnings_workflow_runs_projection_without_arming_public_send():
    workflow = (ROOT / ".github/workflows/marketing-earnings-wire.yml").read_text(
        encoding="utf-8"
    )

    assert "data/chronicle" in workflow
    assert "python -m scripts.marketing_earnings_call_projection" in workflow
    assert workflow.index("project Chronicle earnings-call events") < workflow.index(
        "commit queued earnings posts"
    )

    # Comments may explain the independent send switch. The workflow itself must
    # not assign it: queuing CEI material cannot silently become publication.
    active_lines = [
        line for line in workflow.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert not any(
        re.match(r"\s*MARKETING_PUBLISH_ENABLED\s*:", line)
        for line in active_lines
    )


def test_workflow_carries_the_existing_r2_host_credentials_for_call_cards():
    workflow = (ROOT / ".github/workflows/marketing-earnings-wire.yml").read_text(
        encoding="utf-8"
    )
    step = workflow.split("- name: project Chronicle earnings-call events", 1)[1]
    step = step.split("- name: commit queued earnings posts", 1)[0]

    for key in (
        "R2_ENDPOINT",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
    ):
        assert f"{key}:" in step
