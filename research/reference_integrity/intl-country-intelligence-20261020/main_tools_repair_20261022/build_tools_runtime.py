"""Build a review repair with the normal builder and the retained production inputs."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import argparse, json, os, re, shutil, subprocess, sys, tarfile, time
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--label", required=True, choices=("shelltools20261022",))
    parser.add_argument("--overlay", action="append", default=[])
    args = parser.parse_args()
    build = Path("/tmp/intl-rig-shelltools-20261022") / args.label / "source"
    if build.exists():
        raise RuntimeError("Build directory exists; inspect the prior result before a new attempt")
    build.mkdir(parents=True)
    archive = build.parent / "source.tar"
    subprocess.run(["git", "archive", "--format=tar", "--output=" + str(archive),
                    args.source_sha, "config.yml", "config", "collectors", "engine",
                    "lib", "scripts", "templates", "requirements.txt", "site/fonts", "site/favicon.svg"],
                   cwd=ROOT, check=True, timeout=120)
    with tarfile.open(archive) as tf:
        tf.extractall(build, filter="data")
    snapshot_path = OUT.parent / "production_input_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text())
    input_archive = ROOT / snapshot["archive"]["path"]
    assert sha256(input_archive.read_bytes()).hexdigest() == snapshot["archive"]["sha256"]
    with tarfile.open(input_archive) as tf:
        assert all(n.startswith("data/") or n in {
            "site/macrodata/global_regime_fragment.json", "site/live_config.js",
            "production_input_snapshot.json"} for n in tf.getnames())
        tf.extractall(build, filter="data")
    for row in snapshot["files"]:
        assert sha256((build / row["path"]).read_bytes()).hexdigest() == row["sha256"], row["path"]
    overlays = []
    for name in args.overlay:
        source = (ROOT / name).resolve()
        assert source.is_relative_to(ROOT) and name.startswith(("templates/", "lib/", "engine/"))
        raw = source.read_bytes()
        (build / name).write_bytes(raw)
        overlays.append({"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    target = OUT / ("proposed_" + args.label + "_repair")
    assert not target.exists()
    target.mkdir()
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    command = [sys.executable, "-m", "scripts.build_intl"]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    with (OUT / ("repair_" + args.label + "_build.log")).open("w") as log:
        result = subprocess.run(command, cwd=build, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=1200)
    receipt = {
        "schema": "intl.current_main_build.v1",
        "build_driver_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "static_dependency_source_commit": args.source_sha,
        "source_commit": args.source_sha, "source_overlays": overlays,
        "input_snapshot": "../production_input_snapshot.json",
        "input_snapshot_sha256": sha256(snapshot_path.read_bytes()).hexdigest(),
        "kind": "ordinary builder with copied existing production stores",
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
        for name in sorted(required):
            source = build / "site" / name
            if not source.is_file():
                source = build / "templates" / name
            if not source.is_file():
                receipt.setdefault("missing_optional_assets", []).append(name)
                continue
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            raw = dest.read_bytes()
            receipt["files"].append({"path": str(dest.relative_to(ROOT)),
                "source_path": str(source.relative_to(build)), "sha256": sha256(raw).hexdigest(),
                "bytes": len(raw)})
        receipt["html_bytes"] = html.stat().st_size
        receipt["html_sha256"] = sha256(html.read_bytes()).hexdigest()
    (OUT / ("repair_" + args.label + "_build_receipt.json")).write_text(
        json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}))
    return result.returncode
if __name__ == "__main__":
    raise SystemExit(main())