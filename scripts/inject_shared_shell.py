"""Apply or verify the common Shared Shell capability on retained HTML pages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.pages import dbase_prefix, write_page
from lib.shared_shell import (ASSET_NAME, STYLESHEET_NAME, asset_version,
                              stylesheet_version, copy_shared_shell_asset, inject_shared_shell_text)
from scripts.optimize_assets import paired_html_pages


def run(site: Path, *, check: bool) -> dict:
    if check:
        for name in (ASSET_NAME, STYLESHEET_NAME):
            emitted = site / name
            source = Path(__file__).resolve().parent.parent / "templates" / name
            if not emitted.is_file() or emitted.read_bytes() != source.read_bytes():
                raise ValueError("Shared Shell asset does not match its source: " + name)
    else:
        copy_shared_shell_asset(site)
    version = asset_version(site)
    css_version = stylesheet_version(site)
    changed = []
    # Paired source files first, matching the existing optimizer/sync ownership.
    for template, emitted in paired_html_pages(site):
        original = template.read_text()
        result = inject_shared_shell_text(original, dbase_prefix(emitted), version=version, css_version=css_version,
                                          response_kind="coming_soon" if emitted.name == "coming-soon.html" else "content")
        if result != original:
            changed.append(str(template))
            if not check:
                template.write_text(result)
    files = documents = 0
    for path in sorted(site.rglob("*.html")):
        if path.is_symlink() or not path.is_file():
            continue
        files += 1
        original = path.read_text()
        result = inject_shared_shell_text(original, dbase_prefix(path), version=version, css_version=css_version,
                                          response_kind="coming_soon" if path.name == "coming-soon.html" else "content")
        if 'data-mmx-shared-shell-bridge="' in result:
            documents += 1
        if result != original:
            changed.append(str(path))
            if not check:
                write_page(path, result)
    return {"htmlFiles": files, "documents": documents, "changed": len(changed),
            "version": version, "examples": changed[:8]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=Path("site"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run(args.site_dir, check=args.check)
    print(json.dumps(result, ensure_ascii=False))
    return int(args.check and result["changed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
