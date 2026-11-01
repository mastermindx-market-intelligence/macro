"""Focused tests for the retired /movers.html moved-notice stub.

Honest scope: the normal full run of scripts/build_ticker_pages walks the whole
market dataset (reads membership.parquet and ~1,595 stockdata blobs), which is
out of scope for a zero-data patch. These tests therefore exercise the real
helper (``_write_movers_stub``), the real CLI ``--movers-page-only`` early
return, the real Jinja template and the real ``lib.pages.write_page`` inside an
isolated temporary root (monkeypatched ``config.ROOT`` / module ``SITE``),
mirroring tests/test_redirect_stub_page_only.py's isolation approach — and
check the normal-run emission seam structurally rather than fabricating a
full-market execution.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import scripts.build_ticker_pages as bt
from lib import config

TARGET = "/stocks/index.html#today-movers"


@pytest.fixture
def isolated_site(tmp_path, monkeypatch):
    """Temporary site root; module globals + config.ROOT pointed at tmp."""
    site = tmp_path / "site"
    site.mkdir()
    monkeypatch.setattr(bt, "SITE", site)
    if hasattr(config, "ROOT"):
        monkeypatch.setattr(config, "ROOT", tmp_path)
    return site


def test_page_only_returns_before_run_and_writes_only_stub(isolated_site, monkeypatch):
    """--movers-page-only must exit ahead of run() and emit only the stub."""
    def _sentinel(*_a, **_k):
        raise AssertionError("run() must not be reached in --movers-page-only mode")

    monkeypatch.setattr(bt, "run", _sentinel)

    rc = bt.main(["--movers-page-only"])

    assert rc == 0
    assert (isolated_site / "movers.html").is_file()
    # page-only mode performs ONLY the fixed stub emission: no payloads/data
    assert not (isolated_site / "stocks").exists()
    assert not (isolated_site / "sitemap.xml").exists()
    assert not (isolated_site / "stockdata").exists()
    assert not (isolated_site / "ohlc").exists()


def test_stub_page_contract_uses_real_write_page(isolated_site):
    """Real template + real Jinja + real write_page: fixed target everywhere."""
    assert bt._write_movers_stub(isolated_site) is True

    html = (isolated_site / "movers.html").read_text(encoding="utf-8")

    # constant fixed target shared by the noscript refresh, the visible link
    # and the navigation script — never a forwarded hash/query
    assert html.count(TARGET) >= 3
    assert f'content="0;url={TARGET}"' in html
    assert f'href="{TARGET}"' in html
    assert "location.replace" in html
    assert "MMXSharedShell" in html
    assert "'replace'" in html
    assert "?t=" not in html
    assert "encodeURIComponent" not in html

    # standard seo head resolved + noindex,follow
    assert "_seo_head" not in html
    assert 'content="noindex,follow"' in html

    # existing theme + shared tokens, no stale Aug-7 population or build date
    assert re.search(r'href="theme\.css(?:\?v=[0-9a-f]{8})?"', html)
    assert not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", html)
    assert "generated_utc" not in html
    assert "lastmod" not in html


def test_write_movers_stub_is_failsoft_without_template(tmp_path, monkeypatch):
    """Missing template must warn and return False, never raise."""
    empty = tmp_path / "no_templates"
    empty.mkdir()
    site = tmp_path / "site2"
    site.mkdir()
    monkeypatch.setattr(bt, "TEMPLATES_DIR", empty)

    assert bt._write_movers_stub(site) is False
    assert not (site / "movers.html").exists()
    monkeypatch.setattr(bt, "SITE", site)
    assert bt.main(["--movers-page-only"]) == 1


def test_normal_run_emission_seam_is_guarded():
    """Structural seam check (no full-market fixture): the stub emission in
    run() sits on the successful canonical-index path, guarded to the canonical
    output (out == site/stocks) and to full runs only (no --only subset), and
    the CLI page-only short-circuit sits ahead of the run() call."""
    src = Path(bt.__file__).read_text(encoding="utf-8")

    assert 'if out == site / "stocks" and only_tickers is None:' in src
    assert "_write_movers_stub(site)" in src
    assert src.index("index_written = True") < src.index("_write_movers_stub(site)")

    assert "--movers-page-only" in src
    assert src.index("_write_movers_stub(SITE)") < src.index("rc = run(")


def test_canonical_movers_pair_is_current_and_has_fixed_marker():
    root = Path(bt.__file__).resolve().parents[1]
    source = (root / "templates/movers.html").read_bytes()
    emitted = root / "site/movers.html"
    if emitted.exists():
        assert emitted.read_bytes() == source
    assert b'data-mmx-movers-redirect="1"' in source
    assert b"var(--bg," in source and b"var(--text," in source


def test_stubs_lane_keeps_original_scopes_and_declares_page_only_owner():
    root = Path(bt.__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/render.yml").read_text()
    assert 'scripts.build_ticker_pages --movers-page-only' in workflow
    assert '|templates/movers.html) echo stubs;;' in workflow
    assert 'scripts/build_ticker_pages.py) echo stubs' not in workflow
    import yaml
    dag = yaml.safe_load((root / "config/dag.yml").read_text())
    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values(): yield from walk(child)
        elif isinstance(value, list):
            for child in value: yield from walk(child)
    assert any(row.get("module") == "scripts.build_ticker_pages" and row.get("args") == ["--movers-page-only"] for row in walk(dag))
