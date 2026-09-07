"""One-off evidence capture for the debt-maturity panel (packet B-F09-3,
META-CEO ruling round 2 fix round, MAJOR-3).

Round-2 review MAJOR-3: the previously committed evidence was full-page
ticker-page screenshots (5251-8350px tall) with no panel crop and no
recorded anchor offset, so a reviewer could not locate the #debt-maturity
element inside a reviewer's budget -- the theme-law dual-read could not
actually be performed from the committed matrix.

This script does NOT define a second evidence plane (scripts/
check_ui_visual_evidence.py's ABSOLUTE PROHIBITION): it builds four MINIMAL
fixture pages whose entire <body> is nothing but the #debt-maturity panel
(no ticker chrome, no hero, no other sections), and then calls the ONE
canonical capture tool, scripts/capture_page_evidence.py, to actually shoot
them. Because the fixture page contains nothing else, that tool's own
full-page screenshot IS a tight panel-level crop by construction -- this
satisfies MAJOR-3's "panel-level crop, not the whole ticker page" ask while
staying inside the single `mastermind.p0_evidence.v2` manifest schema the
design-system evidence gate requires.

Isolation (macro sparse-worktree / nightly-sole-advancer law): fixture HTML
+ a theme.css copy are written into a SCRATCH temp directory only (never
into site/ or data/); the capture tool serves that scratch directory itself
over its own local HTTP server. Output (PNGs + manifest.json + smells.json)
goes only under mockups/evidence/debt_maturity/ -- already tracked, already
this packet's own evidence directory.

Round-3 review BLOCKER: MAJOR-1's fix introduced a new user-facing terminal
branch (`unresolved`, its own EN/ZH copy) with zero dual-theme evidence --
house theme law treats missing evidence for a material user-facing change as
PARTIAL/BLOCKED, never PASS, so a text-only "tests cover it" argument does
not satisfy the law. `no_maturity_facts` (inherited from round 2, its own
copy too) was likewise never captured. Six pages are captured now: the four
the prior evidence run captured (reported / not_loaded / no_filings /
identity_mismatch) plus `unresolved` and `no_maturity_facts`. `not_applicable`
alone renders NO section (nothing to crop) and stays covered by
tests/test_debt_maturity.py's test_etf_page_renders_no_chip_and_no_section.

Usage::

    python3 -m scripts.capture_debt_maturity_evidence
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "debt_maturity"

STATUSES = ("reported", "not_loaded", "no_filings", "identity_mismatch", "unresolved", "no_maturity_facts")

# No baked data-theme/data-lang: scripts/capture_page_evidence.py's own
# _APPLY_STATE_SCRIPT sets those attributes after load (falling back to a
# direct docEl.setAttribute() call when window.setTheme/setLang are absent,
# exactly the case here -- this fixture loads no theme.js).
_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>debt-maturity evidence fixture -- {status}</title>
<link rel="stylesheet" href="theme.css">
<style>
  /* Flat, uniform background for this evidence fixture only -- theme.css's
     shared ambient aurora wash (html body::before, a soft gradient) is
     genuine product chrome on a real page but defeats the corner-pixel trim
     below (a gradient never matches a single corner color), so it is
     disabled here. This is capture tooling, not a shipped surface. */
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--text); }}
  body::before {{ display:none !important; }}
</style>
</head>
<body>
{section}
</body>
</html>
"""


def _status_contexts() -> dict[str, dict]:
    from engine.debt_maturity import extract_maturity_ladder

    fixture = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "debt_maturity" / "aapl_trimmed.json").read_text()
    )
    as_of = date(2025, 1, 1)
    reported = extract_maturity_ladder(fixture, cik="0000320193", as_of=as_of)
    no_filings = extract_maturity_ladder(None, cik="0000999999", as_of=as_of)
    not_loaded = {
        "schema": "debt_maturity.v1", "status": "not_loaded", "cik": "0000320193",
        "buckets": [], "total_reported_usd": None, "total_display": None,
        "near_share_pct": None, "buckets_reported": 0, "buckets_total": 6,
        "as_of": as_of.isoformat(),
    }
    # a mismatched cik on the SAME real facts -> engine's own identity_mismatch
    identity_mismatch = extract_maturity_ladder(fixture, cik="0000999999", as_of=as_of)
    # Round-3 review BLOCKER: `unresolved` (a CIK lookup was attempted and
    # found nothing -- scripts/build_stock_library.py's own shape, never
    # produced by the pure engine, so built by hand exactly as that call
    # site builds it) and `no_maturity_facts` (a real filing exists, via the
    # engine, but none of the six tags carry an annual period -- an empty
    # us-gaap facts block under the SAME cik).
    unresolved = {
        "schema": "debt_maturity.v1", "status": "unresolved", "cik": None,
        "buckets": [], "total_reported_usd": None, "total_display": None,
        "near_share_pct": None, "buckets_reported": 0, "buckets_total": 6,
        "as_of": as_of.isoformat(),
    }
    no_maturity_facts = extract_maturity_ladder(
        {"cik": "0000320193", "facts": {"us-gaap": {}}}, cik="0000320193", as_of=as_of,
    )
    assert reported["status"] == "reported", reported["status"]
    assert no_filings["status"] == "no_filings", no_filings["status"]
    assert identity_mismatch["status"] == "identity_mismatch", identity_mismatch["status"]
    assert no_maturity_facts["status"] == "no_maturity_facts", no_maturity_facts["status"]
    return {
        "reported": reported,
        "not_loaded": not_loaded,
        "no_filings": no_filings,
        "identity_mismatch": identity_mismatch,
        "unresolved": unresolved,
        "no_maturity_facts": no_maturity_facts,
    }


def _render_section(debt_maturity: dict) -> str:
    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.globals["t"] = i18n.t
    tmpl = env.get_template("_debt_maturity.html.j2")
    return tmpl.render(debt_maturity=debt_maturity)


def _write_fixtures(scratch: Path, contexts: dict[str, dict]) -> None:
    shutil.copy(TEMPLATES_DIR / "theme.css", scratch / "theme.css")
    for status, dm in contexts.items():
        section = _render_section(dm)
        (scratch / f"{status}.html").write_text(_SHELL.format(status=status, section=section))


def _trim_to_content(manifest_path: Path) -> None:
    """Post-capture: crop every captured PNG down to its actual content
    bounding box (the fixture page's body is background right up to the
    panel's own edges, so this IS a panel-level crop) and record the new
    pixel dims. `viewport_width`/`viewport_height` (the REQUESTED viewport,
    what the gate checks) are left untouched -- only `width`/`height` (the
    captured PNG's own pixel dims, which the gate only requires be non-None,
    never a specific value) change.
    """
    from PIL import Image, ImageChops

    manifest = json.loads(manifest_path.read_text())
    for page in manifest.get("pages", []):
        for state in page.get("states", []):
            if not state.get("captured") or not state.get("file"):
                continue
            png_path = manifest_path.parent / state["file"]
            if not png_path.exists():
                continue
            im = Image.open(png_path).convert("RGB")
            bg = im.getpixel((0, 0))
            diff = ImageChops.difference(im, Image.new("RGB", im.size, bg))
            bbox = diff.getbbox()
            if bbox is None:
                continue  # uniform background, nothing to crop to
            pad = 16
            left, top, right, bottom = bbox
            left = max(0, left - pad)
            top = max(0, top - pad)
            right = min(im.width, right + pad)
            bottom = min(im.height, bottom + pad)
            cropped = im.crop((left, top, right, bottom))
            cropped.save(png_path)
            state["width"], state["height"] = cropped.size
            state["bytes"] = png_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUT_DIR.glob("*.png"):
        stale.unlink()

    scratch = Path(tempfile.mkdtemp(prefix="dm_evidence_"))
    try:
        _write_fixtures(scratch, _status_contexts())
        routes = ",".join(f"/{status}.html" for status in STATUSES)
        cmd = [
            sys.executable, "-m", "scripts.capture_page_evidence",
            "--site-dir", str(scratch),
            "--routes", routes,
            "--output-dir", str(OUT_DIR),
            "--manifest", str(OUT_DIR / "manifest.json"),
            "--smells", str(OUT_DIR / "smells.json"),
            "--viewports", "desktop,mobile",
            "--locales", "en,zh",
            "--themes", "dark,light",
            "--max-pages", str(len(STATUSES)),
        ]
        result = subprocess.run(cmd, cwd=REPO_ROOT)
        if result.returncode != 0:
            return result.returncode
        _trim_to_content(OUT_DIR / "manifest.json")
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
