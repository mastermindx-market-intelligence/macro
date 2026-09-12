"""Regression coverage for live AI-brief refresh injection.

The dashboard embeds each brief body at render time. A tab left open across a
nightly render therefore keeps yesterday's body unless the shipped page carries
the small live-refresh client. The post-render optimizer is the common path for
all generated HTML surfaces, so it owns attaching that client to pages that
contain the shared ``.aib2`` renderer.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.optimize_assets import _attach_aibrief_freshness, optimize  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
_ASSET = "assets/js/aibrief-freshness.js"
_SOURCE = "_aibrief_freshness.js.j2"


def _write_asset(site: Path, body: str = "window.__aibriefFreshness = true;\n") -> None:
    asset = site / _ASSET
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text(body)


def test_optimizer_attaches_versioned_live_refresh_to_aibrief_page(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    _write_asset(site)
    (site / "macro.html").write_text(
        '<html><head></head><body><div class="aib2" data-lens="macro">'
        '<span class="aib2-hdr-date">2026-09-09</span></div></body></html>'
    )

    assert optimize(site) == 1

    out = (site / "macro.html").read_text()
    refs = re.findall(
        r'<script src="assets/js/aibrief-freshness\.js\?v=[0-9a-f]{8}" defer></script>',
        out,
    )
    assert len(refs) == 1
    assert out.index(refs[0]) < out.lower().index("</body>")

    # A second optimizer pass must not add a second client or rewrite the page.
    assert optimize(site) == 0
    assert (site / "macro.html").read_text().count("aibrief-freshness.js") == 1


def test_optimizer_syncs_render_owned_freshness_source_before_hashing(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    templates = tmp_path / "templates"
    templates.mkdir()
    source_body = "window.__aibriefFreshness = 'render-owned-source';\n"
    (templates / _SOURCE).write_text(source_body)
    _write_asset(site, "window.__aibriefFreshness = 'stale-generated-output';\n")
    page = site / "macro.html"
    page.write_text(
        '<html><body><div class="aib2" data-lens="macro">'
        '<span class="aib2-hdr-date">2026-09-09</span></div></body></html>'
    )

    assert optimize(site) == 1

    assert (site / _ASSET).read_text() == source_body
    stamp = hashlib.sha256(source_body.encode()).hexdigest()[:8]
    assert f'aibrief-freshness.js?v={stamp}' in page.read_text()


def test_optimizer_uses_depth_correct_asset_path(tmp_path: Path) -> None:
    site = tmp_path / "site"
    nested = site / "desk" / "daily"
    nested.mkdir(parents=True)
    _write_asset(site)
    page = nested / "index.html"
    page.write_text(
        "<html><body><section class='panel aib2' data-lens='macro'></section></body></html>"
    )

    assert optimize(site) == 1

    out = page.read_text()
    assert re.search(
        r'<script src="\.\./\.\./assets/js/aibrief-freshness\.js\?v=[0-9a-f]{8}" defer></script>',
        out,
    )


def test_optimizer_does_not_duplicate_existing_refresh_client(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    _write_asset(site)
    (site / "macro.html").write_text(
        '<html><body><div class="aib2" data-lens="macro"></div>'
        '<script src="assets/js/aibrief-freshness.js"></script></body></html>'
    )

    assert optimize(site) == 1

    out = (site / "macro.html").read_text()
    assert out.count("aibrief-freshness.js") == 1
    assert re.search(r'aibrief-freshness\.js\?v=[0-9a-f]{8}', out)


def test_optimizer_does_not_attach_refresh_to_unrelated_page(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    _write_asset(site)
    original = "<html><head></head><body><p>ordinary page</p></body></html>"
    (site / "about.html").write_text(original)

    optimize(site)

    assert "aibrief-freshness.js" not in (site / "about.html").read_text()


def test_optimizer_fails_open_when_freshness_asset_is_missing(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    page = site / "macro.html"
    original = '<html><body><div class="aib2" data-lens="macro"></div></body></html>'
    page.write_text(original)

    optimize(site)

    assert "aibrief-freshness.js" not in page.read_text()


def test_every_shipped_shared_brief_surface_is_eligible_for_refresh() -> None:
    site = ROOT / "site"
    source = ROOT / "templates" / _SOURCE
    assert source.is_file()
    assert (site / _ASSET).is_file()
    assert source.read_bytes() == (site / _ASSET).read_bytes()

    for name in ("macro.html", "china.html", "hk.html", "aibrief.html"):
        page = site / name
        text = page.read_text(encoding="utf-8")
        assert re.search(r'class=["\'][^"\']*\baib2\b', text), name

        out = _attach_aibrief_freshness(text, page.parent, site)
        assert out.count("aibrief-freshness.js") == 1, name
        assert out.index("aibrief-freshness.js") < out.lower().rindex("</body>"), name
