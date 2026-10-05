from __future__ import annotations

from scripts import portfolio_decision_deadman as deadman


def test_future_shallow_release_is_accepted_by_deployed_repair_contract(tmp_path, monkeypatch) -> None:
    (tmp_path / "brain").mkdir()
    (tmp_path / "app").mkdir()
    (tmp_path / "brain/provider_waterfall.py").write_text(
        'if "access token could not be refreshed" in msg:\n    return "auth"\n',
        encoding="utf-8",
    )
    (tmp_path / "app/scheduler.py").write_text(
        'def _brain_job_outcome(result):\n'
        '    if target == "rejected_no_submission":\n'
        '        return "error", "FREEZE", {"reason": "missing_submission"}\n'
        '    finished_extra.get("target_status")\n'
        '_brain_job_outcome(_result)\n',
        encoding="utf-8",
    )

    class NoHistory:
        returncode = 1

    monkeypatch.setattr(deadman, "DEPLOY_ROOT", tmp_path)
    monkeypatch.setattr(deadman.subprocess, "run", lambda *args, **kwargs: NoHistory())
    assert deadman._release_contains_fix("f" * 40) is True
