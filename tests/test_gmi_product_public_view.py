"""Public product rendering checks against a freshly built GMI source model.

These exercise publication boundaries and navigation, not a frozen screenshot's
markup. Model-owner tests remain separate from the product view.
"""
from copy import deepcopy
import json
import re

import pytest
from bs4 import BeautifulSoup

from scripts.build_gmi_explorer import build_live_model, render_site


@pytest.fixture(scope="module")
def current_model():
    return build_live_model()


@pytest.fixture(scope="module")
def pages(current_model, tmp_path_factory):
    out = tmp_path_factory.mktemp("gmi_public_product")
    return {p.name: p.read_text() for p in render_site(current_model, out)}


def test_all_topics_remain_addressable(current_model, pages):
    soup = BeautifulSoup(pages["gmi.html"], "html.parser")
    payload = json.loads(soup.select_one("#gmi-topic-data").string)
    ids = {t["id"] for t in payload["topics"]}
    assert ids == set(current_model["micros"])
    assert len(ids) == len(payload["topics"])
    assert all(t["paths"] for t in payload["topics"])
    index = BeautifulSoup(pages["gmi-index.html"], "html.parser")
    assert len(index.select("a.gmi-irow-name[href*='#theme=']")) == len(ids)


def test_public_pages_do_not_emit_internal_relationships(current_model, pages):
    combined = "\n".join(pages.values())
    for edge in current_model["edges"]:
        assert edge["relationship_key"] not in combined
    payload = json.loads(BeautifulSoup(pages["gmi.html"], "html.parser").select_one("#gmi-topic-data").string)
    assert set(payload) == {"topics", "categories", "asof"}
    assert "No relationships cleared for public display" in pages["gmi-relationships.html"]


def test_restricted_correction_history_cannot_leak(current_model, tmp_path):
    model = deepcopy(current_model)
    secret = "RESTRICTED-CORRECTION-SENTINEL"
    model["edges"][0]["correction_lineage"] = [{"known_at": "2026-11-03T00:00:00Z", "reason": "part_iii_only_amendment", "accession": secret, "amends_accession": secret}]
    rendered = "\n".join(p.read_text() for p in render_site(model, tmp_path))
    assert secret not in rendered


def test_rejected_product_is_not_presented_as_evidence(current_model, tmp_path):
    model = deepcopy(current_model)
    secret = "REJECTED-PRODUCT-SENTINEL"
    model["issuers"][0]["links"][0]["curation"]["decision"] = "REJECT"
    model["issuers"][0]["links"][0]["scope"]["product"] = secret
    rendered = "\n".join(p.read_text() for p in render_site(model, tmp_path))
    assert secret not in rendered


def test_dates_and_stage_are_together_and_no_stale_graph_permission(pages):
    soup = BeautifulSoup(pages["gmi.html"], "html.parser")
    card = soup.select_one(".gmi-evidence-card")
    assert card
    top = card.select_one(".gmi-evidence-date").get_text(" ", strip=True)
    assert "26 Feb 2024" in top and "Planned" in top
    assert "graph_membership_use" not in pages["gmi-issuer-mu.html"]
    assert "NOT_GRANTED" not in pages["gmi-issuer-mu.html"]


def test_company_route_and_shared_shell_remain_integrated(pages):
    assert "gmi-companies.html" in pages
    for name, html in pages.items():
        soup = BeautifulSoup(html, "html.parser")
        assert len(soup.select("h1")) == 1, name
        assert soup.select_one(".gmi-product-nav a[href='gmi-companies.html']"), name
        assert soup.select_one("script[src='theme.js']"), name
        assert soup.select_one("link[href='theme.css']"), name
        assert soup.select_one(".gmi-skip[href='#main']"), name
    company = BeautifulSoup(pages["gmi-companies.html"], "html.parser")
    assert company.select_one("link[rel='canonical']")["href"].endswith("gmi-companies.html")


def test_payload_escapes_source_text(current_model, tmp_path):
    model = deepcopy(current_model)
    model["issuers"][0]["links"][0]["scope"]["product"] = "</script><img src=x onerror=alert(1)>"
    html = next(p for p in render_site(model, tmp_path) if p.name == "gmi.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    assert not soup.select("img[onerror]")
    payload = json.loads(soup.select_one("#gmi-topic-data").string)
    assert any("</script>" in (c["product"] or "") for t in payload["topics"] for c in t["connections"])
