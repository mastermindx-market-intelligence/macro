"""Render the data-free Basic Materials sector dossier shell.

This builder does not read source data, create a private reader, or bake research
observations into the rendered site. The page stays explicitly unbound until the
incumbent GMI/source/private owners accept and expose the required reader.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402


def _temp_sibling(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.tmp")


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = _temp_sibling(destination)
    try:
        shutil.copyfile(source, temp)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def render_shell(root: Path) -> Path:
    root = Path(root)
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    html = env.get_template("basic_materials_intelligence.html.j2").render(
        generated_utc="unbound",
        active_section="research",
        active_page="basic_materials_intelligence",
    )
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"

    page = site / "basic_materials_intelligence.html"
    temp = _temp_sibling(page)
    try:
        write_page(temp, html)
        os.replace(temp, page)
    finally:
        temp.unlink(missing_ok=True)

    for name in ("basic_materials_intelligence.css", "basic_materials_intelligence.js"):
        _atomic_copy(root / "templates" / name, site / name)
    return page


def render_from_state(root: Path) -> Path:
    return render_shell(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=config.ROOT)
    args = parser.parse_args(argv)
    page = render_shell(args.root)
    print(f"wrote {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())