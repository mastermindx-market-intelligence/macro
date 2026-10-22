"""Build the GMI explorer pages -> site/gmi*.html.

Mirror of ``scripts/build_ontology_explorer.py``: a feature-owned builder that
does not extend ``scripts/build_site.py``. It reads the coverage proof output
(running the proof itself when ``--coverage-report`` is not given) and the
theme crosswalk through :mod:`scripts.gmi_explorer.model`, renders the six
explorer pages plus one page per issuer, and syncs its paired assets.

Writes nothing under ``data/``. The model JSON debug dump (``--model-out``)
refuses to land under ``data/`` or ``site/`` for the same reason the proof
refuses such an ``--out``: a debug artifact must never masquerade as data.

Usage: python -m scripts.build_gmi_explorer
       python scripts/build_gmi_explorer.py --coverage-report DIR --site-dir DIR
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402
from scripts.gmi_explorer.model import build_model  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_gmi_explorer")

ROOT = Path(__file__).resolve().parent.parent
#: route -> template. The issuer template is rendered once per model issuer.
TEMPLATES = {
    "gmi.html": ("gmi_map.html.j2", "map"),
    "gmi-index.html": ("gmi_index.html.j2", "index"),
    "gmi-relationships.html": ("gmi_relationships.html.j2", "relationships"),
    "gmi-coverage.html": ("gmi_coverage.html.j2", "coverage"),
    "gmi-states.html": ("gmi_states.html.j2", "states"),
}
ISSUER_TEMPLATE = ("gmi_issuer.html.j2", "issuer")
#: non-.j2 assets that ship byte-identically to site/ (paired plain-copy law).
#: Owned by the parallel lane; copied only when present.
PAIRED_ASSETS = ("gmi.css", "gmi.js")
SNAPSHOT_DIRNAME = Path("data/symbol_directory/snapshots")


def _newest_snapshot() -> Path:
    snaps = sorted((ROOT / SNAPSHOT_DIRNAME).glob("*.parquet"), key=lambda p: p.name)
    if not snaps:
        raise FileNotFoundError(f"no dated snapshot under {SNAPSHOT_DIRNAME}")
    return snaps[-1]


def _run_proof() -> tuple[dict, dict, str]:
    """Run the coverage proof into a temp dir; return (report, manifest, argv).

    The activity ledger is read BY DEFAULT; ``--activity-proposals`` is never
    passed — the proof does not de-duplicate and every row would count twice.
    """
    snapshot = _newest_snapshot()
    argv = [sys.executable, "-m", "scripts.gmi_coverage_proof",
            "--symbol-directory", str(snapshot.relative_to(ROOT)),
            "--out", "<tmp>"]
    env = dict(os.environ, TZ="UTC")
    with tempfile.TemporaryDirectory(prefix="gmi_proof_") as tmp:
        proc = subprocess.run(
            [sys.executable, "-m", "scripts.gmi_coverage_proof",
             "--symbol-directory", str(snapshot.relative_to(ROOT)),
             "--out", tmp],
            cwd=ROOT, env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            tail = "\n".join((proc.stderr or proc.stdout).splitlines()[-10:])
            raise RuntimeError(f"gmi_coverage_proof failed rc={proc.returncode}:\n{tail}")
        report = json.loads((Path(tmp) / "coverage_report.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (Path(tmp) / "UNIVERSE_MANIFEST.json").read_text(encoding="utf-8"))
    return report, manifest, "TZ=UTC " + " ".join(argv)


def _model_out_guard(path: Path) -> None:
    resolved = path.resolve()
    for guarded in ("data", "site"):
        boundary = (ROOT / guarded).resolve()
        if resolved == boundary or boundary in resolved.parents:
            raise SystemExit(f"--model-out {path} is under {boundary}/; refusing")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--coverage-report", default=None,
                        help="directory holding coverage_report.json (skips the proof run)")
    parser.add_argument("--manifest", default=None,
                        help="UNIVERSE_MANIFEST.json beside --coverage-report")
    parser.add_argument("--site-dir", default=None,
                        help="target site directory (default config storage.site_dir)")
    parser.add_argument("--model-out", default=None,
                        help="debug dump of the model JSON (never under data/ or site/)")
    args = parser.parse_args(argv)

    if args.coverage_report:
        report_dir = Path(args.coverage_report)
        report = json.loads(
            (report_dir / "coverage_report.json").read_text(encoding="utf-8"))
        manifest = None
        if args.manifest:
            manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        proof_command = None
    else:
        report, manifest, proof_command = _run_proof()

    model = build_model(report, manifest, repo_root=ROOT)
    if proof_command:
        model["provenance"]["proof_command"] = proof_command

    if args.model_out:
        out = Path(args.model_out)
        _model_out_guard(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(model, indent=1, sort_keys=True, ensure_ascii=False)
                       + "\n", encoding="utf-8")
        log.info("wrote model %s", out)

    site = Path(args.site_dir) if args.site_dir else ROOT / config.load()["storage"]["site_dir"]
    site.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,
    )
    for page, (template, page_key) in TEMPLATES.items():
        write_page(site / page, env.get_template(template).render(
            model=model, nav_prefix="", page_key=page_key))
        log.info("wrote %s", site / page)
    template, page_key = ISSUER_TEMPLATE
    for issuer in model["issuers"]:
        page = f"gmi-issuer-{issuer['ticker'].lower()}.html"
        write_page(site / page, env.get_template(template).render(
            model=model, nav_prefix="", page_key=page_key, issuer=issuer))
        log.info("wrote %s", site / page)

    for name in PAIRED_ASSETS:
        source = ROOT / "templates" / name
        if not source.exists():
            log.info("paired asset templates/%s not present yet; skipping", name)
            continue
        target = site / name
        if not target.exists() or target.read_bytes() != source.read_bytes():
            target.write_bytes(source.read_bytes())
            log.info("synced %s", name)

    log.info("gmi explorer: %d pages at %s",
             len(TEMPLATES) + len(model["issuers"]), site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
