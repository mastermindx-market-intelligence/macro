#!/usr/bin/env python3
"""Render an explicitly non-public Catalyst Loop preview, never the live site."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
ASSETS = ("catalyst_scan.css", "catalyst_scan.js")


def render_preview(out: Path) -> Path:
    target = out.resolve()
    site = (ROOT / "site").resolve()
    if target == site or site in target.parents or target == ROOT or ROOT in target.parents:
        raise ValueError("Refusing to place a preview under the live repository")
    if target.exists() and any(target.iterdir()):
        raise ValueError("Preview destination must be empty")
    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, autoescape=True)
    markup = env.get_template("catalyst_scan.html.j2").render()
    if '<meta name="robots" content="noindex,nofollow">' not in markup:
        raise ValueError("Preview requires noindex")
    target.mkdir(parents=True, exist_ok=True)
    dest = target / "catalyst-scan.html"
    dest.write_text(markup, encoding="utf-8")
    for asset in ASSETS:
        shutil.copyfile(TEMPLATES / asset, target / asset)
    theme = ROOT / "site" / "theme.css"
    if theme.is_file():
        shutil.copyfile(theme, target / "theme.css")
    return dest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True, help="Empty preview directory outside repo")
    args = p.parse_args()
    print("CATALYST_PREVIEW_NOT_PUBLISHED:", render_preview(args.out))


if __name__ == "__main__":
    main()
