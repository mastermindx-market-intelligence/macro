"""tests/test_build_sanctions_map_no_path_stamp.py — F02 R1.

Pins the absence of the post-render ``data-news="1"`` path stamp that the
template-driven ``data-news-gbr="1"`` mechanism (templates/sanctions_map.html.j2
:142 + CSS :49/:62/:106) replaced. After PR #8281 the template is the only
mechanism, and the post-render ``str.replace`` in ``scripts/build_sanctions_map.py``
contradicted the D5 invariant asserted by tests/test_sanctions_map_event_pins.py
(:119-122 / :175 / :486) — the served page still carried the attribute the
tests promised was gone.
"""
from __future__ import annotations

import inspect
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent

# Belt-and-braces: the script does its own sys.path.insert, but importing the
# module from a bare ``pytest`` run wants the project root on PYTHONPATH too.
sys.path.insert(0, str(ROOT))


def test_builder_has_no_post_render_news_stamp():
    """The function and every reference to it must be gone from the module."""
    import scripts.build_sanctions_map as bsm

    assert not hasattr(bsm, "_apply_public_news_path_marks"), (
        "_apply_public_news_path_marks still defined — it was inert after #8281"
    )
    src = inspect.getsource(bsm)
    assert 'data-news="1"' not in src, (
        "build_sanctions_map.py still mentions inline data-news=\"1\"; the"
        " template's data-news-gbr is the only UK news mechanism"
    )
    assert "_apply_public_news_path_marks" not in src, (
        "build_sanctions_map.py still references _apply_public_news_path_marks"
    )


def test_build_output_has_no_inline_news_attr(monkeypatch, tmp_path):
    """End-to-end: build() under a UK event must produce data-news-gbr="1" and
    no inline data-news="1" path attribute."""
    import scripts.build_sanctions_map as bsm

    today = datetime.now(timezone.utc).date()
    asof = today.isoformat()
    vm = {
        "public_news": [
            {
                "title": "Bank Rate held at four percent",
                "url": "https://www.bankofengland.co.uk/news/2026/rate",
                "source": "boe_news",
                "jurisdiction": "UK",
                "iso3": "GBR",
                "asof": asof,
                "seendate": asof,
            }
        ],
        "public_news_state": "ok",
        "public_news_common": {"source": "Bank of England", "jurisdiction": "UK"},
        "countries": [],
        "coverage": None,
    }

    # The script calls ``sanctions_map.build()`` and ``sanctions_map.rungs_for(...)``
    # on its imported reference; replace that whole attribute with a fake module.
    fake_sanctions_map = SimpleNamespace(
        build=lambda: vm,
        rungs_for=lambda vm_, all_iso3: {},
    )
    monkeypatch.setattr(bsm, "sanctions_map", fake_sanctions_map)

    monkeypatch.setattr(bsm, "LATEST_JSON", tmp_path / "latest.json")
    # Narrowest patch: keep ``config.ROOT`` pointing at the real repo (the
    # Jinja loader walks ``config.ROOT / "templates"``); only ``config.load()``
    # needs to return a writable stub for the write target. ``write_page``
    # itself is monkeypatched so nothing actually hits disk.
    monkeypatch.setattr(
        bsm,
        "config",
        SimpleNamespace(ROOT=ROOT, load=lambda: {"storage": {"site_dir": str(tmp_path / "site")}}),
    )

    written: list[tuple[Path, str]] = []

    def _capture(path, html):
        written.append((path, html))

    monkeypatch.setattr(bsm, "write_page", _capture)

    bsm.build()

    assert len(written) == 1, f"expected one page write, got {len(written)}"
    _path, html = written[0]
    assert 'data-news-gbr="1"' in html, (
        "template mechanism (data-news-gbr=\"1\") must still mark a UK event"
    )
    assert 'data-news="1"' not in html, (
        "post-render data-news=\"1\" path stamp is back; the template is the"
        " only UK news mechanism"
    )


def test_template_is_only_news_mechanism():
    """The template still emits the only mechanism; no inline data-news="1"."""
    src = (ROOT / "templates" / "sanctions_map.html.j2").read_text(encoding="utf-8")
    assert "data-news-gbr=" in src, (
        "template must still emit data-news-gbr= for the GBR mark"
    )
    assert 'data-news="1"' not in src, (
        "template must not contain inline data-news=\"1\"; that was the"
        " post-render stamp the build script used to add"
    )