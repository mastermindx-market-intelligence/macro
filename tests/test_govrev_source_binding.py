"""Offline source/caller binding checks; no original operation is observed."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest
import yaml

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts/ci"))
import govrev_source_binding as binding
import govrev_publisher_preflight as pre

EVENT = "a" * 40
PERSISTED = "b" * 40
LATER = "c" * 40


def native(workflow=binding.PUBLISHER, source=""):
    return {"GITHUB_REPOSITORY": binding.REPOSITORY, "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": EVENT, "GITHUB_WORKFLOW_REF":
            f"{binding.REPOSITORY}/.github/workflows/{workflow}@refs/heads/main",
            "GOVREV_CALL_SOURCE_SHA": source}


def test_direct_event_binds_native_sha():
    assert binding.check_checkout(native(), EVENT)["kind"] == "native_event"
    with pytest.raises(binding.BindingRefused):
        binding.check_checkout(native(), LATER)
    with pytest.raises(binding.BindingRefused):
        binding.select_source(native(source=PERSISTED))


@pytest.mark.parametrize("caller", sorted(binding.CALLERS))
@pytest.mark.parametrize("event_name", ["push", "schedule"])
def test_caller_uses_settled_advanced_commit_instead_of_initial_event(caller, event_name):
    env = native(caller, PERSISTED)
    env["GITHUB_EVENT_NAME"] = event_name
    assert binding.check_checkout(env, PERSISTED)["source_sha"] == PERSISTED
    with pytest.raises(binding.BindingRefused, match="checkout_source_mismatch"):
        binding.check_checkout(env, EVENT)


@pytest.mark.parametrize("source", ["", "main", "refs/heads/main", "a" * 39, "A" * 40,
                                    "a" * 41, "a" * 40 + "\n", "$(id)", None])
def test_missing_malformed_caller_source_never_falls_back(source):
    with pytest.raises(binding.BindingRefused):
        binding.select_source(native("daily.yml", source))


@pytest.mark.parametrize("key,value", [
    ("GITHUB_REPOSITORY", "other/repo"), ("GITHUB_REF", "refs/heads/feature"),
    ("GITHUB_SHA", "main"), ("GITHUB_WORKFLOW_REF", "unknown"),
    ("GITHUB_WORKFLOW_REF", f"{binding.REPOSITORY}/.github/workflows/daily.yml@refs/heads/feature"),
])
def test_native_caller_provenance_required(key, value):
    env = native("daily.yml", PERSISTED)
    env[key] = value
    with pytest.raises(binding.BindingRefused):
        binding.select_source(env)


def fms_receipt():
    return {"contract": "fms.acquisition_persistence.v1", "state": "ORIGINAL_EFFECT_CONFIRMED",
            "target_ref": "refs/heads/main", "candidate": EVENT,
            "attempts": [{"state": "acknowledged", "expected_commit": PERSISTED,
                          "observed_commit": LATER}]}


def test_fms_uses_confirmed_candidate_not_original_checkout_or_later_descendant():
    receipt = fms_receipt()
    assert binding.settled_fms_source(receipt) == PERSISTED
    receipt["attempts"][-1]["state"] = "effect_unknown"
    # An uncertain push reply may be settled by the incumbent same-run observer.
    assert binding.settled_fms_source(receipt) == PERSISTED


@pytest.mark.parametrize("state", ["EFFECT_UNKNOWN", "REFUSED", "PREPARED_NO_PUSH",
                                    "PREPARATION_REFUSED_NO_NEW_PUSH", "DEFINITE_CONTENTION_BUDGET_EXHAUSTED"])
def test_unsettled_fms_receipt_cannot_emit_binding(tmp_path, state):
    receipt = fms_receipt()
    receipt["state"] = state
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt))
    output = tmp_path / "output"
    result = subprocess.run([sys.executable, str(BASE / "scripts/ci/govrev_source_binding.py"),
                             "--fms-receipt", str(path)],
                            env={**os.environ, "GITHUB_OUTPUT": str(output)}, capture_output=True)
    assert result.returncode == 75
    assert not output.exists()


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(attempts=[]), lambda r: r.update(target_ref="refs/heads/feature"),
    lambda r: r["attempts"][-1].update(expected_commit="main"),
    lambda r: r["attempts"][-1].pop("observed_commit"),
    lambda r: r["attempts"][-1].update(state="refused"),
])
def test_invalid_fms_confirmation_refuses(mutate):
    receipt = fms_receipt()
    mutate(receipt)
    with pytest.raises(binding.BindingRefused):
        binding.settled_fms_source(receipt)


@pytest.mark.parametrize("source,actual,accepted", [
    ("", EVENT, True), ("", LATER, False),
    (PERSISTED, PERSISTED, True), (PERSISTED, EVENT, False), ("main", EVENT, False),
])
def test_native_main_binding_precedes_baseline_API_and_history(tmp_path, monkeypatch, source, actual, accepted):
    env = native("daily.yml", source) if source else native()
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("GITHUB_RUN_ID", "10")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-unused")
    monkeypatch.setattr(pre.proof, "_head_commit", lambda root: actual)
    monkeypatch.setattr(pre, "source_closure", lambda root: {})
    calls = []

    def baseline(root):
        calls.append("baseline")
        raise pre.Refused("synthetic_baseline_stop")

    def forbidden(*args, **kwargs):
        pytest.fail("API/history must not be reached")

    monkeypatch.setattr(pre, "read_baseline", baseline)
    monkeypatch.setattr(pre.GitHub, "json", forbidden)
    monkeypatch.setattr(pre.GitHub, "archive", forbidden)
    monkeypatch.setattr(pre, "preflight", forbidden)
    out = tmp_path / "out"
    assert pre.main(["--root", str(tmp_path / "root"), "--out-dir", str(out)]) == 75
    case = json.loads((out / pre.CASE).read_text())
    assert calls == (["baseline"] if accepted else [])
    assert (case["reason"] == "synthetic_baseline_stop") == accepted
    assert case["phase"] == "preflight_refused_before_effect"
    assert not (out / pre.CHECKPOINT).exists()


def load_workflow(name):
    return yaml.load((BASE / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def test_workflow_contract_no_floating_main_or_shell_input_interpolation():
    workflow = load_workflow(binding.PUBLISHER)
    assert workflow["on"]["workflow_call"]["inputs"]["source_sha"]["required"] == "true"
    steps = workflow["jobs"]["refresh"]["steps"]
    assert steps[0]["with"]["ref"] == "${{ github.sha }}"
    assert steps[1]["id"] == "source_binding"
    assert steps[2]["with"]["ref"] == "${{ steps.source_binding.outputs.source_sha }}"
    assert steps[3]["name"] == pre.STEP_NAME
    for step in (steps[1], steps[3]):
        assert step["env"]["GOVREV_CALL_SOURCE_SHA"] == "${{ inputs.source_sha }}"
        assert "${{ inputs." not in step["run"]
    daily = load_workflow("daily.yml")["jobs"]
    assert daily["government_revenue_projection"]["with"]["source_sha"] == "${{ needs.collect.outputs.government_revenue_source_sha }}"
    assert daily["collect"]["outputs"]["government_revenue_source_sha"] == "${{ steps.pushdata.outputs.source_sha }}"
    fms = load_workflow("fms-acquire.yml")["jobs"]
    assert fms["publish"]["with"]["source_sha"] == "${{ needs.acquire.outputs.source_sha }}"
    persist = next(s["run"] for s in fms["acquire"]["steps"] if s.get("id") == "persist")
    assert persist.index("python -B -m scripts.ci.fms_persist") < persist.index("--fms-receipt") < persist.index('echo "publish_default=true"')
    assert "scripts/ci/govrev_source_binding.py" in pre.SOURCE_PATHS


@pytest.mark.parametrize("push_ok,drift", [(True, False), (True, True), (False, False)])
def test_actual_daily_success_branch_emits_only_the_pushed_unchanged_commit(tmp_path, push_ok, drift):
    steps = load_workflow("daily.yml")["jobs"]["collect"]["steps"]
    run = next(s["run"] for s in steps if s.get("id") == "pushdata")
    start = run.index("GOVREV_PUSH_SOURCE_SHA=")
    end = run.index("\n    fi", start) + len("\n    fi")
    block = run[start:end]
    output = tmp_path / "output"
    # This runs only the real branch excerpt with shell-only fakes, no Git calls.
    script = f'''set -eu
counter=0
git() {{ counter=$((counter+1)); if [ -e "$GITHUB_OUTPUT.seen" ] && [ "{str(drift).lower()}" = true ]; then echo {LATER}; else touch "$GITHUB_OUTPUT.seen"; echo {PERSISTED}; fi; }}
push_do() {{ {"return 0" if push_ok else "return 1"}; }}
push_won() {{ :; }}
{block}
'''
    result = subprocess.run(["bash", "-c", script], env={**os.environ, "GITHUB_OUTPUT": str(output),
                            "PUSH_ATTEMPT": "1"}, capture_output=True)
    text = output.read_text() if output.exists() else ""
    if push_ok and not drift:
        assert result.returncode == 0
        assert f"source_sha={PERSISTED}\n" in text and "published=true\n" in text
    else:
        assert "source_sha=" not in text and "published=true" not in text
        assert result.returncode == (75 if drift else 0)
