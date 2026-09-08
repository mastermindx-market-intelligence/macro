"""Normal asset processing for the canonical macro target only.

Uses the same writer and library functions as the daily lane
(scripts.externalize_css + scripts.optimize_assets.make_optimizer +
lib.pages.write_page). Does not sweep or prune other pages.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from lib.pages import (  # noqa: E402
    dbase_prefix,
    externalize_css_text,
    externalize_js_text,
    write_page,
)
from scripts.optimize_assets import make_optimizer  # noqa: E402

OUT = Path(__file__).resolve().parent
TARGET = ROOT / "site" / "macro.html"
CSS_ROOT = ROOT / "site" / "assets" / "css"
JS_ROOT = ROOT / "site" / "assets" / "js"
MIN_BYTES = 1024


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    import subprocess

    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def main() -> int:
    before = sha256(TARGET)
    text = TARGET.read_text(encoding="utf-8")
    prefix = dbase_prefix(TARGET)
    minted_css: list[str] = []
    minted_js: list[str] = []

    def make_href(css: str, index: int, media, _prefix: str = prefix):
        data = css.encode("utf-8")
        if len(data) < MIN_BYTES:
            return None
        h = hashlib.sha256(data).hexdigest()[:8]
        dst = CSS_ROOT / f"{h}.css"
        CSS_ROOT.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            dst.write_text(css, encoding="utf-8")
            minted_css.append(dst.name)
        return f"{_prefix}assets/css/{h}.css?v={h}"

    def make_js_src(js: str, index: int, _prefix: str = prefix):
        data = js.encode("utf-8")
        if len(data) < MIN_BYTES:
            return None
        h = hashlib.sha256(data).hexdigest()[:8]
        dst = JS_ROOT / f"{h}.js"
        JS_ROOT.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            dst.write_text(js, encoding="utf-8")
            minted_js.append(dst.name)
        return f"{_prefix}assets/js/{h}.js?v={h}"

    after_ext_html = externalize_js_text(externalize_css_text(text, make_href), make_js_src)
    write_page(TARGET, after_ext_html)
    after_externalize = sha256(TARGET)

    optimizer = make_optimizer(ROOT / "site")
    optimized = optimizer(TARGET.read_text(encoding="utf-8"), TARGET.parent)
    write_page(TARGET, optimized)
    after_optimize = sha256(TARGET)

    receipt = {
        "method": (
            "scripts.build_site.write_page via build_macro_target.py; "
            "lib.pages.externalize_css_text + externalize_js_text + write_page; "
            "scripts.optimize_assets.make_optimizer + lib.pages.write_page"
        ),
        "full_site_build": False,
        "manual_splice": False,
        "target": "site/macro.html",
        "utc": datetime.now(timezone.utc).isoformat(),
        "builder_raw_sha256": before,
        "after_externalize_sha256": after_externalize,
        "after_optimize_sha256": after_optimize,
        "git_blob_after": git_blob(TARGET),
        "minted_css": minted_css,
        "minted_js": minted_js,
        "contains_public_rail": "gde-context" in TARGET.read_text(encoding="utf-8")
        and "Risk context" in TARGET.read_text(encoding="utf-8"),
    }
    (OUT / "asset-optimizer-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
