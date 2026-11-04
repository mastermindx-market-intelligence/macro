"""Verify the retained International candidate without rebuilding or reacquiring data."""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone
import yaml

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
FROZEN = "883a1e48efdf9c334c08665262efa0961b1997a0"
SOURCE = "442042e591d255dd24b540ff240edb4c0410c297"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, timeout=20)

def main():
    proposal = yaml.safe_load((EVIDENCE / "proposal.yml").read_text())
    evidence = json.loads((EVIDENCE / "FINAL_ARTIFACT_EVIDENCE.json").read_text())
    approval = yaml.safe_load((EVIDENCE / "approval.yml").read_text())
    preparation = json.loads((EVIDENCE / "PUBLICATION_PREPARATION.json").read_text())
    artifact = proposal["proposed_artifact"]
    errors, checks = [], []
    def check(name, ok):
        checks.append(name)
        if not ok:
            errors.append(name)

    check("frozen identity", artifact["frozen_sha"] == FROZEN)
    check("source identity", artifact["source_commit"] == evidence["source_commit"] == SOURCE)
    check("approval identity", approval["artifact_sha"] == FROZEN)
    check("approval bytes", digest((EVIDENCE / "approval.yml").read_bytes()) == preparation["approval_sha256"])
    check("source ancestry", subprocess.run(["git", "merge-base", "--is-ancestor", SOURCE, FROZEN], cwd=ROOT).returncode == 0)
    for row in evidence["receipts"] + evidence["screenshots"] + evidence["source_files"]:
        path = ROOT / row["path"]
        check("digest:" + row["path"], path.is_file() and digest(path.read_bytes()) == row["sha256"])
    for relative in artifact["paths"] + [row["path"] for row in artifact["screenshots"]]:
        path = ROOT / relative
        if path.is_dir():
            continue
        check("frozen blob:" + relative, git("show", FROZEN + ":" + relative) == path.read_bytes())
    html = ROOT / artifact["paths"][0]
    actual_html = digest(html.read_bytes())
    check("HTML identity", actual_html == artifact["html_sha256"] == evidence["html_sha256"] == preparation["html_sha256"])
    review_bindings = []
    for name in ("product_regression", "visual_taste"):
        path = EVIDENCE / "reviews" / (name + ".yml")
        review = yaml.safe_load(path.read_text())
        check("review artifact:" + name, review["artifact_sha"] == FROZEN)
        review_bindings.append({"role": name, "path": str(path.relative_to(ROOT)), "sha256": digest(path.read_bytes())})
    check("retained browser failures", sum(row.get("failed", 0) for row in evidence["receipts"]) == 0)
    report = {
        "schema": "intl.recovery_verification.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "operation": "intl-country-cockpit-20261018",
        "predecessor_conversation": "6ad430fc-45bc-83e9-87d6-6925261eae24",
        "protected_law_sha": "c9cbee5569ba50e30e28715d930809061a169517",
        "artifact_sha": FROZEN,
        "source_sha": SOURCE,
        "observed_local_head": git("rev-parse", "HEAD").decode().strip(),
        "observed_main": git("rev-parse", "origin/main").decode().strip(),
        "html_sha256": actual_html,
        "proposal_sha256": digest((EVIDENCE / "proposal.yml").read_bytes()),
        "checked_count": len(checks),
        "errors": errors,
        "review_bindings": review_bindings,
        "retained_browser_assertions": sum(row.get("passed", 0) for row in evidence["receipts"]),
        "new_browser_execution": False,
        "new_data_acquisition": False,
        "production_acceptance": False,
        "scope": "Readback binding of the existing frozen artifact and its retained source, review, image and browser evidence. Current-main composition and hosted/served acceptance remain separate.",
    }
    output = EVIDENCE / "RECOVERY_VERIFICATION_20261021.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(output), "sha256": digest(output.read_bytes()), "checks": len(checks), "errors": errors}))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
