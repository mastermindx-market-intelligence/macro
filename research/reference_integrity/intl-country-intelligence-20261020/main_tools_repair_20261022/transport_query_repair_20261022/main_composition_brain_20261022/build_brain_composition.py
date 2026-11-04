"""Build the Brain composition with the normal builder and retained production inputs."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import argparse, json, os, re, shutil, subprocess, sys, tarfile, time
ROOT = Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
OUT = ROOT / (
    "research/reference_integrity/intl-country-intelligence-20261020/"
    "main_tools_repair_20261022/transport_query_repair_20261022/"
    "main_composition_brain_20261022"
)
# The prior reviewed 44-route artifact inventory, preserving nested font routes.
ORIGINAL_ASSETS = frozenset("""
account.js chart_i18n.js charts.js
dashboard-icons.css dashboard-icons.js data_base.js
favicon.svg fonts/Inter-400.woff2 fonts/Inter-500.woff2
fonts/Inter-600.woff2 fonts/Inter-700.woff2 fonts/Inter-800.woff2
fonts/Inter-900.woff2 fonts/InterDisplay-500.woff2 fonts/InterDisplay-600.woff2
fonts/InterDisplay-700.woff2 intl.html intl_library_search.js
intl_workspace.css intl_workspace.js intl_workspace_entry.js
intl_workspace_history.css intl_workspace_macro.css intl_workspace_risk.css
intl_workspace_scenario.js intl_workspace_state.js intl_workspace_surveillance.css
live.js live_config.js logo_config.js
mm_brain.js mm_brain_visuals.css mtf.js
nav_market.js navigation-refresh.css product-nav-icons.css
shared_shell.css shared_shell_bridge.js stock-logos.js
stockdata.js stockview.js tablesort.js
theme.css theme.js
""".split())
BRAIN_ASSETS = frozenset({
    "mm_brain_presentation.js",
    "mm_brain_markdown.js",
    "mm_brain_finance.js",
    "mm_brain_finance.css",
    "mm_brain_finance_math_v1.js",
    "mm_brain_math.js",
    "mm_brain_visuals.js",
})
EXPECTED_ASSETS = ORIGINAL_ASSETS | BRAIN_ASSETS
INPUT_SNAPSHOT_SHA256 = "081592644c4f2d425fdde59d7b8e153e4aa214aa00d115ba64b13bd31c145b08"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--label", default="braincomposition20261022",
                        choices=("braincomposition20261022",))
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha must be the full immutable 40-character commit SHA")
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", args.source_sha + "^{commit}"],
        cwd=ROOT, check=True, capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    if resolved != args.source_sha:
        raise RuntimeError("The supplied source SHA must identify that exact commit")
    build = Path("/private/tmp/intl-rig-brain-composition-20261022/source")
    target = OUT / ("proposed_" + args.label + "_repair")
    log_path = OUT / ("repair_" + args.label + "_build.log")
    receipt_path = OUT / ("repair_" + args.label + "_build_receipt.json")
    for path in (build.parent, target, log_path, receipt_path):
        if path.exists() or path.is_symlink():
            raise RuntimeError("Output exists; preserve and inspect the prior result: " + str(path))
    build.mkdir(parents=True)
    archive = build.parent / "source.tar"
    subprocess.run(["git", "archive", "--format=tar", "--output=" + str(archive),
                    args.source_sha, "config.yml", "config", "collectors", "engine",
                    "lib", "scripts", "templates", "requirements.txt", "site/fonts", "site/favicon.svg"],
                   cwd=ROOT, check=True, timeout=120)
    with tarfile.open(archive) as tf:
        tf.extractall(build, filter="data")
    snapshot_path = OUT.parent.parent.parent / "production_input_snapshot.json"
    snapshot_raw = snapshot_path.read_bytes()
    if sha256(snapshot_raw).hexdigest() != INPUT_SNAPSHOT_SHA256:
        raise RuntimeError("The retained production input snapshot changed")
    snapshot = json.loads(snapshot_raw)
    if len(snapshot["files"]) != 510 or len({row["path"] for row in snapshot["files"]}) != 510:
        raise RuntimeError("The retained production snapshot must contain exactly 510 unique inputs")
    input_archive = ROOT / snapshot["archive"]["path"]
    assert sha256(input_archive.read_bytes()).hexdigest() == snapshot["archive"]["sha256"]
    with tarfile.open(input_archive) as tf:
        assert all(n.startswith("data/") or n in {
            "site/macrodata/global_regime_fragment.json", "site/live_config.js",
            "production_input_snapshot.json"} for n in tf.getnames())
        tf.extractall(build, filter="data")
    for row in snapshot["files"]:
        assert sha256((build / row["path"]).read_bytes()).hexdigest() == row["sha256"], row["path"]
    overlays = []  # Exact committed source only; no overlay interface.
    target.mkdir()
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    command = [sys.executable, "-m", "scripts.build_intl"]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    with log_path.open("x") as log:
        result = subprocess.run(command, cwd=build, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=1200)
    receipt = {
        "schema": "intl.current_main_build.v1",
        "build_driver_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "static_dependency_source_commit": args.source_sha,
        "source_commit": args.source_sha, "source_overlays": overlays,
        "input_snapshot": "../../../production_input_snapshot.json",
        "input_snapshot_sha256": sha256(snapshot_raw).hexdigest(),
        "kind": "ordinary builder with copied existing production stores",
        "artifact_inventory_kind": "build output plus required static dependency inventory",
        "command": command, "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.monotonic() - tick, 2),
        "exit_code": result.returncode, "source_reacquisition": False,
        "production_mutation": False, "files": [],
    }
    if result.returncode == 0:
        html = build / "site/intl.html"
        text = html.read_text()
        required = {"intl.html", "mm_brain.js", "account.js", "mm_brain_visuals.css", "favicon.svg", "nav_market.js"}
        required.update(BRAIN_ASSETS)
        fonts = sorted((build / "site/fonts").glob("*.woff2"))
        assert fonts, "The pinned production typeface assets must be present"
        required.update("fonts/" + p.name for p in fonts)
        required.update(p.name for p in (build / "site").iterdir()
                        if p.is_file() and p.suffix in {".css", ".js"})
        for item in re.findall(r"""(?:src|href)=["']([^"']+)["']""", text):
            item = item.split("?")[0].split("#")[0].lstrip("/")
            if item and "://" not in item and not item.startswith("data:") and item.endswith(
                    (".css", ".js", ".woff2", ".woff", ".json")):
                required.add(item)
        if required != EXPECTED_ASSETS or len(required) != 51:
            raise RuntimeError("Expected exactly the prior 44 routes plus seven Brain dependencies; "
                               + "missing=" + repr(sorted(EXPECTED_ASSETS - required))
                               + ", unexpected=" + repr(sorted(required - EXPECTED_ASSETS)))
        for name in sorted(required):
            source = build / "site" / name
            if not source.is_file():
                source = build / "templates" / name
            if not source.is_file():
                raise RuntimeError("Required build/static dependency is missing: " + name)
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            raw = dest.read_bytes()
            receipt["files"].append({"path": str(dest.relative_to(ROOT)),
                "source_path": str(source.relative_to(build)), "sha256": sha256(raw).hexdigest(),
                "bytes": len(raw)})
        receipt["html_bytes"] = html.stat().st_size
        receipt["html_sha256"] = sha256(html.read_bytes()).hexdigest()
    with receipt_path.open("x") as receipt_file:
        receipt_file.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}))
    return result.returncode
if __name__ == "__main__":
    raise SystemExit(main())
