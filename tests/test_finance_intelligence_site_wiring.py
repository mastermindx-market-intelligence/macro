"""Finance Intelligence page: the site builder carries its render hook.

Split out of tests/test_finance_intelligence_page.py. The assertion reads the site
builder as TEXT. The exclusive finance-intelligence job's closure check follows any
read .py file through its imports; for the site builder that is about 500 files
across engine/, collectors/ and lib/, none of which this assertion depends on.

It runs in the public-render-fastlane legacy job (gate: code, inferred scope). That
job already owns scripts/build_site.py, so the assertion runs on every change to the
builder and adds no job to any packing probe. A job of its own would add one to every
probe (#8010 did; see test_exclusive_curation_narrows_ordinary_code_prs).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_site_wires_finance_intelligence_hook():
    site_builder = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert "scripts.build_finance_intelligence_page" in site_builder
    assert "finance_intelligence.html render failed" in site_builder
