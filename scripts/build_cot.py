"""Render the COT board and a coherent source-owned, immutable data bundle.

Called by the existing build_site pipeline. No network requests or new scheduler.
Standalone: python -m scripts.build_cot [--output path]
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from engine.cot_positioning import build_snapshot, validate_snapshot
from lib import config

CATEGORIES = {
    "equities": ("Equities", "\u80a1\u7968\u6307\u6570"),
    "fixed_income": ("Fixed income", "\u56fa\u5b9a\u6536\u76ca"),
    "energy": ("Energy", "\u80fd\u6e90"),
    "metals": ("Metals", "\u91d1\u5c5e"),
    "crypto": ("Crypto futures", "\u52a0\u5bc6\u8d44\u4ea7\u671f\u8d27"),
    "currencies": ("Currencies", "\u8d27\u5e01"),
}
TIERS = {
    "extreme": ("Extreme", "\u6781\u7aef"), "setup": ("Elevated", "\u7a81\u51fa"),
    "watch": ("Watch", "\u7559\u610f"), "neutral": ("Typical", "\u5e38\u6001"),
    "unavailable": ("No score", "\u6682\u65e0\u8bc4\u5206"),
}
STATES = {
    "current": ("Current", "\u6700\u65b0"), "stale": ("Old report", "\u65e7\u62a5\u544a"),
    "awaiting_update": ("Awaiting update", "\u7b49\u5f85\u66f4\u65b0"),
    "unavailable": ("Unavailable", "\u6682\u4e0d\u53ef\u7528"),
}


def _atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def build(*, site: Path | None = None, snapshot: dict | None = None) -> Path:
    site = Path(site) if site is not None else config.site_dir()
    snapshot = snapshot if snapshot is not None else build_snapshot()
    validate_snapshot(snapshot)
    templates = config.ROOT / "templates"
    env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(["html", "xml", "j2"]))
    page = env.get_template("cot_positioning.html.j2").render(
        snapshot=snapshot, categories=CATEGORIES, tiers=TIERS, states=STATES,
    )
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    digest = snapshot["content_sha256"]
    # Publish dependencies first, then the pointer/page. One page fetches exactly
    # its own immutable snapshot, never the latest pointer from another build.
    immutable = site / "cotdata" / f"{digest}.json"
    if immutable.exists():
        if immutable.read_text(encoding="utf-8") != payload:
            raise ValueError("COT immutable publication collision")
    else:
        _atomic(immutable, payload)
    _atomic(site / "cotdata" / "latest.json", payload)
    for name in ("cot_positioning.css", "cot_positioning.js"):
        _atomic(site / name, (templates / name).read_text(encoding="utf-8"))
    _atomic(site / "cot.html", page)
    return site / "cot.html"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(build(site=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
