"""R16 + live preflight for the ``vars.MACRO_DATA_LANE`` runs-on switch.

The switch re-points ~66 scheduled data jobs at once and its VALUE lives in
GitHub settings, so R11 only ever sees the quoted fallback. These tests pin the
two halves of the guard: the static SHAPE (R16, check_runner_policy.py) and the
live VALUE (data-lane preflight, check_runner_queue_hostage.py).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from tests.test_runner_policy import fixture_tree, run_guard

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
HOSTAGE = ROOT / "scripts" / "check_runner_queue_hostage.py"
LIVENESS = WORKFLOWS / "nightly-liveness.yml"


def _write_job(workflows: Path, runs_on: str) -> None:
    (workflows / "zz-data-lane.yml").write_text(
        "name: zz\non:\n  workflow_dispatch:\njobs:\n  lane:\n"
        f"    runs-on: {runs_on}\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )


def _r16(tmp_path: Path, runs_on: str) -> list[str]:
    root, registry, workflows = fixture_tree(tmp_path)
    _write_job(workflows, runs_on)
    result = run_guard(root, registry, workflows)
    return [line for line in result.stdout.splitlines() if "runner-policy-R16" in line]


@pytest.mark.parametrize(
    "runs_on",
    [
        """[self-hosted, "${{ vars.MACRO_DATA_LANE || 'macstudio' }}"]""",
        """[self-hosted, "${{ vars.MACRO_DATA_LANE || 'macstudio-light' }}"]""",
        """[self-hosted, "${{vars.MACRO_DATA_LANE||'macstudio'}}"]""",
    ],
)
def test_valid_switch_forms_pass(tmp_path: Path, runs_on: str) -> None:
    assert _r16(tmp_path, runs_on) == []


@pytest.mark.parametrize(
    ("runs_on", "needle"),
    [
        # mutant: typo'd fallback label
        ("""[self-hosted, "${{ vars.MACRO_DATA_LANE || 'macstudo' }}"]""", "fallback"),
        # mutant: fallback outside the registered pair (live label, wrong lane)
        ("""[self-hosted, "${{ vars.MACRO_DATA_LANE || 'render-heavy' }}"]""", "fallback"),
        # mutant: unknown repository variable in runs-on
        ("""[self-hosted, "${{ vars.MACRO_DATA_LANES || 'macstudio' }}"]""", "allowlist"),
        ("""[self-hosted, "${{ vars.RUNNER_LABEL || 'macstudio' }}"]""", "allowlist"),
        # mutant: bracket access dodges the dotted-name parse
        ("""[self-hosted, "${{ vars['MACRO_DATA_LANE'] || 'macstudio' }}"]""", "allowlist"),
        # mutant: no fallback -> unset variable yields an empty label
        ("""[self-hosted, "${{ vars.MACRO_DATA_LANE }}"]""", "exact form"),
        # mutant: && / ternary shapes
        ("""[self-hosted, "${{ vars.MACRO_DATA_LANE && 'macstudio' || 'macstudio-light' }}"]""", "exact form"),
        # mutant: dropped self-hosted / extra label / bare string
        ("""["${{ vars.MACRO_DATA_LANE || 'macstudio' }}"]""", "exactly"),
        ("""[self-hosted, Linux, "${{ vars.MACRO_DATA_LANE || 'macstudio' }}"]""", "exactly"),
        (""""${{ vars.MACRO_DATA_LANE || 'macstudio' }}\"""", "exactly"),
        # mutant: a previously-legit if: variable smuggled into runs-on
        ("""[self-hosted, "${{ vars.CI_EXECUTION_ROUTE || 'macstudio' }}"]""", "allowlist"),
    ],
)
def test_mutant_switch_forms_are_refused(tmp_path: Path, runs_on: str, needle: str) -> None:
    lines = _r16(tmp_path, runs_on)
    assert lines, f"R16 missed mutant {runs_on}"
    assert any(needle in line for line in lines), lines


def test_if_level_lane_variables_keep_working(tmp_path: Path) -> None:
    """CI_EXECUTION_ROUTE / AD1_M1_LANE select lanes via job ``if:``; R16 must not
    look there. The live tree carries both and must stay green."""
    root, registry, workflows = fixture_tree(tmp_path)
    (workflows / "zz-if.yml").write_text(
        "name: zz\non:\n  workflow_dispatch:\njobs:\n  lane:\n"
        "    if: vars.AD1_M1_LANE == 'on' && vars.CI_EXECUTION_ROUTE != 'pc'\n"
        "    runs-on: [self-hosted, macstudio]\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    result = run_guard(root, registry, workflows)
    assert "runner-policy-R16" not in result.stdout


def test_every_live_switch_is_the_exact_form() -> None:
    """The real tree: every MACRO_DATA_LANE consumer is a registered-fallback switch."""
    seen = 0
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for job in (document.get("jobs") or {}).values():
            runs_on = job.get("runs-on") if isinstance(job, dict) else None
            if "MACRO_DATA_LANE" in str(runs_on):
                seen += 1
                assert isinstance(runs_on, list) and runs_on[0] == "self-hosted", path
                assert runs_on[1] in (
                    "${{ vars.MACRO_DATA_LANE || 'macstudio' }}",
                    "${{ vars.MACRO_DATA_LANE || 'macstudio-light' }}",
                ), (path, runs_on)
    assert seen >= 60, seen


# ── live preflight ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hostage():
    spec = importlib.util.spec_from_file_location("check_runner_queue_hostage_dl", HOSTAGE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VIEW = {
    "macstudio": {"status": "live", "carried_by": ["host-a"]},
    "macstudio-light": {"status": "live", "carried_by": ["host-b"]},
    "data-linux": {"status": "orphaned", "carried_by": []},
}


@pytest.mark.parametrize(
    ("value", "online", "want"),
    [
        (None, None, "ok"),
        ("  ", None, "ok"),
        ("macstudio", None, "ok"),
        ("macstudio", {"self-hosted", "macstudio"}, "ok"),
        ("data-linx", None, "breach"),            # typo'd value
        ("data-linux", None, "breach"),           # set before a carrier exists
        ("data-linux", {"data-linux"}, "breach"), # registry not flipped yet
        ("macstudio-light", {"macstudio"}, "breach"),  # live in registry, offline now
    ],
)
def test_data_lane_preflight_verdicts(hostage, value, online, want) -> None:
    assert hostage.evaluate_data_lane(value, VIEW, online)["verdict"] == want


def test_data_lane_preflight_blind_registry_is_indeterminate(hostage) -> None:
    assert hostage.evaluate_data_lane("data-linux", {}, None)["verdict"] == "indeterminate"
    assert hostage.evaluate_data_lane("data-linux", None, None)["verdict"] == "indeterminate"


def test_data_lane_preflight_fails_the_cli(hostage, monkeypatch, capsys) -> None:
    monkeypatch.setenv("MACRO_DATA_LANE", "data-linx")
    monkeypatch.delenv("RUNNER_LIST_TOKEN", raising=False)
    monkeypatch.setattr(hostage, "_notify", lambda report: None)
    assert hostage.check_data_lane() == 1
    assert "data-lane-preflight" in capsys.readouterr().out
    monkeypatch.setenv("MACRO_DATA_LANE", "")
    assert hostage.check_data_lane() == 0


def test_fetch_online_labels_counts_online_runners_only(hostage, monkeypatch) -> None:
    payload = {"runners": [
        {"status": "online", "labels": [{"name": "self-hosted"}, {"name": "macstudio"}]},
        {"status": "offline", "labels": [{"name": "data-linux"}]},
    ]}
    monkeypatch.setattr(hostage, "_get", lambda url, token, what: payload)
    assert hostage.fetch_online_labels("o/r", "t") == {"self-hosted", "macstudio"}
    assert hostage.fetch_online_labels("o/r", None) is None


def test_liveness_lane_passes_the_variable_in() -> None:
    document = yaml.safe_load(LIVENESS.read_text(encoding="utf-8"))
    step = next(
        s for s in document["jobs"]["queue-hostage"]["steps"]
        if "check_runner_queue_hostage.py" in str(s.get("run", ""))
    )
    assert step["env"]["MACRO_DATA_LANE"] == "${{ vars.MACRO_DATA_LANE }}"
