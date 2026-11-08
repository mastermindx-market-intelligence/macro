"""Retirement guard: no workflow may publish the GitHub Pages mirror.

mastermindx-market-intelligence/macro is going PRIVATE (DEC:B1-MACRO-PRIVATE-CUTOVER).
The GitHub Pages mirror (mastermindx-market-intelligence.github.io/macro) served the
full site tree — including the premium Prophet plan book + premiumdata — anonymously,
independent of the repo's visibility toggle. Wave D retired every Pages PRODUCER step
(`actions/upload-pages-artifact`, `actions/deploy-pages`) from daily.yml, weekly.yml,
closing-bell.yml, and pages.yml so no future run can re-publish that mirror.

This is a pin, not a one-time sweep: it fails CI the moment either action reappears in
any workflow file, in a real (non-comment) `uses:` step.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"

RETIRED_ACTIONS = ("actions/upload-pages-artifact", "actions/deploy-pages")


def _all_uses_values() -> dict[str, list[str]]:
    """{workflow filename: [every `uses:` value found in any job's steps]}."""
    out: dict[str, list[str]] = {}
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        uses_values: list[str] = []
        for job in (doc.get("jobs") or {}).values():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps") or []:
                if isinstance(step, dict) and "uses" in step:
                    uses_values.append(str(step["uses"]))
        out[path.name] = uses_values
    return out


def test_every_workflow_yaml_parses():
    # A parse failure here would silently blind the rest of this guard.
    found = list(WORKFLOWS_DIR.glob("*.yml"))
    assert found, "no workflow files found — has .github/workflows/ moved?"
    for path in found:
        yaml.safe_load(path.read_text(encoding="utf-8"))


def test_no_workflow_step_uses_a_retired_pages_action():
    """Parses each workflow's real step graph (not a text grep) so a comment
    merely mentioning the action name can never trip or hide this guard."""
    offenders = []
    for wf, uses_values in _all_uses_values().items():
        for uses in uses_values:
            for retired in RETIRED_ACTIONS:
                if uses.startswith(retired):
                    offenders.append(f"{wf}: uses {uses!r}")
    assert not offenders, (
        "GitHub Pages producer re-introduced — retired pre-private-cutover "
        "(DEC:B1-MACRO-PRIVATE-CUTOVER):\n" + "\n".join(offenders)
    )


def test_pages_workflow_is_retired_or_absent():
    """pages.yml was the manual-only Pages mirror redeploy button. It is either
    deleted outright, or reduced to a workflow_dispatch no-op — never a live
    Pages deploy again."""
    path = WORKFLOWS_DIR / "pages.yml"
    if not path.exists():
        return
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for job in (doc.get("jobs") or {}).values():
        assert isinstance(job, dict)
        for step in job.get("steps") or []:
            if isinstance(step, dict) and "uses" in step:
                uses = str(step["uses"])
                assert not any(uses.startswith(r) for r in RETIRED_ACTIONS), (
                    f"pages.yml still deploys via {uses!r}"
                )


def test_vps_main_sync_wake_is_main_only_and_least_privilege():
    """A hosted wake must not turn PR source into an SSH deployment permission."""
    path = WORKFLOWS_DIR / "vps-main-sync-wake.yml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"push", "workflow_dispatch"}
    assert triggers["workflow_dispatch"] == {}
    assert triggers["push"]["branches"] == ["main"]
    paths = triggers["push"]["paths"]
    assert "site/**" in paths and "templates/**" in paths
    assert "app/**" in paths and "admin/**" in paths
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert list(workflow["jobs"]) == ["wake"]
    job = workflow["jobs"]["wake"]
    assert "github.repository == 'mastermindx-market-intelligence/macro'" in job["if"]
    assert "github.ref == 'refs/heads/main'" in job["if"]
    assert "continue-on-error" not in path.read_text(encoding="utf-8")


def test_vps_main_sync_wake_reuses_pinned_host_and_locked_updater_only():
    """Wake existing VPS publisher, never create another writer/checkout/rsync."""
    path = WORKFLOWS_DIR / "vps-main-sync-wake.yml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["wake"]["steps"]
    assert len(steps) == 2
    checkout = steps[0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"]["sparse-checkout"] == "app/deploy/ohlc_origin_known_hosts"
    assert checkout["with"]["persist-credentials"] is False
    command = steps[1]["run"]
    assert steps[1]["env"] == {"VPS_DEPLOY_KEY": "${{ secrets.VPS_DEPLOY_KEY }}"}
    assert command.count("root@146.190.142.17") == 1
    assert "StrictHostKeyChecking=yes" in command
    assert 'UserKnownHostsFile="$HOST_PIN"' in command
    assert "ssh-keyscan" not in command and "accept-new" not in command
    assert "/usr/local/bin/macro-update" in command
    assert "/var/log/macro-update.log" in command
    assert "git -C /opt/macro rev-parse --verify HEAD" in command
    executable = "\n".join(line for line in command.splitlines()
                           if not line.lstrip().startswith("#"))
    assert "git reset" not in executable and "rsync " not in executable
    assert "git push" not in command and "gh pr merge" not in command
    assert "workflow_dispatch" not in command
    assert "|| true" not in command
    pin = (ROOT / "app" / "deploy" / "ohlc_origin_known_hosts").read_text()
    assert pin == "146.190.142.17 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEc8ibhWOj35RC4FXjydG27GMxKfjiVXOw0s7hiCySkk\n"
    assert "grep -qx '146.190.142.17 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEc8ibhWOj35RC4FXjydG27GMxKfjiVXOw0s7hiCySkk'" in command
