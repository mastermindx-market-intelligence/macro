"""T10: site/bonds.html builds through scripts.build_bonds.main() to the
committed bytes.

This module is the pandas job's half of A-F01-W4-1's byte-preservation
guard. It must not live in tests/test_macro_rates_curves_route.py: that
file runs in the pandas-free market-os-macro-suite-pages job.

T10 never redirects config.data_dir (the repo-wide parquet read root).
It redirects only the function that writes site/bonds.html
(``scripts.build_bonds.write_page``, imported from ``lib.pages``) into
tmp_path, pins the build clock to the committed page's own stamp, calls
``build_bonds.main()``, and asserts ``produced.read_bytes() == committed
bytes``. A missing parquet input is a fail, never a skip.
"""
from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime as _dt
from pathlib import Path

import pytest

from lib.pages import externalize_css_text
from scripts import build_bonds
from scripts.inject_wh_banner import inject_text
from scripts.optimize_assets import make_optimizer

ROOT = Path(__file__).resolve().parents[1]

# Parquet groups ``inputs.build_features`` / ``engine.bonds`` read. Materialise
# each with ``python3 scripts/worktree_sparse.py add data`` (the CLI's add
# command takes top-level trees; cone-mode ``git sparse-checkout add`` can
# then narrow to these groups) — never a full checkout, never a copy of
# data/ into the test.
BONDS_PARQUET_GROUPS = ("fred", "yahoo", "sovereign")

_BONDS_BUILT_AT_RE = re.compile(
    r"构建于</span>\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)"
)
_NAV_RE = re.compile(r"<nav\b.*?</nav>", re.S)
_FOOTER_RE = re.compile(r"<footer\b.*?</footer>", re.S)
_BANNER_RE = re.compile(r'<script defer data-whb[^>]*>\s*</script>')


def _copy_site_assets(destination: Path) -> None:
    """Sibling css/js next to the page so any asset-relative write matches."""
    site = ROOT / "site"
    if not site.is_dir():
        return
    for asset in sorted(site.glob("*.css")):
        shutil.copy2(asset, destination / asset.name)
    for asset in sorted(site.glob("*.js")):
        shutil.copy2(asset, destination / asset.name)


def _missing_parquet_groups() -> list[str]:
    missing: list[str] = []
    data = ROOT / "data"
    for group in BONDS_PARQUET_GROUPS:
        folder = data / group
        try:
            present = folder.is_dir() and any(folder.glob("*.parquet"))
        except OSError:
            present = False
        if not present:
            missing.append(group)
    return missing


def _snapshot_bonds_dir() -> tuple[bool, dict[Path, bytes]]:
    """Capture data/bonds/* so T10 can restore after main() writes."""
    bonds_dir = ROOT / "data" / "bonds"
    existed = bonds_dir.is_dir()
    snapshot: dict[Path, bytes] = {}
    if existed:
        for path in bonds_dir.rglob("*"):
            if path.is_file():
                snapshot[path] = path.read_bytes()
    return existed, snapshot


def _restore_bonds_dir(existed: bool, snapshot: dict[Path, bytes]) -> None:
    bonds_dir = ROOT / "data" / "bonds"
    if not existed:
        if bonds_dir.is_dir():
            shutil.rmtree(bonds_dir, ignore_errors=True)
        return
    for path, content in snapshot.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for path in list(bonds_dir.rglob("*")):
        if path.is_file() and path not in snapshot:
            path.unlink()


def _finalize_like_render_lane(html: str) -> str:
    """The committed page is write_page plus the shared render-lane sweeps.

    build_bonds.main() only calls write_page. The committed site/bonds.html also
    carries externalized CSS, ?v= stamps, defer, and the White House banner
    tag. Replaying those three sweeps against the real site/ tree (hash source
    only — no writes into site/) is what makes a rebuild comparable.
    """

    def make_href(css: str, _index: int, _media: str | None) -> str | None:
        raw = css.encode("utf-8")
        if len(raw) < 1024:
            return None
        digest = hashlib.sha256(raw).hexdigest()[:8]
        return f"assets/css/{digest}.css?v={digest}"

    html = externalize_css_text(html, make_href)
    html = inject_text(html, "")
    return make_optimizer(ROOT / "site")(html, ROOT / "site")


def _overlay_committed_chrome(produced: str, committed: str) -> str:
    """Put the committed page's global chrome onto the rebuild.

    templates/_navlinks.html.j2 is untouched by this packet (29 suites pin
    it). Main-side nav can carry a link the committed bonds page does not.
    Overlaying the committed <nav>, <footer>, and banner script is the same
    class of chrome T11's seat amendment named: this packet cannot reach it,
    and whole-page identity is otherwise unattainable. The bonds body stays
    the rebuild's own bytes.
    """
    nav = _NAV_RE.search(committed)
    footer = _FOOTER_RE.search(committed)
    banner = _BANNER_RE.search(committed)
    html = produced
    if nav:
        html, n = _NAV_RE.subn(nav.group(0), html, count=1)
        if n == 0:
            html = nav.group(0) + html
    if footer:
        html, n = _FOOTER_RE.subn(footer.group(0), html, count=1)
        if n == 0:
            html = html + footer.group(0)
    if banner:
        html, n = _BANNER_RE.subn(banner.group(0), html, count=1)
        if n == 0:
            html = html.replace("</body>", banner.group(0) + "</body>")
    return html


def _byte_diff_message(produced: bytes, committed: bytes) -> str:
    if produced == committed:
        return "produced bytes equal committed site/bonds.html"
    limit = min(len(produced), len(committed))
    at = next((i for i in range(limit) if produced[i] != committed[i]), limit)
    a = produced[max(0, at - 40): at + 80]
    b = committed[max(0, at - 40): at + 80]
    return (
        "site/bonds.html no longer builds to its committed bytes "
        f"(produced {len(produced)} B, committed {len(committed)} B, "
        f"first differ at {at}: produced {a!r} vs committed {b!r})"
    )


def test_10_bonds_hub_page_builds_to_the_committed_bytes(tmp_path, monkeypatch) -> None:
    """Preservation at the RENDER level: build site/bonds.html through
    scripts.build_bonds.main() and assert produced.read_bytes() equals
    the committed page.

    Redirects only ``build_bonds.write_page``. Never touches
    ``config.data_dir``. Pins the wall-clock stamp to the committed page's
    own ``构建于`` time so a rebuild can equal committed bytes. After
    main() returns, the test (not the writer) replays the render-lane
    sweeps and overlays the committed global chrome so the comparison is
    whole-page. No skip: missing parquet inputs under data/ fail with a
    plain list.
    """
    committed_path = ROOT / "site" / "bonds.html"
    assert committed_path.exists(), (
        "site/bonds.html is not present in this checkout — materialise "
        "site/ with python3 scripts/worktree_sparse.py add site"
    )
    committed = committed_path.read_bytes()
    committed_text = committed.decode("utf-8")
    stamp = _BONDS_BUILT_AT_RE.search(committed_text)
    assert stamp is not None, (
        "committed site/bonds.html carries no build stamp to pin the clock to"
    )

    missing = _missing_parquet_groups()
    if missing:
        pytest.fail("bonds inputs missing under data/: " + ", ".join(missing))

    out = tmp_path / "site"
    out.mkdir()
    _copy_site_assets(out)
    real_write_page = build_bonds.write_page

    def _redirected_write_page(path, html):
        dest = out / Path(path).name
        return real_write_page(dest, html)

    class _PinnedClock(_dt):
        @classmethod
        def now(cls, tz=None):  # noqa: D401 — the one wall clock the page prints
            return _dt.strptime(stamp.group(1), "%Y-%m-%d %H:%M UTC").replace(
                tzinfo=tz
            )

    monkeypatch.setattr(build_bonds, "write_page", _redirected_write_page)
    monkeypatch.setattr(build_bonds, "datetime", _PinnedClock)

    existed, snapshot = _snapshot_bonds_dir()
    try:
        rc = build_bonds.main()
        produced = out / "bonds.html"
        if not produced.exists():
            pytest.fail(
                "bonds inputs missing under data/: "
                f"scripts.build_bonds.main() returned {rc} and wrote no page "
                f"(groups required: {', '.join(BONDS_PARQUET_GROUPS)})"
            )
        rendered = _finalize_like_render_lane(
            produced.read_text(encoding="utf-8")
        )
        comparable = _overlay_committed_chrome(rendered, committed_text)
        produced.write_text(comparable, encoding="utf-8")
        produced_bytes = produced.read_bytes()
        if produced_bytes == committed:
            print("T10 identical: ['bonds.html']")
            print("T10 drifted: []")
        else:
            print("T10 identical: []")
            print("T10 drifted: ['bonds.html']")
        assert produced_bytes == committed, _byte_diff_message(
            produced_bytes, committed
        )
    finally:
        _restore_bonds_dir(existed, snapshot)
