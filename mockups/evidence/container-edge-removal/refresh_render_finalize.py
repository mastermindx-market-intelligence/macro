"""Finalize and verify a scheduled-render merge through existing owners."""
from pathlib import Path
import hashlib, json, subprocess, sys, time

R = Path.cwd()
E = R / "mockups/evidence/container-edge-removal"
D = E / "integration-render-refresh"
MAIN = "43b5acdb0d0f264091f5aa33c129625fd0b28b8c"
HEAD = "bac05c4c15f648acb845a67caa54a7103b28fa6b"
BASE = "0386ca72ffa9accf9ca2cb7b2ee42a5221d82b9b"
sys.path.insert(0, str(R))
assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == HEAD
assert subprocess.check_output(["git", "rev-parse", "MERGE_HEAD"], text=True).strip() == MAIN

def sha(b):
    return hashlib.sha256(b).hexdigest()

def invoke_recipe(name, replacements):
    path = E / name
    code = path.read_text()
    for old, new in replacements:
        assert code.count(old) == 1, (name, old[:80], code.count(old))
        code = code.replace(old, new)
    exec(compile(code, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})

invoke_recipe("repair_generated_css.py", [
    ("Path('mockups/evidence/container-edge-removal/generated-css-receipt.json')",
     "Path('mockups/evidence/container-edge-removal/integration-render-refresh/generated-css-receipt.json')")
])
invoke_recipe("finish_consumers.py", [
    ("(E/'consumer-residual-repairs.json')", "(E/'integration-render-refresh/consumer-residual-repairs.json')")
])
from scripts.optimize_assets import optimize
stamped = optimize(R / "site")
assert stamped >= 0
(D / "asset-stamp-receipt.json").write_text(json.dumps({
    "owner": "scripts.optimize_assets.optimize",
    "main": MAIN,
    "changed_files": stamped,
}, indent=2) + "\n")
maps = json.loads((E / "integration/combined-renames.json").read_text())
maps.update(json.loads((D / "consumer-projection-receipt.json").read_text())["renamed_assets"])
for row in json.loads((D / "generated-css-receipt.json").read_text()):
    target = row["asset"].removeprefix("site/")
    for old in row["old"]:
        if old != Path(target).stem:
            maps["assets/css/" + old + ".css"] = target
# The exact Canada divider repair reverses this one contextual projection.
# The accepted original asset therefore remains valid and is not globally retired.
retained = "assets/css/65788f85.css"
neutral_variant = "assets/css/d4935829.css"
if maps.get(retained) == neutral_variant:
    old_bytes = (R / "site" / retained).read_bytes()
    assert old_bytes == subprocess.check_output(["git", "show", HEAD + ":site/" + retained])
    approved = ".nb-cau-pop .cau-row + .cau-row { border-top:1px solid color-mix(in srgb,var(--warn) 20%,var(--line)); padding-top:4px; margin-top:2px; }"
    neutral = ".nb-cau-pop .cau-row + .cau-row { border-top:1px solid var(--line); padding-top:4px; margin-top:2px; }"
    assert old_bytes.decode().count(approved) == 1
    assert (R / "site" / neutral_variant).read_bytes() == old_bytes.decode().replace(approved, neutral).encode()
    refs = {key: [] for key in (retained, neutral_variant)}
    for page in (R / "site").rglob("*.html"):
        text = page.read_text()
        for key in refs:
            if key in text:
                refs[key].append(str(page.relative_to(R)))
    assert refs[retained] == ["site/canada.html"] and not refs[neutral_variant], refs
    maps.pop(retained)
(D / "combined-renames.json").write_text(json.dumps(maps, indent=2) + "\n")
assert sha((R / "site/glossary.html").read_bytes()) == "ffbb4e2501f135e55da566992545caee7bea3571325244363d0ce20ee1f92d48"
print(json.dumps({"finalized": True, "canonical_asset_stamp_files": stamped, "canonical_glossary_retained": True}), flush=True)

checks = []
def run(name, command):
    log = D / (name + ".log")
    print(json.dumps({"starting": name}), flush=True)
    started = time.monotonic()
    with log.open("w") as stream:
        p = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    row = {
        "name": name,
        "exit_code": p.returncode,
        "seconds": round(time.monotonic() - started, 2),
        "log": str(log.relative_to(R)),
    }
    checks.append(row)
    (D / "validation-receipt.json").write_text(json.dumps({
        "schema": "mastermind.container_edge_render_refresh_validation.v1",
        "main": MAIN,
        "accepted_reference": HEAD,
        "checks": checks,
    }, indent=2) + "\n")
    print(json.dumps(row), flush=True)
    print(log.read_text()[-1800:], flush=True)
    assert p.returncode == 0, name

def recipe_command(name, replacements):
    path = E / name
    code = path.read_text()
    for old, new in replacements:
        assert code.count(old) == 1, (name, old[:80], code.count(old))
        code = code.replace(old, new)
    return [sys.executable, "-c",
            "exec(compile(" + repr(code) + "," + repr(str(path)) +
            ",'exec'),{'__name__':'__main__','__file__':" + repr(str(path)) + "})"]

run("preservation", recipe_command("verify_integrated_consumers.py", [
    ("I=E/'integration'", "I=E/'integration-render-refresh'"),
    ("c58c69bf42786f29c8857550bdb244d08da35240", MAIN),
    ("97abae6fa8f17bdb71f8670d59d1ba43497e3ae7", HEAD),
    ("65f534bdc1369d2496f8e044a90636997e223392", BASE),
]))
paths = [
    "site/cycledata/cycle_engine.js",
    "site/marketsdata/markets_engine.js",
    "site/measurementdata/measurement_data.js",
    "site/regimedata/regime_prior.js",
    "site/sector_central_data.js",
]
rows = []
for path in paths:
    current = (R / path).read_bytes()
    expected = subprocess.check_output(["git", "show", MAIN + ":" + path])
    assert current == expected, path
    rows.append({"path": path, "sha256": sha(current), "exact_main": True})
(D / "external-data-preservation.json").write_text(json.dumps(rows, indent=2) + "\n")
run("template-sync", [sys.executable, "scripts/check_template_site_sync.py"])
run("glossary-parity", [sys.executable, "-m", "pytest", "-q",
    "tests/test_glossary_contract.py::test_site_pair_matches_a_fresh_render_of_the_template",
    "tests/test_glossary_contract.py::test_committed_glossary_page_carries_the_alert_banner_script"])
run("consumer-audit", recipe_command("audit_consumers.py", [
    ("renamed=json.loads((E/'consumer-projection-receipt.json').read_text())['renamed_assets']",
     "renamed=json.loads((E/'integration-render-refresh/combined-renames.json').read_text())"),
    ("(E/'consumer-residual-audit.json')", "(E/'integration-render-refresh/consumer-residual-audit.json')")
]))
audit = json.loads((D / "consumer-residual-audit.json").read_text())
assert not audit["residuals"] and not audit["missing_assets"] and not audit["superseded_references"]
diff = R / ".cache/glossary-output-repair/render-refresh-ui.diff"
with diff.open("wb") as stream:
    subprocess.run(["git", "diff", "--binary", MAIN, "--", "."], stdout=stream, check=True)
run("ui-evidence", [sys.executable, "scripts/check_ui_visual_evidence.py", "--diff-file", str(diff)])
print("RENDER_REFRESH_VERIFIED", flush=True)
