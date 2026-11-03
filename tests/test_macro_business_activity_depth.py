"""A reference period is not a definition-publication clock (P12.T40)."""
from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

from lib import macro_suite_view
from scripts import build_macro_suite_pages as builder


ROOT = Path(__file__).resolve().parents[1]


def test_business_definition_version_does_not_invent_publication_date():
    page = next(p for p in builder.SUITE_PAGES if p.workspace_id == "business_activity")
    snapshot, artifact = builder.read_workspace(ROOT / "tests/fixtures/macro_suite_t11", page)
    assert snapshot["metrics"]["items"][0]["reference_period"]
    assert snapshot["metrics"]["items"][0]["released_at"] is None
    view = macro_suite_view.build_view(
        snapshot, page_built_at="2026-11-03T18:00:00Z", artifact=artifact,
        layout=builder._layout_for(page.workspace_id),
    )
    before = json.dumps(view, sort_keys=True)
    html = builder.render_page(builder._environment(ROOT), page, view)
    cards = BeautifulSoup(html, "html.parser").select(".mq-metric")
    assert len(cards) == len(view["metrics"])
    for metric, card in zip(view["metrics"], cards):
        definition = next(
            row.select_one("dd") for row in card.select(".mq-metric-meta > div")
            if row.select_one("dt .l-en").get_text(strip=True) == "Definition version"
        )
        # The owner supplies the version, but supplies no definition-release clock.
        # Do not promote its economic reference period to publication evidence.
        assert definition.get_text(strip=True) == (metric["definition_version"] or "—")
        reference = next(
            row.select_one("dd") for row in card.select(".mq-metric-meta > div")
            if row.select_one("dt .l-en").get_text(strip=True) == "Reference period"
        )
        if metric["reference_period"]:
            assert reference.get_text(strip=True) == metric["reference_period"]
    assert json.dumps(view, sort_keys=True) == before
