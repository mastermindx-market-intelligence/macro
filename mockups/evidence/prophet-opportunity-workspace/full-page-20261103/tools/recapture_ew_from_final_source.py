"""Genuinely recapture EW-P4 before binding its receipt to final, committed render inputs."""
from pathlib import Path
import argparse, hashlib, json, subprocess, sys, time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", type=Path, required=True)
parser.add_argument("--source-head", required=True)
parser.add_argument("--log", type=Path, required=True)
args = parser.parse_args()
root = args.workspace.resolve()
def git(*parts):
    return subprocess.check_output(["git", *parts], cwd=root, text=True).strip()
head = git("rev-parse", "HEAD")
assert head == args.source_head, (head, args.source_head)
prior_receipt_rel = "research/evidence/ew_p4_descriptive_ui_20261105_c2/receipt.json"
receipt_rel = "research/evidence/ew_p4_descriptive_ui_20261105_integrated71971/receipt.json"
output_rel = str(Path(receipt_rel).parent)
prior_bytes = subprocess.check_output(["git", "show", head + ":" + prior_receipt_rel], cwd=root)
prior = json.loads(prior_bytes)
assert (root / prior_receipt_rel).read_bytes() == prior_bytes, "Preserve an existing uncommitted receipt; reconcile its owner first."
assert not (root / output_rel).exists(), "Preserve new capture identity; reconcile the original process before a retry."
paths = sorted({row["path"] for row in prior["pr_source_equivalence"]["render_files"]} | {
    "templates/_prophet_page.css.j2",
    "templates/_prophet_opportunity_card.html.j2",
})
def blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
source_blobs = {path: git("rev-parse", head + ":" + path) for path in paths}
for path, expected in source_blobs.items():
    assert blob((root / path).read_bytes()) == expected, "Uncommitted render input: " + path
assert not args.log.exists(), "Use the original process/log for reconciliation; this log already exists."
started = time.time()
with args.log.open("x") as log:
    completed = subprocess.run(
        [sys.executable, "tests/probe_ew_p4_descriptive_ui_browser.py", "--output", output_rel],
        cwd=root, stdout=log, stderr=subprocess.STDOUT, check=False)
assert completed.returncode == 0, "Canonical recapture failed; see " + str(args.log)
assert git("rev-parse", "HEAD") == head, "Source head moved during capture."
for path, expected in source_blobs.items():
    assert blob((root / path).read_bytes()) == expected, "Render input moved during capture: " + path
receipt_path = root / receipt_rel
rec = json.loads(receipt_path.read_text())
assert rec["source_revision"] == head and rec["production_authenticated"] is False
assert len(rec["cases"]) == 68 and "pr_source_equivalence" not in rec
for case in rec["cases"]:
    shot = receipt_path.parent / case["screenshot"]
    assert hashlib.sha256(shot.read_bytes()).hexdigest() == case["sha256"], shot
    assert case["no_horizontal_overflow"] is True and case["page_errors"] == [], case["screenshot"]
for name in ("contact-radar-observed", "contact-radar-stale", "contact-sc-observed",
             "contact-sc-states", "contact-radar-states"):
    assert (receipt_path.parent / (name + ".png")).is_file(), name
rec["pr_source_equivalence"] = {
    "note": (
        "All 68 screenshots and five contact sheets were genuinely regenerated with the "
        "canonical tests/probe_ew_p4_descriptive_ui_browser.py at source_revision, in local "
        "anonymous synthetic Playwright contexts. The render inputs below were checked "
        "against the committed source before and after capture. The pending evidence-only "
        "commit retains those exact blobs. Prophet includes newly consumed by the dashboard "
        "are bound explicitly. This is not production or authenticated product acceptance."
    ),
    "pr_branch": git("branch", "--show-current"),
    "pr_parent_of_evidence_commit": head,
    "render_files": [
        {"path": path, "blob_at_source_revision": source_blobs[path],
         "blob_on_pr_branch": source_blobs[path], "equal": True}
        for path in paths
    ],
    "all_equal": True,
}
rec["previous_capture"] = {
    "source_revision": prior["source_revision"],
    "receipt_path": prior_receipt_rel,
    "receipt_git_blob": git("rev-parse", head + ":" + prior_receipt_rel),
    "receipt_sha256": hashlib.sha256(prior_bytes).hexdigest(),
}
receipt_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"source_revision": head, "cases": len(rec["cases"]),
                  "bound_render_files": len(paths), "duration_seconds": round(time.time()-started, 2),
                  "receipt": str(receipt_path), "canonical_recapture_exit": completed.returncode}))
