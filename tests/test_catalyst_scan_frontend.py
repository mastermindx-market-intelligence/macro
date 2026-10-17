"""Catalyst Session03 offline first-value UX: no backend/publication effects."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "render_catalyst_scan.py"
SOURCE_HTML = ROOT / "templates" / "catalyst_scan.html.j2"
SOURCE_JS = ROOT / "templates" / "catalyst_scan.js"
SOURCE_CSS = ROOT / "templates" / "catalyst_scan.css"


def _builder():
    spec = importlib.util.spec_from_file_location("catalyst_scan_preview", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_preview_render_scan_first_navigable(tmp_path):
    builder = _builder()
    page = builder.render_preview(tmp_path / "preview")
    assert page.is_file()
    html = page.read_text(encoding="utf-8")
    assert 'content="noindex,nofollow"' in html
    assert 'OFFLINE UI PREVIEW' in html
    assert 'name="referrer" content="no-referrer"' in html
    assert html.index('id="cs-scan-form"') < html.index('id="cs-optin"')
    assert 'id="cs-results"' in html and 'id="cs-optin"' in html
    assert 'id="cs-verify-form"' in html
    assert 'id="cs-js-needed"' in html
    assert 'href="/us_stocks.html"' in html
    assert "/stocks.html" not in html
    assert 'id="cs-scan-controls" disabled' in html
    assert 'name="email" type="email"' in html
    assert '<noscript>' in html and 'Nothing has been submitted' in html
    assert (page.parent / "catalyst_scan.js").read_bytes() == SOURCE_JS.read_bytes()
    assert (page.parent / "catalyst_scan.css").read_bytes() == SOURCE_CSS.read_bytes()
    assert page.parent == tmp_path / "preview"


def test_preview_refuses_live_site_and_overwrites(tmp_path):
    build = _builder()
    with pytest.raises(ValueError, match="live repository"):
        build.render_preview(ROOT / "site")
    with pytest.raises(ValueError, match="live repository"):
        build.render_preview(ROOT / "site" / "catalyst")
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "valuable.txt").write_text("do not touch")
    with pytest.raises(ValueError, match="empty"):
        build.render_preview(occupied)
    assert (occupied / "valuable.txt").read_text() == "do not touch"


def test_css_accessible_narrow_layout_and_focus():
    css = SOURCE_CSS.read_text(encoding="utf-8")
    assert "@media(max-width:600px)" in css
    assert "@media(max-width:345px)" in css
    assert "grid-template-columns:1fr" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert ".cs-scan-form fieldset" in css


def test_frontend_never_embeds_identity_or_receipt_in_share_urls():
    js = SOURCE_JS.read_text(encoding="utf-8")
    assert 'url.searchParams.set("tickers", lastTickers.join(","))' in js
    assert "window.location.pathname" in js
    assert "new URL(window.location.pathname, window.location.origin)" in js
    assert "credentials: \"same-origin\"" in js
    assert "referrerPolicy: \"no-referrer\"" in js
    assert "localStorage.setItem" not in js
    assert "localStorage.removeItem" not in js
    assert "sessionStorage." not in js
    assert "result.public_ref" in js
    assert "scan_receipt: scanReceipt" in js
    assert 'el("cs-scan-controls").disabled = false' in js


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_parses_with_node():
    out = subprocess.run(["node", "--check", str(SOURCE_JS)],
                         text=True, capture_output=True, timeout=12, check=False)
    assert out.returncode == 0, out.stderr
