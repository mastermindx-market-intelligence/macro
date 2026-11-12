"""The registered nuclear mount and the paid route, without a monkeypatch.

B2 registers ``nuclear_power``. This suite is the publication proof: the US
basket page emits that mount, and ``POST /api/themes/v1/research/query``
serves the real registration. ``uranium_miners`` and every non-US region
still publish nothing.
"""
from __future__ import annotations

from pathlib import Path

import jinja2
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.earnings as earnings_api
import app.theme_research as theme_research
from engine.market_ontology.theme_research_registry import (
    registration_for as real_registration_for,
)
from scripts.build_theme_detail import _theme_research_mount

ROOT = Path(__file__).resolve().parents[1]
_SLICES = "reactor_technology,nuclear_components,fuel_cycle"


def _render(mount: object) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
        undefined=jinja2.Undefined,
    )
    return env.get_template("_theme_research_mount.html.j2").render(
        theme_research_mount=mount,
    )


def test_us_nuclear_page_emits_the_three_slice_mount():
    context = _theme_research_mount("nuclear_power", "us")
    assert context is not None
    assert context["anchor_theme_id"] == "nuclear_power"
    assert context["slices"] == _SLICES
    html = _render(context)
    assert "Nuclear power industry research" in html
    assert "核电产业研究" in html
    assert f'data-slices="{_SLICES}"' in html
    assert "gmi-curation://" not in html
    assert "co:us:" not in html


def test_uranium_miners_and_non_us_publish_nothing():
    assert _theme_research_mount("uranium_miners", "us") is None
    assert _theme_research_mount("nuclear_power", "china") is None


def test_registered_route_serves_nuclear_without_a_monkeypatch():
    """Auth is overridden. ``registration_for`` is the real registry entry."""
    assert theme_research.registration_for is real_registration_for
    app = FastAPI()
    app.include_router(theme_research.router)
    app.dependency_overrides[earnings_api.require_site_full_user] = lambda: {
        "id": "paid-user", "tier": "essential",
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/themes/v1/research/query", json={
            "anchor_theme_id": "nuclear_power",
            "slice_key": "fuel_cycle",
            "view": "economics",
            "time_mode": "latest",
        })
    assert response.status_code != 404, response.text
    assert "private" in response.headers["cache-control"]
    assert "no-store" in response.headers["cache-control"]
    assert "noindex" in response.headers["x-robots-tag"]
    assert "noarchive" in response.headers["x-robots-tag"]
    body = response.json()
    assert body["schema"] == "nuclear_theme_research.v1"
    assert body["authority"]
    assert all(value is False for value in body["authority"].values())
