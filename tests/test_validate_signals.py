"""Tests for the signal→chart contract gate (scripts/validate_signals.py + SCHEMA.json).

A valid fixture passes clean; each invalid fixture (missing ticker, quality on a 'sell',
non-date 'date', unsorted markers, plus the brain-leaf shape) must produce at least one
error. The real SCHEMA.json is loaded — these tests double as a guard that the schema and
the validator agree on the §7 contract.
"""
from __future__ import annotations

import ast
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
import yaml

from scripts import validate_signals as vs


SCHEMA = vs.load_schema()


# ---- valid fixtures -------------------------------------------------------

def _valid_ticker() -> dict:
    return {
        "ticker": "AAPL", "asof": "2026-06-18", "tf": "3D",
        "state": "long-bias", "above200": True, "weekly_bull": False,
        "trail_stop": 187.42, "trail_breach": False,
        "risk_flags": ["2025-08-20", "2026-02-04"],
        "early_markers": ["2025-07-09", "2026-03-05"], "early_now": False,
        "markers": [
            {"date": "2025-07-16", "type": "buy", "quality": "take", "reason": "held confirmation"},
            {"date": "2025-09-30", "type": "sell"},
            {"date": "2026-01-16", "type": "cut"},
            {"date": "2026-03-12", "type": "rebuy", "quality": "block", "reason": "counter-trend, no reclaim"},
            {"date": "2026-06-16", "type": "buy", "quality": "pending", "reason": "pending confirmation"},
        ],
    }


def _valid_leaf() -> dict:
    return {
        "asof": "2026-06-16", "tf": "3D", "universe": "us_deep",
        "note": "entry-quality RISK signal (display-only, NOT alpha)",
        "signals": [
            {"ticker": "AAPL", "asof": "2026-06-18", "state": "short-bias",
             "above200": True, "weekly_bull": True, "trail_stop": 187.42, "trail_breach": False,
             "early_now": False, "last": {"date": "2026-06-10", "type": "sell"}},
            {"ticker": "BA", "asof": "2026-06-16", "state": "long-bias",
             "above200": True, "weekly_bull": False, "trail_stop": None, "trail_breach": False,
             "early_now": True,
             "last": {"date": "2026-06-16", "type": "buy", "quality": "pending", "reason": "pending confirmation"}},
            {"ticker": "XYZ", "asof": "2026-06-16", "state": "mixed",
             "above200": False, "weekly_bull": False, "trail_stop": 12.5, "trail_breach": True,
             "early_now": False, "last": None},
        ],
    }


def test_valid_ticker_passes():
    assert vs.validate_ticker_doc(_valid_ticker(), SCHEMA, "fix") == []


def test_valid_leaf_passes():
    assert vs.validate_brain_leaf(_valid_leaf(), SCHEMA, "fix") == []


def test_pending_quality_is_accepted():
    # `pending` is a real third quality value the engine emits — the schema MUST allow it.
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2026-06-16", "type": "buy", "quality": "pending", "reason": "x"}]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix") == []


def test_pit_disclosure_is_accepted():
    # RC-R2 (engine/marker_integrity.py) appends a `pit` drift-disclosure dict to
    # every per-ticker file. The 2026-07-12 nightlies failed the §7 gate wholesale
    # (226/226 files) because the schema lagged the writer — pit MUST validate.
    doc = _valid_ticker()
    doc["pit"] = {
        "kept_frozen": 3906, "refined": 0, "appended": 0, "drift_lost": 0,
        "drift_deep_new": 0, "relabel_blocked": 0, "prev_asof": "2026-07-09",
        "last_night": {"kept_frozen": 279, "refined": 0, "appended": 0,
                       "drift_lost": 0, "drift_deep_new": 0, "relabel_blocked": 0},
    }
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix") == []


def test_pit_first_write_null_prev_asof_accepted():
    # First-ever write has no prior vintage: merge_payload sets prev_asof=None.
    doc = _valid_ticker()
    doc["pit"] = {"kept_frozen": 0, "prev_asof": None, "last_night": {}}
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix") == []


def test_engine_analyze_output_conforms_to_schema():
    """The live engine's analyze() output MUST validate against the schema.

    This is the key anti-drift test: a change to engine/signal_quality.py that adds, renames, or
    re-types a field without updating SCHEMA.json would make additionalProperties:false reject the
    output here — failing the test BEFORE it can ship. Uses a deterministic synthetic series (no
    RNG) so it is stable across runs and needs no data fixtures.
    """
    import numpy as np
    import pandas as pd
    from engine.signal_quality import analyze

    idx = pd.bdate_range("2019-01-01", periods=900)
    t = np.arange(len(idx), dtype=float)
    close = pd.Series(100 + 18 * np.sin(t / 33) + 0.015 * t + 4 * np.sin(t / 6), index=idx)
    res = analyze("SYNTH", close)
    assert res is not None, "engine produced no result for a 900-bar series"
    assert vs.validate_ticker_doc(res, SCHEMA, "engine analyze()") == []
    # The brain-leaf entry derived from analyze() (per §7.B) must also conform.
    entry = {k: res[k] for k in ("ticker", "asof", "state", "above200", "weekly_bull",
                                 "trail_breach", "trail_stop", "early_now")}
    entry["last"] = res["markers"][-1] if res["markers"] else None
    leaf = {"asof": res["asof"], "tf": "3D", "universe": "us_deep", "signals": [entry]}
    assert vs.validate_brain_leaf(leaf, SCHEMA, "engine leaf") == []


# ---- invalid fixtures (each must fail) ------------------------------------

def test_missing_ticker_fails():
    doc = _valid_ticker()
    del doc["ticker"]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_quality_on_sell_fails():
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2025-09-30", "type": "sell", "quality": "take"}]
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("quality" in e for e in errs)


def test_quality_on_cut_fails():
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2026-01-16", "type": "cut", "quality": "block"}]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


# ---- `reasons`: the EXHAUSTIVE buy-filter account (2026-08-04) ---------------
# `reason` is a FIRST-MATCH label — the buy filter returns on the first leg that refuses a
# name, so 002155.SZ shipped "veto: bearish divergence" while ALSO failing reclaim-and-hold
# (research/cn_prophet_audit/CN_DIVERGENCE_VETO_AUDIT.md). `reasons` names every failing leg.

def _over_determined_marker() -> dict:
    return {"date": "2026-06-17", "type": "buy", "quality": "block",
            "reason": "veto: bearish divergence",
            "reasons": ["veto: bearish divergence", "failed next-bar hold"]}


def test_exhaustive_reasons_on_a_buy_is_accepted():
    doc = _valid_ticker()
    doc["markers"] = [_over_determined_marker()]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix") == []


def test_single_element_reasons_fails():
    # A one-element list says exactly what `reason` already said. The writer omits it, so its
    # ABSENCE means [reason] — a lone element would make that fallback ambiguous.
    doc = _valid_ticker()
    m = _over_determined_marker()
    m["reasons"] = ["veto: bearish divergence"]
    doc["markers"] = [m]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_reasons_on_sell_fails():
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2025-09-30", "type": "sell",
                       "reasons": ["a", "b"]}]
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("reasons" in e for e in errs)


def test_reasons_not_opening_on_the_markers_own_reason_fails():
    # Rule 3. Every downstream reader falls back to [reason] when `reasons` is absent, which is
    # only sound while reasons[0] IS reason. An account opening on a different leg would ship a
    # gate_reasons whose first element contradicts the gate_reason beside it.
    doc = _valid_ticker()
    m = _over_determined_marker()
    m["reasons"] = ["failed next-bar hold", "veto: bearish divergence"]
    doc["markers"] = [m]
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("reasons[0]" in e for e in errs), errs


def test_reasons_survive_the_brain_leaf_last_marker():
    # `signalEntry.last` reuses the same $def, so the account rides the brain leaf too.
    leaf = _valid_leaf()
    leaf["signals"][0]["last"] = _over_determined_marker()
    assert vs.validate_brain_leaf(leaf, SCHEMA, "fix") == []


def test_non_date_date_fails():
    doc = _valid_ticker()
    doc["markers"] = [{"date": "07/16/2025", "type": "buy", "quality": "take", "reason": "x"}]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_bad_calendar_date_fails():
    # passes the YYYY-MM-DD pattern but is not a real date — must still be rejected.
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2026-13-45", "type": "buy", "quality": "take", "reason": "x"}]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_unsorted_markers_fail():
    doc = _valid_ticker()
    doc["markers"] = [
        {"date": "2026-03-12", "type": "sell"},
        {"date": "2025-07-16", "type": "buy", "quality": "take", "reason": "x"},
    ]
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("ascending" in e or "after" in e for e in errs)


def test_duplicate_date_markers_fail():
    # strict ascending — two markers on the same bar date is a contract violation.
    doc = _valid_ticker()
    doc["markers"] = [
        {"date": "2025-07-16", "type": "buy", "quality": "take", "reason": "x"},
        {"date": "2025-07-16", "type": "sell"},
    ]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_bad_state_fails():
    doc = _valid_ticker()
    doc["state"] = "bullish"  # not in [long-bias, short-bias, mixed]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_unknown_marker_type_fails():
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2025-07-16", "type": "scale-in"}]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_extra_field_fails():
    # additionalProperties:false — a stray/typo'd field is exactly the drift we want to catch.
    doc = _valid_ticker()
    doc["confidence"] = 0.9
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_leaf_missing_signals_fails():
    leaf = _valid_leaf()
    del leaf["signals"]
    assert vs.validate_brain_leaf(leaf, SCHEMA, "fix")


def test_leaf_quality_on_sell_last_fails():
    leaf = _valid_leaf()
    leaf["signals"][0]["last"] = {"date": "2026-06-10", "type": "sell", "quality": "take"}
    errs = vs.validate_brain_leaf(leaf, SCHEMA, "fix")
    assert errs
    assert any("quality" in e for e in errs)


# ---- new rules: trail layer + cross-shape consistency ---------------------

def test_buy_without_quality_fails():
    # the chart needs quality on every buy/rebuy — a bare buy is a drift the gate must catch.
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2025-07-16", "type": "buy"}]
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("quality" in e and "missing" in e for e in errs)


def test_rebuy_without_quality_fails():
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2025-07-16", "type": "rebuy"}]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_reason_on_sell_fails():
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2025-09-30", "type": "sell", "reason": "should not be here"}]
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("reason" in e for e in errs)


def test_trail_fields_valid_passes():
    # trail_stop/trail_breach/risk_flags are the display-only risk layer — accepted when well-formed.
    assert vs.validate_ticker_doc(_valid_ticker(), SCHEMA, "fix") == []


def test_trail_stop_null_passes():
    doc = _valid_ticker()
    doc["trail_stop"] = None  # null when insufficient history
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix") == []


def test_risk_flags_unsorted_fails():
    doc = _valid_ticker()
    doc["risk_flags"] = ["2026-02-04", "2025-08-20"]  # descending
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("risk_flags" in e and "ascending" in e for e in errs)


def test_risk_flags_bad_date_fails():
    doc = _valid_ticker()
    doc["risk_flags"] = ["2025-08-20", "not-a-date"]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_risk_flag_in_markers_stream_fails():
    # risk_flag must NOT leak into the trade-marker stream (it has its own list).
    doc = _valid_ticker()
    doc["markers"] = [{"date": "2025-07-16", "type": "risk_flag"}]
    assert vs.validate_ticker_doc(doc, SCHEMA, "fix")


def test_early_markers_unsorted_fails():
    # early_markers is the 2D-MACD advance-warning date list — also must be ascending.
    doc = _valid_ticker()
    doc["early_markers"] = ["2026-03-05", "2025-07-09"]  # descending
    errs = vs.validate_ticker_doc(doc, SCHEMA, "fix")
    assert errs
    assert any("early_markers" in e and "ascending" in e for e in errs)


# ---- end-to-end run() over a temp tree ------------------------------------

def _write_tree(tmp_path, leaf):
    """Write one per-ticker file for every leaf ticker so the leaf ⊆ files invariant holds."""
    sigdir = tmp_path / "signals"
    sigdir.mkdir()
    for s in leaf["signals"]:
        doc = _valid_ticker()
        doc["ticker"] = s["ticker"]
        (sigdir / f"{s['ticker']}.json").write_text(json.dumps(doc))
    leaf_path = tmp_path / "leaf.json"
    leaf_path.write_text(json.dumps(leaf))
    return sigdir, leaf_path


def test_run_passes_on_valid_tree(tmp_path):
    leaf = _valid_leaf()
    sigdir, leaf_path = _write_tree(tmp_path, leaf)
    audit = tmp_path / "audit.json"
    rc = vs.run(signals_dir=sigdir, leaf_path=leaf_path, audit_path=audit)
    assert rc == 0
    a = json.loads(audit.read_text())
    assert a["errors"] == []
    assert a["files_checked"] == len(leaf["signals"]) + 1
    assert a["n_markers"] == len(leaf["signals"]) * len(_valid_ticker()["markers"])
    assert a["asof"] == "2026-06-16"


def test_run_fails_and_writes_audit_on_invalid_tree(tmp_path):
    leaf = _valid_leaf()
    sigdir, leaf_path = _write_tree(tmp_path, leaf)
    bad = _valid_ticker()
    bad["ticker"] = "AAPL"
    del bad["ticker"]  # corrupt the AAPL file (missing required field)
    (sigdir / "AAPL.json").write_text(json.dumps(bad))
    audit = tmp_path / "audit.json"
    rc = vs.run(signals_dir=sigdir, leaf_path=leaf_path, audit_path=audit)
    assert rc == 1
    assert json.loads(audit.read_text())["errors"]


def test_run_fails_on_leaf_missing_per_ticker_file(tmp_path):
    # leaf lists a ticker with no per-ticker file -> partial/inconsistent write.
    leaf = _valid_leaf()
    sigdir, leaf_path = _write_tree(tmp_path, leaf)
    (sigdir / "BA.json").unlink()  # drop a file the leaf still claims
    audit = tmp_path / "audit.json"
    rc = vs.run(signals_dir=sigdir, leaf_path=leaf_path, audit_path=audit)
    assert rc == 1
    assert any("BA" in e and "missing" in e for e in json.loads(audit.read_text())["errors"])


def test_run_fails_when_leaf_missing(tmp_path):
    sigdir = tmp_path / "signals"
    sigdir.mkdir()
    (sigdir / "AAPL.json").write_text(json.dumps(_valid_ticker()))
    audit = tmp_path / "audit.json"
    rc = vs.run(signals_dir=sigdir, leaf_path=tmp_path / "nope.json", audit_path=audit)
    assert rc == 1


# ---- workflow publication boundary (MAS-258; synthetic data only) ----------

@lru_cache(maxsize=4)
def _signal_workflow(name):
    root = Path(__file__).resolve().parents[1]
    return yaml.safe_load((root / ".github/workflows" / f"{name}.yml").read_text())


def _signal_steps(name):
    jobs = _signal_workflow(name)["jobs"]
    steps = jobs["engine" if name == "daily" else
                 "closingbell" if name == "closing-bell" else name]["steps"]
    gates = [i for i, step in enumerate(steps)
             if "scripts.build_signal_quality" in step.get("run", "")]
    assert len(gates) == 1
    return steps, gates[0]


_SIGNAL_STUB = r'''
import json, os, pathlib, subprocess, sys
P = pathlib.Path
args = sys.argv[1:]
kind = P(sys.argv[0]).name
with open(os.environ["CALLS"], "a") as stream:
    stream.write(json.dumps([kind, *args]) + "\n")
scenario = os.environ["SCENARIO"]
if kind == "git":
    if args[0] == "rev-parse" and scenario == "ref_failure":
        sys.exit(23)
    if args[0] in {"restore", "checkout"} and scenario in {"restore_leaf", "restore_charts"}:
        # Model a real partial restore: one path changes before the other fails.
        restored = "site/signals/" if scenario == "restore_leaf" else "data/signal_archive/mtf_signals_latest.json"
        split = args.index("--")
        subprocess.run([os.environ["REAL_GIT"], *args[:split + 1], restored], check=True)
        sys.exit(24)
    if args[0] == "clean" and scenario == "cleanup_failure":
        sys.exit(25)
    result = subprocess.run([os.environ["REAL_GIT"], *args])
    if result.returncode == 0 and args[0] == "clean" and scenario == "invalid_fallback":
        P("data/signal_archive/mtf_signals_latest.json").write_text("{}")
    sys.exit(result.returncode)
module = args[1]
if module == "scripts.build_signal_quality":
    doc = json.loads(P("site/signals/AAPL.json").read_text())
    doc["asof"] = "2026-06-19"
    P("site/signals/AAPL.json").write_text(json.dumps(doc))
    # Valid but unaccepted bytes must not be salvaged after a partial build.
    for filename in ("STRAY.json", "ignored-STRAY.json"):
        P("site/signals", filename).write_text(json.dumps(doc))
    if scenario not in {"success", "validator_failure", "engine_failure"}:
        sys.exit(21)
elif module == "scripts.validate_signals":
    count_path = P("validator_count")
    count = int(count_path.read_text()) + 1 if count_path.exists() else 1
    count_path.write_text(str(count))
    if scenario == "validator_failure" and count == 1:
        sys.exit(22)
    sys.path.insert(0, os.environ["PROJECT_ROOT"])
    from scripts import validate_signals as validator
    # Real validator, with every mutable/data path redirected into this fixture.
    sys.exit(validator.run(P("site/signals").resolve(),
                          P("data/signal_archive/mtf_signals_latest.json").resolve(),
                          P("audit.json").resolve()))
elif module == "engine.run":
    sys.exit(26 if scenario == "engine_failure" else 0)
else:
    raise AssertionError("Unexpected producer: " + module)
'''


def _exercise_signal_gate(tmp_path, workflow, scenario="success", *, bad_output=False):
    """Run the actual YAML Bash with an inert builder and isolated real Git/validator."""
    real_git = shutil.which("git")
    assert real_git, "git is required for the isolated restoration proof"
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        env.pop(key, None)
    def git(*args):
        return subprocess.run([real_git, *args], cwd=tmp_path, env=env,
                              check=True, capture_output=True, text=True)
    sigdir = tmp_path / "site/signals"
    sigdir.mkdir(parents=True)
    leaf = tmp_path / "data/signal_archive/mtf_signals_latest.json"
    leaf.parent.mkdir(parents=True)
    ticker = sigdir / "AAPL.json"
    ticker.write_text(json.dumps(_valid_ticker()))
    leaf_doc = _valid_leaf()
    leaf_doc["signals"] = leaf_doc["signals"][:1]
    leaf.write_text(json.dumps(leaf_doc))
    assert vs.run(sigdir, leaf, tmp_path / "fixture-audit.json") == 0
    baseline = {path: path.read_bytes() for path in (ticker, leaf)}
    ledger = tmp_path / "data/unrelated-ledger.txt"
    ledger.write_text("committed nightly ledger\n")
    (tmp_path / ".gitignore").write_text("site/signals/ignored-*.json\n")
    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Inert fixture", "-c", "user.email=fixture@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
        "commit", "-qm", "synthetic baseline")
    baseline_sha = git("rev-parse", "HEAD").stdout.strip()
    # Stage a distinct, schema-valid unaccepted signal candidate. Index checkout is wrong.
    for path in (ticker, leaf):
        doc = json.loads(path.read_text())
        doc["asof"] = "2026-06-20"
        path.write_text(json.dumps(doc))
    git("add", "site/signals", "data/signal_archive")
    for path, content in baseline.items():
        path.write_bytes(content)
    ledger.write_text("uncommitted nightly ledger must survive\n")
    git("add", "data/unrelated-ledger.txt")
    ledger_index = git("show", ":data/unrelated-ledger.txt").stdout
    bindir = tmp_path / "stub-bin"
    bindir.mkdir()
    for name in ("python", "git"):
        stub = bindir / name
        stub.write_text(f"#!{sys.executable}\n" + _SIGNAL_STUB)
        stub.chmod(0o755)
    calls = tmp_path / "calls.jsonl"
    output = tmp_path / "outputs"
    if bad_output:
        output.mkdir()
    env.update(PATH=str(bindir) + os.pathsep + os.defpath, CALLS=str(calls),
               REAL_GIT=real_git, SCENARIO=scenario, PROJECT_ROOT=str(vs.ROOT),
               RUNNER_TEMP=str(tmp_path), GITHUB_OUTPUT=str(output),
               GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    steps, index = _signal_steps(workflow)
    script = tmp_path / "gate.sh"
    script.write_text(steps[index]["run"])
    result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
    trace = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines()
                   if "=" in line) if output.is_file() else {}
    assert ledger.read_text() == "uncommitted nightly ledger must survive\n"
    assert git("show", ":data/unrelated-ledger.txt").stdout == ledger_index
    return result, trace, outputs, baseline, baseline_sha


@pytest.mark.parametrize("workflow", ["engine-render", "closing-bell", "earlyclose"])
@pytest.mark.parametrize("scenario", ["builder_failure", "validator_failure", "engine_failure"])
def test_signal_workflow_stops_before_rejected_consumption(tmp_path, workflow, scenario):
    result, trace, outputs, _, _ = _exercise_signal_gate(tmp_path, workflow, scenario)
    assert result.returncode != 0, result.stdout + result.stderr
    modules = [call[2] for call in trace if call[0] == "python"]
    assert modules == {
        "builder_failure": ["scripts.build_signal_quality"],
        "validator_failure": ["scripts.build_signal_quality", "scripts.validate_signals"],
        "engine_failure": ["scripts.build_signal_quality", "scripts.validate_signals", "engine.run"],
    }[scenario]
    assert outputs.get("accepted") != "true"


@pytest.mark.parametrize("workflow", ["engine-render", "closing-bell", "earlyclose", "daily"])
def test_signal_workflow_success_is_affirmatively_admitted(tmp_path, workflow):
    result, trace, outputs, _, _ = _exercise_signal_gate(tmp_path, workflow)
    assert result.returncode == 0, result.stdout + result.stderr
    modules = [call[2] for call in trace if call[0] == "python"]
    assert modules[:2] == ["scripts.build_signal_quality", "scripts.validate_signals"]
    assert ("engine.run" in modules) == (workflow != "daily")
    assert not any(call[0] == "git" and call[1] in {"restore", "checkout", "clean"} for call in trace)
    assert outputs.get("accepted") == "true"


@pytest.mark.parametrize("scenario", ["builder_failure", "validator_failure"])
def test_signal_daily_fallback_restores_commit_not_index_then_revalidates(tmp_path, scenario):
    result, trace, outputs, baseline, sha = _exercise_signal_gate(tmp_path, "daily", scenario)
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs.get("accepted") == "true"
    for path, content in baseline.items():
        assert path.read_bytes() == content
    assert not (tmp_path / "site/signals/STRAY.json").exists()
    assert not (tmp_path / "site/signals/ignored-STRAY.json").exists()
    restore = next(i for i, call in enumerate(trace) if call[:2] == ["git", "restore"])
    assert f"--source={sha}" in trace[restore]
    assert {"--staged", "--worktree"}.issubset(trace[restore])
    clean = next(i for i, call in enumerate(trace) if call[:2] == ["git", "clean"])
    validations = [i for i, call in enumerate(trace) if call[:3] == ["python", "-m", "scripts.validate_signals"]]
    assert restore < clean < validations[-1]
    assert len(validations) == (2 if scenario == "validator_failure" else 1)


@pytest.mark.parametrize("scenario", ["restore_leaf", "restore_charts", "cleanup_failure", "invalid_fallback", "ref_failure"])
def test_signal_daily_unproved_fallback_is_rejected(tmp_path, scenario):
    result, trace, outputs, _, _ = _exercise_signal_gate(tmp_path, "daily", scenario)
    assert result.returncode != 0, result.stdout + result.stderr
    assert outputs.get("accepted") != "true"
    assert not any(call[:3] == ["python", "-m", "engine.run"] for call in trace)
    if scenario in {"restore_leaf", "restore_charts", "cleanup_failure", "ref_failure"}:
        assert not any(call[:3] == ["python", "-m", "scripts.validate_signals"] for call in trace)


@pytest.mark.parametrize("workflow", ["engine-render", "closing-bell", "earlyclose", "daily"])
def test_signal_output_failure_cannot_admit_a_candidate(tmp_path, workflow):
    result, trace, outputs, _, _ = _exercise_signal_gate(tmp_path, workflow, bad_output=True)
    assert result.returncode != 0
    assert not trace
    assert not outputs


# These paths cannot publish candidate signal bytes. Security tombstone cleanup and
# diagnostics deliberately remain available on failure. Other producers are not exceptions.
_SIGNAL_FAILURE_SAFE = {
    "guard — market-state board coherence (ui.ms_board_coherence)",
    "restore accepted leader source for downstream consumers",
    "enforce Prophet R2 index tombstone (unconditional)",
    "restore accepted Prophet source for downstream derivations",
    "retain this run's Theme Graph generation witness (advisory)",
    "signal sanity (correctness tripwire — warn mode)",
    "verify R2 data plane freshness (loud tripwire — the publish above is non-fatal)",
    "OIP PIT — fail closed after unrelated rendering completes",
    "timings ledger + 85% budget tripwire (W2)",
    "timings band — engine-core (W2)",
    "timings band — prophet (W2)",
    "timings band — builders-parallel (W2)",
    "timings band — tail-desks (W2)",
    "timings band — commit-publish (W2)",
}


def _signal_step_eligible(condition, *, outcome, accepted, job_success, lane="off"):
    """Small evaluator for this frozen workflow's scalar conditions, not an Actions runner."""
    expression = str(condition or "success()").strip()
    if expression.startswith("${{"):
        assert expression.endswith("}}")
        expression = expression[3:-2].strip()
    assert "${{" not in expression and "}}" not in expression
    # The gate has no continue-on-error: its failure also makes job success false.
    job_success = job_success and outcome not in {"failure", "cancelled"}
    status = {"always": True, "success": job_success, "failure": not job_success, "cancelled": False}
    if not re.search(r"\b(?:always|success|failure|cancelled)\s*\(", expression):
        if not job_success:
            return False
    for name, value in status.items():
        expression = re.sub(r"\b" + name + r"\s*\(\s*\)", str(value), expression)
    def value(match):
        field = match.group(0)
        if field == "steps.signal_gate.outcome":
            return repr(outcome)
        if field == "steps.signal_gate.outputs.accepted":
            return repr(accepted)
        if field.endswith(".outcome"):
            return repr("success")
        if field.endswith(".theme_graph_witness"):
            return repr("retained-witness")
        if field.endswith((".ready", ".r2_ready", ".succeeded")):
            return repr("true")
        if field == "vars.AD1_M1_LANE":
            return repr(lane)
        return repr("")
    expression = re.sub(r"\b(?:steps|vars)\.[\w.-]+", value, expression)
    expression = re.sub(r"!(?!=)", " not ", expression).replace("&&", " and ").replace("||", " or ")
    tree = ast.parse(expression.strip(), mode="eval")
    allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
               ast.Compare, ast.Eq, ast.NotEq, ast.Constant)
    assert all(isinstance(node, allowed) for node in ast.walk(tree)), expression
    return bool(eval(compile(tree, "<inert-step-if>", "eval"), {"__builtins__": {}}))


@pytest.mark.parametrize("workflow", ["engine-render", "closing-bell", "earlyclose", "daily"])
@pytest.mark.parametrize("outcome,accepted", [
    ("failure", "false"), ("failure", "true"), ("cancelled", ""),
    ("skipped", ""), ("", ""), ("success", ""), ("success", "false"),
])
def test_signal_unconditional_sinks_require_complete_gate(workflow, outcome, accepted):
    steps, index = _signal_steps(workflow)
    assert steps[index].get("id") == "signal_gate"
    assert not steps[index].get("continue-on-error", False)
    # Successful earlier steps plus a skipped/missing gate must also fail closed.
    for job_success in (False, True):
        effects = [step.get("name", step.get("uses")) for step in steps[index + 1:]
                   if step.get("name") not in _SIGNAL_FAILURE_SAFE
                   and _signal_step_eligible(step.get("if"), outcome=outcome,
                                             accepted=accepted, job_success=job_success)]
        assert not effects, effects


@pytest.mark.parametrize("workflow", ["engine-render", "closing-bell", "earlyclose", "daily"])
def test_signal_accepted_consumers_keep_normal_success_path(workflow):
    steps, index = _signal_steps(workflow)
    for step in steps[index + 1:]:
        if step.get("name") in _SIGNAL_FAILURE_SAFE:
            continue
        assert _signal_step_eligible(step.get("if"), outcome="success", accepted="true", job_success=True), step.get("name")
        if not re.search(r"\b(?:always|success|failure|cancelled)\s*\(", str(step.get("if", ""))):
            assert not _signal_step_eligible(step.get("if"), outcome="success", accepted="true", job_success=False), step.get("name")


def test_signal_daily_diagnostics_survive_and_later_unrelated_failure_does_not_erase_acceptance():
    steps, index = _signal_steps("daily")
    by_name = {step.get("name"): step for step in steps[index + 1:]}
    for name in ["enforce Prophet R2 index tombstone (unconditional)",
                 "verify R2 data plane freshness (loud tripwire — the publish above is non-fatal)",
                 "timings ledger + 85% budget tripwire (W2)"]:
        assert _signal_step_eligible(by_name[name].get("if"), outcome="failure", accepted="false", job_success=False)
    for name in ["checkpoint core engine outputs to main (durable before tail desks)",
                 "commit engine outputs", "commit chronicle artifacts",
                 "assemble machine-consumable feeds (site/feeds -> R2)",
                 "publish heavy per-ticker stores to R2 (additive; no-op without creds)"]:
        assert _signal_step_eligible(by_name[name].get("if"), outcome="success", accepted="true", job_success=False)
