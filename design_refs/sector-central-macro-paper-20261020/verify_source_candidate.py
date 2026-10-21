"""Check only the candidate delta and the repository's existing style gates."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def run(args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
tracked = run(["git", "diff", "--unified=0", "--", "templates"])
assert tracked.returncode == 0, tracked.stderr
parts = [tracked.stdout]
new_partials = [
    "templates/_sector_central_paper.css.j2",
    "templates/_sector_central_brief.html.j2",
    "templates/_sector_central_brief.js.j2",
    "templates/_sector_central_coverage.js.j2",
    "templates/_sector_prophet_context.html.j2",
    "templates/_sector_prophet_context.css.j2",
    "templates/_sector_prophet_context.js.j2",
]
for path in new_partials:
    assert (ROOT / path).is_file()
    if run(["git", "ls-files", "--error-unmatch", path]).returncode != 0:
        delta = run(["git", "diff", "--no-index", "--unified=0", "/dev/null", path])
        assert delta.returncode in (0, 1), delta.stderr
        parts.append(delta.stdout)
(OUT / "design.diff").write_text("".join(parts))
commands = {
    "design-system-check.txt": ["python3", "scripts/check_design_system.py", "--mode", "enforce-added", "--diff-file", str(OUT / "design.diff")],
    "runtime-style-check.txt": ["python3", "scripts/check_runtime_style_injection.py"],
    "whitespace-check.txt": ["git", "diff", "--check"],
}
codes = {}
for name, args in commands.items():
    result = run(args)
    (OUT / name).write_text(result.stdout + result.stderr)
    codes[name] = result.returncode
    print(name + ": exit " + str(result.returncode))
paired = (ROOT / "templates/si_workspace.js").read_bytes() == (ROOT / "site/si_workspace.js").read_bytes()
assert paired, "Paired router assets differ"
stock_paired = (ROOT / "templates/stocktable.js").read_bytes() == (ROOT / "site/stocktable.js").read_bytes()
assert stock_paired, "Paired stocktable assets differ"
receipt = {"checks": codes, "router_asset_byte_equal": paired, "stocktable_asset_byte_equal": stock_paired, "added_partials_checked": new_partials}
(OUT / "source-check-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
assert all(code == 0 for code in codes.values()), codes
print("Paired router and stocktable assets are byte-identical; all candidate source checks passed.")
