"""One authorized study execution; refuses replay or an existing family. No network."""
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import engine.local_projections as lp
from engine.trial_ledger import TrialLedger
from scripts.run_local_projections import parse_panel
FAMILY = "f10_lp_alfred_cpi_payroll_descriptive"
SPEC_PATH = ROOT / "research/local_projections/ALFRED_CPI_PAYROLL_V2_STUDY_SPEC.json"
SPEC_SHA = "d70bbc156dc892dfbcf538dc712a5772ec2fb43cb5a3af3c41b7d0a5af7c4871"
PANEL_PATH = ROOT / "data/experiments/local_projection_alfred_cpi_payroll_v2_panel.csv"
PANEL_SHA = "4456ebeff9ebd0e218d5d3b58b643c9a4fdc2e96b8cecabca55736287e7d14a6"
PREFIX = ROOT / "data/experiments/local_projection_alfred_cpi_payroll_v2"
REG_PATH = Path(str(PREFIX) + "_registration.json")
BUNDLE_PATH = Path(str(PREFIX) + "_results.json")
LEDGER_PATH = ROOT / "data/trial_ledger.jsonl"
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def durable_new(path, obj):
    raw = (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return digest(raw)
def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--execute-released-harness":
        raise SystemExit("Requires the verified protected harness merge SHA; this file does not estimate when imported.")
    release = sys.argv[2]
    subprocess.run(["git", "merge-base", "--is-ancestor", release, "HEAD"], cwd=ROOT, check=True)
    released_harness = subprocess.check_output(["git", "show", release + ":scripts/run_local_projections.py"], cwd=ROOT)
    assert released_harness == (ROOT / "scripts/run_local_projections.py").read_bytes(), "Current CLI differs from the verified protected release."
    if REG_PATH.exists() or BUNDLE_PATH.exists():
        raise SystemExit("Existing original study effect/receipt: inspect it; never replay this driver.")
    spec_raw, panel_raw = SPEC_PATH.read_bytes(), PANEL_PATH.read_bytes()
    assert digest(spec_raw) == SPEC_SHA and digest(panel_raw) == PANEL_SHA
    spec = json.loads(spec_raw)
    cutoff = dt.datetime.fromisoformat(spec["cutoff"])
    panel = parse_panel(panel_raw, cutoff)
    assert len(panel["y"]) == 332
    settings = [spec["primary"], *spec["robustness_family"]]
    assert [s["lags"] for s in settings] == [4, 2, 8]
    estimator_sha = digest(Path(lp.__file__).read_bytes())
    configs = [{"harness": "mastermind.local_projection_run/v1", "estimator_schema": lp.SCHEMA,
                "estimator_sha256": estimator_sha, "input_sha256": PANEL_SHA,
                "cutoff": panel["cutoff"], "period_start": panel["period"][0],
                "period_end": panel["period"][-1], "n_rows": len(panel["y"]),
                **s, "fdr_alpha": lp.FDR_ALPHA,
                "transform": "none; supplied y and shock values, ordered observation rows"} for s in settings]
    before = LEDGER_PATH.read_bytes()
    ledger = TrialLedger(LEDGER_PATH)
    assert not ledger.load_error and not ledger.corrupt_lines
    assert ledger.literal_n(FAMILY) == 0 and FAMILY not in ledger.families(), "Existing family: reconcile original registrations, never reset family."
    added = ledger.log_grid(configs, family=FAMILY, info_cutoff=panel["cutoff"],
                            source="research/local_projections/ALFRED_CPI_PAYROLL_V2_STUDY_SPEC.json",
                            note="All three prespecified lag configurations, before any estimation; frozen StudySpec SHA256 " + SPEC_SHA)
    assert added == 3
    after = LEDGER_PATH.read_bytes()
    assert after.startswith(before)
    cold = TrialLedger(LEDGER_PATH)
    assert cold.effective_n(FAMILY) == 3 and not cold.load_error and not cold.corrupt_lines
    rows = [json.loads(line) for line in after.splitlines() if json.loads(line).get("family") == FAMILY]
    assert len(rows) == 3 and [r["config"] for r in rows] == configs
    registration = {"schema": "f10.lp.registration_receipt/v1", "family": FAMILY,
                    "study_spec_sha256": SPEC_SHA, "input_sha256": PANEL_SHA,
                    "source_freeze_commit": "a44faea61cfcf8ca9e7e017f3bba0a54b5da5814",
                    "protected_harness_merge": release,
                    "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    "driver_sha256": digest(Path(__file__).read_bytes()),
                    "ledger_path": "data/trial_ledger.jsonl", "before_sha256": digest(before),
                    "after_sha256": digest(after), "new_rows": rows, "effective_n": 3,
                    "state_at_receipt": "ALL_THREE_REGISTERED_DURABLY_BEFORE_ANY_ESTIMATION"}
    reg_sha = durable_new(REG_PATH, registration)
    runs = []
    for role, config in zip(("primary", "robustness_lags_2", "robustness_lags_8"), configs):
        command = [sys.executable, str(ROOT / "scripts/run_local_projections.py"), "--input", str(PANEL_PATH),
                   "--cutoff", spec["cutoff"], "--family", FAMILY, "--ledger", str(LEDGER_PATH),
                   "--horizons", str(config["horizons"]), "--lags", str(config["lags"]),
                   "--embargo", str(config["embargo"])]
        process = subprocess.run(command, cwd=ROOT.parent, text=True, capture_output=True)
        durable_new(Path(str(PREFIX) + "_" + role + "_process.json"),
                    {"returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr})
        assert process.returncode == 0, "Retain failure; registration already exists; do not replay automatically."
        envelope = json.loads(process.stdout)
        assert envelope["registration"]["config"] == config
        assert envelope["registration"]["effective_n"] == 3
        assert envelope["registration"]["new_trial_logged"] is False
        assert digest(LEDGER_PATH.read_bytes()) == digest(after)
        runs.append({"role": role, "envelope": envelope})
    import numpy, pandas
    bundle = {"schema": "f10.lp.native_study_results/v1", "study_spec_sha256": SPEC_SHA,
              "input_sha256": PANEL_SHA, "registration_receipt_sha256": reg_sha,
              "estimator_sha256": estimator_sha,
              "harness_sha256": digest((ROOT / "scripts/run_local_projections.py").read_bytes()),
              "runtime": {"python": sys.version, "numpy": numpy.__version__, "pandas": pandas.__version__},
              "coverage": spec["coverage"], "runs": runs,
              "authority": spec["authority"], "scientific_acceptance": False,
              "completed_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    durable_new(BUNDLE_PATH, bundle)
    print(json.dumps({"registration": str(REG_PATH), "bundle": str(BUNDLE_PATH), "runs": len(runs), "registered_search_n": 3}))
if __name__ == "__main__":
    main()
