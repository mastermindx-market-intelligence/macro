"""Build a review-only bundle from the exact assigned Macro candidate."""
from __future__ import annotations
import base64
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "3667000ca153496d8ff69e8864b159ac1e7b9de0"
def run(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert run("git", "rev-parse", "HEAD").stdout.strip() == BASE
test = json.loads((OUT / "candidate-test-receipt.json").read_text())
assert test["exit_code"] == 0 and test["source_unchanged_during_run"]
for name, expected in test["source_sha256"].items():
    assert digest(ROOT / name) == expected, "Source changed after tests: " + name
overlap = json.loads((OUT / "main-overlap-receipt.json").read_text())
paths = overlap["candidate_source_paths"]
assert len(paths) == 25
parts = []
for name in paths:
    tracked = run("git", "ls-files", "--error-unmatch", name).returncode == 0
    diff = run("git", "diff", "--binary", "--", name) if tracked else \
        run("git", "diff", "--no-index", "--binary", "/dev/null", name)
    assert diff.returncode in ((0,) if tracked else (0, 1)), diff.stderr
    assert diff.stdout, "Expected candidate delta absent: " + name
    parts.append(diff.stdout)
patch = OUT / "source-review.patch"
patch.write_text("".join(parts))
reverse = run("git", "apply", "--reverse", "--check", str(patch))
(OUT / "patch-check.txt").write_text(reverse.stdout + reverse.stderr)
assert reverse.returncode == 0, reverse.stderr
white = run("git", "diff", "--check")
(OUT / "whitespace-check.txt").write_text(white.stdout + white.stderr)
assert white.returncode == 0, white.stderr

for name in ("pytest-tmp", "pytest-ci-tmp", "pytest-screener-tmp",
             "pytest-compat-tmp", "pytest-clock-tmp", "__pycache__"):
    target = OUT / name
    if target.is_dir():
        assert not target.is_symlink() and target.resolve().parent == OUT.resolve()
        shutil.rmtree(target)

plan = ROOT / "research/SECTOR_CENTRAL_MACRO_PAPER_PIVOT_2026_10_20.md"
(OUT / "BUILD_PLAN.md").write_bytes(plan.read_bytes())
paper = json.loads((OUT / "paper-read-receipt.json").read_text())
manifest = {
    "schema": "macro_sector_source_review/v2",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "repository": "mastermindx-market-intelligence/macro",
    "operation_id": "sector-central-macro-paper-pivot-20261020-sol-001",
    "branch": "sol/web-sector-central-macro-paper-pivot-20261020-sol-001",
    "base_sha": BASE, "status": "PROVISIONAL_UNPUBLISHED_SOURCE_CANDIDATE",
    "canonical_url": "https://www.mastermind-x.com/sector_central.html",
    "source_sha256": {name: digest(ROOT / name) for name in paths},
    "selected_test_run": test,
    "source_checks": json.loads((OUT / "source-check-receipt.json").read_text()),
    "patch_reverse_check_exit": reverse.returncode,
    "final_whitespace_exit": white.returncode,
    "render_receipt": json.loads((OUT / "render-receipt.json").read_text()),
    "screener_probe": json.loads((OUT / "screener-source-probe.json").read_text()),
    "sector_clock_probe": json.loads((OUT / "sector-clock-source-probe.json").read_text()),
    "main_overlap": overlap,
    "paper": {"file_id": paper["file_id"], "page_id": paper["page_id"],
              "artboard_count": paper["artboard_count"], "node_count": paper["node_count"],
              "write_schema": paper["write_schema"],
              "image_receipt": json.loads((OUT / "paper-image-receipt.json").read_text())},
    "publication": json.loads((OUT / "publication-blocker.json").read_text()),
    "browser_candidate_verified": False, "paper_board_updated": False,
    "full_design_review_approved": False, "production_published": False,
    "additional_implementation_pending": ["Native Paper Dossier journey",
                                         "Native Paper Research-question receiver journey"],
}
allowed = {".md", ".txt", ".json", ".py", ".jsx", ".jpg", ".html", ".diff"}
excluded = {"review-manifest.json", "transport-receipt.json"}
files = {path.name: path for path in OUT.iterdir()
         if path.is_file() and path.suffix in allowed and path.name not in excluded}
files["macro-sector-central.patch"] = patch
manifest["archive_file_sha256"] = {name: digest(path) for name, path in sorted(files.items())}
manifest_path = OUT / "review-manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
files["review-manifest.json"] = manifest_path
archive = OUT / "Macro_Sector_Central_Source_Review_2026-10-20.zip"
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, path in sorted(files.items()):
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 20, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
raw64 = base64.b64encode(archive.read_bytes()).decode()
wrapped = "\n".join(raw64[i:i+76] for i in range(0, len(raw64), 76)) + "\n"
(OUT / (archive.name + ".b64")).write_text(wrapped)
receipt = {"archive": archive.name, "archive_bytes": archive.stat().st_size,
           "archive_sha256": digest(archive), "archive_entries": len(files),
           "base64_lines": len(wrapped.splitlines()),
           "patch_sha256": digest(patch), "patch_bytes": patch.stat().st_size,
           "plan_sha256": digest(plan), "manifest_sha256": digest(manifest_path),
           "tests": test["result_line"], "source_unchanged_since_tests": True}
(OUT / "transport-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
