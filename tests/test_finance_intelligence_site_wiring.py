"""Finance Intelligence page: the site builder carries its render hook.

Split out of tests/test_finance_intelligence_page.py so it runs in an always-on
legacy job. The assertion reads the site builder as TEXT. The exclusive
finance-intelligence job's closure check follows any read .py file through its
imports; for the site builder that is about 500 files across engine/, collectors/
and lib/, none of which this assertion depends on. An always-on job carries no
path filter, so no closure has to be declared and the assertion still runs on
every change to the builder.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_site_wires_finance_intelligence_hook():
    site_builder = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert "scripts.build_finance_intelligence_page" in site_builder
    assert "finance_intelligence.html render failed" in site_builder
