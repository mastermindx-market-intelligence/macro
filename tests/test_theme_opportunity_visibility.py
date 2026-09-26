"""Lane E shared theme-opportunity presentation contract.

The JSON cases are isolated fixtures only. They exercise the current display fields and
negative states; no fixture is permitted to become published market data.
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
FIXTURES = json.loads(
    (ROOT / "tests/fixtures/theme_opportunity_visibility.json").read_text(encoding="utf-8")
)


def _render(case_name: str) -> str:
    case = next(c for c in FIXTURES["cases"] if c["name"] == case_name)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(("html", "j2")),
    )
    template = env.from_string(
        """{% import '_theme_opportunity_visibility.html.j2' as opportunity %}
        {{ opportunity.strip(
            theme_id=case.theme_id,
            current_lens=case.current_lens,
            dimensions=case.dimensions,
            setup_id=case.setup_id,
            as_of=case.as_of
        ) }}"""
    )
    return template.render(case=case)


def test_fixture_is_explicitly_non_publishable() -> None:
    assert FIXTURES["_fixture_only"] is True
    assert "Never publish" in FIXTURES["_note"]


def test_shared_strip_keeps_five_dimensions_independent_and_bilingual() -> None:
    html = _render("qualified_entry")
    assert 'data-mx-opportunity="ai_semiconductors"' in html
    for dimension in ("leadership", "thesis", "crowding", "entry", "health"):
        assert f'data-dimension="{dimension}"' in html
    assert "Qualified entry" in html and "入场已确认" in html
    assert "Unavailable" in html and "暂不可用" in html
    assert "data-tip-en=" in html and "data-tip-zh=" in html
    assert "confidence" not in html.lower()


def test_shared_strip_preserves_lens_routes_and_canonical_setup_identity() -> None:
    html = _render("adverse_stale")
    assert 'href="radar.html#theme-defense_aerospace"' not in html
    assert 'aria-current="page"' in html
    assert 'href="foresight.html#theme-defense_aerospace"' in html
    assert 'href="state_of_themes.html#theme-defense_aerospace"' in html
    assert 'href="sector_central.html#theme-defense"' in html
    assert "Stale inputs" in html and 'data-state="stale"' in html


def test_unknowns_and_missing_setup_route_do_not_collapse_to_quiet_or_zero() -> None:
    html = _render("partial_unknown")
    assert html.count("Unavailable") >= 4
    assert 'data-route-unavailable="setup"' in html
    assert "sector_central.html#theme-" not in html
    assert ">0<" not in html
    assert "Quiet" not in html


def test_owned_surfaces_consume_one_component_contract_and_keep_deep_links() -> None:
    tracker = (TEMPLATES / "state_of_themes.html.j2").read_text(encoding="utf-8")
    foresight = (TEMPLATES / "foresight.html.j2").read_text(encoding="utf-8")
    radar = (TEMPLATES / "radar.html.j2").read_text(encoding="utf-8")
    panel = (ROOT / "site/radar_panel.js").read_text(encoding="utf-8")

    assert "_theme_opportunity_visibility.html.j2" in tracker
    assert "opportunity.tracker_strip" in tracker
    assert 'id="theme-{{ th.theme_id }}"' in tracker

    assert "_theme_opportunity_visibility.html.j2" in foresight
    assert "opportunity.foresight_strip" in foresight
    assert 'id="theme-{{ r.theme }}"' in foresight

    assert "_theme_opportunity_visibility.html.j2" in radar
    assert "opportunity.styles" in radar
    assert "function opportunityStrip(" in panel
    assert 'id="theme-' in panel
    for route in (
        "radar.html#theme-",
        "foresight.html#theme-",
        "state_of_themes.html#theme-",
        "sector_central.html#theme-",
    ):
        assert route in panel
