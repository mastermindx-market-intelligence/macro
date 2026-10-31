"""US Regime History: the site builder takes its table rows from the helper.

Split out of tests/test_regime_history_us_basis.py. The assertion reads the site
builder as TEXT. The exclusive regime-history-surfaces job's closure check follows any
read .py file through its imports; for the site builder that is about 500 files, none
of which this assertion depends on.

It runs in the public-render-fastlane legacy job, which already owns
scripts/build_site.py, so the assertion runs on every change to the builder and adds no
job to any packing probe.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_site_takes_its_rows_from_the_helper():
    site_builder = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert 'lifespan_rows=finished_lifespan_rows(hist["quad"])' in site_builder
