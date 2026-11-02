"""Consumer Cyclical PLNT card: the site builder carries its render hook.

Split out of tests/test_consumer_cyclical_plnt_page.py, following
tests/test_finance_intelligence_site_wiring.py. The assertion reads the site
builder as TEXT. The exclusive consumer-cyclical-economic-change job's closure
check follows any read .py file through its imports; for the site builder that
is about 500 files across engine/, collectors/ and lib/, none of which this
assertion depends on.

It runs in the public-render-fastlane legacy job (gate: code, inferred scope),
which already owns scripts/build_site.py, so the assertion runs on every change
to the builder and adds no job to any packing probe.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_site_wires_consumer_cyclical_plnt_hook():
    site_builder = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    # Exact import statement as it appears in scripts/build_site.py:8414
    # (quoted verbatim): a prefix-only match survives a renamed module
    # such as scripts.build_consumer_cyclical_plnt_page_typo.
    assert (
        "from scripts.build_consumer_cyclical_plnt_page import render"
        " as _render_plnt" in site_builder
    )
    assert "consumer_cyclical_plnt.html render failed" in site_builder
